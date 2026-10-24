# MLflow en Docker

Servidor y cliente de verificación con **MLflow 3.17.2** en la imagen oficial. Requiere Docker Desktop con contenedores Linux y Docker Compose. La imagen se construye desde `ghcr.io/mlflow/mlflow:v3.17.2` y verifica la versión incluida. El archivo `requirements.txt` de esta carpeta declara esa misma versión. La dependencia del proyecto también está fijada en el `requirements.txt` de la raíz.

## Iniciar

Desde la raíz del repositorio:

```powershell
docker compose -f docker/mlflow/compose.yaml up -d --build --wait
```

Abrir [MLflow](http://localhost:5000). El puerto se publica en `127.0.0.1:5000` para uso local. El primer inicio descarga la imagen base y las dependencias.

## Verificar desde otro contenedor

```powershell
docker compose -f docker/mlflow/compose.yaml --profile herramientas run --rm cliente
```

El cliente espera al servidor saludable y registra un parámetro, una métrica y un JSON sintético. Después recupera la ejecución y descarga el archivo mediante HTTP. Se guarda en el experimento `verificacion_infraestructura`; no representa entrenamiento ni resultados de dengue. Las ejecuciones posteriores reutilizan esa prueba para comprobar la persistencia.

```powershell
docker compose -f docker/mlflow/compose.yaml ps
docker compose -f docker/mlflow/compose.yaml logs --tail 50 mlflow
```

## Persistencia y conexión

El volumen Docker `modelo-dengue-mlflow_mlflow_data` contiene:

- `/mlflow/mlflow.db`: SQLite con experimentos, parámetros, métricas y metadatos.
- `/mlflow/artifacts`: modelos, gráficos y demás artefactos.

El servidor recibe y entrega los artefactos por HTTP. Los clientes no necesitan montar el volumen ni acceder a rutas internas del contenedor. La base y sus archivos quedan en el almacenamiento de Docker Desktop, fuera de la sincronización de OneDrive.

| Origen del cliente | Tracking URI |
| --- | --- |
| Python/Jupyter en Windows | `http://127.0.0.1:5000` |
| Contenedor en este Compose | `http://mlflow:5000` |

El cliente de prueba y el servidor se ejecutan completamente en Docker. Los notebooks actuales conservan su entorno y sus resultados. Para conectar sus entrenamientos más adelante se deberá disponer del cliente Python fijado en las dependencias y configurar `MLFLOW_TRACKING_URI`; el servicio `importador` permite registrar los experimentos existentes sin modificar el entrenamiento; ver `../../docs/seguimiento_mlflow.md`.

## Detener y volver a iniciar

```powershell
docker compose -f docker/mlflow/compose.yaml down
docker compose -f docker/mlflow/compose.yaml up -d --wait
```

`down` conserva el volumen. La opción `--volumes` lo elimina, incluidos los experimentos y artefactos almacenados. No hace falta usarla para reiniciar o reconstruir la imagen.

Para comprobar la conservación al recrear el contenedor:

```powershell
docker compose -f docker/mlflow/compose.yaml up -d --force-recreate --wait
docker compose -f docker/mlflow/compose.yaml --profile herramientas run --rm cliente
```

Debe recuperar el mismo `run_id` e informar `reutilizado: true`.

## Referencias

- [MLflow Tracking Server](https://mlflow.org/docs/latest/self-hosting/architecture/tracking-server/).
- [Almacenamiento de metadatos](https://mlflow.org/docs/latest/self-hosting/architecture/backend-store/).

El registro de referencias existentes se documenta en [seguimiento MLflow](../../docs/seguimiento_mlflow.md). La integración automática en nuevos entrenamientos es el siguiente paso.
