"""Registro explícito en MLflow; no entrena, no usa autolog y no publica microdatos."""
import hashlib
import json
import math
from pathlib import Path
import tempfile
import pandas as pd

METRICAS = ["n", "prevalencia", "umbral_probabilidad", "sensibilidad", "precision",
            "f1", "f2", "especificidad", "pr_auc_AP", "roc_auc", "brier", "tn", "fp", "fn", "tp"]
CONTRATO = "importacion_v1"


def preparar_metricas(tabla):
    """Una ejecución por método; NaN queda documentado como indefinido, nunca como cero."""
    if tabla.empty or tabla.bloque.duplicated().any():
        raise ValueError("Se requiere exactamente una fila por bloque en cada ejecución.")
    if "modelo" in tabla and tabla.modelo.nunique() != 1:
        raise ValueError("No mezclar métodos en la misma ejecución.")
    valores, indefinidas = {}, []
    for row in tabla.to_dict("records"):
        for nombre in METRICAS:
            clave = f"{row['bloque']}.{nombre}"
            valor = row[nombre]
            if pd.isna(valor):
                indefinidas.append(clave)
            elif not math.isfinite(float(valor)):
                raise ValueError(f"Métrica no finita: {clave}")
            else:
                valores[clave] = float(valor)
    return valores, sorted(indefinidas)


def huella_registro(params, metricas, archivos):
    """Incluye contenido de artefactos, no rutas absolutas ni fecha de importación."""
    payload = {"contrato": CONTRATO, "parametros": params, "metricas": metricas,
               "archivos": {nombre: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                            for nombre, path in sorted(archivos.items())}}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()


def json_seguro(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False, default=str), encoding="utf-8")


def verificar_registro(client, run_id, parametros, metricas, indefinidas, huella):
    """Comprueba los valores guardados y el manifiesto remoto, también al reutilizar."""
    run = client.get_run(run_id)
    if run.info.status != "FINISHED":
        raise ValueError(f"La ejecución {run_id} no terminó correctamente.")
    assert run.data.tags["huella_importacion"] == huella
    for key, value in parametros.items():
        assert run.data.params[key] == str(value), (run_id, key)
    assert set(run.data.metrics) == set(metricas), run_id
    for key, value in metricas.items():
        assert math.isclose(run.data.metrics[key], value, rel_tol=0, abs_tol=1e-12), key
    assert not set(indefinidas).intersection(run.data.metrics)
    with tempfile.TemporaryDirectory() as dest:
        path = client.download_artifacts(run_id, "trazabilidad/manifiesto.json", dest)
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
        assert manifest["huella_importacion"] == huella
        assert manifest["metricas_indefinidas"] == indefinidas
        for artifact_path, expected in manifest["artefactos_sha256"].items():
            downloaded = client.download_artifacts(run_id, artifact_path, dest)
            assert hashlib.sha256(Path(downloaded).read_bytes()).hexdigest() == expected, artifact_path
    return run


def registrar_ejecucion(*, tracking_uri, experimento, nombre, parametros, etiquetas,
                       tabla_metricas, archivos, modelo=None, ejemplo=None):
    """Función común para registrar una ejecución ya evaluada con artefactos permitidos.

    El llamador valida primero datos e inferencias. Si el contenido ya está registrado,
    recupera esa ejecución y comprueba su integridad en lugar de duplicarla.
    """
    import mlflow
    import mlflow.sklearn
    from mlflow.models import infer_signature
    from mlflow import MlflowClient
    import importlib.metadata

    for nombre_archivo, path in archivos.items():
        if Path(nombre_archivo).is_absolute() or '..' in Path(nombre_archivo).parts:
            raise ValueError("La ruta del artefacto debe ser relativa y permanecer dentro de la ejecución.")
        if Path(nombre_archivo).name != Path(path).name:
            raise ValueError("El nombre declarado del artefacto debe coincidir con el archivo local.")
    valores, indefinidas = preparar_metricas(tabla_metricas)
    huella = huella_registro(parametros, valores, archivos)
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)
    exp = client.get_experiment_by_name(experimento)
    exp_id = exp.experiment_id if exp else client.create_experiment(experimento)
    matches = client.search_runs([exp_id], filter_string=(
        f"tags.huella_importacion = '{huella}' and attributes.status = 'FINISHED'"))
    if matches:
        if len(matches) != 1:
            raise ValueError("Hay ejecuciones duplicadas con la misma huella; revisar antes de importar.")
        run_id = matches[0].info.run_id
        verificar_registro(client, run_id, parametros, valores, indefinidas, huella)
        return {"run_id": run_id, "reutilizado": True,
                "modelo_uri": matches[0].data.tags.get("modelo_uri")}
    if mlflow.active_run() is not None:
        raise ValueError("Cerrar la ejecución activa antes de registrar una ejecución independiente.")
    with mlflow.start_run(experiment_id=exp_id, run_name=nombre, tags={
            **etiquetas, "huella_importacion": huella, "contrato_registro": CONTRATO}) as run:
        run_id = run.info.run_id
        mlflow.log_params(parametros)
        mlflow.log_metrics(valores, synchronous=True)
        for artifact_path, local_path in archivos.items():
            parent = str(Path(artifact_path).parent).replace("\\", "/")
            mlflow.log_artifact(str(local_path), artifact_path=parent if parent != "." else None)
        with tempfile.TemporaryDirectory() as dest:
            manifest = Path(dest) / "manifiesto.json"
            json_seguro(manifest, {"huella_importacion": huella,
                "metricas_indefinidas": indefinidas,
                "artefactos_sha256": {nombre: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                                      for nombre, path in archivos.items()},
                "tipo_ejecucion": etiquetas["tipo_ejecucion"],
                "nota": "Hora MLflow = registro actual; no representa la fecha del entrenamiento original."})
            mlflow.log_artifact(str(manifest), artifact_path="trazabilidad")
        modelo_uri = None
        if modelo is not None:
            # Predice probabilidades. El umbral se conserva por separado como regla de decisión.
            requirements = [f"{pkg}=={importlib.metadata.version(pkg)}" for pkg in
                            ["scikit-learn", "numpy", "pandas", "joblib", "cloudpickle"]]
            info = mlflow.sklearn.log_model(sk_model=modelo, name="logistica",
                signature=infer_signature(ejemplo, modelo.predict_proba(ejemplo)),
                input_example=ejemplo, pip_requirements=requirements,
                pyfunc_predict_fn="predict_proba")
            modelo_uri = info.model_uri
            mlflow.set_tag("modelo_uri", modelo_uri)
    verificar_registro(client, run_id, parametros, valores, indefinidas, huella)
    return {"run_id": run_id, "reutilizado": False, "modelo_uri": modelo_uri}
