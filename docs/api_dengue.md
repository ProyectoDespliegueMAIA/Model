# API de predicciones semanales de dengue

La API sirve la regresión logística con clima de la segunda ronda para Cali, Ibagué y Villavicencio. El horizonte es de una semana. Cada ciudad conserva su modelo, sus predictores y su umbral. La API carga los modelos al iniciar y calcula las probabilidades para las semanas históricas disponibles de 2022 a 2025. El cálculo usa los predictores históricos y la respuesta añade los casos observados para que el frontend pueda contrastarlos con la predicción.

2022–2023 corresponde a la calibración del umbral. 2024 y 2025 corresponden a las evaluaciones retrospectivas. Las inferencias usan las series consolidadas, incluido el clima definitivo del proyecto.

## Ejecutar desde la raíz del repositorio

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-api.txt
.venv/Scripts/python.exe scripts/exportar_api_dengue.py
.venv/Scripts/python.exe -m uvicorn dengue.api:app --app-dir src --host 127.0.0.1 --port 8000
```

La exportación requiere los resultados de la [segunda ronda](benchmark_clima_ronda2.md), el panel epidemiológico semanal y los CSV diarios de clima. Con --clima se puede indicar la ruta de los CSV. La exportación valida los hashes de los insumos y compara las probabilidades y alertas con el benchmark. Genera data/api_dengue, carpeta local excluida de Git con modelos, metadatos y filas semanales agregadas. Para ejecutar la API en otro entorno, transferir este paquete de confianza y, si cambia la ubicación, definir DENGUE_API_DATA_DIR. El servidor solo necesita ese paquete al iniciar.

## Contrato para el frontend

| Método y ruta | Resultado |
|---|---|
| GET /health | Estado del servicio. |
| GET /api/v1/ciudades | Ciudad, código DANE, versión del modelo, ventana climática, umbral y semanas disponibles. |
| GET /api/v1/ciudades/{ciudad}/semanas?anio=2024 | Semanas consultables, fechas, corte de predicción y bloque de evaluación. El año es opcional. |
| GET /api/v1/ciudades/{ciudad}/predicciones/{anio}/{semana} | Probabilidad, umbral, alerta, P75 de casos, conteo y exceso observados. |

Identificadores de ciudad: cali, ibague y villavicencio. La alerta se activa cuando la probabilidad supera estrictamente el umbral. Para explorar escenarios, el frontend puede enviar ?umbral=0.6 en una consulta. El cambio aplica únicamente a esa respuesta y conserva el umbral municipal por defecto en otro campo. El P75 se expresa en conteos y la probabilidad y su umbral se expresan en escala de 0 a 1. Una semana no disponible retorna 404 y los parámetros inválidos retornan 422.

- [Documentación interactiva](http://127.0.0.1:8000/docs)
- [Ejemplo para Cali, semana 20 de 2024](http://127.0.0.1:8000/api/v1/ciudades/cali/predicciones/2024/20)

Para el desarrollo local se permiten orígenes de React en los puertos 3000 y 5173. En otro entorno, configurar DENGUE_CORS_ORIGINS con los orígenes permitidos separados por comas. Al publicar, configurar el host y el acceso según el entorno de despliegue.

## Serie e indicadores para el dashboard

`GET /api/v1/ciudades/{ciudad}/dashboard?desde=2024-01-01&hasta=2024-12-28`

El endpoint devuelve el municipio, la cobertura, el umbral aplicado, los indicadores y la serie cronológica. Las fechas ISO son opcionales e inclusivas. Se incluye la semana si algún día cae en el rango. Cada conteo corresponde a la **semana completa**. Si se omiten las fechas, se devuelve la cobertura completa del panel epidemiológico de 2007 a 2025. El parámetro opcional `umbral` cambia la línea de decisión, las alertas y los indicadores de esa consulta.

| Elemento del dashboard | Datos |
|---|---|
| Filtros superiores | Ciudad y rango de fechas. El umbral se puede exponer como control de simulación. |
| Tarjetas | Notificaciones observadas, semanas con exceso, alertas, falsas alertas y excesos omitidos. Mostrar también las semanas con conteo y las semanas evaluables como denominadores. |
| Gráfico de vigilancia | `casos_observados` y `p75_casos` en el eje de conteos. |
| Gráfico del modelo | `probabilidad_exceso` y `umbral_probabilidad` en escala de 0 a 1. |
| Tabla o mapa de calor por año y semana | `anio_epi`, `semana_epi`, `resultado` y los valores de la serie. Al seleccionar una semana con predicción se puede abrir el detalle existente. |
| Comparación territorial | Consultar las tres ciudades con el mismo rango. Usar los códigos DANE para enlazar un mapa municipal en React si se dispone de la capa geográfica. |

Las semanas con datos faltantes mantienen valores `null`. El frontend debe mostrar la falta de observación como un hueco. Las probabilidades corresponden a las semanas elegibles de 2022 a 2025. En un período sin semanas evaluables, falsas alertas y excesos omitidos son `null`. Un cero indica que sí hubo semanas evaluadas y ningún evento de esa clase. Los casos son conteos de notificaciones y no se comparan como tasas de incidencia.

Si ya existe un paquete anterior, volver a ejecutar `scripts/exportar_api_dengue.py` para añadir `historico.csv` por ciudad.

## Ejecutar API y modelos en Docker

Desde la raíz del repositorio, con Docker Desktop activo:

```powershell
docker compose -f docker/api/compose.yaml up -d --build --wait
Invoke-RestMethod http://127.0.0.1:8000/health
```

La imagen incorpora los tres modelos y las tablas del paquete local data/api_dengue. Si faltan esos archivos o cambian los insumos, ejecutar la exportación documentada arriba antes de construir. La imagen funciona sin MLflow, sin los CSV originales y sin montar volúmenes de datos al arrancar. El puerto 8000 se publica solo en la interfaz local. React se conecta desde el puerto 5173 y se puede configurar otro origen con DENGUE_CORS_ORIGINS.

Para detener el servicio, ejecutar docker compose -f docker/api/compose.yaml stop.

## Acerca del modelo

| Método y ruta | Contenido |
|---|---|
| GET /api/v1/ciudades/{ciudad}/modelo | Métricas de la segunda ronda de logística, MLP y persistencia. Incluye las configuraciones probadas, AP de búsqueda, predictores y umbrales de ambos clasificadores. |
| GET /api/v1/ciudades/{ciudad}/datos | Fuentes, cobertura climática y estadísticas epidemiológicas por año. |

Se distinguen la calibración 2022–2023 y las evaluaciones retrospectivas 2024 y 2025. Las métricas no definidas son null. Los gráficos de ajuste muestran AP por configuración en los cortes temporales. Los experimentos originales no guardaron una curva de pérdida por época.

Si se usa un paquete previo, regenerarlo con scripts/exportar_api_dengue.py y reconstruir la imagen para incluir evaluacion.json y estadisticas.json.
