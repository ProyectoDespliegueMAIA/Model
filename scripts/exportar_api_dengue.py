"""Exporta el paquete de inferencia histórica de la logística con clima."""
import argparse
import json
import shutil
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

import benchmark_clima_ronda2 as ronda
import benchmark_clima as base

SALIDA = base.ROOT / "data/api_dengue"
COLUMNAS = ["anio_epi", "semana_epi", "inicio_semana", "fin_semana", "corte_prediccion",
            "casos", "umbral_casos", "exceso", "bloque"]


def exportar_evaluacion(origen, destino, historico, auditoria):
    metricas = pd.read_csv(origen / "metricas.csv", float_precision="round_trip")
    metricas = metricas.loc[metricas.modelo.isin(["persistencia", "logistica", "mlp"])]
    modelos = {}
    for nombre in ("logistica", "mlp"):
        info = json.loads((origen / f"{nombre}.json").read_text(encoding="utf-8"))
        modelos[nombre] = {k: info[k] for k in (
            "mejor", "predictores", "umbral", "operador_umbral", "busqueda", "estabilidad_mlp")}
    base.guardar_json(destino / "evaluacion.json", {
        "ronda": 2, "horizonte_semanas": 1, "percentil_etiqueta": 75,
        "busqueda_anios": list(base.ANIOS_BUSQUEDA), "ajuste_final_hasta": 2021,
        "calibracion_umbral": [2022, 2023], "evaluacion_retrospectiva": [2024, 2025],
        "modelos": modelos, "metricas": json.loads(metricas.to_json(orient="records", double_precision=15)),
    })
    anuales = []
    for anio, grupo in historico.groupby("anio_epi"):
        conteos = grupo.casos.dropna()
        etiquetas = grupo.exceso.dropna()
        anuales.append({
            "anio_epi": int(anio), "semanas": len(grupo), "semanas_con_conteo": len(conteos),
            "semanas_con_etiqueta": len(etiquetas),
            "notificaciones": int(conteos.sum()) if len(conteos) else None,
            "semanas_con_exceso": int(etiquetas.sum()) if len(etiquetas) else None,
        })
    base.guardar_json(destino / "estadisticas.json", {
        "fuente_notificaciones": "SIVIGILA, evento 210, agrupación por inicio de síntomas",
        "fuente_clima": "JavaScript en Google Earth Engine; CHIRPS diario y ERA5-Land diario, media espacial municipal",
        "variables_climaticas": ["Precipitación (mm)", "Temperatura (°C)", "Humedad relativa (%)"],
        "dias_clima": auditoria["dias_clima"], "inicio_clima": auditoria["inicio_clima"],
        "fin_clima": auditoria["fin_clima"], "semanas_clima_completas": auditoria["semanas_clima_completas"],
        "semanas_elegibles": auditoria["elegibles_comunes"], "anuales": anuales,
    })


def exportar(clima, salida):
    for slug in base.CIUDADES:
        panel, auditoria = ronda.panel_ronda2(slug, clima)
        origen = ronda.SALIDA / slug
        evidencia = json.loads((origen / "auditoria.json").read_text(encoding="utf-8"))
        for llave in ("sha256_panel", "sha256_clima"):
            if auditoria[llave] != evidencia[llave]:
                raise ValueError(f"El insumo {llave} de {slug} cambió desde el benchmark")
        meta = json.loads((origen / "logistica.json").read_text(encoding="utf-8"))
        if meta["operador_umbral"] != ">":
            raise ValueError(f"Operador inesperado para {slug}")
        referencia = pd.read_csv(origen / "predicciones.csv", parse_dates=["inicio_semana"],
                                 float_precision="round_trip")
        referencia = referencia.loc[referencia.modelo.eq("logistica")]
        filas = referencia.merge(panel, on=["inicio_semana", "anio_epi", "semana_epi", "exceso", "umbral_casos"],
                                 validate="one_to_one")
        if len(filas) != len(referencia) or filas.empty:
            raise ValueError(f"No coinciden las semanas de {slug}")
        modelo = joblib.load(origen / "logistica.joblib")
        for _, bloque in filas.groupby("bloque", sort=False):
            prob = modelo.predict_proba(bloque[meta["predictores"]])[:, 1]
            np.testing.assert_allclose(prob, bloque.probabilidad, rtol=0, atol=1e-12)
            np.testing.assert_array_equal(prob > meta["umbral"], bloque.prediccion)
        destino = salida / slug
        destino.mkdir(parents=True, exist_ok=True)
        filas[COLUMNAS + meta["predictores"]].to_csv(destino / "semanas.csv", index=False)
        cfg = base.config("piloto" if slug == "cali" else slug)
        ruta_panel = base.raiz_salida(cfg) / "data/processed" / f"{slug}_panel_semanal.csv"
        historico = pd.read_csv(ruta_panel, usecols=COLUMNAS[:-1], float_precision="round_trip")
        diario = pd.read_csv(clima / f"clima_diario_{base.CIUDADES[slug]}.csv", parse_dates=["fecha"])
        diario["inicio_semana"] = diario.fecha - pd.to_timedelta((diario.fecha.dt.dayofweek + 1) % 7, unit="D")
        semanal = diario.groupby("inicio_semana").agg(
            precipitacion_mm=("precipitacion_mm", "sum"), temperatura_C=("temperatura_C", "mean"),
            humedad_relativa=("humedad_relativa", "mean"), dias_clima=("fecha", "size"))
        semanal.loc[semanal.dias_clima.ne(7), base.CLIMA] = np.nan
        historico["inicio_semana"] = pd.to_datetime(historico.inicio_semana)
        historico = historico.merge(semanal, on="inicio_semana", how="left", validate="one_to_one")
        historico.sort_values("inicio_semana").to_csv(destino / "historico.csv", index=False)
        exportar_evaluacion(origen, destino, historico, auditoria)
        shutil.copyfile(origen / "logistica.joblib", destino / "logistica.joblib")
        base.guardar_json(destino / "metadata.json", dict(
            ciudad=slug, nombre={"cali": "Cali", "ibague": "Ibagué", "villavicencio": "Villavicencio"}[slug],
            codigo_dane=auditoria["municipio"], modelo="logistica_clima_ronda2",
            umbral=meta["umbral"], operador_umbral=meta["operador_umbral"],
            predictores=meta["predictores"], ventana_clima=meta["mejor"]["variante"],
            sha256_panel=auditoria["sha256_panel"], sha256_clima=auditoria["sha256_clima"]))
        print(f"{slug}: {len(filas)} semanas exportadas")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clima", type=Path, default=base.ROOT.parents[2] / "DatosClima")
    parser.add_argument("--salida", type=Path, default=SALIDA)
    args = parser.parse_args()
    exportar(args.clima, args.salida)
