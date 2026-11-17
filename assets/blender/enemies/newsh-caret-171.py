"""newsh-caret-171: the grey dart lying on the ground (newsh^.shp 171, newshd.shp 171/190/209),
hard-surface (D50-D53, D65), its top view on the inner edge of the sprite's ink border (D74).

What the sprite shows (reference/models/newsh-caret-171, 12x14, palette 5, four frames that differ
only in the band's colour):
- Plan (inner mask): a rod 3 px wide (cols 4-6) from row 1 to row 11, its blunt nose against the
  ink at row 12 (nose down the screen); a rear set of swept fins (rows 1-2 to cols 2-8, row 3 to
  cols 3-7: a straight trailing edge flush with the rod's back end, the leading edge sweeping in to
  the rod at row 4) and a mid set (rows 6-7 to cols 2-8, rows 5 and 8 to cols 3-7: a hexagon, both
  edges tapered).
- Colours: the rod 10 with a 13 centre line (a lit round rod: the line is sheen, not a part); the
  rod's back end 8 (row 1); the fins 14 with 11 on their tips and edges (trimmed median 14); the
  band at row 10 116-120-116 on frame 171, 118-122-118 on 190, 122-126-122 on 209: a light ring
  whose dark ends are the round band's shading, so the lamp takes the centre index and cycles it
  with the frame (palette_material frames=, D17), its two thin retaining rims the darker one.

Design: a small air-dropped dart (a sensor/mine dart) lying flat on its fins, the rod on the
ground. One lathed body: a machined nozzle collar at the back (a recessed bore), a seam groove, the
round body with a shallow seam between the fin sets (the rod is a clean faired surface: the
access panels, bolts and black seam grooves of the first build read as dark stripes in game and
are gone, 2026-11-17), the glowing band set between two raised rims,
a closed, blunt rounded nose. Horizontal fins as chamfered tapered plates at the rod's
axis height: the tail fins with a separate trailing flap (a real hinge gap), the mid fins plain,
both with chamfered root fairings. Two upright blades on top (a cruciform set seen from above as
the sprite's bright centre line): a swept tail blade and a lower mid blade. Underside: the rod and
fins close; nothing modelled there.

Run: Blender --background --factory-startup --python assets/blender/enemies/newsh-caret-171.py [-- --no-bake]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part, hull  # noqa: E402

NAME = "newsh-caret-171"
MODEL = f"enemies/{NAME}"
BAKE_DIR = Path(__import__("tempfile").gettempdir()) / "newsh-caret-171-bake"
PX = 1 / 12

# Coordinates in sprite px: x across from the rod's axis (column edge 5.5, +x = screen right),
# y = row edge (0 top / the dart's back, 12 the nose), z up from the ground.
XA = 5.5 - 6.0          # the axis' offset from the sprite centre (column edge 6)
YC = 7.0                # the sprite centre row edge
R = 1.46                # rod radius (the rod's inner mask is 3 px wide)
ZA = R                  # the axis height (the rod lies on the ground)
SEG = 20                # segments round the rod
# The whole dart is built round, then pressed to this share of its height: an oval rod whose broad
# top faces the light reads as the sprite's light rod (10 with a 13 sheen line) from the game
# camera, where a round one turned its flanks away into near-black stripes (2026-11-17 walkthrough).
SQUASH = 0.62

# Material slots.
ROD, BACK, FIN, BLADE, DEEP, LAMP, RIM, EDGE = range(8)
# The rod takes 11, a step above the sprite's 10: the sprite's rod is 10 flanks round a 13 sheen
# line, and a rod of 10 lit by the game rendered charcoal flanks beside the white fins (D201; the
# 2026-11-17 walkthrough: "thin dark grey with white edges"); 13 washed it into the fins.
PAL_OF = {ROD: 11, BACK: 8, FIN: 14, BLADE: 13, DEEP: 32, LAMP: 120, RIM: 116, EDGE: 11}
LAMP_FRAMES = {190: 122, 209: 126}   # the band's centre pixel per frame (120 on both 171s)
RIM_FRAMES = {190: 118, 209: 122}    # its dark ends
# Low metallic: the dart is the sprite's light greys (rod 10 with a 13 sheen line, fins 14), and
# mid-grey steel at more metallic renders charcoal under the game's light (D201).
METAL = 0.12
TINT = (0.95, 0.97, 1.0)
AO_KEEP = 0.5


def materials(sprite):
    pal = lambda slot, metallic, rough, **kw: common.palette_material(  # noqa: E731
        sprite, PAL_OF[slot], f"{NAME}-{['rod', 'back', 'fin', 'blade', 'deep', 'lamp', 'rim', 'edge'][slot]}",
        metallic=metallic * METAL, roughness=rough, **kw)
    return [
        pal(ROD, 0.6, 0.38),
        pal(BACK, 0.55, 0.45),
        pal(FIN, 0.55, 0.36),
        pal(BLADE, 0.6, 0.34),
        pal(DEEP, 0.2, 0.8),
        pal(LAMP, 0.0, 0.45, emission_strength=1.0, frames=LAMP_FRAMES),
        pal(RIM, 0.3, 0.45, frames=RIM_FRAMES),
        pal(EDGE, 0.55, 0.4),
    ]


TEXTURED = (ROD, BACK, FIN, BLADE, DEEP, EDGE)


# --- the lathed body ---------------------------------------------------------------------------

# (y, radius, material of the span to the next point) of the body's profile, traversed round the
# outside from the bottom of the nozzle bore (on the axis) to the tip of the closed nose.
PROFILE = [
    (1.62, 0.00, DEEP),   # bore bottom
    (1.62, 0.52, DEEP),
    (1.14, 0.52, BACK),   # bore wall
    (1.14, 0.84, BACK),   # nozzle lip face
    (1.06, 0.96, BACK),   # lip chamfer
    (1.06, 1.16, BACK),   # collar back face
    (1.24, R, BACK),      # collar chamfer
    (1.80, R, ROD),       # collar | a shallow seam (no black groove: at 12 px a dark seam read
    (1.84, R - 0.06, ROD),  # as a stripe across the light rod)
    (1.90, R - 0.06, ROD),
    (1.94, R, ROD),
    (4.40, R, ROD),       # shallow seam between the fin sets
    (4.44, R - 0.05, ROD),
    (4.50, R - 0.05, ROD),
    (4.54, R, ROD),
    (9.62, R, ROD),
    (9.62, 1.36, RIM),    # step down into the band's seat
    (9.70, 1.36, RIM),
    (9.70, 1.53, RIM),    # rear retaining rim
    (9.86, 1.53, RIM),
    (9.92, 1.47, LAMP),   # the lamp ring
    (10.88, 1.47, RIM),
    (10.94, 1.53, RIM),   # front retaining rim
    (11.10, 1.53, RIM),
    (11.10, 1.42, ROD),
    (11.45, 1.40, ROD),   # the nose
    (11.70, 1.28, ROD),
    (11.86, 1.06, ROD),   # a closed, blunt rounded nose (no pit: the dart leads with it)
    (11.95, 0.72, ROD),
    (11.99, 0.36, ROD),
    (12.00, 0.00, ROD),
]


def build_body(P):
    """Lathe PROFILE round the axis; each face faces out along the profile's own normal."""
    rings = []
    for y, r, _ in PROFILE:
        if r < 1e-6:
            rings.append([P.v((0.0, y, ZA))] * SEG)
        else:
            rings.append([P.v((r * math.cos(2 * math.pi * (k + 0.5) / SEG), y,
                                ZA + r * math.sin(2 * math.pi * (k + 0.5) / SEG))) for k in range(SEG)])
    for i in range(len(PROFILE) - 1):
        y0, r0, mat = PROFILE[i]
        y1, r1, _ = PROFILE[i + 1]
        dy, dr = y1 - y0, r1 - r0
        for k in range(SEG):
            j = (k + 1) % SEG
            a = 2 * math.pi * (k + 1) / SEG
            out = (math.cos(a) * dy, -dr, math.sin(a) * dy)
            quad = []
            for v in (rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]):
                if v not in quad:
                    quad.append(v)
            P.f(quad, mat, out=out)


# --- fins ----------------------------------------------------------------------------------------

def inset(poly, d):
    """Polygon (convex, either winding) moved in by d along each vertex's miter."""
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    out = []
    for i in range(n):
        (x0, y0), (x1, y1), (x2, y2) = poly[i - 1], poly[i], poly[(i + 1) % n]
        def nrm(ax, ay, bx, by):
            dx, dy = bx - ax, by - ay
            ln = math.hypot(dx, dy) or 1e-9
            nx, ny = dy / ln, -dx / ln
            if nx * ((ax + bx) / 2 - cx) + ny * ((ay + by) / 2 - cy) > 0:
                nx, ny = -nx, -ny   # point inward
            return nx, ny
        a, b = nrm(x0, y0, x1, y1), nrm(x1, y1, x2, y2)
        sx, sy = a[0] + b[0], a[1] + b[1]
        ln = math.hypot(sx, sy) or 1e-9
        ux, uy = sx / ln, sy / ln
        c = max(0.35, ux * b[0] + uy * b[1])
        out.append((x1 + ux * d / c, y1 + uy * d / c))
    return out


def plate_fin(P, poly, z, t_root, t_tip, x_root, x_tip, ch, mat, mirror=True):
    """A flat fin plate with chamfered edges, its thickness tapering from t_root at x_root to
    t_tip at x_tip; one convex hull per side (mirrored about the axis)."""
    def th(x):
        f = min(1.0, max(0.0, (abs(x) - x_root) / (x_tip - x_root)))
        return t_root + (t_tip - t_root) * f
    sides = (1, -1) if mirror else (1,)
    for s in sides:
        pts = []
        for x, y in poly:
            e = 0.32 * th(x) / 2
            pts += [(s * x, y, z + e), (s * x, y, z - e)]
        for x, y in inset(poly, ch):
            t = th(x) / 2
            pts += [(s * x, y, z + t), (s * x, y, z - t)]
        hull(P, pts, mat)


TAIL = [(0.9, 1.80), (3.46, 1.80), (3.46, 2.92), (0.9, 4.70)]   # main tail fin, root buried
FLAP = [(0.9, 1.06), (3.46, 1.06), (3.46, 1.68), (0.9, 1.68)]   # trailing flap behind a hinge gap
MID = [(0.9, 4.58), (3.46, 6.05), (3.46, 7.95), (0.9, 9.42)]
# Leading-edge caps (the nose-ward edges, where the sprite draws its fins 11): strips along the
# edge a little thicker than the plate, so they stand proud of it.
TAIL_LE = [(3.46, 1.98), (3.46, 2.92), (0.9, 4.70), (0.9, 4.02)]
MID_LE = [(3.46, 6.98), (3.46, 7.95), (0.9, 9.42), (0.9, 8.80)]


def build_fins(P):
    plate_fin(P, TAIL, ZA, 0.62, 0.34, 1.4, 3.46, 0.16, FIN)
    plate_fin(P, FLAP, ZA, 0.46, 0.28, 1.4, 3.46, 0.12, FIN)
    plate_fin(P, MID, ZA, 0.58, 0.32, 1.4, 3.46, 0.16, FIN)
    plate_fin(P, TAIL_LE, ZA, 0.72, 0.42, 1.4, 3.46, 0.1, EDGE)
    plate_fin(P, MID_LE, ZA, 0.68, 0.40, 1.4, 3.46, 0.1, EDGE)
    # Hinge barrels at the flap's front edge: a short round knuckle each side near the root.
    for s in (1, -1):
        for x0, x1 in ((1.55, 2.25),):
            pts = []
            for k in range(8):
                a = 2 * math.pi * k / 8
                for x in (x0, x1):
                    pts.append((s * x, 1.74 + 0.1 * math.cos(a), ZA + 0.16 * math.sin(a)))
            hull(P, pts, BACK)
    # Root fairings: chamfered strips where each fin meets the rod.
    for (y0, y1) in ((1.9, 4.2), (5.1, 8.9)):
        for s in (1, -1):
            pts = []
            for y, h in ((y0, 0.0), (y0 + 0.5, 1.0), (y1 - 0.5, 1.0), (y1, 0.0)):
                xo = 1.30 + 0.38 * h
                hz = 0.12 + 0.14 * h
                pts += [(s * 1.1, y, ZA + hz + 0.05), (s * xo, y, ZA + 0.08), (s * xo, y, ZA - 0.08),
                        (s * 1.1, y, ZA - hz - 0.05)]
            hull(P, pts, ROD)


def blade(P, prof, t, ch, mat):
    """An upright blade in the plane x = 0: prof is (y, z) points (convex), t thick, edges chamfered."""
    pts = []
    for y, z in prof:
        pts += [(0.32 * t / 2, y, z), (-0.32 * t / 2, y, z)]
    for y, z in inset(prof, ch):
        pts += [(t / 2, y, z), (-t / 2, y, z)]
    hull(P, pts, mat)


def build_blades(P):
    top = ZA + R
    blade(P, [(1.14, top - 0.4), (1.14, top + 1.3), (1.85, top + 1.3), (4.25, top - 0.4)], 0.36, 0.1, BLADE)
    blade(P, [(5.0, top - 0.4), (6.2, top + 0.9), (7.7, top + 0.9), (9.1, top - 0.4)], 0.32, 0.09, BLADE)


# --- assembly ------------------------------------------------------------------------------------

def finish(part, mats, coll):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, XA * PX), (0, -PX, 0, YC * PX), (0, 0, PX * SQUASH, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(part.name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(part.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(part.smooth_angle))
    return obj


def build(coll, sprite):
    mats = materials(sprite)
    body = Part("dart_body", smooth_angle=40)
    build_body(body)
    fins = Part("dart_fins", smooth_angle=30)
    build_fins(fins)
    blades = Part("dart_blades", smooth_angle=30)
    build_blades(blades)
    return [finish(p, mats, coll) for p in (body, fins, blades)]


# The outline shell's source: one convex hull per section of the dart (tail fins, mid fins, nose),
# rod and fins together, upright blades left out. The game's ink is an inverted hull pushed out along
# the shell's normals, and in a concave crease that push folds over itself and shows its back faces:
# a shell traced on the model drew a black bar down each fin root (2026-11-17 walkthrough). Each hull
# is convex, so only the notches between the sections (where the sprite has ink) are creases; its
# top view is the model's own but for slivers well under a pixel where a fin edge meets the rod.
SECTIONS = ((0.0, 4.55), (4.55, 9.45), (9.45, 12.5))


def rod_radius(y):
    """The body's outer radius at row edge y (PROFILE past the nozzle bore, interpolated)."""
    outer = [(py, r) for py, r, _ in PROFILE[5:]]
    for (ya, ra), (yb, rb) in zip(outer, outer[1:]):
        if ya <= y <= yb and yb > ya:
            return ra + (rb - ra) * (y - ya) / (yb - ya)
    return outer[0][1] if y < outer[0][0] else 0.0


def shell_source(parts, coll):
    """A closed mesh (the union of the sections' hulls) from the body and fin parts' vertices."""
    bm = bmesh.new()
    for y0, y1 in SECTIONS:
        pts = []
        for obj in parts:
            for v in obj.data.vertices:
                co = obj.matrix_world @ v.co
                y = YC - co.y / PX   # back to the sprite's row edges
                if y0 - 1e-4 <= y <= y1 + 1e-4:
                    pts.append(co.copy())
        # The rod's own ring at each end of the section (its vertices sit only at profile steps).
        for y in (max(y0, 1.06), min(y1, 12.0)):
            r = rod_radius(y)
            for k in range(SEG):
                a = 2 * math.pi * (k + 0.5) / SEG
                pts.append(Vector(((r * math.cos(a) + XA) * PX, -(y - YC) * PX,
                                   (ZA + r * math.sin(a)) * PX * SQUASH)))
        verts = [bm.verts.new(p) for p in pts]
        res = bmesh.ops.convex_hull(bm, input=verts)
        drop = {g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)}
        bmesh.ops.delete(bm, geom=list(drop), context="VERTS")
    me = bpy.data.meshes.new(f"{NAME}_shellsrc")
    bm.to_mesh(me)
    bm.free()
    src = bpy.data.objects.new(f"{NAME}_shellsrc", me)
    coll.objects.link(src)
    return src


def bake_maps(obj, out_dir, size=512, samples=64):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = TINT, TEXTURED
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            fill_background(img)
            img.name = img.name.replace("talon", "dart171")


def fill_background(img):
    """The bake clears to black and leaves it between the UV islands. At the game's size the
    texture is sampled from its small mip levels (and the compressed UVs land a texel off), so
    that black bleeds into the dart as dark streaks and a charcoal cast (the 2026-11-17 walkthrough:
    a thin dark dart where the sprite is solid white). Fill every unbaked texel with the mean of the
    baked ones: the islands' borders and mips then keep the dart's own value."""
    import numpy as np
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(-1, 4)
    # Colour map: baked texels are >= 0.48 x tint; rm map: R is always 1 where baked.
    empty = (px[:, 0] < 0.2) if "rm" not in img.name else (px[:, 0] < 0.5)
    if empty.all() or not empty.any():
        return
    px[empty, :3] = px[~empty, :3].mean(axis=0)
    if "rm" not in img.name:
        # Keep half the occlusion: at 12 px the full AO drew every seam and panel skirt as a black
        # stripe down the rod; the shading of the forms themselves is the game's lighting.
        tint = np.array(TINT, dtype=np.float32)
        px[:, :3] = tint - (tint - px[:, :3]) * AO_KEEP
    px[:, 3] = 1.0
    img.pixels.foreach_set(px.ravel())
    img.update()
    if img.filepath_raw:
        img.save()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    parts = build(coll, sprite)
    # The outline shell from sealed section hulls of the body and fins (SECTIONS), before the
    # parts are joined and their hidden faces culled.
    src = shell_source(parts[:2], coll)
    shell = common.outline_shell(src, coll, voxel=0.007, faces=1400, smooth=8, inside=0.004)
    shell.name = shell.data.name = f"{NAME}_outline"
    src_me = src.data
    bpy.data.objects.remove(src, do_unlink=True)
    bpy.data.meshes.remove(src_me)
    obj = T.join(parts, NAME)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        BAKE_DIR.mkdir(parents=True, exist_ok=True)
        shell.hide_render = True   # it must not occlude the model in the AO bake
        bake_maps(obj, BAKE_DIR)
        shell.hide_render = False
        fmt = "WEBP"
    common.export_sprite_model(WT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
