"""Estados, clasificación motor y fronteras del modelo de propiedades constantes.

Las temperaturas se expresan en K, presiones en kPa, cp en J/(kg K)
y energías específicas en kJ/kg. La optimización se separa en optimizacion.py.
"""

from math import isfinite, log
import numpy as np

TOL_REL = 1e-10
MOTIVOS = {
    "compresion": "compresión no positiva (rp <= 1)",
    "expansion": "sin expansión disponible (p3 <= p4)",
    "calor_aportado": "calor aportado no positivo (T3 <= T2)",
    "trabajo_neto": "trabajo neto no positivo (wt <= wc)",
}


class ErrorNumerico(ArithmeticError):
    """Los parámetros son admisibles, pero el cálculo no se puede resolver."""


def validar_parametros(T1, T3, gamma, cp, p1, eta_c=1, eta_t=1, delta=0):
    """Valida entradas matemáticas, sin imponer funcionamiento motor."""
    if not all(isfinite(v) for v in (T1, T3, gamma, cp, p1, eta_c, eta_t, delta)):
        raise ValueError("Todos los parámetros deben ser finitos.")
    if not T3 > T1 > 0:
        raise ValueError("Se requieren temperaturas con T3 > T1 > 0 K.")
    if gamma <= 1 or cp <= 0 or p1 <= 0:
        raise ValueError("Se requieren gamma > 1, cp > 0 y p1 > 0.")
    if not (0 < eta_c <= 1 and 0 < eta_t <= 1 and 0 <= delta < 1):
        raise ValueError("Se requieren 0 < eta_c, eta_t <= 1 y 0 <= delta < 1.")


def calcular_estados(T1, T3, gamma, rp, p1, eta_c=1, eta_t=1, delta=0):
    """Evalúa las ecuaciones existentes incluso fuera del dominio motor."""
    validar_parametros(T1, T3, gamma, 1, p1, eta_c, eta_t, delta)
    if not isfinite(rp) or rp <= 0:
        raise ValueError("rp debe ser positivo y finito.")
    try:
        a = (gamma - 1) / gamma
        T2s = T1 * rp**a
        p2 = p1 * rp
        p3 = p2 * (1 - delta)
        T4s = T3 * (p1 / p3)**a
        T2 = T1 + (T2s - T1) / eta_c
        T4 = T3 - eta_t * (T3 - T4s)
    except (OverflowError, ZeroDivisionError) as error:
        raise ErrorNumerico("Estados fuera del rango numérico representable.") from error
    if not all(isfinite(v) and v > 0 for v in (T1, T2, T3, T4, p1, p2, p3, T2s, T4s)):
        raise ErrorNumerico("Estados no representables como valores positivos finitos.")
    return {"temperaturas": (T1, T2, T3, T4), "presiones": (p1, p2, p3, p1),
            "T2s": T2s, "T4s": T4s}


def calcular_energias(temperaturas, cp):
    """Balance cp ΔT con signo, sin exigir motor ni dividir entre qin."""
    if not isfinite(cp) or cp <= 0:
        raise ValueError("cp debe ser positivo y finito.")
    T1, T2, T3, T4 = temperaturas
    if not all(isfinite(T) and T > 0 for T in temperaturas):
        raise ValueError("Se requieren cuatro temperaturas positivas y finitas.")
    wc = cp * (T2 - T1) / 1000
    wt = cp * (T3 - T4) / 1000
    valores = {"trabajo_compresor": wc, "trabajo_turbina": wt,
               "trabajo_neto": wt - wc, "calor_aportado": cp * (T3 - T2) / 1000}
    if not all(isfinite(v) for v in valores.values()):
        raise ErrorNumerico("Balance energético fuera del rango numérico.")
    return valores


def evaluar_punto(T1, T3, gamma, cp, rp, p1, eta_c=1, eta_t=1, delta=0,
                  tolerancia=TOL_REL):
    """Devuelve estados, energías y TODOS los motivos; inviabilidad no lanza error."""
    validar_parametros(T1, T3, gamma, cp, p1, eta_c, eta_t, delta)
    if not isfinite(tolerancia) or not 0 <= tolerancia < 1:
        raise ValueError("La tolerancia relativa debe estar en [0, 1).")
    estados = calcular_estados(T1, T3, gamma, rp, p1, eta_c, eta_t, delta)
    energias = calcular_energias(estados["temperaturas"], cp)
    p3 = estados["presiones"][2]
    escala = max(abs(energias["trabajo_compresor"]), abs(energias["trabajo_turbina"]),
                 cp / 1000 * max(T1, T3))
    if not isfinite(escala):
        raise ErrorNumerico("Escala energética no representable para la tolerancia.")
    margenes = {"compresion": rp - 1, "expansion": p3 - p1,
                "calor_aportado": energias["calor_aportado"],
                "trabajo_neto": energias["trabajo_neto"]}
    tolerancias = {"compresion": tolerancia * max(rp, 1),
                   "expansion": tolerancia * max(p3, p1),
                   "calor_aportado": tolerancia * escala,
                   "trabajo_neto": tolerancia * escala}
    motivos = tuple(c for c in margenes if margenes[c] <= tolerancias[c])
    fronteras = tuple(c for c in margenes if abs(margenes[c]) <= tolerancias[c])
    viable = not motivos
    return {**estados, **energias, "viable": viable, "motivos": motivos,
            "fronteras": fronteras, "margenes": margenes, "tolerancias": tolerancias,
            "rendimiento": energias["trabajo_neto"] / energias["calor_aportado"] if viable else None,
            "back_work_ratio": (energias["trabajo_compresor"] / energias["trabajo_turbina"]
                                if viable else None)}


def bisectar_raiz(funcion, inferior, superior, tolerancia=1e-12, iteraciones=100):
    """Raíz acotada por cambio de signo; tolerancia relativa en la abscisa."""
    if not (isfinite(inferior) and isfinite(superior) and inferior <= superior
            and isfinite(tolerancia) and 0 < tolerancia < 1 and iteraciones > 0):
        raise ValueError("Intervalo o controles de bisección inválidos.")
    fi, fs = funcion(inferior), funcion(superior)
    if not all(isfinite(v) for v in (fi, fs)):
        raise ErrorNumerico("Función no finita en la bisección.")
    if fi == 0:
        return inferior
    if fs == 0:
        return superior
    if (fi > 0) == (fs > 0):
        raise ValueError("La bisección requiere un cambio de signo.")
    for _ in range(iteraciones):
        medio = inferior + (superior - inferior) / 2
        fm = funcion(medio)
        if not isfinite(fm):
            raise ErrorNumerico("Función no finita en la bisección.")
        if fm == 0 or superior - inferior <= tolerancia * max(abs(medio), 1):
            return medio
        if (fm > 0) == (fi > 0):
            inferior, fi = medio, fm
        else:
            superior = medio
    raise ErrorNumerico("La bisección no converge con los controles indicados.")


def calcular_dominios(T1, T3, gamma, cp, p1, eta_c=1, eta_t=1, delta=0):
    """Fronteras abiertas: intersección de expansión, calor y Q(x)<0.

    x=rp**a, h=(T3/T1)*eta_c*eta_t, k=(1-delta)**(-a).
    Q=(x-1)(x-h)+h(k-1) es cuadrática convexa: su región negativa
    es un intervalo o vacía. Intersectar intervalos no crea tramos separados.
    """
    validar_parametros(T1, T3, gamma, cp, p1, eta_c, eta_t, delta)
    a = (gamma - 1) / gamma
    theta = T3 / T1
    try:
        ideal_superior = theta**(1 / a)
        expansion = 1 / (1 - delta)
        calor = (1 + eta_c * (theta - 1))**(1 / a)
        k = (1 - delta)**(-a)
        h = theta * eta_c * eta_t
        discriminante = (h - 1)**2 - 4 * h * (k - 1)
        if not all(isfinite(v) for v in (theta, k, h, discriminante)):
            raise ErrorNumerico("Cuadrática del dominio fuera del rango numérico.")
        limites_trabajo = ()
        intervalo = ()
        if discriminante > 0:
            # El vértice está entre las dos raíces; Q(vértice)<0.
            centro = (1 + h) / 2
            def Q(x):
                return (x - 1) * (x - h) + h * (k - 1)
            # Q(0)=hk>0; Q(1+h)=hk>0. No es una optimización.
            baja = bisectar_raiz(Q, 0, centro)
            alta = bisectar_raiz(Q, centro, 1 + h)
            limites_trabajo = (baja**(1 / a), alta**(1 / a))
            inferior = max(1, expansion, limites_trabajo[0])
            superior = min(calor, limites_trabajo[1])
            # Si h<=1, Q(x)>=0 para x>=k>=1. Evita un falso
            # intervalo diminuto por el redondeo de la raíz x=1.
            if h > 1 and inferior < superior:
                intervalo = (inferior, superior)
    except (OverflowError, ZeroDivisionError) as error:
        raise ErrorNumerico("Fronteras fuera del rango numérico representable.") from error
    if not all(isfinite(v) and v > 0 for v in
               (ideal_superior, expansion, calor, *limites_trabajo)):
        raise ErrorNumerico("Las fronteras no son representables.")
    if ideal_superior <= 1:
        raise ErrorNumerico("El dominio ideal es menor que la resolución numérica.")
    return {"ideal": {"intervalo": (1, ideal_superior), "expansion": 1,
                      "calor": ideal_superior, "trabajo": (1, ideal_superior)},
            "noideal": {"intervalo": intervalo, "expansion": expansion, "calor": calor,
                        "trabajo": limites_trabajo, "discriminante": discriminante},
            "tolerancia_puntos": TOL_REL, "tolerancia_biseccion": 1e-12}


def describir_inviabilidad(punto, dominio):
    """Texto con motivos simultáneos y límites físicos, en rp adimensional."""
    intervalo = dominio["intervalo"]
    limites = (f"Intervalo motor abierto: {intervalo[0]:.10g} < rp < {intervalo[1]:.10g}."
               if intervalo else "No existe intervalo motor para esta combinación.")
    motivos = "; ".join(MOTIVOS[c] for c in punto["motivos"])
    return (motivos or "Punto motor viable") + ". " + limites + (
        " Las fronteras y su banda de tolerancia numérica se excluyen del interior motor.")


def construir_barrido(T1, T3, gamma, cp, p1, eta_c=1, eta_t=1, delta=0,
                      relaciones=None, dominios=None, puntos_interes=()):
    """Malla acotada y curvas con NaN en TODOS los puntos excluidos."""
    if dominios is None:
        dominios = calcular_dominios(T1, T3, gamma, cp, p1, eta_c, eta_t, delta)
    if relaciones is None:
        limite = dominios["ideal"]["intervalo"][1]
        # Ventana completa: no se recorta una frontera física por una cota fija.
        superior = limite * 1.05 if limite < np.finfo(float).max / 1.05 else limite
        muestras = list(np.geomspace(1, superior, 500)) + list(np.linspace(1, superior, 500))
        for nombre in ("ideal", "noideal"):
            dominio = dominios[nombre]
            for frontera in (dominio["expansion"], dominio["calor"], *dominio["trabajo"]):
                muestras.extend(frontera * factor for factor in (1 - 1e-6, 1, 1 + 1e-6)
                                if 1 <= frontera * factor <= superior)
            if dominio["intervalo"]:
                lo, hi = dominio["intervalo"]
                muestras.extend(np.linspace(lo, min(hi, superior), 101)
                                if lo < superior else [])
        for rp in puntos_interes:
            if not isfinite(rp) or not 1 <= rp <= superior:
                raise ValueError("Un punto de interés debe ser finito y estar dentro de la vista.")
            radio_log = log(superior) * .015
            muestras.extend(np.geomspace(max(1, rp / np.exp(radio_log)),
                                         min(superior, rp * np.exp(radio_log)), 17))
            muestras.append(rp)
        relaciones = np.unique(muestras)
    relaciones = np.asarray(relaciones, dtype=float)
    if relaciones.ndim != 1 or len(relaciones) < 2 or not np.all(np.isfinite(relaciones)):
        raise ValueError("Se requiere una malla unidimensional finita con al menos dos puntos.")
    if np.any(relaciones <= 0) or np.any(np.diff(relaciones) <= 0):
        raise ValueError("Las relaciones deben ser positivas y estrictamente crecientes.")
    resultado = {"relaciones": relaciones, "dominios": dominios,
                 "intervalo_visual": (float(relaciones[0]), float(relaciones[-1]))}
    for nombre, eficiencias in (("ideal", (1, 1, 0)), ("noideal", (eta_c, eta_t, delta))):
        puntos = [evaluar_punto(T1, T3, gamma, cp, float(rp), p1, *eficiencias)
                  for rp in relaciones]
        mascara = np.array([p["viable"] for p in puntos], dtype=bool)
        resultado[nombre] = {"puntos": puntos, "viable": mascara,
            "motivos": [p["motivos"] for p in puntos],
            "rendimiento": np.array([p["rendimiento"] if p["viable"] else np.nan for p in puntos]),
            "trabajo_neto": np.array([p["trabajo_neto"] if p["viable"] else np.nan for p in puntos])}
    return resultado
