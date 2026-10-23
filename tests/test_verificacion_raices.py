"""Contrastes analíticos de raíces y fronteras; no validación experimental."""

from math import sqrt
import unittest

from viabilidad import calcular_dominios, evaluar_punto


class VerificacionRaicesTests(unittest.TestCase):
    # Nombre, T1 [K], T3 [K], gamma [-], cp [J/(kg K)], p1 [kPa],
    # eficiencia de compresor, eficiencia de turbina, pérdida de presión.
    CASOS_NO_IDEALES = (
        ("referencia", 288.15, 1600, 1.4, 1005, 100, .85, .9, .05),
        ("gamma_133", 300, 1200, 1.33, 1100, 90, .9, .92, .08),
        ("entrada_fria", 280, 1450, 1.36, 1010, 85, .78, .88, .12),
        ("perdida_moderada", 320, 1900, 1.4, 1040, 120, .8, .9, .16),
    )

    # Bisección: intervalo final relativo ~1e-12 en x; transformación
    # rp=x**(1/a) amplifica el error relativo por 1/a en primer orden.
    ATOL_X = 2e-12       # x adimensional
    RTOL_X = 2e-12
    ATOL_RP = 1e-9      # relación de presiones adimensional
    RTOL_RP = 2e-11
    RTOL_Q = 2e-11      # residuo relativo a los términos de Q
    SEPARACION = 1e-5   # fuera de la banda de clasificación de 1e-10

    def test_raices_noideales_con_referencias_y_residuos(self):
        for nombre, T1, T3, gamma, cp, p1, eta_c, eta_t, delta in self.CASOS_NO_IDEALES:
            with self.subTest(caso=nombre):
                a = (gamma - 1) / gamma
                h = (T3 / T1) * eta_c * eta_t
                k = (1 - delta)**(-a)
                D = (h - 1)**2 - 4 * h * (k - 1)
                self.assertGreater(D, 0)
                raiz_D = sqrt(D)
                x_referencias = ((1 + h - raiz_D) / 2, (1 + h + raiz_D) / 2)
                rp_referencias = tuple(x**(1 / a) for x in x_referencias)

                calculado = calcular_dominios(T1, T3, gamma, cp, p1, eta_c, eta_t, delta)
                rp_calculadas = calculado["noideal"]["trabajo"]
                self.assertEqual(len(rp_calculadas), 2)
                self.assertAlmostEqual(calculado["noideal"]["discriminante"], D,
                                       delta=1e-13 + 1e-13 * abs(D))

                for lado, x_ref, rp_ref, rp_num in zip(
                        ("inferior", "superior"), x_referencias, rp_referencias, rp_calculadas):
                    with self.subTest(raiz=lado):
                        x_num = rp_num**a  # Se recupera x de la salida, no de Q ni de bisectar_raiz.
                        error_x = abs(x_num - x_ref)
                        error_rp = abs(rp_num - rp_ref)
                        relativo_x = error_x / abs(x_ref)
                        relativo_rp = error_rp / abs(rp_ref)
                        residuo = x_num*x_num - (1 + h)*x_num + h*k
                        escala_Q = max(1, x_num*x_num, abs((1 + h)*x_num), h*k)
                        self.assertLessEqual(
                            error_x, self.ATOL_X + self.RTOL_X*abs(x_ref),
                            f"{nombre}/{lado}: error x={error_x:.3g}; relativo={relativo_x:.3g}")
                        self.assertLessEqual(
                            error_rp, self.ATOL_RP + self.RTOL_RP*abs(rp_ref),
                            f"{nombre}/{lado}: error rp={error_rp:.3g}; relativo={relativo_rp:.3g}")
                        self.assertLessEqual(
                            abs(residuo), self.RTOL_Q*escala_Q,
                            f"{nombre}/{lado}: Q(x)={residuo:.3g}; escala={escala_Q:.3g}")

    def test_interseccion_de_restricciones_y_fronteras_abiertas(self):
        for nombre, T1, T3, gamma, cp, p1, eta_c, eta_t, delta in self.CASOS_NO_IDEALES:
            with self.subTest(caso=nombre):
                a = (gamma - 1) / gamma
                theta = T3 / T1
                h = theta * eta_c * eta_t
                k = (1 - delta)**(-a)
                D = (h - 1)**2 - 4*h*(k - 1)
                x_menos, x_mas = ((1 + h - sqrt(D))/2, (1 + h + sqrt(D))/2)
                rp_menos, rp_mas = x_menos**(1/a), x_mas**(1/a)
                limite_expansion = 1/(1 - delta)
                limite_calor = (1 + eta_c*(theta - 1))**(1/a)
                inferior = max(1, limite_expansion, rp_menos)
                superior = min(limite_calor, rp_mas)
                self.assertLess(inferior, superior)

                dominio = calcular_dominios(T1, T3, gamma, cp, p1, eta_c, eta_t, delta)
                for actual, esperado in zip(dominio["noideal"]["intervalo"],
                                             (inferior, superior)):
                    self.assertLessEqual(abs(actual - esperado),
                                         self.ATOL_RP + self.RTOL_RP*abs(esperado))
                self.assertLessEqual(abs(dominio["noideal"]["expansion"] - limite_expansion),
                                     self.ATOL_RP + self.RTOL_RP*limite_expansion)
                self.assertLessEqual(abs(dominio["noideal"]["calor"] - limite_calor),
                                     self.ATOL_RP + self.RTOL_RP*limite_calor)

                puntos = (
                    ("exterior_inferior", inferior*(1-self.SEPARACION), False),
                    ("interior_inferior", inferior*(1+self.SEPARACION), True),
                    ("centro", sqrt(inferior*superior), True),
                    ("interior_superior", superior*(1-self.SEPARACION), True),
                    ("exterior_superior", superior*(1+self.SEPARACION), False),
                )
                for etiqueta, rp, motor in puntos:
                    with self.subTest(punto=etiqueta):
                        x = rp**a
                        Q = x*x - (1+h)*x + h*k
                        # Cuatro desigualdades independientes del evaluador.
                        fisicamente_motor = (rp > 1 and rp > limite_expansion
                                             and x < 1+eta_c*(theta-1) and Q < 0)
                        self.assertEqual(fisicamente_motor, motor)
                        punto = evaluar_punto(T1, T3, gamma, cp, rp, p1,
                                              eta_c, eta_t, delta)
                        self.assertEqual(punto["viable"], motor)
                        if motor:
                            self.assertGreater(punto["calor_aportado"], 0)
                            self.assertGreater(punto["trabajo_neto"], 0)
                            self.assertGreater(punto["presiones"][2], p1)

                # Las raíces matemáticas son excluidas también por la banda
                # positiva usada por evaluar_punto, distinta de la bisección.
                for frontera in dominio["noideal"]["intervalo"]:
                    punto = evaluar_punto(T1, T3, gamma, cp, frontera, p1,
                                          eta_c, eta_t, delta)
                    self.assertFalse(punto["viable"])
                    self.assertIn("trabajo_neto", punto["fronteras"])

    def test_limite_reversible_factoriza_y_es_abierto(self):
        T1, T3, gamma, cp, p1 = 300, 1200, 1.4, 1005, 100
        a = (gamma - 1)/gamma
        theta = T3/T1
        # eta_c=eta_t=1 y delta=0: h=theta, k=1, D=(theta-1)**2.
        h, k = theta, 1
        D = (h-1)**2 - 4*h*(k-1)
        self.assertEqual(D, (theta-1)**2)
        for x in (1, 1.5, 2.5, theta, 5):
            with self.subTest(x=x):
                self.assertAlmostEqual(x*x-(1+h)*x+h*k, (x-1)*(x-theta))
        dominio = calcular_dominios(T1, T3, gamma, cp, p1)
        rp_esperadas = (1, theta**(1/a))
        for actual, esperado in zip(dominio["noideal"]["trabajo"], rp_esperadas):
            self.assertLessEqual(abs(actual-esperado),
                                 self.ATOL_RP + self.RTOL_RP*esperado)
        for frontera in rp_esperadas:
            self.assertFalse(evaluar_punto(T1, T3, gamma, cp, frontera, p1)["viable"])

    def test_discriminante_negativo_y_raiz_doble(self):
        # Construcciones exactas simples, sin exigir D≈0 por cancelación.
        casos = (
            ("negativo", 300, 600, 1.4, 1005, 100, .8, .8, .5),
            ("doble", 300, 600, 1.4, 1005, 100, .5, 1, 0),
        )
        for nombre, T1, T3, gamma, cp, p1, eta_c, eta_t, delta in casos:
            with self.subTest(caso=nombre):
                a = (gamma-1)/gamma
                h = (T3/T1)*eta_c*eta_t
                k = (1-delta)**(-a)
                D = (h-1)**2-4*h*(k-1)
                dominio = calcular_dominios(T1, T3, gamma, cp, p1,
                                            eta_c, eta_t, delta)["noideal"]
                if nombre == "negativo":
                    self.assertLess(D, 0)
                    self.assertLess(dominio["discriminante"], 0)
                    vertice = (1+h)/2
                    self.assertGreater(vertice*vertice-(1+h)*vertice+h*k, 0)
                else:
                    self.assertEqual((h, k, D), (1, 1, 0))
                    self.assertEqual(dominio["discriminante"], 0)
                    for x in (.5, 1, 1.5):
                        self.assertEqual(x*x-(1+h)*x+h*k, (x-1)**2)
                        self.assertGreaterEqual((x-1)**2, 0)
                self.assertEqual(dominio["trabajo"], ())
                self.assertEqual(dominio["intervalo"], ())

    def test_raices_reales_sin_dominio_motor(self):
        # theta=2, eta_c=eta_t=1/2, delta=0 -> h=1/2, k=1.
        # Q=(x-1/2)(x-1), negativa sólo en x∈(1/2,1): rp<1.
        T1, T3, gamma, cp, p1, eta_c, eta_t, delta = (
            300, 600, 1.4, 1005, 100, .5, .5, 0)
        a = (gamma-1)/gamma
        h, k = (T3/T1)*eta_c*eta_t, (1-delta)**(-a)
        D = (h-1)**2 - 4*h*(k-1)
        self.assertEqual(D, .25)
        x_ref = ((1+h-sqrt(D))/2, (1+h+sqrt(D))/2)
        self.assertEqual(x_ref, (.5, 1))
        dominio = calcular_dominios(T1, T3, gamma, cp, p1,
                                    eta_c, eta_t, delta)["noideal"]
        self.assertGreater(dominio["discriminante"], 0)
        self.assertEqual(dominio["intervalo"], ())
        for rp_num, x in zip(dominio["trabajo"], x_ref):
            self.assertLessEqual(abs(rp_num-x**(1/a)),
                                 self.ATOL_RP+self.RTOL_RP*x**(1/a))
        x_interior = .75
        self.assertLess(x_interior*x_interior-(1+h)*x_interior+h*k, 0)
        rp_interior = x_interior**(1/a)
        self.assertLess(rp_interior, 1)  # Intervalo Q<0 excluido por compresión.
        self.assertFalse(evaluar_punto(T1, T3, gamma, cp, rp_interior, p1,
                                      eta_c, eta_t, delta)["viable"])
        self.assertFalse(evaluar_punto(T1, T3, gamma, cp, 2, p1,
                                      eta_c, eta_t, delta)["viable"])


if __name__ == "__main__":
    unittest.main()
