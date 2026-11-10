# Tyrian 3D asset inventory

Every episode's levels and what each needs, with what the repo already has, so the remaster of
the rest of the game can go episode by episode with shared assets done first. Generated from
the game data and the repo by `tools/inventory.mjs`; the machine-readable version is
[`inventory.json`](inventory.json) (ids and counts; `levels[].enemies` has every enemy type per level).

**Regenerate:** `npm run inventory` (static parse plus a bot run of every level, a few minutes; `node tools/inventory.mjs --no-play` for the static part only, a few seconds). Needs the Tyrian 2.1 data in `data/` or `TYRIAN_DATA`.

## How to read it

- **Level** `E.N`: episode E, level N of `tyrianE.lvl` (the `]L[` command's level number). A level the
  script reaches from several sections (or on one difficulty only) lists each.
- **Unit**: one piece of modelling work, split the way the Blender scripts are: a multi-piece object
  (`assembly-*`, from `src/viewer/assemblies.json`), else one model script (`newshX-N`, with its
  animation frames `-f2`...), else a sprite with no model yet (`<sheet>-<frame>`). An enemy's damaged
  frames belong to its unit.
- **Status** of a unit: `flagship` = hard-surface model with the outline shell (D50-D53, D65);
  `concept` = concept-baked model (D44); `basic` = the first catalogue model (D15); `partial` = some
  frames have no model; `sprite` = no model; `flat` = flat painted art (D42); `blank` = empty frames.
  Done means `flagship` with every damaged frame modelled (enemies), `flat` (pickups, shots), and HD art
  or a structure model for every tile (tilesets).
- **Events**: level events that create it, summed over levels (static). **Ticks**: ticks on screen in
  the bot run (tests/sim/bot.ts: invulnerable, always firing, sweeping), summed over levels.
- **Conditional**: only the armour ship's chain, which comes to any level when armour is low (D56).
- **2P only**: spawned only by events that two-player (or arcade) games run (event 63 skips them otherwise).

## Per-episode summary

| Episode | Levels | Unique sprites | Enemy units: flagship / older model / total | Damaged frames unmodelled | Tilesets: HD / structure models / total | Boss levels (boss units) | Songs (remastered) | Story pictures (redrawn) |
|---|---|---|---|---|---|---|---|---|
| 1 | 18 | 888 | 87 / 76 / 165 | 0 | 2 / 2 / 2 | 9 (16) | 15 (15) | 3 (3) |
| 2 | 12 | 683 | 31 / 113 / 152 | 4 | 2 / 1 / 2 | 6 (22) | 11 (11) | 2 (2) |
| 3 | 12 | 1202 | 75 / 122 / 197 | 0 | 3 / 2 / 3 | 6 (22) | 15 (15) | 1 (1) |
| 4 | 20 | 762 | 27 / 133 / 197 | 0 | 5 / 2 / 5 | 15 (56) | 18 (18) | 3 (3) |

Whole game: 62 levels; 485 enemy units (89 flagship, 349 older-style models, 47 with frames still unmodelled), decor (indestructible boss and scenery pieces) included; 69 pickup and empty units; 5 tilesets (5 with HD art, 2 with structure models); 231 shot frames (231 with flat art); 33 songs used (33 remastered).

Unique sprites counts each enemy and pickup frame (normal and damaged) once per episode; boss units are
the units created with a boss bar's link number (event 79), pieces included.

## Highest-leverage work

Assets not done yet, those used by the most levels first (then episodes, then time on screen in the
bot run, then events). Doing these first means nothing is done twice for a later episode.

### Tilesets

A tileset is one shapes?.dat: HD terrain art (D57) and structure models (D34, D47) are per tileset,
so a tileset shared by many levels is the biggest single piece of terrain work.

| Tileset | Levels | Episodes | Tiles used (layers 0/1/2) | HD art (0/1/2) | In structure models (0/1/2) | Uncovered (0/1/2) | Levels using it |
|---|---|---|---|---|---|---|---|
| shapesz | 32 | 1, 2, 3, 4 | 275 / 60 / 178 | 266 / 16 / 73 | 85 / 0 / 55 | 9 / 44 / 50 | 1.1 ASTEROID1, 1.2 ASTEROID2, 1.3 ASTEROID?, 1.4 BUBBLES, 1.5 DELIANI, 1.6 MINEMAZE, 1.7 MINES, 1.9 TYRIAN, 1.10 BONUS, 1.11 HOLES, 1.13 SOH JIN, 1.14 WINDY, 1.15 TYRIAN, 1.16 ASSASSIN, 1.18 ** ALE **, 2.3 BONUS, 2.4 ASTCITY, 2.5 SOH JIN, 2.7 GEM WAR, 2.8 MARKERS, 2.9 MISTAKES, 3.2 AST. CITY, 3.3 GAUNTLET, 3.5 BONUS, 3.7 STARGATE, 3.8 TYRIAN X, 3.11 New Deli, 3.12 MACES, 4.1 HARVEST, 4.2 WINDY, 4.14 DREAD-NOT, 4.16 NOSE DRIP |
| shapes) | 10 | 4 | 113 / 57 / 26 | 112 / 14 / 0 | 0 / 0 / 0 | 1 / 43 / 26 | 4.4 SURFACE, 4.5 CORE, 4.6 SIDE EXIT, 4.7 UNDERDELI, 4.9 LAVA EXIT, 4.10 DESERTRUN, 4.12 LAVA RUN, 4.15 BRAINIAC, 4.17 TIME WAR, 4.18 SQUADRON |
| shapesw | 7 | 3, 4 | 113 / 73 / 85 | 100 / 28 / 17 | 0 / 0 / 0 | 13 / 45 / 68 | 3.1 CAMANIS, 3.4 IXMUCANE, 3.6 FLEET, 3.9 SAWBLADES, 4.8 ICE EXIT, 4.11 ?TUNNEL?, 4.20 ICESECRET |
| shapesx | 7 | 2, 4 | 199 / 138 / 39 | 191 / 7 / 11 | 0 / 0 / 0 | 8 / 131 / 28 | 2.1 TORM, 2.2 GYGES, 2.6 GRYPHON, 2.10 BOTANY A, 2.11 BOTANY B, 2.12 BONUS, 4.13 EYESPY |
| shapesy | 6 | 1, 3, 4 | 108 / 71 / 47 | 108 / 68 / 45 | 15 / 0 / 0 | 0 / 3 / 2 | 1.8 SAVARA, 1.12 SAVARA, 1.17 SAVARA V, 3.10 SAVARA Y, 4.3 SAVARA IV, 4.19 APPROACH |

### Enemy models (top 40)

| # | Unit | Kind | Status | Levels | Episodes | Events | Ticks | Where |
|---|---|---|---|---|---|---|---|---|
| 1 | newshd-95 | ground | basic | 5 | 3 | 0 | 5108 | 1.1, 1.2, 1.3, 2.4, 3.2 |
| 2 | newshd-152 | ground | basic | 5 | 3 | 0 | 4140 | 1.1, 1.2, 1.3, 2.4, 3.2 |
| 3 | newshd-114 | ground | basic | 5 | 3 | 0 | 3909 | 1.1, 1.2, 1.3, 2.4, 3.2 |
| 4 | newshd-133 | ground | basic | 5 | 3 | 0 | 3027 | 1.1, 1.2, 1.3, 2.4, 3.2 |
| 5 | newshd-5 | ground | basic | 5 | 3 | 0 | 2311 | 1.1, 1.2, 1.3, 2.4, 3.2 |
| 6 | newshd-123 | ground | basic | 5 | 3 | 0 | 2015 | 1.1, 1.2, 1.3, 2.4, 3.2 |
| 7 | newshf-11 | ground | basic | 5 | 3 | 77 | 1868 | 1.8, 1.12, 1.17, 3.10, 4.3 |
| 8 | newshd-43 | ground | basic | 5 | 3 | 3 | 1803 | 1.1, 1.2, 1.3, 2.4, 3.2 |
| 9 | newshd-85 | ground | basic | 5 | 3 | 0 | 1410 | 1.1, 1.2, 1.3, 2.4, 3.2 |
| 10 | newsh3-229 | air+ground | basic | 5 | 1 | 26 | 6135 | 4.5, 4.6, 4.8, 4.15, 4.20 |
| 11 | newsh3-246 | ground | basic | 5 | 1 | 72 | 4584 | 4.6, 4.8, 4.12, 4.15, 4.20 |
| 12 | newshp-191 | air | basic | 4 | 3 | 33 | 3790 | 1.2, 1.3, 2.4, 3.2 |
| 13 | newshp-193 | air | basic | 4 | 3 | 33 | 3790 | 1.2, 1.3, 2.4, 3.2 |
| 14 | newshp-153 | air | basic | 4 | 3 | 33 | 3244 | 1.2, 1.3, 2.4, 3.2 |
| 15 | newshp-155 | air | basic | 4 | 3 | 33 | 3244 | 1.2, 1.3, 2.4, 3.2 |
| 16 | newshc-1 | air | basic | 4 | 3 | 58 | 2436 | 1.5, 3.5, 3.11, 4.1 |
| 17 | assembly-newshd-127 | air | basic | 4 | 3 | 32 | 2164 | 1.1, 1.2, 2.4, 3.2 |
| 18 | newshd-18 | ground | basic | 4 | 3 | 0 | 1793 | 1.2, 1.3, 2.4, 3.2 |
| 19 | newshd-267 | air | basic | 4 | 3 | 23 | 1504 | 1.1, 1.2, 2.4, 3.2 |
| 20 | newshd-169 | air | basic | 4 | 3 | 18 | 1168 | 1.1, 1.2, 2.4, 3.2 |
| 21 | assembly-newshj-191 | custom+ground (boss) | basic | 4 | 2 | 48 | 80439 | 2.1, 2.10, 2.11, 4.11 |
| 22 | assembly-newshj-267 | custom (boss) | basic | 4 | 2 | 12 | 21942 | 2.1, 2.10, 2.11, 4.11 |
| 23 | newshm-117 | air+ground | basic | 4 | 2 | 127 | 5185 | 1.3, 1.6, 1.18, 3.3 |
| 24 | newsh-caret-163 | ground | basic | 4 | 2 | 0 | 2495 | 1.14, 4.2, 4.7, 4.12 |
| 25 | newsh5-121 | air+ground (boss) | basic | 4 | 1 | 94 | 155461 | 4.7, 4.14, 4.15, 4.16 |
| 26 | newsh5-89 | ground (boss) | basic | 4 | 1 | 30 | 52625 | 4.4, 4.9, 4.15, 4.16 |
| 27 | assembly-newshg-191 | air | basic | 4 | 1 | 126 | 16433 | 2.1, 2.10, 2.11, 2.12 |
| 28 | assembly-newshg-267 | air | basic | 4 | 1 | 74 | 7838 | 2.1, 2.10, 2.11, 2.12 |
| 29 | assembly-newshg-231 | air | basic | 4 | 1 | 66 | 7676 | 2.1, 2.10, 2.11, 2.12 |
| 30 | newsh3-271 | ground | basic | 4 | 1 | 4 | 4940 | 4.8, 4.14, 4.15, 4.20 |
| 31 | newshd-228 | ground | basic | 3 | 3 | 0 | 4430 | 1.3, 2.4, 3.1 |
| 32 | newshc-49 | air (boss) | basic | 3 | 3 | 27 | 3620 | 1.5, 3.11, 4.1 |
| 33 | assembly-newshs-13 | air | basic | 3 | 3 | 18 | 3518 | 1.2, 2.4, 3.2 |
| 34 | assembly-newsha-1 | decor+ground | basic | 3 | 2 | 132 | 31314 | 2.5, 2.9, 4.19 |
| 35 | assembly-newsha-229 | decor+ground | basic | 3 | 2 | 132 | 31308 | 2.5, 2.9, 4.19 |
| 36 | newsh7-53 | ground (boss) | basic | 3 | 2 | 182 | 15300 | 3.1, 4.8, 4.20 |
| 37 | newsh-hash-41 | ground (boss) | basic | 3 | 2 | 51 | 7972 | 3.4, 3.9, 4.11 |
| 38 | newsh-hash-39 | ground (boss) | basic | 3 | 2 | 51 | 7963 | 3.4, 3.9, 4.11 |
| 39 | newsh7-152 | ground | basic | 3 | 2 | 172 | 7438 | 3.1, 4.8, 4.20 |
| 40 | newsh-hash-3 | ground (boss) | basic | 3 | 2 | 51 | 6927 | 3.4, 3.9, 4.11 |

396 enemy units are not done; the full list is `ranking.units` in inventory.json.

### Pickups without flat art (top 20)

| # | Unit | Status | Levels | Episodes | Events | Ticks | Where |
|---|---|---|---|---|---|---|---|

0 pickup units have no flat art (`ranking.pickups`); 69 do.

### Shots without flat art (top 25)

Enemy shots are counted per level from each enemy type's turret weapons; player shots per episode from
every weapon and sidekick the episode's shops sell.

| # | Shot (sheet\|size\|frame) | Fired by | Levels (enemy) | Episodes | Ticks |
|---|---|---|---|---|---|

0 shot frames have no flat art (`ranking.shots`); 231 do.

### Music and pictures

Every song a level or the script plays has an orchestral and a synth arrangement (public/tyrian-remaster/manifest.json, D40); nothing to do.
Every story picture the scripts show is redrawn (public/art/pictures.json, D19). Episode 3's `]A[` plays tyrend.anm's original frames (src/app/episodeEnd.ts).

## Per-level rows

Units: enemy units total / flagship / older model / with unmodelled frames (pickups and empty
frames left out). Terrain: tiles with HD art or a structure model over tiles used, per layer.
Structures: structure models whose pattern occurs whole in the map. Bot: the bot run's result,
ticks, and units seen.

### Episode 1

| Level | Name | Sections | Tileset | Terrain covered (0/1/2) | Structures | Enemy types | Units | Bosses | Songs | Special | Bot |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.9 | TYRIAN | 3 (below hard) | shapesz | 66/66 15/16 55/56 | 82 | 126 | 30 / 30 / 0 / 0 | assembly-newsh4-124 | 18, 15 | text window, music fade, song change, enemy continual damage | done, 8169 ticks, 36 seen |
| 1.15 | TYRIAN | 3 (hard+) | shapesz | 66/66 15/16 55/56 | 82 | 127 | 30 / 30 / 0 / 0 | assembly-newsh4-124 | 18, 15 | headlight, text window, music fade, song change, enemy continual damage | done, 8073 ticks, 35 seen |
| 1.1 | ASTEROID1 | 5 | shapesz | 59/60 0/1 0/1 | 0 | 112 | 39 / 16 / 23 / 0 | assembly-newshm-45 | 1 | text window | done, 6116 ticks, 41 seen |
| 1.2 | ASTEROID2 | 6 | shapesz | 62/63 0/1 0/1 | 0 | 104 | 36 / 14 / 21 / 1 | assembly-newshs-165, newshs-267 | 2 | text window | done, 8511 ticks, 41 seen |
| 1.12 | SAVARA | 10 (hard+) | shapesy | 56/56 9/10 0/1 | 0 | 90 | 21 / 17 / 4 / 0 | assembly-newshf-195, assembly-newshf-270 | 33, 22 | difficulty change, music fade, text window, song change | done, 6154 ticks, 27 seen |
| 1.7 | MINES | 13 | shapesz | 17/18 0/1 0/1 | 0 | 40 | 9 / 5 / 4 / 0 | - | 17 | - | done, 1747 ticks, 12 seen |
| 1.4 | BUBBLES | 16 bonus | shapesz | 41/42 0/1 0/1 | 0 | 26 | 6 / 5 / 1 / 0 | - | 26 | colour filter | done, 3267 ticks, 15 seen |
| 1.5 | DELIANI | 19 | shapesz | 24/24 0/13 0/42 | 0 | 85 | 27 / 9 / 18 / 0 | assembly-newshc-197, assembly-newshc-243, assembly-newshc-271, assembly-newsht-39 +4 | 14, 26 | difficulty change, background 2 opaque, music fade, song change, text window, clear enemies | done, 5781 ticks, 31 seen |
| 1.3 | ASTEROID? | 21 bonus | shapesz | 54/55 0/1 0/1 | 7 | 86 | 41 / 17 / 23 / 1 | - | 2 | - | done, 3444 ticks, 38 seen |
| 1.6 | MINEMAZE | 23 bonus | shapesz | 19/20 0/9 0/1 | 0 | 51 | 12 / 8 / 4 / 0 | - | 23 | - | done, 3530 ticks, 14 seen |
| 1.10 | BONUS | 25 bonus | shapesz | 13/14 0/1 0/1 | 0 | 36 | 14 / 14 / 0 / 0 | - | 18 | clear enemies | done, 2005 ticks, 17 seen |
| 1.11 | HOLES | 28 bonus | shapesz | 27/27 15/16 46/47 | 13 | 62 | 18 / 16 / 2 / 0 | - | 24 | special weapon given | done, 4605 ticks, 20 seen |
| 1.8 | SAVARA | 29 | shapesy | 67/67 49/50 45/46 | 2 | 85 | 24 / 17 / 7 / 0 | assembly-newshf-195, assembly-newshf-270 | 33, 22 | clear enemies, text window, music fade, song change | done, 6127 ticks, 30 seen |
| 1.13 | SOH JIN | 31 | shapesz | 16/16 0/1 0/1 | 0 | 39 | 8 / 6 / 2 / 0 | - | 16 | difficulty change | done, 4846 ticks, 8 seen |
| 1.14 | WINDY | 33 bonus | shapesz | 27/31 15/16 0/2 | 13 | 18 | 7 / 5 / 2 / 0 | - | 26 | - | done, 3080 ticks, 7 seen |
| 1.16 | ASSASSIN | 36 | shapesz | 32/33 13/14 23/24 | 0 | 53 | 12 / 12 / 0 / 0 | assembly-newsh4-124 | 36, 15, 35 | blur, headlight, lava, music fade, text window, song change, colour filter, difficulty change | done, 5318 ticks, 12 seen |
| 1.17 | SAVARA V | 38 | shapesy | 58/58 49/50 45/46 | 0 | 63 | 16 / 14 / 2 / 0 | assembly-newshf-195, assembly-newshf-270, assembly-newshi-115, assembly-newshi-154 | 33, 22 | water, text window, music fade, song change | done, 8711 ticks, 17 seen |
| 1.18 | ** ALE ** | 41 | shapesz | 15/15 1/1 0/1 | 14 | 26 | 15 / 12 / 3 / 0 | - | 41, 35 | difficulty change, text window, music fade, song change, map jump | unfinished, 60000 ticks, 10 seen |

Between levels (the episode 1 script): section 11: song 16, picture 5, text; section 26: song 31, picture 5, episode end; section 39: song 9, picture 5, text, song 5, picture 5, text; section 42: song 8, picture 9, text, song 22, pan 8, text, song 38, picture 9, text, picture 9, text, picture 9, text.

### Episode 2

| Level | Name | Sections | Tileset | Terrain covered (0/1/2) | Structures | Enemy types | Units | Bosses | Songs | Special | Bot |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2.1 | TORM | 2 | shapesx | 68/70 0/1 0/1 | 0 | 118 | 33 / 10 / 23 / 0 | assembly-newshh-159, assembly-newshh-197, assembly-newshj-191, assembly-newshj-267 | 28, 22, 6 | difficulty change, music fade, song change, text window, clear enemies | done, 7661 ticks, 38 seen |
| 2.2 | GYGES | 4 | shapesx | 13/15 7/70 11/37 | 0 | 92 | 31 / 1 / 23 / 7 | assembly-newshn-195, newshn-3, newshn-41, newshn-43 +4 | 14, 12 | text window, music fade, song change, difficulty change | done, 6341 ticks, 32 seen |
| 2.3 | BONUS | 6 bonus | shapesz | 13/14 0/1 0/1 | 0 | 22 | 12 / 10 / 2 / 0 | - | 28 | - | done, 1568 ticks, 11 seen |
| 2.4 | ASTCITY | 8 | shapesz | 54/54 0/1 0/1 | 0 | 77 | 31 / 12 / 19 / 0 | - | 1 | difficulty change | done, 6621 ticks, 32 seen |
| 2.5 | SOH JIN | 10 | shapesz | 0/1 0/1 0/3 | 0 | 39 | 10 / 2 / 8 / 0 | - | 4 | - | done, 5180 ticks, 9 seen |
| 2.6 | GRYPHON | 12 | shapesx | 64/67 0/53 0/1 | 0 | 66 | 22 / 1 / 20 / 1 | assembly-newsh0-79, newsh0-1, newsh0-13, newsh0-15 +4 | 24 | background 2 opaque, text window | done, 6602 ticks, 22 seen |
| 2.7 | GEM WAR | 15 | shapesz | 0/1 0/1 0/3 | 0 | 25 | 9 / 1 / 8 / 0 | assembly-newshv-91, newshv-19 | 24 | text window | done, 7920 ticks, 14 seen |
| 2.8 | MARKERS | 17 | shapesz | 0/1 0/1 0/3 | 0 | 23 | 13 / 1 / 12 / 0 | - | 2 | - | done, 3480 ticks, 13 seen |
| 2.9 | MISTAKES | 19 | shapesz | 0/1 0/1 0/3 | 0 | 57 | 23 / 4 / 19 / 0 | - | 17 | text window | done, 3030 ticks, 16 seen |
| 2.10 | BOTANY A | 21 | shapesx | 69/72 0/1 0/1 | 0 | 49 | 14 / 2 / 12 / 0 | assembly-newshj-191, assembly-newshj-267 | 24, 6 | difficulty change, text window, music fade, song change | done, 6467 ticks, 13 seen |
| 2.11 | BOTANY B | 22 | shapesx | 66/69 0/1 0/1 | 0 | 34 | 11 / 2 / 9 / 0 | assembly-newshj-191, assembly-newshj-267 | 13, 6 | difficulty change, text window, music fade, clear enemies, song change | done, 6627 ticks, 10 seen |
| 2.12 | BONUS | 24 bonus | shapesx | 68/70 0/1 0/1 | 0 | 40 | 12 / 2 / 10 / 0 | - | 28 | difficulty change | done, 1430 ticks, 14 seen |

Between levels (the episode 2 script): section 13: song 8, picture 7, text, picture 5, episode end; section 20: picture 5, song 16, text.

### Episode 3

| Level | Name | Sections | Tileset | Terrain covered (0/1/2) | Structures | Enemy types | Units | Bosses | Songs | Special | Bot |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 3.3 | GAUNTLET | 2 | shapesz | 29/31 0/9 0/1 | 0 | 76 | 18 / 6 / 12 / 0 | - | 1 | difficulty change | done, 3051 ticks, 19 seen |
| 3.4 | IXMUCANE | 4 | shapesw | 15/15 26/32 17/28 | 0 | 124 | 24 / 1 / 23 / 0 | assembly-newshr-169, assembly-newshr-273 | 14, 15 | text window, music fade, clear enemies, song change | done, 5781 ticks, 25 seen |
| 3.5 | BONUS | 6 bonus | shapesz | 23/24 0/21 0/2 | 0 | 44 | 13 / 6 / 7 / 0 | - | 28 | difficulty change | done, 5230 ticks, 17 seen |
| 3.7 | STARGATE | 8 | shapesz | 42/44 0/1 0/1 | 0 | 51 | 9 / 5 / 4 / 0 | - | 16 | text window | done, 4815 ticks, 12 seen |
| 3.1 | CAMANIS | 10 | shapesw | 57/59 0/23 0/2 | 0 | 79 | 17 / 2 / 15 / 0 | assembly-newsh7-203, assembly-newshb-115, assembly-newshb-154, assembly-newshb-2 +3 | 4, 5 | text window, colour filter, music fade, song change | done, 7580 ticks, 18 seen |
| 3.6 | FLEET | 12 | shapesw | 23/34 0/1 0/55 | 0 | 106 | 26 / 4 / 22 / 0 | assembly-newsho-156, assembly-newsho-79, newsho-191, newsho-193 | 29 | background 2 opaque, clear enemies, text window | done, 8431 ticks, 26 seen |
| 3.2 | AST. CITY | 15 | shapesz | 66/67 0/1 0/1 | 0 | 100 | 36 / 16 / 20 / 0 | - | 2 | difficulty change | done, 7102 ticks, 37 seen |
| 3.8 | TYRIAN X | 17 | shapesz | 66/66 15/16 55/56 | 82 | 124 | 28 / 28 / 0 / 0 | assembly-newsh4-124 | 18, 15 | difficulty change, text window, music fade, song change, enemy continual damage | done, 6020 ticks, 33 seen |
| 3.9 | SAWBLADES | 19 | shapesw | 15/15 24/29 17/28 | 0 | 82 | 19 / 1 / 18 / 0 | - | 14 | - | done, 5280 ticks, 20 seen |
| 3.10 | SAVARA Y | 21 | shapesy | 67/67 49/50 45/46 | 2 | 89 | 22 / 16 / 6 / 0 | assembly-newshf-195, assembly-newshf-270 | 21, 22, 17 | music fade, song change, text window, clear enemies | done, 5267 ticks, 24 seen |
| 3.11 | New Deli | 23 | shapesz | 24/24 0/13 0/42 | 0 | 85 | 28 / 9 / 19 / 0 | assembly-newshc-197, assembly-newshc-243, assembly-newsht-39, newshc-163 +2 | 14, 26 | difficulty change, music fade, song change, text window, clear enemies | done, 5814 ticks, 32 seen |
| 3.12 | MACES | 25 bonus | shapesz | 13/14 0/1 0/1 | 0 | 37 | 8 / 2 / 6 / 0 | - | 7 | difficulty change | done, 3290 ticks, 11 seen |

Between levels (the episode 3 script): section 13: song 9, anim, text, text, text, picture 5, episode end.

### Episode 4

| Level | Name | Sections | Tileset | Terrain covered (0/1/2) | Structures | Enemy types | Units | Bosses | Songs | Special | Bot |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 4.4 | SURFACE | 2 | shapes) | 32/32 0/5 0/1 | 0 | 71 | 28 / 1 / 16 / 11 | assembly-newsh-caret-77, newsh3-1 | 38 | headlight, difficulty change, text window | done, 6901 ticks, 29 seen |
| 4.12 | LAVA RUN | 4 | shapes) | 14/14 0/21 0/1 | 0 | 73 | 22 / 4 / 18 / 0 | assembly-newsh9-10, assembly-newsh9-85, assembly-newshk-121, newsh3-6 +2 | 17 | flip, lava, difficulty change, text window, colour filter | done, 4514 ticks, 21 seen |
| 4.5 | CORE | 6 | shapes) | 16/16 13/14 0/1 | 0 | 61 | 15 / 3 / 12 / 0 | assembly-newsh3-117, assembly-newsh3-118, assembly-newsh3-96, assembly-newsh3-99 | 23 | water, background 2 opaque, text window, colour filter, level timer, random explosions | done, 7730 ticks, 18 seen |
| 4.11 | ?TUNNEL? | 8 bonus | shapesw | 2/2 15/20 8/9 | 0 | 29 | 8 / 1 / 7 / 0 | assembly-newshj-191, assembly-newshj-267, newsh-hash-1, newsh-hash-3 +2 | 6 | background 2 opaque, text window, music fade, song change, level timer, random explosions | done, 2958 ticks, 7 seen |
| 4.8 | ICE EXIT | 10 | shapesw | 3/3 0/21 0/1 | 0 | 47 | 13 / 3 / 10 / 0 | assembly-newsh-caret-54 | 4 | iced, text window | done, 4574 ticks, 14 seen |
| 4.1 | HARVEST | 12 | shapesz | 16/16 0/1 18/53 | 1 | 47 | 13 / 6 / 7 / 0 | assembly-newsh5-39, assembly-newsh5-45, assembly-newsht-39 | 16 | text window | done, 8588 ticks, 13 seen |
| 4.7 | UNDERDELI | 14 | shapes) | 22/22 0/1 0/1 | 0 | 79 | 24 / 3 / 14 / 7 | assembly-newsh9-10, assembly-newsh9-85, newsh-caret-68, newsh5-121 +3 | 36 | water, background 2 opaque, text window, difficulty change, level timer | done, 9921 ticks, 23 seen |
| 4.3 | SAVARA IV | 16 | shapesy | 68/68 0/1 0/1 | 0 | 51 | 16 / 12 / 4 / 0 | assembly-newshf-195, assembly-newshf-270 | 33 | water, text window | done, 5846 ticks, 19 seen |
| 4.14 | DREAD-NOT | 18 | shapesz | 0/1 0/1 0/3 | 0 | 69 | 24 / 1 / 21 / 2 | assembly-newsh9-10, assembly-newsh9-115, assembly-newsh9-119, assembly-newsh9-197 +10 | 35 | water, difficulty change, background 2 opaque | done, 25038 ticks, 21 seen |
| 4.13 | EYESPY | 20 | shapesx | 29/30 0/14 0/1 | 0 | 53 | 14 / 1 / 12 / 1 | assembly-newsh-caret-196, assembly-newsh9-191, assembly-newsh9-210, assembly-newsh9-39 +3 | 13 | flip, difficulty change, text window, colour filter | done, 12373 ticks, 14 seen |
| 4.15 | BRAINIAC | 22 | shapes) | 14/15 1/17 0/19 | 0 | 75 | 24 / 3 / 21 / 0 | assembly-newsh-caret-123, assembly-newsh-caret-54, assembly-newsh5-198, assembly-newsh5-233 +4 | 38 | headlight, iced-starfield, lava, difficulty change, background 2 opaque, text window, colour filter, random explosions | done, 13870 ticks, 25 seen |
| 4.16 | NOSE DRIP | 25 | shapesz | 14/14 13/14 13/14 | 13 | 34 | 13 / 2 / 11 / 0 | assembly-newsh-caret-269, assembly-newsh5-191, assembly-newsh5-91, newsh5-121 +4 | 18 | water, text window | done, 9734 ticks, 11 seen |
| 4.2 | WINDY | 27 bonus | shapesz | 17/17 0/1 0/3 | 15 | 19 | 8 / 5 / 3 / 0 | - | 1, 31 | song change | done, 3430 ticks, 7 seen |
| 4.10 | DESERTRUN | 29 bonus | shapes) | 35/35 0/5 0/1 | 0 | 32 | 7 / 1 / 6 / 0 | - | 2, 21, 22 | blur, text window, song change | done, 2197 ticks, 15 seen |
| 4.9 | LAVA EXIT | 31 | shapes) | 20/20 0/21 0/1 | 0 | 42 | 9 / 5 / 4 / 0 | assembly-newsh-caret-123, newsh5-51, newsh5-89 | 29 | lava, water, text window | done, 5675 ticks, 9 seen |
| 4.6 | SIDE EXIT | 36 | shapes) | 7/7 13/14 0/1 | 0 | 36 | 7 / 3 / 4 / 0 | - | 23 | lava, background 2 opaque | done, 3818 ticks, 12 seen |
| 4.17 | TIME WAR | 40 | shapes) | 21/21 1/1 0/7 | 0 | 40 | 29 / 1 / 10 / 18 | - | 37 | difficulty change | done, 6060 ticks, 29 seen |
| 4.18 | SQUADRON | 45 | shapes) | 0/1 1/1 0/1 | 0 | 14 | 8 / 1 / 7 / 0 | - | 37 | difficulty change, clear enemies, map jump | unfinished, 60000 ticks, 8 seen |
| 4.19 | APPROACH | 47 | shapesy | 1/1 14/14 0/1 | 0 | 41 | 11 / 3 / 8 / 0 | newsha-199 | 36 | blur, map jump, text window | done, 5013 ticks, 11 seen |
| 4.20 | ICESECRET | 50 | shapesw | 22/23 0/14 0/1 | 0 | 52 | 14 / 3 / 11 / 0 | assembly-newsh-caret-123, assembly-newsh-caret-54 | 35, 4 | blur, headlight, level timer, background wrap, music fade, special weapon given, song change | done, 5030 ticks, 11 seen |

Between levels (the episode 4 script): section 23: song 34, picture 5, text, song 30, picture 5, text, picture 5, text, song 22, picture 5, text, picture 5, text; section 32: picture 13, text; section 37: picture 5, song 9, text; section 38: picture 5, song 29, text; section 41: picture 5, song 37, text, picture 5, text, picture 0, text; section 42: picture 5, song 9, text; section 43: song 8, picture 5, episode end; section 48: picture 5, song 40, text, picture 5, text, picture 5, song 39, text, picture 5, text, picture 5, text, picture 5, text.

## Not determined statically

- Whether a possible enemy shows depends on play: event 66 skips spawns below a difficulty, 61, 70
  and 75 branch on flags and on which enemies are alive, random spawns depend on
  `levelEnemyFrequency`, and an enemy that only animates when event 24 says so may never show its
  other frames. The static lists over-cover; each level's `play.unitsNotSeen` and the ticks show what
  one bot playthrough met.
- An enemy whose shape bank the level never loads is drawn from whatever sheet its enemy slot last
  had (the C's "Ignoring sprite from unloaded shape table"); statically it has `unloadedBank` and no
  unit. The bot run adds what it actually drew to the level (`play.unitsFoundByBot`): 8 level/frame finds, listed in `notes.foundByBot`.
- Player shots depend on what the player buys, so they are per episode (everything its shops sell),
  not per level. Explosions (newsh6.shp, drawn as hot sprites on purpose, D35) are left out.
- Structure-model matches scan the whole map; a level may never scroll to some rows.
- Hard-only level variants are played at hard difficulty; other difficulties' event skips are not played.

