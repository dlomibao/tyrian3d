// Sequential binary reader over a byte buffer, mirroring OpenTyrian's fileRead* helpers
// (src/file.h). Values are little-endian unless the method name says otherwise.
// Reading past the end throws, where OpenTyrian sets file.error and exits.

export type Bytes = ArrayBuffer | Uint8Array;

export function toBytes(data: Bytes): Uint8Array {
  return data instanceof Uint8Array ? data : new Uint8Array(data);
}

export class BinaryReader {
  readonly bytes: Uint8Array;
  private readonly view: DataView;
  /** Current byte offset (fileGetPosition / fileSetPosition). */
  pos: number;

  constructor(data: Bytes, pos = 0) {
    this.bytes = toBytes(data);
    this.view = new DataView(this.bytes.buffer, this.bytes.byteOffset, this.bytes.byteLength);
    this.pos = pos;
  }

  get length(): number {
    return this.bytes.length;
  }

  get remaining(): number {
    return this.bytes.length - this.pos;
  }

  seek(pos: number): this {
    if (pos < 0 || pos > this.bytes.length) {
      throw new RangeError(`seek to ${pos} outside 0..${this.bytes.length}`);
    }
    this.pos = pos;
    return this;
  }

  private take(n: number): number {
    const at = this.pos;
    if (n < 0 || at + n > this.bytes.length) {
      throw new RangeError(`read of ${n} bytes at ${at} past end (${this.bytes.length})`);
    }
    this.pos = at + n;
    return at;
  }

  u8(): number {
    return this.view.getUint8(this.take(1));
  }
  s8(): number {
    return this.view.getInt8(this.take(1));
  }
  u16(): number {
    return this.view.getUint16(this.take(2), true);
  }
  s16(): number {
    return this.view.getInt16(this.take(2), true);
  }
  u16be(): number {
    return this.view.getUint16(this.take(2), false);
  }
  u32(): number {
    return this.view.getUint32(this.take(4), true);
  }
  s32(): number {
    return this.view.getInt32(this.take(4), true);
  }
  /** fileReadBool: any non-zero byte is true. */
  bool(): boolean {
    return this.u8() !== 0;
  }

  /** A copy of the next n bytes. */
  bytesCopy(n: number): Uint8Array {
    const at = this.take(n);
    return this.bytes.slice(at, at + n);
  }

  u8Array(n: number): number[] {
    return Array.from({ length: n }, () => this.u8());
  }
  s8Array(n: number): number[] {
    return Array.from({ length: n }, () => this.s8());
  }
  u16Array(n: number): number[] {
    return Array.from({ length: n }, () => this.u16());
  }

  /**
   * Turbo Pascal `string[maxLen]`: a length byte followed by maxLen bytes of storage.
   * The length is clamped to maxLen like OpenTyrian's `name[MIN(nameLen, 30)] = '\0'`.
   */
  pascalString(maxLen: number): string {
    const len = Math.min(this.u8(), maxLen);
    const at = this.take(maxLen);
    return latin1(this.bytes.subarray(at, at + len));
  }
}

/** Bytes to a string, one char per byte (the data is DOS code page 437; text is ASCII). */
export function latin1(bytes: Uint8Array): string {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return s;
}
