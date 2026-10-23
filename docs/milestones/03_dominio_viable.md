# Fase 1 — Dominio físicamente viable del ciclo Brayton

## Estado anterior
El simulador calculaba ciclos ideal y no ideal, el óptimo de trabajo ideal y seis gráficas en HTML autocontenido. Flask admitía nueve parámetros y ambos modos compartían cuatro informes. Un punto no motor en un barrido fijo podía rechazar toda la ejecución.

## Qué se ha añadido
El módulo `viabilidad.py` comparte estados y balances, clasifica todos los motivos de inviabilidad y obtiene dominios abiertos o vacíos. Se adaptan los barridos y las cuatro gráficas de relación de presiones, con NaN en puntos excluidos, fronteras y bandas motoras. HTML incluye condiciones, límites y recuentos; Flask distingue inviabilidad física, entradas inválidas y límites numéricos, conservando datos e historial.

## Nuevos conceptos de ingeniería
La frontera ideal es `(T3/T1)^(gamma/(gamma−1))`, distinta del óptimo de trabajo ideal. Las pérdidas exigen expansión disponible, calor positivo y trabajo positivo por separado. La transformación x=rp^a convierte wn>0 en una desigualdad cuadrática convexa; su intersección con las otras restricciones demuestra un intervalo abierto o vacío para este modelo. Calor positivo no garantiza trabajo positivo. Las fronteras de trabajo se localizan por bisección acotada y el límite reversible recupera el ideal.

Con los valores de referencia: ideal `1 < rp < 403.4175203200`; no ideal `1.0696541023 < rp < 155.4543260392`. Los resultados en rp=10 se conservan: 505.619018 y 369.476301 kJ/kg. Las tolerancias computacionales no equivalen a incertidumbre experimental.

## Nuevos conceptos de Python
Separación entre evaluación con signo, clasificación y API estricta; diccionarios con motivos simultáneos; función callback y cierre local para bisección; máscaras booleanas y NaN; muestreo lineal/geométrico combinado y deduplicación. Las gráficas consumen datos ya clasificados y los errores inesperados no se silencian con un `except ValueError` genérico.

## Qué hemos aprendido
Un resultado no motor puede ser una evaluación matemática válida. Las fronteras físicas, los extremos de dibujo y la malla del óptimo ideal son conceptos distintos. Se han superado 40 pruebas: 22 existentes conservadas y 18 nuevas, incluidas fronteras, dominio vacío, reversibilidad, curvas, CLI, Flask e integridad de informes. Esto verifica implementación; no valida experimentalmente un motor real.

## Limitaciones que siguen existiendo
Gas ideal con cp/gamma constantes, equipos adiabáticos y pérdida relativa fija. No hay optimización no ideal (Fase 2), propiedades variables, química, combustible, caudal, potencia, empuje ni mapas. La ventana gráfica se limita a rp=10000; las fronteras completas se conservan en tablas. La banda numérica puede excluir interiores extremadamente estrechos. T-s/P-v y optimización siguen siendo ideales; la referencia debe ser motora en ambos modelos para generar su informe. No se incorpora bloqueo multiproceso del historial.

## Commit asociado
Este milestone se incluye junto con el código, las pruebas y la guía de aprendizaje en el commit de cierre con mensaje `Implement Brayton feasible operating domain with tests and learning guide`. Su hash se consulta en Git: no se incrusta el identificador del propio commit en su contenido. Rama de implementación `feature/fase-1-dominio-viable`, base `3003bc8cd2d84547cc48e09f136f849d555599e2`. Verificación de cierre del 20 de octubre de 2026: suite completa, 40 pruebas superadas antes del commit; PNG históricos idénticos a la base. Es verificación de implementación, no validación experimental.
