"""Rendimiento térmico: máximo interior, supremo no alcanzado y dominio vacío.

API de Fase 3: métodos físicos independientes y comparación para main/HTML/Flask.
T [K], cp [J/(kg K)], p1 [kPa], energías [kJ/kg], rendimiento fracción.
Las evaluaciones físicas se delegan íntegramente a viabilidad.evaluar_punto.
"""

from math import exp, expm1, isfinite, log, log1p, sqrt
import numpy as np

from viabilidad import ErrorNumerico, calcular_dominios, evaluar_punto, validar_parametros


def estudiar_rendimiento_ideal(T1, T3, gamma, cp, p1):
    """Supremo ideal 1-T1/T3; la frontera NO es un punto motor alcanzable."""
    dominio = calcular_dominios(T1, T3, gamma, cp, p1)["ideal"]
    return {"estado": "supremo_no_alcanzado",
            "motivo": "Rendimiento ideal estrictamente creciente: no hay máximo interior.",
            "dominio": dominio, "candidato": None, "analitico": None,
            "numerico": None, "concordancia": None,
            "supremo": {"rendimiento": 1 - T1 / T3,
                        "rp_frontera": dominio["intervalo"][1], "alcanzado": False}}


def calcular_candidato_rendimiento(T1, T3, gamma, eta_c=1, eta_t=1, delta=0):
    """Raíz estacionaria estable; None sólo en el caso exactamente reversible.

    No comprueba dominio motor: un candidato matemático no implica máximo físico.
    B=1+eta_c*(theta-1), h=eta_c*eta_t*theta, H=h*k,
    S=(B-1)*(B-h)+h*(k-1); x*=B/(1+sqrt(S/H)).
    """
    validar_parametros(T1, T3, gamma, 1, 1, eta_c, eta_t, delta)
    if eta_c == eta_t == 1 and delta == 0:
        return None
    try:
        a = (gamma - 1) / gamma
        theta = T3 / T1
        B = 1 + eta_c * (theta - 1)
        h = eta_c * eta_t * theta
        k_menos_uno = expm1(-a * log1p(-delta))
        H = h * (1 + k_menos_uno)
        # S=H-A*B, pero esta suma positiva evita cancelación casi reversible.
        B_menos_h = (1 - eta_c) + eta_c * theta * (1 - eta_t)
        S = eta_c * (theta - 1) * B_menos_h + h * k_menos_uno
        if not all(isfinite(v) and v > 0 for v in (B, H, S)):
            raise ErrorNumerico("Coeficientes estacionarios no resolubles.")
        rp = exp((log(B) - log1p(sqrt(S / H))) / a)
    except (OverflowError, ZeroDivisionError) as error:
        raise ErrorNumerico("Candidato de rendimiento fuera del rango numérico.") from error
    if not isfinite(rp) or rp <= 0:
        raise ErrorNumerico("Candidato de rendimiento no representable.")
    return rp


def buscar_maximo_rendimiento_numerico(T1, T3, gamma, cp, p1,
                                       eta_c=1, eta_t=1, delta=0,
                                       muestras=257, tolerancia_log=1e-9,
                                       max_iteraciones=100):
    """Malla logarítmica + sección áurea, sin usar la raíz estacionaria.

    Recalcula dominios, acepta sólo motores y exige testigos admisibles de descenso
    a ambos lados. Una cima recortada por la banda numérica no se declara máximo.
    """
    validar_parametros(T1, T3, gamma, cp, p1, eta_c, eta_t, delta)
    if (isinstance(muestras, bool) or not isinstance(muestras, int)
            or not 5 <= muestras <= 4097):
        raise ValueError("muestras debe ser un entero entre 5 y 4097.")
    if (not isfinite(tolerancia_log) or not 0 < tolerancia_log < 1
            or isinstance(max_iteraciones, bool) or not isinstance(max_iteraciones, int)
            or not 1 <= max_iteraciones <= 1000):
        raise ValueError("Controles numéricos de rendimiento inválidos.")
    dominios = calcular_dominios(T1, T3, gamma, cp, p1, eta_c, eta_t, delta)
    if eta_c == eta_t == 1 and delta == 0:
        return estudiar_rendimiento_ideal(T1, T3, gamma, cp, p1)
    dominio = dominios["noideal"]
    if not dominio["intervalo"]:
        return {"estado": "sin_dominio", "motivo": "Dominio motor vacío.",
                "dominio": dominio, "rp": None, "ciclo": None, "supremo": None}
    lo, hi = dominio["intervalo"]
    ylo, yhi = log(lo), log(hi)
    margen = 8 * np.finfo(float).eps * max(1, abs(ylo), abs(yhi))
    izquierda = ylo + margen
    derecha = yhi - margen
    if not ylo < izquierda < derecha < yhi:
        raise ErrorNumerico("No se representa una ventana interior de rendimiento.")
    registros = {}

    def evaluar(y):
        rp = exp(float(y))
        if not lo < rp < hi:
            return -np.inf
        if rp not in registros:
            registros[rp] = evaluar_punto(T1, T3, gamma, cp, rp, p1, eta_c, eta_t, delta)
        punto = registros[rp]
        # No se divide por qin nulo, negativo o dentro de su banda cero.
        return punto["rendimiento"] if punto["viable"] else -np.inf

    malla = np.linspace(izquierda, derecha, muestras)
    rendimientos = np.array([evaluar(y) for y in malla])
    if not np.any(np.isfinite(rendimientos)):
        raise ErrorNumerico("La malla no encuentra puntos motores resolubles.")
    indice = int(np.argmax(rendimientos))
    if indice in (0, muestras - 1):
        raise ErrorNumerico("La malla no acota un máximo interior de rendimiento.")
    izquierda, derecha = float(malla[indice - 1]), float(malla[indice + 1])
    intervalo_busqueda = (exp(float(malla[0])), exp(float(malla[-1])))
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
        raise ErrorNumerico("La búsqueda de rendimiento no converge.")
    evaluar((izquierda + derecha) / 2)
    aceptados = [(rp, p) for rp, p in registros.items() if p["viable"]]
    rp, punto = max(aceptados, key=lambda par: par[1]["rendimiento"])
    margen_eta = 64 * np.finfo(float).eps
    descenso_izquierdo = any(r < rp and p["rendimiento"] < punto["rendimiento"] - margen_eta
                             for r, p in aceptados)
    descenso_derecho = any(r > rp and p["rendimiento"] < punto["rendimiento"] - margen_eta
                           for r, p in aceptados)
    if not descenso_izquierdo or not descenso_derecho:
        raise ErrorNumerico("No se resuelven ambos lados del máximo; no se acepta una frontera numérica.")
    return {"estado": "maximo_interior", "motivo": "Máximo motor numérico de rendimiento.",
            "dominio": dominio, "rp": rp, "ciclo": punto, "supremo": None,
            "intervalo_busqueda": intervalo_busqueda,
            "intervalo_final": (exp(izquierda), exp(derecha)),
            "paso_log_inicial": float(malla[1] - malla[0]),
            "tolerancia_log": tolerancia_log,
            "resolucion_rp": rp * max(tolerancia_log, 32 * sqrt(np.finfo(float).eps)),
            "muestras_iniciales": muestras, "evaluaciones": len(registros),
            "iteraciones": iteraciones}


def optimizar_rendimiento(T1, T3, gamma, cp, p1, eta_c=1, eta_t=1, delta=0):
    """Identifica solución, comprueba candidato motor y contrasta dos métodos.

    ErrorNumerico es una excepción explícita, nunca un máximo/supremo ficticio.
    """
    dominios = calcular_dominios(T1, T3, gamma, cp, p1, eta_c, eta_t, delta)
    if eta_c == eta_t == 1 and delta == 0:
        return estudiar_rendimiento_ideal(T1, T3, gamma, cp, p1)
    dominio = dominios["noideal"]
    if not dominio["intervalo"]:
        return {"estado": "sin_dominio", "motivo": "Dominio motor vacío: sin máximo de rendimiento.",
                "dominio": dominio, "candidato": None, "analitico": None,
                "numerico": None, "concordancia": None, "supremo": None}
    candidato = calcular_candidato_rendimiento(T1, T3, gamma, eta_c, eta_t, delta)
    lo, hi = dominio["intervalo"]
    if not lo < candidato < hi:
        raise ErrorNumerico("Candidato de rendimiento no resoluble en el interior motor.")
    punto = evaluar_punto(T1, T3, gamma, cp, candidato, p1, eta_c, eta_t, delta)
    if not punto["viable"]:
        raise ErrorNumerico("El máximo de rendimiento no supera las bandas numéricas de motor.")
    numerico = buscar_maximo_rendimiento_numerico(T1, T3, gamma, cp, p1, eta_c, eta_t, delta)
    diferencia_rp = abs(numerico["rp"] - candidato)
    diferencia_eta = abs(numerico["ciclo"]["rendimiento"] - punto["rendimiento"])
    tol_rp = 2e-6 * max(candidato, numerico["rp"])
    # Amplificación de redondeo en el cociente W/qin, especialmente cerca de qin=0.
    condicion = (cp / 1000 * T3) / min(punto["calor_aportado"], numerico["ciclo"]["calor_aportado"])
    tol_eta = max(1e-10, 64 * np.finfo(float).eps * condicion)
    if diferencia_rp > tol_rp or diferencia_eta > tol_eta:
        raise ErrorNumerico("No concuerdan los máximos analítico y numérico de rendimiento.")
    return {"estado": "maximo_interior", "motivo": "Único máximo interior motor de rendimiento.",
            "dominio": dominio, "candidato": candidato,
            "analitico": {"rp": candidato, "ciclo": punto}, "numerico": numerico,
            "supremo": None, "concordancia": {"diferencia_rp": diferencia_rp,
                "tolerancia_rp": tol_rp, "diferencia_rendimiento": diferencia_eta,
                "tolerancia_rendimiento": tol_eta, "condicion_cociente": condicion}}


def comparar_criterios(trabajo, rendimiento):
    """Compara B (máximo eta) con A (máximo W), sin recalcular física.

    Ganancia en puntos porcentuales; reducción relativa referida a W_A>0;
    diferencias rp y calor con signo B-A. Datos no disponibles quedan como None.
    """
    if trabajo["estado"] != "disponible" or rendimiento["estado"] != "maximo_interior":
        return {"estado": "no_disponible", "motivo": "No hay dos máximos motores alcanzados para comparar.",
                "punto_a": trabajo["analitico"], "punto_b": None,
                "diferencia_rp": None, "ganancia_rendimiento_pp": None,
                "reduccion_trabajo_porcentaje": None, "diferencia_calor": None}
    a, b = trabajo["analitico"], rendimiento["analitico"]
    ca, cb = a["ciclo"], b["ciclo"]
    return {"estado": "disponible", "motivo": "Diferencias B menos A; reducción de trabajo respecto a A.",
            "punto_a": a, "punto_b": b, "diferencia_rp": b["rp"] - a["rp"],
            "ganancia_rendimiento_pp": 100 * (cb["rendimiento"] - ca["rendimiento"]),
            "reduccion_trabajo_porcentaje": 100 * (ca["trabajo_neto"] - cb["trabajo_neto"]) / ca["trabajo_neto"],
            "diferencia_calor": cb["calor_aportado"] - ca["calor_aportado"]}
