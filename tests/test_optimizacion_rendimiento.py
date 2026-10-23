"""Verificación unitaria de rendimiento, sin integrar HTML/Flask ni validar motores reales."""

import math
import unittest
from unittest.mock import patch
import numpy as np

import optimizacion_rendimiento as opt
from optimizacion import optimizar_trabajo_neto
from viabilidad import ErrorNumerico, calcular_dominios, evaluar_punto


class RendimientoTests(unittest.TestCase):
    def setUp(self):
        self.base = (288.15, 1600, 1.4, 1005, 100, .85, .9, .05)

    def test_ideal_monotonia_estricta_y_derivada(self):
        T1,T3,gamma,cp,p1 = self.base[:5]
        a = (gamma-1)/gamma
        limite = calcular_dominios(T1,T3,gamma,cp,p1)['ideal']['intervalo'][1]
        rp = np.geomspace(1.001,limite*.999,101)
        eta = [evaluar_punto(T1,T3,gamma,cp,float(r),p1)['rendimiento'] for r in rp]
        self.assertTrue(np.all(np.diff(eta)>0))
        for r in rp:
            self.assertGreater(a*r**(-a-1),0)
            self.assertAlmostEqual(evaluar_punto(T1,T3,gamma,cp,float(r),p1)['rendimiento'],1-r**(-a),places=11)

    def test_ideal_supremo_no_es_optimo_motor(self):
        r = opt.estudiar_rendimiento_ideal(*self.base[:5])
        self.assertEqual(r['estado'],'supremo_no_alcanzado')
        self.assertIsNone(r['analitico'])
        self.assertIsNone(r['numerico'])
        self.assertIsNone(r['candidato'])
        self.assertFalse(r['supremo']['alcanzado'])
        self.assertAlmostEqual(r['supremo']['rendimiento'],.81990625,places=13)
        frontera = r['supremo']['rp_frontera']
        p = evaluar_punto(288.15,1600,1.4,1005,frontera,100)
        self.assertFalse(p['viable'])
        self.assertIsNone(p['rendimiento'])
        self.assertAlmostEqual(p['calor_aportado'],0,places=9)
        valores = [evaluar_punto(288.15,1600,1.4,1005,frontera*(1-e),100)['rendimiento']
                   for e in (1e-2,1e-3,1e-4)]
        self.assertLess(valores[0],valores[1])
        self.assertLess(valores[1],valores[2])
        self.assertLess(valores[-1],r['supremo']['rendimiento'])

    def test_limite_completamente_reversible_no_busca_maximo(self):
        with patch.object(opt,'evaluar_punto',side_effect=AssertionError('no evaluar frontera')):
            a = opt.optimizar_rendimiento(*self.base[:5])
            n = opt.buscar_maximo_rendimiento_numerico(*self.base[:5])
        self.assertEqual(a['estado'],'supremo_no_alcanzado')
        self.assertEqual(n['supremo'],a['supremo'])
        self.assertIsNone(opt.calcular_candidato_rendimiento(288.15,1600,1.4))

    def test_cociente_derivado_coincide_con_balance(self):
        T1,T3,g,cp,p1,ec,et,d = self.base
        theta = T3/T1; a=(g-1)/g
        B=1+ec*(theta-1); h=ec*et*theta; H=h*(1-d)**(-a)
        for rp in (2,10,35,80,140):
            x=rp**a
            eta=(1+h-x-H/x)/(B-x)
            self.assertAlmostEqual(eta,evaluar_punto(T1,T3,g,cp,rp,p1,ec,et,d)['rendimiento'],places=12)

    def test_estacionariedad_y_segunda_derivada(self):
        T1,T3,g,cp,p1,ec,et,d=self.base
        a=(g-1)/g; B=1+ec*(T3/T1-1); h=ec*et*T3/T1; H=h*(1-d)**(-a)
        rp=opt.calcular_candidato_rendimiento(T1,T3,g,ec,et,d); x=rp**a
        A=1+h-B
        self.assertAlmostEqual(A*x*x-2*H*x+H*B,0,places=10)
        segunda=-2*H/(x**3*(B-x))
        self.assertLess(segunda,0)
        eta=[evaluar_punto(T1,T3,g,cp,rp*f,p1,ec,et,d)['rendimiento'] for f in (.999,1,1.001)]
        self.assertGreater(eta[1],eta[0]); self.assertGreater(eta[1],eta[2])
        self.assertLess(eta[0]-2*eta[1]+eta[2],0)

    def test_unicidad_cambio_de_signo_de_derivada(self):
        T1,T3,g,cp,p1,ec,et,d=self.base
        a=(g-1)/g; B=1+ec*(T3/T1-1); h=ec*et*T3/T1; H=h*(1-d)**(-a)
        lo,hi=calcular_dominios(*self.base)['noideal']['intervalo']
        xs=np.linspace(lo**a,hi**a,501)
        F=1+h-B+H*B/xs**2-2*H/xs
        self.assertTrue(np.all(np.diff(F)<0))
        self.assertGreater(F[0],0); self.assertLess(F[-1],0)
        self.assertEqual(np.count_nonzero(np.diff(np.sign(F))),1)

    def test_caso_referencia_y_estados(self):
        r=opt.optimizar_rendimiento(*self.base)
        self.assertEqual(r['estado'],'maximo_interior')
        self.assertAlmostEqual(r['candidato'],35.45232357076706,places=10)
        p=r['analitico']['ciclo']
        self.assertTrue(p['viable']); self.assertGreater(p['calor_aportado'],0)
        self.assertAlmostEqual(p['rendimiento'],.4389310716312654,places=12)
        self.assertAlmostEqual(p['trabajo_neto'],313.7389152634013,places=9)
        self.assertAlmostEqual(p['calor_aportado'],714.7794620631579,places=9)
        np.testing.assert_allclose(p['temperaturas'],[288.15,888.7766546635245,1600,687.1953201987628],rtol=1e-12)
        np.testing.assert_allclose(p['presiones'],[100,3545.2323570767057,3367.97073922287,100],rtol=1e-12)
        c=r['concordancia']
        self.assertLessEqual(c['diferencia_rp'],c['tolerancia_rp'])
        self.assertLessEqual(c['diferencia_rendimiento'],c['tolerancia_rendimiento'])
        self.assertLess(r['numerico']['evaluaciones'],400)

    def test_busqueda_numerica_independiente(self):
        with patch.object(opt,'calcular_candidato_rendimiento',side_effect=AssertionError('no usar raíz')):
            n=opt.buscar_maximo_rendimiento_numerico(*self.base)
        self.assertAlmostEqual(n['rp'],35.45232357076706,delta=1e-4)
        self.assertTrue(n['ciclo']['viable'])
        lo,hi=n['dominio']['intervalo']
        self.assertLess(lo,n['intervalo_busqueda'][0]); self.assertLess(n['intervalo_busqueda'][1],hi)

    def test_perdidas_individuales_y_familias(self):
        for T3 in (800,1600,5000):
            for ec,et,d in ((.85,1,0),(1,.9,0),(1,1,.05),(.85,.9,.05),(.5,.6,.3),(.8,.9,.7)):
                with self.subTest(T3=T3,ec=ec,et=et,delta=d):
                    r=opt.optimizar_rendimiento(288.15,T3,1.4,1005,100,ec,et,d)
                    if not r['dominio']['intervalo']:
                        self.assertEqual(r['estado'],'sin_dominio')
                        continue
                    self.assertEqual(r['estado'],'maximo_interior')
                    lo,hi=r['dominio']['intervalo']
                    for p in (r['analitico'],r['numerico']):
                        self.assertLess(lo,p['rp']); self.assertLess(p['rp'],hi)
                        self.assertTrue(p['ciclo']['viable'])
                        self.assertGreater(p['ciclo']['rendimiento'],0)
                        self.assertLess(p['ciclo']['rendimiento'],1)

    def test_coeficiente_cuadratico_cero_y_negativo(self):
        for et in (1-288.15/1600,.6):
            r=opt.optimizar_rendimiento(288.15,1600,1.4,1005,100,.85,et,0)
            self.assertEqual(r['estado'],'maximo_interior')
            self.assertLess(r['concordancia']['diferencia_rp'],r['concordancia']['tolerancia_rp'])

    def test_vacio_sin_candidato_ni_busqueda(self):
        for delta in (0,.8):
            with patch.object(opt,'buscar_maximo_rendimiento_numerico',side_effect=AssertionError('sin buscar')):
                with patch.object(opt,'calcular_candidato_rendimiento',side_effect=AssertionError('sin candidato')):
                    r=opt.optimizar_rendimiento(288.15,300,1.4,1005,100,.5,.5,delta)
            self.assertEqual(r['estado'],'sin_dominio')
            self.assertIsNone(r['analitico']); self.assertIsNone(r['supremo'])
            with patch.object(opt,'evaluar_punto',side_effect=AssertionError('sin evaluaciones')):
                n=opt.buscar_maximo_rendimiento_numerico(288.15,300,1.4,1005,100,.5,.5,delta)
            self.assertEqual(n['estado'],'sin_dominio'); self.assertIsNone(n['rp'])

    def test_parametros_proximos_al_ideal_no_se_redondean_a_reversibles(self):
        limite=opt.estudiar_rendimiento_ideal(*self.base[:5])['supremo']
        for ec,et,d in ((1-1e-8,1,0),(1,1-1e-8,0),(1,1,1e-12)):
            r=opt.optimizar_rendimiento(288.15,1600,1.4,1005,100,ec,et,d)
            self.assertEqual(r['estado'],'maximo_interior')
            self.assertLess(r['candidato'],limite['rp_frontera'])
            self.assertLess(r['analitico']['ciclo']['rendimiento'],limite['rendimiento'])
            self.assertTrue(r['analitico']['ciclo']['viable'])

    def test_dominio_estrecho_y_maximo_no_resoluble(self):
        T3=288.15/(.85*.9)*(1+1e-4)
        r=opt.optimizar_rendimiento(288.15,T3,1.4,1005,100,.85,.9,0)
        self.assertEqual(r['estado'],'maximo_interior')
        self.assertLess(r['dominio']['intervalo'][1]-r['dominio']['intervalo'][0],.001)
        for f in (opt.optimizar_rendimiento,opt.buscar_maximo_rendimiento_numerico):
            with self.assertRaises(ErrorNumerico):
                f(288.15,288.15/(.85*.9)*(1+1e-7),1.4,1005,100,.85,.9,0)

    def test_frontera_de_calor_no_se_divide(self):
        evaluar=opt.evaluar_punto
        def comprobar(*args,**kwargs):
            p=evaluar(*args,**kwargs)
            if not p['viable']:
                self.assertIsNone(p['rendimiento'])
            return p
        with patch.object(opt,'evaluar_punto',side_effect=comprobar):
            n=opt.buscar_maximo_rendimiento_numerico(288.15,1600,1.4,1005,100,1,1,1e-12)
        self.assertTrue(n['ciclo']['viable'])
        self.assertGreater(n['ciclo']['calor_aportado'],n['ciclo']['tolerancias']['calor_aportado'])

    def test_banda_numerica_no_crea_un_maximo_de_frontera(self):
        evaluar=opt.evaluar_punto
        def recortar(*args,**kwargs):
            p=evaluar(*args,**kwargs)
            if args[4]>20:
                return {**p,'viable':False,'rendimiento':None}
            return p
        with patch.object(opt,'evaluar_punto',side_effect=recortar):
            with self.assertRaises(ErrorNumerico):
                opt.buscar_maximo_rendimiento_numerico(*self.base)

    def test_optimos_fuera_de_intervalos_antiguos(self):
        bajo=opt.optimizar_rendimiento(300,324,1.4,1005,100,.99,.99,0)
        alto=opt.optimizar_rendimiento(288.15,5000,1.4,1005,100,.85,.9,.05)
        self.assertLess(bajo['candidato'],2)
        self.assertGreater(alto['candidato'],50)
        self.assertGreater(alto['numerico']['rp'],50)

    def test_invariancia_cp_p1_y_recalculo(self):
        a=opt.optimizar_rendimiento(*self.base)
        b=opt.optimizar_rendimiento(288.15,1600,1.4,2010,200,.85,.9,.05)
        opt.optimizar_rendimiento(288.15,5000,1.4,1005,100,.8,.9,.7)
        c=opt.optimizar_rendimiento(*self.base)
        self.assertEqual(a,c)
        self.assertEqual(a['candidato'],b['candidato'])
        self.assertAlmostEqual(a['analitico']['ciclo']['rendimiento'],b['analitico']['ciclo']['rendimiento'])
        self.assertAlmostEqual(2*a['analitico']['ciclo']['trabajo_neto'],b['analitico']['ciclo']['trabajo_neto'])
        np.testing.assert_allclose(np.array(a['analitico']['ciclo']['presiones'])*2,b['analitico']['ciclo']['presiones'])

    def test_maximo_rendimiento_distinto_del_maximo_trabajo(self):
        eta=opt.optimizar_rendimiento(*self.base)['analitico']
        w=optimizar_trabajo_neto(*self.base)['analitico']
        self.assertGreater(eta['rp'],w['rp'])
        self.assertGreater(eta['ciclo']['rendimiento'],w['ciclo']['rendimiento'])
        self.assertLess(eta['ciclo']['trabajo_neto'],w['ciclo']['trabajo_neto'])

    def test_errores_de_entrada_controles_y_representacion(self):
        for cambios in ({'muestras':3},{'muestras':True},{'muestras':5000},
                        {'tolerancia_log':0},{'tolerancia_log':math.nan},{'max_iteraciones':0}):
            with self.subTest(cambios=cambios),self.assertRaises(ValueError):
                opt.buscar_maximo_rendimiento_numerico(*self.base,**cambios)
        with self.assertRaises(ValueError):
            opt.optimizar_rendimiento(288.15,1600,1.4,1005,100,0,.9,.05)
        with self.assertRaises(ErrorNumerico):
            opt.buscar_maximo_rendimiento_numerico(*self.base,max_iteraciones=1)
        with self.assertRaises(ErrorNumerico):
            opt.calcular_candidato_rendimiento(1,1e300,1.00001,.85,.9,.05)

    def test_discrepancia_de_metodos_es_error_explicito(self):
        buscar=opt.buscar_maximo_rendimiento_numerico
        def alterar(*args,**kwargs):
            r=buscar(*args,**kwargs)
            return {**r,'rp':r['rp']*1.01}
        with patch.object(opt,'buscar_maximo_rendimiento_numerico',side_effect=alterar):
            with self.assertRaises(ErrorNumerico):
                opt.optimizar_rendimiento(*self.base)


if __name__ == '__main__':
    unittest.main()
