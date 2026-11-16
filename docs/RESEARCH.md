# Research and implementation decisions

Reviewed 2026-11-16. This is a task-specific research assessment, not a claim that
one model is universally state of the art. Text-to-MIDI, melody harmonization,
symbolic arrangement and audio accompaniment are different tasks; their published
metrics are not interchangeable. No downloaded neural checkpoint was benchmarked here.

## Recommended architecture

```text
immutable audio + source MIDI
          |
notes with duration / confidence / performance time
          |
reviewable key alternatives + meter/beat evidence + repeated motifs
          |
user intent -> validated arrangement brief
          |
harmonic plan: chord identities AND change locations
          |
voice leading + register + instrument-specific texture
          |
MIDI checks + candidate comparison + listening feedback
          |
accepted arrangement, stored with provenance
```

Keep performance time and score time separate. A transcription exported at 120 BPM
has an encoding clock; it does not necessarily have a trustworthy musical beat map.
Keep the original melody immutable. Use a learned model only at a well-defined stage
where its output can be checked and compared with a deterministic baseline.

## Papers most relevant to this task

| Work | What it contributes | Relevance and evidence limits |
|---|---|---|
| [AccoMontage2, ISMIR 2022](https://archives.ismir.net/ismir2022/paper/000029.pdf) | Separates harmonization from piano texture arrangement; optimizes note-level fit, phrase-template fit and whole-piece connections | Closest architectural match. Its evaluation selected small sets from Nottingham and POP909, with annotated 4/8-bar phrases and restricted meters. That does not establish performance on this unmetered 13-note hum. Borrow the separation and phrase consistency; evaluate the actual system after beat/phrase annotation. |
| [AccoMontage, 2021](https://arxiv.org/abs/2108.11213) | Retrieves accompaniment phrases and transfers them to a supplied lead sheet | Useful once chords are known. It is not itself the missing melody-to-chord stage. A curated, licensed pattern library may improve texture before training a new generator. |
| [AutoHarmonizer, 2024](https://link.springer.com/article/10.1186/s13636-023-00314-6) | Models flexible chord-change rhythm and controllable harmonic density, with a vocabulary of 1,462 chord types | Directly addresses the difference between choosing chords and choosing their timing. Still uses scored temporal representation; it does not solve arbitrary rubato by itself. Authors acknowledge remaining quality limitations. [Code and weights](https://github.com/sander-wood/autoharmonizer) are a concrete next comparison target. |
| [Structure and chord constraints / B*, 2025](https://arxiv.org/pdf/2512.07627) | Combines beam/A*-style search and backtracking to satisfy user-specified chord positions in transformer harmonization | Reinforces that a future chord constraint needs explicit enforcement, not just a prompt. Worst-case exponential search is unsuitable as an unbounded interactive step. Our validated landmark overrides implement the user-facing requirement, not B* itself. |
| [MIDI-LLM, 2025 paper](https://arxiv.org/html/2511.03942v1) and [current implementation](https://github.com/slSeanWU/MIDI-LLM) | Adapts a language model for text-conditioned multitrack MIDI generation | Candidate for style sketches or alternative generation. Text control is not proof of exact source-melody retention. Repository recommends a CUDA GPU with at least 16 GB VRAM. Not a drop-in replacement for this CPU-based accompaniment workflow. |
| [MIDI-SAG, May 2026 revision](https://arxiv.org/html/2602.22029v2) | Uses explicit MIDI, harmonic guidance and structural planning to generate accompaniment audio | Strong support for a modular musical representation. Its output is audio, not editable MIDI notes; preserve that distinction. Timing, harmony and structure remain useful even in a modern learned synthesis system. Relevant later if realistic backing audio becomes a deliverable. |
| [AnyAccomp, 2025](https://arxiv.org/html/2509.14052v1) | Uses a quantized melodic bottleneck to reduce dependence on source-separation artifacts in audio-conditioned accompaniment | Important domain-mismatch warning: clean humming differs from separated studio vocals. It generates accompaniment audio; it is not a replacement for a MIDI arranger. Claims on its own generalization benchmarks need reproduction on this user's recordings. |
| [SongDriver, 2022](https://arxiv.org/abs/2209.06054) | Addresses anticipatory, real-time accompaniment using cached harmonic information | Relevant if live keyboard jamming becomes the objective. The current task has the whole recording available, so offline lookahead is useful and the harder live prediction problem is unnecessary. |

Additional leads found, not deeply reproduced: [encoder-only harmonization,
EAIM 2026](https://openreview.net/pdf?id=tNtRTTQU1h) (full PDF access was blocked by
a browser challenge), and [CPFG-Net perceptual-feature control](https://arxiv.org/abs/2511.14600).
Their abstracts suggest useful approaches to chord locking and expressive control;
that is not enough evidence to recommend replacing the working stack with them.

## Libraries and models: retain, compare, or defer

| Component | Decision | Reason / primary source |
|---|---|---|
| Mido | Retain for interchange and exact event preservation | Small, sufficient dependency for this prototype. Preserve the whole tempo map and all source messages. [Project](https://github.com/mido/mido) |
| music21 | Retain for musical analysis, spelling and richer harmony | Key analysis supplies hypotheses and alternatives, not ground truth. [Key analysis documentation](https://music21.org/music21docs/usersGuide/usersGuide_15_key.html) |
| Basic Pitch | Keep as a measured transcription baseline | Supports polyphonic, instrument-agnostic transcription; its authors say it works best on one instrument at a time. A polyphonic model may still produce extra simultaneous notes on humming. [Official repository](https://github.com/spotify/basic-pitch) |
| pYIN / torchcrepe | Compare for single-voice humming | Retain voiced/unvoiced information and pitch confidence, then segment notes with hysteresis and onset evidence. F0 estimation alone is not note segmentation. Existing `correccion_nuevo.py` is an unfinished pYIN experiment. [librosa maintainer explanation](https://github.com/librosa/librosa/issues/1824), [torchcrepe](https://github.com/maxrmorrison/torchcrepe) |
| Beat This! | Optional beat/downbeat benchmark | Useful for rhythm-bearing recordings; do not assume it can disambiguate a short solo hum. Tapped beats and a count-in offer stronger user-specific evidence. [Official repository](https://github.com/CPJKU/beat_this) |
| MIDI-GPT | Retain as an experimental candidate generator | Provides track conditioning, infilling and richer controls than the app currently uses. Pin model+library version, use public controls where possible, preserve context and score candidates. [Repository](https://github.com/Metacreation-Lab/MIDI-GPT), [models](https://github.com/Metacreation-Lab/MIDI-GPT/blob/main/docs/models.md) |
| MusicLang prediction | Targeted comparison | Chord-conditioned symbolic generation is relevant after an explicit harmonic plan. Evaluate preservation, setup and model/data licensing before adopting. [Official project](https://github.com/MusicLang/musiclang_predict) |
| Text2MIDI | Secondary text-generation baseline | Its central input is descriptive text, so melody-preserving accompaniment needs additional mechanisms and verification. [Official repository](https://github.com/AMAAI-Lab/Text2midi) |
| Symusic / MidiTok | Defer until dataset-scale work | Useful processing/tokenization infrastructure, not harmonization solutions by themselves. [Symusic](https://github.com/Yikai-Liao/symusic), [MidiTok](https://github.com/Natooz/MidiTok) |

## What was implemented from these lessons

The prototype in `src/musical.py` separates a harmonic plan from its voicing and
rhythm. Fixed-meter mode performs dynamic programming over diatonic chord choices.
Experimental free-time mode jointly selects chord identities and boundaries at
source onsets, penalizing excessive changes. Short stepwise resolutions receive
less mismatch cost than unresolved non-chord notes. A simple exact-pitch motif
detector can reuse harmonic decisions across repeated phrases at their respective
performed times. A second dynamic program favors smooth, ordered voicings within
explicit register and spacing limits.

This is a new lightweight heuristic baseline. It does not reproduce the neural
models, training data, template retrieval or published scores of the cited papers.
The current grammar is deliberately limited: major/minor/Dorian/Mixolydian triads,
plus the major dominant in minor. Richer chords should be added with clear roles
for extensions and dissonance resolution, not by blindly permitting all scale notes.

## LLM changes worth making

Do not first replace Gemini with a larger model. Its original input and decision
contract omit essential information; a model upgrade cannot recover missing durations
or a nonexistent beat map. Structured JSON ensures shape, not musical correctness.
Google supports JSON Schema/Pydantic structured output, but application validation
is still necessary. [Official structured-output guide](https://aistudio.google.com/docs/structured-output)

The next conversation contract should return one of `ask_question`, `propose_arrangement`,
`revise_arrangement` or `accept_arrangement`, together with a versioned project brief.
Store accepted and proposed briefs separately; reset or load context per project.
This replaces the current extra yes/no LLM call and avoids remembering a rejected
proposal as if it had been accepted. Keep speech styling independent of composition.

Expose musically actionable controls: role, register, voicing width, texture,
harmonic-change density, tension/resolution, and which region may change. Emotion
words are preferences to explore, not universal mappings such as “sad = minor.”
Where key is ambiguous, let the user compare short alternatives instead of treating
the estimator's top score as a command to modify their melody.

## Evaluation before promoting a new default

Use a held-out set of 15–30 user-owned examples: clean humming, noisy humming,
repeated notes, vibrato, pickups, slow rubato, syncopation, major/minor/modal examples,
and short keyboard motifs. Mark note boundaries and beat/phrase evidence independently.
Do not tune everything to `0_melodia_original.mid`.

Compare (1) original LLM-chord renderer, (2) current MIDI-GPT adapter, (3) deterministic
baseline, (4) constrained/model hybrid. Use the same melody and SoundFont, comparable
levels, seeded sampling where supported, and several candidates per neural condition.

Hard checks: unchanged source events, valid note pairs/ranges, tempo-map preservation,
requested maximum polyphony, explicit chord-lock compliance, channel isolation, latency
and failure rate. Diagnostic metrics: duration-weighted chord-tone compatibility,
voice-leading movement, register collisions, onset-grid error when a reference grid
exists, phrase-repeat consistency and density adherence. Do not maximize chord-tone
ratio blindly: that would punish useful passing tones and suspensions.

Blinded listening should rate melody identity, harmonic fit, timing, expressive fit,
and preference. Record disagreements and the reason for rejection. A high technical
pass rate or a published FAD-style audio score is not proof of a satisfying accompaniment.

## Next engineering order

1. Choose a harmonic interpretation for the supplied melody through listening and
   collect the intended emotional/style direction. Keep the reviewed and automatic
   versions as separate baselines.
2. Add a count-in/tap-tempo option and a small set of editable beat/phrase landmarks.
   Save these alongside raw audio, raw MIDI and accepted arrangement metadata.
3. Benchmark Basic Pitch against a monophonic pitch/segmentation route on those
   recordings; avoid unconditional nearest-scale correction.
4. Add a small licensed texture library (sustained, arpeggio, bass, sparse comping)
   and instrument-specific ranges/playability. The existing generic voicer is not
   a guitar fingering or piano hand-allocation model.
5. Evaluate AutoHarmonizer or AccoMontage2 on well-annotated examples; evaluate
   constrained MIDI-GPT on the same examples. Introduce a model only if listening
   and preservation checks show a useful improvement.
6. Refactor project state, service initialization, playback cancellation and recording
   finalization before integrating more autonomous conversational behavior.

Training a new foundation model is not justified by the available data. A small,
well-tested musical planning/validation library is justified and is what this
prototype starts to provide.
