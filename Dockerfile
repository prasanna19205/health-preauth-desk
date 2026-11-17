
FROM python:3.11-slim

WORKDIR /app

COPY agents/requirements.txt ./agents/requirements.txt
COPY rag/requirements.txt ./rag/requirements.txt

RUN pip install --no-cache-dir -r agents/requirements.txt \
    && pip install --no-cache-dir -r rag/requirements.txt \
    && pip install --no-cache-dir fastapi uvicorn

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
