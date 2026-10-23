# V.2 — Verificación independiente del Mapa de Diseño `rp–T3`

**Preparada el 22/10/2026 para revisión; sin commit ni publicación.** Repositorio `cferper/Brayton_simutalor`, rama `mejoras/verificacion-numerica`, commit remoto de partida verificado `8d767b69858c4a3a055c11bbba3294124770d743` (V.1 de Sensibilidad ya publicada). El análisis se realizó en una copia temporal independiente. **No cambia** `mapa_diseno.py`, la termodinámica, las reglas de viabilidad, los optimizadores, las gráficas de producción ni Flask.

## 1. Alcance, supuestos y unidades

El modelo existente describe gas perfecto con `cp` y `gamma` constantes, eficiencias isentrópicas prescritas, componentes adiabáticos y pérdida de presión relativa `delta` en el combustor. Un mapa mantiene fijos `T1`, `gamma`, `cp`, `p1`, `eta_c`, `eta_t` y `delta`, y evalúa filas de `T3` [K] y columnas de `rp` [adimensional]. `cp` se introduce en J/(kg·K); trabajo y calor se expresan en kJ/kg; `eta` es una **fracción** en los cálculos físicos y **porcentaje** en la matriz del mapa.

El oráculo `referencia_termodinamica` de `tests/test_verificacion_mapa_diseno.py` se reconstruyó algebraicamente **sin llamar** a `mapa_diseno`, `evaluar_punto`, `calcular_dominios` ni optimizadores para obtener sus valores esperados:

\[
a=\frac{\gamma-1}{\gamma},\quad r_e=r_p(1-\delta),\quad k=\frac{c_p}{1000},
\]
\[
T_2=T_1\left[1+\frac{r_p^a-1}{\eta_c}\right],\quad
T_4=T_3\left[1-\eta_t(1-r_e^{-a})\right],
\]
\[
w_c=k(T_2-T_1),\quad w_t=k(T_3-T_4),\quad
W=w_t-w_c,\quad Q_{in}=k(T_3-T_2).
\]

`eta=W/Qin` se considera **rendimiento motor** exclusivamente cuando la compresión, la expansión efectiva, el calor y el trabajo superan las condiciones de admisión. El oráculo comprueba tanto los cuatro signos estrictos como una banda de aceptación `1e-10` de esta versión, reconstruyendo sus márgenes y escalas en el archivo de pruebas. **Interior matemático** no equivale necesariamente a **celda aceptada**. Los valores negativos de `W` y `Qin` se conservan, no se sustituyen por cero; si un punto no es motor, su `eta` operativa es `None` y la matriz de rendimiento contiene `NaN`.

### Parámetros estudiados

| Perfil | `T1` K | `gamma` | `cp` J/(kg·K) | `p1` kPa | `eta_c` | `eta_t` | `delta` |
|---|---:|---:|---:|---:|---:|---:|---:|
| N1, predeterminado | 288.15 | 1.4 | 1005 | 100 | .85 | .90 | .05 |
| N2, adverso para dominio | 300 | 1.4 | 1005 | 100 | .60 | .70 | .20 |
| N3, contraste A | 300 | 1.4 | 1005 | 100 | .90 | .94 | .03 |
| Reversible | 288.15 | 1.4 | 1005 | 100 | 1 | 1 | 0 |

Se utilizaron también las dos variaciones **aisladas** `cp×1.7` y `p1×3.2` del perfil N1. No se alteró ningún valor predeterminado del programa.

## 2. Resultados independientes de celdas y máscaras

La siguiente muestra procede de una **ejecución real** con N1 y malla logarítmica `rp=(1,10,100)`, `T3=(400,1000,1600)`; se recogen celdas ilustrativas de las nueve. `T1` se mantiene en 288.15 K; `T3` es la temperatura de la fila. Se muestran cifras redondeadas para leerlas, no para exigir identidad de decimales.

| `T3` K | `rp` | `T2` K | `T4` K | `W` kJ/kg | `Qin` kJ/kg | `eta` motor % | Estado |
|---:|---:|---:|---:|---:|---:|---:|---|
| 400 | 1 | 288.150000 | 405.314731 | −5.341305 | 112.409250 | — | Compresión, expansión y trabajo excluidos |
| 400 | 10 | 603.656530 | 229.213840 | −145.443972 | −204.674813 | — | Calor y trabajo no positivos |
| 400 | 100 | 1212.804271 | 138.002829 | −665.970386 | −816.868293 | — | Calor y trabajo no positivos |
| 1000 | 10 | 603.656530 | 573.034600 | 112.016165 | 398.325187 | 28.121788 | Motor |
| 1600 | 10 | 603.656530 | 916.855359 | 369.476301 | 1001.325187 | 36.898732 | Motor |
| 1600 | 100 | 1212.804271 | 552.011317 | 123.951084 | 389.131707 | 31.853247 | Motor |

**Errores realmente medidos** en once celdas seleccionadas de otra malla N1, `rp=.8–100` lineal con 9 columnas y `T3=400–1600 K` con 5 filas:

| Magnitud | Mayor error absoluto | Mayor error relativo definido | Localización del mayor absoluto |
|---|---:|---:|---|
| Temperaturas `T1–T4` | `2.274e-13 K` | `2.060e-16` | Fila `T3=1600`, columna 8 |
| `wc`, `wt`, `W`, `Qin` | `4.547e-13 kJ/kg` | `1.258e-15` | `wt`, fila `T3=1600`, columna 8 |
| `eta` fraccionaria, sólo motor | `4.996e-16` | `1.568e-15` | Fila `T3=1600`, columna 8 |

El máximo del error relativo puede ocurrir en una magnitud/celda distinta del máximo absoluto: no se convierte un resultado en garantía general de precisión. En el caso ensayado, **los motivos de exclusión coincidieron**; todas las celdas tenían valores representables y ninguna fue `limite_numerico`.

La orientación comprobada es `matriz[i,j] ↔ (T3[i],rp[j])`, nunca al revés. `preparar_resultados` aplica `mask=~viable` sólo a las prestaciones motoras; el valor calculado con signo permanece en la matriz base. La máscara `limite_numerico` es separada de la inviabilidad física.

## 3. Fronteras analíticas: derivación y mediciones

La referencia `fronteras_cerradas` usa:

\[
x=r_p^a,\quad \theta=T_3/T_1,\quad h=\theta\eta_c\eta_t,
\quad b=(1-\delta)^{-a},
\]
\[
Q(x)=(x-1)(x-h)+h(b-1),\quad
D=(h-1)^2-4h(b-1).
\]

La identidad

\[
W=-\frac{kT_1}{\eta_c x}Q(x)
\]

demuestra que, para parámetros físicos positivos, **`W>0` equivale a `Q(x)<0`**. Si `D>0`, las raíces matemáticas son `x±=(1+h±sqrt(D))/2` y las relaciones de presiones respectivas son `x±^(1/a)`. Hay que intersectar su intervalo abierto con `rp>1`, `rp>1/(1−delta)` y `rp<(1+eta_c(theta−1))^(1/a)`; `D>0` por sí solo **no garantiza motor**.

| Perfil | `T3` K | Discriminante `D` | Intervalo motor abierto independiente `rp` |
|---|---:|---:|---|
| N1 | 400 | −0.0588733 | Vacío |
| N1 | 700 | 0.6271190 | (1.121289960, 8.213938380) |
| N1 | 1000 | 2.5818089 | (1.086673679, 29.534327499) |
| N1 | 1300 | 5.8051964 | (1.075320485, 74.763572895) |
| N1 | 1600 | 10.2972816 | (1.069654102, 155.454326039) |
| N2 | 400 | 0.0461373 | Vacío: no hay intersección física |
| N2 | 700 | −0.2576597 | Vacío |
| N2 | 1000 | −0.2086567 | Vacío |
| N2 | 1300 | 0.1931463 | (1.839686543, 5.526065642) |
| N2 | 1600 | 0.9477492 | (1.549258409, 13.572323892) |

En las **10 filas** el carácter vacío/no vacío coincidió con el mapa. Mayor discrepancia absoluta entre los extremos numéricos de dominio y la referencia cerrada: **`3.359e-11 rp`**, en el límite superior N1 a 1600 K (error relativo aproximadamente `2.16e-13`). Se comprobaron además las dos raíces de trabajo incluso cuando no existía intersección motora, puntos dentro/fuera y el signo de `Q(x)` frente a `W`. Se eligieron raíces moderadas; el resultado no abarca casi dobles ni discriminantes extremos.

### Banda numérica en una frontera matemáticamente abierta

En N1, `T3=1600 K`, se tomaron distancias relativas interiores `1e-6` y `1e-12` desde ambos extremos de `rp`:

| Lado y distancia | `W` kJ/kg | `Qin` kJ/kg | Banda `tol(W)` kJ/kg | Motor admitido |
|---|---:|---:|---:|---|
| Inferior `1e-6` | `3.123624e-4` | 1311.791177 | `1.608e-7` | Sí |
| Inferior `1e-12` | `3.121450e-10` | 1311.791277 | `1.608e-7` | No, banda de trabajo |
| Superior `1e-12` | `3.119567e-10` | 218.522223 | `1.608e-7` | No, banda de trabajo |
| Superior `1e-6` | `3.123627e-4` | 218.522635 | `1.608e-7` | Sí |

Las dos celdas matemáticamente interiores pero excluidas conservan `W` y `Qin` calculables; **no publican rendimiento de motor**. No se clasificaron como errores de representación. La prueba preexistente `test_limites_numericos_distintos_de_inviabilidad` ejercita, por inyección explícita de `ErrorNumerico`, el camino distinto de límite numérico; no se afirma haber encontrado un límite real de representación en estas mallas moderadas.

## 4. Trayectorias continuas A y B

**A:** la posición analítica independiente procede de anular la derivada del trabajo:

\[
r_{p,A}^{a}=\sqrt{\eta_c\eta_t\frac{T_3}{T_1}(1-\delta)^{-a}}.
\]

Se comparó para cinco temperaturas entre 700 y 1700 K, en N1 y N3 (10 filas), exigiendo pertenencia al intervalo abierto, admisibilidad y trabajo superior al de vecinos a `0.92·rp_A` y `1.08·rp_A`. El máximo error absoluto observado fue **`2.132e-14 rp`** y **`2.842e-13 kJ/kg`** en trabajo, ambos en N1 a 1700 K (`rp_A≈14.338335212`, `W_A≈420.121932455 kJ/kg`). Los máximos no se obtienen seleccionando un píxel de la malla.

**B:** el único ensayo que requiere SciPy lo importa dentro de su método de prueba; `minimize_scalar(method='bounded')` maximiza la fracción `W/Qin` en `log(rp)` con **valores recalculados por la referencia independiente**. No emplea `calcular_candidato_rendimiento` ni el optimizador del programa para elegir la solución. Se comprobaron cuatro filas N1:

| `T3` K | `rp_B` mapa | `rp_B` SciPy | `|Δrp|` | `eta_B` fracción | `|Δeta|` |
|---:|---:|---:|---:|---:|---:|
| 900 | 7.637568173 | 7.637568171 | `2.511e-9` | 0.241240339449 | `5.551e-17` |
| 1200 | 16.418778047 | 16.418778043 | `4.242e-9` | 0.346706606958 | `6.661e-16` |
| 1500 | 29.831956812 | 29.831955842 | `9.701e-7` | 0.419471596160 | `2.220e-16` |
| 1800 | 48.553069289 | 48.553066586 | `2.703e-6` | 0.472615202263 | `1.110e-16` |

SciPy finalizó con éxito en las cuatro filas, **11 evaluaciones por fila**. Máximo error relativo observado en `rp_B`: aproximadamente `5.57e-8` (1800 K). Cerca de un máximo plano, dos posiciones pueden producir rendimientos casi idénticos; no se exige igualdad exacta en `rp`. B superó o igualó el rendimiento evaluado en A.

El ensayo reversible (`eta_c=eta_t=1`, `delta=0`) conservó en todas sus filas `B.estado='supremo_no_alcanzado'`, con `eta_sup=1−T1/T3`, **sin `rp_B` finita**. Los máximos A del reversible y ambos A/B no ideales ensayados quedaron fuera de ventanas visuales estrechas (`rp≤4` o `rp≤3`) **sin ser recortados ni convertidos en máximos de borde**.

## 5. Tamaño de malla y representación

Dos mallas geométricas/logarítmicas anidadas sobre N1, `rp=1.05–100`, `T3=700–1700 K`, se contrastaron con nodos compartidos:

| Malla `(n_rp×n_T3)` | Celdas | Celdas motoras | Valores compartidos | Óptimos continuos |
|---|---:|---:|---|---|
| 7×3 | 21 | 13 | Referencia gruesa | A/B calculados por fila |
| 13×5 | 65 | 47 | Mismos valores en índices pares | A/B idénticos en filas compartidas |

Los errores **del mejor valor muestreado** frente al máximo continuo calculado por el mapa fueron:

| `T3` K | `W_A − W_malla` gruesa, kJ/kg | Fina, kJ/kg | `eta_B − eta_malla` gruesa, puntos % | Fina, puntos % |
|---:|---:|---:|---:|---:|
| 700 | 3.484797 | 0.230763 | 0.576193 | 0.461691 |
| 1200 | 3.744677 | 0.563167 | 0.772229 | 0.065580 |
| 1700 | 6.722914 | 0.113882 | 0.079552 | 0.079552 |

Como la malla fina **contiene** todos los nodos de la gruesa, el mejor valor admisible muestreado no empeoró. En 1700 K, el mejor rendimiento muestreado conservó el mismo valor; **no se exigió mejora estricta**. Para cada fila, el mejor valor discreto se mantuvo por debajo del continuo dentro de la tolerancia. Si las mallas no comparten nodos, esta monotonía no está garantizada. Más columnas mejoran la representación, **no trasladan** el óptimo analítico.

Se interceptaron las llamadas reales a `Axes.pcolormesh` de los tres mapas producidos (`shading='nearest'`): ejes `rp` logarítmico, `T3` lineal, valores y máscaras exactamente correspondientes a las matrices calculadas. Las líneas A/B fuera de la ventana gráfica se pasaron con posiciones `NaN` **sin cambiar** las `rp` almacenadas. Los cortes a 1700 K coincidieron con las ecuaciones independientes aun sin ser una fila existente. La figura de viabilidad combina visualmente no motor y límite numérico en gris, pero los datos y contadores siguen distinguiéndolos. Se verificaron etiquetas `rp [−]` y `T3 [K]`; las pruebas anteriores ya verifican PNG, informes e integración Flask. Esto **no** equivale a una revisión visual exhaustiva de todas las imágenes o de todos los tamaños de pantalla.

## 6. Invariantes físicos y criterios de aceptación

En mapas N1 de 5 columnas × 3 filas se modificó **un parámetro físico cada vez**. Multiplicar `cp` por `1.7` multiplicó `W` y `Qin` por `1.7`, conservando rendimiento/máscara; multiplicar `p1` por `3.2` conservó prestaciones específicas y admisión dentro del redondeo. Para `rp` fija con expansión efectiva, aumentar `T3` en 600 K produjo `ΔW=k eta_t[1−(rp(1−delta))^(−a)]·600`, y se cumplió `W=wt−wc` en todas las celdas revisadas. La presión absoluta no influye en prestaciones específicas de **este modelo**; no debe extrapolarse a turbomáquinas reales.

| Propiedad | Criterio utilizado en los 9 métodos nuevos | Resultado |
|---|---|---|
| Estados y energía por celda | `|ΔT|≤1e-9 K`; `|Δenergía|≤2e-10 kJ/kg` | Correcto |
| Rendimiento y exclusión | `|Δeta|≤2e-10` fracción; sólo en celda motor; `NaN` si no lo es | Correcto |
| Fronteras analíticas | `|Δrp|≤3e-9·max(1,rp)`; dominio vacío comprobado | Correcto |
| Banda abierta | Signos estrictos, márgenes, tolerancias y estados separados | Correcto |
| A interior | `|Δrp_A|≤2e-9·rp_A`; `|ΔW_A|≤2e-10 kJ/kg` | Correcto |
| B interior con SciPy opcional | `|Δrp_B|≤3e-5·rp_B`; `|Δeta_B|≤3e-9` fracción; `success`, dominio abierto y viabilidad | Correcto (SciPy disponible) |
| Mallas anidadas | Valores compartidos `rtol≤3e-14`, `atol≤2e-11`; mejor muestreo no decreciente con holgura `1e-9` | Correcto |
| Escalados y primera ley | Energías `atol≤3e-10 kJ/kg`, `rtol≤3e-14`; balance `≤1e-11 kJ/kg` | Correcto |
| Datos dibujados | Tres mapas sin interpolación de contornos, máscaras y trayectorias fuera de vista | Correcto |

Estos umbrales se establecen a partir de las escalas del modelo, contratos y precisión de doble coma flotante; **no se infieren como cotas universales** de los errores observados ni se amplían para encubrir fallos. La tolerancia de posición B es deliberadamente más laxa que la de valor por el carácter plano de ese objetivo.

## 7. Pruebas reproducibles y resultado real

Entorno usado: **Linux**, Python **3.12.14**, NumPy **2.5.4**, Matplotlib **3.11.2**, Flask **3.1.3**, Jinja2 **3.1.6** y SciPy opcional **1.17.0**. El intérprete estaba en `/tmp/brayton_etapa_6_venv/bin/python`, fuera del repositorio, con las dependencias declaradas en `requirements.txt`. No se modificaron dependencias.

Desde la raíz del proyecto, usando el Python del entorno aislado:

```bash
MPLCONFIGDIR=/tmp/brayton_v2_mpl /tmp/brayton_etapa_6_venv/bin/python -B -m unittest discover -s tests -p test_verificacion_mapa_diseno.py -v
MPLCONFIGDIR=/tmp/brayton_v2_mpl /tmp/brayton_etapa_6_venv/bin/python -B -m unittest discover -s tests -p test_mapa_diseno.py -v
```

En Windows PowerShell se puede sustituir el intérprete, si se dispone de `.venv` instalado, por `.\.venv\Scripts\python.exe` y definir previamente `$env:MPLCONFIGDIR = Join-Path $env:TEMP 'brayton_mapa_mpl'`. **No se ha ejecutado V.2 en Windows**.

| Grupo | Métodos | Correctas | Fallos | Omisiones |
|---|---:|---:|---:|---:|
| `test_verificacion_mapa_diseno.py`, nuevos | 9 | 9 | 0 | 0 |
| `test_mapa_diseno.py`, regresiones existentes | 21 | 21 | 0 | 0 |
| **Total de esta intervención** | **30** | **30** | **0** | **0** |

Primera ejecución de las nuevas pruebas: `9/9` en **1.334 s**; tras ampliar las aserciones de raíces/trazas gráficas, **9/9** en **1.522 s**; tras añadir explícitamente ausencia de máximos A/B en filas vacías, **9/9** en **1.914 s**. Las 21 regresiones existentes: **21/21 en 3.049 s**. Son métodos distintos; las repeticiones focalizadas de las nueve pruebas tras cambiar las aserciones **no se suman** al total de 30. No se ha ejecutado de nuevo la suite completa histórica de 215 pruebas. Si no se instala SciPy, el método de B se omite expresamente y no puede contarse como correcto, aunque la simulación normal no lo requiera.

## 8. Aprendizaje, limitaciones y estado de Git

**MATEMÁTICAS / INGENIERÍA.** El mapa es una muestra finita de ecuaciones continuas. Las fronteras se calculan a partir de condiciones físicas **abiertas** y no se desplazan a bordes de píxel. La discriminante indica dos raíces de trabajo, pero sólo su intersección con expansión y calor positivo determina el dominio. Una curva A/B representa una optimización por temperatura, **no** el máximo de la imagen. Los máximos de rendimiento pueden ser planos y sus posiciones menos estables que el valor del objetivo. La banda de redondeo excluye puntos casi fronterizos aunque matemáticamente sean interiores.

**PYTHON.** Un helper puro para estados y otro para raíces separan las referencias del código comprobado. La indexación `[i,j]` conserva fila y columna; `np.ma` oculta visualmente celdas sin borrar su contenido, mientras `NaN` significa ausencia de rendimiento motor. `unittest.subTest` etiqueta escenarios, `patch.object` observa datos que realmente recibe Matplotlib y `skipUnless` mantiene opcional SciPy. Ninguno de estos helpers pertenece a producción.

**Alcance confirmado:** coherencia algebraica del mapa, signos, dominios y máscaras, trayectorias A/B, mallas anidadas moderadas, escalados, primera ley y datos de representación. **Queda fuera:** validación experimental, propiedades variables, eficiencia dependiente del punto de operación, casi raíces dobles, límites extremos de representación, grandes costes de malla, inspección visual exhaustiva o ejecución nativa Windows. La comparación B con SciPy sigue siendo numérica y no una validación física independiente del modelo. No se han encontrado discrepancias de producción en los casos ensayados.

**Estado:** cambios sin commit, sólo `tests/test_verificacion_mapa_diseno.py`, este documento 14 y `CODE_WALKTHROUGH.md` en la copia temporal `brayton_v2_mapa_diseno/`; rama local `mejoras/verificacion-numerica` sobre el commit publicado `8d767b69858c4a3a055c11bbba3294124770d743`. Se requiere revisión y autorización explícita antes de publicar.
