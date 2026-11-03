export const meta = {
  name: 'music-arrange',
  description: 'Arrange (or rework) Tyrian songs as orchestral and synth versions in the tyrian3d-remaster repo: one agent per song, both styles, its own worktree and branch',
  whenToUse: 'Redoing songs after the user listened (all 41 exist since D40). See docs/agents/WORKFLOWS.md and docs/music-pipeline.html.',
  phases: [{ title: 'Arrange' }, { title: 'Bench' }],
}

// Generalised from tyrian-music-arrangements (all 41 songs: 41 agents, ~62 min at 16 concurrent).
// The arrangements live in the private remaster repo (tyrian3d-remaster, cloned next to tyrian3d);
// publishing the renders into tyrian3d's public/tyrian-remaster/ is a separate, manual step.
//
// args = {
//   songs: [{ song: 1, title: '<title from song-NN.json>', notes: 'what the user heard and wants changed' }],  // required
//   styles: ['orchestral', 'synth'],
//   repo: '/Users/dlomibao/projects/tyrian3d-remaster',
//   worktrees: '/Users/dlomibao/projects/tyrian3d-remaster-wt',   // song-NN worktrees (branch song/NN)
//   push: true,                        // push the song branch (never main)
//   concurrency: 16,
//   tiers: { arrange },                // default Opus (medium); cheaper only after a bench
//   bench: { stages: ['arrange'], model: 'sonnet', n: 1, only: true }, date: 'YYYY-MM-DD',
//   rev: 0
// }

const A = args || {}
if (!A.songs || !A.songs.length) return { error: 'args.songs is required' }
const REPO = A.repo || '/Users/dlomibao/projects/tyrian3d-remaster'
const WTS = A.worktrees || '/Users/dlomibao/projects/tyrian3d-remaster-wt'
const STYLES = A.styles || ['orchestral', 'synth']
const PUSH = A.push !== false

const TIER = { opus: { model: 'opus', effort: 'medium' }, sonnet: { model: 'sonnet', effort: 'medium' }, haiku: { model: 'haiku' } }
function asTier(t) {
  const o = typeof t === 'string' ? { ...(TIER[t] || { model: t }) } : { ...t }
  if (o.effort && !['low', 'medium', 'high'].includes(o.effort)) o.effort = 'high'
  return o
}
const tier = (stage) => asTier((A.tiers && A.tiers[stage]) || 'opus')
const BENCH = A.bench ? { model: 'sonnet', n: 1, only: true, stages: ['arrange'], ...A.bench } : null
const REV = (s) => {
  const r = (A.rev || 0) + ((s && s.rev) || 0)
  return r ? `\n[run revision ${r}]` : ''
}

const SCHEMA = {
  type: 'object',
  properties: {
    song: { type: 'number' },
    versions: { type: 'array', items: { type: 'object', properties: {
      style: { type: 'string' }, file: { type: 'string' }, report: { type: 'string' },
      arrangement: { type: 'string', description: 'which original line went to which instrument, what you added or changed, and why' },
      concerns: { type: 'string', description: 'what may sound off and should be listened to first' } },
      required: ['style', 'file', 'arrangement', 'concerns'] } },
    commits: { type: 'number' },
    pushed: { type: 'boolean' },
    problems: { type: 'string' },
  },
  required: ['song', 'versions', 'commits', 'pushed', 'problems'],
}
const BV = { type: 'object', properties: { verdict: { type: 'string', enum: ['cheap-ok', 'opus-needed'] }, metric: { type: 'string' }, rework: { type: 'string' }, notes: { type: 'string' } }, required: ['verdict', 'metric', 'rework', 'notes'] }

const brief = (s, wt, branch, push) => {
  const nn = String(s.song).padStart(2, '0')
  return `You are arranging music from Tyrian (1995, music by Alexander Brandon, with additional music by Andreas Molnar; "ZANAC3" and "ZANAC5" reproduce music from Compile's Zanac). Each version must be clearly the same composition (same melodies, harmony, rhythm, structure, tempo and length) and sound as good as you can make it. You can't listen to audio, so you work from the notes, the instrument ranges and the analysis reports, carefully.

Song ${s.song}: "${s.title}". Versions: ${STYLES.join(', ')}. ${STYLES.includes('orchestral') ? 'orchestral: a cinematic orchestra from the VSCO 2 CE sample instruments (strings, brass, woodwinds, harp, piano, timpani, orchestral percussion), plus VCSL one-shot percussion if it helps. ' : ''}${STYLES.includes('synth') ? 'synth: a modern electronic/synthwave production with tools/synth.py (supersaw leads and pads, analog-style basses with filter envelopes, arps, FM bells, synthesized drums); synths carry it.' : ''}
${s.notes ? 'THE USER LISTENED AND SAID: ' + s.notes + '\nThe existing scripts arrangements/<style>/song-' + nn + '.py are the starting point: fix what the user heard, keep what works.' : ''}

Where to work
- Your worktree of the private repo: ${wt} (branch ${branch}). If it doesn't exist: git -C ${REPO} worktree add ${wt} -b ${branch} main (or check out the existing branch), then symlink .venv, .tools and samples from ${REPO}. Work only there; don't touch other songs.
- Read: README.md, tools/remaster.py (the API, documented at the top), tools/synth.py (presets), tools/INSTRUMENTS.md (playable ranges, one-shot percussion folders). Python: .venv/bin/python.
- Scripts: arrangements/<style>/song-${nn}.py; running one renders out/<style>/song-${nn}.ogg with .report.png and .json. Use only this repo's files and tools; no downloads, no MCP tools.

Pitch bends (the user's correction): a long note that slides, scoops, wobbles or sweeps is ONE held note with its pitch movement in Note.bends. Never chop a bent note into short notes. Part.bends: "all" (synth default), "slides" (sample default), "none". A drum is usually one note with a big falling bend.

Understanding the original: load_source(${s.song}).describe() (channels, ranges, patches, echoes, tempo grid); src.channel(n) gives notes. Split a channel by patch where it changes role. Echo channels (src.echoes()) become delay/reverb, not a second instrument. Fast arpeggios can become sustained chords or harp/piano figures (orchestral) or stay arps (synth). Sample instruments are silent outside their range: Part.extend, split_by_range(); fix every warning render_song prints. source/original/song-${nn}.ogg is the original; the report compares spectrogram and loudness.

Quality bar: every note of the composition still there; melody on top and clear, bass solid; added layers only to support; the report's spectrogram and loudness follow the original's shape, no clipping; iterate (render, read the report, adjust) up to about 4 times per version. render_song handles loops, mixing and mastering; don't change tools/.

Commit after each version renders well: git add arrangements/<style>/song-${nn}.py out/<style>/song-${nn}.ogg out/<style>/song-${nn}.report.png out/<style>/song-${nn}.json && git commit, message "Song ${s.song} <style>: ${s.title}" plus the attribution lines the harness gives. ${push ? 'Then git push -q -u origin ' + branch + '. Never push to main or force-push.' : 'Do NOT push.'}
Return each version with its file, report, a short description of the arrangement, and what should be listened to first.${REV(s)}`
}

const nn = (s) => String(s.song).padStart(2, '0')
let songs = A.songs
if (BENCH && BENCH.only) songs = songs.slice(0, BENCH.n)
const benchSet = new Set(BENCH ? songs.slice(0, BENCH.n).map(s => s.song) : [])
const benchRows = []

async function arrange(s) {
  const real = () => agent(brief(s, `${WTS}/song-${nn(s)}`, `song/${nn(s)}`, PUSH), { ...(benchSet.has(s.song) ? TIER.opus : tier('arrange')), label: `song ${s.song} ${s.title}`, phase: 'Arrange', schema: SCHEMA })
  if (!benchSet.has(s.song)) return real()
  const cm = asTier(BENCH.model)
  const [cheap, canon] = await parallel([
    () => agent(brief(s, `${WTS}/song-${nn(s)}-bench-${cm.model}`, `song/${nn(s)}-bench-${cm.model}`, false), { ...cm, label: `song ${s.song}:bench-${cm.model}`, phase: 'Arrange', schema: SCHEMA }),
    real,
  ])
  const v = await agent(`BENCH JUDGE (don't edit files). Song ${s.song} "${s.title}" was arranged twice from the same brief: by ${cm.model} (worktree ${WTS}/song-${nn(s)}-bench-${cm.model}) and by Opus (worktree ${WTS}/song-${nn(s)}). ${cm.model}: ${JSON.stringify(cheap).slice(0, 2500)} Opus: ${JSON.stringify(canon).slice(0, 2500)}
Compare them yourself: read both scripts and both report PNGs (spectrogram and loudness vs the original), check every original line is present and bent notes are held (not chopped), render warnings, clipping, balance. You can't hear: judge structure and fidelity only, and say what the user should listen to. Would the ${cm.model} versions need significant rework to reach the Opus versions? verdict cheap-ok or opus-needed; metric; rework.`, { ...TIER.opus, label: `bench-judge:song ${s.song}`, phase: 'Bench', schema: BV })
  benchRows.push({ step: 'arrange', models: `${cm.model} vs opus`, sample: `song ${s.song}`, metric: v ? v.metric : 'judge failed', verdict: v ? v.verdict : 'none', rework: v ? v.rework : '', date: A.date || 'TODO', note: 'confirm by listening before trusting it' })
  return canon
}

// A worker pool, so args.concurrency can sit below the workflow's cap of 16.
const queue = [...songs]
const results = []
async function worker() {
  while (queue.length) {
    const s = queue.shift()
    const r = await arrange(s)
    results.push(r || { song: s.song, versions: [], commits: 0, pushed: false, problems: 'agent failed' })
    log(`song ${s.song}: ${r ? r.versions.length + ' versions' : 'failed'} (${results.length}/${songs.length})`)
  }
}
await Promise.all(Array.from({ length: Math.min(A.concurrency || 16, songs.length) }, worker))
if (BENCH) log(`bench: ${benchRows.map(r => `${r.sample}: ${r.verdict}`).join('; ')}`)
return { results, bench: BENCH ? benchRows : null }
