"""Presentación educativa: textos compartidos y conclusiones tomadas de datos."""
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime
from io import StringIO
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import dashboard
import main
import mapa_diseno
import reporting
import sensibilidad
import web_app
from test_reporting import InformeParser


class ExplicacionesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = main.PARAMETROS_PREDETERMINADOS.copy()
        with tempfile.TemporaryDirectory() as d, redirect_stdout(StringIO()):
            with patch.object(main, 'crear_informe_html', wraps=reporting.crear_informe_html) as crear:
                cls.normal = main.main(d).read_text(encoding='utf-8')
            cls.args, cls.kw = crear.call_args.args, crear.call_args.kwargs
        # Fixtures de presentación: PNG válido ya generado, sin redibujar física.
        cls.pngs = list(cls.args[7].values())
        cls.png = cls.pngs[0]
        cls.fecha, cls.version = datetime.now(), dict(commit='prueba', modificado=True)
        cls.ofat = sensibilidad.analizar_sensibilidad(cls.p, 'delta', 0, .2, 3)
        cls.ofat_html = reporting.crear_informe_sensibilidad_html(cls.ofat,
            {k: cls.pngs[i] for i, k in enumerate(('trabajo_neto', 'rendimiento', 'rp'))}, cls.fecha, cls.version)
        cls.mapa = mapa_diseno.analizar_mapa(cls.p, n_rp=3, n_T3=3, cortes=(1600,))
        cls.map_png = {k: cls.pngs[i] for i, k in enumerate(('mapa_trabajo_neto.png', 'mapa_rendimiento.png', 'mapa_viabilidad.png', 'corte_0.png'))}
        cls.map_html = reporting.crear_informe_mapa_html(cls.mapa, cls.map_png, cls.fecha, cls.version)

    def test_introduccion_y_glosario_en_tres_informes(self):
        for html in (self.normal, self.ofat_html, self.map_html):
            self.assertNotIn('¿Qué estamos estudiando?', html)
            self.assertIn('no calcula empuje', html)
            self.assertEqual(html.count('data-edu-tabs='), 6)
            self.assertIn('Glosario de magnitudes', html)
            for termino in ('Back work ratio', 'kJ/kg', 'kW', 'eta_c y eta_t', 'delta'):
                self.assertIn(termino, html)

    def test_siete_explicaciones_normales_especificas(self):
        for nombre in self.args[7]:
            self.assertIn(dashboard.EXPLICACIONES_GRAFICAS[nombre], self.normal)
        self.assertIn('1→2 es compresión isentrópica', self.normal)
        self.assertIn('No representa la generación de entropía de equipos no ideales', self.normal)

    def test_objetivos_y_disponibilidad(self):
        self.assertIn('¿Qué intentamos optimizar?', self.normal)
        self.assertIn('supremo no alcanzado', self.normal)
        self.assertIn('Dominio motor vacío', self.normal)
        self.assertIn('no un ciclo operativo ni un punto B', self.normal)

    def test_contexto_ofat_delta_y_fijos(self):
        self.assertIn('delta [fracción], de 0 a 0.2, con 3 muestras', self.ofat_html)
        fijos = re.search(r'Parámetros fijos: (.*?)</p>', self.ofat_html)[1]
        self.assertNotIn('delta=', fijos)
        self.assertIn('T3=1600 K', fijos)
        self.assertNotIn('relacion_presiones=', fijos)
        self.assertIn('En R, rp=10 permanece fija', self.ofat_html)

    def test_contexto_ofat_temperatura(self):
        e = sensibilidad.analizar_sensibilidad(self.p, 'T3', 200, 1600, 3)
        html = reporting.crear_informe_sensibilidad_html(e, {k: self.pngs[i] for i, k in enumerate(('trabajo_neto', 'rendimiento', 'rp'))}, self.fecha, self.version)
        fijos = re.search(r'Parámetros fijos: (.*?)</p>', html)[1]
        self.assertNotIn('T3=', fijos)
        self.assertIn('delta=0.05 fracción', fijos)
        self.assertIn('T3 [K], de 200 a 1600, con 3 muestras', html)

    def test_tres_explicaciones_ofat_y_normalizacion(self):
        for k in ('trabajo_neto', 'rendimiento', 'rp'):
            self.assertIn(dashboard.EXPLICACIONES_GRAFICAS[k], self.ofat_html)
        self.assertIn('2 puntos porcentuales', self.ofat_html)
        self.assertIn('normalización singular', self.ofat_html)
        self.assertIn('no demuestra la existencia de un punto motor', self.ofat_html)

    def test_explicaciones_mapa_y_corte_sin_repeticion(self):
        self.assertIn('¿Qué estamos modificando y por qué?', self.map_html)
        self.assertIn('rp de 1 a 100 y T3 de 600 a 2000 K', self.map_html)
        for k in self.map_png:
            if k.startswith('mapa_'): self.assertIn(dashboard.EXPLICACIONES_GRAFICAS[k], self.map_html)
        self.assertEqual(self.map_html.count(dashboard.EXPLICACIONES_GRAFICAS['corte']), 1)
        self.assertIn('no una T3 óptima global', self.map_html)
        self.assertIn('No es un mapa operativo real', self.map_html)

    def test_conclusion_normal_consume_comparacion_calculada(self):
        c = self.kw['comparacion_criterios']
        self.assertIn(f"reduce el trabajo específico un {c['reduccion_trabajo_porcentaje']:.3f} %", self.normal)
        kw = deepcopy(self.kw)
        kw['comparacion_criterios']['reduccion_trabajo_porcentaje'] = 1.234
        kw['comparacion_criterios']['ganancia_rendimiento_pp'] = .567
        html = reporting.crear_informe_html(*self.args, **kw)
        self.assertIn('reduce el trabajo específico un 1.234 % y aumenta el rendimiento 0.567 puntos porcentuales', html)

    def test_conclusion_no_afirma_sacrificio_si_signo_no_lo_permite(self):
        kw = deepcopy(self.kw)
        kw['comparacion_criterios']['reduccion_trabajo_porcentaje'] = -1
        html = reporting.crear_informe_html(*self.args, **kw)
        conclusion = re.search(r'class="card educational-conclusions"(.*?)</ul>', html, re.S)[1]
        self.assertNotIn('Pasar de A a B reduce', conclusion)

    def test_conclusiones_ofat_solo_disponibilidad_real(self):
        for s in 'RAB':
            n = sum(r[s]['estado'] == 'disponible' for r in self.ofat['registros'])
            self.assertIn(f'{s}: {n}/3 muestras con ciclo motor', self.ofat_html)
        conclusion = re.search(r'class="card educational-conclusions"(.*?)</ul>', self.ofat_html, re.S)[1]
        self.assertNotIn('aumentar', conclusion)

    def test_supremo_reversible_no_es_maximo_alcanzado(self):
        p = {**self.p, 'eta_c': 1., 'eta_t': 1., 'perdida_presion_combustor': 0.}
        e = mapa_diseno.analizar_mapa(p, n_rp=3, n_T3=3, cortes=(1600,))
        html = reporting.crear_informe_mapa_html(e, self.map_png, self.fecha, self.version)
        self.assertIn('máximo B alcanzado en 0 de las 3 temperaturas', html)
        self.assertIn('En 3 temperaturas, B es un supremo no alcanzado', html)

    def test_conclusion_dominio_vacio_y_ventana_recortada(self):
        p = {**self.p, 'eta_c': .2, 'eta_t': .2}
        e = mapa_diseno.analizar_mapa(p, n_rp=3, n_T3=3, cortes=(1600,))
        html = reporting.crear_informe_mapa_html(e, self.map_png, self.fecha, self.version)
        self.assertIn('0 de 9 celdas muestreadas cumplen', html)
        self.assertIn('3 temperaturas tienen dominio motor vacío', html)
        e = mapa_diseno.analizar_mapa(self.p, n_rp=3, n_T3=3, rp_max=2, cortes=(1600,))
        html = reporting.crear_informe_mapa_html(e, self.map_png, self.fecha, self.version)
        self.assertIn('quedan fuera de la ventana rp mostrada', html)

    def test_escapado_y_numero_conclusiones(self):
        self.assertNotIn('<script>', dashboard.bloque_educativo('<script>', '<script>'))
        html = dashboard.conclusiones_html(['<script>']*6)
        self.assertEqual(html.count('<li>'), 4)
        self.assertNotIn('<script>', html)
        texto = reporting.imagen_html(self.png, '<titulo>', '<script>')
        self.assertIn('&lt;script&gt;', texto)

    def test_autonomia_y_datos_png_conservados(self):
        for html, cantidad in ((self.normal, 7), (self.ofat_html, 3), (self.map_html, 4)):
            parser = InformeParser(); parser.feed(html)
            self.assertEqual(len(parser.imagenes), cantidad)
            self.assertFalse(parser.externos)
            self.assertEqual(html.count('¿Qué hemos aprendido de esta simulación?'), 1)

    def test_estilos_educativos_son_legibles_y_responsivos(self):
        css = (Path(__file__).resolve().parents[1] / 'static' / 'style.css').read_text(encoding='utf-8')
        for selector in ('.educational-intro', '.educational-note', '.educational-conclusions',
                         '.plot-help', '#ayuda .metric-list', '@media(max-width:760px)'):
            self.assertIn(selector, css)
        self.assertIn('.plot-help{font-size:13px;line-height:1.65', css)
        self.assertIn('#ayuda .metric-list dd{font:13px/1.6', css)

    def test_dashboard_comparte_textos_del_informe(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(web_app.app.config, TESTING=True, OUTPUTS_DIR=Path(d)):
            ruta = reporting.guardar_informe_html(self.map_html, d, self.fecha)
            cliente = web_app.app.test_client()
            vista = cliente.get('/informes/'+ruta.name).get_data(as_text=True)
            self.assertNotIn(dashboard.INTRODUCCION, vista)
            for texto in (dashboard.EXPLICACIONES_GRAFICAS['mapa_viabilidad.png'],):
                self.assertEqual(vista.count(texto), 1)
            self.assertEqual(cliente.get('/informes/'+ruta.name+'?descargar=1').get_data(as_text=True), self.map_html)
            self.assertIn('Glosario de magnitudes', cliente.get('/').get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
