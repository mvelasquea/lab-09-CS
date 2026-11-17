"""VERSIÓN DESPUÉS: el servicio solo coordina; cada decisión vive en su patrón."""
from dataclasses import dataclass, field

from externos import AgendaClinicaSDK, AgendaHospitalClient, ClienteLLMFalso, ModeloLocalFalso
from .agendas import Cupo, FabricaAgendas, ClinicaAdapter, HospitalAdapter
from .estados import EstadoCita, Solicitada
from .eventos import PublicadorEventos, NotificadorWhatsApp, ProgramadorRecordatorios
from .ia import GeneradorSugerencias, ClaudeAdapter, LocalAdapter, ConCache, cadena_de_guardrails
from .politicas import FabricaPoliticas, MasProximo, MenorCarga, MedicoPreferido
from .validaciones import cadena_de_reserva


@dataclass
class Cita:
    id: int
    dni: str
    celular: str
    especialidad: str
    medico_preferido: str = None
    activas_previas: int = 0
    cupo: Cupo = None
    codigo: str = None
    _estado: EstadoCita = field(default_factory=Solicitada, repr=False)

    @property
    def estado(self) -> str:
        return self._estado.nombre

    def cambiar_a(self, nuevo: EstadoCita):
        self._estado = nuevo

    # Cada operación delega en el estado actual (patrón State)
    def verificar_solicitable(self):
        self._estado.verificar_solicitable(self)

    def confirmar(self, cupo, codigo):
        self._estado.confirmar(self, cupo, codigo)

    def atender(self):
        self._estado.atender(self)

    def marcar_no_asistio(self):
        self._estado.marcar_no_asistio(self)

    def cancelar(self):
        self._estado.cancelar(self)


class ServicioCitas:
    def __init__(self, clinica=None, hospital=None, llm=None, local=None):
        clinica, hospital = clinica or AgendaClinicaSDK(), hospital or AgendaHospitalClient()
        self.fabrica_agendas = FabricaAgendas()
        self.fabrica_agendas.registrar("CLINICA", lambda: ClinicaAdapter(clinica))
        self.fabrica_agendas.registrar("HOSPITAL", lambda: HospitalAdapter(hospital))
        self.fabrica_politicas = FabricaPoliticas()
        self.fabrica_politicas.registrar("PROXIMO", MasProximo)
        self.fabrica_politicas.registrar("CARGA", MenorCarga)
        self.fabrica_politicas.registrar("PREFERIDO", MedicoPreferido)
        self.validaciones = cadena_de_reserva()
        self.eventos = []
        self.publicador = PublicadorEventos()
        self.publicador.suscribir("cita_confirmada", NotificadorWhatsApp(self.eventos))
        self.publicador.suscribir("cita_confirmada", ProgramadorRecordatorios(self.eventos))
        self.generador = GeneradorSugerencias(
            {"claude": ConCache(ClaudeAdapter(llm or ClienteLLMFalso())),
             "local": ConCache(LocalAdapter(local or ModeloLocalFalso()))},
            cadena_de_guardrails())

    def solicitar_cita(self, cita: Cita, sede: str, politica: str = "PROXIMO") -> str:
        self.validaciones.procesar(cita)
        agenda = self.fabrica_agendas.crear(sede)
        estrategia = self.fabrica_politicas.crear(politica)
        cupos = agenda.cupos_disponibles(cita.especialidad)
        if not cupos:
            raise ValueError("No hay cupos disponibles")
        cupo = estrategia.elegir(cupos, cita)
        resultado = agenda.reservar(cupo, cita.dni)
        if resultado.confirmada:
            cita.confirmar(cupo, resultado.codigo)
            self.publicador.publicar("cita_confirmada", {
                "id": cita.id, "celular": cita.celular, "medico": cupo.medico, "inicio": cupo.inicio})
        else:
            cita.cancelar()
        return cita.estado

    def sugerir_especialidad(self, motivo: str, proveedor: str = "claude") -> str:
        return self.generador.sugerir_especialidad(motivo, proveedor)
