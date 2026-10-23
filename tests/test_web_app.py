"""Pruebas HTTP locales con Flask test_client, sin abrir sockets."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import main as simulador
import web_app
from test_reporting import InformeParser


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.carpeta = Path(self.temporal.name) / "outputs"
        self.configuracion = patch.dict(web_app.app.config, {
            "OUTPUTS_DIR": self.carpeta, "TESTING": False, "PROPAGATE_EXCEPTIONS": False,
        })
        self.configuracion.start()
        self.addCleanup(self.configuracion.stop)
        self.client = web_app.app.test_client()
        self.datos = {nombre: str(valor) for nombre, valor in web_app.valores_formulario().items()}

    def test_formulario_predeterminados_y_restablecer(self):
        respuesta = self.client.get("/")
        texto = respuesta.get_data(as_text=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("Configuración del ciclo", texto)
        self.assertEqual(texto.count('type="number"'), 19)  # Nueve físicos + tres OFAT + seis mapa + T0.
        self.assertIn('value="5.0"', texto)
        self.assertIn("Ejecutar simulación", texto)
        self.assertIn("Restablecer valores", texto)
        with self.client.get("/static/style.css") as estilo:
            self.assertEqual(estilo.status_code, 200)
        self.assertFalse(self.carpeta.exists())

    def test_validacion_de_todos_los_campos_sin_informes(self):
        casos = [(nombre, "", "obligatorio") for nombre in self.datos]
        casos += [(nombre, "texto", "número válido") for nombre in self.datos]
        casos += [(nombre, no_finito, "finito") for nombre in self.datos for no_finito in ("nan", "inf", "-inf", "1e999")]
        casos += [(nombre, valor, "mayor que 0") for nombre in ("T1", "T3", "p1", "cp") for valor in ("0", "-1")]
        casos += [(nombre, valor, "mayor que 1") for nombre in ("gamma", "relacion_presiones") for valor in ("1", "0.5")]
        casos += [(nombre, valor, "eficiencia") for nombre in ("eta_c", "eta_t") for valor in ("0", "-1", "1.01")]
        casos += [("perdida_presion_combustor", valor, "pérdida") for valor in ("-1", "100", "101")]
        for nombre, valor, mensaje in casos:
            with self.subTest(nombre=nombre, valor=valor):
                datos = {**self.datos, nombre: valor}
                with patch.object(web_app, "main") as ejecutar:
                    respuesta = self.client.post("/", data=datos)
                self.assertEqual(respuesta.status_code, 400)
                self.assertIn(mensaje, respuesta.get_data(as_text=True))
                ejecutar.assert_not_called()
        datos = self.datos.copy()
        del datos["T1"]
        self.assertEqual(self.client.post("/", data=datos).status_code, 400)
        self.assertFalse(self.carpeta.exists())

    def test_conversion_porcentaje_y_limites_admitidos(self):
        datos = {**self.datos, "eta_c": "1", "eta_t": "1", "perdida_presion_combustor": "0"}
        parametros, errores = web_app.leer_parametros(datos)
        self.assertEqual(errores, {})
        self.assertEqual(parametros["perdida_presion_combustor"], 0)
        parametros, errores = web_app.leer_parametros(self.datos)
        self.assertEqual(errores, {})
        self.assertEqual(parametros["perdida_presion_combustor"], .05)
        self.assertEqual(simulador.PARAMETROS_PREDETERMINADOS["perdida_presion_combustor"], .05)

    def test_referencia_y_otro_caso_con_seis_imagenes_actuales(self):
        imagenes_anteriores = None
        datos_modificados = {
            "T1": "300", "T3": "1700", "p1": "110", "cp": "1010", "gamma": "1.38",
            "relacion_presiones": "12", "eta_c": ".88", "eta_t": ".92", "perdida_presion_combustor": "3",
        }
        crear = simulador.crear_informe_html
        for datos in (self.datos, datos_modificados):
            with patch.object(simulador, "crear_informe_html", wraps=crear) as generador:
                with redirect_stdout(StringIO()):
                    respuesta = self.client.post("/", data=datos)
            self.assertEqual(respuesta.status_code, 303)
            vista = self.client.get(respuesta.location)
            self.assertEqual(vista.status_code, 200)
            texto = vista.get_data(as_text=True)
            self.assertIn("Volver al formulario", texto)
            argumentos = generador.call_args.args
            parametros, errores = web_app.leer_parametros(datos)
            self.assertEqual(errores, {})
            self.assertEqual(argumentos[0], parametros)
            ideal = simulador.calcular_ciclo_ideal(
                parametros["T1"], parametros["T3"], parametros["gamma"], parametros["cp"],
                parametros["relacion_presiones"], parametros["p1"],
            )
            real = simulador.calcular_ciclo_noideal(
                parametros["T1"], parametros["T3"], parametros["gamma"], parametros["cp"],
                parametros["relacion_presiones"], parametros["p1"], parametros["eta_c"],
                parametros["eta_t"], parametros["perdida_presion_combustor"],
            )
            for ciclo in (ideal, real):
                self.assertIn(f"{ciclo['trabajo_neto']:.6f}", texto)
                self.assertIn(f"{ciclo['rendimiento'] * 100:.6f}", texto)
            descarga = self.client.get(respuesta.location + "?descargar=1")
            self.assertIn("attachment;", descarga.headers["Content-Disposition"])
            contenido = descarga.get_data(as_text=True)
            self.assertNotIn("Volver al formulario", contenido)
            nombre = respuesta.location.rsplit("/", 1)[1]
            self.assertEqual(contenido, (self.carpeta / nombre).read_text(encoding="utf-8"))
            parser = InformeParser()
            parser.feed(contenido)
            self.assertEqual(len(parser.imagenes), 7)
            self.assertEqual(parser.externos, [])
            self.assertCountEqual(parser.imagenes, argumentos[7].values())
            if imagenes_anteriores is None:
                for numero in ("505.619018", "48.205253", "369.476301", "36.898732"):
                    self.assertIn(numero, contenido)
            else:
                self.assertTrue(all(a != b for a, b in zip(imagenes_anteriores, parser.imagenes)))
                self.assertNotIn("505.619018", contenido)
            imagenes_anteriores = parser.imagenes
        self.assertEqual(simulador.PARAMETROS_PREDETERMINADOS["T1"], 288.15)
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_cinco_ejecuciones_mezcladas_terminal_web(self):
        rutas = []
        for indice in range(5):
            with redirect_stdout(StringIO()):
                if indice % 2 == 0:
                    rutas.append(simulador.main(self.carpeta))
                else:
                    respuesta = self.client.post("/", data=self.datos)
                    self.assertEqual(respuesta.status_code, 303)
                    rutas.append(self.carpeta / respuesta.location.rsplit("/", 1)[1])
        self.assertFalse(rutas[0].exists())
        self.assertTrue(all(ruta.exists() for ruta in rutas[1:]))
        self.assertEqual(len(list(self.carpeta.glob("*.html"))), 4)
        self.assertEqual(self.client.get("/informes/" + rutas[0].name).status_code, 404)

    def test_casos_no_admisibles_conservan_datos_e_historial(self):
        self.carpeta.mkdir()
        previo = self.carpeta / "notas.html"
        previo.write_text("archivo ajeno", encoding="utf-8")
        for T3 in ("400", "500"):
            with self.subTest(T3=T3):
                respuesta = self.client.post("/", data={**self.datos, "T3": T3})
                self.assertEqual(respuesta.status_code, 400)
                texto = respuesta.get_data(as_text=True)
                self.assertIn("no son admisibles", texto)
                self.assertIn(f'value="{T3}"', texto)
                self.assertEqual(list(self.carpeta.iterdir()), [previo])
                self.assertEqual(previo.read_text(encoding="utf-8"), "archivo ajeno")

    def test_error_inesperado_se_registra_y_no_se_presenta_como_fisico(self):
        with patch.object(simulador, "guardar_grafica_rendimiento", side_effect=ValueError("DETALLE_INTERNO_SECRETO")):
            with self.assertLogs(web_app.app.logger, level="ERROR") as registro:
                respuesta = self.client.post("/", data=self.datos)
        self.assertEqual(respuesta.status_code, 500)
        texto = respuesta.get_data(as_text=True)
        self.assertIn("error interno", texto)
        self.assertNotIn("DETALLE_INTERNO_SECRETO", texto)
        self.assertIn("DETALLE_INTERNO_SECRETO", "\n".join(registro.output))
        self.assertFalse(self.carpeta.exists())

    def test_no_se_exponen_archivos_ajenos_o_rutas_locales(self):
        self.carpeta.mkdir()
        nombre = "brayton_2026-10-17_00-00-00-000000_" + "a" * 32 + ".html"
        (self.carpeta / nombre).write_text("archivo ajeno sin marcas", encoding="utf-8")
        for ruta in ("/main.py", "/AGENTS.md", "/informes/main.py", "/informes/..%2Fmain.py", "/informes/" + nombre):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 404)

    def test_servidor_se_configura_solo_para_loopback_sin_debug(self):
        with patch.object(web_app.app, "run") as run:
            web_app.iniciar_servidor()
        run.assert_called_once_with(host="127.0.0.1", port=5000, debug=False,
                                    use_reloader=False, threaded=False)

    def test_importar_modulos_no_ejecuta_ni_escucha(self):
        codigo = """
from unittest.mock import patch
with patch('flask.Flask.run', side_effect=AssertionError('servidor iniciado')):
    with patch('reporting.guardar_informe_html', side_effect=AssertionError('informe creado')):
        import main
        import web_app
"""
        resultado = subprocess.run([sys.executable, "-B", "-c", codigo],
                                   capture_output=True, text=True, check=True, timeout=20)
        self.assertEqual(resultado.stdout, "")

    def test_main_directo_con_valores_predeterminados(self):
        # Ejecuta realmente el punto de entrada; reemplaza solo su destino para
        # no consumir el historial de informes que está revisando el usuario.
        codigo = """
import runpy, sys
from pathlib import Path
import reporting
guardar = reporting.guardar_informe_html
def guardar_en_prueba(contenido, carpeta, fecha):
    return guardar(contenido, Path(sys.argv[1]), fecha)
reporting.guardar_informe_html = guardar_en_prueba
runpy.run_path('main.py', run_name='__main__')
"""
        resultado = subprocess.run([sys.executable, "-B", "-c", codigo, str(self.carpeta)],
                                   capture_output=True, text=True, check=True, timeout=30)
        self.assertEqual(len(resultado.stdout.splitlines()), 3)
        archivos = list(self.carpeta.glob("*.html"))
        self.assertEqual(len(archivos), 1)
        self.assertIn("505.619018", archivos[0].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
