// The hue half of the smoothie filters (DECISIONS.md D31), done where the C does it: on palette
// indices. lava_filter writes hue 0x70, iced_blur_filter 0x80 and water_filter its own hue (but
// leaves grey and cloud-blue pixels, (index & 0x30) == 0, alone) into every pixel drawn before the
// filter runs. Palette materials apply the same index arithmetic to draws whose pass height (D5) is
// under a filter's ceiling, after the draw's own effect, so the colours keep their lighting.
// Pixels the water recoloured are marked with alpha 0.5 in the screen filters' render target, for
// its ripple (screenFilters.ts). The value half (waves, smears, blurs) is post-processing there.

export const MAX_SCREEN_HUE_STAGES = 6;

/** One hue change: draws below `ceiling` (world height) take hue `hue` (0..15). */
export interface ScreenHueStage {
  ceiling: number;
  hue: number;
  /** water_filter: only indices with (index & 0x30) != 0 change, and they're marked. */
  water: boolean;
}

/** GLSL for palette materials: the uniforms, and screenHueIndex(index, height, water). */
export const SCREEN_HUE_PARS = /* glsl */ `
uniform int screenHueCount;
uniform float screenHueCeiling[${MAX_SCREEN_HUE_STAGES}];
uniform float screenHueHue[${MAX_SCREEN_HUE_STAGES}];
uniform float screenHueWater[${MAX_SCREEN_HUE_STAGES}];
float screenHueIndex(float index, float height, inout float water) {
  for (int i = 0; i < ${MAX_SCREEN_HUE_STAGES}; i++) {
    if (i >= screenHueCount) break;
    if (height >= screenHueCeiling[i]) continue;
    float lo = mod(index, 16.0);
    if (screenHueWater[i] > 0.5) {
      if ((int(index + 0.5) & 0x30) != 0) {
        index = screenHueHue[i] * 16.0 + lo;
        water = 1.0;
      }
    } else {
      index = screenHueHue[i] * 16.0 + lo;
    }
  }
  return index;
}
`;

/** The current hue stages, as uniforms shared by one renderer's palette materials. */
export class ScreenHue {
  readonly uniforms = {
    screenHueCount: { value: 0 },
    screenHueCeiling: { value: new Array<number>(MAX_SCREEN_HUE_STAGES).fill(-1) },
    screenHueHue: { value: new Array<number>(MAX_SCREEN_HUE_STAGES).fill(0) },
    screenHueWater: { value: new Array<number>(MAX_SCREEN_HUE_STAGES).fill(0) },
  };
  private stages: readonly ScreenHueStage[] = [];

  set(stages: readonly ScreenHueStage[]): void {
    const u = this.uniforms;
    if (stages.length === 0 && u.screenHueCount.value === 0) return;
    this.stages = stages.slice(0, MAX_SCREEN_HUE_STAGES);
    u.screenHueCount.value = this.stages.length;
    this.stages.forEach((s, i) => {
      u.screenHueCeiling.value[i] = s.ceiling;
      u.screenHueHue.value[i] = s.hue;
      u.screenHueWater.value[i] = s.water ? 1 : 0;
    });
  }

  /**
   * The hue byte (hue << 4) a whole model at `height` takes, or -1. Models are coloured per part,
   * not per index, so the water's per-index test is left out (nothing the water covers is a model).
   */
  modelHue(height: number): number {
    let hue = -1;
    for (const s of this.stages) if (!s.water && height < s.ceiling) hue = s.hue << 4;
    return hue;
  }
}
