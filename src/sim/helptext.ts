// The parts of JE_loadHelpText (OpenTyrian src/helptext.c L165-385) the game uses: miscText and
// miscTextB, the strings JE_drawTextWindow shows ("Weapon Power-Up!", "You picked up ..."), and
// the item screen's planet names, menus, help lines and ship descriptions (parseMenuText).

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

/** Load the strings into g.miscText / g.miscTextB, and the item screen's texts (loadMenuText). */
export function loadHelpText(hdt: Uint8Array): void {
  const t = parseHelpText(hdt);
  g.miscText = t.miscText;
  g.miscTextB = t.miscTextB;
  loadMenuText(hdt);
}

/** The texts the item screen (game_menu.c) uses, from the rest of JE_loadHelpText (helptext.c L165-385). */
export interface MenuText {
  /** pName[21]: planet names, string[15]. */
  pName: string[];
  /** mainMenuHelp[34]: the help line under the menus, string[65]. */
  mainMenuHelp: string[];
  /** menuInt[0..14][..]: menu titles and choices, string[17]. Entry [m][0] is menu m's title. */
  menuInt: string[][];
  /** shipInfo[13][2]: the two "Ship Specs" paragraphs per ship, string[255]. */
  shipInfo: [string, string][];
  /** episode_name[6]: entry 0 is the menu title, 1-5 the episodes. */
  episodeName: string[];
  /** difficulty_name[7]: entry 0 is the menu title, then Wimp/Easy/Normal/Hard/... by difficulty level. */
  difficultyName: string[];
  /** difficultyNameB[11]: the high score table's difficulty column, by difficulty level (string[20]). */
  difficultyNameB: string[];
}

/** helptext.c menuInt_entries[MENU_MAX + 1]: how many strings each menuInt[m] reads (-1: none). */
const menuInt_entries = [-1, 7, 9, 8, -1, -1, 11, -1, -1, -1, 6, 4, 6, 7, 5];

/** JE_loadHelpText's read order after miscTextB (helptext.c L207-381), keeping what the item screen needs. */
export function parseMenuText(hdt: Uint8Array): MenuText {
  const r = new BinaryReader(hdt);
  r.u32(); // Episode 1-3 item data position

  // readEncryptedString(file, dst, size) keeps at most size - 1 characters.
  const section = (count: number, size = 256): string[] => {
    readEncryptedString(r);
    const out = Array.from({ length: count }, () => readEncryptedString(r).slice(0, size - 1));
    readEncryptedString(r);
    return out;
  };

  const menuInt: string[][] = Array.from({ length: menuInt_entries.length }, () => []);

  section(HELP_TXT_COUNT); /*Online Help*/
  const pName = section(PNAME_COUNT, 16); /*Planet names*/
  section(HELPTEXT_MISCTEXT_COUNT); /*Miscellaneous text*/
  section(HELPTEXT_MISCTEXTB_COUNT); /*Little Miscellaneous text*/
  menuInt[6] = section(menuInt_entries[6], 18); /*Key names*/
  section(7); /*Main Menu*/ // menuText
  section(9); /*Event text*/ // outputs
  section(6); /*Help topics*/ // topicName
  const mainMenuHelp = section(34, 66); /*Main Menu Help*/
  menuInt[1] = section(menuInt_entries[1], 18); /*Menu 1 - Main*/
  menuInt[2] = section(menuInt_entries[2], 18); /*Menu 2 - Items*/
  menuInt[3] = section(menuInt_entries[3], 18); /*Menu 3 - Options*/
  section(6); /*InGame Menu*/
  section(6); /*Detail Level*/
  section(5); /*Game speed text*/
  const episodeName = section(6, 31); // episode names (menus.c episode_name[6][31])
  const difficultyName = section(7, 21); // difficulty names (menus.c difficulty_name[7][21])
  section(5); // gameplay mode names
  menuInt[10] = section(menuInt_entries[10], 18); /*Menu 10 - 2Player Main*/
  section(3); /*Input Devices*/
  section(4); /*Network text*/
  menuInt[11] = section(menuInt_entries[11], 18); /*Menu 11 - 2Player Network*/
  const difficultyNameB = section(11, 21); /*HighScore Difficulty Names*/
  menuInt[12] = section(menuInt_entries[12], 18); /*Menu 12 - Network Options*/
  menuInt[13] = section(menuInt_entries[13], 18); /*Menu 13 - Joystick*/
  section(5); /*Joystick Button Assignments*/
  section(11); /*SuperShips - For Super Arcade Mode*/
  section(9); /*SuperShips - For Super Arcade Mode*/ // specialName
  section(25); /*Secret DESTRUCT game*/
  section(17); /*Secret DESTRUCT weapons*/
  section(5); /*Secret DESTRUCT modes*/

  /*NEW: Ship Info*/
  readEncryptedString(r);
  const shipInfo: [string, string][] = [];
  for (let i = 0; i < 13; ++i) shipInfo.push([readEncryptedString(r).slice(0, 255), readEncryptedString(r).slice(0, 255)]);
  readEncryptedString(r);

  /*Menu 12 - Network Options*/ // (menuInt[14]: the Super Tyrian menu; no closing string)
  readEncryptedString(r);
  menuInt[14] = Array.from({ length: menuInt_entries[14] }, () => readEncryptedString(r).slice(0, 17));

  return { pName, mainMenuHelp, menuInt, shipInfo, episodeName, difficultyName, difficultyNameB };
}

/** Load the item screen's texts into g.pName, g.mainMenuHelp, g.menuInt and g.shipInfo. */
export function loadMenuText(hdt: Uint8Array): void {
  const t = parseMenuText(hdt);
  g.pName = t.pName;
  g.mainMenuHelp = t.mainMenuHelp;
  g.menuInt = t.menuInt;
  g.shipInfo = t.shipInfo;
}
