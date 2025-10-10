# FastAPI VLM API Dockerfile
FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y build-essential python3-dev

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
