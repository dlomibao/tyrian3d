// tyrian.cdt: the credits JE_playCredits scrolls (OpenTyrian src/mainint.c L2347-2380). It's 131
// encrypted strings; the first character of each picks the colour bank ('A' + bank), '.' or an
// empty string is a blank line.

import { readEncryptedString } from "./crypt";
import { BinaryReader, type Bytes } from "./reader";

/** credstr[131][65 + 1] */
export const CREDITS_LINES = 131;

/** Read the credits' lines (each at most 65 characters, as the C's buffers keep). */
export function parseCredits(data: Bytes): string[] {
  const r = new BinaryReader(data);
  const lines: string[] = [];
  for (let i = 0; i < CREDITS_LINES; ++i) lines.push(r.remaining > 0 ? readEncryptedString(r).slice(0, 65) : "");
  return lines;
}
