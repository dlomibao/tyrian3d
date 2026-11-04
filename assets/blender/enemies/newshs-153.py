"""Red lamp panel (newshs.shp frames 153-163): a hard-surface 3D version of its sprite.

What the sprite shows (24 x 28, it fills its whole frame, no ink border: tools/sprite_mask.py says
full-rect, so the top view goes to the frame's outer edge): three lamp modules stacked down the
panel, each a grey machined bezel (palette 8; its bright top and left lines are the chamfers
catching the light from the upper left) round a capsule-shaped bay 18 x 7 px. In the bay a dark
red reflector lip (113) and a domed red glass lens whose rings go 113 / 114 / 115 from the edge
in when it is off. Down the right side (columns 20-23) a riser beam carries a conduit: a lit inner
rail (7), a channel (5) with a pipe in it (6), a dark outer rail (4), clamped at the top of every
module. The top row is the base frame (5) the modules sit on.

In the game (levels 1.21, 1.5, 1.6, 2.8, 3.15; e.g. ASTEROID2, episode 1 main 6) the panels stack
end to end into long light strips down both sides of the playfield, so the beam, the pipe and the
base run flush to the panel's top and bottom edges and the module rhythm continues across the joins.

Frames: one model covers all six; the lamps light in turn (bottom on 153/155, middle on 157/159,
top on 161/163, "lit" then "brightest"). Each lamp's four lens zones (reflector lip, outer band,
inner band, core) are palette materials with frames= (D17), their indices per state measured from
the sprite: lip 113/114/115, band 113/115/119, inner 114/117/120, core 115/117/120.

Style: usp_talon parts (D50-D53), AO/roughness bake of the metal embedded in the GLB (no concept
projection), outline shell (D51). The underside is a plain closed slab.

Sprite px: x = column edge - 12, y = row edge (0 top .. 28 bottom), z up; usp_talon.finish maps
X = x/12, Y = (14 - y)/12, Z = z/12.

Run: blender --background --factory-startup --python assets/blender/enemies/newshs-153.py
     [-- --no-bake] [--preview out.png] [--matmap out.json]
"""


import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh  # noqa: F401
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part, cbox, hull  # noqa: E402

NAME = "newshs-153"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
FRAMES = [153, 155, 157, 159, 161, 163]

# --- materials ---------------------------------------------------------------------------------
# Metal: palette index per region = the median of the sprite's pixels there (dark shading and
# bright edge lines left out as lighting).
METAL = [
    # tag, palette index, metallic, roughness
    ("base", 5, 0.35, 0.55),      # base frame (top row, median 5)
    ("bezel", 8, 0.4, 0.42),      # lamp module bezels (rows 1/10/19 and columns 0-1, median 8)
    ("bezel_low", 7, 0.4, 0.44),  # the bezels' lower lips (rows 9/18/27, median 7)
    ("rail_in", 7, 0.45, 0.4),    # beam inner rail (columns 19-20, median 7)
    ("channel", 5, 0.3, 0.6),     # conduit channel floor (column 21, median 5)
    ("pipe", 6, 0.5, 0.35),       # conduit (column 22, median 6)
    ("rail_out", 4, 0.4, 0.5),    # beam outer rail (column 23, median 4)
    ("clamp", 7, 0.5, 0.38),      # pipe clamps (rows 0-1, 10, 19 on the beam)
    ("bolt", 9, 0.6, 0.3),        # screw heads
    ("seam", 3, 0.2, 0.7),        # panel-line grooves
]
(BASE, BEZEL, BEZEL_LOW, RAIL_IN, CHAN, PIPE, RAIL_OUT, CLAMP, BOLT, SEAM) = range(len(METAL))
# Lamp lens zones: index per lamp state (0 off, 1 lit, 2 brightest), from the sprite.
ZONES = [("lip", [113, 114, 115], 0.6), ("band", [113, 115, 119], 0.8),
         ("inner", [114, 117, 120], 1.0), ("core", [115, 117, 120], 1.1)]
# Each lamp's state per frame, by its lens top row.
LAMPS = {2: [0, 0, 0, 0, 1, 2], 11: [0, 0, 1, 2, 0, 0], 20: [1, 2, 0, 0, 0, 0]}
TINT = (0.97, 0.98, 1.0)


def materials(sprite):
    mats, info = [], {}
    for tag, idx, met, rough in METAL:
        m = common.palette_material(sprite, idx, f"n153_{tag}", metallic=met, roughness=rough)
        mats.append(m)
        info[m.name] = {"index": idx}
    lens = {}
    for t, states in LAMPS.items():
        for zi, (tag, shades, strength) in enumerate(ZONES):
            idx = [shades[s] for s in states]
            frames = {f: i for f, i in zip(FRAMES, idx) if i != idx[0]}
            m = common.palette_material(sprite, idx[0], f"n153_{tag}{t}", metallic=0.0, roughness=0.22,
                                        emission_strength=strength, frames=frames)
            lens[(t, zi)] = len(mats)
            mats.append(m)
            info[m.name] = {"index": idx[0], "frames": {str(f): i for f, i in zip(FRAMES, idx)}}
    return mats, lens, info


# --- outlines ----------------------------------------------------------------------------------

def rrect(cx, cy, hw, hh, r, k=8, m=6):
    """Rounded rectangle loop (corner arcs of k+1 points, m points inside each long side, none
    inside the short sides), always the same point count, so rings of it bridge with quads. A
    stadium is r = hh (kept a hair under so the short sides don't collapse to one point)."""
    r = max(0.02, min(r, hh - 0.01, hw - 0.01))
    pts = []
    centres = [(cx + hw - r, cy + hh - r), (cx - hw + r, cy + hh - r), (cx - hw + r, cy - hh + r),
               (cx + hw - r, cy - hh + r)]
    for i, (ox, oy) in enumerate(centres):
        a0 = math.pi / 2 * i
        arc = [(ox + r * math.cos(a0 + math.pi / 2 * j / k), oy + r * math.sin(a0 + math.pi / 2 * j / k))
               for j in range(k + 1)]
        pts += arc
        if i % 2 == 0:  # after corners 0 and 2 comes a long (horizontal) side
            nx, ny = centres[(i + 1) % 4]
            a1 = a0 + math.pi / 2
            p0 = arc[-1]
            p1 = (nx + r * math.cos(a1), ny + r * math.sin(a1))
            pts += [(p0[0] + (p1[0] - p0[0]) * s / (m + 1), p0[1] + (p1[1] - p0[1]) * s / (m + 1))
                    for s in range(1, m + 1)]
    return pts


def ring_loft(P, rings, mats, cap=None, cap_mat=None):
    """Quads between consecutive rings [(pts, z, hint)] where hint is 'up' (faces point up) or a
    point the faces point away from; mats[i] is the material of band i. cap: 'top' closes the last
    ring facing up, 'bottom' closes the first facing down."""
    vs = [[P.v((x, y, z)) for x, y in pts] for pts, z, _ in rings]
    for i in range(len(rings) - 1):
        hint = rings[i][2]
        a, b = vs[i], vs[i + 1]
        n = len(a)
        for j in range(n):
            jj = (j + 1) % n
            q = (a[j], a[jj], b[jj], b[j])
            if hint == "up":
                P.f(q, mats[i], out=(0, 0, 1))
            else:
                P.f(q, mats[i], away=hint)
    if cap == "top":
        P.f(vs[-1], cap_mat, out=(0, 0, 1))
    if cap == "bottom":
        P.f(vs[0], cap_mat, out=(0, 0, -1))
    return vs


def tube_y(P, x, z, r, y0, y1, mat, sides=12, cap0=True, cap1=True):
    """A round tube along y."""
    ring = lambda y: [P.v((x + r * math.cos(2 * math.pi * k / sides), y, z + r * math.sin(2 * math.pi * k / sides)))
                      for k in range(sides)]
    a, b = ring(y0), ring(y1)
    for k in range(sides):
        kk = (k + 1) % sides
        P.f((a[k], a[kk], b[kk], b[k]), mat, away=(x, (y0 + y1) / 2, z))
    if cap0:
        P.f(a, mat, out=(0, -1, 0))
    if cap1:
        P.f(b, mat, out=(0, 1, 0))


def bolt(P, x, y, z, r=0.32, h=0.25, mat=BOLT, sides=6):
    """A hex screw head standing on z."""
    lo = [P.v((x + r * math.cos(2 * math.pi * k / sides + 0.3), y + r * math.sin(2 * math.pi * k / sides + 0.3), z - 0.1))
          for k in range(sides)]
    hi = [P.v((x + 0.85 * r * math.cos(2 * math.pi * k / sides + 0.3), y + 0.85 * r * math.sin(2 * math.pi * k / sides + 0.3), z + h))
          for k in range(sides)]
    for k in range(sides):
        kk = (k + 1) % sides
        P.f((lo[k], lo[kk], hi[kk], hi[k]), mat, away=(x, y, z))
    P.f(hi, mat, out=(0, 0, 1))


# --- parts -------------------------------------------------------------------------------------
Z_BASE = 2.0      # top of the base frame
Z_BEZ = 4.3       # top of the lamp bezels
LENS_X = (-10.0, 8.0)   # lens bay: columns 2-19
BAY_HH = 3.5      # lens bay half height (rows t .. t+7)


def build_base(P):
    """The base frame: one slab under the whole tile, closed underneath (plain belly)."""
    hull(P, cbox(-12.0, 12.0, 0.0, 28.0, -0.6, Z_BASE, 0.0, 0.0), BASE)
    # Panel-line grooves across its top between the panels' joins show at row 0 only: a shallow
    # dark seam strip just inside the top edge (the sprite's row 0 has its darkest pixels there).
    hull(P, cbox(-11.6, 7.9, 0.25, 0.55, Z_BASE - 0.1, Z_BASE + 0.05, 0.0, 0.0), SEAM)
    # Side and end faces: recessed vent slots on the long west side, between the modules' feet, and
    # on the south end (seen by the tilted game camera).
    for y0 in (3.0, 6.0, 12.0, 15.0, 21.0, 24.0):
        hull(P, cbox(-12.12, -11.9, y0, y0 + 1.8, -0.1, 1.2, 0.0, 0.0), SEAM)
    for x0 in (-9.5, -5.5, -1.5, 2.5):
        hull(P, cbox(x0, x0 + 2.6, 27.9, 28.12, -0.1, 1.1, 0.0, 0.0), SEAM)


def build_module(P, D, mats, lens, t):
    """One lamp module: a chamfered bezel round a capsule bay, a red reflector lip sloping down into
    it and a domed lens in four glowing zones. t = the lens bay's top row."""
    y0, y1 = t - 1 + 0.08, t + 8 - 0.08
    ox0, ox1 = -12.0, 8.6
    ocx, ocy, ohw, ohh = (ox0 + ox1) / 2, (y0 + y1) / 2, (ox1 - ox0) / 2, (y1 - y0) / 2
    bcx, bcy = (LENS_X[0] + LENS_X[1]) / 2, t + BAY_HH
    bhw = (LENS_X[1] - LENS_X[0]) / 2
    centre = (ocx, ocy, 1.0)

    def bay(off):  # the bay's stadium grown by off (negative: inside the lens)
        return rrect(bcx, bcy, bhw + off, BAY_HH + off, BAY_HH + off)

    rect = lambda inset, r=0.9: rrect(ocx, ocy, ohw - inset, ohh - inset, r - inset * 0.6)
    lip, band, inner, core = (lens[(t, z)] for z in range(4))
    # Dome profile: depth into the lens d (px from the bay edge) -> z.
    def dz(d):
        return 2.95 + 1.15 * math.sin(math.pi / 2 * min(1.0, (d - 1.0) / 2.35))
    rings = [
        (rect(0.0), 1.2, centre),           # foot (sunk into the base)
        (rect(0.0), Z_BEZ - 0.55, "up"),    # wall
        (rect(0.5), Z_BEZ, "up"),           # outer chamfer (the bright top / left line)
        (bay(0.42), Z_BEZ, "up"),           # flat bezel top
        (bay(0.0), Z_BEZ - 0.35, "up"),     # inner bevel down to the lip
        (bay(-0.5), 3.35, "up"),            # reflector lip, sloping into the bay
        (bay(-1.0), dz(1.0), "up"),         # lens edge
        (bay(-1.5), dz(1.5), "up"),
        (bay(-2.0), dz(2.0), "up"),
        (bay(-2.45), dz(2.45), "up"),
        (bay(-2.9), dz(2.9), "up"),
        (bay(-3.12), dz(3.12), "up"),
        (bay(-3.3), dz(3.3), "up"),
    ]
    band_mats = [BEZEL, BEZEL, BEZEL, BEZEL, lip, lip, band, band, inner, inner, core, core]
    first = len(P.hints)
    vs = ring_loft(P, rings, band_mats, cap="top", cap_mat=core)
    # Close the foot underneath (hidden in the base; keeps the part watertight).
    P.f(vs[0], BEZEL, out=(0, 0, -1))
    # The lower lip below the bay takes the sprite's index there (rows t+7: 7, not 8).
    for face, _, _ in P.hints[first:]:
        if face.is_valid and face.material_index == BEZEL and face.calc_center_median().y > t + 7.0:
            face.material_index = BEZEL_LOW
    # Screw heads on the bezel's wide left band, two per module.
    for yy in (t + 0.9, t + 6.1):
        bolt(D, -11.05, yy, Z_BEZ)
    # A machined index notch on the bezel's top edge (the sprite's dark nick on each module's lower
    # lip, column 13): a small dark slot.
    hull(D, cbox(0.6, 1.5, t + 7.35, t + 7.85, Z_BEZ - 0.25, Z_BEZ + 0.02, 0.0, 0.0), SEAM)


def build_beam(P, D):
    """The riser beam down the right side (columns 20-23): inner rail, channel, conduit pipe, outer
    rail with bolted side plates, and a clamp over the pipe at the top of every module."""
    # Inner rail with its lit chamfer toward the lamps (column 20's bright line).
    hull(P, [(8.0, y, z) for y in (0.0, 28.0) for z in (0.0, 4.15)] +
         [(8.55, y, 4.75) for y in (0.0, 28.0)] + [(9.0, y, z) for y in (0.0, 28.0) for z in (0.0, 4.75)], RAIL_IN)
    hull(P, cbox(9.0, 11.1, 0.0, 28.0, 0.0, 2.9, 0.0, 0.0), CHAN)
    # Outer rail (its outer face a hair inside the edge, the side plates finish it).
    hull(P, [(11.1, y, z) for y in (0.0, 28.0) for z in (0.0, 4.75)] +
         [(11.6, y, 4.75) for y in (0.0, 28.0)] + [(11.85, y, z) for y in (0.0, 28.0) for z in (0.0, 4.5)], RAIL_OUT)
    for t in LAMPS:  # side plates, one per module, seams at the module joins
        y0, y1 = t - 1 + 0.18, t + 8 - 0.18
        hull(D, cbox(11.8, 12.0, y0, y1, 0.35, 4.2, 0.1, 0.1), RAIL_OUT)
        for yy in (y0 + 0.9, y1 - 0.9):
            for zz in (1.1, 3.4):
                D_bolt_side(D, 12.0, yy, zz)
    # Conduit: runs flush end to end so stacked panels join into one line (column 22).
    tube_y(D, 10.5, 3.52, 0.62, 0.0, 28.0, PIPE, sides=14)
    for y in (0.35, 9.55, 18.55):
        hull(D, cbox(9.0, 11.1, y, y + 1.1, 2.9, 3.25, 0.12, 0.08), CLAMP)  # foot plate
        pts = []
        for yy in (y + 0.12, y + 0.98):
            for k in range(9):
                a = math.pi * k / 8
                pts.append((10.5 + 0.82 * math.cos(a), yy, 3.52 + 0.82 * math.sin(a)))
        hull(D, pts, CLAMP)  # the strap over the pipe
        bolt(D, 9.35, y + 0.55, 3.25, r=0.24, h=0.2)


def D_bolt_side(D, x, y, z, r=0.2, h=0.12, sides=6):
    """A hex screw head on an east-facing (+x) face."""
    lo = [D.v((x - 0.05, y + r * math.cos(2 * math.pi * k / sides), z + r * math.sin(2 * math.pi * k / sides)))
          for k in range(sides)]
    hi = [D.v((x + h, y + 0.85 * r * math.cos(2 * math.pi * k / sides), z + 0.85 * r * math.sin(2 * math.pi * k / sides)))
          for k in range(sides)]
    for k in range(sides):
        kk = (k + 1) % sides
        D.f((lo[k], lo[kk], hi[kk], hi[k]), BOLT, away=(x, y, z))
    D.f(hi, BOLT, out=(1, 0, 0))


def build(coll, sprite):
    mats, lens, info = materials(sprite)
    P = Part("n153_body", smooth_angle=35)
    D = Part("n153_detail", smooth_angle=40)
    build_base(P)
    for t in LAMPS:
        build_module(P, D, mats, lens, t)
    build_beam(P, D)
    return [T.finish(p, mats, coll) for p in (P, D)], mats, info


def bake_maps(obj, out_dir, mats):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT = TINT
    T.TEXTURED = tuple(range(len(METAL)))  # metal only; the glowing lenses stay plain
    try:
        T.bake_maps(obj, out_dir, size=1024, samples=96)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", "n153")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    objs, mats, info = build(coll, sprite)
    obj = T.join(objs, NAME)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    if "--matmap" in argv:
        Path(argv[argv.index("--matmap") + 1]).write_text(json.dumps(info, indent=1))
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix="nshs153_bake_"), mats)
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, voxel=0.016, faces=1500, smooth=16)
    common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)
    if "--preview" in argv:
        shell.hide_render = True
        f = sprite["frames"][0]
        common.render_preview([obj], argv[argv.index("--preview") + 1],
                              ROOT / "reference" / "models" / NAME / f["image"], size=2, frame=f["index"])


if __name__ == "__main__":
    main()
