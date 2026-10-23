"""Tarea 1.4: sensibilidad de controles numéricos, sin modificar producción.

No son benchmarks temporales: se observan errores, residuos, llamadas y paradas
en casos motores moderados; las referencias analíticas no guían las búsquedas.
"""

from math import exp, log, sqrt
import unittest

from optimizacion import buscar_maximo_numerico, calcular_candidato_analitico
from optimizacion_rendimiento import (
    buscar_maximo_rendimiento_numerico, calcular_candidato_rendimiento,
)
from viabilidad import ErrorNumerico, bisectar_raiz, calcular_dominios, evaluar_punto


class ConvergenciaNumericaTests(unittest.TestCase):
    # Nombre, T1/T3 [K], gamma, cp [J/(kg K)], p1 [kPa], eta_c, eta_t, delta.
    IDEAL = ("ideal", 288.15, 1600, 1.4, 1005, 100, 1, 1, 0)
    NO_IDEALES = (
        ("referencia", 288.15, 1600, 1.4, 1005, 100, .85, .9, .05),
        ("gamma_133", 300, 1200, 1.33, 1100, 90, .9, .92, .08),
    )
    TOLERANCIAS_RAIZ = (1e-6, 1e-8, 1e-10, 1e-12)
    MALLAS = (17, 33, 65, 129, 257, 513)
    TOLERANCIAS_LOG = (1e-5, 1e-7, 1e-9, 1e-11)
    DISTANCIAS_FRONTERA = (1e-3, 1e-6, 1e-9, 1e-12)

    def _referencias_raices(self):
        """Devuelve (nombre, f, lo, hi, x_ref, a) sin llamar a bisección.

        Las x y sus intervalos son adimensionales; a=None para sqrt(2).
        """
        casos = [("raiz_sqrt2", lambda x: x*x - 2, 1, 2, sqrt(2), None)]
        for nombre, T1, T3, gamma, cp, p1, ec, et, delta in self.NO_IDEALES:
            a = (gamma - 1) / gamma
            h = T3 / T1 * ec * et
            k = (1 - delta)**(-a)
            D = (h - 1)**2 - 4*h*(k - 1)
            self.assertGreater(D, 0)
            centro = (1 + h) / 2

            def Q(x, h=h, k=k):
                return (x - 1)*(x - h) + h*(k - 1)

            casos.extend(((nombre + "_inferior", Q, 0, centro,
                           ((1 + h) - sqrt(D))/2, a),
                          (nombre + "_superior", Q, centro, 1 + h,
                           ((1 + h) + sqrt(D))/2, a)))
        return casos

    def test_biseccion_tolerancias_anchuras_y_coste(self):
        for nombre, funcion, lo, hi, referencia, a in self._referencias_raices():
            for tol in self.TOLERANCIAS_RAIZ:
                with self.subTest(raiz=nombre, tolerancia=tol):
                    observaciones = []

                    def contado(x):
                        valor = funcion(x)
                        observaciones.append((x, valor))
                        return valor

                    x = bisectar_raiz(contado, lo, hi, tolerancia=tol,
                                      iteraciones=100)
                    self.assertGreaterEqual(len(observaciones), 3)
                    self.assertLessEqual(len(observaciones), 102)
                    self.assertEqual(observaciones[0][0], lo)
                    self.assertEqual(observaciones[1][0], hi)
                    izquierda, derecha = lo, hi
                    fi = funcion(izquierda)
                    fm = None
                    self.assertLessEqual(fi*funcion(derecha), 0)
                    for i, (medio, fm) in enumerate(observaciones[2:], start=1):
                        # Reconstruye la acotación conservada, sin suponer
                        # que el error observado se divida por dos cada vez.
                        self.assertAlmostEqual(medio, (izquierda + derecha)/2,
                                               delta=4e-15*max(1, abs(medio)))
                        ancho_previo = (hi - lo)/2**(i-1)
                        self.assertAlmostEqual(derecha - izquierda, ancho_previo,
                                               delta=5e-14*max(1, hi - lo))
                        if fi*fm <= 0:
                            derecha = medio
                        else:
                            izquierda, fi = medio, fm
                        self.assertLessEqual(fi*funcion(derecha), 0)

                    n = len(observaciones) - 2
                    ancho_previo = (hi - lo)/2**(n-1)
                    self.assertTrue(fm == 0 or
                                    ancho_previo <= tol*max(1, abs(x))
                                    + 5e-14*max(1, hi - lo))
                    self.assertLessEqual(abs(x - referencia),
                                         ancho_previo/2 + 5e-13*max(1, abs(referencia)))
                    self.assertEqual(x, observaciones[-1][0])
                    self.assertLessEqual(abs(funcion(x)),
                                         abs(funcion(referencia)) +
                                         8*max(1, abs(hi), abs(lo))*ancho_previo)
                    if a is not None:
                        rp, rp_ref = x**(1/a), referencia**(1/a)
                        # La potencia amplifica la sensibilidad: comprobar
                        # contra una cota local conservadora, no contra tol.
                        self.assertLessEqual(abs(rp - rp_ref)/rp_ref,
                            4*abs(x - referencia)/(a*referencia) + 1e-12)

    def test_biseccion_agotamiento_e_intervalo_invalido(self):
        for nombre, funcion, lo, hi, _, _ in self._referencias_raices():
            for max_iter in (1, 5, 12):
                with self.subTest(raiz=nombre, max_iteraciones=max_iter):
                    llamadas = [0]

                    def contado(x):
                        llamadas[0] += 1
                        return funcion(x)

                    with self.assertRaisesRegex(ErrorNumerico, "no converge"):
                        bisectar_raiz(contado, lo, hi, tolerancia=1e-12,
                                      iteraciones=max_iter)
                    self.assertEqual(llamadas[0], max_iter + 2)
        with self.assertRaises(ValueError):
            bisectar_raiz(lambda x: x*x + 1, 1, 2)

    def test_mallas_trabajo_acotacion_precision_y_coste(self):
        for nombre, *parametros in (self.IDEAL, *self.NO_IDEALES):
            T1, T3, gamma, cp, p1, ec, et, delta = parametros
            dominio = calcular_dominios(*parametros)["noideal"]
            lo, hi = dominio["intervalo"]
            rp_ref = calcular_candidato_analitico(T1, T3, gamma, ec, et, delta)
            w_ref = evaluar_punto(T1, T3, gamma, cp, rp_ref, p1, ec, et, delta)["trabajo_neto"]
            for muestras in self.MALLAS:
                with self.subTest(caso=nombre, muestras=muestras):
                    resultado = buscar_maximo_numerico(*parametros, dominio=dominio,
                        muestras=muestras, tolerancia_log=1e-9, max_iteraciones=100)
                    self.assertTrue(resultado["ciclo"]["viable"])
                    self.assertTrue(lo < resultado["rp"] < hi)
                    self.assertEqual(resultado["muestras_iniciales"], muestras)
                    self.assertGreaterEqual(resultado["evaluaciones"], muestras)
                    self.assertLess(resultado["iteraciones"], 100)
                    self.assertLessEqual(abs(resultado["rp"] - rp_ref), 2e-7*rp_ref)
                    self.assertLessEqual(abs(resultado["ciclo"]["trabajo_neto"] - w_ref),
                                         1e-9)  # kJ/kg; máximo plano

                    # Comprueba por separado que la malla inicial sí acota
                    # el óptimo analítico, incluso con sólo 17 nodos.
                    ylo, yhi = log(lo), log(hi)
                    margen = (yhi-ylo)*1e-6
                    y0, y1 = ylo + margen, yhi - margen
                    paso = (y1-y0)/(muestras-1)
                    ys = [y0 + i*paso for i in range(muestras)]
                    valores = [evaluar_punto(T1, T3, gamma, cp, exp(y), p1,
                                             ec, et, delta)["trabajo_neto"] for y in ys]
                    indice = max(range(muestras), key=valores.__getitem__)
                    self.assertTrue(0 < indice < muestras-1)
                    self.assertLess(ys[indice-1], log(rp_ref))
                    self.assertLess(log(rp_ref), ys[indice+1])
                    self.assertAlmostEqual(resultado["paso_log_inicial"], paso,
                                           delta=2e-14)

    def test_tolerancias_refinamiento_trabajo(self):
        for nombre, *p in (self.IDEAL, *self.NO_IDEALES):
            T1, T3, gamma, cp, p1, ec, et, delta = p
            dominio = calcular_dominios(*p)["noideal"]
            rp_ref = calcular_candidato_analitico(T1, T3, gamma, ec, et, delta)
            w_ref = evaluar_punto(T1, T3, gamma, cp, rp_ref, p1, ec, et, delta)["trabajo_neto"]
            for tol in self.TOLERANCIAS_LOG:
                with self.subTest(caso=nombre, tolerancia_log=tol):
                    r = buscar_maximo_numerico(*p, dominio=dominio, muestras=257,
                                               tolerancia_log=tol, max_iteraciones=100)
                    self.assertTrue(r["ciclo"]["viable"])
                    self.assertLessEqual(abs(r["rp"] - rp_ref)/rp_ref,
                                         max(2e-7, 3*tol))
                    self.assertLessEqual(abs(r["ciclo"]["trabajo_neto"] - w_ref), 1e-9)
                    self.assertGreaterEqual(r["evaluaciones"], 257)
                    self.assertLessEqual(r["iteraciones"], 100)
                    self.assertGreaterEqual(r["resolucion_rp"], r["rp"]*tol)
                    ancho_log = log(r["intervalo_final"][1]/r["intervalo_final"][0])
                    self.assertLessEqual(ancho_log, tol + 1e-14)

    def test_tolerancias_refinamiento_rendimiento(self):
        for nombre, *p in self.NO_IDEALES:
            T1, T3, gamma, cp, p1, ec, et, delta = p
            rp_ref = calcular_candidato_rendimiento(T1, T3, gamma, ec, et, delta)
            eta_ref = evaluar_punto(T1, T3, gamma, cp, rp_ref, p1,
                                    ec, et, delta)["rendimiento"]
            for tol in self.TOLERANCIAS_LOG:
                with self.subTest(caso=nombre, tolerancia_log=tol):
                    r = buscar_maximo_rendimiento_numerico(*p, muestras=257,
                        tolerancia_log=tol, max_iteraciones=100)
                    self.assertEqual(r["estado"], "maximo_interior")
                    self.assertTrue(r["ciclo"]["viable"])
                    self.assertLessEqual(abs(r["rp"] - rp_ref)/rp_ref,
                                         max(2e-6, 3*tol))
                    self.assertLessEqual(abs(r["ciclo"]["rendimiento"] - eta_ref), 1e-10)
                    self.assertGreaterEqual(r["evaluaciones"], 257)
                    self.assertLessEqual(r["iteraciones"], 100)
                    self.assertGreaterEqual(r["resolucion_rp"], r["rp"]*tol)
                    ancho_log = log(r["intervalo_final"][1]/r["intervalo_final"][0])
                    self.assertLessEqual(ancho_log, tol + 1e-14)

    def test_agotamiento_controlado_en_ambos_optimizadores(self):
        for nombre, *p in (self.IDEAL, self.NO_IDEALES[0]):
            dominio = calcular_dominios(*p)["noideal"]
            for max_iter in (1, 12, 30):
                with self.subTest(algoritmo="trabajo", caso=nombre, iteraciones=max_iter):
                    with self.assertRaisesRegex(ErrorNumerico, "no converge"):
                        buscar_maximo_numerico(*p, dominio=dominio,
                            tolerancia_log=1e-11, max_iteraciones=max_iter)
            with self.subTest(algoritmo="trabajo", caso=nombre, iteraciones=100):
                self.assertIsNotNone(buscar_maximo_numerico(*p, dominio=dominio,
                    tolerancia_log=1e-11, max_iteraciones=100))

        for nombre, *p in self.NO_IDEALES:
            for max_iter in (1, 12, 30):
                with self.subTest(algoritmo="rendimiento", caso=nombre,
                                  iteraciones=max_iter):
                    with self.assertRaisesRegex(ErrorNumerico, "no converge"):
                        buscar_maximo_rendimiento_numerico(*p, tolerancia_log=1e-11,
                            max_iteraciones=max_iter)
            with self.subTest(algoritmo="rendimiento", caso=nombre, iteraciones=100):
                self.assertEqual(buscar_maximo_rendimiento_numerico(*p,
                    tolerancia_log=1e-11, max_iteraciones=100)["estado"], "maximo_interior")

    def test_fronteras_abiertas_y_banda_de_viabilidad(self):
        for nombre, *p in (self.IDEAL, self.NO_IDEALES[0]):
            dominio = calcular_dominios(*p)["noideal"]
            lo, hi = dominio["intervalo"]
            for lado, limite in (("inferior", lo), ("superior", hi)):
                resultados = []
                for distancia in self.DISTANCIAS_FRONTERA:
                    with self.subTest(caso=nombre, lado=lado, distancia=distancia):
                        rp = limite*(1+distancia if lado == "inferior" else 1-distancia)
                        self.assertTrue(lo < rp < hi)
                        punto = evaluar_punto(*p[:4], rp, *p[4:])
                        fisico = evaluar_punto(*p[:4], rp, *p[4:], tolerancia=0)
                        # Una banda no equivale a un dominio físicamente vacío.
                        self.assertTrue(fisico["viable"])
                        self.assertEqual(punto["viable"], all(
                            punto["margenes"][clave] > punto["tolerancias"][clave]
                            for clave in punto["margenes"]))
                        if distancia >= 1e-9:
                            self.assertTrue(punto["viable"])
                        else:
                            self.assertFalse(punto["viable"])
                            self.assertIsNone(punto["rendimiento"])
                            self.assertTrue(punto["motivos"])
                        self.assertGreater(punto["calor_aportado"], 0)
                        self.assertGreater(punto["trabajo_neto"], 0)
                        resultados.append(punto)

                # Propiedad física local (tres distancias representables),
                # no hipótesis de monotonía de errores de redondeo.
                for anterior, siguiente in zip(resultados[:2], resultados[1:3]):
                    self.assertGreater(anterior["trabajo_neto"],
                                       siguiente["trabajo_neto"])
                    if nombre == "ideal" and lado == "superior":
                        self.assertGreater(anterior["calor_aportado"],
                                           siguiente["calor_aportado"])

                borde = evaluar_punto(*p[:4], limite, *p[4:])
                self.assertFalse(borde["viable"])
                self.assertIsNone(borde["rendimiento"])

            w = buscar_maximo_numerico(*p, dominio=dominio)
            self.assertTrue(lo < w["rp"] < hi and w["ciclo"]["viable"])
            e = buscar_maximo_rendimiento_numerico(*p)
            if nombre == "ideal":
                self.assertEqual(e["estado"], "supremo_no_alcanzado")
                self.assertFalse(e["supremo"]["alcanzado"])
            else:
                self.assertEqual(e["estado"], "maximo_interior")
                self.assertTrue(lo < e["rp"] < hi and e["ciclo"]["viable"])

    def test_dominio_vacio_separa_ausencia_de_fallo_numerico(self):
        p = (300, 600, 1.4, 1005, 100, .5, .5, 0)
        dominio = calcular_dominios(*p)["noideal"]
        self.assertEqual(dominio["intervalo"], ())
        self.assertIsNone(buscar_maximo_numerico(*p, dominio=dominio))
        resultado = buscar_maximo_rendimiento_numerico(*p)
        self.assertEqual(resultado["estado"], "sin_dominio")
        self.assertIsNone(resultado["rp"])
