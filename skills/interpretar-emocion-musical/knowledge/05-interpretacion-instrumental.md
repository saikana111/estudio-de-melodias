# Traducir un instrumento a gestos MIDI

Elegí primero qué toca la parte y después el programa. Una línea, un acorde
sostenido y golpes repetidos del mismo acorde necesitan eventos distintos.
Usá el SoundFont del proyecto para juzgar ataque, decaimiento y balance.

| Familia | Del gesto al arreglo | Qué escuchar y corregir |
|---|---|---|
| Guitarra rasgueada | Programas 24–31, bloques, 2–4 voces, rasgueo=true. El motor escalona las alturas alternando grave→agudo y agudo→grave, con un pequeño descenso de velocity a lo largo del golpe. Conserva los finales y recorta el desplazamiento en notas cortas. | Debe percibirse un golpe con recorrido. Si suena como demasiadas cuerdas o demasiado denso, bajar voces. Probar guitarra limpia 27 antes de elegir distorsión por defecto. |
| Guitarra punteada | Para arpegio, elegir 3 voces, patron=arpegio, rasgueo=false. Para una línea, voces=1. En afinación estándar las cuerdas abiertas son MIDI 40,45,50,55,59,64. Preferir medio para los acordes. | Un guitarrista toca una altura por cuerda. El escalonado actual ordena alturas y no calcula cuerda/traste. No prometer digitación, hammer-on, bend o slide. Los keyswitches dependen de una biblioteca específica. |
| Bajo eléctrico | 33 digitado o 34 con púa según el ataque. Una raíz por segmento, línea monofónica debajo del acorde. Ajustar balance_bajo si tapa la melodía. | La cuerda más grave de un cuatro cuerdas estándar da MIDI 28. Sostener cuando hay espacio; para un ataque más seco elegir articulación normal solo si el resto también debe acortarse. No prometer ghost notes o slap por cambiar velocity. |
| Piano / eléctrico | Bloques para apoyo vertical, arpegio para continuidad. Velocity moldea cada ataque. Preferir una dinámica por frase antes que variar al azar cada nota. | Con una muestra de piano, alargar una nota deja decaer el sonido. Para un fondo que crece de verdad, considerar cuerdas. El brief no programa pedal de sustain. |
| Cuerdas | 48 para sección ligada, 45 para ataques pizzicato. Para sostén, usar legato y curva arco; para pizzicato elegir notas separadas. | CC11 da forma a la intensidad sostenida. No cambia muestra de arco, vibrato ni posición. Una sección puede tocar acordes, una línea de violín solo exige considerar sus límites. |
| Flauta / clarinete | Programa 73 / 71. Para solista usar una voz o asignar respuesta_gm al rol que contesta en huecos. Dejar respiraciones entre frases. | Revisar continuidad y registro. Si el tarareo no deja silencio, la respuesta no aparece. No fabricar respiración con ruido aleatorio. |
| Batería | El instrumento se elige por nota en canal MIDI 10 (índice 9). El motor usa bombo 36, caja 38 y charles cerrado 42. La caja articula el backbeat; las corcheas débiles del charles llevan menor velocity. | Escuchar bombo con el bajo. Si parece desconectado del canto libre, probar acentos o ninguna batería. No añadir desviaciones aleatorias a todo el kit. |

Para «más real» identificá primero el defecto audible: acordes de guitarra que
atacan como teclas → rasgueo; melodía tapada → balance o registro; ataques
idénticos → acentos/fraseo; timbre incorrecto incluso en una sola nota → probar
otro programa o SoundFont. En cada revisión conservá el MIDI fuente y modificá
una causa a la vez. No afirmar que escuchaste la muestra si solo recibiste notas.
