"""Validación de las plantillas de antecedentes, sin ejecutar inferencia."""
from datetime import date, datetime
from io import BytesIO
import math
from zipfile import BadZipFile, ZipFile

from openpyxl import load_workbook
from dengue.plantillas import plantilla, informacion

MAX_BYTES = 5 * 1024 * 1024


def validar_archivo(contenido, ciudad, nombre, fecha):
    errores = []
    def error(hoja, fila, columna, mensaje):
        errores.append(dict(hoja=hoja, fila=fila, columna=columna, mensaje=mensaje))
    def salida(filas=0):
        return dict(valido=not errores, municipio=ciudad, semana_objetivo=informacion(fecha),
                    filas_validar=filas, total_errores=len(errores), errores=errores)
    if not contenido or len(contenido) > MAX_BYTES:
        error("Archivo", None, None, "El archivo debe contener un Excel .xlsx de hasta 5 MB.")
        return salida()
    try:
        with ZipFile(BytesIO(contenido)) as z:
            if len(z.infolist()) > 200 or sum(i.file_size for i in z.infolist()) > 20 * 1024 * 1024:
                raise ValueError("El contenido del Excel excede el tamaño permitido.")
        libro = load_workbook(BytesIO(contenido), read_only=True, data_only=False, keep_links=False)
    except Exception:
        error("Archivo", None, None, "No se pudo abrir el archivo. Usa una plantilla Excel .xlsx válida.")
        return salida()
    try:
        for hoja in ("Instrucciones", "Datos"):
            if hoja not in libro.sheetnames:
                error(hoja, None, None, "Falta esta hoja. Descarga nuevamente la plantilla.")
        if errores:
            return salida()
        esperado = load_workbook(BytesIO(plantilla(ciudad, nombre, fecha)), read_only=True)
        try:
            instrucciones = list(libro["Instrucciones"].iter_rows(min_row=2, max_row=5, max_col=2, values_only=True))
            originales = list(esperado["Instrucciones"].iter_rows(min_row=2, max_row=5, max_col=2, values_only=True))
            for numero, (actual, original) in enumerate(zip(instrucciones, originales), 2):
                if actual != original:
                    error("Instrucciones", numero, "A:B", "El municipio o la semana objetivo no coincide con la selección. Usa la plantilla correspondiente.")
            referencias = list(esperado["Datos"].values)
        finally:
            esperado.close()
        hoja = libro["Datos"]
        hoja.calculate_dimension(force=True)
        if hoja.max_row > 10000 or hoja.max_column > 30:
            error("Datos", None, None, "La hoja excede el tamaño previsto para la plantilla.")
            return salida()
        filas = list(hoja.iter_rows(values_only=True))
        while filas and all(v is None or v == "" for v in filas[-1]):
            filas.pop()
        if not filas or tuple(filas[0]) != tuple(referencias[0]):
            error("Datos", 1, "A:I", "Los encabezados deben conservarse exactamente como en la plantilla.")
            return salida()
        n = len(filas)-1
        if n != len(referencias)-1:
            error("Datos", None, None, f"Se requieren {len(referencias)-1} filas semanales; se encontraron {n}.")
        vistos = set()
        columnas = referencias[0]
        for numero, fila in enumerate(filas[1:], 2):
            if numero > len(referencias):
                error("Datos", numero, "D", "Fila adicional fuera del período solicitado.")
                continue
            referencia = referencias[numero-1]
            for indice in range(5):
                valor, requerido = fila[indice], referencia[indice]
                if isinstance(valor, datetime):
                    valor = valor.date().isoformat()
                elif isinstance(valor, date):
                    valor = valor.isoformat()
                if indice in (1,2):
                    correcto = str(valor) == str(requerido)
                else:
                    correcto = valor == requerido
                if not correcto:
                    error("Datos", numero, f"{chr(65+indice)} · {columnas[indice]}", f"Debe ser {requerido}. Conserva el orden semanal de la plantilla.")
            if str(fila[3]) in vistos:
                error("Datos", numero, "D · inicio_semana", "La semana está duplicada.")
            vistos.add(str(fila[3]))
            for indice in range(5,9):
                valor = fila[indice]
                columna = f"{chr(65+indice)} · {columnas[indice]}"
                if valor is None or valor == "":
                    error("Datos", numero, columna, "Completa este dato. Usa cero solo si se observó cero.")
                    continue
                if isinstance(valor, bool) or (isinstance(valor,str) and valor.startswith("=")):
                    error("Datos", numero, columna, "Introduce un número, sin fórmulas.")
                    continue
                try:
                    numero_valor = float(valor)
                    if not math.isfinite(numero_valor):
                        raise ValueError()
                except (TypeError, ValueError):
                    error("Datos", numero, columna, "Introduce un número válido. En Excel usa celdas numéricas.")
                    continue
                if indice in (5,6) and numero_valor < 0:
                    error("Datos", numero, columna, "El valor debe ser mayor o igual a cero.")
                if indice == 5 and not numero_valor.is_integer():
                    error("Datos", numero, columna, "El conteo debe ser un número entero.")
                if indice == 8 and not 0 <= numero_valor <= 100:
                    error("Datos", numero, columna, "La humedad debe estar entre 0 y 100.")
        return salida(n)
    finally:
        libro.close()
