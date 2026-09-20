# I am adding comments for me to easily understand the codes
# audio.py - every sound effect and music track is synthesised with maths
# when the game starts, so the game needs no audio files at all.
# numpy does the heavy lifting; if it is missing the game simply runs silent.

import random

import pygame

try:
    import numpy as np
except ImportError:          # the game still works without numpy, just silently
    np = None

RATE = 44100


# ------------------------------------------------------------------ synth building blocks
def _t(duration):
    return np.arange(int(RATE * duration)) / RATE


def _phase(freq_start, freq_end, duration, curve="exp"):
    """Running phase for a (possibly sliding) frequency."""
    n = int(RATE * duration)
    if curve == "exp" and freq_start > 0 and freq_end > 0:
        freqs = freq_start * (freq_end / freq_start) ** np.linspace(0, 1, n)
    else:
        freqs = np.linspace(freq_start, freq_end, n)
    return np.cumsum(freqs) / RATE


def _wave(kind, phase):
    frac = phase % 1.0
    if kind == "sine":
        return np.sin(2 * np.pi * phase)
    if kind == "square":
        return np.where(frac < 0.5, 1.0, -1.0) * 0.6
    if kind == "pulse":
        return np.where(frac < 0.25, 1.0, -1.0) * 0.6
    if kind == "saw":
        return (2 * frac - 1) * 0.7
    if kind == "tri":
        return 2 * np.abs(2 * frac - 1) - 1
    raise ValueError(kind)


def _tone(kind, f0, f1, duration, attack=0.005, release=0.05, vibrato=0.0, vib_rate=6.0):
    phase = _phase(f0, f1, duration)
    if vibrato:
        t = _t(duration)
        phase = phase + vibrato * np.sin(2 * np.pi * vib_rate * t) / (2 * np.pi * vib_rate)
    return _envelope(_wave(kind, phase), attack, release)


def _noise(duration, smooth=1):
    data = np.random.uniform(-1, 1, int(RATE * duration))
    if smooth > 1:
        data = np.convolve(data, np.ones(smooth) / smooth, mode="same") * np.sqrt(smooth) * 0.8
    return data


def _envelope(data, attack=0.005, release=0.05, curve=1.0):
    n = len(data)
    env = np.ones(n)
    a = min(n, int(RATE * attack))
    r = min(n, int(RATE * release))
    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    if r > 0:
        env[n - r:] *= np.linspace(1, 0, r) ** curve
    return data * env


def _decay(data, rate):
    return data * np.exp(-np.arange(len(data)) / RATE * rate)


def _lowpass(data, width):
    if width <= 1:
        return data
    return np.convolve(data, np.ones(width) / width, mode="same")


def _mix(*parts):
    """Add sounds of different lengths together."""
    out = np.zeros(max(len(p) for p in parts))
    for p in parts:
        out[: len(p)] += p
    return out


def _concat(*parts):
    return np.concatenate(parts)


def _silence(duration):
    return np.zeros(int(RATE * duration))


def _mix_into(target, source, start_sample, gain=1.0):
    end = min(len(target), start_sample + len(source))
    if end > start_sample:
        target[start_sample:end] += source[: end - start_sample] * gain


def _to_sound(mono, volume=1.0, stereo_spread=0.0):
    peak = np.max(np.abs(mono)) or 1.0
    mono = mono / peak * volume
    left = mono
    right = mono
    if stereo_spread:
        shift = int(RATE * stereo_spread)
        right = np.concatenate([np.zeros(shift), mono[:-shift]]) if shift else mono
    stereo = np.stack([left, right], axis=1)
    stereo = np.clip(stereo * 32767, -32768, 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


def _note(name):
    """'A4' -> 440 Hz. Supports sharps like 'C#5'."""
    names = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3,
             "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
    octave = int(name[-1])
    semis = names[name[:-1]] + (octave - 4) * 12
    return 440.0 * 2 ** (semis / 12)


# ------------------------------------------------------------------ sound effects
def _build_sfx():
    s = {}
    s["jump"] = _to_sound(_tone("pulse", 280, 640, 0.09, release=0.05), 0.32)
    s["land"] = _to_sound(_decay(_lowpass(_noise(0.08), 12), 40) + _decay(_tone("sine", 120, 60, 0.08), 30), 0.35)
    s["death"] = _to_sound(_mix(
        _decay(_lowpass(_noise(0.45), 3), 9) * 0.9,
        _envelope(_tone("saw", 420, 50, 0.45), 0.002, 0.2) * 0.8,
        _decay(_tone("sine", 90, 40, 0.4), 6)), 0.75)
    s["splat"] = _to_sound(_decay(_lowpass(_noise(0.18), 20), 18), 0.45)
    s["crumble"] = _to_sound(
        _decay(_lowpass(_noise(0.35), 6), 7) * (0.6 + 0.4 * np.sign(np.sin(np.arange(int(RATE * 0.35)) / RATE * 2 * np.pi * 23))),
        0.4)
    s["pop"] = _to_sound(_tone("square", 1500, 700, 0.06, release=0.03) + _decay(_noise(0.06), 50) * 0.5, 0.35)
    s["spring"] = _to_sound(_tone("sine", 180, 900, 0.28, release=0.1, vibrato=35, vib_rate=28), 0.5)
    s["bump"] = _to_sound(_tone("square", 190, 140, 0.07, release=0.04), 0.3)
    s["reveal"] = _to_sound(_concat(_tone("tri", 660, 660, 0.06), _tone("tri", 990, 990, 0.12, release=0.08)), 0.35)
    s["checkpoint"] = _to_sound(_concat(_tone("sine", _note("E6"), _note("E6"), 0.1), _tone("sine", _note("B6"), _note("B6"), 0.25, release=0.2)), 0.35)
    win = _concat(*[_tone("pulse", _note(n), _note(n), 0.08, release=0.02) for n in ("C5", "E5", "G5")],
                  _tone("pulse", _note("C6"), _note("C6"), 0.45, release=0.35))
    s["win"] = _to_sound(_mix(win, _lowpass(_noise(len(win) / RATE), 30) * 0.05), 0.45)
    sad = _concat(*[_tone("saw", _note(n), _note(n) * 0.98, 0.26, release=0.05, vibrato=4) for n in ("G3", "F#3", "F3")],
                  _tone("saw", _note("E3"), _note("E3") * 0.96, 0.8, release=0.3, vibrato=10, vib_rate=5))
    s["sad"] = _to_sound(_lowpass(sad, 6), 0.5)
    s["troll"] = _to_sound(_concat(_tone("square", 520, 900, 0.07), _tone("square", 900, 300, 0.16, release=0.08)), 0.3)
    s["rumble"] = _to_sound(_decay(_lowpass(_noise(0.7), 40), 4) + _decay(_tone("sine", 55, 40, 0.7), 4) * 0.6, 0.6)
    s["slam"] = _to_sound(_decay(_lowpass(_noise(0.3), 18), 14) + _decay(_tone("sine", 80, 35, 0.3), 10), 0.7)
    s["arrow"] = _to_sound(_envelope(_lowpass(_noise(0.22), 2), 0.12, 0.08) * 0.8 + _tone("sine", 2400, 1800, 0.22, 0.1, 0.1) * 0.1, 0.35)
    s["saw_on"] = _to_sound(_envelope(_tone("saw", 110, 190, 0.35, vibrato=20, vib_rate=40), 0.02, 0.1), 0.25)
    s["say"] = _to_sound(_tone("tri", 520, 520, 0.03, release=0.02), 0.12)
    s["ui_move"] = _to_sound(_tone("square", 900, 900, 0.025, release=0.015), 0.14)
    s["ui_select"] = _to_sound(_tone("pulse", 600, 1100, 0.07, release=0.04), 0.25)
    s["ui_back"] = _to_sound(_tone("pulse", 600, 330, 0.07, release=0.04), 0.22)
    s["dark"] = _to_sound(_concat(_tone("square", 1200, 1200, 0.02), _silence(0.05), _decay(_lowpass(_noise(0.3), 30), 8)), 0.3)
    s["stomp"] = _to_sound(_mix(_tone("square", 400, 900, 0.08, release=0.04), _decay(_lowpass(_noise(0.1), 8), 30) * 0.6), 0.4)
    s["orb"] = _to_sound(_tone("sine", 1400, 500, 0.14, release=0.06, vibrato=40, vib_rate=30), 0.3)
    s["cannon"] = _to_sound(_mix(_decay(_lowpass(_noise(0.4), 10), 9), _decay(_tone("sine", 90, 40, 0.4), 7)), 0.7)
    s["laser"] = _to_sound(_mix(_tone("saw", 1800, 1600, 0.35, attack=0.01, release=0.15) * 0.5,
                                _decay(_noise(0.35), 10) * 0.3), 0.35)
    s["flip"] = _to_sound(_concat(_tone("square", 500, 500, 0.03), _tone("square", 750, 750, 0.04, release=0.03)), 0.2)
    s["swoop"] = _to_sound(_envelope(_lowpass(_noise(0.3), 3), 0.1, 0.15) + _tone("sine", 900, 300, 0.3, 0.05, 0.1) * 0.3, 0.4)
    s["reverse"] = _to_sound(_tone("saw", 300, 900, 0.18, vibrato=60, vib_rate=15) + _tone("saw", 900, 300, 0.18) * 0.5, 0.3)
    return s


# ------------------------------------------------------------------ music
def _drum_kick():
    return _decay(_tone("sine", 150, 42, 0.22, 0.001, 0.05), 14)


def _drum_hat():
    return _decay(_noise(0.05) - _lowpass(_noise(0.05), 4), 60)


def _drum_snare():
    return _decay(_lowpass(_noise(0.18), 2), 18) * 0.8 + _decay(_tone("tri", 190, 160, 0.18), 20) * 0.4


def _build_track(bpm, chords, bass_pattern, arp_pattern, drums, lead=None, bars_per_chord=1,
                 pad=True, arp_wave="tri", swing=0.0):
    """A small sequencer: chords, bass, arpeggio, drums, optional lead melody."""
    beat = 60.0 / bpm
    bar = beat * 4
    total_bars = len(chords) * bars_per_chord
    out = np.zeros(int(RATE * bar * total_bars) + RATE)
    step = beat / 4  # 16th notes
    kick, hat, snare = _drum_kick(), _drum_hat(), _drum_snare()

    for bar_index in range(total_bars):
        chord = chords[bar_index // bars_per_chord]
        root = _note(chord[0])
        bar_start = bar_index * bar
        if pad:
            for n in chord:
                tone = _tone("saw", _note(n) / 2, _note(n) / 2, bar, attack=0.3, release=0.4)
                _mix_into(out, _lowpass(tone, 18), int(RATE * bar_start), 0.05)
        for i, hit in enumerate(bass_pattern):
            if hit:
                mult = hit if isinstance(hit, float) else 1.0
                t0 = bar_start + i * step
                tone = _tone("square", root / 4 * mult, root / 4 * mult, step * 1.8, 0.003, 0.03)
                _mix_into(out, _lowpass(tone, 5), int(RATE * t0), 0.22)
        for i, idx in enumerate(arp_pattern):
            if idx is None:
                continue
            note_freq = _note(chord[idx % len(chord)]) * (2 if idx >= len(chord) else 1)
            t0 = bar_start + i * step + (swing * step if i % 2 else 0)
            tone = _decay(_tone(arp_wave, note_freq, note_freq, step * 1.6, 0.002, 0.04), 8)
            _mix_into(out, tone, int(RATE * t0), 0.09)
        for i, ch in enumerate(drums):
            t0 = int(RATE * (bar_start + i * step))
            if ch == "k":
                _mix_into(out, kick, t0, 0.5)
            elif ch == "s":
                _mix_into(out, snare, t0, 0.28)
            elif ch == "h":
                _mix_into(out, hat, t0, 0.12)
            elif ch == "x":
                _mix_into(out, kick, t0, 0.5)
                _mix_into(out, hat, t0, 0.12)
        if lead:
            notes = lead[bar_index % len(lead)]
            for i, n in enumerate(notes):
                if n:
                    f = _note(n)
                    t0 = bar_start + i * beat
                    tone = _tone("pulse", f, f, beat * 0.95, 0.01, 0.1, vibrato=3, vib_rate=5)
                    _mix_into(out, _lowpass(tone, 3), int(RATE * t0), 0.07)

    loop_len = int(RATE * bar * total_bars)
    # fold the tail back to the start so the loop is seamless
    tail = out[loop_len:]
    out = out[:loop_len]
    out[: len(tail)] += tail
    return out


def _build_music():
    tracks = {}
    # Title: slow and ominous
    tracks["menu"] = _build_track(
        bpm=78,
        chords=[("A3", "C4", "E4"), ("F3", "A3", "C4"), ("D3", "F3", "A3"), ("E3", "G#3", "B3")],
        bass_pattern=[1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        arp_pattern=[0, None, 1, None, 2, None, 3, None, 2, None, 1, None, 0, None, 1, None],
        drums="k" + "." * 7 + "s" + "." * 7,
        bars_per_chord=2, arp_wave="sine")
    # Gameplay: driving, a little mocking
    tracks["game"] = _build_track(
        bpm=132,
        chords=[("A3", "C4", "E4"), ("F3", "A3", "C4"), ("C3", "E3", "G3"), ("G3", "B3", "D4")],
        bass_pattern=[1, 0, 1, 0, 1, 0, 1, 2.0, 1, 0, 1, 0, 1, 0, 2.0, 1],
        arp_pattern=[0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 4, 3, 2, 1, 2, 3],
        drums="x.h.s.h.x.hks.hh",
        lead=[["E5", None, "C5", "D5"], ["C5", None, "A4", None], ["G4", "C5", "E5", None], ["D5", None, "B4", None]],
        bars_per_chord=2)
    # Final world: faster, darker
    tracks["abyss"] = _build_track(
        bpm=148,
        chords=[("D3", "F3", "A3"), ("A#2", "D3", "F3"), ("C3", "E3", "G3"), ("A2", "C#3", "E3")],
        bass_pattern=[1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 2.0, 0, 1, 0],
        arp_pattern=[0, 2, 1, 3, 0, 2, 1, 3, 4, 2, 3, 1, 2, 0, 1, None],
        drums="x.hkx.h.s.hkx.sh",
        lead=[["A5", "F5", None, "D5"], ["F5", None, "D5", "A#4"], ["G5", "E5", None, "C5"], ["E5", "C#5", "A4", None]],
        bars_per_chord=2, arp_wave="square")
    # Act II: fast and relentless
    tracks["gauntlet"] = _build_track(
        bpm=162,
        chords=[("E3", "G3", "B3"), ("C3", "E3", "G3"), ("D3", "F#3", "A3"), ("B2", "D#3", "F#3")],
        bass_pattern=[1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 2.0, 1],
        arp_pattern=[0, 1, 2, 4, 2, 1, 0, 2, 1, 3, 2, 4, 3, 2, 1, 0],
        drums="x.hks.hkx.hks.sh",
        lead=[["B4", "E5", "G5", "F#5"], ["E5", None, "C5", "E5"], ["F#5", "A5", "F#5", "D5"], ["D#5", None, "B4", None]],
        bars_per_chord=2, arp_wave="square")
    # Act III: slow, tense, lonely
    tracks["climb"] = _build_track(
        bpm=92,
        chords=[("D3", "F3", "A3"), ("A#2", "D3", "F3"), ("G2", "A#2", "D3"), ("A2", "C#3", "E3")],
        bass_pattern=[1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        arp_pattern=[0, None, 2, None, 4, None, 2, None, 1, None, 3, None, 5, None, 3, None],
        drums="k.......s...k.h.",
        lead=[["A4", None, None, "D5"], ["F5", None, "E5", None], ["D5", None, None, "A#4"], ["C#5", None, "E5", None]],
        bars_per_chord=2, arp_wave="sine")
    return tracks


# ------------------------------------------------------------------ public manager
class AudioManager:
    """Plays sound effects and loops music, respecting the volume settings."""

    def __init__(self, settings):
        self.settings = settings
        self.sounds = {}
        self.music = {}
        self.current_track = None
        self.enabled = np is not None and pygame.mixer.get_init() is not None
        if not self.enabled:
            print("[audio] numpy or mixer unavailable - running without sound.")
            return
        pygame.mixer.set_num_channels(32)
        pygame.mixer.set_reserved(1)
        self.music_channel = pygame.mixer.Channel(0)
        np.random.seed(7)
        self.sounds = _build_sfx()
        self.music = {name: _to_sound(data, 0.8) for name, data in _build_music().items()}

    def _sfx_volume(self):
        return self.settings["master_volume"] * self.settings["sfx_volume"]

    def play(self, name, volume=1.0, pitch_jitter=False):
        if not self.enabled or name not in self.sounds:
            return
        sound = self.sounds[name]
        channel = sound.play()
        if channel:
            v = self._sfx_volume() * volume
            if pitch_jitter:
                v *= random.uniform(0.85, 1.0)
            channel.set_volume(v)

    def play_music(self, name, fade_ms=900):
        if not self.enabled or name == self.current_track or name not in self.music:
            return
        self.current_track = name
        self.music_channel.fadeout(300)
        self.music_channel.play(self.music[name], loops=-1, fade_ms=fade_ms)
        self.update_volumes()

    def stop_music(self, fade_ms=600):
        if self.enabled:
            self.music_channel.fadeout(fade_ms)
            self.current_track = None

    def duck_music(self, amount):
        """Temporarily lower the music (used by the pause menu)."""
        if self.enabled:
            self.music_channel.set_volume(self.settings["master_volume"] * self.settings["music_volume"] * amount)

    def update_volumes(self):
        if self.enabled:
            self.music_channel.set_volume(self.settings["master_volume"] * self.settings["music_volume"])
