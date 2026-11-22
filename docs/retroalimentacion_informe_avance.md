# Retroalimentación del informe de avance

Registro del 13 de noviembre de 2026. Calificación confirmada por el usuario: 68/100. Coincide con la suma de los siete criterios de la rúbrica.

| Criterio | Puntaje | Acción para la entrega final |
|---|---:|---|
| Propuesta | 8/10 | Concentrar la formulación del problema en la introducción. Justificar con datos la inclusión inicial de Cali, Medellín, Villavicencio e Ibagué y distinguirla de la selección final. |
| Datos | 5/15 | Mostrar una tabla por variable con fuente, fórmula, semanas usadas y disponibilidad al corte. Explicitar la etiqueta binaria y los controles contra fuga. |
| Construcción | 20/35 | Especificar modelos, entradas, configuración y protocolo temporal. Evaluar una variante con variables ambientales si se pueden obtener con cobertura y disponibilidad verificables. |
| Resultados | 10/10 | Conservar matrices y acortar títulos. Mostrar el soporte de las métricas, falsas alertas y excesos omitidos. |
| Análisis | 15/20 | Comparar contra persistencia y contextualizar las métricas con estudios de alerta temprana, indicando horizonte, definición del evento y diferencias de evaluación. |
| Referencias | 5/5 | Conservar la calidad de las fuentes y vincularlas con decisiones y resultados. |
| Presentación | 5/5 | Hacer visibles los pasos metodológicos y revisar el archivo exacto que se va a entregar. |

Datos y construcción concentran 25 de los 32 puntos descontados en las capturas. Priorizar esos criterios antes de ampliar el número de modelos.

Para la semana objetivo t, definir exceso como conteo observado estrictamente superior al P75 de la misma semana epidemiológica en los cinco años anteriores. Preservar la distinción entre ese umbral de casos y el umbral de probabilidad de alerta. Mostrar un ejemplo de la semana 20 donde la ventana reciente usa las semanas 16 a 19 y la estacionalidad describe la semana 20. Ajustar transformaciones y modelos dentro de cada corte de entrenamiento y seleccionar hiperparámetros y umbrales dentro del período de desarrollo. Los resultados de 2024 y 2025 ya se examinaron. Documentar el carácter retrospectivo de los conteos y su posible demora de consolidación.

Orden de trabajo recomendado: fijar el protocolo y la procedencia de variables, comparar persistencia y regresión logística con la misma evaluación, medir el aporte de las variables ambientales con y sin ellas sobre las mismas semanas, y agregar modelos complejos según el tiempo y la evidencia. Usar las fechas del proyecto para priorizar el despliegue del 26, la sustentación del 27 y el informe final del 29 de noviembre de 2026.
