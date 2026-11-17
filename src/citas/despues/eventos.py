"""Notificaciones desacopladas: patrón OBSERVER (publicador / suscriptores)."""
from abc import ABC, abstractmethod
from datetime import timedelta


class Suscriptor(ABC):
    @abstractmethod
    def actualizar(self, evento: str, datos: dict) -> None: ...


class PublicadorEventos:
    def __init__(self):
        self._suscriptores = {}

    def suscribir(self, evento: str, suscriptor: Suscriptor):
        self._suscriptores.setdefault(evento, []).append(suscriptor)

    def publicar(self, evento: str, datos: dict):
        for s in self._suscriptores.get(evento, []):
            s.actualizar(evento, datos)


class NotificadorWhatsApp(Suscriptor):
    def __init__(self, bandeja):
        self._bandeja = bandeja

    def actualizar(self, evento, datos):
        self._bandeja.append(
            f"whatsapp:{datos['celular']}:Cita {datos['id']} confirmada con "
            f"{datos['medico']} el {datos['inicio']:%d/%m/%Y %H:%M}")


class ProgramadorRecordatorios(Suscriptor):
    def __init__(self, bandeja, anticipacion=timedelta(hours=24)):
        self._bandeja, self._anticipacion = bandeja, anticipacion

    def actualizar(self, evento, datos):
        recordar = datos["inicio"] - self._anticipacion
        self._bandeja.append(f"recordatorio:{datos['id']}:{recordar.isoformat(timespec='minutes')}")
