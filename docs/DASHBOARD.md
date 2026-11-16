# Local Melody Studio

The dashboard is presented in Spanish (including controls, status, key suggestions
and musical warnings). Configuration identifiers and technical JSON remain stable.
See [integration notes in Spanish](INTEGRACION.md) for the optional dashboard and
the existing ESP32/host-Python processing path.

Start with `start-studio.cmd` (Windows), `./start-studio.ps1` (PowerShell), or
`python src/dashboard.py`. A normal installation needs Python 3.11+ and
`pip install -r requirements-core.txt`. The Windows launcher finds the project venv,
then this workspace's portable Python, then Python on PATH.

The server binds only to `127.0.0.1`, defaults to port 8765, and opens the browser.
Use `--port 8766` for a different port or `--no-browser` to print the URL without
opening it. Stop with Ctrl+C in its terminal. This is a local application, not an
Internet-facing deployment. It uses no external assets, APIs or cloud credentials.

## Workflow

1. Upload a `.mid`/`.midi` file or try the supplied example.
2. Confirm the melody channel. The initial suggestion is the channel with most
   notes, not a semantic melody detector. UI channels are numbered 1–16; JSON uses 0–15.
3. Choose tonal center/mode, texture, voicing/register, voice count, instrument roles,
   harmonic rhythm and change resistance. Automatic key selection compares major
   and minor profiles. Dorian/Mixolydian require an explicit tonic. A fresh upload
   resets the tonal center to automatic; the example button explicitly applies the
   reviewed E Dorian settings.
4. Generate the default ensemble, or explicitly select longer composition. Song
   mode exposes full and short forms and contrast pace.
5. Compare versions and preview the source/result. Download MIDI, the decision
   report and reusable settings. Session versions are held in browser memory:
   download before closing or refreshing. Uploaded files are not stored on disk.

The browser synth honors note timing/tempo and velocity. It does not reproduce GM
instrument timbres, sustain/controller state or pitch bends. The actual MIDI retains
source events and contains the selected program changes for use in a DAW.

## Architecture and previous workflow

The original hardware app relied on Gemini briefs and MIDI-GPT, with a chord-based
fallback. The first deterministic improvements were exposed as Python APIs and CLI
commands; `case_study.py`, `reproduce.py` and `build_examples.py` are reproducible
experiments, not the intended everyday UI.

The dashboard uses `generation.generate` for both modes. That service validates
input/configuration, selects the requested lead channel, inherits source meter and
calls the same `ensemble.arrange` / `song.develop` engines used by the fixtures.
There is no special melody-specific generation branch. The example is just a file
and an explicit configuration. `delivery.save_bundle` produces the downloadable
MIDI and provenance report. `preview_notes` converts timing to seconds for playback.

Ensemble is now the default in the dashboard, CLI and ESP32 app. Longer composition
requires a deliberate UI selection or CLI `--song`. The legacy single-track CLI is
available with `--single`; MIDI-GPT remains opt-in in the hardware app.

## Reuse and compatibility tests

```powershell
python -m unittest discover -s tests -v
python scripts/validate_generation.py path/to/midi-folder --output ensemble-check.json
python scripts/validate_generation.py path/to/midi-folder --song --output song-check.json
```

The report separates supported files, explicit unsupported inputs, and unexpected
errors. Choose a new report filename on each run. These checks use the dashboard
service, not a separate simplified generator.

Current checks: 34 tests pass, including 48 generation cases from 24 independent
synthetic melodies spanning all 12 tonic classes, four modes, three meters,
four PPQ resolutions, nonzero lead channels, varied durations, rests and velocities.
The tests round-trip generated MIDI and verify original tracks remain exact.
HTTP checks cover page delivery, MIDI inspection, generation/download payload and
rejection of cross-origin requests. JavaScript passes Node syntax validation.

On the repository's `midi/` directory, ensemble succeeds for 18 of 23 files;
five contain no pitched notes. Song succeeds for 12 of 23, with 11 explicitly
unsupported inputs and no unexpected failures. See
`artifacts/dashboard-corpus.json` and `artifacts/dashboard-song-corpus.json`.
This demonstrates structural compatibility, not good-sounding results on every
melody. No browser automation surface was available in this environment, so visual
layout and audio interaction have not been verified in a real browser here.

## Deliberate limits

Uploads: 2 MB, 4096 total pitched notes, ten minutes, synchronous PPQ MIDI.
Generation: up to 256 selected melody notes; song mode further requires 4–64,
constant tempo, one lead instrument and no other pitched parts/drums. Both engines
support constant 3/4, 4/4 or 6/8. Malformed/hanging notes and unsupported inputs
produce visible errors rather than silent repairs. Ensemble retains existing
other parts but does not reconcile their harmony; start with melody-only MIDI when
possible. Instrument selection changes GM programs, not instrument-specific fingering.
One generation runs at a time. These bounds keep the local prototype manageable;
they do not imply support for arbitrary complete multitrack scores.
