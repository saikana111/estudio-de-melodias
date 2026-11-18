"""Edit generated tracks by role. Recorded tracks are never removal candidates."""
from copy import deepcopy
from pathlib import Path
import os
import tempfile

import mido

PREFIX = "Sugerencia IA"
GM_FAMILIES = ("piano", "percusión afinada", "órgano", "guitarra", "bajo",
               "cuerdas", "ensamble", "metales", "saxofón", "flauta",
               "sintetizador", "colchón", "efecto", "instrumento étnico",
               "percusión", "efecto sonoro")


def guardar_midi(midi, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temp = Path(f.name)
    try:
        midi.save(temp)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def rol(track):
    return track.name.removeprefix(PREFIX).strip(" -") if track.name.startswith(PREFIX) else ""


def etiqueta(track):
    role = rol(track)
    if role == "Bateria":
        return "batería"
    program = next((m.program for m in track if m.type == "program_change"), None)
    if program is None:
        return role
    return f"{role} ({GM_FAMILIES[program // 8]})"


def sin_pistas(project, names):
    result = deepcopy(project)
    result.tracks = [t for t in result.tracks if not (rol(t) and t.name in names)]
    del result.merged_track
    return result


def incorporar(project, track):
    result = sin_pistas(project, {track.name})
    used = {m.channel for t in result.tracks for m in t if hasattr(m, "channel")}
    added = deepcopy(track)
    ch = next((m.channel for m in added if hasattr(m, "channel")), None)
    if ch in used:
        free = next((i for i in range(2, 16) if i != 9 and i not in used), None)
        if ch == 9 or free is None:
            raise ValueError("No hay un canal libre para agregar esa pista.")
        added = mido.MidiTrack(m.copy(channel=free) if hasattr(m, "channel") else m for m in added)
    result.tracks.append(added)
    result.type = 1
    return result


def ajustar_dinamica(project, names, delta):
    result = deepcopy(project)
    for track in result.tracks:
        if rol(track) and track.name in names:
            for msg in track:
                if msg.type == "note_on" and msg.velocity:
                    msg.velocity = min(127, max(1, msg.velocity + delta))
    del result.merged_track
    return result
