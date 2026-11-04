export const meta = {
  name: 'model-flagship',
  description: 'Hard-surface remodel of sprite models (enemies, bosses, assemblies, ships, sidekicks, structures): scout or list, blueprint, competing designs for heroes, judge, finisher, strict review loop',
  whenToUse: 'Remastering a batch of models to the D65 standard (sprite-authoritative hard-surface, AO bake only). See docs/agents/WORKFLOWS.md for args.',
  phases: [
    { title: 'Setup' },
    { title: 'Scout' },
    { title: 'Blueprint' },
    { title: 'Design' },
    { title: 'Judge' },
    { title: 'Finish' },
    { title: 'Review' },
    { title: 'Bench' },
  ],
}

// Generalised from enemies-flagship (D65; 28 level-1 models, 173 agents, ~147 min) and
// player-ships-flagship / forward-push (D50-D53, the 8 player ships).
//
// args = {
//   worktree: '/Users/dlomibao/projects/tyrian-worktrees/<branch>',   // required, shared by all agents
//   scratch:  '/Users/dlomibao/projects/tyrian-scratch/<task>',       // required, never /private/tmp
//   items: [{ name, kind, tier, script, desc, rev? }],  // kind: enemy|boss|ship|sidekick|structure; tier: hero|standard
//   scout: 'what to list, e.g. every enemy and boss model episode 2 level 3 uses',  // used when items is absent
//   context: 'extra brief for every agent (episode, level, what changed upstream)',
//   setup: 'optional task for a lead agent that builds shared kits first (structures: a lib_<x>.py)',
//   mode: 'full' | 'lean',       // lean: no blueprint, one design, max 2 reviews (E3/E4 "good enough")
//   blueprint: 'all' | 'hero' | 'none',   // default 'all' in full mode, 'none' in lean
//   heroRounds: 3, standardRounds: 2,     // strict-review rounds
//   escalateAfter: 1,            // fix rounds after this many use tiers.fixEscalate
//   tiers: { setup, scout, blueprint, design, judge, finish, fix, fixEscalate, review: 'opus'|'sonnet'|'haiku'|{model, effort} },
//                                // every stage defaults to Opus (medium); set a cheaper one only after a bench
//   bench: { stages: ['finish', 'fix', 'review'], model: 'sonnet', n: 2, only: true },  // bench mode, see below
//   date: 'YYYY-MM-DD',          // stamped on bench rows (scripts can't read the clock)
//   python, blender, data,       // tool paths (defaults below)
//   rev: 0,                      // bump to force a live re-run on resume (the cache is a prefix of calls)
// }

const A = args || {}
if (!A.worktree || !A.scratch) return { error: 'args.worktree and args.scratch are required' }
const WT = A.worktree
const SP = A.scratch
const PY = A.python || '/Users/dlomibao/projects/tyrian3d-remaster/.venv/bin/python'
const BL = A.blender || '/Applications/Blender.app/Contents/MacOS/Blender'
const DATA = A.data || '/Users/dlomibao/projects/tyrian/data'
const LEAN = A.mode === 'lean'
const BP_MODE = A.blueprint || (LEAN ? 'none' : 'all')

const BENCH_ROOT = `${SP}/bench`
// ---- Tiers and bench mode (docs/agents/PLAYBOOK.md "Model tiers" and "Bench results") ----
// Every stage runs on Opus unless args.tiers names a cheaper model for it, which should happen only
// after a bench confirmed it. Effort is never above 'high'.
const TIER = { opus: { model: 'opus', effort: 'medium' }, sonnet: { model: 'sonnet', effort: 'medium' }, haiku: { model: 'haiku' } }
function asTier(t) {
  const o = typeof t === 'string' ? { ...(TIER[t] || { model: t }) } : { ...t }
  if (o.effort && !['low', 'medium', 'high'].includes(o.effort)) o.effort = 'high'
  return o
}
const tier = (stage) => asTier((A.tiers && A.tiers[stage]) || 'opus')
// args.bench = { stages: ['finish', ...], model: 'sonnet'|'haiku', n: 2, only: true }: for the first n
// items, each benched stage also runs on the cheaper model in a sandbox, an Opus judge compares the two,
// and the rows come back in `bench`. The Opus result is the one used downstream. only: process just
// those n items. Paste the rows into PLAYBOOK.md "Bench results".
const BENCH = A.bench ? { model: 'sonnet', n: 2, only: true, stages: [], ...A.bench } : null
const benchRows = []
const BV = { type: 'object', properties: { verdict: { type: 'string', enum: ['cheap-ok', 'opus-needed'] }, metric: { type: 'string' }, rework: { type: 'string' }, notes: { type: 'string' } }, required: ['verdict', 'metric', 'rework', 'notes'] }
const SANDBOX = (dir) => `BENCH RUN: an Opus agent does this same step for real after you, so do NOT create or edit anything outside ${dir} (not in the worktree, not elsewhere in scratch, no git, no PRs, no Gemini lock unless the step is the Gemini operator). Copy every file you would edit into ${dir} and change the copies; write every output (scripts, .glb, renders, sheets, captures, reports) under ${dir}. Blender: run it on your copy and export only into ${dir} (the script's --out option if it has one, otherwise change your copy's export to common.export_glb(objects, '${dir}/<name>.glb')); never tools/build-models.sh, export_sprite_model or export_tile_model. Tools with --out/--work options: point them into ${dir}. Report paths under ${dir}.`
async function run(stage, key, prompt, opts, readOnly) {
  const benched = BENCH && BENCH.stages.includes(stage) && (!BENCH.keys || BENCH.keys.has(String(key).split(':')[0]))
  if (!benched) return agent(prompt, { ...tier(stage), ...opts })
  const cheapTier = asTier(BENCH.model)
  const dir = `${BENCH_ROOT}/${stage}/${String(key).replace(/[^A-Za-z0-9_.-]/g, '_')}-${cheapTier.model}`
  const cheapPrompt = readOnly ? prompt : `${prompt}\n\n${SANDBOX(dir)}`
  let cheap, canon
  if (readOnly) {
    [cheap, canon] = await parallel([
      () => agent(cheapPrompt, { ...cheapTier, ...opts, label: `${opts.label}:bench-${cheapTier.model}` }),
      () => agent(prompt, { ...TIER.opus, ...opts }),
    ])
  } else {
    cheap = await agent(cheapPrompt, { ...cheapTier, ...opts, label: `${opts.label}:bench-${cheapTier.model}` })
    canon = await agent(prompt, { ...TIER.opus, ...opts })
  }
  const v = await agent(`BENCH JUDGE for Tyrian 3D (don't edit files). The step "${stage}" (item ${key}) was done twice from the same brief: by ${cheapTier.model}${readOnly ? '' : ' in a sandbox (' + dir + ')'} and by Opus (the real result, used downstream).
Brief (start): ${prompt.slice(0, 2500)}
${cheapTier.model} result: ${JSON.stringify(cheap).slice(0, 3000)}
Opus result: ${JSON.stringify(canon).slice(0, 3000)}
Check both yourself, not from their claims: measure what this step's acceptance rules measure (models: top-view IoU per frame vs the sprite, feature overlay, per-region colour, build log, game-camera renders; reviews and audits: same verdict, same real issues found, nothing below threshold passed; captures: complete, not blank, the right ticks; code: tests and typecheck; music: report vs the original, every line present). Would the ${cheapTier.model} output need significant rework to reach the Opus output's quality? verdict cheap-ok or opus-needed; metric: what you compared, with both sides' numbers; rework: what would have to be redone (empty if none).`, { ...TIER.opus, label: `bench-judge:${stage}:${key}`, phase: 'Bench', schema: BV })
  benchRows.push({ step: stage, models: `${cheapTier.model} vs opus`, sample: String(key), metric: v ? v.metric : 'judge failed', verdict: v ? v.verdict : 'none', rework: v ? v.rework : '', date: A.date || 'TODO' })
  return canon
}
function benchReport() {
  if (!BENCH) return null
  log(`bench: ${benchRows.map(r => `${r.step}/${r.sample}: ${r.verdict}`).join('; ') || 'no rows'}`)
  return benchRows
}
// ---- end tiers and bench ----

const REV = (it) => {
  const r = (A.rev || 0) + ((it && it.rev) || 0)
  return r ? `\n[run revision ${r}]` : ''
}

const COMMON = `Tyrian 3D (browser 3D remake of OpenTyrian). Worktree ${WT} (data/, reference/, .shape are git-ignored links; never commit them). Python with PIL/numpy: ${PY}; Blender: ${BL}. Node commands need NODE_OPTIONS=. Tests: TYRIAN_DATA=${DATA} NODE_OPTIONS= npx vitest run --no-fsModuleCache. Dev server: TYRIAN_DATA=${DATA} NODE_OPTIONS= npx vite --port <free 5220-5299> (stop it after). Captures: node tools/cdpshot.mjs "<url>" <out.png> 40000 <w> <h> (waits for models). Scratch (survives restarts): ${SP}/. ${A.context || ''}`

const CONTRACT = {
  enemy: `Keep the game contract exactly: palette materials (pal_<index>) so palettes/fades/hit flash work; the same export path, model path and src/render/spriteModels JSON entry as the current script; EVERY animation frame the current model covers (D17, D46: a frame left behind flashes); for assemblies (assembly-*) keep the piece structure, regions, pivots and per-piece frames; turrets keep their aim pivots. Triangles: small ~2-6k, large/boss ~8-20k.`,
  ship: `Keep the game contract exactly: palette materials (pal_<index>), export through common.export_sprite_model as the current script does (same model path, spriteModels JSON, banking frames). Engines: tyrian_engines extras like the Talon. Triangles ~5-12k.`,
  sidekick: `Keep the game contract exactly: palette materials (pal_<index>), export via common.export_sprite_model with load_sprite(...)["sprites"] so "ungrouped": true is kept (D49), every animation frame. Triangles small (~1-4k).`,
  structure: `Keep the tile contract exactly: lib_tiles.export_tile_model with the same model name, tileset, layer, pattern, keepTiles and minRows as the current script (src/render/tileModels/*.json must not change unless the brief says so); palette materials from the tiles' pixels. Heights: ground models stand at 0 and stay under 0.2 where ground enemies sit on them; layer-2 models within about +-0.35 of their pass. Island rock is the tiles' own pixels as relief (lib_tiles.rock_tile / sprite_rock, ROCK_COLOURS, plain materials, no outline, D63, D66), never slabs or boulders.`,
}
CONTRACT.boss = CONTRACT.enemy

const RULES = `THE USER'S RULES (strict): the ORIGINAL SPRITE is authoritative for (1) the top-down silhouette (match it row by row; top-view IoU vs the sprite mask >= 0.95 at sprite resolution on EVERY frame, except a player ship's banking frames: >= 0.80 half bank / >= 0.70 full bank at its fitted roll and shift from tools/bank_roll.py --fit, never reshaping the model for them (D93, docs/agents/OUTLINE-BORDER.md); round where the sprite is round, no tiers or boxy corners it doesn't have), (2) the position, size and shape of canopies/windshields/eyes/lights/hatches the sprite shows, (3) the major colours: the sprite's own palette index per region (median of each part's pixels, ignoring the darkest shading and brightest highlights, which are lighting), satin metal, not saturated or mirror gold. Concepts and blueprints only guide side/front/rear design and detail where they agree with the sprite. Bright spots are sheen, not bumps; the sprite's outline ring and shading are lighting (tools/calibration/rubric.md, "Reading a sprite"). Hard surfaces stay hard, round parts round, pipes stay pipes; keep every feature in assets/blender/features/<name>.json if it exists.
STYLE: the hard-surface standard of the player ships and level-1 enemies (DECISIONS D50-D53, D65): lofts with chamfered sections, pchip station interpolation, modelled panel lines, machined detail; helpers in assets/blender/usp_talon.py (import it, e.g. "import usp_talon as T"; Part, cbox, hull, pchip, bake_maps) and common.py (outline_shell, palette_material, frame_part, split_assembly). Texture: AO/roughness bake only, "bake": "model" in assets/blender/textures/<name>/maps.json if that folder exists. NO concept projection bake (it reads as crinkled foil). Add the outline shell (common.outline_shell, D51).
UNDERSIDE: only a plausible closed shape, no detail, no iterations spent on it. Detail goes where the tilted top-down game camera sees: top, front, sides, rear.`

const BRIEF = (it) => `${COMMON}
Other agents work on other models in this worktree at the same time: touch only files for your model (its script, its .glb/.json outputs, its textures/<name>/ folder) and ${SP}/${it.name}/. Never edit shared files (common.py, usp_talon.py, lib_*.py, tools/, src/, tests/): copy helpers into your script instead and report what should be shared. Run no state-changing git commands.

GOAL: ${it.kind} "${it.name}" (${it.desc}; current script ${it.script}; reference sprite/frames ${WT}/reference/models/${it.name}/ with sprite.json palette indices, or reference/tiles/ for structures; concept if any under assets/blender/features/concepts/) as a hard-surface model that reads as a real, convincing object from ALL angles (tilted game camera, ?viewer=${it.name}) AND is unmistakably the original sprite in 3D.
${RULES}
${CONTRACT[it.kind] || CONTRACT.enemy}
If an input file named in this brief is missing (for example a scratch file lost to a restart), say so first in notes and rebuild it from the sources before going on.`

// Schemas
const LIST = { type: 'object', properties: { items: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, kind: { type: 'string', enum: ['enemy', 'boss', 'ship', 'sidekick', 'structure'] }, tier: { type: 'string', enum: ['hero', 'standard'] }, script: { type: 'string' }, desc: { type: 'string' } }, required: ['name', 'kind', 'tier', 'script', 'desc'] } }, notes: { type: 'string' } }, required: ['items', 'notes'] }
const SETUP = { type: 'object', properties: { ok: { type: 'boolean' }, guide: { type: 'string' }, files: { type: 'array', items: { type: 'string' } } }, required: ['ok', 'guide'] }
const BPOUT = { type: 'object', properties: { png: { type: 'string' }, json: { type: 'string' }, notes: { type: 'string' } }, required: ['png', 'notes'] }
const DOUT = { type: 'object', properties: { script: { type: 'string' }, glb: { type: 'string' }, sheet: { type: 'string' }, iou: { type: 'number' }, notes: { type: 'string' } }, required: ['script', 'sheet', 'notes'] }
const JOUT = { type: 'object', properties: { winner: { type: 'string' }, scores: { type: 'object' }, grafts: { type: 'array', items: { type: 'string' } }, must_fix: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' } }, required: ['winner', 'grafts', 'must_fix', 'notes'] }
const FOUT = { type: 'object', properties: { ok: { type: 'boolean' }, iou: { type: 'number' }, sheet: { type: 'string' }, cmp: { type: 'string' }, files: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' } }, required: ['ok', 'sheet', 'notes'] }
const ROUT = { type: 'object', properties: { verdict: { type: 'string', enum: ['ship', 'fix'] }, score: { type: 'number' }, iou: { type: 'number' }, issues: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' } }, required: ['verdict', 'score', 'issues', 'notes'] }

// Setup: shared kit by one lead (structures; or anything that needs a new shared helper).
let guide = ''
if (A.setup) {
  phase('Setup')
  const s = await run('setup', 'setup', `${COMMON}

You are the LEAD. Before ${A.items ? A.items.length : 'several'} agents each build one model in parallel (and may not touch shared files), make the shared groundwork: ${A.setup}
Build one item end to end as the worked example if the task names one. Tests and typecheck must pass. Don't commit.
Return ok, files you changed, and guide: an exact how-to for the item agents (helper API, build/bake/render commands, height/origin rules, which files they may touch).${REV()}`, { label: 'setup', phase: 'Setup', schema: SETUP })
  if (!s || !s.ok) return { error: 'setup failed', setup: s }
  guide = `\nLEAD'S GUIDE (follow it): ${s.guide}`
}

// Items: from args, or scouted from the game's data.
let items = A.items
let scout = null
if (!items) {
  if (!A.scout) return { error: 'pass args.items or args.scout' }
  phase('Scout')
  scout = await run('scout', 'scout', `${COMMON}

List the 3D models to remaster: ${A.scout}
Use the game's own data and tools, not guesses: docs/roadmap/inventory.md and tools/inventory.mjs if present; src/sim/levelSprites.ts / src/app/levelPreload.ts (what a level preloads); src/render/spriteModels/*.json and src/render/tileModels/*.json (sprite/tile -> model); reference/models/catalogue.json. Leave out models already rebuilt to the D65 standard (their maps.json says "bake": "model" or their script imports usp_talon) unless the brief says otherwise.
For each: name (model name), kind, tier ('hero' for bosses, assemblies (assembly-*) and large or prominent models; 'standard' otherwise), script (path), desc (what it is, sprite size in px, how often/long it is on screen). If two models share one script or a lib_*.py used only by them, merge them into ONE item named after the script and say so in desc, so two agents never edit the same file. Put shared-file risks in notes. Don't edit files.${REV()}`, { label: 'scout', phase: 'Scout', schema: LIST }, true)
  items = (scout && scout.items) || []
}
items = items.map(i => ({ ...i, kind: i.kind || 'enemy', tier: i.tier || ((i.kind === 'boss' || String(i.name).startsWith('assembly-')) ? 'hero' : 'standard') }))
const heroes = items.filter(i => i.tier === 'hero').length
log(`${items.length} models: ${heroes} hero, ${items.length - heroes} standard; mode ${LEAN ? 'lean' : 'full'}, blueprints ${BP_MODE}`)
if (!items.length) return { scout, results: [] }
if (BENCH) {
  if (BENCH.only) items = items.slice(0, BENCH.n)
  BENCH.keys = new Set(items.slice(0, BENCH.n).map(i => i.name))
  log(`bench: ${BENCH.stages.join(', ')} on ${BENCH.model} vs opus for ${[...BENCH.keys].join(', ')}`)
}

const wantBlueprint = (it) => BP_MODE === 'all' || (BP_MODE === 'hero' && it.tier === 'hero')

const results = await pipeline(items,
  // 1. Blueprint: a multi-view HTML/JS drawing from one 3D point model.
  async (it) => {
    if (!wantBlueprint(it)) return { it, bp: null }
    const bp = await run('blueprint', it.name, `${BRIEF(it)}${guide}

Step 1, BLUEPRINT: write a small HTML/JS page that draws, from ONE 3D point model (named parts, palette indices per region) projected to every view, a multi-view blueprint of ${it.name}: TOP traced from the SPRITE's outline (sprite overlay; must match it) with features where the sprite has them; SIDE, FRONT, REAR, a rough underside outline only, and two shaded 3/4 views. Invent plausible engineering (joints, plates, engines, mounts) consistent with the sprite and its concept. The Talon's blueprint code is the pattern if it exists under /Users/dlomibao/projects/tyrian-scratch/. Render with headless Chrome ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --window-size=2400,1600 --virtual-time-budget=20000 --screenshot=<png> file://<html>) and iterate until the views agree. Write ${SP}/${it.name}/blueprint/. Return png, json, notes.${REV(it)}`, { label: `blueprint:${it.name}`, phase: 'Blueprint', schema: BPOUT })
    return { it, bp }
  },
  // 2. Design: two competing designs for heroes (full mode), one otherwise.
  async ({ it, bp }) => {
    const angles = (it.tier === 'hero' && !LEAN)
      ? [['A', 'Lead with the blueprint geometry and engineering realism (cross-sections first).'], ['B', 'Lead with silhouette and readability from the small tilted game camera, then detail.']]
      : [['A', 'Balance sprite fidelity, game-camera readability and engineering detail.']]
    const designs = (await parallel(angles.map(([id, angle]) => () => run('design', `${it.name}:${id}`, `${BRIEF(it)}${guide}

Step 2, DESIGN ${id}${angles.length > 1 ? ' (competing with one other designer)' : ''}. Angle: ${angle} Blueprint: ${bp ? bp.png + (bp.json ? ' (model ' + bp.json + ')' : '') : 'none (design from the sprite and concept)'}. Write your own script ${SP}/${it.name}/${id}/${it.name}_${id}.py (import common/usp_talon via sys.path; don't edit shared files) exporting ONLY to ${SP}/${it.name}/${id}/${it.name}_${id}.glb (no export_sprite_model / export_tile_model, nothing under public/ or src/). Iterate build -> measure (top-view IoU per frame, feature overlay, per-region colour) -> render (top, side, front, rear, 3/4 high, game camera; one underside view only to check it is closed) beside the sprite -> critique -> fix, until the rules hold and it looks right from every angle. Sheet at ${SP}/${it.name}/${id}/sheet.png. Return script, glb, sheet, iou (worst frame), notes.${REV(it)}`, { label: `design:${it.name}:${id}`, phase: 'Design', schema: DOUT }).then(r => r && { id, ...r })))).filter(Boolean)
    return { it, designs }
  },
  // 3. Judge: only when there are competing designs.
  async ({ it, designs }) => {
    if (!designs.length) return { it, error: 'no designs' }
    if (designs.length === 1) return { it, designs, judge: null }
    const judge = await run('judge', it.name, `${BRIEF(it)}

Step 3, JUDGE (don't edit files). Compare the competing designs of ${it.name}: ${designs.map(d => `${d.id}: sheet ${d.sheet}, glb ${d.glb}, script ${d.script}, iou ${d.iou}; notes ${String(d.notes).slice(0, 1200)}`).join(' | ')}. Load the glbs in Blender, render your own views (game camera, side, front, rear, 3/4; one quick underside check that it is closed) and measure the sprite rules yourself. Criteria in order: sprite fidelity (outline IoU, features, colours), convincing from all angles (no blob, no foil), game-camera read, craft. Return winner (id), scores, grafts (ideas from the other design worth adding, and where), must_fix, notes.${REV(it)}`, { label: `judge:${it.name}`, phase: 'Judge', schema: JOUT }, true)
    return { it, designs, judge }
  },
  // 4. Finish into the real script, then strict review with fix rounds.
  async ({ it, designs, judge, error }) => {
    if (error) return { name: it.name, error }
    const win = designs.find(d => d.id === (judge && judge.winner)) || designs[0]
    const finish = (extra, stage, label) => run(stage, label.replace(/^(finish|fix):/, ''), `${BRIEF(it)}${guide}

${extra ? 'FIX ROUND' : 'Step 4, FINISH'}. ${extra || `Rebuild the real ${it.script} from design ${win.id} (${win.script})${judge ? ' plus the judge\'s grafts and must_fix: ' + JSON.stringify(judge).slice(0, 3500) : ''}.`} Export exactly as the old script did (contract above). Rebuild with tools/build-models.sh -j 2 ${it.script} and read the build log for errors. Measure and render; write ${SP}/${it.name}/final/cmp.png (sprite | top view in palette colours | outline overlay | game camera | 3/4) and sheet.png. Check it in the game if practical (dev server; ?viewer=${it.name} and ?debug=play&seed=1&skip=T&freezeAt=T at a tick when it is on screen; captures with cdpshot). Don't commit. Return ok, iou (worst frame), sheet, cmp, files (repo-relative paths you changed), notes.${REV(it)}`, { label, phase: 'Finish', schema: FOUT })
    let fin = await finish(null, 'finish', `finish:${it.name}`)
    let rev = null
    const rounds = LEAN ? Math.min(2, A.standardRounds || 2) : (it.tier === 'hero' ? (A.heroRounds || 3) : (A.standardRounds || 2))
    const escalateAfter = A.escalateAfter === undefined ? 1 : A.escalateAfter
    for (let round = 1; round <= rounds; round++) {
      rev = await run('review', `${it.name}:${round}`, `${BRIEF(it)}

Step 5, STRICT REVIEW of the finished ${it.name} (don't edit files). Finisher report: ${JSON.stringify(fin).slice(0, 3000)}. Measure the sprite rules yourself (top-view IoU per frame, per-row widths, feature positions, per-region colours) and render your own views (game camera beside the sprite, side, front, rear, 3/4; underside only checked for being closed, never marked down for lacking detail). Check every frame / assembly piece / pivot lines up and the export contract held (git diff of src/render/spriteModels or tileModels shows no change in sprites, frames or patterns). Would a player say it IS the original in 3D and a convincing object from every angle? Any blob, foil, highlight lump, painted shading, open faces, z-fighting, broken frames? Do not pass a model below the IoU threshold or with a lost feature. verdict ship or fix with concrete, fixable issues; score 1-10.${REV(it)}`, { label: `review:${it.name}:${round}`, phase: 'Review', schema: ROUT }, true)
      if (!rev || rev.verdict === 'ship' || round === rounds) break
      const stage = round > escalateAfter ? 'fixEscalate' : 'fix'
      fin = await finish(`Fix round ${round}: the current ${it.script} already holds the earlier work; improve it, don't restart. Reviewer issues:\n${rev.issues.map(i => '- ' + i).join('\n')}\nReviewer notes: ${rev.notes}`, stage, `fix:${it.name}:${round}`)
    }
    return { name: it.name, tier: it.tier, kind: it.kind, winner: win.id, final: fin, review: rev }
  })

const done = results.filter(Boolean)
const failed = done.filter(r => r.error || !r.review || r.review.verdict !== 'ship').map(r => r.name)
if (failed.length) log(`not shipped (run fix-round.js on these): ${failed.join(', ')}`)
return { scout, results: done, notShipped: failed, bench: benchReport() }
