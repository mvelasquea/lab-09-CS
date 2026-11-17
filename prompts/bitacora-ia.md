# Bitácora de IA — Lab 09 (Prompt engineering) · CitaSalud Arequipa

> La IA propone, el equipo decide y verifica. Esta bitácora registra lo que **realmente ocurrió** en la sesión de trabajo
> con el asistente (Claude). Cada integrante debe **confirmar la columna "Decisión del equipo"** y **agregar sus propias
> interacciones** (otros prompts, otras herramientas, hallazgos propios). No se ingresaron datos personales, credenciales
> ni claves de API en ningún prompt. Procedencia y límites de las grabaciones: ver `LEEME-grabaciones.md`.

| # | Interacción | Hallazgo | Evidencia | Decisión del equipo |
|---|---|---|---|---|
| 1 | Diseñar los prompts v1→v3 de la Tarea A (criterios Gherkin) a partir del ejemplo de la guía adaptado a CitaSalud | v1 no es consumible por código (prosa); v2 arregla el formato pero **no evalúa INVEST**: en H7 inventó escenarios con umbrales | promptfoo: v1 0/8, v2 7/8 (falla H7·A4), v3 8/8 | Aceptada: v3 aplica Persona, Cognitive Verifier, Flipped Interaction, Template y few-shot |
| 2 | Diseñar la Tarea B (datos de prueba sintéticos) y la aserción clave | v1 y v2 produjeron DNIs de 8 dígitos y celulares que empiezan con 9: **podrían ser datos reales** | promptfoo: v1 0/8, v2 0/8 (fallan B2, B3, B4), v3 8/8 | Aceptada: DNI `TEST####`, celular `0########`, nombre `[FICTICIO]` |
| 3 | **Sugerencia de la IA rechazada con evidencia:** usar DNIs numéricos "obviamente falsos" (p. ej. `00000001`) | Un DNI de 8 dígitos no se distingue de uno real; el DNI `00000001` aparece en las grabaciones v1 y v2 de B7 | B3 falla en v1/v2 y pasa en v3 con `TEST####` | Rechazada a favor de un formato que **no existe** como DNI |
| 4 | Evaluador defectuoso (E3.4): las aserciones de una sola línea con `return` de B1, B2, B6 y B7 | **Falso negativo del evaluador:** promptfoo lanzó "Unexpected token 'return'" y marcó como fallo respuestas **correctas** (v3 mostraba 4/8 en lugar de 8/8) | Primera corrida de la Tarea B: v3 = 50 %; tras corregir: 100 % | Corregida: aserciones escritas en varias líneas |
| 5 | Proveedor grabado de promptfoo | Primera corrida: **24 errores**, la etiqueta del prompt trae `ruta/v1.txt: <texto>` y se tomó como versión el texto | `Falta la grabación …/{{historia}}/H1.txt` | Corregida en `proveedor_grabado.py` |
| 6 | Pruebas del generador con proveedor grabado | `ProveedorGrabado` tomó `id="EJ"` del **ejemplo few-shot** en lugar del id real: **corrección detectada por las pruebas** (4 fallos) | `pytest`: 4 failed → 88 passed | Corregida: se usa la última coincidencia |
| 7 | Revisar si el esquema basta como defensa | **El esquema no detecta escenarios inventados:** la v2 de H7 es JSON válido que cumple el esquema | `test_regla_semantica_rechaza_escenarios_inventados…` | Aceptada: se agregó una capa de reglas semánticas en el generador |
| 8 | Red teaming con token canario | R1–R4 no vencieron ni a la v1; R5 y R6 solo fallan en v1 | `prompts/seguridad/red-team.md` | Aceptada con la salvedad: probar también un modelo más débil (Opción A/B) |
| 9 | Aserción A3 "sin implementación" | Ya revisa solo los `escenarios`, como corrigió la guía; para texto no JSON (v1) revisa todo el texto | `promptfooconfig.yaml` | Aceptada |

## Pendiente del equipo
- Reemplazar las historias de ejemplo por las de su Product Backlog (y regrabar).
- Ejecutar E7.3 (3 ejecuciones en chats nuevos): ver `prompts/criterios/ejecuciones/LEEME.md`.
- Reparto de Pull Requests y etiqueta `v0.9-prompts`.
