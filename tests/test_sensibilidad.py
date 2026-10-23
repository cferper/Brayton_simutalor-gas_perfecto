"""OFAT: verificaciones físicas, precisión local e integración sin sockets."""

from contextlib import redirect_stdout
from datetime import datetime
from io import BytesIO, StringIO
from pathlib import Path
from time import perf_counter
import tempfile
import unittest
from unittest.mock import patch

import matplotlib.image as mpimg
import numpy as np

import main
import reporting
import sensibilidad as s
import web_app
from optimizacion import optimizar_trabajo_neto
from optimizacion_rendimiento import optimizar_rendimiento
from test_reporting import InformeParser
from viabilidad import ErrorNumerico, calcular_dominios, evaluar_punto


class SensibilidadTests(unittest.TestCase):
    def setUp(self):
        self.p = main.PARAMETROS_PREDETERMINADOS.copy()

    def test_validacion_rangos_y_controles(self):
        for args in (("otro", 1, 2, 5), ("T3", 0, 2, 5), ("T3", 2, 1, 5),
                     ("T3", 1, np.inf, 5), ("eta_c", 0, 1, 5), ("eta_t", .5, 1.1, 5),
                     ("delta", -.1, .2, 5), ("delta", 0, 1, 5), ("T1", 250, 350, 2),
                     ("T1", 250, 350, 202), ("T1", 250, 350, 5.5), ("T1", 250, 350, True)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                s.validar_configuracion(*args)

    def test_malla_extremos_y_no_mutacion(self):
        c = s.validar_configuracion("T3", 800, 2000, 41)
        antes = c.copy()
        x = s.generar_malla(c)
        self.assertEqual(len(x), 41)
        self.assertEqual((x[0], x[-1]), (800, 2000))
        self.assertTrue(np.all(np.diff(x) > 0))
        self.assertEqual(c, antes)

    def test_ofat_conserva_ocho_parametros(self):
        original = self.p.copy()
        for parametro, opciones in s.PARAMETROS_ESTUDIO.items():
            nuevo = s.construir_parametros(self.p, parametro, opciones["rango"][0])
            for clave in self.p:
                if clave != opciones["clave"]:
                    self.assertEqual(nuevo[clave], self.p[clave])
        self.assertEqual(original, self.p)

    def test_r_a_b_contra_evaluaciones_independientes(self):
        for parametro, valor in (("T3", 1600), ("T3", 5000), ("eta_c", .7), ("delta", .3)):
            p = s.construir_parametros(self.p, parametro, valor)
            r = s.evaluar_muestra(p, verificar=True)
            args = s.argumentos_fisicos(p)
            T1, T3, gamma, cp, p1, ec, et, delta = args
            referencia = evaluar_punto(T1, T3, gamma, cp, p["relacion_presiones"], p1, ec, et, delta)
            self.assertEqual(r["R"]["estado"] == "disponible", referencia["viable"])
            for nombre, solucion in (("A", optimizar_trabajo_neto(*args)),
                                     ("B", optimizar_rendimiento(*args))):
                self.assertAlmostEqual(r[nombre]["rp"], solucion["analitico"]["rp"], places=10)
                self.assertIn("búsqueda numérica independiente", r[nombre]["metodo"])
                self.assertEqual(r[nombre]["ciclo"], solucion["analitico"]["ciclo"])
            self.assertGreaterEqual(r["A"]["trabajo_neto"], r["B"]["trabajo_neto"])
            self.assertGreaterEqual(r["B"]["rendimiento"], r["A"]["rendimiento"])
            if valor == 5000:
                self.assertGreater(r["B"]["rp"], 50)

    def test_dominios_frescos_ideal_y_noideal(self):
        estudio = s.analizar_sensibilidad(self.p, "T3", 500, 5000, 9)
        for r in estudio["registros"]:
            self.assertEqual(r["dominios"], calcular_dominios(*s.argumentos_fisicos(r["parametros"])))
            for nombre in "AB":
                if r[nombre]["rp"] is not None:
                    lo, hi = r["dominios"]["noideal"]["intervalo"]
                    self.assertTrue(lo < r[nombre]["rp"] < hi)
        self.assertNotEqual(estudio["registros"][0]["dominios"], estudio["registros"][-1]["dominios"])

    def test_inviable_conserva_todos_los_motivos(self):
        p = {**self.p, "relacion_presiones": 1.01, "perdida_presion_combustor": .8}
        r = s.evaluar_muestra(p)
        self.assertEqual(r["R"]["estado"], "inviable")
        self.assertGreaterEqual(len(r["R"]["motivos"]), 2)
        self.assertIsNone(r["R"]["rendimiento"])
        self.assertFalse(r["R"]["ciclo"]["viable"])

    def test_temperaturas_incompatibles_no_detienen_estudio(self):
        e = s.analizar_sensibilidad(self.p, "T3", 200, 1600, 8)
        self.assertEqual(e["registros"][0]["A"]["estado"], "parametros_inviables")
        self.assertTrue(np.isnan(e["curvas"]["A"]["trabajo_neto"][0]))
        self.assertTrue(np.isfinite(e["curvas"]["A"]["trabajo_neto"][-1]))

    def test_dominio_vacio_no_busca(self):
        p = {**self.p, "T3": 300, "eta_c": .5, "eta_t": .5}
        with patch.object(s, "optimizar_trabajo_neto") as trabajo, patch.object(s, "optimizar_rendimiento") as eta:
            r = s.evaluar_muestra(p, verificar=True)
        self.assertEqual(r["A"]["estado"], "sin_dominio")
        self.assertEqual(r["B"]["estado"], "sin_dominio")
        trabajo.assert_not_called()
        eta.assert_not_called()

    def test_reversible_supremo_no_es_punto_b(self):
        p = {**self.p, "eta_c": 1., "eta_t": 1., "perdida_presion_combustor": 0.}
        e = s.analizar_sensibilidad(p, "T3", 800, 2000, 5)
        for r in e["registros"]:
            self.assertEqual(r["B"]["estado"], "supremo_no_alcanzado")
            self.assertIsNone(r["B"]["rp"])
            self.assertFalse(r["B"]["supremo"]["alcanzado"])
        self.assertTrue(np.isnan(e["curvas"]["B"]["rendimiento"]).all())
        self.assertIsNone(e["sensibilidades"]["B"]["rendimiento"]["derivada"])

    def test_dominio_estrecho_resoluble_y_limite_numerico(self):
        for factor in (1 + 1e-4, 1 + 1e-7):
            p = {**self.p, "T3": self.p["T1"] / (.85 * .9) * factor,
                 "perdida_presion_combustor": 0.}
            r = s.evaluar_muestra(p)
            esperado = "disponible" if factor > 1.00001 else "limite_numerico"
            self.assertEqual(r["A"]["estado"], esperado)
            if esperado != "disponible":
                self.assertIsNone(r["A"]["trabajo_neto"])

    def test_errores_numericos_explicitos_programacion_propaga(self):
        with patch.object(s, "calcular_candidato_rendimiento", side_effect=ErrorNumerico("límite")):
            r = s.evaluar_muestra(self.p)
        self.assertEqual(r["B"]["estado"], "limite_numerico")
        self.assertEqual(r["A"]["estado"], "disponible")
        with patch.object(s, "evaluar_punto", side_effect=ValueError("bug")):
            with self.assertRaisesRegex(ValueError, "bug"):
                s.evaluar_muestra(self.p)

    def test_derivadas_central_con_identidad_analitica(self):
        r = s.calcular_sensibilidad_local(lambda x: x*x, 2., (0., 10.))
        self.assertAlmostEqual(r["derivada"], 4., places=7)
        self.assertAlmostEqual(r["normalizada"], 2., places=7)
        self.assertEqual(r["metodo"], "central")

    def test_derivadas_unilaterales_y_x_cero(self):
        for x, esperado in ((0., "adelante"), (1., "atrás")):
            r = s.calcular_sensibilidad_local(lambda y: 2 + y*y, x, (0., 1.))
            self.assertIn(esperado, r["metodo"])
            self.assertAlmostEqual(r["derivada"], 2*x, places=7)
            if x == 0:
                self.assertIsNone(r["normalizada"])
                self.assertIn("x=0", r["motivo"])

    def test_derivadas_no_ficticias_cero_y_discontinuidad(self):
        for funcion in (lambda x: 1e-15*x, lambda x: x if x >= 2 else None,
                        lambda x: 1. if x >= 2 else 2.):
            r = s.calcular_sensibilidad_local(funcion, 2., (0., 10.))
            self.assertIsNone(r["derivada"])
            self.assertTrue(r["motivo"])

    def test_derivada_rp_a_t3_identidad(self):
        e = s.analizar_sensibilidad(self.p, "T3", 1000, 2000, 5)
        esperado = self.p["gamma"] / (2 * (self.p["gamma"] - 1))
        self.assertAlmostEqual(e["sensibilidades"]["A"]["rp"]["normalizada"], esperado, places=7)
        self.assertAlmostEqual(e["sensibilidades"]["R"]["rp"]["derivada"], 0., places=8)

    def test_eficiencia_en_extremo_y_delta_cero(self):
        for parametro, cambios in (("eta_c", {"eta_c": 1.}), ("delta", {"perdida_presion_combustor": 0.})):
            e = s.analizar_sensibilidad({**self.p, **cambios}, parametro,
                                      *s.PARAMETROS_ESTUDIO[parametro]["rango"], 5)
            r = e["sensibilidades"]["A"]["trabajo_neto"]
            self.assertIsNotNone(r["derivada"])
            self.assertIn("unilateral", r["metodo"])

    def test_no_contaminacion_y_coste_acotado(self):
        inicio = perf_counter()
        primero = s.analizar_sensibilidad(self.p, "T3", 800, 2000, 201)
        s.analizar_sensibilidad(self.p, "eta_c", .6, 1, 5)
        segundo = s.analizar_sensibilidad(self.p, "T3", 800, 2000, 201)
        self.assertTrue(np.array_equal(primero["curvas"]["A"]["rp"], segundo["curvas"]["A"]["rp"]))
        self.assertLess(perf_counter() - inicio, 15.)
        self.assertLessEqual(len(primero["indices_verificacion"]), 4)
        self.assertIn("búsqueda", primero["registros"][0]["A"]["metodo"])
        self.assertNotIn("búsqueda", primero["registros"][1]["A"]["metodo"])

    def test_graficas_conservan_nan_y_dimensiones(self):
        e = s.analizar_sensibilidad(self.p, "T3", 200, 1600, 8)
        import matplotlib.axes
        import matplotlib.figure
        original = matplotlib.axes.Axes.plot
        guardar_original = matplotlib.figure.Figure.savefig
        lineas = []
        limites = []

        def guardar(ejes, x, y, *args, **kwargs):
            lineas.append(np.asarray(y).copy())
            return original(ejes, x, y, *args, **kwargs)

        def guardar_figura(figura, *args, **kwargs):
            limites.append(figura.axes[0].get_xlim())
            return guardar_original(figura, *args, **kwargs)

        with patch.object(matplotlib.axes.Axes, "plot", guardar), \
                patch.object(matplotlib.figure.Figure, "savefig", guardar_figura):
            imagenes = s.crear_graficas_sensibilidad(e)
        self.assertEqual(limites, [(200., 1600.)] * 3)
        self.assertTrue(np.isnan(lineas[0][0]))
        self.assertTrue(np.isfinite(lineas[0][-1]))
        self.assertEqual(len(imagenes), 3)
        for png in imagenes.values():
            pixeles = mpimg.imread(BytesIO(png), format="png")
            self.assertEqual(pixeles.shape[:2], (900, 1350))
            self.assertGreater(float(pixeles.std()), .05)


    def test_consigna_rp_separada_de_resultados_motores_con_t3_inviable(self):
        estudio = s.analizar_sensibilidad(self.p, "T3", 200, 1600, 15)
        mascara_r = np.array([r["R"]["estado"] == "disponible" for r in estudio["registros"]])
        self.assertTrue(mascara_r.any())
        self.assertTrue((~mascara_r).any())
        import matplotlib.figure
        original = matplotlib.figure.Figure.savefig
        trazados = []

        def capturar(figura, *args, **kwargs):
            trazados.append({linea.get_label(): linea for linea in figura.axes[0].lines})
            return original(figura, *args, **kwargs)

        with patch.object(matplotlib.figure.Figure, "savefig", capturar):
            s.crear_graficas_sensibilidad(estudio)
        for k, lineas in zip(("trabajo_neto", "rendimiento", "rp"), trazados):
            for escenario, etiqueta in (("R", "R: puntos motores a rp fija"),
                                        ("A", "A: máximo trabajo"),
                                        ("B", "B: máximo interior de rendimiento")):
                y = lineas[etiqueta].get_ydata()
                esperado = estudio["curvas"][escenario][k] * (100 if k == "rendimiento" else 1)
                np.testing.assert_allclose(y, esperado, equal_nan=True)
                mascara = np.array([r[escenario]["estado"] == "disponible" for r in estudio["registros"]])
                self.assertTrue(np.isnan(y[~mascara]).all())
            consigna = "Consigna rp de referencia (no indica viabilidad)"
            if k == "rp":
                linea = lineas[consigna]
                np.testing.assert_array_equal(linea.get_ydata(), np.full(15, self.p["relacion_presiones"]))
                self.assertEqual(linea.get_color(), "0.5")
                self.assertEqual(linea.get_linestyle(), "-.")
                self.assertEqual(lineas["R: puntos motores a rp fija"].get_marker(), "o")
            else:
                self.assertNotIn(consigna, lineas)


class IntegracionSensibilidadTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.carpeta = Path(self.temporal.name)
        self.config = patch.dict(web_app.app.config, {"OUTPUTS_DIR": self.carpeta,
            "TESTING": False, "PROPAGATE_EXCEPTIONS": False})
        self.config.start()
        self.addCleanup(self.config.stop)
        self.client = web_app.app.test_client()
        self.datos = {k: str(v) for k, v in web_app.valores_formulario().items()}
        self.datos.update(accion="sensibilidad", sens_parametro="T3", sens_minimo="200",
                          sens_maximo="1600", sens_muestras="5")

    def test_flask_estudio_descarga_y_referencia_inviable_admitida(self):
        self.datos["relacion_presiones"] = "300"
        respuesta = self.client.post("/", data=self.datos)
        self.assertEqual(respuesta.status_code, 303)
        vista = self.client.get(respuesta.location).get_data(as_text=True)
        self.assertIn("Volver al formulario", vista)
        descarga = self.client.get(respuesta.location + "?descargar=1")
        self.assertIn("attachment", descarga.headers["Content-Disposition"])
        texto = descarga.get_data(as_text=True)
        parser = InformeParser()
        parser.feed(texto)
        self.assertEqual(len(parser.imagenes), 3)
        self.assertEqual(parser.externos, [])
        for fragmento in ("Análisis de sensibilidad", "parametros_inviables", "inviable", "Commit Git:",
                          "Sensibilidades locales", "búsqueda numérica independiente", "Dominios recalculados"):
            self.assertIn(fragmento, texto)
        self.assertTrue(texto.startswith(reporting.MARCA_INICIO))
        self.assertTrue(texto.endswith(reporting.MARCA_FINAL))

    def test_formulario_errores_conserva_valores(self):
        texto = self.client.get("/").get_data(as_text=True)
        self.assertIn("Análisis de sensibilidad", texto)
        self.assertIn("delta [fracción]", texto)
        for clave, valor in (("sens_muestras", "3.5"), ("sens_muestras", "202"),
                             ("sens_minimo", "inf"), ("sens_parametro", "otro"),
                             ("sens_minimo", "2000")):
            datos = {**self.datos, clave: valor}
            respuesta = self.client.post("/", data=datos)
            self.assertEqual(respuesta.status_code, 400)
            self.assertIn("Configuración de sensibilidad inválida", respuesta.get_data(as_text=True))
            self.assertIn('value="1600"', respuesta.get_data(as_text=True))
        self.assertEqual(list(self.carpeta.iterdir()), [])

    def test_normal_no_ejecuta_ofat_ni_valida_controles(self):
        with patch.object(web_app, "ejecutar_sensibilidad") as ejecutar, \
                patch.object(web_app, "main", return_value=self.carpeta / "normal.html") as normal:
            respuesta = self.client.post("/", data={**self.datos, "accion": "normal", "sens_muestras": "basura"})
        self.assertEqual(respuesta.status_code, 303)
        normal.assert_called_once()
        ejecutar.assert_not_called()

    def test_errores_programacion_no_se_silencian(self):
        with patch.object(web_app, "ejecutar_sensibilidad", side_effect=ValueError("FALLO_INTERNO")):
            with self.assertLogs(web_app.app.logger, level="ERROR"):
                respuesta = self.client.post("/", data=self.datos)
        self.assertEqual(respuesta.status_code, 500)
        texto = respuesta.get_data(as_text=True)
        self.assertNotIn("FALLO_INTERNO", texto)
        self.assertIn('value="200"', texto)

    def test_retencion_mixta_y_fallo_publicacion(self):
        rutas = []
        ajeno = self.carpeta / "notas.html"
        ajeno.write_text("ajeno", encoding="utf-8")
        for i in range(5):
            if i == 0:
                with redirect_stdout(StringIO()):
                    ruta = main.main(self.carpeta)
            else:
                ruta = s.ejecutar_sensibilidad(self.carpeta, main.PARAMETROS_PREDETERMINADOS,
                                              "T3", 800, 2000, 3)
            rutas.append(ruta)
        self.assertFalse(rutas[0].exists())
        self.assertTrue(all(r.exists() for r in rutas[1:]))
        antes = {r: r.read_bytes() for r in self.carpeta.iterdir()}
        with patch.object(Path, "rename", side_effect=OSError("publicación fallida")):
            with self.assertRaises(OSError):
                s.ejecutar_sensibilidad(self.carpeta, main.PARAMETROS_PREDETERMINADOS, "T3", 800, 2000, 3)
        self.assertEqual(antes, {r: r.read_bytes() for r in self.carpeta.iterdir()})
        self.assertEqual(ajeno.read_text(encoding="utf-8"), "ajeno")

    def test_informe_reversible_y_escape(self):
        p = {**main.PARAMETROS_PREDETERMINADOS, "eta_c": 1, "eta_t": 1, "perdida_presion_combustor": 0}
        e = s.analizar_sensibilidad(p, "delta", 0, .1, 3)
        imagenes = s.crear_graficas_sensibilidad(e)
        texto = reporting.crear_informe_sensibilidad_html(e, imagenes, datetime.now(),
                       {"commit": "<script>", "modificado": None})
        self.assertIn("supremo_no_alcanzado", texto)
        self.assertIn("&lt;script&gt;", texto)
        self.assertNotIn("Commit Git: <script>", texto)
        self.assertIn("\\u003cscript>", texto)  # JSON inerte; el dashboard sí incluye JS legítimo.
        self.assertIn("Estado local Git no disponible", texto)
        with self.assertRaises(ValueError):
            reporting.crear_informe_sensibilidad_html(e, {}, datetime.now(), {"commit": None, "modificado": False})


if __name__ == "__main__":
    unittest.main()
