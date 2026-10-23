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

**Pregunta del modelo:** ¿Podemos predecir, a partir de los casos de dengue de las semanas anteriores y la época del año, si los casos de la próxima semana en Cali superarán el umbral histórico correspondiente a esa semana?

| Elemento | Información utilizada | Función |
|---|---|---|
| Predictores X | Semanas recientes y posición de la semana objetivo en el ciclo anual | Información con la que el modelo intenta anticipar el resultado |
| Umbral histórico | Misma semana epidemiológica en los cinco años anteriores | Referencia que define qué llamamos exceso |
| Etiqueta y | Conteo observado del objetivo comparado con su umbral | Respuesta que se aprende en entrenamiento y se verifica después |

El modelo posterior estimará una probabilidad de exceso, no un número exacto de casos ni un diagnóstico individual. Construir la etiqueta con datos observados de la semana objetivo no autoriza usarlos como predictores. El umbral en número de casos es distinto del umbral de probabilidad que activa una alerta.

Ejecutar las celdas en orden. Los cálculos están en `src/dengue/pipeline.py` para reutilizarlos y probarlos. No se muestran filas individuales de pacientes. Los originales permanecen intactos.

**Etapas:** extracción → auditoría → calendario → exploración → canal y etiqueta → variables de historia previa → exportación. El notebook 02 realiza el primer entrenamiento después de estas comprobaciones. Las variables representan asociaciones predictivas, no efectos causales demostrados.'''),
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

Esta comparación histórica define la etiqueta; no sustituye los rezagos recientes que recibirá el modelo. El umbral solo consulta años anteriores. El conteo objetivo se conoce después y permite evaluar si hubo exceso; no se incluye en X.

Es una definición operacional inicial, no una declaración oficial de epidemia ni una reproducción del canal geométrico de Bortman. Cinco observaciones por semana producen umbrales inestables; queda pendiente el análisis de sensibilidad. Los años iniciales sirven para inicializar el canal.

**Semana 53:** no depende exclusivamente de que el año sea bisiesto. Sus registros y su posición en la secuencia se conservan; si falta historia suficiente, `umbral_casos` y `exceso` quedan desconocidos, no en cero. No se combina automáticamente con la semana 52. En la semana 1 posterior, el rezago de una semana sí utiliza la semana 53 cuando existe. En nuestro panel las cuatro semanas 53 no tienen cinco antecedentes válidos dentro de su ventana, por lo que no se usan como objetivos etiquetados.

Por ejemplo, el valor `casos=30` en 2025/53 representa treinta notificaciones agrupadas en una fila semanal, no treinta semanas u observaciones de entrenamiento. La tabla siguiente permite comprobar la diferencia entre conservar el conteo y disponer de una etiqueta.'''),
code('''
panel = agregar_canal(panel,cfg)
display(panel.groupby('anio_epi').agg(etiquetadas=('exceso','count'),positivas=('exceso','sum')))
display(panel.loc[panel.exceso.notna(), ['anio_epi','semana_epi','casos','n_anios_canal','umbral_casos','exceso']].head(10))
assert panel.loc[panel.exceso.notna(),'n_anios_canal'].ge(5).all()
display(panel.loc[panel.semana_epi.eq(53),
    ['anio_epi','semana_epi','inicio_semana','fin_semana','casos','n_anios_canal','umbral_casos','exceso']])
'''),
md('''### 7.1 Ejemplo histórico de las dos referencias temporales

Para ilustrar la semana 20 de 2023, mostramos por separado las doce semanas inmediatamente anteriores y la semana 20 de 2018–2022. Las primeras son la fuente de rezagos y ventanas; las segundas forman el umbral. La tabla del objetivo usa su conteo observado únicamente para verificar la etiqueta: este ejemplo no es una predicción del modelo.'''),
code('''
pos = panel.index[panel.anio_epi.eq(2023) & panel.semana_epi.eq(20)][0]
objetivo = panel.loc[pos]
recientes = panel.iloc[max(0,pos-12):pos][['anio_epi','semana_epi','inicio_semana','fin_semana','casos']]
historico = panel.loc[
    panel.anio_epi.between(objetivo.anio_epi-cfg['ventana_canal_anios'],objetivo.anio_epi-1)
    & panel.semana_epi.eq(objetivo.semana_epi),
    ['anio_epi','semana_epi','inicio_semana','casos']]
print('A. Historia reciente: fuente de los predictores')
display(recientes)
print('B. Misma semana de años anteriores: fuente del umbral')
display(historico)
print('C. Semana objetivo: comparación retrospectiva para obtener la etiqueta')
display(panel.loc[[pos],['anio_epi','semana_epi','casos','umbral_casos','exceso']])
assert recientes.fin_semana.max() < objetivo.inicio_semana
assert historico.anio_epi.lt(objetivo.anio_epi).all()
assert np.isclose(historico.casos.quantile(cfg['cuantil_canal']),objetivo.umbral_casos)
'''),
md('''## 8 Variables disponibles antes de la semana objetivo

La fila t corresponde a la semana a predecir; su corte nominal es el sábado inmediatamente anterior. Se usan conteos de t−1, t−2, t−3, t−4, t−8 y t−12, media/desviación de las cuatro semanas anteriores y estacionalidad conocida del objetivo. Se exige historia completa para estas variables; no se interpolan faltantes.

La hipótesis de trabajo es que la historia reciente ayuda a anticipar el exceso relativo a ese umbral estacional. Un aumento frente a la semana anterior no significa necesariamente exceso, y puede haber exceso aun cuando el conteo esté bajando.

Se excluyen como predictores los conteos del objetivo, su etiqueta, su umbral y las características de pacientes de esa semana. El umbral se guarda para interpretar la etiqueta y construir la referencia de persistencia. Incluso los rezagos finales deben interpretarse como evaluación retrospectiva, pues el retraso de notificación impide afirmar que estuvieran completos al corte.'''),
code('''
panel = agregar_features(panel)
display(panel.loc[panel.elegible_modelo,['inicio_semana','corte_prediccion',*FEATURES,'exceso']].head())
display(pd.DataFrame({'variable':FEATURES,'origen':['historia anterior']*8+['calendario conocido']*2}))
annual, summary = exportar_eda(raw,micro,auditoria,calidad,panel)
display(annual)
display(pd.Series({k:v for k,v in summary.items() if k!='diagnostico_por_archivo'},name='Resultado de preparación').to_frame())
assert not set(FEATURES).intersection({'casos','exceso','umbral_casos','casos_confirmados','hospitalizados'})
assert panel.loc[panel.elegible_modelo,FEATURES+['exceso']].notna().all().all()
'''),
md('''### 8.1 Diccionario del panel y selección de campos

El panel semanal exportado tiene 28 columnas en esta versión. Solo diez son predictores y `exceso` es la respuesta. Los microdatos individuales constituyen otra tabla para auditoría. Elegir un campo como predictor no demuestra significancia estadística ni una mejora: su aporte debe comprobarse en validación temporal.'''),
code('''
significados = {
    'anio_epi':'Año epidemiológico; identifica y separa bloques temporales.',
    'semana_epi':'Número de semana epidemiológica.',
    'inicio_semana':'Domingo de inicio de la semana.',
    'fin_semana':'Sábado de fin de la semana.',
    'semanas_en_anio':'52 o 53; interviene en la codificación del ciclo anual.',
    'n_registros':'Filas incluidas; cero significa ausencia de filas, no cero casos certificado.',
    'casos_confirmados':'Registros de estados finales 3 o 5.',
    'hospitalizados':'Registros con hospitalización indicada.',
    'retraso_mediana':'Mediana de retrasos de notificación no negativos disponibles.',
    'ultima_notificacion':'Última notificación entre los registros de la semana.',
    'semana_con_registros':'Indica presencia de registros, sin certificar cobertura completa.',
    'casos':'Conteo analítico; desconocido cuando no hay registros.',
    'cod_municipio':'Código de Cali, 76001.',
    'n_anios_canal':'Antecedentes válidos disponibles para el umbral de esa semana.',
    'umbral_casos':'P75 de la misma semana en los cinco años anteriores.',
    'exceso':'Etiqueta: 1 si casos supera el umbral, 0 en otro caso; desconocida si falta información.',
    **{f'lag_{k}':f'Conteo de {k} semana(s) antes de la semana objetivo.' for k in [1,2,3,4,8,12]},
    'media_4':'Media de las cuatro semanas anteriores, sin incluir el objetivo.',
    'std_4':'Desviación estándar de las cuatro semanas anteriores.',
    'semana_sin':'Seno de la posición del objetivo en el ciclo anual.',
    'semana_cos':'Coseno de la posición del objetivo en el ciclo anual.',
    'corte_prediccion':'Sábado anterior al objetivo; corte nominal retrospectivo.',
    'elegible_modelo':'Hay etiqueta y todas las variables predictoras disponibles.'}
assert set(significados)==set(panel.columns)
diccionario = pd.DataFrame([
    {'columna':c,'significado':significados[c],
     'uso':('Predictor X' if c in FEATURES else 'Etiqueta y' if c=='exceso'
            else 'Construcción de etiqueta' if c in ['n_anios_canal','umbral_casos']
            else 'Observación histórica' if c=='casos' else 'Identificación o auditoría')}
    for c in panel.columns])
display(diccionario)
print(f'Panel: {panel.shape[0]} filas, {panel.shape[1]} columnas; X: {len(FEATURES)} predictores; y: exceso.')
diccionario.to_csv(ROOT/'reports/tables/diccionario_panel_semanal.csv',index=False)
'''),
md('''## 9 Cierre de la fase exploratoria y siguiente paso

Se exportaron auditoría, manifiesto de fuentes, microdatos locales, panel completo y figuras. La suma se reconcilia después de exclusiones explícitas. Se conservan semanas sin registros como desconocidas y la semana 53 sin eliminaciones artificiales.

**Siguiente notebook:** regresión logística regularizada, entrenamiento hasta 2021, validación 2022–2023, prueba 2024 y evaluación adicional 2025. No se ajusta el modelo con las métricas de prueba. Pendientes: revisión del caso/fecha con el experto, cobertura externa, sensibilidad del canal, simulación con disponibilidad real, clima y extensión a otros municipios.

Referencias: [calendario INS 2025](https://portalsivigila.ins.gov.co/Documentos%20compartidos/Calendario%202025.pdf) y [Umaña et al. 2026](https://publichealth.jmir.org/2026/1/e79914).''')]

cells2=[
md('''# 02 Primer entrenamiento de alerta semanal de dengue

Este ejercicio entrena una **regresión logística con penalización L2** para estimar la probabilidad de exceso en la semana siguiente al corte nominal, según la definición P75 del notebook 01. Se compara con referencias simples. HistGradientBoostingClassifier queda para la siguiente comparación; todavía no hay búsqueda entre familias de modelos.

**Pregunta:** ¿Podemos predecir, a partir de los casos de dengue de las semanas anteriores y la época del año, si los casos de la próxima semana en Cali superarán el umbral histórico correspondiente a esa semana?

Los diez predictores proceden de semanas recientes y del calendario. El P75 de la misma semana de años anteriores define la etiqueta `exceso`, pero esos conteos anuales no entran directamente como predictores. El modelo devuelve una probabilidad; una regla posterior la transforma en alerta. No se pronostica el número exacto de casos.

**Ejecución:** por defecto se valida y reutiliza el modelo local si coincide con los datos, configuración y variables actuales. Si falta o cambió alguno de esos elementos, se entrena de nuevo. Para repetir explícitamente el ajuste, establecer `REENTRENAR=True` en la sección 3. Repetir el mismo ajuste no convierte a 2024 en una prueba nueva.

La evaluación es retrospectiva sobre notificaciones finales: no demuestra rendimiento en tiempo real ni capacidad para detectar brotes definidos por una fuente externa. Ejecutar primero el notebook 01.'''),
md('## 1 Entorno y carga del panel validado'),code(setup),
code('''
panel = pd.read_csv(ROOT/'data/processed/cali_panel_semanal.csv',
    parse_dates=['inicio_semana','fin_semana','corte_prediccion'])
assert cfg['fecha_principal']=='INI_SIN' and cfg['politica_fecha_faltante']=='excluir_sin_sustituir'
assert cfg['horizonte_semanas']==1, 'Este experimento implementa un horizonte de una semana.'
assert not panel.duplicated(['anio_epi','semana_epi']).any()
assert panel.inicio_semana.diff().dropna().eq(pd.Timedelta(days=7)).all()
assert panel.corte_prediccion.eq(panel.inicio_semana-pd.Timedelta(days=1)).all()
reconstruido = agregar_features(agregar_canal(panel,cfg))
np.testing.assert_allclose(panel[FEATURES+['umbral_casos','exceso']],
    reconstruido[FEATURES+['umbral_casos','exceso']],equal_nan=True,atol=1e-12)
assert panel.elegible_modelo.eq(reconstruido.elegible_modelo).all()
assert set(FEATURES).isdisjoint({'casos','umbral_casos','exceso','casos_confirmados','hospitalizados'})
datos = panel.loc[panel.elegible_modelo].copy()
print('Observaciones elegibles:',len(datos))
display(datos.groupby('anio_epi').exceso.agg(['count','sum','mean']).rename(columns={'sum':'positivos','mean':'prevalencia'}))
'''),
md('''## 2 Partición cronológica y propósito de cada bloque

- Hasta 2021: ajuste del escalador y de los coeficientes.
- 2022–2023: elección del umbral de probabilidad, maximizando F2 en una rejilla predefinida; en empates se prefiere el umbral mayor.
- 2024: evaluación de referencia, sin usarla para ajustar coeficientes o escoger umbral en esta ejecución. Ya observada en revisiones anteriores; no es una nueva prueba independiente.
- 2025: evaluación adicional; las cifras requieren revisar cobertura y cambio de comportamiento.

El canal de cada fila se calcula con sus años anteriores. La validación y prueba pueden usar semanas ya observadas anteriores dentro de su propio bloque, sin reentrenar: se simulan orígenes móviles de un paso con datos finales. No equivale a predecir todo el bloque desde un único corte. No hay escalado ni selección de variables con prueba.'''),
code('''
particiones_previas = datos.assign(bloque=np.select(
    [datos.anio_epi<=cfg['fin_entrenamiento'],
     datos.anio_epi.between(cfg['fin_entrenamiento']+1,cfg['fin_validacion']),
     datos.anio_epi.eq(cfg['anio_prueba']),datos.anio_epi.eq(cfg['anio_adicional'])],
    ['entrenamiento','validacion',f"prueba_{cfg['anio_prueba']}",f"adicional_{cfg['anio_adicional']}"],
    default='fuera_del_diseno'))
assert particiones_previas.bloque.ne('fuera_del_diseno').all(), 'Hay años sin bloque de evaluación definido.'
display(particiones_previas.groupby('bloque').agg(n=('exceso','size'),
    positivos=('exceso','sum'),inicio=('inicio_semana','min'),fin=('fin_semana','max')))
print('Variables:',FEATURES)
'''),
md('''## 3 Entrenar el modelo y las referencias

El pipeline ajusta `StandardScaler` con entrenamiento y después `LogisticRegression(C=1, penalty L2 por defecto, solver=lbfgs)`. Los hiperparámetros se fijan antes de mirar prueba. No se aplica SMOTE ni se mezclan fechas.

Referencias: probabilidad constante igual a prevalencia de entrenamiento; persistencia de conteo, que pronostica el último conteo observado y lo contrasta con el umbral conocido del objetivo; y la regla trivial de alertar siempre. Las decisiones binarias de referencia no son probabilidades calibradas. Se informa también la logística a umbral 0,5 para separar el efecto del modelo del efecto del umbral.'''),
code('''
import joblib
from dengue.validacion_modelo import coincide_artefacto, verificar_resultados
REENTRENAR = False
version = cfg['version_experimento']
ruta_artefacto = ROOT/f'modelos/logistica_cali_{version}.joblib'
tablas = ROOT/'reports/tables'
archivos = ['metricas_logistica.csv','predicciones_logistica.csv','particiones_temporales.csv',
            'coeficientes_logistica.csv','seleccion_umbral_validacion.csv']
artefacto = joblib.load(ruta_artefacto) if ruta_artefacto.exists() else None
reutilizar = (not REENTRENAR and artefacto is not None
    and coincide_artefacto(panel,cfg,artefacto['metadata'])
    and all((tablas/f).exists() for f in archivos))
if reutilizar:
    model, metadata = artefacto['pipeline'], artefacto['metadata']
    metricas = pd.read_csv(tablas/'metricas_logistica.csv')
    predicciones = pd.read_csv(tablas/'predicciones_logistica.csv',parse_dates=['inicio_semana'])
    particiones = pd.read_csv(tablas/'particiones_temporales.csv')
    coeficientes = pd.read_csv(tablas/'coeficientes_logistica.csv')
    print('Modelo reutilizado: coinciden panel, configuración, variables y versión. No se reentrenó.')
else:
    model, metricas, predicciones, particiones, coeficientes = entrenar_logistica(panel,cfg)
    metadata = joblib.load(ruta_artefacto)['metadata']
    print('Modelo entrenado: ajuste solicitado o artefacto/resultados ausentes o incompatibles.')
controles = verificar_resultados(panel,cfg,model,metadata,metricas,predicciones,particiones,coeficientes)
display(controles)
display(particiones)
tabla_umbrales = pd.read_csv(tablas/'seleccion_umbral_validacion.csv')
from sklearn.metrics import fbeta_score
val = datos.loc[datos.anio_epi.between(cfg['fin_entrenamiento']+1,cfg['fin_validacion'])]
prob_val = model.predict_proba(val[FEATURES])[:,1]
np.testing.assert_allclose(tabla_umbrales.f2_validacion,
    [fbeta_score(val.exceso,prob_val>=t,beta=2,zero_division=0) for t in tabla_umbrales.umbral])
display(tabla_umbrales.sort_values(['f2_validacion','umbral'],ascending=False).head(6))
print('Umbral de probabilidad validado:',round(metadata['umbral_probabilidad'],2))
'''),
md('''### 3.1 Probabilidad, alerta y comprobación del resultado

El modelo estima una probabilidad de exceso. La alerta se activa si esa probabilidad alcanza el umbral elegido con validación. `umbral_casos` está en número de notificaciones y define el evento que queremos anticipar; `umbral_probabilidad` es un parámetro de decisión aplicado a la salida del clasificador.

La tabla siguiente ilustra semanas de validación: el corte y las variables preceden al objetivo; los casos y la etiqueta observada solo se muestran para comprobar después el resultado. Es un ejemplo retrospectivo, no una alerta actual emitida en tiempo real.'''),
code('''
ejemplo = predicciones.loc[predicciones.bloque.eq('validacion')
    & predicciones.modelo.eq('logistica_umbral_validado')].head(5).copy()
ejemplo['inicio_semana'] = pd.to_datetime(ejemplo.inicio_semana)
ejemplo = ejemplo.merge(panel[['inicio_semana','corte_prediccion']],on='inicio_semana',validate='one_to_one')
ejemplo['umbral_probabilidad'] = metadata['umbral_probabilidad']
display(ejemplo[['corte_prediccion','inicio_semana','probabilidad','umbral_probabilidad',
                'prediccion','casos','umbral_casos','exceso']].rename(columns={
    'inicio_semana':'semana_objetivo','prediccion':'alerta','casos':'casos_observados_despues',
    'exceso':'etiqueta_observada_despues'}).round(4))
'''),
md('''## 4 Métricas fuera de entrenamiento

Sensibilidad: qué proporción de semanas con exceso detectamos. Precisión: qué proporción de alertas corresponde a exceso. AP resume la curva precisión–recobrado (no es el área trapezoidal). Brier evalúa error de probabilidad; menor es mejor. La matriz de confusión permite contar falsas alarmas y excesos omitidos.

La evaluación se hace contra nuestra etiqueta histórica, no contra una lista independiente de brotes. Los resultados de entrenamiento son descriptivos y no evidencia de generalización. Las AUC se dejan vacías si el bloque contiene una sola clase; sensibilidad y F1/F2 se dejan vacíos cuando no hay positivos reales. La precisión queda vacía cuando no se emitió ninguna alerta.

**Lectura crítica:** revisar prevalencia y matriz de confusión junto a sensibilidad y F1. Si un bloque tiene casi todas las semanas positivas, alertar siempre puede obtener métricas altas. La persistencia es una referencia exigente. La reconstrucción v1 responde a una decisión de calidad de datos, no a elegir el resultado que mejore prueba. Como ya se observaron resultados de 2024 en v0, la comparación de versiones es un análisis de sensibilidad, no una nueva prueba independiente.'''),
code('''
cols=['bloque','modelo','n','prevalencia','umbral_probabilidad','sensibilidad','especificidad','precision','f1','f2','pr_auc_AP','roc_auc','brier','tn','fp','fn','tp']
display(metricas.loc[metricas.bloque.ne('entrenamiento'),cols].round(4))
print('Resumen de validación: compara capacidad predictiva con una referencia sencilla.')
resumen = metricas.loc[metricas.bloque.eq('validacion') & metricas.modelo.isin(
    ['logistica_umbral_validado','persistencia_conteo']),
    ['modelo','sensibilidad','precision','f1','fp','fn']].copy()
for c in ['sensibilidad','precision','f1']:
    resumen[c] = 100*resumen[c]
display(resumen.rename(columns={'sensibilidad':'sensibilidad (%)','precision':'precisión (%)','f1':'F1 (%)',
    'fp':'falsas alarmas','fn':'excesos omitidos'}).round(1))
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

Se verificaron métricas por bloque, predicciones, selección del umbral, coeficientes y el artefacto local con metadatos. Si no hubo cambios en los datos o la configuración, se reutilizó el modelo; la salida de la sección 3 informa la acción ejecutada. Se comprobó la huella del panel, el ajuste del escalador solo con entrenamiento y la coincidencia entre inferencias actuales, matrices de confusión y métricas guardadas. El modelo sigue ajustado solo hasta 2021; no se presenta como versión operacional final.

Una buena métrica no resuelve las limitaciones de disponibilidad: los rezagos contienen conteos finales que pudieron notificarse más tarde. Antes de desplegar debemos revisar este supuesto con el experto y evaluar latencias o construir una versión basada en datos disponibles por notificación. Tampoco se ha validado la cobertura de semanas sin registros.

La comparación siguiente debe mantener este protocolo y reservar una evaluación nueva si se usa repetidamente 2024 para tomar decisiones. Prioridades: sensibilidad del canal, validación temporal de HistGradientBoostingClassifier, oportunidad por episodios y extensión municipal. No se afirma que la logística sea el mejor modelo por haber sido el primero.

Referencias: [validación temporal scikit-learn](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split) y [Umaña et al.](https://publichealth.jmir.org/2026/1/e79914).''')]

import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--solo', help='Nombre exacto del notebook de la ciudad seleccionada')
parser.add_argument('--ciudad', choices=['cali','medellin','villavicencio','ibague'], default='cali')
args=parser.parse_args()
for name,items in [('01_preparacion_exploracion_cali.ipynb',cells),('02_primer_modelo_logistica_cali.ipynb',cells2)]:
    if args.ciudad != 'cali':
        import re, copy
        slug=args.ciudad
        nombre={'medellin':'Medellín','villavicencio':'Villavicencio','ibague':'Ibagué'}[slug]
        codigo={'medellin':'05001','villavicencio':'50001','ibague':'73001'}[slug]
        items=copy.deepcopy(items)
        name=name.replace('cali',slug)
        for cell in items:
            text=re.sub(r'(?<![a-z])cali(?![a-z])',slug,cell.source.replace('Cali',nombre)).replace('76001',codigo)
            text=text.replace('scripts/extraer_'+slug+'.py','scripts/extraer_ciudades.py --ciudad '+slug)
            text=text.replace('annual, summary = exportar_eda(raw,micro,auditoria,calidad,panel)',
                              'annual, summary = exportar_eda(raw,micro,auditoria,calidad,panel,cfg)')
            text=re.sub(r"ROOT\s*/\s*((?:f)?['\"])(data/|reports/|modelos/)",r"SALIDA/\1\2",text)
            if cell.cell_type=='code' and 'cfg = config()' in text:
                text=re.sub(r"FIG = SALIDA\s*/",f"SALIDA = raiz_salida(config('{slug}'))\nFIG = SALIDA/",text)
                text=text.replace('cfg = config()',f"cfg = config('{slug}')")
            text=text.replace('La comparación de municipios y el clima quedan para etapas siguientes.',
                              'Este municipio se analiza y entrena por separado; el clima queda para etapas siguientes.')
            text=text.replace('y extensión a otros municipios','y comparación entre municipios')
            text=text.replace('y extensión municipal','y comparación municipal')
            if cell.cell_type=='markdown':
                text=text.replace('Ya observada en revisiones anteriores; no es una nueva prueba independiente.',
                                  'Se reserva para evaluar después del ajuste y de seleccionar el umbral en validación.')
                text=text.replace('Como ya se observaron resultados de 2024 en v0, la comparación de versiones es un análisis de sensibilidad, no una nueva prueba independiente.',
                                  'En Cali 2024 ya fue observado; en este municipio esta es la primera evaluación. No se usa prueba para seleccionar el umbral.')
            if cell.cell_type=='code' and 'workspace = next(' in text:
                text="""cobertura = panel.groupby('anio_epi').agg(
    semanas=('semana_epi','size'), semanas_con_registros=('semana_con_registros','sum'),
    notificaciones=('n_registros','sum'))
cobertura['pct_semanas_con_registros'] = 100*cobertura.semanas_con_registros/cobertura.semanas
display(cobertura.round(2))
print('Presencia de registros no certifica cobertura completa. No imputamos ceros.')"""
            if cell.cell_type=='markdown' and 'Contraste con la serie recibida' in text:
                text='## 4 Cobertura temporal por municipio\n\nRevisamos presencia de registros por año; las semanas sin filas permanecen desconocidas.'
            text=text.replace("parse_dates=['inicio_semana','fin_semana','corte_prediccion']",
                              "dtype={'cod_municipio':'string'}, parse_dates=['inicio_semana','fin_semana','corte_prediccion']")
            text=text.replace('filas_'+slug,'filas_municipio')
            if cell.cell_type=='code' and 'tabla_umbrales =' in text:
                text += """
positivos_validacion = int(val.exceso.sum())
print('Semanas con exceso en validación:', positivos_validacion)
if positivos_validacion < 10:
    print('LIMITACIÓN: pocos excesos en validación; el umbral y la sensibilidad son inestables.')
if tabla_umbrales.f2_validacion.max() == 0:
    print('LIMITACIÓN: F2 es cero en toda la rejilla. El umbral resulta del desempate; no acredita capacidad de alerta.')
print('Las limitaciones se conservan como resultado del primer experimento, sin ajustar con prueba.')
"""
            cell.source=text
    if args.solo and name!=args.solo:
        continue
    n=nbf.v4.new_notebook(cells=items,metadata={
        'kernelspec':{'display_name':'Python · Dengue piloto','language':'python','name':'dengue-piloto'},
        'language_info':{'name':'python','version':'3.12'}})
    dest=ROOT/'notebooks'/name;dest.parent.mkdir(exist_ok=True)
    nbf.write(n,dest)
    print(dest.name,len(items),'celdas')
