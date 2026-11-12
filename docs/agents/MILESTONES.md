# Milestones: remastering the rest of Tyrian 3D

The numbers come from `docs/roadmap/inventory.md` (made by `tools/inventory.mjs`). The tables below
are generated from it: regenerate with `npm run inventory` and update them; don't hand-edit the counts.
Recipes: `PLAYBOOK.md`. Workflows: `WORKFLOWS.md`.

## Where things stand (2026-11-03, from DECISIONS and the repo)

| Area | Done | Not yet |
|---|---|---|
| Enemy/boss models | Every catalogued frame has a first-generation model (D33). Level 1's 28 rebuilt to the hard-surface standard (D65). | Every other level's models at the D65 standard. |
| Player ships, sidekicks | 8 ships at the Talon standard (D50-D53); 10 sidekicks modelled (`assets/blender/sidekicks/`, D49). | - |
| Structures | TYRIAN's tileset `shapesz` (maps 1-3 and 1-9: D34, D44, D47; island rock D63, D66). | Tilesets `shapes)`, `shapesw`, `shapesx`, `shapesy` (levels per tileset: `shapes)` 4-4, 4-5, 4-6, 4-7, 4-9, 4-10, 4-12, 4-15, 4-17, 4-18; `shapesw` 3-1, 3-4, 3-6, 3-9, 4-8, 4-11, 4-20; `shapesx` 2-1, 2-2, 2-6, 2-10, 2-11, 2-12, 4-13; `shapesy` 1-8, 1-12, 1-17, 3-10, 4-3, 4-19). |
| HD terrain | `shapesz` for map 1-9 only (D57-D60); the tool now covers a tileset's levels together and merges (D83). | Other levels of `shapesz` (sheets ready, D83: 200 ground, 1 layer-1 and 19 layer-2 tiles to paint) and the other four tilesets. |
| Flat art (shots, pickups) | Level 1's 179 frames (D43, D56). | Every other weapon, pickup and level palette. |
| Music, sound effects | All 41 songs x 2 styles (D40); all 38 sounds (D41). | The user's listening notes, as they come. |
| UI | Title (D64), HUD (D61), item screen, menus (D26), 13 pictures (D19). | Options, load/save, high scores, data cubes, story screens still in their first look (README). |
| Checks | Level-1 swap/pop test and preload over episode 1 (D54, D56). | The same tests over episodes 2-4. |

Tyrian 2.1 has four episodes (`tyrian1.lvl`..`tyrian4.lvl` in the data); there is no episode 5
(that came with Tyrian 2000), so there is no E5 milestone unless the data changes.

## Weighting

| Milestones | Treatment |
|---|---|
| Shared foundations, E1, E2 | **Full polish.** Models: `model-flagship.js` full mode (blueprint, competing designs for heroes, strict review ≥ 7/10). Every tile HD, every structure modelled, every frame of flat art, a pixel sweep per level until nothing visible is left. |
| E3, E4 | **Good enough plus shared reuse.** Reuse everything from the shared milestone. Unique models in lean mode (one design, ≤ 2 reviews; pass mark ≥ 6.5/10 and outline IoU ≥ 0.95 (user, 2026-11-03; outline measured per the black-border rule, see PLAYBOOK)). HD terrain for every tileset; structure models only for prominent buildings; a pixel sweep per episode fixing the top issues only. |

## Order of work (shared before unique)

1. **Tool gaps** that block everything after: ~~`terrain_hd.py` inventory over several levels of one
   tileset (D58 limit)~~ done (D83: `--tileset`, merging cuts); a draw recorder for flat-art inventories over every weapon (D43 used one not
   in `tools/`); `modelSwap`/preload tests over episodes 2-4.
2. **Shared enemies**: models drawn in more than one episode, by total screen time.
3. **Tilesets** by number of levels using them: structures kit, then HD terrain.
4. **Shots and pickups** for every weapon and item the shops sell, all episodes at once
   (one Gemini family per weapon).
5. **Remaining UI screens** (mockups first, the user picks).
6. Per episode: unique enemies and bosses, unique structures, then a pixel sweep per level.

## M0: Shared foundations

- **Definition of done:**
  - [ ] Tool gaps above closed, with tests.
  - [ ] Every model used in ≥ 2 episodes at the D65 standard (strict review ≥ 7/10, IoU ≥ 0.95 every frame).
  - [ ] Every tileset: structure kit + HD atlas covering all levels that use it; seam ratio ≤ ~0.6 ground.
  - [ ] Flat art for every shot and pickup frame the game can draw; `MODEL_SWAP_REPORT=1` shows no
        shot or pickup left as an extruded sprite.
  - [ ] Remaining UI screens restyled from a user-picked mockup.
  - [ ] CI green; DECISIONS entries; CREDITS rows for new derived art.
- **Inventory** (`inventory.md`; "tiles left" = tiles used by some level with no HD art and no structure model, layers 0/1/2; est. agents from PLAYBOOK/WORKFLOWS rates: ~6 per full-mode model, 5-9 per terrain-hd run, ~12 Gemini requests per episode of flat art):

  | Asset group | Count | Used in episodes | Already at standard | Workflow | Est. agents | Status |
  |---|---|---|---|---|---|---|
  | Shared enemy/boss models | 97 enemy units not flagship-done, used by ≥ 2 levels (16 of them span ≥ 2 episodes). Top: newsh3-229 (5 levels), newsh3-246 (5 levels), newsh3-271 (4 levels), newsh5-121 (4 levels), newsh5-89 (4 levels) | 81 units in 1 episode, 16 in 2, 0 in 3, 0 in 4 | 167 of 264 shared units | model-flagship (full) | ~582 (97 x ~6) | |
  | Tileset `shapes)` | 1 / 43 / 26 = 70 tiles left / structures n/a (see inventory.md) | E4: 10 levels (4-4, 4-5, 4-6, 4-7, 4-9, 4-10, 4-12, 4-15, 4-17, 4-18) | 0 | terrain-hd + model-flagship (structure) | 5-9 (HD) + ~6 per structure (count n/a) | |
  | Tileset `shapesw` | 13 / 45 / 68 = 126 tiles left / structures n/a (see inventory.md) | E3, E4: 7 levels (3-1, 3-4, 3-6, 3-9, 4-8, 4-11, 4-20) | 0 | same | 5-9 (HD) + ~6 per structure (count n/a) | |
  | Tileset `shapesx` | 8 / 131 / 28 = 167 tiles left / structures n/a (see inventory.md) | E2, E4: 7 levels (2-1, 2-2, 2-6, 2-10, 2-11, 2-12, 4-13) | 0 | same | 5-9 (HD) + ~6 per structure (count n/a) | |
  | Tileset `shapesy` | 0 / 3 / 2 = 5 tiles left / structures n/a (see inventory.md) | E1, E3, E4: 6 levels (1-8, 1-12, 1-17, 3-10, 4-3, 4-19) | 0 | same | 5-9 (HD) + ~6 per structure (count n/a) | |
  | Tileset `shapesz` (other levels) | 9 / 32 / 8 = 49 tiles left (92 structure models exist) | E1-E4: 32 levels, 29 besides map Z (1-9, 1-15, 3-8) | map 1-9 (HD 66 / 15 / 0, in structure models 85 / 0 / 55) | terrain-hd | 5-9 per run; one run for all 32 levels: 32 primary sheets, ~42 Gemini requests (D83) | sheets prepared (D83) |
  | Shot frames | 0 without flat art (of 231; 231 flat) | all | level 1's | flat_art.py + Gemini | ~48 Gemini requests (4 episodes x ~12); agents n/a (see inventory.md) | |
  | Pickup frames | 0 pickup units without flat art (0 frames; of 69 units, 69 flat) | all | level 1's | flat_art.py + Gemini | n/a (see inventory.md) | |
  | UI screens | 6 (see table above) | all | 0 | mockups, then build | n/a (see inventory.md) | |

## M1: Episode 1

- **Part A, level 1 polish:** close the level-1 pixel sweep (its 8 `pix-*` PRs), revisit the rock
  outcrop `assembly-newshe-39` (6.5/10, D65), the damaged frames (done: drawn with the intact models, D87),
  and the weak HD tiles D59 lists. Done when a level-1 pixel sweep finds nothing to fix and the user
  has played it.
- **Part B, the rest of episode 1:** per level, unique models (full), structures, HD terrain if not
  shared, then a pixel sweep.
- **Definition of done:** every level of episode 1 passes a pixel sweep with no open issue; the
  swap test lists only known damage frames; preload covers every model shown; the user has played
  the episode through; CI green.
- **Levels** (script order; sec = section in the episode script; Models: total / shared with ≥ 1 other level (done in M0) / unique to the level / flagship, enemy units from `inventory.md`; HD tiles = tiles with HD art over tiles used, all layers; Structures = structure models matching the map whole; flat art = pickup units and enemy shots without flat art; Est. agents = 3 for the sweep + unique unfinished units x 6 (full, M1/M2) or x 4 (lean, M3/M4); the shared and tileset work is in M0):

  | Level (map id, as `terrain_hd.py --level`) | Name | Tileset | Models: total / shared / unique / at standard | Structures | HD tiles | New flat-art frames | Est. agents | Status |
  |---|---|---|---|---|---|---|---|---|
  | 1-9 | TYRIAN (first level, sec 3) | shapesz | 28 rebuilt (D65) / 30 flagship of 30 total (30 shared, 0 unique) | done (D47, D63, D66) | done (D59) | done (D43) | sweep in flight | polish |
  | 1-15 | TYRIAN (sec 3) | shapesz | 30 / 30 / 0 / 30 | done (map Z, as 1-9) | 81/138 | done | ~3 | todo (same map and models as 1-9) |
  | 1-1 | ASTEROID1 (sec 5) | shapesz | 39 / 32 / 7 / 39 | todo | 59/62 | done | ~3 | todo |
  | 1-2 | ASTEROID2 (sec 6) | shapesz | 36 / 35 / 1 / 36 | todo | 62/65 | done | ~3 | todo |
  | 1-12 | SAVARA (sec 10) | shapesy | 21 / 21 / 0 / 21 | todo | 65/67 | done | ~3 | todo |
  | 1-7 | MINES (sec 13) | shapesz | 9 / 8 / 1 / 9 | todo | 17/20 | done | ~3 | todo |
  | 1-4 | BUBBLES (sec 16) | shapesz | 6 / 4 / 2 / 6 | todo | 41/44 | done | ~3 | todo |
  | 1-5 | DELIANI (sec 19) | shapesz | 21 / 21 / 0 / 21 | todo | 24/79 | done | ~3 | todo |
  | 1-3 | ASTEROID? (sec 21) | shapesz | 41 / 33 / 8 / 41 | 7 matched | 54/57 | done | ~3 | todo |
  | 1-6 | MINEMAZE (sec 23) | shapesz | 12 / 12 / 0 / 12 | todo | 19/30 | done | ~3 | todo |
  | 1-10 | BONUS (sec 25) | shapesz | 14 / 14 / 0 / 14 | todo | 13/16 | done | ~3 | todo |
  | 1-11 | HOLES (sec 28) | shapesz | 18 / 17 / 1 / 18 | 13 matched | 88/90 | done | ~3 | todo |
  | 1-8 | SAVARA (sec 29) | shapesy | 24 / 23 / 1 / 24 | todo | 161/163 | done | ~3 | todo |
  | 1-13 | SOH JIN (sec 31) | shapesz | 8 / 6 / 2 / 8 | todo | 16/18 | done | ~3 | todo |
  | 1-14 | WINDY (sec 33) | shapesz | 7 / 7 / 0 / 7 | 13 matched | 42/49 | done | ~3 | todo |
  | 1-16 | ASSASSIN (sec 36) | shapesz | 12 / 12 / 0 / 12 | todo | 68/71 | done | ~3 | todo |
  | 1-17 | SAVARA V (sec 38) | shapesy | 16 / 16 / 0 / 16 | todo | 152/154 | done | ~3 | todo |
  | 1-18 | ** ALE ** (sec 41) | shapesz | 15 / 15 / 0 / 15 | 14 matched | 16/17 | done | ~3 | todo (bot run never ends: see Known issues) |

## M2: Episode 2

- **Weighting:** full polish, after M0.
- **Definition of done:** as M1 for every level of episode 2.
- **Levels:** same columns as M1.

  | Level (map id, as `terrain_hd.py --level`) | Name | Tileset | Models: total / shared / unique / at standard | Structures | HD tiles | New flat-art frames | Est. agents | Status |
  |---|---|---|---|---|---|---|---|---|
  | 2-1 | TORM (sec 2) | shapesx | 33 / 26 / 7 / 25 | todo | 68/72 | done | ~33 | todo |
  | 2-2 | GYGES (sec 4) | shapesx | 31 / 6 / 25 / 4 | todo | 31/122 | done | ~141 | todo |
  | 2-3 | BONUS (sec 6) | shapesz | 12 / 12 / 0 / 12 | todo | 13/16 | done | ~3 | todo |
  | 2-4 | ASTCITY (sec 8) | shapesz | 31 / 31 / 0 / 30 | todo | 54/56 | done | ~3 | todo |
  | 2-5 | SOH JIN (sec 10) | shapesz | 12 / 11 / 1 / 10 | todo | 0/5 | done | ~9 | todo |
  | 2-6 | GRYPHON (sec 12) | shapesx | 22 / 11 / 11 / 8 | todo | 64/121 | done | ~57 | todo |
  | 2-7 | GEM WAR (sec 15) | shapesz | 9 / 4 / 5 / 9 | todo | 0/5 | done | ~3 | todo |
  | 2-8 | MARKERS (sec 17) | shapesz | 13 / 3 / 10 / 3 | todo | 0/5 | done | ~57 | todo |
  | 2-9 | MISTAKES (sec 19) | shapesz | 25 / 25 / 0 / 15 | todo | 0/5 | done | ~3 | todo |
  | 2-10 | BOTANY A (sec 21) | shapesx | 14 / 14 / 0 / 12 | todo | 69/74 | done | ~3 | todo |
  | 2-11 | BOTANY B (sec 22) | shapesx | 11 / 9 / 2 / 7 | todo | 66/71 | done | ~15 | todo |
  | 2-12 | BONUS (sec 24) | shapesx | 12 / 12 / 0 / 9 | todo | 68/72 | done | ~3 | todo |

## M3: Episode 3

- **Weighting:** good enough plus shared reuse (lean models, prominent structures only, top
  issues of one sweep per episode).
- **Definition of done:** no level of episode 3 shows an extruded enemy or a raw original tile
  where a shared asset exists; unique models at the lean pass mark (≥ 6.5/10, IoU ≥ 0.95); the user has
  played it; CI green.
- **Levels:** same columns as M1.

  | Level (map id, as `terrain_hd.py --level`) | Name | Tileset | Models: total / shared / unique / at standard | Structures | HD tiles | New flat-art frames | Est. agents | Status |
  |---|---|---|---|---|---|---|---|---|
  | 3-3 | GAUNTLET (sec 2) | shapesz | 18 / 18 / 0 / 12 | todo | 29/41 | done | ~3 | todo |
  | 3-4 | IXMUCANE (sec 4) | shapesw | 24 / 18 / 6 / 1 | todo | 58/75 | done | ~27 | todo |
  | 3-5 | BONUS (sec 6) | shapesz | 13 / 12 / 1 / 11 | todo | 23/47 | done | ~7 | todo |
  | 3-7 | STARGATE (sec 8) | shapesz | 9 / 6 / 3 / 6 | todo | 42/46 | done | ~15 | todo |
  | 3-1 | CAMANIS (sec 10) | shapesw | 17 / 10 / 7 / 3 | todo | 57/84 | done | ~31 | todo |
  | 3-6 | FLEET (sec 12) | shapesw | 26 / 10 / 16 / 6 | todo | 23/90 | done | ~67 | todo |
  | 3-2 | AST. CITY (sec 15) | shapesz | 36 / 35 / 1 / 35 | todo | 66/69 | done | ~7 | todo |
  | 3-8 | TYRIAN X (sec 17) | shapesz | 28 / 28 / 0 / 28 | done (map Z, as 1-9) | 81/138 | done | ~3 | todo (same map and models as 1-9) |
  | 3-9 | SAWBLADES (sec 19) | shapesw | 19 / 18 / 1 / 1 | todo | 56/72 | done | ~7 | todo |
  | 3-10 | SAVARA Y (sec 21) | shapesy | 22 / 22 / 0 / 22 | todo | 161/163 | done | ~3 | todo |
  | 3-11 | New Deli (sec 23) | shapesz | 22 / 22 / 0 / 21 | todo | 24/79 | done | ~3 | todo |
  | 3-12 | MACES (sec 25) | shapesz | 8 / 8 / 0 / 2 | todo | 13/16 | done | ~3 | todo |

## M4: Episode 4

- **Weighting and definition of done:** as M3, for episode 4.
- **Levels:** same columns as M1.

  | Level (map id, as `terrain_hd.py --level`) | Name | Tileset | Models: total / shared / unique / at standard | Structures | HD tiles | New flat-art frames | Est. agents | Status |
  |---|---|---|---|---|---|---|---|---|
  | 4-4 | SURFACE (sec 2) | shapes) | 28 / 11 / 17 / 1 | todo | 32/38 | done | ~71 | todo |
  | 4-12 | LAVA RUN (sec 4) | shapes) | 22 / 22 / 0 / 5 | todo | 14/36 | done | ~3 | todo |
  | 4-5 | CORE (sec 6) | shapes) | 15 / 9 / 6 / 3 | todo | 29/31 | done | ~27 | todo |
  | 4-11 | ?TUNNEL? (sec 8) | shapesw | 8 / 7 / 1 / 3 | todo | 25/31 | done | ~7 | todo |
  | 4-8 | ICE EXIT (sec 10) | shapesw | 13 / 13 / 0 / 3 | todo | 3/25 | done | ~3 | todo |
  | 4-1 | HARVEST (sec 12) | shapesz | 13 / 9 / 4 / 8 | 1 matched | 33/70 | done | ~19 | todo |
  | 4-7 | UNDERDELI (sec 14) | shapes) | 24 / 14 / 10 / 4 | todo | 22/24 | done | ~43 | todo |
  | 4-3 | SAVARA IV (sec 16) | shapesy | 16 / 16 / 0 / 13 | todo | 68/70 | done | ~3 | todo |
  | 4-14 | DREAD-NOT (sec 18) | shapesz | 24 / 14 / 10 / 1 | todo | 0/5 | done | ~43 | todo |
  | 4-13 | EYESPY (sec 20) | shapesx | 14 / 7 / 7 / 1 | todo | 29/45 | done | ~31 | todo |
  | 4-15 | BRAINIAC (sec 22) | shapes) | 24 / 14 / 10 / 3 | todo | 15/51 | done | ~43 | todo |
  | 4-16 | NOSE DRIP (sec 25) | shapesz | 13 / 7 / 6 / 2 | 13 matched | 27/42 | done | ~27 | todo |
  | 4-2 | WINDY (sec 27) | shapesz | 8 / 7 / 1 / 7 | 15 matched | 17/21 | done | ~7 | todo |
  | 4-10 | DESERTRUN (sec 29) | shapes) | 7 / 6 / 1 / 1 | todo | 35/41 | done | ~7 | todo |
  | 4-9 | LAVA EXIT (sec 31) | shapes) | 9 / 9 / 0 / 5 | todo | 20/42 | done | ~3 | todo |
  | 4-6 | SIDE EXIT (sec 36) | shapes) | 7 / 7 / 0 / 3 | todo | 20/22 | done | ~3 | todo |
  | 4-17 | TIME WAR (sec 40) | shapes) | 29 / 7 / 22 / 1 | todo | 22/29 | done | ~91 | todo |
  | 4-18 | SQUADRON (sec 45) | shapes) | 8 / 6 / 2 / 1 | todo | 1/3 | done | ~11 | todo (bot run never ends: see Known issues) |
  | 4-19 | APPROACH (sec 47) | shapesy | 13 / 12 / 1 / 7 | todo | 15/16 | done | ~7 | todo |
  | 4-20 | ICESECRET (sec 50) | shapesw | 14 / 14 / 0 / 3 | todo | 22/38 | done | ~3 | todo |

## Estimating agents

Plan with the logged rates (PLAYBOOK.md): full-mode models ~6 agents and ~0.8M logged tokens each,
lean ~3-5 agents; a tileset's HD terrain ~5-9 agents and ~25 Gemini requests; a pixel sweep 2-3
agents plus 2-4 per issue; any first use of a cheaper tier adds a bench (2 agents per benched call).
Totals from the tables above (agents by that formula; M0 is the shared enemy models only, tileset work added from its rows):

| Milestone | Levels | Unique unfinished enemy units | Est. agents |
|---|---|---|---|
| M0 | all 62 (shared work) | 97 shared | ~582 for models + 5-9 per tileset HD run (structures n/a, see inventory.md) + ~48 Gemini requests for flat art |
| M1 | 18 | 0 | 54 |
| M2 | 12 | 49 | 330 |
| M3 | 12 | 35 | 176 |
| M4 | 20 | 98 | 452 |

M1-M4 together: 1012 agents; 182 unique + 97 shared = 279 unfinished enemy units (481 enemy units − 202 flagship, per `inventory.json`).

## Known issues (from the inventory run)

- **Level 1.18 "** ALE **"** crashed the sim in the bot run at tick 2815, in `JE_playerCollide`.
  Fixed (D75): galaga mode doubles enemy values until they wrap, and the C then reads past its item
  tables; the port now reads what the C's reference build reads. In that run the ship picks up
  "weapon 208", which fires nothing, so the bot can't finish ALE (the C stalls the same way); the
  inventory's counts for the level stop growing there.
- **Level 4.18 SQUADRON** ran past the bot's 60,000-tick cap. Not a bug (D75): its waves loop
  forever and the level only ends when the ship is out of lives, which the invulnerable bot never is.
