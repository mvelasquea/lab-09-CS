# Cuestionario del Lab 07 — respuestas para CitaSalud Arequipa

> Borrador de apoyo basado en el código real del repositorio. Cada integrante debe leerlo, entenderlo y reescribirlo
> con sus propias palabras antes de entregarlo.

**1. Patrón arquitectónico vs. patrón de diseño.** Un patrón arquitectónico organiza el sistema completo (Lab 04:
monolito modular con capas y eventos entre módulos: Citas, Pacientes, Notificaciones). Un patrón de diseño organiza las
clases *dentro* de un módulo: en Citas, `State` modela el ciclo de la cita y `Strategy` la política de asignación.

**2. Strategy y abierto/cerrado.** `PoliticaAsignacion` tiene tres implementaciones (`MasProximo`, `MenorCarga`,
`MedicoPreferido`). Para agregar una nueva (`UltimoDisponible` en `test_open_closed_nueva_politica_...`) no se
modificó nada del servicio: solo se escribió la clase y se hizo `fabrica_politicas.registrar("ULTIMO", ...)`.

**3. Adapter vs. Decorator.** Ambos envuelven un objeto, pero con intención distinta. El *Adapter* **cambia la
interfaz** (`ClinicaAdapter` convierte `listar_horarios()`/dicts en `cupos_disponibles()`/`Cupo`). El *Decorator*
**conserva la interfaz** y agrega comportamiento (`ConReintentos` sigue siendo una `AgendaMedica`, pero reintenta).

**4. State y la máquina de estados.** El diagrama del Lab 05 ya es un conjunto de estados con transiciones permitidas;
`State` lo materializa 1 a 1: una clase por estado y un método por transición. Ganamos que una transición inválida es
imposible por construcción (la clase base lanza `ValueError`), eliminamos los `if cita.estado == ...` y cada estado
puede crecer con comportamiento propio (p. ej., reembolso al cancelar).

**5. Pruebas de caracterización.** Fijan lo que el sistema hace *hoy* para poder refactorizar sin romperlo; las mismas
pruebas corren sobre `antes` y `despues`. Detectaron un error: ante una sede, política o agenda sin cupos, `antes` dejaba
la cita CONFIRMADA (3 pruebas `xfail` en `antes`, `PASSED` en `despues`). Además, una mutación (reintentar rechazos)
hizo fallar 2 pruebas.

**6. Rechazos y "patternitis".** Se rechazaron Singleton (estado global; impide inyectar SDK simulados), Abstract
Factory (no hay familias de productos) y un LLM como juez (costo y latencia). *Patternitis* es aplicar patrones sin un
olor concreto que los justifique: más clases e indirección sin beneficio.

**7. La salida del LLM como dato no confiable.** Es no determinista, puede equivocarse con seguridad y, en salud, un
error es grave. Guardrails de CitaSalud: `LongitudMaxima` (respuestas anómalas), `SinDiagnostico` (que la IA no
diagnostique), `SinMedicacion` (que no recete) y `EspecialidadDelCatalogo` (que solo se acepte una especialidad
existente y se normalice). Además, el prompt lleva solo el motivo, nunca datos personales.

**8. ¿Valió la pena?** Sí: `solicitar_cita` bajó de complejidad 36 (E) a 3 (A) y el promedio de 10,43 a 1,77;
agregar sedes o políticas no exige modificar el servicio. A cambio, el código creció de 137 a 327 SLOC y de 1 a 10
archivos. Con una sola sede, una sola política y sin IA, la versión antes (con el bug corregido) habría bastado; los
patrones se justifican por los cambios previstos.
