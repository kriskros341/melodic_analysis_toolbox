# TODO — rozwój pod kątem „Muzyka & Biocybernetyka"

**Cel nadrzędny:** pokazać, że to nie jest „tylko" projekt informatyczny — że
analiza tempa i rytmu wprost łączy się z oddziaływaniem uporządkowanych pobudzeń
audytoryjnych na układ ruchowy człowieka (efekty uczenia się E1–E3).

---

## Priorytet 1 — Rama biocybernetyczna (tempo/rytm → motoryka)

Powiązanie z **tematem 6** (Music Entrainment, Musical Motor Feedback) i
**tematem 9** (Rhythmic Auditory Stimulation for Normalisation of Walking —
autorski projekt B+R prowadzącego, NCBR 2022). Literatura: Thaut 2013,
Murgia i in. 2018.

- [x] **Mapowanie BPM → kadencja chodu (steps/min).** Zrobione: `fold_bpm_to_band`
      w `melody.py` składa tempo metrycznymi oktawami (÷2) do pasma chodu, co usuwa
      artefakt _alla breve_ (marsze raportowane jako 2× tempo). Użyte w
      `4_comparison.ipynb`. Wniosek z analizy: po złożeniu prawie cała playlista
      trafia w pasmo ~77–126 BPM — tempo jest więc warunkiem koniecznym, ale
      niewystarczającym do różnicowania funkcji terapeutycznej.
- [x] **Klasyfikacja playlisty wg pasma kadencji RAS.** Zrobione w
      `4_comparison.ipynb` (sekcja „Przydatność do RAS"): ranking + klasy
      dobry/warunkowy/nieodpowiedni + wykres słupkowy. Bezpośrednia odpowiedź na
      temat 9. Wynik: marsze i stabilne utwory wysoko, _Moonlight_/_Nocturne_ odpadają
      (za wolne dla kadencji chodu).
- [x] **Wskaźnik „pulse clarity" / siły pulsu.** Zrobione: `compute_pulse_clarity`
      w `melody.py` — autokorelacja wygładzonej obwiedni onsetów, wysokość szczytu
      w paśmie pulsu. Użyte w klasteryzacji `4_comparison.ipynb`; różnicuje materiał
      regularny (Moonlight 0.89, Canon 0.87) od metrum nieparzystego (Take Five 0.34).
- [x] **Złożony wskaźnik „entrainment suitability".** Zrobione:
      `compute_entrainment_suitability` w `melody.py` — średnia geometryczna trzech
      warunków a priori (dopasowanie kadencji + pulse clarity + niska synkopacja),
      w [0,1]. Średnia geometryczna zeruje wynik, gdy którykolwiek warunek zawiedzie.
- [x] **Interpretacja wyników w języku przedmiotu.** Zrobione (sekcja
      „Interpretacja kontrastowych przypadków" w `4_comparison.ipynb`): Stars and
      Stripes (idealny), Moonlight (czysty puls, ale za wolno → 0), Take Five (tempo
      OK, puls za słaby), Gymnopédie (pouczający — wskaźnik mierzy puls, nie pobudzenie).

## Priorytet 2 — Rozbudowa samej analizy

- [x] **Miara synkopacji / „groove".** Zrobione: `compute_syncopation` w
      `melody.py` — udział onsetów na słabych częściach taktu (siatka beatów z
      hierarchią metryczną 2-adyczną). Użyte w klasteryzacji `4_comparison.ipynb`.
- [x] **Klastrowanie playlisty.** Zrobione w `4_comparison.ipynb`: klastrowanie
      aglomeracyjne (Ward) + dendrogram + macierz podobieństwa na podzbiorze 7 cech
      rytmiczno-formalnych. Wynik: nie odtwarza 3 kategorii apriorycznych, ale grupa
      „złożona" się skupia; ujawnia, że „złożoność" jest dwuwymiarowa (rytmiczna vs
      formalna).
- [x] **Złożoność formalna (zmiany sekcji).** Zrobione: `compute_form_complexity`
      w `melody.py` — średnia odległość między oknami w macierzy samopodobieństwa
      (chroma + gęstość + rejestr). Niska dla powtarzalnych groove'ów (Take Five 0.14),
      wysoka dla wielosekcyjnych (Bohemian 0.25) i modulujących (Clair de Lune 0.24).
- [ ] **Wizualizacje pod kątem rytmu.** Wykres tempo vs. pasmo kadencji chodu;
      histogramy IOI per utwór; oś czasu onsetów.

- [ ] Uzupełnić `glossary.md` o pojęcia: entrainment, RAS, kadencja, pulse
      clarity.
