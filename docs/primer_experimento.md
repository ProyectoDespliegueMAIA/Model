# Primer experimento de clasificación semanal de exceso en Cali

**Documento histórico de v0.** La exclusión por notificación anterior y las cifras de este documento fueron sustituidas por la versión `v1_ini_sin`. Consultar `reconstruccion_fecha_sintomas.md` para la metodología y resultados vigentes. Se conserva este texto para trazabilidad.

Este documento acompaña los notebooks del avance y separa las decisiones de preparación de las conclusiones del primer modelo. Los resultados son retrospectivos y provisionales.

## Preparación ejecutada

Se extrajeron 160.709 registros de los originales. No hubo duplicados exactos de las 69 columnas originales en Cali. Se conservaron estados 2/3/5. Se identificaron cinco registros sin inicio de síntomas para los que se usó notificación, dejando una bandera. Se excluyeron 7.069 cronologías con síntomas posteriores a notificación y un registro fuera de la ventana epidemiológica. Quedaron 153.639 notificaciones incluidas.

La exclusión temporal es una decisión inicial conservadora, no una afirmación de que esas personas no hayan tenido dengue. Las 7.069 cronologías negativas se concentran en el archivo original de 2013: representan el 41,55 % de sus registros de Cali. La inconsistencia está presente en las fechas del Excel original; no se debe atribuir solo a las transformaciones del compañero. Debe revisarse con el experto y realizarse una sensibilidad antes de cerrar la limpieza, pues puede afectar estacionalidad, umbrales y entrenamiento. La auditoría por archivo está en `reports/tables/fechas_por_archivo.csv`. No se recortaron retrasos negativos a cero ni retrasos elevados a 180 días.

El panel conserva 992 semanas y las cuatro semanas 53. Veinte semanas carecen de registros y se mantienen con conteo desconocido. No se certificó completitud de la vigilancia. El canal exige cinco años previos para la misma semana; se obtuvieron 703 etiquetas y 697 filas con todas las variables predictoras disponibles.

## Diseño del modelo

La etiqueta es exceso sobre el P75 de la misma semana en los cinco años anteriores. El objetivo es la semana posterior al corte nominal y las variables excluyen el conteo y las características de pacientes de la propia semana objetivo. El modelo es una regresión logística regularizada L2, C=1, con escalado aprendido solo en entrenamiento.

| Bloque | Años epidemiológicos | Filas | Semanas con exceso |
|---|---|---:|---:|
| Entrenamiento | 2012–2021 | 489 | 171 |
| Validación | 2022–2023 | 104 | 36 |
| Prueba | 2024 | 52 | 49 |
| Evaluación adicional | 2025 | 52 | 0 |

Los primeros años sirven para inicializar el canal. Los límites exactos son epidemiológicos y pueden incluir días del año calendario siguiente. Se seleccionó un umbral de probabilidad de 0,15 por F2 en validación. Ese valor no es el umbral epidemiológico en número de casos.

## Resultados iniciales

| Bloque y método | Sensibilidad | Precisión | F1 | Falsas alarmas | Excesos omitidos |
|---|---:|---:|---:|---:|---:|
| Validación logística | 77,8 % | 73,7 % | 75,7 % | 10 | 8 |
| Validación persistencia de conteo | 97,2 % | 97,2 % | 97,2 % | 1 | 1 |
| Prueba 2024 logística | 100 % | 94,2 % | 97,0 % | 3 | 0 |
| Prueba 2024 alertar siempre | 100 % | 94,2 % | 97,0 % | 3 | 0 |
| Prueba 2024 persistencia de conteo | 98,0 % | 98,0 % | 98,0 % | 1 | 1 |

La regresión no mejora la referencia de persistencia en validación. En 2024 emite alerta en las 52 semanas, con especificidad cero: detecta los 49 excesos pero también alerta en las tres semanas sin exceso. Su alta sensibilidad y F1 no demuestran capacidad selectiva de alerta. La AP de 2024 debe leerse junto a una prevalencia de 94,2 % y apenas tres negativos; no demuestra generalización por sí sola.

En 2025 la logística al umbral validado emite cinco falsas alarmas sobre 52 semanas; no hay positivos con esta definición. No es posible medir sensibilidad o AUC en ese bloque. La menor carga observada de 2025 y el papel de los años epidémicos previos en el canal requieren revisión. No debe interpretarse la ausencia de etiquetas positivas como ausencia de dengue.

## Interpretación para el informe de avance

Puede afirmarse que se construyó y verificó un flujo reproducible desde los originales hasta un primer modelo con evaluación cronológica y referencias explícitas. No puede afirmarse que la logística sea superior, que el canal defina brotes oficiales o que las métricas representen una predicción en tiempo real.

Los conteos por inicio de síntomas y los estados finales se conocen retrospectivamente. Con retrasos de notificación no se garantiza que los rezagos estuvieran completos en su corte nominal. Esta limitación se debe resolver o acotar antes de plantear uso operacional. El siguiente experimento debe revisar el canal y las anomalías y mantener una comparación temporal honesta; no elegir cambios mirando repetidamente la prueba de 2024.
