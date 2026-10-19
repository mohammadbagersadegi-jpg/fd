# NEON GAUNTLET - Intro Cinematic Storyboard

* Duration: **12.0 s** (within the 10-15 s target), 4 shots, hard cuts with a 0.18 s dip-to-black.
* Rendering: `game/src/cinematic.js` - the same code draws it in-engine and offline.
* Offline render: `node tools/capture/movie.js cinematic` -> `artifacts/video/cinematic.mp4` (1440x810, 30 fps, H.264).
* In-engine: plays automatically when the player presses ENTER on the title screen (skippable with ENTER).
* No AI image models were used; every pixel is drawn from the project's own rig, stage layers and 5x7 font.

| Shot | Time | Framing / camera | Subject and action | Type | Transition |
|---|---|---|---|---|---|
| 1 | 0.0 - 3.0 s | Wide, static; slow parallax drift | The rain district at night: skyline, wet street, rain, two lightning flashes at 1.55 s and 2.28 s. Title type "RAIN DISTRICT" tracks in with a cyan rule, caption "BLOCK 07 / 23:48". | 2x scale pixel type | dip to black |
| 2 | 3.0 - 6.2 s | Ground-level tracking shot, camera slides right 46 px/s | VOLT walks in from the left, 2.1x scale, with a mirrored reflection on the wet ground. A pink "RUSTLINE" sign flickers behind him. Subtitle: "THE RUSTLINE CREW OWNS THIS BLOCK". | subtitle | dip to black |
| 3 | 6.2 - 9.2 s | Slow push-in on a 3/4 close-up, hero at 3.15-3.5x | VOLT charges the gauntlet: electric arcs at 18 Hz, teal light pool, breathing rain. Name card "VOLT / ELECTRIC GAUNTLET". Subtitle: "ONE SPARK IS ALL IT TAKES". | name card | dip to black |
| 4 | 9.2 - 12.0 s | Static wide, goons advance from 0.0-2.0 s | Three RIVET silhouettes step out of the rain (brightness 0.4), the middle one's visor glows red. VOLT stands in the foreground with the gauntlet sparking. At 1.1 s the title plate slams in: "NEON GAUNTLET", "A TRIBUTE TO STREETS OF RAGE". End fade 0.5 s. | title slam (scale 4.4 -> 2) | fade out |

## Audio

The cinematic is rendered silent (H.264, no audio track) on purpose: the browser game mixes its own procedural soundtrack and rain bed, and an MP4 audio track would fight it. `artifacts/video/cinematic.mp4` is video-only; `game/index.html` plays the engine version with live audio.

## Visual rules

* One palette for the whole film: indigo night + cyan neon + pink signage + copper accents (no blue/purple gradients beyond the stage's own sky).
* The letterbox (26 px top/bottom) is always present; no shot is full-bleed.
* Text never overlaps a face; the name card sits opposite the hero.
* Every shot has motion inside the frame (rain, parallax, walk cycle, arcs, advancing goons), not just a zoom.
