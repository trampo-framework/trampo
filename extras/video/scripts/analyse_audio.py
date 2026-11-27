"""Levels of a mix, for checking it without listening. Run: python3 -I scripts/analyse_audio.py out/music.wav

Prints clipping, stereo correlation, octave-band levels per music section (relative to the loudest band), and the
RMS of every bar, so a section change can be seen landing on its bar.
"""
import json
import sys
import wave
from pathlib import Path

import numpy as np

grid = json.loads((Path(__file__).resolve().parent.parent / 'src' / 'grid.json').read_text())
bar_s = 4 * 60 / grid['bpm']
w = wave.open(sys.argv[1])
sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), '<i2').reshape(-1, 2).astype(float) / 32768
m = x.mean(1)
print('clipped samples', int((np.abs(x) > 0.999).sum()), ' L/R correlation %.2f' % np.corrcoef(x[:, 0], x[:, 1])[0, 1])
centres = [31, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
print('section     rms dBFS ' + ''.join(f'{c:>7}' for c in centres))
bounds = sorted(grid['music'].items(), key=lambda kv: kv[1])
for (name, a), (_, b) in zip(bounds, bounds[1:]):
    seg = m[int(a * bar_s * sr):int(b * bar_s * sr)]
    S = np.abs(np.fft.rfft(seg)) ** 2
    f = np.fft.rfftfreq(len(seg), 1 / sr)
    lv = [10 * np.log10(S[(f >= c / 1.414) & (f < c * 1.414)].sum() + 1e-9) for c in centres]
    rms = 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-12)
    print(f'{name:10s} {rms:8.1f} ' + ''.join(f'{v - max(lv):7.1f}' for v in lv))
step = int(bar_s * sr)
print('bar rms: ' + ' '.join(f'{i}:{20 * np.log10(np.sqrt((m[i * step:(i + 1) * step] ** 2).mean()) + 1e-9):.0f}' for i in range(grid['bars'])))
