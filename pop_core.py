# Copyright (C) 2026 szabiz - Soli Deo Gloria
#
# Pop Filter Pro Application
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
pop_core.py - MEMORY-EFFICIENT CHUNKED POP FILTER ENGINE (v2,0 - Egyedi Régió Támogatással)
Alacsony RAM-használat 30+ perces fájlokhoz SSD-lapozás és lefagyás nélkül.
Copyright (c) szabiz 2026 - Soli Deo Gloria
"""

import numpy as np
from scipy.io import wavfile

CHUNK_SECONDS = 120
OVERLAP_SECONDS = 2
ROI_HIGH_HZ = 500.0


class AudioFile:
    def __init__(self, path, progress_callback=None):
        self.path = path

        if progress_callback:
            progress_callback(5, "Fájl beolvasása lemezről...")

        fs, data = wavfile.read(path)
        self.fs = fs
        self.orig_dtype = data.dtype
        self.is_stereo = data.ndim > 1
        self.n_channels = data.shape[1] if self.is_stereo else 1

        if np.issubdtype(self.orig_dtype, np.integer):
            self.maxval = float(np.iinfo(self.orig_dtype).max)
            x = data.astype(np.float32) / self.maxval
        else:
            self.maxval = 1.0
            x = data.astype(np.float32)

        self.samples = x if self.is_stereo else x.reshape(-1, 1)
        self.n_samples = self.samples.shape[0]
        self.duration_s = self.n_samples / self.fs

        self.nperseg = max(2048, int(self.fs * 0.085))
        self.noverlap = int(self.nperseg * 0.85)

        # Min/max burkológörbe a kirajzolt hullámhoz: egyszerű lépésközönkénti
        # mintavételezés (samples[::step]) könnyen "átugorhat" egy rövid,
        # éles pop-csúcsot, ha az épp két megtartott minta közé esik - ezért
        # minden kis időszeletben mind a minimumot, mind a maximumot
        # megtartjuk (ahogy az Audacity/Adobe Audition is teszi), így egy
        # pop csúcsa sosem vész el a nagyított/kicsinyített nézetben sem.
        max_buckets = 25000  # 2 pont/köteg (min+max) -> kb. 50 000 pont összesen
        if self.n_samples > max_buckets * 2:
            bucket_size = max(1, self.n_samples // max_buckets)
            n_buckets = self.n_samples // bucket_size
            trimmed = self.samples[:n_buckets * bucket_size, 0].reshape(n_buckets, bucket_size)
            mins = trimmed.min(axis=1)
            maxs = trimmed.max(axis=1)

            interleaved = np.empty(n_buckets * 2, dtype=np.float32)
            interleaved[0::2] = mins
            interleaved[1::2] = maxs
            self.display_wave = interleaved

            t_centers = (np.arange(n_buckets) + 0.5) * bucket_size / self.fs
            self.display_t = np.repeat(t_centers, 2)
        else:
            self.display_wave = self.samples[:, 0]
            self.display_t = np.linspace(0, self.duration_s, len(self.display_wave))


class PopParams:
    def __init__(self,
                 low_f=37.0,
                 high_f=172.0,
                 threshold_db=13.0,
                 max_reduction_db=26.0,
                 attack_ms=2.0,
                 release_ms=45.0,
                 baseline_window_s=0.8,
                 max_pop_duration_ms=180.0):
        self.low_f = low_f
        self.high_f = high_f
        self.threshold_db = threshold_db
        self.max_reduction_db = max_reduction_db
        self.attack_ms = attack_ms
        self.release_ms = release_ms
        self.baseline_window_s = baseline_window_s
        self.max_pop_duration_ms = max_pop_duration_ms

    def to_dict(self) -> dict:
        """JSON-be menthető alakra hozza a paramétereket - az egyedi
        pop-régiók mentéséhez/visszatöltéséhez kell."""
        return dict(
            low_f=self.low_f, high_f=self.high_f,
            threshold_db=self.threshold_db, max_reduction_db=self.max_reduction_db,
            attack_ms=self.attack_ms, release_ms=self.release_ms,
            baseline_window_s=self.baseline_window_s, max_pop_duration_ms=self.max_pop_duration_ms,
        )

    @classmethod
    def from_dict(cls, d: dict) -> "PopParams":
        return cls(
            low_f=d.get('low_f', 37.0), high_f=d.get('high_f', 172.0),
            threshold_db=d.get('threshold_db', 13.0), max_reduction_db=d.get('max_reduction_db', 26.0),
            attack_ms=d.get('attack_ms', 2.0), release_ms=d.get('release_ms', 45.0),
            baseline_window_s=d.get('baseline_window_s', 0.8),
            max_pop_duration_ms=d.get('max_pop_duration_ms', 180.0),
        )


def build_channel_cache(audio: AudioFile, ch: int, progress_callback=None):
    import scipy.signal as signal
    from scipy.ndimage import median_filter

    fs = audio.fs
    channel_data = audio.samples[:, ch]

    chunk_samples = int(fs * CHUNK_SECONDS)
    overlap_samples = int(fs * OVERLAP_SECONDS)
    total_samples = len(channel_data)
    step = chunk_samples - overlap_samples

    nperseg = audio.nperseg
    noverlap = audio.noverlap

    chunks = []
    start = 0
    chunk_idx = 0
    total_chunks = max(1, int(np.ceil(total_samples / step)))

    while start < total_samples:
        end = min(start + chunk_samples, total_samples)
        segment = channel_data[start:end]

        if progress_callback:
            pct = 5 + int(90 * (chunk_idx / total_chunks))
            progress_callback(pct, f"Spektrum elemzése: {chunk_idx + 1}/{total_chunks} blokk...")

        f, t_chunk, Z = signal.stft(
            segment, fs=fs,
            nperseg=nperseg, noverlap=noverlap,
            boundary='zeros', padded=True
        )

        S_mag = np.abs(Z)
        S_phase = np.angle(Z)

        roi_idx = np.where((f >= 0.0) & (f <= ROI_HIGH_HZ))[0]
        S_mag_roi = S_mag[roi_idx, :]

        H_roi = median_filter(S_mag_roi, size=(1, 13))
        P_roi = median_filter(S_mag_roi, size=(13, 1))

        track_max = float(np.max(S_mag) + 1e-9)

        chunks.append(dict(
            start=start, end=end,
            f=f, S_mag=S_mag, S_phase=S_phase,
            roi_idx=roi_idx, S_mag_roi=S_mag_roi,
            H_roi=H_roi, P_roi=P_roi,
            track_max=track_max, t_chunk=t_chunk,
        ))

        start += step
        chunk_idx += 1

    return dict(
        fs=fs, nperseg=nperseg, noverlap=noverlap,
        chunk_samples=chunk_samples, overlap_samples=overlap_samples,
        step=step, total_samples=total_samples, chunks=chunks,
    )


def build_cache(audio: AudioFile, progress_callback=None):
    return [build_channel_cache(audio, ch, progress_callback) for ch in range(audio.n_channels)]


def _chunk_gain_and_attenuation(chunk: dict, params: PopParams):
    f = chunk['f']
    roi_idx = chunk['roi_idx']
    S_mag_roi = chunk['S_mag_roi']
    H_roi = chunk['H_roi']
    P_roi = chunk['P_roi']
    track_max = chunk['track_max']

    low_pop_idx_all = np.where((f >= params.low_f) & (f <= params.high_f))[0]
    roi_set = set(roi_idx.tolist())
    low_pop_idx = np.array([i for i in low_pop_idx_all if i in roi_set], dtype=int)
    pop_in_roi = [i - roi_idx[0] for i in low_pop_idx]

    n_time = S_mag_roi.shape[1]
    attenuation_chunk = np.zeros(n_time, dtype=np.float32)
    wiener_gain = None

    if len(pop_in_roi) > 0:
        alpha = 10.0 ** (params.max_reduction_db / 20.0) - 1.0
        H_sub = H_roi[pop_in_roi, :]
        P_sub = P_roi[pop_in_roi, :]
        S_sub = S_mag_roi[pop_in_roi, :]

        signal_mask = S_sub > (track_max * 0.03)

        wiener_gain = np.ones_like(H_sub)
        denom = (H_sub ** 2) + alpha * (P_sub ** 2) + 1e-8
        calc_gain = (H_sub ** 2) / denom

        pop_condition = (P_sub > H_sub) & signal_mask
        wiener_gain[pop_condition] = calc_gain[pop_condition]

        gain_floor = 10.0 ** (-params.max_reduction_db / 20.0)
        wiener_gain = np.clip(wiener_gain, gain_floor, 1.0)

        mean_gain = np.mean(wiener_gain, axis=0)
        attenuation_chunk = -20 * np.log10(np.maximum(mean_gain, 1e-4))

    return low_pop_idx, pop_in_roi, wiener_gain, attenuation_chunk


def analyze_from_cache(channel_cache: dict, params: PopParams):
    all_t = []
    all_att = []
    fs = channel_cache['fs']

    for chunk in channel_cache['chunks']:
        _, _, _, attenuation_chunk = _chunk_gain_and_attenuation(chunk, params)
        global_t = chunk['t_chunk'] + (chunk['start'] / fs)
        all_t.append(global_t)
        all_att.append(attenuation_chunk)

    full_t = np.concatenate(all_t)
    full_att = np.concatenate(all_att)

    # A blokkok 2 mp-cel átfednek egymással (OVERLAP_SECONDS), ezért az
    # összefűzött idősor NEM feltétlenül monoton növekvő - ezt itt, idő
    # szerinti rendezéssel korrigáljuk, mielőtt bármi mást csinálnánk vele.
    order = np.argsort(full_t, kind='stable')
    full_t = full_t[order]
    full_att = full_att[order]

    return dict(t=full_t, smoothed=full_att)


def pop_segments(analysis, threshold_db=13.0, max_pop_duration_ms=180.0):
    t = analysis['t']
    smoothed = analysis['smoothed']
    active = smoothed >= threshold_db

    segments = []
    i = 0
    n = len(active)
    dt = (t[1] - t[0]) if len(t) > 1 else 0.01
    max_dur_s = (max_pop_duration_ms / 1000.0) if max_pop_duration_ms > 0 else 0.25

    while i < n:
        if active[i]:
            j = i
            while j < n and active[j]:
                j += 1
            start_t = t[i] - dt / 2
            end_t = t[j - 1] + dt / 2
            dur = end_t - start_t
            peak = float(np.max(smoothed[i:j]))

            if dur <= max_dur_s:
                segments.append((max(0.0, start_t), end_t, peak))
            i = j
        else:
            i += 1

    return _merge_overlapping_segments(segments)


def _merge_overlapping_segments(segments, merge_gap_s: float = 0.03):
    """A blokk-átfedések miatt ugyanaz a pop néha két, egymáshoz nagyon
    közeli vagy átfedő szakaszként jelenhet meg (egyszer az egyik, egyszer
    a másik blokkból számolva). Ez összevonja az ilyen, egymáshoz
    merge_gap_s-nál közelebb eső/átfedő szakaszokat egyetlen szakasszá."""
    if not segments:
        return segments
    ordered = sorted(segments, key=lambda s: s[0])
    merged = [ordered[0]]
    for start_t, end_t, peak in ordered[1:]:
        last_start, last_end, last_peak = merged[-1]
        if start_t <= last_end + merge_gap_s:
            merged[-1] = (last_start, max(last_end, end_t), max(last_peak, peak))
        else:
            merged.append((start_t, end_t, peak))
    return merged


def detect_all_from_cache(cache, params: PopParams):
    analyses = [analyze_from_cache(ch_cache, params) for ch_cache in cache]
    segments = pop_segments(analyses[0], params.threshold_db, params.max_pop_duration_ms) if analyses else []
    return analyses, segments


def _segment_envelope(frame_times: np.ndarray, segments, attack_ms: float, release_ms: float) -> np.ndarray:
    env = np.zeros(len(frame_times), dtype=np.float32)
    attack_s = max(attack_ms, 1.0) / 1000.0
    release_s = max(release_ms, 1.0) / 1000.0

    for start_t, end_t, _ in segments:
        core_mask = (frame_times >= start_t) & (frame_times <= end_t)
        env[core_mask] = 1.0

        attack_mask = (frame_times >= start_t - attack_s) & (frame_times < start_t)
        if np.any(attack_mask):
            ramp = (frame_times[attack_mask] - (start_t - attack_s)) / attack_s
            env[attack_mask] = np.maximum(env[attack_mask], ramp)

        release_mask = (frame_times > end_t) & (frame_times <= end_t + release_s)
        if np.any(release_mask):
            progress = (frame_times[release_mask] - end_t) / release_s
            ramp = 1.0 - progress
            env[release_mask] = np.maximum(env[release_mask], ramp)

    return np.clip(env, 0.0, 1.0)


def render_channel_from_cache(channel_cache: dict, params: PopParams, progress_callback=None,
                               start_sample: int = 0, max_duration_s: float = None, custom_regions: list = None):
    import scipy.signal as signal

    fs = channel_cache['fs']
    nperseg = channel_cache['nperseg']
    noverlap = channel_cache['noverlap']
    total_samples = channel_cache['total_samples']

    analysis = analyze_from_cache(channel_cache, params)
    segments = pop_segments(analysis, params.threshold_db, params.max_pop_duration_ms)

    # Minden egyedi régióhoz ELŐRE (a blokk-ciklus előtt, csak egyszer)
    # kiszámoljuk a SAJÁT paramétereivel adódó szegmens-listáját - ezt
    # blokkonként újraszámolni felesleges és lassú lenne.
    region_segments = {}
    if custom_regions:
        for reg in custom_regions:
            reg_analysis = analyze_from_cache(channel_cache, reg['params'])
            region_segments[id(reg)] = pop_segments(
                reg_analysis, reg['params'].threshold_db, reg['params'].max_pop_duration_ms)

    clean_signal = np.zeros(total_samples, dtype=np.float32)
    weights = np.zeros(total_samples, dtype=np.float32)

    relevant_chunks = [c for c in channel_cache['chunks'] if c['end'] > start_sample]
    if max_duration_s is not None:
        end_sample_limit = start_sample + int(max_duration_s * fs)
        relevant_chunks = [c for c in relevant_chunks if c['start'] < end_sample_limit]

    n_chunks = len(relevant_chunks)

    for idx, chunk in enumerate(relevant_chunks):
        if progress_callback:
            pct = 5 + int(90 * (idx / max(1, n_chunks)))
            progress_callback(pct, f"Szűrt hang előállítása: {idx + 1}/{n_chunks} blokk...")

        chunk_start = chunk['start']
        chunk_end = chunk['end']
        S_mag = chunk['S_mag']
        S_phase = chunk['S_phase']
        clean_mag = S_mag.copy()

        global_t = chunk['t_chunk'] + (chunk_start / fs)
        n_frames = len(global_t)

        # Minden egyes IDŐKERETHEZ eldöntjük, melyik paraméter-készlet
        # érvényes rá: egy egyedi régióé (ha az adott keret az ő
        # időtartományába - egy kis margóval kiegészítve - esik), vagy a
        # globális, ha egyikbe sem. Ez biztosítja, hogy egy egyedi
        # beállítás KIZÁRÓLAG a hozzá tartozó pop-ra hasson, ne az egész
        # (akár 120 mp-es) blokkra, és hogy egy blokkon belül TÖBB egyedi
        # régió is egyszerre, egymástól függetlenül érvényesülhessen.
        owner = np.full(n_frames, -1, dtype=int)  # -1 = globális
        if custom_regions:
            for reg_idx, reg in enumerate(custom_regions):
                if chunk_end <= reg['start_sample'] or chunk_start >= reg['end_sample']:
                    continue
                reg_start_t = reg['start_sample'] / fs
                reg_end_t = reg['end_sample'] / fs
                margin_s = max(reg['params'].release_ms, reg['params'].attack_ms, 50.0) / 1000.0
                mask = (global_t >= reg_start_t - margin_s) & (global_t <= reg_end_t + margin_s)
                # csak azokat a kereteket vesszük át, amik még nem tartoznak
                # másik (korábban feldolgozott) egyedi régióhoz
                owner[mask & (owner == -1)] = reg_idx

        # Csoportosítás paraméter-készlet szerint: a globális, plusz minden
        # ténylegesen ebben a blokkban érintett egyedi régió.
        groups = [(-1, params, segments, np.where(owner == -1)[0])]
        if custom_regions:
            for reg_idx, reg in enumerate(custom_regions):
                frame_idx = np.where(owner == reg_idx)[0]
                if len(frame_idx) > 0:
                    groups.append((reg_idx, reg['params'], region_segments[id(reg)], frame_idx))

        for _, active_params, active_segments, frame_idx in groups:
            if len(frame_idx) == 0:
                continue

            low_pop_idx, pop_in_roi, wiener_gain, _ = _chunk_gain_and_attenuation(chunk, active_params)
            if wiener_gain is None:
                continue

            envelope = _segment_envelope(global_t, active_segments, active_params.attack_ms, active_params.release_ms)
            gated_gain = 1.0 - envelope[np.newaxis, :] * (1.0 - wiener_gain)

            for idx_i, fidx in enumerate(low_pop_idx):
                clean_mag[fidx, frame_idx] *= gated_gain[idx_i, frame_idx]

            knock_limit_hz = 8000.0
            knock_idx = np.where((chunk['f'] > active_params.high_f) & (chunk['f'] <= knock_limit_hz))[0]

            if len(knock_idx) > 0 and len(low_pop_idx) > 0:
                mean_low_gain = np.mean(gated_gain[:, frame_idx], axis=0)
                f_knock = chunk['f'][knock_idx]
                f_ratio = (f_knock - active_params.high_f) / (knock_limit_hz - active_params.high_f)
                for i, fidx in enumerate(knock_idx):
                    severity = 0.85 - (f_ratio[i] * 0.70)
                    knock_gain = np.power(np.clip(mean_low_gain, 1e-4, 1.0), severity)
                    clean_mag[fidx, frame_idx] *= knock_gain

        clean_stft = clean_mag * np.exp(1j * S_phase)
        _, x_clean_chunk = signal.istft(
            clean_stft, fs=fs,
            nperseg=nperseg, noverlap=noverlap,
            time_axis=-1
        )

        chunk_len = min(len(x_clean_chunk), chunk_end - chunk_start)
        win = np.hanning(chunk_len).astype(np.float32) if (chunk_start > 0 or chunk_end < total_samples) else np.ones(chunk_len, dtype=np.float32)

        clean_signal[chunk_start:chunk_start + chunk_len] += x_clean_chunk[:chunk_len] * win
        weights[chunk_start:chunk_start + chunk_len] += win

    nonzero = weights > 1e-6
    clean_signal[nonzero] /= weights[nonzero]

    return clean_signal


def render_all_from_cache(audio: AudioFile, cache, params: PopParams, progress_callback=None,
                           start_sample: int = 0, max_duration_s: float = None, custom_regions: list = None):
    import numpy as np
    out = np.zeros_like(audio.samples)
    for ch in range(audio.n_channels):
        out[:, ch] = render_channel_from_cache(cache[ch], params, progress_callback, start_sample, max_duration_s, custom_regions)
    return out


def analyze_channel_chunked(audio: AudioFile, ch: int, params: PopParams, progress_callback=None):
    channel_cache = build_channel_cache(audio, ch, progress_callback)
    analysis = analyze_from_cache(channel_cache, params)
    clean_signal = render_channel_from_cache(channel_cache, params)
    return dict(t=analysis['t'], smoothed=analysis['smoothed'], clean_samples=clean_signal)


def detect_all(audio: AudioFile, params: PopParams, progress_callback=None):
    cache = build_cache(audio, progress_callback)
    return detect_all_from_cache(cache, params)


def render_all(audio: AudioFile, params: PopParams, analyses=None, custom_regions=None):
    cache = build_cache(audio)
    return render_all_from_cache(audio, cache, params, custom_regions=custom_regions)


def save_wav(audio: AudioFile, out_samples: np.ndarray, path: str):
    out = np.clip(out_samples, -1.0, 1.0)
    if np.issubdtype(audio.orig_dtype, np.integer):
        out_data = np.round(out * audio.maxval).astype(audio.orig_dtype)
    else:
        out_data = out.astype(audio.orig_dtype)
    if not audio.is_stereo:
        out_data = out_data[:, 0]
    wavfile.write(path, audio.fs, out_data)
