# Segunda ronda del benchmark climático

Se mantienen Cali, Ibagué y Villavicencio, la etiqueta de exceso P75 y las mismas 709, 708 y 726 semanas elegibles de la primera ronda. La comparación incluye persistencia, los dos modelos de la ronda 1 con solo el umbral reajustado y los dos modelos reentrenados en la ronda 2. Todos los clasificadores incluyen clima.

## Predictores y validación

Se reutilizaron los conteos agrupados por inicio de síntomas, sus rezagos y el calendario epidemiológico. Los datos climáticos diarios proceden de una exportación municipal en Google Earth Engine. Los acumulados semanales de lluvia suman siete valores diarios. Temperatura y humedad relativa se promedian. Además de la semana anterior y el resumen de t−4 a t−1, se probaron ventanas de cuatro semanas de t−5 a t−2 y de t−6 a t−3, usando solo el clima de esa ventana. Las colecciones, el método espacial y la disponibilidad histórica al corte siguen pendientes de verificar. Las ventanas retrasadas simulan una espera mayor para el clima.

La etiqueta se mantiene en 1 solo si el conteo observado supera el P75 de la misma semana en los cinco años anteriores. La búsqueda combina predicciones de validación anual 2017–2021, con entrenamiento expansivo anterior a cada año y escalado ajustado dentro de cada corte. Se elige por AP agrupada y se descartan candidatos con problemas de convergencia. Se probaron valores de regularización alrededor de los ganadores previos, ambos esquemas de pesos de la logística y capas de 8 o 16 neuronas del MLP. Se amplió el extremo de C en Cali y de alpha en Ibagué y Villavicencio. Se fijó semilla 42 y se revisó sensibilidad a 7 y 13.

En 2022–2023 se seleccionó el umbral que detectaba el mayor número de excesos sin superar las falsas alertas de la persistencia (Cali 1, Ibagué 3, Villavicencio 9). Los empates prefieren menos falsas alertas y luego el umbral más alto. Se alerta si la probabilidad supera estrictamente el umbral. El límite se aplica en calibración. El desempeño de 2024 y 2025 muestra retrospectivamente cómo cambian los errores al aplicar ese umbral ya fijado. Ambos años ya se habían examinado en la ronda anterior.

## Resultados

Cada celda indica **excesos detectados / falsas alertas**. En cada ciudad y período, todos los métodos se comparan sobre las mismas semanas.

| Ciudad | Período | Excesos observados | Persistencia | Logística, solo umbral | Logística, ajustada | MLP, solo umbral | MLP, ajustado |
|---|---|---:|---:|---:|---:|---:|---:|
| Cali | 2022–2023 | 36 | 35 / 1 | 25 / 0 | 25 / 0 | 26 / 0 | 24 / 1 |
| Cali | 2024 | 49 | 48 / 1 | 49 / 3 | 49 / 3 | 34 / 2 | 36 / 1 |
| Cali | 2025 | 0 | 0 / 0 | 0 / 5 | 0 / 2 | 0 / 0 | 0 / 0 |
| Ibagué | 2022–2023 | 38 | 33 / 3 | 31 / 3 | 31 / 3 | 24 / 3 | 30 / 3 |
| Ibagué | 2024 | 41 | 39 / 2 | 41 / 9 | 41 / 9 | 40 / 9 | 41 / 9 |
| Ibagué | 2025 | 1 | 1 / 0 | 1 / 39 | 1 / 39 | 0 / 9 | 1 / 28 |
| Villavicencio | 2022–2023 | 61 | 49 / 9 | 44 / 6 | 44 / 6 | 44 / 9 | 42 / 9 |
| Villavicencio | 2024 | 14 | 11 / 6 | 10 / 11 | 10 / 11 | 11 / 15 | 13 / 5 |
| Villavicencio | 2025 | 48 | 46 / 3 | 47 / 4 | 47 / 4 | 45 / 4 | 34 / 4 |

La persistencia detectó más excesos bajo el límite observado de falsas alertas en las tres calibraciones. En Villavicencio 2024, el MLP ajustado pasó de F1 53,8 % en la primera ronda a 81,3 %, con 5 falsas alertas frente a 24. En 2025 pasó de 96,0 % a 79,1 %, y omitió 14 excesos. La mejora de 2024 no se sostuvo entre años. Para ese MLP, la ventana seleccionada fue t−6 a t−3 con 8 neuronas y alpha=1. En Cali ambos ajustes seleccionaron la misma ventana retrasada, con una oscilación de AP en calibración de 79,4 % a 92,1 % según la semilla del MLP. En Ibagué ambos modelos seleccionaron clima de la semana anterior. La logística de Villavicencio también seleccionó la semana anterior y conservó su configuración de la primera ronda.

Como contexto para la rúbrica 5, el MLP de Villavicencio 2024 registró 92,9 % de sensibilidad y 72,2 % de precisión. En 2025 registró 70,8 % y 89,5 %, respectivamente. EWARS-csd en Colombia reportó medianas de 97 % de sensibilidad y 75 % de valor predictivo positivo en las mejores calibraciones municipales. Los desenlaces y protocolos difieren: EWARS usa brotes basados en hospitalizaciones y este experimento predice exceso P75 de notificaciones a una semana. [Schlesinger et al., 2024](https://doi.org/10.3389/fpubh.2024.1323618)

## Reproducción

Desde la raíz del repositorio, tras generar la primera ronda:

```powershell
.venv/Scripts/python.exe scripts/benchmark_clima_ronda2.py
docker compose -f docker/mlflow/compose.yaml run --rm --no-deps importador python scripts/registrar_benchmark_clima.py --ronda 2
```

Los resultados locales quedan en reports/benchmark_clima_ronda2. En MLflow, abrir **Model training** y luego **Runs**. La vista **GenAI** presenta trazas y puede aparecer vacía. [Experimento de la segunda ronda](http://localhost:5000/#/experiments/4).
