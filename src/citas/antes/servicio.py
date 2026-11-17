"""VERSIÓN ANTES: funciona, pero concentra todas las decisiones en condicionales.

Flujo crítico de CitaSalud Arequipa (secuencia del Lab 05): "solicitar y confirmar una cita"
y la función de IA "sugerir la especialidad a partir del motivo de consulta".
"""
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta

from externos import (AgendaClinicaSDK, AgendaHospitalClient, ClienteLLMFalso,
                      ModeloLocalFalso, CODIGOS_HOSPITAL)

ESPECIALIDADES = ["MEDICINA_GENERAL", "PEDIATRIA", "CARDIOLOGIA", "DERMATOLOGIA"]
DIAGNOSTICO = ["usted tiene", "diagnóstico", "diagnostico", "padece", "sufre de", "probablemente tiene"]
MEDICACION = ["paracetamol", "ibuprofeno", "antibiótico", "antibiotico", "dosis", " mg", "tome ", "pastilla"]


@dataclass
class Cupo:
    id: str
    medico: str
    inicio: datetime
    carga: int


@dataclass
class Cita:
    id: int
    dni: str
    celular: str
    especialidad: str
    medico_preferido: str = None
    activas_previas: int = 0
    estado: str = "SOLICITADA"
    cupo: Cupo = None
    codigo: str = None


def _normalizar(texto):
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return sin_tildes.strip().upper().replace(" ", "_")


class ServicioCitas:
    def __init__(self, clinica=None, hospital=None, llm=None, local=None):
        self.clinica = clinica or AgendaClinicaSDK()
        self.hospital = hospital or AgendaHospitalClient()
        self.llm = llm or ClienteLLMFalso()
        self.local = local or ModeloLocalFalso()
        self.eventos = []

    def solicitar_cita(self, cita, sede, politica="PROXIMO"):
        if cita.estado != "SOLICITADA":
            if cita.estado == "CANCELADA":
                raise ValueError("La cita está cancelada")
            elif cita.estado == "CONFIRMADA":
                raise ValueError("La cita ya fue confirmada")
            else:
                raise ValueError("Estado no válido")
        if not (cita.dni.isdigit() and len(cita.dni) == 8):
            raise ValueError("DNI inválido")
        if not (cita.celular.isdigit() and len(cita.celular) == 9 and cita.celular.startswith("9")):
            raise ValueError("Celular inválido")
        if cita.especialidad not in ESPECIALIDADES:
            raise ValueError(f"Especialidad no válida: {cita.especialidad}")
        if cita.activas_previas >= 2:
            raise ValueError("El paciente ya tiene 2 citas activas")
        cita.estado = "CONFIRMADA"
        cupos = []
        if sede == "CLINICA":
            for f in self.clinica.listar_horarios(cita.especialidad):
                cupos.append(Cupo(f["id"], f["medico"], datetime.fromisoformat(f["inicio"]), f["carga"]))
        elif sede == "HOSPITAL":
            for t in self.hospital.consultar_turnos(CODIGOS_HOSPITAL.get(cita.especialidad, 0)):
                cupos.append(Cupo(t[0], t[1], datetime.strptime(t[2], "%d/%m/%Y %H:%M"), t[3]))
        else:
            raise ValueError(f"Sede no soportada: {sede}")
        if not cupos:
            raise ValueError("No hay cupos disponibles")
        if politica == "PROXIMO":
            elegido = cupos[0]
            for c in cupos:
                if c.inicio < elegido.inicio:
                    elegido = c
        elif politica == "CARGA":
            elegido = cupos[0]
            for c in cupos:
                if c.carga < elegido.carga:
                    elegido = c
        elif politica == "PREFERIDO":
            elegido = None
            for c in cupos:
                if c.medico == cita.medico_preferido:
                    elegido = c
                    break
            if elegido is None:
                elegido = cupos[0]
                for c in cupos:
                    if c.inicio < elegido.inicio:
                        elegido = c
        else:
            raise ValueError(f"Política no soportada: {politica}")
        aprobado, codigo = False, None
        if sede == "CLINICA":
            for intento in range(3):
                try:
                    r = self.clinica.bloquear_horario(elegido.id, cita.dni)
                    aprobado, codigo = r["ok"], r.get("codigo")
                    break
                except TimeoutError:
                    if intento == 2:
                        aprobado = False
        else:
            for intento in range(3):
                try:
                    http, id_reserva = self.hospital.reservar_turno(elegido.id, cita.dni)
                    aprobado, codigo = http == 200, id_reserva
                    break
                except TimeoutError:
                    if intento == 2:
                        aprobado = False
        if aprobado:
            cita.cupo = elegido
            cita.codigo = codigo
            self.eventos.append(
                f"whatsapp:{cita.celular}:Cita {cita.id} confirmada con {elegido.medico} el {elegido.inicio:%d/%m/%Y %H:%M}")
            recordar = elegido.inicio - timedelta(hours=24)
            self.eventos.append(f"recordatorio:{cita.id}:{recordar.isoformat(timespec='minutes')}")
        else:
            cita.estado = "CANCELADA"
        return cita.estado

    def sugerir_especialidad(self, motivo, proveedor="claude"):
        prompt = ("Clasifica el motivo de consulta en una de estas especialidades: "
                  f"{', '.join(ESPECIALIDADES)}. Responde solo con el código, sin diagnosticar "
                  f"ni recetar. Motivo: {motivo}")
        if proveedor == "claude":
            texto = self.llm.completar(prompt)
        elif proveedor == "local":
            texto = self.local.generate("llama3", prompt)["response"]
        else:
            raise ValueError(f"Proveedor no soportado: {proveedor}")
        if len(texto) > 80:
            raise ValueError("Guardrail: respuesta demasiado larga")
        for palabra in DIAGNOSTICO:
            if palabra in texto.lower():
                raise ValueError("Guardrail: la IA emitió un diagnóstico")
        for palabra in MEDICACION:
            if palabra in texto.lower():
                raise ValueError("Guardrail: la IA mencionó medicación")
        codigo = _normalizar(texto)
        if codigo not in ESPECIALIDADES:
            raise ValueError(f"Guardrail: especialidad fuera del catálogo '{texto}'")
        return codigo
