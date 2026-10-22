// The part of JE_loadHelpText (OpenTyrian src/helptext.c L165-205) the gameplay needs: miscText
// and miscTextB, the strings JE_drawTextWindow shows ("Weapon Power-Up!", "You picked up ...").

import { BinaryReader, readEncryptedString } from "../data";
import { g } from "./state";

/** helpTxt[39] and pName[21] precede miscText in tyrian.hdt (helptext.c L49-50). */
const HELP_TXT_COUNT = 39;
const PNAME_COUNT = 21;
const HELPTEXT_MISCTEXT_COUNT = 68;
const HELPTEXT_MISCTEXTB_COUNT = 5;

export interface HelpText {
  miscText: string[];
  miscTextB: string[];
}

/** Read miscText and miscTextB from tyrian.hdt (each section is framed by a skipped string). */
export function parseHelpText(hdt: Uint8Array): HelpText {
  const r = new BinaryReader(hdt);
  r.u32(); // Episode 1-3 item data position

  const section = (count: number): string[] => {
    readEncryptedString(r);
    const out = Array.from({ length: count }, () => readEncryptedString(r));
    readEncryptedString(r);
    return out;
  };

  section(HELP_TXT_COUNT); // Online Help
  section(PNAME_COUNT); // Planet names
  const miscText = section(HELPTEXT_MISCTEXT_COUNT); // Miscellaneous text
  const miscTextB = section(HELPTEXT_MISCTEXTB_COUNT); // Little Miscellaneous text
  return { miscText, miscTextB };
}

/** Load the strings into g.miscText / g.miscTextB. */
export function loadHelpText(hdt: Uint8Array): void {
  const t = parseHelpText(hdt);
  g.miscText = t.miscText;
  g.miscTextB = t.miscTextB;
}
