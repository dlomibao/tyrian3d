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

## D17 — Models animate with their sprites through frame-tagged parts and colours

2026-10-27

**Decision:** A model that covers several sprite frames animates by glTF extras set in its Blender
script. A part with `tyrian_frames: [89, 91]` (common.frame_part) shows only on those frames, and a
`pal_<index>` material with `tyrian_frame_pal: {"91": 122}` (palette_material frames=) takes
another palette colour on those frames. The renderer passes each enemy's current sprite frame to
its model (src/render/modelFrames.ts). Frames that change the whole shape keep using one model per
shape (`<name>-f2`, ...), which the game already swaps. The model viewer shows the shapes of one
animation as a single entry and plays it with the sprite.

**Options considered:**
- *Frame-tagged parts and colours (chosen):* one file per model, a shared body, cheap to switch
  (visibility and colour only), and a script can tag just the parts that change.
- *One model per frame for everything:* simplest renderer, but 620 more models and a lot of
  duplicated geometry for a blinking light.
- *Names instead of extras (`flame@f89`):* visible in Blender's outliner, but long frame lists hit
  Blender's 63-character names and three.js rewrites some characters in node names.
- *Procedural animation (spinning, scaling):* smoother than frame steps, but each needs its own
  code and the sprite's timing would have to be matched by hand.

**Review:** Frames are sprite indices (the frame's top-left tile), so a model's frame tags must use
the indices in its sprite.json. The animation is stepwise at the sprite's rate, like the original.

## D18 — Remastered audio lives in a private repo and is only served locally

2026-10-27

**Decision:** New arrangements of the music (and later the sound effects) live in a private repo,
tyrian3d-remaster, because the music is all rights reserved and the arrangements are for showing
the rights holders. The game plays them only when they're served locally: `npm run dev` and
`npm run play:local` (a production build served by `vite preview`) serve its `out/` folder at
`tyrian-remaster/`, and the music switches between the FM original and each style on the title
screen. Songs without a recording fall back to the original. The public build never requests the
pack (it's gated on `VITE_LOCAL_DATA`, set only by `play:local`) and nothing from it is bundled.
`npm run songs-to-midi` turns the game's songs into MIDI for arranging.

**Options considered:**
- *Private repo, served locally (chosen):* the arrangements can't leak into the public repo or
  site, and the full game can still be tested with them.
- *A user-supplied pack like the data zip:* would work on the deployed site, but the site would then
  advertise a way to load unlicensed music.
- *Keep them in the public repo, unlisted:* simplest, but public all the same.

**Review:** If the rights holders agree, decide how the music ships (bundled, or downloaded on
demand) and move it to the public repo with its licence in CREDITS.md.

## D19 — The full-screen pictures are redrawn in Blender and looked up by their JE_loadPic number

2026-10-27

**Decision:** Each of the 13 pictures in `tyrian.pic` (title, menu background, item screen, in-game
frames, story pictures, intro cards, Destruct's screen), and `tshp2.pcx` as number 0, has a new 1920x1200 picture rendered
headless in Blender by `assets/art/<name>.py`, from the game's models and procedural materials,
for the same purpose and layout. The WebPs are committed in `public/art/`, and
`public/art/pictures.json` maps each original's `JE_loadPic` number to its file, so code that
shows picture N looks it up there. Screen furniture (the in-game frames, Destruct's bars) leaves
the original's black playfield transparent. The two intro cards drop the publisher's and developer's
names and logos (and the menu background its credit line) and keep only their mood: a chrome emblem of the Talon
in a sunlit sky, an eclipse in smoke over a grid.

**Options considered:**
- *Redraw in Blender, keyed by picture number (chosen):* the art is ours to ship (the originals
  come from the data, whose licence is unresolved, #10), the scripts rebuild it, and the number is
  what the episode scripts (`]P`, `]U`, `]V`, `]R`) and the C already use.
- *Upscale the originals:* closest to the game, but still the data's pictures, so not shippable.
- *Keep showing the originals from the player's data:* works today, but isn't the remaster.
- *Recreate the logos as they were:* they're the companies' marks, not ours to remake.

**Review:** The pictures follow the originals' composition, not their pixels; the code that
shows them should place text where the original did (the story pictures keep those areas dark or
plain). `tshp2.pcx`, shown by episode 4's `]P 000`, is a separate file; its new picture is
number 0.
## D20 — The weapon preview borrows the sim's globals and gives them back

2026-10-27

**Decision:** The item screen's weapon simulator is ported as the C has it (JE_initWeaponView,
JE_weaponSimUpdate and shots.c's simulate_player_shots in `src/sim/weaponSim.ts`), running on `g`
with the game's own player_shot_create. Unlike the C, it borrows the globals only for the length
of each call: it swaps its own copy of everything it touches in (the ship and sidekick positions,
power, shot slots and their draw keys, the sound queue, the stars, mt_rand and the draw list) and
the game's back out. It draws a draw list, which a second, small View (the game's renderer, framed
on the simulator's 136x175 window) shows in the shop panel in place of the loadout, at the C's
pace (setFrameCount(3), ~23 Hz), in the same submenus as the C: front and rear gun, generator and
both sidekicks. The C's text and bars over it are the shop's HTML; its power bar is a small meter.

**Options considered:**
- *Borrow and give back (chosen):* the game after the item screen is identical with or without
  the preview, however long it was watched (a test runs the C cross-check's shop sessions both
  ways and compares every global). The sim code is still the C's, line for line.
- *Share the globals as the C does:* most faithful, but opening a submenu then advances mt_rand
  by 400 draws (initialize_starfield) and leaves the preview's shots, power and positions behind,
  so the level after the shop would depend on how the player browsed. Nothing checks that path
  against the C, and the start of a level resets most of it anyway.
- *Draw the preview on the main view behind the panel:* no second WebGL context, but the camera
  and the panel's layout would have to be kept in register, and the main view's framing and mask
  would change while the shop is open.

**Review:** If the level after the shop must match the C exactly for a recorded session (demos),
apply the preview's mt_rand use to the game's generator once per submenu opened. The second View
is one extra WebGL context, made once and reused by every item screen.
## D21 — Screens between levels: the script records steps, an HTML canvas plays them

2026-10-27

**Decision:** JE_loadMap records the episode script's pictures, fades, text and music (`]P` `]U`
`]V` `]R` `]C` `]B` `]F` `]W` `]M` `]n`, and the fade_black(50) before the level) as a list of
steps named after the C calls they stand for (src/sim/story.ts), with the C's frame counts. The
host plays them before the item screen, before the level and at the end of an episode
(src/app/storyScreens.ts) on a canvas that stands in for the VGA screen, with the C's frame timer
(one frame is 0x4300 PIT cycles, ~14.4 ms) and its input rules: a key, click, tap or gamepad
button ends a pan, shows the rest of a text at once, then leaves it; fades ignore input. Esc skips
the rest of the scene, as ESCPressed would. The screen is RGB at 6x 320x200: each picture is
coloured with its own palette, text with `colors`, and palette fades are a black or white layer
whose opacity follows fade_palette's straight line. Every picture is drawn through one function,
pictureSource(), which takes the remastered image public/art/pictures.json lists for it
(src/app/pictureArt.ts) before the original from tyrian.pic. JE_main's level fades
(50 frames in, 15 out after a completed level, 10 after a death) are the same kind of layer over
the 3D view and HUD (src/app/fade.ts).

**Options considered:**
- *Recorded steps played by the host (chosen):* the sim stays synchronous and testable (the steps
  for a section are checked against the script), the order with music and the item screen is the
  C's, and the drawing is a line-by-line port of JE_displayText, JE_outCharGlow and the pans.
- *Yield to the host at every screen command:* also in order, but every caller of the generator
  (tests, the bot) would have to handle many more pauses for things they don't draw.
- *An indexed 320x200 screen with real palette fades:* exact for every palette case, but the
  remastered art isn't indexed. With the game's scripts the RGB version looks the same: every
  picture appears from black or from a picture with the same palette, and the one pan (`]U 008[`)
  is between two pictures that share palette 19.
- *A palette brightness ramp in the renderer for the level fades:* would fade the models and tiles
  but not the lighting, sky or HUD; the layer fades everything, as the C's palette did.

**Restyle (interface framework):** the story screens and the episode's end (the `]Q` hint, the
ending animation, the credits, the next episode's title, the Super Arcade code) play on one
framework screen, src/app/cinema.ts. The picture is letterboxed at any aspect ratio, cropped by
up to a fifth to fill more of a wider or taller window, over a blurred copy of itself. Text is in
the interface's type on a translucent panel, coloured from the bank and palette the C drew it in,
each character still glowing in on JE_outCharGlow's steps; long lines join up on narrow screens.
The warning bars flash along the window's edges; the credits roll smoothly at the C's rate;
titles and codes sit over the 3D backdrop (the Super Arcade ship in the hangar). Input is the
framework's: any key, pad button or tap continues, Escape / B / the Skip button skips a scene.
The C's timing, its order of screens and its mt_rand calls are unchanged.

**Review:** The level fade-in runs while the level starts (the C holds the game during the
fade, but its play area is empty then). Text uses the original tiny font scaled up; if remastered
pictures want new type, that's the place to change. Check the warning screen before MINES
(flashing bars and siren) and episode 1's ending (pan up, flash).

## D22 — After the last episode the game goes on into episode 1, as JE_nextEpisode does

2026-10-27

**Decision:** `]Q[` (end of episode) runs the C's sequence inside JE_loadMap (src/sim/tyrian2.ts,
src/sim/episodes.ts): the final score and a secret hint, JE_nextEpisode, then `goto new_game` into
the next episode's first section, with the ship, items, cash, difficulty and data cubes carried
over and the item data reloaded (JE_initEpisode). After the last available episode come the
credits, maybe the SuperCarrot (1 in 6), the next Super Arcade ship's code, and then episode 1 again
with everything kept (gameHasRepeated), not the title screen. Only a Super Tyrian game goes back to
the title. The screens are pauses of the JE_loadMapSteps generator (LoadMapPause, like the item
screen in D13), drawn by src/app/episodeEnd.ts on a 320x200 indexed canvas (src/app/vga.ts) with
the original's fonts, palettes, timing and the decoded tyrend.anm.

**Options considered:**
- *Follow JE_nextEpisode (chosen):* the original's own ending, including its replay of the game
  with the player's gear.
- *Credits, then the title:* simpler to explain, but not what Tyrian does, and it throws away a
  finished game's ship.
- *HTML screens for the text and credits:* consistent with the title and shop, but the credits'
  fading pictures and flying ships, the glowing text and the animation are pixel effects; one canvas
  keeps the whole ending in the original's look.

**Review:** Finish episode 4 and check the credits, the "Type ... at Title" screen and the return to
episode 1's item screen. The fallback is to return false from the `]Q[` case when
jumpBackToEpisode1 is set (back to the title). The title screen doesn't take the Super Arcade codes
yet, so that screen names a code nothing reads.
## D23 — Data cubes: the C's cube list and wrapped text, a scrolling HTML reader, and a NEW mark

2026-10-27

**Decision:** The Data row of the item screen works as in OpenTyrian's `JE_itemScreen`. It lists
the cubes picked up in the last level (`cubeList[0 .. cubeMax-1]`, which the episode script's `]?[`
fills and the level's pickups count). Enter opens a cube in the reader, and Enter, Escape or EXIT
go back. `src/sim/cubes.ts` ports `load_cube`, including its word wrap to 150 tiny-font pixels and
35 characters, and the reader's `yLoc`/`yChg` scrolling. `tools/opentyrian-cubes` checks every
cube of all four episodes against the real C. `src/app/dataCubes.ts` shows the C's wrapped lines in
a nine-line column, which also scrolls with the wheel or a drag. The face is drawn in its own
palette (`facepal`). Cubes the player hasn't opened this session are marked NEW.

**Options considered:**
- *Keep the C's line breaks (chosen):* the line count, "Read: n%" and End all depend on them, and
  the text reads as it did in the original. The column can't reflow to a wider panel.
- *Reflow the text in HTML:* fits any width, but the scroll rules and percentage would no longer
  match the C.
- *Mark new cubes with lastCubeMax:* the C doesn't do this. `lastCubeMax` only records the count
  for saves (JE_saveGame). At the item screen it's never below `cubeMax`, and every cube listed is
  from the last level anyway. So NEW means "not opened yet" instead, kept in memory for the
  session.

On the interface framework the reader takes the framework's input, not its own listeners: up/down
(keys, d-pad, stick), Page Up/Down, Home/End and a pad's LB/RB (one page of Page Down). A press counts
as held for 6 of the C's frames, less than a line takes, so a tap still scrolls one line and the
framework's key repeats keep a held key scrolling (`src/app/cubeReaderControl.ts`). The text is drawn
between the C's frames, so it scrolls smoothly at any display rate.

**Review:** Check that the reader feels right with arrows (one line per tap, as in the C) and the
wheel. Holding a direction can pause briefly after the first line, until the framework's repeat starts
(380 ms on a pad). The C's End key wraps `yLoc` for cubes of nine lines or fewer, which scrolls the text out of
view; here it stays at the top. If NEW isn't wanted, remove it from `dataCubes.ts`, where it
lives.
## D24 — Saved games and settings live in localStorage; the Options menu's setup rows open a settings screen

2026-10-27

**Decision:**
- **Saves:** `src/sim/savegame.ts` ports JE_saveGame/JE_loadGame with the C's 22 slots (1-11 one
  player, 11 being the automatic "LAST LEVEL" backup; 12-22 two players) and the fields of
  JE_SaveFileType, stored as versioned JSON in localStorage (`tyrian3d.saves`). The slots are kept
  in memory too, so the retry backup works without storage. The D14 backup is now
  JE_saveGame(11)/JE_loadGame(11), taken at the same point as before (after JE_loadMap, before the
  level starts). Loading from the item screen re-enters JE_loadMap at the C's new_game label; loading
  from the title follows JE_loadScreen.
- **Settings:** the volumes (tyrMusicVolume/fxVolume, 0-255, default 223 as in the C) and key
  bindings are kept as versioned JSON (`tyrian3d.settings`); the music style stays in MusicSwitch's
  own key. Each control has two keys (OpenTyrian's default plus the WASD/JKL set), rebound with the
  C's swap rule; Escape, P and F11 are reserved.
- **Options menu:** Load, Save and the Music/Sound rows are the C's menu (`game_menu.ts`). The
  Joystick and Keyboard rows open the settings screen (`src/app/options.ts`) instead of the C's
  in-menu MENU_JOYSTICK_CONFIG/MENU_KEYBOARD_CONFIG; the joystick part is a live button check, not
  the C's per-button assignment, since browsers give gamepads a standard layout.

**Options considered:**
- *localStorage JSON with the C's slot layout (chosen):* readable, versioned, and the slot list and
  LAST LEVEL behave like the original.
- *Write the C's encrypted tyrian.sav bytes:* saves could move to and from OpenTyrian, but the format
  carries the high-score table and editor data this port doesn't have; import/export can be added later.
- *IndexedDB:* asynchronous, and the saves are a few kilobytes.
- *Port KEY CONFIG and the joystick menu inside the item screen:* closer to the C's look, but the
  title needs the same settings, and one screen serves both.

**Review:** The C saves the backup after start_level_first's episode-4 difficulty decrement, so in
episode 4 each retry lowers the difficulty one more step; the port saves before it, as D14 did. If
that quirk should be reproduced, move the JE_saveGame call after initLevelWorld. Two-player saves
(slots 12-22) aren't shown on the title's load screen, as there's no two-player game yet. Volumes
now start at the C's 223, about 4 dB below the old full volume for both music and effects.
## D25 — High scores follow JE_highScoreCheck; quitting a game also checks

2026-10-27

**Decision:** The high score tables are OpenTyrian's: the 22 saveFiles entries (a one-player and
a two-player table of three per episode, for episodes 1-3), kept as JSON in localStorage instead
of tyrian.sav, with loadSaves' random default names and scores when there's none yet. The rules
are ported from JE_highScoreCheck (src/sim/highscores.ts): the one-player score is JE_totalScore
(cash plus the value of the ship and gear), only the table of the episode the game started on is
checked, never episode 4 or a game that has repeated, and the difficulty column is
difficultyNameB indexed by the difficulty level at the time. The C's quirks are kept: the shift
that makes room moves names and scores but not difficulties, and cancelling the name entry leaves
the shifted table. The check runs where JE_nextEpisode runs it (episode end), and also when the
player quits to the title from the item screen. The title screen's High Scores entry shows the
tables (JE_highScoreScreen).

**Options considered:**
- *Episode end plus quitting (chosen):* in the C, only JE_nextEpisode checks. A death there
  doesn't end the game either: it reloads the last level (D11, D14). Here, quitting from the item
  screen is the only other way a game ends, so it's the "game over" that can earn a place.
- *Check at each Game over screen:* every retry of one game could add another entry.
- *Episode end only (the C):* a player who never finishes an episode never sees the table fill.
- *Tables for episode 4 too:* localStorage has the room, but the C has no episode 4 table and
  excludes it from the check.

**Review:** A new game's score is already 19,500 on episode 1 (10,000 cash plus the starting
gear), above most of the 1,000-20,000 defaults, so quitting at once can earn a place. If that
feels cheap, drop the check on quitting (the C's behaviour). Normal games show "Easy" in the
difficulty column, because difficultyNameB starts at "Unranked", "Wimp"; that is the C's
indexing, kept on purpose.
## D26 — Menus are one HTML framework over a 3D backdrop; pause quits to the title

2026-10-27

**Decision:** Every screen outside the action is built with `src/ui/` (src/ui/README.md): design
tokens in CSS custom properties, a few base components, a screen manager that shows one screen at
a time with a transition, and one navigation model in which keys, pad buttons and taps become the
same eight intents. The look is a "remastered" Tyrian drawn with CSS: dark panels with gold corner
brackets, the palette's amber, gold, cyan and steel, Orbitron for titles and Exo 2 for text (Google
Fonts, SIL Open Font License, loaded by index.html with system fallbacks). Behind the menus a
three.js backdrop flies the player's ship over a generated dark planet, drawn with the game View's
renderer and only while a screen asks for it. The pause screen's "Quit to title" ends the game.

**Options considered:**
- *HTML framework, shared View renderer (chosen):* text stays sharp at any size and readable on a
  phone, screens are quick to write, the rules stay in `src/sim/`, and one WebGL context serves both
  the game and the menus. The backdrop stops during levels, so play costs nothing extra.
- *Menus drawn in three.js (text meshes, UI in the scene):* one rendering path, but text and
  layout would be hand-built and harder to make accessible and responsive.
- *A second WebGL canvas for the backdrop:* simpler to isolate, but two contexts, and phones limit
  how many a page may hold.
- *Self-hosted fonts:* no request to Google, but the font files would need a dependency or
  committed binaries; the fallbacks keep the game working offline.
- *Pause "Quit" as in OpenTyrian:* JE_inGameSetup's Quit sets reallyEndLevel and playerEndLevel,
  so start_level reloads the "LAST LEVEL" backup and returns to the item screen. A death already
  does that (D14); a way back to the title was what was missing.

**Review:** Play through the title, item screen and a level with keys, a pad and a phone. If the
backdrop's cost shows on slow machines, cap its frame rate or render it at a lower pixel ratio. If
the C's in-game Quit is wanted, add "Retry from item screen" to the pause menu: it's the "died"
path in `run.ts` with `playerEndLevel` set.

## D33 — Frames not worth a model are listed with a reason; a test checks the rest are modelled

2026-10-27

**Decision:** Of the catalogue's 1,717 enemy and ship frames, 1,716 have models. The last one,
newsh0.shp frame 13 (a filler piece of the level 2.12 dragon, seen for 13 ticks), is one
near-black outline pixel in an otherwise empty 24x28 block, so it gets no model and stays
extruded. `tests/render/modelCoverage.test.ts` holds such frames in `NOT_MODELLED` with the reason,
and checks every other catalogued frame has a model whenever `reference/models/` exists.

**Options considered:**
- *Skip it, with the reason in a coverage test (chosen):* the exception is written down where
  the check runs, and the next sim change that brings in a new frame shows up as a failing test
  naming the frame, instead of a silent extruded sprite.
- *Model the pixel as a 1/12-unit cube:* 100% on paper, but a model file and a script for
  something the extruder already draws identically.
- *Drop near-empty frames in the catalogue (a pixel-count threshold):* hides the frame, but the
  threshold is arbitrary and would also hide small real parts such as horn tips.
- *A note in the README only:* nothing would notice new uncovered frames.

**Review:** The coverage test reads the git-ignored catalogue, so it only runs where `npm run
catalogue` has been run, and only as fresh as that catalogue. Regenerate it after sim changes
that affect which enemies are drawn.
## D32 — Cheats: the C's chords and codes, with the title's codes routed to hooks

2026-10-27

**Decision:** The cheats and secret inputs of OpenTyrian are ported as rules on the game state in
`src/sim/cheats.ts`, with thin key handling in `src/app/cheatKeys.ts` (in flight) and
`src/app/titleCodes.ts` (title):
- JE_mainKeyboardInput's chords, run once per tick in which a key went down, with the keys held
  then (key repeats count as input but don't re-hold a key, as in keyboard.c): the Nort ship
  (F2 F4 F6 F7 F9 \ /), invulnerability (F2 F3 F6), self-destruct (F2 F3 F4/F5) and skipping the
  level (F2 F6 F7/F8 without F9), with the HUD's "Cheaters always prosper." The browser's own F1-F10
  actions are held off during a level.
- titleScreen's nine specialName codes, typed on the title. STEALTH ... NORTSHIPZ (Super Arcade),
  DESTRUCT and ENGAGE (Super Tyrian) go to `titleCodeHooks`, which the arcade and Destruct modules
  fill in. A hook that sets up a game resolves true, and the game starts the way a loaded game
  does. Without a hook, a "Code accepted" notice names the ship or mode.
- difficultySelect's hidden difficulties: Shift+G, Shift+] and L O R D add Impossible, Suicide and
  Lord of the Game, one by one, to the title's difficulty row, which now lists difficultySelect's
  six levels with their own names. Before, `difficulty_name` was indexed by level, which only
  matched for the first three.
- params.c's LOOT as `?loot` in the address (richMode: a new game gets 1,000,000 credits).

On the title a code's later letters are taken from the shortcuts and WASD, but its first letter
isn't, so S and D still move and L, O, H and M still open their screens when no code is under way.
L is the exception while Lord of the Game is the next difficulty to unlock. A finished code
starts over: in the C its counter stays at the end, so a key without a character, such as an
arrow, would fire it again after the title comes back.

Not ported: the edited ships (Tab/Caps Lock + 1..0), which need the ship editor's newsh$.shp
(absent from Tyrian 2.1's data); the debug keys (F10 + Backspace); constantPlay, constantDie and
their keys (command-line test modes; the C key's rule is there but constantPlay is never set); and
the Backspace "personal commands" (screenshot pause, smoothies, filter cycling, hyper-speed,
random music), which are developer keys.

**Options considered:**
- *Port the chords as held keys (chosen):* the original's rules, including its quirks: holding
  self-destruct toggles cheating again on every key repeat, and skipping the level sets
  `levelTimer` so `]t[` script jumps act as if the timer ran out.
- *Also accept chord keys typed one after another:* kinder to keyboards that can't hold seven
  keys (the C does this only for LORD), but it would fire chords that were never held, such as
  skip-level halfway through typing the Nort ship.
- *A separate difficulty screen for LORD, as in the C:* no clash with the L shortcut, but it would
  bring back a screen the title merged away.

**Review:** On the title, type `techno` (notice), `destruct` and `engage`. Check that L, O and H
still open their screens. Press Shift+G, Shift+] and type `lord` to show all six difficulties.
In a level, hold F2 F3 F6 and check the HUD line, then F2 F6 F7 (the level ends), and all seven
keys of the Nort ship. Once the arcade and Destruct modules are merged, set `titleCodeHooks` from
them, e.g. in run.ts. To drop a cheat, remove its branch in `JE_mainKeyboardInput`.

## D32a — The high score name entry follows the fanfare with song 31

2026-10-27

**Decision:** JE_highScoreCheck plays the fanfare (song 33) and, after every input of its name
entry, `if (!playing) play_song(31)` (mainint.c L2051-2052). The fanfare doesn't loop, and lasts
about 7 seconds, so the first key, click or button after it ends starts song 31, which loops. The
port played only the fanfare. `MusicPlayer` now has `playing` (lds_play.c's `playing`: true
from play() until a song ends by itself; stop() doesn't clear it). The music worklet reports it to
the main thread, tagged with the play command it belongs to, and a remaster recording counts as
ended when its non-looping buffer finishes.

**Options considered:**
- *Report lds `playing` from the worklet (chosen):* the C's own test, so the song changes exactly
  when the original's would, for any song and any remaster recording.
- *Time the fanfare on the main thread:* no audio changes, but the length differs between the FM
  song and recordings, and the timer drifts if the audio context starts late.
- *Start song 31 when the fanfare ends, without waiting for input:* smoother, but not what the C
  does.

**Review:** Get a high score, wait about 8 seconds on the name entry, then type. Song 31 should
start at that key. If the change at a key press sounds abrupt, start song 31 when `playing` goes
false instead.
## D29 — Attract-mode demos replay the C's demo files, from a fresh state each time

2026-10-27

**Decision:** demo.c is ported as `src/sim/demo.ts` (beginPlayDemo, playDemoKeys, endPlayDemo),
hooked where the C calls it: JE_loadMap reads the demo header instead of the episode script, and
JE_playerMovement replays the recorded keys. A death ends a demo at once, as the C's game-over
branch does with playDemo set. On the host side the title screen has the C's 30-second idle timer
(`src/app/idle.ts`; any key, pointer motion or press, wheel, pad button or stick restarts it, and
it doesn't run while Load Game, Options or High Scores is open); when it fires, the next demo plays
(`src/app/attractDemo.ts`) with "INSERT COIN" (miscText[7]) over it, and any key, click, tap or pad
button returns to the title. The demos cycle 1 to 5, as demoNum does. `?demo` or `?demo=N` plays
one at once. Recording (`recordDemo`) isn't ported.

The one departure from the C: before a demo, the state a game or an earlier demo leaves behind that
the level start doesn't reset (the player structs, including their movement-friction counters;
optionAttachmentReturn; initialDifficulty, which event 66 reads; the bonus-level flags) goes back to
its value at program start. In the C a demo after a game can play differently from one after
launch; a test (tests/sim/demo.test.ts) found demo 3 drifting when played twice in a row after a
game, from x_friction_ticks alone.

**Options considered:**
- *Fresh state per demo (chosen):* every demo plays as it does in OpenTyrian straight after launch,
  which is what the cross-check compares (tools/opentyrian-demo plays all five through the real
  JE_main; all five match tick for tick to the end, including the final random number).
- *Exactly the C, leftovers included:* faithful in the letter, but the demo would depend on what
  was played before it, and nothing could check it.
- *No intro logos after a demo that ran out:* the C shows intro_logos again unless the player
  stopped the demo; this port has no intro logos, so both cases go straight to the title.

**Review:** In OpenTyrian (and so here) demos 1-3 end with the ship destroyed partway through the
level, and demos 4-5 run out of recorded keys. That is the C's behaviour, reproduced, not a desync
of the port; why the C dies (probably recordings made with a DOS Tyrian whose simulation differed
slightly) hasn't been checked. If the deaths look bad as attract mode, the fallback is to stop a demo a little before
its death tick (from the fixtures) rather than altering the sim.
