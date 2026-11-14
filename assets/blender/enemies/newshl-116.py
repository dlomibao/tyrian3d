"""Spiked molten mine (newshl.shp 116, 1 frame).

What it is: a contact mine, red-hot. TIME WAR (4.17) drifts it as indestructible debris and SQUADRON
(4.18) flies it in grids of single craft that fire, so it is a manufactured thing: a spherical
casing of armour panels, heated until it glows, with four horns (the sprite's spikes) in the plane
of the screen, a white-hot core port and a dark fuse socket.

- Ball: a sphere R = BALL_R px round the sprite body's centre (column edge 5.5, row edge 7.5), fitted
  to the inner outline mask (tools/sprite_mask.py) so the game's ink lands on the sprite's ring.
- Casing: a cube-sphere of 54 large armour plates (3 x 3 per cube face, shallow seams so the ball
  reads as one smooth hot sphere at 12 px), turned so the top face's centre plate sits on the core
  port.
- Core port (sprite 127 at column 5, row 6, the ball's centre with heat radiating from it): a
  white-hot dome (127) in a 124 rim, flush or a touch proud of the casing (no recessed wall, so no
  dark band round it), with the casing faces round it graded 124 -> 123 -> 122 so the glow spreads
  into the shell. It sits PORT_DY px south of the top so that the tilted game camera (32 deg,
  view.ts) projects it just north of the ball's visual centre, where the sprite draws it. Fuse
  socket (sprite 1 at column 5, row 9, 3 px below the core): a ring with a dark (1) recess, further
  south for the same reason.
- Colour per casing face: a base heat by angle from an axis tipped north of up (hot north 119-121,
  equator 116-117, dark maroon south crust 114-116) with seeded per-plate jitter, scattered hot
  plates and per-face mottling, and the core glow above; crust plates have hotter seams (lava in the
  cracks). Not the sprite's per-pixel values, which are its top-left lighting (art rule 2). All
  glow surfaces are metallic 1, rough (D126/D173), emission rising with heat; the core is 127.
- Horns: 4 machined horns along +-x, +-y at the equator: a flanged collar and a tapered ogive spike
  (114, dark satin, not glowing). The collars and spike roots glow in the sprite's base colours
  (122 N, 116 S, 118 W, 116 E) so the spikes read through the game's ink.
- Underside: the same closed sphere; no extra detail.

blender --background --python assets/blender/enemies/newshl-116.py [-- --out x.glb]
Exports public/models/enemies/newshl-116.glb and the spriteModels entry; --out writes only that glb.
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newshl-116"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12
W, H = 12, 14

CX, CY = 5.5, 7.5          # ball centre, sprite pixel-edge coords
BALL_R = 4.38              # px
ZS = 0.82                  # height / width: a slightly oblate ball (top features sit nearer the
                           # sprite's places under the tilted game camera)
PORT_DY = -1.2             # core port's top-view offset from the centre, px (south: see above)
SOCKET_DY = -3.2           # fuse socket's
VENT_TILT = math.asin(-PORT_DY / BALL_R)
PANELS = 7                 # plates per cube-face edge (odd: a plate, not a seam, on each face centre);
                           # about 1 sprite px each, so the heat speckles at the sprite's grain
CHAMFER = 0.10             # seam wall width, fraction of a plate
DEPTH = 0.05               # seam depth, px
INTERIOR = 2               # interior segments per plate edge

# Horns: (direction in the top view (+x east, +y north), tip distance from centre px)
# The N tip reaches into the sprite's free ink pixels (rows 0-1, col 5), counted neither way by the IoU.
HORNS = [((0, 1), 6.9), ((0, -1), 6.3), ((1, 0), 6.1), ((-1, 0), 5.7)]
# Short diagonal horns: the sprite's squared corners (inner pixels (2,4), (8,4), (2,10), (8,10) and
# the stepped ring beyond them) are spikes too; with the four main ones the outline is a starburst.
S2 = math.sqrt(0.5)
DIAG_HORNS = [((S2, S2), 5.75), ((-S2, S2), 5.75), ((S2, -S2), 5.6), ((-S2, -S2), 5.6)]
DIAG_SCALE = 0.72          # diagonal horn radii vs the main horn's
# Hot horn bases: the sprite shows its N and S spikes through the colour at their bases (122 at
# row 2 col 5, 116 at row 12 col 5), so those collars and the spike roots glow in that colour; the
# tips stay dark (114). E/W collars take their base pixels' colour too (118 at row 7 col 1, 116 at
# row 7 col 9), so all four spikes read through the game's ink.
HORN_BASE = {(0, 1): 122, (0, -1): 118, (-1, 0): 120, (1, 0): 118}
HOT_ROOT = 5.55            # px from centre: the spike root up to here takes the base colour
# Horn lathe profile (axial distance from centre px, radius px); the spike part is a pchip ogive.
COLLAR = [(3.7, 1.15), (4.25, 1.15), (4.38, 1.06), (4.48, 1.06), (4.55, 0.98), (4.55, 0.92)]

# Emission by heat (D126: below 1 the face is part lit, part glowing, so the ball keeps its form;
# the hot spots, 120 and up, glow at full palette colour and speckle against it).
GLOW = {113: 0.5, 114: 0.55, 115: 0.6, 116: 0.65, 117: 0.7, 118: 0.75, 119: 0.85, 120: 1.0,
        121: 1.05, 122: 1.1, 123: 1.15, 124: 1.2}
# Seam walls: a step cooler than their plate (a shadowed panel line) so the plates speckle apart.
SEAM_GLOW = 0.9
SPIKE_INDEX = 119          # the spike shafts glow orange so they read through the game's ink
SPIKE_TIP = 117
COLLAR_INDEX = 115
RING_INDEX = 124
CORE_INDEX = 127
SOCKET_INDEX = 1
# Heat (art rule 2: the sprite's per-pixel values are its lighting): a base by
# the angle (deg) from a heat axis tipped HEAT_TILT north of straight up (the sprite's hot N half,
# dark maroon S crust), and a core glow by the angle from the core port's axis grading the casing
# right round the plug 124 -> 123 -> 122. Each surface face takes the hotter of the two, plus its
# plate's seeded jitter and a little per-face mottling.
# The in-game look decides (QA, E4 sweep): the sprite reads as a bright starburst of hot orange and
# yellow speckle round a white core, so the base runs 116-119 and the scattered hot plates 120-124.
HEAT_TILT = 50
HEAT_AZ = -25              # heat axis leans this many degrees west of north (the sprite's hot NW)
HEAT = [(28, 120), (55, 119), (80, 118), (105, 117), (130, 116), (181, 115)]
CORE_HEAT = [(9, 124), (16, 123), (24, 122)]
JITTER = 0.30              # chance a plate runs one step cooler or hotter
HOT_PLATES = (0.36, 0.10)  # chance a plate is a hot spot (+3..+5, to 124): hot side, crust side
                           # (the sprite's south half is darker, with few hot spots)
COOL_PLATES = 0.14         # chance a plate is a dark pocket (-2)
MOTTLE = 0.06              # chance a face runs one step off its plate


def P(x, y, z):
    """Sprite pixel-edge column x, row y, height z px -> world."""
    return Vector(((x - W / 2) * PX, (H / 2 - y) * PX, z * PX))


CENTRE = P(CX, CY, 0)
ROT = Matrix.Rotation(-VENT_TILT, 3, "X")   # turns +z towards +y (north)


def cube_to_sphere(v):
    x, y, z = v
    sx = x * math.sqrt(max(0.0, 1 - y * y / 2 - z * z / 2 + y * y * z * z / 3))
    sy = y * math.sqrt(max(0.0, 1 - z * z / 2 - x * x / 2 + z * z * x * x / 3))
    sz = z * math.sqrt(max(0.0, 1 - x * x / 2 - y * y / 2 + x * x * y * y / 3))
    return Vector((sx, sy, sz)).normalized()


FACES = [  # normal, tangent a, tangent b (right-handed: a x b = n)
    (Vector((0, 0, 1)), Vector((1, 0, 0)), Vector((0, 1, 0))),
    (Vector((0, 0, -1)), Vector((0, 1, 0)), Vector((1, 0, 0))),
    (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))),
    (Vector((-1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))),
    (Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((1, 0, 0))),
    (Vector((0, -1, 0)), Vector((1, 0, 0)), Vector((0, 0, 1))),
]


def stations():
    """Plate-local stations 0..1 and their radius offset (px): a V seam (the plate edge at the seam
    floor, -DEPTH) whose chamfered walls rise to the plate top (0) CHAMFER in from the edge."""
    c = CHAMFER
    inner = [c + (1 - 2 * c) * k / INTERIOR for k in range(INTERIOR + 1)]
    return [0.0] + inner + [1.0], [-DEPTH] + [0.0] * len(inner) + [-DEPTH]


HEAT_AXIS = Vector((math.sin(math.radians(HEAT_AZ)) * math.sin(math.radians(HEAT_TILT)),
                    math.cos(math.radians(HEAT_AZ)) * math.sin(math.radians(HEAT_TILT)),
                    math.cos(math.radians(HEAT_TILT))))
PORT_AXIS = Vector((0, PORT_DY, math.sqrt(BALL_R ** 2 - PORT_DY ** 2))).normalized()   # the plug's direction


def band(table, ang):
    return next((i for lim, i in table if ang < lim), None)


def face_heat(d, shift, hot_spot, rng):
    """Palette index of a casing face whose (world, unsquashed) direction from the centre is d.
    shift is the plate's step; hot_spot its hot-spot boost (0 for none)."""
    ang = math.degrees(math.acos(max(-1.0, min(1.0, d.dot(HEAT_AXIS)))))
    idx = band(HEAT, ang) + shift + hot_spot
    r = rng.random()
    if r < MOTTLE / 2:
        idx -= 1
    elif r > 1 - MOTTLE / 2:
        idx += 1
    idx = max(114, min(124, idx))
    core = band(CORE_HEAT, math.degrees(math.acos(max(-1.0, min(1.0, d.dot(PORT_AXIS))))))
    return max(idx, core or 0)


def build_ball(bm, mat):
    rng = random.Random(116)
    us, off = stations()
    n = len(us)
    for normal, a, b in FACES:
        for i in range(PANELS):
            for j in range(PANELS):
                s0, s1 = -1 + 2 * i / PANELS, -1 + 2 * (i + 1) / PANELS
                t0, t1 = -1 + 2 * j / PANELS, -1 + 2 * (j + 1) / PANELS
                grid = []
                dirs = []
                for ku, (u, ou) in enumerate(zip(us, off)):
                    row = []
                    for kv, (v, ov) in enumerate(zip(us, off)):
                        d = ROT @ cube_to_sphere(normal + (s0 + (s1 - s0) * u) * a + (t0 + (t1 - t0) * v) * b)
                        r = BALL_R + min(ou, ov)
                        q = d * r * PX
                        q.z *= ZS
                        row.append(bm.verts.new(CENTRE + q))
                        dirs.append(d)
                    grid.append(row)
                # The plate's seeded offset: a step cooler or hotter, or (crust) a hot spot.
                r = rng.random()
                shift = -1 if r < JITTER / 2 else (1 if r > 1 - JITTER / 2 else 0)
                mid = (s0 + s1) / 2, (t0 + t1) / 2
                t = max(0.0, min(1.0, ((ROT @ cube_to_sphere(normal + mid[0] * a + mid[1] * b)).dot(HEAT_AXIS) + 0.6) / 1.2))
                r = rng.random()
                hot_spot = rng.choice((3, 4, 4, 5)) if r < HOT_PLATES[1] + (HOT_PLATES[0] - HOT_PLATES[1]) * t else \
                    (-2 if r > 1 - COOL_PLATES else 0)
                for ku in range(n - 1):
                    for kv in range(n - 1):
                        k0 = ku * n + kv
                        fd = (dirs[k0] + dirs[k0 + 1] + dirs[k0 + n] + dirs[k0 + n + 1]).normalized()
                        idx = face_heat(fd, shift, hot_spot, rng)
                        f = bm.faces.new((grid[ku][kv], grid[ku + 1][kv], grid[ku + 1][kv + 1], grid[ku][kv + 1]))
                        in_seam = ku in (0, n - 2) or kv in (0, n - 2)
                        if in_seam:
                            si = max(114, idx - 1)
                            f.material_index = mat(si, GLOW[si] * SEAM_GLOW)
                        else:
                            f.material_index = mat(idx, GLOW[idx])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)


def lathe(bm, axis_origin, axis, profile, sides, mat_of, cap_end=True, start=None):
    """Revolve [(axial px, radius px), ...] round `axis` from `axis_origin` (world). mat_of(k) gives
    the material of band k (between profile points k and k+1). A radius 0 point is a tip."""
    axis = axis.normalized()
    ref = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    u = axis.cross(ref).normalized()
    w = axis.cross(u).normalized()
    rings = []
    for h, r in profile:
        c = axis_origin + axis * h * PX
        if r <= 1e-6:
            rings.append([bm.verts.new(c)])
        else:
            rings.append([bm.verts.new(c + r * PX * (math.cos(2 * math.pi * k / sides) * u +
                                                   math.sin(2 * math.pi * k / sides) * w))
                          for k in range(sides)])
    for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for s in range(sides):
            t = (s + 1) % sides
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                face = (r0[0], r1[s], r1[t])
            elif len(r1) == 1:
                face = (r0[s], r0[t], r1[0])
            else:
                face = (r0[s], r0[t], r1[t], r1[s])
            bm.faces.new(face).material_index = mat_of(k)
    if len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat_of(0)
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1]).material_index = mat_of(len(rings) - 2)


def pchip_profile(p0, p1, n=8, power=1.6):
    """Ogive spike from (h0, r0) to tip (h1, 0): radius falls as (1 - t)^(1/power)-ish, full at the
    base, convex towards the tip, sharp tip."""
    (h0, r0), (h1, _) = p0, p1
    out = []
    for k in range(n + 1):
        t = k / n
        r = r0 * (1 - t ** power) * (1 - 0.25 * t)
        out.append((h0 + (h1 - h0) * t, max(0.0, r)))
    out[-1] = (h1, 0.0)
    return out


def build_horns(bm, mat):
    """Main horns (collar, hot root, glowing ogive shaft, cooler tip) and the short diagonal ones."""
    shaft = mat(SPIKE_INDEX, GLOW[SPIKE_INDEX])
    tipm = mat(SPIKE_TIP, GLOW[SPIKE_TIP])
    for (dx, dy), tip in HORNS + DIAG_HORNS:
        diag = abs(dx) > 1e-6 and abs(dy) > 1e-6
        k = DIAG_SCALE if diag else 1.0
        axis = Vector((dx, dy, 0))
        base = HORN_BASE.get((dx, dy), 121 if dy > 0 else 119)
        collar = mat(base, GLOW[base])
        col = [(h, r * k) for h, r in COLLAR]
        prof = col + [(4.64, 0.92 * k), (4.70, 0.80 * k), (4.78, 0.80 * k), (4.84, 0.88 * k)] + \
            pchip_profile((4.84, 0.88 * k), (tip, 0.0), n=8)[1:]
        # Bands: the collar and the spike root to HOT_ROOT in the base colour, the shaft glowing
        # orange, the last third of the spike a step cooler.
        ncol = max(len(COLLAR) - 1, sum(1 for h, _ in prof[:-1] if h < HOT_ROOT))
        ntip = len(prof) - 1 - 3
        lathe(bm, CENTRE, axis, prof, 12,
              lambda b, c=collar, m=ncol, t=ntip: c if b < m else (shaft if b < t else tipm))


def surface_point(dx_px, dy_px):
    """World point and normal of the (oblate) ball's top surface under top-view offset (dx, dy) px."""
    z = ZS * math.sqrt(max(0.0, BALL_R ** 2 - dx_px ** 2 - dy_px ** 2))
    n = Vector((dx_px, dy_px, z / (ZS * ZS))).normalized()
    return CENTRE + Vector((dx_px, dy_px, z)) * PX, n


def build_ports(bm, mat):
    ring = mat(RING_INDEX, 1.6)
    core = mat(CORE_INDEX, 3.0)
    dark = mat(SOCKET_INDEX, 0.0, satin=True)
    # Core port: sprite (5,6), placed for the game camera (PORT_DY).
    o, n = surface_point(0.0, PORT_DY)
    # Flush, slightly proud: a white-hot dome in a 124 rim that rises from just under the casing
    # (no recessed wall, no dark gap); the casing round it grades 124 -> 123 -> 122 (CORE_HEAT).
    prof = [(-0.25, 0.98), (-0.02, 0.98), (0.04, 0.84), (0.08, 0.68), (0.13, 0.52),
            (0.18, 0.36), (0.22, 0.18), (0.23, 0.0)]
    lathe(bm, o, n, prof, 20, lambda k: ring if k < 3 else core)
    # Fuse socket: sprite (5,9), 3 px below the core in the game camera (SOCKET_DY).
    o, n = surface_point(0.0, SOCKET_DY)
    prof = [(-0.25, 0.52), (0.07, 0.52), (0.12, 0.44), (0.10, 0.34), (0.03, 0.30), (0.02, 0.0)]
    collar = mat(COLLAR_INDEX, 0.0, satin=True)
    lathe(bm, o, n, prof, 16, lambda k: collar if k < 3 else dark)


class Mats:
    def __init__(self, sprite):
        self.sprite = sprite
        self.list = []
        self.slots = {}

    def __call__(self, idx, glow, satin=False):
        key = (idx, round(glow, 3), satin)
        if key not in self.slots:
            tag = f"{NAME}-{len(self.list)}"
            if glow > 0:
                m = common.palette_material(self.sprite, idx, tag, metallic=1.0, roughness=0.85,
                                            emission_strength=glow)
            else:
                m = common.palette_material(self.sprite, idx, tag, metallic=0.55, roughness=0.5)
                bsdf = next(nd for nd in m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
                if "Specular IOR Level" in bsdf.inputs:
                    bsdf.inputs["Specular IOR Level"].default_value = 0.25
            self.slots[key] = len(self.list)
            self.list.append(m)
        return self.slots[key]


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = Mats(sprite)
    bm = bmesh.new()
    build_ball(bm, mats)
    build_horns(bm, mats)
    build_ports(bm, mats)
    obj = common.mesh_object(NAME, bm, mats.list, coll, smooth=True)
    # Hard edges: chamfers and collars keep crisp creases.
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(38))
    except Exception as err:  # older API
        print("smooth by angle failed:", err)
    return coll, obj


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(ROOT, NAME)
    coll, body = build(sprite)
    sealed = body.copy()
    sealed.data = body.data.copy()
    coll.objects.link(sealed)
    bpy.context.view_layer.update()
    shell = common.outline_shell(sealed, coll, voxel=0.008, faces=2500, inside=0.006, islands="outer")
    shell.name = f"{NAME}_outline"
    bpy.data.objects.remove(sealed, do_unlink=True)
    assert len(shell.data.polygons) > 0, "outline shell has no mesh"
    for o in (body, shell):
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        print(o.name, "bbox px", [round(min(p[i] for p in bb) / PX, 2) for i in range(3)],
              [round(max(p[i] for p in bb) / PX, 2) for i in range(3)])
    if out:
        common.export_glb([body, shell], out)
    else:
        common.export_sprite_model(ROOT, [body, shell], MODEL, sprite["sprites"])
    me = body.data
    print(f"triangles {sum(len(p.vertices) - 2 for p in me.polygons)}; shell faces {len(shell.data.polygons)}")
    print("materials", [m.name for m in me.materials])


if __name__ == "__main__":
    main()
