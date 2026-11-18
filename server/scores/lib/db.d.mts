import type { DatabaseSync } from "node:sqlite";
export const SCHEMA_VERSION: number;
export function openDb(path: string): DatabaseSync;
export function transaction<T>(db: DatabaseSync, fn: () => T): T;
