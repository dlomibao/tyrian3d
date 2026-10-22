# Credits

This file lists every third-party asset, code source and dataset this project uses: where it
came from, its license, and where it's used. Add a row in the same commit that brings the asset in.

## Code and game data

| What | Source | License | Used for |
|---|---|---|---|
| OpenTyrian | https://github.com/opentyrian/opentyrian | GPL-2.0-or-later | Reference for porting game logic and data formats |
| DOSBox OPL2/OPL3 emulator (via OpenTyrian `opl.c`, based on Ken Silverman's ADLIBEMU.C) | https://github.com/opentyrian/opentyrian/blob/master/src/opl.c | LGPL-2.1-or-later | Ported to `src/audio/opl.ts` for music playback |
| Loudness (LDS) player (via OpenTyrian `lds_play.c`, adapted from AdPlug) | https://github.com/opentyrian/opentyrian/blob/master/src/lds_play.c | GPL-2.0-or-later | Ported to `src/audio/lds.ts` for music playback |
| Tyrian 2.1 game data | https://camanis.net/tyrian/tyrian21.zip (the mirror OpenTyrian links to) | Freeware (not redistributed here; see README) | Level, item, enemy and shape data loaded at runtime |

## 3D models, textures and HDRIs

Models built from this project's own scripts in `assets/blender/` don't need a row here. List
anything imported from outside, such as Poly Haven textures or HDRIs.

| Asset | Source URL | Author | License | Used in |
|---|---|---|---|---|

## Audio

| Asset | Source URL | Author | License | Used in |
|---|---|---|---|---|
