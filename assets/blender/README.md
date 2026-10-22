# Blender build scripts

Each model in the game is built by a Python script in this folder. The script is the source of
truth: re-running it rebuilds the model from scratch and exports it to `public/models/<name>.glb`.

## Conventions

- **One script per asset**, named after it: `player_ship.py` → `public/models/player_ship.glb`.
- **Scripts are idempotent.** Each one deletes and rebuilds its own objects and leaves the rest
  of the scene alone, so it can be re-run safely in a live Blender session.
- **Units:** 1 Blender unit = 1 game unit. Tyrian's play area maps to the X/Y plane, with
  forward = +Y and up = +Z. glTF export converts to Three.js's Y-up.
- **Keep it light:** use low-poly meshes and few materials so the browser can draw a screen
  full of enemies.
- **Imported textures or HDRIs** (for example from Poly Haven) need a row in `/CREDITS.md`.

## Running a script

- **Through the Blender MCP**, in the live Blender session (the usual way while modeling).
- **Headless:** `blender --background --python assets/blender/<name>.py`

`.blend` files are git-ignored because the scripts and exported `.glb` files are what get
committed. If hand-made `.blend` files become necessary, set up Git LFS first.
