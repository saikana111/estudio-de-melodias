# Reproducibility and a coordinated multi-instrument extension

## Exactly what is reproducible

`scripts/reproduce.py` rebuilds the automatic single-track example twice and compares
both byte streams with the already delivered `05-automatic-free-time.mid`. It also
builds the new ensemble twice and compares their bytes. Both checks pass in the
tested environment. `artifacts/original-melody/reproducibility.json` records source,
brief, implementation and output SHA-256 hashes, Python version and Mido provenance.

There is no RNG, seed, cloud API, LLM, neural checkpoint or hand-edited chord list in
this automatic example. It uses ordinary deterministic search. The brief explicitly
chooses E Dorian, three voices, lower register, open voicing, sustained texture,
free-time harmonic search and change cost 1. The source is a fixture, not hardcoded
into the generic engine. `examples/automatic-dorian.json` exposes these choices.

This establishes repeatability, not universal musical quality. It also does not
establish cross-platform/version byte equality. The local Mido source was checked
out at tag 1.3.3, commit `7313549206d95ab8e14d24f91b502fac0264a8e2`; its uninstalled
source-tree version string reports `0.0.0.dev0`, hence the separate revision field.

```powershell
python scripts/reproduce.py
python src/compose.py test/0_melodia_original.mid ensemble.mid --brief examples/automatic-dorian.json --ensemble chamber
```

## Implemented ensemble prototype

`src/ensemble.py` creates a new MIDI containing the unchanged source plus:

| Role | GM program (zero-based) | Musical behavior |
|---|---|---|
| Strings | 48 | Voice-led realization of the shared chord plan |
| Contrabass | 43 | Chord roots in a low register, at least five semitones below the lowest string voice |
| Flute responses | 73 | Short two-note contour responses only inside sufficiently long melody rests; pitches projected onto the preceding harmony |

The last part is omitted if no suitable rests exist. Responses are skipped if a
harmonic boundary falls inside the rest. All generated parts receive unused MIDI
channels. The source object and its original tracks/metadata remain unchanged.
Instrumentation can be changed through the `Ensemble` API or CLI
`--ensemble-config examples/chamber.json`. Bass-compatible harmony is selected
during voicing search, rather than adjusting the bass after an incompatible choice.
The existing application also supports `ACOMPANAMIENTO_MOTOR=ensemble` with whole
group preview, acceptance and replacement.

The ensemble shares harmony; it does not run three independent chord generators.
It enforces bass/string separation and keeps flute responses out of the melody.
It does not enforce every counterpoint rule or instrument-specific articulation.
Existing accompaniment tracks remain present but are not reconciled with the new
arrangement. For a clean comparison, use a melody-only source.

Listen: [structural preview](../artifacts/original-melody/06-ensemble.wav).
Edit/render with a SoundFont: [multitrack MIDI](../artifacts/original-melody/06-ensemble.mid).
The preview synth deliberately uses a common simple timbre, so it demonstrates note
relationships and timing, not realistic strings/bass/flute sounds. The MIDI contains
the actual distinct program selections.

## Where theory should live

Use hard constraints for requirements that must hold: melody preservation, valid
timing, instrument ranges, maximum simultaneous voices, designated chord landmarks,
channel separation and “answer only during rests.” Use soft costs for preferences:
smooth voice leading, harmonic tension/resolution, rhythmic sparsity, phrase reuse,
cadential strength and avoiding unnecessary doubling. Musical traditions differ;
parallel fifths, dissonance and chromaticism should not become universal bans.

Above those decisions, an arrangement plan assigns roles and entrances across
phrases. Below them, patterns or learned models realize playable parts. The LLM
can translate requests into this plan and explain alternatives. Supplying theory
text to an LLM may help its planning, but only executable constraints and checks
can enforce exact invariants.

## Additional research for multiple instruments

- [Structured Multi-Track Accompaniment Arrangement, NeurIPS 2024](https://arxiv.org/html/2310.16334v3)
  separates piano arrangement from orchestration style. Its explicit limitation
  section excludes triple meters, triplets and drums, and omits expressive timing,
  velocity and controllers. That makes it a promising arrangement reference but
  not an automatic solution to this rubato input. [Official demos, code and Colab](https://zhaojw1998.github.io/structured-arrangement/).
- [GETMusic](https://github.com/microsoft/muzic/blob/main/getmusic/README.md) is a
  concrete open-source benchmark for generating tracks conditioned on existing
  ones. Supported program families are limited; the authors recommend incremental
  generation for multiple tracks and do not release their training data. Preserve
  the original melody outside any normalization round trip and verify the adapter.
  The Muzic repository was archived on 2026-10-01 and its setup specifies older
  Torch/CUDA versions, so treat it as a research baseline with integration work,
  not a maintained plug-and-play production dependency.
- [Unifying Symbolic Music Arrangement, NeurIPS 2025](https://arxiv.org/html/2408.15176v5)
  models arrangement as content-conditioned track reconstruction and introduces
  track-oriented REMI-z tokenization. Relevant to additive generation and role-aware
  arrangement; its benchmark results are not evidence of preserved raw MIDI events
  for our case.
- [ViTex, 2026](https://arxiv.org/abs/2603.01984) combines chord conditioning with
  explicit instrument/texture control for eight-measure multitrack output. Useful
  for thinking about a user interface that specifies instrument roles and density,
  rather than only an emotion adjective. Not benchmarked or integrated here.

These are comparison candidates; none of their checkpoints has been run here.
The small deterministic ensemble is a reference against which to test them, not a
claim to match their learned orchestration quality.

## What remains between this and a full composition

Accompaniment mode arranges the existing passage at its existing length. Version
0.2.0 also implements a [section planner and motif development engine](SONG.md):
theme, variation, contrast, return and coda, with coordinated accompaniment for
each section. The supplied melody produces a roughly 53-second miniature.

The theme remains exact; later sections intentionally transform its material.
This is offline composition. Richer bridges, learned orchestration, expressive
performance and broader song forms remain future work; a deterministic grammar
does not by itself establish convincing musical quality across arbitrary inputs.
