// Remastered artwork for the full-screen pictures between levels (DECISIONS.md, "Screens between
// levels"; assets/art/README.md).
//
// The story screens draw every picture through pictureSource() in storyScreens.ts, which looks
// here first. public/art/pictures.json maps each picture number to its new image (relative to the
// site root): JE_loadPic's 1..13 (tyrian.pic), and 0 for tshp2.pcx (the `]P 000[` picture). The
// images are 1920x1200, the original 320x200's 16:10 with the same layout, so the fades, pans and
// text keep their places. The manifest is fetched once, when the first picture is wanted; without
// it (an offline build, a failed request) every picture is the original from the game data.
//
// Pictures the scripts show: 5 (most text screens), 7 (episode 2's ending), 8 and 9 (episode 1's
// ending and the ALE bonus), 13 (episode 4's last world) and 0 (tshp2.pcx, before Time War). The
// others (the item screen, the HUD frames, the title, the intro cards) are in the manifest for the
// screens that use them.

/** Picture number → image path relative to the site root (pictures.json). */
export type PictureManifest = Readonly<Record<string, string>>;

/** The image URL for `pic` in `manifest`, under `base` (the site root), or undefined. Pure, for tests. */
export function pictureUrl(manifest: PictureManifest, pic: number, base: string): string | undefined {
  const path = Object.hasOwn(manifest, String(pic)) ? manifest[pic] : undefined;
  return typeof path === "string" && path !== "" ? `${base}${path.replace(/^\//, "")}` : undefined;
}

let manifest: Promise<PictureManifest> | null = null;

/** public/art/pictures.json, fetched once; empty if it isn't there. */
function loadManifest(): Promise<PictureManifest> {
  manifest ??= fetch(`${import.meta.env.BASE_URL}art/pictures.json`)
    .then((r) => (r.ok ? (r.json() as Promise<PictureManifest>) : {}))
    .catch((err) => {
      console.warn("public/art/pictures.json didn't load; using the original pictures", err);
      return {};
    });
  return manifest;
}

/** The remastered image's URL for a picture, or undefined to use the original from the game data. */
export async function pictureArtUrl(pic: number): Promise<string | undefined> {
  return pictureUrl(await loadManifest(), pic, import.meta.env.BASE_URL);
}
