# Evaluación de Ibagué como ciudad candidata

## Alcance y protocolo

Se evalúa Ibagué (73001) desde los 19 Excel originales, sin reemplazar ni reentrenar Medellín, Cali o Villavicencio. La selección definitiva de las tres ciudades sigue siendo una decisión pendiente.

Se mantiene el protocolo v1_ini_sin: evento 210, municipio de ocurrencia, país 170 y estados 2, 3 y 5; inicio de síntomas sin sustituciones, ausencia de registros como desconocido, calendario semanal completo y semana 53 conservada. La etiqueta es superar estrictamente el P75 de la misma semana en los cinco años anteriores, exigiendo cinco antecedentes válidos. Es una definición operacional, no una declaración oficial de brote.

La logística L2 C=1 y el escalador se ajustan solo hasta 2021. Los diez predictores son los mismos de las otras ciudades. El umbral de probabilidad se selecciona con F2 en 2022–2023 (rejilla 0,10 a 0,90, paso 0,05, empate favorece mayor umbral). Se informa 2024 y, adicionalmente, 2025 sin reajustar. Se compara con persistencia y otras referencias simples; cada municipio se entrena por separado.

## Calidad y cobertura observada

| Ciudad | Extraídos | Incluidos | Sin inicio válido | Semanas sin registros | Semanas elegibles | Notificación anterior a síntomas | Síntomas posteriores a consulta |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Cali | 160709 | 160703 | 5 | 19 | 709 | 7069 | 0 |
| Medellín | 56884 | 56877 | 6 | 54 | 652 | 1267 | 0 |
| Villavicencio | 53422 | 53417 | 2 | 1 | 726 | 2165 | 0 |
| Ibagué | 57321 | 57319 | 0 | 3 | 708 | 2195 | 0 |

En Ibagué hay 992 semanas en el panel y 719 con etiqueta disponible. El inicio de síntomas es interpretable en 100.0000 % de los registros auditados. Presencia de registros no certifica cobertura completa. Las cronologías negativas se conservan con bandera; su detalle por archivo está abajo.

### Auditoría de exclusiones de Ibagué

| etapa | filas_restantes | excluidos |
| --- | --- | --- |
| extraidos_municipio | 57321 | 0 |
| sin_duplicados_exactos_originales | 57321 | 0 |
| evento_y_ubicacion_validos | 57321 | 0 |
| estados_2_3_5 | 57321 | 0 |
| inicio_sintomas_valido_sin_sustitucion | 57321 | 0 |
| dentro_ventana_epidemiologica | 57319 | 2 |

## Disponibilidad de clases

| ciudad | bloque | filas | positivos | inicio | fin | sin_exceso |
| --- | --- | --- | --- | --- | --- | --- |
| Cali | entrenamiento | 501 | 175 | 2012-01-15 | 2022-01-01 | 326 |
| Cali | validacion | 104 | 36 | 2022-01-02 | 2023-12-30 | 68 |
| Cali | prueba_2024 | 52 | 49 | 2023-12-31 | 2024-12-28 | 3 |
| Cali | adicional_2025 | 52 | 0 | 2024-12-29 | 2025-12-27 | 52 |
| Medellín | entrenamiento | 458 | 178 | 2012-04-01 | 2022-01-01 | 280 |
| Medellín | validacion | 94 | 2 | 2022-01-02 | 2023-12-30 | 92 |
| Medellín | prueba_2024 | 50 | 48 | 2023-12-31 | 2024-12-28 | 2 |
| Medellín | adicional_2025 | 50 | 35 | 2024-12-29 | 2025-12-27 | 15 |
| Villavicencio | entrenamiento | 518 | 175 | 2012-01-01 | 2022-01-01 | 343 |
| Villavicencio | validacion | 104 | 61 | 2022-01-02 | 2023-12-30 | 43 |
| Villavicencio | prueba_2024 | 52 | 14 | 2023-12-31 | 2024-12-28 | 38 |
| Villavicencio | adicional_2025 | 52 | 48 | 2024-12-29 | 2025-12-27 | 4 |
| Ibagué | entrenamiento | 515 | 173 | 2012-01-01 | 2022-01-01 | 342 |
| Ibagué | validacion | 93 | 38 | 2022-01-02 | 2023-12-30 | 55 |
| Ibagué | prueba_2024 | 50 | 41 | 2023-12-31 | 2024-12-28 | 9 |
| Ibagué | adicional_2025 | 50 | 1 | 2024-12-29 | 2025-12-27 | 49 |

Ibagué aporta 38 semanas con exceso y 55 sin exceso en validación, frente a 2 y 92 en Medellín. Esto permite valorar la disponibilidad de ambas clases sin elegir la ciudad por su F1 de prueba. Las semanas consecutivas pueden pertenecer al mismo episodio: más semanas no equivalen a más brotes independientes.

### Clases por año en Ibagué

| anio_epi | ciudad | elegibles | excesos | sin_exceso |
| --- | --- | --- | --- | --- |
| 2012 | Ibagué | 52 | 38.00 | 14.00 |
| 2013 | Ibagué | 52 | 44.00 | 8.00 |
| 2014 | Ibagué | 52 | 9.00 | 43.00 |
| 2015 | Ibagué | 52 | 28.00 | 24.00 |
| 2016 | Ibagué | 52 | 4.00 | 48.00 |
| 2017 | Ibagué | 52 | 0.00 | 52.00 |
| 2018 | Ibagué | 52 | 0.00 | 52.00 |
| 2019 | Ibagué | 52 | 35.00 | 17.00 |
| 2020 | Ibagué | 52 | 15.00 | 37.00 |
| 2021 | Ibagué | 47 | 0.00 | 47.00 |
| 2022 | Ibagué | 43 | 1.00 | 42.00 |
| 2023 | Ibagué | 50 | 37.00 | 13.00 |
| 2024 | Ibagué | 50 | 41.00 | 9.00 |
| 2025 | Ibagué | 50 | 1.00 | 49.00 |

## Comparación en validación (2022–2023)

| ciudad | bloque | modelo | n | prevalencia (%) | umbral_probabilidad | sensibilidad (%) | precision (%) | f1 (%) | f2 (%) | especificidad (%) | fp | fn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cali | validacion | logistica_umbral_validado | 104 | 34.62 | 0.45 | 69.44 | 100.00 | 81.97 | 73.96 | 100.00 | 0 | 11 |
| Cali | validacion | persistencia_conteo | 104 | 34.62 | 0.50 | 97.22 | 97.22 | 97.22 | 97.22 | 98.53 | 1 | 1 |
| Medellín | validacion | logistica_umbral_validado | 94 | 2.13 | 0.90 | 0.00 | — | 0.00 | 0.00 | 100.00 | 0 | 2 |
| Medellín | validacion | persistencia_conteo | 94 | 2.13 | 0.50 | 50.00 | 50.00 | 50.00 | 50.00 | 98.91 | 1 | 1 |
| Villavicencio | validacion | logistica_umbral_validado | 104 | 58.65 | 0.10 | 88.52 | 76.06 | 81.82 | 85.71 | 60.47 | 17 | 7 |
| Villavicencio | validacion | persistencia_conteo | 104 | 58.65 | 0.50 | 80.33 | 84.48 | 82.35 | 81.13 | 79.07 | 9 | 12 |
| Ibagué | validacion | logistica_umbral_validado | 93 | 40.86 | 0.10 | 81.58 | 83.78 | 82.67 | 82.01 | 89.09 | 6 | 7 |
| Ibagué | validacion | persistencia_conteo | 93 | 40.86 | 0.50 | 86.84 | 91.67 | 89.19 | 87.77 | 94.55 | 3 | 5 |

El umbral seleccionado de Ibagué es 0.10, con F2 máximo de validación 0.8201. No se optimizó con 2024 ni con 2025. El guion largo representa una métrica no definida, no cero.

## Evaluación posterior del primer modelo

| ciudad | bloque | modelo | n | prevalencia (%) | umbral_probabilidad | sensibilidad (%) | precision (%) | f1 (%) | f2 (%) | especificidad (%) | fp | fn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Ibagué | prueba_2024 | logistica_umbral_validado | 50 | 82.00 | 0.10 | 100.00 | 82.00 | 90.11 | 95.79 | 0.00 | 9 | 0 |
| Ibagué | prueba_2024 | persistencia_conteo | 50 | 82.00 | 0.50 | 95.12 | 95.12 | 95.12 | 95.12 | 77.78 | 2 | 2 |
| Ibagué | adicional_2025 | logistica_umbral_validado | 50 | 2.00 | 0.10 | 100.00 | 4.00 | 7.69 | 17.24 | 51.02 | 24 | 0 |
| Ibagué | adicional_2025 | persistencia_conteo | 50 | 2.00 | 0.50 | 100.00 | 100.00 | 100.00 | 100.00 | 100.00 | 0 | 0 |

Estos bloques permiten describir errores y falsas alarmas; no deben emplearse para escoger reiteradamente ciudades o hiperparámetros y luego presentarse como pruebas independientes. Esta evaluación ocurre después de observar resultados de otras ciudades; su selección es exploratoria. Las AUC se omiten en bloques de una sola clase y no debe confundirse precisión con exactitud global.

## Fechas y anomalías de Ibagué

| ARCHIVO_ORIGEN | registros | cronologias_negativas | mayores_180 | sin_inicio | pct_cronologia_negativa |
| --- | --- | --- | --- | --- | --- |
| Datos_2007_210.xlsx | 1019 | 0 | 0 | 0 | 0.00 |
| Datos_2008_210.xlsx | 553 | 0 | 1 | 0 | 0.00 |
| Datos_2009_210.xlsx | 1767 | 0 | 2 | 0 | 0.00 |
| Datos_2010_210.xlsx | 6416 | 0 | 1 | 0 | 0.00 |
| Datos_2011_210.xlsx | 940 | 0 | 1 | 0 | 0.00 |
| Datos_2012_210.xlsx | 2301 | 0 | 33 | 0 | 0.00 |
| Datos_2013_210.xlsx | 5367 | 2195 | 810 | 0 | 40.90 |
| Datos_2014_210.xlsx | 3103 | 0 | 15 | 0 | 0.00 |
| Datos_2015_210.xlsx | 5056 | 0 | 10 | 0 | 0.00 |
| Datos_2016_210.xlsx | 2163 | 0 | 5 | 0 | 0.00 |
| Datos_2017_210.xlsx | 602 | 0 | 1 | 0 | 0.00 |
| Datos_2018_210.xlsx | 599 | 0 | 2 | 0 | 0.00 |
| Datos_2019_210.xlsx | 5145 | 0 | 8 | 0 | 0.00 |
| Datos_2020_210.xlsx | 2756 | 0 | 1 | 0 | 0.00 |
| Datos_2021_210.xlsx | 314 | 0 | 1 | 0 | 0.00 |
| Datos_2022_210.xlsx | 342 | 0 | 3 | 0 | 0.00 |
| Datos_2023_210.xlsx | 4101 | 0 | 3 | 0 | 0.00 |
| Datos_2024_210.xlsx | 13340 | 0 | 2 | 0 | 0.00 |
| Datos_2025_210.xlsx | 1437 | 0 | 0 | 0 | 0.00 |

## Interpretación y siguiente decisión

**Valoración de Ibagué:** su candidatura es más favorable que la de Medellín para el ejercicio actual por su continuidad observada (3 semanas sin filas frente a 54) y por la disponibilidad de ambas clases en validación (38/55 frente a 2/92). Esta valoración no equivale a certificar la cobertura ni demuestra que la logística sea el mejor modelo. Se recomienda Ibagué como posible sustituta, manteniendo la selección definitiva pendiente y conservando Medellín como experimento documentado.

En validación, 37 de los 38 excesos se concentran en 2023: hace falta comprobar estabilidad en más cortes y episodios. En 2024 la logística emite 50 alertas entre 50 semanas, con 9 falsas alarmas y 0 excesos omitidos; un F1 alto debe leerse junto a esa falta de discriminación binaria. En 2025 hay 1 excesos entre 50 semanas: genera 24 falsas alarmas, con precisión 4.0 % y F1 7.7 %. No es una solución lista para uso operacional.

La candidatura debe justificarse con calidad, continuidad y disponibilidad de ambas clases en desarrollo, junto con pertinencia epidemiológica. Comparar F1 entre municipios no prueba que uno sea más predecible: las prevalencias y etiquetas históricas cambian. Los resultados del primer modelo no sustituyen esa justificación.

Falta validar cobertura con una fuente externa y simular qué información estaba disponible en cada corte: se usan conteos y estados finales, que pudieron notificarse después. Antes de comparar algoritmos o cerrar la selección, conviene predefinir varios cortes de validación temporal dentro del periodo de desarrollo, examinar diversidad de episodios y sensibilidad del canal. Los valores de 2024 y 2025 ya observados deben tratarse como evaluación retrospectiva exploratoria en decisiones posteriores.

## Trazabilidad de fuentes

El Excel de 2013 tiene una huella binaria distinta del manifiesto histórico de Cali. Se reextrajeron sus 17013 registros de Cali para comprobar el contenido: coincidencia del multiconjunto de huellas de las 69 columnas originales = True. No se determinó la causa del cambio binario ni se modificó el experimento de Cali. Los manifiestos actuales de Ibagué, Medellín y Villavicencio coinciden en las 19 huellas de fuente.

Panel SHA-256: `ce7c6b490e2b7cfb156d772647922439de1188137738ce6539678f8878f06cbe`.
