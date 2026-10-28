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

- **Round parts** (pipes, barrels, tanks, pods, domes): a highlight band or spot with darker edges.
  A round part's height above what it sits on should be about its width (a pipe 10 px wide stands
  about 10 px tall; a dome about half its diameter or more).
- **Flat parts** (hull plates, decks, armour panels): even shade, often with a lit edge on the
  light side (upper-left) and a dark edge opposite, which means a bevel. Plates stack: a plate
  drawn over another, with a shadow on its lower-right side, sits higher.
- **Tapering parts** (towers, gun barrels, noses, wings): the width changes along their length, and
  the height should follow it.
- **Recesses** (grilles, vents, windows, hatches): dark pixels inside a part are cut in, not
  painted on.
- **Buildings and ground structures** sometimes show a front wall: a darker band along the bottom
  edge. Its length in pixels suggests the building's height.

Units: one sprite pixel is 1/12 world unit; the elevations carry a ruler in sprite px.

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
| 9 | The game camera's angle |
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
`missing_raised`, `wrong_colour`, `outline_wrong`, `seam`, `lumpy`, `wrong_position`, `other`.

Severity: `high` = the part reads wrong in game; `medium` = visible in the 3/4 views or
elevations; `low` = polish.

Every issue's note says **what is wrong and what it should be, concretely enough to fix**: which
part, its current height or profile, and the target (for example "r12, the left pipe: about 4 px
tall and capsule-flat; should be round, about 10 px tall, as wide as it is in the sprite").
