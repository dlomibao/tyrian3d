import type { RunData } from "./runHash.mjs";
export const MODES: string[];
export const MAX_SCORE: number;
export const MAX_TICKS: number;
export const NAME_MAX: number;
export function nameCharAccepted(ch: string): boolean;
export function sanitizeName(raw: unknown): string;
export function isUuidV4(s: unknown): boolean;
export function isPrintable(s: unknown, max: number): boolean;
export type Invalid = { ok: false; reason: "invalid" | "mode"; error: string };
export function validateRunRequest(
  body: unknown,
): { ok: true; value: { episode: number; difficulty: number; mode: string; build: string; playerId: string | null } } | Invalid;
export function validateScore(body: unknown, tickHz: number): { ok: true; run: RunData; name: string; hash: string } | Invalid;
