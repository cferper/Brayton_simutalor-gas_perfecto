# Fase 6 — Segunda ley y exergía

## Estado anterior
Fase 5 cerrada en `main` y `origin/main`, merge `174ce4fb9ff2a68880c3c452d82c7c179b7e058f`; 160 pruebas verificadas. Existían estados ideales/no ideales, balances, óptimos, OFAT, mapas y un T-s exclusivamente ideal. Al crear `feature/fase-6-segunda-ley-exergia` no había modificaciones del proyecto; sólo respaldos y ZIP locales conocidos sin seguimiento.

## Qué se ha añadido
`segunda_ley.py` calcula entropías relativas, generación adiabática y destrucción de exergía sobre estados existentes. El informe normal añade una sección diferenciada con dos SVG incrustados, conservando sus siete PNG originales. Flask permite diagnóstico independiente y actualización de T0 reutilizando resultados conservados cuando coinciden los parámetros. OFAT y mapas no generan estos análisis por muestra.

## Nuevos conceptos de ingeniería
Balance específico de entropía, irreversibilidad de equipos adiabáticos y Gouy–Stodola. Diferencia entre cambio de entropía del fluido y generación; referencia arbitraria s1=0 y ambiente T0. La suma eD,c+eD,t no es la destrucción de toda la instalación ni la diferencia directa entre trabajos ideal/no ideal.

## Nuevos conceptos de Python
Funciones puras sobre diccionarios existentes; validación, excepciones diferenciadas, tolerancia con valor bruto conservado, copias profundas y actualización parcial. SVG en memoria y reutilización de metadatos de informes para evitar reevaluaciones físicas.

## Qué hemos aprendido
Caso base, T0=288.15 K: s_gen,c=0.0820509581 y s_gen,t=0.0868491326 kJ/(kg·K); eD,c=23.6429836, eD,t=25.0255776 y suma cuantificada=48.6685611 kJ/kg. El ideal tiende a cero. Cambiar T0 a 300 K produce suma=50.6700272 kJ/kg sin cambiar estados ni entropías. Suite final **178/178 OK en 265.170 s** (160 anteriores + 18 nuevas). Revisión visual de ambos SVG y actualización T0 realizada desde Flask aislado. Cálculos analíticos independientes y verificación en la [guía de aprendizaje](09_segunda_ley_exergia_APRENDIZAJE.md).

## Limitaciones que siguen existiendo
Gas ideal, cp/gamma constantes, eficiencias constantes, equipos adiabáticos. No hay combustible, caudal, empuje, química, propiedades variables ni balances completos de exergía. Para la cámara faltan las transferencias de entropía con el calor o un modelo de combustión. Conexiones T-s sólo guían entre estados; no reconstruyen procesos irreversibles. Diagnóstico no motor e inconsistencia no se presentan como prestaciones válidas.

## Commit asociado
Pendiente. Base anterior verificada; rama `feature/fase-6-segunda-ley-exergia`. No se realizan commits, pushes, merges ni cambios posteriores de rama en esta tarea.
