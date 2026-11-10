// The debug console's view of an episode's levels (D109): the episode script's `]L[` commands
// (src/data/episodeScript.ts), numbered, and the sections to jump to.
//
// The harness's `main=` and the game's g.mainLevel are episode-script *sections*, not levels: a
// level is played by the `]L[` in its own section (episode 1's TYRIAN is section 3, after section 2's
// item screen), and its lvlFileNum (tyrian1.lvl's level 9) is a third numbering. The console numbers
// the levels 1..N in script order, one per section with an `]L[` (TYRIAN's normal and hard variants
// share section 3, so they are one entry), and jumps to that section, which plays the level at once.

import { atoi, episodeLevels, type EpisodeScript } from "../../data/episodeScript";

export interface ConsoleLevel {
  /** The console's level number: 1..N in script order. */
  number: number;
  /** The level's name (`]L[`'s levelName, trimmed); variants in one section are joined with " / ". */
  name: string;
  /** Every name the section's `]L[` lines give. */
  names: string[];
  /** The episode-script section (mainLevel, the harness's `main=`) whose `]L[` plays it. */
  section: number;
  /** tyrianN.lvl's level number(s) (lvlFileNum). */
  lvlFileNums: number[];
  /** A bonus level (`$` in the line). */
  bonus: boolean;
}

/** The episode's levels, one per section that plays one, in script order. */
export function listLevels(script: EpisodeScript): ConsoleLevel[] {
  const out: ConsoleLevel[] = [];
  for (const ref of episodeLevels(script)) {
    const name = ref.levelName.trim();
    const last = out.at(-1);
    if (last && last.section === ref.section) {
      if (!last.names.includes(name)) last.names.push(name);
      last.name = last.names.join(" / ");
      last.lvlFileNums.push(ref.lvlFileNum);
      last.bonus ||= ref.bonusLevelCurrent || ref.normalBonusLevelCurrent;
      continue;
    }
    out.push({ number: out.length + 1, name, names: [name], section: ref.section, lvlFileNums: [ref.lvlFileNum], bonus: ref.bonusLevelCurrent || ref.normalBonusLevelCurrent });
  }
  return out;
}

/** A level name for matching: upper case, letters and digits only ("Soh Jin" = "SOHJIN"). */
const key = (s: string) => s.toUpperCase().replace(/[^A-Z0-9]/g, "");

export type LevelTarget = { section: number; level: ConsoleLevel | null; note?: string } | { error: string };

/**
 * What `level` aims at: a level number (`3`), a section (`s12` or `#12`, any section of the
 * script, e.g. one with an item screen), or a name, whole or the start of one, any case, spaces
 * and punctuation ignored (`tyrian`, `soh jin`, `asteroid?`). A name two levels share picks the
 * first and says so.
 */
export function resolveLevel(script: EpisodeScript, levels: ConsoleLevel[], arg: string): LevelTarget {
  const text = arg.trim();
  if (!text) return { error: "which level? (a number, a name, or s<section>)" };
  const sec = /^(?:s|#|section)\s*(\d+)$/i.exec(text);
  if (sec) {
    const section = Number(sec[1]);
    if (section < 1 || section > script.sections.length) return { error: `no section ${section} (this episode has 1-${script.sections.length})` };
    return { section, level: levels.find((l) => l.section === section) ?? null };
  }
  if (/^\d+$/.test(text)) {
    const n = Number(text);
    const level = levels[n - 1];
    if (!level) return { error: `no level ${n} (this episode has 1-${levels.length}; \`levels\` lists them)` };
    return { section: level.section, level };
  }
  const k = key(text);
  if (!k) return { error: `no level called "${text}"` };
  const exact = levels.filter((l) => l.names.some((n) => key(n) === k));
  const found = exact.length ? exact : levels.filter((l) => l.names.some((n) => key(n).startsWith(k)));
  if (found.length === 0) return { error: `no level called "${text}" (\`levels\` lists them)` };
  if (found.length > 1 && !exact.length) return { error: `"${text}" could be ${found.map((l) => `${l.number} ${l.name}`).join(", ")}` };
  const level = found[0];
  const note = found.length > 1 ? `${found.length} levels are called ${level.names[0]}: took ${level.number}; the others are ${found.slice(1).map((l) => l.number).join(", ")}` : undefined;
  return { section: level.section, level, note };
}

/**
 * `]G[`'s destinations (JE_loadMap: mapPNum at s + 7, then section i at s + 4 + (i + 1) * 8), the
 * sections the item screen's map can go to.
 */
export function navTargets(line: string): number[] {
  if (!line.startsWith("]G[")) return [];
  const n = atoi(line.slice(7));
  const out: number[] = [];
  for (let i = 0; i < n; i++) out.push(atoi(line.slice(4 + (i + 1) * 8)));
  return out;
}

/**
 * The section whose item screen leads to the level in `levelSection`: one with an `]I[` whose map
 * (`]G[`) lists it. Null if no item screen leads there (a level reached only by a jump).
 */
export function shopSectionFor(script: EpisodeScript, levelSection: number): number | null {
  for (const sec of script.sections) {
    if (!sec.lines.some((l) => l.startsWith("]I["))) continue;
    if (sec.lines.some((l) => navTargets(l).includes(levelSection))) return sec.number;
  }
  return null;
}

/** Whether a section has an item screen of its own (`]I[`). */
export function hasItemScreen(script: EpisodeScript, section: number): boolean {
  return script.sections.find((s) => s.number === section)?.lines.some((l) => l.startsWith("]I[")) ?? false;
}
