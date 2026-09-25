# Carga GPS — cómo trabajar en este proyecto

Proyecto único para los datos GPS del AT Baleares: **Excel de seguimiento + app PWA +
dashboard**. El preparador solo pasa el PDF de Catapult ("Informe de actividades") de una
sesión o partido; Claude actualiza todo con `gps.py`.

- Excel (fuente de verdad, FUERA del repo, que es público): `~/Desktop/AT BALEARES 26-27/GPS/`
  (`Microciclos/Microciclo N.xlsx`, `Microciclo_Tipo.xlsx`, `Disponibilidad y Minutos.xlsx`,
  `estados_jugadores.json`, `pipeline_ref_log.json`, copias en `_backups/`).
- App (`index.html`, `jugador.html`) y dashboard (`dashboard.html`) leen el mismo `data.js`,
  que genera `import_data.py`. Publicar = push a `main` → GitHub Pages.
- Diseño: `docs/superpowers/specs/2026-09-23-pipeline-pdf-design.md`.

## Al recibir un PDF

1. `python3 gps.py leer <pdf> [<pdf rehab>...]` — tabla, cruce con plantilla, estado vigente,
   grupos de duración y PNG del resumen. **Mira los PNG**: el donut "Participación del
   deportista" (Full/Rehab/N/A) es el checksum de estados y los bloques ("Rehab Barto",
   "Titulares", "Modified"...) dicen quién hizo qué.
2. Decide el estado del día de cada jugador: `full`, `rehab`, `lesion`, `descanso` (sesiones)
   y `nc` / `noconv` (partidos). **Pregunta al preparador solo** si hay una ausencia sin
   explicar, un cambio de estado que el PDF no confirma, o un fallo de GPS. Nunca asumas lesión.
3. `python3 gps.py procesar <pdf>... [--estado 6=descanso] [--fallo-gps 14=50] --prueba`
   para revisar en `GPS/_prueba/`, y luego sin `--prueba` (y con `--publicar` si toca).
   Si el script responde "NECESITO UNA DECISIÓN" no ha escrito nada: pregunta y relanza.
4. Informa: estados, avisos de ACWR > 1,5, cameos en REF_PARTIDO, cambios de estado.

Otros comandos: `abrir --tipo B --partido J5 --rival X --lunes AAAA-MM-DD` (microciclo
nuevo), `estado [dorsal=estado ...]`, `disponibilidad`, `publicar [--sin-avisar]`.

**Lesiones** (`GPS/lesiones.json`, pestaña "Lesionados" del dashboard): cuando un jugador pasa
a lesión o rehab sin lesión abierta, `procesar` se para y pide el tipo → pregúntalo y relanza
con `--lesion 26="Fractura de nariz"` (la baja es ese día). Al volver a full se cierra sola
(alta = ese día). Corregir fechas/tipos: `gps.py lesiones --abrir/--cerrar`. Descanso o
gestión de carga NO es lesión. El diagnóstico se publica tal cual (decisión del preparador).

Fallo de GPS: en partidos con minutos conocidos `--fallo-gps D=min` (estimado desde su REF);
si el preparador dice "ponle los datos de X", `--proxy D=X` (copia, nota de dato proxy, fuera de REF).

Un rehab en un PDF aparte del mismo día se pasa junto al PDF de la sesión (se fusiona).
Una sesión fuera de calendario (p. ej. un martes) va con `--extra` → hoja `Extra_dd-mm_GPS`.

## Reglas de negocio (resumen de la especificación del preparador, 23/09/2026)

- Objetivo del día = `round(REF_PARTIDO × coeficiente, 1)` (hoja MICROCICLOS). MD+1: titular
  si jugó ≥60' el partido anterior, suplente si <60' o no jugó.
- Semáforo: < −10% azul · ±10% verde · +10–20% naranja · > +20% rojo (objetivo 0 → verde).
- full: Obj/Real/Dif/semáforo, cuenta en la media. rehab: solo Real, no cuenta en la media,
  sí en Acumulado y ACWR. lesión: nada (0 en ACWR). descanso: sin objetivo ese día.
- Los cambios de estado se aplican desde ese día en adelante, nunca hacia atrás.
- ACWR: aguda Σ7d/7, crónica Σ28d/28 en días naturales (sin sesión = 0); media de equipo
  sin los ACWR = 0. Se recalcula siempre desde las hojas *_GPS de todos los microciclos.
- REF_PARTIDO tras cada partido de Liga J≥2 con GPS real:
  `nuevo = round((anterior + estimado_T) / 2, 1)`, con
  `estimado_T = Real + (T − M)·(Real/M)·0,90` y **T = duración real de ese partido** (minutos
  EXACTOS del jugador que más jugó, con descuento; desde 25/09/2026, antes era 95'). Sin
  extrapolar si M ≥ T. J1 excluido. J2 y J3 ya recalculados en bloque (bloqueados en
  `pipeline_ref_log.json`). Cameos cortos → avisar, no corregir. Fallo de GPS con minutos
  conocidos: `Real = REF / (1 + 0,9·(T − M)/M)`, marcado como estimado y fuera de REF_PARTIDO.
  Los minutos para la fórmula van con segundos (8:49 ≠ 8,8').
- Partidos: sin objetivo ni semáforo. Tipo A/C, microciclos sin partido o dobles jornadas
  no están especificados: preguntar antes.
- Toda decisión, estimación o cambio de estado queda escrito en las notas del propio Excel.

## Técnica

- openpyxl: vaciar SIEMPRE con `cell.value = None` (`ws.cell(r, c, value=None)` no borra).
- Los Excel de microciclo no tienen fórmulas; Disponibilidad se genera con valores. No hace
  falta LibreOffice.
- Tests: `python3 -m unittest discover tests` (regresión contra el histórico real; se
  saltan si no están los Excel).
- La app: assets con `?v=N` + `CACHE` de `sw.js` si se toca CSS/JS.
