"""Máximo de trabajo específico con dominios de Fase 1, sin cambiar la física.

T en K, cp en J/(kg K), p en kPa, trabajos en kJ/kg; rp adimensional.
La búsqueda numérica no utiliza el candidato analítico para elegir su intervalo.
"""

from math import exp, isfinite, log, sqrt
import numpy as np

from viabilidad import (ErrorNumerico, calcular_dominios, evaluar_punto,
                        validar_parametros)


def calcular_candidato_analitico(T1, T3, gamma, eta_c=1, eta_t=1, delta=0):
    """Punto estacionario matemático; NO asegura dominio motor no vacío."""
    validar_parametros(T1, T3, gamma, 1, 1, eta_c, eta_t, delta)
    a = (gamma - 1) / gamma
    exponente = (log(T3) - log(T1) + log(eta_c) + log(eta_t)
                 - a * log(1 - delta)) / (2 * a)
    try:
        candidato = exp(exponente)
    except OverflowError as error:
        raise ErrorNumerico("Candidato estacionario fuera del rango numérico.") from error
    if not isfinite(candidato) or candidato <= 0:
        raise ErrorNumerico("Candidato estacionario no representable.")
    return candidato


def buscar_maximo_numerico(T1, T3, gamma, cp, p1, eta_c=1, eta_t=1, delta=0,
                           dominio=None, muestras=257, tolerancia_log=1e-9,
                           max_iteraciones=100):
    """Malla logarítmica y sección áurea; acepta sólo puntos motores interiores.

    La concavidad en log(rp) permite refinar sin depender del óptimo analítico.
    Devuelve None si el dominio físico es vacío y ErrorNumerico si no es resoluble.
    """
    validar_parametros(T1, T3, gamma, cp, p1, eta_c, eta_t, delta)
    if not isinstance(muestras, int) or muestras < 5 or muestras > 4097:
        raise ValueError("muestras debe ser un entero entre 5 y 4097.")
    if (not isfinite(tolerancia_log) or not 0 < tolerancia_log < 1
            or not isinstance(max_iteraciones, int) or not 1 <= max_iteraciones <= 1000):
        raise ValueError("Controles numéricos de búsqueda inválidos.")
    if dominio is None:
        dominio = calcular_dominios(T1, T3, gamma, cp, p1, eta_c, eta_t, delta)["noideal"]
    if not dominio["intervalo"]:
        return None
    lo, hi = dominio["intervalo"]
    ylo, yhi = log(lo), log(hi)
    margen = (yhi - ylo) * 1e-6
    izquierda, derecha = ylo + margen, yhi - margen
    if not ylo < izquierda < derecha < yhi:
        raise ErrorNumerico("Dominio demasiado estrecho para construir una búsqueda interior.")
    registros = {}

    def evaluar(y):
        rp = exp(float(y))
        if not lo < rp < hi:
            raise ErrorNumerico("Una muestra de búsqueda no es interior al dominio físico.")
        if rp not in registros:
            registros[rp] = evaluar_punto(T1, T3, gamma, cp, rp, p1, eta_c, eta_t, delta)
        # El trabajo con signo guía el refinamiento; la aceptación exige viable=True.
        return registros[rp]["trabajo_neto"]

    malla = np.linspace(izquierda, derecha, muestras)
    trabajos = np.array([evaluar(y) for y in malla])
    indice = int(np.argmax(trabajos))
    if indice in (0, muestras - 1):
        raise ErrorNumerico("La malla no acota un máximo interior resoluble.")
    izquierda, derecha = float(malla[indice - 1]), float(malla[indice + 1])
    paso_inicial = float(malla[1] - malla[0])
    razon = (sqrt(5) - 1) / 2
    c = derecha - razon * (derecha - izquierda)
    d = izquierda + razon * (derecha - izquierda)
    fc, fd = evaluar(c), evaluar(d)
    for iteraciones in range(1, max_iteraciones + 1):
        if derecha - izquierda <= tolerancia_log:
            break
        if fc < fd:
            izquierda, c, fc = c, d, fd
            d = izquierda + razon * (derecha - izquierda)
            fd = evaluar(d)
        else:
            derecha, d, fd = d, c, fc
            c = derecha - razon * (derecha - izquierda)
            fc = evaluar(c)
    else:
        raise ErrorNumerico("La búsqueda no converge dentro del máximo de iteraciones.")
    evaluar((izquierda + derecha) / 2)
    aceptados = [(rp, p) for rp, p in registros.items() if p["viable"]]
    if not aceptados:
        raise ErrorNumerico("El máximo matemático no supera la banda numérica de viabilidad.")
    rp, punto = max(aceptados, key=lambda par: par[1]["trabajo_neto"])
    # Cerca del máximo el trabajo es plano: el ancho final no garantiza igual
    # precisión en rp. Se informa también una escala conservadora de redondeo.
    resolucion_relativa = max(tolerancia_log, 32 * sqrt(np.finfo(float).eps))
    return {"rp": rp, "ciclo": punto, "intervalo_fisico": (lo, hi),
            "intervalo_busqueda": (exp(float(malla[0])), exp(float(malla[-1]))),
            "intervalo_final": (exp(izquierda), exp(derecha)),
            "paso_log_inicial": paso_inicial, "tolerancia_log": tolerancia_log,
            "resolucion_rp": rp * resolucion_relativa,
            "evaluaciones": len(registros), "iteraciones": iteraciones,
            "muestras_iniciales": muestras}


def optimizar_trabajo_neto(T1, T3, gamma, cp, p1, eta_c=1, eta_t=1, delta=0,
                          dominio=None):
    """Compara máximo analítico/numérico y evalúa estados en el óptimo motor."""
    if dominio is None:
        dominio = calcular_dominios(T1, T3, gamma, cp, p1, eta_c, eta_t, delta)["noideal"]
    else:
        validar_parametros(T1, T3, gamma, cp, p1, eta_c, eta_t, delta)
    candidato = calcular_candidato_analitico(T1, T3, gamma, eta_c, eta_t, delta)
    if not dominio["intervalo"]:
        return {"estado": "sin_dominio", "motivo": "Dominio motor vacío: no existe un máximo motor admisible.",
                "candidato": candidato, "analitico": None, "numerico": None,
                "dominio": dominio, "concordancia": None}
    lo, hi = dominio["intervalo"]
    if not lo < candidato < hi:
        raise ErrorNumerico("El candidato no se resuelve en el interior del dominio calculado.")
    punto = evaluar_punto(T1, T3, gamma, cp, candidato, p1, eta_c, eta_t, delta)
    if not punto["viable"]:
        raise ErrorNumerico("El máximo matemático es demasiado próximo a cero para declararlo motor.")
    numerico = buscar_maximo_numerico(T1, T3, gamma, cp, p1, eta_c, eta_t, delta, dominio)
    diferencia_rp = abs(numerico["rp"] - candidato)
    diferencia_trabajo = abs(numerico["ciclo"]["trabajo_neto"] - punto["trabajo_neto"])
    tol_rp = max(candidato, numerico["rp"]) * 2e-6
    tol_trabajo = 1e-9 * max(abs(punto["trabajo_neto"]), cp / 1000 * T3)
    if diferencia_rp > tol_rp or diferencia_trabajo > tol_trabajo:
        raise ErrorNumerico("No concuerdan los máximos analítico y numérico con las tolerancias declaradas.")
    return {"estado": "disponible", "motivo": "Máximo de trabajo motor interior; no máximo de rendimiento.",
            "candidato": candidato, "analitico": {"rp": candidato, "ciclo": punto},
            "numerico": numerico, "dominio": dominio,
            "concordancia": {"diferencia_rp": diferencia_rp, "tolerancia_rp": tol_rp,
                             "diferencia_trabajo": diferencia_trabajo,
                             "tolerancia_trabajo": tol_trabajo}}
