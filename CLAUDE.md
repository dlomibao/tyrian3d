# Tyrian 3D: agent notes

Browser 3D remake of OpenTyrian (Tyrian 2.1, episodes 1-4): the C's gameplay transliterated to
TypeScript, drawn in three.js. Every enemy, boss and ship is a Blender model of its sprite; shots,
pickups and terrain get painted HD art. Now: remastering the art episode by episode
(`docs/agents/MILESTONES.md`). Read `docs/agents/PLAYBOOK.md` before making any asset.

## Architecture
- `src/sim/`: transliterated OpenTyrian (C names, C integer maths, mt_rand), ~35 Hz tick (D1, D2).
  It never renders; it records a **draw list** (`src/sim/draw.ts`) of sprites and tiles per pass.
- `src/render/`: draw list → 3D. Pass order maps to height, draws lifted along camera rays (D5, D6).
  Meshes carry palette indices; colour comes from the live palette texture (D7).
- Models: `assets/blender/**/*.py` → `public/models/**.glb` + `src/render/spriteModels/*.json`
  (sprites) or `src/render/tileModels/*.json` (tile patterns) (D15, D34). Preloaded per level (D54).
- Flat art: `public/art/sprites/` (shots, pickups; D42) and `public/art/terrain/<tileset>/` (HD
  terrain; D57), each a WebP atlas + manifest; per-sprite/per-tile fallback to the original.
- `src/ui/`, `src/app/`: HTML menus over a 3D backdrop (D26), HUD (D61), title (D64).
- `src/audio/`: OPL + LDS port; remastered music/sfx in `public/tyrian-remaster/` (D40, D41).
- Decisions: `DECISIONS.md` (Dnn). Cite them; add one per real design call.

## Commands (prefix Node commands with `NODE_OPTIONS=`)
```
NODE_OPTIONS= npm run dev                                   # dev server, serves ./data
TYRIAN_DATA=/Users/dlomibao/projects/tyrian/data NODE_OPTIONS= npx vitest run --no-fsModuleCache
NODE_OPTIONS= npx tsc --noEmit                              # typecheck
NODE_OPTIONS= npm run build                                 # typecheck + vite build (what CI runs, after npm test)
TYRIAN_EPISODE_TEST=1 npm test                              # also play every level headless
npm run catalogue; TILES_SHAPES=<x> npm run tiles           # references into reference/ (from the data)
tools/build-models.sh [-j N] [-p previewdir] [-n] script.py ...   # Blender headless builds
```
- Python with PIL/numpy/scipy: `/Users/dlomibao/projects/tyrian3d-remaster/.venv/bin/python`.
  Blender: `/Applications/Blender.app/Contents/MacOS/Blender`.
- Dev server for agents: `TYRIAN_DATA=/Users/dlomibao/projects/tyrian/data NODE_OPTIONS= npx vite --port <free 5220-5299>`; stop it when done.
- Captures: `node tools/cdpshot.mjs "<url>" out.png 30000 <w> <h> [evalExpr]`
  (headless Chrome over CDP; waits for models; plain `--screenshot` fires too early).

## Harness URLs (dev server)
- `?debug=play` real level, bot flying: `&episode=E&main=N &seed=1 &skip=T &freezeAt=T &front=ID&power=P&rear=ID
  &left=ID&right=ID &armor=N` (<6 brings the armour ship) `&difficulty=N` (`&hard=1` = 3, for 1.12 and 1.15) `&solid=1 &steer=left|right &stress=N
  &preload=0 &camera=overhead|tilted|steep &interface=frame|minimal`. Global `tyrianHarness` exposes the draw list.
  Header of `src/debug/playHarness.ts` lists all.
- `?debug=level&episode=E&main=N&front=ID:P&sidekick=L,R&skip=N&god=1` (`src/debug/levelHarness.ts`).
- `?viewer=<model>` sprite vs model; `?debug=models&model=a,b&flash=1`; `?debug=sprites`.
- Looks: `?bg=original`, `?vfx=original`, `?sprites=original`, `?terrain=original|hd`, `?terrainart=<dir>/`.

## Worktrees
Feature work never happens in `/Users/dlomibao/projects/tyrian` (main checkout). Per branch:
```
git -C /Users/dlomibao/projects/tyrian fetch -q origin
git -C /Users/dlomibao/projects/tyrian worktree add /Users/dlomibao/projects/tyrian-worktrees/<b> -b <b> origin/main
cd /Users/dlomibao/projects/tyrian-worktrees/<b>
ln -s ../../tyrian/data data; ln -s ../../tyrian/node_modules node_modules
ln -s ../model-shape/reference reference; ln -s ../model-shape/.shape .shape
```
`.shape` shows as untracked (the ignore rule only matches a directory): never `git add -A`/`git add .`.

## PRs and commits
- Commit with the attribution lines the harness gives. In workflows only the coordinator commits
  unless a stage says otherwise; agents never run state-changing git in a shared worktree.
- Push, open a PR with `gh`, merge **only after CI passes** (`gh pr checks <n> --watch`). The user
  approved merging without review once CI is green. The coordinator deploys after merging.
- New DECISIONS entry: next free Dnn on origin/main, checked right before committing; expect
  renumbering at merge when branches run in parallel.

## Art rules (non-negotiable)
1. **The original sprite wins** on top-down outline, feature placement (cockpits, eyes, lights,
   hatches) and major colours (the sprite's palette index per region). Concepts and blueprints only
   guide side/front/rear and detail where they agree (D52, D65). Measure it: top-view IoU vs the
   sprite mask ≥ 0.95 on every frame, feature overlay, per-region colour.
2. **Highlights are sheen**, not bumps; the sprite's outline ring and shading are lighting, never
   paint or geometry. Judge material first: rock/organic highlights are lit faces (rubric).
3. **Undersides**: a plausible closed shape only. No detail, no review iterations spent there.
4. **No concept-projection bake ("foil")**: hard-surface geometry + AO/roughness bake only,
   `"bake": "model"` in maps.json, outline shell (D50, D51, D65).
5. Keep the game contract: `pal_<index>` materials, every frame, assembly pieces/pivots, export paths.
6. **Never commit the original game data** (`data/`, tyrian21.zip contents, sprite/tile PNGs
   extracted from it, Gemini input sheets, review sheets). Derived art is public, with a
   CREDITS.md row naming the original authors (D3, D16, D41).
7. Judge in the game's own render (headless captures), not only Blender (D53).

## Shared resources
- **Gemini**: one request at a time across all agents. Take the lock before each request:
  `set -o noclobber; echo "<agent> $(date)" > /Users/dlomibao/projects/tyrian-scratch/gemini.lock`
  (fails → wait 60 s, retry); `rm` it as soon as that answer is downloaded. Own tab, close it after.
  Stop and report at Gemini's usage warning.
- **Scratch**: long-lived working files go in `/Users/dlomibao/projects/tyrian-scratch/<task>/`.
  The session scratchpad (`/private/tmp/claude-*`) is wiped on restart.
- **Concurrency**: one workflow runs at most 16 agents; at most 20 agents in total. No Fable unless
  the user asks.
- **Model tiers**: Opus for every step unless PLAYBOOK.md "Bench results" shows Sonnet/Haiku
  passed a bench for that step type (bench first, record the verdict); effort never above `high`.
- Blender builds and bakes are CPU-heavy (18-core Mac; `build-models.sh` already uses half the
  cores): with many agents building at once, build only your own scripts and pass `-j` small.

## Docs
- `docs/agents/PLAYBOOK.md`: per-asset recipes, model tiers, lessons from the user's corrections.
- `docs/agents/WORKFLOWS.md` + `tools/workflows/*.js`: reusable Workflow scripts, args, costs, resume.
- `docs/agents/MILESTONES.md`: episode order, definitions of done.
- Pipelines: `docs/art-pipeline.html`, `docs/terrain-pipeline.html`, `docs/music-pipeline.html`;
  modelling: `assets/blender/README.md`, `tools/calibration/rubric.md`.
