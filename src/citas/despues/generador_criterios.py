"""Prompts como código: generadores de criterios Gherkin (Tarea A) y datos de prueba (Tarea B).

Se usan DETRÁS del puerto ProveedorLLM del Lab 07 (Strategy: Claude, modelo local o grabado) y la
salida del LLM se trata como DATO NO CONFIABLE: capa 3 de la defensa =
  (1) JSON válido, (2) cumple el JSON Schema (contrato) y (3) reglas semánticas.
Si algo falla se lanza SalidaInvalida: la respuesta se descarta y nunca se muestra "tal cual".
"""
import json
import pathlib
import re

from jsonschema import ValidationError, validate

from .ia import ProveedorLLM

RAIZ = pathlib.Path(__file__).resolve().parents[3]
PROMPTS = RAIZ / "prompts"


class SalidaInvalida(Exception):
    """La respuesta del LLM no cumple el contrato: se descarta y se registra."""


class ProveedorGrabado(ProveedorLLM):
    """Doble de prueba: devuelve la respuesta GRABADA (prompts/<tarea>/grabaciones/<version>/<id>.txt)."""

    def __init__(self, tarea: str, version: str, caso: str = None):
        self._dir = PROMPTS / tarea / "grabaciones" / version
        self._caso = caso          # si es None, el id se deduce del prompt

    def completar(self, prompt: str) -> str:
        # El dato real va al final del prompt (el ejemplo few-shot también trae un id="EJ"): se toma la ÚLTIMA coincidencia.
        ids = re.findall(r'<(?:historia|pedido)[^>]*?id="([^"]+)"', prompt) or re.findall(r"\((\w+)\):", prompt)
        return (self._dir / f"{self._caso or ids[-1]}.txt").read_text(encoding="utf-8")


class ProveedorFijo(ProveedorLLM):
    """Doble de prueba: devuelve un texto fijo y recuerda el último prompt recibido."""

    def __init__(self, texto: str):
        self.texto, self.ultimo_prompt = texto, None

    def completar(self, prompt: str) -> str:
        self.ultimo_prompt = prompt
        return self.texto


class _GeneradorBase:
    TAREA = ""

    def __init__(self, proveedor: ProveedorLLM, version: str):
        self._proveedor = proveedor          # Strategy: Claude, OpenAI, modelo local o grabado
        self.version = version
        carpeta = PROMPTS / self.TAREA
        self._plantilla = (carpeta / f"{version}.txt").read_text(encoding="utf-8")
        self._esquema = json.loads((carpeta / "esquema.json").read_text(encoding="utf-8"))

    def _generar(self, id_caso: str, clave: str, texto_entrada: str) -> dict:
        prompt = self._plantilla.replace("{{id}}", id_caso).replace("{{" + clave + "}}", texto_entrada)
        texto = self._proveedor.completar(prompt)
        try:
            datos = json.loads(texto)
            validate(datos, self._esquema)                    # capa 3: contrato
            self._reglas(datos)                                # capa 3: reglas semánticas
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            raise SalidaInvalida(f"{self.version}/{id_caso}: {str(e).splitlines()[0]}") from e
        return datos

    def _reglas(self, datos: dict) -> None: ...


class GeneradorCriterios(_GeneradorBase):
    TAREA = "criterios"

    def generar(self, id_historia: str, historia: str) -> dict:
        return self._generar(id_historia, "historia", historia)

    def _reglas(self, r):
        if not r["invest_ok"]:
            if r["escenarios"] or not (1 <= len(r["preguntas"]) <= 3):
                raise ValueError("Una historia que no cumple INVEST lleva 1-3 preguntas y 0 escenarios")
            return
        tipos = [e["tipo"] for e in r["escenarios"]]
        if not (2 <= len(tipos) <= 4 and "exito" in tipos and ("error" in tipos or "borde" in tipos)):
            raise ValueError("Se esperan 2-4 escenarios con al menos uno de éxito y uno de error o borde")


class GeneradorDatosPrueba(_GeneradorBase):
    TAREA = "datos_prueba"

    def generar(self, id_pedido: str, pedido: str) -> dict:
        return self._generar(id_pedido, "pedido", pedido)

    def _reglas(self, d):
        ids = {p["id"] for p in d["pacientes"]}
        for p in d["pacientes"]:
            if not re.fullmatch(r"TEST\d{4}", p["dni"]) or not re.fullmatch(r"0\d{8}", p["celular"]):
                raise ValueError(f"Paciente {p['id']} con DNI o celular de formato real")
            if not p["nombre"].startswith("[FICTICIO]"):
                raise ValueError(f"Paciente {p['id']} sin la marca [FICTICIO]")
        if any(c["paciente_id"] not in ids for c in d["citas"]):
            raise ValueError("Cita que apunta a un paciente inexistente")


def pedido_desde_criterios(criterios: dict) -> str:
    """ENCADENAMIENTO (Tarea A -> Tarea B): convierte los escenarios en un pedido de datos de prueba.

    Un paciente y una cita por escenario, para poder ejecutar cada criterio de aceptación.
    """
    n = len(criterios["escenarios"])
    titulos = "; ".join(e["titulo"] for e in criterios["escenarios"])
    return f"{n} pacientes con una cita cada uno, para probar los escenarios: {titulos}."
