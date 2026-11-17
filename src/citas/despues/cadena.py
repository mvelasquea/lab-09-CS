"""CHAIN OF RESPONSIBILITY: base común para cadenas de eslabones.

Se usa en dos lugares: las validaciones de la reserva (validaciones.py) y los
guardrails de la salida del LLM (ia.py). Cada eslabón tiene UNA responsabilidad:
comprueba (o transforma) el dato y lo pasa al siguiente; si algo falla, lanza ValueError
y la cadena se corta.
"""
from abc import ABC, abstractmethod


class Eslabon(ABC):
    def __init__(self, siguiente=None):
        self._siguiente = siguiente

    def procesar(self, dato):
        dato = self._aplicar(dato)
        return self._siguiente.procesar(dato) if self._siguiente else dato

    @abstractmethod
    def _aplicar(self, dato): ...
