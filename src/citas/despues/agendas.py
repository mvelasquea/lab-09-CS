"""Agendas médicas: ADAPTER + STRATEGY (puerto) + DECORATOR (reintentos) + FACTORY (registro).

El servicio habla con el puerto AgendaMedica; cada sede es una estrategia intercambiable y
cada SDK externo se traduce con un adaptador. Los adaptadores NO contienen reglas de negocio.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from externos import CODIGOS_HOSPITAL
from .fabrica import Fabrica


@dataclass(frozen=True)
class Cupo:
    id: str
    medico: str
    inicio: datetime
    carga: int


@dataclass(frozen=True)
class ResultadoReserva:
    confirmada: bool
    codigo: str | None = None


class AgendaMedica(ABC):
    """Puerto (interfaz) común: todas las sedes se usan igual."""

    @abstractmethod
    def cupos_disponibles(self, especialidad: str) -> list: ...

    @abstractmethod
    def reservar(self, cupo: Cupo, dni: str) -> ResultadoReserva: ...


# ---------- ADAPTER: traduce cada SDK a la interfaz AgendaMedica ----------
class ClinicaAdapter(AgendaMedica):
    def __init__(self, sdk):
        self._sdk = sdk

    def cupos_disponibles(self, especialidad):
        return [Cupo(f["id"], f["medico"], datetime.fromisoformat(f["inicio"]), f["carga"])
                for f in self._sdk.listar_horarios(especialidad)]

    def reservar(self, cupo, dni):
        r = self._sdk.bloquear_horario(cupo.id, dni)
        return ResultadoReserva(r["ok"], r.get("codigo"))


class HospitalAdapter(AgendaMedica):
    def __init__(self, cliente):
        self._cliente = cliente

    def cupos_disponibles(self, especialidad):
        turnos = self._cliente.consultar_turnos(CODIGOS_HOSPITAL.get(especialidad, 0))
        return [Cupo(t[0], t[1], datetime.strptime(t[2], "%d/%m/%Y %H:%M"), t[3]) for t in turnos]

    def reservar(self, cupo, dni):
        http, id_reserva = self._cliente.reservar_turno(cupo.id, dni)
        return ResultadoReserva(http == 200, id_reserva)


# ---------- DECORATOR: agrega reintentos sin modificar los adaptadores ----------
class ConReintentos(AgendaMedica):
    """Reintenta SOLO ante TimeoutError. Un rechazo ('horario ocupado') NO se reintenta."""

    def __init__(self, interna: AgendaMedica, intentos: int = 3):
        self._interna, self._intentos = interna, intentos

    def cupos_disponibles(self, especialidad):
        return self._interna.cupos_disponibles(especialidad)

    def reservar(self, cupo, dni):
        for _ in range(self._intentos):
            try:
                return self._interna.reservar(cupo, dni)
            except TimeoutError:
                continue
        return ResultadoReserva(False)


# ---------- FACTORY (registro): crea la sede adecuada por nombre ----------
class FabricaAgendas(Fabrica):
    def __init__(self):
        super().__init__("Sede")

    def crear(self, nombre: str) -> AgendaMedica:
        return ConReintentos(super().crear(nombre))
