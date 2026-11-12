"""newshf-238: the bottom-right nose corner of a red armoured hull with a grey ball turret
half sunk in a dark socket (newshf.shp frame 238; partner newshf-230 is its mirror on the left).

Read from the sprite (24 x 28 px, rows 0-21 drawn):
  - socket: cols 1-7, rows 1-13, open to the top and to the left tile edge (230 holds the other half);
    its walls and floor are the sprite's ink/dark (pal 1);
  - ball: a grey sphere in the socket, centre about col 2, row 7 (pal 5, satin metal; the bright
    pixels at its upper left are sheen);
  - rim: an L-shaped raised collar round the socket, cols 8-11 down the right of it and rows 13-14
    under it (pal 69; its lit lip pixels 71-75 are lighting);
  - field: the plate under the rim, sloping off to the rounded outer edge (pal 67);
  - plate B between the panel lines at cols 12 and 16 (pal 68), plate C cols 17-20 (pal 65), and a
    low ledge at the top right, cols 21-23 (pal 68);
  - outer edge: the diagonal and bottom rows, rounded down toward the belly (the darkening rows).
Top-view edge at the INNER edge of the ink border (D74). Flat closed belly at z = 0.

What it is (D120/D122 identify the object first; DECISIONS D167): the red FLYING gun fortress at the end of
SAVARA, in three sections that separate, not a ground building. In 1.8 and 1.12 SAVARA it holds at
the top of the screen over open sea; event 20 then pushes the two wing
sections (assembly-newshf-191 with newshf-230 on the left, assembly-newshf-199 with newshf-238 on the
right) out sideways at +-6 px/tick and back, while the centre gun module (assembly-newshf-195) roams
on its own; in 1.17 SAVARA V the same pieces spawn on the sky layer. The model already reads as that
from the game camera: armoured hull plating, barrels and turrets over a closed flat underside, with no
foundations, legs or walls down to a ground. So it was not rebuilt, and its pieces and pivots are
unchanged so the split still works.

Seen in episodes 1-4 (levels 1.10, 1.29, 1.38, 2.2, 3.21, 4.16). One frame (238); hit flash and
damage are runtime effects (D86). Outline shell per D51.

Run: blender --background --python assets/blender/enemies/newshf-238.py [-- --preview out.png] [--renders <dir>]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402  (pchip)

NAME = "newshf-238"
MODEL = f"enemies/{NAME}"
WT = common.repo_root(__file__)
W, H = 24, 28


# --- sprite px (x right, y down the rows, z up, all in px) to Blender units -----------------------

def X(x):
    return (x - W / 2) / 12


def Y(y):
    return (H / 2 - y) / 12


def Z(z):
    return z / 12


# --- the outer edge: x of the diagonal at row edge y (fitted to the inner mask's last pixels) ------

DIAG_Y = [2.6, 3.6, 5.5, 7.0, 8.5, 10.5, 12.5, 14.5, 16.5, 18.5, 19.5, 20.5, 21.5, 22.0]
DIAG_X = [24.0, 23.25, 22.6, 21.9, 21.0, 19.0, 17.0, 15.0, 13.0, 11.0, 9.7, 8.1, 6.2, 4.6]
_diag = T.pchip(DIAG_Y, DIAG_X)


def diag_x(y):
    return 24.0 if y <= DIAG_Y[0] else _diag(min(y, DIAG_Y[-1]))


def diag_y(x):
    """Row edge where the diagonal reaches column edge x (bisection; diag_x falls with y)."""
    lo, hi = DIAG_Y[0], DIAG_Y[-1]
    for _ in range(60):
        mid = (lo + hi) / 2
        if diag_x(mid) > x:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def diag_run(x0, x1, step=0.5):
    """Points along the diagonal from column x0 down to column x1 (x0 > x1), as (x, y)."""
    y0, y1 = diag_y(x0), diag_y(x1)
    n = max(2, int(math.ceil(abs(y1 - y0) / step)))
    return [(diag_x(y0 + (y1 - y0) * i / n), y0 + (y1 - y0) * i / n) for i in range(n + 1)]


# --- polygon helpers (Blender XY) ----------------------------------------------------------------

def signed_area(poly):
    n = len(poly)
    return sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n)) / 2


def offset_polygon(poly, dists):
    """Move each edge of a CCW polygon inward by its own distance; vertices at the offset edges' meets."""
    n = len(poly)
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln, dx / ln
        d = dists[i]
        lines.append(((x0 + nx * d, y0 + ny * d), (dx, dy)))
    out = []
    for i in range(n):
        (p, u), (q, v) = lines[i - 1], lines[i]
        den = u[0] * v[1] - u[1] * v[0]
        lu, lv = math.hypot(*u) or 1.0, math.hypot(*v) or 1.0
        if abs(den) / (lu * lv) < 0.2:  # nearly parallel: average the two offset points
            d0, d1 = dists[i - 1], dists[i]
            ox, oy = poly[i]
            nu = (-u[1] / lu * d0, u[0] / lu * d0)
            nv = (-v[1] / lv * d1, v[0] / lv * d1)
            out.append((ox + (nu[0] + nv[0]) / 2, oy + (nu[1] + nv[1]) / 2))
            continue
        t = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / den
        out.append((p[0] + u[0] * t, p[1] + u[1] * t))
    # An edge shorter than the insets round it turns over: collapse it to its midpoint (the
    # vertex count stays, so the rings still loft).
    for _ in range(4):
        flipped = False
        for i in range(n):
            j = (i + 1) % n
            ox, oy = poly[j][0] - poly[i][0], poly[j][1] - poly[i][1]
            nx, ny = out[j][0] - out[i][0], out[j][1] - out[i][1]
            if ox * nx + oy * ny < -1e-12:
                mid = ((out[i][0] + out[j][0]) / 2, (out[i][1] + out[j][1]) / 2)
                out[i] = out[j] = mid
                flipped = True
        if not flipped:
            break
    return out


def plate(bm, pts_px, edges, z_top, h_round, top_mat, steps=6, tilt=None):
    """A plate standing on the ground: straight walls, then a rounded shoulder up to a flat top.

    pts_px: outline in sprite px (any winding). edges[i] = (inset_px, wall_mat) for the edge from
    point i to i+1: how far in that edge's shoulder reaches (0 = a straight wall to the top, as at a
    tile edge the hull continues past). The shoulder is a quarter round (vertical at the wall,
    level at the top); every edge's shoulder rises over the same h_round. tilt(x_px) -> dz_px
    lowers the plate's top toward one side (its walls stay put)."""
    poly = [(X(x), Y(y)) for x, y in pts_px]
    if signed_area(poly) < 0:
        poly = poly[::-1]
        n = len(edges)
        edges = [edges[(n - 2 - j) % n] for j in range(n)]
    n = len(poly)
    z_wall = z_top - h_round
    rings = []  # (ring points, z, kind)
    rings.append((poly, 0.0, "wall"))
    rings.append((poly, max(0.0, z_wall - 0.25), "wall"))
    rings.append((poly, z_wall, "wall"))
    for k in range(1, steps + 1):
        th = math.pi / 2 * k / steps
        d = [e[0] / 12 * (1 - math.cos(th)) for e in edges]
        rings.append((offset_polygon(poly, d), z_wall + h_round * math.sin(th), "shoulder"))
    # a narrow level band so the top's normals stay level
    last = [e[0] / 12 + 0.25 / 12 for e in edges]
    rings.append((offset_polygon(poly, last), z_top, "top"))
    verts = []
    for pts, z, _ in rings:
        row = []
        for (x, y) in pts:
            zz = z
            if tilt and z > z_wall + 1e-6:
                zz = z - tilt(x * 12 + W / 2, H / 2 - y * 12) * ((z - z_wall) / h_round)
            row.append(bm.verts.new((x, y, Z(zz))))
        verts.append(row)
    bm.faces.new(list(reversed(verts[0]))).material_index = edges[0][1]
    bm.faces.new(verts[-1]).material_index = top_mat
    for r in range(len(rings) - 1):
        kind = rings[r + 1][2]
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((verts[r][i], verts[r][j], verts[r + 1][j], verts[r + 1][i]))
            f.material_index = edges[i][1] if kind == "wall" else top_mat


def sphere(bm, centre_px, r_px, mat, seg=28, rings=14):
    cx, cy, cz = centre_px
    start = len(bm.verts)
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=Z(r_px))
    for v in res["verts"]:
        v.co += Vector((X(cx), Y(cy), Z(cz)))
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.material_index = mat
    return start


def clip_all(bm, co, no):
    clip(bm, co, no, bm.verts[:] + bm.edges[:] + bm.faces[:])


def merge(dst, src):
    me = bpy.data.meshes.new("tmp")
    src.to_mesh(me)
    src.free()
    dst.from_mesh(me)
    bpy.data.meshes.remove(me)


def geom_since(bm, vstart):
    bm.verts.ensure_lookup_table()
    vs = set(bm.verts[vstart:])
    edges = [e for e in bm.edges if all(v in vs for v in e.verts)]
    faces = [f for f in bm.faces if all(v in vs for v in f.verts)]
    return list(vs) + edges + faces


def clip(bm, co, no, geom):
    cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
    edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    if edges:
        bmesh.ops.holes_fill(bm, edges=edges, sides=0)


# --- the model -----------------------------------------------------------------------------------

L = 0.6      # left tile edge (col 0 is the seam ink with newshf-230)
TOP = 0.6    # top edge where row 0 is ink (socket, plate C)
SEAM_A, SEAM_B = 12.25, 12.75   # the panel line at col 12
SEAM_C, SEAM_D = 16.25, 16.75   # the panel line at col 16
LEDGE_X = 21.0
RIM_Y0, RIM_Y1 = 13.4, 15.0     # the rim's band under the socket
SOCK_R = 7.6                    # the socket's right wall
BOTTOM = 22.0
BALL_C = (4.1, 7.2)             # the ball's centre (sprite px), radius and centre height
BALL_R = 3.6
BALL_ZC = 1.8

# heights in px (12 px = 1 unit)
Z_BASE = 1.4
Z_RIM = 3.9
Z_B = 3.6
Z_FIELD = 3.3
Z_C = 3.3
Z_LEDGE = 1.9


def build():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    pal = lambda i, m, r: common.palette_material(sprite, i, NAME, metallic=m, roughness=r)  # noqa: E731
    mats = [
        pal(1, 0.2, 0.8),     # 0 socket walls, floor, panel-line floors
        pal(69, 0.4, 0.42),   # 1 rim round the socket
        pal(67, 0.4, 0.45),   # 2 field under the rim
        pal(68, 0.4, 0.45),   # 3 plate B and the ledge
        pal(65, 0.4, 0.48),   # 4 plate C
        pal(5, 0.65, 0.32),   # 5 ball (satin)
        pal(3, 0.6, 0.4),     # 6 bearing collar (the dark grey round the ball's foot)
    ]
    SOCK, RIM, FIELD, PB, PC, BALL, COLLAR = range(7)
    bm = bmesh.new()

    # Base slab: fills the panel lines and floors the socket; kept a hair inside the plates' walls.
    base = [(L, 1.0), (24.0 - 0.3, 1.0)] + [(x - 0.3, min(y, BOTTOM - 0.3)) for x, y in diag_run(23.99, DIAG_X[-1] + 0.4)] + [(L, BOTTOM - 0.3)]
    plate(bm, base, [(0, SOCK)] * len(base), Z_BASE, 0.3, SOCK, steps=1)

    # Rim: L-shaped collar, right of and under the socket, its socket side a rounded lip.
    arc = [(SOCK_R - 2.2 + 2.2 * math.cos(a), RIM_Y0 - 2.2 + 2.2 * math.sin(a))
           for a in [math.radians(t) for t in (0, 22.5, 45, 67.5, 90)]]
    rim = [(SOCK_R, 0.0), (SEAM_A, 0.0), (SEAM_A, RIM_Y1), (L, RIM_Y1), (L, RIM_Y0)] + arc[::-1]
    # arc runs from (SOCK_R-2.2, RIM_Y0) up to (SOCK_R, RIM_Y0-2.2), then back to the first point
    rim_edges = [(0, RIM), (0.5, SOCK), (0.6, RIM), (0.6, RIM)] + [(0.55, SOCK)] * (len(arc)) + [(0.55, SOCK)]
    rim_edges = rim_edges[:len(rim)]
    plate(bm, rim, rim_edges, Z_RIM, 1.3, RIM)

    # Plate A: the field round the socket, under the rim, out to the rounded edge.
    run = diag_run(SEAM_A, DIAG_X[-1])
    pa = [(SOCK_R, 0.0), (SEAM_A, 0.0)] + run + [(L, BOTTOM), (L, RIM_Y0)] + arc[::-1]
    ae = [(0, FIELD), (0.5, SOCK)] + [(3.0, FIELD)] * (len(run) - 1) + [(2.6, FIELD), (1.4, FIELD)] + [(1.5, SOCK)] * (len(arc) + 1)
    # its top falls gently toward the rounded south-east edge (the sprite's rows 15-21 darken)
    plate(bm, pa, ae, Z_FIELD, 2.1, FIELD, tilt=lambda x, y: 0.09 * max(0.0, y - RIM_Y1))

    # Plate B between the panel lines.
    run = diag_run(SEAM_C, SEAM_B)
    pb = [(SEAM_B, 0.0), (SEAM_C, 0.0)] + run
    be = [(0, PB), (0.5, SOCK)] + [(2.6, PB)] * (len(run) - 1) + [(0.6, SOCK)]
    plate(bm, pb, be, Z_B, 1.8, PB)

    # Plate C, its top falling off toward the ledge.
    run = diag_run(LEDGE_X, SEAM_D)
    pc = [(SEAM_D, TOP), (LEDGE_X, TOP)] + run
    ce = [(0, PC), (1.1, PC)] + [(2.6, PC)] * (len(run) - 1) + [(0.5, SOCK)]
    plate(bm, pc, ce, Z_C, 1.8, PC, tilt=lambda x, y: 0.16 * max(0.0, x - SEAM_D))

    # The low ledge at the top right.
    run = diag_run(23.99, LEDGE_X - 1.0)
    le = [(LEDGE_X - 1.0, 0.0), (24.0, 0.0)] + run
    lee = [(0, PB), (0.8, PB)] + [(0.9, PB)] * (len(run) - 1) + [(0, PB)]
    plate(bm, le, lee, Z_LEDGE, 0.8, PB)

    # Bearing collar the ball turns in: a low chamfered ring on the socket floor.
    part = bmesh.new()
    prof = ((4.05, Z_BASE - 0.1), (4.05, Z_BASE + 0.4), (3.85, Z_BASE + 0.62),
            (3.6, Z_BASE + 0.62), (3.45, Z_BASE + 0.4), (3.45, Z_BASE - 0.1))
    seg = 32
    grid = [[part.verts.new((X(BALL_C[0] + r * math.cos(2 * math.pi * i / seg)), Y(BALL_C[1] + r * math.sin(2 * math.pi * i / seg)),
                             Z(z))) for i in range(seg)] for r, z in prof]
    for a in range(len(grid)):
        b = (a + 1) % len(grid)
        for i in range(seg):
            j = (i + 1) % seg
            part.faces.new((grid[a][i], grid[a][j], grid[b][j], grid[b][i])).material_index = COLLAR
    clip_all(part, (X(L), 0, 0), (-1, 0, 0))
    merge(bm, part)

    # Ball: a whole sphere sitting in the socket (the hull's west side is open water in game, so
    # it is not cut there); only the part under the floor is dropped.
    part = bmesh.new()
    sphere(part, (BALL_C[0], BALL_C[1], BALL_ZC), BALL_R, BALL)
    clip_all(part, (0, 0, Z(Z_BASE - 0.2)), (0, 0, -1))
    merge(bm, part)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(35))
    return obj, coll, sprite


# --- renders -------------------------------------------------------------------------------------

def renders(objs, out_dir, shell=None):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for o in scene.objects:
        o.hide_render = o not in objs
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    scene.render.film_transparent = True
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")

    def cam(name, loc, look, ortho=None, lens=60, up="Y"):
        data = bpy.data.cameras.new(name)
        if ortho:
            data.type = "ORTHO"
            data.ortho_scale = ortho
        else:
            data.lens = lens
        c = bpy.data.objects.new(name, data)
        scene.collection.objects.link(c)
        c.location = loc
        c.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", up).to_euler()
        return c

    def shot(c, path, rx, ry, flat=False):
        scene.camera = c
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        scene.render.resolution_percentage = 100
        if flat:
            sh.light = "FLAT"
            sh.color_type = "SINGLE"
            sh.single_color = (1, 1, 1)
            sh.show_cavity = False
            scene.display.shading.show_object_outline = False
        else:
            sh.light = "STUDIO"
            sh.color_type = "MATERIAL"
            sh.show_cavity = True
            sh.cavity_type = "BOTH"
            sh.show_specular_highlight = True
            scene.display.shading.show_object_outline = False
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    k = 10
    top = cam("top", (0, 0, 10), (0, 0, 0), ortho=H / 12)
    top.rotation_euler = (0, 0, 0)
    shot(top, out_dir / "top_mask.png", W * k, H * k, flat=True)
    shot(top, out_dir / "top.png", W * 20, H * 20)
    # tilted game camera: from the bottom of the screen, about 25 degrees off vertical
    d = 6.0
    a = math.radians(25)
    shot(cam("game", (0, -d * math.sin(a), d * math.cos(a)), (0, 0, 0.1), lens=55), out_dir / "game.png", 600, 600)
    a = math.radians(45)
    shot(cam("game45", (0, -d * math.sin(a), d * math.cos(a)), (0, 0, 0.1), lens=55), out_dir / "game45.png", 600, 600)
    shot(cam("q34", (4.0, -4.0, 3.2), (0, -0.1, 0.1), lens=55), out_dir / "q34.png", 600, 600)
    shot(cam("q34b", (-3.2, -4.6, 3.0), (0, -0.1, 0.1), lens=55), out_dir / "q34b.png", 600, 600)
    for nm, loc, rot in (("side", (10, 0, 0.3), (90, 0, 90)), ("front", (0, -10, 0.3), (90, 0, 0)),
                         ("rear", (0, 10, 0.3), (90, 0, 180))):
        c = cam(nm, loc, (0, 0, 0.3), ortho=2.6)
        c.rotation_euler = tuple(math.radians(v) for v in rot)
        shot(c, out_dir / f"{nm}.png", 600, 300)
    shot(cam("under", (2.5, -3.0, -3.0), (0, 0, 0), lens=55), out_dir / "under.png", 400, 400)


def main():
    obj, coll, sprite = build()
    shell = common.outline_shell(obj, coll)
    print("triangles", sum(len(p.vertices) - 2 for p in obj.data.polygons))
    common.export_sprite_model(WT, [obj, shell], MODEL, sprite["sprites"])
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--preview" in argv:
        fr = sprite["frames"][0]
        ref = Path(WT) / "reference" / "models" / NAME / fr["image"]
        common.render_preview([obj, shell], argv[argv.index("--preview") + 1], ref, size=fr["size"])
    if "--renders" in argv:
        renders([obj], argv[argv.index("--renders") + 1])


if __name__ == "__main__":
    main()
