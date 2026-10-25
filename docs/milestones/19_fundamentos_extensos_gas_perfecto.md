# Fundamentos extensos del Brayton de gas perfecto

Fecha de cierre documental: 25/10/2026. Rama: `mejoras/educacion-gas-perfecto`.
Base verificada al retomar: `1228bcd4b5b65af083f7a15883c8832a982ef880`.
Existía un borrador local de 122 líneas añadidas en `guias_educativas.py`, sin commit.

## Estado anterior

El dashboard tenía seis pares de pestañas educativas, guías breves para ocho secciones y todos los cálculos científicos actuales. El borrador local incorporaba ocho bloques por sección, con algunas extensiones inferiores a 700 palabras; faltaban cierre editorial, estilo, pruebas y documentación de esta fase.

## Qué se ha añadido

Se completan ocho bloques de fundamentos por sección: Simulación (707 palabras), Resultados (708), Optimización (717), Sensibilidad (711), Mapa (731) y Segunda ley (733). Conteo aproximado del cuerpo con `split()`, excluyendo títulos. Informes y Ayuda amplían reproducibilidad y diagnóstico sin una longitud artificial. Los resúmenes de uso permanecen breves.

`BLOQUES` conserva texto plano escapado al generar HTML en `construir_pestanas()`. CSS mejora ancho de lectura, separación y ajuste de expresiones. No cambia plantilla, formularios, navegación ni cálculo. Tres pruebas nuevas cubren estructura/extensión, escape y ubicación HTTP; se conservan las seis anteriores.

Verificación del 25/10/2026: nueve pruebas educativas correctas; seis vistas revisadas a 1280 y 390 px sin desbordamiento. Suite completa final: 307 pruebas, cinco aserciones LF/CRLF y dos errores de privilegios de enlaces simbólicos, con ocho omisiones opcionales de SciPy. No es una suite completamente correcta; el contraste con las guías de la base reproduce las incidencias de Windows. Los detalles y tiempos constan en la guía de aprendizaje §6. Los 13 módulos Python de raíz ajenos a las guías no tienen cambios binarios frente a la base.

## Nuevos conceptos de ingeniería

La mejora es educativa: deducción isentrópica con propiedades constantes, primera ley y signos, rendimiento ideal y sus hipótesis, derivadas de objetivos A/B, máximo frente a supremo, OFAT y diferencias finitas, malla frente a óptimos continuos y Gouy–Stodola para destrucción parcial. No introduce nueva física. Los ejemplos se distinguen del caso activo y de validación externa.

## Nuevos conceptos de Python

Diccionario declarativo de tuplas anidadas, desempaquetado, composición con dos `join`, selección de contenido mediante `if clave in BLOQUES` y escape antes de `safe` en Jinja. Se reutilizan funciones existentes sin nuevas dependencias. La [guía de aprendizaje](19_fundamentos_extensos_gas_perfecto_APRENDIZAJE.md) desarrolla contratos, ejemplos y comprobaciones.

## Qué hemos aprendido

La organización didáctica de cp(T) sirve de referencia, pero sus ecuaciones y algoritmos no se pueden trasladar al gas caloríficamente perfecto. El mapa de este repositorio calcula A/B por fila, y segunda ley no entrega exergía física de los cuatro estados. Explicar el código exige verificar estos alcances antes de redactar. El manual actual se sincroniza en §2, §4.41 y Evolution of the project.

## Limitaciones que siguen existiendo

Modelo estacionario de composición y propiedades constantes, sin química, mapas reales, empuje, refrigeración ni límites materiales. No hay validación experimental nueva. La exergía destruida calculada es parcial. No hay workflow local de GitHub Actions en la base inspeccionada. El contraste de referencia fue de solo lectura en `C:/Proyectos/Brayton_Simulator`, HEAD `8ca5fe74519478ab3735763f8c466f0795553445`; había un archivo de planificación ajeno sin seguimiento que se conserva.

## Commit asociado

Pendiente al redactar: la base identificada no es el commit de esta fase. El hash final se comunica tras el commit; no se anticipa un hash dentro de su propio contenido.
