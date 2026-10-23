"""Presentación estática y rutas; interactividad real se comprueba en navegador aparte."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import dashboard
import main
import reporting
import sensibilidad
import web_app
from test_reporting import InformeParser


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as carpeta:
            with patch.object(main, 'crear_informe_html', wraps=reporting.crear_informe_html) as crear:
                with redirect_stdout(StringIO()):
                    ruta = main.main(carpeta)
            cls.html = ruta.read_text(encoding='utf-8')
            cls.args, cls.kw = crear.call_args.args, crear.call_args.kwargs
        cls.metadata, cls.paneles = dashboard.separar_presentacion(cls.html)

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.carpeta = Path(self.temporal.name)
        self.config = patch.dict(web_app.app.config, {'OUTPUTS_DIR': self.carpeta, 'TESTING': True})
        self.config.start()
        self.addCleanup(self.config.stop)
        self.client = web_app.app.test_client()
        self.datos = {k: str(v) for k, v in web_app.valores_formulario().items()}

    def test_seis_secciones_y_nueve_parametros_sin_duplicar(self):
        html = self.client.get('/').get_data(as_text=True)
        for clave, nombre in dashboard.SECCIONES:
            self.assertIn(f'id="{clave}"', html)
            self.assertIn(f'href="#{clave}"', html)
        for clave in web_app.CAMPOS:
            self.assertEqual(html.count(f'name="{clave}"'), 1)
        self.assertEqual(html.count('type="number"'), 19)  # 9 físicos, 3 OFAT, 6 mapa + T0.
        for titulo, _ in dashboard.GRUPOS:
            self.assertIn(titulo, html)

    def test_kpi_seis_valores_del_caso_noideal(self):
        valores = {'rp': 10., 'trabajo': self.args[2]['trabajo_neto'],
                   'rendimiento': 100*self.args[2]['rendimiento'], 'calor': self.args[2]['calor_aportado'],
                   'max_trabajo': self.kw['comparacion_criterios']['punto_a']['ciclo']['trabajo_neto'],
                   'max_rendimiento': 100*self.kw['comparacion_criterios']['punto_b']['ciclo']['rendimiento']}
        self.assertEqual(self.html.count('data-kpi='), 6)
        for clave, valor in valores.items():
            tarjeta = re.search(f'data-kpi="{clave}"(.*?)</article>', self.html, re.S)[1]
            self.assertIn(f'{valor:.3f}', tarjeta)

    def test_kpi_y_comparacion_no_hardcodeados(self):
        args = list(self.args)
        args[2] = {**args[2], 'trabajo_neto': 123.456789, 'rendimiento': .23456, 'calor_aportado': 526.}
        html = reporting.crear_informe_html(*args, **self.kw)
        self.assertIn('123.457', re.search('data-kpi="trabajo"(.*?)</article>', html, re.S)[1])
        self.assertIn('23.456', re.search('data-kpi="rendimiento"(.*?)</article>', html, re.S)[1])

    def test_no_disponible_no_se_convierte_en_cero(self):
        tarjeta = dashboard.tarjeta_kpi('x', 'Valor', None, '%', 'Sin punto motor')
        self.assertIn('No disponible', tarjeta)
        self.assertNotIn('0.000', tarjeta)
        respuesta = self.client.post('/', data={**self.datos, 'T3': '400'})
        self.assertEqual(respuesta.status_code, 400)
        self.assertNotIn('data-kpi=', respuesta.get_data(as_text=True))

    def test_reversible_sin_maximo_b(self):
        args, kw = list(self.args), self.kw.copy()
        kw['comparacion_criterios'] = {**kw['comparacion_criterios'], 'estado': 'no_disponible', 'punto_b': None}
        ideal = {'estado': 'supremo_no_alcanzado', 'analitico': None, 'motivo': 'Supremo no alcanzado',
                 'supremo': {'rendimiento': .8, 'rp_frontera': 100, 'alcanzado': False}}
        kw['estudio_rendimiento'] = {'ideal': ideal, 'noideal': ideal}
        html = reporting.crear_informe_html(*args, **kw)
        tarjeta = re.search('data-kpi="max_rendimiento"(.*?)</article>', html, re.S)[1]
        self.assertIn('No disponible', tarjeta)
        self.assertIn('Supremo no alcanzado', tarjeta)

    def test_siete_png_una_vez_y_cinco_pestanas(self):
        parser = InformeParser(); parser.feed(self.html)
        self.assertEqual(len(parser.imagenes), 7)
        self.assertCountEqual(parser.imagenes, self.args[7].values())
        self.assertEqual(parser.externos, [])
        self.assertEqual(len(re.findall(r'<button\b[^>]*data-plot-tab=', self.html)), 5)
        for clave in ('rendimiento', 'trabajo', 'diagramas', 'compromiso', 'todas'):
            self.assertIn(f'data-plot-tab="{clave}"', self.html)

    def test_detalles_plegados_conservan_textos(self):
        self.assertIn('<details class="card"><summary>Estados y balances detallados</summary>', self.html)
        for texto in ('Comprobaciones ejecutadas', 'T2s', 'T4s', 'Comparación del ciclo ideal',
                      'Optimización del rendimiento térmico', 'Constante específica R'):
            self.assertIn(texto, self.html)

    def test_informe_autonomo_recursos_y_licencia_incrustados(self):
        self.assertIn('data:font/woff2;base64,', self.html)
        self.assertIn('SIL OPEN FONT LICENSE', self.html)
        self.assertNotIn('href="/static/', self.html)
        self.assertNotIn('src="/static/', self.html)
        self.assertNotRegex(self.html, r'(?:src|href)=[\'\"]https?://')
        self.assertIn('<svg ', self.html)
        self.assertIn('<noscript>', self.html)

    def test_metadatos_json_seguro_y_paneles_recuperables(self):
        self.assertEqual(self.metadata['tipo'], 'normal')
        self.assertEqual(self.metadata['parametros'], self.args[0])
        self.assertEqual(set(self.paneles), {'resultados', 'optimizacion', 'sensibilidad', 'segunda_ley'})
        self.assertNotIn('<', dashboard.json_seguro({'x': '</script><script>alert(1)</script>'}))
        self.assertIsNone(dashboard.separar_presentacion('<html>antiguo</html>'))

    def test_tres_png_ofat_y_disponibilidad(self):
        e = sensibilidad.analizar_sensibilidad(main.PARAMETROS_PREDETERMINADOS, 'T3', 200, 1600, 5)
        imagenes = sensibilidad.crear_graficas_sensibilidad(e)
        html = reporting.crear_informe_sensibilidad_html(e, imagenes, self.args[8], self.args[9])
        parser = InformeParser(); parser.feed(html)
        self.assertEqual(len(parser.imagenes), 3)
        self.assertEqual(parser.externos, [])
        self.assertEqual(len(re.findall(r'<button\b[^>]*data-plot-tab=', html)), 3)
        self.assertIn('muestras', html)
        self.assertIn('no disponibles', html)
        self.assertIn('parametros_inviables', html)
        self.assertIn('consigna', html)

    def test_vista_local_conserva_parametros_y_descarga_original(self):
        ruta = reporting.guardar_informe_html(self.html, self.carpeta, self.args[8])
        vista = self.client.get('/informes/'+ruta.name)
        self.assertEqual(vista.status_code, 200)
        texto = vista.get_data(as_text=True)
        self.assertIn('Volver al formulario', texto)
        self.assertIn('Descargar informe HTML', texto)
        self.assertIn('value="288.15"', texto)
        self.assertIn('value="5.0"', texto)
        descarga = self.client.get('/informes/'+ruta.name+'?descargar=1')
        self.assertEqual(descarga.get_data(as_text=True), self.html)

    def test_historial_solo_lectura_y_compatibilidad_anterior(self):
        antiguo = reporting.MARCA_INICIO+'<html>anterior</html>'+reporting.MARCA_FINAL
        ruta = reporting.guardar_informe_html(antiguo, self.carpeta, self.args[8])
        ajeno = self.carpeta/'notas.html'; ajeno.write_text('personal', encoding='utf-8')
        antes = {p.name: p.read_bytes() for p in self.carpeta.iterdir()}
        html = self.client.get('/').get_data(as_text=True)
        self.assertIn(ruta.name, html)
        self.assertIn('Informe anterior', html)
        self.assertNotIn('notas.html', html)
        self.assertEqual(antes, {p.name: p.read_bytes() for p in self.carpeta.iterdir()})
        self.assertEqual(self.client.get('/informes/'+ruta.name).status_code, 200)

    def test_acciones_no_se_ejecutan_al_navegar(self):
        with patch.object(web_app, 'main') as normal, patch.object(web_app, 'ejecutar_sensibilidad') as ofat:
            for clave, _ in dashboard.SECCIONES:
                self.assertEqual(self.client.get('/#'+clave).status_code, 200)
        normal.assert_not_called(); ofat.assert_not_called()

    def test_ayuda_documentos_sin_rutas_arbitrarias(self):
        self.assertEqual(self.client.get('/documentacion/README.md').status_code, 200)
        self.assertEqual(self.client.get('/documentacion/CODE_WALKTHROUGH.md').status_code, 200)
        self.assertEqual(self.client.get('/documentacion/web_app.py').status_code, 404)

    def test_css_y_js_contratos_de_accesibilidad_estaticos(self):
        css = (dashboard.RAIZ/'static/style.css').read_text(encoding='utf-8')
        js = (dashboard.RAIZ/'static/dashboard.js').read_text(encoding='utf-8')
        for fragmento in ('prefers-reduced-motion', ':focus-visible', 'overflow-x:auto', '@media(max-width:760px)'):
            self.assertIn(fragmento, css)
        for fragmento in ('ArrowRight', 'ArrowLeft', 'showModal', 'aria-selected', 'hashchange'):
            self.assertIn(fragmento, js)
        self.assertNotIn('fetch(', js)
        self.assertNotIn('XMLHttpRequest', js)


if __name__ == '__main__':
    unittest.main()
