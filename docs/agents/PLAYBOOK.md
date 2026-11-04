# Agent playbook: remastering Tyrian 3D

How to make each kind of asset, which model runs each step, and the rules learned from the user's
corrections. Audience: Claude Code agents and the coordinator running workflows. Terse on purpose;
the reasons are in `DECISIONS.md` (Dnn) and `docs/*.html`.

Read first: `CLAUDE.md` (art rules, worktrees, Gemini lock), then the recipe for your asset type.
Workflows that run these recipes: `docs/agents/WORKFLOWS.md`. Episode order: `docs/agents/MILESTONES.md`.

Cost figures come from the run logs of session 0dbe1f8e (`~/.claude/projects/-Users-dlomibao-projects-tyrian/0dbe1f8e-*/workflows/wf_*.json`:
`agentCount`, `durationMs`, `totalTokens`) and per-agent transcript timestamps. "Tokens" below is the
run log's `totalTokens` figure as logged; what it counts (cache reads or not) wasn't checked, so use
it to compare runs, not to price them.

## Model tiers

Rules (user, 2026-11-03):
- **Every stage runs on Opus unless a bench has confirmed a cheaper model for that step type.**
  The templates default every stage to Opus and take a per-stage `args.tiers` map.
- **Effort never above `high`.** Default `medium` (Opus and Sonnet). `high` only for the hero
  branding asset (the Talon runs used `high`); never `xhigh`/`max`. The templates clamp it.
- **Bench first.** The first time Sonnet or Haiku is used for a step type, run a small piece of it
  on both the cheaper model and Opus and compare with an independent check (metrics, tests, or an
  Opus judge). No significant rework needed → the cheaper model takes the rest of that step type.
  Otherwise Opus. Record the verdict in "Bench results" below so later sessions reuse it. Templates:
  `args.bench` (WORKFLOWS.md).
- No Fable unless the user asks for it in that request.

| Step type | Tier now | Proposed cheaper tier | Status | Why / evidence |
|---|---|---|---|---|
| Design: blueprint, competing designs | Opus | none | - | Invents side engineering and shape language; the whole result rests on it (D50, D65). |
| Judge (pick a winner, grafts) | Opus | none | - | Taste plus measurement; cheap (median 1.3 min). |
| Strict review / regrade | Opus for strict design reviews; Sonnet only for measurement-based refit re-reviews | Sonnet (refit re-reviews only) | benched 2026-11-03: cheap-ok for refit re-reviews | The D74 refit re-review bench (below) gave Sonnet the same verdicts and numbers as Opus, so re-reviews that only remeasure a refit may run on Sonnet. Strict design reviews stay Opus: **Sonnet was lenient here.** forward-push (2026-11-02) used Sonnet reviewers for the 7 player ships: all 7 shipped on round 1, including Supercarrot at IoU 0.944 (target 0.95) and U-Ship with windshield IoU 0.69. The Opus reviewers on the 28 level-1 enemies asked for 15 fix rounds and still failed 4 at the end. |
| Audit (find what's still pixelated, group into issues) | Opus | none | - | Judgement over many captures. |
| Novel fixes (new renderer path, new tool feature, first-of-kind asset) | Opus | none | - | Problem-solving; the pixel-sweep fixes were all different. |
| Music arrangement | Opus | Sonnet | proposed, unbenched | Creative and blind (agents can't hear); the user caught chopped slides once. Bench only with the user listening. |
| UI mockups | Opus | none | - | Taste; the user picks from mockups. |
| Finish from an approved design (port a winning design into the real script, export contract) | Sonnet | Sonnet | benched 2026-11-04: cheap-ok | Shared-enemies bench (D91, below): on newsh3-267 Sonnet's glb was byte-identical to Opus's; on assembly-newsh-caret-123 it needed minor integration fixes only (uncapped outline shells at the piece seams). The strict review that follows stays Opus; escalate a failing fix round to Opus. |
| Fix round with a concrete issue list | Opus | Sonnet | benched: opus-needed (2026-11-04); earlier cheap-ok only for a measurement-only single-sprite refit (2026-11-03) | Shared-enemies bench (D91): Sonnet's fix round on newsh3-267 painted colour regions face by face from a level field, stair-stepped and blotchy, where Opus cut smooth region boundaries. D74 refit bench: Sonnet passed a single-sprite refit (newsh2-89) but hacked the multi-piece assembly-newsh2-87. Fix rounds run on Opus. |
| Revert from backups + rebuild | Opus | Sonnet (effort low) | proposed, unbenched | Used 7 times on Sonnet in the logs (model-fix-loop, lighting pass, level1-models, model-features-2); every one restored the script and rebuilt, rebuilding where `.glb` backups were missing. No Opus comparison was made, so it's not a bench. |
| Small UI/code fix with a precise spec | Opus | Sonnet | proposed, unbenched | forward-push's `ui-fixes` (outline colour, menu ship placement, D55) ran on Sonnet and merged. Single sample. |
| Scout / inventory listing from the game's data | Opus | Sonnet | proposed, unbenched | Reading code and JSON into a list. Mistakes here (merged scripts, missed models) cost every later stage, so bench before switching. |
| Running an existing tool end to end (terrain_hd inventory/sheets/fake, flat_art sheets) | Opus | Sonnet | proposed, unbenched | Mechanical when the tool covers the case; the template returns `needsTool` to Opus when it doesn't. |
| Gemini operator (Chrome, one request at a time) | Opus | Sonnet | proposed, unbenched | Mechanical but fiddly UI driving plus a quality check of each answer. Bench by hand on 2 sheets (an in-workflow bench would double requests). |
| Doc updates, DECISIONS drafts from a finished report | Opus | Sonnet | proposed, unbenched | Writing from facts already gathered. |
| Captures (cdpshot at given ticks), draw-list dumps, contact sheets | Opus | Haiku | proposed, unbenched | No judgement, but a blank capture (models not loaded) must be noticed; templates retry on `tiers.captureFallback`. Haiku has not been used in this project. |
| Renames, file moves, running build-models.sh and reporting the log | Opus | Haiku | proposed, unbenched | No judgement. Untested here. |

Risks to watch when a bench passes: a cheaper reviewer that ships too easily (above); a cheaper
finisher that edits shared files or drops an animation frame (the Opus review catches the second,
`git status` the first); a capture agent that returns blank PNGs as success.

### Bench results

Fill one row per bench (the templates return these rows in `bench`). A step type with a `cheap-ok`
row may use the cheaper model via `args.tiers`; until then it runs on Opus.

| Step type | Models | Sample | Metric | Verdict | Date |
|---|---|---|---|---|---|
| Docs: fill tables from a data file (MILESTONES from inventory.json) | Sonnet 5.5 (medium) vs Opus review | All TODO(inventory) cells in MILESTONES.md | Opus recomputed the headline counts from inventory.json | cheap-ok with a numbers check: structure and per-level rows right; 2 of ~10 headline counts off by 2 (it counted 2 pickups as enemy units) and it called its total "matching" when it did not. Have the agent compute counts with a script, and have the coordinator recheck totals | 2026-11-03 |
| Fix: single-sprite model refit (D74 inner edge) | Sonnet 5.5 (medium) vs Opus (medium), judged by Opus | newsh2-89 | Rule IoU (inner mask): Sonnet 0.9745, Opus 0.9904 | cheap-ok: both pass the gate; small porting rework only | 2026-11-03 |
| Fix: multi-piece assembly refit (D74 inner edge) | Sonnet 5.5 (medium) vs Opus (medium), judged by Opus | assembly-newsh2-87 | Grid IoU: Sonnet 0.96, Opus 0.9888 | opus-needed: Sonnet passed by 0.01 with a geometry hack (an embedded ink mask that warps vertices near edges and squashes bevels) | 2026-11-03 |
| Review: refit re-review | Sonnet 5.5 (medium) vs Opus (medium), judged by Opus | newsh2-89, assembly-newsh2-87 | Verdicts and measured numbers against Opus's | cheap-ok for measurement-based refit re-reviews only (same verdicts, same numbers); strict design reviews stay Opus, given the earlier evidence of Sonnet leniency | 2026-11-03 |
| Finish from an approved design | Sonnet 5.5 vs Opus, judged by Opus | newsh3-267 | GLB and spriteModels entries vs Opus's; sprite_mask rule IoU | cheap-ok: byte-identical glb (310,216 bytes), iou_rule_grid 1.0 on both frames, same as Opus | 2026-11-04 |
| Finish from an approved design | Sonnet 5.5 vs Opus, judged by Opus | assembly-newsh-caret-123 | Script line by line vs Opus's; grid IoU, per-piece IoU | cheap-ok: same design-B geometry, grid IoU 0.9924 both, per-piece IoU identical, the 8 spriteModels JSONs byte-identical; minor integration fixes (uncapped outline shells) | 2026-11-04 |
| Fix round (design issues) | Sonnet 5.5 vs Opus, judged by Opus | newsh3-267 round 1 | sprite_mask rule IoU; colour regions | opus-needed: both pass the gate (Sonnet rule 0.9527 / grid 1.0, Opus 0.9495 / 0.9887), but Sonnet coloured whole faces from a level field: stair-stepped, blotchy colour regions | 2026-11-04 |

## Recipes

Common to all: work in a worktree (`CLAUDE.md`), scratch in `/Users/dlomibao/projects/tyrian-scratch/<task>/`,
one agent per asset touching only its own files, the coordinator commits. Measure, don't eyeball:
every art step has a number (IoU, colour error, seam ratio) and a capture from the real game.

### 1. Enemy and boss models (single-sprite and assemblies)

- **Standard:** D65 (level-1 enemies), D50-D53 (Talon, player ships). Workflow: `tools/workflows/model-flagship.js`.
- **Inputs:** the model name and current script (`assets/blender/enemies/<name>.py`; assemblies
  `assembly-<sheet>-<n>.py`), `reference/models/<name>/` (`sprite.json` palette indices per frame,
  frame PNGs, `assembly.png`), concept `assets/blender/features/concepts/<name>.jpg` if any, feature
  list `assets/blender/features/<name>.json` if any. Which models a level uses: `docs/roadmap/inventory.md`,
  `src/sim/levelSprites.ts`, `src/render/spriteModels/*.json`.
- **Steps:**
  1. Scout or list the models; merge models that share a script or a private `lib_*.py` into one item.
     Tier: hero = boss, `assembly-*`, large or prominent; standard = the rest.
  2. Blueprint: HTML/JS multi-view drawing from one 3D point model, top view traced from the sprite.
  3. Design: two competing designs (A: engineering first, B: silhouette/game camera first) for heroes, one for standard; each in scratch, exporting only to scratch.
  4. Judge (heroes): winner + grafts + must_fix.
  5. Finish into the real script; `tools/build-models.sh -j 2 <script>`; `"bake": "model"` in
     `assets/blender/textures/<name>/maps.json` if that folder exists; outline shell.
  6. Strict review (edits nothing, measures itself): ship or fix; up to 3 rounds for heroes, 2 for standard.
  7. Still failing → `fix-round.js`.
- **Commands:** `tools/build-models.sh -j 2 assets/blender/enemies/<name>.py`;
  `?viewer=<name>` (top view with "Sprite over model"); `?debug=models&model=<name>&flash=1`;
  `?debug=play&seed=1&skip=T&freezeAt=T` at a tick where it is on screen;
  `MODEL_SWAP_REPORT=1` with `tests/render/modelSwap.test.ts` lists sprites still drawn extruded.
- **Accept:** top-view IoU ≥ 0.95 at sprite resolution on every frame against the sprite's *inner*
  mask, its ink border left to the game's outline (`tools/sprite_mask.py <name> --measure top.png`,
  `iou_rule_grid`; [OUTLINE-BORDER.md](OUTLINE-BORDER.md), D74); canopies,
  eyes, lights where the sprite has them; each part in the sprite's palette index for that region;
  every frame and assembly piece/pivot as before (`git diff src/render/spriteModels/` shows no frame
  change); no foil, no highlight lumps; triangles ~2-6k small, ~8-20k boss; strict review score ≥ 7/10.
- **Failure modes → fix:**

  | Symptom | Fix |
  |---|---|
  | Bright sprite pixels became lumps | Sheen: material (metalness/roughness), not geometry (rubric "Reading a sprite"). |
  | Model dark in game, shading painted on | The sprite's ring and shading are lighting; use mid-tone indices (D39 lighting pass). |
  | Wrinkled "tinfoil" surface | Concept projection bake: remove it, `"bake": "model"` (D50, D65). |
  | Outline boxy / tiered where the sprite is round | pchip plan curve fitted to the sprite mask (D52). |
  | Model reads fatter than its sprite in game | Edge at the inner edge of the ink border; the game's ink is the border (D74). |
  | Colours read saturated brass in game | Judge on headless-Chrome captures, not Blender; lower metalness, cool tint on the bake (D53). |
  | A feature vanished over rounds (Gencore windshield) | Feature list; a lost feature fails review whatever else improved. |
  | Rock round a machine reads as a dark box | Rock is island relief from the sprite's pixels, outside the outline shell (D66). |
  | Animation frame flashes plain | All frames textured/exported together (D46). |
  | Enemy pops from sprite to model | Level preload list (D54); add conditional spawns (D56). |
  | Two agents edited one script | Merge such models into one item at scout time. |
- **Cost/time (enemies-flagship, 28 models: 15 hero, 13 standard):** 173 agents, 147 min wall clock,
  21.8M tokens; 28 blueprints, 43 designs, 15 judges, 43 finish/fix, 43 reviews. Per-agent median:
  blueprint 8 min, design 11 (max 53), judge 1.3, finish/fix 21 (max 49), review 1.3 (max 6.5)
  (medians include the agents redone after the scratch wipe). Result: 24 shipped, 4 needed
  `enemies-fix-round` (12 agents, 44 min, 1.5M); 27 of 28 ended at 7-8/10 (D65). Rule of thumb:
  ~6 agents and ~0.8M tokens per model in full mode.
  Lean mode (no blueprint, one design, Opus build + review) is what forward-push did for the 7
  player ships: 16 agents for ships + two unrelated fixes, 42 min (its reviews were Sonnet; see tiers).

### 2. Structure and tile models

- **Standard:** D34 (tile models by pattern), D47 (whole-structure models, biggest pattern wins),
  D63/D66 (island rock from the tiles' own pixels). Workflow: `model-flagship.js` with
  `kind: 'structure'` and `args.setup` for the shared kit.
- **Inputs:** `TILES_SHAPES=<x> npm run tiles` → `reference/tiles/shapes<x>/` (`tiles.json`, maps,
  per-tile PNGs, usual neighbours); the tileset's structure list (scout it into a
  `<tileset>-structures.json` like `assets/blender/features/concepts/tyr-structures.json`); existing
  kits `assets/blender/tiles/lib_tiles.py` (`rock_tile`, `sprite_rock`, `export_tile_model`),
  `lib_l1bld.py`, `lib_tyrbld.py`.
- **Tall buildings** (tiles that paint a roof with a wall below it): check with
  `tools/tall_buildings.py analyse` first; if tall, follow `docs/agents/TALL-BUILDINGS.md` (D82:
  the real building drawn in the art's oblique view, `lib_tall.py`), not the top-view IoU rule.
- **Steps:** (1) Lead: shared kit for the tileset (`lib_<tileset>bld.py`), pattern matching
  (`minRows`, `keepTiles`), one worked example, the real-map test in `tests/render/remaster.test.ts`
  extended. (2) One agent per structure, own `tiles/<prefix>_<unit>.py`. (3) Review from the game
  camera against the original crop. (4) Plain terrain (rock islands) uses `rock_tile`, never slabs
  or boulders.
- **Commands:** `tools/build-models.sh assets/blender/tiles/<script>.py`;
  `TYRIAN_DATA=... NODE_OPTIONS= npx vitest run tests/render/remaster.test.ts tests/render/islandRock.test.ts`;
  `?debug=play&seed=1&skip=T&freezeAt=T` (and `&bg=original` to compare);
  `?debug=sprites&episode=E&level=L&row=R&freeze=F`.
- **Accept:** every pattern told apart from the others and from terrain in every level that uses
  the tileset (remaster test); ground models at 0 and under 0.2 where ground enemies sit, layer-2
  within about ±0.35; no seams against neighbouring rock tiles; no pop from per-tile to structure
  except where `minRows` must (D47); same object and layout as the original from the game camera.
- **Failure modes → fix:** island reads as a grid of tiles → per-pixel relief in shared
  `ROCK_COLOURS`, not per-tile boulders (D63); structure sits in a dark square → its rock unbaked,
  `tyrian_plain` (D63); dark band on the island under an enemy's rock → `tyrian_ground`, no shadow
  (D66); a structure shares tiles with terrain → `minRows` and a real-map test (D44); 970 draw calls
  for a fortress → instanced structures (D34).
- **Cost/time:** tyrian-buildings (12 TYRIAN structures, concept-based, D47): 41 agents, 48 min,
  3.4M tokens; lead 19 min; build median 8 min; grade 0.6; fix 5.5. The concept-bake look it used is
  superseded by the hard-surface rule; budget about one flagship item per structure.

### 3. HD terrain via Gemini

- **Standard:** D57 (game side, contract), D58 (sheets, cutter, seams), D59 (picking paintings),
  D60 (checked in game), D83 (a tileset over all its levels, merging cuts). Full flow and Gemini tips:
  `docs/terrain-pipeline.html`. Workflow: `tools/workflows/terrain-hd.js`.
- **Inputs:** the tileset (`--tileset shapesz`: every level that uses it) or a list of its levels;
  `TILES_SHAPES=<x> npm run tiles`; the structure models already matched (they replace or stand on tiles).
- **Steps:** inventory (all the tileset's levels) → check the layer 1-2 `kind`s (terrain is painted,
  structure is left to models, empty needs nothing; `--kind` fixes a misread tile) → sheets (softened,
  in `SEND.md`'s order; ground and layer-2 terrain as map regions, the rest as contexts) → Gemini, one
  request at a time under `gemini.lock` → `cut --cache` (merges: tiles the atlas has stay byte for
  byte) → `check` → inspect every contact sheet and `cut-report.json` → atlas in
  `public/art/terrain/<tileset>/` + CREDITS row → play the levels in both looks.
- **Commands:**
  ```
  PY=/Users/dlomibao/projects/tyrian3d-remaster/.venv/bin/python; W=/Users/dlomibao/projects/tyrian-scratch/<task>/work
  $PY tools/terrain_hd.py --tileset shapesz --work $W inventory | sheets | fake
  $PY tools/terrain_hd.py --tileset shapesz --work $W cut --cache $W/cands.pkl [--pick 0:68=region-l0-03#0] [--exclude 0:332] [--recut 1:42]
  $PY tools/terrain_hd.py --tileset shapesz --work $W check [--contact new|all|1-11]
  TYRIAN_DATA=... NODE_OPTIONS= npx vitest run tests/render/terrainArt.test.ts tests/tools/terrainHd.test.ts
  ?debug=play&seed=1&skip=T&freezeAt=T  [&terrain=original] [&dpr=0.3] [&terrainart=<dir>/]
  ```
  A fake run cuts into a scratch copy of the tileset folder (`--out`), never into `public/`.
- **Accept:** every terrain tile covered or deliberately left to fall back; `git diff` shows the kept
  atlas images unchanged (only the manifest and new images change); seam ratio (step across tile
  edges / step inside tiles) ≤ ~0.6 ground, ≤ ~0.85 clouds and layer-2 cutouts (TYRIAN: 0.57, 0.82),
  on `check`'s `new` line and per level; NCC ≥ ~0.5 per cell; blockiness ≤ ~2 (deblock softens
  1.6-2.4); colour close to the original; no seams, gaps or misplaced tiles in game at several ticks
  and at `&dpr=0.3`; fallback works with a tile removed.
- **Failure modes → fix:** Gemini copies the pixel blocks → softened sheets (the default now); picks
  scored by blockiness, deblock (D59, D60). Trees drawn from the side → say the material and "seen
  straight down, no trunks" (doc §3; the prompts do). A twig repeated across the map → `novel_detail`
  penalty or `--pick`. Context-painted dirt patches next to region-painted dirt → region bonus (D59).
  HD first frame slow, worm drawn as sprites → atlases uploaded during preload (D60). Gemini "running
  low on usage" after ~25 Pro requests → stop, cut with what exists; next session restore the atlas
  folder (`git checkout -- public/art/terrain/<tileset>`) and cut again with all answers (doc §3).
  Kept tiles meeting in pairs their level never had (TYRIAN's clouds on HOLES: 1.11) → `--recut` that
  layer over all levels, or variants (D83). Metal plating/pipes on layers 1-2 → structure models, not
  paintings (D83). Grey boxes or smears in black space, an edge taking a colour from another level's
  neighbour (green under BONUS's plates) → `cut --edge-aware` (empty tiles are held black by default, D89).
  Gemini repaints what the prompt's material names: SEND.md's group labels can be wrong (grey brick floors
  called "asteroid rock" got buildings and dirt paths); look at the sheet and name its material (D89).
- **Cost/time (TYRIAN, shapesz):** 5 agents, 108 min, 1.2M tokens: prep and game side 23 min in
  parallel, Gemini operator 44 min (27 requests: 21 sheets + 6 retries), assemble 25, verify 16.
  Later tilesets skip the game side. **`shapesz`, its other 31 levels (D83):** 32 primary sheets
  (~42 requests with retries, 2 Gemini sessions), 28 optional. Registration costs ~7 s of CPU per
  sheet (TYRIAN: 3.5 min for 21), but on a loaded machine (load ~60) 24 sheets took 18 min.
  Actual (D89, one operator session): 45 requests (33 primary incl. 2 cloud sheets, 12 retries), no
  usage warning, ~2.5 h of Gemini; the cut of 45 answers took ~2.7 h on a machine at load ~60 (35
  CPU-min), later cuts from `--cache` minutes. Check each answer as it lands (registration per sheet).

### 4. Flat art for shots and pickups

- **Standard:** D42 (game side: flat quads from `public/art/sprites/manifest.json`), D43 (Gemini
  sheets, cutter), D56 (painted tracers for frames Gemini gets wrong). Tool: `tools/flat_art.py`.
- **Inputs:** an inventory of the sprites a level actually draws: play it headless with the bot over
  every weapon/power/sidekick the shops of that episode sell, plus arcade mode for orbs and capsules,
  and record each draw's sheet id and index (D43 "Inventory"; the recorder used then is not in
  `tools/`, so the first agent writes one, or uses `tools/inventory.mjs` if it covers draws). Check it
  against the enemies' turret weapons.
- **Steps:** add the level's families to `SHEET_GROUPS` in `flat_art.py` → `sheets` (at most 12 cells
  of 256 px, mirrored pairs share a cell) → Gemini one at a time (lock) → `cut --check` → contact
  sheet review → frames Gemini can't paint go in `PAINTED` (e.g. `paint_tracer`).
- **Commands:**
  ```
  $PY tools/flat_art.py --palette <level palette> sheets --inventory INV.json --out $W/sheets
  $PY tools/flat_art.py cut --inputs $W/sheets/manifest.json --results $W/results --check $W/check.png
  ?debug=play&front=ID&power=P (A switches the art, N the weapon) &stress=800 for CPU
  ```
- **Accept:** every drawn frame in the atlas from its own cell, facing the right way (mirrored pairs
  included); fit score ≥ ~0.5; alpha is the original silhouette (hitbox reads the same); 2x2 pickups
  seamless across tiles; renderer CPU unchanged at `&stress=800` (D42: 2.7-3.0 ms).
- **Failure modes → fix:** two weapons painted alike (Vulcan vs Pulse) → compare original | atlas
  per frame; paint it (D56). Gemini adds glow → the cutter keeps only the brightest pixels the sprite
  covers. Wide strips refused → keep sheets near a supported aspect. Palette fades don't reach the
  art (by design, D42).
- **Cost/time:** level 1's 179 frames came from 11 sheets (D43); no workflow run log exists for it
  (done in the main loop). Budget ~12 Gemini requests per episode's new families, plus retries.

### 5. Music arrangements

- **Status:** all 41 songs exist in orchestral and synth (D40), so this is for reworking songs after
  the user listens. Pipeline: `docs/music-pipeline.html`; repo `/Users/dlomibao/projects/tyrian3d-remaster`
  (private; per-song worktrees in `/Users/dlomibao/projects/tyrian3d-remaster-wt/song-NN`, branch `song/NN`).
  Workflow: `tools/workflows/music-arrange.js`.
- **Inputs:** `MIDI_OUT=../tyrian3d-remaster/source npm run songs-to-midi` (source MIDI with bends,
  JSON, original OGG); the existing `arrangements/<style>/song-NN.py`; the user's listening notes.
- **Steps:** one agent per song, both styles; render; read `out/<style>/song-NN.report.png`
  (spectrogram and loudness vs the original); iterate ≤ ~4 times per version; commit and push the
  song branch; the user listens (`tools/export_listen.sh NN`); merge; `tools/build_manifest.py`;
  copy OGGs + manifest into tyrian3d `public/tyrian-remaster/`.
- **Accept:** every line of the original present; bent notes held, never chopped; no render
  warnings (silent notes); report shape follows the original; loops seamless; the user's ear.
- **Failure modes → fix:** slides chopped into short notes → keep `Note.bends`, `Part.bends`
  (user, 2026-10-27); echo channel as a second instrument → `src.echoes()` to delay/reverb; silent
  notes outside a sample's range → `Part.extend`, `split_by_range`; reverb cut at the loop → render_song
  renders twice.
- **Cost/time:** 41 songs: 41 agents, 62 min at 16 concurrent, 7.4M tokens; per song median 19 min
  (max 53).

### 6. Sound effects

- **Status:** all 38 remade (29 effects, 9 voices), public, Options → Sound style (D36, D41).
  Default stays the original sounds.
- **Redo one:** in the remaster repo, `.venv/bin/python tools/sfx.py <ids> [--listen]` (reads the
  originals from `TYRIAN_DATA`), writes `out/sfx/remaster/NN-name.ogg` with a report; copy into
  `public/tyrian-remaster/sfx/remaster/` and the manifest. Keep pitch, timing, length and K-weighted
  loudness of the original; `gain_db` 0-6 dB carries the difference (D36).
- **Accept:** the user listens (nobody had when D36 was written; `listen/LISTENING-NOTES.md` in
  the private repo lists what to check first).

### 7. UI

- **Standard:** one HTML framework over a 3D backdrop (D26, `src/ui/README.md`); HUD as the
  original's bronze frame in SVG (D61); title (D64). Screens still in their first look: Options,
  load, save, high scores, data cubes, story screens (README).
- **Steps:** (1) Read the original screen (JE_loadPic number, the C's layout). (2) 3-4 mockups in
  HTML/CSS/JS in scratch, captured at 16:10, 21:9 and phone. (3) **The user picks** (they chose
  "Faithful bronze" and "Painted motion + Cinematic dawn"). (4) Build the pick with real values
  (wired to the sim, not placeholders), keys/pad/touch, reduced motion, fallbacks. (5) Tests for the
  pure parts (layout, menu state).
- **Accept:** the original's layout and palette; only the original logo, traced (IoU 0.97, D64),
  never a redrawn one; every window shape keeps the playfield corners visible (D61); 60 fps, no new
  fonts or CDNs; Options rows follow the Music/Sound/Terrain style-row pattern (D57, D61).
- **Failure modes → fix:** mockup redraws the logo → trace the sprite (user, 2026-11-03); panel hides
  the menu ship → measure the free slot (D55); playfield cut off → fit the camera to the opening (D61).
- **Cost/time:** HUD and title were built in the main loop and side agents; no comparable run log.

### 8. Verification captures

- **Tools:** `node tools/cdpshot.mjs "<url>" out.png <waitMs> <w> <h> [evalExpr]`
  (CDP headless Chrome, Metal ANGLE, prints `evalExpr`'s JSON; use 30-60 s waits so models load);
  `?debug=play` (bot, `seed`, `skip`, `freezeAt`, weapons, `armor`, `camera`, `interface`);
  `?debug=level`; `?viewer=<name>`; `?debug=models`; `python tools/review_sheet.py <name> --which current --out DIR`
  (12-panel sheet + metrics JSON); `tests/render/modelSwap.test.ts` (`MODEL_SWAP_REPORT=1`).
- **Standard set per level:** every ~250 ticks across the level, plus explosions, boss damage and
  death, pickups and coin values, `&armor=3` (armour ship), sidekick shots, shield/hurt flashes,
  messages/HUD, level start/end; 1920x1200 for review, 3840x2160 for pixel hunting; HD vs
  `&terrain=original` / `&bg=original` pairs; `&dpr=0.3` for far mips.
- **Accept:** no blank or loading frames (redo with a longer wait); the tick in the file name;
  before/after pairs at the same ticks and seed.
- **Failure modes → fix:** plain `--screenshot` fires before models load → cdpshot; harness `skip=`
  locked in original tiles for structures seen before their model loaded → fixed, skip waits for all
  models (D63); Blender preview colours differ from the game → capture the game (D53).

## Lessons (from the user's corrections)

1. **The original sprite is the ruler, written as numbers.** "doesn't match the overhead outline and
   cockpit windshield of original": outline IoU, windshield overlay and per-region palette index are
   acceptance metrics, not suggestions (D52).
2. **Teach taste with examples, not knobs.** "generic height multiplier won't look good": use review
   sheets, the user's calibrated ratings and the rubric (D39, `tools/calibration/rubric.md`).
3. **Name the misreadings.** "the bright spot isn't a hump": highlights are sheen; judge material
   first, "some things aren't metallic".
4. **Guard features, not scores.** The Gencore Phoenix lost its windshield while scores rose: keep
   feature lists; a lost feature is a regression.
5. **Ships and machines are hard surfaces with some round parts.** Pipes stay pipes, blades stay
   blades; never let everything go bubbly.
6. **No projected concept bake.** "blobby with wrinkled tinfoil": blueprint first, modelled detail,
   AO/roughness bake only (D50, D65).
7. **Judge through the game's camera and the game's renderer.** A Blender preview misreported the
   Talon's colours (D53).
8. **Play it.** "the armor recovery ship looks like it is still a sprite", "the Vulcan cannon looked
   more like the pulse cannon": only playing found them; add a test that fails on leftovers (D54, D56).
9. **Spend effort where the camera looks.** Undersides: closed and plausible, nothing more.
10. **Check the premise against the C before "fixing" gameplay.** "the player can't travel fully
    left and right": the limits were already the C's; the real gap was 3.5 px of banking lean (D62).
11. **Agents can't hear.** Slides chopped into short notes went unnoticed until the user listened;
    music needs the user's ear before merging.
12. **Taste decisions go to the user as mockups.** Build 3-4 options, the user picks, then automate
    (HUD, title). Only the original logo, traced.
13. **Budget usage on purpose.** No Fable unless asked; Opus by default, cheaper tiers only after a
    bench; effort at most high; the user moved the agent cap six times (3 → 20).
14. **Respect outside limits.** One Gemini request at a time, under the lock; stop at the usage warning.
15. **Keep state out of temp folders.** A restart wiped the session scratchpad and 2 h of blueprints;
    after a restart, check cached workflow results still point at files that exist (WORKFLOWS.md).
16. **Back up before editing, screen results.** A usage limit cut agents mid-edit, and agents on a
    stale target returned placeholder grades of 1: fixers back up first; screen for placeholders.
17. **Ask what's left before claiming done.** "What other pieces need remastering to have a complete
    asset swap for level 1?": answer from the draw list (pixel sweep), not from memory.
18. **Public by default, credited; original data never.** Derived art, music and sfx are public with
    a CREDITS.md row; the zip's contents and extracts stay out of git (D41).
