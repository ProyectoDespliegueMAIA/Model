# Informe de avance

`informe_avance.docx` e `informe_avance.md` contienen el mismo texto, tablas y figuras. La revisión está dentro de esta carpeta: el Word de la ruta original no permitió lectura ni sobrescritura durante la actualización y se conservó sin forzar su acceso. Corte del informe: 24 de octubre de 2026.

Se verificaron **ocho páginas en Word**, resumen de **253 palabras**, cuatro figuras y veinte ejecuciones de MLflow. Los datos no confirmados de programa y correos permanecen vacíos por instrucción del equipo; se conserva el correo que ya figuraba en el borrador.

## Cobertura de los criterios de evaluación

| Criterio del instructivo | Peso | Evidencia en el informe |
| --- | --- | --- |
| Descripción de la propuesta | 10 % | Página 1: resumen, contexto, objetivos y alcance |
| Recolección y preparación | 15 % | Páginas 2–3: fuentes, auditoría, calendario y trabajos relacionados |
| Construcción de modelos o solución | 35 % | Páginas 3–4: etiqueta P75, predictores, pipeline, particiones, selección de umbral y arquitectura |
| Presentación de resultados | 10 % | Páginas 5–6: comparación por método, periodos y matrices de confusión |
| Análisis de resultados | 20 % | Páginas 7–8: limitaciones, interpretación, mejoras, cronograma y conclusiones |
| Referencias | 5 % | Página 8: referencias numeradas y enlaces |
| Presentación y redacción | 5 % | Ocho páginas revisadas visualmente, siglas explicadas, tablas y figuras con fuente |

La cobertura documenta dónde se atiende cada criterio; no representa una calificación asignada por el curso.

## Contenido de la carpeta

- `informe_avance.docx`: versión Word revisada tras las observaciones.
- `informe_avance.md`: versión Markdown con el mismo contenido.
- `figuras/`: series municipales, arquitectura, F2 de los cinco métodos y matrices de 2024.
- `datos/ejecuciones_mlflow.json`: lectura de las veinte ejecuciones desde el servidor local, con identificadores y métricas.
- `datos/metricas_mlflow.csv`: métricas de los veinte métodos por bloque, contrastadas con las tablas originales. Las métricas indefinidas quedan vacías.
- `datos/perfil_ciudades.csv` y `datos/particiones_temporales.csv`: evidencia agregada de preparación y composición de los bloques.
- `contenido_base.md` y `generar_informe.py`: fuente común y generador de ambas versiones. Los marcadores de tablas del contenido base se resuelven con los datos, no son parte del entregable.

## Reproducción y edición

Editar el contenido base y regenerar permite mantener Word y Markdown sincronizados. El generador comprueba la correspondencia entre métricas locales y MLflow y coteja el texto de los párrafos y celdas de ambas versiones. Las ediciones manuales posteriores en Word no se trasladan automáticamente al Markdown.

El generador usa `python-docx`, pandas, ReportLab y PDFium del runtime de documentos de Codex. La paginación se verificó con exportación nativa de Word y revisión de imágenes; los archivos temporales de esa revisión están en `.cache/informeAvance/`, fuera del control de versiones.

Los datos publicados en esta carpeta son agregados. No se incluyen microdatos individuales, ni se reentrena o modifica ningún modelo durante la elaboración del informe. La API y React se presentan como componentes pendientes, no como un despliegue ya realizado.


## Aclaraciones incorporadas en la revisión

- Página 1: diferencia entre la historia anual que define el P75 y las semanas recientes que usa el modelo; interpretación de F1 y excesos detectados por ciudad.
- Página 2: agregados mensuales como alcance inicial, significado de país y estados, definición del conteo y párrafo explícito de exclusiones antes de la tabla.
- Página 3: faltantes de inicio de síntomas por ciudad, cronologías de 2013, calendario y semana 53 en lenguaje más sencillo; definición de rezagos y ejemplo de la semana 20.
- Página 4: uso de 2007–2011 para historia, entrenamiento 2012–2021 y propósito separado de validación, prueba y evaluación adicional; optimización prevista.
- Páginas 6 y 8: enlaces a la fuente del repositorio y a las rutas de evidencia, con publicación pendiente a cargo del equipo.
- Páginas 7 y 8: perceptrón multicapa MLP y optimización de hiperparámetros explícitos como trabajo futuro, no como resultados ya obtenidos.

El generador escribe por defecto `informeAvance/informe_avance.docx`; admite `--salida-word` para elegir otra ruta. Los modelos, sus métricas y los archivos del experimento no cambian en esta revisión.
