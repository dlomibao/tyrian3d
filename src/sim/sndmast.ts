// Sound effect and voice ids (OpenTyrian src/sndmast.h). The sim writes these into g.soundQueue.

export const S_NONE = 0;
export const S_WEAPON_1 = 1;
export const S_WEAPON_2 = 2;
export const S_ENEMY_HIT = 3;
export const S_EXPLOSION_4 = 4;
export const S_WEAPON_5 = 5;
export const S_WEAPON_6 = 6;
export const S_WEAPON_7 = 7;
export const S_SELECT = 8;
export const S_EXPLOSION_8 = 8;
export const S_EXPLOSION_9 = 9;
export const S_WEAPON_10 = 10;
export const S_EXPLOSION_11 = 11;
export const S_EXPLOSION_12 = 12;
export const S_WEAPON_13 = 13;
export const S_WEAPON_14 = 14;
export const S_WEAPON_15 = 15;
export const S_SPRING = 16;
export const S_WARNING = 17;
export const S_ITEM = 18;
export const S_HULL_HIT = 19;
export const S_MACHINE_GUN = 20;
export const S_SOUL_OF_ZINGLON = 21;
export const S_EXPLOSION_22 = 22;
export const S_CLINK = 23;
export const S_CLICK = 24;
export const S_WEAPON_25 = 25;
export const S_WEAPON_26 = 26;
export const S_SHIELD_HIT = 27;
export const S_CURSOR = 28;
export const S_POWERUP = 29;
/** "Cleared enemy platform." */
export const V_CLEARED_PLATFORM = 30;
/** "Large enemy approaching." */
export const V_BOSS = 31;
/** "Enemies ahead." */
export const V_ENEMIES = 32;
/** "Good luck." */
export const V_GOOD_LUCK = 33;
/** "Level completed." */
export const V_LEVEL_END = 34;
/** "Danger." */
export const V_DANGER = 35;
/** "Warning: spikes ahead." */
export const V_SPIKES = 36;
/** "Data acquired." */
export const V_DATA_CUBE = 37;
/** "Unexplained speed increase." */
export const V_ACCELERATE = 38;

/** windowTextSamples[9] (sndmast.c): the voice played with each level-event message (event 16). */
export const windowTextSamples = [
  V_DANGER,
  V_BOSS,
  V_ENEMIES,
  V_CLEARED_PLATFORM,
  V_DANGER,
  V_SPIKES,
  V_ACCELERATE,
  V_DANGER,
  V_ENEMIES,
] as const;
