// The screens at the end of an episode, on the stage the story screens use (cinema.ts).
// JE_loadMap (src/sim/tyrian2.ts) pauses for each one (LoadMapPause) and the host runs it with
// episodeEndScreens():
//
// - "anim": playAnim("tyrend.anm", 0, 7) (animlib.c L152-278), episode 3's `]A[`: the original
//   frames, scaled up on the stage.
// - "displayText": JE_displayText (tyrian2.c L3709-3760) with JE_outCharGlow (mainint.c L85-170):
//   the final score and a secret hint, `]Q[`, glowing in on the story screens' text panel over
//   the script's picture 5.
// - "credits": JE_playCredits (mainint.c L2347-2518), after the last episode: the credits roll
//   smoothly in the interface's type, the C's pictures fade in and out beside them and a ship
//   weaves up the side.
// - "nextEpisode": the next episode's name, from JE_nextEpisode (mainint.c L987-1000), as a title
//   card over the 3D backdrop.
// - "superArcadeCode": the next Super Arcade ship and its code (tyrian2.c L2603-2645), a card over
//   the ship turning in the hangar.
// - "highScoreCheck": JE_highScoreCheck isn't part of this feature; nothing is shown.
//
// What the C does with the game's state there (the hint's text, the next episode, the SuperCarrot)
// is in the sim; these only draw and wait, with the C's frame timing and its rule that any key
// moves on. They use the sim's mt_rand where the C does (the credits' ships), so the random
// sequence afterwards is the C's for the same key presses.

import { animFrames, parseAnim } from "../data/anim";
import { parseCredits } from "../data/credits";
import { parseSpriteTable, type TableSprite } from "../data";
import type { MusicPlayer } from "../audio/remaster";
import { parseMenuText, type MenuText } from "../sim/helptext";
import { mt_rand } from "../sim/mtrand";
import { requireFile, type TyrianFiles } from "../sim/resources";
import { s8, s16 } from "../sim/cint";
import { g, SA_ENGAGE, SA_NORTSHIPZ } from "../sim/state";
import { TYREND_ANIM, type LoadMapPause } from "../sim/tyrian2";
import { SANextShip, SAShip } from "../sim/varz";
import { h, title, ui } from "../ui";
import { bankTint, openCinema, releaseCinema, STAGE_H, STAGE_W, type Cinema } from "./cinema";
import { BLACK } from "./fade";
import { displayTextOver, drawPicture, paletteColors, pictureSource } from "./storyScreens";
import { paletteRgb, Vga, type PressSource } from "./vga";

export interface EpisodeEndHost {
  files: TyrianFiles;
  music: MusicPlayer;
}

/** pcxmast.c pcxpal[]: each picture's palette. */
const pcxpal = [0, 7, 5, 8, 10, 5, 18, 19, 19, 20, 21, 22, 5];

/** Every episode's `]Q[` comes right after `]P 005[`, whose picture the hint is written over. */
const HINT_PICTURE = 5;

/** The songs JE_playCredits plays (play_song(8), then play_song(9) at the end). */
const SONG_CREDITS = 8;
const SONG_CREDITS_END = 9;

let menuText: { hdt: Uint8Array; text: MenuText } | null = null;
function texts(files: TyrianFiles): MenuText {
  const hdt = requireFile(files, "tyrian.hdt");
  if (menuText?.hdt !== hdt) menuText = { hdt, text: parseMenuText(hdt) };
  return menuText.text;
}

/** The stage's presses, as the 320x200 screen's waits read them. */
const stageInput = (stage: Cinema): PressSource => ({ get: () => stage.getInput(), clear: () => stage.clearInput() });

/**
 * The host's handler for JE_loadMap's pauses other than the item screen. Make one for each
 * JE_loadMap: it plays the songs the episode script asks for from then on (`]M`, play_song).
 */
export function episodeEndScreens(host: EpisodeEndHost): (pause: Exclude<LoadMapPause, "itemScreen">) => Promise<void> {
  g.song = -1; // only songs asked for during this JE_loadMap
  let playing = -1;
  const playSimSong = () => {
    if (g.song >= 0 && g.song !== playing) host.music.play(g.song);
    playing = g.song;
  };

  return async (pause) => {
    if (pause === "highScoreCheck") return; // JE_highScoreCheck: not part of this feature
    playSimSong();
    // The stage the story screens left up (the hint is written over their picture), or a new one.
    const stage = openCinema();
    try {
      switch (pause) {
        case "anim":
          await playAnim(stage, host.files);
          break;
        case "displayText":
          await displayHint(stage, host.files);
          break;
        case "credits":
          await playCredits(stage, host);
          playing = -1;
          break;
        case "nextEpisode":
          await showNextEpisode(stage, host.files);
          break;
        case "superArcadeCode":
          await showSuperArcadeCode(stage, host.files);
          break;
      }
    } finally {
      stage.setSkip("none");
      releaseCinema();
    }
  };
}

/** playAnim(filename, startingFrame, speed) (animlib.c L152-278), each frame scaled up on the stage. */
async function playAnim(stage: Cinema, files: TyrianFiles): Promise<void> {
  const { filename, startingFrame, speed } = TYREND_ANIM;

  stage.clearOverlay();
  stage.setMode("picture");
  stage.setSkip("skip");
  stage.fade.set(0); // the animation sets its own palette
  const v = new Vga({
    input: stageInput(stage),
    onShow: (canvas) => {
      stage.ctx.imageSmoothingEnabled = false;
      stage.ctx.drawImage(canvas, 0, 0, STAGE_W, STAGE_H);
      stage.present();
    },
  });

  v.clr256();
  v.showVGA();

  const data = files.get(filename);
  if (!data) {
    console.warn(`Failed to open file '${filename}'`);
    return;
  }
  const anim = parseAnim(data);

  v.setPalette(anim.palette);

  for (const image of animFrames(anim, startingFrame)) {
    v.setFrameCount(speed);
    v.pixels.set(image);
    v.showVGA();

    if (await v.waitUntilGetInputOrElapsed()) break;
  }
}

/**
 * The `]Q[` text: JE_displayText of g.levelWarningText at g.frameCountMax in picture 5's palette,
 * then fade_black(15). It's written over the picture the script's `]P 005[` put up; if the stage
 * is fresh (that picture wasn't shown), picture 5 is put up first.
 */
async function displayHint(stage: Cinema, files: TyrianFiles): Promise<void> {
  const palette = pcxpal[HINT_PICTURE - 1];
  if (!stage.showing || stage.mode !== "picture") {
    const { source } = await pictureSource(files, HINT_PICTURE, palette);
    stage.blank();
    drawPicture(stage, source);
    stage.fade.set(0);
  }
  stage.clearOverlay();

  await displayTextOver(stage, paletteColors(palette), {
    lines: [...g.levelWarningText],
    prompt: g.miscText[4],
    frameCountMax: g.frameCountMax,
    warningRed: false,
    warningDisplay: false,
    useLastBank: g.useLastBank,
  });

  await stage.fadeTo(1, BLACK, 15);
}

/** One line of tyrian.cdt as the credits show it: its colour bank and text, or null for a blank line. */
export function creditLine(raw: string): { bank: number; text: string } | null {
  if (raw.length === 0 || raw[0] === ".") return null;
  return { bank: (raw.charCodeAt(0) - 65) & 0xff, text: raw.slice(1) };
}

/**
 * How far the credits have rolled at tick `ticks`, in lines: line L's top is at (11 + L - roll)
 * lines from the top of the C's 10-line screen (y = 220 + 20 L - ticks / 3, 20 pixels a line).
 * The C moves a pixel every 3 ticks; this is the same line, without the steps. Pure, for tests.
 */
export function creditsRoll(ticks: number): number {
  return ticks / 3 / 20;
}

/** JE_playCredits (mainint.c L2347-2518). */
async function playCredits(stage: Cinema, host: EpisodeEndHost): Promise<void> {
  let currentpic = 0;
  let fade = 0;
  let fadechg = 1;
  let currentship = 0;
  let shipx = 0;
  let shipxwait = 0;
  let shipxc = 0;
  let shipxca = 0;

  const estsc = host.files.get("estsc.shp");
  const cdt = host.files.get("tyrian.cdt");
  if (!estsc || !cdt) {
    console.warn("JE_playCredits: estsc.shp or tyrian.cdt is missing");
    return;
  }
  const extraShapes = parseSpriteTable(estsc).sprites; // load_sprites_file(EXTRA_SHAPES, "estsc.shp")

  // Only the timers and the sprite blits of the C's screen are used: the credits are drawn on the stage.
  const v = new Vga({ input: stageInput(stage) });

  v.setFrameCount2(1000);

  host.music.play(SONG_CREDITS);

  // load credits text
  const credstr = parseCredits(cdt);

  const colors = paletteRgb(g.res.palettes[6 - 1]);
  stage.blank();
  stage.setSkip("skip");
  const view = new CreditsView(stage, credstr, colors, extraShapes);
  await stage.fadeTo(0, BLACK, 2); // fade_palette(colors, 2)

  let songFaded = false;
  let endSong = false;

  const ticks_max = credstr.length * 20 * 3;
  for (let ticks = 0; ticks < ticks_max; ++ticks) {
    v.setFrameCount(1);

    view.picture(currentpic, fade);

    fade += fadechg;
    if (fade === 0 && fadechg === -1) {
      fadechg = 1;
      ++currentpic;
      if (currentpic >= extraShapes.length) currentpic = 0;
    }
    if (fade === 15) fadechg = 0;

    if (v.frameCount2Elapsed()) {
      v.setFrameCount2(900);

      fadechg = -1;
    }

    if (ticks % 200 === 0) {
      currentship = (mt_rand() % 11) + 1;
      shipxwait = (mt_rand() % 80) + 10;
      if (mt_rand() % 2 === 1) {
        shipx = 1;
        shipxc = 0;
        shipxca = 1;
      } else {
        shipx = 900;
        shipxc = 0;
        shipxca = -1;
      }
    }

    shipxwait = s16(shipxwait - 1);
    if (shipxwait === 0) {
      if (shipx === 1 || shipx === 900) shipxc = 0;
      shipxca = -shipxca;
      shipxwait = (mt_rand() % 40) + 15;
    }
    shipxc = s8(shipxc + shipxca);
    shipx = s16(shipx + shipxc);
    if (shipx < 1) {
      shipx = 1;
      shipxwait = 1;
    }
    if (shipx > 900) {
      shipx = 900;
      shipxwait = 1;
    }
    const tmp_unknown = shipxc * shipxc;
    if (450 + tmp_unknown < 0 || 450 + tmp_unknown > 900) {
      if (shipxca < 0 && shipxc < 0) shipxwait = 1;
      if (shipxca > 0 && shipxc > 0) shipxwait = 1;
    }

    let ship_sprite = g.res.items.ships[currentship].shipGraphic;
    if (shipxc < -10) ship_sprite -= shipxc < -20 ? 4 : 2;
    else if (shipxc > 10) ship_sprite += shipxc > 20 ? 4 : 2;

    // blit_sprite2x2(shipx / 40, 184 - (ticks % 200), ship_sprite)
    view.ship(ship_sprite, shipx, 184 - (ticks % 200));

    // The lines bottom_line - 10 .. bottom_line - 1 at y = 20 - (ticks / 3) % 20 + 20 k.
    view.roll(creditsRoll(ticks));

    // levels-in-episode, under the last picture
    view.note(currentpic === extraShapes.length - 1 ? g.miscText[54] : null);

    const bottom_line = Math.trunc(Math.trunc(ticks / 3) / 20);
    // fade_song() every tick of that line in the C; once is the same.
    if (bottom_line === credstr.length - 8 && !songFaded) {
      songFaded = true;
      host.music.fade();
    }

    if (ticks === ticks_max - 1) {
      --ticks;
      // play_song(9) every tick from here; it only starts the song the first time.
      if (!endSong) host.music.play(SONG_CREDITS_END);
      endSong = true;
    }

    // JE_showVGA()

    if (await v.waitUntilGetInputOrElapsed()) break;
  }

  await stage.fadeTo(1, BLACK, 10); // fade_black(10)
}

/** The credits on the stage: the rolling lines, the pictures beside them, the ship and the note. */
class CreditsView {
  private readonly rollEl: HTMLElement;
  private readonly noteEl: HTMLElement;
  private readonly shipEl: HTMLCanvasElement;
  private readonly pictures: (HTMLCanvasElement | null)[];
  private shownPic = -1;
  private shipSprite = -1;
  private noteText: string | null = null;
  /** A scratch 320x200 screen to draw the C's sprites on before cutting them out. */
  private readonly scratch = new Vga();

  constructor(
    stage: Cinema,
    credstr: string[],
    private readonly colors: Uint8Array,
    shapes: (TableSprite | null)[],
  ) {
    this.rollEl = h("div", { class: "cinema-credits__roll" });
    for (const raw of credstr) {
      const line = creditLine(raw);
      const el = h("div", { class: "cinema-credits__line", text: line?.text ?? "" });
      // JE_outTextAdjust(..., color, -2): the bank's shade, two below the glyphs' own.
      if (line) el.style.setProperty("--tint", bankTint(colors, line.bank).ink);
      this.rollEl.append(el);
    }
    this.noteEl = h("div", { class: "cinema-credits__note" });
    this.shipEl = h("canvas", { class: "cinema-credits__ship", attrs: { width: "24", height: "28" } });
    // Each picture once, at full brightness; the C's fade (fade - 15) becomes its opacity.
    this.pictures = shapes.map((pic) => {
      if (!pic) return null;
      this.scratch.clr256();
      this.scratch.blitSpriteHV(0, 0, pic, 0x0, 0);
      const canvas = this.scratch.cutOut(pic.width, Math.min(pic.height, 200), colors);
      canvas.className = "cinema-credits__pic";
      canvas.style.setProperty("--aspect", `${pic.width} / ${pic.height}`);
      return canvas;
    });
    stage.layer.replaceChildren(
      h("div", { class: "cinema-credits", attrs: { "aria-label": "Credits", role: "marquee" } }, this.rollEl),
      ...this.pictures.filter((p): p is HTMLCanvasElement => p !== null),
      this.shipEl,
      this.noteEl,
    );
  }

  /** blit_sprite_hv(pic, 319 - width, 100 - height / 2, 0x0, fade - 15): picture `n` at fade 0..15. */
  picture(n: number, fade: number): void {
    if (n !== this.shownPic) {
      this.pictures[this.shownPic]?.style.setProperty("--o", "0");
      this.shownPic = n;
    }
    this.pictures[n]?.style.setProperty("--o", String(Math.max(0, Math.min(1, fade / 15))));
  }

  /** The ship: sprite `sprite` (2x2 tiles) at x shipx / 40 and y, in the C's 320x200 screen. */
  ship(sprite: number, shipx: number, y: number): void {
    if (sprite !== this.shipSprite) {
      this.shipSprite = sprite;
      this.scratch.clr256();
      this.scratch.blitSprite2x2(0, 0, g.res.spriteSheet9.data, sprite);
      const cut = this.scratch.cutOut(24, 28, this.colors);
      const ctx = this.shipEl.getContext("2d")!;
      ctx.clearRect(0, 0, 24, 28);
      ctx.drawImage(cut, 0, 0);
    }
    this.shipEl.style.setProperty("--x", String((shipx - 1) / 899));
    this.shipEl.style.setProperty("--y", String(y / 200));
  }

  /** Roll the lines `roll` lines on (creditsRoll). */
  roll(roll: number): void {
    this.rollEl.style.transform = `translateY(calc(${(11 - roll).toFixed(4)} * var(--line)))`;
  }

  /** The note under the last picture (miscText[54], the levels in each episode), or none. */
  note(text: string | null): void {
    if (text === this.noteText) return;
    this.noteText = text;
    if (text !== null) this.noteEl.textContent = text;
    this.noteEl.classList.toggle("is-shown", text !== null);
  }
}

/** An episode's name, "Episode 2: Treachery", as a title and its kicker. */
export function splitEpisodeName(name: string): { kicker?: string; title: string } {
  const at = name.indexOf(":");
  if (at < 0) return { title: name.trim() };
  return { kicker: name.slice(0, at).trim(), title: name.slice(at + 1).trim() };
}

/**
 * JE_nextEpisode's title for the next episode (mainint.c L992-1000): its name (miscText[4], the
 * C's "Press a key" under it, is the card's key hint), faded in, until a key is pressed.
 */
async function showNextEpisode(stage: Cinema, files: TyrianFiles): Promise<void> {
  const name = splitEpisodeName(texts(files).episodeName[g.episodeNum] ?? "");

  stage.blank();
  stage.setMode("space");
  stage.showCard(h("div", { class: "cinema-card" }, title(name.title, name.kicker)));

  await stage.fadeTo(0, BLACK, 15); // fade_palette(colors, 15)

  await stage.waitUntilGetInput();
}

/**
 * After the last episode, the next Super Arcade ship (tyrian2.c L2603-2645): its name, the ship
 * (the backdrop's 3D model of its sprite, turning in the hangar) and the code to type at the
 * title screen, faded in over 50 frames, until a key is pressed.
 */
async function showSuperArcadeCode(stage: Cinema, files: TyrianFiles): Promise<void> {
  const { superShips, specialName } = texts(files);
  const next = SANextShip[g.superArcadeMode];

  stage.blank();
  const card = h("div", { class: "cinema-card" });
  if (next === SA_ENGAGE) {
    card.append(title(`${g.miscTextB[4]} ${g.pName[0]}`), h("p", { text: `Or play... ${specialName[7]}` }));
  } else {
    card.append(title(superShips[next], superShips[0]));
  }

  // blit_sprite2x2(148, 70, ships[SAShip[next - 1]].shipGraphic)
  const shipGraphic = next < SA_NORTSHIPZ ? g.res.items.ships[SAShip[next - 1]].shipGraphic : -1;
  // else if (next == SA_NORTSHIPZ) trentWin = true: done by the sim.
  stage.setMode(shipGraphic >= 0 ? "hangar" : "space");
  if (shipGraphic >= 0) ui.backdrop?.setShipGraphic?.(shipGraphic);

  // "Type <code> at Title", the code picked out.
  card.append(h("p", {}, "Type ", h("span", { class: "cinema-code", text: specialName[next - 1] }), " at Title"));
  stage.showCard(card);

  await stage.fadeTo(0, BLACK, 50); // fade_palette(colors, 50)

  await stage.waitUntilGetInput();

  // The backdrop shows the player's own ship again.
  if (shipGraphic >= 0) ui.backdrop?.setShipGraphic?.(g.res.items.ships[g.player[0].items.ship]?.shipGraphic ?? -1);
}
