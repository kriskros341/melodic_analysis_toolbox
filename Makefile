.PHONY: fetch report watch clean

fetch:
	mkdir -p .fonts
	curl -fsSL -o .fonts/FiraMono-Regular.ttf https://github.com/google/fonts/raw/main/ofl/firamono/FiraMono-Regular.ttf
	curl -fsSL -o .fonts/FiraMono-Medium.ttf https://github.com/google/fonts/raw/main/ofl/firamono/FiraMono-Medium.ttf
	curl -fsSL -o .fonts/FiraMono-Bold.ttf https://github.com/google/fonts/raw/main/ofl/firamono/FiraMono-Bold.ttf

report:
	typst compile --font-path .fonts report/raport.typ report/raport.pdf

watch:
	typst watch --font-path .fonts report/raport.typ report/raport.pdf

clean:
	rm -rfv .fonts
