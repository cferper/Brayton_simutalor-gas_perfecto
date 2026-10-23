"""V.5: contratos HTTP, aislamiento e informes, sin servidor ni archivos reales."""

from contextlib import redirect_stdout
from datetime import datetime, timezone
from html.parser import HTMLParser
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import dashboard
import main
import reporting
import segunda_ley
import web_app
from sensibilidad import argumentos_fisicos
from viabilidad import evaluar_punto


class FormularioParser(HTMLParser):
    """Recoge controles por nombre y su opción seleccionada, sin ejecutar JavaScript."""

    def __init__(self):
        super().__init__()
        self.campos = {}
        self.seleccion_actual = None

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        if tag in ("input", "select") and atributos.get("name"):
            self.campos[atributos["name"]] = atributos
            if tag == "select":
                self.seleccion_actual = atributos["name"]
        if tag == "option" and self.seleccion_actual and "selected" in atributos:
            self.campos[self.seleccion_actual]["seleccion"] = atributos.get("value")

    def handle_endtag(self, tag):
        if tag == "select":
            self.seleccion_actual = None


class VerificacionIntegracionWebV5(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory(prefix="brayton_v5_")
        self.addCleanup(temporal.cleanup)
        self.raiz = Path(temporal.name)
        self.salidas = self.raiz / "informes"
        config = patch.dict(web_app.app.config, {
            "OUTPUTS_DIR": self.salidas, "TESTING": False, "PROPAGATE_EXCEPTIONS": False,
        })
        config.start()
        self.addCleanup(config.stop)
        self.cliente = web_app.app.test_client()
        self.form = {k: str(v) for k, v in web_app.valores_formulario().items()}
        self.form.update(T1="310", T3="1750", p1="110", cp="1020", gamma="1.37",
                         relacion_presiones="8", eta_c="0.88", eta_t="0.91",
                         perdida_presion_combustor="7.5")
        self.fisicos = {k: float(v) for k, v in self.form.items()}
        self.fisicos["perdida_presion_combustor"] = 0.075
        self.sens = dict(sens_parametro="T3", sens_minimo="1200", sens_maximo="1900",
                         sens_muestras="3")
        self.mapa = dict(mapa_rp_min="2", mapa_rp_max="18", mapa_T3_min="1200",
                         mapa_T3_max="1900", mapa_n_rp="3", mapa_n_T3="3",
                         mapa_escala="lineal", mapa_cortes="1300, 1800")

    def _informe(self, tipo, *, parametros=None, segunda_ley=None):
        """Construye un informe propio sintético con marcas, paneles y metadatos."""
        p = (parametros or self.fisicos).copy()
        metadata = {"dashboard": 1, "tipo": tipo, "parametros": p,
                    "fecha": "2026-10-23T09:00:00+02:00",
                    "git": {"commit": "a" * 40, "modificado": False}}
        if tipo == "sensibilidad":
            metadata["estudio"] = {"parametro": "T3", "minimo": 1200.0,
                                   "maximo": 1900.0, "muestras": 3}
        if tipo == "mapa":
            metadata["mapa"] = {"rp_min": 2.0, "rp_max": 18.0, "T3_min": 1200.0,
                                "T3_max": 1900.0, "n_rp": 3, "n_T3": 3,
                                "escala": "lineal", "cortes": [1300.0, 1800.0]}
        if segunda_ley is not None:
            metadata["segunda_ley"] = segunda_ley
        elif tipo == "segunda_ley":
            metadata["segunda_ley"] = {"T0": 303.15}
        paneles = {k: f'<p data-origen="{tipo}">{tipo} {k}</p>'
                  for k in ("resultados", "optimizacion", "sensibilidad", "mapa", "segunda_ley")}
        valores = p.copy()
        valores["perdida_presion_combustor"] *= 100
        if metadata.get("segunda_ley"):
            valores["T0"] = metadata["segunda_ley"]["T0"]
        if metadata.get("estudio"):
            c = metadata["estudio"]
            valores.update(sens_parametro=c["parametro"], sens_minimo=c["minimo"],
                           sens_maximo=c["maximo"], sens_muestras=c["muestras"])
        if metadata.get("mapa"):
            c = metadata["mapa"]
            valores.update({"mapa_" + k: v for k, v in c.items() if k != "cortes"})
            valores["mapa_cortes"] = ", ".join(map(str, c["cortes"]))
        contenido = (reporting.MARCA_INICIO +
                     dashboard.renderizar_dashboard(valores, contenidos=paneles, metadata=metadata,
                                                    modo_local=False, seccion_inicial=tipo) +
                     reporting.MARCA_FINAL)
        ruta = reporting.guardar_informe_html(contenido, self.salidas,
                                             datetime(2026, 10, 23, 9, tzinfo=timezone.utc))
        return ruta, contenido, metadata

    def test_enrutamiento_simulacion_y_nueve_entradas(self):
        with patch.object(web_app, "main", return_value=self.salidas / "normal.html") as ejecutar, \
             patch.object(web_app, "ejecutar_sensibilidad") as sens, \
             patch.object(web_app, "ejecutar_mapa") as mapa, \
             patch.object(web_app, "ejecutar_segunda_ley") as ley:
            respuesta = self.cliente.post("/", data={**self.form, "accion": "normal", "T0": "302.5"})
        self.assertEqual((respuesta.status_code, respuesta.location), (303, "/informes/normal.html"))
        ejecutar.assert_called_once_with(self.salidas, parametros=self.fisicos, T0=302.5)
        sens.assert_not_called(); mapa.assert_not_called(); ley.assert_not_called()

    def test_enrutamiento_sensibilidad_y_T0_no_aplicable(self):
        with patch.object(web_app, "ejecutar_sensibilidad", return_value=self.salidas / "sens.html") as ejecutar, \
             patch.object(web_app, "main") as normal, patch.object(web_app, "ejecutar_mapa") as mapa, \
             patch.object(web_app, "ejecutar_segunda_ley") as ley:
            respuesta = self.cliente.post("/", data={**self.form, **self.sens,
                "accion": "sensibilidad", "T0": "no se usa"})
        self.assertEqual((respuesta.status_code, respuesta.location), (303, "/informes/sens.html"))
        ejecutar.assert_called_once_with(self.salidas, self.fisicos, parametro="T3",
                                         minimo=1200.0, maximo=1900.0, muestras=3)
        normal.assert_not_called(); mapa.assert_not_called(); ley.assert_not_called()

    def test_enrutamiento_mapa_y_configuracion_tipificada(self):
        with patch.object(web_app, "ejecutar_mapa", return_value=self.salidas / "mapa.html") as ejecutar, \
             patch.object(web_app, "main") as normal, \
             patch.object(web_app, "ejecutar_sensibilidad") as sens, \
             patch.object(web_app, "ejecutar_segunda_ley") as ley:
            respuesta = self.cliente.post("/", data={**self.form, **self.mapa,
                "accion": "mapa", "T0": "no se usa"})
        self.assertEqual((respuesta.status_code, respuesta.location), (303, "/informes/mapa.html"))
        ejecutar.assert_called_once_with(self.salidas, self.fisicos, rp_min=2.0, rp_max=18.0,
                                         T3_min=1200.0, T3_max=1900.0, n_rp=3, n_T3=3,
                                         escala="lineal", cortes=(1300.0, 1800.0))
        normal.assert_not_called(); sens.assert_not_called(); ley.assert_not_called()

    def test_enrutamiento_segunda_ley_y_T0(self):
        with patch.object(web_app, "ejecutar_segunda_ley", return_value=self.salidas / "ley.html") as ejecutar, \
             patch.object(web_app, "main") as normal, \
             patch.object(web_app, "ejecutar_sensibilidad") as sens, \
             patch.object(web_app, "ejecutar_mapa") as mapa:
            respuesta = self.cliente.post("/", data={**self.form, "accion": "segunda_ley",
                                                       "T0": "303.15"})
        self.assertEqual((respuesta.status_code, respuesta.location), (303, "/informes/ley.html"))
        ejecutar.assert_called_once_with(self.salidas, self.fisicos, 303.15, None)
        normal.assert_not_called(); sens.assert_not_called(); mapa.assert_not_called()

    def test_rechazos_multiseccion_conservan_datos_y_no_generan_informes(self):
        casos = [
            ("normal", {"T1": ""}, "obligatorio"),
            ("normal", {"p1": "NaN"}, "finito"),
            ("sensibilidad", {**self.sens, "sens_minimo": "2000", "sens_maximo": "1200"}, "sensibilidad"),
            ("sensibilidad", {**self.sens, "T3": "250", "T1": "310"}, "referencia"),
            ("mapa", {**self.mapa, "mapa_n_rp": "2"}, "mapa"),
            ("mapa", {**self.mapa, "mapa_cortes": "nan"}, "mapa"),
            ("segunda_ley", {"T0": "inf"}, "T0"),
        ]
        for accion, cambios, mensaje in casos:
            with self.subTest(accion=accion, cambios=cambios), \
                 patch.object(web_app, "main") as normal, \
                 patch.object(web_app, "ejecutar_sensibilidad") as sens, \
                 patch.object(web_app, "ejecutar_mapa") as mapa, \
                 patch.object(web_app, "ejecutar_segunda_ley") as ley:
                datos = {**self.form, "accion": accion, **cambios}
                respuesta = self.cliente.post("/", data=datos)
                self.assertEqual(respuesta.status_code, 400)
                html = respuesta.get_data(as_text=True)
                self.assertIn(mensaje, html)
                self.assertIn(f'data-initial-section="{accion if accion != "normal" else "simulacion"}"', html)
                form = FormularioParser(); form.feed(html)
                for k, v in datos.items():
                    if k in dashboard.CAMPOS or k == "T0":
                        self.assertEqual(form.campos[k].get("value"), v)
                normal.assert_not_called(); sens.assert_not_called()
                mapa.assert_not_called(); ley.assert_not_called()
        self.assertFalse(self.salidas.exists())

    def test_cuatro_ejecuciones_reales_aisladas_y_retencion(self):
        configuraciones = [
            ("normal", {}, "normal"),
            ("sensibilidad", self.sens, "sensibilidad"),
            ("mapa", self.mapa, "mapa"),
            ("segunda_ley", {"T0": "298.15"}, "segunda_ley"),
        ]
        anteriores = {}
        for accion, extras, tipo in configuraciones:
            with self.subTest(accion=accion), redirect_stdout(StringIO()):
                respuesta = self.cliente.post("/", data={**self.form, **extras, "accion": accion})
                self.assertEqual(respuesta.status_code, 303)
                ruta = self.salidas / respuesta.location.rsplit("/", 1)[1]
                texto = ruta.read_text(encoding="utf-8")
                metadata, paneles = dashboard.separar_presentacion(texto)
                self.assertEqual(metadata["tipo"], tipo)
                self.assertEqual(metadata["parametros"], self.fisicos)
                self.assertEqual(set(metadata["parametros"]), set(dashboard.CAMPOS))
                self.assertIn("fecha", metadata)
                self.assertIn("git", metadata)
                self.assertTrue(paneles[{"normal": "resultados", "sensibilidad": "sensibilidad",
                                         "mapa": "mapa", "segunda_ley": "segunda_ley"}[tipo]])
                if tipo == "sensibilidad":
                    self.assertEqual(metadata["estudio"]["muestras"], 3)
                    self.assertEqual(metadata["estudio"]["parametro"], "T3")
                if tipo == "mapa":
                    self.assertEqual(metadata["mapa"]["n_rp"], 3)
                    self.assertEqual(metadata["mapa"]["cortes"], [1300.0, 1800.0])
                if tipo == "segunda_ley":
                    self.assertEqual(metadata["segunda_ley"]["T0"], 298.15)
                for nombre, original in anteriores.items():
                    self.assertEqual((self.salidas / nombre).read_bytes(), original)
                anteriores[ruta.name] = ruta.read_bytes()
        self.assertEqual(len(anteriores), 4)
        self.assertEqual({p.name for p in self.salidas.glob("*.html")}, set(anteriores))

    def test_historial_metadata_fecha_git_legado_y_filtrado(self):
        ruta, texto, datos = self._informe("normal")
        antiguo = reporting.guardar_informe_html(reporting.MARCA_INICIO +
            "<html><header>Histórico</header><body>Anterior</body></html>" +
            reporting.MARCA_FINAL, self.salidas, datetime.now(timezone.utc))
        ilegible = self.salidas / "apuntes.html"
        ilegible.write_text("personal", encoding="utf-8")
        incompleto = self.salidas / ("brayton_2026-10-23_08-00-00-000000_" + "b" * 32 + ".html")
        incompleto.write_text(reporting.MARCA_INICIO + "sin cierre", encoding="utf-8")
        fuera = self.raiz / "fuera.txt"; fuera.write_text("personal", encoding="utf-8")
        enlace = self.salidas / ("brayton_2026-10-23_08-00-00-000000_" + "c" * 32 + ".html")
        enlace.symlink_to(fuera)
        antes = {p.name: p.read_bytes() for p in self.salidas.iterdir() if not p.is_symlink()}
        entradas = web_app.listar_informes()
        self.assertEqual({i["nombre"] for i in entradas}, {ruta.name, antiguo.name})
        self.assertEqual({i["tipo"] for i in entradas}, {"Simulación normal", "Informe anterior"})
        registrado = next(i for i in entradas if i["nombre"] == ruta.name)
        self.assertEqual(registrado["fecha"], datos["fecha"])
        self.assertEqual(registrado["commit"], datos["git"]["commit"])
        self.assertIn("T1=310", registrado["resumen"])
        self.assertIn("rp=8", registrado["resumen"])
        self.assertEqual(antes, {p.name: p.read_bytes() for p in self.salidas.iterdir() if not p.is_symlink()})
        self.assertEqual(self.cliente.get("/informes/" + antiguo.name).status_code, 200)

    def test_recuperacion_cuatro_informes_descarga_identica_sin_recalculo(self):
        for tipo in ("normal", "sensibilidad", "mapa", "segunda_ley"):
            with self.subTest(tipo=tipo):
                ruta, original, metadata = self._informe(tipo)
                with patch.object(web_app, "main", side_effect=AssertionError("recalculo")), \
                     patch.object(web_app, "ejecutar_sensibilidad", side_effect=AssertionError("recalculo")), \
                     patch.object(web_app, "ejecutar_mapa", side_effect=AssertionError("recalculo")), \
                     patch.object(web_app, "ejecutar_segunda_ley", side_effect=AssertionError("recalculo")):
                    vista = self.cliente.get("/informes/" + ruta.name)
                    descarga = self.cliente.get("/informes/" + ruta.name + "?descargar=1")
                self.assertEqual(vista.status_code, 200)
                self.assertEqual(descarga.status_code, 200)
                self.assertEqual(descarga.get_data(as_text=True), original)
                self.assertEqual(descarga.data, ruta.read_bytes())
                self.assertIn("attachment", descarga.headers["Content-Disposition"])
                form = FormularioParser(); form.feed(vista.get_data(as_text=True))
                for k, v in self.fisicos.items():
                    esperado = 7.5 if k == "perdida_presion_combustor" else v
                    self.assertEqual(float(form.campos[k]["value"]), esperado)
                self.assertEqual(form.campos["informe_origen"]["value"], ruta.name)
                if tipo == "sensibilidad":
                    self.assertEqual(form.campos["sens_parametro"]["seleccion"], "T3")
                    self.assertEqual(form.campos["sens_muestras"]["value"], "3")
                if tipo == "mapa":
                    self.assertEqual(form.campos["mapa_n_rp"]["value"], "3")
                    self.assertEqual(form.campos["mapa_escala"]["seleccion"], "lineal")
                    self.assertEqual(form.campos["mapa_cortes"]["value"], "1300.0, 1800.0")
                if tipo == "segunda_ley":
                    self.assertEqual(float(form.campos["T0"]["value"]), 303.15)
                self.assertEqual((self.salidas / ruta.name).read_text(encoding="utf-8"), original)

    def test_reutilizacion_segunda_ley_solo_si_nueve_entradas_coinciden(self):
        T1, T3, gamma, cp, p1, ec, et, delta = argumentos_fisicos(self.fisicos)
        estados = {
            "ideal": evaluar_punto(T1, T3, gamma, cp, self.fisicos["relacion_presiones"], p1),
            "noideal": evaluar_punto(T1, T3, gamma, cp, self.fisicos["relacion_presiones"],
                                      p1, ec, et, delta),
        }
        previo = segunda_ley.analizar_segunda_ley(estados, cp, gamma, 303.15)
        previo_serializado = json.loads(json.dumps(previo))  # Las tuplas pasan a listas en HTML/JSON.
        ruta, _, _ = self._informe("segunda_ley", segunda_ley=previo)
        self.assertEqual(web_app.estudio_conservado(ruta.name, self.fisicos), previo_serializado)
        otros = {**self.fisicos, "eta_t": 0.9}
        self.assertIsNone(web_app.estudio_conservado(ruta.name, otros))
        with patch.object(web_app, "ejecutar_segunda_ley", return_value=self.salidas / "nuevo.html") as ejecutar:
            respuesta = self.cliente.post("/", data={**self.form, "accion": "segunda_ley",
                "T0": "310.5", "informe_origen": ruta.name})
            self.assertEqual(respuesta.status_code, 303)
            ejecutar.assert_called_once_with(self.salidas, self.fisicos, 310.5, previo_serializado)
            ejecutar.reset_mock()
            respuesta = self.cliente.post("/", data={**self.form, "eta_t": "0.9",
                "accion": "segunda_ley", "T0": "310.5", "informe_origen": ruta.name})
            self.assertEqual(respuesta.status_code, 303)
            ejecutar.assert_called_once_with(self.salidas, otros, 310.5, None)
        # Con un estudio físicamente válido, actualizar T0 no debe recalcular estados.
        with patch("viabilidad.evaluar_punto", side_effect=AssertionError("recalculó los estados")):
            respuesta = self.cliente.post("/", data={**self.form, "accion": "segunda_ley",
                "T0": "310.5", "informe_origen": ruta.name})
        self.assertEqual(respuesta.status_code, 303)
        guardado = self.salidas / respuesta.location.rsplit("/", 1)[1]
        actualizado, _ = dashboard.separar_presentacion(guardado.read_text(encoding="utf-8"))
        modelo = actualizado["segunda_ley"]
        self.assertEqual(modelo["T0"], 310.5)
        for nombre in ("ideal", "noideal"):
            antes, despues = previo_serializado["modelos"][nombre], modelo["modelos"][nombre]
            self.assertEqual(antes["entropias"], despues["entropias"])
            self.assertEqual(antes["temperaturas"], despues["temperaturas"])
            for equipo in ("compresor", "turbina"):
                self.assertAlmostEqual(despues["componentes"][equipo]["exergia_destruida"],
                                       310.5 * antes["componentes"][equipo]["valor"], places=12)

    def test_rutas_malformadas_symlink_e_informe_incompleto(self):
        ruta, _, _ = self._informe("normal")
        referencia = self.raiz / "privado.html"
        referencia.write_bytes(ruta.read_bytes())
        alias = self.salidas / ("brayton_2026-10-23_08-00-00-000000_" + "c" * 32 + ".html")
        alias.symlink_to(referencia)
        incompleto = self.salidas / ("brayton_2026-10-23_08-00-00-000000_" + "d" * 32 + ".html")
        incompleto.write_text(reporting.MARCA_INICIO + "sin marca final", encoding="utf-8")
        for nombre in ("web_app.py", "..%2Fprivado.html", alias.name, incompleto.name):
            with self.subTest(nombre=nombre):
                self.assertEqual(self.cliente.get("/informes/" + nombre).status_code, 404)
                self.assertEqual(self.cliente.get("/informes/" + nombre + "?descargar=1").status_code, 404)
        for documento in ("main.py", "..%2Fmain.py", "AGENTS.md"):
            self.assertEqual(self.cliente.get("/documentacion/" + documento).status_code, 404)
        self.assertIsNone(web_app.estudio_conservado(alias.name, self.fisicos))
        self.assertIsNone(web_app.estudio_conservado(incompleto.name, self.fisicos))

    def test_excepcion_interna_del_mapa_no_se_presenta_como_fisica(self):
        with patch.object(web_app, "ejecutar_mapa", side_effect=RuntimeError("FALLO_INTERNO_V5")):
            with self.assertLogs(web_app.app.logger, level="ERROR") as registro:
                respuesta = self.cliente.post("/", data={**self.form, **self.mapa, "accion": "mapa"})
        texto = respuesta.get_data(as_text=True)
        self.assertEqual(respuesta.status_code, 500)
        self.assertIn("error interno", texto)
        self.assertNotIn("FALLO_INTERNO_V5", texto)
        self.assertNotIn("Inviabilidad física", texto)
        self.assertIn("FALLO_INTERNO_V5", "\n".join(registro.output))
        self.assertFalse(self.salidas.exists())

    def test_secciones_educativas_conectadas_sin_duplicar_formulario(self):
        html = self.cliente.get("/").get_data(as_text=True)
        parser = FormularioParser(); parser.feed(html)
        self.assertEqual(set(self.fisicos), set(dashboard.CAMPOS))
        self.assertEqual(set(dashboard.CAMPOS).issubset(parser.campos), True)
        for nombre in dashboard.CAMPOS:
            self.assertEqual(html.count(f'name="{nombre}"'), 1)
        for nombre, _ in dashboard.SECCIONES:
            with self.subTest(seccion=nombre):
                self.assertIn(f'<section class="dashboard-panel" id="{nombre}"', html)
                if nombre in ("informes", "ayuda"):
                    self.assertIn(f'id="titulo-{nombre}"', html)
                    continue
                self.assertIn(f'data-edu-tabs="{nombre}"', html)
                self.assertIn(f'id="{nombre}-vista-uso"', html)
                self.assertIn(f'id="{nombre}-vista-fundamentos"', html)
                self.assertIn(f'id="{nombre}-tab-fundamentos"', html)
        for k in ("normal", "sensibilidad", "mapa", "segunda_ley"):
            self.assertIn(f'value="{k}"', html)
        self.assertIn('href="#informes"', html)
        self.assertIn('name="informe_origen"', html)


if __name__ == "__main__":
    unittest.main()
