"""Documenta la evaluación exploratoria de Ibagué sin cambiar la selección de ciudades."""
from pathlib import Path
import sys
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dengue.pipeline import config, raiz_salida
from resumir_ciudades import tabla


def main():
    calidad, particiones, metricas, anuales = [], [], [], []
    for slug in ["piloto", "medellin", "villavicencio", "ibague"]:
        cfg = config(slug)
        salida = raiz_salida(cfg)
        nombre = cfg["nombre_municipio"]
        q = json.loads((salida / "reports/resumen_eda.json").read_text(encoding="utf-8"))
        calidad.append({"Ciudad": nombre, "Extraídos": q["filas_extraidas"],
            "Incluidos": q["filas_finales"], "Sin inicio válido": q["ini_sin_no_parseable"],
            "Semanas sin registros": q["semanas_sin_registros_no_imputadas"],
            "Semanas elegibles": q["semanas_elegibles_modelo"],
            "Notificación anterior a síntomas": q["anomalias_notificacion_conservadas"],
            "Síntomas posteriores a consulta": q["sintomas_posteriores_consulta"]})
        p = pd.read_csv(salida / "reports/tables/particiones_temporales.csv")
        p.insert(0, "ciudad", nombre)
        p["sin_exceso"] = p.filas - p.positivos
        particiones.append(p)
        m = pd.read_csv(salida / "reports/tables/metricas_logistica.csv")
        m.insert(0, "ciudad", nombre)
        metricas.append(m)
        prefijo = "cali" if slug == "piloto" else slug
        panel = pd.read_csv(salida / f"data/processed/{prefijo}_panel_semanal.csv")
        anual = panel.loc[panel.elegible_modelo].groupby("anio_epi").exceso.agg(
            elegibles="count", excesos="sum")
        anual["sin_exceso"] = anual.elegibles - anual.excesos
        anual.insert(0, "ciudad", nombre)
        anuales.append(anual.reset_index())
        if slug == "ibague":
            q_ibague = q
            audit = pd.read_csv(salida / "reports/tables/auditoria_limpieza.csv")
            fechas = pd.read_csv(salida / "reports/tables/fechas_por_archivo.csv")
            umbrales = pd.read_csv(salida / "reports/tables/seleccion_umbral_validacion.csv")
            metadata = json.loads((salida / f"modelos/logistica_ibague_{cfg['version_experimento']}.json").read_text(encoding="utf-8"))
    calidad = pd.DataFrame(calidad)
    particiones = pd.concat(particiones, ignore_index=True)
    metricas = pd.concat(metricas, ignore_index=True)
    anuales = pd.concat(anuales, ignore_index=True)
    resumen = metricas.loc[metricas.bloque.ne("entrenamiento") & metricas.modelo.isin(
        ["logistica_umbral_validado", "persistencia_conteo"]),
        ["ciudad", "bloque", "modelo", "n", "prevalencia", "umbral_probabilidad",
         "sensibilidad", "precision", "f1", "f2", "especificidad", "fp", "fn"]].copy()
    for c in ["prevalencia", "sensibilidad", "precision", "f1", "f2", "especificidad"]:
        resumen[c] *= 100
        resumen.rename(columns={c: c + " (%)"}, inplace=True)
    destino = ROOT / "reports/evaluacion_ibague"
    destino.mkdir(parents=True, exist_ok=True)
    for nombre, df in [("calidad", calidad), ("particiones", particiones),
                       ("metricas", metricas), ("clases_por_anio", anuales)]:
        df.to_csv(destino / f"{nombre}.csv", index=False)
    validacion = particiones.loc[particiones.bloque.eq("validacion")]
    vi = validacion.loc[validacion.ciudad.eq("Ibagué")].iloc[0]
    vm = validacion.loc[validacion.ciudad.eq("Medellín")].iloc[0]
    valoracion = (
        f"Ibagué aporta {int(vi.positivos)} semanas con exceso y {int(vi.sin_exceso)} sin exceso "
        f"en validación, frente a {int(vm.positivos)} y {int(vm.sin_exceso)} en Medellín. "
        "Esto permite valorar la disponibilidad de ambas clases sin elegir la ciudad por su F1 de prueba. "
        "Las semanas consecutivas pueden pertenecer al mismo episodio: más semanas no equivalen a más brotes independientes."
    )
    if umbrales.f2_validacion.max() == 0:
        valoracion += " Toda la rejilla obtiene F2=0; el umbral resulta solo del desempate y no acredita capacidad de alerta."
    desarrollo_val = anuales.loc[anuales.ciudad.eq("Ibagué") & anuales.anio_epi.between(
        cfg["fin_entrenamiento"]+1,cfg["fin_validacion"])]
    concentracion = desarrollo_val.sort_values("excesos",ascending=False).iloc[0]
    logistica_ibague = metricas.loc[metricas.ciudad.eq("Ibagué") &
        metricas.modelo.eq("logistica_umbral_validado")].set_index("bloque")
    prueba = logistica_ibague.loc["prueba_2024"]
    extra = logistica_ibague.loc["adicional_2025"]
    auditoria_fuente = salida / "reports/auditoria_fuente_2013.json"
    nota_fuente = ""
    if auditoria_fuente.exists():
        fuente = json.loads(auditoria_fuente.read_text(encoding="utf-8"))
        nota_fuente = ("El Excel de 2013 tiene una huella binaria distinta del manifiesto histórico de Cali. "
            f"Se reextrajeron sus {fuente['filas_cali_actuales']} registros de Cali para comprobar el contenido: "
            f"coincidencia del multiconjunto de huellas de las 69 columnas originales = {fuente['mismas_huellas_69_columnas']}. "
            "No se determinó la causa del cambio binario ni se modificó el experimento de Cali. "
            "Los manifiestos actuales de Ibagué, Medellín y Villavicencio coinciden en las 19 huellas de fuente.")
    texto = f"""# Evaluación de Ibagué como ciudad candidata

## Alcance y protocolo

Se evalúa Ibagué (73001) desde los 19 Excel originales, sin reemplazar ni reentrenar Medellín, Cali o Villavicencio. La selección definitiva de las tres ciudades sigue siendo una decisión pendiente.

Se mantiene el protocolo v1_ini_sin: evento 210, municipio de ocurrencia, país 170 y estados 2, 3 y 5; inicio de síntomas sin sustituciones, ausencia de registros como desconocido, calendario semanal completo y semana 53 conservada. La etiqueta es superar estrictamente el P75 de la misma semana en los cinco años anteriores, exigiendo cinco antecedentes válidos. Es una definición operacional, no una declaración oficial de brote.

La logística L2 C=1 y el escalador se ajustan solo hasta 2021. Los diez predictores son los mismos de las otras ciudades. El umbral de probabilidad se selecciona con F2 en 2022–2023 (rejilla 0,10 a 0,90, paso 0,05, empate favorece mayor umbral). Se informa 2024 y, adicionalmente, 2025 sin reajustar. Se compara con persistencia y otras referencias simples; cada municipio se entrena por separado.

## Calidad y cobertura observada

{tabla(calidad)}

En Ibagué hay {q_ibague['semanas_panel']} semanas en el panel y {q_ibague['semanas_con_etiqueta']} con etiqueta disponible. El inicio de síntomas es interpretable en {q_ibague['porcentaje_inicio_valido']:.4f} % de los registros auditados. Presencia de registros no certifica cobertura completa. Las cronologías negativas se conservan con bandera; su detalle por archivo está abajo.

### Auditoría de exclusiones de Ibagué

{tabla(audit)}

## Disponibilidad de clases

{tabla(particiones)}

{valoracion}

### Clases por año en Ibagué

{tabla(anuales.loc[anuales.ciudad.eq('Ibagué')])}

## Comparación en validación (2022–2023)

{tabla(resumen.loc[resumen.bloque.eq('validacion')])}

El umbral seleccionado de Ibagué es {metadata['umbral_probabilidad']:.2f}, con F2 máximo de validación {umbrales.f2_validacion.max():.4f}. No se optimizó con 2024 ni con 2025. El guion largo representa una métrica no definida, no cero.

## Evaluación posterior del primer modelo

{tabla(resumen.loc[resumen.ciudad.eq('Ibagué') & resumen.bloque.ne('validacion')])}

Estos bloques permiten describir errores y falsas alarmas; no deben emplearse para escoger reiteradamente ciudades o hiperparámetros y luego presentarse como pruebas independientes. Esta evaluación ocurre después de observar resultados de otras ciudades; su selección es exploratoria. Las AUC se omiten en bloques de una sola clase y no debe confundirse precisión con exactitud global.

## Fechas y anomalías de Ibagué

{tabla(fechas)}

## Interpretación y siguiente decisión

**Valoración de Ibagué:** su candidatura es más favorable que la de Medellín para el ejercicio actual por su continuidad observada (3 semanas sin filas frente a 54) y por la disponibilidad de ambas clases en validación (38/55 frente a 2/92). Esta valoración no equivale a certificar la cobertura ni demuestra que la logística sea el mejor modelo. Se recomienda Ibagué como posible sustituta, manteniendo la selección definitiva pendiente y conservando Medellín como experimento documentado.

En validación, {int(concentracion.excesos)} de los {int(vi.positivos)} excesos se concentran en {int(concentracion.anio_epi)}: hace falta comprobar estabilidad en más cortes y episodios. En 2024 la logística emite {int(prueba.fp+prueba.tp)} alertas entre {int(prueba.n)} semanas, con {int(prueba.fp)} falsas alarmas y {int(prueba.fn)} excesos omitidos; un F1 alto debe leerse junto a esa falta de discriminación binaria. En 2025 hay {int(extra.fn+extra.tp)} excesos entre {int(extra.n)} semanas: genera {int(extra.fp)} falsas alarmas, con precisión {100*extra.precision:.1f} % y F1 {100*extra.f1:.1f} %. No es una solución lista para uso operacional.

La candidatura debe justificarse con calidad, continuidad y disponibilidad de ambas clases en desarrollo, junto con pertinencia epidemiológica. Comparar F1 entre municipios no prueba que uno sea más predecible: las prevalencias y etiquetas históricas cambian. Los resultados del primer modelo no sustituyen esa justificación.

Falta validar cobertura con una fuente externa y simular qué información estaba disponible en cada corte: se usan conteos y estados finales, que pudieron notificarse después. Antes de comparar algoritmos o cerrar la selección, conviene predefinir varios cortes de validación temporal dentro del periodo de desarrollo, examinar diversidad de episodios y sensibilidad del canal. Los valores de 2024 y 2025 ya observados deben tratarse como evaluación retrospectiva exploratoria en decisiones posteriores.

## Trazabilidad de fuentes

{nota_fuente}

Panel SHA-256: `{metadata['sha256_panel']}`.
"""
    (ROOT / "docs/evaluacion_ibague.md").write_text(texto, encoding="utf-8")
    print(valoracion)
    print(resumen.loc[resumen.ciudad.eq("Ibagué")].to_string(index=False))


if __name__ == "__main__":
    main()
