# Reusable workflows

Parameterised Workflow scripts in `tools/workflows/`, generalised from the runs that made level 1.
Each takes everything session-specific through `args` (worktree, scratch dir, items, per-stage
model tiers); none hard-codes a session path. Recipes and acceptance rules: `PLAYBOOK.md`.

| Script | For | Based on (run) |
|---|---|---|
| `model-flagship.js` | enemies, bosses, assemblies, ships, sidekicks, structures to the D65 hard-surface standard | enemies-flagship (D65), player-ships-flagship / forward-push (D50-D53), tyrian-buildings (setup lead) |
| `fix-round.js` | items that failed strict review | enemies-fix-round |
| `terrain-hd.js` | HD terrain for a tileset via Gemini | terrain-hd (D57-D60) |
| `pixel-sweep.js` | what still looks pixelated in a level: capture, audit, fix per issue, review | level1-pixel-sweep |
| `music-arrange.js` | reworking songs (all 41 exist) | tyrian-music-arrangements |

## Running one

With the Workflow tool, by path (absolute, from the worktree you are in), args as real JSON:

```
Workflow({
  scriptPath: "/Users/dlomibao/projects/tyrian-worktrees/<branch>/tools/workflows/model-flagship.js",
  args: {
    worktree: "/Users/dlomibao/projects/tyrian-worktrees/<branch>",
    scratch: "/Users/dlomibao/projects/tyrian-scratch/<task>",
    scout: "every enemy and boss model that episode 1 level 2 uses (docs/roadmap/inventory.md)",
    context: "Episode 1, level 2. Level 1's models (D65) are the reference.",
    date: "2026-11-04"
  }
})
```

- Create the worktree (with its symlinks, `CLAUDE.md`) and the scratch dir first. Never use the
  session scratchpad (`/private/tmp/claude-*`) as `scratch`: it is wiped on restart.
- The coordinator commits after the run (pixel-sweep's fixers commit and open PRs on their own
  branches; nothing merges before CI).
- Scripts can't read the clock: pass `date` for bench rows.
- If the user names a model and effort for agents ("opus high"), use these scripts through the
  Workflow tool (it sets both per agent), never the plain Agent tool.

### Common args

| Arg | Meaning |
|---|---|
| `worktree`, `scratch` | required (pixel-sweep: `scratch`, it makes a worktree per issue) |
| `tiers` | per-stage model: `{ finish: 'sonnet', review: 'opus', capture: { model: 'haiku' } }`. **Every stage defaults to Opus, effort medium.** Set a cheaper model only for a step type with a `cheap-ok` row in PLAYBOOK.md "Bench results". Effort above `high` is clamped to `high`. |
| `bench` | `{ stages: [...], model: 'sonnet'\|'haiku', n: 2, only: true }`: see Bench mode |
| `context` | extra brief prepended for every agent (episode, level, what changed upstream) |
| `rev`, `items[i].rev` | bump to force a live re-run on resume (the cache is a prefix: everything from the first changed call on runs live; see Resume) |
| `python`, `blender`, `data` | tool paths; defaults are this Mac's (`tyrian3d-remaster/.venv`, `/Applications/Blender.app`, `~/projects/tyrian/data`) |

### Stage names (keys of `tiers` and `bench.stages`)

| Script | Stages |
|---|---|
| model-flagship | `setup`, `scout`, `blueprint`, `design`, `judge`, `finish`, `fix`, `fixEscalate`, `review` |
| fix-round | `fix`, `fixEscalate`, `review` |
| terrain-hd | `prep`, `tool`, `gameSide`, `gemini`, `assemble`, `capture`, `captureFallback`, `verify` |
| pixel-sweep | `capture`, `captureFallback`, `audit`, `fix`, `fixRound`, `review` |
| music-arrange | `arrange` |

`fixEscalate`: model-flagship's fix rounds after `escalateAfter` (default 1), and fix-round's last
fix, use this tier, so a cheaper fixer that didn't get there hands over to Opus.
`captureFallback`: re-runs a capture that came back empty.

## Bench mode

The rule (PLAYBOOK.md "Model tiers"): before a step type runs on Sonnet or Haiku, bench it.

```
args.bench = { stages: ['finish', 'review'], model: 'sonnet', n: 2, only: true }
```

For the first `n` items, each listed stage runs twice: the cheaper model first, in a sandbox
(`<scratch>/bench/<stage>/<item>-<model>/`; it may not touch the worktree, run git or export into
`public/`), then Opus for real (its result is the one used downstream). Read-only stages (review,
judge, scout, audit) run both side by side with no sandbox. An Opus judge then measures both
(IoU, features, colours, build log; same verdict and issues for reviews; complete captures) and
returns `cheap-ok` or `opus-needed`. `only: true` processes just those `n` items; `false` goes on
with the rest at the normal tiers. The script returns the rows in `bench`: copy them into
PLAYBOOK.md "Bench results", then set `tiers` for the next runs.

- Cost: +2 agents per benched stage call (cheap + judge); sandboxed stages run one after the other.
- `gemini` can't be benched in terrain-hd (it would send every sheet twice): bench the operator by
  hand on 2 sheets, inside the Gemini budget.
- Pixel-sweep's `fix` stage makes worktrees and PRs, which the sandbox forbids: it is novel work and
  stays on Opus; bench `capture`, `review` or `fixRound` instead.
- Music benches need the user's ear: the judge can only compare reports and scripts.

## Expected agents, time and cost

From the logged runs (PLAYBOOK.md explains the token figure). Wall clock assumes the cap of 16.

| Script | Agents | Logged run it is based on |
|---|---|---|
| model-flagship, full | hero 7-10 (blueprint, 2 designs, judge, finish, ≤3 reviews, ≤2 fixes); standard 4-6; +1 setup, +1 scout | 28 models: 173 agents, 147 min, 21.8M tokens (~6.2 agents, ~0.8M per model) |
| model-flagship, `mode: 'lean'` | 3-5 per item (design, finish, ≤2 reviews, ≤1 fix) | forward-push ships: 16 agents incl. 2 other fixes, 42 min |
| fix-round | 2-4 per item | 4 items: 12 agents, 44 min, 1.5M |
| terrain-hd | 5-9 (prep, game side?, tool?, Gemini, assemble, capture, verify) | TYRIAN: 5 agents, 108 min, 1.2M; the Gemini operator alone 44 min for 27 requests |
| pixel-sweep | 2-3 + 2-4 per issue | level 1: audit 27 min, 8 fixers ~31-34 min each (the run was still going when this was written) |
| music-arrange | 1 per song | 41 songs: 41 agents, 62 min, 7.4M |
| any, with `bench` | +2 per benched stage call | none yet |

Per-agent medians to plan with: blueprint 8 min, design 11 (max 53), finish 21 (max 49), review
and judge ~1-2, song 19 (max 53), terrain prep 23.

## Concurrency and file ownership

- One workflow runs at most **16** agents at once (`min(16, CPUs-2)` on this 18-core Mac); more
  queue. The user's overall cap is 20 agents, so a workflow leaves room for ~4 others.
- Gemini: one request at a time across everything, via `/Users/dlomibao/projects/tyrian-scratch/gemini.lock`
  (`CLAUDE.md`). Two Gemini workflows can run together only because of the lock; they still share
  Gemini's usage (~25 Pro requests before its warning).
- **Agents in one workflow touch only their own item's files** (its script, its `.glb`/JSON outputs,
  its `textures/<name>/`, its scratch folder). No shared files (`common.py`, `usp_talon.py`,
  `lib_*.py`, `tools/`, `src/`, `tests/`) unless the stage owns them (a `setup` lead, a game-side or
  tool agent). No state-changing git in a shared worktree. Models that share a script are merged
  into one item at scout time.
- Blender builds are CPU-heavy; the briefs use `tools/build-models.sh -j 2 <own script>`.

## Resume after a restart or a kill

`Workflow({ scriptPath, args, resumeFromRunId })` replays every unchanged agent call from the
cache and runs the rest live. Cached results can point at files that no longer exist (2026-11-02:
the session scratchpad was wiped and 2 h of blueprints and designs had to be redone). Before
resuming:

1. Find the run's journal: `~/.claude/projects/-Users-dlomibao-projects-tyrian/<session>/subagents/workflows/<runId>/journal.jsonl`.
2. List cached results whose files are gone:
   ```
   python3 - <journal.jsonl> <<'EOF'
   import json, os, re, sys
   lab, miss, seen = {}, 0, 0
   for line in open(sys.argv[1]):
       d = json.loads(line)
       if d.get('type') == 'started': lab[d['agentId']] = d.get('label')
       if d.get('type') != 'result': continue
       for p in set(re.findall(r'(/(?:Users|private|tmp)/[^\s"\'`|,;:)\]\\{]+)', json.dumps(d.get('result')))):
           p = p.rstrip('.')
           if '<' in p or '*' in p: continue
           seen += 1
           if not os.path.exists(p): miss += 1; print('MISSING', lab.get(d['agentId']), p)
   print(f'{seen} paths checked, {miss} missing')
   EOF
   ```
   (Run on the enemies-flagship journal it lists the blueprints and designs lost under `/private/tmp`.)
3. The cache is a prefix: calls replay until the first one whose prompt or options changed, and that
   call and every later one run live. So:
   - Few items lost files: start a fresh run (no `resumeFromRunId`) with `args.items` = just those
     items; the finished items' work is already in their files.
   - Nothing lost, run interrupted: resume with the same script and args (100% replay, then live).
   - `rev` (or `items[i].rev`) changes the prompts, which forces a live re-run from that item's first
     call on; use it when a cached result is wrong, not to cherry-pick.
   Agents are also told to rebuild a missing input themselves before going on.
4. Check the worktree too: `git -C <worktree> status --short` (half-done edits from an agent that
   was cut off), and restore from the fixer's backups if a model doesn't build.

## Templates by example

**Episode 2 enemies, full polish (scout from the inventory):**
```
{ worktree, scratch, scout: "every enemy and boss model in episode 2, levels 1-3", context: "...", date }
```

**Episode 3 models, "good enough":**
```
{ worktree, scratch, items: [...from docs/roadmap/inventory.md...], mode: "lean", context: "...", date }
```

**A tileset's structures** (one lead builds the kit, then one agent per structure):
```
{ worktree, scratch, items: [{ name: "shapesx-tower", kind: "structure", tier: "standard", script: "assets/blender/tiles/xbld_tower.py", desc: "..." }],
  setup: "a lib_xbld.py kit for shapesx.dat like lib_tyrbld.py: patterns from <structures.json>, rock via lib_tiles.rock_tile, the remaster test extended; tyrbld_drum.py is the worked example to follow" }
```

**First bench of Sonnet finishing and fixing:**
```
{ worktree, scratch, items: [...2 standard items...], bench: { stages: ["finish", "fix"], model: "sonnet", n: 2, only: true }, date }
```

**Fix the leftovers:**
```
fix-round.js { worktree, scratch, items: [{ name, script, issues: [...from the review...] }], rounds: 2 }
```

**HD terrain for another tileset:**
```
terrain-hd.js { worktree, scratch, levels: ["all"], tileset: "shapesx", maxRequests: 25, ticks: [1, 500, 1500, 3000] }
```
`levels: ["all"]` with `tileset` runs every level of the tileset together (`--tileset`, D75); or list
`["<ep>-<n>", ...]`. The cut merges into the tileset's atlas, so a batch of levels at a time works too.

**Pixel sweep of a level:**
```
pixel-sweep.js { scratch, level: { episode: 1, main: 2, name: "...", ticks: [0, 7000], bossAt: "..." }, exclude: "...", maxIssues: 8 }
```

**Rework songs the user listened to:**
```
music-arrange.js { songs: [{ song: 7, title: "<title>", notes: "the bass drowns the lead after the break" }], styles: ["synth"] }
```
