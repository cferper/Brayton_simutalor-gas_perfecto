"""Presentación HTML y conservación de informes; no contiene ecuaciones del ciclo."""

from base64 import b64encode
from html import escape
from pathlib import Path
import re
import subprocess
from uuid import uuid4
from warnings import warn
from time import perf_counter

from dashboard import (terminar_informe, EXPLICACIONES_GRAFICAS, bloque_educativo,
                       conclusiones_html, TEXTO_OPTIMIZACION, TEXTO_DISPONIBILIDAD)
from diagnostico_informe import (diagnostico_simulacion, diagnostico_optimos,
                                diagnostico_segunda_ley, diagnostico_estudio)
from diagnostico_html import renderizar_diagnostico


MARCA_INICIO = "<!-- Brayton Simulator report v1 -->"
MARCA_FINAL = "<!-- Brayton Simulator report complete -->"
PATRON_INFORME = re.compile(
    r"brayton_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-\d{6}_[0-9a-f]{32}\.html"
)


def crear_informe_sensibilidad_html(estudio, imagenes, fecha, version_git):
    """Presenta datos OFAT ya calculados; tres PNG, sin ecuaciones ni archivos externos."""
    if set(imagenes) != {"trabajo_neto", "rendimiento", "rp"}:
        raise ValueError("El informe de sensibilidad exige exactamente tres gráficas.")
    c = estudio["configuracion"]
    referencia = tabla_html(("Parámetro", "Valor (K, kPa, J/(kg·K) o fracción)"),
                            estudio["referencia"].items())
    filas = []
    dominios = []
    for x, registro in zip(estudio["valores"], estudio["registros"]):
        dominio = registro["dominios"]
        dominios.append((f"{x:.9g}",
            str(dominio["ideal"]["intervalo"]) if dominio else "No disponible",
            str(dominio["noideal"]["intervalo"]) if dominio else "No disponible",
            registro["motivo_dominio"] or "Intervalos físicos abiertos; () = vacío"))
        for s in "RAB":
            r = registro[s]
            valores = ["—" if r[k] is None else f"{r[k] * (100 if k == 'rendimiento' else 1):.9g}"
                       for k in ("rp", "trabajo_neto", "rendimiento", "calor_aportado")]
            motivo = "; ".join(r["motivos"])
            if r["supremo"]:
                motivo += (f" Supremo {100*r['supremo']['rendimiento']:.9g} %, "
                           f"frontera excluida rp={r['supremo']['rp_frontera']:.9g}; no alcanzado.")
            diagnostico = "—"
            if r["ciclo"] and r["estado"] != "disponible":
                diagnostico = (f"Evaluación firmada, no punto motor: W={r['ciclo']['trabajo_neto']:.9g} kJ/kg; "
                               f"Qin={r['ciclo']['calor_aportado']:.9g} kJ/kg")
            filas.append((f"{x:.9g}", s, r["estado"], *valores, r["metodo"], motivo,
                          diagnostico, str(r["verificacion"]) if r["verificacion"] else "No realizada / no aplicable"))
    resultados = tabla_html((c["parametro"], "Escenario", "Estado", "rp [−]", "W [kJ/kg]",
                            "η [%]", "Qin [kJ/kg]", "Método", "Motivos / límites",
                            "Diagnóstico físico", "Contraste numérico: intervalos y concordancia"), filas)
    tabla_dominios = tabla_html((c["parametro"], "Ideal: rp", "No ideal: rp", "Observación"), dominios)
    locales = []
    for s in "RAB":
        for k, r in estudio["sensibilidades"][s].items():
            locales.append((s, k, *["—" if r[n] is None else f"{r[n]:.9g}" for n in
                ("derivada", "normalizada", "paso", "error_estimado")], r["metodo"] or "—", r["motivo"]))
    tabla_local = tabla_html(("Caso", "Y", "dY/dx", "S=(x/Y)dY/dx", "Paso efectivo", "Diferencia h/h2",
                              "Esquema", "Motivo de indisponibilidad"), locales)
    graficas = "".join(imagen_html(imagenes[k], titulo) for k, titulo in (
        ("trabajo_neto", "Trabajo específico neto · R/A/B"),
        ("rendimiento", "Rendimiento térmico · R/A/B"), ("rp", "Relaciones de presiones · R/A/B")))
    tendencias = "".join(f"<li>{escape(t)}</li>" for t in estudio["tendencias"])
    estado_git = {True: "AVISO: cambios locales sin confirmar; el hash no identifica por sí solo este código.",
                  False: "Árbol de trabajo limpio.", None: "Estado local Git no disponible."}[version_git["modificado"]]
    legado = (MARCA_INICIO + f'''<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Brayton Simulator — Análisis de sensibilidad</title><style>
body{{font:16px/1.6 'Segoe UI',Arial,sans-serif;color:#192b3a;background:#edf1f5;margin:0}}
main{{max-width:1200px;margin:30px auto;padding:0 24px}}header{{background:#153c55;color:white;padding:28px;border-radius:10px}}
section{{background:white;padding:24px;margin:24px 0;border-radius:10px}}h1{{line-height:1.2}}
table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{border:1px solid #d4dce3;padding:8px;text-align:left}}
th{{background:#e8eff5}}.table-wrap,.table-container{{overflow-x:auto}}figure{{margin:20px 0}}img{{width:100%;height:auto}}
.warning{{background:#fff3d2;color:#483900;padding:12px}}@media print{{body{{background:white}}main{{margin:0}}section{{padding:8px}}}}
</style></head><body><main><header><h1>Análisis de sensibilidad paramétrica</h1>
<p>Brayton Simulator · OFAT · {escape(str(fecha))}</p>
<p>Commit Git: {escape(version_git['commit'] or 'No disponible')}</p><p class="warning">{estado_git}</p></header>
<section><h2>Configuración y referencia</h2><p>{escape(c['parametro'])} [{escape(c['unidad'])}],
{c['minimo']:.9g} a {c['maximo']:.9g}; {c['muestras']} muestras. Cálculo: {estudio['segundos_calculo']:.3f} s (sin dibujo/publicación).</p>
{referencia}<p>R: rp fija del formulario. A: máximo trabajo específico reajustando rp.
B: máximo interior de rendimiento reajustando rp. Los supremos no alcanzados no son puntos operativos.
Sólo cambia un parámetro físico; cp y gamma permanecen constantes. delta se expresa como fracción.</p>
<p>Candidatos analíticos de Fases 2/3, con dominio y viabilidad comprobados en cada muestra.
Búsqueda independiente en extremos, centro y muestra más próxima a la referencia: índices {escape(str(estudio['indices_verificacion']))} (desde cero).
El método figura por resultado; un fallo numérico no demuestra inviabilidad física.</p></section>
<section><h2>Tres gráficas de sensibilidad</h2>{graficas}<p>NaN interrumpe curvas no disponibles.
La línea gris de consigna rp de referencia no indica viabilidad. Los puntos motores R,
marcados con círculos, y las curvas operativas A/B conservan huecos donde no están disponibles.
Escala simétrica logarítmica indicada cuando difieren mucho las escalas.</p></section>
<section><h2>Resultados y motivos por muestra</h2>{resultados}</section>
<section><h2>Dominios recalculados por muestra</h2>{tabla_dominios}
<p>Intervalo físico abierto: no es la ventana interior de búsqueda ni el rango visual del parámetro.</p></section>
<section><h2>Tendencias muestreadas</h2><ul>{tendencias}</ul></section>
<section><h2>Sensibilidades locales en la referencia</h2><p>Se evalúan en el valor del parámetro del formulario,
incluso si queda fuera del rango dibujado. dY/dx conserva unidades de Y por unidad de x;
η usa fracción y rp es adimensional. Multiplicar dη/dx por 100 da puntos porcentuales por unidad de x.
S interpreta cambios relativos porcentuales pequeños, no puntos porcentuales.
Paso inicial cbrt(epsilon)·max(|x|,1); diferencias centrales o unilaterales de orden 2;
contraste h/h2. Calor próximo a cero, falta de motor y transiciones no dan coeficientes ficticios.</p>{tabla_local}</section>
<section><h2>Limitaciones</h2><p>OFAT es local respecto a los otros parámetros: no mide interacciones ni establece una clasificación
universal. Una malla finita puede omitir regiones estrechas y fronteras entre muestras; no interpolar huecos.
Gas ideal, cp/gamma constantes, equipos adiabáticos y pérdida relativa fija por muestra.
Sin química, caudal, potencia, empuje ni mapa bidimensional. Tolerancias y redondeo limitan máximos degenerados.
Verificación de código y consistencia interna; no validación con datos experimentales externos.</p></section>
</main></body></html>''' + MARCA_FINAL)
    return terminar_informe(legado, estudio["referencia"], imagenes, fecha, version_git, sensibilidad=estudio,
        diagnosticos={'sensibilidad': diagnostico_estudio(estudio, 'sensibilidad')})


def crear_informe_mapa_html(estudio, imagenes, fecha, version_git):
    """Informe 2D con recursos incrustados y resultados previamente calculados."""
    from dashboard import renderizar_dashboard, plegable
    from mapa_diseno import preparar_resultados
    inicio = perf_counter()
    c, resumen = estudio['configuracion'], preparar_resultados(estudio)
    tablas = []
    for fila in estudio['filas']:
        muestra = fila['muestra']
        dominio = muestra['dominios']['noideal']['intervalo'] if muestra['dominios'] else None
        for s in 'AB':
            r = muestra[s]
            tablas.append((f"{fila['T3']:.6g}", s, r['estado'],
                f"{r['rp']:.9g}" if r['rp'] is not None else 'No disponible',
                f"{r['trabajo_neto']:.6f}" if r['trabajo_neto'] is not None else 'No disponible',
                f"{100*r['rendimiento']:.6f}" if r['rendimiento'] is not None else 'No disponible',
                f"{r['calor_aportado']:.6f}" if r['calor_aportado'] is not None else 'No disponible',
                f"{100*r['supremo']['rendimiento']:.6f}" if r['supremo'] else 'No aplicable',
                str(dominio), '; '.join(r['motivos'])))
    botones = ''.join(f'<button type="button" role="tab" id="tab-mapa-{k}" aria-controls="graficas-mapa" data-plot-tab="{k}" aria-selected="false">{t}</button>'
                      for k, t in (('trabajo_neto', 'Trabajo'), ('rendimiento', 'Rendimiento'), ('viabilidad', 'Viabilidad')))
    figuras = ''.join(imagen_html(imagenes[f'mapa_{k}.png'], titulo, EXPLICACIONES_GRAFICAS[f'mapa_{k}.png']).replace('<figure>', f'<figure data-plot-group="{k}">')
                      for k, titulo in (('trabajo_neto', 'Trabajo neto motor [kJ/kg]'),
                                       ('rendimiento', 'Rendimiento térmico motor [%]'), ('viabilidad', 'Viabilidad y fronteras físicas')))
    cortes = ''.join(imagen_html(imagenes[f'corte_{i}.png'], f"Corte T3={fila['T3']:g} K").replace('<figure>', f'<figure data-corte="{i}">')
                     for i, fila in enumerate(estudio['cortes']))
    opciones = ''.join(f'<option value="{i}">{f["T3"]:g} K</option>' for i, f in enumerate(estudio['cortes']))
    unidades = dict(T1='K', p1='kPa', cp='J/(kg·K)', gamma='−', eta_c='fracción', eta_t='fracción', perdida_presion_combustor='fracción')
    fijo = tabla_html(('Parámetro fijo', 'Valor', 'Unidad'), [(k, estudio['referencia'][k], unidades[k]) for k in unidades])
    contexto = (f"Variamos simultáneamente rp de {c['rp_min']:g} a {c['rp_max']:g} y T3 de {c['T3_min']:g} a {c['T3_max']:g} K. "
        'Cada punto representa un ciclo diferente. T1, p1, cp, gamma, eta_c, eta_t y delta permanecen fijos, con los valores de la tabla. '
        'Buscamos comparar regiones motoras y objetivos por temperatura, no una T3 óptima global.')
    observaciones = [f"{resumen['motores']} de {resumen['celdas']} celdas muestreadas cumplen las condiciones motoras; {resumen['limites_numericos']} presentan límites numéricos."]
    disponibles = {s: sum(f['muestra'][s]['estado'] == 'disponible' for f in estudio['filas']) for s in 'AB'}
    observaciones.append(f"Hay máximo A alcanzado en {disponibles['A']} temperaturas y máximo B alcanzado en {disponibles['B']} de las {c['n_T3']} temperaturas de la malla.")
    vacias = sum(f['muestra']['dominios'] is not None and not f['muestra']['dominios']['noideal']['intervalo'] for f in estudio['filas'])
    supremos = sum(f['muestra']['B']['estado'] == 'supremo_no_alcanzado' for f in estudio['filas'])
    if vacias:
        observaciones.append(f'{vacias} temperaturas tienen dominio motor vacío, independientemente de la ventana rp dibujada.')
    if supremos:
        observaciones.append(f'En {supremos} temperaturas, B es un supremo no alcanzado: no existe un ciclo operativo que lo alcance.')
    fuera = sum(r['rp'] is not None and not c['rp_min'] <= r['rp'] <= c['rp_max']
                for f in estudio['filas'] for r in (f['muestra']['A'], f['muestra']['B']))
    if fuera:
        observaciones.append(f'{fuera} máximos A/B calculados quedan fuera de la ventana rp mostrada; el borde de la imagen no los sustituye.')
    contenido = (bloque_educativo('¿Qué estamos modificando y por qué?', contexto)
        + f'<div class="card"><h3>Mapa no ideal rp–T3</h3><p>{resumen["motores"]} / {resumen["celdas"]} celdas motoras; '
        f'{resumen["limites_numericos"]} límites numéricos. {c["n_T3"]} filas T3 × {c["n_rp"]} columnas rp. '
        f'rp: {c["rp_min"]:g}–{c["rp_max"]:g} ({escape(c["escala"])}); T3: {c["T3_min"]:g}–{c["T3_max"]:g} K.</p>'
        f'<p>Cálculo: {estudio["segundos_calculo"]:.3f} s. Cálculo + gráficas: {estudio.get("segundos_preparacion", 0):.3f} s.</p>'
        '<p>Gas ideal, cp/gamma, eficiencias y pérdida relativa constantes; equipos adiabáticos. Sin combustible, caudal, potencia, empuje o tobera. '
        'Verificación interna, no validación experimental. A/B se calculan independientemente de las columnas y pueden quedar fuera de vista. '
        'Los huecos interrumpen las curvas; los cortes no amplían la ventana rp del mapa.</p>' + fijo + '</div>'
        f'<div class="card" data-plot-viewer><div class="plot-tabs" role="tablist" aria-label="Mapas de diseño">{botones}</div><div class="plot-grid" id="graficas-mapa" role="tabpanel">{figuras}</div></div>'
        f'<div class="card"><p class="plot-help">{escape(EXPLICACIONES_GRAFICAS["corte"])}</p><label for="selector-corte">Cortes de T3</label><select id="selector-corte">{opciones}</select>'
        f'<div class="plot-grid" id="cortes-mapa">{cortes}</div></div>'
        + plegable('Resultados principales A/B y dominios',
            bloque_educativo('¿Qué intentamos optimizar?', TEXTO_OPTIMIZACION)
            + bloque_educativo('Máximo, supremo y dominio vacío', TEXTO_DISPONIBILIDAD)
            + tabla_html(('T3 [K]', 'Criterio', 'Estado', 'rp', 'W [kJ/kg]', 'eta [%]', 'Qin [kJ/kg]', 'Supremo no alcanzado [%]', 'Dominio abierto', 'Motivo'), tablas))
        + conclusiones_html(observaciones))
    aviso = {True: 'AVISO: cambios locales sin confirmar', False: 'Árbol de trabajo limpio', None: 'Estado local Git no disponible'}[version_git['modificado']]
    info = f'<div class="card"><h3>Informe actual</h3><p>{escape(fecha.isoformat())}</p><p>Commit Git: {escape(version_git.get("commit") or "No disponible")}</p><p>{aviso}</p><p>Consulta o descarga desde Informes en el servidor local.</p></div>'
    valores = estudio['referencia'].copy(); valores['perdida_presion_combustor'] *= 100
    valores.update({'mapa_' + k: v for k, v in c.items() if k != 'cortes'})
    valores['mapa_cortes'] = ', '.join(str(t) for t in c['cortes'])
    diagnostico = diagnostico_estudio(estudio, 'mapa')
    contenido += renderizar_diagnostico(diagnostico, 'mapa')
    metadata = dict(dashboard=1, tipo='mapa', parametros=estudio['referencia'], mapa=c, fecha=fecha.isoformat(), git=version_git,
                    diagnosticos={'mapa': diagnostico})
    pagina = renderizar_dashboard(valores, contenidos=dict(resultados='', optimizacion='', sensibilidad='', mapa=contenido),
        metadata=metadata, modo_local=False, informe_actual=info, seccion_inicial='mapa')
    estudio['segundos_html'] = perf_counter() - inicio
    return MARCA_INICIO + pagina + MARCA_FINAL


def seccion_segunda_ley_html(estudio):
    """Presentación compacta de resultados calculados y dos SVG autocontenidos."""
    from segunda_ley import crear_graficas_segunda_ley
    figuras = crear_graficas_segunda_ley(estudio)
    contenido = bloque_educativo('¿Por qué generan entropía los equipos reales?',
        'Bajo la hipótesis adiabática y estacionaria, las irreversibilidades del compresor y la turbina aumentan la entropía del fluido. '
        'Se compara el ideal isentrópico con el no ideal usando exactamente sus cuatro estados calculados. s1=0 es una referencia arbitraria, no entropía absoluta.')
    contenido += bloque_educativo('¿Qué significa destruir exergía?',
        f"Con T0={estudio['T0']:g} K, Gouy–Stodola da eD=T0·s_gen: capacidad de producir trabajo útil destruida por irreversibilidad. "
        'T0 sólo cambia esta valoración, no las temperaturas, trabajo, rendimiento u óptimos. La suma cuantificada comprende únicamente compresor y turbina; no es la pérdida total de la instalación ni la diferencia directa de trabajo ideal/no ideal.')
    filas_s, filas_c, filas_camara = [], [], []
    for nombre, d in estudio['modelos'].items():
        modelo = 'Ideal' if nombre == 'ideal' else 'No ideal'
        if 'entropias' in d:
            filas_s.append((modelo, *(f'{x:.8f}' for x in d['entropias'])))
        if d['estado'] not in ('motor', 'diagnostico_no_motor'):
            contenido += bloque_educativo(modelo+': '+d['estado'], d['motivo'])
            continue
        contenido += f'<p><strong>{modelo}:</strong> {escape(d["estado"])}; {escape(", ".join(d["motivos"]) or "sin motivos de exclusión")}.</p>'
        for equipo, c in d['componentes'].items():
            filas_c.append((modelo, equipo, f'{c["valor"]:.8f}', f'{c["exergia_destruida"]:.6f}'))
            if c['bruto'] < 0:
                contenido += f'<p class="muted">{modelo} · {equipo}: s_gen bruta={c["bruto"]:.3g}; cero por redondeo dentro de tolerancia {c["tolerancia"]:.3g} kJ/(kg·K).</p>'
        contenido += f'<p>{modelo} · suma cuantificada de compresor y turbina: <strong>{d["suma_componentes"]:.6f} kJ/kg</strong>.</p>'
        camara = d['camara']
        filas_camara.append((modelo, *(f'{camara[k]:.8f}' for k in ('termica', 'presion', 'total'))))
    contenido += tabla_html(('Modelo', 's1', 's2', 's3', 's4 [kJ/(kg·K)]'), filas_s)
    contenido += tabla_html(('Modelo', 'Equipo', 's_gen [kJ/(kg·K)]', 'eD [kJ/kg]'), filas_c)
    contenido += '<div class="plot-grid">' + ''.join(
        f'<figure data-segunda-ley="{nombre}">{svg}<figcaption>{texto}</figcaption></figure>'
        for nombre, svg, texto in (('estados_ts', figuras['estados_ts'], 'Estados T-s: conexiones discontinuas sólo como guía visual; no describen procesos irreversibles internos.'),
                                   ('exergia_componentes', figuras['exergia_componentes'], 'Destrucción de exergía específica de los dos equipos adiabáticos; la suma se indica separadamente.'))) + '</div>'
    contenido += bloque_educativo('¿Por qué no calculamos todavía todas las pérdidas del ciclo?',
        's3−s2 es el incremento de entropía del fluido en el aporte de calor; se descompone en contribuciones de temperatura y presión. '
        'No es la generación de entropía de la cámara: falta la entropía transferida con el calor, sus temperaturas de frontera o un modelo de combustión. '
        'No calculamos una eficiencia exergética global.')
    from dashboard import plegable
    contenido += plegable('Cambio de entropía del fluido 2→3 [kJ/(kg·K)]',
        tabla_html(('Modelo', 'Temperatura', 'Presión', 'Cambio total del fluido'), filas_camara))
    return contenido


def crear_informe_segunda_ley_html(parametros, estudio, fecha, version):
    """Informe diagnóstico o de actualización T0; sin simulación normal adicional."""
    from dashboard import renderizar_dashboard, parametros_fijos_texto
    paneles = dict(resultados='', optimizacion='', sensibilidad='', segunda_ley=bloque_educativo('Parámetros del caso', parametros_fijos_texto(parametros, ())) + seccion_segunda_ley_html(estudio))
    diagnostico = diagnostico_segunda_ley(parametros, estudio)
    paneles['segunda_ley'] += renderizar_diagnostico(diagnostico, 'segunda_ley')
    valores = parametros.copy(); valores['perdida_presion_combustor'] *= 100; valores['T0'] = estudio['T0']
    metadata = dict(dashboard=1, tipo='segunda_ley', parametros=parametros, segunda_ley=estudio,
                    fecha=fecha.isoformat(), git=version, diagnosticos={'segunda_ley': diagnostico})
    aviso = {True:'Cambios locales sin confirmar', False:'Árbol de trabajo limpio', None:'Estado Git no disponible'}[version['modificado']]
    info = f'<div class="card"><p>{escape(fecha.isoformat())} · Commit Git: {escape(version.get("commit") or "No disponible")} · {aviso}</p></div>'
    return MARCA_INICIO + renderizar_dashboard(valores, contenidos=paneles, metadata=metadata,
        modo_local=False, informe_actual=info, seccion_inicial='segunda_ley') + MARCA_FINAL


def obtener_version_git(carpeta):
    """Consulta HEAD y cambios locales sin modificar el repositorio."""
    try:
        commit = subprocess.run(
            ["git", "-C", str(carpeta), "rev-parse", "--verify", "HEAD"],
            capture_output=True, text=True, check=True, timeout=5,
        ).stdout.strip()
        estado = subprocess.run(
            ["git", "-C", str(carpeta), "status", "--porcelain", "--untracked-files=normal"],
            capture_output=True, text=True, check=True, timeout=5,
        ).stdout
        return {"commit": commit, "modificado": bool(estado.strip())}
    except (OSError, subprocess.SubprocessError):
        # Una copia sin Git sigue pudiendo generar resultados; no se asume limpia.
        return {"commit": None, "modificado": None}


def tabla_html(encabezados, filas):
    """Convierte encabezados y filas de valores ya formateados en una tabla."""
    cabecera = "".join(f"<th scope='col'>{escape(str(valor))}</th>" for valor in encabezados)
    cuerpo = "".join(
        "<tr>" + "".join(f"<td>{escape(str(valor))}</td>" for valor in fila) + "</tr>"
        for fila in filas
    )
    return f"<div class='table-wrap'><table><thead><tr>{cabecera}</tr></thead><tbody>{cuerpo}</tbody></table></div>"


def imagen_html(imagen, titulo, explicacion=None):
    """Incorpora los bytes PNG de esta ejecución como una URL de datos Base64."""
    if not imagen.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("La gráfica debe contener una imagen PNG válida.")
    contenido = b64encode(imagen).decode("ascii")
    etiqueta = escape(titulo)
    ayuda = f'<p class="plot-help">{escape(explicacion)}</p>' if explicacion else ''
    return (
        f"<figure><img src='data:image/png;base64,{contenido}' alt='{etiqueta}'>"
        f"<figcaption>{etiqueta}</figcaption>{ayuda}</figure>"
    )


def seccion_optimizacion_html(parametros, referencias, optimizaciones, barrido):
    """Presenta resultados ya calculados; None se muestra como no disponible."""
    tablas = []
    for nombre in ("ideal", "noideal"):
        r = optimizaciones[nombre]
        tablas.append(f"<h3>Modelo {nombre}</h3><p>{escape(r['motivo'])}</p>")
        if r["estado"] != "disponible":
            tablas.append("<p>Óptimo motor: No disponible. No se ejecuta una búsqueda en un dominio vacío.</p>")
            continue
        a, n, c = r["analitico"], r["numerico"], r["concordancia"]
        lo, hi = r["dominio"]["intervalo"]
        filas = [
            ("Relación de presiones de referencia", f"{parametros['relacion_presiones']:.10g}", "—"),
            ("Trabajo neto de referencia", f"{referencias[nombre]['trabajo_neto']:.6f}", "kJ/kg"),
            ("rp de máximo trabajo · analítica", f"{a['rp']:.10f}", "—"),
            ("rp de máximo trabajo · numérica", f"{n['rp']:.10f}", "—"),
            ("Trabajo máximo · analítico", f"{a['ciclo']['trabajo_neto']:.6f}", "kJ/kg"),
            ("Trabajo máximo · numérico", f"{n['ciclo']['trabajo_neto']:.6f}", "kJ/kg"),
            ("Rendimiento EN el máximo de trabajo", f"{a['ciclo']['rendimiento'] * 100:.6f}", "%"),
            ("Dominio físico abierto", f"{lo:.10g} < rp < {hi:.10g}", "—"),
            ("Intervalo de optimización numérica", f"{n['intervalo_busqueda'][0]:.10g} a {n['intervalo_busqueda'][1]:.10g}", "—"),
            ("Intervalo final del refinamiento", f"{n['intervalo_final'][0]:.10g} a {n['intervalo_final'][1]:.10g}", "—"),
            ("Muestras iniciales / evaluaciones totales", f"{n['muestras_iniciales']} / {n['evaluaciones']}", "—"),
            ("Paso logarítmico inicial", f"{n['paso_log_inicial']:.6g}", "—"),
            ("Tolerancia de parada en log(rp)", f"{n['tolerancia_log']:.3g}", "—"),
            ("Escala de resolución numérica en rp", f"{n['resolucion_rp']:.6g}", "—"),
            ("Diferencia absoluta en rp / tolerancia", f"{c['diferencia_rp']:.6g} / {c['tolerancia_rp']:.6g}", "—"),
            ("Diferencia absoluta en trabajo / tolerancia", f"{c['diferencia_trabajo']:.6g} / {c['tolerancia_trabajo']:.6g}", "kJ/kg"),
        ]
        tablas.append(tabla_html(("Magnitud", "Resultado", "Unidad"), filas))
        if nombre == "noideal":
            tablas.append("<h3>Estados del ciclo no ideal en el máximo de trabajo</h3>")
            tablas.append(tabla_html(("Estado", "T [K]", "p [kPa]"), [
                (i, f"{T:.6f}", f"{p:.6f}") for i, (T, p) in enumerate(zip(
                    a["ciclo"]["temperaturas"], a["ciclo"]["presiones"]), start=1)]))
    ideal, real = optimizaciones["ideal"], optimizaciones["noideal"]
    if ideal["estado"] == real["estado"] == "disponible":
        ai, ar = ideal["analitico"], real["analitico"]
        tablas.append(tabla_html(("Comparación (ideal menos no ideal)", "Diferencia", "Unidad"), [
            ("Relaciones de máximo trabajo", f"{ai['rp'] - ar['rp']:.10f}", "—"),
            ("Trabajos máximos", f"{ai['ciclo']['trabajo_neto'] - ar['ciclo']['trabajo_neto']:.6f}", "kJ/kg")]))
    if barrido is not None:
        lo, hi = barrido["intervalo_visual"]
        tablas.append(f"<p>Ventana gráfica completa: {lo:.10g} a {hi:.10g}; {len(barrido['relaciones'])} muestras compartidas. "
                      "Incluye fronteras y óptimos; las comparaciones añaden un panel de detalle no ideal "
                      "cuando la amplitud logarítmica o el trabajo máximo difieren mucho.</p>")
    return ("<section><h2>Optimización del trabajo específico neto</h2>"
            "<p>Se maximiza trabajo específico a parámetros fijos, NO rendimiento térmico. "
            "Se distingue candidato estacionario matemático de máximo motor interior. "
            "La segunda derivada en x=rp^a es negativa; si existe dominio motor, "
            "el candidato pertenece a su interior. La búsqueda independiente usa malla logarítmica "
            "y sección áurea dentro de ese dominio, sin usar el candidato analítico para acotarla.</p>"
            "<p>La resolución inicial, el criterio de parada y la precisión en rp son distintos: "
            "cerca del máximo el trabajo es plano y el redondeo impide atribuir al resultado "
            "tantos dígitos fiables como su estrecho intervalo final. Las tolerancias son numéricas, "
            "no incertidumbre experimental.</p>" + "".join(tablas) + "</section>")


def seccion_rendimiento_html(estudios, comparacion):
    """Presenta máximos, supremos y comparación A/B ya calculados; sin física nueva."""
    partes = ["<section><h2>Optimización del rendimiento térmico</h2>"]
    for nombre in ("ideal", "noideal"):
        r = estudios[nombre]
        partes.append(f"<h3>Rendimiento {nombre}</h3><p>{escape(r['motivo'])}</p>")
        if r["estado"] == "supremo_no_alcanzado":
            limite = r["supremo"]
            partes.append(f"<p>Supremo no alcanzado: {limite['rendimiento']*100:.6f} %. "
                          f"Se aproxima cuando rp tiende a {limite['rp_frontera']:.10g} por la izquierda. "
                          "La frontera no es un punto motor; qin y trabajo se anulan. No existe máximo interior ni punto B.</p>")
        elif r["estado"] == "sin_dominio":
            partes.append("<p>Máximo de rendimiento: No disponible. Dominio motor vacío.</p>")
        elif r["estado"] == "maximo_interior":
            a, n, c = r["analitico"], r["numerico"], r["concordancia"]
            filas = [("rp de máximo rendimiento · analítica", f"{a['rp']:.10f}", "—"),
                     ("rp de máximo rendimiento · numérica", f"{n['rp']:.10f}", "—"),
                     ("Rendimiento máximo", f"{a['ciclo']['rendimiento']*100:.6f}", "%"),
                     ("Rendimiento máximo · numérico", f"{n['ciclo']['rendimiento']*100:.6f}", "%"),
                     ("Trabajo en el máximo rendimiento", f"{a['ciclo']['trabajo_neto']:.6f}", "kJ/kg"),
                     ("Calor en el máximo rendimiento", f"{a['ciclo']['calor_aportado']:.6f}", "kJ/kg"),
                     ("Intervalo físico abierto", f"{r['dominio']['intervalo'][0]:.10g} < rp < {r['dominio']['intervalo'][1]:.10g}", "—"),
                     ("Ventana numérica de rendimiento", f"{n['intervalo_busqueda'][0]:.10g} a {n['intervalo_busqueda'][1]:.10g}", "—"),
                     ("Diferencia rp / tolerancia", f"{c['diferencia_rp']:.6g} / {c['tolerancia_rp']:.6g}", "—"),
                     ("Diferencia rendimiento / tolerancia", f"{c['diferencia_rendimiento']:.6g} / {c['tolerancia_rendimiento']:.6g}", "fracción"),
                     ("Evaluaciones / iteraciones", f"{n['evaluaciones']} / {n['iteraciones']}", "—"),
                     ("Paso inicial / parada en ln(rp)", f"{n['paso_log_inicial']:.6g} / {n['tolerancia_log']:.6g}", "—"),
                     ("Escala de resolución en rp", f"{n['resolucion_rp']:.6g}", "—")]
            partes.append(tabla_html(("Magnitud", "Resultado", "Unidad"), filas))
            partes.append(tabla_html(("Estado en B", "T [K]", "p [kPa]"), [
                (i,f"{T:.6f}",f"{p:.6f}") for i,(T,p) in enumerate(zip(
                    a["ciclo"]["temperaturas"],a["ciclo"]["presiones"]),start=1)]))
    partes.append("<h3>Dos decisiones de diseño: A y B</h3>")
    filas=[]
    for clave, etiqueta in (("punto_a","A · Máximo trabajo"),("punto_b","B · Máximo rendimiento")):
        p=comparacion[clave]
        if p is not None:
            c=p["ciclo"]
            filas.append((etiqueta,f"{p['rp']:.10f}",f"{c['trabajo_neto']:.6f}",
                          f"{c['rendimiento']*100:.6f}",f"{c['calor_aportado']:.6f}"))
        else:
            filas.append((etiqueta,"No disponible","—","—","—"))
    partes.append(tabla_html(("Criterio","rp","Trabajo [kJ/kg]","Rendimiento [%]","Calor [kJ/kg]"),filas))
    if comparacion["estado"] == "disponible":
        partes.append(tabla_html(("Comparación B respecto a A","Valor","Unidad"),[
            ("Diferencia de relaciones rp (B−A)",f"{comparacion['diferencia_rp']:.10f}","—"),
            ("Ganancia de rendimiento",f"{comparacion['ganancia_rendimiento_pp']:.6f}","puntos porcentuales"),
            ("Reducción relativa de trabajo respecto a A",f"{comparacion['reduccion_trabajo_porcentaje']:.6f}","%"),
            ("Diferencia de calor aportado (B−A)",f"{comparacion['diferencia_calor']:.6f}","kJ/kg")]))
    else:
        partes.append(f"<p>{escape(comparacion['motivo'])}</p>")
    partes.append("<p>El máximo rendimiento puede entregar menos trabajo específico: cada criterio responde a una decisión distinta. "
                  "Círculo azul: máximo trabajo ideal; rombo naranja: A, máximo trabajo no ideal; estrella verde: B, máximo rendimiento no ideal. "
                  "El ideal tiene un supremo, sin marcador de máximo rendimiento. Las fronteras discontinuas delimitan dominios abiertos.</p>"
                  "<p>Modelo educativo con cp/gamma, eficiencias y pérdida fijas. No es un modelo de motor real de alta fidelidad. "
                  "Malla inicial, parada y precisión efectiva son distintas; un cociente con calor muy pequeño amplifica el redondeo. "
                  "La clasificación de Fase 1 excluye su banda cero y los fallos numéricos se notifican; la concordancia no constituye validación experimental.</p></section>")
    return "".join(partes)


def crear_informe_html(parametros, ideal, noideal, detalles_ideal, optimo,
                       rendimientos, comprobaciones, imagenes, fecha, version, barrido=None,
                       optimizaciones=None, *, estudio_rendimiento=None, comparacion_criterios=None, segunda_ley=None):
    """Presenta resultados y seis PNG suministrados por main, sin recalcular física."""
    base = {"rendimiento_brayton.png", "diagrama_ts_brayton.png", "diagrama_pv_brayton.png",
            "trabajo_neto_vs_rp.png", "comparacion_ideal_noideal.png", "trabajo_neto_ideal_noideal.png"}
    esperadas = base | ({"compromiso_trabajo_rendimiento.png"} if estudio_rendimiento is not None else set())
    if set(imagenes) != esperadas:
        raise ValueError("El informe requiere las seis gráficas originales y, con Fase 3, la gráfica de compromiso.")
    filas_parametros = [
        ("T1 · Entrada del compresor", f"{parametros['T1']:.2f}", "K"),
        ("T3 · Entrada de la turbina", f"{parametros['T3']:.2f}", "K"),
        ("cp", f"{parametros['cp']:.2f}", "J/(kg·K)"),
        ("gamma = cp/cv", f"{parametros['gamma']:.4f}", "—"),
        ("Relación de presiones del compresor", f"{parametros['relacion_presiones']:.4f}", "—"),
        ("p1 · Presión inicial", f"{parametros['p1']:.2f}", "kPa"),
        ("Eficiencia isentrópica del compresor", f"{parametros['eta_c']:.4f}", "—"),
        ("Eficiencia isentrópica de la turbina", f"{parametros['eta_t']:.4f}", "—"),
        ("Pérdida relativa de presión del combustor", f"{parametros['perdida_presion_combustor']:.4f}", "fracción"),
        ("Pérdida de presión del combustor", f"{parametros['perdida_presion_combustor'] * 100:.2f}", "%"),
    ]
    estados_ideal = [
        (i, f"{T:.2f}", f"{p:.2f}", f"{v:.6f}", f"{s:.6f}")
        for i, (T, p, v, s) in enumerate(zip(
            ideal["temperaturas"], ideal["presiones"],
            detalles_ideal["volumenes"], detalles_ideal["entropias"]
        ), start=1)
    ]
    estados_noideal = [
        (i, f"{T:.2f}", f"{p:.2f}")
        for i, (T, p) in enumerate(zip(noideal["temperaturas"], noideal["presiones"]), start=1)
    ]
    magnitudes = (
        ("Trabajo del compresor (consumo)", "trabajo_compresor", 1, "kJ/kg"),
        ("Trabajo de la turbina (producción)", "trabajo_turbina", 1, "kJ/kg"),
        ("Trabajo neto", "trabajo_neto", 1, "kJ/kg"),
        ("Calor aportado", "calor_aportado", 1, "kJ/kg"),
        ("Rendimiento térmico", "rendimiento", 100, "%"),
        ("Back work ratio", "back_work_ratio", 1, "—"),
    )
    balance_ideal = [(nombre, f"{ideal[clave] * factor:.6f}", unidad)
                     for nombre, clave, factor, unidad in magnitudes]
    balance_noideal = [(nombre, f"{noideal[clave] * factor:.6f}", unidad)
                       for nombre, clave, factor, unidad in magnitudes]
    comparacion = [(nombre, f"{ideal[clave] * factor:.6f}",
                    f"{noideal[clave] * factor:.6f}", unidad)
                   for nombre, clave, factor, unidad in magnitudes]
    referencias = [(nombre, f"{ideal[clave]:.6f}", f"{noideal[clave]:.6f}", "K")
                   for nombre, clave in (("T2s", "T2s"), ("T4s", "T4s"))]
    comparacion_estados = [
        (f"T{i} [K]", f"{Ti:.2f}", f"{Tr:.2f}")
        for i, (Ti, Tr) in enumerate(zip(ideal["temperaturas"], noideal["temperaturas"]), start=1)
    ] + [
        (f"p{i} [kPa]", f"{pi:.2f}", f"{pr:.2f}")
        for i, (pi, pr) in enumerate(zip(ideal["presiones"], noideal["presiones"]), start=1)
    ]
    filas_optimo = [
        ("Relación de presiones óptima analítica", f"{optimo['rp_analitica']:.6f}", "—"),
        ("Relación de presiones óptima numérica", f"{optimo['rp_numerica']:.6f}", "—"),
        ("Escala de resolución numérica en rp", f"{optimo['paso']:.7f}", "—"),
        ("Trabajo neto máximo analítico", f"{optimo['trabajo_analitico']:.6f}", "kJ/kg"),
        ("Trabajo neto máximo numérico", f"{optimo['trabajo_numerico']:.6f}", "kJ/kg"),
        ("T2 en el óptimo analítico", f"{optimo['temperaturas'][1]:.2f}", "K"),
        ("T4 en el óptimo analítico", f"{optimo['temperaturas'][3]:.2f}", "K"),
        ("Rendimiento en el óptimo analítico", f"{optimo['rendimiento'] * 100:.6f}", "%"),
    ]
    unidades = ("Magnitud", "Valor", "Unidad")
    lista_comprobaciones = "".join(f"<li>{escape(texto)}</li>" for texto in comprobaciones)
    fecha_texto = escape(fecha.strftime("%d/%m/%Y · %H:%M:%S %z"))
    commit_texto = escape(version["commit"] or "No disponible")
    if version["modificado"] is True:
        estado_version = "Cambios sin confirmar: esta ejecución incluye modificaciones locales o archivos sin seguimiento. El commit identifica la base, no una versión exacta reproducible de estos resultados."
    elif version["modificado"] is False:
        estado_version = "Árbol de trabajo limpio: sin cambios pendientes ni archivos sin seguimiento detectados por Git."
    else:
        estado_version = "Estado Git no disponible: no se ha podido verificar el commit o los cambios locales."
    dominio_html = ""
    if barrido is not None:
        filas = []
        conteos = []
        for nombre in ("ideal", "noideal"):
            d = barrido["dominios"][nombre]
            intervalo = d["intervalo"]
            motor = (f"{intervalo[0]:.10g} < rp < {intervalo[1]:.10g}"
                     if intervalo else "Vacío")
            raices = ", ".join(f"{rp:.10g}" for rp in d["trabajo"]) or "Sin raíces distintas"
            filas.append((nombre, motor, f"rp > {d['expansion']:.10g}",
                          f"rp < {d['calor']:.10g}", raices, "Motor viable"))
            motivos = barrido[nombre]["motivos"]
            conteos.append((nombre, int(barrido[nombre]["viable"].sum()),
                            *(sum(c in fallos for fallos in motivos)
                              for c in ("compresion", "expansion", "calor_aportado", "trabajo_neto"))))
        dominio_html = "<section><h2>Dominio físicamente viable</h2>" + (
            "<p>Se exige compresión rp &gt; 1, expansión p3 &gt; p4, aporte de calor "
            "T3 &gt; T2 y trabajo neto wt &gt; wc. Las fronteras no son puntos motores. "
            "En el ideal: 1 &lt; rp &lt; (T3/T1)^(gamma/(gamma−1)). "
            "Calor positivo no garantiza que la turbina cubra el consumo del compresor.</p>"
        ) + tabla_html(("Modelo", "Intervalo motor abierto", "Expansión", "Calor positivo",
                        "Fronteras wn = 0", "Caso de referencia"), filas) + (
            "<p>En el no ideal, con x=rp^a, h=(T3/T1) eta_c eta_t y k=(1−delta)^(−a), "
            "wn &gt; 0 equivale a Q(x)=(x−1)(x−h)+h(k−1) &lt; 0. "
            "La cuadrática convexa demuestra que el dominio es un intervalo abierto o vacío. "
            "Se localizan las raíces por bisección (tolerancia relativa en x: 1e−12). "
            "Esto localiza fronteras; no optimiza el modelo no ideal.</p>"
            "<p>La clasificación excluye una banda relativa de 1e−10 alrededor del cero "
            "en cada condición, escalada en sus propias unidades. Es una precaución de "
            "redondeo, no incertidumbre experimental ni cambio de las ecuaciones.</p>"
        ) + tabla_html(("Modelo", "Puntos motores", "Sin compresión", "Sin expansión",
                        "Calor no positivo", "Trabajo no positivo"), conteos) + (
            f"<p>Malla representada: {len(barrido['relaciones'])} puntos entre rp = "
            f"{barrido['relaciones'][0]:.10g} y {barrido['relaciones'][-1]:.10g}. "
            "Combina muestreo lineal y logarítmico, fronteras y sus vecindades; "
            "la ventana se adapta al dominio completo sin un recorte fijo de rp. "
            "Las fronteras de la tabla se calculan independientemente del dibujo. "
            "Los motivos pueden solaparse: sus recuentos no deben sumarse. "
            "NaN corta las curvas en puntos excluidos; nunca se publica rendimiento motor allí. "
            "Las bandas tenues y líneas discontinuas indican los dominios y sus fronteras.</p></section>"
        )
    intervalo_busqueda = optimo.get("intervalo_busqueda", (1.01, 50))
    optimizacion_html = (seccion_optimizacion_html(parametros, {"ideal": ideal, "noideal": noideal},
                                                   optimizaciones, barrido)
                         if optimizaciones is not None else "")
    rendimiento_html = ""
    if estudio_rendimiento is not None:
        rendimiento_html = seccion_rendimiento_html(estudio_rendimiento, comparacion_criterios)
        rendimiento_html += imagen_html(imagenes["compromiso_trabajo_rendimiento.png"],
            "Compromiso no ideal: trabajo específico neto frente a rendimiento; rp es el parámetro. No toda la curva es frontera de Pareto.")
    legado = f"""{MARCA_INICIO}
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Brayton Simulator · {fecha_texto}</title>
<style>
:root {{ color-scheme: light; font-family: 'Segoe UI', Arial, sans-serif; color: #192b3a; background: #edf1f5; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; line-height: 1.6; }}
main {{ max-width: 1120px; margin: 32px auto; padding: 0 24px; }}
header {{ padding: 30px 36px; background: #153c55; color: white; border-radius: 10px; }}
header p {{ margin: 4px 0; }}
header code {{ overflow-wrap: anywhere; }}
.version-warning {{ margin-top: 12px; padding: 10px 14px; background: #fff1cf; color: #624400; border-radius: 4px; }}
h1 {{ margin: 0 0 8px; font-size: 2rem; }}
h2 {{ margin: 0 0 16px; font-size: 1.4rem; color: #153c55; }}
h3 {{ font-size: 1.05rem; margin-top: 24px; }}
section {{ margin-top: 24px; padding: 28px 32px; background: white; border: 1px solid #d7e0e7; border-radius: 10px; }}
.note {{ color: #475969; }}
.status {{ display: inline-block; margin-top: 14px; padding: 3px 12px; background: #dff2e7; color: #185639; border-radius: 4px; }}
.table-wrap {{ overflow-x: auto; margin: 14px 0 22px; }}
table {{ width: 100%; border-collapse: collapse; font-size: .95rem; font-variant-numeric: tabular-nums; }}
th, td {{ padding: 10px 13px; text-align: right; border-bottom: 1px solid #dde5ec; white-space: nowrap; }}
th {{ background: #eaf0f5; color: #153c55; }}
th:first-child, td:first-child {{ text-align: left; white-space: normal; }}
tbody tr:nth-child(even) {{ background: #f7f9fb; }}
figure {{ margin: 24px 0 12px; }}
img {{ display: block; width: 100%; max-width: 950px; height: auto; margin: auto; }}
figcaption {{ text-align: center; font-size: .9rem; color: #475969; }}
li {{ margin: 8px 0; }}
footer {{ padding: 24px 0; font-size: .85rem; color: #475969; }}
@media (max-width: 600px) {{ main {{ margin: 12px auto; padding: 0 10px; }} header, section {{ padding: 20px 16px; }} h1 {{ font-size: 1.6rem; }} }}
@media print {{ body {{ background: white; }} main {{ margin: 0; max-width: none; }} section {{ break-inside: auto; }} figure {{ break-inside: avoid; }} }}
</style>
</head>
<body><main>
<header><h1>Brayton Simulator</h1><p>Informe de resultados · {fecha_texto}</p>
<p>Commit Git: <code>{commit_texto}</code></p>
<p class="{'version-warning' if version['modificado'] is not False else 'version'}">{estado_version}</p>
<span class="status">Ejecución completada · {len(imagenes)} gráficas incorporadas</span></header>
<section><h2>Parámetros de la ejecución</h2>
<p class="note">Modelo educativo de gas ideal con cp y gamma constantes. Equipos adiabáticos en régimen estacionario; se desprecian cambios de energía cinética y potencial. No es un modelo de motor real de alta fidelidad.</p>
{tabla_html(unidades, filas_parametros)}</section>
{dominio_html}
{optimizacion_html}
{rendimiento_html}
<section><h2>Ciclo ideal · caso de referencia</h2>
<p>Estados: 1 entrada del compresor, 2 salida del compresor, 3 entrada de turbina y 4 salida de turbina. La entropía es relativa, con s1 = 0.</p>
{tabla_html(("Estado", "T [K]", "p [kPa]", "v [m³/kg]", "s [kJ/(kg·K)]"), estados_ideal)}
{tabla_html(unidades, balance_ideal)}
<p>Constante específica R: {detalles_ideal['R']:.6f} J/(kg·K).</p>
<p>Rendimiento por fórmula ideal: {detalles_ideal['rendimiento_formula'] * 100:.6f} %. Rendimiento por balance: {ideal['rendimiento'] * 100:.6f} %.</p>
<p>Incremento de entropía 2→3: {detalles_ideal['incremento_23']:.6f} kJ/(kg·K). Incremento 1→4: {detalles_ideal['incremento_14']:.6f} kJ/(kg·K).</p>
<h3>Rendimiento ideal frente a relación de presiones</h3>
{tabla_html(("Relación de presiones", "Rendimiento ideal [%]"), [(rp, f"{eta:.2f}" if eta is not None else "Fuera del dominio motor") for rp, eta in rendimientos])}
{imagen_html(imagenes['rendimiento_brayton.png'], 'Rendimiento exclusivamente ideal · dominio motor, eje rp logarítmico')}</section>
<section><h2>Diagramas termodinámicos exclusivamente ideales</h2>
{imagen_html(imagenes['diagrama_ts_brayton.png'], 'Diagrama T-s del ciclo ideal de referencia')}
{imagen_html(imagenes['diagrama_pv_brayton.png'], 'Diagrama P-v del ciclo ideal de referencia')}</section>
<section><h2>Trabajo ideal y comprobación de su máximo</h2>
<p>Máximo de trabajo específico neto a temperaturas extremas fijas. No es una maximización del rendimiento. Búsqueda numérica adaptada entre rp = {intervalo_busqueda[0]:.10g} y {intervalo_busqueda[1]:.10g}. Este intervalo de búsqueda y el intervalo representado son distintos del límite físico.</p>
{tabla_html(unidades, filas_optimo)}
{imagen_html(imagenes['trabajo_neto_vs_rp.png'], 'Trabajo neto ideal y máximo analítico contrastado con la malla numérica')}</section>
<section><h2>Ciclo no ideal · caso de referencia</h2>
<p>Eficiencias isentrópicas de compresor y turbina y pérdida de presión del combustor. No se calculan entropías ni volúmenes no ideales en este informe.</p>
{tabla_html(("Estado", "T [K]", "p [kPa]"), estados_noideal)}
<p>Referencias isentrópicas: T2s = {noideal['T2s']:.6f} K; T4s = {noideal['T4s']:.6f} K. T4s utiliza la presión real de entrada de la turbina tras la pérdida del combustor.</p>
{tabla_html(unidades, balance_noideal)}</section>
<section><h2>Comparación del ciclo ideal y no ideal</h2>
{tabla_html(("Magnitud", "Ideal", "No ideal"), comparacion_estados)}
{tabla_html(("Referencia", "Ideal", "No ideal", "Unidad"), referencias)}
{tabla_html(("Magnitud", "Ideal", "No ideal", "Unidad"), comparacion)}
<p>Ambas curvas usan la misma malla adaptada y los parámetros de esta ejecución; sólo se dibuja el interior motor de cada modelo.</p>
{imagen_html(imagenes['comparacion_ideal_noideal.png'], 'Rendimiento térmico · comparación ideal / no ideal')}
{imagen_html(imagenes['trabajo_neto_ideal_noideal.png'], 'Trabajo específico neto · comparación ideal / no ideal')}</section>
<section><h2>Comprobaciones ejecutadas</h2><ul>{lista_comprobaciones}</ul>
<p class="note">Registro de controles de esta ejecución. Los residuos del caso se presentan en Diagnóstico y coherencia física. Las baterías históricas V.1–V.5 no se ejecutan al generar este informe.</p>
<p class="note">Estas comprobaciones verifican coherencia del código y del modelo; no constituyen validación frente a datos experimentales externos.</p></section>
<footer>Informe autocontenido: HTML, CSS y {len(imagenes)} imágenes PNG Base64. No necesita Internet ni archivos de imagen externos. Las energías son específicas (kJ/kg), no potencias.</footer>
</main></body></html>
{MARCA_FINAL}"""
    return terminar_informe(legado, parametros, imagenes, fecha, version, noideal=noideal,
        barrido=barrido, optimizaciones=optimizaciones, estudio_rendimiento=estudio_rendimiento,
        comparacion=comparacion_criterios, segunda_ley=segunda_ley,
        diagnosticos={'resultados': diagnostico_simulacion(parametros, ideal, noideal, segunda_ley),
                      'optimizacion': diagnostico_optimos(parametros, optimizaciones, estudio_rendimiento),
                      **({'segunda_ley': diagnostico_segunda_ley(parametros, segunda_ley)} if segunda_ley else {})})


def guardar_informe_html(contenido, carpeta, fecha):
    """Publica un HTML completo y después conserva los cuatro informes propios recientes."""
    if not contenido.startswith(MARCA_INICIO) or not contenido.endswith(MARCA_FINAL):
        raise ValueError("El informe no contiene las marcas de documento completo.")
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = f"brayton_{fecha.strftime('%Y-%m-%d_%H-%M-%S-%f')}_{uuid4().hex}.html"
    ruta = carpeta / nombre
    temporal = carpeta / f".{nombre}.tmp"
    # 'x' evita sobrescribir incluso el temporal de otra ejecución.
    archivo = temporal.open("x", encoding="utf-8")
    try:
        with archivo:
            archivo.write(contenido)
        if ruta.exists():
            raise FileExistsError(f"Ya existe el destino del informe: {ruta}")
        # En Windows rename falla si el destino existe: no lo reemplaza.
        temporal.rename(ruta)
    finally:
        temporal.unlink(missing_ok=True)

    # La limpieza solo se alcanza tras publicar correctamente el informe completo.
    # Si la limpieza no es posible, el informe sigue siendo válido y se avisa.
    try:
        informes = []
        for candidato in carpeta.iterdir():
            if (PATRON_INFORME.fullmatch(candidato.name) and not candidato.is_symlink()
                    and candidato.is_file()):
                try:
                    texto = candidato.read_text(encoding="utf-8")
                except UnicodeError:
                    continue  # Un archivo ajeno o ilegible no es un informe propio.
                if texto.startswith(MARCA_INICIO) and texto.endswith(MARCA_FINAL):
                    informes.append(candidato)
        # mtime refleja la finalización de escritura, no el inicio de los cálculos.
        informes.sort(key=lambda archivo: (archivo.stat().st_mtime_ns, archivo.name), reverse=True)
        for antiguo in informes[4:]:
            antiguo.unlink()
    except (OSError, UnicodeError) as error:
        warn(f"Informe guardado en {ruta}; no se pudo completar la conservación de cuatro informes: {error}")
    return ruta
