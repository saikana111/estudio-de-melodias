# Integración con el instrumento original

El panel está en español y es opcional. El generador no necesita navegador,
servidor web, pantalla táctil ni controles nuevos en la placa.

## Hardware que aparece en el repositorio

`teclado_esp32/platformio.ini` configura una placa `esp32dev`, firmware Arduino y
comunicación serie a 115200 baudios. `src/esp32.py` usa `COM8`; `src/reproducir.py`
usa el controlador de audio `dsound`. La evidencia apunta a un ESP32 conectado a
una computadora Windows que ejecuta Python. No confirma una placa Android.

El ESP32 gestiona teclas, botones y pantalla; el proceso Python de la computadora
gestiona grabación, transcripción, conversación, generación y reproducción.
Antes de cambiar de plataforma hay que confirmar con la desarrolladora dónde
corre Python, qué sistema usa y cómo conecta el audio y el puerto serie.

## Sustitución del paso de generación

Se conserva el recorrido existente:

1. Grabar y transcribir la melodía a MIDI.
2. Obtener los ajustes musicales a partir de la conversación.
3. Generar una propuesta con `sugerencia.ensamble(datos, proyecto, canal)`.
4. Escucharla con la reproducción existente.
5. Aceptarla o rechazarla mediante la interacción Sí/No del ESP32.

`main.generar_sugerencia` selecciona el ensamble por defecto.
`project_arrangement.candidate` devuelve un proyecto de prueba sin modificar el
original, reserva los canales del teclado y agrupa las pistas generadas como
«Sugerencia IA». Al aceptar, `proponer_ensamble` guarda las pistas MIDI; al rechazar,
no reemplaza el proyecto. No se cambió el protocolo serie para este reemplazo.

Para usarlo fuera del flujo de conversación, con `src` en la ruta de importación:

```python
from musical import Brief
from project_arrangement import candidate

prueba, informe = candidate(
    proyecto,
    Brief(patron="sostenido", ritmo_armonico="libre"),
    melody_channel=canal_melodia,
)
# Reproducir prueba; confirmar antes de reemplazar/guardar proyecto.
```

La interfaz general para archivos es `generation.generate(bytes_midi, ajustes)`;
el adaptador del instrumento añade el manejo de las sugerencias anteriores y de
los canales reservados. Ambos llaman a `ensemble.arrange`, el mismo motor musical.
El desarrollo largo usa `song.develop` y se activa solo a pedido; no reemplaza el
comportamiento habitual del botón de acompañamiento.

## Qué permanece estable y qué falta verificar

Se mantienen los identificadores de configuración, las estructuras JSON y los
eventos MIDI. La traducción se limita a la presentación del panel; el JSON técnico
conserva sus nombres para seguir siendo reutilizable por código y archivos previos.

El motor independiente requiere Python y Mido; no necesita modelos neuronales ni
una GPU. Eso no significa que pueda ejecutarse directamente en el ESP32 ni que
Android ya esté validado. La aplicación completa sigue dependiendo de sus módulos
de transcripción, conversación y audio. En otro equipo hay que revisar puerto
serie, controlador de audio, SoundFonts, dependencias y rendimiento real.

Las pruebas automatizadas cubren generación y aceptación/rechazo simulados. Falta
probar el recorrido con la placa, micrófono y salida de audio de la desarrolladora.
El panel sirve para configurar y comparar en la computadora; no es una nueva
dependencia del firmware ni una obligación de agregar controles a su pantalla.
