"""Mapa no ideal: filas T3, columnas rp; reutiliza la física de Fases 1–4."""
from datetime import datetime
from pathlib import Path
from time import perf_counter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

from sensibilidad import argumentos_fisicos, evaluar_muestra
from viabilidad import ErrorNumerico, evaluar_punto, validar_parametros

MAX_CELDAS = 20000


def validar_configuracion(referencia, rp_min=1., rp_max=100., T3_min=600., T3_max=2000.,
                          n_rp=100, n_T3=80, escala='log', cortes=()):
    """Valida configuración, no exige que las celdas sean motores."""
    validar_parametros(*argumentos_fisicos(referencia))
    if not all(np.isfinite(v) for v in (rp_min, rp_max, T3_min, T3_max)):
        raise ValueError('Los límites deben ser finitos.')
    if not 0 < rp_min < rp_max or not referencia['T1'] < T3_min < T3_max:
        raise ValueError('Se requiere 0 < rp mínima < máxima y T1 < T3 mínima < máxima; ninguna T3 puede ser <= T1.')
    if any(isinstance(n, bool) or not isinstance(n, int) or not 3 <= n <= 401 for n in (n_rp, n_T3)):
        raise ValueError('Cada resolución debe ser un entero entre 3 y 401.')
    if n_rp * n_T3 > MAX_CELDAS:
        raise ValueError(f'El mapa admite como máximo {MAX_CELDAS} celdas.')
    if escala not in ('lineal', 'log'):
        raise ValueError('La escala rp debe ser lineal o log.')
    cortes = tuple(float(t) for t in cortes) or (T3_min, (T3_min + T3_max)/2, T3_max)
    if len(cortes) > 5 or any(not np.isfinite(t) or not T3_min <= t <= T3_max for t in cortes):
        raise ValueError('Selecciona de uno a cinco cortes T3 dentro del rango.')
    return dict(rp_min=float(rp_min), rp_max=float(rp_max), T3_min=float(T3_min),
                T3_max=float(T3_max), n_rp=n_rp, n_T3=n_T3, escala=escala,
                cortes=tuple(dict.fromkeys(cortes)))


def crear_malla(configuracion):
    """Devuelve ejes rp y T3 (no busca óptimos en estas columnas)."""
    c = configuracion
    rp = (np.geomspace if c['escala'] == 'log' else np.linspace)(c['rp_min'], c['rp_max'], c['n_rp'])
    T3 = np.linspace(c['T3_min'], c['T3_max'], c['n_T3'])
    if not np.all(np.diff(rp) > 0) or not np.all(np.diff(T3) > 0):
        raise ValueError('La resolución solicitada no es representable en coma flotante.')
    return rp, T3


def evaluar_fila(referencia, temperatura, relaciones, verificar=False):
    """Dominio/óptimos una vez por fila, evaluaciones escalares con signo."""
    parametros = {**referencia, 'T3': float(temperatura)}
    muestra = evaluar_muestra(parametros, verificar=verificar)
    datos = []
    for rp in relaciones:
        try:
            punto = evaluar_punto(parametros['T1'], parametros['T3'], parametros['gamma'],
                parametros['cp'], float(rp), parametros['p1'], parametros['eta_c'],
                parametros['eta_t'], parametros['perdida_presion_combustor'])
            datos.append({**punto, 'estado': 'motor' if punto['viable'] else 'inviable'})
        except ErrorNumerico as error:
            datos.append(dict(viable=False, estado='limite_numerico', motivos=(str(error),),
                              rendimiento=None, trabajo_neto=np.nan, calor_aportado=np.nan))
    return dict(T3=float(temperatura), muestra=muestra, puntos=datos)


def obtener_mascaras(filas):
    """Dos booleanas (n_T3,n_rp): motor y límite numérico, nunca confundirlas."""
    return {k: np.array([[p['viable'] if k == 'viable' else p['estado'] == 'limite_numerico'
                         for p in fila['puntos']] for fila in filas], dtype=bool)
            for k in ('viable', 'limite_numerico')}


def extraer_fronteras(filas):
    """Fronteras exactas del evaluador de dominios, independientes de píxeles."""
    resultado = {k: [] for k in ('inferior', 'superior', 'expansion', 'calor')}
    for fila in filas:
        dominios = fila['muestra']['dominios']
        dominio = dominios['noideal'] if dominios else None
        intervalo = dominio['intervalo'] if dominio else ()
        for k, valor in (('inferior', intervalo[0] if intervalo else np.nan),
                         ('superior', intervalo[1] if intervalo else np.nan),
                         ('expansion', dominio['expansion'] if dominio else np.nan),
                         ('calor', dominio['calor'] if dominio else np.nan)):
            resultado[k].append(valor)
    return {k: np.array(v) for k, v in resultado.items()}


def obtener_trayectorias(filas):
    """Conserva registros A/B completos; rp es NaN si no hay máximo alcanzado."""
    return {s: dict(registros=[f['muestra'][s] for f in filas],
                    rp=np.array([f['muestra'][s]['rp'] if f['muestra'][s]['estado'] == 'disponible'
                                 else np.nan for f in filas])) for s in 'AB'}


def extraer_cortes(estudio, temperaturas):
    """Reutiliza filas exactas; evalúa sólo las temperaturas adicionales pedidas."""
    c = estudio['configuracion']
    cortes = tuple(float(t) for t in temperaturas)
    if len(cortes) > 5 or any(not np.isfinite(t) or not c['T3_min'] <= t <= c['T3_max'] for t in cortes):
        raise ValueError('Hasta cinco cortes finitos incluidos en el rango T3.')
    resultado = []
    for t in cortes:
        indice = np.flatnonzero(estudio['T3'] == t)
        resultado.append(estudio['filas'][int(indice[0])] if len(indice)
                         else evaluar_fila(estudio['referencia'], t, estudio['rp']))
    return resultado


def analizar_mapa(referencia, **configuracion):
    """Estudio completo fresco; energías con signo, rendimiento motor en %."""
    inicio = perf_counter()
    c = validar_configuracion(referencia, **configuracion)
    rp, temperaturas = crear_malla(c)
    indices = tuple(sorted({0, len(temperaturas)//2, len(temperaturas)-1}))
    filas = [evaluar_fila(referencia, t, rp, i in indices) for i, t in enumerate(temperaturas)]
    matrices = {k: np.array([[p[k] if p[k] is not None else np.nan for p in f['puntos']]
                            for f in filas]) for k in ('trabajo_neto', 'calor_aportado', 'rendimiento')}
    matrices['rendimiento'] *= 100
    motivos = np.empty((len(temperaturas), len(rp)), dtype=object)
    for i, fila in enumerate(filas):
        for j, punto in enumerate(fila['puntos']):
            motivos[i, j] = punto['motivos']
    estudio = dict(referencia=referencia.copy(), configuracion=c, rp=rp, T3=temperaturas,
                   filas=filas, matrices=matrices, mascaras=obtener_mascaras(filas),
                   motivos=motivos,
                   fronteras=extraer_fronteras(filas), trayectorias=obtener_trayectorias(filas),
                   indices_verificacion=indices)
    estudio['cortes'] = extraer_cortes(estudio, c['cortes'])
    estudio['segundos_calculo'] = perf_counter() - inicio
    return estudio


def preparar_resultados(estudio):
    """Matrices motoras enmascaradas y resumen; no repite cálculos físicos."""
    viable = estudio['mascaras']['viable']
    return dict(prestaciones={k: np.ma.array(v, mask=~viable) for k, v in estudio['matrices'].items()},
                motores=int(viable.sum()), celdas=viable.size,
                limites_numericos=int(estudio['mascaras']['limite_numerico'].sum()))


def crear_graficas_mapa(estudio):
    """Tres mapas sin contornos interpolados y un PNG de dos ejes por corte."""
    from io import BytesIO
    imagenes = {}
    rp, temperaturas, c = estudio['rp'], estudio['T3'], estudio['configuracion']
    preparados = preparar_resultados(estudio)
    for nombre, titulo, unidad in (('trabajo_neto', 'Trabajo neto motor', 'kJ/kg'),
                                  ('rendimiento', 'Rendimiento térmico motor', '%'),
                                  ('viabilidad', 'Viabilidad (banda numérica excluida)', '')):
        fig, ax = plt.subplots(figsize=(9, 6), dpi=150)
        try:
            ax.set_facecolor('#d9dde2')
            if nombre == 'viabilidad':
                z = estudio['mascaras']['viable'].astype(float)
                artista = ax.pcolormesh(rp, temperaturas, z, shading='nearest',
                    cmap=ListedColormap(['#d9dde2', '#287eaa']), vmin=0, vmax=1, rasterized=True)
                barra = fig.colorbar(artista, ax=ax, ticks=[0, 1])
                barra.ax.set_yticklabels(['No motor / límite numérico', 'Motor'])
                for k, texto, estilo in (('inferior', 'Frontera motora inferior', '--'),
                                         ('superior', 'Frontera motora superior', '-.'),
                                         ('expansion', 'Límite de expansión', ':'),
                                         ('calor', 'Límite de calor positivo', ':')):
                    x = estudio['fronteras'][k]
                    ax.plot(np.where((x >= rp[0]) & (x <= rp[-1]), x, np.nan), temperaturas,
                            estilo, label=texto, linewidth=1)
            else:
                artista = ax.pcolormesh(rp, temperaturas, preparados['prestaciones'][nombre],
                                        shading='nearest', cmap='viridis', rasterized=True)
                fig.colorbar(artista, ax=ax, label=f'{titulo} [{unidad}]')
            for s, estilo in (('A', '-'), ('B', '--')):
                x = estudio['trayectorias'][s]['rp']
                ax.plot(np.where((x >= rp[0]) & (x <= rp[-1]), x, np.nan), temperaturas,
                        estilo, color='#bf3434' if s == 'A' else '#702c9b', linewidth=1.8,
                        label=f'{s}: máximo físico (puede quedar fuera de vista)')
            ax.set(xlabel='Relación de presiones rp [−]', ylabel='T3 [K]', title=titulo,
                   xlim=(rp[0], rp[-1]), ylim=(temperaturas[0], temperaturas[-1]))
            ax.set_xscale('log' if c['escala'] == 'log' else 'linear')
            ax.legend(fontsize=7)
            fig.tight_layout()
            salida = BytesIO(); fig.savefig(salida, format='png')
            imagenes[f'mapa_{nombre}.png'] = salida.getvalue()
        finally:
            plt.close(fig)
    for i, fila in enumerate(estudio['cortes']):
        fig, axes = plt.subplots(2, 1, figsize=(9, 7), dpi=150, sharex=True)
        try:
            for ax, clave, unidad in zip(axes, ('trabajo_neto', 'rendimiento'), ('kJ/kg', '%')):
                y = [p[clave] * (100 if clave == 'rendimiento' else 1) if p['viable'] else np.nan
                     for p in fila['puntos']]
                ax.plot(rp, y, label=f"T3={fila['T3']:g} K; sólo motor")
                dominio = fila['muestra']['dominios']
                if dominio and dominio['noideal']['intervalo']:
                    lo, hi = dominio['noideal']['intervalo']
                    if max(lo, rp[0]) < min(hi, rp[-1]):
                        ax.axvspan(max(lo, rp[0]), min(hi, rp[-1]), alpha=.08, color='green', label='Dominio motor abierto')
                    for frontera in (lo, hi):
                        if rp[0] <= frontera <= rp[-1]: ax.axvline(frontera, color='gray', linestyle=':')
                for s, marcador in (('A', 'D'), ('B', '*')):
                    registro = fila['muestra'][s]
                    if registro['estado'] == 'disponible' and rp[0] <= registro['rp'] <= rp[-1]:
                        valor = registro['ciclo'][clave] * (100 if clave == 'rendimiento' else 1)
                        ax.plot(registro['rp'], valor, marcador, label=f'{s}: máximo físico')
                etiqueta = 'Trabajo específico neto' if clave == 'trabajo_neto' else 'Rendimiento térmico'
                ax.set(ylabel=f'{etiqueta} [{unidad}]', xlim=(rp[0], rp[-1]))
                ax.set_xscale('log' if c['escala'] == 'log' else 'linear'); ax.legend(fontsize=8)
                ax.grid(alpha=.2)
            axes[-1].set_xlabel('Relación de presiones rp [−]')
            fig.tight_layout(); salida = BytesIO(); fig.savefig(salida, format='png')
            imagenes[f'corte_{i}.png'] = salida.getvalue()
        finally:
            plt.close(fig)
    return imagenes


def ejecutar_mapa(carpeta_salida, parametros, **configuracion):
    """Calcula, dibuja y publica con la retención compartida de cuatro informes."""
    from reporting import crear_informe_mapa_html, guardar_informe_html, obtener_version_git
    inicio = perf_counter()
    estudio = analizar_mapa(parametros, **configuracion)
    imagenes = crear_graficas_mapa(estudio)
    estudio['segundos_preparacion'] = perf_counter() - inicio
    html = crear_informe_mapa_html(estudio, imagenes, datetime.now().astimezone(),
                                   obtener_version_git(Path(__file__).resolve().parent))
    return guardar_informe_html(html, carpeta_salida, datetime.now().astimezone())
