"""Validaciones de la reserva: CHAIN OF RESPONSIBILITY.

Cada eslabón valida UNA regla (responsabilidad única). El orden de la cadena es el orden
de las reglas; agregar una regla nueva es agregar un eslabón.
"""
from .cadena import Eslabon
from .catalogo import ESPECIALIDADES


class EstadoSolicitable(Eslabon):
    """Delega en el patrón State: solo una cita SOLICITADA puede pedirse."""

    def _aplicar(self, cita):
        cita.verificar_solicitable()
        return cita


class DniValido(Eslabon):
    def _aplicar(self, cita):
        if not (cita.dni.isdigit() and len(cita.dni) == 8):
            raise ValueError("DNI inválido")
        return cita


class CelularValido(Eslabon):
    def _aplicar(self, cita):
        if not (cita.celular.isdigit() and len(cita.celular) == 9 and cita.celular.startswith("9")):
            raise ValueError("Celular inválido")
        return cita


class EspecialidadValida(Eslabon):
    def _aplicar(self, cita):
        if cita.especialidad not in ESPECIALIDADES:
            raise ValueError(f"Especialidad no válida: {cita.especialidad}")
        return cita


class LimiteCitasActivas(Eslabon):
    def __init__(self, maximo=2, siguiente=None):
        super().__init__(siguiente)
        self._maximo = maximo

    def _aplicar(self, cita):
        if cita.activas_previas >= self._maximo:
            raise ValueError(f"El paciente ya tiene {self._maximo} citas activas")
        return cita


def cadena_de_reserva() -> Eslabon:
    return EstadoSolicitable(DniValido(CelularValido(EspecialidadValida(LimiteCitasActivas()))))
