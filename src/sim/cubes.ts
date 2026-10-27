// Data cubes: the story messages a level's cube pickups unlock, read in the item screen.
//
// How the C wires them up:
//   - The episode script's `]?[ n a b c d` (JE_loadMap, tyrian2.c L2391-2399, in tyrian2.ts) names
//     the cubes the level just played holds, in pickup order, into cubeList[4], and lowers cubeMax
//     to n; `]![` and `]+[` set or add to cubeMax for cubes the story hands over.
//   - JE_main sets cubeMax = 0 when a level starts (tyrian2.c L839-840), and picking up a cube
//     (an enemy with evalue 1: tyrian2.c L1570-1573, mainint.c L4711-4716) adds one. So the item
//     screen lists the cubes found in the last level only: cubeList[0 .. cubeMax-1].
//   - lastCubeMax = cubeMax when JE_loadMap starts (tyrian2.c L2313) is what saves keep (config.c
//     L416, L495-496; run.ts's LAST LEVEL backup), so a reloaded game shows the same cubes. The
//     C draws nothing from it.
//   - JE_itemScreen calls load_cubes, which reads each listed cube from cubetxt<episode>.dat
//     (episodes.c L255) and word-wraps its text to the reader's 150-pixel column.
//
// Ported here: cube_struct, cube[4], load_cubes/load_cube (game_menu.c L69-76, L1727-1846), and
// the reader's scrolling (yLoc/yChg in JE_itemScreen's inner loop, L811-866 and L967-1013, and
// the Home/End keys, L1337-1345). The menus themselves are in game_menu.ts; src/app/dataCubes.ts
// draws them.

import { BinaryReader, decryptString } from "../data";
import { u16 } from "./cint";
import { JE_textWidth, TINY_FONT } from "./fonthand";
import { requireFile, type TyrianFiles } from "./resources";
import { g } from "./state";

/** game_menu.c cube_struct: title[81], header[13], face_sprite, text[90][36], last_line. */
export interface cube_struct {
  title: string;
  header: string;
  /** Index into FACE_SHAPES, or -1 for no face. */
  face_sprite: number;
  /** The word-wrapped text, 90 lines (empty lines are paragraph breaks). */
  text: string[];
  /** The number of lines up to the last one with text. */
  last_line: number;
}

const TEXT_LINES = 90;
const newCube = (): cube_struct => ({ title: "", header: "", face_sprite: -1, text: new Array<string>(TEXT_LINES).fill(""), last_line: 0 });

/** static struct cube_struct cube[4] (one slot per cubeList entry). */
export const cube: cube_struct[] = Array.from({ length: 4 }, newCube);

/** sizeof(*cube->text) - 1 and the reader's column width in TINY_FONT pixels (game_menu.c L113-114). */
const cube_line_chars = 35;
const cube_line_width = 150;

/** pcxmast.c facepal[12]: the palette (index into palettes) each face is drawn with. */
export const facepal = [1, 2, 3, 4, 6, 9, 11, 12, 16, 13, 14, 15];

/** episodes.c cubeFilename (FKA Episodes.cubeFile), set by JE_initEpisode. */
export function cubeFilename(episodeNum = g.episodeNum): string {
  return `cubetxt${episodeNum}.dat`;
}

/**
 * The C's File plus a char buf[256] that readEncryptedString writes into: load_cube parses the
 * face number from buf[4] onwards whatever the cube's '*' line holds, so a short line such as
 * "*03" leaves bytes from an earlier, longer line there. This keeps the buffer as the C does.
 */
class CubeFile {
  private r: BinaryReader;
  /** file.error: a read went past the end. */
  error = false;

  constructor(data: Uint8Array) {
    this.r = new BinaryReader(data);
  }

  /** readEncryptedString (helptext.c L89-106) into dst, keeping at most dst.length - 1 bytes. */
  readEncryptedString(dst: Uint8Array): void {
    if (this.r.remaining < 1) {
      this.error = true;
      return;
    }
    const len = this.r.u8();
    if (this.r.remaining < len) {
      this.error = true;
      return;
    }
    const buffer = decryptString(this.r.bytesCopy(len));
    const n = Math.min(len, dst.length - 1);
    dst.set(buffer.subarray(0, n));
    dst[n] = 0;
  }
}

/** A NUL-terminated char array (from offset `at`) as a string, one char per byte. */
function cstr(buf: Uint8Array, at = 0): string {
  let s = "";
  for (let i = at; i < buf.length && buf[i] !== 0; i++) s += String.fromCharCode(buf[i]);
  return s;
}

/** str_pop_int's value (mainint.c L2696-2716): strtol(str, &end, 10), 0 when there are no digits. */
function strtol(s: string): number {
  let i = 0;
  while (i < s.length && (s[i] === " " || (s.charCodeAt(i) >= 9 && s.charCodeAt(i) <= 13))) i++;
  let sign = 1;
  if (s[i] === "+" || s[i] === "-") sign = s[i++] === "-" ? -1 : 1;
  let v = 0;
  const start = i;
  while (i < s.length && s[i] >= "0" && s[i] <= "9") v = v * 10 + (s.charCodeAt(i++) - 48);
  return i === start ? 0 : sign * v;
}

/** load_cubes (game_menu.c L1727-1737): load the cubes cubeList names into cube[0 .. cubeMax-1]. */
export function load_cubes(files: TyrianFiles): void {
  if (g.cubeMax > cube.length) throw new Error(`cubeMax ${g.cubeMax} > ${cube.length}`); // assert(cubeMax <= COUNTOF(cube))
  if (g.cubeMax === 0) return;

  const data = requireFile(files, cubeFilename());
  for (let cube_slot = 0; cube_slot < g.cubeMax; ++cube_slot) {
    cube[cube_slot].text.fill("");

    load_cube(data, cube_slot, g.cubeList[cube_slot]);
  }
}

/**
 * load_cube (game_menu.c L1739-1846): read cube number cube_index (1-based: the text after the
 * cube_index-th '*' line) into cube[cube_slot], word-wrapping its text the way the reader shows
 * it. As in the C, last_line is only set when a line gets text, so a cube without any keeps the
 * slot's previous value. `data` is cubetxt<episode>.dat.
 */
export function load_cube(data: Uint8Array, cube_slot: number, cube_index: number): boolean {
  const file = new CubeFile(data);
  const c = cube[cube_slot];

  const buf = new Uint8Array(256);

  // seek to the cube
  while (cube_index > 0) {
    file.readEncryptedString(buf);

    if (buf[0] === 0x2a /* '*' */ || file.error) --cube_index;
  }

  c.face_sprite = strtol(cstr(buf, 4));
  --c.face_sprite;

  const title = new Uint8Array(81);
  const header = new Uint8Array(13);
  file.readEncryptedString(title);
  file.readEncryptedString(header);
  c.title = cstr(title);
  c.header = cstr(header);

  let line = 0,
    line_chars = 0,
    line_width = 0;

  // for each line of decrypted text, split the line into words
  // and add them individually to the lines of wrapped text
  for (;;) {
    file.readEncryptedString(buf);

    // end of data
    if (buf[0] === 0x2a /* '*' */ || file.error) break;

    const s = cstr(buf);

    // new paragraph
    if (s.length === 0) {
      if (line_chars === 0) line += 4; // subsequent new paragaphs indicate 4-line break
      else ++line;
      line_chars = 0;
      line_width = 0;

      continue;
    }

    for (const word of s.split(" ")) {
      const word_chars = word.length,
        word_width = JE_textWidth(word, TINY_FONT);

      // word won't fit; no can do
      if (word_chars > cube_line_chars || word_width > cube_line_width) break;

      let prepend_space = true;

      line_chars += word_chars + (prepend_space ? 1 : 0);
      line_width += word_width + (prepend_space ? 6 : 0);

      // word won't fit on current line; use next
      if (line_chars > cube_line_chars || line_width > cube_line_width) {
        ++line;
        line_chars = word_chars;
        line_width = word_width;

        prepend_space = false;
      }

      // append word
      if (line < TEXT_LINES) {
        if (prepend_space) c.text[line] += " ";
        c.text[line] += word;

        // track last line with text
        c.last_line = line + 1;
      }
    }
  }

  if (file.error) throw new Error(`Failed to read from file '${cubeFilename()}': cube ${cube_index} past the end`); // logFatal

  return true;
}

/** How many cubes a cubetxt file holds: its '*' lines, less the one that closes the last cube. */
export function cubeCount(data: Uint8Array): number {
  const file = new CubeFile(data);
  const buf = new Uint8Array(256);
  let stars = 0;
  for (;;) {
    file.readEncryptedString(buf);
    if (file.error) break;
    if (buf[0] === 0x2a) ++stars;
  }
  return stars - 1;
}

// --- The reader (MENU_DATA_CUBE_SUB): scrolling ---

/**
 * JE_itemScreen's reader statics: yLoc, the scroll position in pixels (12 per line; JE_word), and
 * yChg, the pixels it moves per frame (JE_shortint). The C shows 9 lines from yLoc / 12.
 */
export const cubeReader = { yLoc: 0, yChg: 0 };

/** Lines the reader shows at once (y 49..156 at 12 pixels a line), and pixels per line. */
export const CUBE_READER_LINES = 9;
export const CUBE_LINE_HEIGHT = 12;

/** What the reader's input does in a frame (the C reads keysactive, so held keys repeat). */
export interface CubeReaderInput {
  up?: boolean;
  down?: boolean;
  pageUp?: boolean;
  pageDown?: boolean;
  /** A new mouse click on the upper / lower half of the text (MOUSE_POINTER_UP / _DOWN). */
  clickUp?: boolean;
  clickDown?: boolean;
}

/** JE_menuFunction opening the reader (game_menu.c L2783-2788). */
export function cubeReader_open(): void {
  cubeReader.yLoc = 0;
  cubeReader.yChg = 0;
}

/**
 * One frame of the reader (game_menu.c L811-866 then L967-1013): move by yChg, stop once on a
 * line boundary, then read this frame's input. A tap scrolls one whole line a pixel a frame; Page
 * Up/Down two pixels a frame.
 */
export function cubeReader_frame(c: cube_struct, input: CubeReaderInput): void {
  const r = cubeReader;
  if (r.yLoc + r.yChg < 0) {
    r.yChg = 0;
    r.yLoc = 0;
  }

  r.yLoc = u16(r.yLoc + r.yChg);
  const temp2 = r.yLoc % CUBE_LINE_HEIGHT;

  if (temp2 === 0) r.yChg = 0;

  if (input.clickUp) r.yChg = -1;
  else if (input.clickDown) r.yChg = 1;

  if (input.pageUp) r.yChg = -2;
  if (input.pageDown) r.yChg = 2;

  if (input.up) r.yChg = -1;
  if (input.down) r.yChg = 1;

  if (r.yChg < 0 && r.yLoc === 0) r.yChg = 0;
  if (r.yChg > 0 && Math.trunc(r.yLoc / CUBE_LINE_HEIGHT) > c.last_line - 10) r.yChg = 0;
}

/**
 * Home and End (game_menu.c L1337-1345). The C's End sets yLoc = (last_line - 9) * 12, which for a
 * cube of 9 lines or fewer wraps the JE_word and scrolls the text out of view; here it stays at 0.
 */
export function cubeReader_home(): void {
  cubeReader.yLoc = 0;
}
export function cubeReader_end(c: cube_struct): void {
  cubeReader.yLoc = Math.max(0, (c.last_line - 9) * CUBE_LINE_HEIGHT);
}

/** The reader's "Read: n%" (game_menu.c L847-852). */
export function cubeReader_percent(c: cube_struct): number {
  return c.last_line <= 9 ? 100 : Math.trunc((cubeReader.yLoc * 100) / ((c.last_line - 9) * CUBE_LINE_HEIGHT));
}
