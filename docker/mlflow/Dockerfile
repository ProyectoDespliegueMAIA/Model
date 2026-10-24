FROM ghcr.io/mlflow/mlflow:v3.17.2
ENV PYTHONUNBUFFERED=1
WORKDIR /opt/mlflow
COPY requirements.txt .
RUN python -c "import mlflow; assert mlflow.__version__ == '3.17.2'"
COPY verificar_instalacion.py .
EXPOSE 5000
CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000"]
