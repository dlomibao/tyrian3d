# Damaged frames

**Decided (D87, 2026-11-03):** the user picked approach D from the proposal on this branch (PR #104):
- **A** for every damaged frame: the enemy's intact model, damaged at runtime by the difference
  between its intact and damaged sprite frames;
- **C**, a model of its own, only where A can't show the frame.

Approach B (generic noise damage and smoke) was dropped.

## For agents: a new enemy with damaged frames

Normally **nothing to do**. Model the intact frames as usual. When the enemy is hit hard enough
and the game swaps it to a damaged frame (`dgr`/`dani` in the enemy data), the renderer draws that
frame with the intact model. That frame is then:
- cut away where the damaged sprite lost pixels;
- tinted, scorched and glowing where it changed them.

No bake, no data, no script.

Check it in the game with `?debug=play&hurt=1`: every enemy that has a damaged look takes it at its
next hit. Compare with `&damage=off` (the extruded sprite, as before D87).

Make a model of the damaged frame itself (C) only if it fails review the way the boss's arm wrecks
did: the damaged frame is mostly a different picture, debris instead of the piece. A cut and repaint
of the intact model then reads as the intact piece, burning. To build one:
1. Build it like `assets/blender/enemies/assembly-newsh4-124-damaged.py`: the intact build, cut and
   relieved by the pixel difference.
2. Export it with its own `spriteModels/*.json` for the damaged frame. A damaged frame with a model
   of its own always uses it.
3. Add a row to the table below.

Blank damaged frames (a destroyed piece) draw nothing; no model is needed.

## How A works

| Part | File | What it does |
|---|---|---|
| Routing | `src/render/damage/damageRoute.ts`, `Sprite2Router.route` | The level's damaged frames come from the enemy data (`sim/levelSprites.ts` `levelDamageFrames`). A damaged frame without a model of its own goes to the intact model of the enemy's best-matching intact frame. The renderer and `tests/render/modelSwap.test.ts` share this routing. |
| Textures | `damageFrames.ts` | Three 24x28 (or 12x14) textures per damaged frame, built from the sheet's pixels and the live palette the first time it's drawn. **mask:** cut, darker, hot, changed. **tint:** damaged ÷ intact colour, plus how much to replace outright where no multiplier reaches, such as rock turning into a blue pool. **paint:** the damaged colours. |
| Shader | `damageShader.ts` | Patches the clone's materials. Each fragment is projected straight down onto the sprite. **Cut:** a discard with a charred, glowing rim. While anything is cut, the materials are two-sided and the inside is drawn charred, so a cut reads as a burnt-through wall in Tilted and Steep. **Paint and scorch:** full on faces that look up, a third on vertical faces, so the top-down projection doesn't streak down the sides. **Glow:** glowing parts dim and recolour. |
| Outline | `src/render/outlineEffect.js` (three.js's OutlineEffect, forked) | Cuts the ink outline the same way, so the outline follows the cut silhouette. |
| Shadows | `damageDepthMaterial` (`customDepthMaterial`) | The same cut in the shadow pass, so cut-away parts cast no shadow. |

## Which frames have a model of their own (C)

| Frame | Enemy | Why |
|---|---|---|
| `newsh4.shp` 240 | level-1 boss, left shoulder (assembly-newsh4-124, piece newsh4-88) → `enemies/newsh4-88-d` | the shoulder becomes a wreck: 30% of the piece gone, 47% of the rest repainted as debris. A reads as the intact shoulder, burning |
| `newsh4.shp` 244 | level-1 boss, right shoulder (newsh4-92) → `enemies/newsh4-92-d` | the same: 23% gone, 47% repainted |

The rock outcrop's shot-away frames (`newshe.shp` 7, 9, 11, 45, 47, 49) also have models of their own,
from D81 (PR #95, merged before this decision); they are kept.

Both boss wrecks are built by `assembly-newsh4-124-damaged.py`, which now exports only these two. Together they
add 0.83 MB. The other ten damaged boss pieces it once exported (2.46 MB in all, with the dome
turret's 0.1 MB) were dropped: A draws those frames.

### A correction to the proposal's census

The proposal said about 2% of damaged frames (3 of 183) "grow a new shape outside the old outline".
That came from pairing each damaged frame with the best-matching frame of its whole unit, which for
multi-piece enemies can be another piece. Paired properly, with the enemy's own intact frames from
the enemy data, as the renderer does:
- no damaged frame in the four episodes adds more than 25% new pixels outside its intact outline;
- the most is 18% (`newshu.shp` 7 and 115-119, assembly-newshu-79);
- the boss's 240 and 244 add 1% and 3%.

So the "new shape" rule as written selects nothing. The two boss wrecks keep their models because A
visibly fails on them (comparison sheets), not because of that rule. Census of the 178 damaged frames
the game uses, by kind:

| Kind | Frames | Drawn by |
|---|---|---|
| Scorch and holes (same outline, <50% repainted) | 93 | A |
| Repainted (more than half the pixels new) | 38 | A |
| Shot away (more than 15% gone) | 33 | A, apart from boss 240/244 (C) |
| Same picture (<2% of pixels differ) | 9 | the intact model (A draws the few changed pixels) |
| Blank (destroyed) | 5 | nothing |
| New shape (>25% added outside the outline) | 0 | C if one appears |

Repainted frames are the ones to watch in review: the boss wrecks are among them. The census uses
`damageStats`/`damageKind` from `damageRoute.ts`. Output, with the script and pair images:
`tyrian-scratch/damage-approach/census/census2.json`.

## Known limits

- A is paint and cuts on the intact shape: no crater depth, no debris relief. A frame whose damage
  is mostly debris needs C (above).
- The cut is a vertical cookie-cutter through the whole model, top to bottom. It is right from
  Overhead; from Tilted and Steep it shows as a straight, charred wall.
- The cut's inside is charred and unlit by design. The ink outline follows the cut silhouette, but
  there is no ink line along the cut edge itself; the charred rim stands in for it.
- The tint is computed from the live palette when the frame is first drawn, and again when the
  palette changes. The enemy hit-flash hue applies to the model's colours as before, and the tint
  multiplies them.

## Cost

| | |
|---|---|
| Agent work per enemy | none for A; a C model is one script and build |
| Download | 0 for A; boss C models 0.83 MB |
| Runtime | per damaged frame on screen: three tiny textures, built once. Per fragment of a damaged model: 3 texture reads and a few dozen ALU. One extra shader program per material kind (shared by every enemy), a depth material per clone mesh for shadows, and an outline program variant for damaged clones |

Measured in headless Chrome at 1920x1080 (Tilted, three runs each; all at 60 fps). The comparison is
`?damage=off`, which behaves as main:

| Scene | Renderer CPU per frame, off → on | Draw calls, off → on |
|---|---|---|
| Boss, tick 7950 | 8.5-10.1 → 11.1-12.2 ms | 346 → 448 |
| SAVARA cruiser, tick 2660 | 5.2-5.5 → 8.1-8.5 ms | 389 → 569 |

Most of the extra cost is drawing the damaged pieces as models rather than instanced sprites.
Before/after sheets: `tyrian-scratch/damage-approach/prod/sheets/damage-{boss,levels}.png`.
