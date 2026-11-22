"""Registra los resultados del benchmark en MLflow sin volver a entrenar."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import mlflow
from mlflow import MlflowClient

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTO = "dengue_benchmark_clima"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ronda", choices=(1, 2), type=int, default=1)
    ronda = parser.parse_args().ronda
    sufijo = "_ronda2" if ronda == 2 else ""
    experimento = mlflow.set_experiment(EXPERIMENTO + sufijo)
    cliente = MlflowClient()
    codigo = ROOT / "scripts/benchmark_clima.py"
    for ciudad in ("cali", "ibague", "villavicencio"):
        ruta = ROOT / "reports" / ("benchmark_clima" + sufijo) / ciudad
        with (ruta / "metricas.csv").open(encoding="utf-8", newline="") as archivo:
            filas = list(csv.DictReader(archivo))
        for metodo in dict.fromkeys(fila["modelo"] for fila in filas):
            propias = [fila for fila in filas if fila["modelo"] == metodo]
            artefactos = [ruta / "auditoria.json", codigo]
            params = {"horizonte_semanas": 1, "percentil_etiqueta": 75}
            if ronda == 2:
                artefactos.append(ROOT / "scripts/benchmark_clima_ronda2.py")
                params["presupuesto_fp"] = json.loads((ruta / "auditoria.json").read_text(
                    encoding="utf-8"))["presupuesto_fp"]
            if metodo != "persistencia":
                configuracion = ruta / f"{metodo}.json"
                metadata = json.loads(configuracion.read_text(encoding="utf-8"))
                params.update(metadata["configuracion"])
                params.update(variante=metadata["mejor"]["variante"], umbral=metadata["umbral"])
                if ronda == 2:
                    params.update(operador_umbral=metadata["operador_umbral"], origen=metadata["origen"])
                artefactos.extend([configuracion, ruta / f"{metodo}.joblib"])
            else:
                params["regla"] = "lag_1 > umbral_casos"
            huella = hashlib.sha256(json.dumps(propias, sort_keys=True).encode())
            with (ruta / "predicciones.csv").open(encoding="utf-8", newline="") as archivo:
                predicciones = [fila for fila in csv.DictReader(archivo) if fila["modelo"] == metodo]
            huella.update(json.dumps(predicciones, sort_keys=True).encode())
            for archivo in artefactos:
                huella.update(hashlib.sha256(archivo.read_bytes()).digest())
            clave = huella.hexdigest()
            previos = cliente.search_runs([experimento.experiment_id],
                filter_string=f"tags.huella = '{clave}' AND attributes.status = 'FINISHED'")
            if previos:
                print(ciudad, metodo, previos[0].info.run_id, "reutilizado")
                continue
            with mlflow.start_run(run_name=f"{ciudad}_{metodo}_benchmark{sufijo}", tags={
                "ciudad": ciudad, "modelo": metodo, "huella": clave, "evaluacion": "retrospectiva", "ronda": str(ronda)
            }) as run:
                mlflow.log_params(params)
                mlflow.log_metrics({f"{fila['bloque']}.{k}": float(v) for fila in propias
                                    for k, v in fila.items() if k not in ("modelo", "bloque") and v})
                mlflow.log_dict(propias, "metricas.json")
                mlflow.log_dict(predicciones, "predicciones.json")
                for archivo in artefactos:
                    mlflow.log_artifact(str(archivo))
            print(ciudad, metodo, run.info.run_id)


if __name__ == "__main__":
    main()
