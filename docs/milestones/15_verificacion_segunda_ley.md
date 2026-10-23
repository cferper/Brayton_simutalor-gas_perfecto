# V.3 — Verificación independiente de Segunda Ley y Exergía

**Estado:** preparada para revisión, sin commit ni publicación. **Base remota comprobada:** `d6f9dc9d9ebd14b3de991623cb9d5653195ed4e9`, rama `mejoras/verificacion-numerica`, 22/10/2026. `main` remoto observado en `27d4519094d5eb74f5009a1889a1e74dc8dddb94`. Copia temporal independiente. El programa de producción, los modelos físicos, Flask, las dependencias y la interfaz no se han modificado.

## 1. Objetivo, alcance y distinción científica

Se examina si `segunda_ley.py` **implementa correctamente las ecuaciones que declara** para el gas ideal con `cp` y `gamma` constantes. Es **verificación de software** mediante un oráculo decimal de las diferencias de entropía, fórmulas analíticas de componentes y un balance alternativo de exergía. **No es validación física experimental:** no se comparan datos de turbomáquinas reales, propiedades variables, combustión ni pérdidas de un motor completo.

El archivo nuevo `tests/test_verificacion_segunda_ley.py` contiene **9 pruebas**. Se mantienen, sin modificar, los 18 métodos de `tests/test_segunda_ley.py` y se seleccionan 4 regresiones de estados, primera ley, irreversibilidades y no motores. No se ejecuta la suite completa ni se altera su recuento histórico de 215 pruebas en el cierre de la nueva Fase 1.

## 2. Ecuaciones y oráculos verdaderamente independientes

Con temperaturas positivas `T>0` en K, presiones positivas `p>0` en una unidad común (aquí kPa), `cp` en J/(kg·K) y `gamma>1`:

\[
R=c_p\frac{\gamma-1}{\gamma},\qquad
\Delta s_{i\to j}=\frac{c_p}{1000}\ln\frac{T_j}{T_i}
-\frac{R}{1000}\ln\frac{p_j}{p_i}
\quad\left[\frac{\mathrm{kJ}}{\mathrm{kg\,K}}\right].
\]

La primera referencia usa `decimal.Decimal` con 70 cifras de precisión, incluido el logaritmo natural, para formar por separado el término térmico y de presión sin llamar a `segunda_ley.cambio_entropia`. Los cálculos del simulador permanecen en `float`; el oráculo también recibe los valores binarios de estado, convertidos a su representación decimal de entrada mediante `str`. Es una comprobación independiente de fórmulas y aritmética, **no** una medida de incertidumbre experimental.

Un segundo oráculo reconstruye los cuatro estados sin llamar a `viabilidad`:

\[
a=\frac{\gamma-1}{\gamma},\quad p_2=p_1r_p,\quad
p_3=p_1r_p(1-\delta),\quad p_4=p_1,\\
T_2=T_1\left[1+\frac{r_p^a-1}{\eta_c}\right],\quad
T_4=T_3\left[1-\eta_t\left(1-[r_p(1-\delta)]^{-a}\right)\right].
\]

Se verifica `s1=0` como **referencia relativa**, el signo y la magnitud de `s2,s3,s4` y cada identidad telescópica `s[j]-s[i]=Δs(i→j)`. En adiabáticos estacionarios:

\[
s_{\mathrm{gen},c}=s_2-s_1,\quad
s_{\mathrm{gen},t}=s_4-s_3,\quad
e_{D,c}=T_0s_{\mathrm{gen},c},\quad
e_{D,t}=T_0s_{\mathrm{gen},t}.
\]

Además se contrastan las fórmulas cerradas, sin utilizar resultados del módulo:

\[
s_{\mathrm{gen},c}=\frac{c_p}{1000}\ln\left(\frac{1+(r_p^a-1)/\eta_c}{r_p^a}\right),\quad
s_{\mathrm{gen},t}=\frac{c_p}{1000}\ln\left(\left[1-\eta_t\left(1-r_e^{-a}\right)\right]r_e^a\right),\quad r_e=r_p(1-\delta).
\]

La tercera vía es el **balance independiente de exergía de flujo** para equipos adiabáticos, con `ψ=h−T0·s` (las constantes arbitrarias se cancelan), `Δh=cp·ΔT/1000` en kJ/kg:

- Compresor: `eD,c = wc − (ψ2−ψ1)`.
- Turbina: `eD,t = (ψ3−ψ4) − wt`.
- Se contrasta `eD,c+eD,t` con `suma_componentes`, **sólo una suma parcial**, nunca la destrucción total de la instalación.

En la cámara, `s3−s2=cp/1000·ln(T3/T2)−R/1000·ln(p3/p2)`. El término de presión es cero cuando `delta=0` y positivo para `delta>0`; **no** se identifica `s3−s2` con generación de entropía de la cámara. Faltan los intercambios de entropía mediante calor y/o el modelo de combustión.

## 3. Entradas y resultados medidos

Parámetros comunes salvo variación indicada: `cp=1005 J/(kg·K)`, `p1=100 kPa`, `T0=288.15 K`. `rp`, `eta_c`, `eta_t`, `delta` y `gamma` son adimensionales. Todos los valores de esta tabla se **recalcularon** sobre la versión indicada mediante la ejecución de `evaluar_punto`/`analizar_estados` y se contrastaron con los oráculos; no se copiaron de registros anteriores.

| Caso | T1; T3 [K] | rp; gamma | eta_c; eta_t; delta | Viabilidad |
|---|---|---|---|---|
| Base no ideal | 288.15; 1600 | 10; 1.4 | .85; .90; .05 | Motor |
| B, distintas eficiencias | 305; 1450 | 6; 1.32 | .72; .96; .12 | Motor |
| C, turbina más irreversible | 288.15; 2200 | 22; 1.52 | .93; .78; 0 | Motor |
| Diagnóstico no motor | 288.15; 400 | 50; 1.4 | .85; .90; .05 | No motor: calor y trabajo neto no positivos |
| Ideal reversible | 288.15; 1600 | 10; 1.4 | 1; 1; 0 | Motor |

| Caso | T1, T2, T3, T4 [K], redondeadas a .001 | s1, s2, s3, s4 [kJ/(kg·K)], redondeadas a .000001 |
|---|---|---|
| Base no ideal | 288.150; 603.657; 1600.000; 916.855 | 0; .082051; 1.076407; 1.163256 |
| B | 305.000; 535.438; 1450.000; 987.941 | 0; .129049; 1.161409; 1.181187 |
| C | 288.150; 870.354; 2200.000; 1080.029 | 0; .048196; .980146; 1.327868 |
| No motor | 288.150; 985.770; 400.000; 159.467 | 0; .112782; −.778958; −.594604 |
| Ideal | 288.150; 556.331; 1600.000; 828.716 | 0; ≈0; 1.061678; 1.061678 |

| Caso | s_gen,c; s_gen,t [kJ/(kg·K)] | eD,c; eD,t [kJ/kg] | Suma parcial [kJ/kg] |
|---|---|---|---:|
| Base no ideal | .0820509581; .0868491326 | 23.642984; 25.025578 | 48.668561 |
| B | .1290486137; .0197782600 | 37.185358; 5.699106 | 42.884464 |
| C | .0481964833; .3477224221 | 13.887817; 100.196216 | 114.084033 |
| No motor | .1127824120; .1843539370 | 32.498252; 53.121587 | 85.619839 |
| Ideal | ≈0; 0 | 0; 0 | 0 |

**Cámara en el caso base:** término térmico `0.9796272985`, presión `0.0147285031`, cambio total `0.9943558016 kJ/(kg·K)`. Al fijar `delta=0`, el término de presión pasa a cero; al aumentarlo a .20 sube, con el término térmico constante si permanecen `T2` y `T3`. En el punto no motor `s3−s2` es negativo, pero se conservan estados y diagnósticos; **no** se publica rendimiento motor.

## 4. Márgenes, tolerancias y hallazgos numéricos

- **Criterios de las pruebas:** `3e−13 kJ/(kg·K)` para entropías; `5e−13` para generaciones analíticas; `3e−10 kJ/kg` para exergías por balance alternativo; `7e−13` absoluto para generaciones **brutas** casi reversibles (no usar error relativo cerca de cero). Se usan `1e−10` aproximadamente en escalados de exergía y `5e−12` para la prueba extrema de logaritmos.
- **Diferencias efectivamente observadas** al reconstruir los cinco perfiles anteriores contra `Decimal`: máximo absoluto en `s_i` **`6.8002e−16 kJ/(kg·K)`** y en `eD,c/eD,t` **`1.9185e−13 kJ/kg`**. En los cuatro perfiles no ideales (excluyendo magnitudes de módulo `≤1e−9`) los máximos relativos fueron **`6.030e−15`** en entropía y **`1.122e−14`** en exergía. Son máximos **observados en esta selección**, no garantías universales.
- **Límite reversible:** con `eta_c=eta_t=1` y `delta=0`, `s_gen` y destrucciones cuantificadas son cero a resolución numérica. También se ensayan eficiencias `1−1e−8` y `1−1e−12`. El bruto se conserva; sólo un negativo dentro de `1e−10·max(|s_entrada|,|s_salida|,cp/1000)` se trunca a cero. Uno fuera lanza `InconsistenciaSegundaLey` o produce diagnóstico de inconsistencia en `analizar_estados`.
- **Invariantes:** duplicar `T0` duplica `eD` y no modifica `T,p,s` ni el estudio previo; multiplicar `cp` por 1.7, con `gamma` fija, escala `s` y `eD` por 1.7; multiplicar `p1` por 3.25 conserva incrementos de `s` y `eD`. Las ecuaciones de estado y los trabajos siguen gobernados por los mismos parámetros originales.
- **Robustez:** se evalúan temperaturas y presiones `1e−300` a `1e300` cuyo cociente directo sería `1e600`, no representable como `float`; el resultado sigue siendo finito gracias a diferencias de logaritmos. Se verifica además un cambio de temperatura relativo de orden `1e−13`, así como límites de `cp` subnormal no representable al dividir por 1000, `T0` no positivo/no finito, `cp≤0`, `gamma≤1`, y desbordamiento de exergía al utilizar `cp=20000` con `T0=1e308` (clasificado `limite_numerico`). Esta última referencia es **un ensayo de representabilidad**, no una temperatura ambiental realista.
- **Diagnóstico:** se mantienen las cuatro entropías y las generaciones cuantificables en un punto no motor, sin rendimiento ni eficiencia exergética global. Una entropía adiabática claramente decreciente entrega estado `inconsistencia`, con temperaturas, presiones y entropías, **sin** eD artificial. Los datos enviados a T–s y a barras se interceptaron en Matplotlib; coinciden con los cuatro estados y las dos eD calculadas para ideal/no ideal. Se comprobaron etiquetas, unidades, la presentación de no motor y la distinción entre cambio de entropía del fluido y generación de cámara.

Los valores impresos en informes redondean (`s` a 8 decimales y `eD` a 6). La comparación científica en pruebas se realiza **antes** del formato, con tolerancias numéricas; no debe esperarse identidad decimal exacta entre representaciones redondeadas. Las referencias `Decimal` tampoco garantizan comportamiento numérico uniforme ante todos los extremos representables.

## 5. Métodos de prueba, ejecución y resultados

**PYTHON.** El oráculo `entropia_decimal(Ti, pi, Tj, pj, cp, gamma)` recibe seis números finitos positivos (`gamma>1`): temperaturas [K], presiones en unidad común, `cp` [J/(kg·K)] y devuelve la tupla `(termica, presion, total)` de tres `float` en kJ/(kg·K). Usa `Decimal`, `localcontext().prec=70` y la comprensión `map(lambda x: Decimal(str(x)), ...)`, no llama a módulos de física; lo invocan directamente las pruebas. Ejemplo: `entropia_decimal(300,100,600,100,1005,1.4)[2]≈0.696613` (referencia aproximada). El contrato físico lo fijan los tests; entradas inválidas pueden lanzar errores de `Decimal`.

El oráculo `estados_referencia(parametros)` recibe `dict` de nueve entradas físicas (`T1`, `T3`, `rp`, `p1`, `gamma`, `cp`, `eta_c`, `eta_t`, `delta`; los dos últimos usan nombres completos del proyecto) y devuelve `dict` con `temperaturas` [K], `presiones` [kPa], `wc`, `wt` [kJ/kg]. Usa potencias, balances analíticos y `cp/1000`; lo llaman los métodos de la clase de tests, **nunca** `viabilidad.calcular_estados`. Ejemplo: `estados_referencia(PARAMETROS_PREDETERMINADOS)['temperaturas'][1]≈603.657 K`. No introduce una nueva API del simulador; requiere parámetros físicos válidos y puede propagar `KeyError`, `ZeroDivisionError` o desbordamientos fuera de su dominio moderado de prueba.

La clase `VerificacionSegundaLeyIndependiente(TestCase)` usa `setUp(self)` para copiar el diccionario base y `punto(self, parametros)` para construir la observación de producción con `evaluar_punto`; esta última recibe un diccionario, devuelve el registro físico ya clasificado y la llaman los nueve `test_*(self)`. Los nueve métodos, invocados por `unittest` y de retorno `None`, cubren respectivamente cuatro entropías, generación analítica, límite reversible, balance alternativo de exergía, cámara, invariantes `T0/cp/p1`, robustez, no motor/inconsistencia y trazas/HTML. `subTest` etiqueta perfiles, `assertAlmostEqual(..., delta=...)` usa error **absoluto**, y `unittest.mock.patch.object` intercepta coordenadas y alturas de barras, devolviendo después la llamada original a Matplotlib; no cambia producción ni datos. Ejemplo: `python -B -m unittest discover -s tests -p 'test_verificacion_segunda_ley.py' -v`.

**Entorno realmente ejecutado:** Linux `6.18.55`, Python `3.12.14`; entorno aislado `/tmp/brayton_v3_venv` con las dependencias de `requirements.txt`: NumPy `2.5.4`, Matplotlib `3.11.2`, Flask `3.1.3` y Jinja2 `3.1.6` (transitiva de Flask). **SciPy no se instaló ni utilizó**, pues no interviene en esta verificación ni está declarada en `requirements.txt`. No se ha ejecutado Windows directamente.

Comandos, desde la raíz de la copia temporal:

```bash
python3 -m venv /tmp/brayton_v3_venv
/tmp/brayton_v3_venv/bin/python -m pip install -r requirements.txt
MPLCONFIGDIR=/tmp/brayton_v3_mpl /tmp/brayton_v3_venv/bin/python -B -m unittest discover -s tests -p 'test_verificacion_segunda_ley.py' -v
PYTHONPATH=tests MPLCONFIGDIR=/tmp/brayton_v3_mpl /tmp/brayton_v3_venv/bin/python -B -m unittest -v test_segunda_ley test_verificacion_analitica.VerificacionAnaliticaIdealTests.test_estados_con_referencias_isentropicas test_verificacion_analitica.VerificacionAnaliticaIdealTests.test_balances_con_referencias_y_residuo test_invariantes_fisicos.InvariantesFisicosTests.test_irreversibilidades_aisladas_reducen_trabajo test_invariantes_fisicos.InvariantesFisicosTests.test_no_motores_conservan_balance_y_motivos
```

| Ejecución | Métodos | Correctos | Fallos | Errores/omisiones | Tiempo `unittest` |
|---|---:|---:|---:|---:|---:|
| V.3 final, tras ajustar un supuesto de prueba | 9 | 9 | 0 | 0 | 0.599 s |
| Regresiones: 18 Segunda Ley + 2 estados/primera ley + 2 física/no motor | 22 | 22 | 0 | 0 | 0.776 s |
| **Total distinto comprobado** | **31** | **31** | **0** | **0** | **1.375 s** |

**Incidencia durante el diseño del test (no de producción):** en la primera ejecución, 8/9 pasaron. El noveno esperaba incorrectamente que `T0=1e308` desbordara con `cp=1005`; su suma todavía era finita. Se corrigió **solamente el dato de entrada del test** a `cp=20000` (también utilizado al evaluar el punto), de modo que la suma de eD supera el máximo de `float`; la repetición focalizada de los 9 dio OK. No se ha ocultado un fallo de física ni corregido un algoritmo. La cifra 31 cuenta **métodos distintos que pasaron al final**, no acumula repeticiones.

## 6. Limitaciones y pendientes

1. El gas ideal de `cp`/`gamma` constantes, el modelo de eficiencias y la hipótesis de adiabaticidad son supuestos de partida; no se han comprobado con datos externos.
2. No hay balances globales de exergía de cámara, rechazo de calor, combustible ni instalación completa. `suma_componentes` sólo suma compresor y turbina.
3. Los límites de flotante y las bandas de redondeo se verifican por casos seleccionados, no por búsqueda exhaustiva de todos los subnormales o cancelaciones. La banda `1e−10` es criterio de la implementación, no precisión certificada de todos los estados.
4. Las pruebas de SVG comprueban **datos que llegan al trazador y textos**; no sustituyen una inspección estética o una validación en todos los navegadores. No se ha comprobado Windows de forma nativa.
5. No se detectaron errores de producción en los perfiles estudiados. **No se modifica producción ni se inicia V.4.** Pendiente de revisión humana y autorización de commit/publicación.
