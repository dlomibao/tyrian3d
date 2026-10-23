"""Blue-glass fortress (newsh7.shp 1, 3, 39 and 41, a 2x2 block): a 3D version of its sprites.

Seen in episode 3 (level 3.10). Four 2x2 sprites make one 48 x 56 px ground structure standing in
water: a wide grey platform with a lit rim, blue skylights in its top corners, rows of raised side
panels, a bar across its back and two pillars round a dark well holding a lying blue canister with
a collar. In front of the well a tall grey housing with chamfered shoulders rises from the platform
and runs out over the water: four glowing blue glass tubes on its top, two blue lights, a ledge,
two glass-topped blocks with glowing slots, and a sloped front with a big glowing blue lens in a
dark socket, blue pipes down its sides and two small blue vents at its foot. The water round it
(the right edge and the bottom of the sprites) is a flat apron in the sprite's water colours.

Built whole in assembly coordinates, then cut into the four pieces (newsh7-1 top left, newsh7-3
top right, newsh7-39 bottom left, newsh7-41 bottom right). Each sprite has one frame.

Run: blender --background --python assets/blender/enemies/assembly-newsh7-39.py [-- --preview out.png]
(the preview is the whole structure; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "assembly-newsh7-39"
ROOT = common.repo_root(__file__)
PIECES = ["newsh7-1", "newsh7-3", "newsh7-39", "newsh7-41"]
# Assembly pixel (0, 0) is the top-left corner of newsh7-1 (screen cx 248 - 12, cy -18 - 14); the
# block is 48 x 56 px and its centre (screen 260, -4) is the Blender origin.
CX0, CY0 = 260, -4
U = 1 / 12  # one sprite pixel in units

PLAT = 0.20  # platform top
HZ = 0.42  # housing top
FOOT = 0.16  # where the housing's sloped front meets its foot


def XE(e):
    """Assembly pixel column edge to Blender X."""
    return (e - 24) * U


def YE(e):
    """Assembly pixel row edge to Blender Y (sprite up is +Y)."""
    return (28 - e) * U


def tag(bm, before, mat, smooth):
    """Set the material and shading of every face not in `before` (a set of the earlier faces)."""
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def box(bm, c0, r0, c1, r1, z0, z1, mat):
    """A flat-shaded box over pixel edges c0..c1, r0..r1, from z0 to z1."""
    n = set(bm.faces)
    pts = [(XE(c0), YE(r1)), (XE(c1), YE(r1)), (XE(c1), YE(r0)), (XE(c0), YE(r0))]
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2)
    tag(bm, n, mat, False)


def poly(bm, edges, z0, z1, mat):
    """A flat-shaded prism with an outline of (column edge, row edge) points."""
    n = set(bm.faces)
    pts = [(XE(c), YE(r)) for c, r in edges]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2)
    tag(bm, n, mat, False)


def tube_y(bm, col_edge, sections, mat, sides=10, smooth=True):
    """A loft down the sprite centred on a column edge: sections are (row edge, half width px,
    half height, z centre)."""
    before, n = set(bm.verts), set(bm.faces)
    common.loft(bm, [(YE(r), w * U, h, z) for r, w, h, z in sections], sides=sides)
    for vert in set(bm.verts) - before:  # (common.shift_x goes by index, which create_uvsphere upsets)
        vert.co.x += XE(col_edge)
    tag(bm, n, mat, smooth)


def prism_x(bm, c0, c1, profile, mat):
    """A prism running across the sprite from column edge c0 to c1 with a (row edge, z) profile."""
    n = set(bm.faces)
    left = [bm.verts.new((XE(c0), YE(r), z)) for r, z in profile]
    right = [bm.verts.new((XE(c1), YE(r), z)) for r, z in profile]
    bm.faces.new(left)
    bm.faces.new(list(reversed(right)))
    k = len(profile)
    for i in range(k):
        j = (i + 1) % k
        bm.faces.new((left[j], left[i], right[i], right[j]))
    tag(bm, n, mat, False)


def ellipsoid(bm, ce, re, z, rx_px, ry_px, rz, mat, tilt=0.0, segments=16, rings=8):
    """An ellipsoid centred on (column edge, row edge, z), tipped by `tilt` radians so its top
    faces down the screen."""
    n = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    ca, sa = math.cos(tilt), math.sin(tilt)
    for vert in res["verts"]:
        x, y, zz = vert.co.x * rx_px * U, vert.co.y * ry_px * U, vert.co.z * rz
        vert.co = Vector((XE(ce) + x, YE(re) + y * ca - zz * sa, z + y * sa + zz * ca))
    tag(bm, n, mat, True)


def slope_z(r):
    """Height of the housing's sloped front at row edge r (flat top to row 41, foot at 49.5)."""
    if r <= 41:
        return HZ
    return HZ - (HZ - FOOT) * min(1.0, (r - 41) / 8.5)


def to_object(name, bm, mats, coll):
    """Like common.mesh_object, but keeps each face's own smooth/flat flag."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


# --- the structure -----------------------------------------------------------------------------

def build(sprite, coll):
    t = "nsh7_39"
    pal = lambda i, **kw: common.palette_material(sprite, i, t, **kw)  # noqa: E731
    mats = [
        pal(4, metallic=0.4, roughness=0.55),  # 0 platform grey
        pal(7, metallic=0.45, roughness=0.45),  # 1 light grey rims, housing
        pal(6, metallic=0.4, roughness=0.5),  # 2 mid grey panels, pillars
        pal(5, metallic=0.4, roughness=0.5),  # 3 dark grey band, steps
        pal(8, metallic=0.45, roughness=0.4),  # 4 lit pillar faces
        pal(10, metallic=0.5, roughness=0.35),  # 5 bright ridges
        pal(11, metallic=0.5, roughness=0.3),  # 6 shoulder lip highlight
        pal(3, metallic=0.3, roughness=0.7),  # 7 dark grooves
        pal(2, metallic=0.3, roughness=0.8),  # 8 shadow, lens socket
        pal(130, metallic=0.4, roughness=0.3),  # 9 blue window frames, right pipe
        pal(129, metallic=0.6, roughness=0.15),  # 10 blue skylight glass, collar, left pipe
        pal(56, metallic=0.5, roughness=0.3),  # 11 blue canister
        pal(54, metallic=0.5, roughness=0.3),  # 12 dark blue backing, vents
        pal(158, metallic=0.2, roughness=0.15, emission_strength=2.0),  # 13 glowing glass tubes
        pal(157, metallic=0.2, roughness=0.15, emission_strength=2.0),  # 14 tube tips
        pal(155, emission_strength=3.0),  # 15 left blue light
        pal(153, emission_strength=3.0),  # 16 right blue light
        pal(154, metallic=0.2, roughness=0.15, emission_strength=3.0),  # 17 lens, slots
        pal(141, emission_strength=5.0),  # 18 lens highlight
        pal(58, metallic=0.5, roughness=0.15),  # 19 glass tops of the front blocks
        pal(147, metallic=0.3, roughness=0.4),  # 20 deep blue lens rim
    ]
    (GREY, LIGHT, MID, DARK, LIT, RIDGE, LIP, GROOVE, SHADOW, FRAME, GLASS, CAN, BACK, TUBE, TIP,
     LAMP_L, LAMP_R, LENS, SHINE, TOPGLASS, RIM) = range(len(mats))
    bm = bmesh.new()

    # Platform (columns 1-42, rows 1-36) with a lit rim on its top, left and right edges.
    box(bm, 1, 1, 43, 37, 0.0, PLAT, GREY)
    box(bm, 1, 1, 43, 2, PLAT, PLAT + 0.04, LIGHT)
    box(bm, 1, 2, 2, 35, PLAT, PLAT + 0.04, LIGHT)
    box(bm, 42, 2, 43, 35, PLAT, PLAT + 0.04, MID)
    box(bm, 2, 28, 5, 34, PLAT, PLAT + 0.01, MID)  # lighter strip left of the housing
    box(bm, 5, 25, 6, 37, PLAT, PLAT + 0.006, GROOVE)  # shadow lines either side of the housing
    box(bm, 38, 27, 41, 36, PLAT, PLAT + 0.006, SHADOW)

    # Bar across the back (columns 9-34, rows 3-5) with a lit upper edge.
    box(bm, 9, 3, 35, 6, PLAT, 0.29, DARK)
    box(bm, 9, 3, 35, 4, 0.29, 0.30, MID)

    # Skylights in the top corners: a blue frame round darker glass.
    for c in (3, 36):
        box(bm, c, 3, c + 5, 8, PLAT, 0.27, FRAME)
        box(bm, c + 1, 4, c + 4, 7, 0.27, 0.285, GLASS)

    # Side panels: grey blocks with a light L-shaped frame (left on the left side, right on the
    # right) and a small blue window in the corner next to the well.
    for r0 in (9, 15):
        box(bm, 3, r0, 8, r0 + 5, PLAT, 0.25, MID)
        box(bm, 3, r0, 4, r0 + 5, 0.25, 0.27, LIGHT)
        box(bm, 4, r0 + 4, 8, r0 + 5, 0.25, 0.27, LIGHT)
        box(bm, 6, r0, 8, r0 + 2, 0.25, 0.28, FRAME)
        box(bm, 36, r0, 41, r0 + 5, PLAT, 0.25, MID)
        box(bm, 40, r0, 41, r0 + 5, 0.25, 0.27, LIGHT)
        box(bm, 36, r0 + 4, 40, r0 + 5, 0.25, 0.27, LIGHT)
        box(bm, 36, r0, 38, r0 + 2, 0.25, 0.28, FRAME)
    box(bm, 3, 21, 6, 27, PLAT, 0.25, MID)
    box(bm, 3, 21, 4, 27, 0.25, 0.27, LIGHT)
    box(bm, 37, 21, 41, 27, PLAT, 0.25, MID)
    box(bm, 40, 21, 41, 27, 0.25, 0.27, LIGHT)

    # Pillars either side of the well, lit on their left faces, on low steps.
    for c in (10, 30):
        box(bm, c, 7, c + 1, 19, PLAT, 0.36, LIT)
        box(bm, c + 1, 7, c + 4, 19, PLAT, 0.36, MID)
        box(bm, c + 1, 7, c + 4, 8, 0.36, 0.37, LIGHT)
    box(bm, 8, 7, 10, 19, PLAT, 0.25, DARK)
    box(bm, 34, 7, 36, 19, PLAT, 0.25, DARK)

    # The blue canister lying in the well (columns 19-26, rows 7-18) with a wider collar.
    tube_y(bm, 23, [(6.6, 2.4, 0.08, 0.25), (7.2, 3.0, 0.11, 0.25), (17.0, 3.0, 0.11, 0.25),
                    (18.6, 2.6, 0.09, 0.25), (19.0, 2.0, 0.06, 0.25)], CAN, sides=12)
    tube_y(bm, 23, [(11.9, 3.6, 0.13, 0.25), (12.4, 4.0, 0.15, 0.25), (16.0, 4.0, 0.15, 0.25),
                    (16.6, 3.6, 0.13, 0.25)], GLASS, sides=12)

    # The housing: chamfered shoulders (rows 20-24), sides at columns 6 and 37.
    poly(bm, [(10, 20), (34, 20), (38, 24), (38, 38.5), (6, 38.5), (6, 24)], 0.0, HZ, LIGHT)
    box(bm, 33, 24, 38, 38.5, HZ, HZ + 0.006, DARK)  # its darker right side
    box(bm, 10, 20, 17, 21, HZ, HZ + 0.012, LIP)  # lit front edge of the shoulders
    box(bm, 30, 20, 34, 21, HZ, HZ + 0.012, RIDGE)
    # Its front runs out over the water to row 49 and slopes down to the foot.
    prism_x(bm, 7, 37, [(38, 0.0), (38, HZ), (41, HZ), (49.5, FOOT), (49.5, 0.0)], LIGHT)
    # Bright ridges down both shoulders (columns 11-12 and 31-32).
    for c in (12, 32):
        tube_y(bm, c, [(20.5, 0.0, 0.0, HZ), (21.0, 1.0, 0.035, HZ), (40.5, 1.0, 0.035, HZ),
                       (41.0, 0.0, 0.0, HZ)], RIDGE, sides=6)

    # Four glass tubes on a dark blue backing (columns 17-27, rows 19-30): glowing at the top,
    # dark down the middle, lit again at their lower tips.
    box(bm, 16.5, 19, 28.5, 31, HZ - 0.02, HZ + 0.012, BACK)
    for c in (18, 21, 24, 27):
        z = HZ + 0.02
        tube_y(bm, c, [(19.0, 0.0, 0.0, z), (19.3, 0.8, 0.035, z), (19.8, 1.0, 0.05, z),
                       (24.0, 1.0, 0.05, z)], TUBE, sides=8)
        tube_y(bm, c, [(24.0, 1.0, 0.05, z), (29.0, 1.0, 0.05, z)], FRAME, sides=8)
        tube_y(bm, c, [(29.0, 1.0, 0.05, z), (30.6, 1.0, 0.05, z), (31.0, 0.0, 0.0, z)], TIP, sides=8)

    # Blue lights either side of the tubes.
    box(bm, 14, 24, 16, 26, HZ, HZ + 0.03, LAMP_L)
    box(bm, 29, 24, 31, 26, HZ, HZ + 0.03, LAMP_R)

    # Ledge under the tubes and the dark groove below it.
    box(bm, 16, 31, 30, 34, HZ, HZ + 0.05, LIGHT)
    box(bm, 14, 34, 30, 36, HZ, HZ + 0.006, GROOVE)

    # Two glass-topped blocks with glowing slots, and a divider between them (rows 36-41).
    for c in (15, 24):
        box(bm, c, 36, c + 5, 41.5, HZ, HZ + 0.06, DARK)
        box(bm, c, 36, c + 5, 38, HZ + 0.06, HZ + 0.07, TOPGLASS)
        box(bm, c, 39, c + 5, 41.5, HZ + 0.06, HZ + 0.07, LENS)
        box(bm, c, 41.4, c + 5, 41.7, HZ - 0.02, HZ + 0.06, LENS)
    box(bm, 20, 36, 24, 41.5, HZ, HZ + 0.04, LIGHT)

    # The big lens in a dark socket on the sloped front (columns 17-28, rows 42-48).
    tilt = math.atan2(HZ - FOOT, 8.5 * U)
    zc = slope_z(45.5)
    ellipsoid(bm, 23, 45.8, zc, 8.6, 5.0, 0.025, SHADOW, tilt=tilt)
    ellipsoid(bm, 23, 45.6, zc + 0.01, 6.6, 3.9, 0.04, RIM, tilt=tilt)
    ellipsoid(bm, 23, 45.5, zc + 0.02, 5.8, 3.3, 0.07, LENS, tilt=tilt, segments=18, rings=9)
    ellipsoid(bm, 20.5, 45.2, zc + 0.09, 1.7, 0.9, 0.02, SHINE, tilt=tilt, segments=10, rings=5)

    # Blue pipes down the housing's sides (columns 5-6 and 37-38, rows 40-48).
    tube_y(bm, 6, [(39.0, 0.0, 0.0, 0.12), (39.6, 1.0, 0.07, 0.12), (48.6, 1.0, 0.07, 0.12),
                   (49.2, 0.0, 0.0, 0.12)], GLASS, sides=8)
    tube_y(bm, 38, [(39.0, 0.0, 0.0, 0.12), (39.6, 1.0, 0.07, 0.12), (48.6, 1.0, 0.07, 0.12),
                    (49.2, 0.0, 0.0, 0.12)], FRAME, sides=8)

    # Small blue vents at the foot (columns 12-13 and 30-31, rows 47-49).
    box(bm, 12, 47, 14, 49.5, 0.0, slope_z(47) - 0.01, BACK)
    box(bm, 30, 47, 32, 49.5, 0.0, slope_z(47) - 0.01, CAN)

    return to_object(NAME, bm, mats, coll)


WATER_LEVELS = (51, 54, 57, 59)


def water_index(v):
    """Quantise a water pixel to one of four palette shades (anything else reads as dark water)."""
    if v < 48 or v > 61:
        return 51
    return min(WATER_LEVELS, key=lambda w: abs(w - v))


def build_water(sprite, grid, coll):
    """A flat apron in the water's colours round the structure: the right edge (columns 44-47) and
    everything below the platform (rows 38-55) outside the housing, run-length merged per row."""
    t = "nsh7_39w"
    mats = [common.palette_material(sprite, i, t, metallic=0.1, roughness=0.2) for i in WATER_LEVELS]
    bm = bmesh.new()
    for r in range(56):
        runs = []
        for c in range(48):
            if not (c >= 44 or r >= 38):
                continue
            k = WATER_LEVELS.index(water_index(grid[r][c]))
            if runs and runs[-1][1] == c and runs[-1][2] == k:
                runs[-1][1] = c + 1
            else:
                runs.append([c, c + 1, k])
        for c0, c1, k in runs:
            vs = [bm.verts.new((XE(x), YE(y), 0.01)) for x, y in ((c0, r + 1), (c1, r + 1), (c1, r), (c0, r))]
            bm.faces.new(vs).material_index = k
    mesh = bpy.data.meshes.new(NAME + "_water")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME + "_water", mesh)
    coll.objects.link(obj)
    return obj


def merged_sprite():
    """newsh7-39's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsh7-39")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def assembly_grid(layout):
    """The 48 x 56 block's palette indices (first frames), rows top to bottom."""
    grid = [[-1] * 48 for _ in range(56)]
    for name, cx, cy in layout:
        frame = common.load_sprite(ROOT, name)["frames"][0]
        x0, y0 = cx + 24 - 12, cy + 28 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                grid[y0 + r][x0 + c] = v
    return grid


def composite_png(sprite, grid, out):
    """The whole structure's sprite as one 48 x 56 image (render_preview size 4)."""
    import numpy as np
    img = np.zeros((56, 48, 4), dtype=np.float32)
    for r in range(56):
        for c in range(48):
            v = grid[r][c]
            if v >= 0:
                img[r, c] = [*(ch / 255 for ch in sprite["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 48, 56, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    grid = assembly_grid(layout)
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    water = build_water(sprite, grid, coll)
    pieces = common.split_assembly(obj, layout)
    wpieces = common.split_assembly(water, [(n + "_w", cx, cy) for n, cx, cy in layout])
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name], wpieces[name + "_w"]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(sprite, grid, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj, water], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name], wpieces[name + "_w"]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
