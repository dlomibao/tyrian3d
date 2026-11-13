"""newsh-caret-152 design A: the grey dart of newsh-caret-171 lying sideways, nose to the LEFT
(newsh^.shp 152, 12x14, palette 5, one frame). A projectile: launched by newsh-caret-171's carrier
(e4:42) and assembly-newshv-14 (e4:323), flying left (x -11..-2) in UNDERDELI and LAVA RUN.

What the sprite shows: the 171 drawing turned a quarter turn clockwise. Rod rows 4-6 (inner mask),
cols 0-10: the blunt nose at col 0 (the sprite draws it to the picture's edge, no ink there), the
band at col 1 (116-120-116: a round lamp ring, its dark ends shading), the back end 8 at col 10, ink
at col 11. Tail fins cols 8-10 rows 1-3 / 7-9 (straight trailing edge flush with the back, leading
edge swept in), mid fins cols 3-6 (a hexagon each side). Colours as 171: rod 10 with a 13 sheen
line, fins 14 with 11 edges, back 8.

Design: the exact 171 build (same profile, fins, flap, blades, panels, materials) so the pair and
171 read as one object; the finished mesh is rotated -90 degrees about Z and moved -1 px in X and
+1 px in Y (the sprite's rod sits at row edge 5.5, nose on col edge 0). The band does not cycle
here (only frame 152 exists): lamp 120, rims 116.

newsh-caret-190 (nose right) is the mirror: its script loads this module and calls build_model("newsh-caret-190").
Run: blender --background --python assets/blender/enemies/newsh-caret-152.py [-- --no-bake] [--out x.glb]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
WT = HERE.parents[2]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part, hull  # noqa: E402

NAME = "newsh-caret-152"   # rebound by build_model for the mirror
MODEL = f"enemies/{NAME}"
FLIP = False
BAKE_DIR = Path(__import__("tempfile").gettempdir()) / "newsh-caret-152-bake"
PX = 1 / 12

# Coordinates in sprite px: x across from the rod's axis (column edge 5.5, +x = screen right),
# y = row edge (0 top / the dart's back, 12 the nose), z up from the ground.
XA = 5.5 - 6.0          # the axis' offset from the sprite centre (column edge 6)
YC = 7.0                # the sprite centre row edge
R = 1.46                # rod radius (the rod's inner mask is 3 px wide)
ZA = R                  # the axis height (the rod lies on the ground)
SEG = 20                # segments round the rod

# Material slots.
ROD, BACK, FIN, BLADE, DEEP, LAMP, RIM, EDGE = range(8)
PAL_OF = {ROD: 10, BACK: 8, FIN: 14, BLADE: 13, DEEP: 32, LAMP: 120, RIM: 116, EDGE: 11}
LAMP_FRAMES = None   # one frame (152): the band stays 120
RIM_FRAMES = None
METAL = 0.3
TINT = (0.95, 0.97, 1.0)


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
    (1.80, R, DEEP),      # collar | seam groove
    (1.80, R - 0.17, DEEP),
    (1.93, R - 0.17, DEEP),
    (1.93, R, ROD),
    (4.40, R, DEEP),      # seam groove between the fin sets
    (4.40, R - 0.14, DEEP),
    (4.52, R - 0.14, DEEP),
    (4.52, R, ROD),
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


def arc_plate(P, y0, y1, a0, a1, d, c, mat, depth=0.12, n=4):
    """A curved access panel on the rod from y0 to y1 and angle a0 to a1 (degrees, 90 = top):
    standing d proud with 45-degree chamfered edges c wide and a skirt sunk `depth` into the rod."""
    def P3(a, y, r):
        t = math.radians(a)
        return (r * math.cos(t), y, ZA + r * math.sin(t))
    ca = math.degrees(c / R)
    angs = [a0, a0 + ca] + [a0 + ca + (a1 - a0 - 2 * ca) * i / n for i in range(1, n)] + [a1 - ca, a1]
    ys = [y0, y0 + c, y1 - c, y1]
    grid = []
    for yi, y in enumerate(ys):
        row = []
        for ai, a in enumerate(angs):
            edge = yi in (0, 3) or ai in (0, len(angs) - 1)
            row.append(P.v(P3(a, y, R + (d - c if edge else d))))
        grid.append(row)
    away = (0.0, (y0 + y1) / 2, ZA)
    for yi in range(3):
        for ai in range(len(angs) - 1):
            P.f((grid[yi][ai], grid[yi][ai + 1], grid[yi + 1][ai + 1], grid[yi + 1][ai]), mat, away=away)
    low = [[P.v(P3(a, y, R - depth)) for a in angs] for y in ys]
    for ai in range(len(angs) - 1):   # skirts front and back
        P.f((grid[0][ai], grid[0][ai + 1], low[0][ai + 1], low[0][ai]), mat, out=(0, -1, 0))
        P.f((grid[3][ai], grid[3][ai + 1], low[3][ai + 1], low[3][ai]), mat, out=(0, 1, 0))
    for yi in range(3):               # skirts at the two long edges
        for ai, sgn in ((0, -1), (len(angs) - 1, 1)):
            t = math.radians(angs[ai])
            out = (-math.sin(t) * sgn, 0, math.cos(t) * sgn)
            P.f((grid[yi][ai], grid[yi + 1][ai], low[yi + 1][ai], low[yi][ai]), mat, out=out)


def build_panels(P):
    """Access panels on the rod's upper flanks, either side of the blades (the game camera sees
    them), and a belt panel ring at the collar."""
    for s in (1, -1):
        for y0, y1 in ((2.12, 4.22), (4.72, 9.42)):
            a0, a1 = (22, 74) if s > 0 else (106, 158)
            arc_plate(P, y0, y1, a0, a1, 0.07, 0.05, ROD)
        # small bolt heads at the panel corners
        for y in (2.32, 4.02, 4.92, 9.22):
            for a in ((30, 66) if s > 0 else (114, 150)):
                t = math.radians(a)
                c = Vector((math.cos(t) * (R + 0.07), y, ZA + math.sin(t) * (R + 0.07)))
                nrm = Vector((math.cos(t), 0, math.sin(t)))
                u = Vector((0, 1, 0))
                v = nrm.cross(u)
                pts = []
                for k in range(6):
                    q = 2 * math.pi * k / 6
                    for h, rr in ((-0.05, 0.11), (0.05, 0.11), (0.09, 0.06)):
                        pts.append(tuple(c + nrm * h + u * (rr * math.cos(q)) + v * (rr * math.sin(q))))
                hull(P, pts, EDGE)


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
    m = Matrix(((PX, 0, 0, XA * PX), (0, -PX, 0, YC * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    # 171 (nose down the screen) -> 152 (nose left): rotate -90 deg about Z, shift (-1, +1) px.
    rot = Matrix.Translation((-PX, PX, 0)) @ Matrix.Rotation(-math.pi / 2, 4, 'Z')
    if FLIP:   # 190: the exact mirror of 152 across the sprite's centre column
        rot = Matrix.Scale(-1, 4, Vector((1, 0, 0))) @ rot
    bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
    if not FLIP:
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
    panels = Part("dart_panels", smooth_angle=35)
    build_panels(panels)
    return [finish(p, mats, coll) for p in (body, fins, blades, panels)]


def bake_maps(obj, out_dir, size=512, samples=64):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = TINT, TEXTURED
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", "dart152")


def build_model(name=None, argv=None):
    global NAME, MODEL, FLIP, BAKE_DIR
    if name:
        NAME, MODEL, FLIP = name, f"enemies/{name}", name.endswith("190")
    argv = sys.argv[sys.argv.index("--") + 1:] if argv is None and "--" in sys.argv else (argv or [])
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    obj = T.join(build(coll, sprite), NAME)
    # The outline shell from the whole model before hidden faces are culled (sealed parts).
    shell = common.outline_shell(obj, coll, voxel=0.007, faces=1400, smooth=8, inside=0.004)
    shell.name = shell.data.name = f"{NAME}_outline"
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        BAKE_DIR = BAKE_DIR.with_name(f"{NAME}-bake")
        BAKE_DIR.mkdir(parents=True, exist_ok=True)
        shell.hide_render = True   # it must not occlude the model in the AO bake
        bake_maps(obj, BAKE_DIR)
        shell.hide_render = False
        fmt = "WEBP"
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
        common.export_glb([obj, shell], out, image_format=fmt)
    else:
        common.export_sprite_model(WT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)


def main():
    build_model()


if __name__ == "__main__":
    main()
