# V.5 — Verificación de integración web, formularios, informes e historial

**Estado:** preparada para revisión humana, **sin commit ni publicación** (23/10/2026).
Repositorio `cferper/Brayton_simutalor`, rama `mejoras/verificacion-numerica`;
base comprobada `eae71fecab71ba6cd5877e0e81f4dd396c08cb43`. Trabajo realizado en
la copia independiente `brayton_v5_integracion_web/`, no en Windows.
No se modifica ningún archivo de producción, plantilla, estilo, JavaScript o dependencia.

## 1. Propósito y frontera de la verificación

La V.5 comprueba que la interfaz Flask transmite **las nueve entradas físicas correctas**
a cada ejecutor, distingue las cuatro acciones y sus configuraciones, presenta errores
sin generar informes falsos, guarda y recupera archivos de forma coherente, y reutiliza
Segunda Ley al modificar únicamente `T0` **si las nueve entradas coinciden**.
Complementa la termodinámica de V.1–V.4; no vuelve a demostrar las ecuaciones ni
compararlas con experimentos.

La prueba utiliza `Flask.test_client()`: ejercita en memoria las rutas HTTP,
el renderizado real de Jinja y la lógica de Flask **sin abrir un puerto ni un navegador**.
Las ejecuciones de las cuatro modalidades se realizan con el código real y se guardan
en `tempfile.TemporaryDirectory`. Para verificar el despacho sin cálculos innecesarios,
otros métodos sustituyen los cuatro ejecutores por `unittest.mock.patch.object`;
la validación de formularios sigue siendo la real. Las dos modalidades de prueba
no se confunden: los mocks comprueban argumentos, no resultados físicos.

## 2. Contrato de entradas, enrutamiento y resultados

| Acción enviada en `accion` | Función invocada | Configuración propia | `T0` |
|---|---|---|---|
| `normal` | `web_app.main` | Las nueve entradas; simulación completa | Positivo y finito, predeterminado 288,15 K |
| `sensibilidad` | `web_app.ejecutar_sensibilidad` | Parámetro OFAT, mínimo, máximo, muestras enteras | No se consulta en esta acción |
| `mapa` | `web_app.ejecutar_mapa` | Rangos rp/T3, resoluciones enteras, escala y cortes | No se consulta en esta acción |
| `segunda_ley` | `web_app.ejecutar_segunda_ley` | `T0` y estudio anterior compatible o `None` | Positivo y finito, predeterminado 288,15 K |

Campos físicos comunes: `T1` y `T3` [K], `p1` [kPa],
`cp` [J/(kg·K)], `gamma`, `relacion_presiones`, `eta_c`, `eta_t` y
`perdida_presion_combustor`. Son **nueve** entradas. En el HTML,
la pérdida de presión se introduce en **porcentaje**; por ejemplo `7.5`
se entrega a física como `0.075` (fracción). Los otros ocho campos conservan
su valor numérico. Para este caso se utilizaron
`T1=310`, `T3=1750`, `p1=110`, `cp=1020`,
`gamma=1.37`, `rp=8`, `eta_c=0.88`, `eta_t=0.91` y `delta=7.5 %`.

El POST correcto retorna **303 See Other** con la ruta del nuevo informe.
Una entrada rechazada produce **400**, conserva los valores facilitados en el formulario
y no invoca ejecutores. Una excepción no prevista del mapa produce **500**,
se registra técnicamente y no aparece en la pantalla como «inviabilidad física»:
ni el mensaje interno ni un informe ficticio llegan al usuario.

Comprobaciones de rechazo: campo obligatorio vacío; `NaN`; mínimos/máximos
OFAT invertidos; referencia de sensibilidad `T3 ≤ T1`; resolución del mapa
por debajo del mínimo; corte de mapa no finito; `T0=inf` para Segunda Ley.
Son **siete casos dentro de un único método con `subTest`**,
no siete métodos adicionales. Tanto OFAT como el mapa admiten `T0`
textual inválido porque no lo utilizan.

## 3. Ejecuciones integradas y persistencia

Se realizaron **cuatro POST reales** con las mismas nueve entradas:
simulación normal, sensibilidad OFAT `T3=1200…1900 K` (3 muestras),
mapa `rp=2…18` y `T3=1200…1900 K` (malla 3×3, escala lineal,
cortes 1300 y 1800 K), y Segunda Ley con `T0=298.15 K`.
Todas devolvieron 303, crearon un HTML válido y declararon el tipo esperado.
Se extrajeron los metadatos con `dashboard.separar_presentacion` y
se comprobó la conservación exacta de las nueve entradas y la configuración propia.
Los HTML anteriores se compararon **byte a byte** tras cada ejecución;
quedaron exactamente cuatro archivos de informe, sin modificación de los anteriores.
El contenido termodinámico y las gráficas de estas ejecuciones no se vuelven a
verificar numéricamente: corresponden a las etapas previas.

Para estudiar el historial se prepararon además **informes de prueba sintéticos**
con marcas de inicio/fin, paneles y metadatos propios, y uno de formato anterior.
Las pruebas sintéticas sirven para cubrir selección, recuperación y transporte de datos,
**no** representan resultados termodinámicos medidos. Se confirmó:

- El índice reconoce sólo nombres propios, archivos regulares completos y sin
  enlaces simbólicos; omite archivos personales, un informe sin marca final y un
  enlace a otro fichero.
- De un informe moderno lee tipo, fecha, commit Git y resumen de `T1`, `T3`
  y `rp`. Los antiguos válidos se muestran como informes anteriores sin inventar
  metadatos ausentes. La lectura no modifica ninguno de los archivos.
- La vista local recupera los nueve valores físicos y su pérdida porcentual,
  selección OFAT, escala/resolución/cortes del mapa y `T0` de Segunda Ley.
  Al navegar por el historial **no** se ejecuta ningún modelo; se comprobó con
  mocks que lanzarían un error si se invocaran.
- `?descargar=1` devuelve el HTML guardado **exactamente**, sin reescritura
  ni elementos añadidos de la vista local; incluye la cabecera de adjunto.
- Nombres ajenos o manipulados, rutas codificadas para atravesar directorios,
  enlaces simbólicos y archivos truncados no se ofrecen mediante
  `/informes/<nombre>`. `/documentacion/<nombre>` restringe los documentos
  a los dos autorizados.

### Reutilización del estudio de Segunda Ley

Se generó un estudio de referencia **estructuralmente completo y físicamente
calculado** mediante `evaluar_punto` (ideal y no ideal) y
`analizar_segunda_ley`. Se guardó en un informe con sus nueve entradas.
Se verificó que `estudio_conservado` lo recupera tras la serialización JSON,
en la cual las tuplas pasan a listas; si cambia `eta_t`, retorna `None`.

En el POST real posterior, cambiar solo `T0` a **310,5 K** reutilizó el estudio
sin volver a invocar `viabilidad.evaluar_punto` (instrumentado para fallar
si lo intentara). Temperaturas y entropías se conservaron; para compresor y
turbina se comprobó `e_D(T0)=T0·s_gen` hasta 12 decimales.
Con las entradas físicas modificadas, el despacho entrega `None` como
estudio reutilizable. Esto demuestra el camino de decisión y la actualización;
no ensaya todas las posibles corrupciones internas de JSON.

## 4. Inventario de los 12 métodos nuevos

Archivo: `tests/test_verificacion_integracion_web.py`.

| Método (prefijo `test_`) | Contrato observado |
|---|---|
| `enrutamiento_simulacion_y_nueve_entradas` | 303, destino, nueve argumentos y T0 |
| `enrutamiento_sensibilidad_y_T0_no_aplicable` | OFAT tipificado; aislamiento de T0 |
| `enrutamiento_mapa_y_configuracion_tipificada` | Límites, resolución, escala y cortes |
| `enrutamiento_segunda_ley_y_T0` | T0 y ausencia de estudio previo |
| `rechazos_multiseccion_conservan_datos_y_no_generan_informes` | Siete rechazos 400 y valores conservados |
| `cuatro_ejecuciones_reales_aisladas_y_retencion` | Los cuatro flujos, HTML y ausencia de contaminación |
| `historial_metadata_fecha_git_legado_y_filtrado` | Índice, legado, metadatos y archivos ajenos |
| `recuperacion_cuatro_informes_descarga_identica_sin_recalculo` | Rehidratar controles y devolver bytes idénticos |
| `reutilizacion_segunda_ley_solo_si_nueve_entradas_coinciden` | Reutilización física de estados y actualización T0 |
| `rutas_malformadas_symlink_e_informe_incompleto` | Rechazo de nombres, symlinks y truncados |
| `excepcion_interna_del_mapa_no_se_presenta_como_fisica` | 500, registro técnico y mensaje seguro |
| `secciones_educativas_conectadas_sin_duplicar_formulario` | Seis pestañas técnicas, Informes/Ayuda y cuatro acciones |

Los nombres completos se obtienen anteponiendo `test_`; todos se invocan
con `unittest.TestCase`, sin argumentos adicionales ni valores de retorno útiles.
La clase `FormularioParser(HTMLParser)` extrae los atributos por `name`
y la opción `selected`, **sin ejecutar JS**. `setUp` crea un
directorio aislado, un `test_client` y un caso físico alternativo;
`_informe` crea un HTML marcado, con metadatos/paneles sintéticos, sólo
para probar el historial. `addCleanup` restaura la configuración Flask
y elimina los temporales. `subTest` mantiene la trazabilidad de variantes.

## 5. Ejecución y resultados

**Entorno utilizado:** Linux, Python 3.12.14, Flask 3.1.3,
Jinja2 3.1.6, NumPy 2.5.4 y Matplotlib 3.11.2.
Se reutilizó un entorno virtual previamente instalado en `/tmp`;
**no se instalaron ni añadieron dependencias**. Se configuró
`MPLCONFIGDIR=/tmp/brayton_v4_mpl` y se desactivó la generación de
bytecode en las invocaciones.

| Selección ejecutada | Métodos distintos | Correctos | Fallos | Errores | Omitidos | Tiempo dentro de `unittest` |
|---|---:|---:|---:|---:|---:|---:|
| V.5 nueva | 12 | 12 | 0 | 0 | 0 | 4,442 s |
| Regresiones focalizadas: web 4, dashboard 5, guías 3, segunda ley 1, mapa 1 | 14 | 14 | 0 | 0 | 0 | 2,055 + 2,670 s |
| **Total distinto** | **26** | **26** | **0** | **0** | **0** | **9,167 s** |

Ejecución nueva:

```bash
MPLCONFIGDIR=/tmp/brayton_v4_mpl PYTHONDONTWRITEBYTECODE=1 \
  /tmp/brayton_v4_venv/bin/python -B -m unittest discover \
  -s tests -p test_verificacion_integracion_web.py -v
```

En el desarrollo se corrigieron **dos expectativas de la propia prueba**:
las páginas Informes y Ayuda no emplean el control de pestañas de las seis
secciones técnicas, y la recuperación JSON transforma tuplas Python en listas.
Asimismo, una invocación inicial de regresiones escribió mal los nombres
de dos clases `unittest`; las doce regresiones restantes habían pasado,
y las dos afectadas se ejecutaron después con su nombre correcto (**2/2**).
Ninguno de estos incidentes requirió modificar producción. Los recuentos
anteriores incluyen únicamente **métodos distintos con ejecución final válida**;
no contabilizan repeticiones ni errores del lanzador.

## 6. Límites, riesgos y conclusión

1. `Flask.test_client` verifica HTTP, Jinja y lectura de HTML, **no**
   ejecución real del JavaScript, visualización en navegador, accesibilidad
   dinámica, rendimiento concurrente ni integración con Windows.
2. Sólo se probaron configuraciones representativas, no todos los posibles
   formularios malformados, extremos numéricos o archivos con metadatos
   semánticamente manipulados. Las barreras de rutas observadas no sustituyen
   una auditoría de seguridad. `estudio_conservado` contrasta formato del
   contenedor e igualdad de entradas; **no verifica en profundidad la estructura
   interna del bloque `segunda_ley`** antes de devolverlo. Se deja como
   limitación explícita, sin cambiar el código por estar fuera del alcance.
3. La comparación de cuatro informes HTML reales verifica tipo, argumentos,
   persistencia y aislamiento; su contenido termodinámico no se considera
   referencia física independiente en esta V.5.
4. No se ejecutó la suite completa ni las 69 pruebas de V.4, y no se lanzó
   un servidor local real. No se modificaron los resultados o conclusiones
   previamente publicados.

**Conclusión:** **26 métodos distintos correctos (12 nuevos, 14 regresiones),
sin fallos, errores ni omisiones finales**. No se observó un defecto reproducible
de integración web dentro de los escenarios ensayados. V.5 queda **preparada
para revisión, sin commit ni publicación**; ninguna fase posterior ha comenzado.

## 7. Corrección posterior de la limitación JSON — 23/10/2026

Esta sección refleja una intervención **posterior** a las 26 pruebas históricas
de V.5. Base verificada: rama `mejoras/verificacion-numerica`, commit remoto
`d6b3741d6c5834e5657e35a3deac4c0cfd036728`. Se trabaja en una copia
independiente, sin alterar ni sincronizar Windows y **sin commit nuevo**.

### Causa y comportamiento corregido

`web_app.estudio_conservado` comprobaba nombre, ubicación, marcas de HTML y
coincidencia de los nueve parámetros, pero devolvía el bloque `segunda_ley`
sin inspeccionar `modelos`, estados, entropías ni exergías. Una modificación de
esas claves podía provocar errores internos al actualizar T0 o reutilizar
datos incoherentes. Además, algunos metadatos externos defectuosos podían
provocar errores al reconstruir el historial de informes.

`segunda_ley.validar_estudio_reutilizable(estudio, parametros)` verifica ahora:

1. Dos modelos y equipos completos; tipos numéricos auténticos (no `bool`),
   finitud de T, p, s, generación, exergía y T0; clasificación y motivos.
2. `cp`, `gamma` y cuatro T/p frente al modelo ideal o no ideal configurado,
   usando las mismas relaciones físicas existentes sin modificar ecuaciones.
3. Entropías relativas, tolerancia de generación adiabática, generación bruta
   y cuantificada, Gouy–Stodola `eD=T0·sgen`, suma parcial y descomposición
   del cambio de entropía en la cámara.

Las igualdades numéricas del JSON usan `isclose(rtol=1e-9)` y sólo las
entropías/magnitudes derivadas tienen `atol=1e-10` en su unidad. Se respetan
por separado la tolerancia física `TOL_REL` y la banda de generación. No son
incertidumbres experimentales. No se acepta un estudio incompleto de estado
`limite_numerico` o `inconsistencia` para reutilización: se recalcula.

Si el estudio conservado falla, `estudio_conservado` devuelve `None` y la
ejecución reconstruye los dos puntos desde las entradas actuales válidas.
`ejecutar_segunda_ley` verifica también el argumento opcional de llamadas
directas. Si es íntegro y sólo cambia T0, se mantienen los cuatro estados y
sus entropías sin llamar a `evaluar_punto`; sólo se actualiza la exergía
destruida. Ningún archivo histórico se corrige ni reescribe.

`dashboard.separar_presentacion` rechaza un envoltorio JSON de tipos
incompatibles con la navegación. El historial identifica los informes con
metadatos inválidos; su recuperación estructurada responde HTTP 422 y ofrece
descarga del original sin alterarlo. Los informes legados sin bloque de
metadatos continúan su ruta anterior. Los estudios de Segunda Ley internamente
defectuosos que aún se pueden abrir reciben un aviso visible y no se reutilizan.

### Comprobaciones y riesgos pendientes

- Se prepararon **12 métodos nuevos** en `tests/test_integridad_json_v5.py`:
  casos íntegros, nueve parámetros, corrupción estructural y tipográfica,
  no finitos, incoherencias, errores JSON, legado, historial/descargas, caso no
  motor, ejecución directa y T0 con un doble de prueba que impide reevaluar.
- **12/12 nuevos correctos** en un entorno temporal autorizado, con las
  dependencias ya declaradas en `requirements.txt`. El primer intento usó
  el intérprete sin Flask y produjo un error de importación del entorno,
  no un fallo funcional de las pruebas.
- **78/78 regresiones correctas** de los módulos `test_verificacion_integracion_web`,
  `test_segunda_ley`, `test_web_app`, `test_dashboard`, `test_reporting` y
  `test_diagnostico_integracion` (39,398 s de ejecución acumulada en esa invocación).
  **Total: 90/90 métodos distintos, cero fallos y errores finales.**
- Una ejecución matemática **aislada** con un sustituto mínimo de
  `viabilidad` permitió comprobar siete condiciones de aceptación/rechazo
  y copia de T0; no equivale a pruebas HTTP o regresiones.
- No se repitieron las 144 pruebas del panel ni la suite histórica completa.
  Las rutas de historial, recuperación y descarga están cubiertas por las
  pruebas focalizadas y relacionadas; no se realizó auditoría completa de
  archivos externos arbitrarios. La revisión visual del panel había sido
  aceptada por el usuario de forma independiente.
- Ningún conjunto de ecuaciones internas certifica **autenticidad
  criptográfica**. Se pueden construir datos fraudulentos que satisfagan
  simultáneamente las relaciones; tampoco se demuestra validación experimental.

**Estado de esta corrección:** implementada y verificada mediante **90/90
pruebas relacionadas** en copia independiente; sin commit ni publicación,
pendiente de revisión y autorización expresa del usuario.
