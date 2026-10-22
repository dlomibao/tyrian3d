# Blender build scripts

Each model in the game is built by a Python script in this folder. The script is the source of
truth: re-running it rebuilds the model from scratch and exports it to `public/models/<name>.glb`.

## Matching the original sprites

Every model is a 3D version of its original Tyrian sprite: the same silhouette, proportions,
colors and details, not a new design.

1. Render the sprites: `node tools/extract-sprites.mjs data reference/sprites`. This writes the
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
- **Stable material names**, so the game can find parts by name (e.g. `engine_glow`).
- **Keep it light:** use low-poly meshes and few materials so the browser can draw a screen
  full of enemies.
- **Imported textures or HDRIs** (for example from Poly Haven) need a row in `/CREDITS.md`.

## Running a script

- **Through the Blender MCP**, in the live Blender session (the usual way while modeling):

      import sys; path = "<repo>/assets/blender/<name>.py"; sys.modules.pop("common", None)
      exec(compile(open(path).read(), path, "exec"), {"__file__": path, "__name__": "__main__"})

- **Headless:** `blender --background --python assets/blender/<name>.py`

`.blend` files are git-ignored because the scripts and exported `.glb` files are what get
committed. If hand-made `.blend` files become necessary, set up Git LFS first.
