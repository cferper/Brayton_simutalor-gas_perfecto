"""Verificación del dominio físico; no validación contra datos experimentales."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import matplotlib.pyplot as plt
import main
import web_app
from viabilidad import (ErrorNumerico, bisectar_raiz, calcular_dominios,
                        construir_barrido, describir_inviabilidad, evaluar_punto)


class ViabilidadTests(unittest.TestCase):
    def setUp(self):
        self.base = (288.15, 1600, 1.4, 1005, 100, .85, .9, .05)
        self.dominios = calcular_dominios(*self.base)

    def punto(self, rp, ideal=False, **cambios):
        p = main.PARAMETROS_PREDETERMINADOS.copy()
        p.update(cambios)
        return evaluar_punto(p['T1'], p['T3'], p['gamma'], p['cp'], rp, p['p1'],
                             *( (1, 1, 0) if ideal else
                                (p['eta_c'], p['eta_t'], p['perdida_presion_combustor']) ))

    def test_limites_ideales_y_optimo_distintos(self):
        lo, hi = self.dominios['ideal']['intervalo']
        self.assertEqual(lo, 1)
        self.assertAlmostEqual(hi, (1600 / 288.15)**3.5, places=9)
        self.assertAlmostEqual(main.calcular_relacion_optima(288.15, 1600, 1.4)**2, hi, places=9)
        for rp in (lo, hi):
            self.assertFalse(self.punto(rp, ideal=True)['viable'])
        self.assertTrue(self.punto(hi * (1 - 1e-6), ideal=True)['viable'])
        self.assertFalse(self.punto(hi * (1 + 1e-6), ideal=True)['viable'])

    def test_expansion_con_perdidas_y_motivos_simultaneos(self):
        limite = self.dominios['noideal']['expansion']
        self.assertAlmostEqual(limite, 1 / .95, places=14)
        punto = self.punto(limite)
        self.assertIn('expansion', punto['fronteras'])
        self.assertIn('trabajo_neto', punto['motivos'])
        self.assertIn('expansion', punto['motivos'])
        self.assertNotIn('calor_aportado', punto['motivos'])
        self.assertIsNone(punto['rendimiento'])

    def test_frontera_calor(self):
        frontera = self.dominios['noideal']['calor']
        punto = self.punto(frontera)
        self.assertIn('calor_aportado', punto['fronteras'])
        self.assertIn('trabajo_neto', punto['motivos'])
        self.assertGreater(punto['presiones'][2], punto['presiones'][3])
        self.assertIsNone(punto['rendimiento'])

    def test_raices_trabajo_y_vecindades(self):
        for i, rp in enumerate(self.dominios['noideal']['trabajo']):
            with self.subTest(raiz=i):
                punto = self.punto(rp)
                # Bisección en x a 1e-12: residuo energético muy inferior a 1e-7 kJ/kg.
                self.assertAlmostEqual(punto['trabajo_neto'], 0, delta=1e-7)
                self.assertIn('trabajo_neto', punto['fronteras'])
                self.assertFalse(punto['viable'])
                interior = rp * (1 + 1e-6 if i == 0 else 1 - 1e-6)
                exterior = rp * (1 - 1e-6 if i == 0 else 1 + 1e-6)
                self.assertTrue(self.punto(interior)['viable'])
                self.assertFalse(self.punto(exterior)['viable'])

    def test_calor_positivo_no_basta_para_motor(self):
        punto = self.punto(200)
        self.assertGreater(punto['calor_aportado'], 0)
        self.assertLess(punto['trabajo_neto'], 0)
        self.assertEqual(punto['motivos'], ('trabajo_neto',))

    def test_limite_reversible_en_estados_dominios_y_barrido(self):
        dominios = calcular_dominios(288.15, 1600, 1.4, 1005, 100)
        np.testing.assert_allclose(dominios['ideal']['intervalo'],
                                   dominios['noideal']['intervalo'], rtol=1e-11)
        barrido = construir_barrido(288.15, 1600, 1.4, 1005, 100)
        for clave in ('viable', 'rendimiento', 'trabajo_neto'):
            np.testing.assert_equal(barrido['ideal'][clave], barrido['noideal'][clave])
        for rp in (1, 10, 403.4175203200289, 500):
            self.assertEqual(self.punto(rp, ideal=True), self.punto(rp, eta_c=1, eta_t=1,
                                                                  perdida_presion_combustor=0))

    def test_dominio_vacio_sin_perdida_y_con_perdida(self):
        for T3, ec, et, delta in ((300, .5, .5, 0), (400, .85, .9, .5), (576.3, .5, 1, 0)):
            d = calcular_dominios(288.15, T3, 1.4, 1005, 100, ec, et, delta)
            self.assertEqual(d['noideal']['intervalo'], ())
            barrido = construir_barrido(288.15, T3, 1.4, 1005, 100, ec, et, delta)
            self.assertFalse(barrido['noideal']['viable'].any())
            self.assertTrue(np.isnan(barrido['noideal']['rendimiento']).all())

    def test_dominios_coinciden_con_clasificacion_en_combinaciones(self):
        # Verifica la intersección, incluidas eficiencias muy pequeñas y pérdida grande.
        for theta, ec, et, delta in ((1.1, 1, 1, 0), (5, .8, .9, .05),
                                     (10, .1, .2, .8), (100, .9, .95, .7)):
            d = calcular_dominios(300, 300 * theta, 1.4, 1005, 100, ec, et, delta)
            intervalo = d['noideal']['intervalo']
            for rp in np.geomspace(1.0001, min(d['ideal']['calor'] * 1.1, 1e7), 100):
                punto = evaluar_punto(300, 300 * theta, 1.4, 1005, rp, 100, ec, et, delta)
                interior = bool(intervalo and intervalo[0] < rp < intervalo[1])
                self.assertEqual(punto['viable'], interior)

    def test_invariancia_limites_con_cp_y_presion(self):
        otros = calcular_dominios(288.15, 1600, 1.4, 1500, 50, .85, .9, .05)
        self.assertEqual(otros, self.dominios)

    def test_barrido_mixto_conserva_motivos_y_nan(self):
        b = construir_barrido(*self.base, relaciones=[1, 1.03, 2, 10, 200, 500])
        for nombre in ('ideal', 'noideal'):
            mascara = b[nombre]['viable']
            self.assertTrue(mascara.any())
            self.assertTrue((~mascara).any())
            for clave in ('rendimiento', 'trabajo_neto'):
                self.assertTrue(np.isnan(b[nombre][clave][~mascara]).all())
                self.assertTrue(np.isfinite(b[nombre][clave][mascara]).all())
        self.assertGreater(len(b['noideal']['motivos'][0]), 1)
        self.assertLess(len(construir_barrido(*self.base)['relaciones']), 1300)

    def test_graficas_reciben_nan_sin_puentear_zonas_excluidas(self):
        b = construir_barrido(*self.base, relaciones=[1, 1.03, 2, 10, 200, 500])
        figuras = []
        subplots = main.plt.subplots
        cerrar = main.plt.close
        def capturar(*args, **kwargs):
            figura, ejes = subplots(*args, **kwargs)
            figuras.append((figura, ejes))
            return figura, ejes
        imagenes = {}
        try:
            with patch.object(main.plt, 'subplots', side_effect=capturar), patch.object(main.plt, 'close'):
                main.guardar_comparaciones_ciclos(*self.base, imagenes, b)
            for (_, ejes), clave in zip(figuras, ('rendimiento', 'trabajo_neto')):
                for linea, nombre in zip(ejes.lines[:2], ('ideal', 'noideal')):
                    self.assertTrue(np.isnan(linea.get_ydata()[~b[nombre]['viable']]).all())
        finally:
            for buffer in imagenes.values():
                buffer.close()
            cerrar('all')

    def test_parametros_invalidos_no_son_inviabilidad(self):
        for cambios in ({'T3': 200}, {'gamma': 1}, {'cp': 0}, {'eta_c': 0},
                        {'perdida_presion_combustor': 1}, {'T1': float('nan')}):
            with self.subTest(cambios=cambios), self.assertRaises(ValueError):
                self.punto(10, **cambios)
        with self.assertRaises(ValueError):
            construir_barrido(*self.base, relaciones=[10, 2])

    def test_limite_numerico_no_se_clasifica_como_inviabilidad(self):
        with self.assertRaises(ErrorNumerico):
            calcular_dominios(1, 1e300, 1.01, 1005, 100)
        with self.assertRaises(ErrorNumerico):
            self.punto(1e308, p1=1e308)

    def test_biseccion_y_errores_de_acotacion(self):
        self.assertAlmostEqual(bisectar_raiz(lambda x: x*x - 2, 1, 2), 2**.5, delta=2e-12)
        with self.assertRaises(ValueError):
            bisectar_raiz(lambda x: x*x + 1, 1, 2)
        with self.assertRaises(ErrorNumerico):
            bisectar_raiz(lambda x: float('nan'), 1, 2)
        with self.assertRaises(ErrorNumerico):
            bisectar_raiz(lambda x: x*x - 2, 1, 2, iteraciones=1)

    def test_texto_con_todos_los_motivos_y_limites(self):
        texto = describir_inviabilidad(self.punto(1), self.dominios['noideal'])
        for palabra in ('compresión', 'expansión', 'trabajo neto', '1.069654102', '155.454326'):
            self.assertIn(palabra, texto)

    def test_flask_acepta_caso_motor_con_antiguo_barrido_inviable(self):
        datos = {k: str(v) for k, v in web_app.valores_formulario().items()}
        datos['T3'] = '800'
        with tempfile.TemporaryDirectory() as temporal, patch.dict(web_app.app.config, OUTPUTS_DIR=Path(temporal)):
            with redirect_stdout(StringIO()):
                respuesta = web_app.app.test_client().post('/', data=datos)
            self.assertEqual(respuesta.status_code, 303)
            texto = next(Path(temporal).glob('*.html')).read_text(encoding='utf-8')
            self.assertIn('Dominio físicamente viable', texto)
            self.assertIn('banda relativa de 1e−10', texto)
            self.assertIn('NaN corta', texto)

    def test_flask_muestra_limite_numerico_y_conserva_datos(self):
        datos = {k: str(v) for k, v in web_app.valores_formulario().items()}
        with patch.object(web_app, 'main', side_effect=ErrorNumerico('frontera no representable')):
            respuesta = web_app.app.test_client().post('/', data=datos)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('Límite numérico', respuesta.get_data(as_text=True))
        self.assertIn('value="1600"', respuesta.get_data(as_text=True))

    def test_busqueda_ideal_se_adapta_sin_optimizar_noideal(self):
        relaciones, trabajos, indice = main.buscar_optimo_numerico(288.15, 400, 1.4, 1005)
        limite = calcular_dominios(288.15, 400, 1.4, 1005, 100)['ideal']['calor']
        self.assertLess(relaciones[-1], limite)
        self.assertGreater(trabajos.min(), 0)
        self.assertAlmostEqual(relaciones[indice], main.calcular_relacion_optima(288.15, 400, 1.4),
                               delta=relaciones[1]-relaciones[0])


if __name__ == '__main__':
    unittest.main()
