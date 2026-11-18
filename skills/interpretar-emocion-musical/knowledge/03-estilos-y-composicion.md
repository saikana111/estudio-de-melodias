# Estilos, forma y desarrollo: conocimiento musical aplicable

## Reglas por estilo y textura

Estas fichas modifican un perfil emocional; no son copias de artistas ni motores
de género completos. La preferencia explícita del usuario gana sobre la ficha.
No confundas un timbre con un género: un piano eléctrico no basta para hacer jazz.

| Contexto | Decisiones ejecutables | Qué no prometer |
|---|---|---|
| Balada íntima | Piano 0 o nylon 24; 2–3 voces; sostenido/1 o arpegio medias/medio/1; intensidad 54–66. Priorizar melodía, respuestas discretas. | Una estructura de estrofa/estribillo desde el JSON actual. |
| Canción acústica | Nylon 24 o acero 25; arpegio 3 voces, medias/medio/2 para flujo regular; normal. Si tarareo libre, volver a sostenido/1. | Rasgueos físicos, cejillas o digitación. |
| Piano minimalista | Piano 0; arpegio de 2–3 alturas, patrón y actividad estables; dinámica moderada. Mantener una idea reconocible. | Ostinato exacto de alturas: el motor cambia notas según armonía. |
| Fondo ambiental | Cuerdas 48 o coro 52; sostenido/1; legato; intensidad 48–64; disposición abierta si viable. | Reverb, texturas granulares o drones independientes. |
| Cámara lírica | Cuerdas 48, 3 voces, sostenido/1, legato, arco; medio. Bajo y respuestas acompañan sin competir. | Contrapunto estricto o técnicas de arco realistas. |
| Cine contemplativo | Piano 0 o cuerdas 48; poca actividad, curva arco, perfil automático/reposado según tensión deseada. | Sincronización exacta con escenas. |
| Cine de tensión | Cuerdas 48, perfil creciente; elegir entre sostén/1 y bloques/2 según energía. Aumentar dinámica solo si pide intensidad. | Clusters, glissandi o disonancia controlada. |
| Cine heroico | Corno 60 o cuerdas 48; 3–4 voces, medio/abierta, 76–88, crescendo o arco; bloques moderados. | Orquesta completa, percusión épica o cambios de metales por sección. |
| Canción de cuna | Piano 0 o caja de música 10; 2–3 voces, actividad 1, 46–58, articulación ligada o normal. | Balanceo de 6/8 inferido de un archivo sin metro fiable. |
| Juego delicado | Pizzicato 45 o celesta 8; bloques/arpegio, medias/medio/2, staccato, 58–72. | Que sonido agudo signifique siempre alegría. |
| Pop acústico | Piano/guitarra, bloques o arpegio, actividad 2, normal, 65–78. Usar acordes legibles y melodía destacada. | Groove pop completo sin batería. |
| Rock, aproximación de apoyo | Bloques, 2–3 voces, ataques marcados, 78–90. Conservar espacio de la melodía. | Power chords garantizados, riffs de guitarra, distorsión o batería. |
| Jazz, aproximación tímbrica | Piano 0 o vibráfono 11; arpegio/bloques moderados y aire con articulación original. Preguntar qué rasgo busca. | Séptimas, tensiones extendidas, swing y reharmonización jazz que el motor no implementa. |
| Bossa/latino, aproximación tímbrica | Nylon 24, intensidad moderada, textura transparente. Si busca el ritmo, explicar la limitación. | Síncopa, clave o patrón de bossa auténticos mediante actividad. |
| Electrónica/lo-fi, aproximación tímbrica | Piano eléctrico 4; patrón repetido sencillo, dinámica contenida. | Beat, sidechain, filtros, saturación o ruido de cinta. |
| Himno/solemnidad | Órgano 19 o coro 52; 3–4 voces, sostenido, actividad 1, normal/legato, reposado o resolver. | Reglas corales SATB, letras cantadas o efecto espiritual universal. |

## Armonía y melodía

**Ejecutable:** el motor busca acordes compatibles con las notas y favorece
continuidad entre disposiciones. Seleccioná textura/registro/perfil para que
la armonía apoye el fraseo. No escribas acordes puntuales en campos inventados.

**Criterio musical:** notas largas o acentuadas suelen tener más peso estructural
que notas de paso. Una nota ajena al acorde puede ser paso, bordadura, apoyatura
o suspensión; no la llames error solo por ser cromática. Sin duración/acento o
contexto suficiente, no diagnostiques su función. No corrijas automáticamente
la escala del original para producir una emoción.

**Conducción de voces:** movimientos pequeños ayudan a unir acordes; saltos
grandes pueden marcar contraste pero también distraer. El motor ya penaliza
saltos. No prometas reglas de contrapunto estricto como evitar todas las quintas
paralelas: no hay tal garantía. Disposición abierta no equivale a movimiento suave.

**Modo y color:** mayor/menor pueden orientar expectativas dentro de ciertas
tradiciones, pero no son etiquetas emocionales universales. Una melodía mayor
puede acompañarse con menor energía y más intimidad sin cambiarla a menor.
Cambiar modo o modular requiere una ruta distinta: el esquema actual no lo expresa.

**Tensión:** separá tensión funcional (dirección armónica), aspereza sonora
(interacción de frecuencias/timbre), densidad (notas simultáneas) y energía
(actividad/dinámica). «Más tenso» no implica subir las cuatro. El perfil controla
solo una preferencia funcional; voces no añade disonancia de forma controlada.

## Fraseo, espacio y jerarquía

**Ejecutable:** una sola melodía sigue siendo protagonista. Frente a un canto
rápido o rubato, sostenido con actividad 1 evita una capa de ataques competidora.
Frente a notas largas, arpegios moderados pueden aportar movimiento sin tocar
sus alturas. Los balances reducen la competencia entre partes.

**Llamada y respuesta:** el motor de ensamble responde durante silencios aptos,
con una figura corta derivada del contorno. No promete responder a cada frase
ni producir una segunda melodía independiente. Si la entrada no tiene huecos,
subir balance_respuesta no crea respuestas.

**Respiración:** usar articulación normal/staccato o patrones repetidos con
original deja espacio. Sostenido+legato mantiene continuidad, incluso con
espacio=mucho. No describas esa combinación como pausas entre acordes.

**Unidad:** repetir timbre, registro y textura da continuidad perceptual. No
equivale a unísono. Unísono exige las mismas alturas; homorritmia ataques comunes.
Bloques alinea ataques de la parte armónica, no de todos los instrumentos.

## Diseñar un recorrido emocional

| Recorrido solicitado | Aproximación ejecutable en un acompañamiento | Límite |
|---|---|---|
| Serenidad constante | reposado + estable + actividad 1 | El original puede contener tensión propia. |
| Expectativa que aumenta | creciente + estable si no quiere más volumen; crescendo si sí | Una curva global, no sucesión de escenas. |
| Clímax y descanso | perfil arco + curva arco | No coloca un clímax en un segundo exacto. |
| Alivio final | resolver + estable o diminuendo | Preferencia, no cadencia final obligatoria. |
| Desvanecimiento | diminuendo, actividad baja | No borra ni ralentiza la melodía. |
| Energía constante con dudas | creciente + estable + actividad 2 | Tensión y energía pueden variar por separado. |
| De tristeza a celebración | Explicar que hacen falta cambios por secciones | Un perfil global no cambia instrumentos y ritmo a mitad. |
| Sorpresa súbita o corte dramático | Requiere nuevos eventos/edición estructural | No sustituirlo silenciosamente por crescendo. |

## Desarrollo de una pieza más larga

Este conocimiento sirve para conversar y orientar una ampliación; no agregues
estas instrucciones como campos al esquema de acompañamiento. El motor de canción
existente ofrece tema, variación, contraste, regreso y coda en otra interfaz,
con límites de entrada. No lo actives por inferir que «componer» significa alargar.

| Técnica | Para qué sirve y cómo decidir | Estado actual |
|---|---|---|
| Repetición reconocible | Establece identidad antes de variar. Repetir una idea permite percibir sus cambios. | El motor reutiliza ciertos motivos armónicos; no hay interruptor en Arreglo. |
| Variación contenida | Cambiar una dimensión manteniendo el motivo; da continuidad con novedad. | Revisión de textura/dinámica ejecutable; variación de notas solo en modo canción. |
| Contraste de sección | Cambiar energía, registro o textura para diferenciar una sección, conservando algún vínculo. | Cambios de expresión por sección en modo canción; no desde Arreglo. |
| Regreso | Recuperar el motivo tras contraste crea reconocimiento. Puede regresar más pleno o más íntimo. | Modo canción; no forma arbitraria controlable por este JSON. |
| Coda | Reducir material y orientar el cierre; puede ser serena, afirmativa o suspendida. | Coda concreta del modo canción; no todas esas variantes están implementadas. |
| Secuencia diatónica | Repetir un motivo en otro grado mantiene su contorno y crea dirección. | Uso limitado en el contraste del modo canción; no secuencias libres. |
| Fragmentación | Repetir una parte breve de un motivo puede concentrar energía. No confundir con notas aleatorias. | Requiere ampliar el planificador de motivos. |
| Aumentación/disminución | Escalar duraciones del motivo conserva relaciones y cambia sensación de amplitud. | Requiere transformar la melodía; no es actividad del acompañamiento. |
| Pedal armónico | Sostener una altura bajo armonías cambiantes genera continuidad/tensión contextual. | Bajo actual sigue raíces; requiere ampliar motor. |
| Ostinato exacto | Figura reiterada con identidad rítmica/melódica; permite desarrollo sobre una base. | Arpegio es aproximación textural, no ostinato exacto configurable. |
| Modulación | Cambiar centro tonal puede dar dirección formal. Necesita preparación y coherencia con la melodía. | Requiere ampliar motor; no seleccionar instrumento más brillante como sustituto literal. |
| Contrapunto | Líneas independientes que se relacionan armónica y rítmicamente. | Respuestas en huecos no equivalen a contrapunto; requiere ampliar motor. |

Cuando el usuario pida una técnica no implementada, conservá la intención:
por ejemplo, para «que crezca la expectativa» podés proponer creciente/crescendo;
para «modulá a otro tono», esa propuesta no cumple la operación solicitada y debés
decirlo. Nunca presentes una aproximación expresiva como transformación exacta.

## Mezclas de intención: resolver conflictos sin perder matices

- **Triste + esperanzado:** sostener intimidad y baja/moderada energía, orientar
  cierre con resolver. No obligar alegría, más volumen o cambio de modo.
- **Triste + enérgico:** ritmo más activo, intensidad según pedido; conservar el
  timbre y dirección aprobados. Tristeza no exige lentitud absoluta.
- **Feliz + tranquilo:** reposado y actividad 1; no usar automáticamente staccato
  y actividad 4. Alegría puede ser serena.
- **Inquietante + suave:** creciente, intensidad baja, sin densidad excesiva.
  Para suspenso por silencio, usar original en repetidos, no legato sostenido.
- **Épico + íntimo:** preguntar si quiere inicio íntimo y expansión o grandeza
  contenida. En una sola textura, amplitud de voces con intensidad moderada;
  para transformación temporal compleja, explicar necesidad de secciones.
- **Romántico + no empalagoso:** priorizar referencia del usuario; limitar arco
  dinámico y densidad, evitar asumir cuerdas/coro y clímax grandes.
- **Oscuro + no triste:** no reducir energía automáticamente; usar timbre/registro
  prudente y dirección de tensión. Si requiere aspereza, aclarar su límite.
- **Nostálgico + referencia personal:** conservar el instrumento o carácter
  asociado a esa referencia aunque contradiga una ficha. No inventar recuerdos.

Después de escuchar, distinguí: qué expresa, qué hizo sentir, qué le gustó y qué
quiere cambiar. Guardar una preferencia no convierte la hipótesis en regla universal.
