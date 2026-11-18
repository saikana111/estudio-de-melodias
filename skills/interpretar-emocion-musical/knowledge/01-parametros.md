# Reglas ejecutables de elección y revisión

## Instrumento: ataque y sostén antes que etiqueta emocional

Respetá el instrumento pedido si existe como programa GM (numeración 0–127).
Sin preferencia, elegí según textura. Estas son opciones de partida; el timbre
real depende del SoundFont y de la intensidad.

| Necesidad | Programa | Decisión musical |
|---|---|---|
| Ataque claro, intimidad, armonía legible | piano 0 | Permite acordes o arpegios; una nota larga decae aunque el MIDI siga activo. |
| Ataque redondo, ambiente suave | piano eléctrico 4 | Alternativa cálida al piano; no implica agregar efectos lo-fi. |
| Toque delicado, brillo puntual | celesta 8 o caja de música 10 | Usar intensidad 45–62 y no duplicar una melodía aguda con demasiados ataques. |
| Brillo percusivo más suave | vibráfono 11 | Notas medias/largas, actividad 1–2; no genera swing por sí solo. |
| Sonido acústico cercano | guitarra nylon 24 | Arpegio para continuidad, bloques para acordes. No simula rasgueo o digitación. |
| Ataque acústico más marcado | guitarra acero 25 | Bloques/arpegio con intensidad moderada; más ataque no exige más notas. |
| Flujo delicado y resonante | arpa 46 | Arpegio de 3–4 alturas; no genera glissandi. |
| Fondo sostenido, amplitud o drama | cuerdas 48 | Sostenido y legato; dinámica da movimiento sin añadir ataques. |
| Cuerdas de ataque corto | pizzicato 45 | Bloques/arpegio con normal o staccato; no usarlo como si sostuviera un colchón. |
| Sonido sostenido estable | órgano 19 | Acordes largos y pocas rearticulaciones; su asociación solemne depende del contexto. |
| Color coral sostenido | coro 52 | Acordes largos moderados; no genera palabras ni voces reales. |
| Carácter amplio de metales | corno 60 | Intensidad 65–85, registro medio, ataques espaciados; evitar saturar una melodía débil. |
| Una línea de viento | flauta 73 o clarinete 71 | Preferir voces 1; para acordes preferir cuerdas/piano salvo pedido explícito de sección. |

No cambies instrumento al recibir «menos fuerte»; ajustá intensidad. No cambies
un instrumento expresamente pedido para forzar el preset de una emoción.

## Textura: voces, disposición y registro

- `voces: 1`: línea monofónica de apoyo; pierde la identidad de acordes completos.
  Elegila para una segunda línea solicitada o mínimo apoyo, no como solución
  automática a «más suave». Con una voz usá `disposicion: cerrada`.
- `voces: 2`: textura desnuda, menos peso vertical. Son dos notas del acorde,
  no contrapunto independiente ni dúo con ritmos separados.
- `voces: 3`: base de acordes clara; primera opción cuando no se pide densidad.
- `voces: 4`: mayor grosor mediante duplicaciones; no implica acordes de séptima.
  Usala para amplitud/drama si la melodía no está ya muy cargada.
- `disposicion: cerrada`: alturas dentro de una octava. Elegila para compacidad,
  articulación conjunta o cuando abierta no deja sitio al bajo.
- `disposicion: abierta`: extensión mínima de una octava. Elegila para amplitud
  espacial con 2–4 voces; no suma reverb ni cambia cantidad de notas.
- `registro: medio` (MIDI 48–71): punto de partida en el ensamble; suele dejar
  sitio al bajo. Si no tenés datos fiables de registro, usá medio.
- `registro: agudo` (60–83): para elevar el acompañamiento sobre una melodía
  grave o buscar brillo. Si la melodía ya ocupa esa zona, preferí medio.
- `registro: grave` (36–59): para apoyo oscuro cuando la disposición deja lugar
  al bajo. No combines por defecto grave + abierta + 4 voces en ensamble:
  puede no existir una disposición válida con el contrabajo separado.

Elegí registro por las alturas realmente recibidas, no por «triste=grave».
No interpretes un número de canal como registro. Si el análisis no contiene
duraciones, no afirmes saber qué notas predominan por duración.

## Patrón, actividad, duración y silencios: elegirlos juntos

`patron: sostenido` mantiene la armonía durante cada segmento. Elegilo para
continuidad, calma, drama lento o tarareo libre sin pulso confirmado.
`actividad: 1` da un ataque por segmento; 2, 3 o 4 subdividen ese segmento.
`notas` y `espacio` no cambian la pauta del sostenido.

`patron: bloques` ataca las voces juntas. Elegilo para apoyos claros, firmeza,
énfasis o acordes repetidos. No implica batería ni un patrón rítmico de género.

`patron: arpegio` alterna las alturas del acorde de una en una. Elegilo para
movimiento con menos densidad simultánea. Con voces 1 repite una sola altura.
No prometas un patrón de guitarra específico, inversión fija o síncopa.

En bloques/arpegio, el intervalo entre ataques es:
`unidad(notas) × factor(espacio) / actividad`, en negras MIDI.
Unidades: cortas=0.5, medias=1, largas=2. Factores: poco=1, medio=2, mucho=4.
Son unidades del archivo, no una estimación segura del pulso humano.

| Resultado deseado con patrón repetido | notas | espacio | actividad | Intervalo entre ataques |
|---|---|---|---|---|
| Puntos muy separados | largas | mucho | 1 | 8 negras |
| Apoyo lento | largas | medio | 1 | 4 negras |
| Movimiento moderado | medias | medio | 1 | 2 negras |
| Movimiento regular | medias | medio | 2 | 1 negra |
| Movimiento ágil | medias | poco | 2 | 0.5 negras |
| Textura muy activa | cortas | poco | 2 | 0.25 negras |

Los segmentos pueden recortar esas duraciones. No selecciones cortas+poco+4
sin un pedido muy activo: produce muchos ataques. Para una melodía rápida o
irregular, preferí sostenido/1 antes de imponer otra capa rápida.

`articulacion: original` conserva la duración propia del patrón. En bloques y
arpegios ocupa hasta 90% de la unidad `notas`, recortada al próximo ataque.
Con `espacio: mucho` deja pausas útiles; preferila si el usuario pide aire real.
`legato` ocupa el 100% del intervalo entre ataques: liga la textura. Aunque
aumentes espacio, llena ese intervalo; no lo uses para prometer más silencio.
`normal` ocupa el 80% del intervalo; `staccato` el 45%: útiles para respiración
moderada o ataques claramente separados. No son pedal, arco ni técnica real.
La articulación también afecta bajo y respuestas en el ensamble.

## Dinámica: separar intensidad, evolución y balance

- `intensidad: 24–110` es velocity base, no dB. Sin referencia: 48–58 delicado,
  59–70 moderado, 71–84 presente, 85–96 enérgico. Reservá extremos para pedidos
  claros y revisión auditiva. Para «un poco más/menos fuerte», ajustá ±6 y
  conservá instrumento, actividad y armonía. Recortá siempre al rango permitido.
- `curva_dinamica: estable`: sin evolución deliberada de volumen; elegila para
  calma constante, pulso uniforme o «sin cambiar el volumen».
- `crescendo`: aumento a lo largo del acompañamiento; para acumulación/impulso.
- `diminuendo`: retirada progresiva; para desvanecerse o terminar contenido.
- `arco`: crecer y bajar; para una frase con clímax y reposo final.
  Estas curvas afectan velocidades y CC11. No existe un campo de profundidad
  del arco ni varias curvas independientes dentro de este JSON.
- `balance_bajo` y `balance_respuesta` son offsets de velocity (−36 a 12).
  Base: −13 y −20. Para una parte demasiado presente, restá 6 a su balance;
  para destacarla, sumá 6, sin cambiar intensidad de las otras partes.
  −36 reduce presencia, no silencia. Las respuestas solo aparecen si hay huecos.

Si pide «sin flauta» o «solo piano», el esquema actual no puede desactivar las
otras partes del ensamble. Explicalo y ofrecé el flujo de pista única si está
disponible; no finjas que bajar balance es quitar un instrumento.

## Tensión y dirección armónica

- `automatico`: que la compatibilidad melódica y la continuidad decidan, sin
  trayectoria extra. Usalo cuando no hay intención de tensión definida.
- `reposado`: preferencia por estabilidad; calma, sencillez o reposo continuo.
- `creciente`: preferencia por acumular tensión; anticipación, inquietud o empuje.
- `resolver`: preferencia por relajación hacia el final; alivio o cierre.
- `arco`: tensión que crece y vuelve; recorrido dramático con regreso.

Son preferencias suaves de búsqueda tonal. No aumentan cromatismo ni garantizan
un acorde final concreto. Para «más tensión sin más volumen», cambiá el perfil
a creciente y conservá intensidad, curva, instrumentos y balances.
Para «más calma sin bajar volumen», probá reposado y actividad menor, conservando
intensidad. Para «menos triste» preguntá si busca esperanza, energía o menos
drama cuando esa diferencia afecte la elección; no conviertas a mayor.

## Tabla de revisiones mínimas

| Pedido sobre un arreglo existente | Acción | Mantener |
|---|---|---|
| Más suave/fuerte | intensidad −6/+6, dentro de 24–110 | resto |
| Más/menos movimiento | actividad +1/−1, dentro de 1–4 | intensidad, instrumento, perfil |
| Menos ataques, ya actividad 1 | en repetidos subir espacio un nivel; en sostenido explicar mínimo por segmento | voces y timbre |
| Acordes menos densos | voces −1, mínimo 1; cerrada si queda 1 | ritmo, intensidad |
| Más aire entre notas | normal→staccato, o repetidos con original y mayor espacio | tempo original |
| Más conectado | legato | ataque y altura originales de la melodía |
| Más amplio | abierta si voces >1 y registro viable | intensidad y cantidad de voces |
| Menos grave | registro grave→medio o medio→agudo si no pisa la melodía | instrumento y patrón |
| Bajo tapa la melodía | balance_bajo −6 | armonía y respuesta |
| Respuestas distraen | balance_respuesta −6 | demás partes |
| Que cierre con alivio | perfil resolver; diminuendo solo si también pide retirarse | intensidad si no pidió volumen |
| Tenso pero delicado | creciente, intensidad 52–62, actividad 1–2 | delicadeza, sin aumentar todo a la vez |
| Triste pero enérgico | conservar timbre/perfil triste aceptados, aumentar actividad un nivel | no forzar alegría o modo mayor |

No alteres varios ejes a la vez para una corrección pequeña: así el usuario
puede identificar qué cambió. Si llega un límite, describilo sin afirmar haber
aplicado una modificación que no cambia el MIDI.
