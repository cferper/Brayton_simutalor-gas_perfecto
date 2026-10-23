"""Máximos motores, adaptación por ejecución e integración sin validación externa."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import main
import optimizacion as opt
import reporting
import web_app
from viabilidad import ErrorNumerico, calcular_dominios, construir_barrido, evaluar_punto


class OptimizacionTests(unittest.TestCase):
    def setUp(self):
        self.base = (288.15, 1600, 1.4, 1005, 100, .85, .9, .05)

    def test_formula_estacionaria_independiente(self):
        T1, T3, gamma, _, _, ec, et, delta = self.base
        a = (gamma - 1) / gamma
        esperado = (ec * et * T3 / (T1 * (1-delta)**a))**(1/(2*a))
        self.assertAlmostEqual(opt.calcular_candidato_analitico(T1,T3,gamma,ec,et,delta), esperado, places=11)

    def test_segunda_derivada_negativa_y_maximo(self):
        T1,T3,gamma,cp,p1,ec,et,delta = self.base
        a=(gamma-1)/gamma
        rp=opt.calcular_candidato_analitico(T1,T3,gamma,ec,et,delta)
        x=rp**a
        segunda=-2*(cp/1000)*et*T3*(1-delta)**(-a)/x**3
        self.assertLess(segunda,0)
        valores=[evaluar_punto(T1,T3,gamma,cp,rp*f,p1,ec,et,delta)['trabajo_neto']
                 for f in (.999,1,1.001)]
        self.assertGreater(valores[1],valores[0])
        self.assertGreater(valores[1],valores[2])
        self.assertLess(valores[0]-2*valores[1]+valores[2],0)

    def test_referencia_analitica_numerica_y_estados(self):
        r=opt.optimizar_trabajo_neto(*self.base)
        self.assertEqual(r['estado'],'disponible')
        self.assertAlmostEqual(r['analitico']['rp'],12.89505166962397,places=10)
        self.assertAlmostEqual(r['analitico']['ciclo']['trabajo_neto'],373.21082748271016,places=9)
        self.assertAlmostEqual(r['analitico']['ciclo']['rendimiento'],.3921261442203449,places=11)
        np.testing.assert_allclose(r['analitico']['ciclo']['temperaturas'],
                                   [288.15,652.9729714016366,1600,863.8229714016369],rtol=1e-12)
        np.testing.assert_allclose(r['analitico']['ciclo']['presiones'],
                                   [100,1289.5051669623963,1225.0299086142763,100],rtol=1e-12)
        self.assertLessEqual(r['concordancia']['diferencia_rp'],r['concordancia']['tolerancia_rp'])
        self.assertLessEqual(r['concordancia']['diferencia_trabajo'],r['concordancia']['tolerancia_trabajo'])
        self.assertLess(r['numerico']['evaluaciones'],400)

    def test_busqueda_numerica_no_utiliza_candidato_analitico(self):
        with patch.object(opt,'calcular_candidato_analitico',side_effect=AssertionError('dependencia analítica')):
            n=opt.buscar_maximo_numerico(*self.base)
        self.assertAlmostEqual(n['rp'],12.8950516696,delta=3e-5)
        self.assertTrue(n['ciclo']['viable'])

    def test_candidato_siempre_interior_si_hay_motor(self):
        for T3 in (400,800,1600,5000,20000):
            for ec,et,delta in ((1,1,0),(.85,.9,.05),(.5,.6,.3),(.8,.9,.7)):
                with self.subTest(T3=T3,ec=ec,et=et,delta=delta):
                    r=opt.optimizar_trabajo_neto(288.15,T3,1.4,1005,100,ec,et,delta)
                    intervalo=r['dominio']['intervalo']
                    if intervalo:
                        self.assertLess(intervalo[0],r['analitico']['rp'])
                        self.assertLess(r['analitico']['rp'],intervalo[1])
                        self.assertLess(intervalo[0],r['numerico']['rp'])
                        self.assertLess(r['numerico']['rp'],intervalo[1])
                        self.assertTrue(r['analitico']['ciclo']['viable'])
                    else:
                        self.assertIsNone(r['analitico'])
                        self.assertIsNone(r['numerico'])

    def test_limite_reversible_recupera_optimo_ideal(self):
        r=opt.optimizar_trabajo_neto(288.15,1600,1.4,1005,100)
        self.assertAlmostEqual(r['analitico']['rp'],main.calcular_relacion_optima(288.15,1600,1.4),places=11)
        self.assertAlmostEqual(r['analitico']['ciclo']['trabajo_neto'],532.8022301185676,places=9)

    def test_dominio_vacio_no_llama_a_la_busqueda(self):
        with patch.object(opt,'buscar_maximo_numerico',side_effect=AssertionError('no debe buscar')):
            r=opt.optimizar_trabajo_neto(288.15,300,1.4,1005,100,.5,.5,0)
        self.assertEqual(r['estado'],'sin_dominio')
        self.assertIsNotNone(r['candidato'])
        self.assertIsNone(r['analitico'])
        self.assertIsNone(r['numerico'])
        self.assertIsNone(r['concordancia'])
        self.assertIsNone(opt.buscar_maximo_numerico(288.15,300,1.4,1005,100,.5,.5,0))

    def test_dominio_estrecho_resoluble_y_banda_no_resoluble(self):
        for incremento,resoluble in ((1e-4,True),(1e-7,False)):
            T3=288.15/(.85*.9)*(1+incremento)
            if resoluble:
                r=opt.optimizar_trabajo_neto(288.15,T3,1.4,1005,100,.85,.9,0)
                self.assertTrue(r['analitico']['ciclo']['viable'])
                self.assertLess(r['dominio']['intervalo'][1]-r['dominio']['intervalo'][0],.001)
            else:
                with self.assertRaises(ErrorNumerico):
                    opt.optimizar_trabajo_neto(288.15,T3,1.4,1005,100,.85,.9,0)

    def test_controles_invalidos_y_limites_numericos(self):
        for cambios in ({'muestras':3},{'muestras':5000},{'tolerancia_log':0},{'max_iteraciones':0}):
            with self.subTest(cambios=cambios),self.assertRaises(ValueError):
                opt.buscar_maximo_numerico(*self.base,**cambios)
        with self.assertRaises(ValueError):
            opt.calcular_candidato_analitico(288.15,1600,1.4,0,.9,.05)
        with self.assertRaises(ErrorNumerico):
            opt.calcular_candidato_analitico(1,1e300,1.00001)
        with self.assertRaises(ErrorNumerico):
            opt.buscar_maximo_numerico(*self.base,max_iteraciones=1)

    def test_maximos_fuera_de_los_antiguos_intervalos(self):
        bajo=opt.optimizar_trabajo_neto(300,324,1.4,1005,100,.99,.99,0)
        self.assertLess(bajo['analitico']['rp'],2)
        for T3 in (5000,20000):
            for ec,et,delta in ((1,1,0),(.85,.9,.05)):
                r=opt.optimizar_trabajo_neto(288.15,T3,1.4,1005,100,ec,et,delta)
                self.assertGreater(r['analitico']['rp'],50)
                self.assertGreater(r['numerico']['intervalo_busqueda'][1],r['analitico']['rp'])

    def test_cp_y_p1_no_alteran_rp_pero_si_energias_y_presiones(self):
        a=opt.optimizar_trabajo_neto(*self.base)
        b=opt.optimizar_trabajo_neto(288.15,1600,1.4,2010,200,.85,.9,.05)
        self.assertEqual(a['analitico']['rp'],b['analitico']['rp'])
        self.assertAlmostEqual(b['analitico']['ciclo']['trabajo_neto'],2*a['analitico']['ciclo']['trabajo_neto'])
        np.testing.assert_allclose(b['analitico']['ciclo']['presiones'],np.array(a['analitico']['ciclo']['presiones'])*2)

    def test_barrido_completo_sin_recorte_y_con_maximos(self):
        T3=20000
        d=calcular_dominios(288.15,T3,1.4,1005,100,.85,.9,.05)
        ri=opt.calcular_candidato_analitico(288.15,T3,1.4)
        rr=opt.calcular_candidato_analitico(288.15,T3,1.4,.85,.9,.05)
        b=construir_barrido(288.15,T3,1.4,1005,100,.85,.9,.05,dominios=d,puntos_interes=[ri,rr])
        self.assertGreater(b['intervalo_visual'][1],d['ideal']['intervalo'][1])
        self.assertGreater(b['intervalo_visual'][1],10000)
        self.assertLess(len(b['relaciones']),1300)
        for rp in (ri,rr,d['ideal']['intervalo'][1],*d['noideal']['intervalo']):
            self.assertIn(rp,b['relaciones'])
        for nombre in ('ideal','noideal'):
            self.assertTrue(np.isnan(b[nombre]['trabajo_neto'][~b[nombre]['viable']]).all())

    def test_panel_de_detalle_y_marcadores_dentro_de_la_vista(self):
        parametros=(288.15,2000,1.4,1005,100,.5,.6,.3)
        T1,T3,gamma,cp,p1,ec,et,delta=parametros
        d=calcular_dominios(*parametros)
        estudios={'ideal':opt.optimizar_trabajo_neto(T1,T3,gamma,cp,p1,dominio=d['ideal']),
                  'noideal':opt.optimizar_trabajo_neto(*parametros,dominio=d['noideal'])}
        b=construir_barrido(*parametros,dominios=d,puntos_interes=[r['candidato'] for r in estudios.values()])
        figuras=[]
        guardar=main.plt.Figure.savefig
        def capturar(figura,*args,**kwargs):
            figuras.append(figura)
            return guardar(figura,*args,**kwargs)
        imagenes={}
        try:
            with patch.object(main.plt.Figure,'savefig',new=capturar):
                main.guardar_comparaciones_ciclos(*parametros,imagenes,b,estudios)
            for figura in figuras:
                self.assertEqual(len(figura.axes),2)
            ejes=figuras[1].axes[0]
            self.assertGreaterEqual(ejes.get_xlim()[1],d['ideal']['intervalo'][1])
            for r in estudios.values():
                self.assertTrue(ejes.get_xlim()[0]<=r['candidato']<=ejes.get_xlim()[1])
            self.assertEqual(len(ejes.collections),2)
            self.assertIn('Máximo noideal',' '.join(ejes.get_legend_handles_labels()[1]))
        finally:
            for buffer in imagenes.values():
                buffer.close()

    def test_html_sin_optimo_no_muestra_ceros_ficticios(self):
        estudios={'ideal':opt.optimizar_trabajo_neto(288.15,300,1.4,1005,100),
                  'noideal':opt.optimizar_trabajo_neto(288.15,300,1.4,1005,100,.5,.5,0)}
        referencia={'ideal':estudios['ideal']['analitico']['ciclo']}
        html=reporting.seccion_optimizacion_html({'relacion_presiones':1.01},referencia,estudios,None)
        self.assertIn('No disponible',html)
        self.assertIn('Dominio motor vacío',html)

    def test_flask_recalcula_los_nueve_parametros_y_descarga(self):
        casos=[{}, {'T1':300,'T3':324,'relacion_presiones':1.1,'eta_c':.99,'eta_t':.99,
                    'perdida_presion_combustor':0},
               {'T1':300,'T3':5000,'p1':120,'cp':1200,'gamma':1.38,'eta_c':.7,
                'eta_t':.75,'perdida_presion_combustor':.4,'relacion_presiones':40},{}]
        estudios=[]
        with tempfile.TemporaryDirectory() as carpeta,patch.dict(web_app.app.config,OUTPUTS_DIR=Path(carpeta)):
            client=web_app.app.test_client()
            for cambios in casos:
                parametros={**main.PARAMETROS_PREDETERMINADOS,**cambios}
                datos={k:str(v*100 if k=='perdida_presion_combustor' else v) for k,v in parametros.items()}
                with patch.object(main,'crear_informe_html',wraps=reporting.crear_informe_html) as creador:
                    with redirect_stdout(StringIO()):
                        respuesta=client.post('/',data=datos)
                self.assertEqual(respuesta.status_code,303)
                estudio=creador.call_args.args[-1]
                barrido=creador.call_args.args[-2]
                estudios.append(estudio)
                texto=client.get(respuesta.location+'?descargar=1').get_data(as_text=True)
                self.assertIn('Optimización del trabajo específico neto',texto)
                self.assertIn(f"{estudio['noideal']['analitico']['rp']:.10f}",texto)
                self.assertIn(f"{estudio['noideal']['analitico']['ciclo']['trabajo_neto']:.6f}",texto)
                self.assertIn('Intervalo de optimización numérica',texto)
                self.assertEqual(texto.count("src='data:image/png;base64,"),7)
                self.assertIn(estudio['noideal']['candidato'],barrido['relaciones'])
                self.assertIn(parametros['relacion_presiones'],barrido['relaciones'])
            self.assertEqual(len(list(Path(carpeta).glob('*.html'))),4)
        self.assertEqual(estudios[0],estudios[-1])
        self.assertNotEqual(estudios[0]['noideal']['dominio'],estudios[1]['noideal']['dominio'])
        self.assertGreater(estudios[2]['noideal']['candidato'],50)



if __name__=='__main__':
    unittest.main()
