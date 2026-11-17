# Música, psicología y generación expresiva

Seguimiento: las carencias del motor identificadas aquí dieron lugar a los
[controles expresivos y la reproducción SoundFont de 0.3.0](EXPRESION_Y_SONIDO.md).
La sección «Qué falta en nuestro código» documenta el estado previo a esa implementación.

Revisión orientada al proyecto, 16 de noviembre de 2026. No es una revisión
sistemática ni un metaanálisis. Se consultaron investigaciones, resúmenes de
autores y documentación oficial; algunas páginas de texto completo no estuvieron
disponibles. No se instalaron ni evaluaron modelos nuevos. Las propuestas de
ingeniería de este documento no deben confundirse con resultados experimentales.

## Qué queremos conseguir

Conviene registrar por separado: intención del creador, emoción percibida en la
música, emoción sentida por quien escucha y preferencia personal. Que un resultado
parezca triste, entristezca o guste son respuestas diferentes. El trabajo de
[Zentner, Grandjean y Scherer (2008)](https://pubmed.ncbi.nlm.nih.gov/18729581/)
estudia vocabulario emocional específicamente musical y da origen a GEMS. Es una
referencia de evaluación, no una receta de composición.

Como propuesta de diseño, representar la intención mediante energía, valencia
(carácter agradable/desagradable), tensión, intimidad y una evolución temporal,
sin eliminar las palabras originales del usuario. Estas dimensiones no son una
escala psicológica validada como conjunto; son controles candidatos del producto.
«Nostalgia con esperanza» requiere más contexto que una etiqueta positivo/negativo.

## Evidencia y límites

### Modo, ritmo, dinámica y articulación

[Eerola, Friberg y Bresin (2013)](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2013.00487/full)
manipulan modo, actividad temporal, dinámica, articulación, timbre y registro.
Participaron 46 personas, muchas con experiencia musical. Hay varios indicios
acústicos útiles para comunicar emoción, no un único parámetro determinante.
Su medida temporal usa ataques por segundo: no debemos convertirla directamente
en una tabla universal de BPM. Su conjunto de estímulos tampoco representa todos
los géneros ni culturas.

Aplicación propuesta: controlar actividad del acompañamiento, duración de las notas
y dinámica por separado. Preservar el tempo y los tiempos originales del tarareo
por defecto. Más ataques por segundo puede lograrse con subdivisiones sin acelerar
la melodía. No asignar «tristeza = 60 BPM».

### Mayor y menor no son códigos universales

[Smit et al. (2022)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0269597)
comparan comunidades de Papúa Nueva Guinea con distinta exposición musical y
grupos de Sídney. La asociación entre mayor y mayor felicidad dependió de la
exposición a música de influencia occidental; no demostraron un efecto universal.
Tampoco demostraron que la biología no intervenga.

Aplicación propuesta: preguntar referencias y estilo; usar el modo como hipótesis
musical. No convertir automáticamente a menor una melodía que el usuario desea
conservar: la armonización debe respetar sus notas y explicar incompatibilidades.

### Tensión, disonancia y placer no son equivalentes

[McDermott et al. (2016)](https://mcdermottlab.mit.edu/bib2php/pubs/makeAbs.php?loc=mcdermott16)
aportan evidencia de variación cultural en la preferencia por consonancia. No
corresponde llamar «mala» a toda disonancia. Conviene distinguir aspereza acústica,
distancia tonal, sorpresa y agrado del oyente.

[Cheung et al. (2019)](https://pubmed.ncbi.nlm.nih.gov/31708393/) relacionan placer
con la interacción entre incertidumbre previa y sorpresa armónica en música tonal
occidental. Su resultado no dice «cuanta más sorpresa, mejor». La secuencia y las
expectativas importan.

Aplicación propuesta: componer una trayectoria de preparación, tensión y reposo;
alternar elementos reconocibles y variaciones. Un acorde aislado no basta para
medir esa trayectoria. No tratar una puntuación de tensión como lectura emocional
de una persona.

### Timbre, registro y ejecución

[McAdams et al. (2017)](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2017.00153/full)
examinan cualidades afectivas de sonidos instrumentales considerando registro,
ataque y técnica de ejecución. El nombre del instrumento no describe por sí solo
su efecto expresivo. El estudio de tonos aislados no demuestra el efecto de una
orquestación completa.

Aplicación propuesta: evaluar con el mismo SoundFont/sintetizador que usará el
instrumento. La vista previa sencilla del panel no reproduce los timbres elegidos.
MIDI velocity no equivale a sonoridad percibida en dB: depende del sintetizador y
de las muestras. Cuerdas sostenidas, cortas o con ataques bruscos no son una única
categoría expresiva.

### Síncopa y ganas de moverse

[Witek et al. (2014)](https://doi.org/10.1371/journal.pone.0094446) encuentran una
relación de U invertida entre síncopa y valoraciones de placer/ganas de moverse
en patrones de batería: grados intermedios recibieron valoraciones mayores.
No implica que toda pieza necesite síncopa moderada ni que se haya medido el
movimiento corporal efectivo en ese experimento.

Aplicación propuesta: agregar patrones rítmicos graduados únicamente cuando el
estilo y un pulso confirmado lo justifiquen. Un tarareo libre no proporciona por
sí solo una grilla fiable para imponer groove.

### Unísono, sincronía y unión

Unísono significa tocar la misma altura; homorritmia significa compartir el ritmo,
incluso con alturas diferentes. Varias pistas duplicadas no equivalen necesariamente
a una sección de cuerdas real.

[Tarr et al. (2015)](https://pubmed.ncbi.nlm.nih.gov/26510676/) estudian sincronía y
esfuerzo durante baile grupal, con medidas de vínculo social. Eso no demuestra que
escuchar cuerdas al unísono produzca automáticamente unión social. La extrapolación
sería injustificada. «Sensación de unidad» puede ser una intención compositiva a
explorar mediante ataques compartidos o duplicaciones, no una garantía psicológica.

### Memoria y contexto

[Juslin (2013)](https://pubmed.ncbi.nlm.nih.gov/23769678/) propone el marco BRECVEMA:
reflejos, sincronización rítmica, condicionamiento, contagio, imágenes, recuerdos,
expectativas y juicio estético. Es un marco explicativo, no un algoritmo que
prediga exactamente la emoción de cualquier oyente.

Aplicación propuesta: preguntar qué significa «nostálgico» para esa persona y
guardar, con su elección, referencias y motivos de aceptación/rechazo. Una memoria
biográfica no se puede deducir de la tonalidad del MIDI.

## Herramientas que vale la pena evaluar

| Recurso | Función documentada | Papel propuesto y límite |
|---|---|---|
| [music21](https://music21.org/music21docs/) | Análisis de notas, acordes, tonalidad, intervalos y números romanos | Verificar coherencia armónica; ya aparece en la app original. No es un predictor de emoción. |
| [Partitura](https://partitura.readthedocs.io/en/latest/modules/partitura.musicanalysis.html) | Análisis simbólico; incluye `estimate_tonaltension` | Comparar curvas de tensión tonal entre versiones. Es un modelo estructural, no una medición de ansiedad o emoción sentida. |
| [MusPy](https://muspy.readthedocs.io/en/stable/metrics.html) | Métricas de música simbólica, como entropía de alturas y consistencia rítmica | Describir y verificar resultados. Más entropía o consistencia no implica mayor calidad. |
| [incon](https://github.com/pmcharrison/incon) | Modelos de consonancia simultánea en R | Investigación de acordes y aspereza; no cubre toda la armonía contextual. Evaluarlo fuera del flujo liviano de generación. |
| [Essentia](https://essentia.upf.edu/models.html) | Modelos de audio para etiquetas y regresión de valencia/activación, incluidos DEAM y emoMusic | Segundo evaluador sobre audio renderizado; no reemplaza la escucha humana ni genera MIDI. |
| [EMOPIA](https://github.com/annahung31/EMOPIA) | Datos de piano pop y código para clasificación/generación condicionada por emoción | Referencia para experimentos con MIDI. No asumir generalización a ensambles ni preservación de una melodía dada. |

Los modelos de Essentia del MTG tienen condiciones CC BY-NC-SA 4.0 y una opción
de licencia propietaria; la biblioteca y sus dependencias tienen condiciones
distintas. Revisar [su documentación de licencias](https://essentia.upf.edu/licensing_information.html)
antes de integrarlos en un producto. No asumir que pesos y código tienen la misma
licencia.

El [repositorio de EMOPIA](https://github.com/annahung31/EMOPIA) especifica licencia
no comercial para el dataset y una instalación de referencia con Torch 1.7.0.
Distribuye MIDI transcrito y referencias a audio, no todo el audio original.
No es una dependencia lista para instalar sin evaluar compatibilidad y derechos.
No descargamos sus datos ni ejecutamos sus modelos durante esta revisión.

[EMMA (Strauss et al., 2024)](https://link.springer.com/article/10.3758/s13428-024-02336-0)
es una base de fragmentos valorados por emoción sentida mediante GEMS: su publicación
inicial describe 364 fragmentos y 517 participantes. Es útil para diseñar preguntas
y contrastar ejemplos. No es una biblioteca de generación ni convierte la etiqueta
de un fragmento en una receta causal.

## Qué falta en nuestro código

Inspección local: `gem.Arreglo` describe instrumento, voces, duración, espacio,
registro, disposición y patrón. No representa una trayectoria emocional.
`musical.realize` usa velocidades de acompañamiento prefijadas (68/58); bajo y
respuestas también tienen valores prefijados. El motor dispone de búsqueda armónica
y conducción de voces, pero no implementa un control general de dinámica expresiva,
síncopa, tensión por sección o articulación instrumental.

No todos los campos actúan en todo patrón: por ejemplo, el sostenido usa la duración
del segmento armónico, en lugar de la unidad de duración/espacio empleada en los
patrones repetidos. Por eso hay que verificar el MIDI resultante y no conformarse
con que Gemini produzca un JSON válido.

## Plan propuesto, sin cambiar todavía el comportamiento

1. Construir fichas de evidencia: fuente, población/estímulo, emoción percibida o
   sentida, hallazgo, límites, controles disponibles y prueba auditiva sugerida.
   Separar hallazgos de hipótesis de orquestación.
2. Pedir intención, estilo/referencias y restricciones sobre la melodía. No añadir
   una pantalla por cada concepto: conservar el diálogo y Sí/No del instrumento.
3. Traducir la intención a un plan por frases; luego a controles que el generador
   efectivamente implemente. No prometer funciones todavía ausentes.
4. Agregar primero dinámica por parte/sección, balance melodía-acompañamiento,
   articulación y actividad rítmica controlada. Después, tensión/cadencias y
   transformaciones más elaboradas. Es una prioridad de ingeniería, no una
   conclusión experimental que garantice mejores composiciones.
5. Renderizar MIDI con sonido representativo del instrumento. Comparar dos
   variantes, alternando el orden y sin etiquetas emocionales sugestivas antes de
   escuchar. Si se estudia timbre o armonía, controlar sonoridad; si se estudia
   dinámica, no normalizar de manera que borre precisamente esa diferencia.
6. Preguntar por separado qué expresa, qué hizo sentir, cuánto coincide con el
   pedido y cuál prefiere. Registrar el motivo. Repetir con distintas melodías y
   oyentes; conservar desacuerdos en lugar de ocultarlos en una sola etiqueta.
7. Usar métricas estructurales y clasificadores como diagnósticos. No optimizar
   solo el puntaje de un clasificador: puede premiar atajos sonoros y sesgos del
   dataset. La prueba final sigue siendo escuchar y decidir.

Mantener generación MIDI y conversación en el host Python, con el ESP32 como
interfaz existente. La investigación y los modelos de análisis más pesados pueden
ejecutarse fuera del dispositivo; no hay razón para exigirlos en cada interacción.
Un entrenamiento adicional del LLM solo se justifica después de evaluar qué falla:
interpretación del pedido, controles insuficientes, realización musical o sonido.
