# Fase 5 — Mapa de diseño rp–T3

## Estado anterior
Fases 1–4 y dashboard integrados en el merge `b6fdfbeb5aa63605734258449f05a9ff3f964946`. Existían simulaciones individuales y OFAT, con 123 pruebas; no había mapas bidimensionales. Árbol limpio al comenzar, rama `feature/fase-5-mapa-rp-t3`.

## Qué se ha añadido
`mapa_diseno.py`: malla no ideal, máscaras, estados y energías con signo, fronteras, trayectorias A/B independientes de columnas y cortes. Nueva sección del dashboard, tres mapas, selector de cortes y tabla plegable. HTML autónomo con metadatos Git y retención compartida de cuatro informes. No se modifican ecuaciones ni optimizadores.

## Nuevos conceptos de ingeniería
Variación simultánea de rp y T3 a siete parámetros fijos; región motora frente a ventana visual; trayectorias de dos objetivos distintos y supremo reversible sin punto B. Bordes de píxeles y fronteras físicas no son equivalentes.

## Nuevos conceptos de Python
Matrices `(n_T3,n_rp)`, índices por fila/columna, máscaras booleanas y arrays enmascarados; separación entre cálculo, preparación y representación; `pcolormesh(shading='nearest')` sin interpolación de contornos; reutilización de resultados y medición con `perf_counter`.

## Qué hemos aprendido
La precisión del óptimo no depende de los colores ni del tamaño de la malla. A T3=1600 K, A mantiene rp≈12.895052 y W≈373.210827 kJ/kg; B mantiene rp≈35.452324 y eta≈43.893107 %. En la revisión del 21 de octubre de 2026, 8000 celdas se calcularon en 0.146 s; cálculo y seis figuras en 3.381 s; HTML y guardado en 0.380 s. Son medidas locales orientativas, no garantías de tiempo. Suite final: **160/160 OK en 239.457 s** (123 anteriores + 21 del mapa + 16 educativas), con revisión real de mapa, simulación normal y OFAT desde Flask. Detalles de pruebas y revisión en la [guía independiente](08_mapa_diseno_rp_t3_APRENDIZAJE.md).

## Limitaciones que siguen existiendo
Gas ideal, cp/gamma, eficiencias y pérdida relativa constantes; equipos adiabáticos. Sin combustible, caudal, potencia, empuje, tobera o datos experimentales. T3 siempre mayor que T1. Hasta 20000 celdas, 401 muestras por eje y cinco cortes; los mapas discretos no certifican cada punto del continuo. Gris combina no motor y límite numérico, diferenciados en datos y resumen. Los informes autónomos consultan datos guardados; nuevos cálculos requieren Python local.

## Commit asociado
Pendiente: Fase 5 sin commit, push, merge ni cambio de rama por instrucción del usuario. La base anterior no contiene esta fase.
