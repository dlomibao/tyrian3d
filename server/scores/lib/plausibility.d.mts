export const DIFFICULTIES: number[];
export const MARGINS: { floor: number; wallFactor: number; wallSlackS: number; rate: number };
export function difficultyForScore(score: number, initialDifficulty: number): number;
export function randomSpawnBound(n: number, p: number): number;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function levelCap(level: any, d: number, ticks: number): number;
export interface CheckedRun {
  episode: number;
  difficulty: number;
  ended: string;
  levels: { lvl: number; ticks: number; score: number; done: boolean }[];
  score: number;
}
export type CheckResult = { ok: true; cap: number } | { ok: false; reason: string; detail: string };
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function checkRun(data: any, run: CheckedRun, elapsedMs: number): CheckResult;
