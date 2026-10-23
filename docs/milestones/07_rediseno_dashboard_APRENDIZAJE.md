# Dashboard técnico — guía educativa independiente del rediseño

Documento del **21 de octubre de 2026**. Este trabajo reorganiza la presentación de las Fases 1–4; no es la Fase 5 termodinámica. El [manual actual §4.41](../../CODE_WALKTHROUGH.md#441-dashboard-técnico-independiente--presentación-sin-cambios-físicos) explica los contratos dentro del conjunto; el [milestone](07_rediseno_dashboard.md) resume el avance.

## A. Estado inicial y finalidad

Base comprobada: `ac37b9e0b93bcc0449e59fe04d5cfecb082f70ad`, igual en main y origin/main. Incluye cierres de Fases 1–4 y 108 pruebas. Desde la rama local de Fase 5, todavía sin desarrollo, se creó la rama autorizada `feature/rediseno-dashboard`. El único archivo inicial sin seguimiento era `zip.zip`, personal: el usuario autorizó expresamente dejarlo intacto y fuera del proyecto. No se modifica ni añade a Git.

El problema era de lectura: informes muy largos con imágenes verticales dificultaban comparar resultados. La solución es separar entradas, indicadores, decisiones, análisis OFAT, trazabilidad y ayuda. No se cambia ninguna ecuación ni método: los resultados de los optimizadores siguen llegando desde el mismo cálculo, con las mismas unidades y restricciones.

### Iteración del 21 de octubre — implementación completa y revisión

Se crea una capa de presentación compartida, se trasladan los controles a seis secciones y se incrustan sus recursos en informes autónomos. La primera suite pasa 123 pruebas. La revisión en navegador detecta que los enlaces nativos de sección podían producir saltos al ancla; se usa history.pushState con foco preventScroll, conservando fragmentos y Atrás/Adelante. Los conteos OFAT se presentan como enteros y separan inviabilidad física, supremo y límite numérico. Se vuelve a ejecutar la suite completa con estos ajustes. Verificación final: 123/123 pruebas correctas en 70.814 s; se conservan las 108 previas y se añaden 15 de dashboard.

## B. Archivos y responsabilidades

| Archivo | Responsabilidad |
|---|---|
| `dashboard.py`, nuevo | Componer presentación, recursos, KPI, visores y metadatos sin física |
| `templates/index.html` | Una plantilla para dashboard local e informe autónomo |
| `static/style.css` | Paleta técnica, tipografía, sidebar, tarjetas, tablas y adaptación responsive |
| `static/dashboard.js`, nuevo | Navegación progresiva, pestañas, teclado, modal y rangos sugeridos |
| `static/fonts/`, nuevo | Tres WOFF2 IBM Plex sin modificar, OFL y procedencia fijada a commit upstream |
| `static/images/`, nuevo | SVG geométrico original del motor y licencia CC0 |
| `reporting.py` | Mantiene tablas/datos técnicos y los entrega al nuevo compositor antes de guardar |
| `web_app.py` | Renderiza dashboard, recupera entradas de informes, lista historial y sirve dos documentos autorizados |
| `tests/test_dashboard.py`, nuevo | 15 pruebas estáticas y HTTP; no pretende probar interacción real |
| `tests/test_reporting.py` y `test_sensibilidad.py` | Conservan métodos, ajustan clasificación de fragmentos internos y JS legítimo frente a texto escapado |
| README y walkthrough | Explican uso y versión actual |
| Los dos documentos 07 | Hito técnico y aprendizaje independiente |

`main.py`, `viabilidad.py`, `optimizacion.py`, `optimizacion_rendimiento.py`, `sensibilidad.py`, requirements y PNG históricos permanecen iguales a la base. Las guías de fases anteriores no se reescriben. Los informes anteriores tampoco se convierten ni se borran por el rediseño.

## C. Arquitectura y recorrido real

```text
Formulario único de nueve entradas + controles OFAT
  → validación anterior → main o ejecutar_sensibilidad
  → estados/optimización/PNG originales
  → reporting: tablas y explicaciones técnicas existentes
  → terminar_informe: KPI + visores + detalles + metadatos
  → plantilla compartida con recursos incrustados
  → guardar_informe_html: publicar primero, conservar cuatro después
```

En el navegador, un POST sigue redirigiendo con 303 al informe. La vista nueva recupera sus paneles y parámetros desde metadatos; convierte la pérdida a % para el campo y renderiza el formulario editable. La descarga sale antes de esta transformación y es exactamente el archivo guardado. No hay base de datos, cuentas, React ni una SPA que sustituya al servidor.

Las seis secciones son exactamente:

1. **Simulación:** nueve entradas, grupos Condiciones de entrada, Propiedades del fluido y Configuración y pérdidas.
2. **Resultados:** seis indicadores del caso **no ideal** actual, estado/rango motor, visor y estados/balances plegados.
3. **Optimización:** A/B y diferencias con unidades, pp distintos de cambios relativos.
4. **Sensibilidad:** configuración del mismo caso base, conteos, visor, elasticidades y tabla completa plegada.
5. **Informes:** archivos propios completos, ordenados por finalización, consulta/descarga y datos existentes.
6. **Ayuda:** contexto y limitaciones, referencias y rutas acotadas a README/walkthrough.

No se interpreta None como cero: si no hay máximo B alcanzado, se muestra No disponible y su motivo. Los conteos cero de muestras sí son números reales. Una consigna de rp no indica que exista motor; su representación diferenciada de Fase 4 permanece dentro del PNG original.

## D. Contratos de Python nuevos

Entradas físicas: las mismas nueve claves del modelo, T en K, p1 en kPa, cp en J/(kg·K), eficiencias y pérdida interna en fracción; energías en kJ/kg. `valores` de formulario usa pérdida en %. Estas funciones son auxiliares de presentación: no evalúan ecuaciones. Errores de tipo/contrato/archivos propagan; no se etiquetan como inviabilidad física.

| Firma completa | Argumentos y retorno | Llamadas, validación y ejemplo |
|---|---|---|
| `json_seguro(datos)` | Datos serializables finitos → str JSON ASCII, `<` y `&` escapados | La llama renderizador; sin llamadas propias. ValueError por NaN/inf, TypeError por objeto no serializable. `json_seguro({'x':'</script>'})` no cierra el script de datos. |
| `renderizar_dashboard(valores, *, contenidos=None, metadata=None, informes=(), errores=None, modo_local=True, informe_actual='', seccion_inicial='simulacion')` | Dict de entradas, paneles HTML controlados, metadatos, secuencia de fichas, errores, bool y sección → HTML str | Llama json_seguro y Jinja. La usan terminar_informe y rutas. Lee plantilla/CSS/JS/SVG/OFL; en autónomo añade WOFF2 Base64. Propaga errores de recursos. Ejemplo `renderizar_dashboard(valores_formulario())`. |
| `tarjeta_kpi(clave, etiqueta, valor, unidad, explicacion, decimales=3)` | Identificadores/textos str, número o None y precisión int → article HTML | Sin llamadas propias; la usa compositor. Escapa texto y distingue None. `tarjeta_kpi('W','Trabajo',None,'kJ/kg','Sin motor')`. Unidades explícitas, sin cálculo físico. |
| `plegable(titulo, contenido)` | Título str y HTML técnico ya escapado → details/summary cerrado | Sin llamadas propias; compositor la usa. `plegable('Estados',tabla_html(('T',),[(300,)]))`. No elimina contenido. |
| `separar_presentacion(contenido)` | HTML str → `(metadata,paneles)` o None | Sin llamadas propias; rutas/listado la usan. Valida JSON dict con dashboard=1 y marcadores de los tres paneles; no ejecuta scripts. Formato anterior o mal formado da None. `separar_presentacion(html_guardado)`. |
| `visor_graficas(legado, imagenes, sensibilidad=False)` | HTML técnico, dict de PNG bytes y bool → `(visor,detalles,cabecera)` str | Sin llamadas propias; compositor la usa. Exige conservar todos los PNG, ValueError si falta alguno. Usa asociación Base64 para clasificar, no posición inventada. Ejemplo dentro del compositor `visor_graficas(legado,imagenes)`. |
| `terminar_informe(legado, parametros, imagenes, fecha, version, *, noideal=None, barrido=None, optimizaciones=None, estudio_rendimiento=None, comparacion=None, sensibilidad=None)` | Presentación anterior y resultados ya calculados, datetime/Git → HTML autónomo str con marcas completas | Llama visor, tarjetas, plegables, renderizador. La usan ambos creadores de reporting. No calcula estados ni optimiza; deriva sólo presentación y conteos. Ejemplo de entrada real: `main(carpeta_de_prueba)` lleva a esta función. |
| `listar_informes()` | Sin argumentos; configuración Flask → lista de dict nombre/tipo/resumen/fecha/commit/mtime | Llama separar_presentacion; index/vista/errores la usan. Sólo patrón propio, regular sin symlink, UTF-8 y marcas; no escribe ni elimina. Metadatos históricos ausentes se indican. Carpeta inexistente → lista vacía. |
| `ver_documentacion(nombre)` | Nombre str → Response text/plain | Flask la llama; sólo README.md/CODE_WALKTHROUGH.md; demás 404. GET `/documentacion/README.md`. No es un explorador de rutas. |

`CAMPOS`/`GRUPOS` se trasladan al módulo compartido para evitar dos definiciones de formulario; web_app los importa y conserva su interfaz. Las firmas de creadores y funciones físicas existentes no cambian. `index()` sigue validando y ejecutando la acción elegida, pero renderiza mediante la capa compartida. `ver_informe(nombre)` conserva validaciones de ruta/marcas y descarga; añade recuperación de presentación sólo para informes nuevos. `error_interno(error)` mantiene estado 500 y valores introducidos.

### Ejemplo: cifras de A/B

Los indicadores toman `noideal['trabajo_neto']`, `noideal['rendimiento']`, `optimizaciones['noideal']['analitico']` y el estudio de rendimiento. En el caso predeterminado muestran W≈369.476, eta≈36.899 %, A≈373.211 kJ/kg y B≈43.893 %. Al cambiar T3 deben cambiar porque no hay cifras de referencia escritas como constantes de interfaz. Las pruebas sustituyen un resultado y exigen que cambie su tarjeta, sin alterar el algoritmo físico.

## E. HTML y CSS: conceptos que aprender

Una plantilla Jinja contiene variables y bucles; el navegador recibe HTML terminado. Una sola plantilla evita que formulario e informe evolucionen con estilos incompatibles. `|safe` sólo se usa para recursos propios y HTML cuyos textos ya fueron escapados; no convierte datos arbitrarios del usuario en HTML seguro.

CSS Grid crea columnas mediante `repeat(3,minmax(0,1fr))`. `1fr` reparte espacio; el mínimo cero permite encoger sin que una tabla o cifra larga ensanche el documento. `min-width:0` en tarjetas y `.table-wrap{overflow-x:auto}` contienen el desplazamiento dentro de tablas. No se oculta un desbordamiento para disimular datos cortados.

La sidebar ocupa 232 px en escritorio. Por debajo de 1150 px las tarjetas se distribuyen en dos columnas; bajo 760 px el menú es compacto y la columna principal usa todo el ancho; en teléfonos muy estrechos hay un KPI por fila. La preferencia `prefers-reduced-motion` evita movimientos innecesarios. Los controles tienen foco visible, etiquetas asociadas y texto de unidades.

La paleta solicitada se aplica a fondo, superficie, interacción, texto y bordes; verde/ámbar/rojo se reservan para disponibilidad y errores. IBM Plex Sans se usa para lectura y Mono para números/unidades. Procedencia verificable en `static/fonts/SOURCE.md`, licencia IBM SIL OFL 1.1 íntegra local e incrustada en autónomos. Los fallbacks son Segoe UI/Consolas/sistema si el motor no puede cargar WOFF2.

El motor SVG es propio, con geometrías sencillas de compresor, combustor, turbina y tobera, bajo CC0. Es decorativo y no a escala: una imagen de tobera no implementa empuje ni añade otro proceso al ciclo calculado.

## F. JavaScript ligero y accesibilidad

El script es una función autoejecutable que limita nombres al ámbito local. `const` conserva enlaces a arrays/elementos y `let` se usa para referencias que cambian. Los listeners reaccionan a acciones; no llaman Python ni una API de optimización.

- `activateSection(id,focus=false)` recibe nombre de sección y bool, activa un panel y aria-current; usa DOM, no retorna resultados físicos. La llaman navegación, fragmentos y validación nativa. `locationSection()` interpreta fragmentos como `#resultados/compromiso`, activa sección y pestaña; la llaman inicialización, hashchange/popstate y clics delegados.
- `selectTab(button)` es un cierre dentro de cada visor. Recibe botón, filtra los **mismos** figure mediante clases y actualiza ARIA/tabIndex. Lo llaman clic y teclas; no crea copias del PNG. Flechas/Home/End cambian la pestaña seleccionada. Sin JS, no hay clase js y todo sigue visible.
- `enlarge(figure,button)` recibe figura y disparador, copia su src ya presente al dialog y llama showModal. El navegador gestiona Escape y el foco modal; el evento close devuelve foco al botón. No descarga otro PNG ni calcula otro caso.
- Otros callbacks actualizan el menú, rangos sugeridos, estado de impresión y errores de validación. No exponen estado global de simulación. `history.pushState` mantiene URLs sin recargar ni provocar saltos al ancla; popstate permite Atrás/Adelante.

Los botones son reales, no textos simulando controles. Un informe sin JS conserva las seis secciones y todas las figuras; details/summary siguen desplegando tablas de forma nativa. Al imprimir con JS se abren detalles y después se restaura su estado. Sin JS se pueden abrir manualmente antes de imprimir.

## G. Informe autónomo, historial y seguridad

Las siete figuras normales se agrupan por **contenido real**: rendimiento ideal/comparado, trabajo ideal/comparado, T-s/P-v y compromiso W–eta. Todas muestra los mismos siete nodos, no otros siete. OFAT conserva tres figuras y exactamente sus máscaras/consigna, porque los bytes PNG se trasladan intactos.

`json_seguro` genera script de tipo application/json, inerte, con parámetros/fecha/Git y configuración OFAT. Escapar `<` impide que valores como `</script>` cierren esa etiqueta. Tres comentarios delimitan los paneles recuperables para Flask. No se ejecuta JSON con eval ni se guarda una copia del estado en globals o en una base de datos.

En autónomo CSS, JS, SVG y fuentes se incrustan; las figuras ya eran Base64. No hay CSS/JS de CDN. Los controles de ejecución se deshabilitan porque un archivo HTML no puede ejecutar Python: consultar no requiere servidor, generar otro resultado sí. La vista local reconstruye el formulario desde parámetros guardados; conserva la conversión única de delta a %.

El historial sólo enumera archivos propios completos, sin symlinks ni rutas arbitrarias. Los anteriores se sirven en su formato original y sus metadatos ausentes se identifican, sin inventarlos. `guardar_informe_html` no cambia: temporal exclusivo, publicación completa y después retención de cuatro entre ambos tipos. El listado no elimina informes ni altera su orden temporal.

## H. Verificación y límites de lo comprobado

Primera suite: **123/123 OK en 124.582 s**, con todas las 108 previas conservadas. Suite final: 123/123 pruebas correctas en 70.814 s; se conservan las 108 previas y se añaden 15 de dashboard. Comando:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Las 15 pruebas nuevas comprueban seis secciones, nueve parámetros sin duplicados, seis KPI correctos/cambiantes, None sin cero, B ausente por supremo, siete y tres PNG únicos, pestañas/plegables en HTML, recursos incrustados/licencias, JSON seguro, recuperación de parámetros, descarga idéntica, historial sólo lectura, compatibilidad anterior, navegación sin ejecución y acceso documental acotado. Tests estáticos de CSS/JS verifican contratos de marcado, **no** prueban por sí solos interactividad.

Comprobaciones reales realizadas en navegador: envío normal y redirección a Resultados; cambio de pestaña a compromiso; apertura del modal y cierre con Escape con foco de vuelta al disparador; comparación A/B con cifras dinámicas; envío OFAT con T3 mínimo 200 y 15 muestras, incluyendo muestras no disponibles; cambio a su pestaña rp. Se usa un servidor de revisión en 127.0.0.1:5015 y carpeta de informes aislada fuera del repositorio; el servidor habitual conserva 127.0.0.1:5000.

Viewport de escritorio 1440×1000 y móvil 393×852. La inspección DOM mostró ancho del contenido 378 px dentro de viewport ~394 px, sin scroll horizontal del documento. Se revisan también las tablas y navegación por teclado. El resultado del autónomo final y de la copia sin scripts se registra en las comprobaciones de cierre: se generaron informes finales autónomos y una copia sin scripts fuera del repositorio. La suite comprueba sus recursos incrustados, PNG, licencias y contenido accesible sin clase js. La apertura directa file:// fue bloqueada por la política del navegador integrado; no se eludió. No se afirma una prueba interactiva del archivo local ni de JavaScript deshabilitado: la interactividad real se comprobó en Flask local. No se afirma validación exhaustiva de todos los navegadores o un lector de pantalla.

Se compara la fuente de main, viabilidad, ambos optimizadores, sensibilidad y requirements con la base, normalizando sólo CRLF/LF; no cambian. Los seis PNG históricos coinciden byte a byte. Los métodos de prueba anteriores permanecen. La verificación interna no es validación contra un motor experimental.

### Revisión de cierre del 21 de octubre de 2026

Suite completa antes del commit: **123/123 OK en 93.985 s**. El primer intento dentro del sandbox terminó con errores de permisos al escribir y limpiar informes temporales; la ejecución fuera de esa restricción pasó sin cambios de código. Se verificaron de nuevo en Flask aislado la simulación normal, navegación, pestañas por teclado, tablas desplegables y OFAT de T3 entre 200 y 1600 K con cinco muestras (R: tres disponibles; A/B: cuatro). Las pruebas comprueban además descarga idéntica, retención de cuatro informes y ejecución directa de `main.py`, usando carpetas temporales. La apertura `file://` volvió a ser bloqueada por la política del navegador: se mantiene la limitación de revisión interactiva offline indicada arriba. Los módulos físicos y dependencias no tienen diferencias con la base. Se incluye también la regla de eficiencia de `AGENTS.md`, autorizada por el usuario. No se desarrolla Fase 5.

## I. Cinco ejercicios prácticos

1. Cambia T3 desde el formulario y compara el KPI de W con el informe anterior. Debe depender del nuevo cálculo, no de una constante HTML.
2. Usa Todas y luego Diagramas termodinámicos; cuenta nodos figure antes/después. Deben seguir siendo siete, aunque sólo dos sean visibles.
3. Recorre pestañas con Flechas/Home/End; abre Ampliar con teclado y cierra con Escape. Comprueba que el foco vuelve al botón y no se vuelve a ejecutar main.
4. Abre el autónomo sin conexión. Localiza estados/balances y metadatos. Explica por qué consultar funciona pero ejecutar requiere Flask.
5. Compara la tabla JSON de parámetros con los campos recuperados. Justifica por qué pérdida interna 0.05 se presenta como 5 %, y por qué un `<script>` dentro de un dato debe quedar escapado.

## J. Limitaciones y Git

Los informes históricos no se migran; algunos datos del índice no están disponibles. Sin JS hay más contenido vertical y la ampliación modal puede no existir en navegadores antiguos, aunque los PNG originales siguen accesibles. Las tablas anchas usan scroll interno por diseño. No se certifica compatibilidad con todos los motores de navegador, impresoras o tecnologías de asistencia.

La capa de presentación conserva el generador técnico anterior como fuente de detalles y luego compone el dashboard: esto evita perder información, a costa de una etapa intermedia de HTML en memoria. Si se cambian las estructuras técnicas, deben mantenerse sus marcadores y las pruebas de integridad. No se modifica la política ni concurrencia del historial.

Rama de desarrollo `feature/rediseno-dashboard`, base `ac37b9e0b93bcc0449e59fe04d5cfecb082f70ad`. El hash del commit de rediseño está **pendiente en el momento de redactar su contenido**; el cierre Git autorizado se verifica mediante el historial y el informe final, sin inventar el hash del commit que contendrá este documento. La rama de Fase 5 se preparará sin desarrollar sus funcionalidades. `zip.zip` no está presente en la comprobación de cierre y no se ha creado, modificado ni añadido.
