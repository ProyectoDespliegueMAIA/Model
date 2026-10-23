"""Preparación y evaluación retrospectiva; no implementa vigilancia en tiempo real."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FEATURES = ["lag_1", "lag_2", "lag_3", "lag_4", "lag_8", "lag_12",
            "media_4", "std_4", "semana_sin", "semana_cos"]

def config(ciudad="piloto"):
    return json.loads((ROOT / f"configs/{ciudad}.json").read_text(encoding="utf-8"))

def raiz_salida(cfg):
    return ROOT / cfg.get("directorio_salida", ".")

def guardar_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str, allow_nan=False), encoding="utf-8")

def parsear_fecha(values):
    """Día/mes/año explícito: evita confundir 03/07 con 07/03."""
    text = values.astype("string").str.strip()
    result = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    dmy = text.str.extract(r"^(\d{1,2}/\d{1,2}/\d{4})", expand=False)
    result.loc[dmy.notna()] = pd.to_datetime(dmy.dropna(), format="%d/%m/%Y", errors="coerce")
    iso = text.str.extract(r"^(\d{4}-\d{2}-\d{2})", expand=False)
    result.loc[iso.notna()] = pd.to_datetime(iso.dropna(), format="%Y-%m-%d", errors="coerce")
    numeric = pd.to_numeric(text, errors="coerce")
    serial = numeric.between(20000, 60000) & result.isna()
    result.loc[serial] = pd.to_datetime(numeric[serial], unit="D", origin="1899-12-30").dt.floor("D")
    return result

def inicio_anio_epi(year):
    """Domingo de la semana que contiene el 4 de enero (mínimo 4 días del año)."""
    d = pd.Timestamp(year=int(year), month=1, day=4)
    return d - pd.Timedelta(days=(d.dayofweek + 1) % 7)

def calendario(inicial=2007, final=2025):
    rows = []
    for year in range(inicial, final + 1):
        starts = pd.date_range(inicio_anio_epi(year), inicio_anio_epi(year + 1), freq="7D", inclusive="left")
        for week, start in enumerate(starts, 1):
            rows.append({"anio_epi": year, "semana_epi": week,
                         "inicio_semana": start, "fin_semana": start + pd.Timedelta(days=6),
                         "semanas_en_anio": len(starts)})
    return pd.DataFrame(rows)

def preparar_microdatos(raw, cfg):
    """Aplica exclusiones registradas. Nunca recorta retrasos ni interpola fechas."""
    m = raw.copy()
    steps = [{"etapa": "extraidos_municipio", "filas_restantes": len(m), "excluidos": 0}]
    def keep(mask, etapa):
        nonlocal m
        before = len(m)
        m = m.loc[mask].copy()
        steps.append({"etapa": etapa, "filas_restantes": len(m), "excluidos": before-len(m)})
    if "HUELLA_REGISTRO" not in m:
        raise ValueError("Regenerar extracción con huella de las 69 columnas originales.")
    keep(~m.HUELLA_REGISTRO.duplicated(), "sin_duplicados_exactos_originales")
    for c in ["COD_EVE", "COD_PAIS_O", "COD_DPTO_O", "COD_MUN_O", "Estado_final_de_caso", "confirmados"]:
        m[c] = pd.to_numeric(m[c], errors="coerce")
    codigo = str(cfg["municipio"]).zfill(5)
    keep((m.COD_EVE==210) & (m.COD_PAIS_O==170) &
         (m.COD_DPTO_O==int(codigo[:2])) & (m.COD_MUN_O==int(codigo[2:])),
         "evento_y_ubicacion_validos")
    keep(m.Estado_final_de_caso.isin(cfg["inclusion_estados"]), "estados_2_3_5")
    for c in ["INI_SIN", "FEC_NOT", "FEC_CON"]:
        m[c + "_fecha"] = parsear_fecha(m[c])
    if cfg["fecha_principal"] != "INI_SIN" or cfg["politica_fecha_faltante"] != "excluir_sin_sustituir":
        raise ValueError("Este pipeline usa exclusivamente INI_SIN válida, sin fecha alternativa.")
    m["fecha_analitica"] = m.INI_SIN_fecha
    m["fecha_sustituida"] = False
    m["retraso_notificacion_dias"] = (m.FEC_NOT_fecha - m.INI_SIN_fecha).dt.days
    m["flag_notificacion_anterior_sintomas"] = m.retraso_notificacion_dias.lt(0)
    m["flag_consulta_anterior_sintomas"] = m.INI_SIN_fecha.gt(m.FEC_CON_fecha)
    diagnostico = {
        "ini_sin_no_parseable": int(m.INI_SIN_fecha.isna().sum()),
        "fec_not_no_parseable": int(m.FEC_NOT_fecha.isna().sum()),
        "sintomas_posteriores_notificacion": int((m.retraso_notificacion_dias<0).sum()),
        "retrasos_mayores_180": int((m.retraso_notificacion_dias>180).sum()),
        "consecutive_repetidos_no_eliminados_por_id": int(m.CONSECUTIVE.duplicated().sum()),
        "fecha_principal": cfg["fecha_principal"],
        "porcentaje_inicio_valido": float(100*m.INI_SIN_fecha.notna().mean()),
        "fec_con_no_parseable": int(m.FEC_CON_fecha.isna().sum()),
        "sintomas_posteriores_consulta": int(m.flag_consulta_anterior_sintomas.sum()),
    }
    por_archivo = m.assign(
        cronologia_negativa=m.retraso_notificacion_dias.lt(0),
        demora_mayor_180=m.retraso_notificacion_dias.gt(180),
        sin_inicio=m.INI_SIN_fecha.isna()).groupby("ARCHIVO_ORIGEN").agg(
            registros=("ARCHIVO_ORIGEN","size"),
            cronologias_negativas=("cronologia_negativa","sum"),
            mayores_180=("demora_mayor_180","sum"),
            sin_inicio=("sin_inicio","sum"))
    por_archivo["pct_cronologia_negativa"]=100*por_archivo.cronologias_negativas/por_archivo.registros
    diagnostico["diagnostico_por_archivo"] = por_archivo.reset_index().to_dict("records")
    keep(m.fecha_analitica.notna(), "inicio_sintomas_valido_sin_sustitucion")
    m["inicio_semana"] = m.fecha_analitica - pd.to_timedelta((m.fecha_analitica.dt.dayofweek+1)%7, unit="D")
    cal = calendario(cfg["anio_inicial"], cfg["anio_final"])
    keep(m.inicio_semana.isin(cal.inicio_semana), "dentro_ventana_epidemiologica")
    m = m.merge(cal, on="inicio_semana", how="left", validate="many_to_one")
    m["confirmado"] = m.Estado_final_de_caso.isin([3,5]).astype(int)
    m["hospitalizado"] = (pd.to_numeric(m.PAC_HOS, errors="coerce")==1).astype(int)
    m["cod_municipio"] = cfg["municipio"]
    assert ((m.fecha_analitica>=m.inicio_semana) & (m.fecha_analitica<=m.fin_semana)).all()
    diagnostico["filas_finales"] = len(m)
    diagnostico["fechas_sustituidas_finales"] = int(m.fecha_sustituida.sum())
    diagnostico["anomalias_notificacion_conservadas"] = int(m.flag_notificacion_anterior_sintomas.sum())
    return m, pd.DataFrame(steps), diagnostico

def construir_panel(m, cfg):
    cal = calendario(cfg["anio_inicial"], cfg["anio_final"])
    diagnostic = m.assign(retraso_valido=m.retraso_notificacion_dias.where(m.retraso_notificacion_dias.ge(0)))
    agg = diagnostic.groupby("inicio_semana").agg(
        n_registros=("confirmado", "size"), casos_confirmados=("confirmado", "sum"),
        hospitalizados=("hospitalizado", "sum"),
        retraso_mediana=("retraso_valido", "median"),
        ultima_notificacion=("FEC_NOT_fecha", "max"))
    p = cal.merge(agg, on="inicio_semana", how="left", validate="one_to_one")
    p["semana_con_registros"] = p.n_registros.notna()
    p["n_registros"] = p.n_registros.fillna(0).astype(int)
    # Ausencia de filas no certifica cero casos: solo esta columna descriptiva vale cero.
    p["casos"] = p.n_registros.astype(float).where(p.semana_con_registros)
    p["cod_municipio"] = cfg["municipio"]
    assert p.n_registros.sum() == len(m)
    assert p.inicio_semana.diff().dropna().eq(pd.Timedelta(days=7)).all()
    return p

def agregar_canal(p, cfg):
    p = p.copy()
    thresholds, counts = [], []
    k = cfg["ventana_canal_anios"]
    for row in p.itertuples():
        history = p.loc[p.anio_epi.between(row.anio_epi-k, row.anio_epi-1) &
                        p.semana_epi.eq(row.semana_epi), "casos"].dropna()
        counts.append(len(history))
        thresholds.append(history.quantile(cfg["cuantil_canal"], interpolation="linear")
                          if len(history)>=cfg["min_anios_canal"] else np.nan)
    p["n_anios_canal"] = counts
    p["umbral_casos"] = thresholds
    p["exceso"] = (p.casos > p.umbral_casos).astype(float).where(p.casos.notna() & p.umbral_casos.notna())
    return p

def agregar_features(p):
    p = p.copy()
    for lag in [1,2,3,4,8,12]:
        p[f"lag_{lag}"] = p.casos.shift(lag)
    p["media_4"] = p.casos.shift(1).rolling(4, min_periods=4).mean()
    p["std_4"] = p.casos.shift(1).rolling(4, min_periods=4).std()
    phase = 2*np.pi*(p.semana_epi-1)/p.semanas_en_anio
    p["semana_sin"], p["semana_cos"] = np.sin(phase), np.cos(phase)
    p["corte_prediccion"] = p.inicio_semana-pd.Timedelta(days=1)
    p["elegible_modelo"] = p[FEATURES+["exceso"]].notna().all(axis=1)
    return p

def exportar_eda(raw, m, audit, quality, panel, cfg=None):
    cfg = config() if cfg is None else cfg
    ROOT = raiz_salida(cfg)
    ciudad = cfg.get("slug", "cali")
    if not panel.cod_municipio.astype(str).eq(str(cfg["municipio"])).all():
        raise ValueError("El panel no pertenece al municipio configurado.")
    dest = ROOT/"data/processed"
    dest.mkdir(parents=True, exist_ok=True)
    reports = ROOT/"reports/tables"
    reports.mkdir(parents=True, exist_ok=True)
    m.to_csv(dest/f"{ciudad}_microdatos_validados.csv", index=False)
    excluded = raw.loc[~raw.HUELLA_REGISTRO.isin(m.HUELLA_REGISTRO)].copy()
    excluded["motivo_fecha"] = np.where(parsear_fecha(excluded.INI_SIN).isna(),
        "inicio_sintomas_ausente_o_invalido", "fuera_ventana_u_otra_regla_ver_auditoria")
    excluded.to_csv(dest/"registros_excluidos.csv",index=False)
    panel.to_csv(dest/f"{ciudad}_panel_semanal.csv", index=False)
    audit.to_csv(reports/"auditoria_limpieza.csv", index=False)
    pd.DataFrame(quality["diagnostico_por_archivo"]).to_csv(reports/"fechas_por_archivo.csv",index=False)
    annual = panel.groupby("anio_epi").agg(
        semanas=("semana_epi","size"), con_registros=("semana_con_registros","sum"),
        notificaciones_incluidas=("n_registros","sum"), elegibles=("elegible_modelo","sum"))
    annual.to_csv(reports/"resumen_anual.csv")
    summary = {**quality, "filas_extraidas":len(raw), "semanas_panel":len(panel),
               "semanas_sin_registros_no_imputadas":int((~panel.semana_con_registros).sum()),
               "semanas_53":int((panel.semana_epi==53).sum()),
               "semanas_con_etiqueta":int(panel.exceso.notna().sum()),
               "semanas_elegibles_modelo":int(panel.elegible_modelo.sum()),
               "positivos_etiquetados":int(panel.exceso.sum()),
               "alcance":"evaluación retrospectiva; sin reconstrucción de versiones históricas del reporte"}
    guardar_json(ROOT/"reports/resumen_eda.json", summary)
    return annual, summary

def entrenar_logistica(panel, cfg):
    """Primera comparación: hiperparámetros fijos y umbral elegido solo en validación."""
    ROOT = raiz_salida(cfg)
    ciudad = cfg.get("slug", "cali")
    if not panel.cod_municipio.astype(str).eq(str(cfg["municipio"])).all():
        raise ValueError("No se pueden mezclar municipios en un modelo independiente.")
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (average_precision_score, roc_auc_score, brier_score_loss,
        precision_score, recall_score, f1_score, fbeta_score, confusion_matrix)
    import joblib
    d = panel.loc[panel.elegible_modelo].copy()
    train = d.loc[d.anio_epi<=cfg["fin_entrenamiento"]]
    val = d.loc[d.anio_epi.between(cfg["fin_entrenamiento"]+1, cfg["fin_validacion"])]
    test = d.loc[d.anio_epi==cfg["anio_prueba"]]
    extra = d.loc[d.anio_epi==cfg["anio_adicional"]]
    for name, block in [("entrenamiento",train),("validacion",val)]:
        if block.exceso.nunique()!=2:
            raise ValueError(f"{name}: se requieren ambas clases para esta evaluación.")
    if test.empty:
        raise ValueError("No hay filas elegibles en prueba: revisar cobertura y etiquetas.")
    assert train.fin_semana.max() < val.inicio_semana.min()
    assert val.fin_semana.max() < test.inicio_semana.min()
    model = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000,
                          solver="lbfgs", random_state=cfg["semilla"]))
    model.fit(train[FEATURES], train.exceso.astype(int))
    prob_val = model.predict_proba(val[FEATURES])[:,1]
    grid = np.arange(.10,.91,.05)
    scores = pd.DataFrame({"umbral":grid, "f2_validacion":[fbeta_score(val.exceso, prob_val>=t, beta=2, zero_division=0) for t in grid]})
    # Empates: escoger el umbral más alto para reducir carga de alertas.
    threshold = float(scores.sort_values(["f2_validacion","umbral"], ascending=False).iloc[0].umbral)
    prevalence = float(train.exceso.mean())
    metrics, predictions = [], []
    splits=[]
    for name, block in [("entrenamiento",train),("validacion",val),("prueba_2024",test),("adicional_2025",extra)]:
        splits.append({"bloque":name,"filas":len(block),"positivos":int(block.exceso.sum()),
                       "inicio":str(block.inicio_semana.min().date()),"fin":str(block.fin_semana.max().date())})
        if block.empty:
            continue
        y = block.exceso.astype(int)
        probs = {"logistica_umbral_validado":model.predict_proba(block[FEATURES])[:,1],
                 "logistica_umbral_0_5":model.predict_proba(block[FEATURES])[:,1],
                 "prevalencia_entrenamiento":np.full(len(block), prevalence),
                 "siempre_alerta":np.ones(len(block)),
                 "persistencia_conteo":(block.lag_1>block.umbral_casos).astype(float).to_numpy()}
        for method, prob in probs.items():
            t = threshold if method=="logistica_umbral_validado" else .5
            pred = (prob>=t).astype(int)
            tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
            metrics.append({"bloque":name,"modelo":method,"n":len(y),"prevalencia":float(y.mean()),
                "umbral_probabilidad":t,"sensibilidad":recall_score(y,pred,zero_division=0) if y.sum()>0 else None,
                "precision":precision_score(y,pred,zero_division=0) if pred.sum()>0 else None,
                "f1":f1_score(y,pred,zero_division=0) if y.sum()>0 else None,
                "f2":fbeta_score(y,pred,beta=2,zero_division=0) if y.sum()>0 else None,
                "especificidad":float(tn/(tn+fp)) if tn+fp>0 else None,
                "pr_auc_AP":average_precision_score(y,prob) if y.nunique()==2 else None,
                "roc_auc":roc_auc_score(y,prob) if y.nunique()==2 else None,
                "brier":brier_score_loss(y,prob),"tn":int(tn),"fp":int(fp),"fn":int(fn),"tp":int(tp)})
            out = block[["inicio_semana","anio_epi","semana_epi","casos","umbral_casos","exceso"]].copy()
            out["bloque"], out["modelo"], out["probabilidad"], out["prediccion"] = name, method, prob, pred
            predictions.append(out)
    metric_df, pred_df = pd.DataFrame(metrics), pd.concat(predictions, ignore_index=True)
    reports = ROOT/"reports/tables"
    reports.mkdir(parents=True, exist_ok=True)
    metric_df.to_csv(reports/"metricas_logistica.csv", index=False)
    pred_df.to_csv(reports/"predicciones_logistica.csv", index=False)
    scores.to_csv(reports/"seleccion_umbral_validacion.csv", index=False)
    pd.DataFrame(splits).to_csv(reports/"particiones_temporales.csv", index=False)
    coefficients = pd.DataFrame({"variable":FEATURES,"coeficiente_estandarizado":model[-1].coef_[0]})
    coefficients.to_csv(reports/"coeficientes_logistica.csv", index=False)
    (ROOT/"modelos").mkdir(parents=True, exist_ok=True)
    metadata = {"municipio":cfg["municipio"],"modelo":"logistica_L2_C1",
                "features":FEATURES,"config":cfg,"umbral_probabilidad":threshold,
                "entrenado_hasta":str(train.fin_semana.max().date()),"particiones":splits,
                "semana_objetivo":"una semana después del corte nominal",
                "canal":"P75 de la misma semana en los cinco años anteriores; exige cinco valores",
                "advertencia":"Retrospectivo: datos finales por inicio de síntomas, no disponibles necesariamente al corte. Sin calibración externa ni validación prospectiva.",
                "sha256_panel":hashlib.sha256(panel.to_csv(index=False).encode()).hexdigest()}
    version=cfg["version_experimento"]
    metadata["version_experimento"]=version
    joblib.dump({"pipeline":model,"metadata":metadata}, ROOT/f"modelos/logistica_{ciudad}_{version}.joblib")
    guardar_json(ROOT/f"modelos/logistica_{ciudad}_{version}.json",metadata)
    return model, metric_df, pred_df, pd.DataFrame(splits), coefficients
