"""Benchmark retrospectivo de alerta semanal con clima por municipio."""
import argparse
import hashlib
import itertools
import json
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dengue.pipeline import FEATURES, config, raiz_salida, guardar_json

CIUDADES = {"cali": "Cali", "ibague": "Ibague", "villavicencio": "Villavicencio"}
CLIMA = ["precipitacion_mm", "temperatura_C", "humedad_relativa"]
ANIOS_BUSQUEDA = range(2017, 2022)


def preparar_panel(slug, directorio):
    cfg = config("piloto" if slug == "cali" else slug)
    ruta_panel = raiz_salida(cfg) / "data/processed" / f"{slug}_panel_semanal.csv"
    ruta_clima = directorio / f"clima_diario_{CIUDADES[slug]}.csv"
    panel = pd.read_csv(ruta_panel, parse_dates=["inicio_semana", "fin_semana"])
    diario = pd.read_csv(ruta_clima, parse_dates=["fecha"]).sort_values("fecha")
    if (diario.empty or diario.fecha.isna().any() or diario.fecha.duplicated().any()
            or not diario.municipio.eq(CIUDADES[slug]).all()
            or not np.isfinite(diario[CLIMA].to_numpy()).all()
            or diario.precipitacion_mm.lt(0).any()
            or not diario.humedad_relativa.between(0, 100).all()):
        raise ValueError(f"Revisar integridad del clima de {slug}")
    diario["inicio_semana"] = diario.fecha - pd.to_timedelta((diario.fecha.dt.dayofweek + 1) % 7, unit="D")
    semanal = diario.groupby("inicio_semana").agg(
        precipitacion_mm=("precipitacion_mm", "sum"),
        temperatura_C=("temperatura_C", "mean"),
        humedad_relativa=("humedad_relativa", "mean"), dias=("fecha", "size"))
    panel = panel.sort_values("inicio_semana").merge(semanal, how="left", on="inicio_semana", validate="one_to_one")
    if not panel.inicio_semana.diff().dropna().eq(pd.Timedelta(days=7)).all():
        raise ValueError(f"Calendario discontinuo en {slug}")
    clima_valido = panel[CLIMA].where(panel.dias.eq(7), axis=0)
    for col in CLIMA:
        previo = clima_valido[col].shift(1)
        panel[f"{col}_lag1"] = previo
        ventana = previo.rolling(4, min_periods=4)
        panel[f"{col}_prev4"] = ventana.sum() if col == "precipitacion_mm" else ventana.mean()
    comunes = panel.loc[panel.elegible_modelo].dropna(subset=columnas("lag1_prev4")).copy()
    auditoria = {
        "municipio": cfg["municipio"], "dias_clima": len(diario),
        "inicio_clima": diario.fecha.min().date(), "fin_clima": diario.fecha.max().date(),
        "semanas_clima_completas": int(semanal.dias.eq(7).sum()),
        "elegibles_epidemiologia": int(panel.elegible_modelo.sum()), "elegibles_comunes": len(comunes),
        "sha256_panel": hashlib.sha256(ruta_panel.read_bytes()).hexdigest(),
        "sha256_clima": hashlib.sha256(ruta_clima.read_bytes()).hexdigest(),
    }
    return comunes, auditoria


def columnas(variante):
    return FEATURES + [f"{c}_lag1" for c in CLIMA] + (
        [f"{c}_prev4" for c in CLIMA] if variante == "lag1_prev4" else [])


def crear_modelo(tipo, valor, ajuste, semilla=42):
    if tipo == "logistica":
        estimador = LogisticRegression(C=valor, class_weight="balanced" if ajuste else None,
                                       max_iter=2000, random_state=semilla)
    else:
        estimador = MLPClassifier(hidden_layer_sizes=(ajuste,), alpha=valor, max_iter=1200,
                                  solver="lbfgs", early_stopping=False, random_state=semilla)
    return make_pipeline(StandardScaler(), estimador)


def ajustar(tipo, valor, ajuste, train, x, semilla=42):
    modelo = crear_modelo(tipo, valor, ajuste, semilla)
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always", ConvergenceWarning)
        modelo.fit(train[x], train.exceso.astype(int))
    return modelo, any(issubclass(a.category, ConvergenceWarning) for a in avisos)


def buscar(tipo, d):
    cortes = [(anio, d[d.anio_epi < anio], d[d.anio_epi == anio]) for anio in ANIOS_BUSQUEDA]
    if any(a.exceso.nunique() != 2 or b.empty for _, a, b in cortes):
        raise ValueError("Cada corte de búsqueda requiere ambas clases")
    resultados = []

    def probar(etapa, valor, ajuste, variante):
        x = columnas(variante)
        puntajes, avisos = {}, 0
        observados, probabilidades = [], []
        for anio, train, val in cortes:
            modelo, aviso = ajustar(tipo, valor, ajuste, train, x)
            prob = modelo.predict_proba(val[x])[:, 1]
            puntajes[str(anio)] = (average_precision_score(val.exceso, prob)
                                   if val.exceso.nunique() == 2 else None)
            observados.extend(val.exceso)
            probabilidades.extend(prob)
            avisos += aviso
        resultados.append(dict(etapa=etapa, valor=valor, ajuste=ajuste, variante=variante,
                               ap=average_precision_score(observados, probabilidades), avisos=avisos, ap_por_anio=puntajes))

    valores, ajustes = ([.01, .1, 1, 10], [False, True]) if tipo == "logistica" else ([.001, .01, .1, 1], [8, 16])
    for valor, ajuste, variante in itertools.product(valores, ajustes, ["lag1", "lag1_prev4"]):
        probar("inicial", valor, ajuste, variante)

    def elegir():
        convergentes = [fila for fila in resultados if fila["avisos"] == 0]
        if not convergentes:
            raise RuntimeError(f"Ninguna configuracion convergio en todos los cortes: {tipo}")
        return max(convergentes, key=lambda f: f["ap"])

    inicial = elegir()
    for factor in [1 / np.sqrt(10), np.sqrt(10)]:
        probar("fina", inicial["valor"] * factor, inicial["ajuste"], inicial["variante"])
    return elegir(), resultados


def medidas(y, pred, prob=None):
    tn, fp, fn, tp = map(int, confusion_matrix(y, pred, labels=[0, 1]).ravel())
    positivos, alertas = tp + fn, tp + fp
    return dict(n=len(y), positivos=positivos, alertas=alertas, tn=tn, fp=fp, fn=fn, tp=tp,
                precision=tp/alertas if alertas else None, sensibilidad=tp/positivos if positivos else None,
                f1=2*tp/(2*tp+fp+fn) if positivos else None,
                f2=5*tp/(5*tp+fp+4*fn) if positivos else None,
                ap=average_precision_score(y, prob) if prob is not None and y.nunique() == 2 else None,
                roc_auc=roc_auc_score(y, prob) if prob is not None and y.nunique() == 2 else None)


def ejecutar(slug, clima, salida):
    d, auditoria = preparar_panel(slug, clima)
    train = d[d.anio_epi <= 2021]
    bloques = {"umbral_2022_2023": d[d.anio_epi.between(2022, 2023)],
               "retrospectiva_2024": d[d.anio_epi == 2024],
               "retrospectiva_2025": d[d.anio_epi == 2025]}
    val = bloques["umbral_2022_2023"]
    if val.exceso.nunique() != 2 or any(b.empty for b in bloques.values()):
        raise ValueError(f"Bloques insuficientes para {slug}")
    salida = salida / slug
    salida.mkdir(parents=True, exist_ok=True)
    guardar_json(salida / "auditoria.json", auditoria)
    metricas, predicciones = [], []

    def registrar(tipo, bloque, filas, pred, prob=None, umbral=None):
        metricas.append(dict(modelo=tipo, bloque=bloque, umbral=umbral,
                             **medidas(filas.exceso, pred, prob)))
        predicciones.append(filas[["inicio_semana", "anio_epi", "semana_epi", "exceso", "umbral_casos"]]
                            .assign(modelo=tipo, bloque=bloque, prediccion=pred, probabilidad=prob))

    for bloque, filas in bloques.items():
        registrar("persistencia", bloque, filas, filas.lag_1.gt(filas.umbral_casos).astype(int))

    for tipo in ["logistica", "mlp"]:
        mejor, resultados = buscar(tipo, d)
        x = columnas(mejor["variante"])
        modelo, aviso = ajustar(tipo, mejor["valor"], mejor["ajuste"], train, x)
        if aviso:
            raise RuntimeError(f"El ajuste final de {slug}/{tipo} no convergio")
        prob_val = modelo.predict_proba(val[x])[:, 1]
        curva = [{"umbral": i / 100, **medidas(val.exceso, prob_val >= i / 100)}
                 for i in range(10, 91, 5)]
        umbral = max(curva, key=lambda f: (f["f2"], f["umbral"]))["umbral"]
        estabilidad = {}
        if tipo == "mlp":
            for semilla in [7, 13, 42]:
                alterno, aviso_semilla = ajustar(tipo, mejor["valor"], mejor["ajuste"], train, x, semilla)
                prob = alterno.predict_proba(val[x])[:, 1]
                estabilidad[str(semilla)] = {"ap": average_precision_score(val.exceso, prob),
                                              "aviso_convergencia": aviso_semilla}
        for bloque, filas in bloques.items():
            prob = modelo.predict_proba(filas[x])[:, 1]
            registrar(tipo, bloque, filas, (prob >= umbral).astype(int), prob, umbral)
        joblib.dump(modelo, salida / f"{tipo}.joblib")
        guardar_json(salida / f"{tipo}.json", dict(mejor=mejor, predictores=x, umbral=umbral,
                     busqueda=resultados, grilla_umbral=curva,
                     estabilidad_mlp=estabilidad, configuracion=modelo.steps[-1][1].get_params()))
    pd.concat(predicciones).to_csv(salida / "predicciones.csv", index=False)
    pd.DataFrame(metricas).to_csv(salida / "metricas.csv", index=False)
    print(f"{slug}: {len(d)} semanas, {len(train)} para ajuste final", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clima", type=Path, default=ROOT.parents[2] / "DatosClima")
    parser.add_argument("--salida", type=Path, default=ROOT / "reports/benchmark_clima")
    args = parser.parse_args()
    for ciudad in CIUDADES:
        ejecutar(ciudad, args.clima, args.salida)
