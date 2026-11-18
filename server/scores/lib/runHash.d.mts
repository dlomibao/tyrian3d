export interface RunItem {
  id: number;
  power: number;
}
export interface RunLevel {
  /** lvlFileNum: the level's id in its episode. */
  lvl: number;
  /** Sim ticks the level ran. */
  ticks: number;
  /** JE_totalScore when the level ended (cumulative). */
  score: number;
  /** Finished (true), or the level the run was quit in (false, last only). */
  done: boolean;
}
export interface RunData {
  token: string;
  episode: number;
  difficulty: number;
  mode: string;
  tickHz: number;
  ended: "quit" | "episode";
  ship: number;
  front: RunItem;
  rear: RunItem;
  shield: number;
  generator: number;
  sidekicks: number[];
  levels: RunLevel[];
  score: number;
}
export function canonicalRun(run: RunData): string;
export function runHash(run: RunData): Promise<string>;
