FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY api/ ./api/
COPY query/ ./query/

# Data directory (mounted at runtime via volume)
RUN mkdir -p /data/chroma_store /data/figures

ENV SCZ_DATA_DIR=/data
ENV SCZ_FIGURES_DIR=/data/figures
ENV PYTHONPATH=/app

EXPOSE 8003

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8003"]
