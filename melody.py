"""Ekstrakcja cech melodyczno-rytmicznych z plików MIDI na potrzeby analizy
porównawczej i oceny przydatności utworu jako bodźca rytmicznego (RAS)."""

import math
from collections import Counter
from collections.abc import Sequence

import numpy as np
import pretty_midi  # type: ignore[import-untyped]


def compute_tempo_features(utwor: pretty_midi.PrettyMIDI) -> dict[str, float]:
    """Wyznacza zbiorcze metryki tempa z obiektu MIDI.

    Args:
        utwor: Wczytany utwór (obiekt typu ``pretty_midi.PrettyMIDI``).

    Returns:
        Słownik z kluczami ``bpm_mean`` (średnie tempo), ``bpm_std`` (odchylenie
        standardowe tempa) oraz ``tempo_stability`` (``1 - znormalizowane
        odchylenie``, gdzie 1.0 oznacza stałe tempo). Przy braku zdarzeń tempa
        wszystkie wartości wynoszą 0.0.
    """
    _, bpms = utwor.get_tempo_changes()
    bpms = np.asarray(bpms, dtype=float)
    bpms = bpms[np.isfinite(bpms) & (bpms > 0)]

    if len(bpms) == 0:
        return {
            "bpm_mean": 0.0,
            "bpm_std": 0.0,
            "tempo_stability": 0.0,
        }

    bpm_mean = float(np.mean(bpms))
    bpm_std = float(np.std(bpms))
    tempo_stability = 1.0 - bpm_std / bpm_mean if bpm_mean > 0 else 0.0

    return {
        "bpm_mean": bpm_mean,
        "bpm_std": bpm_std,
        "tempo_stability": tempo_stability,
    }


def fold_bpm_to_band(
    bpm: float, low: float = 60.0, high: float = 140.0, fold_up: bool = False
) -> float:
    """Składa tempo do zadanego pasma przez oktawy metryczne (dzielenie/mnożenie ×2).

    Metadane tempa w MIDI odczytywane są na poziomie ćwierćnuty, więc utwory
    zapisane *alla breve* raportują tempo dwukrotnie zawyżone (marsz ~110 BPM
    czytany jest jako ~220). Dzielenie przez 2 znosi ten artefakt oktawy
    metrycznej, dzięki czemu wartość daje się interpretować jako kadencja kroków
    dla rytmicznej stymulacji słuchowej (RAS).

    Domyślnie składane w dół są tylko tempa zbyt szybkie; utwory naprawdę wolne
    pozostają nietknięte, by zachować oś wolne/szybkie (istotną np. dla materiału
    relaksacyjnego). ``fold_up=True`` podwaja również tempa poniżej ``low`` (ścisła
    normalizacja do jednej oktawy).

    Args:
        bpm: Tempo wejściowe w uderzeniach na minutę.
        low: Dolna granica pasma docelowego.
        high: Górna granica pasma docelowego.
        fold_up: Czy podwajać także tempa poniżej ``low``.

    Returns:
        Tempo złożone do pasma; 0.0 dla wejścia niedodatniego lub nieskończonego.
    """
    b = float(bpm)
    if not np.isfinite(b) or b <= 0:
        return 0.0
    while b > high:
        b /= 2.0
    if fold_up:
        while b < low:
            b *= 2.0
    return b


def compute_ioi_features(utwor: pretty_midi.PrettyMIDI) -> dict[str, float]:
    """Liczy regularność odstępów międzyonsetowych (IOI) i gęstość zdarzeń.

    Args:
        utwor: Wczytany utwór MIDI.

    Returns:
        Słownik z kluczami ``notes_per_beat`` (gęstość onsetów na uderzenie),
        ``ioi_cv`` (współczynnik zmienności IOI) oraz ``ioi_entropy`` (entropia
        rozkładu IOI). Przy mniej niż dwóch onsetach wszystkie wartości to 0.0.
    """
    onsets = collect_onsets(utwor)
    if len(onsets) < 2:
        return {
            "notes_per_beat": 0.0,
            "ioi_cv": 0.0,
            "ioi_entropy": 0.0,
        }

    ioi = np.diff(onsets)
    ioi = ioi[np.isfinite(ioi) & (ioi > 0)]
    if len(ioi) == 0:
        return {
            "notes_per_beat": 0.0,
            "ioi_cv": 0.0,
            "ioi_entropy": 0.0,
        }

    ioi_mean = float(np.mean(ioi))
    ioi_std = float(np.std(ioi))
    ioi_cv = ioi_std / ioi_mean if ioi_mean > 0 else 0.0

    counts, _ = np.histogram(ioi, bins=20)
    total = counts.sum()
    if total > 0:
        probs = counts[counts > 0] / total
        ioi_entropy = float(-np.sum(probs * np.log2(probs)))
    else:
        ioi_entropy = 0.0

    tempo_features = compute_tempo_features(utwor)
    bpm_mean = tempo_features["bpm_mean"]
    notes_per_beat = (
        (60.0 / bpm_mean) / ioi_mean if bpm_mean > 0 and ioi_mean > 0 else 0.0
    )

    return {
        "notes_per_beat": notes_per_beat,
        "ioi_cv": ioi_cv,
        "ioi_entropy": ioi_entropy,
    }


def collect_onsets(utwor: pretty_midi.PrettyMIDI, tol: float = 0.03) -> np.ndarray:
    """Zbiera i deduplikuje czasy onsetów ze wszystkich instrumentów nieperkusyjnych.

    Args:
        utwor: Wczytany utwór MIDI.
        tol: Tolerancja (w sekundach) scalania onsetów niemal równoczesnych.

    Returns:
        Posortowana tablica czasów onsetów (w sekundach) po deduplikacji.
    """
    onsets: list[float] = []
    for inst in utwor.instruments:
        if inst.is_drum:
            continue
        onsets.extend(note.start for note in inst.notes)

    def dedupe_onsets(times: Sequence[float], tol: float) -> np.ndarray:
        """Scala onsety niemal równoczesne w obrębie tolerancji (w sekundach)."""
        sorted_times = np.sort(np.asarray(times, dtype=float))
        sorted_times = sorted_times[np.isfinite(sorted_times)]
        if len(sorted_times) == 0:
            return sorted_times

        keep = [float(sorted_times[0])]
        for t in sorted_times[1:]:
            # 30 ms ~ próg rozdzielczości czasowej słuchu dla równoczesności.
            if t - keep[-1] > tol:
                keep.append(float(t))
        return np.array(keep)

    return dedupe_onsets(onsets, tol=tol)


def compute_pulse_clarity(
    utwor: pretty_midi.PrettyMIDI,
    fs_env: int = 100,
    min_bpm: float = 50.0,
    max_bpm: float = 210.0,
    smooth_sigma_s: float = 0.04,
) -> float:
    """Siła dominującego pulsu okresowego z autokorelacji obwiedni onsetów.

    Buduje wygładzoną obwiednię onsetów, autokorreluje ją i zwraca wysokość
    najsilniejszego szczytu autokorelacji w prawdopodobnym zakresie okresu
    uderzenia, znormalizowaną do energii w opóźnieniu zerowym (zakres ~0..1).
    Równy, metrycznie regularny groove uzyskuje wysoką wartość; materiał rubato
    lub ametryczny - niską. Wyższa wyrazistość pulsu wiąże się z silniejszym
    porywaniem ruchowym, stąd jej znaczenie dla RAS.

    Args:
        utwor: Wczytany utwór MIDI.
        fs_env: Częstotliwość próbkowania obwiedni onsetów (Hz).
        min_bpm: Najwolniejsze rozważane tempo (wyznacza maksymalne opóźnienie).
        max_bpm: Najszybsze rozważane tempo (wyznacza minimalne opóźnienie).
        smooth_sigma_s: Odchylenie standardowe (w sekundach) wygładzania gaussowskiego.

    Returns:
        Wyrazistość pulsu w zakresie [0, 1]; 0.0 dla materiału zbyt krótkiego lub
        pozbawionego okresowości.
    """
    onsets = collect_onsets(utwor)
    if len(onsets) < 4:
        return 0.0

    duration = float(onsets[-1] - onsets[0])
    if duration <= 0:
        return 0.0

    n = int(np.ceil(duration * fs_env)) + 1
    env = np.zeros(n)
    idx = np.clip(((onsets - onsets[0]) * fs_env).astype(int), 0, n - 1)
    np.add.at(env, idx, 1.0)

    # Wygładzanie gaussowskie, by onsety blisko siatki wzmacniały się, a nie znosiły.
    sigma = max(smooth_sigma_s * fs_env, 1.0)
    radius = int(np.ceil(3 * sigma))
    kernel = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    kernel /= kernel.sum()
    env = np.convolve(env, kernel, mode="same")

    env = env - env.mean()
    if not np.any(env):
        return 0.0

    acf = np.correlate(env, env, mode="full")[len(env) - 1 :]
    if acf[0] <= 0:
        return 0.0
    acf = acf / acf[0]

    lag_min = int(np.floor(fs_env * 60.0 / max_bpm))
    lag_max = min(int(np.ceil(fs_env * 60.0 / min_bpm)), len(acf) - 1)
    if lag_min < 1 or lag_max <= lag_min:
        return 0.0

    return float(np.clip(acf[lag_min : lag_max + 1].max(), 0.0, 1.0))


def compute_syncopation(utwor: pretty_midi.PrettyMIDI, subdivisions: int = 4) -> float:
    """Synkopacja: jaka część aktywności onsetów przypada na słabe pozycje metryczne.

    Każdy onset umieszczany jest według swojej fazy w obrębie uderzenia na siatce
    ``subdivisions`` pozycji, ważonej binarną hierarchią metryczną (najmocniejsza
    jest mocna część taktu). Zwraca ``1 - średnia(siła metryczna onsetów)`` w
    [0, 1]: 0 oznacza, że każdy onset trafia na najmocniejsze pozycje (brak
    synkopacji), wyższe wartości - więcej umiejscowień na słabej części. Uzupełnia
    wyrazistość pulsu w opisie złożoności rytmicznej.

    Args:
        utwor: Wczytany utwór MIDI.
        subdivisions: Liczba pozycji siatki w obrębie jednego uderzenia.

    Returns:
        Miara synkopacji w zakresie [0, 1]; 0.0 przy braku uderzeń lub onsetów.
    """
    beats = np.asarray(utwor.get_beats(), dtype=float)
    if len(beats) < 2:
        return 0.0

    onsets = collect_onsets(utwor)
    if len(onsets) == 0:
        return 0.0

    # Siła metryczna pozycji siatki przez głębokość 2-adyczną (mocna część = pozycja 0).
    def metric_level(j: int) -> int:
        if j == 0:
            j = subdivisions
        level = 1
        while j % 2 == 0:
            j //= 2
            level += 1
        return level

    strengths = np.array([metric_level(j) for j in range(subdivisions)], dtype=float)
    strengths /= strengths.max()

    k = np.searchsorted(beats, onsets, side="right") - 1
    valid = (k >= 0) & (k < len(beats) - 1)
    k = k[valid]
    ons = onsets[valid]
    if len(ons) == 0:
        return 0.0

    spans = beats[k + 1] - beats[k]
    ok = spans > 0
    if not np.any(ok):
        return 0.0
    phase = (ons[ok] - beats[k[ok]]) / spans[ok]
    pos = (np.round(phase * subdivisions).astype(int)) % subdivisions

    return float(1.0 - strengths[pos].mean())


def compute_form_complexity(
    utwor: pretty_midi.PrettyMIDI, window_s: float = 4.0
) -> float:
    """Niejednorodność formalna w czasie z macierzy samopodobieństwa.

    Dzieli utwór na okna o stałej długości i opisuje każde profilem chroma (klas
    wysokości), gęstością onsetów i średnim rejestrem. Zwraca średnią parami
    odległość kosinusową między oknami niepustymi (średnia z elementów
    pozadiagonalnych macierzy niepodobieństwa) w [0, 1]: niska dla utworów
    utrzymujących jedną fakturę i harmonię (pojedyncza ciągła sekcja), wysoka dla
    utworów przechodzących między kontrastującymi sekcjami (modulacje, zmiany
    rejestru lub gęstości). Ujmuje złożoność *formalną*, nie rytmiczną - więc
    powtarzalny groove w nieparzystym metrum wypada nisko, a utwór wielosekcyjny
    wysoko.

    Args:
        utwor: Wczytany utwór MIDI.
        window_s: Długość pojedynczego okna analizy (w sekundach).

    Returns:
        Złożoność formalna w zakresie [0, 1]; 0.0, gdy aktywne są mniej niż dwa okna.
    """
    notes: list[tuple[float, int]] = []
    for inst in utwor.instruments:
        if inst.is_drum:
            continue
        notes.extend((note.start, note.pitch) for note in inst.notes)
    if not notes:
        return 0.0

    end = utwor.get_end_time()
    n_win = max(int(np.ceil(end / window_s)), 1)
    chroma = np.zeros((n_win, 12))
    density = np.zeros(n_win)
    register = np.zeros(n_win)
    count = np.zeros(n_win)
    for start, pitch in notes:
        w = min(int(start / window_s), n_win - 1)
        chroma[w, pitch % 12] += 1.0
        density[w] += 1.0
        register[w] += pitch
        count[w] += 1.0

    active = count > 0
    if active.sum() < 2:
        return 0.0
    chroma = chroma[active]
    density = density[active]
    register = register[active] / count[active]

    row_sums = chroma.sum(axis=1, keepdims=True)
    chroma = chroma / np.where(row_sums == 0, 1, row_sums)
    density = density / density.max() if density.max() > 0 else density
    span = register.max() - register.min()
    register = (
        (register - register.min()) / span if span > 0 else np.zeros_like(register)
    )

    feats = np.hstack([chroma, density[:, None], register[:, None]])
    norms = np.linalg.norm(feats, axis=1, keepdims=True)
    feats = feats / np.where(norms == 0, 1, norms)
    sim = feats @ feats.T
    iu = np.triu_indices(len(feats), k=1)
    return float(np.clip(1.0 - sim[iu].mean(), 0.0, 1.0))


def build_rolls(
    utwor: pretty_midi.PrettyMIDI, fs: int, min_notes: int = 10
) -> tuple[list[np.ndarray], list[tuple[int, pretty_midi.Instrument]]]:
    """Zwraca piano-rolle wszystkich ścieżek nieperkusyjnych o dostatecznej gęstości.

    Args:
        utwor: Wczytany utwór MIDI.
        fs: Częstotliwość próbkowania piano-rolla (kolumny na sekundę).
        min_notes: Minimalna liczba nut, by ścieżka została uwzględniona.

    Returns:
        Para ``(rolls, instruments)``: lista piano-rolli (tablice 128×T) oraz lista
        par ``(indeks_instrumentu, instrument)`` w tej samej kolejności.
    """
    rolls = []
    instruments = []
    for i, inst in enumerate(utwor.instruments):
        if inst.is_drum or len(inst.notes) < min_notes:
            continue
        rolls.append(inst.get_piano_roll(fs=fs))
        instruments.append((i, inst))
    return rolls, instruments


def pad_rolls(
    rolls: list[np.ndarray], max_len: int | None = None
) -> tuple[list[np.ndarray], int]:
    """Dopełnia wszystkie rolle zerami do wspólnej liczby kolumn.

    Args:
        rolls: Lista piano-rolli (tablice 128×T o różnej długości).
        max_len: Docelowa liczba kolumn; gdy ``None``, używana jest długość
            najdłuższego rolla.

    Returns:
        Para ``(padded, max_len)``: lista rolli o równej długości oraz przyjęta
        liczba kolumn.
    """
    if max_len is None:
        max_len = max(r.shape[1] for r in rolls)
    padded = []
    for r in rolls:
        if r.shape[1] < max_len:
            r = np.hstack([r, np.zeros((128, max_len - r.shape[1]))])
        padded.append(r)
    return padded, max_len


def highest_active_pitch(
    roll_window: np.ndarray, min_pitch: int = 48, min_energy_per_frame: int = 10
) -> int | None:
    """Zwraca najwyższą wysokość o dostatecznej energii w oknie albo ``None``.

    Args:
        roll_window: Wycinek piano-rolla (128 wierszy × kolumny okna).
        min_pitch: Najniższa rozważana wysokość MIDI.
        min_energy_per_frame: Próg energii na kolumnę, by uznać wysokość za aktywną.

    Returns:
        Najwyższa aktywna wysokość MIDI lub ``None``, gdy żadna nie przekracza progu.
    """
    window_len = roll_window.shape[1]
    if window_len == 0:
        return None
    threshold = min_energy_per_frame * window_len
    for pitch in range(127, min_pitch - 1, -1):
        if roll_window[pitch].sum() >= threshold:
            return pitch
    return None


def compute_highest_per_instrument(
    padded: list[np.ndarray],
    beat_frames: Sequence[int],
    min_pitch: int = 48,
    min_energy_per_frame: int = 10,
) -> list[list[int | None]]:
    """Dla każdego instrumentu i okna wyrównanego do uderzenia wyznacza najwyższą aktywną wysokość.

    Args:
        padded: Lista piano-rolli o równej długości (zob. :func:`pad_rolls`).
        beat_frames: Indeksy kolumn wyznaczające granice okien (uderzeń).
        min_pitch: Najniższa rozważana wysokość MIDI.
        min_energy_per_frame: Próg energii na kolumnę.

    Returns:
        Lista list: ``highest[indeks_instrumentu][indeks_uderzenia]`` to wysokość
        lub ``None``.
    """
    n_windows = len(beat_frames) - 1
    result: list[list[int | None]] = []
    for roll in padded:
        row: list[int | None] = []
        for w in range(n_windows):
            window = roll[:, beat_frames[w] : beat_frames[w + 1]]
            row.append(highest_active_pitch(window, min_pitch, min_energy_per_frame))
        result.append(row)
    return result


def track_lead_voice(
    highest: list[list[int | None]], n_windows: int, n_inst: int, switch_n: int = 3
) -> tuple[np.ndarray, list[int | None]]:
    """Śledzi głos prowadzący na podstawie ciągłości w czasie.

    Pozostaje przy bieżącym instrumencie prowadzącym, dopóki pretendent nie utrzyma
    wyższej wysokości przez ``switch_n`` kolejnych uderzeń. Przy zmianie wszystkie
    serie są zerowane.

    Args:
        highest: Najwyższe wysokości na instrument i uderzenie (zob.
            :func:`compute_highest_per_instrument`).
        n_windows: Liczba okien (uderzeń).
        n_inst: Liczba instrumentów.
        switch_n: Liczba kolejnych uderzeń przewagi wymagana do zmiany prowadzącego.

    Returns:
        Para ``(lead_inst_idx, lead_pitch)``: tablica indeksów instrumentu
        prowadzącego na uderzenie oraz lista wysokości (lub ``None``) na uderzenie.
    """
    lead_inst_idx = np.zeros(n_windows, dtype=int)
    lead_pitch: list[int | None] = [None] * n_windows

    # Inicjalizacja: instrument o najwyższej wysokości na pierwszym uderzeniu.
    first_pitches = [highest[i][0] for i in range(n_inst)]
    current_lead = max(
        range(n_inst),
        key=lambda i: p if (p := first_pitches[i]) is not None else -1,
    )

    streaks: dict[int, int] = {}

    for w in range(n_windows):
        current_pitch = highest[current_lead][w]
        lead_inst_idx[w] = current_lead
        lead_pitch[w] = current_pitch

        new_streaks: dict[int, int] = {}
        for i in range(n_inst):
            if i == current_lead:
                continue
            p = highest[i][w]
            if p is None:
                continue
            if current_pitch is None or p > current_pitch:
                new_streaks[i] = streaks.get(i, 0) + 1

        streaks = new_streaks

        best_challenger = max(
            ((i, s) for i, s in streaks.items() if s >= switch_n),
            key=lambda x: highest[x[0]][w] or -1,
            default=None,
        )
        if best_challenger is not None:
            current_lead = best_challenger[0]
            streaks = {}

    return lead_inst_idx, lead_pitch


def compute_contour(lead_pitch_changes: Sequence[int | None]) -> list[str]:
    """Klasyfikuje kierunek melodii między kolejnymi wysokościami głosu prowadzącego.

    Args:
        lead_pitch_changes: Sekwencja wysokości głosu prowadzącego na uderzenie
            (``None`` oznacza pauzę).

    Returns:
        Lista etykiet o jeden element krótsza niż wejście, z wartościami: ``'up'``,
        ``'down'``, ``'same'``, ``'leap'`` (interwał większy niż próg) lub
        ``'rest'`` (jedna z porównywanych wysokości to ``None``).
    """
    leap_threshold = 3  # w półtonach

    contour: list[str] = []
    for i in range(1, len(lead_pitch_changes)):
        curr = lead_pitch_changes[i]
        prev = lead_pitch_changes[i - 1]
        if curr is not None and prev is not None:
            interval = curr - prev
            if abs(interval) > leap_threshold:
                contour.append("leap")
            elif interval > 0:
                contour.append("up")
            elif interval < 0:
                contour.append("down")
            else:
                contour.append("same")
        else:
            contour.append("rest")
    return contour


def rle(pitch_data: Sequence[int | None]) -> list[tuple[int, int, int]]:
    """Koduje sekwencję wysokości metodą RLE (run-length encoding).

    Args:
        pitch_data: Sekwencja wysokości na uderzenie (``None`` dozwolone).

    Returns:
        Lista segmentów ``(pitch, start, end)``, gdzie ``start`` i ``end`` to indeksy
        początku i końca (wyłącznie) ciągu o stałej wysokości. Ciągi pauz (``None``)
        są pomijane.
    """
    segments: list[tuple[int, int, int]] = []
    current_pitch: int | None = None
    current_start = 0
    for i, pitch in enumerate(pitch_data):
        if pitch != current_pitch:
            if current_pitch is not None:
                segments.append((current_pitch, current_start, i))
            current_pitch = pitch
            current_start = i
    # ostatni segment
    if current_pitch is not None:
        segments.append((current_pitch, current_start, len(pitch_data)))

    return segments


def segment_phrases(
    lead_pitch: Sequence[int | None], min_rest_beats: int = 2
) -> list[list[tuple[int, int]]]:
    """Dzieli głos prowadzący na frazy w miejscach dłuższych pauz.

    Granica frazy wypada tam, gdzie wystąpi co najmniej ``min_rest_beats`` kolejnych
    pauz (``None``).

    Args:
        lead_pitch: Wysokości głosu prowadzącego na uderzenie (``None`` to pauza).
        min_rest_beats: Liczba kolejnych pauz rozpoczynająca nową frazę.

    Returns:
        Lista fraz; każda fraza to lista par ``(indeks_uderzenia, pitch)``.
    """
    phrases: list[list[tuple[int, int]]] = []
    current_phrase: list[tuple[int, int]] = []
    rest_count = 0

    for i, pitch in enumerate(lead_pitch):
        if pitch is None:
            rest_count += 1
            if rest_count >= min_rest_beats and current_phrase:
                phrases.append(current_phrase)
                current_phrase = []
        else:
            rest_count = 0
            current_phrase.append((i, pitch))

    if current_phrase:
        phrases.append(current_phrase)

    return phrases


def compute_feature_vector(
    lead_pitch: Sequence[int | None],
    phrases: list[list[tuple[int, int]]],
    utwor: pretty_midi.PrettyMIDI,
) -> dict[str, float | list[float]]:
    """Agreguje wszystkie cechy jednego utworu do wspólnego słownika.

    Łączy cechy melodyczne (liczone z głosu prowadzącego i fraz) z cechami tempa
    oraz rytmiczno-formalnymi (tempo, IOI, wyrazistość pulsu, synkopacja, złożoność
    formalna).

    Args:
        lead_pitch: Wysokości głosu prowadzącego na uderzenie (``None`` to pauza).
        phrases: Frazy jako listy par ``(indeks_uderzenia, pitch)`` (zob.
            :func:`segment_phrases`).
        utwor: Wczytany utwór MIDI.

    Returns:
        Słownik cech: skalary (m.in. ``interval_entropy``, ``melodic_redundancy``,
        ``step_leap_ratio``, ``pitch_range``, ``avg_phrase_length``,
        ``pulse_clarity``, ``syncopation``, ``form_complexity`` oraz cechy tempa i
        IOI) i ``pc_histogram`` (znormalizowany 12-elementowy histogram klas
        wysokości). Pusty słownik, gdy głos prowadzący nie zawiera żadnej wysokości.
    """
    active = [p for p in lead_pitch if p is not None]
    if not active:
        return {}

    # --- interwały (zredukowane, w obrębie fraz) ---
    intervals: list[int] = []
    for phrase in phrases:
        pitches = [p for _, p in phrase]
        collapsed = [pitches[0]]
        for p in pitches[1:]:
            if p != collapsed[-1]:
                collapsed.append(p)
        for i in range(len(collapsed) - 1):
            intervals.append(collapsed[i + 1] - collapsed[i])

    interval_counts = Counter(intervals)
    total_iv = len(intervals)

    # entropia interwałów
    entropy = 0.0
    if total_iv > 0:
        entropy = -sum(
            (c / total_iv) * math.log2(c / total_iv) for c in interval_counts.values()
        )

    # redundancja melodyczna — liczba grup RLE / aktywne uderzenia
    redundancy = len(rle(lead_pitch)) / len(active)

    # stosunek kroków do skoków
    contour = compute_contour(lead_pitch)
    c = Counter(contour)
    steps = c.get("up", 0) + c.get("down", 0) + c.get("same", 0)
    leaps = c.get("leap", 0)
    step_leap_ratio = steps / leaps if leaps > 0 else float("inf")

    # zakres wysokości
    pitch_range = max(active) - min(active)

    # średnia długość frazy w uderzeniach
    avg_phrase_len = (
        sum(ph[-1][0] - ph[0][0] + 1 for ph in phrases) / len(phrases)
        if phrases
        else 0.0
    )

    # histogram klas wysokości (12 wartości, znormalizowany)
    pc_counts = Counter(p % 12 for p in active)
    pc_histogram = [pc_counts.get(i, 0) / len(active) for i in range(12)]

    tempo_features = compute_tempo_features(utwor)
    ioi_features = compute_ioi_features(utwor)

    return {
        "interval_entropy": entropy,
        "melodic_redundancy": redundancy,
        "step_leap_ratio": min(step_leap_ratio, 10.0),  # ograniczenie inf
        "pitch_range": pitch_range,
        "avg_phrase_length": avg_phrase_len,
        "pc_histogram": pc_histogram,
        "pulse_clarity": compute_pulse_clarity(utwor),
        "syncopation": compute_syncopation(utwor),
        "form_complexity": compute_form_complexity(utwor),
        **tempo_features,
        **ioi_features,
    }


def compute_entrainment_suitability(
    features: dict[str, float],
    low_cadence: float = 90.0,
    high_cadence: float = 130.0,
    tol: float = 30.0,
    min_cadence: float = 0.05,
) -> float:
    """Aprioryczny wskaźnik (0..1) przydatności utworu jako bodźca RAS.

    Łączy trzy warunki, które literatura RAS (Thaut, Murgia) wiąże ze skutecznym
    porywaniem ruchowym, jako ich średnią geometryczną - tak, by zawód na
    którymkolwiek wymiarze obniżał cały wynik:

    * dopasowanie kadencji - tempo złożone w komfortowym paśmie kadencji chodu
      (domyślnie ~90-130 kroków/min), z liniowym spadkiem poza pasmem (szerokość ``tol``);
    * wyrazistość pulsu - wyraźny, wyrazisty puls okresowy, do którego można dostroić kroki;
    * trzymanie się rytmu - niska synkopacja, czyli przewidywalna mocna część taktu.

    Człon kadencji jest ograniczony od dołu wartością ``min_cadence`` (domyślnie
    0.05), więc tempo daleko poza pasmem drastycznie - ale nie do zera - obniża
    wynik. Dzięki temu ranking pozostaje informatywny wśród utworów nieodpowiednich
    (np. wolny, lecz bardzo równy metrycznie utwór), zamiast sprowadzać je wszystkie
    do dokładnie 0.

    Args:
        features: Słownik cech (zob. :func:`compute_feature_vector`); używane są
            ``bpm_mean``, ``pulse_clarity`` i ``syncopation``.
        low_cadence: Dolna granica pasma kadencji (kroki/min).
        high_cadence: Górna granica pasma kadencji (kroki/min).
        tol: Szerokość liniowego spadku poza pasmem (w BPM).
        min_cadence: Dolne ograniczenie członu kadencji.

    Returns:
        Wskaźnik przydatności do RAS w zakresie [0, 1].
    """
    bpm = fold_bpm_to_band(features["bpm_mean"])
    if low_cadence <= bpm <= high_cadence:
        cadence = 1.0
    elif bpm < low_cadence:
        cadence = max(0.0, 1.0 - (low_cadence - bpm) / tol)
    else:
        cadence = max(0.0, 1.0 - (bpm - high_cadence) / tol)
    cadence = max(cadence, min_cadence)

    pulse = float(np.clip(features.get("pulse_clarity", 0.0), 0.0, 1.0))
    on_beat = float(np.clip(1.0 - features.get("syncopation", 0.0), 0.0, 1.0))
    return float((cadence * pulse * on_beat) ** (1.0 / 3.0))
