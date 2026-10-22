// Tyrian's text obfuscation. Port of decrypt_string / readEncryptedString (OpenTyrian
// src/helptext.c), used by levels*.dat, tyrian.hdt's help text, tyrian.cdt and cubetxt*.dat.

import { type BinaryReader, latin1 } from "./reader";

const CRYPT_KEY = [204, 129, 63, 255, 71, 19, 25, 62, 1, 99];

/** decrypt_string: XOR with the key, then with the previous (still encrypted) byte, back to front. */
export function decryptString(encrypted: Uint8Array): Uint8Array {
  const s = encrypted.slice();
  for (let i = s.length - 1; i >= 0; i--) {
    s[i] ^= CRYPT_KEY[i % CRYPT_KEY.length];
    if (i > 0) s[i] ^= s[i - 1];
  }
  return s;
}

/** readEncryptedString: a length byte, then that many encrypted bytes. */
export function readEncryptedString(r: BinaryReader): string {
  const len = r.u8();
  return latin1(decryptString(r.bytesCopy(len)));
}
