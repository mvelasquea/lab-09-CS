# Procedencia de las grabaciones (léase antes de entregar)

La guía exige que **cada respuesta se grabe tal como la dio el modelo, sin editarla** y que cada grupo use su asistente.

**Cómo se generaron las grabaciones de este repositorio:** las redactó el asistente Claude en **una sola sesión de
trabajo**, respondiendo a cada prompt ya renderizado (v1, v2 y v3 para cada caso de las Tareas A y B, y los ataques de
red teaming). No se ajustaron para que fallen o pasen: los resultados de promptfoo son los que salieron.

**Limitaciones que deben conocer (y declarar):**
- No son respuestas de chats independientes: salieron de una misma sesión que conocía los tres prompts.
- Las listas largas y repetitivas de los casos **B6** (20 pacientes en v1 y v2, 10 en v3) se **compusieron con un
  script auxiliar** por su tamaño; el formato y el contenido siguen lo que daría el modelo, pero no se escribieron a mano.
- Las historias de `casos.yaml` son **ejemplos del dominio CitaSalud**, no su Product Backlog real.

**Qué deben hacer ustedes si su docente exige sesiones propias:** reemplacen las historias por las de su backlog, abran
chats **nuevos** y peguen el prompt renderizado de cada versión y caso; guarden cada respuesta cruda en
`prompts/<tarea>/grabaciones/<version>/<id>.txt` y vuelvan a ejecutar `promptfoo eval`. Los números cambiarán: eso es
parte del ejercicio. Documenten en `bitacora-ia.md` qué asistente y qué fecha usaron.
