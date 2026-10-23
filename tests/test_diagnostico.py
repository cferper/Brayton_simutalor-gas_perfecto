"""Diagnósticos calculados sobre datos actuales; no son validación externa."""

from copy import deepcopy
import json
from math import isclose, log
from unittest import TestCase
from unittest.mock import patch

from diagnostico import _comparar, diagnosticar_ciclo, diagnosticar_optimizacion
from main import PARAMETROS_PREDETERMINADOS
from optimizacion import optimizar_trabajo_neto
from optimizacion_rendimiento import optimizar_rendimiento
from segunda_ley import analizar_segunda_ley
from sensibilidad import evaluar_muestra
from viabilidad import evaluar_punto


class DiagnosticoFisicoTests(TestCase):
    def setUp(self):
        self.p = PARAMETROS_PREDETERMINADOS.copy()
        p = self.p
        args = tuple(p[k] for k in ("T1", "T3", "gamma", "cp", "relacion_presiones", "p1"))
        self.ciclos = {"ideal": evaluar_punto(*args),
                       "noideal": evaluar_punto(*args, p["eta_c"], p["eta_t"], p["perdida_presion_combustor"])}
        self.sl = analizar_segunda_ley(self.ciclos, p["cp"], p["gamma"])

    def filas(self, modelo="noideal", ciclo=None, parametros=None, con_segunda_ley=True):
        """Devuelve dict id->fila para comprobar relaciones sin depender del HTML."""
        return {f["id"]: f for f in diagnosticar_ciclo(
            parametros or self.p, self.ciclos[modelo] if ciclo is None else ciclo,
            modelo=modelo, segunda_ley=self.sl["modelos"][modelo] if con_segunda_ley else None,
            T0=self.sl["T0"] if con_segunda_ley else None)}

    def test_ideal_viable_y_referencia_cerrada_independiente(self):
        filas = self.filas("ideal")
        self.assertFalse([f for f in filas.values() if f["estado"] == "atencion"])
        # Referencia calculada directamente con las entradas, sin evaluador.
        p = self.p
        x = p["relacion_presiones"] ** ((p["gamma"] - 1) / p["gamma"])
        t2, t4 = p["T1"] * x, p["T3"] / x
        qout = p["cp"] * (t4 - p["T1"]) / 1000
        referencia = p["cp"] * (p["T3"] - t2) / 1000 - qout
        self.assertTrue(isclose(filas["balance_calores"]["referencia"], referencia, rel_tol=1e-13))
        self.assertAlmostEqual(filas["rendimiento_ideal"]["referencia"], 1 - 1 / x, places=14)
        self.assertEqual(filas["balance_trabajos"]["naturaleza"], "identidad")
        self.assertEqual(filas["rendimiento_ideal"]["naturaleza"], "contraste")
        self.assertEqual(filas["segunda_ley_global"]["estado"], "no_evaluable")

    def test_noideal_viable_y_segunda_ley_con_datos(self):
        filas = self.filas()
        self.assertFalse([f for f in filas.values() if f["estado"] == "atencion"])
        for clave in ("balance_trabajos", "balance_calores", "eta_c", "eta_t", "sgen_compresor_signo",
                      "exergia_turbina", "exergia_compresor_balance", "exergia_suma"):
            self.assertEqual(filas[clave]["estado"], "cumple", clave)
        p = self.p
        x = p["relacion_presiones"] ** ((p["gamma"] - 1) / p["gamma"])
        sgen_c = p["cp"] / 1000 * log((1 + (x - 1) / p["eta_c"]) / x)
        self.assertAlmostEqual(filas["sgen_compresor_estados"]["referencia"], sgen_c, places=13)
        self.assertEqual(filas["segunda_ley_camara"]["estado"], "no_evaluable")
        self.assertIn("no es su generación", filas["segunda_ley_camara"]["motivo"])

    def test_trabajo_alterado_no_se_sustituye_por_recalculo(self):
        ciclo = deepcopy(self.ciclos["noideal"])
        ciclo["trabajo_neto"] += 2.
        filas = self.filas(ciclo=ciclo)
        self.assertEqual(filas["balance_trabajos"]["estado"], "atencion")
        self.assertAlmostEqual(filas["balance_trabajos"]["residuo"], 2., places=10)
        self.assertEqual(filas["balance_trabajos"]["valor"], ciclo["trabajo_neto"])
        self.assertEqual(filas["balance_calores"]["estado"], "atencion")
        self.assertEqual(filas["rendimiento"]["estado"], "atencion")

    def test_clasificacion_viable_ausente_o_no_booleana_no_es_exito(self):
        ciclo = deepcopy(self.ciclos["noideal"])
        ciclo["viable"] = None
        self.assertEqual(self.filas(ciclo=ciclo)["clasificacion_motor"]["estado"], "no_evaluable")
        for valor in ("False", 1, 0):
            with self.subTest(valor=valor):
                ciclo["viable"] = valor
                fila = self.filas(ciclo=ciclo)["clasificacion_motor"]
                self.assertEqual(fila["estado"], "atencion")
                json.dumps(fila, allow_nan=False)

    def test_estados_presiones_y_eficiencias_alterados(self):
        ciclo = deepcopy(self.ciclos["noideal"])
        ciclo["T2s"] += 5
        ciclo["presiones"] = (100., 1000., 900., 100.)
        filas = self.filas(ciclo=ciclo)
        self.assertEqual(filas["T2s"]["estado"], "atencion")
        self.assertEqual(filas["presion_3"]["estado"], "atencion")
        self.assertEqual(filas["T4s"]["estado"], "atencion")

    def test_ciclo_no_motor_conserva_balance_y_no_inventa_cocientes(self):
        p = {**self.p, "relacion_presiones": 200.}
        c = evaluar_punto(p["T1"], p["T3"], p["gamma"], p["cp"], 200., p["p1"],
                          p["eta_c"], p["eta_t"], p["perdida_presion_combustor"])
        filas = self.filas(ciclo=c, parametros=p, con_segunda_ley=False)
        self.assertEqual(filas["motor_trabajo_neto"]["estado"], "atencion")
        self.assertEqual(filas["balance_trabajos"]["estado"], "cumple")
        self.assertEqual(filas["balance_calores"]["estado"], "cumple")
        self.assertEqual(filas["rendimiento"]["estado"], "no_evaluable")
        self.assertIsNone(filas["rendimiento"]["valor"])
        self.assertEqual(filas["clasificacion_motor"]["estado"], "cumple")

    def test_frontera_de_compresion_no_define_eficiencia(self):
        p = {**self.p, "relacion_presiones": 1.}
        c = evaluar_punto(p["T1"], p["T3"], p["gamma"], p["cp"], 1., p["p1"])
        filas = self.filas("ideal", c, p, False)
        self.assertEqual(filas["motor_compresion"]["estado"], "atencion")
        self.assertEqual(filas["eta_c"]["estado"], "no_evaluable")
        self.assertEqual(filas["eta_t"]["estado"], "no_evaluable")

    def test_tolerancias_absoluta_y_relativa_no_universal(self):
        kwargs = dict(identificador="prueba", nombre="Tolerancia", grupo="Ensayo", relacion="x=y",
                      unidad="kJ/kg", explicacion="Prueba de las dos ramas del criterio.", atol=1e-10, rtol=1e-9)
        absoluto = _comparar(valor=5e-11, referencia=0., **kwargs)
        relativo = _comparar(valor=1e6 + 5e-4, referencia=1e6, **kwargs)
        fuera = _comparar(valor=1e6 + 2e-3, referencia=1e6, **kwargs)
        self.assertEqual(absoluto["tolerancia"], 1e-10)
        self.assertEqual(absoluto["estado"], "cumple")
        self.assertGreater(relativo["tolerancia"], 9.99e-4)
        self.assertEqual(relativo["estado"], "cumple")
        self.assertEqual(fuera["estado"], "atencion")
        filas = self.filas()
        self.assertNotEqual(filas["balance_trabajos"]["tolerancia"], filas["rendimiento"]["tolerancia"])
        self.assertEqual(filas["motor_trabajo_neto"]["tolerancia"], self.ciclos["noideal"]["tolerancias"]["trabajo_neto"])

    def test_segunda_ley_ausente_es_no_evaluable(self):
        filas = self.filas(con_segunda_ley=False)
        for clave in ("entropia_estado_2", "sgen_compresor_estados", "sgen_turbina_signo",
                      "exergia_compresor", "exergia_suma"):
            self.assertEqual(filas[clave]["estado"], "no_evaluable", clave)
            self.assertIsNone(filas[clave]["valor"])

    def test_sl_sin_energias_no_recalcula_ni_declara_no_motor(self):
        sl = self.sl["modelos"]["noideal"]
        with patch("diagnostico.evaluar_punto", side_effect=AssertionError("No debe recalcular estados")):
            filas = {f["id"]: f for f in diagnosticar_ciclo(self.p, sl, segunda_ley=sl, T0=300.)}
        self.assertEqual(filas["clasificacion_motor"]["estado"], "no_evaluable")
        self.assertIsNone(filas["balance_trabajos"]["valor"])
        self.assertEqual(filas["balance_trabajos"]["estado"], "no_evaluable")
        self.assertEqual(filas["exergia_compresor_balance"]["estado"], "no_evaluable")
        # Se conserva eD para 288.15 K: cambiar sólo el argumento debe advertir.
        self.assertEqual(filas["exergia_compresor"]["estado"], "atencion")

    def test_bandas_guardadas_evitan_recalcular_ciclos(self):
        with patch("diagnostico.evaluar_punto", side_effect=AssertionError("Bandas ya disponibles")):
            self.assertEqual(self.filas()["motor_expansion"]["estado"], "cumple")

    def test_segunda_ley_alterada_detecta_entropias_y_exergia(self):
        sl = deepcopy(self.sl["modelos"]["noideal"])
        sl["entropias"] = (0., 4., 5., 6.)
        sl["componentes"]["turbina"]["exergia_destruida"] += 1.
        filas = {f["id"]: f for f in diagnosticar_ciclo(self.p, self.ciclos["noideal"], segunda_ley=sl, T0=self.sl["T0"])}
        self.assertEqual(filas["entropia_estado_2"]["estado"], "atencion")
        self.assertEqual(filas["exergia_turbina"]["estado"], "atencion")
        self.assertEqual(filas["exergia_suma"]["estado"], "atencion")
        self.assertEqual(filas["exergia_compresor_balance"]["estado"], "atencion")

    def test_negativos_de_redondeo_y_violation_de_segunda_ley(self):
        sl = deepcopy(self.sl["modelos"]["ideal"])
        c = sl["componentes"]["compresor"]
        c.update(bruto=-5e-11, valor=0., exergia_destruida=0.)
        filas = {f["id"]: f for f in diagnosticar_ciclo(self.p, self.ciclos["ideal"], "ideal", segunda_ley=sl, T0=self.sl["T0"])}
        self.assertEqual(filas["sgen_compresor_signo"]["estado"], "cumple")
        self.assertEqual(filas["sgen_compresor_corregida"]["estado"], "cumple")
        c["bruto"] = -5e-6
        filas = {f["id"]: f for f in diagnosticar_ciclo(self.p, self.ciclos["ideal"], "ideal", segunda_ley=sl, T0=self.sl["T0"])}
        self.assertEqual(filas["sgen_compresor_signo"]["estado"], "atencion")
        self.assertEqual(filas["sgen_compresor_corregida"]["estado"], "no_evaluable")

    def test_valores_no_finitos_son_advertencia_serializable(self):
        for valor in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(valor=valor):
                ciclo = deepcopy(self.ciclos["noideal"])
                ciclo["trabajo_neto"] = valor
                ciclo["tolerancias"]["trabajo_neto"] = valor
                filas = self.filas(ciclo=ciclo)
                self.assertEqual(filas["balance_trabajos"]["estado"], "atencion")
                json.dumps(list(filas.values()), allow_nan=False)

    def test_ausencia_y_limite_numerico_no_son_inviabilidad_fisica(self):
        filas = self.filas(ciclo={}, con_segunda_ley=False)
        self.assertFalse([f for f in filas.values() if f["estado"] == "atencion"])
        self.assertEqual(filas["motor_trabajo_neto"]["estado"], "no_evaluable")
        sl = {"estado": "limite_numerico", "motivo": "Desbordamiento deliberado"}
        filas = {f["id"]: f for f in diagnosticar_ciclo(self.p, {}, segunda_ley=sl)}
        self.assertEqual(filas["segunda_ley_estado"]["estado"], "atencion")
        self.assertIn("no equivale", filas["segunda_ley_estado"]["explicacion"])

    def test_maximos_interiores_usan_concordancia_real(self):
        p = self.p
        args = tuple(p[k] for k in ("T1", "T3", "gamma", "cp", "p1", "eta_c", "eta_t", "perdida_presion_combustor"))
        for objetivo, optimizador in (("trabajo", optimizar_trabajo_neto), ("rendimiento", optimizar_rendimiento)):
            with self.subTest(objetivo=objetivo):
                estudio = optimizador(*args)
                filas = diagnosticar_optimizacion(p, estudio, objetivo=objetivo)
                self.assertTrue(all(f["estado"] == "cumple" for f in filas))
                estudio["analitico"]["rp"] = estudio["dominio"]["intervalo"][0]
                filas = diagnosticar_optimizacion(p, estudio, objetivo=objetivo)
                self.assertEqual(filas[0]["estado"], "atencion")
                self.assertIn("frontera", filas[0]["valor"])

    def test_supremo_reversible_no_se_trata_como_maximo(self):
        p = self.p
        estudio = optimizar_rendimiento(p["T1"], p["T3"], p["gamma"], p["cp"], p["p1"])
        filas = diagnosticar_optimizacion(p, estudio, "ideal", "rendimiento")
        self.assertEqual(filas[0]["estado"], "cumple")
        self.assertEqual(filas[0]["valor"], "Supremo no alcanzado")
        self.assertEqual(filas[-1]["estado"], "no_evaluable")
        estudio["supremo"]["alcanzado"] = True
        self.assertEqual(diagnosticar_optimizacion(p, estudio, "ideal", "rendimiento")[0]["estado"], "atencion")

    def test_registros_ofat_reutilizan_residuos_sin_inventar_busqueda(self):
        for verificar in (False, True):
            muestra = evaluar_muestra(self.p, verificar=verificar)
            for escenario, objetivo in (("A", "trabajo"), ("B", "rendimiento")):
                with self.subTest(verificar=verificar, escenario=escenario):
                    registro = {**muestra[escenario], "dominio": muestra["dominios"]["noideal"]}
                    filas = diagnosticar_optimizacion(self.p, registro, objetivo=objetivo)
                    self.assertEqual(filas[0]["estado"], "cumple")
                    self.assertTrue(all(f["estado"] == ("cumple" if verificar else "no_evaluable") for f in filas[1:]))
                    if verificar:
                        self.assertIn("residuo", filas[1]["explicacion"])

    def test_optimizacion_vacia_y_limite_no_son_maximos(self):
        filas = diagnosticar_optimizacion(self.p, {"estado": "sin_dominio", "motivo": "Dominio vacío"})
        self.assertEqual(filas[0]["estado"], "no_evaluable")
        filas = diagnosticar_optimizacion(self.p, {"estado": "limite_numerico", "motivo": "Fallo de convergencia"})
        self.assertEqual(filas[0]["estado"], "atencion")
        self.assertNotIn("motor", filas[0]["motivo"])

    def test_contrato_completo_y_entradas_de_modelo(self):
        requeridas = {"id", "nombre", "grupo", "relacion", "valor", "referencia", "residuo",
                      "residuo_relativo", "tolerancia", "unidad", "estado", "explicacion", "motivo",
                      "criterio", "naturaleza", "comparacion"}
        filas = self.filas()
        self.assertTrue(all(requeridas <= f.keys() for f in filas.values()))
        self.assertTrue(all(f["estado"] in ("cumple", "atencion", "no_evaluable") for f in filas.values()))
        json.dumps(list(filas.values()), allow_nan=False)
        with self.assertRaises(ValueError):
            diagnosticar_ciclo(self.p, self.ciclos["ideal"], "desconocido")
        with self.assertRaises(ValueError):
            diagnosticar_optimizacion(self.p, {}, objetivo="potencia")
