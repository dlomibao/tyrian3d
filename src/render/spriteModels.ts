// Which sprites are drawn as Blender models (DECISIONS.md D4, D15, D49).
//
// Each model built by a script in assets/blender/ writes a small JSON file to spriteModels/ beside
// its .glb in public/models/ (common.export_sprite_model in assets/blender/common.py). It names the
// sprites the model replaces. One file per model, so models built in parallel never edit the same
// file.

/** Sprites of one sheet that a model replaces. */
export interface SpriteRef {
  /** Sprite2Sheet.id, e.g. "newsh1.shp" or "tyrian.shp#8". */
  sheet: string;
  /** 1 = a 12x14 sprite, 2 = a 2x2 block of tiles (24x28). */
  size: 1 | 2;
  /** Sprite index of the top-left tile of each animation frame the model replaces. */
  frames: number[];
  /**
   * For a player ship: frames[0] is the level frame and the banking frames are frames[0] + n * step
   * for n = -max..max (blit_sprite2x2 at shipGraphic + ship_banking * 2). The model rolls with them.
   * Without it, the sprites are a grouped object (an enemy) and the model stays level.
   */
  bank?: { step: number; max: number };
  /**
   * [two-player] With `bank`: the frames are the first sprite of a grouped draw (a ship drawn in
   * two halves, blitShipHalves, like the dragonwing), so the model replaces the whole group and
   * rolls with the group's banking frame.
   */
  group?: boolean;
  /**
   * The frames are drawn on their own, not as part of an enemy (blit_sprite2 or blit_sprite2x2 with
   * no drawGroup): the player's sidekicks (JE_playerMovement). The model replaces each such draw of
   * these frames, centred on the sprite, and shows the frame drawn (animated models, D17).
   */
  ungrouped?: boolean;
}

export interface SpriteModelEntry {
  /** Model path in public/models/, without .glb, e.g. "enemies/newsh1-17". */
  model: string;
  sprites: SpriteRef[];
}

const files = import.meta.glob<SpriteModelEntry>("./spriteModels/*.json", { eager: true, import: "default" });

/** Every model entry in spriteModels/. */
export const SPRITE_MODELS: readonly SpriteModelEntry[] = Object.values(files);

export const spriteModelKey = (sheet: string, size: number, index: number): string => `${sheet}|${size}|${index}`;

/** A model that replaces a player ship's sprite and its banking frames. */
export interface ModelOverride {
  sheetId: string;
  /** Sprite index of the level (unbanked) frame. */
  baseIndex: number;
  /** Index step between banking frames, and how many frames there are to each side. */
  bankStep: number;
  maxBank: number;
  /** The size the sprite is drawn at (2 for blit_sprite2x2). */
  size: 1 | 2;
  /** Model path in public/models/. */
  model: string;
}

export interface SpriteModels {
  /** spriteModelKey(sheet, size, frame) to model path, for grouped objects (enemies). */
  grouped: Map<string, string>;
  /** Player ships with banking frames. */
  banked: ModelOverride[];
  /** [two-player] For grouped ships with banking frames: spriteModelKey to the bank, -1..1. */
  groupBank: Map<string, number>;
  /** spriteModelKey(sheet, size, frame) to model path, for sprites drawn on their own (sidekicks). */
  ungrouped: Map<string, string>;
}

/** Index the entries. Throws if two models claim the same frame. */
export function spriteModels(entries: readonly SpriteModelEntry[] = SPRITE_MODELS): SpriteModels {
  const grouped = new Map<string, string>();
  const banked: ModelOverride[] = [];
  const groupBank = new Map<string, number>();
  const ungrouped = new Map<string, string>();
  const claimed = new Map<string, string>();
  const claim = (key: string, model: string) => {
    const other = claimed.get(key);
    if (other !== undefined && other !== model) throw new Error(`${model} and ${other} both replace ${key}`);
    claimed.set(key, model);
  };
  for (const e of entries) {
    for (const ref of e.sprites) {
      if (ref.bank && ref.group) {
        // [two-player] a grouped ship (two halves) that banks: every frame is the group's model
        const [base] = ref.frames;
        for (let n = -ref.bank.max; n <= ref.bank.max; n++) {
          const key = spriteModelKey(ref.sheet, ref.size, base + n * ref.bank.step);
          claim(key, e.model);
          grouped.set(key, e.model);
          groupBank.set(key, n / ref.bank.max);
        }
        continue;
      }
      if (ref.bank) {
        const [base] = ref.frames;
        for (let n = -ref.bank.max; n <= ref.bank.max; n++) claim(spriteModelKey(ref.sheet, ref.size, base + n * ref.bank.step), e.model);
        banked.push({ sheetId: ref.sheet, baseIndex: base, bankStep: ref.bank.step, maxBank: ref.bank.max, size: ref.size, model: e.model });
        continue;
      }
      for (const frame of ref.frames) {
        const key = spriteModelKey(ref.sheet, ref.size, frame);
        claim(key, e.model);
        (ref.ungrouped ? ungrouped : grouped).set(key, e.model);
      }
    }
  }
  return { grouped, banked, groupBank, ungrouped };
}
