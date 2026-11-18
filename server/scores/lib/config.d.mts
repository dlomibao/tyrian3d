export interface ScoresConfig {
  port: number;
  host: string;
  dbPath: string;
  hmacSecret: string;
  ipSalt: string;
  maxScoresPath: string;
  trustProxy: string[];
  corsOrigin: string | null;
}
export const DEFAULT_LIMITS: { runs: number; scores: number; reports: number; get: number };
export function loadConfig(env?: Record<string, string | undefined>): ScoresConfig;
export function parseTrustProxy(value: string | undefined): string[];
