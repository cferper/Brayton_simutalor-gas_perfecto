"""Guías educativas estáticas del dashboard. No realizan cálculos ni alteran estados."""
from html import escape

# Ecuaciones expresadas bajo la hipótesis de gas caloríficamente perfecto del simulador.
GUIAS = {
 'simulacion': {
  'resumen': 'Define los estados de entrada, las propiedades del gas, la relación de presiones y las pérdidas. Calculamos los cuatro estados del ciclo, el trabajo consumido por el compresor, el producido por la turbina y el calor aportado. Comparamos el ciclo ideal con el no ideal.',
  'fundamentos': 'El ciclo Brayton ideal comprende dos transformaciones isentrópicas y dos intercambios de calor a presión constante. El modelo no ideal emplea eficiencias isentrópicas de compresor y turbina y una pérdida de presión en el combustor. Se supone gas ideal, cₚ y γ constantes, y equipos adiabáticos.',
  'ecuaciones': [('Exponente isentrópico','a = (γ − 1)/γ'),('Compresor','T₂ = T₁[1 + (rₚᵃ − 1)/ηc]'),('Combustor','p₃ = p₂(1 − δ)'),('Turbina','T₄ = T₃[1 − ηt(1 − ((1 − δ)rₚ)⁻ᵃ)]'),('Balance','wₙ = cₚ[(T₃ − T₄) − (T₂ − T₁)]; qᵢₙ = cₚ(T₃ − T₂)')],
  'metodo': 'Validamos las entradas, calculamos temperaturas y presiones, evaluamos los balances específicos y comprobamos el dominio motor antes de presentar prestaciones. cₚ se expresa en J/(kg·K) en la entrada y los resultados energéticos se muestran en kJ/kg.',
  'interpretacion': 'Un estado matemáticamente calculable no implica un ciclo motor: se exige expansión disponible, aporte de calor y trabajo neto positivos. El modelo es termodinámico; no calcula empuje ni potencia sin información adicional.'},
 'resultados': {
  'resumen': 'Resume el ciclo correspondiente a los parámetros elegidos. Los valores de trabajo y calor son específicos (por kilogramo de fluido), no potencias. Las gráficas muestran cómo cambian las prestaciones al variar rₚ dentro del dominio motor.',
  'fundamentos': 'La primera ley para compresor y turbina adiabáticos relaciona el cambio de entalpía con el trabajo específico. Para un gas con cₚ constante, Δh = cₚΔT. El rendimiento térmico relaciona el trabajo neto motor con el calor aportado.',
  'ecuaciones': [('Trabajo del compresor','w꜀ = cₚ(T₂ − T₁)'),('Trabajo de la turbina','wₜ = cₚ(T₃ − T₄)'),('Trabajo neto','wₙ = wₜ − w꜀'),('Calor aportado','qᵢₙ = cₚ(T₃ − T₂)'),('Rendimiento','ηth = wₙ / qᵢₙ')],
  'metodo': 'Se evalúan los estados 1–4 y se aplican los filtros físicos de viabilidad. Para las curvas se recorre rₚ y se dejan sin trazar los puntos no motores. Los máximos se calculan por métodos propios, no leyendo el píxel más alto de una figura.',
  'interpretacion': 'Compara la posición de los máximos y las regiones sin datos; un hueco indica inviabilidad o falta de disponibilidad numérica, no necesariamente un valor cero. Los diagramas T–s y p–v históricos representan el ciclo ideal.'},
 'optimizacion': {
  'resumen': 'Estudia dos elecciones de diseño: A busca el mayor trabajo específico neto y B el mayor rendimiento térmico. Para cada objetivo se reajusta rₚ respetando el dominio motor. El mejor rₚ para trabajo no tiene por qué ser el mejor para rendimiento.',
  'fundamentos': 'Maximizar el trabajo específico y maximizar la razón trabajo/calor son problemas distintos. En el Brayton ideal con T₁ y T₃ fijas, ηth crece con rₚ dentro del dominio; su supremo está en una frontera excluida. Con pérdidas y dominio motor puede existir un máximo interior de rendimiento.',
  'ecuaciones': [('Objetivo A','max wₙ(rₚ) sujeto a ciclo motor'),('Objetivo B','max ηth(rₚ) = wₙ(rₚ)/qᵢₙ(rₚ)'),('Ideal','ηideal = 1 − rₚ⁻ᵃ'),('Máximo trabajo ideal','rₚ,A = (T₃/T₁)^(1/(2a))'),('Cambio de rendimiento','Δη [puntos porcentuales] = ηB[%] − ηA[%]')],
  'metodo': 'Se calculan los límites viables y se buscan candidatos analíticos y numéricos independientes. Se verifica que cada candidato sea interior y motor. Después se evalúan estados, trabajo, rendimiento y calor en A y B y se cuantifica el compromiso.',
  'interpretacion': 'En B puede ganarse rendimiento sacrificando trabajo específico. Si solo existe un supremo no alcanzado, no hay un punto B operativo que comparar. No confundas puntos porcentuales de rendimiento con variaciones porcentuales relativas.'},
 'sensibilidad': {
  'resumen': 'Varía un único factor —T₁, T₃, ηc, ηt o δ— mientras los restantes parámetros físicos permanecen fijos. Para cada muestra se comparan R (rₚ fija), A (máximo trabajo reajustando rₚ) y B (máximo rendimiento reajustando rₚ). Sirve para reconocer tendencias locales y pérdidas de viabilidad.',
  'fundamentos': 'OFAT (un factor cada vez) aísla la respuesta del modelo al modificar una entrada. No detecta interacciones entre dos parámetros. En A y B también cambia rₚ por la reoptimización: esas curvas no son una sensibilidad a rₚ fija.',
  'ecuaciones': [('Sensibilidad absoluta','∂Y/∂x ≈ [Y(x+h) − Y(x−h)]/(2h)'),('Sensibilidad normalizada','S(Y,x) = (x/Y) · ∂Y/∂x'),('R','rₚ = rₚ,referencia'),('A y B','rₚ,A(x) = arg max wₙ ; rₚ,B(x) = arg max ηth')],
  'metodo': 'Se genera una malla del factor seleccionado; en cada muestra se reconstruye el ciclo, se recalcula su dominio y se obtienen R, A y B cuando están disponibles. Las derivadas locales emplean diferencias finitas con comprobaciones de paso y estabilidad; pueden quedar no disponibles.',
  'interpretacion': 'Compara las curvas R y A/B para separar el efecto de variar la entrada del de optimizar el diseño. Los NaN cortan las curvas inviables; la línea de consigna rₚ de R puede seguir visible aunque el ciclo ya no sea motor. Una sensibilidad local no ordena universalmente la importancia de las entradas.',
  'experimento': 'Prueba T₃ entre 800 y 2000 K. Observa si aumentan el trabajo y las relaciones de presiones óptimas. Repite con ηc y comprueba dónde aparecen puntos no motores.'},
 'mapa': {
  'resumen': 'Explora simultáneamente dos variables: relación de presiones rₚ y temperatura de entrada a la turbina T₃. Cada celda representa un ciclo completo; el color expresa trabajo, rendimiento o viabilidad y las curvas superpuestas señalan decisiones de diseño para cada T₃.',
  'fundamentos': 'Una superficie bidimensional permite reconocer interacciones que un barrido OFAT no muestra. El dominio motor depende de ambas variables; las fronteras separan estados matemáticamente posibles de condiciones que producen trabajo neto y calor positivo.',
  'ecuaciones': [('Malla de condiciones','(rₚ,i, T₃,j) → estados 1–4'),('Trabajo en cada celda','wₙ(rₚ,T₃) = cₚ[(T₃ − T₄) − (T₂ − T₁)]'),('Rendimiento motor','ηth(rₚ,T₃) = wₙ/qᵢₙ'),('Criterio motor','qᵢₙ > 0 ; wₙ > 0 ; compresión y expansión disponibles')],
  'metodo': 'Se fijan las otras siete entradas y se evalúa la malla rₚ × T₃. Los puntos no motores se enmascaran; después se representan mapas de prestaciones y fronteras, y cortes de T₃. Los óptimos A/B se calculan para cada temperatura de forma independiente de la resolución de píxeles.',
  'interpretacion': 'Los colores son resultados específicos del modelo, no mapas experimentales de un motor. Las zonas sin color no representan prestaciones cero. La escala logarítmica de rₚ solo cambia la visualización y el muestreo, no la definición física de los óptimos.',
  'experimento': 'Compara un mapa con rₚ lineal y otro logarítmico. Después fija dos temperaturas en los cortes y observa cómo se desplazan A y B.'},
 'segunda_ley': {
  'resumen': 'Cuantifica las irreversibilidades del compresor y la turbina mediante cambios de entropía y destrucción de exergía. Puedes cambiar la temperatura ambiente de referencia T₀ sin alterar los estados termodinámicos ya calculados.',
  'fundamentos': 'En equipos adiabáticos estacionarios, la generación de entropía se relaciona con la irreversibilidad. El teorema de Gouy–Stodola conecta la exergía destruida con T₀ y la generación de entropía. Aquí se analizan compresor y turbina; no es un balance exergético integral del motor.',
  'ecuaciones': [('Entropía relativa','Δs = cₚ ln(Tsal/Tent) − R ln(psal/pent)'),('Constante del gas','R = cₚ(γ − 1)/γ'),('Exergía destruida','eD = T₀ sgen'),('Adiabático','sgen = ssal − sent ≥ 0')],
  'metodo': 'Se utilizan los estados del ciclo ideal y del no ideal. Se obtienen cambios de entropía y generación en cada equipo, y se multiplican por T₀ para calcular exergía destruida. El valor T₀ solo actúa en este diagnóstico de segunda ley.',
  'interpretacion': 'Una exergía destruida positiva mide potencial útil perdido por irreversibilidad. Cambiar T₀ altera la exergía destruida calculada, pero no el trabajo específico del ciclo. Si el caso no es motor, los resultados se etiquetan como diagnóstico.'},
 'informes': {
  'resumen': 'Conserva y permite descargar los últimos cuatro informes completos. Cada HTML incorpora sus gráficas, resultados y explicaciones, además de metadatos de ejecución para reproducir el caso.',
  'fundamentos': 'Un cálculo científico reproducible debe registrar condiciones, unidades, hipótesis y versión del código. Un resultado numérico verificado mediante pruebas no equivale a validación experimental.',
  'ecuaciones': [('Identificación de un caso','resultado = modelo(parámetros, versión)'),('Trazabilidad','parámetros + fecha + metadatos Git + hipótesis')],
  'metodo': 'El programa prepara un informe HTML autónomo con imágenes incorporadas; publica de manera controlada la versión final y mantiene un historial limitado a cuatro informes completos.',
  'interpretacion': 'Consulta la fecha y los parámetros antes de comparar informes. Un informe anterior puede corresponder a otro conjunto de entradas y no es automáticamente comparable con el caso actual.'},
 'ayuda': {
  'resumen': 'Consulta definiciones, unidades y limitaciones del simulador. Las explicaciones de cada sección describen las ecuaciones y el procedimiento; el walkthrough y las guías por fase ofrecen un desarrollo más extenso.',
  'fundamentos': 'El modelo emplea un gas ideal caloríficamente perfecto. No resuelve mapas reales de componentes, combustión química, dinámica transitoria ni empuje de un aerorreactor.',
  'ecuaciones': [('Relación de presiones','rₚ = p₂/p₁'),('Rendimiento térmico','ηth = wₙ/qᵢₙ'),('Energía y potencia','P = ṁ · wₙ (solo con caudal conocido)')],
  'metodo': 'Localiza el parámetro o magnitud en el glosario y contrasta su interpretación con los estados, balances y dominios indicados en Resultados.',
  'interpretacion': 'Las fórmulas y gráficas representan hipótesis simplificadas: no utilices el simulador como herramienta de certificación o dimensionamiento final de un aerorreactor.'},
}

def construir_guias():
    """Construye HTML a partir de contenido editorial constante y escapado."""
    resultado={}
    for clave, g in GUIAS.items():
        def texto(t): return escape(t)
        ec=''.join(f'<dt>{texto(n)}</dt><dd><code>{texto(f)}</code></dd>' for n,f in g['ecuaciones'])
        practica=(f'<p class="edu-experiment"><strong>Prueba tú mismo:</strong> {texto(g["experimento"])}</p>' if g.get('experimento') else '')
        resultado[clave]=(f'<div class="edu-guide" aria-label="Explicación educativa">'
            f'<div class="edu-overview"><strong>Qué vas a estudiar y calcular</strong><p>{texto(g["resumen"])}</p></div>'
            f'<details class="edu-details"><summary>Fundamentos termodinámicos, ecuaciones y procedimiento <span class="edu-hint">Ver explicación completa</span></summary>'
            f'<div class="edu-details-body"><h3>Fundamentos físicos</h3><p>{texto(g["fundamentos"])}</p>'
            f'<h3>Ecuaciones del modelo</h3><dl class="edu-equations">{ec}</dl>'
            f'<h3>Cómo lo calcula el programa</h3><p>{texto(g["metodo"])}</p>'
            f'<h3>Cómo interpretar los resultados</h3><p>{texto(g["interpretacion"])}</p>{practica}</div></details></div>')
    return resultado


def construir_pestanas():
    """Fragmentos educativos compartidos para las dos vistas por sección."""
    resultado = {}
    for clave, g in GUIAS.items():
        esc = escape
        ecuaciones = ''.join(
            f'<dt>{esc(titulo)}</dt><dd><code>{esc(expresion)}</code></dd>'
            for titulo, expresion in g['ecuaciones']
        )
        practica = (f'<p class="edu-experiment"><strong>Prueba tú mismo:</strong> {esc(g["experimento"])}</p>'
                    if g.get('experimento') else '')
        resultado[clave] = {
            'resumen': f'<div class="edu-overview"><strong>Qué vamos a estudiar</strong><p>{esc(g["resumen"])}</p></div>',
            'teoria': (
                f'<div class="edu-theory"><h3>Fundamentos termodinámicos</h3><p>{esc(g["fundamentos"])}</p>'
                f'<h3>Ecuaciones y magnitudes</h3><dl class="edu-equations">{ecuaciones}</dl>'
                f'<h3>Procedimiento de cálculo</h3><p>{esc(g["metodo"])}</p>'
                f'<h3>Interpretación de resultados</h3><p>{esc(g["interpretacion"])}</p>{practica}</div>'
            )
        }
    return resultado
