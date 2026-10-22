// Where the Tyrian data comes from in the browser (DECISIONS.md D3).

import type { TyrianFiles } from "../sim/resources";

export class FileMap implements TyrianFiles {
  constructor(private readonly files: Map<string, Uint8Array>) {}

  get(name: string): Uint8Array | undefined {
    return this.files.get(name.toLowerCase());
  }

  get size(): number {
    return this.files.size;
  }
}

/** Game files worth loading (skips the DOS executables and docs). */
export const isGameFile = (name: string): boolean => !/\.(exe|doc|ovl|diz|com|bat|txt|ini|int|box|tfp|ico)$/i.test(name);

/** Dev server: load every file from /tyrian-data/ (served from the local data/ folder). */
export async function loadDevFiles(): Promise<FileMap | null> {
  if (!import.meta.env.DEV) return null;
  const list = await fetch("tyrian-data/index.json").then((r) => (r.ok ? (r.json() as Promise<string[]>) : null)).catch(() => null);
  if (!list?.length) return null;
  const names = list.filter(isGameFile);
  const entries = await Promise.all(
    names.map(async (name) => [name.toLowerCase(), new Uint8Array(await (await fetch(`tyrian-data/${encodeURIComponent(name)}`)).arrayBuffer())] as const),
  );
  return new FileMap(new Map(entries));
}
