// tyrend.anm: a Deluxe Paint Animation ("LPF ANIM") file, the one animation Tyrian plays (episode 3's
// ending, `]A[` in levels3.dat). Ported from OpenTyrian src/animlib.c (playAnim and its readers).
//
// Layout: a 256-byte header (u16 pageCount at 6, u32 recordCount at 8), a 256-colour BGRx palette
// (1024 bytes), 256 page descriptors (u16 firstRecord, recordCount, recordsSize), then 64 KB pages
// from 0xB00. A page holds a run of records (frames) in order: an 8-byte header, a u16 size per
// record, then the records. Each record is a 4-byte header and a run/skip/dump delta against the
// previous frame of a 320x200 image (decodeRunSkipDump). The pages themselves aren't in order.

import { toBytes, type Bytes } from "./reader";

export const ANIM_WIDTH = 320;
export const ANIM_HEIGHT = 200;

export interface Anim {
  /** fileHeader.pageCount */
  pageCount: number;
  /** fileHeader.recordCount: the frames, the last of which playAnim never shows. */
  recordCount: number;
  /** 256 colours as 8-bit RGB triples, colour 0 forced to black as playAnim does. */
  palette: Uint8Array;
  pageDescriptors: { firstRecord: number; recordCount: number; recordsSize: number }[];
  data: Uint8Array;
}

/** memreader.c's MemReader: reads past the end set `error` and return 0. */
class MemReader {
  constructor(
    public data: Uint8Array,
    public pos: number,
    public size: number,
    public error = false,
  ) {}

  /** memReaderSplit */
  split(size: number): MemReader {
    this.error ||= this.size < size;
    if (this.error) return new MemReader(this.data, 0, 0, true);
    const r = new MemReader(this.data, this.pos, size);
    this.pos += size;
    this.size -= size;
    return r;
  }

  /** memReaderSkip */
  skip(size: number): void {
    this.error ||= this.size < size;
    if (this.error) return;
    this.pos += size;
    this.size -= size;
  }

  /** memReadU8 */
  u8(): number {
    this.error ||= this.size < 1;
    if (this.error) return 0;
    this.size -= 1;
    return this.data[this.pos++];
  }

  /** memReadU16 */
  u16(): number {
    this.error ||= this.size < 2;
    if (this.error) return 0;
    const v = this.data[this.pos] | (this.data[this.pos + 1] << 8);
    this.pos += 2;
    this.size -= 2;
    return v;
  }
}

/** memwriter.c's MemWriter over the 320x200 image. */
class MemWriter {
  pos = 0;
  error = false;
  constructor(public data: Uint8Array) {}

  get size(): number {
    return this.data.length - this.pos;
  }

  /** memWriterSkip */
  skip(size: number): void {
    this.error ||= this.size < size;
    if (this.error) return;
    this.pos += size;
  }

  /** memWriteFill */
  fill(value: number, size: number): void {
    this.error ||= this.size < size;
    if (this.error) return;
    this.data.fill(value, this.pos, this.pos + size);
    this.pos += size;
  }

  /** memWriteRead */
  read(reader: MemReader, size: number): void {
    this.error ||= this.size < size;
    reader.error ||= reader.size < size;
    this.error ||= reader.error;
    reader.error = this.error;
    if (this.error) return;
    this.data.set(reader.data.subarray(reader.pos, reader.pos + size), this.pos);
    this.pos += size;
    reader.pos += size;
    reader.size -= size;
  }
}

/** readFileHeader, readPalette and readPageDescriptors (animlib.c L46-98). */
export function parseAnim(bytes: Bytes): Anim {
  const data = toBytes(bytes);
  if (data.length < 0xb00) throw new Error("tyrend.anm: too short");

  const header = new MemReader(data, 0, 256);
  header.skip(6);
  const pageCount = header.u16();
  const recordCount = header.u16() | (header.u16() << 16); // memReadU32

  const palette = new Uint8Array(256 * 3);
  const pal = new MemReader(data, 256, 1024);
  for (let i = 0; i < 256; ++i) {
    palette[i * 3 + 2] = pal.u8(); // b
    palette[i * 3 + 1] = pal.u8(); // g
    palette[i * 3] = pal.u8(); // r
    pal.u8();
  }
  // playAnim: palette[0] is black.
  palette[0] = palette[1] = palette[2] = 0;

  const desc = new MemReader(data, 256 + 1024, 6 * 256);
  const pageDescriptors = Array.from({ length: 256 }, () => ({ firstRecord: desc.u16(), recordCount: desc.u16(), recordsSize: desc.u16() }));

  return { pageCount, recordCount, palette, pageDescriptors, data };
}

/** decodeRunSkipDump (animlib.c L100-150): apply one record's delta to the image. */
function decodeRunSkipDump(writer: MemWriter, reader: MemReader): void {
  while (!reader.error) {
    const opCode = reader.u8();

    if (opCode === 0) {
      // 00: Short run
      const size = reader.u8();
      const value = reader.u8();
      writer.fill(value, size);
    } else if (opCode > 0x80) {
      // 81..FF: Short skip
      writer.skip(opCode - 0x80);
    } else if (opCode < 0x80) {
      // 01..7F: Short dump
      writer.read(reader, opCode);
    } else {
      // 80: Long op
      const opCode = reader.u16();

      if (opCode === 0) {
        // 0000: Stop
        return;
      } else if (opCode >= 0xc000) {
        // C000..FFFF: Long run
        const size = opCode - 0xc000;
        const value = reader.u8();
        writer.fill(value, size);
      } else if (opCode < 0x8000) {
        // 0001..7FFF: Long skip
        writer.skip(opCode);
      } else {
        // 8000..BFFF: Long dump
        writer.read(reader, opCode - 0x8000);
      }
    }
  }
}

/**
 * playAnim's frame loop (animlib.c L152-275) without the timing: yields the 320x200 image (palette
 * indices) after each step of `record`, where the C shows it and then waits `speed` frames
 * (setFrameCount(speed), waitUntilGetInputOrElapsed). The same buffer is yielded each time.
 */
export function* animFrames(anim: Anim, startingFrame = 0): Generator<Uint8Array, void, void> {
  const { data, pageDescriptors } = anim;
  const dataSize = 1 << 16;

  let firstRecord = 0;
  let recordCount = 0;

  let recordSizesReader = new MemReader(data, 0, 0);
  let recordsReader = new MemReader(data, 0, 0);

  const image = new Uint8Array(ANIM_WIDTH * ANIM_HEIGHT);

  for (let record = startingFrame; record < anim.recordCount - 1; ++record) {
    if (record < firstRecord || record - firstRecord >= recordCount) {
      // The record is not in the page that is loaded.
      // Find the page that contains the record and load it.

      for (let i = 0; i < anim.pageCount; ++i) {
        const pageDescriptor = pageDescriptors[i];
        firstRecord = pageDescriptor.firstRecord;
        recordCount = pageDescriptor.recordCount;
        const recordsSize = pageDescriptor.recordsSize;

        if (record >= firstRecord && record - firstRecord < recordCount) {
          const pos = 0xb00 + (i << 16); // fileSetPosition

          const pageSize = 8 + 2 * recordCount + recordsSize;
          const size = Math.max(0, Math.min(pageSize, dataSize, data.length - pos)); // fileReadAtMost

          const pageReader = new MemReader(data, pos, size, size !== pageSize);

          // Skip the page header.
          pageReader.skip(8);

          // The page header is followed by the record sizes and the records.
          recordSizesReader = pageReader.split(2 * recordCount);
          recordsReader = pageReader;
          break;
        }
      }
    }

    while (record >= firstRecord && recordCount > 0) {
      firstRecord += 1;
      recordCount -= 1;

      const recordSize = recordSizesReader.u16();

      if (recordSizesReader.error) continue;

      const recordReader = recordsReader.split(recordSize);

      // Skip record if unneeded.
      if (record > firstRecord) continue;

      // Read record header.
      recordReader.u8(); // Bitmap ID (assumed 'B')
      recordReader.u8(); // Flags (assumed 0)
      recordReader.u16(); // Body Type (assumed 1)

      // Decode record body to image.
      decodeRunSkipDump(new MemWriter(image), recordReader);
    }

    yield image; // JE_showVGA, then setFrameCount(speed) has elapsed
  }
}
