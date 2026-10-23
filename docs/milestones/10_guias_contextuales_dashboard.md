# Guías contextuales del dashboard — ampliación educativa

Esta mejora añade una guía a cada una de las ocho secciones del simulador. En el estado revisado el 21 de octubre de 2026, Simulación, Resultados, Optimización, Sensibilidad, Mapa de diseño y Segunda ley separan Uso y configuración (resumen visible y controles) de Fundamentos y procedimiento (ecuaciones, hipótesis e interpretación). Informes y Ayuda conservan resúmenes y detalles plegables, sin esas dos pestañas. Sensibilidad y Mapa incluyen además experimentos sugeridos. No se repite una introducción global.

El contenido editorial reside en `guias_educativas.py`, separado de las funciones de cálculo. `dashboard.py` lo pasa a `templates/index.html`, que es compartida por la aplicación Flask y los informes HTML autónomos. `static/style.css` define la presentación responsive. Las ecuaciones se muestran como texto matemático legible, sin dependencias web externas. No se modifican los algoritmos físicos.

Se añaden pruebas en `tests/test_guias_educativas.py` para presencia y estructura de las guías. Los ensayos integrales de Flask deben ejecutarse en el entorno local con las dependencias del proyecto. Esta documentación no reemplaza las guías de aprendizaje de las fases anteriores.
