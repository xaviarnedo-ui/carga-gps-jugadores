"""REF_PARTIDO como media ponderada por minutos (pretemporada peso 1 + cada partido, peso min/T)."""
import json
import os
import shutil
import sys
import tempfile
import unittest

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline import config as C, partido, referencia, ref_componentes as RC  # noqa: E402


class Media(unittest.TestCase):
    def test_media_simple_y_filtros(self):
        c = {"pretemporada": {m: 100 for m in C.METRICS},
             "partidos": {"J2": {"fecha": "2026-09-13", "valores": {m: 200 for m in C.METRICS}},
                          "J3": {"fecha": "2026-09-20", "valores": {m: 600 for m in C.METRICS}}}}
        self.assertEqual(RC.ref_de(c)["distancia"], 300)                        # (100+200+600)/3
        self.assertEqual(RC.ref_de(c, antes_de="2026-09-20")["distancia"], 150)  # antes de J3
        self.assertEqual(RC.ref_de(c, sin="J2")["distancia"], 350)

    def test_ponderada_por_minutos(self):
        c = {"pretemporada": {m: 100 for m in C.METRICS},
             "partidos": {"J2": {"fecha": "2026-09-13", "minutos": 100, "duracion": 100,
                                 "valores": {m: 200 for m in C.METRICS}},
                          "J3": {"fecha": "2026-09-20", "minutos": 25, "duracion": 100,
                                 "valores": {m: 1000 for m in C.METRICS}},
                          "J4": {"fecha": "2026-09-27", "minutos": 110, "duracion": 100,
                                 "valores": {m: 300 for m in C.METRICS}}}}
        # (1·100 + 1·200 + 0,25·1000 + 1·300) / 3,25 — J4 no pesa más de 1 aunque M > T
        self.assertEqual(RC.ref_de(c)["distancia"], round(850 / 3.25, 1))


@unittest.skipUnless(os.path.exists(RC.RUTA) and os.path.exists(C.TIPO_XLSX), "faltan ficheros del club")
class Reproceso(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.rutas = (RC.RUTA, C.REF_LOG_JSON)
        RC.RUTA = shutil.copy(RC.RUTA, self.tmp)
        C.REF_LOG_JSON = os.path.join(self.tmp, "log.json")
        with open(C.REF_LOG_JSON, "w") as f:
            json.dump({}, f)

    def tearDown(self):
        RC.RUTA, C.REF_LOG_JSON = self.rutas
        shutil.rmtree(self.tmp)

    def test_reprocesar_no_cuenta_dos_veces(self):
        wt = openpyxl.load_workbook(C.TIPO_XLSX)       # en memoria: no se guarda
        antes = RC.n_datos(RC.cargar()["7"])
        datos = {7: {"distancia": 11000, "hmld": 1800, "hsr": 600, "sprint": 12, "acc": 30, "dec": 40,
                     "min": 95.0}}
        partido.actualizar_ref(wt, "J99", "2026-12-01", datos, {7: "Riera"}, 95.0)
        una = referencia.ref_partido(wt)[7]
        partido.actualizar_ref(wt, "J99", "2026-12-01", datos, {7: "Riera"}, 95.0)
        dos = referencia.ref_partido(wt)[7]
        self.assertEqual(una, dos)
        comp = RC.cargar()["7"]
        self.assertEqual(RC.n_datos(comp), antes + 1)    # los que ya tenía + J99 (una sola vez)


if __name__ == "__main__":
    unittest.main()
