// Locates the Tyrian 2.1 data for parser tests. The data isn't committed (see issue #10),
// so suites use describe.skipIf(!hasData(...)) and skip cleanly when it's absent.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

export const DATA_DIR = process.env.TYRIAN_DATA ?? "data";

export function dataPath(name: string): string {
  return join(DATA_DIR, name);
}

export function hasData(...names: string[]): boolean {
  return names.every((n) => existsSync(dataPath(n)));
}

export function readData(name: string): Uint8Array {
  return new Uint8Array(readFileSync(dataPath(name)));
}
