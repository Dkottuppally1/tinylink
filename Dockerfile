FROM python:3.12-slim
WORKDIR /code

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# this packages my app into a container so that when other devs are opening up my application all they need to do is open docker and run this in a container