# Tyrian 3D

A browser-based 3D remake of the DOS vertical-scrolling shooter **Tyrian**, built on top of
[OpenTyrian](https://github.com/opentyrian/opentyrian), the open-source C port.

The goal is to keep Tyrian's gameplay (levels, weapons, enemies, shop and story) and rebuild
its presentation in real-time 3D that runs in the browser. Ships, enemies and props are modeled
in Blender and exported as glTF; everything else is extruded from the original sprites.

## Play

**https://dlomibao.github.io/tyrian3d/**

The game runs on the original Tyrian 2.1 data, which isn't hosted here (see [Game data](#game-data)).
Download [tyrian21.zip](https://camanis.net/tyrian/tyrian21.zip), the freeware release that
OpenTyrian links to, and choose or drop it on the page. It stays in your browser, cached for next time.

| Action | Keyboard | Gamepad |
|---|---|---|
| Move | Arrow keys / WASD | D-pad / left stick |
| Fire | Space / J | A / right trigger |
| Change rear-weapon mode | Enter / L | X |
| Sidekicks | Left Ctrl, Left Alt / K, ; | LB, RB |
| Pause | Esc / P | Start |

## Status

All four episodes of Tyrian 2.1 are playable, from the title screen's episode and difficulty
choice through to each episode's end, with the original's enemies, weapons, events, music and
sound. Between levels the item screen sells and upgrades gear and lets you pick the next
destination on the map (arrows, Enter, Esc; `/` changes the rear gun's firing mode). If your ship
is destroyed, you go back to that item screen with the loadout you launched with.

- **Not yet:** the item screen's Data Cubes and Options menus, arcade and two-player modes, and
  the cutscenes between episodes.
- **Everything else:** in [Issues](../../issues) and [Milestones](../../milestones). Design calls
  made along the way are in [DECISIONS.md](DECISIONS.md).

## How it works

- **Simulation (`src/sim/`):** a close transliteration of OpenTyrian's gameplay code: `JE_main`'s
  level loop, enemies, level events, player movement, weapons, collisions and explosions. It keeps
  the C names, integer semantics and random number generator, so it plays like the original. Tests
  compare it tick by tick against OpenTyrian's own C, compiled and run on the same input.
- **Draw list:** instead of drawing pixels, the simulation records each sprite and tile it would
  draw, tagged with its draw pass.
- **Renderer (`src/render/`):** turns the draw list into a 3D scene. Draw order maps to height.
  Sprites are extruded from their pixels into rounded 3D shapes. Hand-made Blender models replace
  key sprites; the player's USP Talon is the first. Motion is interpolated, so it's smooth at any
  refresh rate, though the game logic ticks at the original ~35 Hz.
- **Audio (`src/audio/`):** the original sound effects, plus the AdLib music played through a
  port of the OPL emulator and the LDS song player. It matches OpenTyrian's output sample for sample.
- **Data (`src/data/`):** parsers for Tyrian's level, item, enemy, sprite, palette and episode
  script formats.

## Asset pipeline

Each 3D model is built by a Python script in [`assets/blender/`](assets/blender/) and exported
to `public/models/*.glb`. The scripts are committed, so every model can be rebuilt from scratch;
`.blend` files are not committed. Anything imported from outside the project, such as Poly Haven
textures or HDRIs, gets a row in [CREDITS.md](CREDITS.md).

## Game data

OpenTyrian describes Tyrian 2.1 as freeware and bundles it with its releases. However, the zip
itself still contains Epic MegaGames' original `license.doc`, which forbids copying. Until the
redistribution terms are confirmed ([#10](../../issues/10)), the data isn't committed here and
isn't deployed with the web build.

For local development, fetch it into `data/`, which is git-ignored:

    ../opentyrian/get_data.sh data     # or download tyrian21.zip and extract it with lowercase names

## Development

    npm install
    npm run dev        # dev server; serves ./data (or $TYRIAN_DATA) so no zip is needed
    npm test           # unit tests (data parser tests skip when data/ is missing;
                       # set TYRIAN_DATA to read the data from elsewhere)
    npm run build      # typecheck and production build
    TYRIAN_EPISODE_TEST=1 npm test   # also play every level of all four episodes headless

Debug pages: `?debug=sprites` (renderer test bench), `/src/audio/debugMusic.html` (music player).

## License

GPL-2.0-or-later. This project derives from OpenTyrian, which uses the same license; see
[LICENSE](LICENSE). The Tyrian game data has its own freeware terms and isn't covered by this license.
