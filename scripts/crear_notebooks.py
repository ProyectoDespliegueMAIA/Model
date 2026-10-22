"""Construye dos notebooks didácticos. Ejecutarlos mediante ejecutar_notebooks.py."""
from pathlib import Path
from textwrap import dedent
import nbformat as nbf

ROOT=Path(__file__).resolve().parents[1]
def md(text):return nbf.v4.new_markdown_cell(dedent(text).strip())
def code(text):return nbf.v4.new_code_cell(dedent(text).strip())
setup='''
from pathlib import Path
import sys, json
import numpy as np
import pandas as pd
from IPython.display import display, Image
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / 'configs/piloto.json').exists())
sys.path.insert(0, str(ROOT / 'src'))
from dengue.pipeline import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'figure.figsize': (12,4), 'font.size': 10})
FIG = ROOT / 'reports/figures'
FIG.mkdir(parents=True, exist_ok=True)
cfg = config()
display(pd.Series(cfg, name='Configuración acordada').to_frame())
'''

cells=[
md('''# 01 Preparación y exploración semanal de dengue en Cali

**Propósito:** obtener una serie semanal trazable antes de entrenar. Este piloto utiliza notificaciones del evento 210 con estados 2, 3 y 5; sus conteos no equivalen a todas las infecciones existentes. La comparación de municipios y el clima quedan para etapas siguientes.

Ejecutar las celdas en orden. Los cálculos están en `src/dengue/pipeline.py` para reutilizarlos y probarlos. No se muestran filas individuales de pacientes. Los originales permanecen intactos.

**Etapas:** extracción → auditoría → calendario → exploración → canal → variables causales → exportación. El notebook 02 realiza el primer entrenamiento después de estas comprobaciones.'''),
md('''## 1 Configuración y fuentes

La extracción se ejecuta antes de este notebook con `python scripts/extraer_cali.py`. Lee los 19 Excel, conserva archivo y fila de origen y genera una huella de las 69 columnas originales por registro. Los CSV derivados del compañero sirven como contraste; no constituyen la fuente canónica porque su calendario necesita reconstrucción.'''),
code(setup),
code('''
source = ROOT / 'data/raw/cali_original.csv'
if not source.exists():
    raise FileNotFoundError('Ejecutar primero scripts/extraer_cali.py')
raw = pd.read_csv(source, dtype='string', keep_default_na=False)
manifest = pd.DataFrame(json.loads((ROOT/'data/raw/manifiesto_fuentes.json').read_text(encoding='utf-8')))
display(manifest[['archivo','filas','filas_cali','sha256']])
print(f'Extraídos: {len(raw):,} registros; columnas: {raw.shape[1]}')
assert len(raw) == manifest.filas_cali.sum()
'''),
md('''## 2 Reglas de limpieza y trazabilidad

1. Eliminar solo duplicados exactos de las columnas originales, conservando el primer origen; no deduplicar por identificador aislado.
2. Conservar evento 210, país 170, departamento 76, municipio 001 y estados finales 2/3/5.
3. Parsear día/mes/año explícitamente, ISO o serial Excel; nunca inferir fechas ambiguas.
4. Usar exclusivamente inicio de síntomas; si falta o no puede parsearse, separar el registro sin sustituirlo por notificación.
5. Conservar los registros con notificación anterior a síntomas y marcar la anomalía; no utilizar FEC_NOT como requisito de inclusión. Comprobar síntomas frente a consulta como control adicional, sin inventar fechas.
6. Conservar retrasos mayores de 180 días como diagnóstico, sin recortarlos artificialmente.
7. Limitar por año epidemiológico validado, no por nombre de archivo.

El estado final y las revisiones posteriores impiden reconstruir perfectamente qué se sabía en cada corte. La evaluación inicial será retrospectiva.

**Decisión actualizada v1:** las 7.069 cronologías negativas de notificación se concentran en el archivo original de 2013. Se conservan como registros con síntomas válidos, con bandera de anomalía. El inicio de síntomas es interpretable en 160.704 de 160.709 registros, y no hay síntomas posteriores a consulta cuando ambas fechas están disponibles. Esto respalda su elección, sin garantizar que cada fecha sea verdadera. Los cinco registros sin inicio se separan. La versión anterior y sus métricas se guardaron en `data/historico/cronologia_v0/`.'''),
code('''
micro, auditoria, calidad = preparar_microdatos(raw, cfg)
display(auditoria)
display(pd.Series({k:v for k,v in calidad.items() if k!='diagnostico_por_archivo'}, name='Diagnóstico').to_frame())
display(pd.DataFrame(calidad['diagnostico_por_archivo']))
display(micro.groupby('Estado_final_de_caso').size().rename('registros').to_frame())
assert micro.HUELLA_REGISTRO.is_unique
assert micro.cod_municipio.eq('76001').all()
'''),
md('''## 3 Reconstrucción del calendario epidemiológico

Se usan semanas domingo–sábado. La primera semana contiene al menos cuatro días del año (se obtiene desde el 4 de enero). Verificación de referencia INS 2025: semana 1 del 29/12/2024 al 04/01/2025 y semana 53 del 28/12/2025 al 03/01/2026. Debe contrastarse el calendario histórico si se incorporan otras convenciones o fuentes.

No se fuerza un panel de 52 semanas por año. Una semana sin registros se conserva con `n_registros=0` como hecho de extracción, pero `casos=NaN`: todavía no certificamos cero casos epidemiológicos ni completitud del reporte.'''),
code('''
panel = construir_panel(micro, cfg)
display(panel.groupby('anio_epi').agg(semanas=('semana_epi','size'),
    notificaciones=('n_registros','sum'), semanas_sin_registros=('semana_con_registros',lambda x: (~x).sum())))
display(panel.loc[panel.semana_epi.eq(53), ['anio_epi','semana_epi','inicio_semana','fin_semana','n_registros']])
print('Reconciliación:', panel.n_registros.sum(), 'registros =', len(micro), 'microdatos incluidos')
assert panel.n_registros.sum() == len(micro)
'''),
md('''## 4 Contraste con la serie recibida

Las diferencias combinan la corrección de calendario y las exclusiones explícitas. No deben atribuirse todas a semanas 53. La comparación no altera el archivo del compañero. Los porcentajes clínicos contemporáneos y los valores interpolados del CSV anterior no entran a la matriz inicial.'''),
code('''
workspace = next((p for p in ROOT.parents if (p/'06_serie_temporal_semanal_76001_lista_ML.csv').exists()), None)
if workspace:
    anterior = pd.read_csv(workspace/'06_serie_temporal_semanal_76001_lista_ML.csv')
    display(pd.DataFrame({'serie':['Recibida','Reconstruida'],
        'filas':[len(anterior), len(panel)],
        'suma_notificaciones':[int(anterior.casos_totales_validos.sum()), int(panel.n_registros.sum())]}))
    # Comprobación independiente de la incompatibilidad de claves/fechas recibidas.
    amigo = pd.read_csv(workspace/'05_microdatos_limpios_municipio_76001.csv', usecols=['ANIO_EPI','SEMANA_EPI','FECHA_EPIDEMIOLOGICA'])
    amigo['fecha'] = pd.to_datetime(amigo.FECHA_EPIDEMIOLOGICA, format='%Y-%m-%d', errors='coerce')
    limites = amigo.groupby(['ANIO_EPI','SEMANA_EPI']).fecha.agg(['min','max'])
    print('Grupos recibidos con fechas que abarcan más de 7 días:', int(((limites['max']-limites['min']).dt.days>6).sum()))
else:
    print('Contraste opcional omitido: CSV del compañero no localizado.')
'''),
md('''## 5 Evolución histórica y cobertura

Una caída de notificaciones no demuestra por sí misma disminución de transmisión: puede combinar vigilancia, clasificación y cambios de reporte. Las cifras de 2025 deben revisarse en ese contexto. La vista histórica es descriptiva; no se utiliza para escoger variables o parámetros con el conjunto de prueba.'''),
code('''
fig, ax = plt.subplots()
ax.plot(panel.inicio_semana, panel.casos, linewidth=0.8, color='#17608a')
ax.set(xlabel='Inicio de semana epidemiológica', ylabel='Notificaciones incluidas', title='Cali 2007–2025 · serie reconstruida por inicio de síntomas')
ax.grid(alpha=.2); fig.tight_layout()
fig.savefig(FIG/'01_serie_semanal.png', dpi=160); plt.close(fig)
display(Image(filename=str(FIG/'01_serie_semanal.png')))
'''),
code('''
# Solo desarrollo para explorar estacionalidad sin seleccionar usando prueba.
desarrollo = panel.loc[panel.anio_epi<=cfg['fin_entrenamiento']]
estacional = desarrollo.groupby('semana_epi').casos.agg(['median','count'])
fig, axes = plt.subplots(1,2,figsize=(12,4))
axes[0].plot(estacional.index,estacional['median'],color='#17608a')
axes[0].set(title='Mediana semanal en desarrollo',xlabel='Semana epidemiológica',ylabel='Notificaciones')
anual = panel.groupby('anio_epi').n_registros.sum()
axes[1].bar(anual.index,anual.values,color='#17608a')
axes[1].set(title='Conteos por año epidemiológico',xlabel='Año',ylabel='Notificaciones incluidas')
axes[1].set_xticks(list(range(2007,2026,3)))
fig.tight_layout();fig.savefig(FIG/'02_estacionalidad_anual.png',dpi=160);plt.close(fig)
display(Image(filename=str(FIG/'02_estacionalidad_anual.png')))
'''),
md('''## 6 Retrasos y disponibilidad

Los retrasos se calculan sin convertir negativos en cero ni valores altos en 180. Las cronologías negativas de notificación se conservan como anomalías; solo los retrasos no negativos se utilizan para resumir demoras interpretables. La notificación no decide la agrupación ni la inclusión. Los conteos finales por síntomas pueden incluir notificaciones recibidas después del corte nominal: esto limita la interpretación operacional del modelo de la siguiente etapa.'''),
code('''
demora_valida = micro.retraso_notificacion_dias.where(micro.retraso_notificacion_dias.ge(0))
display(demora_valida.describe(percentiles=[.5,.9,.95,.99]).to_frame())
print('Anomalías de notificación conservadas:', int(micro.flag_notificacion_anterior_sintomas.sum()))
print('Porcentaje con notificación más de 7 días después de síntomas:',
      round(100*demora_valida.dropna().gt(7).mean(),2), '(entre retrasos no negativos disponibles)')
fig,ax=plt.subplots()
delay = demora_valida.dropna()
ax.hist(delay[delay<=90],bins=30,color='#17608a')
ax.set(title='Retrasos de notificación · se muestran 0–90 días',xlabel='Días desde síntomas',ylabel='Registros')
fig.tight_layout();fig.savefig(FIG/'03_retrasos.png',dpi=160);plt.close(fig)
display(Image(filename=str(FIG/'03_retrasos.png')))
'''),
md('''## 7 Definición inicial del exceso

Para el objetivo semanal t, el umbral es el percentil 75 de los conteos de **esa misma semana epidemiológica en los cinco años anteriores**, con interpolación lineal del cuantil. Se requieren cinco valores válidos; si faltan, no se asigna etiqueta. `exceso=1` cuando el conteo observado supera estrictamente el umbral.

Es una definición operacional inicial, no una declaración oficial de epidemia ni una reproducción del canal geométrico de Bortman. Cinco observaciones por semana producen umbrales inestables; queda pendiente el análisis de sensibilidad. Las semanas 53 se conservan en la serie y en los rezagos, aunque pueden no tener suficientes años previos para etiquetarse. Los años iniciales sirven para inicializar el canal.'''),
code('''
panel = agregar_canal(panel,cfg)
display(panel.groupby('anio_epi').agg(etiquetadas=('exceso','count'),positivas=('exceso','sum')))
display(panel.loc[panel.exceso.notna(), ['anio_epi','semana_epi','casos','n_anios_canal','umbral_casos','exceso']].head(10))
assert panel.loc[panel.exceso.notna(),'n_anios_canal'].ge(5).all()
'''),
md('''## 8 Variables disponibles antes de la semana objetivo

La fila t corresponde a la semana a predecir; su corte nominal es el sábado inmediatamente anterior. Se usan conteos de t−1, t−2, t−3, t−4, t−8 y t−12, media/desviación de las cuatro semanas anteriores y estacionalidad conocida del objetivo. Se exige historia completa para estas variables; no se interpolan faltantes.

Se excluyen como predictores los conteos del objetivo, su etiqueta, su umbral y las características de pacientes de esa semana. El umbral se guarda para interpretar la etiqueta y construir la referencia de persistencia. Incluso los rezagos finales deben interpretarse como evaluación retrospectiva, pues el retraso de notificación impide afirmar que estuvieran completos al corte.'''),
code('''
panel = agregar_features(panel)
display(panel.loc[panel.elegible_modelo,['inicio_semana','corte_prediccion',*FEATURES,'exceso']].head())
display(pd.DataFrame({'variable':FEATURES,'origen':['historia anterior']*8+['calendario conocido']*2}))
annual, summary = exportar_eda(raw,micro,auditoria,calidad,panel)
display(annual)
display(pd.Series({k:v for k,v in summary.items() if k!='diagnostico_por_archivo'},name='Resultado de preparación').to_frame())
'''),
md('''## 9 Cierre de la fase exploratoria y siguiente paso

Se exportaron auditoría, manifiesto de fuentes, microdatos locales, panel completo y figuras. La suma se reconcilia después de exclusiones explícitas. Se conservan semanas sin registros como desconocidas y la semana 53 sin eliminaciones artificiales.

**Siguiente notebook:** regresión logística regularizada, entrenamiento hasta 2021, validación 2022–2023, prueba 2024 y evaluación adicional 2025. No se ajusta el modelo con las métricas de prueba. Pendientes: revisión del caso/fecha con el experto, cobertura externa, sensibilidad del canal, simulación con disponibilidad real, clima y extensión a otros municipios.

Referencias: [calendario INS 2025](https://portalsivigila.ins.gov.co/Documentos%20compartidos/Calendario%202025.pdf) y [Umaña et al. 2026](https://publichealth.jmir.org/2026/1/e79914).''')]

cells2=[
md('''# 02 Primer entrenamiento de alerta semanal de dengue

Este ejercicio entrena una **regresión logística con penalización L2** para estimar la probabilidad de exceso en la semana siguiente al corte nominal, según la definición P75 del notebook 01. Se compara con referencias simples. HistGradientBoostingClassifier queda para la siguiente comparación; todavía no hay búsqueda entre familias de modelos.

La evaluación es retrospectiva sobre notificaciones finales: no demuestra rendimiento en tiempo real ni capacidad para detectar brotes definidos por una fuente externa. Ejecutar primero el notebook 01.'''),
md('## 1 Entorno y carga del panel validado'),code(setup),
code('''
panel = pd.read_csv(ROOT/'data/processed/cali_panel_semanal.csv',
    parse_dates=['inicio_semana','fin_semana','corte_prediccion'])
datos = panel.loc[panel.elegible_modelo].copy()
print('Observaciones elegibles:',len(datos))
display(datos.groupby('anio_epi').exceso.agg(['count','sum','mean']).rename(columns={'sum':'positivos','mean':'prevalencia'}))
'''),
md('''## 2 Partición cronológica y propósito de cada bloque

- Hasta 2021: ajuste del escalador y de los coeficientes.
- 2022–2023: elección del umbral de probabilidad, maximizando F2 en una rejilla predefinida; en empates se prefiere el umbral mayor.
- 2024: prueba sin seleccionar modelo o umbral con sus resultados.
- 2025: evaluación adicional; las cifras requieren revisar cobertura y cambio de comportamiento.

El canal de cada fila se calcula con sus años anteriores. La validación y prueba pueden usar semanas ya observadas anteriores dentro de su propio bloque, sin reentrenar: se simulan orígenes móviles de un paso con datos finales. No equivale a predecir todo el bloque desde un único corte. No hay escalado ni selección de variables con prueba.'''),
code('''
particiones_previas = datos.assign(bloque=np.select(
    [datos.anio_epi<=2021,datos.anio_epi.between(2022,2023),datos.anio_epi.eq(2024)],
    ['entrenamiento','validacion','prueba_2024'],default='adicional_2025'))
display(particiones_previas.groupby('bloque').agg(n=('exceso','size'),
    positivos=('exceso','sum'),inicio=('inicio_semana','min'),fin=('fin_semana','max')))
print('Variables:',FEATURES)
'''),
md('''## 3 Entrenar el modelo y las referencias

El pipeline ajusta `StandardScaler` con entrenamiento y después `LogisticRegression(C=1, penalty L2 por defecto, solver=lbfgs)`. Los hiperparámetros se fijan antes de mirar prueba. No se aplica SMOTE ni se mezclan fechas.

Referencias: probabilidad constante igual a prevalencia de entrenamiento; persistencia de conteo, que pronostica el último conteo observado y lo contrasta con el umbral conocido del objetivo; y la regla trivial de alertar siempre. Las decisiones binarias de referencia no son probabilidades calibradas. Se informa también la logística a umbral 0,5 para separar el efecto del modelo del efecto del umbral.'''),
code('''
model, metricas, predicciones, particiones, coeficientes = entrenar_logistica(panel,cfg)
display(particiones)
display(pd.read_csv(ROOT/'reports/tables/seleccion_umbral_validacion.csv').sort_values('f2_validacion',ascending=False).head(6))
'''),
md('''## 4 Métricas fuera de entrenamiento

Sensibilidad: qué proporción de semanas con exceso detectamos. Precisión: qué proporción de alertas corresponde a exceso. AP resume la curva precisión–recobrado (no es el área trapezoidal). Brier evalúa error de probabilidad; menor es mejor. La matriz de confusión permite contar falsas alarmas y excesos omitidos.

La evaluación se hace contra nuestra etiqueta histórica, no contra una lista independiente de brotes. Los resultados de entrenamiento son descriptivos y no evidencia de generalización. Las AUC se dejan vacías si el bloque contiene una sola clase; sensibilidad y F1/F2 se dejan vacíos cuando no hay positivos reales. La precisión queda vacía cuando no se emitió ninguna alerta.

**Lectura crítica:** revisar prevalencia y matriz de confusión junto a sensibilidad y F1. Si un bloque tiene casi todas las semanas positivas, alertar siempre puede obtener métricas altas. La persistencia es una referencia exigente. La reconstrucción v1 responde a una decisión de calidad de datos, no a elegir el resultado que mejore prueba. Como ya se observaron resultados de 2024 en v0, la comparación de versiones es un análisis de sensibilidad, no una nueva prueba independiente.'''),
code('''
cols=['bloque','modelo','n','prevalencia','umbral_probabilidad','sensibilidad','especificidad','precision','f1','f2','pr_auc_AP','roc_auc','brier','tn','fp','fn','tp']
display(metricas.loc[metricas.bloque.ne('entrenamiento'),cols].round(4))
'''),
md('## 5 Matriz de confusión de prueba y evolución de probabilidades'),
code('''
row=metricas.loc[(metricas.bloque=='prueba_2024')&(metricas.modelo=='logistica_umbral_validado')].iloc[0]
matrix=np.array([[row.tn,row.fp],[row.fn,row.tp]],dtype=int)
fig,axes=plt.subplots(1,2,figsize=(12,4))
axes[0].imshow(matrix,cmap='Blues')
for (i,j),value in np.ndenumerate(matrix):axes[0].text(j,i,str(value),ha='center',va='center',fontsize=16)
axes[0].set(xticks=[0,1],yticks=[0,1],xticklabels=['Sin alerta','Alerta'],yticklabels=['Sin exceso','Exceso'],
            xlabel='Predicción',ylabel='Observado',title='Prueba 2024 · matriz de confusión')
q=predicciones.loc[(predicciones.bloque=='prueba_2024')&(predicciones.modelo=='logistica_umbral_validado')]
axes[1].plot(q.inicio_semana,q.probabilidad,label='Probabilidad')
axes[1].scatter(q.inicio_semana,q.exceso,label='Exceso observado',s=15)
axes[1].axhline(row.umbral_probabilidad,linestyle='--',color='gray',label='Umbral validado')
axes[1].set(ylabel='Probabilidad / etiqueta',title='Prueba 2024 · comparación semanal',ylim=(-.05,1.05))
axes[1].tick_params(axis='x',rotation=30);axes[1].legend(fontsize=8)
fig.tight_layout();fig.savefig(FIG/'04_prueba_logistica.png',dpi=160);plt.close(fig)
display(Image(filename=str(FIG/'04_prueba_logistica.png')))
'''),
md('''## 6 Inspección de probabilidades y coeficientes

La curva de calibración es descriptiva: con pocas semanas no permite afirmar calibración robusta. Los coeficientes estandarizados representan asociaciones condicionadas al resto de variables y pueden ser inestables por correlación entre rezagos; no tienen interpretación causal.'''),
code('''
from sklearn.calibration import calibration_curve
frac, mean = calibration_curve(q.exceso,q.probabilidad,n_bins=5,strategy='quantile')
fig,ax=plt.subplots(figsize=(5,4));ax.plot([0,1],[0,1],'--',color='gray');ax.plot(mean,frac,'o-',color='#17608a')
ax.set(xlabel='Probabilidad media',ylabel='Fracción observada de exceso',title='Calibración descriptiva · prueba 2024')
fig.tight_layout();fig.savefig(FIG/'05_calibracion_prueba.png',dpi=160);plt.close(fig)
display(Image(filename=str(FIG/'05_calibracion_prueba.png')))
display(coeficientes.sort_values('coeficiente_estandarizado',key=abs,ascending=False).round(4))
'''),
md('''## 7 Artefactos y lectura de resultados

Se guardaron métricas por bloque, predicciones, selección del umbral, coeficientes y un artefacto local con pipeline y metadatos. El modelo sigue entrenado solo hasta 2021: no se reajustó usando prueba ni se presenta como una versión operacional final.

Una buena métrica no resuelve las limitaciones de disponibilidad: los rezagos contienen conteos finales que pudieron notificarse más tarde. Antes de desplegar debemos revisar este supuesto con el experto y evaluar latencias o construir una versión basada en datos disponibles por notificación. Tampoco se ha validado la cobertura de semanas sin registros.

La comparación siguiente debe mantener este protocolo y reservar una evaluación nueva si se usa repetidamente 2024 para tomar decisiones. Prioridades: sensibilidad del canal, validación temporal de HistGradientBoostingClassifier, oportunidad por episodios y extensión municipal. No se afirma que la logística sea el mejor modelo por haber sido el primero.

Referencias: [validación temporal scikit-learn](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split) y [Umaña et al.](https://publichealth.jmir.org/2026/1/e79914).''')]

for name,items in [('01_preparacion_exploracion_cali.ipynb',cells),('02_primer_modelo_logistica_cali.ipynb',cells2)]:
    n=nbf.v4.new_notebook(cells=items,metadata={
        'kernelspec':{'display_name':'Python · Dengue piloto','language':'python','name':'dengue-piloto'},
        'language_info':{'name':'python','version':'3.12'}})
    dest=ROOT/'notebooks'/name;dest.parent.mkdir(exist_ok=True)
    nbf.write(n,dest)
    print(dest.name,len(items),'celdas')
