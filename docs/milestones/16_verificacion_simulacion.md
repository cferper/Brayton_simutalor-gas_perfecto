# V.4 — Verificación independiente de Simulación, gráficos e informes

**Estado:** preparada para revisión, **sin commit ni publicación** (23/10/2026). Repositorio `cferper/Brayton_simutalor`, rama `mejoras/verificacion-numerica`, commit remoto de partida comprobado `df8389207e53d22cb10474e96ec1a77e6650cf57`. La referencia `main` remota observada fue `27d4519094d5eb74f5009a1889a1e74dc8dddb94`. Se creó una copia de trabajo independiente `brayton_v4_simulacion/`; no se alteraron versiones anteriores ni el ordenador Windows.

## 1. Objetivo, alcance y tres niveles de comprobación

Se comprueba la cadena **entrada → cálculo físico → datos de Matplotlib → tablas y tarjetas → HTML autocontenido** de la sección **Simulación**. Abarca el ciclo ideal y no ideal y las siete figuras. No introduce modelos, refactorizaciones ni cambios en `main.py`, `viabilidad.py`, `reporting.py`, `dashboard.py`, `web_app.py`, plantillas, CSS, JS o dependencias.

Los ocho métodos nuevos de `tests/test_verificacion_simulacion.py` emplean tres tipos de referencia:

1. **Física independiente:** las temperaturas, presiones y balances se reconstruyen algebraicamente en `referencia_fisica`, sin llamar a `main` ni a `viabilidad` para obtener el valor esperado.
2. **Integración de datos:** se intercepta la entrada efectiva de `reporting.crear_informe_html` durante dos ejecuciones y se compara con la referencia física, y se comprueba el estudio de Segunda Ley recibido por ese mismo informe.
3. **Representación:** se intercepta `Figure.savefig` de Matplotlib, sin escribir imágenes de prueba, y se examinan series, extremos, coordenadas, máscaras y unidades. En dos ejecuciones reales se comparan también los **bytes PNG** proporcionados al informe con sus siete imágenes Base64.

Esto constituye **verificación de software**, no validación experimental del modelo termodinámico. La coincidencia no prueba que las ecuaciones representen una turbina real.

## 2. Entorno y ejecución

**Entorno realmente utilizado:** Linux 6.18.55, Python 3.12.14, NumPy 2.5.4, Matplotlib 3.11.2, Flask 3.1.3, Jinja2 3.1.6. Entorno aislado `/tmp/brayton_v4_venv` creado con `python3 -m venv`; instalación de **sólo** las dependencias existentes en `requirements.txt` (`numpy`, `matplotlib`, `Flask`, con sus transitivas). SciPy no es necesario, no estaba declarado y no se instaló. `MPLCONFIGDIR` se configuró dentro de `/tmp`, sin modificar archivos del proyecto. No se ejecutó Windows.

Comandos realizados desde la copia V.4:

```bash
python3 -m venv /tmp/brayton_v4_venv
/tmp/brayton_v4_venv/bin/python -m pip install -r requirements.txt
MPLCONFIGDIR=/tmp/brayton_v4_mpl PYTHONDONTWRITEBYTECODE=1 /tmp/brayton_v4_venv/bin/python -B -m unittest discover -s tests -p 'test_verificacion_simulacion.py' -v
PYTHONPATH=tests MPLCONFIGDIR=/tmp/brayton_v4_mpl PYTHONDONTWRITEBYTECODE=1 /tmp/brayton_v4_venv/bin/python -B -m unittest -v test_reporting test_dashboard test_integracion_rendimiento test_web_app test_explicaciones
```

Tras ampliar la comprobación de las tarjetas A/B y la procedencia de Segunda Ley, se repitió **sólo** el método `test_dos_ejecuciones_html_kpi_png_sin_datos_residuales`, que pasó. La suite completa **no** se ejecutó. Los tiempos de los dos grupos se refieren a sus ejecuciones iniciales completas; la repetición focalizada se informa por separado.

| Ejecución | Métodos distintos | Correctos | Fallos | Errores / omitidos | Tiempo `unittest` |
|---|---:|---:|---:|---:|---:|
| V.4 nueva, ocho métodos | 8 | 8 | 0 | 0 / 0 | 3.572 s |
| Regresiones: reporting 11, dashboard 15, integración rendimiento 8, web 11, explicaciones 16 | 61 | 61 | 0 | 0 / 0 | 46.146 s |
| **Total distinto** | **69** | **69** | **0** | **0 / 0** | **49.718 s** |
| Reejecución de un método ampliado, no suma métodos | 1 | 1 | 0 | 0 / 0 | 3.611 s |

## 3. Ecuaciones y convenciones físicas independientes

Para un gas ideal de `cp` y `gamma` constantes, definimos `a=(gamma−1)/gamma`, relación de compresión `rp=p2/p1` y pérdida de presión relativa del combustor `delta`. Los equipos se consideran adiabáticos y el trabajo del compresor es **consumo positivo**:

\[
p_2=p_1r_p,\quad p_3=p_1r_p(1-\delta),\quad p_4=p_1,\qquad
T_{2s}=T_1r_p^a,\quad T_2=T_1+\frac{T_{2s}-T_1}{\eta_c},
\]
\[
T_{4s}=T_3\left(\frac{p_1}{p_3}\right)^a,\quad
T_4=T_3-\eta_t(T_3-T_{4s}).
\]

Para el ideal: `eta_c=eta_t=1`, `delta=0`. Con `cp` en **J/(kg·K)**, temperaturas en **K** y presiones en **kPa**:

\[
w_c=\frac{c_p(T_2-T_1)}{1000},\qquad
w_t=\frac{c_p(T_3-T_4)}{1000},\qquad
w_{net}=w_t-w_c,\qquad q_{in}=\frac{c_p(T_3-T_2)}{1000}
\quad [\mathrm{kJ/kg}].
\]

\[
\eta=\frac{w_{net}}{q_{in}},\qquad BWR=\frac{w_c}{w_t}.
\]

`eta` se mantiene como **fracción interna** y sólo se convierte a porcentaje (`×100`) en las figuras, tablas y tarjetas que así lo indican. `delta` entra como fracción (`0.05`) aunque el formulario muestre `5 %`. No se asigna rendimiento ni BWR motor a un punto no viable. El oráculo emplea signos estrictos y perfiles alejados de fronteras; no reproduce deliberadamente la banda de tolerancia `TOL_REL=1e−10` para puntos casi degenerados, ya cubierta en V.2.

## 4. Dos perfiles reproducibles y resultados físicos

| Parámetro | Base | Alterno | Unidad |
|---|---:|---:|---|
| `T1` | 288.15 | 305 | K |
| `T3` | 1600 | 1450 | K |
| `p1` | 100 | 145 | kPa |
| `rp` | 10 | 6 | — |
| `cp` | 1005 | 1120 | J/(kg·K) |
| `gamma` | 1.4 | 1.32 | — |
| `eta_c`, `eta_t` | 0.85; 0.90 | 0.72; 0.96 | — |
| `delta` | 0.05 | 0.12 | fracción |

Se ejecutaron ambos perfiles y los dos modelos en la copia indicada. Los siguientes valores proceden de un cálculo nuevo con el oráculo físico y de su comparación con las funciones de producción; están **redondeados sólo para documentar**.

| Perfil y modelo | T1, T2, T3, T4 [K] | p1, p2, p3, p4 [kPa] |
|---|---|---|
| Base ideal | 288.150; 556.331; 1600.000; 828.716 | 100; 1000; 1000; 100 |
| Base no ideal | 288.150; 603.657; 1600.000; 916.855 | 100; 1000; 950; 100 |
| Alterno ideal | 305.000; 470.915; 1450.000; 939.129 | 145; 870; 870; 145 |
| Alterno no ideal | 305.000; 535.438; 1450.000; 987.941 | 145; 870; 765.6; 145 |

| Perfil y modelo | `wc` [kJ/kg] | `wt` [kJ/kg] | `wnet` [kJ/kg] | `qin` [kJ/kg] | `eta` [%] | BWR [—] |
|---|---:|---:|---:|---:|---:|---:|
| Base ideal | 269.521453 | 775.140472 | 505.619018 | 1048.887797 | 48.205253 | 0.347707 |
| Base no ideal | 317.084063 | 686.560364 | 369.476301 | 1001.325187 | 36.898732 | 0.461844 |
| Alterno ideal | 185.824852 | 572.175464 | 386.350612 | 1096.575148 | 35.232479 | 0.324769 |
| Alterno no ideal | 258.090072 | 517.506420 | 259.416348 | 1024.309928 | 25.325962 | 0.498719 |

**Discrepancias observadas:** las 4 × (4 temperaturas + 4 presiones + 6 magnitudes escalares) comparaciones del ciclo ideal/no ideal dieron una máxima diferencia absoluta de **0 al nivel de la representación `float`** en los perfiles indicados. El oráculo utiliza expresiones algebraicas equivalentes y el mismo tipo numérico, por lo que la coincidencia exacta en esta muestra **no es una garantía general** ni implica que todas las representaciones decimales sean idénticas. Tolerancias de aceptación: para `T`/`p`, `rtol=3e−13`, `atol=3e−10`; para trabajo, calor, `eta`, BWR y referencias isentrópicas, diferencia absoluta `≤3e−10` en la unidad correspondiente. Las identidades de primera ley y cociente de eficiencia se comprueban además con `1e−10 kJ/kg` y `1e−12` en fracción.

Como referencia adicional, los extremos no ideales y los candidatos A/B producidos por optimización fueron:

| Perfil | Dominio motor no ideal (rp abierto) | rp de A, máximo trabajo | W(A) [kJ/kg] | rp de B, máximo rendimiento | eta(B) [%] |
|---|---|---:|---:|---:|---:|
| Base | (1.069654102; 155.454326039) | 12.895052 | 373.210827 | 35.452324 | 43.893107 |
| Alterno | (1.204675413; 127.620028505) | 12.399222 | 286.533618 | 31.658063 | 36.522023 |

Estos son **valores observados**, no nuevos máximos calculados por el oráculo. Para trazar la procedencia, el test recibe la `rp` calculada por el optimizador y recalcula **independientemente** el trabajo o el rendimiento del punto antes de cotejarlo con su marcador y tarjeta. Las pruebas previas V.1–V.3 cubren con más profundidad la determinación de esos extremos.

## 5. Las siete gráficas: qué llega al trazador

Se inspeccionaron los datos de cada `Figure` inmediatamente antes de guardar, no píxeles. Las curvas puntuales de rendimiento y trabajo utilizaron el barrido adimensional `rp=(1, 1.5, 3, 6, 10, 20, 50, 500)` y referencias calculadas con las ecuaciones de la sección 3. Se comprobaron también el texto del eje, sus unidades, marcas y cortes por inviabilidad.

| PNG | Qué se contrastó contra el oráculo |
|---|---|
| `rendimiento_brayton.png` | `rp` en horizontal (eje logarítmico); rendimiento **ideal** multiplicado por 100; `NaN` en puntos no motores |
| `diagrama_ts_brayton.png` | Cuatro estados ideales, s1=s2=0 y s3=s4; segmentos verticales isentrópicos; isóbaras `s=s0+cp/1000·ln(T/T0)`; `K`, `kJ/(kg·K)` |
| `diagrama_pv_brayton.png` | Cuatro estados ideales, `p·1000·v=RT`; isentrópicas `pv^gamma` constante; dos isóbaras y 200 muestras por proceso; `m³/kg`, `kPa` |
| `trabajo_neto_vs_rp.png` | `rp` horizontal y trabajo ideal `kJ/kg`; `NaN` fuera de motor; marca del máximo ideal calculado físicamente |
| `comparacion_ideal_noideal.png` | Ambas series de rendimiento de la **misma** malla, porcentaje, máscaras diferentes cuando procede y marcadores de A/B con `rp` y valores físicos correctos |
| `trabajo_neto_ideal_noideal.png` | Ambas series de trabajo neto, `kJ/kg`, en la misma malla; marcadores A/B y conservación de la serie completa, incluso si el eje la recorta visualmente |
| `compromiso_trabajo_rendimiento.png` | Pares `(w_net [kJ/kg], 100·eta [%])` del barrido no ideal; exclusiones como `NaN`, A/B en coordenadas físicas; ausencia de estrella B cuando no se suministra máximo interior |

En T–s se comprobaron las 100 muestras de cada isóbara y en P–v las 200 muestras de cada recorrido, incluidos interiores y extremos, además de las coordenadas de los cuatro estados. Las fórmulas se aplicaron fuera de las funciones gráficas; las series contrastadas cumplieron `rtol≤2e−12` en las comprobaciones termodinámicas de curvas. Para trabajo/rendimiento se aceptaron diferencias absolutas de `3e−10–4e−10` por muestra, según la magnitud; en marcadores, hasta `3e−9` para trabajo. En la muestra ensayada no hubo diferencias que superaran esos criterios. No se ha supuesto que el diagrama T–s o P–v represente el ciclo no ideal.

La línea del compromiso es **un barrido paramétrico**, no una frontera de Pareto completa. La comprobación de B ausente es una entrada focalizada del trazador, no una afirmación sobre la existencia de B en todos los casos. El test no obliga a una disposición concreta de los artistas Matplotlib ni compara imágenes píxel a píxel.

## 6. Trazabilidad de HTML, dashboard y ejecuciones sucesivas

Se generaron dos simulaciones reales en un directorio temporal común. Para cada una:

- Los argumentos efectivos de `crear_informe_html` contienen las **nueve entradas** de esa ejecución, el ideal/no ideal contrastados con el oráculo y los datos de optimización de su propio perfil.
- Se contrastaron en el HTML las cuatro filas de estados de cada modelo, los trabajos y el calor en kJ/kg, los rendimientos visibles `×100`, el `T1/T3` del formulario y la pérdida `delta×100` mostrada en porcentaje. Las KPI de caso actual (`rp`, trabajo, rendimiento, calor) y las de A/B se contrastaron también con su referencia física. Las cifras HTML se aceptan **tras aplicar su formato declarado** (2 decimales para estados, 6 para balances, 3 para tarjetas); un redondeo visible no cambia el cálculo subyacente.
- `dashboard.separar_presentacion` recuperó los metadatos del perfil y los paneles `resultados`, `optimizacion`, `sensibilidad`, `segunda_ley`. El estudio de Segunda Ley tenía `T0=288.15 K` y los estados `T,p` **del mismo perfil**; las ecuaciones exergéticas en sí pertenecen a V.3.
- Los siete buffers de imágenes enviados a `crear_informe_html` comenzaron por la firma PNG y coincidieron **byte a byte**, sin duplicaciones, con los siete `src=data:image/png;base64` del HTML. Los hashes SHA-256 de T–s y de comparación ideal/no ideal fueron distintos entre las ejecuciones; no hubo reutilización de la gráfica anterior.
- `main.PARAMETROS_PREDETERMINADOS` quedó inalterado, y las gráficas se generaron en memoria: los tests no crearon PNG permanentes.

El formulario `web_app.leer_parametros` convirtió `12 %` a `0.12` para el perfil alterno y conservó el contrato de `5 %` para el valor inicial. Para el punto no motor `T1=288.15 K`, `T3=400 K`, `rp=50`, `eta_c=.85`, `eta_t=.90`, `delta=.05`, el oráculo obtuvo `T2≈985.770 K`, `w_net≈−459.372499 kJ/kg`, `q_in≈−588.699128 kJ/kg` y **ningún rendimiento motor**. Tanto `main.main` como el formulario POST rechazaron la simulación normal, con diagnóstico de inviabilidad, sin informe, KPI de trabajo ni residuo en el directorio temporal.

## 7. Alcance de las pruebas y limitaciones

1. La termodinámica de referencia contrasta **las mismas hipótesis ideales simplificadas**, no datos experimentales: `cp` y `gamma` constantes, equipos adiabáticos, eficiencias y pérdida de combustor prescritas. No se han validado aerodinámica, combustión ni componentes reales.
2. Dos casos motores y un caso no motor no cubren todos los extremos o casos mal condicionados. Las bandas próximas a las fronteras y los máximos planos se estudiaron en fases previas; aquí se evita confundir errores de redondeo con defectos de transporte de datos.
3. El test inspecciona los datos entregados a Matplotlib y la integridad PNG/Base64, **no la fidelidad de cada píxel**, su apariencia en todos los navegadores ni la accesibilidad dinámica del JavaScript. Los tests de dashboard y Flask existentes aportan regresiones complementarias.
4. No se ejecutó Windows; no se afirma compatibilidad comprobada allí. SciPy es opcional y no interviene en esta etapa.
5. La verificación de los puntos A/B comprueba su transporte y valores físicos, pero no vuelve a demostrar exhaustivamente la convergencia de los optimizadores, ya cubierta en Fase 1 y V.1–V.2.

**Conclusión técnica:** los **69 métodos distintos** seleccionados terminaron correctamente; en los casos estudiados **no se detectó defecto reproducible** entre cálculo, gráfica, informe y dashboard. Esto permite considerar **V.4 verificada dentro de su alcance y preparada para revisión humana**, no publicada. No se modifica producción ni se inicia la siguiente verificación.
