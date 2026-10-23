# Fase 3 — Optimización del rendimiento térmico y comparación de objetivos

## Estado anterior

La Fase 2, integrada en el commit base `5629eb076d10ad54852f74a438fda8a970db5f04`, calculaba los dominios ideal/no ideal y los máximos de trabajo específico, con seis gráficas HTML y nueve campos Flask locales. Conocer el rendimiento en el máximo trabajo no equivalía a optimizarlo. La base tenía 55 pruebas. Rama de desarrollo: `feature/fase-3-optimizacion-rendimiento`.

## Qué se ha añadido

`optimizacion_rendimiento.py` estudia el supremo ideal, obtiene el candidato no ideal mediante una raíz racionalizada, realiza una búsqueda numérica independiente y compara los puntos A (máximo trabajo) y B (máximo rendimiento). Reutiliza dominios, estados y balances de Fase 1 sin cambiar sus ecuaciones ni los resultados de Fase 2.

`main.py` integra los estudios con los parámetros de cada ejecución. Conserva las seis figuras anteriores, adapta las dos comparaciones con marcadores A/B y añade una séptima curva paramétrica de trabajo frente a rendimiento. `reporting.py` incorpora el estudio, estados óptimos, concordancia, diferencias y límites; Flask conserva sus nueve campos, acceso local, descarga, Git e historial de cuatro informes. No se introduce SciPy ni otra dependencia.

## Nuevos conceptos de ingeniería

Máximo alcanzado frente a supremo no alcanzado: el rendimiento ideal crece estrictamente y su frontera superior no es motora. Con cualquier pérdida estricta y dominio motor no vacío, el rendimiento no ideal tiene un máximo interior único. Se deriva eta=N(x)/(B−x), se prueba que el numerador de su derivada decrece y se obtiene x*=B/(1+sqrt(S/H)). Se distingue existencia matemática de resolución numérica en las bandas de frontera.

Comparación de criterios a temperaturas extremas fijas: un mayor rendimiento puede exigir menos trabajo específico. La ganancia de rendimiento en puntos porcentuales difiere de un cambio relativo porcentual. La curva de compromiso usa rp como parámetro; no toda ella es una frontera de Pareto.

## Nuevos conceptos de Python

Funciones estables `log1p`/`expm1`, raíz racionalizada y resultados con estados de disponibilidad explícitos. Se desarrollan conceptos de Fase 2: cierre/caché local, malla logarítmica, sección áurea, exclusión mediante −infinito interno y selección de registros. Los argumentos sólo por nombre del presentador conservan la compatibilidad de sus argumentos posicionales. Se reutilizan diccionarios, arrays/NaN, buffers y pruebas con sustituciones temporales.

## Qué hemos aprendido

Caso predeterminado: A tiene rp=12.8950516696, trabajo=373.2108274827 kJ/kg y rendimiento=39.2126144220 %. B tiene rp analítico=35.4523235708, numérico=35.4523219222, trabajo=313.7389152634 kJ/kg y rendimiento=43.8931071631 %. Pasar de A a B gana 4.6804927411 pp, reduce trabajo un 15.9352054763 % y cambia calor en −236.9827016782 kJ/kg. El supremo ideal es 81.990625 %, no alcanzado en un ciclo motor.

Verificación de cierre del 20 de octubre de 2026: **83/83 pruebas OK en 51.733 s**, distinguiéndola de las comprobaciones previas. Se conservan las 55 pruebas anteriores y se añaden 20 unitarias y ocho de integración. Se revisan figuras/informes en una carpeta aislada, sin alterar outputs ni PNG históricos. Es verificación de implementación, no validación experimental externa.

## Limitaciones que siguen existiendo

Gas ideal con cp/gamma constantes, eficiencias y pérdida fijas; sin combustible, caudal, potencia, empuje ni mapas. Diagramas T-s/P-v sólo del ideal de referencia. Un máximo casi degenerado puede no resolverse por encima de la banda cero; el ancho final no certifica la precisión efectiva de rp ni la fidelidad del modelo. El informe exige referencia motora en ambos modelos; el vacío se estudia mediante API independiente. La retención no incorpora bloqueo entre procesos.

## Commit asociado

Implementación: `44145f3553ee502ed7d547762651d12ca1c41d40` — `Implement Brayton thermal efficiency optimization and work trade-off`. La base `5629eb076d10ad54852f74a438fda8a970db5f04` no contiene esta fase. Asociación incorporada en el cierre de Git autorizado, una vez conocido el hash; el commit de implementación dejó el campo pendiente. La integración se registra mediante merge explícito en main, sin reescribir historial. [Guía educativa independiente](05_optimizacion_rendimiento_APRENDIZAJE.md).
