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
| Remastered shot and pickup sprites (`public/art/sprites/`) | Generated with Google Gemini (Nano Banana) from input sheets of Tyrian's original sprites, cut and fitted with `tools/flat_art.py` (DECISIONS.md D43) | Based on Tyrian's sprite art (Daniel Cook) | As the art they're based on | Drawn flat in game in place of the original shot and pickup sprites (D42) |
| Concept images of models (`assets/blender/features/concepts/`) | Generated with Google Gemini (Nano Banana) from the sprites above; two supplied by the project's author | Based on Daniel Cook's Tyrian art | As the art they're based on | Design references for the Blender models; not shipped in the game |

## Audio

| Asset | Source URL | Author | License | Used in |
|---|---|---|---|---|
| Tyrian soundtrack (the compositions the remastered music arranges) | https://alexanderbrandon.bandcamp.com/ ; https://www.materiacollective.com/music/tyrian-original-game-soundtrack | Alexander Brandon, with additional music by Andreas Molnar ("ZANAC3" and "ZANAC5" reproduce music from Compile's *Zanac*) | Theirs; the arrangements here are covers | `public/tyrian-remaster/`: orchestral and synth arrangements of all 41 songs, made for this project |
| Orchestral samples used to render the orchestral arrangements | https://github.com/sgossner/VSCO-2-CE , https://github.com/sgossner/VCSL | Versilian Studios (Sam Gossner) | CC0 | `public/tyrian-remaster/orchestral/` |
| Remade sound effects and voices (`public/tyrian-remaster/sfx/`) | Made for this project in the tyrian3d-remaster repo | Based on Tyrian's original sound effects and voices (Eclipse Productions; published by Epic MegaGames, 1995), resynthesized; three layer CC0 VSCO-2-CE percussion samples | This project's; the originals are their authors' | The Sound style "remaster" (Options, `?sound=remaster`) |
| sfizz (renders the sample instruments) | https://github.com/sfztools/sfizz | sfizz contributors | BSD-2-Clause | Rendering the orchestral arrangements (not shipped) |
