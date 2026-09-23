"""Regresión de hojas de partido: J3 (con fallo de GPS de Hernández) y J2."""
import os
import sys
import unittest

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline import config as C, informe, partido, referencia  # noqa: E402
from pipeline.pdf_catapult import dur_a_min  # noqa: E402
from pipeline.xlsx import filas_jugadores, plantilla_de, vaciar  # noqa: E402

BASE = os.path.dirname(C.GPS_DIR)


def snapshot(ws, ignorar=()):
    filas, media = filas_jugadores(ws)
    out = {}
    for r in list(filas.values()) + [media]:
        for c in range(4, 13):
            if (r, c) in ignorar:
                continue
            v = ws.cell(r, c).value
            if c == C.MAT_DUR and v:
                v = dur_a_min(v)                       # J2 guardaba H:MM:SS
            if r == media and isinstance(v, float) and c != C.MAT_VMAX:
                v = round(v, 1)                        # J2 guardaba la media con 2 decimales
            out[(r, c)] = v
    return out


class RegresionPartido(unittest.TestCase):
    def caso(self, n, key, pdf, fallos=None):
        ruta = os.path.join(C.MICRO_DIR, f"Microciclo {n}.xlsx")
        if not (os.path.exists(ruta) and os.path.exists(pdf)):
            self.skipTest("faltan ficheros del club")
        wb = openpyxl.load_workbook(ruta)
        ws = wb[f"{key}_GPS"]
        filas, media = filas_jugadores(ws)
        # Vel. máx / PL del jugador con GPS roto no son reproducibles (se pusieron a mano),
        # y por tanto tampoco la media de esas dos columnas
        ignorar = {(r, c) for r in [filas[d] for d in (fallos or {})] + ([media] if fallos else [])
                   for c in (C.MAT_VMAX, C.MAT_PL)}
        antes = snapshot(ws, ignorar)
        nombres, _ = plantilla_de(ws)
        datos, sin = informe.datos_por_dorsal(informe.leer(pdf), nombres)
        self.assertEqual(sin, [])
        ref = referencia.ref_partido(openpyxl.load_workbook(C.TIPO_XLSX))
        for d, mins in (fallos or {}).items():
            datos[d] = partido.estimar_por_fallo(ref[d], mins, partido.pl_por_metro(datos))
        for r in filas.values():
            for c in range(4, 13):
                vaciar(ws.cell(r, c))
        partido.rellenar(ws, datos)
        despues = snapshot(ws, ignorar)
        difs = [(k, antes[k], despues[k]) for k in antes if antes[k] != despues[k]]
        self.assertEqual(difs, [], difs[:10])

    def test_j3_con_fallo_gps(self):
        self.caso(10, "J3", os.path.join(BASE, "J3 UCAM.pdf"), fallos={14: 50})

    def test_j2(self):
        self.caso(9, "J2", os.path.join(C.GPS_DIR, "Partidos", "J2 INTERCITY.pdf"))


class Formulas(unittest.TestCase):
    def test_fatiga(self):
        self.assertEqual(referencia.estimar_95(1000, 95), 1000)
        self.assertEqual(referencia.estimar_95(1000, 100), 1000)
        self.assertAlmostEqual(referencia.estimar_95(5000, 50), 5000 + 45 * 100 * 0.9)

    def test_inversa_es_inversa(self):
        for mins in (20, 50, 80):
            est = referencia.estimar_95(4321, mins)
            self.assertAlmostEqual(referencia.real_desde_ref(est, mins), 4321)


if __name__ == "__main__":
    unittest.main()
