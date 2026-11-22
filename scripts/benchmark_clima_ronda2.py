"""Segunda ronda del benchmark climático y ajuste del presupuesto de falsas alertas."""
import argparse
import itertools
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

import benchmark_clima as base

SALIDA = base.ROOT / "reports/benchmark_clima_ronda2"
ANTERIOR = base.ROOT / "reports/benchmark_clima"


def panel_ronda2(slug, clima):
    panel, auditoria = base.preparar_panel(slug, clima)
    diario = pd.read_csv(clima / f"clima_diario_{base.CIUDADES[slug]}.csv", parse_dates=["fecha"])
    fechas = diario.fecha
    diario["domingo"] = fechas - pd.to_timedelta((fechas.dt.dayofweek + 1) % 7, unit="D")
    semanal = diario.groupby("domingo").agg(
        precipitacion_mm=("precipitacion_mm", "sum"),
        temperatura_C=("temperatura_C", "mean"),
        humedad_relativa=("humedad_relativa", "mean"), dias=("fecha", "size"))
    semanal = semanal.reindex(pd.date_range(semanal.index.min(), semanal.index.max(), freq="7D"))
    completos = semanal[base.CLIMA].where(semanal.dias.eq(7), axis=0)
    for retraso in (2, 3):
        for col in base.CLIMA:
            ventana = completos[col].shift(retraso).rolling(4, min_periods=4)
            resumen = ventana.sum() if col == "precipitacion_mm" else ventana.mean()
            panel[f"{col}_prev4_lag{retraso}"] = panel.inicio_semana.map(resumen)
    if panel[columnas("prev4_lag2") + columnas("prev4_lag3")].isna().any().any():
        raise ValueError(f"Las ventanas retrasadas no cubren la cohorte común de {slug}")
    return panel, auditoria


def columnas(variante):
    if variante.startswith("prev4_lag"):
        return base.FEATURES + [f"{c}_{variante}" for c in base.CLIMA]
    return base.columnas(variante)


def elegir_umbral(y, prob, limite_fp):
    """Maximiza TP sujeto al límite de FP; desempata por menos FP y mayor umbral."""
    opciones = []
    for umbral in np.unique(np.r_[0.0, prob, 1.0]):
        pred = prob > umbral
        fp = int(np.sum(pred & (y == 0)))
        tp = int(np.sum(pred & (y == 1)))
        if fp <= limite_fp:
            opciones.append((tp, -fp, float(umbral)))
    return max(opciones)[2]


def buscar(slug, tipo, panel, anterior):
    semanas = ["lag1", "lag1_prev4", "prev4_lag2", "prev4_lag3"]
    valor = anterior["valor"]
    valores = {valor, valor / np.sqrt(10), valor * np.sqrt(10)}
    if (slug, tipo) == ("cali", "logistica") or (slug != "cali" and tipo == "mlp"):
        valores.add(valor * 10)
    ajustes = [False, True] if tipo == "logistica" else [8, 16]
    cortes = [(anio, panel[panel.anio_epi < anio], panel[panel.anio_epi == anio])
              for anio in base.ANIOS_BUSQUEDA]
    y = np.concatenate([val.exceso.to_numpy() for _, _, val in cortes])
    resultados = []
    for regularizacion, ajuste, variante in itertools.product(sorted(valores), ajustes, semanas):
        x = columnas(variante)
        probs, avisos = [], 0
        for _, train, val in cortes:
            modelo, aviso = base.ajustar(tipo, regularizacion, ajuste, train, x)
            probs.extend(modelo.predict_proba(val[x])[:, 1])
            avisos += aviso
        resultados.append(dict(valor=float(regularizacion), ajuste=ajuste, variante=variante,
                               ap=average_precision_score(y, probs), avisos=avisos))
    candidatos = sorted((r for r in resultados if not r["avisos"]), key=lambda r: -r["ap"])
    if not candidatos:
        raise RuntimeError(f"Sin candidata convergente: {slug}/{tipo}")
    # La semilla de producción se fija antes de buscar. Las otras auditan estabilidad.
    return candidatos[0], resultados


def ejecutar(slug, clima, destino):
    panel, auditoria = panel_ronda2(slug, clima)
    train = panel[panel.anio_epi <= 2021]
    bloques = {"umbral_2022_2023": panel[panel.anio_epi.between(2022, 2023)],
               "retrospectiva_2024": panel[panel.anio_epi == 2024],
               "retrospectiva_2025": panel[panel.anio_epi == 2025]}
    val = bloques["umbral_2022_2023"]
    limite_fp = int((val.lag_1.gt(val.umbral_casos) & val.exceso.eq(0)).sum())
    destino = destino / slug
    destino.mkdir(parents=True, exist_ok=True)
    base.guardar_json(destino / "auditoria.json", dict(auditoria, presupuesto_fp=limite_fp))
    metricas, predicciones = [], []

    def registrar(nombre, bloque, filas, pred, prob=None, umbral=None):
        metricas.append(dict(modelo=nombre, bloque=bloque, umbral=umbral,
                             **base.medidas(filas.exceso, pred, prob)))
        predicciones.append(filas[["inicio_semana", "anio_epi", "semana_epi", "exceso", "umbral_casos"]]
                            .assign(modelo=nombre, bloque=bloque, prediccion=pred, probabilidad=prob))

    for bloque, filas in bloques.items():
        registrar("persistencia", bloque, filas, filas.lag_1.gt(filas.umbral_casos).astype(int))

    for tipo in ("logistica", "mlp"):
        ruta = ANTERIOR / slug
        origen = json.loads((ruta / f"{tipo}.json").read_text(encoding="utf-8"))
        modelo_original = joblib.load(ruta / f"{tipo}.joblib")
        mejor, busqueda = buscar(slug, tipo, panel, origen["mejor"])
        x = columnas(mejor["variante"])
        modelo, aviso = base.ajustar(tipo, mejor["valor"], mejor["ajuste"], train, x)
        if aviso:
            raise RuntimeError(f"El ajuste final no convergió: {slug}/{tipo}")
        estabilidad = {}
        if tipo == "mlp":
            for semilla in (7, 13, 42):
                alterno, aviso = base.ajustar(tipo, mejor["valor"], mejor["ajuste"], train, x, semilla)
                prob = alterno.predict_proba(val[x])[:, 1]
                estabilidad[str(semilla)] = {"ap": average_precision_score(val.exceso, prob),
                                             "aviso_convergencia": aviso}
        for nombre, estimador, features, seleccion, ronda in [
            (f"{tipo}_solo_umbral", modelo_original, origen["predictores"], origen["mejor"], "modelo_ronda1"),
            (tipo, modelo, x, mejor, "modelo_ronda2"),
        ]:
            prob = estimador.predict_proba(val[features])[:, 1]
            umbral = elegir_umbral(val.exceso.to_numpy(), prob, limite_fp)
            for bloque, filas in bloques.items():
                prob = estimador.predict_proba(filas[features])[:, 1]
                registrar(nombre, bloque, filas, (prob > umbral).astype(int), prob, umbral)
            joblib.dump(estimador, destino / f"{nombre}.joblib")
            base.guardar_json(destino / f"{nombre}.json", dict(
                origen=ronda, mejor=seleccion, predictores=features, umbral=umbral,
                operador_umbral=">", presupuesto_fp=limite_fp,
                busqueda=busqueda if ronda == "modelo_ronda2" else [],
                estabilidad_mlp=estabilidad if ronda == "modelo_ronda2" else {},
                configuracion=estimador.steps[-1][1].get_params()))
    pd.concat(predicciones).to_csv(destino / "predicciones.csv", index=False)
    pd.DataFrame(metricas).to_csv(destino / "metricas.csv", index=False)
    print(f"{slug}: {len(panel)} semanas; tope de {limite_fp} falsas alertas en calibración", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clima", type=Path, default=base.ROOT.parents[2] / "DatosClima")
    parser.add_argument("--salida", type=Path, default=SALIDA)
    args = parser.parse_args()
    for slug in base.CIUDADES:
        ejecutar(slug, args.clima, args.salida)
