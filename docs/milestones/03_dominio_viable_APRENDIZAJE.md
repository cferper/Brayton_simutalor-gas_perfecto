# Fase 1 — Aprendizaje del dominio físicamente viable del ciclo Brayton

**Fecha de documentación: 20 de octubre de 2026.** Reconstrucción a partir del código y las diferencias de Git frente a `3003bc8cd2d84547cc48e09f136f849d555599e2`. Esta fecha identifica la redacción de esta guía independiente, no una fecha de implementación inventada.

**Para qué estudiar este documento:** comprender las novedades de Fase 1, por qué se incorporaron y cómo programarlas. El [manual completo actual](../../CODE_WALKTHROUGH.md) explica todo el repositorio; el [milestone técnico](03_dominio_viable.md) resume esta etapa. Aquí sólo se desarrollan sus cambios frente al estado anterior. Las referencias §4/§14 de las fichas apuntan al manual completo como lectura adicional, no como requisito para seguir los ejemplos.

## A. Qué había antes y qué hemos conseguido

En el commit de partida ya había ciclos ideal y no ideal con eficiencias isentrópicas y pérdida de presión del combustor, estados y balances, diagramas ideales T-s/P-v y máximo de trabajo exclusivamente ideal. Se ejecutaba desde `python main.py` o desde Flask local con nueve parámetros. Cada ejecución publicaba un HTML autocontenido con seis imágenes Base64 y metadatos Git; terminal y web compartían un historial de cuatro informes y protegían archivos ajenos y PNG históricos.

La limitación estaba en los barridos: rendimiento ideal entre rp=2 y 30, comparación de 300 pares entre 2 y 30 y búsqueda ideal de 100001 puntos entre 1.01 y 50. Los ciclos estrictos rechazaban calor o trabajo no positivos. Por eso un punto no motor podía detener un barrido completo, incluso si el caso de referencia era viable. La comparación capturaba `ValueError` junto a errores aritméticos y los presentaba como rechazo del estudio; no devolvía una clasificación física consultable de cada punto.

La fase separa tres preguntas: **¿son válidos los parámetros?**, **¿describe el punto un motor?** y **¿se puede representar numéricamente el resultado?** Ahora puedes consultar un punto no motor sin interrumpir el barrido, identificar todas sus causas y distinguir las fronteras físicas del intervalo que se dibuja. No se sustituyó el modelo termodinámico por otro de mayor fidelidad: se analizan las consecuencias de sus mismas ecuaciones.

## B. Qué se ha añadido al código

### B.1. Archivos y alcance de la comparación

La tabla corresponde al núcleo de Fase 1 frente al commit base. «Nuevo» describe archivos presentes en el árbol de trabajo y todavía no incluidos en un commit propio.

| Archivo | Estado en Fase 1 | Cambio real | Por qué fue necesario |
|---|---|---|---|
| `viabilidad.py` | Nuevo | Estados y energías compartidos, clasificación, dominios, bisección y barridos | Consultar inviabilidad normal sin interrumpir el estudio ni duplicar ecuaciones |
| `main.py` | Modificado | Delega cálculos comunes, clasifica referencia/barrido, adapta búsqueda ideal y cuatro gráficas de rp | Coordinar resultados motores y distinguir sus fronteras de las ventanas numéricas |
| `reporting.py` | Modificado | `crear_informe_html` recibe barrido opcional y presenta límites, causas y mallas reales | Explicar el significado de las curvas sin perder compatibilidad, Git, Base64 o retención |
| `web_app.py` | Modificado | `index` captura también `ErrorNumerico` con mensaje diferenciado | No presentar una limitación de representación como conclusión termodinámica |
| `templates/index.html` | Modificado | Pie explicativo sobre dominio y puntos excluidos | Retirar la advertencia obsoleta de rechazo por cualquier punto del barrido fijo |
| `tests/test_viabilidad.py` | Nuevo | 18 pruebas de límites, clasificación, máscaras, bisección y regresión HTTP | Verificar las nuevas garantías y sus casos límite |
| `tests/test_web_app.py` | Modificado | T3=400/500 K en el caso de rechazo, conservando la prueba y el historial protegido | Mantener una expectativa física correcta tras aceptar T3=800 K |
| `README.md` | Modificado | Dominio, ejemplos de consulta, comportamiento, estructura y limitaciones | Permitir ejecutar y entender la nueva capacidad |
| `CODE_WALKTHROUGH.md` | Modificado | Arquitectura, funciones, física, programación, ejemplos y ejercicios de Fase 1 | Explicar el código de esa versión junto con sus cambios |
| `docs/milestones/03_dominio_viable.md` | Nuevo | Resumen académico de la etapa | Distinguir el avance mayor de los detalles del walkthrough |

`tests/test_reporting.py` no cambió y sus 11 pruebas se conservaron. No se modificaron dependencias, el CSS ni los PNG históricos. Después de la implementación física se añadió `Abrir_Brayton_Simulator.cmd` como acceso al formulario existente y se reorganizó la documentación; son intervenciones auxiliares de esta rama, no nuevas ecuaciones ni parte del algoritmo de dominio. Su contexto se distingue al final de esta guía.

### B.2. Las ocho funciones nuevas de viabilidad.py

Estos contratos permiten usar las novedades de forma independiente. Los valores predeterminados eta_c=eta_t=1 y delta=0 representan el límite reversible; el formulario normal utiliza los valores no ideales de F.

**Contrato común.** Los argumentos físicos son escalares reales (`int`, `float` o escalares NumPy); T1/T3 en K, cp en J/(kg·K), p1 en kPa. `gamma`, `rp`, `eta_c`, `eta_t`, `delta` y tolerancias relativas no tienen unidades. No se aceptan arrays como temperaturas de entrada de estas funciones escalares. Las tuplas de estados siempre siguen 1,2,3,4. Los errores de tipos o estructuras mal usados se propagan; la API no los oculta como inviabilidad física.

#### `validar_parametros(T1, T3, gamma, cp, p1, eta_c=1, eta_t=1, delta=0)`

- **Propósito físico:** comprobar la familia de modelos antes de analizar su dominio: finitud, T3>T1>0, gamma>1, cp/p1>0, eficiencias en (0,1] y pérdida en [0,1). La relación T3>T1 es una condición de entrada del estudio motor, no prueba suficiente de viabilidad.
- **Retorno:** `None`; `ValueError` si se incumple. No recibe rp ni decide sobre un punto del barrido.
- **Llama:** ninguna función propia. La llaman `calcular_estados`, `evaluar_punto`, `calcular_dominios` y `main`.
- **PYTHON:** argumentos por defecto, `all` sobre un generador y comparaciones encadenadas. No instala dependencias.
- **Ejemplo:** `validar_parametros(288.15,1600,1.4,1005,100,.85,.9,.05)` termina sin valor visible.

#### `calcular_estados(T1, T3, gamma, rp, p1, eta_c=1, eta_t=1, delta=0)`

- **Propósito físico:** evaluar exactamente las ecuaciones de temperaturas y presiones del apartado D, sin exigir qin o wn positivos. Centraliza la física ideal/no ideal: eficiencias unidad y delta cero recuperan el ideal.
- **Retorno:** diccionario `temperaturas` (tupla de cuatro K), `presiones` (cuatro kPa), `T2s`/`T4s` [K]. El ideal usa la expresión algebraicamente equivalente T3*(p1/p3)**a; puede diferir en el último bit de T3/rp**a.
- **Validación/errores:** llama a `validar_parametros` con cp auxiliar=1; exige rp positivo finito y estados positivos finitos. `ValueError` corresponde a entradas inválidas. Desbordamiento, división por subdesbordamiento o estados no representables generan `ErrorNumerico`, que hereda de `ArithmeticError`. Las ecuaciones de equipos se interpretan como compresor/turbina motores sólo tras clasificarlas.
- **Llama:** `validar_parametros`; la llaman `evaluar_punto` y `calcular_temperaturas`. No importa `main`, evitando dependencias circulares.
- **PYTHON:** potencias, tuplas, diccionario y captura limitada de `OverflowError`/`ZeroDivisionError` alrededor de las operaciones.
- **Ejemplo:** `calcular_estados(288.15,1600,1.4,10,100,.85,.9,.05)['presiones']` → `(100,1000,950,100)`.

#### `calcular_energias(temperaturas, cp)`

- **Propósito físico:** balance cp·ΔT con signo; un trabajo negativo es un resultado matemático interpretable, no una excepción de Python. Comparte las cuatro ecuaciones de energía con la API estricta antigua.
- **Entradas:** secuencia de cuatro temperaturas positivas finitas [K] y cp positivo finito [J/(kg·K)].
- **Retorno:** diccionario `trabajo_compresor`, `trabajo_turbina`, `trabajo_neto`, `calor_aportado`, todos [kJ/kg]. No divide entre qin ni calcula rendimiento.
- **Llama:** ninguna propia; la llaman `evaluar_punto` y `calcular_balance_energetico`.
- **Errores:** `ValueError` para cp/temperaturas inválidos o longitud incorrecta; `ErrorNumerico` para energías no finitas; errores de tipo se propagan.
- **PYTHON:** desempaquetado de cuatro elementos, resta y `.values()` para comprobar resultados.
- **Ejemplo:** `calcular_energias((300,500,450,350),1000)` devuelve wc=200, wt=100, wn=−100, qin=−50 kJ/kg; no es un ciclo motor.

#### `evaluar_punto(T1, T3, gamma, cp, rp, p1, eta_c=1, eta_t=1, delta=0, tolerancia=TOL_REL)`

- **Propósito físico:** consultar un punto sin lanzar excepciones por inviabilidad esperada. Exige márgenes positivos para compresión, expansión, calor y trabajo, con las tolerancias del apartado D.
- **Retorno:** estados y energías anteriores más `viable` booleano, `motivos` y `fronteras` como tuplas de códigos, diccionarios `margenes`/`tolerancias` con unidades de cada condición, `rendimiento=wn/qin` y `back_work_ratio=wc/wt` sólo si es viable; fuera del motor ambos cocientes son `None`.
- **Motivos:** `compresion`, `expansion`, `calor_aportado`, `trabajo_neto`; se conservan TODOS. `fronteras` identifica condiciones dentro de la banda de cero, aunque otra condición falle lejos de cero.
- **Llama:** `validar_parametros`, `calcular_estados`, `calcular_energias`. La llaman `construir_barrido`, `calcular_ciclo_noideal`, `main` (referencia y tabla ideal) y pruebas.
- **Errores:** parámetros inválidos o tolerancia fuera de [0,1) → `ValueError`; estados, energía o escala numéricamente no representables → `ErrorNumerico`. Una lista de motivos no vacía es una devolución normal.
- **PYTHON:** `tuple(c for ... if ...)` filtra códigos; `not motivos` es `True` para tupla vacía; `**estados` y `**energias` reúnen diccionarios. La expresión condicional evalúa el cociente sólo en la rama viable, evitando divisiones engañosas.
- **Ejemplo:** `evaluar_punto(288.15,1600,1.4,1005,200,100,.85,.9,.05)` da calor positivo y trabajo negativo: `motivos=('trabajo_neto',)` y `rendimiento=None`.

#### `bisectar_raiz(funcion, inferior, superior, tolerancia=1e-12, iteraciones=100)`

- **Propósito:** resolver una raíz, no optimizar trabajo. `funcion` es un objeto invocable de un escalar a otro; los extremos, la raíz x y Q no tienen unidades en este uso. El número máximo de iteraciones es un entero positivo.
- **Retorno:** escalar con raíz aproximada. Acepta una raíz exacta en los extremos; si no, exige signos opuestos. Repite el punto medio y conserva la mitad con cambio de signo hasta ancho <= tolerancia*max(abs(medio),1), o residuo exactamente cero.
- **Llama:** el callback recibido; la llama `calcular_dominios` dos veces cuando hay dos raíces distintas. Usar una función como argumento es pasar una operación sin ejecutarla todavía.
- **Errores:** `ValueError` para controles/intervalo inválidos o ausencia de cambio de signo; `ErrorNumerico` para función no finita o agotamiento de iteraciones. Ninguno se silencia en el barrido.
- **PYTHON:** `for _ in range(iteraciones)` repite un número acotado de veces; `_` indica que el índice no se usa. `(fm>0)==(fi>0)` compara signos sin multiplicar números que podrían desbordarse.
- **Ejemplo:** `bisectar_raiz(lambda x: x*x-2,1,2)` → aproximadamente `1.41421356237`. `lambda` crea una función corta; no es una ecuación adicional del simulador.

#### `calcular_dominios(T1, T3, gamma, cp, p1, eta_c=1, eta_t=1, delta=0)`

- **Propósito físico:** obtener fronteras independientemente del intervalo representado. La demostración del apartado D prueba un dominio abierto, único o vacío para ESTE modelo. cp y p1 no alteran sus límites, aunque se validan y sí cambian energías/presiones dimensionales.
- **Retorno:** diccionario con `ideal` y `noideal`; cada uno contiene `intervalo=(inferior,superior)` o `()`, `expansion` (cota inferior), `calor` (cota superior) y `trabajo` (raíces ordenadas o `()`). Todos son rp adimensionales. El no ideal añade `discriminante`; el contenedor añade `tolerancia_puntos=1e-10` y `tolerancia_biseccion=1e-12`.
- **Método:** cotas de expansión/calor analíticas; discriminante y convexidad establecen dónde puede haber Q<0; bisección en [0,centro] y [centro,1+h] localiza sus dos ceros. Se convierten x a rp y se intersecta con rp>1, expansión y calor. Si h<=1, no hay motor para x>=k>=1, evitando intervalos ficticios por redondeo de la raíz x=1.
- **Función local `Q(x)`:** cierre dentro de `calcular_dominios` que recibe x adimensional, devuelve `(x−1)*(x−h)+h*(k−1)` y utiliza h/k del ámbito exterior. No llama a funciones propias; la llama `bisectar_raiz`. No es una nueva API pública. Ejemplo conceptual con h=4 y k=1: Q(2)=−2. Un resultado no finito lo rechaza la bisección.
- **Llama:** `validar_parametros`, `bisectar_raiz`. La llaman `construir_barrido`, `calcular_ciclo_noideal` en rechazos, `buscar_optimo_numerico`, `main` y pruebas.
- **Errores:** entradas inválidas → `ValueError`; fronteras/cuadrática no representables o dominio ideal indistinguible de rp=1 → `ErrorNumerico`. Dominio no ideal vacío → resultado normal `intervalo=()`, no excepción.
- **PYTHON:** función anidada, tupla vacía y `max`/`min` para intersecar intervalos; `**` es potencia al convertir x a rp.
- **Ejemplo:** `calcular_dominios(288.15,1600,1.4,1005,100,.85,.9,.05)['noideal']['intervalo']` → aproximadamente `(1.0696541023,155.4543260392)`.

#### `describir_inviabilidad(punto, dominio)`

- **Propósito:** explicación de todas las condiciones fallidas y de los límites físicos; no recalcula ecuaciones. `punto` procede de `evaluar_punto`; `dominio` es el subdiccionario ideal/noideal de `calcular_dominios`.
- **Retorno:** `str` con motivos traducidos mediante `MOTIVOS`, intervalo abierto o aviso de dominio vacío, y exclusión de fronteras/banda numérica. rp no tiene unidad; los estados conservan las suyas.
- **Llama:** ninguna propia; la llaman `main`, `calcular_ciclo_noideal` y pruebas.
- **PYTHON:** `'; '.join(...)` une todos los motivos; `or` permite texto de punto viable con tupla vacía.
- **Errores:** un diccionario mal formado puede producir `KeyError`/`TypeError`, que se propagan; no captura fallos de programación.
- **Ejemplo:** `describir_inviabilidad(punto, dominios['noideal'])`, tras las llamadas anteriores, incluye `1.069654102 < rp < 155.454326`.

#### `construir_barrido(T1, T3, gamma, cp, p1, eta_c=1, eta_t=1, delta=0, relaciones=None, dominios=None)`

- **Propósito físico:** separar el estudio numérico del dibujo, mantener puntos inviables con motivos y ofrecer curvas exclusivamente motoras.
- **Entradas:** ocho escalares del contrato común; `relaciones` opcional, secuencia 1D finita, positiva, estrictamente creciente con al menos dos puntos; `dominios` opcional, resultado coherente de `calcular_dominios` para esos mismos parámetros. Si se aportan dominios, el llamador debe garantizar su coherencia.
- **Retorno:** diccionario `relaciones` (array rp), `dominios`, `ideal` y `noideal`. Cada modelo contiene lista `puntos` con todos los estados/energías y clasificación, máscara booleana `viable`, lista `motivos`, arrays `rendimiento` [fracción] y `trabajo_neto` [kJ/kg] que valen `np.nan` fuera del motor. El trabajo firmado original permanece en `puntos`.
- **Muestreo:** 500 puntos geométricos + 500 lineales entre 1 y `min(1.05*limite_ideal,10000)`, más fronteras visibles y sus vecinos relativos ±1e−6; hasta 101 puntos por intervalo motor para resolver dominios estrechos. `np.unique` ordena y elimina repetidos. Son menos de 1300 puntos: coste acotado. El ejemplo tiene 1212. El límite 10000 es de visualización, no físico; los límites reales se conservan en tablas y mensajes aunque queden fuera de la figura.
- **Llama:** `calcular_dominios` si no se recibe y `evaluar_punto` para cada modelo y rp. La llaman `main`, las dos funciones gráficas que admiten barrido opcional y pruebas. `main` verifica comparaciones sólo donde ambos modelos son motores.
- **Errores:** malla inválida → `ValueError`; problemas numéricos → `ErrorNumerico`; errores inesperados se propagan. No captura `ValueError` para saltar puntos. Inviabilidad → máscara falsa y motivos.
- **PYTHON:** `np.asarray(...,dtype=float)` normaliza el contenedor; `.ndim`/`np.diff` revisan forma/orden; `np.geomspace` multiplica por un factor constante; `.extend` incorpora muestras; `np.unique` ordena y deduplica. `mascara` es array de booleanos y `~mascara` lo invierte elemento a elemento. NaN es un valor flotante especial que interrumpe un trazo de Matplotlib; no equivale a trabajo cero.
- **Ejemplo:** `b=construir_barrido(288.15,1600,1.4,1005,100,.85,.9,.05,relaciones=[1,2,10,200,500])`; `b['noideal']['motivos'][3]` indica sólo trabajo no positivo.

### B.3. Funciones modificadas y dibujo del dominio

Las siguientes funciones ya existían, salvo `marcar_dominio`. Se adaptaron donde hacía falta reutilizar los cálculos o presentar la clasificación, sin refactorizar los diagramas ideales ni la publicación.

| Función y archivo | Antes → después; motivo | Funciones propias que utiliza ahora |
|---|---|---|
| `calcular_temperaturas` — `main.py` | Ecuaciones ideales locales → estados comunes con eficiencias unidad; conserva el rechazo estricto de calentamiento no positivo | `calcular_rendimiento`, `calcular_estados` |
| `calcular_balance_energetico` — `main.py` | Cuatro energías calculadas localmente → balance compartido; conserva validaciones motoras y rendimiento | `calcular_energias` |
| `calcular_ciclo_noideal` — `main.py` | Estados/balance estrictos en la propia función → evaluación clasificada y rechazo con todos los motivos y límites | `evaluar_punto`; si es inviable, `calcular_dominios` y `describir_inviabilidad` |
| `marcar_dominio` — `main.py` | No existía → añade escala logarítmica, bandas y fronteras; reutiliza el mismo criterio gráfico | Ninguna; usa métodos de Matplotlib |
| `guardar_comparaciones_ciclos` — `main.py` | Barrido fijo estricto y captura genérica → consume barrido clasificado, curvas con NaN y límites | `construir_barrido` si no se recibe; `marcar_dominio` |
| `buscar_optimo_numerico` — `main.py` | Malla siempre [1.01,50] → 100001 puntos interiores adaptados; evita fallos por evaluar fuera del motor ideal | `calcular_dominios`, `calcular_relacion_optima`, `calcular_trabajo_neto` |
| `guardar_grafica_trabajo_neto` — `main.py` | Dibujo del trabajo suministrado → admite dominio opcional y datos con cortes; señala el máximo fuera de vista sin ampliar la ventana | `marcar_dominio` si se recibe dominio |
| `guardar_grafica_rendimiento` — `main.py` | Fórmula ideal en 100 puntos fijos → rendimiento ideal clasificado en la malla adaptada; no prolonga eficiencias como motor fuera del dominio | `construir_barrido` si falta; `marcar_dominio` |
| `main` — `main.py` | Captura amplia de rechazos numéricos → valida entradas explícitamente, clasifica antes de publicar y verifica comparaciones sólo donde ambos ciclos son motores | Nuevas: `validar_parametros`, `calcular_dominios`, `evaluar_punto`, `describir_inviabilidad`, `construir_barrido`; conserva cálculo/óptimo ideal, comparación reversible, gráficos y generación/guardado del informe (§4.19) |
| `crear_informe_html` — `reporting.py` | Presentaba resultados y rangos fijos → añade dominio y rangos reales con un argumento final opcional; mantiene llamadas anteriores | `tabla_html`, `imagen_html` |
| `index` — `web_app.py` | Capturaba `ErrorModelo` → distingue también `ErrorNumerico`; conserva el formulario y la redirección tras éxito | `valores_formulario`, `leer_parametros`, `main` |

También se añadió la clase de excepción `ErrorNumerico(ArithmeticError)` y se actualizó la descripción de `ErrorModelo(ValueError)`: no son funciones físicas. En pruebas se creó `ViabilidadTests` con `setUp`, el helper `punto` y 18 métodos de prueba; el helper local `capturar` inspecciona líneas de Matplotlib. Se modificó el método `WebTests.test_casos_no_admisibles_conservan_datos_e_historial`. Su inventario completo se conserva en el manual actual, §4.34 y §4. No cambiaron las ecuaciones de `calcular_relacion_optima`, los diagramas T-s/P-v ni la lógica de publicación/retención.

La función nueva de dibujo tiene la firma `marcar_dominio(ejes, dominio, etiqueta, color)`. Recibe un objeto `Axes`, el subdiccionario de límites de un modelo (rp adimensional) y dos cadenas; devuelve `None` y modifica escala/leyenda/bandas de ese eje. La llaman las tres funciones de dibujo de rp de la tabla. No llama a funciones físicas: utiliza `set_xscale`, `axvline`, `axvspan` y los límites de Matplotlib. Un uso es `marcar_dominio(ejes, dominios['ideal'], 'ideal', 'tab:blue')` tras dibujar datos ya clasificados. Un eje o diccionario incorrecto provoca errores de estructura/biblioteca, no inviabilidad termodinámica.

## C. Cómo lo hemos implementado

### 1. Calcular estados antes de exigir un ciclo motor

**INGENIERÍA:** las ecuaciones de compresor, pérdida de presión y turbina son las que ya existían; ahora se evalúan antes de imponer calor/trabajo positivos. Las ecuaciones y unidades se desarrollan en D.

**PYTHON:** `calcular_estados` valida las entradas, calcula cuatro temperaturas/presiones y devuelve un diccionario. `calcular_energias` aplica cp·ΔT sin rechazar un trabajo neto negativo. Así las funciones estrictas y la clasificación utilizan una sola implementación de las fórmulas.

### 2. Evaluar los márgenes del punto

**INGENIERÍA:** se comprueban compresión, expansión, aporte de calor y trabajo neto. Que los estados sean positivos no basta.

**PYTHON:** `evaluar_punto` crea los márgenes `rp-1`, `p3-p1`, `calor_aportado` y `trabajo_neto`. Cada margen se compara en su propia unidad con su tolerancia. Sólo devuelve `viable=True` si todos superan la banda de cero. Si el punto no es motor, rendimiento y BWR son `None`; no se divide por qin para publicar un cociente engañoso.

### 3. Conservar todas las condiciones que fallan

Fragmento real de `evaluar_punto`:

```python
motivos = tuple(c for c in margenes if margenes[c] <= tolerancias[c])
fronteras = tuple(c for c in margenes if abs(margenes[c]) <= tolerancias[c])
viable = not motivos
```

**PYTHON:** no hay una cadena de `if/elif` que se detenga tras el primer motivo. La comprensión recorre todas las claves. La segunda tupla distingue proximidad a una frontera de estar claramente fuera. No hay un `except ValueError` genérico para silenciar fallos de programación al recorrer la malla.

### 4. Calcular límites independientes de la malla

**INGENIERÍA:** el ideal tiene frontera analítica; expansión/calor no ideales también. El signo del trabajo se transforma en una desigualdad cuadrática cuya convexidad demuestra intervalo abierto o vacío.

**PYTHON:** `calcular_dominios` calcula las cotas y usa `max` para intersecar cotas inferiores y `min` para superiores. Una tupla vacía `()` significa dominio vacío. No se infiere un límite físico del último punto que salió viable en un array.

### 5. Localizar raíces mediante bisección acotada

**INGENIERÍA:** las raíces son fronteras wn=0; no se maximiza el trabajo no ideal.

**PYTHON:** se pasa la función local `Q` a `bisectar_raiz`, sin ejecutarla al pasarla. Con signos opuestos en los extremos se calcula el medio, se evalúa su signo y se conserva la mitad que sigue conteniendo el cero. Se limita a 100 pasos y una tolerancia de ancho relativa en x de 1e−12. Un intervalo mal acotado o una operación no finita sigue siendo un error explícito.

### 6. Construir una malla con coste acotado

**INGENIERÍA:** interesa observar el entorno de rp=1 y fronteras lejanas sin confundir la ventana de dibujo con el dominio completo.

**PYTHON:** `construir_barrido` combina `np.geomspace` y `np.linspace`, añade fronteras visibles y vecinos relativos 1±1e−6, y hasta 101 muestras por intervalo motor. `np.unique` ordena y elimina duplicados. El extremo es `min(1.05*limite_ideal,10000)`. Se evalúa cada rp para el ideal y el no ideal por separado. La malla automática tiene menos de 1300 puntos; una malla aportada por el usuario debe ser unidimensional, finita, positiva y estrictamente creciente.

### 7. Entregar a las gráficas máscaras y NaN

**INGENIERÍA:** cada curva sólo representa su interior motor; un tramo excluido no es un resultado nulo.

**PYTHON:** el barrido conserva listas de puntos completos y motivos, una máscara booleana y arrays para dibujo con `np.nan` fuera del motor. Matplotlib corta el trazo en esos valores. El trabajo firmado permanece en `puntos`; no se destruye al preparar la gráfica. El sombreado y las verticales añaden límites ya calculados, no nuevos cálculos físicos. T-s y P-v siguen siendo del caso ideal de referencia; se conservan exactamente seis imágenes.

### 8. Llevar el estudio al HTML

**PYTHON:** `main` pasa el barrido como último argumento de `crear_informe_html`, manteniendo compatibles los diez argumentos anteriores. El generador presenta condiciones, límites, viabilidad de referencia y recuentos de causas; no recalcula estados. Esos recuentos pueden solaparse. Las seis figuras se generan en `BytesIO` y se incorporan como Base64.

**INGENIERÍA:** el informe distingue cotas físicas, ventana gráfica y malla de comprobación del óptimo IDEAL. Identifica unidades y tolerancias sin presentarlas como incertidumbre experimental.

### 9. Integrar los rechazos con Flask

**PYTHON:** `index` llama al mismo `main` que el terminal y captura `ErrorModelo` o `ErrorNumerico` con mensajes distintos, conservando el texto introducido. Si la referencia no es motor en ambos modelos, se rechaza antes de crear/publicar el informe; no se limpia el historial. Los errores inesperados se registran como HTTP 500, no como motivos físicos. Un POST correcto termina en redirección 303 al informe; el recorrido concreto está en F.

## D. Nuevos conceptos de ingeniería

### D.1. Ecuaciones existentes que ahora se comparten

El modelo sigue siendo gas ideal con cp/gamma constantes y equipos adiabáticos en régimen estacionario; se desprecian cambios de energía cinética y potencial. Estados 1/2: entrada/salida de compresor; 3/4: entrada/salida de turbina. Define delta como fracción de pérdida, no porcentaje escrito en el formulario.

$$
a=\frac{\gamma-1}{\gamma},\quad
p_2=p_1r_p,\quad p_3=p_2(1-\delta),\quad p_4=p_1,
$$
$$
T_{2s}=T_1r_p^a,\quad
T_2=T_1+\frac{T_{2s}-T_1}{\eta_c},\quad
T_{4s}=T_3(p_4/p_3)^a,\quad
T_4=T_3-\eta_t(T_3-T_{4s}).
$$

T2s y T4s son referencias isentrópicas entre las presiones correspondientes. Bajar eta_c aumenta T2 y el consumo; bajar eta_t reduce la caída de temperatura y el trabajo de turbina. Perder presión en el combustor reduce la expansión disponible incluso antes de aplicar eta_t. No se multiplica simplemente el trabajo ideal por una eficiencia global.

### D.2. Condiciones, fronteras y demostración del dominio

Un **dominio viable** es el conjunto de relaciones de presión que permite funcionar como motor con las temperaturas, eficiencias y pérdida fijadas. No significa que todas esas condiciones sean realizables por una máquina real: sólo que cumplen las restricciones del modelo educativo.

Con $a=(\gamma-1)/\gamma>0$, $r_p=p_2/p_1$, compresor de consumo positivo y cp en J/(kg·K):

$$
w_c=\frac{c_p(T_2-T_1)}{1000},\quad
w_t=\frac{c_p(T_3-T_4)}{1000},\quad
w_n=w_t-w_c,\quad q_{in}=\frac{c_p(T_3-T_2)}{1000}.
$$

Las cuatro energías están en **kJ/kg**, no kW. Las temperaturas son K, las presiones kPa y las relaciones/eficiencias adimensionales. Se exige (r_p>1), (p_3>p_4), (q_{in}>0) y (w_n>0). Tener calor positivo no garantiza que la turbina cubra el consumo del compresor.

**Ideal.** Con $x=r_p^a$, se cumple $T_2=T_1x$, $T_4=T_3/x$ y:

$$
w_n=\frac{c_p}{1000}(1-1/x)(T_3-T_1x).
$$

Para T3>T1 y rp>1, calor/trabajo son positivos si $x<T_3/T_1$. Así:

$$1<r_p<(T_3/T_1)^{\gamma/(\gamma-1)}.$$

Los extremos no pertenecen al dominio: en rp=1 no hay compresión ni trabajo; en la cota superior desaparecen calor y trabajo. El máximo de trabajo IDEAL está dentro, en $r_{p,opt}=(T_3/T_1)^{\gamma/[2(\gamma-1)]}$, y no es una frontera de funcionamiento.

**No ideal.** La pérdida relativa delta reduce p3 a $p_1r_p(1-\delta)$. Las cotas analíticas son:

$$
r_p>\frac{1}{1-\delta}\quad\text{(expansión)},\qquad
r_p<[1+\eta_c(T_3/T_1-1)]^{1/a}\quad\text{(calor)}.
$$

Para estudiar el trabajo, define $\theta=T_3/T_1$, $h=\theta\eta_c\eta_t$, $k=(1-\delta)^{-a}$ y $x=r_p^a$. Multiplicar wn por un factor positivo permite comprobar su signo mediante:

$$w_n>0\iff Q(x)=x^2-(1+h)x+hk=(x-1)(x-h)+h(k-1)<0.$$

Q es convexa. Si su discriminante $D=(h-1)^2-4h(k-1)$ es positivo, sólo es negativa entre dos raíces distintas; si D<=0, no tiene interior negativo. Si h<=1 tampoco hay motor para x>=k>=1. Intersectar esa región con las restricciones de compresión, expansión y calor da un intervalo abierto o vacío. Como x aumenta con rp, la conversión a rp no lo rompe en tramos desconectados. Esta demostración depende del modelo actual, no de una propiedad universal de todos los motores.

La bisección localiza las raíces de Q a ambos lados de su vértice: Q(0)=Q(1+h)=hk>0 y Q en el vértice es negativa cuando D>0. El vértice sirve para acotar **raíces**; no se ha implementado el óptimo no ideal. Con eficiencias unidad y delta=0, Q=(x−1)(x−theta) y se recupera el dominio ideal. La derivación completa y las tolerancias están en [§14](../../CODE_WALKTHROUGH.md#14-relación-entre-código-y-ecuaciones).

### D.3. Tolerancias e interpretación de la referencia

La clasificación usa `TOL_REL=1e-10`. La escala energética es `max(abs(wc),abs(wt),(cp/1000)*max(T1,T3))`, en kJ/kg. En la referencia equivale a una banda energética aproximada de 1.608e−7 kJ/kg. Para compresión se escala con max(rp,1) y para expansión con max(p3,p1). Los extremos matemáticos son abiertos; además se excluye esa pequeña banda de redondeo al declarar un punto motor. No representa incertidumbre experimental.

| Límite calculado con los valores predeterminados | rp adimensional |
|---|---:|
| Dominio ideal | 1 < rp < 403.4175203200 |
| Expansión no ideal | rp > 1.0526315789 |
| Aporte de calor no ideal | rp < 254.8459320044 |
| Raíces de trabajo no ideal | 1.0696541023 y 155.4543260392 |
| Intersección motora no ideal | 1.0696541023 < rp < 155.4543260392 |
| Máximo de trabajo IDEAL, no frontera de viabilidad | rp ≈ 20.0852562921 |

En este ejemplo el trabajo impone restricciones más fuertes que expansión/calor por separado. En rp=200 hay calor positivo pero wn<0. En rp=1 pueden fallar simultáneamente compresión, expansión y trabajo. Una combinación con dominio vacío no equivale a un fallo del programa: devuelve `intervalo=()` y puntos no motores. Una frontera no representable numéricamente, en cambio, requiere informar `ErrorNumerico`.

## E. Nuevos conceptos de Python y programación

Algunos recursos, como diccionarios y tuplas, ya existían antes; la fase los aplica a resultados y clasificación más ricos. No todo lo explicado aquí se introdujo por primera vez en el repositorio.

**Módulos y clasificación.** Un módulo es un archivo importable que agrupa una responsabilidad. `viabilidad.py` no importa `main`; así el coordinador puede importar sus cálculos sin formar un ciclo de imports. Calcular un punto y decidir cómo mostrarlo son tareas distintas. Por ejemplo, esta llamada real no genera archivos ni figuras:

```python
from viabilidad import evaluar_punto
punto = evaluar_punto(288.15, 1600, 1.4, 1005, 200, 100, .85, .9, .05)
print(punto['viable'])       # False
print(punto['motivos'])      # ('trabajo_neto',)
print(punto['rendimiento'])  # None
```

`punto` es un diccionario: se buscan valores mediante claves entre corchetes. `motivos` es una **tupla de códigos** dentro del diccionario, no una cadena que imponga un único fallo. Una tupla vacía `()` significa que no se ha excluido ninguna condición. `None` declara que no se ofrece un rendimiento motor; no significa rendimiento cero. `fronteras`, `margenes` y `tolerancias` permiten distinguir la cercanía numérica a un límite de un fallo claro.

**Máscaras booleanas y NaN.** Una máscara contiene un `True`/`False` por muestra, en el mismo orden que el array de resultados. Fragmentos reales de `construir_barrido`:

```python
mascara = np.array([p['viable'] for p in puntos], dtype=bool)
np.array([p['rendimiento'] if p['viable'] else np.nan for p in puntos])
```

La comprensión recorre los diccionarios y extrae un dato de cada uno. La expresión `valor if condicion else alternativa` elige qué guardar. Ejemplo pequeño de la misma sintaxis de selección:

```python
import numpy as np
mascara = np.array([True, False, True])
valores = np.array([10.0, np.nan, 20.0])
print(valores[mascara])   # [10. 20.]
print(valores[~mascara])  # [nan]
```

`~mascara` invierte cada booleano. NaN es un valor flotante especial que ocupa la posición excluida: Matplotlib interrumpe el trazo allí. Borrar esa posición y unir los puntos restantes podría ocultar una zona excluida; sustituirla por cero inventaría un resultado. El ejemplo ilustra el mecanismo; para estas ecuaciones, la prueba algebraica establece un único intervalo motor o vacío. El trabajo firmado original sigue accesible en `barrido[modelo]['puntos']`.

**Bisección.** Se recibe una función como argumento, no sólo números. `bisectar_raiz` evalúa el punto medio y conserva la mitad del intervalo que cambia de signo. Cada paso reduce el ancho aproximadamente a la mitad. Ejemplo numérico independiente, sin introducir nuevas ecuaciones del motor:

```python
from viabilidad import bisectar_raiz
raiz = bisectar_raiz(lambda x: x*x - 2, 1, 2)
# Aproximadamente 1.41421356237
```

`lambda x: ...` crea una función corta; la bisección la llama después con distintos valores. Dentro de `calcular_dominios`, `Q(x)` es una función local que recuerda h y k de la llamada exterior: un **cierre**. Se detiene con una raíz exacta o ancho <= 1e−12*max(abs(x),1), hasta 100 iteraciones.

**Tolerancias y errores.** Los flotantes pueden dejar un residuo diminuto donde la ecuación exacta vale cero. `evaluar_punto` exige margen mayor que una banda relativa de 1e−10: usa max(rp,1) para compresión, max(p3,p1) para presión y una escala energética en kJ/kg para calor/trabajo. La banda no cambia la ecuación ni mide incertidumbre experimental; excluye puntos demasiado próximos a cero para declararlos interiores motores.

- `evaluar_punto` devuelve `viable=False` ante inviabilidad esperada; los barridos continúan clasificados.
- Entradas inválidas generan `ValueError`. En `main`, su captura se limita a la validación explícita; las API estrictas pueden rechazar un caso no motor mediante `ErrorModelo`.
- Estados/fronteras no representables o una bisección que agota iteraciones generan `ErrorNumerico`. Una dificultad numérica no demuestra que el dominio físico esté vacío.
- Un fallo inesperado de código, dibujo o disco se propaga. Flask registra el detalle y presenta HTTP 500 genérico; no lo convierte silenciosamente en un punto inviable. Los rechazos esperados conservan valores e historial y usan HTTP 400.

### E.1. Qué aprender de cada recurso

Esta tabla completa los ejemplos anteriores. Su columna «ejemplo» es una expresión breve para practicar, no una ampliación del código.

| Concepto: qué es | Por qué se usa / dónde aparece | Ejemplo pequeño | Qué aprender para dominarlo |
|---|---|---|---|
| Módulo: archivo importable con una responsabilidad | `viabilidad.py` comparte física; `main.py` coordina; `reporting.py` presenta; `web_app.py` recibe HTTP | `from viabilidad import evaluar_punto` | Imports, nombres, evitar dependencias circulares y efectos al importar |
| Diccionario: resultados accesibles por claves | `evaluar_punto` reúne propiedades, energías y clasificación | `punto['temperaturas'][1]` selecciona T2 [K] | Claves frente a índices; tipos y unidades de cada valor; diccionarios anidados |
| Retorno compuesto: un solo objeto agrupa varios resultados | `calcular_estados` devuelve diccionario; `leer_parametros` ya devolvía una pareja | `parametros, errores = leer_parametros(datos)` | Tupla frente a diccionario; orden y desempaquetado; distinguir número de objetos devueltos y datos contenidos |
| Función como argumento: operación invocable | `calcular_dominios` entrega Q a `bisectar_raiz` | `bisectar_raiz(lambda x: x*x-2,1,2)` | Diferenciar pasar `Q` de ejecutar `Q(x)`; parámetros y cierres |
| Bisección: reducir un intervalo con cambio de signo | `bisectar_raiz` localiza fronteras con límite de iteraciones | Medio de [1,2] = 1.5; x²−2 es positivo allí, se conserva [1,1.5] | Invariantes de un bucle, continuidad, parada y error de aproximación |
| Máscara booleana: una condición por muestra | `construir_barrido` separa los interiores de cada modelo | `np.array([3,4])[np.array([True,False])]` da [3] | Longitudes alineadas, indexación booleana y `~` elemento a elemento |
| NaN: valor flotante especial para muestra excluida | Arrays de gráficas, no el trabajo firmado de `puntos` | `np.isnan(np.nan)` da True | Detectar NaN con `np.isnan`; no comprobarlo con igualdad ni reemplazarlo por cero |
| Tolerancia: margen numérico con escala y unidades | `evaluar_punto` y `bisectar_raiz` usan criterios diferentes | Un wn=1e−9 kJ/kg no supera la banda de referencia ≈1.608e−7 | Relativo/absoluto, unidades, redondeo y diferencia entre precisión numérica e incertidumbre física |
| Excepción propia: tipo específico para un fallo | `ErrorNumerico(ArithmeticError)` es nuevo; `ErrorModelo` ya existía | `raise ErrorNumerico('No converge')` ilustra la sintaxis | Herencia básica, `raise`, `except` específico y propagación de errores inesperados |
| Prueba automática: aserciones repetibles sobre un comportamiento | `ViabilidadTests(unittest.TestCase)` añade 18 métodos | `self.assertFalse(punto['viable'])` | `self`, preparación con `setUp`, aserciones, `subTest`, fallos esperados y límites de la evidencia |

### E.2. Organización y alcance de las pruebas

- `tests/test_viabilidad.py`: 18 pruebas nuevas de fronteras/vecinos, dominio vacío, invariancia con cp/p1, reversibilidad, motivos simultáneos, arrays y NaN en las líneas realmente dibujadas, bisección, errores numéricos y regresión Flask.
- `tests/test_web_app.py`: conserva 11 métodos, adaptando la expectativa de rechazo a T3=400/500 K; T3=800 K se cubre como éxito nuevo. También comprueba formulario, cambios de datos, descarga, retención compartida, errores y ejecución directa.
- `tests/test_reporting.py`: sus 11 métodos no cambian; verifican referencia, seis PNG de la ejecución, dimensiones, metadatos Git, publicación, colisiones, retención y archivos ajenos.

En la implementación de esta fase registrada en la conversación se ejecutó `python -B -m unittest discover -s tests -v` con resultado final de **40 pruebas superadas**. Ese resultado pertenece a la verificación de implementación anterior; no se presenta como una nueva ejecución en esta tarea exclusivamente documental. El recuento actual se ha contrastado leyendo el AST de los archivos de prueba.

No se añade una prueba que replique cada línea: se comprueban propiedades con significado. Las tolerancias de comparación están en el código; por ejemplo las raíces deben dejar un residuo wn dentro de 1e−7 kJ/kg y los puntos vecinos se separan por un factor relativo 1e−6. Verificar estas propiedades no valida un motor frente a datos externos.

## F. Recorrido completo de un ejemplo

Usa el formulario local ya existente, desde `python web_app.py` o el acceso por doble clic. No se ha añadido una web pública ni un formulario nuevo durante la Fase 1.

| Campo del formulario | Valor |
|---|---:|
| T1 [K] | 288.15 |
| T3 [K] | 1600 |
| p1 [kPa] | 100 |
| Relación de presiones | 10 |
| cp [J/(kg·K)] | 1005 |
| gamma | 1.4 |
| eta_c | 0.85 |
| eta_t | 0.90 |
| Pérdida de presión [%] | 5 |

1. **GET del formulario.** Flask llama a `index`; `valores_formulario` entrega una copia de valores predeterminados con pérdida en %. Jinja muestra nueve campos. Visitar esta página no ejecuta `main`.
2. **POST de datos.** Al pulsar «Ejecutar simulación», `index` conserva `request.form.to_dict()` y llama a `leer_parametros(request.form)`. Recibe dos diccionarios, parámetros y errores. El 5 del formulario se divide una sola vez entre 100: delta=0.05. No hay error de campo.
3. **Entrada al coordinador.** `index` llama a `main(app.config['OUTPUTS_DIR'], parametros=parametros)`. Main captura fecha/metadatos mediante `obtener_version_git`, copia la configuración y aplica los valores recibidos.
4. **Familia y referencia.** `validar_parametros` y la revisión de rp comprueban entradas. `calcular_dominios` obtiene los límites de D. `evaluar_punto` se llama para el ideal con pérdidas por defecto 1,1,0 y para el no ideal con .85,.9,.05. Cada llamada usa `calcular_estados` y `calcular_energias`.
5. **Decisión física.** Ambas referencias dan `viable=True`. La tupla de motivos está vacía. No se lanza `ErrorModelo`; con otro caso inviable, `describir_inviabilidad` explicaría las causas antes de guardar nada.
6. **Familia de ciclos.** `construir_barrido` recibe los dominios ya calculados y produce 1212 relaciones con resultados/máscaras separados. `main` recorre los pares y llama a `comprobar_comparacion_ciclos` únicamente donde ambos son motores.
7. **Comprobaciones ideales conservadas.** Se calculan `calcular_rendimiento`, `calcular_temperaturas`, `calcular_balance_energetico`, `calcular_entropias` y `calcular_estados_pv`. Se contrastan balance, entropía y gas ideal. En la referencia ideal wn≈505.619018 kJ/kg.
8. **Máximo sólo ideal.** `calcular_relacion_optima` y `buscar_optimo_numerico` contrastan rp≈20.085256 con 100001 puntos; `calcular_trabajo_neto` comprueba wn≈532.802230 kJ/kg en ese máximo. El paso de la malla predeterminada es 0.0004899.
9. **Ciclos y límite reversible.** `calcular_ciclo_ideal` y `calcular_ciclo_noideal` agrupan las referencias; `comprobar_comparacion_ciclos` contrasta tendencias y el caso no ideal 1,1,0. En el no ideal configurado T2≈603.656530 K, T4≈916.855359 K y wn≈369.476301 kJ/kg.
10. **Seis figuras en memoria.** `guardar_grafica_rendimiento`, `guardar_diagrama_ts`, `guardar_diagrama_pv` y `guardar_grafica_trabajo_neto` generan cuatro buffers. `guardar_comparaciones_ciclos` añade dos; las curvas de rp reutilizan el barrido y `marcar_dominio`. No se leen los PNG históricos.
11. **Documento.** `main` reúne `detalles_ideal`, `optimo`, tabla de cinco rendimientos clasificados, `comprobaciones` y bytes de `imagenes`; llama a `crear_informe_html(..., fecha, version, barrido)`. `tabla_html` escapa texto y `imagen_html` incorpora PNG Base64. Los recuentos de motivos son de la malla, no probabilidades físicas.
12. **Publicación y navegación.** Tras cerrar buffers/figuras con `finally`, `guardar_informe_html` publica un documento completo y conserva los cuatro propios más recientes. Devuelve su `Path` a `main` y luego a `index`; la respuesta es una redirección 303. El GET posterior llama a `ver_informe`, que sirve la copia con navegación. La descarga conserva el HTML autocontenido original.

Así los datos pasan de cadenas HTTP a diccionario numérico, después a diccionarios de estados y arrays clasificados, bytes PNG, texto HTML y finalmente una ruta de archivo. Las unidades no están incorporadas al tipo `float`: las conserva el contrato de cada función.

## G. Qué puedo probar por mi cuenta

Los siguientes experimentos son propuestas de estudio. No se han ejecutado simulaciones HTML ni generado gráficos al redactar esta guía. Las ejecuciones desde Flask sí publican informes y aplican la retención habitual de cuatro; las consultas Python siguientes no guardan archivos.

### 1. Flask: referencia original y límites nuevos

Introduce exactamente la tabla de F y ejecuta. Espera ambos modelos motores, números de H conservados y la nueva sección de dominio. Distingue el máximo ideal rp≈20.085256 de las fronteras ideales/no ideales de D. Demuestra la separación entre resultados ya existentes y nuevas salidas de análisis.

### 2. Flask: calor positivo no garantiza trabajo positivo

Restablece los valores y cambia sólo rp a **200**. Espera rechazo por trabajo no ideal no positivo, límites disponibles y datos conservados, sin informe nuevo ni limpieza del historial. Puedes consultar ese mismo punto en Python con el ejemplo de E: qin≈110.990380 kJ/kg, wn≈−83.407517 kJ/kg y `rendimiento=None`. Demuestra que el fallo físico no es un error de sintaxis ni falta de calor.

### 3. Flask: barrido mixto que antes abortaba

Restablece y cambia sólo **T3 a 800 K**, manteniendo rp=10. Espera éxito de referencia y un informe con zonas excluidas del barrido. Los intervalos se estrechan y la gráfica no prolonga rendimientos como motores en todos los puntos. Este comportamiento tiene la prueba `test_flask_acepta_caso_motor_con_antiguo_barrido_inviable`.

### 4. Python: ambos lados de una frontera

```python
from viabilidad import calcular_dominios, evaluar_punto
d = calcular_dominios(288.15, 1600, 1.4, 1005, 100, .85, .9, .05)
r = d['noideal']['trabajo'][1]
for factor in (1 - 1e-6, 1, 1 + 1e-6):
    p = evaluar_punto(288.15, 1600, 1.4, 1005, r * factor, 100, .85, .9, .05)
    print(factor, p['viable'], p['motivos'], p['fronteras'])
```

Espera motor por debajo; en la raíz se identifica la frontera de trabajo y no el interior; por encima wn<0. Demuestra la diferencia entre límite calculado, banda de cero y punto viable.

### 5. Python: recuperación reversible y máscaras

```python
import numpy as np
from viabilidad import construir_barrido
b = construir_barrido(288.15, 1600, 1.4, 1005, 100,
                      relaciones=[1, 2, 10, 200, 500])
print(b['ideal']['viable'])
print(np.allclose(b['ideal']['rendimiento'], b['noideal']['rendimiento'],
                  equal_nan=True))
print(np.isnan(b['ideal']['rendimiento'][~b['ideal']['viable']]))
```

Los argumentos por defecto corresponden a eficiencias unidad y delta cero. Espera máscara `[False, True, True, True, False]`, comparación verdadera y todas las muestras excluidas con NaN. `equal_nan=True` sirve aquí para comprobar que ambos arrays excluyen las mismas posiciones; NaN normalmente no es igual a sí mismo. No optimiza el no ideal.

### 6. Python: dominio vacío con entradas válidas

```python
from viabilidad import calcular_dominios, evaluar_punto
d = calcular_dominios(288.15, 300, 1.4, 1005, 100, .5, .5, 0)
p = evaluar_punto(288.15, 300, 1.4, 1005, 1.02, 100, .5, .5, 0)
print(d['noideal']['intervalo'])
print(p['motivos'], p['rendimiento'])
```

Espera `()` para el dominio no ideal y rendimiento `None`. En rp=1.02 el calor aún es positivo, pero el trabajo falla. T3>T1 y las eficiencias son válidas; sencillamente no hay un interior motor no ideal para esa familia. Aquí h<=1 permite entender el resultado sin confundirlo con desbordamiento ni con una excepción de programación.

## H. Qué permanece igual y qué está pendiente

### H.1. Resultados y funciones conservados

Se mantienen gas ideal de propiedades constantes, balances y unidades, nueve parámetros, ejecución directa y servidor local, seis imágenes Base64 de 1350 × 900, metadatos Git, descarga y retención segura de cuatro informes. Los diagramas T-s/P-v y la fórmula del óptimo ideal no se convierten en modelos no ideales nuevos.

| Magnitud de referencia en rp=10 | Ideal | No ideal |
|---|---:|---:|
| Trabajo del compresor [kJ/kg] | 269.521453 | 317.084063 |
| Trabajo de turbina [kJ/kg] | 775.140472 | 686.560364 |
| Trabajo neto [kJ/kg] | 505.619018 | 369.476301 |
| Calor aportado [kJ/kg] | 1048.887797 | 1001.325187 |
| Rendimiento [%] | 48.205253 | 36.898732 |

Cambian la clasificación y la representación fuera del motor, no estos resultados interiores. El óptimo ideal conserva rp analítica≈20.0852562921, numérica≈20.0852363 y wn≈532.802230 kJ/kg en el máximo analítico. La malla de dibujo predeterminada [1,423.5883963360], la frontera ideal≈403.4175203200 y la búsqueda ideal [1.01,50] cumplen funciones diferentes.

### H.2. Limitaciones pendientes

El modelo conserva gas ideal, cp/gamma constantes, flujo estacionario, equipos adiabáticos y pérdida relativa fija. No incluye química, propiedades variables, masa de combustible, caudal, potencia, empuje ni mapas de componentes. Los diagramas y la optimización siguen siendo ideales; la optimización no ideal corresponde a la Fase 2 y no se implementó aquí.

La vista de rp tiene coste y ventana acotados; no ver una frontera lejana en el gráfico no elimina su valor calculado en las tablas. La clasificación excluye una pequeña banda numérica y puede no resolver interiores extremadamente estrechos. El informe exige referencia motora en ambos modelos; las funciones de consulta permiten estudiar dominios vacíos por separado. La retención continúa sin bloqueo multiproceso. Ninguna de estas verificaciones sustituye contrastar el modelo con datos físicos externos.

### H.3. Evidencia y comprobación de esta guía

Los resultados de la suite de implementación (40 pruebas) se describen en E.2 como evidencia anterior. En la tarea documental de creación de esta guía se revisaron código, diferencias de Git, contratos y pruebas; se comprueban enlaces, sintaxis de fragmentos y ejemplos numéricos sin gráficos, y se contrastan hashes para asegurar que sólo cambia documentación. Esa reorganización no modificó ni reejecutó la suite completa; la nueva ejecución de cierre se registra al final de esta guía. No se generan informes ni se altera el historial de resultados.

## I. Relación con Git

- **Base verificada:** `3003bc8cd2d84547cc48e09f136f849d555599e2`, mensaje `Add HTML reports and local Flask interface with educational documentation`.
- **Rama de desarrollo:** `feature/fase-1-dominio-viable`. Al inicio de la revisión de cierre, su HEAD y `main` apuntaban a la misma base; la implementación y los complementos locales estaban sin commit.
- **Commit de cierre:** esta guía se incluye con la implementación y su milestone en el commit con mensaje `Implement Brayton feasible operating domain with tests and learning guide`. El hash de esa revisión se consulta en Git; no puede escribirse dentro del contenido de su propio commit. La base identifica el estado anterior, no el resultado de Fase 1.
- **Comparación realizada:** diferencias de archivos seguidos respecto a esa base más inspección de archivos nuevos sin seguimiento; contraste de funciones mediante AST y lectura del cambio de la prueba HTTP. Un simple `git diff` no muestra el contenido de archivos nuevos sin seguimiento.
- **Fecha:** 20 de octubre de 2026, fecha de documentación. Los registros previos de la conversación y del historial que se sustituye se distinguían como documentación del 19 de octubre; no se reconstruyen otras fases ni se afirma una fecha histórica de implementación a partir del timestamp de un archivo.
- **Informe técnico conservado:** [03_dominio_viable.md](03_dominio_viable.md), sin borrar ni renombrar los milestones anteriores.
- La reorganización que creó esta guía fue exclusivamente documental y no realizó operaciones de publicación. El cierre Git/GitHub posterior fue autorizado expresamente por el usuario; se distingue a continuación.

## Seguimiento de iteraciones dentro de esta fase

Estas notas breves reúnen el contexto de las intervenciones de la rama sin mantener un historial acumulativo dentro del manual global.

### Implementación del dominio — reconstrucción documental

La implementación principal y sus correcciones se estudian en A–I; se contrastan contra la base Git y la verificación anterior de 40 pruebas. La primera explicación por iteraciones había sido documentada el 19 de octubre de 2026 como reconstrucción, no como registro contemporáneo de todos los pasos de programación. Este documento independiente se redacta el 20 de octubre sin inventar más hitos temporales.

### Complementos locales posteriores al núcleo físico

Los registros documentales del 19 de octubre describían una política de historial global y el acceso `Abrir_Brayton_Simulator.cmd`. Este último facilita arrancar/reutilizar Flask y abrir el formulario; no cambia funciones físicas ni el algoritmo de dominio. Su uso vigente sigue explicado en el manual y README. Las pruebas de arranque que constan en la conversación no sustituyen las termodinámicas.

### 20 de octubre de 2026 — Aprendizaje independiente por fases

Se crea esta guía, se sustituye la política de `AGENTS.md` y se retira del walkthrough el historial acumulativo, manteniendo su manual del estado actual y su resumen de grandes hitos. README enlaza las distintas lecturas. Esta reorganización no modifica código, pruebas, interfaces ni los milestones técnicos. Las siguientes iteraciones de esta fase actualizarán este mismo archivo; una fase nueva tendrá otro `NN_nombre_fase_APRENDIZAJE.md`.

### 20 de octubre de 2026 — Verificación y cierre de Fase 1

El usuario autoriza guardar y publicar la fase, incorporarla mediante merge explícito a la rama principal real y preparar una rama independiente para Fase 2 sin implementar sus funciones. Se verifica que la base y el reflog corresponden al commit indicado y que los 13 archivos pendientes son los cambios conocidos de la fase y sus complementos documentales/de acceso local.

Antes del commit se ejecuta de nuevo la suite completa con el entorno virtual: **40 pruebas superadas** (11 de informes, 11 de Flask y 18 de viabilidad). La suite incluye ejecución directa de main, referencia Flask, seis PNG Base64 y retención segura. Los seis PNG históricos coinciden byte a byte con la base y los resultados de prueba se escriben en carpetas temporales, sin consumir el historial del usuario.

Se actualizan únicamente notas de verificación y relación con Git en el manual y documentos de fase; no cambian funciones, ecuaciones, dependencias ni pruebas. Conceptos de programación/herramientas: un commit guarda una instantánea local; push publica commits; un merge explícito conserva dos padres y hace visible la incorporación de la fase. Una rama nueva nombra un punto de partida, sin necesitar un commit vacío.

La documentación se prepara junto con el commit de cierre; la publicación y la incorporación sólo se deben declarar completadas cuando Git las confirme. El informe final de la tarea proporcionará los hashes reales del commit de fase, merge y base de la nueva rama. No se inventan identificadores futuros ni se presenta esta comprobación como validación experimental.
