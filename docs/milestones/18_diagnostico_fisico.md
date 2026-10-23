# Diagnóstico y coherencia física de cada informe

## Estado anterior

La base comprobada es `12c3dc27397789faa61ad49c7e80faa4e8ef3791`, rama `mejoras/verificacion-numerica`, el **23/10/2026**. El programa calculaba ciclos, dominios, óptimos A/B, sensibilidad OFAT, mapas y Segunda Ley, y guardaba HTML autónomo con historial de cuatro informes. Las verificaciones V.1–V.5 se ejecutaban durante el desarrollo. La lista `comprobaciones` de la simulación reunía mensajes de controles previos, sin un contrato uniforme de magnitudes, residuos, unidades y tolerancias para todas las modalidades.

## Qué se ha añadido

El panel **Diagnóstico y coherencia física** presenta controles calculados con los resultados concretos del informe. Cada registro distingue `Cumple`, `Atención` y `No evaluable`, muestra valores/referencias disponibles, residuos y tolerancias y ofrece una explicación desplegable. La ausencia de una magnitud o la inaplicabilidad de una ecuación no se transforma en éxito.

La arquitectura separa `diagnostico.py` (controles científicos), `diagnostico_informe.py` (selección y agrupación por modalidad) y `diagnostico_html.py` (HTML), con integración en `reporting.py` y `dashboard.py`. La selección usa resultados existentes; no vuelve a ejecutar optimizadores ni cambia las ecuaciones de producción. Los informes guardados conservan el panel; el historial lo recupera y la descarga devuelve el documento original. Los informes anteriores siguen siendo consultables, sin atribuirles diagnósticos nuevos.

Los contratos completos y el recorrido de datos se explican en [§4.56 del manual actual](../../CODE_WALKTHROUGH.md); los conceptos y ejercicios de esta iteración se desarrollan en [§12 del aprendizaje de la fase vigente](11_verificacion_numerica_APRENDIZAJE.md). Este avance pertenece a esa misma fase; no abre otra.

## Nuevos conceptos de ingeniería

- Un **residuo** mide la discrepancia de una relación para datos concretos; una **tolerancia** decide cuándo esa discrepancia es compatible con la precisión y escala adoptadas.
- La primera ley, las relaciones de estados y las referencias isentrópicas deben interpretarse según el modelo ideal o no ideal. Recalcular la misma identidad con las mismas magnitudes proporciona coherencia interna, no evidencia física independiente.
- Un punto puede conservar balances algebraicos y simultáneamente incumplir restricciones de funcionamiento motor. La admisión y el diagnóstico energético responden a preguntas distintas.
- La generación adiabática de compresor/turbina y Gouy–Stodola se comprueban sólo con los datos disponibles. El cambio de entropía del fluido en la cámara no determina por sí solo su generación ni la destrucción total de exergía del ciclo.
- Los óptimos interiores se diferencian de las fronteras excluidas y del supremo ideal de rendimiento, que no constituye un máximo alcanzado.

## Nuevos conceptos de Python

Se introducen registros homogéneos de diagnóstico y una separación explícita entre cálculo, orquestación y presentación. Los diccionarios conservan el significado de cada campo; `None` representa información ausente y no un cero. La agrupación reduce el tamaño del HTML de estudios con muchas muestras manteniendo los recuentos de controles evaluados y ejemplos representativos. HTML utiliza texto escapado y elementos `details`/`summary` nativos, sin necesitar otra dependencia ni ejecutar pruebas históricas en cada petición.

## Qué hemos aprendido

Un panel útil debe explicar **qué se comprueba, con qué datos y hasta dónde alcanza su conclusión**. Mostrar tolerancias y razones de no evaluación evita interpretar un indicador como certificado de exactitud. La trazabilidad exige conservar el diagnóstico del informe original, no recalcularlo al navegar por el historial.

### Comprobaciones realmente ejecutadas y cierre de revisión (23/10/2026)

La ejecución inicial de la sesión anterior había acreditado **19/19 pruebas físicas** y **9/10 de integración**. El caso pendiente se corrigió allí sustituyendo la entrada `rp=1`, rechazada por el formulario, por un escenario no motor `T3=400 K`; su ejecución focalizada **ha pasado en esta revisión**. Los registros de la suite amplia iniciada en la sesión anterior no se recibieron y no se les atribuye ningún resultado.

Esta revisión se ha efectuado en una **copia Linux independiente**, creada desde el commit remoto `12c3dc27397789faa61ad49c7e80faa4e8ef3791`. Se importaron los once archivos de trabajo del ZIP después de comprobar que sus siete referencias coinciden con el commit de partida al normalizar los finales de línea CRLF. **No se ha accedido al directorio de Windows**, ni se ha comprobado su estado Git o el hash del documento personal desde este entorno.

Resultados finales de las ejecuciones focalizadas y relacionadas (sin contar dos veces el caso repetido):

| Pruebas | Resultado |
|---|---:|
| Diagnóstico físico (19 iniciales + 1 nueva) | **20/20** |
| Integración del diagnóstico (10 iniciales + 1 estructural) | **11/11** |
| Regresiones directamente relacionadas: informes, dashboard, web, Segunda Ley, sensibilidad y mapa | **101/101** |
| Contratos V.5 de integración web relacionados | **12/12** |
| **Métodos distintos ejecutados correctamente** | **144/144** |

No se han observado fallos en esas ejecuciones finales. Una invocación intermedia de regresiones tuvo cuatro errores de **importación de tests** porque faltaba `tests` en `PYTHONPATH`; al configurar la ruta, se ejecutaron los 101 métodos correctamente. No se ha ejecutado ni se declara superada la suite completa.

**Defecto detectado y corregido:** si el registro de ciclo contenía `viable=None`, `viable="False"` o `viable=0/1`, el diagnóstico aplicaba `bool(...)`, lo que podía convertir un dato ausente o mal tipado en una clasificación aparentemente correcta. Ahora sólo se compara un `bool` auténtico; `None` queda **No evaluable** y un tipo incorrecto genera **Atención**. La corrección afecta exclusivamente a `diagnostico.py` y sus pruebas; no altera el evaluador ni los algoritmos físicos.

La nueva comprobación estructural del HTML autónomo valida identificadores únicos del panel, referencias accesibles de `aria-labelledby`, parejas `details` y reglas CSS adaptativas incluidas en el documento. Las pruebas de integración verifican generación, recuperación desde historial y descarga exacta del HTML. **No se ha completado una revisión visual real de escritorio/móvil ni interacción manual en navegador**: no había ejecutable de navegador accesible en la copia Linux y la sesión anterior no consiguió conectarse. Una revisión visual sigue recomendada antes de dar el diseño por definitivamente cerrado.

Los valores predeterminados ya documentados —ideal `wn≈505,619018 kJ/kg`, `η≈48,205253 %`; no ideal `wn≈369,476301 kJ/kg`, `η≈36,898732 %`— pertenecen al modelo existente; las comprobaciones actuales contrastan relaciones, no validan esas cifras con datos experimentales.

## Limitaciones que siguen existiendo

El modelo sigue usando gas ideal, `cp`/`gamma` constantes y equipos simplificados; no se contrasta con mediciones de motores. El diagnóstico no es una validación experimental ni una auditoría exhaustiva de archivos. Permanece la limitación documentada en V.5: `estudio_conservado` no verifica en profundidad toda la estructura interna de un bloque `segunda_ley` procedente de JSON semánticamente manipulado. La incorporación del panel no se considera una corrección de esa limitación.

También falta comparar la copia revisada con los archivos sin confirmar del repositorio de **Windows** antes de trasladar correcciones. La falta de inspección visual de escritorio/móvil es una limitación distinta de la integridad estructural y de las pruebas HTTP.

## Commit asociado

**Pendiente.** No se ha creado commit ni publicado esta implementación. `12c3dc27397789faa61ad49c7e80faa4e8ef3791` identifica la base verificada y no el commit que contiene el panel. La rama `main` permanece fuera de esta intervención.
