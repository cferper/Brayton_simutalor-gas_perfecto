# Aprendizaje — Enseñar el ciclo de gas perfecto desde el dashboard

## 1. Punto de partida verificado y objetivo

Documentación y cierre: **25/10/2026**. Rama activa: `mejoras/educacion-gas-perfecto`. Base Git verificada: `1228bcd4b5b65af083f7a15883c8832a982ef880` (`chore: add tests documentation and web assets`). Al retomar existían 122 líneas locales añadidas en `guias_educativas.py`. No se atribuye una fecha de implementación anterior a ese borrador ni se confunde la base con el commit de esta fase.

El programa ya calculaba estados, balances, dominio motor, óptimos A/B, sensibilidad, mapa y segunda ley. Disponía de dos pestañas por sección científica, pero la teoría comprometida en Git era breve. El objetivo consiste en aprender a justificar las ecuaciones y leer los resultados, sin cambiar el modelo. La referencia cp(T), en el commit `8ca5fe74519478ab3735763f8c466f0795553445`, se consultó solo para organización pedagógica: módulo educativo, plantilla, CSS, manual y documentos 28. Sus inversiones de propiedades y sus balances no son los de este repositorio.

## 2. PYTHON: datos separados de cálculo

`GUIAS` conserva resúmenes y guías compactas. El nuevo `BLOQUES` contiene seis claves y ocho pasos por clave. Un fragmento real de su estructura es:

```python
BLOQUES = {
 'simulacion': (
  ('1 · Concepto físico: el ciclo Brayton', (
```

El diccionario relaciona una clave de sección con una tupla. Cada elemento es otro par: un título y una tupla de párrafos. Las cadenas son texto plano. La coma de una tupla con un solo elemento importa: `('texto',)` es una tupla; `('texto')` sigue siendo una cadena. Esta estructura permite escribir contenido sin introducir condicionales físicos ni duplicar plantillas.

Antes se reutilizaban cuatro apartados compactos de `GUIAS` para toda la teoría. Ahora las seis claves de `BLOQUES` sustituyen únicamente su teoría por ocho bloques; los resúmenes siguen iguales. Informes y Ayuda conservan la guía compacta, con fundamentos ampliados sobre unidades, conservación del HTML, interpretación de diagnósticos y verificación frente a validación.

### Función modificada: `construir_pestanas()`

- **Argumentos:** ninguno; lee las constantes editoriales del módulo.
- **Retorno:** `dict[str, dict[str, str]]` con ocho claves de sección; cada valor contiene `resumen` y `teoria`, ambos HTML.
- **Unidades:** la función no calcula magnitudes; el texto define K, kPa, J/(kg·K), kJ/kg y kJ/(kg·K) cuando corresponde.
- **Propósito:** componer presentación estática. No tiene ecuación física propia.
- **Llamadas:** usa `html.escape` y `str.join`; no llama módulos científicos. La llaman `dashboard.renderizar_dashboard` y las pruebas; la ruta Flask o los constructores de informes llegan a ella a través del dashboard.
- **Validación y errores:** la estructura es de autoría interna. Una clave requerida ausente provoca `KeyError`; un par mal formado, `ValueError` al desempaquetar; una entrada no textual puede fallar al escapar. No son errores de las entradas físicas del usuario.
- **Antes/después:** mantiene firma y retorno; añade la sustitución de `teoria` para claves presentes en `BLOQUES`.

```python
if clave in BLOQUES:
    bloques = ''.join(
        f'<section class="edu-deep-block"><h3>{esc(titulo)}</h3>'
        + ''.join(f'<p>{esc(parrafo)}</p>' for parrafo in parrafos)
        + '</section>'
        for titulo, parrafos in BLOQUES[clave]
    )
    resultado[clave]['teoria'] = f'<div class="edu-theory edu-deep">{bloques}</div>'
```

`for titulo, parrafos in ...` desempaqueta cada par. El `join` interior reúne sus párrafos; el exterior reúne los ocho bloques. Las f-strings insertan el texto ya escapado en las etiquetas controladas por el programa. `escape('a < b')` devuelve `a &lt; b`: el navegador muestra la desigualdad sin interpretarla como etiqueta. Se reutilizan conceptos anteriores de diccionario, f-string y escape; la novedad es su composición en dos niveles.

Ejemplo real de uso: `construir_pestanas()['simulacion']['teoria']` devuelve la explicación extensa. Consultar `['resumen']` devuelve únicamente el texto breve. Para corregir una explicación se edita el par correspondiente, no el evaluador físico.

`construir_guias()` conserva su firma, argumentos nulos y retorno `dict[str, str]`: recorre `GUIAS`, llama `escape` y forma resúmenes y detalles. La llaman dashboard y pruebas. No se modifica su algoritmo; Informes/Ayuda reciben el texto ampliado desde las constantes existentes. Ejemplo: `construir_guias()['informes']`. No tiene unidades ni validación física; mantiene los posibles errores de autoría descritos en el manual §4.41.

## 3. HTML, CSS y flujo de presentación

La plantilla ya inserta `pestanas[clave]['teoria'] | safe` en el panel correspondiente. Es seguro aquí porque los títulos y párrafos se escapan antes; no se añade HTML arbitrario. El flujo es: entrada HTTP o informe → `renderizar_dashboard` → `construir_pestanas()` → plantilla → navegador. No se añaden rutas ni peticiones al cambiar de pestaña.

`.edu-deep` limita la lectura a 960 px; `.edu-deep-block` separa los pasos con espacio y borde discreto. Los párrafos usan como máximo 85 `ch`, unidad aproximada basada en anchura de caracteres. `overflow-wrap:anywhere` permite partir expresiones largas en móvil. Se reutilizan los estilos y los controles de pestañas, sin modificar JavaScript, formularios ni gráficas. No hay dependencias nuevas ni cambios de ejecución.

## 4. INTERPRETACIÓN FÍSICA / INGENIERÍA

| Sección | Progresión y distinciones que se enseñan |
| --- | --- |
| Simulación | Ciclo de cuatro estados; gas ideal frente a propiedades constantes; primera y segunda ley; referencias isentrópicas; eficiencias; pérdida δ; restricciones y ejemplo de presiones. |
| Resultados | Energía específica frente a potencia; signos; `Δh=cₚΔT`; cierre energético; deducción del rendimiento ideal; interpretación de T–s/p–v; ejemplo con balance. |
| Optimización | Objetivos A/B; intervalo abierto; derivada y segunda derivada del trabajo; derivada del cociente de rendimiento; búsqueda logarítmica y sección áurea; máximo frente a supremo. |
| Sensibilidad | OFAT de cinco factores; R fija y A/B reoptimizadas; diferencias centrales/unilaterales; h/h2; signo, normalización y huecos; límites e interacciones no estudiadas. |
| Mapa | Ejes rₚ/T₃; filas y columnas; ecuaciones por nodo; clasificación; óptimos por fila; escalas y cortes; diferencia entre máximo discreto y continuo. |
| Segunda ley | Balance de entropía; logaritmos y unidades; referencia relativa; concepto de exergía física; generación adiabática; Gouy–Stodola parcial; tolerancias y gráficas. |

La deducción ideal introduce `x=rₚᵃ`, `T₂=T₁x` y `T₄=T₃/x`; entonces `(T₄−T₁)/(T₃−T₂)=1/x` y `η=1−1/x` si el calor es positivo. Requiere el mismo gas caloríficamente perfecto, equipos isentrópicos y ausencia de pérdida de presión. No es el rendimiento general del modelo no ideal.

En segunda ley se enseña `ds=cₚdT/T−Rdp/p` e integración con constantes. Los equipos son adiabáticos y por eso su variación de entropía coincide con generación; eso no vale automáticamente para la cámara. La exergía física de flujo se define conceptualmente, pero no se presenta como salida: el código solo calcula destrucción de compresor y turbina mediante `T₀sgen`. Su suma sigue siendo parcial. No se añade combustible, presión ambiental ni eficiencia exergética global.

## 5. Ejemplo reproducible y experimentos

Con `T₁=300 K`, `T₃=1200 K`, `γ=1,4`, `cₚ=1000 J/(kg·K)`, eficiencias uno y δ cero, tomar `rₚ=2**3.5` produce `T₂≈600 K` y `T₄≈600 K`. El evaluador final devuelve consumo ≈300, producción ≈600, trabajo neto 300 y calor ≈600 kJ/kg; rendimiento ≈0,5. El rechazo equivalente es 300 kJ/kg y el balance cierra. El candidato de máximo trabajo es `11,313708498984768`; la frontera ideal es 128 y el supremo de rendimiento 0,75, sin punto motor en ella. La cancelación de entropía del compresor ideal da cero con estas entradas. Son ejemplos ilustrativos recomputados en esta tarea, no la salida del formulario predeterminado.

Experimentos sin cambiar el código:

1. Leer los ocho bloques de Simulación y pasar a Uso: los mismos campos permanecen, sin recalcular por cambiar de pestaña.
2. Comparar un ideal con una sola pérdida para relacionar el cambio de estados con trabajo/calor.
3. En sensibilidad, comparar R y A para distinguir pendiente a diseño fijo de respuesta reoptimizada.
4. Refinar columnas del mapa manteniendo temperaturas y entradas: cambia detalle muestreado, no el óptimo independiente de cada fila común.
5. Cambiar T₀ para confirmar que escala destrucción sin alterar los estados del ciclo.

## 6. Iteración de cierre — 25/10/2026

Se retoma y revisa el borrador existente, se completa la extensión a 707/708/717/711/731/733 palabras (cuerpo sin títulos), se amplían Informes/Ayuda y se añade el estilo de lectura. Se precisa que el filtro de salida casi nula en sensibilidad puede omitir tanto derivada como normalización. Se conserva la diferencia entre algoritmos del gas perfecto y cp(T).

Archivos afectados: `guias_educativas.py`, `static/style.css`, `tests/test_guias_educativas.py`, el manual y los dos documentos 19. Ningún módulo científico, dependencia, plantilla ni JavaScript requiere modificación. No se regeneran informes del usuario para revisar textos.

### Comprobaciones de esta tarea

- Nueve pruebas educativas correctas: seis anteriores y tres nuevas. Verifican presencia/estructura, separación de pestañas, extensión, escape y ubicación de cada título y párrafo mediante GET Flask.
- Navegador real: seis pestañas de fundamentos con ocho bloques, a 1280 y 390 px; anchura documental 1265 y 375 px respectivamente, sin desbordamiento horizontal. No se afirma que esta comprobación mida contraste de todas las gráficas o toda interacción previa.
- Ejemplos numéricos anteriores recomputados con `evaluar_punto`, `calcular_candidato_analitico` y `cambio_entropia`.
- La primera suite dentro del sandbox ejecutó 257 pruebas en 103,315 s: 6 fallos, 110 errores y 8 omisiones; se observaron denegaciones de permisos en archivos temporales que provocaban también respuestas HTTP 500. Ese intento no se considera una suite correcta. Se repite fuera del sandbox mediante autorización, sin modificar el código para ocultar el problema.
- Comparación binaria de los 13 módulos Python de raíz ajenos a las guías frente a HEAD: ninguna diferencia. Sintaxis de guías y pruebas comprobada mediante AST; enlaces de los nuevos documentos comprobados y `git diff --check` correcto. La publicación no cambia main ni requiere rebase.
- El primer intento fuera del sandbox ejecutó 307 pruebas en 180,981 s: seis fallos de aserción y dos errores, con ocho omisiones. Una aserción educativa exigía la frase «no calcula empuje»; se conserva esa formulación en la explicación ampliada. Las otras cinco aserciones comparan descargas LF con archivos CRLF: cuatro subcasos de recuperación y uno de integridad JSON. Los dos errores son `WinError 1314` al crear enlaces simbólicos. El número de fallos incluye subcasos, no necesariamente métodos distintos.
- Contraste de 23 pruebas de informes/integración con el módulo educativo original de HEAD cargado solo en memoria: cuatro fallos LF/CRLF y dos errores de privilegios, reproducidos en 24,664 s. No se cambia el checkout ni el módulo original. Un primer ejecutor abreviado desactivaba registros globales y causó además una aserción de `assertLogs`; se eliminó esa alteración del ejecutor y se repitió el contraste. Ese resultado intermedio no se atribuye al producto.
- Contraste ampliado final con las guías originales, incluyendo integridad JSON: **35 pruebas en 33,718 s, cinco aserciones LF/CRLF y dos errores de privilegios**, coincidentes con las incidencias restantes de la suite final. Se confirma así su reproducción sin la ampliación educativa.
- Suite completa final fuera del sandbox: **307 pruebas en 122,694 s, cinco fallos LF/CRLF, dos errores de privilegios y ocho omisiones**. Las ocho omisiones corresponden a comparaciones opcionales con SciPy no instalado. No se afirma que toda la suite pase. Las nueve pruebas educativas y la regresión de texto quedan correctas. El ejecutor temporal solo abrevia los mensajes para evitar volcar HTML/Base64 y se elimina antes del commit. No se equiparan estas pruebas a validación experimental.

### Limitaciones y estado Git

Se conserva el modelo caloríficamente perfecto y el alcance parcial de segunda ley. La revisión es de consistencia de texto/código, pruebas de implementación y presentación, sin datos experimentales externos. En la base no existe `.github/workflows`. La CLI `gh` no está disponible; la publicación usa Git.

La referencia cp(T) permanece en su HEAD indicado y conserva su archivo ajeno de planificación sin seguimiento; no se escribe allí. El commit propio de esta fase está pendiente al redactar este documento; el hash final se informa después de crearlo, sin modificar main ni hacer merges o rebases.
