# Blender build scripts

Each model in the game is built by a Python script in this folder. The script is the source of
truth: re-running it rebuilds the model from scratch and exports it to `public/models/<name>.glb`.

## Matching the original sprites

Every model is a 3D version of its original Tyrian sprite: the same silhouette, proportions,
colors and details, not a new design.

1. Render the sprites: `npm run catalogue` for everything (see below), or
   `node tools/extract-sprites.mjs data reference/sprites` for the sheets and player ships. This writes the
   sprite sheets, the banking frames of each player ship, and a transparent top view of each
   (`ship-<name>-top.png`). `reference/` is git-ignored because it's derived from the game data (#10).
2. Measure the sprite: its width per pixel row gives the outline, and colors are sampled from its pixels.
   Convert pixel colors with `common.srgb()`. One sprite pixel is 1/12 unit, and sprite row `r`
   maps to `y = (14 - r) / 12` for a 24x28 ship.
3. `common.reference_image()` puts the sprite on a plane beside the model in Blender (never
   exported) so they can be compared side by side with the MCP's `look`.

In game, a dark outline (`OUTLINE` in `src/render/view.ts`) reproduces the sprites' black edges.

## Conventions

- **One script per asset**, named after it: `usp_talon.py` → `public/models/usp_talon.glb`.
- **Scripts are idempotent.** Each one deletes and rebuilds its own objects and leaves the rest
  of the scene alone, so it can be re-run safely in a live Blender session.
- **Units:** 1 Blender unit = 1 world unit = 12 Tyrian pixels (`PX_PER_UNIT` in
  `src/game/playfield.ts`). The 264x184 px playfield is 22 x 15.3 units, and a typical ~24 px
  ship is about 2 units long.
- **Axes:** forward = +Y, up = +Z, model centred on the origin. glTF export converts this to
  Three.js's Y-up with forward = -Z, which is up the screen in the game.
- **Shared helpers** (materials, lofts, slabs, export) live in `common.py`.
- **Palette materials:** name a material `pal_<index>_<tag>` (`common.palette_material`) and the
  game colours it with palette entry `<index>`, so level palettes, fades and the enemy hit flash
  apply to the model as they did to the sprite. Use the index of the sprite pixels the part
  stands for. Other materials keep their own colour.
- **Keep it light:** use low-poly meshes and few materials so the browser can draw a screen
  full of enemies.
- **Imported textures or HDRIs** (for example from Poly Haven) need a row in `/CREDITS.md`.

## Models that replace sprites (enemies and player ships)

Every enemy and player ship gets a model (DECISIONS.md D15). What there is to model, and the
reference for each, comes from the catalogue:

    npm run catalogue      # plays every level headless; writes reference/models/ (about 2 min)

`reference/models/catalogue.json` lists all models in priority order (player ships, then flying
enemies, then ground enemies, each by how long they're on screen). Each
`reference/models/<name>/` has:

- `sprite.json`: the sprites the model replaces (`sprites`), every frame's pixels as palette
  indices (`frames[].pixels`, -1 = transparent), the colours of those indices (`colors`), the
  levels it's in and, for a piece of a bigger object, its `assembly`.
- `frame-*.png`: each animation frame, 12 image px per sprite px. `contact.png`: all of them.
- `assembly.png`: for a piece of a bigger object (bosses and big ground structures are several
  2x2 enemies side by side, each with its own model), the whole object as seen in game with this
  piece outlined. Neighbouring enemies can show up too. Model each piece as its part of the
  whole, so the pieces fit together.

A model's script is `assets/blender/enemies/<name>.py` (or `ships/`), named after its catalogue
entry. See `enemies/newshf-1.py` for the pattern:

1. `common.load_sprite(root, name)` reads `sprite.json`.
2. Build the model with the helpers (lofts, slabs, fins, palette materials). Sprite up is +Y, one
   sprite px is 1/12 unit, and the object's centre (its 24x28 or 12x14 block's centre) is the
   origin. Frames that differ only in small details (blinking lights) share one model. Frames
   that change shape can each get a model; export each with the frames it covers.
3. `common.export_sprite_model(root, objects, "enemies/<name>", sprites)` writes the `.glb` and its
   entry in `src/render/spriteModels/`, which is how the game finds it.
4. `common.render_preview(...)` renders the model beside the sprite (top, in-game and 3/4 views).

**Animation** (DECISIONS.md D17). When frames change only details, one model covers them and
animates: `common.frame_part(obj, [frames])` shows a part only on those frames (a flame of each
length, a light that's on), and `common.palette_material(..., frames={frame: index})` changes a
part's palette colour on those frames (a glow that pulses). Export the tagged parts with the
model. `common.render_frame_previews(objects, png, sprite, root)` renders every frame beside its
sprite, one row each. See `enemies/newshm-89.py`.

**Coverage.** `tests/render/modelCoverage.test.ts` checks that every frame in the catalogue has a
model (it skips when `reference/models/` hasn't been generated), and its failure lists the frames
still to model. A frame that isn't worth a model goes in its `NOT_MODELLED` list with the reason
(DECISIONS.md D33); it stays extruded in game. Today that's one frame: newsh0-13, a filler piece of
the level 2.12 dragon that is a single dark outline pixel.

Build headless, several at a time, with previews:

    tools/build-models.sh -j 8 -p /tmp/previews assets/blender/enemies/*.py

A model with concept maps (`textures/<name>/maps.json`, DECISIONS.md D44) is textured by
`texture_bake.py` straight after its build, with all of its animation frames (`-f2`, `-f3` ...),
so a rebuild never leaves it plain or leaves one frame plain among textured ones (D46). An
assembly's bake needs `.shape/<name>/regions.json` (`tools/sprite_shape.py <name>`, git-ignored);
`-n` builds without texturing.

Compare a model with its sprite in the model viewer at `?viewer=<name>`: rotate it freely, or use
Top with "Sprite over model" to check the outline pixel by pixel. `?debug=models` on the dev server
shows models in the game's own renderer (`&model=a,b`, `&page=N`, `&flash=1` for the hit flash).

## Background structures (DECISIONS.md D34)

`?bg=remaster` draws structure tiles (rocks, buildings, trees) as models. Scripts in `tiles/`, one
or more per tileset (`shapesz_bg3.py`, `shapesz_ground.py`), build them from the tiles' pixels:

    TILES_SHAPES=z npm run tiles    # writes reference/tiles/shapesz/ (git-ignored, from the data)
    tools/build-models.sh -p /tmp/previews assets/blender/tiles/*.py

`reference/tiles/<shapes>/tiles.json` has every used tile's pixels (1x and MMPX 2x), the layers and
levels that use it and its usual neighbours; `map-*.png` and `used-l*.png` show where tiles go.
`lib_tiles.py` has the shared parts: `Tileset` (load it with the layer being modelled, as index 0 is
transparent on layers 1 and 2), `boulders` (a rounded stone per stone painted on a tile, found as
hills of brightness and continued across tile edges), `mask_slab` (a slab with the tile's outline,
optionally a coloured relief), `dome`, `block` and `export_tile_model`. A model stands for a
pattern of tiles (rows of tile numbers, -1 = any) and is centred on it; `export_tile_model` writes
the `.glb` to `public/models/tiles/<shapes>/` and the pattern to `src/render/tileModels/`.
Background 3 models sit at their pass's height and keep within about +-0.35 units; ground models
stand at 0 and stay under 0.2 where ground enemies sit on them. `tests/render/remaster.test.ts`
checks that every multi-tile pattern only occurs whole in the levels' maps.

## Running a script

- **Through the Blender MCP**, in the live Blender session (the usual way while modeling):

      import sys; path = "<repo>/assets/blender/<name>.py"; sys.modules.pop("common", None)
      exec(compile(open(path).read(), path, "exec"), {"__file__": path, "__name__": "__main__"})

- **Headless:** `blender --background --python assets/blender/<name>.py`, or many at once with
  `tools/build-models.sh`.

`.blend` files are git-ignored because the scripts and exported `.glb` files are what get
committed. If hand-made `.blend` files become necessary, set up Git LFS first.

## Sprite-shape prototype (not used by the game)

An experiment in inferring 3D shape from the sprites instead of modelling by hand. Nothing in
the game loads it; the model viewer's Prototype switch (`?viewer=<name>&proto=1`, key `p`) shows
its models where they exist.

    PY=<python with numpy, scipy, Pillow>
    $PY tools/sprite_shape.py <name>                 # analysis: .shape/<name>/regions.json, debug PNGs
    blender -b --python assets/blender/proto/shape_model.py -- <name>   # model from the JSON
    $PY tools/review_sheet.py <name> --build         # both of the above, then review sheets + metrics

`<name>` is a catalogue model (`newsh5-47`) or a whole assembly (`assembly-newshb-115`, split into
its pieces after building). The analyser splits the sprite into regions (one palette ramp each,
cut by outlines), gives each a profile (round, flat, dome, taper, recess, void) and heights, and
`tools/shape_profiles.py` turns those parameters into heights for both the analyser and Blender.
`assets/blender/proto/overrides/<name>.json` overrides any region's parameters by id, so fixing a
model means editing JSON, and rebuilding is deterministic. `tools/review_sheet.py` renders one
sheet in a fixed layout (sprite, top, overlay, diff, elevations, 3/4, game camera, region ids)
and writes metrics JSON (silhouette IoU, colour error and height per region, triangles, seams).
`reshape_heights.py` instead rescales a hand-made model's heights from the analysis.
Prototype models go to `public/models/proto/` (listed in its `index.json`).
