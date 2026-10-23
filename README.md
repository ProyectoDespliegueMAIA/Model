# Modelo de alerta semanal de dengue en Cali

Primer ejercicio reproducible de preparación, exploración y clasificación de exceso de notificaciones de dengue. La fuente son los 19 Excel del evento 210 de 2007–2025. Este repositorio inicia el componente de datos y modelo; todavía no incluye API ni React.

## Recorrido del ejercicio

1. Extraer Cali (76001) desde los Excel originales, conservando archivo, fila y huella del registro original.
2. Verificar evento, país, municipio y estados finales 2/3/5.
3. Parsear fechas sin inferencia ambigua y usar exclusivamente inicio de síntomas válido, sin sustituciones.
4. Marcar contradicciones con notificación y consulta como controles de calidad; no excluir por notificación anterior ni exigir que esa fecha esté disponible.
5. Reconstruir semanas domingo–sábado, incluida la semana 53.
6. Reconciliar los conteos y distinguir ausencia de registros de cero casos certificado.
7. Explorar evolución, estacionalidad y retrasos.
8. Construir el canal P75 retrospectivo y etiquetas de exceso.
9. Calcular rezagos y ventanas solo con datos anteriores al objetivo.
10. Entrenar una regresión logística regularizada, escoger el umbral en validación y comparar con referencias.

## Notebooks

- `notebooks/01_preparacion_exploracion_cali.ipynb`: preparación, auditoría, calendario, EDA, canal y variables.
- `notebooks/02_primer_modelo_logistica_cali.ipynb`: particiones, entrenamiento, referencias, métricas y diagnóstico de resultados.

Los notebooks están ejecutados y contienen tablas y figuras agregadas. Sus celdas se deben ejecutar en orden; las funciones reutilizables se encuentran en `src/dengue/pipeline.py`. El segundo notebook requiere las salidas del primero.

El notebook 02 valida y reutiliza el modelo local cuando coinciden la huella del panel, la configuración y las variables; también recalcula inferencias y métricas para comprobar los resultados guardados. Para repetir el ajuste explícitamente, cambiar `REENTRENAR=False` por `True` en su sección 3. Si el artefacto o las tablas faltan, o los datos/configuración cambiaron, se entrena de nuevo. Se puede ejecutar únicamente uno con `scripts/ejecutar_notebooks.py --solo 02_primer_modelo_logistica_cali.ipynb`.

## Entorno y ejecución en Windows

Se utilizó Python 3.12. Los paquetes principales se fijan en `requirements.txt`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Para usar otro lugar de almacenamiento de los Excel, definir `DENGUE_SOURCE_DIR` con la carpeta que contiene los archivos `Datos_2007_210.xlsx` a `Datos_2025_210.xlsx`. Sin esa variable, el extractor busca `Codigo/datos` en los directorios superiores del repositorio.

```powershell
$env:DENGUE_SOURCE_DIR = 'C:\ruta\a\los\Excel'
.\.venv\Scripts\python.exe scripts/extraer_cali.py
.\.venv\Scripts\python.exe scripts/ejecutar_notebooks.py
.\.venv\Scripts\python.exe -m pytest tests -q
```

El script de ejecución crea un kernel Jupyter local al proyecto que usa ese mismo Python. Para trabajar interactivamente, abrir los notebooks en VS Code/Jupyter y elegir el intérprete `.venv\Scripts\python.exe`; no hace falta ejecutar el generador de notebooks. `scripts/crear_notebooks.py` conserva la fuente del contenido y se usa solo para regenerarlos: hacerlo elimina sus salidas, que se recuperan ejecutándolos de nuevo.

El proceso de extracción utiliza tres procesos y no modifica los Excel. La lectura de los 19 archivos puede tardar varios minutos. El entrenamiento inicial funciona en CPU y no requiere GPU.

## Carpetas y resultados

- `configs/piloto.json`: reglas, años, municipio, canal e inclusión de casos.
- `data/raw/`: extracción local y manifiesto SHA-256 de los originales.
- `data/processed/`: microdatos validados y panel semanal completo.
- `reports/tables/`: auditorías, anomalías por archivo, métricas, particiones, coeficientes y predicciones.
- `reports/figures/`: gráficos de exploración y evaluación.
- `modelos/`: pipeline serializado y metadatos del experimento.
- `tests/`: pruebas del calendario y de la causalidad temporal de transformaciones.
- `docs/`: protocolo y lectura del primer resultado.

Los microdatos, modelos, cachés y resultados generados están excluidos de Git. Las salidas de los notebooks son agregadas. No publicar archivos individuales de pacientes. Antes de distribuir series agregadas debe verificarse la procedencia y autorización aplicable.

## Definiciones del primer modelo

La fila representa la semana objetivo. El corte nominal es el sábado inmediatamente anterior. Para esa semana, el umbral es el percentil 75 de los conteos de la misma semana epidemiológica en los cinco años anteriores, exigiendo cinco valores disponibles. Exceso significa superar estrictamente ese umbral. Es una definición operacional inicial, no un umbral oficial de epidemia ni el canal geométrico de Bortman.

Las semanas sin registros quedan con conteo epidemiológico desconocido, sin interpolación ni relleno automático con cero. Las semanas 53 permanecen en el panel; pueden quedar sin etiqueta si no hay suficiente historia. Las covariables de pacientes de la propia semana objetivo y el conteo objetivo no son predictores.

La regresión usa escalado ajustado en entrenamiento y regularización L2 con C=1. Su umbral de probabilidad se elige en 2022–2023 por F2. Se entrena hasta el año epidemiológico 2021, se prueba en 2024 y se informa 2025 como evaluación adicional. No hay reajuste posterior sobre prueba.

## Qué demuestra y qué falta

La versión vigente es `v1_ini_sin`: 160.703 registros incluidos, 992 semanas y 709 observaciones elegibles para modelado. Se separaron cinco registros sin inicio de síntomas y uno fuera de la ventana epidemiológica. La notificación está completa, pero contiene 7.069 contradicciones; inicio de síntomas tiene solo cinco faltantes y no se observaron síntomas posteriores a consulta cuando ambas fechas están disponibles. La fecha principal se eligió por su significado y coherencia, no por conseguir mejores métricas.

El ejercicio verifica un flujo trazable y obtiene métricas retrospectivas. No demuestra superioridad de la logística: persistencia la supera en validación. En v1 la logística alcanza sensibilidad de 69,4 %, precisión de 100 % y F1 de 82,0 % en validación, con umbral de probabilidad 0,45. En 2024 alerta en las 52 semanas, con las mismas decisiones que alertar siempre. En 2025 no hay positivos con esta definición y no se puede medir sensibilidad o AUC.

Se usan conteos finales por inicio de síntomas y clasificación final. No se ha reconstruido qué se sabía realmente en cada fecha; los retrasos pueden hacer que los rezagos no estuvieran completos al corte nominal. Por ello no se presenta como sistema operacional validado. Las 7.069 anomalías de notificación se conservan con bandera y no invalidan automáticamente la fecha de síntomas. Los originales no se alteraron.

Los resultados de v0 y sus notebooks/configuración se conservaron en `data/historico/cronologia_v0/`. `docs/primer_experimento.md` describe aquel experimento histórico; `docs/reconstruccion_fecha_sintomas.md` documenta la decisión actual y su comparación. Tras observar resultados de 2024 en v0, la reconstrucción es un análisis de sensibilidad por calidad de datos y no una nueva prueba independiente.

Siguientes tareas: revisar cronologías y cobertura, contrastar parámetros del canal, evaluar HistGradientBoostingClassifier con validación temporal, medir oportunidad por episodios, comparar los tres municipios y construir API/React. No utilizar reiteradamente 2024 para escoger modelos y luego seguir llamándolo prueba independiente; al tomar nuevas decisiones deben predefinirse cortes adicionales.

## Referencias

- INS, calendario epidemiológico 2025: https://portalsivigila.ins.gov.co/Documentos%20compartidos/Calendario%202025.pdf
- Umaña et al. 2026, parametrización del canal endémico: https://publichealth.jmir.org/2026/1/e79914
- scikit-learn, validación temporal: https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split


## Medellín y Villavicencio: modelos independientes

Se incorporaron Medellín (05001) y Villavicencio (50001) con las mismas reglas y diez predictores del piloto de Cali. Cada municipio tiene su propio canal histórico, escalador, coeficientes y umbral de probabilidad; no se combinan registros de ciudades para ajustar el modelo.

Notebooks, en orden para cada ciudad:

- `notebooks/01_preparacion_exploracion_medellin.ipynb`
- `notebooks/02_primer_modelo_logistica_medellin.ipynb`
- `notebooks/01_preparacion_exploracion_villavicencio.ipynb`
- `notebooks/02_primer_modelo_logistica_villavicencio.ipynb`

```powershell
.\.venv\Scripts\python.exe scripts/extraer_ciudades.py
.\.venv\Scripts\python.exe scripts/ejecutar_notebooks.py --ciudad medellin
.\.venv\Scripts\python.exe scripts/ejecutar_notebooks.py --ciudad villavicencio
.\.venv\Scripts\python.exe scripts/resumir_ciudades.py
```

Las configuraciones se encuentran en `configs/medellin.json` y `configs/villavicencio.json`. Sus salidas locales se aíslan en `ciudades/medellin/` y `ciudades/villavicencio/`, cada una con `data/`, `reports/` y `modelos/`. La carpeta `ciudades/` está excluida de Git. Las rutas de Cali se conservan. El resumen agregado y sus limitaciones se documentan en `docs/resumen_tres_ciudades.md`.

Para regenerar los notebooks de una sola ciudad, usar `scripts/crear_notebooks.py --ciudad medellin` o `--ciudad villavicencio`; después ejecutarlos para recuperar las salidas. El generador no cambia los notebooks de las otras ciudades. No es necesario regenerarlos para trabajar interactivamente.


## Evaluación adicional de Ibagué

Ibagué (73001) se evalúa como candidata, conservando todos los experimentos anteriores. Su inclusión no cambia automáticamente la selección de tres ciudades. Usa `configs/ibague.json` y salidas aisladas en `ciudades/ibague/`.

```powershell
.\.venv\Scripts\python.exe scripts/extraer_ciudades.py --ciudad ibague
.\.venv\Scripts\python.exe scripts/ejecutar_notebooks.py --ciudad ibague
.\.venv\Scripts\python.exe scripts/evaluar_ibague.py
```

Los notebooks son `01_preparacion_exploracion_ibague.ipynb` y `02_primer_modelo_logistica_ibague.ipynb`. El informe agregado se genera en `docs/evaluacion_ibague.md`. La comparación distingue cobertura y disponibilidad de clases de las métricas predictivas. El extractor admite también `--ciudad medellin` y `--ciudad villavicencio` para trabajar con un solo municipio sin reextraer los otros.
