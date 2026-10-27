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

In a two-player game, player 2 moves with W/A/S/D, fires with F, changes the rear weapon's mode
with R and fires the sidekicks with Q and E (or the keypad: 8/5/4/6, 0, `.`, 7 and 9), or uses
the second gamepad.

The keys can be changed in Options. Menus take arrows or WASD, Enter, Esc, a pad's d-pad, A and B,
or taps. On a touch screen the ship follows your finger and fires while you touch; the pause
button sits in the top corner.

## Status

All four episodes of Tyrian 2.1 are playable, from the title screen's episode and difficulty
choice through to each episode's end, with the original's enemies, weapons, events, music and
sound. Between levels the item screen sells and upgrades gear and lets you pick the next
destination on the map (arrows, Enter, Esc; `/` changes the rear gun's firing mode), with the
original's little simulator showing the guns and sidekicks firing before you buy them. Its Data
row holds the data cubes found in the last level, to read there. If your ship is destroyed, you go
back to that item screen with the loadout you launched with. Finishing an
episode, or quitting a game, with a high enough score asks for your name for that episode's high
score table (episodes 1-3, as in the original), which the title screen shows under High Scores.

- **Between levels:** the episode script's story screens play as in the original: pictures, pans,
  flashes and fades, and the glowing text with its warning sirens (any key or tap moves on, Esc skips
  the scene). Remastered pictures can replace the originals without code changes: see
  [`src/app/pictureArt.ts`](src/app/pictureArt.ts). An episode's end shows its hint, episode 3's
  ending animation and, after the last episode, the credits, then carries on into the next episode.
- **Options:** the item screen's Options menu loads and saves games (11 slots, the last being the
  automatic LAST LEVEL backup; Alt-S / Alt-L), and the title has Load Game and Options. Options sets
  the music and sound volume, the music style, the keys (two per control) and checks a gamepad's
  buttons. Saves and settings stay in this browser.
- **Cheats:** the original's secret inputs work. In flight, hold F2 F3 F6 for invulnerability
  ("Cheaters always prosper."), F2 F3 F4 to self-destruct, F2 F6 F7 to skip the level, or F2 F4 F6
  F7 F9 \ / for the Nort ship. On the title, Shift+G, Shift+] and then L O R D reveal the
  Impossible, Suicide and Lord of the Game difficulties (DESTRUCT is accepted, but the Destruct
  game isn't in yet). `?loot` starts new games with 1,000,000 credits. See
  [DECISIONS.md](DECISIONS.md) D32.
- **Attract mode:** left alone for 30 seconds, the title screen plays the original's five recorded
  demos in turn, replayed exactly as OpenTyrian plays them; any key, button or tap returns to the
  title (`?demo` or `?demo=1`..`5` plays one at once).
- **Kind of game:** Start asks for it, as the original's gameplay menu does: 1 Player Full Game,
  1 Player Arcade (no shop, the Stalker armed by what it picks up, and lives) or 2 Player Arcade.
  Typing a Super Arcade ship's code at the title (the original's, shown after each finished game)
  starts that ship; ENGAGE starts Super Tyrian.
- **Two players:** 2 Player Arcade is OpenTyrian's two-player mode on one machine. Player 1 has the
  usual keys, the mouse and the first gamepad; player 2 W/A/S/D, F fire, R change fire, Q/E
  sidekicks (or the keypad, or the second gamepad). Fly close together and stop to link: player 2
  docks under player 1 and turns a gun with the move keys while firing. Each player has lives (their
  weapon's power), and Options and the item screen set each player's keys and gamepad.
- **Not yet:** the Destruct game and network play.
- **Everything else:** in [Issues](../../issues) and [Milestones](../../milestones). Design calls
  made along the way are in [DECISIONS.md](DECISIONS.md).

## How it works

- **Simulation (`src/sim/`):** a close transliteration of OpenTyrian's gameplay code: `JE_main`'s
  level loop, enemies, level events, player movement, weapons, collisions and explosions. It keeps
  the C names, integer semantics and random number generator, so it plays like the original. Tests
  compare it tick by tick against OpenTyrian's own C, compiled and run on the same input.
- **Draw list:** instead of drawing pixels, the simulation records each sprite and tile it would
  draw, tagged with its draw pass.
- **Interface (`src/ui/`):** the title, item screen, messages and pause menu are HTML screens on
  one framework (design tokens, components, a screen manager and one navigation model for keys,
  pads and touch) over a 3D backdrop of the player's ship above a planet. The Options, load, save,
  high score, data cube and story screens still have their first, simpler look, and are opened from
  those screens. See [src/ui/README.md](src/ui/README.md).
- **Renderer (`src/render/`):** turns the draw list into a 3D scene. Draw order maps to height.
  Every enemy, boss and player ship is a Blender model of its original sprite (about 1,280
  models), loaded the first time it appears and coloured from the game's live palette. The
  backgrounds, shots and effects are extruded from their pixels into rounded 3D shapes. Motion is
  interpolated, so it's smooth at any refresh rate, though the game logic ticks at the original
  ~35 Hz.
- **Audio (`src/audio/`):** the original sound effects, plus the AdLib music played through a
  port of the OPL emulator and the LDS song player. It matches OpenTyrian's output sample for sample.
- **Data (`src/data/`):** parsers for Tyrian's level, item, enemy, sprite, palette and episode
  script formats.

## Asset pipeline

Each 3D model is built by a Python script in [`assets/blender/`](assets/blender/) and exported
to `public/models/*.glb`. The scripts are committed, so every model can be rebuilt from scratch
(`tools/build-models.sh` runs them headless in parallel); `.blend` files are not committed. The
models are 3D versions of Daniel Cook's Tyrian art, which he released for anyone to use.
`npm run catalogue` lists every sprite to model. To compare models with their sprites, open the
model viewer at `?viewer` (or `?viewer=<model name>`): the sprite and the model side by side, the
model rotatable, with a top view at the sprite's scale that can lay the sprite over the model.
Bosses and other objects built from several pieces are listed too (`assembly-…`), shown whole. It
works on the dev server and, once the data zip is loaded, on the deployed site. Anything imported from outside the project, such as Poly Haven
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

Debug pages: `?debug=sprites` (renderer test bench), `?debug=play` (a real level played by the test
bot, with chosen weapons; see `src/debug/playHarness.ts`), `/src/audio/debugMusic.html` (music player).
`?vfx=original` shows shots and explosions as the extruded sprites instead of the remastered effects.

## License

GPL-2.0-or-later. This project derives from OpenTyrian, which uses the same license; see
[LICENSE](LICENSE). The Tyrian game data has its own freeware terms and isn't covered by this license.

## Local build with the remaster

To play the complete game locally with everything generated, including the private remastered music
(the `tyrian3d-remaster` repo, cloned next to this one, and `tools/build_manifest.py` run there):

    npm run play:local        # builds to dist-local/ and serves it at http://localhost:4173

It loads the game data from `data/` (or `TYRIAN_DATA`) and the remaster from
`../tyrian3d-remaster/out` (or `TYRIAN_REMASTER`). The title screen then offers Original,
Orchestral and Synth music (`M` cycles; `?music=synth` picks one). `npm run dev` does the same with
hot reload. Neither copies anything private into a build, and the deployed site never asks for it.

