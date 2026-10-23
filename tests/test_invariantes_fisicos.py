"""Primera ley e invariantes del Brayton de cp/gamma constantes; sin validación externa."""

import unittest

from viabilidad import calcular_dominios, evaluar_punto


class InvariantesFisicosTests(unittest.TestCase):
    # nombre, T1/T3 [K], gamma [-], cp [J/(kg K)], rp [-], p1 [kPa],
    # eta_c/eta_t [-], delta [-]; sólo el último caso no es motor.
    CASOS = (
        ("ideal", 288.15, 1600, 1.4, 1005, 10, 100, 1, 1, 0),
        ("noideal", 288.15, 1600, 1.4, 1005, 10, 100, .85, .9, .05),
        ("gamma_133", 300, 1200, 1.33, 1100, 6, 90, .9, .94, .03),
        ("caliente", 270, 1400, 1.36, 990, 14, 95, .88, .92, .07),
        ("no_motor", 288.15, 1600, 1.4, 1005, 200, 100, .85, .9, .05),
    )
    # Registros máximos de las comparaciones efectivamente ejecutadas.
    MEDIDAS = {}
    RTOL = 2e-12
    ATOL_ENERGIA = 1e-10  # kJ/kg
    ATOL_ESTADO = 1e-9    # K o kPa

    def _comparar(self, magnitud, obtenido, referencia, atol):
        """Contrasta escalares y registra errores (absolutos y relativos)."""
        error = abs(obtenido - referencia)
        relativo = error / abs(referencia) if referencia != 0 else None
        registro = type(self).MEDIDAS.setdefault(magnitud, {"abs": 0., "rel": None})
        registro["abs"] = max(registro["abs"], error)
        if relativo is not None:
            registro["rel"] = max(registro["rel"] or 0., relativo)
        self.assertLessEqual(error, atol + self.RTOL * abs(referencia),
                             f"{magnitud}: |error|={error:.5g}, relativo={relativo}")

    def _comprobar_balance(self, punto, cp):
        """Comprueba identidades a partir de los estados, incluso sin motor."""
        T1, T2, T3, T4 = punto["temperaturas"]
        wc = cp * (T2 - T1) / 1000
        wt = cp * (T3 - T4) / 1000
        qin = cp * (T3 - T2) / 1000
        qout = cp * (T4 - T1) / 1000  # No existe como campo público.
        for clave, esperado in (("trabajo_compresor", wc),
                                ("trabajo_turbina", wt),
                                ("trabajo_neto", wt - wc),
                                ("calor_aportado", qin)):
            self._comparar("energia_" + clave, punto[clave], esperado,
                          self.ATOL_ENERGIA)
        escala = max(1, *(abs(v) for v in (wc, wt, qin, qout)))
        for residuo in (punto["trabajo_neto"] - (wt - wc),
                        punto["trabajo_neto"] - (qin - qout),
                        (wt - wc) - (qin - qout)):
            self._comparar("residuo_primera_ley", residuo, 0,
                          self.ATOL_ENERGIA + self.RTOL * escala)
        return qout

    def test_primera_ley_con_referencias_noideales_independientes(self):
        for nombre, T1, T3, gamma, cp, rp, p1, ec, et, delta in self.CASOS:
            with self.subTest(caso=nombre):
                a = (gamma - 1) / gamma
                x = rp ** a
                expansion = rp * (1 - delta)
                T2_ref = T1 * (1 + (x - 1) / ec)
                T4_ref = T3 * (1 - et * (1 - expansion ** (-a)))
                punto = evaluar_punto(T1, T3, gamma, cp, rp, p1, ec, et, delta)
                for actual, esperado in zip(punto["temperaturas"],
                                            (T1, T2_ref, T3, T4_ref)):
                    self._comparar("temperatura", actual, esperado, self.ATOL_ESTADO)
                for actual, esperado in zip(punto["presiones"],
                                            (p1, p1 * rp, p1 * rp * (1-delta), p1)):
                    self._comparar("presion", actual, esperado, self.ATOL_ESTADO)
                referencias = {
                    "trabajo_compresor": cp * (T2_ref - T1) / 1000,
                    "trabajo_turbina": cp * (T3 - T4_ref) / 1000,
                    "calor_aportado": cp * (T3 - T2_ref) / 1000,
                }
                referencias["trabajo_neto"] = (referencias["trabajo_turbina"]
                                               - referencias["trabajo_compresor"])
                for clave, esperado in referencias.items():
                    self._comparar("referencia_" + clave, punto[clave], esperado,
                                  self.ATOL_ENERGIA)
                qout = self._comprobar_balance(punto, cp)
                self._comparar("referencia_qout", qout, cp * (T4_ref - T1) / 1000,
                              self.ATOL_ENERGIA)
                self.assertEqual(punto["viable"], nombre != "no_motor")

    def test_irreversibilidades_aisladas_reducen_trabajo(self):
        T1, T3, gamma, cp, rp, p1 = 288.15, 1600, 1.4, 1005, 10, 100
        ec, et, delta = .95, .98, .01
        base = evaluar_punto(T1, T3, gamma, cp, rp, p1, ec, et, delta)
        cambios = (
            ("compresor", .8, et, delta),
            ("turbina", ec, .82, delta),
            ("perdida", ec, et, .12),
        )
        for nombre, ec_n, et_n, delta_n in cambios:
            with self.subTest(cambio=nombre):
                punto = evaluar_punto(T1, T3, gamma, cp, rp, p1, ec_n, et_n, delta_n)
                self.assertLess(punto["trabajo_neto"], base["trabajo_neto"])
                if nombre == "compresor":
                    self.assertGreater(punto["temperaturas"][1], base["temperaturas"][1])
                    self.assertGreater(punto["trabajo_compresor"], base["trabajo_compresor"])
                    self._comparar("turbina_fija", punto["trabajo_turbina"],
                                  base["trabajo_turbina"], self.ATOL_ENERGIA)
                else:
                    self.assertGreater(punto["temperaturas"][3], base["temperaturas"][3])
                    self.assertLess(punto["trabajo_turbina"], base["trabajo_turbina"])
                    self._comparar("compresor_fijo", punto["trabajo_compresor"],
                                  base["trabajo_compresor"], self.ATOL_ENERGIA)
                    if nombre == "perdida":
                        self.assertLess(punto["presiones"][2] / p1,
                                        base["presiones"][2] / p1)
                self._comprobar_balance(punto, cp)
                self.assertEqual(punto["rendimiento"] is not None, punto["viable"])

    def test_limite_reversible_converge_al_ideal(self):
        T1, T3, gamma, cp, rp, p1 = 288.15, 1600, 1.4, 1005, 10, 100
        ideal = evaluar_punto(T1, T3, gamma, cp, rp, p1)
        errores_anteriores = None
        for epsilon in (.1, .01, .001, .00001):
            with self.subTest(epsilon=epsilon):
                punto = evaluar_punto(T1, T3, gamma, cp, rp, p1,
                                      1-epsilon, 1-epsilon, epsilon)
                self.assertTrue(punto["viable"])
                errores = tuple(abs(punto[clave] - ideal[clave]) for clave in
                                ("trabajo_compresor", "trabajo_turbina",
                                 "trabajo_neto", "calor_aportado", "rendimiento"))
                if errores_anteriores is not None:
                    for error, anterior in zip(errores, errores_anteriores):
                        self.assertLess(error, anterior)
                errores_anteriores = errores
                self._comprobar_balance(punto, cp)
        self.assertLess(errores_anteriores[2], .02)  # kJ/kg, último epsilon=1e-5.

    def test_escalado_cp_sin_cambio_de_temperaturas_ni_rendimiento(self):
        for nombre, *parametros in self.CASOS[:2]:
            with self.subTest(caso=nombre):
                T1, T3, gamma, cp, rp, p1, ec, et, delta = parametros
                base = evaluar_punto(*parametros)
                qout_base = self._comprobar_balance(base, cp)
                for factor in (.6, 1.5, 2.3):
                    with self.subTest(factor_cp=factor):
                        punto = evaluar_punto(T1, T3, gamma, cp*factor, rp, p1,
                                              ec, et, delta)
                        self.assertEqual(punto["temperaturas"], base["temperaturas"])
                        self.assertEqual(punto["presiones"], base["presiones"])
                        for clave in ("trabajo_compresor", "trabajo_turbina",
                                      "trabajo_neto", "calor_aportado"):
                            self._comparar("escala_cp_" + clave, punto[clave],
                                          factor * base[clave], self.ATOL_ENERGIA)
                        qout = self._comprobar_balance(punto, cp*factor)
                        self._comparar("escala_cp_qout", qout, factor*qout_base,
                                      self.ATOL_ENERGIA)
                        self.assertTrue(punto["viable"])
                        self._comparar("escala_cp_eta", punto["rendimiento"],
                                      base["rendimiento"], 1e-12)

    def test_escalado_p1_sin_cambio_de_energias(self):
        for nombre, *parametros in self.CASOS[:2]:
            with self.subTest(caso=nombre):
                T1, T3, gamma, cp, rp, p1, ec, et, delta = parametros
                base = evaluar_punto(*parametros)
                for factor in (.5, 1.7, 3):
                    with self.subTest(factor_p1=factor):
                        punto = evaluar_punto(T1, T3, gamma, cp, rp, p1*factor,
                                              ec, et, delta)
                        for actual, esperado in zip(punto["presiones"], base["presiones"]):
                            self._comparar("escala_p1_presion", actual, factor*esperado,
                                          self.ATOL_ESTADO)
                        for actual, esperado in zip(punto["temperaturas"],
                                                    base["temperaturas"]):
                            self._comparar("escala_p1_temperatura", actual, esperado,
                                          self.ATOL_ESTADO)
                        for clave in ("trabajo_compresor", "trabajo_turbina",
                                      "trabajo_neto", "calor_aportado", "rendimiento"):
                            self._comparar("escala_p1_" + clave, punto[clave],
                                          base[clave], self.ATOL_ENERGIA)
                        self.assertTrue(punto["viable"])

    def test_no_motores_conservan_balance_y_motivos(self):
        casos = (
            ("sin_compresion", (288.15, 1600, 1.4, 1005, 1, 100, 1, 1, 0),
             ("compresion", "expansion")),
            ("sin_expansion", (288.15, 1600, 1.4, 1005, 1.03, 100, .85, .9, .05),
             ("expansion",)),
            ("sin_calor", (288.15, 1600, 1.4, 1005, 500, 100, 1, 1, 0),
             ("calor_aportado",)),
            ("sin_trabajo", (288.15, 1600, 1.4, 1005, 200, 100, .85, .9, .05),
             ("trabajo_neto",)),
            ("dominio_vacio", (300, 400, 1.4, 1005, 4, 100, .85, .9, .5),
             ("trabajo_neto",)),
        )
        for nombre, parametros, motivos_esperados in casos:
            with self.subTest(caso=nombre):
                punto = evaluar_punto(*parametros)
                self.assertFalse(punto["viable"])
                self.assertIsNone(punto["rendimiento"])
                self.assertIsNone(punto["back_work_ratio"])
                self.assertTrue(set(motivos_esperados).issubset(punto["motivos"]))
                for motivo in punto["motivos"]:
                    self.assertLessEqual(punto["margenes"][motivo],
                                         punto["tolerancias"][motivo])
                self._comprobar_balance(punto, parametros[3])
        params = (288.15, 1600, 1.4, 1005, 100, .85, .9, .05)
        intervalo = calcular_dominios(*params)["noideal"]["intervalo"]
        self.assertTrue(intervalo)
        vacio = (300, 400, 1.4, 1005, 100, .85, .9, .5)
        self.assertEqual(calcular_dominios(*vacio)["noideal"]["intervalo"], ())
        limite_alto = intervalo[1]
        for distancia, admitido in ((1e-9, True), (1e-12, False)):
            with self.subTest(banda=distancia):
                rp = limite_alto * (1 - distancia)
                punto = evaluar_punto(params[0], params[1], params[2], params[3], rp,
                                      params[4], *params[5:])
                fisico = evaluar_punto(params[0], params[1], params[2], params[3], rp,
                                       params[4], *params[5:], tolerancia=0)
                self.assertTrue(fisico["viable"])
                self.assertEqual(punto["viable"], admitido)
                self.assertEqual(punto["rendimiento"] is not None, admitido)
                if not admitido:
                    self.assertIn("trabajo_neto", punto["fronteras"])
                    self.assertGreater(punto["margenes"]["trabajo_neto"], 0)
                self._comprobar_balance(punto, params[3])


if __name__ == "__main__":
    unittest.main()
