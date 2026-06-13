import numpy as np
from collections import Counter


def compute_tempo_features(utwor):
    """Return aggregate tempo metrics from a PrettyMIDI-like object."""
    _, bpms = utwor.get_tempo_changes()
    bpms = np.asarray(bpms, dtype=float)
    bpms = bpms[np.isfinite(bpms) & (bpms > 0)]

    if len(bpms) == 0:
        return {
            'bpm_mean': 0.0,
            'bpm_std': 0.0,
            'tempo_stability': 0.0,
        }

    bpm_mean = float(np.mean(bpms))
    bpm_std = float(np.std(bpms))
    tempo_stability = 1.0 - bpm_std / bpm_mean if bpm_mean > 0 else 0.0

    return {
        'bpm_mean': bpm_mean,
        'bpm_std': bpm_std,
        'tempo_stability': tempo_stability,
    }


def fold_bpm_to_band(bpm, low=60.0, high=140.0, fold_up=False):
    """Fold a tempo into a target band by metric octaves (halving / doubling).

    MIDI tempo metadata is read at the quarter-note level, so pieces notated in
    cut time (alla breve) report tempo at twice the felt pulse — a march at
    ~110 BPM reads as ~220. Halving collapses this metric-octave artifact so the
    value is interpretable as step cadence for Rhythmic Auditory Stimulation.

    By default only over-fast tempi are folded down; genuinely slow pieces are
    left untouched so the slow/fast axis (relevant e.g. for relaxation material)
    is preserved. Set fold_up=True to also double tempi below `low` for a strict
    one-octave normalisation. Returns 0.0 for non-positive or non-finite input.
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


def dedupe_onsets(onsets, tol=0.03):
    """Merge near-simultaneous onset times using a tolerance in seconds."""
    onsets = np.sort(np.asarray(onsets, dtype=float))
    onsets = onsets[np.isfinite(onsets)]
    if len(onsets) == 0:
        return onsets

    keep = [float(onsets[0])]
    for t in onsets[1:]:
        # 30 ms approximates human temporal acuity for perceived simultaneity.
        if t - keep[-1] > tol:
            keep.append(float(t))
    return np.array(keep)


def compute_ioi_features(utwor):
    """Return onset-interval regularity and beat-normalised density metrics."""
    onsets = collect_onsets(utwor)
    if len(onsets) < 2:
        return {
            'notes_per_beat': 0.0,
            'ioi_cv': 0.0,
            'ioi_entropy': 0.0,
        }

    ioi = np.diff(onsets)
    ioi = ioi[np.isfinite(ioi) & (ioi > 0)]
    if len(ioi) == 0:
        return {
            'notes_per_beat': 0.0,
            'ioi_cv': 0.0,
            'ioi_entropy': 0.0,
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
    bpm_mean = tempo_features['bpm_mean']
    notes_per_beat = (
        (60.0 / bpm_mean) / ioi_mean
        if bpm_mean > 0 and ioi_mean > 0 else 0.0
    )

    return {
        'notes_per_beat': notes_per_beat,
        'ioi_cv': ioi_cv,
        'ioi_entropy': ioi_entropy,
    }


def collect_onsets(utwor, tol=0.03):
    """Deduplicated onset times across all non-drum instruments (seconds)."""
    onsets = []
    for inst in utwor.instruments:
        if inst.is_drum:
            continue
        onsets.extend(note.start for note in inst.notes)
    return dedupe_onsets(onsets, tol=tol)


def compute_pulse_clarity(utwor, fs_env=100, min_bpm=50, max_bpm=210, smooth_sigma_s=0.04):
    """Strength of the dominant periodic pulse from onset autocorrelation.

    Builds a smoothed onset envelope, autocorrelates it, and returns the height
    of the strongest autocorrelation peak within a plausible beat-period range,
    normalised to the zero-lag energy (range ~0..1). A steady, metrically regular
    groove scores high; rubato or ametric material scores low. Higher pulse
    clarity is associated with stronger motor entrainment, hence relevance to RAS.
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

    # Gaussian smoothing so near-grid onsets reinforce rather than cancel.
    sigma = max(smooth_sigma_s * fs_env, 1.0)
    radius = int(np.ceil(3 * sigma))
    kernel = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    kernel /= kernel.sum()
    env = np.convolve(env, kernel, mode="same")

    env = env - env.mean()
    if not np.any(env):
        return 0.0

    acf = np.correlate(env, env, mode="full")[len(env) - 1:]
    if acf[0] <= 0:
        return 0.0
    acf = acf / acf[0]

    lag_min = int(np.floor(fs_env * 60.0 / max_bpm))
    lag_max = min(int(np.ceil(fs_env * 60.0 / min_bpm)), len(acf) - 1)
    if lag_min < 1 or lag_max <= lag_min:
        return 0.0

    return float(np.clip(acf[lag_min:lag_max + 1].max(), 0.0, 1.0))


def compute_syncopation(utwor, subdivisions=4):
    """Off-beat emphasis: how much onset activity falls on weak metric positions.

    Each onset is placed by its phase within the beat onto a grid of
    `subdivisions` positions, weighted by a binary metric hierarchy (downbeat
    strongest). Returns 1 - mean(metric strength of onsets), in [0, 1]: 0 means
    every onset sits on the strongest positions (no syncopation), higher means
    more off-beat placement. Complements pulse clarity for rhythmic complexity.
    """
    beats = np.asarray(utwor.get_beats(), dtype=float)
    if len(beats) < 2:
        return 0.0

    onsets = collect_onsets(utwor)
    if len(onsets) == 0:
        return 0.0

    # Metric strength per grid position via 2-adic depth (downbeat = position 0).
    def metric_level(j):
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


def compute_form_complexity(utwor, window_s=4.0):
    """Formal heterogeneity over time from a self-similarity matrix.

    Splits the piece into fixed-length windows and describes each by its chroma
    (pitch-class) profile, onset density and mean register. Returns the mean
    pairwise cosine distance between non-empty windows (the mean off-diagonal of
    the self-dissimilarity matrix), in [0, 1]: low for pieces that keep one
    texture and harmony throughout (a single continuous section), high for pieces
    that move between contrasting sections (modulations, changes of register or
    density). Captures formal — not rhythmic — complexity, so a repetitive groove
    in an odd metre scores low while a multi-section piece scores high.
    """
    notes = []
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
    register = (register - register.min()) / span if span > 0 else np.zeros_like(register)

    feats = np.hstack([chroma, density[:, None], register[:, None]])
    norms = np.linalg.norm(feats, axis=1, keepdims=True)
    feats = feats / np.where(norms == 0, 1, norms)
    sim = feats @ feats.T
    iu = np.triu_indices(len(feats), k=1)
    return float(np.clip(1.0 - sim[iu].mean(), 0.0, 1.0))


def build_rolls(utwor, fs, min_notes=10):
    """Return (rolls, instruments) for all non-drum, non-sparse tracks."""
    rolls = []
    instruments = []
    for i, inst in enumerate(utwor.instruments):
        if inst.is_drum or len(inst.notes) < min_notes:
            continue
        rolls.append(inst.get_piano_roll(fs=fs))
        instruments.append((i, inst))
    return rolls, instruments


def pad_rolls(rolls, max_len=None):
    """Pad all rolls to the same column length."""
    if max_len is None:
        max_len = max(r.shape[1] for r in rolls)
    padded = []
    for r in rolls:
        if r.shape[1] < max_len:
            r = np.hstack([r, np.zeros((128, max_len - r.shape[1]))])
        padded.append(r)
    return padded, max_len


def highest_active_pitch(roll_window, min_pitch=48, min_energy_per_frame=10):
    """Return highest pitch with enough sustained energy in the window, or None."""
    window_len = roll_window.shape[1]
    if window_len == 0:
        return None
    threshold = min_energy_per_frame * window_len
    for pitch in range(127, min_pitch - 1, -1):
        if roll_window[pitch].sum() >= threshold:
            return pitch
    return None


def compute_highest_per_instrument(padded, beat_frames, min_pitch=48, min_energy_per_frame=10):
    """
    For each instrument and each beat-aligned window, find the highest active pitch.
    Returns list of lists: highest[inst_idx][beat_idx] = pitch or None.
    """
    n_windows = len(beat_frames) - 1
    result = []
    for roll in padded:
        row = []
        for w in range(n_windows):
            window = roll[:, beat_frames[w]:beat_frames[w + 1]]
            row.append(highest_active_pitch(window, min_pitch, min_energy_per_frame))
        result.append(row)
    return result


def track_lead_voice(highest, n_windows, n_inst, switch_n=3):
    """
    Continuity-based lead voice tracker.

    Stays with the current lead instrument unless a challenger has held a higher
    pitch for switch_n consecutive beats. On a switch, all streaks reset.

    Returns:
        lead_inst_idx: np.ndarray of shape (n_windows,) — instrument index per beat
        lead_pitch:    list of length n_windows — pitch (or None) per beat
    """
    lead_inst_idx = np.zeros(n_windows, dtype=int)
    lead_pitch = [None] * n_windows

    # Bootstrap: pick the instrument with the highest pitch on the first beat
    first_pitches = [highest[i][0] for i in range(n_inst)]
    current_lead = max(
        range(n_inst),
        key=lambda i: first_pitches[i] if first_pitches[i] is not None else -1,
    )

    streaks = {}

    for w in range(n_windows):
        current_pitch = highest[current_lead][w]
        lead_inst_idx[w] = current_lead
        lead_pitch[w] = current_pitch

        new_streaks = {}
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

def compute_contour(lead_pitch_changes):
    leap_threshold = 3  # semitones

    contour = []
    for i in range(1, len(lead_pitch_changes)):
        if lead_pitch_changes[i] is not None and lead_pitch_changes[i-1] is not None:
            interval = lead_pitch_changes[i] - lead_pitch_changes[i-1]
            if abs(interval) > leap_threshold:
                contour.append('leap')
            elif interval > 0:
                contour.append('up')
            elif interval < 0:
                contour.append('down')
            else:
                contour.append('same')
        else:
            contour.append('rest')
    return contour

def rle(pitch_data):
    segments = []
    current_pitch = None
    current_start = 0
    for i, pitch in enumerate(pitch_data):
        if pitch != current_pitch:
            if current_pitch is not None:
                segments.append((current_pitch, current_start, i))
            current_pitch = pitch
            current_start = i
    # add the last segment
    if current_pitch is not None:
        segments.append((current_pitch, current_start, len(pitch_data)))

    return segments


def compute_pitch_classes(lead_pitch_changes):
    return [p % 12 for p in lead_pitch_changes if p is not None]

def compute_key_from_pitch_classes(lead_pitch_changes):
    """
    Returns (major_key, major_corr, minor_key, minor_corr) as strings and floats.
    Uses Krumhansl-Schmuckler profiles.
    """
    NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    pitch_classes = compute_pitch_classes(lead_pitch_changes)
    pitch_class_counts = Counter(pitch_classes)
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    correlations = []
    for i in range(12):
        histogram = [pitch_class_counts.get((pc - i) % 12, 0) for pc in range(12)]
        major_corr = np.corrcoef(histogram, major_profile)[0, 1]
        minor_corr = np.corrcoef(histogram, minor_profile)[0, 1]
        correlations.append((i, major_corr, minor_corr))
    best_major = max(correlations, key=lambda x: x[1])
    best_minor = max(correlations, key=lambda x: x[2])
    return NOTE_NAMES[best_major[0]], best_major[1], NOTE_NAMES[best_minor[0]], best_minor[2]

def segment_phrases(lead_pitch, min_rest_beats=2):
    """
    Split lead_pitch into phrases at gaps of >= min_rest_beats consecutive Nones.
    Returns list of phrases; each phrase is a list of (beat_index, pitch) tuples.
    """
    phrases = []
    current_phrase = []
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


def find_motifs(phrases, n_range=(2, 5), top_k=5):
    """
    Find recurring interval-based motifs within phrases (transposition-invariant).

    Converts each phrase to a sequence of semitone intervals, then counts n-grams
    across all phrases without crossing phrase boundaries.

    Returns dict: n -> list of (interval_tuple, count, [start_beat_indices])
    sorted by count descending.
    """
    from collections import defaultdict

    results = {}
    for n in range(n_range[0], n_range[1] + 1):
        positions = defaultdict(list)

        for phrase in phrases:
            if len(phrase) < n + 1:
                continue
            beat_indices = [b for b, _ in phrase]
            pitches      = [p for _, p in phrase]

            # Collapse consecutive repeated pitches so sustained notes
            # don't create zero intervals that dilute motif matching
            collapsed_beats, collapsed_pitches = [beat_indices[0]], [pitches[0]]
            for b, p in zip(beat_indices[1:], pitches[1:]):
                if p != collapsed_pitches[-1]:
                    collapsed_beats.append(b)
                    collapsed_pitches.append(p)
            beat_indices, pitches = collapsed_beats, collapsed_pitches

            intervals    = [pitches[i + 1] - pitches[i] for i in range(len(pitches) - 1)]

            for i in range(len(intervals) - n + 1):
                ngram = tuple(intervals[i:i + n])
                positions[ngram].append(beat_indices[i])

        ranked = sorted(positions.items(), key=lambda x: len(x[1]), reverse=True)
        results[n] = [(ngram, len(locs), locs) for ngram, locs in ranked[:top_k]]

    return results

def compute_feature_vector(lead_pitch, phrases, utwor):
    """
    Compute a numeric feature vector for one song.
    Returns a dict with scalar metrics + pc_histogram list.
    """
    import math

    active = [p for p in lead_pitch if p is not None]
    if not active:
        return {}

    # --- intervals (collapsed, within phrases) ---
    intervals = []
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

    # interval entropy
    entropy = 0.0
    if total_iv > 0:
        entropy = -sum((c / total_iv) * math.log2(c / total_iv)
                        for c in interval_counts.values())

    # melodic redundancy — unique RLE groups / active beats
    redundancy = len(rle(lead_pitch)) / len(active)

    # step / leap ratio
    contour = compute_contour(lead_pitch)
    c = Counter(contour)
    steps = c.get('up', 0) + c.get('down', 0) + c.get('same', 0)
    leaps = c.get('leap', 0)
    step_leap_ratio = steps / leaps if leaps > 0 else float('inf')

    # pitch range
    pitch_range = max(active) - min(active)

    # average phrase length in beats
    avg_phrase_len = (
        sum(ph[-1][0] - ph[0][0] + 1 for ph in phrases) / len(phrases)
        if phrases else 0.0
    )

    # pitch class histogram (12 values, normalised)
    pc_counts = Counter(p % 12 for p in active)
    pc_histogram = [pc_counts.get(i, 0) / len(active) for i in range(12)]

    tempo_features = compute_tempo_features(utwor)
    ioi_features = compute_ioi_features(utwor)

    return {
        'interval_entropy':   entropy,
        'melodic_redundancy': redundancy,
        'step_leap_ratio':    min(step_leap_ratio, 10.0),  # cap inf
        'pitch_range':        pitch_range,
        'avg_phrase_length':  avg_phrase_len,
        'pc_histogram':       pc_histogram,
        'pulse_clarity':      compute_pulse_clarity(utwor),
        'syncopation':        compute_syncopation(utwor),
        'form_complexity':    compute_form_complexity(utwor),
        **tempo_features,
        **ioi_features,
    }


def feature_vector_to_array(fv):
    """Flatten feature dict to a 1-D numpy array for similarity computation."""
    return np.array([
        fv['interval_entropy'],
        fv['melodic_redundancy'],
        fv['step_leap_ratio'],
        fv['pitch_range'] / 127.0,
        fv['avg_phrase_length'] / 64.0,
        fv['bpm_mean'] / 200.0,
        fv['bpm_std'] / 200.0,
        fv['tempo_stability'],
        min(fv['notes_per_beat'], 4.0) / 4.0,
        fv['ioi_cv'],
        fv['ioi_entropy'] / 5.0,
        fv['pulse_clarity'],
        fv['syncopation'],
        fv['form_complexity'],
        *fv['pc_histogram'],
    ])


def compute_entrainment_suitability(features, low_cadence=90.0, high_cadence=130.0, tol=30.0, min_cadence=0.05):
    """A-priori score (0..1) for suitability as a Rhythmic Auditory Stimulation cue.

    Combines three conditions that the RAS literature (Thaut, Murgia) ties to
    effective motor entrainment, as their geometric mean — so a failure on any
    single dimension pulls the whole score down:
      * cadence fit  — folded tempo inside a comfortable walking-cadence band
        (~90-130 steps/min by default), with linear falloff over `tol` outside;
      * pulse clarity — a clear, salient periodic pulse to lock steps to;
      * on-beatness  — low syncopation, i.e. a predictable downbeat.
    Expects a feature dict from compute_feature_vector (uses bpm_mean,
    pulse_clarity, syncopation).

    The cadence term is floored at `min_cadence` (default 0.05) so a tempo far
    outside the band drastically lowers — but does not hard-zero — the score. This
    keeps the ranking informative among unsuitable pieces (e.g. a slow but very
    steady metronomic piece) instead of collapsing them all to exactly 0.
    """
    bpm = fold_bpm_to_band(features['bpm_mean'])
    if low_cadence <= bpm <= high_cadence:
        cadence = 1.0
    elif bpm < low_cadence:
        cadence = max(0.0, 1.0 - (low_cadence - bpm) / tol)
    else:
        cadence = max(0.0, 1.0 - (bpm - high_cadence) / tol)
    cadence = max(cadence, min_cadence)

    pulse = float(np.clip(features.get('pulse_clarity', 0.0), 0.0, 1.0))
    on_beat = float(np.clip(1.0 - features.get('syncopation', 0.0), 0.0, 1.0))
    return float((cadence * pulse * on_beat) ** (1.0 / 3.0))
