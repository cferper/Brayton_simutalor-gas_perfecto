# V.1 — Verificación independiente del módulo Sensibilidad

**Preparado el 22/10/2026, pendiente de revisión; sin commit ni publicación.**

- Repositorio: `cferper/Brayton_simutalor`; rama `mejoras/verificacion-numerica`.
- Commit remoto de partida comprobado: `cd3349c59e85a0e34e48d9c49aefeb0a4014dd1f`.
- Objetivo: contrastar el **módulo OFAT existente**, sin modificar física, optimizadores, valores por defecto, gráficos, HTML ni Flask.
- Contexto: [cierre publicado de la nueva Fase 1](12_cierre_verificacion_numerica.md) y [Fase 4 de sensibilidad ya implementada](06_sensibilidad_parametrica.md).

## 1. Supuestos y método de contraste

El programa usa gas perfecto con `cp` y `gamma` constantes, `T1<T3`, eficiencias isentrópicas prescritas y pérdida relativa `delta` del combustor. OFAT varía **una** de `T1`, `T3`, `eta_c`, `eta_t` o `delta`, dejando constantes las otras ocho entradas. Las ecuaciones de referencia se reescribieron en `tests/test_verificacion_sensibilidad.py` **sin importar `sensibilidad.py` ni los optimizadores para calcular el oráculo físico**:

\[
 a=(\gamma-1)/\gamma,\quad r_e=r_p(1-\delta),\quad k=c_p/1000,
\]
\[
 T_2=T_1[1+(r_p^a-1)/\eta_c],\quad
 T_4=T_3[1-\eta_t(1-r_e^{-a})],
\]
\[
 W_c=k(T_2-T_1),\quad W_t=k(T_3-T_4),\quad
 W=W_t-W_c,\quad Q_{in}=k(T_3-T_2),\quad \eta=W/Q_{in}.
\]

`T` se mide en K; `cp` en J/(kg·K); `W`, `Q` en kJ/kg; `eta` en **fracción**. La última división **sólo se interpreta como rendimiento motor** cuando `r_p>1`, `r_e>1`, `W>0`, `Q_in>0` y el programa acepta el punto tras sus bandas de viabilidad. El oráculo usa signos estrictos en casos moderados; la aceptación por banda la verifica el programa por separado.

### R — derivadas parciales con `rp` fija

Con `u=r_p^a` y `v=r_e^{-a}`:

| Parámetro `x` | `∂W/∂x` | `∂Qin/∂x` |
|---|---|---|
| `T1` | `−k(u−1)/eta_c` | `−k[1+(u−1)/eta_c]` |
| `T3` | `k eta_t(1−v)` | `k` |
| `eta_c` | `k T1(u−1)/eta_c²` | `k T1(u−1)/eta_c²` |
| `eta_t` | `k T3(1−v)` | `0` |
| `delta` | `−k eta_t T3 a v/(1−delta)` | `0` |

Para rendimiento se aplica la regla del cociente `∂eta/∂x = [(∂W/∂x)Qin − W(∂Qin/∂x)]/Qin²`. Elasticidad adimensional: `S_x^Y = x(∂Y/∂x)/Y` si `x≠0` y `Y` no es nula ni está mal condicionada. Las derivadas respecto a temperaturas tienen unidad kJ/(kg·K) para `W`/`Q`; respecto a eficiencias y `delta`, kJ/kg por unidad de fracción. Para `eta`, fracción por K o por unidad de fracción. **No se confunden derivada relativa y puntos porcentuales.**

### A y B — objetivos reajustados

- **A:** para `W` el punto estacionario se obtuvo sin llamar a `calcular_candidato_analitico`: `rp_A^a = sqrt(eta_c eta_t (T3/T1) (1−delta)^(−a))`. Se comprueba su pertenencia al dominio motor y `W` por balances independientes. Se contrasta también la **identidad de envolvente** `dW_max/dx = (∂W/∂x)_rp=rp_A` en un máximo interior suave. La identidad **no** convierte la derivada de R a `rp` fija en la de A para cualquier punto: sólo es aplicable en el óptimo A.
- **B:** `scipy.optimize.minimize_scalar(method="bounded")`, opcional, minimiza `−eta(log rp)` dentro del dominio motor, sin usar el candidato analítico de B para dirigir la búsqueda. El dominio de entrada procede de `calcular_dominios`, ya verificado en la Fase 1, y se reexige admisibilidad física en la solución; **no** es una verificación independiente nueva de los límites de dicho dominio. Si SciPy falta, este método se **omite**, no se declara superado.
- **Orden:** cuando R, A y B existen como motores interiores, `W_A≥W_R,W_B` y `eta_B≥eta_R,eta_A` dentro de tolerancias. El ciclo reversible ideal tiene **supremo de eta en frontera abierta**, nunca máximo B alcanzado.

## 2. Casos y resultados medidos

**Procedencia:** llamadas reales al commit inicial desde Linux, Python 3.12.14, NumPy 2.5.4, SciPy 1.17.0 y entorno virtual de verificación fuera del repositorio. No se copiaron cifras sin recalcularlas. Parámetros de referencia:

| Caso | `T1` K | `T3` K | `gamma` | `cp` J/(kg·K) | `p1` kPa | `eta_c` | `eta_t` | `delta` | `rp_R` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N1 | 288.15 | 1600 | 1.4 | 1005 | 100 | .85 | .90 | .05 | 10 |
| N2 | 300 | 1200 | 1.33 | 1100 | 90 | .90 | .94 | .03 | 6 |

Otros testigos cambian individualmente `eta_c` a 1, `delta` a 0, `T3` a 1850 K, un R de `rp=300` no motor, un dominio vacío (`T1=300`, `T3=400`, `delta=.5`), o usan `eta_c=eta_t=1`, `delta=0` para el reversible. Las otras entradas se mantienen como en N1. En la prueba R de gradientes: ventanas OFAT `T1:270–310 K`, `T3:1450–1750 K`, `eta_c:.8–.9`, `eta_t:.85–.95`, `delta:.02–.08`, cada una con tres muestras; **las derivadas se evalúan en el punto de referencia**, no en los extremos de esas ventanas.

### R — estados, energía y derivadas

En los dos perfiles, el mayor error absoluto de las expresiones independientes frente a `evaluar_muestra` fue `1.137e−13 K` para temperaturas; `1.137e−13 kJ/kg` para energías; `1.110e−16` para rendimiento como fracción. Mayor error relativo de esas magnitudes: `3.723e−16` (rendimiento). No son cotas universales.

| `x` | `∂W_R/∂x` analítica | Error absoluto `∂W` | `∂Qin_R/∂x` analítica | Error absoluto `∂Qin` | `∂eta_R/∂x` analítica | Error absoluto `∂eta` |
|---|---:|---:|---:|---:|---:|---:|
| `T1` | −1.100413197 | 2.258e−11 | −2.105413197 | 2.026e−11 | −0.0003231142293 | 2.949e−14 |
| `T3` | +0.4291002274 | 1.232e−11 | +1.005000000 | 2.730e−12 | +0.0000581908532 | 1.677e−14 |
| `eta_c` | +373.0400738 | 2.051e−8 | +373.0400738 | 1.112e−8 | +0.2350814883 | 1.429e−11 |
| `eta_t` | +762.8448487 | 2.817e−8 | 0 | 0 | +0.7618352743 | 2.817e−11 |
| `delta` | −228.7638004 | 3.439e−8 | 0 | 0 | −0.2284610467 | 2.600e−11 |

**Máximos observados en estas 15 comparaciones de gradiente:** error absoluto `3.439e−8 kJ/kg por unidad de fracción` en `∂W/∂delta`; error relativo `2.882e−10` en `∂eta/∂T3` (referencia no nula). Un mismo error absoluto no tiene la misma unidad en todas las columnas. Los signos concuerdan: aumentar `T1` o `delta` reduce `W_R` en el caso base; aumentar `T3`, `eta_c` o `eta_t` lo incrementa.

**Extremos permitidos:** con `eta_c=1`, derivada unilateral hacia atrás de `W_R` analítica `+269.52145333`, error `3.812e−8`; con `delta=0`, unilateral hacia delante `−214.16387874`, error `3.802e−8`. Aquí `dW/ddelta` **existe**, pero `S_delta^W=None`: una variación porcentual respecto a cero no define una elasticidad interpretable. La diferencia entre derivadas calculadas con pasos `h` y `h/2` se registra en `error_estimado`; esa diferencia sirve como control heurístico de estabilidad, **no** como error verdadero garantizado.

### A y B — posiciones y objetivos

| Caso | R: `W` kJ/kg / `eta` fracción | A: `rp` / `W` kJ/kg | B: `rp` / `eta` fracción | `|Δrp_B|` frente a SciPy | `|Δeta_B|` |
|---|---|---|---|---:|---:|
| N1 | `369.476301 / .368987324` | `12.895051670 / 373.210827483` | `35.452323571 / .438931071631` | `5.798e−7` | `1.110e−16` |
| N2 | `234.021977 / .298219046` | `11.843948591 / 253.344947511` | `37.270299632 / .433840899269` | `4.165e−8` | `2.220e−16` |

SciPy convergió en ambas comparaciones acotadas, con **11 y 13 evaluaciones** respectivamente; los puntos fueron motores y estrictamente interiores. Mayor error relativo en la **posición B**: aproximadamente `1.64e−8` (N1); el rendimiento, función plana cerca de su máximo, difiere mucho menos que la posición. La `rp_A` independiente discrepó como máximo `1.421e−14`, y `W_A` como máximo `2.274e−13 kJ/kg` en los dos casos. Para la identidad de envolvente: error en `dW_A/dT3` `3.682e−12 kJ/(kg·K)` y en `dW_A/ddelta` `4.986e−9 kJ/kg por unidad de fracción`.

El test de orden R/A/B se ejecutó también con `T3=1850 K`, `eta_c=.92`, `eta_t=.96` y `delta=.09`: se cumplieron las dos desigualdades. El R con `rp=300` del caso N1 es no motor (`W≈−238.200281 kJ/kg`, `Qin≈−79.155563 kJ/kg`); el módulo conserva la **consigna** 300 pero no publica `rp` operativa ni `eta` ni elasticidades de un motor inexistente. En el caso sin dominio no ideal, A/B dan `sin_dominio`. Para el reversible, B sólo declara `supremo_no_alcanzado` con `eta_sup=1−T1/T3`, sin curva ni derivada B ficticia.

### Criterios de aceptación explícitos

- R: `|ΔT|≤1e−9 K`, `|Δenergía|≤2e−10 kJ/kg`, `|Δeta|≤2e−10` para puntos interiores; derivadas centrales `|ΔD|≤2e−6·max(1,|D_ref|)` y unilaterales `≤3e−6·max(1,|D_ref|)` **en la unidad de cada derivada**. Son umbrales de verificación para estos casos, no promesas universales de precisión.
- A: `|Δrp_A|≤2e−9·rp_A` y `|ΔW_A|≤2e−10 kJ/kg`; identidad de envolvente con la tolerancia de derivadas centrales. No aplicar si A no existe como máximo motor interior.
- B: `|Δrp_B|≤2e−6·rp_B(SciPy)` y `|Δeta_B|≤2e−9`; además `success=True`, pertenencia estricta al dominio y signos físicos correctos. `success=True` aislado no prueba viabilidad.
- Orden: holgura `1e−8 kJ/kg` en trabajo y `1e−10` en `eta` fraccionaria por efectos de redondeo. No se exige monotonía exacta de los errores al refinar ni se asignan coeficientes a resultados `None`.

## 3. Pruebas reproducibles

La comparación nueva son **ocho** métodos `unittest` en `tests/test_verificacion_sensibilidad.py`; se ejecutaron **25 regresiones** de `tests/test_sensibilidad.py` y **cuatro** seleccionadas de optimización. Resultado acumulado de estas ejecuciones focalizadas: **37/37 correctas, 0 fallidas, 0 errores, 0 omitidas** con SciPy 1.17.0.

Desde la raíz del repositorio, con el intérprete de un entorno que tenga `requirements.txt` instalado:

```bash
MPLCONFIGDIR=/tmp/brayton_etapa_6_mpl python -B -m unittest discover -s tests -p test_verificacion_sensibilidad.py -v
MPLCONFIGDIR=/tmp/brayton_etapa_6_mpl python -B -m unittest discover -s tests -p test_sensibilidad.py -q
MPLCONFIGDIR=/tmp/brayton_etapa_6_mpl PYTHONPATH=tests python -B -m unittest -q \
  test_optimizacion.OptimizacionTests.test_referencia_analitica_numerica_y_estados \
  test_optimizacion.OptimizacionTests.test_dominio_vacio_no_llama_a_la_busqueda \
  test_optimizacion_rendimiento.RendimientoTests.test_busqueda_numerica_independiente \
  test_optimizacion_rendimiento.RendimientoTests.test_ideal_supremo_no_es_optimo_motor
```

Los comandos anteriores reproducen la selección ejecutada en **Linux**; sustituye `python` por el intérprete real del entorno (`/tmp/brayton_etapa_6_venv/bin/python` fue el utilizado) y elige una carpeta de caché Matplotlib con permisos de escritura. En **Windows PowerShell**, sin depender del `python` global, el primer comando equivale a:

```powershell
$env:MPLCONFIGDIR = Join-Path $env:TEMP 'brayton_sensibilidad_mpl'
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_verificacion_sensibilidad.py -v
```

Para reproducir el **contraste B** instala SciPy **sólo en el entorno opcional de pruebas**, sin tocar `requirements.txt`; en su ausencia habrá **una omisión explícita entre las ocho pruebas nuevas**, no una comparación aprobada. Estas tres ejecuciones no vuelven a repetir la suite completa histórica de 215. Los resultados consignados proceden de Linux; la guía Windows aún no constituye una ejecución nativa verificada.

## 4. Interpretación educativa y limitaciones

**INGENIERÍA.** `dW_R/dT3` responde a subir la temperatura de entrada a turbina **sin cambiar `rp`**. En A, cada perturbación desplaza la relación de presiones que maximiza el trabajo; el teorema de la envolvente explica por qué la derivada del **valor máximo** coincide con la derivada parcial en el óptimo, aunque la posición óptima cambie. En B se persigue otra función objetivo, de modo que W puede disminuir mientras mejora `eta`. Un valor de derivada positivo no autoriza extrapolaciones grandes a través de fronteras o cambios de régimen.

**PYTHON / NUMÉRICO.** Los helpers `referencia_independiente`, `gradientes_r` y `rp_max_trabajo_independiente` son expresiones matemáticas locales al test; `subTest` informa casos parametrizados, `skipUnless` hace explícita la dependencia opcional, `minimize_scalar` trabaja con `y=log(rp)`, y `assertAlmostEqual(..., delta=...)` compara con una tolerancia absoluta y **no** por número de cifras decimales. El programa OFAT diferencia centrales/unilaterales, reevalúa con `h/2`, y usa `None`/`NaN` para ausencia de magnitudes motoras, no para valores físicos iguales a cero.

**Lo verificado:** consistencia del código con las ecuaciones prescritas, derivadas/elasticidades locales, valores y posiciones óptimas representativos y política de disponibilidad. **Lo no verificado:** datos experimentales de turbomáquinas, propiedades variables, extrapolación a motores reales, derivadas cerca de discontinuidades extremadamente estrechas, casi degeneraciones ni ejecución nativa en Windows. La suite completa de 215 corresponde al **cierre anterior**, no a esta intervención. No se detectaron discrepancias que requieran cambiar producción con los casos ensayados.

**Estado Git:** una copia temporal independiente en `mejoras/verificacion-numerica`, commit base `cd3349c`; el test nuevo, este documento y la ampliación del manual quedan **sin commit, push, merge ni pull request**, pendientes de aceptación del usuario.
