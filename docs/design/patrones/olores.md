# Olores detectados y patrón propuesto (E1) — CitaSalud Arequipa

**Flujo crítico (secuencia del Lab 05):** solicitar y confirmar una cita + sugerir especialidad con IA.
**Código analizado:** `src/citas/antes/servicio.py` (1 archivo, 137 SLOC).

## Medición inicial (`radon cc -s -a src/citas/antes/`)

```
M 52:4 ServicioCitas.solicitar_cita - E (36)
C 44:0 ServicioCitas - C (18)
M 133:4 ServicioCitas.sugerir_especialidad - B (9)
Average complexity: C (10.43)
```

`solicitar_cita` tiene complejidad **36 (rango E)**: más de tres veces el umbral recomendado (10).

## Tabla de olores (resultado del Prompt IA 1 + verificación del equipo)

| # | Olor detectado (líneas aprox.) | Patrón propuesto por la IA | Principio SOLID | Costo de aplicarlo | Decisión del equipo |
|---|---|---|---|---|---|
| 1 | `if/elif` por **política de asignación** de cupos (PROXIMO / CARGA / PREFERIDO), 3 bucles casi iguales (l. 80-102) | **Strategy** + Factory (registro) | O (abierto/cerrado) | +1 interfaz, +3 clases | **Aceptado** |
| 2 | El servicio conoce los **detalles de cada SDK**: dict vs. tuplas, ISO vs. `dd/mm/aaaa`, especialidad textual vs. numérica (l. 70-78 y 104-121) | **Adapter** (+ Factory de sedes) | D (inversión de dependencias) | +1 puerto, +2 adaptadores | **Aceptado** |
| 3 | **Bloque de reintentos duplicado** para clínica y hospital (l. 104-121) | **Decorator** (`ConReintentos`) | S, O | +1 clase | **Aceptado** |
| 4 | **Condicionales sobre `cita.estado`** y estado asignado como texto antes de reservar (l. 53-59 y 68) | **State** (coincide con la máquina de estados del Lab 05) | S, O, L | +1 clase base, +5 estados | **Aceptado** |
| 5 | El servicio **arma a mano** el WhatsApp y el recordatorio (l. 125-128) | **Observer** | S, O | +1 publicador, +2 suscriptores | **Aceptado** |
| 6 | **Validaciones de reserva en secuencia**, mezcladas con el resto (l. 53-67) | **Chain of Responsibility** | S, O | +1 base, +5 eslabones | **Aceptado** |
| 7 | `if/elif` por **proveedor de LLM** y validaciones de la respuesta mezcladas (l. 137-153) | **Strategy + Adapter + Chain of Responsibility** (+ Decorator de caché) | S, O, D | +1 puerto, +2 adaptadores, +4 guardrails | **Aceptado** |
| 8 | "`FabricaAgendas` debería ser **Singleton**" | Singleton | — | Estado global | **RECHAZADO**: impide inyectar SDK simulados en las pruebas; cada `ServicioCitas` tiene su fábrica |
| 9 | "Usar **Abstract Factory** para crear familias de sedes (agenda + notificador + facturación)" | Abstract Factory | — | Jerarquía paralela | **RECHAZADO**: no hay familias de productos, solo 2 sedes con 1 producto; sobreingeniería |
| 10 | "Validar la salida del LLM con **otro LLM como juez**" | (ninguno: técnica, no patrón GoF) | — | Costo y latencia extra | **RECHAZADO**: para el MVP bastan reglas deterministas (no hay clave de API ni red en pruebas) |

## Bug encontrado en la versión antes

`solicitar_cita` cambia `cita.estado = "CONFIRMADA"` **antes** de validar la sede, la política o los cupos.
Si luego lanza `ValueError`, la cita queda CONFIRMADA sin cupo. Las tres pruebas
`test_error_de_reserva_no_altera_el_estado[...]` lo documentan como `xfail` en `antes` y pasan en `despues`.
