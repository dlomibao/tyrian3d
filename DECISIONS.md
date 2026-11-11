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

## D27 — Arcade games: a Game row on the title, codes typed over it, and a C bot cross-check

2026-10-27

**Decision:** One-player arcade, the seven Super Arcade ships and Super Tyrian are started by
`startNewGame` (`src/sim/arcade.ts`), a port of newGame()'s arcade branch, newSuperArcadeGame()
and newSuperTyrianGame() as they leave the game once their menus have returned. Everything in
flight (lives as the front weapon's power, pickups arming the ship, the Super Arcade weapons and
specials) was already in the level loop; the one missing piece, the Super Arcade drops taking
turns through the ship's five weapons (tyrian2.c L1548-1555), is added to `game.ts`. The title
gets a **Game** row above the episodes (Full Game, Arcade, 2 Player), cycled with Tab or the pad's
RB or picked with a tap, like the Music row; it isn't a control, so the arrows keep their jobs.
Typing a ship's code (helptext `specialName`: STEALTH ... NORTSHIPZ) opens a "Super Arcade Mode"
card over the title with that ship, the episode and the difficulty one step up; ENGAGE opens
Super Tyrian's "Prepare to play..." screen; DESTRUCT calls a hook for the Destruct game. The
matching is `CodeMatcher`, the C's specialNameProgress loop for any list of codes, so the cheats
work can reuse it. Tests play four arcade games in OpenTyrian's own C (tools/opentyrian-bot, new
`mode` argument) and compare them with the port tick by tick.

**Options considered:**
- *Game row on the title (chosen):* the title already merges New Game, episodeSelect and
  difficultySelect into one screen, so gameplaySelect becomes one more row there, not another step.
- *gameplaySelect as its own screen after choosing an episode:* the C's order, but an extra screen
  for every full game, which is what most players start.
- *Codes only through the C's flow (the code first, then episode and difficulty screens):* the
  title already shows both, so the card names them and asks to start or go back.

Small deviations, each to fit a browser: a letter that carries on a code isn't also one of the
title's shortcuts (L, O, H, M and WASD all occur inside codes), and the title's episode and
difficulty go back to what they were before the code's first letter (STEALTH's S, WEIRD's W and
DESTRUCT's D are moves); Shift, Ctrl, Alt, Meta and the lock keys don't reset a code; Super Tyrian
at Suicide is asked for with Shift held on the last letter as well as Scroll Lock (Macs have
none); beating Super Tyrian (trentWin) shows the C's "Sleep well, Trent" lines and goes back to
the title instead of quitting. Backing out of a Super Arcade card keeps the C's quirk: the next
full game starts in that ship ("smuggle"). Two-player arcade isn't built here: the row shows it
disabled until `twoPlayerArcade.newGame` in `src/sim/arcade.ts` is set by the two-player work.

**Review:** Type a code at the title and play a level of each kind. If the Game row is crowded on
phones, fold 2 Player away until it's available. The cross-check runs each game in fresh modules,
because some state (the ship's friction ticks, the explosion follow) carries over between games in
the port as it does in the C, where each driver run is a new process.

**Integration (2026-10-27):** merged with the two-player and cheats work. The kind of game is chosen
by one mechanism, the two-player work's gameplay menu (`src/app/gameplaySelect.ts`, the C's
gameplaySelect shown after the title's episode and difficulty): 1 Player Full Game, 1 Player Arcade
and 2 Player Arcade all start through `startNewGame`, and Network Game stays greyed out. The title's
Game row (Tab / RB) is gone, as is the `twoPlayerArcade` hook: `startNewGame` calls
`newTwoPlayerGame` (`src/sim/twoplayer.ts`) itself. A code typed at the title skips the menu, since
it has picked its game. The codes are heard by one listener, `TitleCodeListener` in
`src/app/titleCodes.ts`, which uses `CodeMatcher` with the cheats work's hidden-difficulty keys and
one set of shortcut rules (see D32).

## D28 — Local two-player is OpenTyrian's 2 Player Arcade, with each player's own keys and gamepad

2026-10-27

**Decision:** Two players on one machine play OpenTyrian's two-player mode as the C runs it:
newGame's "2 Player Arcade" (`src/sim/twoplayer.ts`: player 1 in the Silver Ship, player 2 in the
dragonwing, no cash, one difficulty step harder), the 2 Player Arcade item-screen menu, lives that
are each player's weapon power, linking (player 2 docks under player 1 and turns a gun), and save
slots 12-22. The parts of JE_main the port had left out (both players' collisions and enemy-shot
hits, the shared shield recharge, allPlayersGone's player-2 clause, the warning for player 2) are
ported, and the C bot driver's new `play2` mode plays a two-player level in OpenTyrian itself:
the port matches it tick for tick, through a link, the linked gun turning, an unlink and player 2's
deaths and respawns. The title's Start asks for the kind of game first (the C's gameplaySelect,
shown after the episode and difficulty here; 1 Player Arcade and Network Game are listed but not
offered). Each player has their own SimInput (`simInputs`); the host fills it from that player's
devices, and a local game sets `inputDevice` to 0 for both, so each player reads all of their own:
player 1 the one-player keys, the mouse/touch and their gamepad; player 2 a key table of their
own (W/A/S/D, F fire, R change fire, Q/E sidekicks, and the keypad; rebindable under "Key config ·
Player 2" in Options) and their gamepad. In a two-player game player 2's keys win over player 1's
(so W/A/S/D move player 2 there). The item screen's Player 1/2 Input rows cycle the gamepad each
player uses (none, pad 1-4), swapping with the other player, as the C cycles inputDevice. A linked
dragonwing's gun follows the stick's angle (joystick_analog_angle). Player 2's ship has a Blender
model of the dragonwing (two sprite halves, so `spriteModels` gained `group` banking). The HUD
shows a panel per player; the high score check asks each player, the higher scorer first; Load
Game pages to the two-player saves with left/right.

**Options considered:**
- *The C's device model (chosen in spirit):* keep inputDevice and its filter in JE_playerMovement,
  but give every player their own input instead of one shared keyboard. The C's own defaults
  (player 1 on the keyboard, player 2 on the mouse) are still there for the cross-check
  (`newTwoPlayerGame(..., { inputDevices: [1, 2] })`), not for play: two people can't share a mouse.
- *One key table with player 2's keys in the second slot:* no new settings, but every one-player
  game would lose its laptop keys.
- *A two-player table for player 1 too:* each player gets half the keyboard by default, but a
  player's custom one-player keys wouldn't carry over. Player 2's keys winning over player 1's
  gets the same effect with the defaults.
- *Two-player full game (the shop, both players buying):* OpenTyrian has no such mode; its
  two-player game is the arcade one.
- *The gameplay menu before the episode (the C's order):* a step more for every one-player game,
  and the title already holds the episode and difficulty.

**Review:** Play a level with two people on one keyboard, and with two pads. If player 2's
defaults are awkward, change DEFAULT_KEYS_2 in `src/app/bindings.ts`. Player 1's W/A/S/D only
drive player 2 in a two-player game; if that surprises, make player 1's table skip only keys
player 2 actually uses. The dragonwing model (`assets/blender/ships/ship-dragonwing.py`) is a first
pass: check it at `?viewer=ship-dragonwing` once the catalogue is rebuilt (its reference is in
`reference/models/ship-dragonwing`, from `npm run catalogue`). The gameplay menu would also be the
place for the 1 Player Arcade mode. D24's note that two-player saves aren't listed no longer holds.

**Integration (2026-10-27):** the gameplay menu is the one way to pick the kind of game; the arcade
work's Game row on the title was dropped (D27). 1 Player Arcade is offered there now and starts
through `startNewGame` (`src/sim/arcade.ts`), which also starts 2 Player Arcade via
`newTwoPlayerGame`. Network Game stays listed but greyed out.

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

## D30 — Destruct is a transliteration of destruct.c in its own module, checked against the C

2026-10-27

**Decision:** Destruct, the hidden artillery game, lives in `src/destruct/`. Its rules
(`sim.ts`) are a close transliteration of OpenTyrian's destruct.c, held in one `DestructGame`
object: the C's names, its float (`Math.fround`) and unsigned arithmetic, and the shared
`mt_rand`, so a seed plays out as in the C. The terrain is the C's 320x200 byte screen
(destructTempScreen); what the C blits onto VGAScreen each tick (units, walls, shot pixels,
crosshairs) is recorded in `draws` for the renderer. `tools/destruct-trace` builds the real
destruct.c with the computer on both sides and records a running digest of the whole state every
10 ticks; `tests/destruct/trace.test.ts` must reproduce it (12 seeds over all five modes, 72,000
ticks, 28 rounds). The game is opened with `openDestruct({ files, view, sfx, music, exitSong })`
(`src/destruct/index.ts`) or `?destruct`.

**Options considered:**
- *Transliterate and cross-check against the C (chosen):* the same approach as the main game
  (D1), and the trace pins it to the original exactly, AI included.
- *Rewrite it as idiomatic TypeScript:* easier to read, but the AI, physics and terrain would
  drift from the original with nothing to check them against.
- *Write the sim into the main game's global state `g`:* destruct.c shares no state with the main
  game besides the RNG and sound queue; its own object keeps it separate and testable.

**Review:** The trace driver compiles the C with `-ffp-contract=off` and correctly rounded
`sinf`/`cosf` (glibc's behaviour, and what the port computes); clang's default fused
multiply-adds on arm64 and macOS's libm `sinf` each move some shots by an ulp. A negative float
converted to unsigned (a very rare "tall" map column) follows arm64, saturating to 0, where x86-64
wraps it. The C's `rand()` for the wall count is not used: with the default config it is always 20.

## D30a — Destruct in 3D: a slab of terrain with real holes, extruded sprites, glowing fire

2026-10-27

**Decision:** The battlefield is seen from the front, a little above, like the original screen.
The dirt (palette 16-25 of picture 11's palette, pcxpal[10] = 21) is a slab 26 px deep: its front
face is one plane textured from the screen (shaded darker with depth and a little per-pixel
noise), and its top, bottom and sides are geometry built from the dirt's outline, so craters,
rings and holes go right through it. The explosion pixels (241-255, fading a step a tick as in
the C) glow additively in front of it, with up to four point lights at the biggest live explosions.
Units and walls are their newsh~.shp sprites extruded like the main game's (src/render/spriteMesh.ts),
coloured from the palette; shots, trails and crosshairs are glowing beads in JE_pixCool's and the
crosshair's palette colours. A big explosion shakes the camera slightly. The black sky gets a
faint starfield. Units and shots are interpolated between ticks; the game ticks at the C's rate,
setFrameCount(1) at the Normal speed: ~14.4 ms, ~70 a second.

**Options considered:**
- *Slab with a textured front and outline walls (chosen):* the terrain is arbitrary pixels (rings
  floating in the air, holes, star-shaped craters), which a heightfield can't hold. Rebuilding only
  the outline walls when the dirt changes stays cheap (a 120 Hz display keeps up).
- *Extruded heightfield:* simple, but loses overhangs, floating rings and holes, which are the
  C's map types.
- *One cube per dirt pixel (instanced):* up to 60,000 cubes, re-uploaded as craters form.
- *Blender models for the units:* they're 12x14 sprites seen side on; extrusion keeps their exact
  look and costs no assets.

**Review:** Check the look and readability at a phone's size and on a slow GPU (shadows and the
outline effect run every frame). Explosions in the sky burn black holes in the C's picture; here
the sky is black anyway, so nothing shows.

## D30b — Destruct's screens, keys and the way in

2026-10-27

**Decision:**
- **Screens:** the title (JE_introScreen), mode select (JE_modeSelect), help (JE_helpScreen) and
  pause (JE_pauseScreen) are interface-framework screens over the battlefield, with the data's
  texts. The mode select also has rows for each side's computer/human switch (the C's F10/F11),
  Help and Leave; F10, F11 and F1 work there too. Escape in a round goes back to it, as in the C,
  and Escape there leaves Destruct.
- **Keys:** the C's default two-player layout on one keyboard (left: C/V angle, A/Z power, X or
  Left Shift fire, Left Alt vehicle, Left Ctrl/Space weapon; right: arrows, Enter/Insert/keypad 0
  fire, \ or keypad 5 vehicle, Page Up/Down weapon), by KeyboardEvent.code so it works on any
  layout. The left side starts as the computer, as in the C's default config. A key tapped
  between two ticks still counts for one tick. Gamepads stand in for keys: pad 1 plays the right
  side, pad 2 the left (d-pad or stick to aim and set power, A fire, X vehicle, LB/RB weapon,
  Start pause, Back leave).
- **Way in:** `openDestruct()` for the title's DESTRUCT code (the cheats work wires it), and
  `?destruct` for development, which reloads into the game when Destruct is left. It borrows the
  game View's renderer, or makes its own canvas without one.

**Options considered:**
- *Framework screens (chosen):* consistent with the rest of the game (D26) and work with pads and
  taps. The C's text drawn on the 320x200 screen would be blurry and keyboard-only.
- *Keep F10/F11 as the only computer switches:* F11 is the browser's full-screen key on some
  systems, so the menu rows make the switch reachable anyway.
- *Remappable Destruct keys:* the C reads them from opentyrian.cfg; no settings screen for them
  yet.

**Review:** A phone can't play it (it is a keyboard game; touch only reaches the menus). The app
never seeds mt_rand (`?destruct` does, from the clock, as opentyr.c's main does), so through the
title the first map is the same on every page load until the main game seeds it.

**Integration (2026-10-27):** typing DESTRUCT on the title now opens Destruct: `run.ts` sets
`destructHook.open` (src/app/titleCodes.ts) to `openDestruct` with the title's song as `exitSong`,
loading `src/destruct/` on first use. The title closes first (it resolves with `destruct`, since
`openDestruct` closes whatever screen is up) and the main loop shows it again when Destruct is
left. The app now seeds mt_rand at start-up (D37), so the first map differs between page loads.

## D31 — Screen filters: hues on palette indices, waves and blurs as a post pass over a pass mask

2026-10-27

**Decision:** The smoothies (event 64: lava, water, iced blur, blur, the headlight and the flipped
screen) and JE_barBright (the Zinglon beam) are recorded by the sim each tick in `drawList.screen`
(`src/sim/smoothies.ts`): which filters run, in JE_main's order, the last draw pass each one
covers, and whether it is the frame's first (the only one that reads the previous frame, since the
C draws into VGAScreen2 until the first filter writes into game_screen). The renderer splits each
filter in two. The hue half (lava 0x70, iced 0x80, the water's hue on indices with
`(index & 0x30) != 0`) is index arithmetic in the palette materials for draws whose pass height
(D5) is under the filter, as the C does it (`src/render/screenHue.ts`); models in those passes take
the hue like the hit flash. The value half (the lava's wave and smear, the water's ripple, the
blurs, the headlight's cone, the flip, the beam) is a post pass (`src/render/screenFilters.ts`):
the scene goes to a render target, a mask pass draws every object's pass height, and the filter
only changes pixels whose top object is under its ceiling. Pixels are placed in game_screen
coordinates by meeting the camera ray with the ground (D6), so the C's per-row and per-chunk wave
tables apply unchanged. Value is brightness; a new value scales the lit colour. Blends with the
previous frame use the per-frame weight that halves it per classic tick. It all runs only while a
filter is on. The level colour filter and brightness (event 44, the flare specials) were already
folded into the palette texture; they showed nothing because `filtrationAvail` was false, so it is
now true, as JE_initProcessorType sets it for processorType 4, which the port plays at.

**Options considered:**
- *Hue on indices, value in a masked post pass (chosen):* the colours are the C's exact palette
  entries under the 3D lighting, and only the passes the C filters are touched.
- *Everything in a post pass, hue guessed from the lit colour:* tried first. Lit colours are
  brighter than palette entries, so the lava came out washed-out yellow, and the water's
  grey/cloud test needed a nearest-palette lookup that lighting fools.
- *A full-screen post pass with no mask:* simplest, but it tints and smears the player's ship,
  shots and sky enemies, which the C draws after the filters.
- *Split the scene into two renders by pass group:* exact layering, but the instanced pools mix
  passes, so it means reorganising the draw-list renderer, and shadows across the split are lost.

**Review:** Play ASSASSIN (episode 1; lava, headlight), SAVARA V (water), and in episode 4 LAVA
RUN (lava, flip), ICE EXIT (iced blur), DESERTRUN (blur) and CORE (water with a level filter);
`?debug=level&episode=E&main=N&skip=T&god=1` starts one. The mask pass draws the scene a second
time while a smoothie is on; if that costs too much on slow machines, render the mask at half
resolution. The water ripple is an approximation of the C's bottom-up recurrence (six rows down).
Blended (translucent) objects count as solid in the mask.

**Integration (2026-10-27), with the remastered effects (D35):** the shot sprites and explosion
sprites are draws in their own passes, so the mask already leaves them alone. The remastered
particles, glows and smoke puffs aren't draws (they have no pass height in the mask) and stand for
shots and explosions, which the C draws after all its filters. So they're on their own camera layer
(`VFX_LAYER`): while a smoothie's post pass runs they're left out of the scene and the mask, and
drawn over the filtered image without depth, before the present pass, so the flip and headlight
still apply to them as JE_starShowVGA does to the whole screen. Outside smoothies nothing changes.

## D31a — The item screen's simulator draws the Plasma Storm's shots, which the C's doesn't

2026-10-27

**Decision:** The user reported that the Plasma Storm doesn't render. It is a sidekick (options
index 9, "Plasma Storm Ammo 10"), not a special weapon. In a level it renders: its shots are
option-shape sprites 22-24 (shot graphics above 60000), drawn blended by player_shot_move_and_draw,
and they fire only on a sidekick key (Left Ctrl / K, Left Alt / ;) while it has ammo, as in the
original. The C's item screen simulator, `simulate_player_shots`, skips shot graphics above 60000,
so the shop showed nothing for it; the port now draws them there as the level does.

**Options considered:**
- *Draw them in the simulator (chosen):* buyers see what they're paying 8000 for.
- *Keep the C's empty preview:* faithful, but it reads as a bug, and was reported as one.

**Review:** Upgrade Ship → Left Sidekick → Plasma Storm. If the C's empty preview is preferred,
remove the `anim_frame > 60000` branch in `simulate_player_shots` (`src/sim/shots.ts`).

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

**Integration (2026-10-27):** merged with the arcade work. The title has one key listener,
`TitleCodeListener` (`src/app/titleCodes.ts`): the codes use the arcade work's `CodeMatcher`
(`src/sim/arcade.ts`; this work's `SpecialNameMatcher` was removed as a duplicate), the hidden
difficulties use `difficultySelectKey`, and the shortcut rule above holds for both. From the arcade
work it also takes these rules: modifier keys alone and key repeats don't break a code (so Shift can
be held for Shift+G or for Super Tyrian at Suicide), and the title's episode and difficulty go back
to where they were before a code's first letter once the code completes. Super Arcade and Super
Tyrian start through the arcade work's screens and `startNewGame`. `titleCodeHooks` is now only
`destructHook.open`: DESTRUCT shows the "isn't in this build yet" notice until the Destruct module
sets it.

DESTRUCT now opens the Destruct game (D30b).

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

## D34 — Remastered backgrounds: the ground upscaled 4x at runtime, structures as tile models found by pattern

2026-10-27

**Decision:** A pilot of the backgrounds' new look, done fully for the tileset of Episode 1's first
level (TYRIAN, `shapesz.dat`), behind a switch: `?bg=remaster` (`Settings.background`;
`DrawListRenderer.setBackgroundStyle`). The default stays `original` (D8) until the other
tilesets have their structures. (Since D48 remastered is the default and `?bg=original` opts out.) Wherever nothing remastered exists, the original tile is drawn.
- **Ground (background 1):** every tile is upscaled 4x with MMPX (`src/render/remaster/mmpx.ts`, a
  port of the paper's MIT code) into a palette-index atlas (`groundAtlas.ts`). A tile is upscaled
  with its eight neighbours as they are in the map that tick, and only its own part kept, so a
  cell comes out exactly as if the whole map had been upscaled at once: no seams, and each slot
  keeps a one-texel border from its neighbours. Slots are keyed by the 3x3 context and reused least
  recently used first (a level has 1,000-2,000 contexts; about 100 are on screen). The shader
  (`groundMaterial.ts`) looks the four nearest texels up in the live palette and blends them, and
  tilts the normal by their brightness, so painted rocks and ridges catch the light.
- **Structures:** Blender models of structure tiles, placed where a pattern of tiles is. Each
  script in `assets/blender/tiles/` writes the `.glb` and a JSON entry in `src/render/tileModels/`
  (model, tileset, layer, the pattern as rows of tile numbers). `tileModels.ts` matches a pattern
  from any of its tiles, checking the cells drawn that tick, so a structure stays whole while part
  of it is off screen. Ground structures stand on their tiles (`keepTiles`); background 2-3 models
  replace theirs. The models are drawn instanced (`structureInstances.ts`): one draw per model
  part however many copies, sharing palette materials.
- **TYRIAN's models** (75): background 3's floating islands and fortresses, one model per tile
  (`shapesz_bg3.py`): a slab with the tile's outline and a rounded boulder per stone in the art
  (found as hills of brightness, with the tile between its usual neighbours, and cut at the tile
  edge so boulders continue across it), the islands' undersides hanging toward the camera, smooth
  relief for the purple carving and the metal maze floor, pits with glowing lava, drums as
  cylinders, a glowing orb. On the ground (`shapesz_ground.py`): two 2x2 bunkers and a 3x2 wreck
  as raised relief of their silhouettes (with a torus and domes for the ring bunker), boulders,
  and a crown per tree in the forest. Ground models stay under 0.2 units where ground enemies
  sit on them (the bunkers, boulders), trees under 0.4.
- **Pipeline:** `npm run tiles` (`tests/tools/tileReference.test.ts`) writes
  `reference/tiles/<shapes>/`: every used tile's pixels at 1x and MMPX 2x, its layers, levels and
  usual neighbours, the in-level palette, PNGs of each tile, its 4x upscale, the layers' tile
  sheets and maps, and a stretch of each level's ground upscaled in context. The Blender scripts
  read `tiles.json`; `tools/build-models.sh` builds them with the rest.

**Options considered:**
- *Ground generated at runtime from the player's data (chosen):* the tiles are in the data the
  player supplies (D3) anyway, every tileset gets it with no per-tileset work, and the result
  is seamless because the neighbours are known when a cell is drawn. Nothing to commit for the
  ground.
- *Upscaled ground textures committed (allowed for the tile art by D16):* reviewable files, and
  room for hand-painted or AI-upscaled ones later, but per-tile files can't be seamless for every
  neighbour a tile has, and 600 tiles per tileset of 4x PNGs is a lot to commit for what the
  game makes as it goes: about 0.17 ms per cell (measured in Node on the dev machine), so ~2 ms
  for a new row of 12 and ~17 ms once at level start. Hand-made overrides can still be added
  later as a lookup before the upscaler.
- *xBR / hqx (as OpenTyrian's video_scale_hqNx.c) instead of MMPX:* smoother, but they blend
  colours, so the result is RGB for one palette: level palettes, fades and JE_filterScreen (D7)
  would no longer apply. MMPX only picks input pixels, so it works on palette indices; the colour
  blending happens in the shader after the palette lookup instead. On the noisy dithered ground
  textures MMPX changes little; the relief lighting does most of the visible work there.
- *Per-tile upscale with clamped or wrapped edges:* measured on TYRIAN's ground, 2% (clamp) and
  0.9% (wrap) of the pixels near a seam differ from a whole-map upscale; in context it's 0%.
- *Structure models cloned per copy, as enemies are:* worked, but a fortress on screen took
  ~970 draw calls and 5.9 ms of CPU a frame; instanced, ~400 and 1.6 ms.
- *Structures modelled entirely by hand:* the most freedom, but 75 models for one tileset; the
  scripts derive shape, size and colour from the tile pixels, so the models follow the art and
  the same recipes extend to the other tilesets' rock, metal and foliage.
- *Every tile as relief (extrusion done better):* uniform, but not "real" 3D; used only where the
  art is a carved or plated surface.

**Review:** Play TYRIAN with `?bg=remaster` and compare with `?bg=original` (the sprite harness:
`?debug=sprites&episode=1&level=9&row=175&freeze=80&bg=remaster`, and
`tyrianHarness.view.draws.setBackgroundStyle("original")` in the console for the same frame).
Known gaps: the purple carving and the metal floor are relief with each 2x pixel's colour, so they
still look pixelated up close and would gain from hand modelling; the island underside is a sloped
face rather than modelled roots; the forest crowns are smooth domes, plainer than the painted
canopy; the clouds (background 2) stay extruded. To extend to another tileset: `TILES_SHAPES=<x>
npm run tiles`, then a `shapes<x>_*.py` like the two here, reusing `lib_tiles.py`. If many
tilesets' models are added, load each tileset's models when its level starts (already done on the
first tile seen) and consider one `.glb` per tileset.

**Integration (2026-10-27):** composes with the screen filters (D31) and the remastered effects
(D35). The remastered ground material applies the smoothies' hue on palette indices like the
original ground (height 0, under every filter) and marks water_filter's pixels; structure models
take a smoothie's hue for their pass height, as enemy models do. Both are instanced at their pass
height, so the smoothie mask places them correctly. The level palette, fades and level filter
still come from the live palette texture.

## D35 — Remastered shots and explosions are a presentation layer over the draw list; on by default

2026-10-27

**Decision:** Shots and explosions get a remastered look (`src/render/vfx/`), drawn from the same
draw list as everything else, so the sim and its draws are untouched. The draw-list renderer calls
it through three hooks (a new tick, each shot or explosion sprite, the end of a frame) and draws a
sprite the way it answers: as before, "hot" (fully emissive, no outline) or not at all.
- **Shots** (both passes) keep their extruded sprite, so silhouette and palette colour are the
  original's, but hot, inside an additive halo of the sprite's own brightest colour that stretches
  back along its last tick's motion into a short trail. A new shot key gets a muzzle flash.
- **Explosions** are recognised by sprite index: each moving type in `explosion_data` draws a run
  of explosion-sheet frames no other type uses (`explosionFrames.ts`, checked against the sim's
  `JE_setupExplosion` in tests), so the index alone gives the type and how far through its ttl it
  is. A type's first frame is its start. Fireballs (types 1-5, 7-10) keep their sprite, hot, under
  a fading glow, and on their first frame throw sparks, embers, tumbling debris and drifting smoke
  and light the scene with one of four pooled point lights. Hit puffs (type 0) become a spark
  burst and flash; smoke sprites (6, 12) become soft puffs. Coin values, shield arcs and trails
  stay as they were.
- **Speed:** particles live in two GPU ring buffers (4,096 additive, 2,048 blended); the vertex
  shader flies them from their spawn values, so the CPU writes a particle once and uploads only new
  slots. Halos and puffs are one instanced draw each, rebuilt into reused buffers. Lights are a
  fixed pool, so shaders never recompile in play. Small fireballs mark every hit on a big enemy, so
  they spawn few particles and debris and smoke only now and then. With 800 extra shots on screen
  (`?debug=play&stress=800`) the renderer's CPU time stayed about 2-3 ms a frame, the same as the
  original look, at 60+ fps.
- **Switch:** `?vfx=original` (or `remastered`). Remastered is the default: in play the shots read
  more clearly than before, enemy shots especially, and the explosions read as fire rather than
  plastic. `?debug=play` (src/debug/playHarness.ts) plays a real level with the test bot, any
  weapons, a fixed seed and `freezeAt=` for comparing the two looks; V switches them there.

**Options considered:**
- *Hooks into the existing renderer plus a separate effects module (chosen):* small edits to
  `drawListRenderer.ts`, and the effects can't change what's drawn, only how.
- *Replace explosion sprites entirely with procedural fireballs:* more "remastered", but loses the
  original's shapes and timing (rings, crescents, the large explosion's quarters).
- *Flat additive sprite billboards from a texture atlas:* softer fire, but a second sprite path
  and a palette-baked atlas to keep in sync; the hot extruded sprite plus glow looked close enough.
- *Fake the flash with ground decals instead of lights:* cheaper per fragment, but enemies and
  terrain wouldn't catch the light. Four lights cost little; they're removed in the original look.
- *CPU-simulated particles:* simpler shaders, but per-particle work every frame.
- *Original as the default:* safest, but the remastered look reads at least as clearly.

**Review:** Play levels with heavy weapons and big boss deaths. If the screen gets too busy, lower
the counts in `spawnBirth` (remasteredFx.ts), or the halo intensity. Switching the look at run time
recompiles shaders once (the light pool comes and goes), a short hitch; acceptable for a URL
option, but an Options row should keep the lights at zero intensity instead. Not done: an Options
menu row (the screen-filters work was changing that screen), and superpixels (JE_doSP) still draw
as plain pixels.

## D36 — Remastered sound effects are resynthesized from the originals and switch per sound

2026-10-27

**Decision:** The private remaster repo (D18) remakes all 38 sounds (29 effects in tyrian.snd, 9
voices in voices.snd) with `tools/sfx.py`, and its `out/manifest.json` lists them under
`sfx.remaster` by sound id. The effects are *resynthesized* from an analysis of each original:
its tonal content as sinusoidal tracks on clean 48 kHz oscillators, the rest as a noise vocoder
following the original's band levels, both extended above the original's 5.5 kHz ceiling, plus
designed layers (sub-bass under explosions, onset transients, three CC0 samples). So each keeps the
original's pitch, timing, length and envelope, which the player reads as feedback. The voices are
macOS `say` (Samantha; the original is a female voice around 220 Hz), fitted to the original's
start and length and pitched to its median, through a ship-computer chain. Every remake is matched
to its original's K-weighted loudness; the originals are clipped 8-bit noise, so a clean remake at
their loudness peaks higher, and the manifest's `gain_db` (0-6 dB) carries the difference.

In the game, `SoundEffects` takes the manifest and offers its sound styles; Options gets a Sound
style row (Original / Remaster) under Music style, remembered in this browser (`?sound=` overrides
it). A remade sound replaces the original only in the sample it plays: same 8 channels, same
replacement rule, same `(vol + 1) / 8` gain, times its `gain_db`. Each sound falls back to the
original on its own until its file has loaded, or if it fails or the style lacks it. Nothing is
requested unless `localAssetsAllowed()`, so the public build never asks for the pack.

**Options considered:**
- *Resynthesis from the originals plus designed layers (chosen):* keeps each sound's pitch and
  timing by construction and drops the 8-bit hiss; but a noisy original can leave tracking
  artifacts, and nothing in it is new design.
- *Designing every effect from scratch (synth.py presets, samples):* freer and possibly better
  sounding, but each would drift from the original's pitch and timing in ways nobody could check
  without listening.
- *Cleaning up the originals (denoise, upsample, exciter):* closest to the original, but it is the
  original audio, not a remake, and 8-bit clipping can't be undone.
- *Voices resynthesized from the originals (a vocoder on the old recordings):* exact delivery, but
  only as intelligible as the 8-bit source. `say` is clearer; its output is for local use only.
- *Limiting remakes to the originals' peak level instead of gain_db:* no peaks above what the game
  had, but matching their loudness would mean 8-14 dB of limiting and a flattened decay.

**Review:** Nobody has listened to these yet (listen/LISTENING-NOTES.md in the private repo lists
what to check first: the explosions, the voices, the most frequent sounds). If gain_db makes busy
scenes clip, lower MAX_GAIN_DB in tools/sfx.py or add a compressor on the effects bus. If the
rights holders approve the music, decide separately whether the effects ship too: they derive from
the game's sounds, so the same permission applies.

## D37 — The game seeds mt_rand from the clock at start-up; `?seed=N` fixes it

2026-10-27

**Decision:** OpenTyrian's main calls `mt_srand(time(NULL))` before anything else (opentyr.c
L757); the port never seeded, so every page load ran from MT19937's default seed (5489) and the
same inputs gave the same game. `runGame` now seeds once at start-up with the seconds since the
epoch (`src/app/seed.ts`), or with `N` from `?seed=N` for debugging. Only the game seeds there:
the tests, the debug harnesses (`?debug=play`, `?debug=level` and `?destruct` set their own) and
the demos (beginPlayDemo's `mt_srand(seed)`) keep fixed seeds, so the demo, bot, arcade,
two-player and Destruct cross-checks are unchanged.

**Options considered:**
- *Seconds since the epoch, as the C (chosen):* the original's behaviour; two loads in the same
  second play alike, as two launches in the same second of the C do.
- *`crypto.getRandomValues`:* never repeats, but no reason to differ from the C.
- *No seed (as before):* repeatable, but every session played the same.

**Review:** Load the game twice and play the same way: enemy fire and drops should differ. To
repeat a session exactly (with the same inputs), load it with the same `?seed=N`.

## D38 — The remastered Synth music plays by default where it's available

2026-10-28

**Decision:** Until the player picks a music style, `MusicSwitch` plays `DEFAULT_MUSIC_STYLE`
("synth") when the remaster manifest has it, otherwise the original FM music. A remembered
choice (`tyrian3d.musicStyle` in localStorage, set by `M` or Options) and `?music=<style>` still
win, so a player who picked Original or Orchestral keeps it. The deployed site has no manifest,
so it plays the original as before; only local builds with the private remaster change.

**Options considered:**
- *Synth when available, choice remembered (chosen):* what the user asked for; nothing changes
  for anyone who already chose, or for the public site.
- *Override remembered choices too:* would undo an explicit pick.
- *Make it a build setting:* more machinery for a single default.

**Review:** In a local build with a fresh browser profile (or after clearing the site's storage),
the title music is the Synth version; `M` cycles and the pick is remembered across reloads. To
go back, set `DEFAULT_MUSIC_STYLE` to "original".

## D39 — Models are improved by a grade→fix→regrade loop calibrated on the user's ratings

2026-10-28

**Decision:** Models are improved in rounds. A grader rates a model's review sheet
(`tools/review_sheet.py`) with `tools/calibration/rubric.md`. A fixer edits the model's own Blender
script against the grade, rebuilds it and renders a new sheet. A second grader, from a different
model family than the fixer and seeing only the two sheets, scores the new sheet and says whether
it is better, the same or worse. A worse round is undone from backups. At most 3 rounds; a
model stops at 4 overall with no high-severity issues, or when a round changes nothing. The
rubric is calibrated on 20 models the user rated (`assets/blender/proto/calibration/feedback.json`):
an Opus and a Fable grader plus a chair graded them and the user agreed with every grade. Opus
fixes; Fable grades.

First run: the 18 calibration models plus the 7 player ships. 22 of the 25 reached 4 overall
(from mostly 2-3). One round of 33 was undone (assembly-newshr-85, round 3). Triangle counts
grew 1.1-2.7x. Only the models' own scripts changed: no shared lib_*.py, no common.py, and the
sprite-model entries (frames, animation) are byte-identical.

**Options considered:**
- *Grade→fix→regrade with revert (chosen):* every kept change was judged better by a grader
  that never saw the fixer's reasoning; regressions are undone automatically.
- *Generate models from the sprite analysis (the model-shape prototype):* only beat the hand
  models on simple round sprites.
- *Rescale the hand models' heights from the analysis (reshape):* one global fix; can't make
  a slab round or cut a recess.

**Review:** Open the model viewer on a few changed models (the player ships, newsh5-47,
assembly-newshb-115) and play a level or two: the models should look like their sprites with
more depth, and nothing should be missing or misplaced. To undo a model, restore its script
from main and rebuild it with `tools/build-models.sh`.

Second run (round two, the next 62 models by screen time) and a lighting pass over all 87
reworked models: the fix loop had read the sprites' drawn lighting as shape and paint (lumps under
metal highlights, the sprite's outline ring and shading painted on, which made models dark in game).
The rubric now says highlights, the outline and the sprite's shading are lighting; each part gets
a material that fits it (polished metal, glass, matte rock or flesh), and panel 9 of the review
sheet renders like the game (EEVEE, metalness and roughness, environment and sun) so graders can
see shine. The user flagged the Gencore Phoenix's highlight lump, which started this.

The player ships' review sheets used to show the hardest left-bank frame rather than the level
frame (`sprite_shape.load_sprite` took `frames[0]`); the two ship grades made from them are
marked superseded and the ships were regraded on corrected sheets.

## D40 — The remastered music is public; the remade sound effects stay private

2026-10-29

**Decision:** The orchestral and synth arrangements of all 41 songs (D18's private pack) are
published in `public/tyrian-remaster/` with a music-only `manifest.json`, so every build, including
the deployed site, offers them (and starts on Synth, D38). `loadRemasterManifest` no longer checks
`localAssetsAllowed`. The remade sound effects and voices (D36) stay in the private repo:
`src/audio/sfx.ts` still only asks for them in local builds, and local builds serve the private
pack (music and effects) at the same path in place of the public one. CREDITS.md credits Alexander
Brandon (and Andreas Molnar), the CC0 VSCO-2-CE and VCSL samples and sfizz.

**Why:** the user decided it. Before acting I reported what I found: the soundtrack is sold as
"all rights reserved" on Brandon's Bandcamp and Materia Collective lists "(P) 2018 Materia
Collective / Materia Music Inc. under exclusive license from Alexander Brandon"; its 2010 free
release is a free download (a Tyrian 2000 bonus on GOG). The user judged that covers are fine, as
others have reused the music without issue, and asked for the music only, with credit.

**Options considered:**
- *Publish the music, keep the effects private (chosen):* what the user asked for.
- *Keep everything private (D18):* the earlier stance.
- *Ask Materia Collective or Brandon first:* still possible; if they object, delete
  `public/tyrian-remaster/` (the game falls back to the original FM music).

**Review:** The deployed site plays the Synth music from the title screen; `M` cycles Original,
Orchestral and Synth. Local builds still play the remade sound effects. The deploy is about 88 MB
bigger.

## D41 — The remade sound effects and voices are public too; anything derived may be

2026-10-29

**Decision:** The 38 remade sound effects and voices (D36) join the music in
`public/tyrian-remaster/sfx/remaster/`, listed in the public manifest, and every build offers the
"remaster" sound style (Options → Sound style, `?sound=remaster`); the default stays the original
sounds. `SoundStyles` no longer checks `localAssetsAllowed`. The user set a standing rule: anything
this project makes that isn't the original game assets themselves may be public, credited to the
original authors it's based on (CREDITS.md); the original data files (tyrian21.zip) still never go
in the repo (D3).

**Options considered:**
- *Publish them (chosen):* the user's rule; they are new syntheses, not copies of tyrian.snd.
- *Keep them local-only (D36):* the earlier stance.

**Review:** On the deployed site, Options → Sound style → Remaster plays the remade sounds; the
original sounds remain the default.

## D42 — Shots and pickups can be drawn flat from remastered art; on where the art exists

2026-10-29

**Decision:** Weapon shots and pickups (power-up orbs, weapon capsules, coins, gems, datacubes) stay
flat 2D sprites, drawn from high-resolution painted art instead of the original pixels, wherever
`public/art/sprites/` has a painting for the sprite (the art pipeline, `tools/flat_art.py`, has its
own entry). The game side (`src/render/spriteArt.ts`, `spriteArtLayer.ts`, hooks in
`drawListRenderer.ts`):
- **Contract.** `public/art/sprites/manifest.json`:
  `{ "scale": 8, "sheets": { "<sheet>": { "image": "<file>", "frames": { "<index>": { "x", "y", "w", "h" } } } } }`.
  `<sheet>` is the draw list's sheet id, `SpriteDraw.sheet.id` / `TableSpriteDraw.table.id`
  (src/sim/resources.ts): `tyrian.shp#7`..`tyrian.shp#11` for tyrian.shp's Sprite2 sheets (#7 is
  spriteSheet8, the shots; #10 spriteSheet11, coins, gems and power-ups; #11 spriteSheet12, more
  shots), `tyrian.shp#0`..`#6` for its sprite tables, `newsh<c>.shp` for the enemy sheets.
  `<index>` is the draw's sprite index as the C passes it: 1-based for Sprite2 sheets, 0-based for
  sprite tables. A frame is the original sprite's box times `scale` (a Sprite2 sprite is 12 wide by
  the rows it decodes to; a table sprite its table width and height), its top-left at the blit
  position. A blit_sprite2x2 draw and a 2x2 enemy are the four tiles index, +1, +19, +20, each with
  its own frame, so art for a 2x2 object should be painted whole and cut into tiles with no soft
  edge along the cuts. `image` is relative to the manifest and URL-escaped when loaded, so a name
  without `#` (e.g. `tyrian-shp-7.webp`) is simplest. Frames are sampled clamped to their own
  rectangle, but mipmaps still reach a few texels out: leave ~8 px of transparent padding between
  frames. Alpha may be straight (not premultiplied); colour comes from the art.
- **Loading.** `main.ts` fetches the manifest at startup and each atlas in the background. No
  manifest (or a bad one) → nothing changes; a sprite missing from the manifest, an atlas still
  loading or failed, or a frame outside its image → that sprite draws exactly as before.
- **Drawing.** A sprite with a painting is a flat quad in the playfield plane at its pass's height,
  placed like every draw (D6: on the camera ray through its screen rectangle, shrunk to keep its
  screen size), so position, size and layering are the original's; the draw list has no flips or
  rotations to honour. For an enemy (a pickup) the object's first tile decides, and a painted object
  is drawn flat instead of as its Blender model (D15); banked player ships keep their models
  unless their sheet is painted. One instanced draw per atlas and pass, rebuilt each frame into
  reused buffers like the halos (D35), unlit and not tone-mapped. Atlases are uploaded
  premultiplied and blended with depth testing, no depth writes, drawn before the other transparent
  draws (renderOrder -1), so explosions, puffs and halos, all in passes above what they overlap,
  land on top.
- **Palette effects** on the art's brightness (the shade 0-15 its luma gives): the enemy hit flash
  (blit_sprite2_filter) and blit_sprite_hv recolour with the palette entry of their hue at that
  shade; "blend" is the usual 55% opacity; JE_filterScreen's level hue recolours the same way and
  its brightness scales the colour; the smoothies' hues (D31) apply by pass height as on palette
  materials. Palette fades and swaps don't reach the art (its colours aren't palette indices).
  Skipped: water_filter's ripple mark (the art is transparent, which the mark doesn't support), and
  shadows (flat art casts none; the extruded shots didn't either).
- **Remastered effects.** Shots keep their halo, trail and muzzle flash (still measured from the
  original sprite), with the painting in place of the hot extruded sprite; pickups get no halo.
- **Switch.** `?sprites=original|remastered`. Without it the sprite art follows the effects look:
  `?vfx=original` draws the original sprites too, the default remastered look draws the art. In
  `?debug=play`, A switches the art (V still switches the effects), and the overlay shows
  `N flat in C` (quads and draw calls).
- **Speed.** `?debug=play&skip=300&freezeAt=330&front=2&power=5&stress=800`: 812 flat quads in 2
  draw calls; the renderer's CPU time was 2.7-3.0 ms a frame with the art and 2.7-3.0 ms without
  (the same as D35's 2-3 ms), at 120 fps, on the dev machine with a synthetic atlas.

**Options considered:**
- *Flat painted quads, one instanced draw per atlas and pass (chosen):* what the art is for (a
  painting has detail the extruder can't keep), and cheap: hundreds of shots cost two draw calls.
- *Paint the art onto the extruded meshes:* keeps some depth, but the extrusion's rounded walls
  stretch the painting at the edges, and every sprite is still a mesh.
- *Palette-quantised art (indices, like the ground in D34):* palette effects would be exact, but the
  painting's colours would collapse to 16 shades per hue; luma-to-shade recolouring gives the hit
  flash and filters at the cost of exactness only while they're on.
- *Alpha test with depth writes:* sorts by depth with no ordering rules, but the soft edges would be
  cut hard and the camera-facing halos would be clipped where they pass behind the quad.
- *Keep pickups as models:* they read as 3D objects, but the request is flat painted pickups;
  the manifest decides per sprite, so a pickup the art leaves out keeps its model.
- *Its own Options row:* the Options screen has only the sound and music styles; the effects and
  background looks (D34, D35) are URL options too, so the art follows them rather than adding the
  first graphics row on its own. A "Graphics" section with all three is the natural next step.

**Review:** With the real atlases committed, play TYRIAN with `?debug=play` (A switches the art, N
the weapon) and compare: shots under their halos, coins and power-ups in flight, the hit flash on
anything painted that can be hit, a level filter fade. Check a 2x2 pickup for seams between its
tiles, and a dense screen with `&stress=800` for CPU time.

## D43 — Flat remastered sprites: Gemini paints input sheets; a cutter fits each painting to its sprite

2026-10-29

**Decision:** The art D42 draws is made by Google Gemini from input sheets of the original sprites
and brought back by `tools/flat_art.py`:
- **Inventory** (first level, TYRIAN): found empirically by playing the level headless with the real
  game loop and the play harness's bot and recording every draw: story mode with the starting
  Pulse-Cannon and each first-shop front weapon, arcade mode (where power-up orbs and capsules
  spawn), every front and rear weapon of the first shop at power 1-11 and in both rear modes, and
  the first shop's sidekicks; then cross-checked against the level's enemy types' turret weapons and
  the weapon ports' op tables. 71 shot sprites (tyrian.shp#7), 76 pickup tiles on tyrian.shp#10
  (coins, gems, the colour-cycling datacube) and 32 on tyrian.shp#9 (power-up orb, weapon and
  sidekick capsules, arcade mode only): 179 atlas frames.
- **Input sheets** (`flat_art.py sheets`, kept out of git as they're rendered from the game data,
  D3): one family per sheet (Pulse and front Multi-Cannon; rear Multi-Cannon; Sonic Wave; the
  other shots; coins; gems; datacubes; orbs and capsules), at most 12 cells of 256 px in 3 or 4
  columns, each sprite scaled up nearest-neighbour by one integer per sheet so the biggest fills
  60% of a cell (small shots come out bigger), centred, on black. A sprite that is another's mirror
  image shares its cell (23 pairs), so Gemini paints it once and both stay symmetric. A
  `manifest.json` beside the sheets says where each picture sits and which atlas frames it feeds.
- **Cutter** (`flat_art.py cut`): for each cell of Gemini's answer (any size, same aspect), the
  art's brightest pixels, as many as the sprite would cover, are its foreground, so a glow or halo
  Gemini adds is left out; the sprite's visible pixels are fitted onto it by scale (0.8-1.25x,
  aspect 0.9-1.1) and shift (FFT cross-correlation, within a fifth of a cell), best Dice overlap.
  Each frame is resampled from the art at 8 texels per sprite pixel; its alpha is the original
  silhouette upscaled smoothly (blurred, then a steep ramp: rounded staircases, a ~1.5 texel soft
  edge), computed over the whole picture so a 2x2 object's tiles meet without seams; colour under
  zero alpha is bled from the nearest visible texel. Frames are shelf-packed per original sheet
  into an RGBA WebP with 8 texels of edge-extended padding. `--check` writes a contact sheet,
  original (8x nearest) | remastered, with each fit's score.
- **Placeholder:** the committed atlases cut the earlier concept paintings
  (`assets/blender/features/concepts/l1-*.jpg`, made from crops of the 4x sprite sheets): 33 of
  the 179 frames (rear Multi-Cannon 1/2/3/5 and their mirrors, Sonic Wave 6/44, bomb 20, the gold
  coin's spin squashed from its face, the green gem, three weapon capsules). The rest draw as
  before until the new sheets come back.

**Options considered:**
- *Gemini paints whole sheets of sprites, a cutter registers each painting to its sprite (chosen):*
  Gemini keeps a grid well and paints a family consistently in one go; the registration absorbs its
  small shifts, rescaling and glow, and the original silhouette as alpha keeps the outline and the
  hitbox read exactly the original's.
- *Gemini's own outline as alpha (background removal):* richer edges, but shapes drift from the
  hitbox and glows become part of the sprite.
- *One request per sprite:* exact framing, but ~150 requests and no consistency across a weapon's
  frames.
- *Algorithmic upscaling only (MMPX/xBR, as the ground in D34):* deterministic and free, but stays
  pixel art; the point here is painted detail.
- *Hand-placed crops:* no fitting code, but every new answer would need hand work.
- *Static inventory from the data only:* misses what play actually draws (and lists pattern slots
  never fired), so play is the source and the data a cross-check.

**Review:** After Gemini answers the 11 sheets, run `python tools/flat_art.py cut --inputs
<sheets>/manifest.json --results <answers> --check check.png` and look at the contact sheet: fit
scores under ~0.5 or a painting that's off its silhouette mean the cell needs a retry (or a
`search`/`scale` edit in the manifest). Known limits: the fit is a scale and shift only (no
rotation); animation frames painted in separate cells may differ more than the original's frames
did; tyrian.shp#5 table sprites (Plasma Storm's shots) and other levels aren't covered yet. To
extend to another level, record its draws the same way and add its families to `SHEET_GROUPS`.

## D44 — Models follow their concept image, then wear it: concept-placed geometry, baked concept detail

2026-10-29

**Decision:** The first level's enemies, structures and the player ships are rebuilt with their
Gemini concept image (`assets/blender/features/concepts/`) as the base, then textured from it.
- **Registration:** `tools/concept_maps.py <name>` lines the concept up with the sprite (the
  sprite's mask is the object mask) and writes `assets/blender/textures/<name>/` (the aligned
  concept, a detail map, a height map, the mask and `maps.json`). A tile structure uses
  `tile:<entry> --concept <name>` and its tiles' mask.
- **Geometry:** each part is placed where the concept draws it, in sprite-pixel coordinates read
  off the aligned concept, with the concept's shape language, while the outline stays inside the
  sprite's (the hitbox read) and materials stay palette materials (`pal_<index>`), so palettes,
  fades and the hit flash still apply.
- **Texture:** `assets/blender/texture_bake.py <name>` runs on a freshly built model: a planar
  "concept" UV and a smart-projected bake UV, an emission bake of the concept's detail on
  upward-facing surfaces times ambient occlusion, and a normal map from the height map. The
  material becomes `Base Color = palette colour × detail` plus the normal map, so the game needs
  no change (the palette still sets `material.color`). Maps are exported as WebP inside the .glb
  (`common.export_glb(image_format="WEBP")`): a textured ship is ~230 KB instead of ~690 KB as
  PNG. Bake intermediates (`textures/*/bake/`) are not tracked.
- **Process:** one agent per model (remodel, build, bake, render), then a grader against the
  previous model; a fix round when asked, a revert when worse. All 33 first-level models and
  ships were kept (3.5–4/5). The four long-strip structures got new full-length concepts first.
- **Shared-tile structures:** map 1-3's buildings use tiles that also occur as plain terrain, so a
  tile pattern can say `minRows`: it is placed only once that many of its rows are on screen and
  every drawn cell matches. A real-map test checks that the rows always tell it apart.

**Options considered:**
- *Concept-placed geometry plus baked concept detail (chosen):* the detail lands on the part it
  belongs to; the pilot (bake onto the old geometry) put cockpits on plain plates.
- *Bake only, keep the old geometry:* cheapest, but misaligned detail where shapes differ.
- *Hand-painted or generated PBR textures per model:* richer, but far more work per model and a
  second source of truth beside the concept.
- *Follow the sprite's outline exactly:* best hitbox match, but fights the concept where it is
  narrower; inside-the-sprite was the compromise.
- *PNG/JPEG/KTX2 maps:* PNG is 3x larger; JPEG has no alpha and worse normals; KTX2 needs a
  transcoder in the page. WebP is supported by three.js's GLTFLoader natively.

**Review:** Look at the models in play (`?debug=level&main=1`) from the game camera. Known limits:
steep sides get no concept detail; small grooves are texture only; concept glows aren't emissive
maps; some models cover noticeably less of the sprite outline (U-Ship 0.76, newsh2-87 0.79,
newshp-13 0.80 IoU) because they follow the concept; assembly-newsh2-273 ended at 3/5 with polish
left. Fallback: revert a model's script from git history and rebuild without the bake.

## D45 — Background 2 is drawn blended, as flat translucent sheets, like the C at processorType 4

2026-10-29

**Decision:** The port plays at processorType 4 (Pentium, D31), where JE_initProcessorType sets
`wild`, so background 2 is drawn with draw_background_2_blend unless an event sets
background2notTransparent; the sim had `wild: false`, so TYRIAN's ice clouds came out opaque. Now
`wild: true` (it only chooses which background-2 draw is made). Blended background-2 tiles
(`effect: "blend"`) are drawn as flat translucent quads at their pass height instead of extruded
tiles: in the original look from the tile atlas (`groundTileMaterial(…, blend)`), in the remastered
look upscaled in context with the ground (`RemasterGroundAtlas` gives them slots, against their empty
neighbours, so the outline comes out smooth; `remasterGroundMaterial(…, blend)` blends the four
texels weighted by coverage). Index 0 is see-through, the rest is drawn at `BLEND_ALPHA` (0.55), no
depth write, no outline, no shadow. The sheets draw before other translucent draws (renderOrder -1;
+1 for background2over 2, drawn over everything). Translucent sprites and models no longer get the
outline shell: OutlineEffect drew it opaque behind them (it reads material.opacity, and the
instanced sprites' alpha is per instance), which turned the clouds into a flat olive sheet and put a
dark husk inside the invulnerable ship.

What the C draws translucent in play, and how it's drawn here:
- Background 2 (draw_background_2_blend: the tile's hue, value averaged with what's under it):
  this entry.
- Explosions (blit_sprite2_blend, explosionTransparent): translucent sprites, or the remastered
  fire (D35).
- The ship while invulnerable (blit_sprite2x2_blend): the model at BLEND_ALPHA, now without outline.
- Special-weapon shots from OPTION_SHAPES (blit_sprite_blend): translucent sprites or flat art.
- Shadows (blit_sprite2_darken): replaced by real shadows (D9). JE_darkenBackground (superWild) is
  not at processorType 4.

**Options considered:**
- *`wild` as at processorType 4, flat translucent sheets (chosen):* the same draws the C makes at
  the port's detail level, and a sheet reads as cloud.
- *Leave `wild` false and blend layer 1 in the renderer:* no sim change, but it would also blend
  where an event asks for an opaque background 2.
- *Extruded tiles at BLEND_ALPHA (what "blend" tiles did before):* their sides double up at every
  tile seam into a grid of bright lines.
- *The C's exact blend (cloud hue, averaged value):* needs the colour underneath; with a fixed
  blend it would take a multiply pass and an add pass per sheet. Plain alpha reads the same way.

**Review:** Play TYRIAN (`?debug=play&seed=1&skip=220&freezeAt=220`, with and without
`&bg=remaster`): the ice clouds should show the ground and ground enemies through them. The C keeps
the cloud's hue and averages brightness, so its clouds are bluer over dark ground than this alpha
blend; if that matters, try the two-pass blend.

## D46 — A model's frames are textured together, and a build textures what has concept maps

2026-10-29

**Decision:** texture_bake.py textures a model's other animation frames (`<name>-f<k>`, one model
per frame) with the first: a frame with the same faces as the first (the same parts moved or
turned) takes its texture and bake UVs face corner by face corner, so the detail turns with the
parts; one with a different mesh is baked on its own from the same maps. tools/build-models.sh runs
the bake right after building any model with concept maps (`-n` skips it). newsh2-229 (the spinning
ring drones in TYRIAN) no longer textures its own frames in its build script.

The drones flashed light and dark because frame 229 was plain while f2-f8 were textured: the
bake textured only the first .glb, so the script baked f2-f8 itself, and the model was rebuilt
after its bake, which left frame 229 plain. Its frames' bake was also much darker than the bake now
is (probably because it ran with all eight frame models overlapping in the scene, where the
ambient occlusion sees the other frames; not checked further).

**Options considered:**
- *Bake every frame in texture_bake.py, and bake in the build (chosen):* one place, and a rebuild
  can't drop textures.
- *Fix newsh2-229 only (rebake its first frame):* fixes the flash, but the next rebuild without a
  bake brings it back, and the other multi-frame models with concept maps would flash once baked.
- *Bake each frame separately always:* simpler, but a turned part's detail stays put on screen
  instead of turning with it.

**Review:** In this commit only newsh2-229 is rebuilt and rebaked. The other models with concept
maps (D44) are plain in git: the commit that made them was rebuilt after its bakes, so it carries
no textures for any enemy or ship (only the seven map 1-3 tile structures and newsh2-229's frames
had them). `tools/build-models.sh $(script for each textures/<name>/)` rebuilds and textures them
(assemblies need `tools/sprite_shape.py <name>` first); several rebuilt models came out not
byte-identical to git, so check them in `?debug=models` before committing.

## D47 — TYRIAN's buildings are whole-structure models from concepts; the biggest matching pattern wins

2026-10-29

**Decision:** The first level (TYRIAN, map 1-9) gets concept-based models for its buildings, the
way map 1-3's got them (D44), while terrain (forest, dirt, roads, clouds, plain rock islands) keeps
its current look. A scout mapped 16 structure types (`assets/blender/features/concepts/
tyr-structures.json`, plan in `assets/blender/tiles/tyrbld_patterns.json`): on the ground the two
bunkers and the wreck (which stand on their tiles); on layer 2 the floating fortress (one 45x15
model from three stitched concept parts), the full-width bridges, white gates, drums, purple carved
blocks (cross, orb, 2x2, 2x3, 2x5), lava pits and craters (which replace their tiles and carry the
rock their tiles paint). `lib_tyrbld.py` (on a generalised `lib_l1bld.py`) supplies the shared
kits: rock islands, metal walkways from the walkway tiles' own pixels, carved purple stone,
lathed and extruded parts, emissive lights. `TileModelIndex` now tries the biggest pattern first,
so a structure wins over the per-tile models of its tiles, which stay as fallbacks (a minRows
structure with one row on screen; other levels). Same-size replacements (the old bunkers and
wreck, tiles 143/153/189/199) are removed. A real-map test checks every pattern is told apart
from the others and from terrain in every level.

**Options considered:**
- *Whole-structure models with biggest-pattern priority (chosen):* one coherent object per
  building, detail lines up across tile seams, and the old per-tile models remain a safe fallback.
- *Re-texture the existing per-tile models from the concepts:* no matching changes, but tile seams
  stay visible and walkways can't get continuous rails.
- *Leave buildings covered by enemies (bunkers, wreck, purple blocks, orb, lava pits) as they
  were:* less work, but they show after kills and would look older than their neighbours.

**Review:** Play TYRIAN with `?bg=remaster`. The bridge (2.4 MB) and fortress (1.9 MB) models carry
large textures; drop their bake size (`texture_bake.py --size`) if loading matters. Graders left
polish items: bridge and purple orb (4/5), crater, lava pit and wreck (3/5). Fallback: delete a
`shapesz-tyrbld-*.json` entry and restore the old per-tile entry from git history.

## D48 — Remastered backgrounds are the default; `?bg=original` opts out

2026-10-29

**Decision:** `Settings.background` now defaults to `remaster` (D34); only `?bg=original` picks the
original's extruded tiles (D8). With the first level's buildings modelled (D47), the old default
meant a player saw flat pixel bunkers unless they knew the switch. The game, `?debug=play`,
`?debug=level` and `?debug=sprites` all read the same setting. Like the effects (`?vfx=`) and sprite
art (`?sprites=`) looks, it's a URL option only: there's no Options row and nothing is stored. Levels
other than TYRIAN get the upscaled ground and keep their original structure tiles until they have
models.

**Options considered:**
- *Default to remaster, URL opt-out (chosen):* matches the effects look (remastered by default since
  D35) and needs no new UI.
- *An Options row stored in the prefs:* lets players switch without the URL, but the other looks
  aren't there either; worth doing for all three together.
- *Keep `original` until every tileset has models:* consistent, but hides the finished first level.

**Review:** Play TYRIAN with no options and check the 3D bunkers, fortresses and bridges; play a
later level and check the upscaled ground holds up without structure models. Fallback: flip the
default back in `src/core/settings.ts`.

## D49 — Sidekicks can be models: `ungrouped` sprite-model entries, catalogued like enemies

2026-10-29

**Decision:** The player's sidekicks (options) get the enemies' model path (D15). JE_playerMovement
draws each sidekick on its own at `gr[animation_frame] + charge`: `blit_sprite2` from tyrian.shp#8
(the ship sheet), or for styles (`tr`) 1 and 2 `blit_sprite2x2` from tyrian.shp#9 at x - 6. Those
draws have no `drawGroup`, so the grouped (enemy) lookup never saw them. A `SpriteRef` can now say
`"ungrouped": true`: `spriteModels()` indexes it in its own `ungrouped` map (frames are still
claimed against every other model), and the renderer replaces an ungrouped sprite2 draw of such a
frame with the model, centred on the sprite and showing the frame drawn (D17 animation). With no
entries, or a model still loading, every sidekick draws as before. `npm run catalogue` writes each
sidekick's `reference/models/sidekick-<name>/` (options that share frames are one model; the items
are in `sprite.json` `sidekicks`) and `sidekicks.json`, not `catalogue.json`, so the enemy
coverage test doesn't count them; `CATALOGUE_SIDEKICKS_ONLY=1` writes just those.

**Options considered:**
- *A separate `ungrouped` entry kind (chosen):* no draw that works today can change, and
  `export_sprite_model` writes it from `load_sprite(...)["sprites"]` unchanged.
- *Look ungrouped draws up in the grouped map:* no new field, but any loose draw of an enemy's
  frame (now or in later ports) would silently turn into that enemy's model.
- *Have the sim set `drawGroup` for sidekicks:* touches the transliterated C for a renderer concern.

**Review:** `?debug=play&left=9&right=16` (and `?debug=models` for a built sidekick) once a model
exists. Fallback: delete the sidekick's `src/render/spriteModels/` entry.

## D50 — The USP Talon is a hand-built flagship: blueprint geometry, modelled detail, no concept bake

2026-10-29

**Decision:** The Talon (the starting ship, large and turning in the menus) is rebuilt by
`assets/blender/usp_talon.py` as a hard-surface model from a multi-view blueprint drawn for it (top,
side, front, rear and underside views in sprite px) and the top-down concept, inside the sprite's
outline. The concept's detail is no longer baked onto it: its maps.json says `"bake": "model"`, so
tools/build-models.sh and texture_bake.py skip it, and the script bakes its own small maps
instead.
- **Geometry:** dark gunmetal cores (pchip-interpolated stations, so lofts never swell) under
  separate brass armour plates that stand 0.15-0.5 px proud with 45-degree chamfers, so panel lines
  are real gaps. Flat faces stay flat (sharp by angle, weighted normals); only fillets, the
  nacelle domes and the glass are smooth. The nacelles have a chamfered, filleted octagon section
  (not a superellipse), armour petals over their front domes and a deep blackened seam; the nose
  has a split spine and thick inner and outer panels; the canopy a sill and a proud cross frame;
  the belly a nose gear door, nacelle gear doors, intakes and ventral pylons. 11.7k triangles,
  hidden faces culled.
- **Texture:** a Cycles bake of ambient occlusion at two scales with an edge lift (a colour
  multiplier) and a roughness/metalness map (crevices rougher, edges polished), WebP in the .glb.
  No normal map. Base Color = map x palette colour, as in D44.
- **Materials:** all palette materials, including the glows (orange 121/123, red 118 and green 204
  navigation lights, emissive), so fades and the hit flash cover the whole ship. The brass is a
  step lighter than the sprite's mid-tone (26) with a duller belly (24, less metallic) and a darker
  frame (19, 21).
- **Process:** three designers built from the blueprint, two judges rendered all three from every
  angle and in game, and the winner (C) took grafts from the others (A's nacelle section, seam band
  and underside; B's thick nose plates) and the judges' fixes (pod domes, belly, brightness,
  outline overspill 1.6 to 0.3 px², cross frame).
- `common.export_sprite_model` takes `image_format` (default unchanged), so a self-baked model
  exports its maps as WebP in one pass; tools/concept_maps.py keeps a maps.json's `bake` key.

**Options considered:**
- *Modelled detail plus a light occlusion bake (chosen):* the user saw the concept bake as "wrinkled
  tinfoil" up close: the concept projected straight down smears on curved and steep surfaces, and
  its normal map crinkles the brass. Modelled panel lines read the same from every angle.
- *Keep the concept bake on flat, upward-facing plates only, with a weak normal map:* keeps the
  concept's grime, but the Talon is seen from the side and below in the menus, where the plates
  would differ from the rest; and the sharp modelled panels already carry the layout.
- *Riveted plates with a full normal map (designer B):* realistic at a glance, but the rivets read as
  dimples up close, the same family of problem.

**Review:** `?debug=models&model=usp_talon`, the title screen, and the item screen's hangar view.
Known limits: the menu backdrop's single engine glow sprite sits between the twin nozzles (it is
placed at the model's tail centre for every ship); OutlineEffect shows small breaks along hard
edges at large sizes; the .glb is ~740 KB (geometry with split normals plus a 1024 px map). Fallback:
the previous script is in git history (rebuild it with `"bake"` removed from maps.json).

## D51 — Talon flagship finish: an outline shell, twin engine glows, a depth prepass when translucent

2026-10-29

**Decision:** The review of D50 found the ship's worst flaws in the menu, where the user judges it,
and a few local modelling faults. Fixed as follows.
- **Outline shell.** OutlineEffect (an inverted hull pushed out along the vertex normals) broke into
  whiskers and doubled strokes on the Talon: its hard edges have split normals and every armour
  plate is its own shell. `common.outline_shell` now exports a smooth closed copy beside the model
  (voxel remesh at 0.012, which closes the panel gaps; smoothed; ~3k triangles; node extra
  `tyrian_outline`). `src/render/modelPrep.ts` (run on every loaded model: loadModel, the model
  viewer) gives the shell a material that writes neither colour nor depth and casts no shadow, and
  turns the model's own outline off, so the outline is one clean contour with the same thickness
  and colour as before. Models without a shell are unchanged.
- **Engine glows.** The menu backdrop put one cyan glow at the tail centre of every ship, a stray
  ball between the Talon's two orange nozzles. A model can now name its engines (object custom
  property `tyrian_engines: {color, at: [[x, y, z], ...]}`, glTF axes): the Talon gets two orange
  glows (palette 121's hue) just behind its nozzles. Ships without it keep the single cyan glow.
- **Depth prepass while translucent.** Drawn translucent (the "blend" effect, e.g. invulnerable),
  a layered model showed its inner cores and plate skirts as dark bands. prepareModel adds a hidden
  depth-only mesh of the whole model (frame-tagged parts left out); setModelBlended shows it and
  draws the model after the particles and glows (renderOrder 3, the prepass just before), so only
  the outer surface blends over what is under it. Cost: a transparent effect *above* a translucent
  model is overdrawn by it rather than over it (only while the model is translucent).
- **Model.** The two-piece shoulder sponson is gone: it ran through the nacelle fronts and the
  flank plates and made the crumpled foil-like shards at the nose/nacelle junction and the Z notch
  on the flank. The nacelles already fill the sprite's outline there; the flank plates now end
  before the nacelle front with a clean gap and the front armour petals start at row 13.2, behind
  a gunmetal nose cap. The tail plate is a boat-tail sloping from the rear hatch to a thin trailing
  edge between the nozzles (it read as a flat shelf). The nacelle tails have a dark end-cap ring
  behind a panel break and a raised boss on the bulkhead, so the rear is not one smooth pillow.
  12.1k triangles plus the 3k shell; top view IoU 0.91 with the sprite, 0.3 px² outside it.
- `?debug=play&solid=1` plays the bot without invulnerability (armour kept topped up), so the ship
  can be checked opaque in play.

**Options considered:**
- *Smooth outline normals in a vertex attribute:* needs a copy of OutlineEffect's shader, and the
  inverted hull of each separate plate still strokes every panel line.
- *No outline on the menu ship:* the sprites' ink edge is part of the look (view.ts OUTLINE), and in play the
  ship would differ from the menu.
- *Hide the cores while translucent instead of a prepass:* the plate skirts and the nacelle shells
  overlap each other too; only a depth prepass gives one surface.

**Review:** the title screen (twin glows, one contour), `?debug=play` (translucent, no inner bands)
and `?debug=play&solid=1` (opaque), `?debug=models&model=usp_talon`. D50's known limits (single
glow, outline breaks) are resolved by this entry. The .glb is ~815 KB.

## D52 — The Talon's sprite is authoritative for its outline, windshield and colours

2026-10-29

**Decision:** The user liked D50/D51's ship but it "doesn't match the overhead outline and cockpit
windshield of the original", and its colours should match "to make it truly feel like an extension
of the original". From now on the original sprite (frame 233) decides the Talon's top-down
silhouette, the windshield's position, size and shape, and the major colours; the blueprint and the
concept only guide the side and front design and the detail where they agree with it.
`assets/blender/usp_talon.py`:
- **Outline:** the plan half width is a smooth pchip curve (`PLAN`) fitted to the sprite's mask
  including its dark outline ring (the hitbox read): a pointed nose widening steadily, no tiers, to
  the pods' round bulge at rows 19-21, a rounded rear and a short narrow tail. The fuselage follows it
  to row 12, the two engine pods' outboard sides from there (their noses buried in the fuselage's
  flank so they blend into it, their inboard sides tucked in at the sprite's dark seam), the tail its
  last rows; each core is inset by the plates that stand on it. Gone: the tiered nose, the square
  shoulders, the boxy outboard armour caps, the vent blocks, the boat-tail plate and the chevron
  block; the nozzles sit in the pods' rounded tails and the tail ends in a recessed vented face.
  Top view vs the sprite: IoU 1.00 on the sprite's grid (each sprite pixel covered at least half),
  0.957 at 20 px per sprite pixel. A smooth outline cannot do much better at that resolution (a
  best-fit smooth curve reaches ~0.962; 0.97 needs the outline to follow the pixel staircase, the
  tiers the user objected to).
- **Windshield:** small, dark and glossy, framed, exactly over the sprite's cockpit pixels (rows
  9.1-11.95, |x| <= 1.8, pointed forward), instead of D50's large canopy further back. The bright
  centre pixels behind it (rows 12-14 and on along the rear body) are sheen on a raised dorsal
  spine, not glass (tools/calibration/rubric.md).
- **Colours:** each part takes the palette index the sprite uses where it covers it (the median of
  those pixels, the darkest shading 16-18 and the highlights 29-31 left out as lighting): nose and
  hatch 24, nose panels, deck, belts and the pods' front cowls 23, the spine 26 with 27 strips, pod
  shells 24 and top panels 25, pod tails and flanks 22, shading 19, recesses and glass 16. Metalness
  scaled to 0.3-0.42 (satin), so the menu's warm light no longer turns it saturated brass. The
  game-lit top view vs the sprite: mean colour dE76 2.1 for the whole ship, 1.7-3.9 per region (the
  windshield 14: the glass is darker than the sprite's mixed cockpit pixels).

**Options considered:**
- *Follow the pixel staircase to push the fine IoU past 0.97:* reintroduces steps in the outline.
- *Keep D50's brighter brass (26, metallic 0.8):* reads as yellow-gold beside the original's khaki.
- *Keep the large canopy:* it sat over the sprite's spine highlight, which is sheen, not glass.

**Review:** the title screen, `?debug=play&solid=1&skip=200`, `?debug=models&model=usp_talon`. The
measurement scripts (top orthographic renders on the sprite grid, IoU, per-row widths, windshield
overlay, per-region colours) are not in the repo; the numbers above are from them. The .glb is
~780 KB.

## D53 — The Talon's colours are measured in the game's own render; no dark bands across the pods

2026-10-29

**Decision:** A review of D52 found the ship still read bronze/brass in the game, not the sprite's
sandy khaki: ship pixels in real captures of the title menu and of `?debug=play` measured HSV
saturation 0.66-0.68 and blue/red 0.33 against the sprite's 0.55 and 0.45 (its pixels of index 19
and up), although the palette indices were right. D52's "game-lit dE 2.1" came from a Blender
approximation of the game's light, which leaves out three's Neutral tone mapping (it subtracts a
small offset from every channel, so the smallest one, blue, loses the most). Colours are now judged
on headless-Chrome captures of the game itself. `assets/blender/usp_talon.py`:
- **Colour:** metalness scale 0.7 -> 0.3 (hull, pods and trim 0.15-0.18 metallic, satin), and the
  baked colour map carries a slight cool tint (`TINT`, linear 0.76 / 0.86 / 1.0; the map cannot go
  above 1, so red and green come down rather than blue up), its occlusion floor raised a little to
  keep the brightness. Captures now measure saturation 0.57 and blue/red 0.43 in both the title menu
  and play (the pods in play 0.55-0.60). The flat (unlit) top view moves a few dE from the bare
  palette (whole ship 6.0), the price of matching where it is seen.
- **No dark bands across the pods and body:** the sprite's seams run lengthwise. Gone: the louvre
  grille across the pods' tops and the grille between the body's belts (one plate now, split along
  either side of the spine), and the spine runs unbroken to the tail. The pods' long top panels run
  from the cowl over the cowl/shell seam (now shallow) to the tail, in two strips with a lengthwise
  seam and an access hatch. This also fixes `pod_s`, which turned small inboard angles into a
  full extra turn, so D52's "top panel" wrapped right round each pod.
- **Detail:** the blade antenna on the spine is gone (dark and thin, it read as a tiny figure standing
  on the spine). The pods' rear halves get a lengthwise flank seam, louvres low on the outboard flank,
  a tail cap in four petals, and nozzle shrouds; the nozzles move out to the pods' tail centres.
- Outline and windshield unchanged: IoU 1.00 on the sprite's grid, 0.959 at 20 px per sprite px.

**Not changed:** the game's ink outline (src/render/view.ts, all models) draws outside the model, so
the Talon's dark contour sits about a sprite pixel outside the sprite's own ring, and its colour is
(0.07, 0.035, 0) linear, (75, 53, 0) on screen, not the ring's near-black (16, 8, 0). Changing it is
a call for every model, not this one.

**Options considered:**
- *Lower metalness only:* at 0.05-0.15 metallic the captures still measured saturation ~0.59-0.6.
- *Lighter palette indices:* would break the sprite's per-region indices (D52).
- *Change the game's lights or tone mapping:* affects every model and the ground.

**Review:** the title screen, `?debug=play&solid=1&skip=400&freezeAt=402` (the ship over water,
which makes its pixels easy to separate). The capture and measurement scripts are not in the repo.

## D54 — A level's models load before it starts; an enemy is drawn one way for its life

2026-11-02

**Problem:** in TYRIAN (level 1) enemies appeared as extruded sprites and then popped into their
models. A model's .glb was fetched the first time its sprite was drawn, and the sprite stood in
until it arrived, so on the deployed site with a cold cache most first appearances popped (level 1
needs about 16 MB of enemy models and 16 MB of structure models). A detector also looked for
frame-coverage swaps (animation frames without a model).

**Decision:**
- **Preload** (`DrawListRenderer.preloadLevel`, `src/app/levelPreload.ts`): after `startLevel` and
  before the first tick (the game, the attract demos, `?debug=play`, `?debug=level`), the level's
  models load: `src/sim/levelSprites.ts` lists every sprite the level can draw (every enemy type any
  event names, the random spawns, what they launch or leave behind, each with all its egraphic
  frames and its damaged graphic, on the sheet of its shape bank if an event of the level loads it;
  the players' ships, two-half ships and sidekicks with their charge frames), with roughly when each
  is first needed (its event's time), and the background tiles with when they scroll in, which pick
  the structure models (`TileModelIndex.modelsOfTiles`; previously the first tile drawn fetched the
  whole tileset). Loads go earliest needed first, six at a time (on-demand loads skip the queue), and
  reuse what's loaded. The level starts once what's due in its first 1000 curLoc (~30 s of play,
  `PRELOAD_WAIT_LOC`; level 1: ~10 MB) and the sprite art have loaded, or after 20 s; the rest load
  in the background while it plays. A status line shows the count if the wait passes 200 ms.
- **Never pop** (`DrawListRenderer.objectLook`): each object (an enemy, its four quarters sharing
  one key; a ship; a sidekick) is decided when it first needs a model: its model if loaded; held back
  (drawn as nothing) for up to `HOLD_MS` = 250 ms if the model is loading; else, or once the hold
  runs out, its extruded sprite **for its whole life**, even after the model arrives (later enemies
  of the type get the model). A model that fails to load: the sprite at once. A model-drawn object
  whose next frame's model isn't in yet is held back that frame. Structures likewise: tiles or model
  decided when one comes into view, kept while it stays in view.
- **Frame coverage** (`tests/render/modelSwap.test.ts`): plays level 1 with the bot and routes every
  draw as the renderer does (`src/render/sprite2Route.ts`, shared with the renderer). The only enemies
  that mix are 19 pieces whose **damaged** frames have no model: the rocks of newshe.shp (types
  522-527, frames 7, 9, 11, 45, 47, 49: shot away they show blue beneath) and the pieces of the large
  multi-part enemy of newsh4.shp (types 46-63, frames 162, 164, 168, 170, 200, 202, 206, 208, 240, 242, 244, 246, 280:
  battle damage). They turn from model to sprite when damaged; that is a real change of look, so
  they aren't mapped to their undamaged models, and 19 damaged models is more than a small fix. They
  are listed in the test (`KNOWN_DAMAGE_SWAPS`), which fails on any other mix. The test also checks,
  over every level of episode 1, that every model a level shows is in its preload list.

**Options considered:**
- *Hide every enemy until its model loads* (the earlier WIP): on a slow network enemies would be
  invisible and still shooting. Rejected for the short hold plus a lifetime choice.
- *Preload every model of every sheet the level loads:* simpler, but loads models of enemy types the
  level never makes; the per-type list for level 1 is 150 models (122 actually shown in a bot run).
- *Wait for all of the level's models:* 32 MB before level 1 starts on a cold cache. The time-ordered
  queue starts the level after the first third.
- *Map damaged frames to the undamaged model:* hides the damage the game shows.

**Review:** `tests/render/modelPop.test.ts` (a delayed loader: hold, lifetime sprite, failure,
queue order, concurrency, wait horizon, timeout), `tests/render/modelSwap.test.ts`. In Chrome
through a throttling proxy with no cache (no revalidation, `no-store`): at 1.5 MB/s level 1 started
after ~9 s with every enemy drawn as its model from its first frame (107 objects, none held or
sprite, no structure as tiles); at 200 KB/s the preload gave up at 20 s with 12 of 72 loaded, and over
the next 2300 frames 25 objects were sprites for life, 11 were held and then models, and nothing
went from sprite to model. On `main` the same run shows extruded enemies beside models. `?debug=play`
takes `&preload=0` to start without waiting.
## D55 — The ink outline is converted from sRGB; the menu ship goes where the panels leave room

**Outline.** OutlineEffect reads `defaultColor` as linear working-space values, so the (0.07, 0.035, 0)
that stood for palette 16, (16, 8, 0), rendered as olive-brown (75, 53, 0) (D53 noted it). Every
outline now takes `INK_OUTLINE` (src/render/outlineColor.ts), (16, 8, 0) converted from sRGB, so it
draws as the sprites' near-black ring: the game View, the menu backdrop, the model viewer and the
destruct renderer (whose own 0.05, 0.03, 0 guess is replaced by the same ink).

**Menu ship.** The title and hangar poses put the ship at a fixed off-centre spot, but the panels
are centred and 28 to 60 rem wide, so at common window sizes the Talon sat partly or wholly behind
them (hangar frameX -0.62 clipped it at the left). The backdrop now measures the top screen's
panels each frame and puts the ship in the best gap beside, above or below them (the pose's side
favoured by 15%), scaled so its reach (a circle on the ground seen from the camera's elevation, plus
height and bob) fits with a 14 px margin, never larger than the pose's scale (`freeSlot`). Panels'
design is untouched. Where no gap takes the ship at a quarter of its scale (phones, where the panel
fills the window) the pose's own framing stays, the ship behind the panel as before.

**Known limit.** At 1126x720 the hangar's 960 px panel leaves only a strip below it, so the Talon
is small there (about half scale); at 1280x800 and up it sits large beside the panel.

## D56 — The armour ship and its crates are models; the Vulcan Cannon's bullets are painted tracers

2026-11-02

**Armour ship.** When a player's armour is under 6, JE_main's low-armour warning (tyrian2.c
L1872-1893, `armorWarning` in src/sim/game.ts) spawns enemy type 560 every 500 ticks: tyrian.shp#10
(Coins&Gems, shape bank 21) frame 279, a 2x2 object, armour 4, which leaves one of the crates
561-563 at random (frames 127, 129, 131: +2, +4, +8 armour). No event names them, so the catalogue,
the preload list and the swap detector (whose bot keeps 10 armour) never met them, and they were
drawn as extruded sprites, as was every crate but 129 (modelled for level 3.25).
- Models: `assets/blender/enemies/tyrian10-279.py`, built with the Talon's hard-surface toolkit
  (D50): the sprite's plan (outline ring included, on its column-12 axis), a red wing bar with the
  lit crease of column 6, a fuselage tapering to the nose at the bottom (it flies down the screen)
  with a spine and twin ridges, round brown pods with a collar and a groove (the dark row 12), two
  engines behind the wing (the lit round tops of rows 0-1), no canopy (the sprite has no glass);
  palette materials at the sprite's mid-tones, baked occlusion, an outline shell. One frame, no
  damaged graphic. `tyrian10-127.py` and `tyrian10-131.py` are the strapped crate's block
  (`tyrian10-129.py`) without straps, in the grey and blue of their sprites.
- Catalogue: `CONDITIONAL_SPAWNS` (tests/tools/spriteCatalogue.test.ts) adds types 560-563 to every
  run; `CATALOGUE_SPAWNS_ONLY=1` writes just their missing folders.
- Preload: `levelSprites` adds `ARMOR_SHIP_TYPES` to every level at time 0 (the ship can come at any
  time; about 330 KB).
- Detector: tests/render/modelSwap.test.ts flies level 1 on 5 armour, so the ship comes and is shot
  down, and now fails if any enemy is drawn as its extruded sprite but for the known damaged frames
  (D54); `MODEL_SWAP_REPORT=1` lists every sprite still drawn extruded (level 1: those damaged
  frames and the explosion sheet, which D35 draws as hot sprites on purpose; no shot or pickup).
- Harness: `?debug=play&armor=N` holds the bot's armour at N (`&armor=3` shows the ship from tick ~60).

**Vulcan Cannon.** Its shots are tyrian.shp#7 frame 67 (power 1-6) and 70 (power 7-11, two side by
side); the Pulse-Cannon's are 58, 59, 60, 62, 165. The atlas mapping was right (each frame cut from
its own cell, no shared or mirrored cell). The originals share one palette ramp (113-124: yellow
head, red tail), the Vulcan's slim (3 px) and twice as fast, the Pulse's 4 px blobs; Gemini painted
both as soft orange flame plumes, so the difference left was the width. The D35 halo and trail are
not the cause (the trail is longer for the faster Vulcan, which helps). Fix: `flat_art.py` can draw a
frame with a painter instead of cutting it (`PAINTED`), and 67 and 70 are `paint_tracer`: down each
column holding the sprite's brightest pixels, the colour is that column's own pixels, smoothly
interpolated, falling across the slug to its neighbours' pixels, with a white-hot core in the head
and a thin lit line; no flame texture. The alpha is the silhouette as for cut frames, and
`cut` packs them with the rest (the other frames are re-encoded from the same sources).
The other first-shop weapons (Multi-Cannon front 2 and rear 10, Protron 13, Sonic Wave 11, Heavy
Guided Bombs 29) were checked frame by frame (original | atlas): every frame they fire is in the
atlas, from its own cell, facing the right way (mirrored pairs included); no other mismatch.

**Options considered:** for the Vulcan, *re-asking Gemini* (not available here) or *the
original pixels upscaled* (stays pixel art beside painted neighbours); for the ship, *a concept
bake* (no concept image exists for it) and *flat art* (it's an enemy, and enemies are models, D15).

**Review:** `?debug=play&armor=3&freezeAt=85` (the ship), `?debug=play&front=7&power=1` and
`&power=7` against `&front=1` (Vulcan vs Pulse).

## D57 — HD terrain: painted tiles from per-tileset atlases, seam-free sampling, an Options switch

2026-11-02

**Decision:** In the remastered backgrounds (D34, the default since D48), a background tile with an
HD painting is drawn from it; every other tile draws as before. The art comes from Gemini through
`tools/terrain_hd.py` (the art pipeline's own entry); this entry is the game side and the contract.
- **Format.** `public/art/terrain/<tileset>/manifest.json` and one `<layer>.webp` per layer with art.
  `<tileset>` is the shapes file without `.dat` (`shapesz`), the layer the draw list's (0 ground, 1
  background 2: TYRIAN's clouds, 2 background 3: islands), a tile key the tile's 0-based record in
  shapes?.dat. `{ "version": 1, "scale": 8, "layers": { "<layer>": { "image", "tiles": { "<n>": { x, y,
  w, h } }, "variants"?: { "<n>": [ { "n": { left|right|up|down: tile or -1 }, x, y, w, h } ] } } } }`.
  Rects are exactly 24x28 times `scale`, at multiples of 16 texels with at least 16 texels of
  edge-extended gutter, atlases at most 4096 square (a rect may name its own `image`). Layer 0 opaque;
  1 and 2 straight-alpha RGBA, colour bled under alpha 0, cloud alpha being coverage only (the game
  applies BLEND_ALPHA). A variant is used where the level's map has all its listed neighbours.
- **Loading** (`src/render/remaster/terrainLoader.ts`, `terrainArt.ts`). `preloadLevel` requests the
  level's tileset and waits for its manifest and atlases with the models (D54); `levelModelInfo` now
  passes the level's maps as tile numbers for the variants. The harnesses, which don't preload, start
  the load at the first tile drawn. A tileset's art is used only once all its atlases have settled.
  No manifest, an unparsable one (a dev server's index.html), a failed atlas, a wrong-sized rect, or
  a rect outside its image: those tiles draw as before.
- **Drawing** (`terrainMaterial.ts`, `DrawListRenderer.drawHdTile`). After the structure-model check
  (models still win; ground tiles under `keepTiles` models are HD too), a tile with art is a flat
  ground quad (the same 24x28 quad and placement as the 4x ground, D6), one instanced draw per atlas
  and kind: ground (opaque MeshStandardMaterial, relief from the painting's brightness measured a
  quarter pixel either side, receives shadows, water's ripple mark), blend (clouds: BLEND_ALPHA x the
  art's coverage, no depth write, the sheets' render order) and cutout (layer 2 and an opaque
  background 2 without models: alpha cut at 0.5, depth written, shadows cast through a depth material
  that cuts the same way). Otherwise the 4x MMPX ground, and the original tile if that can't draw.
- **Seam-free sampling.** The shader picks the mip level from the texel footprint, at most 4, clamps
  the texel position half a texel of the coarser blended level (0.5 x 2^ceil(lod)) inside the rect and
  reads with textureLod. With 16-aligned rects no mip texel up to level 4 spans two tiles, so every
  tap of both blended levels is the cell's own tile, and adjacent cells meet on their own edge
  texels. Atlases are mipmapped (LinearMipmapLinear), unflipped, sRGB; layers 1-2 premultiplied.
- **Palette effects** by brightness, as for the flat sprite art (D42): the smoothies' hues (lava, ice,
  water with its ripple mark) and JE_filterScreen's hue and brightness. Not reachable: palette
  animation and swaps, and water_filter's exception for grey and cloud-blue indices (all of the art
  is recoloured).
- **Switch** (`src/core/terrainStyle.ts`). Options → Graphics → Terrain: Original / HD remaster (a style
  row like Music/Sound style, `optionsRows`' third list), kept in the prefs (`terrain`), and
  `?terrain=original|hd` for the page (the player's later choice replaces it). Default HD. The renderer
  listens and switches at once. "Original" is the terrain as before this entry (the 4x ground);
  `?bg=original` is still the original tiles, and HD art applies only in the remastered backgrounds.
  `?terrainart=<dir>/` loads the art from another folder under public/ (test atlases);
  `stats().hdTiles` counts HD tiles drawn.

**Options considered:**
- *Per-tileset atlas + manifest like the sprite art (chosen):* the D42 pattern the pipeline already
  knows; one request per layer; partial art falls back per tile.
- *Folding HD into the MMPX palette-index atlas (D34):* palette effects would stay exact, but a
  painting quantised to 16 shades per hue loses what it was painted for.
- *Per-context paintings for every 3x3 neighbourhood (as the MMPX slots are):* seam-free by
  construction but 1,000-2,000 paintings per level; one painting per tile, made to meet its
  neighbours, with optional variants where it can't, is a few hundred.
- *Clamp at the base level's half texel with hardware mip selection:* trilinear still reads a
  quarter-texel of the gutter at levels 1+, and anisotropic taps reach further; the shader's own lod
  with a level-scaled clamp is exact (tested on a CPU model of the sampler).
- *Extruding the HD islands like the original tiles (D8):* depth, but the painting's soft silhouette
  and the extruder's walls disagree; flat cutouts with real shadows read as painted islands, and most
  of TYRIAN's islands are models anyway.
- *A URL option only (as D42, D48):* the request was a setting; it's the first Graphics row, the
  natural home for the effects and sprite looks too.

**Review:** With TYRIAN's real atlases: `?debug=play&seed=1&skip=220&freezeAt=220` with and without
`&terrain=original` (clouds over the ground, forest and roads), `&dpr=0.3` for far mips, the islands
around `?debug=sprites&episode=1&level=9&row=140&freeze=80`, and Options → Terrain in the game.
Verified so far with a synthetic atlas whose gutters are magenta (every 7th tile left out for the
fallback): no magenta pixel at dpr 2 or 0.3, while widening the rect by 8 texels from the console
shows 1,306 — the check sees a leak when there is one. Docs: docs/terrain-pipeline.html.

## D58 — HD terrain art: Gemini paints map regions and tile contexts; edge strips are solved jointly

2026-11-02

**Decision:** The art D57 draws is made by Google Gemini from input sheets of the level's tiles and
brought back by `tools/terrain_hd.py`, the way D43 does it for sprites:
- **Inventory** (`inventory`): from the level's maps, what is drawn as a tile in the default look:
  structure-model matches are found on the whole map as `TileModelIndex` finds them (biggest pattern
  first; layer 1-2 models replace their tiles, ground models keep them). For TYRIAN (map 1-9,
  `shapesz.dat`): 66 ground tiles (4,200 cells; 29 of them under the trees, bunkers, wreck and boulders
  of D34/D47, still drawn), 15 cloud tiles on layer 1 (3,208 cells), and none on layer 2 (all 1,290
  cells are under models). Each tile gets its counts, its neighbours per side, its usual neighbours
  (also diagonally) and a representative 3x3 neighbourhood from the map, and a material group from its
  palette ramps (Tyrian's ramps are one colour each).
- **Sheets** (`sheets`), PNGs on black, padded to one of Gemini's aspect ratios (1:1, 3:4, 4:3, 9:16,
  16:9), each with its prompt in `sheets/manifest.json` (cell rects, padding, grid, which tile sits
  where). For the ground, 7x6-tile stretches of the map at 6x (1080 px square), chosen as a set cover
  so every tile is inside one away from its border: 10 sheets. For the clouds, 3x3 contexts at 4x, 7-9
  per sheet (1104 px): 2 sheets. Ground contexts by material (dirt and rock, dirt-forest edges, forest
  under trees, bunker and wreck tiles) are made too, as optional retries (9 sheets).
- **Cutter** (`cut`): each cell of an answer (any size, same aspect) is registered to the sheet's own
  picture of it by normalised cross-correlation over a rescale of +-6% and a shift, each tile then by a
  small shift; the tile is resampled at 8 texels per pixel and its colour matched to the original's
  (per-channel mean and low-frequency contrast). The best-fitting painting per tile wins (or the mean of
  the good ones). Alpha on layers 1-2 is the original silhouette upscaled with MMPX among the tile's
  usual neighbours, blurred and ramped. **Seams:** every tile side has an edge strip (its outer 4 texels,
  smoothed along the edge); all strips are solved at once, least squares over every pair of tiles the
  map puts side by side, weighted by how often, plus a pull of 0.15 towards the tile's own painting.
  The most frequent pairs (a texture next to itself, a tile and its usual neighbour) come out
  (nearly) identical; a side with many different neighbours gets the strip closest to all of them. Each tile's
  border is then moved onto its strips: the difference fades in over 40 texels, so the painting's
  detail stays, and the outer 4 texels are the strip. Atlases are packed to D57's rules.
- **Check** (`check`): contact sheets of the whole map, original beside HD, and a seam measure over
  every edge the map has. On stand-in answers (`fake`: the sheets MMPX-upscaled, rescaled +-1.5%,
  shifted up to 6 px, blurred, noised and colour-shifted), every tile registered with NCC >= 0.94, and
  the colour step between the two texels at a tile edge is 0.88x (ground) and 0.91x (clouds) the step
  between neighbouring texels inside a tile; without the seam pass it was 2.8x and 5.2x.

**Options considered:**
- *Map regions for the ground, contexts for the clouds (chosen):* in a region Gemini paints a tile's
  real neighbours in the same stroke, so most edges already continue (the pairs in a region are the
  map's own) and the strips have less to fix; every tile of the sheet is used, at 6x instead of 4x
  (a 3x3 context spends eight ninths of the sheet on neighbours that are thrown away), so 10 sheets
  cover the ground instead of 9 sheets at lower resolution. Contexts suit the clouds, whose sheets are
  mostly black around a few shapes and which are all one material.
- *Contexts for everything:* the uniform grids Gemini kept well for sprites (D43), but each centre
  tile is painted on its own, so its edges agree with its neighbours' only as far as the seam pass
  forces them. Kept as optional retries.
- *Seams by blending each tile's border to a smooth upscale of its own pixels among its usual
  neighbours:* exact for usual pairs only; on TYRIAN's clouds, where tile 53 has several different
  neighbours on every side, steps of ~20 levels were left at edges like 53 over 63 (inside a tile
  ~2).
- *Variants (D57) for each neighbour combination:* exact, but 824 ground and 629 cloud combinations;
  the jointly solved strips get the measured edges below the inside steps with none. Variants stay
  available for a pair that still shows.
- *Averaging the alpha strips too:* where one tile's edge is empty and its neighbour's isn't, it drew a
  faint line of cloud; alpha stays the silhouette.

**Review:** Send the primary sheets to Gemini one at a time (`sheets/manifest.json` lists them with
their prompts; the ground regions first, then the clouds), save each answer as
`<work>/results/<sheet name>.png|jpg`, then `python tools/terrain_hd.py --work <work> cut` and
`check`, and look at `check/*.jpg` and `cut-report.json` (an NCC under ~0.5 means the cell moved or was
repainted: retry it, or send the optional context sheet for that tile). The atlases in
`public/art/terrain/shapesz/` are committed with the real answers (with a CREDITS.md row, D41); the
sheets and answers stay out of git (D3). Known limits: palette cycling and swaps don't reach the
painting (D57); where only some tiles have art, an HD tile next to a 4x one has an ordinary seam; at
4x and 6x per pixel Gemini's ~1024 px answers are upsampled to 8x, so detail is at most what fits.
To extend to another level: `--level <ep-file>` for `inventory`, `sheets`, `cut` and `check` (the
tileset comes from the level; a tileset shared by several levels should be inventoried for all of
them before its atlas is cut, which the tool does not do yet).

## D59 — TYRIAN's HD terrain from the real Gemini answers; the cutter prefers painted, coherent tiles

2026-11-02

**Decision:** `public/art/terrain/shapesz/` (0.webp 1888x1936 RGB, 1.webp 1056x736 RGBA, manifest.json;
600 KB) is cut by `tools/terrain_hd.py cut` from the 21 Gemini answers (2048 px, 2400x1792 for the
4:3 sheet; every cell registered at scale 1.00). It covers every tile the inventory lists: all 66
ground tiles and all 15 cloud tiles of map 1-9 (layer 2 needs none, D58). None is excluded. On the real
answers the D58 cutter's choice ("the best-fitting painting wins") picked the wrong ones, so the
choice now weighs, per candidate:
- **Pixel blocks** (`blockiness`): the colour steps between texels averaged by phase in the 8-texel
  period of an original pixel, strongest phase over the mean. A painting is 1.0-1.5; region-l0-02's
  answer, which copied the 6x6 blocks, is 3.3-3.7 and fit the original best (NCC 0.99), so it won 8
  tiles. Above 2.0 it costs 0.15 per unit.
- **Made-up marks** (`novel_detail`): the 99.8th percentile of the painting's local high-pass energy
  minus the original's. A twig Gemini drew in one copy of the light dirt (tile 46, 150 cells) showed
  as a grid of marks across the map. It costs 0.03 per unit above the tile's median candidate + 1
  (relative, since a canopy has more detail than dirt).
- **Region over context** (+0.06): a tile painted in a map region shares its neighbours' texture; the
  context sheets painted the dirt around mounds as smooth sand, which showed as tile-shaped patches next
  to region-painted dirt. Contexts still win where regions are poor (16 of 66 ground tiles).
- **Shading follows the original** (`match_lowfreq`, 16 texels): the painting's blur at 16 texels is
  swapped for the original's (among the tile's usual neighbours), so a darker corner Gemini painted
  doesn't become a grid when the tile repeats, and cloud rim tiles match the inside ones in brightness.
`cut` gained `--exclude 0:332,...` (leave tiles out; they fall back), `--pick 0:68=region-l0-03#0`
(hand pick), `--cache FILE` (keeps the registered candidates; registration takes ~3.5 min) and knobs
for the above; `cut-report.json` lists each tile's source, NCC, colour error, blockiness and novel detail.

**Result** (`check`, every edge the map has): ground, colour step across tile edges 1.85 vs 3.08
between texels inside tiles (0.60), 8-texel bands 3.99 vs 7.84 (0.51); clouds 2.15 vs 2.62 (0.82),
bands 7.54 vs 14.74 (0.51). The contact sheets show no seam along the map's own pairs, no labels,
text or cell bleed; on the ground the painting's mean colour error per original pixel is 0.8-3.7%
(median 1.4%; `cut-report.json`). Weak spots, kept since
the fallback would be worse: tiles 37, 39, 110, 224, 332, 333, 350 still have some pixel blocks
(1.9-2.8; 224 is under trees, 332/333 under a bunker); the forest canopy (region-l0-03, 210-233) keeps
some checker but sits under the tree models; the cloud rims (ctx-l1-blue-1: 40-44, 50-52) are painted
as puffier clouds with a little sparkle, colour error up to 0.135, and a few rare vertical pairs
(42 over 61 and 44 over 53 once each, 42 over 52 16 times) keep a visible step (ratio 2.9-10).

**Options considered:**
- *Keep the best fit (D58):* chose blocky copies and the twig; rejected after the contact sheets.
- *Exclude the blocky tiles:* they'd draw as the 4x MMPX ground beside HD neighbours, a seam of
  style at every edge; region-01/08/09 painted the same tiles acceptably.
- *Another Gemini round for region-l0-02:* the operator stopped at Gemini's usage warning; the other
  regions and contexts already cover its tiles. A softened sheet (D58 docs) is the retry if wanted.

**Review:** in game, `?debug=play&seed=1&skip=220&freezeAt=220` against `&terrain=original` was not
looked at in this step; the contact sheets and the seam metric were. To redo a tile: retry its sheet,
delete the cache, `cut` again, and look at `check/l*-rows*.jpg`.

## D60 — HD terrain checked in game: atlases uploaded during the preload, leftover pixel blocks softened

2026-11-02

**Decision:** TYRIAN's HD terrain (D57-D59) was played through in the browser and two things were fixed:
- **Atlas upload in the preload.** `DrawListRenderer.uploadTerrain(renderer)`, called by
  `preloadLevelModels` after `preloadLevel`, hands the level's HD atlases to `renderer.initTexture` when
  the look is HD. Before, the level's first frame decoded and uploaded them with their mipmaps: ~85 ms
  (first frame 270 ms against 180 ms for the original look, the same three runs each), which in
  `?debug=play&skip=2000` was enough to run past D54's 250 ms hold, so the worm and its grabbers came
  out as extruded sprites in HD and as models in Original. Now the first frame is ~180 ms in both. A switch
  to HD in Options still uploads on its next frame (~110 ms once, in a menu).
- **Deblocking** (`tools/terrain_hd.py`, `deblock`). A chosen painting whose blockiness (D59) is above 1.6
  has its block edges softened, fully from 2.4: a 2.5-texel blur mixed in within 3 texels of the columns
  and rows where the 8-texel period's steps are strongest; the blocks' insides keep their detail. 23 of
  the 66 ground tiles are touched: 333 2.81 -> 1.57, 39 2.37 -> 1.58, 332 2.19 -> 1.55, 110 2.09 -> 1.63,
  37 2.03 -> 1.67, 350 2.03 -> 1.64, 224 2.05 -> 1.65; the rest were 1.6-2.0 and end at 1.6-1.7
  (`cut-report.json`: `deblocked`). It showed in game as a rectangle of pixels around the bunker (330-333
  under it) and along the dark rock at tick 1000. `--deblock-from 0` turns it off. Seam measure (D58):
  ground 0.573 (was 0.601), bands 0.50; clouds unchanged (no cloud tile is over 1.6). The atlas is re-cut
  from the same cache (`0.webp` 512 KB); without deblocking the cut still reproduces D59's byte for byte.

**Checked** (`?debug=play&seed=1&skip=T&freezeAt=T`, T = 1, 8, 30, 300, 1000, 2000, 3000, 4200, 5500,
HD and `&terrain=original`, plus `&dpr=0.3`): no seams, gaps or misplaced tiles on the ground or the
clouds at any of them; the clouds translucent over the ground in both looks and seamless; layer 2 is all
models on TYRIAN, so there are no HD island edges to check; colours match the original's (the grass,
dirt, ridges and pools). Options → Graphics → Terrain switches at once and is kept in the settings;
`?terrain=` and a live `setTerrainStyle` switch too. Fallback: a copy of the atlas with tiles 46 (ground)
and 53 (cloud) deleted from its manifest, through `&terrainart=`, draws those 13 cells at tick 300 as the
4x ground (`hdTiles` 130 -> 117), nothing missing. Performance: 120 fps and ~2 ms cpu in the overlay in
both looks. Tests and the typecheck pass.

**Not fixed** (docs/terrain-pipeline.html, "Known limits"): during the level-start fade (levelBrightness
-14 to 0, ~14 ticks) the art's brightness recolouring (D42's) goes darker than the original, whose
darkest ramp entries keep some colour (the cloud blue's index 0 is still (9,21,27)), so for half a second
the HD clouds look grey and the ground black. Doing it right needs each texel's palette hue, which the
painting doesn't carry; a per-layer floor colour was considered and left out as a guess. The weak tiles
D59 lists stay weak, though softer.

**Options considered:**
- *Compile the HD materials in the preload as well:* the upload was 85 of the ~90 ms; after it the
  difference was within run-to-run noise.
- *Exclude the blocky tiles:* the 4x ground beside painted neighbours, a seam of style at every edge (D59).
- *Blur the whole tile:* removes the blocks, and the painting's detail with them; a blur only at the grid
  lines keeps the rest.
- *Another Gemini round for those tiles:* Gemini's usage warning had already come up (D59); the deblock
  needs no new answers.

## D61 — The in-game HUD as the original's bronze frame, the 3D view fitted into its opening

2026-11-02

**Decision:** The one-player HUD draws the approved design "A — Faithful bronze": the original's
sidebar and message bar (JE_loadPic 3, `public/art/hud.webp`) redrawn in SVG on the 320x200 grid, with
the 3D view fitted into the frame's opening, and a gentler default camera. Options → Graphics →
**Interface** (Remastered frame, the default / Minimal, the HUD before this) and **Camera** (Overhead 0° /
Tilted 15°, the default / Steep 32°, the look before this), kept in the prefs;
`?interface=frame|minimal` and `?camera=overhead|tilted|steep` override them for the page
(`src/core/displayStyle.ts`, the same pattern as D57's terrain).
- **Wiring** (`src/app/hud.ts`, `hudFrame.ts`): real values throughout. The generator column is
  `g.power / 10` rows of 90 (tyrian2.c's power bar); shield and armor are one row per point on an
  absolute 30-row scale like JE_dBar3 (armor caps at 28), with the max-shield marker drawn only below
  full as JE_drawShield does; pips are the port's power, 11 at most; the mode lamps follow
  `weapon_mode` (JE_drawPortConfigButtons; both dark without a rear weapon, as the design shows); the
  sidekick boxes show the C's own HUD icon (OPTION_SHAPES `iconGr - 1` in the in-level palette 5,
  pixel-sharp) and draw_segmented_gauge's ammo tenths for sidekicks that run out; the score is
  `p.cash`; the bar shows the message (JE_drawTextWindow) and the level's name at its right. The
  approved tweaks: weapon names under FRONT GUN and REAR GUN (squeezed to fit when long); read-outs at
  the top of the power (percent), shield and armor gauges; the score in the sidebar's wide box —
  **a departure**: JE_inGameDisplays prints it on the playfield at (30, 175); the phone layout as a
  console under the playfield. Boss bars, WARNING, arcade lives and the cheating line stay HTML, over
  the opening. The DOM changes only when a value does.
- **Fitting the view** (`View.setViewport`, `fitCamera`, `playfieldScreenAspect` in
  `src/render/view.ts`): the canvas still covers the window (the menus' backdrop draws with the same
  renderer); the camera is fitted to the playfield rectangle's aspect and shifted off-axis
  (`setViewOffset`) onto it, so all four corners stay on screen and nothing is zoomed. The mask, the
  steering scale and the screen filters work as before, since they read the camera's matrices.
- **The gentle tilt** (user's decision on the PR): at the old 32° the playfield on screen is ~2.2:1 (the
  near edge's width over the foreshortened height), so in the frame's 264x184 opening it left 63 units
  of the 184 empty above it, 47% of the opening with the wedges. Computed for the 16:10 opening
  (`playfieldScreenAspect`), and compared on screen (`?debug=play&freezeAt=900&seed=3`):
  12° 1.59:1, 18-unit band, 16% empty, far edge 86% of the near; 15° 1.65:1, 24 units, 21%, 82%;
  18° 1.71:1, 30 units, 25%, 79%. The side depth the models show goes with sin(tilt): 0.21, 0.26,
  0.31 (32°: 0.53). At 12° the sidekick pods and the walker read as top views; at 18° their fronts
  show clearly, but the band grows by a quarter again. **15°** is the middle of both: half the old
  side depth, under half the old empty area. A stored or URL `tilted` (which meant 32°) now gets 15°;
  `steep` is the old look. The View still starts at 32° (`CAMERA_TILT`), so the item screen's weapon
  preview, whose window size is tuned to it, keeps its look; the game view is set from the choice in
  main.ts. The menus' backdrop has its own camera and the model viewer's "game" angle is its own
  approximation; neither reads the tilt and both are unchanged.
- **Layout** (`src/app/hudLayout.ts`): tilted, the playfield is wider than the original's 264x184 on
  screen. So on 16:10 the frame
  keeps the original's grid (a 264-unit opening, 61-unit sidebar, 16-unit bar), the playfield sits on
  the message bar like the original's, and the opening's rest — the band above it and the wedges by the
  narrower far edge — is a dark recessed bezel with faint ribs and a lit bronze lip along the
  playfield's edges. A wider window widens the opening, up to the playfield's own width (21:9 is filled
  edge to edge); what's left after that is bronze wing plate (the sides on ultrawide, above and below on
  4:3). Overhead, the playfield is 264:184 and fills the 264-unit opening exactly. Portrait (narrower
  than square): the playfield across the width, the console under it, the block centred with plate
  above and below; the safe-area insets are respected.
- **Two-player** games keep the minimal HUD beside twoPlayerHud.ts (the C's two-player sidebar is a
  different picture, JE_loadPic 6) and the full-window view.
- **Fonts:** Gill Sans where the system has it (the original frame's lettering), else the interface's
  Exo 2, already loaded; nothing new is fetched. SVG keeps it crisp at any DPR.
- **Performance:** two full-window SVG layers, each `will-change: transform`: the frame with the
  brushed-metal and shadow filters, built once per layout, and the live layer, whose changed elements
  only repaint it. `?debug=play` at 1920x1080 DPR 2, unfrozen, at 32°, 8 one-second samples each: frame
  60 fps / 1.8-2.3 ms cpu, minimal 60 fps / 1.75-2.3 ms (headless Chrome, which caps at 60).

**Checked** in headless Chrome (`?debug=play&freezeAt=900&seed=3&left=1&right=5&rear=15`, which now
shows the HUD): 16:10, 16:9, 21:9, 4:3 and a 390x844 phone at DPR 3, at 15° and at 32° (16:10 and the
phone also overhead; 16:10 also at 12° and 18°): all four playfield corners visible each time; `&armor=3` for the WARNING; `&interface=minimal` unchanged
from before. The real game from the title: no frame on the title, item screen or options; the frame in
the level; the pause screen's scrim over it; gone again on the level-complete screen and after.
Tests: `tests/app/hudLayout.test.ts` (gauge maps, pips, ammo, the camera fit, the layout at each window
shape, the settings and prefs). Not checked: phone landscape in a browser (only in the layout tests), a real phone's notch and touch steering on one, Safari and
Firefox, the attract demo with the frame, two-player in the browser.

**Options considered:**
- *The design's fixed 259x184 opening:* tilted, the playfield fits it 259 wide and ~118 tall, a third
  of the opening empty, and the design's picture filled it only by cropping the near corners.
- *An opening shaped to the tilted playfield at every size:* a 405x184 opening puts bronze bands over
  a third of a 16:10 screen and loses the original's proportions; it's what a 21:9 window gets.
- *Keeping 32° as the default:* nearly half the opening empty on 16:10; it stays as Steep.
- *Narrowing the field of view instead of the tilt:* flattens the perspective of every model too, and
  the far edge stays as narrow relative to the depth shown.
- *Canvas sized to the opening (`fitContainer`):* the menus' backdrop shares the renderer and
  wants the whole window; the off-axis projection gives the same picture without moving the canvas.
- *Rasterising the frame to an image:* the SVG on its own layer already costs nothing per frame.

**Review:** Is 15° enough depth in motion (the stills were judged frozen)? Play a level in each Camera and Interface on a 16:10 and a 21:9 screen and on a phone:
does the recessed band above the tilted playfield read as part of the frame, or should the playfield
be centred in the opening instead of sitting on the bar? Are the gauge read-outs and weapon names
readable at 1366x768?

## D62 — Player ship models follow the banking frames' sideways shift; the x limits stay the C's

2026-11-02

**Decision:** Reported: "the player can't travel fully left and right; the original could." It
couldn't either, and our limits were already the C's: `JE_playerMovement` clamps x to 40..256 and y
to 10..160 (mainint.c L3857-3880; `src/sim/mainint.ts` L696-712, `PLAYER_MIN_X`/`PLAYER_MAX_X` in
`src/game/playfield.ts`), keys, digital joystick, analog stick and mouse alike (the mouse is relative,
mouseGetRelativePosition, clamped to +-30 a tick, L3538-3554; nothing clamps earlier, and
`src/app/controls.ts` doesn't either, for mouse or touch). The ship's 24-pixel cell is drawn at
x - 5 into game_screen and showNormal shows game_screen from x 24 (backgrnd.c L1018-1040), so at the
limits the cell starts 11 pixels into the 264-pixel window and ends 13 short of its right edge.
Holding a direction banks the ship fully (ship_banking -2/+2, L3883-3884), and the USP Talon's
hard-bank frames are off-centre in that cell: opaque columns 2-15 banked left and 8-21 banked right,
against 3-20 level. So the original's ship stops **13 pixels** from the left edge and **15** from the
right. Ours stopped about 3.5 pixels further in on each side (16.6 / 18.6 overhead, measured from the
model's projected vertices), because the models are rolled about the cell's centre and so lose the
frames' three-pixel lean. Now `src/render/bankShift.ts` measures how far each banking frame's opaque
columns are centred from the level frame's (Talon: -3, -1, 0, +1, +3 pixels) and the renderer moves the
player ship's model that far sideways, eased with the roll, along the camera ray (D6). At the limits
the model now covers 13.6-26.9 / 235.0-248.4 overhead, 12.9-26.1 / 235.8-249.1 at 15° and
11.7-25.9 / 236.2-250.3 at 32°, against the sprite's 13-27 / 235-249 (the rolled model is a little
narrower than the frame; tilted, its height spreads it a little outward). The playfield fit, the mask
and the HUD opening are unchanged (D61's four corners stay visible).

Applies to every banked player ship (Override route) from its own sprites: the Gencore Phoenix and
U-Ship lean like the Talon, the SuperCarrot doesn't, and the Silver Ship's frames lean the other way,
so its model does too. The two-player dragonwing (Group route) is not shifted.

**Options considered:**
- *Widen the x limits:* not the C; changes where shots start and what can hit the ship.
- *Draw the ship's model wider or nearer the edges by moving the camera fit:* breaks D6's "draws land
  on their original screen positions" and D61's corners.
- *Leave it:* the 3.5 pixels are 14 CSS pixels on a 1280-wide window, enough to notice next to the
  original.

**Review:** Hold left and right in a level at each Camera: does the ship's slide toward the bank read
as natural, or does it look like the ship drifting off its guns' line? Fallback: drop the shift
(`bankShift` returning 0) and accept the 3.5-pixel gap.

## D63 — TYRIAN's island rock is the tiles' own pixels as a relief, the same on every tile and structure

2026-11-02

**Decision:** The floating islands of background 3 (shapesz.dat rock tiles 120-124, 130-134,
140-142, 150-152: TYRIAN and eight other levels) are no longer a dark slab with a fitted boulder
per stone. Each rock tile model is the tile's own 2x pixels as a smooth relief
(`lib_tiles.rock_tile`): every pixel in the nearest of one shared set of palette colours
(`ROCK_COLOURS`: the grey ramp, the tan and brass stones), raised by its smoothed brightness through
a fixed range (`ROCK_LUM`, not normalised per tile) up to 0.12, the underside tiles' face hanging
toward the camera as before. TYRIAN's structures that stand on the islands (crater, lava pit,
purple blocks, cross and orb, drums, gates, the fortress's machine) build their rock the same way,
cell by cell (`Structure.rock`), in materials marked `tyrian_plain` that `texture_bake.py` leaves
untextured, so a structure's rock is exactly what the per-tile model of that tile would draw. They
were rebuilt and rebaked; the bridge (its own rim boulders) is unchanged.

Before, an island read as a grid of tiles: each tile fitted its boulders between its *most common*
neighbours, so stones broke at most seams; each picked its own boulder colours (grey or tan per
stone, from a per-tile quantile), so a stone changed colour across a seam; the brass highlights of
the rim tiles came out as flat raised pixel blocks; and the structures' rock was darkened by their
concept bake, so every crater, lava pit and purple block sat in a dark square. The art itself is
painted to tile seamlessly, so drawing its pixels keeps it seamless.

`?debug=play&skip=N` now waits for all the level's models before fast-forwarding (it waited only for
the first ~1000 locs' worth, D54), so a capture part-way in shows what a real run shows instead of the
original tiles locked in for every structure first seen before its model loaded.

**Options considered:**
- *The tiles' pixels as a relief in shared colours, structures' rock the same and unbaked (chosen):*
  seamless by construction, follows the level's palette (palette materials), one kit for both.
- *Fix the boulders (stones from the real neighbours, shared colours):* a per-tile model can't know
  its neighbours, so stones crossing seams still break against all but the usual one.
- *Whole-island models from TYRIAN's map (biggest pattern wins, D47):* exact joins, but some 35
  models for one level, pops from per-tile to island at the screen's top edge (minRows), and every
  other level keeps the broken per-tile look.
- *A baked colour texture per tile instead of per-pixel materials:* fewer draws, but the colours
  would stop following the level's palette (the tiles are in nine levels).

**Review:** Play TYRIAN to the islands (`?debug=play&seed=1&skip=2700&freezeAt=2702`, also 3300,
4300, 4850). Costs: the rock tiles have 1.7-3.9k triangles and 95-205 KB each (nearly flat faces of
one colour merged, `ROCK_MERGE_DEG`; they were 30-135 KB), about +1.4 MB for the 16, and the
rebuilt structures +3.4 MB (their rock is finer and carries bake UVs): +4.8 MB on the level's ~32
MB. They have 10-15 palette materials each, so a screen of islands takes more draws. If loading or
draws matter, coarsen the relief (1x instead of 2x pixels) or trim `ROCK_COLOURS`. The heights still step a little at seams against an unusual neighbour (the slab's
walls close it). Left as found: some of TYRIAN's enemies that sit on the purple blocks and machines
(newsh2 models) carry the old boulders and a dark outline round their base, which now stand out
against the rock; that's in their models. Fallback: revert this commit's scripts and models.

## D64 — The title as the original's: the traced logo and a copper two-step menu over a painted planet at sunrise

2026-11-03

**Decision:** The title screen follows the original's layout: the huge maroon planet arcs from the
top left down the right, the logo sits at the top, and a centred copper menu sits below it with no
panel. The user chose the look from four mockups: the "Painted motion" planet with the "Cinematic
dawn" sunrise and Talons laid over it.

- **Logo:** only the original. `public/art/title/tyrian-logo.svg` is the title sprite
  (tyrian.shp PLANET_SHAPES #146, palette 8) traced to one vector outline (IoU 0.97 against the
  sprite at 1x) with a brushed copper fill, bevel and shadow as SVG filters.
  `tyrian-logo-mask.svg` is the same outline as a silhouette. `logo()` (src/ui/components.ts) shows
  it as an image, crisp at any size, and sweeps a copper glint across it every 9 s with a CSS mask of
  the silhouette, so the shapes never change. The traced file's own SMIL sweep was taken out of our
  copy so the glint follows reduced motion. A test keeps the two files' paths identical. The data
  picker uses the same logo. The Orbitron "TYRIAN" wordmark is gone.
- **Backdrop** (`src/ui/titlePlanet.ts`, the "title" mood of `src/ui/backdrop.ts`; hangar and space
  are unchanged):
  - **The paint:** one full-screen shader. Its brush strokes flow along a flow map and curl field,
    with dry-brush bristles, impasto relief, a painted terminator with a copper band, faint
    night-side lights and a slow breathing light. It renders into a target of at most 0.9 MP (never
    above CSS pixels) about 30 times a second.
  - **The dawn, in the same brushwork:** the amber sun climbs past the limb over the first ~30 s, its
    scatter laid in strokes along the rim. The halo has brushed rays, plus a short anamorphic streak
    and two faint ghosts. The camera pushes in slowly toward the sunrise and settles, with a drift
    and a slight roll.
  - **The composite:** the paint upscaled with a static canvas grain and vignette, plus two flights
    on a 34 s cycle. The real Talon (`usp_talon.glb`) passes alone, banking away toward the sun, with
    its own engine glows (`tyrian_engines`). Then a squadron of four crosses the night side. The
    canvas redraws only when the paint changes or a ship is flying.
  - **Fallbacks:** reduced motion gets one still at t = 26 s (sun up, no ships). Slow frames (over
    50 ms on average) or `?titlefx=half` switch to a half-resolution paint, with the ships kept to
    its pace. Without WebGL, or when the shader fails to compile, a CSS planet stands in
    (`.ui-backdrop-fallback[data-mood="title"]`).
- **Menu** (`src/app/titleMenu.ts`, pure, tested):
  - **Two steps:** Start New Game, Load Game, High Scores, Options, Music: ‹style› (only with music
    styles). Start New Game opens the second step: the episodes (a numeral and the data's title),
    a difficulty row with diamond pips, and Back. Choosing an episode starts it.
  - **The look:** copper type, a brush smear behind the chosen line, copper diamond ticks and a glint.
  - **Kept behaviour:** the keys L, H, O and M, the pad's LB, Y, Back, X and Start, mouse and touch,
    the codes and hidden difficulties, the idle demo and arcade starts. Left and right always pick
    the difficulty on the episodes step, as the old row did; Escape goes back a step. A code that
    completes puts the step and focus back.
  - **Order:** the entries follow the original's (Load Game before High Scores); Options comes last.
- **Colours:** copper, maroon, umber and bone tokens in `tokens.css` (`--ui-copper*`, `--ui-bone`,
  `--ui-umber-ink`...). There is no blue on the title. The other screens keep their look over the
  painted planet (Options, Load Game, High Scores, the Players screen). No new fonts or CDNs: the
  menu is Exo 2 at 700, as already loaded.

**Options considered:**
- *Painted planet plus the dawn layer and real Talons (chosen):* the user's pick; the painted look
  carries the original's streaky planet, and the sunrise and ships give it life without a busy 3D
  scene.
- *A full 3D ray-traced planet (the "Cinematic dawn" mockup alone):* a photographic look, heavier
  (simplex fBm per pixel), and less like the original's painting.
- *Keep the 3D backdrop's blue planet and ship behind a restyled panel:* not the original's layout or
  palette.
- *A hand-drawn or reinterpreted script logo:* ruled out by the user. Only the traced original is
  shown.

**Review:** `npm run dev`. The captures (headless Chrome, `?titlet=24` starts the shot at the
squadron) show 16:10, 21:9, phone portrait and landscape, the episode step, the reduced-motion
still, half resolution and the CSS fallback. Cost on an Apple M5 Pro (ANGLE Metal): 0.37 ms a paint
at 1200 x 750, rAF steady at 60 fps, 30 paints a second. On SwiftShader (software GL, a weak-GPU
proxy) it switched itself to half resolution (600 x 375): 12.5 ms a paint, about 28 fps overall.
Not checked: Safari (the SVG filters and the CSS mask), real phones, real low-end GPUs.

## D65 — Level 1's enemies and boss rebuilt hard-surface, the way the player ships were

2026-11-03

**Decision:** The 28 models that stand in for level 1's (TYRIAN) enemies and boss are rebuilt in the
player ships' style (D50–D53): hard-surface lofts with chamfers, modelled panel lines and machined
detail, an AO/roughness bake only (`"bake": "model"` in each `maps.json`, no concept projection, so
no "crinkled foil"), and the outline shell. The original sprite stays authoritative for the top-down
silhouette (IoU ≥ 0.95 at sprite resolution on every frame), the position of canopies, eyes and
lights, and the major colours (the sprite's palette indices per region). Undersides are only a
plausible closed shape (user's instruction), since the game camera never sees them.

- **Which models:** found from the game's own data (the level's preload list plus a bot playthrough):
  the boss (assembly-newsh4-124), 14 multi-piece assemblies (the horned flyby craft, both boss-style
  arms, both long pipes, the dome works, the carapace bunker, the pylon, the gun walker, the red
  machinery, the eye fortress, both octagon walls, the rock outcrop) and 13 single-sprite flyers and
  ground enemies. Player ships, sidekicks, shots, pickups, the armour supply ship and terrain
  structures are not part of this.
- **Process:** a multi-view HTML/JS blueprint per model; two competing Blender designs and a judge
  for the boss and the assemblies, one design for the small ones; a finisher; then a strict review
  against the sprite with up to three fix rounds (plus one extra round for the four that still
  failed).
- **The game contract is unchanged:** palette materials (`pal_<index>`), the same model paths and
  `spriteModels` entries, every animation frame, and assembly pieces, regions and pivots.

**Options considered:** keep the concept-projected textures from D44 (rejected: the user preferred
how the player ships turned out, and projected concepts look like foil); rebuild only the boss
(rejected: the user asked for all of level 1's enemies); two designs for every model (rejected to save
usage: the 24x28 flyers gain little from it).

**Review:** Final strict-review scores were 7–8 out of 10 for 27 models. The rock outcrop
(assembly-newshe-39) reached only 6.5: from the game camera it matches the sprite (IoU 0.985), but
from the side its slabs still look too boxy, so it is the first one to revisit. Its damaged frames
(newshe 7–49) still swap to sprites (KNOWN_DAMAGE_SWAPS), as before. Check a playthrough of
level 1 for pops, pivots and turret aim. Fallback: revert a single model's script and `.glb` to main.

## D66 — The island rock round level 1's machines is island rock: no slab, no boulders, no outline

2026-11-03

**Decision:** Five of TYRIAN's enemies that sit on the floating islands fill their whole sprite: the
machine, and round it island rock painted to blend with the tiles beneath. Their models now build
that rock as the islands do (D63) instead of as a slab with boulders inside the outline:

- **Which models:** found from the game's draw list over the whole level (the bot's run, the
  router's model for every grouped draw) and the sprites' pixels: the top enemies (drawn at 2.5 over
  the islands at 2.1) whose sprites are opaque to the rectangle's edge with rock round the machine.
  The purple octagon walls `assembly-newsh2-279` (pieces 279/281/283, ticks 2500-5300) and
  `assembly-newsh2-273` (273/275/277), the eye fortress `assembly-newsh2-245` (245/169/207), the red
  machinery `assembly-newsh2-53` (15/17/53/55) and the star core panel `newsh2-153`.
- **The cause:** each model built the sprite's rock as part of the machine: a rock bed slab filling
  the rectangle (279, 273, 53; 153's deck plate with a skirt), cleaved or rounded boulders on it, and
  the outline shell (`common.outline_shell`, D51) made from all of it, so the ink outline ran round
  the sprite's rectangle. Against the D63 islands the boulders were the old look, and the slab's
  edge with its outline read as a dark box.
- **The fix:** `lib_tiles.sprite_rock` builds the rock from the sprite's own pixels the way
  `rock_tile` does: MMPX 2x (a copy of tools/terrain_hd.py's, which needs PIL), rock-ramp pixels
  snapped to `ROCK_COLOURS`, heights from `ROCK_LUM`, flat shaded, the per-tile models' finish,
  plain materials (not baked). Where the machine stands (its footprint, ray cast from above) the
  rock is level and dark under it; any other paint keeps its own index (53's blue stone). It is a
  separate object per piece (origin at the piece's centre, heights from the whole assembly so the
  pieces meet), outside the outline shell, marked `tyrian_ground`: the renderer gives it no shadow
  (`castsShadow`, modelPrep.ts), which would lay a dark band along two of its edges on the island
  0.4 below. The slabs, boulders, sand blobs, 53's dark deck and 153's plate and corner blocks are
  gone; every machine part, palette material, frame, piece and pivot is as it was. The bakes keep
  the rock as an occluder, so the machines' feet still darken on it.

**Options considered:**
- *The sprite's rock as island relief at the enemy's height, no outline, no shadow (chosen):* the
  enemy is placed on the camera ray through its screen point (D6), so the rock lands on screen
  exactly where the sprite draws it and the island goes on under the machine.
- *Leave the rock out and let the island tiles beneath show:* the sprite's own stones (the beige ones
  round the caps) would be lost, and what the map has under each enemy was not checked.
- *Keep the boulders, only drop the slab's outline:* the boulders still don't match the islands.
- *Lower the rock to the islands' height:* it would cut into the island's own relief and flicker.

**Review:** `?debug=play&seed=1&skip=N&freezeAt=N` at 3300 (purple walls), 4300 and 3800 (star core),
4600 (eye fortress over both walls), 4850 (red machinery). Costs: the 14 GLBs are 4.2 MB, 0.27 MB
smaller than before. Left as found: the star core keeps the outline down its sides, where the sprite
paints straight, symmetric metal beams to the rectangle's edge (machine, not rock); a small step can
show where an enemy's rock meets an unusual neighbour (as D63's tiles), and the middle wall piece
(275) has its seams computed between its first neighbours in the row. The ground enemies with full
sprites (`assembly-newsh2-115`, `-119`, the rock outcrop `assembly-newshe-39`) stand on level 1's dirt,
not island rock, and are unchanged.
Fallback: revert the five scripts and their GLBs; `castsShadow` is harmless without the flag.

## D74 — A model's top-view edge goes to the inner edge of the sprite's ink border; the game's ink stands in for it

2026-11-03

**Decision:** Models are matched to the sprite **without its ink border**. The border is the ink
pixels of the sprite's boundary ring (luma < 26: palette 1, 2 and each ramp's darkest steps, 16, 32,
48, 64, 80, 112, ...; 4-adjacent to transparency or the picture's edge). The model's top view covers
the rest (the inner mask), and the game's ink outline (`OUTLINE`, unchanged) draws where the border
was. Where the sprite draws colour to its edge, the edge stays where it is. A part only one colour
pixel wide inside its ink, or drawn in ink alone, keeps at least half its sprite width (each side
in by at most a quarter of it); its border pixels count neither way. The hard rule becomes: rule
IoU ≥ 0.95 on the sprite's grid on every frame, from `tools/sprite_mask.py <name> --measure top.png`
(`iou_rule_grid`). The rule for agents: docs/agents/OUTLINE-BORDER.md. No shipped model is rebuilt
here.

- **The border, surveyed** (each model's main frame, assemblies whole): level 1's 28 models: 18 have
  a closed border (≥ 85% of the ring ink), 2 partial, 4 none, 4 opaque to the rectangle (island
  machines, rock). All 8 player ships closed. All episodes' 993 enemy sprites (822 not opaque to the
  rectangle): 28% closed, 42% 50-85% ink, 22% 20-50%, 9% under 20%; the gaps are coloured pixels
  (lit rims, glows), not a shadow side: every side is ink about equally often (65-68%). One pixel
  thick: in bordered sprites the next layer in is 6-35% ink (median per group), 26 of 228 closed enemy
  sprites have a 2 px border. Most common ink: palette 1 (12, 12, 12), then 2, 112, 32, 64, 16, 48.
- **The experiment.** The current models of the Talon, newsh2-89, newsh2-191 (thin arcs), newsh2-267
  (thin legs), the boss assembly-newsh4-124 and the eye fortress assembly-newsh2-245 (no border, the
  control) were drawn still in the game's renderer (`?debug=models`, frame-HUD viewport at
  1920x1080, 5.4 screen px per sprite px) and compared with the sprite at the same place and scale.
  Then copies pulled in to the inner edge (a plan warp, scratch only) were drawn the same way.
  The ink is 3-4 screen px, 0.55-0.75 sprite px.

  | Overhead (15° camera) | silhouette IoU with the sprite, current → inner | edge offset per side, sprite px |
  |---|---|---|
  | USP Talon | 0.818 → 0.929 (0.800 → 0.933) | +0.68 → -0.08 (+0.70 → -0.05) |
  | newsh2-89 | 0.851 → 0.913 (0.795 → 0.846) | +0.97 → +0.30 (+1.19 → +0.54) |
  | newsh2-191 | 0.689 → 0.816 (0.641 → 0.797) | +0.69 → +0.19 (+0.72 → +0.25) |
  | newsh2-267 | 0.737 → 0.743 (0.668 → 0.679) | +0.74 → +0.15 (+0.83 → +0.27) |
  | assembly-newsh4-124 | 0.809 → 0.838 (0.762 → 0.780) | +1.37 → +0.78 (+2.17 → +1.56) |
  | assembly-newsh2-245 (control) | 0.946 (0.928) | +0.21 (+0.31) |

  Every model matched to the outer edge read fatter than its sprite (the Talon 22% more area);
  at the inner edge the size matches within a third of a pixel and the thin parts still read.
  (267's IoU stays low because its legs don't follow the sprite's, whatever the edge.)
- **Tool:** `tools/sprite_mask.py` finds the border and writes the outer, inner and free masks, a
  per-sprite survey line, PNG masks to trace, and `--measure` for a top-view render. Standard library
  only (Blender's Python and the system's); `tests/tools/spriteMask.test.ts`.

**Options considered:**
- *Inner edge, the game's ink for the border (chosen):* the silhouette with the ink lands on the
  sprite's; the sprite's dark ring and the model's ink outline are the same thing.
- *Outer edge, ink thinned or dropped:* the ink is the look of every model (D51, D55) and is set
  per screen, not per model; at its width the outer-edge models are still 0.7 px fat, and without
  it the models lose the sprites' dark edge.
- *Middle of the border pixel:* +0.2 to +0.5 px per side from the numbers above, between the two.
- *Strip the border only on closed-border sprites:* per-pixel stripping already leaves inkless
  edges alone, so one rule covers partial borders too.

**Affected (follow-up, not done here).** The models built to the old rule, top views rendered from
their .glbs (rule IoU on the grid now; each would pull its edge in about 1 px where the sprite has
ink):

- Player ships: Talon 0.79, Dragonwing 0.83, Gencore Phoenix 0.70, Microcorp Stalker 0.76, Nort
  ship 0.87, Silver ship 0.83, Supercarrot 0.74, U-Ship 0.71 (its border is 54% of its pixels, 64
  of them free).
- Level 1 (D65): assembly-newsh2-3 0.74, -9 0.75, -87 0.80, -123 0.78, assembly-newsh4-81 0.75, the boss
  assembly-newsh4-124 0.90, newsh2-127 0.86, -159 0.80, -171 0.70, -191 0.72, -229 0.60, -267 0.79, -269 0.80,
  -271 0.80, -49 0.71, -51 0.72, -89 0.86, newshp-13 0.73. Nearly passing: assembly-newsh4-195 0.94,
  -231 0.94 (partial borders). Already passing (no border or opaque to the rectangle):
  assembly-newsh2-53, -115, -119, -245, -273, -279, newshe-39, newsh2-153.
- The older models (D44 and before): of 1022 sprite-model entries with a reference sprite, 253 have
  a closed border and 521 a partial one; they change whenever they are rebuilt.

**Found on the way:** `newsh2-159`'s outline shell (and its -f2..-f5 frames') covers only the
model's middle band, so it shows no ink at all in game (a shell made from the wrong island). Tall
models also read bigger than their sprites in game: a model's origin plane covers the sprite's
screen area (D6) and parts above it are nearer the camera (the boss's +0.78 at the inner edge); that
is height, not the border.

**Review:** the comparison sheets (sprite | current | inner, overhead at game scale, x3 with the
sprite's edge, 15°) and the scripts are in `tyrian-scratch/outline-border/` (`sheets/`, `ingame.py`,
`measure.py`, `survey.py`). Fallback: measure against the outer mask again (`iou_outer_grid`).
## D75 — Galaga mode's doubled pickups read past the item tables: the port reads what the C's reference build reads

2026-11-03

**Decision:** The two "port bugs" the whole-game inventory found (MILESTONES.md, Known issues) are
the C's own behaviour. The sim now reproduces it instead of crashing:

- **ALE crash (level 1.18, section 41):** in galaga mode JE_searchFor doubles the value of every
  enemy it finds (tyrian2.c L4148-4160; tyrian2.ts JE_searchFor), and `evalue` is a JE_integer, so
  it wraps. Events 70 and 75 search again on every pass of a level's waiting loops, so an enemy of
  value 15 reaches 30720 after eleven doublings. Touching it, JE_playerCollide (mainint.c L4634-4669; mainint.ts JE_playerCollide) takes
  it for a front-weapon pickup and reads `weaponPort[720].name`, sets the weapon id to u8(720) = 208
  and the special to `specialArcadeWeapon[719]`, all past the tables' ends. The port threw on the
  undefined record (tick 2815 of tools/inventory.mjs's run, seed 1041). Other reachable cases: 375
  (a cash pickup in ALE) reaches 30464 (weapon 208, special `specialArcadeWeapon[463]` = 125), and
  250 reaches 32000 (rear weapon u8(1000) = 232, name `weaponPort[1000]`). SQUADRON's enemies can do
  the same.
- **What the C does:** undefined behaviour, so whatever its memory holds. On the reference build
  (tools/opentyrian-bot/run.sh: Apple clang -O1, arm64 macOS, where every bot fixture comes from)
  the item tables lie back to back: options, powerSys, shields, ships, special, weaponPort, weapons
  (71,820 bytes; checked with the linker's symbol addresses and by dumping the block from the
  running C for episodes 1 and 4, byte for byte equal to what src/sim/overrun.ts builds). The
  constant tables from SAWeapon on are followed by the rest of OpenTyrian's read-only data.
  src/sim/overrun.ts rebuilds the item block from the item data (JE_loadItemDat's fields at the
  structs' offsets, `name[min(len, 30)] = '\0'`, zero padding), appends to weaponPorts, specials
  and options every record a Uint8 id can select (up to 255, decoded from it), reads the pickup's
  names as `%s` would, and holds the 2,562 compiled bytes from SAWeapon on for
  `specialArcadeWeapon`, `optionSelect` and `SAWeapon` reads past their ends. Past both blocks
  (weapon names for values from 30805 or 31805, SAWeapon in a Super Arcade galaga game) the C reads
  its mutable globals or build-dependent unwind tables; the port reads zeros, "" for a name. Those
  only feed the text window, or need a Super Arcade game in a galaga level. Weapon 208 then fires
  nothing (player_shot_create rejects ports over 42), so the bot can't kill the enemies event 70
  waits for and ALE stalls at curLoc 2601-2610: the C does the same, tick for tick, for 30,000 ticks.
  JE_playerCollide also gains the C's Uint8 truncation of `items.special` (value - 32100) and of a
  Super Arcade weapon id.
- **SQUADRON never ends (level 4.18, section 45):** genuine. Its event list has no end-level event
  (11) or ready-to-end (36); after the start it jumps to a wave table at 60000 that calls the waves
  (event 54, each returning through event 76) and jumps back to 60000. The invulnerable bot can't
  end it; the C, with the same bot, matched the port for 60,000 ticks (seed 4045, every 100th
  tick). The only end is the ship out of lives: game over, then the C waits for a key (the host's
  key in src/app/run.ts), as with the bot without its cheats.
- **Found on the way (the mortal SQUADRON cross-check):** start_level_first's JE_drawArmor
  (tyrian2.c L834) caps armor at 28, and the port skipped it as HUD; it also called JE_getShipInfo
  a second time after the level's world setup (game.ts startLevel), which the C doesn't. ENGAGE's
  Stalker 21.126 has 30 armor, so the port's ship started at 30 instead of 28 and the armour ship
  came later than the C's. newgame.ts now caps as the C does, and startLevel no longer repeats
  JE_getShipInfo.

**Tests:** tests/sim/galaga.test.ts (the read-only block starts with the three tables; every
in-range record decodes from the rebuilt memory as the item data parses it; ALE's inventory run
survives tick 2815 with weapon 208; SQUADRON's loop, and its game over with a mortal bot). C
cross-checks in botTrace.test.ts: `ale-seed1041` (the inventory's ALE run, 6,000 ticks) and
`squadron-mortal` (14,000 ticks: game over at 13,136, then the wait for a key). driver.c gains BOT_SEED (seed
before JE_initPlayerData, as the inventory does) and BOT_MORTAL (no cheats); run.sh's play_case
takes `seed=N` and `mortal`. Each botTrace case now starts from new players, as each driver run is a
fresh process (JE_initPlayerData leaves friction, mouse and sidekick state alone, in the C too).
docs/roadmap/inventory.* are regenerated: ALE runs its 60,000 ticks. Some counts of later levels
shift slightly because the inventory plays every level in one process and ALE's full run leaves
that same player state behind (episode 2 played alone gives the old numbers).

**Options considered:**
- *Reproduce the reference build's memory (chosen):* the C cross-checks are this build, and with
  it the port matches the C through and past the overrun.
- *A guard (skip the pickup, or treat a missing record as empty):* hides the divergence: the C does
  pick it up, loses its gun and stalls.
- *Clamp the doubled value:* changes what the C's galaga games do (a 32000 would become a cash
  pickup instead of rear weapon 232).

Fallback: drop `extendItemTables` and the overrun accessors; the C tables' bounds then throw again.

## D76 — Coin and gem values as crisp flat art, redrawn from their own pixels

2026-11-03

**Decision:** The value a coin, gem or data cube shows when picked up (a fixed-position explosion,
types 35-52 of newsh6.shp: 10, 25, 50, 75, 100, 250, 500, 1K, 2K, 5K, the brown ALE/375 plaque,
800, 150, 350, 500, 750, the red 50 and DATA) is drawn as flat sprite art (D42) in the remastered
look, instead of an extruded sprite: chunky pixel digits standing up off a dark plate.
- **The art** (`tools/value_art.py`, no Gemini): each of the 18 sprites is redrawn from its own
  pixels. Every digit pixel is joined to its digit neighbours and the centre lines are drawn with a
  rounded-square pen a little under a pixel wide, so every digit keeps the original's shape,
  placement and staircase layout but has clean antialiased edges and softened corners; the colours
  are the digits' own palette colours (palette 5, as the other flat art) blended smoothly between
  pixel centres, with a soft bevel lit from the upper left. The plate is the sprite's darkest colour
  under its whole silhouette, rounded as the flat art's alpha is, shaded slightly top to bottom with
  a faint glow of the digits round them. The red 150/350/500/750, which have no plate, get a faint
  dark shadow inside their box.
- **Wiring:** one atlas, `public/art/sprites/newsh6-shp.webp` (66 KB), and a `newsh6.shp` sheet in
  the manifest, keyed by the sprite drawn (explosion_data's sprite + 1). None of those indices is a
  frame of a moving explosion, and no enemy bank loads newsh6, so nothing else changes. The manifest
  gains an optional per-sheet `scale` (`spriteArt.ts`): these frames are 16 texels per pixel, twice
  the rest, as the numbers are small and read. `flat_art.py cut` now keeps sheets it didn't make.
- **The game contract** is the flat art's: `?sprites=original` (or A, or the original effects look)
  draws them extruded as before; the explosions' "blend" draws them at the renderer's 0.55 opacity;
  the level filter and brightness recolour them; the atlas is loaded with the others before the level.

**Options considered:**
- *Vector text in a font (canvas or SDF quad) at the draw's position:* sharp at any size, but the
  values are partly not text (the ALE/375 plaque, the slanted 1K, the staircases, the multi-coloured
  800) and the original's plates and colour ramps would be approximations.
- *Gemini paintings, like the other flat art:* nothing to gain over redrawing 1-px strokes exactly,
  and a painted digit can drift from the original's.
- *Keep them extruded, with smoothing:* still a 3D slab with sides for a 2D readout.

**Review:** `?debug=play&seed=1&skip=T&freezeAt=T&armor=99` at T = 301 (75 over a fireball), 815 and
2031 (DATA), 1670 (two 25s), 6426 (250). The flat draws go before the other transparent draws, so
a value spawned on a fireball now sits under its glow rather than over it (still readable). Cost:
66 KB download, one more draw call while a value is on screen. Fallback: drop the manifest's
`newsh6.shp` entry.

## D77 — The shield's hit arcs become one energy bubble round the ship

2026-11-03

**Decision:** When a hit only takes shield, JE_playerDamage draws nine light-blue arc tiles (explosion
types 14-22, newsh6 sprites 229-237, 248-256 and 267-275) in a 4x3 grid round the ship, for three
ticks. The remastered effects (D35) drew them as hot extruded sprites: stair-stepped pixel arcs.
They now draw as one energy bubble (`src/render/vfx/shieldLayer.ts`): a sphere squashed to 20 x 11 x
19 px round the ship model, at the ship's height, additive, its rim bright by a fresnel term (so from
the game's camera it reads as the original's ring), with a faint hexagonal cell pattern and a wave
running from its middle to its rim over the hit. The arcs are hidden.
- **Placement and timing, from the original:** `explosionFrames.ts` gains an `ExplosionKind.Shield`
  for types 14-22 and `shieldArcCentre(type)`, each arc's offset to the middle of its grid, so every
  arc of one hit names the same point (the player's x + 7, y + 9: just below the ship sprite's middle,
  as the C draws them; a test checks it against the sim's JE_playerDamage). One bubble is drawn per
  hit and frame, on exactly the frames the arcs are drawn, moving with them (they scroll, as in the
  C). It grows (0.84, 0.94, 1.04 of its size) and fades (1, 0.8, 0.5) over the three frames, as the
  arcs widen; two hits a tick apart overlap as two bubbles, each with its own cell pattern.
- **Colour:** the arc sprite's own palette colour, the way the shot halos take theirs (D35), so
  palette fades and flashes carry through.
- **Light:** the first frame also lights the ship's surroundings faintly in that colour, from the
  explosions' pool of four lights (merged across the nine arcs).
- **Switch:** `?vfx=original` (or V in the play harness) draws the arcs as the original sprites, as
  before. Other spark types (11, 13, 23-34: shot trails) are unchanged.

**Options considered:**
- *A fresnel bubble round the ship (chosen):* one instanced draw, no assets, smooth at any size, and
  from above it is the original's ring.
- *Flat art for the arc tiles (D42):* would keep the 4x3 tile seams and the gap at the bottom right
  (the C draws only nine of twelve tiles); a ring split into nine sprites stays a pixel object.
- *A full shield mesh that stays round the ship and flashes:* would add a state the sim doesn't have.

**Review:** `?debug=play&seed=1&skip=N&freezeAt=N&solid=1` at 295, 296, 297 (a hit, then a second one
a tick later) and 636; captures in tyrian-scratch/pixel-sweep/shield-hit-arcs/. At 1920x1080 the
harness held 60 fps with cpu about 7.3 ms a frame at tick 296 (two bubbles) and about 7.0 at 290 (no
hit), 311 and 315 draw calls: within the noise of a machine busy with other runs. No
download beyond the new module (6 KB of source, 2.4 KB gzipped). If the bubble reads too strong or
weak, the shader's `a` line and `SHIELD_FADE` in remasteredFx.ts set it.

## D78 — Cloud rims: the HD cloud tiles' alpha follows a smoothed contour, solved across tile edges

2026-11-03

**Decision:** The alpha of the HD terrain's layers 1-2 (`tools/terrain_hd.py`, `alpha_level`,
`solve_alpha`) is no longer the MMPX 8x silhouette blurred at 3 texels and ramped (D58), which kept the
8-texel stairs MMPX leaves on slopes that aren't 45 degrees and drew TYRIAN's cloud rims (40-44, 50-52,
54, 62-64) as polygons. It is now:
- **A smoothed contour.** The MMPX mask's signed distance (clamped to +-24 texels), blurred at 8 texels
  (one original pixel), with alpha a smoothstep over +-2 texels across its zero. Straight runs stay
  where they were; stairs and one-pixel corners round off. The cloud's shape is still the original's:
  against D58's alpha the half-alpha contour moves 2-4 texels in most tiles and at most 14 texels
  (under 2 original pixels; 41 and 51, where the edge solve bends it).
- **Solved across tile edges.** A tile's contour near a side follows its usual neighbour there, so where
  two tiles that aren't each other's usual neighbour meet (43|44 23 times, 63|64 21 times) the contours
  met with a jog, and 44's left edge drew a thin dark sliver above 43's rim. The distance field (not
  alpha) now gets the colour's seam treatment (D58: strips solved jointly over the map's pairs, faded in
  over 40 texels), over pairs the map has at least 5 times, so contours bend to a shared crossing point.
  Alpha itself is still not averaged (D58's faint line), and rare pairs are left out: with 44|53 (once)
  in, a bar of cloud appeared at 44's empty right edge.
- **`realpha`**, a new command, redoes just this on the committed atlas (colour bled again from what was
  visible), since the Gemini answers aren't kept; `cut` does the same after its colour seams.

**Result** (`public/art/terrain/shapesz/1.webp`, 78.6 KB -> 80.4 KB, same layout; layer 0 untouched):
the stair score (strongest 8-texel phase of the alpha's steps over the mean) of the rim tiles went from
1.8-3.2 to 1.1-1.9 (63: 3.24 -> 1.68, 52: 2.95 -> 1.74, 43: 2.74 -> 1.59, 54: 2.72 -> 1.91); the
count-weighted mean alpha step across the map's tile edges from 0.0026 to 0.0005. In game
(`?debug=play&seed=1&skip=T&freezeAt=T`, T = 300, 1000, 2000, 6500, at 1920x1080 and 3840x2160) the rims
are soft curves with the original's dark edge colour, and 60 fps with the same cpu ms as before.
Remaining: the dark edge is the original's outline colour bled under the alpha (kept, it is the
original's); colour seams inside the clouds are unchanged; pairs seen under 5 times keep their jog.

**Options considered:**
- *Blur the mask more (sigma 6-8) and keep D58's ramp:* rounds the stairs too, but the ramp's width
  then grows with the blur (~6 texels, soft edges); the blurred distance keeps a 4-texel ramp.
- *The painting's own matte:* Gemini's cloud/black edge registered loosely and the rim tiles were
  painted puffier than the original (D59), so it would move the outline.
- *Edge-clamped context at the sides* (contour independent of the neighbour): kinks every diagonal
  contour at a tile edge.

**Review:** before/after captures and crops in `tyrian-scratch/pixel-sweep/cloud-rim-stairsteps/`
(`cmp_*.png`). Fallback: `git checkout` the previous `1.webp`; `realpha --alpha-min-pairs 1000000` keeps
the smoothing without the edge solve.

## D79 — TYRIAN's HD ground repainted from softened sheets: no pixel blocks or checker dither left in the paintings

2026-11-03

**Decision:** About a third of the 66 HD ground tiles (D59/D60) were still upscaled pixel art: 8-texel blocks
and the original's checker dither, which D60's deblock (block edges only) left inside the blocks. At 4K the dark
rock (ticks 0-2300), the light dirt (2500-3000) and the jungle floor between the leaf models (4500-7400) showed a
clear pixel grid. The ground atlas (`public/art/terrain/shapesz/0.webp`, same rects and size, 512 → 508 KB) is
re-cut with eight new Gemini answers; the clouds (`1.webp`) are untouched.
- **Softened input** (`sheets --soft 0.5`, the retry D59 suggested): each region sheet MMPX-smoothed, then blurred by
  half an original pixel, black kept black, written to `sheets/soft/` with a `softPrompt` (paint crisp detail, no
  pixel grid, checkerboard or dither). The blur keeps ~30% of a one-pixel alternation along an axis and ~10%
  diagonally, so Gemini has no blocks or dither to copy; every answer came back painted (blockiness 1.03-1.12,
  against 1.5-1.9 for the tiles it replaced). Sent one at a time, each with a prompt naming what the region shows:
  region-l0-01 (dirt and the crater mound), 02 (rock and dirt paths), 03 and 10 (forest), 04 and 07 (grass
  fringe), 06 (rock and the wreck), 08 (dirt and rock patches). 05 (the H-shaped ridges) came back with wider,
  flatter ridges than the original and is not used.
- **A partial round** (`cut --base DIR`): the old atlas's tiles compete as candidates, so new answers for some
  regions replace what they cover without the old answers (which are no longer on disk). Every candidate is then
  scored the same way: the NCC of its per-pixel means against the original, less its colour error, less 0.12 for a
  base tile (`--base-cost`: its pixel copying is only partly measured), less the pixel penalties below. A layer
  with nothing new is copied from the base unchanged; a base tile that wins is not deblocked or reshaded again.
  The novelty cost (D59) is measured against the new paintings only (a pixel copy has no marks of its own).
- **Pixel period** (`pixel_period`): blocks and dither alike, the alternation from one original pixel to the next
  (8-texel cells) against the same over 6- and 11-texel cells, which no pixel grid lines up with. A painting is
  1.0-1.1; the old light dirt 46 was 1.72, grass fringe 89 1.61, canopy 211 1.52. It costs 0.6 per unit above 1.15.
  With `--blocky-free 1.2 --blocky-cost 0.3` (the base tiles are deblocked, so their blockiness reads low).
- **Result:** 54 of the 66 ground tiles are new paintings; kept from the old atlas are 95, 96, 105, 108
  (ridges, already painted) and the bunker ground 320-323 and 330-333, picked back (`--pick 0:320=base#0`, ...):
  it sits under the bunker models, and the bunker pads are another change's. Hand picks: 99 (`region-l0-06#0`; the scores kept the old one, whose blocks showed in game at
  tick 750), 79 (`region-l0-07#0`,
  its only new painting; it has a few dark sprigs on the sand below the grass patch) and 222 (`region-l0-03#0`;
  the old one was checker). Seam measure (D58): texel step across edges 0.46 of the step inside tiles (was 0.57),
  8-texel bands 0.56 (0.50). The cache is now per answer (`--cache`): a new or changed answer is registered and
  added.

**Checked** in game, `?debug=play&seed=1&skip=T&freezeAt=T&armor=99` at 3840x2160 for T = 750, 1000, 2000, 2750,
5000, 6000, the old atlas through `&terrainart=` (a temporary copy) against the new: the dark rock's grid, the light
dirt's checker and the jungle floor's checker between the leaf models are gone; outlines, the crater, the ridges and
the colours still match the original's; no seams or misplaced tiles. Contact sheets (`check`) for the whole map.
Overlay at tick 1000 (4K, headless, a loaded machine): 54 fps / 8.3 ms before, 56-58 fps / 8.6-9.6 ms after (run-to-run noise); same draws
and atlas size. The typecheck passes; the tests pass except tests that time out on a machine
running many agents (no source file changed; see the PR).

**Options considered:**
- *Edge-aware smoothing of the blocky tiles (no Gemini):* removes the checker, and the detail inside the 8-texel
  cells with it; the tiles would be smooth blur among painted neighbours.
- *A full re-cut from every old answer:* the old answers aren't kept (D3, a scratch folder since deleted); the base
  mode needs only the new ones, and keeps the old tiles that are still the best.
- *Region-l0-05 for the ridges:* its ridges are wider and flatter than the original's and lost the bright rim; the
  old ridge tiles were already painted.
- *Context sheets for the grass fringe:* D59 found brown-green-edges-1 came back as blocks even softened; the two
  grass regions covered every fringe tile.

## D80 — Fireballs and big explosions are flat painted art, like the shots (D42/D43)

2026-11-03

**Decision:** Explosion types 1 (the fireball, newsh6.shp sprites 122-133) and 2-5 / 7-10 (a big
explosion's quarters: air 3-14, 22-33, 41-52, 60-71; ground 154-165, 173-184, 192-203, 211-222) draw
from painted art instead of extruded voxel sprites. At 4K the extruded, emissive sprites read as
blocky pink pixel clouds and a stair-stepped red ring, the biggest bright things on screen.
- **Art:** `tools/flat_art.py` now reads the newsh<c>.shp sheets, and `tools/flat_art_explosions.json`
  is the inventory: three Gemini sheets of 12 cells (the fireball's 12 frames, then a big
  explosion's 12 frames for air and for ground, each frame its four quarters composed as one 24x28
  picture by `LAYOUTS`, as JE_setupExplosionLarge places them) so the quarters are cut from one
  painting and meet without seams. `cut --merge` rebuilds only `newsh6-shp.webp` (108 frames,
  1024x2048, 187 KB) and adds its sheet to `public/art/sprites/manifest.json`, keeping the others.
- **Fire-specific cut options** (inventory, per object): `floor` 0.8 lifts any texel the painting
  made darker than 0.8x the original pixel's own (smoothed) colour, so Gemini's dark smoke never
  replaces a bright original ring; `alpha` {sigma 5, lo 0.3, hi 0.55} is a softer silhouette than
  D43's, so a one-pixel staircase ring becomes a smooth thin line (the edge grows by about a third
  of a sprite pixel; lo 0.1 grew it ~0.8 px and showed a hard cut where a frame touches its box). Fit scores: air 0.94-0.98, ground 0.84-0.98, fireball 0.49-0.93 (0.49 is the
  last, faintest ring frame, whose colour is mostly the floor).
- **One atlas with D76's coin values** (merged with D76, which also drew into newsh6.shp): the
  values stay at 16 texels per pixel through a per-frame `scale` in the manifest (SpriteArtFrame.scale;
  the sheet is at the manifest's 8). Either tool rebuilds the shared atlas and keeps the other's
  frames: `value_art.py` cuts the explosions back out of it and packs them again with the values,
  and `flat_art.py cut` keeps a rebuilt sheet's frames that have their own scale (and, always, the
  sheets it doesn't rebuild).
- **Game side: no other code change.** Sprite2Router already routes a draw with art to Route.Flat before
  the effects; RemasteredFx.sprite still runs, so the glow behind each explosion, its light, sparks,
  embers, debris and smoke stay, and its SpriteLook.Hot is ignored for the flat quad. `?sprites=original`
  (or `?vfx=original`, or A in `?debug=play`) brings back the extruded hot sprites. Palette fades
  don't reach the art (D42); level 1 has none during explosions.
- **Cost:** +187 KB download. At the same frozen ticks the flat explosions are one more instanced
  draw call (the newsh6 atlas) and replace up to dozens of extruded sprite meshes: calls went
  456 -> 436 (tick 249) and 262 -> 243 (tick 330); the overlay's renderer CPU at 3840x2160 was
  5.3-6.3 ms after vs 7.1-8.5 ms before at ticks 150/170/249/750 (a busy machine, other agents'
  captures running, so read it as "no worse"), 60 fps.

**Options considered:**
- *Flat painted frames via the D43 pipeline (chosen):* reads as the original (same outline, frame
  timing, holes and colours), and is free at run time.
- *A procedural fireball shader (noise billboard tinted from the sprite's colours, SpriteLook.Hidden):*
  smoother animation and no art, but its shape would be ours, not the original's frames.
- *Original silhouette alpha (D43's smooth_alpha):* keeps the outline exactly, but left the thin
  rings as dashes at 4K.

**Review:** play `?debug=play&seed=1&skip=249&freezeAt=249&armor=99` (big air explosions) and
`skip=750` (ground ones), and press A to compare. Known limit: overlapping explosions keep the draw
list's order, quarter by quarter, so where two big explosions overlap one can cut straight across
the other at a quarter edge, as in the original (it was there with the extruded sprites too).
Fallback: remove the `newsh6.shp` sheet from the manifest.

## D81 — The rock outcrop's shot-away frames are models: a crater with a pool of blue, from the sprite's fields

2026-11-03

**Problem:** the ground rock outcrop of level 1 (newshe.shp, six 2x2 enemies, types 522-527 once hit
hard enough) had models only for its whole frames (1, 3, 5, 39, 41, 43, `assembly-newshe-39`). Its
damaged frames 7, 9, 11, 45, 47 and 49 (the rock shot away, a pool of blue showing beneath) had none,
so each piece turned from the 3D rock into extruded pixel blocks when hit (D54's `KNOWN_DAMAGE_SWAPS`;
ticks ~2012-2115 with `&power=11`, at the right edge).

**Decision:** `assembly-newshe-39.py -- --damaged` builds the damaged state as one assembly cut into
the same six pieces and exports them as `newshe-<n>-f2` (each listed for its damaged frame in
`src/render/spriteModels/newshe-<n>-f2.json`, so the existing router, preload (levelSprites lists
damaged graphics) and never-pop rules apply unchanged). The sprite is authoritative and shows no rock
left, so the model is what it shows, not a broken boulder: a dark scorched crater, a flat pool of blue
ringed by its dark rim, loose stones round it and a few broken shards on its south side. Built like
D63, from smoothed fields of the sprite's own pixels, so no edge is a pixel step:
- the scorch: a thin slab cut along the 0.5 iso-line of the blurred dark-pixel mask (index 32,
  160-163); lone dark pixels become small round flecks;
- the pool: a slab cut from the blurred mask of the blue (144-159) and its rim (80-83); its top is split
  into isobands of the bilinear sprite (the blue ramp is ordered dark to bright), every other ramp
  index so a piece has at most ~20 materials; slightly glossy, a faint palette glow on the brighter
  bands; the bright spots are sheen, kept as colour, not relief;
- the stones: each 4-connected group of grey pixels (2-11) is a convex stone on its own pixels, height
  from its size (to ~4.6 px), lit faces in its brightest indices;
- no ground patch: like the undamaged pieces (D67), the sprite's dirt round the crater is not
  modelled (it was a plate of 2 x 2 px dirt cells with a hard edge against the HD ground); the HD
  ground shows there, and the covered crater tiles under it (D67) keep the original crater hidden;
- an ink outline shell (D51) of the stones and pool only; plain palette materials, no bake.
The frames are read from the game data at build time (`TYRIAN_DATA`/`data`, palette 5): the catalogue
only has an enemy's own frames.

**Options considered:** *the rocks with a broken top exposing a blue core* (the issue's first idea):
the damaged sprites show no rock mass at all, so it would not read as the original. *Per-pixel
coloured pool:* square steps again. *Isobands of every ramp index:* 27 materials on the biggest piece;
every other index looks the same in game at half the draw calls.

**Review:** in game (`?debug=play&seed=1&skip=2050&freezeAt=2050&armor=99&power=11`) at 1280x800 and
3840x2160 the shot-away pieces are the crater and pool instead of pixel blocks; 60 fps, cpu ~9 ms in
both, draw calls 380 -> 480 while four damaged pieces are on screen. Six GLBs, 667 KB in all (level 1
preloads them with the damaged graphics). `tests/render/modelSwap.test.ts` no longer lists types
522-527 and passes (no model/sprite mix on level 1, preload coverage on episode 1).
Fallback: delete the six `newshe-*-f2` GLBs and JSONs; the damaged frames go back to extruded sprites.

## D82 — Tall buildings are real buildings drawn in the art's oblique view

2026-11-03

**Decision:** A structure whose tiles paint a roof with a wall below it is built as the real
building, then drawn the way its tiles draw it.
- **Is it tall?** `tools/tall_buildings.py analyse` splits the tiles into roof and wall. In each
  column the edge is the biggest drop in brightness, summed over a tile's width. The structure is
  tall when all of these hold:
  - the painted wall band is at least 6 px;
  - the band runs along ≥ 60% of the building's columns;
  - it is about as tall everywhere (spread ≤ 0.5);
  - it is darker than the roof (≥ 0.08);
  - its detail runs up and down.

  The game camera can't show that much wall. At 15° a vertical wall shows 0.31 px per px of height
  at mid-screen (0.72 at the top, −0.09 at the bottom), and a ground structure may be 0.8 units
  tall (D5), about 3 px of wall.
- **The model** (`assets/blender/tiles/lib_tall.py`):
  - it stands on the roof's outline moved down by the wall band, i.e. where the wall meets the
    ground;
  - its walls are vertical, 1 px of height per px of painted wall;
  - the roof and the south wall wear their own pixels, row for row, as a low relief in palette
    materials;
  - no concept bake.
- **The renderer** (`src/render/remaster/structureInstances.ts`) reads two extras:
  - `tyrian_oblique: k` puts each vertex on the camera ray through the base-plane point the art
    draws it at (k px up the screen per px of height). This is D6's lift, applied per vertex.
  - `tyrian_depth_band: [lo, hi]` gives each vertex the depth of that ray's point at its height
    squeezed into the band: [0, 0.04] on the ground, under background 2's under pass at 0.05;
    [0, 0.38] on background 3.

  So the roof and wall land exactly where the tiles paint them, at every tilt and scroll
  position. Everything the original drew over the tiles still draws over the building. Normals,
  light and shadows are the real building's (the shadow pass doesn't use the transform).
- **Measured** with `tools/tall_buildings.py measure` (`tools/tall_render.py`). It renders the game's
  three cameras at the screen's top, centre and bottom, projected onto the ground plane, and scores
  screen IoU, roof/wall IoU, per-region colour, footprint IoU and drift. Acceptance targets are in
  `docs/agents/TALL-BUILDINGS.md`.
- **Applied** to SAVARA's two towers (Episode 1, map 1-8; `assets/blender/tiles/savbld_towers.py`,
  the tiles kept under them). Their tiles are a kit that also makes shorter and taller towers in
  Episodes 1 and 4, so each pattern needs all its rows drawn (`minRows` 5 and 7). Until then the
  tiles show, and the model lands exactly on them. TYRIAN (level 1) has no tall structure by the test: its 14
  analysed patterns fail on band spread, wall darkness or detail direction. In game no variant
  improved on its drums (a 7 px front face on one tile). So level 1 is unchanged.

**Options considered:** each was built from the same split with the same kit, on SAVARA's wide tower
(54 px wall under a 57 px roof) and tall tower (110 px under 56), and TYRIAN's drum. Each was judged
in the game at 0°, 15° and 32° and at three ticks of its pass. Metrics are for the wide tower: screen
IoU at 0°/15°/32°, mid-screen; drift from the top of the screen to the bottom at 15°.
- *A, footprint + true height, real perspective:* IoU 0.42/0.64/0.77; drift 37 px (tall tower 86).
  The roof floats off its tiles, magnified (the tall tower is 9 units, half the camera's height). Big
  dark side faces show. Turrets or shots on the roof would miss it.
- *B, fit the 15° camera within the pass budget (0.8 units, walls leaning back):* IoU
  0.96/0.93/0.88; drift 3 px. It looks like the original, but as a 3D object it is the "sloped slab".
  Its wall faces up, so it is lit like a roof (wall IoU 0.12).
- *C0, true height plus a static lean fitted to 15°:* IoU 0.83/0.75/0.74; drift 12 px. A leaning
  slab.
- *C, true building, oblique-locked (chosen):* IoU 0.98 at every tilt and place, roof 0.95, wall
  0.97; colour error 3/4; drift 0. It looks like the original at all three tilts, with wall lighting,
  relief and a real shadow, and in the viewer it is a true tower.
- *True height fitted to 15° with vertical walls:* the wide tower would be 172 px (14 units, 74% of
  the camera's height). Rejected without building it.

**Found on the way:**
- A raised ground structure hides background 2's under pass (SAVARA's clouds at 0.05). Hence the
  ground band's top of 0.04. The existing ground structures are up to 0.8 units tall (lib_l1bld
  TALL_MAX), so they would do the same over clouds; not checked in game.
- The pass budget (D5) caps every structure's real height at well under a unit. The depth band
  lifts that cap for any model that needs it.

**Review:**
- Play SAVARA (`?debug=play&main=29&seed=1&skip=2300&freezeAt=2300`, and 2500 for the tall tower) at
  each Camera.
- Known limits:
  - The building never shows more wall at 32° and has no parallax, like every flat tile.
  - Its side faces never show.
  - Its tall shadow falls beside the painted one in the ground tiles.
  - The wall wears the painted wall's colours and is lit as a south-facing wall, so it reads darker
    than the tiles in places.
  - Layer-2 tall structures, and buildings whose roof edge steps, aren't covered by the kit yet.
  - The wide and tall towers are 12.8k and 13.7k triangles, 0.65 and 0.71 MB (one quad per wall pixel).
- Fallback: delete `src/render/tileModels/shapesy-savbld-*.json`. The renderer's extras are inert
  without them.

## D83 — HD terrain per tileset: every level that uses it at once, cuts merged into the atlas, layer 2 sorted into terrain and structures

2026-11-03

**Decision:** `tools/terrain_hd.py` works on a tileset rather than a level, so `shapesz` (32 of the 62 levels) can be
done without undoing level 1 (D58's limit: a second level's cut replaced the first's atlas).
- **Levels.** Every command takes `--level 1-9,1-11,...` or `--tileset shapesz` (the levels whose `tyrian<ep>.lvl`
  slot names that shapes file: the same 32 `docs/roadmap/inventory.json` lists). The inventory merges the tiles
  over all the maps: counts summed and per level, usual neighbours over every map, one representative 3x3
  neighbourhood from whichever level fits best; `hasArt` from the atlas already there. One level gives exactly
  D58's inventory.
- **Kinds.** Each tile gets a kind: *terrain* (painted: all ground tiles; on layers 1-2 natural materials, brown and
  green ramps, fills that meet themselves on every side, tiles a ground model stands on elsewhere, tiles with art),
  *structure* (layers 1-2 hard surface: plating, pipes, walls, machines; left to structure models, D34/D47, painted
  only with `--structures`), *empty* (one colour, Tyrian's black space: nothing to paint, it falls back to the 4x
  ground, which looks the same). `--kind 2:575=terrain` overrides. Tiles also list structure models and paintings
  of the same tile on other layers.
- **Sheets** only for tiles that still need a painting (no art, terrain, no painting on another layer to reuse):
  map regions as a set cover over every level's map (also for layer 2's terrain), contexts as before; softened from
  the start (D59/D60's lesson; the nearest-neighbour picture beside it), prompts naming each region's two main
  materials (per layer: the same colours are clouds on layer 1 and purple metal on layer 2), a `send` order (most-used
  new tiles first), `SEND.md` and a prompt file per sheet for the operator, and a request count.
- **Cut merges.** The tiles already in `public/art/terrain/<tileset>/` are kept: their images are not rewritten, their
  rects not moved. In the seam solve their edge strips are held (moved to the right-hand side), so new tiles are pulled
  onto them and they don't move. New tiles go into new images (`0-2.webp`; `2.webp` for a layer without art yet), at
  most 323 per image, whose rects name them, which D57's format already allowed. A tile without a painting of its own
  reuses the same tile's painting from another layer. `--recut`, `--replace` (D58-D60's fresh cut), `--no-reuse`. One
  level into an empty folder (or `--replace`) still writes TYRIAN's fake-answer atlas byte for byte (checked against
  the previous tool from the same cache).
- **Game side:** none needed. One fix: the loader marked only a layer's main image as opaque, so a layer-0 rect's own
  image would have been uploaded premultiplied (harmless for an opaque image, but not the contract); it now marks
  every layer-0 image (test added).
- **Check** reports seams over all the levels, for the edges with a new tile and for the rest, per level, and also only
  where the original itself is continuous across the edge (`continuousRatio`); contact sheets only of the row blocks
  with a new tile.

**Layer 2 on other levels.** On TYRIAN every layer-2 cell was under a model (D58). Over `shapesz`'s 32 levels, 115
layer-2 tiles are drawn as plain tiles, on five maps:
- *terrain, painted* (73 tiles, 16,100 cells): the brown rock masses and plateaus of 1-11 HOLES and 1-16 ASSASSIN
  (35-57, 76, 80-119), the grass and forest of 4-1 HARVEST (68, 69, 210-234), and HOLES' bunker, wreck and boulder
  tiles (112, 113, 320-352). 54 of them are TYRIAN's ground tiles, so their paintings are reused; 19 need Gemini (3
  region sheets). The tree, bunker, wreck and boulder tiles have ground models on level 1 (keepTiles): layer-2 entries
  for those models would stand them on layer 2 the same way (not done here).
- *structure, to model* (42 tiles, 2,625 cells): the purple and grey plating, pipes, coils and machines (290-304,
  550-595) of 1-5 DELIANI, 3-11 New Deli (the same map) and 4-1 HARVEST: a structure kit by pattern, like level 1's.
- Layer 1 likewise: TYRIAN's island rock (120-142) on 1-6 MINEMAZE and 3-3 GAUNTLET (the layer-2 rock models would
  serve with layer-1 entries), girders (576-599) on 1-5/3-11 and purple plating (536-581) on 3-5 BONUS (structure), and
  one fill, 518, the blue panel floor behind all of 1-18 ALE (painted).

**The `shapesz` batch** (not sent; a Gemini operator run follows under the shared lock): 200 ground tiles, 1 layer-1
and 19 layer-2 tiles to paint, 9 empty; 32 primary sheets (28 ground regions, 3 layer-2 regions, 1 layer-1 context),
about 42 requests with retries at TYRIAN's rate (27 for 21), so two Gemini sessions; 28 optional context sheets for
retries. The sheets are made from the game data and stay out of git (D3).

**Fake runs** (stand-in answers, cut into a copy of the committed atlas). The kept images came out byte for byte in
both. Seams are the step across tile edges over the step inside tiles; on fake answers TYRIAN alone measures 0.81
(D58: 0.88), against 0.57 on its real answers, so these compare runs rather than meet D60's target.
- *All 32 levels* (60 sheets): 200 new ground tiles, 1 layer-1 and 73 layer-2 tiles (34 of them reused paintings).
  Ground: edges with a new tile 0.659 (bands 0.60), kept-only edges 0.568 (bands 0.49); per level median 0.71, TYRIAN
  0.573 as before; worst 3-5 BONUS 1.49 (the purple pipe kit drawn on the ground, in pairs that occur once or twice),
  3-7 STARGATE 1.34 and 1-4 BUBBLES 1.12 (glossy red bubbles; faint smears in the black beside the clusters), 1-10/2-3
  BONUS 1.07. Layer 2: 0.72 (bands 0.39; 1-11 0.70, 4-1 0.75, 1-16 0.82). Layer 1: the new fill 0.91.
- *Five levels* (1-9, 1-11, 1-16, 1-5, 4-1; 24 sheets): ground new-tile edges 0.585, kept-only 0.561; 1-11 0.588, 1-5
  0.637, 4-1 0.632, 1-16 0.80 (ASSASSIN's asteroid rock ends at tile borders against space); layer 2 0.73.

Tests: `tests/tools/terrainHd.test.ts` runs `terrain_hd_test.py` (merge byte for byte over 1-9, 1-11, 1-16; new edges
under 0.65 and over 1.5x worse without the seam pass; level 1's edges as before; a second cut changes nothing; held
strips stay).

**Found, not fixed:** TYRIAN's 15 cloud tiles were seam-solved over TYRIAN's map only; 1-11, 1-14, 1-16 and 4-16
use them in other pairs (42 over 52: 16 times in TYRIAN, hundreds there), and the merge keeps them, so the cloud
measure is 0.82 on 1-9 but 1.11 on 1-11 and 1.13 on 1-16 (bands 0.51 on all). The fix changes level 1's clouds:
re-cut layer 1 over all the levels (`--recut 1:40,...`; TYRIAN's answers are not kept, so 2 cloud sheets again) or
D57 variants for the worst pairs.

**Options considered:**
- *Merge into the atlas, new tiles in new images (chosen):* level 1 untouched by construction; the format already
  had per-rect images; one more instanced draw per extra image.
- *Re-cut the whole tileset into one atlas per layer:* one image per layer, but every re-encode of the lossy WebP
  changes the kept tiles and the strips of the kept tiles would move with the new pairs; TYRIAN's answers aren't
  kept, so it couldn't be re-cut from its paintings anyway.
- *Copy the kept tiles' texels into a new packed atlas (lossless):* unchanged texels, but lossless atlases are much
  bigger (not measured here) and every level's download changes.
- *Paint layer-2 structures too:* flat paintings of pipes and machines next to D34's models; models are the rule for
  hard surface.
- *Edge-aware strips (implemented, `--edge-aware`, off):* don't tie two strips where the original has a real edge
  between the tiles (its facing pixels differ by 64-128 levels or more in some channel), one system per original pixel.
  Over the 32 levels it measured no better where the original is continuous (new ground edges 0.642 against 0.641)
  and kept the real edges (0.725 against 0.659 in all); with 40-100 it was worse (0.758 continuous); the smears beside
  the bubbles stayed. Kept as an option to try on real answers.

**Review:** `sheets/SEND.md` in the batch folder; the fake run's `check/*.jpg` (HOLES' layer 2, ASSASSIN's asteroid
rock). In game after the real cut: each level's `?debug=play&episode=E&main=N&seed=1&skip=T&freezeAt=T` in both looks.

## D84 — TYRIAN's island rock redrawn HD: the tiles' own stones as smooth cushions in a palette-data texture, an edge band per neighbour

2026-11-03

**Decision:** The island rock (the 16 rock tiles of D63, the rock TYRIAN's structures carry, and the rock
round the five machines of D66) no longer draws each 2x pixel as a palette-coloured face, which read as
pixel stair-steps and checker shading next to the painted HD ground. It is the same stones, redrawn:
- **The stones** (`assets/blender/tiles/lib_rock_hd.py`, numpy only, so Blender and the checks run the same
  code). From the art among its neighbours: MMPX 2x; each pixel climbs the smoothed brightness to its
  peak and the pixels of one peak are one stone (grey and warm stones found apart, so a tan stone doesn't
  climb into the brighter grey one beside it); basins whose shared edge is, on average, nearly as bright
  as the dimmer peak merge (one stone, two highlights); pixels darker than 0.12 are mortar, outline and
  roots. Then at 8 texels per pixel: the signed distance to a stone's edge (from the 4x boundary,
  smoothed, so outlines are curves, not steps), the stone's own shading smoothed (plus the art's
  highlights kept as crisp glints: sheen, not bumps), its majority ramp; and pointwise a soft mortar line
  along every edge, a cushion rising over 1.8 px, the shading a little darker toward the edge, a little
  tile-periodic surface noise. Each stone keeps its place, size, outline and colour from the art.
- **Palette data, not colour.** The texture is R shade (0..15, continuous), G ramp code (grey, tan, brass;
  an enemy's rock may add one more, the red machinery's blue-grey stone), B height. The game draws it with
  `src/render/rockMaterial.ts`: colour = palette[ramp * 16 + shade], interpolated between the two shades,
  from the live palette texture, so level palettes, fades and JE_filterScreen apply exactly, and the hit
  flash and smoothie hue (the `hue` that `colourFrame` gives pal_ materials) replace the ramp as the C
  does. One material per tile instead of 10-15 palette materials. The textures are packed as lossless
  WebP, which the glTF export embeds as they are (a lossy WebP, as the bakes export, halves the
  colour channels the height and ramp live in: the bump went flat and seams came back). The tan stones are the art's own tan
  (D63 snapped many to brass, so they read gold before).
- **Relief is the bump.** B is a bump map (three.js's, reading B; at a tile's edge the slope is taken
  looking back, not past the edge). The tops are level: geometry is per tile and can't follow the edge
  bands below, and any relief there (tried: cushions from the texture, edges pinned to one height, the
  normals set up along the seams) left a fine crease along every seam. The rock tiles are now 0.6-2k
  triangles instead of 1.7-3.9k (every vertex along a tile's edge is kept, so neighbours share them:
  an edge one side merges into one and the other doesn't rasterises with hairline gaps). The island's outline is the 2x pixels with the stair steps rounded off;
  the underside tiles (140-142) still hang their face toward the camera.
- **Seams.** A tile's texture is made among its usual neighbours on TYRIAN's map and its edges solved
  against every tile the map puts beside it (D58's strip solve), but only 34% of the map's seams have both
  tiles' usual neighbours matching, and a solved compromise showed as a soft light band along the row
  seams. So for every pair of island tiles the map puts side by side (401 pairs, structures' tiles
  included), the two are computed together and each gets a 3 px **edge band** for that neighbour
  (`pair_bands`, in a second texture on the material's emission slot, keys in `tyrian_rock_bands`).
  `StructureInstances` gives each copy a `rockBands` instance attribute from the level's map (left,
  right, up, down), and the shader draws the band for the neighbour that is actually there, fading into
  the tile over 1 px; in a corner the nearer side wins. A structure's rock is one material per cell
  (`tyrian_rock_cell`: its row and column), so each cell of each copy gets the bands of its own
  neighbours, inside the structure and round it. A neighbour without a band (other levels' pairs) gets
  the solved texture.
- **Structures and enemies use the same builder.** `Structure.rock` builds each cell with `rock_tile`
  (the concept bake, `texture_bake.py`, now keeps a plain material's own UV map through its round trip:
  it used to drop every UV map, which gave the rock the bake's);
  under a structure's own parts the rock is level and darkened in its texture with a soft edge (no
  pixel-step dark patches). `sprite_rock` (D66) builds the enemy's rock from its sprite with the same
  code, one texture for the whole assembly, dark under the machine, a sheet without side walls (each
  piece reaching 0.5 px over its neighbour, as the game places pieces apart), fading out over 1.5 px at
  the edge of its painted area into the island under it (coverage in the texture's alpha; the material
  stays translucent).
- **Original look.** Tied to Options → Graphics → Terrain (D57): "Original" draws the same texture one
  colour per original 2x pixel (whole shades and ramps, no bump): the pixel look, as the original look
  draws the ground from its MMPX tiles. It is not D63's exact relief or colours (that would need the old
  models alongside); `git revert` of this entry's commit is the way back to them.

**Options considered:**
- *Geometry stones (each stone a bevelled cushion mesh in palette materials):* crisp, but a cushion per
  stone in every tile is more triangles and draws than D63, the stones' shading would still be one colour
  per material, and stones crossing seams still break unless both tiles know each other.
- *Gemini painting (D58/D59's way):* allowed during this work, but a painting doesn't carry palette data
  (fades, flash and other levels' palettes would only be approximated, D60's limits), the stones would move
  and need registering, and seams would still need the solve. The deterministic stones keep the art's
  stones exactly.
- *A plain RGB texture:* fewer channels, but no exact fades or hit flash, and the tiles are in nine levels'
  palettes.
- *Seams by the strip solve alone:* measured smooth (step ratio below 1) but visibly smeared along rows;
  *per-tile textures with no solve:* a hard grid. *Variants (a model per neighbour set):* hundreds of
  textures. Edge bands per pair are the variants' cost cut to the 3 px that matter.

**Review:** `?debug=play&seed=1&skip=T&freezeAt=T&armor=99`, T = 2700, 3000, 3300, 3550, 4300, 4900, 5000,
and at 3840x2160 (before/after in the PR). Seams, `python tools/rock_hd_check.py` (every seam between
island rock tiles on map 1-9, 1,210, as the game draws them): colour step across a seam 2.12 against 2.00
between texels inside (ratio 1.06), 8-texel bands 13.6 vs 13.3 (1.02); the original 1x art 1.13 / 1.15;
the solved textures without bands 0.87 / 0.58 (lower because a smear has no steps: that was the light
band along the rows). Costs: the 42 models (16 tiles, 12 structures, 14 enemy pieces) are 16.7 MB →
13.1 MB (tiles 2.6 → 1.6, structures 9.9 → 8.0, enemies 4.2 → 3.5); draw calls in the overlay at
T = 2700/3000/3300/3550/4300/4900/5000, 1132/1078/875/686/1122/1065/762 → 514/445/255/289/453/541/344;
CPU per frame (overlay, before and after run alternately on a heavily loaded machine, so only the
ratio means much) 16.5-18.6 → 8.2-9.7 ms at 2700, 9.9-13.5 → 4.6 ms at 3300, 17.7-19.0 → 8.9-9.2 ms
at 4300, 51-59 → 60 fps. Known limits: the crater's cell is darker than the rock round it,
as its art is; an enemy's rock meets the island under it with a 1.5 px fade (its coverage in the
texture's alpha), and stones there don't line up with the tiles'; pairs from the other eight levels
that use these tiles fall back to the solved textures.
Fallback: revert this commit (scripts, models, rockMaterial.ts, the instance attribute).

## D85 — The menus in copper and bronze: the original's layouts on umber glass over the dimmed planet

2026-11-03

**Decision:** Every menu screen outside the title (D64) and the HUD (D61) drops the navy and gold
look. The user chose direction 3, "Copper and bronze", from three mockups
(`tyrian-scratch/ui-copper/mockups/d3-hybrid.html`, sheet `sheets/d3-hybrid-sheet.png`).

- **Panes:** dark umber glass (`--ui-pane`, 86%, 8 px blur) in a 2 px bronze rim lit from above.
  `.ui-panel` and the new `.ui-pane` draw the rim as one border with a shade per side, so the glass
  stays see-through and the corners round without a wrapper element.
- **One colour rule:** what you choose is copper: titles in the title menu's copper type, small
  spaced kickers and section labels, and the chosen line with the title's brush smear, a diamond tick
  and lit copper words. What the game counts is phosphor green, as on the HUD: credits, prices,
  scores, gauges (volume, power, armour, shield, the generator) and the help line, which becomes the
  HUD's message bar (`.ui-msgbar`, a well). There is no glow, and green is used only for numbers and
  the message bar. Primary buttons (Done, Continue) are drawn as a chosen line with ticks on both
  sides.
- **Tokens first** (`src/ui/tokens.css`): the copper, rim, well and phosphor tokens are added, and
  the old names (`--ui-gold`, `--ui-cyan`, `--ui-ink`, `--ui-steel`...) point at copper and bone, so
  every screen that read them follows. `--ui-focus-fill` is now a full background value (the
  smear), not a gradient. `--ui-player1/2` keep the HUD's gold and cyan for telling players apart.
  The HUDs (`.hud`, `.hud2`) pin their old colours, so play looks the same.
- **Layouts:** the item screen is the original's. A pane holds the picture (loadout, simulator or
  cube portrait) over readout wells (credits, power with arrows, upgrade cost). A second pane holds
  the menu's title and list, with prices on the right. The message bar runs along the bottom.
  Options lays its sections out in columns on wide screens (settings | keys | player 2's keys and
  the gamepad check). High Scores puts the episode pager beside the title. On phones the panes fill
  the window with the message bar at the foot (the mockup's phone renders).
- **Backdrop** (`src/ui/backdrop.ts`): the blue hangar is retired over the planet. Every mood draws
  the title's painted planet (`titlePlanet.ts`): "title" as before; "space" (every other menu,
  including the screens opened over the title) dims it with the mockup's scrim in its composite pass
  and hides the flying Talons; "hangar" (the item screen, episode-end cards) adds the player's ship,
  turning, lit warm, in the freeSlot gap beside the panes (D55). Where no gap takes it (phones) the
  ship isn't drawn rather than showing behind the panes. The planet keeps one clock across moods, so
  going between the title and a menu only dims or brightens it (it starts over, from 0 on the title
  or at 30 s in a menu, only when a screen comes up after a level). With reduced motion the planet
  is one still frame, the ship holds a three-quarter view, and the dimming doesn't fade. The older 3D
  planet and starfield remain only as the stand-in if the planet's shader can't run. The CSS stand-in
  without WebGL is the title's planet under the same scrim.
- No new fonts or CDNs. The title is pixel-identical in a reduced-motion capture, and the HUD in a
  `?debug=play` capture (only the debug timing line differs).

**Not converted:** pictures and text colours that are the game's own (story pictures and their
palette-tinted text, the cube portraits, item and planet sprites). The power well shows the upgrade
cost; the downgrade refund is only in the left arrow's tooltip and label.

**Review:** captures (desktop 1920x1080, phone 430x932) and the contact sheet are in
`tyrian-scratch/ui-copper/impl/`. The script is `capture-impl.mjs` (scenarios menus, shop, flow,
extras, two).

## D86 — Level 1's ground bunkers and rock outcrop stand on the HD ground, not on a pad of pixel cells

2026-11-03

**Decision:** The dome works (`assembly-newsh2-115`: newsh2-77/79/115/117), the carapace bunker
(`assembly-newsh2-119`: newsh2-81/83/119/121) and the rock outcrop (`assembly-newshe-39`: newshe-1/3/5/39/41/43)
no longer export the sprite's dirt. It was a floor of 2x2-pixel cells in flat palette colours (the
outcrop's and the dome works') or a 1-px relief grid (the bunker's), which at 4K read as a blocky brown
rectangle round each machine, and as a pixel square under the clouds. The HD ground (D57-D60) now shows
round them, and their real shadows fall on it. The dirt is still built for the AO bake, as an occluder
only, so the machines' feet still darken where they meet the ground; then it is deleted. Every machine
part, palette material, frame, piece and pivot is as it was.

The dirt also had a job: the level puts both bunkers on the tiles of their own wrecks (the
`tyrbld-bunker-ring` and `-hull` ground structures, D34/D47, shapesz 320/321/330/331 and 322/323/332/333,
six and three copies), and the rock outcrop on the `tyrbld-wreck` crater (340-342/350-352, ticks
~1320-2100), which the original's opaque sprites hide until the enemy dies. Without it the
wreck's model and its HD painting showed round and under the live machine (the bunker floats at the
enemy height over the ground). So:

- **Covered structures** (`src/render/remaster/opaqueCover.ts`, `DrawListRenderer`): a ground (layer 0)
  structure is placed after the frame's draws are known, and left out when the part of its pattern
  inside the playfield lies under opaque pixels of ground enemies' sprites drawn as models (sampled
  every 4 px, 3 px in from its edges, a thinner seen sliver down its middle; translucent "blend" draws
  don't count). This is the original's rule (an opaque sprite hides the tiles under it), so the wreck
  appears the frame its bunker dies. Layer 1-2 structures are placed as before.
  - *Only the playfield part:* the tiles scroll in a row ahead of the screen, but the sim draws an
    enemy's sprites only near it (`JE_drawEnemy`: a 2x2 enemy's top half once `ey > -13`, its bottom
    half once `ey > -26`). Testing the whole pattern, the rock outcrop's crater (the outcrop's two rows
    enter 35 ticks apart) failed the test and showed round the rocks from tick 1318 to 1352, as it
    scrolled in. Outside the playfield nothing is seen (`View` masks it), and a pattern wholly outside
    it is placed as without enemies.
  - *Only ground enemies* (`Pass.GroundEnemies`, `JE_drawEnemy(50/100)`): they stand on the ground's
    structures. Aircraft and the ship fly over them at their own height, and their models don't erase
    the ground; counting them made the trees and boulders (112, 210-233) vanish under passing aircraft
    (level 1 ticks ~2630-5920, HOLES throughout).
- **Covered tiles**: a ground cell of a ground structure's tile (`WRECK_TILES`, from the tile models)
  is also drawn after the frame's draws, and when its own 24x28 cell lies under opaque modelled enemy
  pixels it draws without the wreck: in the HD terrain look from a "covered" painting, in the other
  looks (Terrain: Original, `bg=original`) as its pixels with every non-dirt pixel taking its nearest
  dirt pixel's index (`paintOutWreck`, TYRIAN's dirt ramp 16-21), which reads as the sprite's dirt did.
  The crater is scorched dirt drawn in the dirt colours, so painting out leaves its outline; in the
  pixel looks its covered cells draw as the plain ground tile round it (shapesz 100, `COVERED_STAND_IN`).
  **The HD look never falls back to pixels:** a covered cell with no covered painting (a tree or boulder
  a ground enemy stands on) keeps its normal HD tile, as on main.
  The covered painting is a new optional manifest key per layer, `"covered": { "<tile>": rect }`
  (`terrainArt.ts`, `TerrainTileset.coveredTile`), here in its own atlas `0-covered.webp` (14 tiles, 66 KB).
  `tools/terrain_covered.py` makes it, one Gemini request per set: `sheet bunkers` puts both bunker
  patterns with one ring of their real map neighbours from the HD atlas on a 16:9 sheet, `sheet wreck`
  the crater's 3x2 on a 1:1 sheet; Gemini painted the wrecks out to dirt; `cut` registers each answer
  (NCC 0.986/0.988/0.984 away from the wrecks), takes the painting only over the wreck's pixels (from
  the original tiles, grown 12 texels, feathered; the crater's whole 3x2 area, as it fills it), pulls
  its low frequencies to the HD tiles round it, and keeps the HD tile elsewhere, so the tiles' edges and
  seams are unchanged.
  `terrain_hd.py cut` keeps the manifest's `covered` entries; rerun `terrain_covered.py cut` after it.

**Options considered:**
- *Drop the dirt, hide the covered wreck and paint its tiles out (chosen):* the HD ground is continuous
  round the machines, the wreck still appears on the kill, and the rule is the original's.
- *Keep a pad, smoothed (a dirt-colour gradient, or the sprite's dirt upscaled):* still a rectangle
  that doesn't match the painted HD ground round it.
- *Only drop the dirt:* the wreck's brass ring, grey hull and ribbed pipes showed beside and under the
  bunkers (captured at ticks 250, 750, 1000).
- *A contact-shadow decal:* not needed; the real shadow and the baked AO seat the machines, and a
  translucent decal would need its own palette and fade handling.

**Checked:** `?debug=play&seed=1&skip=T&freezeAt=T+2&armor=99`, T = 250, 750, 1000, 1400, 1500, 1800,
2000, 4521 at 3840x2160 before and after, and 750 and 1400 (the outcrop) with `&terrain=original` and
`&bg=original`; the destroyed bunker at tick 250 shows its wreck, and at 1400/2000 the outcrop stands on
continuous ground in every look with no wreck showing (its structure is left out). A whole-level scan
(ticks 2-7600, every 3rd frame, the renderer's covered ground cells) finds covered cells only of the 14
painted wreck tiles and of trees/boulders (which keep their HD tile); 4521 (a covered tree) is pixel-identical to main. Draw calls drop (457 → 373,
377 → 311, 391 → 325, 305 → 180 at those ticks) and the frame cpu time is no higher. The 14 GLBs are
3.83 MB → 3.66 MB; with the covered atlas the level downloads ~135 KB less. Tests:
`tests/render/opaqueCover.test.ts` (cover, `paintOutWreck`, every wreck pattern's tile has a covered
painting) and a covered-tile case in `terrainArt.test.ts`.
**Fix round (review):** the crater (`tyrbld-wreck`) showed round the outcrop for ticks 1318-1352 as it
scrolled in (the whole-pattern test; see *Only the playfield part* above). A frame-by-frame probe
(stepping `tyrianHarness`, reading `groundStructures` and `cover.covered()`) over ticks 1301-1370 now
finds the crater and its six ground cells covered on every tick the outcrop is on screen, and a scan of
ticks 0-2300, every tick, finds no bunker or crater structure placed while a live ground enemy overlaps
it (the only overlaps are aircraft over real wrecks); `episode=3&main=17` (TYRIAN X, map Z) likewise.
The damaged outcrop frames (D81) drop their dirt plate as well, and the covered paintings were
recomposed (`terrain_covered.py cut`) against D79's repainted atlas.
Fallback: revert the three scripts and GLBs and the renderer change (`covered` in the manifest is then
unused and harmless).

## D87 — Damaged frames are drawn with the intact model, damaged by the difference between the two sprite frames

2026-11-03

**Problem:** when an enemy is hit hard enough the game swaps it to a damaged frame: burns, holes,
shot-away plates, wrecks. The models covered the intact frames only, so those frames fell back to
the extruded sprite beside the HD models (`KNOWN_DAMAGE_SWAPS`, D54). The game uses 178 such frames
(about 290 counted per episode); modelling each one doesn't scale. Proposal and comparison: PR #104,
`docs/agents/DAMAGE-FRAMES.md`. The user picked the hybrid (D).

**Decision:**
- **A, for every damaged frame by default** (`src/render/damage/`).
  - **Routing.** `Sprite2Router` sends a damaged frame without a model of its own to the enemy's
    intact model, at the intact frame whose pixels it matches best. The level's damaged frames come
    from the enemy data (`levelDamageFrames`: `dgr`, `dani` as `game.ts` uses them). The renderer and
    `modelSwap.test.ts` share this routing.
  - **Textures.** The model's shaders get three tiny textures of the difference between the two
    frames, built from the sheet's pixels and the live palette the first time the frame is drawn.
    They are projected straight down onto the model:
    - pixels gone are cut away, with a charred, glowing rim;
    - pixels changed are tinted by damaged ÷ intact colour, or replaced outright where no multiplier
      reaches (a new hue);
    - pixels that got darker get scorch;
    - pixels that turned hot glow.
  - **Tilted and Steep.** Paint and scorch fade to a third on faces that don't look up, so the
    projection doesn't streak down the sides. While anything is cut, the materials are two-sided and
    draw a charred inside, so a cut reads as a burnt-through wall.
  - **Outline.** OutlineEffect is forked (`src/render/outlineEffect.js`) so the ink outline is cut the
    same way and follows the cut silhouette.
  - **Shadows.** A depth material with the same cut (`customDepthMaterial`), so cut-away parts cast no
    shadow.
  - Blank damaged frames (destroyed pieces) draw nothing, as before.
- **C, a model of its own, only where A fails review:** the level-1 boss's shoulder wrecks, frames 240
  and 244 (`enemies/newsh4-88-d`, `newsh4-92-d` from `assembly-newsh4-124-damaged.py`, 0.83 MB).
  Their damage replaces most of the piece with debris (23-30% gone, 47% repainted), and A drew them as
  the intact shoulder, burning. A damaged frame with its own `spriteModels` entry always uses it.
- **B (generic noise damage, smoke) dropped.**
- `KNOWN_DAMAGE_SWAPS` is gone. `modelSwap.test.ts` now requires every damaged frame of level 1 to be
  drawn by a model. `tools/inventory.mjs` counts a damaged frame as covered when its unit has an
  intact model.
- Debug: `?damage=off` draws damaged frames as before; `?debug=play&hurt=1` damages every enemy at
  its next hit.

**Census correction.** The proposal said 2% of damaged frames grow a new shape outside the intact
outline. That came from pairing frames across a multi-piece unit. Paired with each enemy's own intact
frames, none adds more than 18% outside its outline (the boss's 240 and 244: 1% and 3%). So the C rule
is "fails review", not a pixel threshold. By kind:

| Kind | Frames |
|---|---|
| Scorch and holes | 93 |
| Repainted | 38 |
| Shot away | 33 |
| Same picture | 9 |
| Blank | 5 |

**Options considered (PR #104):**
- *C, a model per frame:* the most faithful, with crater depth and debris. The dome turret took one
  agent 16 min; the boss pieces are a 750-line script and 36 min of Blender per build; 2.5 MB for the
  boss alone. Kept only for the two wrecks.
- *B, generic damage levels:* cheap, but the damage lands in the wrong places and doesn't read as the
  original's frame.
- *Leave the sprites (D54):* a pixel-art patch on an HD model.

**Review:** before/after sheets (`?damage=off` vs default) in `tyrian-scratch/damage-approach/prod/sheets/`:
- the boss at ticks 6835 (`&hurt=1`), 7400 and 7950;
- SAVARA's damaged cruiser (`main=29`, tick 2660);
- the dome turret (`main=21`, tick 3470);

each in Overhead, Tilted and Steep. Frame times, headless Chrome, 1920x1080, Tilted, three runs each, `?damage=off` (as main) vs default. All
runs were at 60 fps.

| Scene | Renderer CPU per frame, off → on | Draw calls, off → on |
|---|---|---|
| Boss, tick 7950 (13 damaged pieces) | 8.5-10.1 → 11.1-12.2 ms | 346 → 448 |
| SAVARA cruiser, tick 2660 | 5.2-5.5 → 8.1-8.5 ms | 389 → 569 |

The cost is drawing the damaged pieces as models instead of instanced sprites, plus their outline
and shadow passes, as any model costs.

## D88 — Level 1's enemies, the boss and five player ships refitted to the inner edge (D74)

2026-11-03

**Decision:** D74's refit is applied to the models that passed its strict re-review: their top
views now end on the inner edge of the sprite's ink border, and the game's ink outline draws the
border. Each passed the acceptance gate, rule IoU >= 0.95 against the inner mask on every frame
(`tools/sprite_mask.py --measure`, `iou_rule_grid`), with real geometry changes (plans, plates,
nozzles, pods moved in), not mask warping.
- **Single-sprite enemies** (fixes on Sonnet 5.5, two second-round fixes escalated to Opus:
  newsh2-267 and newshp-13; re-reviews on Sonnet): newsh2-127 0.9977, newsh2-159 0.9571,
  newsh2-171 0.963, newsh2-191 0.9603, newsh2-229 0.9724, newsh2-267 0.9927, newsh2-269 0.9818,
  newsh2-271 0.9819, newsh2-49 0.9557, newsh2-51 0.9666, newshp-13 0.96 (all frames).
- **From the bench** (Opus's versions, PLAYBOOK "Bench results"): newsh2-89 0.9904;
  assembly-newsh2-87 0.9888 for the whole assembly (pieces newsh2-85 0.9933, newsh2-87 0.9536).
- **Assemblies** (fixes on Opus, re-reviews on Sonnet): assembly-newsh2-3 1.0, assembly-newsh2-9
  0.9954, assembly-newsh2-123 0.9944, assembly-newsh4-81 0.9583 (its shared `lib_b065.py`, also
  assembly-newsh4-123's), the boss assembly-newsh4-124 0.9943 (22 pieces rebuilt),
  assembly-newsh4-195 0.9624, assembly-newsh4-231 0.9568.
- **Player ships** (fixes on Opus, re-reviews on Sonnet): the USP Talon 0.9535 (rolled and shifted
  as the game banks it, on every banking frame: chined pods, the ship shortened to the inner edge's
  length), Dragonwing 0.9567, Nort Ship 0.9963, Silver Ship 0.9613, Supercarrot 0.9699.
- **Not refitted (failed the re-review, left as they were):** Gencore Phoenix 0.6858, Microcorp
  Stalker 0.849, U-Ship 0.4393. Their scripts, models and entries are main's; they are being
  investigated separately.
- **Shared code:** `usp_talon.py`'s changes are to the Talon's own plan, sections and parts (the
  helpers other scripts import, `Part`, `plate`, `hull`, `pchip`, `fillet`, `bake_maps`,
  `cull_hidden`, `POD_UNIT`, ..., are unchanged), so the other ships and enemies built on it build as
  before. `lib_b065.py` is used only by assembly-newsh4-81 and -123, both refitted.
- **The boss's wrecks (D87)** are rebuilt from the refitted boss: `assembly-newsh4-124-damaged.py`
  imports the boss's build, so newsh4-88-d and newsh4-92-d follow its new geometry. (It now imports
  `mmpx2x` from `lib_rock_hd`, where D84 moved it.)

**Review:** the comparison sheets and measurements are in `tyrian-scratch/inner-refit/<model>/`.
Fallback: revert the scripts and GLBs listed above.

## D89 — `shapesz` HD terrain over all 32 levels: the batch painted, the clouds re-cut over every level, empty tiles held black in the seam solve

2026-11-04

**Decision:** The `shapesz` batch D83 prepared is painted and cut into the tileset's atlas
(`public/art/terrain/shapesz/`): every level that uses the tileset now draws its ground, clouds and layer-2
terrain from HD paintings.
- **Merged, level 1 kept.** The 66 ground tiles and their `covered` paintings (D86) are kept byte for byte
  (`0.webp`, `0-covered.webp` unchanged, rects unchanged); 200 new ground tiles in `0-2.webp` (1.3 MB);
  layer 2's 73 terrain tiles in `2.webp` (39 painted, 34 reusing a ground painting, D83); layer 1 in a
  new `1.webp`.
- **Clouds re-cut over all the levels** (the user's call): D83 found TYRIAN's clouds, solved on TYRIAN's
  map only, seamed on HOLES and ASSASSIN (1.11, 1.13). `sheets --recut 1:40,...,1:64` gave two cloud
  context sheets (the 15 cloud tiles and the 518 blue panel fill of 1-18 ALE), painted again and cut
  with `cut --recut` over all 32 levels. Level 1's clouds change slightly (captures below).
- **Gemini:** 45 requests in one session, no usage warning: 33 primary sheets (the batch's 32, with the
  fill's own sheet folded into the two cloud sheets) and 12 retries. Two first sends vanished without an
  answer while a page script polled for 35 s at a time; sending and then waiting with plain waits worked.
  Every answer was registered against its sheet as it landed (NCC, blockiness, pixel period per tile).
  Retries, each a second candidate (`<sheet>-r2` in the manifest, so the cutter chooses per tile):
  the 518 fill (painted as large panels, NCC 0.04 → 0.91), region-l0-24 (pods turned into a silo,
  0.56 → 0.91), 07 (pixel copy, blockiness 2.48 → 1.33, sent as D79's MMPX-and-blur sheet), 12 (black
  space filled with bricks, 0.70 → 0.99), 10 (0.63 → 0.90), the bubbles 01, 17, 23, 09 (bubbles moved,
  rock invented: 0.68-0.81 → 0.87-0.99), 26 (raised ridges painted as pipes), 16 (a sunken floor painted
  as grilles) and 08 (rock added in the black).
- **Prompts name the material.** SEND.md's labels come from the palette groups, and several were wrong:
  grey woven-brick floors were "grey cratered asteroid rock", purple plating "dark blue-grey metal deck",
  grass meadows "dense forest canopy". Gemini repaints what it is told: 24 grew a building, 12 and 10
  dirt paths. 19 primary sheets went with the material named from the sheet (purple plating, grey brick,
  grass meadow, brown ridges); the prompts sent are in `tyrian-scratch/shapesz-hd/work/sheets/sent/`.
- **Seams: the empty tiles are held, and the cut is edge-aware.** In game the first cut showed (a) a
  green band under BONUS's purple plates (3-5): tile 571's bottom strip was solved against HARVEST's
  grass below it, as the black below it on BONUS is an *empty* tile (one colour, no painting, D83) that
  took no part in the solve; and (b) grey tile-shaped boxes and smears in the black round the plates and
  the bubbles (3-5, 3-7, 1-4), strips pulled towards their painted neighbours. `cut` now holds the
  ground's empty tiles as fixed neighbours at their own colour (`--no-empty-edges` to turn it off), and
  this atlas is cut with `--edge-aware` (D83's option: strips are not tied across a real edge of the
  original). The two together removed the green band and the boxes and most of the smears (captures
  `*-variants.jpg`: original, plain, edge-aware, empty-held, both). The empty tiles only matter on
  levels that have them; level 1 has none.

**Result** (`check`, every edge of all 32 maps; step across tile edges over step inside tiles):
- Ground: edges with a new tile 0.609 (0.541 where the original is continuous), kept-only 0.477, bands
  0.60. Per level (all / continuous): 1-9 0.456 (as before), most levels 0.44-0.66; the worst 3-5 BONUS
  2.83 / 1.39, 3-7 STARGATE 1.38 / 1.04, 1-4 BUBBLES 1.31 / 0.86, 1-10 and 2-3 BONUS 0.95 / 0.94. The
  edge-aware cut keeps the hard step where plating or a bubble meets black, which the measure counts as
  a seam: the plain cut measured 3-5 1.07 / 1.00, 3-7 1.17 / 1.08, 1-4 0.96 / 0.87, but showed (a)
  and (b) in game. Faint smears beside some bubble clusters remain.
- Clouds (layer 1): 0.706 (continuous 0.673); 1-11 0.84, 1-16 0.82, 4-16 0.86 (were 1.11, 1.13 and
  unmeasured), 1-9 0.70 (was 0.82), 1-18 (the fill) 0.57.
- Layer 2: 0.533; 1-11 0.60, 1-16 0.69, 4-1 0.47.
- 46 ground tiles deblocked (D60); remaining blockiness above 2: 116, 430, 431, 545, 547, 549, 568,
  584, 585 (pixel-sized brick and plating patterns; 549 comes from 16-r2, a smoothed copy).

**Checked** in game (`?debug=play&episode=E&main=N&seed=1&skip=T&freezeAt=T`, against `&terrain=original`):
1-9 TYRIAN t300, t1500, t2000 (ground unchanged: mean pixel difference 0.37 at t2000 against the atlas
before; the clouds re-cut), 1-4 BUBBLES t1200, 3-7 STARGATE t1500, 3-5 BONUS t1500, 1-11 HOLES t1200 (clouds
and layer-2 rock), 1-18 ALE t400 (the blue fill), 1-16 ASSASSIN t1500, 4-1 HARVEST t1500 (grass, trees),
1-5 DELIANI t1500. Captures in `tyrian-scratch/shapesz-hd/captures/` (`*-pair.jpg` original | HD,
`*-variants.jpg`, `1-9-t*-before-after.jpg`). No seams, gaps or misplaced tiles beyond the limits above.
Typecheck and `terrainArt`, `terrainHd` and `inventory` tests pass. `terrain_hd_test.py` now merges into
level 1's part of the committed atlas (it covers every level now, so there would be nothing new to cut).

**Options considered:**
- *Keep TYRIAN's clouds and add variants (D57) for the worst pairs:* level 1 unchanged, but variants
  for 42 over 52 and the like on four levels; the user chose the re-cut.
- *The plain cut (D83's defaults):* the best seam measure on the worst levels, but the green band and
  grey boxes in game.
- *Variants for tiles that meet black on one map and grass on another (571):* exact, but the tool makes
  no variants yet; holding the empty tiles fixes it for every such pair at once.
- *More retries (16's sunken floor, the remaining bubble smears):* the session had used 45 of an estimated
  ~42; the cutter already prefers the better candidate per tile.

**Review:** the sheets, answers (`results-raw/`), per-answer registration (`review/*.txt`, side-by-sides),
contact sheets (`check/`) and `cut-report.json` are in `tyrian-scratch/shapesz-hd/work/` (not in git, D3).
Recut from the cache: `terrain_hd.py --tileset shapesz --work W cut --cache W/cands.pkl --edge-aware --recut
1:40,...,1:64` reproduces this atlas byte for byte.

## D90 — The Talon's outline shell bridges the refitted hull; the player ship wears with its armour

2026-11-04

**Problem:** after D88 the USP Talon showed black cracks across its pods and body.
- **Where:** in the item screen's hangar, at full armour, and in flight. The user read it as the
  runtime damage (D87).
- **Not the cause:** the damage code. `?damage=off` showed the same cracks, and the menus' backdrop
  doesn't use it at all.
- **Not the geometry:** in `?viewer=usp_talon` the cracks went away with Outline off.
- **The cause: the outline shell (D51).** It is a voxel remesh at 0.012, smoothed and decimated, and
  on the refitted hull it followed the new chines and seams into the creases. Its back faces there
  drew ink across the surface. The pre-D88 Talon, with rounder pods, didn't do this.

**Decision:**
- **Shell.** `common.outline_shell` takes `inside`: after smoothing, every shell vertex outside the
  model goes back onto it, that far inside (Shrinkwrap, inside mode). The Talon's shell is now made
  from 0.03 voxels (it bridges the seams), held 0.004 inside; it was 0.012. Nothing else is
  rebuilt; the default is unchanged.
  - Tried first, and the cracks stayed: a 1500- or 4000-face shell held 0.004-0.035 inside, and an
    undecimated one.
  - Of the other D88 ships, the Silver Ship shows a few faint lines in the viewer (not fixed here).
    Dragonwing, Nort Ship and Supercarrot look clean.
  - Later the same day: the Silver Ship takes the Talon's shell (0.03 voxels, held 0.004 inside),
    which removes its ink wedges across the hull by the vents. Dragonwing, Nort Ship, Supercarrot and
    D93's U-Ship, Gencore Phoenix and Microcorp Stalker, checked in `?viewer=` with Outline on and
    off, show ink only on their silhouettes and where one part overlaps another, so they are left
    as they are.
- **The player ship's wear (the user's rule).** The player ship has no damaged frames, so its look
  follows its current armour, both ways, never latched (`src/render/damage/shipDamage.ts`):
  - **Reference:** the ship's maximum, `initial_armor`, not the level-start armour (D75: the C caps
    that at 28).
  - **Ratio:** `ratio = armor / initial_armor`, clamped to [0, 1]. Armour above the reference
    (pickups, the armour ship's crates) is full. A zero or missing reference is healthy.
  - **Levels:**
    - clean at 50% and above;
    - light scorch below 50% (`LIGHT`);
    - heavier scorch with embers below 25% (`HEAVY`).
  - **Going down** happens at once. **Going back up** needs `HYSTERESIS` = 3% of the maximum above
    the threshold, so it doesn't flicker. A pickup from under 25% to over 53% goes straight to clean.
  - **Fade:** the look eases at `FADE_PER_S` = 0.8 coverage per second, kept within [0, 1].
  - **Look:** scorch is a fixed blotch pattern projected top-down like D87's damage. `COVER`
    0.28 / 0.55 of the ship, `HOT` embers in the heavy level. Paint only, never a cut.
  - The user can tune all of these: they are the constants at the top of `shipDamage.ts`.
  - **Two players:** each ship follows its own armour and reference.
- **Never in menus.** A level's tick puts each player's armour in the draw list (`DrawList.ships`,
  `sim/game.ts`). The renderer draws a ship worn only from that. The item screen's preview
  (`weaponSim`), the menus' backdrop (title flights, hangar) and the model viewer never carry it,
  so they show the ship clean. The first draw list with armour snaps to it; after that the look
  eases.
- **Debug:** `?debug=play&armor=N@T,N@T` holds N from tick T on, e.g. `1@0,4@330,8@420` for a
  pickup.

**Review:** `tests/render/shipDamage.test.ts`:
- armour at 150%, exactly at the thresholds, at 0, and a zero or missing reference;
- down through the thresholds and back up;
- hovering at a threshold;
- the pickup jump;
- fade bounds;
- two players;
- clean ships drawn without armour;
- no cut in ship mode.

Sheets in `tyrian-scratch/damage-ship-fix/ship-sheet.png`:
- the hangar, before and after;
- in flight at full armour, before and after;
- 40% and 10% armour;
- recovery 10% → 40% → 80%;
- the title flights.

## D91 — Gameplay performance: measured, then the hitches moved out of play

2026-11-04

**Problem:** the user found play "struggling a bit". Measured first (`?debug=play&solid=1`, the production
build, headless Chrome on the real GPU, 1512x900 at DPR 2 = 3024x1800, 60 Hz; a WebGL wrapper times
shader compiles and texture uploads per frame; scripts in `tyrian-scratch/perf-1/`):
- **Steady play is not the problem.** Main thread ~3 ms a frame (sim 0.2, draw list 0.2, three's
  submit with outline and shadows 2.3), GPU 5-9 ms; level 1, the boss and HOLES held 60 fps with p95
  16.7-17.5 ms. The outline pass adds ~15 draw calls (models outline only their shells), not a second
  scene; the shadow pass ~115.
- **The stutter is first-use work during play:** a texture's first draw uploads it (the flat art's
  atlases 18-30 ms: newsh6's 832x4096 at the first explosion, tyrian.shp#10's 1024x2048 at its first
  shot), a new enemy model's textures (20-45 ms for a batch of 24), and a material variant's first
  draw compiles its shaders (20-35 ms each time mid-level; 130-730 ms over the first two frames of a
  level).

**Decision (one fix per PR, each measured):**
1. **Flat art atlases at preload.** `preloadLevelModels` uploads the sprite art's atlases
   (`uploadSpriteArt`) after the HD terrain's. The same atlases serve every level, so only the first
   level's preload pays (~250 ms more of preload). The first-explosion and first-shot hitches are gone:
   HOLES 5 → 3 frames over 33 ms (the 3 left are the level's first two frames), the boss 5 → 3.
2. **Shaders and textures warmed at preload, the rest as they load.** After the uploads,
   `preloadLevelModels` awaits `View.warmUp()`:
   - `DrawListRenderer.beginWarmUp` puts in front of the camera a clone of every loaded model (the
     clone stays in its pool for play), a quad of every instanced material variant, each HD terrain
     material kind of the level's tileset and a batch per sprite art atlas;
   - for each way a clone is drawn (opaque, then translucent: the invulnerable ship) the main and
     outline passes compile in parallel (`renderer.compileAsync`, and `compileAsync` added to the
     forked OutlineEffect), every texture is uploaded (`initTexture`), and one draw into a single
     pixel (scissor) builds the shadow pass's programs;
   - clones are patched for damage when they're made, not at their first damaged frame (`uDmgOn` 0
     draws exactly as unpatched), so the warm-up covers that program;
   - models and structures that finish loading during play (D54 waits only for the first ~30 s of a
     level) are compiled in parallel when they arrive (`View.warmLate`) and their textures uploaded
     one a frame before they are due;
   - production skips three's shader error checks (`debug.checkShaderErrors` off outside dev),
     which query every program's logs at its first use.
3. **Model textures capped at 1024** (`MAX_MODEL_TEXTURE`, `models.ts`). Fifteen models carry
   2048 or 4096 maps (TYRIAN's bridge, fortress and base buildings, seven of the boss's arm pieces):
   one 2048 upload stalls ~50 ms, a 4096 ~200 ms. They are scaled down in a worker
   (`textureResize.worker.ts`; createImageBitmap with a resize is synchronous on its thread, 400 ms of
   main thread over a level start when done there). A model fills a few hundred pixels, so 1024
   still gives a texel per pixel; the in-game captures and the model gallery match main to within
   1-2 levels. The island rock's palette-data textures (D84) are never resampled.
4. **The outline pass's bookkeeping.** Its per-frame maps were plain objects whose keys (every
   material and object ever outlined) piled up and were listed with `Object.keys` every frame; they
   are Maps, cleared. It swaps materials on visible objects only (`traverseVisible`): the warm-up's
   hidden clones made the full traverse cost ~1.4 ms a frame.

Measured (60 Hz, 3024x1800; load average 5-7, other agents' GPU work shows as frames with a slow GPU
and little JS, counted apart): frames over 33 ms caused by the main thread, main → this change;
max rAF JS time; shader programs linked during play.

| Scene | > 33 ms (main thread) | max frame JS | programs linked in play |
|---|---|---|---|
| Level 1, ticks 0-2000 | 8 (2) → 3 (1) | 139 → 135 ms (first frame) | 25 → 4 |
| Boss, ticks 6650-7400 | 5 (4) → 3 (1) | 727 → 47 ms | 23 → 1 |
| HOLES, ticks 0-2000 | 5 (4) → 1 (1) | 173 → 75 ms (first frame) | 28 → 0 |

Level preload is longer by the warm-up (~0.3-0.6 s, compiles in parallel; once per session for the
shared materials).

5. **Dynamic resolution, Options → Graphics → Resolution: Auto (default) or Full**
   (`src/render/resolutionScaler.ts`, `resolutionStyle`, `?resolution=auto|full`). Every 60 frames: if
   a quarter came later than 60 fps allows (> 20.8 ms) while the view's own main-thread work stayed
   under 10 ms (so the GPU is the late part), the render scale drops a step (x0.8, down to half the
   pixel ratio); after 5 s with no late frames it steps back up, waiting twice as long each time a
   raise is undone at once. At 60 fps, and on a 120 Hz screen alternating 8 and 17 ms frames, it never
   moves, so the picture is the full one whenever the GPU keeps up; a level's end restores full
   resolution for the menus. Measured: the boss at 4800x2700 (GPU-bound) 33 → 52 fps, frames over
   33 ms 208 → 45 (scale settled at 0.64); at 3024x1800 HOLES stayed at full scale, and the boss
   dipped to 0.8 for 23% of its frames while other agents loaded the GPU (load 12), back to 1 after.

6. **The upscaled ground only where the HD terrain has no painting.** Every tick the remastered
   ground atlas (D34) upscaled (MMPX) and looked up every visible ground cell, though with HD terrain
   (D57, the default) the painting draws nearly all of them: `prepare` now skips cells the HD art
   covers (they still give their neighbours context); a switch to the original terrain look
   prepares them all again. `setDrawList` 0.7-0.9 → 0.1 ms a tick, a level's first tick 24-50 →
   1-2 ms, ~17% less garbage (HOLES 604 → 499 MB freed over 1000 ticks). Captures identical.

7. **A translucent model draws in one pass.** three.js draws a transparent two-sided material twice
   (back faces, then front) and flips its `side` with `needsUpdate` for each, so every material of a
   translucent model recomputed its shader program twice a frame: the invulnerable Talon (every
   level's first 100 ticks, pickups, the harness's bot) cost ~0.35 ms a frame in program lookups
   and doubled the garbage (23 → 13 MB/s). Blended clones set `forceSinglePass`; the depth prepass
   (D51) already hides the far faces, so the picture matches (29 edge pixels within 31 levels at
   tick 400).

8. **Hidden clones skip three's matrix update.** A level keeps a clone of every model it has
   loaded (3,100 objects in the boss fight, 250 visible), and `scene.updateMatrixWorld` walked
   them all every render, recomposing every part's matrix: the largest JS item of a frame in a
   CPU profile. Hidden clones set `matrixWorldAutoUpdate` false; a clone's parts, which never move
   (only the root is placed), keep fixed local matrices. `updateMatrixWorld` 0.21 → 0.15 ms
   (median of three runs each, boss tick 7000); captures identical.

9. **No key strings per tile per frame.** The remastered background's per-draw lookups built
   strings for every tile every frame (structure ids, pattern verdicts, the HD terrain's material
   key, the tileset prefix): numeric keys and per-layer maps instead. HOLES allocates 15.8 → 12.5
   MB/s (the three functions 64 → 16 MB over 15 s); captures identical.

**The whole run, main before D91 → after items 1-8** (same machine minutes, load average 4-5;
`?debug=play&solid=1`, 3024x1800, 60 Hz; frame interval ms; "JS" = frames over 33 ms whose own
JS took over 25 ms; max JS = the longest frame's JS; programs linked during play):

| Scene | mean | p95 | p99 | max | > 33 ms (JS) | max JS | programs |
|---|---|---|---|---|---|---|---|
| Level 1, ticks 0-2000 | 16.8 → 16.7 | 18.3 → 18.1 | 18.7 → 18.6 | 380 → 69 | 6 (3) → 5 (0) | 138 → 25 | 25 → 4 |
| Boss, ticks 6650-7400 | 17.3 → 16.9 | 17.0 → 17.0 | 32.1 → 17.6 | 318 → 259* | 12 (2) → 2 (0) | 315 → 14 | 23 → 1 |
| HOLES, ticks 0-2000 | 16.8 → 16.7 | 16.8 → 17.9 | 17.6 → 18.5 | 368 → 25 | 4 (3) → 0 (0) | 176 → 12 | 28 → 0 |

\* the harness's first frame after fast-forwarding 6650 ticks. A second round of the same runs was
spoiled by other agents' load (load average 74-220) and is not counted. What's left in level 1 is
its first second (models that load in the background at a level's start arrive, D54), which plays
under the level's fade-in, and GPU time taken by other processes.

**Not done (estimates):**
- *Instancing enemy models* (one clone per enemy, a draw per part, plus outline shell and shadow):
  250-500 draw calls a frame, ~2-3 ms of three's submit; per-instance damage, flash and blend
  make it a large change (days). Not needed for 60 fps on this machine.
- *Shadow pass*: ~25% of the GPU frame in busy scenes (1-3 ms at 3024x1800). A tighter shadow camera
  or caster culling changes how shadows look; left to a design call.
- *Level start*: wait in preload for every model (or for the ones in flight) instead of the first
  ~30 s of them (D54) to take the background parses out of the first second; costs preload time
  on a cold network.

## D92 — Twenty enemies shared across episodes rebuilt hard-surface; a palette-pulsed ring counts as ink

2026-11-04

**Decision:** The first batch of shared enemies (drawn in more than one episode; MILESTONES.md
"Order of work", step 2) is rebuilt to the D65 standard and D74's inner-edge fit, the way level 1's
were: blueprint, competing designs for the heroes, judge, finisher, strict review, fix rounds (all
on Opus; Sonnet only in the bench below). Top-view rule IoU on the grid (`iou_rule_grid`, inner
mask, every frame):
- **Heroes (assemblies and bosses):** assembly-newsh-caret-123 0.9698 (design B), assembly-newshf-270
  0.9827 (B), assembly-newshf-191 0.9827, assembly-newshf-195 0.9986, assembly-newshf-199 0.9877.
- **Standard:** newsh3-267 0.9887, newshe-195 0.9726, newshe-235 0.9688, newshf-123 0.981,
  newshf-169 1.0, newshf-171 1.0, newshf-230 0.9761, newshf-238 0.9886, newshd-79 1.0, newshd-127
  0.9747, newshd-191 0.9644, newshs-153 0.9955, newshs-171 1.0, newshs-269 0.9651, newshm-115 1.0
  (rule 0.9529).
- newshf-230, newshd-79 and newshs-269 shipped after a fix round. newshm-115 (the blue mine ball)
  took two: the glints, then the sheen. Its sheen is a polished, clear-coated patch at the upper
  left, where the sprite draws its white blob (SHEEN_PATCHES); its glb is the only one with
  KHR_materials_clearcoat (three loads MeshPhysicalMaterial). The last round left the sheen too
  weak, and the one before had too many wet glints. Tuned between them at game scale (MINES, tick
  1640): patch roughness 0.20, coat 0.22, 26 degrees, satin 0.66 elsewhere, metallic 0.35. The
  ball nearer the middle now shows one clear white sheen at the upper left. The one near the
  field's top-left corner still shows only a small glint, because the room's reflection depends on
  the ball's place on screen.

**Palette-pulse rule** (`tools/sprite_mask.py`, OUTLINE-BORDER.md rule 1): a boundary-ring pixel at
a ramp's darkest step counts as ink when the palette pulses it above the luma limit. When another
frame of the same model is the same drawing with the palette shifted (same opaque mask, at least
90% of its pixels one constant index shift away in the same 16-colour ramp: a pulse partner), a ring
pixel above luma 26 is ink if it is ink, in the same ramp, on a pulse partner. newshm-115's ring is
palette 53 (luma 41) on frames 115 and 279 and ink on the darker pulse frames 165/203/241. It is one
border, so the inner edge now holds on all five frames. The rule also changes tyrian10-14/-32/-51,
newsha-199, newshk-115 and newshl-115, and no other frame in reference/models. `--no-pulse` measures
by luma alone. Test: `tests/tools/spriteMask.test.ts`.

**Bench** (PLAYBOOK "Bench results"): Sonnet finishing from an approved design is cheap-ok. On
newsh3-267 its glb was byte-identical to Opus's, and on assembly-newsh-caret-123 it needed minor
integration fixes only, such as uncapped outline shells at the piece seams. Sonnet fix rounds are
opus-needed: on newsh3-267 it painted colour regions face by face from a level field, which left
stair-stepped, blotchy regions.

**Review:** comparison sheets and captures are in `tyrian-scratch/shared-enemies-1/<model>/`.
Fallback: revert the 20 scripts and their GLBs; `--no-pulse` for the old measure.

## D93 — Player ships' banking frames: the level model at a fitted roll and shift, never reshaped for them; their own bars

2026-11-04

**Decision:** A player ship's model is fitted to its level frame only (D74: rule IoU ≥ 0.95). Its
banking frames are that model rolled and moved sideways by the game, and the **pose is fitted per
ship** to its banking sprites, not the model: `bank.roll` (degrees at bank steps 1..max) and, where
it beats bankShift.ts's guess, `bank.shift` (game px per frame) in its spriteModels entry, written by
the script with `common.with_bank_roll`. `tools/bank_roll.py <name> --fit` finds them; it keeps the
old pose (35° × step / max, bankShift.ts) unless another roll is better by more than 0.02 mean IoU,
or another shift by more than 0.01. **Accept:** level frame ≥ 0.95, each half-bank frame ≥ 0.80,
each full-bank frame ≥ 0.70 (`tools/bank_roll.py <name>`). No part, height or offset is added to a
model for its banking frames. The rule for agents: docs/agents/OUTLINE-BORDER.md "Banking frames".

- **Renderer:** `bankRoll` (spriteModels.ts) gives each banking frame's roll from the entry (default
  `DEFAULT_FULL_ROLL` = 35 × n / max, as `MAX_ROLL` did); `Sprite2Route.roll` replaces `bank`, and
  the eased roll in drawListRenderer.ts is unchanged otherwise. An entry's `shift` replaces
  bankShift.ts for that ship (D62); the two-halves Dragonwing still isn't shifted.
- **Ships:** U-Ship roll 40 / 55. Gencore Phoenix 40 / 50, shift −3.5, −1.5, 0, 1.5, 3.5
  (bankShift: −2.5, −1, 0, 1, 3.5). Microcorp Stalker 17.5 / 27.5, shift −0.5, −0.5, 0, 0.5, 2.5
  (bankShift: 1, 0, 0, 0, 1). The other five keep the old pose: the fit found nothing better.
  The three models are the D74 inner-edge refit with its bank-only parts taken out: the Phoenix's
  5 px ventral fins, 4 px strakes and 1 px lift; the Stalker's 3 px endplate fins, forked tip
  prongs and body raised 3 px over the wings (now a 0.45 px tip rail, the body level with the
  wings). The U-Ship had none.

**Why (measured).** The D74 refit asked ≥ 0.95 on every frame, banking frames included, and U-Ship
(0.43-0.55), Phoenix (0.61-0.75) and Stalker (0.83-0.91) failed after two fix rounds each and were
left as they were (D88). This decision refits them.

- *The measurement was right.* An independent harness (Blender top view, k = 10) reproduces the
  fixers' numbers to the digit (U-Ship 0.442 / 0.553 / 1.000 / 0.538 / 0.434). Checked against the
  code: frame base − 4 is ship_banking −2, moving left (mainint.ts L712-715); rotation.z = −bank ×
  35° is +Y × bank × 35° in Blender (glTF +Z is Blender −Y), the ship's top leaning into the turn; the pivot
  is the model origin at the cell's centre; the shift is bankShift.ts's opaque-column centre; the
  frames are the 2x2 composites the game draws (sprite.json, the draw list's index); `?height` is 1.
  In game (`?debug=play&ship=10`, new `&ship=`) the clone reads roll 40.0° and shift −1 on frame 269.
- *The art draws a different roll per ship.* IoU of each banking sprite with the level sprite
  (shifted, no roll) says how far the art moved, and the best rigid roll of the level model says
  how far a roll gets (half-bank frames, full-bank frames):

  | Ship | level sprite vs bank sprite | old pose (17.5 / 35°, bankShift) | fitted pose (this decision) |
  |---|---|---|---|
  | USP Talon | 0.89, 0.88 / 0.79, 0.80 | 0.984, 0.984 / 0.959, 0.965 | same |
  | Silver ship | 0.89, 0.90 / 0.79, 0.81 | 0.982, 0.982 / 0.965, 0.996 | same |
  | Supercarrot | 0.91, 0.93 / 0.88, 0.90 | 0.958, 0.981 / 0.970, 0.981 | same |
  | Dragonwing | 0.93, 0.93 / 0.88, 0.87 | 0.965, 0.989 / 0.957, 0.967 | same |
  | U-Ship | 0.39, 0.38 / 0.30, 0.30 | 0.553, 0.538 / 0.442, 0.434 | 0.873, 0.876 / 0.781, 0.776 |
  | Gencore Phoenix | 0.57, 0.56 / 0.53, 0.59 | 0.620, 0.613 / 0.626, 0.703 | 0.831, 0.838 / 0.849, 0.859 |
  | Microcorp Stalker | 0.83, 0.83 / 0.68, 0.70 | 0.816, 0.818 / 0.585, 0.611 | 0.879, 0.856 / 0.791, 0.779 |

  Level frames: Talon 0.952, Silver 0.989, Supercarrot 1.000, Dragonwing 0.996, Nort 0.996 (no
  banks), U-Ship 1.000, Phoenix 0.996, Stalker 0.974. The five that passed are the refit's models
  (inner-refit worktree). The old pose suits the Talon, whose art is a true roll (0.79 → 0.96 at full
  bank). The U-Ship's arms close from 12 px apart (centre to centre) to 9 at half bank and 6 at full,
  and the Phoenix's 20 px plan becomes one solid wedge 15-17 px wide (inside the ink): both draw about
  40° at half bank, more than twice the old 17.5°. The Stalker's art is hardly a roll at all: its
  banks keep the full 21 px span; its best half-bank roll is 0° and the old 17.5° is within 0.01 of it.
- *bankShift.ts misplaces some redraws.* The opaque columns' centre tracks the Talon, Silver,
  Supercarrot and U-Ship exactly (the fit moves none), but the Stalker's both hard-bank frames sit
  1 px right though its nose leans into the turn, and the Phoenix's are 0.5-1 px short. At the
  fitted roll the fitted shift adds +0.04 to +0.14 to the Stalker's frames and +0.00 to +0.07 to the
  Phoenix's. (The refit's raised Stalker body was mostly making up for that shift.)
- *What is left is hand drawing no rigid pose follows:* the U-Ship's arms drawn touching at full
  bank, the Phoenix's slots between hull and blades filled in, the Stalker's far wing redrawn shorter
  with its tip in place. The art isn't consistent with itself either: each left bank against the
  mirrored right bank scores 0.93 (Phoenix, full) and 0.94-0.95 (Stalker), so no mirror-symmetric
  model matches both sides.

**Options considered:**
- *Fitted pose, model untouched, lower bars on banks (chosen):* one number or two per ship, the
  roll stays a smooth ease (the frames change instantly and often; the roll eases with a 1/12 s time
  constant), nothing to rebuild, and the passing ships stay as they are. The bars sit below the
  fitted worst (0.831 half, 0.776 full), and each of the three fails them at its old pose (U-Ship and
  Phoenix at half bank, 0.54-0.62; the Stalker at full bank, 0.59-0.61).
- *Bank-only geometry (the refit's rounds):* the Phoenix's fins and lift reached 0.68-0.75, the
  Stalker's endplates and prongs 0.83-0.91, and both show as tall plates and keels in the side, front
  and hangar views (D85 shows the ship large and turning).
- *Per-frame models or morph targets:* swapping nodes per frame (`tyrian_frames`) pops, since the
  sprite frame flips at once while the roll eases; morph targets need the same morphs on the
  outline shell and four hand-made poses per ship, to chase art whose left and right banks
  disagree by 5-7%.
- *Roll plus a sideways stretch* (a world-X scale after the roll, exact in the top view, measured
  at bankShift's shift): +0.00 to +0.10 over the best roll alone, the big gains only at ×1.2-1.4
  (Phoenix: 0.91 half, 0.84-0.86 full; U-Ship ×1.4 at 70°: 0.83 full) and none near 0.95: a
  visibly squashed 3D model for a few hundredths.
- *Keep ≥ 0.95 on banking frames:* none of the three can pass without the parts above.

**Found on the way:** the game's perspective camera adds or takes away roll by where the ship is:
it sees a ship at the playfield's side edge about atan(11 / 22.9) ≈ 26° off vertical (overhead
camera), so a ship banking toward the middle looks rolled less and one banking toward the edge more.
That is D6's lift along camera rays, the same for every model; the fit (orthographic) holds for the
middle of the screen, and the in-game captures here are taken there. The play harness gains
`&ship=ID` (item number) to fly any ship.

**Review:** `tyrian-scratch/ship-banking/`: `fail3.png` and `pass.png` (all banking sprites, 10x),
`final/cmp-<ship>.png` (the refit's model at the old pose | this model at the old pose | at the
fitted pose, each frame's sprite beside the diff: green model on inner, red outside, blue missed),
`game/` (in-game crops, old and new pose), `stalker/views.png` (the Stalker main / refit / this,
front, side, 3/4, top). Fallback: delete an entry's `roll`/`shift` for the old pose.

## D94 — Episode 1's remaining pickups drawn from Gemini flat art (D42/D43)

2026-11-04

**Decision:** Every pickup unit episode 1 draws that still showed as an extruded `sprite` or
`basic` unit (inventory.json, kind `pickup`) now has flat art: 80 objects (some 2x2), 266 new atlas
frames in `tyrian.shp#10` (76 -> 226), `tyrian.shp#9` (32 -> 148) and a new `newshp.shp` atlas
(`newshp-shp.webp`, 12 frames; its three objects are the pickup newshp-85 used on 11 levels).
This includes `tyrian.shp#9` 155 and 199 (about 30 levels each).
- **Inputs:** an inventory of those objects in the D43 format (kept in `tyrian-scratch/e1-pickups/`),
  four families (`e1-pickups-10`, `-10-small`, `-9`, `-newshp`) added to `SHEET_GROUPS`: 9 sheets of
  8-12 cells, 9 Gemini requests, no retries and no usage warning. Level palette 5 for all: every
  level's in-level palette is `pcxpal[2]` (tyrian2.ts), so one palette serves episode 1.
- **Cut:** fit scores min 0.58 / mean 0.81-0.93 per sheet; the lowest are the two-letter bomb
  pickup (10:89, 108-109: 0.67) and a few `#9` capsules (0.58-0.7), which read right in game.
- **Tool change:** `cut --merge` now keeps the frames an atlas already has when only part of it is
  re-cut (before, only frames with their own scale survived), so a new batch adds to
  `tyrian-shp-9/10` instead of replacing them. A sheet of 8 cells is now 3x3 (was 4x2, 2:1, which
  Gemini cannot answer).
- **In game:** no code change; `?sprites=original` brings back the extruded pickups. Checked on
  level 1 (ticks 625, 1135) and level 7 (tick 100).

**Options considered:**
- *Hand-pick the frames per level:* fewer requests, but the shared pickups would still differ
  between levels; the whole episode's set is only 9 requests.

## D95 — `shapesy` HD terrain over its six SAVARA levels: 15 sheets, no retries; grey paintings keep water_filter's exception

2026-11-04

**Decision:** the `shapesy` tileset (SAVARA: levels 1-8, 1-12, 1-17, 3-10, 4-3, 4-19) now draws its ground
from HD paintings (`public/art/terrain/shapesy/`: 108 ground tiles, `0.webp`, 0.7 MB), made with D83's
multi-level pipeline: `inventory`, `sheets`, Gemini, `cut --edge-aware`, `check`.
- **Layers 1 and 2 are not painted.** All 68 + 45 tiles are `structure` (SAVARA's towers are modelled, D82), so
  one layer (0) and 15 primary sheets (7x6-tile map regions) cover everything; the 16 optional context sheets
  were not needed (every tile is on a region sheet).
- **Gemini:** 15 requests, no retries, no usage warning. Prompts named each sheet's real material, written from
  the contact sheet (grey stone-brick fortress floor with dark brick walls; deep blue rippled water; brown sandy
  dirt with palm jungle seen from above; sheet 13's island with its bronze ring) rather than SEND.md's
  palette-group labels (D89); sheets softened (the default). Every answer registered at scale 11.38, shift 0:
  fit 0.84-0.99 (0.70 on the two water-heavy sheets 07 and 13, where the texture gives the match little to
  hold; the layout is kept by eye), tile NCC median 0.85-0.99, blockiness max 2.75 (08, painted flat, not
  copied). Another agent held the lock for ~25 minutes in the middle of the run.
- **Seams** (`check`, every edge of the six maps; step across edges over step inside tiles): ground 0.563
  (where the original is continuous 0.562), bands 0.496. Per level: 1-8 0.524, 1-12 0.664, 1-17 0.597, 3-10
  0.524, 4-3 0.642, 4-19 0.465. The cut's weak fits (NCC < 0.5): tiles 20, 21 (open water).
- **Shader fix, found in game.** On 4-3 (SAVARA IV) the grey fortress floor came out blue: that level runs
  water_filter, which in the original leaves grey indices (`index & 0x30 == 0`) alone, and the HD terrain
  shader (D57) hands every painted colour the hue ramp's index (16 + shade), so greys were recoloured.
  `terrainPalette` now gives a near-grey painting (chroma < 0.04) a grey index (0 + shade). Other tilesets
  only differ on grey paintings under a hue filter.

**Checked** in game (`?debug=play&seed=1&skip=T&freezeAt=T`, against `&terrain=original`): 1-8 t600, t1800;
1-12 t1200; 3-10 t1000; 4-3 t1200, t2500 (blue before the fix, grey after; a few bluish specks remain in the
bricks). Sheet: `tyrian-scratch/shapesy-hd/captures/shapesy-compare.jpg`. 1-17 and 4-19 were not captured
(4-19 is all one brown tile). Not looked at: the seams at `&dpr=0.3`.

**Review:** sheets, answers, per-answer registration and `cut-report.json` are in
`tyrian-scratch/shapesy-hd/work/` (not in git, D3).

## D96 — A shot-off enemy leaves a scorch mark on the structure it stood on (remastered backgrounds)

**Context:** on TYRIAN's islands the purple eye fortress (`shapesz-tyrbld-purple-orb`) carries nine cap
enemies (newsh2 273-283, enemy types 32-37). The user found it jarring that a destroyed cap reveals an intact
machine. Checked against the real OpenTyrian, not our reproduction: `tools/opentyrian-bot` gained
`BOT_DUMP`/`BOT_DUMP_TICKS` (the shown frame, VGAScreenSeg through the live palette, as PPM),
`BOT_WATCH=lo-hi` (prints each watched enemy's death and its enemyDat death fields) and `BOT_POWER` (the
harness's power 5). With `BOT_SEED=1` level 1 plays as `?debug=play&seed=1` does (caps 53/54 die at tick 2581
in both). The caps have `dgr 0, dlevel 0, dani 0, enemydie 0`, the explosions only blit to the screen
(`blit_sprite2` into VGAScreen each frame), and no tile changes: **the original stamps nothing.** The mark is
the terrain itself: the background-3 tile under each cap already paints a cracked, broken socket, hidden while
the cap sprite covers it. Our original look shows that tile too; the remastered structure model builds intact
faceted bosses there, so a dead cap reveals a clean machine.

**Decision:** render-only scorch marks (`src/render/remaster/scorchLayer.ts`), in the remastered backgrounds
only (the original look already shows the painted socket):
- The sim records, output only, each enemy destroyed without a dead look in `DrawList.deaths`
  (`recordEnemyDeath` at the two places JE_main frees a shot enemy's slot: key, centre, the layer its slot
  group scrolls with, size). Nothing reads it back; game logic is unchanged.
- The renderer marks a death when the enemy stood on a **structure** tile (a tile model matches it) of its
  layer, opaque at its centre, and had moved with that tile over its last tick (so aircraft flying over a
  structure leave nothing). The mark is pinned to that tile's draw key and offset: it scrolls with the layer
  exactly and lasts until the tile leaves the screen, as the original's painted socket does.
- Look: a procedural decal, 11.5 px radius for a 24x28 enemy (6.5 px for 12x14): ragged near-black soot, a
  shattered-plate crack network (Voronoi edges, finer toward the impact) plus a few radial cracks, a dark
  centre; the cracks glow orange and cool within about a second. Drawn just above what the models build under
  an enemy (0.35 on backgrounds 2/3, 0.40 on the ground) and below the enemies' pass, projected on the camera
  ray (D6), premultiplied alpha (dark char plus additive embers).
- Cost: one instanced draw call; a fixed pool of 64 marks (the oldest gives way); per tick a scan of the
  draw list only while marks exist or something died.

**Not done:** rebuilding the purple-orb model's bosses broken (the mark covers it, and generalises to every
structure with enemies on it); scorch on plain ground or HD terrain without a structure model. The harness's
`&skip=` only shows its last two ticks, so a capture must skip to before the death to see a mark.

**Checked:** comparison sheets (real C | ours original | ours remastered, ticks 2579/2582/2616/2650) in
`tyrian-scratch/cap-scorch/` (`sheet-before.png`, `sheet-after.png`); the original look is unchanged.

## D97 — Episode 1's remaining shots drawn from Gemini flat art (D42/D43)

2026-11-04

**Decision:** every shot frame episode 1 draws (player weapons, sidekick shots, enemy bullets) that still
showed as an extruded sprite (inventory.json `shots`, status `sprite`) now has flat art: 101 frames, 79 new in
`tyrian.shp#7` (71 -> 150) and 22 in a new `tyrian.shp#11` atlas (`tyrian-shp-11.webp`, the Sidekick/orb shots).
Includes the enemy shots drawn on the most levels: #7 286-288 (17/16/16 levels) and 168 (15).
- **Inputs:** inventory in `tyrian-scratch/e1-shots/` (enemy shots first by level count), three families
  (`e1-shots-enemy`, `-player`, `-11`) in `SHEET_GROUPS`: 9 sheets of 9-12 cells, 9 Gemini requests, no
  retries, no usage warning. Level palette 5.
- **Cut:** `cut --merge`; fit min 0.71 / mean 0.79-0.97 per sheet (lowest: #7 208-209 and 175, 177, 181, 0.71-0.77,
  small red stars/rings). Mirrored pairs share a cell; 2 frames stay painted tracers (D56, #7 67, 70).
  Gemini redrew the tiny rocket shots (#7 31-33, 57, 76, 95) as small ships/rockets; they keep the sprite's
  outline and read as missiles in game.
- **In game:** no code change; `?sprites=original` brings back the extruded shots. Checked on level 1 with
  Multi-Cannon (t700), Protron + sidekicks (t1200), Mega Pulse (t1800); sheet
  `tyrian-scratch/e1-shots/before-after.png`. Not captured: the other weapons' frames.

## D98 — Menus scroll on short phones: one definite track per screen, panes that scroll, a help bar that stays (extends D85)

**Reported:** on a phone the item screens (shop, its submenus, Data Cubes reader, ship specs), Options, Load
and the two-player shop were cut off at the window's edge with no way to reach the rest.

**Cause.** `.ui-screen` is a fixed, `overflow: hidden` grid whose one row was `auto`. A percentage height
resolves against a definite track, so the pane's `max-height: 100%` (and the shop's phone `height: 100%`)
resolved to nothing, the pane grew to its content and the screen clipped it. `overflow-y: auto` on `.ui-panel`
(D85) never had anything to scroll. Options and Load looked fine only because their flex column got a height
from elsewhere. No touch handler was involved: `controls.ts` only handles pointers on the canvas, during play.

**Decision.**
- `.ui-screen` gets `grid-template: minmax(0, 1fr) / minmax(0, 1fr)`: one track the size of the window, so
  panes size against it; `touch-action: pan-y` lets a finger pan a menu (and nothing else), `overscroll-behavior`
  keeps the page still. Panes and `.ui-scroll` also get `-webkit-overflow-scrolling: touch`.
- The shop panel's children lose `min-height: 0` (it let the rows squeeze into the window and the panes
  overlap once the height was definite); its rows are `max-content`. On short windows (width <= 720 or height
  <= 520) the help bar spans every row, `position: sticky` at the foot of the scrolling panel, with a last row
  of its height so it never covers a pane; the panes are placed by hand (a definite-row item makes
  auto-placement skip its cells). Load and High Scores' message bars stick the same way.
- The title's row is `minmax(min-content, 1fr)` and the screen scrolls, for a window too short for its menu.
- Focus reveal was already there (`reveal()` = `scrollIntoView({block: "nearest"})`: menus, options, shop,
  high score picker); `scroll-padding-block` keeps it clear of the sticky bar.
- `tests/app/menuScroll.test.ts` pins the structure and fails if a screen id is opened that isn't on its list,
  or a screen's CSS sets its pane's overflow to hidden/visible.

**Checked** (headless Chrome, mobile + touch emulation, `Input.synthesizeScrollGesture` swipes; every menu item
brought into view by scrolling) at 375x667, 390x844, 667x375 and 844x390: title steps, Options, Load, High Scores,
Players, the item screen in every submenu (front gun with its simulator, sidekicks, Options, nav, Data list,
cube reader, specs, quit), two-player shop, data picker, game over, save name, high score entry, pause, story
text. Desktop (1920x1080) captures of the title and item screen match. Captures:
`tyrian-scratch/mobile-scroll/` (`before-*`, `b3-*`). Not covered: the arcade and episode-end screens (not
reachable headless without a level), the destruct mode picker.

## D100 — Touch play: the HUD's own boxes are the rear-mode and sidekick buttons (extends D61)

**Asked:** on a phone, drag-anywhere steering with firing while touched is fine as it is; what's missing is a way to
fire the sidekicks and change the rear gun's mode. A first draft added separate on-screen buttons in a strip or
column outside the frame; the user's better idea replaced it: the instruments themselves are the controls.

**Decision.**
- **Tap the REAR GUN box or its MODE lamps** to change the rear mode (`changeFire`, as Enter does). **Hold a
  SIDEKICK box** to fire that sidekick (`leftSidekick` / `rightSidekick`, held inputs in the sim like the keys).
  No new buttons, and the frame looks as it did; a held target gets a faint copper wash and rim (`.is-down`).
- **Hit areas** are invisible boxes laid over the SVG by `HudFrame.build` from `hudTargets(layout)`
  (`hudFrame.ts`, pure, so it is tested): each box grown evenly to 44 px on the window (`growTarget`) where its
  neighbours leave room. Landscape: one column in the sidebar, the sidekicks reaching down over plain plate, so
  41-44 px tall at 390-375 px heights (the MODE label caps the first). Portrait: the rear box (44) plus the MODE row
  (33, the score box is under it), and each sidekick grown down over the console's greebles to 44.
- **The finger belongs to the target.** `pointerdown` there is `preventDefault`ed, stopped, and
  pointer-captured; `Controls` only steers from touches that start on the canvas, so a press neither steers nor
  fires, and it works while another finger steers. `Controls.touchAction` holds the action while down and latches a tap
  shorter than a tick for one sample (the sim's `portConfigChange` makes a held MODE change once).
- **Only on touch, only in play.** On for a coarse pointer or after a finger was the last input
  (`<html data-input="touch">`), in the framed HUD while a level runs; `?touchhud=1|0` forces it either way (to try
  it with a mouse). Desktop is unchanged. Two-player has no framed HUD and no touch path (player 2 has none); the
  minimal interface has no boxes, so neither has targets.
- The existing touch pause button stays; steering and auto-fire are untouched.

**Checked** (headless Chrome, mobile + touch emulation, `Input.dispatchTouchEvent` with two fingers, `?debug` off,
a real level, the bot's rear weapon fitted) at 390x844, 375x667, 844x390, 667x375: a finger alone on a sidekick box
holds it and doesn't move or fire the ship; tapping MODE toggles the mode once (also when held 600 ms); with finger 1
steering on the playfield, finger 2 on each target presses it, finger 1's steering carries on, and release clears it.
At 1920x1080 the targets are off. Captures: `tyrian-scratch/mobile-scroll/th-*`. Tests: `tests/app/hudTargets.test.ts`.
## D99 — The shop's Options reach the one settings screen; the shop shows the original's titles; the HUD says CREDITS (extends D85, D61)

**Reported:** (1) Options from the shop lacked settings the title's Options has; (2) the shop showed an invented
"Item screen" kicker; (3) the HUD's "SCORE" is really the player's cash.

**Found.** Both entries already call the same `showOptions` with the same sfx and music. The gap was the shop's
Options *menu*: the original's pane (Load, Save, Music and Sound sliders, Joystick, Keyboard, Done) shows only the
volumes, and the settings screen with the music and sound styles, Terrain, Interface, Camera and Resolution
rows was behind Joystick and Keyboard only.

**Decision.**
- `run.ts` builds one `OptionsHost`; the title's `showOptions(optionsHost)` and the shop (`ItemScreenHost extends
  OptionsHost`, `runItemScreen({ files, ...optionsHost })`) use it, and `optionsRowsFor(host)` is the one source of
  the rows, so they cannot drift. Changes apply live and are saved by the same code (`savePrefs`).
- In the shop's Options pane, Enter (or tapping a selected row) on Music or Sound now opens the same settings screen
  (`menu.setupRequest = "sound"`), like Joystick and Keyboard (sections "joystick", "keyboard" still focus their part).
  The hint reads "All settings". The original's rows and their order are unchanged.
- Headings are the original's: `JE_drawMenuHeader` / the submenu title (`menuInt`) and nothing above them. The
  "Item screen" kicker (an internal name, `JE_itemScreen`) and the invented "Upgrade Ship" kicker are gone; the
  dialog's aria-label is the open menu's title. "Retry from the item screen" now says "the shop".
- The in-game HUD label is "CREDITS" in the bronze frame (wide and phone console), the minimal HUD and the
  two-player HUD (these two had no label; they now show one), and the level-complete line. Number format is
  unchanged. "High Scores" and the original's "Player 1 Score:" text are left alone.

Captures: shop top menu, Front Gun submenu, Options pane and the settings screen opened from it, beside the title's Options, and the three HUDs.

## D101 — TYRIAN's walkway deck is not metallic, so the road keeps the original's brightness when the fortress model swaps in (extends D47)

**Reported:** "Road in level 1 on floating platforms becomes dark after it initially pops in."

**Found.** The road is the fortress (and bridge) model's walkway deck. A structure with `minRows` is only placed
once two of its rows are on screen, so for the first ticks the road draws as its HD tile (luma about 86, the
original's); then the model replaces it (tick 4193 in `?debug=play&seed=1`). The model's deck was palette grey 5
(dark) with `metallic=0.5`; under the scene's lights and room environment a half-metallic dark grey keeps only
half its diffuse, so it drew at luma about 58. Not a load swap, the shadow map or a late texture: it happens with
every model preloaded, and `castShadow = false` changes nothing on the road.

**Decision.** The `walk` and `walk_dark` kinds in `lib_tyrbld.py` are non-metallic (roughness 0.55) and `rail`
is 0.3 metallic (was 0.6); fortress and bridge rebuilt with their documented bakes (2048 / 4096 px). The road
measures about 81 against the original's 86 and no longer steps at the swap. The swap itself stays (D54: the
structure is decided when it first shows); only the brightness mismatch was visible.

Captures: `tyrian-scratch/road-dark/strip-compare.png` (before/after ticks 4186-4198).

## D102 — Every setting is reachable from inside a game on touch, gamepad and keys: Options on the pause menu, and an "All settings…" row in the shop's Options (extends D99)

**Reported (phone).** (1) The pause menu in a level offered only Resume and Quit to title. (2) The shop's Options pane
(D99) showed the original's rows; the full settings screen was behind Enter, or "tap twice" on Music or Sound, which a
tap on a volume bar never does, so nothing said it was there.

**Decision.**
- `showPause(optionsHost)` lists Resume, **Options**, Quit to title. Options opens `showOptions` with the run's one
  `OptionsHost` (D99) over the pause screen (`over: true`, so closing it returns to the pause menu). The game never
  leaves its paused state; changes apply live and are saved by the same code (volume, music and sound style, terrain,
  interface, camera, resolution). The settings screen's own D98 scrolling and Back/Done work on touch, pad and keys.
- The shop's Options menu gets a ninth row, "All settings…", between Keyboard and Done (`menuChoices[MENU_OPTIONS]`
  8 to 9; Done is now 9). It sets `menu.setupRequest = "sound"`. The original's rows and their behaviour are
  unchanged, but this one opens on the **first** tap (the original's rows focus on the first tap and act on the
  second, `JE_itemScreen_mouse`). It has a help line of its own. Enter on Music or Sound still opens it too.
- Other paths: the two-player and arcade menus (and Super Tyrian) all reach this same Options menu
  (`menu.curMenu = MENU_OPTIONS`), so they gain the row; the title already had Options. No other settings entry was
  keyboard-only. Modem/network's `MENU_LIMITED_OPTIONS` isn't ported.

Captures: `tyrian-scratch/pause-options/captures/` (L1 = 844x390, L2 = 390x844 touch: pause, Options, Camera applied,
resume; p1 = shop row and settings; D = desktop keys).

## D103 — Level 1's sand-pad turrets stand on the HD ground, and DELIANI's glass orbs are painted in blobs (extends D86)

2026-11-04

**Cause.** The episode-1 QA sweep (issues 5, 7) found two models that read wrong in the game's render, neither a
pipeline bug: models carry palette-index materials, not textures, so D91's texture worker and D87's damage masks
are not involved.
- **SOH JIN (1.13):** the bell turret `newshf-39` and the sand pod `newsha-91` exported the sprite's tile
  background as a box of sand (`SAND` plate over the whole 24x28 tile), the same fault as D86's dirt pads. It
  showed as a beige rectangle round each turret on the HD ground.
- **DELIANI (1.5):** the glass orb (`assembly-newshu-129`, four 2x2 pieces, two orbs overlapped at tick 5531) paints
  its cube-sphere faces cell by cell from the sprite's colour classes, so the sprite's pixel dithering and its 1 px
  dark gaps came out as speckled green, grey and violet squares on the glass.

**Decision.**
- `newshf-39` and `newsha-91` no longer export the sand; the dome stands at z = 0 (the pod's dark crater disc stays).
  The HD ground shows round them. Frames, pieces and exports are as they were.
- `assembly-newshu-129.py` filters the part map before painting (`smooth_parts`, 7x7 majority; DARK casts no votes
  and is replaced by its neighbours' part). The mass, lobes and lamp stay; the stray dark/violet squares and
  one-pixel specks go. All three states (grey, green, purple) are rebuilt.
- Not changed: `assembly-newsh3-191` (sand plate) and `assembly-newshj-127` (jungle ground plate) have the same
  kind of pad but are in episodes 3-4; check them in those levels' passes.

Captures: `tyrian-scratch/qa-quick/` (`before_*`/`after_*`: 1.5 t5531, 1.13 t300 and t1615).

## D104 — Explosions are drawn more see-through than other blends, so the ground shows through the fire (extends D35, D80)

2026-11-04

**Problem.** The C blends explosions about 50/50 with the ground (`explosionTransparent`, `blit_sprite2_blend`). Ours drew
them at the shared `BLEND_ALPHA` 0.55 and then added glow (emissive 1.6, a 0.65 halo), and a big explosion stacks many
overlapping sprites, so the fire read as opaque.

**Decision.**
- `EXPLOSION_ALPHA = 0.28` for blend draws in `Pass.Explosions` (flat art and sprite models); every other blend keeps
  `BLEND_ALPHA`. 0.40 was tried first: overlapping puffs still covered the ground, so it was lowered until the ground
  pattern shows through a stack of them.
- `HOT_BLEND_GLOW` 1.6 -> 0.9 and the fireball halo 0.65 -> 0.3, so the fire does not wash the ground out.
  Lights and sparks are unchanged, so explosions keep their flash.

Captures: `tyrian-scratch/explosion-alpha/` (`scan700.png`/`after700.png`, `scan1000.png`/`after1000.png`: 1.1 seed 1, power 8).

## D105 — Explosions draw through a stencil, so stacked fire stays as see-through as one layer (extends D104)

2026-11-04

**Cause.** D104's 0.28 looked no different: a boss's death piles dozens of explosion sprites on one spot, and
n layers at opacity a cover 1 - (1 - a)^n, so any single-layer alpha ends solid. The atlas alpha is not the problem
(checked: `newsh6-shp.webp` has about 1% faint texels, tight frames, no background quads; the glow, lights and halo were
also not it: with them off, 0.12 still came out solid).

**Decision.**
- The flat art's explosion pass (`spriteArtLayer.ts` `stencilled`) writes a stencil and skips pixels already
  written: each pixel takes one explosion layer (the first drawn), blended at `EXPLOSION_ALPHA` 0.4 (D104: 0.28).
  The renderer and the screen-filter target now carry a stencil buffer.
- Texels with source alpha under 0.1 are discarded, so faint edges neither show as a halo nor block the layer behind.
- Glow settings stay as D104 set them.
- The look: ground and structures show through the whole fireball; overlapping puffs no longer pile up, only the
  flash and sparks add density. Layers no longer show depth ordering in a stack (the first drawn wins).

Captures: `tyrian-scratch/explosion-alpha/` (`cmp2_700.png`, `cmp2_1000.png`: before = main before #135, after = this).

## D106 — Explosions take up to three layers per pixel, and soft puff edges no longer leave dark seams (extends D105)

2026-11-04

**Decision.**
- D105's one layer per pixel becomes three: the 1st, (N+1)th and (2N+1)th explosion drawn on a pixel, none after, with
  `EXPLOSION_LAYER_EVERY` N = 2 (`spriteArtLayer.ts`). A colourless full-screen quad sets the stencil to 256 - 3N just
  before the explosion pass; each explosion draw (pass or fail) increments it, saturating at 255, and passes where
  `stencil & (N-1) == 0` (counts 0, N, 2N; 255 never passes). N must be a power of two. Only N = 2 was tried.
- `EXPLOSION_ALPHA` 0.4 -> 0.33: three stacked layers cover 1 - 0.67^3 = 0.70, so the ground still shows a little.
- **Seams.** The dark lines where puffs overlapped were the first-drawn puff's soft rim (dark red, alpha 0.1-0.5)
  claiming the stencil and blocking the puff behind. Texels under 0.5 source alpha are now discarded in the art shader
  (D105 used 0.1), so only a puff's solid body claims a layer; its edge is a touch harder.

Captures: `tyrian-scratch/explosion-alpha/` (`cmp_L2b_700.png`, `cmp_L2b_1000.png`: left = main after #136, right = this).

## D107 — SAVARA's clouds (`shapesy` layers 1 and 2) are painted terrain, from 13 Gemini sheets

2026-11-04

**How clouds are drawn.** Clouds are not sprites: they are background-2 and background-3 *tiles* (`TileDraw`,
`src/sim/draw.ts:102`), drawn by the terrain path (`src/render/remaster/terrainArt.ts`, `groundAtlas.ts`;
D45, D57). On SAVARA the layer-2 (background 3) cloud tiles draw opaque (`effect "none"`, pass 5) and layer 1
(background 2) draws blended; TYRIAN's/WINDY/HOLES clouds (`shapesz`, layer 1) were already painted by D89, so the
QA report's issue 3 (clouds with stair-stepped edges) was only still true for `shapesy`. D95 had left layers 1-2
unpainted because its inventory classed all 68 + 45 tiles as `structure`; they are all cloud pieces plus the
water tiles layer 1 repeats (these reuse layer 0's paintings).

**Decision.** `inventory --kind` marks every layer 1-2 `shapesy` tile `terrain`; `sheets`, Gemini, `cut --edge-aware`,
`check` as D83. 13 primary sheets (7 `ctx-l1-*`, 6 `region-l2-*`), prompts' material changed from SEND.md's "icy
translucent clouds" to "soft fluffy white and pale-blue cumulus cloud puffs seen from above, with soft feathered wispy
edges, no ice, no rock" (D89: name the real material). Atlas: `public/art/terrain/shapesy/1.webp` (68 tiles) and
`2.webp` (45), alpha is the original silhouette (translucency and shapes kept); colour is matched to the original.
- **Gemini:** 14 requests (1 lost: the first answer never appeared in the chat after a page reload, resent), 0 bad
  answers, no usage warning. Layout was kept on every sheet (registration 7.42 / 11.38 px per original px).
- **Seams** (`check`): layer 1 0.628 (continuous 0.565), bands 0.451; layer 2 0.977 (continuous 0.803), bands 0.631.
  Weak fits (NCC < 0.5): 1:125, 1:242, 2:237, 2:246, 2:266, 2:278.
- **Not covered:** clouds on tilesets with no HD atlas (other episodes' tilesets, `shapes*` other than y and z): they
  have no HD ground either, so a cloud-only atlas would sit on pixel terrain; do them with their tileset's run.

**Checked** in game (`?debug=play&episode=1&main=8&seed=1&skip=300&freezeAt=300`), before/after under
`tyrian-scratch/clouds/captures/`. Answers, sheets and prompts: `tyrian-scratch/clouds/work/shapesy/` (not in git, D3).

## D112 — `shapesw` HD terrain: 100 of 110 ground, 28 of 33 layer-1 and 17 of 27 layer-2 tiles from 26 Gemini sheets (two passes)

2026-11-04

**Decision:** the `shapesw` tileset (levels 3-1, 3-4, 3-6, 3-9, 4-8, 4-11, 4-20) gets `public/art/terrain/shapesw/`
(`0.webp`, 60 ground tiles, 0.4 MB), made with D83's pipeline (`inventory`, `sheets`, Gemini, `cut --edge-aware`,
`check`). Partial: the run stopped at Gemini's usage limit (every Pro image model showed "limit resets Nov 4, 11:05
PM") after 7 of 26 primary sheets; the other 50 layer-0 tiles and all of layers 1-2 still fall back to the original
(per-tile fallback, D57). Not finished.
- **Layer 1-2 kinds corrected by hand.** The classifier called the 3-6 FLEET layer-2 ship hulls (brown and grey plated
  machinery) terrain because the main ramp is brown. They are structure: 158 layer-2 tiles overridden with `--kind`
  (list in the scratch folder, `kinds.txt`), left to models. That leaves 27 layer-2 and 33 layer-1 terrain tiles (brown
  rock) to paint. Layer 0 of 3-6 (grey hull plating on black) stays in the sheets: layer 0 has no structure kind.
- **Sheet prompts rewritten** from the contact sheets (D89): SEND.md's labels were wrong ("icy translucent clouds" for
  what is a frozen glacier: turquoise sheet ice, frosted ice shelves with icicle cliffs, navy paved roads; "asteroid
  rock" for 3-6's ship hull). Brown dirt on 3-4, brown rock plateaus on layers 1-2, hull plating on 3-6.
- **Gemini:** 7 answers kept (3-4 dirt 2, 3-1 ice 5; 3-1 sheets also feed 4-8). Requests: 9 sent (1 stray "Paris
  postcard" suggestion tile click, stopped; 1 sheet dropped silently by Gemini and re-sent). Every answer registered at
  scale 11.38: fit 0.80-0.99, tile NCC median 0.85-0.99 (min 0.62 on a cell), blockiness max 1.97.
- **Seams** (`check`, layer 0, every edge): 0.831 across / inside (where the original is continuous 0.754), bands
  0.481. Above the ~0.6 ground target but the original is itself 0.754 on this icy texture; the worst pairs (ratio 7-10)
  are a painted tile meeting a not-yet-painted one, which goes away as sheets are added. Weak cells (NCC < 0.5): none.

**Checked** in game (`?debug=play&episode=E&main=10&seed=1&skip=T&freezeAt=T`, against `&terrain=original`): 3-1
(CAMANIS) t600, t1500; 4-8 (ICE EXIT) t600, t1500. Sheet: `tyrian-scratch/terrain-shapesw/shapesw-compare.jpg`.
terrainArt and terrainHd tests pass. Not looked at: other levels, `&dpr=0.3`.

**Next:** when the Pro limit resets, send the remaining 19 primary sheets (SEND.md order, prompts in
`work/prompts/`), then `cut --cache work/cands.pkl --edge-aware` and `check`. Sheets, answers, `cands.pkl`,
`cut-report.json` are in `tyrian-scratch/terrain-shapesw/work/` (not in git, D3).

**Second pass (Nov 9):** the other 19 primary sheets sent (29 requests, 10 of them retries; no usage warning, no limit
hit; four sends were stopped before going out because the page was in the wrong state). Atlas folder restored, then
`cut --cache --edge-aware --exclude <25 tiles>`: 60 ground tiles kept byte for byte, 40 new ground, 28 layer-1, 17 layer-2
(0-2.webp, 1.webp, 2.webp; 0.85 MB in all).
- **Prompts changed after two failures.** The glacier answers came back as dramatic ice caves (fit 0.29, NCC 0.00) and
  the first layer-2 answers as a pixel tile kit or a cave scene. Prompts now say "Do not rearrange, invent or move
  anything", "flat, straight top-down view, no perspective, no dramatic lighting", and for layer 2 / contexts "on a pure
  black background ... do not paint a cave, sky, ground or scenery". The word "spaceship" made Gemini draw a ship in
  space (sheets 08, 12; "flat game-map floor texture ... not a ship" did not cure it).
- **Sheets that stayed poor** after their one retry (sheet NCC median): ground 02 0.80 (fine), 03 0.97, 14 0.50, 10 0.56,
  05 0.51, 15 0.25, 16 0.59, 17 0.94 (after an anti-pixel-grid retry; first answer was a pixel copy), 06 0.16 and 08 0.05 and
  12 0.04 (hull plating; Gemini redraws it as a ship), layer-2 02 0.16. Tiles whose best candidate scored under 0.4 are
  excluded and fall back to the original: ground 3 6 7 21 22 31 32 33 267 268 (hull sheets, ice 267-268), layer 1 498 500
  501 506 518, layer 2 450 451 452 454 470 472 473 474 475 488.
- **Seams** (`check`, every edge): layer 0 0.885 across / inside (original continuous 0.769; the 41,593 edges between
  kept tiles 0.831 vs 0.754), bands 0.503; layer 1 0.836 (continuous 0.830), bands 0.416; layer 2 0.949 (continuous 0.931),
  bands 0.537. Above the ~0.6 / 0.85 targets on ground and layer 2, but each is within about 0.1 of the original's own
  ratio on this high-contrast ice and rock; edges that touch a new ground tile are 1.91 (continuous 1.27), the
  painted-next-to-fallback pairs.
- **In game** (`episode=E&main=M&seed=1&skip=T&freezeAt=T`, both looks; section numbers: 3-1 CAMANIS E3 main 10, 4-8
  ICE EXIT E4 main 10, 3-4 IXMUCANE main 4, 3-6 FLEET main 12, 3-9 SAWBLADES main 19): 3-1 and 4-8 at t600/t1500 (before |
  after: `tyrian-scratch/terrain-shapesw/captures/compare-3-1-r2.jpg`, `compare-4-8-r2.jpg`), 3-4, 3-6, 3-9 at t900
  (`compare-3-4-3-6-3-9-r2.jpg`, original | HD). No gaps or misplaced tiles seen. terrainArt and terrainHd tests pass.
  Not looked at: 4-11, 4-20, `&dpr=0.3`, fallback with a tile removed.
## D108 — The remaining 60 shot frames and 7 pickup units drawn from Gemini flat art (D42/D43, finishes D94/D97)

2026-11-04

**Decision:** every shot frame and pickup unit that `docs/roadmap/inventory.json` listed as still extruded
(`sprite`/`basic`/`partial`) now has flat art, so no shot or pickup draws as an extruded sprite in any episode:
60 shot frames (`tyrian.shp#7` +34, 150 -> 184, `tyrian.shp#11` +26, 22 -> 48) and 7 pickup units (`tyrian.shp#10`
+41 frames, 226 -> 267: 37, 57, 76, 114, 133, the 2x2 92 and the 2x2 191 family). The inventory was not stale:
checked against the manifest, 60 shot frames and 14 pickup frames were missing (frame 273 of 191 already had art).
The most-drawn one is #7 198 (7 levels, 3 episodes), with #7 199 (96,631 ticks) and #7 162, 285, 61.
- **Inputs:** an inventory in the D43 format (`tyrian-scratch/flat-art-rest/inventory.json`, shots in order of ticks
  drawn), four families (`rest-shots-enemy`, `-player`, `-11`, `rest-pickups`) added to `SHEET_GROUPS`: 8 sheets of 6-12
  cells, palette 5 (every level of every episode draws with `pcxpal[2]`, hud.ts).
- **Gemini:** 8 sheets, 10 requests (two of the first run went out with no image attached, because the page had not
  finished loading when the sheet was pasted: they answered with a generic grid and were discarded; `player-1` and
  `enemy-2` were sent again), no usage warning. Take-away for the operator: wait for the page after navigating and
  check the pasted thumbnail before sending.
- **Cut:** `cut --merge`; fit min 0.33 / mean 0.57-0.98 per sheet. Frames Gemini painted wrongly (D56): none, so no new
  `PAINTED` entry (the two Vulcan tracers stay). Weak fits: #10 114 (grapes, 0.33), #10 57 and 133 (gems, 0.45-0.48),
  #7 120 (blue beam, 0.62), the 2x2 #10 92 (a hot-dog sign, 0.62); all read as the right object in the contact sheet. #7 198,
  199 and 200 (the blue lightning wiggles) fit 0.80-0.83.
- **Removed after review:** the 2x2 hot-dog pickup (#10 92, 93, 111, 112) is not shipped: its red/yellow "HOT DOG"
  lettering was lost and tile 92 was a black blob, so those 4 frames are taken out of the manifest and draw as the
  original sprite (unit 92 stays extruded; the atlas still holds their unused pixels, and a plain re-cut would add them
  back). Follow-up: redo that cell with a prompt that keeps the lettering, or a painter (D56). Counts above include them:
  net +37 frames in `tyrian.shp#10`, 263 frames, and 6 of the 7 pickup units.
- **Hot-dog redone (Nov 10, branch `hotdog-art`):** a sheet of just the hot-dog (new `SHEET_GROUPS` family
  `rest-hotdog`, one 24x28 cell: hot dog on a blue steel dish, "HOT" above, "DOG" below) with a prompt that spells
  out the dish, the two words, the letter layout and the red/orange glossy-block lettering. One Gemini request, no
  retry: the lettering is Gemini's and reads "HOT" / "DOG" in the sprite's layout, no black blob in tile 92.
  `cut --merge` (palette 5): fit 0.87 on all four tiles, so frames 92, 93, 111, 112 are back in the manifest
  (`tyrian.shp#10`: 267 frames, all 7 pickup units flat). No painter needed (D56 untouched).
  Comparison (original | flat art): `tyrian-scratch/hotdog-art/compare.png`; contact sheet `.../check.png`.
- **In game:** no code change; `?sprites=original` brings back the old look. Checked on 3.7 STARGATE (tick 2473) and
  4.9 LAVA EXIT (tick 14), the levels where #7 198/199 are drawn; the status line's "flat in" count rises (0 -> 2, 0 -> 1).
  Captures: `tyrian-scratch/flat-art-rest/before-after.png`; contact sheet `.../check.png`. Tests: tsc, vitest (703 passed).
  Not captured: the pickups, the sidekick shots #11 134-153.

**Options considered:**
- *Painting the thin wiggles and streaks procedurally (D56):* not needed, Gemini kept their outline and read as energy.

Answers, sheets and prompts: `tyrian-scratch/flat-art-rest/` (not in git, D3).

## D113 — `shapesx` HD terrain: 191 of 196 ground, 7 of 14 layer-1 and 11 of 13 layer-2 tiles from 24 Gemini sheets (two rounds; D83, D95)

2026-11-04

**Decision:** the `shapesx` tileset (levels 2-1 TORM, 2-2, 2-6, 2-10 BOTANY A, 2-11, 2-12, 4-13 EYESPY) gets a
partial HD atlas (`public/art/terrain/shapesx/`: `0.webp`, 70 ground tiles, 0.56 MB). The tiles it lacks fall back
per tile to the original (D57), so every level plays; the rest is a second round.
- **Inventory:** layer 0 has 196 terrain tiles to paint (+3 empty); layer 1 has 14 terrain and 120 structure
  (cyan plating, left to models); layer 2 has 13 terrain and 21 structure. 24 primary sheets (20 ground regions, 2
  layer-2 regions, 2 layer-1 contexts); layers 1 and 2 have no art yet.
- **Prompts rewritten by hand** (D89): SEND.md calls the biomechanical hull and alien flesh "cyan" and the horns
  "brown rock". The real materials: forest canopy with blue water, cliffs and grey pipes (regions 03, 05, 06, 09, 13,
  14, 16, 19); purple veined tissue (08, 20); steel hull plating and pipes (01, 02, 07, 10, 11, 15, 18); alien
  flesh with eyes and bone spikes (04, 12, 17); tan horns and claws on black (layer 2, layer-1 contexts). Generator:
  `tyrian-scratch/terrain-shapesx/bin/mkprompts.py`.
- **Gemini:** 4 requests sent (regions 05, 03, 13, 06: all forest and water), 0 retries, all painted well,
  registered at scale 11.38, NCC median 0.60-0.67. Then Pro, 3.8 Flash, 3.1 Pro and 4 Argon were greyed out in the
  mode picker ("Limit resets Nov 4, 11:05 PM"; the account is shared by four agents and ~14 min waits for the lock
  kept the pace low), so sending stopped. 20 primary sheets are unsent (SEND.md order: 19, 09, 16, 14 forest,
  then 08, 20, 01, 17, 04, 15, 10, 12, 02, 18, 11, 07, layer 2, layer 1).
- **Seams** (`check`, ground edges that include fallback tiles, so inflated): 0.73 overall (continuous 0.73,
  bands 0.51); per level 2-1 0.75, 2-10 0.62, 2-11 0.73, 2-12 0.74. Weak fit (NCC < 0.5): tile 596. Re-measure after the full cut.
- **Checked in game** (2-1, 2-10 at ticks 1200 and 2400, both looks): painted forest, water and cliffs meet cleanly;
  unpainted tiles show as the original beside them.

**Second round (Nov 9):** the 20 remaining primary sheets sent (25 requests, 5 of them retries: 09, 10, 20, 12, 02; no usage
warning, no limit hit). Atlas folder restored, then `cut --cache --edge-aware --exclude <14 tiles>`: 70 ground tiles kept
byte for byte, 121 new ground, 7 layer-1, 11 layer-2 (`0-2.webp`, `1.webp`, `2.webp`; 1.4 MB in all).
- **Sheet quality** (tile NCC median, after the retry where there was one): forest 19 0.73, 16 0.52, 14 0.95, 09 0.24
  (first try 0.10: stayed weak); purple 08 0.66, 20 0.94; hull 01 0.87, 15 0.89, 18 0.78, 11 0.77, 07 0.71, 02 0.98, 10 0.06
  (two tries, both failed to register); flesh 17 0.83, 04 0.49, 12 0.98; layer 2: 02 0.81, 01 0.57; layer 1: ctx-2 1.00,
  ctx-1 0.70. Sheets 20, 15, 12 and 02 came back as near copies of the pixel blocks (blockiness 4.2-4.8, NCC 0.9+) even after
  an "anti-aliased, no pixel grid" retry on 20 and 02; the cut deblocks them. Hull prompts now say "flat game-map floor
  texture, not a ship or vehicle" (Gemini drew a ship in space for the same wording in `shapesw`); layer-2 and context
  prompts say "on a pure black background ... do not paint a cave, sky or scenery". The layer-1 prompts written by
  `mkprompts.py` had lost their "Repaint every piece" sentence (it replaced everything from the first parenthesis), so
  both contexts were resent with the full text.
- **Left to the original** (best candidate scored under 0.4): ground 86 111 127 566 567, layer 1 62 450 451 452 458 459
  467 (the other 7 are painted), layer 2 313 314.
- **Seams** (`check`, every edge): layer 0 0.865 across / inside (original continuous 0.823), bands 0.544; the 19,625
  edges between kept tiles 0.730 (continuous 0.729), the 17,611 edges that touch a new tile 1.018 (continuous 0.932),
  bands 0.617; layer 1 0.804 (continuous 0.801; only 5 edges); layer 2 0.398 (continuous 0.398), bands 0.678. Ground is
  above the ~0.6 target, but within 0.04-0.09 of the original's own ratio on this forest and hull texture.
- **In game** (`episode=2&main=M&seed=1&skip=T&freezeAt=T`, both looks; section numbers: 2-1 TORM main 2, 2-10 BOTANY A main
  21, 2-6 GRYPHON main 12, 2-12 BONUS main 24): 2-1 and 2-10 at t1200/t2400 (original | round 1 | round 2:
  `tyrian-scratch/terrain-shapesx/captures/compare-2-1-r2.jpg`, `compare-2-10-r2.jpg`), 2-6 t1500 and 2-12 t900
  (`compare-2-6-2-12-r2.jpg`, original | HD). Forest, water, cliffs and hull slabs line up with the original; the repainted
  hull slabs on 2-10 are darker steel with a faint teal halo at their edges, and 2-6's central hull block shows a green
  tint (found and fixed below). Left tiles show as the original beside them. terrainArt
  and terrainHd tests pass. Not looked at: 2-2, 2-11, 4-13, `&dpr=0.3`, fallback with a tile removed.

**The teal rim (found after round 2, fixed with `terrain_hd.py rimfix`):** the 2-6 tint and the 2-10 halo were one
thing, and not a shader recolouring (`paletteTexture.ts` / `terrainMaterial.ts` of D111 changed nothing; with the
whole palette path bypassed the tint stayed). The atlas itself had it: the seam strips (the outer 4 texels, solved
across tile pairs) took the lighter cyan of the original's edge pixels, so every blue-grey plating tile carried an
8-texel ring greener than its interior (green sits 0.78 of the way from red to blue in the ring, 0.56-0.60 inside:
tile 12 edge [41,66,73] vs inside [40,54,65]). Tiled, the rings drew a teal grid, and the 2-6 block read as a green
rectangle. `fix_rim` lowers the green to the plating's ratio (`RIM_RHO` 0.58) within 12 texels of the edge, fading
over 12 more; red and blue stay, so the rim keeps its light. It is one colour function of the texel (two tiles that
met in one edge colour still do) and runs only on tiles whose interior is blue over green over red (jungle, rock
and water come back as they were). It changed 95 of the 191 ground tiles (82 in `0-2.webp`, 13 in `0.webp`),
re-encoded at the same layout and quality 92; layers 1-2 don't have it. `tests/tools/terrain_hd_test.py` (RimFix).
The same pass is worth running on a new tileset after its cut (`rimfix <tileset> --dry-run` lists the tiles).
After: 2-6 t1500 and 2-10 t1200/t2400, original | HD, `tyrian-scratch/terrain-shapesx/captures/r3/compare-2-6-r3.jpg`,
`compare-2-10-t1200-r3.jpg`, `compare-2-10-t2400-r3.jpg`: no tint, no halo.
## D111 — `shapes)` HD terrain: all 112 ground tiles and all 14 layer-1 rock tiles, from 16 Gemini sheets (two rounds)

2026-11-04

**Decision:** the tileset `shapes)` (episode 4's SURFACE, CORE, SIDE EXIT, UNDERDELI, LAVA EXIT, DESERTRUN, LAVA RUN,
BRAINIAC, TIME WAR, SQUADRON: 4.4-4.7, 4.9, 4.10, 4.12, 4.15, 4.17, 4.18) gets an atlas,
`public/art/terrain/shapes)/` (`0.webp`+`0-2.webp` ground, `1.webp`+`1-2.webp` layer 1, 0.9 MB), from D83's pipeline: `inventory`, `sheets`,
Gemini, `cut --edge-aware`, `check`. Round 1 (first commit) painted 89+7 tiles and stopped at the Pro limit; round 2 (Nov 9) sent the six remaining sheets and merged
  them over the kept atlas (`git checkout` of the folder, then `cut --cache --edge-aware`: 89+7 kept byte for byte, 23+7 new).
- **Folder name.** The tileset's letter is ")" (`data/shapes).dat`); `tileset_levels` strips "shapes" and `parseTileId` only
  strips ".dat", so the folder is literally `shapes)` and nothing needed changing. Quote it in shells:
  `--tileset 'shapes)'`. The dev server serves `/art/terrain/shapes)/manifest.json` (200) and the levels draw it.
- **Kinds.** Layer 0: 112 terrain + 1 empty; layer 1: 14 terrain (rock chunks on lava, a dark-blue fill) and 35
  structure (left to models); layer 2: all 24 structure, nothing painted.
- **Gemini:** 13 answered requests for 10 answers kept (ctx-l1-brown-2, region-l0-02, 13, 09, 10, 05, 01, 07, 03, 04),
  3 retries: 02's first send came back 4:3 (the default ratio; not downloaded), 02's second and 13's first went
  out with the image not attached (the paste raced the page load) and came back as invented art. Then the Gemini usage limit hit while sending region-l0-14 ("Continuing with Flash-Lite";
  limit resets Nov 4 11:05 PM); stopped there. Prompts named each sheet's real material (SEND.md's group labels were
  wrong: "asteroid rock" for a desert with metal bases, "flesh" wording made Gemini rearrange the red cells, so the
  text now says to keep every cell and patch where it is) and add "do not rearrange, invent or move anything".
  Workflow lessons: set the aspect ratio to 1:1 on every request (the default is 4:3), and check the upload
  (`user-query img` count 1) before pressing Return. Registration: fit 0.99+ on every sheet but the invented first
  02/13 (resent), tile NCC median 0.98-0.99 (0.56 on 04, a low-contrast dark brick floor).
- **Seams** (`check`, all ten maps): ground 0.558 (continuous original 0.545), bands 0.501; layer 1 1.059
  (original continuous 1.048: its tiles are alpha rock shapes over a flat fill, so the ratio is the original's own).
- **Weak cells:** NCC < 0.5 on tile 0:79 only. Uncovered, falling back to the original: ground 63 70 73 74 75 76 85 86
  92 (dark deck, sheets 08/12/14) and 130-134, 140-144, 150-153 (purple plates, sheets 06/11); layer 1 31-35, 41, 42
  (sheet ctx-l1-brown-1). Next round: send region-l0-14, 08, 12, 06, 11 and ctx-l1-brown-1 (6 requests), then `cut`
  again with `--cache`; keep the atlas (merge) or restore it first to re-pick among all answers (doc §3).
- **Shader fix, found in game: LAVA EXIT's pink.** On 4.9 the pink fuzzy patches drew as flat saturated red. 4.9 runs
  water_filter with hue 7 (smoothie 2, below the ground's ceiling); the original draws the patches with palette 5's
  salmon bank (0x46-0x4b), which water_filter leaves alone (`index & 0x30 == 0`), and the lava with 0x7x. The HD shader
  (D57) gave every painted texel the hue ramp's index (16 + shade, D95 added only grey 0 + shade), so the pink was
  recoloured to 0x70 + shade: red. Now each texel's bank is the raw palette's nearest colour's:
  `PaletteTexture.indexLut` is a 32³ sRGB cube (256x128 R8 texture, built on first use per palette, ~22 ms, cached)
  holding the nearest index by redmean distance, and `terrainPalette` takes `bank + shade` (near-greys still take bank
  0, D95). Only the bank matters, and only for water_filter's exception: the hue filters replace it and untouched
  texels keep their painted colour, so levels without water_filter draw exactly as before. Checked against the
  original (blurred mean |HD - original|, before -> after): 4.9 t300 12.4 -> 4.4, t900 18.3 -> 4.7 (the patches 34-37
  -> 3); SAVARA IV (episode 4 `main=16`, water_filter hue 3) t1200 6.4 -> 4.2, t2500 5.7 -> 4.4: its water's lighter
  blues now keep their painted colour (about half the original's water pixels there are the exempt bank 0x80, the
  rest 0x3x), where all of it was darkened to 0x30 + shade before; the grey floor is unchanged; TYRIAN (episode 1 `main=1`) t300, t1500 identical (no hue stage). Captures:
  `tyrian-scratch/terrain-shapes-paren/captures/pink-fix/` (`compare-4-9-fix.jpg`, `compare-regression.jpg`: original
  | HD before | HD after). Test `tests/render/paletteLut.test.ts`. The flat sprite art (`spriteArtLayer.ts`, D42)
  still takes 16 + shade; nothing of it was seen under a water_filter, so it is left alone.

**Checked** in game (`?debug=play&episode=4&main=2` (4.4) and `main=31` (4.9)`&seed=1&skip=T&freezeAt=T`, T 300 and 900,
`&terrain=original` for the other half): the desert and metal plating on 4.4 match the original's layout; 4.12's lava
reads well. Captures: `tyrian-scratch/terrain-shapes-paren/captures/compare-4-4.jpg`, `compare-4-9.jpg`. Tests
`terrainArt` + `terrainHd`: 21 passed. Answers, sheets, prompts, `cands.pkl`: `tyrian-scratch/terrain-shapes-paren/work/` (not in git, D3).

**Round 2 (Nov 9):** sent region-l0-14, 08, 12, 06, 11 and ctx-l1-brown-1 (7 requests: region-l0-06's first answer came
back as invented art and was resent once; no usage warning, no limit hit). Fits 0.69-0.98 (06's first try 0.24), tile
NCC medians 0.70-0.86 (14 lava 0.86, 08 dark deck 0.98, 12 0.81, 11 purple 0.70, 06 0.82, ctx-l1-brown-1 0.98). Every
ground and layer-1 tile now has a painting. Seams after the merge (`check`, all maps): layer 0 0.564 overall (original
continuous 0.548; the 4,568 edges touching a new tile 0.637 vs continuous 0.588), bands 0.534; layer 1 1.178 (continuous
1.170, alpha rock shapes over a flat fill, the original's own ratio). Weakest new tiles (cut-report score): ground 0:143
0.50, 0:150 0.58 (purple, sheet 06), layer 1 31-35 0.58-0.96. Blockiness on the dark-deck and purple sheets is 1.8-4.4
(Gemini kept the pixel blocks there; the cut deblocks). In game 4.4 and 4.9 at t300/t900 read cleanly; captures
`tyrian-scratch/terrain-shapes-paren/captures/compare-4-4-r2.jpg`, `compare-4-9-r2.jpg` (original | round 1 | round 2).
## D109 — A debug console for testing: cheats, hidden settings and level jumps, through the game's own state and flow

**Asked:** a console to type cheats, switch hidden settings and change or skip levels, on desktop and phone,
in the deployed build too.

**Decision.**
- **Ways in.** Options → **Debug console** (a "Testing" row on the one settings screen, so the title's
  Options, the shop's "All settings…" and the pause menu's Options all have it, D99/D102; the settings
  screen closes first, so the console sits right over the title, shop or pause screen), **backtick** anywhere
  (in a running level the loop pauses first, as for the pause screen), and `tyrianConsole.open()` /
  `tyrianConsole.run("line")` in devtools for scripted checks. Esc, backtick, Close or B closes it; a level
  resumes.
- **The screen.** A framework screen (`id: "console"`) in the menus' bronze-rimmed umber pane (D85, the HUD's
  look, D61), at the top of the window over the paused game: a monospace scrollback in a phosphor well, the
  input line under it with history (Up/Down, kept in this browser) and Tab completion (commands, then each
  command's words: ports, sides, styles, episodes, level names). On touch screens Tab, ↑, ↓ and Run are
  buttons that don't take the focus from the field; the field takes the on-screen keyboard and the screen
  fits itself to `visualViewport` (the part above the keyboard); the scrollback scrolls (D98). `help` lists
  every command with its arguments (two columns, or one under the other on a phone).
- **Cheats act through the sim**, so they behave as the real game's: `god` is the original's invulnerability
  (`youAreCheating`, F2 F3 F6); `armor N` goes through JE_drawArmor's cap (28); `shield N` up to
  `shield_max`; `heal`; `credits N`; `weapon front|rear ID [power]` as a pickup (shot pattern reset, the
  message bar's "You got the …", `calc_purple_balls_needed` since lives alias the power); `power N`;
  `sidekick left|right ID` set up by JE_drawOptions; `kill` kills each destructible enemy on screen (not
  armour 255, not pickups) through `destroyEnemy`, the shot loop's kill branch moved into a function of its
  own (no change to the loop: the bot traces match); `skip`/`next` is the original's skip-level cheat
  (`cheatSkipLevel`, moved out of JE_mainKeyboardInput), so the level ends as completed 40 ticks later.
  `weapons` and `sidekicks` list the ids. The HUD updates while the console is open.
- **Levels are sections.** `levels [episode]` numbers each section with an `]L[` 1..N in script order
  (TYRIAN's normal and hard variants share section 3: one entry) and shows its section (the harness's
  `main=`, g.mainLevel) and tyrianN.lvl number. `level [episode] <number|name|s<section>>` takes the list's
  number, a name (any case, spaces ignored, a unique start is enough; a shared name such as SAVARA takes
  the first and says so) or a raw section. The jump goes through the game flow: in a level the loop ends
  with outcome "jump" and run.ts does JE_initEpisode and loads from that section (JE_loadMap plays its
  `]L[` straight away; items carry over); in the shop the sim's own exits (mainLevel + jumpSection, the
  map's choice, or gameLoaded for another episode, as loading a game from the shop does); on the title a
  one-player full game starts there. `shop` goes to the item screen whose map leads to this level (a section
  with `]I[` and a `]G[` naming it), or from the title to a new game's first. A jump needs the console right
  over the title, pause screen or shop, not over a screen opened from them.
- **Settings and looks.** Each shows its value without an argument. Real settings go through the setters
  Options uses and are saved by `savePrefs` (terrain, camera, interface, resolution; music and sound styles
  keep themselves). The URL-only looks switch live in the renderer for this page (`vfx`, `sprites`, `bg`;
  structures already placed keep their look). `fps`/`perf` toggles a corner overlay (fps, frame time, tick,
  speed, draw-list size; remembered). `tick` shows the level's tick count; `speed N` (0-8) scales the time
  the fixed-step loop accumulates, so ticks stay the classic fixed ones and only more or fewer run per
  frame (0 freezes; the effects' clock follows); `seed` shows the start-up seed, `seed N` reseeds mt_rand.
  `reset` puts the settings, looks, styles, speed and overlay back to their defaults (not volumes or keys).
  `clear`, `close`.
- **Bundle.** `src/app/consoleBridge.ts` (the place, hooks, speed, ticks, the backtick key) is in the main
  bundle; the console (`src/debug/console/`, ~21 kB) loads on first use.

**Not covered:** the `?debug=play|level` harnesses (their own loops; their URL params still work) and
two-player games' player 2 (the cheats act on player 1).

Tests: `tests/debug/console.test.ts` (parser, completion, history, level numbering and sections, the
commands on a real level: armour cap, god vs a lethal hit, a fitted gun firing, sidekick setup, kill, skip
to a completed level), `tests/app/options.test.ts` (the row). Captures: `tyrian-scratch/debug-console/captures/`
(`d-*` 1920x1080, `p-*` 390x844 touch through Options on the title and the pause menu, `f-*` shop jumps and skip).

## D110 — Shop lists in the debug console: `shop all` and per-category edits, through an override layer the item screen reads (extends D109, D85, D98)

**Asked:** console commands to see how the shop looks with long lists: an unlocked shop selling everything the
real game sells, and temporary edits of one category's list, without breaking the sim's C-shaped lists.

**Decision.**
- **Commands** (the `shop` command's subcommands; `shop [episode]` still goes to an item screen, D109):
  `shop all [on|off]` (no argument: the state), `shop list [category]`, `shop items <category> [filter]`,
  `shop set <category> <id|name…>`, `shop add|remove <category> <id|name…>`, `shop clear <category>`,
  `shop reset [category]`. Categories are the Upgrade Ship rows in the shop's order and words: `ships`, `front`,
  `rear`, `shields`, `generators`, `left`, `right`, with aliases (`ship`, `f`, `front-gun`, `shield`, `gen`, `ls`,
  `rs`, …; case, spaces, dashes and a plural "s" don't matter). Items by id or name (whole or a unique start;
  `zica-laser`, `"Zica Laser"`); a name two items share (the two Vulcan Cannons) takes the one the real game sells
  in that category if only one is, else asks for the id. Tab completes subcommands, categories, ids and names.
  `help shop` lists the subcommands.
- **`shop all` is computed from the data**: every `]I[` in levels1-4.dat (61 item screens), its 9 lines read by
  the sim's own `itemAvailLine` (factored out of JE_loadMap's `]I[`, so the sim and the console parse them the
  same way; a test checks each of episode 1's screens against itemAvail as JE_loadMap leaves it). The union per
  category, in the merchant's order (ascending, None last): ships 9, front 18, rear 13 (with None), shields 9,
  generators 6, left 23 and right 30 sidekicks (with None). The shop rows Engine and Armor are never shown
  (itemAvailMap skips them). Nothing outside a shop list gets in: the ships no item screen sells (Stalker 8,
  U-Ship, Silver Ship, Nort Ship), the internal "Miscellaneous Option Weapons" port, the joke guns (Banana Blast, HotDog),
  the Nort and rear-only guns in the front list, Companion Ship Quicksilver and the HXS Class C shield. Shop
  lists that the data does have stay, odd ones included: SuperCarrot (episode 2), Tropical Cherry Companion and
  the episode 4 secret-route screens (The Stalker 21.126, Beno Protron System -B-); the front-firing sidekicks
  only in the right list, as the data sells them. Edits may use any id in the category's item table (with a note
  when no shop sells it there): front 1-42, rear 0-42, ships 1-13, shields 1-10, generators 1-6, sidekicks 0-30.
- **An override layer, not bigger arrays.** `g.itemAvail[9][10]` / `itemAvailMax` stay exactly the level's: the
  item screen reads every list through `availList(row)` / `availCount(row)` in `game_menu.ts` (the update's
  weapon powers, the cursor skip, the mouse's cost check, JE_genItemMenu, Enter's "Done" power, the rows), which
  give the console's list for an overridden row and the C arrays otherwise. JE_itemScreen_init's merge of
  last_items still runs on the real arrays (factored sort `sortMerchantRow`, same loop); the console's lists get
  the same treatment: what the player has (last_items and items) is added and the list sorted, so the screen
  always offers the item owned, as the game does. Buying, selling, power, Escape and the preview are the C's own
  code on the longer list; `temp_weapon_power` has room for any u8-length list. With no console list every read
  is the C array's: `shop reset` restores normal behaviour exactly, and the C cross-check trace still matches.
- **A change while the shop is up** applies at once (`JE_itemScreen_listsChanged`): in an Upgrade Ship list the
  list is left as Escape leaves it (loadout and credits as when it opened) and opened again on the new list, with
  no sounds. Turning lists off after buying an item from them leaves the level's lists as they are; that item is
  listed from the next item screen on (last_items), like anything the player flew in with.
- **Lifetime: until `shop reset` (or `shop all off`), through level changes and new games**, for the page only.
  Chosen over "until the level changes" so a selection can be checked across several item screens and jumps
  (`level`, `shop`) without retyping, and so `shop all` and edits follow one rule. Nothing is stored: not in
  localStorage, not in saved games (the lists aren't part of a save); an item bought from a console list is
  the player's like any purchase.
- **Long lists in the UI.** An item list (`.shop-list--items`, only in the Upgrade Ship lists; the game's own have
  at most 7 rows) scrolls inside the menu pane: on desktop it is capped at the window less the panes' other parts
  (`100dvh − 8vh − 13rem`, at least 18rem), so the title, the simulator, the credits/power/upgrade readouts and
  the help bar stay in view instead of the whole panel scrolling them away; on phones at 56dvh, so the simulator
  is a short swipe below, and a swipe past the list's end carries on down the panel. `reveal()` already brought
  the cursor's row into view and now scrolls the list. Keys and pad wrap through all rows (the C's); a tap or
  click on any row works; short windows (≤ 520 px tall) keep the panel's scroll (D98).

**Checked** (headless Chrome, `tools/cdpshot.mjs` with `tyrianConsole.run(...)`, and touch emulation with swipes):
1920x1080 and 390x844 with `shop all` on the front-gun list scrolled to its middle, a `shop set` list, the 31-row
right-sidekick list opened on the owned None at its end, swiped, a row tapped twice and bought, the swipe chaining
to the panel. Captures: `tyrian-scratch/shop-cheats/captures/`. Tests: `tests/debug/console.test.ts` (categories
and aliases, completion, the union: counts, ranges, order, nothing never sold, the sim's own lists; set, add,
remove, clear, reset, items; buying the Widget Beam from `shop all` as a normal purchase; off restoring the
level's lists exactly; lists lasting through later item screens; every row of a 31-row list reachable).

## D114 — Episode-1 QA bugs: the glass orb's paint follows smooth edges, HD terrain's near-grey test is in sRGB, the gem blocks are one colour (extends D103, D95, D111)

2026-11-10

From `tyrian-scratch/e1-qa/REPORT.md` (issues 3, 5, 7), checked on main before changing anything.
- **DELIANI glass orb (1.5, `assembly-newshu-129`).** The same model D103 fixed, not a regression: D103 removed the
  speckle, but the glass was still painted cell by cell on a 20x20-per-face cube sphere, so the green mass and the grey
  lobes showed as hard pixel squares (about 1.6 sprite px each), which still read as a corrupt texture. Now
  `PartField` blurs each part of the (D103-smoothed) part map (Gaussian, sigma 0.9 px), samples it bilinearly and takes
  the strongest part; cells an edge between parts runs through are split 3 ways per edge (`subdivide_edges` with grid
  fill, new vertices put back on the ball) and every face is painted by its centre. Same parts, colours, states and
  frames; the eight painted GLBs grow from 32-47 KB to 57-119 KB (the purple states are unchanged).
- **SAVARA V (1.17): jungle and shore stayed green and brown under the blue water.** Not the clouds (D107's clouds
  match the original at t300). SAVARA V runs water_filter (hue 3) over the ground; the HD shader (D95) gives a texel
  the exempt grey bank when its chroma is under 0.04, but measured that chroma on the *linear* colour, where every dark
  colour is near grey: 44% of a jungle tile's texels (the original's tile has 6% grey pixels) and the dark shore
  browns kept their painted colour. The test is now on the sRGB colour (the same 0.04), and `terrainBank` takes that
  sRGB colour. Blurred mean |HD - original| (1920x1080 playfield): 1.17 t5800 10.0 -> 8.8, t8400 12.9 -> 11.2, t2900
  2.8 -> 1.6; regressions: SAVARA IV (4.16, D95's grey floor) t1200 3.7 -> 3.5, t2500 3.8 -> 3.7, the floor stays grey;
  LAVA EXIT (4.9, D111's pink) t300 4.3 -> 2.5, the pink stays pink and the dark lava now takes the red hue as the
  original does. Levels without a hue stage draw as before.
- **WINDY (1.14) seam.** The orange gem block (`newshm-17`) and its siblings (`-15` green $, `-53`, `-55`, `-153`, all
  `lib_b078.tile_materials`) painted the sprite's lighting: a dark red front band (the seam where the block overlaps
  the red block below it, 1 px apart as in the C) and yellow rim-light patches. Every role now takes the body colour,
  as `newshm-1` (the red block) already did (art rule 2). Geometry unchanged.
- **Already fixed on main, not changed:** SOH JIN's bell turrets have no sand pad (D103). The key there
  (`tyrian.shp#10` 243, flat art from D94) never had a tile rectangle: what shows round it is the sprite's own black
  drop shadow, painted into the flat art (stair-stepped). Left as is; a cutter rule that drops the shadow indices
  (160, 161) from the silhouette would remove it.

Captures: `tyrian-scratch/e1-qa-bugs/` (`bug1_*` orb, `bug2_*` SOH JIN, `bug3_*` and `cmp_*.jpg` SAVARA V and the
regression levels: original | before | after, `bug4_*` WINDY).

## D115 — The purple machines build the broken sockets their tiles paint; the scorch over them is only the fresh break (extends D96, D47)

2026-11-10

**Context:** the user compared TYRIAN (1.3) with the real OpenTyrian: when a cap of the island machines is shot off,
the original shows a cracked, broken stone where it sat; ours showed an intact octagonal boss (the orb) or a ringed dome
(the 2x2/2x3/2x5 blocks, the cross) under D96's procedural scorch, which read as a decal on an intact socket. D96 had
found why: the original stamps nothing; the background-3 tile under each cap *is* the broken socket, hidden while the
cap's sprite covers it.

**Options:** (a) broken-socket geometry in the machine models, shown per cap when that cap dies; (b) D96's decal
upgraded to a mesh or decal matching the crack art; (c) the models' bosses built broken, always, as the tiles paint
them. (a) needs per-instance, per-part visibility in the instanced structures (D34) plus a reliable death record per
cap (the harness's `skip=` only renders its last ticks, saves and level starts never see the deaths). (b) can only add
over the intact boss, not take it away, and still depends on seeing the death. (c) is what the original does: no
runtime state, every machine instance and cap position at once, every camera tilt (the cap's model covers its socket
on screen as the sprite covers the tile, D6).

**Decision:** (c).
- `assets/blender/tiles/lib_sockets.py` (numpy only): per boss tile (155-157, 165, 167, 175-177) the cracks read off
  its art as polylines (`CRACKS`; ends near the rim run on to it), plus its darkest pits (palette 80-83); the octagon
  minus those, rasterised at 8 samples per px, gives the chunks (outlines simplified to px/3); each chunk takes the
  palette index its pixels mostly paint, kept to the stone's 86-89. `--overlay out.png` draws them over the tiles.
- `lib_tyrbld.Structure.broken_sockets(z0)`: a socket wherever the pattern has a boss tile, at the tile's own boss
  centre (`BOSS_AT`): each chunk a prism with a chamfered top, tilted (rising 0.012 per px outward: the middle sagged
  where the cap was torn out, plus a turn of its own), dropped up to 0.13 and pushed up to 0.5 px outward, over a dark
  floor (index 82) at 30% height that shows in the cracks. Tops ≤ 0.30, under the enemies' 0.33 (`check()`).
  Hard-surface prisms, flat shaded; undersides closed and plain.
- The orb, the 2x2/2x3/2x5 blocks and the cross call it in place of their bosses/domes/knobs. Their other parts are
  unchanged. The orb and the cross are baked from concept maps as before, but `lib_sockets.py --maps` sets the detail
  to neutral and the relief flat under every socket, so the sockets get occlusion only (art rule 4); the blocks were
  and stay plain (build-models.sh finds no maps for `tyrbld_purple_blocks.py`). Structure models draw no outline (D8),
  so no outline shell.
- The entries carry `brokenSockets: true`; D96's scorch layer takes the structure's mark kind
  (`StructureMark`: none / scorch / socket). Over a socket the painted crack network and the hole glow only while hot
  (about a second), and the soot is at 35%: the fresh break still flashes, then the modelled break shows. Other
  structures (bunkers, wreck, fortress, pits) keep the full D96 mark.
- A boss whose cell never carries a cap (the 2x5's last column) now shows broken from the start, as its tile does.

**Checked:** intact machine (all caps alive, t2560): mean |after - before| 0.017 per channel over the machine's
600x400 crop, 113 of 240000 px over 10 (the scorch's sparks). Captures in `tyrian-scratch/island-sockets/final/`:
`cmp-2560.png`, `cmp-2650.png`, `cmp-3300.png`, `zoom-3300.png` (before | after | `&bg=original&terrain=original
&sprites=original`), `closeup-socket-3300.png` (one socket, 4K); `model-cross.png`, `model-2x5.png` (Blender views).
GLB sizes (KB, before → after): orb 813 → 893, 2x2 467 → 463, 2x3 658 → 648, 2x5 1027 → 1010, cross 1278 → 1341;
triangles after: orb 10.1k, 2x2 4.9k, 2x3 7.2k, 2x5 11.4k, cross 15.4k.

## D116 — Episode-1 enemy rebuild: 32 models (about 40 inventory units) to the D65 hard-surface standard

2026-11-10

**Decision:** the 32 episode-1 enemy, boss and assembly items the scout listed from the inventory (still the older
`basic` look; most-seen first, by the bot run's ticks on screen) are rebuilt with `tools/workflows/model-flagship.js`
(full mode, blueprints for heroes; D65's recipe: hard-surface geometry, AO/roughness bake `"bake": "model"`, outline shell,
art rules 1-5). The scout merged items whose scripts share a lib only between themselves, so no two agents edited one
file: the wall-block family `newshm-1/15/17/53` (one new `lib_newshm_block.py`; `lib_b078` stays for `newshm-55/123/153`),
`assembly-newshi-154` + `newshi-19` (`lib_b069.py` deleted, no user left), the twin pads `newsha-93` + `newsha-17`,
and `assembly-newshu-129` (one script, 4 units). No shared lib (`lib_b073`, `common.py`, ...) was edited. Damaged
frames the intact models now draw (D87): `newshs` 241/243/279/281, `newsht` 117/123/157/159, `newshu` 239 (moved to
`newshu-93-f2`).

| Model | Tier | Top-view IoU (finisher, worst frame) | Review IoU | Score |
|---|---|---|---|---|
| newshm-1 (+15, 17, 53) | hero | 0.9759 | 0.9759 | 8 |
| assembly-newshi-115 | hero | 0.9847 | 0.9847 | 6 (fix round, shipped, see below) |
| assembly-newsht-39 | hero | 0.963 | 0.9969 | 8 |
| assembly-newshi-154 (+ newshi-19) | hero | 0.9642 | 0.9607 | 8 |
| assembly-newshc-197 | hero | 0.9678 | 0.9557 | 8 |
| newsha-93 (+ newsha-17) | standard | 0.9519 | 0.9519 | 8 |
| newsh-caret-171 | standard | 0.9237 (sub-pixel; grid 1.0) | 1.0 | 8 |
| assembly-newshf-81 | hero | 0.9896 | 0.9896 | 8 |
| assembly-newshs-7 | hero | 0.9934 | 0.9934 | 8 |
| assembly-newshi-243 | hero | 0.9678 | 0.9678 | 8 |
| assembly-newshc-283 | hero | 0.974 | 0.974 | 7 |
| newshs-191 | standard | 1.0 | 1.0 | 8 |
| newsha-169 | standard | 0.9656 | 0.9656 | 8 |
| newshe-153 | standard | 0.9755 | 0.9782 | 7 |
| assembly-newshs-165 | hero | 0.986 | 0.986 | 8 |
| newshj-19 | standard | 0.9367 (sub-pixel; grid 1.0) | 1.0 | 7 |
| newshd-275 | standard | 0.9792 | 0.9792 | 8 |
| assembly-newshm-45 | hero | 1.0 | 1.0 | 8 |
| assembly-newshp-267 | hero | 0.994 | 0.994 | 8 |
| assembly-newshd-45 | hero | 0.962 | 0.962 | 7.5 |
| newsha-199 | hero | 0.951 | 0.9503 | 7 |
| newshs-229 | standard | 0.9955 | 0.9955 | 7 |
| newshf-39 | standard | 0.9953 | 0.9953 | 8 (fix round) |
| assembly-newshs-39 | hero | 0.9664 | 0.97 | 8 |
| newshe-277 | standard | 0.9825 | 0.9825 | 8 |
| newshf-1 | standard | 0.974 | 0.974 | 7.5 |
| assembly-newshd-39 | hero | 0.9763 | 0.9763 | 7 |
| assembly-newshu-129 | hero | 0.9679 | 0.9648 | 7.5 |
| newshe-233 | standard | 1.0 (grid) | 0.9446 (sub-pixel; grid 1.0) | 7 (fix round) |
| assembly-newshp-165 | hero | 0.9858 | 0.9858 | 8 |
| assembly-newshu-79 | hero | 0.9877 | 0.9907 | 7.5 |
| newshs-11 | standard | 0.994 | 0.994 | 8 |

**Merged with D114 (#145, which changed the same models while this ran):** the DELIANI orb (`assembly-newshu-129`,
units newshu-91/93/129/131) takes this rebuild, not D114's repaint: its continents are painted smooth on the new
geometry (coordinator's review). The WINDY gem blocks `newshm-15/17/53` take this rebuild (`lib_newshm_block.py`), which
keeps D114's rule: the shell is one body colour (the sprite's flat-top index), no painted rim light or dark front band;
the only dark parts are geometry (the inset foot plate under the shell and the small lifting sockets). WINDY at tick
1026 shows no seam where a gem block overlaps the red block below (`tyrian-scratch/e1-enemies/merge-check/
windy_1.14_t1026.png`; `windy_seam_cmp.png`: before D114 | D114 | this). `newshm-55/153` keep D114's `lib_b078` fix.

31 shipped by strict review (3 of them after a fix round); `assembly-newshi-115` is shipped by the coordinator's call.
**IoU gate:** `tools/sprite_mask.py`'s accept line is `iou_rule_grid` ≥ 0.95 (OUTLINE-BORDER.md); three small models
miss 0.95 only on the sub-pixel `iou_rule`, from the smoothed diagonal steps of a tiny sprite, with grid IoU 1.0 on
every frame: `newsh-caret-171` (0.9237, a size-1 sprite), `newshj-19` (0.9367 on frames 38 and 76, size 1) and
`newshe-233` (0.9446, 16x15 px). The reviewers shipped them on the grid value.

**Follow-ups (known):**
- `assembly-newshi-115` (SAVARA) was built here as a dome fortress, which was wrong: it is a blimp. Redone in D120.
- `assembly-newshc-283`'s run ended `ok: false` only because of the pillar head `newshc-77` (`newshc-77.py` with
  `lib_b110.build_head`/`head_materials`), outside the item's scope: recess the eye socket (a dark disc with the eye in it,
  not thin ellipsoids on the dome), raise the ball/stem roughness to ~0.42-0.45 (now chrome), and make the neck a collar
  on the pillar axis (h = 5 px). Its own five models pass.
- `assembly-newshm-45` stays `basic` in the regenerated inventory: the unit also draws frames 7/9/11, which
  `newshm-7.json` maps to the older `newshm-7.glb` (`newshm-7.py`, lib_b073), and the item rebuilt only its six pieces
  (45/47/49, 83/85/87). Rebuild `newshm-7` to match. The other 39 units of the batch are `flagship` now.
- `newshm-55/123/153` still use `lib_b078`; move them to `lib_newshm_block.py` (variants plus emblems) so the family
  matches.
- `src/viewer/assemblies.json` has no layout for `assembly-newshs-165`, `-newshm-45`, `-newshs-39`, `-newshp-165`, so
  `?viewer=` can't show them whole (the catalogue writes that file; regenerate with `npm run catalogue`).
- `tools/sprite_mask.py` can't score `newshi-19` (it counts the dark browns 64/65/66/161 as ink on frame 19 and finds
  no ink on 76/95): the ink set should be per sprite.

**Cost:** 198 agents (1 scout, 19 blueprints, 51 designs, 19 judges, 54 finish/fix, 54 reviews; first finishes on
Sonnet, the rest Opus), 27.4M subagent tokens, about 5.5 h at `maxAgents: 8`; the fix round (`fix-round.js`, 3 items)
8 agents, 0.93M tokens, about 45 min. Sheets: `tyrian-scratch/e1-enemies/<name>/final/` and
`.../fixround/<name>/final/` (not in git, D3).

## D117 — Refit and outline-shell fixes: the level-1 flagship's halves end inside their own sprites, five shells held inside

2026-11-10

**Problem:** a visual audit of D88 and D92 (`tyrian-scratch/refit-audit/`) found artefacts the IoU gate
cannot see:
- **assembly-newsh4-123 / assembly-newsh4-81** (`lib_b065.py`, used only by these two; the boss
  assembly-newsh4-124 and its wrecks don't import it): D88 cut the joined model of each piece back
  to its own sprite's rows in the 4 rows the two halves share (per column, `trim_overlap`). The
  cut went through the model after `cull_hidden`, so it was no longer closed: open sections, sliver
  fragments and stair steps along -123's front and -81's rear. The outline shell kept the piece box,
  so past the cut it stood out as a black slab with an ink loop, visible in `?debug=models` at game
  scale. The same cut removed -123's red-rimmed nozzles (the shoulder pods' aft ends).
- **D92 enemies, outline on only:** assembly-newshf-195 ink wedges on the dome's right half,
  newshs-171 two ink slits beside the hub, newshs-269 an ink sheet behind the chin (rear right in
  the 3/4 view) and a wedge at the left seam.
- **newshf-230, outline off:** a pale sliver through the red rail at the bend.

**Decision:**
- **Each half of the flagship is built its own way, part by part, before the join** (`clip_rules`,
  `clip_part`). Every closed part that crosses one of its assembly's lines is cut there and capped;
  a part reaching less than 0.4 px inside is dropped whole (no slivers). Parts cut on the same line
  whose caps would overlap are cut 0.03 px apart, so no two caps are coplanar (they z-fought, and
  the occlusion bake stippled them). The piece boxes then cut nothing along the shared rows.
  - **Each part ends straight, at its own length.** On the shared row (-81's row 27, -123's row 24,
    half colour and half ink in both sprites) a part ends at the row's near or far edge, whichever
    its own pixels of that row vote for: colour inside the ink +1, ink or nothing -1, free 0. This
    replaces D88's per-column stair steps and keeps the rule IoU over 0.95 per piece.
  - **Side lines:** -81's body parts (wing roots, torso, armour) stay inside cols 14.6-46.4 (its
    rows 26-27 are ink beside the pods); -123's head parts (arm, armour block, core stubs) inside
    15.6-46.4, and its wings' leading edges inside the sprite's diagonal above row 29. The lower
    sprite is symmetric about column edge 31, the upper about 30.5.
  - **The shoulder pods** are their own part: -81 keeps them whole (they end at row 27.95, in its
    box); -123 drops them.
- **-123's nozzles are back, scaled in:** a red lip round a dark throat, a red band, the grey housing
  and a tapered back, the pods' section (`pod_nozzles`). They sit on the two free ink pixels the
  lower sprite draws for each pod's end (cols 10-11, 50-51), radius 1.1 px, rows 24.0-25.4, so they
  add no pixel to its top view. Each is mounted on a thin rod (0.34 px across) to the arm's cut end,
  so it does not float. With -81 present they sit inside its pods.
- **D90's shell for these models:** 0.03 voxels, held 0.004 inside.
  - **The flagship:** `lib_b065.outline_shell` (it keeps every outer island, so horns, claws, arcs
    and nozzles keep their ink) takes `inside`. It is made from each half's own build, so it ends
    where the model does.
  - **assembly-newshf-195** at 2000 faces (1000 left an ink streak on the dome).
  - **newshs-171** at 3000 faces.
  - **newshf-230:** D90's shell too; it also clears ink ticks beside its studs.
  - **newshs-269 keeps its built shell**, held inside by the same Shrinkwrap. Its crest comes down
    to the chin's channel floor (0.45) and to 1.45 over the plates' seams. A voxel shell, even D90's,
    drew ink specks round the dome's well and the drum.
- **newshf-230's sliver:** where the band of rib B is clipped by the curved deck next to its panel
  seam (and where the arm meets that seam), offset_polygon's step carried a short edge's top past
  itself, so the top ring crossed itself. `hold_offsets` collapses such a flipped edge where the
  offset lines on either side of it meet, repeating until no top edge runs backwards; no other
  vertex moves.
  - Its top seam moves from 0.55 to 0.6 px. At 0.55, an 8x top render still covered half of row 0
    (rule IoU 0.9316); at 0.6 it is D92's 0.9761.

**Result** (rule IoU on the grid, `tools/sprite_mask.py --measure` of top renders of the exported
GLBs, outline shells left out, 8x):

| Model | after | before (main) |
|---|---|---|
| newsh4-81 / -83 / -85 | 0.9521 / 0.9583 / 0.9875 | 0.9728 / 0.9731 / 0.9875 |
| newsh4-119 / -121 / -123 | 0.955 / 0.9618 / 0.9881 | 0.9583 / 0.9756 / 0.9881 |
| assembly-newsh4-81 / -123 (grid) | 0.97 / 0.9908 | 0.9885 / 1.0 |
| newshf-157 / -159 / -195 / -197 | 0.9924 / 0.9423 / 0.9969 / 0.9532 | same (shell only) |
| assembly-newshf-195 (grid) | 0.9986 | 0.9986 |
| newshs-171, all 4 frames | 1.0 | 1.0 |
| newshs-269 | 0.9901 | 0.9901 |
| newshf-230 | 0.9761 | 0.9316 (by this measure) |

- **The flagship's lower per-piece numbers** come from the straight part ends. D88's stair steps
  matched row 27 pixel for pixel.
- **newshf-159 below 0.95:** every pixel it misses is on the piece seam: the per-piece mask counts
  the dark column at the shared edge as border. Its grid is 0.9986; it was not changed here.
- **Ink outside the silhouette** (`inkout`, px beyond the normal ink width, 3/4 front):
  assembly-newsh4-123 20558 → 17, assembly-newsh4-81 2132 → 830, newshs-269 8171 → 2415.
- **Interior ink** (outline on minus off, per mille, front / 3/4 rear / top):
  | Model | before | after |
  |---|---|---|
  | -123 | 20.3 / 11.0 / 6.3 | 12.3 / 5.6 / 1.1 |
  | -81 | 32.5 / 21.2 / 8.6 | 12.2 / 7.6 / 4.3 |
  | newshs-171 | 5.5 / 5.4 / 9.1 | 0.04 / 0.06 / 0.0 |
  | newshs-269 top | 2.35 | 0.42 |

  What is left is ink where one part overlaps another, plus small marks at the right horn's crease
  (a fold in the horn's sweep).

**Checked:** `?viewer=` (top, game angle, 3/4 front and rear, outline on and off) and
`?debug=models` at 1920x1080, before and after.

**Options considered:**
- *Keep D88's per-column cut and only cap it:* the caps of a culled mesh don't close, and the stair
  steps remain.
- *One straight line per assembly:* row 27 is half ink, half colour, so either edge missed the 0.95
  per piece (-83 0.92-0.94).
- *Bigger nozzles:* the lower sprite draws only two ink pixels there; anything wider adds pixels.
- *A voxel shell for newshs-269:* specks round the well.

**Review:** sheets in `tyrian-scratch/enemy-refit-fixes/sheets/`: `before-after-closeups.png`,
`before-after-viewer.png`, `before-after-game-scale.png`. Measures in `measure/`. Fallback: revert
the five scripts and their GLBs.

## D118 — The Silver Ship rebuilt from its pre-refit parts on the inner edge; the Nort Ship's shell held inside

2026-11-10

**Problem:** the refit audit (`tyrian-scratch/refit-audit/`, `closeups/`) found two player ships that
look worse than their numbers:
- **Nort Ship:** black ink cracks across the white nose and cockpit plates in the hangar and the
  viewer, gone with Outline off. They predate D88. The shell (D51, 0.012 voxels) was remeshed from
  the culled hull: the open plates' both sides were wrapped, the shell followed the seams between
  the plates in, and its back faces drew ink across them (D90's cause, on the Talon).
- **Silver Ship, after D88:**
  - The fuselage's half width was fitted to the inner mask row by row (`FW` 4.12 → 4.95 → 4.25 →
    5.15 over rows 7-14), so the top plates' edges followed the pixel staircase: jagged and crumpled
    in the hangar.
  - The fuselage rode 3 px high to suit the banking frames (D88, before D93 forbade bank-only
    shaping) and covered the pods' bays: the sprite's two red light tubes per side (rows 18 and 20)
    showed as one thin bar.
  - The pods' outboard corners were made tight (0.35 fillets) so the rolled pods kept the banks'
    span: boxy red and grey blocks, seen when the ship banks.

**Decision:**
- **Silver Ship: the pre-D88 ship (afcea65b) pulled in one pixel, not reshaped.** The inner mask is
  the whole sprite's mask one pixel in at every row (nose rows 1-2 1.5, wing tip row 8 6.5, waist
  4.5, pods 8.5, the rear diagonal x + y = 29, the tail's end at row 26), so each part keeps its
  pre-refit shape and its outboard edge moves in, as one smooth curve through the inner mask's steps:
  - the nose: an ogive from row 0.95, the old outline 1 px in;
  - the wings: the leading edge on half width y - 2.1, a short tip at 6.5 (row 8), the trailing edge
    one straight sweep in through row 9 to the waist;
  - the pods: the old round section (`_pod_unit`, large fillets), outboard edge 1 px in, so 1 px
    narrower;
  - the nozzles: exits on x + y = 29;
  - the tail block shortened from row 26.9 to 26.05 (`T`).
  - Back from before D88: the two glowing tubes and the strut in each pod's bay, the rounded pods,
    the single-level hull (no 3 px lift, no keel, no anhedral).
  - Kept from D90: the shell from 0.03 voxels, held 0.004 inside.
- **The Silver Ship's banking pose (D93):** the fit keeps the game's roll (17.5 / 35°) but moves
  the banked ship sideways 0 / 0.5 px, not bankShift.ts's 1 / 2 (`bank.shift` [0.5, 0, 0, 0, -0.5]).
  Rolled about its axis, the model's top view already moves sideways (its parts stand above and
  below the axis); with bankShift's slide on top it overshot the sprites. (D88's 3 px lift made up
  for the same slide the other way.)
- **Nort Ship: D90's shell, from a closed copy.** The shell is made from the joined model before
  `cull_hidden` (as the Silver Ship's always was), kept out of the scene during the bake, from 0.03
  voxels, held 0.004 inside. The model itself is unchanged.

**Result:**

| | rule IoU (grid), level frame | half bank 79 / 83 | full bank 77 / 85 |
|---|---|---|---|
| Silver Ship, this | 0.9965 | 0.9379 / 0.9276 | 0.8657 / 0.8688 |
| Silver Ship, this at bankShift's shift | 0.9965 | 0.8733 / 0.8949 | 0.7175 / 0.7508 |
| Silver Ship, main (D88, D93's table) | 0.989 | 0.982 / 0.982 | 0.965 / 0.996 |
| Nort Ship | 0.9963 (main 0.9963) | - | - |

(`tools/bank_roll.py <name>`, k = 10; `tools/sprite_mask.py --measure` of a 20x top render gives the
same grid numbers.) The banks are below main's, which was shaped for them; D93's bars are 0.80 / 0.70.

Interior ink the outline adds in `?viewer=` (outline on vs off, 4 views round the model at the
free view's height, pixels inside the silhouette that go dark): Nort 3763-4479 px per view on main →
689-1142 (the rest is where one part overlaps another; one view's count was a camera still settling);
Silver 169-1090 → 386-669, also overlaps only.

**Checked:** `?viewer=` both ships from four sides at 3/4 height, outline on and off; the hangar
backdrop (`tyrianUi.backdrop.setMood('hangar')`, `setShip`), four moments each; in game
(`?debug=play&seed=1&ship=11|12&solid=1`) at ticks 300 and 700, and banking (`&steer=left|right`,
ticks 12 and 30): the Silver Ship's two tubes a side and round pods read in the banks, the Nort's
dark specks on the nose and cockpit plates are gone.

**Options considered:**
- *Smooth D88's model in place (a pchip through its jagged half widths, rounder pod corners):* keeps
  the 3 px lift and keel that cover the bays and only exist for the banks, which D93 no longer asks
  for.
- *The pre-D88 model unchanged:* rule IoU 0.83 (D74's survey), it reads a pixel fat per edge in game.
- *A uniform plan scale instead of the 1 px pull-in:* the inner mask is an offset, not a scale (the
  nose loses a whole row, the pods half a pixel per side), and a scale moves the windshield off the
  cockpit pixels.

**Review:** `tyrian-scratch/ship-refit-fixes/sheets/`: `viewer-silver-ship.png` (main, this, and
the pre-D88 model), `viewer-nort-ship.png`, `viewer-ink-outline-on-vs-off.png`, `hangar-*.png`,
`game-*.png` (main | this), `silver-banking-frames-iou.png` (each frame's sprite beside the model's
top view at the fitted pose). Raw captures beside it; the pre-D88 script and GLB in `ref/`. Fallback: the two scripts, GLBs and the Silver Ship's
spriteModels entry from main.

## D119 — The play harness no longer holds the armour at 0 without `&armor=`; the wear rule was right

2026-11-10

**Problem:** in `?debug=play` captures the Silver Ship showed heavy wear (D90: orange scorch, embers)
from tick 12 on, at what should be full armour; its hangar render was clean. The PR #150 captures
(`tyrian-scratch/ship-refit-fixes/sheets/game-silver-ship.png`) used
`?debug=play&seed=1&ship=11&freezeAt=T&steer=left|right&solid=1`, without `&armor=`.
- **The armour really was 0.** `tyrianHarness.g.player[0].armor` read 0 at every tick (12, 300, 700),
  for the Talon too; the draw list's `ships` was `[{armor: 0, reference: 10}]`, so wear level 2.
- **The cause: D90's `&armor=` parser.** Without the parameter it split `""` into `[""]`, and
  `Number("")` is 0, so the plan was "hold 0 from tick 0". The harness's own default (top the
  armour up to 28 with `&solid=1`, else 10) never ran. Every `?debug=play` run since D90 without
  `&armor=` held the armour at 0: every ship looked heavily worn, and with `&solid=1` the first hull
  hit would kill the bot.
- **Not the cause:** `shipDamage.ts`, the reference, the Silver Ship's model. The reference is the
  ship's `initial_armor` (its item's `dmg`: Silver Ship 10, Talon 10), as D90 says. With
  `&armor=28` / `4` / `2` the old code drew clean / light / heavy. A real game start (console
  `level 1 tyrian`, the Talon and then the Silver Ship) read `armor 9 of 10`, wear level 0.

**Decision:**
- `src/debug/armorPlan.ts` parses `&armor=`: empty or malformed entries are dropped, so without the
  parameter nothing is held and the harness tops the armour up as documented. `&armor=0` still holds 0.
- No change to the wear rule or its constants.
- Tests: `tests/debug/armorPlan.test.ts` (absent, empty, single values, schedules, junk);
  `tests/sim/shipWear.test.ts` starts level 1 with each ship 1-13 and checks the draw list carries
  the level-start armour (`min(dmg, 28)`) against `dmg`: clean at the start, light at 40%, heavy
  at 20%, clean at exactly 50%.

**Review:** `tyrian-scratch/ship-wear-check/ship-wear-sheet.png`: the Silver Ship and the Talon
before (no `&armor=`: held at 0, heavy) and after (full: clean; `&armor=4`: light; `&armor=2`:
heavy), and SuperCarrot, Phoenix, Stalker, U-Ship and Nort Ship clean at full. Ships 1-13 at ticks
12, 300 and 700, with and without `&armor=28`: armour 28, wear level 0 (`caps/ticks-*.txt`).

## D120 — The SAVARA boss is a blimp: `assembly-newshi-115` rebuilt as an airship (corrects D116)

**Problem:** D116 built `assembly-newshi-115` (the SAVARA boss, levels 1.8 / 1.12 / 1.17 / 3.10) as a flat-bottomed ground
dome fortress. The user pointed out it is a **blimp**. The sprite's lozenge body, tail cap (`newshi-154`), propeller and
nacelles are an airship's; a dome on the ground reads as the wrong object however well the outline matches.

**Decision:** rebuilt as an airship in `assets/blender/enemies/assembly-newshi-115.py`:
- a floating gas envelope: round underside, meridian seams converging toward the nose and the tail cap;
- a propeller of airfoil blades on a hub inside a closed duct-guard loop;
- a closed tail dome; nacelle colour corrected to the sprite's palette index.
The pieces `newshi-{3,5,39,41,43,45,77,79,81,83,115,117,119,121}` and the `-f2` frames of 3/5/41/43 were rebuilt;
`src/render/spriteModels/*.json` are unchanged.

**Measured:** rule IoU grid 0.9801 (frame 1) / 0.9799 (frame 2); every piece >= 0.95 (worst `newshi-5` f2, 0.9531).
Six fix rounds; the last strict review was still 6/10 "fix". Shipped by the coordinator because it now reads as the
right object, a clear improvement over D116's ground dome. Review sheet:
`tyrian-scratch/savara-blimp/assembly-newshi-115/final/cmp.png`.

**Follow-ups (known):**
- The propeller blades are irregular in size (the sprite's two frames are not a rotation of one real propeller).
- The duct ring is lumpy; it should be a smooth constant-section ring parallel to the rotor disc.
- The red centre mast crosses the rotor disc.
- The envelope height is 0.55 of its width, not the 0.6-0.8 asked. **Needs a user decision:** the pass-height budget
  is belly -5 against water -5.4, crown 31.5, fittings 33.6, with the ship passing at 34.2; may the envelope go higher?
- The bow shoulder masses are lumpy.
- The envelope shading is fairly flat from the game camera.

**Lesson:** establish what an object *is* before modelling it, and judge "does it read as that object" first, before
outline IoU, colours or detail. D116's dome matched the numbers and was still the wrong thing. The scout/design brief
names the object type (blimp, ground bunker, rock, ship), and reviewers score object reading before anything else.

## D121 — Episode-1 enemy rebuild, batch 2: 32 more models to the D65 hard-surface standard

2026-11-10

**Decision:** the next 40 episode-1 inventory units still in the older look (D116's ranking: not `flagship`, not
pickups, most-seen first by the bot run's ticks on screen) are rebuilt with `tools/workflows/model-flagship.js`, as D116
did (full mode, blueprints for heroes; D65's recipe: hard-surface geometry, AO/roughness bake `"bake": "model"`,
outline shell, art rules 1-5). The scout folded the 40 units into 32 items: `assembly-newshm-45` is `newshm-7.py` (the
lamp frames D116 left basic), `assembly-newshp-191` builds `newshp-191/193/153/155`, `assembly-newshd-127` is
`assembly-newshd-245.py`, `newshs-9.py` absorbs `newshs-93.py` (deleted; `lib_b040` had no other user), and the five
`lib_b014` asteroids were one item, `newshd-95` (see follow-ups: only `newshd-95` was rebuilt). No shared lib
(`lib_b0xx`, `common.py`, `usp_talon.py`) was edited; several items went standalone instead. `newshc-77` gains
`newshc-77-f8` for its wrecked frame 91. This also closes two D116 follow-ups: `newshm-7` is rebuilt (so
`assembly-newshm-45` can count as flagship) and `newshc-77`'s eye socket, chrome and neck are redone.

| Model | Tier | Top-view IoU (finisher, worst frame) | Review IoU | Score |
|---|---|---|---|---|
| newshm-7 (unit assembly-newshm-45) | hero | 0.9702 | 1.0 | 8 (fix round) |
| newshm-117 | standard | 0.9846 | 0.9846 | 8 (fix round) |
| newshd-95 | standard | 0.9823 | 0.9823 | 7 |
| newshc-163 | hero | 0.9633 | 0.9633 | 8 |
| newshd-228 | standard | 0.8577 (sub-pixel; grid 1.0) | 1.0 | 7.5 |
| newshf-47 | standard | 0.9797 | 0.9847 | 8 |
| newshd-77 | standard | 1.0 | 0.9961 | 8 |
| assembly-newshp-191 (newshp-191/193/153/155) | hero | 1.0 | 1.0 | 7 |
| newsha-167 | standard | 0.969 | 0.969 | 7 |
| assembly-newshd-165 | hero | 1.0 | 1.0 | 7 |
| newshc-49 | hero | 0.9858 | 0.9858 | 7.5 |
| assembly-newshs-13 | hero | 0.987 | 0.9568 | 8 |
| newshe-13 | standard | 1.0 | 0.9748 | 8 (fix round) |
| assembly-newshp-9 | hero | 0.9831 | 0.9831 | 7 |
| newsha-91 | standard | 0.9908 | 0.9908 | 8 |
| newshc-77 (+ -f8, frame 91) | hero | 0.9535 | 0.9535 | 8 |
| assembly-newshd-89 | hero | 0.9864 | 0.9766 | 8 |
| newshd-121 | standard | 0.9943 | 0.9943 | 8 |
| newshu-45 | standard | 0.9645 | 0.9645 | 7 |
| newshi-278 | standard | 0.9541 | 0.9541 | 7.5 |
| newsh-caret-163 | standard | 0.9655 | 0.9655 | 7 |
| newshc-1 | standard | 0.9715 | 0.9717 | 8 (fix round) |
| newsha-89 | standard | 0.9608 | 0.9721 | 8 (fix round) |
| newshs-9 (+ newshs-93, -93-f2) | standard | 1.0 | 1.0 | 8 (fix round) |
| newsha-283 | standard | 0.9718 | 0.9718 | 8 |
| assembly-newshc-271 | hero | 0.9922 | 0.9922 | 8 |
| assembly-newshd-245 (unit assembly-newshd-127) | hero | 0.9916 | 0.9916 | 8 |
| newshe-155 | standard | 0.9647 | 0.9624 | 8 |
| newshc-171 | standard | 0.9544 | 0.9544 (grid 1.0) | 7.5 |
| newshd-123 | standard | 0.9662 | 0.9662 | 7 |
| newshe-201 | standard | 0.973 | 0.9865 | 8 |
| newshf-11 | standard | 1.0 | 1.0 | 8 |

26 shipped by strict review in the run; `newshm-7`, `newshm-117`, `newshe-13`, `newshc-1`, `newsha-89` and `newshs-9`
after one `fix-round.js` pass (all 8/10). **IoU gate** (D116, OUTLINE-BORDER.md: `iou_rule_grid` ≥ 0.95):
`newshd-228` (the merging ice orbs, a size-1 sprite of 4-px orbs, inner masks of 12-24 px) is 0.8577-0.8701 on the
sub-pixel `iou_rule` on its five frames, the round orbs against the stair-stepped mask, and grid 1.0 on all five
(228, 247, 266, 304, 285; the coordinator re-rendered the shipped glbs' top views with the shells hidden and ran
`tools/sprite_mask.py --measure`; edge -0.01 to +0.06 px). Like `newsh-caret-171` in D116, it ships on the grid value.
Every other item is ≥ 0.95 on the rule as reported.

**Inventory** (regenerated, bot run): 36 of the 40 units are `flagship`, `assembly-newshm-45` included; episode 1 is
now 123 flagship / 40 older / 165 enemy units (was 87 / 76). The 4 left are the asteroids `newshd-152/114/133/5`.

**Rebuild check:** `newshs-9.py`, `newshc-77.py` and `newsha-89.py` rebuilt clean in a throwaway worktree
(`build-models.sh -j 2 -n`). `newsha-89` and all eight `newshc-77` glbs are byte-identical; `newshs-93`/`-93-f2` differ
only in triangle index order, and `newshs-9`'s outline shell in vertex order (decimation; same vertex count, bounds
within 3e-5).

**Follow-ups (known):**
- Glow materials wash out in the game: `src/render/modelFrames.ts` (line 87) copies the palette colour into
  `emissive`, and the environment and sun light add on top. `newshm-7`'s lens reads salmon/pink-red instead of a
  yellow core in orange/red (frame 9) or a dim ember (frame 7); `newsha-89`'s pit floor reads about pal 118 against the
  sprite's 116 and its collar/core go pink-peach; `newsh-caret-163`'s outer bands do not glow. Needs an emissive-only
  or unlit path for glow materials. `newshd-121` works round it with a local `dim_visor()` (a base-colour multiplier
  on red visors), which belongs in `usp_talon.py`/`common.py` if kept.
- The `lib_b014` asteroid family: only `newshd-95` was rebuilt (standalone; its `rock()` is spec-driven). Move
  `rock()` into a new `lib_newshd_rock.py` and rebuild `newshd-152/114/133/5` (and `newshd-18/43`, the lib's other
  users) so `lib_b014` can go; `newshd-123` (on `lib_b036`) should keep matching that rock look.
- `newshc-77.py` reads frame 91's sprite from `tyrian-scratch/e1-enemies-2/newshc-77/blueprint/ref91/` (it is not in
  `reference/models/newshc-77/`), and without it skips frame 91's extra colours silently. Make the catalogue write
  frame 91 into the reference instead. `newshd-77`, `newshd-121`, `newshe-155` and `newshc-171` also write their bakes
  or stats under `tyrian-scratch/` (as `newshf-1` and `newsha-169` already did): move them to `textures/<name>/`.
- `assembly-newshc-283.py` (D65) reads `newshc-77.glb` for context; re-check that machine in a level after this
  rebuild. Not captured in a level either: `assembly-newshp-191` (its seams against `newshs-191`/`newshm`
  neighbours), `newshd-77`, `newshd-95` (no frame-95 asteroid in 6000 ticks of 1.1), and `newshi-278`'s damaged frames
  268/270/272 (D87 should route them to the intact model).
- Shared code: `common.split_assembly` keeps faces that lie on the cut plane, so a part flush with a seam leaks into
  the next piece (`assembly-newshc-271` pulled its plinth in to 24.02..47.98); `common.export_glb` should take a
  `vertex_color_name` (`assembly-newshd-245` patches it for its COLOR_0 lens glow); `newsha-169.py` and
  `newshe-201.py` are near-duplicates (a `lib_mine.py` with ramp and slot arguments); `common.outline_shell` keeps
  only the largest island, so `newshc-77`'s wreck (frame 91, loose parts) shells each part in a local `wreck_shell()`:
  give it a keep-all-islands option.
- `?viewer=` cannot show `assembly-newshp-9` or `newshe-201-f2/-f3` (they fall back to atom-bombs); capture the
  pieces (`?viewer=newshp-1`) until `src/viewer/assemblies.json` is regenerated (`npm run catalogue`).
- Polish the reviews listed as optional: `assembly-newshp-9`'s derrick leans only ~12° (reads as a low ramp from the
  side); `assembly-newshp-191`'s sinking-stone liners show before the stones drop and its rubble borders read as
  beads; `assembly-newshs-13`'s eave tips float when `newshs-89/91` are shown alone; `newshm-117`'s shell is still
  3,000 faces (asked 1,500-2,000); `newshc-77`'s sight slit reads as two specks; `assembly-newshd-165`'s docstring
  is stale.

**Cost:** 172 agents (1 scout, 11 blueprints, 43 designs, 11 judges, 32 finishes on Sonnet, 21 fixes, 53 reviews),
21.8M subagent tokens, about 5.8 h at `maxAgents: 7`; the fix round (`fix-round.js`, 6 items) 12 agents, 1.18M
tokens, about 27 min. Sheets: `tyrian-scratch/e1-enemies-2/<name>/final/` and `.../fixround/<name>/final/` (not in
git, D3).

## D122 — Launched projectiles and orbs rebuilt as what they are (object-identity audit)

2026-11-10

**Decision:** D120 found the SAVARA boss built as a grounded fortress when it was a blimp, with the outline IoU
passing. A read-only audit then checked every episode-1 model's *behaviour* against what it was built as. Method
(`tools/enemy_behaviour.mjs`, run per inventory unit): for each enemy type that draws the unit, its **launcher** (the
type whose `launch` field spawns it), its **motion** (`mv(xc,yc)` in px/tick, turret/no turret) and the **layers** its
spawn events use. A unit launched by another enemy and moving at 3-5 px/tick is a projectile, whatever layer it spawns
on: the ground/air layer (25/50/75 vs 0) does not mean grounded or flying. Six models were built as grounded objects
though they are launched or float; each was rebuilt with `tools/workflows/fix-round.js` (6 items) and shipped.

| Model | Behaviour | Now (was) | IoU (worst frame) | Score |
|---|---|---|---|---|
| newshj-19 | types 752/755/762/767/839, launched by 754/756/763/769/838, mv(±4,0) or (±3,±3) | launched fireball, one floating oval turned through 4 frames, heat bands white to dark red (a campfire) | 1.0 | 8 |
| newsha-199 | flying orb | glowing orb with a rim crescent (a lamp on a ring) | 0.9509 (grid 1.0; bar 0.95, little margin) | 8 |
| newshi-19 | the blimp's dropped mine | glossy pulsing sphere, bore through it where the sprite is transparent (a washer with a blade) | 0.974 on the fixer's constant-ink metric | 7 |
| newshm-117 | floating orb, 3 growth frames | round floating spiral orb, closed belly (a flat shell on a base) | 0.9808 | 7 |
| newshe-277 | three orbs | three floating glowing orbs (pods on sleds) | 0.9825 | 7, verdict "fix" on minor points only |
| newshs-9 | type 592, launched by `newshs-93`'s 590, mv(0,4) | missile with the nose at row 11, tail and exhaust at row 1 (was reversed); also closes `newsh-caret-171`'s nose hole (launched, mv(±2,5)/(0,1)) | 1.0 | 8 |

The coordinator ships all six. `newshe-277`'s object reading is resolved; its remaining review issues are follow-ups.
Sheets: `tyrian-scratch/object-fixes/<name>/final/cmp.png`, audit output `tyrian-scratch/object-audit/` (not in git, D3).

**IoU note (`newshi-19`):** the review's `tools/sprite_mask.py --measure` gives 0.77/0.86/1.0/0.80/0.79 on its five frames
because the sprite's ink pulses 32 -> 1 -> 2 -> 3 and index 3 (luma 40) is above `INK_LUMA` and missed by the pulse
rule; no single geometry passes the tool on all frames. The fixer's constant-ink metric (ink = 32/1/2/3 on the
boundary) gives 1.0/1.0/1.0/1.0/0.974. Shipped on that, like `newshd-228` (D121); fixing the tool's pulse rule is open.

**Renderer finding:** `src/render/modelFrames.ts` (`colourFrame`, line 87) copies the palette colour into `emissive`, so
a model's own emissive strength below 1 cannot take effect; glow wash-out is the same cause as D121's glow follow-up.
`newshj-19` works round it with metallic 1.0 / roughness 0.6 (no environment diffuse). A real fix is an emissive-only or
unlit path for glow materials (the D121 follow-up).

**Follow-ups (known):**
- `newshe-277` (review issues): flame lick and tail tip read salmon not orange (model uses pal 120, sprite median 121);
  1-2 px dark specks on every orb in game (shell or body showing between flush patches); the swirl band ends in a hard
  square cut above y 4.4 (taper it like the tail); a faint dark crease across the upper body.
- `newshm-117`: the 9 radial seams make a pumpkin shell, the sprite's dark crescent groove should run deeper; band one
  index lighter than the sprite. `newsha-199`: the lower-right rim cap reads as a second lamp from the side.
  `newshi-19`: the bore leaves open holes in the lower hemisphere in side/3/4 views. `newshs-9`: tail nozzle rim could be
  wider; `newsh-caret-171` nose dome has AO specks and its docstring still says "lying flat" (it is launched).
- Audit minor items: `assembly-newshd-39` and `-89` drift in space but have flat bases; `newshd-121` is a flying drone on
  a ground stalk; `assembly-newshu-129` has a foot; `assembly-newshi-154`: reconcile D120's "tail" label with the audit and
  round its underside.
- **Could not determine from behaviour** (need the user or a closer look): `assembly-newshp-267` and
  `assembly-newshc-283` (towers or tanks?); `newshf-1` and `newshf-47` (which end is the head?); `assembly-newshu-79`
  (wreck or working machine?).
- `tools/enemy_behaviour.mjs` covers episodes 1 and 3 only and reads `docs/roadmap/inventory.json`.

## D123 — Episode-1 enemy rebuild, batch 3: the last 16 items (36 units) to the D65 hard-surface standard

2026-11-10

**Decision:** the 36 episode-1 inventory units still in the older look after D121 (all of them except the six
`lib_b014` asteroids, which the `asteroids` branch rebuilds) are rebuilt with `tools/workflows/model-flagship.js` as
D116 and D121 did (full mode, blueprints for heroes; D65's recipe: hard-surface geometry, AO/roughness bake
`"bake": "model"`, outline shell, art rules 1-5). New in this batch, after D120/D122: the scout recorded each item's
**object identity** with evidence from the game's data (`tools/enemy_behaviour.mjs`: launcher, motion, spawn layers;
D122's rule that the ground/air layer and the AIR explosion bit do not say grounded or flying), and the designs were
built to it (launched things closed and free-flying, fixed things standing on the ground). The scout folded the 36
units into 16 items, merging every family that shares one `lib_b0xx` so one agent keeps it consistent. Shared libs
used by flagships were not edited (items went standalone); `lib_b138` was edited because all five of its users were in
one item. `newshd-115` is a new model (script, glb and spriteModels entry).

| Model (glbs) | Identity (evidence) | IoU: sub-pixel rule (grid), worst frame | Score |
|---|---|---|---|
| newshp-237 (+ -f2..-f5), newshp-53, newshp-171 | 237: fixed ground bunker (ground events, mv 0, turret 60, launches 171); 53: the same housing as a missile silo (launches newshp-19); 171: launched homing mine (lby 198, acc 94/94), free-flying round mine | bunker and silo 0.994 (0.994); mine 0.894 (1.0) | 7 |
| newshd-267 | fixed ground power housing (ground events, mv 0, no turret, 20-step glow) | 0.9911 (0.9911) with its `tyrian_ground` stone floor (full-rect tile; the housing alone measures 0.70 against it) | 8 |
| newshd-85 | free-flying asteroid (random spawns only, falls at 4-6 px/tick); closed round underside | 0.963 (0.9825) | 8 |
| newshs-267 | turret module riding the link-45 tracked tank `assembly-newshs-165` at a constant offset (+12, +4 from piece 548); the scout's "hovering launcher" and the old "ground structure" both superseded, confirmed at 1.2 ticks 10010/10300 | 0.9864 (1.0) | 8 |
| newshd-169 (+ -f2..-f6) | fixed ground turret-silo (ground events, mv 0, turret 144, iris animation) | 0.9658 (0.9658) | 8 |
| newsha-281 | space mine (mv 0, walls of mines in 1.6, ground2 in 1.7); whole round ball, closed underside | 0.9509 (1.0) | 8 |
| newshf-85 (+ -f2, -f3), newshf-77 (+ -f2), newshf-55, newshf-53 | the SAVARA fighter squadron: flying fighters, sky layer, 2-4 px/tick down; nose at the sprite's bottom | 0.885 (0.961, newshf-85-f3) | 8 |
| assembly-newshc-243 (newshc-239/241/243), newshc-238 | the big blue rifle: a heavy gun unit moved by global ev19 velocities, muzzle tip 238 carries turret 55; pairs with `assembly-newshc-271` (D121) | whole 0.985 (0.9948); worst piece newshc-239 0.9461 (0.9714); 238 0.8914 (1.0) | 8 |
| newshc-275 | muzzle cap of the moving gun `assembly-newshc-271` (turret 46) | 0.9692 (1.0) | 8 |
| newshd-88, newshd-34, newshd-157 (+ -f2, -f3), newshd-16, newshd-239 | 88/34: edge pieces of the drifting rock heap `assembly-newshd-89`; 157: flying clamshell pod (sky layer, turret 24); 16: tusked crawler moving down-screen, built hovering (no legs drawn), closed keel; 239: fixed wall spawner (launches `newshs-171`) | 0.9321 (0.9747, newshd-16) | 7.5 |
| newshd-31, newshd-15 | edge pieces of the drifting rock heap `assembly-newshd-89`; closed rock undersides | 0.8568 (1.0, newshd-15); 31: 0.9417 (1.0) | 7 |
| newshp-19 | launched missile (lby `newshp-53`, mv 0,3): nose down-screen at the sprite's bottom, exhaust glow at the top | 0.9529 (0.9783) | 8 |
| newshc-19 | launched purple shell (lby `newshu-55` and `newshu-43`), free-flying, round closed hull | 0.9282 (1.0) | 8 |
| assembly-newshu-15 (newshu-15/17/53/55/19/38) | one intact fixed ground station (all ev6 ground, mv 0), laid out from the 1.5 spawn positions; `newshu-19`/`-38` are its left fringe, `newshu-79` its base; `newshu-55` launches `newshc-19` | whole machine 0.9833 (0.9993); **newshu-19 alone 0.9222 (0.9375)**; newshu-38 alone 0.9377 (0.9626) | 8 |
| newshm-55 | wall block of the WINDY block wall (`assembly-newshm-1` family; ground2, dat3 +2, mv 0, as newshm-15/-53) | 0.9997 (1.0) | 7, "fix" (fixed by the coordinator, below) |
| newshd-115 (new) | flying craft (sky layer at the screen edges, mv 0,2, turret 5, swung round by ev19) | 0.9399 (0.966) | 8 |

15 shipped by strict review in the run. **IoU check:** the coordinator re-rendered every shipped glb's top view on
its sprite grid with the outline shell, `tyrian_ground` parts and other frames' parts hidden, ran
`tools/sprite_mask.py --measure` per frame (66 renders), and composed the two machines from their pieces (the rifle
from the catalogue layout, the station from `assembly-newshu-15.py`'s `PIECES`). The three low figures the finishers
reported are sub-pixel `iou_rule` values, not the gate (`iou_rule_grid` ≥ 0.95, D116/D121): `newshp-237`'s 0.8904 is
the mine `newshp-171` (0.894 rule, grid 1.0 on all seven frames); `newshd-88`'s 0.9323 is `newshd-16` (0.9321, grid
0.9747); `assembly-newshu-15`'s 0.9375 is `newshu-19` measured alone, and its grid value is 0.9375 too. Every
mismatch there is a sprite pixel on the seam with the 2x2 pieces: the tool counts the tile's edge as outside, so dark
seam pixels become border the model should not cover, though in the machine they are interior (the whole machine is
0.9993 on the grid). It ships on the whole-machine value; the per-unit figure is a follow-up. Everything else is ≥ 0.95
on the grid. `newshd-169` re-measures 0.9658 (the finisher reported 0.9975), still above the bar.

**newshm-55 fix (coordinator):** the review found the family's dark foot missing from the export (`pal_52` spanned
only y 0.217-0.375 m against `newshm-15`'s 0.0-0.375), so the block floated about 0.66 px over its bed plate, and the
outline shell (y 0.075-0.761) did not wrap the plate. Cause: the bed plate was built into the block's bmesh, both capped
at z 0 and overlapping the foot, and `lib_newshm_block.cut_sockets`'s exact boolean dropped the foot. The plate is now
its own closed part, built after the socket cut and joined (`T.join`) like the emblem; the block shell, foot, sockets
and bolts come from `lib_newshm_block` unchanged, with D114's single body colour (57). Rebuilt (`build-models.sh -j 2`):
`pal_52` spans 0.0-0.375 as on `newshm-15`, the shell spans 0.0-0.761 and reaches the plate's four corners (to within
0.01 m), the side view shows the foot standing on the plate with no gap, and the top view is 0.9997 (grid 1.0). In
WINDY (`?debug=play&episode=1&main=33&skip=895&freezeAt=895&camera=tilted`) the ? block sits in the wall between the
red and X blocks with its black plate corners outlined, as the sprite's.

**Coordinator clean-up:** `newshd-15.py` (the old boulder on `lib_b137`, which would have overwritten the new
`newshd-15.glb` on a full rebuild) now runs `newshd-31.py`, which exports both, as `newshc-238.py` runs
`assembly-newshc-243.py`: list only one of each pair to `build-models.sh`. `lib_b023`, `lib_b058`, `lib_b135` and
`lib_b137` had no users left and are deleted.

**Rebuild check:** `newshd-15.py` (so `newshd-31` and `newshd-15`), `newsha-281.py` and `newshp-171.py` rebuilt in a
throwaway worktree (`build-models.sh -j 2 -n`): all four glbs and their spriteModels entries byte-identical.

**Inventory** (regenerated, bot run): episode 1 is 149 flagship / 10 not / 159 enemy units (was 123 / 42 / 165; the
assembly scripts now group `newshu-15/17/19/38/53/55` as `assembly-newshu-15` and fold `newshc-238` into
`assembly-newshc-243`). Of the batch's 36 units, 32 are flagship. Left: the six `lib_b014` asteroids
(`newshd-152/114/133/5/43/18`, the `asteroids` branch) and four units their items did not rebuild (below).

**Identity answers:** `newshf-85`'s head is the bottom end (mouth and fang at rows 17-19); `newshf-55` flies down the
screen with a mask pixel-identical to `newshf-47`'s, so `newshf-47`'s nose is also at the bottom, which is how D121
built it: D122's open question is closed for `newshf-47` (`newshf-1` stays open). `newshs-267` is a turret module on
the tank, not a free platform.

**Follow-ups (known):**
- Not rebuilt though in the scout's items: `newshp-271` (twin-cannon ground turret, still on `lib_b123`), `newshp-95`
  (the green copy of the `newshp-19` missile, launched by `newshs-93`; no script or spriteModels entry yet; share
  `newshp-19`'s geometry as a palette swap), `newshc-39` (vent block with a gun on `assembly-newshc-283`'s floor, still
  on `lib_b110`) and `newshd-229` (the crystal asteroid, still on `lib_b036`; match `newshd-85` and the asteroid
  family). One small run.
- `newshu-19`'s per-unit grid IoU is 0.9375 (seam pixels; the machine is 0.9993). Either teach `sprite_mask.py` to
  measure a piece inside its machine's layout (pieces that are separate units of one assembly script) or accept it
  on the whole machine as recorded here.
- Colour, one step each: `newshp-237`'s ditch is pal 2 (sprite 1); `newshd-267`'s lower front band is 71 (sprite 69)
  and its slit post reads as a black hole from the game camera; `newshs-267`'s rack walls 8 (sprite 6); `newshf-77`'s
  fuselage 106 (sprite median 103); `newshd-88`/`-34` boulder faces one step off; `newshd-31`'s ledge reads 6 (sprite
  8); `newshd-115`'s exhaust bells 115 (sprite 118 with hot 121-124 cores) and its glow slot one strip where the
  sprite has two hot spots; `newshm-55`'s shell 57 (sprite median 56).
- Form polish: `newshp-237`'s rubble edge reads as a riveted plate; `newshd-267`'s lower housing reads soft (a cushion);
  `newshd-31`'s three boulders show gaps and a spiky lump in free views (fine in the heap); `newshp-19`'s dorsal fin
  hides the exhaust core from the tilted camera and draws a dark line down the bell from above; `assembly-newshu-15`'s
  lens dome has a notch where it meets the drum, and its west drum head reads as a hole from low west; `newshd-85`'s
  V-grooves show the outline shell as black ink lines (as `newshd-123`); `newshd-115`'s wing-bar ends are chamfered
  boxes (sprite slightly rounded).
- Mesh tidiness (hidden): open loops in `newshp-171` (40 edges in the belt), `newshd-267` (bolt bottoms), `newshc-19`
  (96 edges), `assembly-newshc-243` (tube ends and seams). Triangle counts above the small-enemy guide (2-6k):
  `newshd-169` 7.7-8.2k per stage, `newshd-16` 8.7k, `newshd-239` 7.8k, `newshd-157` frames 6.8-7.4k.
- `newshc-19.py` (line 42) bakes into a hard-coded `tyrian-scratch` path (as `newshd-77`, `newshd-121`, `newshe-155`,
  `newshc-171` in D121); move bakes to a temp dir or `textures/<name>/`.
- Not captured in a level: `newsha-281` (1.6 MINEMAZE), `assembly-newshc-243` (1.5 at about tick 5700 with `seed=1`
  and no skip), the `newshd-88` family, `newshd-115`, `newshc-19` against its launchers; `newshs-267`'s +12/+4 offset
  was not re-run. Its docstring and `sprite.json` still say "3.15 ground structure", and its "4 spawns in 3.2" is
  unverified.
- Renderer: `newsha-281`'s bronze reads lighter and yellower than the sprite (as `newsha-283`), `newshc-275`'s red
  charge ring (emission 3.0) reads brighter than the sprite's one 114 pixel: both wait on the emissive fix (D121, D122).
  `newsha-283`'s squash (a ball flattened on the ground, though it moves) is worth a look.
- `tools/review_sheet.py --which current` renders `newshp-19` all black (old outer-mask metric): use
  `sprite_mask.py --measure` and the viewer.

**Cost:** 73 agents (1 scout, 4 blueprints, 20 designs, 4 judges, 16 finishes on Sonnet, 6 fixes, 22 reviews), 8.78M
subagent tokens, about 2.2 h at 6 concurrent, for 16 items covering 36 units (4 hero, 12 standard). Per-agent
median: design 10.8 min (max 35), finish 2.1 (max 33), fix 11.4, review 3.5 (max 34). Sheets:
`tyrian-scratch/e1-enemies-3/<name>/final/`, the coordinator's measurements in `tyrian-scratch/e1-enemies-3/integrate/`
(not in git, D3).

## D124 — Episode-1 enemy rebuild, batch 4: the last four units to the D65 hard-surface standard

2026-11-10

The four units D123 left (its follow-ups) were rebuilt by a `model-flagship` run (wf_896154b4-68b) to the same rules
as D123 (original sprite wins on outline, features and colour; D52, D65; outline shell D50, D51). All four shipped, no
unit failed. Episode 1 is now **153 flagship / 6 not / 159 enemy units**; the six left are the `lib_b014` asteroids
(`newshd-152/114/133/5/43/18`, the `asteroids` branch).

| Unit | Identity | Top-view IoU (worst frame) | Review score |
|---|---|---|---|
| newshp-271 | fixed twin-cannon ground turret on its stone pad, four frames (271/273/275/277) | 0.9541 (turret only; grid 0.9688-0.9851) | 7 |
| newshp-95 (new script, spriteModels entry, GLB) | launched green missile (type 460, mv 0,5, launched by `newshs-93`), the green palette swap of `newshp-19`; one geometry, four frames | 0.951 (dark outline ring excluded, as D51) | 8 |
| newshc-39 | fixed vent block with a gun emplacement on `assembly-newshc-283`'s floor, frames 39/41/43; `maps.json` with `"bake": "model"` | 0.958 | 8 |
| newshd-229 | free-flying crystal asteroid (rock plus a per-frame emissive gem), frames 229/231/233/235 | 0.984 | 7.5 |

**Notes on the build.**
- `newshp-95.py` loads `newshp-19.py` read-only (importlib) and calls its `build_missile` with the green body pair (39,
  41) read from the sprite. It depends on `newshp-19.py`'s `build_missile` signature. Its input,
  `reference/models/newshp-95/` (`sprite.json` plus frame PNGs, made from the game data because the catalogue bot never
  saw it on screen), lives in the git-ignored `reference/` symlink, as every script's input does (`newshp-19` reads
  `reference/models/newshp-19/`). The committed GLBs mean CI doesn't rebuild models; to rebuild on a fresh checkout,
  regenerate the reference entry first (the catalogue or `tools/sprite_mask.py`'s sprite.json step).
- `newshc-39.py` was fixed in one round (boolean palette transfer, groove-free outline-shell source, a darker apron, the
  mantlet and gun on the plate lip) and its `tube()` degenerate-axis bug on the x axis fixed.
- `newshp-271.py` and `newshd-229.py` are rewritten on `common.export_sprite_model` with repo-relative paths; their
  spriteModels entries came out byte-identical.
- `lib_b123`, `lib_b110` and `lib_b036` have no users left and are deleted.

**Follow-ups (known):**
- `newshp-271`: the muzzle-brake boxes have square outer bottom corners (sprite rounds them; a 1 px chamfer would raise
  the turret-only IoU, which has little margin, 0.954-0.958); side lamps stick out about 1 px; the muzzle bore is a flat
  red disc that reads as a lamp lens from the front. It has no texture bake (`textures/newsh2-271` is an old name).
- `newshp-95` (inherited from `newshp-19`'s shared `build_missile`, already in D123): the dorsal fin draws a dark line
  down the bell from above and hides the exhaust core from the tilted camera. Colour drift of one ramp step in places
  (row 4 reads 8 for 9; vane lips 103 for 101). Not checked in a level (the missile appears in 1.3 and the bot saw 0
  ticks of it); IoU was measured from the design-step render of the same geometry, not the final GLB.
- `newshc-39`: the block reads a step paler than the sprite, and the pal_8 bolt heads throw small specular pings (lower
  pal_8's metallic or raise its roughness toward pal_7's 0.45/0.42); glow bars start at col 8 where the sprite's slot
  wall is ink (trivial). IoU has little margin: any edit must not pull the base in.
- `newshd-229`: from the game camera the V grooves read as four pillow lobes round the gem (narrow them away from the
  junction); the 233 crystal reads pale periwinkle (124,124,252) against the sprite's royal blue, a renderer matter
  (`modelFrames.ts` adds the colour to the emissive): re-capture 231/233/235 after the emissive fix and lower the GEMS
  strengths (3.5-6.0) only if 233 still washes out. The rock recipe is copied inline from `newshd-85`: move it into a
  shared `lib_rock` helper in a separate change.
- Not run in a level (`?debug=play`): `newshp-271`, `newshp-95`, `newshd-229` (viewer only); `newshc-39` was captured in
  1.5 at tick 2542.

**Inventory** (regenerated, bot run): episode 1 is 153 flagship / 6 not / 159 enemy units (was 149 / 10 / 159); whole
game 155 flagship of 479. M0 shared units not flagship-done: 130.

**Cost:** 15 agents, 1.63M subagent tokens. Sheets: `tyrian-scratch/e1-enemies-4/<name>/final/` (not in git, D3).

## D125 — The newshd asteroid family on one rock builder (`lib_newshd_rock`), the last six episode-1 units

2026-11-10

**Problem:** D121 rebuilt only `newshd-95` of the asteroids that shared `lib_b014`; `newshd-152/114/133/5` (and the
lib's other users `newshd-18/43`) stayed in the older look, which the QA sweep called "blocky faceted grey,
voxel-like stair steps on the silhouette" (icosphere pushed to a pixel-traced outline, faces painted with the sprite's
shading ramp). They are asteroids floating in space (ASTEROID1-3 and later episodes): round all over, the underside
seen from the side at the tilted camera, no base.

**Decision:**
- **One builder.** `newshd-95.py`'s spec-driven `rock()` moves into `assets/blender/enemies/lib_newshd_rock.py`
  (`main(NAME, SPEC, paint=, parts=)`): a body lofted from the sprite's inner mask (D74), its top raised into the
  summit and the lumps, crests and creases the sprite draws (`bumps`, `crests`, `valleys`, new), planar fracture faces
  (`cuts`, `fine`, and `rim_spalls`, new, so the waist never reads as a belt), crack grooves and impact pits;
  matte palette material, AO/roughness bake (`"bake"` by the script, D50/D65), outline shell. `newshd-95` builds the
  same: geometry and shell identical, bake within run-to-run noise (its committed glb is kept). It keeps D121's shell
  (0.012 voxels) and its bake with the shell's source copy in the scene (`bake_with_copy`: the coincident copy darkens
  its AO about 12%); the six new ones use D90's shell (0.03 voxels, held 0.004 inside) from a sealed copy kept out of
  the bake (D118). `lib_b014` has no users left and is deleted.
- **Each rock from its own sprite** (art rules 1-3; rocks: highlights are lit faces, not sheen): the sprite's lit
  patches become lumps cut by fracture faces turned to the light, its dark creases become valleys (a fine crack in
  some), its dark spots pits, its shadowed side falls away; a rounder dome than 95's (`rise`/`fall` 0.7/0.8) and no flat
  underside plane (95's -82° cut is not used). One matte material per rock region (metallic 0, roughness 0.9): the
  trimmed median of the sprite's own ramp, its ink ring, dark limb and glints being lighting.
  - `newshd-152`: three lit facets (upper-left, the upper-right strip, lower-left), the crease between the upper two,
    the pit under the strip; pal_104.
  - `newshd-114`: the leaning egg; the upper lit strip and the lower-left patch with the crease and crack between; pal_104.
  - `newshd-133`: the summit right of middle with its lit streak down-left, the dark upper right; pal_103.
  - `newshd-5`: the large rock: the bright upper mass, the right and lower lobes, the two creases with cracks, five pits;
    a finer outline trace (144 rays, 1 smoothing pass) so its flat sides hold; pal_7.
  - `newshd-18`: `newshd-5`'s SPEC (read from its script) plus the vent: a bed pressed into the right lobe's face
    (scorched pal_5, frame 93), a plate and low lens in it (119/117/122/126, a step cooler on 55, `frame_part` 18/55),
    the rock round it glow-lit pal_11 on frame 18 only (`frames={55: 7, 93: 7}`).
  - `newshd-43`: the three-lobed rock with the notch on its right; the upper lobe's bright ridge, the bright cluster low
    in the middle, the two creases between the lobes; pal_7.

**Result** (`tools/sprite_mask.py --measure` on the shipped glbs' top views, shells hidden; colours: the model's flat
top palette index vs the sprite's, trimmed medians per region):

| Model | grid IoU (rule) | rock colour model / sprite | other region | tris (rock + shell) |
|---|---|---|---|---|
| newshd-152 | 0.9921 (0.9376) | 104 / 104 | - | 2530 + 3000 |
| newshd-114 | 0.9906 (0.9342) | 104 / 104 | - | 1936 + 3000 |
| newshd-133 | 1.0 (0.9342) | 103 / 103 | - | 1854 + 3000 |
| newshd-5 | 0.9705 (0.9490) | 7 / 7 | - | 4162 + 3000 |
| newshd-18 (18 / 55 / 93) | 0.9705 each | 7 / 7 | vent 119/119, 117/117; bed 5/5 | 4162 + 3000 + 346 |
| newshd-43 | 0.9727 (0.9482) | 7 / 7 | - | 4008 + 3000 |
| newshd-95 (unchanged) | 0.9823 (0.9322) | 104 / 104 | - | 1602 + 2400 |

Built with `tools/build-models.sh -j 2`; captured in ASTEROID1/2 (`?debug=play&episode=1&main=5|6&seed=1&solid=1`,
ticks 1.5: 282, 680, 1737, 3029, 3446, 3558; 1.6: 119, 2414, 3028, 5742, 5772, 5773, 5819). Sheets (sprite beside the
model: top, game angle, 3/4, sides, underside, in-game crops): `tyrian-scratch/asteroids/final/<name>/sheet-<frame>.png`
(not in git, D3).

**Inventory** (regenerated, bot run): episode 1 is **159 flagship / 0 not / 159 enemy units** (was 153 / 6 / 159);
whole game 161 flagship of 479. M0 shared units not flagship-done: 124 (was 130).

**Follow-ups (known):**
- In game the rocks read lighter and smoother than their mottled sprites (one matte mid-tone, lit from high up); the
  big rocks' tops still close towards the summit in a few broad faces. A local faceting pass ("chisel": facets pressed
  in at sites over the top) was tried and dropped: on the loft it bunched at the summit, on a voxel remesh it tore the
  mesh and tripled the triangles.
- `newshd-18`: the vent is small and dull red in game (D121's glow wash-out follow-up); its bed shows a light wedge on
  the lobe's uphill side and the plate's upper edge stands a little proud of the steep lobe from the 3/4 views.
- `newshd-95` keeps D121's darker bake (`bake_with_copy`) and its flat underside; rebuild it on D90/D118 with the
  family's matte roughness if the user wants the family to match exactly.
- `newshd-114` has a small facet cluster where its crease meets the summit's faces (0.3 px; invisible in game).

## D126 — A model's glow takes its authored strength, below 1 too, and replaces its lit colour

2026-11-10

**Problem (the D121 and D122 glow wash-out).** `colourFrame` (`src/render/modelFrames.ts`, line 87 before this change)
copied the palette colour into a pal_ material's `emissive`. Blender's glTF exporter writes a glow (emission colour =
base colour, from `common.palette_material`) as colour × strength in `emissiveFactor`, and only the part that doesn't
fit under 1 into `KHR_materials_emissive_strength` (three's `emissiveIntensity`). So the copy kept the extension and
dropped the strength in the factor: in game a glow emitted palette × the extension (1 for every strength whose
colour × strength fits under 1: 0.4, 0.12, 2.5 on a dark red all showed as 1), and on top of that the material was lit
in full in the same colour, then Neutral tone mapped. A lit-plus-glowing orange or red runs past 1 and goes pale:
`newshm-7`'s lens salmon, `newsha-89`'s core peach, `newshj-19`'s bands cream and pink, `newshe-277`'s orbs salmon.
All 1,730 pal_ glow materials in `public/models/` have emission colour = base colour (scanned), so the authored strength
is exactly `max(emissive) / max(colour) × emissiveIntensity`.

**Decision:** `rigModel` reads that strength once per material (`glowStrength`, kept in `userData.tyrianGlow` so
recolouring and `Material.clone` don't lose it; `emissiveIntensity` becomes 1). `colourFrame` then sets
`emissive = palette × strength` and `colour = palette × max(0, 1 − strength)`: the glow's light stands in for the lit
colour. Strength 1 or more is the palette colour unlit (what the sprite pixel is); 0.4 is 60% lit and 40% glow (an
ember). Colour still comes from the live palette per frame (D7: fades, level palettes, the hit flash's hue,
`tyrian_frame_pal`). It is the default for every model, not opt-in. D35's hot shots and fireballs are extruded
sprites with their own palette material (`paletteMaterial.ts`) and don't go through `colourFrame`: unchanged.

**Options considered:**
- *Honour the strength and fade the lit colour (chosen):* fixes both halves of the wash-out with no model rebuilt.
- *Honour the strength only (emissive = palette × strength, lit colour kept):* tried; the lenses and pits barely
  changed, since the lit term was most of the wash-out (`newsha-89` is authored at 1 and was already "honoured").
- *Opt-in per material (a glTF extra or a name convention):* safest for untested models, but needs every glowing model
  rebuilt to benefit, and leaves two meanings of `emission_strength`. Not needed: the check below found no model worse.
- *An unlit material for glows (MeshBasicMaterial):* loses the damage shader patch (D87), shadows received, the
  outline shell's material contract and the partial glows below 1.
- *Clamp the glow at the palette colour:* would keep saturated colours from going pale at high strengths, but
  discards what the scripts authored above 1 (white-hot cores); left to the scripts instead (follow-ups).

**Check.** Before (origin/main) against after, in `?viewer=` at the game angle and free, against the sprite: `newshm-7`
(frames 7/9/11), `newsha-89`, `newsh-caret-163`, `newshj-19` (4 frames), `newshe-277`, `newsha-199`, `usp_talon`,
`ship-microcorp-stalker`, `ship-silver-ship`, the level 1 glows (`newsh2-229`, `newsh2-87`, `newsh4-1`, `tyrian10-14`,
`newsh2-123`, `newsh2-127`, `newshe-1`, `newshe-39`, `newshp-13`, `tyrian10-39`, `newsh2-153`, `newsh2-171`,
`newsh2-267`, `newshp-85`) and `newshd-229` (231/233/235), `newshc-275`, `newsha-281`, `newshd-121`. And in game
(`?debug=play`, seed 1, frozen): TYRIAN (main 1) at ticks 300/900/1500/2400 (the Talon's engines, shots, explosions,
level 1 enemies) and SOH JIN (main 31) at 1304/2920/3004 (`newsha-89`, `newshj-19`, `newsha-199`); shots, explosions
and the Talon came out the same. Sheets: `tyrian-scratch/emissive-fix/` (`emissive-fix-sheet.png`). The reported glows now read in their palette bands (yellow core
in orange and red rings, ember on frame 7, the pit at its own dark red, orange orbs, blue rings on the caret); the rest
look the same or closer to the sprite. Of the 1,730 glow materials, 219 (authored below 1) emit less than before and
1,118 more (their strength was in `emissiveFactor`); with the lit colour gone, totals moved little. Viewer only: `newshm-7`
(ASTEROID1, main 5: on the draw list at 6860/7372 but not on screen in the frozen frames), `newsh-caret-163` (WINDY)
and `newshe-277` (ALE), which did not show in 8,000 ticks of `main=33`/`41`.

**Follow-ups (art, in the model scripts):**
- Saturated colours at high strength still go pale under Neutral tone mapping: `newshp-85`'s pulse (reds at 2.5-4.5)
  reads pink, `newshd-229`'s 233 gem (3.5-6.0) periwinkle. Lower those strengths toward 1 / brightest channel.
- Workarounds that can go: `newshj-19`'s metallic 1.0 / roughness 0.6 (D122) and `newshd-121`'s `dim_visor()` (D121).
- `palette_material`'s docstring (`assets/blender/common.py`) now says what a strength means in game.
## D127 — Stars show only where background 1 is black, as the C tests its screen

2026-11-10

**Problem** (`tyrian-scratch/e1-qa-2/REPORT.md` issue 1): stars were drawn over floors and models in 1.1, 1.2, 1.3, 1.6, 1.7
and 1.14. `update_and_draw_starfield` (backgrnd.c L1067-1101) paints a star pixel only where the screen is still 0 after
background 1, but the draw list has no screen, so the sim recorded every star pixel and the renderer drew them all at
`Pass.Starfield`'s height (0.02, D5), over the ground.

**Decision:** the renderer tests each star pixel as the C did (`src/render/starCover.ts`): against the background-1
tiles of the same draw list, at their tick positions, a pixel over a non-zero tile pixel is skipped. The cover is a
320x200 byte mask, rebuilt once per draw list. Stars over black space draw as before. Everything the C drew after the
stars (backgrounds 2 and 3, enemies, shots) already covers them by depth, as it sits higher (D5). The test is on the
original tile's pixels, not the HD painting (D57): the painted space tiles (0, 58, 59) are black in both.

**Not stars:** the dark crosses left on 1.6's pipe at t1050 and on 1.14's blocks at t2680 are `JE_drawSP`'s
superpixels (`Pass.Effects`, drawn over everything in the C too); unchanged.

Captures: `tyrian-scratch/qa2-renderer/` (`before/`, `stars-after/`, `cmp_*.jpg`: 1.1 t4050 and t1050 (space), 1.2
t4050, 1.6 t1050, 1.7 t1597, 1.14 t2680).

## D128 — A damaged frame's textures are upsampled smoothly, so the damage has no pixel blocks (extends D87, like D114)

2026-11-10

**Problem** (`tyrian-scratch/e1-qa-2/REPORT.md` issue 8): SOH JIN's damaged red blocks (1.13 t1800,
`enemies/newshm-1`) showed a blocky pixel camouflage at 4K. The report guessed nearest-neighbour sampling; the textures
were already bilinear (`damageFrames.ts`). The cause: D87's three textures are the sprite's 24x28 (or 12x14) pixels, one
texel each, and a repainted frame changes pixel by pixel, so bilinear filtering showed every texel as a square with
straight creases between them (one sprite pixel is about 15 px on a 4K screen).

**Decision:** the textures are built at 4x (`DAMAGE_UPSAMPLE`, 96x112 for a 2x2 sprite) from the same per-pixel values,
each channel upsampled separably:
- the cut (`mask` r) by a Catmull-Rom cubic, which passes through every pixel's value, so a one-pixel hole stays a hole
  and straight cut edges stay where they were, without the bilinear corners;
- scorch, embers, the changed-colour amount, the tint and the paint by a Gaussian of 0.75 sprite px (D114 used 0.9 for
  the glass orb's parts), so a repainted frame's pixel noise reads as soft blotches.
The shader is unchanged (it reads in sprite-pixel UVs, so the texture size doesn't matter to it). The player ship's wear
(D90) keeps its own pattern texture. Build cost: about 0.1M multiply-adds per channel per frame and palette, on a frame's
first draw and on palette changes.

Checked with `?debug=play&hurt=1`: the SOH JIN blocks (1.13 t1050, t1800 at 4K), DELIANI's green pod
(`newshc-197`/`-199`, 1.5 t3300) and SAVARA's cut `newshi-278` (1.12 t3300, its charred, glowing cut rims unchanged).
Test: `tests/render/damageUpsample.test.ts`.

Captures: `tyrian-scratch/qa2-renderer/` (`dmg-before/`, `dmg-after/`, `dmg-after/cmp_*`: left before, right after).

## D129 — A blended sheet rises over the models it covers, so clouds and ice no longer cut them with a straight line (extends D5, D6, D45)

2026-11-10

**Problem** (`tyrian-scratch/e1-qa-2/REPORT.md` issue 9): WINDY's clouds (1.14 t1050, t2680) and TYRIAN's ice (1.9 t300)
cut through the gem blocks and the dome with a straight line: the part above the sheet was clear, the part below
clouded. Both are `draw_background_2_blend` sheets in `Pass.Background2Mid`, drawn flat at that pass's height (0.9, D5,
D45), but the ground-enemy models under them stand at 0.45 and reach 1.13-1.26, so depth put their tops above the
sheet. In the C the sheet is averaged over everything drawn before it, the whole block.

**Decision:** each blended sheet tile is placed after the frame's draws, at `sheetHeight` (`src/render/sheetLift.ts`):
its pass's height, raised to 0.04 over the highest top of the earlier passes' models it overlaps on screen, and kept
0.04 under the lowest bottom of the later passes' models it overlaps; if both can't hold, half way between. A model's
screen box and heights come from its source's box (cached per model pool) at its placement (D6 keeps its footprint at
the sprite's size). D6 makes this free of layout changes: a sheet at any height covers the same screen area, so tiles
at different heights still meet. Only the blended sheets move: the opaque layers (SAVARA's painted clouds, D107; the
cloud rims, D78) and every other draw keep D5's heights.

**Options considered:**
- *No depth test for the sheets:* they'd be painted over the later passes' opaque models too (sky enemies, the ship),
  as three.js draws translucent objects after all opaque ones and there is no per-pass order to put them in.
- *One fixed, higher height for blended sheets:* the ground blocks reach 1.26, past `Background3Under` (1.25) and into
  the sky enemies' (1.65) undersides, which hang about half a unit below their height (the Talon spans 2.82-3.79 round
  its 3.3), so no single height clears both.

Test: `tests/render/sheetLift.test.ts`. Captures: `tyrian-scratch/qa2-renderer/` (`before/`, `sheet-after/`,
`sheet-after/cmp_*.png`: left before, right after).

## D130 — Episode-1 fortress and machine enemies stand on the HD ground: no floor plate painted from the sprite (extends D86, D103)

2026-11-10

**Problem** (`tyrian-scratch/e1-qa-2/REPORT.md` issue 3): fourteen enemy scripts exported the sprite's ground round the
machine as a floor plate painted pixel by pixel from the sprite (four grey tones from the stone set's greys, as
`lib_b073.floor`, or DELIANI's blue tiles traced per pixel). In game it showed as a rectangle of raw grey (or blue)
pixel cells under each machine, on top of the HD terrain: ASTEROID1's boss and pods, ASTEROID2's turrets and carts,
ASTEROID?'s fortress row, DELIANI's pillar ends and vent block. Checked per candidate in the game's render
(4K captures at ticks where each is on screen, found by stepping the harness and reading the draw list):

| Script | Plate | Seen in | Done |
|---|---|---|---|
| `assembly-newshm-45` (ASTEROID1 boss) + `newshm-7` (its bay frames 7/9/11) | per-pixel stone | 1.1 t5966 | plate kept as the AO bake's occluder, deleted before export |
| `assembly-newshd-245` (beetle pod pair) | per-pixel stone | 1.1 t2160/2950, 1.2 t1500 | not exported |
| `assembly-newshs-13` ("26" block) | `lib_b073.floor` | 1.2 t9200 | not built |
| `assembly-newshs-39` (black orb) | per-pixel stone | 1.1 t5300, 1.2 t2100, 1.3 t850 | not exported (the launch bay's pit and coaming stay) |
| `newshd-267` (pink power housing) | per-pixel stone | 1.1 t2160/2950/4680, 1.2 t1305 | not exported |
| `newshd-275` (caged turret) | per-pixel stone | 1.1 t2950, 1.2 t4500/5550, 1.3 t3310 | not exported |
| `newshs-11` (green-window dome) | per-pixel stone | 1.1 t1900/4800/5300, 1.2 t1305 | not built; the flange's foot closed with a flat ring |
| `newshs-229` (red crystal clamp) | per-pixel stone | 1.1 t4680, 1.2 t1305, 1.3 t3310 | not exported |
| `newshd-127` (lamp pod) | per-pixel stone | 1.2 t2100, 1.3 t3310 | not built |
| `newshs-191` (capsule rack) | per-pixel stone | 1.1 t2950, 1.3 t3310/3515 | not exported |
| `assembly-newshc-283` (DELIANI twin pillar) | per-pixel blue tiles, ink-outlined | 1.5 t2560/3300 | AO occluder only, deleted before export; the outline shell made from the machine alone |
| `newshc-39` (DELIANI vent block) | per-pixel blue tiles, in the shell | 1.5 t2560 | AO occluder only, deleted; left out of the shell |
| `assembly-newsh2-115` (TYRIAN dome works) | none: D86 already drops its dirt | 1.9 t300/500 | unchanged. The QA's "dome plate" at 1.9 t300 is the machine's own modelled steel bed seen through the ice sheet (issue 9, D129); at t500, clear of it, it stands on the HD dirt |
| `assembly-newshp-9` (derrick), `assembly-newshp-165` ("218" container) | modelled (kerbs, paving, grates; plain materials), not pixels | 1.1 t1900/4680, 1.2 t9200 | unchanged: a D65 base, no pixel cells |

**Decision:** the machines stand on the HD ground, as D86's bunkers and D103's turrets. Where the script bakes AO
(`newshm-45`, `newshc-283`, `newshc-39`) the plate is still built for the bake, as D86's dirt, so the feet darken where
they meet the ground, and its faces are deleted before the cut and export (`newshc-*`: the floor's palette materials
are flagged copies, `tyrian_floor`; the machine is culled and outlined on its own). Elsewhere the plate is left out of
the export (kept for the scripts' review renders where they use it) or not built. Every machine part, palette
material, frame, piece and pivot is as it was: no `spriteModels` entry changed. `lib_b073.floor` has no caller left;
its docstring says it is for bake occluders only. `newshd-275.py` imported `common` from, and exported into, a
hard-coded other worktree (`tyrian-worktrees/e1-enemies`); it now uses its own checkout.

**IoU** against the object without its ground: ground = the sprite pixels whose top surface in the old model was the
plate (top z ≤ 0.7 px on more than half the pixel); the sprite with those pixels made transparent is measured with
`tools/sprite_mask.py` (`masks`, `measure`) against the new model's top view (any geometry, shell left out).
`outer` keeps the machine's dark ring, `inner` is D74's rule (the ring left to the game's ink). Worst piece per unit:

| Unit | ground px removed | outer grid IoU | inner grid IoU (rule) |
|---|---|---|---|
| assembly-newshm-45 (+ newshm-7) | 1740 | 1.0 | 0.888 (newshm-83) |
| assembly-newshd-245 | 676 | 1.0 | 0.945 (newshd-281) |
| assembly-newshs-13 | 772 | 0.902 (newshs-13) | 0.879 (newshs-91) |
| assembly-newshs-39 | 2044 | 0.835 (newshs-79) | 0.651 (newshs-79) |
| newshd-267 | 202 | 1.0 | 0.992 |
| newshd-275 | 301 | 1.0 | 0.905 |
| newshs-11 | 351 | 0.988 | 0.960 |
| newshs-229 | 234 | 1.0 | 0.886 |
| newshd-127 | 334 | 0.983 | 0.959 |
| newshs-191 | 144 | 1.0 | 0.998 |
| assembly-newshc-283 | 824 | 0.762 (newshc-245) | 0.892 (newshc-283) |
| newshc-39 | 245 | 0.899 | 0.966 |

The stone-set models were fitted with the whole tile opaque, so most cover the machine's dark ring (outer 1.0, inner
lower); the DELIANI models were fitted to D74's inner mask (inner high, outer lower; `newshc-245` has no ground at
all). The low values of `newshs-39` and `newshs-13` are machine parts below 0.7 px that the height rule counts as
ground: the launch bay's pit floor and coaming (22-57 px per piece) and the gutters and ramp foot (23-61 px). No
machine part moved; no plate face is left (`newshm-*`, `newshc-*` checked by palette in the exported glbs).

Built with `tools/build-models.sh -j 2`; tests, typecheck, build pass. Captures, before and after, 3840x2160
(`?debug=play&episode=1&main=M&seed=1&skip=T&freezeAt=T`): 1.1 t1900, 2160, 2950, 4680, 4800, 5300, 5966; 1.2 t1305,
1500, 2100, 4500, 5550, 9200; 1.3 t700, 850, 3310, 3515; 1.5 t2560, 3300; 1.9 t300, 500, in
`tyrian-scratch/no-floor-plates/` (`before/`, `after/`, `pairs/`, `crops/`; IoU in `iou/`).

**Follow-ups (known):**
- What the plate hid now shows where the terrain draws the machine or its wreck under the enemy (D86's problem, which
  D86's cover rule solves only for TYRIAN's ground enemies on small wreck structures): ASTEROID? (1.3 t3310) shows a strip
  of the `l1bld` red-bar structure under the capsule racks' front edge and a dark ring under the caged turrets; DELIANI
  (1.5 t2560/3300) shows a sliver of the pillar end's red hatch, painted in the HD terrain, beside each pillar end
  model. Small (about one sprite pixel), but a D86-style covered painting or cover rule for those tiles would remove it.
- `newshs-229`'s jaw slots now show the ground down them (the sprite draws them near-black, "the floor far below"); a
  modelled dark slot floor inside each jaw would match the sprite's depth if it reads too light.
- The stone-set models cover their sprite's dark ring (see IoU): a D74 refit would put their edges on the inner mask.
## D131 — A fireball's last rings fade out, so its last frame no longer leaves a red hollow square (extends D80, D106)

2026-11-10

**Problem** (`tyrian-scratch/e1-qa-2/REPORT.md` issue 10): a red hollow square was left where some explosions had been
(1.5 t4050, 1.2 t3300 and t8111, 1.9 t300, 1.11 t4205). Found from the draw list: each is `newsh6.shp` 133, the last
of the fireball's 12 frames (type 1, sprites 122-133, `explosionFrames.ts`), drawn as D80's flat art in
`Pass.Explosions`. The original sprite is a sparse ring of dim red pixels whose sides run straight; the painting keeps
that outline (its fit was the lowest of the sheet, 0.49, "mostly the floor") and D106's art shader drops texels under
0.5 alpha, so it draws as a thin, crisp, dark-red octagon at the full explosion opacity: a hollow square, once the fire
round it has gone. Not the stencil (D105/D106): a lone frame shows it.

**Decision:** a fireball's flat art fades over its last three frames: opacity x0.8, x0.45, x0.15 (`flatExplosionFade`,
`FIREBALL_TAIL`), so the ring dies out as the fire does and the last frame is a faint trace. Every other explosion frame
(big explosions, smoke, sparks, hits, coin values) and the original look (`?sprites=original`) draw as before. The art
is unchanged.

**Options considered:** repainting frame 133 rounder and softer (a new cut of the D80 sheet, and still a crisp line
under D106's alpha cut); dropping the frame (one tick of the original's ring gone, and the fire would end on a
thicker ring).

Test: `tests/render/explosionFade.test.ts`. Captures: `tyrian-scratch/qa2-renderer/` (`redbox-before/`,
`redbox-after/`, `redbox-after/cmp_all.png`: left before, right after, one row per tick above).
