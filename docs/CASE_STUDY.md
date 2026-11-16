# The supplied melody: 0_melodia_original.mid

The actual MIDI agrees with the user's 13 note-on entries. It has a single track,
480 ticks/quarter, no tempo events and no meter events. Playback uses MIDI's default
500,000 microseconds/quarter (120 BPM). First onset: tick 1907 ≈ 1.986 seconds.
Last note ends at tick 13796 ≈ 14.371 seconds. Those are playback timestamps, not
evidence of the singer's intended tempo. Analysis: `artifacts/original-melody/source-analysis.json`.

Pitch sequence: **B3 E4 F#4 E4 D4 C#4 B3 B3 E4 F#4 E4 D4 C#4** (C4=60 convention).
The six-note motif occurs at note indices 0 and 7; index 6 is an extra B. Durations
vary substantially, and there is a small E/D overlap in the first occurrence.
Neither overlap nor expressive timing is “corrected” by the new accompaniment.

## Why the earlier chord method can sound wrong

The supplied text correctly accumulates MIDI delta times. However, `Tiempo: 3814`
alone has no musical unit without PPQ/tempo, and omitting note-offs hides whether
the E is brief or sustained. The same chord could support one and clash with the
other. A sequence of chord names and integer durations also says nothing about
which note is in the bass, inversions, voice motion, register, spacing, rhythmic
placement, or melodic tension and resolution.

Even the key is ambiguous. This prototype's duration-profile estimator ranks E
major highest (correlation 0.75264), but the melody has D natural and no G/G# to
settle E's minor/major third. E Dorian, E Mixolydian and B minor offer plausible
interpretations; D major is another possible pitch collection. These are musical
hypotheses, not detected truths. Applying the original nearest-scale correction
under E major would move D to D#, altering the idea.

## Comparison versions

1. **E Dorian:** Em → A → Bm → Em → A, using reviewed landmarks at ticks
   1907, 5843, 7852, 8531, 12068. D over A can act as a suspension resolving to C#.
   The ending remains open rather than adding an invented final melody note.
2. **E Mixolydian:** E → A → Bm → E → A at the same landmarks. The accompaniment's
   G# changes the major/minor character without changing the original melody.
3. **B minor:** Bm → Em → A → Bm → Em → A, at ticks 1907, 3814, 5843, 7852,
   10137, 12068. This provides an alternative tonic interpretation.
4. **Automatic E Dorian:** searches chord identities and source-onset boundaries,
   then reuses corresponding harmonic decisions for the detected six-note repeat.
   Current result is Em → A for each motif, with Em under the intervening B.
   Unlike the first three versions, no chord landmarks are hand-specified.

All versions use three spaced voices in a lower register and sustained texture.
The source track is retained exactly; generated note velocities are deliberately
lower than the melody. The WAV synth additionally uses a lower accompaniment gain.
Program changes, CC and pitch bends are not implemented in this preview synth.

## What the automatic experiment adds

The free-time search can hold harmony across multiple melody notes instead of
assuming every onset is a beat or changing chords every fixed four quarters.
It gives shorter stepwise notes resolving to longer chord tones a lower mismatch
cost, penalizes excessive changes, and preserves repeated harmonic decisions.
Voicing is optimized afterward across the complete chord sequence.

These are transparent heuristics, inspired by distinctions in the literature;
this is not a reimplementation or performance reproduction of a published neural
model. The repeated-motif detector matches pitch sequences only and may mistake
repeated material that should be reharmonized. Disable `repetir_armonia` for that
case. The automatic output is a candidate to evaluate, not the declared winner.

## Listening procedure

Compare the original and alternatives at equal playback settings, first using the
WAV previews and then the MIDI with the same SoundFont. Ask whether the melody still
sounds like the intended idea; whether harmonic changes support the phrase; whether
the ending should remain open; and whether the accompaniment is too dense, low or
static. Compare variants blind and record preferences, not just a single score.

After a harmonic interpretation is accepted, add pulse/texture. For this freely
timed recording, tapping beats or marking a small number of downbeats is better
evidence than assuming the 120 BPM MIDI container represents the sung rhythm.
