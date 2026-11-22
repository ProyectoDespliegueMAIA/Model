"""Inferencia a una semana con antecedentes cargados y el modelo municipal."""
from io import BytesIO
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from openpyxl import load_workbook, Workbook

from dengue.plantillas import informacion, inicio_anio


def predecir(contenido, ciudad, fecha):
    meta_semana = informacion(fecha)
    root = Path(os.environ.get("DENGUE_API_DATA_DIR", Path(__file__).resolve().parents[2] / "data/api_dengue")) / ciudad
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    modelo = joblib.load(root / "logistica.joblib")
    historico = pd.read_csv(root / "historico.csv", parse_dates=["inicio_semana"])
    libro = load_workbook(BytesIO(contenido), read_only=True, data_only=False)
    try:
        filas = list(libro["Datos"].values)
    finally:
        libro.close()
    nuevos = pd.DataFrame(filas[1:], columns=filas[0])
    nuevos = nuevos.rename(columns={"notificaciones": "casos"})
    nuevos["inicio_semana"] = pd.to_datetime(nuevos.inicio_semana)
    clim = ["precipitacion_mm", "temperatura_C", "humedad_relativa"]
    for col in ["casos", "anio_epi", "semana_epi"] + clim:
        nuevos[col] = pd.to_numeric(nuevos[col], errors="raise")
    columnas = ["inicio_semana", "anio_epi", "semana_epi", "casos"] + clim
    todos = pd.concat([historico[columnas], nuevos[columnas]], ignore_index=True).sort_values("inicio_semana")
    t = pd.Timestamp(meta_semana["inicio"])
    antecedentes = todos.set_index("inicio_semana")
    features = {}
    usados = set()
    clima_usado = set()
    for lag in (1,2,3,4,8,12):
        dia = t-pd.Timedelta(weeks=lag)
        features[f"lag_{lag}"] = antecedentes.casos.get(dia, np.nan)
        usados.add(dia)
    recientes = antecedentes.casos.reindex(pd.date_range(t-pd.Timedelta(weeks=4), periods=4, freq="7D"))
    features["media_4"] = recientes.mean() if recientes.notna().all() else np.nan
    features["std_4"] = recientes.std() if recientes.notna().all() else np.nan
    anio = meta_semana["anio_epi"]
    n_semanas = (inicio_anio(anio+1)-inicio_anio(anio)).days//7
    fase = 2*np.pi*(meta_semana["semana_epi"]-1)/n_semanas
    features["semana_sin"], features["semana_cos"] = np.sin(fase), np.cos(fase)
    for nombre in metadata["predictores"]:
        for col in clim:
            if nombre == f"{col}_lag1":
                dia = t-pd.Timedelta(weeks=1)
                features[nombre] = antecedentes[col].get(dia, np.nan)
                usados.add(dia)
                clima_usado.add(dia)
            elif nombre.startswith(f"{col}_prev4"):
                lag = int(nombre[-1]) if "_lag" in nombre else 1
                fechas = pd.date_range(t-pd.Timedelta(weeks=lag+3), periods=4, freq="7D")
                valores = antecedentes[col].reindex(fechas)
                features[nombre] = ((valores.sum() if col=="precipitacion_mm" else valores.mean())
                                    if valores.notna().all() else np.nan)
                usados.update(fechas)
                clima_usado.update(fechas)
    faltantes = [k for k in metadata["predictores"] if not np.isfinite(features[k])]
    if faltantes:
        raise ValueError("Faltan antecedentes históricos para calcular: " + ", ".join(faltantes))
    prob = float(modelo.predict_proba(pd.DataFrame([features])[metadata["predictores"]])[0,1])
    historia = todos.loc[todos.anio_epi.between(anio-5, anio-1) &
                         todos.semana_epi.eq(meta_semana["semana_epi"]), ["anio_epi","casos"]].dropna()
    p75 = float(historia.casos.quantile(.75)) if len(historia)==5 else None
    return dict(ciudad=ciudad, nombre=metadata["nombre"], semana_objetivo=meta_semana,
        probabilidad_exceso=prob, umbral_probabilidad=metadata["umbral"], alerta=prob>metadata["umbral"],
        p75_casos=p75, anios_referencia=historia.anio_epi.astype(int).tolist(),
        aviso_p75=None if p75 is not None else "No hay cinco antecedentes anuales válidos para calcular el P75.",
        modelo=metadata["modelo"], entrenamiento_hasta=2021, operador_umbral=">",
        sha256_archivo=hashlib.sha256(contenido).hexdigest(),
        predictores={k:float(features[k]) for k in metadata["predictores"]},
        semanas_antecedentes=[d.date().isoformat() for d in sorted(usados)],
        notificaciones_recientes=[
            {"inicio_semana": dia.date().isoformat(),
             "clima_utilizado": dia in clima_usado,
             **{col: float(antecedentes[col].get(dia)) if pd.notna(antecedentes[col].get(dia)) else None for col in clim},
             "notificaciones": float(antecedentes.casos.get(dia))
                 if pd.notna(antecedentes.casos.get(dia)) else None}
            for dia in pd.date_range(t-pd.Timedelta(weeks=12), periods=12, freq="7D")])


def excel_resultado(resultado):
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Prediccion"
    filas = [
        ["Campo","Resultado"], ["Municipio",resultado["nombre"]],
        ["Inicio semana objetivo",str(resultado["semana_objetivo"]["inicio"])],
        ["Fin semana objetivo",str(resultado["semana_objetivo"]["fin"])],
        ["Probabilidad de exceso",resultado["probabilidad_exceso"]],
        ["Umbral municipal",resultado["umbral_probabilidad"]],
        ["Alerta","Sí" if resultado["alerta"] else "No"],
        ["P75 de casos",resultado["p75_casos"]],
        ["Aviso P75",resultado["aviso_p75"] or ""],
        ["Modelo",resultado["modelo"]], ["Entrenamiento hasta",2021],
        ["SHA256 del archivo",resultado["sha256_archivo"]],
    ]
    for fila in filas:
        hoja.append(fila)
    hoja["B5"].number_format=hoja["B6"].number_format="0.00%"
    hoja.column_dimensions["A"].width=30
    hoja.column_dimensions["B"].width=80
    variables=libro.create_sheet("Predictores")
    variables.append(["Variable","Valor"])
    for k,v in resultado["predictores"].items():
        variables.append([k,v])
    variables.column_dimensions["A"].width=38
    semanas=libro.create_sheet("Antecedentes")
    semanas.append(["Inicio semana utilizada"])
    for dia in resultado["semanas_antecedentes"]:
        semanas.append([dia])
    semanas.column_dimensions["A"].width=28
    salida=BytesIO()
    libro.save(salida)
    return salida.getvalue()
