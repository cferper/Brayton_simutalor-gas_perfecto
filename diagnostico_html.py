"""Presentación compartida del diagnóstico de consistencia interna, sin cálculo físico."""

from html import escape
from math import isfinite
from numbers import Real
from urllib.parse import quote


def renderizar_diagnostico(diagnostico, clave="actual"):
    """Devuelve HTML escapado de un diagnóstico ya calculado.

    ``diagnostico`` contiene ``items``, ``resumen`` y ``alcance``. Cada item
    conserva su ecuación, valores, residuo, tolerancia y explicación; este
    presentador no los recalcula ni ejecuta pruebas de verificación. ``clave``
    distingue los identificadores cuando se incluyen varios paneles.
    """
    estados = {
        "cumple": "Cumple",
        "atencion": "Atención",
        "no_evaluable": "No evaluable",
    }

    def texto(valor):
        """Escapa texto para su inclusión en contenido o atributos HTML."""
        return escape(str(valor), quote=True)

    def numero(valor):
        """Da formato de lectura sin alterar el valor usado en los cálculos."""
        if valor is None:
            return "No disponible"
        if isinstance(valor, Real) and not isinstance(valor, bool):
            if not isfinite(valor):
                return "No disponible (no finito)"
            return texto(f"{valor:.6g}")
        return texto(valor)

    def magnitud(valor, unidad):
        """Presenta el valor y su unidad sin interpretar la relación física."""
        unidad_html = f' <span class="diagnostico-unidad">[{texto(unidad)}]</span>'
        return numero(valor) + (unidad_html if unidad else "")

    prefijo = "diagnostico-" + quote(str(clave), safe="")
    alcance = diagnostico.get("alcance", "Consistencia interna del modelo implementado.")
    resumen = diagnostico.get("resumen", {})
    grupos = {}
    for item in diagnostico.get("items", ()):
        grupos.setdefault(str(item.get("grupo", "Comprobaciones")), []).append(item)

    partes = [
        f'<section class="card diagnostico-panel" id="{prefijo}" '
        f'aria-labelledby="{prefijo}-titulo">',
        f'<h3 id="{prefijo}-titulo">Diagnóstico y coherencia física</h3>',
        '<p class="diagnostico-intro">Comprobaciones de consistencia interna del modelo '
        'y de los resultados calculados. No constituyen validación experimental '
        'ni ejecutan la batería de verificación V.1–V.5.</p>',
        '<ul class="diagnostico-resumen" aria-label="Resumen del diagnóstico">',
    ]
    for estado, etiqueta in estados.items():
        partes.append(
            f'<li class="diagnostico-estado diagnostico-{estado}">'
            f'<strong>{numero(resumen.get(estado, 0))}</strong> {etiqueta}</li>'
        )
    partes.extend(['</ul>', f'<p class="diagnostico-alcance">{texto(alcance)}</p>'])
    if any(item.get("conteos") is not None for items in grupos.values() for item in items):
        partes.append(
            '<p class="diagnostico-alcance">El resumen cuenta comprobaciones individuales '
            'de todas las muestras. Cada fila agregada muestra los valores de un ejemplo '
            'localizado; sus recuentos abarcan todas las muestras y ese ejemplo no las '
            'representa por sí solo.</p>'
        )
    if not grupos:
        partes.append('<p>No hay comprobaciones disponibles para este contexto.</p>')

    for indice_grupo, (grupo, items) in enumerate(grupos.items()):
        grupo_id = f"{prefijo}-grupo-{indice_grupo}"
        conteos_grupo = dict(cumple=0, atencion=0, no_evaluable=0)
        for item in items:
            if item.get("conteos") is not None:
                for estado in estados:
                    conteos_grupo[estado] += item["conteos"].get(estado, 0)
            else:
                estado = item.get("estado", "no_evaluable")
                conteos_grupo[estado if estado in estados else "no_evaluable"] += 1
        resumen_grupo = "".join(
            f'<span class="diagnostico-estado diagnostico-{estado}">{etiqueta}: '
            f'{numero(conteos_grupo[estado])}</span>'
            for estado, etiqueta in estados.items()
        )
        partes.extend([
            '<details class="diagnostico-grupo">',
            f'<summary id="{grupo_id}">{texto(grupo)} '
            f'<span class="diagnostico-numero">({len(items)} relaciones)</span>'
            f'<span class="diagnostico-grupo-resumen">{resumen_grupo}</span></summary>',
            f'<table class="diagnostico-tabla" aria-labelledby="{grupo_id}">',
            '<thead><tr><th scope="col">Comprobación</th><th scope="col">Resultado</th>'
            '<th scope="col">Residuo</th><th scope="col">Tolerancia</th>'
            '<th scope="col">Estado</th></tr></thead><tbody>',
        ])
        for indice_item, item in enumerate(items):
            estado = item.get("estado", "no_evaluable")
            if estado not in estados:
                estado = "no_evaluable"
            unidad = item.get("unidad", "")
            fila_id = f"{grupo_id}-comprobacion-{indice_item}"
            explicaciones = (
                ("Ecuación / relación", item.get("relacion", "No disponible")),
                ("Interpretación física", item.get("explicacion", "No disponible")),
                ("Naturaleza", item.get("naturaleza", "Consistencia interna")),
                ("Criterio de tolerancia", item.get("criterio", "No disponible")),
                ("Motivo / observación", item.get("motivo") or "Sin observaciones adicionales."),
                ("Alcance", alcance),
            )
            partes.extend([
                f'<tr data-diagnostico-id="{texto(item.get("id", ""))}" '
                f'data-estado="{estado}">',
                '<td data-label="Comprobación">',
                f'<strong>{texto(item.get("nombre", "Comprobación"))}</strong>',
                '<details class="diagnostico-explicacion">',
                f'<summary id="{fila_id}">Ver ecuación y significado</summary><dl>',
            ])
            for etiqueta, contenido in explicaciones:
                partes.append(f'<dt>{etiqueta}</dt><dd>{texto(contenido)}</dd>')
            contexto = item.get("contexto", item.get("peor_caso"))
            if contexto is not None:
                if isinstance(contexto, dict):
                    contexto = "; ".join(f"{nombre}: {valor}" for nombre, valor in contexto.items())
                partes.append(f'<dt>Contexto del ejemplo mostrado</dt><dd>{texto(contexto)}</dd>')
            partes.extend([
                '</dl></details></td>',
                '<td data-label="Resultado">',
                f'<span class="diagnostico-valor">{magnitud(item.get("valor"), unidad)}</span>',
                f'<span class="diagnostico-referencia">Referencia: '
                f'{magnitud(item.get("referencia"), unidad)}</span></td>',
                f'<td data-label="Residuo">{magnitud(item.get("residuo"), unidad)}',
            ])
            if item.get("residuo_relativo") is not None:
                partes.append(
                    '<span class="diagnostico-referencia">Relativo [−]: '
                    f'{numero(item["residuo_relativo"])}</span>'
                )
            partes.extend([
                '</td>',
                f'<td data-label="Tolerancia">{magnitud(item.get("tolerancia"), unidad)}</td>',
                '<td data-label="Estado">',
                f'<span class="diagnostico-estado diagnostico-{estado}">{estados[estado]}</span>',
            ])
            conteos = item.get("conteos")
            if conteos is not None:
                for nombre_estado, etiqueta in estados.items():
                    partes.append(
                        f'<span class="diagnostico-conteo">{etiqueta}: '
                        f'{numero(conteos.get(nombre_estado, 0))}</span>'
                    )
            if item.get("muestras") is not None:
                partes.append(
                    '<span class="diagnostico-conteo">Muestras: '
                    f'{numero(item["muestras"])}</span>'
                )
            partes.append('</td></tr>')
        partes.append('</tbody></table></details>')
    partes.append('</section>')
    return "".join(partes)
