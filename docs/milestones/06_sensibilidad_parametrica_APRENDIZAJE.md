# Fase 4 — Sensibilidad paramétrica: guía de aprendizaje independiente

Documentación de la implementación del **20 de octubre de 2026**. Dirigida a cuarto de Ingeniería Aeroespacial con Python básico. Explica las novedades de esta fase; el [manual actual](../../CODE_WALKTHROUGH.md#440-sensibilidad-ofat--sensibilidadpy-html-y-flask) contiene sus contratos junto al resto del proyecto y el [milestone técnico](06_sensibilidad_parametrica.md) resume el avance.

## A. Punto de partida verificado y alcance

La rama de desarrollo de esta fase es `feature/fase-4-sensibilidad-parametrica`. Su HEAD inicial coincidía exactamente con main: `899024c518348fa48944041059aa885cc127af7e`, merge de Fase 3. Esa base incluye el commit de implementación `44145f3553ee502ed7d547762651d12ca1c41d40`; el historial se ha consultado, sin reescribirlo. `zip.zip` ya estaba sin seguimiento al empezar y permanece intacto. Al inicio no había commit de Fase 4; la asociación de la implementación registrada después se recoge en §K. La base no debe citarse como si contuviera esta implementación.

Existían dominios motores, máximo de trabajo ideal/no ideal, supremo ideal y máximo de rendimiento no ideal, comparación A/B, siete gráficas HTML, nueve parámetros Flask, descarga, metadatos Git y retención de cuatro informes. Había 83 pruebas. Las guías anteriores conservan su contexto histórico; esta fase no añade sus capacidades retrospectivamente a ellas.

Faltaba comparar cómo cambian los resultados al variar T1, T3, eficiencias o pérdida manteniendo el resto. Ahora se añade ese estudio, con disponibilidad y derivadas fiables cuando se pueden calcular. No cambian ecuaciones ni hipótesis: gas ideal, cp y gamma constantes, equipos adiabáticos y pérdida relativa fija **por muestra**. No hay combustión química, caudal, potencia, empuje ni mapa rp–T3.

### Iteración del 20 de octubre de 2026 — implementación y revisión completa

Se incorporan núcleo OFAT, controles Flask, tres gráficas, informe y 24 pruebas. La primera ejecución aislada con archivos encontró permisos del sandbox sobre temporales Windows; no se interpretó como un fallo físico. La suite con acceso adecuado pasó 107 pruebas. La revisión visual detectó que el autoajuste de Matplotlib ocultaba los primeros valores de x cuando todas sus curvas eran NaN: se fijó explícitamente todo el intervalo configurado y se añadió una aserción. Verificación final: 107/107 pruebas OK en 131.473 s, tras el ajuste visual. Esta subsección registra la iteración relevante; el manual explica directamente el comportamiento final.

### Iteración del 21 de octubre de 2026 — consigna frente a punto motor

`crear_graficas_sensibilidad(estudio)` conserva firma/retorno y no recalcula física. Antes sustituía el array de rp de R por `np.full`, ofreciendo una sola línea horizontal R ambigua. Ahora conserva el array operativo con NaN, lo muestra con círculos y añade **otra** línea gris punto-raya, «Consigna rp de referencia (no indica viabilidad)». `np.full(n,rp_ref)` sólo construye esa consigna; no rellena datos operativos. La escala considera ambas clases de líneas, pero el aviso de ausencia de resultados sólo consulta `datos_operativos`, la lista de tres arrays R/A/B. La consigna no puede hacer pasar por disponible un resultado ausente. El HTML aclara la distinción.

Ingeniería: una entrada elegida puede conservarse aunque no exista un motor admisible. Python: se separa el array enmascarado de resultados de otro array auxiliar para dibujar la configuración; `np.isfinite` y `any` comprueban disponibilidad, y `marker`, `linestyle`, `color` y `zorder` distinguen trazados sin alterar datos. Las demás figuras mantienen sus máscaras. No cambian ecuaciones, optimizadores ni sus resultados.

Nueva prueba `test_consigna_rp_separada_de_resultados_motores_con_t3_inviable(self)`: T3 de 200 a 1600 K, 15 muestras, con R disponible y no disponible. El callback local `capturar(figura, *args, **kwargs)` intercepta `savefig`, conserva las líneas reales y devuelve el guardado original; no modifica cálculo ni archivos del usuario. Verifica los nueve arrays operativos frente al estudio, sus NaN, el estilo/leyenda de la consigna constante y los marcadores R. La suite conserva las 107 pruebas anteriores y añade ésta: 108/108 pruebas correctas en 147.931 s con la suite completa, incluyendo la nueva prueba de consigna y máscaras. Es verificación interna, no validación experimental.

## B. Qué archivos cambian y por qué

| Archivo | Papel nuevo o modificado |
|---|---|
| `sensibilidad.py`, nuevo | Validación/malla, copia OFAT, evaluador R/A/B, derivadas, datos, tres PNG y coordinación de publicación |
| `reporting.py` | Nuevo presentador de sensibilidad; reutiliza tablas, PNG Base64, Git, marcas y guardado |
| `web_app.py` | `index()` distingue botones normal/OFAT; `error_interno()` pasa opciones y conserva datos |
| `templates/index.html` | Sección independiente con selector/rango/muestras y sugerencias por parámetro |
| `static/style.css` | Estilo del selector coherente con los campos |
| `tests/test_sensibilidad.py`, nuevo | 19 pruebas de cálculo y seis de integración |
| `tests/test_web_app.py` | Conserva métodos anteriores; el formulario tiene 12 inputs numéricos: nueve físicos y tres OFAT |
| `CODE_WALKTHROUGH.md`, `README.md` | Estado actual y procedimiento de uso |
| `06_sensibilidad_parametrica.md` y esta guía | Hito técnico y aprendizaje independiente |

`main.py`, `viabilidad.py`, `optimizacion.py`, `optimizacion_rendimiento.py`, dependencias y los seis PNG históricos no se modifican. Reutilizar esas funciones permite contrastar el estudio contra evaluaciones individuales existentes. El almacenamiento tampoco se duplica: ambos tipos de informe usan el guardado anterior.

Antes, todo POST válido ejecutaba `main`. Ahora `index` convierte las mismas nueve entradas y consulta el botón `accion`: normal mantiene ese camino; sensibilidad valida cuatro controles y llama a `ejecutar_sensibilidad`. Los errores de configuración se capturan antes del cálculo; un ValueError inesperado del cálculo no se convierte en un rechazo físico, sino en el tratamiento 500 ya existente. La referencia debe cumplir T3>T1; no tiene que ser motora a rp fija para OFAT. Las combinaciones térmicas incompatibles surgidas dentro del barrido se registran y no abortan todo.

## C. Qué significa variar un factor

OFAT significa *One Factor At A Time*. Si se estudia T3, cambian sólo T3 y, en A/B, la variable de decisión rp. T1, p1, cp, gamma, eta_c, eta_t y delta se mantienen. En R permanece además rp. No se estudian interacciones entre dos entradas, ni incertidumbre estadística, ni un mapa bidimensional.

Los tres escenarios responden a preguntas diferentes:

| Escenario | Decisión sobre rp | Pregunta |
|---|---|---|
| R | Fija, introducida en formulario | ¿Qué cambia si no reajusto la compresión? |
| A | Recalculada para cada x | ¿Cuál es el mayor trabajo específico admisible ahora? |
| B | Recalculada para cada x | ¿Cuál es la mayor fracción del calor convertida en trabajo? |

Las ecuaciones siguen delegadas a `evaluar_punto`. Sólo se acepta un punto con compresión, expansión, Qin y W positivos por encima de sus tolerancias. El candidato matemático no basta. `calcular_dominios` proporciona los intervalos físicos actuales; no se conserva el óptimo de la muestra anterior ni se utiliza una ventana fija.

Con eficiencias unitarias y pérdida nula, el rendimiento crece hasta un **supremo no alcanzado**; B no existe como ciclo operativo. El informe ofrece el valor límite y su frontera excluida, pero sus curvas y coeficientes operativos quedan indisponibles. En dominio vacío A/B no intentan optimización. Un límite numérico conserva ese nombre: no demuestra ausencia física de motor.

### Tres intervalos diferentes

1. El rango de x, elegido por el usuario, define el eje horizontal y su malla.
2. Cada intervalo físico abierto de rp se calcula por muestra con Fase 1.
3. La búsqueda numérica de las muestras seleccionadas usa una ventana interior de ese dominio y refinamiento propio; queda registrada junto con su concordancia.

Las tablas conservan dominios ideal/no ideal completos; las gráficas de esta fase muestran resultados frente a x, no un nuevo barrido rp. No se rehace la viabilidad.

### Rangos y límites

Sugerencias educativas: T1 250–350 K, T3 800–2000 K, eta_c/eta_t 0.6–1, delta 0–0.2. El selector propone sus extremos; se pueden editar. Son sugerencias, no límites universales. La validación exige temperaturas positivas, eficiencias en (0,1], delta en [0,1), extremos finitos ordenados y 3–201 muestras enteras. El límite de 201 controla coste y tamaño de tablas; no fija una frontera física.

En el campo físico principal la pérdida se escribe en **%**. En el estudio `delta` se escribe en **fracción**: 0.05 significa 5 %. Mantener esta distinción evita barrer pérdidas cien veces mayores de lo previsto.

## D. Cómo se implementa: funciones y datos

Las entradas físicas son dict con nueve claves; temperaturas K, cp J/(kg·K), p1 kPa, otras adimensionales. Energías de salida kJ/kg; eta fracción. Los errores de entrada globales son ValueError; estructura/tipos de programación incorrectos propagan. No se capturan excepciones genéricas para convertirlas en resultados aparentemente válidos.

### Contratos del núcleo

| Firma completa | Argumentos → retorno; validaciones/errores | Llama / la llaman; ejemplo |
|---|---|---|
| `validar_configuracion(parametro, minimo, maximo, muestras)` | Nombre str, dos extremos reales, n int → dict con parámetro/extremos/n/unidad. Valida límites descritos; ValueError, excluido bool como n. Sin física. | No llama funciones propias; la usan estudio, malla e index. `validar_configuracion('T3',800,2000,41)` |
| `generar_malla(configuracion)` | Dict anterior → ndarray lineal float con extremos. Valida configuración y diferencias estrictamente positivas; ValueError por muestras indistinguibles. | Llama validación/NumPy; la usa el estudio. Con delta 0–0.2 y n=3 da `[0,.1,.2]`. |
| `construir_parametros(referencia, parametro, valor)` | Dict físico, nombre str, x real → copia con una clave distinta. No valida modelo; nombre desconocido KeyError. | Sin llamadas propias; estudio/callback. `construir_parametros(base,'delta',.1)` |
| `argumentos_fisicos(parametros)` | Dict físico → tupla de ocho entradas en orden de dominios/optimizadores, sin rp. KeyError si faltan claves. Apoyo sin ecuaciones. | Sin llamadas propias; estudio/evaluador. `calcular_dominios(*argumentos_fisicos(base))` |
| `registro_escenario(estado, motivos=(), rp=None, ciclo=None, metodo='no aplicable', supremo=None, verificacion=None)` | Estado/método str, motivos secuencia, rp escalar, ciclo/supremo/verificación dict o None → registro uniforme. Sólo disponible ofrece rp/W/eta/Qin; conserva ciclo diagnóstico si existe. Inconsistencias de contrato propagan. | Sin llamadas propias; evaluador. `registro_escenario('sin_dominio',('Dominio motor vacío.',))` |
| `evaluar_muestra(parametros, verificar=False)` | Nueve entradas y bool → dict con parámetros, dominios, motivo y R/A/B. T3<=T1 registrado, no excepción; ErrorNumerico capturado por escenario, bugs propagan. | Llama adaptador, registro, dominios/evaluador de Fase 1 y candidatos/coordinadores de Fases 2/3; estudio/callback la llaman. `evaluar_muestra(base,True)` |
| `calcular_sensibilidad_local(funcion, x, limites, escala=1.)` | Callback float→float/None, x real, extremos físicos representables, escala de Y → dict derivada, normalizada, método, paso, error estimado y motivo. Rechazos de fiabilidad registrados; errores del callback propagan. | Llama callback; estudio la llama. Con `lambda x:x*x`, x=2, límites (0,10), da 4 y 2. |
| `analizar_sensibilidad(referencia, parametro, minimo, maximo, muestras=41)` | Nueve entradas válidas y controles → dict completo del estudio, sin archivos. Valida referencia, rp>1 y configuración; ValueError global, errores por muestra explícitos. | Llama las funciones anteriores y validación física; API/tests/ejecutor la llaman. `analizar_sensibilidad(base,'T3',800,2000,41)` |

`registro_escenario` ofrece `estado`, `motivos`, `rp`, `ciclo`, `metodo`, `supremo`, `verificacion` y magnitudes. `verificacion` contiene ventanas de búsqueda/final y concordancia numérica cuando se hizo. `ciclo` conserva los valores con signo de R inviable: en HTML se identifican como diagnóstico, sin inventar rendimiento motor. Un `None` no significa cero.

El estudio agrupa `referencia`, `configuracion`, `valores`, `registros`, `curvas`, `sensibilidades`, `referencia_local`, `indices_verificacion`, `tendencias`, `segundos_calculo`. Así se puede probar el cálculo sin dibujar ni escribir archivos. Los arrays tienen igual longitud y cada índice conserva la correspondencia con la muestra original.

### Funciones de presentación y ejecución

| Firma completa | Entrada/salida, finalidad y errores | Relaciones y ejemplo |
|---|---|---|
| `crear_graficas_sensibilidad(estudio)` | Dict completo → dict de tres bytes PNG W/eta/rp. 1350×900; no calcula física. Errores inesperados de contrato/dibujo propagan; recursos se cierran en finally. | Usa Matplotlib/BytesIO, no otras funciones propias; ejecutor/tests la llaman. `imagenes=crear_graficas_sensibilidad(estudio)` |
| `crear_informe_sensibilidad_html(estudio, imagenes, fecha, version_git)` | Dict, tres PNG, datetime, Git dict → str HTML. ValueError si no hay exactamente esas claves o PNG inválido; sin cálculo físico. | reporting: llama tabla_html/imagen_html; ejecutor la llama. `crear_informe_sensibilidad_html(estudio,imagenes,datetime.now(),{'commit':None,'modificado':None})` |
| `ejecutar_sensibilidad(carpeta_salida, parametros, parametro, minimo, maximo, muestras=41)` | Ruta str/Path, nueve entradas y controles → Path publicado. Propaga fallos de cálculo, dibujo/publicación; sin nuevas ecuaciones. | Llama estudio, gráficos, consulta Git, nuevo presentador y guardado compartido; index/API/tests la llaman. `ejecutar_sensibilidad('pruebas',base,'T3',800,2000,41)` |

Dentro de `analizar_sensibilidad`, `evaluar_local(x)` es un cierre: recibe x y devuelve muestra desde caché local, llamando copia/evaluador sólo si falta. `magnitud(x)` consulta ese cierre para escenario s y magnitud k; devuelve float o None si no es operativo o Qin es demasiado pequeño. Lo llama inmediatamente el diferenciador dentro del bucle; no se guarda para ejecutarlo cuando s/k hayan cambiado. `evaluar_local` también obtiene `referencia_local`. Ejemplo interno para s=A,k=W,x=1600: 373.210827 kJ/kg. La caché pertenece a una sola ejecución, no contamina peticiones posteriores.

Las clases nuevas de pruebas tienen `setUp(self)` y `test_*(self)`, sin argumentos físicos ni retorno de cálculo; las invoca unittest. Usan las API anteriores para comprobar contratos, referencias, efectos de archivo y errores inyectados. No son funciones del modelo. El helper del test de gráficas intercepta `plot`/`savefig` para verificar NaN y límites; luego ejecuta las operaciones reales.

## E. Sensibilidades: matemáticas y significado

Para una magnitud Y:

```text
D = dY/dx
S = (x/Y) D
ΔY/Y ≈ S · Δx/x
```

D tiene unidades, por ejemplo kJ/(kg·K) si Y es W y x=T3. S es adimensional. La aproximación vale para perturbaciones pequeñas dentro del mismo régimen, no cambios grandes ni cruces de fronteras. Para A/B se recalcula rp al perturbar x: la derivada incluye ese reajuste óptimo.

Si eta_B=0.438931 y S_etaB,T3≈0.674343, un aumento pequeño del 1 % relativo en T3 aproxima un 0.674343 % **relativo** en eta_B: unos 0.2960 puntos porcentuales alrededor de esa condición. No significa +0.674343 pp ni una ley universal.

### Diferencias finitas implementadas

Con paso h:

```text
Central:       [Y(x+h) − Y(x−h)] / (2h)
Hacia delante: [−3Y(x) + 4Y(x+h) − Y(x+2h)] / (2h)
Hacia atrás:   [3Y(x) − 4Y(x−h) + Y(x−2h)] / (2h)
```

Las tres fórmulas son de orden 2 para funciones suaves. Se usa central si cabe en el intervalo físico; en eta=1 o delta=0 puede proceder unilateral. El paso inicial es `cbrt(eps)*max(abs(x),1)`: equilibra truncamiento O(h²) y redondeo O(eps/h), con escala mínima de una unidad. En T3=1600, el paso fino h/2≈0.00484436356 K. No es el paso de la malla OFAT.

Se calcula también con h/2, exigiendo diferencia ≤`1e-3*abs(D_fina)+1e-7*abs(escala)/max(abs(x),1)`. Es una comprobación heurística de estabilidad, no una garantía matemática para toda función ni incertidumbre experimental. No se anuncian sensibilidades cuando:

- La referencia no es un motor resoluble o no hay óptimo alcanzado.
- Una perturbación cambia a no disponibilidad o da límite numérico.
- La derivada no se estabiliza al reducir el paso.
- |Y|≤1e−9·escala o Qin<1e−7·cp·T3/1000 (condicionamiento pobre).
- No puede representarse una perturbación admisible.

Escalas: cp·T3/1000 para energías, 1 para eta y rp de referencia para rp. En x=0 sólo se ofrece derivada absoluta: un porcentaje de una entrada nula no es interpretable. Un régimen muy estrecho puede quedar sin coeficiente; es preferible informar el motivo que forzar una cifra.

La referencia local es la del formulario, aunque quede fuera del intervalo dibujado. Los límites para derivar son físicos: T1∈(0,T3), T3>T1, eficiencias∈(0,1], delta∈[0,1). `np.nextafter` representa el vecino interior de extremos estrictos. No se inventa una frontera cerrada válida.

## F. Python y NumPy: qué aprender

### Copiar antes de variar

Fragmento real:

```python
parametros = referencia.copy()
parametros[PARAMETROS_ESTUDIO[parametro]["clave"]] = float(valor)
```

Un diccionario asocia claves y valores. `.copy()` crea otro contenedor para que asignar T3 no cambie la referencia de la próxima muestra. Es copia superficial: aquí basta porque los valores son números inmutables; con listas internas haría falta revisar esa decisión. Debes poder comprobar que las otras ocho claves permanecen iguales.

### Arrays alineados y NaN

Fragmento real del estudio:

```python
curvas = {s: {k: np.array([r[s][k] if r[s][k] is not None else np.nan
                           for r in registros]) for k in MAGNITUDES} for s in "RAB"}
```

Es una comprensión anidada: un dict por escenario y otro por magnitud; dentro, una lista se transforma en array. La condición distingue None de cero. NaN significa ausencia gráfica y corta líneas de Matplotlib. Si filtraras todos los puntos inválidos antes de `plot`, podrías unir dos regiones separadas. Si pusieras cero, inventarías un resultado físico. `np.isfinite` identifica disponibilidad y `np.diff` comprueba monotonía de la malla; `np.r_` ayuda a contar comienzos de tramos.

### Callback, cierre y caché

Una función puede recibirse como argumento. El diferenciador llama a `funcion(x+h)` sin conocer si calcula W o rp. El cierre `magnitud` recuerda s/k y referencia de su función exterior; la caché local permite reutilizar cada perturbación entre 12 coeficientes. Ejemplo didáctico independiente: `lambda x:x*x` describe Y=x². Lo nuevo es desarrollar ese patrón para coeficientes; callbacks y caché ya aparecían en búsquedas anteriores.

### Un conjunto para evitar búsquedas duplicadas

Fragmento real:

```python
indices = {0, muestras // 2, muestras - 1, int(np.argmin(abs(valores - x0)))}
```

Las llaves crean un `set` de índices distintos. `//` es división entera; `argmin` devuelve la posición más próxima a x0. Si referencia y centro coinciden, no se duplica la búsqueda. Las búsquedas originales pueden costar cientos de evaluaciones: se reservan para hasta cuatro muestras, manteniendo fórmula, dominio y comprobación física en **todas**. El método figura en cada resultado: no se afirma contraste numérico donde no se hizo.

### Contratos con estados y excepciones

Los estados disponibles, inviables, sin dominio, supremo, límite numérico y parámetros incompatibles no son intercambiables. `except ErrorNumerico` captura una limitación esperada de representación; no captura un ValueError inesperado de programación. Las pruebas inyectan ambos para verificar esa distinción. Los `None` se presentan como raya o motivo, sin sustituirlos por cero.

### Tiempo, recursos e interfaz

`perf_counter()` mide tiempo transcurrido para comparar coste, no fecha de documentación. Fecha/Git se guardan aparte. `with BytesIO()` y `finally: plt.close(figura)` liberan memoria incluso si falla el informe. La publicación reutiliza un temporal exclusivo y sólo después elimina informes antiguos.

En Jinja `tojson` convierte el catálogo de opciones a JavaScript seguro; un manejador local de `change` rellena sugerencias al cambiar selector. Eso modifica campos, no calcula termodinámica. La autoridad de validación sigue en Python. Los dos botones envían valores diferentes de `accion`, permitiendo conservar un formulario único de nueve parámetros físicos.

## G. Recorrido de un ejemplo real

Referencia: T1=288.15 K, T3=1600 K, p1=100 kPa, rp=10, cp=1005 J/(kg·K), gamma=1.4, eta_c=0.85, eta_t=0.90 y delta=0.05. Estudio T3 entre 800 y 2000 K, 41 muestras.

```python
from main import PARAMETROS_PREDETERMINADOS
from sensibilidad import analizar_sensibilidad
estudio = analizar_sensibilidad(PARAMETROS_PREDETERMINADOS, "T3", 800, 2000, 41)
print(estudio["referencia_local"]["A"]["trabajo_neto"])
print(estudio["sensibilidades"]["A"]["rp"]["normalizada"])
```

El cálculo no publica un informe; el botón Flask usa después el ejecutor para dibujar y guardar. La malla tiene paso 30 K; 1600 no pertenece a esa malla, por lo que `referencia_local` se evalúa aparte. Los contrastes de la malla usan extremos, centro y vecino más próximo a 1600; el diferenciador usa sus propias perturbaciones analíticas físicamente verificadas.

| T3 [K] | Caso | rp | W [kJ/kg] | eta [%] | Qin [kJ/kg] |
|---|---|---|---|---|---|
| 800 | R | 10 | 26.196119 | 13.275608 | 197.325187 |
| 800 | A | 3.833722 | 63.962228 | 18.020683 | 354.937864 |
| 800 | B | 5.605096 | 58.065565 | 19.511149 | 297.601985 |
| 1600, referencia local | R | 10 | 369.476301 | 36.898732 | 1001.325187 |
| 1600, referencia local | A | 12.895052 | 373.210827 | 39.212614 | 951.762164 |
| 1600, referencia local | B | 35.452324 | 313.738915 | 43.893107 | 714.779462 |
| 2000 | R | 10 | 541.116392 | 38.559587 | 1403.325187 |
| 2000 | A | 19.055292 | 568.030012 | 44.717204 | 1270.271756 |
| 2000 | B | 64.269908 | 471.647796 | 50.078199 | 941.822604 |

A entrega mayor W; B mayor eta pero menor trabajo que A. B a 2000 K está fuera de rp=50: reutilizar intervalos antiguos habría ocultado la solución. La referencia reproduce exactamente Fase 3, sin cambiar el modelo.

Coeficientes locales T3=1600:

| Magnitud | R | A | B |
|---|---|---|---|
| dW/dT3 [kJ/(kg·K)] | 0.4291002274 | 0.4624111961 | 0.3754935380 |
| S_W,T3 | 1.8581986500 | 1.9824127792 | 1.9149350989 |
| S_eta,T3 | 0.2523267310 | 0.6645110967 | 0.6743426771 |
| S_rp,T3 | 0 | 1.7499999997 | 2.6732063889 |

La identidad rp_A∝T3^[gamma/(2(gamma−1))] da S_rpA=1.75, una comprobación independiente del diferenciador. Las energías incluyen cp/1000; sus unidades no son potencia. No deduzcas de esta tabla qué parámetro será siempre más importante.

## H. Gráficas, HTML y uso Flask

Las tres figuras independientes muestran W [kJ/kg], eta [%] y rp frente al parámetro con su unidad. R/A/B usan estilos/leyendas distintos. La figura de rp diferencia la consigna constante, gris y de trazo punto-raya, de R operativo, azul con círculos. La leyenda dice explícitamente que la consigna no indica viabilidad. R, A y B conservan sus NaN en las tres figuras; ninguna curva operativa se rellena con una constante para conectar muestras excluidas. Sólo la consigna describe la configuración incluso fuera del dominio motor. El rango x completo se fija expresamente; y se ajusta a datos. Si difieren por más de factor 100 se indica escala simétrica logarítmica, sin recortar las otras curvas.

El HTML incorpora tres PNG Base64 de 1350×900 y CSS propio: no depende de imágenes externas, JS remoto ni servidor una vez descargado. Contiene parámetros, rango/n, explicación de escenarios, resultados/motivos/diagnósticos firmados, dominios abiertos, ventanas/concordancias numéricas, tendencias, sensibilidades locales/motivos y Git con aviso de cambios. Los supremos muestran su límite sin una fila operativa B falsa. Las tendencias son recuentos y extremos de muestras, no garantías sobre todo el intervalo continuo.

Se reutilizan nombre y marcas de documento completo, permitiendo que la ruta anterior lo muestre o descargue. El título distingue sensibilidad de simulación normal. La retención conserva cuatro informes **entre ambos tipos**, sin otro cupo paralelo. Un fallo de publicación no elimina anteriores; archivos ajenos siguen intactos. No hay bloqueo multiproceso.

Uso: abre el lanzador existente o `python web_app.py`, conserva las nueve entradas, selecciona el parámetro y ajusta extremos/n en **Análisis de sensibilidad**. Pulsa **Ejecutar análisis de sensibilidad**. El otro botón conserva simulación normal y siete figuras. `main.py` directo tampoco ejecuta OFAT. Flask sigue en 127.0.0.1, debug/reloader/threading desactivados; sin cuentas, bases de datos ni despliegue público.

## I. Verificación realizada y resultados preservados

Primera suite de esta tarea: **107/107 OK en 93.103 s**. Son las 83 anteriores y 24 nuevas; no se elimina ninguna anterior. Verificación final tras fijar rango visual: 107/107 pruebas OK en 131.473 s, tras el ajuste visual. Comando:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Las pruebas incluyen validación, malla, ocho parámetros intactos, R/A/B frente a evaluaciones individuales, dominios dinámicos, óptimos fuera de antiguos rangos, motivos simultáneos, vacío sin búsqueda, reversibilidad/supremo sin punto, dominio estrecho, límite numérico, errores inesperados, derivadas analíticas/centrales/unilaterales/x=0/valores pequeños/discontinuidades, caché aislada, coste, NaN/ejes/PNG, Flask/descarga/retención mixta/fallo parcial. La simulación directa normal y sus siete figuras se verifican mediante pruebas previas conservadas y una generación adicional aislada.

Comprobaciones manuales reproducibles de 41 muestras:

| Estudio | Resultado observado | Tiempo total aproximado |
|---|---|---|
| T3 800–2000 K | R/A/B disponibles en 41 muestras | 1.88 s |
| eta_c 0.6–1 | R/A/B disponibles en 41 muestras | 1.92 s |
| delta 0–0.2 | R/A/B disponibles en 41 muestras | 1.85 s |
| T3 200–800 K | R: seis temperaturas incompatibles, 30 puntos inviables, cinco motores; A/B: seis incompatibles, 13 dominios vacíos, 22 disponibles | 2.14 s |
| Reversible, T3 800–2000 K | 41 supremos B, ningún punto operativo B ficticio | 1.81 s |
| T3 800–20000 K | Escala grande, curvas y rp fija visibles | 2.07 s |

Estos tiempos incluyen tres gráficas y publicación; cálculo puro estuvo entre ~0.045 y 0.10 s (mediciones de este equipo, con otras comprobaciones concurrentes). La prueba de coste ejecuta estudios de 201 muestras y comprueba un margen amplio de 15 s para evitar una regresión drástica, sin imponer un benchmark universal. Seleccionar hasta cuatro búsquedas permite escalar sin optimizar numéricamente cada punto.

Los informes/figuras de revisión están en una carpeta aislada fuera del repositorio y no consumen `outputs/`. Se inspeccionan visualmente trabajo frente a T3, rendimiento con muestras excluidas y rp a escalas grandes; se contrastan firmas PNG/Base64, ausencia de recursos externos y tamaños. Los PNG históricos permanecen intactos. Esto es **verificación** de código, ecuaciones y consistencia interna; no **validación** con un motor experimental.

## J. Cinco ejercicios con comprobaciones orientativas

1. **Copias OFAT.** Cambia delta a 0.1 con `construir_parametros`; compara las nueve claves con referencia. Sólo la pérdida debe cambiar. Explica por qué no usarías `parametros=referencia`.
2. **Derivada conocida.** Ejecuta `calcular_sensibilidad_local(lambda x:x*x,2.,(0.,10.))`. Espera D≈4, S≈2; repite con `lambda x:2+x*x` en x=0. La derivada unilateral es ~0 y S no se interpreta porcentualmente.
3. **R frente a reajuste.** Estudia T3 800–2000 con 21 y 41 muestras; compara referencia local. Debe permanecer igual porque la derivada no usa el paso de esa malla. Explica por qué A supera W_R y B supera eta_A cuando son operativos.
4. **Reversibilidad y NaN.** Usa eta_c=eta_t=1 y delta=0; estudia T3. Verifica que B tiene supremos pero no rp/ciclo operativo ni coeficientes. Explica por qué eliminar NaN o sustituirlos por cero engañaría al dibujar.
5. **Frontera y unidades.** Barre T3 200–800. Cuenta estados y reproduce la tabla de verificación; mira diagnósticos firmados de R inviable. Después estudia delta 0–0.2 y justifica la diferencia con escribir 20 en ese máximo. No confundas pérdida fraccionaria con el campo principal en %.

Son prácticas sobre las API implementadas, no nuevas funcionalidades añadidas automáticamente. Para publicar experimentos usa una carpeta alternativa, conservando el historial del usuario.

## K. Limitaciones y estado de Git

OFAT no detecta interacciones entre factores, ni incertidumbre estadística ni una importancia universal. Una malla finita puede omitir una isla estrecha entre muestras; el programa no la rellena por interpolación. Los coeficientes son locales, sus escalas/pasos son criterios numéricos explícitos y h/h2 no prueba suavidad global. Casos casi degenerados pueden resultar no disponibles por redondeo y tolerancias de las fases previas.

Se mantienen las hipótesis originales y la separación entre verificación y validación externa. No hay propiedades variables, combustible, caudal, potencia, empuje ni mapas. El historial no coordina varios procesos; Flask secuencial evita simultaneidad dentro de su proceso.

La implementación está registrada en `88c026395a9aba9cf72819305cfe2540f200e54a` — `Implement Brayton parametric sensitivity analysis with Flask integration`, desarrollada en `feature/fase-4-sensibilidad-parametrica` desde `899024c518348fa48944041059aa885cc127af7e`. El 21 de octubre de 2026, el usuario autorizó expresamente su cierre en Git. La verificación previa al commit de este cierre supera 108/108 pruebas en 80.205 s, distinta de las comprobaciones anteriores. El hash real se incorpora ahora mediante un commit exclusivamente documental adicional autorizado, sin modificar código ni resultados. La integración y los hashes de merge/publicación se consultan en el historial de Git; no se inventa el hash propio del commit documental. `zip.zip` permanece local y ajeno a los commits.
