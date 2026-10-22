"""Documenta el cambio de fecha principal sin escoger la versión por sus métricas."""
from pathlib import Path
import sys,json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from dengue.pipeline import parsear_fecha

raw=pd.read_csv(ROOT/'data/raw/cali_original.csv',dtype='string',keep_default_na=False)
rows=[]
dates={c:parsear_fecha(raw[c]) for c in ['INI_SIN','FEC_CON','FEC_NOT']}
for c,d in dates.items():
    rows.append({'campo':c,'total':len(raw),'fechas_interpretables':int(d.notna().sum()),
                 'ausentes_o_invalidas':int(d.isna().sum()),'porcentaje_interpretable':100*d.notna().mean()})
pd.DataFrame(rows).to_csv(ROOT/'reports/tables/completitud_fechas.csv',index=False)
old=ROOT/'data/historico/cronologia_v0'
before=json.loads((old/'resumen_eda.json').read_text(encoding='utf-8'))
after=json.loads((ROOT/'reports/resumen_eda.json').read_text(encoding='utf-8'))
old_metrics=pd.read_csv(old/'reports/tables/metricas_logistica.csv')
new_metrics=pd.read_csv(ROOT/'reports/tables/metricas_logistica.csv')
comparison=pd.concat([old_metrics.assign(version='v0'),new_metrics.assign(version='v1_ini_sin')],ignore_index=True)
comparison.to_csv(ROOT/'reports/tables/comparacion_cronologias.csv',index=False)
lines=['# Reconstrucción con inicio de síntomas como única fecha principal','',
       'Versión vigente: v1_ini_sin. Decisión adoptada el 22 de octubre de 2026. Se reconstruyeron panel, canal, etiquetas, variables y entrenamiento. El objetivo y los cortes de evaluación no se cambiaron para mejorar métricas.','',
       '## Decisión y controles','',
       'Usar exclusivamente INI_SIN para fechar cada caso. Los registros sin fecha válida se separan sin sustituirla por notificación o consulta. FEC_NOT y FEC_CON permanecen como controles de calidad, sin ser condición de disponibilidad para incluir un inicio válido. Una anomalía de notificación se marca; no se corrigen o inventan sus fechas.','',
       '| Campo | Fechas interpretables | Faltantes o inválidas | Completitud |','|---|---:|---:|---:|']
for r in rows:lines.append(f"| {r['campo']} | {r['fechas_interpretables']:,} | {r['ausentes_o_invalidas']} | {r['porcentaje_interpretable']:.4f} % |")
both=dates['INI_SIN'].notna()&dates['FEC_CON'].notna()
lines += ['',f"En {int(both.sum()):,} registros hay inicio y consulta interpretables; en ninguno el inicio es posterior a consulta. Esto respalda la coherencia interna, pero no certifica la fecha real de cada acontecimiento. Notificación tiene mayor completitud, pero las 7.069 contradicciones favorecen escoger síntomas para la evolución retrospectiva.",'',
          '## Efecto de la reconstrucción','',
          '| Indicador | v0 | v1 inicio de síntomas |','|---|---:|---:|']
for label,key in [('Registros incluidos','filas_finales'),('Fechas sustituidas','fechas_sustituidas_finales'),
                  ('Semanas del panel','semanas_panel'),('Semanas sin registros','semanas_sin_registros_no_imputadas'),
                  ('Semanas etiquetadas','semanas_con_etiqueta'),('Filas elegibles para modelo','semanas_elegibles_modelo')]:
    lines.append(f'| {label} | {before[key]:,} | {after[key]:,} |')
lines += ['', 'Se conservaron los 7.069 registros antes retirados por notificación anterior. A la vez, se separaron los cinco que antes utilizaban una fecha alternativa. El cambio neto es de 7.064 registros. Además, permanece la exclusión de un inicio fuera de la ventana epidemiológica. Los seis excluidos actuales están en data/processed/registros_excluidos.csv. Las semanas sin registros permanecen desconocidas, sin imputación a cero.','',
          '## Comparación de validación 2022–2023','',
          '| Versión y método | Sensibilidad | Precisión | F1 | Falsas alarmas | Excesos omitidos |',
          '|---|---:|---:|---:|---:|---:|']
q=comparison.loc[comparison.bloque.eq('validacion')&comparison.modelo.isin(['logistica_umbral_validado','persistencia_conteo'])]
for r in q.itertuples():
    lines.append(f'| {r.version} {r.modelo} | {100*r.sensibilidad:.1f} % | {100*r.precision:.1f} % | {100*r.f1:.1f} % | {r.fp} | {r.fn} |')
lines += ['', 'La logística sigue sin mejorar a la persistencia en validación. En 2024 continúa alertando en todas las semanas; una sensibilidad alta allí no demuestra discriminación. No se eligió la fecha por estos resultados. La comparación entre versiones es una sensibilidad metodológica; 2024 ya fue observado y no se presenta como una nueva prueba independiente.','',
          '## Alcance y verificación','',
          'Se ejecutaron los dos notebooks, se conservaron los resultados anteriores y se agregaron pruebas que garantizan que una notificación anterior o ausente no elimine un inicio válido y que una fecha de síntomas faltante no se sustituya. Las contradicciones de las fechas auxiliares permanecen visibles.','',
          'La evaluación sigue siendo retrospectiva con datos finales. Elegir síntomas para agrupar no resuelve el retraso de disponibilidad operacional. Se requiere esa evaluación antes de afirmar que el servicio anticipa brotes en tiempo real.']
(ROOT/'docs/reconstruccion_fecha_sintomas.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Completitud y comparación v0/v1 documentadas.')
