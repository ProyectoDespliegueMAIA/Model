# Reconstrucción con inicio de síntomas como única fecha principal

Versión vigente: v1_ini_sin. Decisión adoptada el 22 de octubre de 2026. Se reconstruyeron panel, canal, etiquetas, variables y entrenamiento. El objetivo y los cortes de evaluación no se cambiaron para mejorar métricas.

## Decisión y controles

Usar exclusivamente INI_SIN para fechar cada caso. Los registros sin fecha válida se separan sin sustituirla por notificación o consulta. FEC_NOT y FEC_CON permanecen como controles de calidad, sin ser condición de disponibilidad para incluir un inicio válido. Una anomalía de notificación se marca; no se corrigen o inventan sus fechas.

| Campo | Fechas interpretables | Faltantes o inválidas | Completitud |
|---|---:|---:|---:|
| INI_SIN | 160,704 | 5 | 99.9969 % |
| FEC_CON | 160,703 | 6 | 99.9963 % |
| FEC_NOT | 160,709 | 0 | 100.0000 % |

En 160,701 registros hay inicio y consulta interpretables; en ninguno el inicio es posterior a consulta. Esto respalda la coherencia interna, pero no certifica la fecha real de cada acontecimiento. Notificación tiene mayor completitud, pero las 7.069 contradicciones favorecen escoger síntomas para la evolución retrospectiva.

## Efecto de la reconstrucción

| Indicador | v0 | v1 inicio de síntomas |
|---|---:|---:|
| Registros incluidos | 153,639 | 160,703 |
| Fechas sustituidas | 5 | 0 |
| Semanas del panel | 992 | 992 |
| Semanas sin registros | 20 | 19 |
| Semanas etiquetadas | 703 | 709 |
| Filas elegibles para modelo | 697 | 709 |

Se conservaron los 7.069 registros antes retirados por notificación anterior. A la vez, se separaron los cinco que antes utilizaban una fecha alternativa. El cambio neto es de 7.064 registros. Además, permanece la exclusión de un inicio fuera de la ventana epidemiológica. Los seis excluidos actuales están en data/processed/registros_excluidos.csv. Las semanas sin registros permanecen desconocidas, sin imputación a cero.

## Comparación de validación 2022–2023

| Versión y método | Sensibilidad | Precisión | F1 | Falsas alarmas | Excesos omitidos |
|---|---:|---:|---:|---:|---:|
| v0 logistica_umbral_validado | 77.8 % | 73.7 % | 75.7 % | 10 | 8 |
| v0 persistencia_conteo | 97.2 % | 97.2 % | 97.2 % | 1 | 1 |
| v1_ini_sin logistica_umbral_validado | 69.4 % | 100.0 % | 82.0 % | 0 | 11 |
| v1_ini_sin persistencia_conteo | 97.2 % | 97.2 % | 97.2 % | 1 | 1 |

La logística sigue sin mejorar a la persistencia en validación. En 2024 continúa alertando en todas las semanas; una sensibilidad alta allí no demuestra discriminación. No se eligió la fecha por estos resultados. La comparación entre versiones es una sensibilidad metodológica; 2024 ya fue observado y no se presenta como una nueva prueba independiente.

## Alcance y verificación

Se ejecutaron los dos notebooks, se conservaron los resultados anteriores y se agregaron pruebas que garantizan que una notificación anterior o ausente no elimine un inicio válido y que una fecha de síntomas faltante no se sustituya. Las contradicciones de las fechas auxiliares permanecen visibles.

La evaluación sigue siendo retrospectiva con datos finales. Elegir síntomas para agrupar no resuelve el retraso de disponibilidad operacional. Se requiere esa evaluación antes de afirmar que el servicio anticipa brotes en tiempo real.
