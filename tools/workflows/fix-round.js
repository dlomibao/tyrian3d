export const meta = {
  name: 'fix-round',
  description: 'Extra fix rounds for models (or other assets) that failed strict review: fix from concrete issues, strict re-review, escalate the last fix to Opus',
  whenToUse: 'After model-flagship (or any review loop) leaves items at verdict fix. See docs/agents/WORKFLOWS.md.',
  phases: [{ title: 'Fix' }, { title: 'Review' }, { title: 'Bench' }],
}

// Generalised from enemies-fix-round (4 level-1 models that failed strict review: 12 agents, ~44 min).
//
// args = {
//   worktree, scratch,                       // required
//   items: [{ name, script, issues?: [..], issuesFile?: 'path', notes?: '', kind?: 'enemy', rev? }],
//   rounds: 2,                               // re-reviews per item
//   context: 'extra brief',
//   rules: 'override the acceptance rules (default: the sprite rules for models)',
//   tiers: { fix, fixEscalate, review },     // all default to Opus (medium); cheaper only after a bench
//   bench: { stages: ['fix', 'review'], model: 'sonnet', n: 2, only: true }, date: 'YYYY-MM-DD',
//   python, blender, data, rev
// }

const A = args || {}
if (!A.worktree || !A.scratch || !A.items) return { error: 'args.worktree, args.scratch and args.items are required' }
const WT = A.worktree
const SP = A.scratch
const PY = A.python || '/Users/dlomibao/projects/tyrian3d-remaster/.venv/bin/python'
const BL = A.blender || '/Applications/Blender.app/Contents/MacOS/Blender'
const DATA = A.data || '/Users/dlomibao/projects/tyrian/data'
const ROUNDS = A.rounds || 2

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

const RULES = A.rules || `Rules: the ORIGINAL SPRITE is authoritative for the top-down silhouette (top-view IoU vs the sprite mask >= 0.95 at sprite resolution on EVERY frame), feature positions and major colours (the sprite's palette index per region; bright spots are sheen, not bumps). Undersides only need a plausible closed shape. Keep the game contract: palette materials (pal_<index>), same export path / model path / spriteModels or tileModels JSON, every frame, assembly pieces/regions/pivots. No concept projection bake.`

const CTX = (it) => `Tyrian 3D (browser 3D remake of OpenTyrian). Worktree ${WT} (data/, reference/, .shape are git-ignored links). Python with PIL: ${PY}; Blender: ${BL}. Node commands need NODE_OPTIONS=; tests TYRIAN_DATA=${DATA} NODE_OPTIONS= npx vitest run --no-fsModuleCache. ${A.context || ''}
Item "${it.name}", script ${it.script || '(find it: grep assets/blender for the name)'}; reference sprite/frames in reference/models/${it.name}/; earlier work in ${SP}/${it.name}/. It FAILED review. The issues: ${it.issues ? '\n' + it.issues.map(i => '- ' + i).join('\n') : ''}${it.issuesFile ? '\nRead the reviewer issues and notes for ' + it.name + ' in ' + it.issuesFile + '.' : ''}${it.notes ? '\nNotes: ' + it.notes : ''}
${RULES}
Other agents edit other items in this worktree at the same time: touch only ${it.name}'s files and ${SP}/${it.name}/; never edit shared files (common.py, usp_talon.py, lib_*.py, tools/, src/); run no state-changing git commands.`

const ROUT = { type: 'object', properties: { verdict: { type: 'string', enum: ['ship', 'fix'] }, score: { type: 'number' }, iou: { type: 'number' }, issues: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' } }, required: ['verdict', 'score', 'issues', 'notes'] }
const FOUT = { type: 'object', properties: { ok: { type: 'boolean' }, iou: { type: 'number' }, cmp: { type: 'string' }, files: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' } }, required: ['ok', 'notes'] }

const FIXSTEPS = (it) => `Improve the current script, don't restart. If two rules conflict (a design change vs the IoU threshold), find the design that satisfies both. Rebuild with tools/build-models.sh -j 2 ${it.script || '<script>'}, read the log, measure IoU per frame, feature overlay and region colours, render game camera / side / front / 3/4 beside the sprite, write ${SP}/${it.name}/final/cmp.png. Don't commit. Return ok, iou (worst frame), cmp, files, notes.`

let ITEMS = A.items
if (BENCH) {
  if (BENCH.only) ITEMS = ITEMS.slice(0, BENCH.n)
  BENCH.keys = new Set(ITEMS.slice(0, BENCH.n).map(i => i.name))
}
const res = await pipeline(ITEMS,
  async (it) => {
    let fin = await run('fix', it.name, `${CTX(it)}\n\nFIX: resolve every issue above. ${FIXSTEPS(it)}${REV(it)}`, { label: `fix:${it.name}`, phase: 'Fix', schema: FOUT })
    let rev = null
    for (let round = 1; round <= ROUNDS; round++) {
      rev = await run('review', `${it.name}:${round}`, `${CTX(it)}\n\nSTRICT RE-REVIEW (don't edit files). Fixer report: ${JSON.stringify(fin).slice(0, 2500)}. Measure the rules yourself (IoU per frame, features, colours), render your own views (game camera beside the sprite, side, front, 3/4; underside only checked for being closed). Were the earlier issues resolved? Did anything regress (a lost feature counts as a regression whatever else improved)? Would a player say it IS the original in 3D? verdict ship or fix, concrete issues, score 1-10.${REV(it)}`, { label: `review:${it.name}:${round}`, phase: 'Review', schema: ROUT }, true)
      if (!rev || rev.verdict === 'ship' || round === ROUNDS) break
      // The last fix of the loop uses tiers.fixEscalate (Opus by default): a cheaper fixer has had a go.
      const stage = round === ROUNDS - 1 ? 'fixEscalate' : 'fix'
      fin = await run(stage, `${it.name}:${round + 1}`, `${CTX(it)}\n\nFIX AGAIN: the re-review found:\n${rev.issues.map(i => '- ' + i).join('\n')}\nNotes: ${rev.notes}\n${FIXSTEPS(it)}${REV(it)}`, { label: `fix:${it.name}:${round + 1}`, phase: 'Fix', schema: FOUT })
    }
    return { name: it.name, final: fin, review: rev }
  })
const done = res.filter(Boolean)
const left = done.filter(r => !r.review || r.review.verdict !== 'ship').map(r => r.name)
if (left.length) log(`still failing, for the coordinator/user: ${left.join(', ')}`)
return { results: done, stillFailing: left, bench: benchReport() }
