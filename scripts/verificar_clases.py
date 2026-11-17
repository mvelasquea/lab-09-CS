"""Verifica que docs/design/clases.puml coincida con el código (clases y herencias).

Uso (desde la raíz del repo):   python scripts/verificar_clases.py
Usa pyreverse (incluido en pylint) para extraer el modelo REAL del código y lo compara
con el diagrama escrito a mano. Sale con código 1 si hay diferencias.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
tmp = tempfile.mkdtemp()
subprocess.run(["pyreverse", "-o", "puml", "-p", "citas", "-d", tmp, "src/citas/despues"],
               cwd=RAIZ, check=True, capture_output=True, env={"PYTHONPATH": "src/citas", "PATH": "/usr/local/bin:/usr/bin:/bin"})
real = Path(tmp, "classes_citas.puml").read_text(encoding="utf-8")
doc = (RAIZ / "docs/design/clases.puml").read_text(encoding="utf-8")

corto = lambda nombre: nombre.split(".")[-1]
clases_real = {corto(m) for m in re.findall(r'^(?:abstract class|class|interface) "?([\w.]+)"?', real, re.M)}
clases_doc = set(re.findall(r'^\s*(?:abstract class|class|interface) (\w+)', doc, re.M))
clases_doc.discard("")
herencia_real = {(corto(a), corto(b)) for a, b in re.findall(r'([\w.]+) --\|> ([\w.]+)', real)}
herencia_doc = {(a, b) for b, a in re.findall(r'(\w+) <\|[-.]+ (\w+)', doc)}

errores = []
for c in sorted(clases_real - clases_doc):
    errores.append(f"Falta en el diagrama: clase {c}")
for c in sorted(clases_doc - clases_real - {"ServicioCitas"} ):
    errores.append(f"Sobra en el diagrama (no existe en el código): clase {c}")
for h in sorted(herencia_real - herencia_doc):
    errores.append(f"Falta en el diagrama: {h[0]} hereda de {h[1]}")
for h in sorted(herencia_doc - herencia_real):
    errores.append(f"Sobra en el diagrama: {h[0]} hereda de {h[1]}")
print(f"Clases en el código: {len(clases_real)} | en el diagrama: {len(clases_doc)}")
print(f"Herencias/realizaciones en el código: {len(herencia_real)} | en el diagrama: {len(herencia_doc)}")
print("\n".join(errores) if errores else "OK: el diagrama coincide con el código")
sys.exit(1 if errores else 0)
