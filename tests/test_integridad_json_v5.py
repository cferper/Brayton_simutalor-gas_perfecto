"""V.5: JSON conservado inválido no puede alimentar una actualización T0."""
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
from io import StringIO
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import dashboard
import main
import reporting
import segunda_ley
import web_app
from viabilidad import evaluar_punto


class IntegridadJSONV5(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.salidas = Path(temporal.name) / 'outputs'
        config = patch.dict(web_app.app.config, OUTPUTS_DIR=self.salidas, TESTING=True)
        config.start()
        self.addCleanup(config.stop)
        self.cliente = web_app.app.test_client()
        self.p = main.PARAMETROS_PREDETERMINADOS.copy()
        self.form = {k: str(v * 100 if k == 'perdida_presion_combustor' else v)
                     for k, v in self.p.items()}
        p = self.p
        puntos = dict(ideal=evaluar_punto(p['T1'], p['T3'], p['gamma'], p['cp'], p['relacion_presiones'], p['p1']),
                      noideal=evaluar_punto(p['T1'], p['T3'], p['gamma'], p['cp'], p['relacion_presiones'],
                                             p['p1'], p['eta_c'], p['eta_t'], p['perdida_presion_combustor']))
        self.estudio = segunda_ley.analizar_segunda_ley(puntos, p['cp'], p['gamma'], 288.15)

    def informe(self, estudio=None):
        metadata = dict(dashboard=1, tipo='segunda_ley', parametros=self.p.copy(),
                        segunda_ley=self.estudio if estudio is None else estudio,
                        fecha='2026-10-23T10:00:00+02:00', git=dict(commit='a' * 40, modificado=False))
        paneles = {k: '<p>Informe conservado</p>' for k in
                   ('resultados', 'optimizacion', 'sensibilidad', 'mapa', 'segunda_ley')}
        valores = self.p.copy()
        valores['perdida_presion_combustor'] *= 100
        valores['T0'] = 288.15
        html = (reporting.MARCA_INICIO + dashboard.renderizar_dashboard(
            valores, contenidos=paneles, metadata=metadata, modo_local=False) + reporting.MARCA_FINAL)
        return reporting.guardar_informe_html(html, self.salidas, datetime.now(timezone.utc))

    def adulterar(self, ruta, cambio):
        html = ruta.read_text(encoding='utf-8')
        patron = r'(<script type="application/json" id="brayton-metadata">)(.*?)(</script>)'
        metadata = json.loads(re.search(patron, html, re.S)[2])
        cambio(metadata)
        html = re.sub(patron, lambda m: m[1] + json.dumps(metadata, allow_nan=True) + m[3], html, count=1, flags=re.S)
        ruta.write_text(html, encoding='utf-8')
        return ruta.read_bytes()

    def test_estudio_real_serializado_es_reutilizable(self):
        ruta = self.informe()
        estudio = web_app.estudio_conservado(ruta.name, self.p)
        self.assertEqual(estudio, json.loads(json.dumps(self.estudio)))
        self.assertTrue(segunda_ley.validar_estudio_reutilizable(estudio, self.p))

    def test_nueve_parametros_distintos_no_reutilizan(self):
        ruta = self.informe()
        for nombre in self.p:
            with self.subTest(nombre=nombre):
                otros = {**self.p, nombre: self.p[nombre] * 1.01}
                self.assertIsNone(web_app.estudio_conservado(ruta.name, otros))

    def test_campos_obligatorios_y_estructuras_incompletas(self):
        cambios = (
            lambda d: d['segunda_ley'].pop('modelos'),
            lambda d: d['segunda_ley']['modelos'].pop('ideal'),
            lambda d: d['segunda_ley']['modelos']['ideal'].pop('componentes'),
            lambda d: d['segunda_ley']['modelos']['ideal']['componentes'].pop('turbina'),
            lambda d: d['segunda_ley']['modelos']['ideal'].update(temperaturas=[288., 400.]),
            lambda d: d['segunda_ley']['modelos']['noideal'].update(entropias=[0., 1., 2.]),
            lambda d: d['segunda_ley']['modelos']['noideal'].update(camara={}),
        )
        for i, cambio in enumerate(cambios):
            with self.subTest(caso=i):
                ruta = self.informe()
                antes = self.adulterar(ruta, cambio)
                self.assertIsNone(web_app.estudio_conservado(ruta.name, self.p))
                self.assertEqual(antes, ruta.read_bytes())

    def test_tipos_incorrectos_incluidos_booleanos(self):
        cambios = (
            lambda d: d['segunda_ley'].update(cp=True),
            lambda d: d['segunda_ley'].update(T0='288.15'),
            lambda d: d['segunda_ley']['modelos']['ideal'].update(temperaturas='texto'),
            lambda d: d['segunda_ley']['modelos']['ideal']['temperaturas'].__setitem__(1, True),
            lambda d: d['segunda_ley']['modelos']['noideal'].update(viable=1),
            lambda d: d['segunda_ley']['modelos']['noideal']['componentes']['turbina'].update(valor=False),
        )
        for i, cambio in enumerate(cambios):
            with self.subTest(caso=i):
                ruta = self.informe()
                self.adulterar(ruta, cambio)
                self.assertIsNone(web_app.estudio_conservado(ruta.name, self.p))

    def test_none_nan_infinito_y_cadenas_no_numericas(self):
        for valor in (None, float('nan'), float('inf'), float('-inf'), 'nan'):
            with self.subTest(valor=str(valor)):
                ruta = self.informe()
                self.adulterar(ruta, lambda d: d['segunda_ley']['modelos']['ideal']['entropias'].__setitem__(2, valor))
                self.assertIsNone(web_app.estudio_conservado(ruta.name, self.p))

    def test_incoherencia_de_estados_entropia_exergia_y_camara(self):
        cambios = (
            lambda d: d['segunda_ley']['modelos']['ideal']['temperaturas'].__setitem__(1, 444.),
            lambda d: d['segunda_ley']['modelos']['noideal']['presiones'].__setitem__(2, 999.),
            lambda d: d['segunda_ley']['modelos']['ideal']['entropias'].__setitem__(1, 0.4),
            lambda d: d['segunda_ley']['modelos']['noideal']['componentes']['turbina'].update(bruto=0.4),
            lambda d: d['segunda_ley']['modelos']['noideal']['componentes']['turbina'].update(exergia_destruida=100.),
            lambda d: d['segunda_ley']['modelos']['noideal'].update(suma_componentes=0.),
            lambda d: d['segunda_ley']['modelos']['noideal']['camara'].update(total=12.),
            lambda d: d['segunda_ley']['modelos']['noideal'].update(viable=False, estado='diagnostico_no_motor'),
        )
        for i, cambio in enumerate(cambios):
            with self.subTest(caso=i):
                ruta = self.informe()
                self.adulterar(ruta, cambio)
                self.assertIsNone(web_app.estudio_conservado(ruta.name, self.p))

    def test_json_interno_danado_recalcula_y_conserva_original(self):
        ruta = self.informe()
        original = self.adulterar(ruta, lambda d: d['segunda_ley']['modelos']['ideal'].pop('componentes'))
        with patch.object(web_app, 'ejecutar_segunda_ley', return_value=self.salidas / 'nuevo.html') as ejecutar:
            r = self.cliente.post('/', data={**self.form, 'accion': 'segunda_ley',
                                              'T0': '300', 'informe_origen': ruta.name})
        self.assertEqual(r.status_code, 303)
        ejecutar.assert_called_once_with(self.salidas, self.p, 300., None)
        self.assertEqual(ruta.read_bytes(), original)
        consulta = self.cliente.get('/informes/' + ruta.name)
        self.assertEqual(consulta.status_code, 200)
        self.assertIn('no se reutilizarán', consulta.get_data(as_text=True))
        self.assertEqual(self.cliente.get('/informes/' + ruta.name + '?descargar=1').data, original)

    def test_json_externo_malformado_o_con_tipos_invalidos_no_provoca_500(self):
        ruta = self.informe()
        original = ruta.read_text(encoding='utf-8')
        roto = original.replace('"dashboard": 1', '"dashboard": {', 1)
        ruta.write_text(roto, encoding='utf-8')
        self.assertIsNone(web_app.estudio_conservado(ruta.name, self.p))
        self.assertEqual(self.cliente.get('/informes/' + ruta.name).status_code, 422)
        self.assertIn('metadatos inválidos', web_app.listar_informes()[0]['tipo'])
        self.assertEqual(self.cliente.get('/informes/' + ruta.name + '?descargar=1').data,
                         roto.encode('utf-8'))
        ruta.write_text(original, encoding='utf-8')
        self.adulterar(ruta, lambda d: d.update(parametros={'T1': True}))
        self.assertEqual(self.cliente.get('/informes/' + ruta.name).status_code, 422)

    def test_informe_sin_metadata_historico_sigue_abriendo(self):
        contenido = reporting.MARCA_INICIO + '<html><header>Histórico</header><body>Válido</body></html>' + reporting.MARCA_FINAL
        ruta = reporting.guardar_informe_html(contenido, self.salidas, datetime.now(timezone.utc))
        self.assertEqual(self.cliente.get('/informes/' + ruta.name).status_code, 200)
        self.assertEqual(self.cliente.get('/informes/' + ruta.name + '?descargar=1').get_data(as_text=True), contenido)

    def test_T0_real_actualiza_exergia_sin_evaluar_puntos(self):
        ruta = self.informe()
        with patch('viabilidad.evaluar_punto', side_effect=AssertionError('recalculo de estados')):
            with redirect_stdout(StringIO()):
                r = self.cliente.post('/', data={**self.form, 'accion': 'segunda_ley',
                                                  'T0': '300', 'informe_origen': ruta.name})
        self.assertEqual(r.status_code, 303)
        nuevo = self.salidas / r.location.rsplit('/', 1)[1]
        actualizado, _ = dashboard.separar_presentacion(nuevo.read_text(encoding='utf-8'))
        self.assertEqual(actualizado['segunda_ley']['T0'], 300.)
        for nombre in ('ideal', 'noideal'):
            previo, posterior = self.estudio['modelos'][nombre], actualizado['segunda_ley']['modelos'][nombre]
            self.assertEqual(list(previo['entropias']), posterior['entropias'])
            self.assertEqual(list(previo['temperaturas']), posterior['temperaturas'])
            for c in ('compresor', 'turbina'):
                self.assertAlmostEqual(posterior['componentes'][c]['exergia_destruida'],
                                       300 * previo['componentes'][c]['valor'])

    def test_caso_no_motor_completo_tambien_es_reutilizable(self):
        p = {**self.p, 'T3': 400., 'relacion_presiones': 50.}
        puntos = dict(ideal=evaluar_punto(p['T1'], p['T3'], p['gamma'], p['cp'], p['relacion_presiones'], p['p1']),
                      noideal=evaluar_punto(p['T1'], p['T3'], p['gamma'], p['cp'], p['relacion_presiones'],
                                             p['p1'], p['eta_c'], p['eta_t'], p['perdida_presion_combustor']))
        estudio = json.loads(json.dumps(segunda_ley.analizar_segunda_ley(puntos, p['cp'], p['gamma'])))
        self.assertTrue(segunda_ley.validar_estudio_reutilizable(estudio, p))

    def test_ejecucion_directa_tampoco_acepta_json_invalido(self):
        adulterado = deepcopy(self.estudio)
        adulterado['modelos']['ideal'].pop('componentes')
        with patch.object(segunda_ley, 'actualizar_T0', side_effect=AssertionError('reutilizó estudio inválido')) as actualizar:
            with redirect_stdout(StringIO()):
                resultado = segunda_ley.ejecutar_segunda_ley(self.salidas, self.p, 300., adulterado)
        actualizar.assert_not_called()
        meta, _ = dashboard.separar_presentacion(resultado.read_text(encoding='utf-8'))
        self.assertEqual(meta['segunda_ley']['T0'], 300.)


if __name__ == '__main__':
    unittest.main()
