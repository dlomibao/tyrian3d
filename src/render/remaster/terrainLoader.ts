// Fetches HD terrain art (terrainArt.ts, DECISIONS.md D57): a tileset's manifest when one of its
// levels starts (or its first tile is drawn), then the atlases that level's map can draw from (all
// of them without a map); any other atlas when a tile first asks for it (D234). Missing or bad
// files only mean the tiles draw as before; nothing here throws.

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
 * Load `public/<dir><tileset>/manifest.json` and its atlases: `images(tileset)`'s, or every one.
 * Resolves (never rejects) once the manifest and those atlases have loaded or failed: to the
 * tileset, or null without usable art. The tileset loads any other atlas when asked for it
 * (TerrainTileset.loadImage), each once.
 */
export async function loadTerrainTileset(
  name: string,
  base: string = import.meta.env.BASE_URL,
  io: TerrainLoadIo = browserIo(),
  dir: string = artDir(),
  images?: (tileset: TerrainTileset<THREE.Texture>) => Iterable<string>,
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
  // That includes the images layer-0 rects name for themselves (a merged tileset's new tiles, D83).
  for (const [layer, art] of manifest.layers) {
    if (layer !== (0 as TerrainLayer)) continue;
    opaque.add(art.image);
    for (const r of art.tiles.values()) if (r.image) opaque.add(r.image);
    for (const list of art.variants.values()) for (const r of list) if (r.image) opaque.add(r.image);
    for (const f of art.fields.values()) for (const r of f.rects) if (r.image) opaque.add(r.image);
    for (const r of art.covered.values()) if (r.image) opaque.add(r.image); // covered paintings (D86)
  }
  const loads = new Map<string, Promise<void>>();
  tileset.loadImage = (image) => {
    let p = loads.get(image);
    if (!p) {
      p = !tileset.images.has(image)
        ? Promise.resolve()
        : io.loadTexture(root + image.split("/").map(encodeURIComponent).join("/")).then(
            ({ texture, width, height }) => {
              prepareTerrainTexture(texture, !opaque.has(image));
              tileset.setImage(image, { texture, width, height });
            },
            (err) => console.warn(`terrain art ${name}/${image} didn't load; its tiles draw as before`, err),
          );
      loads.set(image, p);
    }
    return p;
  };
  await tileset.loadImages(images ? images(tileset) : tileset.images.keys());
  return tileset;
}

/** The per-layer tile maps of a level (levelTileMaps), for choosing the atlases to load. */
export type TerrainMaps = readonly (ArrayLike<number> | undefined)[];

type TilesetLoad = (name: string, images?: (tileset: TerrainTileset<THREE.Texture>) => Iterable<string>) => Promise<TerrainTileset<THREE.Texture> | null>;

/** Every tileset's HD art, loaded on first request. */
export class TerrainArtSet {
  private readonly loads = new Map<string, Promise<TerrainTileset<THREE.Texture> | null>>();
  private readonly ready = new Map<string, TerrainTileset<THREE.Texture> | null>();

  constructor(private readonly load: TilesetLoad = (n, images) => loadTerrainTileset(n, undefined, undefined, undefined, images)) {}

  /**
   * Start loading `tileset`'s art if not yet asked for: with `maps` (the level's), only the atlases
   * those maps can draw from, else every atlas (D234). Settles when the manifest and those atlases
   * have loaded or failed; a later request with other maps loads what they add.
   */
  request(tileset: string, maps?: TerrainMaps): Promise<TerrainTileset<THREE.Texture> | null> {
    const wanted = maps && ((t: TerrainTileset<THREE.Texture>) => t.imagesFor(maps));
    let p = this.loads.get(tileset);
    if (!p) {
      p = this.load(tileset, wanted)
        .catch(() => null)
        .then((t) => {
          this.ready.set(tileset, t);
          return t;
        });
      this.loads.set(tileset, p);
      return p;
    }
    return wanted ? p.then(async (t) => (t && (await t.loadImages(wanted(t))), t)) : p;
  }

  /** The tileset's art if it has finished loading (null: none; undefined: not loaded yet). */
  get(tileset: string): TerrainTileset<THREE.Texture> | null | undefined {
    return this.ready.get(tileset);
  }
}
