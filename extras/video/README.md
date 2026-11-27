# Trampo intro video

A short launch film for Trampo: 148 seconds, 1920x1080, 30 fps, narrated, with an original soundtrack. It is
written for readers who are not engineers, such as a chief executive watching it from an email. Ten scenes: big AI
tools give you pieces, not a way of working, and what the AI learns gets lost; Trampo is a toolbox the team builds from the tools it already has, starting small and growing; a tech
lead maps how the team works on one project; the whole team works through it and each piece of work teaches people
and the agent; nothing starts until you say yes and nothing is done until an independent check passes; lessons build
one shared memory, from one file to topics to playbooks, and each new skill shows more of the system; it compounds, and anything spotted on the way is recorded,
with urgent items going to a person; the history keeps the why, so knowledge stays when someone leaves; a real team's seven
weeks as charts, quality then speed; and where it ends up, with how to start. The finished
file is published as a release asset, not kept in git.

## Rebuild it

You need Node 20 or later, Python 3 with numpy, and ffmpeg with libx264. The voice is committed, so the build needs
no speech model. From a clean clone:

```bash
cd extras/video && npm ci && npm run build
```

That runs the check, synthesises and masters the music into `public/music.wav`, renders the video with the music and
the voice mixed in (the music drops under the voice), brings the mix to -16 LUFS and writes `out/trampo-intro.mp4`
and `out/intro-poster.png`.

## Publish a new cut

1. Upload the full-size file to the release: `gh release upload video-1 out/trampo-intro.mp4 --clobber`.
2. Make a copy under 10 MB for the inline player:
   `ffmpeg -i out/trampo-intro.mp4 -vf scale=-2:720 -c:v libx264 -crf 28 -preset slow -c:a aac -b:a 128k out/trampo-intro-720p.mp4`.
3. Drag that copy into the GitHub web editor of any file, copy the `github.com/user-attachments/assets/...` link it
   inserts, and cancel the edit. Only the web editor makes these links; the API and `gh` cannot.
4. Put the new link on its own line near the top of the top-level `README.md`, in place of the old one.

## Where the numbers come from

Every number on screen is in `RESULTS` in `src/intro-data.ts`, and every spoken line is in `src/narration.json`. Both
are held to the "Measured on the reference system" section of the top-level `README.md`. `npm run check`, which the
build runs first, fails when the video shows or says a number that section does not have, or when an on-screen string
outside `RESULTS` carries a digit and is not listed in `NOT_MEASUREMENTS`. Change the README first, then the video.

The check also fails when on-screen or spoken text uses a word in `JARGON` (card, runbook, QA, ledger, session and
others) or in `ALARM` (words that make ordinary work sound like a security story): the film uses plain words such as
"a piece of work", "playbook", "an independent check" and "record" instead.

## Edit a scene

- Words on screen: `src/intro-data.ts`. All displayed text is there, so the check sees it.
- Words spoken: `src/narration.json`, one entry per line, in the order the scene shows them. `READ` in
  `src/intro-data.ts` pairs each spoken line with what is on screen while it plays.
- Layout and motion: `src/Intro.tsx`, one component per scene, registered in `PARTS` at the bottom. Each scene
  reveals its pictures at the frames `cues()` returns, which is where each spoken line starts.
- Timing: `src/grid.json`. It holds the tempo and the bars of every scene and every music section. The music script
  reads the same file, so cuts stay on bar lines. The check fails when the scenes do not tile the video, when a music
  lift no longer starts with its scene, or when a scene is too short for its voice: a line holds the screen for as
  long as it takes to say plus 0.6 s, or 0.3 s a word plus 1 s to read, whichever is longer.
- Preview while editing: `npx remotion studio src/index.ts` (run the build once first, so `public/music.wav` exists).

## The voice

The narration is spoken by Kokoro-82M, an open-weight speech model, run locally. Model: `hexgrad/Kokoro-82M` at
commit `f3ff3571791e39611d31c381e3a41a3af07b4987`, with the `kokoro` Python package 0.9.4. Weights and code are both
Apache-2.0. Voice: `af_heart` (American English), at speed 1.0. No hosted speech service is used.

`scripts/voice.py` writes one clip per spoken line to `public/voice/<scene>-<n>.mp3` and the length of each to
`src/voice.json`; both are committed. After changing `src/narration.json`, regenerate them with a Python 3.12
environment outside the repository:

```bash
uv venv --python 3.12 ../../../tts-venv
VIRTUAL_ENV=../../../tts-venv uv pip install kokoro==0.9.4 soundfile \
  "en_core_web_sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"
../../../tts-venv/bin/python scripts/voice.py
npm run check
```

To respeak only some scenes, name them: `../../../tts-venv/bin/python scripts/voice.py results`. The first run downloads the model from Hugging Face. If the check says a scene is too short, add bars to it in
`src/grid.json`.

The product name is `NAME` in `src/intro-data.ts`, used on screen and in the voice (`narration.json` writes it as
`{name}`). After changing it, respeak the scenes that say it: `../../../tts-venv/bin/python scripts/voice.py turn end`.

## The music

`scripts/music.py` synthesises the soundtrack with numpy: pads, bass, soft drums, a delayed arpeggio and reverb, at
the tempo in `grid.json`. It is original and uses no samples, so it needs no licence. `scripts/master.py` brings it
to -16 LUFS with a true peak of -1.5 dBTP. `scripts/analyse_audio.py out/music.wav` prints clipping, band levels per
section and the level of each bar, for checking a change without listening.

## Remotion licence

The video is rendered with Remotion, which has its own licence, separate from this repository's. Remotion is free
for individuals and for companies of up to 3 people. Larger companies need a company licence to render it. See
https://www.remotion.dev/license.
