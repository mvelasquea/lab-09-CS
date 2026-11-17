"""Pruebas que solo son posibles (o fáciles) gracias a los patrones. Cada patrón tiene su prueba."""
from datetime import datetime

import pytest
from externos import (AgendaClinicaSDK, AgendaHospitalClient, ClienteLLMFalso, ModeloLocalFalso)
from despues.servicio import ServicioCitas, Cita
from despues.agendas import (AgendaMedica, ClinicaAdapter, HospitalAdapter, ConReintentos,
                             Cupo, ResultadoReserva)
from despues.politicas import PoliticaAsignacion, MasProximo, MenorCarga, MedicoPreferido
from despues.cadena import Eslabon
from despues.validaciones import cadena_de_reserva
from despues.ia import (GeneradorSugerencias, ClaudeAdapter, ConCache, LongitudMaxima,
                        SinDiagnostico, SinMedicacion, EspecialidadDelCatalogo)
from despues.eventos import Suscriptor


def nueva_cita(id=1, especialidad="MEDICINA_GENERAL", **extra):
    return Cita(id=id, dni="45678912", celular="959000111", especialidad=especialidad, **extra)


# ======================================================== STRATEGY + FACTORY (abierto/cerrado)
class AgendaSurFalsa(AgendaMedica):
    def cupos_disponibles(self, especialidad):
        return [Cupo("S1", "Dr. Sur", datetime(2026, 11, 2, 8, 0), 0)]

    def reservar(self, cupo, dni):
        return ResultadoReserva(True, "S-00001")


def test_open_closed_nueva_sede_sin_modificar_el_servicio():
    s = ServicioCitas()
    s.fabrica_agendas.registrar("CLINICA_SUR", AgendaSurFalsa)       # extensión, no modificación
    c = nueva_cita()
    assert s.solicitar_cita(c, "CLINICA_SUR") == "CONFIRMADA" and c.codigo == "S-00001"


class UltimoDisponible(PoliticaAsignacion):
    def elegir(self, cupos, cita):
        return max(cupos, key=lambda x: x.inicio)


def test_open_closed_nueva_politica_sin_modificar_el_servicio():
    s = ServicioCitas()
    s.fabrica_politicas.registrar("ULTIMO", UltimoDisponible)
    c = nueva_cita()
    s.solicitar_cita(c, "CLINICA", "ULTIMO")
    assert c.cupo.medico == "Dra. Flores"                            # la del 28/10, la más tardía


CUPOS = [Cupo("a", "Dr. A", datetime(2026, 10, 27, 10), 5),
         Cupo("b", "Dr. B", datetime(2026, 10, 27, 9), 7),
         Cupo("c", "Dr. C", datetime(2026, 10, 28, 8), 1)]


def test_strategy_las_politicas_son_intercambiables_y_puras():
    cita = nueva_cita(medico_preferido="Dr. A")
    assert MasProximo().elegir(CUPOS, cita).medico == "Dr. B"
    assert MenorCarga().elegir(CUPOS, cita).medico == "Dr. C"
    assert MedicoPreferido().elegir(CUPOS, cita).medico == "Dr. A"
    assert MedicoPreferido(respaldo=MenorCarga()).elegir(CUPOS, nueva_cita()).medico == "Dr. C"


def test_politica_desconocida_se_rechaza_antes_de_reservar():
    clinica = AgendaClinicaSDK()
    with pytest.raises(ValueError, match="Política"):
        ServicioCitas(clinica=clinica).solicitar_cita(nueva_cita(), "CLINICA", "AL_AZAR")
    assert clinica.llamadas == 0


# ======================================================== ADAPTER
def test_adapter_dos_sdk_distintos_producen_la_misma_interfaz():
    c1 = ClinicaAdapter(AgendaClinicaSDK()).cupos_disponibles("PEDIATRIA")
    c2 = HospitalAdapter(AgendaHospitalClient()).cupos_disponibles("PEDIATRIA")
    assert all(isinstance(c, Cupo) for c in c1 + c2)
    assert c1[0].inicio == datetime(2026, 10, 27, 11, 0)             # ISO -> datetime
    assert c2[0].inicio == datetime(2026, 10, 27, 9, 30)             # dd/mm/aaaa -> datetime


def test_adapter_traduce_las_respuestas_de_reserva():
    cupo = Cupo("x", "Dr. X", datetime(2026, 10, 27, 9), 0)
    assert ClinicaAdapter(AgendaClinicaSDK(rechaza=True)).reservar(cupo, "1") == ResultadoReserva(False)
    assert HospitalAdapter(AgendaHospitalClient()).reservar(cupo, "1").confirmada is True


# ======================================================== STATE
def test_state_impide_transiciones_invalidas():
    c = nueva_cita()
    c.cancelar()
    for operacion in (c.atender, c.marcar_no_asistio, c.cancelar):
        with pytest.raises(ValueError):
            operacion()
    with pytest.raises(ValueError):
        c.confirmar(CUPOS[0], "X")


def test_state_recorre_la_maquina_de_estados_del_lab05():
    c = nueva_cita()
    assert c.estado == "SOLICITADA"
    c.confirmar(CUPOS[0], "C-1")
    assert (c.estado, c.cupo.medico, c.codigo) == ("CONFIRMADA", "Dr. A", "C-1")
    c.atender()
    assert c.estado == "ATENDIDA"


def test_state_no_asistio_y_cancelacion_desde_confirmada():
    a, b = nueva_cita(1), nueva_cita(2)
    a.confirmar(CUPOS[0], "C-1"); a.marcar_no_asistio()
    b.confirmar(CUPOS[1], "C-2"); b.cancelar()
    assert (a.estado, b.estado) == ("NO_ASISTIO", "CANCELADA")


@pytest.mark.parametrize("estado_final", ["ATENDIDA", "NO_ASISTIO", "CANCELADA"])
def test_state_los_estados_finales_no_permiten_nada(estado_final):
    c = nueva_cita()
    if estado_final == "CANCELADA":
        c.cancelar()
    else:
        c.confirmar(CUPOS[0], "C-1")
        c.atender() if estado_final == "ATENDIDA" else c.marcar_no_asistio()
    assert c.estado == estado_final
    for operacion in (c.atender, c.marcar_no_asistio, c.cancelar, c.verificar_solicitable):
        with pytest.raises(ValueError):
            operacion()


def test_state_la_cita_ya_confirmada_no_toca_la_agenda_externa():
    clinica, s, c = AgendaClinicaSDK(), None, nueva_cita()
    s = ServicioCitas(clinica=clinica)
    s.solicitar_cita(c, "CLINICA")
    with pytest.raises(ValueError, match="ya fue confirmada"):
        s.solicitar_cita(c, "CLINICA")
    assert clinica.llamadas == 1                                      # no se reservó dos veces


# ======================================================== OBSERVER
class Auditoria(Suscriptor):
    def __init__(self):
        self.registros = []

    def actualizar(self, evento, datos):
        self.registros.append((evento, datos["id"]))


def test_observer_nuevo_suscriptor_sin_tocar_el_servicio():
    s, aud = ServicioCitas(), Auditoria()
    s.publicador.suscribir("cita_confirmada", aud)
    s.solicitar_cita(nueva_cita(7), "HOSPITAL")
    assert aud.registros == [("cita_confirmada", 7)]


def test_observer_dos_suscriptores_originales_reciben_el_evento():
    s = ServicioCitas()
    s.solicitar_cita(nueva_cita(3), "CLINICA")
    assert [e.split(":")[0] for e in s.eventos] == ["whatsapp", "recordatorio"]


def test_observer_una_cita_cancelada_no_publica_nada():
    s = ServicioCitas(clinica=AgendaClinicaSDK(rechaza=True))
    aud = Auditoria()
    s.publicador.suscribir("cita_confirmada", aud)
    s.solicitar_cita(nueva_cita(), "CLINICA")
    assert aud.registros == [] and s.eventos == []


# ======================================================== DECORATOR
def test_decorator_reintentos_envuelve_sin_modificar_al_adaptador():
    clinica = AgendaClinicaSDK(fallas=2)
    agenda = ConReintentos(ClinicaAdapter(clinica), intentos=3)
    assert agenda.reservar(CUPOS[0], "45678912").confirmada is True
    assert clinica.llamadas == 3


def test_decorator_reintentos_no_reintenta_los_rechazos():
    clinica = AgendaClinicaSDK(rechaza=True)
    assert ConReintentos(ClinicaAdapter(clinica)).reservar(CUPOS[0], "1").confirmada is False
    assert clinica.llamadas == 1


def test_decorator_cache_evita_llamadas_repetidas():
    llm = ClienteLLMFalso()
    s = ServicioCitas(llm=llm)
    s.sugerir_especialidad("tos seca"); s.sugerir_especialidad("tos seca")
    assert llm.llamadas == 1


def test_decorator_cache_se_apila_sobre_cualquier_proveedor():
    modelo = ModeloLocalFalso()
    s = ServicioCitas(local=modelo)
    s.sugerir_especialidad("tos seca", "local"); s.sugerir_especialidad("tos seca", "local")
    assert modelo.llamadas == 1


# ======================================================== CHAIN OF RESPONSIBILITY
def test_chain_validaciones_cortan_en_el_primer_error():
    c = nueva_cita()
    c.dni, c.celular = "1", "1"                                       # dos errores
    with pytest.raises(ValueError, match="DNI"):
        cadena_de_reserva().procesar(c)


class SoloAdultos(Eslabon):
    def _aplicar(self, cita):
        if getattr(cita, "edad", 99) < 18:
            raise ValueError("Debe reservar un adulto")
        return cita


def test_chain_se_agrega_una_regla_nueva_sin_tocar_las_demas():
    cadena = SoloAdultos(cadena_de_reserva())
    c = nueva_cita()
    c.edad = 10
    with pytest.raises(ValueError, match="adulto"):
        cadena.procesar(c)
    c.edad = 30
    assert cadena.procesar(c) is c


def test_chain_guardrails_cortan_y_no_llaman_a_los_siguientes():
    class Espia(Eslabon):
        llamado = False

        def _aplicar(self, texto):
            Espia.llamado = True
            return texto

    cadena = SinDiagnostico(Espia())
    with pytest.raises(ValueError, match="diagnóstico"):
        cadena.procesar("Usted tiene gripe")
    assert Espia.llamado is False


def test_chain_cada_guardrail_protege_una_cosa():
    assert LongitudMaxima(5).procesar("ok") == "ok"
    with pytest.raises(ValueError, match="larga"):
        LongitudMaxima(5).procesar("demasiado")
    with pytest.raises(ValueError, match="medicación"):
        SinMedicacion().procesar("tome ibuprofeno")
    assert EspecialidadDelCatalogo().procesar("Medicina general") == "MEDICINA_GENERAL"


# ======================================================== IA aislada (Strategy + doble de prueba)
def test_ia_el_prompt_no_contiene_datos_personales():
    llm = ClienteLLMFalso()
    cita = nueva_cita()
    ServicioCitas(llm=llm).sugerir_especialidad("me duele el pecho")
    assert cita.dni not in llm.ultimo_prompt and cita.celular not in llm.ultimo_prompt
    assert "me duele el pecho" in llm.ultimo_prompt


def test_ia_proveedor_intercambiable_sin_tocar_el_dominio():
    class OtroProveedor(ClaudeAdapter):
        def completar(self, prompt):
            return "CARDIOLOGIA"

    g = GeneradorSugerencias({"otro": ConCache(OtroProveedor(None))},
                             SinDiagnostico(EspecialidadDelCatalogo()))
    assert g.sugerir_especialidad("palpitaciones", "otro") == "CARDIOLOGIA"
