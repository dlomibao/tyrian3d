// The high score name entry's character grid for pads and touch screens (src/app/namePicker.ts).
import { describe, expect, test } from "vitest";
import { nameAppend, nameDelete, PICKER_COLUMNS, PICKER_SETS, pickerCell, pickerMove, pickerNextSet, pickerRows } from "../../src/app/namePicker";
import { HIGH_SCORE_NAME_MAX, highScoreNameAccepts } from "../../src/sim/highscores";

describe("the grid", () => {
  test("every row covers the ten columns once, and every character is one the entry accepts", () => {
    for (let set = 0; set < PICKER_SETS.length; set++) {
      for (const row of pickerRows(set)) {
        const cols = row.flatMap((c) => Array.from({ length: c.span }, (_, i) => c.col + i));
        expect(cols).toEqual(Array.from({ length: PICKER_COLUMNS }, (_, i) => i));
        for (const c of row) if (c.key.kind === "char") expect(highScoreNameAccepts(c.key.char)).toBe(true);
      }
    }
  });

  test("left/right move along a row and wrap; up/down keep the column", () => {
    let s = { set: 0, row: 0, col: 0 };
    s = pickerMove(s, "left");
    expect(pickerCell(s).key).toEqual({ kind: "char", char: "J" });
    s = pickerMove(s, "right");
    expect(pickerCell(s).key).toEqual({ kind: "char", char: "A" });
    s = pickerMove({ set: 0, row: 0, col: 4 }, "up"); // wraps to the bottom row: the space bar
    expect(pickerCell(s).key).toEqual({ kind: "space" });
    s = pickerMove(s, "down");
    expect(pickerCell(s).key).toEqual({ kind: "char", char: "E" });
  });

  test("on the bottom row, left/right step over the wide keys", () => {
    let s = { set: 0, row: 4, col: 0 };
    expect(pickerCell(s).key.kind).toBe("set");
    s = pickerMove(s, "right");
    expect(pickerCell(s).key.kind).toBe("space");
    s = pickerMove(s, "right");
    expect(pickerCell(s).key.kind).toBe("delete");
    s = pickerMove(s, "right");
    expect(pickerCell(s).key.kind).toBe("ok");
    s = pickerMove(s, "right");
    expect(pickerCell(s).key.kind).toBe("set");
    s = pickerMove(s, "left");
    expect(pickerCell(s).key.kind).toBe("ok");
  });

  test("changing the set keeps the focus in place", () => {
    const s = pickerNextSet({ set: 0, row: 1, col: 2 });
    expect(pickerCell(s).key).toEqual({ kind: "char", char: "m" });
    expect(pickerNextSet(s, -1).set).toBe(0);
    expect(pickerNextSet({ set: 0, row: 0, col: 0 }, -1).set).toBe(PICKER_SETS.length - 1);
  });
});

describe("editing the name, by the C's rules", () => {
  test("only characters the font has, at most 28 (temp < 28)", () => {
    expect(nameAppend("Ac", "e")).toBe("Ace");
    expect(nameAppend("Ace", "@")).toBe("Ace");
    expect(nameAppend("Ace", " ")).toBe("Ace ");
    const full = "x".repeat(HIGH_SCORE_NAME_MAX);
    expect(nameAppend(full, "y")).toBe(full);
    expect(nameAppend(full.slice(1), "y")).toHaveLength(HIGH_SCORE_NAME_MAX);
  });

  test("delete takes off the last character", () => {
    expect(nameDelete("Ace")).toBe("Ac");
    expect(nameDelete("")).toBe("");
    expect(nameDelete("Zoë")).toBe("Zo");
  });
});
