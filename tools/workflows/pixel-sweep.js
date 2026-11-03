export const meta = {
  name: 'pixel-sweep',
  description: 'Find what still looks pixelated or low-res in a level (Haiku captures + draw-list dumps, Opus audit), fix each issue in its own worktree and PR, strict review with a fix round',
  whenToUse: 'Closing out a level or episode: everything the player sees should be remastered. See docs/agents/WORKFLOWS.md.',
  phases: [{ title: 'Capture' }, { title: 'Audit' }, { title: 'Fix' }, { title: 'Review' }, { title: 'Bench' }],
}

// Generalised from level1-pixel-sweep (TYRIAN: audit ~27 min, then 8 issues fixed in parallel, ~31 min
// each, one worktree + PR per issue).
//
// args = {
//   scratch,                               // required
//   level: { episode: 1, main: 1, name: 'TYRIAN', ticks: [0, 7500], bossAt: '6700-7300' },  // required
//   step: 250,                             // capture every N ticks
//   moments: 'extra special moments to capture',
//   exclude: 'what other agents are already fixing (left out of the audit)',
//   maxIssues: 8,
//   gemini: true,                          // fixers may use Gemini (one request at a time, lock)
//   prs: true,                             // fixers push and open PRs (never merge); false: commit only
//   main: '/Users/dlomibao/projects/tyrian', worktrees: '/Users/dlomibao/projects/tyrian-worktrees',
//   prefix: 'pix',                         // worktree/branch prefix: <prefix>-<issue id>
//   tiers: { capture, captureFallback, audit, fix, fixRound, review },  // all default to Opus (medium)
//   bench: { stages: ['capture', 'fixRound', 'review'], model: 'sonnet'|'haiku', n: 2, only: false }, date: 'YYYY-MM-DD',
//   context, python, rev
// }

const A = args || {}
if (!A.scratch || !A.level) return { error: 'args.scratch and args.level are required' }
const SC = A.scratch
const MAIN = A.main || '/Users/dlomibao/projects/tyrian'
const WTS = A.worktrees || '/Users/dlomibao/projects/tyrian-worktrees'
const PFX = A.prefix || 'pix'
const PY = A.python || '/Users/dlomibao/projects/tyrian3d-remaster/.venv/bin/python'
const L = A.level
const [T0, T1] = L.ticks || [0, 7500]
const STEP = A.step || 250
const MAXI = A.maxIssues || 8
const LOCK = '/Users/dlomibao/projects/tyrian-scratch/gemini.lock'

const BENCH_ROOT = `${SC}/bench`
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
const PLAYURL = (extra) => `?debug=play&episode=${L.episode}&main=${L.main}&seed=1${extra}`

const ENV = `Tyrian 3D: a browser 3D remake of OpenTyrian. Repo ${MAIN} (main is current). Python with PIL: ${PY}. Blender: /Applications/Blender.app/Contents/MacOS/Blender. Node commands need NODE_OPTIONS=. Tests: TYRIAN_DATA=${MAIN}/data NODE_OPTIONS= npx vitest run --no-fsModuleCache. Typecheck: NODE_OPTIONS= npx tsc --noEmit. Dev server: TYRIAN_DATA=${MAIN}/data NODE_OPTIONS= npx vite --port <a free port 5220-5299>; stop it when done. Captures: node tools/cdpshot.mjs "<url>" <out.png> 30000 <w> <h> [evalExpr] (headless Chrome over CDP; waits for models; evalExpr's JSON result is printed). Harness: ${PLAYURL('&skip=T&freezeAt=T&armor=99')}; src/debug/playHarness.ts lists the options (front/power/rear weapons, left/right sidekicks, armor under 6 brings the armour ship, camera, interface); the global tyrianHarness exposes the draw list. The level: episode ${L.episode}, main ${L.main} (${L.name || ''}), ticks ${T0}-${T1}${L.bossAt ? ', boss around ' + L.bossAt : ''}. Context: DECISIONS.md and docs/*.html (models D15/D65, flat art D42/D43 tools/flat_art.py, HD terrain D57-D60 tools/terrain_hd.py, island rock D63/D66, HUD D61). ${A.context || ''}
${A.exclude ? 'EXCLUDED (another agent is on it): ' + A.exclude : ''}
The user's art rules: the original sprite is authoritative for outline, feature placement and major colours; bright sprite highlights are sheen, not bumps; remastered art must still read as the original. Never commit the original game data, extracted sprite PNGs or Gemini input sheets; derived art is fine with a CREDITS.md row.`

const GEMINI = A.gemini === false ? 'Do not use Gemini.' : `GEMINI may be used (https://gemini.google.com/images in Chrome via the Claude in Chrome tools, loaded with one ToolSearch call). ONE request at a time across all agents: take the lock with: set -o noclobber; echo "<you> $(date)" > ${LOCK} ; if that fails wait 60 s and retry; remove it as soon as that request's answer is downloaded. Own new tab, close it after. Tips in docs/terrain-pipeline.html section 3. If Gemini shows a usage or limit warning, stop using it and report.`

const CAP = { type: 'object', properties: { ok: { type: 'boolean' }, captures: { type: 'array', items: { type: 'string' } }, drawDumps: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' } }, required: ['ok', 'captures', 'drawDumps', 'notes'] }
const ISSUES = { type: 'object', properties: { issues: { type: 'array', items: { type: 'object', properties: {
  id: { type: 'string', description: 'short kebab-case slug' }, title: { type: 'string' }, what: { type: 'string' }, where: { type: 'string', description: 'ticks / conditions where it shows, and how prominent' },
  evidence: { type: 'array', items: { type: 'string' } }, cause: { type: 'string' }, approach: { type: 'string' }, needsGemini: { type: 'boolean' }, priority: { type: 'number', description: '1 = most visible' } },
  required: ['id', 'title', 'what', 'where', 'evidence', 'cause', 'approach', 'needsGemini', 'priority'] } }, notes: { type: 'string' } }, required: ['issues', 'notes'] }
const FIX = { type: 'object', properties: { ok: { type: 'boolean' }, pr: { type: 'string' }, branch: { type: 'string' }, before: { type: 'array', items: { type: 'string' } }, after: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' } }, required: ['ok', 'notes'] }
const REVIEW = { type: 'object', properties: { verdict: { type: 'string', enum: ['ship', 'fix'] }, issues: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' } }, required: ['verdict', 'issues', 'notes'] }

// 1. Captures and draw-list dumps: mechanical (a Haiku candidate once benched); retried on tiers.captureFallback if empty.
phase('Capture')
const ticks = []
for (let t = T0; t <= T1; t += STEP) ticks.push(t)
const capPrompt = `${ENV}

CAPTURES ONLY: no judging, no edits. In ${MAIN} (or a clean worktree of origin/main), start the dev server, then for each tick T in [${ticks.join(', ')}] capture ${PLAYURL('&skip=T&freezeAt=T&armor=99')} at 3840x2160 to ${SC}/audit/t<T>.png, with evalExpr dumping that tick's draw list as JSON to ${SC}/audit/t<T>-draws.json: for each draw its kind, pass, sheet id, sprite index, and how the renderer draws it (model / flat art / HD tile / structure model / extruded sprite or original tile); read src/debug/playHarness.ts and src/render/sprite2Route.ts for how to get that from tyrianHarness, and write the small helper script to ${SC}/audit/dump.js. Special moments too: explosions and hits; the boss taking damage and dying; pickups (coins and their value numbers, power-ups, armour crates); &armor=3 (the armour ship); sidekick shots (&left=/&right=); the ship's shield and hurt flashes; messages and HUD text; level start and end. ${A.moments || ''} A blank or black capture or a loading line means the wait was too short: redo it with 60000. Stop the server. Return ok, captures, drawDumps, notes (anything that failed).${REV()}`
let cap = await run('capture', 'capture', capPrompt, { label: 'capture', phase: 'Capture', schema: CAP })
if (!cap || !cap.ok || !cap.captures || !cap.captures.length) cap = await agent(capPrompt, { ...tier('captureFallback'), label: 'capture-retry', phase: 'Capture', schema: CAP })

// 2. Audit: judgement.
phase('Audit')
const audit = await run('audit', 'audit', `${ENV}

AUDIT: find everything in this level that still looks pixelated or low-res next to the remastered 3D look. Captures and draw-list dumps: ${JSON.stringify(cap || {}).slice(0, 3000)} (in ${SC}/audit/; take more with cdpshot if needed). List every draw that renders as a raw or upscaled original sprite (no model, no flat or HD art), every tile layer or texture without HD art, sprite-swap fallbacks (KNOWN_DAMAGE_SWAPS in tests/render/modelSwap.test.ts; MODEL_SWAP_REPORT=1 lists every sprite still drawn extruded), and fonts or number glyphs drawn from sprite sheets. Group the findings into concrete, fixable issues, at most ${MAXI}, most visible first; for each the cause (file, function, data), a recommended approach (3D model, flat art via tools/flat_art.py and Gemini, VFX/shader, HD vector text, ...) and whether it needs Gemini. Leave out what is fine as it is (deliberate original-style options) and say why. Do not edit the repo. Return issues and notes.${REV()}`, { label: 'audit', phase: 'Audit', schema: ISSUES }, true)
const all = ((audit && audit.issues) || []).sort((a, b) => a.priority - b.priority)
let issues = all.slice(0, MAXI)
if (BENCH) {
  if (BENCH.only) issues = issues.slice(0, BENCH.n)
  BENCH.keys = new Set(issues.slice(0, BENCH.n).map(i => i.id))
}
if (all.length > MAXI) log(`dropped ${all.length - MAXI} lower-priority issues: ${all.slice(MAXI).map(i => i.id).join(', ')}`)
log(`${issues.length} issues: ${issues.map(i => i.id + (i.needsGemini ? ' (gemini)' : '')).join(', ')}`)

const SHIP = A.prs === false
  ? 'Commit on your branch (messages end with the attribution lines the harness gives); do NOT push.'
  : 'Commit (messages end with the attribution lines the harness gives), push, and open a PR with gh. Do NOT merge: the coordinator merges after CI.'

// 3-4. Fix each issue in its own worktree, then strict review with one fix round.
phase('Fix')
const results = await pipeline(issues,
  async (it) => run('fix', it.id, `${ENV}
${GEMINI}

FIX one pixelation issue end to end.
Issue: ${JSON.stringify(it)}
- Work in your own new worktree: git -C ${MAIN} fetch -q origin && git -C ${MAIN} worktree add ${WTS}/${PFX}-${it.id} -b ${PFX}-${it.id} origin/main, then symlink data (-> ../../tyrian/data), node_modules (-> ../../tyrian/node_modules), reference (-> ../model-shape/reference) and .shape (-> ../model-shape/.shape) into it. Touch only what this issue needs; other agents fix other issues on their own branches. Never git add -A.
- Implement the best fix. Keep the game contract: palette materials and fades, every frame, pivots, no pop-in, existing options and fallbacks. New art goes behind the existing remastered/original switch where one applies.
- Verify in the game: before and after captures at the same ticks, including 3840x2160 close-ups, in ${SC}/${it.id}/. Tests and typecheck pass. Check fps/cpu in the overlay and the download size.
- Add a DECISIONS.md entry with the next free Dnn on origin/main (expect renumbering at merge).
- ${SHIP}
Return ok, pr, branch, before and after (paths), notes.${REV(it)}`, { label: `fix:${it.id}`, phase: 'Fix', schema: FIX }).then(f => ({ it, f })),
  async ({ it, f }) => {
    if (!f || !f.ok) return { id: it.id, fix: f }
    let fix = f, rev = null
    for (let r = 1; r <= 2; r++) {
      rev = await run('review', `${it.id}:${r}`, `${ENV}

STRICT REVIEW of the fix for "${it.title}" (${it.what}). Fixer report: ${JSON.stringify(fix).slice(0, 3000)}. Read branch ${fix.branch || PFX + '-' + it.id} in ${WTS}/${PFX}-${it.id} (don't edit). Run the game from that worktree, capture the same moments yourself and compare with main. Is the pixelation gone at the game camera and at 4K? Does it still read as the original? Any regressions (seams, pop-in, wrong frames, fades, performance, other levels using the same assets)? Do tests pass? verdict ship or fix, with concrete issues.${REV(it)}`, { label: `review:${it.id}:${r}`, phase: 'Review', schema: REVIEW }, true)
      if (!rev || rev.verdict === 'ship' || r === 2) break
      fix = await run('fixRound', `${it.id}:${r}`, `${ENV}
${GEMINI}

FIX ROUND for "${it.title}" in your worktree ${WTS}/${PFX}-${it.id} (branch ${fix.branch || PFX + '-' + it.id}${fix.pr ? ', PR ' + fix.pr : ''}). The reviewer found:\n${rev.issues.map(i => '- ' + i).join('\n')}\nNotes: ${rev.notes}\nFix exactly these, verify again with before/after captures, run tests and typecheck. ${SHIP} Return ok, pr, branch, before, after, notes.${REV(it)}`, { label: `fix2:${it.id}`, phase: 'Fix', schema: FIX })
    }
    return { id: it.id, title: it.title, fix, review: rev }
  })
return { capture: cap, audit, results: results.filter(Boolean), bench: benchReport() }
