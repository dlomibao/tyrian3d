// Remastered shop icons (DECISIONS.md D210): painted high-resolution versions of the item screen's
// pictures (JE_drawItem's 24x28 blocks), made by tools/shop_icons.py from Gemini's paintings.
//
// public/art/shop/manifest.json lists each icon's frame in one atlas:
//
//   { "scale": 6, "image": "icons.webp",
//     "icons": { "newsh1.shp:7": { "x": 8, "y": 8, "w": 144, "h": 168 } } }
//
// keyed "<sheet id>:<first sprite index>": newsh1.shp for weapons, shields, generators and
// sidekicks (itemGraphic), tyrian.shp#8 (spriteSheet9) for ships (shipGraphic). A frame is the
// 24x28 picture times `scale`, its alpha the original silhouette. An icon the manifest leaves out,
// or any icon before the atlas has loaded (or when it fails), draws as the original pixels.
//
// The look follows the flat sprite art (D42): `?sprites=original|remastered`, else the effects
// look (`?vfx=original` draws the original pixels).

import { spriteArtModeFromSearch, type SpriteArtMode } from "../render/spriteArt";
import { vfxModeFromSearch } from "../render/vfx/vfxMode";

/** One icon's frame in the atlas, in atlas pixels. */
export interface ShopIconFrame {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface ShopIconManifest {
  scale: number;
  image: string;
  icons: Map<string, ShopIconFrame>;
}

const isCount = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v) && v >= 0;

/** Check and index a manifest; null if it isn't one. Malformed frames are dropped with a warning. */
export function parseShopIconManifest(json: unknown, warn: (msg: string) => void = console.warn): ShopIconManifest | null {
  if (typeof json !== "object" || json === null) return null;
  const { scale, image, icons } = json as { scale?: unknown; image?: unknown; icons?: unknown };
  if (!isCount(scale) || scale <= 0 || typeof image !== "string" || image === "" || typeof icons !== "object" || icons === null) return null;
  const out: ShopIconManifest = { scale, image, icons: new Map() };
  for (const [key, f] of Object.entries(icons as Record<string, unknown>)) {
    const { x, y, w, h } = (f ?? {}) as Record<string, unknown>;
    if (!/^.+:\d+$/.test(key) || !isCount(x) || !isCount(y) || !isCount(w) || !isCount(h) || w === 0 || h === 0) {
      warn(`shop icons: frame ${key} is malformed; it draws as the original`);
      continue;
    }
    out.icons.set(key, { x, y, w, h });
  }
  return out;
}

/** The manifest key of an icon: its sheet's id and its first sprite's index. */
export const shopIconKey = (sheetId: string, index: number): string => `${sheetId}:${index}`;

/** The icon look the page asks for: `?sprites=`, else the effects look (D42's switch). */
export function shopIconMode(search?: string): SpriteArtMode {
  return spriteArtModeFromSearch(search) ?? (vfxModeFromSearch(search) === "remastered" ? "remastered" : "original");
}

interface Loaded {
  manifest: ShopIconManifest;
  atlas: CanvasImageSource;
  width: number;
  height: number;
}

let loaded: Loaded | null = null;
let loading: Promise<boolean> | null = null;
const urls = new Map<string, string>();

/**
 * Fetch the manifest and atlas once (no-op in the original look). Resolves true when the art is
 * ready, false when there is none (missing, malformed or failed: every icon stays original).
 */
export function loadShopIcons(base: string = import.meta.env.BASE_URL): Promise<boolean> {
  if (shopIconMode() === "original") return Promise.resolve(false);
  loading ??= (async () => {
    try {
      const res = await fetch(`${base}art/shop/manifest.json`);
      if (!res.ok) return false;
      const manifest = parseShopIconManifest(await res.json());
      if (!manifest) return false;
      const img = new Image();
      img.decoding = "async";
      img.src = `${base}art/shop/${manifest.image.split("/").map(encodeURIComponent).join("/")}`;
      await img.decode();
      loaded = { manifest, atlas: img, width: img.naturalWidth, height: img.naturalHeight };
      return true;
    } catch (err) {
      console.warn("shop icons didn't load; using the original pictures", err);
      return false;
    }
  })();
  return loading;
}

/**
 * The remastered icon for (sheet, first sprite) as an image URL, or undefined to draw the original
 * (no art for it, not loaded yet, or the original look). Each icon is cut from the atlas once.
 */
export function shopIconUrl(sheetId: string, index: number): string | undefined {
  if (!loaded || shopIconMode() === "original") return undefined;
  const key = shopIconKey(sheetId, index);
  const hit = urls.get(key);
  if (hit !== undefined) return hit || undefined;
  const f = loaded.manifest.icons.get(key);
  let url = "";
  if (f && f.x + f.w <= loaded.width && f.y + f.h <= loaded.height) {
    const canvas = document.createElement("canvas");
    canvas.width = f.w;
    canvas.height = f.h;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.drawImage(loaded.atlas, f.x, f.y, f.w, f.h, 0, 0, f.w, f.h);
      url = canvas.toDataURL();
    }
  }
  urls.set(key, url);
  return url || undefined;
}
