"""Presentación compartida local/autónoma. No calcula ciclos ni optimizaciones."""

from base64 import b64encode
from html import escape
import json
from math import isfinite
from pathlib import Path
import re

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sensibilidad import PARAMETROS_ESTUDIO
from guias_educativas import construir_guias, construir_pestanas

RAIZ = Path(__file__).resolve().parent
SECCIONES = (("simulacion", "Simulación"), ("resultados", "Resultados"),
             ("optimizacion", "Optimización"), ("sensibilidad", "Sensibilidad"),
             ("mapa", "Mapa de diseño"), ("segunda_ley", "Segunda ley"), ("informes", "Informes"), ("ayuda", "Ayuda"))
GRUPOS = (("Condiciones de entrada", ("T1", "T3", "p1")),
          ("Propiedades del fluido", ("cp", "gamma")),
          ("Configuración y pérdidas", ("relacion_presiones", "eta_c", "eta_t", "perdida_presion_combustor")))
CAMPOS = {
    "T1": ("T1 · Entrada del compresor", "K", "Temperatura absoluta mayor que 0", "0", None),
    "T3": ("T3 · Entrada de la turbina", "K", "Temperatura absoluta mayor que 0", "0", None),
    "p1": ("p1 · Presión de entrada", "kPa", "Presión absoluta mayor que 0", "0", None),
    "relacion_presiones": ("rp · Relación de presiones", "adimensional", "Mayor que 1; rp = p2/p1", "1", None),
    "cp": ("cp · Calor específico", "J/(kg·K)", "Mayor que 0; constante en el modelo", "0", None),
    "gamma": ("gamma · Relación cp/cv", "adimensional", "Mayor que 1", "1", None),
    "eta_c": ("eta_c · Eficiencia del compresor", "fracción", "0 < eta_c ≤ 1", "0", "1"),
    "eta_t": ("eta_t · Eficiencia de la turbina", "fracción", "0 < eta_t ≤ 1", "0", "1"),
    "perdida_presion_combustor": ("delta · Pérdida del combustor", "%", "0 ≤ pérdida < 100 %; 5 significa 5 %", "0", "100"),
}
AYUDA = (
    ("El ciclo Brayton", "Compresión, aporte de calor, expansión y rechazo de calor. El modelo describe un ciclo, no un motor completo."),
    ("Ideal y no ideal", "El ideal utiliza equipos isentrópicos. El no ideal incorpora eficiencias de compresor/turbina y pérdida de presión en el combustor."),
    ("Relación de presiones rp", "rp = p2/p1 es la relación de compresión. No es la relación real de expansión cuando hay pérdida de presión."),
    ("Dominio motor viable", "Exige compresión y expansión disponibles, calor aportado positivo y trabajo neto positivo. Sus fronteras están excluidas."),
    ("Dos criterios de diseño", "A maximiza el trabajo específico. B maximiza el rendimiento térmico cuando existe un máximo interior. Un supremo no alcanzado no es un punto operativo."),
    ("OFAT y limitaciones", "OFAT varía una entrada conservando las demás. No mide interacciones. Gas ideal con cp/gamma constantes; sin combustible, caudal, potencia, empuje ni mapas. Verificación interna, no validación experimental."),
)


INTRODUCCION = ('Analizamos un ciclo Brayton simplificado ideal o no ideal: el compresor consume trabajo, '
    'el calor eleva la temperatura y la turbina produce trabajo. El trabajo neto es la diferencia entre '
    'producción y consumo; el rendimiento térmico relaciona trabajo neto y calor aportado. Son energías '
    'específicas, no potencia. Todavía no calculamos el empuje de un aerorreactor real.')

GLOSARIO = (
    ('rp [−]', 'Relación p2/p1 del compresor. Con pérdida en el combustor no coincide con la relación de expansión de la turbina.'),
    ('T1 y T3 [K]', 'Temperaturas absolutas de entrada al compresor y a la turbina; delimitan los niveles térmicos del ciclo.'),
    ('eta_c y eta_t [fracción]', 'Eficiencias isentrópicas: una compresión menos eficiente consume más trabajo y una expansión menos eficiente produce menos, para las mismas condiciones de referencia.'),
    ('delta [fracción o %]', 'Pérdida relativa de presión del combustor. El formulario usa porcentaje y los cálculos usan fracción: 5 % equivale a 0,05.'),
    ('Trabajo del compresor [kJ/kg]', 'Consumo específico durante la compresión, calculado con el incremento de temperatura y cp.'),
    ('Trabajo de la turbina [kJ/kg]', 'Producción específica durante la expansión, calculada con la caída de temperatura y cp.'),
    ('Trabajo neto [kJ/kg]', 'Trabajo de turbina menos trabajo de compresor. Un valor positivo es necesario, aunque no suficiente por sí solo, para clasificar un ciclo motor.'),
    ('Calor aportado Qin [kJ/kg]', 'Energía térmica específica añadida entre 2 y 3. Debe ser positiva para un ciclo motor del modelo.'),
    ('Rendimiento térmico [fracción o %]', 'Cociente trabajo neto/Qin para un punto motor. Se presenta en porcentaje; fuera del dominio motor no se publica como prestación válida.'),
    ('Back work ratio [−]', 'Cociente entre consumo del compresor y producción de la turbina; indica qué fracción de esa producción se necesita para comprimir.'),
    ('Trabajo específico y potencia', 'kJ/kg mide energía por unidad de masa; kW mide energía por unidad de tiempo. Sin caudal másico no se calcula potencia.'),
)

EXPLICACIONES_GRAFICAS = {
    'rendimiento_brayton.png': 'X es rp y Y el rendimiento ideal [%]. Varía sólo rp; T1, T3, cp, gamma y las demás entradas permanecen constantes. El rendimiento ideal crece dentro del dominio motor, pero su límite superior no es un máximo operativo: allí se anulan el calor aportado y el trabajo.',
    'comparacion_ideal_noideal.png': 'X es rp y Y el rendimiento térmico [%]. Se comparan ideal y no ideal con las mismas entradas fijas, variando sólo rp. Las pérdidas modifican la conversión de calor en trabajo y pueden producir un máximo interior no ideal. Los huecos excluyen puntos no motores; mayor rendimiento no significa necesariamente mayor trabajo específico.',
    'trabajo_neto_vs_rp.png': 'X es rp y Y el trabajo neto ideal [kJ/kg], a T1 y T3 constantes y sin variar las demás entradas. Aumentar rp modifica tanto la producción de la turbina como el consumo del compresor. Su diferencia presenta un máximo interior; por eso el trabajo puede decrecer aunque el rendimiento ideal siga aumentando.',
    'trabajo_neto_ideal_noideal.png': 'X es rp y Y el trabajo neto [kJ/kg]. Sólo cambia rp; temperaturas, propiedades y pérdidas permanecen fijas. Compara el balance ideal con el no ideal: las ineficiencias afectan consumo y producción, y la pérdida de presión reduce la expansión disponible. Los máximos se contrastan independientemente del muestreo y sólo se dibujan regiones motoras.',
    'diagrama_ts_brayton.png': 'Diagrama exclusivamente ideal: X es entropía específica relativa [kJ/(kg·K)] y Y temperatura [K], con el caso introducido fijo. 1→2 es compresión isentrópica; 2→3, aporte de calor isóbaro; 3→4, expansión isentrópica; 4→1, rechazo de calor isóbaro. No representa la generación de entropía de equipos no ideales.',
    'diagrama_pv_brayton.png': 'Diagrama exclusivamente ideal: X es volumen específico [m³/kg] y Y presión [kPa], sin barrer entradas. 1→2 comprime isentrópicamente; 2→3 aporta calor a presión constante; 3→4 expande isentrópicamente; 4→1 rechaza calor a presión constante. El recorrido muestra el ciclo motor del modelo de gas ideal, no volúmenes geométricos de un motor real.',
    'compromiso_trabajo_rendimiento.png': 'X es trabajo neto [kJ/kg] y Y rendimiento térmico [%]; rp parametriza la curva, manteniendo T1, T3, propiedades y pérdidas constantes. A y B responden a objetivos diferentes. Elegir B puede reducir el trabajo por kilogramo a cambio de aprovechar mejor el calor; no toda la curva constituye una frontera de Pareto.',
    'trabajo_neto': 'X es el parámetro OFAT seleccionado, con la unidad indicada, y Y trabajo neto [kJ/kg]. Las demás entradas permanecen fijas, salvo rp en A/B, que se reajusta para cada objetivo. R conserva rp de referencia. Los huecos indican resultados operativos no disponibles; comparar escenarios permite separar el efecto del parámetro del reajuste del diseño.',
    'rendimiento': 'X es el parámetro OFAT seleccionado y Y rendimiento térmico [%]. Se mantienen las demás entradas, con rp fija en R y reajustada en A/B. B busca la mayor fracción de calor convertida en trabajo, no el mayor trabajo específico. Un cambio de 40 % a 42 % son 2 puntos porcentuales, equivalentes a un incremento relativo del 5 %.',
    'rp': 'X es el parámetro OFAT y Y rp [−]. A/B muestran los máximos alcanzados con los demás parámetros físicos fijos; sus huecos respetan la disponibilidad motora. La consigna R permanece constante incluso si el ciclo deja de ser viable: esa línea de referencia no demuestra la existencia de un punto motor.',
    'mapa_trabajo_neto.png': 'X es rp y Y T3 [K]; cada celda representa un ciclo con esos valores y siete entradas fijas. El color indica trabajo neto motor [kJ/kg]; gris excluye ciclos no motores o límites numéricos. A maximiza trabajo y B rendimiento para cada T3. No buscamos todavía una T3 óptima global.',
    'mapa_rendimiento.png': 'X es rp y Y T3 [K], a siete parámetros fijos. El color indica rendimiento térmico [%]: valores mayores aprovechan mejor el calor dentro del modelo. B identifica su máximo por temperatura y A permite comparar el diseño de máximo trabajo. Maximizar rendimiento no equivale a maximizar trabajo; gris no representa prestaciones motoras válidas.',
    'mapa_viabilidad.png': 'X es rp y Y T3 [K], a siete entradas fijas. La región motora cumple simultáneamente compresión, expansión, calor positivo y trabajo neto positivo. Las fronteras calculadas delimitan el dominio abierto y pueden ser más precisas que el borde de las celdas. No es un mapa operativo real de compresor o turbina; gris también incluye límites numéricos.',
    'corte': 'Este corte fija T3 y mantiene los otros siete parámetros; sólo varía rp [−] en X. Los ejes Y muestran trabajo neto [kJ/kg] y rendimiento [%]. Comparar temperaturas permite observar el desplazamiento de los óptimos calculados. Las marcas A/B son independientes de las columnas; los huecos excluyen puntos no motores y un supremo no se marca como B.',
}

TEXTO_OPTIMIZACION = ('A — Máximo trabajo específico: buscamos la rp que produce más trabajo neto por kilogramo, '
    'manteniendo constantes los demás parámetros. B — Máximo rendimiento: buscamos la rp que convierte en trabajo '
    'la mayor proporción del calor aportado. No son necesariamente el mismo diseño; obtener mayor rendimiento '
    'puede exigir sacrificar trabajo específico.')
TEXTO_DISPONIBILIDAD = ('Un máximo interior alcanzado es un punto motor admisible. Un supremo no alcanzado es '
    'un valor límite, no un ciclo operativo ni un punto B. Dominio motor vacío significa que ninguna rp cumple '
    'simultáneamente las condiciones motoras; un límite numérico indica falta de resolución fiable, no prueba de inviabilidad física.')


def bloque_educativo(titulo, texto):
    """Tarjeta breve de texto plano; escapa título y contenido, sin cálculos."""
    return f'<div class="card educational-note"><h3>{escape(titulo)}</h3><p>{escape(texto)}</p></div>'


def conclusiones_html(observaciones):
    """Hasta cuatro observaciones ya obtenidas de datos, nunca genera tendencias."""
    frases = list(observaciones)[:4] or ['No hay resultados suficientes para extraer una conclusión fiable.']
    return ('<div class="card educational-conclusions"><h3>¿Qué hemos aprendido de esta simulación?</h3><ul>'
            + ''.join(f'<li>{escape(f)}</li>' for f in frases) + '</ul></div>')


def parametros_fijos_texto(parametros, variables):
    """Lista valores/unidades de entradas no barridas ni reajustadas."""
    unidades = dict(T1='K', T3='K', p1='kPa', cp='J/(kg·K)', gamma='−', eta_c='fracción',
                    eta_t='fracción', perdida_presion_combustor='fracción', relacion_presiones='−')
    return '; '.join(f"{'delta' if k == 'perdida_presion_combustor' else k}={v:g} {unidades[k]}"
                     for k, v in parametros.items() if k not in variables)


def json_seguro(datos):
    """JSON incrustable en script inerte, sin cierres HTML aportados por valores."""
    return json.dumps(datos, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c").replace("&", "\\u0026")


def renderizar_dashboard(valores, *, contenidos=None, metadata=None, informes=(), errores=None,
                         modo_local=True, informe_actual="", seccion_inicial="simulacion"):
    """HTML de seis secciones; recursos locales o incrustados, sin cálculo físico."""
    css = (RAIZ / "static/style.css").read_text(encoding="utf-8")
    js = (RAIZ / "static/dashboard.js").read_text(encoding="utf-8")
    if modo_local:
        css = '<link rel="stylesheet" href="/static/style.css">'
        js = '<script src="/static/dashboard.js" defer></script>'
    else:
        for fuente in (RAIZ / "static/fonts").glob("*.woff2"):
            css = css.replace(f"fonts/{fuente.name}", "data:font/woff2;base64," + b64encode(fuente.read_bytes()).decode("ascii"))
        css = "<style>" + css + "</style>"
        js = "<script>" + js + "</script>"
    entorno = Environment(loader=FileSystemLoader(RAIZ / "templates"), autoescape=select_autoescape(["html"]))
    return entorno.get_template("index.html").render(
        titulo="Configuración del ciclo" if modo_local else "Informe técnico",
        css=css, js=js, motor=(RAIZ / "static/images/engine-cutaway.svg").read_text(encoding="utf-8"),
        valores=valores, grupos=GRUPOS, campos=CAMPOS, estudios=PARAMETROS_ESTUDIO,
        secciones=SECCIONES, guias=construir_guias(), pestanas=construir_pestanas(), ayuda=AYUDA, errores=errores or {}, informes=informes,
        tiene_informe=bool(metadata), texto_intro=INTRODUCCION, glosario=GLOSARIO,
        contenidos=contenidos or {k: "" for k in ("resultados", "optimizacion", "sensibilidad")},
        informe_actual=informe_actual, modo_local=modo_local, seccion_inicial=seccion_inicial,
        catalogo=json_seguro(PARAMETROS_ESTUDIO), metadata=json_seguro(metadata or {}),
        licencia_fuentes=(RAIZ / "static/fonts/OFL.txt").read_text(encoding="utf-8"))


def tarjeta_kpi(clave, etiqueta, valor, unidad, explicacion, decimales=3):
    """Tarjeta numérica de presentación: None se muestra como no disponible, no cero."""
    numero = f"{valor:.{decimales}f}" if valor is not None else "No disponible"
    estado = "Disponible" if valor is not None else "No disponible"
    return (f'<article class="kpi" data-kpi="{escape(clave)}"><div class="kpi-label">{escape(etiqueta)}</div>'
            f'<div class="kpi-value">{numero} <span class="unit">{escape(unidad)}</span></div>'
            f'<small>{escape(explicacion)}</small><span class="badge {"available" if valor is not None else "unavailable"}">{estado}</span></article>')


def plegable(titulo, contenido):
    """Details nativo cerrado, contenido HTML ya escapado por sus presentadores."""
    return f'<details class="card"><summary>{escape(titulo)}</summary><div class="detail-body">{contenido}</div></details>'


def separar_presentacion(contenido):
    """Extrae metadatos y paneles de un informe nuevo; None para formato histórico."""
    coincidencia = re.search(r'<script type="application/json" id="brayton-metadata">(.*?)</script>', contenido, re.S)
    if not coincidencia:
        return None
    try:
        metadata = json.loads(coincidencia[1])
    except (ValueError, TypeError):
        return None
    if not isinstance(metadata, dict) or type(metadata.get("dashboard")) is not int or metadata['dashboard'] != 1:
        return None
    parametros = metadata.get('parametros')
    if (not isinstance(parametros, dict) or not set(CAMPOS).issubset(parametros)
            or any(type(parametros[k]) not in (int, float) or not isfinite(parametros[k]) for k in CAMPOS)
            or not isinstance(metadata.get('tipo'), str)
            or not isinstance(metadata.get('fecha'), str)
            or not isinstance(metadata.get('git'), dict)):
        return None
    version = metadata['git']
    if (version.get('commit') is not None and not isinstance(version['commit'], str)) or (
            version.get('modificado') is not None and type(version['modificado']) is not bool):
        return None
    estudio = metadata.get('estudio')
    if estudio is not None and (not isinstance(estudio, dict)
            or not isinstance(estudio.get('parametro'), str)
            or estudio['parametro'] not in CAMPOS
            or any(type(estudio.get(k)) not in (int, float) or not isfinite(estudio[k])
                   for k in ('minimo', 'maximo'))
            or type(estudio.get('muestras')) is not int):
        return None
    mapa = metadata.get('mapa')
    if mapa is not None and (not isinstance(mapa, dict)
            or not isinstance(mapa.get('cortes'), list)
            or any(type(t) not in (int, float) or not isfinite(t) for t in mapa['cortes'])
            or any(type(mapa.get(k)) not in (int, float) or not isfinite(mapa[k])
                   for k in ('rp_min', 'rp_max', 'T3_min', 'T3_max'))
            or any(type(mapa.get(k)) is not int for k in ('n_rp', 'n_T3'))
            or not isinstance(mapa.get('escala'), str)):
        return None
    segunda = metadata.get('segunda_ley')
    if segunda is not None and (not isinstance(segunda, dict)
            or type(segunda.get('T0')) not in (int, float)
            or not isfinite(segunda['T0']) or segunda['T0'] <= 0):
        return None
    paneles = {}
    for clave in ("resultados", "optimizacion", "sensibilidad"):
        parte = re.search(f'<!--PANEL:{clave}-->(.*?)<!--FIN:{clave}-->', contenido, re.S)
        if parte is None:
            return None
        paneles[clave] = parte[1]
    parte_mapa = re.search(r'<!--PANEL:mapa-->(.*?)<!--FIN:mapa-->', contenido, re.S)
    if parte_mapa:
        paneles['mapa'] = parte_mapa[1]
    parte_segunda = re.search(r'<!--PANEL:segunda_ley-->(.*?)<!--FIN:segunda_ley-->', contenido, re.S)
    if parte_segunda:
        paneles['segunda_ley'] = parte_segunda[1]
    return metadata, paneles


def visor_graficas(legado, imagenes, sensibilidad=False):
    """Extrae los PNG existentes una vez y los organiza en pestañas sin duplicarlos."""
    figuras = re.findall(r"<figure>.*?</figure>", legado, re.S)
    por_png = {b64encode(datos).decode("ascii"): nombre for nombre, datos in imagenes.items()}
    grupos = {"rendimiento_brayton.png": "rendimiento", "comparacion_ideal_noideal.png": "rendimiento",
              "trabajo_neto_vs_rp.png": "trabajo", "trabajo_neto_ideal_noideal.png": "trabajo",
              "diagrama_ts_brayton.png": "diagramas", "diagrama_pv_brayton.png": "diagramas",
              "compromiso_trabajo_rendimiento.png": "compromiso"}
    pestañas = (("trabajo_neto", "Trabajo neto"), ("rendimiento", "Rendimiento térmico"), ("rp", "Relaciones de presiones")) if sensibilidad else (
        ("rendimiento", "Rendimiento"), ("trabajo", "Trabajo"), ("diagramas", "Diagramas termodinámicos"),
        ("compromiso", "Compromiso de diseño"), ("todas", "Todas"))
    ordenadas = []
    for figura in figuras:
        png = re.search(r"data:image/png;base64,([^'\"]+)", figura)[1]
        nombre = por_png[png]
        grupo = nombre if sensibilidad else grupos[nombre]
        explicacion = f'<p class="plot-help">{escape(EXPLICACIONES_GRAFICAS[nombre])}</p>'
        figura = figura.replace('</figcaption>', '</figcaption>' + explicacion, 1)
        ordenadas.append(figura.replace("<figure>", f'<figure data-plot-group="{grupo}">', 1))
    if len(ordenadas) != len(imagenes):
        raise ValueError("El visor debe conservar exactamente todas las gráficas del informe.")
    prefijo = "ofat" if sensibilidad else "normal"
    botones = "".join(f'<button type="button" role="tab" id="tab-{prefijo}-{k}" aria-controls="graficas-{prefijo}" aria-selected="{str(i == 0).lower()}" data-plot-tab="{k}">{escape(t)}</button>' for i, (k, t) in enumerate(pestañas))
    visor = (f'<div class="card" data-plot-viewer="{prefijo}"><div class="card-title"><h3>Visor de gráficas</h3>'
             f'<span class="badge">{len(figuras)} gráficas</span></div><div class="plot-tabs" role="tablist" aria-label="Gráficas de {prefijo}">{botones}</div>'
             f'<p class="plot-help">Selecciona una vista. Amplía una gráfica para revisar sus leyendas y fronteras.</p>'
             f'<div class="plot-grid" id="graficas-{prefijo}" role="tabpanel" aria-labelledby="tab-{prefijo}-{pestañas[0][0]}">{"".join(ordenadas)}</div></div>')
    sin_figuras = re.sub(r"<figure>.*?</figure>", "", legado, flags=re.S)
    cuerpo = re.search(r"<body><main>(.*?)</main></body>", sin_figuras, re.S)[1]
    cabecera = re.search(r"<header>(.*?)</header>", cuerpo, re.S)[1]
    cuerpo = re.sub(r"<header>.*?</header>", "", cuerpo, flags=re.S)
    cuerpo = cuerpo.replace("<section>", '<div class="technical-section">').replace("</section>", "</div>")
    return visor, cuerpo, cabecera


def terminar_informe(legado, parametros, imagenes, fecha, version, *, noideal=None,
                     barrido=None, optimizaciones=None, estudio_rendimiento=None,
                     comparacion=None, sensibilidad=None, segunda_ley=None, diagnosticos=None):
    """Convierte presentación heredada a dashboard conservando datos/PNG sin recalcular."""
    from reporting import MARCA_INICIO, MARCA_FINAL, seccion_segunda_ley_html
    from diagnostico_html import renderizar_diagnostico
    visor, detalles, cabecera = visor_graficas(legado, imagenes, sensibilidad is not None)
    paneles = {k: "" for k in ("resultados", "optimizacion", "sensibilidad")}
    metadata = {"dashboard": 1, "tipo": "sensibilidad" if sensibilidad is not None else "normal",
                "parametros": parametros, "fecha": fecha.isoformat(), "git": version}
    if diagnosticos is not None:
        metadata['diagnosticos'] = diagnosticos
    valores = parametros.copy()
    valores["perdida_presion_combustor"] *= 100
    if segunda_ley is not None:
        metadata['segunda_ley'] = segunda_ley
        valores['T0'] = segunda_ley['T0']
        paneles['segunda_ley'] = bloque_educativo('Parámetros del caso', parametros_fijos_texto(parametros, ())) + seccion_segunda_ley_html(segunda_ley)
    if sensibilidad is not None:
        c = sensibilidad["configuracion"]
        metadata["estudio"] = c
        valores.update(sens_parametro=c["parametro"], sens_minimo=c["minimo"], sens_maximo=c["maximo"], sens_muestras=c["muestras"])
        tarjetas = []
        observaciones = []
        for s in "RAB":
            disponibles = sum(r[s]["estado"] == "disponible" for r in sensibilidad["registros"])
            inviables = sum(r[s]["estado"] in ("inviable", "parametros_inviables", "sin_dominio") for r in sensibilidad["registros"])
            supremos = sum(r[s]["estado"] == "supremo_no_alcanzado" for r in sensibilidad["registros"])
            numericos = sum(r[s]["estado"] == "limite_numerico" for r in sensibilidad["registros"])
            observaciones.append(f"{s}: {disponibles}/{c['muestras']} muestras con ciclo motor {'a rp fija' if s == 'R' else 'en el máximo alcanzado'}; "
                                 f'{inviables} inviables, {supremos} supremos no alcanzados y {numericos} límites numéricos.')
            tarjetas.append(tarjeta_kpi(s, f"{s} · Muestras operativas", disponibles, f"/ {c['muestras']}",
                f"{c['muestras'] - disponibles} no disponibles: {inviables} inviables, {supremos} supremos, {numericos} límites numéricos", decimales=0))
        filas_locales = []
        for s in "RAB":
            coeficientes = []
            for k in ("trabajo_neto", "rendimiento", "rp"):
                local = sensibilidad["sensibilidades"][s][k]
                valor = local["normalizada"]
                coeficientes.append(f'<td>{valor:.4f}</td>' if valor is not None else '<td>No disponible</td>')
            filas_locales.append(f'<tr><td>{s}</td>{"".join(coeficientes)}</tr>')
        resumen_local = ('<div class="card"><h3>Sensibilidades locales en la referencia</h3>'
            '<p class="muted">S=(x/Y)dY/dx es una sensibilidad normalizada local y adimensional: aproxima el cambio relativo de Y ante un cambio relativo pequeño de x. Incluye reajuste de rp en A/B; no es un cambio en puntos porcentuales ni un ranking universal. No está disponible sin punto motor, con normalización singular o derivada numéricamente no fiable.</p>'
            '<div class="table-wrap"><table><thead><tr><th>Escenario</th><th>S trabajo</th><th>S rendimiento</th><th>S rp</th></tr></thead><tbody>'
            + "".join(filas_locales) + '</tbody></table></div><small>Derivadas absolutas, paso y motivos de indisponibilidad en la tabla detallada.</small></div>')
        clave_variable = PARAMETROS_ESTUDIO[c['parametro']]['clave']
        contexto = (f"OFAT varía un parámetro cada vez: {c['parametro']} [{c['unidad']}], de {c['minimo']:g} a {c['maximo']:g}, "
            f"con {c['muestras']} muestras. En R, rp={parametros['relacion_presiones']:g} permanece fija; A reajusta rp para máximo trabajo "
            'y B para máximo rendimiento alcanzado. Las demás entradas permanecen constantes.')
        fijos = parametros_fijos_texto(parametros, (clave_variable, 'relacion_presiones'))
        paneles["sensibilidad"] = (bloque_educativo('¿Qué estamos modificando?', contexto)
            + f'<p class="muted">Parámetros fijos: {escape(fijos)}.</p>'
            + bloque_educativo('Disponibilidad de los resultados', TEXTO_DISPONIBILIDAD)
            + f'<div class="card"><h3>{escape(c["parametro"])} [{escape(c["unidad"])}] · {c["minimo"]:g}–{c["maximo"]:g}</h3>'
            f'<p>{c["muestras"]} muestras · R: rp fija · A: máximo trabajo · B: máximo rendimiento alcanzado.</p></div>'
            f'<div class="kpi-grid">{"".join(tarjetas)}</div>' + visor + resumen_local + plegable("Tabla de resultados, tendencias y límites", detalles)
            + conclusiones_html(observaciones))
    else:
        a = optimizaciones["noideal"]["analitico"] if optimizaciones else None
        eta = estudio_rendimiento["noideal"] if estudio_rendimiento else None
        b = eta["analitico"] if eta else None
        nota_b = eta["motivo"] if eta else "Estudio no disponible"
        indicadores = (("rp", "Relación de presiones", parametros["relacion_presiones"], "−", "Caso actual no ideal"),
            ("trabajo", "Trabajo específico neto", noideal["trabajo_neto"], "kJ/kg", "Caso actual no ideal"),
            ("rendimiento", "Rendimiento térmico", noideal["rendimiento"] * 100 if noideal["rendimiento"] is not None else None, "%", "Caso actual no ideal"),
            ("calor", "Calor aportado", noideal["calor_aportado"], "kJ/kg", "Caso actual no ideal"),
            ("max_trabajo", "Máximo trabajo específico", a["ciclo"]["trabajo_neto"] if a else None, "kJ/kg", "A · Máximo trabajo no ideal"),
            ("max_rendimiento", "Máximo rendimiento térmico", b["ciclo"]["rendimiento"] * 100 if b else None, "%", "B · Máximo interior" if b else nota_b))
        intervalo = barrido["dominios"]["noideal"]["intervalo"] if barrido else None
        estado = f"Rango motor abierto: {intervalo[0]:.6g} &lt; rp &lt; {intervalo[1]:.6g}." if intervalo else "Dominio no disponible en este informe."
        observaciones = [f"A rp={parametros['relacion_presiones']:g}, el caso no ideal entrega trabajo neto de {noideal['trabajo_neto']:.3f} kJ/kg."]
        if b and a:
            observaciones.append(f"El máximo A está en rp={a['rp']:.6g}; el máximo B está en rp={b['rp']:.6g}.")
        elif eta and eta['estado'] == 'supremo_no_alcanzado':
            observaciones.append(f"B no es un punto operativo: su supremo de rendimiento {100*eta['supremo']['rendimiento']:.3f} % no se alcanza.")
        elif eta:
            observaciones.append(f"No hay máximo B disponible: {eta['motivo']}")
        if comparacion and comparacion['estado'] == 'disponible':
            perdida, ganancia = comparacion['reduccion_trabajo_porcentaje'], comparacion['ganancia_rendimiento_pp']
            if perdida >= 0 and ganancia >= 0:
                observaciones.append(f'Pasar de A a B reduce el trabajo específico un {perdida:.3f} % y aumenta el rendimiento {ganancia:.3f} puntos porcentuales.')
        if len(observaciones) == 1:
            observaciones.append('Este informe no dispone de dos máximos alcanzados para comparar objetivos.')
        paneles["resultados"] = ('<div class="kpi-grid">' + "".join(tarjeta_kpi(*i) for i in indicadores) + '</div>'
            '<div class="card status-card"><span class="badge available">Ciclo motor verificado</span><h3>Estado del ciclo</h3>'
            f'<p>{estado} Las fronteras quedan excluidas; consulta las tolerancias en los detalles.</p></div>' + visor +
            plegable("Estados y balances detallados", detalles) + conclusiones_html(observaciones))
        decisiones = []
        for letra, titulo, punto, motivo in (("A", "Máximo trabajo específico", a, "No disponible"), ("B", "Máximo rendimiento térmico", b, nota_b)):
            if punto:
                datos = (("rp óptima", punto["rp"], "−"), ("Trabajo neto", punto["ciclo"]["trabajo_neto"], "kJ/kg"),
                         ("Rendimiento", punto["ciclo"]["rendimiento"] * 100, "%"), ("Calor aportado", punto["ciclo"]["calor_aportado"], "kJ/kg"))
                contenido = '<dl class="metric-list">' + "".join(f'<dt>{t}</dt><dd>{v:.3f} <small>{u}</small></dd>' for t, v, u in datos) + '</dl>'
            else:
                contenido = f'<span class="badge unavailable">No disponible</span><p>{escape(motivo)}</p>'
            decisiones.append(f'<article class="card design-card"><div class="card-title"><h3>{letra} — {titulo}</h3><span class="letter">{letra}</span></div>{contenido}</article>')
        compromiso = '<p>No hay dos máximos operativos alcanzados para comparar.</p>'
        if comparacion and comparacion["estado"] == "disponible":
            compromiso = '<dl class="metric-list">' + "".join(f'<dt>{t}</dt><dd>{comparacion[k]:.3f} <small>{u}</small></dd>' for k, t, u in (
                ("ganancia_rendimiento_pp", "Ganancia de rendimiento", "pp"), ("reduccion_trabajo_porcentaje", "Reducción relativa del trabajo", "%"),
                ("diferencia_calor", "Diferencia de calor B−A", "kJ/kg"), ("diferencia_rp", "Diferencia de rp B−A", "−"))) + '</dl>'
        paneles["optimizacion"] = (bloque_educativo('¿Qué intentamos optimizar?', TEXTO_OPTIMIZACION)
            + bloque_educativo('Máximo, supremo y dominio vacío', TEXTO_DISPONIBILIDAD)
            + f'<div class="two-columns">{"".join(decisiones)}</div><div class="card tradeoff"><h3>Compromiso entre objetivos</h3>{compromiso}<a href="#resultados/compromiso">Ver gráfica de compromiso</a></div>')
    for clave, diagnostico in (diagnosticos or {}).items():
        fragmento = renderizar_diagnostico(diagnostico, clave)
        if clave in ('resultados', 'sensibilidad') and visor in paneles.get(clave, ''):
            paneles[clave] = paneles[clave].replace(visor, fragmento + visor, 1)
        else:
            paneles[clave] = paneles.get(clave, '') + fragmento
    info = '<div class="card metadata">' + cabecera.replace("<h1>", "<h3>").replace("</h1>", "</h3>") + '</div>'
    pagina = renderizar_dashboard(valores, contenidos=paneles, metadata=metadata,
                                  modo_local=False, informe_actual=info,
                                  seccion_inicial="sensibilidad" if sensibilidad is not None else "resultados")
    return MARCA_INICIO + pagina + MARCA_FINAL
