"""Original track for the Trampo intro. Run: python3 -I scripts/music.py out/music-raw.wav

Synthesised from nothing but numpy, so there is no sample or licence behind it. The tempo, the length and every
section boundary come from src/grid.json, the same file the video reads, so a cut always lands on a bar line.
"""
import json
import sys
import wave
from pathlib import Path

import numpy as np

GRID = json.loads((Path(__file__).resolve().parent.parent / 'src' / 'grid.json').read_text())
M = GRID['music']
SR = 44100
BEAT = 60 / GRID['bpm']
BAR = 4 * BEAT
BARS = GRID['bars']
N = int(BARS * BAR * SR) + SR * 3
rng = np.random.default_rng(7)

LIFTS = [(M['liftA'], M['break']), (M['liftB'], M['groove']), (M['liftC'], M['outro'])]

# Cmaj9, Am9, Fmaj9, G6/9: one chord per bar, a four-bar loop. MIDI notes.
CHORDS = [
    (48, [60, 64, 67, 71, 74]),
    (45, [57, 60, 64, 67, 71]),
    (41, [57, 60, 64, 65, 69]),
    (43, [59, 62, 64, 67, 69]),
]


def section(bar):
    if bar < M['build']:
        return 'intro'
    if any(a <= bar < b for a, b in LIFTS):
        return 'lift'
    if M['break'] <= bar < M['liftB']:
        return 'break'
    if M['groove'] <= bar < M['liftC']:
        return 'groove'
    if bar >= M['outro']:
        return 'outro'
    return 'build'


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def t_of(bar, beat=0.0):
    return int((bar * BAR + beat * BEAT) * SR)


def env_adsr(n, a, d, s, r_len):
    a, d = max(1, int(a * SR)), max(1, int(d * SR))
    e = np.full(n, s, dtype=np.float64)
    e[:a] = np.linspace(0, 1, a)
    e[a:a + d] = np.linspace(1, s, len(e[a:a + d]))
    r = min(n, int(r_len * SR))
    e[n - r:] *= np.linspace(1, 0, r)
    return e


def soft_saw(f, n, harmonics, tilt, detune_cents, phase):
    t = np.arange(n) / SR
    f = f * 2 ** (detune_cents / 1200)
    out = np.zeros(n)
    for k in range(1, harmonics + 1):
        if f * k > 9000:
            break
        out += np.sin(2 * np.pi * f * k * t + phase * k) / k ** tilt
    return out


def add(buf, start, sig, gain=1.0):
    end = min(len(buf), start + len(sig))
    if end > start:
        buf[start:end] += sig[: end - start] * gain


L = np.zeros(N)
R = np.zeros(N)
drums = np.zeros(N)
kick_env = np.zeros(N)

PAD_LEVEL = {'intro': 0.08, 'build': 0.09, 'lift': 0.085, 'break': 0.1, 'groove': 0.09, 'outro': 0.09}
for bar in range(BARS):
    _, notes = CHORDS[bar % 4]
    n = int(BAR * SR) + int(1.2 * SR)
    lvl = PAD_LEVEL[section(bar)]
    e = env_adsr(n, 0.6, 0.8, 0.8, 1.4)
    for m in notes:
        for d, side in ((-9, 'L'), (0, 'C'), (8, 'R')):
            s = soft_saw(hz(m), n, 16, 1.25, d, rng.uniform(0, 6.28)) * e * lvl / len(notes)
            if side in 'LC':
                add(L, t_of(bar), s, 1.0 if side == 'L' else 0.7)
            if side in 'RC':
                add(R, t_of(bar), s, 1.0 if side == 'R' else 0.7)


def kick(bar, beat, g=1.0):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 46 + 80 * np.exp(-t * 28)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7.5)
    s[: int(0.003 * SR)] *= np.linspace(0, 1, int(0.003 * SR))
    add(drums, t_of(bar, beat), s, 0.36 * g)
    add(kick_env, t_of(bar, beat), -0.55 * np.exp(-t * 9))


def hat(bar, beat, decay, g):
    n = int(0.06 * SR)
    x = np.diff(np.diff(rng.standard_normal(n), prepend=0.0), prepend=0.0)
    x /= np.max(np.abs(x)) + 1e-9
    add(drums, t_of(bar, beat), x * np.exp(-np.arange(n) / SR * decay), g)


def clap(bar, beat, g):
    n = int(0.3 * SR)
    x = np.diff(np.convolve(rng.standard_normal(n), np.ones(6) / 6, mode='same'), prepend=0.0)
    x /= np.max(np.abs(x)) + 1e-9
    t = np.arange(n) / SR
    e = np.exp(-t * 18)
    for off in (0.0, 0.011, 0.022):
        e = e + 0.6 * np.exp(-np.clip(t - off, 0, None) * 120) * (t >= off)
    add(drums, t_of(bar, beat), x * e / 2.2, g)


for bar in range(BARS):
    sec = section(bar)
    if sec == 'build':
        kick(bar, 0, 0.7)
        kick(bar, 2, 0.7)
        for b in range(8):
            hat(bar, b / 2, 70, 0.05 if b % 2 else 0.03)
    elif sec == 'lift':
        for b in range(4):
            kick(bar, b)
        for b in (1, 3):
            clap(bar, b, 0.22)
        for b in range(8):
            hat(bar, b / 2, 55 if b % 2 else 90, 0.09 if b % 2 else 0.05)
    elif sec == 'groove':
        kick(bar, 0, 0.85)
        kick(bar, 2, 0.85)
        kick(bar, 2.5, 0.45)
        clap(bar, 3, 0.15)
        for b in range(8):
            hat(bar, b / 2, 65, 0.07 if b % 2 else 0.04)
    elif sec == 'break':
        for b in range(4):
            hat(bar, b + 0.5, 60, 0.06)
        if bar % 2:
            kick(bar, 0, 0.5)
    elif sec == 'outro' and bar < BARS - 2:
        kick(bar, 0, 0.6)
        kick(bar, 2, 0.6)
        for b in range(8):
            hat(bar, b / 2, 70, 0.045)

bass = np.zeros(N)
for bar in range(M['build'], BARS - 2):
    sec = section(bar)
    root, _ = CHORDS[bar % 4]
    f = hz(root - 12 if root > 44 else root)
    busy = sec in ('lift', 'groove')
    pattern = [(0, 0.45), (1.5, 0.4), (2.5, 0.4), (3, 0.3), (3.5, 0.4)] if busy else [(0, 0.9), (2, 0.9)]
    for beat, dur in pattern:
        n = int(dur * SR)
        t = np.arange(n) / SR
        s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t) + 0.08 * np.sin(6 * np.pi * f * t)
        add(bass, t_of(bar, beat), s * env_adsr(n, 0.008, 0.15, 0.7, 0.06), 0.07 if sec == 'break' else 0.10)

pl_l = np.zeros(N)
pl_r = np.zeros(N)
for bar in range(M['liftA'], BARS - 4):
    sec = section(bar)
    if sec == 'break':
        continue
    steps = 16 if sec == 'lift' else 8
    _, notes = CHORDS[bar % 4]
    seq = [notes[i] + 12 for i in (0, 2, 1, 3, 2, 4, 3, 1)]
    for i in range(steps):
        if steps == 16 and i % 4 == 3 and bar % 2:
            continue
        m = seq[i % 8]
        n = int(0.35 * SR)
        t = np.arange(n) / SR
        s = (np.sin(2 * np.pi * hz(m) * t)
             + (0.45 * np.sin(4 * np.pi * hz(m) * t) + 0.2 * np.sin(6 * np.pi * hz(m) * t)) * np.exp(-t * 18)) * np.exp(-t * 9)
        s[:40] *= np.linspace(0, 1, 40)
        g = 0.07 if sec == 'lift' else 0.055
        pan = 0.5 + 0.3 * np.sin(i)
        beat = i / 4 if steps == 16 else i / 2
        add(pl_l, t_of(bar, beat), s, g * (1 - pan) * 2)
        add(pl_r, t_of(bar, beat), s, g * pan * 2)

dly = int(0.375 * SR)
dl, dr = pl_l.copy(), pl_r.copy()
for k in range(1, 6):
    src_l, src_r = (pl_r, pl_l) if k % 2 else (pl_l, pl_r)
    dl[k * dly:] += src_l[: N - k * dly] * 0.42 ** k
    dr[k * dly:] += src_r[: N - k * dly] * 0.42 ** k

for lift, _ in LIFTS:
    n = int(BAR * SR)
    s = np.diff(rng.standard_normal(n), prepend=0.0) / 4 * np.linspace(0, 1, n) ** 2.5 * 0.05
    add(L, t_of(lift - 1), s)
    add(R, t_of(lift - 1), s)

duck = 1 + np.clip(kick_env, -0.6, 0)
L = L * duck + bass * duck + dl
R = R * duck + bass * duck + dr


def reverb(x, seed, seconds=2.6, mix=0.22):
    n = int(seconds * SR)
    r = np.random.default_rng(seed).standard_normal(n) * np.exp(-np.arange(n) / SR * (6.9 / seconds))
    r = np.convolve(r, np.ones(8) / 8, mode='same')
    r /= np.sqrt(np.sum(r ** 2))
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(r, size), size)[: len(x)]
    return x * (1 - mix) + wet * mix


L = reverb(L + drums * 0.35, 1) + drums * 0.75
R = reverb(R + drums * 0.35, 2) + drums * 0.75

total = int(BARS * BAR * SR)
g = np.ones(N)
fade_in = t_of(2)
g[:fade_in] = np.linspace(0, 1, fade_in) ** 1.5
fade_out = t_of(BARS - 4)
g[fade_out:total] = np.linspace(1, 0, total - fade_out) ** 1.3
g[total:] = 0
L, R = L * g, R * g
peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
L, R = np.tanh(L / peak * 1.1) * 0.85, np.tanh(R / peak * 1.1) * 0.85

pcm = (np.clip(np.stack([L[:total], R[:total]], axis=1), -1, 1) * 32767).astype('<i2')
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print(f'wrote {sys.argv[1]}: {total / SR:.2f} s, {BARS} bars at {GRID["bpm"]} BPM')
