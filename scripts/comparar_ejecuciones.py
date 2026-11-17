"""E7.3 No determinismo: compara varias ejecuciones del MISMO prompt sobre los MISMOS casos.

Estructura esperada (cada archivo es la respuesta CRUDA de un chat NUEVO, sin editar):
  prompts/criterios/ejecuciones/run1/H1.txt, run2/H1.txt, run3/H1.txt, ... (y lo mismo para H2, H5)
Uso:  python scripts/comparar_ejecuciones.py prompts/criterios/ejecuciones
Muestra, por caso: si los textos son idénticos, si el JSON es idéntico, y qué cambia (tipos, cantidad de
escenarios, campos), además de la longitud de cada respuesta.
"""
import json
import pathlib
import sys

raiz = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "prompts/criterios/ejecuciones")
runs = sorted(d for d in raiz.glob("run*") if d.is_dir())
if len(runs) < 3:
    sys.exit(f"Faltan ejecuciones: se encontraron {len(runs)} carpetas run* en {raiz} (se necesitan 3).")
casos = sorted({f.stem for r in runs for f in r.glob("*.txt")})
for caso in casos:
    textos = [(r / f"{caso}.txt").read_text(encoding="utf-8").strip() if (r / f"{caso}.txt").exists() else None for r in runs]
    print(f"\n== {caso} ==")
    print("  longitudes:", [len(t) if t else None for t in textos])
    print("  textos idénticos:", len({t for t in textos}) == 1)
    parsed = []
    for t in textos:
        try:
            parsed.append(json.loads(t))
        except Exception:
            parsed.append(None)
    print("  JSON válido en cada ejecución:", [p is not None for p in parsed])
    if all(parsed):
        print("  JSON idéntico:", all(p == parsed[0] for p in parsed))
        print("  invest_ok:", [p["invest_ok"] for p in parsed])
        print("  escenarios (cantidad):", [len(p["escenarios"]) for p in parsed])
        print("  tipos:", [[e["tipo"] for e in p["escenarios"]] for p in parsed])
        print("  títulos:", [[e["titulo"] for e in p["escenarios"]] for p in parsed])
