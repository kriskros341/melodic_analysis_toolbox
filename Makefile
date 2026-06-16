.PHONY: fetch report watch slides clean lint format

lint: 
	uv run ruff check .
	uv run mypy --strict .

format:
	uv run ruff format .

fetch:
	mkdir -p .fonts
	curl -fsSL -o .fonts/FiraMono-Regular.ttf https://github.com/google/fonts/raw/main/ofl/firamono/FiraMono-Regular.ttf
	curl -fsSL -o .fonts/FiraMono-Medium.ttf https://github.com/google/fonts/raw/main/ofl/firamono/FiraMono-Medium.ttf
	curl -fsSL -o .fonts/FiraMono-Bold.ttf https://github.com/google/fonts/raw/main/ofl/firamono/FiraMono-Bold.ttf

report:
	typst compile --font-path .fonts report/raport.typ report/raport.pdf

watch:
	typst watch --font-path .fonts report/raport.typ report/raport.pdf

slides:
	typst compile --font-path .fonts report/slajdy.typ report/slajdy.pdf

clean:
	find . \( -type d -name __pycache__ -o -name "*.pyc" -o -type d -name .mypy_cache -o -type d -name .ruff_cache -o -type d -name .fonts \) -prune -exec rm -rfv {} \;
