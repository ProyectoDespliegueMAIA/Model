# Primer análisis y regresión logística en tres ciudades

## Protocolo común

Cali (76001), Medellín (05001) y Villavicencio (50001) se preparan y modelan por separado desde los 19 Excel originales de 2007–2025. Se verifica evento 210, país 170, municipio de ocurrencia y estados finales 2, 3 y 5. La inclusión de estos estados reproduce el piloto; no equivale a contar únicamente casos confirmados.

Se usa exclusivamente INI_SIN, sin sustituirla por notificación. Se excluyen fechas ausentes/inválidas y fuera del calendario; se conserva y señala la notificación anterior a síntomas. Una inconsistencia con consulta también se informa: no debe afirmarse que elegir INI_SIN elimina todas las contradicciones de una nueva ciudad.

Cada panel tiene 992 semanas y 28 columnas. Las semanas sin registros se mantienen como desconocidas. La semana 53 permanece en la secuencia; sin cinco antecedentes comparables no tiene etiqueta. Los diez predictores son seis rezagos (1, 2, 3, 4, 8 y 12), media y desviación de las cuatro semanas anteriores, seno y coseno del calendario.

Exceso significa superar estrictamente el P75 de la misma semana en los cinco años anteriores, calculado dentro de cada municipio. La regresión estima probabilidad de exceso la semana siguiente al corte nominal, no el conteo de casos. Se ajustan StandardScaler y logística L2 C=1 solo hasta 2021; el umbral se elige por F2 en 2022–2023 (rejilla 0,10–0,90, pasos 0,05; empate favorece umbral mayor). Se evalúan 2024 y, adicionalmente, 2025 sin reajustar. Cada municipio tiene un escalador, coeficientes y umbral independientes.

## Calidad y disponibilidad

| Ciudad | Extraídos | Incluidos | Sin inicio válido | Inicio válido (%) | Semanas sin filas | Semanas elegibles | Notificación anterior a síntomas | Síntomas posteriores a consulta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cali | 160709 | 160703 | 5 | 100.00 | 19 | 709 | 7069 | 0 |
| Medellín | 56884 | 56877 | 6 | 99.99 | 54 | 652 | 1267 | 0 |
| Villavicencio | 53422 | 53417 | 2 | 100.00 | 1 | 726 | 2165 | 0 |

## Particiones temporales

| ciudad | bloque | filas | positivos | inicio | fin |
| --- | --- | --- | --- | --- | --- |
| Cali | entrenamiento | 501 | 175 | 2012-01-15 | 2022-01-01 |
| Cali | validacion | 104 | 36 | 2022-01-02 | 2023-12-30 |
| Cali | prueba_2024 | 52 | 49 | 2023-12-31 | 2024-12-28 |
| Cali | adicional_2025 | 52 | 0 | 2024-12-29 | 2025-12-27 |
| Medellín | entrenamiento | 458 | 178 | 2012-04-01 | 2022-01-01 |
| Medellín | validacion | 94 | 2 | 2022-01-02 | 2023-12-30 |
| Medellín | prueba_2024 | 50 | 48 | 2023-12-31 | 2024-12-28 |
| Medellín | adicional_2025 | 50 | 35 | 2024-12-29 | 2025-12-27 |
| Villavicencio | entrenamiento | 518 | 175 | 2012-01-01 | 2022-01-01 |
| Villavicencio | validacion | 104 | 61 | 2022-01-02 | 2023-12-30 |
| Villavicencio | prueba_2024 | 52 | 14 | 2023-12-31 | 2024-12-28 |
| Villavicencio | adicional_2025 | 52 | 48 | 2024-12-29 | 2025-12-27 |

## Métricas comparables dentro de cada ciudad

| ciudad | bloque | modelo | n | prevalencia (%) | umbral_probabilidad | sensibilidad (%) | precision (%) | f1 (%) | especificidad (%) | fp | fn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cali | validacion | logistica_umbral_validado | 104 | 34.62 | 0.45 | 69.44 | 100.00 | 81.97 | 100.00 | 0 | 11 |
| Cali | validacion | persistencia_conteo | 104 | 34.62 | 0.50 | 97.22 | 97.22 | 97.22 | 98.53 | 1 | 1 |
| Cali | prueba_2024 | logistica_umbral_validado | 52 | 94.23 | 0.45 | 100.00 | 94.23 | 97.03 | 0.00 | 3 | 0 |
| Cali | prueba_2024 | persistencia_conteo | 52 | 94.23 | 0.50 | 97.96 | 97.96 | 97.96 | 66.67 | 1 | 1 |
| Cali | adicional_2025 | logistica_umbral_validado | 52 | 0.00 | 0.45 | — | 0.00 | — | 96.15 | 2 | 0 |
| Cali | adicional_2025 | persistencia_conteo | 52 | 0.00 | 0.50 | — | — | — | 100.00 | 0 | 0 |
| Medellín | validacion | logistica_umbral_validado | 94 | 2.13 | 0.90 | 0.00 | — | 0.00 | 100.00 | 0 | 2 |
| Medellín | validacion | persistencia_conteo | 94 | 2.13 | 0.50 | 50.00 | 50.00 | 50.00 | 98.91 | 1 | 1 |
| Medellín | prueba_2024 | logistica_umbral_validado | 50 | 96.00 | 0.90 | 68.75 | 100.00 | 81.48 | 100.00 | 0 | 15 |
| Medellín | prueba_2024 | persistencia_conteo | 50 | 96.00 | 0.50 | 97.92 | 97.92 | 97.92 | 50.00 | 1 | 1 |
| Medellín | adicional_2025 | logistica_umbral_validado | 50 | 70.00 | 0.90 | 5.71 | 100.00 | 10.81 | 100.00 | 0 | 33 |
| Medellín | adicional_2025 | persistencia_conteo | 50 | 70.00 | 0.50 | 94.29 | 94.29 | 94.29 | 86.67 | 2 | 2 |
| Villavicencio | validacion | logistica_umbral_validado | 104 | 58.65 | 0.10 | 88.52 | 76.06 | 81.82 | 60.47 | 17 | 7 |
| Villavicencio | validacion | persistencia_conteo | 104 | 58.65 | 0.50 | 80.33 | 84.48 | 82.35 | 79.07 | 9 | 12 |
| Villavicencio | prueba_2024 | logistica_umbral_validado | 52 | 26.92 | 0.10 | 100.00 | 30.43 | 46.67 | 15.79 | 32 | 0 |
| Villavicencio | prueba_2024 | persistencia_conteo | 52 | 26.92 | 0.50 | 78.57 | 64.71 | 70.97 | 84.21 | 6 | 3 |
| Villavicencio | adicional_2025 | logistica_umbral_validado | 52 | 92.31 | 0.10 | 100.00 | 92.31 | 96.00 | 0.00 | 4 | 0 |
| Villavicencio | adicional_2025 | persistencia_conteo | 52 | 92.31 | 0.50 | 95.83 | 93.88 | 94.85 | 25.00 | 3 | 2 |

La persistencia pronostica el último conteo y lo contrasta con el umbral de casos de la semana objetivo. Es una referencia binaria; sus valores 0/1 no son probabilidades calibradas. Las tablas locales incluyen también logística a umbral 0,5, prevalencia constante, siempre alerta, F2, AP, ROC AUC, Brier y matrices de confusión. El guion largo indica una métrica no definida; no significa cero. Se debe interpretar sensibilidad y F1 junto a prevalencia, especificidad y falsas alarmas.

## Lectura del primer resultado

**Medellín:** de 56.884 registros extraídos se incluyen 56.877; se excluyen seis sin inicio válido y uno fuera del calendario. Hay 54 semanas sin registros. Las 1.267 notificaciones anteriores a síntomas proceden del archivo de 2013; no se observaron síntomas posteriores a consulta cuando ambas fechas eran interpretables. En validación solo hay dos excesos entre 94 semanas elegibles. Toda la rejilla obtiene F2=0: el umbral 0,90 resulta únicamente de la regla de desempate y no demuestra un umbral útil. En 2024 omite 15 de 48 excesos; en 2025 omite 33 de 35. No es un modelo listo para uso operacional. Conviene evaluar varios cortes de validación temporal dentro del periodo de desarrollo antes de nuevas comparaciones.

**Villavicencio:** de 53.422 registros extraídos se incluyen 53.417; se excluyen dos sin inicio válido y tres fuera del calendario. Solo hay una semana sin registros. Las 2.165 notificaciones anteriores a síntomas proceden del archivo de 2013; no se observaron síntomas posteriores a consulta cuando ambas fechas eran interpretables. En validación hay 61 excesos en 104 semanas; el umbral seleccionado es 0,10. La logística alcanza sensibilidad 88,5 %, precisión 76,1 % y F1 81,8 %, frente a F1 82,4 % de persistencia. En 2024 detecta los 14 excesos, pero genera 32 falsas alarmas; en 2025 alerta todas las semanas evaluadas, por lo que su F1 alto no demuestra discriminación de semanas sin exceso.

Estos patrones justifican conservar los experimentos como referencia inicial y comparar algoritmos bajo un protocolo temporal más robusto, sin prometer que una familia más compleja resolverá las limitaciones.

## Límites de interpretación

- La presencia de registros en una semana no demuestra cobertura completa. Los conteos y las métricas entre ciudades no son una clasificación de riesgo o incidencia: faltan denominadores de población y validación externa de cobertura.
- El escalador y los coeficientes se ajustan solo en entrenamiento. El canal y los rezagos de una semana usan antecedentes cronológicos; la simulación avanza semana a semana con conteos finales, sin reentrenamiento dentro de prueba.
- Los datos finales y sus estados pudieron conocerse después del corte nominal. Esta evaluación retrospectiva no demuestra rendimiento en tiempo real. La elección de INI_SIN conserva significado epidemiológico, pero no resuelve la disponibilidad o exactitud de todas las fechas.
- 2024 ya se había observado en Cali. Esta es la primera evaluación de las otras dos ciudades; las revisiones posteriores deben reconocer que estos resultados también fueron observados. No escoger hiperparámetros con prueba y seguir presentándola como nueva.
- P75 con cinco antecedentes es una definición inicial de exceso, no una declaración oficial de brote. Faltan sensibilidad del canal, validación temporal en más cortes y evaluación de oportunidad por episodios.
- Este paso no incorpora todavía MLflow, HistGradientBoosting ni red neuronal; establece los primeros modelos independientes con un protocolo común.

## Análisis anual

### Cali

| anio_epi | semanas | con_registros | notificaciones_incluidas | elegibles |
| --- | --- | --- | --- | --- |
| 2007 | 52 | 33 | 138 | 0 |
| 2008 | 53 | 53 | 1027 | 0 |
| 2009 | 52 | 52 | 5682 | 0 |
| 2010 | 52 | 52 | 11000 | 0 |
| 2011 | 52 | 52 | 1394 | 0 |
| 2012 | 52 | 52 | 1967 | 33 |
| 2013 | 52 | 52 | 17013 | 52 |
| 2014 | 53 | 53 | 5874 | 52 |
| 2015 | 52 | 52 | 14439 | 52 |
| 2016 | 52 | 52 | 19307 | 52 |
| 2017 | 52 | 52 | 3700 | 52 |
| 2018 | 52 | 52 | 1731 | 52 |
| 2019 | 52 | 52 | 3867 | 52 |
| 2020 | 53 | 53 | 13230 | 52 |
| 2021 | 52 | 52 | 5724 | 52 |
| 2022 | 52 | 52 | 2821 | 52 |
| 2023 | 52 | 52 | 13125 | 52 |
| 2024 | 52 | 52 | 35604 | 52 |
| 2025 | 53 | 53 | 3060 | 52 |

### Medellín

| anio_epi | semanas | con_registros | notificaciones_incluidas | elegibles |
| --- | --- | --- | --- | --- |
| 2007 | 52 | 3 | 3 | 0 |
| 2008 | 53 | 53 | 889 | 0 |
| 2009 | 52 | 49 | 413 | 0 |
| 2010 | 52 | 52 | 15456 | 0 |
| 2011 | 52 | 52 | 781 | 0 |
| 2012 | 52 | 52 | 703 | 3 |
| 2013 | 52 | 52 | 2297 | 49 |
| 2014 | 53 | 53 | 3223 | 49 |
| 2015 | 52 | 52 | 3746 | 52 |
| 2016 | 52 | 52 | 17236 | 52 |
| 2017 | 52 | 52 | 2094 | 52 |
| 2018 | 52 | 52 | 1169 | 52 |
| 2019 | 52 | 52 | 1229 | 52 |
| 2020 | 53 | 53 | 623 | 52 |
| 2021 | 52 | 51 | 235 | 45 |
| 2022 | 52 | 51 | 223 | 46 |
| 2023 | 52 | 52 | 437 | 48 |
| 2024 | 52 | 52 | 4882 | 50 |
| 2025 | 53 | 53 | 1238 | 50 |

### Villavicencio

| anio_epi | semanas | con_registros | notificaciones_incluidas | elegibles |
| --- | --- | --- | --- | --- |
| 2007 | 52 | 52 | 1478 | 0 |
| 2008 | 53 | 52 | 308 | 0 |
| 2009 | 52 | 52 | 1595 | 0 |
| 2010 | 52 | 52 | 3211 | 0 |
| 2011 | 52 | 52 | 1677 | 0 |
| 2012 | 52 | 52 | 2936 | 51 |
| 2013 | 52 | 52 | 5249 | 51 |
| 2014 | 53 | 53 | 3949 | 52 |
| 2015 | 52 | 52 | 2073 | 52 |
| 2016 | 52 | 52 | 1302 | 52 |
| 2017 | 52 | 52 | 547 | 52 |
| 2018 | 52 | 52 | 2250 | 52 |
| 2019 | 52 | 52 | 8183 | 52 |
| 2020 | 53 | 53 | 1082 | 52 |
| 2021 | 52 | 52 | 541 | 52 |
| 2022 | 52 | 52 | 1893 | 52 |
| 2023 | 52 | 52 | 5926 | 52 |
| 2024 | 52 | 52 | 3711 | 52 |
| 2025 | 53 | 53 | 5506 | 52 |
