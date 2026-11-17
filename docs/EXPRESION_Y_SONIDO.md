# Expresión y reproducción instrumental — 0.3.0

El motor mantiene el ensamble como opción predeterminada y la composición más larga
como opción explícita. La melodía original conserva sus eventos MIDI. No se entrenó
un modelo neuronal nuevo: se agregaron controles musicales ejecutables a la búsqueda
armónica y a la realización de las partes.

## Controles disponibles

Se encuentran en «Expresión musical y balance» dentro del panel. Los mismos campos
forman parte de `Brief`, de los archivos JSON y del esquema que completa Gemini.

| Campo | Valores | Efecto real |
|---|---|---|
| `intensidad` | 24–110, predeterminado 68 | Velocidad MIDI base de la armonía |
| `curva_dinamica` | estable, crescendo, diminuendo, arco | Cambia velocidades de ataque y agrega una envolvente de expresión CC11, incluso durante notas sostenidas |
| `articulacion` | original, legato, normal, staccato | Conserva el patrón o utiliza el 100%, 80% o 45% de cada espacio temporal disponible |
| `actividad` | 1–4 | Subdivide segmentos sostenidos o aumenta la frecuencia del patrón repetido; no cambia el tempo de la melodía |
| `perfil_armonico` | automatico, reposado, creciente, resolver, arco | Añade preferencias de estabilidad/tensión al costo de búsqueda de acordes |
| `balance_bajo` | −36 a 12, predeterminado −13 | Diferencia de velocidad del bajo respecto de la armonía |
| `balance_respuesta` | −36 a 12, predeterminado −20 | Diferencia de velocidad de las respuestas respecto de la armonía |

La actividad modifica la parte armónica; el bajo conserva una nota por segmento y
las respuestas siguen limitadas a silencios de la melodía. Las articulaciones no
prolongan notas sobre el acorde siguiente. Legato aquí significa ocupar el espacio
disponible: no implementa técnicas específicas de arco, pedal o digitación.

La tensión funcional usa una escala heurística por grado, no una medida psicológica
validada. El ajuste a la melodía sigue participando en la búsqueda; un perfil no
garantiza una cadencia ni una emoción. Los acordes explícitos tienen prioridad. Los
perfiles evolutivos permiten rearmonizar motivos repetidos, y el informe lo indica.

Los valores predeterminados conservan el MIDI del ensamble entregado en 0.2.0, algo
verificado por comparación de bytes. Con curvas dinámicas se agregan CC11 solamente
a canales generados. La expresión se restablece al terminar y se conserva al unir
las secciones de una pieza larga.

## Desarrollo por secciones

«Variar la expresión entre secciones» aplica un plan explícito a la pieza larga:
variación algo más suave y creciente, contraste más activo, regreso y coda con
descanso. Es una propuesta compositiva editable, no una fórmula emocional.

La API acepta `Song(expresion_secciones={...})`, con ajustes por `variation`,
`contrast`, `return` y `coda`. El tema inicial utiliza el mismo ensamble que el modo
de acompañamiento. Los ajustes de sección se guardan en el informe y sobreviven a
la exportación/importación del panel. Ver `examples/expressive-song.json`.

## SoundFont y reproducción local

```powershell
python scripts/setup_audio.py
python src/dashboard.py
```

El instalador descarga [GeneralUser GS 2.0.3](https://github.com/mrbumpy409/GeneralUser-GS)
y, en Windows x64, [FluidSynth 2.6.2](https://github.com/FluidSynth/fluidsynth/releases/tag/v2.6.2).
Verifica hashes SHA-256, conserva la licencia del SoundFont y registra fuentes y
hashes en `assets/soundfonts/audio-assets.json`. Los binarios y el SF2 no se añaden
al repositorio; el instalador permite reproducir la configuración.

En Linux/macOS hay que instalar FluidSynth con el administrador de paquetes del
sistema. `FLUIDSYNTH_BIN` permite elegir otro ejecutable y `SOUNDFONT_PATH` otro
SoundFont. Si existe el antiguo `assets/soundfonts/FluidR3_GM.sf2`, se lo prefiere;
en su ausencia se usa GeneralUser GS. La aplicación de hardware comparte esta
selección de SoundFont; `FLUIDSYNTH_DRIVER` permite configurar su controlador de
audio, cuyo valor anterior era `dsound`.

En el panel, «Escuchar original» y «Escuchar resultado» preparan un WAV estéreo con
FluidSynth y lo reproducen en un elemento de audio del navegador. La salida mantiene
programas, tempo, controles y pitch bend del MIDI, dentro de lo que interpreta
FluidSynth/GM. No se normaliza cada versión por separado: se utiliza ganancia fija
0.35 para conservar diferencias de dinámica. No se promete articulación orquestal
avanzada ni idéntico sonido en otros sintetizadores.

Después de preparar un resultado aparece «Descargar audio WAV». El MIDI continúa
siendo la salida principal. El sintetizador sencillo permanece como alternativa
explícita; no se usa silenciosamente si el SoundFont falla. Ese modo sencillo no
reproduce CC11, instrumentos ni pitch bends.

El servidor guarda como máximo ocho WAV en una caché temporal de sesión. La escucha
con SoundFont admite resultados de hasta diez minutos; superar ese límite no impide
descargar el MIDI generado. La caché desaparece al cerrar el servidor: descargar los
audios que se quieran conservar. No hay llamadas de audio a servicios externos.

## Reproducir ejemplos y pruebas

```powershell
python scripts/build_expressive_examples.py --output-dir artifacts/mi-comparacion
python -m unittest discover -s tests -v
```

El script produce ensamble expresivo, ensamble más activo/staccato y pieza larga,
cada uno con MIDI, WAV instrumental e informe. Se niega a sobrescribir resultados.
Los informes identifican el SoundFont por hash y registran ajustes de renderizado.

44 pruebas pasan en el entorno local, incluidas tres pruebas con FluidSynth real:
distinción entre programas de piano/cuerdas/flauta, efecto de controles de volumen,
y preparación/caché/descarga HTTP. También se verifican dinámica, articulación,
actividad, búsqueda armónica, expresión por secciones y conservación de la fuente.
Las pruebas de audio se omiten si no están instalados el motor y el SoundFont.
También pasa `node tests/dashboard_controls.cjs`: comprueba la opción inicial,
controles expresivos y exportación/importación mediante un DOM simulado.
Se corrigió la caché de pistas mezcladas de Mido para que duración y vista previa
incluyan las pistas agregadas después de inspeccionar el original.

No hubo evaluación auditiva humana controlada ni prueba del hardware ESP32. No hay
un navegador automatizable disponible en este entorno; se verificaron los endpoints,
el audio generado y la sintaxis JavaScript, no la interacción visual completa.
