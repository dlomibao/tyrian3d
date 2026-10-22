/*
 *  Copyright (C) 2002-2010  The DOSBox Team
 *  OPL2/OPL3 emulation library
 *
 *  This library is free software; you can redistribute it and/or
 *  modify it under the terms of the GNU Lesser General Public
 *  License as published by the Free Software Foundation; either
 *  version 2.1 of the License, or (at your option) any later version.
 *
 *  This library is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 *  Lesser General Public License for more details.
 *
 *  You should have received a copy of the GNU Lesser General Public
 *  License along with this library; if not, write to the Free Software
 *  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
 */

/*
 * Originally based on ADLIBEMU.C, an AdLib/OPL2 emulation library by Ken Silverman
 * Copyright (C) 1998-2001 Ken Silverman
 * Ken Silverman's official web site: "http://www.advsys.net/ken"
 */

/*
 * TypeScript port of OpenTyrian's src/opl.c (the DOSBox OPL emulator, OPL2 build: OpenTyrian
 * does not define OPLTYPE_IS_OPL3). Ported for Tyrian 3D; still LGPL-2.1-or-later.
 *
 * The C mixes 32-bit unsigned phase counters, signed 32-bit products and doubles; this port keeps
 * each of those exactly: `>>> 0` where the C stores into a Bit32u, `Math.imul`/`| 0` where it
 * multiplies or truncates into a Bit32s, and double expressions evaluated in the C's order so the
 * IEEE results match. The only intentional change is that the chip is an instance instead of file
 * globals, and `rand()` (rhythm-mode noise) is a local deterministic LCG.
 */

import { exp2 } from "./exp2";

const FIXEDPT = 0x10000; // fixed-point calculations using 16+16
const FIXEDPT_LFO = 0x1000000; // fixed-point calculations using 8+24

const WAVEPREC = 1024; // waveform precision (10 bits)

const INTFREQU = 14318180.0 / 288.0; // clocking of the chip

const OF_TYPE_ATT = 0;
const OF_TYPE_DEC = 1;
const OF_TYPE_REL = 2;
const OF_TYPE_SUS = 3;
const OF_TYPE_SUS_NOKEEP = 4;
const OF_TYPE_OFF = 5;

const ARC_CONTROL = 0x00;
const ARC_TVS_KSR_MUL = 0x20;
const ARC_KSL_OUTLEV = 0x40;
const ARC_ATTR_DECR = 0x60;
const ARC_SUSL_RELR = 0x80;
const ARC_FREQ_NUM = 0xa0;
const ARC_KON_BNUM = 0xb0;
const ARC_PERC_MODE = 0xbd;
const ARC_FEEDBACK = 0xc0;
const ARC_WAVE_SEL = 0xe0;

const OP_ACT_OFF = 0x00;
const OP_ACT_NORMAL = 0x01; // regular channel activated (bitmasked)
const OP_ACT_PERC = 0x02; // percussion channel activated (bitmasked)

const BLOCKBUF_SIZE = 512;

const NUM_CHANNELS = 9;
const MAXOPERATORS = NUM_CHANNELS * 2;

// vibrato constants
const VIBTAB_SIZE = 8;
// VIBFAC is `70/50000` without braces in the C: integer multiply then divide (see vibval()).

// tremolo constants and table
const TREMTAB_SIZE = 53;
const TREM_FREQ = 3.7; // tremolo at 3.7hz

// key scale level lookup table
const kslmul = [0.0, 0.5, 0.25, 1.0]; // -> 0, 3, 1.5, 6 dB/oct

// frequency multiplicator lookup table
const frqmul_tab = [0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 12, 12, 15, 15];

// map a channel number to the register offset of the modulator (=register base)
const modulatorbase = [0, 1, 2, 8, 9, 10, 16, 17, 18];

// map a register base to a modulator operator number or operator number
const regbase2modop = [0, 1, 2, 0, 1, 2, 0, 0, 3, 4, 5, 3, 4, 5, 0, 0, 6, 7, 8, 6, 7, 8];
const regbase2op = [0, 1, 2, 9, 10, 11, 0, 0, 3, 4, 5, 12, 13, 14, 0, 0, 6, 7, 8, 15, 16, 17];

// start of the waveform
const waveform = [
  WAVEPREC,
  WAVEPREC >> 1,
  WAVEPREC,
  (WAVEPREC * 3) >> 2,
  0,
  0,
  (WAVEPREC * 5) >> 2,
  WAVEPREC << 1,
];

// length of the waveform as mask
const wavemask = [
  WAVEPREC - 1,
  WAVEPREC - 1,
  (WAVEPREC >> 1) - 1,
  (WAVEPREC >> 1) - 1,
  WAVEPREC - 1,
  ((WAVEPREC * 3) >> 2) - 1,
  WAVEPREC >> 1,
  WAVEPREC - 1,
];

// where the first entry resides
const wavestart = [0, WAVEPREC >> 1, 0, WAVEPREC >> 2, 0, 0, 0, WAVEPREC >> 3];

// envelope generator function constants
const attackconst = [1 / 2.82624, 1 / 2.2528, 1 / 1.88416, 1 / 1.59744];
const decrelconst = [1 / 39.28064, 1 / 31.41608, 1 / 26.17344, 1 / 22.44608];

const step_skip_mask = [0xff, 0xfe, 0xee, 0xba, 0xaa];

// Waveform and key-scale tables: in the C these are built on the first adlib_init() only, and they
// don't depend on the sample rate, so they're built once at module load here.
const wavtable = new Int16Array(WAVEPREC * 3); // wave form table
const kslev: Uint8Array[] = Array.from({ length: 8 }, () => new Uint8Array(16)); // key scale levels
{
  // create waveform tables
  for (let i = 0; i < WAVEPREC >> 1; i++) {
    wavtable[(i << 1) + WAVEPREC] = Math.trunc(16384 * Math.sin(((i << 1) * Math.PI * 2) / WAVEPREC));
    wavtable[(i << 1) + 1 + WAVEPREC] = Math.trunc(
      16384 * Math.sin((((i << 1) + 1) * Math.PI * 2) / WAVEPREC),
    );
    wavtable[i] = wavtable[(i << 1) + WAVEPREC];
  }
  for (let i = 0; i < WAVEPREC >> 3; i++) {
    wavtable[i + (WAVEPREC << 1)] = wavtable[i + (WAVEPREC >> 3)] - 16384;
    wavtable[i + ((WAVEPREC * 17) >> 3)] = wavtable[i + (WAVEPREC >> 2)] + 16384;
  }

  // key scale level table verified ([table in book]*8/3)
  const k7 = [0, 24, 32, 37, 40, 43, 45, 47, 48];
  for (let i = 0; i < 9; i++) kslev[7][i] = k7[i];
  for (let i = 9; i < 16; i++) kslev[7][i] = i + 41;
  for (let j = 6; j >= 0; j--) {
    for (let i = 0; i < 16; i++) {
      let oct = kslev[j + 1][i] - 8;
      if (oct < 0) oct = 0;
      kslev[j][i] = oct;
    }
  }
}

// pow(2, x) results that only depend on register values. They go through a correctly rounded
// exp2 (see exp2.ts) so they match a good C libm bit for bit.
// vol: vol_in = (0..63) + kslmul*kslev is a multiple of 0.25 in [0, 63 + 112].
const volTable = new Float64Array(4 * (63 + 112) + 1);
for (let q = 0; q < volTable.length; q++) volTable[q] = exp2((q / 4) * -0.125 - 14);
const sustainLevelTable = new Float64Array(15);
for (let s = 0; s < 15; s++) sustainLevelTable[s] = exp2(s * -0.5);

/** Exposed for cross-checking against the C tables in tests. */
export const oplTables = { wavtable, kslev } as const;

/** One FM operator (op_type in the C). */
class Operator {
  cval = 0; // Bit32s current output
  lastcval = 0; // Bit32s last output (used for feedback)
  tcount = 0; // Bit32u time (position in waveform)
  wfpos = 0; // Bit32u
  tinc = 0; // Bit32u time increment
  amp = 0.0; // amplification (envelope)
  step_amp = 0.0;
  vol = 0.0; // volume
  sustain_level = 0.0; // sustain level
  mfbi = 0; // Bit32s feedback amount
  a0 = 0.0; // attack rate function coefficients
  a1 = 0.0;
  a2 = 0.0;
  a3 = 0.0;
  decaymul = 0.0; // decay/release rate functions
  releasemul = 0.0;
  op_state = OF_TYPE_OFF; // current state of operator (attack/decay/sustain/release/off)
  toff = 0; // Bit32u
  freq_high = 0; // Bit32s highest three bits of the frequency, used for vibrato calculations
  cur_wform = 0; // start of selected waveform (index into wavtable)
  cur_wmask = 0; // mask for selected waveform
  act_state = OP_ACT_OFF; // activity state (regular, percussion)
  sus_keep = false; // keep sustain level when decay finished
  vibrato = false; // vibrato/tremolo enable bits
  tremolo = false;

  // variables used to provide non-continuous envelopes
  generator_pos = 0; // Bit32u for non-standard sample rates we need to determine how many samples have passed
  cur_env_step = 0; // current (standardized) sample position
  env_step_a = 0; // number of std samples of one step (for attack/decay/release mode)
  env_step_d = 0;
  env_step_r = 0;
  step_skip_pos_a = 0; // Bit8u position of 8-cyclic step skipping (always 2^x to check against mask)
  env_step_skip_a = 0; // bitmask that determines if a step is skipped (respective bit is zero then)

  /** memset(op, 0) followed by adlib_init's explicit field setup. */
  reset(): void {
    this.cval = this.lastcval = 0;
    this.tcount = this.wfpos = this.tinc = 0;
    this.amp = this.step_amp = this.vol = this.sustain_level = 0.0;
    this.mfbi = 0;
    this.a0 = this.a1 = this.a2 = this.a3 = 0.0;
    this.decaymul = this.releasemul = 0.0;
    this.op_state = OF_TYPE_OFF;
    this.act_state = OP_ACT_OFF;
    this.toff = 0;
    this.cur_wmask = wavemask[0];
    this.cur_wform = waveform[0];
    this.freq_high = 0;
    this.sus_keep = this.vibrato = this.tremolo = false;
    this.generator_pos = 0;
    this.cur_env_step = 0;
    this.env_step_a = this.env_step_d = this.env_step_r = 0;
    this.step_skip_pos_a = 0;
    this.env_step_skip_a = 0;
  }
}

/** `(Bit32s)((vib_lut[i]*freq_high/8)*FIXEDPT*VIBFAC)` with VIBFAC = `70/50000` (integer math). */
function vibval(lut: number, freq_high: number): number {
  return Math.trunc((Math.trunc((lut * freq_high) / 8) * FIXEDPT * 70) / 50000);
}

/** clipit16 */
function clipit16(ival: number): number {
  if (ival < 32768) {
    if (ival > -32769) return ival;
    return -32768;
  }
  return 32767;
}

/** An emulated OPL2 chip (DOSBox OPL emulator). */
export class Opl {
  private readonly op: Operator[] = Array.from({ length: MAXOPERATORS }, () => new Operator());

  private int_samplerate = 0;

  private status = 0;
  private readonly adlibreg = new Uint8Array(256); // adlib register set
  private readonly wave_sel = new Uint8Array(22); // waveform selection

  // vibrato/tremolo increment/counter
  private vibtab_pos = 0;
  private vibtab_add = 0;
  private tremtab_pos = 0;
  private tremtab_add = 0;

  private generator_add = 0; // should be a chip parameter

  private recipsamp = 0.0; // inverse of sampling rate

  // vibrato/tremolo tables
  private readonly vib_table = new Int32Array(VIBTAB_SIZE);
  private readonly trem_table = new Int32Array(TREMTAB_SIZE * 2);

  private readonly vibval_const = new Int32Array(BLOCKBUF_SIZE);
  private readonly tremval_const = new Int32Array(BLOCKBUF_SIZE);

  // vibrato value tables (used per-operator)
  private readonly vibval_var1 = new Int32Array(BLOCKBUF_SIZE);
  private readonly vibval_var2 = new Int32Array(BLOCKBUF_SIZE);

  // calculated frequency multiplication values (depend on sampling rate)
  private readonly frqmul = new Float64Array(16);
  // decay/release multipliers by rate*16+toff (depend on sampling rate; see init)
  private readonly decrelmulTable = new Float64Array(16 * 16);

  // adlib_getsample's stack buffers
  private readonly outbufl = new Int32Array(BLOCKBUF_SIZE);
  private readonly vib_lut = new Int32Array(BLOCKBUF_SIZE);
  private readonly trem_lut = new Int32Array(BLOCKBUF_SIZE);

  // rand() state for rhythm-mode noise (glibc-style LCG; deterministic per chip).
  private randState = 1;

  constructor(samplerate: number) {
    this.init(samplerate);
  }

  get sampleRate(): number {
    return this.int_samplerate;
  }

  private rand(): number {
    this.randState = (Math.imul(this.randState, 1103515245) + 12345) >>> 0;
    return (this.randState >>> 16) & 0x7fff;
  }

  // ---- operator envelope/phase steps ----

  private operator_advance(op_pt: Operator, vib: number): void {
    op_pt.wfpos = op_pt.tcount; // waveform position

    // advance waveform time
    op_pt.tcount = (op_pt.tcount + op_pt.tinc) >>> 0;
    op_pt.tcount = (op_pt.tcount + ((Math.imul(op_pt.tinc | 0, vib) / FIXEDPT) | 0)) >>> 0;

    op_pt.generator_pos = (op_pt.generator_pos + this.generator_add) >>> 0;
  }

  private operator_advance_drums(
    op_pt1: Operator,
    vib1: number,
    op_pt2: Operator,
    vib2: number,
    op_pt3: Operator,
    vib3: number,
  ): void {
    const c1 = op_pt1.tcount >>> 16;
    const c3 = op_pt3.tcount >>> 16;
    const phasebit = ((c1 & 0x88) ^ ((c1 << 5) & 0x80)) | ((c3 ^ (c3 << 2)) & 0x20) ? 0x02 : 0x00;

    const noisebit = this.rand() & 1;

    const snare_phase_bit = (op_pt1.tcount >>> 16 >>> 8) & 1;

    //Hihat
    let inttm = (phasebit << 8) | (0x34 << (phasebit ^ (noisebit << 1)));
    op_pt1.wfpos = (inttm * FIXEDPT) >>> 0; // waveform position
    // advance waveform time
    op_pt1.tcount = (op_pt1.tcount + op_pt1.tinc) >>> 0;
    op_pt1.tcount = (op_pt1.tcount + ((Math.imul(op_pt1.tinc | 0, vib1) / FIXEDPT) | 0)) >>> 0;
    op_pt1.generator_pos = (op_pt1.generator_pos + this.generator_add) >>> 0;

    //Snare
    inttm = ((1 + snare_phase_bit) ^ noisebit) << 8;
    op_pt2.wfpos = (inttm * FIXEDPT) >>> 0; // waveform position
    // advance waveform time
    op_pt2.tcount = (op_pt2.tcount + op_pt2.tinc) >>> 0;
    op_pt2.tcount = (op_pt2.tcount + ((Math.imul(op_pt2.tinc | 0, vib2) / FIXEDPT) | 0)) >>> 0;
    op_pt2.generator_pos = (op_pt2.generator_pos + this.generator_add) >>> 0;

    //Cymbal
    inttm = (1 + phasebit) << 8;
    op_pt3.wfpos = (inttm * FIXEDPT) >>> 0; // waveform position
    // advance waveform time
    op_pt3.tcount = (op_pt3.tcount + op_pt3.tinc) >>> 0;
    op_pt3.tcount = (op_pt3.tcount + ((Math.imul(op_pt3.tinc | 0, vib3) / FIXEDPT) | 0)) >>> 0;
    op_pt3.generator_pos = (op_pt3.generator_pos + this.generator_add) >>> 0;
  }

  // output level is sustained, mode changes only when operator is turned off (->release)
  // or when the keep-sustained bit is turned off (->sustain_nokeep)
  private static operator_output(op_pt: Operator, modulator: number, trem: number): void {
    if (op_pt.op_state !== OF_TYPE_OFF) {
      op_pt.lastcval = op_pt.cval;
      const i = ((op_pt.wfpos + modulator) >>> 0) >>> 16;

      // wform: -16384 to 16383 (0x4000)
      // trem :  32768 to 65535 (0x10000)
      // step_amp: 0.0 to 1.0
      // vol  : 1/2^14 to 1/2^29 (/0x4000; /1../0x8000)

      op_pt.cval =
        ((op_pt.step_amp * op_pt.vol * wavtable[op_pt.cur_wform + (i & op_pt.cur_wmask)] * trem) / 16.0) |
        0;
    }
  }

  // output level is sustained, mode changes only when operator is turned off (->release)
  // or when the keep-sustained bit is turned off (->sustain_nokeep)
  private static operator_sustain(op_pt: Operator): void {
    const num_steps_add = op_pt.generator_pos >>> 16; // number of (standardized) samples
    op_pt.cur_env_step += num_steps_add;
    op_pt.generator_pos = (op_pt.generator_pos - num_steps_add * FIXEDPT) >>> 0;
  }

  // operator in release mode, if output level reaches zero the operator is turned off
  private static operator_release(op_pt: Operator): void {
    // ??? boundary?
    if (op_pt.amp > 0.00000001) {
      // release phase
      op_pt.amp *= op_pt.releasemul;
    }

    const num_steps_add = op_pt.generator_pos >>> 16; // number of (standardized) samples
    for (let ct = 0; ct < num_steps_add; ct++) {
      op_pt.cur_env_step++; // sample counter
      if ((op_pt.cur_env_step & op_pt.env_step_r) === 0) {
        if (op_pt.amp <= 0.00000001) {
          // release phase finished, turn off this operator
          op_pt.amp = 0.0;
          if (op_pt.op_state === OF_TYPE_REL) {
            op_pt.op_state = OF_TYPE_OFF;
          }
        }
        op_pt.step_amp = op_pt.amp;
      }
    }
    op_pt.generator_pos = (op_pt.generator_pos - num_steps_add * FIXEDPT) >>> 0;
  }

  // operator in decay mode, if sustain level is reached the output level is either
  // kept (sustain level keep enabled) or the operator is switched into release mode
  private static operator_decay(op_pt: Operator): void {
    if (op_pt.amp > op_pt.sustain_level) {
      // decay phase
      op_pt.amp *= op_pt.decaymul;
    }

    const num_steps_add = op_pt.generator_pos >>> 16; // number of (standardized) samples
    for (let ct = 0; ct < num_steps_add; ct++) {
      op_pt.cur_env_step++;
      if ((op_pt.cur_env_step & op_pt.env_step_d) === 0) {
        if (op_pt.amp <= op_pt.sustain_level) {
          // decay phase finished, sustain level reached
          if (op_pt.sus_keep) {
            // keep sustain level (until turned off)
            op_pt.op_state = OF_TYPE_SUS;
            op_pt.amp = op_pt.sustain_level;
          } else {
            // next: release phase
            op_pt.op_state = OF_TYPE_SUS_NOKEEP;
          }
        }
        op_pt.step_amp = op_pt.amp;
      }
    }
    op_pt.generator_pos = (op_pt.generator_pos - num_steps_add * FIXEDPT) >>> 0;
  }

  // operator in attack mode, if full output level is reached,
  // the operator is switched into decay mode
  private static operator_attack(op_pt: Operator): void {
    op_pt.amp = ((op_pt.a3 * op_pt.amp + op_pt.a2) * op_pt.amp + op_pt.a1) * op_pt.amp + op_pt.a0;

    const num_steps_add = op_pt.generator_pos >>> 16; // number of (standardized) samples
    for (let ct = 0; ct < num_steps_add; ct++) {
      op_pt.cur_env_step++; // next sample
      if ((op_pt.cur_env_step & op_pt.env_step_a) === 0) {
        // check if next step already reached
        if (op_pt.amp > 1.0) {
          // attack phase finished, next: decay
          op_pt.op_state = OF_TYPE_DEC;
          op_pt.amp = 1.0;
          op_pt.step_amp = 1.0;
        }
        op_pt.step_skip_pos_a = (op_pt.step_skip_pos_a << 1) & 0xff;
        if (op_pt.step_skip_pos_a === 0) op_pt.step_skip_pos_a = 1;
        if (op_pt.step_skip_pos_a & op_pt.env_step_skip_a) {
          // check if required to skip next step
          op_pt.step_amp = op_pt.amp;
        }
      }
    }
    op_pt.generator_pos = (op_pt.generator_pos - num_steps_add * FIXEDPT) >>> 0;
  }

  /** opfuncs[op_pt->op_state](op_pt) */
  private static opfunc(op_pt: Operator): void {
    switch (op_pt.op_state) {
      case OF_TYPE_ATT:
        Opl.operator_attack(op_pt);
        break;
      case OF_TYPE_DEC:
        Opl.operator_decay(op_pt);
        break;
      case OF_TYPE_REL:
        Opl.operator_release(op_pt);
        break;
      case OF_TYPE_SUS: // sustain phase (keeping level)
        Opl.operator_sustain(op_pt);
        break;
      case OF_TYPE_SUS_NOKEEP: // sustain_nokeep phase (release-style)
        Opl.operator_release(op_pt);
        break;
      default: // operator_off
        break;
    }
  }

  // ---- parameter changes ----

  private decrelmul(rate: number, toff: number): number {
    if (toff < 16) return this.decrelmulTable[rate * 16 + toff];
    const f = -7.4493 * decrelconst[toff & 3] * this.recipsamp;
    return exp2(f * Math.pow(2.0, rate + (toff >>> 2)));
  }

  private change_attackrate(regbase: number, op_pt: Operator): void {
    const attackrate = this.adlibreg[ARC_ATTR_DECR + regbase] >> 4;
    if (attackrate) {
      const f =
        Math.pow(2.0, attackrate + (op_pt.toff >>> 2) - 1) * attackconst[op_pt.toff & 3] * this.recipsamp;
      // attack rate coefficients
      op_pt.a0 = 0.0377 * f;
      op_pt.a1 = 10.73 * f + 1;
      op_pt.a2 = -17.57 * f;
      op_pt.a3 = 7.42 * f;

      const step_skip = attackrate * 4 + op_pt.toff;
      const steps = step_skip >> 2;
      op_pt.env_step_a = (1 << (steps <= 12 ? 12 - steps : 0)) - 1;

      const step_num = step_skip <= 48 ? 4 - (step_skip & 3) : 0;
      op_pt.env_step_skip_a = step_skip_mask[step_num];

      if (step_skip >= 62) {
        op_pt.a0 = 2.0; // something that triggers an immediate transition to amp:=1.0
        op_pt.a1 = 0.0;
        op_pt.a2 = 0.0;
        op_pt.a3 = 0.0;
      }
    } else {
      // attack disabled
      op_pt.a0 = 0.0;
      op_pt.a1 = 1.0;
      op_pt.a2 = 0.0;
      op_pt.a3 = 0.0;
      op_pt.env_step_a = 0;
      op_pt.env_step_skip_a = 0;
    }
  }

  private change_decayrate(regbase: number, op_pt: Operator): void {
    const decayrate = this.adlibreg[ARC_ATTR_DECR + regbase] & 15;
    // decaymul should be 1.0 when decayrate==0
    if (decayrate) {
      op_pt.decaymul = this.decrelmul(decayrate, op_pt.toff);
      const steps = (decayrate * 4 + op_pt.toff) >> 2;
      op_pt.env_step_d = (1 << (steps <= 12 ? 12 - steps : 0)) - 1;
    } else {
      op_pt.decaymul = 1.0;
      op_pt.env_step_d = 0;
    }
  }

  private change_releaserate(regbase: number, op_pt: Operator): void {
    const releaserate = this.adlibreg[ARC_SUSL_RELR + regbase] & 15;
    // releasemul should be 1.0 when releaserate==0
    if (releaserate) {
      op_pt.releasemul = this.decrelmul(releaserate, op_pt.toff);
      const steps = (releaserate * 4 + op_pt.toff) >> 2;
      op_pt.env_step_r = (1 << (steps <= 12 ? 12 - steps : 0)) - 1;
    } else {
      op_pt.releasemul = 1.0;
      op_pt.env_step_r = 0;
    }
  }

  private change_sustainlevel(regbase: number, op_pt: Operator): void {
    const sustainlevel = this.adlibreg[ARC_SUSL_RELR + regbase] >> 4;
    // sustainlevel should be 0.0 when sustainlevel==15 (max)
    if (sustainlevel < 15) {
      op_pt.sustain_level = sustainLevelTable[sustainlevel]; // pow(FL2,(fltype)sustainlevel * (-FL05))
    } else {
      op_pt.sustain_level = 0.0;
    }
  }

  private change_waveform(regbase: number, op_pt: Operator): void {
    // waveform selection
    op_pt.cur_wmask = wavemask[this.wave_sel[regbase]];
    op_pt.cur_wform = waveform[this.wave_sel[regbase]];
    // (might need to be adapted to waveform type here...)
  }

  private change_keepsustain(regbase: number, op_pt: Operator): void {
    op_pt.sus_keep = (this.adlibreg[ARC_TVS_KSR_MUL + regbase] & 0x20) > 0;
    if (op_pt.op_state === OF_TYPE_SUS) {
      if (!op_pt.sus_keep) op_pt.op_state = OF_TYPE_SUS_NOKEEP;
    } else if (op_pt.op_state === OF_TYPE_SUS_NOKEEP) {
      if (op_pt.sus_keep) op_pt.op_state = OF_TYPE_SUS;
    }
  }

  // enable/disable vibrato/tremolo LFO effects
  private change_vibrato(regbase: number, op_pt: Operator): void {
    op_pt.vibrato = (this.adlibreg[ARC_TVS_KSR_MUL + regbase] & 0x40) !== 0;
    op_pt.tremolo = (this.adlibreg[ARC_TVS_KSR_MUL + regbase] & 0x80) !== 0;
  }

  // change amount of self-feedback
  private change_feedback(chanbase: number, op_pt: Operator): void {
    const feedback = this.adlibreg[ARC_FEEDBACK + chanbase] & 14;
    if (feedback) op_pt.mfbi = Math.pow(2.0, (feedback >> 1) + 8) | 0;
    else op_pt.mfbi = 0;
  }

  private change_frequency(chanbase: number, regbase: number, op_pt: Operator): void {
    const reg = this.adlibreg;
    // frequency
    const frn = ((reg[ARC_KON_BNUM + chanbase] & 3) << 8) + reg[ARC_FREQ_NUM + chanbase];
    // block number/octave
    const oct = (reg[ARC_KON_BNUM + chanbase] >> 2) & 7;
    op_pt.freq_high = (frn >> 7) & 7;

    // keysplit
    const note_sel = (reg[8] >> 6) & 1;
    op_pt.toff = ((frn >> 9) & (note_sel ^ 1)) | ((frn >> 8) & note_sel);
    op_pt.toff += oct << 1;

    // envelope scaling (KSR)
    if (!(reg[ARC_TVS_KSR_MUL + regbase] & 0x10)) op_pt.toff >>>= 2;

    // 20+a0+b0:
    op_pt.tinc = (frn << oct) * this.frqmul[reg[ARC_TVS_KSR_MUL + regbase] & 15] >>> 0;
    // 40+a0+b0:
    const vol_in = (reg[ARC_KSL_OUTLEV + regbase] & 63) + kslmul[reg[ARC_KSL_OUTLEV + regbase] >> 6] * kslev[oct][frn >> 6];
    op_pt.vol = volTable[vol_in * 4]; // pow(FL2,(fltype)(vol_in * -0.125 - 14))

    // operator frequency changed, care about features that depend on it
    this.change_attackrate(regbase, op_pt);
    this.change_decayrate(regbase, op_pt);
    this.change_releaserate(regbase, op_pt);
  }

  private enable_operator(regbase: number, op_pt: Operator, act_type: number): void {
    // check if this is really an off-on transition
    if (op_pt.act_state === OP_ACT_OFF) {
      const wselbase = regbase;

      op_pt.tcount = (wavestart[this.wave_sel[wselbase]] * FIXEDPT) >>> 0;

      // start with attack mode
      op_pt.op_state = OF_TYPE_ATT;
      op_pt.act_state |= act_type;
    }
  }

  private static disable_operator(op_pt: Operator, act_type: number): void {
    // check if this is really an on-off transition
    if (op_pt.act_state !== OP_ACT_OFF) {
      op_pt.act_state &= ~act_type;
      if (op_pt.act_state === OP_ACT_OFF) {
        if (op_pt.op_state !== OF_TYPE_OFF) op_pt.op_state = OF_TYPE_REL;
      }
    }
  }

  // ---- public chip interface ----

  /** adlib_init: reset the chip for the given output sample rate. */
  init(samplerate: number): void {
    this.int_samplerate = samplerate;

    this.generator_add = (INTFREQU * FIXEDPT) / this.int_samplerate >>> 0;

    this.adlibreg.fill(0);
    this.wave_sel.fill(0);
    for (const o of this.op) o.reset();

    this.recipsamp = 1.0 / this.int_samplerate;
    for (let i = 15; i >= 0; i--) {
      this.frqmul[i] = ((frqmul_tab[i] * INTFREQU) / WAVEPREC) * FIXEDPT * this.recipsamp;
    }

    // decaymul/releasemul for every (rate, toff): pow(FL2, f*pow(FL2, rate+(toff>>2))) with
    // f = -7.4493*decrelconst[toff&3]*recipsamp. toff never exceeds 15 (1 + oct*2).
    for (let rate = 1; rate < 16; rate++) {
      for (let toff = 0; toff < 16; toff++) {
        const f = -7.4493 * decrelconst[toff & 3] * this.recipsamp;
        this.decrelmulTable[rate * 16 + toff] = exp2(f * Math.pow(2.0, rate + (toff >>> 2)));
      }
    }

    this.status = 0;

    // create vibrato table
    const vib_table = this.vib_table;
    vib_table[0] = 8;
    vib_table[1] = 4;
    vib_table[2] = 0;
    vib_table[3] = -4;
    for (let i = 4; i < VIBTAB_SIZE; i++) vib_table[i] = vib_table[i - 4] * -1;

    // vibrato at ~6.1 ?? (opl3 docs say 6.1, opl4 docs say 6.0, y8950 docs say 6.4)
    // VIBTAB_SIZE*FIXEDPT_LFO/8192 is integer math (= 16384) before the double multiply.
    this.vibtab_add = (((VIBTAB_SIZE * FIXEDPT_LFO) / 8192) * INTFREQU) / this.int_samplerate >>> 0;
    this.vibtab_pos = 0;

    this.vibval_const.fill(0);

    // create tremolo table
    const trem_table_int = new Int32Array(TREMTAB_SIZE);
    for (let i = 0; i < 14; i++) trem_table_int[i] = i - 13; // upwards (13 to 26 -> -0.5/6 to 0)
    for (let i = 14; i < 41; i++) trem_table_int[i] = -i + 14; // downwards (26 to 0 -> 0 to -1/6)
    for (let i = 41; i < 53; i++) trem_table_int[i] = i - 40 - 26; // upwards (1 to 12 -> -1/6 to -0.5/6)

    for (let i = 0; i < TREMTAB_SIZE; i++) {
      // 0.0 .. -26/26*4.8/6 == [0.0 .. -0.8], 4/53 steps == [1 .. 0.57]
      const trem_val1 = (((trem_table_int[i] * 4.8) / 26.0) / 6.0); // 4.8db
      const trem_val2 = ((Math.trunc(trem_table_int[i] / 4) * 1.2) / 6.0) / 6.0; // 1.2db (larger stepping)

      this.trem_table[i] = (exp2(trem_val1) * FIXEDPT) | 0;
      this.trem_table[TREMTAB_SIZE + i] = (exp2(trem_val2) * FIXEDPT) | 0;
    }

    // tremolo at 3.7hz
    this.tremtab_add = (TREMTAB_SIZE * TREM_FREQ * FIXEDPT_LFO) / this.int_samplerate >>> 0;
    this.tremtab_pos = 0;

    this.tremval_const.fill(FIXEDPT);
  }

  /** adlib_write: write `val` to register `idx`. */
  write(idx: number, val: number): void {
    idx &= 0xff;
    val &= 0xff;
    const op = this.op;
    this.adlibreg[idx] = val;

    switch (idx & 0xf0) {
      case ARC_CONTROL:
        if (idx === 0x04) {
          // IRQ reset, timer mask/start
          if (val & 0x80) {
            // clear IRQ bits in status register
            this.status &= ~0x60;
          } else {
            this.status = 0;
          }
        }
        break;
      case ARC_TVS_KSR_MUL:
      case ARC_TVS_KSR_MUL + 0x10: {
        // tremolo/vibrato/sustain keeping enabled; key scale rate; frequency multiplication
        const num = idx & 7;
        const base = (idx - ARC_TVS_KSR_MUL) & 0xff;
        if (num < 6 && base < 22) {
          const modop = regbase2modop[base];
          const regbase = base;
          const chanbase = modop;

          // change tremolo/vibrato and sustain keeping of this operator
          const op_ptr = op[modop + (num < 3 ? 0 : 9)];
          this.change_keepsustain(regbase, op_ptr);
          this.change_vibrato(regbase, op_ptr);

          // change frequency calculations of this operator as
          // key scale rate and frequency multiplicator can be changed
          this.change_frequency(chanbase, base, op_ptr);
        }
        break;
      }
      case ARC_KSL_OUTLEV:
      case ARC_KSL_OUTLEV + 0x10: {
        // key scale level; output rate
        const num = idx & 7;
        const base = (idx - ARC_KSL_OUTLEV) & 0xff;
        if (num < 6 && base < 22) {
          const modop = regbase2modop[base];
          const chanbase = modop;

          // change frequency calculations of this operator as
          // key scale level and output rate can be changed
          const op_ptr = op[modop + (num < 3 ? 0 : 9)];
          this.change_frequency(chanbase, base, op_ptr);
        }
        break;
      }
      case ARC_ATTR_DECR:
      case ARC_ATTR_DECR + 0x10: {
        // attack/decay rates
        const num = idx & 7;
        const base = (idx - ARC_ATTR_DECR) & 0xff;
        if (num < 6 && base < 22) {
          const regbase = base;

          // change attack rate and decay rate of this operator
          const op_ptr = op[regbase2op[base]];
          this.change_attackrate(regbase, op_ptr);
          this.change_decayrate(regbase, op_ptr);
        }
        break;
      }
      case ARC_SUSL_RELR:
      case ARC_SUSL_RELR + 0x10: {
        // sustain level; release rate
        const num = idx & 7;
        const base = (idx - ARC_SUSL_RELR) & 0xff;
        if (num < 6 && base < 22) {
          const regbase = base;

          // change sustain level and release rate of this operator
          const op_ptr = op[regbase2op[base]];
          this.change_releaserate(regbase, op_ptr);
          this.change_sustainlevel(regbase, op_ptr);
        }
        break;
      }
      case ARC_FREQ_NUM: {
        // 0xa0-0xa8 low8 frequency
        const base = (idx - ARC_FREQ_NUM) & 0xff;
        if (base < 9) {
          const opbase = base;
          // regbase of modulator:
          const modbase = modulatorbase[base];

          const chanbase = base;

          this.change_frequency(chanbase, modbase, op[opbase]);
          this.change_frequency(chanbase, modbase + 3, op[opbase + 9]);
        }
        break;
      }
      case ARC_KON_BNUM: {
        if (idx === ARC_PERC_MODE) {
          if ((val & 0x30) === 0x30) {
            // BassDrum active
            this.enable_operator(16, op[6], OP_ACT_PERC);
            this.change_frequency(6, 16, op[6]);
            this.enable_operator(16 + 3, op[6 + 9], OP_ACT_PERC);
            this.change_frequency(6, 16 + 3, op[6 + 9]);
          } else {
            Opl.disable_operator(op[6], OP_ACT_PERC);
            Opl.disable_operator(op[6 + 9], OP_ACT_PERC);
          }
          if ((val & 0x28) === 0x28) {
            // Snare active
            this.enable_operator(17 + 3, op[16], OP_ACT_PERC);
            this.change_frequency(7, 17 + 3, op[16]);
          } else {
            Opl.disable_operator(op[16], OP_ACT_PERC);
          }
          if ((val & 0x24) === 0x24) {
            // TomTom active
            this.enable_operator(18, op[8], OP_ACT_PERC);
            this.change_frequency(8, 18, op[8]);
          } else {
            Opl.disable_operator(op[8], OP_ACT_PERC);
          }
          if ((val & 0x22) === 0x22) {
            // Cymbal active
            this.enable_operator(18 + 3, op[8 + 9], OP_ACT_PERC);
            this.change_frequency(8, 18 + 3, op[8 + 9]);
          } else {
            Opl.disable_operator(op[8 + 9], OP_ACT_PERC);
          }
          if ((val & 0x21) === 0x21) {
            // Hihat active
            this.enable_operator(17, op[7], OP_ACT_PERC);
            this.change_frequency(7, 17, op[7]);
          } else {
            Opl.disable_operator(op[7], OP_ACT_PERC);
          }

          break;
        }
        // regular 0xb0-0xb8
        const base = (idx - ARC_KON_BNUM) & 0xff;
        if (base < 9) {
          const opbase = base;
          // regbase of modulator:
          const modbase = modulatorbase[base];

          if (val & 32) {
            // operator switched on
            this.enable_operator(modbase, op[opbase], OP_ACT_NORMAL); // modulator (if 2op)
            this.enable_operator(modbase + 3, op[opbase + 9], OP_ACT_NORMAL); // carrier (if 2op)
          } else {
            // operator switched off
            Opl.disable_operator(op[opbase], OP_ACT_NORMAL);
            Opl.disable_operator(op[opbase + 9], OP_ACT_NORMAL);
          }

          const chanbase = base;

          // change frequency calculations of modulator and carrier (2op) as
          // the frequency of the channel has changed
          this.change_frequency(chanbase, modbase, op[opbase]);
          this.change_frequency(chanbase, modbase + 3, op[opbase + 9]);
        }
        break;
      }
      case ARC_FEEDBACK: {
        // 0xc0-0xc8 feedback/modulation type (AM/FM)
        const base = (idx - ARC_FEEDBACK) & 0xff;
        if (base < 9) {
          const opbase = base;
          const chanbase = base;
          this.change_feedback(chanbase, op[opbase]);
        }
        break;
      }
      case ARC_WAVE_SEL:
      case ARC_WAVE_SEL + 0x10: {
        const num = idx & 7;
        const base = (idx - ARC_WAVE_SEL) & 0xff;
        if (num < 6 && base < 22) {
          if (this.adlibreg[0x01] & 0x20) {
            // wave selection enabled, change waveform
            this.wave_sel[base] = val & 3;
            const op_ptr = op[regbase2modop[base] + (num < 3 ? 0 : 9)];
            this.change_waveform(base, op_ptr);
          }
        }
        break;
      }
      default:
        break;
    }
  }

  /** adlib_reg_read */
  readReg(port: number): number {
    // opl2-detection routines require ret&6 to be 6
    if ((port & 1) === 0) {
      return this.status | 6;
    }
    return 0xff;
  }

  /**
   * adlib_getsample: render `numsamples` mono 16-bit samples into `sndptr` starting at `offset`.
   */
  getSample(sndptr: Int16Array, offset: number, numsamples: number): void {
    const op = this.op;
    const reg = this.adlibreg;
    const outbufl = this.outbufl;
    const vib_lut = this.vib_lut;
    const trem_lut = this.trem_lut;
    const vibval_const = this.vibval_const;
    const tremval_const = this.tremval_const;
    const vibval_var1 = this.vibval_var1;
    const vibval_var2 = this.vibval_var2;
    const output = Opl.operator_output;
    const opfunc = Opl.opfunc;

    let endsamples: number;
    let out = offset;

    for (let cursmp = 0; cursmp < numsamples; cursmp += endsamples) {
      endsamples = numsamples - cursmp;
      if (endsamples > BLOCKBUF_SIZE) endsamples = BLOCKBUF_SIZE;

      outbufl.fill(0, 0, endsamples);

      // vibrato/tremolo value table pointers
      let vibval1: Int32Array, vibval2: Int32Array, vibval3: Int32Array, vibval4: Int32Array;
      let tremval1: Int32Array, tremval2: Int32Array, tremval3: Int32Array, tremval4: Int32Array;

      // calculate vibrato/tremolo lookup tables
      const vib_tshift = (reg[ARC_PERC_MODE] & 0x40) === 0 ? 1 : 0; // 14cents/7cents switching
      for (let i = 0; i < endsamples; i++) {
        // cycle through vibrato table
        this.vibtab_pos = (this.vibtab_pos + this.vibtab_add) >>> 0;
        if (this.vibtab_pos / FIXEDPT_LFO >= VIBTAB_SIZE) this.vibtab_pos -= VIBTAB_SIZE * FIXEDPT_LFO;
        vib_lut[i] = this.vib_table[(this.vibtab_pos / FIXEDPT_LFO) | 0] >> vib_tshift; // 14cents (14/100 of a semitone) or 7cents

        // cycle through tremolo table
        this.tremtab_pos = (this.tremtab_pos + this.tremtab_add) >>> 0;
        if (this.tremtab_pos / FIXEDPT_LFO >= TREMTAB_SIZE) this.tremtab_pos -= TREMTAB_SIZE * FIXEDPT_LFO;
        if (reg[ARC_PERC_MODE] & 0x80) trem_lut[i] = this.trem_table[(this.tremtab_pos / FIXEDPT_LFO) | 0];
        else trem_lut[i] = this.trem_table[TREMTAB_SIZE + ((this.tremtab_pos / FIXEDPT_LFO) | 0)];
      }

      if (reg[ARC_PERC_MODE] & 0x20) {
        //BassDrum
        const c0 = op[6];
        const c9 = op[6 + 9];
        if (reg[ARC_FEEDBACK + 6] & 1) {
          // additive synthesis
          if (c9.op_state !== OF_TYPE_OFF) {
            if (c9.vibrato) {
              vibval1 = vibval_var1;
              for (let i = 0; i < endsamples; i++) vibval1[i] = vibval(vib_lut[i], c9.freq_high);
            } else vibval1 = vibval_const;
            if (c9.tremolo) tremval1 = trem_lut; // tremolo enabled, use table
            else tremval1 = tremval_const;

            // calculate channel output
            for (let i = 0; i < endsamples; i++) {
              this.operator_advance(c9, vibval1[i]);
              opfunc(c9);
              output(c9, 0, tremval1[i]);

              const chanval = c9.cval * 2;
              outbufl[i] += chanval;
            }
          }
        } else {
          // frequency modulation
          if (c9.op_state !== OF_TYPE_OFF || c0.op_state !== OF_TYPE_OFF) {
            if (c0.vibrato && c0.op_state !== OF_TYPE_OFF) {
              vibval1 = vibval_var1;
              for (let i = 0; i < endsamples; i++) vibval1[i] = vibval(vib_lut[i], c0.freq_high);
            } else vibval1 = vibval_const;
            if (c9.vibrato && c9.op_state !== OF_TYPE_OFF) {
              vibval2 = vibval_var2;
              for (let i = 0; i < endsamples; i++) vibval2[i] = vibval(vib_lut[i], c9.freq_high);
            } else vibval2 = vibval_const;
            if (c0.tremolo) tremval1 = trem_lut; // tremolo enabled, use table
            else tremval1 = tremval_const;
            if (c9.tremolo) tremval2 = trem_lut; // tremolo enabled, use table
            else tremval2 = tremval_const;

            // calculate channel output
            for (let i = 0; i < endsamples; i++) {
              this.operator_advance(c0, vibval1[i]);
              opfunc(c0);
              output(c0, Math.trunc(((c0.lastcval + c0.cval) * c0.mfbi) / 2), tremval1[i]);

              this.operator_advance(c9, vibval2[i]);
              opfunc(c9);
              output(c9, Math.imul(c0.cval, FIXEDPT), tremval2[i]);

              const chanval = c9.cval * 2;
              outbufl[i] += chanval;
            }
          }
        }

        //TomTom (j=8)
        if (op[8].op_state !== OF_TYPE_OFF) {
          const c = op[8];
          if (c.vibrato) {
            vibval3 = vibval_var1;
            for (let i = 0; i < endsamples; i++) vibval3[i] = vibval(vib_lut[i], c.freq_high);
          } else vibval3 = vibval_const;

          if (c.tremolo) tremval3 = trem_lut; // tremolo enabled, use table
          else tremval3 = tremval_const;

          // calculate channel output
          for (let i = 0; i < endsamples; i++) {
            this.operator_advance(c, vibval3[i]);
            opfunc(c); //TomTom
            output(c, 0, tremval3[i]);
            const chanval = c.cval * 2;
            outbufl[i] += chanval;
          }
        }

        //Snare/Hihat (j=7), Cymbal (j=8)
        if (op[7].op_state !== OF_TYPE_OFF || op[16].op_state !== OF_TYPE_OFF || op[17].op_state !== OF_TYPE_OFF) {
          let c0 = op[7];
          let c9 = op[7 + 9];
          if (c0.vibrato && c0.op_state !== OF_TYPE_OFF) {
            vibval1 = vibval_var1;
            for (let i = 0; i < endsamples; i++) vibval1[i] = vibval(vib_lut[i], c0.freq_high);
          } else vibval1 = vibval_const;
          // (sic: == OF_TYPE_OFF, as in the C)
          if (c9.vibrato && c9.op_state === OF_TYPE_OFF) {
            vibval2 = vibval_var2;
            for (let i = 0; i < endsamples; i++) vibval2[i] = vibval(vib_lut[i], c9.freq_high);
          } else vibval2 = vibval_const;

          if (c0.tremolo) tremval1 = trem_lut; // tremolo enabled, use table
          else tremval1 = tremval_const;
          if (c9.tremolo) tremval2 = trem_lut; // tremolo enabled, use table
          else tremval2 = tremval_const;

          c0 = op[8];
          c9 = op[8 + 9];
          if (c9.vibrato && c9.op_state === OF_TYPE_OFF) {
            vibval4 = vibval_var2;
            for (let i = 0; i < endsamples; i++) vibval4[i] = vibval(vib_lut[i], c9.freq_high);
          } else vibval4 = vibval_const;

          if (c9.tremolo) tremval4 = trem_lut; // tremolo enabled, use table
          else tremval4 = tremval_const;

          // calculate channel output
          for (let i = 0; i < endsamples; i++) {
            this.operator_advance_drums(op[7], vibval1[i], op[7 + 9], vibval2[i], op[8 + 9], vibval4[i]);

            opfunc(op[7]); //Hihat
            output(op[7], 0, tremval1[i]);

            opfunc(op[7 + 9]); //Snare
            output(op[7 + 9], 0, tremval2[i]);

            opfunc(op[8 + 9]); //Cymbal
            output(op[8 + 9], 0, tremval4[i]);

            const chanval = (op[7].cval + op[7 + 9].cval + op[8 + 9].cval) * 2;
            outbufl[i] += chanval;
          }
        }
      }

      const max_channel = NUM_CHANNELS;
      for (let cur_ch = max_channel - 1; cur_ch >= 0; cur_ch--) {
        // skip drum/percussion operators
        if (reg[ARC_PERC_MODE] & 0x20 && cur_ch >= 6 && cur_ch < 9) continue;

        const k = cur_ch;
        const c0 = op[cur_ch];
        const c9 = op[cur_ch + 9];

        // check for FM/AM
        if (reg[ARC_FEEDBACK + k] & 1) {
          // 2op additive synthesis
          if (c9.op_state === OF_TYPE_OFF && c0.op_state === OF_TYPE_OFF) continue;
          if (c0.vibrato && c0.op_state !== OF_TYPE_OFF) {
            vibval1 = vibval_var1;
            for (let i = 0; i < endsamples; i++) vibval1[i] = vibval(vib_lut[i], c0.freq_high);
          } else vibval1 = vibval_const;
          if (c9.vibrato && c9.op_state !== OF_TYPE_OFF) {
            vibval2 = vibval_var2;
            for (let i = 0; i < endsamples; i++) vibval2[i] = vibval(vib_lut[i], c9.freq_high);
          } else vibval2 = vibval_const;
          if (c0.tremolo) tremval1 = trem_lut; // tremolo enabled, use table
          else tremval1 = tremval_const;
          if (c9.tremolo) tremval2 = trem_lut; // tremolo enabled, use table
          else tremval2 = tremval_const;

          // calculate channel output
          for (let i = 0; i < endsamples; i++) {
            // carrier1
            this.operator_advance(c0, vibval1[i]);
            opfunc(c0);
            output(c0, Math.trunc(((c0.lastcval + c0.cval) * c0.mfbi) / 2), tremval1[i]);

            // carrier2
            this.operator_advance(c9, vibval2[i]);
            opfunc(c9);
            output(c9, 0, tremval2[i]);

            const chanval = c9.cval + c0.cval;
            outbufl[i] += chanval;
          }
        } else {
          // 2op frequency modulation
          if (c9.op_state === OF_TYPE_OFF && c0.op_state === OF_TYPE_OFF) continue;
          if (c0.vibrato && c0.op_state !== OF_TYPE_OFF) {
            vibval1 = vibval_var1;
            for (let i = 0; i < endsamples; i++) vibval1[i] = vibval(vib_lut[i], c0.freq_high);
          } else vibval1 = vibval_const;
          if (c9.vibrato && c9.op_state !== OF_TYPE_OFF) {
            vibval2 = vibval_var2;
            for (let i = 0; i < endsamples; i++) vibval2[i] = vibval(vib_lut[i], c9.freq_high);
          } else vibval2 = vibval_const;
          if (c0.tremolo) tremval1 = trem_lut; // tremolo enabled, use table
          else tremval1 = tremval_const;
          if (c9.tremolo) tremval2 = trem_lut; // tremolo enabled, use table
          else tremval2 = tremval_const;

          // calculate channel output
          for (let i = 0; i < endsamples; i++) {
            // modulator
            this.operator_advance(c0, vibval1[i]);
            opfunc(c0);
            output(c0, Math.trunc(((c0.lastcval + c0.cval) * c0.mfbi) / 2), tremval1[i]);

            // carrier
            this.operator_advance(c9, vibval2[i]);
            opfunc(c9);
            output(c9, Math.imul(c0.cval, FIXEDPT), tremval2[i]);

            const chanval = c9.cval;
            outbufl[i] += chanval;
          }
        }
      }

      // convert to 16bit samples
      for (let i = 0; i < endsamples; i++) sndptr[out++] = clipit16(outbufl[i]);
    }
  }
}
