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

Build headless, several at a time, with previews:

    tools/build-models.sh -j 8 -p /tmp/previews assets/blender/enemies/*.py

Check models in the game's renderer at `?debug=models` on the dev server (`&model=a,b`,
`&page=N`, `&flash=1` for the hit flash).

## Running a script

- **Through the Blender MCP**, in the live Blender session (the usual way while modeling):

      import sys; path = "<repo>/assets/blender/<name>.py"; sys.modules.pop("common", None)
      exec(compile(open(path).read(), path, "exec"), {"__file__": path, "__name__": "__main__"})

- **Headless:** `blender --background --python assets/blender/<name>.py`, or many at once with
  `tools/build-models.sh`.

`.blend` files are git-ignored because the scripts and exported `.glb` files are what get
committed. If hand-made `.blend` files become necessary, set up Git LFS first.
