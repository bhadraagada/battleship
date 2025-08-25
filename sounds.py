import io
import math
import os
import wave
from array import array
from typing import List, Tuple

import pygame


SAMPLE_RATE = 22050
BITS = 16
CHANNELS = 1


def _tone_samples(freq: float, duration_ms: int, volume: float = 0.5, waveform: str = "sine") -> array:
    n_samples = int(SAMPLE_RATE * duration_ms / 1000)
    data = array("h")
    two_pi_f = 2 * math.pi * freq
    attack = max(1, int(0.01 * n_samples))
    release = max(1, int(0.10 * n_samples))
    sustain_len = max(0, n_samples - attack - release)
    for i in range(n_samples):
        # envelope
        if i < attack:
            env = i / attack
        elif i < attack + sustain_len:
            env = 1.0
        else:
            env = max(0.0, (n_samples - i) / release)

        t = i / SAMPLE_RATE
        if waveform == "square":
            raw = 1.0 if math.sin(two_pi_f * t) >= 0 else -1.0
        elif waveform == "saw":
            # simple sawtooth
            raw = 2.0 * (t * freq - math.floor(0.5 + t * freq))
        else:  # sine
            raw = math.sin(two_pi_f * t)

        val = int(raw * env * volume * ((2 ** (BITS - 1)) - 1))
        data.append(val)
    return data


def _write_wav_bytes(segments: List[Tuple[float, int, float, str]]) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(BITS // 8)
        wf.setframerate(SAMPLE_RATE)
        for freq, ms, vol, wave_name in segments:
            samples = _tone_samples(freq, ms, vol, wave_name)
            wf.writeframes(samples.tobytes())
    return buf.getvalue()


def _ensure_file(path: str, segments: List[Tuple[float, int, float, str]]):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = _write_wav_bytes(segments)
        with open(path, "wb") as f:
            f.write(data)


def ensure_sounds(base: str = "assets"):
    # UI click
    _ensure_file(
        os.path.join(base, "click.wav"),
        [(600, 40, 0.4, "sine"), (800, 35, 0.35, "sine")],
    )
    # Start jingle
    _ensure_file(
        os.path.join(base, "start.wav"),
        [(400, 90, 0.38, "sine"), (520, 90, 0.38, "sine"), (660, 120, 0.34, "sine")],
    )
    # Miss: low soft blip
    _ensure_file(
        os.path.join(base, "miss.wav"),
        [(260, 120, 0.32, "sine")],
    )
    # Hit: sharp high tone
    _ensure_file(
        os.path.join(base, "hit.wav"),
        [(900, 70, 0.45, "square"), (700, 60, 0.35, "sine")],
    )
    # Sunk: descending triad
    _ensure_file(
        os.path.join(base, "sunk.wav"),
        [(700, 120, 0.5, "sine"), (560, 120, 0.45, "sine"), (420, 160, 0.42, "sine")],
    )


def load_sounds(base: str = "assets") -> dict:
    ensure_sounds(base)
    return {
        "click": pygame.mixer.Sound(os.path.join(base, "click.wav")),
        "start": pygame.mixer.Sound(os.path.join(base, "start.wav")),
        "miss": pygame.mixer.Sound(os.path.join(base, "miss.wav")),
        "hit": pygame.mixer.Sound(os.path.join(base, "hit.wav")),
        "sunk": pygame.mixer.Sound(os.path.join(base, "sunk.wav")),
    }

