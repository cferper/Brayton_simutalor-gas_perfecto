# Fase 3 — Optimización del rendimiento térmico: guía de aprendizaje

Guía independiente del estado final de Fase 3, revisada el **20 de octubre de 2026**, para un estudiante de cuarto de Ingeniería Aeroespacial con Python básico. Integra las dos entregas provisionales sin duplicarlas. El [walkthrough](../../CODE_WALKTHROUGH.md) explica todo el proyecto; el [milestone técnico](05_optimizacion_rendimiento.md) resume este avance. Esta guía se centra en lo aprendido al pasar de Fase 2 a Fase 3.

## A. Punto de partida

Al terminar Fase 2 podíamos clasificar los dominios motores ideal/no ideal, obtener sus máximos de trabajo específico y comparar los modelos en seis gráficas HTML. Los nueve campos de Flask, Git en los informes, descarga e historial de cuatro ejecuciones ya existían. La base tenía 55 pruebas.

Faltaba responder otra pregunta de diseño: ¿qué rp maximiza la fracción del calor aportado convertida en trabajo? Un ciclo con el mayor W no tiene necesariamente la mayor eta=W/qin. Fase 3 mantiene el máximo de trabajo (A), calcula el máximo de rendimiento no ideal (B) cuando existe y muestra el compromiso entre ambos. También demuestra por qué el ideal sólo tiene un supremo no alcanzado.

No se cambian las hipótesis: gas ideal, cp/gamma constantes, equipos adiabáticos, eficiencias y pérdida relativa fijas, sin combustible/caudal ni mapas de máquinas. Las ecuaciones de estados y balances siguen en viabilidad.py. Esta es una ampliación de análisis, no un nuevo modelo físico.

## B. Cambios de código

| Archivo | Cambio respecto a Fase 2 | Funciones/contratos afectados |
|---|---|---|
| `optimizacion_rendimiento.py`, nuevo | Estudio de eta y comparación de objetivos | estudiar_rendimiento_ideal, calcular_candidato_rendimiento, buscar_maximo_rendimiento_numerico, optimizar_rendimiento, comparar_criterios |
| `main.py`, modificado | Coordina estudios de eta, añade B al barrido y séptima imagen | main, guardar_comparaciones_ciclos; nueva guardar_grafica_compromiso |
| `reporting.py`, modificado | Sección de eta/A/B, estados y límite ideal; siete PNG actuales | nueva seccion_rendimiento_html; crear_informe_html añade argumentos sólo por nombre y conserva formato anterior |
| `tests/test_optimizacion_rendimiento.py`, nuevo | 20 comprobaciones unitarias de física/métodos | RendimientoTests |
| `tests/test_integracion_rendimiento.py`, nuevo | Ocho comprobaciones de la integración | IntegracionRendimientoTests |
| `tests/test_optimizacion.py`, `test_reporting.py`, `test_web_app.py`, modificados | Conservan todos sus métodos; esperan siete imágenes actuales | Recuento, comentario de buffers y replay de kwargs del presentador |
| `CODE_WALKTHROUGH.md` y `README.md` | Manual y uso actualizados | Contratos, arquitectura, ejecución, ejemplos, pruebas y limitaciones |
| `docs/milestones/05_*.md`, nuevos | Milestone y esta guía de Fase 3 | Complementan el manual sin copiarlo completo |

viabilidad.py, optimizacion.py y las 13 funciones físicas originales de main permanecen intactos. web_app.py, templates/, static/, dependencias y seis PNG históricos también se conservan. Flask recibe los resultados nuevos por su llamada existente a main; no necesita más campos ni otra ruta.

### Contratos físicos de la API nueva

Las entradas físicas son escalares reales: T [K], cp [J/(kg·K)], p1 [kPa]; eficiencias, delta, gamma y rp adimensionales. Los ciclos conservan el contrato completo de `evaluar_punto`, incluidas temperaturas/presiones, trabajos/calor [kJ/kg], rendimiento fracción, viabilidad, motivos y bandas. Firmas y detalle de estructuras actuales también en [CODE_WALKTHROUGH apartado F8](../../CODE_WALKTHROUGH.md#438-rendimiento--optimizacion_rendimientopy).

### `estudiar_rendimiento_ideal(T1, T3, gamma, cp, p1)`

Recibe cinco parámetros, llama a `calcular_dominios` y devuelve motivo, dominio ideal y `estado='supremo_no_alcanzado'`. `candidato/analitico/numerico/concordancia` son None; `supremo` contiene rendimiento fracción, `rp_frontera` y `alcanzado=False`. La llaman usuarios/pruebas y los otros estudios en reversibilidad. Propaga validación `ValueError` o frontera irresoluble `ErrorNumerico`. Ejemplo: `estudiar_rendimiento_ideal(288.15,1600,1.4,1005,100)` ofrece supremo 0.81990625, no ciclo motor en rp≈403.41752032.

### `calcular_candidato_rendimiento(T1, T3, gamma, eta_c=1, eta_t=1, delta=0)`

Recibe seis parámetros térmicos, retorna float rp matemático o None en reversibilidad exacta. No usa cp/p1 porque cancelan. Llama a `validar_parametros` con cp=p1=1 auxiliares, sin hipótesis nueva. La llama el coordinador y las pruebas/usuarios; no localiza dominios ni evalúa estados. Lanza `ValueError` para entradas o `ErrorNumerico` para coeficientes/resultado/desbordamiento. Ejemplo de raíz matemática: `calcular_candidato_rendimiento(288.15,1600,1.4,.85,.9,.05)≈35.4523235708`; aún debe comprobarse que sea motor.

### `buscar_maximo_rendimiento_numerico(T1, T3, gamma, cp, p1, eta_c=1, eta_t=1, delta=0, muestras=257, tolerancia_log=1e-9, max_iteraciones=100)`

Ocho parámetros físicos y controles del apartado F. Llama a validación, cálculo actual de dominios, estudio ideal en reversibilidad y evaluación física mediante el cierre. La llaman coordinador y pruebas/usuarios. Con vacío devuelve motivo/dominio y rp/ciclo/supremo=None; con reversible, el contrato del estudio ideal. Con máximo devuelve estado/motivo/dominio, rp/ciclo, supremo=None, intervalos de búsqueda/final (pares de rp), paso logarítmico inicial, tolerancia logarítmica, escala `resolucion_rp` y conteos de muestras/evaluaciones/iteraciones. Los consumidores deben consultar `estado` antes de acceder a campos de un máximo.

Su función local `evaluar(y)` recibe ln(rp), devuelve eta fracción admisible o −infinito interno. Usa `exp`, límites abiertos y caché local; la llaman comprensión y refinamiento. Ejemplo interno: `evaluar(log(10))` consulta rp=10, sin exponer calor nulo a una división nueva. Propaga errores físicos de evaluación.

La búsqueda lanza `ValueError` por controles/entradas y `ErrorNumerico` si no hay ventana/malla/cima resoluble o no converge. Ejemplo: `buscar_maximo_rendimiento_numerico(288.15,1600,1.4,1005,100,.85,.9,.05)['rp']≈35.4523219222`. No usa el candidato para llegar a ese número.

### `optimizar_rendimiento(T1, T3, gamma, cp, p1, eta_c=1, eta_t=1, delta=0)`

Coordina ocho parámetros y devuelve `estado/motivo/dominio/candidato/analitico/numerico/concordancia/supremo`. En un máximo, `analitico={'rp':...,'ciclo':...}`, `numerico` tiene el contrato anterior y `concordancia` tiene diferencias y tolerancias de rp/rendimiento más `condicion_cociente` (todos adimensionales). Con vacío los cinco campos de resultados son None; con reversible retorna el estudio ideal.

Llama a dominios, estudio ideal, candidato, evaluación y búsqueda; lo llaman pruebas/usuarios directos. La llama `main`. Verifica candidato interior y viable antes de aceptarlo; puede propagar `ValueError` y lanzar `ErrorNumerico` por candidato no resoluble o desacuerdo. Ejemplo completo:

```python
from optimizacion_rendimiento import optimizar_rendimiento
r = optimizar_rendimiento(288.15,1600,1.4,1005,100,.85,.9,.05)
if r['estado'] == 'maximo_interior':
    punto = r['analitico']['ciclo']
    print(r['analitico']['rp'], punto['rendimiento']*100)
    print(punto['trabajo_neto'], punto['calor_aportado'])
```

### Comparación y presentación: contratos nuevos

`comparar_criterios(trabajo, rendimiento)` recibe los diccionarios finales del máximo trabajo y del estudio de eta para **los mismos parámetros**. Devuelve estado/motivo, punto_a y punto_b (rp/ciclo), diferencia_rp [adimensional], ganancia_rendimiento_pp [pp], reduccion_trabajo_porcentaje [%] y diferencia_calor [kJ/kg]. No recalcula física ni llama a funciones propias; la llaman main y pruebas. Si falta uno de los máximos, conserva A si existe y deja B/diferencias=None. Los datos deben respetar el contrato motor W_A>0; datos mal formados pueden producir KeyError/TypeError. Ejemplo: `c=comparar_criterios(w,r)` con los estudios ya calculados; `c['ganancia_rendimiento_pp']≈4.6804927411`.

`guardar_grafica_compromiso(barrido, comparacion, ruta)` recibe el barrido clasificado de esta ejecución, la comparación anterior y destino Path/cadena/BytesIO. Devuelve None y escribe un PNG 1350×900: W [kJ/kg] horizontal, eta [%] vertical, rp como parámetro. La llama main, no llama a otras funciones propias y usa plot/scatter sobre datos existentes. NaN evita puentes por muestras excluidas; A/B sólo se dibujan si existen. Propaga errores de estructura/dibujo/escritura. Ejemplo: `guardar_grafica_compromiso(barrido,c,buffer)`, seguido de `buffer.getvalue()` y `buffer.close()`.

`seccion_rendimiento_html(estudios, comparacion)` recibe dict con entradas ideal/noideal y comparación A/B. Devuelve str HTML con supremo, estado del máximo, resultados/estados/contraste y límites. Recibe eta fracción, T K, p kPa, W/qin kJ/kg y convierte eta a porcentaje al presentar. La llama crear_informe_html; llama a tabla_html y usa escape, f-strings, enumerate/zip/join. No modifica datos ni calcula física; pueden propagarse KeyError/TypeError si están incompletos. Ejemplo: `fragmento=seccion_rendimiento_html(estudios,c)`.

### Funciones existentes adaptadas: antes y después

```python
main(carpeta_salida=None, parametros=None)
guardar_comparaciones_ciclos(T1, T3, gamma, cp, p1, eta_c, eta_t,
                            perdida_presion_combustor, imagenes, barrido=None,
                            optimizaciones=None, estudio_rendimiento=None)
crear_informe_html(parametros, ideal, noideal, detalles_ideal, optimo,
                   rendimientos, comprobaciones, imagenes, fecha, version,
                   barrido=None, optimizaciones=None, *,
                   estudio_rendimiento=None, comparacion_criterios=None)
```

main conserva firma, nueve claves/unidades y retorno Path al informe. Antes coordinaba sólo máximos de trabajo; ahora añade estudios de eta y comparación de criterios. La llaman entrada protegida, Flask y pruebas. Propaga ErrorModelo para referencia no motora, ErrorNumerico para cálculo no resoluble y los fallos inesperados de código/publicación. Ejemplo sin alterar el historial habitual: `main(carpeta_salida=carpeta_temporal,parametros={'T3':1700})`.

guardar_comparaciones_ciclos conserva sus argumentos anteriores y None de retorno, añade estudio_rendimiento opcional, marca A/B en eta(rp) y W(rp) y conserva los dos buffers mutables de imagen. La llama main y llama a construir_barrido si falta, más marcar_dominio. No evalúa física; los errores de datos/dibujo/escritura se propagan. Un estudio debe corresponder al barrido y parámetros recibidos. Antes sólo marcaba máximos de trabajo en W; ahora también en eta y añade B cuando existe.

crear_informe_html conserva doce posiciones anteriores y retorno str; los dos argumentos de Fase 3 se pasan por nombre. Sin estudios sigue admitiendo seis imágenes; con ellos requiere siete claves y comparación asociada. Llama a los presentadores, tabla_html e imagen_html; la llama main. ValueError indica claves/firma PNG inválidas; datos ausentes pueden producir KeyError/TypeError. No escribe el informe: publicación y retención siguen en guardar_informe_html. Ejemplo de la extensión: `crear_informe_html(..., estudio_rendimiento=estudios, comparacion_criterios=c)`. Los puntos suspensivos sólo resumen los argumentos previos, no son una llamada lista para ejecutar.

## C. Cómo se ha implementado

1. Flask recibe texto de nueve campos. leer_parametros valida rangos, convierte a float y transforma la pérdida porcentual en fracción. La validación HTML no sustituye a la del servidor.
2. main copia parámetros, comprueba la referencia y calcula dominios actuales de Fase 1. Una referencia físicamente inviable conserva su rechazo anterior y no publica informe.
3. optimizar_trabajo_neto obtiene ambos máximos de Fase 2. Después se estudia el ideal/reversible y se optimiza eta no ideal mediante el módulo nuevo.
4. El estudio clasifica primero reversibilidad/vacío, obtiene un candidato cuando procede, comprueba motor interior y contrasta con una búsqueda que no utiliza la fórmula para elegir sus puntos.
5. comparar_criterios selecciona A/B y calcula diferencias de resultados disponibles. El valor rp del formulario sigue siendo referencia, sin limitar la búsqueda.
6. construir_barrido combina mallas y fronteras actuales. main le pasa referencia, máximos de trabajo y rp_B sólo si existe; el barrido conserva todos los puntos y sus motivos y ofrece arrays con NaN fuera del motor.
7. Los dibujadores generan los seis PNG anteriores y el séptimo de compromiso en buffers nuevos. Comparaciones frente a rp: círculo azul de máximo trabajo ideal, rombo naranja A y estrella verde B; fronteras discontinuas y panel no ideal de detalle si las escalas lo requieren.
8. crear_informe_html incorpora tablas, estados y siete imágenes Base64 sin recursos externos. Describe ideal como supremo, nunca como punto B alcanzado.
9. guardar_informe_html publica un archivo completo antes de aplicar retención de cuatro informes reconocidos; archivos ajenos y PNG históricos quedan fuera. Flask redirige por 303 y permite vista/descarga del mismo informe.
10. main cierra buffers/figuras con finally. Cada llamada usa configuración y cachés locales; los resultados del POST anterior no fijan dominios ni óptimos del siguiente.

```text
POST -> nueve parámetros -> dominio/referencia -> máximos W y estudio eta
     -> comparación A/B -> barrido con puntos de interés -> siete PNG
     -> HTML completo -> publicación -> retención -> GET/descarga
```

En el compromiso se representa (W(rp),100*eta(rp)) en orden de rp, sin ordenar por W ni eliminar muestras para volver a unirlas. La curva puede plegarse: varios rp dan un mismo trabajo con rendimientos distintos. No toda la curva es una frontera de Pareto; hay puntos dominados por otros de mayor W y eta. No se implementa un algoritmo de filtrado Pareto ni un nuevo objetivo de optimización.

## D. Conceptos nuevos de ingeniería

### Ideal: máximo frente a supremo

Con `a=(gamma−1)/gamma>0` y rp>1:

```text
eta_ideal(rp) = 1−rp^(−a)
d eta_ideal / d rp = a*rp^(−a−1) > 0
```

El dominio motor abierto es `1<rp<theta^(1/a)`, theta=T3/T1>1. La función crece estrictamente, así que cualquier punto motor admite otro a su derecha con mayor rendimiento: no existe máximo alcanzado. Su supremo es

```text
lim eta_ideal = 1−1/theta = 1−T1/T3
rp → theta^(1/a) por la izquierda
```

La frontera superior lleva T2=T3, T4=T1 y qin=W=0. El cociente W/qin es indeterminado en esa frontera y el punto no es motor. Es válido calcular el **límite** por la expresión simplificada; no es válido asignar ese valor a un ciclo admisible en la frontera.

**Aprendizaje:** un máximo requiere un punto del conjunto que alcance el valor; un supremo puede ser sólo el límite de valores alcanzables. En Python no se devuelve `rp_optima` ideal ni un ciclo artificial: `analitico/numerico/candidato=None` y un campo `supremo` con `alcanzado=False`.

### No ideal: derivación y condiciones

#### Variables y relación con Fase 1

| Símbolo | Definición | Unidad/interpretación |
|---|---|---|
| a | (gamma−1)/gamma | Adimensional, exponente isentrópico |
| x | rp^a | Adimensional, cambio de variable creciente |
| theta | T3/T1 | Adimensional, temperaturas extremas |
| B | 1+eta_c*(theta−1) | Cota de x para calor positivo |
| h | eta_c*eta_t*theta | Parámetro energético de Fase 1 |
| k | (1−delta)^(-a) | ≥1, pérdida en expansión |
| H | h*k | >0 |
| A | 1+h−B | Coeficiente que puede ser positivo, cero o negativo |
| C | cp/1000 | kJ/(kg·K) |

Se parte de las mismas temperaturas de `viabilidad.py`:

```text
T2 = T1*[1+(x−1)/eta_c]
T4 = T3*[1−eta_t+eta_t*k/x]
qin = C*(T3−T2) = C*(T1/eta_c)*(B−x)
W = C*[eta_t*T3*(1−k/x)−(T1/eta_c)*(x−1)]
  = C*(T1/eta_c)*N(x), N(x)=1+h−x−H/x
eta(x) = N(x)/(B−x), siempre con x<B y punto motor
```

Estas expresiones se derivan para estudiar la función; el módulo nuevo **no reimplementa** los estados ni balances. Para evaluarlos llama a `evaluar_punto` y recibe sus resultados/clasificación. cp cancela en el cociente, y p1 no aparece en las relaciones térmicas: la relación de presiones óptima y el rendimiento no dependen de sus escalas en este modelo. W y qin sí escalan con cp; las presiones escalan con p1.

#### Derivada y unicidad

Aplicamos la regla del cociente, recordando que d(B−x)/dx=−1:

```text
eta'(x) = [N'(x)*(B−x)+N(x)]/(B−x)^2 = F(x)/(B−x)^2
N'(x) = −1+H/x^2
F(x) = A+H*B/x^2−2*H/x
F'(x) = N''(x)*(B−x) = −2*H*(B−x)/x^3 < 0
```

F decrece estrictamente mientras qin>0. Su signo puede cruzar cero a lo sumo una vez; no es necesario suponer que eta sea globalmente cóncava en rp ni en ln(rp). Como x y ln(rp) crecen con rp, un aumento seguido de descenso se conserva bajo esos cambios de variable. Esa unimodalidad, y no una concavidad inventada, justifica la sección áurea.

#### Por qué hay máximo con cualquier pérdida estricta si existe motor

Introducimos

```text
S = H−A*B = Q(B)
  = (B−1)*(B−h)+h*(k−1)
B−h = (1−eta_c)+eta_c*theta*(1−eta_t) >= 0
B−1 = eta_c*(theta−1) > 0
```

S es no negativa. Sólo es cero si eta_c=eta_t=1 y delta=0. Cualquier pérdida estricta hace S>0, por pequeña que sea en matemáticas exactas. Además `N(B)=−S/B<0`: el calor nulo queda después de la frontera superior de trabajo de un dominio motor no vacío.

La condición W>0 de Fase 1 es `Q(x)=(x−1)*(x−h)+h*(k−1)<0`. Si existe motor, h>1 y las dos raíces de trabajo son distintas. La inferior coincide con las cotas de compresión/expansión sin pérdida de presión y queda por encima de ellas con pérdida positiva; la superior queda por debajo de B. En ambas, N=0 y el denominador B−x es positivo. N cruza de negativo a positivo en la inferior (N'>0) y de positivo a negativo en la superior (N'<0). Por tanto F es positiva en la inferior y negativa en la superior.

Continuidad + decrecimiento estricto de F prueban **existencia y unicidad de un máximo interior**. En el punto estacionario:

```text
eta''(x*) = F'(x*)/(B−x*)^2 = −2*H/[x*^3*(B−x*)] < 0
```

Si el dominio es vacío, no hay máximo motor. Si todas las pérdidas desaparecen exactamente, eta vuelve a ser estrictamente creciente y sólo tiene el supremo ideal. Si el dominio o la cima no se resuelven por encima de las bandas numéricas, se lanza `ErrorNumerico`: eso no equivale a vacío matemático ni a reversibilidad.

#### Solución cerrada estable

La estacionariedad se reduce a:

```text
P(x)=A*x^2−2*H*x+H*B=0
x*=(H−sqrt(H*S))/A                  si A no es cero
x*=B/(1+sqrt(S/H))                 forma racionalizada general
rp*=exp(log(x*)/a)
```

La primera forma puede restar números próximos y falla como expresión cuando A=0; la racionalizada evita ambos problemas y también sirve con A<0. En la reversibilidad S=0 daría x*=B, la frontera excluida. El código identifica primero ese caso y retorna `None` para el candidato, no lo ofrece como máximo.

La suma no negativa de S evita calcular `H−A*B` por cancelación. `B−h` se forma como suma `(1−eta_c)+eta_c*theta*(1−eta_t)`. `k−1` se obtiene mediante `expm1(−a*log1p(−delta))`: así no se pierde una pérdida muy pequeña al restar 1 de una exponencial ya redondeada.

**Comparación con Fase 2:** en el máximo de trabajo, N'=0 y N>0, de modo que F=N>0. El rendimiento todavía está creciendo allí. Su único máximo aparece a mayor x/rp cuando hay pérdidas y dominio motor; no coincide con el máximo de trabajo. No estamos cambiando la función objetivo de Fase 2, sino estudiando otra.

## E. Conceptos nuevos de Python

Las herramientas siguientes aparecen realmente en Fase 3. Algunas ya existían en Fase 2: se reutilizan con otra función objetivo y condiciones de aceptación.

### 1. Funciones estables: log1p y expm1

**Definición:** log1p(z)=ln(1+z) y expm1(z)=exp(z)−1, calculadas evitando perder el pequeño incremento por redondeo. **Motivo/lugar:** calcular_candidato_rendimiento necesita conservar delta muy pequeño y una S positiva sin restas de cantidades casi iguales.

```python
k_menos_uno = expm1(-a * log1p(-delta))
B_menos_h = (1 - eta_c) + eta_c * theta * (1 - eta_t)
S = eta_c * (theta - 1) * B_menos_h + h * k_menos_uno
```

**Práctica:** importa exp/expm1 y compara `exp(1e-16)-1` con `expm1(1e-16)`. La primera puede ser cero; la segunda conserva un incremento próximo a 1e-16. Aprende que igualdad algebraica no garantiza la misma precisión numérica.

### 2. Estados y None para resultados que no existen

**Definición:** un diccionario guarda pares clave/valor; una clave estado permite distinguir estructuras disponibles. None representa ausencia, no el número cero. **Motivo/lugar:** estudiar_rendimiento_ideal y optimizar_rendimiento no deben fabricar un óptimo cuando sólo hay un supremo o dominio vacío. main consulta estado antes de añadir B.

```python
if estudio_rendimiento['noideal']['estado'] == 'maximo_interior':
    puntos_interes.append(estudio_rendimiento['noideal']['analitico']['rp'])
```

**Práctica:** compara `optimizar_rendimiento(288.15,1600,1.4,1005,100)` con la misma llamada añadiendo `.85,.9,.05`. Explica por qué sólo la segunda permite acceder a analitico/rp. No sustituyas None por cero para obtener una tabla aparentemente completa.

### 3. Cierre y caché local (concepto reutilizado)

**Definición:** una función interior puede usar parámetros y variables del ámbito exterior; un diccionario local memoriza evaluaciones ya hechas. **Motivo/lugar:** evaluar(y), dentro de buscar_maximo_rendimiento_numerico, conserva estados por rp durante una única búsqueda.

```python
if rp not in registros:
    registros[rp] = evaluar_punto(T1, T3, gamma, cp, rp, p1, eta_c, eta_t, delta)
punto = registros[rp]
return punto['rendimiento'] if punto['viable'] else -np.inf
```

**Práctica:** reproduce la idea con `cache={}` y una función pequeña que guarda n*n cuando n no está en cache. Llama dos veces con n=3. Después crea otro diccionario vacío: eso ilustra por qué una ejecución nueva no hereda parámetros anteriores. −infinito sólo excluye una puntuación interna del argmax; no es un rendimiento físico.

### 4. Sección áurea, asignación múltiple y for/else (reutilizados)

**Definición:** se reduce un intervalo unimodal conservando una evaluación anterior. Python evalúa el lado derecho de una asignación múltiple antes de asignar los nombres de la izquierda. **Motivo/lugar:** buscar_maximo_rendimiento_numerico aplica sección áurea sin depender del candidato.

```python
if fc < fd:
    izquierda, c, fc = c, d, fd
    d = izquierda + razon * (derecha - izquierda)
    fd = evaluar(d)
```

**Práctica:** usa `a,b=2,5; a,b=b,a` y comprueba el intercambio. Después sigue en papel un paso con fc<fd. El else de un for se ejecuta si se agotan iteraciones sin break: aquí produce ErrorNumerico, mientras que break significa criterio de parada alcanzado.

### 5. Argumentos sólo por nombre y reenvío de kwargs

**Definición:** el asterisco aislado en una firma obliga a nombrar los argumentos que le siguen. **Motivo/lugar:** crear_informe_html añade estudios y comparación sin cambiar las posiciones de Fase 2; las pruebas de replay deben reenviar también kwargs.

```python
estudio_rendimiento=estudio_rendimiento,
comparacion_criterios=comparacion_criterios,
```

Éste es el fragmento real de la llamada final de main. **Práctica:** define `def mostrar(x, *, unidad='K'): return str(x)+' '+unidad` y llama `mostrar(300,unidad='K')`. Un segundo argumento posicional debe rechazarse. **Qué aprender:** ampliar un contrato explícitamente conserva la compatibilidad y evita confundir objetos de distintas fases.

### 6. Arrays y buffers para conservar coherencia (reutilizados)

**Definición:** un array representa una secuencia numérica; NaN interrumpe el trazado y BytesIO almacena bytes de una figura sin un archivo intermedio. **Motivo/lugar:** guardar_grafica_compromiso usa dos arrays emparejados del mismo barrido, ya clasificados.

```python
ejes.plot(real['trabajo_neto'], real['rendimiento'] * 100,
          color='tab:orange', label='Ciclo no ideal · rp variable, sólo interior motor')
```

**Práctica:** crea x=[1,2,np.nan,4] e y=[10,20,np.nan,40] y dibújalos en una figura de práctica: no debe existir segmento que puente el hueco. No elimines NaN antes de dibujar. La imagen del informe sale de getvalue() del buffer actual, no de un PNG histórico del disco.

## F. Algoritmos numéricos

### Tipos de resultado

| Situación | Resultado |
|---|---|
| Ideal o parámetros exactamente reversibles | `estado='supremo_no_alcanzado'`; sólo límite/frontera, sin ciclo óptimo |
| No ideal, dominio abierto no vacío y máximo resoluble | `estado='maximo_interior'`; candidato comprobado, ciclos y contraste |
| Dominio motor vacío | `estado='sin_dominio'`; valores de máximo no disponibles |
| Entrada incorrecta | `ValueError` |
| Cálculo/banda/precisión/convergencia no resoluble | `ErrorNumerico`, no otro tipo de solución ficticio |

No se usa `isclose` para convertir parámetros casi ideales en exactamente ideales. Los últimos casos pueden tener máximo interior extremadamente próximo a la frontera: se intenta resolverlo y se comunica el límite numérico cuando corresponde.

### Búsqueda independiente

Cada llamada recalcula `calcular_dominios` con los ocho parámetros actuales. No recibe intervalos persistidos ni usa la raíz analítica para escoger ventanas o puntos. Se construyen 257 muestras en y=ln(rp) y se refina por sección áurea entre los vecinos de la mejor muestra. El margen interior es sólo `8*eps*max(1,abs(ylo),abs(yhi))`, relativo a la representación de y; evita el redondeo hacia las fronteras sin el recorte relativo 10⁻⁶ de la búsqueda de trabajo, que podría ocultar una cima casi reversible.

Se reutilizan NumPy y biblioteca estándar, sin SciPy. Si no hay muestras admisibles o la malla no acota un máximo interior, se lanza error. La banda cero puede recortar parte del dominio físico: el conjunto de puntos aceptables no redefine el intervalo motor matemático.

La función local `evaluar(y)` mantiene una caché de estados sólo durante esa llamada. En puntos excluidos usa −infinito como puntuación interna; jamás lo devuelve como rendimiento físico ni divide por qin dentro de la banda cero. Las energías y el rendimiento se consultan a `evaluar_punto`. El máximo se elige entre los registros `viable=True`.

Se exige además algún testigo admisible a cada lado con rendimiento inferior en más de 64*eps. Si el mejor punto queda pegado a un recorte numérico sin descenso observable al otro lado, se rechaza como máximo no resuelto. No se fuerza un extremo de malla como máximo ni como supremo. Esta salvaguarda es conservadora; no certifica todos los dígitos.

### Tolerancias distintas

- Parada: ancho en ln(rp)≤10⁻⁹, hasta 100 iteraciones por defecto.
- Controles de API: 5–4097 muestras; 1–1000 iteraciones; 0<tolerancia_log<1. Booleanos no son conteos aceptados.
- Escala de resolución informada: `rp*max(tolerancia_log,32*sqrt(eps))`, reutilizando la idea de Fase 2.
- Concordancia rp: `|Δrp|≤2e−6*max(rp_a,rp_n)`.
- Concordancia eta: `|Δeta|≤max(1e−10,64*eps*condicion)`, con `condicion=(cp/1000*T3)/min(qin_a,qin_n)`.

La última escala reconoce la amplificación del redondeo al dividir por un calor pequeño. No es validación física ni una cota de error rigurosa. El intervalo refinado puede no contener el mejor registro si se producen empates de redondeo; su anchura no representa la precisión real de rp. El código muestra error explícito si los métodos discrepan con estas tolerancias.

### Relación entre tres intervalos

El dominio físico abierto procede íntegramente de calcular_dominios; no cambia al aumentar la resolución. La ventana numérica sólo evalúa su interior y no se usa como límite visual. La vista de rp abarca desde 1 hasta un margen sobre el límite ideal, con muestras en fronteras y óptimos, y puede añadir un panel no ideal ampliado. Ninguna ventana fija 2–30 o 1.01–50 limita el estudio actual.

La razón áurea sólo requiere unimodalidad: el signo único de F permite usarla también en ln(rp), sin afirmar concavidad global de eta. Las bandas de aceptación numérica pueden recortar una parte del dominio matemático. Si no hay descenso admisible observable a ambos lados, se rechaza una cima de frontera numérica. La fórmula analítica se usa después para contrastar, no para escoger ventana ni solución numérica.

## G. Ejemplo completo

Parámetros anteriores predeterminados: T1=288.15 K, T3=1600 K, gamma=1.4, cp=1005 J/(kg·K), p1=100 kPa, eta_c=.85, eta_t=.90, delta=.05. El rp_ref=10 de la interfaz no entra en esta API: es referencia de comparación, no restricción de búsqueda.

| Magnitud | Máximo trabajo Fase 2 | Máximo rendimiento |
|---|---:|---:|
| rp analítico | 12.8950516696 | 35.4523235708 |
| Rendimiento [%] | 39.2126144220 | 43.8931071631 |
| Trabajo [kJ/kg] | 373.2108274827 | 313.7389152634 |
| Calor aportado [kJ/kg] | 951.7621637414 | 714.7794620632 |

Para rendimiento, rp numérica≈35.4523219222 y eta numérica≈0.438931071631265. Diferencia rp≈1.64856·10⁻⁶ frente a tolerancia≈7.09046·10⁻⁵; diferencia eta≈5.55·10⁻¹⁷ frente a 10⁻¹⁰. Se usan 297 evaluaciones únicas y 38 iteraciones registradas. La ventana de búsqueda≈(1.0696541022628128,155.45432603919744) se deriva del dominio de Fase 1; no es una ventana fija ni una figura nueva.

Estados en el máximo analítico de rendimiento:

| Estado | T [K] | p [kPa] |
|---|---:|---:|
| 1 | 288.150000 | 100.000000 |
| 2 | 888.776655 | 3545.232357 |
| 3 | 1600.000000 | 3367.970739 |
| 4 | 687.195320 | 100.000000 |

Ideal: supremo≈81.990625 % cuando rp tiende a 403.41752032 por la izquierda. Ese punto límite no aparece como óptimo admisible ni se evalúa un ciclo con qin=0.

La referencia rp=10 sigue dando W=505.6190182490 kJ/kg y eta=48.2052532077 % en el ideal; W=369.4763010448 kJ/kg y eta=36.8987323745 % en el no ideal. El estudio de óptimos no sustituye la referencia del formulario.

El barrido predeterminado actual tiene **1282 muestras** en [1,423.5883963360], incluyendo rp=10, máximos de trabajo y rp_B. Ese recuento depende de la deduplicación; no es una constante física ni se usa como criterio de precisión. El informe reúne los nueve valores, los dos dominios, estudios, estados óptimos y siete PNG 1350×900; main conserva su resumen de tres líneas.

Diferencias B respecto a A: Δrp=22.5572719011, ganancia=4.6804927411 puntos porcentuales, reducción relativa de trabajo=15.9352054763 % y Δqin=−236.9827016782 kJ/kg. La ganancia en pp es la resta entre porcentajes, no un incremento relativo. Un rendimiento mayor no equivale a más trabajo útil por kilogramo.

## H. Experimentos prácticos

Se proponen seis experimentos reproducibles. Desde Flask la pérdida se introduce en porcentaje; desde Python delta es fracción. Las llamadas a API no generan archivos. Para informes experimentales de Python utiliza una carpeta temporal alternativa, conservando el historial habitual.

1. **Separar objetivos.** Ejecuta los valores predeterminados. Espera A rp≈12.895052, eta≈39.212614 %, W≈373.210827 kJ/kg; B rp≈35.452324, eta≈43.893107 %, W≈313.738915 kJ/kg. Identifica ambos símbolos en eta(rp), W(rp) y compromiso; explica por qué B queda a la izquierda de A en el eje W.
2. **Reversibilidad exacta.** Mantén T1/T3 y rp_ref=10, usa eta_c=eta_t=1 y pérdida 0 %. Espera supremo≈81.990625 %, sin máximo interior de eta ni punto B. Los dos máximos de trabajo se superponen y se recuperan los estados ideales. No intentes evaluar W/qin en la frontera de calor nulo.
3. **Efecto de escala.** Duplica cp de 1005 a 2010 y p1 de 100 a 200. rp_A/rp_B y rendimientos permanecen; W y qin se duplican, y las cuatro presiones se duplican. Ejemplo directo: `optimizar_rendimiento(288.15,1600,1.4,2010,200,.85,.9,.05)`. Compara con la llamada de §G.
4. **Óptimos fuera de ventanas antiguas.** Caso frío T1=300, T3=324, eficiencias .99/.99, pérdida 0 %, rp_ref=1.1: B rp≈1.140760 y eta≈1.822540 %. Caso caliente T1=288.15, T3=5000, eficiencias .85/.9, pérdida 5 %, rp_ref=40: B rp≈691.384059 y eta≈67.887012 %. Comprueba que ambos se ven sin modificar intervalos a mano. El caso caliente verifica adaptación matemática, no propiedades reales del aire a esa temperatura.
5. **Casi reversible y calor pequeño.** Usa eta_c=eta_t=.9999, pérdida **0.01 %** (delta=.0001) y referencia 10. Espera B rp≈371.446659 y eta≈81.123797 %, con calor/trabajo positivos: hay máximo interior, aunque próximo al límite ideal. No se reclasifica como reversible por aproximación. Con delta=1e-12 y eficiencias 1 puedes estudiar más de cerca la pérdida de precisión y el aumento de condicion_cociente.
6. **Vacío y banda cero.** T1=288.15, T3=300, eficiencias .5/.5, pérdida 0 %, referencia 10: Flask debe mostrar el rechazo de Fase 1 sin nuevo informe, y `optimizar_rendimiento(288.15,300,1.4,1005,100,.5,.5,0)` retorna sin_dominio. Para estudiar un dominio estrecho, usa desde Python T3=288.15/(.85*.9)*(1+1e-4), delta=0: máximo resoluble. Con 1e-7 en vez de 1e-4, espera ErrorNumerico por banda cero, no un nuevo supuesto físico.

## I. Limitaciones

- Modelo educativo de gas ideal con cp/gamma y eficiencias constantes, pérdida fija, equipos adiabáticos y energías cinética/potencial despreciables. No incorpora química, combustible, caudal, potencia, empuje ni mapas.
- T-s y P-v siguen siendo del ideal de referencia. La curva W-eta no implementa filtrado Pareto ni optimización multiobjetivo.
- Coma flotante y bandas cero limitan las cimas casi degeneradas. Cerca de qin=0 el cociente amplifica el redondeo: tolerancia de concordancia, paso inicial y anchura final no garantizan dígitos físicos exactos. Incluso una eta numérica ligeramente por encima del límite ideal por ruido debe interpretarse con esa escala y las limitaciones del cociente, no como mejora física.
- main exige referencia motora en ambos modelos para generar diagramas y tablas coherentes. Vacío y puntos no motores pueden analizarse con las funciones independientes. Un punto de referencia motor y dominio vacío serían contradictorios, por eso no se fuerza un informe exitoso.
- Retención de cuatro informes propios sin bloqueo entre procesos independientes. La interfaz continúa local y secuencial, sin despliegue público.
- Todas las comprobaciones descritas verifican implementación, consistencia y almacenamiento. No hay validación experimental contra un motor ni estimación de incertidumbre física a partir de estas tolerancias.

## J. Relación con Git y verificación de cierre

Rama de desarrollo: `feature/fase-3-optimizacion-rendimiento`. Base verificada antes de parte 1 y preservada durante toda la fase: `5629eb076d10ad54852f74a438fda8a970db5f04`, merge de Fase 2. Al empezar no había cambios seguidos; `zip.zip` ya estaba sin seguimiento. Permanece ajeno a la fase y no se añade ni modifica.

**Commit de implementación de Fase 3:** `44145f3553ee502ed7d547762651d12ca1c41d40` — `Implement Brayton thermal efficiency optimization and work trade-off`. La base no contiene Fase 3. El hash se incorpora en el cierre de Git posterior autorizado por el usuario; la entrega inicial permanecía sin commit para revisión. Código y documentación educativa se registran juntos. La rama de desarrollo se publica mediante push normal y la integración se registra con un merge explícito en main. El hash del merge se consulta en Git: no se intenta incrustar por adelantado el del propio commit contenedor.

### Resultado final y conservación de Fases 1/2

El 20 de octubre de 2026 se ejecutó la orden solicitada:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

**83/83 pruebas OK en 51.733 s** en la verificación de cierre. Se mantienen los 55 métodos de Fase 2 (11 informes, 11 web, 18 viabilidad, 15 optimización de trabajo) y se añaden 20 unitarios de rendimiento y ocho de integración. Las expectativas de número de imágenes cambian legítimamente de seis a siete y el replay del presentador reenvía sus kwargs; no se elimina ni desactiva ningún método anterior.

Se verifican: balances/unidades, monotonía y supremo, fórmula estacionaria y curvatura/unicidad, límite reversible y casi reversible, dominio vacío/estrecho, controles/errores, independencia de caminos, candidatos por debajo de 2 y por encima de 50, invariancia cp/p1, recálculo entre POST, relación HTML/física, marcadores, NaN, compromiso admisible, siete PNG sin recursos externos, descarga, retención de cuatro, archivos ajenos, errores físicos/numéricos/internos e importación/punto de entrada de main. Los seis PNG históricos y las 13 funciones físicas originales se comparan con la base; viabilidad.py y optimizacion.py se conservan.

Revisión científica adicional en este cierre: 80 configuraciones estrechas entre incrementos 2.108e-5 y 2.2e-5 de h sobre 1, comprobando las cimas que Fase 1 clasifica como viables; los casos comprobados no requirieron corrección funcional. Se revisaron pérdidas de presión de 1e-4, 1e-8, 1e-12 y 1e-16 para eficiencias unidad: se conservan la distinción de estados y las tolerancias que reflejan el mal condicionamiento del cociente.

### Revisión visual real y alcance

En este cierre se generaron tres informes aislados: predeterminado; T3=2000, eta_c=.5, eta_t=.6, pérdida 30 %, referencia 4; casi reversible eta_c=eta_t=.9999, pérdida .01 %, referencia 10. Se inspeccionaron visualmente los PNG reales de compromiso y comparaciones, incluyendo paneles de detalle, unidades, leyendas y marcadores. Los archivos de revisión están fuera del repositorio, en `C:/Users/cjfer/.codex/visualizations/2026/10/17/01a14956-9360-78e1-b8b0-949cf8a296ce/fase3_cierre_d95nnfhi`. La estructura y recursos HTML se comprobaron automáticamente; no se afirma una inspección completa del documento HTML en navegador. No se utilizó outputs para estas revisiones.

### Iteraciones relevantes de la fase

- **20 de octubre de 2026, parte 1:** derivación, clasificación de extremos, candidato estable y búsqueda independiente; 20 unitarias nuevas, 75 pruebas completas OK en aquella ejecución.
- **20 de octubre de 2026, parte 2:** integración en main/HTML/Flask, puntos A/B y séptima gráfica; ocho pruebas nuevas, 83 OK en aquella ejecución.
- **20 de octubre de 2026, parte 3:** revisión científica/documental y visual, reorganización de esta misma guía en A–J, milestone 05 y README/manual sincronizados; 83 OK en el cierre actual. Sin nuevas funcionalidades ni Fase 4.

### Cierre de Git autorizado

Después de la revisión el usuario autorizó commit, publicación e integración de Fase 3. La suite previa al commit se repitió con **83/83 OK en 52.699 s**. Se registra el hash real de implementación y se prepara la rama `feature/fase-4-sensibilidad-parametrica` desde main actualizado, sin desarrollar funcionalidades de Fase 4. La verificación posterior al merge se comunica al finalizar la integración. Este cierre no cambia ecuaciones, métodos, gráficas ni resultados físicos.
