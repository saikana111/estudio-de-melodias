import os
from pathlib import Path

import fluidsynth
import mido
import pygame

_SOUNDFONTS = Path(__file__).resolve().parents[1]/"assets/soundfonts"
RUTA_GM = os.environ.get("SOUNDFONT_PATH") or str(next(
    (p for p in (_SOUNDFONTS/"FluidR3_GM.sf2", _SOUNDFONTS/"GeneralUser-GS.sf2") if p.is_file()),
    _SOUNDFONTS/"FluidR3_GM.sf2"))
RUTA_PIANO = os.path.join("assets", "soundfonts", "piano.sf2")        # piano con capas de velocity

# Canal del teclado del ESP32. Es propio para que su instrumento no pise al de la melodía (canal 0).
CANAL_TECLADO = 1

# En MIDI, el volumen y los efectos se manejan con mensajes de control (Control Change, CC),
# cada uno con un número fijo: 7 es el volumen, 91 la reverb y 93 el chorus.
CONTROLES = {"VOL": 7, "REV": 91, "CHO": 93}
volumen_general = 127  # también lo usa gem.py para la voz de la IA

fs = fluidsynth.Synth()
fs.setting("synth.gain", 1.0)
fs.start(driver=os.environ.get("FLUIDSYNTH_DRIVER", "dsound"))
sfid = fs.sfload(RUTA_GM)

# El SoundFont General MIDI tiene pocas grabaciones por instrumento: una nota suave suena
# igual que una fuerte, solo que más baja. El piano dedicado tiene la misma nota grabada a
# varias intensidades (capas de velocity): tocar suave cambia también el timbre, como en un
# piano real. Se carga como segundo SoundFont y se asigna solo al canal del teclado.
sfid_piano = fs.sfload(RUTA_PIANO) if os.path.exists(RUTA_PIANO) else None
if sfid_piano == -1:
    sfid_piano = None


# ---------- Tocar en vivo (teclado del ESP32) ----------

def elegir_instrumento(instrumento):
    """Instrumento del teclado. Para el piano (0) se usa el SoundFont con capas de velocity."""
    if instrumento == 0 and sfid_piano is not None:
        fs.program_select(CANAL_TECLADO, sfid_piano, 0, 0)
    else:
        fs.program_select(CANAL_TECLADO, sfid, 0, instrumento)


def tocar_nota(nota, velocidad):
    # velocidad = velocity MIDI (1-127) medido por el ESP32 con los dos switches de la tecla
    fs.noteon(CANAL_TECLADO, nota, velocidad)


def soltar_nota(nota):
    fs.noteoff(CANAL_TECLADO, nota)


# ---------- Reproducir el proyecto ----------

def _sonar(msg):
    """Le pasa un mensaje MIDI a FluidSynth para que suene."""
    if msg.type == "program_change":
        if msg.channel == CANAL_TECLADO:
            elegir_instrumento(msg.program)   # respeta el piano con capas de velocity
        else:
            fs.program_select(msg.channel, sfid, 0, msg.program)
    elif msg.type == "note_on":
        if msg.velocity > 0:
            fs.noteon(msg.channel, msg.note, msg.velocity)
        else:
            fs.noteoff(msg.channel, msg.note)   # note_on con velocity 0 = soltar
    elif msg.type == "note_off":
        fs.noteoff(msg.channel, msg.note)
    elif msg.type == "control_change":
        fs.cc(msg.channel, msg.control, msg.value)


def _mensajes(proyecto):
    """Mensajes del proyecto en orden y con su espera, listos para sonar.
    La primera vez que se reproduce un archivo, mido mezcla todas las pistas en una sola
    y se guarda esa mezcla (un caché) para no volver a armarla. El problema es que el
    proyecto cambia después de eso: si no se borra la mezcla guardada, sigue sonando la
    vieja y no se escuchan las pistas nuevas, los cambios de instrumento ni los movimientos."""
    del proyecto.merged_track   # borra la mezcla guardada: play() la arma de nuevo
    return proyecto.play()


def reproducir_proyecto(proyecto):
    """Reproduce todas las pistas juntas, cada una con su instrumento. La función play()
    de mido mezcla las pistas en una sola línea de tiempo y espera entre mensaje y mensaje
    lo que corresponde."""
    for msg in _mensajes(proyecto):
        _sonar(msg)


def reproducir_pista(proyecto, canal):
    """Reproduce una sola pista del proyecto (la del canal indicado)."""
    for msg in _mensajes(proyecto):
        if not msg.is_meta and msg.channel == canal:
            _sonar(msg)


# ---------- Perilla (potenciómetro) ----------

def aplicar_perilla(control, valor, canal=None):
    """Aplica lo que manda la perilla: POT:VOL:90 cambia el volumen de todo el proyecto,
    POT:REV:90 o POT:CHO:90 la reverb o el chorus, y con canal (POT:REV:90:2) solo esa pista.
    La voz de la IA no pasa por FluidSynth (se reproduce con pygame), así que el volumen
    se aplica en los dos lugares, sin cambiar el volumen de Windows."""
    global volumen_general
    cc = CONTROLES.get(control)
    if cc is None:
        return
    if canal is not None:              # solo una pista (Efectos de la pista)
        fs.cc(canal, cc, valor)
        return
    for c in range(16):                # todo el proyecto: instrumentos, pistas...
        fs.cc(c, cc, valor)
    if control == "VOL":               # ...y la voz de la IA
        volumen_general = valor
        if pygame.mixer.get_init():    # si la IA está hablando, cambia en el momento
            pygame.mixer.music.set_volume(valor / 127)


def cerrar():
    fs.delete()
