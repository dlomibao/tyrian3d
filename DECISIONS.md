# Decisions

Judgment calls made while working autonomously, logged for review. Each has a **Review:** line
naming what to check and the fallback if you disagree.

## D1 — Transliterate OpenTyrian's simulation; turn its blits into a draw list

2026-10-22

**Decision:** Port the gameplay code (JE_main's level loop, JE_drawEnemy, JE_eventSystem, player
movement, shots, collisions, explosions) to TypeScript as a close transliteration under `src/sim/`.
Keep the C function and variable names, and the C integer semantics (`src/sim/cint.ts`). Every
`blit_sprite*` call becomes an entry in a per-tick draw list (`src/sim/draw.ts`), and every
background tile draw does too. The 3D renderer consumes that list and never touches game state.

**Options considered:**
- *Transliteration plus a draw list (chosen):* the game plays like the original, because it is the
  original logic. Bugs can be checked line by line against the C, and the renderer is fully
  decoupled. The cost: C-style code (globals, 1-based arrays, `goto`s rewritten as flags).
- *Clean-room reimplementation from behavior:* idiomatic TypeScript, but every enemy pattern,
  weapon and event would have to be rediscovered and would drift from the original. Far more
  error-prone.
- *Run OpenTyrian compiled to WASM with a 3D front end:* the most faithful, but OpenTyrian's
  drawing is welded into its logic, so the 3D renderer would still need the same draw-list
  surgery inside C. It would also mean a GPL C toolchain in the build.

**Review:** Is a C-shaped TypeScript core acceptable? The fallback is to refactor modules into
idiomatic classes one at a time, behind the same draw list, once behavior is pinned down by tests.

## D2 — The simulation runs at the classic tick rate; smoothness comes from interpolation

2026-10-22

**Decision:** The ported simulation always ticks at Tyrian's Normal speed (~34.8 Hz). Rendering
runs at display rate (60 Hz or more) and interpolates each drawn sprite between its positions in
the last two ticks. Draws carry stable `key`s so they can be matched across ticks. `Timing` and
`?hz=` remain for non-ported code, but the ported sim ignores them.

**Options considered:**
- *Classic tick plus render interpolation (chosen):* exact original gameplay, and smooth 60+ fps
  motion on screen.
- *Rescale the ported logic to 60 Hz:* Tyrian's movement is integer pixels per frame with
  integer accelerations. Scaling those breaks patterns, collisions and RNG-driven timing.
- *Run the logic at 60 Hz unscaled:* the game would run 1.7x too fast.

**Review:** This meets "adaptable to 60 fps" visually, but not as a 60 Hz *logic* mode. The
fallback for true 60 Hz logic is a separate fixed-point pass over the sim later, verified against
classic-rate traces.

## D3 — The game data is supplied by the player and never deployed

2026-10-22

**Decision:**
- **Production (GitHub Pages):** the page asks the player for `tyrian21.zip`, which they choose
  or drop in, and reads it in the browser. It's cached in IndexedDB for later visits.
- **Dev server:** Vite serves the local git-ignored `data/` folder at `/tyrian-data/`, through
  dev-only middleware that is never part of the build.

The game files never enter the repo or the deployed site.

**Options considered:**
- *Player-supplied zip (chosen):* the deployed site works without redistributing data whose
  licence is unresolved (#10).
- *Deploy the data:* the simplest, but it redistributes files whose bundled `license.doc` forbids copying.
- *Fetch the zip from the mirror at runtime:* blocked by CORS, and it depends on a third-party host.

**Review:** If #10 resolves in favor of redistribution, add the data to the Pages build and skip
the picker. The loader already accepts the same files from any source.

## D4 — Sprites become 3D by extruding their pixels; Blender models override key sprites

2026-10-22

**Decision:** Any sprite without a hand-made model is rendered as a mesh generated at runtime from
its pixels: one column per opaque pixel, with height from the pixel's distance to the sprite edge
(so shapes are rounded), colored from the palette, with the same dark outline as the Talon.
Hand-made Blender models (like `usp_talon.glb`) override specific sprites by sheet and index.

**Options considered:**
- *Runtime pixel extrusion plus selected Blender overrides (chosen):* every sprite in the game is
  3D and recognisably the original, with no per-asset work needed to play a full level. The
  sprites only exist at runtime (D3), so meshes can't be prebuilt from them anyway.
- *Hand-model every enemy in Blender first:* the best look, but it's hundreds of sprites, so it
  would block playability for weeks.
- *Flat billboards:* trivial, but not 3D.

**Review:** Check the extruded look in play. Replace high-visibility sprites (bosses, common
enemies) with Blender models over time; the override table is the place.

## D5 — Draw order maps to height

2026-10-22

**Decision:** Each draw pass in JE_main gets a fixed height above the ground plane, rising in
draw order: background 1 < ground enemies < background 2 < sky enemies < background 3 < top
enemies < shots and the player < enemy shots < explosions. Passes that change order at runtime
(`background2over`, `background3over`, `topEnemyOver`, `skyEnemyOverAll`) move between heights,
which keeps the original's occlusion under a top-down camera.

**Options considered:**
- *Heights by draw order (chosen):* it reproduces the original's layering exactly and gives real depth.
- *Everything on one plane, sorted by draw order:* faithful, but flat.
- *Physically motivated heights per object type:* breaks the cases where the original reorders passes.

**Review:** Look for layering mistakes in levels that toggle `background2over` and the like. The
fallback is per-level height overrides.

## D6 — Draws are lifted along camera rays, so the screen layout is exactly the original's

2026-10-22

**Decision:** Each draw is placed at its pass height (D5), but not straight above its ground
position. It goes on the ray from the camera through that ground position, and it's scaled by the
same factor, so it covers exactly the screen area it covered in the original
(`writeMatrix` in `src/render/drawListRenderer.ts`). The camera frames the original's 264x184
window: game_screen x 24..288, y 0..184 (`showNormal`, src/backgrnd.c). A screen-space mask
covers everything outside that window's outline, because the C draws tiles and sprites past the
window's edges. Under the tilted camera, the window's outline is a trapezoid.

**Options considered:**
- *Ray-projected placement (chosen):* shots visibly hit what they hit in the original, and nothing
  drifts toward the screen edges as it gets higher. Heights only change depth, lighting and shadows.
- *Straight up from the ground position:* higher passes would be magnified and pushed outward by
  perspective, up to ~15% near the edges. Collisions would look wrong.
- *Clipping planes instead of a mask:* they're exact in 3D, but OutlineEffect's outline material
  ignores clipping planes, so outlines of clipped objects stayed visible.

**Review:** A side effect is that a raised draw's real ground point is nearer the camera than it
looks, so its shadow drifts down the screen. The sun is placed to cancel most of this (`view.ts`).
If shadows look detached, lower `PASS_HEIGHT`. `?clip=0` shows everything that was drawn.

## D7 — Meshes store palette indices; colour comes from a palette texture

2026-10-22

**Decision:** Extruded meshes carry each pixel's palette index as a vertex attribute. Ground tiles
are an index atlas. Shaders look colours up in a 256x1 texture of the active palette. The C's
index arithmetic runs in the shader from a per-instance attribute: `blit_sprite2_filter` is
`(filter & 0xF0) | (i & 15)`, and `blit_sprite_hv` applies hue/value with the C's saturation.
JE_filterScreen (the level-wide hue and brightness) depends only on the index, so it is baked into
the palette texture (`remapScreenIndex`).

**Options considered:**
- *Index attribute plus palette texture (chosen):* one mesh per sprite serves every palette,
  hit flash and screen filter. Switching costs one 1 KB texture upload.
- *Bake RGB vertex colours, cached per palette and filter:* simpler shaders, but a filter flash
  or palette change would mean new meshes (up to 16 variants per hit sprite).

**Review:** Palette-cycling effects, if the port adds them, just update the texture. Lighting
shifts colours a little. Tone mapping is Neutral (not ACES) to keep the palette's hues.

## D8 — Ground tiles are flat textured quads; background layers 2 and 3 are extruded

2026-10-22

**Decision:** Background 1 (opaque) is one instanced 24x28 quad per tile, sampling the
palette-index atlas with nearest filtering: one draw call for the whole ground. Backgrounds 2 and 3
(which have transparency) are extruded like sprites, but lower (4 px) and with *open borders*: the
tile's own edge doesn't count as an edge, so shapes continue seamlessly across tiles. There's one
instanced mesh per distinct tile. No outline on tiles.

**Options considered:**
- *Flat ground plus extruded layers (chosen):* the terrain reads as solid 3D structures over a
  crisp floor, at a few dozen draw calls per screen.
- *Alpha-tested textured quads with thickness for layers 2 and 3:* cheaper, but flat-looking, and
  the outline pass would outline the whole quad.
- *Extruding the ground too:* ~300 tiles × up to 672 columns per screen. Too heavy, and the floor
  should be flat.

**Review:** Check tall structures in later levels. `TILE_EXTRUDE` in `spriteMesh.ts` tunes height.
Some tiles may want outlines; layer 3 is often clouds or high structures, which may want more height.

## D9 — Real shadows replace the shadow sprites; blend is translucency; shots glow

2026-10-22

**Decision:**
- `darken` draws (the ship's shadow, drawn when `background2` is on) are skipped. The shadow map
  gives every object a real shadow instead.
- `blend` draws (invulnerability, blended background 2) render at 55% opacity.
- Shots, explosions and effects use a partly emissive material, so they read as energy.
- Pixels and rects (superpixels, warning bars) are unlit quads.

**Options considered:**
- *Shadow map (chosen):* it's consistent for every object, including enemies and terrain, which
  had no shadows in the original.
- *Render darken sprites as dark translucent decals:* faithful to where the original put the
  ship's shadow, but the ship would get two shadows.

**Review:** If the original's exact shadow offset matters, draw darken sprites as decals at the
ground height, and set the ship's `castShadow` to false.

## D10 — Interpolation matching: key, kind, and order within the key

2026-10-22

**Decision:** A draw matches the previous tick's draw of the same kind with the same `key`. When
several draws share a key in one tick (multi-sprite enemies, the ship and its parts), the n-th
matches the n-th. Key -1, pixels and rects never interpolate. A move of more than 40 px on either
axis in one tick snaps instead of sliding (`src/render/interpolation.ts`).

**Options considered:**
- *Key plus occurrence order (chosen):* the sim only needs stable keys per object. The C's draw
  order within an object is already stable.
- *Require unique keys per draw:* it would force sub-keys into every multi-sprite draw site of the port.
- *Nearest-neighbour matching without keys:* it fails when enemies cross.

**Review:** The sim agents should give each enemy, shot and explosion slot a stable key (e.g.
slot index plus a per-kind base), and give background tiles their map position. If an object's
part count changes between ticks, parts may pair up wrongly for one frame.

## D11 — A failed level restarts from its starting loadout; there are no lives

2026-10-22

**Decision:** In a one-player story game, when the ship is destroyed the game shows "Game over",
then restarts the same level with the items and cash the player had when it began. This is what
OpenTyrian does (`start_level` → `JE_loadGame(11)` restores the backup saved as "LAST LEVEL"). The HUD
shows no lives counter.

**Options considered:**
- *Restart the level from its start state (chosen):* matches the original's story mode.
- *Arcade-style lives:* the original's lives belong to arcade mode, which isn't ported.
- *Send the player back to the title:* harsher than the original.

**Review:** Play to a death and check the retry restores the weapons and cash the level started
with. The fallback is a "back to title" option on the game-over screen.

## D12 — The camera fits the play area exactly, solved numerically

2026-10-22

**Decision:** The camera framing projects the play area's four ground corners and iterates the
distance and aim point until the outline fills the window, centred. Before this, a closed-form
estimate cut off the near (bottom) edge, where the player flies, under the tilted perspective.

**Options considered:**
- *Iterative fit (chosen):* exact for any tilt, field of view and aspect ratio, and runs only on resize.
- *Closed-form estimate with a bigger margin:* wastes screen space and is still off at extreme aspect ratios.
- *Orthographic camera:* exact by construction, but loses the depth that makes the scene 3D.

**Review:** Resize to portrait and ultrawide and check the whole field stays visible. The
fallback is the old formula with a larger margin.

## D13 — The item screen pauses JE_loadMap; its rules are ported, its screen is HTML

2026-10-22

**Decision:** `JE_loadMap` is a generator (`JE_loadMapSteps`) that yields where the C calls
`JE_itemScreen` (`]I[`). The host runs the item screen, then resumes the script, which jumps to
the section the player picked on the map, as the C does. `src/sim/game_menu.ts` ports
JE_itemScreen's rules without its drawing: the menu state (`curMenu`, `curSel`, `menuChoices`,
`old_items`, `temp_weapon_power`), its key and mouse handlers, JE_menuFunction, JE_genItemMenu,
JE_cashLeft and JE_computeDots. `src/app/shop.ts` draws that state as an HTML overlay and feeds it
keys, pad buttons and clicks. `loadLevel` still works without a host. By default the item screen
makes the C's unattended choice (the last map destination, as with `constantPlay`), so tests and
the playthrough bot follow the same route as OpenTyrian.

**Options considered:**
- *Generator plus a ported menu state machine (chosen):* the script runs in one place and in
  order, and every rule comes from the C, including the odd ones: the trade-in when a submenu
  opens, the cursor skipping items the player can't afford, and the 16-bit sum in JE_cashLeft. A
  trace from the real C item screen running scripted keys (tools/opentyrian-shop) checks it.
- *Split loadLevel into "run to the shop" and "continue" functions:* the same result, but the
  script reader's state has to be carried between the calls by hand.
- *A clean-room shop UI with its own rules:* simpler code, but prices, trade-ins and power costs
  would drift from the original.

**Review:** Data Cubes, Options, load/save and the weapon simulator preview aren't ported, and
their rows show as "not available". The C's mouse rule needs two clicks: the first moves the
cursor and the second selects. If that feels wrong on touch, the UI can send both clicks on one
tap.

## D14 — A failed level goes back through the item screen, as JE_loadGame(11) does

2026-10-22

**Decision:** The "LAST LEVEL" backup is taken after JE_loadMap, so after shopping. It holds
saveLevel: the section JE_loadMap started from. After a death the game restores the backup and
runs JE_loadMap from that section again. The player is back in the item screen with the loadout
and credits they launched with. After each level the difficulty goes back to its pre-level value
(`difficultyLevel = oldDifficultyLevel`). A completed level also applies JE_endLevelAni's state
changes (adjust_difficulty, last_items). This refines D11.

**Options considered:**
- *Follow JE_saveGame/JE_loadGame (chosen):* the same retry loop as the original.
- *Restart the level directly (D11 as first built):* skips the item screen, which the original
  doesn't do. It also skips any route choice the section offers.

**Review:** Die in a level and check that you return to the item screen with what you launched
with.

## D15 — Every enemy and player ship gets a Blender model, found through one JSON file per model

2026-10-22

**Decision:** The sim marks each enemy's tiles as one object (`SpriteDraw.groupIndex`, the frame's
top-left sprite, plus the offset to the object's centre and which tile is drawn first). The
renderer draws a model at the centre on the first tile and skips the rest. Which frames a model
replaces is in `src/render/spriteModels/<name>.json`, written by the model's Blender script and
loaded with `import.meta.glob`. Models load the first time their sprite is drawn; until then the
sprite stays extruded. Materials named `pal_<index>` take their colour from the live palette.
The work list comes from `npm run catalogue`, which plays every level headless: 1,003 enemy
models (458 flying, 545 ground) and 7 player ships. One enemy's animation frames, and identical
pictures, are one model. Pieces of bosses and big structures are separate models, built from the
picture of the whole. Flying enemies come before ground ones, each in order of time on screen.

**Options considered:**
- *Group in the sim, one JSON per model, lazy loading (chosen):* the renderer stays ignorant of
  enemy rules. Agents building models in parallel never touch the same file. Players only
  download the models for what they've seen.
- *Group in the renderer by draw key:* no sim change, but the renderer would have to know the
  2x2 tile layout and the key encoding.
- *One manifest file listing every model:* simpler to read, but every parallel batch would
  conflict on it.
- *Baked model colours (as the Talon had):* simpler, but models wouldn't change with level
  palettes, fades or the hit flash.

**Review:** Watch a level with modelled enemies: models should sit exactly where the sprites
were, flash when hit and fade with the level. Boss pieces should line up. Models can be large in
number; if load stalls show up, preload a level's models when it starts.

## D16 — The ship and tile art is free to use; the rest of the game data still isn't hosted

2026-10-22

**Decision:** Daniel Cook released the Tyrian ship and tile graphics for anyone to use in their
games (https://lostgarden.com/2007/04/05/free-game-graphics-tyrian-ships-and-tiles/), so models
that copy the sprites closely are fine to commit and deploy. The release covers only the art,
so the data zip (levels, music, text, code) still isn't committed or hosted (D3), and the
catalogue's reference images, which are rendered from that zip, stay out of git.

**Options considered:**
- *Commit models, keep the data and references out (chosen):* uses the release as written.
- *Commit the reference images too:* they're the released art, but they're extracted from the
  data files, whose own licence forbids copying them. The Lost Garden pack has its own PNGs
  if references ever need to be committed.

**Review:** The page gives no formal licence, only "use and abuse them as desired". It asks
for a link back, which CREDITS.md gives.
