"""Puerta de calidad para el CI de prompts (E7).

Falla (exit 1) si la mejor versión baja del umbral o si EMPEORA un caso que la versión anterior aprobaba.
Uso:  python scripts/umbral.py prompts/criterios/resultados.json --version v3 --previa v2 --min 85
"""
import argparse
import sys

from resumen_resultados import cargar

ap = argparse.ArgumentParser()
ap.add_argument("resultados")
ap.add_argument("--version", required=True)
ap.add_argument("--previa")
ap.add_argument("--min", type=float, default=85.0)
a = ap.parse_args()
casos, _, _ = cargar(a.resultados)
mia = casos[a.version]
tasa = 100 * sum(mia.values()) / len(mia)
print(f"{a.resultados}: {a.version} = {tasa:.1f} % (umbral {a.min:.0f} %)")
errores = []
if tasa < a.min:
    errores.append(f"La tasa de {a.version} ({tasa:.1f} %) está por debajo del umbral")
if a.previa:
    regresiones = [c for c, ok in casos[a.previa].items() if ok and not mia.get(c, False)]
    if regresiones:
        errores.append(f"Regresión: {a.version} empeora casos que {a.previa} aprobaba: {', '.join(regresiones)}")
print("\n".join(errores) if errores else "OK: sin regresiones y sobre el umbral")
sys.exit(1 if errores else 0)
