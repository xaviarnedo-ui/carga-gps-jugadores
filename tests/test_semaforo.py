"""Semáforo con tolerancia por métrica (decisión del 27/10/2026)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline import config as C  # noqa: E402
from pipeline.xlsx import semaforo  # noqa: E402


class Tolerancias(unittest.TestCase):
    def test_distancia_10(self):
        self.assertEqual(semaforo(1095, 1000, "distancia"), C.VERDE)
        self.assertEqual(semaforo(880, 1000, "distancia"), C.AZUL)
        self.assertEqual(semaforo(1150, 1000, "distancia"), C.NARANJA)
        self.assertEqual(semaforo(1250, 1000, "distancia"), C.ROJO)

    def test_hsr_acc_dec_20(self):
        self.assertEqual(semaforo(118, 100, "hsr"), C.VERDE)
        self.assertEqual(semaforo(82, 100, "acc"), C.VERDE)
        self.assertEqual(semaforo(79, 100, "dec"), C.AZUL)
        self.assertEqual(semaforo(135, 100, "hsr"), C.NARANJA)
        self.assertEqual(semaforo(141, 100, "hsr"), C.ROJO)

    def test_sprint_absoluto(self):
        self.assertEqual(semaforo(3, 1.5, "sprint"), C.VERDE)      # +1,5 sprints: en zona
        self.assertEqual(semaforo(0, 2.5, "sprint"), C.AZUL)       # −2,5: por debajo
        self.assertEqual(semaforo(5, 1.5, "sprint"), C.NARANJA)    # +3,5
        self.assertEqual(semaforo(7, 1.5, "sprint"), C.ROJO)       # +5,5


if __name__ == "__main__":
    unittest.main()
