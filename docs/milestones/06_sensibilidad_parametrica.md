# Fase 4 — Análisis de sensibilidad paramétrica OFAT

## Estado anterior

Fase 3 integrada en main mediante `899024c518348fa48944041059aa885cc127af7e`. Permitía optimizar trabajo y rendimiento, comparar A/B, calcular dominios y generar siete gráficas HTML desde nueve entradas Flask. Existían 83 pruebas. No se comparaban automáticamente familias de ciclos variando una entrada distinta de rp.

## Qué se ha añadido

`sensibilidad.py` estudia T1, T3, eta_c, eta_t o delta por OFAT; conserva ocho entradas y compara R (rp fija), A (máximo W) y B (máximo eta alcanzado). Reutiliza candidatos y física de Fases 1–3, con dominios nuevos y comprobación motora por muestra. Búsquedas independientes en extremos, centro y vecino de referencia, explícitas en cada resultado; sin SciPy.

Se registran todas las causas de R inviable, vacío motor, supremo no alcanzado, parámetros térmicos incompatibles y límite numérico. Diferencias finitas centrales/unilaterales contrastan h y h/2 para derivadas absolutas y elasticidades en la referencia. No se fabrican puntos B ni coeficientes de casos no disponibles.

Flask añade selector, rango y muestras (3–201) y botón separado. Tres gráficas W/eta/rp de 1350×900, con NaN en todas las curvas operativas y escalas adaptadas; la consigna de rp se identifica por separado con línea gris punto-raya y R motor con círculos; el eje x conserva todo el rango, incluidos tramos sin motor. `reporting.py` genera HTML autocontenido con resultados, dominios, causas, tendencias, métodos, contraste y Git. Reutiliza publicación/descarga y retención compartida de cuatro informes. Simulación normal y sus siete figuras preservadas. README/manual actualizados y guía independiente de esta fase.

## Nuevos conceptos de ingeniería

OFAT a condiciones de referencia, diferencia entre sensibilidad a rp fija y tras optimizar, elasticidad S=(x/Y)dY/dx y distinción entre cambios relativos de rendimiento y puntos porcentuales. Disponibilidad y condicionamiento importan tanto como la derivada. OFAT no mide interacciones ni ofrece una jerarquía universal de parámetros; los dominios abiertos no son rangos gráficos ni ventanas numéricas.

## Nuevos conceptos de Python

Copias por muestra, datos anidados con estados explícitos, arrays alineados/NaN, callbacks y caché sólo local, conjunto de índices de comprobación, contraste de perturbaciones y medición con `perf_counter`. Integración por acción de formulario con Jinja/JavaScript local para sugerencias; separación entre cálculo, dibujo, presentación y publicación. Se desarrollan conceptos previos de funciones, buffers y excepciones específicas.

## Qué hemos aprendido

Para T3=1600 K y entradas predeterminadas: R da 369.476301 kJ/kg y 36.898732 %; A da rp=12.895052, W=373.210827 y eta=39.212614 %; B da rp=35.452324, W=313.738915 y eta=43.893107 %. S_rpA,T3≈1.75, coherente con gamma/[2(gamma−1)]. A 2000 K, B pasa a rp≈64.269908, fuera de antiguos intervalos fijos.

Verificación del 20 de octubre de 2026: primera suite completa 107/107 OK (93.103 s), conservando las 83 pruebas previas y añadiendo 24. Revisión final: 107/107 pruebas OK en 131.473 s, tras el ajuste visual. Comprobaciones con T3, eficiencia, pérdidas, puntos inviables, reversible y escalas grandes; simulación normal, publicación mixta, descarga, fallo parcial y PNG históricos conservados. Cálculos de 41 muestras ~0.045–0.10 s; con tres gráficas/HTML ~1.8–2.2 s en este equipo. Figuras inspeccionadas fuera de outputs. Verificación interna, sin validación experimental.

Revisión del 21 de octubre de 2026: separación explícita entre consigna y rp operativo de R; prueba específica con T3 y muestras inviables. 108/108 pruebas correctas en 147.931 s con la suite completa, incluyendo la nueva prueba de consigna y máscaras.

## Limitaciones que siguen existiendo

Gas ideal y propiedades constantes; sin combustible, caudal, potencia, empuje ni mapas bidimensionales. Malla finita configurable puede omitir regiones estrechas; diferencia h/h2 es diagnóstico heurístico, no cota rigurosa. Candidatos de todas las muestras se verifican físicamente, pero sólo algunas se contrastan numéricamente. No se fuerza una respuesta ante redondeo/fronteras degeneradas. La retención no tiene bloqueo entre procesos. La referencia requiere entradas válidas y T3>T1, aunque su rp fija no necesita ser motora para un estudio OFAT.

## Commit asociado

Implementación: `88c026395a9aba9cf72819305cfe2540f200e54a` — `Implement Brayton parametric sensitivity analysis with Flask integration`. Rama de desarrollo `feature/fase-4-sensibilidad-parametrica`; base verificada `899024c518348fa48944041059aa885cc127af7e`, que contiene Fase 3, no Fase 4. Asociación incorporada en un commit documental adicional autorizado el 21 de octubre de 2026, una vez conocido el hash real; el commit de implementación dejó el campo pendiente. Verificación previa al commit en este cierre: 108/108 pruebas OK en 80.205 s. `zip.zip` permanece local y sin seguimiento; no forma parte del commit. [Guía de aprendizaje independiente](06_sensibilidad_parametrica_APRENDIZAJE.md).
