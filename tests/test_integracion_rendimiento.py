"""Integración de Fase 3: datos de cada ejecución, figuras y HTML/Flask local."""
from contextlib import redirect_stdout
from io import BytesIO, StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import matplotlib.image as mpimg

import main
import reporting
import web_app
from optimizacion import optimizar_trabajo_neto
from optimizacion_rendimiento import optimizar_rendimiento, estudiar_rendimiento_ideal, comparar_criterios
from viabilidad import construir_barrido, calcular_dominios
from test_reporting import InformeParser


class IntegracionRendimientoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=(288.15,1600,1.4,1005,100,.85,.9,.05)
        with tempfile.TemporaryDirectory() as carpeta:
            with patch.object(main,'crear_informe_html',wraps=reporting.crear_informe_html) as crear:
                with redirect_stdout(StringIO()): ruta=main.main(carpeta)
            cls.html=ruta.read_text(encoding='utf-8')
            cls.args=crear.call_args.args
            cls.kw=crear.call_args.kwargs

    def test_comparacion_y_html_con_resultados_fisicos(self):
        c=self.kw['comparacion_criterios']
        a,b=c['punto_a'],c['punto_b']
        self.assertEqual(a,optimizar_trabajo_neto(*self.base)['analitico'])
        self.assertEqual(b,optimizar_rendimiento(*self.base)['analitico'])
        self.assertAlmostEqual(c['diferencia_rp'],b['rp']-a['rp'])
        self.assertAlmostEqual(c['ganancia_rendimiento_pp'],100*(b['ciclo']['rendimiento']-a['ciclo']['rendimiento']))
        self.assertAlmostEqual(c['reduccion_trabajo_porcentaje'],100*(1-b['ciclo']['trabajo_neto']/a['ciclo']['trabajo_neto']))
        self.assertAlmostEqual(c['diferencia_calor'],b['ciclo']['calor_aportado']-a['ciclo']['calor_aportado'])
        for numero in (f"{b['rp']:.10f}",f"{b['ciclo']['rendimiento']*100:.6f}",
                       f"{c['ganancia_rendimiento_pp']:.6f}",f"{c['reduccion_trabajo_porcentaje']:.6f}",
                       f"{c['diferencia_calor']:.6f}"):
            self.assertIn(numero,self.html)
        self.assertIn('Optimización del rendimiento térmico',self.html)
        self.assertIn('Supremo no alcanzado',self.html)
        self.assertIn('puntos porcentuales',self.html)
        self.assertIn('No toda la curva es frontera de Pareto',self.html)

    def test_siete_imagenes_autocontenidas_y_malla_con_punto_b(self):
        parser=InformeParser();parser.feed(self.html)
        self.assertEqual(len(parser.imagenes),7);self.assertEqual(parser.externos,[])
        self.assertCountEqual(parser.imagenes,self.args[7].values())
        for png in parser.imagenes:
            self.assertEqual(mpimg.imread(BytesIO(png),format='png').shape[:2],(900,1350))
        b=self.kw['comparacion_criterios']['punto_b']
        barrido=self.args[10]
        self.assertIn(b['rp'],barrido['relaciones'])
        self.assertLessEqual(b['rp'],barrido['intervalo_visual'][1])

    def test_marcadores_rp_y_cortes_nan(self):
        figuras=[]
        def capturar(figura,*args,**kwargs): figuras.append(figura)
        imagenes={}
        with patch.object(main.plt.Figure,'savefig',new=capturar):
            main.guardar_comparaciones_ciclos(*self.base,imagenes,self.args[10],self.args[11],self.kw['estudio_rendimiento'])
        try:
            for figura,clave,factor in zip(figuras,('rendimiento','trabajo_neto'),(100,1)):
                eje=figura.axes[0]
                self.assertEqual(len(eje.collections),3)
                for coleccion,punto in zip((eje.collections[1],eje.collections[2]),
                                           (self.kw['comparacion_criterios']['punto_a'],self.kw['comparacion_criterios']['punto_b'])):
                    np.testing.assert_allclose(coleccion.get_offsets(),[[punto['rp'],punto['ciclo'][clave]*factor]])
                for linea,nombre in zip(eje.lines[:2],('ideal','noideal')):
                    self.assertTrue(np.isnan(linea.get_ydata()[~self.args[10][nombre]['viable']]).all())
        finally:
            for buf in imagenes.values():buf.close()
            main.plt.close('all')

    def test_compromiso_es_parametrico_admisible_con_ambos_puntos(self):
        figuras=[]
        def capturar(figura,*args,**kwargs):figuras.append(figura)
        with BytesIO() as buf,patch.object(main.plt.Figure,'savefig',new=capturar):
            main.guardar_grafica_compromiso(self.args[10],self.kw['comparacion_criterios'],buf)
        eje=figuras[0].axes[0];linea=eje.lines[0];real=self.args[10]['noideal']
        np.testing.assert_allclose(linea.get_xdata(),real['trabajo_neto'],equal_nan=True)
        np.testing.assert_allclose(linea.get_ydata(),real['rendimiento']*100,equal_nan=True)
        self.assertTrue(np.isnan(linea.get_xdata()[~real['viable']]).all())
        for col,clave in zip(eje.collections,('punto_a','punto_b')):
            p=self.kw['comparacion_criterios'][clave]['ciclo']
            np.testing.assert_allclose(col.get_offsets(),[[p['trabajo_neto'],p['rendimiento']*100]])
        main.plt.close('all')

    def test_reversible_sin_punto_b_ni_diferencias_ficticias(self):
        w=optimizar_trabajo_neto(*self.base[:5]);r=optimizar_rendimiento(*self.base[:5])
        c=comparar_criterios(w,r)
        self.assertIsNone(c['punto_b']);self.assertIsNone(c['diferencia_rp'])
        html=reporting.seccion_rendimiento_html({'ideal':r,'noideal':r},c)
        self.assertIn('No existe máximo interior ni punto B',html)
        self.assertIn('No disponible',html)
        self.assertNotIn('Reducción relativa de trabajo respecto a A',html)
        figuras=[]
        def capturar(figura,*args,**kwargs):figuras.append(figura)
        b=construir_barrido(*self.base[:5])
        with BytesIO() as buf,patch.object(main.plt.Figure,'savefig',new=capturar):
            main.guardar_grafica_compromiso(b,c,buf)
        self.assertEqual(len(figuras[0].axes[0].collections),1)
        main.plt.close('all')

    def test_vacio_no_se_inventa_informe_ni_maximo(self):
        p=(288.15,300,1.4,1005,100,.5,.5,0)
        w=optimizar_trabajo_neto(*p);r=optimizar_rendimiento(*p)
        c=comparar_criterios(w,r)
        self.assertIsNone(c['punto_a']);self.assertIsNone(c['punto_b'])
        html=reporting.seccion_rendimiento_html({'ideal':estudiar_rendimiento_ideal(*p[:5]),'noideal':r},c)
        self.assertIn('Dominio motor vacío',html)
        with tempfile.TemporaryDirectory() as carpeta:
            with self.assertRaises(main.ErrorModelo):
                main.main(carpeta,{'T3':300,'eta_c':.5,'eta_t':.5,'perdida_presion_combustor':0})
            self.assertEqual(list(Path(carpeta).iterdir()),[])

    def test_flask_recalcula_cambios_reversibilidad_descarga_y_retencion(self):
        casos=[{}, {'T1':300,'T3':324,'relacion_presiones':1.1,'eta_c':.99,'eta_t':.99,'perdida_presion_combustor':0},
               {'T3':5000,'cp':1200,'gamma':1.38,'p1':120,'eta_c':.7,'eta_t':.75,'perdida_presion_combustor':.4,'relacion_presiones':40},
               {'eta_c':1,'eta_t':1,'perdida_presion_combustor':0},{}]
        estudios=[];rutas=[]
        with tempfile.TemporaryDirectory() as carpeta,patch.dict(web_app.app.config,OUTPUTS_DIR=Path(carpeta)):
            (Path(carpeta)/'notas.html').write_text('archivo ajeno',encoding='utf-8')
            client=web_app.app.test_client()
            for cambios in casos:
                p={**main.PARAMETROS_PREDETERMINADOS,**cambios}
                datos={k:str(v*100 if k=='perdida_presion_combustor' else v) for k,v in p.items()}
                with patch.object(main,'crear_informe_html',wraps=reporting.crear_informe_html) as crear:
                    with redirect_stdout(StringIO()):respuesta=client.post('/',data=datos)
                self.assertEqual(respuesta.status_code,303)
                rutas.append(respuesta.location)
                estudio=crear.call_args.kwargs['estudio_rendimiento']['noideal'];estudios.append(estudio)
                descarga=client.get(respuesta.location+'?descargar=1')
                self.assertEqual(descarga.status_code,200)
                self.assertIn('attachment',descarga.headers['Content-Disposition'])
                html=descarga.get_data(as_text=True)
                parser=InformeParser();parser.feed(html)
                self.assertEqual(parser.externos,[]);self.assertEqual(len(parser.imagenes),7)
                self.assertIn('Commit Git:',html)
                if estudio['estado']=='maximo_interior':
                    self.assertIn(f"{estudio['analitico']['rp']:.10f}",html)
                    self.assertIn(estudio['analitico']['rp'],crear.call_args.args[10]['relaciones'])
            self.assertEqual(len(list(Path(carpeta).glob('brayton_*.html'))),4)
            self.assertEqual(client.get(rutas[0]).status_code,404)
            self.assertEqual((Path(carpeta)/'notas.html').read_text(encoding='utf-8'),'archivo ajeno')
        self.assertEqual(estudios[0],estudios[-1])
        self.assertLess(estudios[1]['candidato'],2);self.assertGreater(estudios[2]['candidato'],50)
        self.assertEqual(estudios[3]['estado'],'supremo_no_alcanzado')

    def test_compatibilidad_presentador_de_seis_imagenes(self):
        args=list(self.args)
        args[7]={k:v for k,v in args[7].items() if k!='compromiso_trabajo_rendimiento.png'}
        html=reporting.crear_informe_html(*args)
        parser=InformeParser();parser.feed(html)
        self.assertEqual(len(parser.imagenes),6)
        self.assertNotIn('Optimización del rendimiento térmico',html)


if __name__=='__main__':unittest.main()
