# Cinematic

| File | What it is |
|---|---|
| `storyboard.md` | shot list with timings, camera, action and type |
| `spec.json` | machine-readable description of the same |
| `rendered-video.mp4` | rendered 12 s film (1440x810, 30 fps, H.264, no audio) - identical copy of `../artifacts/video/cinematic.mp4` |
| `../artifacts/video/gameplay.mp4` | 49.7 s autopilot playthrough of stage 1 (proof of playability) |
| `../game/src/cinematic.js` | the drawing code - single source of truth |
| `../tools/capture/movie.js` | offline renderer (Node canvas -> ffmpeg) |
| `../game/watch.html` | browser page that plays the MP4 |

Regenerate:

```bash
node tools/capture/movie.js cinematic   # 12 s film
node tools/capture/movie.js gameplay    # full stage playthrough
node tools/capture/movie.js all
```

The film is **not** required to boot the game. The game has its own engine-side
playback of the exact same shots, so the cinematic works even when the MP4 cannot
be played by the browser.
