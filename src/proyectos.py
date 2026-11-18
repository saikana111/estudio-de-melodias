import os
import re
import unicodedata
from datetime import datetime

import mido
from revision_musical import guardar_midi

import esp32
from asistente import gem   # Gemini o ChatGPT, según IA_CHAT en el .env
import grabar

# Cada proyecto es un archivo MIDI tipo 1: un solo .mid con varias pistas adentro.
# Se eligió este formato porque mido ya lo maneja y porque el archivo se puede abrir
# en cualquier programa de música, como Reaper o MuseScore, para seguir editándolo.
CARPETA = "proyectos"
TICKS_POR_TIEMPO = 480   # resolución de tiempo (ticks_per_beat) de todos los proyectos
BPM = 120                # pulso con el que se graba el teclado

# Cada pista usa su propio canal MIDI, y ese canal es lo que la identifica (ver Multipista
# con FluidSynth). La primera melodía va al canal 0, el primer teclado al 1 y la sugerencia
# de la IA al 2. Las grabaciones siguientes usan los canales que queden libres.
NOMBRES = {0: "Melodia", 1: "Teclado", 2: "Sugerencia IA"}
CANALES_EXTRA = [3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15]   # el 9 no: en General MIDI es la batería


def nombre_pista(pista):
    """Nombre de una pista: el que tiene guardado adentro (track_name) o, si no tiene,
    el que le corresponde por su canal."""
    canal = canal_de_pista(pista)
    return pista.name or NOMBRES.get(canal, f"Pista {canal}")


# =====================================================================
#  Crear, guardar, abrir, listar y renombrar
# =====================================================================

def nuevo():
    """Crea un proyecto vacío (un MIDI tipo 1 sin pistas)."""
    return mido.MidiFile(type=1, ticks_per_beat=TICKS_POR_TIEMPO)


def guardar(proyecto, nombre):
    """Guarda el proyecto en proyectos/nombre.mid. Se llama cada vez que algo cambia,
    así no se pierde el progreso."""
    os.makedirs(CARPETA, exist_ok=True)
    guardar_midi(proyecto, os.path.join(CARPETA, nombre + ".mid"))


def abrir(nombre):
    return mido.MidiFile(os.path.join(CARPETA, nombre + ".mid"))


def listar():
    """Nombres de los proyectos guardados (sin el .mid), los más nuevos primero."""
    if not os.path.isdir(CARPETA):
        return []
    archivos = [a for a in os.listdir(CARPETA) if a.endswith(".mid")]
    archivos.sort(key=lambda a: os.path.getmtime(os.path.join(CARPETA, a)), reverse=True)
    return [a[:-4] for a in archivos]


def renombrar(nombre_viejo, nombre_nuevo):
    os.rename(os.path.join(CARPETA, nombre_viejo + ".mid"),
              os.path.join(CARPETA, nombre_nuevo + ".mid"))


# =====================================================================
#  Pistas
# =====================================================================

def canal_de_pista(pista):
    """Canal MIDI de una pista (el de su primer mensaje con canal), o None si no tiene."""
    for msg in pista:
        if msg.type in ("note_on", "note_off", "program_change"):
            return msg.channel
    return None


def canales(proyecto):
    """Canales de las pistas del proyecto, en el orden en que están guardadas."""
    return [c for p in proyecto.tracks if (c := canal_de_pista(p)) is not None]


def nombres(proyecto):
    """Pares (canal, nombre) de las pistas del proyecto, en el orden en que están guardadas."""
    return [(c, nombre_pista(p)) for p in proyecto.tracks if (c := canal_de_pista(p)) is not None]


def nombre_de(proyecto, canal):
    """Nombre de la pista de ese canal."""
    return dict(nombres(proyecto)).get(canal, NOMBRES.get(canal, f"Pista {canal}"))


def canal_libre(proyecto, preferido):
    """Canal para una pista nueva: el preferido si nadie lo usa (0 para la melodía, 1 para
    el teclado) y, si ya está ocupado, el primero libre de los demás. Así cada grabación
    queda en su propia pista en vez de pisar a la anterior. Devuelve None si no queda ninguno."""
    usados = canales(proyecto)
    for canal in [preferido] + CANALES_EXTRA:
        if canal not in usados:
            return canal
    return None


def nombre_libre(proyecto, base):
    """Nombre para una pista nueva: "Melodia", y si ya existe "Melodia 2", "Melodia 3"..."""
    usados = [nombre for _, nombre in nombres(proyecto)]
    nombre, numero = base, 1
    while nombre in usados:
        numero += 1
        nombre = f"{base} {numero}"
    return nombre


def poner_pista(proyecto, pista):
    """Agrega la pista al proyecto. Si ya había una en ese canal, la reemplaza."""
    borrar_pista(proyecto, canal_de_pista(pista))
    proyecto.tracks.append(pista)


def borrar_pista(proyecto, canal):
    proyecto.tracks = [p for p in proyecto.tracks if canal_de_pista(p) != canal]


def cambiar_instrumento(proyecto, canal, instrumento):
    """Cambia el program_change de la pista de ese canal (el instrumento con que suena)."""
    for pista in proyecto.tracks:
        if canal_de_pista(pista) != canal:
            continue
        for i, msg in enumerate(pista):
            if msg.type == "program_change":
                pista[i] = msg.copy(program=instrumento)
                return
        pista.insert(0, mido.Message("program_change", channel=canal, program=instrumento, time=0))
        return


def mover_pista(proyecto, canal, tiempos):
    """Corre la pista de ese canal la cantidad de tiempos indicada (negativo = antes).
    Como en MIDI el tiempo de cada mensaje se cuenta desde el anterior (tiempo delta),
    alcanza con cambiar el primer mensaje de nota: el resto se corre con él."""
    ticks = int(tiempos * proyecto.ticks_per_beat)
    for pista in proyecto.tracks:
        for i, msg in enumerate(pista):
            if msg.type in ("note_on", "note_off") and msg.channel == canal:
                # solo el primer mensaje de nota: el resto se corre con él
                pista[i] = msg.copy(time=max(0, msg.time + ticks))
                return


# =====================================================================
#  Convertir a pista (la melodía de Basic Pitch y lo grabado en el teclado)
# =====================================================================

def _encabezado(nombre, canal, instrumento):
    """Toda pista empieza con su nombre (track_name) y su instrumento (program_change)."""
    pista = mido.MidiTrack()
    pista.append(mido.MetaMessage("track_name", name=nombre))
    pista.append(mido.Message("program_change", channel=canal, program=instrumento, time=0))
    return pista


def midi_a_pista(archivo, nombre, canal, instrumento, ticks_destino):
    """Convierte un archivo MIDI (la melodía que generó Basic Pitch) en una pista del
    proyecto, con ese nombre, en el canal indicado y con los ticks_per_beat del proyecto."""
    origen = mido.MidiFile(archivo)
    factor = ticks_destino / origen.ticks_per_beat   # cambio de resolución de tiempo
    pista = _encabezado(nombre, canal, instrumento)

    acumulado = 0.0   # tiempo absoluto en ticks del proyecto (los deltas se suman escalados)
    anterior = 0
    for msg in mido.merge_tracks(origen.tracks):
        acumulado += msg.time * factor
        if msg.type in ("note_on", "note_off"):
            ahora = round(acumulado)
            pista.append(msg.copy(channel=canal, time=ahora - anterior))
            anterior = ahora
    return pista


def teclado_a_pista(eventos, nombre, canal, instrumento, ticks_destino):
    """Convierte lo tocado en el teclado en una pista. Cada evento es
    (segundos desde que empezó la grabación, "on" / "off", nota, velocity)."""
    pista = _encabezado(nombre, canal, instrumento)
    anterior = 0
    for segundos, tipo, nota, velocidad in eventos:
        ahora = round(segundos * (BPM / 60) * ticks_destino)   # segundos -> tiempos -> ticks
        pista.append(mido.Message("note_on" if tipo == "on" else "note_off",
                                  channel=canal, note=nota,
                                  velocity=velocidad if tipo == "on" else 0,
                                  time=max(0, ahora - anterior)))
        anterior = ahora
    return pista


# =====================================================================
#  Nombres dichos en voz alta (del usuario y de los proyectos)
# =====================================================================

def sin_tildes(texto):
    """La pantalla muestra el nombre sin tildes, porque sus fuentes no las tienen."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def limpiar_nombre(texto):
    """Convierte un nombre en un nombre de archivo válido:
    "Canción del mar" se guarda como cancion_del_mar.mid."""
    texto = re.sub(r"[^a-zA-Z0-9 _-]", "", sin_tildes(texto)).strip().lower()   # deja _ y - escritos
    return texto.replace(" ", "_")[:30]


# Lo que dice la IA: (pregunta al mostrar el nombre, frase al confirmarlo)
FRASES = {
    "usuario":  ("¿Tu nombre es {}?", "[warmly] Te doy la bienvenida, {}."),
    "proyecto": ("¿El proyecto se llama {}?", "[cheerfully] Listo, el proyecto se llama {}."),
}


def pedir_nombre(tipo):
    """Micrófono y confirmación, hasta que se responde Sí. El nombre se graba con el
    botón de chat, Whisper lo transcribe y se confirma en la pantalla con el joystick."""
    rechazados = []
    while True:
        if grabar.grabar() != "chat":
            continue  # la grabación quedó vacía: se vuelve a grabar
        nombre = gem.transcribir("grabacion_chat.wav").strip(" .,!?¿¡")
        if rechazados and nombre:  # desde el segundo intento, la IA corrige la transcripción
            nombre = gem.corregir_nombre(nombre, rechazados)
        if not nombre:
            continue  # no se entendió nada: se vuelve a grabar

        pregunta, final = FRASES[tipo]
        esp32.enviar(f"NOMBRE:{sin_tildes(nombre)}")  # pantalla "¿Es correcto?"
        gem.leer(pregunta.format(nombre), expresar=False)  # frase fija
        if esp32.esperar_confirmacion():  # Sí = True, No = False
            gem.leer(final.format(nombre), expresar=False)
            return nombre
        rechazados.append(nombre)


def preguntar_nombre_proyecto():
    """"¿Deseas ponerle un nombre al proyecto?" Con Sí se dice en voz alta;
    con No, el nombre se arma con la fecha y la hora."""
    audio = f"audios/pregunta_nombre_voz{gem.voz_actual}.mp3"
    if os.path.exists(audio):
        gem.reproducir_audio(audio)  # audio ya grabado: suena al instante y sin internet
    else:
        gem.leer("¿Deseas ponerle un nombre al proyecto?", expresar=False)
    if esp32.esperar_si_no():  # pantalla con Sí y No
        return limpiar_nombre(pedir_nombre("proyecto"))
    return datetime.now().strftime("proyecto_%d-%m_%H%M")
