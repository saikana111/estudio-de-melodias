import bisect
import math

import mido


def detectar_tonalidad(archivo):
    """Detecta la tonalidad y la escala de un archivo MIDI con music21, que aplica
    algoritmos de teoría musical real. Devuelve la tonalidad (por ejemplo, C major).
    Detecta escalas mayores y menores; si se quieren escalas más exóticas, music21
    las tiene, pero hay que compararlas una por una con las notas."""
    
    from music21 import converter
    return converter.parse(archivo).analyze("key")


def grilla_rock(midi, inicios):
    tempo = next((m.tempo for pista in midi.tracks for m in pista if m.type == "set_tempo"), 500000)
    pulso = estimar_pulso(inicios, midi.ticks_per_beat, tempo)
    return {"beat_ticks": max(1, round(pulso)), "downbeat": inicios[0]}


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


# =====================================================================
#  Cuantización: llevar los tiempos cantados a figuras (negra, corchea...)
# =====================================================================
# Basic Pitch no cuantiza: guarda cada nota en el instante exacto en que la detectó (con una
# precisión de unos 12 ms) y escribe todo como si fuera a 120 BPM, aunque se haya cantado a
# otro tempo. Por eso una nota que "era" una negra puede durar 1,13 tiempos y otra empezar en
# el tiempo 5,9. Acá se estima el pulso real del canto y cada inicio y cada duración se llevan
# a la grilla de ese pulso, en semicorcheas. Las notas quedan como figuras exactas y la teoría
# musical que viene después (acordes, compases, desarrollo de la canción) trabaja más prolija.
#
# El tempo del canto se respeta: la grilla se arma con el pulso de la persona, no con los
# 120 BPM del archivo, así que la melodía dura lo mismo que cuando se cantó.

# False para no cuantizar: la melodía queda con los tiempos tal cual se cantaron. Conviene
# cuando se canta libre, sin un pulso parejo (ver cuantizar()).
CUANTIZAR = True
SUBDIVISION = 4          # partes por pulso: 4 = semicorcheas, 2 = corcheas
# Tempos que se prueban. Es una octava justa a propósito: una melodía a 140 BPM también
# encaja en una grilla de 70 con las figuras al doble (corcheas en vez de negras) y no hay
# forma de saber cuál de las dos se pensó. Se elige siempre la que cae en este rango.
BPM_MINIMO = 60
BPM_MAXIMO = 120
FIGURAS = {1: "semicorchea", 2: "corchea", 3: "corchea con puntillo", 4: "negra",
           6: "negra con puntillo", 8: "blanca", 12: "blanca con puntillo", 16: "redonda"}


def _notas(pista):
    """Notas de una pista como [inicio, fin, nota, velocity] (ticks absolutos)."""
    notas, abiertas, ahora = [], {}, 0
    for mensaje in pista:
        ahora += mensaje.time
        if mensaje.type == "note_on" and mensaje.velocity > 0:
            abiertas[mensaje.note] = (ahora, mensaje.velocity)
        elif mensaje.type in ("note_on", "note_off") and mensaje.note in abiertas:
            inicio, velocity = abiertas.pop(mensaje.note)
            notas.append([inicio, ahora, mensaje.note, velocity])
    return sorted(notas)


def _desajuste(inicios, paso):
    """Qué tan mal caen los inicios de las notas en una grilla de ese paso, entre 0 (todos
    justo sobre una línea de la grilla) y 1 (desparramados al azar).

    Cada inicio se piensa como una aguja de reloj que da una vuelta por paso: si la grilla es
    la correcta, todas las agujas apuntan más o menos para el mismo lado (el lugar donde cae
    la grilla); si no, apuntan para cualquier lado y se anulan al sumarlas. No hace falta
    saber de antemano dónde empieza la grilla: la suma lo encuentra sola."""
    x = sum(math.cos(2 * math.pi * t / paso) for t in inicios)
    y = sum(math.sin(2 * math.pi * t / paso) for t in inicios)
    return 1 - math.hypot(x, y) / len(inicios)


def estimar_pulso(inicios, ticks_por_tiempo, tempo_archivo=500000):
    """Cuánto dura un pulso (una negra) del canto, en ticks del archivo.

    1) Se prueban todos los tempos entre BPM_MINIMO y BPM_MAXIMO, de a un cuarto de BPM, y se
       queda el que deja los inicios de las notas más cerca de una semicorchea (_desajuste).
       Antes se usaba la mediana de las distancias entre notas, pero con mitad de corcheas y
       mitad de negras caía justo entre las dos y daba un tempo equivocado.
    2) Ajuste fino: cada inicio se ubica en la semicorchea más cercana de esa grilla y se
       calcula la grilla que mejor pasa por todos los inicios (una recta por cuadrados mínimos)."""
    segundos_por_tick = tempo_archivo / 1e6 / ticks_por_tiempo
    if len(inicios) < 3:
        return float(ticks_por_tiempo)   # con dos notas no se puede saber el tempo
    candidatos = [60 / (bpm / 4) / segundos_por_tick
                  for bpm in range(BPM_MINIMO * 4, BPM_MAXIMO * 4 + 1)]   # pulso en ticks
    # Además de caer en semicorcheas, se premia que muchas notas caigan en corcheas y en el
    # pulso: con errores grandes al cantar, un tempo equivocado puede encajar de casualidad
    # en semicorcheas, pero no en las tres grillas a la vez. Con esto, en 120 melodías de
    # prueba con errores de 30 a 60 ms acertó el tempo en 119 (solo semicorcheas: 101).
    pulso = min(candidatos, key=lambda p: _desajuste(inicios, p / SUBDIVISION)
                + 0.5 * _desajuste(inicios, p / 2) + 0.25 * _desajuste(inicios, p))

    for _ in range(3):   # unas vueltas de ajuste alcanzan para que se estabilice
        paso = pulso / SUBDIVISION
        lugares = [round((t - inicios[0]) / paso) for t in inicios]
        if len(set(lugares)) < 2:
            break
        media_x = sum(lugares) / len(lugares)
        media_y = sum(inicios) / len(inicios)
        pendiente = (sum((x - media_x) * (y - media_y) for x, y in zip(lugares, inicios))
                     / sum((x - media_x) ** 2 for x in lugares))
        pulso = pendiente * SUBDIVISION
    return pulso


def cuantizar(archivo, bpm=None):
    """Lleva los tiempos de la melodía a figuras exactas y guarda en el mismo archivo.

    bpm: el tempo, si se conoce (por ejemplo, si se cantó con metrónomo). Sin él, se estima
    con estimar_pulso(), que anda bien cuando se canta con un pulso parejo. Si se canta muy
    libre no hay un pulso que encontrar: igual se arma una grilla, pero las notas pueden
    moverse bastante (el resumen dice cuánto).

    - Cada inicio se mide desde la nota anterior y esa distancia se redondea a semicorcheas
      (así, si la persona se apura o se frena un poco, la grilla la sigue y no se acumula error).
    - Cada nota dura hasta la siguiente (esa es su figura), salvo que haya sonado menos de la
      mitad de ese tiempo: entonces hay un silencio y su duración se redondea a semicorcheas.
    - Se borran los pitchwheel (los vibratos que guarda Basic Pitch): quedaban en sus tiempos
      viejos y la app igual no los usa.
    Devuelve un resumen: tempo estimado (BPM), pulso en ticks y cuánto se movieron las notas."""
    if not CUANTIZAR:
        return None
    midi = mido.MidiFile(archivo)
    tempo = next((m.tempo for p in midi.tracks for m in p if m.type == "set_tempo"), 500000)
    con_notas = [p for p in midi.tracks if any(m.type == "note_on" for m in p)]
    todas = sorted(n for p in con_notas for n in _notas(p))
    if len(todas) < 2:
        return None   # con una sola nota no hay ritmo que corregir

    inicios = sorted({n[0] for n in todas})
    if bpm:   # tempo conocido: un pulso dura 60/bpm segundos, pasado a ticks del archivo
        pulso = 60 / bpm / (tempo / 1e6 / midi.ticks_per_beat)
    else:
        pulso = estimar_pulso(inicios, midi.ticks_per_beat, tempo)
    paso = pulso / SUBDIVISION

    # Inicio cuantizado de cada inicio original (las notas que empiezan juntas siguen juntas)
    nuevo = {inicios[0]: float(inicios[0])}
    for anterior, actual in zip(inicios, inicios[1:]):
        nuevo[actual] = nuevo[anterior] + max(1, round((actual - anterior) / paso)) * paso

    movidas = []
    for pista in con_notas:
        notas = _notas(pista)
        cuantizadas = []
        for inicio, fin, nota, velocity in notas:
            a = nuevo[inicio]
            pasos = max(1, round((fin - inicio) / paso))
            despues = inicios[bisect.bisect_right(inicios, inicio):]   # inicios de las notas siguientes
            if despues:
                hasta_la_siguiente = max(1, round((nuevo[despues[0]] - a) / paso))
                # La figura de una nota es el tiempo hasta la nota siguiente: al cantar, cada nota
                # se corta un poco antes de la otra y eso no es un silencio. Solo si sonó menos de
                # la mitad de ese tiempo hay un silencio de verdad y se respeta su duración.
                if fin - inicio >= 0.5 * (despues[0] - inicio):
                    pasos = hasta_la_siguiente
                else:
                    pasos = min(_figura_simple(fin - inicio, paso), hasta_la_siguiente)
            else:
                pasos = _figura_simple(fin - inicio, paso)   # la última nota no tiene con qué medirse
            cuantizadas.append((round(a), round(a + pasos * paso), nota, velocity))
            movidas.append(abs(a - inicio))
        canal = next((m.channel for m in pista if m.type == "note_on"), 0)
        _reescribir(pista, cuantizadas, canal)

    midi.save(archivo)
    segundos_por_tick = tempo / 1e6 / midi.ticks_per_beat
    return {"bpm": round(60 / (pulso * segundos_por_tick), 1), "pulso_ticks": round(pulso, 2),
            "notas": len(todas),
            "movimiento_medio_ms": round(1000 * segundos_por_tick * sum(movidas) / len(movidas)),
            "movimiento_maximo_ms": round(1000 * segundos_por_tick * max(movidas))}


def _figura_simple(ticks, paso):
    """Para una nota seguida de un silencio (o la última): la figura común más cercana, en
    semicorcheas. Al cantar, una nota se corta antes de su valor, así que se compara con lo
    que sonó un 15 % más largo (una blanca cantada suele durar como 7 semicorcheas)."""
    largo = ticks * 1.15 / paso
    return min(FIGURAS, key=lambda pasos: abs(pasos - largo))


def _reescribir(pista, notas, canal):
    """Vuelve a armar la pista con las notas cuantizadas. Se conservan los demás mensajes
    (nombre, instrumento...) salvo los de nota y los pitchwheel."""
    eventos, ahora = [], 0
    for mensaje in pista:
        ahora += mensaje.time
        if mensaje.type not in ("note_on", "note_off", "pitchwheel", "end_of_track"):
            eventos.append((ahora, 0, mensaje.copy(time=0)))
    for inicio, fin, nota, velocity in notas:
        eventos.append((inicio, 2, mido.Message("note_on", channel=canal, note=nota, velocity=velocity)))
        eventos.append((fin, 1, mido.Message("note_off", channel=canal, note=nota, velocity=0)))
    eventos.sort(key=lambda e: (e[0], e[1]))   # en el mismo instante: primero apagar, después prender
    pista.clear()
    anterior = 0
    for tick, _, mensaje in eventos:
        pista.append(mensaje.copy(time=tick - anterior))
        anterior = tick
    pista.append(mido.MetaMessage("end_of_track", time=0))


def figura(ticks, pulso_ticks):
    """Nombre de la figura de una duración ya cuantizada ("negra", "corchea"...)."""
    pasos = round(ticks / (pulso_ticks / SUBDIVISION))
    return FIGURAS.get(pasos, f"{pasos} semicorcheas")


def midi_txt(archivo, canal=None):
    """Gemini no es capaz de leer archivos MIDI. Esta función recorre el archivo nota por
    nota y lo transforma en texto, con cada nota, su velocidad y su tiempo. Ese texto es
    el que se le envía a la IA para que pueda comprenderlo y dar sugerencias musicales."""
    archivo_midi = mido.MidiFile(archivo)
    texto = " "
    for pista in archivo_midi.tracks:
        tiempo_acumulado = 0
        for mensaje in pista:
            # Los mensajes tienen un tiempo "delta" (tiempo desde el evento anterior)
            tiempo_acumulado += mensaje.time
            # Filtrar solo los mensajes de nota musical
            if mensaje.type == "note_on" and mensaje.velocity > 0 and (canal is None or mensaje.channel == canal):
                texto = f"{texto} \n Nota: {mensaje.note} | Velocidad: {mensaje.velocity} | Canal: {mensaje.channel} | Tiempo: {tiempo_acumulado}"
    return texto


    
