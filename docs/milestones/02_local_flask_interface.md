# Interfaz local Flask para configurar el ciclo

## Estado anterior

`python main.py` ejecutaba el caso con nueve parámetros definidos dentro de `main()` y generaba un informe HTML autocontenido con seis gráficas, identificación Git y conservación de cuatro informes. Cambiar los datos requería editar Python.

## Qué se ha añadido

`python web_app.py` inicia un formulario exclusivamente en `http://127.0.0.1:5000`, sin debug interactivo ni recarga automática. Los nueve valores se convierten y validan en el servidor; la pérdida pasa de porcentaje a fracción. Flask reutiliza `main` y las 13 funciones físicas originales, sin duplicar ecuaciones.

Los valores predeterminados están en un diccionario que se copia por ejecución. Se conserva la llamada anterior `main(carpeta_salida)` y el comando de terminal. La web muestra y descarga el mismo informe, compartiendo `outputs/` y su conservación. Solo la copia visualizada lleva enlaces de navegación.

## Nuevos conceptos de ingeniería

Entrada de datos con unidades explícitas, eficiencias fraccionarias y pérdida porcentual. Distinción entre un campo fuera de rango y una combinación rechazada por el modelo o por sus estudios fijos. No se han añadido hipótesis, ecuaciones, optimizaciones ni análisis de dominio viable.

## Nuevos conceptos de Python

Flask, peticiones HTTP GET/POST, rutas y decoradores, plantillas Jinja, respuestas 200/303/400/404/500, configuración por copia de diccionarios y excepción específica `ErrorModelo`. Pruebas con `test_client`, sustitución temporal de configuración y ejecución del punto de entrada en un subproceso.

## Qué hemos aprendido

El navegador envía texto, no magnitudes físicas. La validación HTML no sustituye la del servidor; un POST correcto debe llegar al mismo núcleo que el comando de terminal. Los errores de programación se registran con traceback y no se confunden con errores del modelo. Las rutas de informes se restringen a archivos propios completos, sin aceptar rutas locales arbitrarias.

Se han superado 22 pruebas, incluidas simulaciones con parámetros modificados, seis imágenes de la misma ejecución, historial mezclado de cinco ejecuciones que deja cuatro informes, entradas inválidas, errores inesperados y ausencia de efectos al importar. Se ha comprobado el arranque real local y el formulario en navegador. Son verificaciones de implementación, no validación experimental de un motor.

## Limitaciones que siguen existiendo

Mismo modelo simplificado de propiedades constantes, mismas seis gráficas y barridos fijos; algunos casos válidos en la relación de referencia pueden fallar en un barrido. No hay búsqueda de dominio viable, web pública, autenticación ni base de datos. El servidor atiende una petición cada vez para evitar interferencias de Matplotlib; no se añade bloqueo entre un proceso Flask y otro de terminal. La descarga sigue siendo estática y autocontenida.

## Commit asociado

Incluido junto con los informes HTML en el commit con mensaje `Add HTML reports and local Flask interface with educational documentation`. Su hash se consulta en el historial Git; no se incrusta en el contenido del propio commit.
