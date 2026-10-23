"""Verificación de resultados, imágenes y conservación segura de informes."""

from base64 import b64decode
from contextlib import redirect_stdout
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from io import BytesIO, StringIO
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

import matplotlib.image as mpimg
import main
import reporting


class InformeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.imagenes = []
        self.externos = []

    def handle_starttag(self, tag, attrs):
        for nombre, valor in attrs:
            if nombre in ("src", "href") and not valor.startswith("#"):
                if tag == "img" and valor.startswith("data:image/png;base64,"):
                    self.imagenes.append(b64decode(valor.split(",", 1)[1], validate=True))
                else:
                    self.externos.append(valor)


class InformesTests(unittest.TestCase):
    def test_referencia_fisica(self):
        ideal = main.calcular_ciclo_ideal(288.15, 1600, 1.4, 1005, 10, 100)
        real = main.calcular_ciclo_noideal(288.15, 1600, 1.4, 1005, 10, 100, .85, .90, .05)
        for clave, esperado in (
            ("trabajo_compresor", 269.521453330597),
            ("trabajo_turbina", 775.1404715796212),
            ("trabajo_neto", 505.61901824902424),
            ("calor_aportado", 1048.887796669403),
            ("rendimiento", .48205253207687887),
        ):
            with self.subTest(clave=clave):
                self.assertAlmostEqual(ideal[clave], esperado, places=10)
        self.assertAlmostEqual(real["trabajo_neto"], 369.47630104478424, places=10)
        self.assertAlmostEqual(real["rendimiento"], .3689873237449492, places=12)
        self.assertAlmostEqual(main.calcular_relacion_optima(288.15, 1600, 1.4), 20.085256292117077, places=10)

    def test_cinco_ejecuciones_completas_html_e_imagenes(self):
        raiz = Path(main.__file__).resolve().parent
        historicos = {p: sha256(p.read_bytes()).hexdigest() for p in raiz.glob("*.png")}
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal) / "outputs"
            carpeta.mkdir()
            ajenos = {
                "notas.html": b"archivo ajeno",
                "grafica_historica.png": b"PNG historico ajeno",
                "brayton_2020-01-01_00-00-00-000000_" + "a" * 32 + ".html": b"sin marcas propias",
                "brayton_2020-01-01_00-00-00-000000_" + "b" * 32 + ".html": b"\xff\xfe",
                "brayton_2020-01-01_00-00-00-000000_" + "c" * 32 + ".html": reporting.MARCA_INICIO.encode() + b"incompleto",
            }
            for nombre, contenido in ajenos.items():
                (carpeta / nombre).write_bytes(contenido)
            rutas = []
            # Se comparan los bytes incrustados con los siete buffers suministrados
            # al generador en cada ejecución, no con archivos PNG del disco.
            creador_real = main.crear_informe_html
            for _ in range(5):
                salida = StringIO()
                with patch.object(main, "crear_informe_html", wraps=creador_real) as creador:
                    with redirect_stdout(salida):
                        ruta = main.main(carpeta)
                rutas.append(ruta)
                self.assertEqual(len(salida.getvalue().splitlines()), 3)
                documento = ruta.read_text(encoding="utf-8")
                parser = InformeParser()
                parser.feed(documento)
                self.assertEqual(len(parser.imagenes), 7)
                self.assertEqual(parser.externos, [])
                originales = creador.call_args.args[7]
                self.assertCountEqual(parser.imagenes, originales.values())
                for png in parser.imagenes:
                    pixels = mpimg.imread(BytesIO(png), format="png")
                    self.assertEqual(pixels.shape[:2], (900, 1350))
                    self.assertGreater(float(pixels.std()), .05)
                for texto in ("505.619018", "369.476301", "48.205253", "36.898732",
                              "287.142857", "1.061678", "20.085256",
                              "532.802230", "kJ/kg", "m³/kg", "kJ/(kg·K)",
                              "Comprobaciones ejecutadas", "1600.00"):
                    self.assertIn(texto, documento)
                numerico = creador.call_args.args[-1]["ideal"]["numerico"]
                self.assertIn(f"{numerico['rp']:.6f}", documento)
                self.assertTrue(documento.endswith(reporting.MARCA_FINAL))
                self.assertIn("Commit Git:", documento)
                self.assertIn(creador.call_args.args[9]["commit"] or "No disponible", documento)
            self.assertFalse(rutas[0].exists())
            self.assertTrue(all(p.exists() for p in rutas[1:]))
            self.assertEqual(len(set(rutas)), 5)
            for nombre, contenido in ajenos.items():
                self.assertEqual((carpeta / nombre).read_bytes(), contenido)
            self.assertEqual(len(list(carpeta.iterdir())), 4 + len(ajenos))
            self.assertEqual(list(carpeta.glob("*.tmp")), [])
        self.assertEqual(historicos, {p: sha256(p.read_bytes()).hexdigest() for p in historicos})

    def test_fallo_de_calculo_no_toca_informes_anteriores(self):
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            previo = carpeta / "previo.html"
            previo.write_text("informe anterior", encoding="utf-8")
            with patch.object(main, "calcular_temperaturas", side_effect=ValueError("dato inválido")):
                with self.assertRaisesRegex(ValueError, "dato inválido"):
                    main.main(carpeta)
            self.assertEqual(list(carpeta.iterdir()), [previo])
            self.assertEqual(previo.read_text(encoding="utf-8"), "informe anterior")

    def test_fallo_de_publicacion_no_limpia_ni_deja_html_parcial(self):
        fecha = datetime(2026, 10, 17, tzinfo=timezone.utc)
        completo = reporting.MARCA_INICIO + "\n<html>completo</html>\n" + reporting.MARCA_FINAL
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            rutas = [reporting.guardar_informe_html(completo, carpeta, fecha) for _ in range(4)]
            contenido_previo = {p: p.read_bytes() for p in rutas}
            with patch.object(Path, "open", side_effect=PermissionError("fallo de escritura")):
                with self.assertRaisesRegex(PermissionError, "escritura"):
                    reporting.guardar_informe_html(completo, carpeta, fecha)
            self.assertEqual({p: p.read_bytes() for p in carpeta.iterdir()}, contenido_previo)
            with patch.object(Path, "rename", side_effect=OSError("fallo de publicación")):
                with self.assertRaisesRegex(OSError, "publicación"):
                    reporting.guardar_informe_html(completo, carpeta, fecha)
            self.assertEqual({p: p.read_bytes() for p in carpeta.iterdir()}, contenido_previo)

    def test_nombre_repetido_no_sobrescribe(self):
        fecha = datetime(2026, 10, 17, tzinfo=timezone.utc)
        completo = reporting.MARCA_INICIO + "texto" + reporting.MARCA_FINAL
        with tempfile.TemporaryDirectory() as temporal:
            with patch.object(reporting, "uuid4") as uuid:
                uuid.return_value.hex = "a" * 32
                ruta = reporting.guardar_informe_html(completo, temporal, fecha)
                with self.assertRaises(FileExistsError):
                    reporting.guardar_informe_html(completo + "nuevo" + reporting.MARCA_FINAL, temporal, fecha)
                self.assertEqual(ruta.read_text(encoding="utf-8"), completo)

    def test_html_escapa_texto_y_rechaza_imagen_invalida(self):
        tabla = reporting.tabla_html(("A&B",), [("<script>",)])
        self.assertIn("A&amp;B", tabla)
        self.assertIn("&lt;script&gt;", tabla)
        self.assertNotIn("<script>", tabla)
        with self.assertRaises(ValueError):
            reporting.imagen_html(b"no es png", "gráfica")
        with tempfile.TemporaryDirectory() as temporal:
            with self.assertRaises(ValueError):
                reporting.guardar_informe_html("HTML incompleto", temporal, datetime.now())
            self.assertEqual(list(Path(temporal).iterdir()), [])

    def test_temporal_ajeno_con_nombre_repetido_se_conserva(self):
        fecha = datetime(2026, 10, 17, tzinfo=timezone.utc)
        completo = reporting.MARCA_INICIO + "texto" + reporting.MARCA_FINAL
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            nombre = ".brayton_2026-10-17_00-00-00-000000_" + "a" * 32 + ".html.tmp"
            ajeno = carpeta / nombre
            ajeno.write_text("temporal ajeno", encoding="utf-8")
            with patch.object(reporting, "uuid4") as uuid:
                uuid.return_value.hex = "a" * 32
                with self.assertRaises(FileExistsError):
                    reporting.guardar_informe_html(completo, carpeta, fecha)
            self.assertEqual(ajeno.read_text(encoding="utf-8"), "temporal ajeno")

    def test_grafica_en_memoria_refleja_gamma(self):
        curvas = []
        for gamma in (1.3, 1.4):
            with BytesIO() as buffer:
                main.guardar_grafica_rendimiento(gamma, buffer)
                curvas.append(buffer.getvalue())
        self.assertNotEqual(curvas[0], curvas[1])

    def test_version_git_limpia_y_con_cambios(self):
        for estado in ("", " M main.py\n", "A  reporting.py\n", "?? nuevo.py\n"):
            with self.subTest(estado=estado):
                respuestas = [subprocess.CompletedProcess([], 0, "a" * 40),
                              subprocess.CompletedProcess([], 0, estado)]
                with patch.object(reporting.subprocess, "run", side_effect=respuestas):
                    version = reporting.obtener_version_git(Path("."))
                self.assertEqual(version, {"commit": "a" * 40, "modificado": bool(estado)})

    def test_git_no_disponible_no_se_presenta_como_limpio(self):
        for error in (FileNotFoundError(), subprocess.CalledProcessError(128, ["git"]),
                      subprocess.TimeoutExpired(["git"], 5)):
            with self.subTest(error=type(error).__name__):
                with patch.object(reporting.subprocess, "run", side_effect=error):
                    self.assertEqual(reporting.obtener_version_git("."), {"commit": None, "modificado": None})

    def test_cabecera_distingue_git_limpio_modificado_y_desconocido(self):
        # Reutiliza las entradas reales ya calculadas una vez, sin repetir simulaciones.
        crear = reporting.crear_informe_html
        with tempfile.TemporaryDirectory() as temporal:
            with patch.object(main, "crear_informe_html", wraps=crear) as generador:
                with redirect_stdout(StringIO()):
                    main.main(temporal)
            argumentos = list(generador.call_args.args)
            for version, esperado in (
                ({"commit": "a" * 40, "modificado": False}, "Árbol de trabajo limpio"),
                ({"commit": "a" * 40, "modificado": True}, "Cambios sin confirmar"),
                ({"commit": None, "modificado": None}, "Estado Git no disponible"),
            ):
                argumentos[9] = version
                documento = crear(*argumentos, **generador.call_args.kwargs)
                self.assertIn(esperado, documento)
                self.assertIn(version["commit"] or "No disponible", documento)
                if version["modificado"] is not False:
                    self.assertNotIn("Árbol de trabajo limpio", documento)


if __name__ == "__main__":
    unittest.main()
