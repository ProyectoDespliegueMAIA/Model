FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DENGUE_API_DATA_DIR=/app/data/api_dengue OPENBLAS_NUM_THREADS=1
WORKDIR /app
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt && useradd --create-home dengue
COPY src/dengue/ /app/src/dengue/
COPY data/api_dengue/ /app/data/api_dengue/
USER dengue
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s CMD ["python","-c","import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2)"]
CMD ["python","-m","uvicorn","dengue.api:app","--app-dir","src","--host","0.0.0.0","--port","8000"]
