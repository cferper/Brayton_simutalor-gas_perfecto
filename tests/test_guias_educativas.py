import unittest
from guias_educativas import construir_guias, construir_pestanas, GUIAS, BLOQUES

class TestGuias(unittest.TestCase):
    def test_todas_las_secciones(self):
        self.assertEqual(set(construir_guias()), set(GUIAS))
        self.assertEqual(len(GUIAS), 8)

    def test_cada_guia_contiene_fundamentos_y_ecuaciones(self):
        for nombre, html in construir_guias().items():
            with self.subTest(nombre=nombre):
                for texto in ('Qué vas a estudiar y calcular', 'Fundamentos físicos', 'Ecuaciones del modelo', 'Cómo lo calcula el programa', 'Cómo interpretar los resultados'):
                    self.assertIn(texto, html)
                self.assertIn('<details', html)
                self.assertIn('<code>', html)

    def test_guia_no_modifica_calculos(self):
        self.assertIn('OFAT', construir_guias()['sensibilidad'])
        self.assertIn('exergía', construir_guias()['segunda_ley'])


class TestPestanasEducativas(unittest.TestCase):
    def test_seis_vistas_tienen_resumen_y_fundamentos(self):
        from pathlib import Path
        import re
        t = Path(__file__).resolve().parents[1].joinpath('templates/index.html').read_text(encoding='utf-8')
        for clave in ('simulacion', 'resultados', 'optimizacion', 'sensibilidad', 'mapa', 'segunda_ley'):
            self.assertIn(f'data-edu-tabs="{clave}"', t)
            self.assertIn(f'pestanas["{clave}"]["resumen"]', t)
            self.assertIn(f'pestanas["{clave}"]["teoria"]', t)
        self.assertNotIn('<div class="card educational-intro">', t)
        self.assertEqual(len(construir_pestanas()), 8)

    def test_contenido_cientifico_separado(self):
        for clave in ('simulacion','resultados','optimizacion','sensibilidad','mapa','segunda_ley'):
            vistas = construir_pestanas()[clave]
            self.assertIn('Qué vamos a estudiar', vistas['resumen'])
            self.assertIn('Ecuaciones y magnitudes', vistas['teoria'])
            self.assertIn('Procedimiento de cálculo', vistas['teoria'])

    def test_ocho_bloques_extensos_sin_teoria_en_resumen(self):
        vistas = construir_pestanas()
        self.assertEqual(set(BLOQUES), {'simulacion', 'resultados', 'optimizacion',
                                     'sensibilidad', 'mapa', 'segunda_ley'})
        for clave, bloques in BLOQUES.items():
            with self.subTest(clave=clave):
                self.assertEqual(len(bloques), 8)
                palabras = sum(len(p.split()) for _, parrafos in bloques for p in parrafos)
                self.assertGreaterEqual(palabras, 700)
                self.assertLessEqual(palabras, 850)
                self.assertEqual(vistas[clave]['teoria'].count('<section '), 8)
                self.assertNotIn('edu-deep-block', vistas[clave]['resumen'])

    def test_bloques_escapan_titulos_y_parrafos(self):
        from unittest.mock import patch
        with patch.dict(BLOQUES, simulacion=(('<script>título</script>', ('a < b & c',)),)):
            teoria = construir_pestanas()['simulacion']['teoria']
        self.assertNotIn('<script>', teoria)
        self.assertIn('&lt;script&gt;', teoria)
        self.assertIn('a &lt; b &amp; c', teoria)

    def test_http_coloca_teoria_en_su_panel(self):
        import web_app
        from html import escape
        respuesta = web_app.app.test_client().get('/')
        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.get_data(as_text=True)
        for clave, bloques in BLOQUES.items():
            inicio = html.index(f'id="{clave}-vista-fundamentos"')
            fin = html.index('</div></div></section>', inicio)
            panel = html[inicio:fin]
            self.assertEqual(panel.count('class="edu-deep-block"'), 8)
            for titulo, parrafos in bloques:
                self.assertIn(escape(titulo), panel)
                for parrafo in parrafos:
                    self.assertIn(escape(parrafo), panel)

    def test_no_ocultar_campos_fuera_de_js(self):
        from pathlib import Path
        base = Path(__file__).resolve().parents[1]
        js = (base/'static/dashboard.js').read_text(encoding='utf-8')
        css = (base/'static/style.css').read_text(encoding='utf-8')
        self.assertIn("select(0)", js)
        self.assertIn('.js .edu-tab-pane[hidden]', css)
