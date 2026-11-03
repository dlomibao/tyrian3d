// Fetches HD terrain art (terrainArt.ts, DECISIONS.md D57): a tileset's manifest when one of its
// levels starts (or its first tile is drawn), then its atlases. Missing or bad files only mean the
// tiles draw as before; nothing here throws.

import * as THREE from "three";
import { TERRAIN_ART_DIR, TerrainTileset, parseTerrainManifest, type TerrainLayer } from "./terrainArt";
import { prepareTerrainTexture } from "./terrainMaterial";

/** How the loader gets its inputs, so tests can run it without a network or WebGL. */
export interface TerrainLoadIo {
  fetchJson(url: string): Promise<unknown | undefined>;
  loadTexture(url: string): Promise<{ texture: THREE.Texture; width: number; height: number }>;
}

const browserIo = (): TerrainLoadIo => ({
  // A dev server answers a missing file with index.html: json() then throws, which is "no art".
  fetchJson: (url) => fetch(url).then((r) => (r.ok ? r.json() : undefined)),
  loadTexture: async (url) => {
    const texture = await new THREE.TextureLoader().loadAsync(url);
    const image = texture.image as { width: number; height: number };
    return { texture, width: image.width, height: image.height };
  },
});

/** `?terrainart=<dir>` (relative to the site root, ending in "/"): another art folder, for testing. */
function artDir(search: string | undefined = typeof location === "undefined" ? undefined : location.search): string {
  const v = search === undefined ? null : new URLSearchParams(search).get("terrainart");
  return v && /^[\w\-./]+\/$/.test(v) && !v.includes("..") ? v : TERRAIN_ART_DIR;
}

/**
 * Load `public/<dir><tileset>/manifest.json` and its atlases. Resolves (never rejects) once the
 * manifest and every atlas have loaded or failed: to the tileset, or null without usable art.
 */
export async function loadTerrainTileset(
  name: string,
  base: string = import.meta.env.BASE_URL,
  io: TerrainLoadIo = browserIo(),
  dir: string = artDir(),
): Promise<TerrainTileset<THREE.Texture> | null> {
  const root = `${base}${dir}${encodeURIComponent(name)}/`;
  let json: unknown;
  try {
    json = await io.fetchJson(`${root}manifest.json`);
  } catch {
    return null; // No art for this tileset (or a broken file): its tiles draw as before.
  }
  const manifest = json === undefined ? null : parseTerrainManifest(json);
  if (!manifest || manifest.layers.size === 0) return null;
  const tileset = new TerrainTileset<THREE.Texture>(name, manifest);
  // Layer 0 is opaque; the others' soft edges filter without fringes premultiplied.
  const opaque = new Set<string>();
  // That includes the images layer-0 rects name for themselves (a merged tileset's new tiles, D75).
  for (const [layer, art] of manifest.layers) {
    if (layer !== (0 as TerrainLayer)) continue;
    opaque.add(art.image);
    for (const r of art.tiles.values()) if (r.image) opaque.add(r.image);
    for (const list of art.variants.values()) for (const r of list) if (r.image) opaque.add(r.image);
  }
  await Promise.all(
    [...tileset.images.keys()].map((image) =>
      io.loadTexture(root + image.split("/").map(encodeURIComponent).join("/")).then(
        ({ texture, width, height }) => {
          prepareTerrainTexture(texture, !opaque.has(image));
          tileset.setImage(image, { texture, width, height });
        },
        (err) => console.warn(`terrain art ${name}/${image} didn't load; its tiles draw as before`, err),
      ),
    ),
  );
  return tileset;
}

/** Every tileset's HD art, loaded on first request. */
export class TerrainArtSet {
  private readonly loads = new Map<string, Promise<TerrainTileset<THREE.Texture> | null>>();
  private readonly ready = new Map<string, TerrainTileset<THREE.Texture> | null>();

  constructor(private readonly load: (name: string) => Promise<TerrainTileset<THREE.Texture> | null> = (n) => loadTerrainTileset(n)) {}

  /** Start loading `tileset`'s art if not yet asked for; settles when it has loaded or failed. */
  request(tileset: string): Promise<TerrainTileset<THREE.Texture> | null> {
    let p = this.loads.get(tileset);
    if (!p) {
      p = this.load(tileset)
        .catch(() => null)
        .then((t) => {
          this.ready.set(tileset, t);
          return t;
        });
      this.loads.set(tileset, p);
    }
    return p;
  }

  /** The tileset's art if it has finished loading (null: none; undefined: not loaded yet). */
  get(tileset: string): TerrainTileset<THREE.Texture> | null | undefined {
    return this.ready.get(tileset);
  }
}
