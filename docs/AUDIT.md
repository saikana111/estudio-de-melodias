# Project audit

Audit date: 2026-11-16. Original commit: `2ec208c` (cloned via the requested SSH URL).
Scope: tracked Python application and experiments, ESP32 firmware/protocol, dependency
list, checked-in MIDI examples, and the newly supplied `test/0_melodia_original.mid`.
Findings below describe the original checkout unless marked changed.

## What the project actually does

`main.py` coordinates a Windows computer and ESP32 instrument. The ESP32 scans
two contacts per key to estimate velocity, displays menus, and sends serial button,
key, instrument and control messages. Python records microphone audio; Basic Pitch
transcribes it; music21 guesses a key; the old correction step forces notes into
that scale. Projects store multiple MIDI tracks, identified by MIDI channel.

`gem.py` is the active LLM component, despite older Whisper/Groq/Llama experiments
remaining in `src`. Groq transcribes conversation audio, Gemini holds a global chat
and produces arrangement JSON, ElevenLabs speaks, with edge-tts/gTTS fallbacks.
FluidSynth plays MIDI. `acompanante.py` calls Metacreation MIDI-GPT on CPU. If any
step in the arrangement/model block fails, the old app asks Gemini for chord names
and renders repeated block chords instead. Accepting a suggestion replaces channel 2.

The implementation does not presently compose song sections. It generates one
accompaniment track for an existing project. Instruments, voice count, duration
and silence controls do not constitute an explicit harmonic or formal plan.

## Findings, ordered by impact

| Priority | Evidence | Consequence | Status / action |
|---|---|---|---|
| High | `main.procesar_melodia` unconditionally called `correccion.corregir`; correction overwrites the MIDI | An uncertain key estimate becomes an irreversible musical assertion; chromatic tones can be changed, and adjacent pitches may collapse onto one pitch | Default snapping disabled; keep raw audio and raw MIDI as immutable evidence in a future project format |
| High | Original `correccion.midi_txt` included note-on pitch/velocity/channel/absolute ticks only | LLM cannot distinguish short passing tones from held notes, and has no PPQ, meter or tempo context | Replaced with bounded structured note durations, quarter-note units, metadata and key alternatives |
| High | `sugerencia.grilla_de_pulso` uses median onset intervals; `acompanante.mapa_de_tiempo` rounds each interval independently | Melody rhythm is mistaken for beat; tempo can be doubled/halved; syncopation and expressive timing can be warped | New backend supports explicit score timing or free-time harmonic landmarks without rewriting source timing |
| High | LLM chord durations advance along a variable onset-derived grid | “Four beats” may not mean four actual beats; harmonic changes drift relative to phrases | New harmony plan records exact boundaries and keeps realization separate |
| High | No harmonic plan in MIDI-GPT request; only texture attributes; no output quality gate | A request for a bass or sparse chords does not guarantee functional harmony or melodic support | Added inspectable harmonic search and global voicing search; learned output evaluation remains future work |
| High | `main.generar_sugerencia` originally sends all project notes to the LLM and estimates key from the saved whole project | Existing accompaniment, including a previous suggestion, can contaminate interpretation of the selected melody | LLM note context now selects the requested melody channel; the old music21 whole-project key hint still needs replacement |
| Medium | Broad exception catches cover JSON request, API errors and MIDI-GPT generation | A network/schema/implementation failure looks like a musical-model failure; fallback silently changes generator | Tonal route now fails explicitly instead of falling back; legacy MIDI-GPT fallback remains for comparison |
| Medium | Pydantic fields were unbounded ints/plain strings; `json.loads` bypassed local model validation | Invalid instruments, voice counts and labels can reach rendering, or silently fall back to defaults | Added enum/range constraints and local validation; chord fallback bounded too |
| Medium | `notas_de_pista` keys active notes by pitch only | Overlapping same-pitch notes overwrite each other; channels are not separated | New core uses channel+pitch FIFO and diagnoses malformed note pairs; legacy reader still exists |
| Medium | `proyectos.midi_a_pista` rescales PPQ but drops tempo/pitch bends/controllers | General imported MIDI can play at the wrong speed or lose articulation; Basic Pitch's 120 BPM assumption hides this | Standalone path preserves original tracks/tempo map; general importer still needs tempo-aware conversion |
| Medium | Keyboard capture stops without explicitly closing held keys | Saved keyboard tracks can contain hanging notes | New parser rejects this; recording finalization still requires a fix and hardware regression test |
| Medium | Live keyboard and recorded keyboard playback share channel 1 | Playback program changes and note-offs may interfere with live playing | Reserve a separate live synth part or implement independent synth instances |
| Medium | Global chat and `ultimo_arreglo` are not project-scoped or reset on open/new | Intent and rejected choices can leak between projects | Persist explicit project state; not yet refactored |
| Medium | Original requirements omit google-genai, edge-tts, gTTS and pygame despite unconditional imports | Fresh installation cannot reliably start | Added an extra direct-dependency list and minimal isolated core requirements; full app install unverified |
| Medium | `gem` initializes API client and `reproducir` initializes audio at import time; cyclic app imports | Core behavior cannot be imported/tested without credentials/native audio dependencies | New musical core has no such imports; whole-app dependency injection remains future work |
| Medium | Missing SoundFonts, Windows `dsound` driver, fixed COM8 | Deployment is machine-specific; synth loading failure lacks strong validation | Document and add configuration/health checks before hardware release |
| Low | `convertir` did not create its output directory and returned a nonexistent path if generation failed | Confusing downstream errors | Creates directory and raises at the failing stage now |
| Low | Alternate `correccion_nuevo.py` does not flush its final active note; pitch smoothing includes zero-filled silence | Drops final note and may mishandle boundaries | Experimental, unused by main; requires tests before adoption |
| Low | `src/grabar copy.py` has an indentation error; older `IA.py`, `llama.py`, `txt_voz.py` execute work at import time | Repository-wide compile/import checks fail or trigger unintended work | Reported, left as historical experiments; active modules compile |

## MIDI-GPT verification: avoid blaming the wrong thing

Inspected exact `v0.4.2` source (`e8516c2`) and its pinned Symusic `v0.6.0`
(`43ff252`). The polyphony quantile mapping really uses N−1 bins, so the existing
`voces - 1` mapping is not an off-by-one bug. Its writer places initial metadata
in the first musical track; a hypothesized extra conductor-track offset is **not
confirmed and is not the explanation for this version**.

The adapter now reads the logical `Score` track directly, avoiding redundant MIDI
serialization. This is robustness/clarity, not a claimed sound-quality fix. The
adapter still has heuristic timing normalization, private `_analyzer` coupling,
no explicit seed, no post-generation harmonic evaluation and no full neural
regression run in this environment. The model has more controls than the app uses.

## Hardware and concurrency observations

Firmware uses a nonblocking key state machine and a nonblocking serial-line reader;
those are useful foundations. Velocity is a linear transform of contact travel time,
so calibration and the timing impact of display drawing must be measured on hardware.
The serial Python reader also directly calls voice-preview and synth functions:
blocking/erroring operations there can delay key handling. MIDI playback blocks the
main application loop, so queued user actions are processed later. Project mutation
and live recording use shared state with limited synchronization. None of these
physical timing issues has been measured here; they are risks inferred from code.

## Reproducible evidence

- `python -m unittest discover -s tests -v`: 20 core/CLI/ensemble tests, including overlapping
  notes, repeated motifs under rubato, modal harmony, key preservation, PPQ conversion,
  range/polyphony, malformed input, and meter rejection.
- `python scripts/evaluate.py`: 38 repository MIDIs examined on melody channel 0;
  33 usable, five empty selected channels rejected (files 12, 14, 15, 16 and 17 in
  `midi/`). These are not 33 listening-test wins.
- `python scripts/case_study.py`: original source preserved through saved/reloaded
  MIDI; three reviewed alternatives plus automatic free-time accompaniment; WAV previews.
- Active/new Python modules compile. Broad `compileall` still finds the pre-existing
  indentation error in `grabar copy.py`.

No ESP32, microphone/audio-driver test, cloud LLM/TTS call, Basic Pitch inference,
MIDI-GPT checkpoint inference, or blinded listening assessment was performed.
The local environment had no Python on PATH; a workspace-local Python 3.11.9 runtime
and exact Mido/packaging source tags were used after package-host downloads failed.
No changes were pushed or committed upstream.
