"""newshm-55, the WINDY wall's blue question-mark block (newshm.shp frame 55, 24 x 28 px).

Identity: a WALL BLOCK of the fixed block wall (assembly-newshm-1), spawned on ground2 with the
family's dat3 +2 and no motion, turret or launcher. So it is built as the same cast part as
newshm-1/-15/-17/-53: lib_newshm_block's glossy rounded block (imported, not edited; its shell,
foot plate, parting groove, lifting sockets, plateau seam and shoulder bolts are the family's exact
formulas, so it tiles with its neighbours), in the sprite's steel blue, with a raised enamel
question mark on the flat top.

- Footprint: the block is the family's outline, pixel for pixel newshm-15's (same 5-3-2-1-1 corner
  staircase). The sprite is a full rectangle, though: its corners outside the block are opaque
  near-black (index 64, 68 px). They are built as what they read as, a flat dark bed plate (the
  socket / mortar bed the block is set in): pal_64, 0.24 px thick, filling the cell to the inner
  edge of the frame's ink ring (22 x 26 px, D74), so the top view covers the whole sprite mask, the
  game gets the original's black corners against the grass, and the cell still tiles.
- Colour: shell = the flat-top index 57 (D114: one body colour; the lit NW rim 60-63 and the dark
  south roll 53-55 are light on the shoulder and the slope), foot plate 52 (shell - 5, as the
  family). Question mark = 58, the trimmed median of its stroke pixels (its 60-61 upper-left edge and
  54-55 lower-right edge are the light on a raised stroke).
- Question mark: a rounded (half-pill) raised stroke conformed to the top, its centreline traced
  from the sprite (hook from row 8 col 8.5 over rows 5-6 to cols 14-15, down the diagonal to the
  stem foot at row 14), and a separate domed dot centred on the sprite's dot (11.6, 15.7). Small
  fillet at the stroke's foot so it reads cast with the block, not stuck on.
- Underside: the bed plate's flat closed bottom.

Run: blender --background --python assets/blender/enemies/newshm-55.py [-- --no-bake]
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "assets" / "blender" / "enemies"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
import lib_newshm_block as B  # noqa: E402

NAME = "newshm-55"
SHELL_PAL, FOOT_PAL, MARK_PAL, BED_PAL = 57, 52, 58, 64
BED_Z = 0.24        # px: bed plate thickness (0.02 m)
BED_CH = 0.3        # px: chamfer on the bed plate's corners

# Question mark, sprite pixel-index coords (col, row); B.P adds the half pixel.
HOOK = [(8.5, 8.3), (8.6, 7.1), (9.3, 6.1), (10.5, 5.5), (12.0, 5.35), (13.4, 5.7), (14.4, 6.6),
        (14.75, 7.9), (14.4, 9.1), (13.6, 10.15), (12.7, 11.1), (12.05, 12.1), (11.85, 12.9), (11.85, 13.35)]
STROKE_W = 1.9      # px
RAISE = 0.75        # px above the shell surface
DOT = (11.7, 15.9, 1.05, 0.68)   # col, row, radius, height (px)


def chaikin(pts, n=2):
    for _ in range(n):
        q = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            q += [(a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25),
                  (a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75)]
        q.append(pts[-1])
        pts = q
    return pts


def round_stroke(m, pts_px, width, raise_, mat, sink=0.35, nsec=9):
    """A raised stroke with a rounded section (a flattened half pill on a small foot fillet),
    conformed to the shell top, with domed end caps."""
    pts = chaikin([B.P(c, r) for c, r in pts_px], 3)
    n = len(pts)
    hw = width / 2
    # section: (lateral fraction of hw, height fraction of raise_) from one side round to the other
    sec = []
    for k in range(nsec):
        a = math.pi * k / (nsec - 1)          # 0 .. pi
        sec.append((math.cos(a), math.sin(a) ** 0.8))
    def make_row(x, y, nx, ny, ls=1.0, hs=1.0):
        w = hw * ls
        row = [m.bm.verts.new((x + nx * w * 1.12, y + ny * w * 1.12, B.surface_z(x + nx * w * 1.12, y + ny * w * 1.12) - sink))]
        for u, h in sec:
            px, py = x + nx * w * u, y + ny * w * u
            row.append(m.bm.verts.new((px, py, B.surface_z(px, py) + raise_ * h * hs)))
        row.append(m.bm.verts.new((x - nx * w * 1.12, y - ny * w * 1.12, B.surface_z(x - nx * w * 1.12, y - ny * w * 1.12) - sink)))
        return row

    frames = []
    for i, (x, y) in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy) or 1
        frames.append((x, y, dx / d, dy / d))
    rows = [make_row(x, y, -ty, tx) for x, y, tx, ty in frames]

    def cap(fr, sign):
        """Rounded end: the section shrinks on a quarter circle as it runs on past the end."""
        x, y, tx, ty = fr
        out = []
        for j in (1, 2, 3, 4):
            ang = math.pi / 2 * j / 4.6
            f = hw * math.sin(ang) * sign
            out.append(make_row(x + tx * f, y + ty * f, -ty, tx, max(math.cos(ang), 0.12), max(math.cos(ang), 0.12) ** 0.7))
        return out

    allrows = list(reversed(cap(frames[0], -1))) + rows + cap(frames[-1], 1)
    K = len(rows[0])
    for r0, r1 in zip(allrows, allrows[1:]):
        for k in range(K):
            j = (k + 1) % K
            m.bm.faces.new((r0[k], r1[k], r1[j], r0[j])).material_index = mat
    m.bm.faces.new(allrows[0]).material_index = mat
    m.bm.faces.new(allrows[-1]).material_index = mat
    return rows


def dome(m, c, r, rad, h, mat, sink=0.35, nring=6, nseg=20):
    cx, cy = B.P(c, r)
    zs = B.surface_z(cx, cy)
    rings = []
    for k in range(nring):
        t = k / (nring - 1)                         # 0 at the foot, 1 near the crown
        rr = rad * (1.08 if k == 0 else math.cos(t * math.pi / 2 * 0.92))
        z = zs - sink if k == 0 else zs + h * math.sin(t * math.pi / 2 * 0.92) ** 0.9
        rings.append(m.ringv([(cx + rr * math.cos(2 * math.pi * i / nseg), cy + rr * math.sin(2 * math.pi * i / nseg)) for i in range(nseg)], z))
    for r0, r1 in zip(rings, rings[1:]):
        m.bridge(r0, r1, mat)
    m.cap(rings[-1], mat, up=True)
    m.cap(rings[0], mat, up=False)


def bed_plate(m, mat):
    """Flat closed plate under the block, out to the inner edge of the frame's ink ring."""
    hx, hy, c = B.HX, B.HY, BED_CH
    pts = [(-hx + c, -hy), (hx - c, -hy), (hx, -hy + c), (hx, hy - c),
           (hx - c, hy), (-hx + c, hy), (-hx, hy - c), (-hx, -hy + c)]
    r0 = m.ringv(pts, 0.0)
    r1 = m.ringv(pts, BED_Z)
    m.bridge(r0, r1, mat)
    m.cap(r0, mat, up=False)
    m.cap(r1, mat, up=True)


def build(sprite, coll):
    B.TS = B.ring_params()
    pal = lambda i, tag, **kw: common.palette_material(sprite, i, f"{NAME}_{tag}", **kw)  # noqa: E731
    mats = [pal(SHELL_PAL, "enamel", metallic=0.28, roughness=0.3),
            pal(FOOT_PAL, "steel", metallic=0.35, roughness=0.55),
            pal(MARK_PAL, "mark", metallic=0.32, roughness=0.24),
            pal(BED_PAL, "bed", metallic=0.1, roughness=0.75)]
    SHELL, DARK, MARK, BED = 0, 1, 2, 3

    m = B.Mesh()
    B.build_shell(m, SHELL)
    B.build_foot(m, DARK)
    bmesh.ops.recalc_face_normals(m.bm, faces=m.bm.faces)
    S = Matrix.Scale(B.PX, 4)
    bmesh.ops.transform(m.bm, matrix=S, verts=m.bm.verts)
    me = bpy.data.meshes.new(NAME)
    m.bm.to_mesh(me)
    m.bm.free()
    for mt in mats:
        me.materials.append(mt)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    # the family's lifting sockets (the lib scales its module globals to metres around the cut)
    B.SOCKETS = [tuple(v * B.PX for v in s) for s in B.SOCKETS]
    hx, hy = B.HX, B.HY
    B.HX, B.HY = hx * B.PX, hy * B.PX
    B.cut_sockets(obj, coll, DARK)
    B.HX, B.HY = hx, hy

    # The bed plate is its own closed part, added after the socket boolean: built into the block's
    # bmesh, it overlapped the family's dark foot (both capped at z 0) and the exact boolean dropped
    # the foot, so the block floated 0.66 px over the plate. Joined (T.join) after the cut, the foot
    # stands on the plate as on newshm-15/17/53, and the outline shell's voxel remesh fuses the two.
    p = B.Mesh()
    bed_plate(p, BED)
    bmesh.ops.recalc_face_normals(p.bm, faces=p.bm.faces)
    bmesh.ops.transform(p.bm, matrix=S, verts=p.bm.verts)
    me3 = bpy.data.meshes.new(NAME + "_bed")
    p.bm.to_mesh(me3)
    p.bm.free()
    for mt in mats:
        me3.materials.append(mt)
    o3 = bpy.data.objects.new(NAME + "_bed", me3)
    coll.objects.link(o3)

    e = B.Mesh()
    B.bolts(e, SHELL)
    round_stroke(e, HOOK, STROKE_W, RAISE, MARK)
    dome(e, DOT[0], DOT[1], DOT[2], DOT[3], MARK)
    bmesh.ops.recalc_face_normals(e.bm, faces=e.bm.faces)
    bmesh.ops.transform(e.bm, matrix=S, verts=e.bm.verts)
    me2 = bpy.data.meshes.new(NAME + "_emblem")
    e.bm.to_mesh(me2)
    e.bm.free()
    for mt in mats:
        me2.materials.append(mt)
    o2 = bpy.data.objects.new(NAME + "_emblem", me2)
    coll.objects.link(o2)
    for o in (obj, o2, o3):
        o.data.shade_smooth()
        o.data.set_sharp_from_angle(angle=math.radians(38))
    return [obj, o2, o3], mats


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    parts, mats = build(sprite, coll)
    obj = T.join(parts, NAME)
    closed = obj.copy()
    closed.data = obj.data.copy()
    closed.modifiers.clear()
    coll.objects.link(closed)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        tint, textured = T.TINT, T.TEXTURED
        T.TINT = (1.0, 1.0, 1.0)
        T.TEXTURED = tuple(range(len(mats)))
        try:
            T.bake_maps(obj, tempfile.mkdtemp(prefix=f"{NAME}_A_bake_"), size=1024, samples=96)
        finally:
            T.TINT, T.TEXTURED = tint, textured
        for img in bpy.data.images:
            if img.name.startswith("talon_"):
                img.name = img.name.replace("talon_", f"{NAME}_")
        fmt = "WEBP"
    shell = common.outline_shell(closed, coll, voxel=0.014, faces=1500, smooth=8)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    common.export_sprite_model(WT, [obj, shell], f"enemies/{NAME}", sprite["sprites"], image_format=fmt)
    print(f"{NAME}: built")


if __name__ == "__main__":
    main()
