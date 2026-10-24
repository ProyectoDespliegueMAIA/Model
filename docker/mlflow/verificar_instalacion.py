"""Prueba de infraestructura repetible: parámetros, métricas y artefactos vía HTTP."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import mlflow
from mlflow import MlflowClient


def main():
    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
    experiment = mlflow.set_experiment("verificacion_infraestructura")
    client = MlflowClient()
    previous = client.search_runs([experiment.experiment_id],
        filter_string="tags.proposito = 'verificacion_docker_v1'", max_results=1)
    if previous:
        run_id = previous[0].info.run_id
    else:
        with mlflow.start_run(run_name="instalacion_docker", tags={
            "proposito": "verificacion_docker_v1", "tipo": "infraestructura",
            "descripcion": "Datos sintéticos de prueba; no es un experimento de dengue."}) as run:
            mlflow.log_param("version_mlflow", mlflow.__version__)
            mlflow.log_metric("verificacion", 1.0)
            mlflow.log_dict({"estado": "correcto", "datos": "sinteticos"}, "verificacion.json")
            run_id = run.info.run_id
    stored = client.get_run(run_id)
    assert stored.info.status == "FINISHED"
    assert stored.data.metrics["verificacion"] == 1.0
    assert stored.data.params["version_mlflow"] == mlflow.__version__
    with TemporaryDirectory() as dest:
        artifact = client.download_artifacts(run_id, "verificacion.json", dest)
        assert json.loads(Path(artifact).read_text()) == {"estado": "correcto", "datos": "sinteticos"}
    print(json.dumps({"estado": "correcto", "run_id": run_id,
        "version": mlflow.__version__, "reutilizado": bool(previous),
        "metricas_y_artefactos": "verificados"}))


if __name__ == "__main__":
    main()
