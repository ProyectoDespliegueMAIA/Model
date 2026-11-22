"""API de inferencia histórica para el modelo municipal de dengue."""
from contextlib import asynccontextmanager
from datetime import date
from enum import Enum
import json
import os
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Path as Ruta, Query, Request
from fastapi.middleware.cors import CORSMiddleware
import joblib
import numpy as np
import pandas as pd
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
Umbral = Annotated[float, Query(ge=0, le=1)]


class Ciudad(str, Enum):
    cali = "cali"
    ibague = "ibague"
    villavicencio = "villavicencio"


class Municipio(BaseModel):
    ciudad: Ciudad
    nombre: str
    codigo_dane: str
    modelo: str
    umbral_predeterminado: float
    semanas_disponibles: int
    ventana_clima: str


class Semana(BaseModel):
    anio_epi: int
    semana_epi: int
    inicio_semana: date
    fin_semana: date
    corte_prediccion: date
    bloque: str


class Prediccion(Semana):
    ciudad: Ciudad
    modelo: str
    modo: Literal["retrospectivo"] = "retrospectivo"
    probabilidad_exceso: float
    umbral_probabilidad: float
    umbral_predeterminado: float
    operador_umbral: Literal[">"] = ">"
    alerta: bool
    p75_casos: float
    casos_observados: int
    exceso_observado: bool


def cargar_paquete(ruta):
    municipios = {}
    for ciudad in Ciudad:
        carpeta = ruta / ciudad.value
        meta = json.loads((carpeta / "metadata.json").read_text(encoding="utf-8"))
        modelo = joblib.load(carpeta / "logistica.joblib")
        filas = pd.read_csv(carpeta / "semanas.csv", float_precision="round_trip")
        if (meta["ciudad"] != ciudad.value or meta["predictores"] != list(modelo.feature_names_in_)
                or list(modelo.classes_) != [0, 1] or not 0 <= meta["umbral"] <= 1
                or meta["operador_umbral"] != ">" or filas.empty
                or filas.duplicated(["anio_epi", "semana_epi"]).any()
                or not np.isfinite(filas[meta["predictores"]].to_numpy()).all()):
            raise ValueError(f"Paquete de inferencia incompatible para {ciudad.value}")
        # Los bloques reproducen el mismo cálculo vectorizado del benchmark.
        for _, bloque in filas.groupby("bloque", sort=False):
            filas.loc[bloque.index, "probabilidad"] = modelo.predict_proba(bloque[meta["predictores"]])[:, 1]
        semanas = filas.sort_values("inicio_semana").to_dict("records")
        resumen = Municipio(ciudad=ciudad, nombre=meta["nombre"], codigo_dane=meta["codigo_dane"],
                            modelo=meta["modelo"], umbral_predeterminado=meta["umbral"],
                            semanas_disponibles=len(semanas), ventana_clima=meta["ventana_clima"])
        municipios[ciudad] = (resumen, {(fila["anio_epi"], fila["semana_epi"]): fila for fila in semanas})
    return municipios


def cargar_historicos(ruta):
    historicos = {}
    for ciudad in Ciudad:
        archivo = ruta / ciudad.value / "historico.csv"
        if not archivo.exists():
            continue
        filas = pd.read_csv(archivo, float_precision="round_trip").sort_values("inicio_semana")
        dias = pd.to_datetime(filas.inicio_semana)
        if filas.empty or not dias.diff().dropna().eq(pd.Timedelta(days=7)).all():
            raise ValueError(f"Calendario histórico incompatible para {ciudad.value}")
        historicos[ciudad] = filas.astype(object).where(filas.notna(), None).to_dict("records")
    return historicos


@asynccontextmanager
async def lifespan(app):
    ruta = Path(os.environ.get("DENGUE_API_DATA_DIR", ROOT / "data/api_dengue"))
    app.state.municipios = cargar_paquete(ruta)
    app.state.historicos = cargar_historicos(ruta)
    app.state.informacion = {}
    for ciudad in Ciudad:
        for documento in ("evaluacion", "estadisticas"):
            archivo = ruta / ciudad.value / f"{documento}.json"
            if archivo.is_file():
                app.state.informacion[ciudad, documento] = json.loads(archivo.read_text(encoding="utf-8"))
    yield


app = FastAPI(title="Alertas semanales de dengue", version="1.2.0", lifespan=lifespan)
origenes = os.environ.get("DENGUE_CORS_ORIGINS",
                        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in origenes.split(",") if o.strip()],
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


@app.get("/health")
def salud():
    return {"estado": "ok"}


@app.get("/api/v1/ciudades", response_model=list[Municipio])
def ciudades(request: Request):
    return [resumen for resumen, _ in request.app.state.municipios.values()]


@app.get("/api/v1/ciudades/{ciudad}/semanas", response_model=list[Semana])
def semanas(request: Request, ciudad: Ciudad, anio: Annotated[int | None, Query(ge=2022, le=2025)] = None):
    _, filas = request.app.state.municipios[ciudad]
    return [Semana(**fila) for fila in filas.values() if anio is None or fila["anio_epi"] == anio]


@app.get("/api/v1/ciudades/{ciudad}/predicciones/{anio}/{semana}", response_model=Prediccion)
def prediccion(request: Request, ciudad: Ciudad, anio: Annotated[int, Ruta(ge=2022, le=2025)],
               semana: Annotated[int, Ruta(ge=1, le=53)], umbral: Umbral | None = None):
    resumen, filas = request.app.state.municipios[ciudad]
    fila = filas.get((anio, semana))
    if fila is None:
        raise HTTPException(404, "Semana sin predicción histórica disponible para la ciudad")
    aplicado = resumen.umbral_predeterminado if umbral is None else umbral
    return Prediccion(**Semana(**fila).model_dump(), ciudad=ciudad, modelo=resumen.modelo,
                      probabilidad_exceso=fila["probabilidad"], umbral_probabilidad=aplicado,
                      umbral_predeterminado=resumen.umbral_predeterminado,
                      alerta=fila["probabilidad"] > aplicado, p75_casos=fila["umbral_casos"],
                      casos_observados=int(fila["casos"]), exceso_observado=bool(fila["exceso"]))


class PuntoDashboard(BaseModel):
    precipitacion_mm: float | None = None
    temperatura_C: float | None = None
    humedad_relativa: float | None = None
    dias_clima: int | None = None
    anio_epi: int
    semana_epi: int
    inicio_semana: date
    fin_semana: date
    corte_prediccion: date
    casos_observados: int | None
    p75_casos: float | None
    exceso_observado: bool | None
    probabilidad_exceso: float | None
    alerta: bool | None
    bloque: str | None
    resultado: Literal["acierto_alerta", "falsa_alerta", "exceso_omitido", "acierto_sin_alerta"] | None


class IndicadoresDashboard(BaseModel):
    semanas: int
    semanas_con_conteo: int
    semanas_con_etiqueta: int
    semanas_con_prediccion: int
    semanas_evaluables: int
    notificaciones_observadas: int | None
    semanas_con_exceso_observado: int | None
    alertas_del_modelo: int | None
    aciertos_alerta: int | None
    falsas_alertas: int | None
    excesos_omitidos: int | None
    aciertos_sin_alerta: int | None


class Dashboard(BaseModel):
    municipio: Municipio
    modo: Literal["retrospectivo"] = "retrospectivo"
    desde: date
    hasta: date
    cobertura_desde: date
    cobertura_hasta: date
    umbral_probabilidad: float
    operador_umbral: Literal[">"] = ">"
    indicadores: IndicadoresDashboard
    serie: list[PuntoDashboard]


@app.get("/api/v1/ciudades/{ciudad}/dashboard", response_model=Dashboard)
def dashboard(request: Request, ciudad: Ciudad, desde: date | None = None, hasta: date | None = None,
              umbral: Umbral | None = None):
    municipio, predicciones = request.app.state.municipios[ciudad]
    historico = request.app.state.historicos.get(ciudad)
    if historico is None:
        raise HTTPException(503, "Reexportar el paquete de datos para habilitar el dashboard")
    inicio = date.fromisoformat(historico[0]["inicio_semana"])
    fin = date.fromisoformat(historico[-1]["fin_semana"])
    desde = inicio if desde is None else desde
    hasta = fin if hasta is None else hasta
    if desde > hasta:
        raise HTTPException(422, "La fecha desde debe ser anterior o igual a hasta")
    aplicado = municipio.umbral_predeterminado if umbral is None else umbral
    estados = {
        (True, True): "acierto_alerta", (True, False): "falsa_alerta",
        (False, True): "exceso_omitido", (False, False): "acierto_sin_alerta",
    }
    serie = []
    for fila in historico:
        if date.fromisoformat(fila["fin_semana"]) < desde or date.fromisoformat(fila["inicio_semana"]) > hasta:
            continue
        pred = predicciones.get((fila["anio_epi"], fila["semana_epi"]))
        prob = pred["probabilidad"] if pred is not None else None
        alerta = prob > aplicado if prob is not None else None
        exceso = bool(fila["exceso"]) if fila["exceso"] is not None else None
        serie.append(PuntoDashboard(
            precipitacion_mm=fila.get("precipitacion_mm"), temperatura_C=fila.get("temperatura_C"),
            humedad_relativa=fila.get("humedad_relativa"), dias_clima=fila.get("dias_clima"),
            anio_epi=fila["anio_epi"], semana_epi=fila["semana_epi"],
            inicio_semana=fila["inicio_semana"], fin_semana=fila["fin_semana"],
            corte_prediccion=fila["corte_prediccion"], casos_observados=fila["casos"],
            p75_casos=fila["umbral_casos"], exceso_observado=exceso,
            probabilidad_exceso=prob, alerta=alerta, bloque=pred["bloque"] if pred else None,
            resultado=estados.get((alerta, exceso)),
        ))
    conteos = [p.casos_observados for p in serie if p.casos_observados is not None]
    etiquetas = [p.exceso_observado for p in serie if p.exceso_observado is not None]
    alertas = [p.alerta for p in serie if p.alerta is not None]
    resultados = [p.resultado for p in serie if p.resultado is not None]
    indicadores = IndicadoresDashboard(
        semanas=len(serie), semanas_con_conteo=len(conteos), semanas_con_etiqueta=len(etiquetas),
        semanas_con_prediccion=len(alertas), semanas_evaluables=len(resultados),
        notificaciones_observadas=sum(conteos) if conteos else None,
        semanas_con_exceso_observado=sum(etiquetas) if etiquetas else None,
        alertas_del_modelo=sum(alertas) if alertas else None,
        aciertos_alerta=resultados.count("acierto_alerta") if resultados else None,
        falsas_alertas=resultados.count("falsa_alerta") if resultados else None,
        excesos_omitidos=resultados.count("exceso_omitido") if resultados else None,
        aciertos_sin_alerta=resultados.count("acierto_sin_alerta") if resultados else None,
    )
    return Dashboard(municipio=municipio, desde=desde, hasta=hasta, cobertura_desde=inicio,
                     cobertura_hasta=fin, umbral_probabilidad=aplicado, indicadores=indicadores, serie=serie)


def consultar_informacion(request, ciudad, documento):
    contenido = request.app.state.informacion.get((ciudad, documento))
    if contenido is None:
        raise HTTPException(503, "Reexportar el paquete de datos para habilitar esta información")
    return {"ciudad": ciudad, **contenido}


@app.get("/api/v1/ciudades/{ciudad}/modelo", summary="Evaluación comparativa y búsqueda de modelos")
def informacion_modelo(request: Request, ciudad: Ciudad):
    return consultar_informacion(request, ciudad, "evaluacion")


@app.get("/api/v1/ciudades/{ciudad}/datos", summary="Fuentes y estadísticas de cobertura")
def informacion_datos(request: Request, ciudad: Ciudad):
    return consultar_informacion(request, ciudad, "estadisticas")

@app.get("/api/v1/plantillas/periodo", summary="Consultar la semana objetivo de una plantilla")
def periodo_plantilla(fecha_objetivo: date):
    from dengue.plantillas import informacion
    try:
        return informacion(fecha_objetivo)
    except ValueError as error:
        raise HTTPException(422, str(error))


@app.get("/api/v1/ciudades/{ciudad}/plantilla", summary="Descargar plantilla Excel de antecedentes")
def descargar_plantilla(request: Request, ciudad: Ciudad, fecha_objetivo: date):
    from fastapi.responses import Response
    from dengue.plantillas import plantilla
    try:
        nombre = request.app.state.municipios[ciudad][0].nombre
        contenido = plantilla(ciudad.value, nombre, fecha_objetivo)
    except ValueError as error:
        raise HTTPException(422, str(error))
    return Response(contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="plantilla_{ciudad.value}_{fecha_objetivo}.xlsx"'})

@app.post("/api/v1/ciudades/{ciudad}/plantilla/validar", summary="Validar los antecedentes de un Excel")
async def validar_plantilla(request: Request, ciudad: Ciudad, fecha_objetivo: date):
    from dengue.plantillas import informacion
    from dengue.validar_plantilla import validar_archivo, MAX_BYTES
    from starlette.concurrency import run_in_threadpool
    try:
        informacion(fecha_objetivo)
    except ValueError as error:
        raise HTTPException(422, str(error))
    contenido = bytearray()
    async for fragmento in request.stream():
        contenido.extend(fragmento)
        if len(contenido) > MAX_BYTES:
            raise HTTPException(413, "El archivo supera el límite de 5 MB.")
    nombre = request.app.state.municipios[ciudad][0].nombre
    return await run_in_threadpool(validar_archivo, bytes(contenido), ciudad.value, nombre, fecha_objetivo)


@app.post("/api/v1/ciudades/{ciudad}/prediccion-carga", summary="Predecir la semana objetivo desde un Excel")
async def prediccion_carga(request: Request, ciudad: Ciudad, fecha_objetivo: date,
                           descargar: bool = False):
    from dengue.validar_plantilla import validar_archivo, MAX_BYTES
    from dengue.inferencia_carga import predecir, excel_resultado
    from dengue.plantillas import informacion
    from fastapi.responses import Response
    from starlette.concurrency import run_in_threadpool
    try:
        informacion(fecha_objetivo)
    except ValueError as error:
        raise HTTPException(422, str(error))
    contenido = bytearray()
    async for fragmento in request.stream():
        contenido.extend(fragmento)
        if len(contenido)>MAX_BYTES:
            raise HTTPException(413, "El archivo supera el límite de 5 MB.")
    contenido = bytes(contenido)
    nombre = request.app.state.municipios[ciudad][0].nombre
    validacion = await run_in_threadpool(validar_archivo, contenido, ciudad.value, nombre, fecha_objetivo)
    if not validacion["valido"]:
        raise HTTPException(422, {"mensaje":"Corrige el archivo antes de predecir.", "errores":validacion["errores"]})
    try:
        resultado = await run_in_threadpool(predecir, contenido, ciudad.value, fecha_objetivo)
    except ValueError as error:
        raise HTTPException(422, str(error))
    if descargar:
        archivo = await run_in_threadpool(excel_resultado, resultado)
        return Response(archivo, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="prediccion_{ciudad.value}_{fecha_objetivo}.xlsx"'})
    return resultado
