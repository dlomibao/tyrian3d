import { describe, expect, test } from "vitest";
import { decodePcxFile, decodePcxRle, decodePicture, PCX_NUM, picturePositions } from "../../src/data/pictures";
import { hasData, readData } from "./dataDir";

test("decodePcxRle: runs, literals, and a run that doesn't fit is dropped with what follows", () => {
  // 0xC3 0x07: three 7s; 0x05: one 5; 0xC0 0x09: a zero-length run.
  const img = decodePcxRle(new Uint8Array([0xc3, 7, 5, 0xc0, 9, 0x3f]));
  expect(Array.from(img.subarray(0, 6))).toEqual([7, 7, 7, 5, 0x3f, 0]);
  expect(img).toHaveLength(320 * 200);

  // Fill to 2 pixels short of the end, then a 3-pixel run (dropped) and a literal (also dropped:
  // MemWriter's error sticks).
  const runs = new Array(Math.floor((64000 - 2) / 63)).fill([0xff, 1]).flat();
  const left = 64000 - 2 - runs.length / 2 * 63;
  const data = new Uint8Array([...runs, 0xc0 | left, 1, 0xc3, 2, 4]);
  const full = decodePcxRle(data);
  expect(full[64000 - 3]).toBe(1);
  expect(full[64000 - 2]).toBe(0);
  expect(full[64000 - 1]).toBe(0);
});

describe.skipIf(!hasData("tyrian.pic"))("tyrian.pic (JE_loadPic)", () => {
  test("holds PCX_NUM pictures of 320x200", () => {
    const data = readData("tyrian.pic");
    const pcxpos = picturePositions(data);
    expect(pcxpos).toHaveLength(PCX_NUM + 1);
    expect(pcxpos[0]).toBe(2 + 4 * PCX_NUM);
    expect(pcxpos[PCX_NUM]).toBe(data.length);
    for (let id = 1; id <= PCX_NUM; id++) {
      const pic = decodePicture(data, id)!;
      expect(pic).toHaveLength(64000);
      expect(pic.some((c) => c !== 0)).toBe(true);
    }
    expect(decodePicture(data, 0)).toBeNull();
    expect(decodePicture(data, PCX_NUM + 1)).toBeNull();
  });
});

describe.skipIf(!hasData("tshp2.pcx"))("tshp2.pcx (JE_loadPCX)", () => {
  test("decodes to 320x200 with its own 8-bit palette from the last 768 bytes", () => {
    const data = readData("tshp2.pcx");
    // The PCX header: version 5, RLE, 8 bits per pixel, window 0,0..319,199.
    expect([data[0], data[1], data[2], data[3]]).toEqual([10, 5, 1, 8]);
    const pcx = decodePcxFile(data)!;
    expect(pcx.pixels).toHaveLength(64000);
    expect(pcx.palette8).toEqual(data.slice(data.length - 768));
    expect(Math.max(...pcx.palette8)).toBeGreaterThan(63); // 8-bit, unlike palette.dat
    expect(data[data.length - 769]).toBe(12); // the PCX palette marker, after the pixel data
  });
});
