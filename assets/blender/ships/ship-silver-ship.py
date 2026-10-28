"""Silver Ship (player ship, tyrian.shp#8 frame 81 and its banking frames 77-85): a 3D version of
its sprite.

A grey fighter, nose up the screen, built around column 11 of the sprite: a pointed fuselage with
a dark canopy, small swept fins beside the canopy, two side pods hugging the rear fuselage with
red striped engines at their backs, and three ribs on the tail. The banking frames show the pods
sit low beside a raised fuselage.

The faces take the palette shades the sprite shows where they are seen from above: the fuselage is
light grey with a white strip down column 9, mid grey on its left flank (column 8) and dark on its
right one (column 14, and the nose right of column 12); the left pod's inner slope is mid grey.

Run: blender --background --python assets/blender/ships/ship-silver-ship.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import math  # noqa: E402

import bmesh  # noqa: E402

import common  # noqa: E402
from lib_b002 import H, W, P, X, Y, _ring_point, loft, mirror, slab  # noqa: E402

NAME = "ship-silver-ship"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = 11.5  # the ship's centreline: the middle of sprite column 11


def ridge(bm, sections, sides, mat, power, dark=None, dark_mat=0, rim=None, nose=None, paint=None):
    """loft() for the fuselage, with a cut-in canopy: dark = (row0, row1, half_width, depth) in px.
    Ring vertices on top within half_width of the axis, between those rows, sink by depth, and the
    faces between them take dark_mat, so the canopy is a dark well in the nose, not a dome.
    rim = (mat, side): faces on the side's flank (+1 right, -1 left, 0 both) take that darker
    material. nose = (mat, row): faces ahead of that row take mat. paint(col, row, cu, cv) returns
    a material (or None to keep it) for a face from where it is seen from above (col, row of its
    centre in sprite px) and which way it faces (cu, cv: cosine and sine of its angle round the
    ring), so the faces follow the sprite's shading."""
    rings = []
    for r, c, hw, hh, z in sections:
        y, x = Y(r), X(c)
        if hw == 0 and hh == 0:
            rings.append((r, [bm.verts.new((x, y, P(z)))]))
            continue
        sink = dark and dark[0] < r < dark[1]
        ring = []
        for i in range(sides):
            u, v = _ring_point(2 * math.pi * (i + 0.5) / sides, power)
            vz = z + hh * v
            if sink and v > 0 and abs(hw * u) < dark[2]:
                vz -= dark[3]
            ring.append(bm.verts.new((x + P(hw) * u, y, P(vz))))
        rings.append((r, ring))
    for (ra, r0), (rb, r1) in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            f = bm.faces.new(face)
            f.material_index = mat
            a = 2 * math.pi * (i + 1) / sides
            cu = math.cos(a)
            if rim and (abs(cu) if rim[1] == 0 else rim[1] * cu) > rim[2]:
                f.material_index = rim[0]
            if nose and rb <= nose[1] + 0.01:
                f.material_index = nose[0]
            ctr = f.calc_center_median()
            if paint:
                m = paint(ctr.x * 12 + W / 2, H / 2 - ctr.y * 12, cu, math.sin(a))
                if m is not None:
                    f.material_index = m
            if dark and dark[0] - 0.01 <= ra and rb <= dark[1] + 0.01:
                if ctr.z > 0 and abs(ctr.x - X(sections[0][1])) < P(dark[2] + 0.9):
                    f.material_index = dark_mat
    if len(rings[-1][1]) > 1:
        bm.faces.new(rings[-1][1]).material_index = mat


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(12, metallic=0.6, roughness=0.35),  # 0 fuselage, light grey
        pal(14, metallic=0.6, roughness=0.3),  # 1 white strip down column 9, front part
        pal(8, metallic=0.55, roughness=0.4),  # 2 right pod, mid grey
        pal(6, metallic=0.5, roughness=0.45),  # 3 canards
        pal(2, metallic=0.1, roughness=0.1),  # 4 canopy glass
        pal(115, metallic=0.3, roughness=0.4, emission_strength=2.0),  # 5 red engines
        pal(10, metallic=0.6, roughness=0.35),  # 6 front engine bands
        pal(2, metallic=0.4, roughness=0.6),  # 7 dark tail block between the pipes, pods' outer flanks
        pal(8, metallic=0.6, roughness=0.35),  # 8 exhaust pipes
        pal(4, metallic=0.5, roughness=0.45),  # 9 the fuselage's shadowed right flank
        pal(7, metallic=0.55, roughness=0.4),  # 10 the darker nose tip and fuselage underside
        pal(15, metallic=0.6, roughness=0.3),  # 11 white strip, its brightest rear part
        pal(9, metallic=0.55, roughness=0.4),  # 12 fuselage's left flank, the left pod's inner slope
        pal(11, metallic=0.2, roughness=0.15),  # 13 the glint in the canopy
        pal(6, metallic=0.55, roughness=0.4),  # 14 the right pod's shadowed inner slope, rear engine bands
        pal(11, metallic=0.6, roughness=0.35),  # 15 the fuselage ahead of row 13
        pal(5, metallic=0.5, roughness=0.45),  # 16 the nose's shadowed right side
        pal(9, metallic=0.55, roughness=0.4),  # 17 left pod, lit, a shade lighter
        pal(10, metallic=0.55, roughness=0.4),  # 18 the left pod's lit inner slope
    ]
    HULL, STRIP, POD, FIN, GLASS, RED, BAND, DARK, PIPE, SHADE, SIDE, WHITE, MID, GLINT, POD_DK, HULL_FWD, NOSE_SHADE, POD_L, POD_L_IN = range(19)
    bm = bmesh.new()

    def hull_paint(c, r, cu, cv):
        """The sprite's shades on the fuselage's upper faces (cols in px, row of the face centre)."""
        if cv <= 0:
            return None
        if r < 9.2:  # the nose: lit left of the canopy, in shadow right of column 12
            if c >= 12.0:
                return NOSE_SHADE
            if r > 3.4 or c < 11.0:
                return SIDE if c < 9.0 else MID if c < 11.0 else None
            return None
        if r > 21.0:  # the tail end between the pipes' roots
            return MID
        if c >= 13.97:  # the dark right flank, column 14
            return SHADE
        if c < 9.03:  # the mid-grey left flank, column 8
            return MID
        if c < 10.06:  # the white strip, column 9, brightest toward the tail
            return WHITE if r > 16.5 else STRIP
        return HULL_FWD if r < 13.0 else None  # the fuselage is a shade darker ahead of row 13

    # Fuselage, nose (row 0) to the tail (row 22): a rounded ridge about 7.5 px tall at its widest
    # (+5.1/-2.7), (row, half width, half height, z) in px. The sprite's 1 px dark outline is inside it.
    hull = [(-0.1, 0, 0, 0.5), (0.7, 1.5, 1.2, 0.6), (1.6, 2.3, 2.0, 0.9), (3.4, 3.2, 2.9, 1.1),
            (5.0, 3.5, 3.4, 1.2), (5.7, 3.5, 3.5, 1.2), (8.5, 3.6, 3.7, 1.2), (9.2, 3.6, 3.8, 1.2),
            (13.0, 3.6, 3.9, 1.2), (16.5, 3.6, 3.9, 1.2), (18.0, 3.6, 3.8, 1.2), (21.0, 3.5, 3.2, 0.9),
            (22.2, 3.3, 1.8, 0.4)]
    # The canopy: a dark slot about 3 px wide sunk into the nose (rows 5-9, columns 10-12).
    ridge(bm, [(r, AXIS, w, h, z) for r, w, h, z in hull], 18, HULL, 0.85,
          dark=(5.0, 9.2, 1.0, 0.9), dark_mat=GLASS, rim=(SIDE, 0, 0.8), nose=(SIDE, 3.4), paint=hull_paint)
    # The canopy's glint: the one light pixel in it (column 11, row 6), a sliver of lit glass
    # sitting in the slot.
    floor = 1.2 + 3.5 - 0.9  # the slot's floor on the axis at row 5.7, in px
    slab(bm, [(11.0, 6.0), (12.0, 6.0), (12.0, 7.0), (11.0, 7.0)], floor - 0.2, floor + 0.35, mat=GLINT, bevel=0.15)

    # The tail (rows 21-26): a dark block sunk below three round exhaust pipes (columns 9, 11, 13).
    loft(bm, [(20.5, AXIS, 3.3, 1.6, -0.2), (26.0, AXIS, 3.2, 1.5, -0.2), (26.8, AXIS, 3.15, 1.0, -0.2)],
         sides=12, mat=DARK, power=0.6)
    for c in (9.5, 11.5, 13.5):
        loft(bm, [(19.5, c, 0.95, 0.95, 1.3), (25.8, c, 0.95, 0.95, 1.3), (26.4, c, 0.6, 0.6, 1.3)],
             sides=8, mat=PIPE)

    # Canards beside the canopy (rows 5-10, out to columns 4 and 19), dark grey.
    fin = [(9.0, 4.3), (4.2, 8.0), (4.2, 9.8), (8.8, 10.0)]
    for side in (1, -1):
        pts = fin if side == 1 else [(mirror(AXIS, c), r) for c, r in fin]
        slab(bm, pts, -0.3, 0.9, mat=FIN, bevel=0.2)

    # Side pods (rows 10-23, out to columns 2 and 21): round bodies about 4.5 px tall, lower than the
    # ridge, (row, centre col, half width, half height, z) for the left one.
    pod = [(9.9, 7.6, 0, 0, -0.2), (10.5, 7.3, 1.2, 1.1, -0.2), (12.0, 7.0, 1.7, 1.6, -0.3),
           (13.0, 6.6, 2.4, 2.0, -0.35), (14.0, 6.0, 2.8, 2.3, -0.4), (15.0, 5.6, 3.4, 2.5, -0.4),
           (20.4, 5.6, 3.4, 2.5, -0.4), (21.2, 5.9, 3.0, 2.3, -0.4), (22.2, 6.5, 2.6, 1.9, -0.4),
           (22.9, 6.7, 1.9, 1.3, -0.4)]
    # Red engines set into the pods' backs (columns 5-7, rows 18-25), tapering in toward the tail.
    engine = [(17.6, 6.5, 1.5, 2.8, -0.2), (23.8, 6.6, 1.45, 2.4, -0.3), (24.8, 7.2, 0.9, 1.6, -0.3),
              (25.8, 7.7, 0.35, 0.8, -0.3)]
    for side in (1, -1):
        m = (lambda c: c) if side == 1 else (lambda c: mirror(AXIS, c))
        # The pods' upper inner slope (next to the fuselage) is mid grey on the lit left pod and a
        # shade darker on the right one; the outer flank is the sprite's near-black edge.
        inner, base = (POD_L_IN, POD_L) if side == 1 else (POD_DK, POD)
        pod_paint = lambda c, r, cu, cv, inner=inner, side=side: inner if cv > 0 and side * cu > 0.3 else None  # noqa: E731
        ridge(bm, [(r, m(c), w, h, z) for r, c, w, h, z in pod], 12, base, 0.85, rim=(DARK, -side, 0.55),
              paint=pod_paint)
        loft(bm, [(r, m(c), w, h, z) for r, c, w, h, z in engine], sides=10, mat=RED, power=0.6)
        # Grey bands between the red stripes (rows 19 and 21).
        for r, band in ((19.0, BAND), (21.0, POD_DK)):  # light grey, then mid-dark grey
            loft(bm, [(r, m(6.5), 1.65, 2.95, -0.2), (r + 1.0, m(6.5), 1.65, 2.9, -0.25)],
                 sides=10, mat=band, power=0.6)

    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


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
