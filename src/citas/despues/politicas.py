"""Política de asignación de cupos: STRATEGY (+ FACTORY de registro).

Cada política es una clase intercambiable. Agregar una nueva NO modifica el servicio.
"""
from abc import ABC, abstractmethod

from .fabrica import Fabrica


class PoliticaAsignacion(ABC):
    @abstractmethod
    def elegir(self, cupos: list, cita):
        """Devuelve el cupo elegido entre los disponibles (lista no vacía)."""


class MasProximo(PoliticaAsignacion):
    def elegir(self, cupos, cita):
        return min(cupos, key=lambda c: c.inicio)


class MenorCarga(PoliticaAsignacion):
    def elegir(self, cupos, cita):
        return min(cupos, key=lambda c: c.carga)


class MedicoPreferido(PoliticaAsignacion):
    """Respeta al médico preferido del paciente; si no tiene cupo, usa la política de respaldo."""

    def __init__(self, respaldo: PoliticaAsignacion = None):
        self._respaldo = respaldo or MasProximo()

    def elegir(self, cupos, cita):
        for c in cupos:
            if c.medico == cita.medico_preferido:
                return c
        return self._respaldo.elegir(cupos, cita)


class FabricaPoliticas(Fabrica):
    def __init__(self):
        super().__init__("Política")
