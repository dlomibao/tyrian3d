// The on-screen character picker of the high score name entry (src/app/highScoresScreen.ts), for
// pads and touch screens, which can't type. OpenTyrian's JE_highScoreCheck (mainint.c L1921-2156)
// only reads typed characters, Backspace/Delete, Return and Escape (and the mouse on OK/CANCEL),
// so this is the remaster's: a grid of the characters the entry accepts, moved through with the
// d-pad and pressed with A or a tap. What a name may hold stays the C's (highScoreNameAccepts, at
// most 28 characters, added at the end and taken off the end). Pure, so it's tested without a
// browser.

import { HIGH_SCORE_NAME_MAX, highScoreNameAccepts } from "../sim/highscores";

/** Grid width: every row covers columns 0-9. */
export const PICKER_COLUMNS = 10;

export type PickerKey = { kind: "char"; char: string } | { kind: "set" } | { kind: "space" } | { kind: "delete" } | { kind: "ok" };

/** A key of the grid: `span` columns from `col`. */
export interface PickerCell {
  key: PickerKey;
  col: number;
  span: number;
}

/** The character sets the `set` key cycles through. */
export const PICKER_SETS = [
  { name: "ABC", rows: ["ABCDEFGHIJ", "KLMNOPQRST", "UVWXYZ.-'!", "0123456789"] },
  { name: "abc", rows: ["abcdefghij", "klmnopqrst", "uvwxyz.-'!", "0123456789"] },
  // The other characters the font has (fontMap), and a few of its CP437 letters.
  { name: "#+=", rows: ["!\"#$%'()*+", ",-./:;=?[\\", "]{|}äöüéñç", "0123456789"] },
] as const;

/** The grid of a set: its character rows, then [next set][space][delete][OK]. */
export function pickerRows(set: number): PickerCell[][] {
  const rows: PickerCell[][] = PICKER_SETS[set].rows.map((chars) => [...chars].map((char, col) => ({ key: { kind: "char", char }, col, span: 1 })));
  rows.push([
    { key: { kind: "set" }, col: 0, span: 3 },
    { key: { kind: "space" }, col: 3, span: 3 },
    { key: { kind: "delete" }, col: 6, span: 2 },
    { key: { kind: "ok" }, col: 8, span: 2 },
  ]);
  return rows;
}

/** Where the picker's focus is: the set shown, the row, and a column (0-9) that up/down keep. */
export interface PickerState {
  set: number;
  row: number;
  col: number;
}

/** The cell at the state's row covering its column. */
export function pickerCell(state: PickerState): PickerCell {
  const row = pickerRows(state.set)[state.row];
  return row.find((c) => state.col >= c.col && state.col < c.col + c.span) ?? row[0];
}

/**
 * Move the focus one key: left/right go to the neighbouring key of the row, up/down to the key of
 * the next row under the same column (so going down to the space bar and back up returns to the
 * same letter). Every direction wraps.
 */
export function pickerMove(state: PickerState, dir: "up" | "down" | "left" | "right"): PickerState {
  const rows = pickerRows(state.set);
  if (dir === "up" || dir === "down") {
    const row = (state.row + (dir === "down" ? 1 : -1) + rows.length) % rows.length;
    return { ...state, row };
  }
  const row = rows[state.row];
  const at = Math.max(0, row.findIndex((c) => state.col >= c.col && state.col < c.col + c.span));
  const next = row[(at + (dir === "right" ? 1 : -1) + row.length) % row.length];
  return { ...state, col: next.col };
}

/** The next character set (the `set` key), keeping the focus where it is. */
export function pickerNextSet(state: PickerState, delta = 1): PickerState {
  return { ...state, set: (state.set + delta + PICKER_SETS.length) % PICKER_SETS.length };
}

/** The name with `ch` added at the end, as the C takes it: only a character the font has, while there are fewer than 28. */
export function nameAppend(name: string, ch: string): string {
  return highScoreNameAccepts(ch) && [...name].length < HIGH_SCORE_NAME_MAX ? name + ch : name;
}

/** The name with its last character taken off (Backspace/Delete). */
export function nameDelete(name: string): string {
  return [...name].slice(0, -1).join("");
}
