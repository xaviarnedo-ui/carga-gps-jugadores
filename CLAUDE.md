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

Jugador con objetivo individual que NO cuenta para la MEDIA EQUIPO unos días (p. ej. gestión de
cargas tras un alta): `estado --fuera-media 7,18 --desde F --hasta F --nota T` (Excel, app y dashboard
lo excluyen de la media y del cumplimiento del equipo; mantiene objetivo y semáforo).
Objetivo fijado a mano (p. ej. última semana de readaptación por encima del 100%): `objetivos_manuales`
en `estados_jugadores.json` ({"S62": {"20": {métricas}}}); se escribe aunque esté en rehab, se valora con
semáforo y la app lo marca "Readapt. · obj. individual". Combínalo con `--fuera-media` y aplica con
`microciclo.propagar_estados(n, [dorsal])`.

Otros comandos: `objetivos S57` (PDF de objetivos del día para el campo, en `GPS/Informes/Objetivos/`; va en una sola lista por dorsal (decisión del preparador, 19/10; `--por-posicion` para agrupar; `--sin-lesionados` deja solo al grupo); con `--compensar S56` suma a cada jugador lo que le faltó en S56, <90% → hasta el 100%, salvo métrica con ACWR >1,5 o plan de readaptación), `abrir --tipo B --partido J5 --rival X --lunes AAAA-MM-DD` (semana con Copa u otra estructura: `--dias MD+1,MD-2,MD-1,COPA1,MD-2,MD-1,J9 --rival-de COPA1=Eldense`; la Copa es la hoja `COPA1_GPS` y un PDF titulado «COPA …» va a ella) (microciclo
nuevo), `estado [dorsal=estado ...]`, `disponibilidad`, `publicar [--sin-avisar]`.

**Lesiones** (`GPS/lesiones.json`, pestaña "Lesionados" del dashboard): cuando un jugador pasa
a lesión o rehab sin lesión abierta, `procesar` se para y pide el tipo → pregúntalo y relanza
con `--lesion 26="Fractura de nariz"` (la baja es ese día). Al volver a full se cierra sola
(alta = ese día). Corregir fechas/tipos: `gps.py lesiones --abrir/--cerrar`. Descanso o
gestión de carga NO es lesión. Si una lesión se confirma sin PDF (diagnóstico posterior):
`lesiones --abrir D --tipo T --baja F` + `estado D=lesion --desde F --nota T`, que quita el objetivo
en las sesiones aún no cargadas del microciclo activo (las cargadas no se tocan). El diagnóstico se publica tal cual (decisión del preparador).

Rol del MD+1 a mano (p. ej. jugó entero con el filial el día del partido → recuperación): `roles_md1` en `estados_jugadores.json` ({"S71": {"26": "T"}}) y `microciclo.propagar_estados(n, [dorsal])`; lo respetan procesar, propagar y `tipo`.

Fallo de GPS: en partidos con minutos conocidos `--fallo-gps D=min` (estimado desde su REF);
si el preparador dice "ponle los datos de X", `--proxy D=X` (copia, nota de dato proxy, fuera de REF); "ponle la media del equipo" → `--proxy D=media` (media de los full de la sesión).

Un rehab en un PDF aparte del mismo día se pasa junto al PDF de la sesión (se fusiona).
Tras `procesar` (sin `--prueba`) los PDF se mueven solos a `GPS/Sesiones/` o `GPS/Partidos/` (partidos de Liga y del filial con `--ref-duracion`); si ya existía uno con ese nombre, el viejo va a la Papelera.
Una sesión fuera de calendario (p. ej. un martes) va con `--extra` → hoja `Extra_dd-mm_GPS`.

## Reglas de negocio (resumen de la especificación del preparador, 23/09/2026)

- Objetivo del día = `round(REF_PARTIDO × coeficiente, 1)` (hoja MICROCICLOS). MD+1: titular
  si jugó ≥60' el partido anterior, suplente si <60' o no jugó.
- Semáforo (desde 27/10/2026, `C.TOLERANCIA` y `reglas.js`): zona verde Distancia/HMLD ±10%, HSR/ACC/DEC ±20%,
  Sprints ±2 en valor absoluto; azul por debajo, naranja hasta el doble de la tolerancia por encima, rojo más
  (objetivo 0 → verde). % de cumplimiento de una sesión = media ponderada de real/obj (MD-4: ACC y DEC ×2;
  MD-3: HSR y Sprints ×2; Distancia y HMLD ×1, `C.PESOS_DIA`); el de la semana = media de sus sesiones.
  Sprints en el %: dentro de ±2 = 100%; fuera solo cuenta lo que se sale (`C.ratio_cumplimiento`).
  MD+1 titulares: solo objetivo de Distancia y HMLD (coeficiente vacío en MICROCICLOS = sin objetivo).
- full: Obj/Real/Dif/semáforo, cuenta en la media. rehab: solo Real, no cuenta en la media,
  sí en Acumulado y ACWR. lesión: nada (0 en ACWR). descanso: sin objetivo ese día.
- Los cambios de estado se aplican desde ese día en adelante, nunca hacia atrás.
- Acumulado semanal: quien tiene objetivo semanal acumula solo desde su primer día con objetivo
  (+ Extra desde ese día); su readaptación previa no se compara con el objetivo (sí va al ACWR).
  Quien no tiene objetivo en toda la semana: acumulado total, informativo (corrección 26/09).
- ACWR: aguda Σ7d/7, crónica Σ28d/28 en días naturales (sin sesión = 0); media de equipo
  sin los ACWR = 0. Se recalcula siempre desde las hojas *_GPS de todos los microciclos.
- REF_PARTIDO = MEDIA PONDERADA POR MINUTOS (desde 19/10/2026; antes media simple) de la
  pretemporada (peso 1) y de cada partido de Liga (peso = minutos jugados / duración real, máx. 1;
  los cameos cuentan pero poco) J≥2 con GPS real (+ Copa, `COPA#`, como uno de Liga más desde el 26/10; + partidos con el filial si el preparador lo pide, `--ref-duracion`). Los
  componentes viven en `GPS/ref_componentes.json` (desde 28/09; antes cada partido promediaba
  con el valor anterior). Cada partido entra como `estimado_T`, con
  `estimado_T = Real + (T − M)·(Real/M)·0,90` y **T = duración real de ese partido** (minutos
  EXACTOS del jugador que más jugó, con descuento; desde 25/09/2026, antes era 95'). Sin
  extrapolar si M ≥ T. J1 excluido. Reprocesar un partido sobrescribe su componente (no cuenta
  dos veces). Cameos cortos → avisar, no corregir. Fallo de GPS con minutos
  conocidos: `Real = REF / (1 + 0,9·(T − M)/M)`, marcado como estimado y fuera de REF_PARTIDO.
  Los minutos para la fórmula van con segundos (8:49 ≠ 8,8').
- Partidos de Liga (J2+): objetivo por jugador = su REF_PARTIDO de justo antes de ese partido
  escalada a sus minutos (exactos) con la fórmula de fatiga inversa (T = duración real). Lo
  escribe `procesar` en la hoja J#_GPS, bloque N-T ("Obj …" + "Cumpl. medio"; A-L intactas) y
  colorea el real con el semáforo; `import_data.py` lo lee de ahí (si falta, lo calcula con
  `pipeline/ref_historial.py`). Estimados por fallo de GPS: con objetivo (para la media) pero
  sin semáforo ni %. J1 y amistosos: sin objetivo. Tipo A/C, microciclos sin partido o dobles jornadas
  no están especificados: preguntar antes.
- Toda decisión, estimación o cambio de estado queda escrito en las notas del propio Excel.

## Técnica

- openpyxl: vaciar SIEMPRE con `cell.value = None` (`ws.cell(r, c, value=None)` no borra).
- Los Excel de microciclo no tienen fórmulas; Disponibilidad se genera con valores. No hace
  falta LibreOffice.
- Tests: `python3 -m unittest discover tests` (regresión contra el histórico real; se
  saltan si no están los Excel).
- La app: assets con `?v=N` + `CACHE` de `sw.js` si se toca CSS/JS.
