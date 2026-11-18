# Del género a una interpretación MIDI

La ruta de ensamble de la aplicación original usa el esquema ArregloBanda.
Gemini propone instrumentación y gesto. El host asigna canales, comprueba si
ya hay percusión y genera los eventos. El esquema básico sigue sirviendo al
motor tonal y a MIDI-GPT. Las dos fichas nuevas entran en las instrucciones
de Gemini mediante el cargador local existente.

## Fuentes y decisiones

- La formación documentada de los Kings of Rhythm reúne piano, guitarra eléctrica,
  bajo, batería y saxos. Sirve como ejemplo histórico de que una banda puede
  cubrir ritmo, armonía y melodía con varias formaciones. La plantilla reducida
  de rock aquí es una elección de arreglo. [TeachRock](https://curriculum.teachrock.org/posts/the-sun-king-sam-phillips)
- Usamos el backbeat en 2 y 4 y distinguimos el bombo en cuatro negras de house.
  El tutorial permite escuchar y editar el patrón. [Ableton](https://learningmusic.ableton.com/make-beats/backbeats.html)
- La afinación estándar y las posiciones del diapasón condicionan las alturas
  que se pueden tocar juntas. Una mejora posterior sería buscar digitaciones
  con una altura por cuerda y continuidad de posición. [Yamaha](https://hub.yamaha.com/guitars/g-how-to/summer-school-alternate-guitar-tunings/)
- Los instrumentos virtuales dedicados distinguen patrones, acentos y gestos
  grabados. En General MIDI implementamos una aproximación reproducible al
  rasgueo con ataques ordenados y acentos. Su temporización es una decisión del
  proyecto. [Manual de Session Guitarist](https://docs.native-instruments.com/pdf-guides/SESSION_GUITARIST_-_ELECTRIC_SUNBURST_Manual.pdf)

Para probar rock con un tarareo libre, usar guitarra 29, bajo 34, sin
respuestas, batería de acentos y rasgueo. Si se confirma una grilla de 4/4,
elegir batería rock. Comparar dos versiones del mismo arreglo variando solo
rasgueo para escuchar la diferencia entre digitación simultánea y ataque
escalonado. Evaluar aparte si el ritmo acompaña al tarareo y si el timbre del
SoundFont encaja con el subgénero.
