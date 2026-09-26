"""Hoja Acumulado: se recalcula entera desde las hojas de sesión (idempotente).

Obj  = suma de los Obj de las sesiones de la semana (sin el partido); vacío si no tiene ninguno.
Acum = suma de los Real de las sesiones ya cargadas + sesiones Extra. Para quien tiene Objetivo
       semanal solo cuenta desde su PRIMER día con objetivo de la semana (sesiones con objetivo +
       Extra desde ese día): la readaptación previa no se compara con un objetivo que no tenía
       (sí cuenta en su ACWR). Quien no tiene objetivo en toda la semana: todo, informativo.
Dif  = Acum − Obj.
Semáforo del Acumulado = vs el objetivo "a fecha" (Obj de las sesiones ya cargadas).
MEDIA EQUIPO = jugadores con Objetivo semanal (si aún no tienen real, cuenta 0).
"""
import re

from . import config as C
from . import sesion
from .xlsx import fecha_hoja, filas_jugadores, limpio, num, pinta, r1, semaforo, vaciar


def _extras(wb):
    return [wb[n] for n in wb.sheetnames if n.lower().startswith("extra") and n.endswith("_GPS")]


def recalcular(wb):
    ws = wb["Acumulado"]
    filas, fila_media = filas_jugadores(ws)
    ses = [(k, s, sesion.hecha(s), filas_jugadores(s)[0]) for k, s, _ in sesion.hojas_sesion(wb)]
    extras = [(e, filas_jugadores(e)[0]) for e in _extras(wb)]

    resumen, parciales = {}, []
    for dorsal, fila in filas.items():
        obj = {m: None for m in C.METRICS}
        obj_fecha = {m: None for m in C.METRICS}
        acum = {m: None for m in C.METRICS}

        def suma(dic, m, v):
            if v is not None:
                dic[m] = (dic[m] or 0) + v

        # primer día con objetivo de la semana (None si no tiene objetivo ningún día)
        desde = next((fecha_hoja(s) for _, s, _, fs in ses
                      if dorsal in fs and sesion.tiene_objetivo(s, fs[dorsal])), None)
        fuera = False
        for key, s, hecha, fs in ses:
            if dorsal not in fs:
                continue
            con_obj = sesion.tiene_objetivo(s, fs[dorsal])
            for m, c in C.SES_OBJ_COL.items():
                o = num(s.cell(fs[dorsal], c).value)
                suma(obj, m, o)
                if hecha:
                    suma(obj_fecha, m, o)
                real = num(s.cell(fs[dorsal], c + 1).value)
                if desde is None or con_obj:
                    suma(acum, m, real)
                elif real is not None:
                    fuera = True
        for e, fe in extras:
            if dorsal in fe:
                if desde is not None and fecha_hoja(e) < desde:
                    fuera = True
                    continue
                for m, c in C.MAT_COL.items():
                    suma(acum, m, num(e.cell(fe[dorsal], c).value))
        if fuera:
            parciales.append((ws.cell(fila, 2).value, desde))
        resumen[dorsal] = (obj, obj_fecha, acum)
        for m, c in C.SES_OBJ_COL.items():
            o, a = r1(obj[m]), acum[m]
            ws.cell(fila, c).value = limpio(o)
            ws.cell(fila, c + 1).value = limpio(r1(a))
            ws.cell(fila, c + 2).value = limpio(r1(a - o)) if o is not None and a is not None else None
            pinta(ws.cell(fila, c + 1), semaforo(a, obj_fecha[m]) if obj_fecha[m] else None)

    con_obj = [d for d, (o, _, _) in resumen.items() if any(v is not None for v in o.values())]
    for m, c in C.SES_OBJ_COL.items():
        if not con_obj:
            for k in range(3):
                vaciar(ws.cell(fila_media, c + k))
            continue
        n = len(con_obj)
        o = r1(sum(resumen[d][0][m] or 0 for d in con_obj) / n)
        of = sum(resumen[d][1][m] or 0 for d in con_obj) / n
        a = r1(sum(resumen[d][2][m] or 0 for d in con_obj) / n)
        ws.cell(fila_media, c).value = limpio(o)
        ws.cell(fila_media, c + 1).value = limpio(a)
        ws.cell(fila_media, c + 2).value = limpio(r1(a - o))
        pinta(ws.cell(fila_media, c + 1), semaforo(a, of) if of else None)

    # nota de quien vuelve a mitad de semana (fila media+3, se reescribe siempre)
    nota = ws.cell(fila_media + 3, 1)
    nota.value = (" ".join(f"{n}: acumulado desde su primer día con objetivo ({d:%d/%m}); su carga de "
                           f"readaptación anterior no se compara con el objetivo (sí cuenta en su ACWR)."
                           for n, d in parciales) or None)

    # cabecera: "... · S46, S47 CARGADAS"
    a3 = ws.cell(3, 1)
    cargadas = [k for k, _, hecha, _ in ses if hecha]
    if a3.value:
        base = re.sub(r"\s*·\s*[^·]*CARGAD[OA]S?\s*$", "", str(a3.value))
        a3.value = base + (f" · {', '.join(cargadas)} CARGADA{'S' if len(cargadas) > 1 else ''}"
                           if cargadas else "")
    return resumen
