export interface TokenPayload {
  v: 1;
  id: string;
  iat: number;
  ep: number;
  diff: number;
  mode: string;
}
export const TOKEN_MAX_AGE_MS: number;
export const REPORT_TOKEN_MAX_AGE_MS: number;
export function issueToken(secret: string, run: { ep: number; diff: number; mode: string }, now: number): { token: string; payload: TokenPayload };
export function verifyToken(
  secret: string,
  token: unknown,
  now: number,
  maxAgeMs?: number,
): { ok: true; payload: TokenPayload } | { ok: false; reason: "token" | "expired"; payload?: TokenPayload };
