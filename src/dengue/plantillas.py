"""Plantillas XLSX de antecedentes semanales para nuevas predicciones."""
from datetime import date, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
ET.register_namespace("", NS)


def inicio_anio(anio):
    enero = date(anio, 1, 4)
    return enero - timedelta(days=(enero.weekday() + 1) % 7)


def informacion(fecha, hoy=None):
    hoy = hoy or __import__("datetime").datetime.now(ZoneInfo("America/Bogota")).date()
    inicio = fecha - timedelta(days=(fecha.weekday() + 1) % 7)
    actual = hoy - timedelta(days=(hoy.weekday() + 1) % 7)
    if inicio < inicio_anio(2026) or inicio > actual:
        raise ValueError("Selecciona una semana desde el año epidemiológico 2026 hasta la semana actual.")
    anio = fecha.year
    if inicio < inicio_anio(anio):
        anio -= 1
    elif inicio >= inicio_anio(anio + 1):
        anio += 1
    semana = (inicio - inicio_anio(anio)).days // 7 + 1
    return {"anio_epi": anio, "semana_epi": semana, "inicio": inicio, "fin": inicio + timedelta(days=6),
            "ultima_semana_requerida": inicio - timedelta(days=7),
            "filas": (inicio - inicio_anio(2026)).days // 7, "fecha_maxima": hoy}


def hoja(filas, anchos):
    root = ET.Element(f"{{{NS}}}worksheet")
    vista = ET.SubElement(ET.SubElement(root, f"{{{NS}}}sheetViews"), f"{{{NS}}}sheetView", workbookViewId="0")
    ET.SubElement(vista, f"{{{NS}}}pane", ySplit="1", topLeftCell="A2", activePane="bottomLeft", state="frozen")
    cols = ET.SubElement(root, f"{{{NS}}}cols")
    for i, ancho in enumerate(anchos, 1):
        ET.SubElement(cols, f"{{{NS}}}col", min=str(i), max=str(i), width=str(ancho), customWidth="1")
    data = ET.SubElement(root, f"{{{NS}}}sheetData")
    for n, valores in enumerate(filas, 1):
        row = ET.SubElement(data, f"{{{NS}}}row", r=str(n))
        for i, valor in enumerate(valores):
            celda = ET.SubElement(row, f"{{{NS}}}c", r=f"{chr(65+i)}{n}", t="inlineStr")
            ET.SubElement(ET.SubElement(celda, f"{{{NS}}}is"), f"{{{NS}}}t").text = str(valor)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def plantilla(ciudad, nombre, fecha):
    meta = informacion(fecha)
    filas = [["municipio", "anio_epi", "semana_epi", "inicio_semana", "fin_semana",
              "notificaciones", "precipitacion_mm", "temperatura_C", "humedad_relativa"]]
    dia = inicio_anio(2026)
    while dia < meta["inicio"]:
        anio = dia.year
        if dia < inicio_anio(anio):
            anio -= 1
        elif dia >= inicio_anio(anio + 1):
            anio += 1
        filas.append([ciudad, anio, (dia-inicio_anio(anio)).days//7+1, dia.isoformat(),
                      (dia+timedelta(days=6)).isoformat(), "", "", "", ""])
        dia += timedelta(days=7)
    instrucciones = [
        ["Campo", "Instrucción"],
        ["Municipio", nombre],
        ["Semana objetivo", f'{meta["anio_epi"]} - {meta["semana_epi"]}'],
        ["Inicio objetivo", meta["inicio"].isoformat()], ["Fin objetivo", meta["fin"].isoformat()],
        ["Datos a diligenciar", "Completa todas las filas de Datos, hasta la semana anterior al objetivo."],
        ["Calendario", "Las fechas siguen semanas epidemiológicas de domingo a sábado. Conserva fechas y encabezados."],
        ["notificaciones", "Conteo semanal por inicio de síntomas, con las mismas reglas de inclusión del proyecto. Entero >= 0."],
        ["precipitacion_mm", "Lluvia acumulada semanal en milímetros. Número >= 0."],
        ["temperatura_C", "Temperatura media semanal en grados Celsius."],
        ["humedad_relativa", "Humedad relativa media semanal, entre 0 y 100."],
        ["Datos desconocidos", "Deja vacío si falta un dato. Usa 0 únicamente cuando se haya observado cero."],
        ["Semana objetivo", "La semana objetivo está excluida de las filas de entrada."],
        ["Antecedentes hasta 2025", "El sistema utiliza su histórico interno para completar antecedentes previos a 2026."],
        ["Primera semana de 2026", "Si no hay filas en Datos, todos los antecedentes pertenecen al histórico interno."],
    ]
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        z.writestr("_rels/.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", '<workbook xmlns="'+NS+'" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Instrucciones" sheetId="1" r:id="rId1"/><sheet name="Datos" sheetId="2" r:id="rId2"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", hoja(instrucciones, [30, 115]))
        z.writestr("xl/worksheets/sheet2.xml", hoja(filas, [20, 14, 14, 18, 18, 20, 22, 20, 22]))
    return output.getvalue()
