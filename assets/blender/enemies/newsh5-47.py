"""Purple belted pod (newsh5.shp frame 47): a 3D version of its sprite.

Seen in episode 4 (levels 4 and 12). A purple ball as tall as it is wide, lighter above its middle
and darker below, girdled by a maroon belt (rows 11-16) with a gold strap down its front and a dark
opening cut in below the belt. One frame.

Run: blender --background --python assets/blender/enemies/newsh5-47.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b004 as lib  # noqa: E402

NAME = "newsh5-47"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def E(r):
    """Pixel edge row to Blender Y."""
    return (14 - r) / 12


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(88, metallic=0.15, roughness=0.4),  # 0 light purple upper shell
        pal(86, metallic=0.15, roughness=0.45),  # 1 darker purple lower shell
        pal(243, metallic=0.15, roughness=0.6),  # 2 maroon belt
        pal(250, metallic=0.8, roughness=0.25),  # 3 gold strap
        pal(94, metallic=0.6, roughness=0.2),  # 4 pale strap top
        pal(241, metallic=0.2, roughness=0.6),  # 5 dark lip under the belt (row 17)
        pal(81, metallic=0.0, roughness=0.8),  # 6 dark opening below the belt
        pal(245, metallic=0.25, roughness=0.4),  # 7 bright crimson top row of the belt (row 11)
        pal(244, metallic=0.25, roughness=0.4),  # 8 crimson bottom row of the belt (row 16)
        pal(242, metallic=0.2, roughness=0.5),  # 9 shaded lower belt row (row 15)
        pal(83, metallic=0.15, roughness=0.6),  # 10 shadowed purple lip over the belt (row 10)
    ]
    UPPER, LOWER, BELT, GOLD, PALE, EDGE, PANEL, BELT_HI, BELT_LO, BELT_SH, LIP = range(11)
    bm = bmesh.new()

    # Shell: a ball as tall as it is wide. Columns 0-23 and rows 0-26 with the dark rim, so the
    # outline covers the sprite's; about 23 px from bottom to top, centred on the midplane.
    shell = lib.Ellipsoid(0.0, E(13.5), 12.2 / 12, 13.5 / 12, 11.5 / 12)
    shell.build(bm, segments=32, rings=22, mat_index=UPPER)
    belt_top, belt_bottom = E(11.0), E(17.0)
    for f in bm.faces:
        if f.calc_center_median().y < (belt_top + belt_bottom) / 2:
            f.material_index = LOWER
    body = common.mesh_object(NAME, bm, mats, coll, smooth=True)

    # The dark opening under the belt (rows 18-23, columns 5-16), cut about 3.5 px into the ball
    # with a floor that follows its curve; the lighter shell is left round it as a lip. Its outline
    # is straight-ish along the belt and rounds off below, as in the sprite.
    ocx, ocy, orx, ry_up, ry_down, depth = -0.5 / 12, E(18.6), 6.4 / 12, 0.5 / 12, 4.9 / 12, 3.5 / 12
    def outline(k, scale, sides=24):
        ang = 2 * math.pi * (k + 0.5) / sides
        sy = math.sin(ang)
        return ocx + orx * scale * math.cos(ang), ocy + (ry_up if sy > 0 else ry_down) * scale * sy
    bm = bmesh.new()
    rings = []
    for scale, z in ((1.0, None), (1.0, -0.02), (0.82, -depth), (0.45, -depth)):
        ring = []
        for k in range(24):
            x, y = outline(k, scale)
            ring.append(bm.verts.new((x, y, 2.0 if z is None else shell.top(x, y) + z)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(24):
            j = (k + 1) % 24
            bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = PANEL
    centre = bm.verts.new((ocx, ocy - 1.5 / 12, shell.top(ocx, ocy - 1.5 / 12) - depth))
    for k in range(24):
        j = (k + 1) % 24
        bm.faces.new((rings[-1][k], rings[-1][j], centre)).material_index = PANEL
    bm.faces.new(list(reversed(rings[0]))).material_index = PANEL
    cutter = common.mesh_object(NAME + "-cutter", bm, mats, coll)
    mod = body.modifiers.new("opening", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.material_mode = "INDEX"
    with bpy.context.temp_override(object=body, active_object=body):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    # A crisp edge round the opening: its faces don't share normals with the shell.
    rim = [e for e in bm.edges if len(e.link_faces) == 2
           and (e.link_faces[0].material_index == PANEL) != (e.link_faces[1].material_index == PANEL)]
    bmesh.ops.split_edges(bm, edges=rim)

    # Belt: a thin strap round the ball's equator (rows 11-16), about 0.7 px proud and following
    # its curve, with bright crimson edge rows, a shadowed purple lip above (row 10) and a dark
    # lip below (row 17) sloping back down to the shell.
    G = 0.06
    def ring(y, grow):
        u = (y - shell.y0) / shell.b
        k = math.sqrt(max(0.0, 1 - u * u))
        return (y, shell.a * k + grow, shell.c * k + grow, 0.0)
    bands = [  # (from row, to row, grow at the top edge, grow at the bottom edge, material)
        (18.0, 17.0, 0.0, G, EDGE),
        (17.0, 16.0, G, G, BELT_LO),
        (16.0, 15.0, G, G, BELT_SH),
        (15.0, 12.0, G, G, BELT),
        (12.0, 11.0, G, G, BELT_HI),
        (11.0, 10.0, G, 0.0, LIP),
    ]
    for r0, r1, g0, g1, mat in bands:
        common.loft(bm, [ring(E(r0), g0), ring(E(r1), g1)], sides=32, mat_index=mat,
                    cap_start=False, cap_end=False)

    # Gold strap down the front of the belt (columns 11-12, rows 12-16) with its pale top
    # (row 11): a straight bar about 0.8 px proud of the belt.
    belt = lib.Ellipsoid(0.0, shell.y0, shell.a + G, shell.b, shell.c + G)
    def bar(x0, x1, rows, proud, mat):
        rings = []
        for r in rows:
            y = E(r)
            zt = belt.top(0.0, y) + proud
            zb = belt.top(x1, y) - 0.04
            rings.append([bm.verts.new(p) for p in
                          ((x0, y, zb), (x0, y, zt), (x1, y, zt), (x1, y, zb))])
        for q0, q1 in zip(rings, rings[1:]):
            for i in range(3):
                bm.faces.new((q0[i], q0[i + 1], q1[i + 1], q1[i])).material_index = mat
        bm.faces.new(list(reversed(rings[0]))).material_index = mat
        bm.faces.new(rings[-1]).material_index = mat
    bar(-1.0 / 12, 1.0 / 12, (17.0, 15.0, 13.5, 12.0), 0.07, GOLD)
    bar(-1.0 / 12, 1.0 / 12, (12.0, 11.0), 0.075, PALE)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(body.data)
    bm.free()
    for poly in body.data.polygons:
        poly.use_smooth = True
    return body


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], sprite, ROOT, NAME)


if __name__ == "__main__":
    main()
