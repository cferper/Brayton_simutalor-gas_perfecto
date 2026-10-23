"""V.2: referencias físicas independientes para el mapa bidimensional rp–T3.

No se utilizan evaluadores, dominios ni optimizadores del proyecto para
construir los valores esperados; las bandas de aceptación se distinguen de
las desigualdades matemáticas estrictas.
"""

from importlib.util import find_spec
from math import log, sqrt
from unittest import TestCase, skipUnless
from unittest.mock import patch

import matplotlib.pyplot as plt
import numpy as np

import mapa_diseno as mapa
from main import PARAMETROS_PREDETERMINADOS


def referencia_termodinamica(parametros, rp, T3):
    """Estados K, energías kJ/kg y admisión calculados sólo con ecuaciones."""
    T1 = parametros['T1']
    ec, et = parametros['eta_c'], parametros['eta_t']
    delta = parametros['perdida_presion_combustor']
    a = (parametros['gamma'] - 1) / parametros['gamma']
    k = parametros['cp'] / 1000
    p1 = parametros['p1']
    p3 = p1 * rp * (1 - delta)
    T2 = T1 * (1 + (rp**a - 1) / ec)
    T4 = T3 * (1 - et * (1 - (rp * (1 - delta))**(-a)))
    wc, wt = k * (T2 - T1), k * (T3 - T4)
    W, Q = wt - wc, k * (T3 - T2)
    margenes = dict(compresion=rp - 1, expansion=p3 - p1,
                    calor_aportado=Q, trabajo_neto=W)
    escala = max(abs(wc), abs(wt), k * max(T1, T3))
    # Banda contractual de la versión comprobada, no frontera matemática.
    tol = 1e-10
    tolerancias = dict(compresion=tol * max(rp, 1),
                       expansion=tol * max(p3, p1),
                       calor_aportado=tol * escala,
                       trabajo_neto=tol * escala)
    estrictamente_motor = all(valor > 0 for valor in margenes.values())
    admitido = all(margenes[clave] > tolerancias[clave] for clave in margenes)
    return dict(temperaturas=(T1, T2, T3, T4), trabajo_compresor=wc,
                trabajo_turbina=wt, trabajo_neto=W, calor_aportado=Q,
                rendimiento=W / Q if admitido else None,
                estrictamente_motor=estrictamente_motor, admitido=admitido,
                margenes=margenes, tolerancias=tolerancias,
                motivos=tuple(k for k in margenes if margenes[k] <= tolerancias[k]))


def fronteras_cerradas(parametros, T3):
    """Intersección abierta de compresión, expansión, calor y Q(x)<0."""
    T1, ec, et = parametros['T1'], parametros['eta_c'], parametros['eta_t']
    delta = parametros['perdida_presion_combustor']
    a = (parametros['gamma'] - 1) / parametros['gamma']
    theta = T3 / T1
    h = theta * ec * et
    b = (1 - delta)**(-a)
    D = (h - 1)**2 - 4 * h * (b - 1)
    expansion = 1 / (1 - delta)
    calor = (1 + ec * (theta - 1))**(1 / a)
    trabajo = ()
    intervalo = ()
    if D > 0:
        x_bajo = (1 + h - sqrt(D)) / 2
        x_alto = (1 + h + sqrt(D)) / 2
        trabajo = (x_bajo**(1 / a), x_alto**(1 / a))
        inferior = max(1, expansion, trabajo[0])
        superior = min(calor, trabajo[1])
        if h > 1 and inferior < superior:
            intervalo = (inferior, superior)
    return dict(discriminante=D, h=h, b=b, expansion=expansion,
                calor=calor, trabajo=trabajo, intervalo=intervalo)


def rp_max_trabajo(parametros, T3):
    """Estacionario A deducido directamente de dW/d(rp**a)=0."""
    a = (parametros['gamma'] - 1) / parametros['gamma']
    ec, et = parametros['eta_c'], parametros['eta_t']
    delta = parametros['perdida_presion_combustor']
    return (ec * et * T3 / parametros['T1'] * (1 - delta)**(-a))**(1 / (2 * a))


class VerificacionMapaIndependiente(TestCase):
    def setUp(self):
        self.p = PARAMETROS_PREDETERMINADOS.copy()

    def test_celdas_estados_balances_signos_y_clasificacion(self):
        estudio = mapa.analizar_mapa(self.p, rp_min=.8, rp_max=100,
                                    T3_min=400, T3_max=1600, n_rp=9, n_T3=5,
                                    escala='lineal', cortes=(1000,))
        casos = ((0, 0), (0, 1), (0, 4), (1, 1), (2, 0), (2, 2),
                 (2, 8), (4, 0), (4, 1), (4, 4), (4, 8))
        self.assertFalse(estudio['mascaras']['viable'][0].any())
        for i, j in casos:
            with self.subTest(fila=i, columna=j):
                rp, T3 = estudio['rp'][j], estudio['T3'][i]
                ref = referencia_termodinamica(self.p, rp, T3)
                actual = estudio['filas'][i]['puntos'][j]
                for obtenido, esperado in zip(actual['temperaturas'], ref['temperaturas']):
                    self.assertAlmostEqual(obtenido, esperado, delta=1e-9)
                for clave in ('trabajo_compresor', 'trabajo_turbina',
                              'trabajo_neto', 'calor_aportado'):
                    self.assertAlmostEqual(actual[clave], ref[clave], delta=2e-10)
                self.assertEqual(actual['viable'], ref['admitido'])
                self.assertEqual(actual['motivos'], ref['motivos'])
                self.assertAlmostEqual(estudio['matrices']['trabajo_neto'][i, j],
                                       ref['trabajo_neto'], delta=2e-10)
                self.assertAlmostEqual(estudio['matrices']['calor_aportado'][i, j],
                                       ref['calor_aportado'], delta=2e-10)
                if ref['admitido']:
                    self.assertAlmostEqual(estudio['matrices']['rendimiento'][i, j],
                                           100 * ref['rendimiento'], delta=2e-10)
                else:
                    self.assertIsNone(actual['rendimiento'])
                    self.assertTrue(np.isnan(estudio['matrices']['rendimiento'][i, j]))
        self.assertLess(estudio['matrices']['trabajo_neto'][0, 1], 0)
        self.assertLess(estudio['matrices']['calor_aportado'][0, 8], 0)
        self.assertEqual(estudio['motivos'][0, 0][0], 'compresion')
        self.assertEqual(estudio['mascaras']['limite_numerico'].sum(), 0)

    def test_fronteras_cuadratica_y_dominios_independientes(self):
        perfiles = (self.p, {**self.p, 'T1': 300, 'eta_c': .6,
                             'eta_t': .7, 'perdida_presion_combustor': .2})
        for p in perfiles:
            e = mapa.analizar_mapa(p, rp_min=1, rp_max=50, T3_min=400,
                                  T3_max=1600, n_rp=5, n_T3=5,
                                  cortes=(900,))
            for i, T3 in enumerate(e['T3']):
                with self.subTest(eta_c=p['eta_c'], T3=T3):
                    ref = fronteras_cerradas(p, T3)
                    real = e['filas'][i]['muestra']['dominios']['noideal']
                    self.assertAlmostEqual(real['discriminante'],
                                           ref['discriminante'], delta=2e-12)
                    self.assertAlmostEqual(e['fronteras']['expansion'][i],
                                           ref['expansion'], delta=1e-12)
                    self.assertAlmostEqual(e['fronteras']['calor'][i],
                                           ref['calor'], delta=1e-9)
                    self.assertEqual(bool(real['intervalo']), bool(ref['intervalo']))
                    self.assertEqual(len(real['trabajo']), len(ref['trabajo']))
                    for actual_raiz, raiz_cerrada in zip(real['trabajo'], ref['trabajo']):
                        self.assertAlmostEqual(actual_raiz, raiz_cerrada,
                                               delta=3e-9 * max(1, raiz_cerrada))
                    for indice, frontera in enumerate(ref['intervalo']):
                        self.assertAlmostEqual(real['intervalo'][indice], frontera,
                                               delta=3e-9 * max(1, frontera))
                    if ref['intervalo']:
                        lo, hi = ref['intervalo']
                        medio = sqrt(lo * hi)
                        self.assertTrue(referencia_termodinamica(p, medio, T3)['estrictamente_motor'])
                        for rp in (lo * .95, hi * 1.05):
                            self.assertFalse(referencia_termodinamica(p, rp, T3)['estrictamente_motor'])
                    else:
                        self.assertFalse(e['mascaras']['viable'][i].any())
                        for s in 'AB':
                            self.assertEqual(e['trayectorias'][s]['registros'][i]['estado'],
                                             'sin_dominio')
                            self.assertTrue(np.isnan(e['trayectorias'][s]['rp'][i]))
            # La cuadrática tiene el mismo signo negativo que el trabajo positivo
            # cuando rp proporciona expansión efectiva y los factores son positivos.
            T3 = 1600
            f = fronteras_cerradas(p, T3)
            a = (p['gamma'] - 1) / p['gamma']
            for rp in (1.5, 3, 8, 25, 75):
                x = rp**a
                Qx = (x - 1) * (x - f['h']) + f['h'] * (f['b'] - 1)
                W = referencia_termodinamica(p, rp, T3)['trabajo_neto']
                self.assertEqual(Qx < 0, W > 0)

    def test_banda_numerica_y_mascara_motor(self):
        T3 = 1600
        lo, hi = fronteras_cerradas(self.p, T3)['intervalo']
        relaciones = (lo * (1 + 1e-6), lo * (1 + 1e-12),
                      hi * (1 - 1e-12), hi * (1 - 1e-6))
        fila = mapa.evaluar_fila(self.p, T3, relaciones)
        mascara = mapa.obtener_mascaras([fila])
        for j, rp in enumerate(relaciones):
            ref = referencia_termodinamica(self.p, rp, T3)
            punto = fila['puntos'][j]
            self.assertEqual(punto['viable'], ref['admitido'])
            self.assertEqual(punto['motivos'], ref['motivos'])
            self.assertEqual(mascara['viable'][0, j], ref['admitido'])
            self.assertFalse(mascara['limite_numerico'][0, j])
            if j in (1, 2):
                self.assertFalse(punto['viable'])
                self.assertIsNone(punto['rendimiento'])
                self.assertLessEqual(punto['margenes']['trabajo_neto'],
                                     punto['tolerancias']['trabajo_neto'])
            else:
                self.assertTrue(punto['viable'])
        preparados = mapa.preparar_resultados(dict(matrices={
            k: np.array([[p[k] if p[k] is not None else np.nan for p in fila['puntos']]])
            for k in ('trabajo_neto', 'calor_aportado', 'rendimiento')}, mascaras=mascara))
        for matriz in preparados['prestaciones'].values():
            np.testing.assert_array_equal(matriz.mask, ~mascara['viable'])

    def test_trayectoria_A_como_maximo_continuo_por_temperatura(self):
        for p in (self.p, {**self.p, 'T1': 300, 'eta_c': .9, 'eta_t': .94,
                           'perdida_presion_combustor': .03}):
            e = mapa.analizar_mapa(p, rp_min=1, rp_max=50,
                                  T3_min=700, T3_max=1700, n_rp=5,
                                  n_T3=5, cortes=(1200,))
            for i, T3 in enumerate(e['T3']):
                with self.subTest(T3=T3, eta_c=p['eta_c']):
                    frontera = fronteras_cerradas(p, T3)['intervalo']
                    registro = e['trayectorias']['A']['registros'][i]
                    if not frontera:
                        self.assertEqual(registro['estado'], 'sin_dominio')
                        self.assertTrue(np.isnan(e['trayectorias']['A']['rp'][i]))
                        continue
                    esperado = rp_max_trabajo(p, T3)
                    self.assertTrue(frontera[0] < esperado < frontera[1])
                    self.assertEqual(registro['estado'], 'disponible')
                    self.assertAlmostEqual(registro['rp'], esperado,
                                           delta=2e-9 * esperado)
                    ref = referencia_termodinamica(p, esperado, T3)
                    self.assertTrue(ref['admitido'])
                    self.assertAlmostEqual(registro['ciclo']['trabajo_neto'],
                                           ref['trabajo_neto'], delta=2e-10)
                    for factor in (.92, 1.08):
                        vecino = esperado * factor
                        self.assertLess(referencia_termodinamica(p, vecino, T3)['trabajo_neto'],
                                        ref['trabajo_neto'])

    @skipUnless(find_spec('scipy') is not None, 'SciPy es opcional para contrastar B')
    def test_trayectoria_B_con_scipy_independiente_en_varias_filas(self):
        from scipy.optimize import minimize_scalar
        e = mapa.analizar_mapa(self.p, rp_min=1, rp_max=30,
                              T3_min=900, T3_max=1800, n_rp=5, n_T3=4,
                              cortes=(1200,))
        for i, T3 in enumerate(e['T3']):
            with self.subTest(T3=T3):
                lo, hi = fronteras_cerradas(self.p, T3)['intervalo']
                epsilon = 1e-6
                objetivo = lambda y: -referencia_termodinamica(self.p, np.exp(y), T3)['rendimiento']
                res = minimize_scalar(objetivo, bounds=(log(lo) + epsilon,
                                            log(hi) - epsilon), method='bounded',
                                      options={'xatol': 1e-11})
                self.assertTrue(res.success)
                ref_rp = float(np.exp(res.x))
                ref = referencia_termodinamica(self.p, ref_rp, T3)
                self.assertTrue(ref['admitido'])
                registro = e['trayectorias']['B']['registros'][i]
                self.assertEqual(registro['estado'], 'disponible')
                self.assertTrue(lo < registro['rp'] < hi)
                self.assertAlmostEqual(registro['rp'], ref_rp, delta=3e-5 * ref_rp)
                self.assertAlmostEqual(registro['ciclo']['rendimiento'],
                                       ref['rendimiento'], delta=3e-9)
                self.assertGreaterEqual(registro['ciclo']['rendimiento'],
                                        e['trayectorias']['A']['registros'][i]['ciclo']['rendimiento'] - 1e-10)

    def test_supremo_ideal_y_optimos_no_recortados_a_ventana(self):
        ideal = {**self.p, 'eta_c': 1., 'eta_t': 1.,
                 'perdida_presion_combustor': 0.}
        e = mapa.analizar_mapa(ideal, rp_min=1, rp_max=4,
                              T3_min=900, T3_max=1600, n_rp=5, n_T3=3,
                              cortes=(900,))
        for i, T3 in enumerate(e['T3']):
            r = e['trayectorias']['B']['registros'][i]
            self.assertEqual(r['estado'], 'supremo_no_alcanzado')
            self.assertIsNone(r['rp'])
            self.assertAlmostEqual(r['supremo']['rendimiento'],
                                   1 - ideal['T1'] / T3, delta=1e-12)
            self.assertTrue(np.isnan(e['trayectorias']['B']['rp'][i]))
            a = e['trayectorias']['A']['registros'][i]
            self.assertAlmostEqual(a['rp'], rp_max_trabajo(ideal, T3), delta=1e-9)
            self.assertGreater(a['rp'], e['rp'][-1])
        noideal = mapa.analizar_mapa(self.p, rp_min=1, rp_max=3,
                                    T3_min=1400, T3_max=2000, n_rp=5,
                                    n_T3=3, cortes=(1700,))
        for s in 'AB':
            for rp in noideal['trayectorias'][s]['rp']:
                self.assertGreater(rp, noideal['rp'][-1])

    def test_mallas_anidadas_y_cotas_del_optimo_continuo(self):
        opciones = dict(rp_min=1.05, rp_max=100, T3_min=700, T3_max=1700,
                        escala='log', cortes=(1200,))
        gruesa = mapa.analizar_mapa(self.p, **opciones, n_rp=7, n_T3=3)
        fina = mapa.analizar_mapa(self.p, **opciones, n_rp=13, n_T3=5)
        np.testing.assert_allclose(fina['rp'][::2], gruesa['rp'], rtol=2e-15)
        np.testing.assert_allclose(fina['T3'][::2], gruesa['T3'], rtol=2e-15)
        for clave in ('trabajo_neto', 'calor_aportado', 'rendimiento'):
            np.testing.assert_allclose(fina['matrices'][clave][::2, ::2],
                                       gruesa['matrices'][clave], equal_nan=True,
                                       rtol=3e-14, atol=2e-11)
        np.testing.assert_array_equal(fina['mascaras']['viable'][::2, ::2],
                                      gruesa['mascaras']['viable'])
        for s in 'AB':
            np.testing.assert_allclose(fina['trayectorias'][s]['rp'][::2],
                                       gruesa['trayectorias'][s]['rp'], equal_nan=True,
                                       rtol=3e-14, atol=1e-10)
        for i in range(len(gruesa['T3'])):
            f = 2 * i
            for clave, s, conversion in (('trabajo_neto', 'A', 1),
                                         ('rendimiento', 'B', 100)):
                val_g = gruesa['matrices'][clave][i, gruesa['mascaras']['viable'][i]]
                val_f = fina['matrices'][clave][f, fina['mascaras']['viable'][f]]
                self.assertGreater(len(val_g), 0)
                self.assertGreaterEqual(np.max(val_f) + 1e-9, np.max(val_g))
                maximo_continuo = fina['trayectorias'][s]['registros'][f]['ciclo'][clave] * conversion
                self.assertLessEqual(np.max(val_f), maximo_continuo + 2e-9)

    def test_invariantes_en_matriz_cp_p1_y_primera_ley(self):
        opciones = dict(rp_min=2, rp_max=15, T3_min=1000,
                        T3_max=1600, n_rp=5, n_T3=3,
                        cortes=(1300,))
        base = mapa.analizar_mapa(self.p, **opciones)
        cp = mapa.analizar_mapa({**self.p, 'cp': 1.7 * self.p['cp']}, **opciones)
        p1 = mapa.analizar_mapa({**self.p, 'p1': 3.2 * self.p['p1']}, **opciones)
        for clave in ('trabajo_neto', 'calor_aportado'):
            np.testing.assert_allclose(cp['matrices'][clave], 1.7 * base['matrices'][clave],
                                       rtol=3e-14, atol=3e-10)
            np.testing.assert_allclose(p1['matrices'][clave], base['matrices'][clave],
                                       rtol=3e-14, atol=3e-10)
        for otro in (cp, p1):
            np.testing.assert_array_equal(otro['mascaras']['viable'], base['mascaras']['viable'])
            np.testing.assert_allclose(otro['matrices']['rendimiento'],
                                       base['matrices']['rendimiento'], equal_nan=True,
                                       rtol=3e-14, atol=3e-11)
        a = (self.p['gamma'] - 1) / self.p['gamma']
        k = self.p['cp'] / 1000
        for j, rp in enumerate(base['rp']):
            subida_esperada = k * self.p['eta_t'] * (
                1 - (rp * (1 - self.p['perdida_presion_combustor']))**(-a)) * 600
            self.assertAlmostEqual(base['matrices']['trabajo_neto'][-1, j]
                                   - base['matrices']['trabajo_neto'][0, j],
                                   subida_esperada, delta=3e-10)
        for fila in base['filas']:
            for punto in fila['puntos']:
                self.assertAlmostEqual(punto['trabajo_turbina'] - punto['trabajo_compresor'],
                                       punto['trabajo_neto'], delta=1e-11)
                ref = referencia_termodinamica(self.p,
                                                punto['presiones'][1] / self.p['p1'], fila['T3'])
                self.assertAlmostEqual(punto['calor_aportado'], ref['calor_aportado'],
                                       delta=2e-10)

    def test_datos_de_graficas_y_corte_sin_interpolacion(self):
        estudio = mapa.analizar_mapa(self.p, rp_min=1, rp_max=3,
                                    T3_min=1400, T3_max=2000, n_rp=5,
                                    n_T3=3, escala='log', cortes=(1700,))
        original = plt.Axes.pcolormesh
        original_plot = plt.Axes.plot
        superficies = []
        trayectorias_dibujadas = []
        def observar(ax, x, y, z, **kwargs):
            if np.shape(z) == (3, 5):
                superficies.append((ax, np.array(x), np.array(y),
                                     np.ma.array(z, copy=True), kwargs.copy()))
            return original(ax, x, y, z, **kwargs)
        def observar_curva(ax, *args, **kwargs):
            etiqueta = kwargs.get('label', '')
            if etiqueta.endswith('máximo físico (puede quedar fuera de vista)'):
                trayectorias_dibujadas.append((etiqueta, np.asarray(args[0]).copy(),
                                               np.asarray(args[1]).copy()))
            return original_plot(ax, *args, **kwargs)
        with patch.object(plt.Axes, 'pcolormesh', new=observar), \
                patch.object(plt.Axes, 'plot', new=observar_curva):
            imagenes = mapa.crear_graficas_mapa(estudio)
        self.assertEqual(len(imagenes), 4)
        self.assertEqual(len(superficies), 3)
        self.assertEqual(len(trayectorias_dibujadas), 6)
        for _, posiciones, temperaturas in trayectorias_dibujadas:
            self.assertTrue(np.isnan(posiciones).all())
            np.testing.assert_array_equal(temperaturas, estudio['T3'])
        for s in 'AB':
            self.assertTrue((estudio['trayectorias'][s]['rp'] > estudio['rp'][-1]).all())
        resultados = mapa.preparar_resultados(estudio)
        for i, (ax, x, y, z, kwargs) in enumerate(superficies):
            np.testing.assert_allclose(x, estudio['rp'])
            np.testing.assert_allclose(y, estudio['T3'])
            self.assertEqual(kwargs['shading'], 'nearest')
            self.assertEqual(ax.get_xscale(), 'log')
            self.assertEqual(ax.get_xlabel(), 'Relación de presiones rp [−]')
            self.assertEqual(ax.get_ylabel(), 'T3 [K]')
            if i < 2:
                nombre = ('trabajo_neto', 'rendimiento')[i]
                np.testing.assert_array_equal(np.ma.getmaskarray(z),
                                              ~estudio['mascaras']['viable'])
                np.testing.assert_allclose(z.compressed(),
                                           resultados['prestaciones'][nombre].compressed())
            else:
                np.testing.assert_array_equal(z, estudio['mascaras']['viable'].astype(float))
        corte = estudio['cortes'][0]
        self.assertEqual(corte['T3'], 1700)
        for j, rp in enumerate(estudio['rp']):
            ref = referencia_termodinamica(self.p, rp, 1700)
            self.assertAlmostEqual(corte['puntos'][j]['trabajo_neto'],
                                   ref['trabajo_neto'], delta=2e-10)
        self.assertFalse(plt.get_fignums())


if __name__ == '__main__':
    import unittest
    unittest.main()
