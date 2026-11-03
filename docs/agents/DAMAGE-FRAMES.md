# Damaged frames: one approach for the whole game (proposal)

Status: **proposal, user decision pending.** Prototypes live on branch `damage-approach` behind
`?damage=a|b|c`. Without the flag the game is unchanged.

## The problem

Many enemies change sprite frame when they are hit hard enough: burn holes, scorch, shot-away plates,
wrecks. Our models cover the intact frames only, so those frames fall back to the extruded sprite
(`KNOWN_DAMAGE_SWAPS`, D54). `docs/roadmap/inventory.md` counts about 290 such frames over the four
episodes, 110 of them in episode 1. One model per frame does not scale.

What the frames are. I sorted the 183 distinct damaged frames in `inventory.json` by how each differs
from its unit's best-matching intact frame. The pairing is by best pixel match, so a few assembly
pieces are paired wrongly; read these as rough shares.

| Kind | Frames | Share | Example |
|---|---|---|---|
| Scorch and holes: same outline, some pixels darker or hot | 94 | 51% | the dome turret 269→275, the boss wings 162-208 |
| Repainted wreck: same outline, most pixels new | 39 | 21% | newshm-1 1→2, the rocks 39→7 |
| Shot away: >15% of the pixels gone | 33 | 18% | the boss cable 18→170, newshc-77 83→91 |
| Same picture: <2% changed | 9 | 5% | the boss pod 128→280, 90→242 |
| Destroyed: blank | 5 | 3% | the boss arm pieces 276-284 |
| New shape: >25% new pixels outside the old outline | 3 | 2% | the boss shoulders 88→240, 92→244 |

On average a damaged frame loses 10% of its pixels, changes 36% of the rest, and adds 4%.
Script and pair images: `tyrian-scratch/damage-approach/census/` (`census.py`, `census-ep1-*.png`).
These are not committed because they contain game pixels.

## The candidates as built

All three run on the same two enemies:
- the level-1 boss, `assembly-newsh4-124`, in TYRIAN with `power=11`. Ticks: 7100 intact, 7400 arms
  destroyed (240, 244, 246), 7950 wings burnt (162-208);
- the red dome turret, `newshs-269`, damaged frame 275. It is an ordinary "basic" model in 6 levels
  of 3 episodes, and its damage is the most common kind (scorch). Captured in ASTEROID? (`main=21`)
  with `power=5&hurt=1`: tick 3425 intact, tick 3470 damaged.

`&hurt=1` (new, `playHarness.ts`) cuts every enemy's armour to just above its damage level, so the
bot's next hit damages it through the sim's own path.

### A: damage taken from the original frame (`?damage=a`)

`src/render/damage/damageFrames.ts` and `damageShader.ts`. When a damaged frame has no model of its
own, the enemy's intact model draws it. Picking the frame:
- the level's damaged frames come from enemy data (`levelDamageFrames`, from `dgr`/`dani` as `game.ts`
  uses them);
- the intact frame is the one with a model whose pixels match best.

The first time the frame is drawn, two 24x28 textures are built from the sheet's own pixels:
- **mask texture:**
  - **r:** the pixel went. The fragment is cut (alpha-clip), with a charred, glowing rim.
  - **g:** extra scorch where the pixel got darker.
  - **b:** the pixel turned hot. Embers glow there.
  - **a:** the weight of the recolour.
- **colour texture:** per pixel, the tint (damaged ÷ intact colour, from the live palette) that turns
  the intact colour into the damaged one. The model keeps its own shading, and the tint carries only
  the change.

Every fragment of the model is projected straight down onto the sprite (model x, z × 12 px), so the
damage lands where the sprite shows it. Each part handles it as follows:
- glowing parts dim or recolour too;
- while anything is cut, the material draws its back faces as a charred inside;
- while anything is cut, the outline shell is hidden.

No baking, no per-enemy data, no new meshes.

### B: parametric damage levels (`?damage=b`)

The same hook and the same shader, without textures. Each damaged frame gets one of three levels:
1. **light:** 0.5 smoke/s;
2. **heavy:** more than 10% gone or 45% changed. Holes, 1.5 smoke/s;
3. **wreck:** more than 40% gone. 3 smoke/s.

The level is picked automatically from the same pixel numbers. A real B would use a small table per
frame instead. Each level draws:
- value-noise scorch;
- noise holes with glowing rims;
- embers;
- smoke and sparks through the remastered VFX (`RemasteredFx.damageSmoke`).

"Same picture" frames get nothing. Hiding or swapping a broken sub-part, the other half of B, needs
those parts tagged in each model's Blender script (per-enemy agent work). The prototype doesn't do it.

### C: a model per damaged frame (`?damage=c`)

The models are listed in `src/render/damage/cModels/*.json` and are added to the router only with the
flag. They come from two places:
- **The boss** comes from `assembly-newsh4-124-damaged.py`, started on the stopped
  `pix-boss-damaged-frames` branch and finished here. It rebuilds the whole boss and, per piece:
  - cuts away pixels that vanished;
  - cuts craters where pixels darkened;
  - fills wrecks with a pixel relief.

  It produces 12 damaged pieces, plus two "same picture" frames drawn with the intact models.
- **The dome** comes from `newshs-269-damaged.py`, which repaints the intact build per pixel of
  frame 275.

## Comparison sheets

`tyrian-scratch/damage-approach/sheets/damage-{a,b,c}.png` (and `damage-off.png`, main today). Each
sheet shows:
- the original 2D frames of the same ticks above the 3D results;
- both enemies;
- the damaged states in Overhead, Tilted and Steep;
- cost notes.

The sheets contain game pixels and stay out of git.

## Cost per enemy

| | A: from the frame | B: parametric | C: model per frame |
|---|---|---|---|
| Agent work per damaged frame | none: automatic for every frame in the game | none for scorch, holes and smoke; tagging sub-parts is extra per model | dome: 16 min, 5 Blender runs, one agent (paint only, no new shape). Boss: a 750-line script, then 36 min of Blender per build. Over ~290 frames: tens of agent-hours plus review |
| Assets | none | none | dome +102 KB (the intact model is 45 KB); boss +2.46 MB for 12 pieces; rocks (PR #95) +667 KB for 6 |
| Load | two 24x28 textures per damaged frame, built on first draw | nothing | one more GLB per frame in the preload |
| GPU | 2 texture reads and ~25 ALU ops per fragment of a damaged model; one extra program per material kind, plus a double-sided variant while cut | noise (~4 fbm octaves) per fragment; smoke particles | an ordinary model |
| Draw calls | damaged pieces draw as models instead of instanced sprites: the same as C | same as A | same |

Measured in headless Chrome at boss tick 7950 (Tilted, 1920x1080, `?debug=play` overlay; headless timing is rough):

| Mode | fps | Renderer CPU per frame | Draw calls |
|---|---|---|---|
| main (damaged pieces as extruded sprites) | 60 | 6.7, 8.1 ms (two runs) | 302 |
| A | 60 | 9.5, 10.0 ms | 434 |
| B | 60 | 9.8 ms (75 smoke and spark particles) | 434 |
| C | 60 | 10.6 ms | 531 |

All three cost about the same:
- the extra cost over main is drawing 13 damaged pieces as models instead of instanced sprites;
- C has more calls because its pieces carry their own outline shells, while A hides the shells of
  cut pieces;
- the runs vary by 1-2 ms, so the per-fragment shader cost of A and B doesn't show at this scale.

## How each degrades by camera

- **Overhead:**
  - A lines up exactly with the sprite: cuts, scorch and tint sit on the sprite's pixels;
  - B's damage is in the wrong places (noise, not the sprite);
  - C is exact.
- **Tilted (default):**
  - A: the cuts are vertical cookie-cutter walls through the model. They are charred inside, so they
    read as burnt-through rather than see-through. Paint on side faces is projected from the top, so
    it streaks a little down steep sides;
  - B: unchanged;
  - C: shows real crater depth and debris.
- **Steep:**
  - A: the vertical cuts and streaked side paint show most. A wreck frame whose new pixels lie outside
    the intact outline (boss 240, 244) can't grow geometry, so the arms look cut off rather than
    wrecked;
  - C is best here;
  - B looks generic.
- **All:**
  - A and B hide the outline shell while anything is cut, because OutlineEffect's outline material
    doesn't run the patch. Shadows still come from the uncut model;
  - C keeps both.

## What the sheets show

- **Boss wings (162-208, scorch and holes):**
  - A puts the burns and holes where the sprite has them, with glowing rims, on the HD wing;
  - C adds crater depth and debris;
  - B covers the wings with even, lava-like noise that is not where the sprite burns.
- **Boss arms (240, 244, new shape):** they fall away as wrecks.
  - C builds the wreck;
  - A shows the cut and tinted shoulder chunk: it reads as a burning fragment but not the original's
    wreck outline;
  - B shows a noisy, holed shoulder with smoke.
- **Dome (275, scorch):** a subtle frame in the original (the ball and housing blacken, the reds
  shift).
  - A: the ball and housing darken, and the dome's reds shift a little (subtle, as in the original);
  - C: about the same, but its per-pixel repaint shows small pixel squares on the dome;
  - B's light level hardly shows: it needs smoke to read as hurt at all.

## Recommendation: D = A everywhere, C only for "new shape" frames

1. **A as the general approach.** It needs no agent work. It is the only option that covers all ~290
   frames at once, and it follows the original's damaged pixels, which is the bar here. It handles:
   - scorch and holes (51%);
   - repainted wrecks (21%);
   - shot-away frames (18%);
   - same-picture frames (5%).

   Destroyed (blank) frames already draw nothing.
2. **C for the few frames that grow a new shape** (2%: more than ~25% new pixels outside the intact
   outline, such as boss 240 and 244). Also use C for a hero frame the user flags. A census rule can
   list them. The boss's C models already exist from this branch.
3. **B's smoke and sparks as an optional garnish** on heavy and wreck levels. Noise holes and noise
   scorch stay out: they don't match the sprite.

Before A ships for real (next PR, after the decision):
- the outline: extend OutlineEffect's outline material with the same cut, so cut pieces keep their
  ink line;
- shadows: a matching depth material, so cut parts stop casting shadows;
- a top-down cap on cut walls, if the charred inside isn't enough in Steep;
- remove `KNOWN_DAMAGE_SWAPS` and test that every damaged frame of every level routes to a model.

Trade-offs to weigh:
- A's damage is paint and cuts on the intact shape. It has no depth: craters, bent plates and debris
  are C's;
- the user's art rule "the original sprite wins" is met for colour and outline, but A's side faces
  get projected paint;
- C at the size of the game is the most faithful and by far the most expensive;
- B is cheap but doesn't read as the original.

Not applied across the game: user decision pending.
