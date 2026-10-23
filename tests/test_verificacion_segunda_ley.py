"""V.3: contraste independiente de entropía y exergía, sin alterar física."""

from copy import deepcopy
from decimal import Decimal, localcontext
from math import isfinite, log
from unittest import TestCase
from unittest.mock import patch

from matplotlib.axes import Axes

import main
import reporting
import segunda_ley as sl
from viabilidad import ErrorNumerico, evaluar_punto


def entropia_decimal(Ti, pi, Tj, pj, cp, gamma):
    """Δs del gas ideal [kJ/(kg K)] con logaritmos Decimal de 70 dígitos."""
    with localcontext() as contexto:
        contexto.prec = 70
        ti, p_i, tj, p_j, c, g = map(
            lambda x: Decimal(str(x)), (Ti, pi, Tj, pj, cp, gamma))
        R = c * (g - 1) / g
        termica = c * (tj / ti).ln() / 1000
        presion = -R * (p_j / p_i).ln() / 1000
        return tuple(float(x) for x in (termica, presion, termica + presion))


def estados_referencia(parametros):
    """Estados T [K], p [kPa], trabajos [kJ/kg], sin evaluador propio."""
    p = parametros
    a = (p['gamma'] - 1) / p['gamma']
    rp, delta = p['relacion_presiones'], p['perdida_presion_combustor']
    p2, p3 = p['p1'] * rp, p['p1'] * rp * (1 - delta)
    t2 = p['T1'] * (1 + (rp**a - 1) / p['eta_c'])
    t4 = p['T3'] * (1 - p['eta_t'] * (1 - (rp * (1 - delta))**(-a)))
    t = (p['T1'], t2, p['T3'], t4)
    presiones = (p['p1'], p2, p3, p['p1'])
    k = p['cp'] / 1000
    return dict(temperaturas=t, presiones=presiones,
                wc=k * (t2 - t[0]), wt=k * (t[2] - t4))


class VerificacionSegundaLeyIndependiente(TestCase):
    def setUp(self):
        self.p = main.PARAMETROS_PREDETERMINADOS.copy()

    def punto(self, parametros):
        p = parametros
        return evaluar_punto(p['T1'], p['T3'], p['gamma'], p['cp'],
                            p['relacion_presiones'], p['p1'], p['eta_c'],
                            p['eta_t'], p['perdida_presion_combustor'])

    def test_cuatro_entropias_incrementos_y_referencias_decimales(self):
        perfiles = (self.p,
                    {**self.p, 'T1': 305., 'T3': 1450., 'relacion_presiones': 6.,
                     'gamma': 1.32, 'eta_c': .72, 'eta_t': .96,
                     'perdida_presion_combustor': .12},
                    {**self.p, 'T3': 2200., 'relacion_presiones': 22.,
                     'gamma': 1.52, 'eta_c': .93, 'eta_t': .78,
                     'perdida_presion_combustor': 0.})
        for p in perfiles:
            with self.subTest(rp=p['relacion_presiones'], gamma=p['gamma']):
                oracle = estados_referencia(p)
                d = sl.analizar_estados(self.punto(p), p['cp'], p['gamma'])
                self.assertEqual(d['entropias'][0], 0.)
                for i in range(4):
                    self.assertAlmostEqual(d['temperaturas'][i], oracle['temperaturas'][i], delta=1e-11)
                    self.assertAlmostEqual(d['presiones'][i], oracle['presiones'][i], delta=2e-12)
                    ref = entropia_decimal(oracle['temperaturas'][0], oracle['presiones'][0],
                                           oracle['temperaturas'][i], oracle['presiones'][i],
                                           p['cp'], p['gamma'])
                    self.assertAlmostEqual(d['entropias'][i], ref[2], delta=3e-13)
                    if i:
                        salto = entropia_decimal(oracle['temperaturas'][i-1], oracle['presiones'][i-1],
                                                 oracle['temperaturas'][i], oracle['presiones'][i],
                                                 p['cp'], p['gamma'])[2]
                        self.assertAlmostEqual(d['entropias'][i]-d['entropias'][i-1], salto, delta=3e-13)

    def test_generaciones_analiticas_con_perdidas_independientes(self):
        perfiles = ((.85, .9, .05), (.7, 1., 0.), (1., .72, .16),
                    (.95, .97, .02))
        p = self.p
        a = (p['gamma'] - 1) / p['gamma']
        x = p['relacion_presiones']**a
        for ec, et, delta in perfiles:
            with self.subTest(eta_c=ec, eta_t=et, delta=delta):
                q = {**p, 'eta_c': ec, 'eta_t': et, 'perdida_presion_combustor': delta}
                d = sl.analizar_estados(self.punto(q), p['cp'], p['gamma'])
                e = (p['relacion_presiones']*(1-delta))**a
                sc = p['cp']/1000 * log((1+(x-1)/ec)/x)
                st = p['cp']/1000 * log((1-et*(1-1/e))*e)
                self.assertEqual(d['estado'], 'motor')
                for componente, referencia in (('compresor', sc), ('turbina', st)):
                    self.assertGreaterEqual(referencia, -2e-15)
                    self.assertAlmostEqual(d['componentes'][componente]['valor'], referencia, delta=5e-13)
                if ec == 1.:
                    self.assertAlmostEqual(d['componentes']['compresor']['valor'], 0., delta=3e-13)
                if et == 1.:
                    self.assertAlmostEqual(d['componentes']['turbina']['valor'], 0., delta=3e-13)

    def test_reversibilidad_y_cancelacion_casi_isentropica(self):
        for eficiencia in (1., 1.-1e-8, 1.-1e-12):
            with self.subTest(eficiencia=eficiencia):
                p = {**self.p, 'eta_c': eficiencia, 'eta_t': eficiencia,
                     'perdida_presion_combustor': 0.}
                ref = estados_referencia(p)
                d = sl.analizar_estados(self.punto(p), p['cp'], p['gamma'])
                for componente, i, j in (('compresor', 0, 1), ('turbina', 2, 3)):
                    esperado = entropia_decimal(ref['temperaturas'][i], ref['presiones'][i],
                                                ref['temperaturas'][j], ref['presiones'][j],
                                                p['cp'], p['gamma'])[2]
                    gen = d['componentes'][componente]
                    self.assertAlmostEqual(gen['bruto'], esperado, delta=7e-13)
                    self.assertLess(abs(gen['bruto']-esperado), gen['tolerancia'])
                    self.assertGreaterEqual(gen['valor'], 0)
                    if eficiencia == 1.:
                        self.assertAlmostEqual(gen['valor'], 0., delta=1e-12)
        redondeo = sl.generacion_adiabatica(1., 1.-5e-12, 1.005)
        self.assertEqual(redondeo['valor'], 0.)
        self.assertLess(redondeo['bruto'], 0.)
        with self.assertRaises(sl.InconsistenciaSegundaLey):
            sl.generacion_adiabatica(1., 1.-5e-8, 1.005)

    def test_exergia_mediante_balances_alternativos_de_flujo(self):
        perfiles = (self.p, {**self.p, 'T3': 1800., 'relacion_presiones': 15.,
                            'eta_c': .78, 'eta_t': .84, 'perdida_presion_combustor': .08})
        for p in perfiles:
            for T0 in (270., 288.15, 330.):
                with self.subTest(rp=p['relacion_presiones'], T0=T0):
                    r = estados_referencia(p)
                    d = sl.analizar_estados(self.punto(p), p['cp'], p['gamma'], T0)
                    s = tuple(entropia_decimal(r['temperaturas'][0], r['presiones'][0],
                                               r['temperaturas'][i], r['presiones'][i],
                                               p['cp'], p['gamma'])[2] for i in range(4))
                    # ψ2−ψ1 y ψ3−ψ4: se omite una constante común arbitraria.
                    delta_psi_c = p['cp']/1000*(r['temperaturas'][1]-r['temperaturas'][0])-T0*(s[1]-s[0])
                    delta_psi_t = p['cp']/1000*(r['temperaturas'][2]-r['temperaturas'][3])-T0*(s[2]-s[3])
                    ed_c = r['wc']-delta_psi_c
                    ed_t = delta_psi_t-r['wt']
                    self.assertAlmostEqual(d['componentes']['compresor']['exergia_destruida'], ed_c, delta=3e-10)
                    self.assertAlmostEqual(d['componentes']['turbina']['exergia_destruida'], ed_t, delta=3e-10)
                    self.assertAlmostEqual(d['suma_componentes'], ed_c+ed_t, delta=4e-10)
                    self.assertAlmostEqual(ed_c, T0*(s[1]-s[0]), delta=3e-10)
                    self.assertAlmostEqual(ed_t, T0*(s[3]-s[2]), delta=3e-10)

    def test_camara_y_presion_sin_atribuir_generacion(self):
        previos = []
        for delta in (0., .05, .2):
            p = {**self.p, 'perdida_presion_combustor': delta}
            r = estados_referencia(p)
            d = sl.analizar_estados(self.punto(p), p['cp'], p['gamma'])
            termica, presion, total = entropia_decimal(
                r['temperaturas'][1], r['presiones'][1], r['temperaturas'][2],
                r['presiones'][2], p['cp'], p['gamma'])
            self.assertAlmostEqual(d['camara']['termica'], termica, delta=3e-13)
            self.assertAlmostEqual(d['camara']['presion'], presion, delta=3e-13)
            self.assertAlmostEqual(d['camara']['total'], total, delta=3e-13)
            self.assertNotIn('generacion', d['camara'])
            previos.append((termica, presion, total))
        self.assertAlmostEqual(previos[0][1], 0., delta=1e-14)
        self.assertAlmostEqual(previos[0][0], previos[2][0], delta=1e-13)
        self.assertLess(previos[0][2], previos[1][2])
        self.assertLess(previos[1][2], previos[2][2])

    def test_invariantes_T0_cp_y_p1(self):
        original = sl.analizar_estados(self.punto(self.p), self.p['cp'], self.p['gamma'])
        estudio = {'T0': 288.15, 'modelos': {'noideal': original}}
        estudio_copia = deepcopy(estudio)
        nuevo = sl.actualizar_T0(estudio, 2*288.15)['modelos']['noideal']
        self.assertEqual(estudio, estudio_copia)
        for clave in ('temperaturas', 'presiones', 'entropias', 'camara'):
            self.assertEqual(nuevo[clave], original[clave])
        for nombre in ('compresor', 'turbina'):
            self.assertAlmostEqual(nuevo['componentes'][nombre]['exergia_destruida'],
                                   2*original['componentes'][nombre]['exergia_destruida'], delta=1e-10)
        for p, factor in (({**self.p, 'cp': self.p['cp']*1.7}, 1.7),
                          ({**self.p, 'p1': self.p['p1']*3.25}, 1.)):
            d = sl.analizar_estados(self.punto(p), p['cp'], p['gamma'])
            for a, b in zip(d['entropias'], original['entropias']):
                self.assertAlmostEqual(a, factor*b, delta=6e-13)
            for nombre in ('compresor', 'turbina'):
                self.assertAlmostEqual(d['componentes'][nombre]['exergia_destruida'],
                                       factor*original['componentes'][nombre]['exergia_destruida'], delta=2e-10)

    def test_extremos_logaritmicos_y_errores_de_representacion(self):
        # El cociente 1e300/1e-300 desbordaría en float; las entradas son finitas.
        q = sl.cambio_entropia(1e-300, 1e300, 1e300, 1e-300, 1005., 1.4)
        ref = entropia_decimal(1e-300, 1e300, 1e300, 1e-300, 1005., 1.4)
        self.assertTrue(all(isfinite(x) for x in q.values()))
        for clave, esperado in zip(('termica', 'presion', 'total'), ref):
            self.assertAlmostEqual(q[clave], esperado, delta=5e-12)
        q = sl.cambio_entropia(300., 100., 300.*(1+1e-13), 100., 1005., 1.4)
        cercano = entropia_decimal(300., 100., 300.*(1+1e-13), 100., 1005., 1.4)[2]
        self.assertAlmostEqual(q['total'], cercano, delta=2e-14)
        with self.assertRaises(ErrorNumerico):
            sl.cambio_entropia(300., 100., 400., 100., 5e-324, 1.4)
        for invalido in (0., -1., float('inf'), float('nan'), True):
            with self.subTest(T0=invalido), self.assertRaises(ValueError):
                sl.validar_referencia(invalido)
        for cp, gamma in ((0., 1.4), (-1., 1.4), (1005., 1.),
                          (1005., .999), (1005., float('inf'))):
            with self.subTest(cp=cp, gamma=gamma), self.assertRaises(ValueError):
                sl.cambio_entropia(300., 100., 400., 100., cp, gamma)
        # El producto T0*s_gen desborda y se clasifica, no se entrega como número.
        p_grande = {**self.p, 'cp': 20000.}
        punto = self.punto(p_grande)
        extremo = sl.analizar_segunda_ley({'ideal': punto, 'noideal': punto},
                                           p_grande['cp'], p_grande['gamma'], 1e308)
        self.assertEqual(extremo['modelos']['noideal']['estado'], 'limite_numerico')

    def test_no_motor_inconsistencia_y_diagnostico_sin_eficiencia(self):
        p = {**self.p, 'T3': 400., 'relacion_presiones': 50.}
        punto = self.punto(p)
        self.assertFalse(punto['viable'])
        self.assertIsNone(punto['rendimiento'])
        d = sl.analizar_estados(punto, p['cp'], p['gamma'])
        self.assertEqual(d['estado'], 'diagnostico_no_motor')
        self.assertEqual(d['viable'], False)
        self.assertEqual(d['motivos'], punto['motivos'])
        self.assertEqual(len(d['entropias']), 4)
        self.assertNotIn('eficiencia_exergetica_global', d)
        alterado = deepcopy(self.punto(self.p))
        alterado['temperaturas'] = (self.p['T1'], 300., self.p['T3'], 900.)
        inconsistente = sl.analizar_estados(alterado, self.p['cp'], self.p['gamma'])
        self.assertEqual(inconsistente['estado'], 'inconsistencia')
        self.assertIn('compresor', inconsistente['motivo'])
        self.assertEqual(len(inconsistente['entropias']), 4)
        self.assertNotIn('componentes', inconsistente)
        self.assertNotIn('suma_componentes', inconsistente)

    def test_datos_enviados_a_graficas_y_tablas_de_informe(self):
        ideal_p = {**self.p, 'eta_c': 1., 'eta_t': 1.,
                   'perdida_presion_combustor': 0.}
        estados = {'ideal': self.punto(ideal_p), 'noideal': self.punto(self.p)}
        estudio = sl.analizar_segunda_ley(estados, self.p['cp'], self.p['gamma'])
        trazas, barras = [], []
        trazar, bar = Axes.plot, Axes.bar

        def capturar_traza(ejes, *args, **kwargs):
            if len(args) >= 2 and isinstance(args[0], tuple) and len(args[0]) == 5:
                trazas.append((args[0], args[1], kwargs.get('label', '')))
            return trazar(ejes, *args, **kwargs)

        def capturar_barras(ejes, *args, **kwargs):
            if len(args) >= 2 and len(args[1]) == 2:
                barras.append((tuple(args[1]), kwargs.get('label', '')))
            return bar(ejes, *args, **kwargs)

        with patch.object(Axes, 'plot', capturar_traza), patch.object(Axes, 'bar', capturar_barras):
            figuras = sl.crear_graficas_segunda_ley(estudio)
        self.assertEqual(set(figuras), {'estados_ts', 'exergia_componentes'})
        self.assertEqual(len(trazas), 2)
        self.assertEqual(len(barras), 2)
        for indice, modelo in enumerate(('ideal', 'noideal')):
            d = estudio['modelos'][modelo]
            self.assertEqual(tuple(trazas[indice][0]), (*d['entropias'], d['entropias'][0]))
            self.assertEqual(tuple(trazas[indice][1]), (*d['temperaturas'], d['temperaturas'][0]))
            self.assertEqual(barras[indice][0], tuple(d['componentes'][k]['exergia_destruida']
                                                       for k in ('compresor', 'turbina')))
            self.assertIn('Ideal' if modelo == 'ideal' else 'No ideal', trazas[indice][2])
        html = reporting.seccion_segunda_ley_html(estudio)
        self.assertIn('s_gen [kJ/(kg·K)]', html)
        self.assertIn('eD [kJ/kg]', html)
        self.assertIn('Entropía específica relativa s [kJ/(kg·K)]', html)
        self.assertIn('Temperatura [K]', html)
        self.assertIn('No calculamos una eficiencia exergética global.', html)
        for modelo in ('ideal', 'noideal'):
            d = estudio['modelos'][modelo]
            for componente in ('compresor', 'turbina'):
                self.assertIn(f"{d['componentes'][componente]['exergia_destruida']:.6f}", html)
        no_motor = {**self.p, 'T3': 400., 'relacion_presiones': 50.}
        diagnostico = sl.analizar_segunda_ley(
            {'ideal': self.punto({**no_motor, 'eta_c': 1., 'eta_t': 1.,
                                  'perdida_presion_combustor': 0.}),
             'noideal': self.punto(no_motor)}, no_motor['cp'], no_motor['gamma'])
        self.assertIn('diagnóstico no motor', sl.crear_graficas_segunda_ley(diagnostico)['estados_ts'])
        self.assertIn('diagnostico_no_motor', reporting.seccion_segunda_ley_html(diagnostico))
