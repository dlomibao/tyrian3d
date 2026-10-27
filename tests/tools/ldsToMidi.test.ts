// Opt-in: the game's 41 songs as MIDI, for arranging them (the private remaster repo).
//
//   MIDI_OUT=../tyrian3d-remaster/source npm run songs-to-midi
//
// Plays each song of music.mus through the ported Loudness player and OPL emulator (the same code
// as the game) and records what the player writes to the FM chip. Each song becomes:
//   song-NN.mid        one track per OPL channel (and a drum track for OPL rhythm mode), 1 MIDI
//                      tick = 1 player update (69.5 Hz); a note starts where the player strikes one
//                      (playsound or key-on) and arpeggio steps are notes; slides, vibrato, scoops and
//                      drum pitch falls are pitch bend (range 24 semitones, set by RPN 0); pitches are
//                      the fundamental each FM patch sounds (pitchShift); velocity and CC11
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
/** Pitch-bend range set on every channel (RPN 0), in semitones. */
const BEND_RANGE = 24;
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
  // New notes are the player's playsound calls; pitch changes without one are slides, vibrato or
  // an arpeggio (whether a channel's arpeggio is running is read after each update).
  const internals = lds as unknown as {
    playsound(inst: number, chan: number, high: number): void;
    channel: { arp_size: number }[];
  };
  const realPlaysound = internals.playsound.bind(lds);
  const struck: Set<number>[] = [];
  internals.playsound = (inst: number, chan: number, high: number) => {
    (struck[tick] ??= new Set()).add(chan);
    realPlaysound(inst, chan, high);
  };
  const arpeggio: boolean[][] = [];
  lds.update = () => {
    const ok = realUpdate();
    arpeggio[tick] = internals.channel.map((c) => c.arp_size !== 0);
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

  // Replay the register writes tick by tick into notes. A note starts at a key-on or a playsound;
  // while it's held, an arpeggio step starts a new note and any other pitch change (slides, vibrato,
  // scoops, a drum's falling pitch) becomes pitch bend on it (range BEND_RANGE semitones).
  const tracks: Ev[][] = Array.from({ length: 10 }, () => []);
  const patches = new Map<string, { id: number; params: Record<string, number>; shift: number }>();
  const chan = Array.from({ length: 9 }, () => ({
    on: false, note: 0, ref: 0, bend: 0, lastStep: 0, patch: -1, vel: 0, count: 0, bends: 0, min: 128, max: -1, patches: new Set<number>(),
  }));
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
  const bendTo = (ch: number, t: number, semis: number) => {
    const v = Math.max(0, Math.min(16383, Math.round(8192 + (semis / BEND_RANGE) * 8192)));
    tracks[ch].push({ tick: t, data: [0xe0 | ch, v & 0x7f, v >> 7] });
  };
  const off = (ch: number, t: number) => {
    const s = chan[ch];
    if (!s.on) return;
    s.on = false;
    tracks[ch].push({ tick: t, data: [0x80 | ch, s.note, 0] });
  };
  /** Start a note at the exact (fractional) MIDI pitch `exact`. */
  const on = (ch: number, t: number, exact: number) => {
    const s = chan[ch];
    const m = MOD_SLOT[ch];
    const p = patchOf(ch);
    if (p.id !== s.patch) {
      tracks[ch].push({ tick: t, data: [0xff, 0x06, ...vlq(`patch ${p.id}`.length), ...Buffer.from(`patch ${p.id}`, "latin1")] });
      s.patch = p.id;
    }
    const note = Math.max(0, Math.min(127, Math.round(exact) + p.shift));
    if (s.bend !== 0) bendTo(ch, t, 0);
    s.bend = 0;
    s.patches.add(p.id);
    s.vel = velocityOf(regs[0x40 + m + 3] & 0x3f);
    tracks[ch].push({ tick: t, data: [0x90 | ch, note, s.vel] });
    s.on = true;
    s.note = note;
    s.ref = Math.round(exact);
    s.lastStep = t;
    s.count++;
    s.min = Math.min(s.min, note);
    s.max = Math.max(s.max, note);
  };
  const keyRose = new Array<boolean>(9).fill(false);
  let w = 0;
  for (let t = 0; t <= endTick; t++) {
    keyRose.fill(false);
    for (; w < writes.length && writes[w].tick === t; w++) {
      const { reg, val } = writes[w];
      const prev = regs[reg];
      regs[reg] = val;
      if (reg >= 0xb0 && reg <= 0xb8 && !(prev & 0x20) && val & 0x20) keyRose[reg & 0x0f] = true;
      if (reg >= 0x40 && reg <= 0x55) {
        // Level changes of a sounding note's carrier: expression.
        for (let ch = 0; ch < 9; ch++) {
          if (reg === 0x40 + MOD_SLOT[ch] + 3 && chan[ch].on) {
            const v = velocityOf(val & 0x3f);
            tracks[ch].push({ tick: t, data: [0xb0 | ch, 11, Math.min(127, Math.round((v / Math.max(1, chan[ch].vel)) * 127))] });
          }
        }
      } else if (reg === 0xbd) {
        const nowRhythm = val & 0x20 ? val : 0;
        for (const d of RHYTHM) {
          const was = rhythm & 0x20 && rhythm & d.bit, is = nowRhythm & d.bit;
          if (is && !was) tracks[9].push({ tick: t, data: [0x99, d.note, 100] }, { tick: t + 4, data: [0x89, d.note, 0] });
        }
        rhythm = nowRhythm;
      }
    }
    // Each channel as it stands at the end of this tick.
    for (let ch = 0; ch < 9; ch++) {
      const s = chan[ch];
      const keyOn = (regs[0xb0 + ch] & 0x20) !== 0;
      const fnum = regs[0xa0 + ch] | ((regs[0xb0 + ch] & 3) << 8);
      if (!keyOn || fnum === 0) {
        off(ch, t);
        continue;
      }
      const exact = noteOf(fnum, (regs[0xb0 + ch] >> 2) & 7);
      if (exact < 0 || exact > 127) continue;
      const newNote = !s.on || keyRose[ch] || struck[t]?.has(ch);
      // An arpeggio step is a note when the previous step was held 2 ticks or more; faster steps (a
      // drum's pitch fall, a one-tick "zap") are bend on one note.
      const pitchStep = s.on && arpeggio[t]?.[ch] && Math.round(exact) !== Math.round(s.ref + s.bend);
      const arpStep = pitchStep && t - s.lastStep >= 2;
      if (pitchStep) s.lastStep = t;
      if (newNote || arpStep || Math.abs(exact - s.ref) > BEND_RANGE - 0.5) {
        off(ch, t);
        on(ch, t, exact);
        continue;
      }
      const semis = Math.round((exact - s.ref) * 100) / 100;
      if (semis !== s.bend) {
        bendTo(ch, t, semis);
        if (s.bend === 0) s.bends++;
        s.bend = semis;
      }
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
  // Each melodic channel opens by setting its pitch-bend range (RPN 0) to BEND_RANGE semitones.
  for (const t of used) {
    if (t.ch === 9) continue;
    t.events.unshift(...[[101, 0], [100, 0], [6, BEND_RANGE], [38, 0]].map(([cc, v]) => ({ tick: 0, data: [0xb0 | t.ch, cc, v] })));
  }
  const midi = Buffer.concat([head, track(tempoTrack, `Tyrian song ${song + 1}`), ...used.map((t) => track(t.events, t.ch === 9 ? "OPL rhythm" : `OPL channel ${t.ch}`))]);

  const analysis = {
    song: song + 1,
    seconds: endTick / UPDATE_HZ,
    loops: loopTick > 0,
    updateHz: UPDATE_HZ,
    ticksPerRow: rowSpeed,
    midiTicksPerQuarter: division,
    note: "1 MIDI tick = 1 player update; a quarter note is taken as 4 rows",
    bendRange: BEND_RANGE,
    channels: chan.map((s, i) => ({ channel: i, notes: s.count, bentNotes: s.bends, range: s.count ? [s.min, s.max] : null, patches: [...s.patches] })).filter((c) => c.notes),
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
