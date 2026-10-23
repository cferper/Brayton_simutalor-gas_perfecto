"""V.4: oráculos físicos y trazabilidad de Simulación, gráficos y HTML.

No utiliza funciones de producción para construir las referencias físicas.
Intercepta Figure.savefig para inspeccionar las coordenadas, no los píxeles.
"""

from base64 import b64decode
from contextlib import contextmanager, redirect_stdout
from hashlib import sha256
from io import BytesIO, StringIO
from math import log
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import dashboard
import main
import reporting
import web_app
from optimizacion import optimizar_trabajo_neto
from optimizacion_rendimiento import optimizar_rendimiento
from viabilidad import construir_barrido


BASE = dict(main.PARAMETROS_PREDETERMINADOS)
ALTERNO = {
    "T1": 305.0, "T3": 1450.0, "p1": 145.0, "relacion_presiones": 6.0,
    "cp": 1120.0, "gamma": 1.32, "eta_c": .72, "eta_t": .96,
    "perdida_presion_combustor": .12,
}


def referencia_fisica(parametros, *, ideal=False, rp=None):
    """Oráculo separado: 9 entradas, resultados [K, kPa, kJ/kg, fracción].

    Sólo se usa con entradas finitas moderadas. No invoca main ni viabilidad.
    Para no motores, rendimiento y back work ratio son None.
    """
    T1, T3 = parametros["T1"], parametros["T3"]
    p1, cp, gamma = parametros["p1"], parametros["cp"], parametros["gamma"]
    r = parametros["relacion_presiones"] if rp is None else rp
    ec = 1.0 if ideal else parametros["eta_c"]
    et = 1.0 if ideal else parametros["eta_t"]
    d = 0.0 if ideal else parametros["perdida_presion_combustor"]
    a = (gamma - 1) / gamma
    p2, p3 = p1 * r, p1 * r * (1 - d)
    T2s = T1 * r**a
    T4s = T3 * (p1 / p3)**a
    T2 = T1 + (T2s - T1) / ec
    T4 = T3 - et * (T3 - T4s)
    wc, wt = cp * (T2 - T1) / 1000, cp * (T3 - T4) / 1000
    wnet, qin = wt - wc, cp * (T3 - T2) / 1000
    motor = r > 1 and p3 > p1 and qin > 0 and wnet > 0
    return {
        "temperaturas": (T1, T2, T3, T4), "presiones": (p1, p2, p3, p1),
        "T2s": T2s, "T4s": T4s, "trabajo_compresor": wc,
        "trabajo_turbina": wt, "trabajo_neto": wnet, "calor_aportado": qin,
        "rendimiento": wnet / qin if motor else None,
        "back_work_ratio": wc / wt if motor else None, "viable": motor,
    }


@contextmanager
def capturar_figuras():
    """Conserva coordenadas de Figure antes de su cierre; no escribe PNG."""
    figuras = []

    def interceptar(figura, *args, **kwargs):
        figuras.append(figura)

    with patch.object(main.plt.Figure, "savefig", new=interceptar):
        yield figuras


def curva(ejes, etiqueta):
    """Busca una serie por etiqueta semántica, sin depender del orden de plot."""
    coinciden = [linea for linea in ejes.lines if linea.get_label().startswith(etiqueta)]
    if len(coinciden) != 1:
        raise AssertionError(f"Se esperaba una sola serie {etiqueta}: {len(coinciden)}")
    return coinciden[0]


class VerificacionSimulacionIndependiente(unittest.TestCase):
    def comprobar_referencia(self, observado, esperado, *, ideal=False):
        """Compara estados y balances; los redondeos HTML se ensayan aparte."""
        for nombre in ("temperaturas", "presiones"):
            np.testing.assert_allclose(observado[nombre], esperado[nombre], rtol=3e-13, atol=3e-10)
        for clave in ("T2s", "T4s", "trabajo_compresor", "trabajo_turbina",
                      "trabajo_neto", "calor_aportado", "rendimiento", "back_work_ratio"):
            with self.subTest(magnitud=clave, ideal=ideal):
                self.assertAlmostEqual(observado[clave], esperado[clave], delta=3e-10)
        self.assertAlmostEqual(observado["trabajo_neto"],
                               observado["trabajo_turbina"] - observado["trabajo_compresor"], delta=1e-10)
        self.assertAlmostEqual(observado["rendimiento"],
                               observado["trabajo_neto"] / observado["calor_aportado"], delta=1e-12)

    def test_estados_presiones_energia_y_bwr_en_dos_perfiles(self):
        for p in (BASE, ALTERNO):
            with self.subTest(perfil=p["T1"]):
                args = (p["T1"], p["T3"], p["gamma"], p["cp"], p["relacion_presiones"], p["p1"])
                ideal = main.calcular_ciclo_ideal(*args)
                real = main.calcular_ciclo_noideal(*args, p["eta_c"], p["eta_t"],
                                                   p["perdida_presion_combustor"])
                self.comprobar_referencia(ideal, referencia_fisica(p, ideal=True), ideal=True)
                self.comprobar_referencia(real, referencia_fisica(p))
                self.assertGreater(real["trabajo_compresor"], ideal["trabajo_compresor"])
                self.assertLess(real["trabajo_turbina"], ideal["trabajo_turbina"])
                self.assertGreater(real["back_work_ratio"], ideal["back_work_ratio"])

    def test_diagrama_ts_ideal_coordenadas_y_procesos(self):
        p = ALTERNO
        ref = referencia_fisica(p, ideal=True)
        T1, T2, T3, T4 = ref["temperaturas"]
        s3 = p["cp"] / 1000 * log(T3 / T2)
        entropias = (0., 0., s3, s3)
        self.assertAlmostEqual(s3, p["cp"] / 1000 * log(T4 / T1), delta=1e-12)
        with BytesIO() as destino, capturar_figuras() as figuras:
            main.guardar_diagrama_ts(ref["temperaturas"], entropias, p["cp"], destino)
        self.assertEqual(len(figuras), 1)
        eje = figuras[0].axes[0]
        self.assertIn("ideal", eje.get_title().lower())
        self.assertIn("kJ/(kg·K)", eje.get_xlabel())
        self.assertIn("[K]", eje.get_ylabel())
        for clave, ses, temps in (
            ("1→2", np.array([0., 0.]), np.array([T1, T2])),
            ("2→3", p["cp"] / 1000 * np.log(np.linspace(T2, T3, 100) / T2), np.linspace(T2, T3, 100)),
            ("3→4", np.array([s3, s3]), np.array([T3, T4])),
            ("4→1", s3 + p["cp"] / 1000 * np.log(np.linspace(T4, T1, 100) / T4), np.linspace(T4, T1, 100)),
        ):
            linea = curva(eje, clave)
            np.testing.assert_allclose(linea.get_xdata(), ses, rtol=2e-13, atol=2e-12)
            np.testing.assert_allclose(linea.get_ydata(), temps, rtol=2e-13, atol=2e-10)
        np.testing.assert_allclose(eje.collections[0].get_offsets(),
                                   np.column_stack((entropias, ref["temperaturas"])), atol=2e-10)
        self.assertEqual({a.get_text() for a in eje.texts if a.get_text()}, {"1", "2", "3", "4"})

    def test_diagrama_pv_ideal_gas_y_trayectorias(self):
        p = ALTERNO
        ref = referencia_fisica(p, ideal=True)
        R = p["cp"] * (1 - 1 / p["gamma"])
        volumenes = tuple(R * T / (1000 * presion) for T, presion in zip(ref["temperaturas"], ref["presiones"]))
        for T, presion, v in zip(ref["temperaturas"], ref["presiones"], volumenes):
            self.assertAlmostEqual(presion * 1000 * v, R * T, delta=2e-10)
        with BytesIO() as destino, capturar_figuras() as figuras:
            main.guardar_diagrama_pv(ref["temperaturas"], ref["presiones"], volumenes,
                                     R, p["gamma"], destino)
        self.assertEqual(len(figuras), 1)
        eje = figuras[0].axes[0]
        self.assertIn("ideal", eje.get_title().lower())
        self.assertIn("m³/kg", eje.get_xlabel())
        self.assertIn("[kPa]", eje.get_ylabel())
        for clave, v0, v1, p0, tipo in (
            ("1→2", volumenes[0], volumenes[1], ref["presiones"][0], "isentropico"),
            ("2→3", volumenes[1], volumenes[2], ref["presiones"][1], "isobaro"),
            ("3→4", volumenes[2], volumenes[3], ref["presiones"][2], "isentropico"),
            ("4→1", volumenes[3], volumenes[0], ref["presiones"][3], "isobaro"),
        ):
            linea = curva(eje, clave)
            v, presiones = np.asarray(linea.get_xdata()), np.asarray(linea.get_ydata())
            np.testing.assert_allclose(v, np.linspace(v0, v1, 200), rtol=1e-13)
            if tipo == "isobaro":
                np.testing.assert_allclose(presiones, p0, rtol=2e-13)
            else:
                np.testing.assert_allclose(presiones * v**p["gamma"],
                                           p0 * v0**p["gamma"], rtol=2e-12)
            self.assertAlmostEqual(presiones[0], p0, delta=2e-9)
        np.testing.assert_allclose(eje.collections[0].get_offsets(),
                                   np.column_stack((volumenes, ref["presiones"])), atol=2e-9)

    def test_graficas_ideales_rendimiento_trabajo_y_mascaras(self):
        p = BASE
        relaciones = np.array([1., 1.5, 3., 6., 10., 20., 50., 500.])
        b = construir_barrido(p["T1"], p["T3"], p["gamma"], p["cp"], p["p1"],
                             p["eta_c"], p["eta_t"], p["perdida_presion_combustor"], relaciones=relaciones)
        muestras = [referencia_fisica(p, ideal=True, rp=float(r)) for r in relaciones]
        eta = np.array([m["rendimiento"] * 100 if m["viable"] else np.nan for m in muestras])
        trabajo = np.array([m["trabajo_neto"] if m["viable"] else np.nan for m in muestras])
        rp_a = (p["T3"] / p["T1"]) ** (p["gamma"] / (2 * (p["gamma"] - 1)))
        w_a = referencia_fisica(p, ideal=True, rp=rp_a)["trabajo_neto"]
        with BytesIO() as destino, capturar_figuras() as figuras:
            main.guardar_grafica_rendimiento(p["gamma"], destino, b)
        eje = figuras[0].axes[0]
        np.testing.assert_array_equal(curva(eje, "Rendimiento ideal").get_xdata(), relaciones)
        np.testing.assert_allclose(curva(eje, "Rendimiento ideal").get_ydata(), eta, equal_nan=True, atol=3e-11)
        self.assertEqual(eje.get_xscale(), "log")
        self.assertIn("(%)", eje.get_ylabel())
        with BytesIO() as destino, capturar_figuras() as figuras:
            main.guardar_grafica_trabajo_neto(relaciones, b["ideal"]["trabajo_neto"], rp_a,
                                             w_a, destino, b["dominios"]["ideal"])
        eje = figuras[0].axes[0]
        np.testing.assert_allclose(curva(eje, "Trabajo específico neto").get_ydata(),
                                   trabajo, equal_nan=True, atol=3e-10)
        self.assertIn("[kJ/kg]", eje.get_ylabel())
        puntos = [c.get_offsets() for c in eje.collections if "Máximo analítico" in c.get_label()]
        self.assertEqual(len(puntos), 1)
        np.testing.assert_allclose(puntos[0], [[rp_a, w_a]], rtol=2e-12)
        self.assertTrue(np.isnan(trabajo[[0, -1]]).all())

    def test_graficas_comparativas_series_y_optimos_fisicos(self):
        p = BASE
        rel = np.array([1., 1.5, 3., 6., 10., 20., 50., 500.])
        args = (p["T1"], p["T3"], p["gamma"], p["cp"], p["p1"])
        eficiencias = (p["eta_c"], p["eta_t"], p["perdida_presion_combustor"])
        b = construir_barrido(*args, *eficiencias, relaciones=rel)
        o = {nombre: optimizar_trabajo_neto(*args, *(eficiencias if nombre == "noideal" else ()))
             for nombre in ("ideal", "noideal")}
        r = {"noideal": optimizar_rendimiento(*args, *eficiencias)}
        imagenes = {}
        try:
            with capturar_figuras() as figuras:
                main.guardar_comparaciones_ciclos(*args, *eficiencias, imagenes,
                                                  barrido=b, optimizaciones=o, estudio_rendimiento=r)
            self.assertEqual(set(imagenes), {"comparacion_ideal_noideal.png", "trabajo_neto_ideal_noideal.png"})
            self.assertEqual(len(figuras), 2)
            for fig in figuras:
                for eje in fig.axes:
                    es_eta = "Rendimiento" in eje.get_ylabel()
                    clave = "rendimiento" if es_eta else "trabajo_neto"
                    factor = 100 if es_eta else 1
                    self.assertIn("relación de presiones", eje.get_xlabel().lower())
                    for nombre in ("ideal", "noideal"):
                        series = [linea for linea in eje.lines if linea.get_label().startswith(f"Ciclo {nombre} ·")]
                        if not series:
                            continue  # El panel de detalle sólo contiene el ciclo no ideal.
                        valores = [referencia_fisica(p, ideal=nombre == "ideal", rp=float(rp)) for rp in rel]
                        esperado = [x[clave] * factor if x["viable"] else np.nan for x in valores]
                        np.testing.assert_allclose(series[0].get_xdata(), rel)
                        np.testing.assert_allclose(series[0].get_ydata(), esperado, equal_nan=True, atol=4e-10)
                        # La serie guarda toda la malla incluso fuera de la ventana visual del eje.
                        self.assertEqual(len(series[0].get_xdata()), len(rel))
                    for col in eje.collections:
                        etiqueta = col.get_label()
                        if etiqueta.startswith("Máximo "):
                            nombre = "noideal" if "noideal" in etiqueta else "ideal"
                            rp = o[nombre]["analitico"]["rp"]
                            ref = referencia_fisica(p, ideal=nombre == "ideal", rp=rp)
                            np.testing.assert_allclose(col.get_offsets(), [[rp, ref[clave] * factor]], rtol=3e-10)
                        elif etiqueta.startswith("B ·"):
                            rp = r["noideal"]["analitico"]["rp"]
                            ref = referencia_fisica(p, rp=rp)
                            np.testing.assert_allclose(col.get_offsets(), [[rp, ref[clave] * factor]], rtol=3e-10)
        finally:
            for imagen in imagenes.values():
                imagen.close()

    def test_compromiso_parametrico_y_ausencia_de_b_ficticio(self):
        p = BASE
        relaciones = np.array([1., 1.5, 3., 6., 10., 20., 50., 500.])
        args = (p["T1"], p["T3"], p["gamma"], p["cp"], p["p1"], p["eta_c"],
                p["eta_t"], p["perdida_presion_combustor"])
        b = construir_barrido(*args, relaciones=relaciones)
        a = optimizar_trabajo_neto(*args)["analitico"]
        opt_b = optimizar_rendimiento(*args)["analitico"]
        esperado = [referencia_fisica(p, rp=float(r)) for r in relaciones]
        wn = [m["trabajo_neto"] if m["viable"] else np.nan for m in esperado]
        eta = [100 * m["rendimiento"] if m["viable"] else np.nan for m in esperado]
        comparacion = {"punto_a": a, "punto_b": opt_b}
        with BytesIO() as destino, capturar_figuras() as figuras:
            main.guardar_grafica_compromiso(b, comparacion, destino)
        eje = figuras[0].axes[0]
        linea = curva(eje, "Ciclo no ideal ·")
        np.testing.assert_allclose(linea.get_xdata(), wn, equal_nan=True, atol=3e-10)
        np.testing.assert_allclose(linea.get_ydata(), eta, equal_nan=True, atol=3e-11)
        self.assertIn("[kJ/kg]", eje.get_xlabel())
        self.assertIn("[%]", eje.get_ylabel())
        for coleccion, rp in zip(eje.collections, (a["rp"], opt_b["rp"])):
            ref = referencia_fisica(p, rp=rp)
            np.testing.assert_allclose(coleccion.get_offsets(),
                                       [[ref["trabajo_neto"], ref["rendimiento"] * 100]], atol=3e-9)
        with BytesIO() as destino, capturar_figuras() as figuras:
            main.guardar_grafica_compromiso(b, {"punto_a": a, "punto_b": None}, destino)
        self.assertEqual(len(figuras[0].axes[0].collections), 1)
        self.assertTrue(any("no hay máximo interior" in t.get_text().lower()
                            for t in figuras[0].axes[0].texts))

    def test_dos_ejecuciones_html_kpi_png_sin_datos_residuales(self):
        historico = BASE.copy()
        hashes = []
        with tempfile.TemporaryDirectory() as temporal:
            for p in (BASE, ALTERNO):
                with self.subTest(perfil=p["T1"]):
                    with patch.object(main, "crear_informe_html", wraps=reporting.crear_informe_html) as crear:
                        with redirect_stdout(StringIO()):
                            ruta = main.main(Path(temporal), p)
                    datos = crear.call_args.args
                    kw = crear.call_args.kwargs
                    ideal, real = referencia_fisica(p, ideal=True), referencia_fisica(p)
                    self.comprobar_referencia(datos[1], ideal, ideal=True)
                    self.comprobar_referencia(datos[2], real)
                    self.assertEqual(datos[0], p)
                    self.assertEqual(kw["segunda_ley"]["T0"], 288.15)
                    for nombre, ref in (("ideal", ideal), ("noideal", real)):
                        fisica = kw["segunda_ley"]["modelos"][nombre]
                        np.testing.assert_allclose(fisica["temperaturas"], ref["temperaturas"], atol=3e-10)
                        np.testing.assert_allclose(fisica["presiones"], ref["presiones"], atol=3e-10)
                    pagina = ruta.read_text(encoding="utf-8")
                    meta, paneles = dashboard.separar_presentacion(pagina)
                    self.assertEqual(meta["parametros"], p)
                    self.assertEqual(meta["tipo"], "normal")
                    self.assertEqual(set(paneles), {"resultados", "optimizacion", "sensibilidad", "segunda_ley"})
                    self.assertIn(f"{p['T1']:.2f}", pagina)
                    self.assertIn(f"{p['T3']:.2f}", pagina)
                    self.assertIn(f"{p['perdida_presion_combustor'] * 100:.2f}", pagina)
                    for i, (T, presion) in enumerate(zip(ideal["temperaturas"], ideal["presiones"]), start=1):
                        self.assertIn(f"<td>{i}</td><td>{T:.2f}</td><td>{presion:.2f}</td>", pagina)
                    for i, (T, presion) in enumerate(zip(real["temperaturas"], real["presiones"]), start=1):
                        self.assertIn(f"<td>{i}</td><td>{T:.2f}</td><td>{presion:.2f}</td></tr>", pagina)
                    for ref in (ideal, real):
                        for clave in ("trabajo_compresor", "trabajo_turbina", "trabajo_neto", "calor_aportado"):
                            self.assertIn(f"{ref[clave]:.6f}", pagina)
                        self.assertIn(f"{ref['rendimiento'] * 100:.6f}", pagina)
                    for clave, valor in (("rp", p["relacion_presiones"]), ("trabajo", real["trabajo_neto"]),
                                         ("rendimiento", real["rendimiento"] * 100), ("calor", real["calor_aportado"])):
                        tarjeta = re.search(f'data-kpi="{clave}"(.*?)</article>', paneles["resultados"], re.S)
                        self.assertIsNotNone(tarjeta)
                        self.assertIn(f"{valor:.3f}", tarjeta[1])
                    a = kw["comparacion_criterios"]["punto_a"]
                    b = kw["comparacion_criterios"]["punto_b"]
                    for punto, kpi, magnitud, factor in (
                        (a, "max_trabajo", "trabajo_neto", 1),
                        (b, "max_rendimiento", "rendimiento", 100),
                    ):
                        if punto is not None:
                            independiente = referencia_fisica(p, rp=punto["rp"])
                            self.assertAlmostEqual(punto["ciclo"]["trabajo_neto"],
                                                   independiente["trabajo_neto"], delta=3e-9)
                            tarjeta = re.search(f'data-kpi="{kpi}"(.*?)</article>', paneles["resultados"], re.S)
                            self.assertIsNotNone(tarjeta)
                            self.assertIn(f"{independiente[magnitud] * factor:.3f}", tarjeta[1])
                    origenes = datos[7]
                    self.assertEqual(len(origenes), 7)
                    incrustadas = [b64decode(s, validate=True) for s in
                                   re.findall(r'data:image/png;base64,([A-Za-z0-9+/=]+)', pagina)]
                    self.assertCountEqual(incrustadas, origenes.values())
                    firmas = {k: sha256(v).hexdigest() for k, v in origenes.items()}
                    self.assertTrue(all(v.startswith(b"\x89PNG\r\n\x1a\n") for v in origenes.values()))
                    hashes.append(firmas)
            self.assertNotEqual(hashes[0]["diagrama_ts_brayton.png"], hashes[1]["diagrama_ts_brayton.png"])
            self.assertNotEqual(hashes[0]["comparacion_ideal_noideal.png"], hashes[1]["comparacion_ideal_noideal.png"])
        self.assertEqual(main.PARAMETROS_PREDETERMINADOS, historico)

    def test_formulario_porcentaje_y_no_motor_sin_informe(self):
        formulario = {k: str(v * 100 if k == "perdida_presion_combustor" else v)
                      for k, v in ALTERNO.items()}
        valores, errores = web_app.leer_parametros(formulario)
        self.assertEqual(errores, {})
        self.assertAlmostEqual(valores["perdida_presion_combustor"], .12)
        self.assertEqual(valores, ALTERNO)
        self.assertEqual(web_app.valores_formulario()["perdida_presion_combustor"], 5.0)
        p = {**BASE, "T3": 400., "relacion_presiones": 50.}
        ref = referencia_fisica(p)
        self.assertFalse(ref["viable"])
        self.assertIsNone(ref["rendimiento"])
        with tempfile.TemporaryDirectory() as temporal:
            destino = Path(temporal)
            with self.assertRaisesRegex(main.ErrorModelo, "Inviabilidad física"):
                main.main(destino, p)
            self.assertEqual(list(destino.iterdir()), [])
            with patch.dict(web_app.app.config, {"OUTPUTS_DIR": destino, "TESTING": True}):
                post = {k: str(v * 100 if k == "perdida_presion_combustor" else v)
                        for k, v in p.items()}
                respuesta = web_app.app.test_client().post("/", data=post)
                self.assertEqual(respuesta.status_code, 400)
                self.assertNotIn('data-kpi="trabajo"', respuesta.get_data(as_text=True))
                self.assertIn("Inviabilidad física", respuesta.get_data(as_text=True))
                self.assertEqual(list(destino.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
