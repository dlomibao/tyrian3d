import type { Server } from "node:http";
import type { DatabaseSync } from "node:sqlite";
import type { ScoresConfig } from "./lib/config.mjs";

export const REPORTS_PER_RUN: number;
export const TOP_N: number;
export const SUMMARY_TTL_MS: number;
export interface ServerOptions extends ScoresConfig {
  /** Clock (ms since the epoch); Date.now by default. */
  now?: () => number;
  /** Parsed maxScores.json instead of reading maxScoresPath. */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  maxScores?: any;
  /** Per-hour limit overrides. */
  limits?: Partial<Record<"runs" | "scores" | "reports" | "get", number>>;
  summaryTtlMs?: number;
}
export interface ScoresApp {
  server: Server;
  db: DatabaseSync;
  listen(port?: number, host?: string): Promise<number>;
  close(): Promise<void>;
}
export function createServer(config: ServerOptions): ScoresApp;
export function start(env?: Record<string, string | undefined>): Promise<ScoresApp>;
