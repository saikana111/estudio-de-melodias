"""Deterministic motif development into a short chamber miniature.

The original tracks are preserved as the first statement. New melodic material
is explicitly derived from the source; this is a small compositional grammar,
not a general song-writing model. No beat is inferred from rubato note gaps.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
import statistics

import mido
from ensemble import Ensemble, arrange
from musical import Brief, Note, SCALES, key_candidates, read_notes, repeated_motif, track_from_notes, add_controls


@dataclass(frozen=True)
class Song:
    sections: tuple = ("theme", "variation", "contrast", "return", "coda")
    contrast_steps: int = 2
    contrast_rate: float = 0.85
    gap_ratio: float = 0.35
    # Optional explicit section overrides; absent means the original song behavior.
    expresion_secciones: dict | None = None

    def __post_init__(self):
        allowed = {"intensidad", "curva_dinamica", "articulacion", "actividad", "perfil_armonico",
                   "balance_bajo", "balance_respuesta"}
        if self.expresion_secciones is not None:
            if not isinstance(self.expresion_secciones, dict):
                raise ValueError("expresion_secciones debe ser un objeto")
            for kind, values in self.expresion_secciones.items():
                if kind not in ("variation", "contrast", "return", "coda") or not isinstance(values, dict) or set(values)-allowed:
                    raise ValueError("Ajustes de expresión por sección no válidos; el tema conserva el ensamble inicial")
                Brief(**values)
        if not isinstance(self.sections, (list, tuple)) or not 2 <= len(self.sections) <= 8:
            raise ValueError("Song requires 2..8 sections")
        if self.sections[0] != "theme" or self.sections[-1] != "coda":
            raise ValueError("Song must start with theme and end with coda")
        if any(s not in ("variation", "contrast", "return") for s in self.sections[1:-1]):
            raise ValueError("Middle sections must be variation, contrast or return")
        if type(self.contrast_steps) is not int or not -4 <= self.contrast_steps <= 4:
            raise ValueError("contrast_steps must be an integer in -4..4")
        for name, lower, upper in (("contrast_rate", 0.5, 1.5), ("gap_ratio", 0, 2)):
            value = getattr(self, name)
            if type(value) not in (float, int) or not lower <= value <= upper:
                raise ValueError(f"Invalid {name}")


def _shift_pitch(pitch, steps, tonic, mode):
    # Retain a chromatic inflection relative to the nearest scale degree.
    scale = [p for p in range(-24, 152) if (p-tonic) % 12 in SCALES[mode]]
    index = min(range(len(scale)), key=lambda i: (abs(scale[i]-pitch), scale[i]))
    target = index+steps
    if not 0 <= target < len(scale):
        raise ValueError("Diatonic transformation exceeds supported range")
    result = scale[target]+pitch-scale[index]
    if not 0 <= result <= 127:
        raise ValueError("Transformed melody exceeds MIDI range")
    return result


def _relative(notes):
    origin = notes[0].start
    return [replace(n, start=n.start-origin, end=n.end-origin) for n in notes]


def _variation(notes, tonic, mode):
    threshold = statistics.median(n.end-n.start for n in notes)*1.25
    result = []
    for n in _relative(notes):
        duration = n.end-n.start
        if n.pitch % 12 == tonic and duration >= max(12, threshold):
            a, b = n.start+round(duration*0.70), n.start+round(duration*0.85)
            result.extend((replace(n, end=a),
                           replace(n, start=a, end=b, pitch=_shift_pitch(n.pitch, 1, tonic, mode), velocity=max(1, n.velocity-10)),
                           replace(n, start=b)))
        else:
            result.append(n)
    return sorted(result)


def _contrast(notes, tonic, mode, settings):
    motif = repeated_motif(notes)
    fragment = notes[motif["starts"][0]:motif["starts"][0]+motif["length"]] if motif else notes[:min(6, len(notes))]
    fragment = _relative(fragment)
    length = max(n.end for n in fragment)
    breathing = round(statistics.median(n.end-n.start for n in fragment)*settings.gap_ratio)
    result = []
    for occurrence, steps in enumerate((settings.contrast_steps, settings.contrast_steps-1)):
        offset = occurrence*round((length+breathing)*settings.contrast_rate)
        for n in fragment:
            start = offset+round(n.start*settings.contrast_rate)
            end = max(start+1, offset+round(n.end*settings.contrast_rate))
            result.append(replace(n, start=start, end=end,
                                  pitch=_shift_pitch(n.pitch, steps, tonic, mode), velocity=min(110, n.velocity+3)))
    return sorted(result)


def _coda(notes, tonic, mode):
    unit = max(4, round(statistics.median(n.end-n.start for n in notes)))
    center = statistics.median(n.pitch for n in notes)
    target = min((p for p in range(12, 116) if p % 12 == tonic), key=lambda p: abs(p-center))
    # Scale degrees 5 -> 2 -> 1, over dominant then tonic; no leading-tone rewrite
    # of the original. Dorian/Mixolydian use their diatonic minor dominant.
    fifth = _shift_pitch(target, -3, tonic, mode)
    second = _shift_pitch(target, 1, tonic, mode)
    result = [Note(0, unit, fifth, 76), Note(unit, 2*unit, second, 72),
              Note(2*unit, 5*unit, target, 68)]
    dominant = "V" if mode in ("major", "minor") else "v"
    tonic_label = "I" if mode in ("major", "mixolydian") else "i"
    return result, ((0, dominant), (2*unit, tonic_label))


def _program(source, channel):
    programs = {m.program for t in source.tracks for m in t
                if m.type == "program_change" and m.channel == channel}
    if len(programs) > 1:
        raise ValueError("Song development currently requires a single melody instrument")
    return next(iter(programs), 0)


def develop(source, brief=None, melody_channel=0, ensemble=None, song=None):
    """Return a longer MIDI plus section/harmonic provenance. Source is immutable."""
    brief = brief or Brief(patron="sostenido", ritmo_armonico="libre")
    ensemble, song = ensemble or Ensemble(), song or Song()
    notes = read_notes(source, melody_channel)
    if not 4 <= len(notes) <= 64:
        raise ValueError("Song grammar currently accepts a 4..64-note seed melody")
    if any(n.channel != melody_channel for n in read_notes(source)):
        raise ValueError("Use a melody-only source for song development; existing accompaniment is not extended")
    if any(m.type in ("note_on", "note_off") and m.channel == 9 for t in source.tracks for m in t):
        raise ValueError("Use a source without a drum track for song development")
    # Dynamic tempo is preserved in accompaniment mode. Extending it requires a
    # performance-time map, not simply appending ticks at the final tempo.
    tempo, meters, tick = 500000, set(), 0
    for msg in mido.merge_tracks(source.tracks):
        tick += msg.time
        if msg.type == "set_tempo":
            if tick and msg.tempo != tempo:
                raise ValueError("Song development needs constant tempo; accompaniment preserves variable tempo")
            tempo = msg.tempo
        if msg.type == "time_signature":
            meters.add((msg.numerator, msg.denominator))
    if len(meters) > 1:
        raise ValueError("Changing meter is unsupported in song development")
    if brief.cambios:
        raise ValueError("Song mode uses section-local harmony; omit absolute cambios from the seed brief")
    key = key_candidates(notes)[0]
    tonic, mode = (brief.tonic, brief.mode) if brief.tonic is not None else (key["tonic"], key["mode"])
    resolved = replace(brief, tonic=tonic, mode=mode)
    # First statement uses the exact accepted accompaniment path.
    first_arrangement, first_report = arrange(source, resolved, melody_channel, ensemble)
    occupied = {m.channel for t in source.tracks for m in t if hasattr(m, "channel")}
    free = [c for c in range(16) if c not in occupied and c not in (9, melody_channel)
            and c not in ensemble.reserved_channels]
    required = 3 if ensemble.responses else 2
    if len(free) < required:
        raise ValueError("Insufficient MIDI channels for song ensemble")
    role_channels = dict(zip(("harmony", "bass", "response"), free))
    programs = {"harmony": ensemble.harmony_program, "bass": ensemble.bass_program,
                "response": ensemble.response_program}
    part_notes = {role: [] for role in role_channels}
    part_controls = {role: [] for role in role_channels}
    melody_development = []
    sections = []
    end = max(n.end for n in notes)
    gap = round(statistics.median(n.end-n.start for n in notes)*song.gap_ratio)
    cursor = 0
    program = _program(source, melody_channel)
    for number, kind in enumerate(song.sections):
        if kind == "theme":
            arranged, local_report = first_arrangement, first_report
            local_notes, offset, local_end = notes, 0, end
            description = "Exact original performance and seed accompaniment"
        else:
            offset = cursor+gap
            local_brief = resolved
            local_ensemble = ensemble
            if kind == "variation":
                local_notes = _variation(notes, tonic, mode)
                description = "Original contour/rhythm with upper-neighbor ornaments on held tonic notes"
                local_ensemble = replace(ensemble, responses=False)
            elif kind == "contrast":
                local_notes = _contrast(notes, tonic, mode, song)
                description = "Source motif sequenced by scale degrees and proportionally shortened/lengthened"
                local_brief = replace(resolved, repetir_armonia=False, registro="medio")
            elif kind == "return":
                local_notes = [replace(n, velocity=min(115, n.velocity+4)) for n in _relative(notes)]
                description = "Return of original pitches and relative timing, slightly stronger dynamics"
            else:
                local_notes, changes = _coda(notes, tonic, mode)
                local_brief = replace(resolved, cambios=changes, patron="sostenido", registro="medio")
                local_ensemble = replace(ensemble, responses=False)
                description = "New 5-2-1 melodic close over dominant and tonic"
            overrides = (song.expresion_secciones or {}).get(kind, {})
            local_brief = replace(local_brief, **overrides)
            local = mido.MidiFile(type=1, ticks_per_beat=source.ticks_per_beat)
            local.tracks.append(track_from_notes(local_notes, program, melody_channel, kind))
            arranged, local_report = arrange(local, local_brief, melody_channel, local_ensemble)
            local_end = max(n.end for n in local_notes)
            melody_development.extend(replace(n, start=n.start+offset, end=n.end+offset,
                                               channel=melody_channel) for n in local_notes)
        for part in local_report["parts"]:
            role = part["role"]
            for track in arranged.tracks:
                tick = 0
                for msg in track:
                    tick += msg.time
                    if msg.type == 'control_change' and msg.channel == part['channel']:
                        part_controls[role].append((tick+offset, msg.copy(channel=role_channels[role], time=0)))
            part_notes[role].extend(replace(n, start=n.start+offset, end=n.end+offset,
                                            channel=role_channels[role])
                                    for n in read_notes(arranged, part["channel"]))
        sections.append({"index": number, "kind": kind, "start_tick": offset,
                         "end_tick": offset+local_end, "description": description,
                         "melody_note_count": len(local_notes),
                         "expression": {key: local_report["brief"][key] for key in
                             ("intensidad", "curva_dinamica", "articulacion", "actividad", "perfil_armonico", "balance_bajo", "balance_respuesta")},
                         "harmony": [{**h, "start_tick": h["start_tick"]+offset,
                                      "end_tick": h["end_tick"]+offset} for h in local_report["harmony"]]})
        cursor = offset+local_end
    result = deepcopy(source)
    result.type = 1
    result.tracks.append(track_from_notes(melody_development, program, melody_channel, "Melody development"))
    parts = []
    for role, generated in part_notes.items():
        if generated:
            channel = role_channels[role]
            result.tracks.append(add_controls(track_from_notes(generated, programs[role], channel, role.capitalize()), part_controls[role]))
            parts.append({"role": role, "channel": channel, "program": programs[role]})
    markers = mido.MidiTrack([mido.MetaMessage("track_name", name="Song form")])
    previous = 0
    for section in sections:
        markers.append(mido.MetaMessage("marker", text=f"{section['index']+1}: {section['kind']}",
                                        time=section["start_tick"]-previous))
        previous = section["start_tick"]
    result.tracks.append(markers)
    del result.merged_track  # Deepcopy can retain the source's cached merged timeline.
    warnings = list(first_report["warnings"])
    if brief.tonic is None:
        warnings.append("Song key inferred once from the seed; confirm before accepting the development.")
    return result, {"brief": asdict(resolved), "ensemble": asdict(ensemble), "song": asdict(song),
                    "key": {"tonic": tonic, "mode": mode}, "parts": parts, "sections": sections,
                    "source_tracks_preserved": result.tracks[:len(source.tracks)] == source.tracks,
                    "duration_seconds": round(mido.tick2second(cursor, source.ticks_per_beat, tempo), 3),
                    "warnings": warnings,
                    "limitations": ["Deterministic short-form grammar; not a general long-form composer.",
                                    "New sections transform note material, not source CC/pitch-bend expression.",
                                    "Constant-tempo melody-only input; rubato note timing is preserved in the theme.",
                                    "Section transitions are short breaths; richer bridges remain future work."]}
