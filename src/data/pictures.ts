// tyrian.pic and tshp2.pcx: the full-screen pictures the episode script shows between levels
// (and the in-game HUD frame). Ports of JE_loadPic (OpenTyrian src/picload.c) and JE_loadPCX
// (src/pcxload.c).
//
// - tyrian.pic: u16 count (PCX_NUM, 13), then count u32 offsets; picture N (1-based) is the PCX
//   run-length data from offset N-1 to offset N (the file's end for the last). There's no PCX
//   header and no palette: JE_loadPic takes palette pcxpal[N-1] from palette.dat.
// - tshp2.pcx: a real PCX file, 320x200, whose data starts after the 128-byte header and whose
//   palette is the 768 bytes at the end. JE_loadPCX copies those bytes straight into `colors`, so
//   they're used as 8-bit values (palette.dat's are 6-bit).

import { BinaryReader, toBytes, type Bytes } from "./reader";

/** pcxmast.h PCX_NUM: pictures in tyrian.pic. */
export const PCX_NUM = 13;

export const PICTURE_W = 320;
export const PICTURE_H = 200;

/** A decoded 320x200 picture: one palette index per pixel, row by row. */
export type PictureIndices = Uint8Array;

/** pcxpos[PCX_NUM + 1]: where each picture's data starts in tyrian.pic, then the file length. */
export function picturePositions(data: Bytes): number[] {
  const bytes = toBytes(data);
  const r = new BinaryReader(bytes);
  const count = r.u16();
  const pcxpos: number[] = [];
  for (let i = 0; i < count && i < PCX_NUM + 1; ++i) pcxpos.push(r.u32());
  for (let i = count; i < PCX_NUM + 1; ++i) pcxpos.push(bytes.length);
  return pcxpos;
}

/**
 * The PCX run-length decoder JE_loadPic and JE_loadPCX share: a byte with its top two bits set
 * repeats the next byte (b & 0x3F) times, any other byte is one pixel. Like the C's MemReader and
 * MemWriter, a run that doesn't fit is dropped (and so is everything after it), and reading past
 * the end stops the loop; the image starts zeroed (calloc).
 */
export function decodePcxRle(data: Uint8Array): PictureIndices {
  const image = new Uint8Array(PICTURE_W * PICTURE_H);
  let readPos = 0;
  let readError = false;
  let writePos = 0;
  let writeError = false;
  const memReadU8 = (): number => {
    readError ||= readPos >= data.length;
    return readError ? 0 : data[readPos++];
  };
  const memWriteFill = (value: number, size: number): void => {
    writeError ||= image.length - writePos < size;
    if (writeError) return;
    image.fill(value, writePos, writePos + size);
    writePos += size;
  };

  while (!readError && image.length - writePos > 0) {
    const b = memReadU8();
    if ((b & 0xc0) === 0xc0) {
      const size = b & 0x3f;
      const value = memReadU8();
      memWriteFill(value, size);
    } else {
      memWriteFill(b, 1); // memWriteU8
    }
  }
  return image;
}

/** JE_loadPic's pixels for picture `id` (1..PCX_NUM), or null where the C logs "does not exist". */
export function decodePicture(data: Bytes, id: number): PictureIndices | null {
  if (id < 1 || id > PCX_NUM) return null;
  const bytes = toBytes(data);
  const pcxpos = picturePositions(bytes);
  const position = pcxpos[id - 1];
  const endPosition = pcxpos[id];
  const size = endPosition > position ? endPosition - position : 0;
  return decodePcxRle(bytes.subarray(position, Math.min(bytes.length, position + size)));
}

/** JE_loadPCX("tshp2.pcx"): its pixels and its 8-bit palette (256 × r, g, b). */
export function decodePcxFile(data: Bytes): { pixels: PictureIndices; palette8: Uint8Array } | null {
  const bytes = toBytes(data);
  if (bytes.length < 128 + 3 * 256) return null; // "Failed to load file"
  const palette8 = bytes.slice(bytes.length - 3 * 256);
  const pixels = decodePcxRle(bytes.subarray(128, bytes.length - 3 * 256));
  return { pixels, palette8 };
}
