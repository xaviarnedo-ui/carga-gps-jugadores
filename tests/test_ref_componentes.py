"""REF_PARTIDO como media simple de componentes (pretemporada = 1 dato + cada partido)."""
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
        datos = {7: {"distancia": 11000, "hmld": 1800, "hsr": 600, "sprint": 12, "acc": 30, "dec": 40,
                     "min": 95.0}}
        partido.actualizar_ref(wt, "J99", "2026-12-01", datos, {7: "Riera"}, 95.0)
        una = referencia.ref_partido(wt)[7]
        partido.actualizar_ref(wt, "J99", "2026-12-01", datos, {7: "Riera"}, 95.0)
        dos = referencia.ref_partido(wt)[7]
        self.assertEqual(una, dos)
        comp = RC.cargar()["7"]
        self.assertEqual(RC.n_datos(comp), 5)            # pretemporada + J2, J3, J4 + J99


if __name__ == "__main__":
    unittest.main()
