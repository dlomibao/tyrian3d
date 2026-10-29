"""Grey fork ship (newsh2.shp frame 269): a 3D version of its sprite.

Seen in episode 1 (levels 1.28, 1.30, 1.36) and 3.17. It flies nose right: a fat grey bullet of
a fuselage with cream cowls and two red lights at its back, a shiny tail cylinder through a thin
upright spar, and two thin rails reaching forward above and below it on swept brown struts. The
sprite is mirror symmetric about row 13. One frame.

Run: blender --background --python assets/blender/enemies/newsh2-269.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import math

import bmesh
import bpy
from mathutils import Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b053 as lib  # noqa: E402
from lib_b053 import PX, X, Y  # noqa: E402

NAME = "newsh2-269"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = 13.0  # the sprite's mirror row


# Fuselage profile along +X, back (column 3.7) to nose (column 23.6): (column, half width px). The
# widths follow the sprite's outline (rows 7-19 from column 6 to 16, then the taper to the point).
HULL = [(3.7, 0.0), (4.0, 3.0), (4.5, 4.6), (5.2, 5.6), (6.2, 6.3), (8.0, 6.45), (12.0, 6.45),
        (16.3, 6.3), (17.5, 5.6), (18.6, 5.0), (19.6, 4.4), (20.6, 3.7), (21.6, 2.9), (22.5, 1.9),
        (23.2, 1.0), (23.6, 0.0)]
ROUND = 0.8  # half height / half width: the sprite shades the fuselage round, so it is nearly as tall


def hull_w(c):
    """The fuselage's half width in px at column c."""
    for (c0, w0), (c1, w1) in zip(HULL, HULL[1:]):
        if c0 <= c <= c1:
            return w0 + (w1 - w0) * (c - c0) / (c1 - c0)
    return 0.0


def shell(bm, c0, c1, d0, d1, grow, mat_for, nc=6, nd=6, sink=0.3, rel=False):
    """A plate wrapped over the fuselage between columns c0-c1 and px offsets d0-d1 from the axis
    (positive = above it in the sprite, i.e. +Y), standing `grow` px proud of the hull and sunk
    `sink` px into it, with closed edges. mat_for(c, d) picks each face's material (d in px). With
    rel, d0-d1 are fractions of the local half width instead, so the plate wraps to the flank."""
    yc = Y(AXIS)
    first = len(bm.faces)

    def point(c, d, extra):
        w = max(hull_w(c), 1e-3)
        if rel:
            d = d * w
        u = max(-0.999, min(0.999, d / w))
        z = ROUND * w * math.sqrt(1 - u * u)
        n = Vector((0.0, u, math.sqrt(1 - u * u) / ROUND)).normalized()
        base = Vector((X(c), yc + d * PX, z * PX))
        return base + n * (extra * PX)

    cs = [c0 + (c1 - c0) * i / nc for i in range(nc + 1)]
    ds = [d0 + (d1 - d0) * j / nd for j in range(nd + 1)]
    outer = [[bm.verts.new(point(c, d, grow)) for d in ds] for c in cs]
    inner = [[bm.verts.new(point(c, d, -sink)) for d in ds] for c in cs]
    faces = []
    for i in range(nc):
        for j in range(nd):
            f = bm.faces.new((outer[i][j], outer[i + 1][j], outer[i + 1][j + 1], outer[i][j + 1]))
            cm, dm = (cs[i] + cs[i + 1]) / 2, (ds[j] + ds[j + 1]) / 2
            f.material_index = mat_for(cm, dm * hull_w(cm) if rel else dm)
            faces.append(f)
            g = bm.faces.new((inner[i][j + 1], inner[i + 1][j + 1], inner[i + 1][j], inner[i][j]))
            g.material_index = f.material_index
    edge = ([(0, j) for j in range(nd + 1)] + [(i, nd) for i in range(1, nc + 1)]
            + [(nc, j) for j in range(nd - 1, -1, -1)] + [(i, 0) for i in range(nc - 1, 0, -1)])
    for (i0, j0), (i1, j1) in zip(edge, edge[1:] + edge[:1]):
        f = bm.faces.new((outer[i0][j0], inner[i0][j0], inner[i1][j1], outer[i1][j1]))
        cm, dm = cs[min(i0, nc - 1)], ds[min(j0, nd - 1)]
        f.material_index = mat_for(cm, dm * hull_w(cm) if rel else dm)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first:]:
        f.smooth = True


def append_mesh(bm, obj):
    """Copy an object's mesh (faces, material indices, smooth flags) into bm, then delete it."""
    mesh = obj.data
    verts = [bm.verts.new(v.co) for v in mesh.vertices]
    for p in mesh.polygons:
        f = bm.faces.new([verts[i] for i in p.vertices])
        f.material_index = p.material_index
        f.smooth = p.use_smooth
    bpy.data.objects.remove(obj)
    bpy.data.meshes.remove(mesh)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(9, metallic=0.55, roughness=0.35),  # 0 grey hull
        pal(11, metallic=0.6, roughness=0.25),  # 1 light grey: lit seam, collar, tail drum
        pal(4, metallic=0.4, roughness=0.5),  # 2 dark grey: spar, bay walls, machinery
        pal(29, metallic=0.3, roughness=0.4),  # 3 cream cowls
        pal(165, metallic=0.2, roughness=0.6),  # 4 dark brown cowl rims
        pal(23, metallic=0.3, roughness=0.5),  # 5 brown struts
        pal(7, metallic=0.6, roughness=0.3),  # 6 rails
        pal(119, emission_strength=3.5),  # 7 red lamps
        pal(31, emission_strength=2.0),  # 8 pale plate on the back
        pal(3, metallic=0.2, roughness=0.7),  # 9 near-black bay floor and seams
        pal(121, emission_strength=4.0),  # 10 orange lamp cores
        pal(5, metallic=0.5, roughness=0.4),  # 11 grey divider between the lamps
    ]
    HULLM, LIGHT, DARK, CREAM, BROWN, STRUT, RAIL, RED, PALE, BLACK, ORANGE, MID = range(12)
    yc = Y(AXIS)

    # ---- the fuselage, with the engine bay cut into its back ----
    hbm = bmesh.new()
    lib.sweep(hbm, [(X(c), yc, 0.0, w * PX, ROUND * w * PX) for c, w in HULL], sides=20, mat=HULLM)
    body = lib.to_object(NAME + "-hull", hbm, mats, coll)

    # Engine bay (rows 11-14, columns 6-11): a box cut about 2.8 px into the back, walls dark.
    bx0, bx1, by0, by1, floor_z = X(5.5), X(11.5), Y(14.5), Y(10.5), 0.17
    cbm = bmesh.new()
    outline = [(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)]
    top = [cbm.verts.new((x, y, 1.0)) for x, y in outline]
    bot = [cbm.verts.new((x, y, floor_z)) for x, y in outline]
    for k in range(4):
        j = (k + 1) % 4
        cbm.faces.new((bot[k], bot[j], top[j], top[k])).material_index = DARK
    cbm.faces.new(list(reversed(bot))).material_index = BLACK
    cbm.faces.new(top).material_index = BLACK
    cutter = common.mesh_object(NAME + "-cutter", cbm, mats, coll)
    mod = body.modifiers.new("bay", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.material_mode = "INDEX"
    with bpy.context.temp_override(object=body, active_object=body):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)
    for p in body.data.polygons:
        if p.material_index in (DARK, BLACK):
            p.use_smooth = False
    bm = bmesh.new()
    append_mesh(bm, body)

    # Two red lamps in the bay (columns 6 and 8, rows 12-14), upright bars with an orange core on
    # row 13, a grey divider between them (column 7) and low machinery behind (columns 9-11).
    for c in (6.0, 8.0):
        lib.box(bm, X(c) - 0.45 * PX, Y(14.4), X(c) + 0.45 * PX, Y(11.6), floor_z, 0.355, mat=RED)
        lib.box(bm, X(c) - 0.3 * PX, Y(13.4), X(c) + 0.3 * PX, Y(12.6), 0.355, 0.37, mat=ORANGE)
    lib.box(bm, X(7.0) - 0.4 * PX, Y(14.3), X(7.0) + 0.4 * PX, Y(11.7), floor_z, 0.30, mat=MID)
    lib.box(bm, X(8.8), Y(14.3), X(11.3), Y(11.8), floor_z, 0.24, mat=DARK)
    lib.sweep(bm, [(X(9.0), Y(12.9), 0.27, 0.45 * PX, 0.45 * PX), (X(11.3), Y(12.9), 0.27, 0.45 * PX, 0.45 * PX)],
              sides=8, mat=MID)

    # A lit panel edge across the back at column 12 (rows 11-15), the pale plate on row 13
    # (columns 12-14) and the dark seam on row 14 (columns 13-16).
    shell(bm, 11.75, 12.3, -2.6, 2.6, 0.3, lambda c, d: LIGHT, nc=1, nd=6, sink=0.3)
    shell(bm, 12.4, 14.6, -0.5, 0.5, 0.35, lambda c, d: PALE, nc=2, nd=1, sink=0.3)
    shell(bm, 13.0, 16.5, -1.5, -0.6, 0.1, lambda c, d: BLACK, nc=2, nd=1, sink=0.3)

    # ---- the half above the axis (mirrored below) ----
    first = len(bm.verts)
    # Armour cowl wrapped round the fuselage's rear shoulder (rows 7-10, columns 5-9) down to its
    # flank: a cream plate (rows 9-10, columns 5-7) framed by a dark brown rim along its front
    # (columns 8-9) and outer edge (rows 7-8).
    def cowl_mat(c, d):
        return CREAM if c < 7.5 and d < 4.6 else BROWN
    shell(bm, 4.8, 9.6, 0.4, 0.999, 0.5, cowl_mat, nc=6, nd=6, sink=0.3, rel=True)

    # Swept brown strut from the rail's back end down to the spar's top (rows 3-6): a hard bar.
    lib.sweep(bm, [(X(6.2), Y(3.0), 0.0, 0.0, 0.0), (X(5.6), Y(3.3), 0.0, 1.2 * PX, 1.0 * PX),
                   (X(3.6), Y(4.9), 0.0, 1.25 * PX, 1.0 * PX), (X(1.0), Y(5.8), 0.0, 1.25 * PX, 1.0 * PX),
                   (X(-0.4), Y(6.0), 0.0, 0.0, 0.0)], sides=6, mat=STRUT, smooth=False)
    # Rail reaching forward (row 3, columns 5-15) with a chamfered tip and a bright collar at
    # column 8.
    lib.sweep(bm, [(X(5.2), Y(3.0), 0.0, 1.0 * PX, 0.9 * PX), (X(14.6), Y(3.0), 0.0, 1.0 * PX, 0.9 * PX),
                   (X(15.4), Y(3.0), 0.0, 0.4 * PX, 0.4 * PX)], sides=8, mat=RAIL, smooth=False)
    lib.sweep(bm, [(X(7.6), Y(3.0), 0.0, 1.25 * PX, 1.15 * PX), (X(8.5), Y(3.0), 0.0, 1.25 * PX, 1.15 * PX)],
              sides=8, mat=LIGHT, smooth=False)
    lib.mirror(bm, first, axis="y", about=yc)

    # Upright spar at the back (column 2, rows 6-20) and the shiny tail drum through it (columns
    # 0-4, rows 10-14): a cylinder with chamfered ends, as tall as it is wide.
    lib.sweep(bm, [(X(2.0), Y(5.6), 0.0, 0.9 * PX, 0.9 * PX), (X(2.0), Y(20.4), 0.0, 0.9 * PX, 0.9 * PX)],
              sides=8, mat=DARK, smooth=False)
    r, dy = 2.6 * PX, Y(12.6)
    lib.sweep(bm, [(X(-0.45), dy, 0.0, 0.0, 0.0), (X(-0.45), dy, 0.0, r - 0.6 * PX, r - 0.6 * PX),
                   (X(-0.05), dy, 0.0, r, r), (X(4.2), dy, 0.0, r, r),
                   (X(4.6), dy, 0.0, r - 0.5 * PX, r - 0.5 * PX)], sides=16, mat=LIGHT)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
