# Carga GPS · AT Baleares 26-27

App móvil (PWA, sin backend) para ver la carga GPS del equipo. HTML + CSS + JS
vanilla. Se aloja como sitio estático (GitHub Pages). Sin login: cada jugador
recibe su enlace `jugador.html?j=<dorsal>`.

## Dos versiones

| Versión | Archivo | Para quién |
|---|---|---|
| **Entrenador** | `index.html` | Preparador físico. 5 pestañas: Inicio, Sesión, Microciclo, Carga A:C, Partidos. Selector de microciclo arriba. |
| **Jugador** | `jugador.html?j=<dorsal>` | Cada jugador. Solo sus datos + la media del equipo. 5 pestañas: Sesión, Microciclo, Carga A:C, Perfil, Historial. |

El dorsal se guarda en `localStorage` al abrir el enlace la primera vez, así que
al añadir la app a la pantalla de inicio sigue sabiendo quién es. Abrir
`jugador.html` sin `?j=` muestra un selector de prueba.

### Vista entrenador
- **Inicio** — estado del microciclo; **avisos destacados** (récords de Vel. máx, desviaciones ±50% del objetivo, volumen bajo del microciclo); avisos de carga ACWR; reparto de semáforo de la última sesión; y **Top 5 por parámetro** de la última sesión y del microciclo.
- **Sesión** — media del equipo (6 métricas + Vel. máx, Player Load y duración) y, debajo, cada jugador con un **minicírculo** del % medio conseguido (color de semáforo); al desplegar, su real / objetivo individual / media equipo.
- **Microciclo** — lo mismo pero con el acumulado de sesiones del microciclo.
- **Carga A:C** — ACWR del equipo + gráfica de 28 días de la media del equipo; debajo cada jugador con su gráfica individual en un desplegable.
- **Partidos** — telaraña de la media del equipo (REF_PARTIDO); seleccionas jugadores (hasta 5) y se superponen sus perfiles para compararlos, con tabla numérica.


## Datos: de dónde salen

Los datos **NO se editan a mano**. Se importan de los Excel reales:

```
~/Desktop/AT BALEARES 26-27/GPS/
├── Microciclo_Tipo.xlsx            (coeficientes Tipo A/B/C · REF_PARTIDO)
└── Microciclos/Microciclo 1-7.xlsx (hojas Sxx_GPS, PTx_GPS, Acumulado, CARGA_AC)
```

```bash
cd ~/Desktop/carga-gps && python3 import_data.py
```

`import_data.py` lee esos Excel y regenera `data.js`. **La app solo muestra lo
que hay en el Excel** (obj / real / dif / ACWR / medias). El importador calcula:
el acumulado *real* solo-sesiones, la serie diaria de Player Load de 28 días, y
la media de equipo de Vel. máx / Player Load / duración por sesión.

Estado actual: **M1–M6 cerrados, M7 en curso**. El microciclo con el número más
alto es siempre el "activo"; el resto, historial. 20 jugadores, grupos DEF/MED/DEL.

## Publicar (una vez)

```bash
cd ~/Desktop/carga-gps
gh repo create carga-gps-jugadores --public --source=. --remote=origin --push
gh api -X POST repos/xaviarnedo-ui/carga-gps-jugadores/pages -f build_type=legacy -f 'source[branch]=main' -f 'source[path]=/'
```

URL: `https://xaviarnedo-ui.github.io/carga-gps-jugadores/`
- Jugador dorsal 8 → `…/jugador.html?j=8`
- Entrenador → `…/index.html`

## Actualizar (cada Excel nuevo)

```bash
cd ~/Desktop/carga-gps && python3 import_data.py && git commit -am "datos" && git push
```

GitHub Pages se actualiza solo en ~1 min. Si tocas `styles.css` / `*.js`, sube
también `?v=N` en `index.html`/`jugador.html` y el `CACHE` de `sw.js`.

Para avisar a los jugadores suscritos de que hay datos nuevos, añade `--avisar`:

```bash
cd ~/Desktop/carga-gps && python3 import_data.py --avisar && git commit -am "datos" && git push
```

## Notificaciones push (avisos de datos nuevos)

Cada persona (jugador o cuerpo técnico) activa el aviso con la campana de la barra
superior, en su vista — necesita tener la app **añadida a la pantalla de inicio**
en iPhone (iOS 16.4+); en Android va también desde el navegador. `import_data.py
--avisar` manda entonces una notificación «Datos de GPS actualizados» a todos los
suscritos. Las suscripciones del cuerpo técnico se guardan con `dorsal` nulo.

Usa el mismo proyecto Supabase que la app de hábitos. **Montaje (una vez):**

1. SQL Editor de Supabase → ejecuta `supabase-gps-notificaciones.sql` (crea `gps_push_subs`).
2. Edge Functions → *Create function* `gps-notify` → pega `supabase-edge-function-gps-notify.ts`.
3. En los *Secrets* de esa función añade `GPS_NOTIFY_SECRET` (mismo valor que en tu `.env`
   local; copia `.env.example` a `.env`). `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` ya existen.

No hay cron: la función solo se dispara cuando ejecutas `--avisar`.

## Previsualizar en local

```bash
cd ~/Desktop/carga-gps && python3 -m http.server 4599
```

- Entrenador → `http://localhost:4599/index.html`
- Jugador (dorsal 8) → `http://localhost:4599/jugador.html?j=8`

## Estructura de archivos

| Archivo | Qué es |
|---|---|
| `index.html` + `app.js` | Versión **entrenador** |
| `jugador.html` + `jugador.js` | Versión **jugador** |
| `styles.css` | Sistema visual (variables CSS, claro/oscuro), compartido |
| `data.js` | **Los datos** (~1 MB). `window.GPS_DATA_ALL = { meta, refPartido, coeficientes, microciclos, M1..M7 }` |
| `import_data.py` | Lee los Excel → genera `data.js` |
| `manifest.json` / `manifest.jugador.json` + `icons/` | PWA (incluye `icons/escudo.png`) |
| `fotos/<dorsal>.png` | Foto de cada jugador (240 px, recortadas de las fichas 4K de `~/Desktop/AT BALEARES 26-27/Fotos jugadores/`) |
| `sw.js` | Cache offline + notificaciones push |
| `supabase-gps-notificaciones.sql` + `supabase-edge-function-gps-notify.ts` | Backend de las notificaciones (Supabase) |
| `.env.example` | Plantilla para `.env` (no se sube): claves para `import_data.py --avisar` |
| `gen_data.py`, `gen_icons.py` | Generador de datos de ejemplo (histórico) e iconos |

## Estructura de `data.js`

```js
M6: {
  meta: { n, titulo, tipo:"B", semana, calculoFecha, calculoISO, estado:"activo" },
  orden: [ {tipo:"sesion", key:"S22"}, ..., {tipo:"partido", key:"PT7"}, ... ],  // cronológico
  sesiones: { S22: { date, role, tipo, nota, players:[{dorsal,jugador,grupo,
                     distancia:{obj,real,dif}, ..., velMax, playerLoad, duracion, estado}],
                     teamAvg:{...} }, ... },
  partidos: { PT7: { date, role:"Partido", rival, nota, players:[{... distancia:{obj:null,real,dif:null} ...}], teamAvg } },
  cargasObjetivo: { players, teamAvg, nota },   // SOLO sesiones de entrenamiento
  cargasSemana:   { players, teamAvg, nota },   // sesiones + partido(s)  (hoja "Acumulado" del Excel)
  cargaAC: { players:[{dorsal, acwr, cargaAguda, cargaCronica, plS22.., plPT7..,
                       serie:{pl,aguda,cronica,acwr,ses} }],   // serie (28 d) en TODOS los microciclos
             teamAvg, nota, serieDias:[...28 fechas...] }        // (ventana que acaba en su fecha de cálculo)
}
```

## Pantallas — jugador

1. **Sesión** — sus 6 métricas (tú / objetivo / media equipo) con semáforo, V.máx, Player Load, duración y la nota del día. Un partido no lleva objetivo: se compara con la media del equipo.
2. **Microciclo** — objetivo acumulado de **solo las sesiones de entrenamiento** (el partido no cuenta) frente a lo realizado.
3. **Carga A:C** — su ACWR de hoy, carga aguda / crónica (con la media del equipo al lado) y la gráfica de los **últimos 28 días**: Player Load por día, línea de carga aguda (media 7 d), línea de crónica (media 28 d) y el ACWR de cada día.
4. **Perfil** — telaraña de su REF_PARTIDO (Distancia, HMLD, HSR, Sprints, ACC, DEC, Vel. máx) frente a la media del equipo + tabla numérica.
5. **Historial** — todos los microciclos (ninguno desplegado por defecto). Cada uno con un
   **círculo de cumplimiento** (% del objetivo de sesiones, coloreado por semáforo) en la
   cabecera. Al desplegar: ACWR al cierre, PL total de la semana, y por métrica lo realizado
   en las **sesiones vs su objetivo** (con color de semáforo) y **lo realizado en el partido**
   de esa semana; más una gráfica **solo de los días de ese microciclo** (cabe entera sin scroll)
   con las columnas de Player Load coloreadas por el semáforo de esa sesión (partidos en gris),
   el **ACWR integrado** como línea + puntos sobre un eje a la derecha, y debajo el tipo de sesión
   (MD-4, MD-3, …) y la fecha.

## Semáforo (métricas con objetivo)

| Color | Regla |
|---|---|
| 🔵 Azul | real < −10 % (corto) |
| 🟢 Verde | dentro de ±10 % (cumplido) |
| 🟠 Naranja | +10 % a +20 % (pasado) |
| 🔴 Rojo | > +20 % (muy pasado) |

## ACWR (carga aguda / crónica)

- **Aguda** = Σ Player Load de los últimos 7 días naturales ÷ 7 (los descansos cuentan como 0).
- **Crónica** = Σ de los últimos 28 días ÷ 28.
- **ACWR** = aguda ÷ crónica.
- Zonas: 🔵 < 0,80 infracarga · 🟢 0,80–1,30 óptima · 🟠 1,31–1,50 precaución · 🔴 > 1,50 riesgo.
- Al principio de temporada (M1–M2) el ACWR sale disparado (crónica aún casi vacía): no es fiable hasta que hay ~4 semanas de datos.

## Notas sobre los datos reales

- La metodología del preparador ha ido cambiando entre microciclos (objetivos primero
  uniformes y luego individuales; semáforo primero de 3 colores y luego de 4;
  REF_PARTIDO primero "el más alto por parámetro" y luego "la media de los partidos").
  La app aplica de forma uniforme el criterio más reciente para el color, pero los
  números (obj / real / dif) son siempre los que trae cada Excel.
- **PT4** (Playas Calvià) está anulado como referencia de partido; su Player Load sí
  cuenta para el ACWR.
- Sin datos de un jugador en una sesión/partido → `estado: "na"` (no participó).
