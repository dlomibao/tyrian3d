# Model review rubric

How a model's review sheet (`tools/review_sheet.py`) is graded, by a person on the rating page
(`tools/calibration/index.html`) or by a grader agent. The page's criteria, anchors and issue types
are the same as here; change both together.

## What the models are for

Every enemy, boss and player ship in Tyrian 3D is a Blender model that replaces its original
sprite. A model must be **the sprite brought into 3D**: the same silhouette, proportions, colours
and details, with believable depth. The game camera looks almost straight down, so the top view
must match the sprite closely; depth shows in the lighting, the shadows and the slight tilt.

The common failure is **flatness**: parts modelled as low slabs or squashed capsules when the
sprite's shading and size say they're tall, round, tapered or stacked. Judge each part's height
against what the sprite implies:

- **Keep every feature.** Each model has a feature list (`assets/blender/features/<name>.json`):
  the named parts of the sprite (windshield, canopy, pipes, tanks, fins, guns, intakes, lights, panel
  lines) with where they are and what they must look like. Every listed feature must still be there
  and read as what it is; a lost or weakened feature is a regression no matter what else improved.
  Compare with the original hand-made model too (the baseline), not only the last round.
- **Hard surfaces stay hard, round parts stay round.** Ships, machines, guns and buildings are
  mostly hard surfaces: flat panels, crisp chamfered edges and sharp creases, given height by
  extruding and bevelling panels, not by inflating or subdividing them. But they can also have round
  parts: canopies and cockpit bubbles, engine nacelles and nozzles, fuselages or pods the sprite
  shades round, domes, tanks, round pipes. Follow the sprite part by part: where it draws a flat
  panel or a hard edge, keep it flat and crisp; where it draws a curve (a highlight band with soft
  falloff, a round outline), make it round. What is wrong is everything turning soft: a ship whose
  flat panels and edges have gone bubbly or blobby is worse even if it is taller.
- **Pipes are pipes.** A pipe is a cylinder of constant diameter that follows its path: straight
  runs, bends, clamps and flanges. Never a chain of bulges, capsules or spheres (that reads as
  tanks). A tank is only where the sprite shows a closed vessel with end caps.
- **Glass stays glass.** Windshields, canopies, windows and visors are distinct glass parts with
  crisp edges (glossy material, slightly raised or set in a frame), even where the sprite draws them
  as a bright highlight. Don't merge them into the hull or paint them out.
- **Round parts** (pipes, barrels, tanks, pods, domes): a highlight band or spot with darker edges,
  on a part whose outline is round too. A round part's height above what it sits on should be about
  its width (a pipe 10 px wide stands about 10 px tall; a dome about half its diameter or more).
- **Metallic sheen is not geometry.** A small, very bright spot or streak (often near-white) on a
  hull is usually a specular highlight on shiny metal, not a hump, knob or dome. Don't add or ask
  for geometry for it; the model's metallic material and the lighting make the shine. Model a bump
  only when the outline, the part's width or a shadow beside it says the surface rises there. (The
  user pointed this out on the Gencore Phoenix: its bright centre spot is sheen, and the lump the
  first fix round put there is wrong.) Judge the material first: not everything is metal. On
  rock, earth, organic creatures, cloth or matte paint a highlight usually is a lit face of a real
  shape (so model the shape, matte); on glass, gems, wet or glossy surfaces it is shine (use a
  glossy material, not geometry); on metal hulls a small hot spot is shine. Give each part the
  material that makes its highlights read right: metallic and smooth for polished metal, low
  metallic and rough for rock or flesh.
- **Flat parts** (hull plates, decks, armour panels): even shade, often with a lit edge on the
  light side (upper-left) and a dark edge opposite, which means a bevel. Plates stack: a plate
  drawn over another, with a shadow on its lower-right side, sits higher.
- **Tapering parts** (towers, gun barrels, noses, wings): the width changes along their length, and
  the height should follow it.
- **The sprite's lighting is not paint.** Sprites draw their light: a dark outline around the edge,
  darker pixels on the lower-right side, lighter on the upper-left, highlights. The game lights the
  model and draws its own dark outline (`OUTLINE` in src/render/view.ts), so a model must not paint
  the sprite's outline ring onto its sides, nor bake the sprite's shading into its colours on
  curved surfaces: that darkens it twice (a grey ball turns black from the game camera) and looks
  blocky. Give each part its mid-tone colour and let the light shade it; paint only real markings
  (stripes, lights, panel colours), not shading.
- **Recesses** (grilles, vents, windows, hatches): dark pixels inside a part are cut in, not
  painted on.
- **Buildings and ground structures** sometimes show a front wall: a darker band along the bottom
  edge. Its length in pixels suggests the building's height.

Units: one sprite pixel is 1/12 world unit; the elevations carry a ruler in sprite px.

## Reading a sprite

What the pixel patterns mean, learned by comparing sprites with high-resolution reimaginings of them
(`assets/blender/features/concepts/`). A good reading names every part as a real kind of object (a
pipe, a clamp, a coil, a mast, a windshield, an armour plate) and builds it the way that object is
built.

- **First name the part, then model it.** An artist redrawing the sprite at high resolution turns
  each ambiguous cluster of pixels into a known object; do the same. The feature list records it.
- **A thin bright line along a part is an edge catching the light**, a bevel or ridge, so the
  surface has a crisp edge there. It is not a separate strip of material.
- **A bright streak down the middle of a long part with darker sides is a cylinder** (a pipe or
  barrel): keep its diameter constant along its length; a bend keeps the same diameter.
- **Alternating light and dark bands across a narrow part are rings**: ribs, coils, stacked
  discs or strap bands around a pipe.
- **A grid of small squares is bolted plating or a clamp box**: raised boxes with seams between
  them, wrapped around whatever they sit on.
- **A saturated colour (blue, red, yellow) with a near-white core is a light**: glowing glass set
  in a housing (an arch, a frame, a socket), emissive, not a coloured lump.
- **A dark slot or band with a single bright pixel near it is glass**: a windshield, canopy or
  window, recessed in a frame, with the bright pixel as its glint.
- **Dark areas inside the silhouette are depth**: a gap between parts, a seam, or a recessed bay
  that holds smaller parts (pipes, machinery). They are not flat black floor.
- **Dark lines between lighter areas are seams between panels or parts.** Use them to split the
  model into separate plates and pieces.
- **Speckled or dithered pixels on a flat area are surface wear or texture**, not bumps.
- **When one half of a symmetric object is darker, that is shadow.** The light comes from the upper
  left, so the right or lower side is drawn darker. Build both halves the same shape and colour and
  let the light do it.
- **A small isolated near-white pixel on metal or glass is a glint** (see the sheen rule above).
- **Thin vertical stacks of small blocks with knobs at the sides are masts or antennas.**

## The sheet

1920 x 2038 px, a 30 px header, then four rows of 480 px panels, each under a 22 px title:

| Panel | Content |
|---|---|
| 1 | The sprite, enlarged with nearest-neighbour scaling |
| 2 | The model from straight above, orthographic, at the sprite's scale, lit |
| 3 | The sprite laid over the model's flat colours at 50% |
| 4 | Diff: red = sprite pixels the model misses, blue = model where the sprite is empty, grey to yellow = colour error |
| 5 | Side elevation, orthographic, from the right (sprite top is to the right); two panels wide; ruler in px |
| 6 | Front elevation, orthographic, from the screen bottom; two panels wide; ruler in px |
| 7, 8 | Three-quarter views, front-right and back-left |
| 9 | The game camera's angle, lit like the game (EEVEE: each part's metalness and roughness, environment light and sun). The only panel that shows material shine; judge sheen and colour in game here |
| 10 | Region map: the sprite split into regions (same colour family, connected), with ids like r7 |
| 11 | The height the shading analysis infers for each pixel (a hint, often wrong on shading; trust width more) |
| 12 | Metrics (also in the sheet's .json) |

The analysis in panels 10 and 11 is a tool, not the truth. Its width-based heights are a fair guide
to size and roundness; its shading reads are unreliable (it mistakes sloped panels for round ones).

Metrics: `silhouette_iou` = how well the top-view outline matches the sprite (1 = exact);
`max_height_px` and `height_to_width` = how tall the model is overall; `colour_dE_mean` = colour
error seen from above; `height_error_px_mean` = how far the model's region heights are from the
analysis's guesses; `seams` (assemblies) = height steps where pieces meet.

## Scores (1 to 5)

Score what the sheet shows. 2 and 4 are between the anchors.

| Criterion | 1 | 3 | 5 |
|---|---|---|---|
| **Outline & colour** (`silhouette`) | Outline or colours clearly differ from the sprite | Recognisable, but some parts' outline or colour is off | Top view matches the sprite |
| **Volume & heights** (`volume`) | Everything flat, or heights uniformly wrong | Some parts right, others too flat or too tall | Every part is about as tall as the sprite implies |
| **Profiles** (`profile`) | Round things flat or boxy, flat things blobby | Mixed: some profiles right, some wrong | Round parts round, flat parts flat, tapers taper |
| **Detail** (`detail`) | Recesses and raised details missing | The main details are there | Every detail the sprite shows, in relief |
| **Reads in game** (`game`) | From the game camera it doesn't look like the sprite | Recognisable from the game camera | Looks like the sprite brought into 3D |
| **Pieces fit together** (`cohesion`, assemblies only) | Pieces don't fit: gaps, steps, mismatched heights | Small seams or steps | Reads as one object |
| **Overall** (`overall`) | Unacceptable; redo it | OK as a start (2 = poor, 4 = good) | Ship it |

## Issues

Each issue points at one spot: a panel (1-12), a position inside it (0-1 across, 0-1 down), and
the region id when one applies. Types:

`too_flat`, `too_tall`, `should_be_round`, `should_be_flat`, `should_taper`, `missing_recess`,
`missing_raised`, `wrong_colour`, `outline_wrong`, `seam`, `lumpy`, `wrong_position`,
`feature_lost` (a listed feature is gone or no longer reads as what it is), `should_be_angular` (a
hard surface gone soft or bubbly), `bulging` (a pipe or rail with varying thickness), `other`.

Severity: `high` = the part reads wrong in game; `medium` = visible in the 3/4 views or
elevations; `low` = polish.

Every issue's note says **what is wrong and what it should be, concretely enough to fix**: which
part, its current height or profile, and the target (for example "r12, the left pipe: about 4 px
tall and capsule-flat; should be round, about 10 px tall, as wide as it is in the sprite").

## Calibration (2026-10-28)

A committee (an Opus and a Fable grader and a chair) graded 20 models' sheets; the user reviewed
their grades and agreed with all of them. Those grades, in
`assets/blender/proto/calibration/feedback.json` (status `done`, `acceptedFromCommittee`), are the
reference set: grade new sheets the way they were graded, and fix models toward what they ask for.
What they found, most common first (152 issues on 20 models):

- **Too flat** (30) and **round parts built as slabs or squashed capsules** (17) are the main
  problems. 11 of the 20 scored 1-2 on volume. A sprite part that is drawn round (a highlight band
  with dark edges) is as tall as it is wide; pods and spheres are spheres, not lenses.
- **Colours** (29) and **outlines** (28) come next: parts in the wrong palette shade from above, and
  outlines that drift from the sprite's (IoU under about 0.8 is worth a look).
- **Recesses** (15): grilles, vents, ports and windows drawn dark in the sprite are cut in.
- Overall scores: 4 for the best two (the building assembly-newshj-43, newshe-235), 3 for eight,
  2 for ten. A 4 is the bar for "good"; fixing a 2 starts with its heights and profiles.
