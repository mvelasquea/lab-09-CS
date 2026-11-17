# ADR-005: Patrones de diseño en el módulo Citas

- **Estado:** Aceptado (27/10/2026)
- **Decisores:** Grupo XX (CitaSalud Arequipa) — Construcción de Software 2026B
- **Relacionado:** ADR-001…004 (Lab 04), diagrama de secuencia y máquina de estados (Lab 05)

## Contexto

`solicitar_cita()` tenía complejidad ciclomática **36 (E)** y 137 SLOC en un solo archivo. Cada sede nueva
(clínica, hospital, …), cada política de asignación de cupos o cada proveedor de IA obligaba a modificar el servicio.
La versión antes tenía además un bug: ante una sede, política o agenda sin cupos, la cita quedaba CONFIRMADA.
La salida del LLM (que sugiere la especialidad desde el motivo de consulta) no es confiable: podría emitir
un diagnóstico o una medicación. El MVP debe estar en producción en 1 mes.

## Decisión

| Problema (olor) | Patrón | Prueba que lo demuestra |
|---|---|---|
| `if/elif` por política de cupos | **Strategy** (`PoliticaAsignacion`) + **Factory** (`FabricaPoliticas`) | `test_open_closed_nueva_politica_sin_modificar_el_servicio` |
| El servicio conoce los SDK de cada sede | **Adapter** (`ClinicaAdapter`, `HospitalAdapter`) + **Factory** (`FabricaAgendas`) | `test_adapter_dos_sdk_distintos_producen_la_misma_interfaz`, `test_open_closed_nueva_sede_sin_modificar_el_servicio` |
| Reintentos duplicados / caché | **Decorator** (`ConReintentos`, `ConCache`) | `test_decorator_reintentos_no_reintenta_los_rechazos`, `test_decorator_cache_evita_llamadas_repetidas` |
| Condicionales sobre `cita.estado` | **State** (Lab 05) | `test_state_impide_transiciones_invalidas`, `test_state_los_estados_finales_no_permiten_nada` |
| Avisos armados a mano | **Observer** (`PublicadorEventos`) | `test_observer_nuevo_suscriptor_sin_tocar_el_servicio` |
| Validaciones mezcladas | **Chain of Responsibility** (`Eslabon`) | `test_chain_se_agrega_una_regla_nueva_sin_tocar_las_demas` |
| Salida del LLM no confiable | **Strategy + Adapter** (`ProveedorLLM`) + **Chain** (guardrails) + **Decorator** (caché) | `test_guardrails_bloquean_respuestas_invalidas`, `test_ia_proveedor_intercambiable_sin_tocar_el_dominio` |

Se **rechazan**: **Singleton** (estado global, impide inyectar SDK simulados), **Abstract Factory**
(no hay familias de productos: sobreingeniería), **LLM como juez** de la salida (costo y latencia; bastan reglas
deterministas) y **Command + cola** (no hay requisito offline para este flujo todavía).

**Reglas de la IA:** el prompt contiene solo el motivo de consulta (nunca DNI, nombre ni celular); la IA clasifica
hacia el catálogo de especialidades y **nunca diagnostica ni receta**; su salida pasa por la cadena de guardrails.

## Consecuencias

- (+) Complejidad máxima de un método: **5** (antes 36); `solicitar_cita` pasó de **E (36) a A (3)**; promedio 10,43 → 1,77.
- (+) Nuevas sedes, políticas, suscriptores y proveedores de IA sin modificar el servicio (abierto/cerrado).
- (+) IA probable sin API ni red (dobles de prueba); 77 pruebas pasan, 3 `xfail` documentan el bug de la versión antes.
- (−) 327 SLOC frente a 137 y 10 archivos frente a 1: más indirección; el equipo debe conocer los patrones.
- (−) `ConReintentos` reintenta reservas ante `TimeoutError`; si la agenda externa no es idempotente podría duplicar
  reservas cuando el timeout ocurre *después* de procesar. Pendiente: enviar una clave de idempotencia.
- (−) `ConCache` guarda en memoria motivos de consulta (dato de salud). Pendiente: política de retención y límites.
