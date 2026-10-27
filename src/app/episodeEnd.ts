// The screens at the end of an episode, drawn as the original drew them: a 320x200 screen (vga.ts)
// in a canvas. JE_loadMap (src/sim/tyrian2.ts) pauses for each one (LoadMapPause) and the host
// runs it with episodeEndScreens():
//
// - "anim": playAnim("tyrend.anm", 0, 7) (animlib.c L152-278), episode 3's `]A[`.
// - "displayText": JE_displayText (tyrian2.c L3709-3760) with JE_outCharGlow (mainint.c L85-170):
//   the final score and a secret hint, `]Q[`.
// - "credits": JE_playCredits (mainint.c L2347-2518), after the last episode.
// - "nextEpisode": the next episode's name, from JE_nextEpisode (mainint.c L987-1000).
// - "superArcadeCode": the next Super Arcade ship and its code (tyrian2.c L2603-2645).
// - "highScoreCheck": JE_highScoreCheck isn't part of this feature; nothing is shown.
//
// What the C does with the game's state there (the hint's text, the next episode, the SuperCarrot)
// is in the sim; these only draw and wait. They use the sim's mt_rand where the C does (the
// credits' ships), so the random sequence afterwards is the C's for the same key presses.

import "./episodeEnd.css";
import { animFrames, parseAnim } from "../data/anim";
import { parseCredits } from "../data/credits";
import { parseSpriteTable } from "../data";
import type { MusicPlayer } from "../audio/remaster";
import { parseMenuText, type MenuText } from "../sim/helptext";
import { mt_rand } from "../sim/mtrand";
import { requireFile, type TyrianFiles } from "../sim/resources";
import { s8, s16 } from "../sim/cint";
import { g, SA_ENGAGE, SA_NORTSHIPZ } from "../sim/state";
import { TYREND_ANIM, type LoadMapPause } from "../sim/tyrian2";
import { SANextShip, SAShip } from "../sim/varz";
import { fontSprite, paletteRgb, Vga, type SpriteTableSprites } from "./vga";

export interface EpisodeEndHost {
  files: TyrianFiles;
  music: MusicPlayer;
}

/** sprite.h: the sprite tables in tyrian.shp. */
const FONT_SHAPES = 0;
const SMALL_FONT_SHAPES = 1;
const TINY_FONT = 2;

/** pcxmast.c pcxpal[]: each picture's palette. */
const pcxpal = [0, 7, 5, 8, 10, 5, 18, 19, 19, 20, 21, 22, 5];

/** Every episode's `]Q[` comes right after `]P 005[`, whose picture the hint is written over. */
const HINT_PICTURE = 5;

/** The songs JE_playCredits plays (play_song(8), then play_song(9) at the end). */
const SONG_CREDITS = 8;
const SONG_CREDITS_END = 9;

const fonts = () => g.res.spriteTables.map((t) => t.sprites) as SpriteTableSprites[];

let menuText: { hdt: Uint8Array; text: MenuText } | null = null;
function texts(files: TyrianFiles): MenuText {
  const hdt = requireFile(files, "tyrian.hdt");
  if (menuText?.hdt !== hdt) menuText = { hdt, text: parseMenuText(hdt) };
  return menuText.text;
}

// One screen stays up between screens that follow each other, so the 3D view doesn't flash
// through; it goes once nothing has used it for a moment (the item screen or the level is next).
let screen: Vga | null = null;
let closeTimer = 0;

function openScreen(): Vga {
  clearTimeout(closeTimer);
  screen ??= new Vga();
  return screen;
}

function releaseScreen(): void {
  clearTimeout(closeTimer);
  closeTimer = window.setTimeout(() => {
    screen?.dispose();
    screen = null;
  }, 150);
}

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
    const v = openScreen();
    try {
      switch (pause) {
        case "anim":
          await playAnim(v, host.files);
          break;
        case "displayText":
          await displayHint(v);
          break;
        case "credits":
          await playCredits(v, host);
          playing = -1;
          break;
        case "nextEpisode":
          await showNextEpisode(v, host.files);
          break;
        case "superArcadeCode":
          await showSuperArcadeCode(v, host.files);
          break;
      }
    } finally {
      releaseScreen();
    }
  };
}

/** playAnim(filename, startingFrame, speed) (animlib.c L152-278). */
async function playAnim(v: Vga, files: TyrianFiles): Promise<void> {
  const { filename, startingFrame, speed } = TYREND_ANIM;

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
 * The `]Q[` text: JE_displayText of g.levelWarningText at g.frameCountMax, over picture 5's
 * palette, then fade_black(15). The picture itself is the episode script's `]P`, not drawn here.
 */
async function displayHint(v: Vga): Promise<void> {
  v.clr256();
  v.setPalette(paletteRgb(g.res.palettes[pcxpal[HINT_PICTURE - 1]]));
  v.input.clear();

  await JE_displayText(v, g.levelWarningText, g.frameCountMax);

  await v.fadeBlack(15);
}

/**
 * JE_displayText (tyrian2.c L3709-3760), without the warning bars (`]W` with sirens) and Esc.
 * `frameCountMax` is a copy: the C's changes to it only matter within the screen.
 */
async function JE_displayText(v: Vga, lines: string[], frameCountMax: number): Promise<void> {
  const tiny = fonts()[TINY_FONT];
  const st = { frameCountMax };

  /* Display Warning Text */
  let tempY = 55;
  for (const line of lines) {
    await JE_outCharGlow(v, 10, tempY, line, tiny, st);
    tempY += 10;
  }

  let slow: boolean;
  if (st.frameCountMax !== 0) {
    st.frameCountMax = 6;
    slow = true;
  } else {
    slow = false;
  }
  const tempW = 184;

  await JE_outCharGlow(v, Vga.fontCenter(g.miscText[4], tiny), tempW, g.miscText[4], tiny, st);

  for (;;) {
    v.setFrameCount(1);

    if (await v.waitUntilGetInputOrElapsed()) break;

    if (st.frameCountMax === 0 && slow) break;
  }
}

/** JE_outCharGlow (mainint.c L85-170): the text lights up a character at a time. */
async function JE_outCharGlow(v: Vga, x: number, y: number, s: string, tiny: SpriteTableSprites, st: { frameCountMax: number }): Promise<void> {
  const glowcol = new Array<number>(60).fill(-8);
  const glowcolc = new Array<number>(60).fill(1);
  const textloc = new Array<number>(60).fill(0);

  const bank = g.useLastBank ? 15 : 14;

  if (s.length === 0) return;

  if (st.frameCountMax === 0) {
    v.textShadePart(x, y, s, bank, 0, tiny);
    v.showVGA();
    return;
  }

  const maxloc = s.length;

  let loc = x;
  for (let z = 0; z < maxloc; z++) {
    textloc[z] = loc;

    const sprite_id = fontSprite(s, z);

    if (s[z] === " ") loc += 6;
    else if (sprite_id !== -1) loc += (tiny[sprite_id]?.width ?? 0) + 1;
  }

  for (loc = 0; loc < s.length + 28; loc++) {
    v.setFrameCount(1);

    let sprite_id = -1;

    let z: number;
    for (z = loc - 28; z <= loc; z++) {
      if (z >= 0 && z < maxloc) {
        sprite_id = fontSprite(s, z);

        const sprite = tiny[sprite_id];
        if (sprite_id !== -1 && sprite) {
          v.blitSpriteHV(textloc[z], y, sprite, bank, glowcol[z]);

          glowcol[z] = s8(glowcol[z] + glowcolc[z]);
          if (glowcol[z] > 9) glowcolc[z] = -1;
        }
      }
    }
    const last = tiny[sprite_id];
    if (sprite_id !== -1 && --z < maxloc && last) v.blitSpriteDark(textloc[z] + 1, y + 1, last, true);

    v.showVGA();

    for (let frameCount = st.frameCountMax; frameCount > 0; --frameCount) {
      await v.waitUntilElapsed();

      if (v.input.get()) st.frameCountMax = 0;

      v.setFrameCount(1);
    }
  }
}

/** JE_playCredits (mainint.c L2347-2518). */
async function playCredits(v: Vga, host: EpisodeEndHost): Promise<void> {
  const small = fonts()[SMALL_FONT_SHAPES];
  const tiny = fonts()[TINY_FONT];

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

  v.setFrameCount2(1000);

  host.music.play(SONG_CREDITS);

  // load credits text
  const credstr = parseCredits(cdt);

  const colors = paletteRgb(g.res.palettes[6 - 1]);
  v.clr256();
  v.showVGA();
  await v.fadePalette(colors, 2);

  let songFaded = false;
  let endSong = false;

  const ticks_max = credstr.length * 20 * 3;
  for (let ticks = 0; ticks < ticks_max; ++ticks) {
    v.setFrameCount(1);

    v.clr256();

    const pic = extraShapes[currentpic];
    if (pic) v.blitSpriteHV(319 - pic.width, 100 - Math.trunc(pic.height / 2), pic, 0x0, fade - 15);

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

    v.blitSprite2x2(Math.trunc(shipx / 40), 184 - (ticks % 200), g.res.spriteSheet9.data, ship_sprite);

    const bottom_line = Math.trunc(Math.trunc(ticks / 3) / 20);
    let y = 20 - (Math.trunc(ticks / 3) % 20);

    for (let line = bottom_line - 10; line < bottom_line; ++line) {
      if (line >= 0 && line < credstr.length) {
        if (credstr[line][0] !== "." && credstr[line].length > 0) {
          const color = (credstr[line].charCodeAt(0) - 65) & 0xff;
          const text = credstr[line].slice(1);

          const x = 110 - Math.trunc(Vga.textWidth(text, small) / 2);

          v.outTextAdjust(x + Math.abs((Math.trunc(y / 18) % 4) - 2) - 1, y - 1, text, color, -8, small, tiny, false);
          v.outTextAdjust(x, y, text, color, -2, small, tiny, false);
        }
      }

      y += 20;
    }

    v.fillRectangleXY(0, 0, 319, 10, 0);
    v.fillRectangleXY(0, 190, 319, 199, 0);

    if (currentpic === extraShapes.length - 1) v.outTextAdjust(5, 180, g.miscText[54], 2, -2, small, tiny, false); // levels-in-episode

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

    v.showVGA();

    if (await v.waitUntilGetInputOrElapsed()) break;
  }

  await v.fadeBlack(10);
}

/**
 * JE_nextEpisode's title for the next episode (mainint.c L992-1000): its name, miscText[4] under
 * it, faded in on palette 6, until a key is pressed.
 */
async function showNextEpisode(v: Vga, files: TyrianFiles): Promise<void> {
  const small = fonts()[SMALL_FONT_SHAPES];
  const name = texts(files).episodeName[g.episodeNum] ?? "";

  v.clr256();
  const colors = paletteRgb(g.res.palettes[6 - 1]);

  v.dString(Vga.fontCenter(name, small), 130, name, small);
  v.dString(Vga.fontCenter(g.miscText[5 - 1], small), 185, g.miscText[5 - 1], small);

  v.showVGA();
  await v.fadePalette(colors, 15);

  await v.waitUntilGetInput();
}

/**
 * After the last episode, the next Super Arcade ship (tyrian2.c L2603-2645): its name, picture
 * and the code to type at the title screen, on picture 1's palette.
 */
async function showSuperArcadeCode(v: Vga, files: TyrianFiles): Promise<void> {
  const font = fonts()[FONT_SHAPES];
  const small = fonts()[SMALL_FONT_SHAPES];
  const { superShips, specialName } = texts(files);
  const next = SANextShip[g.superArcadeMode];

  // JE_loadPic(VGAScreen, 1, false): colors becomes picture 1's palette; the picture is cleared.
  const colors = paletteRgb(g.res.palettes[pcxpal[1 - 1]]);
  v.clr256();

  if (next === SA_ENGAGE) {
    let buffer = `${g.miscTextB[4]} ${g.pName[0]}`;
    v.dString(Vga.fontCenter(buffer, font), 100, buffer, font);

    buffer = `Or play... ${specialName[7]}`;
    v.dString(80, 180, buffer, small);
  } else {
    v.dString(Vga.fontCenter(superShips[0], font), 30, superShips[0], font);
    v.dString(Vga.fontCenter(superShips[next], small), 100, superShips[next], small);
  }

  if (next < SA_NORTSHIPZ) v.blitSprite2x2(148, 70, g.res.spriteSheet9.data, g.res.items.ships[SAShip[next - 1]].shipGraphic);
  // else if (next == SA_NORTSHIPZ) trentWin = true: done by the sim.

  const buffer = `Type ${specialName[next - 1]} at Title`;
  v.dString(Vga.fontCenter(buffer, small), 160, buffer, small);
  v.showVGA();

  await v.fadePalette(colors, 50);

  await v.waitUntilGetInput();
}
