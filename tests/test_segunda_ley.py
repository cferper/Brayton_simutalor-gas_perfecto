"""Segunda ley: balances independientes y presentación sin cambiar Fases 1–5."""
from copy import deepcopy
from datetime import datetime
from math import log
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main
import reporting
import segunda_ley as sl
import web_app
from viabilidad import evaluar_punto, ErrorNumerico


class SegundaLeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = main.PARAMETROS_PREDETERMINADOS.copy()
        p = cls.p
        cls.estados = dict(ideal=evaluar_punto(p['T1'], p['T3'], p['gamma'], p['cp'], p['relacion_presiones'], p['p1']),
            noideal=evaluar_punto(p['T1'], p['T3'], p['gamma'], p['cp'], p['relacion_presiones'], p['p1'], p['eta_c'], p['eta_t'], p['perdida_presion_combustor']))
        cls.e = sl.analizar_segunda_ley(cls.estados, p['cp'], p['gamma'])
        cls.html = reporting.crear_informe_segunda_ley_html(p, cls.e, datetime.now(), dict(commit='prueba', modificado=True))

    def test_estados_y_entropias_relativas(self):
        for k in ('ideal', 'noideal'):
            d = self.e['modelos'][k]
            self.assertEqual(len(d['entropias']), 4); self.assertEqual(d['entropias'][0], 0)
            self.assertEqual(d['temperaturas'], self.estados[k]['temperaturas'])

    def test_identidad_gas_ideal_y_unidades(self):
        d = self.e['modelos']['noideal']; p = self.p
        R = p['cp']*(1-1/p['gamma'])
        for i in range(4):
            esperado = (p['cp']*log(d['temperaturas'][i]/p['T1'])-R*log(d['presiones'][i]/p['p1']))/1000
            self.assertAlmostEqual(d['entropias'][i], esperado, places=12)

    def test_contraste_analitico_independiente(self):
        p = self.p; a = (p['gamma']-1)/p['gamma']; rp = p['relacion_presiones']
        q = rp**a; expansion = rp*(1-p['perdida_presion_combustor'])
        sc = p['cp']/1000*log((1+(q-1)/p['eta_c'])/q)
        st = p['cp']/1000*log((1-p['eta_t']*(1-expansion**(-a)))*expansion**a)
        for clave, esperado in (('compresor', sc), ('turbina', st)):
            c = self.e['modelos']['noideal']['componentes'][clave]
            self.assertAlmostEqual(c['valor'], esperado, places=12)
            self.assertAlmostEqual(c['exergia_destruida'], 288.15*esperado, places=10)

    def test_generacion_no_negativa(self):
        for d in self.e['modelos'].values():
            for c in d['componentes'].values(): self.assertGreaterEqual(c['valor'], 0)

    def test_limite_reversible(self):
        p = self.p
        punto = evaluar_punto(p['T1'], p['T3'], p['gamma'], p['cp'], p['relacion_presiones'], p['p1'])
        d = sl.analizar_estados(punto, p['cp'], p['gamma'])
        for c in d['componentes'].values(): self.assertAlmostEqual(c['valor'], 0, places=12)
        self.assertAlmostEqual(d['suma_componentes'], 0, places=10)

    def test_eficiencias(self):
        p = self.p
        for ec, et, equipo in ((.7, p['eta_t'], 'compresor'), (p['eta_c'], .7, 'turbina')):
            punto = evaluar_punto(p['T1'], p['T3'], p['gamma'], p['cp'], 10, p['p1'], ec, et, .05)
            d = sl.analizar_estados(punto, p['cp'], p['gamma'])
            self.assertGreater(d['componentes'][equipo]['valor'], self.e['modelos']['noideal']['componentes'][equipo]['valor'])

    def test_T0_proporcional_sin_modificar_estados(self):
        previo = deepcopy(self.e)
        with patch.object(sl, 'cambio_entropia', side_effect=AssertionError('No recalcular')):
            doble = sl.actualizar_T0(self.e, 576.3)
        self.assertEqual(self.e, previo)
        for k in ('ideal', 'noideal'):
            self.assertEqual(doble['modelos'][k]['entropias'], self.e['modelos'][k]['entropias'])
            self.assertEqual(doble['modelos'][k]['temperaturas'], self.e['modelos'][k]['temperaturas'])
            self.assertAlmostEqual(doble['modelos'][k]['suma_componentes'], 2*self.e['modelos'][k]['suma_componentes'])

    def test_referencia_invalida(self):
        for x in (0, -1, float('nan'), float('inf'), True):
            with self.subTest(x=x), self.assertRaises(ValueError): sl.validar_referencia(x)

    def test_estados_invalidos(self):
        with self.assertRaises(ValueError): sl.cambio_entropia(0,100,400,100,1005,1.4)
        with self.assertRaises(ValueError): sl.analizar_estados({**self.estados['ideal'], 'temperaturas': (300,400)},1005,1.4)
        with self.assertRaises(ValueError): sl.cambio_entropia(300,100,400,100,1005,1)

    def test_negativo_importante_no_se_recorta(self):
        with self.assertRaises(sl.InconsistenciaSegundaLey): sl.generacion_adiabatica(1,.9)
        r = sl.generacion_adiabatica(1,1-1e-12)
        self.assertEqual(r['valor'], 0); self.assertLess(r['bruto'], 0)

    def test_inconsistencia_identificada(self):
        estados = deepcopy(self.estados)
        estados['noideal']['temperaturas'] = (288.15, 300, 1600, 900)
        e = sl.analizar_segunda_ley(estados,1005,1.4)
        self.assertEqual(e['modelos']['noideal']['estado'], 'inconsistencia')
        self.assertEqual(len(e['modelos']['noideal']['entropias']),4)

    def test_camara_no_es_generacion(self):
        c = self.e['modelos']['noideal']['camara']
        self.assertAlmostEqual(c['total'], c['termica']+c['presion'])
        R = 1005*(1-1/1.4)/1000
        self.assertAlmostEqual(c['presion'], -R*log(.95))
        self.assertNotIn('generacion', c)
        self.assertIn('No es la generación de entropía de la cámara', self.html)

    def test_diagnostico_no_motor(self):
        p = self.p
        punto = evaluar_punto(p['T1'],400,p['gamma'],p['cp'],50,p['p1'],.85,.9,.05)
        self.assertFalse(punto['viable'])
        d = sl.analizar_estados(punto,1005,1.4)
        self.assertEqual(d['estado'], 'diagnostico_no_motor'); self.assertEqual(len(d['entropias']),4)

    def test_limites_numericos(self):
        e = sl.analizar_segunda_ley(self.estados,1e308,1.4,1e308)
        self.assertEqual(e['modelos']['noideal']['estado'], 'limite_numerico')
        with self.assertRaises(ErrorNumerico): sl.actualizar_T0({**self.e, 'modelos': {'noideal': {**self.e['modelos']['noideal'], 'componentes': {'c':dict(valor=1e308)}}}},1e308)

    def test_dos_svg_autocontenidos(self):
        g = sl.crear_graficas_segunda_ley(self.e)
        self.assertEqual(set(g), {'estados_ts','exergia_componentes'})
        for svg in g.values():
            self.assertTrue(svg.startswith('<svg')); self.assertNotIn('<image ', svg)
        self.assertEqual(self.html.count('data-segunda-ley='),2)
        self.assertIn('sólo como guía visual',self.html)

    def test_total_parcial_y_no_eficiencia_global(self):
        d = self.e['modelos']['noideal']
        self.assertAlmostEqual(d['suma_componentes'], sum(c['exergia_destruida'] for c in d['componentes'].values()))
        self.assertIn('no es la pérdida total de la instalación',self.html)

    def test_flask_diagnostico_reutilizacion_y_descarga(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(web_app.app.config, TESTING=True, OUTPUTS_DIR=Path(d)):
            cliente = web_app.app.test_client()
            datos = {k:str(v) for k,v in web_app.valores_formulario().items()}
            datos.update(accion='segunda_ley',T0='288.15',T3='400',relacion_presiones='50')
            r = cliente.post('/',data=datos); self.assertEqual(r.status_code,303)
            html = cliente.get(r.location).get_data(as_text=True)
            self.assertIn('diagnostico_no_motor',html)
            self.assertEqual(cliente.get(r.location+'?descargar=1').get_data(as_text=True), next(Path(d).glob('*.html')).read_text(encoding='utf-8'))
            datos.update(T0='300',informe_origen=r.location.rsplit('/',1)[1])
            with patch('viabilidad.evaluar_punto',side_effect=AssertionError('No reevaluar')):
                r2=cliente.post('/',data=datos)
            self.assertEqual(r2.status_code,303)
            datos['T0']='0'; self.assertEqual(cliente.post('/',data=datos).status_code,400)

    def test_fuente_reutilizada_solo_si_coinciden_parametros(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(web_app.app.config, OUTPUTS_DIR=Path(d)):
            ruta=reporting.guardar_informe_html(self.html,d,datetime.now())
            self.assertIsNotNone(web_app.estudio_conservado(ruta.name,self.p))
            self.assertIsNone(web_app.estudio_conservado(ruta.name,{**self.p,'T3':1700}))
            self.assertIsNone(web_app.estudio_conservado('../zip.zip',self.p))


if __name__ == '__main__': unittest.main()
