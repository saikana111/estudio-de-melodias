"""Deterministic tonal accompaniment. Times are MIDI ticks, never guessed seconds.

This is an inspectable major/minor baseline, not a universal composition model.
The original performance is never quantized or pitch-corrected.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from itertools import combinations
import math
import statistics

import mido


@dataclass(frozen=True, order=True)
class Note:
    start: int
    end: int
    pitch: int
    velocity: int = 72
    channel: int = 0


def read_notes(midi, channel=None):
    """Pair events by channel AND pitch, FIFO for overlapping repeated notes.

    Fail on unmatched events rather than silently using a damaged transcription.
    Sustain is not expanded: source playback retains its original controllers.
    """
    if midi.type == 2 or midi.ticks_per_beat <= 0:
        raise ValueError("Only synchronous, PPQ MIDI files are supported")
    active, notes, tick = defaultdict(deque), [], 0
    for msg in mido.merge_tracks(midi.tracks):
        tick += msg.time
        if msg.type not in ("note_on", "note_off"):
            continue
        if channel is not None and msg.channel != channel:
            continue
        if msg.channel == 9:
            continue
        key = (msg.channel, msg.note)
        if msg.type == "note_on" and msg.velocity:
            active[key].append((tick, msg.velocity))
        elif active[key]:
            start, velocity = active[key].popleft()
            if tick <= start:
                raise ValueError("Zero-length note in source MIDI")
            notes.append(Note(start, tick, msg.note, velocity, msg.channel))
        else:
            raise ValueError(f"Unmatched note-off: channel {msg.channel}, pitch {msg.note}")
    if any(active.values()):
        raise ValueError("Source contains notes without note-off; repair the recording first")
    return sorted(notes)


@dataclass(frozen=True)
class Brief:
    instrumento: int = 0
    voces: int = 3
    notas: str = "largas"
    espacio: str = "medio"
    registro: str = "medio"
    disposicion: str = "cerrada"
    patron: str = "bloques"
    tonic: int | None = None
    mode: str = "major"
    # Quarter-note duration in source ticks; None uses MIDI PPQ, not onset gaps.
    beat_ticks: int | None = None
    downbeat: int = 0
    numerator: int = 4
    denominator: int = 4
    bars_per_chord: int = 1
    # Optional reviewed harmonic landmarks: [(source_tick, roman_chord), ...].
    cambios: tuple = ()
    ritmo_armonico: str = "compases"
    costo_cambio: float = 3.0
    repetir_armonia: bool = True
    # These are musical controls, not measurements of a listener's emotions.
    intensidad: int = 68
    curva_dinamica: str = "estable"
    articulacion: str = "original"
    actividad: int = 1
    perfil_armonico: str = "automatico"
    balance_bajo: int = -13
    balance_respuesta: int = -20

    def __post_init__(self):
        for name, low, high in (("instrumento", 0, 127), ("voces", 1, 4),
                                ("downbeat", 0, 2**31-1), ("bars_per_chord", 1, 4),
                                ("intensidad", 24, 110), ("actividad", 1, 4),
                                ("balance_bajo", -36, 12), ("balance_respuesta", -36, 12)):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"Invalid {name}: {value}")
        for name, choices in {
            "notas": ("cortas", "medias", "largas"),
            "espacio": ("poco", "medio", "mucho"),
            "registro": ("grave", "medio", "agudo"),
            "disposicion": ("cerrada", "abierta"),
            "patron": ("bloques", "arpegio", "sostenido"),
            "mode": ("major", "minor", "dorian", "mixolydian"),
            "ritmo_armonico": ("compases", "libre"),
            "curva_dinamica": ("estable", "crescendo", "diminuendo", "arco"),
            "articulacion": ("original", "legato", "normal", "staccato"),
            "perfil_armonico": ("automatico", "reposado", "creciente", "resolver", "arco"),
        }.items():
            if getattr(self, name) not in choices:
                raise ValueError(f"Invalid {name}: {getattr(self, name)}")
        if self.tonic is not None and (type(self.tonic) is not int or not 0 <= self.tonic < 12):
            raise ValueError("tonic must be a pitch class 0..11")
        if self.beat_ticks is not None and (type(self.beat_ticks) is not int or self.beat_ticks < 1):
            raise ValueError("beat_ticks must be a positive integer")
        if (self.numerator, self.denominator) not in ((3, 4), (4, 4), (6, 8)):
            raise ValueError("Baseline supports 3/4, 4/4 and 6/8 only")
        previous = -1
        for change in self.cambios:
            if len(change) != 2 or type(change[0]) is not int or change[0] <= previous or not isinstance(change[1], str):
                raise ValueError("cambios must contain increasing nonnegative ticks and Roman chord labels")
            previous = change[0]
        if type(self.costo_cambio) not in (int, float) or not math.isfinite(self.costo_cambio) or not 0.1 <= self.costo_cambio <= 20:
            raise ValueError("costo_cambio must be a finite number in 0.1..20")
        if type(self.repetir_armonia) is not bool:
            raise ValueError("repetir_armonia must be boolean")


SCALES = {"major": (0, 2, 4, 5, 7, 9, 11), "minor": (0, 2, 3, 5, 7, 8, 10),
          "dorian": (0, 2, 3, 5, 7, 9, 10), "mixolydian": (0, 2, 4, 5, 7, 9, 10)}
PROFILES = {
    "major": (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88),
    "minor": (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17),
}
NAMES = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")


def key_candidates(notes):
    """Duration-weighted profile correlations; scores are NOT probabilities."""
    histogram = [0.0] * 12
    for n in notes:
        histogram[n.pitch % 12] += n.end - n.start
    mean = statistics.mean(histogram)
    x = [v - mean for v in histogram]
    result = []
    for mode, profile in PROFILES.items():
        for tonic in range(12):
            y = [profile[(pc - tonic) % 12] - statistics.mean(profile) for pc in range(12)]
            denom = math.sqrt(sum(v*v for v in x) * sum(v*v for v in y))
            score = sum(a*b for a, b in zip(x, y)) / denom if denom else 0
            result.append({"tonic": tonic, "mode": mode, "name": NAMES[tonic] + " " + mode,
                           "score": round(score, 5)})
    return sorted(result, key=lambda item: item["score"], reverse=True)


@dataclass(frozen=True)
class Chord:
    degree: int
    root: int
    pcs: tuple[int, ...]
    label: str


def chords_for(tonic, mode):
    scale = SCALES[mode]
    labels = {"major": ("I", "ii", "iii", "IV", "V", "vi", "vii°"),
              "minor": ("i", "ii°", "III", "iv", "v", "VI", "VII"),
              "dorian": ("i", "ii", "III", "IV", "v", "vi°", "VII"),
              "mixolydian": ("I", "ii", "iii°", "IV", "v", "vi", "VII")}[mode]
    chords = [Chord(i, (tonic+s) % 12,
                    tuple((tonic+scale[(i+j) % 7]) % 12 for j in (0, 2, 4)), labels[i])
              for i, s in enumerate(scale)]
    if mode == "minor":
        chords.append(Chord(4, (tonic+7) % 12, ((tonic+7) % 12, (tonic+11) % 12,
                                             (tonic+2) % 12), "V"))
    return chords


def _transition(a, b):
    # Soft functional preferences; melody evidence can override them.
    preferred = {0: (1, 3, 4, 5), 1: (4, 6), 2: (5, 3), 3: (0, 1, 4),
                 4: (0, 5), 5: (1, 3, 4), 6: (0,)}
    return 0.25 if a == b else (0 if b.degree in preferred[a.degree] else 0.65)


def _fit(notes, chord, start, end, beat):
    total = cost = 0.0
    for index, n in enumerate(notes):
        overlap = max(0, min(end, n.end) - max(start, n.start)) / beat
        if not overlap:
            continue
        # Held notes and notes at the harmony boundary carry more evidence.
        weight = overlap * (1.6 if n.start <= start < n.end else 1.0)
        distance = min(min((n.pitch-pc) % 12, (pc-n.pitch) % 12) for pc in chord.pcs)
        penalty = 0 if distance == 0 else 1.7 if distance == 1 else 1.0
        # A short non-chord tone resolving by step to a longer chord tone is
        # different from an unresolved clash. This is a heuristic, not a parser
        # for suspensions/counterpoint; the original note remains untouched.
        if distance and index+1 < len(notes):
            following = notes[index+1]
            if (following.start < end and following.pitch % 12 in chord.pcs
                    and abs(following.pitch-n.pitch) <= 2
                    and n.end-n.start < following.end-following.start):
                penalty *= 0.25
        cost += weight * penalty
        total += weight
    return 4 * cost / total if total else 0.0


def harmonic_tension(chord):
    """Functional heuristic in 0..1, not a psychoacoustic or emotional score."""
    return (0.0, 0.45, 0.30, 0.40, 0.80, 0.25, 1.0)[chord.degree]


def tension_target(profile, position):
    x = max(0.0, min(1.0, position))
    return {"reposado": 0.1, "creciente": 0.15+0.65*x,
            "resolver": 0.75*(1-x), "arco": 0.1+0.7*(1-abs(2*x-1))}.get(profile)


def _expression_cost(chord, start, end, notes, brief):
    if brief is None or brief.perfil_armonico == "automatico":
        return 0.0
    first, last = notes[0].start, max(n.end for n in notes)
    target = tension_target(brief.perfil_armonico, ((start+end)/2-first)/max(1, last-first))
    return 2.0*abs(harmonic_tension(chord)-target)


def _free_harmony(notes, chords, change_cost, brief=None):
    """Semi-Markov search: jointly select chord identities and change locations.

    Candidates are real melody onsets, not guessed beats. A segment may span up
    to 16 onsets; adjacent equal chords are coalesced. O(N * 16 * C^2) states,
    with additional note-overlap scoring; bounded to 512 source notes.
    """
    if len(notes) > 512:
        raise ValueError("Free-time search supports at most 512 notes; split into phrases")
    boundaries = sorted({n.start for n in notes}) + [max(n.end for n in notes)]
    unit = statistics.median(n.end-n.start for n in notes)
    best = [{} for _ in boundaries]
    for end_idx in range(1, len(boundaries)):
        for j, chord in enumerate(chords):
            candidates = []
            for start_idx in range(max(0, end_idx-16), end_idx):
                start, end = boundaries[start_idx], boundaries[end_idx]
                occupied = sum(max(0, min(end, n.end)-max(start, n.start)) for n in notes) / unit
                fit = _fit(notes, chord, start, end, unit) * occupied / 4
                fit += _expression_cost(chord, start, end, notes, brief)*occupied/4
                if brief and brief.perfil_armonico != "automatico" and end_idx == len(boundaries)-1:
                    fit += 2*abs(harmonic_tension(chord)-tension_target(brief.perfil_armonico, 1))
                # Diminished triads remain available but need positive evidence.
                fit += 0.3 * occupied if "°" in chord.label else 0
                if start_idx == 0:
                    candidates.append((fit + (0 if chord.degree == 0 else 0.4), [(start, end, chord)]))
                else:
                    for k, (previous_cost, path) in best[start_idx].items():
                        transition = 0 if j == k else change_cost + _transition(chords[k], chord)
                        candidates.append((previous_cost + fit + transition, path + [(start, end, chord)]))
            best[end_idx][j] = min(candidates, key=lambda candidate: candidate[0])
    _, path = min(best[-1].values(), key=lambda candidate: candidate[0])
    merged = []
    for start, end, chord in path:
        if merged and merged[-1][2] == chord:
            merged[-1] = (merged[-1][0], end, chord)
        else:
            merged.append((start, end, chord))
    return merged


def repeated_motif(notes):
    """Longest exact pitch motif (4..16 notes), with nonoverlapping occurrences.

    This deliberately does not claim to infer musical phrase boundaries from
    rubato timing. Pitch-only repeats are proposals, and can be disabled.
    """
    # Note-order motif matching is meaningful for a melody, not a chord stack.
    if not notes:
        return None
    tolerance = statistics.median(n.end-n.start for n in notes) * 0.1
    if any(a.start == b.start or a.end-b.start > tolerance for a, b in zip(notes, notes[1:])):
        return None
    pitches = [n.pitch for n in notes]
    for length in range(min(16, len(notes)//2), 3, -1):
        groups = defaultdict(list)
        for start in range(len(notes)-length+1):
            key = tuple(pitches[start:start+length])
            if len(set(key)) >= 3 and (not groups[key] or start >= groups[key][-1]+length):
                groups[key].append(start)
        repeated = [(key, starts) for key, starts in groups.items() if len(starts) > 1]
        if repeated:
            key, starts = max(repeated, key=lambda item: len(item[1]))
            return {"length": length, "starts": starts, "pitches": key}
    return None


def _repeat_harmony(notes, chords, cost, motif, brief=None):
    """Reuse chord decisions at matching note positions; retain performance time."""
    length, starts = motif["length"], motif["starts"]
    canonical = notes[starts[0]:starts[0]+length]
    template = _free_harmony(canonical, chords, cost, brief)
    indices = {n.start: i for i, n in enumerate(canonical)}
    changes = [(indices[start], chord) for start, _, chord in template]
    result, cursor = [], 0
    for occurrence in starts:
        if cursor < occurrence:
            result.extend(_free_harmony(notes[cursor:occurrence], chords, cost, brief))
        phrase = notes[occurrence:occurrence+length]
        for i, (index, chord) in enumerate(changes):
            stop = phrase[changes[i+1][0]].start if i+1 < len(changes) else max(n.end for n in phrase)
            result.append((phrase[index].start, stop, chord))
        cursor = occurrence+length
    if cursor < len(notes):
        result.extend(_free_harmony(notes[cursor:], chords, cost, brief))
    # Adjacent source notes can overlap slightly after transcription. Harmonic
    # segments must not overlap even though the source melody is preserved.
    return [(a, min(b, result[i+1][0]) if i+1 < len(result) else b, c)
            for i, (a, b, c) in enumerate(result) if b > a]


def plan_harmony(notes, brief, ppq):
    if not notes:
        raise ValueError("Selected melody channel has no notes")
    candidates = key_candidates(notes)
    tonic, mode = (brief.tonic, brief.mode) if brief.tonic is not None else (
        candidates[0]["tonic"], candidates[0]["mode"])
    beat = brief.beat_ticks or ppq
    bar = beat * brief.numerator * 4 / brief.denominator
    span = bar * brief.bars_per_chord
    end = max(n.end for n in notes)
    # A pickup gets a short initial harmonic segment, not a shifted melody.
    boundaries = [0] if brief.downbeat else []
    boundaries += list(range(brief.downbeat, end, max(1, round(span))))
    first = min(n.start for n in notes)
    boundaries = sorted({first} | {t for t in boundaries if first < t < end}) + [end]
    chords = chords_for(tonic, mode)
    costs, paths = {}, {}
    for idx, (start, stop) in enumerate(zip(boundaries, boundaries[1:])):
        next_costs, next_paths = {}, {}
        for j, chord in enumerate(chords):
            local = _fit(notes, chord, start, stop, beat)
            local += _expression_cost(chord, start, stop, notes, brief)
            # Prefer a settled final tonic, but do not force it against the melody.
            if idx == len(boundaries)-2 and chord.degree != 0 and brief.perfil_armonico == "automatico":
                local += 0.65
            if idx == 0:
                next_costs[j] = local + (0 if chord.degree == 0 else 0.3)
                next_paths[j] = [j]
            else:
                best = min(costs, key=lambda k: costs[k] + _transition(chords[k], chord))
                next_costs[j] = costs[best] + _transition(chords[best], chord) + local
                next_paths[j] = paths[best] + [j]
        costs, paths = next_costs, next_paths
    path = paths[min(costs, key=costs.get)]
    plan = [(a, b, chords[j]) for a, b, j in zip(boundaries, boundaries[1:], path)]
    motif = None
    if brief.ritmo_armonico == "libre" and not brief.cambios:
        plan = _free_harmony(notes, chords, brief.costo_cambio, brief)
        motif = repeated_motif(notes) if brief.repetir_armonia and brief.perfil_armonico in ("automatico", "reposado") else None
        if motif:
            plan = _repeat_harmony(notes, chords, brief.costo_cambio, motif, brief)
    if brief.cambios:
        by_label = {c.label: c for c in chords}
        if brief.cambios[0][0] < first or brief.cambios[-1][0] >= end:
            raise ValueError("Chord landmarks must lie within the melody performance")
        if any(label not in by_label for _, label in brief.cambios):
            raise ValueError(f"Unsupported chord label; choose from {list(by_label)}")
        stops = [tick for tick, _ in brief.cambios[1:]] + [end]
        plan = [(tick, stop, by_label[label]) for (tick, label), stop in zip(brief.cambios, stops)]
    warnings = []
    if brief.perfil_armonico not in ("automatico", "reposado") and brief.repetir_armonia:
        warnings.append("El perfil armónico evolutivo permite rearmonizar motivos repetidos.")
    if brief.cambios and brief.perfil_armonico != "automatico":
        warnings.append("Los acordes explícitos tienen prioridad sobre el perfil armónico.")
    if brief.actividad > 1 and brief.ritmo_armonico == "libre":
        warnings.append("La actividad subdivide los segmentos armónicos; no estima un pulso del tarareo.")
    if brief.tonic is None:
        warnings.append("Key inferred; confirm it. Profile scores are not confidence probabilities.")
    if brief.beat_ticks is None:
        if brief.patron != "sostenido":
            warnings.append("Grid uses MIDI PPQ; transcription at 120 BPM does not prove the performed tempo.")
    outside = sorted({n.pitch % 12 for n in notes} - {(tonic + p) % 12 for p in SCALES[mode]})
    if outside:
        warnings.append(f"Melody has pitch classes outside the selected scale: {outside}; preserved, not corrected.")
    if brief.downbeat >= end:
        warnings.append("Downbeat is after the melody; only a pickup segment was harmonized.")
    return plan, {"key": {"tonic": tonic, "mode": mode}, "key_candidates": candidates[:3],
                  "warnings": warnings, "beat_ticks": beat, "repeated_motif": motif}


def _voicings(chord, brief):
    lo, hi = {"grave": (36, 59), "medio": (48, 71), "agudo": (60, 83)}[brief.registro]
    pitches = [p for p in range(lo, hi+1) if p % 12 in chord.pcs]
    if brief.voces == 1:
        return [(p,) for p in pitches if p % 12 == chord.root]
    result = []
    for v in combinations(pitches, brief.voces):
        if len(set(p % 12 for p in v)) < min(3, brief.voces):
            continue
        if brief.disposicion == "cerrada" and v[-1] - v[0] > 12:
            continue
        if brief.disposicion == "abierta" and v[-1] - v[0] < 12:
            continue
        # Avoid close low-register clusters.
        if any(a < 48 and b-a < 5 for a, b in zip(v, v[1:])):
            continue
        result.append(v)
    if not result:
        raise ValueError("No voicing satisfies the requested range/spacing/voice count")
    return result


def expressive_velocity(brief, tick, start, end, role="harmony", accent=0):
    x = max(0.0, min(1.0, (tick-start)/max(1, end-start)))
    delta = {"estable": 0, "crescendo": -12+24*x,
             "diminuendo": 12-24*x, "arco": -10+24*(1-abs(2*x-1))}[brief.curva_dinamica]
    balance = {"harmony": 0, "bass": brief.balance_bajo, "response": brief.balance_respuesta}[role]
    return max(1, min(127, round(brief.intensidad+balance+delta+accent)))


def articulated_end(start, end, articulation):
    fraction = {"original": 1.0, "legato": 1.0, "normal": 0.8, "staccato": 0.45}[articulation]
    return min(end, start+max(1, round((end-start)*fraction)))


def expression_controls(brief, start, end, channel):
    """CC11 changes sounding sustained notes as well as subsequent attacks."""
    if brief.curva_dinamica == "estable":
        return []
    controls = []
    previous = None
    for i in range(65):
        x = i/64
        value = round({"crescendo": 76+36*x, "diminuendo": 112-36*x,
                       "arco": 76+36*(1-abs(2*x-1))}[brief.curva_dinamica])
        tick = start+round((end-start)*x)
        if value != previous:
            controls.append((tick, mido.Message('control_change', channel=channel, control=11, value=value)))
        previous = value
    controls.append((end, mido.Message('control_change', channel=channel, control=11, value=127)))
    return controls


def add_controls(track, controls):
    if not controls:
        return track
    events, tick = [], 0
    for message in track:
        tick += message.time
        if message.type != 'end_of_track':
            events.append((tick, 1, message.copy(time=0)))
    events.extend((tick, 0, message.copy(time=0)) for tick, message in controls)
    result, previous = mido.MidiTrack(), 0
    for tick, _, message in sorted(events, key=lambda e: (e[0], e[1])):
        result.append(message.copy(time=tick-previous))
        previous = tick
    return result


def realize(plan, notes, brief, beat, voicing_filter=None):
    """Global DP voice leading, then a repeatable rhythm; no random note sampling."""
    options = [_voicings(chord, brief) for _, _, chord in plan]
    if voicing_filter is not None:
        options = [[v for v in choices if voicing_filter(chord, v)]
                   for (_, _, chord), choices in zip(plan, options)]
        if any(not choices for choices in options):
            raise ValueError("No voicing leaves room for the bass; choose a higher harmony register or closed spacing")
    costs, paths = {}, {}
    center = {"grave": 47, "medio": 57, "agudo": 72}[brief.registro]
    for i, choices in enumerate(options):
        a, b, _ = plan[i]
        sounding = [n.pitch for n in notes if n.start < b and n.end > a]
        next_costs, next_paths = {}, {}
        for v in choices:
            local = abs(statistics.mean(v)-center) * 0.04
            local += sum(0.4 for p in v for n in sounding if abs(p-n) <= 1) / max(1, len(sounding))
            if not i:
                next_costs[v], next_paths[v] = local, [v]
            else:
                def movement(prev):
                    leaps = [abs(x-y) for x, y in zip(prev, v)]
                    return sum(leaps)*0.12 + sum(max(0, d-5)*0.25 for d in leaps)
                best = min(costs, key=lambda prev: costs[prev]+movement(prev))
                next_costs[v] = costs[best]+movement(best)+local
                next_paths[v] = paths[best]+[v]
        costs, paths = next_costs, next_paths
    voicings = paths[min(costs, key=costs.get)]
    result = []
    unit = {"cortas": 0.5, "medias": 1, "largas": 2}[brief.notas] * beat
    spacing = {"poco": 1, "medio": 2, "mucho": 4}[brief.espacio]
    for (start, end, _), voicing in zip(plan, voicings):
        step = max(1, round((end-start)/brief.actividad)) if brief.patron == "sostenido" else max(1, round(unit * spacing/brief.actividad))
        for index, tick in enumerate(range(start, end, step)):
            pitches = (voicing[index % len(voicing)],) if brief.patron == "arpegio" else voicing
            # Never overlap a repeated note with itself when density increases.
            slot_end = min(end, tick+step)
            stop = slot_end if brief.patron == "sostenido" else min(slot_end, tick+max(1, round(unit*0.9)))
            if brief.articulacion != "original":
                stop = articulated_end(tick, slot_end, brief.articulacion)
            for pitch in pitches:
                velocity = expressive_velocity(brief, tick, plan[0][0], plan[-1][1], accent=0 if index == 0 else -10)
                result.append(Note(tick, stop, pitch, velocity, 2))
    return result, voicings


def track_from_notes(notes, program, channel, name="Acompanamiento tonal"):
    track = mido.MidiTrack([mido.MetaMessage("track_name", name=name),
                            mido.Message("program_change", program=program, channel=channel)])
    events = []
    for n in notes:
        events.extend([(n.start, 1, n.pitch, n.velocity), (n.end, 0, n.pitch, 0)])
    previous = 0
    for tick, on, pitch, velocity in sorted(events):
        track.append(mido.Message("note_on" if on else "note_off", note=pitch,
                                  velocity=velocity, channel=channel, time=tick-previous))
        previous = tick
    return track


def accompany(midi, brief=None, melody_channel=0, output_channel=2, voicing_filter=None):
    brief = brief or Brief()
    meters = {(m.numerator, m.denominator) for track in midi.tracks for m in track
              if m.type == "time_signature"}
    if len(meters) > 1 or (meters and meters != {(brief.numerator, brief.denominator)}):
        raise ValueError("Meter changes or a brief inconsistent with MIDI meter are unsupported")
    if output_channel == melody_channel or output_channel == 9 or not 0 <= output_channel < 16:
        raise ValueError("Accompaniment needs a separate non-drum channel")
    notes = read_notes(midi, melody_channel)
    plan, report = plan_harmony(notes, brief, midi.ticks_per_beat)
    generated, voicings = realize(plan, notes, brief, report["beat_ticks"], voicing_filter)
    report["brief"] = asdict(brief)
    report["source_notes"] = len(notes)
    report["generated_notes"] = len(generated)
    report["harmony"] = [{"start_tick": a, "end_tick": b, "roman": chord.label,
                           "pitch_classes": chord.pcs, "voicing": v,
                           "functional_tension": harmonic_tension(chord),
                           "target_tension": tension_target(brief.perfil_armonico,
                               ((a+b)/2-plan[0][0])/max(1, plan[-1][1]-plan[0][0]))}
                          for (a, b, chord), v in zip(plan, voicings)]
    report["limitations"] = ["Diatonic triads plus minor dominant; no modulation or jazz harmony.",
                              "Voice-leading costs are heuristics, not strict counterpoint rules.",
                              "Other accompaniment tracks are not reharmonized or collision-checked."]
    track = track_from_notes(generated, brief.instrumento, output_channel)
    return add_controls(track, expression_controls(brief, plan[0][0], plan[-1][1], output_channel)), report


def summarize(midi, channel=None, limit=256):
    """LLM context with units, durations, channels and metadata; bounded in size."""
    notes = read_notes(midi, channel)
    metadata, tick = [], 0
    for msg in mido.merge_tracks(midi.tracks):
        tick += msg.time
        if msg.type in ("set_tempo", "time_signature", "key_signature"):
            metadata.append({"tick": tick, **{k: v for k, v in msg.dict().items() if k != "time"}})
    ppq = midi.ticks_per_beat
    return {"ticks_per_quarter": ppq, "metadata": metadata, "note_count": len(notes),
            "truncated": len(notes) > limit, "key_candidates": key_candidates(notes)[:3] if notes else [],
            "notes": [{"pitch": n.pitch, "start_quarters": round(n.start/ppq, 5),
                       "duration_quarters": round((n.end-n.start)/ppq, 5),
                       "velocity": n.velocity, "channel": n.channel} for n in notes[:limit]]}
