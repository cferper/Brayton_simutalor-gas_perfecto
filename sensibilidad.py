"""OFAT sin estado entre ejecuciones; física y candidatos de las fases 1–3.

Temperaturas K, cp J/(kg K), p kPa, energías kJ/kg, eta y delta fracciones.
Las búsquedas independientes se reservan para extremos, centro y vecino de base.
"""

from datetime import datetime
from io import BytesIO
from math import isfinite
from pathlib import Path
from time import perf_counter

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from viabilidad import (ErrorNumerico, MOTIVOS, calcular_dominios, evaluar_punto,
                        validar_parametros)
from optimizacion import calcular_candidato_analitico, optimizar_trabajo_neto
from optimizacion_rendimiento import (calcular_candidato_rendimiento,
                                     optimizar_rendimiento)


PARAMETROS_ESTUDIO = {
    "T1": {"clave": "T1", "unidad": "K", "rango": (250., 350.)},
    "T3": {"clave": "T3", "unidad": "K", "rango": (800., 2000.)},
    "eta_c": {"clave": "eta_c", "unidad": "fracción", "rango": (.6, 1.)},
    "eta_t": {"clave": "eta_t", "unidad": "fracción", "rango": (.6, 1.)},
    "delta": {"clave": "perdida_presion_combustor", "unidad": "fracción", "rango": (0., .2)},
}
MAGNITUDES = ("trabajo_neto", "rendimiento", "calor_aportado", "rp")


def validar_configuracion(parametro, minimo, maximo, muestras):
    """Devuelve configuración normalizada; ValueError en rangos/controles inválidos."""
    if parametro not in PARAMETROS_ESTUDIO:
        raise ValueError("El parámetro debe ser T1, T3, eta_c, eta_t o delta.")
    if (isinstance(muestras, bool) or not isinstance(muestras, int)
            or not 3 <= muestras <= 201):
        raise ValueError("El número de muestras debe ser entero entre 3 y 201.")
    if not all(isfinite(v) for v in (minimo, maximo)) or not minimo < maximo:
        raise ValueError("Los extremos deben ser finitos y mínimo < máximo.")
    if parametro in ("T1", "T3") and minimo <= 0:
        raise ValueError("Las temperaturas se introducen en K y deben ser positivas.")
    if parametro in ("eta_c", "eta_t") and not 0 < minimo < maximo <= 1:
        raise ValueError("Las eficiencias son fracciones: 0 < mínimo < máximo ≤ 1.")
    if parametro == "delta" and not 0 <= minimo < maximo < 1:
        raise ValueError("delta es fracción, no porcentaje: 0 ≤ mínimo < máximo < 1.")
    return {"parametro": parametro, "minimo": float(minimo), "maximo": float(maximo),
            "muestras": muestras, "unidad": PARAMETROS_ESTUDIO[parametro]["unidad"]}


def generar_malla(configuracion):
    """Array lineal de n muestras, extremos incluidos, sin modificar configuración."""
    c = validar_configuracion(**{k: configuracion[k] for k in
                                ("parametro", "minimo", "maximo", "muestras")})
    valores = np.linspace(c["minimo"], c["maximo"], c["muestras"])
    if not np.all(np.diff(valores) > 0):
        raise ValueError("El intervalo no permite representar muestras distintas.")
    return valores


def construir_parametros(referencia, parametro, valor):
    """Copia OFAT de las nueve entradas; nunca modifica el diccionario original."""
    parametros = referencia.copy()
    parametros[PARAMETROS_ESTUDIO[parametro]["clave"]] = float(valor)
    return parametros


def argumentos_fisicos(parametros):
    """Tupla de ocho argumentos común a dominios y optimizadores; sin rp."""
    return tuple(parametros[k] for k in
                 ("T1", "T3", "gamma", "cp", "p1", "eta_c", "eta_t", "perdida_presion_combustor"))


def registro_escenario(estado, motivos=(), rp=None, ciclo=None, metodo="no aplicable", supremo=None,
                       verificacion=None):
    """Registro uniforme; magnitudes operativas None si falta un motor alcanzado."""
    disponible = estado == "disponible"
    return {"estado": estado, "motivos": tuple(motivos), "rp": rp if disponible else None,
            "ciclo": ciclo, "metodo": metodo, "supremo": supremo, "verificacion": verificacion,
            **{k: ciclo[k] if disponible else None for k in MAGNITUDES if k != "rp"}}


def evaluar_muestra(parametros, verificar=False):
    """Dominios frescos y R/A/B; sólo captura ErrorNumerico, no errores de programa.

    Candidatos analíticos de Fases 2/3 comprobados contra dominio y evaluación
    física en TODAS las muestras. verificar=True añade las búsquedas originales.
    """
    argumentos = argumentos_fisicos(parametros)
    resultado = {"parametros": parametros.copy(), "dominios": None, "motivo_dominio": None}
    if parametros["T3"] <= parametros["T1"]:
        motivo = "T3 debe ser mayor que T1: no hay ciclo motor admisible."
        resultado.update({s: registro_escenario("parametros_inviables", (motivo,)) for s in "RAB"})
        resultado["motivo_dominio"] = motivo
        return resultado
    T1, T3, gamma, cp, p1, ec, et, delta = argumentos
    try:
        punto = evaluar_punto(T1, T3, gamma, cp, parametros["relacion_presiones"], p1, ec, et, delta)
        resultado["R"] = registro_escenario(
            "disponible" if punto["viable"] else "inviable",
            tuple(MOTIVOS[m] for m in punto["motivos"]), parametros["relacion_presiones"],
            punto, "evaluación física a rp fija")
    except ErrorNumerico as error:
        resultado["R"] = registro_escenario("limite_numerico", (str(error),))
    try:
        resultado["dominios"] = calcular_dominios(*argumentos)
    except ErrorNumerico as error:
        resultado["motivo_dominio"] = str(error)
        resultado.update({s: registro_escenario("limite_numerico", (str(error),)) for s in "AB"})
        return resultado
    dominio = resultado["dominios"]["noideal"]
    for escenario, candidato, optimizador in (
            ("A", calcular_candidato_analitico, optimizar_trabajo_neto),
            ("B", calcular_candidato_rendimiento, optimizar_rendimiento)):
        if not dominio["intervalo"]:
            resultado[escenario] = registro_escenario("sin_dominio", ("Dominio motor vacío.",))
            continue
        if escenario == "B" and ec == et == 1 and delta == 0:
            estudio = optimizar_rendimiento(*argumentos)
            resultado[escenario] = registro_escenario("supremo_no_alcanzado",
                (estudio["motivo"],), supremo=estudio["supremo"])
            continue
        try:
            rp = candidato(T1, T3, gamma, ec, et, delta)
            lo, hi = dominio["intervalo"]
            if not lo < rp < hi:
                raise ErrorNumerico("Candidato no resoluble en el interior del dominio físico.")
            punto = evaluar_punto(T1, T3, gamma, cp, rp, p1, ec, et, delta)
            if not punto["viable"]:
                raise ErrorNumerico("El candidato no supera las bandas numéricas de viabilidad.")
            metodo = "analítico + dominio + evaluación física"
            contraste = None
            if verificar:
                estudio = optimizador(*argumentos)
                contraste = {"intervalo_busqueda": estudio["numerico"]["intervalo_busqueda"],
                             "intervalo_final": estudio["numerico"]["intervalo_final"],
                             "concordancia": estudio["concordancia"]}
                metodo += " + búsqueda numérica independiente"
            resultado[escenario] = registro_escenario("disponible", rp=rp, ciclo=punto, metodo=metodo,
                                                       verificacion=contraste)
        except ErrorNumerico as error:
            resultado[escenario] = registro_escenario("limite_numerico", (str(error),))
    return resultado


def calcular_sensibilidad_local(funcion, x, limites, escala=1.):
    """Derivada escalar y elasticidad mediante pasos h/h2; None indica no disponible.

    funcion(x) devuelve float o None. limites es el intervalo físico cerrado
    representable. Se exige estabilidad al reducir h y no se ocultan excepciones.
    """
    salida = {"derivada": None, "normalizada": None, "metodo": None,
              "paso": None, "error_estimado": None, "motivo": ""}
    y = funcion(x)
    if y is None or not isfinite(y):
        salida["motivo"] = "No existe un punto operativo resoluble en la referencia."
        return salida
    if abs(y) <= 1e-9 * max(abs(escala), np.finfo(float).tiny):
        salida["motivo"] = "Magnitud próxima a cero: cociente mal condicionado."
        return salida
    h = np.cbrt(np.finfo(float).eps) * max(abs(x), 1.)
    lo, hi = limites
    if x - h >= lo and x + h <= hi:
        metodo = "central"
        offsets, pesos = (-1, 1), (-.5, .5)
    elif x + 2 * h <= hi:
        metodo = "unilateral adelante de orden 2"
        offsets, pesos = (0, 1, 2), (-1.5, 2., -.5)
    elif x - 2 * h >= lo:
        metodo = "unilateral atrás de orden 2"
        offsets, pesos = (0, -1, -2), (1.5, -2., .5)
    else:
        salida["motivo"] = "No se resuelve un paso admisible."
        return salida
    derivadas = []
    for paso in (h, h / 2):
        valores = [funcion(x + o * paso) for o in offsets]
        if any(v is None or not isfinite(v) for v in valores):
            salida["motivo"] = "Cambio de disponibilidad/régimen o límite numérico en la perturbación."
            return salida
        derivadas.append(sum(p * v for p, v in zip(pesos, valores)) / paso)
    error = abs(derivadas[1] - derivadas[0])
    tolerancia = 1e-3 * abs(derivadas[1]) + 1e-7 * abs(escala) / max(abs(x), 1.)
    if error > tolerancia:
        salida["motivo"] = "Derivada inestable al reducir el paso: posible frontera o discontinuidad."
        return salida
    salida.update(derivada=derivadas[1], normalizada=x / y * derivadas[1] if x != 0 else None,
                  metodo=metodo, paso=h / 2, error_estimado=error,
                  motivo="x=0: elasticidad relativa no interpretable; se ofrece derivada absoluta." if x == 0 else "")
    return salida


def analizar_sensibilidad(referencia, parametro, minimo, maximo, muestras=41):
    """Estudio OFAT puro: configuración, registros, arrays, tendencias y coeficientes.

    Validación global ValueError; límites numéricos por muestra registrados.
    No escribe archivos ni modifica referencia; devuelve tiempo de cálculo en s.
    """
    inicio = perf_counter()
    configuracion = validar_configuracion(parametro, minimo, maximo, muestras)
    validar_parametros(*argumentos_fisicos(referencia))
    if not isfinite(referencia["relacion_presiones"]) or referencia["relacion_presiones"] <= 1:
        raise ValueError("La rp de referencia debe ser finita y mayor que 1.")
    valores = generar_malla(configuracion)
    clave = PARAMETROS_ESTUDIO[parametro]["clave"]
    x0 = referencia[clave]
    indices = {0, muestras // 2, muestras - 1, int(np.argmin(abs(valores - x0)))}
    registros = [evaluar_muestra(construir_parametros(referencia, parametro, x), i in indices)
                 for i, x in enumerate(valores)]
    curvas = {s: {k: np.array([r[s][k] if r[s][k] is not None else np.nan
                               for r in registros]) for k in MAGNITUDES} for s in "RAB"}
    limites = {"T1": (np.nextafter(0., 1.), np.nextafter(referencia["T3"], 0.)),
               "T3": (np.nextafter(referencia["T1"], np.inf), np.inf),
               "eta_c": (np.nextafter(0., 1.), 1.), "eta_t": (np.nextafter(0., 1.), 1.),
               "delta": (0., np.nextafter(1., 0.))}[parametro]
    cache = {}

    def evaluar_local(x):
        if x not in cache:
            cache[x] = evaluar_muestra(construir_parametros(referencia, parametro, x))
        return cache[x]

    locales = {}
    escalas = {"trabajo_neto": referencia["cp"] / 1000 * referencia["T3"],
               "calor_aportado": referencia["cp"] / 1000 * referencia["T3"],
               "rendimiento": 1., "rp": referencia["relacion_presiones"]}
    for s in "RAB":
        locales[s] = {}
        for k in MAGNITUDES:
            def magnitud(x):
                registro = evaluar_local(x)[s]
                # El cociente eta deja de ser fiable cerca de calor nulo.
                if (registro["estado"] != "disponible" or
                        registro["calor_aportado"] < 1e-7 * escalas["calor_aportado"]):
                    return None
                return registro[k]
            locales[s][k] = calcular_sensibilidad_local(magnitud, x0, limites, escalas[k])
    tendencias = []
    for s in "RAB":
        for k in ("trabajo_neto", "rendimiento"):
            y = curvas[s][k]
            validos = np.isfinite(y)
            segmentos = int(np.sum(validos & np.r_[True, ~validos[:-1]]))
            if validos.any():
                tendencias.append(f"{s} · {k}: {validos.sum()}/{muestras} disponibles; "
                    f"{segmentos} tramo(s); mínimo {y[validos].min():.6g}, máximo {y[validos].max():.6g} "
                    "(rendimiento en fracción). Extremos muestreados, sin ranking universal.")
            else:
                tendencias.append(f"{s} · {k}: ninguna muestra operativa disponible.")
    return {"referencia": referencia.copy(), "configuracion": configuracion, "valores": valores,
            "registros": registros, "curvas": curvas, "sensibilidades": locales,
            "referencia_local": evaluar_local(x0), "indices_verificacion": sorted(indices),
            "tendencias": tendencias, "segundos_calculo": perf_counter() - inicio}


def crear_graficas_sensibilidad(estudio):
    """Tres PNG 1350×900 en memoria; NaN corta curvas, symlog si escalas >100."""
    imagenes = {}
    configuracion = estudio["configuracion"]
    for k, unidad in (("trabajo_neto", "Trabajo neto [kJ/kg]"),
                      ("rendimiento", "Rendimiento [%]"), ("rp", "Relación de presiones [−]")):
        figura, ejes = plt.subplots(figsize=(9, 6))
        try:
            datos_operativos = []
            for s, estilo in (("R", "--"), ("A", "-"), ("B", ":")):
                y = estudio["curvas"][s][k] * (100 if k == "rendimiento" else 1)
                datos_operativos.append(y)
                ejes.plot(estudio["valores"], y, estilo,
                    marker="o" if s == "R" and k == "rp" else None, markersize=3,
                    label={"R": "R: puntos motores a rp fija", "A": "A: máximo trabajo",
                           "B": "B: máximo interior de rendimiento"}[s])
            # La consigna no es un resultado operativo: se identifica por separado.
            if k == "rp":
                ejes.plot(estudio["valores"],
                    np.full(len(estudio["valores"]), estudio["referencia"]["relacion_presiones"]),
                    color="0.5", linestyle="-.", linewidth=1, zorder=1,
                    label="Consigna rp de referencia (no indica viabilidad)")
            datos = np.concatenate([linea.get_ydata() for linea in ejes.lines])
            positivos = abs(datos[np.isfinite(datos) & (datos != 0)])
            if len(positivos) and positivos.max() / positivos.min() > 100:
                ejes.set_yscale("symlog", linthresh=float(positivos.min()))
                ejes.set_title("Escala simétrica logarítmica; huecos = no disponible")
            else:
                ejes.set_title("OFAT · Huecos = no disponible; supremos sin punto operativo")
            ejes.set_xlabel(f"{configuracion['parametro']} [{configuracion['unidad']}]")
            # Autoscale ignora los NaN y ocultaría el inicio inviable del barrido.
            ejes.set_xlim(configuracion["minimo"], configuracion["maximo"])
            ejes.set_ylabel(unidad)
            if not any(np.isfinite(y).any() for y in datos_operativos):
                ejes.text(.5, .5, "Ningún punto operativo disponible", ha="center",
                          transform=ejes.transAxes)
            ejes.grid(True, alpha=.3)
            ejes.legend(fontsize=8)
            figura.tight_layout()
            with BytesIO() as buffer:
                figura.savefig(buffer, format="png", dpi=150)
                imagenes[k] = buffer.getvalue()
        finally:
            plt.close(figura)
    return imagenes


def ejecutar_sensibilidad(carpeta_salida, parametros, parametro, minimo, maximo, muestras=41):
    """Orquesta cálculo→tres PNG→HTML→publicación compartida; devuelve Path."""
    from reporting import (crear_informe_sensibilidad_html, guardar_informe_html,
                           obtener_version_git)
    estudio = analizar_sensibilidad(parametros, parametro, minimo, maximo, muestras)
    imagenes = crear_graficas_sensibilidad(estudio)
    fecha = datetime.now().astimezone()
    version = obtener_version_git(Path(__file__).resolve().parent)
    contenido = crear_informe_sensibilidad_html(estudio, imagenes, fecha, version)
    return guardar_informe_html(contenido, carpeta_salida, fecha)
