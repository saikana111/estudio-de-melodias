"""Escribe las notas de la sugerencia con MIDI-GPT, un modelo entrenado con música en MIDI.

Reparto del trabajo: Gemini entiende lo que pide el usuario y lo resume en pocos datos
(instrumento, cuántas notas a la vez, notas largas o cortas, registro, cuánto espacio) y
MIDI-GPT escribe las notas, mirando las pistas que ya tiene el proyecto.

Este archivo no importa nada del resto del programa (ni el ESP32 ni el sintetizador), así
se puede probar solo con un archivo MIDI."""
import os
import statistics
import tempfile

import mido
import numpy as np
from score_notes import score_track_notes

MODELO = "expressive_medium"   # el que mejor sonó en las pruebas (hay también yellow y prism)
COMPASES_MINIMOS = 4           # el modelo trabaja con ventanas de 4 compases o más
CANAL_BATERIA = 9              # en General MIDI el canal 9 es la batería: no se usa para las pistas

# Lo que elige Gemini -> niveles de los controles de MIDI-GPT.
# Duración de las notas: 0 fusa, 1 semicorchea, 2 corchea, 3 negra, 4 blanca, 5 redonda.
DURACIONES = {"cortas": (1, 3), "medias": (2, 4), "largas": (3, 5)}   # (la más corta, la más larga)
# Proporción de silencio de la pista, de 0 (suena todo el tiempo) a 9 (casi todo silencio).
ESPACIOS = {"poco": 1, "medio": 4, "mucho": 7}
# Nota alrededor de la cual queda la pista (48 = Do de la octava 3, 60 = Do central).
REGISTROS = {"grave": 40, "medio": 55, "agudo": 70}

_motor = None   # el modelo se carga la primera vez que se pide una sugerencia (tarda unos segundos)


def motor():
    """Devuelve el modelo ya cargado. La primera vez lo carga (y si nunca se usó en esta
    computadora, lo descarga: hace falta haber iniciado sesión en Hugging Face)."""
    global _motor
    if _motor is None:
        from midigpt.inference.engine import InferenceEngine   # importarlo tarda: recién acá
        _motor = InferenceEngine.from_pretrained(MODELO, device="cpu")
    return _motor


# =====================================================================
#  Mapa de tiempo: del canto libre a los compases que necesita el modelo
# =====================================================================

def mapa_de_tiempo(onsets, pulso, ticks_por_tiempo):
    """MIDI-GPT piensa en compases y tiempos exactos, pero la melodía se cantó sin metrónomo.
    Esta función arma una tabla de equivalencias entre el tiempo real (cuándo sonó cada nota)
    y el tiempo "de partitura" (en qué tiempo del compás cae).

    Cada inicio de nota de la melodía es un punto de la tabla. La distancia entre dos notas
    seguidas se redondea a medios pulsos (corcheas): si pasaron 1,1 pulsos, en la partitura
    es 1 tiempo; si pasaron 0,45, es medio tiempo. Así el modelo ve una melodía prolija, y
    lo que genera se puede devolver después al tiempo real y cae junto con la voz.

    Devuelve (reales, partitura): dos listas del mismo largo, en ticks."""
    medio_pulso = pulso / 2
    corchea = ticks_por_tiempo // 2
    onsets = onsets or [0]

    # Antes de la primera nota se dejan los compases enteros de silencio que entren.
    posicion = int(onsets[0] // (4 * pulso)) * 4 * ticks_por_tiempo
    reales, partitura = [onsets[0]], [posicion]
    for onset in onsets[1:]:
        pasos = round((onset - reales[-1]) / medio_pulso)
        if pasos == 0:
            continue   # dos notas casi juntas: no hace falta otro punto
        posicion += pasos * corchea
        reales.append(onset)
        partitura.append(posicion)

    # Antes de la primera nota y después de la última no hay voz que seguir:
    # el tiempo avanza con el pulso medido.
    if partitura[0] > 0:   # hay compases de silencio antes de la primera nota
        reales.insert(0, reales[0] - partitura[0] * pulso / ticks_por_tiempo)
        partitura.insert(0, 0)
    reales.append(reales[-1] + 1000 * pulso)
    partitura.append(partitura[-1] + 1000 * ticks_por_tiempo)
    return reales, partitura


# =====================================================================
#  Pistas del proyecto <-> notas
# =====================================================================

def notas_de_pista(pista):
    """Notas de una pista como (inicio, fin, nota, velocity), con tiempos absolutos en ticks.
    En MIDI cada mensaje guarda el tiempo desde el mensaje anterior, así que se van sumando."""
    notas, abiertas, ahora = [], {}, 0
    for msg in pista:
        ahora += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            abiertas[msg.note] = (ahora, msg.velocity)
        elif msg.type in ("note_off", "note_on") and msg.note in abiertas:
            inicio, velocity = abiertas.pop(msg.note)
            notas.append((inicio, ahora, msg.note, velocity))
    return sorted(notas)


def _instrumento_de(pista):
    return next((m.program for m in pista if m.type == "program_change"), 0)


def _pista_en_partitura(pista, canal, reales, partitura):
    """Copia de una pista del proyecto con sus notas pasadas al tiempo de partitura."""
    eventos = []
    for inicio, fin, nota, velocity in notas_de_pista(pista):
        if inicio < reales[0]:
            continue   # sonó antes de donde empieza la partitura
        a = round(float(np.interp(inicio, reales, partitura)))
        b = max(a + 1, round(float(np.interp(fin, reales, partitura))))
        eventos.append((a, 1, mido.Message("note_on", channel=canal, note=nota, velocity=velocity)))
        eventos.append((b, 0, mido.Message("note_off", channel=canal, note=nota, velocity=0)))
    eventos.sort(key=lambda e: (e[0], e[1]))   # en el mismo instante, primero los note_off

    copia = mido.MidiTrack()
    copia.append(mido.Message("program_change", channel=canal, program=_instrumento_de(pista), time=0))
    anterior = 0
    for tick, _, msg in eventos:
        copia.append(msg.copy(time=tick - anterior))
        anterior = tick
    return copia


# =====================================================================
#  Pedido a MIDI-GPT
# =====================================================================

def _controles(datos):
    """Pasa lo que eligió Gemini a los controles del modelo. Devuelve (de_pista, de_compas):
    unos valen para toda la pista y otros se repiten en cada compás. Los nombres cambian
    según el modelo ("max_polyphony" o "bar_max_polyphony"), por eso se le preguntan a él."""
    voces = datos.get("voces", 2)
    voces = min(4, max(1, voces)) if isinstance(voces, int) else 2
    corta, larga = DURACIONES.get(datos.get("notas"), DURACIONES["medias"])
    pedidos = {
        "min_polyphony": max(0, voces - 2),   # nivel 0 = una voz, 1 = dos voces...
        "max_polyphony": voces - 1,
        "min_note_duration": corta,
        "max_note_duration": larga,
        "silence_proportion": ESPACIOS.get(datos.get("espacio"), ESPACIOS["medio"]),
    }
    niveles = motor()._analyzer.attribute_levels()   # control -> "track" (pista) o "bar" (compás)
    de_pista, de_compas = {}, {}
    for nombre, valor in pedidos.items():
        for candidato in (nombre, "bar_" + nombre):
            if candidato in niveles:
                (de_compas if niveles[candidato] == "bar" else de_pista)[candidato] = valor
                break
    return de_pista, de_compas


def _al_registro(notas, registro):
    """Sube o baja la pista de a octavas enteras hasta dejarla en el registro pedido.
    El modelo no tiene un control para esto y tiende a escribir en la misma zona que la
    melodía, donde se pisan. Mover de a octavas no cambia los acordes."""
    centro = REGISTROS.get(registro, REGISTROS["medio"])
    mediana = statistics.median(nota for _, _, nota, _ in notas)
    octavas = round((centro - mediana) / 12)
    while max(nota for _, _, nota, _ in notas) + 12 * octavas > 108:   # más agudo que un piano
        octavas -= 1
    while min(nota for _, _, nota, _ in notas) + 12 * octavas < 24:    # más grave que un bajo
        octavas += 1
    return [(inicio, fin, nota + 12 * octavas, velocity) for inicio, fin, nota, velocity in notas]


def generar(pistas, ticks_por_tiempo, onsets, pulso, datos):
    """Genera una pista nueva que acompaña a las pistas dadas.

    pistas  : pistas del proyecto que el modelo tiene que escuchar (las de mido)
    onsets  : inicios de las notas de la melodía, en ticks (marcan el pulso del usuario)
    pulso   : cuánto dura un pulso de esa melodía, en ticks
    datos   : lo que eligió Gemini: instrumento, voces, notas, espacio y registro

    Devuelve las notas nuevas como (inicio, fin, nota, velocity), en ticks del proyecto."""
    from midigpt import Bar, Score, Track   # se importa acá: cargarlo demora el arranque
    from midigpt.inference.config import GenerationRequest, InferenceConfig, TrackPrompt

    instrumento = datos.get("instrumento", 0)
    if not isinstance(instrumento, int) or not 0 <= instrumento <= 127:
        instrumento = 0   # la IA mandó cualquier cosa: piano

    reales, partitura = mapa_de_tiempo(onsets, pulso, ticks_por_tiempo)

    # 1) Las pistas del proyecto, en tiempo de partitura, van a un MIDI temporal:
    #    es la forma en que la librería sabe leer música.
    contexto = mido.MidiFile(type=1, ticks_per_beat=ticks_por_tiempo)
    canales = [c for c in range(16) if c != CANAL_BATERIA]
    for canal, pista in zip(canales, pistas):
        contexto.tracks.append(_pista_en_partitura(pista, canal, reales, partitura))

    with tempfile.TemporaryDirectory() as carpeta:
        entrada = os.path.join(carpeta, "contexto.mid")
        contexto.save(entrada)
        musica = Score.from_midi(entrada)
        cantidad = len(musica.tracks)

        # 2) Se agrega una pista vacía con el instrumento elegido: es la que hay que llenar.
        compases = max(COMPASES_MINIMOS, max(len(p.bars) for p in musica.tracks))
        for pista in musica.tracks:
            pista.bars.extend(Bar() for _ in range(compases - len(pista.bars)))
        musica.tracks.append(Track(bars=[Bar() for _ in range(compases)], instrument=instrumento))

        # 3) El pedido: las pistas que ya estaban quedan como contexto (bars=[] = no tocarlas)
        #    y la nueva se genera entera, compás por compás (autoregressive).
        de_pista, de_compas = _controles(datos)
        pedido = GenerationRequest(
            tracks=[TrackPrompt(id=i, bars=[]) for i in range(cantidad)] + [TrackPrompt(
                id=cantidad, bars=list(range(compases)), autoregressive=True, attributes=de_pista,
                bar_attributes={c: dict(de_compas) for c in range(compases)} if de_compas else {})],
            config=InferenceConfig(model_dim="auto", mask_mode="attention"))
        resultado = motor().session(musica, pedido).run()

    # 4) De la música generada interesa solo la pista nueva. Sus tiempos vuelven de la
    #    partitura al tiempo real con la misma tabla, leída al revés.
    notas = []
    # Read the logical track directly; avoid a redundant MIDI round trip and
    # dependence on writer-specific track ordering. v0.4.2's writer preserves it.
    for inicio, fin, nota, velocity in score_track_notes(resultado, cantidad, ticks_por_tiempo):
        a = round(float(np.interp(inicio, partitura, reales)))
        b = round(float(np.interp(fin, partitura, reales)))
        notas.append((a, max(a + 1, b), nota, velocity))

    # El modelo completa el último compás aunque la grabación termine antes: lo que empieza
    # después del final de lo grabado se descarta, y la última nota suena un pulso más como mucho.
    final = max(fin for pista in pistas for _, fin, _, _ in notas_de_pista(pista))
    notas = [(a, min(b, final + pulso), nota, velocity) for a, b, nota, velocity in notas if a < final]
    if not notas:
        raise ValueError("MIDI-GPT no generó ninguna nota")
    return _al_registro(notas, datos.get("registro"))
