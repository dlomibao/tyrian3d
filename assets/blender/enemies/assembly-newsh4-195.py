"""Bronze boss arm (newsh4.shp, assembly of 7 pieces): a 3D version of its sprites.

Seen in levels 1.3 and 3.17. Seven 2x2 enemies in a row make one 168x28 px arm reaching out to
the right (sprite.json `assemblyLayout`): a thick bronze upper arm with a dark underside
(newsh4-153), a ball joint on a narrow neck (newsh4-155), a forearm ringed by a grey metal collar
and a bright rib (newsh4-157), a grey-brown box and a grey block on top (newsh4-159), and a
tapering horn-like claw that curves down to a point (newsh4-191, -193, -195) with two small grey
clamps on it. Every piece has one frame.

The whole arm is built once in assembly coordinates, then cut into the seven pieces with
common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh4-195.py [-- --preview out.png]
(the preview is the whole arm; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "assembly-newsh4-195"
ROOT = common.repo_root(__file__)
PIECES = ["newsh4-153", "newsh4-155", "newsh4-157", "newsh4-159", "newsh4-191", "newsh4-193", "newsh4-195"]
# Assembly pixel (0, 0) is the top-left corner of newsh4-153 (screen cx 50 - 12, cy -18 - 14);
# the arm is 168 x 28 px and its centre (screen 122, -18) is the Blender origin.
CX0, CY0 = 122, -18
W, H = 168, 28
PX = 1 / 12


def XE(u):
    """Assembly pixel-edge coordinate (column c spans u in [c, c + 1]) to Blender X."""
    return (u - W / 2) / 12


def YE(v):
    """Assembly pixel-edge coordinate (row r spans v in [r, r + 1]) to Blender Y (up is +Y)."""
    return (H / 2 - v) / 12


# --- geometry helpers --------------------------------------------------------------------------

def _faces_between(bm, rings, mat, smooth, cap_start=True, cap_end=True):
    sides = max(len(r) for r in rings)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            faces.append(bm.faces.new(f))
    if cap_start and len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_end and len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces


def loft_x(bm, sections, sides=12, mat=0, smooth=True, shear=None):
    """A tube along the arm (+X). Sections are (u, v_top, v_bottom, half_height_units, z): the
    pixel-edge column and the top and bottom pixel edges it covers there. Zero width collapses
    the ring to a point. `shear(u, v)` may return a column offset per vertex (slanted ends)."""
    rings = []
    for u, vt, vb, hz, z in sections:
        vc, hw = (vt + vb) / 2, (vb - vt) / 2
        if hw <= 0 and hz <= 0:
            rings.append([bm.verts.new((XE(u), YE(vc), z))])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            v = vc - hw * math.cos(a)
            uu = u + (shear(u, v) if shear else 0.0)
            ring.append(bm.verts.new((XE(uu), YE(v), z + hz * math.sin(a))))
        rings.append(ring)
    return _faces_between(bm, rings, mat, smooth)


def sweep(bm, path, sides=8, mat=0, smooth=True):
    """A tube along a path of (u, v, z, half_width_px, half_height_units), rings perpendicular
    to the path in the XY plane."""
    pts = [Vector((XE(u), YE(v), z)) for u, v, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (u, v, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * PX * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
    return _faces_between(bm, rings, mat, smooth)


def block(bm, u0, v0, u1, v1, z0, z1, mat=0, bevel=0.0):
    """A box over pixel edges [u0, u1] x [v0, v1], from z0 up to z1 (top edges chamfered by `bevel` px)."""
    b = bevel
    outline = [(XE(u0), YE(v1)), (XE(u1), YE(v1)), (XE(u1), YE(v0)), (XE(u0), YE(v0))]
    n = len(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    if b:
        top = [(XE(u0 + b), YE(v1 - b)), (XE(u1 - b), YE(v1 - b)), (XE(u1 - b), YE(v0 + b)), (XE(u0 + b), YE(v0 + b))]
        common.slab(bm, top, b * PX, z=z1 + b * PX / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n:]:
        f.smooth = False


def ellipsoid(bm, u, v, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8):
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for vert in res["verts"]:
        vert.co = Vector((XE(u) + vert.co.x * rx_px * PX, YE(v) + vert.co.y * ry_px * PX, z + vert.co.z * rz))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = True


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


# --- the sprite as one grid --------------------------------------------------------------------

def grid():
    """The assembly's pixels (palette indices, -1 transparent) as rows of W columns."""
    g = [[-1] * W for _ in range(H)]
    sprite = common.load_sprite(ROOT, PIECES[0])
    for e in sprite["assemblyLayout"]:
        frame = common.load_sprite(ROOT, e["model"])["frames"][0]
        x0, y0 = e["cx"] - CX0 + W // 2 - 12, e["cy"] - CY0 + H // 2 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, val in enumerate(row):
                if val >= 0:
                    g[y0 + r][x0 + c] = val
    return g


def profile(g, c):
    """Top and bottom pixel edges of the sprite in column c."""
    rows = [r for r in range(H) if g[r][c] >= 0]
    return rows[0], rows[-1] + 1


# --- the arm -----------------------------------------------------------------------------------

def build(sprite, g):
    coll = common.reset_collection(NAME)
    tag = "nsh4a"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(24, metallic=0.45, roughness=0.35),  # 0 bronze upper arm and ball
        pal(18, metallic=0.35, roughness=0.5),  # 1 dark underside
        pal(21, metallic=0.4, roughness=0.4),  # 2 forearm and claw
        pal(23, metallic=0.4, roughness=0.4),  # 3 lighter rail along the forearm
        pal(26, metallic=0.5, roughness=0.3),  # 4 bright ribs and rims
        pal(8, metallic=0.8, roughness=0.25),  # 5 grey metal collar
        pal(2, metallic=0.4, roughness=0.6),  # 6 dark lower half of the collar
        pal(166, metallic=0.4, roughness=0.45),  # 7 grey-brown box
        pal(5, metallic=0.75, roughness=0.3),  # 8 grey block
        pal(4, metallic=0.7, roughness=0.35),  # 9 grey clamps
        pal(19, metallic=0.35, roughness=0.5),  # 10 neck
        pal(164, metallic=0.4, roughness=0.5),  # 11 box strut
    ]
    BRONZE, UNDER, ARM, RAIL, RIB, COLLAR, CDARK, BOX, GREY, CLAMP, NECK, STRUT = range(12)
    bm = bmesh.new()

    # Upper arm (columns 0-31): a thick tube, cut off by the piece's left edge, rounded at its end.
    loft_x(bm, [(-2, 1, 13, 0.27, 0.04), (26, 1, 13, 0.27, 0.04), (28.5, 1.3, 12.7, 0.25, 0.04),
                (30.5, 2.2, 11.8, 0.2, 0.04), (31.6, 4.0, 10.0, 0.12, 0.04), (32.0, 7.0, 7.0, 0.0, 0.04)],
           sides=16, mat=BRONZE)
    # Its dark underside (rows 13-21), ending in a slanted edge with a bright rim.
    loft_x(bm, [(-2, 12.5, 22, 0.2, -0.06), (27.5, 12.5, 22, 0.2, -0.06), (29.0, 13.0, 21.5, 0.16, -0.06),
                (29.6, 14.5, 20.0, 0.08, -0.06)], sides=12, mat=UNDER,
           shear=lambda u, v: 0.0 if u < 20 else (22 - v) * 0.7)
    sweep(bm, [(28.6, 21.6, -0.04, 0.6, 0.06), (32.0, 18.0, -0.03, 0.7, 0.07), (35.0, 14.5, -0.03, 0.6, 0.06)],
          sides=6, mat=RIB)

    # Neck (columns 30-37) and the ball joint (columns 34-52) with its lower lobe.
    loft_x(bm, [(29, 2, 13, 0.19, 0.02), (38, 2.5, 13, 0.19, 0.02)], sides=12, mat=NECK)
    ellipsoid(bm, 43.2, 9.0, 0.0, 8.6, 8.0, 0.29, mat=BRONZE, segments=18, rings=10)
    ellipsoid(bm, 42.2, 14.5, -0.06, 6.0, 5.5, 0.2, mat=UNDER, segments=14, rings=8)

    # Forearm and claw (columns 46-166): the upper body down to row 10, then the whole tapering
    # claw as the sprite outlines it, thinning to a point at the tip.
    secs = []
    for u in [46, 50] + list(range(54, 104, 8)) + list(range(104, 166, 3)) + [165.5]:
        c = min(int(u), W - 3)
        # Average the stepped pixel outline over a few columns so the claw's edges run smooth.
        near = [profile(g, k) for k in range(max(c - 2, 0), min(c + 3, W - 2))]
        top = sum(p[0] for p in near) / len(near)
        bot = sum(p[1] for p in near) / len(near)
        if u < 101:
            bot = 10.6
        elif u < 106:
            bot = 10.6 + (u - 101) / 5 * (bot - 10.6)
        t = max(0.0, (u - 50) / 116)
        hz = 0.24 * (1 - t) ** 0.9 + 0.015
        z = -0.06 * t * t
        secs.append((u, top, bot, hz, z))
    u_tip = 166.2
    secs.append((u_tip, 24.6, 24.6, 0.0, -0.06))
    loft_x(bm, secs, sides=12, mat=ARM)

    # Lighter rail along the forearm's lower side (rows 11-12), widening at its root over the ball.
    loft_x(bm, [(45.5, 11.5, 12.5, 0.0, -0.05), (46.5, 10.2, 14.0, 0.12, -0.05), (52, 10.2, 13.2, 0.14, -0.05),
                (57, 10.2, 13.0, 0.15, -0.05), (100, 10.2, 13.0, 0.14, -0.05), (106, 10.5, 13.6, 0.12, -0.05),
                (110, 11.5, 13.0, 0.0, -0.05)], sides=10, mat=RAIL)

    # Grey metal collar (columns 57-65): bright above, dark below, with a bright rib beside it.
    faces = loft_x(bm, [(56.4, 0.8, 13.0, 0.0, 0.0), (56.6, 0.6, 13.2, 0.27, 0.0), (65.6, 0.6, 13.2, 0.27, 0.0),
                        (65.8, 0.8, 13.0, 0.0, 0.0)], sides=16, mat=COLLAR)
    split_y = YE(7.0)
    for f in faces:
        if f.calc_center_median().y < split_y:
            f.material_index = CDARK
    loft_x(bm, [(65.9, 1.0, 13.0, 0.0, -0.01), (66.0, 0.8, 13.2, 0.26, -0.01), (67.0, 0.8, 13.2, 0.26, -0.01),
                (67.1, 1.0, 13.0, 0.0, -0.01)], sides=14, mat=RIB)

    # Grey-brown box on top (columns 76-82, rows 1-6) with a strut down its right side.
    block(bm, 75.8, 1.4, 82.6, 6.6, 0.0, 0.27, mat=BOX, bevel=0.5)
    block(bm, 79.6, 6.4, 82.6, 12.8, -0.12, 0.18, mat=STRUT)
    # Grey block (columns 84-89, rows 2-6).
    block(bm, 84.4, 1.8, 89.6, 7.2, 0.0, 0.26, mat=GREY, bevel=0.5)
    # Small grey bits at the collar's foot (columns 71-73, rows 9-12).
    block(bm, 70.6, 8.8, 73.4, 12.4, -0.12, 0.12, mat=CLAMP)

    # Grey clamps on the claw (columns 105-111, rows 4-8 and columns 124-129, rows 7-11), each
    # with a bright rib behind it.
    block(bm, 104.6, 4.4, 111.4, 8.6, -0.05, 0.2, mat=CLAMP, bevel=0.4)
    block(bm, 123.6, 6.6, 129.6, 11.4, -0.06, 0.16, mat=CLAMP, bevel=0.4)
    for u, hz in ((112.0, 0.2), (130.2, 0.16)):
        top, bot = profile(g, int(u))
        loft_x(bm, [(u - 0.1, top + 0.3, bot - 0.3, 0.0, 0.0), (u, top - 0.1, bot + 0.1, hz, -0.02),
                    (u + 1.0, top, bot + 0.1, hz, -0.02), (u + 1.1, top + 0.3, bot - 0.3, 0.0, -0.02)],
               sides=12, mat=RIB)

    return to_object(NAME, bm, mats, coll)


def merged_sprite():
    """newsh4-195's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsh4-195")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(g, colors, out):
    """The whole arm's sprite as one image, padded to the 24:28 shape that render_preview expects
    for size 14 (168 x 196 px, the arm in the middle)."""
    import numpy as np
    img = np.zeros((196, 168, 4), dtype=np.float32)
    y0 = (196 - H) // 2
    for r in range(H):
        for c in range(W):
            if g[r][c] >= 0:
                img[y0 + r, c] = [*(ch / 255 for ch in colors[str(g[r][c])]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 168, 196, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    g = grid()
    obj = build(sprite, g)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    print(f"whole arm: {len(obj.data.polygons)} faces")
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(g, sprite["colors"], Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=14, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
