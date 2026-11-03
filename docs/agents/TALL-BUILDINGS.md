# Tall buildings and structures

How to model a structure whose tiles paint a roof with a wall below it (the art's fake perspective).
Standard: DECISIONS.md D82. Kit: `assets/blender/tiles/lib_tall.py`. Measure: `tools/tall_buildings.py`.
Worked example: `assets/blender/tiles/savbld_towers.py` (SAVARA's towers).

## Is it tall?

Tyrian draws tall buildings in a fixed oblique view: the roof, and under it the south wall. The game
camera can't show that much wall. At 15° a vertical wall shows 0.31 px per px of height at mid-screen,
0.72 at the screen's top and -0.09 at its bottom. A ground structure may be 0.8 units tall (D5), which
is about 3 px of wall. So a wall band of 6 px or more can't come from real height.

```
python tools/tall_buildings.py analyse <shapes> '<pattern json>' [--layer N] [--ground ramp,ramp]
```

It prints the split (R roof, W wall) and a verdict. **Tall** means all of these hold:

| Measure | Threshold | Meaning |
|---|---|---|
| `wall_px` | ≥ 6 | The median wall band (foot − roof edge) per column |
| `cover` | ≥ 0.6 | The share of the building's columns that have a roof/wall edge |
| `spread` | ≤ 0.5 | (p90 − p10) / median of the band: about as tall everywhere |
| `darker` | ≥ 0.08 | The roof's mean luminance minus the wall's |
| `vertical` | ≥ 1.0 | The wall's detail runs up and down (brightness changes across it more than down it) |

`--ground` gives the ground's palette ramps (index >> 4) when the default (the ramps on the pattern's
border) is wrong. Always look at the split as well: the verdict picks candidates, not models.

Results so far:
- SAVARA's towers: tall (wall 54 and 110 px, spread 0.06-0.10).
- TYRIAN (level 1): none of the 14 structure patterns analysed is tall (the fortress and bridge
  weren't analysed). They fail on spread (purple blocks, gates, wreck, bunker-ring, lava pit, drums),
  vertical (bunker-ring, gates, lava pit), darker (bunker-hull, wreck, crater) or cover (wreck,
  crater). The drums are borderline: a 7 px wall with spread 0.8. In game none of the variants
  improved on the current drum.

**Not tall:** use the ordinary rule (top-view IoU ≥ 0.95 against the tiles' mask, features, colours).

## The rule for a tall structure

1. **Footprint:** the roof's outline moved down by the wall band, so the building stands where its
   painted wall meets the ground.
2. **Walls are vertical**, and the building is as tall as the painted wall band (1 px of height per
   px of wall).
3. **Faces wear their pixels.** The roof takes the roof's pixels, and the south wall takes the wall's
   pixels row for row (the top wall row at the top). Use palette materials (`pal_<index>`). Detail is
   modelled (relief, parts), not baked: no concept bake, because a top-down projection doesn't land
   on an oblique model.
4. **Drawn oblique-locked.** Give the model the extras `tyrian_oblique: wall_px / height_px` (1) and
   `tyrian_depth_band: [lo, hi]` (`lib_tall.DEPTH_BAND`: ground [0, 0.04], under background 2 at
   0.05; background 3 [0, 0.38]). `TallBuilding.export` does both. The renderer
   (`structureInstances.ts`) puts each vertex on the camera ray through the point the art draws it
   at, with the depth of a squeezed copy:
   - the roof and wall land exactly on the painted roof and wall at every tilt and scroll position;
   - enemies, shots, the player and background 2 still draw over it, as in the original;
   - light, normals and shadows are the real building's.
5. **Ground (layer 0):** keep the tiles (`keepTiles`). The model covers the painted building, and
   the tiles show round it. Tile kits shared with other walls need `minRows`; check with
   `tests/render/remaster.test.ts`. SAVARA's towers needed all their rows: the same kit makes
   shorter and taller towers. The switch from tiles to model hardly shows, because the model lands
   on the tiles.
6. **Background 3 (layer 2):** not done yet. The model replaces its tiles, so it must carry its rock
   (D63), and the rock must not take the oblique view. Use a separate object or model, and check the
   renderer reads the extras per object.

## Accept

```
python tools/tall_buildings.py measure <shapes> '<pattern>' public/models/tiles/<shapes>/<name>.glb [--layer N]
```

This renders the model as the game's three cameras see it (0°, 15° and 32°, at the screen's top,
centre and bottom), projected onto the ground plane so it lines up with the tiles. It scores the
renders against the split (metrics in `.shape/tall/<name>/metrics.json`). Every view must meet these:

| Metric | Target |
|---|---|
| `screen_iou` | ≥ 0.95 (model silhouette against the building's mask) |
| `roof_iou`, `wall_iou` | ≥ 0.85 (up-facing faces on the painted roof, walls on the painted wall) |
| `roof_dE`, `wall_dE` | ≤ 6 (flat palette colours against the tiles, CIE76) |
| `<cam>-drift_px` | ≤ 1 (the roof's movement against the tiles between the screen's top and bottom) |
| `footprint_iou` | ≥ 0.85 (the section 1 px above the base against the moved roof outline) |

Then capture it in game at 0°, 15° and 32° (`?debug=play&main=N&seed=1&skip=T&freezeAt=T&camera=...`)
next to `&bg=original`, and at three ticks as it scrolls. Check that enemies and shots draw over it,
that background 2 (clouds) still covers it, and that its shadow falls where it should.

## What was tried (D82)

All on SAVARA's wide and tall towers and TYRIAN's drum. "15°" is the default camera.

| Approach | In game | Screen IoU 0°/15°/32° (wide) | Drift at 15° |
|---|---|---|---|
| A: footprint + true height, real perspective | The roof floats off its tiles, magnified (the 110 px tower is half the camera's height). It shows big dark side faces. | 0.42 / 0.64 / 0.77 | 37 px (tall: 86) |
| B: fit the 15° camera within the pass budget (0.8 u) | Looks like the original. As a 3D object it's a ramp: the "sloped slab". | 0.96 / 0.93 / 0.88 | 3 px |
| C0: true height + a static lean to fit 15° | A leaning slab, with drift | 0.83 / 0.75 / 0.74 | 12 px |
| **C: true building, oblique-locked (chosen)** | Looks like the original at all tilts, with wall lighting and a real shadow. As a 3D object it's a true tower. | 0.98 / 0.98 / 0.98 | 0 |

Costs of C:
- It never shows more wall at 32° and has no parallax, like every flat tile (D6).
- It needs the renderer's per-vertex transform. Its 3D-ness is lighting, relief and shadow.
