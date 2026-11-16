"""Read a MIDI-GPT Score track without relying on serialized MIDI track indices."""


def score_track_notes(score, index, target_ppq):
    track = score.tracks[index]
    scale = target_ppq / score.resolution
    offset = 0.0
    result = []
    for bar in track.bars:
        for note in bar.notes:
            start = round((offset + note.onset_ticks) * scale)
            end = round((offset + note.onset_ticks + note.duration_ticks) * scale)
            if note.duration_ticks > 0:
                result.append((start, max(start+1, end), note.pitch, note.velocity))
        offset += bar.beat_length * score.resolution
    return sorted(result)
