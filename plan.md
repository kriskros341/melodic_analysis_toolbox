# Melodic Analysis Pipeline — Plan

## Goal
Compare melodic complexity and style across game MIDI soundtracks.
Output: per-song feature vectors + similarity matrix.

---

## Phase 1 — Fix Foundations

### 1.1 Continuity-based lead voice tracker
- Per time window, compute highest active pitch per non-drum instrument
- Score instruments by recency: prefer the instrument that led in the previous window
- Only switch lead instrument when another has been consistently higher for N windows
- Replaces the broken "select once globally" approach

### 1.2 Beat-aligned windows
- Use MIDI tempo map to align analysis windows to beats (or half-beats), not fixed 0.5s
- Musically meaningful — patterns repeat on metric grid, not clock grid
- `pretty_midi` exposes `get_beats()` for this

---

## Phase 2 — Missing Melody Fundamentals

### 2.1 Key / tonality detection
- Build pitch class histogram from melody notes
- Match against major/minor/modal templates (Krumhansl-Schmuckler or simple correlation)
- Output: detected key + mode

### 2.2 Pitch class histogram
- Distribution across 12 pitch classes (transposition-invariant)
- Comparable across songs regardless of key

### 2.3 Contour analysis
- Classify each interval as: step up, step down, leap up, leap down, repeat (0)
  - Step = 1–2 semitones, Leap = 3+
- Metrics: step/leap ratio, direction change rate, overall contour shape

---

## Phase 3 — Phrase Structure

### 3.1 Phrase segmentation
- Detect phrase boundaries via rests (silence > threshold) and long notes
- Store melody as list of phrases, not one flat sequence
- Fix n-gram analysis to not span phrase boundaries

### 3.2 Motif detection
- Find recurring short pitch/interval sequences within phrases
- Use interval-based (transposition-invariant) representation
- Rank by frequency and coverage

---

## Phase 4 — Cross-Song Comparison

### 4.1 Feature vector per song
Package all metrics into one dict per MIDI file:
- Interval entropy
- Melodic redundancy (RLE ratio)
- Step/leap ratio
- Pitch range (semitones)
- Average phrase length (beats)
- Pitch class histogram (12 values)
- Top 3 most common intervals
- Top 3 most common 3-grams (interval-based)

### 4.2 Similarity matrix
- Cosine similarity between feature vectors for all song pairs
- Heatmap visualization
- Answer: which songs are melodically closest?

---

## Current State of `0_exploration.ipynb`

| Component | Status |
|---|---|
| Track selection (highest avg pitch) | Done but result unused |
| Piano roll (all instruments mixed) | Done — needs lead voice tracker |
| Highest pitch per window | Done — needs beat alignment |
| RLE compression | Done — None handling bug |
| N-gram analysis (pitch + interval) | Done — spans phrase boundaries |
| Interval entropy | Done |
| Melodic redundancy metric | Done |
| Key detection | Missing |
| Contour analysis | Missing |
| Phrase segmentation | Missing |
| Feature vector / comparison | Missing |

---

## Files to Analyze
- `open.mid`
- `aoe_open.mid`
- `atetkali.mid`
- `Battlefield_2_Menu_Music.mid`
- `d64title.mid`
- `Phazonruler_-_Sm4sh_Menu.mid`
- `ps3_lbp_sm01.mid`
- `StatsScreen.mid`

---

## Open Questions
- Should phrase segmentation use rests only, or also harmonic cadence detection?
- Is Krumhansl-Schmuckler key detection worth the complexity, or is simple histogram correlation enough?
- Should the similarity matrix use raw feature values or normalize per-feature first?
