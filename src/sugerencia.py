import random
from copy import deepcopy
from dataclasses import fields, replace

import mido
from music21 import harmony

import acompanante
import esp32
from asistente import gem   # Gemini o ChatGPT, según IA_CHAT en el .env
import proyectos
import reproducir
from ensemble import Ensemble, arrange
from musical import Brief
from song import develop

# La sugerencia de una sola pista (MIDI-GPT o los acordes de Gemini) usa el canal 2.
# El ensamble y la composición larga usan varios canales libres (ver ensamble()).
CANAL_IA = 2

# Todas las pistas que arma la IA empiezan con este nombre. Así se reconocen para
# reemplazarlas por la sugerencia siguiente sin tocar lo que grabó el usuario.
PREFIJO_IA = "Sugerencia IA"
NOMBRES_ROLES = {"harmony": "Armonia", "bass": "Bajo", "response": "Respuestas", "drums": "Bateria"}

# Instrumentos del ensamble si Gemini no elige otros (números de General MIDI)
BAJO_PREDETERMINADO = 43         # contrabajo
RESPUESTAS_PREDETERMINADO = 73   # flauta

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
    contexto = [p for p in proyecto.tracks
                if proyectos.canal_de_pista(p) not in (None, CANAL_IA) and not es_sugerencia(p)]
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


# =====================================================================
#  Ensamble y composición larga (reglas musicales, sin IA entrenada)
# =====================================================================
# Vienen del proyecto "estudio-de-melodias" (musical.py, ensemble.py y song.py). A partir de
# la melodía eligen acordes de la escala con una búsqueda que mide qué tan bien encaja cada
# acorde con las notas cantadas, y con ese plan escriben la armonía, un bajo que toca la
# fundamental de cada acorde y respuestas cortas en los silencios de la melodía.
# Gemini elige el instrumento y el carácter (los datos), igual que para MIDI-GPT.

def es_sugerencia(pista):
    """True si la pista la armó la IA (y se reemplaza con la próxima sugerencia)."""
    return pista.name.startswith(PREFIJO_IA)


def _sin_sugerencias(proyecto):
    """Copia del proyecto sin las sugerencias anteriores: es lo que escuchan los generadores."""
    copia = deepcopy(proyecto)
    copia.tracks = [p for p in copia.tracks if not es_sugerencia(p)]
    return copia


def _brief_y_ensamble(datos):
    """Pasa lo que eligió Gemini a los dos objetos que usan los generadores:
    Brief (carácter de la armonía) y Ensemble (instrumentos de cada parte)."""
    datos = dict(datos)
    bajo = datos.pop("instrumento_bajo", BAJO_PREDETERMINADO)
    respuestas = datos.pop("instrumento_respuestas", RESPUESTAS_PREDETERMINADO)
    con_respuestas = datos.pop("respuestas", True)
    # El canto no sigue un metrónomo: la armonía cambia donde cambian las notas cantadas,
    # no en compases fijos.
    datos.setdefault("ritmo_armonico", "libre")
    validos = {campo.name for campo in fields(Brief)}
    brief = Brief(**{clave: valor for clave, valor in datos.items() if clave in validos})
    grupo = Ensemble(bass_program=bajo, harmony_program=brief.instrumento,
                     response_program=respuestas, responses=con_respuestas)
    return brief, grupo


def _canales_usados(midi):
    return {m.channel for p in midi.tracks for m in p if hasattr(m, "channel")}


def _sin_lugar_para_el_bajo(error):
    """El generador no encontró acordes que dejen lugar al bajo debajo (pasa con la armonía
    en registro grave o con las voces muy separadas)."""
    return isinstance(error, ValueError) and ("voicing" in str(error) or "room" in str(error))


def _probar_registros(armar, datos):
    """Llama a armar(brief, grupo) con lo que eligió Gemini. Si el bajo no entra debajo de la
    armonía, vuelve a probar con la armonía más arriba y las voces juntas."""
    intentos = [datos] + [{**datos, "registro": registro, "disposicion": "cerrada"}
                          for registro in ("medio", "agudo") if registro != datos.get("registro")]
    for numero, intento in enumerate(intentos):
        try:
            resultado = armar(*_brief_y_ensamble(intento))
            if numero:
                print(f"La armonía se pasó al registro {intento['registro']} para dejarle lugar al bajo.")
            return resultado
        except ValueError as e:
            if not _sin_lugar_para_el_bajo(e) or numero == len(intentos) - 1:
                raise


def ensamble(datos, proyecto, canal_melodia=0):
    """Agrega armonía, bajo y respuestas alrededor de la melodía, cada uno en su pista, y si
    Gemini lo eligió, batería y rasgueo de guitarra (band.py, ver _interpretar()).
    Devuelve (proyecto de prueba con las pistas nuevas, informe). No toca el proyecto."""
    fuente = _sin_sugerencias(proyecto)
    if datos.get("progresion_rock", datos.get("bateria") == "rock"):
        import correccion
        inicios = onsets_melodia(fuente, canal_melodia)
        if inicios:
            datos = dict(datos, ritmo_armonico="rock", **correccion.grilla_rock(fuente, inicios))
    # El canal 1 queda libre aunque no haya teclado grabado: es el del teclado en vivo.
    reservados = tuple(sorted(_canales_usados(fuente) | {0, 1, 9}))
    prueba, informe, brief = _probar_registros(
        lambda brief, grupo: arrange(fuente, brief, canal_melodia,
                                     replace(grupo, reserved_channels=reservados)) + (brief,),
        datos)
    _interpretar(datos, fuente, prueba, informe, brief, canal_melodia)
    for pista, parte in zip(prueba.tracks[len(fuente.tracks):], informe["parts"]):
        pista.name = f"{PREFIJO_IA} - {NOMBRES_ROLES[parte['role']]}"
    return prueba, informe


def _interpretar(datos, fuente, prueba, informe, brief, canal_melodia):
    """Batería y rasgueo (band.py, del proyecto estudio-de-melodias):
    - rasgueo: los acordes de guitarra (programas 24 a 31) no suenan todos juntos como en un
      teclado: cada nota entra un poquito después, como un golpe de púa.
    - bateria "acentos": bombo y caja en cada cambio de acorde; sigue al canto aunque sea libre.
    - bateria "rock" o "house": un patrón con pulso fijo. El pulso sale de la melodía (con la
      misma búsqueda que usa la cuantización) y arranca en su primera nota; sin eso, el patrón
      iba a 120 BPM aunque se hubiera cantado a otro tempo."""
    bateria = datos.get("bateria", "ninguna")
    rasgueo = bool(datos.get("rasgueo", False))
    if bateria == "ninguna" and not rasgueo:
        return
    from band import perform
    if bateria in ("rock", "house") and brief.beat_ticks is None:
        import correccion
        inicios = onsets_melodia(fuente, canal_melodia)
        pulso = round(correccion.estimar_pulso(inicios, fuente.ticks_per_beat))
        brief = replace(brief, beat_ticks=pulso, downbeat=inicios[0] if inicios else 0)
        print(f"Batería {bateria}: pulso de {60 / (pulso / fuente.ticks_per_beat * 0.5):.0f} BPM")
    perform(fuente, prueba, informe, brief, canal_melodia, bateria, rasgueo)


def cancion(datos, proyecto, canal_melodia=0):
    """Composición larga: la melodía queda como tema y sigue con variación, contraste,
    regreso y un final, todo con el ensamble acompañando. Las notas nuevas de la melodía
    van a una pista propia. Devuelve (proyecto de prueba, informe). No toca el proyecto."""
    fuente = _sin_sugerencias(proyecto)
    melodia = next((p for p in fuente.tracks if proyectos.canal_de_pista(p) == canal_melodia), None)
    if melodia is None:
        raise ValueError(f"no hay ninguna pista en el canal {canal_melodia}")

    # El desarrollo trabaja sobre la melodía sola: las otras pistas grabadas siguen sonando
    # en el tema, pero no se estiran a las secciones nuevas.
    semilla = mido.MidiFile(type=1, ticks_per_beat=fuente.ticks_per_beat)
    semilla.tracks.append(deepcopy(melodia))
    usados = _canales_usados(fuente) | {0, 1, 9}
    resultado, informe = _probar_registros(
        lambda brief, grupo: develop(semilla, brief, canal_melodia,
                                     replace(grupo, reserved_channels=tuple(sorted(usados)))),
        datos)

    # Las pistas nuevas del resultado (después de la melodía copiada): el desarrollo de la
    # melodía, las partes del ensamble y los marcadores de cada sección.
    nuevas = resultado.tracks[1:]
    canales_partes = {parte["channel"] for parte in informe["parts"]}
    libre = next((c for c in range(16) if c not in usados | canales_partes), None)
    if libre is None:
        raise ValueError("no quedan canales MIDI libres para la composición larga")
    prueba = deepcopy(fuente)
    for pista in nuevas:
        canal = proyectos.canal_de_pista(pista)
        if canal == canal_melodia:
            # El resto de la melodía va en un canal propio: en el proyecto cada canal es una pista.
            pista = mido.MidiTrack(m.copy(channel=libre) if hasattr(m, "channel") else m for m in pista)
            pista.name = f"{PREFIJO_IA} - Cancion"
        elif canal is not None:
            rol = next(p["role"] for p in informe["parts"] if p["channel"] == canal)
            pista.name = f"{PREFIJO_IA} - {NOMBRES_ROLES[rol]}"
        else:
            pista.name = f"{PREFIJO_IA} - Secciones"   # marcadores, se ven al abrirlo en Reaper
        prueba.tracks.append(pista)
    return prueba, informe


# =====================================================================
#  Escuchar la sugerencia y aceptarla o no
# =====================================================================

def proponer(prueba, proyecto, nombre):
    """Hace escuchar el proyecto de prueba (el proyecto con la sugerencia nueva) y pregunta
    en la pantalla "¿Aceptar sugerencia?". Si se acepta, el proyecto pasa a ser la prueba y
    se guarda. Devuelve True si se aceptó."""
    esp32.enviar("PANTALLA:SUGERENCIA")  # "¿Aceptar sugerencia?" Sí / No
    reproducir.reproducir_proyecto(prueba)

    if esp32.esperar_si_no():  # Sí: reemplaza a la sugerencia anterior y se guarda
        proyecto.tracks = prueba.tracks
        proyectos.guardar(proyecto, nombre)
        return True

    # No: se descarta. Como el chat guarda el historial, la IA sabe qué propuso
    # y pregunta qué cambiaría el usuario. Responder no es obligatorio.
    gem.hablar("El usuario escuchó la sugerencia y la rechazó. "
               "Preguntale en una sola frase qué le gustaría cambiar.")
    return False


def proponer_sugerencia(pista, proyecto, nombre):
    """Lo mismo que proponer(), para una sugerencia de una sola pista (MIDI-GPT o acordes
    de Gemini): la prueba es el proyecto sin las sugerencias anteriores, más esta pista."""
    prueba = _sin_sugerencias(proyecto)
    prueba.tracks = [p for p in prueba.tracks if proyectos.canal_de_pista(p) != CANAL_IA] + [pista]
    return proponer(prueba, proyecto, nombre)
