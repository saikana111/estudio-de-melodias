import random
import json
import os

import mido
from music21 import harmony

import acompanante
import esp32
import gem
import proyectos
import reproducir
from musical import Brief, accompany
from project_arrangement import candidate
from ensemble import Ensemble


def ensamble(datos, proyecto, canal_melodia=0):
    return candidate(proyecto, Brief(**datos), canal_melodia,
                     Ensemble(harmony_program=datos.get("instrumento", 48)))


def proponer_ensamble(prueba, informe, proyecto, nombre):
    """Preview/accept the entire generated group, retaining all source tracks."""
    esp32.enviar("PANTALLA:SUGERENCIA")
    reproducir.reproducir_proyecto(prueba)
    if esp32.esperar_si_no():
        proyecto.tracks = prueba.tracks
        proyecto.type = 1
        proyectos.guardar(proyecto, nombre)
        with open(os.path.join(proyectos.CARPETA, nombre + ".arrangement.json"), "w", encoding="utf-8") as f:
            json.dump(informe, f, indent=2, ensure_ascii=False)
        return True
    gem.hablar("El usuario escuchó el ensamble y lo rechazó. Preguntale qué quiere cambiar.")
    return False

# La sugerencia de la IA siempre usa el canal 2 (ver Multipista con FluidSynth)
CANAL_IA = 2


def pista_tonal(datos, proyecto, canal_melodia=0):
    """Offline harmonic planner, compatible with the existing arrangement brief."""
    pista, informe = accompany(proyecto, Brief(**datos), canal_melodia, CANAL_IA)
    print("Plan tonal:", informe)
    return pista

# Cuánto dura cada golpe respecto de su lugar en la grilla. 0.85 deja un respiro
# antes del golpe siguiente; con 1.0 las notas quedan pegadas (acordes "colgados").
LARGO_NOTA = 0.85

# Límites del pulso, en tiempos del proyecto (1 tiempo = 0,5 s, porque Basic Pitch
# guarda todo a 120 BPM). Si la melodía tiene muchas notas rápidas, la mediana da un
# pulso demasiado corto y el acompañamiento golpearía muy seguido: se duplica.
# Si da uno demasiado largo (pocas notas largas), se divide a la mitad.
PULSO_MINIMO = 0.6   # 0,3 s: más rápido que esto suena atropellado
PULSO_MAXIMO = 2.4   # 1,2 s: más lento que esto vuelve a sonar "colgado"


# =====================================================================
#  Grilla de pulso (sale de la melodía cantada)
# =====================================================================

def onsets_melodia(proyecto, canal=0):
    """Tiempos absolutos (en ticks) donde empieza cada nota de la melodía.
    En una pista MIDI cada mensaje lleva su tiempo relativo al mensaje anterior,
    así que se van sumando para reconstruir el tiempo absoluto de cada note_on."""
    onsets = set()
    for pista in proyecto.tracks:
        t = 0
        for msg in pista:
            t += msg.time
            if msg.type == "note_on" and msg.velocity > 0 and msg.channel == canal:
                onsets.add(t)
    return sorted(onsets)


def grilla_de_pulso(onsets, ticks_por_tiempo):
    """Convierte los inicios de nota en una grilla de pulso. Devuelve (grilla, pulso).

    El pulso se estima con la mediana de los intervalos entre onsets: la mediana
    ignora los valores raros, así que una nota muy larga o dos muy pegadas no la
    corren. Los onsets reales quedan como puntos de la grilla (por eso el
    acompañamiento sigue al cantante aunque se apure o se frene) y los silencios
    largos se rellenan repitiendo el pulso, para que también haya acordes donde
    no hay voz. Recibe tiempos, no le importa de dónde salieron: el día que se
    quiera marcar el pulso con una tecla, esos toques pueden reemplazar a los onsets."""
    if len(onsets) < 2:
        # casi no hay notas cantadas: grilla regular de un pulso por tiempo
        inicio = onsets[0] if onsets else 0
        return [inicio + k * ticks_por_tiempo for k in range(16)], ticks_por_tiempo

    intervalos = sorted(b - a for a, b in zip(onsets, onsets[1:]))
    pulso = intervalos[len(intervalos) // 2]   # mediana
    while pulso < PULSO_MINIMO * ticks_por_tiempo:
        pulso *= 2
    while pulso > PULSO_MAXIMO * ticks_por_tiempo:
        pulso //= 2

    grilla = [onsets[0]]
    for onset in onsets[1:]:
        while onset - grilla[-1] > 1.6 * pulso:   # silencio largo: rellenar
            grilla.append(grilla[-1] + pulso)
        if onset - grilla[-1] > 0.5 * pulso:      # nota nueva: anclar la grilla ahí
            grilla.append(onset)
    return grilla, pulso


# =====================================================================
#  Sugerencia -> MIDI
# =====================================================================

def _instrumento(datos):
    """Instrumento que eligió Gemini (0-127 de General MIDI). Si mandó cualquier cosa: piano."""
    instrumento = datos.get("instrumento", 0)
    return instrumento if isinstance(instrumento, int) and 0 <= instrumento <= 127 else 0


def _armar_pista(eventos, canal, instrumento):
    """Arma la pista "Sugerencia IA" a partir de pares (tick absoluto, mensaje)."""
    # De tiempos absolutos a tiempos delta (lo que mido espera). Los note_off van
    # antes que los note_on del mismo instante para no cortar una nota recién tocada.
    eventos.sort(key=lambda e: (e[0], 0 if e[1].type == "note_off" else 1))
    pista = mido.MidiTrack()
    pista.append(mido.MetaMessage("track_name", name="Sugerencia IA"))
    pista.append(mido.Message("program_change", channel=canal, program=instrumento, time=0))
    anterior = 0
    for t, msg in eventos:
        pista.append(msg.copy(time=t - anterior))
        anterior = t
    return pista


def sugerencia_a_midi(datos, canal, grilla, pulso):
    """Convierte la sugerencia de Gemini (un diccionario leído de su JSON) en una
    pista MIDI tocada con patrón. Gemini decide QUÉ tocar (los acordes en cifrado
    americano y cuántos pulsos dura cada uno) y acá Python decide CUÁNDO y CÓMO:
    el acorde se vuelve a golpear en cada pulso de la grilla, con el bajo en el
    primer golpe, acento, velocities variadas y notas que terminan un poco antes
    del golpe siguiente."""
    eventos = []  # pares (tick absoluto, mensaje); al final se pasan a tiempos delta
    i = 0         # posición en la grilla

    for acorde in datos.get("acordes", []):
        try:
            # music21 traduce el cifrado a notas MIDI, pero en una zona grave
            # ("Am" = La2, Do3, Mi3) donde las notas juntas se empastan.
            graves = [p.midi for p in harmony.ChordSymbol(acorde["cifrado"]).pitches]
            pulsos = int(acorde["tiempos"])
        except Exception:
            continue  # acorde mal escrito: se saltea
        if not graves or pulsos <= 0:
            continue
        notas = [n + 12 for n in graves]   # el acorde, una octava arriba (cerca del Do central)
        bajo = min(graves)                 # la nota más grave, abajo: el "bajo" del patrón

        for k in range(pulsos):
            # si la grilla se queda corta, se extiende repitiendo el pulso
            if i < len(grilla):
                inicio = grilla[i]
            else:
                inicio = grilla[-1] + (i - len(grilla) + 1) * pulso
            fin = grilla[i + 1] if i + 1 < len(grilla) else inicio + pulso
            duracion = max(1, int((fin - inicio) * LARGO_NOTA))

            if k == 0:                  # primer pulso del acorde: acento + bajo
                golpe = [bajo] + notas
                vel_base = 92
            else:                       # pulsos siguientes: el acorde solo, más suave
                golpe = notas
                vel_base = 68

            for n in golpe:
                # pequeña variación aleatoria: dos golpes nunca salen idénticos
                vel = max(1, min(127, vel_base + random.randint(-6, 6)))
                eventos.append((inicio, mido.Message("note_on", channel=canal, note=n, velocity=vel)))
                eventos.append((inicio + duracion, mido.Message("note_off", channel=canal, note=n, velocity=0)))
            i += 1

    return _armar_pista(eventos, canal, _instrumento(datos))


def pista_con_midigpt(datos, proyecto, canal_melodia=0):
    """Arma la pista de la sugerencia con MIDI-GPT: Gemini eligió el instrumento y el carácter
    (datos) y el modelo escribe las notas escuchando las pistas que ya tiene el proyecto.
    canal_melodia = canal de la pista a la que acompaña (de ahí sale el pulso)."""
    onsets = onsets_melodia(proyecto, canal_melodia)
    _, pulso = grilla_de_pulso(onsets, proyecto.ticks_per_beat)
    # El modelo escucha todo menos la sugerencia anterior, que es la que se va a reemplazar.
    contexto = [p for p in proyecto.tracks if proyectos.canal_de_pista(p) not in (None, CANAL_IA)
                and not p.name.startswith("Sugerencia IA")]
    with gem.cronometro("MIDI-GPT (escribir las notas)"):
        notas = acompanante.generar(contexto, proyecto.ticks_per_beat, onsets, pulso, datos)

    eventos = []
    for inicio, fin, nota, velocity in notas:
        eventos.append((inicio, mido.Message("note_on", channel=CANAL_IA, note=nota, velocity=velocity)))
        eventos.append((fin, mido.Message("note_off", channel=CANAL_IA, note=nota, velocity=0)))
    return _armar_pista(eventos, CANAL_IA, _instrumento(datos))


def pista_con_acordes(datos, proyecto, canal_melodia=0):
    """Método anterior, que queda como respaldo: Gemini dice los acordes y Python los toca
    con un patrón sobre la grilla de pulso."""
    # La grilla sale de la melodía ya grabada: el acompañamiento cae donde
    # el usuario cantó, no donde diga un reloj.
    onsets = onsets_melodia(proyecto, canal_melodia)
    grilla, pulso = grilla_de_pulso(onsets, proyecto.ticks_per_beat)
    pista = sugerencia_a_midi(datos, CANAL_IA, grilla, pulso)
    if not any(m.type == "note_on" for m in pista):
        # Todos los acordes estaban mal escritos: no hay nada para escuchar.
        # main.generar_sugerencia() atrapa el error, vuelve a la pantalla principal y avisa.
        raise ValueError(f"la IA no devolvió ningún acorde que se pueda tocar: {datos}")
    return pista


def proponer_sugerencia(pista, proyecto, nombre):
    """Hace escuchar la pista de la sugerencia junto con el resto del proyecto y pregunta
    en la pantalla "¿Aceptar sugerencia?". Devuelve True si se aceptó."""
    # Copia del proyecto con la sugerencia, solo para escucharla (sin tocar el proyecto guardado).
    # Si ya había una sugerencia aceptada antes, en la prueba se escucha la nueva en su lugar.
    prueba = mido.MidiFile(type=1, ticks_per_beat=proyecto.ticks_per_beat)
    prueba.tracks = [p for p in proyecto.tracks
                     if proyectos.canal_de_pista(p) != CANAL_IA
                     and not p.name.startswith("Sugerencia IA")] + [pista]

    esp32.enviar("PANTALLA:SUGERENCIA")  # "¿Aceptar sugerencia?" Sí / No
    reproducir.reproducir_proyecto(prueba)

    if esp32.esperar_si_no():  # Sí: se agrega (reemplazando la anterior) y se guarda
        proyecto.tracks = prueba.tracks
        proyectos.guardar(proyecto, nombre)
        return True

    # No: se descarta. Como el chat guarda el historial, la IA sabe qué propuso
    # y pregunta qué cambiaría el usuario. Responder no es obligatorio.
    gem.hablar("El usuario escuchó la sugerencia y la rechazó. "
               "Preguntale en una sola frase qué le gustaría cambiar.")
    return False
