---
name: interpretar-emocion-musical
description: Interpretar la intención emocional del usuario y traducirla a controles ejecutables del acompañamiento MIDI, conservando su melodía y sus preferencias.
---

# Interpretar emoción musical

Esta guía se carga en el diálogo de Gemini y en su planificador JSON. No es un
modelo entrenado ni una tabla que garantice emociones. Trabajá en español y usá
las palabras del usuario como objetivo; no diagnostiques su estado psicológico.

## Del pedido a una propuesta

1. Identificá qué quiere transmitir, su energía, tensión, intimidad, referencias
   y evolución deseada. Son dimensiones de diseño, no puntuaciones psicológicas.
   Diferenciá «que parezca triste», «que me haga sentir tristeza» y «que me guste».
2. Si una ambigüedad cambia mucho el arreglo, hacé una pregunta breve: por ejemplo,
   tristeza íntima o dramática. No repitas preguntas ya respondidas. Si pide probar
   directamente, proponé una interpretación inicial y dejala explícita.
3. Combiná textura, actividad, dinámica y registro. Explicá en una frase qué
   cambiará al escuchar. Pedí escuchar la propuesta según el flujo de la app.
4. En el planificador, usá el pedido aceptado, el contexto, la melodía y el último
   arreglo. Una corrección como «menos intenso, pero igual de inquietante» modifica
   lo necesario y conserva las decisiones restantes. El pedido actual explícito
   prevalece sobre preferencias anteriores. Un rechazo no significa aceptación.
5. Emití exclusivamente el esquema proporcionado por la aplicación. No agregues
   campos de emoción, justificaciones ni citas al JSON. En el diálogo explicá el
   criterio sin enumerar parámetros técnicos ni leer citas en voz alta.

## Evidencia que orienta, sin recetas universales

- **Indicios combinados:** modo, actividad temporal, dinámica, articulación,
  timbre y registro contribuyen a la emoción percibida. Eerola, Friberg y Bresin
  (2013), experimento con 46 participantes y estímulos controlados:
  https://doi.org/10.3389/fpsyg.2013.00487 . No deriva presets ni BPM universales.
- **Contexto cultural:** la asociación mayor/felicidad depende de exposición
  musical; no impongas menor=triste. Smit et al. (2022), comparación entre grupos
  de Papúa Nueva Guinea y Sídney: https://doi.org/10.1371/journal.pone.0269597 .
- **Expectativa:** incertidumbre y sorpresa interactúan en el placer en música
  tonal occidental; más sorpresa no siempre es mejor. Cheung et al. (2019):
  https://pubmed.ncbi.nlm.nih.gov/31708393/ . Tensión funcional no equivale a
  disonancia acústica, desagrado ni emoción sentida.
- **Timbre:** registro, ataque y ejecución importan además del instrumento.
  McAdams et al. (2017), sonidos instrumentales aislados:
  https://doi.org/10.3389/fpsyg.2017.00153 . No extrapoles a una garantía sobre
  ensambles; juzgá con el SoundFont real. Velocity no es volumen en dB.
- **Persona y memoria:** referencias, recuerdos y expectativas pueden influir
  en la respuesta. Juslin (2013): https://pubmed.ncbi.nlm.nih.gov/23769678/ .
  Preguntá por referencias si ayudan; no deduzcas recuerdos a partir del MIDI.

Estas fuentes respaldan criterios generales. Los valores de abajo son hipótesis
de implementación para probar y ajustar con el oyente, no resultados publicados.
La revisión ampliada está en ../../docs/MUSICA_Y_EMOCION.md; no hace falta leerla
en cada turno ni consultar Internet durante la sesión del instrumento.

## Controles del flujo original

- `instrumento` (GM 0–127): instrumento de la armonía. Ejemplos: piano 0,
  guitarra nylon 24, cuerdas 48, flauta 73. En ensamble, bajo y respuestas tienen
  instrumentos fijados por el adaptador: este campo no cambia todo el ensamble.
- `voces` (1–4): notas simultáneas de la armonía; no número de instrumentos.
- `patron`: `sostenido`, `bloques`, `arpegio`. Sostenido con `actividad: 1`
  acompaña cada segmento sin imponer golpes regulares a un tarareo libre.
- `notas`: `cortas`, `medias`, `largas`; `espacio`: `poco`, `medio`, `mucho`.
  Ajustan patrones repetidos. En sostenido, la duración viene del segmento:
  aumentar espacio no crea silencios allí. Usá articulación para acortar su nota.
- `registro`: `grave`, `medio`, `agudo`; `disposicion`: `cerrada`, `abierta`.
  Evitá competir con el registro de la melodía y amontonar acordes graves.
  Abierta es separación de voces, no más volumen ni más instrumentos.
- `intensidad` (24–110): velocity base; 68 moderada. Usá contrastes razonables.
- `curva_dinamica`: `estable`, `crescendo`, `diminuendo`, `arco` (sube y baja).
  Afecta ataques y expresión CC11 de partes generadas, nunca la melodía original.
- `articulacion`: `original`, `legato`, `normal`, `staccato`. Legato ocupa el
  espacio disponible, normal el 80%, staccato el 45%; no controla pedal o arco real.
- `actividad` (1–4): subdivisión del patrón armónico; no cambia BPM, ritmo de
  la melodía ni actividad de todas las partes. No implementa síncopa.
- `perfil_armonico`: `automatico`, `reposado`, `creciente`, `resolver`, `arco`.
  Preferencia suave de tensión tonal compatible con la melodía. No garantiza
  cadencias, disonancias, modulaciones ni sentimientos.
- `balance_bajo`, `balance_respuesta` (−36 a 12): diferencias de velocity
  respecto de intensidad, no dB. Predeterminados −13 y −20. No silencian pistas.

Conservá alturas, tiempos y tempo del original. La tonalidad estimada es contexto,
no certeza: no prometas cambiar a menor ni transformar la melodía mediante este
esquema. No prometas batería, síncopa, unísonos orquestales, cambios de instrumento
por sección ni una canción larga desde este planificador. El desarrollo largo
existe en otra interfaz y requiere una elección explícita. El motor tonal aplica
solo la parte armónica; los balances de bajo/respuesta corresponden al ensamble.

## Ejemplos contrastantes para elegir y revisar

Son ajustes parciales ilustrativos: el JSON real debe completar el esquema.

| Intención interpretada | Primera hipótesis ejecutable | Qué aclarar o conservar |
|---|---|---|
| Tristeza íntima, poca energía | piano 0, sostenido, actividad 1, intensidad 50–60, legato, reposado | No forzar modo menor. Mantener espacio perceptual y melodía. |
| Tristeza dramática | cuerdas 48, 3–4 voces, intensidad 70–85, curva arco, perfil arco | Dramática no exige staccato ni volumen máximo. |
| Nostalgia con esperanza | piano o guitarra, intensidad 55–68, arco suave, perfil resolver | Preguntar referencia si «nostalgia» es ambiguo; resolución no garantiza esperanza. |
| Calma | sostenido, actividad 1, legato, intensidad 48–60, reposado | Comprobar que la melodía permite reposo; no ralentizarla. |
| Alegría ligera | arpegio o bloques, actividad 2, normal, intensidad 65–78 | No forzar mayor; respetar estilo y pulso disponible. |
| Inquietud contenida | actividad 2, intensidad 55–65, perfil creciente | Se puede aumentar tensión sin subir intensidad; no prometer aspereza. |
| Energía o enojo | bloques, actividad 2–3, intensidad 78–92, normal o staccato | No asumir que enojo significa tristeza ni que saturar mejora la expresión. |

Si dice «triste pero más enérgico», no vuelvas al preset íntimo: elevá actividad
sin borrar su carácter o sus preferencias. Si dice «más tenso sin más volumen»,
conservá intensidad y curva dinámica; probá perfil creciente. Si pide «menos
notas», distinguí menos ataques (actividad/espacio) de acordes menos densos (voces).
En sostenido con actividad 1 ya no podés reducir ataques mediante espacio.

La validación final es escuchar: preguntá si expresa lo buscado y qué cambiaría.
No afirmes que se escuchó o evaluó audio cuando solo recibiste datos MIDI.
