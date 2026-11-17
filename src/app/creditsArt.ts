// Remastered end-credits art (DECISIONS.md D218): painted high-resolution versions of the nine
// pictures JE_playCredits fades in beside the rolling text (estsc.shp), and of the ship weaving up
// the side, made by tools/credits_art.py from Gemini's paintings.
//
// public/art/credits/manifest.json lists one WebP per picture, by its index in estsc.shp:
//
//   { "scale": 5, "pictures": { "0": { "image": "picture-0.webp", "w": 700, "h": 800 } } }
//
// a picture `scale` texels per original pixel, grey as the C draws it (blit_sprite_hv, hue 0), its
// alpha the original's silhouette. The ship: a frame is drawn painted when D210's shop icons
// (`tyrian.shp#8:<sprite>`, the level frame) or public/art/credits/ships/ (the same format, the
// four banking frames) have it; a ship whose five frames aren't all painted draws as the original,
// so it never changes look as it banks. Anything missing, not loaded yet or failed draws the
// original pixels, and so does the original look (`?sprites=original`, else `?vfx=original`: D42's
// switch, as the shop icons follow it).

import { loadShopIcons, parseShopIconManifest, shopIconMode, shopIconUrl, type ShopIconManifest } from "./shopIcons";

/** The C's ship sheet (tyrian.shp table 8, spriteSheet9), as the shop icons key it. */
export const SHIP_SHEET = "tyrian.shp#8";

/** The frames a credits ship shows round its level frame (episodeEnd.ts: |shipxc| > 10, > 20). */
export const SHIP_BANKS = [-4, -2, 0, 2, 4] as const;

export interface CreditsPicture {
  image: string;
  w: number;
  h: number;
}

export interface CreditsArtManifest {
  scale: number;
  pictures: Map<number, CreditsPicture>;
}

const isCount = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v) && v >= 0;

/** Check and index a manifest; null if it isn't one. Malformed pictures are dropped with a warning. */
export function parseCreditsArtManifest(json: unknown, warn: (msg: string) => void = console.warn): CreditsArtManifest | null {
  if (typeof json !== "object" || json === null) return null;
  const { scale, pictures } = json as { scale?: unknown; pictures?: unknown };
  if (!isCount(scale) || scale <= 0 || typeof pictures !== "object" || pictures === null) return null;
  const out: CreditsArtManifest = { scale, pictures: new Map() };
  for (const [key, p] of Object.entries(pictures as Record<string, unknown>)) {
    const { image, w, h } = (p ?? {}) as Record<string, unknown>;
    if (!/^\d+$/.test(key) || typeof image !== "string" || image === "" || !isCount(w) || !isCount(h) || w === 0 || h === 0) {
      warn(`credits art: picture ${key} is malformed; it draws as the original`);
      continue;
    }
    out.pictures.set(Number(key), { image, w, h });
  }
  return out;
}

const fileUrl = (base: string, dir: string, image: string): string =>
  `${base}${dir}${image.split("/").map(encodeURIComponent).join("/")}`;

async function fetchJson(url: string): Promise<unknown> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: ${res.status}`);
  return res.json();
}

async function decoded(url: string): Promise<HTMLImageElement> {
  const img = new Image();
  img.decoding = "async";
  img.src = url;
  await img.decode();
  return img;
}

/** The credits' painted art, once loaded: each picture as it decodes, and the ship's frames. */
export class CreditsArt {
  private readonly ready = new Map<number, HTMLImageElement>();
  private readonly frameUrls = new Map<number, string>();

  constructor(
    /** Each picture's image, resolved when it has decoded (null if it failed). */
    readonly pictures: Map<number, Promise<HTMLImageElement | null>>,
    private readonly ships: { manifest: ShopIconManifest; atlas: HTMLImageElement } | null,
  ) {
    for (const [n, p] of pictures) void p.then((img) => img && this.ready.set(n, img));
  }

  /** Picture `n`'s painting if it has decoded, else undefined (draw the original). */
  picture(n: number): HTMLImageElement | undefined {
    return this.ready.get(n);
  }

  /** Ship frame `sprite` (tyrian.shp#8) as an image URL: D210's shop icon, else a banking frame. */
  shipFrame(sprite: number): string | undefined {
    const shop = shopIconUrl(SHIP_SHEET, sprite);
    if (shop) return shop;
    const hit = this.frameUrls.get(sprite);
    if (hit !== undefined) return hit || undefined;
    let url = "";
    const f = this.ships?.manifest.icons.get(`${SHIP_SHEET}:${sprite}`);
    const atlas = this.ships?.atlas;
    if (f && atlas && f.x + f.w <= atlas.naturalWidth && f.y + f.h <= atlas.naturalHeight) {
      const canvas = document.createElement("canvas");
      canvas.width = f.w;
      canvas.height = f.h;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.drawImage(atlas, f.x, f.y, f.w, f.h, 0, 0, f.w, f.h);
        url = canvas.toDataURL();
      }
    }
    this.frameUrls.set(sprite, url);
    return url || undefined;
  }

  /** Whether the ship whose level frame is `shipGraphic` has every frame it can show painted. */
  shipPainted(shipGraphic: number): boolean {
    return SHIP_BANKS.every((d) => this.shipFrame(shipGraphic + d) !== undefined);
  }
}

/**
 * Load the credits art (nothing in the original look). Resolves once the manifests (and the ship
 * frames) are in, with the pictures still decoding; null when there is none (missing or malformed:
 * every picture and the ship stay original).
 */
export async function loadCreditsArt(base: string = import.meta.env.BASE_URL): Promise<CreditsArt | null> {
  if (shopIconMode() === "original") return null;
  try {
    const dir = "art/credits/";
    const [manifest, ships] = await Promise.all([
      fetchJson(`${base}${dir}manifest.json`).then((j) => parseCreditsArtManifest(j)),
      (async () => {
        try {
          const m = parseShopIconManifest(await fetchJson(`${base}${dir}ships/manifest.json`));
          if (!m) return null;
          const [atlas] = await Promise.all([decoded(fileUrl(base, `${dir}ships/`, m.image)), loadShopIcons(base)]);
          return { manifest: m, atlas };
        } catch (err) {
          console.warn("credits ship art didn't load; the ships stay original", err);
          return null;
        }
      })(),
    ]);
    if (!manifest) return null;
    const pictures = new Map<number, Promise<HTMLImageElement | null>>();
    for (const [n, p] of manifest.pictures) {
      pictures.set(
        n,
        decoded(fileUrl(base, dir, p.image)).catch((err) => {
          console.warn(`credits picture ${n} didn't load; it draws as the original`, err);
          return null;
        }),
      );
    }
    return new CreditsArt(pictures, ships);
  } catch (err) {
    console.warn("credits art didn't load; using the original pictures", err);
    return null;
  }
}
