// Slajdy do prezentacji projektu (wykład "Muzyka i Biocybernetyka").
// Budowanie:  make slides   (lub: typst compile --font-path .fonts report/slajdy.typ report/slajdy.pdf)
//
// Treść jest destylatem raportu (report/raport.typ) - slajdy mają być oparciem
// dla mówcy, nie tekstem do czytania. Figury pochodzą z 4_comparison.ipynb
// (report/figures/*.png); po zmianie ekstrakcji cech wygeneruj je ponownie.
//
// #speaker-note[...] to notatki prelegenta - nie pojawiają się na slajdzie,
// służą do ćwiczenia mówienia.

#import "@preview/touying:0.5.5": *
#import themes.metropolis: *

#show: metropolis-theme.with(
  aspect-ratio: "16-9",
  // Paleta: biel + koral #e8634a (akcent, pasek nagłówka, slajdy focus).
  // Tekst pozostaje ciemny dla czytelności.
  config-colors(
    primary: rgb("#e8634a"),
    primary-light: rgb("#e8634a").lighten(70%),
    secondary: rgb("#e8634a"),
    neutral-lightest: rgb("#ffffff"),
    neutral-dark: rgb("#e8634a"),
    neutral-darkest: rgb("#222222"),
  ),
  // Pogrubienia (*...*) mają być czarne (emfaza wagą), a nie koralowe -
  // koral rezerwujemy na chrom (nagłówek, focus, pasek) i celowe callouty.
  config-common(show-strong-with-alert: false),
  config-info(
    title: [Automatyczna analiza melodyczno-rytmiczna MIDI w kontekście RAS],
    subtitle: [Czy z pliku MIDI da się obiektywnie ocenić bodziec rytmiczny?],
    author: [Krzysztof Czuba #h(1em) Piotr Skowroński],
    date: datetime(year: 2026, month: 6, day: 17),
    institution: [Muzyka i Biocybernetyka],
  ),
)

// Fonty: Fira Sans (domyślny dla metropolis) nie jest zainstalowany,
// więc używamy Helvetica Neue (body) i Fira Mono (kod) - jak w raporcie.
#set text(lang: "pl", font: "Helvetica Neue")
#show raw: set text(font: "Fira Mono")

#title-slide()

// ===========================================================================
= Tło i motywacja

== Muzyka jako bodziec czasowy

#speaker-note[
  Otwórz tezą. To NIE jest projekt o MIDI - to projekt o entrainmencie i RAS,
  czyli temat 6 i temat 9 z naszego wykładu (projekt B+R prowadzącego, NCBR).
  Powiedz to wprost: tu łączymy analizę sygnału z tym, co było na zajęciach.
]

- Muzyka = uporządkowana sekwencja zdarzeń o mierzalnym tempie, rytmie i pulsie.
- *Music entrainment* (Thaut): rytm działa jak zewnętrzny zegar, do którego
  mimowolnie dostraja się układ ruchowy.
- *RAS* (Rhythmic Auditory Stimulation): regularny bodziec słuchowy normalizuje
  chód - Murgia i in. wykazali to dla choroby Parkinsona.

#focus-slide[
  Tempo, puls i regularność - czy da się je zmierzyć\
  i przewidzieć, który utwór jest dobrym „metronomem” dla ruchu?
]

// ===========================================================================
= Dane i metoda

== Korpus: 15 plików MIDI, 3 grupy aprioryczne

#speaker-note[
  Podkreśl: podział to HIPOTEZA do sprawdzenia, nie prawda referencyjna.
  Zwróć uwagę na asymetrię definicji - to wróci w wynikach.
]

#grid(
  columns: (1fr, 1fr, 1fr),
  gutter: 1em,
  [
    *RAS* (chód) \
    _funkcjonalnie_ \
    #text(size: 0.8em)[Sousa, Strauss, Elgar, Survivor, Bee Gees]
  ],
  [
    *Relaksacja* \
    _funkcjonalnie_ \
    #text(size: 0.8em)[Satie, Debussy, Pachelbel, Beethoven, Chopin]
  ],
  [
    *Złożoność* \
    _strukturalnie_ \
    #text(size: 0.8em)[Queen, Brubeck, Pink Floyd, King Crimson, Radiohead]
  ],
)

#v(0.8em)
- Podział traktujemy jako *hipotezę*: czy obiektywne cechy go odtworzą?
- Uwaga: „RAS” i „relaksacja” to *funkcje*, „złożoność” to *budowa* - ta
  asymetria jest celowa i wróci w wynikach.

== Dlaczego MIDI?

- MIDI to *zapis symboliczny*, nie audio: wprost daje onsety, tempo, wysokości,
  instrumenty - bez separacji źródeł z nagrania.
- *Zaleta:* powtarzalna, spójna reprezentacja dla wielu utworów -> idealne do
  prototypu metody porównawczej.
- *Wada:* upraszcza brzmienie, dynamikę i mikro-timing wykonania.

#v(0.5em)
#align(center)[
  #text(fill: rgb("#e8634a"))[
    *Wnioski dotyczą struktury zapisanej w MIDI, nie konkretnego nagrania audio.*
  ]
]

== Pipeline i cechy rytmiczno-formalne

#speaker-note[
  Nie tłumacz wszystkich cech po kolei - wybierz JEDNĄ (pulse clarity) i wyjaśnij
  intuicyjnie: "jak wyraźny jest metronom w tle". Reszta to lista.
]

Dla każdego utworu wyciągamy melodię główną (`track_lead_voice`),
dzielimy ją na fragmenty zgodne z beatami i mierzymy cechy rytmu.

#grid(
  columns: (1fr, 1.3fr),
  gutter: 1.2em,
  [
    *Mierzone cechy:*
    - tempo (dopasowane do tempa chodu)
    - *wyrazistość pulsu* (`pulse_clarity`)
    - synkopacja (rytm grany „obok” pulsu)
    - regularność odstępów między nutami
    - złożoność formy
  ],
  [
    *`pulse_clarity` - intuicja:* \
    jak wyraźny, regularny „metronom” słychać w tle. \
    Blisko 1 -> mocny, równy puls (_Canon_ 0.87). \
    Nisko -> tempo elastyczne lub nieparzyste (_Take Five_ 0.34).
  ],
)

== Wskaźnik przydatności do RAS

#speaker-note[
  TO JEST SEDNO metody. Kluczowa myśl: średnia geometryczna - jeden słaby
  warunek ciągnie całość w dół. Suma ważona by to zamaskowała.
]

Trzy warunki, które literatura wiąże ze skuteczną synchronizacją ruchu, łączymy
*średnią geometryczną*:

#align(center, text(size: 1.4em)[
  $ S = root(3, c dot p dot (1 - s)) $
])

#grid(
  columns: (1fr, 1fr, 1fr),
  gutter: 1em,
  [$c$ - dopasowanie *kadencji* (tempo w paśmie $approx$ 90–130 kroków/min)],
  [$p$ - *wyrazistość pulsu*],
  [$1 - s$ - *przewidywalność* (mało synkopacji)],
)

#v(0.6em)
#align(center)[
  #text(fill: rgb("#e8634a"))[*Jeden warunek zawiedzie -> cały wskaźnik pada.*]
  Mierzymy łatwość synchronizacji ruchu z pulsem, nie pobudzenie.
]

// ===========================================================================
= Wyniki

== Profile grup: podział nie jest jednowymiarowy

#grid(
  columns: (1.4fr, 1fr),
  gutter: 1em,
  align: horizon,
  image("figures/radar.png", width: 100%),
  [
    - Grupy różnią się głównie na osiach *pulsu, gęstości onsetów i tempa*.
    - Ale profile się *przenikają* - pierwszy sygnał, że aprioryczny podział nie
      jest jednowymiarowy.
  ],
)

== Ranking przydatności do RAS

#speaker-note[
  Nie czytaj słupków. Opowiedz 3 historie kontrastowe - każda da się obronić
  słuchem. To najbardziej "klikający" moment prezentacji.
]

#grid(
  columns: (1.3fr, 1fr),
  gutter: 1em,
  align: horizon,
  image("figures/ras_suitability.png", width: 100%),
  [
    *Wskaźnik to iloczyn - wystarczy jeden słaby warunek:*
    - *Stars & Stripes* (0.81) - wzorzec: tempo $approx$111, czysty puls.
    - *Moonlight* (0.29) - *odpada mimo najczystszego pulsu* (0.89): 45 BPM za
      wolno -> tempo to twarde ograniczenie.
    - *Take Five* (0.57) - tempo OK, ale nierówny rytm daje słaby puls.
    - *Gymnopédie* (0.91, *najwyżej*) - „relaksacyjny”, a świetny metronom.
  ],
)

== Najważniejszy wynik: „złożoność” ma dwie twarze

#speaker-note[
  TO jest wasz oryginalny wynik i najlepszy moment naukowy. Podkreśl meta-wniosek:
  cechy dobraliśmy z TEORII, nie pod etykiety - i właśnie dlatego ujawniły
  strukturę, której nie zakładaliśmy.
]

Algorytm klastrowania na 7 cechach (dendrogram) dał *inne* grupy niż
zakładaliśmy. Aprioryczna klasa „złożona” *rozpadła się* - jej utwory rozeszły
się do różnych klastrów, bo „złożoność” miesza dwa zjawiska:

#grid(
  columns: (1.2fr, 1fr),
  gutter: 1em,
  align: horizon,
  image("figures/dendrogram.png", width: 100%),
  [
    - *rytmiczna* (nierówny rytm, słaby puls): _Take Five_, _Money_ - ale forma
      prosta (powtarzalny groove).
    - *formalna* (wiele sekcji, zmiany): _Bohemian Rhapsody_, a też
      „relaksacyjne” _Clair de Lune_, _Nocturne_.
  ],
)

#v(0.3em)
#align(center)[
  #text(fill: rgb("#e8634a"))[*To algorytm sam ujawnił tę strukturę - cechy
  liczyliśmy z teorii, nie dostrajaliśmy ich pod etykiety.*]
]

// ===========================================================================
= Podsumowanie

== Ograniczenia

#speaker-note[
  Uprzedź pytania egzaminatora. To buduje wiarygodność, nie osłabia.
]

- *Reprezentacja symboliczna* - MIDI ≠ audio, brak mikro-timingu wykonania.
- *Mała próba* - N = 15 w przestrzeni 7D: klastry niestabilne -> *prototyp, nie dowód*.
- *Subiektywne etykiety* - podział aprioryczny to hipoteza, nie „prawda”.
- *Brak walidacji na ludziach* - wskaźnik oparty na przesłankach teoretycznych.

== Wnioski i kierunki dalsze

*Trzy wnioski:*
+ Tempo jest *konieczne, ale niewystarczające*.
+ Wyrazistość pulsu - korelat *entrainmentu* (zgodnie z Thautem).
+ „Złożoność” jest *dwuwymiarowa*: trudny rytm ≠ skomplikowana budowa.

#v(0.5em)
*Dalej (wg stosunku wartości do nakładu):*
+ Render do audio -> analiza widmowa i mikro-timing.
+ Większy korpus MIDI + sprzężenie z biofeedbackiem (tętno, HRV, parametry ruchu).

#focus-slide[
  Z pliku MIDI da się policzyć interpretowalne cechy bodźca rytmicznego -\
  i pokazują one więcej, niż zakładał intuicyjny podział.
]

== Bibliografia

#set text(size: 0.82em)
#set par(spacing: 0.9em)

+ Thaut, M. H. (2013). _Biomedical Research in Music._ W: _Rhythm, Music, and the
  Brain: Scientific Foundations and Clinical Applications_, s. 61–84. Routledge, New York.
+ Murgia, M. i in. (2018). _The Use of Footstep Sounds as Rhythmic Auditory
  Stimulation for Gait Rehabilitation in Parkinson's Disease: A Randomized
  Controlled Trial._ Frontiers in Neurology, 9.
+ Natanson, T. (1992). _Programowanie muzyki terapeutycznej._ Wrocław (Zeszyt
  naukowy nr 53, Seria Monografie).
+ Cylulko, P. (1992). _Diagnoza i diagnostyka muzykoterapeutyczna._ W:
  _Programowanie muzyki terapeutycznej_ (Zeszyt naukowy nr 53). Wrocław.
+ Pałosz, P. (2009). _Przegląd badań nad uwarunkowaniami preferencji muzycznych._
  Przegląd Psychologiczny, 52(2).
