# Benchmark de alertas semanales con clima

Evaluamos si las notificaciones de dengue de la próxima semana, agrupadas por inicio de síntomas, superarán la referencia histórica de Cali, Ibagué o Villavicencio. Elegimos las tres ciudades por cobertura coincidente de clima y vigilancia y por contar con semanas etiquetadas en los bloques de desarrollo. Se ajustó un modelo de cada familia por municipio. Medellín quedó como exploración previa y no tiene CSV climático en el insumo de esta fase.

## Datos, predictores y etiqueta

Sea t la semana epidemiológica objetivo. Las semanas van de domingo a sábado y el corte nominal es el sábado anterior a t.

| Predictor | Fuente y construcción | Ventana |
|---|---|---|
| lag_1, lag_2, lag_3, lag_4, lag_8, lag_12 | Conteo de notificaciones incluidas de SIVIGILA, agrupadas por municipio y fecha de inicio de síntomas | t−1, t−2, t−3, t−4, t−8, t−12 |
| media_4, std_4 | Media y desviación estándar muestral de los mismos conteos | t−4 a t−1 |
| semana_sin, semana_cos | Seno y coseno de 2π × (semana epidemiológica − 1) / número de semanas del año | Calendario conocido de t |
| precipitación, temperatura y humedad de la última semana | Suma de precipitación diaria en mm y medias diarias de temperatura en °C y humedad relativa en % | t−1 |
| resúmenes climáticos de cuatro semanas | Suma de las cuatro precipitaciones semanales y media de las cuatro temperaturas y humedades semanales | t−4 a t−1, con siete días por semana |

Los CSV climáticos municipales fueron extraídos diariamente desde Google Earth Engine, según la información del equipo. Falta identificar las colecciones, el método de agregación espacial y la latencia de publicación. Cada CSV tiene 6.940 fechas únicas entre el 1 de enero de 2007 y el 31 de diciembre de 2025, con valores finitos en las tres variables. Hay 990 semanas completas por ciudad. Las dos semanas parciales de los extremos no aportan resúmenes completos. Al exigir cuatro semanas climáticas previas completas se conservaron las 709, 708 y 726 filas epidemiológicas elegibles de Cali, Ibagué y Villavicencio, respectivamente.

La etiqueta vale **1** cuando el conteo observado en t supera estrictamente el P75 de la misma semana epidemiológica en los cinco años previos de la ciudad. Vale **0** si el conteo es igual o menor. Una semana con conteo desconocido o sin los cinco antecedentes válidos queda sin etiqueta. El umbral de probabilidad de alerta se ajusta por separado.

Los conteos y el clima observados se desplazan antes de calcular ventanas. Por ejemplo, para la semana 20 se usan datos observados como máximo de la semana 19, y los cuatro resúmenes abarcan las semanas 16 a 19. El P75 se construye con semanas 20 de años anteriores. El escalado se ajusta exclusivamente dentro de cada bloque de entrenamiento. La evaluación usa series retrospectivas consolidadas. Para demostrar desempeño operativo hace falta reconstruir qué valores estaban disponibles al emitir cada alerta, dadas las demoras de notificación y de publicación del clima.

## Modelos y selección

La referencia de persistencia alerta cuando el último conteo observado supera el P75 de la semana objetivo. Los dos clasificadores usan los diez predictores epidemiológicos y calendáricos, más tres o seis climáticos. Los diez predictores originales se eligieron por criterio técnico. La comparación entre ventanas climáticas de una y cuatro semanas forma parte de la búsqueda, con la misma población de semanas para ambos modelos.

- Regresión logística con regularización L2, optimizador LBFGS, C en {0.01, 0.1, 1, 10} y pesos de clase uniformes o balanceados.
- MLP con una capa oculta ReLU de 8 o 16 neuronas, optimizador LBFGS y alpha en {0.001, 0.01, 0.1, 1}. Se usa la semilla 42 y se documenta la estabilidad con las semillas 7, 13 y 42.
- Cada modelo compara dos conjuntos de clima y 16 configuraciones iniciales. La búsqueda fina prueba dos valores de regularización alrededor del ganador inicial. Se elige por precisión promedio (AP) sobre las predicciones fuera de entrenamiento agrupadas de cinco cortes expansivos (validaciones anuales 2017–2021). Los años de una sola clase quedan representados en el conjunto agrupado. Se excluyen configuraciones con avisos de convergencia en los cortes.
- El ajuste final usa las semanas elegibles hasta 2021. En 2022–2023 se elige el umbral de probabilidad que maximiza F2 entre 0,10 y 0,90 con pasos de 0,05 y desempate por umbral más alto. Sus métricas describen calibración del umbral. Se aplican los modelos y umbrales fijados a 2024 y 2025, dos períodos retrospectivos que ya se habían examinado en el avance.

| Ciudad | Logística: C, pesos, clima | MLP: neuronas, alpha, clima |
|---|---|---|
| Cali | 31,62, balanceados, última semana y cuatro previas | 8, 0,1, última semana y cuatro previas |
| Ibagué | 0,01, balanceados, última semana | 8, 3,16, última semana y cuatro previas |
| Villavicencio | 0,1, balanceados, última semana | 8, 3,16, última semana y cuatro previas |

Una ejecución alternativa de MLP en Cali (semilla 13) emitió un aviso de convergencia. El modelo reportado (semilla 42) convergió.

## Resultados y literatura

| Ciudad | Período | F1 persistencia | F1 logística | F1 MLP |
|---|---|---:|---:|---:|
| Cali | 2022–2023 | 97,2 % | 82,0 % | 77,8 % |
| Cali | 2024 | 98,0 % | 97,0 % | 80,5 % |
| Cali | 2025 | — | — | — |
| Ibagué | 2022–2023 | 89,2 % | 80,5 % | 74,1 % |
| Ibagué | 2024 | 95,1 % | 90,1 % | 90,1 % |
| Ibagué | 2025 | 100,0 % | 4,3 % | 9,5 % |
| Villavicencio | 2022–2023 | 82,4 % | 81,2 % | 80,9 % |
| Villavicencio | 2024 | 71,0 % | 50,9 % | 53,8 % |
| Villavicencio | 2025 | 94,8 % | 96,0 % | 96,0 % |

Cali 2025 tuvo cero excesos. Solo la logística emitió alertas, dos. Ibagué 2025 tuvo un exceso, detectado por los tres métodos, con 0, 45 y 19 falsas alertas para persistencia, logística y MLP. En Villavicencio 2024 los dos modelos detectaron 14 de 14 excesos, con 27 y 24 falsas alertas, frente a 11 de 14 y seis falsas alertas con persistencia. En 2025 los dos modelos detectaron 48 de 48 excesos con cuatro falsas alertas, frente a 46 de 48 y tres falsas alertas con persistencia. La elección depende del costo de omitir excesos frente a la carga de investigar alertas.

Schlesinger et al. (2024) reportaron en Colombia medianas de 97 % de sensibilidad y 75 % de valor predictivo positivo para las mejores calibraciones municipales de EWARS-csd. Usaron temperatura, lluvia y brotes definidos sobre hospitalizaciones semanales. En Villavicencio 2024, la sensibilidad de los dos clasificadores fue 100 % y la precisión 34,1 % y 36,8 %, respectivamente. Las cifras contextualizan el costo de la sensibilidad alta. La definición del evento, el horizonte y el procedimiento de calibración difieren y limitan la comparación directa. [Estudio EWARS-csd en Colombia](https://doi.org/10.3389/fpubh.2024.1323618)

El benchmark compara familias de modelos sobre variables climáticas. Estimar el aporte aislado del clima requeriría una variante sin clima en las mismas semanas.

## Reproducción y evidencia

Desde la raíz del repositorio, ejecutar con el entorno Python del proyecto:

```powershell
.venv/Scripts/python.exe scripts/benchmark_clima.py
docker compose -f docker/mlflow/compose.yaml up -d --wait mlflow
docker compose -f docker/mlflow/compose.yaml run --rm --no-deps importador python scripts/registrar_benchmark_clima.py
```

Los modelos, las predicciones semanales, las métricas, la búsqueda completa, los umbrales y los hashes de los insumos quedan en la ruta local reports/benchmark_clima. El argumento --clima permite indicar otra ruta a los tres CSV originales. El registro reutiliza ejecuciones terminadas con la misma huella. [Experimento MLflow](http://localhost:5000/#/experiments/3).
