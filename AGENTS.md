# AGENTS.md

## Project Shape

- Python 3.12 project managed with `uv` (`.python-version`, `pyproject.toml`, `uv.lock`).
- Reusable analysis code lives in the root module `melody.py`; notebooks import it directly with `from melody import ...`.
- Numbered notebooks are the exploratory workflow: `0_exploration.ipynb`, `1_lead_voice_detection.ipynb`, `2_graphical_analysis.ipynb`, `3_structure_analysis.ipynb`, `4_comparison.ipynb`.
- Committed MIDI fixtures live in `music/`; `README.md` only lists external MIDI sources.
- `plan.md` is useful for project intent, but verify its status notes against `melody.py` and the notebooks before relying on them.

## Commands

- Quick syntax check: `uv run python -m py_compile melody.py`.
- Typecheck: `uv run mypy melody.py`.
- Lint: `uv run ruff check .`; Ruff also checks `.ipynb` files here, so notebook cell import ordering can fail E402.
- There is no pytest/unittest suite or CI config in the repo.

## Analysis Conventions

- `build_rolls` expects a `pretty_midi.PrettyMIDI`-like object and filters drum tracks plus instruments with fewer than `min_notes` notes.
- Piano rolls are 128-row pitch matrices with frames as columns; `pad_rolls` pads shorter rolls with zero columns.
- Beat-aligned windows use frame indexes derived in notebooks, then `compute_highest_per_instrument` reads `roll[:, beat_frames[w]:beat_frames[w + 1]]`.
- `track_lead_voice` intentionally switches lead instruments only after a challenger is higher for `switch_n` consecutive windows; do not replace it with a per-window max unless changing behavior intentionally.
- Melody sequences use `None` for rests; phrase helpers expect phrases as lists of `(beat_index, pitch)` tuples.
