import random
import string
import sqlite3
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl


app = FastAPI(title="TinyLink")
DB_PATH = "tinylink.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
def init_db():
    conn = get_db()
    conn.execute(""" 
        CREATE TABLE IF NOT EXISTS links(
            code TEXT PRIMARY KEY,
            original_url TEXT NOT NULL,
            created_at TEXT NOT NULL,
            click_count INTEGER DEFAULT 0
        )
                
    """)
    conn.commit()
    conn.close()

init_db()

class ShortenRequest(BaseModel):
    url: HttpUrl

class ShortenResponse(BaseModel):
    code: str
    short_url: str
    original_url: str

class StatsResponse(BaseModel):
    code: str
    original_url: str
    click_count: int
    created_at: str

def generate_code(length: int = 6) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))

def code_exists(conn, code:str) -> bool:
    row  = conn.execute("SELECT 1 FROM links WHERE code = ?", (code,)).fetchone()
    return row is not None

def generate_unique_code(conn) -> str:
    code = generate_code()
    while code_exists(conn, code):
        code = generate_code()
    return code

@app.post("/shorten", response_model=ShortenResponse)
def shorten_url(request: ShortenRequest):
    conn = get_db()
    code = generate_unique_code(conn)
    conn.execute(
        "INSERT INTO links (code, original_url, created_at, click_count) VALUES (?, ?, ?, 0)",
        (code, str(request.url), datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()
    return ShortenResponse(code = code, short_url = f"/r/{code}", original_url = str(request.url))

@app.get("/r/{code}")
def redirect_to_orginal(code: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM links WHERE code = ?", (code,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code= 404, detail = "short link not found")
    conn.execute("UPDATE links SET click_count = click_count + 1 WHERE code  = ?", (code,))
    conn.commit()
    original_url = row["original_url"]
    conn.close()
    return RedirectResponse(url = original_url)

@app.get("/stats/{code}", response_model=StatsResponse)
def get_stats(code: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM links WHERE code = ?", (code,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Short link not found")
    return StatsResponse(
        code=row["code"],
        original_url=row["original_url"],
        click_count=row["click_count"],
        created_at=row["created_at"],
    )


@app.get("/")
def root():
    return {"message": "TinyLink API is running. POST /shorten to create a short link."}