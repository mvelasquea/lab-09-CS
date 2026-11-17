"""Pruebas de caracterización: las MISMAS pruebas se ejecutan sobre la versión 'antes' y la
versión 'despues'. Si todas pasan en ambas, el refactor conservó el comportamiento observable
(estado, eventos, excepciones). Ninguna prueba llama a servicios reales.
"""
import importlib
import pytest
from externos import (AgendaClinicaSDK, AgendaHospitalClient, ClienteLLMFalso, ModeloLocalFalso)


@pytest.fixture(params=["antes.servicio", "despues.servicio"])
def m(request):
    return importlib.import_module(request.param)


def cita(m, id=1, especialidad="MEDICINA_GENERAL", **extra):
    return m.Cita(id=id, dni="45678912", celular="959000111", especialidad=especialidad, **extra)


# ---------------------------------------------------------------- reserva: caminos felices
def test_reserva_clinica_publica_confirmacion_y_recordatorio(m):
    s, c = m.ServicioCitas(), cita(m)
    assert s.solicitar_cita(c, "CLINICA") == "CONFIRMADA"
    assert c.cupo.medico == "Dr. Mamani" and c.codigo.startswith("C-")
    assert s.eventos == [
        "whatsapp:959000111:Cita 1 confirmada con Dr. Mamani el 27/10/2026 09:00",
        "recordatorio:1:2026-10-26T09:00",
    ]


def test_reserva_hospital_aprobada(m):
    s, c = m.ServicioCitas(), cita(m)
    assert s.solicitar_cita(c, "HOSPITAL") == "CONFIRMADA"
    assert c.cupo.medico == "Dr. Ccama" and c.codigo.startswith("H-")


# ---------------------------------------------------------------- políticas de asignación
def test_politica_menor_carga_elige_al_medico_menos_ocupado(m):
    c = cita(m)
    m.ServicioCitas().solicitar_cita(c, "CLINICA", "CARGA")
    assert c.cupo.medico == "Dra. Flores"


def test_politica_medico_preferido(m):
    c = cita(m, medico_preferido="Dra. Quispe")
    m.ServicioCitas().solicitar_cita(c, "CLINICA", "PREFERIDO")
    assert c.cupo.medico == "Dra. Quispe"


def test_politica_preferido_sin_cupo_usa_el_mas_proximo(m):
    c = cita(m, medico_preferido="Dr. Inexistente")
    m.ServicioCitas().solicitar_cita(c, "CLINICA", "PREFERIDO")
    assert c.cupo.medico == "Dr. Mamani"


# ---------------------------------------------------------------- fallas y reintentos
def test_cupo_tomado_se_cancela_sin_eventos_ni_reintentos(m):
    clinica = AgendaClinicaSDK(rechaza=True)
    s, c = m.ServicioCitas(clinica=clinica), cita(m)
    assert s.solicitar_cita(c, "CLINICA") == "CANCELADA"
    assert s.eventos == []
    assert clinica.llamadas == 1          # un rechazo NO se reintenta (evita reservas duplicadas)


def test_reintenta_tras_dos_timeouts(m):
    clinica = AgendaClinicaSDK(fallas=2)
    assert m.ServicioCitas(clinica=clinica).solicitar_cita(cita(m), "CLINICA") == "CONFIRMADA"
    assert clinica.llamadas == 3


def test_tres_timeouts_cancelan(m):
    hospital = AgendaHospitalClient(fallas=3)
    assert m.ServicioCitas(hospital=hospital).solicitar_cita(cita(m), "HOSPITAL") == "CANCELADA"
    assert hospital.llamadas == 3


# ---------------------------------------------------------------- ciclo de vida
def test_no_se_puede_solicitar_dos_veces(m):
    s, c = m.ServicioCitas(), cita(m)
    s.solicitar_cita(c, "CLINICA")
    with pytest.raises(ValueError):
        s.solicitar_cita(c, "CLINICA")


def test_no_se_puede_solicitar_una_cita_cancelada(m):
    s, c = m.ServicioCitas(clinica=AgendaClinicaSDK(rechaza=True)), cita(m)
    s.solicitar_cita(c, "CLINICA")
    with pytest.raises(ValueError):
        s.solicitar_cita(c, "CLINICA")


# ---------------------------------------------------------------- validaciones de reserva
@pytest.mark.parametrize("extra, mensaje", [
    ({"dni": "1234"}, "DNI"),
    ({"celular": "859000111"}, "Celular"),
    ({"especialidad": "ASTROLOGIA"}, "Especialidad"),
    ({"activas_previas": 2}, "citas activas"),
])
def test_validaciones_de_reserva(m, extra, mensaje):
    c = cita(m)
    for campo, valor in extra.items():
        setattr(c, campo, valor)
    with pytest.raises(ValueError, match=mensaje):
        m.ServicioCitas().solicitar_cita(c, "CLINICA")
    assert c.estado == "SOLICITADA"


def test_sede_no_soportada(m):
    with pytest.raises(ValueError, match="Sede"):
        m.ServicioCitas().solicitar_cita(cita(m), "MARTE")


def test_politica_no_soportada(m):
    with pytest.raises(ValueError, match="Política"):
        m.ServicioCitas().solicitar_cita(cita(m), "CLINICA", "AL_AZAR")


@pytest.mark.parametrize("escenario", ["sede", "sin_cupos", "politica"])
def test_error_de_reserva_no_altera_el_estado(m, request, escenario):
    if request.node.callspec.params["m"] == "antes.servicio":
        request.applymarker(pytest.mark.xfail(
            reason="BUG de la versión antes: deja la cita CONFIRMADA aunque lance la excepción"))
    vacia = AgendaClinicaSDK(horarios=[]) if escenario == "sin_cupos" else None
    s, c = m.ServicioCitas(clinica=vacia), cita(m)
    args = {"sede": ("MARTE", "PROXIMO"), "sin_cupos": ("CLINICA", "PROXIMO"),
            "politica": ("CLINICA", "AL_AZAR")}[escenario]
    with pytest.raises(ValueError):
        s.solicitar_cita(c, *args)
    assert c.estado == "SOLICITADA"


# ---------------------------------------------------------------- IA: sugerir especialidad
def test_sugerencia_valida_con_claude(m):
    assert m.ServicioCitas().sugerir_especialidad("mi niño tiene fiebre") == "PEDIATRIA"


def test_sugerencia_con_modelo_local_normaliza_el_formato(m):
    assert m.ServicioCitas().sugerir_especialidad("dolor de muela", "local") == "MEDICINA_GENERAL"


def test_proveedor_ia_no_soportado(m):
    with pytest.raises(ValueError, match="Proveedor"):
        m.ServicioCitas().sugerir_especialidad("tos", "gpt-x")


@pytest.mark.parametrize("respuesta, mensaje", [
    ("Usted tiene gastritis", "diagnóstico"),
    ("Tome paracetamol cada 8 horas", "medicación"),
    ("ASTROLOGIA", "catálogo"),
    ("A" * 100, "demasiado larga"),
])
def test_guardrails_bloquean_respuestas_invalidas(m, respuesta, mensaje):
    s = m.ServicioCitas(llm=ClienteLLMFalso(respuesta))
    with pytest.raises(ValueError, match=mensaje):
        s.sugerir_especialidad("dolor de estómago")


def test_modelo_local_tambien_pasa_por_los_guardrails(m):
    s = m.ServicioCitas(local=ModeloLocalFalso("Usted tiene gripe"))
    with pytest.raises(ValueError, match="diagnóstico"):
        s.sugerir_especialidad("tos", "local")
