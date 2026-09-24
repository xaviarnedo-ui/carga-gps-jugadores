# Pipeline PDF → Excel → app + dashboard

Fecha: 2026-09-23 · Estado: aprobado ("dale gas")

## Objetivo

Que el preparador solo tenga que pasar el PDF de Catapult ("Informe de actividades") de una
sesión o partido y que, de una vez, se actualicen:

1. los Excel de seguimiento (`~/Desktop/AT BALEARES 26-27/GPS/`),
2. la app PWA (entrenador + jugador) y
3. el dashboard analítico — estos dos ya comparten `data.js`, así que basta con
   `import_data.py` + `git push`.

Las reglas de negocio vienen de la "Especificación de reglas — Procesamiento de datos
GPS/rendimiento" que el preparador pasó el 23/09 (resumen en `CLAUDE.md`).

## Reparto de trabajo

- **Scripts deterministas (`pipeline/`, CLI `gps.py`)**: todo lo mecánico — leer el PDF,
  escribir hojas, semáforos, medias, Acumulado, ACWR, Disponibilidad, REF_PARTIDO,
  apertura de microciclo, copia de seguridad, verificación, publicación.
- **Claude**: lo que requiere criterio — mirar el donut de participación y los bloques del
  PDF (son imagen), decidir el estado de cada jugador (full / rehab / lesión / descanso /
  convocado-no-jugó), preguntar solo ante ambigüedades médicas/técnicas, y lanzar el script.

## Componentes

| Módulo | Responsabilidad |
|---|---|
| `pipeline/config.py` | rutas, métricas, colores de semáforo |
| `pipeline/pdf_catapult.py` | PDF → `Informe` (código, tipo MD, fecha, filas por jugador, medias); PNG de las págs. 1-2 |
| `pipeline/plantilla.py` | nombre del PDF ("MARTIN, ALVARO") → dorsal, usando los nombres de las hojas |
| `pipeline/xlsx.py` | utilidades openpyxl (vaciar con `cell.value = None`, semáforo, localizar filas) |
| `pipeline/estados.py` | `GPS/estados_jugadores.json`: estado vigente de cada jugador + historial fechado |
| `pipeline/sesion.py` | rellenar `S##_GPS` (Real/Dif/semáforo, VelMax/PL/Duración, MEDIA EQUIPO, notas) y propagar cambios de estado a los Obj del resto de la semana |
| `pipeline/partido.py` | rellenar `J#/PT#_GPS`, estimación por fallo de GPS (fórmula inversa), actualización de REF_PARTIDO con deshacer |
| `pipeline/extra.py` | crear `Extra_dd-mm_GPS` para sesiones fuera de calendario |
| `pipeline/acumulado.py` | recalcular la hoja `Acumulado` entera desde las hojas de sesión |
| `pipeline/carga_ac.py` | histórico diario PL/HSR/Sprint de todos los microciclos → ACWR y hoja `CARGA_AC` |
| `pipeline/disponibilidad.py` | regenerar `Disponibilidad y Minutos.xlsx` desde los microciclos (valores, sin fórmulas) |
| `pipeline/microciclo.py` | abrir el microciclo N+1 (copia + vaciado + objetivos) |
| `pipeline/publicar.py` | `import_data.py` + commit + push |

## Decisiones

- **Fuente de verdad = las hojas `*_GPS`.** Acumulado, CARGA_AC y Disponibilidad se
  recalculan enteros cada vez (idempotente: procesar dos veces el mismo PDF da lo mismo).
  El ACWR del Excel actual no es reproducible con la fórmula de la especificación (p. ej.
  Montcheu PL 1,30 en el Excel vs 1,18 calculado); a partir de ahora se recalcula siempre
  desde los datos de las hojas.
- **Sin LibreOffice**: los Excel de microciclo no tienen fórmulas; Disponibilidad se genera
  con valores calculados (TOTAL, MÁXIMO, % DISPON.) en vez de fórmulas.
- **Disponibilidad propia**: se regenera desde los microciclos; el fichero antiguo (hasta
  agosto) se archiva en `GPS/_archivo/`.
- **Copia de seguridad** de cada Excel antes de tocarlo en `GPS/_backups/<timestamp>/`.
- **REF_PARTIDO**: cada actualización guarda los valores previos en
  `GPS/pipeline_ref_log.json`, de modo que reprocesar un partido deshace y vuelve a aplicar
  (nunca promedia dos veces).
- **`import_data.py`**: `LIGA_REF` y `NO_REF` se derivan de los datos (partidos J≥2 con
  datos; jugadores marcados como estimados) en vez de mantenerse a mano.
- **Media del Acumulado**: jugadores con Objetivo semanal; si aún no tienen real cuenta 0.
  Semáforo del Acumulado = acumulado vs objetivo "a fecha" (suma de los Obj de las sesiones
  ya cargadas).
- Excel y datos NUNCA entran en el repo (es público). Los tests de regresión leen los Excel
  locales y se saltan si no existen.

## Flujo al recibir un PDF

1. `python3 gps.py leer <pdf>` → tabla, cruce con plantilla, ausencias, grupos de duración,
   estado vigente de cada jugador, PNG de resumen para leer el donut.
2. Claude decide estados (pregunta si hay una ausencia sin explicar o un cambio de estado
   no confirmado).
3. `python3 gps.py procesar <pdf> [--estado 6=descanso ...] [--publicar]`
   → backup → hoja de sesión/partido → Acumulado → CARGA_AC → Disponibilidad → verificación
   → `import_data.py` → (push + aviso a jugadores).

## Pruebas

`tests/` (unittest, sin dependencias): regresión con el histórico — vaciar S46/S45/S44/J3 de
una copia, reprocesar su PDF y comparar celda a celda con el Excel original; tests unitarios
de fórmulas (fatiga, inversa, ACWR, semáforo, nombres).

## Ampliación 2026-09-24: lesiones

- `GPS/lesiones.json` (`pipeline/lesiones.py`): una entrada por lesión (dorsal, tipo, baja, alta).
  Una lesión va de la baja al primer día de vuelta full; la readaptación va dentro.
  `procesar` la abre al pasar a lesión/rehab (exige `--lesion D="tipo"`) y la cierra al volver
  a full. `import_data.py` la publica en `data.js` como `lesiones` (diagnóstico visible: decisión
  del preparador).
- Dashboard: pestaña "Lesionados" (abiertas / cerradas, desplegable con mini-gráficas por
  métrica de las sesiones de la baja + Extra frente a su media de las 4 semanas previas, y
  tabla). En "Sesión", los lesionados y en readaptación salen en una tabla aparte debajo.
- Carga inicial (confirmada por el preparador): Anglada esguince grave 27/07–21/09; roturas de
  isquio de Andone 19/08, Payeras 25/08, Llinares 30/08–19/09, Bejarano 02/09; Fontanet fractura
  de nariz 17/09. El resto de ausencias largas fueron gestión de cargas.
