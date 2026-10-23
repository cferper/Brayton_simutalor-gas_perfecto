
# Simulador educativo Brayton ideal y no ideal con informe HTML autocontenido.

from pathlib import Path
from datetime import datetime
from io import BytesIO

from viabilidad import (calcular_estados, calcular_energias, evaluar_punto, calcular_dominios,
                        construir_barrido, describir_inviabilidad, validar_parametros, ErrorNumerico)
from optimizacion import optimizar_trabajo_neto
from optimizacion_rendimiento import estudiar_rendimiento_ideal, optimizar_rendimiento, comparar_criterios
from reporting import crear_informe_html, guardar_informe_html, obtener_version_git
from segunda_ley import analizar_segunda_ley, validar_referencia
from math import isclose, isfinite, log

import numpy as np
import matplotlib

# Agg permite guardar la gráfica sin abrir ventanas ni utilizar Tkinter.
matplotlib.use("Agg")
import matplotlib.pyplot as plt


PARAMETROS_PREDETERMINADOS = {
    "T1": 288.15, "T3": 1600, "p1": 100, "relacion_presiones": 10,
    "cp": 1005, "gamma": 1.4, "eta_c": 0.85, "eta_t": 0.90,
    "perdida_presion_combustor": 0.05,  # Fracción: 5 %.
}


class ErrorModelo(ValueError):
    """El caso de referencia no pertenece al dominio motor."""


def calcular_rendimiento(gamma, relacion_presiones):
    # Comprobamos que los datos sean válidos para el ciclo Brayton ideal.
    if not isfinite(gamma) or gamma <= 1:
        raise ValueError("gamma debe ser mayor que 1.")
    if not isfinite(relacion_presiones) or relacion_presiones <= 1:
        raise ValueError("La relación de presiones debe ser mayor que 1.")

    # Devolvemos el rendimiento como una fracción, no como un porcentaje.
    return 1 - 1 / (relacion_presiones ** ((gamma - 1) / gamma))


def calcular_rendimientos(gamma, relaciones_presiones=(5, 10, 15, 20, 25)):
    # Reutilizamos el cálculo del ciclo y ordenamos las relaciones de menor a mayor.
    return [
        (relacion, calcular_rendimiento(gamma, relacion) * 100)
        for relacion in sorted(relaciones_presiones)
    ]


def calcular_temperaturas(T1, T3, gamma, relacion_presiones):
    # Reutilizamos las validaciones de gamma y de la relación de presiones.
    calcular_rendimiento(gamma, relacion_presiones)
    if not all(isfinite(T) and T > 0 for T in (T1, T3)):
        raise ValueError("T1 y T3 deben ser temperaturas absolutas positivas y finitas.")

    estados = calcular_estados(T1, T3, gamma, relacion_presiones, 1)
    temperaturas = estados["temperaturas"]
    if T3 <= temperaturas[1]:
        raise ValueError("T3 debe superar T2 para aportar calor y producir trabajo neto.")
    return temperaturas


def calcular_balance_energetico(T1, T2, T3, T4, cp):
    if not isfinite(cp) or cp <= 0:
        raise ValueError("cp debe ser positivo y finito, en J/(kg·K).")
    if not all(isfinite(T) and T > 0 for T in (T1, T2, T3, T4)):
        raise ValueError("Todas las temperaturas deben ser positivas y finitas.")
    if not (T2 > T1 and T3 > T2 and T3 > T4 and T4 > T1):
        raise ValueError("Las temperaturas deben permitir compresión, calentamiento, expansión y enfriamiento.")

    # cp·ΔT da J/kg; dividimos entre 1000 para obtener kJ/kg.
    # El trabajo del compresor se expresa como consumo positivo.
    energias = calcular_energias((T1, T2, T3, T4), cp)
    trabajo_compresor = energias["trabajo_compresor"]
    trabajo_turbina = energias["trabajo_turbina"]
    trabajo_neto = energias["trabajo_neto"]
    calor_aportado = energias["calor_aportado"]
    if not all(isfinite(valor) and valor > 0 for valor in (
        trabajo_compresor, trabajo_turbina, trabajo_neto, calor_aportado
    )):
        raise ValueError("Los trabajos y el calor deben ser finitos y positivos para un ciclo motor.")
    rendimiento_balance = trabajo_neto / calor_aportado
    if not 0 < rendimiento_balance < 1:
        raise ValueError("El rendimiento térmico debe estar entre 0 y 1.")
    return {
        "trabajo_compresor": trabajo_compresor,
        "trabajo_turbina": trabajo_turbina,
        "trabajo_neto": trabajo_neto,
        "calor_aportado": calor_aportado,
        "rendimiento": rendimiento_balance,
    }


def calcular_ciclo_ideal(T1, T3, gamma, cp, relacion_presiones, p1):
    temperaturas = calcular_temperaturas(T1, T3, gamma, relacion_presiones)
    _, presiones, _ = calcular_estados_pv(temperaturas, cp, gamma, relacion_presiones, p1)
    balance = calcular_balance_energetico(*temperaturas, cp)
    return {
        "temperaturas": temperaturas,
        "presiones": presiones,
        "T2s": temperaturas[1],
        "T4s": temperaturas[3],
        **balance,
        "back_work_ratio": balance["trabajo_compresor"] / balance["trabajo_turbina"],
    }


def calcular_ciclo_noideal(T1, T3, gamma, cp, relacion_presiones, p1,
                          eta_c, eta_t, perdida_presion_combustor):
    punto = evaluar_punto(T1, T3, gamma, cp, relacion_presiones, p1,
                          eta_c, eta_t, perdida_presion_combustor)
    if not punto["viable"]:
        dominios = calcular_dominios(T1, T3, gamma, cp, p1, eta_c, eta_t, perdida_presion_combustor)
        raise ErrorModelo(describir_inviabilidad(punto, dominios["noideal"]))
    return punto


def comprobar_comparacion_ciclos(ideal, noideal, eta_c, eta_t, perdida_presion_combustor):
    if eta_c < 1:
        if not (noideal["temperaturas"][1] > noideal["T2s"]
                and noideal["trabajo_compresor"] > ideal["trabajo_compresor"]):
            raise ValueError("El compresor irreversible debe consumir más trabajo y tener T2 > T2s.")
    if eta_t < 1 and not noideal["temperaturas"][3] > noideal["T4s"]:
        raise ValueError("La turbina irreversible debe tener T4 > T4s.")
    if (eta_t < 1 or perdida_presion_combustor > 0) and not (
        noideal["trabajo_turbina"] < ideal["trabajo_turbina"]
    ):
        raise ValueError("La turbina no ideal debe producir menos trabajo que la ideal.")
    if eta_c < 1 or eta_t < 1 or perdida_presion_combustor > 0:
        if not noideal["rendimiento"] < ideal["rendimiento"]:
            raise ValueError("El rendimiento no ideal debe ser menor que el ideal.")
    else:
        # Límite reversible: ambos modelos deben dar los mismos estados y balances.
        if not np.allclose(noideal["temperaturas"], ideal["temperaturas"], rtol=1e-9, atol=1e-12):
            raise ValueError("El límite reversible no reproduce las temperaturas ideales.")
        for clave in ("trabajo_compresor", "trabajo_turbina", "trabajo_neto",
                      "calor_aportado", "rendimiento", "back_work_ratio"):
            if not isclose(noideal[clave], ideal[clave], rel_tol=1e-9, abs_tol=1e-12):
                raise ValueError("El límite reversible no reproduce el balance ideal.")


def marcar_dominio(ejes, dominio, etiqueta, color):
    # Líneas discontinuas: fronteras físicas; banda tenue: intervalo motor abierto.
    ejes.set_xscale("log")
    if dominio["intervalo"]:
        inferior, superior = dominio["intervalo"]
        vista = ejes.get_xlim()
        for frontera in (inferior, superior):
            if vista[0] <= frontera <= vista[1]:
                ejes.axvline(frontera, color=color, linestyle="--", alpha=.7)
        ejes.axvspan(max(inferior, vista[0]), min(superior, vista[1]),
                    color=color, alpha=.05, label=f"Dominio motor {etiqueta}")
        ejes.set_xlim(vista)
    else:
        ejes.plot([], [], color=color, linestyle="--", label=f"{etiqueta}: dominio vacío")


def guardar_comparaciones_ciclos(T1, T3, gamma, cp, p1, eta_c, eta_t,
                                perdida_presion_combustor, imagenes, barrido=None,
                                optimizaciones=None, estudio_rendimiento=None):
    if barrido is None:
        barrido = construir_barrido(T1, T3, gamma, cp, p1, eta_c, eta_t,
                                    perdida_presion_combustor)
    dominio_real = barrido["dominios"]["noideal"]["intervalo"]
    vista = barrido["intervalo_visual"]
    detalle = False
    if dominio_real:
        amplitud_real = log(dominio_real[1] / dominio_real[0])
        w_ideal = max((p["trabajo_neto"] for p in barrido["ideal"]["puntos"] if p["viable"]), default=0)
        w_real = max((p["trabajo_neto"] for p in barrido["noideal"]["puntos"] if p["viable"]), default=0)
        detalle = log(vista[1] / vista[0]) > 4 * amplitud_real or (w_real > 0 and w_ideal > 20 * w_real)
    for clave, factor, eje_y, titulo, archivo in (
        ("rendimiento", 100, "Rendimiento térmico [%]", "Rendimiento: ciclo ideal y no ideal",
         "comparacion_ideal_noideal.png"),
        ("trabajo_neto", 1, "Trabajo específico neto [kJ/kg]", "Trabajo neto: ciclo ideal y no ideal",
         "trabajo_neto_ideal_noideal.png"),
    ):
        if detalle:
            figura, paneles = plt.subplots(2, 1, figsize=(9, 6))
        else:
            figura, ejes = plt.subplots(figsize=(9, 6))
            paneles = [ejes]
        for indice, ejes in enumerate(paneles):
            nombres = (("ideal", "tab:blue"), ("noideal", "tab:orange")) if indice == 0 else (("noideal", "tab:orange"),)
            for nombre, color in nombres:
                ejes.plot(barrido["relaciones"], barrido[nombre][clave] * factor,
                          color=color, label=f"Ciclo {nombre} · interior motor")
            if indice == 0:
                ejes.set_xlim(vista)
            else:
                lo, hi = dominio_real
                margen = .04 * log(hi / lo)
                ejes.set_xlim(max(1, lo / np.exp(margen)), min(vista[1], hi * np.exp(margen)))
            for nombre, color in nombres:
                marcar_dominio(ejes, barrido["dominios"][nombre], nombre, color)
                if optimizaciones is not None:
                    resultado = optimizaciones[nombre]
                    if resultado["estado"] == "disponible":
                        rp = resultado["analitico"]["rp"]
                        valor = resultado["analitico"]["ciclo"][clave] * factor
                        ejes.scatter([rp], [valor], color=color, marker="o" if nombre == "ideal" else "D",
                                     zorder=5, label=f"Máximo {nombre} de trabajo ({'A' if nombre == 'noideal' else 'ideal'}): rp={rp:.6g}; valor={valor:.5g}")
            if estudio_rendimiento is not None:
                r = estudio_rendimiento["noideal"]
                if r["estado"] == "maximo_interior":
                    b = r["analitico"]
                    ejes.scatter([b["rp"]], [b["ciclo"][clave] * factor], color="tab:green",
                                 marker="*", s=110, zorder=6,
                                 label=f"B · Máximo rendimiento noideal: rp={b['rp']:.6g}")
                else:
                    ejes.text(.02, .94, "Sin punto B: " + r["estado"].replace("_", " "),
                              transform=ejes.transAxes, fontsize=8)
            ejes.set_title(titulo if indice == 0 else "Detalle del dominio no ideal (escalas propias)", fontsize=10)
            ejes.set_xlabel("Relación de presiones (escala logarítmica)", fontsize=9)
            ejes.set_ylabel(eje_y, fontsize=9)
            ejes.grid(True)
            ejes.legend(fontsize=6 if detalle else 7)
        figura.tight_layout()
        imagenes[archivo] = BytesIO()
        figura.savefig(imagenes[archivo], format="png", dpi=150)
        plt.close(figura)


def guardar_grafica_compromiso(barrido, comparacion, ruta):
    """Curva paramétrica no ideal W-eta en orden de rp, con NaN y puntos A/B."""
    figura, ejes = plt.subplots(figsize=(9, 6))
    real = barrido["noideal"]
    ejes.plot(real["trabajo_neto"], real["rendimiento"] * 100, color="tab:orange",
              label="Ciclo no ideal · rp variable, sólo interior motor")
    for clave, simbolo, color, etiqueta in (("punto_a", "D", "tab:orange", "A · Máximo trabajo"),
                                           ("punto_b", "*", "tab:green", "B · Máximo rendimiento")):
        punto = comparacion[clave]
        if punto is not None:
            ciclo = punto["ciclo"]
            ejes.scatter([ciclo["trabajo_neto"]], [ciclo["rendimiento"] * 100],
                         marker=simbolo, color=color, s=110, zorder=5,
                         label=f"{etiqueta}: rp={punto['rp']:.6g}")
    if comparacion["punto_b"] is None:
        ejes.text(.03, .92, "Punto B no disponible: no hay máximo interior alcanzado.", transform=ejes.transAxes, fontsize=9)
    ejes.set_title("Compromiso trabajo–rendimiento del ciclo no ideal")
    ejes.set_xlabel("Trabajo específico neto [kJ/kg]")
    ejes.set_ylabel("Rendimiento térmico [%]")
    ejes.grid(True)
    ejes.legend(fontsize=8)
    figura.text(.5, .015, "rp es el parámetro de la curva; no toda la curva es una frontera de Pareto.",
                ha="center", fontsize=9)
    figura.tight_layout(rect=(0, .035, 1, 1))
    figura.savefig(ruta, format="png", dpi=150)
    plt.close(figura)


def calcular_trabajo_neto(T1, T3, gamma, cp, relacion_presiones):
    # Reutilizamos el cálculo de estados y las validaciones del ciclo motor.
    temperaturas = calcular_temperaturas(T1, T3, gamma, relacion_presiones)
    return calcular_balance_energetico(*temperaturas, cp)["trabajo_neto"]


def calcular_relacion_optima(T1, T3, gamma):
    calcular_rendimiento(gamma, 2)  # Validación de gamma.
    if not all(isfinite(T) and T > 0 for T in (T1, T3)) or T3 <= T1:
        raise ValueError("Se requieren temperaturas finitas con T3 > T1 > 0.")
    # Con x = rp**((gamma-1)/gamma), dw_neto/dx = cp·(T3/x² - T1).
    # La segunda derivada es negativa: x = sqrt(T3/T1) es un máximo.
    relacion_optima = (T3 / T1) ** (gamma / (2 * (gamma - 1)))
    if not isfinite(relacion_optima) or relacion_optima <= 1:
        raise ValueError("La relación óptima debe ser finita y mayor que 1.")
    return relacion_optima


def buscar_optimo_numerico(T1, T3, gamma, cp):
    # Sólo se busca el máximo IDEAL; malla interior adaptada al dominio.
    limite = calcular_dominios(T1, T3, gamma, cp, 1)["ideal"]["intervalo"][1]
    inferior = min(1.01, 1 + .01 * (limite - 1))
    superior = min(limite - 1e-8 * (limite - 1), max(50, 1.25 * calcular_relacion_optima(T1, T3, gamma)))
    if not 1 < inferior < superior < limite:
        raise ErrorNumerico("No se puede resolver una malla interior para el óptimo ideal.")
    relaciones = np.linspace(inferior, superior, 100001)
    trabajos = np.array([
        calcular_trabajo_neto(T1, T3, gamma, cp, relacion)
        for relacion in relaciones
    ])
    indice_maximo = int(np.argmax(trabajos))
    return relaciones, trabajos, indice_maximo


def guardar_grafica_trabajo_neto(relaciones, trabajos, rp_optima, trabajo_maximo, ruta, dominio=None):
    figura, ejes = plt.subplots(figsize=(9, 6))
    ejes.plot(relaciones, trabajos, label="Trabajo específico neto")
    if min(relaciones) <= rp_optima <= max(relaciones):
        ejes.scatter([rp_optima], [trabajo_maximo], color="red", s=70, zorder=5,
                     label="Máximo analítico (verificado numéricamente)")
        ejes.annotate(f"rp = {rp_optima:.4f}\nTrabajo máximo = {trabajo_maximo:.2f} kJ/kg",
                      xy=(rp_optima, trabajo_maximo), xytext=(15, -55),
                      textcoords="offset points", arrowprops={"arrowstyle": "->"})
    else:
        ejes.text(.03, .93, f"Máximo ideal rp={rp_optima:.6g}, fuera de la vista",
                  transform=ejes.transAxes)
    if dominio is not None:
        ejes.set_xlim(float(min(relaciones)), float(max(relaciones)))
        marcar_dominio(ejes, dominio, "ideal", "tab:blue")
    ejes.set_title("Trabajo neto del ciclo Brayton ideal")
    ejes.set_xlabel("Relación de presiones")
    ejes.set_ylabel("Trabajo específico neto [kJ/kg]")
    ejes.grid(True)
    ejes.legend(loc="lower right")
    figura.tight_layout()
    figura.savefig(ruta, format="png", dpi=150)
    plt.close(figura)


def calcular_entropias(T1, T2, T3, T4, cp):
    # Aplicamos las mismas validaciones físicas que al balance energético.
    calcular_balance_energetico(T1, T2, T3, T4, cp)
    cp_kj = cp / 1000  # kJ/(kg·K).
    incremento_23 = cp_kj * log(T3 / T2)
    incremento_14 = cp_kj * log(T4 / T1)
    # Comparamos sin redondear: la tolerancia es menor que la precisión impresa.
    if not isclose(incremento_23, incremento_14, rel_tol=1e-9, abs_tol=1e-12):
        raise ValueError("Los incrementos de entropía 2→3 y 1→4 no coinciden: el ciclo no es isentrópico.")
    s1 = 0.0  # Referencia arbitraria de entropía específica relativa.
    s2 = s1  # Compresión isentrópica.
    s3 = s2 + incremento_23
    s4 = s3  # Expansión isentrópica.
    return s1, s2, s3, s4


def guardar_diagrama_ts(temperaturas, entropias, cp, ruta):
    T1, T2, T3, T4 = temperaturas
    # Validamos también las entradas cuando se llama a esta función por separado.
    esperadas = calcular_entropias(T1, T2, T3, T4, cp)
    if len(entropias) != 4 or not all(
        isclose(s, esperado, rel_tol=1e-9, abs_tol=1e-12)
        for s, esperado in zip(entropias, esperadas)
    ):
        raise ValueError("Las entropías deben corresponder al ciclo con s1 = 0.")
    s1, s2, s3, s4 = entropias
    cp_kj = cp / 1000

    # En una isóbara, s(T) = s_inicial + cp·ln(T/T_inicial).
    # Muestreamos las curvas en el sentido de recorrido del ciclo.
    temperaturas_23 = np.linspace(T2, T3, 100)
    entropias_23 = s2 + cp_kj * np.log(temperaturas_23 / T2)
    temperaturas_41 = np.linspace(T4, T1, 100)
    entropias_41 = s4 + cp_kj * np.log(temperaturas_41 / T4)
    procesos = (
        ([s1, s2], [T1, T2], "1→2: compresión isentrópica"),
        (entropias_23, temperaturas_23, "2→3: calentamiento a presión constante"),
        ([s3, s4], [T3, T4], "3→4: expansión isentrópica"),
        (entropias_41, temperaturas_41, "4→1: enfriamiento a presión constante"),
    )
    figura, ejes = plt.subplots(figsize=(9, 6))
    for valores_s, valores_T, etiqueta in procesos:
        linea, = ejes.plot(valores_s, valores_T, label=etiqueta)
        # Una flecha sobre cada proceso indica el sentido del ciclo.
        if len(valores_s) == 2:
            inicio = (valores_s[0], valores_T[0] + 0.4 * (valores_T[1] - valores_T[0]))
            fin = (valores_s[1], valores_T[0] + 0.6 * (valores_T[1] - valores_T[0]))
        else:
            inicio = (valores_s[40], valores_T[40])
            fin = (valores_s[60], valores_T[60])
        ejes.annotate("", xy=fin, xytext=inicio,
                      arrowprops={"arrowstyle": "->", "color": linea.get_color(), "lw": 2})

    ejes.scatter(entropias, temperaturas, color="black", zorder=5)
    for estado, s, T in zip((1, 2, 3, 4), entropias, temperaturas):
        ejes.annotate(str(estado), (s, T), xytext=(8, 8), textcoords="offset points")
    ejes.set_title("Diagrama T-s del ciclo Brayton ideal")
    ejes.set_xlabel("Entropía específica relativa [kJ/(kg·K)]")
    ejes.set_ylabel("Temperatura [K]")
    ejes.grid(True)
    ejes.margins(x=0.12, y=0.12)
    ejes.legend(loc="upper left", fontsize=8)
    figura.tight_layout()
    figura.savefig(ruta, format="png", dpi=150)
    plt.close(figura)


def comprobar_estados_pv(temperaturas, presiones, volumenes, R, gamma):
    # Las presiones se reciben en kPa; Pv = RT requiere Pa si R está en J/(kg·K).
    if not all(len(valores) == 4 for valores in (temperaturas, presiones, volumenes)):
        raise ValueError("Se requieren cuatro temperaturas, presiones y volúmenes.")
    if not isfinite(R) or R <= 0 or not isfinite(gamma) or gamma <= 1:
        raise ValueError("Se requieren R positivo y gamma mayor que 1, ambos finitos.")
    if not all(isfinite(valor) and valor > 0
               for valores in (temperaturas, presiones, volumenes) for valor in valores):
        raise ValueError("Las temperaturas, presiones y volúmenes deben ser positivos y finitos.")
    for estado, (T, p, v) in enumerate(zip(temperaturas, presiones, volumenes), start=1):
        if not isclose(p * 1000 * v, R * T, rel_tol=1e-9, abs_tol=1e-12):
            raise ValueError(f"El estado {estado} no cumple la ecuación del gas ideal.")
    p1, p2, p3, p4 = presiones
    v1, v2, v3, v4 = volumenes
    if not (p2 > p1 and isclose(p2, p3, rel_tol=1e-9)
            and isclose(p4, p1, rel_tol=1e-9)):
        raise ValueError("Las presiones deben corresponder a las dos isóbaras del ciclo Brayton.")
    # Usar kPa en ambos extremos no altera la comprobación de Pv^gamma constante.
    for inicio, fin in ((0, 1), (2, 3)):
        if not isclose(presiones[inicio] * volumenes[inicio] ** gamma,
                       presiones[fin] * volumenes[fin] ** gamma, rel_tol=1e-9):
            raise ValueError("Los estados no cumplen Pv^gamma constante en las isentrópicas.")
    if not (v2 < v1 and v3 > v2 and v4 > v3 and v1 < v4):
        raise ValueError("Los volúmenes no permiten el recorrido del ciclo motor.")


def calcular_estados_pv(temperaturas, cp, gamma, relacion_presiones, p1):
    calcular_rendimiento(gamma, relacion_presiones)
    # Validamos las temperaturas, cp y la coherencia de las etapas isentrópicas.
    calcular_entropias(*temperaturas, cp)
    if not isfinite(p1) or p1 <= 0:
        raise ValueError("p1 debe ser positiva y finita, en kPa.")
    R = cp * (1 - 1 / gamma)  # J/(kg·K), pues R = cp - cv y cv = cp/gamma.
    presiones = (p1, relacion_presiones * p1, relacion_presiones * p1, p1)
    volumenes = tuple(R * T / (p * 1000) for T, p in zip(temperaturas, presiones))
    comprobar_estados_pv(temperaturas, presiones, volumenes, R, gamma)
    return R, presiones, volumenes


def guardar_diagrama_pv(temperaturas, presiones, volumenes, R, gamma, ruta):
    comprobar_estados_pv(temperaturas, presiones, volumenes, R, gamma)
    p1, p2, p3, p4 = presiones
    v1, v2, v3, v4 = volumenes
    # Muestreamos en el sentido del ciclo: las isentrópicas son curvas, no rectas.
    volumenes_12 = np.linspace(v1, v2, 200)
    presiones_12 = p1 * (v1 / volumenes_12) ** gamma
    volumenes_34 = np.linspace(v3, v4, 200)
    presiones_34 = p3 * (v3 / volumenes_34) ** gamma
    procesos = (
        (volumenes_12, presiones_12, "1→2: compresión isentrópica"),
        (np.linspace(v2, v3, 200), np.full(200, p2), "2→3: calentamiento a presión constante"),
        (volumenes_34, presiones_34, "3→4: expansión isentrópica"),
        (np.linspace(v4, v1, 200), np.full(200, p4), "4→1: enfriamiento a presión constante"),
    )
    figura, ejes = plt.subplots(figsize=(9, 6))
    for valores_v, valores_p, etiqueta in procesos:
        linea, = ejes.plot(valores_v, valores_p, label=etiqueta)
        ejes.annotate("", xy=(valores_v[110], valores_p[110]),
                      xytext=(valores_v[90], valores_p[90]),
                      arrowprops={"arrowstyle": "->", "color": linea.get_color(), "lw": 2})
    ejes.scatter(volumenes, presiones, color="black", zorder=5)
    for estado, v, p in zip((1, 2, 3, 4), volumenes, presiones):
        ejes.annotate(str(estado), (v, p), xytext=(8, 8), textcoords="offset points")
    ejes.set_title("Diagrama P-v del ciclo Brayton ideal")
    ejes.set_xlabel("Volumen específico [m³/kg]")
    ejes.set_ylabel("Presión [kPa]")
    ejes.grid(True)
    ejes.margins(x=0.08, y=0.12)
    ejes.legend(loc="upper right", fontsize=8)
    figura.tight_layout()
    figura.savefig(ruta, format="png", dpi=150)
    plt.close(figura)


def guardar_grafica_rendimiento(gamma, ruta, barrido=None):
    if barrido is None:
        p = PARAMETROS_PREDETERMINADOS
        barrido = construir_barrido(p["T1"], p["T3"], gamma, p["cp"], p["p1"])
    figura, ejes = plt.subplots(figsize=(9, 6))
    ejes.plot(barrido["relaciones"], barrido["ideal"]["rendimiento"] * 100,
              label="Rendimiento ideal · interior motor")
    ejes.set_xlim(barrido["intervalo_visual"])
    marcar_dominio(ejes, barrido["dominios"]["ideal"], "ideal", "tab:blue")
    ejes.set_title(f"Rendimiento térmico del ciclo Brayton ideal (γ = {gamma})")
    ejes.set_xlabel("Relación de presiones p₂/p₁ (escala logarítmica)")
    ejes.set_ylabel("Rendimiento térmico (%)")
    ejes.grid(True)
    ejes.legend(fontsize=8)
    figura.tight_layout()
    figura.savefig(ruta, format="png", dpi=150)
    plt.close(figura)


def main(carpeta_salida=None, parametros=None, *, T0=288.15):
    T0 = validar_referencia(T0)
    fecha = datetime.now().astimezone()
    version = obtener_version_git(Path(__file__).resolve().parent)
    # Copia por ejecución: el formulario no modifica los valores predeterminados.
    configuracion = PARAMETROS_PREDETERMINADOS.copy()
    if parametros is not None:
        if any(clave not in configuracion for clave in parametros):
            raise ValueError("La configuración contiene parámetros desconocidos.")
        configuracion.update(parametros)
    parametros = configuracion
    T1 = parametros["T1"]
    T3 = parametros["T3"]
    p1 = parametros["p1"]
    relacion_presiones = parametros["relacion_presiones"]
    cp = parametros["cp"]
    gamma = parametros["gamma"]
    eta_c = parametros["eta_c"]
    eta_t = parametros["eta_t"]
    perdida_presion_combustor = parametros["perdida_presion_combustor"]
    comprobaciones = []
    # Entradas inválidas, inviabilidad física y fallo numérico son situaciones distintas.
    try:
        validar_parametros(T1, T3, gamma, cp, p1, eta_c, eta_t, perdida_presion_combustor)
        if not isfinite(relacion_presiones) or relacion_presiones <= 0:
            raise ValueError("rp debe ser positivo y finito.")
    except ValueError as error:
        # Sólo validación de entradas: los errores de cálculo no se silencian.
        raise ErrorModelo(f"Parámetros no admisibles: {error}") from error
    dominios = calcular_dominios(T1, T3, gamma, cp, p1, eta_c, eta_t, perdida_presion_combustor)
    referencia = {
        "ideal": evaluar_punto(T1, T3, gamma, cp, relacion_presiones, p1),
        "noideal": evaluar_punto(T1, T3, gamma, cp, relacion_presiones, p1,
                                eta_c, eta_t, perdida_presion_combustor),
    }
    fallos = [f"{nombre}: {describir_inviabilidad(punto, dominios[nombre])}"
              for nombre, punto in referencia.items() if not punto["viable"]]
    if fallos:
        raise ErrorModelo("Inviabilidad física: los ciclos seleccionados no son admisibles como motores. "
                          + " ".join(fallos))
    optimizaciones = {
        "ideal": optimizar_trabajo_neto(T1, T3, gamma, cp, p1, dominio=dominios["ideal"]),
        "noideal": optimizar_trabajo_neto(T1, T3, gamma, cp, p1, eta_c, eta_t,
                                         perdida_presion_combustor, dominios["noideal"]),
    }
    estudio_rendimiento = {
        "ideal": estudiar_rendimiento_ideal(T1, T3, gamma, cp, p1),
        "noideal": optimizar_rendimiento(T1, T3, gamma, cp, p1, eta_c, eta_t,
                                         perdida_presion_combustor),
    }
    comparacion_criterios = comparar_criterios(optimizaciones["noideal"], estudio_rendimiento["noideal"])
    comprobaciones.append("Rendimiento: supremo ideal no alcanzado; clasificación no ideal y concordancia de métodos verificadas cuando existe máximo interior.")
    puntos_interes = [relacion_presiones] + [r["analitico"]["rp"] for r in optimizaciones.values()
                                           if r["estado"] == "disponible"]
    if estudio_rendimiento["noideal"]["estado"] == "maximo_interior":
        puntos_interes.append(estudio_rendimiento["noideal"]["analitico"]["rp"])
    barrido = construir_barrido(T1, T3, gamma, cp, p1, eta_c, eta_t,
                                perdida_presion_combustor, dominios=dominios,
                                puntos_interes=puntos_interes)
    for ideal, real in zip(barrido["ideal"]["puntos"], barrido["noideal"]["puntos"]):
        if ideal["viable"] and real["viable"]:
            comprobar_comparacion_ciclos(ideal, real, eta_c, eta_t, perdida_presion_combustor)
    rendimiento = calcular_rendimiento(gamma, relacion_presiones)
    T1, T2, T3, T4 = calcular_temperaturas(T1, T3, gamma, relacion_presiones)
    balance = calcular_balance_energetico(T1, T2, T3, T4, cp)
    s1, s2, s3, s4 = calcular_entropias(T1, T2, T3, T4, cp)
    R, presiones, volumenes = calcular_estados_pv((T1, T2, T3, T4), cp, gamma, relacion_presiones, p1)
    comprobaciones.append("Entradas y estados ideales positivos y finitos; balance de ciclo motor con calor y trabajo neto positivos y rendimiento entre 0 y 1.")
    comprobaciones.append("Incrementos de entropía 2→3 y 1→4 coincidentes, con rel_tol=1e-9 y abs_tol=1e-12.")
    comprobaciones.append("Cuatro estados ideales coherentes con Pv=RT, dos isóbaras y Pv^gamma constante en las isentrópicas; recorrido motor de volúmenes.")
    if not isclose(balance["rendimiento"], rendimiento, rel_tol=1e-9, abs_tol=1e-12):
        raise ValueError("El rendimiento del balance no coincide con la fórmula del ciclo ideal.")
    comprobaciones.append("Rendimiento ideal por fórmula y por balance coincidentes, con rel_tol=1e-9 y abs_tol=1e-12.")

    # Ambos óptimos se recalculan con los dominios de esta ejecución.
    estudio_ideal = optimizaciones["ideal"]
    rp_optima_analitica = estudio_ideal["analitico"]["rp"]
    rp_optima_numerica = estudio_ideal["numerico"]["rp"]
    paso_busqueda = estudio_ideal["numerico"]["resolucion_rp"]
    temperaturas_optimas = estudio_ideal["analitico"]["ciclo"]["temperaturas"]
    trabajo_maximo = estudio_ideal["analitico"]["ciclo"]["trabajo_neto"]
    rendimiento_optimo = estudio_ideal["analitico"]["ciclo"]["rendimiento"]
    comprobaciones.append("Máximos ideal y no ideal: candidatos interiores motores, concordancia analítica-numérica verificada con tolerancias explícitas; intervalos recalculados con los parámetros actuales.")

    ciclo_ideal = calcular_ciclo_ideal(T1, T3, gamma, cp, relacion_presiones, p1)
    ciclo_noideal = calcular_ciclo_noideal(T1, T3, gamma, cp, relacion_presiones, p1,
                                         eta_c, eta_t, perdida_presion_combustor)
    comprobar_comparacion_ciclos(ciclo_ideal, ciclo_noideal, eta_c, eta_t, perdida_presion_combustor)
    comprobaciones.append("Eficiencias, pérdida de presión y estados no ideales admisibles; comparación de temperaturas de referencia, trabajos y rendimiento según las pérdidas introducidas.")
    ciclo_limite_ideal = calcular_ciclo_noideal(T1, T3, gamma, cp, relacion_presiones, p1, 1, 1, 0)
    comprobar_comparacion_ciclos(ciclo_ideal, ciclo_limite_ideal, 1, 1, 0)
    comprobaciones.append("Límite reversible: temperaturas y balances recuperan el ideal con eta_c=eta_t=1 y pérdida=0, dentro de las tolerancias establecidas.")
    # Cada buffer contiene una gráfica nueva; no se leen los PNG históricos.
    imagenes = {
        nombre: BytesIO() for nombre in (
            "rendimiento_brayton.png", "diagrama_ts_brayton.png",
            "diagrama_pv_brayton.png", "trabajo_neto_vs_rp.png",
        )
    }
    try:
        guardar_grafica_rendimiento(gamma, imagenes["rendimiento_brayton.png"], barrido)
        guardar_diagrama_ts((T1, T2, T3, T4), (s1, s2, s3, s4), cp, imagenes["diagrama_ts_brayton.png"])
        guardar_diagrama_pv((T1, T2, T3, T4), presiones, volumenes, R, gamma, imagenes["diagrama_pv_brayton.png"])
        guardar_grafica_trabajo_neto(barrido["relaciones"], barrido["ideal"]["trabajo_neto"],
                                    rp_optima_analitica, trabajo_maximo, imagenes["trabajo_neto_vs_rp.png"], dominios["ideal"])
        guardar_comparaciones_ciclos(T1, T3, gamma, cp, p1, eta_c, eta_t,
                                    perdida_presion_combustor, imagenes, barrido, optimizaciones, estudio_rendimiento)
        imagenes["compromiso_trabajo_rendimiento.png"] = BytesIO()
        guardar_grafica_compromiso(barrido, comparacion_criterios, imagenes["compromiso_trabajo_rendimiento.png"])
        comprobaciones.append("Barrido clasificado por condiciones simultáneas; curvas sólo en puntos motores y comparación comprobada donde ambos modelos son viables.")
        detalles_ideal = {
            "R": R, "volumenes": volumenes, "entropias": (s1, s2, s3, s4),
            "rendimiento_formula": rendimiento,
            "incremento_23": s3 - s2, "incremento_14": cp / 1000 * log(T4 / T1),
        }
        optimo = {
            "rp_analitica": rp_optima_analitica, "rp_numerica": rp_optima_numerica,
            "intervalo_busqueda": estudio_ideal["numerico"]["intervalo_busqueda"],
            "paso": paso_busqueda, "trabajo_analitico": trabajo_maximo,
            "trabajo_numerico": estudio_ideal["numerico"]["ciclo"]["trabajo_neto"],
            "temperaturas": temperaturas_optimas, "rendimiento": rendimiento_optimo,
        }
        contenido = crear_informe_html(
            parametros, ciclo_ideal, ciclo_noideal, detalles_ideal, optimo,
            [(rp, eta if evaluar_punto(T1, T3, gamma, cp, rp, p1)["viable"] else None)
             for rp, eta in calcular_rendimientos(gamma)], comprobaciones,
            {nombre: buffer.getvalue() for nombre, buffer in imagenes.items()}, fecha, version, barrido, optimizaciones,
            estudio_rendimiento=estudio_rendimiento, comparacion_criterios=comparacion_criterios,
            segunda_ley=analizar_segunda_ley(referencia, cp, gamma, T0),
        )
    finally:
        for buffer in imagenes.values():
            buffer.close()
        plt.close("all")
    if carpeta_salida is None:
        carpeta_salida = Path(__file__).resolve().parent / "outputs"
    ruta_informe = guardar_informe_html(contenido, carpeta_salida, fecha)
    print("Ejecución completada.")
    print(f"Informe HTML: {ruta_informe.resolve()}")
    print(f"Gráficas incorporadas: {len(imagenes)}")
    return ruta_informe


if __name__ == "__main__":
    main()
