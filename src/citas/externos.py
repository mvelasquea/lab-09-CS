"""Servicios externos SIMULADOS de CitaSalud Arequipa (no se modifican: representan SDK de terceros).

Cada proveedor tiene una interfaz distinta, como ocurre en la vida real:
  - AgendaClinicaSDK: diccionarios, fechas ISO y bloqueo con un dict {"ok": ...}.
  - AgendaHospitalClient: tuplas, fechas dd/mm/aaaa, especialidad numérica y
    respuesta (código HTTP, id).
  - ClienteLLMFalso / ModeloLocalFalso: simulan un LLM (p. ej. Claude) y un modelo
    local (p. ej. Ollama) con interfaces y formatos de respuesta distintos.

Nada de esto necesita red ni claves de API.
"""
import itertools

HORARIOS_CLINICA = [
    {"id": "C1", "medico": "Dra. Quispe",  "especialidad": "MEDICINA_GENERAL", "inicio": "2026-10-27T10:00", "carga": 4},
    {"id": "C2", "medico": "Dr. Mamani",   "especialidad": "MEDICINA_GENERAL", "inicio": "2026-10-27T09:00", "carga": 6},
    {"id": "C3", "medico": "Dra. Flores",  "especialidad": "MEDICINA_GENERAL", "inicio": "2026-10-28T08:00", "carga": 1},
    {"id": "C4", "medico": "Dr. Condori",  "especialidad": "PEDIATRIA",        "inicio": "2026-10-27T11:00", "carga": 2},
    {"id": "C5", "medico": "Dra. Huamani", "especialidad": "CARDIOLOGIA",      "inicio": "2026-10-29T15:30", "carga": 3},
]

CODIGOS_HOSPITAL = {"MEDICINA_GENERAL": 1, "PEDIATRIA": 2, "CARDIOLOGIA": 3}
# (id_turno, codigo_especialidad, medico, "dd/mm/aaaa hh:mm", citas_del_dia)
TURNOS_HOSPITAL = [
    ("H1", 1, "Dr. Ccama",   "27/10/2026 08:00", 5),
    ("H2", 1, "Dra. Apaza",  "28/10/2026 14:00", 2),
    ("H3", 2, "Dr. Chambi",  "27/10/2026 09:30", 7),
    ("H4", 3, "Dra. Valdez", "30/10/2026 10:00", 1),
]


class AgendaClinicaSDK:
    """SDK simulado de la agenda de la clínica: diccionarios y fechas ISO."""
    _seq = itertools.count(1)

    def __init__(self, fallas=0, rechaza=False, horarios=None):
        self.fallas = fallas        # cuántas veces responde con timeout antes de funcionar
        self.rechaza = rechaza      # simula que otro paciente tomó el horario (carrera)
        self.llamadas = 0           # llamadas a bloquear_horario
        self.horarios = [dict(h) for h in (HORARIOS_CLINICA if horarios is None else horarios)]

    def listar_horarios(self, especialidad: str) -> list:
        return [dict(h) for h in self.horarios if h["especialidad"] == especialidad]

    def bloquear_horario(self, id_horario: str, dni: str) -> dict:
        self.llamadas += 1
        if self.fallas > 0:
            self.fallas -= 1
            raise TimeoutError("La agenda de la clínica no respondió")
        if self.rechaza:
            return {"ok": False, "motivo": "horario ocupado"}
        return {"ok": True, "codigo": f"C-{next(self._seq):05d}"}


class AgendaHospitalClient:
    """Cliente simulado del hospital: tuplas, especialidad numérica y (código HTTP, id)."""
    _seq = itertools.count(1)

    def __init__(self, fallas=0, rechaza=False, turnos=None):
        self.fallas = fallas
        self.rechaza = rechaza
        self.llamadas = 0
        self.turnos = list(TURNOS_HOSPITAL if turnos is None else turnos)

    def consultar_turnos(self, codigo_especialidad: int) -> list:
        return [(t[0], t[2], t[3], t[4]) for t in self.turnos if t[1] == codigo_especialidad]

    def reservar_turno(self, id_turno: str, documento: str) -> tuple:
        self.llamadas += 1
        if self.fallas > 0:
            self.fallas -= 1
            raise TimeoutError("El hospital no respondió")
        if self.rechaza:
            return 409, None
        return 200, f"H-{next(self._seq):05d}"


_REGLAS_LLM = [
    (("niño", "niña", "bebé", "hijo", "hija"), "PEDIATRIA"),
    (("corazón", "pecho", "palpitaciones"), "CARDIOLOGIA"),
    (("piel", "mancha", "sarpullido"), "DERMATOLOGIA"),
]


def _clasificar(motivo: str, formato) -> str:
    motivo = motivo.lower()
    for palabras, especialidad in _REGLAS_LLM:
        if any(p in motivo for p in palabras):
            return formato(especialidad)
    return formato("MEDICINA_GENERAL")


class ClienteLLMFalso:
    """Simula un modelo de lenguaje (p. ej., Claude). Devuelve el texto configurado o clasifica por palabras clave."""

    def __init__(self, respuesta=None):
        self.respuesta = respuesta
        self.llamadas = 0
        self.ultimo_prompt = None

    def completar(self, prompt: str) -> str:
        self.llamadas += 1
        self.ultimo_prompt = prompt
        if self.respuesta is not None:
            return self.respuesta
        return _clasificar(prompt.split("Motivo:")[-1], lambda e: e)


class ModeloLocalFalso:
    """Simula un modelo local (p. ej., Ollama): otra interfaz y otro formato ('Medicina general')."""

    def __init__(self, respuesta=None):
        self.respuesta = respuesta
        self.llamadas = 0

    def generate(self, model: str, text: str) -> dict:
        self.llamadas += 1
        if self.respuesta is not None:
            return {"model": model, "response": self.respuesta}
        legible = lambda e: e.replace("_", " ").capitalize()
        return {"model": model, "response": _clasificar(text.split("Motivo:")[-1], legible)}
