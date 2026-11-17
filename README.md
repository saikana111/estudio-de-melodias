# Instrumento musical IA — accompaniment and melody development

Developed from [alissa21/instrumento-musical-ia](https://github.com/alissa21/instrumento-musical-ia).
The original project history and ESP32 application are retained, alongside the new
deterministic generators, Spanish dashboard, research and reproducible examples.

This checkout contains the original ESP32 application plus a hardware-free,
deterministic accompaniment engine and a short-form composition engine. MIDI is
the primary output; WAV files are optional listening previews.

## Local dashboard (recommended)

Version 0.3.0 adds expressive dynamics/articulation/activity, harmonic trajectories,
section overrides, and real General MIDI playback with FluidSynth + SoundFont.
Run `python scripts/setup_audio.py` once to install the pinned local audio assets.
See [Spanish expression and audio guide](docs/EXPRESION_Y_SONIDO.md).

New rendered examples: [expressive ensemble MIDI](artifacts/v0.3.0/ensamble-expresivo.mid)
and [SoundFont audio](artifacts/v0.3.0/ensamble-expresivo.wav);
[developed piece MIDI](artifacts/v0.3.0/pieza-desarrollada.mid)
and [SoundFont audio](artifacts/v0.3.0/pieza-desarrollada.wav).

Open **`start-studio.cmd`** on Windows, or run `python src/dashboard.py`.
The dashboard opens at **http://127.0.0.1:8765**. On a new machine, first create a
Python environment and install `requirements-core.txt` as described below.

Upload MIDI, confirm its melody channel, choose harmony and instruments, preview
and download the result. **Ensemble is the default. Longer composition is opt-in.**
Settings can be exported/imported and versions compared within the current session.
No cloud service or MIDI-GPT installation is required for this dashboard.
See [dashboard operation and validation](docs/DASHBOARD.md).

## Version 0.2.0 deliverables

- [Ensemble accompaniment MIDI](artifacts/v0.2.0/accompaniment.mid): the original
  melody with coordinated harmony, bass and responses.
- [Developed song MIDI](artifacts/v0.2.0/song.mid): approximately 53 seconds,
  with theme, ornamented variation, contrasting sequence, return and coda.
- Optional previews: [accompaniment WAV](artifacts/v0.2.0/accompaniment.wav)
  and [song WAV](artifacts/v0.2.0/song.wav).

Both preserve the original MIDI tracks. The song adds transformed melodic material
after the original statement. See [implementation and reproduction](docs/SONG.md)
for commands, configuration and limits. This is an explicit compositional grammar,
not a trained general-purpose songwriter.

Start with [the audit](docs/AUDIT.md), [research and decisions](docs/RESEARCH.md),
and [the supplied melody case study](docs/CASE_STUDY.md).
The [ensemble extension](docs/ENSEMBLE.md) documents reproducibility and coordinated
multi-instrument arranging.

## Listen to the supplied melody

Previews use one simple additive synthesizer for comparison, not the application's
General MIDI SoundFonts. They are structural listening aids, not production audio.

| Version | WAV | Editable MIDI |
|---|---|---|
| Original | [Listen](artifacts/original-melody/00-original.wav) | [Source](test/0_melodia_original.mid) |
| E Dorian, reviewed landmarks | [Listen](artifacts/original-melody/01-e-dorian.wav) | [MIDI](artifacts/original-melody/01-e-dorian.mid) |
| E Mixolydian, same landmarks | [Listen](artifacts/original-melody/02-e-mixolydian.wav) | [MIDI](artifacts/original-melody/02-e-mixolydian.mid) |
| B minor alternative | [Listen](artifacts/original-melody/03-b-minor.wav) | [MIDI](artifacts/original-melody/03-b-minor.mid) |
| Automatic free-time harmony, E Dorian hypothesis | [Listen](artifacts/original-melody/05-automatic-free-time.wav) | [MIDI](artifacts/original-melody/05-automatic-free-time.mid) |
| Coordinated bass, strings and flute responses | [Structural preview](artifacts/original-melody/06-ensemble.wav) | [MIDI](artifacts/original-melody/06-ensemble.mid) |

The three reviewed versions have manually selected harmonic landmarks. The last
version chooses its own chord boundaries; its key/mode remains an explicit choice.
Each result has a neighboring `.analysis.json` documenting its decisions.

## Run independently of ESP32/cloud/audio devices

Use Python 3.11 or later in a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-core.txt
.\.venv\Scripts\python -m unittest discover -s tests -v
.\.venv\Scripts\python scripts/evaluate.py
.\.venv\Scripts\python scripts/case_study.py
.\.venv\Scripts\python scripts/reproduce.py
.\.venv\Scripts\python src/compose.py test/0_melodia_original.mid my-result.mid --brief artifacts/original-melody/01-e-dorian.brief.json
```

The CLI now defaults to ensemble generation, preserving original tracks and metadata
and assigning unused channels. Use `--song` for development or `--single` for the
previous single-part mode. It refuses to overwrite existing outputs.
Use `--melody-channel` to select the lead; `--output-channel` applies to `--single`. Time units in
the brief are **ticks of the input MIDI**, not milliseconds. MIDI quarter notes are
not necessarily the musical beat in compound meter.

For automatic free-time accompaniment, use a brief such as:

```json
{
  "tonic": 4,
  "mode": "dorian",
  "instrumento": 0,
  "voces": 3,
  "registro": "grave",
  "disposicion": "abierta",
  "patron": "sostenido",
  "ritmo_armonico": "libre",
  "costo_cambio": 1,
  "repetir_armonia": true
}
```

`tonic` uses pitch classes C=0 through B=11. `mode` accepts major, minor, dorian,
mixolydian. Automatic key guessing only compares major/minor profiles and reports
alternatives; those scores are not probabilities. Larger `costo_cambio` discourages
chord changes. `repetir_armonia` shares decisions across an exact repeated pitch
motif; disable it when a repeated melody should be reharmonized.

For metered recordings use `ritmo_armonico: "compases"`, set meter, downbeat and
optionally `beat_ticks` (ticks per musical quarter note). Default PPQ timing is
appropriate for an already scored MIDI, not proof of a freely sung tempo. The
engine supports constant 3/4, 4/4 and 6/8; it rejects mismatched/changing meters.

## Existing application integration

The original app now defaults to the coordinated ensemble. The equivalent explicit
configuration, with the reviewed example settings, is:

```powershell
$env:ACOMPANAMIENTO_MOTOR = 'ensemble'
$env:ARREGLO_CONFIG = 'examples/automatic-dorian.json'
python src/main.py
```

This route still needs the original ESP32, SoundFonts and cloud credentials because
the existing conversational app imports those services. The standalone CLI does
not. The app's LLM brief controls instrument/voices/texture; `ARREGLO_CONFIG`
optionally overrides it with confirmed musical settings. Accept/reject applies to
the whole generated ensemble, reserving the live keyboard channels. `tonal` remains
available for single-part accompaniment. Longer song generation is exposed through
the dashboard and standalone CLI; the ESP32 menu has no song-form editor.
Set `ACOMPANAMIENTO_MOTOR=midigpt` only to compare the legacy neural path.

Automatic destructive scale-snapping is now off. The legacy behavior can be enabled
with `CORREGIR_ESCALA=1`, but it can alter intentional notes in the transcription.
`GEMINI_MODEL` can override the original model name; cloud availability was not tested.
`requirements-app-extra.txt` lists missing imports found in the original app;
neither it nor the original dependency list is a newly validated full lockfile.

## Validation scope

44 tests currently pass (including three real SoundFont rendering tests), including 48 generation cases across 24 independent
synthetic seeds, HTTP upload/generation, song development, deterministic output,
source preservation, and mocked app accept/reject behavior. Corpus evaluation of
the single-part engine covers 38 existing MIDIs: 33
successes and five empty selected melody channels, explicitly rejected. Saved case
study files preserve the original melody. See `artifacts/corpus-evaluation.json`.

This does not establish a musical quality win. There has been no blinded listening
study, neural-model inference benchmark, fresh audio transcription benchmark, or
physical hardware test. The baseline supports diatonic triads and a minor dominant;
it does not implement jazz extensions, modulation, strict counterpoint, instrument
fingering, or analysis of every existing accompaniment part.
