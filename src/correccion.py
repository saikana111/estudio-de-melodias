import mido
import json
from musical import summarize
from music21 import converter


def detectar_tonalidad(archivo):
    """Detecta la tonalidad y la escala de un archivo MIDI con music21, que aplica
    algoritmos de teoría musical real. Devuelve la tonalidad (por ejemplo, C major).
    Detecta escalas mayores y menores; si se quieren escalas más exóticas, music21
    las tiene, pero hay que compararlas una por una con las notas."""
    
    return converter.parse(archivo).analyze("key")


def texto_tonalidad(tonalidad):
    """Escribe la tonalidad para mandársela a Gemini. music21 escribe los bemoles con "-"
    ("E- major" es Mi bemol mayor) y Gemini lo leía como Mi mayor: se cambia por "b" ("Eb major")."""
    return f"{tonalidad.tonic.name.replace('-', 'b')} {tonalidad.mode}"


def _afinar(nota, escala):
    """Si la nota no pertenece a la escala, la corre al semitono más cercano que sí."""
    if nota % 12 in escala:
        return nota
    for paso in (1, -1):   # una nota desafinada queda a un semitono de la escala
        if 0 <= nota + paso <= 127 and (nota + paso) % 12 in escala:
            return nota + paso
    return nota


def corregir(archivo, tonalidad):
    """Corrige los errores y la desafinación que pueda haber al cantar: cada nota
    desviada se corre para que quede dentro de las notas de su escala y suene afinada.
    Se hace con mido, que permite modificar archivos MIDI, y se guarda en el mismo archivo."""
    escala = {p.pitchClass for p in tonalidad.pitches}
    archivo_midi = mido.MidiFile(archivo)
    for pista in archivo_midi.tracks:
        for i, mensaje in enumerate(pista):
            # La misma corrección para note_on y note_off: cada nota se apaga igual que se prendió.
            if mensaje.type in ("note_on", "note_off"):
                pista[i] = mensaje.copy(note=_afinar(mensaje.note, escala))
    archivo_midi.save(archivo)


def midi_txt(archivo, canal=None):
    """Gemini no es capaz de leer archivos MIDI. Esta función recorre el archivo nota por
    nota y lo transforma en texto, con cada nota, su velocidad y su tiempo. Ese texto es
    el que se le envía a la IA para que pueda comprenderlo y dar sugerencias musicales."""
    return json.dumps(summarize(mido.MidiFile(archivo), canal), ensure_ascii=False)


    
