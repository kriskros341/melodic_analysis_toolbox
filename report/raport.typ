#import "@preview/ilm:2.0.0": *

#set text(lang: "pl")

#show: ilm.with(
  raw-text: (font: "Fira Mono", size: 9pt),
  title: [Automatyczna analiza melodyczno-rytmiczna playlisty MIDI w kontekście rytmicznej stymulacji słuchowej],
  authors: ("Krzysztof Czuba", "Piotr Skowroński"),
  date: datetime(year: 2026, month: 6, day: 17),
  date-format: "[day] czerwca [year repr:full]",
  abstract: [
    Praca pokazuje, jak z plików MIDI automatycznie wyznaczyć cechy
    melodyczno-rytmiczne i wykorzystać je do oceny muzyki jako bodźca rytmicznego.
    Analizujemy 15 utworów, wstępnie podzielonych na trzy grupy: RAS (chód),
    relaksacja i muzyka złożona. Dla każdego utworu mierzymy tempo, regularność
    onsetów, wyrazistość pulsu, synkopację i złożoność formy. Cech tych używamy
    dwojako: do grupowania utworów (sprawdzamy, czy obiektywne parametry odtwarzają
    nasz wstępny podział) oraz do wskaźnika przydatności utworu jako bodźca
    _Rhythmic Auditory Stimulation_ (RAS). Otrzymujemy trzy wnioski. Tempo jest
    warunkiem koniecznym, ale niewystarczającym. Wyrazistość pulsu jest wiązana
    ze zdolnością do synchronizacji ruchu. „Złożoność" zaś rozpada się na dwie
    osobne osie: rytmiczną i formalną. Pracę traktujemy jako prototyp metody i jawnie
    nazywamy jej ograniczenia: uproszczenia zapisu MIDI i małą próbę.
  ],
  bibliography: bibliography("refs.yml", style: "ieee"),
  appendix: (
    enabled: true,
    title: [Załącznik: kluczowe funkcje modułu `melody.py`],
    body: [
      #table(
        columns: 2,
        align: (left, left),
        stroke: 0.5pt + luma(180),
        table.header([*Funkcja*], [*Rola*]),
        [`track_lead_voice`], [Śledzenie głównego głosu melodycznego z ciągłością w czasie.],
        [`fold_bpm_to_band`], [Składanie tempa metrycznymi oktawami do pasma kadencji.],
        [`compute_pulse_clarity`], [Wyrazistość pulsu z autokorelacji obwiedni onsetów.],
        [`compute_syncopation`], [Udział onsetów na słabych częściach taktu (hierarchia metryczna).],
        [`compute_form_complexity`], [Złożoność formalna z macierzy samopodobieństwa okien.],
        [`compute_ioi_features`], [Regularność odstępów międzyonsetowych (`ioi_cv`, `ioi_entropy`).],
        [`compute_entrainment_suitability`], [Złożony wskaźnik przydatności do RAS (średnia geometryczna).],
        [`compute_feature_vector`], [Agregacja wszystkich cech utworu do wspólnego słownika.],
      )
    ],
  ),
  // Adjust those if needed
  figure-index: (enabled: false),
  table-index: (enabled: false),
  listing-index: (enabled: false),
)

= Wprowadzenie i cel

Muzyka może być traktowana jako uporządkowany bodziec czasowy: sekwencja zdarzeń
dźwiękowych o mierzalnym tempie, rytmie, regularności i strukturze pulsu. W takim
ujęciu szczególnie interesujące są zastosowania, w których parametry muzyki mogą
wspierać synchronizację ruchu, regulację pobudzenia lub projektowanie
powtarzalnego bodźca terapeutycznego.

Celem niniejszego opracowania jest sprawdzenie, czy z plików MIDI da się
automatycznie wydobyć cechy, które mają sens interpretacyjny w kontekście
*muzycznego porywania* (_music entrainment_) i *rytmicznej stymulacji słuchowej*
(_Rhythmic Auditory Stimulation_, RAS): tempo, regularność onsetów, wyrazistość
pulsu, synkopację oraz złożoność formalną.

Praca ma charakter prototypu metody: łączy ekstrakcję cech z symbolicznej
reprezentacji MIDI, porównanie utworów w przestrzeni cech oraz prosty wskaźnik
przydatności do RAS. Nie próbuje oceniać wartości artystycznej utworów ani
formułować zaleceń klinicznych.

= Tło teoretyczne

*Muzyczne porywanie (entrainment).* Zdolność układu nerwowo-mięśniowego do
synchronizacji z zewnętrznym, periodycznym bodźcem rytmicznym jest dobrze
udokumentowana. Według Thauta @thaut2013 rytm działa jak zewnętrzny zegar, do
którego mimowolnie dostrajają się wzorce ruchowe; mechanizm ten leży u podstaw
neurorehabilitacji ruchu.

*Rytmiczna stymulacja słuchowa (RAS).* W zastosowaniu klinicznym regularny bodziec
słuchowy poprawia parametry chodu u pacjentów z deficytami motorycznymi. Murgia i
współautorzy @murgia2018 wykazali w badaniu z randomizacją, że bodziec rytmiczny
(odgłosy kroków) normalizuje chód w chorobie Parkinsona. Kluczowe dla skuteczności
RAS są: *przewidywalność* i *wyrazistość pulsu* oraz *tempo* możliwe do sprzęgnięcia
z kadencją kroków.

*Programowanie muzyki terapeutycznej.* Natanson @natanson1992 oraz Cylulko
@cylulko1992 podkreślają, że dobór muzyki terapeutycznej nie powinien być
przypadkowy, lecz wynikać z celowego dopasowania parametrów bodźca do funkcji
terapeutycznej. To stanowi bezpośrednie uzasadnienie dla obiektywizacji cech
muzycznych, którą podejmuje niniejsza praca. Szerszy kontekst uwarunkowań odbioru
muzyki omawia Pałosz @palosz2009.

Z powyższego wynika robocza teza pracy: cechy takie jak tempo, regularność
onsetów, wyrazistość pulsu i synkopacja pozwalają obiektywizować potencjał utworu
jako bodźca rytmicznego, niezależnie od subiektywnej oceny jego atrakcyjności.

= Dane i metoda

== Dlaczego MIDI?

MIDI (_Musical Instrument Digital Interface_) nie jest nagraniem audio, lecz
symbolicznym opisem zdarzeń muzycznych: zawiera m.in. wysokości dźwięków, momenty
ich rozpoczęcia, czas trwania, kanały/instrumenty oraz informacje o tempie. Dzięki
temu pozwala analizować strukturę rytmiczną i melodyczną bez wcześniejszej
separacji źródeł z sygnału audio.

Format MIDI wybrano, ponieważ dobrze pasuje do celu pracy: umożliwia bezpośrednie
wyznaczanie onsetów, tempa, przybliżonej melodii prowadzącej i cech formalnych w
sposób powtarzalny dla wielu utworów. Jest to korzystne przy prototypowaniu metody
porównawczej, w której ważniejsza jest spójność reprezentacji niż wierność
pojedynczemu wykonaniu.

Konsekwencją tego wyboru jest ograniczenie interpretacji wyników. MIDI upraszcza
brzmienie, dynamikę i ekspresję wykonawczą, a wiele plików ma sztywne tempo.
Dlatego uzyskane cechy opisują przede wszystkim zapis symboliczny utworu, nie
pełne doświadczenie akustyczne konkretnego nagrania.

== Korpus

Analizie poddano 15 plików MIDI dobranych tak, by reprezentowały trzy *grupy
aprioryczne* o domniemanej różnej funkcji:

- *RAS* - utwory o regularnym pulsie i marszowym lub tanecznym charakterze (Sousa, Strauss,
  Elgar, Survivor, Bee Gees);
- *relaksacja* - utwory wolniejsze, o niższej gęstości zdarzeń (Satie, Debussy,
  Pachelbel, Beethoven, Chopin);
- *złożoność* - utwory o nietypowym metrum lub zmiennej strukturze (Queen, Brubeck,
  Pink Floyd, King Crimson, Radiohead).

Podział ten traktujemy jako *hipotezę do sprawdzenia*: czy obiektywne cechy
odtworzą ten intuicyjny podział funkcjonalny?

Warto zauważyć asymetrię w samych definicjach grup: „RAS" i „relaksacja" określono
*funkcjonalnie* (przez zamierzony efekt bodźca), a „złożoność" *strukturalnie*
(przez budowę utworu). Asymetria jest celowa - pozwala sprawdzić, czy strukturalna
złożoność przekłada się na odrębne, mierzalne cechy. Jak pokażą wyniki, przekłada
się tylko częściowo, bo sama „złożoność" rozpada się na osobne osie rytmiczną i
formalną.

== Pipeline ekstrakcji

Dla każdego pliku: (1) detekcja głównego głosu melodycznego z ciągłością w czasie
(`track_lead_voice`), (2) wyrównanie okien analizy do siatki beatów wyznaczonej z
mapy tempa MIDI, (3) wyznaczenie cech melodycznych i rytmiczno-formalnych. Kod
analityczny zebrano w module `melody.py`, a eksperyment w notatniku
`4_comparison.ipynb`.

== Cechy rytmiczno-formalne

Do opisu bodźca pod kątem RAS wybrano cechy o jasnej interpretacji fizycznej:

- *Tempo złożone do pasma kadencji* (`fold_bpm_to_band`). MIDI zapisuje tempo na
  poziomie ćwierćnuty, więc utwory w metrum _alla breve_ (marsze) mają tempo
  zawyżone dwukrotnie (np. _Stars and Stripes_ ≈ 222 zamiast ≈ 111 BPM). Składamy
  więc tempo o metryczne oktawy (÷2), ale *tylko w dół* - tak usuwamy ten artefakt,
  a zarazem nie zawyżamy utworów naprawdę wolnych. Dzięki temu wartość odpowiada
  realnemu tempu bodźca, w zakresie typowym dla synchronizacji ruchu.
- *Wyrazistość pulsu* (`pulse_clarity`) - wysokość najsilniejszego szczytu
  autokorelacji wygładzonej obwiedni onsetów w paśmie pulsu, znormalizowana do
  energii w zerze. Wartość bliska 1 oznacza wyraźny, regularny puls; niska -
  materiał rubato lub ametryczny.
- *Synkopacja* (`syncopation`) - udział onsetów przypadających na słabe części
  taktu, ważony hierarchią metryczną na siatce beatów; mierzy rytmiczną
  „nieoczywistość".
- *Złożoność formalna* (`form_complexity`) - średnia odległość kosinusowa między
  oknami czasowymi w macierzy samopodobieństwa (profil chroma + gęstość + rejestr).
  Niska dla utworu jednorodnego (jedna sekcja), wysoka dla wielosekcyjnego lub
  modulującego.
- *Regularność odstępów* (`ioi_cv`, `ioi_entropy`) - współczynnik zmienności i
  entropia odstępów międzyonsetowych (IOI).

== Wskaźnik przydatności do RAS

Trzy warunki, które literatura @thaut2013 @murgia2018 wiąże ze skuteczną
synchronizacją ruchu, łączymy w jeden wskaźnik. Używamy *średniej geometrycznej*,
bo wtedy słaby wynik na dowolnym z warunków obniża cały wskaźnik:

$ S = root(3, c dot p dot (1 - s)) $

gdzie $c$ - dopasowanie kadencji (tempo złożone w paśmie ≈ 90–130 kroków/min, z
liniowym spadkiem poza pasmem), $p$ - wyrazistość pulsu, a $(1-s)$ -
przewidywalność (im mniej synkopacji, tym wyższa). Wskaźnik mierzy to, jak łatwo
zsynchronizować ruch z pulsem - nie energię ani pobudzenie.

== Klasteryzacja i uwaga metodologiczna

Cechy standaryzujemy (`StandardScaler`) i grupujemy metodą Warda na trzy klastry.
Używamy przy tym *tylko cech rytmiczno-formalnych*. Świadomie pomijamy
12-elementowy histogram klas wysokości (koduje on tonację): po standaryzacji
zdominowałby odległości i utwory grupowałyby się według tonacji, a nie funkcji.

Ważny wybór: cechy dobraliśmy z góry, na podstawie teorii, a *nie* tak, by klastry
jak najlepiej pasowały do etykiet. Gdybyśmy dostrajali je pod tę jedną 15-utworową
próbę, łatwo byłoby zobaczyć wzór, którego naprawdę nie ma. Dlatego przy tak małej
próbie traktujemy wynik jako prototyp metody, a nie potwierdzony rezultat.

= Wyniki

== Profile cech grup apriorycznych

@fig-radar przedstawia uśrednione, znormalizowane profile cech dla trzech grup.
Grupy różnią się przede wszystkim na osiach pulsu, gęstości onsetów i tempa, lecz
profile częściowo się przenikają - pierwszy sygnał, że podział aprioryczny nie jest
jednowymiarowy.

#figure(
  image("figures/radar.png", width: 68%),
  caption: [Uśrednione profile cech (min-maks) dla grup apriorycznych.],
) <fig-radar>

@tbl-features zestawia kluczowe cechy oraz wskaźnik przydatności do RAS dla całego
korpusu (uszeregowany malejąco wg przydatności).

#figure(
  block(text(size: 8.5pt)[
    #table(
      columns: 8,
      align: (left, center, center, center, center, center, center, left),
      stroke: 0.5pt + luma(180),
      table.header(
        [*Utwór*], [*Kat.*], [*BPM*], [*Puls*], [*Synk.*], [*Forma*], [*Przyd.*], [*Ocena RAS*],
      ),
      [Gymnopédie No. 1], [relaks.], [90], [0.75], [0.01], [0.19], [0.906], [dobry],
      [Stars and Stripes], [RAS], [111], [0.68], [0.22], [0.10], [0.811], [dobry],
      [Bohemian Rhapsody], [złoż.], [103], [0.66], [0.33], [0.25], [0.764], [dobry],
      [Radetzky March], [RAS], [95], [0.47], [0.12], [0.11], [0.745], [dobry],
      [Pomp and Circumstance], [RAS], [90], [0.56], [0.29], [0.19], [0.734], [dobry],
      [Eye of the Tiger], [RAS], [119], [0.59], [0.37], [0.14], [0.720], [dobry],
      [Canon in D], [relaks.], [77], [0.87], [0.27], [0.15], [0.712], [dobry],
      [Stayin' Alive], [RAS], [104], [0.54], [0.43], [0.09], [0.677], [warunkowy],
      [Money], [złoż.], [126], [0.39], [0.29], [0.12], [0.652], [warunkowy],
      [21st Century Schizoid Man], [złoż.], [124], [0.43], [0.41], [0.18], [0.635], [warunkowy],
      [Clair de Lune], [relaks.], [83], [0.52], [0.45], [0.24], [0.606], [warunkowy],
      [Paranoid Android], [złoż.], [77], [0.53], [0.35], [0.20], [0.577], [warunkowy],
      [Take Five], [złoż.], [84], [0.34], [0.30], [0.14], [0.574], [warunkowy],
      [Moonlight Sonata I], [relaks.], [45], [0.89], [0.44], [0.18], [0.291], [nieodpowiedni],
      [Nocturne Op. 9 No. 2], [relaks.], [58], [0.41], [0.40], [0.21], [0.230], [nieodpowiedni],
    )
  ]),
  caption: [Cechy rytmiczno-formalne i wskaźnik przydatności do RAS. BPM -
    tempo złożone do pasma kadencji; Puls - `pulse_clarity`; Synk. - synkopacja;
    Forma - `form_complexity`; Przyd. - wskaźnik $S$.],
) <tbl-features>

== Klasteryzacja: "złożoność" jest dwuwymiarowa

Klastrowanie na siedmiu cechach rytmiczno-formalnych *nie odtwarza* trzech
kategorii apriorycznych (@tbl-conf): każda kategoria rozkłada się na różne klastry.
Struktura nie jest jednak losowa - grupa „złożona" koncentruje się (4 z 5 utworów w
jednym klastrze) i *nie pojawia się* w klastrze materiału o najwyższej regularności
pulsu, ku któremu ciąży relaksacja.

#figure(
  table(
    columns: 4,
    align: (left, center, center, center),
    stroke: 0.5pt + luma(180),
    table.header([*Kategoria aprioryczna*], [*Klaster 0*], [*Klaster 1*], [*Klaster 2*]),
    [RAS], [2], [2], [1],
    [relaksacja], [2], [3], [0],
    [złożoność], [4], [0], [1],
  ),
  caption: [Tabela zgodności: kategorie aprioryczne wobec klastrów algorytmu.],
) <tbl-conf>

Najważniejszy wynik ujawnia cecha `form_complexity`. Okazuje się, że _Take Five_
(forma 0.14) i _Money_ (0.12) mają *niską* złożoność formalną - są to powtarzalne
groove'y (ostinato w 5/4, riff w 7/4), złożone *rytmicznie* (niski `pulse_clarity`),
ale formalnie jednorodne. Wysoką złożoność formalną mają faktycznie wielosekcyjne
_Bohemian Rhapsody_ (0.25) i _Paranoid Android_ (0.20). Co więcej, romantyczne
utwory „relaksacyjne" - _Clair de Lune_ (0.24), _Nocturne_ (0.21) - także wypadają
wysoko, bo modulują i zmieniają fakturę. Wniosek: aprioryczna etykieta „złożona"
*miesza dwa różne zjawiska* - złożoność rytmiczną i formalną. Cecha policzona z
przesłanek teoretycznych, a nie dostrojona pod etykiety, ujawniła strukturę,
której nie zakładano.

Strukturę hierarchiczną i podobieństwa ilustrują @fig-dendro oraz @fig-sim.

#figure(
  image("figures/dendrogram.png", width: 100%),
  caption: [Dendrogram (metoda Warda).],
) <fig-dendro>

#figure(
  image("figures/similarity.png", width: 100%),
  caption: [Podobieństwo (1 − znorm. odl. euklidesowa, cechy standaryzowane).],
) <fig-sim>

== Przydatność do Rhythmic Auditory Stimulation

Wskaźnik $S$ dał ranking utworów jako potencjalnych bodźców RAS (@fig-ras; wartości
w @tbl-features). Progi klas (dobry / warunkowy / nieodpowiedni) są *ilustracyjne*,
nie klinicznymi punktami odcięcia.

#figure(
  image("figures/ras_suitability.png", width: 85%),
  caption: [Ranking przydatności do RAS; kolor oznacza kategorię aprioryczną.
    Linie pionowe - progi ilustracyjne 0,45 i 0,70.],
) <fig-ras>

Wskaźnik dobrze ilustruje, że przydatność do RAS jest *iloczynem* trzech
niezależnych warunków - wystarczy, że jeden zawiedzie, by utwór odpadł. Cztery
przypadki kontrastowe:

- *Stars and Stripes Forever* (≈ 0.81) - _idealny kandydat_. Tempo składa się do
  ≈ 111 BPM (środek pasma kadencji), puls wyrazisty, niska synkopacja. Marszowy
  charakter czyni go przykładem bardzo stabilnego bodźca rytmicznego.
- *Moonlight Sonata* (≈ 0.29) - _odpada mimo czystego pulsu_. Ma najwyższą w korpusie
  wyrazistość pulsu (0.89), lecz tempo 45 BPM leży daleko poniżej przyjętego pasma
  kadencji. Tempo spoza pasma drastycznie obniża wskaźnik (choć go nie zeruje) -
  *tempo pozostaje twardym ograniczeniem*.
- *Take Five* (≈ 0.57) - _tempo dobre, puls za słaby_. Tempo (84 BPM) mieści się w
  paśmie, ale metrum 5/4 daje niski `pulse_clarity` (0.34) - regularna synchronizacja
  z takim pulsem jest trudniejsza. Pokazuje, że *sama kadencja nie wystarcza*.
- *Gymnopédie No. 1* (≈ 0.91, najwyżej) - _przypadek pouczający_. To utwór
  „relaksacyjny", a wypada najlepiej, bo ma regularny puls w paśmie kadencji i
  niemal zerową synkopację. Wskaźnik mierzy *entrainowalność pulsu*, a nie
  pobudzenie - spokojny, miarowy utwór bywa świetnym metronomem.

= Dyskusja

*Tempo jest warunkiem koniecznym, ale niewystarczającym.* Po złożeniu tempa
większość playlisty trafia w zakres ≈ 77–126 BPM - obszar potencjalnie użyteczny
dla synchronizacji ruchu. Samo tempo nie rozdziela jednak funkcji bodźca: muzyka
marszowa, taneczna i spora część materiału „relaksacyjnego" mają podobny puls.

*Wyrazistość pulsu a synchronizacja ruchu.* Wyrazistość pulsu zachowuje się zgodnie
z teorią: jest najwyższa dla utworów o stabilnym, prostym pulsie (_Moonlight_ 0.89,
_Canon_ 0.87), a najniższa dla metrum nieparzystego i zmiennej faktury (_Take Five_
0.34). To właśnie ta cecha - według Thauta @thaut2013 - decyduje o tym, czy ruch da
się zsynchronizować z muzyką.

*Złożoność ma dwie twarze.* Nasz najważniejszy wniosek: złożoność rytmiczna
(nieparzyste metrum, słaby puls) i złożoność formalna (wiele sekcji, modulacje) to
*dwie osobne rzeczy*, a wstępna etykieta „złożona" je myli. Dobrze pokazuje to, po
co dobieraliśmy cechy z góry, a nie pod etykiety: cecha, której nie naginaliśmy do
podziału, ujawniła w danych strukturę, której się nie spodziewaliśmy.

*Mierzalny opis bodźca.* W duchu Natansona @natanson1992 i Cylulki @cylulko1992
praca pokazuje, że świadomy dobór muzyki terapeutycznej wymaga kilku uzupełniających
się, mierzalnych cech. Dopiero wyrazistość pulsu, synkopacja i złożoność formy
dodały do opisu osobne osie: przewidywalność pulsu oraz złożoność rytmiczną i
formalną. Klastrowanie służy tu do sprawdzenia podziału, a nie do potwierdzania go
z góry.

= Ograniczenia

- *Reprezentacja symboliczna.* MIDI nie zawiera sygnału audio ani mikro-timingu
  żywego wykonania. Wyniki dotyczą więc struktury zapisanej w MIDI, nie konkretnego
  nagrania audio. Analiza brzmienia, mikro-timingu i cech widmowych wymagałaby
  renderu MIDI do audio albo pracy bezpośrednio na nagraniach.
- *Mała próba.* N = 15 w przestrzeni 7-wymiarowej oznacza, że struktura klastrów
  jest niestabilna; wynik to prototyp, nie dowód.
- *Heurystyka melodii.* Detekcja głównego głosu opiera się na najwyższym aktywnym
  dźwięku - uproszczenie zawodzące w gęstej fakturze.
- *Subiektywne etykiety.* Podział aprioryczny jest intuicyjny i - jak pokazano -
  niejednorodny (miesza funkcję bodźca ze strukturą utworu); to hipoteza do
  sprawdzenia, a nie „prawda" referencyjna.
- *Brak walidacji na ludziach.* Wskaźnik przydatności do RAS opiera się na
  przesłankach teoretycznych, nie na pomiarze reakcji ruchowej lub fizjologicznej.

= Wnioski i kierunki dalsze

Zbudowano kompletny pipeline obiektywizacji bodźca muzycznego: od ekstrakcji cech
rytmiczno-formalnych, przez klastrowanie testujące podział aprioryczny, po wskaźnik
przydatności do RAS z interpretowalnym uzasadnieniem. Najważniejsze wnioski: tempo
jest konieczne, lecz niewystarczające; wyrazistość pulsu to korelat wiązany w
literaturze z entrainmentem; pojęcie złożoności jest dwuwymiarowe.

Kierunki dalsze, uszeregowane wg stosunku wartości do nakładu:

+ *Tania walidacja* - wskaźnik zgodności klastrów z etykietami (ARI) oraz analiza
  stabilności (leave-one-out / bootstrap), by zamienić deklarowaną niestabilność na
  zmierzoną.
+ *Render do audio + analiza widmowa* (FFT, reprezentacje melowe) - jedyna droga,
  by rzetelnie objąć cechy widmowe i mikro-timing.
+ *Powiększenie korpusu* i ewentualne sprzężenie cech z biofeedbackiem (np.
  parametry ruchu, tętno, HRV, reakcja elektrodermalna) - krok ku rzeczywistemu systemowi
  wspomagania terapii.
