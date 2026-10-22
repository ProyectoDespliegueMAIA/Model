"""Extrae el piloto desde los Excel originales, sin usar fechas ya transformadas."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from zipfile import ZipFile
from lxml import etree as ET
from collections import Counter
import csv
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[1]
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
COLUMNAS = [
    "CONSECUTIVE", "COD_EVE", "COD_PAIS_O", "COD_DPTO_O", "COD_MUN_O",
    "FEC_NOT", "INI_SIN", "FEC_CON", "SEMANA", "ANO", "EDAD", "UNI_MED",
    "SEXO", "AREA", "TIP_SS", "PAC_HOS", "AJUSTE", "FEC_AJU",
    "Estado_final_de_caso", "nom_est_f_caso", "confirmados",
]

def source_dir():
    if os.environ.get("DENGUE_SOURCE_DIR"):
        return Path(os.environ["DENGUE_SOURCE_DIR"])
    for p in ROOT.parents:
        if (p / "Codigo/datos").is_dir():
            return p / "Codigo/datos"
    raise FileNotFoundError("Configurar DENGUE_SOURCE_DIR con los Excel originales.")

def extraer_archivo(path):
    path = Path(path)
    target = ROOT / "data/raw/partes" / f"{path.stem}_76001.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    keys = COLUMNAS + ["ARCHIVO_ORIGEN", "FILA_ORIGEN", "HUELLA_REGISTRO"]
    n_total = n_cali = 0
    with ZipFile(path) as z, target.open("w", encoding="utf-8", newline="") as out:
        strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            with z.open("xl/sharedStrings.xml") as f:
                for _, el in ET.iterparse(f, events=("end",), tag=NS + "si"):
                    strings.append("".join(el.itertext()))
                    el.clear()
                    while el.getprevious() is not None:
                        del el.getparent()[0]

        def value(cell):
            if cell is None:
                return ""
            if cell.get("t") == "inlineStr":
                return "".join(cell.itertext()).strip()
            v = cell.find(NS + "v")
            if v is None:
                return ""
            text = v.text or ""
            return (strings[int(text)] if cell.get("t") == "s" else text).strip()

        writer = csv.DictWriter(out, fieldnames=keys)
        writer.writeheader()
        header = None
        with z.open("xl/worksheets/sheet1.xml") as f:
            for _, row in ET.iterparse(f, events=("end",), tag=NS + "row"):
                cells = {c.get("r").rstrip("0123456789"): c for c in row}
                if header is None:
                    header = {value(c): k for k, c in cells.items()}
                    required = {"COD_DPTO_O", "COD_MUN_O", "COD_PAIS_O", "INI_SIN", "FEC_NOT"}
                    if not required.issubset(header):
                        raise ValueError(f"Esquema incompleto: {path.name}")
                else:
                    n_total += 1
                    dep = value(cells.get(header["COD_DPTO_O"]))
                    mun = value(cells.get(header["COD_MUN_O"]))
                    if dep.zfill(2) == "76" and mun.zfill(3) == "001":
                        d = {k: value(cells.get(header.get(k))) for k in COLUMNAS}
                        d.update(ARCHIVO_ORIGEN=path.name, FILA_ORIGEN=row.get("r"))
                        original = {k: value(cells.get(v)) for k, v in header.items()}
                        d["HUELLA_REGISTRO"] = hashlib.sha256(
                            json.dumps(original, sort_keys=True, ensure_ascii=False).encode("utf-8")
                        ).hexdigest()
                        writer.writerow(d)
                        n_cali += 1
                row.clear()
                while row.getprevious() is not None:
                    del row.getparent()[0]
    print(f"{path.name}: {n_cali:,} registros de Cali / {n_total:,} filas", flush=True)
    return {"archivo": path.name, "sha256": digest, "bytes": path.stat().st_size,
            "filas": n_total, "filas_cali": n_cali, "columnas_extraidas": COLUMNAS}

def main():
    paths = sorted(source_dir().glob("Datos_*_210.xlsx"))
    if not paths:
        raise FileNotFoundError("No hay archivos Datos_*_210.xlsx en la fuente.")
    with ProcessPoolExecutor(max_workers=3) as pool:
        manifest = list(pool.map(extraer_archivo, paths))
    output = ROOT / "data/raw/cali_original.csv"
    with output.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        for i, path in enumerate(paths):
            part = ROOT / "data/raw/partes" / f"{path.stem}_76001.csv"
            with part.open(encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                head = next(reader)
                if i == 0:
                    writer.writerow(head)
                writer.writerows(reader)
    (ROOT / "data/raw/manifiesto_fuentes.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Extracción terminada: {sum(x['filas_cali'] for x in manifest):,} filas", flush=True)

if __name__ == "__main__":
    main()
