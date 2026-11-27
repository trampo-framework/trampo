# Extras

Material about Trampo that is not part of it. None of it is needed to use Trampo, and nothing in `core/`,
`modules/`, `scripts/` or CI reads it.

| Path | What it is |
| --- | --- |
| [video/](video/README.md) | Source of the intro film: scenes, narration, voice clips, music and the rebuild script. `npm run check` here reads the "Measured on the reference system" section of the top-level README. |
| `intro-poster.png` | A still from the film. |
| [video-storyboard.md](video-storyboard.md) | The plan for a screen recording of the lite setup. |
| `figures/` | `coverage-figures.py` and `throughput-figures.py`, which reproduce the numbers in [Measured results](../docs/wiki/Measured-results.md) from a workspace's history and telemetry. Each has a `--self-test`. |

## Removing it

`git rm -r extras` is safe: the suite and the leak scan pass without it. Three places then point at a missing path:

- `README.md`, the line under the video link that names `extras/video/`.
- `docs/wiki/Home.md`, the Video section, which names `extras/video/`.
- `docs/wiki/Measured-results.md`, the two "To reproduce" lines, which name `extras/figures/`.
