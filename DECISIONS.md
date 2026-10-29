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
