"""SuperCarrot (player ship, tyrian.shp#8 frame 119 and its banking frames 115-123): a 3D version
of its sprite, shaped after its concept art (features/concepts/ship-supercarrot.jpg).

An armoured carrot pod, point up the screen: a bullet-nosed root as round in section as it is wide,
built of overlapping orange armour plates whose seams arch forward over the top (the sprite's
light ridge rings at rows 6, 8 and 14 read as those plate lips), a darker tip cap and a dark
collar band at its rounded back; one eye, a glossy copper lens in a round bronze housing with a
dark recessed ring and a glowing pale pupil; and behind it, where the sprite draws a three-leaf
tuft, a green mechanical tail: a dark stem with cables, three thin hard-edged armour fins (the
leaves: one out to the left, a long keel down the middle with a light raised spine, one out to the
right) and small engine pods between them with green-glowing nozzles. Centred on sprite column
11.5; the parts sit where the registered concept (textures/ship-supercarrot/concept.png) draws
them, so its baked detail lands on the matching part.

Run: blender --background --python assets/blender/ships/ship-supercarrot.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import bmesh  # noqa: E402

import common  # noqa: E402
from lib_b002 import P, X, Y, dome, loft, tube  # noqa: E402

NAME = "ship-supercarrot"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = 11.5  # the middle of sprite column 11
EYE = (11.6, 11.7)  # the eye housing's centre (pixel edges), where the concept draws it
SIDES = 28  # round sections of the root

BODY_SHADE = 121  # the armour plates' orange (the sprite's commonest body colour)
LIP_SHADE = 122  # the plate lips (the sprite's light ridge rings)
TIP_SHADE = 120  # the darker red-orange tip cap
COLLAR_SHADE = 120  # the darker collar band at the back
BACK_SHADE = 118  # the dark red back of the root
RIM_SHADE = 182  # the eye housing's bronze rim
DARK_SHADE = 179  # the housing's recessed dark ring
RING_SHADE = 181  # the segmented inner ring
COLLAR_EYE_SHADE = 183  # the bronze collar round the lens
LENS_SHADE = 184  # the copper lens
PUPIL_SHADE = 126  # the glowing pale pupil
FIN_SHADE = 197  # the green armour fins (the leaves)
SPINE_SHADE = 200  # the keel's light raised spine (the sprite's midrib)
STEM_SHADE = 194  # the dark green stem
POD_SHADE = 193  # the engine pods, dark green metal
CABLE_SHADE = 180  # the cables
GLOW_SHADE = 205  # the nozzles' green glow

# The root's half width (px) at row edges, tip (row 0) to back (row 19.3): the concept's bullet
# outline, kept over the sprite's outline ring.
BODY = [(0.0, 0.0), (0.15, 0.45), (0.5, 0.85), (1.0, 1.2), (2.0, 1.6), (3.0, 2.3), (4.0, 2.6),
        (5.0, 3.15), (6.0, 3.6), (7.0, 4.1), (8.0, 4.45), (8.5, 4.6), (9.0, 4.75), (9.5, 4.9),
        (10.0, 5.05), (10.5, 5.2), (11.0, 5.3), (11.5, 5.45), (12.0, 5.6), (12.5, 5.8), (13.0, 6.0),
        (13.5, 6.15), (14.0, 6.3), (14.5, 6.35), (15.0, 6.45), (16.0, 6.4), (17.0, 5.9), (18.0, 4.95),
        (18.6, 4.3), (19.0, 3.4), (19.2, 2.0), (19.3, 0.0)]

# Plate seams: (row at the sides, row over the top centre, lip rise px). The concept's plate seams
# arch forward over the top (stacked chevrons); the one below the eye dips round its housing.
SEAMS = [(4.0, 2.0, 0.22), (6.2, 4.0, 0.25), (9.0, 7.0, 0.28), (13.0, 14.9, 0.3), (17.3, 17.3, 0.3),
         (18.4, 18.4, 0.22)]


def half_width(row):
    """The root's half width (px) at a row (pixel edges)."""
    row = min(max(row, 0.0), BODY[-1][0])
    return next(w0 + (w1 - w0) * (row - r0) / (r1 - r0)
                for (r0, w0), (r1, w1) in zip(BODY, BODY[1:]) if r0 <= row <= r1)


def ring_angles(n):
    return [2 * math.pi * (i + 0.5) / n for i in range(n)]


def seam_lip(bm, side_row, top_row, rise, mat, width=0.45):
    """A plate lip round the root: a raised band (rise px proud) following the round section, at
    side_row on the flanks and arching to top_row over the top. Its front edge is steep, its back
    slopes onto the next plate."""
    rings = []
    for dr, lift in ((-width * 0.5, 0.02), (-width * 0.3, rise), (width * 0.15, rise * 0.85), (width * 0.5, 0.02)):
        ring = []
        for a in ring_angles(SIDES):
            u, v = math.cos(a), math.sin(a)
            s = max(v, 0.0) ** 1.5
            row = side_row + (top_row - side_row) * s + dr
            r = half_width(row) + lift
            ring.append(bm.verts.new((X(AXIS) + P(r) * u, Y(row), P(r) * v)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(SIDES):
            j = (i + 1) % SIDES
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).material_index = mat


def annulus(bm, c, r, r_in, r_out, z_top, z_bot, mat, sides=24, z_in=None, mat_in=None):
    """A flat ring round (col, row) c, r between radii r_in and r_out (px) with its top at z_top;
    the outer wall drops to z_bot, the inner wall to z_in (default z_bot)."""
    z_in = z_bot if z_in is None else z_in
    pts = [(math.cos(2 * math.pi * i / sides), math.sin(2 * math.pi * i / sides)) for i in range(sides)]

    def ring(rad, z):
        return [bm.verts.new((X(c + rad * u), Y(r + rad * v), P(z))) for u, v in pts]

    ob, ot, it, ib = ring(r_out, z_bot), ring(r_out, z_top), ring(r_in, z_top), ring(r_in, z_in)
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((ob[i], ob[j], ot[j], ot[i])).material_index = mat
        bm.faces.new((ot[i], ot[j], it[j], it[i])).material_index = mat
        bm.faces.new((it[i], it[j], ib[j], ib[i])).material_index = mat if mat_in is None else mat_in


def disc(bm, c, r, rad, z, mat, sides=24):
    verts = [bm.verts.new((X(c + rad * math.cos(2 * math.pi * i / sides)), Y(r + rad * math.sin(2 * math.pi * i / sides)),
                           P(z))) for i in range(sides)]
    bm.faces.new(verts).material_index = mat


def plate(bm, outline, z0, z1, mat, droop=0.0):
    """A thin hard-edged armour plate: the outline (col, row pixel edges) extruded between heights
    z0 and z1 (px), its outer parts lowered by `droop` px per px from the axis (a fin that slopes
    down outward)."""
    area = sum(c0 * r1 - c1 * r0 for (c0, r0), (c1, r1) in zip(outline, outline[1:] + outline[:1]))
    pts = list(outline) if area < 0 else list(reversed(outline))  # anticlockwise in Blender XY
    dz = [-droop * abs(c - AXIS) for c, _ in pts]
    bot = [bm.verts.new((X(c), Y(r), P(z0 + d))) for (c, r), d in zip(pts, dz)]
    top = [bm.verts.new((X(c), Y(r), P(z1 + d))) for (c, r), d in zip(pts, dz)]
    bm.faces.new(top).material_index = mat
    bm.faces.new(list(reversed(bot))).material_index = mat
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i])).material_index = mat


def pod(bm, c, r0, r1, rad, z, mat, glow):
    """An engine pod along the rows r0 to r1 at column c, with a glowing nozzle at its back."""
    tube(bm, [(c, r0, rad * 0.75, rad * 0.75, z), (c, r0 + 0.3, rad, rad, z), (c, r1 - 0.45, rad, rad, z),
              (c, r1 - 0.3, rad * 0.8, rad * 0.8, z)], sides=8, mat=mat)
    tube(bm, [(c, r1 - 0.32, rad * 0.62, rad * 0.62, z), (c, r1, rad * 0.62, rad * 0.62, z)], sides=8, mat=glow)


def build(sprite):
    coll = common.reset_collection(NAME)

    (BODY_T, LIP, RIM, DARK, RING, ECOLLAR, LENS, PUPIL, FIN, SPINE, STEM, POD, CABLE,
     GLOW) = range(14)  # part tags, repainted below
    bm = bmesh.new()

    # The root: a round loft, tip to back.
    before = set(bm.verts)
    loft(bm, [(r, AXIS, w, w, 0.0) for r, w in BODY], sides=SIDES, mat=BODY_T)
    # Press the root down inside the eye housing so the housing's recessed rings show.
    for v in set(bm.verts) - before:
        d = math.hypot(v.co.x - X(EYE[0]), v.co.y - Y(EYE[1])) * 12
        if v.co.z > 0 and d < 3.2:
            v.co.z = min(v.co.z, P(4.3))
    for side_row, top_row, rise in SEAMS:
        seam_lip(bm, side_row, top_row, rise, LIP)

    # The eye: a bronze housing ring set into the top of the root, a recessed dark ring with a
    # segmented inner ring, a bronze collar and the copper lens with its glowing pupil.
    annulus(bm, *EYE, 2.45, 3.0, 5.45, 3.6, RIM, sides=28, z_in=4.75)
    disc(bm, *EYE, 2.5, 4.8, DARK, sides=24)
    annulus(bm, *EYE, 1.55, 2.1, 5.05, 4.75, RING, sides=20)
    annulus(bm, *EYE, 1.0, 1.45, 5.3, 4.75, ECOLLAR, sides=20)
    dome(bm, EYE[0], EYE[1], 1.05, 1.05, 0.85, z=5.0, rings=4, sides=16, mat=LENS)
    dome(bm, 11.5, 11.45, 0.42, 0.42, 0.2, z=5.72, rings=2, sides=10, mat=PUPIL)

    # The stem: a dark block out of the root's back, with a cable either side.
    tube(bm, [(AXIS, 18.3, 2.3, 1.8, 0.3), (AXIS, 19.4, 2.25, 1.5, 0.4), (11.3, 20.9, 1.8, 1.1, 0.4)],
         sides=8, mat=STEM, power=0.6)
    for path in ([(9.8, 18.6), (9.3, 19.3), (9.4, 20.2), (10.1, 20.9)],
                 [(13.2, 18.6), (13.45, 19.3), (13.1, 20.0), (12.6, 20.7)]):
        tube(bm, [(c, r, 0.3, 0.3, 0.9) for c, r in path], sides=6, mat=CABLE)

    # The engine pods between the fins, nozzles glowing at their backs.
    for c, r0, r1, rad in ((8.55, 21.6, 24.0, 0.55), (7.3, 22.7, 24.7, 0.42), (13.0, 21.6, 24.4, 0.55),
                           (14.1, 22.6, 24.7, 0.5), (12.4, 24.0, 25.8, 0.42)):
        pod(bm, c, r0, r1, rad, 0.35, POD, GLOW)
    # The dark machinery deck the fins and pods are bolted to.
    plate(bm, [(7.0, 20.6), (14.2, 20.6), (15.3, 22.4), (15.3, 24.6), (9.0, 24.6), (8.0, 23.9), (6.6, 23.9),
               (6.4, 21.5)], -0.4, 0.1, POD)

    # The fins (the sprite's three leaves), thin hard-edged armour plates traced from the concept.
    plate(bm, [(7.6, 20.0), (8.5, 20.5), (7.3, 21.8), (6.9, 22.6), (6.8, 24.6), (6.75, 25.6), (6.1, 26.3), (6.0, 26.9),
               (5.05, 26.9), (5.05, 23.4), (5.7, 22.3), (5.9, 21.3), (6.6, 20.9)], 0.5, 1.1, FIN, droop=0.12)
    plate(bm, [(6.6, 21.1), (9.9, 20.6), (9.9, 21.6), (7.0, 22.3)], 0.3, 0.8, FIN, droop=0.1)  # strut
    plate(bm, [(9.9, 22.6), (10.3, 22.6), (10.3, 26.8), (9.1, 26.6), (9.1, 24.0)], 0.4, 1.0, FIN, droop=0.1)
    plate(bm, [(12.2, 20.1), (12.9, 20.5), (15.9, 22.2), (15.95, 24.9), (15.2, 24.9), (15.0, 22.9),
               (12.9, 21.1)], 0.5, 1.1, FIN, droop=0.12)
    # The keel down the middle (the middle leaf), with its light raised spine (the midrib).
    plate(bm, [(10.0, 20.2), (12.6, 20.2), (12.6, 24.4), (11.7, 25.6), (11.5, 27.9), (10.1, 27.9), (10.0, 26.0)],
          0.6, 1.6, FIN)
    plate(bm, [(10.5, 21.0), (12.0, 21.0), (12.0, 24.0), (11.3, 25.0), (11.15, 27.0), (10.55, 27.0)],
          1.6, 1.9, SPINE)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    slots, mats = {}, []

    def slot(i, **kw):
        if i not in slots:
            slots[i] = len(mats)
            mats.append(common.palette_material(sprite, i, NAME, **kw))
        return slots[i]

    # Each part its mid-tone, lit by the game (the sprite's outline, flanks and highlight are its
    # light). Armour plates semi-matte, bronze eye parts metallic, the lens glossy, the pupil and
    # the nozzles emissive, the fins flat shaded and only lightly metallic so they stay crisp.
    smooth_parts = (BODY_T, LIP, LENS, PUPIL, STEM, POD, CABLE, GLOW)
    for f in bm.faces:
        c = f.calc_center_median()
        row = 14 - c.y * 12
        part = f.material_index
        f.smooth = part in smooth_parts
        if part == BODY_T:
            v = max(c.z * 12 / max(half_width(row), 0.3), 0.0)
            if row < 4.0 - 2.0 * min(v, 1.0) ** 1.5:  # the tip cap, ahead of the first seam
                f.material_index = slot(TIP_SHADE, metallic=0.15, roughness=0.5)
            elif row > 18.4:
                f.material_index = slot(BACK_SHADE, metallic=0.15, roughness=0.6)
            elif row > 17.3:
                f.material_index = slot(COLLAR_SHADE, metallic=0.15, roughness=0.55)
            else:
                f.material_index = slot(BODY_SHADE, metallic=0.15, roughness=0.5)
        elif part == LIP:
            f.material_index = slot(LIP_SHADE, metallic=0.15, roughness=0.45)
        elif part == RIM:
            f.material_index = slot(RIM_SHADE, metallic=0.6, roughness=0.4)
        elif part == DARK:
            f.material_index = slot(DARK_SHADE, metallic=0.3, roughness=0.7)
        elif part == RING:
            f.material_index = slot(RING_SHADE, metallic=0.5, roughness=0.5)
        elif part == ECOLLAR:
            f.material_index = slot(COLLAR_EYE_SHADE, metallic=0.6, roughness=0.35)
        elif part == LENS:
            f.material_index = slot(LENS_SHADE, metallic=0.3, roughness=0.12)
        elif part == PUPIL:
            f.material_index = slot(PUPIL_SHADE, metallic=0.0, roughness=0.2, emission_strength=3.0)
        elif part == FIN:
            f.material_index = slot(FIN_SHADE, metallic=0.15, roughness=0.55)
        elif part == SPINE:
            f.material_index = slot(SPINE_SHADE, metallic=0.15, roughness=0.5)
        elif part == STEM:
            f.material_index = slot(STEM_SHADE, metallic=0.3, roughness=0.6)
        elif part == POD:
            f.material_index = slot(POD_SHADE, metallic=0.35, roughness=0.55)
        elif part == CABLE:
            f.material_index = slot(CABLE_SHADE, metallic=0.1, roughness=0.7)
        else:  # the nozzle glow
            f.material_index = slot(GLOW_SHADE, metallic=0.0, roughness=0.4, emission_strength=2.5)

    bm.faces.index_update()
    flat = {f.index for f in bm.faces if not f.smooth}
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    for poly in obj.data.polygons:
        poly.use_smooth = poly.index not in flat
    return obj


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        level = sprite["frames"][len(sprite["frames"]) // 2]
        ref = ROOT / "reference" / "models" / NAME / level["image"]
        common.render_preview([obj], out, ref, size=level["size"])


if __name__ == "__main__":
    main()
