"""Hardware-free adapter for the existing project's multi-track suggestion UI."""
from copy import deepcopy
from dataclasses import replace

from ensemble import Ensemble, arrange

GENERATED_PREFIX = "Sugerencia IA"


def candidate(project, brief, melody_channel=0, ensemble=None, *, drums="ninguna", guitar=False):
    """Replace only named prior suggestions, reserve the live keyboard channel.

    Returns a preview project without mutating the live/saved project. Accepting
    or rejecting is the UI's responsibility.
    """
    source = deepcopy(project)
    source.tracks = [t for t in source.tracks if not t.name.startswith(GENERATED_PREFIX)]
    ensemble = ensemble or Ensemble()
    reserved = tuple(sorted(set(ensemble.reserved_channels) | {0, 1, 9}))
    result, report = arrange(source, brief, melody_channel,
                             replace(ensemble, reserved_channels=reserved))
    if drums != "ninguna" or guitar:
        from band import perform
        if drums not in ("ninguna", "acentos", "rock", "house"):
            raise ValueError("Patrón de batería desconocido")
        perform(source, result, report, brief, melody_channel, drums, guitar)
        report["interpretacion"] = {"bateria": drums, "rasgueo": guitar}
    for track, part in zip(result.tracks[len(source.tracks):], report["parts"]):
        track.name = f"{GENERATED_PREFIX} - {part['role']}"
    return result, report
