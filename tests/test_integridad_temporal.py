import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from dengue.pipeline import calendario, inicio_anio_epi, parsear_fecha, agregar_canal, agregar_features, config, construir_panel, preparar_microdatos

def test_fechas_ambiguas_respetan_dia_mes():
    result = parsear_fecha(pd.Series(["03/07/2024 12:00:00 a. m.","07/03/2024","31/02/2024","2024-12-29"]))
    assert result.iloc[0] == pd.Timestamp("2024-07-03")
    assert result.iloc[1] == pd.Timestamp("2024-03-07")
    assert pd.isna(result.iloc[2])
    assert result.iloc[3] == pd.Timestamp("2024-12-29")

def test_calendario_ins_2025_incluye_semana_53():
    c=calendario(2025,2025)
    assert len(c)==53
    assert c.iloc[0].inicio_semana==pd.Timestamp("2024-12-29")
    assert c.iloc[0].fin_semana==pd.Timestamp("2025-01-04")
    assert c.iloc[-1].fin_semana==pd.Timestamp("2026-01-03")

def test_no_se_omiten_semanas_ni_se_saltan_lags():
    p=calendario(2024,2025)
    assert p.inicio_semana.diff().dropna().eq(pd.Timedelta(days=7)).all()
    p["casos"]=np.arange(len(p),dtype=float)
    p=agregar_features(p.assign(exceso=0))
    assert p.iloc[-1].lag_1==p.iloc[-2].casos
    assert p.iloc[-1].corte_prediccion<p.iloc[-1].inicio_semana

def test_future_counts_do_not_change_prior_labels_or_features():
    cfg=config(); p=calendario(2007,2025);p["casos"]=np.arange(len(p),dtype=float)+1
    before=agregar_features(agregar_canal(p,cfg))
    cutoff=pd.Timestamp("2023-01-01")
    changed=p.copy();changed.loc[changed.inicio_semana>=cutoff,"casos"] *= 1000
    after=agregar_features(agregar_canal(changed,cfg))
    cols=["umbral_casos","exceso","lag_1","media_4"]
    pd.testing.assert_frame_equal(before.loc[before.inicio_semana<cutoff,cols],after.loc[after.inicio_semana<cutoff,cols])

def test_target_count_does_not_enter_own_features_or_channel():
    p=calendario(2007,2025);p["casos"]=np.arange(len(p),dtype=float)+1;cfg=config()
    i=400
    first=agregar_features(agregar_canal(p,cfg))
    p.loc[i,"casos"]=1000000
    second=agregar_features(agregar_canal(p,cfg))
    cols=["umbral_casos","lag_1","lag_12","media_4","std_4"]
    pd.testing.assert_series_equal(first.loc[i,cols],second.loc[i,cols])

def test_ausencia_de_registros_permanece_desconocida():
    cfg=config(); c=calendario(2007,2025)
    m=pd.DataFrame({"inicio_semana":[c.iloc[0].inicio_semana],"confirmado":[1],
                    "hospitalizado":[0],"retraso_notificacion_dias":[3],"FEC_NOT_fecha":[pd.Timestamp("2007-01-02")]})
    p=construir_panel(m,cfg)
    assert p.iloc[1].n_registros==0
    assert pd.isna(p.iloc[1].casos)
    assert p.n_registros.sum()==1

def test_fecha_sintomas_no_depende_de_notificacion_ni_se_sustituye():
    base={"COD_EVE":"210","COD_PAIS_O":"170","COD_DPTO_O":"76","COD_MUN_O":"001",
          "Estado_final_de_caso":"2","confirmados":"0","FEC_CON":"12/03/2013",
          "PAC_HOS":"2","ARCHIVO_ORIGEN":"ejemplo.xlsx"}
    raw=pd.DataFrame([
        {**base,"CONSECUTIVE":"a","HUELLA_REGISTRO":"a","INI_SIN":"10/03/2013","FEC_NOT":"01/03/2013"},
        {**base,"CONSECUTIVE":"b","HUELLA_REGISTRO":"b","INI_SIN":"","FEC_NOT":"12/03/2013"},
        {**base,"CONSECUTIVE":"c","HUELLA_REGISTRO":"c","INI_SIN":"10/03/2013","FEC_NOT":""}])
    m,steps,quality=preparar_microdatos(raw,config())
    assert set(m.CONSECUTIVE)=={"a","c"}
    assert m.fecha_analitica.eq(pd.Timestamp("2013-03-10")).all()
    assert not m.fecha_sustituida.any()
    assert m.loc[m.CONSECUTIVE.eq("a"),"flag_notificacion_anterior_sintomas"].all()
    assert quality["anomalias_notificacion_conservadas"]==1
