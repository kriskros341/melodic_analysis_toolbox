# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Package Management

- **Install dependencies**: `uv sync` (installs from `uv.lock`)

### Code Quality

- **Lint and typecheck**: `make lint` (runs `ruff check .` and `mypy --strict .`)
- **Format code**: `make format` or `uv run ruff format .`
- **Clean cache/generated local files**: `make clean` (removes `__pycache__`, `.mypy_cache`, `.ruff_cache`, `.fonts`)

### Report

- **Fetch report fonts**: `make fetch` (downloads Fira Mono fonts into `.fonts/`)
- **Build Typst report**: `make report` (compiles `report/raport.typ` to `report/raport.pdf`)
- **Watch Typst report**: `make watch`

## Project

Academic coursework project for _Muzyka & Biocybernetyka_. The project analyzes MIDI files to compare melodic/rhythmic properties and estimate usefulness as a timed auditory stimulus for **Rhythmic Auditory Stimulation (RAS)** / motor entrainment.

The written report and user-facing prose are in Polish. `glossary.md` contains domain terms, and `TODO.md` tracks remaining work.

## Structure

```text
.
├── melody.py                 # Main reusable module for MIDI melody/rhythm analysis
├── 4_comparison.ipynb        # Notebook comparing songs and generating figures
├── music/                    # MIDI fixtures used as analysis input
├── report/                   # Typst report source and generated PDF
│   ├── figures/              # Figures used in the report, generated from the notebook
│   ├── raport.typ            # Typst report source
│   ├── raport.pdf            # Generated final report
│   └── refs.yml              # Hayagriva bibliography
├── glossary.md               # Glossary of domain terms
├── plan.md                   # Project plan and analysis roadmap
├── TODO.md                   # Task list and ideas
├── Makefile                  # Commands for lint, format, clean, fetch, report, watch
├── pyproject.toml            # Project metadata, Python version, dependencies, Ruff config
├── uv.lock                   # Locked dependency versions for uv
├── README.md                 # Project overview and usage notes
├── AGENTS.md                 # Agent instructions and analysis invariants
└── CLAUDE.md                 # This file
```

## Stack

- Python 3.12+
- `uv` for dependency management
- `pretty_midi` for MIDI parsing and piano rolls
- `numpy` / `scipy` for numerical analysis
- `scikit-learn` for vector comparison and visualization support
- `matplotlib` for charts in notebooks/report figures
- Typst + Hayagriva (`report/refs.yml`) for the written report
- No web frameworks; this is a research/analysis project, not an application.

## Code Style

- Reusable analysis code lives in the root module `melody.py`; notebooks import it with `from melody import ...`.
- Use type hints for new functions and keep `mypy --strict` compatibility in mind.
- Follow existing docstring style: Polish explanations for analysis functions, with `Args` / `Returns` sections.
- Keep user-facing prose, report text, comments explaining domain assumptions, and documentation in Polish.
- Prefer small, direct functions over framework-like abstractions; this is a compact analysis toolbox.
- Keep reusable functions path-agnostic. File paths and plotting orchestration belong in notebooks or scripts, not deep inside feature extraction helpers.
- Ruff line length is 120 and import sorting is enabled (`I001`). Ruff also checks notebooks, so notebook import ordering can fail linting.

## Domain Context

Key concepts used throughout the project:

- **MIDI onset**: note start time; onset sequences are used for IOI, pulse clarity, and syncopation.
- **IOI (Inter-Onset Interval)**: time between consecutive note starts; used to measure rhythmic regularity.
- **Beat-aligned window**: analysis window based on MIDI beat positions, not fixed wall-clock seconds.
- **Piano roll**: 128-row pitch matrix with time frames as columns.
- **Lead voice**: extracted melodic line, tracked across instruments with continuity constraints.
- **Pulse clarity**: strength of periodic beat structure, estimated from autocorrelation of the onset envelope.
- **Syncopation**: fraction of onset activity landing on weak metric positions.
- **Form complexity**: structural repetition/contrast estimated with a self-similarity matrix.
- **RAS index**: entrainment suitability score combining cadence fit, pulse clarity, and inverse syncopation.

## Analysis Pipeline

`melody.py` implements one per-track pipeline whose stages span several functions. Read related functions together before changing behavior.

1. **Tempo**: `compute_tempo_features`, then `fold_bpm_to_band` folds BPM by metric octaves. By default it folds high tempi down only, which handles _alla breve_ marches without inflating genuinely slow pieces.
2. **Lead voice**: `build_rolls` -> `pad_rolls` -> `compute_highest_per_instrument` -> `track_lead_voice` extract one melodic line across beat-aligned windows.
3. **Rhythm/form features**: `compute_ioi_features`, `compute_pulse_clarity`, `compute_syncopation`, and `compute_form_complexity` describe rhythmic regularity and structural repetition.
4. **Melodic features**: `compute_contour`, `rle`, and `segment_phrases` describe direction changes, repetition, and phrase grouping.
5. **Aggregation**: `compute_feature_vector` bundles all metrics into a dictionary.
6. **RAS suitability**: `compute_entrainment_suitability` computes a geometric mean of cadence fit, pulse clarity, and `1 - syncopation`; any zero term zeroes the score.

## Important

- Read `AGENTS.md` as the source of truth for project shape, commands, and analysis invariants.
- `build_rolls` expects a `pretty_midi.PrettyMIDI`-like object and filters drum tracks plus instruments with fewer than `min_notes` notes.
- Beat-aligned windows use frame indexes derived in notebooks, then `compute_highest_per_instrument` reads `roll[:, beat_frames[w]:beat_frames[w + 1]]`.
- `track_lead_voice` intentionally switches lead instruments only after a challenger is higher for `switch_n` consecutive windows. Do not replace it with a per-window maximum unless intentionally changing the method.
- Melody sequences use `None` for rests; phrase helpers expect phrases as lists of `(beat_index, pitch)` tuples.
- Report figures in `report/figures/*.png` are generated by executing `4_comparison.ipynb`; regenerate them after changing feature extraction or plotting code.
- Report text should preserve the biocybernetic/RAS framing and stay in Polish.
- Committed MIDI examples live in `music/`; external sources are listed in `README.md`.
- `plan.md` is useful for intent, but verify status notes against `melody.py` and the notebook before relying on them.

## References

- Thaut, Michael H., _Rhythm, Music, and the Brain: Scientific Foundations and Clinical Applications_, 2013.
- Murgia et al., _The Use of Footstep Sounds as Rhythmic Auditory Stimulation for Gait Rehabilitation in Parkinson's Disease_, 2018.
- Natanson, Tadeusz, _Programowanie muzyki terapeutycznej_, 1992.
- Cylulko, Paweł, _Diagnoza i diagnostyka muzykoterapeutyczna_, 1992.
- Pałosz, Paulina, _Przegląd badań nad uwarunkowaniami preferencji muzycznych_, 2009.
