# Melodic Analysis Toolbox

Projekt zaliczeniowy na przedmiot _Muzyka i Biocybernetyka_

## Struktura projektu

```text
.
├── melody.py                 # Główny moduł z funkcjami do analizy melodii i danych MIDI
├── 4_comparison.ipynb        # Notebook porównujący utwory i metryki melodyczne
├── music/                    # Pliki MIDI używane jako dane wejściowe do analiz
├── report/                   # Raport projektu w Typst oraz wygenerowany PDF
│   ├── figures/              # Wykresy i ilustracje używane w raporcie
│   ├── raport.typ            # Źródło raportu
│   ├── raport.pdf            # Wygenerowany raport końcowy
│   └── refs.yml              # Bibliografia / źródła do raportu
├── glossary.md               # Słownik pojęć używanych w projekcie
├── plan.md                   # Plan prac i założenia projektu
├── TODO.md                   # Lista zadań i pomysłów
├── Makefile                  # Polecenia pomocnicze: lint, format, clean, fetch, report, watch
├── pyproject.toml            # Konfiguracja projektu i zależności Pythona
├── uv.lock                   # Zablokowane wersje zależności dla uv
├── README.md                 # Ten plik
├── AGENTS.md                 # Instrukcje dla agentów pracujących w repozytorium
└── CLAUDE.md                 # Wskazówki dla Claude Code
```

## Instalacja

1. Zainstaluj `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Instalacja zależności:

```bash
uv sync
```

3. Uruchom środowisko wirtualne

```bash
source .venv/bin/activate
```

## Development

Projekt korzysta z Makefile do typowych zadań:

- `make lint` — Lintowanie (ruff + mypy --strict)
- `make format` — Formatowanie (ruff)
- `make clean` - Usunięcie plików cache
- `make fetch` - Pobranie potrzebnych fontów do raportu
- `make report` - Kompilacja raportu z typst do PDF
- `make watch` - Kompilacja w watchmode

## Źródła muzyki

- https://bitmidi.com/
- https://vgmusic.com/music/

## Autorzy

Krzysztof Czuba
Piotr Skowroński
