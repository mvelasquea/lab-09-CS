# Bitácora de IA (E7) — CitaSalud Arequipa

> **Regla de oro:** la IA propone, el equipo decide y verifica. Esta bitácora registra lo que **realmente ocurrió**
> en la sesión de trabajo con el asistente (Claude). Cada integrante debe **revisar y confirmar la columna
> "Decisión del equipo"** y **agregar sus propias interacciones** (otras herramientas, otros prompts, otras
> correcciones). No se ingresaron datos personales, credenciales ni claves de API en ningún prompt.

| # | Prompt (resumen) | Propuesta de la IA | Verificación realizada | Decisión del equipo |
|---|---|---|---|---|
| 1 | **Detector de olores** (Prompt IA 1): guía del Lab 07 + caso CitaSalud (política de cupos, ciclo de la cita, recordatorios, validaciones, IA que clasifica el motivo) | Versión *antes* y tabla de 10 filas: 7 olores con su patrón (Strategy, Adapter, Decorator, State, Observer, Chain) y 3 alternativas a descartar (Singleton, Abstract Factory, LLM como juez) | `radon cc` → `solicitar_cita` = E (36). Se **corrigieron los números de línea** citados en `olores.md` contrastándolos con `grep -n` sobre el archivo real | 7 aceptados, 3 rechazados *(confirmar)* |
| 2 | Generar `externos.py`, `antes/servicio.py` y pruebas de caracterización | Simuladores con interfaces distintas (dict/ISO vs. tupla/`dd/mm/aaaa`), versión ingenua y 27 pruebas sobre `antes` | `pytest -k antes` → **24 passed, 3 xfailed**; todas verifican estado, eventos y excepciones, ninguna llama a servicios reales | Aceptada |
| 3 | Refactor del flujo hacia Strategy + Adapter + Factory + Decorator + State + Observer + Chain | Módulos `agendas`, `politicas`, `estados`, `eventos`, `validaciones`, `cadena`, `ia`, `fabrica`. **Desviación de la guía:** se pidió todo en un solo paso; la guía recomienda un patrón por vez (Prompt IA 2) | Suite completa sobre `antes` y `despues`: **51 passed, 3 xfailed** a la primera. `radon`: `solicitar_cita` E(36) → A(3) | Aceptada. *El equipo debe repartir el código en commits E2, E3, E4, E5* |
| 4 | Revisión del flujo `despues`: ¿qué pasa si la cita ya está CONFIRMADA? | **Error de diseño detectado al revisar (no por una prueba en rojo):** si el estado se valida después de llamar a la agenda, se reservaría dos veces. Se agregó el eslabón `EstadoSolicitable` y `test_state_la_cita_ya_confirmada_no_toca_la_agenda_externa` | *Mutación real:* se quitó `EstadoSolicitable` de la cadena → **1 prueba falla** (la nueva). Las pruebas de caracterización **no** lo detectaban (solo comprueban que lance `ValueError`) | Corregida |
| 5 | Verificar que las pruebas atrapan el error típico de la IA (`ConReintentos` que reintenta también los rechazos) | Variante "mutante" de `ConReintentos` escrita a propósito (**no** fue un error espontáneo de la IA) | Con el mutante: **2 pruebas fallan** (`test_cupo_tomado_se_cancela_sin_eventos_ni_reintentos[despues]` y `test_decorator_reintentos_no_reintenta_los_rechazos`); se restauró el código y vuelven a pasar 77 | Código original conservado |
| 6 | Bug de la versión antes (hallazgo del refactor) | `solicitar_cita` deja la cita **CONFIRMADA** si falla la sede, la política o no hay cupos | 3 pruebas `test_error_de_reserva_no_altera_el_estado`: `xfail` en `antes`, **PASSED** en `despues` | Corregida (esperar a validar antes de cambiar de estado) |
| 7 | Revisión de las propias pruebas | El escenario `politica` de `test_error_de_reserva_no_altera_el_estado` usaba una agenda vacía, así que fallaba por "sin cupos" y no por la política | Se corrigió para que cada escenario tenga **una sola causa** | Corregida |
| 8 | Diagramas PlantUML desde el código | 7 diagramas (políticas, agendas, estados, eventos, validaciones, IA, secuencia) + `clases.puml` consolidado | `scripts/verificar_clases.py` (pyreverse): **40 clases y 27 herencias coinciden**; revisión visual de `agendas.png` y `secuencia.png` | Aceptada (sin correcciones de nombres en esta ejecución) |
| 9 | Guardrails y privacidad de la IA | Cadena `LongitudMaxima → SinDiagnostico → SinMedicacion → EspecialidadDelCatalogo`; el prompt lleva **solo el motivo** (sin DNI, nombre ni celular) | `test_ia_el_prompt_no_contiene_datos_personales`, `test_guardrails_bloquean_respuestas_invalidas` (4 casos) | Aceptada. Rechazado "otro LLM como juez" |

## Lecciones

1. Las pruebas de caracterización **no lo detectan todo**: comprobar solo que se lance una excepción dejó pasar una
   doble reserva. Hay que verificar también los *efectos* (por ejemplo, cuántas veces se llamó al servicio externo).
2. Pedir todos los patrones de una vez funciona, pero oculta *qué olor elimina cada uno*. Conviene un patrón por commit.
3. La IA como clasificador de motivos de consulta maneja **datos de salud**: minimizar lo que se envía y no cachear
   en disco sin una política de retención.
