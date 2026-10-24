"""Verifica que datos, artefacto y resultados guardados sean del mismo experimento."""
import hashlib
import numpy as np
import pandas as pd
from sklearn.metrics import (confusion_matrix, precision_score, recall_score,
    f1_score, fbeta_score, brier_score_loss, average_precision_score, roc_auc_score)
from .pipeline import FEATURES

def coincide_artefacto(panel, cfg, metadata):
    # Los artefactos históricos se generaron en Windows. Admitir únicamente la
    # diferencia LF/CRLF permite verificarlos en Linux sin cambiar datos ni metadatos.
    huellas = {hashlib.sha256(panel.to_csv(index=False, lineterminator=salto).encode()).hexdigest()
               for salto in ['\n', '\r\n']}
    return (metadata.get('sha256_panel') in huellas
            and metadata.get('config')==cfg and metadata.get('features')==FEATURES
            and metadata.get('version_experimento')==cfg['version_experimento'])

def verificar_resultados(panel, cfg, model, metadata, metricas, predicciones, particiones, coeficientes):
    """Recalcula inferencias y métricas sin ajustar coeficientes ni usar prueba para elegir."""
    if not coincide_artefacto(panel,cfg,metadata):
        raise ValueError('El artefacto no coincide con el panel/configuración actual: reentrenar.')
    if cfg['horizonte_semanas']!=1:
        raise ValueError('Este experimento admite exclusivamente horizonte de una semana.')
    d=panel.loc[panel.elegible_modelo].copy()
    bloques={
        'entrenamiento':d.loc[d.anio_epi<=cfg['fin_entrenamiento']],
        'validacion':d.loc[d.anio_epi.between(cfg['fin_entrenamiento']+1,cfg['fin_validacion'])],
        f"prueba_{cfg['anio_prueba']}":d.loc[d.anio_epi.eq(cfg['anio_prueba'])],
        f"adicional_{cfg['anio_adicional']}":d.loc[d.anio_epi.eq(cfg['anio_adicional'])]}
    train=bloques['entrenamiento']
    assert pd.Timestamp(metadata['entrenado_hasta'])==train.fin_semana.max()
    assert train.fin_semana.max()<bloques['validacion'].inicio_semana.min()
    assert bloques['validacion'].fin_semana.max()<bloques[f"prueba_{cfg['anio_prueba']}"].inicio_semana.min()
    np.testing.assert_allclose(model[0].mean_,train[FEATURES].mean().to_numpy(),atol=1e-10)
    assert len(coeficientes)==len(FEATURES) and coeficientes.variable.tolist()==FEATURES
    np.testing.assert_allclose(coeficientes.coeficiente_estandarizado,model[-1].coef_[0],atol=1e-12)
    predicciones=predicciones.copy()
    predicciones['inicio_semana']=pd.to_datetime(predicciones.inicio_semana)
    assert not predicciones.duplicated(['modelo','inicio_semana']).any()
    expected_rows=0
    controls=[]
    for name,b in bloques.items():
        info=particiones.loc[particiones.bloque.eq(name)]
        assert len(info)==1 and int(info.iloc[0].filas)==len(b)
        assert int(info.iloc[0].positivos)==int(b.exceso.sum())
        if b.empty:
            continue
        probabilities={
            'logistica_umbral_validado':model.predict_proba(b[FEATURES])[:,1],
            'logistica_umbral_0_5':model.predict_proba(b[FEATURES])[:,1],
            'prevalencia_entrenamiento':np.full(len(b),train.exceso.mean()),
            'siempre_alerta':np.ones(len(b)),
            'persistencia_conteo':(b.lag_1>b.umbral_casos).astype(float).to_numpy()}
        y=b.exceso.astype(int).to_numpy()
        for method,prob in probabilities.items():
            expected_rows+=len(b)
            threshold=metadata['umbral_probabilidad'] if method=='logistica_umbral_validado' else .5
            pred=(prob>=threshold).astype(int)
            stored=predicciones.loc[predicciones.bloque.eq(name)&predicciones.modelo.eq(method)].sort_values('inicio_semana')
            assert len(stored)==len(b)
            assert stored.inicio_semana.tolist()==b.inicio_semana.tolist()
            np.testing.assert_allclose(stored.probabilidad,prob,atol=1e-12)
            np.testing.assert_array_equal(stored.prediccion,pred)
            np.testing.assert_array_equal(stored.exceso,y)
            np.testing.assert_allclose(stored.casos,b.casos,atol=1e-12)
            np.testing.assert_allclose(stored.umbral_casos,b.umbral_casos,atol=1e-12)
            rows=metricas.loc[metricas.bloque.eq(name)&metricas.modelo.eq(method)]
            assert len(rows)==1
            r=rows.iloc[0];tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
            np.testing.assert_array_equal([r.tn,r.fp,r.fn,r.tp],[tn,fp,fn,tp])
            expected={
                'n':len(b),'prevalencia':y.mean(),'umbral_probabilidad':threshold,
                'sensibilidad':recall_score(y,pred) if y.sum()>0 else np.nan,
                'precision':precision_score(y,pred) if pred.sum()>0 else np.nan,
                'f1':f1_score(y,pred) if y.sum()>0 else np.nan,
                'f2':fbeta_score(y,pred,beta=2) if y.sum()>0 else np.nan,
                'especificidad':tn/(tn+fp) if tn+fp>0 else np.nan,
                'brier':brier_score_loss(y,prob),
                'pr_auc_AP':average_precision_score(y,prob) if len(np.unique(y))==2 else np.nan,
                'roc_auc':roc_auc_score(y,prob) if len(np.unique(y))==2 else np.nan}
            for c,v in expected.items():
                assert np.isclose(r[c],v,atol=1e-12,equal_nan=True),(name,method,c)
        controls.append({'bloque':name,'semanas_verificadas':len(b),'metodos_verificados':len(probabilities),
                         'predicciones_y_metricas':'coinciden'})
    assert len(predicciones)==expected_rows
    assert len(metricas)==sum(not b.empty for b in bloques.values())*5
    val=bloques['validacion'];prob=model.predict_proba(val[FEATURES])[:,1]
    grid=np.arange(.10,.91,.05)
    scores=[(fbeta_score(val.exceso,prob>=t,beta=2,zero_division=0),t) for t in grid]
    chosen=max(scores)[1]
    assert np.isclose(chosen,metadata['umbral_probabilidad'])
    return pd.DataFrame(controls)
