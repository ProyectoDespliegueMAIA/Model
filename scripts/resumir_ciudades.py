"""Consolida auditoría y métricas agregadas; no vuelve a entrenar ni selecciona modelos."""
from pathlib import Path
import sys
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dengue.pipeline import config, raiz_salida


def tabla(df):
    def valor(v):
        if pd.isna(v):
            return "—"
        if isinstance(v, float):
            return f"{v:.2f}"
        return str(v)
    return "\n".join([
        "| " + " | ".join(map(str, df.columns)) + " |",
        "| " + " | ".join(["---"] * len(df.columns)) + " |",
        *["| " + " | ".join(valor(v) for v in row) + " |" for row in df.itertuples(index=False, name=None)]])


def main():
    eda, metricas, particiones, detalles = [], [], [], []
    for slug in ["piloto", "medellin", "villavicencio"]:
        cfg = config(slug)
        city = cfg["nombre_municipio"]
        salida = raiz_salida(cfg)
        resumen = json.loads((salida / "reports/resumen_eda.json").read_text(encoding="utf-8"))
        eda.append({"Ciudad": city, "Extraídos": resumen["filas_extraidas"],
            "Incluidos": resumen["filas_finales"],
            "Sin inicio válido": resumen["ini_sin_no_parseable"],
            "Inicio válido (%)": resumen["porcentaje_inicio_valido"],
            "Semanas sin filas": resumen["semanas_sin_registros_no_imputadas"],
            "Semanas elegibles": resumen["semanas_elegibles_modelo"],
            "Notificación anterior a síntomas": resumen["anomalias_notificacion_conservadas"],
            "Síntomas posteriores a consulta": resumen["sintomas_posteriores_consulta"]})
        m = pd.read_csv(salida / "reports/tables/metricas_logistica.csv")
        m.insert(0, "ciudad", city)
        metricas.append(m)
        p = pd.read_csv(salida / "reports/tables/particiones_temporales.csv")
        p.insert(0, "ciudad", city)
        particiones.append(p)
        anual = pd.read_csv(salida / "reports/tables/resumen_anual.csv")
        detalles.append(f"### {city}\n\n" + tabla(anual))
    eda = pd.DataFrame(eda)
    metricas = pd.concat(metricas, ignore_index=True)
    particiones = pd.concat(particiones, ignore_index=True)
    dest = ROOT / "reports/comparacion_ciudades"
    dest.mkdir(parents=True, exist_ok=True)
    eda.to_csv(dest / "auditoria_resumen.csv", index=False)
    metricas.to_csv(dest / "metricas_logistica_tres_ciudades.csv", index=False)
    particiones.to_csv(dest / "particiones.csv", index=False)
    comparacion = metricas.loc[metricas.bloque.ne("entrenamiento") & metricas.modelo.isin(
        ["logistica_umbral_validado", "persistencia_conteo"]),
        ["ciudad", "bloque", "modelo", "n", "prevalencia", "umbral_probabilidad",
         "sensibilidad", "precision", "f1", "especificidad", "fp", "fn"]].copy()
    for c in ["prevalencia", "sensibilidad", "precision", "f1", "especificidad"]:
        comparacion[c] *= 100
    comparacion.rename(columns={c: c + " (%)" for c in [
        "prevalencia", "sensibilidad", "precision", "f1", "especificidad"]}, inplace=True)
    texto = """# Primer análisis y regresión logística en tres ciudades

## Protocolo común

Cali (76001), Medellín (05001) y Villavicencio (50001) se preparan y modelan por separado desde los 19 Excel originales de 2007–2025. Se verifica evento 210, país 170, municipio de ocurrencia y estados finales 2, 3 y 5. La inclusión de estos estados reproduce el piloto; no equivale a contar únicamente casos confirmados.

Se usa exclusivamente INI_SIN, sin sustituirla por notificación. Se excluyen fechas ausentes/inválidas y fuera del calendario; se conserva y señala la notificación anterior a síntomas. Una inconsistencia con consulta también se informa: no debe afirmarse que elegir INI_SIN elimina todas las contradicciones de una nueva ciudad.

Cada panel tiene 992 semanas y 28 columnas. Las semanas sin registros se mantienen como desconocidas. La semana 53 permanece en la secuencia; sin cinco antecedentes comparables no tiene etiqueta. Los diez predictores son seis rezagos (1, 2, 3, 4, 8 y 12), media y desviación de las cuatro semanas anteriores, seno y coseno del calendario.

Exceso significa superar estrictamente el P75 de la misma semana en los cinco años anteriores, calculado dentro de cada municipio. La regresión estima probabilidad de exceso la semana siguiente al corte nominal, no el conteo de casos. Se ajustan StandardScaler y logística L2 C=1 solo hasta 2021; el umbral se elige por F2 en 2022–2023 (rejilla 0,10–0,90, pasos 0,05; empate favorece umbral mayor). Se evalúan 2024 y, adicionalmente, 2025 sin reajustar. Cada municipio tiene un escalador, coeficientes y umbral independientes.

## Calidad y disponibilidad

""" + tabla(eda) + "\n\n## Particiones temporales\n\n" + tabla(particiones)
    texto += "\n\n## Métricas comparables dentro de cada ciudad\n\n" + tabla(comparacion)
    texto += """

La persistencia pronostica el último conteo y lo contrasta con el umbral de casos de la semana objetivo. Es una referencia binaria; sus valores 0/1 no son probabilidades calibradas. Las tablas locales incluyen también logística a umbral 0,5, prevalencia constante, siempre alerta, F2, AP, ROC AUC, Brier y matrices de confusión. El guion largo indica una métrica no definida; no significa cero. Se debe interpretar sensibilidad y F1 junto a prevalencia, especificidad y falsas alarmas.

## Lectura del primer resultado

**Medellín:** de 56.884 registros extraídos se incluyen 56.877; se excluyen seis sin inicio válido y uno fuera del calendario. Hay 54 semanas sin registros. Las 1.267 notificaciones anteriores a síntomas proceden del archivo de 2013; no se observaron síntomas posteriores a consulta cuando ambas fechas eran interpretables. En validación solo hay dos excesos entre 94 semanas elegibles. Toda la rejilla obtiene F2=0: el umbral 0,90 resulta únicamente de la regla de desempate y no demuestra un umbral útil. En 2024 omite 15 de 48 excesos; en 2025 omite 33 de 35. No es un modelo listo para uso operacional. Conviene evaluar varios cortes de validación temporal dentro del periodo de desarrollo antes de nuevas comparaciones.

**Villavicencio:** de 53.422 registros extraídos se incluyen 53.417; se excluyen dos sin inicio válido y tres fuera del calendario. Solo hay una semana sin registros. Las 2.165 notificaciones anteriores a síntomas proceden del archivo de 2013; no se observaron síntomas posteriores a consulta cuando ambas fechas eran interpretables. En validación hay 61 excesos en 104 semanas; el umbral seleccionado es 0,10. La logística alcanza sensibilidad 88,5 %, precisión 76,1 % y F1 81,8 %, frente a F1 82,4 % de persistencia. En 2024 detecta los 14 excesos, pero genera 32 falsas alarmas; en 2025 alerta todas las semanas evaluadas, por lo que su F1 alto no demuestra discriminación de semanas sin exceso.

Estos patrones justifican conservar los experimentos como referencia inicial y comparar algoritmos bajo un protocolo temporal más robusto, sin prometer que una familia más compleja resolverá las limitaciones.

## Límites de interpretación

- La presencia de registros en una semana no demuestra cobertura completa. Los conteos y las métricas entre ciudades no son una clasificación de riesgo o incidencia: faltan denominadores de población y validación externa de cobertura.
- El escalador y los coeficientes se ajustan solo en entrenamiento. El canal y los rezagos de una semana usan antecedentes cronológicos; la simulación avanza semana a semana con conteos finales, sin reentrenamiento dentro de prueba.
- Los datos finales y sus estados pudieron conocerse después del corte nominal. Esta evaluación retrospectiva no demuestra rendimiento en tiempo real. La elección de INI_SIN conserva significado epidemiológico, pero no resuelve la disponibilidad o exactitud de todas las fechas.
- 2024 ya se había observado en Cali. Esta es la primera evaluación de las otras dos ciudades; las revisiones posteriores deben reconocer que estos resultados también fueron observados. No escoger hiperparámetros con prueba y seguir presentándola como nueva.
- P75 con cinco antecedentes es una definición inicial de exceso, no una declaración oficial de brote. Faltan sensibilidad del canal, validación temporal en más cortes y evaluación de oportunidad por episodios.
- Este paso no incorpora todavía MLflow, HistGradientBoosting ni red neuronal; establece los primeros modelos independientes con un protocolo común.

## Análisis anual

""" + "\n\n".join(detalles)
    (ROOT / "docs/resumen_tres_ciudades.md").write_text(texto + "\n", encoding="utf-8")
    print(comparacion.to_string(index=False))


if __name__ == "__main__":
    main()
