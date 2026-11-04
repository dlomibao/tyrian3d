export const meta = {
  name: 'terrain-hd',
  description: "HD terrain for a tileset via Gemini: inventory + sheets (and game-side work if needed) in parallel, one Gemini operator one request at a time, assemble seam-free atlases, capture, verify",
  whenToUse: 'A tileset (or level) needs HD terrain art (D57-D60). See docs/agents/WORKFLOWS.md and docs/terrain-pipeline.html.',
  phases: [{ title: 'Prep' }, { title: 'Tool' }, { title: 'Generate' }, { title: 'Assemble' }, { title: 'Capture' }, { title: 'Verify' }, { title: 'Bench' }],
}

// Generalised from terrain-hd (TYRIAN 1-9, shapesz: 5 agents, ~108 min, 27 Gemini requests in ~40 min).
// The tool (tools/terrain_hd.py) and the game side (D57) exist now, so prep is mostly running them.
//
// args = {
//   worktree, scratch,                 // required; the work folder defaults to <scratch>/work
//   levels: ['1-9'],                   // episode-file level ids (as terrain_hd.py --level takes), or ['all'] with tileset: every level using it (D83)
//   tileset: 'shapesz',                // for the briefs and the atlas path public/art/terrain/<tileset>/
//   gameSide: 'optional brief',        // renderer/settings work this tileset needs (runs beside prep, Opus)
//   maxRequests: 25,                   // Gemini budget for this run (Pro warned "running low" after ~25)
//   ticks: [1, 300, 1000, 2000, 3000], // capture ticks per level for verification
//   tiers: { prep, tool, gameSide, gemini, assemble, capture, captureFallback, verify },  // all default to Opus (medium)
//   bench: { stages: ['prep', 'capture'], model: 'sonnet'|'haiku' }, date: 'YYYY-MM-DD',  // 'gemini' can't be benched here
//   context, python, data, rev
// }

const A = args || {}
if (!A.worktree || !A.scratch || !A.levels || !A.levels.length) return { error: 'args.worktree, args.scratch and args.levels are required' }
const WT = A.worktree
const SP = A.scratch
const W = A.work || `${SP}/work`
const PY = A.python || '/Users/dlomibao/projects/tyrian3d-remaster/.venv/bin/python'
const DATA = A.data || '/Users/dlomibao/projects/tyrian/data'
const LEVELS = A.levels
const TS = A.tileset || '(the levels\' tileset)'
const LVARG = LEVELS.length === 1 && LEVELS[0] === 'all' && A.tileset ? `--tileset ${A.tileset}` : `--level ${LEVELS.join(',')}`
const MAXREQ = A.maxRequests || 25
const TICKS = A.ticks || [1, 300, 1000, 2000, 3000, 4200, 5500]
const LOCK = '/Users/dlomibao/projects/tyrian-scratch/gemini.lock'

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
if (BENCH && BENCH.stages.includes('gemini')) {
  // Benching the operator here would send every sheet twice. Bench it by hand on 2 sheets instead.
  BENCH.stages = BENCH.stages.filter(st => st !== 'gemini')
  log('bench: the gemini stage is not benched in-workflow (it would double Gemini requests); bench it by hand')
}
const REV = A.rev ? `\n[run revision ${A.rev}]` : ''

const COMMON = `Tyrian 3D (browser 3D remake of OpenTyrian, three.js + TypeScript). Worktree ${WT} (data/, reference/, .shape are git-ignored links to the original game data: never commit them, nor sheets, answers or contact sheets made from it). Node commands need NODE_OPTIONS=. Tests: TYRIAN_DATA=${DATA} NODE_OPTIONS= npx vitest run --no-fsModuleCache; typecheck NODE_OPTIONS= npx tsc --noEmit. Python with PIL/numpy/scipy: ${PY}. Work folder (survives restarts): ${W}. Scratch: ${SP}.
Task: HD terrain for tileset ${TS}, levels ${LEVELS.join(', ')}. Read docs/terrain-pipeline.html (the whole flow, commands, Gemini tips, known limits) and DECISIONS D57-D60 and D83 first. Commands: ${PY} tools/terrain_hd.py ${LVARG} --work ${W} inventory|sheets|fake|cut [--cache ${W}/cands.pkl]|check (one list of levels for every command). Structure models (src/render/tileModels) still win over HD tiles; atlases go to public/art/terrain/<tileset>/ with a CREDITS.md row (D41). ${A.context || ''}
Other agents may work in this worktree: touch only the files your step names; run no state-changing git commands (the coordinator commits).`

const OUT = { type: 'object', properties: { ok: { type: 'boolean' }, notes: { type: 'string' }, files: { type: 'array', items: { type: 'string' } } }, required: ['ok', 'notes'] }
const PREP = { type: 'object', properties: { ok: { type: 'boolean' }, needsTool: { type: 'boolean' }, toolTask: { type: 'string' }, sheets: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' } }, required: ['ok', 'needsTool', 'notes'] }
const GEN = { type: 'object', properties: { ok: { type: 'boolean' }, done: { type: 'array', items: { type: 'string' } }, missing: { type: 'array', items: { type: 'string' } }, requests: { type: 'number' }, usageWarning: { type: 'boolean' }, notes: { type: 'string' } }, required: ['ok', 'done', 'missing', 'notes'] }
const CAP = { type: 'object', properties: { ok: { type: 'boolean' }, captures: { type: 'array', items: { type: 'string' } }, contact: { type: 'string' }, notes: { type: 'string' } }, required: ['ok', 'captures', 'notes'] }

// Prep (mechanical: run the existing tool), with game-side work beside it when the tileset needs it.
phase('Prep')
const prepTask = () => run('prep', 'prep', `${COMMON}

PREP. Run inventory and sheets into ${W} for all the levels at once (${LVARG}: the tool merges them per tile and the cut merges into the tileset's existing atlas, D83). The sheets are softened and ordered by the tool (sheets/SEND.md: send order, prompts, request count; ground and layer-2 terrain as map regions, the rest as contexts); estimate the Gemini requests against the budget ${MAXREQ} (including retries). Check the inventory: the layer 1-2 kinds (structure tiles are left to models; fix a misread tile with --kind), tiles under structure models, layers with no tiles left, any tile the tool can't handle.
If the tool lacks something this tileset needs (a new layer kind, say), DON'T change it: return needsTool true and toolTask with exactly what is missing. Run ${PY} tools/terrain_hd.py fake and cut/check on the fake answers to prove the flow end to end, cutting into a scratch copy of public/art/terrain/<tileset>/ (--out), never into public/. Return ok, needsTool, toolTask, sheets (primary sheet names in send order), notes (counts per layer, cells, the request estimate).${REV}`, { label: 'prep', phase: 'Prep', schema: PREP })
const gameTask = () => A.gameSide ? run('gameSide', 'game-side', `${COMMON}

GAME-SIDE. You own src/, tests/ and the docs for this change; another agent runs the art tool at the same time. Task: ${A.gameSide}
Keep D57's contract and fallbacks (no manifest / a bad rect / a missing tile → that tile draws as before). Tests, typecheck, a DECISIONS entry (next free Dnn), docs/terrain-pipeline.html updated. Verify in the browser with a synthetic atlas if the real one isn't there yet (captures to ${SP}/game/). Return ok, notes, files.${REV}`, { label: 'game-side', phase: 'Prep', schema: OUT }) : Promise.resolve(null)
let [prep, game] = await parallel([prepTask, gameTask])
if (!prep || !prep.ok) return { error: 'prep failed', prep, game }

if (prep.needsTool) {
  phase('Tool')
  const tool = await run('tool', 'tool', `${COMMON}

TOOL. tools/terrain_hd.py needs: ${prep.toolTask}
Extend it without changing what it produces for already-cut tilesets (re-cut shapesz from its cache if you can and compare bytes, or explain). Keep its CLI documented in its docstring and in docs/terrain-pipeline.html. Then redo the prep steps it blocked: inventory and sheets into ${W}, fake + cut + check end to end. Return ok, notes (what changed, sheets in send order, request estimate), files.${REV}`, { label: 'tool', phase: 'Tool', schema: OUT })
  if (!tool || !tool.ok) return { error: 'tool step failed', prep, tool, game }
  prep = { ...prep, toolNotes: tool.notes }
}

// One Gemini operator: one request at a time, under the shared lock.
phase('Generate')
const gen = await run('gemini', 'gemini', `${COMMON}

GEMINI OPERATOR. Send the primary sheets in ${W}/sheets/ (manifest.json gives each sheet's prompt and aspect ratio; send order: ${(prep.sheets || []).join(', ') || 'as the manifest lists them'}) to Google Gemini in the user's Chrome with the Claude-in-Chrome tools (load them with ONE ToolSearch call: "select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__tabs_close_mcp,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__find"). The user is signed in and allowed downloads.
Follow docs/terrain-pipeline.html section 3 exactly (gemini.google.com/images; a new chat per sheet; PNG to the clipboard with osascript then cmd+V and wait ~6 s; the aspect-ratio menu; the prompt via document.execCommand('insertText'); poll from page JS in calls under 40 s; "Download full size image" ~3 s after the answer appears; answers land in ~/Downloads/Gemini_Generated_Image_*.jpeg).
ONE REQUEST AT A TIME ACROSS ALL AGENTS: before each request take the lock with: set -o noclobber; echo "terrain-hd $(date)" > ${LOCK} ; if that fails another agent holds it: wait 60 s and retry. Remove ${LOCK} as soon as that answer is downloaded (also if the request fails). Use your own new tab and close it at the end.
Save each answer as ${W}/results/<sheet>.png (raw copy in ${W}/results-raw/). Check each at full size against its sheet (grid and layout kept, colours kept, no labels, not a copy of the pixel blocks); retry a bad one at most twice, with the prompt changes the doc suggests (say the material and the viewpoint; softened input). Budget: at most ${MAXREQ} requests in total. If Gemini shows a usage or limit warning, stop at once (release the lock) and report which sheets are done and which are missing. Return ok, done, missing, requests, usageWarning, notes (per sheet: first answer, retries, outcome).${REV}`, { label: 'gemini', phase: 'Generate', schema: GEN })
if (!gen || !gen.done || !gen.done.length) return { error: 'no Gemini answers', prep, game, gen }
if (gen.missing && gen.missing.length) log(`Gemini answers missing for: ${gen.missing.join(', ')} (their tiles fall back unless other sheets cover them)`)

phase('Assemble')
const asm = await run('assemble', 'assemble', `${COMMON}

ASSEMBLE. Gemini report: ${JSON.stringify(gen).slice(0, 2500)}. Run cut (with --cache ${W}/cands.pkl) and check on the real answers in ${W}/results/. Inspect EVERY contact sheet in ${W}/check/ at full size and cut-report.json: no visible seams along the map's pairs, colours close to the original, no labels/text/cell bleed, no copied pixel blocks (blockiness over ~2 → --pick another candidate or let deblock soften it), no made-up marks repeating across the map (--pick or --exclude). A tile with no good painting stays out (it falls back). Report the seam measure (ratio of the step across tile edges to the step inside tiles; TYRIAN reached 0.57 ground, 0.82 clouds). Write the atlas to public/art/terrain/<tileset>/ and add or extend the CREDITS.md row. Update docs/terrain-pipeline.html with anything new about this tileset. Return ok, notes (tiles covered vs inventory, seam measure, picks/exclusions, weak tiles), files.${REV}`, { label: 'assemble', phase: 'Assemble', schema: OUT })
if (!asm || !asm.ok) return { error: 'assemble failed', prep, game, gen, asm }

// Captures are mechanical (a Haiku candidate once benched); retried on tiers.captureFallback if empty.
phase('Capture')
const capPrompt = `${COMMON}

CAPTURES ONLY (no judging, no edits). Start the dev server (TYRIAN_DATA=${DATA} NODE_OPTIONS= npx vite --port <free 5220-5299>, in ${WT}). For each level of ${LEVELS.join(', ')} (find its episode/main numbers for ?debug=play&episode=E&main=N in src/debug/playHarness.ts or the level list) and each tick T of ${TICKS.join(', ')}, capture with node tools/cdpshot.mjs "http://localhost:<port>/?debug=play&episode=E&main=N&seed=1&skip=T&freezeAt=T" <png> 40000 1920 1200 twice: as is (HD) and with &terrain=original appended. Also one at &dpr=0.3 per level. Save to ${SP}/verify/<level>-<T>-hd.png and -orig.png. Make a contact sheet of HD | original pairs with ${PY} (PIL) at ${SP}/verify/contact.jpg. A capture that is blank, black or shows a loading line means the wait was too short: redo it with 60000. Stop the server. Return ok, captures, contact, notes.${REV}`
let cap = await run('capture', 'capture', capPrompt, { label: 'capture', phase: 'Capture', schema: CAP })
if (!cap || !cap.ok || !cap.captures || !cap.captures.length) cap = await agent(capPrompt, { ...tier('captureFallback'), label: 'capture-retry', phase: 'Capture', schema: CAP })

phase('Verify')
const ver = await run('verify', 'verify', `${COMMON}

VERIFY and fix. Assembly report: ${JSON.stringify(asm).slice(0, 2000)}. Game-side report: ${JSON.stringify(game || {}).slice(0, 1200)}. Captures: ${JSON.stringify(cap || {}).slice(0, 2500)} (take more yourself with cdpshot if you need them). Check: no seams, gaps or misplaced tiles; clouds translucent and seamless; colours consistent with the original; structure models still drawn over HD tiles; the fallback (a copy of the manifest without one tile, through &terrainart=<dir>/, draws that tile as the 4x ground, nothing missing); Options → Graphics → Terrain and ?terrain= switch at once; fps/cpu in the debug overlay about the same in both looks. Fix what's wrong (tool, atlas, renderer); run tests and typecheck. Write a DECISIONS entry (next free Dnn on origin/main) for this tileset's atlas and checks. Return ok, notes (what you checked, fixes, remaining issues), files (capture paths first).${REV}`, { label: 'verify', phase: 'Verify', schema: OUT })
return { prep, game, gen, asm, cap, ver, bench: benchReport() }
