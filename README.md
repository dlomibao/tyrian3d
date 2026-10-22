# Tyrian 3D

A browser-based 3D remake of the DOS vertical-scrolling shooter **Tyrian**, built on top of
[OpenTyrian](https://github.com/opentyrian/opentyrian), the open-source C port.

The goal is to keep Tyrian's gameplay (levels, weapons, enemies, shop and story) and rebuild
its presentation in real-time 3D that runs in the browser. Ships, enemies and props are modeled
in Blender and exported as glTF.

## Status

Early planning. Nothing playable yet.

## Proposed stack

These choices aren't final.

- **Rendering:** Three.js (WebGL2, with WebGPU later where it's supported)
- **Language and build:** TypeScript + Vite
- **Assets:** Blender → glTF 2.0 (`.glb`), with models built through the Blender MCP
- **Game logic:** ported from OpenTyrian's C source (`src/`), not a from-scratch rewrite,
  so it plays the same as the original
- **Camera:** gameplay stays on a 2D plane, seen from a fixed, slightly angled 3D camera
  ("2.5D"), so the original level layouts and hitboxes still apply

## Roadmap

1. **Foundations:** Vite/TS/Three.js skeleton, game loop, input, deploy to GitHub Pages
2. **Data loading:** parse the Tyrian 2.1 data files (levels, items, enemies, shapes) in TypeScript
3. **Core gameplay:** player ship movement, firing, the first weapons, collision, a scrolling level
4. **Enemies:** enemy definitions, movement patterns and spawning from level event scripts
5. **3D art pass:** Blender models for the player ship, common enemies, bullets and terrain
6. **Full episode 1:** all levels, the shop and upgrades, bosses, the HUD
7. **Audio:** music (Loudness/AdLib emulation or re-recorded tracks) and sound effects
8. **Remaining episodes, arcade and two-player modes**

Progress is tracked in [Issues](../../issues) and [Milestones](../../milestones).

## Asset pipeline

Each 3D model is built by a Python script in [`assets/blender/`](assets/blender/) and exported
to `public/models/*.glb`. The scripts are committed, so every model can be rebuilt from scratch;
`.blend` files are not committed. Anything imported from outside the project, such as Poly Haven
textures or HDRIs, gets a row in [CREDITS.md](CREDITS.md).

## Game data

Tyrian 2.1 was released as freeware by its author. This repo doesn't redistribute the data
files. Get them from the mirror that OpenTyrian links to
([tyrian21.zip](https://camanis.net/tyrian/tyrian21.zip)) and put them in `data/`, which is
git-ignored.

## License

GPL-2.0-or-later. This project derives from OpenTyrian, which uses the same license; see
[LICENSE](LICENSE). The Tyrian game data has its own freeware terms and isn't covered by this license.
