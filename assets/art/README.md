# Picture scripts

New artwork for Tyrian's full-screen pictures, for the remastered version: the originals in
`tyrian.pic` come with the game data, whose licence is unresolved (#10), so they can't be shipped.
Each picture is rebuilt in Blender for the same purpose and layout, at 1920x1200 (the original
320x200's 8:5), from the game's own models (`public/models/*.glb`) and procedural materials.

- **One script per picture:** `assets/art/<name>.py` renders `public/art/<name>.webp` (under 600 KB).
  Run it headless from the repository root (never in a live Blender session: it resets the scene):

      /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python assets/art/<name>.py
      ... --python assets/art/<name>.py -- --preview     # 480x300, few samples, to reference/art/<name>.png

- **Shared helpers** (scene, camera, lights, model import, starfields, glows, WebP output) live in
  `common.py`.
- **`public/art/pictures.json`** maps each original picture number (`JE_loadPic`'s id) to its new
  file, relative to the site root. Code that shows a picture looks it up there.
- **The originals,** for comparison: `npm run pictures` decodes them to
  `reference/pictures/pic-NN.png` (git-ignored, as it's derived from the data) and lists every
  episode-script line that shows one (`]P`, `]U`, `]V`, `]R`) in `reference/pictures/uses.txt`.

## The pictures in tyrian.pic

Numbers are `JE_loadPic` ids (1-based); the palette is `pcxpal[id - 1]` (`src/sim/tyrian2.ts`).

| # | Where the game shows it | What it depicts | New picture |
|---|---|---|---|
| 1 | The item screen / shop (`JE_itemScreen`, game_menu.c), also cleared to black behind the super-arcade start | A bronze biomechanical frame: an arched window on the left for the ship, two gauges with helmet and shield icons under it, and a large panel on the right for the menus | `item_screen.webp` |
| 2 | Behind the title screen's submenus: episode and difficulty choice, setup, high scores, the network wait screen (mainint.c, menus.c, opentyr.c) | A red sun with flares on its upper limb, its lower half in shadow, over a blue wireframe grid; "An Epic MegaGames production ©1994" along the bottom | `menu_background.webp` |
| 3 | The in-game frame, one player (`JE_main`, tyrian2.c: `JE_loadPic(twoPlayerMode ? 6 : 3)`) | Black playfield on the left; a bronze side panel on the right with FRONT GUN, REAR GUN and MODE readouts, shield and armour bars; a power bar along the bottom | `hud.webp` |
| 4 | The title screen (`titleScreen`, mainint.c), under the TYRIAN logo and menu | A red planet with white clouds seen from orbit, its limb sweeping from top left to bottom right under a violet haze; red streaks in the bottom left | `title.webp` |
| 5 | The usual backdrop for story text, warnings and secret hints (`]P 005`, all episodes) | A dark violet gas giant in the middle of black space, lit only on its left edge | `story_planet.webp` |
| 6 | The in-game frame, two players | As 3, with two shield/armour panels stacked on the right | `hud_two_player.webp` |
| 7 | End of episode 2 (`]P 007`, levels2 section 13) | A golden dragon's head lying dead on a stone-tiled floor, green crystal growing from a wound behind its eye | `story_dragon.webp` |
| 8 | End of episode 1, panned up to (`]U 008`, levels1 section 42: "If not, things could become unpleasant.") | A flayed, grinning skull impaled on a horn, against a violet sky with a huge planet and a small moon over a spiky black horizon | `story_skull.webp` |
| 9 | End of episode 1 and the news reports that follow (`]P 009`, levels1 section 42) | A dim brown tangle of horns, tendrils and claws in the dark | `story_tangle.webp` |
| 10 | The first intro logo (`intro_logos`, mainint.c) | The publisher's logo: a chrome emblem against a sunlit sky of clouds | `intro_publisher.webp` |
| 11 | Destruct, the hidden artillery game (destruct.c) | Black, with a red status bar for each player across the top | `destruct.webp` |
| 12 | The second intro logo (`intro_logos`) | The developer's logo: a figure holding up an eclipsed sun among smoky clouds, over a grid, the studio name below | `intro_studio.webp` |
| 13 | Episode 4, after the tunnel boss (`]P 013`, levels4 section 32: re-heating planet Zica) | A red grid filling the top for the text; along the bottom, a figure at a heavy gun emplacement in red light | `story_zica.webp` |

`]P 907` (episode 3's ending) is not a picture: numbers over 900 clear the screen and set picture
(n - 900)'s palette. `]P 000` (episode 4) shows `tshp2.pcx`, a separate file.

The logos (10 and 12) and the credit line on 2 belong to their companies, so the new pictures keep
the mood and layout without the names or marks.
