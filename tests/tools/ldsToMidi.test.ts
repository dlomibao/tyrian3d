// Opt-in: the game's 41 songs as MIDI, for arranging them (the private remaster repo).
//
//   MIDI_OUT=../tyrian3d-remaster/source npm run songs-to-midi
//
// Plays each song of music.mus through the ported Loudness player and OPL emulator (the same code
// as the game) and records what the player writes to the FM chip. Each song becomes:
//   song-NN.mid        one track per OPL channel (and a drum track for OPL rhythm mode), 1 MIDI
//                      tick = 1 player update (69.5 Hz); notes start at key-on and change on every
//                      pitch step of a semitone or more (arpeggios, slides); pitches are the
//                      fundamental each FM patch sounds (pitchShift); velocity and CC11
//                      follow the carrier's level; each FM patch is named in the track's events
//   song-NN.json       analysis: length, loop point, the player's row speed, per channel the
//                      notes' range and count and the FM patches used, with their parameters
//   song-NN.wav        the original as the game plays it (one loop), for comparison
// The output is derived from the game's music, which is all rights reserved: it goes to the private
// repo only.
import { describe, test } from "vitest";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { MusicRenderer, parseMusicMus } from "../../src/audio/musicRenderer";
import { hasData, readData } from "../data/dataDir";

const OUT = process.env.MIDI_OUT ?? "";
const RATE = 44100;
const UPDATE_HZ = 69.5;
const MAX_SECONDS = 600;
/** OPL2 operator offsets of each channel's modulator; the carrier is +3. */
const MOD_SLOT = [0, 1, 2, 8, 9, 10, 16, 17, 18];
/** OPL rhythm-mode bits of register 0xBD (bit 4 .. 0) and their General MIDI drums. */
const RHYTHM = [
  { bit: 0x10, name: "bass drum", note: 36 },
  { bit: 0x08, name: "snare", note: 38 },
  { bit: 0x04, name: "tom", note: 45 },
  { bit: 0x02, name: "cymbal", note: 49 },
  { bit: 0x01, name: "hi-hat", note: 42 },
];

interface Ev {
  tick: number;
  data: number[];
}

/** Variable-length quantity for MIDI delta times. */
function vlq(n: number): number[] {
  const out = [n & 0x7f];
  while ((n >>= 7)) out.unshift((n & 0x7f) | 0x80);
  return out;
}

function track(events: Ev[], name: string): Uint8Array {
  const bytes: number[] = [];
  const meta = (type: number, text: string) => {
    const t = [...Buffer.from(text, "latin1")];
    return [0xff, type, ...vlq(t.length), ...t];
  };
  bytes.push(0, ...meta(0x03, name));
  // At one tick: note-offs, then patch markers, then the rest, so a marker precedes the note it names.
  const order = (e: Ev) => (e.data[0] === 0xff ? 1 : (e.data[0] & 0xf0) === 0x80 ? 0 : 2);
  events.sort((a, b) => a.tick - b.tick || order(a) - order(b));
  let last = 0;
  for (const e of events) {
    bytes.push(...vlq(e.tick - last), ...e.data);
    last = e.tick;
  }
  bytes.push(0, 0xff, 0x2f, 0);
  const head = Buffer.alloc(8);
  head.write("MTrk", 0, "latin1");
  head.writeUInt32BE(bytes.length, 4);
  return Buffer.concat([head, Buffer.from(bytes)]);
}

function writeWav(path: string, samples: Int16Array, rate: number): void {
  const h = Buffer.alloc(44);
  h.write("RIFF", 0, "latin1");
  h.writeUInt32LE(36 + samples.length * 2, 4);
  h.write("WAVEfmt ", 8, "latin1");
  h.writeUInt32LE(16, 16);
  h.writeUInt16LE(1, 20);
  h.writeUInt16LE(1, 22);
  h.writeUInt32LE(rate, 24);
  h.writeUInt32LE(rate * 2, 28);
  h.writeUInt16LE(2, 32);
  h.writeUInt16LE(16, 34);
  h.write("data", 36, "latin1");
  h.writeUInt32LE(samples.length * 2, 40);
  writeFileSync(path, Buffer.concat([h, Buffer.from(samples.buffer, samples.byteOffset, samples.byteLength)]));
}

/** MIDI note (fractional) of an OPL2 F-number and block (49716 Hz chip clock). */
const noteOf = (fnum: number, block: number) => 69 + 12 * Math.log2((fnum * 49716) / 2 ** (20 - block) / 440);
/** OPL2 frequency multipliers, as twice their value (MULT 0 = x0.5). */
const MULT2 = [1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 20, 24, 24, 30, 30];
const gcd = (a: number, b: number): number => (b ? gcd(b, a % b) : a);
/**
 * Semitones from the channel's base frequency to the fundamental heard: with strong modulation
 * (modulator level under 24 steps) the spectrum's spacing, gcd of the two operators' frequencies;
 * with weak modulation the carrier's; with additive synthesis the lower operator's.
 */
function pitchShift(p: { modMult: number; carMult: number; modLevel: number; additive: number }): number {
  const m = MULT2[p.modMult], c = MULT2[p.carMult];
  const f2 = p.additive ? Math.min(m, c) : p.modLevel < 24 ? gcd(m, c) : c;
  return Math.round(12 * Math.log2(f2 / 2));
}
/** Velocity from an operator's total level (0.75 dB per step). */
const velocityOf = (tl: number) => Math.max(1, Math.min(127, Math.round(127 * 10 ** ((-tl * 0.75) / 40))));

function convert(mus: Uint8Array, song: number) {
  const r = new MusicRenderer(RATE, mus);
  const regs = new Uint8Array(256);
  let tick = 0;
  const writes: { tick: number; reg: number; val: number }[] = [];
  const opl = r.opl;
  const realWrite = opl.write.bind(opl);
  opl.write = (reg: number, val: number) => {
    writes.push({ tick, reg: reg & 0xff, val: val & 0xff });
    realWrite(reg, val);
  };
  const lds = r.lds;
  const realUpdate = lds.update.bind(lds);
  let loopTick = -1;
  let rowSpeed = -1;
  lds.update = () => {
    const ok = realUpdate();
    tick++;
    const speed = (lds as unknown as { tempo: number }).tempo;
    if (rowSpeed < 0 && speed) rowSpeed = speed;
    if (loopTick < 0 && lds.songlooped) loopTick = tick;
    return ok;
  };
  r.play(song);
  const audio: Int16Array[] = [];
  const block = 1024;
  while (tick < MAX_SECONDS * UPDATE_HZ && loopTick < 0 && (lds.playing || tick === 0)) {
    const buf = new Int16Array(block);
    r.renderRaw(buf, 0, block);
    audio.push(buf);
  }
  const endTick = loopTick > 0 ? loopTick : tick;
  // Trim the audio at the loop point.
  const total = Math.min(audio.length * block, Math.round((endTick / UPDATE_HZ) * RATE));
  const pcm = new Int16Array(total);
  audio.forEach((b, i) => pcm.set(b.subarray(0, Math.max(0, Math.min(block, total - i * block))), i * block));

  // Replay the register writes into notes.
  const tracks: Ev[][] = Array.from({ length: 10 }, () => []);
  const patches = new Map<string, { id: number; params: Record<string, number>; shift: number }>();
  const chan = Array.from({ length: 9 }, () => ({ on: false, onTick: -1, onEvent: null as Ev | null, note: 0, base: 0, patch: -1, vel: 0, count: 0, min: 128, max: -1, patches: new Set<number>() }));
  let rhythm = 0;
  const patchOf = (ch: number) => {
    const m = MOD_SLOT[ch], c = m + 3;
    const keyRegs = [0x20 + m, 0x20 + c, 0x40 + m, 0x60 + m, 0x60 + c, 0x80 + m, 0x80 + c, 0xe0 + m, 0xe0 + c, 0xc0 + ch];
    const key = keyRegs.map((k) => (k === 0x40 + m ? regs[k] & 0x3f : regs[k])).join(",");
    let p = patches.get(key);
    if (!p) {
      p = {
        shift: 0,
        id: patches.size,
        params: {
          modMult: regs[0x20 + m] & 15, carMult: regs[0x20 + c] & 15, modLevel: regs[0x40 + m] & 0x3f,
          carAttack: regs[0x60 + c] >> 4, carDecay: regs[0x60 + c] & 15, carSustain: regs[0x80 + c] >> 4, carRelease: regs[0x80 + c] & 15,
          carSustained: (regs[0x20 + c] >> 5) & 1, feedback: (regs[0xc0 + ch] >> 1) & 7, additive: regs[0xc0 + ch] & 1,
          modWave: regs[0xe0 + m] & 3, carWave: regs[0xe0 + c] & 3,
        },
      };
      p.shift = pitchShift(p.params as never);
      patches.set(key, p);
    }
    return p;
  };
  const off = (ch: number, t: number) => {
    const s = chan[ch];
    if (!s.on) return;
    s.on = false;
    // A pitch is written in two registers; a note that ends on the tick it started was the
    // in-between value, not a note.
    if (t === s.onTick) {
      const i = tracks[ch].lastIndexOf(s.onEvent!);
      if (i >= 0) tracks[ch].splice(i, 1);
      s.count--;
      return;
    }
    tracks[ch].push({ tick: t, data: [0x80 | ch, s.note, 0] });
  };
  const on = (ch: number, t: number, base: number) => {
    const s = chan[ch];
    const m = MOD_SLOT[ch];
    const p = patchOf(ch);
    const patch = p.id;
    const note = Math.max(0, Math.min(127, base + p.shift));
    if (patch !== s.patch) {
      tracks[ch].push({ tick: t, data: [0xff, 0x06, ...vlq(`patch ${patch}`.length), ...Buffer.from(`patch ${patch}`, "latin1")] });
      s.patch = patch;
    }
    s.patches.add(patch);
    s.vel = velocityOf(regs[0x40 + m + 3] & 0x3f);
    s.onEvent = { tick: t, data: [0x90 | ch, note, s.vel] };
    s.onTick = t;
    tracks[ch].push(s.onEvent);
    s.on = true;
    s.note = note;
    s.base = base;
    s.count++;
    s.min = Math.min(s.min, note);
    s.max = Math.max(s.max, note);
  };
  for (const w of writes) {
    if (w.tick > endTick) break;
    const prev = regs[w.reg];
    regs[w.reg] = w.val;
    const t = w.tick;
    if ((w.reg >= 0xa0 && w.reg <= 0xa8) || (w.reg >= 0xb0 && w.reg <= 0xb8)) {
      const ch = w.reg & 0x0f;
      const keyOn = (regs[0xb0 + ch] & 0x20) !== 0;
      const fnum = regs[0xa0 + ch] | ((regs[0xb0 + ch] & 3) << 8);
      const note = Math.round(noteOf(fnum, (regs[0xb0 + ch] >> 2) & 7));
      const s = chan[ch];
      if (!keyOn) off(ch, t);
      else if (!s.on || (w.reg >= 0xb0 && (prev & 0x20) === 0)) {
        off(ch, t);
        if (fnum > 0 && note >= 0 && note < 128) on(ch, t, note);
      } else if (note !== s.base && fnum > 0 && note >= 0 && note < 128) {
        off(ch, t); // a pitch step of a semitone or more: arpeggio, slide or new note
        on(ch, t, note);
      }
    } else if (w.reg >= 0x40 && w.reg <= 0x55) {
      // Level changes of a sounding note's carrier: expression.
      for (let ch = 0; ch < 9; ch++) {
        if (w.reg === 0x40 + MOD_SLOT[ch] + 3 && chan[ch].on) {
          const v = velocityOf(w.val & 0x3f);
          tracks[ch].push({ tick: t, data: [0xb0 | ch, 11, Math.min(127, Math.round((v / Math.max(1, chan[ch].vel)) * 127))] });
        }
      }
    } else if (w.reg === 0xbd) {
      const nowRhythm = w.val & 0x20 ? w.val : 0;
      for (const d of RHYTHM) {
        const was = rhythm & 0x20 && rhythm & d.bit, is = nowRhythm & d.bit;
        if (is && !was) tracks[9].push({ tick: t, data: [0x99, d.note, 100] }, { tick: t + 4, data: [0x89, d.note, 0] });
      }
      rhythm = nowRhythm;
    }
  }
  for (let ch = 0; ch < 9; ch++) off(ch, endTick);

  const used = tracks.map((t, i) => ({ events: t, ch: i })).filter((t) => t.events.length > 0);
  const tempoTrack: Ev[] = [{ tick: 0, data: [0xff, 0x51, 3, ...[16, 8, 0].map((s) => (Math.round((rowSpeed > 0 ? rowSpeed * 4 : 96) * (1e6 / UPDATE_HZ)) >> s) & 0xff)] }];
  const division = rowSpeed > 0 ? rowSpeed * 4 : 96; // one quarter = 4 rows of the player
  const head = Buffer.alloc(14);
  head.write("MThd", 0, "latin1");
  head.writeUInt32BE(6, 4);
  head.writeUInt16BE(1, 8);
  head.writeUInt16BE(used.length + 1, 10);
  head.writeUInt16BE(division, 12);
  const midi = Buffer.concat([head, track(tempoTrack, `Tyrian song ${song + 1}`), ...used.map((t) => track(t.events, t.ch === 9 ? "OPL rhythm" : `OPL channel ${t.ch}`))]);

  const analysis = {
    song: song + 1,
    seconds: endTick / UPDATE_HZ,
    loops: loopTick > 0,
    updateHz: UPDATE_HZ,
    ticksPerRow: rowSpeed,
    midiTicksPerQuarter: division,
    note: "1 MIDI tick = 1 player update; a quarter note is taken as 4 rows",
    channels: chan.map((s, i) => ({ channel: i, notes: s.count, range: s.count ? [s.min, s.max] : null, patches: [...s.patches] })).filter((c) => c.notes),
    drums: tracks[9].filter((e) => (e.data[0] & 0xf0) === 0x90).length,
    patches: [...patches.values()].map((p) => ({ id: p.id, semitonesFromBase: p.shift, ...p.params })),
  };
  return { midi, analysis, pcm };
}

describe.skipIf(!OUT || !hasData("music.mus"))("songs to MIDI", () => test("convert", () => {
  mkdirSync(OUT, { recursive: true });
  const songs = parseMusicMus(readData("music.mus"));
  for (let i = 0; i < songs.length; i++) {
    const { midi, analysis, pcm } = convert(readData("music.mus"), i);
    const base = join(OUT, `song-${String(i + 1).padStart(2, "0")}`);
    writeFileSync(`${base}.mid`, midi);
    writeFileSync(`${base}.json`, JSON.stringify(analysis, null, 1) + "\n");
    writeWav(`${base}.wav`, pcm, RATE);
  }
}), 600_000);
