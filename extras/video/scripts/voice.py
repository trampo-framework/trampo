"""Speak src/narration.json with Kokoro-82M into public/voice/*.mp3 and write each clip's length to src/voice.json.

Run with a Python that has kokoro and soundfile installed (see README.md, "The voice"):
  python scripts/voice.py [scene ...]
With scene names it speaks only those scenes and keeps the other clips. The build does not run this: the clips and src/voice.json are committed.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from kokoro import KPipeline

ROOT = Path(__file__).resolve().parent.parent
SR = 24000
NARRATION = json.loads((ROOT / 'src' / 'narration.json').read_text())
NAME = re.search(r"export const NAME = '([^']+)'", (ROOT / 'src' / 'intro-data.ts').read_text()).group(1)
OUT = ROOT / 'public' / 'voice'
OUT.mkdir(parents=True, exist_ok=True)
ONLY = set(sys.argv[1:]) or set(NARRATION['lines'])
for old in OUT.glob('*.mp3'):
    if old.stem.rsplit('-', 1)[0] in ONLY:
        old.unlink()

pipe = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')
LENGTHS = ROOT / 'src' / 'voice.json'
lengths = json.loads(LENGTHS.read_text()) if LENGTHS.exists() else {}
for scene, lines in NARRATION['lines'].items():
    if scene not in ONLY:
        continue
    lengths[scene] = []
    for i, line in enumerate(lines):
        audio = np.concatenate([r.audio.numpy() for r in pipe(line.replace('{name}', NAME), voice=NARRATION['voice'], speed=NARRATION['speed'])])
        loud = np.flatnonzero(np.abs(audio) > 0.01)
        audio = audio[max(0, loud[0] - 240): loud[-1] + 2400]
        audio = audio / np.max(np.abs(audio)) * 0.89
        pcm = (audio * 32767).astype('<i2').tobytes()
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '1', '-i', '-',
                        '-c:a', 'libmp3lame', '-b:a', '96k', str(OUT / f'{scene}-{i}.mp3')], input=pcm, check=True)
        lengths[scene].append(round(len(audio) / SR, 3))
        print(f'{scene}-{i}: {lengths[scene][-1]:.2f} s  {line.replace("{name}", NAME)}')

LENGTHS.write_text(json.dumps({k: lengths[k] for k in NARRATION['lines']}, indent=2) + '\n')
