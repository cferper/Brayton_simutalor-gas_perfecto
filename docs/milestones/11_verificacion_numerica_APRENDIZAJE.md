# Nuevo Plan de Mejoras — Fase 1: verificación numérica

Documento educativo iniciado el **22 de octubre de 2026**, con la iteración de diagnóstico del **23/10/2026** en §12. No debe confundirse esta **nueva Fase 1 de verificación numérica y comparación de modelos** con la **antigua Fase 1 de dominio físicamente viable** ([milestone 03](03_dominio_viable.md)). Las afirmaciones de las iteraciones anteriores conservan su contexto histórico; §12 distingue la nueva funcionalidad y las comprobaciones de esta tarea.

**Base histórica de la fase:** `27d4519094d5eb74f5009a1889a1e74dc8dddb94` (rama `main` al iniciar la Tarea 1.1). Las cinco tareas se publicaron en `mejoras/verificacion-numerica`: 1.1 en `275e7558b7d05322054f89ecd672ed5563c59469`, 1.2 en `143d10fd25ebd23ddb897722b7843bddabfd16a5`, 1.3 en `8ecbc1bf75e7e68fc3377cbf97017f8480d32553`, 1.4 en `c3b4bfea12cf6faa1dc90c8f8fb16fb9e8fe7131` y **1.5 en `57da73db01882ab32bd5d92d14bdbe739c272b79`**. La **Etapa 6 de cierre**, que documenta la ejecución completa, se prepara sobre ese último commit y sigue **pendiente de revisión y publicación**.

## 1. Estado anterior y propósito

Antes de la tarea, el simulador calculaba ciclos ideales y no ideales, clasificaba el dominio motor, buscaba óptimos analíticos y numéricos, estudiaba sensibilidad, mapas y segunda ley. Ya existían pruebas de referencias físicas, límite reversible, fronteras, relación óptima, búsqueda numérica independiente del candidato analítico e integración. No se han duplicado esas verificaciones de forma aislada.

Faltaba contrastar **sistemáticamente varios puntos motores ideales** con expresiones escritas directamente en el propio test y medir los residuos de conservación. El objetivo es detectar errores de implementación en estados, unidades, signos, energía y rendimiento **antes** de añadir modelos más complejos. Se añade únicamente `tests/test_verificacion_analitica.py` y se actualiza el manual; las funciones de producción, constantes, optimizadores, HTML, Flask y dependencias **no cambian**.

## 2. Interpretación física y referencias independientes de implementación

Hipótesis: gas ideal con `cp` y `gamma` constantes; compresión y expansión isentrópicas, calentamiento y enfriamiento isóbaros; ciclo motor abierto en relación de presiones (`rp>1` y aporte/trabajo positivos). `T1` y `T3` son temperaturas absolutas en K; `cp` se recibe en J/(kg·K), `rp` y `gamma` son adimensionales.

Las referencias se construyen **sin llamar a `calcular_estados`, `calcular_temperaturas` ni `calcular_ciclo_ideal`** para obtener los valores esperados:

```python
a = (gamma - 1) / gamma
T2_ref = T1 * rp**a
T4_ref = T3 / rp**a
wc_ref = cp * (T2_ref - T1) / 1000
wt_ref = cp * (T3 - T4_ref) / 1000
qin_ref = cp * (T3 - T2_ref) / 1000
qout_ref = cp * (T4_ref - T1) / 1000
```

**INGENIERÍA.** `wc` representa consumo positivo de compresor; `wt`, trabajo positivo de turbina; `qin`, calor aportado, y `qout`, calor rechazado positivo. Dividir por 1000 convierte J/kg a **kJ/kg**. El código devuelve `wc`, `wt`, `wneto` y `qin`, pero **no** devuelve `qout`: en las pruebas se obtiene a partir de las temperaturas.

Se comprueban las identidades de primera ley:

\[
w_{neto}=w_t-w_c=q_{in}-q_{out},\qquad
R_E=w_{neto}-(q_{in}-q_{out})\quad [\mathrm{kJ/kg}].
\]

La comparación de estados y energías con ecuaciones escritas en el test es una referencia **separada del código de producción**, aunque algebraicamente usa el **mismo modelo físico**. Las igualdades de trabajo y primera ley, incluido `R_E`, son **controles internos de consistencia**; no constituyen dos experimentos independientes ni prueban que el modelo describa un motor real.

El rendimiento ideal se contrasta como fórmula analítica y como cociente, siempre en **puntos motores** previamente clasificados por `evaluar_punto`:

\[
\eta_{ideal}=1-r_p^{-a}=\frac{w_{neto}}{q_{in}},\qquad q_{in}>0.
\]

Las fronteras con aporte nulo y los puntos no motores quedan deliberadamente fuera de esta tarea; no se divide entre cero ni se inventa un rendimiento motor.

En el **máximo de trabajo específico** para `T1`, `T3` constantes se cumple:

\[
r_{p,*}=\left(\frac{T_3}{T_1}\right)^{1/(2a)},
\qquad T_{2,*}=T_{4,*}=\sqrt{T_1T_3}.
\]

El test comprueba ambas temperaturas en la solución analítica y también en los estados que devuelve una llamada **directa** a `buscar_maximo_numerico`. Este buscador explora un dominio interior y refina mediante sección áurea, sin consultar el candidato analítico para localizar el máximo. La igualdad de temperaturas es una propiedad adicional, distinta de volver a comprobar solamente `rp_*`.

## 3. PYTHON — cómo están organizadas las pruebas

La clase `VerificacionAnaliticaIdealTests(unittest.TestCase)` reúne cuatro métodos. Cada uno recibe sólo `self`, no devuelve resultados físicos (retorno implícito `None`) y `unittest` lo invoca automáticamente. Las cinco tuplas de `CASOS` contienen `(nombre, T1, T3, gamma, cp, rp, p1)` con unidades del apartado anterior y `p1` en kPa. Todos son moderados, representables y motores. El último método utiliza sólo los tres primeros para las búsquedas.

| Firma del método | Qué comprueba | Funciones existentes llamadas |
|---|---|---|
| `test_estados_con_referencias_isentropicas(self)` | T1–T4, T2s y T4s [K] contra potencias isentrópicas directas | `main.calcular_ciclo_ideal` |
| `test_balances_con_referencias_y_residuo(self)` | Cuatro energías [kJ/kg], `wn=wt-wc`, `wn=qin-qout`, residuo y comparación con calor de referencia | `main.calcular_ciclo_ideal` |
| `test_rendimiento_analitico_frente_a_balance_motor(self)` | Viabilidad, `qin>0`, rendimiento [fracción] como fórmula y cociente | `evaluar_punto`, `main.calcular_rendimiento` |
| `test_temperaturas_coinciden_en_maximo_ideal_analitico_y_numerico(self)` | T2=T4=raíz geométrica [K] en candidato y búsqueda numérica motor interior | `main.calcular_relacion_optima`, `main.calcular_temperaturas`, `calcular_dominios`, `buscar_maximo_numerico` |

**Errores y validación.** Los cinco casos se seleccionan en el dominio admisible; por ello las funciones no deberían lanzar `ValueError` o `ErrorNumerico` en su uso normal. Un resultado que supere una tolerancia produce una aserción fallida (`AssertionError`) con nombre de caso, magnitud, error y tolerancia. Otras excepciones de producción se propagan para que `unittest` las muestre como errores, no como resultados físicos.

### ¿Qué aporta `unittest.subTest()`?

```python
for nombre, T1, T3, gamma, cp, rp, p1 in self.CASOS:
    with self.subTest(caso=nombre):
        # Calcular referencia y resultado; comprobar tolerancias.
        ...
```

**PYTHON.** `for` desempaqueta cada tupla, y `with` abre un contexto que identifica el caso. Si falla una aserción, el informe señala, por ejemplo, `caso='gamma_133'`, y se siguen examinando los demás casos. No se crean cinco métodos distintos ni se cambia el modelo por usar `subTest`. La salida de `unittest` cuenta **cuatro métodos**, con **18 casos parametrizados** (5+5+5+3), no 18 métodos independientes.

## 4. Errores y tolerancias

- **Error absoluto:** `abs(calculado-referencia)`, con la unidad de la magnitud (K, kJ/kg o fracción).
- **Error relativo:** `error_absoluto/abs(referencia)`, adimensional y sólo definido para referencia distinta de cero. El test de energías lo calcula para diagnosticar fallos, pero no guarda un máximo relativo agregado.
- **Residuo de identidad física:** cuánto se aparta de cero una igualdad como `wn-(qin-qout)`. Se expresa en **kJ/kg** y se compara con la escala energética del caso, no con una tolerancia térmica.

Se exige:

\[
|x-x_{ref}|\leq \varepsilon_{abs}+\varepsilon_{rel}|x_{ref}|.
\]

| Magnitud | Tolerancia absoluta | Relativa |
|---|---:|---:|
| Temperatura | `1e-9 K` | `2e-12` |
| Energía / residuo | `1e-10 kJ/kg` | `2e-12` |
| Rendimiento | `2e-13` (fracción) | `2e-12` |

Para residuos, la parte relativa multiplica `max(abs(wc),abs(wt),abs(wn),abs(qin),abs(qout))` del caso. Son tolerancias para redondeos en doble precisión y magnitudes moderadas; **no representan errores de medición** ni tolerancias universales para fronteras o extremos.

En el máximo numérico, si `epsilon_rp=resolucion_rp/rp`, la sensibilidad local ideal es aproximadamente `|dT|/T≈a*|drp|/rp`. La comparación usa un margen en K proporcional a `a*sqrt(T1*T3)*epsilon_rp`, más la tolerancia térmica anterior, con factor conservador para comparar simultáneamente T2, T4 y su diferencia. La `resolucion_rp` del buscador es una **escala conservadora informada, no una cota formal demostrada**.

## 5. Comprobaciones realmente ejecutadas

Ejecutadas el **22 de octubre de 2026** en una copia local del commit base, con dependencias del proyecto instaladas **fuera del repositorio**:

```bash
PYTHONPATH=/tmp/brayton_task_1_1_pkgs MPLCONFIGDIR=/tmp/mpl_brayton_task_1_1 python -B -m unittest discover -s tests -p 'test_verificacion_analitica.py' -v
```

**Resultado:** cuatro métodos nuevos correctos, cero fallos, cero errores (`Ran 4 tests ... OK`). Cuatro métodos anteriores directamente relacionados también pasaron por separado:

- `OptimizacionTests.test_limite_reversible_recupera_optimo_ideal`
- `OptimizacionTests.test_busqueda_numerica_no_utiliza_candidato_analitico`
- `ViabilidadTests.test_limites_ideales_y_optimo_distintos`
- `InformesTests.test_referencia_fisica`

El total focalizado es **8 métodos superados**, sin ejecutar de nuevo la suite completa. El último cierre integral histórico anotado en §4.44 del manual fue **178/178** (anterior a las seis pruebas de guías contextuales y a esta tarea); no debe atribuirse a esta ejecución.

Con cinco casos motores, máximos errores absolutos observados en un cálculo adicional:

| Comprobación | Máximo observado |
|---|---:|
| Temperaturas contra referencia | `1.1368683772161603e-13 K` |
| Energías contra referencia | `1.1368683772161603e-13 kJ/kg` |
| Rendimiento contra fórmula | `1.1102230246251565e-16` |
| Residuo de primera ley | `1.1368683772161603e-13 kJ/kg` |

**No se registró un máximo agregado de errores relativos**; no se atribuye uno al experimento.

Caso base (`T1=288.15 K`, `T3=1600 K`, `gamma=1.4`, `cp=1005 J/(kg·K)`, `rp=10`): `T2≈556.330550578 K`, `T4≈828.715948677 K`, `wn≈505.619018249 kJ/kg`, `eta≈0.482052532`. En su óptimo **numérico**: `rp≈20.085256021667`, `sqrt(T1*T3)≈678.999263623 K` y `|T2−T4|≈5.22445e-6 K`. La diferencia térmica del óptimo es mayor que el redondeo de un cálculo directo, como corresponde a la resolución de la búsqueda.

## 6. Limitaciones, próximos pasos y trazabilidad

1. Se han contrastado cinco casos interiores moderados, no todos los valores admisibles. No se han estudiado condicionamiento, límites de representación, puntos degenerados ni fronteras abiertas.
2. En esta **Tarea 1.1** aún no se había comparado ningún algoritmo con SciPy; esa comparación se añadió posteriormente en la Tarea 1.3 (§8). Los estudios de mallas y convergencia estaban pendientes entonces y se abordan en la Tarea 1.4 (§9).
3. No hay datos experimentales ni comparación con una correlación de un motor real: esto es **verificación de software** y de consistencia bajo el modelo de gas ideal con propiedades constantes, **no validación física**.
4. No se modifica `qout` como salida pública ni se añaden funciones de producción para los tests.
5. Esta tarea no crea un milestone **técnico de cierre** de la Fase 1 completa. El documento se ampliará en futuras tareas de esta fase, sin presentar como realizados sus resultados pendientes.

**Archivos de la Tarea 1.1:** `tests/test_verificacion_analitica.py`, `CODE_WALKTHROUGH.md` (§4.45, estructura y conceptos de pruebas) y este documento. Los archivos de las fases anteriores permanecen en su contexto histórico. La publicación de 1.1 corresponde al commit `275e755`. La Tarea 1.2 se preparó inicialmente sin commit y fue **publicada después** en `143d10f`.

### Experimentos de aprendizaje sugeridos (no ejecutados)

- Cambia una sola entrada de `CASOS` en una copia y calcula a mano T2, T4, wc y wt antes de ejecutar el método.
- Introduce deliberadamente una referencia incorrecta y observa cómo `subTest` identifica el caso sin detener los demás.
- Compara la magnitud de un residuo en kJ/kg con la escala del trabajo: no confundas un residuo diminuto con un error de modelo despreciable para cualquier motor real.

## 7. Iteración del 22 de octubre de 2026 — Tarea 1.2

### Estado, objetivo y referencia matemática

**Estado de partida verificado:** rama remota `mejoras/verificacion-numerica`, commit `275e7558b7d05322054f89ecd672ed5563c59469`, copia de trabajo limpia antes de editar. El simulador ya construía fronteras de compresión, expansión, calor y trabajo, y `test_viabilidad.py` comprobaba cambios de signo, vecindades de la raíz y clasificación. Faltaba una comparación sistemática de **ambas raíces calculadas por bisección** con su posición exacta según la ecuación cuadrática. Esta tarea sólo añade `tests/test_verificacion_raices.py` y actualiza estas explicaciones; las ecuaciones y las funciones de producción no cambian.

Con `a=(gamma−1)/gamma>0`, `x=rp**a`, `theta=T3/T1`, `h=theta*eta_c*eta_t`, `k=(1−delta)**(−a)`, la condición de trabajo motor es:

\[
Q(x)=x^2-(1+h)x+hk<0,\qquad D=(h-1)^2-4h(k-1).
\]

Si `D>0`, las raíces matemáticas independientes son `x_±=((1+h)±sqrt(D))/2` y `rp_±=x_±**(1/a)`. El test las calcula con operaciones aritméticas y `math.sqrt` **sin llamar a `bisectar_raiz()` ni a `calcular_dominios()` para determinar las referencias**. Después consulta `calcular_dominios()` para compararlas. Es independencia **de implementación**, no un modelo físico independiente.

**INTERPRETACIÓN FÍSICA.** El signo de Q se obtiene multiplicando el trabajo específico neto por un factor positivo; por eso `Q<0` equivale a trabajo positivo. Deben cumplirse simultáneamente las cuatro condiciones:

1. Compresión: `rp>1`.
2. Expansión: `rp>1/(1−delta)`.
3. Calor aportado positivo: `x<1+eta_c*(theta−1)`.
4. Trabajo neto positivo: `Q(x)<0`.

El intervalo motor es su **intersección abierta**, que puede ser vacía. Las raíces de Q por sí solas no certifican un motor. El ensayo utiliza un punto central y puntos a distancia relativa `1e−5` en los dos lados de cada frontera: esto supera la banda `1e−10` de clasificación en `evaluar_punto`. En la frontera exacta se excluye el estado porque la condición es estricta y la pequeña banda numérica lo clasifica como no motor; **la banda no es parte de la ecuación física**.

### PYTHON y algoritmo de bisección

La clase `VerificacionRaicesTests(unittest.TestCase)` declara cuatro casos no ideales moderados en tuplas y cinco métodos con firma `metodo(self)` y retorno implícito `None`. Sus entradas físicas son T1/T3 [K], gamma/eficiencias/delta [adimensional], cp [J/(kg·K)] y p1 [kPa]. Cada método llama a `calcular_dominios` y, cuando comprueba clasificación, a `evaluar_punto`. `for` recorre los parámetros; `zip` empareja raíces y resultados; `with self.subTest(caso=..., raiz=... o punto=...)` identifica un fallo concreto, sin interrumpir el resto. Una aserción falsa produce `AssertionError`; parámetros inesperadamente inválidos podrían propagar `ValueError` o `ErrorNumerico`. Ejemplo de ejecución:

```bash
python -B -m unittest discover -s tests -p 'test_verificacion_raices.py' -v
```

La **bisección** parte de un intervalo donde una función continua toma signos contrarios y, en cada iteración, elige la mitad que mantiene el cambio de signo. Por el teorema del valor intermedio, esa mitad conserva alguna raíz; el ancho disminuye geométricamente (`ancho_inicial/2**n`). `bisectar_raiz()` detiene la búsqueda cuando el ancho es suficientemente pequeño respecto a `max(abs(x_medio),1)` (tolerancia relativa `1e−12`) o encuentra un cero exacto. Esa condición es un criterio de parada en **x**, no una garantía universal sobre `rp` o sobre toda raíz mal condicionada.

La comparación evalúa tres clases de error diferentes:

| Medida | Definición | Unidad |
|---|---|---|
| Error absoluto de raíz | `abs(x_num−x_ref)` o `abs(rp_num−rp_ref)` | adimensional |
| Error relativo de raíz | error absoluto dividido por `abs(referencia)` no nula | adimensional |
| Residuo de función | `abs(Q(x_num))` | adimensional (escala de términos de Q) |

El residuo mide cuán cerca está `Q(x_num)` de cero, **no directamente la distancia hasta la raíz**; cuando `Q'(x)` es pequeño, una posición imprecisa puede dar un residuo pequeño. Además, `rp=x**(1/a)` amplifica en primer orden el error relativo aproximadamente `1/a` veces. Por eso los umbrales de posición se separan por variable: en x, `atol=2e−12` y `rtol=2e−12`; en rp, `atol=1e−9` y `rtol=2e−11`. Para el residuo se exige `abs(Q)≤2e−11*max(1,x²,abs((1+h)x),hk)`. Son tolerancias conservadoras para doble precisión y raíces simples moderadas; no se aplica un único umbral indiscriminado.

### Casos especiales y pruebas realmente ejecutadas

Las cinco comprobaciones nuevas son: (1) raíces analíticas y residuos para cuatro combinaciones no ideales (ocho raíces); (2) intersección de restricciones, punto interior, vecindades exteriores e interiores y exclusión de las fronteras; (3) límite reversible con `Q=(x−1)(x−theta)`, fronteras `rp=1` y `rp=theta**(1/a)`; (4) `D<0` y raíz doble exacta `D=0` con `theta=2`, `eta_c=.5`, `eta_t=1`, `delta=0`, de modo que `Q=(x−1)²`; (5) `D=.25>0` con `h=.5,k=1`, raíces `x=.5` y `x=1`, pero toda la región de `Q<0` exige `rp<1`, incompatible con compresión. No se han confundido estos tres últimos fenómenos con límites de representación numérica.

**Ejecución real, 22/10/2026.** Los cinco métodos nuevos pasaron (`5/5`); también siete métodos de `ViabilidadTests` directamente relacionados (raíces y vecindades, calor, expansión, reversible, dominios vacíos, clasificación combinada y errores de bisección), `7/7`. **Total focalizado: 12/12; cero fallos y cero errores**. No se ejecutó de nuevo la suite general ni se modificó un módulo físico.

| Máximo observado entre 8 raíces no ideales | Valor | Caso y raíz |
|---|---:|---|
| Error absoluto en x | `9.1304741545e−13` | entrada_fria, superior |
| Error relativo en x | `3.7747594652e−13` | entrada_fria, inferior |
| Error absoluto en rp | `1.1246470422e−10` | entrada_fria, superior |
| Error relativo en rp | `1.4261261054e−12` | entrada_fria, inferior |
| Mayor `abs(Q(x_num))` | `2.2444268666e−12` | entrada_fria, superior |

Estos números se obtuvieron además con un cálculo diagnóstico separado, sobre los mismos cuatro casos, y **no** son límites universales del método. La verificación sólo confirma la implementación y la interpretación de su **modelo termodinámico simplificado**; validar físicamente un motor requeriría datos o referencias externas. Quedaron entonces pendientes el condicionamiento junto a raíces casi dobles, límites de representación y estudios de convergencia (estos últimos se desarrollan para casos moderados en §9). Las comparaciones con SciPy se añadieron posteriormente (§8). La Tarea 1.2 se ejecutó primero sin commit y **fue publicada después** en la rama de desarrollo, commit `143d10f`.

## 8. Iteración del 22 de octubre de 2026 — Tarea 1.3: comparación opcional con SciPy

### Qué había antes y qué se contrasta

**Punto de partida:** rama `mejoras/verificacion-numerica`, commit remoto exacto `143d10fd25ebd23ddb897722b7843bddabfd16a5`. Las Tareas 1.1 y 1.2 ya verificaban identidades físicas, raíces cuadráticas y fronteras abiertas mediante ecuaciones directas. Todavía no se habían contrastado los **algoritmos propios** de raíces y máximos con implementaciones numéricas distintas.

Se añade `tests/test_comparacion_scipy.py` y se documenta en [§4.47 del manual](../../CODE_WALKTHROUGH.md). No se modifica ninguna función física ni de optimización; no se añade SciPy a `requirements.txt`. La comparación usa SciPy únicamente si está instalado. Si no, seis pruebas quedan marcadas como **omitidas** con `unittest.skipIf`; otras dos siguen ejecutándose sin SciPy.

### INGENIERÍA Y MATEMÁTICAS — tres métodos para encontrar raíces

Se comparan `bisectar_raiz` propio, `scipy.optimize.bisect` y `scipy.optimize.brentq` aplicados al **mismo intervalo con cambio de signo** y a la misma función:

- `f(x)=x²−2` en `[1,2]`: referencia matemática independiente `sqrt(2)`.
- `Q(x)=(x−1)(x−h)+h(k−1)` de tres ciclos no ideales, en dos intervalos que encierran respectivamente cada raíz. La fórmula cuadrática directa proporciona las referencias, como en la Tarea 1.2.

La **bisección** divide repetidamente el intervalo que contiene el cambio de signo; es robusta por continuidad, pero reduce el ancho a un ritmo fijo. **Brent** también mantiene un intervalo válido y combina pasos seguros con interpolación para acelerar cuando es conveniente. No se utiliza ninguno si los extremos tienen el mismo signo: los tres rechazan `f(x)=x²+1` en `[1,2]` con `ValueError`.

La variable termodinámica es `x=rp**a`, donde `a=(gamma−1)/gamma`. La posición buscada es `rp=x**(1/a)`: una pequeña desviación relativa de x puede aumentar en rp aproximadamente por el factor `1/a`. Por ello se registran **errores absolutos y relativos en ambas variables** y, por separado, el **residuo** `|Q(x)|`. Un residuo pequeño no garantiza una raíz bien localizada si la pendiente cerca de ella es pequeña.

### INGENIERÍA Y PYTHON — máximos de trabajo y rendimiento

Se compara cada buscador propio de malla logarítmica y **sección áurea** con `scipy.optimize.minimize_scalar(method="bounded")`. Dado que `minimize_scalar` busca un *mínimo*, el callback devuelve `-trabajo_neto` [kJ/kg] o `-rendimiento` [fracción]: minimizar `-W` equivale a maximizar `W`, y análogamente para eta.

Ambos algoritmos buscan en `y=log(rp)`, con `rp=exp(y)`. Así el intervalo representa **razones multiplicativas** de presión y evita comparar una búsqueda en escala lineal con otra logarítmica. Se recorta sólo para la búsqueda una fracción `1e−6` en cada extremo del intervalo logarítmico abierto; **las fronteras físicas no cambian**. Se prueban cuatro máximos interiores de trabajo (uno ideal y tres no ideales) y tres máximos interiores de rendimiento **no ideal**.

Para aceptar un máximo de SciPy se exige, además de `result.success` y números finitos, estar dentro del dominio, superar `evaluar_punto(...)["viable"]` y presentar valores menores del objetivo en dos puntos interiores a ambos lados. Este último control es una evidencia local de máximo, **no una demostración global para funciones arbitrarias**. El rendimiento ideal constituye un contraejemplo deliberado: crece hacia una frontera de aporte nulo y sólo tiene **supremo no alcanzado**. SciPy puede informar éxito junto a la frontera; el filtro descarta correctamente la etiqueta de máximo motor interior. Cuando no existe dominio motor, la búsqueda propia informa ausencia de solución en vez de atribuirla a fallo de convergencia.

**PYTHON.** `for` y `unittest.subTest()` reutilizan combinaciones de parámetros sin crear docenas de métodos. Una función interna `contado(x)` utiliza un cierre sobre una lista `[0]` para contar cada evaluación; en SciPy se coteja con `function_calls` (raíces) o `nfev` (máximos). `types.SimpleNamespace` fabrica cuatro resultados falsos (`success=False`, frontera, NaN, punto sin máximo) para verificar el filtro sin necesitar provocar fallos reales inestables. Las firmas y retornos de los dos auxiliares, junto a los ocho tests, están descritos en el manual §4.47.

### Tolerancias, precisión y resultados observados

Se fijan explícitamente `xtol=rtol=1e−12` en `bisect`/`brentq`; el método propio usa `tolerancia=1e−12`, que detiene por **anchura relativa del intervalo en x**. No son criterios matemáticamente idénticos. Para las referencias analíticas se comprueba:

| Magnitud | Límite de error/residuo |
|---|---|
| Raíz x, adimensional | `|Δx|≤2e−12+3e−12|x_ref|` |
| Raíz rp, adimensional | `|Δrp|≤1e−9+2e−11|rp_ref|` |
| Residuo de Q, adimensional | `|Q(x)|≤2e−11·max(1,x²,|(1+h)x|,hk)` |
| Posición rp del máximo, adimensional | `|Δrp|≤1e−6+2e−6·max(rp_propio,rp_SciPy)` |
| Trabajo máximo, kJ/kg | `|ΔW|≤1e−8+1e−10·max(|W_propio|,|W_SciPy|,cp*T3/1000)` |
| Rendimiento máximo, fracción | `|Δeta|≤1e−10+1e−10·|eta_SciPy|` |

En máximos se fija `xatol=1e−9` en `y=log(rp)` para SciPy y `tolerancia_log=1e−9` para el buscador propio. Cerca de un máximo plano, los valores de W o eta varían **cuadráticamente** con la desviación de posición; por tanto, pueden coincidir casi a precisión de máquina mientras rp difiere en varias millonésimas. Las tolerancias permiten esa geometría, sin ser márgenes experimentales. `resolucion_rp` informa una escala de precisión interna, no una cota formal del error frente a SciPy.

**Ejecución real (22/10/2026, SciPy 1.17.0):** ocho métodos nuevos superados, ninguno fallido u omitido; ocho pruebas preexistentes de raíces/optimización también superadas. **Total focalizado: 16/16.** En un ensayo separado que simula ausencia de SciPy, se ejecutaron **2 métodos correctos y 6 omitidos**. No se ejecutó la suite completa.

| Comparación | Mayor error absoluto observado | Mayor error relativo observado |
|---|---:|---:|
| Raíces Q, posición x frente a fórmula cuadrática (3 métodos) | `3.3155700e−12` | `1.1178260e−12` |
| Raíces Q, posición rp frente a fórmula cuadrática (3 métodos) | `4.2663828e−10` | `4.5051234e−12` |
| Máximo trabajo, posición rp propia frente a SciPy | `7.2124703e−7` | `5.9060284e−8` |
| Máximo trabajo, W propio frente a SciPy [kJ/kg] | `2.2737368e−13` | `4.8875800e−16` |
| Máximo rendimiento no ideal, posición rp | `1.7468397e−6` | `6.9062480e−8` |
| Máximo rendimiento no ideal, eta [fracción] | `3.3306691e−16` | `8.5944239e−16` |

El mayor residuo en las seis raíces de Q y tres métodos fue `|Q(x)|=1.0637699e−11` (SciPy `bisect`, raíz superior del caso de referencia). La mayor diferencia **entre bisección propia y SciPy bisect**, sin fórmula intermedia, fue `3.5766945e−12` en x y `4.6023274e−10` en rp; frente a `brentq` fue `1.6404655e−12` en x y `2.0206414e−10` en rp.

Para el ejemplo `x²−2=0`, con referencia `sqrt(2)≈1.4142135623730951`, los errores absolutos fueron `2.1605e−13` (propia, 43 llamadas), `1.5803e−12` (`bisect`, 41 llamadas) y `4.1300e−14` (`brentq`, 8 llamadas). Sólo describen ese caso, no la rapidez garantizada de cada algoritmo.

| Ejemplo no ideal de referencia | Método propio | SciPy bounded | Evaluaciones propia / SciPy |
|---|---:|---:|---:|
| rp para máximo trabajo | `12.89505173504` | `12.89505166962` | 297 / 6 |
| Trabajo máximo [kJ/kg] | `373.2108274827` | `373.2108274827` | — |
| rp para máximo rendimiento | `35.45232192220` | `35.45232299066` | 297 / 11 |
| Rendimiento máximo [fracción] | `0.4389310716313` | `0.4389310716313` | — |

Los contadores de raíces variaron de **43 a 45** evaluaciones propias, **41 a 43** en `bisect` y **10 a 11** en `brentq` para estos seis intervalos; los ejemplos de máximos propios usaron 297 evaluaciones (malla y refinamiento) frente a **6–24** de SciPy para trabajo y **11–14** para rendimiento. Se cuentan funciones **en estrategias distintas**: no se concluye superioridad universal de velocidad ni se exigen iteraciones exactas en los tests.

**Caso límite observado:** SciPy devuelve `success=True` y `rp≈403.4151` para el rendimiento ideal. `evaluar_punto` aún considera motor ese punto interior, pero su rendimiento sigue aumentando al acercarse a la frontera: **no es un máximo interior**, y el filtro lo rechaza. El buscador propio conserva `estado="supremo_no_alcanzado"`.

### Qué hemos aprendido y qué queda pendiente

Los resultados son consistentes en estos ejemplos **moderados y con máximos interiores resolubles**. No se ha detectado una discrepancia que justifique alterar por ahora los algoritmos propios. La diferencia de evaluaciones sugiere estudiar su coste en futuras tareas, pero **sin benchmarks exhaustivos aquí**. En casos cercanos a raíces dobles, fronteras abiertas o máximos muy planos podría ser necesario estudiar precisión y criterios de aceptación con mayor cuidado.

Esta es **verificación cruzada de implementaciones que comparten el mismo modelo**; no valida los supuestos termodinámicos frente a datos experimentales. Al cerrar la Tarea 1.3 aún estaban pendientes los estudios de tolerancia, malla, convergencia, condicionamiento y límites numéricos; el estudio representativo de los tres primeros se prepara en §9. La Tarea 1.3 quedó **publicada después** en el commit `8ecbc1b` de `mejoras/verificacion-numerica`, sin modificar `main`.

## 9. Iteración del 22 de octubre de 2026 — Tarea 1.4: convergencia y sensibilidad numérica

### Qué se estudia y por qué

**Estado verificado:** rama remota `mejoras/verificacion-numerica`, commit `8ecbc1bf75e7e68fc3377cbf97017f8480d32553`. La Tarea 1.3 había demostrado concordancia con SciPy en casos seleccionados, pero no explicaba cuánto cambia la respuesta cuando se modifican la **tolerancia**, el **presupuesto de iteraciones** o el **número de muestras**. Esta Tarea 1.4 añade sólo `tests/test_convergencia_numerica.py`, la sección [4.48 del manual](../../CODE_WALKTHROUGH.md) y esta sección educativa. No se cambian funciones de producción, predeterminados, interfaz ni dependencias.

En matemáticas, una sucesión converge si se acerca a un límite. En un ordenador, la **convergencia numérica** significa que el algoritmo satisface un **criterio de parada declarado**, con operaciones finitas y redondeo. Son conceptos conectados, pero distintos: cumplir la condición de anchura de un intervalo no equivale a demostrar un error exacto en `rp`; tampoco implica que la física del modelo sea experimentalmente correcta.

### A. Raíces: tolerancia, anchura, residuos y coste

La bisección exige una función continua cuyos valores en los extremos tengan signos contrarios. Si el intervalo inicial mide `L`, tras `n` divisiones su anchura geométrica será `L/2**n`; si el algoritmo hace la comprobación antes de subdividir una última vez, hay que contar exactamente en qué momento se observa esa anchura. Se ensayan `f(x)=x²−2` con referencia `sqrt(2)` y **dos raíces** de la cuadrática de trabajo de cada uno de dos ciclos no ideales (`referencia` y `gamma_133`), con fórmulas directas `x_±=((1+h)±sqrt(D))/2`. Son cinco raíces en total, todas simples y moderadas. Para las cuatro tolerancias se mantienen **100 iteraciones disponibles**.

| Tolerancia en x | Máx. `|Δx|` | Máx. `|Δrp|` | Máx. residuo `|f(x)|` | Pasos de bisección | Evaluaciones |
|---|---:|---:|---:|---:|---:|
| `1e−6` | `3.281e−7` | `4.222e−5` | `1.053e−6` | 21–23 | 23–25 |
| `1e−8` | `1.405e−8` | `2.075e−6` | `3.164e−8` | 27–29 | 29–31 |
| `1e−10` | `1.417e−10` | `1.824e−8` | `4.548e−10` | 34–36 | 36–38 |
| `1e−12` | `3.191e−13` | `3.359e−11` | `8.397e−13` | 41–43 | 43–45 |

El error relativo máximo en x de toda la serie es `2.787e−7` (`gamma_133`, raíz inferior, `1e−6`); en rp es `1.123e−6` (mismo caso). Los máximos absolutos de x (`3.281e−7`), rp (`4.222e−5`) y residuo (`1.053e−6`) corresponden a la raíz **superior** del caso de referencia con `1e−6`. Los valores en rp se refieren únicamente a las cuatro raíces termodinámicas, no a `sqrt(2)`.

**INGENIERÍA.** La conversión `rp=x**(1/a)` con `a=(gamma−1)/gamma` puede amplificar el error relativo en aproximadamente `1/a`. El **residuo** `|Q(x)|` expresa el defecto de la ecuación, mientras que el **error de raíz** mide distancia a la solución analítica; una pendiente pequeña puede dejar un residuo minúsculo sin precisión de posición. Por eso la prueba compara el error con la **última anchura reconstruida** más un margen para coma flotante; nunca interpreta `tolerancia` como una cota universal de rp.

Al limitar deliberadamente la búsqueda a **1, 5 o 12 pasos** con `tolerancia=1e−12`, las cinco raíces producen `ErrorNumerico` por agotamiento. El callback registra exactamente dos evaluaciones de los extremos más las de esos pasos. Un intervalo sin cambio de signo produce `ValueError`, no un falso resultado ni un diagnóstico de dominio motor vacío. No se estudian aquí raíces casi dobles.

### B. Tamaño de malla: resolución inicial frente a coste

`buscar_maximo_numerico()` toma muestras en `y=log(rp)` y refina con sección áurea. Se fijan `tolerancia_log=1e−9`, `max_iteraciones=100` y los parámetros físicos de **tres casos** (ideal, no ideal de referencia y `gamma_133`); sólo cambia `muestras`. El óptimo analítico se usa **después**, para medir el error y verificar si los nodos vecinos del mejor punto inicial lo acotaban, nunca para orientar el algoritmo.

| Muestras | Máx. error `rp` | Máx. error trabajo [kJ/kg] | Evaluaciones | Iteraciones refinamiento |
|---:|---:|---:|---:|---:|
| 17 | `8.492e−7` | `1.705e−13` | 62–63 | 43–44 |
| 33 | `8.414e−7` | `2.274e−13` | 77–78 | 42–43 |
| 65 | `2.389e−7` | `2.274e−13` | 108 | 41 |
| 129 | `3.969e−7` | `2.274e−13` | 170–171 | 39–40 |
| **257** | **`1.792e−7`** | **`1.705e−13`** | **297** | **38** |
| 513 | `5.359e−7` | `5.684e−14` | 551–552 | 36–37 |

Las seis mallas acotaron el máximo interior en estos tres casos. El mayor error absoluto de rp se produjo con **17 nodos en el caso ideal** (`8.492e−7`); el mayor relativo fue `4.389e−8` con 17 nodos en el caso de referencia. El mayor error observado de trabajo fue `2.274e−13 kJ/kg` (entre otros, referencia con 33 nodos). Aumentar muestras **no mejora obligatoriamente el error de rp**: las diferencias son pequeñas, el máximo es plano y el valor de W ya está próximo al límite de redondeo. En cambio, más muestras sí elevan claramente las evaluaciones. Son **contadores de funciones, no tiempos de CPU**; no se ha hecho benchmarking.

### C. Refinamiento: cambiar sólo la tolerancia logarítmica

Con `muestras=257` y `max_iteraciones=100` fijos, se aplican las cuatro tolerancias a **trabajo** (los tres casos anteriores) y a **rendimiento no ideal** (dos casos con máximo interior). El candidato estacionario `calcular_candidato_analitico` o `calcular_candidato_rendimiento` es referencia de contraste, no entrada de búsqueda. El error de posición se expresa en `rp` (adimensional), el trabajo en **kJ/kg** y el rendimiento como **fracción**, no como porcentaje.

| `tolerancia_log` | Máx. `|Δrp|` trabajo | Máx. `|ΔW|` [kJ/kg] | Evaluaciones trabajo (máx.) | Máx. `|Δrp|` rendimiento | Máx. `|Δeta|` | Evaluaciones rendimiento (máx.) |
|---|---:|---:|---:|---:|---:|---:|
| `1e−5` | `9.258e−12` | `2.274e−13` | 278 | `1.829e−5` | `2.237e−14` | 278 |
| `1e−7` | `2.530e−7` | `1.137e−13` | 288 | `1.082e−6` | `2.220e−16` | 287 |
| `1e−9` | `1.792e−7` | `1.705e−13` | 297 | `1.649e−6` | `2.220e−16` | 297 |
| `1e−11` | `1.792e−7` | `2.274e−13` | 307 | `1.649e−6` | `2.220e−16` | 306 |

Las iteraciones máximas fueron respectivamente **19, 29, 38 y 48** para trabajo, y **19, 28, 38 y 47** para rendimiento. El mayor error absoluto de rp de trabajo en esta serie (`2.530e−7`) corresponde al **ideal, `1e−7`**, y el mayor error relativo (`1.485e−8`) a **`gamma_133`, `1e−11`**. En rendimiento el mayor error absoluto (`1.829e−5`), relativo (`5.849e−7`) y en fracción (`2.237e−14`) se produjo en **`gamma_133`, `1e−5`**. Los errores máximos de cada fila pueden corresponder a casos distintos: no constituyen una trayectoria de un único ensayo.

**Máximo plano y doble precisión.** En un extremo estacionario, la derivada primera se anula y el cambio de W/eta por un pequeño desplazamiento en rp suele ser de **segundo orden**. Por ello una coincidencia de quince cifras en trabajo **no** garantiza la misma precisión en la posición. Los buscadores informan `resolucion_rp=rp·max(tolerancia_log,32√eps)`; como `32√eps≈4.768e−7` para `float64`, esta escala **deja de reducirse** al pedir `1e−7`, `1e−9` o `1e−11`. Es una estimación conservadora de resolución, no el error medido. Para el caso no ideal de referencia, la `resolucion_rp` observada de **trabajo** fue `1.290e−4` (`1e−5`) y aproximadamente `6.149e−6` (`1e−7`, `1e−9`, `1e−11`); para **rendimiento**, `3.545e−4` y aproximadamente `1.690e−5`, respectivamente. En ese mismo caso, el error efectivo de rp a `1e−9` y `1e−11` resultó idéntico mientras las evaluaciones crecieron de 297 a 306–307. Una tolerancia más estricta puede aumentar el coste sin aportar cifras fiables adicionales; ello no prueba por sí solo un defecto.

Con el control fijo `tolerancia_log=1e−11`, los presupuestos máximos de **1, 12 y 30 iteraciones** causaron el mensaje explícito de no convergencia en los casos seleccionados de ambos optimizadores; con **100** finalizaron correctamente. No se inventan posiciones ni evaluaciones para las búsquedas que lanzan una excepción, pues su API no devuelve un resultado parcial.

### D. Fronteras físicas abiertas y banda de admisión

Los dominios son intervalos **abiertos** por exigencias físicas (`rp>1`, expansión, `qin>0` y `wneto>0`). En los casos ideal y no ideal de referencia se examinan puntos interiores multiplicando el extremo inferior por `1+distancia` o el superior por `1−distancia`. Una distancia muy pequeña aún puede superar cero matemáticamente y, a la vez, ser **rechazada por la banda numérica relativa `1e−10`** de `evaluar_punto()`.

| Caso / frontera | Distancia relativa | Trabajo `wneto` [kJ/kg] | Calor `qin` [kJ/kg] | ¿Motor aceptado? |
|---|---:|---:|---:|---|
| Ideal, superior | `1e−3` | `0.376799` | `0.459593` | Sí |
| Ideal, superior | `1e−6` | `3.76688e−4` | `4.59429e−4` | Sí |
| Ideal, superior | `1e−9` | `3.76688e−7` | `4.59428e−7` | Sí |
| Ideal, superior | `1e−12` | `3.76531e−10` | `4.59306e−10` | **No (banda)** |
| No ideal, superior | `1e−3` | `0.312446` | `218.934` | Sí |
| No ideal, superior | `1e−9` | `3.12295e−7` | `218.522` | Sí |
| No ideal, superior | `1e−12` | `2.44427e−10` | `218.522` | **No (banda)** |

La frontera inferior de ambos casos presenta el mismo patrón de admisión: `1e−3`, `1e−6` y `1e−9` aceptados; `1e−12` excluido. Con `tolerancia=0`, los puntos a esas cuatro distancias aún tienen todos los márgenes estrictamente positivos; el diagnóstico correcto a `1e−12` es **punto matemáticamente interior excluido por tolerancia**, no ausencia de dominio. En ambos extremos el trabajo tiende a cero, pero `qin` sólo tiende a cero en el extremo **superior ideal**: el no ideal del ejemplo pierde la condición de trabajo antes que la de calor. Al ser rechazado un punto, `rendimiento=None`, evitando dividir por aporte de calor no admisible. Las propias fronteras quedan excluidas; el rendimiento ideal conserva un **supremo no alcanzado** y no se declara un máximo ficticio.

### PYTHON, tolerancias de aceptación y comprobaciones reales

Se usan `unittest.TestCase`, ocho métodos y `subTest()` para identificar combinaciones, sin crear centenares de métodos independientes. El auxiliar `_referencias_raices(self)` prepara los cinco intervalos y sus fórmulas; su callback `Q(x,h=h,k=k)` fija los coeficientes de cada caso mediante argumentos por defecto para evitar reutilizar por accidente los del último ciclo. `contado(x)` guarda cada evaluación. En mallas, el test reconstruye por separado los puntos iniciales, identifica el nodo de máximo y confirma que sus vecinos encierran el óptimo analítico. Las firmas, unidades, excepciones y llamadas aparecen en el [manual §4.48](../../CODE_WALKTHROUGH.md).

Las pruebas de bisección verifican el intervalo dividido y un margen de coma flotante de `5e−13·max(1,|x_ref|)`; el error relativo transformado en rp se controla mediante `4|Δx|/(a·x_ref)+1e−12`. Para posiciones del máximo de trabajo se admite `|Δrp|≤2e−7·rp_ref` al variar mallas, o `|Δrp|/rp_ref≤max(2e−7,3*tolerancia_log)` al variar tolerancia. Para rendimiento no ideal se exige `|Δrp|/rp_ref≤max(2e−6,3*tolerancia_log)`. En magnitudes objetivo, `|ΔW|≤1e−9 kJ/kg` y `|Δeta|≤1e−10`. Estos márgenes son deliberadamente mayores que los errores medidos en los casos **moderados** ensayados; no se han reajustado para imponer monotonía ni son garantías generales. Se comprueba adicionalmente la anchura final en logaritmos con `tolerancia_log+1e−14` para redondeo al exponenciar límites.

**Ejecución realmente realizada el 22/10/2026:** `8/8` métodos nuevos correctos y `8/8` regresiones seleccionadas correctas de `test_verificacion_raices.py`, `test_comparacion_scipy.py` y `test_optimizacion_rendimiento.py`. **Total final 16 métodos superados, 0 fallidos, 0 omitidos**, sin suite general. Hubo una aserción inicialmente incorrecta en el test nuevo: el dominio vacío se representa como `()` y no como `None`; se corrigió únicamente esa expectativa y se ejecutaron de nuevo las ocho pruebas nuevas con éxito. No se detectó error de producción. Comandos:

```bash
python -B -m unittest discover -s tests -p 'test_convergencia_numerica.py' -v
PYTHONPATH=tests python -B -m unittest -v \
  test_verificacion_raices.VerificacionRaicesTests.test_raices_noideales_con_referencias_y_residuos \
  test_verificacion_raices.VerificacionRaicesTests.test_interseccion_de_restricciones_y_fronteras_abiertas \
  test_comparacion_scipy.ComparacionSciPyTests.test_raiz_matematica_conocida \
  test_comparacion_scipy.ComparacionSciPyTests.test_maximo_trabajo_con_bounded \
  test_comparacion_scipy.ComparacionSciPyTests.test_maximo_rendimiento_noideal_con_bounded \
  test_optimizacion_rendimiento.RendimientoTests.test_busqueda_numerica_independiente \
  test_optimizacion_rendimiento.RendimientoTests.test_banda_numerica_no_crea_un_maximo_de_frontera \
  test_optimizacion_rendimiento.RendimientoTests.test_ideal_supremo_no_es_optimo_motor
```

**Conclusiones acotadas.** Los **257 nodos predeterminados son razonables**: los tres ejemplos acotan un máximo admisible y alcanzan error de rp menor de `2e−7` con unas 297 evaluaciones. No obstante, 17–129 nodos también lo consiguen en estos ejemplos y pueden ahorrar llamadas: no se demuestra que 257 sea óptimo para otros dominios. **`tolerancia_log=1e−9` es razonable**, aunque en estos máximos planos apretar más que `1e−7` no ofreció mejora consistente de la posición. **100 iteraciones bastaron** holgadamente en lo ensayado (máximo 48), no en cualquier problema posible. La planitud, las evaluaciones redundantes cuando la precisión está saturada y la clasificación en las bandas estrechas merecen investigaciones futuras; **no hay evidencia para cambiar hoy los algoritmos ni los controles predeterminados**. Permanecen fuera de alcance raíces casi dobles, estudio estadístico o temporal de eficiencia, extremos de representación y validación física experimental. **Nota posterior de trazabilidad:** la Tarea 1.4 fue publicada en `c3b4bfea12cf6faa1dc90c8f8fb16fb9e8fe7131`; la frase original de «pendiente de revisión» describía sólo el estado anterior a esa publicación.

## 10. Iteración del 22 de octubre de 2026 — Tarea 1.5: energía e invariantes físicos

### Objetivo y significado de la primera ley

La base verificada es la rama remota `mejoras/verificacion-numerica` en `c3b4bfea12cf6faa1dc90c8f8fb16fb9e8fe7131`. La batería 1.1 contrastaba principalmente el **ideal**; 1.2–1.4 verificaron raíces, máximos y sus controles numéricos. Faltaba un contraste compacto de los balances **no ideales**, de su respuesta a cambios físicos y de su coherencia cuando el punto es calculable pero **no produce trabajo motor admisible**. Se añade sólo `tests/test_invariantes_fisicos.py`; `viabilidad.py`, optimizadores, interfaz y dependencias permanecen inalterados.

Para compresor/turbina adiabáticos y `cp` constante, se usan temperaturas absolutas en K, `cp` en J/(kg·K) y se divide por 1000 para obtener **kJ/kg**:

\[
\begin{aligned}
w_c &= c_p(T_2-T_1)/1000, & w_t &= c_p(T_3-T_4)/1000,\\
q_{in} &= c_p(T_3-T_2)/1000, & q_{out} &= c_p(T_4-T_1)/1000,\\
w_{neto} &= w_t-w_c &= q_{in}-q_{out}.
\end{aligned}
\]

`qout` se calcula **únicamente dentro del test** y puede tener signo algebraico fuera de las condiciones de motor; no es una salida nueva de producción. La verificación construye referencias no ideales a partir de los **parámetros de entrada**, sin llamar a los métodos verificados para calcular lo esperado: con `a=(gamma−1)/gamma`, `E=rp(1−delta)` (expansión efectiva),

\[
T_{2,ref}=T_1\left[1+\frac{rp^a-1}{\eta_c}\right],\qquad
T_{4,ref}=T_3\left[1-\eta_t\left(1-E^{-a}\right)\right].
\]

Desde esas referencias se reconstruyen `wc`, `wt`, `wn`, `qin` y `qout`. Se ensayan cinco conjuntos: un ideal de anclaje, tres no ideales motores moderados (incluida `gamma=1.33`) y un no ideal no motor (`rp=200`). Verificar una identidad y comparar referencias de implementación sirve para detectar signos, unidades o errores de programación. **No es una validación física externa** de eficiencias, gas perfecto o pérdidas reales.

### Irreversibilidades, límite reversible y cambios de escala

Con `rp=10`, `T1=288.15 K`, `T3=1600 K`, `gamma=1.4`, `cp=1005 J/(kg·K)` y `p1=100 kPa`, se parte de `eta_c=.95`, `eta_t=.98`, `delta=.01` y se modifica **una sola magnitud cada vez**. Reducir `eta_c` a `.8` eleva `T2` y `wc`; reducir `eta_t` a `.82` eleva `T4` y reduce `wt`; elevar `delta` a `.12` reduce `p3/p4` y `wt`. En los tres casos disminuye `wn` y se comprueba de nuevo la primera ley. Se consulta el indicador motor del resultado: las tendencias algebraicas **no dependen** de que la combinación resulte admisible como motor.

El límite reversible se verifica poniendo simultáneamente `eta_c=eta_t=1−epsilon`, `delta=epsilon` con `epsilon=.1, .01, .001, .00001`. La diferencia absoluta de trabajo neto respecto del ideal a igual `rp=10` se redujo sucesivamente a `130.36835`, `12.844907`, `1.2828066` y `0.012826236 kJ/kg`. La diferencia de rendimiento pasó de `0.11377736` a `1.0989753e−5` (fracciones, no puntos porcentuales). Es una tendencia **en esos cuatro casos**, no una demostración de monotonicidad universal de todos los indicadores.

La invariancia es consecuencia de las **hipótesis del modelo**:

- Al cambiar sólo `cp` por los factores `.6`, `1.5`, `2.3` (ideal y no ideal), las temperaturas y presiones permanecieron idénticas; `wc`, `wt`, `wn`, `qin`, `qout` se escalaron linealmente y `eta=wn/qin` permaneció constante en puntos motores.
- Al cambiar sólo `p1` por `.5`, `1.7`, `3`, las cuatro presiones se escalaron de forma proporcional; las temperaturas, energías específicas y rendimiento no cambiaron en los casos ejecutados. Las relaciones de presión, no su escala absoluta, fijan aquí las temperaturas.

Las conclusiones dejarían de tener esa forma sencilla si `cp` dependiera de temperatura o si las pérdidas cambiaran con presión, caudal o geometría.

### Estados no motores: coherencia no equivale a admisión

También se evalúan cinco casos: `rp=1` ideal (sin compresión/expansión), `rp=1.03` con pérdida `.05` (expansión insuficiente), `rp=500` ideal (`qin≤0`), `rp=200` no ideal (calor aún positivo, `wn≤0`) y `T1=300 K`, `T3=400 K`, eficiencias `.85/.9`, pérdida `.5` (dominio motor vacío). Se comprueba **a la vez** que las cuatro energías se pueden calcular, el balance cierra, los códigos de `motivos` corresponden a márgenes que no superan sus umbrales y el rendimiento y el cociente de trabajos motores son `None`. Un dominio vacío se registra como `intervalo=()`; no significa que fallen las operaciones de energía.

La banda se observa cerca de la frontera superior no ideal `rp≈155.454326`. Con separación relativa `1e−9`, el programa acepta el punto (`wn≈3.12295e−7 kJ/kg`, mayor que el umbral `1.608e−7`); a `1e−12`, la energía neta sigue positiva (`≈2.44427e−10 kJ/kg`) pero queda **dentro** de la tolerancia energética, de modo que se informa `trabajo_neto` como motivo/frontera y **no** se publica rendimiento motor. Con `tolerancia=0` el punto sigue teniendo márgenes físicamente positivos. Esto diferencia *estado matemáticamente interior*, *punto admitido por la banda* y *dominio vacío*. Entradas físicamente imposibles (por ejemplo `cp<=0`) generan `ValueError`, y un límite no representable genera `ErrorNumerico`; estos dos últimos contratos ya se prueban en `test_viabilidad.py` y no se duplican.

### PYTHON: pruebas parametrizadas, errores y resultados observados

`InvariantesFisicosTests(unittest.TestCase)` contiene **seis métodos `test_...`**, con `subTest(caso=...)`, `subTest(factor_cp=...)`, `subTest(factor_p1=...)` para mostrar la combinación exacta que falla. La clase declara `CASOS` como tuplas de entradas en unidades explícitas y `MEDIDAS` como diccionario donde registra máximos realmente medidos. `_comparar(self,magnitud,obtenido,referencia,atol)` conserva por nombre el error absoluto y el relativo si la referencia no es cero; `_comprobar_balance(self,punto,cp)` contrasta cuatro energías y tres residuos y retorna el calor rechazado calculado para el ensayo. Ambos son **auxiliares exclusivos de la prueba**, con firmas y llamadas desarrolladas en [§4.49 del manual](../../CODE_WALKTHROUGH.md). El módulo se ejecuta con `python -B -m unittest discover -s tests -p 'test_invariantes_fisicos.py' -v`, sin bibliotecas adicionales.

Se acepta `|resultado−referencia| ≤ atol + 2e−12·|referencia|`, con `atol=1e−9 K/kPa` para estados y `1e−10 kJ/kg` para energías; el residuo de primera ley permite además el término de redondeo `2e−12·escala_energética`. La parte absoluta protege referencias cercanas a cero; la relativa escala con el tamaño. En cocientes como `eta`, se usa una tolerancia absoluta propia. **No son incertidumbres físicas del motor.** Un error relativo de residuo frente a referencia cero no está definido; por eso se da el residuo **absoluto**.

**Mediciones ejecutadas (22/10/2026, cinco casos de referencia y escalados):**

| Magnitud contrastada | Máximo error absoluto | Máximo error relativo |
|---|---:|---:|
| Temperaturas vs. referencia | `2.274e−13 K` | `1.883e−16` |
| Trabajos y calor vs. referencia independiente | `4.547e−13 kJ/kg` | `5.452e−15` |
| `qout` del estado vs. referencia | `1.137e−13 kJ/kg` | `2.320e−16` |
| Residuos de primera ley | `2.842e−13 kJ/kg` | No definido (cero) |
| Energías con escalado de `cp` | `4.547e−13 kJ/kg` | `2.880e−16` |
| Rendimiento con escalado de `cp` | `1.110e−16` (fracción) | `3.009e−16` |
| Energías y rendimiento al escalar `p1` | `0` | `0` |

Los máximos de las distintas columnas pueden venir de casos diferentes. La comparación del balance calculado directamente con sus mismas temperaturas produjo diferencias exactamente nulas para las cuatro energías; los **residuos** no necesariamente son cero por la suma/resta en coma flotante. Estos valores son magnitudes medibles del **software** bajo estos escenarios, no errores conocidos frente a mediciones de turbinas reales.

**Pruebas realmente ejecutadas:** los **6 métodos nuevos** y **6 regresiones relacionadas** de `test_verificacion_raices.py`, `test_comparacion_scipy.py` y `test_convergencia_numerica.py` finalizaron correctamente: **12/12** en la primera verificación. Las otras **9 regresiones** de `test_verificacion_analitica.py`, `test_viabilidad.py` y `test_segunda_ley.py` se bloquearon inicialmente en la importación `main → reporting → dashboard` por ausencia de `jinja2` (sin llegar a evaluar aserciones). Después se instaló **exclusivamente `requirements.txt`** en un entorno virtual aislado de `/tmp` y se ejecutaron esas nueve pruebas: **9/9 correctas, 0 fallidas, 0 omitidas**. Total acumulado: **21/21 métodos correctos**, en dos etapas; **no se repitieron las doce pruebas anteriores** ni se ejecutó la suite completa. Entorno complementario: **Python 3.12.14, Flask 3.1.3, Jinja2 3.1.6, NumPy 2.5.4 y Matplotlib 3.11.2**. No se modificaron dependencias declaradas ni interfaz. Comandos (la segunda etapa utiliza el intérprete del entorno virtual):

```bash
python -B -m unittest discover -s tests -p 'test_invariantes_fisicos.py' -v
PYTHONPATH=tests python -B -m unittest -v \
  test_verificacion_raices.VerificacionRaicesTests.test_interseccion_de_restricciones_y_fronteras_abiertas \
  test_verificacion_raices.VerificacionRaicesTests.test_limite_reversible_factoriza_y_es_abierto \
  test_verificacion_raices.VerificacionRaicesTests.test_raices_reales_sin_dominio_motor \
  test_comparacion_scipy.ComparacionSciPyTests.test_dominio_vacio_se_distingue_de_fallo_numerico \
  test_convergencia_numerica.ConvergenciaNumericaTests.test_fronteras_abiertas_y_banda_de_viabilidad \
  test_convergencia_numerica.ConvergenciaNumericaTests.test_dominio_vacio_separa_ausencia_de_fallo_numerico
```

```bash
PYTHONPATH=tests python -B -m unittest -v \
  test_verificacion_analitica.VerificacionAnaliticaIdealTests.test_balances_con_referencias_y_residuo \
  test_viabilidad.ViabilidadTests.test_limite_reversible_en_estados_dominios_y_barrido \
  test_viabilidad.ViabilidadTests.test_calor_positivo_no_basta_para_motor \
  test_viabilidad.ViabilidadTests.test_invariancia_limites_con_cp_y_presion \
  test_viabilidad.ViabilidadTests.test_parametros_invalidos_no_son_inviabilidad \
  test_viabilidad.ViabilidadTests.test_limite_numerico_no_se_clasifica_como_inviabilidad \
  test_segunda_ley.SegundaLeyTests.test_contraste_analitico_independiente \
  test_segunda_ley.SegundaLeyTests.test_limite_reversible \
  test_segunda_ley.SegundaLeyTests.test_diagnostico_no_motor
```

**Trazabilidad posterior:** la Tarea 1.5 se publicó en `57da73db01882ab32bd5d92d14bdbe739c272b79`. Las afirmaciones anteriores sobre pruebas focalizadas describen el **momento de la Tarea 1.5**; la suite completa se ejecutó después, en la Etapa 6 (§11). Siguen fuera del alcance la validación experimental, propiedades variables, extremos numéricos y nuevas optimizaciones.

## 11. Iteración del 22 de octubre de 2026 — Etapa 6: reproducibilidad y cierre técnico

### Qué cambia respecto de las tareas anteriores

Las tareas 1.1–1.5 añadieron comprobaciones **especializadas**. Su ejecución por separado no garantizaba que todas las pruebas, informes y rutas Flask funcionasen juntas tras los últimos cambios. En esta etapa se reunió la evidencia en una [matriz de aceptación, tablas y procedimiento reproducible](12_cierre_verificacion_numerica.md), sin modificar código físico, optimizadores, controles predeterminados ni dependencias declaradas. El resultado de la etapa es **documentación de cierre pendiente de revisión**, no un nuevo modelo.

### PYTHON — entorno aislado, ejecución y verificaciones opcionales

`python3 -m venv` permite instalar en un directorio temporal las versiones concretas de NumPy, Matplotlib y Flask que usa una ejecución, sin modificar el intérprete global ni el repositorio. Flask incorpora Jinja2 como dependencia. `unittest discover -s tests -q` busca los módulos de pruebas y devuelve un conteo de **métodos**, mientras que `subTest()` agrupa subcasos dentro de un método: por eso **215 tests** no significa sólo 215 combinaciones de parámetros físicos.

SciPy se añadió **únicamente al entorno temporal de verificación** (`1.17.0`), no a `requirements.txt`. Esto permitió comprobar en la ejecución general los seis métodos que de otro modo se omiten. Además, un proceso focalizado bloqueó `import scipy` y demostró que el cálculo ideal/no ideal y los imports de `main`/Flask siguen funcionando: de ocho métodos del archivo comparativo, **dos pasaron y seis quedaron omitidos explícitamente**. Un `skip` no equivale a un resultado positivo sobre SciPy.

**Ejecución real del cierre (22/10/2026):** Linux `6.18.55`, Python `3.12.14`, NumPy `2.5.4`, Matplotlib `3.11.2`, Flask `3.1.3`, Jinja2 `3.1.6`, SciPy `1.17.0`. Una **única ejecución** de `python -B -m unittest discover -s tests -q` finalizó **215/215 OK, 0 fallos, 0 omisiones, 0 errores de importación**, en **69.358 s**. No se realizó una ejecución equivalente en Windows ni una inspección visual nueva de gráficos. La evidencia Flask/HTML procede de las pruebas de integración que sí formaron parte de la suite.

### INGENIERÍA — referencias, errores y límites

Se recalcularon desde las funciones del commit de partida `57da73d` un ciclo ideal motor, dos no ideales motores, un dominio no ideal vacío, dos puntos muy cercanos al límite superior y máximos de trabajo/rendimiento. A la entrada no ideal de referencia (`rp=10`) resultaron `w_neto≈369.476301 kJ/kg` y `eta≈0.368987324`; para el ideal `w_neto≈505.619018 kJ/kg` y `eta≈0.482052532`. Una distancia relativa `1e−12` de la frontera superior no ideal deja trabajo algebraico positivo (`2.444267e−10 kJ/kg`), pero **no** rendimiento motor por la banda de viabilidad (`1.608e−7 kJ/kg` para el trabajo en ese caso). Los máximos interiores A y B se recogen por separado; el ideal sólo tiene **supremo no alcanzado** de rendimiento. Parámetros, todas las salidas y unidades aparecen en el [cierre técnico](12_cierre_verificacion_numerica.md), sin duplicar aquí sus tablas.

Las cifras se imprimen con un número finito de decimales; un `float` representa aproximaciones binarias. **Error de raíz, residuo de una ecuación y tolerancia de parada son conceptos distintos**, y comparar números redondeados como si fueran idénticos puede ocultar un margen pequeño. La matriz reúne umbrales realmente utilizados en 1.1–1.5: absolutos cuando la referencia se aproxima a cero, relativos cuando la escala importa y mayores márgenes de posición cuando el máximo es plano. Los mayores errores anteriores **no se transforman en garantías universales** mediante el cierre.

**Lo aprendido:** una suite verde y referencias analíticas/SciPy verifican el comportamiento del **software para el modelo planteado**, no que un motor real respete `cp`, `gamma`, eficiencias y pérdidas constantes. La **validación física** necesitaría mediciones o referencias externas independientes. También quedan por investigar casos casi degenerados, límite de representación y modelos de componentes más realistas. Tras revisión del usuario, la fase **puede proponerse como cerrada en el alcance Linux comprobado**, manteniendo explícita la ausencia de ejecución nativa Windows y sin comenzar aún otra fase ni publicar la Etapa 6.

## 12. Iteración del 23 de octubre de 2026 — diagnóstico científico en los informes

### Base comprobada, alcance y estado de Git

Esta iteración se mantiene dentro de la **fase de verificación**: amplía la explicación de resultados ya calculados, sin introducir un nuevo modelo termodinámico. El informe previo situó los cambios sin commit en Windows y mencionó el documento personal `docs/PLAN_MEJORAS_BRAYTON_SIMULATOR.md`. En esta revisión se ha comprobado **por separado** la rama remota `mejoras/verificacion-numerica` y su commit `12c3dc27397789faa61ad49c7e80faa4e8ef3791`, pero **no se ha accedido al repositorio Windows** ni al documento personal. Los archivos del ZIP se cotejaron con una copia Linux limpia del commit remoto, normalizando finales de línea, antes de reproducir allí los once cambios. El hash es la base, no un commit del panel. No se han creado commits, publicaciones ni otra fase.

Antes existían cálculos, clasificadores físicos y mensajes en `comprobaciones`, más verificaciones históricas V.1–V.5. Faltaba explicar uniformemente, para **cada informe**, los valores contrastados, residuos, unidades, tolerancias y magnitudes no disponibles. La solución incorpora el panel sin sustituir resultados, KPI o gráficas y sin ejecutar V.1–V.5 al generar un informe.

### INGENIERÍA — qué demuestra cada comprobación

Con trabajo específico de compresor consumido positivo y turbina producido positivo,

\[
w_n=w_t-w_c,\qquad q_{out}=\frac{c_p(T_4-T_1)}{1000},\qquad
R_E=(q_{in}-q_{out})-w_n.
\]

Las energías se expresan en **kJ/kg**, mientras `cp` entra en **J/(kg·K)**. El factor 1000 expresa una conversión de unidad, no un ajuste empírico. `qout` reconstruido de las temperaturas permite comprobar la coherencia de los valores guardados; si todas las magnitudes proceden de expresiones algebraicamente equivalentes, un residuo pequeño **no constituye una referencia física independiente**. Los contrastes contra ecuaciones de estado escritas en el diagnóstico son otra implementación del mismo modelo, no mediciones de un motor real.

En el ideal, con `a=(gamma−1)/gamma`, las temperaturas de referencia son `T2=T1·rp**a` y `T4=T3/rp**a`. En el no ideal se usan las presiones reales y las eficiencias: `T2=T1+(T2s−T1)/eta_c`, `T4=T3−eta_t·(T3−T4s)`, con `p3=p2·(1−delta)`. Aplicar la isentrópica ideal a la temperatura real de una máquina no ideal daría una advertencia falsa. El diagnóstico identifica el modelo y no exige una igualdad que no le corresponde.

La viabilidad exige expansión efectiva, aporte de calor y trabajo neto positivos por encima de las bandas numéricas del clasificador. Es posible que un punto no motor conserve la primera ley; la conservación no demuestra que el punto pueda entregar trabajo como motor. Tampoco se inventa un rendimiento operativo cuando falta admisión o el denominador no permite calcularlo.

Para equipos adiabáticos se interpreta `sgen=s_salida−s_entrada`; Gouy–Stodola es `eD=T0·sgen`, con `T0` en K, `sgen` en kJ/(kg·K) y `eD` en kJ/kg. La cámara sólo proporciona un cambio de entropía del fluido: sin caracterizar la transferencia de calor, no se deduce de él su generación. Por ello la suma compresor+turbina sigue siendo **parcial**. Si el informe carece de datos de Segunda Ley se muestra **No evaluable**, con motivo, y no se inventan entropías.

### PYTHON — separar dato, decisión y HTML

`diagnostico.py` crea registros de control; `diagnostico_informe.py` selecciona los resultados existentes de cada modalidad y resume los controles; `diagnostico_html.py` convierte esos registros en HTML. `reporting.py` conecta estas capas y `dashboard.py` conserva el panel entre el informe autónomo y su vista local. Esta separación permite comprobar ecuaciones sin depender del navegador y modificar el diseño sin cambiar la física.

Un **registro uniforme** es un diccionario cuyas claves tienen siempre el mismo significado: identificación, magnitud, resultado/referencia, residuo, tolerancia, unidad, estado y explicación. `None` indica información que no existe o no procede; no debe sustituirse por `0`. Una **agrupación** resume muchos registros equivalentes por comprobación y contexto, conserva cuántos cumplen/advierten/no son evaluables y selecciona un ejemplo útil para estudiar una discrepancia. Así una malla densa no obliga a leer una tabla con miles de filas.

La clasificación `viable` ilustra una distinción importante de tipos: `bool("False")` es `True` en Python porque una cadena no vacía es verdadera; también `bool(None)` y `bool(0)` son `False`. Por ello comparar `float(bool(ciclo["viable"]))` podía declarar **Cumple** sin haber recibido un booleano válido. El diagnóstico actualizado acepta sólo `True`/`False` como dato clasificatorio: con `None` muestra **No evaluable**, y con una cadena o un número registra **Atención**. Se ha añadido una prueba de regresión específica sin alterar el clasificador `evaluar_punto`.

Los argumentos de sólo nombre que siguen a `*` expresan opciones que conviene identificar al llamar. Los generadores y `for` recorren muestras sin recalcularlas. `html.escape` convierte caracteres como `<` en texto seguro. `details`/`summary` permiten abrir la ecuación, la causa y el criterio de tolerancia sin JavaScript adicional. El manual actual [§4.56](../../CODE_WALKTHROUGH.md) contiene las firmas completas, entradas/salidas, llamadas y ejemplos de las funciones nuevas; este documento desarrolla sus novedades sin copiar el resto del simulador.

### Funciones nuevas y relación con el flujo anterior

En esta tabla, `p` es el diccionario de nueve entradas; `ciclo` conserva T [K], p [kPa], energía [kJ/kg] y cocientes adimensionales. `estudio_sl` contiene entropías [kJ/(kg·K)], exergías [kJ/kg] y T0 [K]. Las funciones de apoyo no cambian unidades. Errores estructurales inesperados se propagan para distinguirlos de inviabilidad; los datos ausentes y las ecuaciones inaplicables producen registros no evaluables.

| Firma completa | Argumentos, retorno, propósito, llamadas y ejemplo |
|---|---|
| `diagnosticar_ciclo(parametros, ciclo, modelo="noideal", contexto="Caso actual", segunda_ley=None, T0=None)` | `parametros/ciclo: dict`, `modelo/contexto: str`, Segunda Ley de **un modelo** opcional y T0 opcional [K] → `list[dict]`. Reúne controles de estados, energía, motor y Segunda Ley. Usa comparadores/helpers y bandas guardadas o `evaluar_punto`; lo llaman coordinadores. Modelo desconocido → `ValueError`. Ejemplo: `diagnosticar_ciclo(p,ciclo,modelo='ideal')`. |
| `diagnosticar_optimizacion(parametros, estudio, modelo="noideal", objetivo="trabajo", contexto="")` | Dos diccionarios y tres textos → lista de controles de clasificación/concordancia, sin buscar otro óptimo. Usa `_registro`/`_comparar`/`_finito`; lo llaman coordinador A/B y muestras OFAT/mapa. Modelo/objetivo desconocido → `ValueError`; contraste ausente → no evaluable. Ejemplo: `diagnosticar_optimizacion(p,optimizaciones['noideal'])`. |
| `resumir_diagnosticos(items, alcance, agrupar=False)` | Iterable de registros, texto y booleano → `dict(items,resumen,alcance)`. Copia y cuenta todos los controles; opcionalmente agrupa por `(grupo,id)`. Usa `isfinite`; lo llaman los cuatro coordinadores. Estado desconocido → `KeyError`. Ejemplo: `resumir_diagnosticos([], 'Sin datos')`. |
| `diagnostico_simulacion(parametros, ideal, noideal, segunda_ley=None)` | Diccionarios de entradas/ciclos y Segunda Ley opcional → resumen de ambos modelos. Llama `diagnosticar_ciclo` y `resumir_diagnosticos`; lo llama `crear_informe_html`. Ejemplo: `diagnostico_simulacion(p,ideal,noideal,estudio_sl)`. |
| `diagnostico_optimos(parametros, optimizaciones=None, estudio_rendimiento=None)` | Entradas y estudios A/B opcionales → resumen de óptimos y ciclos candidatos guardados. Llama diagnosticadores de ciclo/óptimo y resumen; lo llama `crear_informe_html`. Copia parámetros para cada rp. Ejemplo: `diagnostico_optimos(p,trabajo,rendimiento)`. |
| `diagnostico_segunda_ley(parametros, estudio)` | Entradas y estudio Segunda Ley → resumen de estados/análisis; las energías no guardadas siguen ausentes. Llama diagnóstico de ciclo y resumen; lo llaman creadores normal/Segunda Ley. Ejemplo: `diagnostico_segunda_ley(p,estudio_sl)`. |
| `diagnostico_estudio(estudio, tipo)` | Estudio `dict` y texto sensibilidad/mapa → resumen agrupado completo, sin submuestrear los controles. Llama el generador local `recorrer()` y resumen; lo llaman creadores OFAT/mapa. Tipo desconocido → `ValueError`. Ejemplo: `diagnostico_estudio(ofat,'sensibilidad')`. |
| `renderizar_diagnostico(diagnostico, clave="actual")` | Resumen `dict` y clave `str` → HTML `str` seguro y con identificadores distintos. Llama helpers locales de texto/número/unidad y `quote`; lo llaman reporting y dashboard. No tiene ecuaciones ni valida física. Ejemplo: `renderizar_diagnostico(resumen,'resultados')`. |

Las funciones internas son `_finito(valor)` (objeto→bool), `_registro(identificador, nombre, grupo, relacion, unidad, explicacion, naturaleza="identidad", **datos)` (textos/campos→registro), `_comparar(identificador, nombre, grupo, relacion, valor, referencia, unidad, explicacion, *, atol=1e-12, rtol=1e-9, escala=None, naturaleza="identidad")` (magnitudes/tolerancias en su unidad→registro de igualdad), `_margen(identificador, nombre, grupo, relacion, valor, limite, unidad, explicacion, *, estricto=True)` (margen/banda→registro de desigualdad) y `_diagnosticar_segunda_ley(grupo, estudio, T0, cp, gamma, ciclo)` (datos de un modelo→lista de controles de entropía/exergía). Los diagnosticadores llaman estos apoyos; la última sólo se llama desde `diagnosticar_ciclo`. Sus validaciones, errores y ejemplos detallados están en el contrato del motor de §4.56.

`_items_muestra(muestra, escenarios, ubicacion)` recibe diccionario, letras R/A/B y texto, y **produce** controles mediante `yield`; lo llama `recorrer()`, función local sin argumentos que captura el estudio/tipo y se consume en `resumir_diagnosticos`. Llama a los diagnosticadores y no resuelve otro ciclo. Ejemplo: `list(_items_muestra(muestra,'AB','T3=1600 K'))`. Una clave de escenario incorrecta propaga `KeyError`. Los apoyos locales `texto(valor)`, `numero(valor)` y `magnitud(valor, unidad)` devuelven cadenas escapadas dentro de `renderizar_diagnostico`; `numero`/`magnitud` usan `texto`, y `magnitud` usa `numero`. Sus ejemplos y tratamiento de `None`/no finitos se explican en el mismo contrato HTML del manual.

Antes, `terminar_informe` sólo organizaba resultados/KPI; ahora añade `diagnosticos=None` como opción por nombre, conserva los registros en metadata y llama al presentador para cada panel. Los cuatro creadores públicos de informes mantienen sus firmas: añaden las llamadas de diagnóstico antes de guardar. El historial recupera ese HTML sin llamar al motor de diagnóstico. Por ello estudiar o descargar un informe no altera el resultado que se calculó originalmente.

### Experimentos de aprendizaje y límites conservados

1. Genera el caso predeterminado y compara el balance de trabajo con el de calor. Identifica cuáles utilizan las mismas temperaturas y por qué no son experimentos independientes.
2. Compara ideal/no ideal: conserva T1, T3, cp y rp, pero interpreta las eficiencias y la pérdida de presión con su ecuación correspondiente. Explica qué unidad tiene cada residuo.
3. En una prueba aislada, altera una energía del diccionario resultante y observa una advertencia; no cambies las ecuaciones de producción para fabricar el caso.
4. Consulta un informe sólo de Segunda Ley. Explica por qué disponer de temperaturas y entropías no equivale a disponer del balance energético guardado.
5. Abre un informe anterior desde el historial y descarga uno actual. La consulta debe conservar el diagnóstico guardado, sin ejecutar el modelo de nuevo.

Son prácticas propuestas, **no una afirmación de que el lector ya las haya ejecutado**. La evidencia ejecutada en esta tarea se identifica separadamente en el [milestone 18](18_diagnostico_fisico.md). En el momento de aquella revisión permanecía la limitación V.5: la reutilización no inspeccionaba la semántica de un bloque `segunda_ley` de JSON manipulado. El panel por sí solo no corrigió ese comportamiento, abordado posteriormente en §13. Tampoco constituye validación experimental ni cambia `cp`, `gamma`, las hipótesis de equipos o los optimizadores.

### Evidencia inicial y resultado de la revisión del 23/10/2026

En la sesión inicial constaban **19/19 métodos físicos** correctos; integración **9/10** por una expectativa sobre `rp=1`, rechazado por el formulario. Se cambió aquel escenario a `T3=400 K` sin modificar producción, pero aún no constaba la nueva ejecución. En esta revisión **el caso focalizado ha pasado**.

Sobre la copia independiente se ejecutaron **20/20 pruebas físicas**, **11/11 de integración del diagnóstico**, **101/101 regresiones de reporting/dashboard/Flask/Segunda Ley/sensibilidad/mapa** y **12/12 pruebas de contratos web V.5**: **144 métodos distintos correctos**. Se añadieron dos pruebas: una detecta la coerción indebida de `viable` y otra comprueba en el HTML autónomo identificadores, referencias de accesibilidad, pares `details` y presencia de CSS adaptativo. Una primera invocación de las regresiones carecía de `tests` en `PYTHONPATH`: dio cuatro errores de importación del ejecutor, corregidos al repetir esos 101 métodos. No hay resultado documental de la suite general iniciada en la sesión anterior y **no se ha ejecutado la suite completa** en esta revisión.

La sesión anterior pudo arrancar Flask, pero el navegador no conectó. Esta revisión ha contrastado las respuestas HTTP de generación, historial y descarga con el cliente Flask, además de la estructura HTML y las reglas CSS. **No se han visto ni accionado manualmente el panel en escritorio/móvil**; falta esa comprobación visual antes de dar el acabado por definitivamente cerrado. La copia no es el repositorio Windows: trasladar las correcciones allí exige comparar los archivos reales, sin sobrescribir los cambios pendientes. El [milestone técnico 18](18_diagnostico_fisico.md) conserva el desglose de verificaciones, limitaciones y estado sin commit.

## 13. Iteración del 23 de octubre de 2026 — integridad de estudios JSON de V.5

### PYTHON — tres niveles de comprobación

**Forma:** `isinstance(estudio, dict)` y comprobar que están presentes dos
modelos, cuatro temperaturas, cuatro presiones, cuatro entropías y dos
componentes. Es distinto de comprobar sólo que un texto es JSON válido:
`{"modelos": {}}` es JSON válido, pero no describe nuestro estudio.

**Tipo y dominio:** `type(x) in (int, float)` excluye `True`, aunque en Python
`isinstance(True, int)` sea verdadero. `math.isfinite` excluye NaN e infinitos.
Para una temperatura se exige además `x > 0` [K]. Un dato opcional ausente
puede ser legítimo en otros contextos; un estado necesario para reutilizar
Segunda Ley no lo es.

**Coherencia numérica:** a diferencia de la forma, compara números y
ecuaciones. `math.isclose(x, referencia, rel_tol=1e-9, abs_tol=...)`
permite redondeo de coma flotante, no desviaciones arbitrarias. La validación
contrasta T/p con los nueve parámetros de entrada, calcula las entropías
relativas del gas perfecto y reconstruye generaciones adiabáticas y
`eD=T0·sgen` guardadas. El piso `abs_tol=1e-10` se limita a las magnitudes
entrópicas y derivadas; para T/p se emplea comparación relativa. Las bandas
de admisión del punto motor y de generación de entropía son independientes
de esa tolerancia informática.

### Flujo seguro y ejemplo

```python
anterior = estudio_conservado(nombre, parametros)
# Un JSON inválido produce None; el HTML histórico no cambia.
ejecutar_segunda_ley(carpeta, parametros, 300.0, anterior)
```

`web_app.estudio_conservado(nombre, parametros)` compara la ruta y las entradas,
luego llama a `segunda_ley.validar_estudio_reutilizable(estudio, parametros)`.
Esta función devuelve un `bool`, nunca repara o reescribe el estudio:
comprueba listas, diccionarios, números y balances, capturando errores
esperables del dato conservado. `ejecutar_segunda_ley` repite la barrera para
llamadas directas. Sólo un estudio válido pasa a `actualizar_T0`, que
conserva estados y entropías usando `deepcopy` y cambia las eD.

Para los metadatos externos dañados, `dashboard.separar_presentacion` devuelve
`None`: el historial muestra que no pueden recuperarse estructuradamente y
la vista devuelve HTTP 422, ofreciendo descargar el HTML original sin
modificarlo. El HTML antiguo sin bloque de metadatos sigue abriéndose como
antes. La consulta de un estudio de Segunda Ley internamente inconsistente
lleva una advertencia y no habilita su reutilización física.

**Funciones nuevas y modificadas:**

- `validar_estudio_reutilizable(estudio, parametros) -> bool`: nuevo control
  sin unidades de retorno; consume T [K], p [kPa], s [kJ/(kg·K)] y eD
  [kJ/kg]. Usa `isclose`, `cambio_entropia`, `generacion_adiabatica` y
  constantes de clasificación; lo llaman Flask y el ejecutor. Retorna
  `False` para errores de forma, tipos o incoherencias, no lanza una excepción
  física por un simple JSON roto. Ejemplo: `validar_estudio_reutilizable(e,p)`.
- `web_app.estudio_conservado(nombre, parametros) -> dict | None`: mismo
  contrato externo, ahora valida el estudio antes de devolverlo. El
  ejecutor también descarta estudios no confiables, recalculando desde
  los nueve parámetros válidos. `dashboard.separar_presentacion(contenido)`
  mantiene su firma y añade validaciones del contenedor necesario para
  reconstruir la vista.
- `web_app.listar_informes() -> list[dict]` y
  `web_app.ver_informe(nombre) -> Response`: gestionan metadatos inválidos
  sin sobrescribir ni interpretar como motor/no motor; la descarga del archivo
  completo sigue siendo exacta.

### Evidencia y límites

Base de esta iteración: `d6b3741d6c5834e5657e35a3deac4c0cfd036728`
en `mejoras/verificacion-numerica`, copia independiente, **sin commit**.
Se ejecutaron **12/12 métodos focalizados** de `test_integridad_json_v5.py`
con Flask y dependencias del proyecto instaladas, con autorización, sólo
en un entorno temporal. Se ejecutaron además **78/78 regresiones relacionadas**
de integración web, Segunda Ley, Flask, dashboard, reporting e integración del
diagnóstico: **90/90 pruebas distintas correctas**. Un primer intento con
un intérprete sin Flask falló al importar, antes de ejecutar los métodos;
no era un fallo del código. Previamente se habían pasado siete comprobaciones
numéricas aisladas usando un sustituto de `viabilidad`; no se cuentan de nuevo
como pruebas `unittest`. No se ha repetido la batería anterior de 144 pruebas.

La validez interna no demuestra autenticidad criptográfica ni concordancia
experimental. Un atacante capaz de alterar de forma matemáticamente coherente
todos los campos podría eludir estas comprobaciones; sin firma o hash de
confianza externo no se puede afirmar que un archivo no fue modificado.
Los estudios clasificados como límites numéricos o inconsistencias sin estados
completos se recalculan en vez de reutilizar una estructura no verificable.
La suite general completa y una auditoría de ficheros hostiles arbitrarios
siguen fuera de alcance. La publicación exige todavía revisión y autorización
explícita del usuario; aquí no se creó ningún commit.
