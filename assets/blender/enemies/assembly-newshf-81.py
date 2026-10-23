"""Twin cannon bunker (newshf.shp, assembly of newshf-43, newshf-81, newshf-119): a 3D version of
its sprites.

Seen in episodes 1, 3 and 4 (levels 1.10, 1.29, 3.21, 4.16). Six 2x2 ground enemies make one
48 x 66 px structure: two identical columns side by side (sprite.json `assemblyLayout`), each
three pieces tall:

- newshf-43: a grey roof braced with diagonal ridges, two blue canisters with glowing lights
  either side of a bevelled grey box, and a blue panel in front of it.
- newshf-81: a dark pit between low grey walls with blue posts and blocks on them; in the pit a
  blue pipe rig with two glowing lights holds the breech of a grey cannon pointing down the
  screen, and grey deck plates either side of the barrel in front.
- newshf-119: the dark ribbed front face of the deck with the cannon's muzzle; its second frame
  (121) is the muzzle flash, a change of shape, so it gets its own model (newshf-119-f2).

One column is built whole in assembly coordinates (newshf-81's centre is the origin) and cut
into its three pieces with common.split_assembly; the second column uses the same models.
Ground object: base at z = 0.

Run: blender --background --python assets/blender/enemies/assembly-newshf-81.py [-- --preview out.png]
(the preview is the whole bunker; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b101 as lib  # noqa: E402

NAME = "assembly-newshf-81"
ROOT = common.repo_root(__file__)
PIECES = ["newshf-43", "newshf-81", "newshf-119"]
# Piece centres relative to newshf-81 (screen cx 80, cy 10) in the left column.
LAYOUT = [("newshf-43", 0, -28), ("newshf-81", 0, 0), ("newshf-119", 0, 28)]


def X(c):
    """Column edge (0 = left edge of the column) to Blender X."""
    return (c - 12) / 12


def Y(r):
    """Assembly row edge (0 = top of newshf-43, 28 = top of newshf-81, 56 = top of newshf-119)."""
    return (42 - r) / 12


def P(points):
    return [(X(c), Y(r)) for c, r in points]


def rect(c0, r0, c1, r1):
    return P([(c0, r0), (c1, r0), (c1, r1), (c0, r1)])


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshf81"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(2, metallic=0.0, roughness=1.0),  # 0 dark pit floor and front face
        pal(3, metallic=0.5, roughness=0.5),  # 1 dark grey ribs
        pal(4, metallic=0.55, roughness=0.45),  # 2 dark grey
        pal(5, metallic=0.55, roughness=0.45),  # 3 grey walls
        pal(6, metallic=0.6, roughness=0.4),  # 4 grey seams
        pal(7, metallic=0.6, roughness=0.4),  # 5 grey roof
        pal(8, metallic=0.6, roughness=0.35),  # 6 light grey plates
        pal(10, metallic=0.65, roughness=0.3),  # 7 bright grey ridges
        pal(56, metallic=0.5, roughness=0.35),  # 8 blue
        pal(54, metallic=0.5, roughness=0.4),  # 9 dark blue
        pal(130, metallic=0.5, roughness=0.3),  # 10 light blue
        pal(133, metallic=0.5, roughness=0.3),  # 11 pale blue bands
        pal(100, metallic=0.4, roughness=0.5),  # 12 deep blue
        pal(157, emission_strength=4.0),  # 13 blue lights
        pal(158, emission_strength=4.0),  # 14 pale blue lights
        pal(9, metallic=0.65, roughness=0.3),  # 15 mid grey
    ]
    (DARK, RIB, GREY4, WALL, SEAM, ROOF, PLATE, RIDGE, BLUE, DBLUE, LBLUE, PBLUE, DEEP, LIGHT, LIGHT2,
     GREY9) = range(16)
    bm = bmesh.new()
    flat_faces = []  # (start, end) face ranges built flat; everything else is set smooth below

    def flat(fn):
        f0 = len(bm.faces)
        fn()
        flat_faces.append((f0, len(bm.faces)))

    # Base plate under the whole column: the pit floor and everything else sits on it.
    flat(lambda: lib.prism(bm, rect(0, 0, 24, 66.5), 0.0, 0.04, mat=DARK))

    # ---- newshf-43: roof, canisters, box, panel (rows 0-28) ----

    # Roof block across the top (rows 0-9), its front edge bevelled down.
    flat(lambda: lib.bevel_block(bm, rect(0, 0, 24, 9.5), 0.04, 0.44, 1.2 / 12, bevel_h=0.06, mat=SEAM,
                                 top_mat=ROOF, edges=[False, False, True, False]))
    # Lighter plates on the outer parts of the roof (the index-8 areas) and the diagonal braces
    # that meet in the middle, with the light edges on the right-hand braces.
    flat(lambda: lib.prism(bm, P([(0, 0.6), (3, 0.6), (6.5, 4.5), (0, 4.5)]), 0.44, 0.452, mat=PLATE))
    flat(lambda: lib.prism(bm, P([(0, 6), (5, 6), (4, 7.5), (2.8, 9.4), (0, 9.4)]), 0.44, 0.452, mat=PLATE))
    flat(lambda: lib.prism(bm, P([(21.5, 1.0), (23, 1.0), (23, 9.4), (19.8, 9.4), (19, 6), (19.8, 4.5)]),
                           0.44, 0.452, mat=PLATE))

    def brace(c0, r0, c1, r1, mat, w=0.55):
        dx, dy = X(c1) - X(c0), Y(r1) - Y(r0)
        length = math.hypot(dx, dy)
        nx, ny = -dy / length * w / 12, dx / length * w / 12
        a, b = (X(c0), Y(r0)), (X(c1), Y(r1))
        flat(lambda: lib.prism(bm, [(a[0] - nx, a[1] - ny), (b[0] - nx, b[1] - ny), (b[0] + nx, b[1] + ny),
                                    (a[0] + nx, a[1] + ny)], 0.43, 0.47, mat=mat))

    brace(3.5, 0.2, 7.5, 4.5, SEAM)
    brace(7.5, 4.5, 3.5, 9.3, SEAM)
    brace(7.5, 4.5, 11.0, 9.0, SEAM)
    brace(21.5, 0.2, 17.6, 4.8, RIDGE)
    brace(17.6, 4.8, 15.4, 9.0, RIDGE)
    brace(17.6, 4.8, 20.0, 7.0, SEAM)
    brace(7.0, 5.0, 7.0, 7.0, GREY9, w=0.45)
    flat(lambda: lib.prism(bm, rect(12.1, 0.2, 12.9, 9.3), 0.43, 0.465, mat=SEAM))
    flat(lambda: lib.prism(bm, rect(12.9, 0.2, 13.9, 9.3), 0.43, 0.47, mat=PLATE))

    # Blue canisters either side (columns 3-6 and 19-22, rows 7-17), lying along Y, with a light.
    for c in (5.0, 21.0):
        lib.cylinder_y(bm, X(c), Y(17.3), Y(6.8), 0.3, 2.3 / 12, 0.18, sides=12, mat=BLUE, cap_mat=LBLUE)
        lib.cylinder_y(bm, X(c), Y(16.2), Y(15.3), 0.3, 2.45 / 12, 0.19, sides=12, mat=DBLUE)
    lib.ellipsoid(bm, (X(3.2), Y(12.5), 0.4), (0.7 / 12, 0.7 / 12, 0.05), sides=8, rings=4, mat=LIGHT2)
    lib.ellipsoid(bm, (X(21.9), Y(12.5), 0.4), (0.7 / 12, 0.7 / 12, 0.05), sides=8, rings=4, mat=LIGHT)
    # Pale caps where the canisters meet the roof (rows 7-9).
    for c in (5.0, 21.0):
        lib.cylinder_y(bm, X(c), Y(9.6), Y(7.6), 0.3, 2.4 / 12, 0.19, sides=12, mat=LBLUE)

    # Grey box in the middle (columns 7-18): bevelled top (rows 9-14), sloping front (rows 14-18).
    def box_top():
        lib.bevel_block(bm, rect(7, 9.2, 18, 14.2), 0.04, 0.38, 1.0 / 12, bevel_h=0.05, mat=GREY9, top_mat=PLATE)
        lib.bevel_block(bm, rect(7.2, 14.0, 17.8, 18.0), 0.04, 0.26, 0.6 / 12, bevel_h=0.04, mat=GREY4,
                        top_mat=WALL)
        lib.prism(bm, rect(7.0, 13.0, 10.0, 14.2), 0.33, 0.385, mat=RIDGE)  # lit lower-left corner
    flat(box_top)

    # Blue panel in front (columns 7-13, rows 19-26) with a light left edge, and the grey block and
    # small blue cap beside it (columns 13-18, rows 18-24); a blue rail along row 26.
    flat(lambda: lib.bevel_block(bm, rect(7, 18.8, 13, 25.6), 0.04, 0.22, 0.6 / 12, bevel_h=0.03, mat=DBLUE,
                                 top_mat=BLUE))
    flat(lambda: lib.prism(bm, rect(7, 19, 8, 25.4), 0.04, 0.235, mat=LBLUE))
    flat(lambda: lib.prism(bm, rect(13, 19.6, 18, 24.2), 0.04, 0.16, mat=WALL))
    flat(lambda: lib.prism(bm, rect(14.8, 17.8, 18, 19.8), 0.04, 0.2, mat=BLUE))
    flat(lambda: lib.prism(bm, rect(7, 25.8, 18, 27.0), 0.04, 0.1, mat=DBLUE, top_mat=BLUE))
    flat(lambda: lib.prism(bm, rect(7, 25.8, 8, 27.0), 0.04, 0.11, mat=LBLUE))

    # Grey machinery on the left (columns 2-7, rows 17-24).
    flat(lambda: lib.prism(bm, rect(2.5, 17.5, 7, 24), 0.04, 0.14, mat=GREY4, top_mat=WALL))

    # ---- side walls down both sides (into newshf-81) ----
    flat(lambda: lib.bevel_block(bm, P([(0, 9.4), (2.6, 9.4), (2.6, 28.5), (1.5, 29), (1.5, 49.5), (0, 49.5)]),
                                 0.04, 0.3, 0.5 / 12, bevel_h=0.03, mat=GREY4, top_mat=WALL))
    flat(lambda: lib.bevel_block(bm, P([(21, 17.3), (24, 17.3), (24, 49.5), (22.6, 49.5), (22.6, 40.5),
                                        (21, 40)]), 0.04, 0.3, 0.5 / 12, bevel_h=0.03, mat=GREY4,
                                 top_mat=WALL))
    flat(lambda: lib.prism(bm, rect(23, 17.3, 24, 49.5), 0.29, 0.31, mat=SEAM))

    # ---- newshf-81: posts, blocks, the pipe rig and the cannon (rows 28-56) ----

    # Blue posts on the walls (rows 29-35) with pale tops.
    for c, top in ((2.5, LBLUE), (21.5, LIGHT2)):
        lib.cylinder_y(bm, X(c), Y(35.8), Y(29.0), 0.3, 1.5 / 12, 0.12, sides=10, mat=BLUE, cap_mat=top)
        lib.cylinder_y(bm, X(c), Y(30.6), Y(29.2), 0.3, 1.55 / 12, 0.125, sides=10, mat=LBLUE)
    lib.ellipsoid(bm, (X(20.5), Y(29.5), 0.4), (0.6 / 12, 0.6 / 12, 0.04), sides=8, rings=4, mat=LIGHT2)

    # Blue blocks lower on the walls (rows 41-48).
    flat(lambda: lib.bevel_block(bm, rect(1.5, 41, 5, 47.6), 0.04, 0.26, 0.6 / 12, bevel_h=0.03, mat=DBLUE,
                                 top_mat=BLUE))
    flat(lambda: lib.bevel_block(bm, rect(19.8, 41, 23, 47.6), 0.04, 0.26, 0.6 / 12, bevel_h=0.03, mat=DBLUE,
                                 top_mat=BLUE))
    flat(lambda: lib.prism(bm, rect(19.8, 41, 20.8, 47.2), 0.04, 0.27, mat=LBLUE))

    # The pipe rig round the breech: a bright crossbar with two lights (rows 42-44), pipes up from
    # it, a grey post, and pipes off to the walls.
    lib.cylinder_y(bm, X(9.9), Y(42.5), Y(36.8), 0.13, 1.1 / 12, 0.08, sides=8, mat=BLUE)
    lib.cylinder_y(bm, X(14.5), Y(43.5), Y(37.8), 0.13, 0.85 / 12, 0.07, sides=8, mat=LBLUE)
    lib.cylinder_y(bm, X(16.5), Y(43.5), Y(37.8), 0.13, 0.85 / 12, 0.07, sides=8, mat=DBLUE)
    lib.cylinder_y(bm, X(8.5), Y(47.0), Y(43.5), 0.1, 0.9 / 12, 0.06, sides=8, mat=DEEP)
    lib.cylinder_y(bm, X(13.8), Y(47.5), Y(43.5), 0.1, 1.0 / 12, 0.06, sides=8, mat=DBLUE)
    flat(lambda: lib.bevel_block(bm, rect(7.8, 41.6, 13.0, 45.2), 0.04, 0.15, 0.4 / 12, bevel_h=0.02, mat=DBLUE,
                                 top_mat=BLUE))
    flat(lambda: lib.bevel_block(bm, rect(13.0, 42.0, 18.0, 44.6), 0.04, 0.13, 0.4 / 12, bevel_h=0.02, mat=DBLUE,
                                 top_mat=BLUE))
    flat(lambda: lib.prism(bm, rect(16.5, 37.6, 21.0, 39.4), 0.04, 0.12, mat=DEEP, top_mat=DBLUE))
    flat(lambda: lib.bevel_block(bm, rect(12, 36.2, 14, 42), 0.04, 0.24, 0.3 / 12, bevel_h=0.02, mat=GREY4,
                                 top_mat=GREY9))

    # Pipes across (left at row 40, right at row 38) and the crossbar (rows 42-44).
    for c0, c1, r, mat, rad in ((7.0, 11.0, 40.5, LBLUE, 0.9), (16.5, 21.0, 38.5, DEEP, 0.9),
                                (7.6, 17.5, 43.0, LBLUE, 1.3)):
        start = len(bm.verts)
        fstart = len(bm.faces)
        common.loft(bm, [(X(c0), rad / 12, rad / 12 * 0.9, 0.0), (X(c1), rad / 12, rad / 12 * 0.9, 0.0)],
                    sides=8, mat_index=mat)
        bm.verts.ensure_lookup_table()
        for v in bm.verts[start:]:  # loft builds along Y: turn it to run along X at row r
            v.co.x, v.co.y = v.co.y, Y(r) + v.co.x
            v.co.z += 0.15
        bm.faces.ensure_lookup_table()
        for f in bm.faces[fstart:]:
            f.smooth = len(f.verts) == 4
    for c in (8.5, 11.5):
        lib.ellipsoid(bm, (X(c), Y(43.5), 0.23), (0.75 / 12, 0.75 / 12, 0.05), sides=8, rings=4, mat=LIGHT)

    # The cannon: breech (rows 46-50), a pale blue band (rows 51-53), the barrel and a wide muzzle
    # with a dark bore on top (newshf-119 rows 0-5).
    cx = X(11.5)
    for y0, y1, rad, mat in ((46.3, 50.3, 1.6, GREY4), (50.3, 51.0, 1.4, DARK), (51.0, 53.0, 1.75, PBLUE),
                             (53.0, 54.0, 1.4, RIB), (54.0, 56.0, 1.6, ROOF)):
        lib.cylinder_y(bm, cx, Y(y1), Y(y0), 0.17, rad / 12, rad / 12 * 0.95, sides=12, mat=mat)
    flat(lambda: lib.bevel_block(bm, rect(9.0, 55.8, 14.0, 61.6), 0.04, 0.27, 0.6 / 12, bevel_h=0.04, mat=GREY4,
                                 top_mat=SEAM))
    flat(lambda: lib.prism(bm, rect(9.0, 55.8, 14.0, 57.6), 0.27, 0.285, mat=RIDGE))
    flat(lambda: lib.prism(bm, rect(10.0, 57.8, 13.0, 60.6), 0.25, 0.29, mat=DARK))

    # Grey deck plates either side of the barrel (rows 50-56), lit along their back edge.
    for c0, c1 in ((0, 9.2), (13.8, 24)):
        flat(lambda c0=c0, c1=c1: lib.bevel_block(bm, rect(c0, 50.2, c1, 56), 0.04, 0.22, 0.4 / 12, bevel_h=0.02,
                                                  mat=RIB, top_mat=GREY4))
        flat(lambda c0=c0, c1=c1: lib.prism(bm, rect(c0, 50.8, c1, 51.8), 0.22, 0.235, mat=SEAM))
    flat(lambda: lib.prism(bm, rect(3, 50.4, 8.5, 51.0), 0.22, 0.24, mat=WALL))

    # ---- newshf-119: the ribbed front face of the deck, stepping down (rows 56-66) ----
    steps = [(56.0, 57.2, 0.2, RIB), (57.2, 58.0, 0.17, DARK), (58.0, 59.0, 0.16, RIB), (59.0, 65.0, 0.12, DARK),
             (65.0, 66.0, 0.07, RIB), (66.0, 66.5, 0.05, DARK)]
    for r0, r1, z, mat in steps:
        for c0, c1 in ((0, 9.0), (14.0, 24)):
            flat(lambda r0=r0, r1=r1, z=z, mat=mat, c0=c0, c1=c1: lib.prism(bm, rect(c0, r0, c1, r1), 0.04, z,
                                                                             mat=mat))
    # Vertical slats in the face (the grille at rows 59-64).
    for c in (1, 3, 18, 20, 22):
        flat(lambda c=c: lib.prism(bm, rect(c, 59.0, c + 0.8, 64.8), 0.04, 0.135, mat=RIB))
    for c in (5.2, 6.4, 15.2):
        flat(lambda c=c: lib.prism(bm, rect(c, 58.6, c + 0.8, 63.5), 0.04, 0.14, mat=GREY4))

    bm.faces.ensure_lookup_table()
    flat_set = set()
    for a, b in flat_faces:
        flat_set.update(range(a, b))
    for i, f in enumerate(bm.faces):
        if i in flat_set:
            f.smooth = False
    return lib.mesh_object_mixed(NAME, bm, mats, coll), mats, coll


def flame(sprite_mats, coll):
    """newshf-119's second frame: the muzzle flash shooting down the screen out of the bore (piece
    coordinates of newshf-119: columns 9-13, rows 1-11)."""
    bm = bmesh.new()
    ex, ey = lib.ex, lib.ey
    common.loft(bm, [(ey(11.8), 0.0, 0.0, 0.0), (ey(10.5), 1.0 / 12, 0.05, 0.0), (ey(8.5), 1.6 / 12, 0.08, 0.0),
                     (ey(6.0), 2.5 / 12, 0.11, 0.0), (ey(3.0), 2.5 / 12, 0.11, 0.0), (ey(1.3), 1.6 / 12, 0.08, 0.0),
                     (ey(0.8), 0.0, 0.0, 0.0)], sides=12, mat_index=0)
    lib.move(bm, 0, ex(11.5), 0, 0.27)
    start = len(bm.verts)
    common.loft(bm, [(ey(9.8), 0.0, 0.0, 0.0), (ey(8.0), 1.2 / 12, 0.08, 0.0), (ey(5.0), 1.8 / 12, 0.11, 0.0),
                     (ey(2.2), 1.6 / 12, 0.1, 0.0), (ey(1.6), 0.0, 0.0, 0.0)], sides=10, mat_index=1)
    lib.move(bm, start, ex(11.5), 0, 0.32)
    lib.ellipsoid(bm, (ex(11.5), ey(4.0), 0.43), (0.9 / 12, 1.6 / 12, 0.03), sides=8, rings=6, mat=2)
    return common.mesh_object("newshf-119-f2_flame", bm, sprite_mats, coll, smooth=True)


def composite_png(out):
    """The whole bunker (both columns, first frames) as one 72 x 84 image (the bunker in the
    middle, matching render_preview's size-6 view)."""
    import numpy as np
    img = np.zeros((84, 72, 4), dtype=np.float32)
    for name, _, cy in LAYOUT:
        data = common.load_sprite(ROOT, name)
        frame = data["frames"][0]
        for x0 in (12, 36):
            y0 = cy + 42 - 14
            for r, row in enumerate(frame["pixels"]):
                for c, v in enumerate(row):
                    if v >= 0 and 0 <= y0 + r < 84:
                        img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 72, 84, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = lib.merged_colors(ROOT, PIECES)
    obj, mats, coll = build(sprite)
    pieces = common.split_assembly(obj, LAYOUT)

    data119 = common.load_sprite(ROOT, "newshf-119")
    fmats = [common.palette_material(data119, 119, "nshf119f", emission_strength=3.0),
             common.palette_material(data119, 123, "nshf119f", emission_strength=4.5),
             common.palette_material(data119, 127, "nshf119f", emission_strength=6.0)]
    fire = flame(fmats, coll)

    for name in ("newshf-43", "newshf-81"):
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    s = data119["sprites"][0]
    common.export_sprite_model(ROOT, [pieces["newshf-119"]], "enemies/newshf-119",
                               [{**s, "frames": [119]}])
    common.export_sprite_model(ROOT, [pieces["newshf-119"], fire], "enemies/newshf-119-f2",
                               [{**s, "frames": [121]}])

    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = composite_png(Path(tempfile.mkdtemp()) / "assembly.png")
        twins = []
        for dx in (-1.0, 1.0):
            twin = obj.copy()
            twin.location.x = dx
            coll.objects.link(twin)
            twins.append(twin)
        common.render_preview(twins, str(out), ref, size=6, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)
        img = ROOT / "reference" / "models" / "newshf-119" / data119["frames"][1]["image"]
        common.render_preview([pieces["newshf-119"], fire], str(out.parent / "newshf-119-f2.png"), img, size=2)


if __name__ == "__main__":
    main()
