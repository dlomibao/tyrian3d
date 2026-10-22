/*
 * OpenTyrian: A modern cross-platform port of Tyrian
 * Copyright (C) The OpenTyrian Development Team
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */

/*
 * TypeScript port of OpenTyrian's src/lds_play.c, the Loudness Sound System (LDS) song player
 * ("A substantial amount of this code has been copied and adapted from adplug").
 *
 * The C keeps its state in unsigned char / unsigned short fields and leans on their wrap-around,
 * so every store below is masked to the C field's width (`& 0xff`, `& 0xffff`). Out-of-range
 * reads that the C would do on malformed data (instrument numbers past the bank, negative note
 * indices) return 0 here instead of reading neighbouring memory; Tyrian's songs don't hit them.
 */

import type { Opl } from "./opl";

const op_table = [0x00, 0x01, 0x02, 0x08, 0x09, 0x0a, 0x10, 0x11, 0x12];

/* Note frequency table (16 notes / octave) */
// prettier-ignore
const frequency = [
  343, 344, 345, 347, 348, 349, 350, 352, 353, 354, 356, 357, 358,
  359, 361, 362, 363, 365, 366, 367, 369, 370, 371, 373, 374, 375,
  377, 378, 379, 381, 382, 384, 385, 386, 388, 389, 391, 392, 393,
  395, 396, 398, 399, 401, 402, 403, 405, 406, 408, 409, 411, 412,
  414, 415, 417, 418, 420, 421, 423, 424, 426, 427, 429, 430, 432,
  434, 435, 437, 438, 440, 442, 443, 445, 446, 448, 450, 451, 453,
  454, 456, 458, 459, 461, 463, 464, 466, 468, 469, 471, 473, 475,
  476, 478, 480, 481, 483, 485, 487, 488, 490, 492, 494, 496, 497,
  499, 501, 503, 505, 506, 508, 510, 512, 514, 516, 518, 519, 521,
  523, 525, 527, 529, 531, 533, 535, 537, 538, 540, 542, 544, 546,
  548, 550, 552, 554, 556, 558, 560, 562, 564, 566, 568, 571, 573,
  575, 577, 579, 581, 583, 585, 587, 589, 591, 594, 596, 598, 600,
  602, 604, 607, 609, 611, 613, 615, 618, 620, 622, 624, 627, 629,
  631, 633, 636, 638, 640, 643, 645, 647, 650, 652, 654, 657, 659,
  662, 664, 666, 669, 671, 674, 676, 678, 681, 683,
];

/* Vibrato (sine) table */
// prettier-ignore
const vibtab = [
  0, 13, 25, 37, 50, 62, 74, 86, 98, 109, 120, 131, 142, 152, 162,
  171, 180, 189, 197, 205, 212, 219, 225, 231, 236, 240, 244, 247,
  250, 252, 254, 255, 255, 255, 254, 252, 250, 247, 244, 240, 236,
  231, 225, 219, 212, 205, 197, 189, 180, 171, 162, 152, 142, 131,
  120, 109, 98, 86, 74, 62, 50, 37, 25, 13,
];

/* Tremolo (sine * sine) table */
// prettier-ignore
const tremtab = [
  0, 0, 1, 1, 2, 4, 5, 7, 10, 12, 15, 18, 21, 25, 29, 33, 37, 42, 47,
  52, 57, 62, 67, 73, 79, 85, 90, 97, 103, 109, 115, 121, 128, 134,
  140, 146, 152, 158, 165, 170, 176, 182, 188, 193, 198, 203, 208,
  213, 218, 222, 226, 230, 234, 237, 240, 243, 245, 248, 250, 251,
  253, 254, 254, 255, 255, 255, 254, 254, 253, 251, 250, 248, 245,
  243, 240, 237, 234, 230, 226, 222, 218, 213, 208, 203, 198, 193,
  188, 182, 176, 170, 165, 158, 152, 146, 140, 134, 127, 121, 115,
  109, 103, 97, 90, 85, 79, 73, 67, 62, 57, 52, 47, 42, 37, 33, 29,
  25, 21, 18, 15, 12, 10, 7, 5, 4, 2, 1, 1, 0,
];

const maxsound = 0x3f;
const maxpos = 0xff;

/** frequency[idx], or 0 where the C would read outside the table. */
function freqAt(idx: number): number {
  return frequency[idx] ?? 0;
}

/** An instrument (SoundBank in the C). All fields are unsigned char unless noted. */
interface SoundBank {
  mod_misc: number;
  mod_vol: number;
  mod_ad: number;
  mod_sr: number;
  mod_wave: number;
  car_misc: number;
  car_vol: number;
  car_ad: number;
  car_sr: number;
  car_wave: number;
  feedback: number;
  keyoff: number;
  portamento: number;
  glide: number;
  finetune: number;
  vibrato: number;
  vibdelay: number;
  mod_trem: number;
  car_trem: number;
  tremwait: number;
  arpeggio: number;
  arp_tab: Uint8Array; // [12]
  start: number; // unsigned short
  size: number; // unsigned short
  fms: number;
  transp: number; // unsigned short
  midinst: number;
  midvelo: number;
  midkey: number;
  midtrans: number;
  middum1: number;
  middum2: number;
}

const EMPTY_SOUNDBANK: SoundBank = {
  mod_misc: 0, mod_vol: 0, mod_ad: 0, mod_sr: 0, mod_wave: 0,
  car_misc: 0, car_vol: 0, car_ad: 0, car_sr: 0, car_wave: 0,
  feedback: 0, keyoff: 0, portamento: 0, glide: 0, finetune: 0,
  vibrato: 0, vibdelay: 0, mod_trem: 0, car_trem: 0, tremwait: 0,
  arpeggio: 0, arp_tab: new Uint8Array(12), start: 0, size: 0, fms: 0, transp: 0,
  midinst: 0, midvelo: 0, midkey: 0, midtrans: 0, middum1: 0, middum2: 0,
};

/** Channel state. unsigned short: gototune, lasttune, packpos, chancheat_high; others unsigned char. */
class Channel {
  gototune = 0;
  lasttune = 0;
  packpos = 0;
  finetune = 0;
  glideto = 0;
  portspeed = 0;
  nextvol = 0;
  volmod = 0;
  volcar = 0;
  vibwait = 0;
  vibspeed = 0;
  vibrate = 0;
  trmstay = 0;
  trmwait = 0;
  trmspeed = 0;
  trmrate = 0;
  trmcount = 0;
  trcwait = 0;
  trcspeed = 0;
  trcrate = 0;
  trccount = 0;
  arp_size = 0;
  arp_speed = 0;
  keycount = 0;
  vibcount = 0;
  arp_pos = 0;
  arp_count = 0;
  packwait = 0;
  readonly arp_tab = new Uint8Array(12);
  chancheat_chandelay = 0;
  chancheat_sound = 0;
  chancheat_high = 0;

  /**
   * c->arp_tab[idx]. arp_pos can reach 14 (arp_size is 4 bits), and in the C struct layout the
   * bytes after arp_tab[11] are one padding byte (always 0) then chancheat.chandelay and
   * chancheat.sound, so reproduce that.
   */
  arpTab(idx: number): number {
    if (idx < 12) return this.arp_tab[idx];
    if (idx === 13) return this.chancheat_chandelay;
    if (idx === 14) return this.chancheat_sound;
    return 0;
  }

  /** memset(channel, 0) */
  clear(): void {
    this.gototune = this.lasttune = this.packpos = 0;
    this.finetune = this.glideto = this.portspeed = this.nextvol = this.volmod = this.volcar = 0;
    this.vibwait = this.vibspeed = this.vibrate = 0;
    this.trmstay = this.trmwait = this.trmspeed = this.trmrate = this.trmcount = 0;
    this.trcwait = this.trcspeed = this.trcrate = this.trccount = 0;
    this.arp_size = this.arp_speed = this.keycount = this.vibcount = this.arp_pos = this.arp_count = 0;
    this.packwait = 0;
    this.arp_tab.fill(0);
    this.chancheat_chandelay = this.chancheat_sound = this.chancheat_high = 0;
  }
}

/** Little-endian reader mirroring memreader.c (reads past the end yield 0 and set `error`). */
class MemReader {
  pos = 0;
  error = false;
  constructor(private readonly data: Uint8Array) {}
  get size(): number {
    return this.data.length - this.pos;
  }
  u8(): number {
    if (this.error || this.size < 1) {
      this.error = true;
      return 0;
    }
    return this.data[this.pos++];
  }
  u16(): number {
    if (this.error || this.size < 2) {
      this.error = true;
      return 0;
    }
    const v = this.data[this.pos] | (this.data[this.pos + 1] << 8);
    this.pos += 2;
    return v;
  }
  skip(n: number): void {
    if (this.error || this.size < n) {
      this.error = true;
      return;
    }
    this.pos += n;
  }
}

/** The LDS player, driving an OPL chip. One instance per chip (the C uses globals). */
export class LdsPlayer {
  private soundbank: SoundBank[] = [];
  private readonly channel: Channel[] = Array.from({ length: 9 }, () => new Channel());
  private positions: { patnum: number; transpose: number }[] | null = null;
  private patterns = new Uint16Array(0);

  private readonly fmchip = new Uint8Array(0xff);
  /** Set by the 0xf9 jump command; never read (as in the C). */
  jumping = 0;
  private fadeonoff = 0;
  private allvolume = 0;
  private hardfade = 0;
  private tempo_now = 0;
  private pattplay = 0;
  private tempo = 0;
  private regbd = 0;
  private readonly chandelay = new Uint8Array(9);
  private mode = 0;
  private pattlen = 0;
  private posplay = 0; // Uint16
  private jumppos = 0; // Uint16
  /** Header speed field (Uint16); unused by the player, as in the C. */
  speed = 0;
  private numpatch = 0; // Uint16
  private numposi = 0; // Uint16
  private mainvolume = 0; // Uint16

  playing = false;
  songlooped = false;

  constructor(private readonly opl: Opl) {}

  /** lds_load: parse one song and rewind. Returns false if the header's mode is unsupported. */
  load(data: Uint8Array): boolean {
    const reader = new MemReader(data);

    /* load header */
    this.mode = reader.u8();
    if (this.mode > 2) return false;
    this.speed = reader.u16();
    this.tempo = reader.u8();
    this.pattlen = reader.u8();
    for (let i = 0; i < 9; i++) this.chandelay[i] = reader.u8();
    this.regbd = reader.u8();

    /* load patches */
    this.numpatch = reader.u16();

    this.soundbank = [];
    for (let i = 0; i < this.numpatch; i++) {
      const sb: SoundBank = {
        mod_misc: reader.u8(),
        mod_vol: reader.u8(),
        mod_ad: reader.u8(),
        mod_sr: reader.u8(),
        mod_wave: reader.u8(),
        car_misc: reader.u8(),
        car_vol: reader.u8(),
        car_ad: reader.u8(),
        car_sr: reader.u8(),
        car_wave: reader.u8(),
        feedback: reader.u8(),
        keyoff: reader.u8(),
        portamento: reader.u8(),
        glide: reader.u8(),
        finetune: reader.u8(),
        vibrato: reader.u8(),
        vibdelay: reader.u8(),
        mod_trem: reader.u8(),
        car_trem: reader.u8(),
        tremwait: reader.u8(),
        arpeggio: reader.u8(),
        arp_tab: new Uint8Array(12),
        start: 0,
        size: 0,
        fms: 0,
        transp: 0,
        midinst: 0,
        midvelo: 0,
        midkey: 0,
        midtrans: 0,
        middum1: 0,
        middum2: 0,
      };
      for (let j = 0; j < 12; j++) sb.arp_tab[j] = reader.u8();
      sb.start = reader.u16();
      sb.size = reader.u16();
      sb.fms = reader.u8();
      sb.transp = reader.u16();
      sb.midinst = reader.u8();
      sb.midvelo = reader.u8();
      sb.midkey = reader.u8();
      sb.midtrans = reader.u8();
      sb.middum1 = reader.u8();
      sb.middum2 = reader.u8();
      this.soundbank.push(sb);
    }

    /* load positions */
    this.numposi = reader.u16();

    const positions: { patnum: number; transpose: number }[] = [];
    for (let i = 0; i < this.numposi; i++) {
      for (let j = 0; j < 9; j++) {
        /*
         * patnum is a pointer inside the pattern space, but patterns are 16bit
         * word fields anyway, so it ought to be an even number (hopefully) and
         * we can just divide it by 2 to get our array index of 16bit words.
         */
        const patnum = reader.u16();
        const transpose = reader.u8();
        positions.push({ patnum: patnum >> 1, transpose });
      }
    }
    this.positions = positions;

    /* load patterns */
    reader.skip(2); /* ignore # of digital sounds */

    const numpatterns = reader.size >> 1;
    this.patterns = new Uint16Array(numpatterns);
    for (let i = 0; i < numpatterns; i++) this.patterns[i] = reader.u16();

    this.rewind();

    return true;
  }

  /** lds_rewind: restart the song from the top and reset the OPL. */
  rewind(): void {
    /* init all with 0 */
    this.tempo_now = 3;
    this.playing = true;
    this.songlooped = false;
    this.jumping = this.fadeonoff = this.allvolume = this.hardfade = this.pattplay = 0;
    this.posplay = this.jumppos = this.mainvolume = 0;
    for (const c of this.channel) c.clear();
    this.fmchip.fill(0);

    const opl = this.opl;
    /* OPL2 init */
    opl.init(opl.sampleRate); /* Reset OPL chip */
    opl.write(1, 0x20);
    opl.write(8, 0);
    opl.write(0xbd, this.regbd);

    for (let i = 0; i < 9; i++) {
      opl.write(0x20 + op_table[i], 0);
      opl.write(0x23 + op_table[i], 0);
      opl.write(0x40 + op_table[i], 0x3f);
      opl.write(0x43 + op_table[i], 0x3f);
      opl.write(0x60 + op_table[i], 0xff);
      opl.write(0x63 + op_table[i], 0xff);
      opl.write(0x80 + op_table[i], 0xff);
      opl.write(0x83 + op_table[i], 0xff);
      opl.write(0xe0 + op_table[i], 0);
      opl.write(0xe3 + op_table[i], 0);
      opl.write(0xa0 + i, 0);
      opl.write(0xb0 + i, 0);
      opl.write(0xc0 + i, 0);
    }
  }

  /** lds_fade */
  fade(speed: number): void {
    this.fadeonoff = speed & 0xff;
  }

  /** lds_setregs */
  private setregs(reg: number, val: number): void {
    reg &= 0xff;
    val &= 0xff;
    if (this.fmchip[reg] === val) return;

    this.fmchip[reg] = val;
    this.opl.write(reg, val);
  }

  /** lds_setregs_adv */
  private setregs_adv(reg: number, mask: number, val: number): void {
    reg &= 0xff;
    this.setregs(reg, (this.fmchip[reg] & mask) | (val & 0xff));
  }

  /** lds_update: advance the song by one tick. Returns false once the song stopped or looped. */
  update(): boolean {
    let comword: number, freq: number, octave: number, tune: number, wibc: number, tremc: number, arpreg: number;
    let vbreak: boolean;
    let level: number, regnum: number, comhi: number, comlo: number;

    if (!this.playing) return false;

    /* handle fading */
    if (this.fadeonoff) {
      if (this.fadeonoff <= 128) {
        if (this.allvolume > this.fadeonoff || this.allvolume === 0) {
          this.allvolume = (this.allvolume - this.fadeonoff) & 0xff;
        } else {
          this.allvolume = 1;
          this.fadeonoff = 0;
          if (this.hardfade !== 0) {
            this.playing = false;
            this.hardfade = 0;
            for (let i = 0; i < 9; i++) {
              this.channel[i].keycount = 1;
            }
          }
        }
      } else {
        if (((this.allvolume + (0x100 - this.fadeonoff)) & 0xff) <= this.mainvolume) {
          this.allvolume = (this.allvolume + 0x100 - this.fadeonoff) & 0xff;
        } else {
          this.allvolume = this.mainvolume & 0xff;
          this.fadeonoff = 0;
        }
      }
    }

    /* handle channel delay */
    for (let chan = 0; chan < 9; chan++) {
      const c = this.channel[chan];
      if (c.chancheat_chandelay) {
        c.chancheat_chandelay = (c.chancheat_chandelay - 1) & 0xff;
        if (!c.chancheat_chandelay) {
          this.playsound(c.chancheat_sound, chan, c.chancheat_high);
        }
      }
    }

    /* handle notes */
    const positions = this.positions;
    if (!this.tempo_now && positions) {
      vbreak = false;
      for (let chan = 0; chan < 9; chan++) {
        const c = this.channel[chan];
        if (!c.packwait) {
          const pos = positions[this.posplay * 9 + chan] ?? { patnum: 0, transpose: 0 };
          const patnum = pos.patnum;
          const transpose = pos.transpose;

          comword = this.patterns[patnum + c.packpos] ?? 0;
          comhi = comword >> 8;
          comlo = comword & 0xff;
          if (comword) {
            if (comhi === 0x80) {
              c.packwait = comlo;
            } else {
              if (comhi >= 0x80) {
                switch (comhi) {
                  case 0xff:
                    c.volcar = (((c.volcar & 0x3f) * comlo) >> 6) & 0x3f;
                    if (this.fmchip[0xc0 + chan] & 1) c.volmod = (((c.volmod & 0x3f) * comlo) >> 6) & 0x3f;
                    break;

                  case 0xfe:
                    this.tempo = comword & 0x3f;
                    break;

                  case 0xfd:
                    c.nextvol = comlo;
                    break;

                  case 0xfc:
                    this.playing = false;
                    /* in real player there's also full keyoff here, but we don't need it */
                    break;

                  case 0xfb:
                    c.keycount = 1;
                    break;

                  case 0xfa:
                    vbreak = true;
                    this.jumppos = (this.posplay + 1) & maxpos;
                    break;

                  case 0xf9:
                    vbreak = true;
                    this.jumppos = comlo & maxpos;
                    this.jumping = 1;
                    if (this.jumppos < this.posplay) {
                      this.songlooped = true;
                    }
                    break;

                  case 0xf8:
                    c.lasttune = 0;
                    break;

                  case 0xf7:
                    c.vibwait = 0;
                    /* PASCAL: c->vibspeed = ((comlo >> 4) & 15) + 2; */
                    c.vibspeed = ((comlo >> 4) + 2) & 0xff;
                    c.vibrate = ((comlo & 15) + 1) & 0xff;
                    break;

                  case 0xf6:
                    c.glideto = comlo;
                    break;

                  case 0xf5:
                    c.finetune = comlo;
                    break;

                  case 0xf4:
                    if (!this.hardfade) {
                      this.allvolume = this.mainvolume = comlo;
                      this.fadeonoff = 0;
                    }
                    break;

                  case 0xf3:
                    if (!this.hardfade) {
                      this.fadeonoff = comlo;
                    }
                    break;

                  case 0xf2:
                    c.trmstay = comlo;
                    break;

                  case 0xf1: /* panorama */
                  case 0xf0: /* progch */
                    /* MIDI commands (unhandled) */
                    break;

                  default:
                    if (comhi < 0xa0) {
                      c.glideto = comhi & 0x1f;
                    }
                    break;
                }
              } else {
                let sound: number;
                let high: number;
                /*
                 * Originally, in assembler code, the player first shifted
                 * logically left the transpose byte by 1 and then shifted
                 * arithmetically right the same byte to achieve the final,
                 * signed transpose value. (Sint8 transp = transpose & 127, with
                 * bit 6 copied into bit 7.)
                 */
                let transp = transpose & 127;
                if (transpose & 64) {
                  transp |= 128;
                }
                transp = (transp << 24) >> 24; // Sint8

                if (transpose & 128) {
                  sound = (comlo + transp) & maxsound;
                  high = (comhi << 4) & 0xffff;
                } else {
                  sound = comlo & maxsound;
                  high = ((comhi + transp) << 4) & 0xffff;
                }

                /*
                PASCAL:
                  sound = comlo & maxsound;
                  high = (comhi + (((transpose + 0x24) & 0xff) - 0x24)) << 4;
                */

                if (!this.chandelay[chan]) {
                  this.playsound(sound, chan, high);
                } else {
                  c.chancheat_chandelay = this.chandelay[chan];
                  c.chancheat_sound = sound;
                  c.chancheat_high = high;
                }
              }
            }
          }

          c.packpos = (c.packpos + 1) & 0xffff;
        } else {
          c.packwait = (c.packwait - 1) & 0xff;
        }
      }

      this.tempo_now = this.tempo;
      /*
        The continue table is updated here, but this is only used in the
        original player, which can be paused in the middle of a song and then
        unpaused. Since AdPlug does all this for us automatically, we don't
        have a continue table here.
      */
      this.pattplay = (this.pattplay + 1) & 0xff;
      if (vbreak) {
        this.pattplay = 0;
        for (let i = 0; i < 9; i++) {
          this.channel[i].packpos = this.channel[i].packwait = 0;
        }
        this.posplay = this.jumppos;
      } else {
        if (this.pattplay >= this.pattlen) {
          this.pattplay = 0;
          for (let i = 0; i < 9; i++) {
            this.channel[i].packpos = this.channel[i].packwait = 0;
          }
          this.posplay = (this.posplay + 1) & maxpos;
        }
      }
    } else {
      this.tempo_now = (this.tempo_now - 1) & 0xff;
    }

    /* make effects */
    for (let chan = 0; chan < 9; chan++) {
      const c = this.channel[chan];
      regnum = op_table[chan];
      if (c.keycount > 0) {
        if (c.keycount === 1) this.setregs_adv(0xb0 + chan, 0xdf, 0);
        c.keycount = (c.keycount - 1) & 0xff;
      }

      /* arpeggio */
      if (c.arp_size === 0) arpreg = 0;
      else {
        arpreg = (c.arpTab(c.arp_pos) << 4) & 0xffff;
        if (arpreg === 0x800) {
          if (c.arp_pos > 0) c.arp_tab[0] = c.arpTab(c.arp_pos - 1);
          c.arp_size = 1;
          c.arp_pos = 0;
          arpreg = (c.arp_tab[0] << 4) & 0xffff;
        }

        if (c.arp_count === c.arp_speed) {
          c.arp_pos = (c.arp_pos + 1) & 0xff;
          if (c.arp_pos >= c.arp_size) c.arp_pos = 0;
          c.arp_count = 0;
        } else c.arp_count = (c.arp_count + 1) & 0xff;
      }

      /* glide & portamento */
      if (c.lasttune && c.lasttune !== c.gototune) {
        if (c.lasttune > c.gototune) {
          if (c.lasttune - c.gototune < c.portspeed) c.lasttune = c.gototune;
          else c.lasttune = (c.lasttune - c.portspeed) & 0xffff;
        } else {
          if (c.gototune - c.lasttune < c.portspeed) c.lasttune = c.gototune;
          else c.lasttune = (c.lasttune + c.portspeed) & 0xffff;
        }

        if (arpreg >= 0x800) arpreg = (c.lasttune - (arpreg ^ 0xff0) - 16) & 0xffff;
        else arpreg = (arpreg + c.lasttune) & 0xffff;

        freq = freqAt(arpreg % (12 * 16));
        octave = ((arpreg / (12 * 16)) | 0) - 1;
        this.setregs(0xa0 + chan, freq & 0xff);
        this.setregs_adv(0xb0 + chan, 0x20, (((octave & 0xffff) << 2) + (freq >> 8)) & 0xdf);
      } else {
        /* vibrato */
        if (!c.vibwait) {
          if (c.vibrate) {
            wibc = (vibtab[c.vibcount & 0x3f] * c.vibrate) & 0xffff;

            if ((c.vibcount & 0x40) === 0) tune = (c.lasttune + (wibc >> 8)) & 0xffff;
            else tune = (c.lasttune - (wibc >> 8)) & 0xffff;

            if (arpreg >= 0x800) tune = (tune - (arpreg ^ 0xff0) - 16) & 0xffff;
            else tune = (tune + arpreg) & 0xffff;

            freq = freqAt(tune % (12 * 16));
            octave = ((tune / (12 * 16)) | 0) - 1;
            this.setregs(0xa0 + chan, freq & 0xff);
            this.setregs_adv(0xb0 + chan, 0x20, (((octave & 0xffff) << 2) + (freq >> 8)) & 0xdf);
            c.vibcount = (c.vibcount + c.vibspeed) & 0xff;
          } else if (c.arp_size !== 0) {
            /* no vibrato, just arpeggio */
            if (arpreg >= 0x800) tune = (c.lasttune - (arpreg ^ 0xff0) - 16) & 0xffff;
            else tune = (c.lasttune + arpreg) & 0xffff;

            freq = freqAt(tune % (12 * 16));
            octave = ((tune / (12 * 16)) | 0) - 1;
            this.setregs(0xa0 + chan, freq & 0xff);
            this.setregs_adv(0xb0 + chan, 0x20, (((octave & 0xffff) << 2) + (freq >> 8)) & 0xdf);
          }
        } else {
          /* no vibrato, just arpeggio */
          c.vibwait = (c.vibwait - 1) & 0xff;

          if (c.arp_size !== 0) {
            if (arpreg >= 0x800) tune = (c.lasttune - (arpreg ^ 0xff0) - 16) & 0xffff;
            else tune = (c.lasttune + arpreg) & 0xffff;

            freq = freqAt(tune % (12 * 16));
            octave = ((tune / (12 * 16)) | 0) - 1;
            this.setregs(0xa0 + chan, freq & 0xff);
            this.setregs_adv(0xb0 + chan, 0x20, (((octave & 0xffff) << 2) + (freq >> 8)) & 0xdf);
          }
        }
      }

      const allvolume = this.allvolume;
      const fmchip = this.fmchip;

      /* tremolo (modulator) */
      if (!c.trmwait) {
        if (c.trmrate) {
          tremc = (tremtab[c.trmcount & 0x7f] * c.trmrate) & 0xffff;
          if (tremc >> 8 <= (c.volmod & 0x3f)) level = ((c.volmod & 0x3f) - (tremc >> 8)) & 0xff;
          else level = 0;

          if (allvolume !== 0 && fmchip[0xc0 + chan] & 1)
            this.setregs_adv(0x40 + regnum, 0xc0, ((level * allvolume) >> 8) ^ 0x3f);
          else this.setregs_adv(0x40 + regnum, 0xc0, level ^ 0x3f);

          c.trmcount = (c.trmcount + c.trmspeed) & 0xff;
        } else if (allvolume !== 0 && fmchip[0xc0 + chan] & 1)
          this.setregs_adv(0x40 + regnum, 0xc0, ((((c.volmod & 0x3f) * allvolume) >> 8) ^ 0x3f) & 0x3f);
        else this.setregs_adv(0x40 + regnum, 0xc0, (c.volmod ^ 0x3f) & 0x3f);
      } else {
        c.trmwait = (c.trmwait - 1) & 0xff;
        if (allvolume !== 0 && fmchip[0xc0 + chan] & 1)
          this.setregs_adv(0x40 + regnum, 0xc0, ((((c.volmod & 0x3f) * allvolume) >> 8) ^ 0x3f) & 0x3f);
      }

      /* tremolo (carrier) */
      if (!c.trcwait) {
        if (c.trcrate) {
          tremc = (tremtab[c.trccount & 0x7f] * c.trcrate) & 0xffff;
          if (tremc >> 8 <= (c.volcar & 0x3f)) level = ((c.volcar & 0x3f) - (tremc >> 8)) & 0xff;
          else level = 0;

          if (allvolume !== 0) this.setregs_adv(0x43 + regnum, 0xc0, ((level * allvolume) >> 8) ^ 0x3f);
          else this.setregs_adv(0x43 + regnum, 0xc0, level ^ 0x3f);
          c.trccount = (c.trccount + c.trcspeed) & 0xff;
        } else if (allvolume !== 0)
          this.setregs_adv(0x43 + regnum, 0xc0, ((((c.volcar & 0x3f) * allvolume) >> 8) ^ 0x3f) & 0x3f);
        else this.setregs_adv(0x43 + regnum, 0xc0, (c.volcar ^ 0x3f) & 0x3f);
      } else {
        c.trcwait = (c.trcwait - 1) & 0xff;
        if (allvolume !== 0)
          this.setregs_adv(0x43 + regnum, 0xc0, ((((c.volcar & 0x3f) * allvolume) >> 8) ^ 0x3f) & 0x3f);
      }
    }

    return !this.playing || this.songlooped ? false : true;
  }

  /** lds_playsound */
  private playsound(inst_number: number, channel_number: number, tunehigh: number): void {
    const c = this.channel[channel_number]; /* current channel */
    const i = this.soundbank[inst_number] ?? EMPTY_SOUNDBANK; /* current instrument */
    const regnum = op_table[channel_number]; /* channel's OPL2 register */
    let volcalc: number;

    /* set fine tune */
    tunehigh += ((i.finetune + c.finetune + 0x80) & 0xff) - 0x80;

    /* arpeggio handling */
    if (!i.arpeggio) {
      const arpcalc = (i.arp_tab[0] << 4) & 0xffff;

      if (arpcalc > 0x800) tunehigh = tunehigh - (arpcalc ^ 0xff0) - 16;
      else tunehigh += arpcalc;
    }

    /* glide handling */
    if (c.glideto !== 0) {
      c.gototune = tunehigh & 0xffff;
      c.portspeed = c.glideto;
      c.glideto = c.finetune = 0;
      return;
    }

    /* set modulator registers */
    this.setregs(0x20 + regnum, i.mod_misc);
    volcalc = i.mod_vol;
    if (!c.nextvol || !(i.feedback & 1)) c.volmod = volcalc;
    else c.volmod = ((volcalc & 0xc0) | (((volcalc & 0x3f) * c.nextvol) >> 6)) & 0xff;

    if ((i.feedback & 1) === 1 && this.allvolume !== 0)
      this.setregs(0x40 + regnum, ((c.volmod & 0xc0) | (((c.volmod & 0x3f) * this.allvolume) >> 8)) ^ 0x3f);
    else this.setregs(0x40 + regnum, c.volmod ^ 0x3f);
    this.setregs(0x60 + regnum, i.mod_ad);
    this.setregs(0x80 + regnum, i.mod_sr);
    this.setregs(0xe0 + regnum, i.mod_wave);

    /* Set carrier registers */
    this.setregs(0x23 + regnum, i.car_misc);
    volcalc = i.car_vol;
    if (!c.nextvol) c.volcar = volcalc;
    else c.volcar = ((volcalc & 0xc0) | (((volcalc & 0x3f) * c.nextvol) >> 6)) & 0xff;

    if (this.allvolume)
      this.setregs(0x43 + regnum, ((c.volcar & 0xc0) | (((c.volcar & 0x3f) * this.allvolume) >> 8)) ^ 0x3f);
    else this.setregs(0x43 + regnum, c.volcar ^ 0x3f);
    this.setregs(0x63 + regnum, i.car_ad);
    this.setregs(0x83 + regnum, i.car_sr);
    this.setregs(0xe3 + regnum, i.car_wave);
    this.setregs(0xc0 + channel_number, i.feedback);
    this.setregs_adv(0xb0 + channel_number, 0xdf, 0); /* key off */

    // C: % and / on int truncate toward zero; JS % matches, `| 0` truncates the division.
    const freq = freqAt(tunehigh % (12 * 16));
    const octave = (((tunehigh / (12 * 16)) | 0) - 1) & 0xff;
    if (!i.glide) {
      if (!i.portamento || !c.lasttune) {
        this.setregs(0xa0 + channel_number, freq & 0xff);
        this.setregs(0xb0 + channel_number, (octave << 2) + 0x20 + (freq >> 8));
        c.lasttune = c.gototune = tunehigh & 0xffff;
      } else {
        c.gototune = tunehigh & 0xffff;
        c.portspeed = i.portamento;
        this.setregs_adv(0xb0 + channel_number, 0xdf, 0x20); /* key on */
      }
    } else {
      this.setregs(0xa0 + channel_number, freq & 0xff);
      this.setregs(0xb0 + channel_number, (octave << 2) + 0x20 + (freq >> 8));
      c.lasttune = tunehigh & 0xffff;
      c.gototune = (tunehigh + ((i.glide + 0x80) & 0xff) - 0x80) & 0xffff; /* set destination */
      c.portspeed = i.portamento;
    }

    if (!i.vibrato) c.vibwait = c.vibspeed = c.vibrate = 0;
    else {
      c.vibwait = i.vibdelay;
      /* PASCAL:    c->vibspeed = ((i->vibrato >> 4) & 15) + 1; */
      c.vibspeed = ((i.vibrato >> 4) + 2) & 0xff;
      c.vibrate = ((i.vibrato & 15) + 1) & 0xff;
    }

    if (!(c.trmstay & 0xf0)) {
      c.trmwait = (i.tremwait & 0xf0) >> 3;
      /* PASCAL:    c->trmspeed = (i->mod_trem >> 4) & 15; */
      c.trmspeed = i.mod_trem >> 4;
      c.trmrate = i.mod_trem & 15;
      c.trmcount = 0;
    }

    if (!(c.trmstay & 0x0f)) {
      c.trcwait = ((i.tremwait & 15) << 1) & 0xff;
      /* PASCAL:    c->trcspeed = (i->car_trem >> 4) & 15; */
      c.trcspeed = i.car_trem >> 4;
      c.trcrate = i.car_trem & 15;
      c.trccount = 0;
    }

    c.arp_size = i.arpeggio & 15;
    c.arp_speed = i.arpeggio >> 4;
    c.arp_tab.set(i.arp_tab);
    c.keycount = i.keyoff;
    c.nextvol = c.glideto = c.finetune = c.vibcount = c.arp_pos = c.arp_count = 0;
  }
}
