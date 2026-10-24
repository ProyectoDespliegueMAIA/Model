# Registro de experimentos de dengue en MLflow

## Qué se registra

El experimento `dengue_exceso_semanal` reúne las cuatro ciudades evaluadas: Cali, Medellín, Villavicencio e Ibagué. Se conserva Medellín como referencia; registrarla no modifica la selección de municipios del proyecto.

Por ciudad se registran cinco ejecuciones, veinte en total:

1. Regresión logística con umbral seleccionado por F2 en validación.
2. La misma logística con umbral de decisión 0,5.
3. Persistencia del último conteo contra el umbral histórico de la semana objetivo.
4. Probabilidad constante igual a la prevalencia de entrenamiento.
5. Alerta permanente.

Hay un clasificador ajustado por ciudad: las dos ejecuciones de logística comparten coeficientes y difieren en la regla de decisión. Las referencias son reglas, no modelos ajustados adicionales. Estas importaciones no llaman a `fit()` ni modifican los archivos originales.

## Ejecutar completamente en Docker

Desde la raíz del repositorio:

```powershell
docker compose -f docker/mlflow/compose.yaml up -d --wait

# Comprobar primero; sin escribir en MLflow.
docker compose -f docker/mlflow/compose.yaml run --rm importador python scripts/importar_experimentos.py --solo-verificar

# Identifica la revisión disponible al importar; no la atribuye al ajuste original.
$env:DENGUE_GIT_COMMIT = git rev-parse HEAD
docker compose -f docker/mlflow/compose.yaml run --rm importador
```

Para una sola ciudad:

```powershell
docker compose -f docker/mlflow/compose.yaml run --rm importador python scripts/importar_experimentos.py --ciudades ibague
```

El importador usa la imagen existente y monta el repositorio como **solo lectura**. Genera archivos intermedios en el almacenamiento temporal del contenedor y envía los resultados al servidor por HTTP. El SDK permanece en Docker. No se necesita reconstruir la imagen al editar el importador, porque lee el código montado.

Repetir la misma importación verifica y reutiliza las ejecuciones ya terminadas. La identidad incluye parámetros, métricas y huellas de los artefactos; no depende de la carpeta temporal. Si cambia el contenido, se registra otra ejecución. Usar un solo importador a la vez. Los intentos fallidos se conservan como `FAILED`; no se reutilizan como resultados válidos.

## Verificación previa y posterior

Antes de crear una ejecución se comprueban todas las ciudades solicitadas:

- Correspondencia de panel, municipio, configuración, variables, versión y metadatos del modelo.
- Separación temporal y escalador ajustado solo con entrenamiento.
- Predicciones originales y métricas de los cinco métodos, incluyendo matrices de confusión.
- Reproducción de la rejilla de F2 y del umbral seleccionado con validación.

Las huellas históricas del panel se generaron en Windows. La validación admite las serializaciones LF y CRLF del mismo contenido para usar Linux; no modifica las huellas guardadas ni acepta cambios de valores. Además se conserva la huella de los bytes del CSV original.

Después del registro se consultan los parámetros y métricas guardados, se descargan los artefactos para verificar sus huellas y se recuperan los modelos MLflow para comprobar sus probabilidades frente a los originales. Las comprobaciones se repiten al reutilizar una ejecución.

## Cómo comparar en la interfaz

Abrir [MLflow](http://localhost:5000), elegir **Experiments** y después `dengue_exceso_semanal`. Filtrar primero por ciudad, por ejemplo:

```text
tags.ciudad = 'Ibagué'
```

Seleccionar ejecuciones y comparar estas columnas:

| Columna | Lectura |
| --- | --- |
| `validacion.sensibilidad` | Proporción de excesos detectados |
| `validacion.precision` | Proporción de alertas correctas |
| `validacion.f1` / `validacion.f2` | Balance de detección y precisión |
| `validacion.especificidad` | Reconocimiento de semanas sin exceso |
| `validacion.fp` / `validacion.fn` | Falsas alarmas y excesos omitidos |
| `validacion.n` / `validacion.prevalencia` | Tamaño y composición del bloque |

Las métricas usan escala 0–1, excepto conteos. Cada periodo tiene su prefijo: `entrenamiento.`, `validacion.`, `prueba_2024.` y `adicional_2025.`. Las métricas indefinidas no se envían como cero: se enumeran en `trazabilidad/manifiesto.json` y permanecen vacías en la interfaz.

La comparación entre municipios es descriptiva. No ordenar todos por F1 para declarar una ciudad o un modelo superior: cada municipio tiene distinta prevalencia y su propio umbral histórico. Los resultados de entrenamiento tampoco prueban generalización.

## Artefactos y trazabilidad

Cada ejecución incluye configuración, regla de decisión, particiones, métricas, predicciones semanales agregadas, controles, matrices de confusión, diagnóstico y gráficos exploratorios. Se incluyen manifiesto SHA-256 de fuentes y copia del código disponible al importar. La logística agrega coeficientes, el artefacto original y un modelo MLflow con firma de entrada y ejemplo de cinco filas de predictores semanales.

No se suben microdatos individuales, identificadores de pacientes ni carpetas completas. La selección de archivos es explícita. El registro conserva el entorno real de importación y las dependencias del proyecto como referencias distintas; no atribuye esas versiones al entrenamiento original.

El modelo MLflow devuelve las dos probabilidades de clase (`predict_proba`); la columna 1 corresponde a exceso. El umbral está en los parámetros y en `trazabilidad/regla_decision.json`, y debe aplicarse después para generar una alerta. El identificador del modelo está en la etiqueta `modelo_uri`. Desde un cliente con MLflow:

```python
modelo = mlflow.sklearn.load_model(modelo_uri)
probabilidad_exceso = modelo.predict_proba(X)[:, 1]
alerta = probabilidad_exceso >= umbral
```

Todas las ejecuciones llevan `tipo_ejecucion=importado` y `sin_reentrenamiento=true`. La hora de MLflow corresponde al registro actual; la fecha original de ajuste no estaba registrada. El commit de importación tampoco se presenta como commit del entrenamiento. Estos modelos no se promueven a producción ni se registran como candidatos finales automáticamente.

## Siguiente paso

Las referencias actuales quedan conservadas. Falta definir varios cortes de validación temporal e integrar esta función de registro en los nuevos ajustes de logística, HistGradientBoosting y red neuronal. Los bloques 2024 y 2025 ya observados son evaluación retrospectiva: no usarlos repetidamente para seleccionar hiperparámetros y seguir presentándolos como pruebas independientes. Persiste la limitación de disponibilidad real de los conteos al corte nominal.

Referencia: [API de MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking/tracking-api/).
