# Fase 2 — Aprender a optimizar el trabajo neto no ideal

Documento independiente de aprendizaje de la implementación de Fase 2, redactado y verificado el **20 de octubre de 2026**. Enseña sus novedades respecto al estado anterior; el [manual actual](../../CODE_WALKTHROUGH.md) explica el conjunto del proyecto y el [milestone técnico](04_optimizacion_noideal.md) resume esta etapa.

## 1. Punto de partida verificable y objetivo

- Rama de desarrollo: `feature/fase-2-optimizacion-noideal`.
- Commit base verificado: `f9f9a0495c4231a4d48399fba4bccdcc0f6bcf6f`. Al comenzar, el árbol estaba limpio.
- Commit que contiene Fase 2: `c2f4bff84a173f3b354a5d0f76c2b7bd2ee1fa21` — `Implement non-ideal Brayton work optimization with dynamic intervals`. La base no contiene esta implementación. El hash se incorpora en el cierre posterior autorizado; durante el desarrollo original se dejó pendiente y no se realizaron operaciones de integración.
- El documento anterior de Fase 1 conserva su alcance histórico; no se reutiliza para explicar Fase 2.

Antes existían ecuaciones ideales/no ideales, dominios motores, seis gráficas HTML, formulario Flask de nueve entradas, historial de cuatro informes y búsqueda del máximo exclusivamente ideal. Ahora el programa encuentra **también el máximo de trabajo específico no ideal**, lo compara mediante dos métodos, evalúa sus estados y adapta ventanas y gráficas a cada ejecución. La pregunta es: con T1, T3, gamma, eficiencias y pérdida fijas, ¿qué relación de presiones entrega mayor trabajo neto por kilogramo?

El trabajo específico se mide en kJ/kg; sin caudal no es una potencia. El rendimiento calculado en ese punto no es un máximo de rendimiento. Las hipótesis siguen siendo gas ideal, cp/gamma constantes, equipos adiabáticos y pérdida relativa de presión fija. Estos cálculos educativos no describen un motor real con alta fidelidad.

## 2. Mapa de cambios y recorrido de los datos

| Archivo | Antes → ahora | Motivo |
|---|---|---|
| `optimizacion.py`, nuevo | No existía → tres funciones y un evaluador local | Separar la búsqueda de física, presentación y servidor |
| `viabilidad.py:construir_barrido` | Vista con tope 10000 → dominio completo y puntos de interés | Mostrar fronteras y máximos aunque excedan ventanas antiguas |
| `main.py:main` | Barrido y búsqueda ideal heredada → dos estudios por ejecución antes del barrido | Reutilizar dominios actuales y añadir máximos a la malla visual |
| `main.py:guardar_comparaciones_ciclos` | Dos curvas sin máximo no ideal → marcadores de ambos y posible detalle | Comparar escalas distintas sin ocultar el dominio general |
| `main.py:guardar_grafica_rendimiento / guardar_grafica_trabajo_neto` | Ejes automáticos → límites explícitos de la vista compartida | Hacer visibles las fronteras relevantes |
| `reporting.py` | Datos de referencia y máximo ideal → sección de optimización y estados no ideales óptimos | Reunir resultados, unidades y precisión declarada |
| `tests/test_optimizacion.py`, nuevo | Sin pruebas de optimización no ideal → 15 métodos | Verificar métodos, límites, adaptación e integración |
| `tests/test_reporting.py` | Esperaba número del antiguo barrido → comprueba el nuevo resultado suministrado | Mantener la prueba completa al cambiar legítimamente el algoritmo |
| `README.md` y `CODE_WALKTHROUGH.md` | Estado anterior → explicación actual | Mantener ejecución, ejemplos y contratos sincronizados |

No se modifican las 13 funciones físicas originales ni el sistema de fronteras, bisección, clasificación y banda cero de Fase 1. `buscar_optimo_numerico` conserva su contrato ideal heredado para llamadas directas y pruebas; `main` utiliza el módulo nuevo para ambos modelos. No se modifica `web_app.py` ni el formulario: su llamada a `main` incorpora los resultados automáticamente. No se alteran dependencias ni PNG históricos.

Recorrido:

```text
POST de nueve valores → web_app.leer_parametros → main
  → validar_parametros y calcular_dominios de ESTA ejecución
  → evaluar referencia; si es inviable, conservar rechazo de Fase 1
  → optimizar_trabajo_neto ideal y no ideal con esos dominios
       → candidato analítico + evaluar_punto
       → buscar_maximo_numerico → evaluar_punto
       → contraste de tolerancias y diccionario de resultados
  → construir_barrido con referencia y máximos como puntos de interés
  → seis imágenes en memoria → crear_informe_html
       → seccion_optimizacion_html → tabla_html
  → publicar HTML completo → conservar cuatro → vista/descarga Flask
```

Sólo se calcula física en las funciones existentes de Fase 1; el optimizador no reimplementa temperaturas ni balances. El presentador sólo lee resultados.

## 3. Ingeniería: derivar el máximo, no memorizarlo

### 3.1. Ecuación y signos

Definimos a=(gamma−1)/gamma>0, C=cp/1000>0 [kJ/(kg·K)], x=rp^a, theta=T3/T1, h=theta·eta_c·eta_t y k=(1−delta)^(-a)≥1. Los demás símbolos son adimensionales. El compresor consume una magnitud positiva que se resta del trabajo producido por la turbina:

```text
W = C [eta_t*T3*(1−(rp*(1−delta))^(−a))
       − (T1/eta_c)*(rp^a−1)]
  = C [eta_t*T3*(1−k/x) − (T1/eta_c)*(x−1)]
```

Al aumentar rp crece el salto útil de la turbina, pero también el coste del compresor. El máximo equilibra sus incrementos marginales.

### 3.2. Primera y segunda derivadas

```text
dW/dx = C [eta_t*T3*k/x² − T1/eta_c]
d²W/dx² = −2*C*eta_t*T3*k/x³ < 0

x*² = eta_c*eta_t*T3*k/T1 = h*k
rp* = (h*k)^(1/(2*a))
    = [eta_c*eta_t*T3/(T1*(1−delta)^a)]^(1/(2*a))
```

Respecto a rp (regla de la cadena dx/drp=a·rp^(a−1)):

```text
dW/drp = C*a*rp^(−a−1) [eta_t*T3*k − (T1/eta_c)*rp^(2*a)]
d²W/drp² en rp* = −2*C*a²*(T1/eta_c)*rp*^(a−2) < 0
```

La segunda derivada negativa en el candidato prueba máximo local. La concavidad estricta global en x y su correspondencia creciente con rp prueban unicidad del máximo global positivo. No afirmamos concavidad global en rp. Para y=ln(rp), también resulta

`d²W/dy²=−C*a²[eta_t*T3*k*exp(−a*y)+(T1/eta_c)*exp(a*y)]<0`.

Esta última propiedad permite refinar una sola cima en coordenada logarítmica.

### 3.3. Por qué siempre es interior cuando hay motor

No basta con sustituir datos en la fórmula. Supón que existe un rp>1 motor con W>0:

1. El trabajo del compresor es positivo; la turbina debe producir más. Por tanto su expansión efectiva exige x>k.
2. Fase 1 expresa W>0 como `Q(x)=(x−1)(x−h)+h(k−1)<0`. Con x>1 y k≥1, esto obliga a x<h y h>1.
3. El máximo global x*=sqrt(hk)>1 alcanza W al menos tan positivo como aquel punto motor. Aplicando el mismo razonamiento al candidato, x*>k y 1<x*<h.
4. El calor positivo exige `x<1+eta_c*(theta−1)`. Como `h=theta*eta_c*eta_t≤theta*eta_c≤1+eta_c*(theta−1)`, el candidato también cumple esa condición.
5. Cumple simultáneamente compresión, expansión, calor y trabajo positivos: está entre las raíces de trabajo y dentro del dominio abierto de Fase 1.

Se demuestra una propiedad del modelo actual, no se impone otra restricción. En una frontera de trabajo W=0 no hay máximo motor admisible. Si el dominio es vacío, un candidato matemático puede seguir existiendo; no se devuelve como máximo físico. Con eficiencias unidad y delta cero se recupera `rp*=(T3/T1)^(1/(2*a))`, la fórmula ideal anterior.

En aritmética finita, una cima muy pequeña puede quedar dentro de la banda cero relativa de Fase 1 (10⁻¹⁰ con escalas físicas). Un intervalo matemáticamente no vacío no garantiza un motor numéricamente resoluble. Se informa `ErrorNumerico` sin afirmar que la termodinámica haya cambiado.

## 4. Implementación numérica y adaptación de intervalos

### 4.1. Tres intervalos distintos

| Concepto | Cálculo por ejecución | Uso |
|---|---|---|
| Dominio físico abierto (lo,hi) | `calcular_dominios` de Fase 1 | Expansión, calor y trabajo positivos |
| Ventana numérica interior | ln(lo)/ln(hi), margen de 10⁻⁶ de su anchura en cada extremo | Buscar el máximo sin aceptar fronteras |
| Ventana visual | Desde 1 hasta 1.05 veces el límite ideal (sin tope fijo) | Mostrar dominios, fronteras y máximos, incluso fuera de 2–30/1.01–50 |

El margen numérico evita evaluar extremos abiertos; no redefine el dominio físico. La ventana de dibujo incluye zonas excluidas para situar fronteras, pero sólo traza puntos motores, con NaN en los demás. Se conserva una cantidad acotada de muestras aunque el dominio alcance millones. Si el margen o los puntos interiores no son representables, se detiene con diagnóstico numérico.

### 4.2. Búsqueda independiente paso a paso

1. Validar entradas y controles. Sin dominio suministrado, obtenerlo de `calcular_dominios`. Vacío → `None` sin evaluar una malla.
2. Crear 257 valores uniformes de y=ln(rp) entre los límites interiores. En rp están espaciados por un cociente constante; cubren tanto relaciones cercanas a 1 como órdenes de magnitud elevados.
3. Evaluar cada rp con `evaluar_punto`, reutilizando un diccionario local de registros. Seleccionar el índice del mayor trabajo. Si es un extremo de la malla, no declarar un falso máximo interior.
4. Acotar con los dos vecinos y refinar por sección áurea. La razón (sqrt(5)−1)/2≈0.618 permite conservar una evaluación cuando se reduce el intervalo; se necesita como mucho una evaluación nueva por paso.
5. Parar cuando la anchura en ln(rp)≤10⁻⁹, con un máximo de 100 iteraciones predeterminadas. Si se agotan sin converger, lanzar `ErrorNumerico`.
6. Elegir el mayor trabajo de todos los registros con `viable=True`. El signo del trabajo puede guiar pasos cercanos a la banda cero, pero esos puntos no se aceptan como soluciones.
7. Comparar con el candidato analítico **después** de la búsqueda. No se utiliza la fórmula para construir la malla ni el intervalo local.

En el caso predeterminado cada modelo usa 297 evaluaciones únicas, no 100001. Los controles permiten 5–4097 muestras y 1–1000 iteraciones, con tolerancia logarítmica finita entre 0 y 1. Son controles de la API, sin campos nuevos de Flask.

### 4.3. Resolución, redondeo y tolerancias

El paso inicial en y no equivale a error final de rp. Cerca del máximo, variaciones pequeñas de rp producen variaciones cuadráticas diminutas del trabajo, que pueden desaparecer por redondeo. El mejor registro guardado puede incluso quedar fuera del último intervalo refinado si hubo valores prácticamente iguales.

Por eso se muestran separadamente:

- paso inicial logarítmico;
- anchura/intervalo final del refinamiento y criterio de parada;
- escala conservadora `resolucion_rp=rp*max(tolerancia_log,32*sqrt(np.finfo(float).eps))`, aproximadamente 4.77·10⁻⁷·rp;
- diferencias analítica-numérica y sus tolerancias.

La escala de resolución no es una cota rigurosa de error. La comparación requiere `|Δrp|≤2e-6*max(rp_analitico,rp_numerico)` y `|ΔW|≤1e-9*max(|W_analitico|,cp/1000*T3)`. La escala térmica de la segunda evita exigir error relativo imposible al cancelar trabajos próximos. Se verifica aparte que el punto supere la banda cero. Estas tolerancias de cálculo no representan incertidumbre experimental ni justifican propiedades constantes a temperaturas extremas.

### 4.4. Todos los parámetros actuales, sin resultados persistentes

`main` recalcula dominios y ambos estudios en cada llamada. La caché del evaluador es local y desaparece al terminar esa búsqueda; no comparte resultados entre POST. Quien suministre `dominio` debe entregar el calculado con esos mismos parámetros, como hace `main`.

T1, T3, gamma, eta_c, eta_t y delta cambian el candidato y pueden cambiar/aniquilar el dominio. cp multiplica energías, p1 escala presiones: no aparecen en rp*, aunque sí se vuelven a usar al evaluar cada ciclo. La novena entrada, rp de referencia, identifica el punto comparado; no impone límites artificiales a la optimización.

### 4.5. Dibujo completo y detalle

`construir_barrido` conserva sus ecuaciones y clasificación, y combina 500 muestras geométricas, 500 lineales, fronteras/vecinos relativos ±10⁻⁶ y 101 por intervalo motor. Añade 17 muestras geométricas alrededor de cada punto de interés y el punto exacto; el radio es 1.5 % de la amplitud logarítmica de la vista. `main` suministra referencia y dos máximos: 1265 puntos distintos en el ejemplo. Con `relaciones` explícitas se respeta esa malla, sin enriquecerla automáticamente.

La figura de trabajo comparado identifica círculo azul ideal y rombo naranja no ideal, con rp/W en leyenda. Si la anchura logarítmica de la vista supera cuatro veces la del dominio no ideal o el máximo trabajo ideal supera veinte veces el no ideal, ambas comparaciones añaden un panel no ideal con escalas propias. Ese detalle amplía su intervalo un 4 % en coordenada logarítmica, conservando arriba la comparación completa. No son restricciones físicas ni una gráfica adicional redundante. Hay siempre seis PNG de 1350×900, Base64 dentro del HTML.

## 5. Contratos de las funciones nuevas y adaptadas

Unidades comunes: T en K, cp en J/(kg·K), p1 en kPa, trabajos en kJ/kg; gamma/eficiencias/delta/rp adimensionales. Se esperan escalares reales, no arrays físicos completos. El [manual §4.35–4.37](../../CODE_WALKTHROUGH.md#435-optimización--optimizacionpy) amplía los contratos; aquí se aplican al estudio nuevo.

### `calcular_candidato_analitico(T1, T3, gamma, eta_c=1, eta_t=1, delta=0)`

Recibe seis escalares físicos, devuelve un rp positivo finito (float) que sólo es candidato. Llama a `validar_parametros` con cp=p1=1 auxiliares. La llama `optimizar_trabajo_neto` y las pruebas. Para evitar productos intermedios grandes evalúa:

```python
exponente = (log(T3) - log(T1) + log(eta_c) + log(eta_t)
             - a * log(1 - delta)) / (2 * a)
candidato = exp(exponente)
```

`log` convierte productos/potencias en sumas/factores y `exp` recupera rp; la fórmula es la derivada anterior, no una aproximación. Parámetros inválidos producen `ValueError`; desbordamiento o candidato no representable producen `ErrorNumerico`, encadenando el error original cuando existe. Ejemplo: `calcular_candidato_analitico(288.15,1600,1.4,.85,.9,.05)≈12.8950516696`.

### `buscar_maximo_numerico(T1, T3, gamma, cp, p1, eta_c=1, eta_t=1, delta=0, dominio=None, muestras=257, tolerancia_log=1e-9, max_iteraciones=100)`

Recibe ocho escalares, dominio opcional de Fase 1 y controles de §4.2. Devuelve `None` si no hay dominio, o diccionario:

| Clave | Contenido/unidad |
|---|---|
| `rp` | Mejor relación motora evaluada, sin unidades |
| `ciclo` | Diccionario de `evaluar_punto`: T/p, referencias isentrópicas, energías, rendimiento y clasificación |
| `intervalo_fisico`, `intervalo_busqueda`, `intervalo_final` | Pares de rp con los tres significados explicados |
| `paso_log_inicial`, `tolerancia_log` | Paso y parada en ln(rp), sin unidades |
| `resolucion_rp` | Escala de redondeo expresada en rp |
| `evaluaciones`, `iteraciones`, `muestras_iniciales` | Conteos enteros |

Llama a `validar_parametros`, a `calcular_dominios` cuando falta el argumento y a `evaluar_punto` mediante su función local. La llama el coordinador y las pruebas; no llama al candidato analítico. Rechaza controles inválidos con `ValueError`; usa `ErrorNumerico` para ventana irresoluble, extremo no acotado, falta de convergencia o falta de punto motor por encima de la banda cero. Propaga fallos de estados. Ejemplo: `buscar_maximo_numerico(288.15,1600,1.4,1005,100,.85,.9,.05)['rp']≈12.8950517350`.

La función local `evaluar(y)` recibe ln(rp) escalar, devuelve W con signo en kJ/kg, transforma con `exp`, exige interior estricto y memoriza el resultado completo de `evaluar_punto`. La llaman la comprensión inicial y los pasos de sección áurea. Su cierre contiene parámetros, límites y registros de esa búsqueda. Ejemplo interno: `evaluar(log(10))` sólo es admisible si rp=10 está dentro de los límites. Puede propagar errores físicos/numéricos; no escribe archivos.

### `optimizar_trabajo_neto(T1, T3, gamma, cp, p1, eta_c=1, eta_t=1, delta=0, dominio=None)`

Coordina las entradas físicas comunes y devuelve `estado`, `motivo`, `candidato`, `dominio`, `analitico`, `numerico` y `concordancia`. `analitico={'rp':...,'ciclo':...}` conserva estados, unidades y clasificación; `numerico` tiene el contrato anterior. `concordancia` contiene `diferencia_rp`/`tolerancia_rp` y `diferencia_trabajo`/`tolerancia_trabajo` (estas últimas kJ/kg).

Con vacío, `estado='sin_dominio'` y los tres campos de resultados físicos son `None`, aunque `candidato` conserva el número matemático. Sin búsqueda. Si existe intervalo pero el candidato no es interior/motor resoluble, o si discrepan métodos, lanza `ErrorNumerico`. Llama al cálculo/validación de dominio, candidato, evaluación física y búsqueda; la llaman `main` y pruebas. Ejemplo: `r=optimizar_trabajo_neto(288.15,1600,1.4,1005,100,.85,.9,.05)`; `r['analitico']['ciclo']['rendimiento']≈0.3921261442`.

### Presentador y firmas adaptadas

`seccion_optimizacion_html(parametros, referencias, optimizaciones, barrido)` recibe diccionarios de nueve parámetros, referencias `ideal/noideal`, estudios `ideal/noideal` y barrido o `None`. Devuelve str HTML, sin cálculo físico. Llama a `tabla_html`, la llama `crear_informe_html`; usa `escape`, bucles, f-strings, `enumerate/zip` y `join`. Presenta unidades, porcentaje, estados, diferencias y diagnósticos; vacío → «No disponible». No necesita una referencia para un estudio no disponible. Datos incompletos/incompatibles pueden producir `KeyError`/`TypeError`. Ejemplo conceptual con datos de esta ejecución: `seccion_optimizacion_html(parametros,{'ideal':ref_i,'noideal':ref_r},estudios,barrido)`.

Las funciones modificadas conservan su retorno y argumentos anteriores:

```python
construir_barrido(T1, T3, gamma, cp, p1, eta_c=1, eta_t=1, delta=0,
                 relaciones=None, dominios=None, puntos_interes=())
guardar_comparaciones_ciclos(T1, T3, gamma, cp, p1, eta_c, eta_t,
                            perdida_presion_combustor, imagenes, barrido=None,
                            optimizaciones=None)
crear_informe_html(parametros, ideal, noideal, detalles_ideal, optimo,
                   rendimientos, comprobaciones, imagenes, fecha, version,
                   barrido=None, optimizaciones=None)
```

El nuevo iterable `puntos_interes` exige rp finitos dentro de la vista cuando se construye automáticamente; el barrido añade `intervalo_visual`, además de puntos, máscaras y motivos ya existentes. El nuevo diccionario opcional `optimizaciones` permite dibujar/presentar estudios ya calculados. Ejemplo: `construir_barrido(...,dominios=d,puntos_interes=[rp_ref,rp_i,rp_r])`. `main(carpeta_salida=None,parametros=None)` mantiene firma/retorno Path, añade el cálculo de estudios antes del barrido y los pasa a gráficas/HTML. Los dos dibujadores ideales mantienen sus firmas, sólo fijan límites de la ventana recibida. Los llamadores siguen siendo `main` y pruebas. Errores de cálculo/dibujo/escritura se propagan; ni el presentador ni el dibujador ocultan fallos con una curva vacía inventada.

## 6. Python nuevo: qué es y qué debes aprender

### Cierre y caché local

Un cierre es una función interior que utiliza nombres de la función exterior. `evaluar` accede a `registros` y a T1/T3/etc. sin añadirlos como argumentos en cada paso. El diccionario memoriza cada rp evaluado durante una búsqueda:

```python
if rp not in registros:
    registros[rp] = evaluar_punto(T1, T3, gamma, cp, rp, p1, eta_c, eta_t, delta)
return registros[rp]['trabajo_neto']
```

Aprende que mutar ese diccionario local no crea una caché global: otra llamada recibe uno vacío. Eso permite reutilizar evaluaciones de la sección áurea sin arrastrar datos de otra ejecución de Flask.

### Sección áurea y asignación múltiple

El algoritmo compara dos puntos interiores c y d. Si `fc<fd`, descarta el tramo izquierdo; una evaluación ya sirve en el nuevo intervalo:

```python
izquierda, c, fc = c, d, fd
```

Python evalúa primero la derecha y asigna después los tres nombres; no hace tres asignaciones secuenciales con valores ya modificados. Ejemplo pequeño: `a,b=b,a` intercambia dos valores. Aprende a seguir qué coordenada y qué trabajo siguen emparejados.

### `for/else` para declarar convergencia

El `else` de un `for` se ejecuta si el bucle se agota sin `break`. Aquí `break` significa que la anchura satisface la parada; agotamiento significa lanzar error de convergencia. No es el `else` del `if`. Aprende a distinguir terminar por éxito de terminar por consumir el presupuesto de iteraciones.

### Elegir estructuras con `key=lambda`

`max(aceptados,key=lambda par:par[1]['trabajo_neto'])` compara el campo trabajo, pero devuelve el par completo (rp,punto). Ejemplo: `max([(2,8),(3,5)],key=lambda par:par[1])` devuelve (2,8). Aprende por qué devolver la estructura completa evita perder sus estados físicos asociados. Tuplas, diccionarios, comprensiones y `lambda` ya aparecían en el proyecto: se reutilizan y amplían, no se presentan como conceptos históricos nuevos por primera vez.

### Límites de representación y pruebas independientes

`np.finfo(float).eps` es una escala de separación relativa de números representables cerca de 1. Su raíz cuadrada orienta el efecto de redondeo cuando el objetivo cambia cuadráticamente cerca del máximo. `raise ErrorNumerico(...) from error` conserva la causa original; se reutiliza la separación previa entre entrada, inviabilidad y fallo numérico. La prueba que parchea el candidato para que lance una excepción mientras la búsqueda funciona demuestra independencia de caminos; comparar dos copias de la misma fórmula no la demostraría.

## 7. Ejemplo completo: valores predeterminados

Entradas: T1=288.15 K, T3=1600 K, gamma=1.4, cp=1005 J/(kg·K), rp_ref=10, p1=100 kPa, eta_c=0.85, eta_t=0.90, delta=0.05 (en Flask se escribe 5 %).

1. Fase 1 obtiene dominio ideal (1,403.4175203200) y no ideal (1.0696541023,155.4543260392). La referencia rp=10 pertenece a ambos.
2. El coordinador ideal recibe `dominios['ideal']` y eficiencias unidad; el no ideal recibe sus parámetros y `dominios['noideal']`.
3. Las ventanas numéricas son aproximadamente (1.0000060000,403.4150998334) y (1.0696594281,155.4535520314). Ninguna es la ventana de dibujo.
4. Cada búsqueda usa 297 evaluaciones únicas (257 iniciales); el criterio logarítmico termina en 38 iteraciones registradas.
5. Se incorporan rp=10 y ambos máximos a la malla visual: 1265 muestras en [1,423.5883963360]. Se generan seis PNG en memoria.
6. El HTML reúne los resultados siguientes, metadatos Git/aviso de cambios y estados; se publica completo y después se aplica la retención. Flask redirige al informe, que se puede descargar.

| Magnitud | Ideal | No ideal |
|---|---:|---:|
| W en rp=10 [kJ/kg] | 505.6190182490 | 369.4763010448 |
| rp* analítico | 20.0852562921 | 12.8950516696 |
| rp* numérico, con los dominios pasados por main | 20.0852560217 | 12.8950517350 |
| W máximo analítico [kJ/kg] | 532.8022301186 | 373.2108274827 |
| W máximo numérico [kJ/kg] | 532.8022301186 | 373.2108274827 |
| Diferencia absoluta rp entre métodos | 2.7045·10⁻⁷ | 6.5421·10⁻⁸ |
| Tolerancia de concordancia rp | 4.0171·10⁻⁵ | 2.5790·10⁻⁵ |
| Rendimiento en el máximo de trabajo [%] | 57.562546 | 39.212614 |

Estados no ideales en el máximo analítico:

| Estado | T [K] | p [kPa] |
|---|---:|---:|
| 1 | 288.150000 | 100.000000 |
| 2 | 652.972971 | 1289.505167 |
| 3 | 1600.000000 | 1225.029909 |
| 4 | 863.822971 | 100.000000 |

Δrp ideal menos no ideal=7.1902046225; ΔW máximo=159.5914026359 kJ/kg. Las eficiencias reducidas penalizan el trabajo. La pérdida también reduce la expansión disponible y modifica el candidato; no se debe afirmar que cualquier aumento de delta reduce necesariamente rp*: en la fórmula entra (1−delta)^(-a). Puede aumentar rp* mientras disminuye W o desaparece el dominio.

En llamadas autónomas sin dominio, incluso con eficiencias unidad, el módulo usa el intervalo `noideal` calculado por Fase 1, cuyas raíces por bisección pueden diferir a nivel de redondeo del límite ideal exacto. Por eso los últimos dígitos numéricos pueden diferir del flujo de `main`; no se atribuye a esas cifras precisión física.

## 8. Experimentos reproducibles sin generar informes

Ejecuta en un intérprete del entorno del proyecto:

```python
from optimizacion import optimizar_trabajo_neto
r = optimizar_trabajo_neto(288.15,1600,1.4,1005,100,.85,.9,.05)
print(r['estado'], r['analitico']['rp'], r['numerico']['rp'])
```

Estos casos se han calculado el 20 de octubre de 2026, con gamma=1.4, cp=1005 y p1=100. Son pruebas de adaptación matemática, no condiciones de operación recomendadas ni validación de cp constante a 20000 K.

| T1/T3 [K] | eta_c/eta_t/delta | Dominio no ideal aproximado | rp* analítico | W máximo [kJ/kg] |
|---|---|---|---:|---:|
| 300/324 | .99/.99/0 | (1,1.220196) | 1.104625 | 0.253272 |
| 288.15/5000 | .85/.90/.05 | (1.057081,8486.197352) | 94.713225 | 2362.363071 |
| 288.15/20000 | .85/.90/.05 | (1.053677,1089742.523921) | 1071.557819 | 13429.031142 |
| 288.15/2000 | .50/.60/.30 | (2.357300,7.894986) | 4.314029 | 26.286794 |
| 288.15/5000 | .80/.90/.70 | (3.806686,6035.666122) | 151.577995 | 1845.258235 |
| 288.15/300 | .50/.50/0 | vacío | No disponible | No disponible |

Preguntas y resultados esperados:

1. ¿Qué pierden las ventanas 2–30/1.01–50? El primer caso tiene óptimo por debajo de 2; los casos altos lo tienen por encima de 50. Una cota visual 10000 oculta fronteras en el tercero.
2. Repite el caso predeterminado después de uno alto. Debe dar el mismo estudio que al inicio: no hay datos del caso anterior en la caché.
3. Duplica cp y p1. rp* no cambia; W y todas las presiones se duplican. En la prueba Flask también cambian gamma, referencia y los restantes parámetros para comprobar el camino completo.
4. Usa `T3=288.15/(.85*.9)*(1+1e-4)` con delta=0. El dominio muy estrecho sigue teniendo un máximo resoluble. Sustituye 1e-4 por 1e-7: el máximo queda dentro de la banda cero y se espera `ErrorNumerico`, no una excepción ocultada ni un cero ficticio.
5. En el caso vacío, inspecciona `candidato` (aprox. 0.094847) y los campos `analitico/numerico` (None). Explica por qué el primero no es una solución motora.
6. Con eta_c=eta_t=1, delta=0, compara con `main.calcular_relacion_optima`: recupera el ideal dentro del redondeo.

Para experimentar desde Flask elige rp_ref interior: 1.1 para el primer caso, 4 para el de T3=2000 y 50 para T3=20000. Si la referencia es inviable, se conserva el mensaje de Fase 1. Un ciclo de referencia motor con dominio vacío sería contradictorio por definición; no se fuerza un informe exitoso para esa combinación. El API independiente permite estudiar el vacío y el presentador tiene soporte «No disponible».

## 9. Verificación realizada y resultados preservados

El 20 de octubre de 2026 se ejecutó:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

**55 pruebas superadas en 40.481 s**: 40 anteriores (11 informes, 11 web, 18 viabilidad) y 15 nuevas. No se elimina ni desactiva ninguna anterior. La expectativa numérica heredada 20.085236 del informe se actualiza porque el flujo utiliza otro método; se conservan sus comprobaciones de balances, seis imágenes actuales, dimensiones, archivos ajenos, historial, publicación y metadatos.

Las nuevas pruebas comparan fórmula independiente, segunda derivada/diferencias finitas, máximo conocido, estados, pertenencia a dominios para familias de parámetros, límite reversible, vacío sin búsqueda, dominio estrecho/banda cero, controles, independencia de la búsqueda, extremos fuera de intervalos antiguos, cp/p1, fronteras/máximos presentes en malla, máscaras NaN, paneles/marcadores, no disponible en HTML y cuatro POST con descarga y repetición del caso inicial. Las anteriores conservan ejecución directa de main, errores diferenciados, importación sin ejecutar/escuchar y retención de cuatro informes.

También se revisaron visualmente informes de parámetros predeterminados, T3=2000 con eficiencias .5/.6 y delta=.3, y T3=20000. Se generaron en `C:/Users/cjfer/.codex/visualizations/2026/10/17/01a14956-9360-78e1-b8b0-949cf8a296ce/fase2_revision`, fuera de `outputs/`, sin alterar su historial. Las comparaciones muestran fronteras y máximos, con detalle no ideal cuando procede. Los PNG históricos se conservan; las 13 funciones físicas originales se contrastan con la base mediante AST, sin añadir una prueba permanente que impida su evolución futura.

Son verificaciones de implementación, consistencia y contratos. No se han contrastado resultados con datos físicos externos ni se afirma validación experimental.

### Iteración del 20 de octubre de 2026 — intervalos dinámicos

El requisito adicional se integra en esta misma fase: la optimización usa los dominios recién calculados, se retira el tope visual fijo, se muestrean máximos/fronteras y se añaden paneles de detalle. Las pruebas de temperatura baja/alta, pérdidas elevadas y cambios consecutivos de Flask verifican esa adaptación. Se actualizan las explicaciones actuales del walkthrough y este mismo documento; no se crea un archivo de aprendizaje por ajuste menor.

## 10. Limitaciones y estado de entrega

Se conserva el modelo simplificado; cp/gamma y eficiencias constantes no describen propiedades reales en toda la gama de temperaturas de prueba. No hay caudal, potencia, mapas, combustible ni química. No se optimiza rendimiento (Fase 3), ni se añaden diagramas T-s/P-v no ideales.

La búsqueda puede informar límite numérico en casos casi degenerados o magnitudes no representables. Las ventanas y resultados son dinámicos dentro de las posibilidades de coma flotante; eso no promete resolver cualquier escalar finito. Un intervalo final diminuto no certifica sus dígitos. Los umbrales de paneles y densidad son decisiones de presentación/coste, independientes del dominio físico.

Fase 2 implementada y verificada en `feature/fase-2-optimizacion-noideal`, registrada en `c2f4bff84a173f3b354a5d0f76c2b7bd2ee1fa21`. Base conservada: `f9f9a0495c4231a4d48399fba4bccdcc0f6bcf6f`. El usuario autorizó posteriormente su commit, publicación e integración mediante un merge explícito en main. Los hashes de integración se consultan en Git; este documento no intenta incluir por adelantado el hash de su propio commit contenedor. La rama de Fase 3 se prepara sin desarrollar funcionalidades nuevas.

### Cierre autorizado del 20 de octubre de 2026

Se registra la asociación con el commit real de implementación y se sustituye el estado pendiente de la entrega inicial. Este cierre de Git no cambia código, ecuaciones ni resultados, ni inicia el desarrollo de Fase 3. Las 55 pruebas de la sección anterior corresponden a la verificación allí identificada; la repetición posterior al merge se informa al finalizar la integración.
