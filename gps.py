#!/usr/bin/env python3
"""Pipeline GPS: PDF de Catapult → Excel de microciclo → Disponibilidad → app + dashboard.

  python3 gps.py leer S47.pdf [Rehab.pdf]            resumen para decidir estados (no escribe nada)
  python3 gps.py procesar S47.pdf [Rehab.pdf] [opciones]
        --estado 6=descanso --estado 26=rehab    estado del día (full/rehab/lesion/descanso/nc/noconv)
        --fallo-gps 14=50                         partido: GPS roto, 50' jugados → estimado desde REF
        --proxy 19=17                             GPS roto: copia los datos del 17 al 19 (dato proxy)
        --descartar 11                            ignora la fila de ese dorsal del PDF (no son minutos jugados)
        --extra --solo 26 [--ref-duracion 95]     Extra con solo esos dorsales (p. ej. partido con el filial);
                                                  --ref-duracion: cuenta para su REF_PARTIDO con esa duración
        --rol 16=S                                MD+1: titular (T) / suplente (S) si vuelve ese día
        --lesion 26="Fractura de nariz"           tipo de una lesión NUEVA (abre la baja ese día)
        --alias "NOMBRE APELLIDO=dorsal"          nombre del PDF que no cruza con la plantilla
        --extra                                   sesión fuera de calendario (hoja Extra_dd-mm)
        --nota "texto"                            nota adicional en la hoja
        --prueba                                  escribe en GPS/_prueba/, no toca nada real
        --publicar [--sin-avisar]                 import_data + git push (+ aviso a jugadores)
  python3 gps.py abrir --tipo B --partido J5 --rival "Rival" --lunes 2026-09-28
  python3 gps.py tipo 12 A                            cambia el Tipo de un microciclo y recalcula objetivos
  python3 gps.py estado [4=lesion ...] [--desde F --nota T]  ver / fijar estado vigente (+ ajusta objetivos pendientes)
  python3 gps.py lesiones [--abrir D --tipo T --baja F | --cerrar D --alta F]   registro de lesiones
  python3 gps.py disponibilidad                       regenerar Disponibilidad y Minutos.xlsx
  python3 gps.py publicar [--sin-avisar] [-m msg]     import_data + git push (+ aviso)
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys

from pipeline import config as C
from pipeline import disponibilidad, estados as E, lesiones as L, microciclo, procesar as P

PNG_DIR = os.path.join(C.GPS_DIR, "_prueba", "resumen_png")


def _pares(lista, conv=str):
    out = {}
    for item in lista or []:
        k, v = item.rsplit("=", 1)
        out[k.strip()] = conv(v.strip())
    return out


def _publicar(mensaje, avisar):
    print(P.importar(avisar=False).strip().splitlines()[0])
    print(P.publicar(mensaje))
    if avisar:
        out = subprocess.run(["python3", "import_data.py", "--solo-avisar"], cwd=C.REPO_DIR,
                             capture_output=True, text=True)
        print(out.stdout.strip() or out.stderr.strip())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("leer")
    a.add_argument("pdfs", nargs="+")
    a = sub.add_parser("procesar")
    a.add_argument("pdfs", nargs="+")
    a.add_argument("--estado", action="append")
    a.add_argument("--fallo-gps", action="append")
    a.add_argument("--rol", action="append")
    a.add_argument("--lesion", action="append")
    a.add_argument("--proxy", action="append")
    a.add_argument("--descartar", type=int, action="append")
    a.add_argument("--solo", type=int, action="append")
    a.add_argument("--ref-duracion", type=float)
    a.add_argument("--alias", action="append")
    a.add_argument("--extra", action="store_true")
    a.add_argument("--nota", default="")
    a.add_argument("--prueba", action="store_true")
    a.add_argument("--publicar", action="store_true")
    a.add_argument("--sin-avisar", action="store_true")
    a = sub.add_parser("abrir")
    a.add_argument("--tipo", required=True)
    a.add_argument("--partido", required=True)
    a.add_argument("--rival", required=True)
    a.add_argument("--lunes", required=True)
    a = sub.add_parser("tipo")
    a.add_argument("n", type=int)
    a.add_argument("tipo")
    a = sub.add_parser("lesiones")
    a.add_argument("--abrir", type=int)
    a.add_argument("--cerrar", type=int)
    a.add_argument("--tipo")
    a.add_argument("--baja")
    a.add_argument("--alta")
    a = sub.add_parser("estado")
    a.add_argument("cambios", nargs="*")
    a.add_argument("--desde", help="fecha AAAA-MM-DD del cambio (por defecto hoy)")
    a.add_argument("--fuera-media", help="dorsales (7,18) con objetivo individual que no cuentan "
                                         "para la MEDIA EQUIPO entre --desde y --hasta")
    a.add_argument("--hasta", help="fecha AAAA-MM-DD (con --fuera-media)")
    a.add_argument("--nota", default="fijado a mano")
    sub.add_parser("disponibilidad")
    a = sub.add_parser("publicar")
    a.add_argument("--sin-avisar", action="store_true")
    a.add_argument("-m", default="Datos GPS actualizados")
    args = ap.parse_args()

    if args.cmd == "leer":
        print(P.leer(args.pdfs, PNG_DIR))

    elif args.cmd == "procesar":
        est = {int(k): v for k, v in _pares(args.estado).items()}
        malos = {k: v for k, v in est.items() if v not in C.ESTADOS}
        if malos:
            sys.exit(f"Estados no válidos: {malos} (válidos: {', '.join(C.ESTADOS)})")
        try:
            res = P.procesar(args.pdfs, override=est,
                             fallos_gps={int(k): float(v) for k, v in _pares(args.fallo_gps).items()},
                             rol_md1={int(k): v.upper() for k, v in _pares(args.rol).items()},
                             alias={k: int(v) for k, v in _pares(args.alias).items()},
                             proxies={int(k): int(v) for k, v in _pares(args.proxy).items()},
                             descartar=args.descartar, solo=args.solo, ref_duracion=args.ref_duracion,
                             tipos_lesion={int(k): v.strip('"') for k, v in _pares(args.lesion).items()},
                             nota=args.nota, extra=args.extra, dry_run=args.prueba)
        except P.NecesitaDecision as e:
            print("NECESITO UNA DECISIÓN (no se ha escrito nada):\n" + str(e))
            sys.exit(2)
        print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
        if not args.prueba:
            print(P.importar(avisar=False).strip())
            if args.publicar:
                _publicar(f"Datos GPS: {res['key']}", avisar=not args.sin_avisar)

    elif args.cmd == "abrir":
        destino, claves, (pk, pf), roles = microciclo.abrir(
            args.tipo.upper(), args.partido.upper(), args.rival, dt.date.fromisoformat(args.lunes))
        print(f"Creado {destino}")
        for k, dia, f in claves:
            print(f"  {k} {dia} {f:%a %d/%m}")
        print(f"  {pk} {pf:%a %d/%m}")
        print("  Titulares MD+1:", sorted(d for d, r in roles.items() if r == "T"))
        disponibilidad.generar()

    elif args.cmd == "estado":
        data = E.cargar()
        desde = args.desde or dt.date.today().isoformat()
        if args.fuera_media:
            if not args.hasta:
                sys.exit("--fuera-media necesita --hasta")
            dors = [int(x) for x in args.fuera_media.split(",")]
            fm = data.setdefault("fuera_media", [])
            fm[:] = [x for x in fm if not (x["dorsal"] in dors and x["desde"] == desde)]
            fm.extend({"dorsal": d, "desde": desde, "hasta": args.hasta, "nota": args.nota} for d in dors)
            E.guardar(data)
            n, _ = P.localizar_por_fecha(dt.date.fromisoformat(desde))
            tocadas = microciclo.propagar_estados(n, dors, data)
            print(f"  Fuera de la media {desde}→{args.hasta}: {dors} · Microciclo {n}: {', '.join(tocadas)}")
        cambios = _pares(args.cambios)
        for k, v in cambios.items():
            if v not in E.PERSISTENTES:
                sys.exit(f"Estado vigente solo puede ser {E.PERSISTENTES}")
            E.cambiar(data, int(k), v, desde, args.nota)
        if cambios:
            E.guardar(data)
            n, _ = P.localizar_por_fecha(dt.date.today())
            tocadas = microciclo.propagar_estados(n, [int(k) for k in cambios], data)
            print(f"  Microciclo {n}: objetivos ajustados en {', '.join(tocadas) or 'ninguna sesión'}")
        for d, info in sorted(data["vigente"].items(), key=lambda t: int(t[0])):
            if info["estado"] != C.FULL:
                print(f"  {d:>3} {info['estado']:7} desde {info['desde']}  {info.get('nota', '')}")
        print("  (el resto: full)")

    elif args.cmd == "tipo":
        for key, dia, k in microciclo.cambiar_tipo(args.n, args.tipo.upper()):
            print(f"  {key} {dia}: {k} objetivos recalculados")
        print(P.importar(avisar=False).strip().splitlines()[0])

    elif args.cmd == "lesiones":
        lst = L.cargar()
        if args.abrir:
            L.abrir(lst, args.abrir, args.tipo, args.baja)
            L.guardar(lst)
        elif args.cerrar:
            L.cerrar(lst, args.cerrar, args.alta)
            L.guardar(lst)
        for l in lst:
            print(f"  #{l['dorsal']:<3} {l['tipo']:22} baja {l['baja']}  alta {l['alta'] or 'ABIERTA'}")

    elif args.cmd == "disponibilidad":
        print(disponibilidad.generar())

    elif args.cmd == "publicar":
        _publicar(args.m, avisar=not args.sin_avisar)


if __name__ == "__main__":
    main()
