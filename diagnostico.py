"""Diagnóstico del resultado concreto; no ejecuta las pruebas históricas.

T [K], p [kPa], cp [J/(kg K)], energía [kJ/kg], s [kJ/(kg K)].
Los contrastes verifican este modelo de propiedades constantes; no constituyen
validación experimental. Nunca se sustituyen las magnitudes recibidas por otras
recalculadas antes de compararlas.
"""

from math import exp, isfinite, log

from viabilidad import ErrorNumerico, evaluar_punto


def _finito(valor):
    """Escalar real -> bool; None/bool y valores no numéricos no son datos."""
    return (not isinstance(valor, bool) and isinstance(valor, (int, float))
            and isfinite(valor))


def _registro(identificador, nombre, grupo, relacion, unidad, explicacion,
              naturaleza="identidad", **datos):
    """Construye una fila dict; las magnitudes ausentes permanecen en None."""
    return {"id": identificador, "nombre": nombre, "grupo": grupo,
            "relacion": relacion, "valor": None, "referencia": None,
            "residuo": None, "residuo_relativo": None, "tolerancia": None,
            "unidad": unidad, "estado": "no_evaluable", "explicacion": explicacion,
            "motivo": "Faltan datos para esta relación.", "criterio": "No aplicable.",
            "naturaleza": naturaleza, "comparacion": "estado",
            **{k: str(v) if isinstance(v, (int, float)) and not isfinite(v) else v
               for k, v in datos.items()}}


def _comparar(identificador, nombre, grupo, relacion, valor, referencia, unidad,
              explicacion, *, atol=1e-12, rtol=1e-9, escala=None,
              naturaleza="identidad"):
    """Compara escalares con |v-ref| <= max(atol, rtol*escala), en su unidad."""
    fila = _registro(identificador, nombre, grupo, relacion, unidad, explicacion,
                     naturaleza, valor=valor, referencia=referencia, comparacion="igualdad")
    if ((valor is not None and not _finito(valor))
            or (referencia is not None and not _finito(referencia))):
        fila.update(estado="atencion", motivo="La magnitud o su referencia no es finita.")
        return fila
    if valor is None or referencia is None:
        return fila
    escala = max(abs(valor), abs(referencia)) if escala is None else escala
    if not _finito(escala) or escala < 0:
        fila.update(estado="atencion", motivo="La escala del contraste no es representable.")
        return fila
    tolerancia = max(atol, rtol * escala)
    residuo = abs(valor - referencia)
    cumple = isfinite(residuo) and residuo <= tolerancia
    fila.update(residuo=residuo if isfinite(residuo) else None,
                residuo_relativo=residuo / escala if escala > 0 and isfinite(residuo) else None,
                tolerancia=tolerancia, estado="cumple" if cumple else "atencion",
                criterio=f"|residuo| ≤ max(atol={atol:.6g}, rtol={rtol:.6g} × escala={escala:.6g}).",
                motivo="" if cumple else "El residuo supera la tolerancia numérica declarada.")
    return fila


def _margen(identificador, nombre, grupo, relacion, valor, limite, unidad,
             explicacion, *, estricto=True):
    """Comprueba margen > banda (o >= -banda para no negatividad)."""
    fila = _registro(identificador, nombre, grupo, relacion, unidad, explicacion,
                     "restricción", valor=valor, referencia=0., tolerancia=limite,
                     comparacion="mayor" if estricto else "no_negativo")
    if valor is None or limite is None:
        return fila
    if not _finito(valor) or not _finito(limite) or limite < 0:
        fila.update(estado="atencion", motivo="Margen o banda numérica no representable.")
        return fila
    cumple = valor > limite if estricto else valor >= -limite
    fila.update(residuo=max(0., limite - valor) if estricto else max(0., -valor),
                estado="cumple" if cumple else "atencion",
                criterio=(f"Margen > {limite:.6g}; frontera y banda excluidas."
                          if estricto else f"Valor ≥ −{limite:.6g}; banda de redondeo alrededor de cero."),
                motivo="" if cumple else ("Condición en la frontera o fuera del interior motor."
                                          if estricto else "Negatividad fuera de la banda de redondeo."))
    return fila


def diagnosticar_ciclo(parametros, ciclo, modelo="noideal", contexto="Caso actual",
                       segunda_ley=None, T0=None):
    """Dict de entradas + ciclo -> lista de diagnósticos con valores originales.

    ``modelo`` es ideal/noideal. ``segunda_ley`` es el registro DE UN MODELO
    de analizar_segunda_ley; ``T0`` [K] se suministra por separado. Datos ausentes
    producen no_evaluable; un resultado no finito produce atencion. No escribe
    archivos. Reutiliza las bandas guardadas; llama evaluar_punto sólo cuando
    faltan esas bandas y el ciclo sí conserva las cuatro energías originales.
    """
    if modelo not in ("ideal", "noideal"):
        raise ValueError("El modelo debe ser ideal o noideal.")
    grupo = f"{contexto} · {modelo}" if contexto else modelo
    filas = []
    ciclo = ciclo or {}
    temperaturas = ciclo.get("temperaturas")
    presiones = ciclo.get("presiones")
    t = tuple(temperaturas) if temperaturas is not None else ()
    p = tuple(presiones) if presiones is not None else ()
    cp, gamma = parametros.get("cp"), parametros.get("gamma")
    valido_t = len(t) == 4 and all(_finito(v) and v > 0 for v in t)
    valido_p = len(p) == 4 and all(_finito(v) and v > 0 for v in p)
    propiedades = _finito(cp) and cp > 0 and _finito(gamma) and gamma > 1
    ec = 1. if modelo == "ideal" else parametros.get("eta_c")
    et = 1. if modelo == "ideal" else parametros.get("eta_t")
    delta = 0. if modelo == "ideal" else parametros.get("perdida_presion_combustor")
    rp = parametros.get("relacion_presiones")
    escala_e = cp / 1000 * max(t) if valido_t and propiedades else None
    identidad = "Consistencia algebraica de magnitudes del mismo modelo; no es una prueba independiente ni una validación experimental."

    for clave, nombre, unidad, datos in (("temperaturas", "Estados: temperaturas absolutas", "K", t),
                                        ("presiones", "Estados: presiones absolutas", "kPa", p)):
        fila = _registro(clave, nombre, grupo, "Cuatro valores positivos y finitos", unidad,
                         "El modelo requiere temperaturas absolutas y presiones positivas.", "restricción")
        if datos:
            correcto = len(datos) == 4 and all(_finito(v) and v > 0 for v in datos)
            fila.update(estado="cumple" if correcto else "atencion", valor=min(datos) if correcto else None,
                        referencia=0., motivo="" if correcto else "Se requieren cuatro estados positivos y finitos.",
                        criterio="Positividad estricta y finitud; no se admite una temperatura o presión negativa por tolerancia.")
        filas.append(fila)

    for clave, nombre, indices in (("trabajo_compresor", "Trabajo del compresor y unidades", (1, 0)),
                                  ("trabajo_turbina", "Trabajo de la turbina y unidades", (2, 3)),
                                  ("calor_aportado", "Calor aportado y unidades", (2, 1))):
        referencia = cp / 1000 * (t[indices[0]] - t[indices[1]]) if valido_t and propiedades else None
        filas.append(_comparar(clave, nombre, grupo, "E = cp·ΔT/1000", ciclo.get(clave), referencia,
                               "kJ/kg", "cp se recibe en J/(kg·K); dividir entre 1000 convierte J/kg en kJ/kg. " + identidad,
                               atol=1e-10, escala=escala_e))
    wc, wt, wn, qin = (ciclo.get(k) for k in ("trabajo_compresor", "trabajo_turbina", "trabajo_neto", "calor_aportado"))
    trabajos = wt - wc if _finito(wt) and _finito(wc) else None
    filas.append(_comparar("balance_trabajos", "Balance de trabajos", grupo, "wn = wt − wc", wn,
                           trabajos, "kJ/kg", "Consumo del compresor positivo; producción de turbina positiva. " + identidad,
                           atol=1e-10, escala=escala_e))
    qout = cp / 1000 * (t[3] - t[0]) if valido_t and propiedades else None
    calor_neto = qin - qout if _finito(qin) and _finito(qout) else None
    filas.append(_comparar("balance_calores", "Primera Ley: calor y trabajo netos", grupo,
                           "wn = qin − qout; qout = cp(T4−T1)/1000", wn, calor_neto, "kJ/kg",
                           "qout es calor rechazado positivo, derivado aquí de los estados. " + identidad,
                           atol=1e-10, escala=escala_e))

    # Las bandas proceden de la API física existente; los márgenes usan los
    # valores RECIBIDOS para no ocultar una eventual discrepancia del resultado.
    nombres_margenes = ("compresion", "expansion", "calor_aportado", "trabajo_neto")
    guardadas = ciclo.get("tolerancias") or {}
    bandas = dict(guardadas) if all(_finito(guardadas.get(k)) and guardadas[k] >= 0
                                    for k in nombres_margenes) else {}
    claves = ("T1", "T3", "gamma", "cp", "relacion_presiones", "p1")
    if (not bandas and all(_finito(v) for v in (wc, wt, wn, qin))
            and all(_finito(parametros.get(k)) for k in claves) and all(_finito(v) for v in (ec, et, delta))):
        try:
            referencia_motor = evaluar_punto(*(parametros[k] for k in claves), ec, et, delta)
            bandas = referencia_motor["tolerancias"]
        except (ValueError, ErrorNumerico) as error:
            filas.append(_registro("limite_evaluacion", "Disponibilidad del evaluador físico", grupo,
                                   "Bandas motoras de evaluar_punto", "—",
                                   "Un fallo de cálculo no significa inviabilidad termodinámica.", "contraste",
                                   estado="atencion", motivo=str(error)))
    margenes = {"compresion": rp - 1 if _finito(rp) else None,
                "expansion": p[2] - p[3] if valido_p else None,
                "calor_aportado": qin, "trabajo_neto": wn}
    for clave, nombre, unidad in (("compresion", "Funcionamiento motor: compresión", "—"),
                                  ("expansion", "Funcionamiento motor: expansión", "kPa"),
                                  ("calor_aportado", "Funcionamiento motor: aporte de calor", "kJ/kg"),
                                  ("trabajo_neto", "Funcionamiento motor: trabajo neto", "kJ/kg")):
        filas.append(_margen("motor_" + clave, nombre, grupo,
                              {"compresion": "rp−1 > banda", "expansion": "p3−p4 > banda",
                               "calor_aportado": "qin > banda", "trabajo_neto": "wn > banda"}[clave],
                              margenes[clave], bandas.get(clave), unidad,
                              "Se reutiliza la banda de viabilidad del modelo: 1e−10 por la escala propia de cada magnitud; no es incertidumbre experimental."))
    motor_conocido = bool(bandas) and all(_finito(v) for v in margenes.values())
    motor = motor_conocido and all(v > bandas[k] for k, v in margenes.items())
    if "viable" in ciclo:
        clasificacion = ciclo["viable"]
        if clasificacion is None or isinstance(clasificacion, bool):
            filas.append(_comparar("clasificacion_motor", "Coherencia de la clasificación motora", grupo,
                                   "viable coincide con los cuatro márgenes",
                                   float(clasificacion) if clasificacion is not None else None,
                                   float(motor) if motor_conocido else None, "—",
                                   "La clasificación booleana se comprueba frente a los márgenes recibidos y las bandas vigentes.",
                                   atol=0., rtol=0., naturaleza="restricción"))
        else:
            filas.append(_registro("clasificacion_motor", "Coherencia de la clasificación motora", grupo,
                                   "viable coincide con los cuatro márgenes", "—",
                                   "La clasificación debe ser un booleano, no un texto ni una cantidad numérica.",
                                   "restricción", estado="atencion", valor=str(clasificacion),
                                   motivo="El campo viable no contiene true/false como valor booleano."))
    filas.append(_margen("calor_rechazado_signo", "Signo del calor rechazado", grupo,
                          "qout > 0", qout, 0., "kJ/kg",
                          "El calor rechazado se expresa como una magnitud positiva para cerrar el ciclo motor."))
    for clave, nombre, denominador, numerador, relacion in (
            ("rendimiento", "Rendimiento térmico", qin, wn, "η = wn/qin"),
            ("back_work_ratio", "Back work ratio", wt, wc, "BWR = wc/wt")):
        ref = numerador / denominador if motor and _finito(numerador) and _finito(denominador) and denominador > 0 else None
        fila = _comparar(clave, nombre, grupo, relacion, ciclo.get(clave), ref, "—", identidad)
        if not motor:
            fila["motivo"] = ("El cociente de prestaciones sólo se interpreta en el interior motor; no se inventa un rendimiento para un punto no motor."
                              if motor_conocido else "Faltan las energías originales o sus bandas para evaluar el cociente motor.")
        filas.append(fila)
        valor = ciclo.get(clave)
        fila = _registro(clave + "_rango", nombre + ": rango motor", grupo, "0 < valor < 1", "—",
                         "Con trabajo neto positivo y calor rechazado positivo, ambos cocientes motores están entre cero y uno.", "restricción")
        if motor and _finito(valor):
            correcto = 0 < valor < 1
            fila.update(valor=valor, estado="cumple" if correcto else "atencion", criterio="Intervalo abierto (0,1).",
                        motivo="" if correcto else "Cociente fuera de su rango motor.")
        elif not motor:
            fila["motivo"] = "El punto no pertenece al interior motor." if motor_conocido else "Faltan datos para decidir el interior motor."
        filas.append(fila)

    for identificador, nombre, valor, ref in (
            ("T1_entrada", "Temperatura de entrada", t[0] if valido_t else None, parametros.get("T1")),
            ("T3_entrada", "Temperatura máxima impuesta", t[2] if valido_t else None, parametros.get("T3"))):
        filas.append(_comparar(identificador, nombre, grupo, "T_estado = T_entrada", valor, ref, "K",
                               "Contraste entre los estados conservados y los parámetros de esta ejecución.", atol=1e-10, naturaleza="contraste"))
    for identificador, nombre, i, j in (("orden_compresion", "Temperaturas de compresión", 1, 0),
                                       ("orden_calentamiento", "Temperaturas de aporte de calor", 2, 1),
                                       ("orden_expansion", "Temperaturas de expansión", 2, 3),
                                       ("orden_enfriamiento", "Temperaturas de rechazo de calor", 3, 0)):
        filas.append(_margen(identificador, nombre, grupo, f"T{i+1}−T{j+1} > 0", t[i] - t[j] if valido_t else None,
                              0., "K", "Orden de temperaturas requerido para interpretar los cuatro procesos como un ciclo motor."))

    p_ref = None
    if _finito(parametros.get("p1")) and _finito(rp) and _finito(delta):
        p1 = parametros["p1"]
        p_ref = (p1, p1 * rp, p1 * rp * (1 - delta), p1)
    for i in range(4):
        filas.append(_comparar(f"presion_{i+1}", f"Relación de presión: estado {i+1}", grupo,
                               ("p1 = entrada", "p2 = p1·rp", "p3 = p2·(1−δ)", "p4 = p1")[i],
                               p[i] if valido_p else None, p_ref[i] if p_ref else None, "kPa",
                               "En el ideal δ=0; en el no ideal la cámara pierde la fracción δ de presión y el rechazo se realiza a p1.",
                               atol=1e-10, naturaleza="contraste"))
    refs_s = {}
    if valido_t and valido_p and propiedades:
        a = (gamma - 1) / gamma
        try:
            refs_s = {"T2s": exp(log(t[0]) + a * (log(p[1]) - log(p[0]))),
                      "T4s": exp(log(t[2]) + a * (log(p[3]) - log(p[2])))}
        except OverflowError:
            pass
    for clave, indice, nombre in (("T2s", 1, "Referencia isentrópica del compresor"),
                                  ("T4s", 3, "Referencia isentrópica de la turbina")):
        valor = (t[indice] if valido_t else None) if modelo == "ideal" else ciclo.get(clave)
        filas.append(_comparar(clave, nombre, grupo,
                               "T2s/T1 = (p2/p1)^a" if clave == "T2s" else "T4s/T3 = (p4/p3)^a",
                               valor, refs_s.get(clave), "K",
                               "La temperatura REAL es isentrópica sólo en el ideal. En el no ideal se contrasta T2s o T4s, no se exige isentropicidad a T2/T4.",
                               atol=1e-10, naturaleza="contraste"))
    for clave, eficiencia, salto_real, salto_iso, relacion in (
            ("eta_c", ec, t[1] - t[0] if valido_t else None,
             refs_s["T2s"] - t[0] if valido_t and refs_s else None,
             "ηc·(T2−T1) = T2s−T1"),
            ("eta_t", et, t[2] - t[3] if valido_t else None,
             t[2] - refs_s["T4s"] if valido_t and refs_s else None,
             "T3−T4 = ηt·(T3−T4s)")):
        aplicable = (_finito(salto_real) and _finito(salto_iso) and salto_real > 0
                     and salto_iso > 0 and _finito(eficiencia))
        obtenido = (eficiencia * salto_real if clave == "eta_c" else salto_real) if aplicable else None
        referencia = (salto_iso if clave == "eta_c" else eficiencia * salto_iso) if aplicable else None
        fila = _comparar(clave, "Eficiencia isentrópica del " + ("compresor" if clave == "eta_c" else "turbina"),
                         grupo, relacion, obtenido, referencia, "K",
                         "Se reconstruye la referencia isentrópica desde las presiones y se usa la ecuación multiplicada para evitar dividir por un salto casi nulo. Sin salto positivo la eficiencia del equipo no es evaluable.",
                         atol=1e-10, escala=max(t) if valido_t else None, naturaleza="contraste")
        if obtenido is None:
            fila["motivo"] = "Faltan estados o no existe un salto térmico positivo que permita definir esta eficiencia."
        filas.append(fila)
    if modelo == "ideal":
        ref_eta = 1 - exp(-((gamma - 1) / gamma) * log(rp)) if propiedades and _finito(rp) and rp > 0 and motor else None
        filas.append(_comparar("rendimiento_ideal", "Rendimiento ideal por dos rutas", grupo,
                               "η_balance = 1−rp^(−a)", ciclo.get("rendimiento"), ref_eta, "—",
                               "Contrasta la fórmula cerrada con el cociente de energía. Son rutas de cálculo distintas dentro del mismo modelo, no una referencia experimental.", naturaleza="contraste"))
    filas.extend(_diagnosticar_segunda_ley(grupo, segunda_ley, T0, cp, gamma, ciclo))
    return filas


def _diagnosticar_segunda_ley(grupo, estudio, T0, cp, gamma, ciclo):
    """Registro de un modelo -> filas de s [kJ/(kg K)] y eD [kJ/kg]."""
    filas = []
    estudio = estudio or {}
    estado = estudio.get("estado")
    if estado in ("limite_numerico", "inconsistencia"):
        filas.append(_registro("segunda_ley_estado", "Disponibilidad de Segunda Ley", grupo,
                               "Análisis cuantificable", "—", "Una inconsistencia o un límite de cálculo no equivale a declarar que el ciclo es no motor.",
                               "contraste", estado="atencion", motivo=estudio.get("motivo", estado)))
    t, p, s = (estudio.get(k, ()) for k in ("temperaturas", "presiones", "entropias"))
    datos = (len(t) == len(p) == len(s) == 4 and all(_finito(v) and v > 0 for v in (*t, *p))
             and all(_finito(v) for v in s) and _finito(cp) and cp > 0 and _finito(gamma) and gamma > 1)
    componentes = estudio.get("componentes", {})
    for i in range(4):
        referencia_s = (cp / 1000 * ((log(t[i]) - log(t[0])) - (1 - 1 / gamma) * (log(p[i]) - log(p[0])))
                        if datos else None)
        filas.append(_comparar(f"entropia_estado_{i+1}", f"Entropía relativa: estado {i+1}", grupo,
                               "si−s1 = cp/1000·ln(Ti/T1) − R/1000·ln(pi/p1)", s[i] if datos else None,
                               referencia_s, "kJ/(kg·K)", "Se fija s1=0 como referencia arbitraria. Son entropías relativas, no absolutas ni generación del ciclo completo.",
                               atol=1e-12, escala=max(abs(s[i]), cp / 1000) if datos else None, naturaleza="contraste"))
    for nombre, i, j in (("compresor", 0, 1), ("turbina", 2, 3)):
        c = componentes.get(nombre, {})
        referencia = (cp / 1000 * ((log(t[j]) - log(t[i])) - (1 - 1 / gamma) * (log(p[j]) - log(p[i])))
                      if datos else None)
        escala_s = max(abs(s[i]), abs(s[j]), cp / 1000) if datos else None
        tol_s = 1e-10 * escala_s if escala_s is not None else None
        filas.append(_comparar(f"sgen_{nombre}_estados", f"Entropía generada: {nombre}", grupo,
                               "sgen,bruta = cp/1000·ln(Tj/Ti) − R/1000·ln(pj/pi)", c.get("bruto"),
                               referencia, "kJ/(kg·K)", "En el equipo adiabático estacionario, el cambio de entropía es generación. Se contrasta el valor bruto, conservando los negativos pequeños antes de corregirlos a cero.",
                               atol=1e-12, escala=escala_s, naturaleza="contraste"))
        filas.append(_margen(f"sgen_{nombre}_signo", f"Segunda Ley: no negatividad en {nombre}", grupo,
                              "sgen,bruta ≥ −banda", c.get("bruto", referencia), tol_s, "kJ/(kg·K)",
                              "Se reutiliza la banda de generación adiabática: 1e−10·max(|si|,|sj|,cp/1000). Un pequeño negativo de redondeo no demuestra violación física.", estricto=False))
        filas.append(_comparar(f"sgen_{nombre}_corregida", f"Generación cuantificada: {nombre}", grupo,
                               "sgen = max(0, sgen,bruta), sólo dentro de banda", c.get("valor"),
                               max(0., c["bruto"]) if _finito(c.get("bruto")) and tol_s is not None and c["bruto"] >= -tol_s else None,
                               "kJ/(kg·K)", "La corrección a cero sólo está permitida para negativos dentro de la tolerancia; se mantiene el valor bruto visible.",
                               atol=1e-12, escala=escala_s))
        ref_ed = T0 * c["valor"] if _finito(T0) and T0 > 0 and _finito(c.get("valor")) else None
        escala_ed = abs(T0) * escala_s if _finito(T0) and escala_s is not None else None
        filas.append(_comparar(f"exergia_{nombre}", f"Gouy–Stodola: {nombre}", grupo,
                               "eD = T0·sgen", c.get("exergia_destruida"), ref_ed, "kJ/kg",
                               "Destrucción específica de exergía del equipo adiabático. Esta multiplicación es una identidad de construcción, no una validación independiente.",
                               atol=1e-10, escala=escala_ed))
        filas.append(_margen(f"exergia_{nombre}_signo", f"Exergía destruida no negativa: {nombre}", grupo,
                              "eD ≥ −T0·banda_s", c.get("exergia_destruida"),
                              T0 * tol_s if _finito(T0) and T0 > 0 and tol_s is not None else None,
                              "kJ/kg", "Para T0 positiva la destrucción de exergía no puede ser negativa fuera del redondeo admitido.", estricto=False))
        trabajo = ciclo.get("trabajo_" + nombre)
        delta_h = cp / 1000 * (t[j] - t[i]) if datos else None
        delta_psi = delta_h - T0 * (s[j] - s[i]) if datos and _finito(T0) and T0 > 0 else None
        ref_balance = ((trabajo - delta_psi) if nombre == "compresor" else (-delta_psi - trabajo)) if _finito(trabajo) and _finito(delta_psi) else None
        filas.append(_comparar(f"exergia_{nombre}_balance", f"Balance alternativo de exergía: {nombre}", grupo,
                               "eD,c = wc−(ψ2−ψ1)" if nombre == "compresor" else "eD,t = (ψ3−ψ4)−wt",
                               c.get("exergia_destruida"), ref_balance, "kJ/kg",
                               "Δψ = cp·ΔT/1000−T0·Δs; se omiten energía cinética y potencial. El balance alternativo usa el trabajo conservado, pero comparte el mismo modelo y no es un dato externo independiente.",
                               atol=1e-10, escala=max(abs(trabajo), abs(delta_psi), abs(ref_ed or 0.)) if _finito(trabajo) and _finito(delta_psi) else None))
    valores_ed = [componentes.get(n, {}).get("exergia_destruida") for n in ("compresor", "turbina")]
    suma = sum(valores_ed) if all(_finito(v) for v in valores_ed) else None
    filas.append(_comparar("exergia_suma", "Suma parcial de exergía destruida", grupo,
                           "eD,parcial = eD,c + eD,t", estudio.get("suma_componentes"), suma, "kJ/kg",
                           "Sólo suma compresor y turbina. No es destrucción total del motor, ni W_ideal−W_noideal.", atol=1e-10))
    for identificador, nombre, motivo in (
            ("segunda_ley_camara", "Generación de entropía de la cámara", "Faltan la transferencia de entropía con calor y las temperaturas de frontera, o un modelo de combustión. El cambio de entropía del fluido no es su generación."),
            ("segunda_ley_global", "Balance global de Segunda Ley y exergía", "No se dispone de las interacciones térmicas completas y sus temperaturas de frontera. La suma de dos equipos es parcial.")):
        filas.append(_registro(identificador, nombre, grupo, "Balance completo del volumen de control", "—",
                               motivo, "restricción", motivo=motivo))
    return filas


def diagnosticar_optimizacion(parametros, estudio, modelo="noideal", objetivo="trabajo", contexto=""):
    """Dict del optimizador -> clasificación y contrastes de rp/objetivo.

    No ejecuta optimizadores ni interpreta viabilidad como prueba de máximo.
    Reutiliza las tolerancias publicadas por los coordinadores existentes.
    rp, eta [-]; W [kJ/kg]. Datos numéricos ausentes -> no_evaluable.
    """
    if modelo not in ("ideal", "noideal") or objetivo not in ("trabajo", "rendimiento"):
        raise ValueError("Modelo u objetivo de optimización desconocido.")
    grupo = " · ".join(v for v in (contexto, modelo, "Optimización de " + objetivo) if v)
    estudio = estudio or {}
    estado = estudio.get("estado")
    fila = _registro("optimo_clasificacion", "Naturaleza del resultado de optimización", grupo,
                     "Máximo interior / frontera / supremo no alcanzado", "—",
                     "Un punto motor no prueba por sí solo un máximo. Se requiere clasificación y contraste de los métodos disponibles.", "restricción")
    filas = [fila]
    if estado == "supremo_no_alcanzado":
        supremo = estudio.get("supremo") or {}
        reversible = modelo == "ideal" or (parametros.get("eta_c") == parametros.get("eta_t") == 1 and parametros.get("perdida_presion_combustor") == 0)
        coherente = (objetivo == "rendimiento" and reversible and supremo.get("alcanzado") is False
                     and estudio.get("analitico") is None and estudio.get("numerico") is None)
        fila.update(valor="Supremo no alcanzado", estado="cumple" if coherente else "atencion",
                    criterio="Rendimiento reversible creciente; frontera excluida y sin ciclo óptimo ficticio.",
                    motivo="" if coherente else "Clasificación incompatible con un supremo reversible no alcanzado.")
        t1, t3 = parametros.get("T1"), parametros.get("T3")
        ref = 1 - t1 / t3 if _finito(t1) and _finito(t3) and t3 > t1 > 0 else None
        filas.append(_comparar("supremo_valor", "Valor del supremo de rendimiento", grupo,
                               "sup η = 1−T1/T3", supremo.get("rendimiento"), ref, "—",
                               "Es un límite no alcanzado: qin y wn tienden a cero en la frontera superior. No se publica como un máximo físico alcanzado.", naturaleza="contraste"))
        filas.append(_registro("optimo_contraste", "Contraste numérico del máximo alcanzado", grupo,
                               "Máximo analítico frente a numérico", "—", "No existe un máximo alcanzado que comparar.",
                               "contraste", motivo="El resultado es un supremo no alcanzado; no hay punto óptimo motor."))
        return filas
    if estado not in ("disponible", "maximo_interior"):
        motivo = estudio.get("motivo") or "; ".join(estudio.get("motivos") or ()) or "No hay un estudio de optimización cuantificable."
        fila.update(valor=estado, estado="atencion" if estado in ("frontera", "limite_numerico", "inconsistencia") else "no_evaluable", motivo=motivo,
                    criterio="Dominio vacío y límite numérico son situaciones distintas.")
        return filas
    es_registro = "rp" in estudio or "ciclo" in estudio or "verificacion" in estudio
    analitico = ({"rp": estudio.get("rp"), "ciclo": estudio.get("ciclo")}
                if es_registro else estudio.get("analitico") or {})
    numerico = estudio.get("numerico") or {}
    dominio = estudio.get("dominio") or {}
    intervalo = dominio.get("intervalo", ())
    rp = analitico.get("rp")
    punto = analitico.get("ciclo") or {}
    interior = len(intervalo) == 2 and _finito(rp) and intervalo[0] < rp < intervalo[1]
    motor = punto.get("viable") is True
    correcto = interior and motor and (estado == "disponible" if objetivo == "trabajo" or es_registro else estado == "maximo_interior")
    fila.update(valor="Candidato interior motor" if correcto else "Candidato inadmisible o de frontera",
                estado="cumple" if correcto else "atencion", criterio="rp en intervalo abierto y ciclo viable; contraste de optimalidad en filas separadas.",
                motivo="" if correcto else "No puede declararse un máximo físico fuera del interior motor.")
    concordancia = ((estudio.get("verificacion") or {}).get("concordancia")
                    if es_registro else estudio.get("concordancia")) or {}
    for clave, nombre, unidad, tol in (("rp", "Concordancia de la relación de presiones óptima", "—", concordancia.get("tolerancia_rp")),
                                      ("trabajo_neto" if objetivo == "trabajo" else "rendimiento",
                                       "Concordancia del objetivo optimizado", "kJ/kg" if objetivo == "trabajo" else "—",
                                       concordancia.get("tolerancia_trabajo" if objetivo == "trabajo" else "tolerancia_rendimiento"))):
        if es_registro:
            diferencia = "diferencia_rp" if clave == "rp" else ("diferencia_trabajo" if objetivo == "trabajo" else "diferencia_rendimiento")
            v, ref = concordancia.get(diferencia), 0.
        else:
            v = numerico.get("rp") if clave == "rp" else (numerico.get("ciclo") or {}).get(clave)
            ref = analitico.get("rp") if clave == "rp" else punto.get(clave)
        filas.append(_comparar("optimo_" + clave, nombre, grupo, "Resultado numérico = resultado analítico", v, ref, unidad,
                               ("Se comprueba el residuo del contraste conservado en esta muestra; no se vuelve a ejecutar la búsqueda. " if es_registro else "")
                               + "La búsqueda numérica no utiliza el candidato analítico para elegir su solución. Las dos rutas comparten el mismo modelo físico; no son validación experimental.",
                               atol=tol if _finito(tol) and tol >= 0 else 0., rtol=0., naturaleza="contraste")
                     if tol is not None else _registro("optimo_" + clave, nombre, grupo,
                                                       "Resultado numérico = resultado analítico", unidad,
                                                       "Sólo se declara contraste cuando la búsqueda y su tolerancia están disponibles.", "contraste",
                                                       valor=v, referencia=ref, motivo="Falta búsqueda numérica o tolerancia de concordancia."))
    return filas
