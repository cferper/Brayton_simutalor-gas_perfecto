# Informes HTML autocontenidos e historial de ejecuciones

## Estado anterior

El simulador calculaba ciclos ideales y no ideales, estados y balances, un óptimo de trabajo ideal y barridos comparativos. Mostraba los resultados en tablas de terminal y guardaba seis PNG con nombres fijos junto a `main.py`, sobrescribiéndolos en cada ejecución.

## Qué se ha añadido

Cada ejecución genera un HTML en `outputs/` con parámetros, resultados, comprobaciones y las seis gráficas nuevas incorporadas como Base64. La terminal muestra tres líneas de resumen. Tras publicar el informe completo, se conservan los cuatro informes propios completos más recientes; los archivos ajenos y PNG históricos quedan fuera de la limpieza.

`reporting.py` concentra la presentación y almacenamiento. Un punto de entrada protegido permite importar las funciones sin ejecutar una simulación. Se añaden pruebas independientes de resultados y conservación. No hay web interactiva ni nuevas dependencias.

## Nuevos conceptos de ingeniería

Trazabilidad entre parámetros, resultados y gráficas de una ejecución y presentación explícita de unidades y alcance ideal/no ideal. Se conserva la distinción entre verificación de implementación y validación con datos físicos externos. No se han introducido ecuaciones ni hipótesis físicas nuevas.

## Nuevos conceptos de Python

Módulos, punto de entrada, HTML/CSS estático, buffers `BytesIO`, bytes frente a texto, Base64, escape HTML, fechas con zona local, UUID, contextos `with`, limpieza con `finally`, publicación mediante temporal y filtrado/ordenación de informes. Las pruebas introducen `unittest`, parser HTML, sustituciones temporales con `patch` y directorios aislados.

## Qué hemos aprendido

Guardar un informe exige completar cálculos e imágenes antes de publicarlo, y publicar antes de limpiar el historial. Las imágenes en memoria evitan utilizar gráficos antiguos. La corrección de la presentación y de la conservación se verifica por separado de las ecuaciones. El walkthrough detalla las funciones y el flujo actuales en sus secciones 4, 9, 10 y 12.

## Limitaciones que siguen existiendo

Gas ideal con propiedades constantes, eficiencias fijas, pérdida de presión simplificada y ausencia de combustible, caudal, empuje y mapas. Diagramas y optimización exclusivamente ideales; intervalos de barrido fijos sin análisis de dominio viable. La retención no usa bloqueo multiproceso y puede quedar incompleta si faltan permisos, con advertencia. La publicación está dirigida al entorno Windows. La vista visual en Chrome/Edge queda pendiente de revisión por el usuario; se han comprobado automáticamente contenido e imágenes.

## Commit asociado

Incluido junto con la interfaz local en el commit con mensaje `Add HTML reports and local Flask interface with educational documentation`. Su hash se consulta en el historial Git; no se incrusta en el contenido del propio commit.
