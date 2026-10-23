"""Verificación interna de Fase 5, sin escribir en outputs/ del proyecto."""
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import matplotlib.pyplot as plt
import numpy as np
import dashboard
import main
import mapa_diseno as mapa
import reporting
import web_app
from sensibilidad import argumentos_fisicos
from viabilidad import ErrorNumerico, evaluar_punto
from test_reporting import InformeParser


class MapaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = main.PARAMETROS_PREDETERMINADOS.copy()
        cls.config = dict(rp_min=1, rp_max=100, T3_min=400, T3_max=2000, n_rp=9, n_T3=5, cortes=(1200,))
        cls.e = mapa.analizar_mapa(cls.p, **cls.config)
        cls.imagenes = mapa.crear_graficas_mapa(cls.e)
        cls.html = reporting.crear_informe_mapa_html(cls.e, cls.imagenes, datetime.now(),
                                                    dict(commit='<prueba>', modificado=True))

    def test_orientacion_y_dimensiones(self):
        e = self.e
        for x in (*e['matrices'].values(), *e['mascaras'].values(), e['motivos']):
            self.assertEqual(x.shape, (5, 9))
        self.assertEqual(e['mascaras']['viable'].dtype, bool)
        self.assertEqual(e['filas'][2]['T3'], e['T3'][2])

    def test_validacion_rangos(self):
        for cambio in (dict(rp_min=0), dict(rp_max=1), dict(T3_min=200), dict(T3_max=500),
                       dict(rp_max=np.inf), dict(escala='otra'), dict(cortes=(200,)),
                       dict(n_rp=True), dict(n_T3=2), dict(n_rp=402), dict(n_rp=200, n_T3=200)):
            with self.subTest(cambio=cambio), self.assertRaises(ValueError):
                mapa.validar_configuracion(self.p, **cambio)

    def test_escalas(self):
        for escala in ('lineal', 'log'):
            rp, t = mapa.crear_malla(mapa.validar_configuracion(self.p, escala=escala, n_rp=7, n_T3=3))
            self.assertAlmostEqual(rp[0], 1); self.assertAlmostEqual(rp[-1], 100)
            paso = np.diff(rp if escala == 'lineal' else np.log(rp))
            np.testing.assert_allclose(paso, paso[0])

    def test_celdas_coinciden_evaluaciones(self):
        for i in (0, 2, 4):
            for j in (0, 3, 8):
                p = {**self.p, 'T3': self.e['T3'][i]}
                a = argumentos_fisicos(p)
                punto = evaluar_punto(a[0], a[1], a[2], a[3], self.e['rp'][j], *a[4:])
                self.assertEqual(self.e['mascaras']['viable'][i, j], punto['viable'])
                self.assertAlmostEqual(self.e['matrices']['trabajo_neto'][i, j], punto['trabajo_neto'])
                self.assertEqual(self.e['motivos'][i, j], punto['motivos'])

    def test_signos_y_rendimiento_no_motor(self):
        self.assertTrue(np.isnan(self.e['matrices']['rendimiento'][~self.e['mascaras']['viable']]).all())
        self.assertTrue((self.e['matrices']['trabajo_neto'] < 0).any())
        self.assertIn('compresion', self.e['motivos'][0, 0])

    def test_fila_sin_dominio_no_es_error_de_entrada(self):
        self.assertFalse(self.e['filas'][0]['muestra']['dominios']['noideal']['intervalo'])
        self.assertFalse(self.e['mascaras']['viable'][0].any())
        self.assertEqual(self.e['trayectorias']['A']['registros'][0]['estado'], 'sin_dominio')

    def test_fronteras_independientes(self):
        for i, f in enumerate(self.e['filas']):
            intervalo = f['muestra']['dominios']['noideal']['intervalo']
            if intervalo:
                self.assertEqual(self.e['fronteras']['inferior'][i], intervalo[0])
                self.assertEqual(self.e['fronteras']['superior'][i], intervalo[1])

    def test_trayectorias_y_contrastes(self):
        for s in 'AB':
            for i, r in enumerate(self.e['trayectorias'][s]['registros']):
                if r['estado'] == 'disponible':
                    self.assertTrue(r['ciclo']['viable'])
                    lo, hi = self.e['filas'][i]['muestra']['dominios']['noideal']['intervalo']
                    self.assertTrue(lo < r['rp'] < hi)
                    if i in self.e['indices_verificacion']:
                        self.assertIsNotNone(r['verificacion']['concordancia'])

    def test_limite_reversible_y_supremo(self):
        p = {**self.p, 'eta_c': 1., 'eta_t': 1., 'perdida_presion_combustor': 0.}
        e = mapa.analizar_mapa(p, n_rp=5, n_T3=3, cortes=(1600,))
        for r, t in zip(e['trayectorias']['B']['registros'], e['T3']):
            self.assertEqual(r['estado'], 'supremo_no_alcanzado')
            self.assertIsNone(r['rp'])
            self.assertAlmostEqual(r['supremo']['rendimiento'], 1-p['T1']/t)
        self.assertTrue(np.isnan(e['trayectorias']['B']['rp']).all())

    def test_refinamiento_no_mueve_optimos(self):
        fino = mapa.analizar_mapa(self.p, **{**self.config, 'n_rp': 41})
        for s in 'AB':
            np.testing.assert_allclose(fino['trayectorias'][s]['rp'], self.e['trayectorias'][s]['rp'], equal_nan=True)
        # Los nodos de una malla 9 se conservan en una 41 (factor cinco).
        np.testing.assert_allclose(fino['matrices']['trabajo_neto'][:, ::5], self.e['matrices']['trabajo_neto'])

    def test_optimo_fuera_ventana_no_se_recorta_fisicamente(self):
        e = mapa.analizar_mapa(self.p, rp_max=3, T3_min=4000, T3_max=10000, n_rp=3, n_T3=3, cortes=(4000,))
        self.assertTrue((e['trayectorias']['A']['rp'] > 100).any())
        self.assertTrue((e['trayectorias']['B']['rp'] > e['rp'][-1]).all())

    def test_cortes_reutilizados_y_exactos(self):
        fila = mapa.extraer_cortes(self.e, (1200,))[0]
        self.assertIs(fila, self.e['filas'][2])
        otra = mapa.extraer_cortes(self.e, (1300,))[0]
        self.assertEqual(otra['T3'], 1300)
        punto = evaluar_punto(self.p['T1'], 1300, self.p['gamma'], self.p['cp'],
                              self.e['rp'][3], self.p['p1'], self.p['eta_c'], self.p['eta_t'], self.p['perdida_presion_combustor'])
        self.assertAlmostEqual(otra['puntos'][3]['trabajo_neto'], punto['trabajo_neto'])
        with self.assertRaises(ValueError): mapa.extraer_cortes(self.e, (3000,))

    def test_limites_numericos_distintos_de_inviabilidad(self):
        with patch.object(mapa, 'evaluar_punto', side_effect=ErrorNumerico('No representable')):
            fila = mapa.evaluar_fila(self.p, 1600, [10])
        self.assertEqual(fila['puntos'][0]['estado'], 'limite_numerico')
        self.assertTrue(np.isnan(fila['puntos'][0]['trabajo_neto']))
        self.assertTrue(mapa.obtener_mascaras([fila])['limite_numerico'][0, 0])

    def test_errores_de_programa_propagan(self):
        with patch.object(mapa, 'evaluar_punto', side_effect=RuntimeError('error')), self.assertRaises(RuntimeError):
            mapa.evaluar_fila(self.p, 1600, [10])

    def test_dominio_una_vez_por_fila_fuera_contrastes(self):
        from sensibilidad import calcular_dominios
        with patch('sensibilidad.calcular_dominios', wraps=calcular_dominios) as dominios:
            mapa.evaluar_fila(self.p, 1600, np.linspace(1, 100, 25))
        self.assertEqual(dominios.call_count, 1)

    def test_mascaras_sin_interpolacion_contornos(self):
        r = mapa.preparar_resultados(self.e)
        for m in r['prestaciones'].values():
            np.testing.assert_array_equal(m.mask, ~self.e['mascaras']['viable'])
        with patch.object(plt.Axes, 'contourf', side_effect=AssertionError('No interpolar contornos')):
            e = {**self.e, 'cortes': []}
            imagenes = mapa.crear_graficas_mapa(e)
        self.assertEqual(len(imagenes), 3)

    def test_tres_figuras_y_corte_png(self):
        self.assertEqual(len(self.imagenes), 4)
        for datos in self.imagenes.values(): self.assertTrue(datos.startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertFalse(plt.get_fignums())

    def test_informe_autocontenido_y_datos(self):
        parser = InformeParser(); parser.feed(self.html)
        self.assertEqual(len(parser.imagenes), 4); self.assertFalse(parser.externos)
        metadata, paneles = dashboard.separar_presentacion(self.html)
        self.assertEqual(metadata['tipo'], 'mapa'); self.assertIn('mapa', paneles)
        self.assertIn('data:font/woff2;base64,', self.html)
        self.assertNotIn('Commit Git: <prueba>', self.html)
        self.assertIn('sin confirmar', self.html)
        self.assertIn('Resultados principales A/B y dominios', self.html)

    def test_retencion_compartida(self):
        with tempfile.TemporaryDirectory() as d:
            for _ in range(5): reporting.guardar_informe_html(self.html, d, datetime.now())
            self.assertEqual(len(list(Path(d).glob('*.html'))), 4)

    def test_flask_mapa_descarga_y_recuperacion(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(web_app.app.config, TESTING=True, OUTPUTS_DIR=Path(d)):
            cliente = web_app.app.test_client()
            datos = {k: str(v) for k, v in web_app.valores_formulario().items()}
            datos.update(accion='mapa', **{'mapa_' + k: str(v) for k, v in self.config.items() if k != 'cortes'}, mapa_cortes='1200')
            respuesta = cliente.post('/', data=datos)
            self.assertEqual(respuesta.status_code, 303)
            vista = cliente.get(respuesta.location).get_data(as_text=True)
            self.assertIn('data-initial-section="mapa"', vista)
            self.assertIn('name="mapa_cortes" value="1200.0"', vista)
            descarga = cliente.get(respuesta.location+'?descargar=1')
            self.assertEqual(descarga.get_data(as_text=True), next(Path(d).glob('*.html')).read_text(encoding='utf-8'))
            self.assertIn('Mapa de diseño', cliente.get('/').get_data(as_text=True))
            datos['mapa_T3_min'] = '100'
            self.assertEqual(cliente.post('/', data=datos).status_code, 400)

    def test_referencia_no_muta_ni_reutiliza_resultados(self):
        p = self.p.copy()
        mapa.analizar_mapa(p, n_rp=3, n_T3=3, cortes=(600,))
        self.assertEqual(p, self.p)
        e = mapa.analizar_mapa({**p, 'eta_c': .4, 'eta_t': .4, 'perdida_presion_combustor': .5}, n_rp=3, n_T3=3, cortes=(600,))
        self.assertLess(e['mascaras']['viable'].sum(), self.e['mascaras']['viable'].sum())


if __name__ == '__main__':
    unittest.main()
