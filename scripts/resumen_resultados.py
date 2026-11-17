"""Resume resultados.json de promptfoo: tasa de aprobación por versión, por aserción y por caso.

Uso:  python scripts/resumen_resultados.py prompts/criterios/resultados.json [--png salida.png] [--md]
Un caso 'aprueba' si pasan TODAS sus aserciones (igual que la Figura 5 de la guía).
"""
import argparse
import json
import pathlib
import re
from collections import defaultdict


def cargar(ruta):
    filas = json.loads(pathlib.Path(ruta).read_text(encoding="utf-8"))["results"]["results"]
    casos = defaultdict(dict)       # version -> caso -> bool
    metricas = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # version -> metrica -> [ok, total]
    fallas = defaultdict(lambda: defaultdict(list))               # version -> caso -> [metricas]
    for f in filas:
        version = pathlib.Path(f["prompt"]["label"].split(".txt")[0]).name
        caso = f["vars"]["id"]
        casos[version][caso] = bool(f["success"])
        for comp in (f.get("gradingResult") or {}).get("componentResults", []):
            m = (comp.get("assertion") or {}).get("metric", "?")
            metricas[version][m][1] += 1
            if comp["pass"]:
                metricas[version][m][0] += 1
            else:
                fallas[version][caso].append(m.split("_")[0])
    return casos, metricas, fallas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("resultados")
    ap.add_argument("--png")
    ap.add_argument("--md", action="store_true")
    a = ap.parse_args()
    casos, metricas, fallas = cargar(a.resultados)
    versiones = sorted(casos, key=lambda v: [int(x) for x in re.findall(r"\d+", v)])
    print("| Versión | Casos aprobados | Tasa |")
    print("|---|---|---|")
    tasas = {}
    for v in versiones:
        ok, n = sum(casos[v].values()), len(casos[v])
        tasas[v] = 100 * ok / n
        print(f"| {v} | {ok}/{n} | {tasas[v]:.1f} % |")
    print("\nFallos por caso:")
    for v in versiones:
        det = ", ".join(f"{c}: {'+'.join(sorted(set(m)))}" for c, m in sorted(fallas[v].items()))
        print(f"  {v}: {det or 'ninguno'}")
    print("\nAprobación por aserción (%):")
    nombres = sorted({m for v in versiones for m in metricas[v]})
    for m in nombres:
        print(f"  {m:28s}", "  ".join(f"{v}={100*metricas[v][m][0]/metricas[v][m][1]:5.1f}" for v in versiones if metricas[v][m][1]))
    if a.png:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        colores = ["#C8310E", "#E39B2D", "#2E75B6", "#1E7B34", "#6B6B6B"]
        fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4), gridspec_kw={"width_ratios": [1, 1.5]})
        for i, v in enumerate(versiones):
            ok, n = sum(casos[v].values()), len(casos[v])
            a1.bar(v, tasas[v], color=colores[i % 5])
            a1.text(i, tasas[v] + 2, f"{tasas[v]:.1f} %\n({ok}/{n})", ha="center", fontsize=9, fontweight="bold")
        a1.set_ylim(0, 120); a1.set_ylabel("Casos que pasan TODAS las aserciones (%)")
        a1.set_title("Tasa de aprobación por versión", fontweight="bold", color="#1A3A5C")
        a1.spines[["top", "right"]].set_visible(False)
        w = 0.8 / len(versiones)
        for i, v in enumerate(versiones):
            vals = [100 * metricas[v][m][0] / metricas[v][m][1] if metricas[v][m][1] else 0 for m in nombres]
            a2.bar([j + i * w for j in range(len(nombres))], vals, w, color=colores[i % 5], label=v)
        a2.set_xticks([j + w * (len(versiones) - 1) / 2 for j in range(len(nombres))])
        a2.set_xticklabels([m.split("_")[0] for m in nombres]); a2.set_ylabel("% de aprobación de la aserción")
        a2.set_title("Aprobación por aserción", fontweight="bold", color="#1A3A5C")
        a2.set_ylim(0, 118); a2.legend(frameon=False, fontsize=8, ncol=len(versiones), loc="upper center"); a2.spines[["top", "right"]].set_visible(False)
        fig.tight_layout(); fig.savefig(a.png, dpi=150)


if __name__ == "__main__":
    main()
