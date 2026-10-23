"""Verificación analítica del Brayton ideal; no validación experimental."""

from math import sqrt
import unittest

import main
from optimizacion import buscar_maximo_numerico
from viabilidad import calcular_dominios, evaluar_punto


class VerificacionAnaliticaIdealTests(unittest.TestCase):
    # Nombre, T1 [K], T3 [K], gamma [-], cp [J/(kg K)], rp [-], p1 [kPa].
    # Casos interiores moderados: la tarea no estudia fronteras ni condicionamiento.
    CASOS = (
        ("referencia", 288.15, 1600, 1.4, 1005, 10, 100),
        ("gamma_133", 300, 1200, 1.33, 1100, 6, 90),
        ("entrada_fria", 260, 1450, 1.36, 1010, 12, 85),
        ("turbina_caliente", 320, 1900, 1.4, 1040, 22, 120),
        ("rp_moderada", 290, 1000, 1.3, 980, 3.5, 105),
    )

    # rtol no expresa incertidumbre del gas: acota redondeos double ordinarios.
    RTOL = 2e-12
    ATOL_T = 1e-9  # K
    ATOL_E = 1e-10  # kJ/kg
    ATOL_ETA = 2e-13  # fracción adimensional

    def test_estados_con_referencias_isentropicas(self):
        for nombre, T1, T3, gamma, cp, rp, p1 in self.CASOS:
            with self.subTest(caso=nombre):
                a = (gamma - 1) / gamma
                esperadas = (T1, T1 * rp**a, T3, T3 / rp**a)
                ciclo = main.calcular_ciclo_ideal(T1, T3, gamma, cp, rp, p1)
                for indice, (actual, esperado) in enumerate(zip(ciclo["temperaturas"], esperadas), 1):
                    error = abs(actual - esperado)
                    tolerancia = self.ATOL_T + self.RTOL * abs(esperado)
                    self.assertLessEqual(error, tolerancia,
                                         f"{nombre}, T{indice}: error {error:.3g} K; "
                                         f"tolerancia {tolerancia:.3g} K")
                self.assertLessEqual(abs(ciclo["T2s"] - esperadas[1]),
                                     self.ATOL_T + self.RTOL * esperadas[1])
                self.assertLessEqual(abs(ciclo["T4s"] - esperadas[3]),
                                     self.ATOL_T + self.RTOL * esperadas[3])

    def test_balances_con_referencias_y_residuo(self):
        for nombre, T1, T3, gamma, cp, rp, p1 in self.CASOS:
            with self.subTest(caso=nombre):
                a = (gamma - 1) / gamma
                T2_ref, T4_ref = T1 * rp**a, T3 / rp**a
                wc_ref = cp * (T2_ref - T1) / 1000
                wt_ref = cp * (T3 - T4_ref) / 1000
                qin_ref = cp * (T3 - T2_ref) / 1000
                qout_ref = cp * (T4_ref - T1) / 1000
                referencias = {
                    "trabajo_compresor": wc_ref,
                    "trabajo_turbina": wt_ref,
                    "trabajo_neto": wt_ref - wc_ref,
                    "calor_aportado": qin_ref,
                }
                ciclo = main.calcular_ciclo_ideal(T1, T3, gamma, cp, rp, p1)
                for clave, esperado in referencias.items():
                    actual = ciclo[clave]
                    error_abs = abs(actual - esperado)
                    error_rel = error_abs / abs(esperado) if esperado != 0 else None
                    tolerancia = self.ATOL_E + self.RTOL * abs(esperado)
                    self.assertLessEqual(error_abs, tolerancia,
                                         f"{nombre}, {clave}: error abs {error_abs:.3g} kJ/kg; "
                                         f"error relativo {error_rel}; tolerancia {tolerancia:.3g} kJ/kg")

                wc = ciclo["trabajo_compresor"]
                wt = ciclo["trabajo_turbina"]
                wn = ciclo["trabajo_neto"]
                qin = ciclo["calor_aportado"]
                qout = cp * (ciclo["temperaturas"][3] - T1) / 1000
                escala = max(abs(wc), abs(wt), abs(wn), abs(qin), abs(qout))
                tolerancia_residuo = self.ATOL_E + self.RTOL * escala
                # Son identidades de conservación, no otra validación independiente de cp constante.
                residuo_trabajo = wn - (wt - wc)
                residuo_primera_ley = wn - (qin - qout)
                for descripcion, residuo in (("trabajo", residuo_trabajo),
                                              ("primera ley", residuo_primera_ley)):
                    self.assertLessEqual(abs(residuo), tolerancia_residuo,
                                         f"{nombre}, {descripcion}: residuo {residuo:.3g} kJ/kg; "
                                         f"escala {escala:.3g} kJ/kg; "
                                         f"tolerancia {tolerancia_residuo:.3g} kJ/kg")
                self.assertLessEqual(abs((wt - wc) - (qin - qout)), tolerancia_residuo)
                self.assertLessEqual(abs(wn - (qin_ref - qout_ref)), tolerancia_residuo)

    def test_rendimiento_analitico_frente_a_balance_motor(self):
        for nombre, T1, T3, gamma, cp, rp, p1 in self.CASOS:
            with self.subTest(caso=nombre):
                punto = evaluar_punto(T1, T3, gamma, cp, rp, p1)
                self.assertTrue(punto["viable"], f"{nombre}: no es un punto motor")
                self.assertGreater(punto["calor_aportado"], 0)
                eta_ref = 1 - rp ** (-(gamma - 1) / gamma)
                eta_formula = main.calcular_rendimiento(gamma, rp)
                eta_balance = punto["trabajo_neto"] / punto["calor_aportado"]
                for etiqueta, eta in (("formula", eta_formula), ("balance", eta_balance)):
                    error = abs(eta - eta_ref)
                    tolerancia = self.ATOL_ETA + self.RTOL * abs(eta_ref)
                    self.assertLessEqual(error, tolerancia,
                                         f"{nombre}, {etiqueta}: error {error:.3g} "
                                         f"(fracción); tolerancia {tolerancia:.3g}")

    def test_temperaturas_coinciden_en_maximo_ideal_analitico_y_numerico(self):
        # La relación del máximo ya está contrastada en test_optimizacion.py.
        for nombre, T1, T3, gamma, cp, _, p1 in self.CASOS[:3]:
            with self.subTest(caso=nombre):
                T_estacionaria = sqrt(T1 * T3)
                rp_analitica = main.calcular_relacion_optima(T1, T3, gamma)
                temperaturas_analiticas = main.calcular_temperaturas(T1, T3, gamma, rp_analitica)
                for temperatura in (temperaturas_analiticas[1], temperaturas_analiticas[3]):
                    self.assertLessEqual(abs(temperatura - T_estacionaria),
                                         self.ATOL_T + self.RTOL * T_estacionaria)

                # Búsqueda directa: no pasa por optimizar_trabajo_neto ni usa su candidato.
                dominio = calcular_dominios(T1, T3, gamma, cp, p1)["ideal"]
                numerico = buscar_maximo_numerico(T1, T3, gamma, cp, p1, dominio=dominio)
                self.assertTrue(numerico["ciclo"]["viable"])
                self.assertLess(dominio["intervalo"][0], numerico["rp"])
                self.assertLess(numerico["rp"], dominio["intervalo"][1])
                T2, T4 = numerico["ciclo"]["temperaturas"][1::2]
                a = (gamma - 1) / gamma
                error_rel_rp = numerico["resolucion_rp"] / numerico["rp"]
                tolerancia_numerica = (self.ATOL_T + self.RTOL * T_estacionaria
                                      + 2 * a * T_estacionaria * error_rel_rp)
                for descripcion, error in (("T2 respecto a raíz geométrica", abs(T2 - T_estacionaria)),
                                           ("T4 respecto a raíz geométrica", abs(T4 - T_estacionaria)),
                                           ("T2-T4", abs(T2 - T4))):
                    self.assertLessEqual(error, 2 * tolerancia_numerica,
                                         f"{nombre}, {descripcion}: error {error:.3g} K; "
                                         f"tolerancia {2*tolerancia_numerica:.3g} K")


if __name__ == "__main__":
    unittest.main()
