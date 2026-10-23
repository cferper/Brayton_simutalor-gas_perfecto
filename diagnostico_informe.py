"""Alcance y agregación de diagnósticos sobre resultados ya calculados.

No ejecuta optimizadores ni reconstruye magnitudes ausentes. Los estudios
grandes se recorren por completo, pero se conserva una fila por control/grupo.
"""
from math import isfinite

from diagnostico import diagnosticar_ciclo, diagnosticar_optimizacion


def resumir_diagnosticos(items, alcance, agrupar=False):
    """Iterable de controles -> dict JSON con items, resumen y alcance.

    En agregados se prioriza Atención, después No evaluable y después el mayor
    residuo normalizado. El ejemplo no sustituye los recuentos de cada estado.
    """
    resumen = dict(cumple=0, atencion=0, no_evaluable=0)
    filas = {}
    individuales = []
    for original in items:
        item = original.copy()
        estado = item['estado']
        resumen[estado] += 1
        if not agrupar:
            individuales.append(item)
            continue
        clave = (item['grupo'], item['id'])
        conteos = dict(cumple=0, atencion=0, no_evaluable=0)
        previo = filas.get(clave)
        if previo is not None:
            conteos.update(previo['conteos'])
        conteos[estado] += 1
        residuo, tolerancia = item.get('residuo'), item.get('tolerancia')
        relativo = (abs(residuo) / tolerancia
                    if item.get('comparacion') == 'igualdad'
                    and isinstance(residuo, (int, float)) and isfinite(residuo)
                    and isinstance(tolerancia, (int, float)) and tolerancia > 0
                    else 0.)
        prioridad = (dict(cumple=0, no_evaluable=1, atencion=2)[estado], relativo)
        if previo is None or prioridad > previo['_prioridad']:
            item['_prioridad'] = prioridad
            filas[clave] = item
        filas[clave].update(conteos=conteos, muestras=sum(conteos.values()))
    if agrupar:
        individuales = list(filas.values())
        for item in individuales:
            item.pop('_prioridad')
        alcance += (' Recuentos de controles individuales; las tablas agrupan por relación y escenario. '
                    'Cada fila conserva todos los recuentos y un ejemplo: prioridad Atención, '
                    'después No evaluable y, entre igualdades, mayor |residuo|/tolerancia. '
                    'En restricciones del mismo estado se conserva el primer ejemplo. '
                    'La tolerancia y los valores mostrados pertenecen a ese ejemplo.')
    return dict(items=individuales, resumen=resumen, alcance=alcance)


def diagnostico_simulacion(parametros, ideal, noideal, segunda_ley=None):
    """Dos ciclos calculados -> resumen; entradas SI del formulario interno."""
    items = []
    for modelo, ciclo in (('ideal', ideal), ('noideal', noideal)):
        datos = segunda_ley.get('modelos', {}).get(modelo) if segunda_ley else None
        items.extend(diagnosticar_ciclo(parametros, ciclo, modelo=modelo,
                     contexto='Caso actual', segunda_ley=datos,
                     T0=segunda_ley.get('T0') if segunda_ley else None))
    return resumir_diagnosticos(items, 'Caso actual ideal y no ideal, con los resultados de esta ejecución.')


def diagnostico_optimos(parametros, optimizaciones=None, estudio_rendimiento=None):
    """Estudios A/B originales -> controles de clasificación y concordancia."""
    items = []
    for objetivo, estudios in (('trabajo', optimizaciones), ('rendimiento', estudio_rendimiento)):
        for modelo in ('ideal', 'noideal'):
            estudio = estudios.get(modelo) if estudios else None
            items.extend(diagnosticar_optimizacion(parametros, estudio, modelo=modelo,
                         objetivo=objetivo, contexto='Optimización'))
            candidato = estudio.get('analitico') if estudio else None
            if candidato and candidato.get('ciclo'):
                p = {**parametros, 'relacion_presiones': candidato['rp']}
                items.extend(diagnosticar_ciclo(p, candidato['ciclo'], modelo=modelo,
                             contexto=f'Máximo de {objetivo}'))
    return resumir_diagnosticos(items, 'Óptimos A/B de ambos modelos. Una frontera excluida no es un máximo alcanzado.')


def diagnostico_segunda_ley(parametros, estudio):
    """Estados/entropías guardados -> controles; energías no guardadas son None."""
    items = []
    for modelo in ('ideal', 'noideal'):
        datos = estudio.get('modelos', {}).get(modelo)
        items.extend(diagnosticar_ciclo(parametros, datos or {}, modelo=modelo,
                     contexto='Segunda Ley', segunda_ley=datos, T0=estudio.get('T0')))
    return resumir_diagnosticos(items, 'Estados y Segunda Ley conservados. Este bloque no contiene trabajos ni calores '
                               'guardados: no se inventan para completar controles. No se recalcula el ciclo al cambiar T0.')


def _items_muestra(muestra, escenarios, ubicacion):
    """Generador sobre registros R/A/B; mantiene sus parámetros y disponibilidad."""
    parametros = muestra['parametros']
    for escenario in escenarios:
        registro = muestra[escenario]
        grupo = f'Escenario {escenario}'
        if escenario != 'R':
            estudio = {**registro, 'dominio': (muestra.get('dominios') or {}).get('noideal')}
            items = diagnosticar_optimizacion(parametros, estudio, objetivo=(
                'trabajo' if escenario == 'A' else 'rendimiento'), contexto=grupo)
            for item in items:
                yield {**item, 'contexto': ubicacion}
        ciclo = registro.get('ciclo')
        if ciclo is not None:
            rp = registro.get('rp')
            p = {**parametros, 'relacion_presiones': rp if rp is not None else parametros['relacion_presiones']}
            for item in diagnosticar_ciclo(p, ciclo, contexto=grupo):
                yield {**item, 'contexto': f"{ubicacion}; rp={p['relacion_presiones']:.9g}"}
        elif escenario == 'R':
            estado = registro['estado']
            yield dict(id='disponibilidad', nombre='Disponibilidad del resultado', grupo=grupo,
                       relacion='Estado del evaluador', valor=estado, referencia=None, residuo=None,
                       tolerancia=None, unidad='—', estado=('atencion' if estado in (
                           'inviable', 'parametros_inviables', 'sin_dominio') else 'no_evaluable'),
                       explicacion='La ausencia por límite numérico no demuestra inviabilidad termodinámica.',
                       motivo='; '.join(registro['motivos']), criterio='Clasificación explícita del evaluador.',
                       naturaleza='Disponibilidad de datos', contexto=ubicacion)


def diagnostico_estudio(estudio, tipo):
    """OFAT o mapa -> controles de todos los resultados, agregados sin muestrear."""
    def recorrer():
        if tipo == 'sensibilidad':
            for valor, muestra in zip(estudio['valores'], estudio['registros']):
                yield from _items_muestra(muestra, 'RAB',
                    f"{estudio['configuracion']['parametro']}={valor:.9g}")
            if estudio.get('referencia_local'):
                yield from _items_muestra(estudio['referencia_local'], 'RAB', 'Referencia local del formulario')
        elif tipo == 'mapa':
            temperaturas = {fila['T3'] for fila in estudio['filas']}
            filas = [(fila, 'Malla') for fila in estudio['filas']]
            filas += [(fila, 'Corte adicional') for fila in estudio['cortes'] if fila['T3'] not in temperaturas]
            for fila, origen in filas:
                parametros = {**estudio['referencia'], 'T3': fila['T3']}
                ubicacion = f"{origen}: T3={fila['T3']:.9g} K"
                for rp, punto in zip(estudio['rp'], fila['puntos']):
                    p = {**parametros, 'relacion_presiones': float(rp)}
                    for item in diagnosticar_ciclo(p, punto, contexto=origen):
                        yield {**item, 'contexto': f'{ubicacion}; rp={rp:.9g}'}
                yield from _items_muestra(fila['muestra'], 'AB', ubicacion)
        else:
            raise ValueError('Tipo de estudio de diagnóstico desconocido.')
    alcance = ('Todos los registros R/A/B del barrido y de la referencia local. '
               'El contraste independiente sólo existe en las muestras que lo guardan.' if tipo == 'sensibilidad'
               else 'Todas las celdas del mapa, cortes adicionales y óptimos A/B por T3. '
                    'La ventana gráfica no define un máximo físico.')
    return resumir_diagnosticos(recorrer(), alcance, agrupar=True)
