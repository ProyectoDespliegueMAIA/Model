"""Verifica e importa referencias retrospectivas en MLflow. Nunca llama a fit()."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
import tempfile
import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dengue.pipeline import config, raiz_salida, FEATURES
from dengue.validacion_modelo import verificar_resultados
from dengue.seguimiento import registrar_ejecucion, json_seguro

METODOS = ["logistica_umbral_validado", "logistica_umbral_0_5", "persistencia_conteo",
           "prevalencia_entrenamiento", "siempre_alerta"]
CIUDADES = {"cali": "piloto", "medellin": "medellin",
            "villavicencio": "villavicencio", "ibague": "ibague"}


def preparar_ciudad(ciudad):
    cfg = config(CIUDADES[ciudad])
    salida = raiz_salida(cfg)
    tablas = salida / "reports/tables"
    panel_path = salida / f"data/processed/{ciudad}_panel_semanal.csv"
    panel = pd.read_csv(panel_path, dtype={"cod_municipio": "string"},
        parse_dates=["inicio_semana", "fin_semana", "corte_prediccion"])
    if not panel.cod_municipio.eq(cfg["municipio"]).all():
        raise ValueError(f"{ciudad}: el panel contiene otro municipio.")
    if panel.duplicated(["anio_epi", "semana_epi"]).any():
        raise ValueError(f"{ciudad}: semanas duplicadas.")
    model_path = salida / f"modelos/logistica_{ciudad}_{cfg['version_experimento']}.joblib"
    artifact = joblib.load(model_path)
    metadata_path = model_path.with_suffix(".json")
    if json.loads(metadata_path.read_text(encoding="utf-8")) != artifact["metadata"]:
        raise ValueError(f"{ciudad}: metadatos JSON y joblib diferentes.")
    m = pd.read_csv(tablas / "metricas_logistica.csv")
    p = pd.read_csv(tablas / "predicciones_logistica.csv", parse_dates=["inicio_semana"])
    s = pd.read_csv(tablas / "particiones_temporales.csv")
    c = pd.read_csv(tablas / "coeficientes_logistica.csv")
    if set(m.modelo) != set(METODOS):
        raise ValueError(f"{ciudad}: métodos faltantes o inesperados.")
    controls = verificar_resultados(panel, cfg, artifact["pipeline"], artifact["metadata"], m, p, s, c)
    # La selección del umbral guardada también debe reproducir validación.
    from sklearn.metrics import fbeta_score
    grid = pd.read_csv(tablas / "seleccion_umbral_validacion.csv")
    np.testing.assert_allclose(grid.umbral, np.arange(.10, .91, .05))
    val = panel.loc[panel.elegible_modelo & panel.anio_epi.between(
        cfg["fin_entrenamiento"]+1, cfg["fin_validacion"])]
    prob = artifact["pipeline"].predict_proba(val[FEATURES])[:, 1]
    np.testing.assert_allclose(grid.f2_validacion,
        [fbeta_score(val.exceso, prob >= t, beta=2, zero_division=0) for t in grid.umbral])
    return {"ciudad": ciudad, "cfg": cfg, "salida": salida, "tablas": tablas,
        "panel": panel, "panel_path": panel_path, "modelo_path": model_path,
        "metadata_path": metadata_path, "modelo": artifact["pipeline"],
        "metadata": artifact["metadata"], "metricas": m, "predicciones": p,
        "particiones": s, "coeficientes": c, "controles": controls}


def figura_confusion(df, destino, ciudad, metodo):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    fig = Figure(figsize=(12, 3.5))
    FigureCanvasAgg(fig)
    axes = fig.subplots(1, len(df), squeeze=False)[0]
    for ax, row in zip(axes, df.itertuples()):
        matrix = np.array([[row.tn, row.fp], [row.fn, row.tp]], dtype=int)
        ax.imshow(matrix, cmap="Blues")
        for (i, j), value in np.ndenumerate(matrix):
            ax.text(j, i, str(value), ha="center", va="center")
        ax.set(xticks=[0, 1], yticks=[0, 1], xticklabels=["Sin alerta", "Alerta"],
            yticklabels=["Sin exceso", "Exceso"], title=row.bloque, xlabel="Predicción")
    fig.suptitle(f"{ciudad} · {metodo}", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, .94))
    fig.savefig(destino, dpi=140)


def importar(preparado, metodo, tracking_uri, experimento, directorio):
    cfg, ciudad = preparado["cfg"], preparado["ciudad"]
    temp = Path(directorio) / ciudad / metodo
    temp.mkdir(parents=True)
    metricas = preparado["metricas"].loc[preparado["metricas"].modelo.eq(metodo)].copy()
    pred = preparado["predicciones"].loc[preparado["predicciones"].modelo.eq(metodo)].copy()
    logistica = metodo.startswith("logistica_")
    umbral = float(metricas.iloc[0].umbral_probabilidad)
    params = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v
              for k, v in cfg.items() if k not in ["directorio_salida", "slug"]}
    params.update(metodo=metodo, variables=json.dumps(FEATURES),
        n_variables=len(FEATURES), umbral_probabilidad=umbral,
        sha256_panel=preparado["metadata"]["sha256_panel"],
        sha256_csv_panel=hashlib.sha256(preparado["panel_path"].read_bytes()).hexdigest(),
        origen="importado", validacion="bloques_fijos_retrospectivos",
        comparacion="dentro_de_cada_ciudad", entrenamiento_realizado="false")
    if logistica:
        estimator = preparado["modelo"][-1]
        params.update(C=estimator.C, solver=estimator.solver, max_iter=estimator.max_iter,
                      regularizacion="L2", escalador="StandardScaler", columna_probabilidad_exceso=1)
    elif metodo == "prevalencia_entrenamiento":
        params["probabilidad_constante"] = float(preparado["panel"].loc[
            preparado["panel"].elegible_modelo & preparado["panel"].anio_epi.le(
                cfg["fin_entrenamiento"]), "exceso"].mean())
    reglas = {"logistica_umbral_validado": "predict_proba(X)[:,1] >= umbral seleccionado por F2 en validación",
        "logistica_umbral_0_5": "predict_proba(X)[:,1] >= 0.5; mismos coeficientes que la logística seleccionada",
        "persistencia_conteo": "lag_1 > umbral_casos de la semana objetivo; salida binaria, no probabilidad calibrada",
        "prevalencia_entrenamiento": "Probabilidad constante: media de exceso en entrenamiento; alerta si >=0.5",
        "siempre_alerta": "Probabilidad de referencia 1 y alerta en todas las semanas"}
    tags = {"ciudad": cfg["nombre_municipio"], "cod_municipio": cfg["municipio"],
        "metodo": metodo, "tipo_ejecucion": "importado", "version_datos": cfg["version_experimento"],
        "familia": "regresion_logistica" if logistica else "referencia",
        "sin_reentrenamiento": "true", "fecha_ajuste_original": "no_registrada",
        "git_commit_importacion": os.environ.get("DENGUE_GIT_COMMIT", "no_disponible"),
        "advertencia": "Retrospectivo: conteos finales, sin reconstrucción de disponibilidad al corte.",
        "mlflow.note.content": (f"{cfg['nombre_municipio']}: {reglas[metodo]}. "
            "Importación del experimento existente; no hubo ajuste. Hora MLflow = importación. "
            "2024/2025 ya observados: no elegir parámetros con estos bloques y presentarlos como pruebas nuevas.")}
    archivos = {}

    def adjuntar(path, carpeta):
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
        archivos[f"{carpeta}/{path.name}"] = path

    for name, frame in [("metricas.csv", metricas), ("predicciones_semanales.csv", pred),
                        ("particiones.csv", preparado["particiones"]),
                        ("controles.csv", preparado["controles"])]:
        frame.to_csv(temp / name, index=False)
        adjuntar(temp / name, "evaluacion")
    if logistica:
        preparado["coeficientes"].to_csv(temp / "coeficientes.csv", index=False)
        adjuntar(temp / "coeficientes.csv", "evaluacion")
        adjuntar(preparado["modelo_path"], "modelo_original")
        adjuntar(preparado["metadata_path"], "modelo_original")
        adjuntar(preparado["tablas"] / "seleccion_umbral_validacion.csv", "evaluacion")
    json_seguro(temp / "configuracion.json", cfg)
    json_seguro(temp / "regla_decision.json", {"metodo": metodo, "regla": reglas[metodo],
        "umbral_probabilidad": umbral, "probabilidad_exceso_columna": 1 if logistica else None,
        "fecha_entrenamiento_original": "desconocida; la fecha de importación no la sustituye"})
    runtime = {"python": platform.python_version(), "paquetes": {
        pkg: importlib.metadata.version(pkg) for pkg in
        ["mlflow", "scikit-learn", "pandas", "numpy", "joblib", "matplotlib"]},
        "nota": "Entorno de importación y verificación; no atribuirlo al ajuste original."}
    json_seguro(temp / "entorno_importacion.json", runtime)
    for name in ["configuracion.json", "regla_decision.json", "entorno_importacion.json"]:
        adjuntar(temp / name, "trazabilidad")
    for source in [ROOT / "src/dengue/pipeline.py", ROOT / "src/dengue/validacion_modelo.py",
                   ROOT / "src/dengue/seguimiento.py", Path(__file__), ROOT / "requirements.txt"]:
        adjuntar(source, "codigo_importacion")
    adjuntar(preparado["salida"] / "data/raw/manifiesto_fuentes.json", "trazabilidad")
    adjuntar(preparado["salida"] / "reports/resumen_eda.json", "eda")
    for name in ["auditoria_limpieza.csv", "resumen_anual.csv", "fechas_por_archivo.csv"]:
        adjuntar(preparado["tablas"] / name, "eda")
    # Las figuras de evaluación se generan por método: no reutilizar una matriz de otro umbral.
    figura_confusion(metricas, temp / "matrices_confusion.png", cfg["nombre_municipio"], metodo)
    adjuntar(temp / "matrices_confusion.png", "figuras")
    for name in ["01_serie_semanal.png", "02_estacionalidad_anual.png", "03_retrasos.png"]:
        adjuntar(preparado["salida"] / "reports/figures" / name, "figuras")
    result = registrar_ejecucion(tracking_uri=tracking_uri, experimento=experimento,
        nombre=f"{ciudad}__{metodo}__{cfg['version_experimento']}", parametros=params,
        etiquetas=tags, tabla_metricas=metricas, archivos=archivos,
        modelo=preparado["modelo"] if logistica else None,
        ejemplo=preparado["panel"].loc[preparado["panel"].elegible_modelo, FEATURES].head(5))
    if logistica:
        import mlflow.sklearn
        recuperado = mlflow.sklearn.load_model(result["modelo_uri"])
        x = preparado["panel"].loc[preparado["panel"].elegible_modelo, FEATURES]
        np.testing.assert_allclose(recuperado.predict_proba(x),
                                   preparado["modelo"].predict_proba(x), atol=1e-12, rtol=0)
    return {"ciudad": ciudad, "metodo": metodo, **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ciudades", nargs="+", choices=list(CIUDADES), default=list(CIUDADES))
    parser.add_argument("--tracking-uri", default=os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
    parser.add_argument("--experimento", default="dengue_exceso_semanal")
    parser.add_argument("--solo-verificar", action="store_true", help="Verificar fuentes locales sin escribir en MLflow")
    args = parser.parse_args()
    if len(args.ciudades) != len(set(args.ciudades)):
        parser.error("No repetir ciudades.")
    # Primero se comprueban todas las ciudades. Una inconsistencia impide iniciar la importación.
    preparados = [preparar_ciudad(city) for city in args.ciudades]
    print(json.dumps({"ciudades_verificadas": args.ciudades, "metodos_por_ciudad": len(METODOS)}), flush=True)
    if args.solo_verificar:
        return
    with tempfile.TemporaryDirectory() as dest:
        results = [importar(p, m, args.tracking_uri, args.experimento, dest)
                   for p in preparados for m in METODOS]
    print(json.dumps({"experimento": args.experimento, "ejecuciones": results}, indent=2), flush=True)


if __name__ == "__main__":
    main()
