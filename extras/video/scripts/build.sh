#!/usr/bin/env bash
# Rebuild the intro from source: check, synthesise and master the music, render with the committed voice, poster.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p out public
npm run check
python3 -I scripts/music.py out/music-raw.wav
python3 -I scripts/master.py out/music-raw.wav public/music.wav
npx remotion render src/index.ts TrampoIntro out/intro-mixed.mp4 --codec=h264 --crf=18 --log=error
ffmpeg -loglevel error -y -i out/intro-mixed.mp4 -c:v copy -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 48000 -c:a aac -b:a 192k out/trampo-intro.mp4
rm out/intro-mixed.mp4
npx remotion still src/index.ts TrampoIntro out/intro-poster.png --frame=540 --log=error
echo "built out/trampo-intro.mp4 and out/intro-poster.png"
