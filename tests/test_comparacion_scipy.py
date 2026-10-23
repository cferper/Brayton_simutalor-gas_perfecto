"""Comparaciones opcionales con SciPy: verificación, no validación física."""

from math import exp, isfinite, log, sqrt
from types import SimpleNamespace
import unittest

from optimizacion import buscar_maximo_numerico
from optimizacion_rendimiento import buscar_maximo_rendimiento_numerico
from viabilidad import bisectar_raiz, calcular_dominios, evaluar_punto

try:
    from scipy import optimize as scipy_optimize
except ImportError:  # El simulador y los demás tests no necesitan SciPy.
    scipy_optimize = None


class ComparacionSciPyTests(unittest.TestCase):
    # nombre, T1 [K], T3 [K], gamma, cp [J/(kg K)], p1 [kPa], eta_c, eta_t, delta
    CASOS_NO_IDEALES = (
        ("referencia", 288.15, 1600, 1.4, 1005, 100, .85, .9, .05),
        ("gamma_133", 300, 1200, 1.33, 1100, 90, .9, .92, .08),
        ("entrada_fria", 280, 1450, 1.36, 1010, 85, .78, .88, .12),
    )
    CASO_IDEAL = ("ideal", 288.15, 1600, 1.4, 1005, 100, 1, 1, 0)

    XTOL = 1e-12  # Abscisa x; SciPy utiliza xtol+rtol*|x|, no sólo rtol.
    RTOL_RAIZ = 1e-12
    ATOL_X = 2e-12
    RTOL_X = 3e-12
    ATOL_RP_RAIZ = 1e-9
    RTOL_RP_RAIZ = 2e-11
    RTOL_RESIDUO = 2e-11

    XATOL_LOG = 1e-9  # Abscisa y=ln(rp), para bounded y los buscadores propios.
    RTOL_RP_OPT = 2e-6
    ATOL_RP_OPT = 1e-6
    ATOL_TRABAJO = 1e-8  # kJ/kg
    RTOL_TRABAJO = 1e-10
    ATOL_ETA = 1e-10    # fracción
    RTOL_ETA = 1e-10
    MARGEN_LOG = 1e-6   # Fracción del intervalo abierto, para SciPy.

    def _resolver_tres_raices(self, funcion, inferior, superior):
        """Ejecuta tres métodos sobre el mismo callback/intervalo y cuenta llamadas."""
        resultados = {}
        for nombre in ("propia", "bisect", "brentq"):
            contador = [0]

            def contado(x):
                contador[0] += 1
                return funcion(x)

            if nombre == "propia":
                raiz = bisectar_raiz(contado, inferior, superior, tolerancia=self.XTOL)
            else:
                raiz, informacion = getattr(scipy_optimize, nombre)(
                    contado, inferior, superior, xtol=self.XTOL,
                    rtol=self.RTOL_RAIZ, maxiter=100, full_output=True, disp=False)
                self.assertTrue(informacion.converged, f"{nombre} no converge")
                self.assertEqual(contador[0], informacion.function_calls)
            resultados[nombre] = (raiz, contador[0])
        return resultados

    def _aceptar_maximo_scipy(self, resultado, dominio, parametros, clave):
        """Acepta sólo solución convergida, motor interior y con descenso bilateral."""
        if (not getattr(resultado, "success", False)
                or not isfinite(resultado.x) or not isfinite(resultado.fun)
                or not dominio["intervalo"]):
            return None
        lo, hi = dominio["intervalo"]
        y = float(resultado.x)
        rp = exp(y)
        if not lo < rp < hi:
            return None
        T1, T3, gamma, cp, p1, eta_c, eta_t, delta = parametros
        punto = evaluar_punto(T1, T3, gamma, cp, rp, p1, eta_c, eta_t, delta)
        if not punto["viable"] or not isfinite(punto[clave]):
            return None

        # Un éxito de bounded cerca de una frontera no implica máximo interior.
        paso = .002 * (log(hi) - log(lo))
        if not log(lo) < y - paso < y + paso < log(hi):
            return None
        testigos = (evaluar_punto(T1, T3, gamma, cp, exp(y + signo*paso), p1,
                                  eta_c, eta_t, delta) for signo in (-1, 1))
        descenso_minimo = 64 * 2.220446049250313e-16 * max(1, abs(punto[clave]))
        if not all(p["viable"] and p[clave] < punto[clave] - descenso_minimo
                   for p in testigos):
            return None
        return rp, punto

    @unittest.skipIf(scipy_optimize is None, "SciPy no instalado: comparaciones omitidas")
    def test_raiz_matematica_conocida(self):
        funcion = lambda x: x*x - 2
        esperado = sqrt(2)
        soluciones = self._resolver_tres_raices(funcion, 1, 2)
        for nombre, (x, llamadas) in soluciones.items():
            with self.subTest(metodo=nombre):
                self.assertLessEqual(abs(x-esperado), self.ATOL_X + self.RTOL_X*esperado)
                self.assertLessEqual(abs(funcion(x)), self.RTOL_RESIDUO*4)
                self.assertGreater(llamadas, 0)

    @unittest.skipIf(scipy_optimize is None, "SciPy no instalado: comparaciones omitidas")
    def test_raices_del_dominio_con_bisect_y_brentq(self):
        for nombre, T1, T3, gamma, cp, p1, ec, et, delta in self.CASOS_NO_IDEALES:
            with self.subTest(caso=nombre):
                a = (gamma-1)/gamma
                h = T3/T1*ec*et
                k = (1-delta)**(-a)
                D = (h-1)**2 - 4*h*(k-1)
                self.assertGreater(D, 0)
                x_ref = ((1+h-sqrt(D))/2, (1+h+sqrt(D))/2)
                centro = (1+h)/2
                funcion = lambda x: (x-1)*(x-h) + h*(k-1)
                rp_dominio = calcular_dominios(T1, T3, gamma, cp, p1,
                                              ec, et, delta)["noideal"]["trabajo"]
                for lado, extremo, xr, rp_calc in zip(
                        ("inferior", "superior"), ((0, centro), (centro, 1+h)),
                        x_ref, rp_dominio):
                    with self.subTest(raiz=lado):
                        soluciones = self._resolver_tres_raices(funcion, *extremo)
                        rp_ref = xr**(1/a)
                        for metodo, (x_num, llamadas) in soluciones.items():
                            with self.subTest(metodo=metodo):
                                rp_num = x_num**(1/a)
                                error_x = abs(x_num-xr)
                                error_rp = abs(rp_num-rp_ref)
                                relativo_x = error_x/abs(xr)
                                relativo_rp = error_rp/abs(rp_ref)
                                self.assertLessEqual(error_x, self.ATOL_X+self.RTOL_X*abs(xr),
                                    f"error en x {error_x:.3g}; relativo {relativo_x:.3g}")
                                self.assertLessEqual(error_rp,
                                    self.ATOL_RP_RAIZ+self.RTOL_RP_RAIZ*abs(rp_ref),
                                    f"error en rp {error_rp:.3g}; relativo {relativo_rp:.3g}")
                                escala_Q = max(1, x_num*x_num, abs((1+h)*x_num), h*k)
                                self.assertLessEqual(abs(funcion(x_num)),
                                                     self.RTOL_RESIDUO*escala_Q)
                                self.assertGreater(llamadas, 0)
                        self.assertLessEqual(abs(rp_calc-rp_ref),
                            self.ATOL_RP_RAIZ+self.RTOL_RP_RAIZ*abs(rp_ref))

    @unittest.skipIf(scipy_optimize is None, "SciPy no instalado: comparaciones omitidas")
    def test_maximo_trabajo_con_bounded(self):
        for nombre, T1, T3, gamma, cp, p1, ec, et, delta in (
                self.CASO_IDEAL, *self.CASOS_NO_IDEALES):
            with self.subTest(caso=nombre):
                parametros = (T1, T3, gamma, cp, p1, ec, et, delta)
                dominio = calcular_dominios(*parametros)["noideal"]
                propio = buscar_maximo_numerico(*parametros, dominio=dominio,
                                                tolerancia_log=self.XATOL_LOG)
                self.assertIsNotNone(propio)
                self.assertTrue(propio["ciclo"]["viable"])
                lo, hi = dominio["intervalo"]
                ylo, yhi = log(lo), log(hi)
                margen = self.MARGEN_LOG*(yhi-ylo)
                llamadas = [0]

                def objetivo(y):
                    llamadas[0] += 1
                    rp = exp(y)
                    punto = evaluar_punto(T1, T3, gamma, cp, rp, p1, ec, et, delta)
                    return -punto["trabajo_neto"]  # Trabajo con signo, como el método propio.

                resultado = scipy_optimize.minimize_scalar(
                    objetivo, bounds=(ylo+margen, yhi-margen), method="bounded",
                    options={"xatol": self.XATOL_LOG, "maxiter": 500})
                self.assertEqual(llamadas[0], resultado.nfev)
                aceptado = self._aceptar_maximo_scipy(resultado, dominio,
                                                       parametros, "trabajo_neto")
                self.assertIsNotNone(aceptado, f"{nombre}: SciPy no resuelve un máximo motor interior")
                rp_scipy, punto_scipy = aceptado
                trabajo_scipy = punto_scipy["trabajo_neto"]
                trabajo_propio = propio["ciclo"]["trabajo_neto"]
                error_rp = abs(propio["rp"] - rp_scipy)
                error_w = abs(trabajo_propio - trabajo_scipy)
                self.assertLessEqual(error_rp,
                    self.ATOL_RP_OPT+self.RTOL_RP_OPT*max(propio["rp"], rp_scipy),
                    f"{nombre}: error rp={error_rp:.3g}, relativo={error_rp/rp_scipy:.3g}")
                self.assertLessEqual(error_w,
                    self.ATOL_TRABAJO+self.RTOL_TRABAJO*max(
                        abs(trabajo_scipy), abs(trabajo_propio), cp*T3/1000),
                    f"{nombre}: error W={error_w:.3g} kJ/kg; relativo={error_w/abs(trabajo_scipy):.3g}")
                self.assertGreater(propio["evaluaciones"], 0)
                self.assertGreater(resultado.nfev, 0)
                self.assertGreater(propio["resolucion_rp"], 0)

    @unittest.skipIf(scipy_optimize is None, "SciPy no instalado: comparaciones omitidas")
    def test_maximo_rendimiento_noideal_con_bounded(self):
        for nombre, T1, T3, gamma, cp, p1, ec, et, delta in self.CASOS_NO_IDEALES:
            with self.subTest(caso=nombre):
                parametros = (T1, T3, gamma, cp, p1, ec, et, delta)
                propio = buscar_maximo_rendimiento_numerico(
                    *parametros, tolerancia_log=self.XATOL_LOG)
                self.assertEqual(propio["estado"], "maximo_interior")
                dominio = propio["dominio"]
                ylo, yhi = (log(x) for x in dominio["intervalo"])
                margen = self.MARGEN_LOG*(yhi-ylo)
                llamadas = [0]

                def objetivo(y):
                    llamadas[0] += 1
                    punto = evaluar_punto(T1, T3, gamma, cp, exp(y), p1, ec, et, delta)
                    return -punto["rendimiento"] if punto["viable"] else float("inf")

                resultado = scipy_optimize.minimize_scalar(
                    objetivo, bounds=(ylo+margen, yhi-margen), method="bounded",
                    options={"xatol": self.XATOL_LOG, "maxiter": 500})
                self.assertEqual(resultado.nfev, llamadas[0])
                aceptado = self._aceptar_maximo_scipy(resultado, dominio,
                                                       parametros, "rendimiento")
                self.assertIsNotNone(aceptado, f"{nombre}: SciPy no demuestra máximo motor interior")
                rp_scipy, punto_scipy = aceptado
                eta_scipy = punto_scipy["rendimiento"]
                eta_propia = propio["ciclo"]["rendimiento"]
                error_rp = abs(propio["rp"] - rp_scipy)
                error_eta = abs(eta_propia - eta_scipy)
                self.assertLessEqual(error_rp,
                    self.ATOL_RP_OPT+self.RTOL_RP_OPT*max(propio["rp"], rp_scipy),
                    f"{nombre}: error rp={error_rp:.3g}; relativo={error_rp/rp_scipy:.3g}")
                self.assertLessEqual(error_eta,
                    self.ATOL_ETA+self.RTOL_ETA*abs(eta_scipy),
                    f"{nombre}: error eta={error_eta:.3g}; relativo={error_eta/eta_scipy:.3g}")
                self.assertGreater(propio["evaluaciones"], 0)
                self.assertGreater(resultado.nfev, 0)

    @unittest.skipIf(scipy_optimize is None, "SciPy no instalado: comparaciones omitidas")
    def test_rendimiento_ideal_es_supremo_no_maximo(self):
        _, T1, T3, gamma, cp, p1, ec, et, delta = self.CASO_IDEAL
        parametros = (T1, T3, gamma, cp, p1, ec, et, delta)
        propio = buscar_maximo_rendimiento_numerico(*parametros)
        self.assertEqual(propio["estado"], "supremo_no_alcanzado")
        self.assertFalse(propio["supremo"]["alcanzado"])
        dominio = calcular_dominios(*parametros)["ideal"]
        ylo, yhi = (log(x) for x in dominio["intervalo"])
        margen = self.MARGEN_LOG*(yhi-ylo)

        def objetivo(y):
            punto = evaluar_punto(T1, T3, gamma, cp, exp(y), p1, ec, et, delta)
            return -punto["rendimiento"] if punto["viable"] else float("inf")

        resultado = scipy_optimize.minimize_scalar(
            objetivo, bounds=(ylo+margen, yhi-margen), method="bounded",
            options={"xatol": self.XATOL_LOG, "maxiter": 500})
        self.assertTrue(resultado.success)
        self.assertGreater(resultado.x, yhi-.01*(yhi-ylo))
        self.assertIsNone(self._aceptar_maximo_scipy(
            resultado, dominio, parametros, "rendimiento"))

    def test_dominio_vacio_se_distingue_de_fallo_numerico(self):
        parametros = (300, 600, 1.4, 1005, 100, .5, .5, 0)
        dominio = calcular_dominios(*parametros)["noideal"]
        self.assertEqual(dominio["intervalo"], ())
        self.assertIsNone(buscar_maximo_numerico(*parametros, dominio=dominio))
        rendimiento = buscar_maximo_rendimiento_numerico(*parametros)
        self.assertEqual(rendimiento["estado"], "sin_dominio")
        self.assertIsNone(rendimiento["rp"])

    @unittest.skipIf(scipy_optimize is None, "SciPy no instalado: comparaciones omitidas")
    def test_intervalos_sin_cambio_de_signo(self):
        funcion = lambda x: x*x + 1
        with self.assertRaises(ValueError):
            bisectar_raiz(funcion, 1, 2, tolerancia=self.XTOL)
        for metodo in (scipy_optimize.bisect, scipy_optimize.brentq):
            with self.subTest(metodo=metodo.__name__), self.assertRaises(ValueError):
                metodo(funcion, 1, 2, xtol=self.XTOL,
                       rtol=self.RTOL_RAIZ, maxiter=100)

    def test_convergencia_y_viabilidad_no_son_equivalentes(self):
        _, T1, T3, gamma, cp, p1, ec, et, delta = self.CASOS_NO_IDEALES[0]
        parametros = (T1, T3, gamma, cp, p1, ec, et, delta)
        dominio = calcular_dominios(*parametros)["noideal"]
        lo, hi = dominio["intervalo"]
        ylo, yhi = log(lo), log(hi)
        # Resultados sintéticos: verifican el filtro sin depender de maxiter/nfev.
        no_convergido = SimpleNamespace(success=False, x=(ylo+yhi)/2, fun=-1)
        no_motor = SimpleNamespace(success=True, x=yhi, fun=-1)
        no_finito = SimpleNamespace(success=True, x=float("nan"), fun=-1)
        sin_maximo = SimpleNamespace(success=True, x=ylo+.1*(yhi-ylo), fun=-1)
        for etiqueta, resultado in (("no_convergido", no_convergido),
                                    ("frontera", no_motor),
                                    ("no_finito", no_finito),
                                    ("punto_no_estacionario", sin_maximo)):
            with self.subTest(caso=etiqueta):
                self.assertIsNone(self._aceptar_maximo_scipy(
                    resultado, dominio, parametros, "trabajo_neto"))


if __name__ == "__main__":
    unittest.main()
