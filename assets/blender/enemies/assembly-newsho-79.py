"""FLEET boss hull (newsho.shp, the 24-piece assembly-newsho-79, 192 x 84 px).

What it is: the upper hull of FLEET's (3.6, main=12) capital ship, a FLYING warship, not a ground fortress.
It spawns on tick 5020 rigid with the grey walker base (assembly-newsho-156) below it and the three
deck hatches (assembly-newsho-191), drifts against the terrain with a weaving x cycle and leaves on
the left after ~2030 ticks. So it is built as one closed flying hull: a dark tapered keel under a
flat armoured deck, the superstructure on top, centred on the sprite plane (z = 0 is the deck edge).

Read from the sprite (mirror symmetric about pixel edge 95.5):
  * centre: the command bridge (grey hood with a louvred vent on its roof, rows 10-37) with sloped hip
    fairings down to the deck; blue armoured claws at its front corners; the big dark glass sensor orb
    in a dark well in front of it, framed by two curved blue shoulder plates and cradled by a heavy
    grey collar (a U-shaped bumper tube); below it the chin bay: a blue hinge barrel across the lid,
    blue cheeks and a dark recessed face with a stepped relief.
  * wings: a sloped blue armour glacis with a bevelled outer end and a crease into a steeper front
    plate (with a small sensor box); a grey dorsal strake (pillar) on it; a turret on the wing's aft
    edge (a rounded housing with two stern gun barrels, domed muzzles); a gun mount block with a
    cross rod behind the glacis; the big recessed dark bay (grey frame bars, a stepped relief on the
    dark face, lamps on the outer rail); a round pipe beside it; a lower block with a bevelled corner,
    a louvred vent housing and two blue fins; a gun barrel slanting out under each shoulder with a
    bright collar ring, and a dark pod below it.
Highlights are sheen and the outline ring is ink (art rule 2): nothing is modelled from them.

Units: c, r = assembly pixel edges (192 x 84); Blender X = (c - 96) / 12, Y = (42 - r) / 12, Z units.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsho-79.py
(exports the 24 pieces through common.export_sprite_model; --noexport, --out X.glb and --review DIR are
for scratch work.)
"""

import math
import sys
from pathlib import Path

import bpy

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b093 as L  # noqa: E402

ROOT = WT
NAME = "assembly-newsho-79"
PIECES = ["newsho-1", "newsho-3", "newsho-5", "newsho-7", "newsho-9", "newsho-11", "newsho-13", "newsho-15",
          "newsho-39", "newsho-41", "newsho-43", "newsho-45", "newsho-47", "newsho-49", "newsho-51", "newsho-53",
          "newsho-77", "newsho-79", "newsho-81", "newsho-83", "newsho-85", "newsho-87", "newsho-89", "newsho-91"]
CX0, CY0 = 116, 55  # screen centre of the assembly (as the old script): Blender origin
W, H = 192, 84
AX = 95.5  # mirror axis (pixel edges)
PX = L.PX
inset, fillet = L.inset, L.fillet


def mirror_full(left):
    return L.mirror_full(left, AX)


# --------------------------------------------------------------------------------------------------
# Materials: the sprite's own palette index per region (regions.py medians); satin metal, D176 F0
# --------------------------------------------------------------------------------------------------

MAT = L.Mats(ROOT, PIECES, NAME, "nsho79a")
WELL = MAT(1, 0.0, 0.9, 0.15)  # the deep black well round the orb (sprite index 1)
G2 = MAT(2, 0.3, 0.55, 0.5)  # dark bay faces, deck
G3 = MAT(3, 0.4, 0.5)  # dark grey mounts, inner walls
G4 = MAT(4, 0.45, 0.45)  # lower block, pipe, barrel
G5 = MAT(5, 0.45, 0.42)  # turret, frame walls
G6 = MAT(6, 0.45, 0.4)  # frame bars
G7 = MAT(7, 0.45, 0.4, 0.65)  # main grey hull
YOKE = MAT(7, 0.25, 0.32, 0.75)  # the U-shaped yoke tube: the sprite's median index 7 (rows 56-66), satin
G8 = MAT(8, 0.5, 0.36, 0.7)  # light grey trim
G9 = MAT(9, 0.55, 0.32, 0.75)  # bright ribs, slats
G10 = MAT(10, 0.6, 0.3, 0.8)  # lamps / collar ring
B56 = MAT(56, 0.4, 0.4, 0.6)  # front plates, lid, fins
B57 = MAT(57, 0.4, 0.4, 0.6)  # claws, shoulder plates
B58 = MAT(58, 0.4, 0.38, 0.6)  # glacis
# The orb: polished black glass (D176: F0 from Specular IOR Level, the sheen is the game's light, not
# paint). Index 2, the sprite's median for the orb (its glint is the sheen).
ORB = MAT(2, 0.0, 0.04, 1.0)
KEEL = MAT(4, 0.4, 0.5, 0.5)  # underside


# --------------------------------------------------------------------------------------------------
# The hull
# --------------------------------------------------------------------------------------------------

DECK = -0.22  # deck top: the floor of the wells, black (the sprite's index 1), sunk well under the parts

# The glacis' outer (north-west) edge, row by row inside the sprite's ink.
WEST = [(30.6, 20.0), (28.0, 21.3), (26.8, 22.6), (25.6, 24.6), (25.2, 25.3), (22.2, 26.3), (19.2, 27.3), (16.4, 28.3), (14.0, 29.7), (6.4, 37.0)]
BELLY_LEFT = [(AX, 20.7), (66, 20.7)] + WEST + [
    (6.4, 65.6), (23.6, 82.9), (56, 82.9), (56, 79), (57.3, 78), (59, 77), (60, 77), (61, 78), (62, 80), (62.8, 82.9),
    (68.2, 82.9), (68.2, 76.6), (69.8, 76.6), (69.8, 82.9), (AX, 82.9)]


def build_keel(B):
    """The deck plate (whole plan, dark top showing in the wells) and a tapered keel under it
    (underside: a plausible closed shape only)."""
    plan = mirror_full(BELLY_LEFT)
    B.mir = False
    B.slab(plan, DECK - 0.14, DECK, WELL, G4, ch=0.0001, chz=0.0001)
    def octo(x0, x1, r0, r1, chx, chy, ch):  # a chamfered rectangle: every ring the same topology
        return [(x0 + chx, r0), (x1 - chx, r0), (x1, r0 + chy), (x1, r1 - ch), (x1 - ch, r1),
                (x0 + ch, r1), (x0, r1 - ch), (x0, r0 + chy)]
    # The rim's aft corners stay inside the deck's bevelled corners (31, 20.7)-(6.4, 37).
    rings = [[(c, r, z) for c, r in octo(*box)] for box, z in (
        ((21, 2 * AX - 21, 31, 67, 16, 9, 5), -1.10), ((11.5, 2 * AX - 11.5, 25, 73, 21, 13, 7), -0.72),
        ((7.6, 2 * AX - 7.6, 21.7, 76, 24.6, 16.0, 9), DECK - 0.10))]
    B.rings(rings, KEEL, top=KEEL, bottom=KEEL)


def build_wing(B):
    """One wing (left; called again mirrored)."""
    # Armour glacis: rows 20.7-36.5, sloping 0.92 -> 0.80, its outer end bevelled 3.5 px.
    gz = lambda c, r: 0.92 - 0.0075 * (r - 20.5)  # noqa: E731
    glacis = [(52, 20.7), (52, 36.5)] + list(reversed(WEST))[:1] + list(reversed(WEST))[1:]
    glacis = [(52, 20.7), (52, 36.5), (6.6, 36.5)] + list(reversed(WEST))[1:]
    n = len(glacis)
    gtop = inset(glacis, [0, 0, 3.6] + [3.4] * (n - 4) + [0.8])
    B.slab(glacis, DECK, 0.0, B58, B58, chz=0.08, zf=gz, top_poly=gtop)
    # Front plate below the crease: steeper, rows 36.5-43.2, 0.80 -> 0.50, the outer end bevelled too.
    fz = lambda c, r: 0.80 - 0.0448 * (r - 36.5)  # noqa: E731
    front = [(6.6, 36.5), (52, 36.5), (52, 43.2), (6.4, 43.2)]
    ftop = [(10.4, 36.5), (52, 36.5), (52, 43.2), (9.6, 43.2)]
    B.slab(front, DECK, 0.0, B56, B56, chz=0.07, zf=fz, top_poly=ftop)
    # A crease rib along the glacis/front join and a small sensor box on the front plate.
    B.sweep([(11.0, 36.6, 0.795, 0.0, 0.0), (11.8, 36.6, 0.795, 0.6, 0.026), (51.5, 36.6, 0.795, 0.6, 0.026),
             (52.0, 36.6, 0.795, 0.0, 0.0)], sides=6, mat=B57)
    B.slab([(30, 37.3), (38.5, 37.3), (38.5, 40.6), (30, 40.6)], 0.40, 0.0, G3, G4, ch=0.5, chz=0.03,
           zf=lambda c, r: 0.815 - 0.036 * (r - 37.3))
    B.box(31.2, 40.0, 37.3, 40.9, 0.40, 0.64, G2, G2, ch=0.2, chz=0.02)
    # Panel plates on the glacis (real grooves between them).
    for c0, c1, r0 in ((19.0, 29.6, 28.4), (30.6, 40.4, 23.0)):
        B.slab([(c0, r0), (c1, 23.0 if c1 < 30 else 22.6), (c1, 35.6), (c0, 35.6)], 0.4, 0.0, B58, B58, ch=0.6,
               chz=0.025, zf=lambda c, r: gz(c, r) + 0.028)

    # Dorsal strake (grey pillar) on the glacis: a chamfered block with a rib band and a hatch.
    strake = fillet([(41, 20.7), (51.8, 20.7), (51.8, 38.6), (41, 38.6)], [0, 0, 1.2, 1.2], 2)
    B.slab(strake, 0.4, 1.10, G7, G7, ch=1.4, chz=0.10)
    B.sweep([(41.6, 26.5, 1.10, 0.0, 0.0), (42.0, 26.5, 1.10, 1.1, 0.04), (51.2, 26.5, 1.10, 1.1, 0.04),
             (51.6, 26.5, 1.10, 0.0, 0.0)], sides=8, mat=G9)
    B.box(43.6, 30.8, 49.2, 36.2, 1.06, 1.125, G6, G5, ch=0.5, chz=0.025)

    # Grey hull between the glacis and the shoulder.
    body = [(52, 20.7), (69.5, 20.7), (69.5, 28.6), (58.6, 29.2), (58.6, 43.2), (52, 43.2)]
    B.slab(body, DECK, 0.66, G7, G7, ch=0.9, chz=0.07)

    # Turret on the wing's aft edge: rounded housing, two stern barrels with domed muzzles.
    house = fillet([(42.45, 20.8), (42.45, 15.0), (43.0, 13.0), (44.0, 12.0), (45.0, 11.0), (55.0, 11.0), (55.6, 12.0),
                    (58.7, 12.0), (58.7, 20.8)], [0, 0.4, 0.5, 0.5, 0.6, 0.6, 0.3, 0, 0], 2)
    B.slab(house, 0.40, 0.95, G4, G4, ch=1.0, chz=0.08, bevel=G3)
    B.slab(fillet([(44.6, 14.3), (57.2, 14.3), (57.2, 20.4), (44.6, 20.4)], 1.2, 2), 0.8, 1.02, G4, G4, ch=0.6,
           chz=0.03)
    for cc, r_tip, rad in ((49.0, 8.9, 2.6), (54.6, 11.4, 2.5)):
        R = rad * PX
        path = [(cc, r_tip, 1.13, 0.0, 0.0), (cc, r_tip + 0.12, 1.13, rad * 0.78, R * 0.78),
                (cc, r_tip + 0.7, 1.13, rad * 0.97, R * 0.97), (cc, r_tip + 2.2, 1.13, rad, R),
                (cc, 19.6, 1.13, rad, R), (cc, 20.4, 1.13, rad * 0.8, R * 0.8)]
        B.sweep(path, sides=12, mat=G5)
        B.sweep([(cc, r_tip + 2.6, 1.13, rad + 0.35, R + 0.35 * PX), (cc, r_tip + 3.4, 1.13, rad + 0.35,
                 R + 0.35 * PX)], sides=12, mat=G9)
    # Gun mount block behind the glacis (rows 16-21), its cross rod and a light housing.
    mount = [(35.8, 16.4), (43.5, 16.4), (43.5, 21.0), (30.6, 21.0), (30.6, 16.9)]
    B.slab(mount, 0.35, 0.66, G3, G3, ch=0.6, chz=0.04)
    B.sweep([(31.5, 18.6, 0.71, 0.0, 0.0), (32.0, 18.6, 0.71, 1.3, 0.06), (42.8, 18.6, 0.71, 1.3, 0.06),
             (43.2, 18.6, 0.71, 0.0, 0.0)], sides=8, mat=G4)
    B.box(33.0, 17.5, 35.4, 22.2, 0.35, 0.80, G5, G4, ch=0.4, chz=0.03)

    # The big recessed bay: a dark face (rows 45-62.4) inside four frame bars.
    B.box(6.4, 43.2, 57.0, 65.0, DECK, 0.20, G2, G5, ch=0.001, chz=0.001)
    zf = 0.52
    B.slab([(6.4, 43.2), (12.2, 43.2), (12.2, 65.0), (6.4, 65.0)], 0.1, zf, G6, G5, ch=0.7, chz=0.06)
    B.slab([(52.6, 43.2), (57.0, 43.2), (57.0, 65.0), (52.6, 65.0)], 0.1, zf, G6, G3, ch=0.6, chz=0.06)
    B.slab([(12.2, 43.2), (52.6, 43.2), (52.6, 45.0), (12.2, 45.0)], 0.1, zf - 0.01, G7, G3, ch=0.4, chz=0.05)
    B.slab([(12.2, 62.4), (52.6, 62.4), (52.6, 65.0), (12.2, 65.0)], 0.1, zf - 0.01, G6, G3, ch=0.5, chz=0.05)
    for r in (47.5, 51.5, 55.5, 59.5):  # lamps on the outer rail
        B.ellipsoid(8.4, r, zf - 0.005, 0.75, 0.75, 0.05, G10, seg=8, rings=4)
    for c0, r0, c1, r1 in ((13.5, 47, 47.5, 47.8), (13.5, 47.8, 14.3, 60), (19, 50, 42.3, 50.8), (14.3, 53, 19.8, 53.8),
                           (19, 50.8, 19.8, 53.0), (41.5, 50.8, 42.3, 53.0), (36.8, 53, 47.5, 53.8),
                           (13.5, 60, 47.5, 60.8), (46.7, 47.8, 47.5, 53.0)):
        B.box(c0, r0, c1, r1, 0.15, 0.26, G4, G3, ch=0.15, chz=0.015)

    # Round pipe beside the bay, with clamps.
    pz, pr = 0.40, 2.4
    B.sweep([(56.3, 37.6, pz, 0.0, 0.0), (56.3, 38.2, pz, 1.9, 1.9 * PX), (56.3, 39.0, pz, pr, pr * PX),
             (56.3, 65.4, pz, pr, pr * PX), (56.3, 66.2, pz, 1.9, 1.9 * PX), (56.3, 66.8, pz, 0.0, 0.0)],
            sides=12, mat=G4)
    for r in (42.5, 52.0, 61.5):
        B.sweep([(56.3, r, pz, 2.75, 2.75 * PX), (56.3, r + 1.0, pz, 2.75, 2.75 * PX)], sides=12, mat=G6)

    # Lower block: a bevelled outer corner (the lit chamfer), a louvred vent housing and two blue fins.
    low = [(6.4, 65.0), (58.6, 65.0), (58.9, 77.0), (57.6, 78.0), (56.0, 79.0), (56.0, 82.9), (23.6, 82.9), (6.4, 65.6)]
    ltop = [(11.5, 65.0), (58.0, 65.0), (58.0, 76.2), (56.9, 77.6), (55.5, 78.6), (55.5, 82.9), (27.4, 82.9), (11.3, 65.6)]
    B.slab(low, DECK, 0.44, G4, G4, chz=0.12, top_poly=ltop, bevel=G5)
    vent = [(25.0, 65.4), (51.2, 65.4), (51.2, 76.2), (29.0, 76.2), (25.0, 72.2)]
    B.slab(vent, 0.38, 0.50, G4, G4, ch=0.5, chz=0.03)
    B.slab(inset(vent, 1.2), 0.44, 0.505, G2, G2, ch=0.01, chz=0.001)
    for r in (68.2, 70.2, 72.2, 74.2):  # louvre slats
        c0 = 26.8 + max(0.0, r - 72.0)
        B.sweep([(c0, r, 0.515, 0.0, 0.0), (c0 + 0.4, r, 0.515, 0.75, 0.035), (49.6, r, 0.515, 0.75, 0.035),
                 (50.0, r, 0.515, 0.0, 0.0)], sides=6, mat=G4, power=0.7)
    for c in (29.6, 37.6):  # blue fins
        B.slab(fillet([(c, 76.6), (c + 4.6, 76.6), (c + 4.6, 82.9), (c, 82.9)], [1.2, 1.2, 0, 0], 2), 0.38, 0.58,
               B56, B56, ch=0.8, chz=0.06)
    # Gun mount under the shoulder, the barrel slanting out (muzzle SW), its collar ring, the pod below.
    B.slab([(58.6, 63.5), (66.5, 63.5), (69.8, 66.5), (69.8, 76.6), (59.0, 76.6), (58.6, 76.2)], DECK, 0.32, G3, G3,
           ch=0.6, chz=0.04)
    bz = 0.52
    bar = [(71.6, 57.0, bz, 0.0, 0.0), (71.0, 57.6, bz, 2.9, 2.9 * PX), (69.6, 59.0, bz, 3.6, 3.6 * PX),
           (56.4, 72.0, bz, 3.3, 3.3 * PX), (55.4, 73.0, bz, 2.6, 2.6 * PX), (55.0, 73.4, bz, 0.0, 0.0)]
    B.sweep(bar, sides=12, mat=G4)
    B.sweep([(65.6, 63.0, bz, 3.95, 3.95 * PX), (64.4, 64.2, bz, 3.95, 3.95 * PX)], sides=12, mat=G9)
    B.sweep([(56.9, 71.5, bz, 2.0, 2.0 * PX), (56.2, 72.2, bz, 2.0, 2.0 * PX)], sides=10, mat=G2)  # muzzle bore
    B.ellipsoid(65.4, 80.0, DECK, 3.3, 3.0, 0.62, G3, seg=12, rings=6)


def build_centre(B):
    B.mir = False
    # Command bridge (hood): grey block, chamfered, a louvred vent on its roof.
    hood = [(84, 11.0), (107, 11.0), (107, 20.7), (111, 20.7), (111, 24.6), (102, 28.6), (102, 37), (89, 37),
            (89, 28.6), (80, 24.6), (80, 20.7), (84, 20.7)]
    B.slab(hood, DECK, 1.28, G7, G7, ch=1.0, chz=0.08)
    # The bridge's front block, a step up (rows 21-36.6).
    B.slab(fillet([(88.6, 20.8), (102.4, 20.8), (102.4, 36.6), (88.6, 36.6)], [0, 0, 1.0, 1.0], 2), 1.2, 1.34, G7, G7,
           ch=0.9, chz=0.06)
    B.box(88.4, 11.8, 102.6, 16.2, 1.2, 1.295, G3, G5, ch=0.5, chz=0.03)
    for k in range(7):  # vent louvres
        c = 89.3 + 2 * k
        B.box(c, 12.2, c + 1.0, 15.8, 1.26, 1.315, G9, G8, ch=0.25, chz=0.015)
    B.box(85.5, 17.4, 105.5, 18.4, 1.24, 1.295, G8, G6, ch=0.3, chz=0.02)  # trim rib across the roof
    for s in (0, 1):
        B.mir = bool(s)
        # Hip fairing: the roof's sloped shoulder down to the hull.
        a, b, c = (84.4, 11.1), (84.4, 20.7), (66.4, 20.7)
        lo = [(a[0], a[1], DECK), (b[0], b[1], DECK), (c[0], c[1], DECK)]
        mid = [(a[0], a[1], 1.18), (b[0], b[1], 1.18), (c[0], c[1], 0.62)]
        top = [(a[0] + 0.2, a[1] + 1.0, 1.22), (b[0] + 0.2, b[1], 1.22), (c[0] + 2.2, c[1], 0.66)]
        B.rings([lo, mid, top], G7, top=G7)
        # Blue claw at the bridge's front corner.
        claw = [(83, 25), (84.5, 25), (88.3, 28.4), (88.3, 36), (85, 38.6), (81, 40.2), (79, 40.2), (77.8, 37),
                (77.8, 34), (81, 32), (82, 26)]
        B.slab(claw, DECK, 0.86, B57, B57, ch=0.9, chz=0.07)
    B.mir = False
    # The polished black glass orb, a sphere seated deep in its black well (its lower half buried).
    oc, orow = AX, 47.6
    B.ellipsoid(oc, orow, 0.30, 11.4, 9.9, 0.82, ORB, seg=32, rings=16, upper=False)
    # Shoulder plates: curved blue armour framing the orb, a rounded-box section, flat aft end.
    for s in (0, 1):
        B.mir = bool(s)
        pts = [(63.6, 29.0), (65.6, 35.0), (67.6, 41.0), (69.6, 46.0), (72.0, 51.0), (74.4, 55.0), (76.0, 57.4)]
        hws = [6.4, 6.4, 6.3, 6.0, 5.5, 4.2, 2.2]
        hhs = [0.36, 0.36, 0.36, 0.35, 0.33, 0.27, 0.15]
        # Rising out of the black well floor (their feet are buried in it), not standing on it.
        path = [(c, r, (0.68 + hh + DECK - 0.04) / 2, hw, (0.68 + hh - DECK + 0.04) / 2)
                for (c, r), hw, hh in zip(pts, hws, hhs)]
        path.append((76.7, 58.4, 0.40, 0.0, 0.0))
        B.sweep(path, sides=20, mat=B57, power=0.28)
        B.sweep([(63.4, 29.3, 1.035, 0.0, 0.0), (63.6, 30.0, 1.035, 0.9, 0.03), (67.4, 41.0, 1.035, 0.9, 0.03),
                 (71.6, 50.4, 1.0, 0.8, 0.03), (73.2, 53.2, 0.97, 0.0, 0.0)], sides=6, mat=B58)
    B.mir = False
    # Collar: the heavy U-shaped bumper under the orb.
    half = [(70.6, 57.0, 0.60, 0.0, 0.0), (71.2, 57.7, 0.56, 3.2, 0.30), (73.5, 59.1, 0.60, 4.6, 0.42),
            (77.5, 60.7, 0.62, 5.1, 0.46), (83.5, 61.9, 0.63, 5.4, 0.48), (89.5, 62.5, 0.63, 5.5, 0.49)]
    path = half + [(AX, 62.6, 0.63, 5.5, 0.49)] + [(2 * AX - c, r, z, w, h) for c, r, z, w, h in reversed(half)]
    B.sweep(path, sides=16, mat=YOKE, power=0.85)
    B.box(73.4, 60.2, 117.6, 68.3, DECK, 0.30, G4, G4, ch=0.6, chz=0.04)
    # Chin bay: blue cheeks, a grey top bar, a hinge barrel (blue / grey / blue) and a dark relief face.
    for s in (0, 1):
        B.mir = bool(s)
        B.slab([(69.9, 71.5), (75.0, 71.5), (75.0, 83.9), (69.9, 83.9)], DECK, 0.48, G4, G4, ch=0.8, chz=0.07, bevel=B56)
    B.mir = False
    B.box(75.0, 73.4, 116.0, 75.6, DECK, 0.42, G6, G4, ch=0.5, chz=0.04)
    B.box(75.0, 75.6, 116.0, 82.9, DECK, 0.14, G2, G2, ch=0.001, chz=0.001)
    for c0, c1, hw, m in ((72.8, 91.3, 2.5, B56), (91.6, 99.4, 2.25, G6), (99.7, 118.2, 2.5, B56)):
        B.sweep([(c0, 71.2, 0.52, 0.0, 0.0), (c0 + 0.5, 71.2, 0.52, hw, hw * PX), (c1 - 0.5, 71.2, 0.52, hw, hw * PX),
                 (c1, 71.2, 0.52, 0.0, 0.0)], sides=14, mat=m, power=0.9)
    for c0, r0, c1, r1 in ((77, 78, 114, 78.8), (77, 78.8, 77.8, 82.9), (113.2, 78.8, 114, 82.9), (85, 81, 106, 81.8)):
        B.box(c0, r0, c1, r1, 0.1, 0.20, G4, G3, ch=0.15, chz=0.015)


def build(coll):
    B = L.Builder(96, 42, AX)
    build_keel(B)
    for s in (0, 1):
        B.mir = bool(s)
        build_wing(B)
    build_centre(B)
    return B.to_object(NAME, MAT.list, coll)


# --------------------------------------------------------------------------------------------------
# Pieces, shell, export
# --------------------------------------------------------------------------------------------------

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    obj = build(coll)
    print("whole tris", L.tris(obj))
    lay = L.layout(ROOT, PIECES, CX0, CY0)
    pieces, shells = L.shell_and_split(obj, lay, coll)
    total = sum(L.tris(p) for p in pieces.values())
    print("pieces total tris", total, "shell tris", sum(L.tris(s) for s in shells.values()))
    if "--noexport" not in argv:  # the game contract, as the old script
        for name in PIECES:
            common.export_sprite_model(ROOT, [pieces[name], shells[name]], f"enemies/{name}",
                                       common.load_sprite(ROOT, name)["sprites"])
    L.place(pieces, shells, lay)
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
        common.export_glb(list(pieces.values()) + list(shells.values()), out)
        print("exported", out)
    if "--review" in argv:
        obj.hide_render = True
        L.review(list(shells.values()), argv[argv.index("--review") + 1], W, H, quick="--quick" in argv,
                 stats={"tris": total, "pal": sorted({k[0] for k in MAT.slots})})


if __name__ == "__main__":
    main()
