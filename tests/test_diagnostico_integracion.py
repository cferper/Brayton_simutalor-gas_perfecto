"""Diagnósticos reales, persistencia HTML y modalidades; sin sustituir física."""
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
from html.parser import HTMLParser
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import dashboard
from diagnostico_html import renderizar_diagnostico
from diagnostico_informe import (diagnostico_estudio, diagnostico_simulacion,
                                resumir_diagnosticos)
import main
import mapa_diseno
import reporting
import segunda_ley
import sensibilidad
import web_app


class DiagnosticoIntegracionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as carpeta, redirect_stdout(StringIO()):
            with patch.object(main, 'crear_informe_html', wraps=reporting.crear_informe_html) as crear:
                ruta = main.main(carpeta)
            cls.html = ruta.read_text(encoding='utf-8')
            cls.args, cls.kw = crear.call_args.args, crear.call_args.kwargs
        cls.metadata, cls.paneles = dashboard.separar_presentacion(cls.html)

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory(prefix='brayton_diagnostico_')
        self.addCleanup(self.temporal.cleanup)
        self.carpeta = Path(self.temporal.name)
        config = patch.dict(web_app.app.config, {'OUTPUTS_DIR': self.carpeta, 'TESTING': True})
        config.start()
        self.addCleanup(config.stop)
        self.cliente = web_app.app.test_client()
        self.parametros = main.PARAMETROS_PREDETERMINADOS.copy()
        self.form = {k: str(v) for k, v in web_app.valores_formulario().items()}

    def test_simulacion_y_optimizacion_guardan_diagnosticos_y_png(self):
        for panel in ('resultados', 'optimizacion', 'segunda_ley'):
            self.assertIn('Diagnóstico y coherencia física', self.paneles[panel])
            datos = self.metadata['diagnosticos'][panel]
            self.assertGreater(datos['resumen']['cumple'], 0)
            self.assertEqual(datos['resumen']['atencion'], 0)
            self.assertEqual(sum(datos['resumen'].values()), len(datos['items']))
        self.assertEqual(self.html.count('data:image/png;base64,'), 7)
        self.assertIn('Las baterías históricas V.1–V.5 no se ejecutan', self.html)
        self.assertIn('no constituyen validación', self.html)

    def test_html_advertencia_corresponde_a_dato_alterado(self):
        args = deepcopy(list(self.args))
        args[2]['trabajo_neto'] += 1.
        html = reporting.crear_informe_html(*args, **self.kw)
        metadata, paneles = dashboard.separar_presentacion(html)
        datos = metadata['diagnosticos']['resultados']
        self.assertGreater(datos['resumen']['atencion'], 0)
        self.assertIn('data-estado="atencion"', paneles['resultados'])
        self.assertTrue(any(item['estado'] == 'atencion' and item['residuo'] >= .99
                            for item in datos['items']))

    def test_historial_y_descarga_conservan_diagnostico_sin_recalcular(self):
        ruta = reporting.guardar_informe_html(self.html, self.carpeta, datetime.now(timezone.utc))
        with patch.object(web_app, 'main', side_effect=AssertionError('No recalcular historial')):
            respuesta = self.cliente.get('/informes/' + ruta.name)
            descarga = self.cliente.get('/informes/' + ruta.name + '?descargar=1')
            historial = self.cliente.get('/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('Diagnóstico y coherencia física', respuesta.get_data(as_text=True))
        metadata, _ = dashboard.separar_presentacion(respuesta.get_data(as_text=True))
        self.assertEqual(metadata['diagnosticos'], self.metadata['diagnosticos'])
        self.assertEqual(descarga.data, self.html.encode('utf-8'))
        self.assertIn('attachment;', descarga.headers['Content-Disposition'])
        self.assertIn(ruta.name, historial.get_data(as_text=True))
        self.assertNotIn('href="/static', descarga.get_data(as_text=True))
        self.assertNotIn('src="/static', descarga.get_data(as_text=True))

    def test_informe_anterior_sin_diagnostico_sigue_abriendo(self):
        metadata = {k: v for k, v in self.metadata.items() if k != 'diagnosticos'}
        paneles = {k: '<p>Resultado histórico conservado</p>' for k in self.paneles}
        html = reporting.MARCA_INICIO + dashboard.renderizar_dashboard(
            self.parametros, contenidos=paneles, metadata=metadata, modo_local=False) + reporting.MARCA_FINAL
        ruta = reporting.guardar_informe_html(html, self.carpeta, datetime.now(timezone.utc))
        vista = self.cliente.get('/informes/' + ruta.name)
        self.assertEqual(vista.status_code, 200)
        self.assertIn('Resultado histórico conservado', vista.get_data(as_text=True))
        self.assertNotIn('Diagnóstico y coherencia física', vista.get_data(as_text=True))

    def test_ofat_real_con_no_motor_y_agregacion(self):
        respuesta = self.cliente.post('/', data={**self.form, 'accion': 'sensibilidad',
            'sens_parametro': 'T3', 'sens_minimo': '300', 'sens_maximo': '1600', 'sens_muestras': '3'})
        self.assertEqual(respuesta.status_code, 303)
        vista = self.cliente.get(respuesta.location)
        metadata, paneles = dashboard.separar_presentacion(vista.get_data(as_text=True))
        datos = metadata['diagnosticos']['sensibilidad']
        self.assertGreater(datos['resumen']['atencion'], 0)
        self.assertGreater(sum(datos['resumen'].values()), len(datos['items']))
        for estado in datos['resumen']:
            self.assertEqual(sum(item['conteos'][estado] for item in datos['items']), datos['resumen'][estado])
        self.assertIn('Contexto del ejemplo mostrado', paneles['sensibilidad'])
        descarga = self.cliente.get(respuesta.location + '?descargar=1')
        self.assertEqual(descarga.status_code, 200)
        self.assertIn('Diagnóstico y coherencia física', descarga.get_data(as_text=True))

    def test_mapa_real_celdas_y_cortes_con_ubicacion(self):
        respuesta = self.cliente.post('/', data={**self.form, 'accion': 'mapa',
            'mapa_rp_min': '1', 'mapa_rp_max': '30', 'mapa_T3_min': '500', 'mapa_T3_max': '1600',
            'mapa_n_rp': '3', 'mapa_n_T3': '3', 'mapa_escala': 'lineal', 'mapa_cortes': '700'})
        self.assertEqual(respuesta.status_code, 303)
        vista = self.cliente.get(respuesta.location)
        metadata, paneles = dashboard.separar_presentacion(vista.get_data(as_text=True))
        datos = metadata['diagnosticos']['mapa']
        self.assertGreater(datos['resumen']['atencion'], 0)
        self.assertTrue(any('Corte adicional' in item['grupo'] for item in datos['items']))
        self.assertTrue(any('rp=' in item.get('contexto', '') for item in datos['items']))
        self.assertIn('Diagnóstico y coherencia física', paneles['mapa'])

    def test_segunda_ley_real_no_motor_y_actualizacion_T0(self):
        form = {**self.form, 'accion': 'segunda_ley', 'T3': '400', 'T0': '300'}
        respuesta = self.cliente.post('/', data=form)
        self.assertEqual(respuesta.status_code, 303)
        vista = self.cliente.get(respuesta.location)
        metadata, paneles = dashboard.separar_presentacion(vista.get_data(as_text=True))
        datos = metadata['diagnosticos']['segunda_ley']
        self.assertGreater(datos['resumen']['atencion'], 0)
        self.assertGreater(datos['resumen']['no_evaluable'], 0)
        self.assertIn('Diagnóstico y coherencia física', paneles['segunda_ley'])
        form.update(T0='320', informe_origen=respuesta.location.rsplit('/', 1)[-1])
        with patch('viabilidad.evaluar_punto', side_effect=AssertionError('No recalcular al cambiar T0')):
            nueva = self.cliente.post('/', data=form)
        self.assertEqual(nueva.status_code, 303)
        meta_nueva, _ = dashboard.separar_presentacion(self.cliente.get(nueva.location).get_data(as_text=True))
        self.assertEqual(meta_nueva['segunda_ley']['T0'], 320.)

    def test_render_escapa_texto_y_deja_details_nativos(self):
        dato = deepcopy(self.metadata['diagnosticos']['resultados'])
        dato['alcance'] = '<script>malo()</script>'
        dato['items'][0].update(nombre='<img src=x>', motivo='<b>motivo</b>')
        html = renderizar_diagnostico(dato, 'prueba"<')
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('&lt;img src=x&gt;', html)
        self.assertIn('<details class="diagnostico-explicacion">', html)
        self.assertIn('data-label="Tolerancia"', html)

    def test_estructura_del_panel_autonomo_y_referencias_accesibles(self):
        class EstructuraDiagnostico(HTMLParser):
            def __init__(self):
                super().__init__()
                self.ids = set()
                self.referencias = []
                self.abiertos = 0
                self.cerrados = 0
                self.repetidos = set()

            def handle_starttag(self, tag, attrs):
                a = dict(attrs)
                identificador = a.get('id', '')
                if identificador.startswith('diagnostico-'):
                    if identificador in self.ids:
                        self.repetidos.add(identificador)
                    self.ids.add(identificador)
                if a.get('aria-labelledby', '').startswith('diagnostico-'):
                    self.referencias.append(a['aria-labelledby'])
                if tag == 'details':
                    self.abiertos += 1

            def handle_endtag(self, tag):
                if tag == 'details':
                    self.cerrados += 1

        parser = EstructuraDiagnostico()
        parser.feed(self.html)
        self.assertFalse(parser.repetidos)
        self.assertTrue(set(parser.referencias) <= parser.ids)
        self.assertGreater(parser.abiertos, 0)
        self.assertEqual(parser.abiertos, parser.cerrados)
        self.assertIn('@media(max-width:760px)', self.html)
        self.assertIn('.diagnostico-tabla td::before', self.html)

    def test_agregacion_conserva_una_advertencia_y_no_oculta_no_evaluables(self):
        base = self.metadata['diagnosticos']['resultados']['items'][0]
        items = [{**base, 'estado': estado, 'contexto': str(i), 'residuo': float(i), 'tolerancia': 1.}
                 for i, estado in enumerate(('cumple', 'no_evaluable', 'atencion', 'cumple'))]
        agregado = resumir_diagnosticos(iter(items), 'Ejemplo', agrupar=True)
        self.assertEqual(agregado['resumen'], dict(cumple=2, atencion=1, no_evaluable=1))
        self.assertEqual(len(agregado['items']), 1)
        self.assertEqual(agregado['items'][0]['contexto'], '2')
        json.dumps(agregado, allow_nan=False)

    def test_diagnostico_no_modifica_resultados_y_ausencia_sl_es_explicita(self):
        p, ideal, real = deepcopy(self.args[:3])
        antes = deepcopy((p, ideal, real))
        datos = diagnostico_simulacion(p, ideal, real)
        self.assertEqual((p, ideal, real), antes)
        self.assertGreater(datos['resumen']['no_evaluable'], 0)
        self.assertEqual(datos['resumen']['atencion'], 0)


if __name__ == '__main__':
    unittest.main()
