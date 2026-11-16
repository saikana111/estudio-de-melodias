# MIDI-first accompaniment and composition, version 0.2.0

The reusable implementation is in `src/musical.py` (harmonic and voicing search),
`src/ensemble.py` (shared harmony across instruments), and `src/song.py` (form and
melodic development). It requires Mido, without a cloud key, checkpoint or ESP32.

## Generate editable MIDI

Run from the repository root after installing `requirements-core.txt`:

```powershell
python src/compose.py test/0_melodia_original.mid accompaniment.mid --brief examples/automatic-dorian.json --ensemble chamber --ensemble-config examples/chamber.json
python src/compose.py test/0_melodia_original.mid song.mid --brief examples/automatic-dorian.json --song --song-config examples/song.json --ensemble-config examples/chamber.json
```

Each command creates a MIDI and neighboring `.analysis.json`. Existing output files
are never overwritten. The report records settings, harmonic decisions, warnings,
source/output SHA-256 hashes, implementation hashes and Python/Mido versions.
MIDI tracks contain separate instrument programs and can be edited or rendered
in a DAW. GM programs are zero-based: strings 48, contrabass 43 and flute 73.

Rebuild both supplied examples, optionally with simple WAV previews:

```powershell
python scripts/build_examples.py --output-dir artifacts/my-rebuild --preview
python -m unittest discover -s tests -v
```

Use a new output directory. There is no random sampling; identical inputs/settings
in the tested environment produce identical MIDI bytes. Cross-version byte equality
is not promised. The local Mido checkout uses tag 1.3.3, commit
`7313549206d95ab8e14d24f91b502fac0264a8e2`; its source-tree version string is
`0.0.0.dev0`. The pinned normal installation is Mido 1.3.3.

## How the longer piece develops the source

| Section | Implemented operation |
|---|---|
| Theme | Exact original tracks and the same accompaniment engine as the standalone ensemble |
| Variation | Upper-neighbor ornaments on sufficiently long tonic notes, with flute responses omitted |
| Contrast | Repeated source motif sequenced by scale degrees, with configurable proportional timing |
| Return | Original pitches and relative timing, with a small velocity increase |
| Coda | New scale-degree 5–2–1 close over dominant and tonic harmony, ending on a held tonic |

For the supplied recording, the result is about 53.2 seconds rather than 14.4.
The six-note repeated motif informs the contrast. E Dorian is an explicit hypothesis
in the example brief, not an automatic certainty. No original note is scale-snapped.
New sections are harmonized separately, then assigned consistent instrument channels.
Markers in the MIDI identify the form. Short breathing spaces separate sections.

`examples/song.json` controls section order, diatonic contrast displacement,
contrast duration ratio and breathing space. Forms contain 2–8 sections, begin with
`theme`, end with `coda`, and use `variation`, `contrast` or `return` in between.
`examples/chamber.json` controls programs and whether responses are enabled.

## API and app integration

With `src` on the Python import path:

```python
import mido
from musical import Brief
from ensemble import Ensemble, arrange
from song import Song, develop

source = mido.MidiFile("melody.mid")
brief = Brief(tonic=4, mode="dorian", patron="sostenido", ritmo_armonico="libre")
accompanied, analysis = arrange(source, brief, ensemble=Ensemble())
extended, song_analysis = develop(source, brief, ensemble=Ensemble(), song=Song())
extended.save("extended.mid")
```

Both APIs return a new MIDI without mutating the source. Use `delivery.save_bundle`
instead of `.save()` when provenance and non-overwriting writes are required.
`project_arrangement.candidate` adapts the ensemble to the original app: reserve
keyboard channels, replace prior generated tracks as a group, and leave the project
unchanged until the existing acceptance interaction confirms the preview.

## Current scope and evidence

Thirty offline tests pass. Tests cover exact seed preservation, matching theme
accompaniment, deterministic generation, return timing, cadence resolution,
instrument/channel separation, file protection, and mocked app acceptance/rejection.
The delivered MIDIs have also been reloaded and checked against the original tracks.
These checks establish implementation properties, not perceptual musical quality.

Song mode accepts a 4–64-note melody-only seed with constant tempo/meter and one
lead instrument. It rejects preexisting accompaniment and absolute chord landmarks.
It preserves the source performance in the theme; later sections transform notes,
not controller/pitch-bend expression. Accompaniment mode can preserve variable tempo.
The sample lacks tempo metadata; its MIDI default is a playback mapping, not proof
that the singer followed a 120 BPM pulse.

This first composition grammar does not implement modulation, sophisticated bridges,
strict counterpoint or learned orchestration. A variation can remain unchanged if
the source has no suitable held tonic notes. WAV previews use a common additive
timbre and do not demonstrate the MIDI's actual GM instruments. The cloud, physical
hardware and full SoundFont application path have not been tested here.
