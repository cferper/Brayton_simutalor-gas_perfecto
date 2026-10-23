# Fase 6 — Aprendizaje de segunda ley y exergía

Documentación del 21 de octubre de 2026. Base verificada `174ce4fb9ff2a68880c3c452d82c7c179b7e058f`, con main/origin sincronizadas y 160 pruebas previas. Rama nueva autorizada `feature/fase-6-segunda-ley-exergia`. ZIP y respaldos locales conocidos quedan intactos; el proyecto estaba sin modificaciones al crear la rama. Fase actual sin commit.

## 1. Qué existía y qué se añade

Fases 1–5 ya resolvían los estados del gas, balances, viabilidad, óptimos A/B, OFAT y mapas. El T-s original era exclusivamente ideal. Ahora se estudian las irreversibilidades del compresor y la turbina, sin alterar ninguno de esos resultados. El cálculo normal recibe un T0 independiente y analiza los registros `referencia` que ya produce `evaluar_punto`: no vuelve a resolver el ciclo para obtener entropías.

La sección nueva reúne tres bloques educativos breves, dos tablas pequeñas, dos figuras SVG y un desplegable con el cambio de entropía en la cámara. Los siete PNG anteriores se conservan; el contador de PNG de la terminal sigue contando esos siete buffers. SVG añade calidad vectorial sin archivos externos ni nuevas dependencias.

## 2. Entropía relativa y segunda ley

**INGENIERÍA.** Para el gas ideal de cp y gamma constantes:

```text
R = cp (1 − 1/gamma)                              [J/(kg·K)]
s_j − s_i = [cp ln(Tj/Ti) − R ln(pj/pi)] / 1000    [kJ/(kg·K)]
s1 = 0
```

T debe estar en K; las presiones deben compartir unidad (aquí kPa), de modo que sus cocientes sean adimensionales. La referencia s1=0 es arbitraria: los números no son entropías absolutas. Se comparan diferencias y se mantienen separados ideal/no ideal. La ecuación de estado es la de [gas ideal y cambio de entropía, MIT](https://web.mit.edu/16.unified/OldFiles/www/SPRING/thermodynamics/notes/node39.html).

Para un equipo estacionario adiabático con una entrada/salida, el balance específico da s_gen=s_salida−s_entrada. Por tanto, compresor: s2−s1; turbina: s4−s3. Las eficiencias menores que uno aumentan la temperatura de salida del compresor y reducen el salto térmico útil de la turbina respecto a sus referencias isentrópicas. A condiciones de referencia fijas, esto aumenta la generación que cuantificamos; las pruebas contrastan ambos efectos.

**PYTHON.** `cambio_entropia` usa diferencias de logaritmos, por ejemplo `log(Tj)-log(Ti)`, para evitar desbordar o anular el cociente antes de tomar su logaritmo. El factor `/1000` convierte J a kJ. Entregamos un dict con términos de temperatura/presión y suma; así no perdemos el significado físico detrás de un único número.

La banda para generación es `1e-10*max(abs(s_entrada),abs(s_salida),cp/1000)`, en kJ/(kg·K). Evita interpretar cancelaciones de redondeo como violaciones físicas. Un negativo dentro de esa banda se presenta como cero, conservando `bruto` y `tolerancia`; un negativo mayor produce `InconsistenciaSegundaLey`. El análisis conserva las entropías diagnósticas y no publica destrucciones para ese modelo inconsistente. Esta tolerancia es numérica, no incertidumbre experimental.

## 3. Exergía y referencia ambiental

```text
eD,c = T0 s_gen,c         [kJ/kg]
eD,t = T0 s_gen,t         [kJ/kg]
suma cuantificada = eD,c + eD,t
```

Gouy–Stodola relaciona la destrucción de exergía con la generación de entropía y una referencia ambiental T0 uniforme; véase la exposición técnica de [NASA sobre entropía y trabajo perdido](https://github.com/nasa/turbo-design/blob/main/entropy_based_efficiency.md). En este proyecto sólo se cuantifican compresor y turbina. No es la destrucción total de exergía de la instalación, ni identifica directamente W_ideal−W_noideal sin balances y condiciones de referencia adicionales. No se introducen exergías absolutas de flujo ni eficiencia exergética global.

Cambiar T0 no altera estados, cp, gamma, eficiencias, calor, trabajo, óptimos o mapas: sólo multiplica las generaciones ya calculadas. `actualizar_T0` usa `deepcopy` para conservar el informe anterior; asigna las nuevas eD sin llamar ni al evaluador ni al cálculo de entropía. Las pruebas bloquean esas llamadas para verificar la reutilización.

## 4. Cambio en la cámara frente a generación

La cámara presenta `s3−s2` como cambio del fluido y separa `cp ln(T3/T2)/1000` y `−R ln(p3/p2)/1000`. Con pérdida de presión, el segundo término es positivo. Estos términos son una identidad entre estados; no constituyen por sí solos una generación total de entropía de la cámara.

Su balance requeriría conocer la entropía que entra con la transferencia de calor, incluidas temperaturas de frontera, o incorporar flujos/reactivos y un modelo de combustión. No se inventa una temperatura de fuente ni se suma este incremento a s_gen,c+s_gen,t. Tampoco se cuantifica el rechazo de calor ni se afirma un balance exergético global cerrado.

## 5. Funciones y contratos nuevos

Contratos comunes: números reales finitos, temperaturas [K], p [kPa], cp [J/(kg·K)], gamma adimensional; s [kJ/(kg·K)], eD [kJ/kg]. Los registros de estado son los de `evaluar_punto`, con `temperaturas`, `presiones`, `viable` y `motivos`. No se reclasifican mediante nuevas ecuaciones. Los diccionarios mal estructurados propagan KeyError/TypeError de programación; no se etiquetan como inviabilidad física.

| Firma completa | Uso, argumentos, retorno, errores y relaciones |
|---|---|
| `validar_referencia(T0)` | Real → float positivo finito [K]; ValueError para cero, negativos, no finitos o bool. La llaman main, rutas/ejecución y funciones de análisis/actualización; no llama funciones propias. Ejemplo: `validar_referencia(288.15)`. |
| `cambio_entropia(Ti, pi, Tj, pj, cp, gamma)` | Seis reales → dict `termica/presion/total`. ValueError para estados/propiedades inválidos; ErrorNumerico ante escala no representable o resultado no finito. La llama `analizar_estados`; usa log e isfinite. Ejemplo: `cambio_entropia(300,100,600,100,1005,1.4)`. |
| `generacion_adiabatica(s_entrada, s_salida, escala=1.)` | Reales en unidades de s → dict `valor/bruto/tolerancia`. ValueError por no finitos/escala no positiva, ErrorNumerico por diferencia infinita, InconsistenciaSegundaLey por negativo importante. La llama análisis de estados; no llama funciones propias. Ejemplo: `generacion_adiabatica(0,.08,1.005)`. |
| `analizar_estados(punto, cp, gamma, T0=288.15)` | Registro clasificado y propiedades → dict de estado, entropías, componentes, suma y cámara; conserva motivos motores originales. Llama validación, cambio y generación. Inconsistencia: retorna diagnóstico con entropías y motivo, sin eD; errores de entrada/números propagan al agregador. Ejemplo: `analizar_estados(punto,1005,1.4)`. |
| `analizar_segunda_ley(estados, cp, gamma, T0=288.15)` | Dict ideal/noideal → estudio con T0/cp/gamma/modelos. Llama validación y análisis por modelo; registra límites numéricos separadamente, sin ocultar entradas inválidas. La llaman main y ejecución diagnóstica. Ejemplo: `analizar_segunda_ley({'ideal':pi,'noideal':pn},1005,1.4)`. |
| `actualizar_T0(estudio, T0)` | Estudio y real → copia con T0 y eD nuevas. Validación y deepcopy; ErrorNumerico si desborda. Conserva modelos no cuantificables y no calcula física. La llama ejecución. Ejemplo: `actualizar_T0(e,300)`. |
| `crear_graficas_segunda_ley(estudio)` | Estudio → dict `estados_ts/exergia_componentes` con SVG str. La llama presentación; Matplotlib/StringIO, cierre en finally e identificadores separados entre SVG. No llama física. Ejemplo: `crear_graficas_segunda_ley(e)['estados_ts']`. |
| `ejecutar_segunda_ley(carpeta_salida, parametros, T0=288.15, estudio_previo=None)` | Path/str, dict de nueve parámetros, T0 y estudio opcional → Path del HTML. Con estudio previo llama sólo actualización; sin él evalúa ideal/noideal una vez y analiza, sin optimizadores/barridos. Llama reporting/Git/guardado. Flask la llama; errores numéricos/entrada/E/S se mantienen diferenciados. Ejemplo: `ejecutar_segunda_ley(d,p,300,e)`. |
| `web_app.estudio_conservado(nombre, parametros)` | Nombre propio str y dict físico → estudio previo o None. Comprueba patrón, ruta dentro de OUTPUTS_DIR, archivo no simbólico, marcas y parámetros idénticos; usa `separar_presentacion`, no física. Lo llama index. Ejemplo: `estudio_conservado(nombre,p)` dentro de configuración local. |
| `reporting.seccion_segunda_ley_html(estudio)` | Estudio → bloque HTML, dos SVG y tablas compactas. Llama gráficas, tablas y helpers educativos/plegable; la llaman informe específico y `terminar_informe`. Escapa textos dinámicos; no calcula estados. Ejemplo: `seccion_segunda_ley_html(e)`. |
| `reporting.crear_informe_segunda_ley_html(parametros, estudio, fecha, version)` | Dict físicos/estudio, datetime y Git dict → HTML autónomo con marcas. Llama sección, renderizador y helpers existentes; la llama ejecución. Propaga errores de contrato/E/S. Ejemplo: `crear_informe_segunda_ley_html(p,e,fecha,version)`. |

`InconsistenciaSegundaLey` deriva de ValueError para señalar una contradicción con la hipótesis adiabática, diferenciada del error numérico. No genera un resultado cero ficticio. Las funciones de cálculo no modifican los diccionarios de estados recibidos; la actualización profunda evita aliasing de diccionarios anidados.

## 6. Integración y recorrido de un ejemplo

1. `main(carpeta_salida=None,parametros=None,*,T0=288.15)` conserva los nueve parámetros físicos y sus cálculos; valida T0 y pasa el estudio calculado sobre `referencia` al informe normal. `*` hace T0 explícitamente nombrado.
2. `crear_informe_html(..., segunda_ley=None)` y `terminar_informe(..., segunda_ley=None)` añaden argumentos opcionales por nombre: las llamadas antiguas siguen funcionando. El panel opcional se guarda junto a metadatos del estudio; la plantilla añade la octava sección y el campo T0, separado de los parámetros físicos.
3. Flask muestra el informe recuperando el panel. Al pulsar actualizar, `estudio_conservado` sólo reutiliza un informe propio íntegro cuyos nueve parámetros coinciden; si se editan, calcula dos puntos nuevos. T0 no se pasa a OFAT ni al mapa.
4. El informe diagnóstico distingue motor/no motor, inconsistencia y límite numérico. T3<=T1 sigue siendo entrada inválida según el validador existente; una combinación matemática válida con W<=0 se permite como diagnóstico.
5. Las dos figuras SVG son autónomas, con glifos incrustados y ancho adaptable. Se conservan siete PNG originales y la retención compartida de cuatro informes. Cambiar T0 genera un informe sólo de segunda ley; no vuelve a dibujar los siete PNG ni a ejecutar óptimos. El archivo descargado no necesita servidor para consulta; nuevos cálculos sí.

## 7. Resultados y verificación del 21 de octubre de 2026

Caso base, T0=288.15 K. Ideal: s≈(0,0,1.0616782566,1.0616782566); ambas generaciones/destrucciones≈0. El valor bruto s2≈−1.11e−16 se conserva como redondeo, no se declara generación negativa importante.

No ideal: s=(0,0.0820509581,1.0764067597,1.1632558923) kJ/(kg·K). Compresor: s_gen=0.0820509581, eD=23.6429835754 kJ/kg. Turbina: s_gen=0.0868491326, eD=25.0255775665 kJ/kg. Suma de los dos=48.6685611419 kJ/kg.

Cámara: cambio del fluido=0.9943558016, contribución térmica=0.9796272985 y de presión=0.0147285031 kJ/(kg·K); ninguna se etiqueta como generación total de la cámara. T0=300 K produce suma=50.6700272170 kJ/kg, sin modificar estados.

Contraste analítico independiente en pruebas: con a=(gamma−1)/gamma, q=rp^a y r_exp=rp(1−delta), s_gen,c=(cp/1000)ln([1+(q−1)/eta_c]/q), s_gen,t=(cp/1000)ln([1−eta_t(1−r_exp^(−a))]r_exp^a). No usan el cálculo de entropía del módulo para formar el resultado esperado.

18 pruebas nuevas pasaron inicialmente en 2.591 s. Cubren estados/unidades/identidad, contraste independiente, reversibilidad, eficiencias, T0, cámara, no motor, inconsistencias, límites numéricos, dos SVG, Flask, descarga y reutilización sin reevaluación. Se conservan los 160 métodos anteriores; se actualizan dos expectativas de número de controles 18→19 y la expectativa de panel normal para incluir segunda ley. Suite completa final: **178/178 OK en 265.170 s**, mediante `python -B -m unittest discover -s tests -q`, fuera del sandbox por los permisos de archivos temporales. Verificación AST: los 160 métodos anteriores siguen presentes. Evaluadores, optimizadores, sensibilidad, mapas, dependencias y PNG históricos no tienen diferencias con la base; main sólo añade coordinación del análisis.

Revisión real desde Flask aislado en 127.0.0.1:5016: informe normal, sección Segunda ley, T0 288.15→300, suma 48.668561→50.670027, tablas y ambas figuras. Ancho DOM 1204 dentro de viewport 1219 px, sin desbordamiento horizontal. Informes/captura se guardan fuera del repositorio. No se afirma prueba interactiva file:// ni revisión móvil exhaustiva. Es verificación de código y consistencia física interna, no validación contra datos experimentales.

## 8. Cuatro ejercicios

1. Reconstruye s2 y s4 a partir de T,p del caso base, calculando R y convirtiendo J a kJ. Comprueba que cambiar la referencia s1 no cambia s_gen.
2. Fija eficiencias en uno y delta en cero: explica por qué compresor/turbina dan generación cero mientras s3−s2 sigue siendo positivo.
3. Duplica T0 con `actualizar_T0`: compara estados, entropías y eD. Explica por qué cambian las últimas sin cambiar el trabajo del ciclo.
4. Usa T3=400 K y rp=50 con los demás valores base. Identifica motivos de no motor, estudia las entropías y explica por qué ese diagnóstico no constituye una prestación motora.

## 9. Limitaciones y estado Git

### Revisión de integración educativa — 21 de octubre de 2026

Se revisaron las dos pestañas de las seis secciones técnicas, incluidas Sensibilidad y Mapa, sin recalcular informes del usuario. Se corrigieron dos interferencias demostradas en navegador: el selector educativo incluía los botones de gráficas anidadas, y un campo obligatorio podía quedar oculto al fallar la validación desde otra sección. Se limita el selector a la barra educativa directa y se abre la vista del campo mediante su relación ARIA. Se reutilizan los mismos nodos y valores; no se modifica la física. Cuatro expectativas de pruebas anteriores se adaptan a la retirada de la introducción global y al recuento separado de pestañas gráficas. Los contratos editoriales y la navegación actual están descritos en §4.41 del walkthrough.

Verificación de esta revisión: seis pruebas específicas OK; integración inicial 53 pruebas con cuatro fallos de expectativas antiguas; tras adaptar esas expectativas, diez pruebas específicas/corregidas OK. Única ejecución completa final: **184/184 OK en 125.071 s**, con `unittest discover -s tests -q`. Se comprobaron en navegador real los dos fallos antes/después, las seis parejas de pestañas, resúmenes, controles de Sensibilidad/Mapa, flechas/Home/End y conservación de T1=310 sin peticiones de cálculo. El servidor de revisión reutilizó un informe conservado en carpeta aislada y fue cerrado. La suite verifica HTML autónomo, descarga e integración Flask; no se afirma validación experimental ni revisión móvil exhaustiva.

No hay nuevas ecuaciones de estados, optimizadores, sensibilidad, mapas, propiedades variables, combustible, caudal o empuje. No se modelan transferencias térmicas con temperaturas de frontera; no se cierra la exergía de toda la instalación. La referencia de entropía es relativa y los SVG sólo conectan estados, sin resolver trayectorias irreversibles internas. La revisión numérica no es validación experimental.

Base `174ce4fb9ff2a68880c3c452d82c7c179b7e058f`, rama `feature/fase-6-segunda-ley-exergia`; código/documentación sin commit para revisión. Sin push, merge ni nuevas fases. Respaldos, zip.zip, outputs/ del usuario y PNG históricos intactos.
