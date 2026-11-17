// The end credits on their own (JE_playCredits, src/app/episodeEnd.ts), for checking the credits'
// pictures and ship (D218) without finishing an episode. Open the dev server with `?debug=credits`.
//
//   &episode=E        the item data the ships come from (default 4; all four give the same ships)
//   &seed=N           the random seed, so the ships come in the same order (default 1)
//   &speed=N          run the credits' clock N times faster (default 1), to reach later pictures
//                     sooner: the C's ~28 s per picture becomes 28 / N
//   &sprites=original the original pictures and ship (the look switch, as everywhere)
//   &screen=anim      another of the episode-end screens instead (episodeEnd.ts): anim (episode 3's
//                     ending: the video, or with &sprites=original tyrend.anm, fetched then, D234),
//                     displayText, nextEpisode, superArcadeCode
//
// No music. Any key skips, as in the game; the credits then start again.

import { loadDevFiles } from "../assets/files";
import { episodeEndScreens } from "../app/episodeEnd";
import type { MusicPlayer } from "../audio/remaster";
import { loadHelpText } from "../sim/helptext";
import { mt_srand } from "../sim/mtrand";
import { buildResources, requireFile } from "../sim/resources";
import { g } from "../sim/state";
import { ui } from "../ui";
import { Backdrop } from "../ui/backdrop";
import type { View } from "../render/view";

const silent: MusicPlayer = {
  songCount: 0,
  play() {},
  restart() {},
  stop() {},
  fade() {},
  playing: false,
  volume: 0,
  resume() {},
  dispose() {},
};

export async function runCreditsHarness(view: View): Promise<void> {
  const params = new URLSearchParams(location.search);
  const num = (k: string, d: number) => (params.has(k) ? Number(params.get(k)) : d);
  ui.attachBackdrop(new Backdrop(view.renderer));
  const files = await loadDevFiles();
  if (!files) {
    document.body.insertAdjacentHTML("beforeend", "<pre style='color:#f88'>?debug=credits needs the dev server with TYRIAN_DATA</pre>");
    return;
  }
  const speed = num("speed", 1);
  if (speed > 1) {
    // The credits' timers read performance.now() (vga.ts): scale it.
    const real = performance.now.bind(performance);
    const t0 = real();
    performance.now = () => t0 + (real() - t0) * speed;
  }
  mt_srand(num("seed", 1));
  g.res = buildResources(files, num("episode", 4));
  view.setPalettes(g.res.palettes);
  loadHelpText(requireFile(files, "tyrian.hdt"));
  Object.assign(window, { tyrianHarness: { view, g } });
  const screens = ["anim", "displayText", "credits", "nextEpisode", "superArcadeCode"] as const;
  const screen = screens.find((s) => s === params.get("screen")) ?? "credits";
  for (;;) await episodeEndScreens({ files, music: silent })(screen);
}
