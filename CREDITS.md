# Credits

This file lists every third-party asset, code source and dataset this project uses: where it
came from, its license, and where it's used. Add a row in the same commit that brings the asset in.

## Code and game data

| What | Source | License | Used for |
|---|---|---|---|
| OpenTyrian | https://github.com/opentyrian/opentyrian | GPL-2.0-or-later | Reference for porting game logic and data formats |
| DOSBox OPL2/OPL3 emulator (via OpenTyrian `opl.c`, based on Ken Silverman's ADLIBEMU.C) | https://github.com/opentyrian/opentyrian/blob/master/src/opl.c | LGPL-2.1-or-later | Ported to `src/audio/opl.ts` for music playback |
| Loudness (LDS) player (via OpenTyrian `lds_play.c`, adapted from AdPlug) | https://github.com/opentyrian/opentyrian/blob/master/src/lds_play.c | GPL-2.0-or-later | Ported to `src/audio/lds.ts` for music playback |
| MMPX pixel-art magnification (Morgan McGuire and Mara Gagiu, JCGT 2021; `js-demo.html` in the paper's supplement) | https://casual-effects.com/research/McGuire2021PixelArt/ | MIT | Ported to `src/render/remaster/mmpx.ts` for the remastered ground (DECISIONS.md D34) |
| Tyrian 2.1 game data | https://camanis.net/tyrian/tyrian21.zip (the mirror OpenTyrian links to) | Freeware (not redistributed here; see README) | Level, item, enemy and shape data loaded at runtime |

## Fonts

| Font | Source URL | Author | License | Used in |
|---|---|---|---|---|
| Orbitron | https://fonts.google.com/specimen/Orbitron | Matt McInerney (The Orbitron Project Authors) | SIL Open Font License 1.1 | Titles, labels and buttons of the interface (`src/ui/tokens.css`), loaded from Google Fonts |
| Exo 2 | https://fonts.google.com/specimen/Exo+2 | Natanael Gama (The Exo 2 Project Authors) | SIL Open Font License 1.1 | Body text of the interface (`src/ui/tokens.css`), loaded from Google Fonts |

## 3D models, textures and HDRIs

Models built from this project's own scripts in `assets/blender/` don't need a row here. List
anything imported from outside, such as Poly Haven textures or HDRIs.

| Asset | Source URL | Author | License | Used in |
|---|---|---|---|---|
| Tyrian ship and tile graphics (the art the models in `assets/blender/` reproduce) | https://lostgarden.com/2007/04/05/free-game-graphics-tyrian-ships-and-tiles/ | Daniel Cook | Free to use in games ("use and abuse them as desired"); link back requested | Every model in `public/models/` is a 3D version of one of these sprites or tiles |
| Concept images of models (`assets/blender/features/concepts/`) | Generated with Google Gemini (Nano Banana) from the sprites above; two supplied by the project's author | Based on Daniel Cook's Tyrian art | As the art they're based on | Design references for the Blender models; not shipped in the game |

## Audio

| Asset | Source URL | Author | License | Used in |
|---|---|---|---|---|
