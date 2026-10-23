"""Contrastes independientes de Sensibilidad OFAT (no modifican producción).

Temperaturas K; cp J/(kg·K); energía kJ/kg; eficiencia como fracción.
Los oráculos de R y A proceden de expresiones termodinámicas escritas aquí;
la búsqueda de B usa SciPy únicamente si está instalado.
"""

from importlib.util import find_spec
from math import exp, log, sqrt
import unittest

import numpy as np

from main import PARAMETROS_PREDETERMINADOS
from sensibilidad import analizar_sensibilidad, evaluar_muestra
from viabilidad import calcular_dominios


def referencia_independiente(p, rp):
    """Estados y energía del gas perfecto, sin llamar al simulador."""
    t1, t3 = p["T1"], p["T3"]
    ec, et = p["eta_c"], p["eta_t"]
    delta, a = p["perdida_presion_combustor"], (p["gamma"] - 1) / p["gamma"]
    factor_c = rp ** a
    factor_t = (rp * (1 - delta)) ** (-a)
    t2 = t1 * (1 + (factor_c - 1) / ec)
    t4 = t3 * (1 - et * (1 - factor_t))
    k = p["cp"] / 1000
    wc, wt = k * (t2 - t1), k * (t3 - t4)
    w, q = wt - wc, k * (t3 - t2)
    motor = rp > 1 and rp * (1 - delta) > 1 and q > 0 and w > 0
    return {"temperaturas": (t1, t2, t3, t4), "trabajo_compresor": wc,
            "trabajo_turbina": wt, "trabajo_neto": w, "calor_aportado": q,
            "rendimiento": w / q if motor else None, "motor": motor}


def gradientes_r(p, rp, parametro):
    """dW/dx, dQ/dx, dη/dx a rp constante; x es un parámetro OFAT."""
    t1, t3 = p["T1"], p["T3"]
    ec, et = p["eta_c"], p["eta_t"]
    delta, a, k = p["perdida_presion_combustor"], (p["gamma"] - 1) / p["gamma"], p["cp"] / 1000
    u = rp ** a
    v = (rp * (1 - delta)) ** (-a)
    derivadas = {
        "T1": (-k * (u - 1) / ec, -k * (1 + (u - 1) / ec)),
        "T3": (k * et * (1 - v), k),
        "eta_c": (k * t1 * (u - 1) / ec**2, k * t1 * (u - 1) / ec**2),
        "eta_t": (k * t3 * (1 - v), 0.),
        "delta": (-k * et * t3 * a * v / (1 - delta), 0.),
    }
    dw, dq = derivadas[parametro]
    ref = referencia_independiente(p, rp)
    if not ref["motor"]:
        raise ValueError("El gradiente del rendimiento requiere un punto motor.")
    w, q = ref["trabajo_neto"], ref["calor_aportado"]
    return dw, dq, (dw * q - w * dq) / q**2


def rp_max_trabajo_independiente(p):
    """Estacionariedad analítica de W en rp, sin consultar optimizacion.py."""
    a = (p["gamma"] - 1) / p["gamma"]
    x = sqrt(p["eta_c"] * p["eta_t"] * p["T3"] / p["T1"]
             * (1 - p["perdida_presion_combustor"]) ** (-a))
    return x ** (1 / a)


class VerificacionSensibilidadIndependiente(unittest.TestCase):
    def setUp(self):
        self.base = PARAMETROS_PREDETERMINADOS.copy()

    def test_r_estados_y_energia_con_dos_modelos_no_ideales(self):
        casos = (self.base, {**self.base, "T1": 300., "T3": 1200.,
                            "gamma": 1.33, "cp": 1100., "p1": 90.,
                            "relacion_presiones": 6., "eta_c": .9,
                            "eta_t": .94, "perdida_presion_combustor": .03})
        for p in casos:
            with self.subTest(rp=p["relacion_presiones"], gamma=p["gamma"]):
                ref = referencia_independiente(p, p["relacion_presiones"])
                r = evaluar_muestra(p)["R"]
                self.assertTrue(ref["motor"])
                self.assertEqual(r["estado"], "disponible")
                for encontrado, esperado in zip(r["ciclo"]["temperaturas"], ref["temperaturas"]):
                    self.assertAlmostEqual(encontrado, esperado, delta=1e-9)
                for magnitud in ("trabajo_compresor", "trabajo_turbina", "trabajo_neto",
                                 "calor_aportado", "rendimiento"):
                    self.assertAlmostEqual(r["ciclo"][magnitud], ref[magnitud], delta=2e-10)

    def test_r_derivadas_analiticas_y_elasticidades_cinco_parametros(self):
        ventanas = {"T1": (270., 310.), "T3": (1450., 1750.),
                    "eta_c": (.8, .9), "eta_t": (.85, .95), "delta": (.02, .08)}
        claves = {"T1": "T1", "T3": "T3", "eta_c": "eta_c", "eta_t": "eta_t",
                  "delta": "perdida_presion_combustor"}
        for parametro, (lo, hi) in ventanas.items():
            with self.subTest(parametro=parametro):
                estudio = analizar_sensibilidad(self.base, parametro, lo, hi, 3)
                dw, dq, deta = gradientes_r(self.base, self.base["relacion_presiones"], parametro)
                x = self.base[claves[parametro]]
                ref = referencia_independiente(self.base, self.base["relacion_presiones"])
                for magnitud, esperado in (("trabajo_neto", dw), ("calor_aportado", dq),
                                            ("rendimiento", deta)):
                    observado = estudio["sensibilidades"]["R"][magnitud]
                    self.assertEqual(observado["metodo"], "central")
                    self.assertIsNotNone(observado["derivada"])
                    self.assertAlmostEqual(observado["derivada"], esperado,
                                           delta=2e-6 * max(1., abs(esperado)))
                    elasticidad = x * esperado / ref[magnitud]
                    self.assertAlmostEqual(observado["normalizada"], elasticidad,
                                           delta=2e-6 * max(1., abs(elasticidad)))
                if parametro in ("T1", "delta"):
                    self.assertLess(dw, 0)
                else:
                    self.assertGreater(dw, 0)

    def test_fronteras_eta_c_uno_y_delta_cero_derivadas_unilaterales(self):
        for parametro, cambio, ventana, sentido in (
                ("eta_c", {"eta_c": 1.}, (.8, 1.), "atrás"),
                ("delta", {"perdida_presion_combustor": 0.}, (0., .1), "adelante")):
            with self.subTest(parametro=parametro):
                p = {**self.base, **cambio}
                estudio = analizar_sensibilidad(p, parametro, *ventana, 3)
                dw, dq, deta = gradientes_r(p, p["relacion_presiones"], parametro)
                for magnitud, esperado in (("trabajo_neto", dw), ("calor_aportado", dq),
                                            ("rendimiento", deta)):
                    salida = estudio["sensibilidades"]["R"][magnitud]
                    self.assertIn(sentido, salida["metodo"])
                    self.assertAlmostEqual(salida["derivada"], esperado,
                                           delta=3e-6 * max(1., abs(esperado)))
                    if parametro == "delta":
                        self.assertIsNone(salida["normalizada"])
                        self.assertIn("x=0", salida["motivo"])

    def test_a_optimo_analitico_independiente_y_teorema_envolvente(self):
        for p in (self.base, {**self.base, "T1": 300., "T3": 1200.,
                             "gamma": 1.33, "cp": 1100., "p1": 90.,
                             "relacion_presiones": 6., "eta_c": .9,
                             "eta_t": .94, "perdida_presion_combustor": .03}):
            rp = rp_max_trabajo_independiente(p)
            referencia = referencia_independiente(p, rp)
            salida = evaluar_muestra(p)["A"]
            self.assertTrue(referencia["motor"])
            self.assertEqual(salida["estado"], "disponible")
            self.assertAlmostEqual(salida["rp"], rp, delta=2e-9 * rp)
            self.assertAlmostEqual(salida["trabajo_neto"], referencia["trabajo_neto"], delta=2e-10)
        for parametro, ventana in (("T3", (1450., 1750.)), ("delta", (.02, .08))):
            with self.subTest(parametro=parametro):
                estudio = analizar_sensibilidad(self.base, parametro, *ventana, 3)
                rp = rp_max_trabajo_independiente(self.base)
                esperado = gradientes_r(self.base, rp, parametro)[0]
                obtenido = estudio["sensibilidades"]["A"]["trabajo_neto"]
                self.assertAlmostEqual(obtenido["derivada"], esperado,
                                       delta=2e-6 * max(1., abs(esperado)))

    @unittest.skipUnless(find_spec("scipy") is not None, "SciPy opcional no instalado")
    def test_b_maximo_interior_con_scipy_independiente(self):
        from scipy.optimize import minimize_scalar

        casos = (self.base, {**self.base, "T1": 300., "T3": 1200.,
                            "gamma": 1.33, "cp": 1100., "p1": 90.,
                            "relacion_presiones": 6., "eta_c": .9,
                            "eta_t": .94, "perdida_presion_combustor": .03})
        for p in casos:
            with self.subTest(T3=p["T3"], gamma=p["gamma"]):
                args = (p["T1"], p["T3"], p["gamma"], p["cp"], p["p1"],
                        p["eta_c"], p["eta_t"], p["perdida_presion_combustor"])
                inferior, superior = calcular_dominios(*args)["noideal"]["intervalo"]
                ventana = (log(inferior) + 1e-7, log(superior) - 1e-7)
                def objetivo(y):
                    return -referencia_independiente(p, exp(y))["rendimiento"]
                minimo = minimize_scalar(objetivo, method="bounded", bounds=ventana,
                                         options={"xatol": 1e-10, "maxiter": 500})
                self.assertTrue(minimo.success)
                rp_b = exp(minimo.x)
                ref = referencia_independiente(p, rp_b)
                self.assertTrue(inferior < rp_b < superior and ref["motor"])
                salida = evaluar_muestra(p)["B"]
                self.assertEqual(salida["estado"], "disponible")
                self.assertAlmostEqual(salida["rp"], rp_b, delta=2e-6 * rp_b)
                self.assertAlmostEqual(salida["rendimiento"], ref["rendimiento"], delta=2e-9)

    def test_orden_r_a_b_con_referencias_fisicas_independientes(self):
        for p in (self.base, {**self.base, "T3": 1850., "eta_c": .92,
                             "eta_t": .96, "perdida_presion_combustor": .09}):
            salida = evaluar_muestra(p)
            self.assertTrue(all(salida[k]["estado"] == "disponible" for k in "RAB"))
            referencias = {k: referencia_independiente(p, salida[k]["rp"]) for k in "RAB"}
            self.assertTrue(all(ref["motor"] for ref in referencias.values()))
            for k in "RAB":
                self.assertAlmostEqual(salida[k]["trabajo_neto"],
                                       referencias[k]["trabajo_neto"], delta=2e-10)
                self.assertAlmostEqual(salida[k]["rendimiento"],
                                       referencias[k]["rendimiento"], delta=2e-12)
            self.assertGreaterEqual(referencias["A"]["trabajo_neto"] + 1e-8,
                                    max(ref["trabajo_neto"] for ref in referencias.values()))
            self.assertGreaterEqual(referencias["B"]["rendimiento"] + 1e-10,
                                    max(ref["rendimiento"] for ref in referencias.values()))

    def test_r_no_motor_y_dominio_vacio_no_inventan_elasticidad(self):
        p = {**self.base, "relacion_presiones": 300.}
        ref = referencia_independiente(p, 300.)
        self.assertFalse(ref["motor"])
        estudio = analizar_sensibilidad(p, "T3", 1500., 1700., 3)
        self.assertEqual(estudio["referencia_local"]["R"]["estado"], "inviable")
        self.assertIsNone(estudio["referencia_local"]["R"]["rp"])
        self.assertTrue(np.isnan(estudio["curvas"]["R"]["rp"]).all())
        self.assertIsNone(estudio["sensibilidades"]["R"]["rendimiento"]["derivada"])
        self.assertEqual(p["relacion_presiones"], 300.)
        vacio = {**self.base, "T1": 300., "T3": 400., "relacion_presiones": 2.,
                 "perdida_presion_combustor": .5}
        r = evaluar_muestra(vacio)
        self.assertFalse(referencia_independiente(vacio, 2.)["motor"])
        self.assertEqual((r["A"]["estado"], r["B"]["estado"]), ("sin_dominio", "sin_dominio"))
        self.assertIsNone(r["R"]["rendimiento"])

    def test_ideal_rendimiento_creciente_y_b_supremo_no_alcanzado(self):
        p = {**self.base, "eta_c": 1., "eta_t": 1., "perdida_presion_combustor": 0.}
        estudio = analizar_sensibilidad(p, "T3", 1450., 1750., 3)
        a = (p["gamma"] - 1) / p["gamma"]
        for r in estudio["registros"]:
            b = r["B"]
            self.assertEqual(b["estado"], "supremo_no_alcanzado")
            self.assertIsNone(b["rp"])
            self.assertAlmostEqual(b["supremo"]["rendimiento"], 1 - p["T1"] / r["parametros"]["T3"],
                                   delta=2e-12)
            limite = (r["parametros"]["T3"] / p["T1"]) ** (1 / a)
            eta_1 = referencia_independiente(r["parametros"], 10.)["rendimiento"]
            eta_2 = referencia_independiente(r["parametros"], sqrt(10. * limite))["rendimiento"]
            self.assertLess(eta_1, eta_2)
            self.assertLess(eta_2, b["supremo"]["rendimiento"])
        self.assertTrue(np.isnan(estudio["curvas"]["B"]["rendimiento"]).all())


if __name__ == "__main__":
    unittest.main()
