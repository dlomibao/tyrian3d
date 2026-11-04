# Outline border: where a model's top-view edge goes

Rule for every model that replaces a sprite (enemies, bosses, player ships, sidekicks). Decision:
DECISIONS.md D74. Tool: `tools/sprite_mask.py`.

## The rule

Most sprites draw a dark ink border, 1 px wide, all round the object. The game draws its own ink
outline round every model (`OUTLINE` in src/render/view.ts, from the model's outline shell, D51).
That ink stands in for the sprite's border, so:

1. **The model's top-view edge goes to the INNER edge of the sprite's ink border.** The border is
   the ink pixels of the sprite's boundary ring: luma < 26 (palette 1, 2 and each ramp's darkest
   steps: 16, 32, 48, 64, 80, 112, ...) and 4-adjacent to transparency or the picture's edge.
2. **Where the sprite has no ink at its edge** (colour drawn to the edge: island rock, glows,
   flames, a lit rim), the edge stays at the outer edge. The inner mask already keeps those pixels.
3. **Thin parts keep at least half their sprite width.** A part only 1 colour pixel wide inside
   its ink (arcs, legs, antennae, claw tips), or drawn in ink alone, is pulled in by at most a
   quarter of its width on each side, never to nothing. Its border pixels are "free": they count
   neither way.
4. **Don't model or paint the border.** No dark rim, skirt or bevel band standing in for the ring;
   the game's ink does that. The outline shell is made from the model as before
   (`common.outline_shell`), so it follows the new edge by itself.

## Accept

```
python3 tools/sprite_mask.py <name> --measure <top.png>     # top view on the sprite's grid
```

`iou_rule_grid` ≥ 0.95 on every frame (the old "IoU ≥ 0.95 vs the sprite mask", now against the
inner mask with the free pixels left out); a player ship's banking frames have their own bars
(below, D89). Render the top view without the outline shell and
without `tyrian_ground` rock. `--json` prints the masks (`o` = border, `#` = inner); `--png ... --inner`
writes the inner mask to trace in a blueprint or fit a plan curve (D52's pchip) to.

## Banking frames (player ships, D89)

A player ship's banking frames are its level-frame model rolled and moved sideways by the game; the
model is fitted to the level frame only.

1. **Never shape the model for a banking frame.** No parts, heights or offsets that only help a bank
   (ventral fins, endplates, a body raised off the roll axis, forked tips): the 1995 banking sprites
   are hand drawn, not rotations, and such parts didn't get there (the D74 refit's tries: Phoenix
   0.68-0.75, Stalker 0.83-0.91 on its banks), while they show in the side, front and hangar views.
2. **Fit the pose instead:** `tools/bank_roll.py <name> --fit` (Blender) sweeps the roll per bank
   step and the shift per frame, as the game draws them, and prints `"roll"` (and `"shift"` where it
   beats bankShift.ts's). Put them in the script's export with
   `common.with_bank_roll(sprite["sprites"], BANK_ROLL, BANK_SHIFT)`; they land in the ship's
   spriteModels entry as `bank.roll` / `bank.shift`. The fit keeps the game's 17.5 / 35 degrees
   unless the art clearly draws another roll (U-Ship 40 / 55, Phoenix 40 / 50).
3. **Accept:** `tools/bank_roll.py <name>` prints every frame's `iou_rule_grid` at the ship's pose:
   level frame ≥ 0.95, half-bank frames ≥ 0.80, full-bank frames ≥ 0.70.

## Why (measured, D74)

In the game at 1920x1080 with the default frame HUD (5.4 screen px per sprite px), the ink is
about 3-4 screen px, 0.55-0.75 sprite px. Models fitted to the whole sprite (outer edge) plus that
ink came out 0.7-1.0 sprite px fatter per edge than the sprite (Talon 22% more area); in-game
silhouette IoU with the sprite 0.69-0.85. The same models pulled in to the inner edge: -0.1 to
+0.3 px, IoU 0.82-0.93, and thin parts (newsh2-191's arcs, -267's legs) still read. Comparison
sheets: `tyrian-scratch/outline-border/sheets/`.

## Watch for

- **Tall models still look bigger in game.** A model's origin plane covers the sprite's screen
  area (D6); parts above it are nearer the camera and drawn larger (the level-1 boss is +0.8 px per
  edge even at the inner edge). That is the model's height, not the border; keep tall parts' plan
  inside the sprite, don't shrink the plan further.
- **Measure the in-game silhouette too** for heroes: model plus ink at the game's scale against the
  sprite (`tyrian-scratch/outline-border/ingame.py` shows how: draw the object still in
  `?debug=models`, frame-HUD viewport, a flat background).
