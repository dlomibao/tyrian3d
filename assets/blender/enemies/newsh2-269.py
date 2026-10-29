"""Grey fork ship (newsh2.shp frame 269): a 3D version of its sprite.

Seen in episode 1 (levels 1.28, 1.30, 1.36) and 3.17. It flies nose right. Traced from its concept
(features/concepts/newsh2-269.jpg): a riveted grey egg of a fuselage with a darker cone nose, a
bronze armour band round its rear, a chamfered engine bay in its back holding two glowing red
grilles and pipework, a copper plate on the centre seam, a big grey tail drum with red exhausts
on a thin upright spar, and two fork arms (a brown housing and swept strut, a round hub, a
straight grey rail with a chamfered tip) reaching forward above and below. The sprite is mirror
symmetric about row 13. One frame. Textured from the concept by texture_bake.py.

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


# Fuselage profile along +X, back (column 3.9) to nose (column 23.75): (column, half width px). The
# widths follow the sprite's outline ring (rows 6-20 at columns 7-13, then the taper to the blunt
# point at column 23), the egg the concept draws; a shallow groove at column 20.85 parts the nose cone.
HULL = [(3.9, 0.0), (4.0, 3.0), (4.3, 4.3), (5.0, 5.4), (6.0, 6.4), (7.0, 7.1), (8.5, 7.35),
        (13.5, 7.35), (15.0, 7.0), (16.0, 6.4), (17.0, 5.75), (18.5, 5.1), (19.5, 4.6), (20.6, 3.9),
        (20.85, 3.55), (21.1, 3.6), (21.6, 3.2), (22.5, 2.3), (23.2, 1.45), (23.6, 0.6), (23.75, 0.0)]
ROUND = 0.78  # half height / half width: the sprite and the concept shade the fuselage round
NOSE_C = 20.85  # the nose cone's seam


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


def octagon(c0, c1, r0, r1, ch):
    """A rectangle from columns c0-c1 and rows r0-r1 (sprite px) with its corners cut by ch px,
    as (x, y) units, counter-clockwise."""
    pts = [(c0 + ch, r1), (c1 - ch, r1), (c1, r1 - ch), (c1, r0 + ch), (c1 - ch, r0), (c0 + ch, r0),
           (c0, r0 + ch), (c0, r1 - ch)]
    return [(X(c), Y(r)) for c, r in pts]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(9, metallic=0.35, roughness=0.5),  # 0 grey hull plating
        pal(11, metallic=0.3, roughness=0.55),  # 1 light grey: tail drum flanges, rail collar
        pal(4, metallic=0.4, roughness=0.55),  # 2 dark grey: spar, bay walls, machinery
        pal(26, metallic=0.45, roughness=0.45),  # 3 bronze armour band
        pal(167, metallic=0.4, roughness=0.5),  # 4 dark brown rim on the band's front edge
        pal(24, metallic=0.4, roughness=0.5),  # 5 brown arm struts and their housings
        pal(7, metallic=0.25, roughness=0.6),  # 6 rails, hubs and the nose cone
        pal(119, emission_strength=3.5),  # 7 red lamps
        pal(25, metallic=0.6, roughness=0.35),  # 8 copper plate on the centre seam
        pal(3, metallic=0.2, roughness=0.7),  # 9 near-black bay floor
        pal(121, emission_strength=4.0),  # 10 orange lamp cores
        pal(5, metallic=0.5, roughness=0.45),  # 11 grey lamp frame and pipes
        pal(10, metallic=0.4, roughness=0.45),  # 12 tail drum body
    ]
    HULLM, LIGHT, DARK, BRONZE, RIM, STRUT, RAIL, RED, COPPER, BLACK, ORANGE, MID, DRUM = range(13)
    yc = Y(AXIS)

    # ---- the fuselage (an egg with a cone nose), with the engine bay cut into its back ----
    hbm = bmesh.new()
    lib.sweep(hbm, [(X(c), yc, 0.0, w * PX, ROUND * w * PX) for c, w in HULL], sides=20, mat=HULLM)
    hbm.faces.ensure_lookup_table()
    for f in hbm.faces:
        if f.calc_center_median().x > X(NOSE_C):
            f.material_index = RAIL
    body = lib.to_object(NAME + "-hull", hbm, mats, coll)

    # Engine bay (concept: columns 5.4-12.2, rows 10.5-15.5, corners chamfered): cut about 3 px
    # into the back, walls dark, floor near-black.
    floor_z = 0.2
    outline = octagon(5.4, 12.2, 10.6, 15.4, 0.8)
    cbm = bmesh.new()
    top = [cbm.verts.new((x, y, 1.0)) for x, y in outline]
    bot = [cbm.verts.new((x, y, floor_z)) for x, y in outline]
    n = len(outline)
    for k in range(n):
        j = (k + 1) % n
        cbm.faces.new((bot[k], bot[j], top[j], top[k])).material_index = DARK
    cbm.faces.new(list(reversed(bot))).material_index = BLACK
    cbm.faces.new(top).material_index = BLACK
    bmesh.ops.recalc_face_normals(cbm, faces=cbm.faces)
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

    # In the bay: a grey frame holding two glowing red grilles (concept columns 6-7.2 and 7.8-9,
    # rows 11.6-14.4; the sprite's lamps at columns 6 and 8), each with an orange core, and behind
    # them (columns 9.4-11.9) a machinery block with two pipes running along the ship.
    lib.box(bm, X(5.8), Y(14.75), X(9.3), Y(11.25), floor_z, floor_z + 0.9 * PX, mat=MID)
    for c in (6.45, 8.35):
        lib.box(bm, X(c) - 0.6 * PX, Y(14.4), X(c) + 0.6 * PX, Y(11.6), floor_z, floor_z + 1.9 * PX, mat=RED)
        lib.box(bm, X(c) - 0.35 * PX, Y(13.6), X(c) + 0.35 * PX, Y(12.4), floor_z + 1.9 * PX,
                floor_z + 2.05 * PX, mat=ORANGE)
    lib.box(bm, X(9.6), Y(14.6), X(11.8), Y(11.4), floor_z, floor_z + 0.8 * PX, mat=DARK)
    for r in (12.2, 13.8):
        lib.sweep(bm, [(X(9.5), Y(r), floor_z + 1.2 * PX, 0.45 * PX, 0.45 * PX),
                       (X(11.9), Y(r), floor_z + 1.2 * PX, 0.45 * PX, 0.45 * PX)], sides=8, mat=MID)

    # The copper plate on the hull's centre seam (row 13, columns 12.3-14.8), just in front of the bay.
    shell(bm, 12.3, 14.8, -0.5, 0.5, 0.35, lambda c, d: COPPER, nc=2, nd=1, sink=0.3)

    # ---- the half above the axis (mirrored below) ----
    first = len(bm.verts)
    # Bronze armour band wrapped round the fuselage's rear (concept columns 4.5-9.6, from the bay's
    # edge down the flank), with a dark brown rim along its front edge (sprite column 8).
    def band_mat(c, d):
        return RIM if c > 8.6 else BRONZE
    shell(bm, 4.3, 9.6, 0.36, 0.999, 0.5, band_mat, nc=7, nd=6, sink=0.3, rel=True)

    # The fork arm. A brown housing on the spar's top (sprite rows 5-6, columns 0-3), a hard brown
    # strut swept up from it to the hub (columns 4-6, rows 3-4), a round hub with a bolt cap at
    # column 6.6, and the straight grey rail along row 3 to column 15.6 with a chamfered tip.
    lib.bevel_prism(bm, [(X(-0.4), Y(6.6)), (X(3.2), Y(6.6)), (X(3.2), Y(4.5)), (X(-0.4), Y(4.5))],
                    -1.2 * PX, 1.2 * PX, 0.3 * PX, mat=STRUT)
    lib.sweep(bm, [(X(2.4), Y(5.4), 0.0, 1.15 * PX, 0.95 * PX), (X(3.7), Y(4.6), 0.0, 1.15 * PX, 0.95 * PX),
                   (X(4.7), Y(3.7), 0.0, 1.15 * PX, 0.95 * PX), (X(6.2), Y(3.0), 0.0, 1.15 * PX, 0.95 * PX)],
              sides=6, mat=STRUT, smooth=False)
    hub = [(X(6.6) + 1.4 * PX * math.cos(a), Y(3.0) + 1.4 * PX * math.sin(a))
           for a in (2 * math.pi * k / 10 for k in range(10))]
    lib.bevel_prism(bm, hub, -1.1 * PX, 1.3 * PX, 0.3 * PX, mat=RAIL)
    lib.prism(bm, [(X(6.6) + 0.55 * PX * math.cos(a), Y(3.0) + 0.55 * PX * math.sin(a))
                   for a in (2 * math.pi * k / 6 for k in range(6))], 1.2 * PX, 1.6 * PX, mat=DARK)
    lib.sweep(bm, [(X(7.4), Y(3.0), 0.0, 1.2 * PX, 0.95 * PX), (X(12.6), Y(3.0), 0.0, 1.2 * PX, 0.95 * PX),
                   (X(12.8), Y(3.0), 0.0, 0.95 * PX, 0.75 * PX), (X(13.1), Y(3.0), 0.0, 0.95 * PX, 0.75 * PX),
                   (X(13.3), Y(3.0), 0.0, 1.25 * PX, 1.0 * PX), (X(14.9), Y(3.0), 0.0, 1.25 * PX, 1.0 * PX),
                   (X(15.6), Y(3.0), 0.0, 0.45 * PX, 0.4 * PX)], sides=8, mat=RAIL, smooth=False)
    lib.sweep(bm, [(X(7.7), Y(3.0), 0.0, 1.35 * PX, 1.1 * PX), (X(8.6), Y(3.0), 0.0, 1.35 * PX, 1.1 * PX)],
              sides=8, mat=LIGHT, smooth=False)
    lib.mirror(bm, first, axis="y", about=yc)

    # Upright spar at the back (columns 1-3, rows 5-21): a hard dark bar through the tail drum.
    lib.bevel_prism(bm, [(X(1.1), Y(20.6)), (X(2.9), Y(20.6)), (X(2.9), Y(5.4)), (X(1.1), Y(5.4))],
                    -1.0 * PX, 1.0 * PX, 0.25 * PX, mat=DARK)

    # The tail drum (concept: a big grey cylinder, columns 0-4.5, rows 9.8-16.2), its axis along the
    # ship, as tall as it is wide, with a flange at each end and three red exhaust lamps on its back.
    r, dy = 3.05 * PX, yc
    lib.sweep(bm, [(X(-0.2), dy, 0.0, r - 0.5 * PX, r - 0.5 * PX), (X(0.0), dy, 0.0, r + 0.15 * PX, r + 0.15 * PX),
                   (X(0.7), dy, 0.0, r + 0.15 * PX, r + 0.15 * PX), (X(0.8), dy, 0.0, r, r),
                   (X(3.6), dy, 0.0, r, r), (X(3.7), dy, 0.0, r + 0.15 * PX, r + 0.15 * PX),
                   (X(4.4), dy, 0.0, r + 0.15 * PX, r + 0.15 * PX), (X(4.6), dy, 0.0, r - 0.6 * PX, r - 0.6 * PX)],
              sides=16, mat=DRUM)
    bm.faces.ensure_lookup_table()
    for row in (11.2, 13.0, 14.8):
        lib.box(bm, X(-0.45), Y(row + 0.55), X(-0.15), Y(row - 0.55), -0.55 * PX, 0.55 * PX, mat=RED)

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
