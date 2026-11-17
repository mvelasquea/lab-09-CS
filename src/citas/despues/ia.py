"""Sugerir especialidad con IA: STRATEGY + ADAPTER + DECORATOR + CHAIN OF RESPONSIBILITY.

La IA no es determinista: se aísla detrás de una interfaz, se cachea y su salida se trata
como DATO NO CONFIABLE: se valida con una cadena de guardrails antes de usarla.
La IA solo CLASIFICA hacia una especialidad del catálogo; NUNCA diagnostica ni receta.
"""
import unicodedata
from abc import ABC, abstractmethod

from .cadena import Eslabon
from .catalogo import ESPECIALIDADES

DIAGNOSTICO = ["usted tiene", "diagnóstico", "diagnostico", "padece", "sufre de", "probablemente tiene"]
MEDICACION = ["paracetamol", "ibuprofeno", "antibiótico", "antibiotico", "dosis", " mg", "tome ", "pastilla"]


class ProveedorLLM(ABC):
    @abstractmethod
    def completar(self, prompt: str) -> str: ...


# ---------- ADAPTER: cada proveedor se traduce a ProveedorLLM ----------
class ClaudeAdapter(ProveedorLLM):
    def __init__(self, cliente):
        self._cliente = cliente

    def completar(self, prompt):
        return self._cliente.completar(prompt)


class LocalAdapter(ProveedorLLM):
    def __init__(self, modelo, nombre="llama3"):
        self._modelo, self._nombre = modelo, nombre

    def completar(self, prompt):
        return self._modelo.generate(self._nombre, prompt)["response"]


# ---------- DECORATOR: caché ----------
class ConCache(ProveedorLLM):
    """Evita pagar dos veces por el mismo prompt."""

    def __init__(self, interno: ProveedorLLM):
        self._interno, self._cache = interno, {}

    def completar(self, prompt):
        if prompt not in self._cache:
            self._cache[prompt] = self._interno.completar(prompt)
        return self._cache[prompt]


# ---------- CHAIN OF RESPONSIBILITY: guardrails de salida ----------
class LongitudMaxima(Eslabon):
    def __init__(self, maximo=80, siguiente=None):
        super().__init__(siguiente)
        self._maximo = maximo

    def _aplicar(self, texto):
        if len(texto) > self._maximo:
            raise ValueError("Guardrail: respuesta demasiado larga")
        return texto


class SinDiagnostico(Eslabon):
    def _aplicar(self, texto):
        if any(p in texto.lower() for p in DIAGNOSTICO):
            raise ValueError("Guardrail: la IA emitió un diagnóstico")
        return texto


class SinMedicacion(Eslabon):
    def _aplicar(self, texto):
        if any(p in texto.lower() for p in MEDICACION):
            raise ValueError("Guardrail: la IA mencionó medicación")
        return texto


class EspecialidadDelCatalogo(Eslabon):
    """Normaliza ('Medicina general' -> MEDICINA_GENERAL) y exige que exista en el catálogo."""

    def _aplicar(self, texto):
        sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
        codigo = sin_tildes.strip().upper().replace(" ", "_")
        if codigo not in ESPECIALIDADES:
            raise ValueError(f"Guardrail: especialidad fuera del catálogo '{texto}'")
        return codigo


def cadena_de_guardrails() -> Eslabon:
    return LongitudMaxima(80, SinDiagnostico(SinMedicacion(EspecialidadDelCatalogo())))


class GeneradorSugerencias:
    def __init__(self, proveedores: dict, guardrails: Eslabon):
        self._proveedores, self._guardrails = proveedores, guardrails

    def sugerir_especialidad(self, motivo: str, proveedor: str = "claude") -> str:
        if proveedor not in self._proveedores:
            raise ValueError(f"Proveedor no soportado: {proveedor}")
        # Privacidad: el prompt lleva SOLO el motivo; nunca nombre, DNI ni celular.
        prompt = ("Clasifica el motivo de consulta en una de estas especialidades: "
                  f"{', '.join(ESPECIALIDADES)}. Responde solo con el código, sin diagnosticar "
                  f"ni recetar. Motivo: {motivo}")
        return self._guardrails.procesar(self._proveedores[proveedor].completar(prompt))
