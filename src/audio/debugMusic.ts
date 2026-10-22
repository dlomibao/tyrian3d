// Dev-only music test page. Run `npm run dev` and open /src/audio/debugMusic.html (the dev server
// serves the local data folder at /tyrian-data/; set TYRIAN_DATA to point elsewhere, or pass
// ?mus=<url>). Not part of the production build: nothing imports this file, and the build only
// bundles index.html.

import { Music } from "./music";

// Song titles from OpenTyrian's musmast.c (index = play_song argument).
const TITLES = [
  "Asteroid Dance Part 2", "Asteroid Dance Part 1", "Buy/Sell Music", "CAMANIS", "CAMANISE",
  "Deli Shop Quartet", "Deli Shop Quartet No. 2", "Ending Number 1", "Ending Number 2",
  "End of Level", "Game Over Solo", "Gryphons of the West", "Somebody pick up the Gryphone",
  "Gyges, Will You Please Help Me?", "I speak Gygese", "Halloween Ramble", "Tunneling Trolls",
  "Tyrian, The Level", "The MusicMan", "The Navigator", "Come Back to Me, Savara",
  "Come Back again to Savara", "Space Journey 1", "Space Journey 2", "The final edge", "START5",
  "Parlance", "Torm - The Gathering", "TRANSON", "Tyrian: The Song", "ZANAC3", "ZANACS",
  "Return me to Savara", "High Score Table", "One Mustn't Fall", "Sarah's Song",
  "A Field for Mag", "Rock Garden", "Quest for Peace", "Composition in Q", "BEER",
];

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const status = $("status");

async function main(): Promise<void> {
  // ?mus=<url> loads music.mus from elsewhere (e.g. when testing a production build).
  const url = new URLSearchParams(location.search).get("mus") ?? "/tyrian-data/music.mus";
  const res = await fetch(url);
  if (!res.ok) throw new Error(`music.mus: HTTP ${res.status}`);
  const music = new Music(new Uint8Array(await res.arrayBuffer()));
  Object.assign(window, { music });

  const select = $<HTMLSelectElement>("song");
  for (let i = 0; i < music.songCount; i++) {
    const opt = document.createElement("option");
    opt.value = String(i);
    opt.textContent = `${i}: ${TITLES[i] ?? "?"}`;
    select.append(opt);
  }

  const show = (msg: string) => {
    status.textContent = `${msg}\ncontext: ${music.context?.state ?? "not created"} @ ${music.context?.sampleRate ?? "-"} Hz`;
  };
  $("play").onclick = () => {
    music.play(Number(select.value));
    show(`play ${select.value}`);
  };
  $("restart").onclick = () => (music.restart(), show("restart"));
  $("stop").onclick = () => (music.stop(), show("stop"));
  $("fade").onclick = () => (music.fade(), show("fade"));
  $<HTMLInputElement>("volume").oninput = (e) => {
    music.volume = Number((e.target as HTMLInputElement).value);
    show(`volume ${music.volume}`);
  };
  show(`${music.songCount} songs loaded`);
}

main().catch((err) => {
  status.textContent = String(err);
  console.error(err);
});
