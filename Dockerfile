# syntax=docker/dockerfile:1
# Image cible : < 1 Go (python:3.11-slim + deps ML minimales)
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dépendances système minimales pour scipy / sklearn wheels
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Installer uniquement les dépendances runtime (pas de xgboost, matplotlib, jupyter)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier uniquement l'application et le modèle final
COPY app/ ./app/
COPY models/final_model.joblib ./models/final_model.joblib

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
