// tyrian.pic, the game's full-screen pictures, and an opt-in dump of them for the new artwork
// (assets/art/README.md):
//
//   PICTURES_OUT=reference/pictures npm run pictures
//
// writes reference/pictures/pic-NN.png (320x200, in each picture's pcxpal palette) and
// reference/pictures/uses.txt, every episode script line that shows a picture (]P ]U ]V ]R).
// The output is derived from the game data, so it stays out of git (reference/ is ignored).
// Without PICTURES_OUT only the decode checks run.
import { describe, expect, test } from "vitest";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { crc32, deflateSync } from "node:zlib";
import { parseEpisodeScript, parsePalettes, vga6To8 } from "../../src/data";
import { hasData, readData } from "../data/dataDir";

const OUT = process.env.PICTURES_OUT ?? "";

/** PCX_NUM (pcxmast.h): pictures in tyrian.pic. */
const PCX_NUM = 13;
/** pcxpal (pcxmast.c): palette index for each JE_loadPic picture, [1..PCX_NUM]. */
const pcxpal = [0, 7, 5, 8, 10, 5, 18, 19, 19, 20, 21, 22, 5] as const;

/**
 * JE_loadPic (picload.c): picture `id` (1-based) as 320x200 palette indices. The file starts
 * with a u16 count and a u32 offset per picture; each picture runs to the next offset (the last
 * to the end of the file) and is PCX run-length coded: a byte with both top bits set is a run of
 * (b & 0x3F) copies of the next byte, any other byte is itself.
 */
export function JE_loadPic(file: Uint8Array, id: number): { pixels: Uint8Array; consumed: number; size: number } {
  const view = new DataView(file.buffer, file.byteOffset, file.byteLength);
  const count = view.getUint16(0, true);
  const pcxpos = (i: number) => (i < count ? view.getUint32(2 + i * 4, true) : file.length);
  const position = pcxpos(id - 1), endPosition = pcxpos(id);
  const size = endPosition > position ? endPosition - position : 0;
  const image = new Uint8Array(320 * 200);
  let r = position, w = 0;
  // while (!reader.error && writer.size > 0): a run past the end is clipped (memWriteFill).
  while (r < position + size && w < image.length) {
    const b = file[r++];
    if ((b & 0xc0) === 0xc0) {
      const value = file[r++];
      const n = Math.min(b & 0x3f, image.length - w);
      image.fill(value, w, w + n);
      w += n;
    } else image[w++] = b;
  }
  return { pixels: image, consumed: r - position, size };
}

function writePng(path: string, width: number, height: number, rgb: Uint8Array): void {
  const raw = Buffer.alloc((width * 3 + 1) * height);
  for (let y = 0; y < height; y++) raw.set(rgb.subarray(y * width * 3, (y + 1) * width * 3), y * (width * 3 + 1) + 1);
  const chunk = (type: string, data: Buffer) => {
    const len = Buffer.alloc(4);
    len.writeUInt32BE(data.length);
    const td = Buffer.concat([Buffer.from(type), data]);
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(crc32(td));
    return Buffer.concat([len, td, crc]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr.set([8, 2, 0, 0, 0], 8);
  writeFileSync(path, Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr), chunk("IDAT", deflateSync(raw)), chunk("IEND", Buffer.alloc(0)),
  ]));
}

describe.skipIf(!hasData("tyrian.pic", "palette.dat"))("tyrian.pic", () => {
  test("holds PCX_NUM pictures, each decoding to a full 320x200 screen", () => {
    const file = readData("tyrian.pic");
    expect(new DataView(file.buffer, file.byteOffset).getUint16(0, true)).toBe(PCX_NUM);
    for (let id = 1; id <= PCX_NUM; id++) {
      const pic = JE_loadPic(file, id);
      // Each picture's data is one screen, at most a byte of padding left over.
      expect(pic.size - pic.consumed, `picture ${id}`).toBeGreaterThanOrEqual(0);
      expect(pic.size - pic.consumed, `picture ${id}`).toBeLessThanOrEqual(1);
    }
  });

  test.skipIf(!OUT || !hasData("levels1.dat"))("writes every picture and its uses", () => {
    mkdirSync(OUT, { recursive: true });
    const file = readData("tyrian.pic");
    const palettes = parsePalettes(readData("palette.dat"));
    for (let id = 1; id <= PCX_NUM; id++) {
      const { pixels } = JE_loadPic(file, id);
      const pal = palettes[pcxpal[id - 1]];
      const rgb = new Uint8Array(320 * 200 * 3);
      for (let i = 0; i < pixels.length; i++)
        for (let c = 0; c < 3; c++) rgb[i * 3 + c] = vga6To8(pal[pixels[i] * 3 + c]);
      writePng(join(OUT, `pic-${String(id).padStart(2, "0")}.png`), 320, 200, rgb);
    }
    const uses: string[] = [];
    for (let ep = 1; ep <= 4; ep++) {
      if (!hasData(`levels${ep}.dat`)) continue;
      const script = parseEpisodeScript(readData(`levels${ep}.dat`));
      for (const sec of script.sections)
        for (const l of sec.lines) if (/^\][PUVR]/.test(l)) uses.push(`ep${ep} sec${sec.number}: ${l}`);
    }
    writeFileSync(join(OUT, "uses.txt"), uses.join("\n") + "\n");
  });
});
