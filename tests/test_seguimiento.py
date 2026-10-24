"""Evita mezclar métodos o convertir métricas indefinidas en resultados ficticios."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dengue.seguimiento import METRICAS, preparar_metricas, huella_registro
from dengue.validacion_modelo import coincide_artefacto
from dengue.pipeline import FEATURES
import hashlib


def fila(bloque="adicional_2025", modelo="logistica_umbral_validado"):
    return {**{key: 0.0 for key in METRICAS}, "bloque": bloque, "modelo": modelo,
            "n": 52, "sensibilidad": np.nan, "f1": np.nan, "roc_auc": np.nan}


def test_metricas_indefinidas_se_omiten_y_ceros_reales_se_conservan():
    values, undefined = preparar_metricas(pd.DataFrame([fila()]))
    assert "adicional_2025.sensibilidad" not in values
    assert "adicional_2025.sensibilidad" in undefined
    assert values["adicional_2025.fp"] == 0
    assert values["adicional_2025.n"] == 52


def test_no_mezcla_metodos_ni_bloques_duplicados():
    with pytest.raises(ValueError):
        preparar_metricas(pd.DataFrame([fila(), fila()]))
    with pytest.raises(ValueError):
        preparar_metricas(pd.DataFrame([fila(), fila("validacion", "persistencia_conteo")]))


def test_infinito_no_se_disfraza_de_metrica_indefinida():
    with pytest.raises(ValueError):
        preparar_metricas(pd.DataFrame([{**fila(), "brier": np.inf}]))


def test_identidad_depende_del_contenido_y_no_de_la_carpeta(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(); b.mkdir()
    (a / "modelo.json").write_text("original")
    (b / "modelo.json").write_text("original")
    first = huella_registro({"municipio": "76001"}, {"validacion.f1": .8}, {"modelo.json": a / "modelo.json"})
    assert first == huella_registro({"municipio": "76001"}, {"validacion.f1": .8}, {"modelo.json": b / "modelo.json"})
    (b / "modelo.json").write_text("cambiado")
    assert first != huella_registro({"municipio": "76001"}, {"validacion.f1": .8}, {"modelo.json": b / "modelo.json"})
    assert first != huella_registro({"municipio": "73001"}, {"validacion.f1": .8}, {"modelo.json": a / "modelo.json"})


def test_huella_historica_admite_saltos_windows_linux_pero_detecta_cambios():
    cfg = {"version_experimento": "ejemplo"}
    panel = pd.DataFrame({"casos": [1, 2, 3]})
    for salto in ["\n", "\r\n"]:
        metadata = {"sha256_panel": hashlib.sha256(panel.to_csv(index=False, lineterminator=salto).encode()).hexdigest(),
                    "config": cfg, "features": FEATURES, "version_experimento": "ejemplo"}
        assert coincide_artefacto(panel, cfg, metadata)
        assert not coincide_artefacto(panel.assign(casos=[1, 2, 4]), cfg, metadata)
