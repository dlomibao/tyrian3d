import type { DatabaseSync } from "node:sqlite";
export const UNKNOWN_COUNTRY: string;
export function ipToBytes(ip: string): Buffer | null;
export function isMappedV4(bytes: Uint8Array): boolean;
export function lookupCountry(db: DatabaseSync, ip: string): string;
export function parseGeoLine(line: string): { start: Buffer; end: Buffer; country: string } | null;
export function loadGeo(db: DatabaseSync, lines: Iterable<string>, chunk?: number): { rows: number; skipped: number };
