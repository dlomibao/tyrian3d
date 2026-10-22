// levels1.dat..levels4.dat: the episode script JE_loadMap (OpenTyrian src/tyrian2.c) steps
// through between levels. It's a sequence of encrypted strings. A line starting with '*'
// opens a numbered section (mainLevel); lines starting with ']' are commands such as
// `]L[` (play a level), `]J` (jump to a section), `]I[` (shop), `]W` (show text).
//
// JE_loadMap seeks to section N by skipping N '*' lines, then executes lines until a
// `]L[` or a jump. Execution falls through section headers, so a section is an entry
// point rather than a closed block. Only `]L[` is decoded here; the rest stay raw lines.

import { readEncryptedString } from "./crypt";
import { BinaryReader, type Bytes } from "./reader";

export interface EpisodeSection {
  /** Section number, as mainLevel (1-based). */
  number: number;
  /** The '*' header line. */
  header: string;
  /** Index in `lines` of the first line after the header, where JE_loadMap starts reading. */
  start: number;
  /** Lines up to the next header (execution may continue past them). */
  lines: string[];
}

export interface EpisodeScript {
  /** Every decrypted line, in file order. */
  lines: string[];
  sections: EpisodeSection[];
}

/** A `]L[` (play level) command, decoded with the same fixed columns as JE_loadMap. */
export interface PlayLevel {
  /** nextLevel = atoi(s + 9): section to continue at; 0 means mainLevel + 1. */
  nextLevel: number;
  /** levelName: up to 9 chars from s + 13. */
  levelName: string;
  /** levelSong = atoi(s + 22): 1-based music track. */
  levelSong: number;
  /** lvlFileNum = atoi(s + 25): 1-based level in tyrianN.lvl, at lvlPos[(lvlFileNum - 1) * 2]. */
  lvlFileNum: number;
  /** bonusLevelCurrent: s[28] == '$'. */
  bonusLevelCurrent: boolean;
  /** normalBonusLevelCurrent: s[27] == '$'. */
  normalBonusLevelCurrent: boolean;
}

/** An `]L[` command with where it appears. */
export interface EpisodeLevelRef extends PlayLevel {
  /** Section the command is in. */
  section: number;
  /** Index in EpisodeScript.lines. */
  line: number;
}

/** Decrypt every line of a levelsN.dat file. */
export function parseEpisodeScript(data: Bytes): EpisodeScript {
  const r = new BinaryReader(data);
  const lines: string[] = [];
  while (r.remaining > 0) lines.push(readEncryptedString(r));

  const sections: EpisodeSection[] = [];
  lines.forEach((line, i) => {
    if (line.startsWith("*")) {
      sections.push({ number: sections.length + 1, header: line, start: i + 1, lines: [] });
    } else {
      sections.at(-1)?.lines.push(line);
    }
  });
  return { lines, sections };
}

/** C atoi: skip leading whitespace, optional sign, then digits; 0 if there are none. */
export function atoi(s: string): number {
  const m = /^\s*([+-]?\d+)/.exec(s);
  return m ? parseInt(m[1], 10) : 0;
}

/** Decode a `]L[` line, or return null for any other line. */
export function parsePlayLevel(s: string): PlayLevel | null {
  if (s[0] !== "]" || s[1] !== "L") return null;
  return {
    nextLevel: atoi(s.slice(9)),
    levelName: s.slice(13, 22),
    levelSong: atoi(s.slice(22)),
    lvlFileNum: atoi(s.slice(25)),
    bonusLevelCurrent: s.length > 28 && s[28] === "$",
    normalBonusLevelCurrent: s.length > 27 && s[27] === "$",
  };
}

/** Every `]L[` command in the script, with its section. */
export function episodeLevels(script: EpisodeScript): EpisodeLevelRef[] {
  const refs: EpisodeLevelRef[] = [];
  for (const section of script.sections) {
    section.lines.forEach((line, i) => {
      const level = parsePlayLevel(line);
      if (level) refs.push({ ...level, section: section.number, line: section.start + i });
    });
  }
  return refs;
}
