// `?destruct`: straight into Destruct, for working on it (the title's DESTRUCT code is the way in
// for players). When the player leaves it, the page reloads without the parameter, into the game.

import { filesFromZip, loadDevFiles, type FileMap } from "../assets/files";
import { loadStoredZip } from "../assets/store";
import { Music } from "../audio/music";
import { SoundEffects } from "../audio/sfx";
import { askForData } from "../app/screens";
import { connectVolumes, loadPrefs } from "../app/prefs";
import { mt_srand } from "../sim/mtrand";
import { requireFile } from "../sim/resources";
import type { View } from "../render/view";
import { openDestruct } from "./index";

/** run.ts's getFiles: the dev server's data, the zip kept from last time, or ask for it. */
async function getFiles(): Promise<FileMap> {
  const dev = await loadDevFiles();
  if (dev) return dev;
  const stored = await loadStoredZip();
  if (stored) {
    try {
      return await filesFromZip(stored);
    } catch {
      // A bad cached copy: ask again.
    }
  }
  return askForData();
}

export async function runDestructDebug(view: View): Promise<void> {
  const files = await getFiles();
  mt_srand(Math.floor(Date.now() / 1000)); // opentyr.c main's mt_srand(time(NULL))
  loadPrefs();
  const context = new AudioContext();
  const music = new Music(requireFile(files, "music.mus"), { context });
  const sfx = new SoundEffects(requireFile(files, "tyrian.snd"), requireFile(files, "voices.snd"), context);
  connectVolumes(music, sfx);
  await openDestruct({ files, view, sfx, music });
  music.stop();
  const url = new URL(location.href);
  url.searchParams.delete("destruct");
  location.href = url.toString();
}
