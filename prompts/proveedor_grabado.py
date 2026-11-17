"""Proveedor de promptfoo que NO llama a ningún modelo: devuelve la respuesta GRABADA.

Lee  prompts/<carpeta>/grabaciones/<version>/<id>.txt  tal como la dio el asistente (sin editar).
La versión se deduce del nombre del archivo del prompt (v1.txt -> v1) y el id de la variable `id`.
Para usar un modelo real, reemplace este proveedor en promptfooconfig.yaml (temperatura 0).
"""
import pathlib

RAIZ = pathlib.Path(__file__).parent


def call_api(prompt, options, context):
    carpeta = (options.get("config") or {}).get("carpeta", "criterios")
    etiqueta = (context.get("prompt") or {}).get("label", "")
    # La etiqueta es "ruta/vN.txt: <inicio del prompt>": se toma solo el nombre del archivo.
    version = pathlib.Path(etiqueta.split(".txt")[0]).name or "v1"
    caso = context["vars"]["id"]
    ruta = RAIZ / carpeta / "grabaciones" / version / f"{caso}.txt"
    if not ruta.exists():
        return {"error": f"Falta la grabación {ruta.relative_to(RAIZ)}"}
    return {"output": ruta.read_text(encoding="utf-8")}
