# Cierre técnico propuesto — nueva Fase 1 de verificación numérica

**Preparado el 22/10/2026 para revisión, sin commit ni publicación.** Rama `mejoras/verificacion-numerica`; versión de producción examinada: `57da73db01882ab32bd5d92d14bdbe739c272b79`. Esta **nueva** Fase 1 no es la antigua fase de dominio viable del [milestone 03](03_dominio_viable.md).

## 1. Resumen ejecutivo

Se ha comprobado que la implementación de Brayton **ideal y no ideal con propiedades constantes** reproduce las expresiones que pretende resolver: estados y balances, raíces y restricciones del dominio motor, máximos interiores y casos sin solución admisible. Las cinco tareas ya publicadas aportaron pruebas separadas del código de producción:

| Tarea | Contraste | Commit publicado |
|---|---|---|
| 1.1 | Referencias analíticas ideales | `275e7558b7d05322054f89ecd672ed5563c59469` |
| 1.2 | Raíces, discriminante y fronteras abiertas | `143d10fd25ebd23ddb897722b7843bddabfd16a5` |
| 1.3 | Bisección/Brent y máximos frente a SciPy opcional | `8ecbc1bf75e7e68fc3377cbf97017f8480d32553` |
| 1.4 | Tolerancias, mallas, iteraciones y bandas de viabilidad | `c3b4bfea12cf6faa1dc90c8f8fb16fb9e8fe7131` |
| 1.5 | Primera ley, irreversibilidades y escalados | `57da73db01882ab32bd5d92d14bdbe739c272b79` |

**Resultado nuevo de esta etapa:** una ejecución completa de `unittest` en Linux terminó con **215 pruebas correctas, ninguna fallida, omitida ni con error de importación (69,358 s)**, incluida la comparación con SciPy. Se añadieron tablas nuevas calculadas sobre el commit indicado y un ensayo focalizado de ausencia de SciPy. **No se ha ejecutado Windows** ni realizado una validación experimental. No se ha encontrado una discrepancia de producción que justifique modificar algoritmos en esta etapa.

## 2. Reproducción desde una copia limpia

El código se ejecuta desde la raíz del repositorio, en la rama indicada. `requirements.txt` sólo declara **NumPy, Matplotlib y Flask** (que instala Jinja2 como dependencia transitiva); SciPy es **opcional y sólo sirve para las seis comparaciones dependientes de él**. Para reproducir exactamente esta ejecución de cierre, instálalo por separado en el entorno de verificación, **sin añadirlo a `requirements.txt`**. La ausencia de SciPy dará seis pruebas omitidas, no seis verificaciones satisfactorias.

### Windows PowerShell

En una **clonación nueva**, el lanzador `py` puede crear el entorno si está disponible. Si ya existe `.venv`, **no lo reemplaces**; usa directamente su intérprete. El `python` global no es necesario:

```powershell
git clone --branch mejoras/verificacion-numerica https://github.com/cferper/Brayton_simutalor.git Brayton_Simulator
cd Brayton_Simulator
py -3 -m venv .venv  # sólo si no existe; requiere el lanzador py instalado
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install scipy==1.17.0  # opcional: comparaciones 1.3
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -q
```

Si `py` tampoco existe, crea `.venv` con la ruta de tu instalación de Python antes de usar los comandos posteriores. Para una copia de trabajo **ya existente**, comprueba primero `git status` y actualiza sólo mediante `git pull --ff-only` si no tienes cambios versionados incompatibles. Los archivos locales no versionados no deben añadirse automáticamente.

### Linux / macOS

```bash
git clone --branch mejoras/verificacion-numerica https://github.com/cferper/Brayton_simutalor.git Brayton_Simulator
cd Brayton_Simulator
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install scipy==1.17.0  # opcional: comparaciones 1.3
mkdir -p /tmp/brayton_mpl
MPLCONFIGDIR=/tmp/brayton_mpl .venv/bin/python -B -m unittest discover -s tests -q
```

La instalación sin versiones fijadas de NumPy/Matplotlib/Flask puede resolver versiones diferentes en otro momento; **anota siempre sus versiones**. `-B` evita archivos de bytecode, `discover` busca pruebas `test_*.py`, `-s tests` selecciona el directorio y `-q` presenta el resumen. El entorno virtual y la caché de Matplotlib no forman parte del repositorio. La suite utiliza temporales para informes; **no necesitas regenerar informes históricos**. No es obligatorio que coincidan los últimos decimales entre plataformas.

## 3. Tablas de referencia medidas en esta etapa

**Procedencia:** ejecución directa de `calcular_dominios`, `evaluar_punto`, `optimizar_trabajo_neto` y `optimizar_rendimiento` del commit `57da73d` el 22/10/2026, con Python 3.12.14. No se han reutilizado cifras históricas sin recalcularlas. `T` en K, `cp` en J/(kg·K), `p1` en kPa, `w` y `q` en kJ/kg, `eta` en **fracción**; `gamma`, `eta_c`, `eta_t`, `delta` y `rp` son adimensionales.

### Entradas y clasificación

| Perfil | T1 | T3 | gamma | cp | p1 | eta_c | eta_t | delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| I (ideal) | 288.15 | 1600 | 1.4 | 1005 | 100 | 1 | 1 | 0 |
| N1 (no ideal) | 288.15 | 1600 | 1.4 | 1005 | 100 | 0.85 | 0.90 | 0.05 |
| N2 (no ideal distinto) | 300 | 1200 | 1.33 | 1100 | 90 | 0.90 | 0.94 | 0.03 |
| Ø (sin dominio no ideal) | 300 | 400 | 1.4 | 1005 | 100 | 0.85 | 0.90 | 0.50 |

| Caso | Perfil y `rp` utilizada | Límites de `rp` del dominio motor (abierto)* | Clasificación y motivo |
|---|---|---|---|
| I | I; `10` | `(1, 403.417520320)` | Motor |
| N1 | N1; `10` | `(1.069654102, 155.454326039)` | Motor |
| N2 | N2; `6` | `(1.044317139, 134.326166857)` | Motor |
| B9 | N1; `155.45432588374453` | Igual que N1 | Motor, interior a ~`1e-9` relativo de la frontera alta |
| B12 | N1; `155.45432603904342` | Igual que N1 | **No admitido**: banda numérica de `trabajo_neto` |
| Ø | Ø; `2` | `()` | **Sin dominio no ideal**; en el punto fallan `expansion` y `trabajo_neto` |

\* Los paréntesis, no corchetes, representan **fronteras excluidas**. En B12 la cuadrática admite interior por signo (`tolerancia=0`), pero `evaluar_punto()` con `1e-10` rechaza el trabajo demasiado pequeño. Aunque Ø carece de dominio **no ideal**, el mismo conjunto de `T1,T3` permitiría estudiar otro ciclo ideal: no debe confundirse con falta de representación numérica.

| Caso | T1 | T2 | T3 | T4 |
|---|---:|---:|---:|---:|
| I | 288.150000 | 556.330551 | 1600.000000 | 828.715949 |
| N1 | 288.150000 | 603.656530 | 1600.000000 | 916.855359 |
| N2 | 300.000000 | 486.607430 | 1200.000000 | 800.645318 |
| B9 | 288.150000 | 1382.564952 | 1600.000000 | 505.585048 |
| B12 | 288.150000 | 1382.564952 | 1600.000000 | 505.585048 |
| Ø | 300.000000 | 377.298937 | 400.000000 | 400.000000 |

| Caso | `w_c` | `w_t` | `w_neto` | `q_in` | Rendimiento motor |
|---|---:|---:|---:|---:|---:|
| I | 269.521453 | 775.140472 | 505.619018 | 1048.887797 | 0.482052532077 |
| N1 | 317.084063 | 686.560364 | 369.476301 | 1001.325187 | 0.368987323745 |
| N2 | 205.268173 | 439.290150 | 234.021977 | 784.731827 | 0.298219046329 |
| B9 | 1099.887026 | 1099.887027 | `3.12295015e-7` | 218.522224 | `1.42912245e-9` |
| B12 | 1099.887027 | 1099.887027 | `2.44426701e-10` | 218.522223 | **No disponible** |
| Ø | 77.685431 | 0.000000 | −77.685431 | 22.814569 | **No disponible** |

La igualdad aparente entre `w_c` y `w_t` de B12 es **efecto del redondeo de la tabla**, no trabajo exactamente nulo: `w_neto=2.444267011e-10 kJ/kg`, por debajo de la banda `1.608e-7 kJ/kg`. B9 tiene `w_neto=3.122950147e-7 kJ/kg`, por encima de esa banda. El residuo de primera ley `w_neto-(q_in-q_out)` medido en estos testigos fue `2.842e-13 kJ/kg` (B9) y `2.842e-14 kJ/kg` (B12); es un residuo algebraico, no un error experimental.

### Óptimos y ausencia de solución

**A** es el máximo interior de trabajo, **B** el máximo interior de rendimiento. Las columnas analíticas son referencias internas distintas de la búsqueda con malla; esta búsqueda usa `muestras=257`, `tolerancia_log=1e-9`, `max_iteraciones=100`.

| Perfil | A: rp analítica / numérica | A: `w_neto` máximo [kJ/kg] | B: rp analítica / numérica | B: `eta` máxima [fracción] |
|---|---|---:|---|---:|
| I | `20.0852562921 / 20.0852561129` | 532.802230119 | **No existe B interior** | Supremo `0.81990625`, no alcanzado, rp frontera `403.417520320` |
| N1 | `12.8950516696 / 12.8950517350` | 373.210827483 | `35.4523235708 / 35.4523219222` | 0.438931071631 |
| N2 | `11.8439485905 / 11.8439480437` | 253.344947511 | `37.2702996321 / 37.2702992355` | 0.433840899269 |
| Ø | No existe A motor | — | No existe B motor | — |

En I, N1 y N2, ambas búsquedas numéricas realizaron **297 evaluaciones y 38 iteraciones** en esta ejecución. No se interpreta ese recuento como constante ni como garantía de rendimiento temporal. En Ø, `optimizar_trabajo_neto` y `optimizar_rendimiento` devolvieron `sin_dominio`, sin máximos ficticios.

**Cómo regenerar las tablas:** desde la raíz, abre el intérprete de `.venv` (`.\.venv\Scripts\python.exe` en Windows o `.venv/bin/python` en Linux/macOS) y utiliza el bloque siguiente como script; también puedes pasarlo a la entrada estándar de Python sin crear archivos en el repositorio:

```python
from viabilidad import evaluar_punto, calcular_dominios
from optimizacion import optimizar_trabajo_neto
from optimizacion_rendimiento import optimizar_rendimiento

perfiles = {
    "I": (288.15, 1600, 1.4, 1005, 100, 1, 1, 0),
    "N1": (288.15, 1600, 1.4, 1005, 100, .85, .9, .05),
    "N2": (300, 1200, 1.33, 1100, 90, .9, .94, .03),
    "Ø": (300, 400, 1.4, 1005, 100, .85, .9, .5),
}
hi = calcular_dominios(*perfiles["N1"])["noideal"]["intervalo"][1]
casos = [("I", "I", 10), ("N1", "N1", 10), ("N2", "N2", 6),
         ("B9", "N1", hi*(1-1e-9)), ("B12", "N1", hi*(1-1e-12)),
         ("Ø", "Ø", 2)]
for nombre, perfil, rp in casos:
    T1, T3, gamma, cp, p1, ec, et, delta = perfiles[perfil]
    punto = evaluar_punto(T1, T3, gamma, cp, rp, p1, ec, et, delta)
    dominio = calcular_dominios(T1, T3, gamma, cp, p1, ec, et, delta)
    print(nombre, rp, punto["temperaturas"],
          tuple(punto[k] for k in ("trabajo_compresor", "trabajo_turbina",
                                  "trabajo_neto", "calor_aportado")),
          punto["rendimiento"], punto["viable"], punto["motivos"],
          dominio["ideal" if perfil == "I" else "noideal"]["intervalo"])
for nombre, p in perfiles.items():
    trabajo, rendimiento = optimizar_trabajo_neto(*p), optimizar_rendimiento(*p)
    print("OPT", nombre, trabajo["estado"], trabajo["analitico"],
          rendimiento["estado"], rendimiento.get("analitico"),
          rendimiento.get("supremo"))
```

No compares las cadenas formateadas mediante igualdad estricta: son valores de punto flotante. Todos los puntos anteriores se clasificaron con la tolerancia predeterminada `TOL_REL=1e-10`; `calcular_dominios` usa bisección con `tolerancia=1e-12` en `x=rp**a`. Para temperaturas/energías moderadas usa como punto de partida `atol_T=1e-9 K`, `atol_E=1e-10 kJ/kg`, `rtol=2e-12`; para rendimiento motor `atol_eta=2e-13`, `rtol=2e-12`. **En B9/B12 no apliques una comparación relativa al trabajo casi cero** ni redondees antes de clasificar; comprueba el margen de trabajo frente a su banda (`1e-10` de la escala energética). Los óptimos numéricos tienen márgenes más amplios por la planitud, descritos a continuación.

## 4. Matriz de verificación y aceptación

Se separa la evidencia **histórica** de cada tarea (ver [guía 11](11_verificacion_numerica_APRENDIZAJE.md)) del **nuevo resultado global** de 215 pruebas. Los errores máximos son observaciones de los casos ensayados, **no cotas universales**.

| Área | Propiedad, prueba y referencia | Criterio de aceptación usado | Evidencia y limitación |
|---|---|---|---|
| Ciclo ideal | `test_verificacion_analitica.py`; relaciones isentrópicas y primera ley directas | `atol_T=1e-9 K`, `atol_E=1e-10 kJ/kg`, `atol_eta=2e-13`, `rtol=2e-12` | Tarea 1.1: hasta `1.137e-13 K` y `1.137e-13 kJ/kg`; cinco casos ideales moderados; no datos externos |
| Raíces y dominio | `test_verificacion_raices.py`; raíces cuadráticas de `Q(x)` y signos de cuatro restricciones | Error x `≤2e-12+2e-12|x_ref|`; rp `≤1e-9+2e-11|rp_ref|`; residuo `≤2e-11` × escala Q; extremos abiertos | Tarea 1.2: ocho raíces, máximo `|Δrp|=1.125e-10`, `|Q|=2.245e-12`; no raíces casi dobles |
| Algoritmos numéricos | `test_comparacion_scipy.py`; `bisect`, `brentq`, `bounded` con SciPy opcional | `xtol=rtol=1e-12` en raíces SciPy; `xatol=1e-9` en `log(rp)`; óptimos `atol_rp=1e-6`, `rtol_rp=2e-6`; trabajo `1e-8+1e-10·escala` kJ/kg; eta `1e-10+1e-10|eta_ref|` | Tarea 1.3: trabajo máximo `|Δrp|=7.212e-7`; rendimiento `1.747e-6`; `success` no basta sin viabilidad; sin SciPy, seis omisiones |
| Convergencia | `test_convergencia_numerica.py`; `sqrt(2)`, Q analítica, óptimos analíticos | Anchura de bisección se divide por dos; en 3 mallas de trabajo `|Δrp|/rp_ref≤2e-7`, `|ΔW|≤1e-9 kJ/kg`; paradas/log y límites de iteraciones | Tarea 1.4: 17–513 muestras y `1e-5` a `1e-11`; 257 razonables, 100 iteraciones bastaron en casos probados; ni mejora monótona ni garantía general |
| Invariantes | `test_invariantes_fisicos.py`; `cp·ΔT`, primera ley, escalados `cp`/`p1` | `atol_E=1e-10 kJ/kg`, `rtol=2e-12`; residuo frente a escala, no frente a cero relativo | Tarea 1.5: máximo residuo `2.842e-13 kJ/kg`, energía `4.547e-13 kJ/kg`; invariantes del **modelo** constante, no de cualquier motor |
| Casos especiales | `test_viabilidad.py`, `test_verificacion_raices.py`, `test_optimizacion_rendimiento.py`, `test_convergencia_numerica.py` | Sin dominio: `intervalo=()` y ningún máximo motor; frontera/banda: sin rendimiento; ideal B: supremo excluido; errores de representación separados | Historial de tareas 1.2–1.5 y casos B12/Ø medidos aquí; no se estudian exhaustivamente discriminantes casi nulos ni extremos de máquina |

La **suite completa nueva** confirma que esas pruebas y las regresiones históricas funcionan juntas en el entorno descrito; no recalcula para este documento todas las estadísticas máximas de los experimentos históricos. Las tolerancias de posición de los máximos **no** son garantías derivadas automáticamente de `tolerancia_log`, porque el máximo puede ser plano.

## 5. Compatibilidad y regresión final

**Ejecución única real el 22/10/2026:**

```text
Linux-6.18.55-x86_64-with-glibc2.39; Python 3.12.14
numpy 2.5.4; matplotlib 3.11.2; Flask 3.1.3; Jinja2 3.1.6
SciPy 1.17.0 (instalación temporal, opcional)
MPLCONFIGDIR=/tmp/brayton_etapa_6_mpl /tmp/brayton_etapa_6_venv/bin/python -B -m unittest discover -s tests -q
Ran 215 tests in 69.358s
OK
```

**215 superadas, 0 fallidas, 0 omitidas, 0 errores de importación.** `unittest` mide tiempo de ejecución de pruebas, no un benchmark estable. Se instaló `requirements.txt` en `/tmp/brayton_etapa_6_venv` y SciPy 1.17.0 sólo en ese entorno. La suite **no se repitió** tras el resultado.

| Compatibilidad comprobada | Evidencia en esta etapa | Alcance |
|---|---|---|
| Contratos públicos de ciclo, viabilidad, bisección y optimizadores | Firmas inspeccionadas; llamadas reales de `evaluar_punto`, `calcular_dominios`, `optimizar_trabajo_neto` y `optimizar_rendimiento`; suite completa | API presente, sin cambio de producción en las tareas 1.1–1.5 |
| SciPy no es necesario para el simulador | Sólo `tests/test_comparacion_scipy.py` importa SciPy; ensayo focalizado bloqueando su importación: importación de `main`, `web_app`, métodos físicos y cálculo de ciclos ideal/no ideal **correctos** | Bloqueo simulado en Linux; no simula todos los posibles fallos de instalación |
| Comparaciones sin SciPy | Ensayo focalizado separado: `8` métodos, `2` correctos, `6` omitidos, `0` fallos/errores | Omisiones informadas, no contadas dentro de las 215 correctas de la suite con SciPy |
| Flask, informes y contenido autónomo | Suite completa incluye `test_web_app.py`, `test_reporting.py`, `test_dashboard.py`, `test_integracion_rendimiento.py` y pruebas educativas | Cliente Flask y temporales; no hubo inspección visual ni ejecución de navegador en esta etapa |
| Interfaz sin cambios por la nueva Fase 1 | `git diff --name-only 27d4519..57da73d` sólo lista cinco archivos de tests y dos documentos; no cambian `main.py`, `web_app.py`, `templates/`, `static/` | Verificación de Git, complementaria a los tests de HTML |
| Puntos no motores | Casos Ø/B12 calculados aquí más pruebas de viabilidad e integración: motivo correcto, `rendimiento=None`, sin máximos falsos | El estado algebraico puede ser representable aunque no admisible como motor |

**Limitación de plataforma:** la ejecución se hizo **en Linux**, no en Windows ni macOS. Las instrucciones de PowerShell se ofrecen para reproducción, **no** como resultado de una prueba realizada en Windows. Las pruebas de informes existentes no equivalen a regenerar todos los gráficos ni a inspeccionar visores reales.

## 6. Interpretación científica, límites y siguiente revisión

- **Verificación del software:** la implementación resuelve con la precisión observada las ecuaciones y restricciones de su **propio modelo**. Referencias analíticas y SciPy permiten detectar errores de programación o de métodos numéricos; la primera ley y los cambios de escala comprueban consistencia interna.
- **Validación física:** requeriría confrontar las hipótesis y predicciones con mediciones de motores, mapas reales de componentes o modelos externos adecuados. **No se ha efectuado validación experimental** y no se puede llamar al simulador modelo predictivo de alta fidelidad.
- **Límites pendientes:** `cp` y `gamma` constantes, eficiencias/pérdida de presión prescritas, sin combustión o caudal modelado; estudio futuro de raíces casi dobles, dominios muy estrechos y límites de representación; datos independientes para validar físicamente. Los estudios 1.3–1.4 no justifican cambiar por ahora los controles predeterminados (`257`, `1e-9`, `100`).

**Valoración para revisión:** los ocho criterios de cierre solicitados se satisfacen **para el alcance ejecutado en Linux**, con la limitación explícita de Windows no probado y validación física ausente. Por tanto se **propone** dar por cerrada técnicamente la nueva Fase 1 tras revisión del usuario. Este documento y los enlaces docentes quedan **pendientes de commit**; no se declara publicada la Etapa 6 ni se empieza otra fase.
