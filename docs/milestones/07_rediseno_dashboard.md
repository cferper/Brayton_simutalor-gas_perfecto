# Rediseño independiente — Dashboard técnico de Brayton Simulator

## Estado anterior

Las Fases 1–4 estaban integradas en main, commit `ac37b9e0b93bcc0449e59fe04d5cfecb082f70ad`, con 108 pruebas. La interfaz presentaba formulario y largos informes verticales, siete gráficas normales o tres OFAT. Se conservaban cuatro informes completos. La rama de Fase 5 no contenía nuevas funcionalidades.

## Qué se ha añadido

Rama independiente `feature/rediseno-dashboard`, creada desde main con autorización para conservar `zip.zip` personal fuera de Git. `dashboard.py` y una plantilla compartida organizan Simulación, Resultados, Optimización, Sensibilidad, Informes y Ayuda. Seis KPI no ideales, comparación A/B, visor normal de cinco pestañas con siete PNG únicos, visor OFAT de tres pestañas, conteos de disponibilidad, elasticidades y tablas plegables.

CSS responsive, JS ligero con fragmentos/historial, navegación por teclado, modal nativo cerrable con Escape y retorno del foco. Informes autónomos con recursos incrustados; sin JS, contenido accesible sin pestañas obligatorias. Historial de sólo lectura, descarga idéntica, recuperación de parámetros desde informes nuevos y acceso acotado a documentación. Los archivos anteriores siguen disponibles sin reescribirlos ni alterar la retención.

IBM Plex Sans/Mono locales desde IBM/plex, SIL OFL 1.1, con procedencia y commit upstream registrados; SVG geométrico propio CC0-1.0. Sin CDN ni nuevas dependencias. No se modifica la física, optimización, viabilidad, OFAT, main ni sus imágenes.

## Nuevos conceptos de ingeniería

Separar el caso actual no ideal, máximo trabajo y máximo rendimiento; distinguir magnitudes no disponibles de ceros reales y supremos de puntos operativos. La organización visual facilita comparar decisiones sin aumentar la fidelidad del modelo. El motor de cabecera es decorativo, no un modelo físico de tobera o empuje.

## Nuevos conceptos de Python

Renderizado Jinja fuera de Flask, composición de HTML, metadatos JSON inertes, recursos Base64 y presentación separada de cálculo. En frontend: CSS Grid con contención del ancho, mejora progresiva, eventos delegados, history/fragmentos, ARIA y diálogo nativo. Se reutilizan las tablas y PNG existentes para mantener información técnica y pruebas anteriores.

## Qué hemos aprendido

Los datos provienen de cada ejecución: A≈373.211 kJ/kg y B≈43.893 % en el caso de referencia, sin fijar esas cifras en la interfaz. Todas reutiliza los siete nodos de imagen; cambiar pestaña no ejecuta otro estudio. La descarga conserva el documento original y la vista Flask recupera el formulario sin recalcularlo.

Verificación del 21 de octubre de 2026: primera suite 123/123 OK en 124.582 s; verificación final: 123/123 pruebas correctas en 70.814 s; se conservan las 108 previas y se añaden 15 de dashboard. Son las 108 pruebas anteriores conservadas y 15 nuevas de presentación/rutas. Interactividad comprobada separadamente en navegador real: simulación, A/B, pestañas, modal/Escape, OFAT con muestras inviables y viewport móvil sin desbordamiento horizontal. Comprobaciones finales del autónomo descritas en la guía. Es verificación interna, no validación experimental.

## Limitaciones que siguen existiendo

Modelo físico anterior intacto. Navegadores antiguos sin dialog nativo mantienen las imágenes en su resolución original accesible, pero pueden carecer de ampliación modal. Sin JS se muestra más contenido verticalmente. Los informes históricos no se migran y sus metadatos pueden no estar disponibles en el índice. El informe autónomo no ejecuta Python: otro cálculo requiere Flask local. La retención conserva sus límites previos de concurrencia.

## Commit asociado

Hash pendiente al redactar el contenido del commit de cierre; consultar el historial Git para la asociación exacta. Base `ac37b9e0b93bcc0449e59fe04d5cfecb082f70ad`, rama de desarrollo `feature/rediseno-dashboard`. Revisión de cierre: 123/123 pruebas OK en 93.985 s; publicación y merge autorizados por el usuario, sin implementar Fase 5. [Guía educativa](07_rediseno_dashboard_APRENDIZAJE.md).
