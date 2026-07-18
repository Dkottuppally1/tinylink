import os
import pytest 
from fastapi.testclient import TestClient

os.environ.setdefault("TESTING", "1")

from app import main # noqa E402

@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test_tinylink.db"
    monkeypatch.setattr (main, "DB_PATH", str (test_db_path))
    main.init_db()
    yield

@pytest.fixture
def client():
    return TestClient(main.app)

def test_root(client):
    response = client.get("/")
    assert response.status_code == 200

def test_shorten_returns_code(client):
    response = client.post("/shorten", json={"url": "https://example.com/"})
    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert len(data["code"]) == 6
    assert data["original_url"] == "https://example.com/"

def test_redirect_to_original(client):
    shorten_resp = client.post("/shorten", json={"url":"https://example.com/"})
    code = shorten_resp.json()["code"]
    redirect_resp = client.get(f"/r/{code}", follow_redirects=False)
    assert redirect_resp.status_code in (302, 307)
    assert redirect_resp.headers["location"] == "https://example.com/"

def test_redirect_unknown_code_returns_404(client):
    response = client.get("/r/doesnotexist", follow_redirects=False)
    assert response.status_code == 404


def test_invalid_url_is_rejected(client):
    response = client.post("/shorten", json={"url": "not-a-valid-url"})
    assert response.status_code == 422


def test_click_count_increments_on_redirect(client):
    shorten_resp = client.post("/shorten", json={"url": "https://example.com"})
    code = shorten_resp.json()["code"]
    client.get(f"/r/{code}", follow_redirects=False)
    client.get(f"/r/{code}", follow_redirects=False)
    stats_resp = client.get(f"/stats/{code}")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["click_count"] == 2


def test_generated_codes_are_unique(client):
    codes = set()
    for _ in range(20):
        resp = client.post("/shorten", json={"url": "https://example.com"})
        codes.add(resp.json()["code"])
    assert len(codes) == 20
