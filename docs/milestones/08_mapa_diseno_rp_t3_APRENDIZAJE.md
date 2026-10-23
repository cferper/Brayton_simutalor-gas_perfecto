# Fase 5 — Aprendizaje del mapa bidimensional rp–T3

Documentación del 21 de octubre de 2026. Base verificada `b6fdfbeb5aa63605734258449f05a9ff3f964946`, merge del rediseño; rama `feature/fase-5-mapa-rp-t3`, inicialmente limpia. Fase actual sin commit. No se altera el historial ni se desarrolla otra fase.

## 1. Del caso individual al espacio de diseño

Antes existían 123 pruebas, casos individuales, dominios abiertos, máximos A/B y sensibilidad OFAT. Un mapa pregunta qué ocurre al variar simultáneamente rp y T3 manteniendo T1, p1, cp, gamma, eta_c, eta_t y pérdida relativa. No añade física. A maximiza trabajo específico; B maximiza rendimiento cuando existe máximo interior. Con equipos reversibles y sin pérdida, B es un supremo no alcanzado: se conserva su valor límite, no se dibuja como un punto operativo.

**INTERPRETACIÓN FÍSICA.** Se reutilizan `evaluar_punto`, `calcular_dominios` y candidatos/contrastes anteriores a través de `sensibilidad.evaluar_muestra`. No se vuelven a escribir las ecuaciones de temperaturas o balances. Trabajo y calor conservan signo en celdas no motoras, mientras eta es NaN allí. Compresión, expansión, Qin positivo y W positivo siguen siendo condiciones simultáneas con las tolerancias existentes. Un dominio vacío es un resultado físico, no un formulario inválido; un `ErrorNumerico` es una limitación de representación y no prueba de inviabilidad.

## 2. Mallas, índices y máscaras

**PYTHON.** `rp` y `T3` son ejes 1D. Los resultados tienen forma `(n_T3,n_rp)`; `W[i,j]` corresponde exactamente a `T3[i]` y `rp[j]`. No se transponen para dibujar. `np.linspace` reparte diferencias uniformes; `np.geomspace` reparte razones uniformes y requiere valores positivos. Los extremos deben ser distinguibles en coma flotante.

```python
import numpy as np
from main import PARAMETROS_PREDETERMINADOS
from mapa_diseno import analizar_mapa

estudio = analizar_mapa(PARAMETROS_PREDETERMINADOS, n_rp=9, n_T3=5)
W = estudio['matrices']['trabajo_neto']
motor = estudio['mascaras']['viable']
print(W.shape)                         # (5, 9)
W_motor = np.ma.array(W, mask=~motor)
```

Una máscara booleana señala disponibilidad: `True` en `motor` significa punto admisible; `~motor` invierte los booleanos y se usa como máscara de exclusión. Un array enmascarado retiene los valores originales pero impide colorear prestaciones excluidas. NaN significa no disponible, nunca cero. La matriz `motivos` tiene dtype object porque cada casilla contiene una tupla de razones, de longitud variable. Los estados completos se conservan en `filas[i]['puntos'][j]`.

## 3. Funciones, contratos y ejecución

Firmas y contratos de `mapa_diseno.py`; las configuraciones son dict, referencia es el dict de nueve escalares del simulador. T3/T1 [K], rp y eficiencias sin dimensión, cp [J/(kg·K)], p1 [kPa], W/Qin [kJ/kg]. Eta de los evaluadores es fracción, en `matrices` y gráficas es %. Ninguna función de presentación introduce ecuaciones.

| Firma completa | Contrato y relaciones |
|---|---|
| `validar_configuracion(referencia, rp_min=1., rp_max=100., T3_min=600., T3_max=2000., n_rp=100, n_T3=80, escala='log', cortes=())` | Devuelve dict normalizado; llama `argumentos_fisicos` y `validar_parametros`; Flask y `analizar_mapa` la llaman. Límites finitos, rp positiva ordenada, T1<T3min<T3max; enteros 3–401, hasta 20000 celdas, escala lineal/log, hasta cinco cortes incluidos. ValueError si falla. Cortes vacíos proponen extremos y centro. |
| `crear_malla(configuracion)` | Devuelve `(rp,T3)` como arrays 1D; la llama `analizar_mapa`; NumPy crea ejes. Rechaza pasos indistinguibles con ValueError. Ejemplo: `crear_malla(validar_configuracion(p,n_rp=3,n_T3=3))`. |
| `evaluar_fila(referencia, temperatura, relaciones, verificar=False)` | Devuelve dict `T3/muestra/puntos`. Llama `evaluar_muestra` una vez y `evaluar_punto` por columna. La llaman análisis y cortes. Captura sólo ErrorNumerico por celda (NaN y motivo), no RuntimeError ni defectos del programa. Ejemplo: `evaluar_fila(p,1600,[1,10,100])`. |
| `obtener_mascaras(filas)` | Devuelve dict de dos matrices bool: viable y limite_numerico. La llama análisis, sin otras llamadas propias; comprensión anidada sigue filas y puntos. Ejemplo: `obtener_mascaras([fila])` produce forma `(1,n_rp)`. |
| `extraer_fronteras(filas)` | Devuelve cuatro arrays de rp: inferior/superior motor, expansión y calor. Sin resolver otra vez dominios; análisis la llama. Sin dominio motor, fronteras motoras NaN; sin dominio calculable, todas NaN. Ejemplo: `extraer_fronteras([fila])['inferior']`. |
| `obtener_trayectorias(filas)` | Devuelve dict A/B con registros y arrays rp; no llama física, la llama análisis. Sólo `disponible` produce rp finita. Registros conservan estado, ciclo, supremo y contraste. Ejemplo: `obtener_trayectorias([fila])['B']['registros'][0]`. |
| `extraer_cortes(estudio, temperaturas)` | Devuelve lista de filas; reutiliza coincidencias exactas o llama `evaluar_fila` para nuevas T3. La llama análisis. Valida hasta cinco T3 finitas incluidas; ValueError fuera de rango. Ejemplo: `extraer_cortes(e,[1600])`. |
| `analizar_mapa(referencia, **configuracion)` | Orquesta validación, ejes, filas, máscaras, fronteras, trayectorias y cortes; devuelve estudio dict y segundos de cálculo. La llama `ejecutar_mapa`. `**` expande controles por nombre; `.copy()` evita modificar referencia. Ejemplo inicial en §2. |
| `preparar_resultados(estudio)` | Devuelve prestaciones enmascaradas y recuentos motores/celdas/límites numéricos, sin recalcular. La llaman gráficas y reporting. Ejemplo: `preparar_resultados(e)['motores']`. |
| `crear_graficas_mapa(estudio)` | Devuelve dict nombre→bytes PNG, tres mapas más un PNG de dos ejes por corte. Llama preparación; la llama ejecución. `try/finally` cierra cada figura incluso ante error. Ejemplo: `crear_graficas_mapa(e)['mapa_viabilidad.png']`. |
| `ejecutar_mapa(carpeta_salida, parametros, **configuracion)` | Devuelve Path del HTML guardado. Llama análisis, gráficas, reporting/versión Git/guardado; Flask la llama. Mide cálculo y preparación; propaga errores de E/S, contrato y programa. Ejemplo: `ejecutar_mapa(carpeta_temporal,p,n_rp=9,n_T3=5)`. |
| `reporting.crear_informe_mapa_html(estudio, imagenes, fecha, version_git)` | Devuelve HTML str con marcas de informe completo; datetime y versión Git dict. Llama preparación, imagen/tabla/plegable y renderizador; la llama ejecución. Registra tiempo HTML en el estudio. KeyError por estructuras incompletas, ValueError por PNG inválido/JSON no finito, errores E/S de recursos propagan. Ejemplo: `crear_informe_mapa_html(e,imagenes,fecha,version)`. |

El flujo nuevo es formulario → `web_app.index` → validación → `ejecutar_mapa` → estudio → PNG en memoria → HTML → publicación/retención → redirección a la vista. No cambia `main.py`. Los módulos de física, ambos optimizadores y sensibilidad permanecen idénticos a la base.

## 4. Óptimos, fronteras y refinamiento

Un dominio por fila se obtiene en `evaluar_muestra`; no se calcula por celda. A/B reutilizan candidatos analíticos con comprobación contra dominio y evaluación física. Sólo filas primera, central y última solicitan contraste numérico independiente, que puede recalcular dominios internamente. Los cortes adicionales tienen su propio dominio, sin contrastes completos repetidos. Esta precisión es independiente de las columnas: refinar de 9 a 41 columnas conserva las rp óptimas.

**INTERPRETACIÓN.** Una ventana 1–100 sólo decide qué mostrar. El máximo físico puede estar en rp>100; no se sustituye por 100 ni por el píxel más brillante. Las curvas visuales sustituyen por NaN los máximos fuera de vista, sin cambiar los registros físicos. La clasificación distingue disponible, sin_dominio, supremo_no_alcanzado y limite_numerico.

`pcolormesh(..., shading='nearest')` pinta celdas sin interpolar contornos entre muestras. El gris queda sin prestaciones motoras. Las líneas de frontera proceden de `calcular_dominios`, no de bordes de píxeles. Una malla más fina reduce la incertidumbre visual sobre la región, sin modificar las ecuaciones ni las tolerancias físicas. Un corte usa las columnas del mapa y una temperatura exacta, aunque no coincida con una fila; sólo dibuja puntos viables y NaN corta los huecos. Marcas A/B y bandas de dominio permanecen independientes del muestreo.

## 5. Dashboard y autonomía del HTML

Se añade la séptima sección, sin reconstruir las anteriores. Los nueve parámetros físicos conservan sus nombres, unidades y validación. Seis controles de malla, escala y lista de hasta cinco cortes se envían sólo con la acción mapa. `web_app.index` valida, genera y redirige; `listar_informes` identifica el estudio; `ver_informe` recupera configuración/entradas. `dashboard.separar_presentacion` acepta un panel mapa opcional: un informe anterior conserva sus tres paneles originales.

Los tres botones reutilizan el visor accesible existente. El selector de cortes sólo oculta/muestra PNG ya calculados; no llama al servidor ni optimiza. Sin JS, todos los mapas/cortes siguen visibles; con JS, sólo la selección está visible. La tabla A/B está plegada por defecto. Informes ofrece consulta/descarga. Las vistas antiguas y archivos guardados no se reescriben.

CSS, JS, fuentes IBM Plex y SVG se incrustan igual que antes; PNG Base64, supuestos y Git están incluidos. La política de cuatro informes sigue centralizada en `guardar_informe_html`. En autónomo, los controles de cálculo se deshabilitan: ver resultados no requiere Flask; calcular otro mapa sí requiere el servidor. Los tiempos son segundos de reloj con `perf_counter`, no carga de CPU ni validación de rendimiento de otro ordenador.

## 6. Resultados y verificación de la iteración del 21 de octubre

Caso predeterminado: rp 1–100 log, T3 600–2000 K, 100 columnas × 80 filas: 6482/8000 celdas motoras; 0 límites numéricos. Cortes 600/1600/2000 K. Cálculo 0.146487 s, cálculo + seis figuras 3.380705 s, HTML y guardado 0.379926 s, total 3.760633 s. Medida orientativa de esta revisión.

A T3=1600 K: A rp=12.89505167, W=373.21082748 kJ/kg, eta=39.21261442 %, Qin=951.76216374 kJ/kg. B rp=35.45232357, W=313.73891526 kJ/kg, eta=43.89310716 %, Qin=714.77946206 kJ/kg. Concuerdan con los cálculos individuales anteriores.

Con eta_c=.6, eta_t=.7, delta=.2 y malla 30×15: 125/450 motores, seis filas sin dominio motor (0.025732 s de cálculo). Reversible, misma malla: 399/450 motores, ninguna fila vacía; B supremo no alcanzado (0.022664 s).

21 pruebas específicas superadas en 5.171 s: dimensiones, rangos/escalas/límites, clasificación/motivos, coincidencia escalar, filas vacías, reversible/supremo, trayectorias/contrastes, refinamiento, óptimos fuera de vista, cortes, límites numéricos frente a errores de programa, un dominio por fila, máscaras/sin contourf, PNG, HTML, retención y Flask/descarga. Se conservan los 123 métodos anteriores, ajustando sólo dos conteos de controles de formulario de 12 a 18.

Verificación inicial del mapa: **144/144 OK en 96.679 s**, con `python -B -m unittest discover -s tests -q`. Se ejecutó fuera del sandbox para evitar los errores de permisos temporales ya conocidos; no fue necesario modificar física ni optimizadores. Una comparación AST con la base confirma que se conservan los 123 métodos anteriores. Pruebas e informes de revisión usan carpetas temporales o de revisión fuera de outputs/ del proyecto. La verificación es interna, no validación experimental.

Revisión real en navegador con Flask aislado en 127.0.0.1:5015: envío de un mapa 13×5 (46/65 motores), pestañas Trabajo/Rendimiento/Viabilidad, selector de corte 600→1600 K, modal y Escape con retorno de foco. Simulación normal: siete PNG; OFAT de T3 200–1600 K, cinco muestras: R tres disponibles, A/B cuatro, tres PNG. Ancho DOM 1204 px dentro de viewport 1219 px; sin desbordamiento horizontal. Captura de viabilidad guardada fuera del repositorio. Recursos autónomos y descarga comprobados mediante pruebas; no se afirma apertura interactiva file://, que la política del navegador integrado bloquea. Tampoco se afirma una revisión móvil adicional.

### Iteración del 21 de octubre de 2026 — informes educativos

Se conserva la Fase 5 anterior y sus 144 pruebas; esta mejora sólo cambia presentación. Base Git y rama siguen siendo los del inicio de esta guía, con el mapa y rediseño pendientes de commit. Los informes normales, OFAT y mapa comparten ahora introducción y glosario en la plantilla existente, con textos técnicos estáticos en `dashboard.py`. Los parámetros y conclusiones se insertan con f-strings sencillas, sin IA, nuevas dependencias ni generación compleja de explicaciones. Los informes previos no se modifican.

**INGENIERÍA.** Se explican magnitudes/unidades, los siete PNG normales (incluidos los procesos exclusivamente ideales T-s/P-v), las tres gráficas OFAT y los tres mapas. A maximiza kJ/kg y B la fracción del calor convertida en trabajo: son objetivos distintos. Se conserva la distinción máximo/supremo/dominio vacío/límite numérico. El texto del corte aparece una sola vez junto al selector. Los objetivos del mapa se añaden dentro del desplegable ya existente para evitar alargar innecesariamente la vista principal.

OFAT identifica automáticamente parámetro, unidad, rango, muestras y valores fijos; rp se explica aparte: consigna en R, ajustada en A/B. La normalización S=(x/Y)dY/dx es local y relativa, no un cambio en puntos porcentuales; se informa de su falta de fiabilidad o punto motor. Las observaciones finales normales usan W, rp y diferencias A/B calculadas; OFAT resume disponibilidad por escenario; el mapa cuenta celdas/temperaturas disponibles, filas vacías, supremos y óptimos fuera de vista. No se afirman tendencias de T3 sin comprobarlas.

**PYTHON.** Tres helpers pequeños, sin cálculos físicos:

- `bloque_educativo(titulo, texto)`: dos str planos → tarjeta HTML str; escapa ambos. Lo llaman `terminar_informe` y `crear_informe_mapa_html`; no llama funciones propias. Tipos inválidos propagan. Ejemplo: `bloque_educativo('Objetivo','A maximiza trabajo específico.')`.
- `conclusiones_html(observaciones)`: iterable de str ya obtenidos de datos → HTML con hasta cuatro observaciones escapadas. Usa lista, `[:4]` y `join`; sin entradas informa de la limitación. Mismos llamadores; sin otras llamadas propias. Ejemplo: `conclusiones_html(['No hay máximo B alcanzado.'])`.
- `parametros_fijos_texto(parametros, variables)`: dict de nueve entradas y colección de claves excluidas → str de valores/unidades no variables. Lo llama `terminar_informe` para OFAT. T [K], p1 [kPa], cp [J/(kg·K)], eficiencias/delta en fracción y rp/gamma sin dimensión. Filtrado de diccionario, alias delta y formato `:g`; claves/valores fuera de contrato propagan errores. Ejemplo: `parametros_fijos_texto(p,('T3','relacion_presiones'))` conserva siete valores fijos.

`reporting.imagen_html(imagen, titulo, explicacion=None)` amplía la firma previa de dos argumentos: PNG bytes y textos str → figure str, con párrafo opcional escapado. Conserva firma PNG y ValueError si es inválida. La llaman los creadores de informes; no calcula física. Ejemplo: `imagen_html(png,'Mapa de trabajo','X: rp; Y: T3 [K].')`. La conversión Base64 no cambia. Los contratos completos actuales están en walkthrough §§4.21 y 4.43.

`renderizar_dashboard` no cambia firma: pasa introducción/glosario y un booleano de presencia de informe a Jinja. `visor_graficas` añade texto por nombre de PNG a sus figuras; `terminar_informe` añade contexto y conclusiones; `crear_informe_mapa_html` reutiliza los mismos helpers/textos. La vista Flask recupera los mismos paneles, sin duplicarlos. El glosario queda en Ayuda y enlazado desde la introducción. No cambian ecuaciones, optimizadores, sensibilidad, mapa, CSS ni JavaScript.

16 pruebas de presentación superadas en la última comprobación de módulo en 7.443 s. Incluyen los tres tipos de informe, parámetros fijos/variables, supremo reversible, dominio vacío, ventana recortada, signos de las diferencias A/B, escape y autonomía/Flask. En una primera comprobación se corrigió una fixture que reutilizaba el mismo PNG para tres gráficas OFAT: la presentación existente identifica figuras por su PNG, por lo que la fixture debe usar PNG distintos. No fue un fallo del cálculo. Última verificación completa: **160/160 OK en 239.457 s** (144 previas y 16 educativas); se distinguen así los resultados actuales de las comprobaciones iniciales.

## 7. Ejercicios

1. Localiza `W[2,3]`, imprime T3/rp correspondientes y compara con `evaluar_punto`. ¿Por qué invertir índices cambia el caso?
2. Refina n_rp de 9 a 41 con las mismas T3: compara nodos comunes, recuentos y trayectorias A/B. Explica por qué los recuentos no deben ser iguales.
3. Reduce eficiencias y eleva pérdida. Busca filas sin dominio y distingue negativo calculable de rendimiento no disponible.
4. Usa el caso reversible. Comprueba que existe A, B no se alcanza y su supremo es un límite, no un punto que deba colorearse.
5. Acota la ventana a rp 1–3 con T3 4000–10000 K. Encuentra óptimos fuera de vista en los registros; explica por qué el borde no es el máximo físico.

## 8. Limitaciones y estado Git

Sin nueva física, tolerancias o dependencias. Límite de 20000 celdas y cinco cortes por experiencia local; proceso síncrono, sin cancelación ni cálculo de otro caso en el archivo HTML. El coloreado es discreto y el muestreo de trayectorias en T3 es finito. Los cortes pueden ser gruesos aunque sus óptimos sean precisos. Se distingue en datos el límite numérico; el gris de los mapas lo agrupa con no motor y el resumen informa su recuento.

Rama de trabajo `feature/fase-5-mapa-rp-t3`, base `b6fdfbeb5aa63605734258449f05a9ff3f964946`. Código y documentación pendientes de commit para revisión. No se modifica `zip.zip` ni se realizan operaciones de publicación o cambio de rama.
