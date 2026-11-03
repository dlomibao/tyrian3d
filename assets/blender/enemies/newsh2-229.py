"""Shield drone in a spinning ring (newsh2.shp frames 229-243): a hard-surface machine that is its
sprite in 3D (the treatment of the player ships, PR #84 / D50-D53).

Seen in episode 1 (levels 25-41) and episode 3 (enemy types 5 and 11). The sprite (24 x 28 px, eight
frames) is authoritative for the top silhouette, the lights and the palette colours; the concept
(assets/blender/features/concepts/newsh2-229.jpg) guides the detail where it agrees. Authored in
sprite px about the drone's centre (x right, y up-screen = rear, z up), scaled by 1/12 at the end.

What it is: a shield-shaped core (flat rear edge, pointed front tip) of two crowned armour lobes
either side of a deep dark seam, a top plate between two shallow faceted red-orange lenses set into
hex housings (the sprite's flat 2x2 lamps), inside a ring of two armour arcs (r 6.5-10.5 px) that
turns clockwise 22.5 degrees a frame. The ring is two-tone like the sprite: a pale pal_10 inner band
and crown strip, a pal_6 outer shoulder.

- Core shell: one closed loft of the sprite outline, chamfered top and bottom, with a modelled
  V-groove belt round its walls; boolean-cut louvred grille slots in the two front faces (seen by
  the game camera), slotted vents in the side walls and two deep counterbored rear nozzles with a
  throat ring and a small dim glow at the bottom; a nose sensor block at the tip.
- Lobes: crowned plates (straight walls, rounded crown), each split by a cut panel groove into an
  upper and lower plate, with a small cut vent grille on the lower plate (concept).
- Arcs: each a chamfered armour band (outer shoulder, raised crown strip, inner shoulder) in four
  plates split by real 0.24 px panel gaps over a dark spine; a dark mechanism rail inside with four
  ribs, and a chamfered clamp block at each end (concept). Arc ends per frame (RING_FIT) are fitted
  to each sprite frame.
- Underside: a plain closed chamfered belly, no detail.

Eight models, one per frame (D46: every frame of the animation): newsh2-229 (frame 229),
newsh2-229-f2 (231) ... newsh2-229-f8 (243); each is centred where its frame draws the drone
(found from the core's top-left light).

Texture: no concept projection (its maps.json says "bake": "model", as the player ships, D50).
Cycles bakes a colour multiplier (ambient occlusion, edge lift) and a roughness/metalness map
(bake_maps below, after usp_talon.bake_maps) on frame 229 to assets/blender/textures/newsh2-229/bake/;
its UVs are copied to the other seven frames (identical topology), so all eight share one pair of
maps and the same brightness. Base Color = map x palette colour, so pal_<index>, fades and the hit
flash still apply; emissive parts keep their flat palette colour. Each frame has an outline shell
(common.outline_shell's recipe, D51, keeping every island: the core and both arcs are separate
pieces) riding as a child.

Run: blender --background --factory-startup --python assets/blender/enemies/newsh2-229.py
     [-- --preview out.png] [--no-bake]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)
NAME = "newsh2-229"
TAG = "newsh2-229"
U = 1 / 12
D2R = math.pi / 180

# The ring's two arcs per sprite frame: (start, end) degrees counter-clockwise from +x, fitted to
# each frame's pixels (top-view IoU 0.96-0.97 for the ring alone).
RING_FIT = {
    229: ((109.0, 251.0), (289.0, 71.0)),
    231: ((82.5, 230.5), (262.5, 50.5)),
    233: ((63.0, 207.0), (243.0, 27.0)),
    235: ((39.5, 187.5), (219.5, 7.5)),
    237: ((6.0, 174.0), (192.0, 350.0)),
    239: ((352.5, 140.5), (172.5, 320.5)),
    241: ((333.0, 117.0), (153.0, 297.0)),
    243: ((309.5, 97.5), (129.5, 277.5)),
}

# ------------------------------------------------------------------------------------------------
# Materials (one list shared by every mesh, so indices line up through joins and booleans)
# ------------------------------------------------------------------------------------------------
(BAND_OUT, STRIP, BAND_IN, WALL, SPINE, RAIL, RIB, CLAMP, SHELL, SHELL_LOW, SEAM, LOBE_M, GROOVE, TOP,
 HOUSING, LENS_TOP, LENS_MID, LENS_SIDE, NOZ_GLOW, DARK) = range(20)
EMISSIVE = {LENS_TOP, LENS_MID, LENS_SIDE, NOZ_GLOW}


def make_materials(sprite):
    def pal(i, part, metal, rough, glow=0.0):
        return common.palette_material(sprite, i, f"{TAG}_{part}", metallic=metal, roughness=rough,
                                       emission_strength=glow)
    return [
        pal(6, "ring_shoulder", 0.42, 0.36),
        pal(10, "ring_strip", 0.45, 0.34),
        pal(10, "ring_inner", 0.42, 0.40),
        pal(5, "ring_wall", 0.38, 0.45),
        pal(2, "ring_spine", 0.25, 0.65),
        pal(3, "ring_rail", 0.38, 0.50),
        pal(4, "ring_rib", 0.42, 0.42),
        pal(3, "ring_clamp", 0.40, 0.45),
        pal(5, "core_shell", 0.40, 0.42),
        pal(4, "core_belly", 0.32, 0.55),
        pal(4, "core_seam", 0.30, 0.55),
        pal(7, "core_lobe", 0.45, 0.32),
        pal(3, "core_groove", 0.30, 0.60),
        pal(6, "core_top", 0.42, 0.38),
        pal(4, "core_housing", 0.40, 0.42),
        pal(121, "lens_cap", 0.0, 0.25, 3.0),
        pal(119, "lens_upper", 0.0, 0.25, 3.0),
        pal(118, "lens_side", 0.0, 0.25, 3.0),
        pal(120, "nozzle_glow", 0.0, 0.5, 1.6),
        pal(2, "recess", 0.20, 0.75),
    ]


# ------------------------------------------------------------------------------------------------
# Geometry helpers, in sprite px (x right, y up-screen = rear, z up)
# ------------------------------------------------------------------------------------------------
def area2(o):
    return sum(o[i][0] * o[(i + 1) % len(o)][1] - o[(i + 1) % len(o)][0] * o[i][1] for i in range(len(o))) / 2


def ccw(o):
    return list(reversed(o)) if area2(o) < 0 else list(o)


def inset(o, d):
    """Inset a (counter-clockwise) outline by d with mitred joins."""
    o = ccw(o)
    n = len(o)
    out = []
    for i in range(n):
        a, b, c = Vector(o[i - 1]), Vector(o[i]), Vector(o[(i + 1) % n])
        e1, e2 = (b - a).normalized(), (c - b).normalized()
        n1, n2 = Vector((-e1.y, e1.x)), Vector((-e2.y, e2.x))
        m = (n1 + n2).normalized()
        k = d / max(0.3, m.dot(n1))
        out.append((b.x + m.x * k, b.y + m.y * k))
    return out


class Part:
    """A bmesh in px with per-face material."""

    def __init__(self):
        self.bm = bmesh.new()

    def face(self, verts, mat):
        f = self.bm.faces.new(verts)
        f.material_index = mat
        return f

    def stack(self, rings, mats, cap_top, cap_bot):
        """rings: [(outline2d, z)], all outlines the same length; mats per band (int or list)."""
        vs = [[self.bm.verts.new((x, y, z)) for x, y in o] for o, z in rings]
        for k in range(len(vs) - 1):
            n = len(vs[k])
            for i in range(n):
                j = (i + 1) % n
                m = mats[k] if isinstance(mats, (list, tuple)) else mats
                self.face((vs[k][i], vs[k][j], vs[k + 1][j], vs[k + 1][i]), m)
        if cap_top is not None:
            self.face(vs[-1], cap_top)
        if cap_bot is not None:
            self.face(list(reversed(vs[0])), cap_bot)
        return vs

    def plate(self, o, z0, z1, c_bot, c_top, mat, side_mat=None, top_mat=None, bot_mat=None):
        o = ccw(o)
        rings = []
        if c_bot > 0:
            rings.append((inset(o, c_bot), z0))
            rings.append((o, z0 + c_bot))
        else:
            rings.append((o, z0))
        if c_top > 0:
            rings.append((o, z1 - c_top))
            rings.append((inset(o, c_top), z1))
        else:
            rings.append((o, z1))
        side = mat if side_mat is None else side_mat
        self.stack(rings, side, mat if top_mat is None else top_mat, mat if bot_mat is None else bot_mat)

    def crown(self, o, z0, zc, z1, shrink, steps, mat):
        """Straight walls z0..zc, then a rounded crown to z1 (quarter-ellipse section)."""
        o = ccw(o)
        mx = sum(p[0] for p in o) / len(o)
        my = sum(p[1] for p in o) / len(o)
        rings = [(o, z0), (o, zc)]
        for k in range(1, steps + 1):
            t = k / steps * math.pi / 2
            f = 1 - shrink * (1 - math.cos(t))
            rings.append(([(mx + (x - mx) * f, my + (y - my) * f) for x, y in o], zc + (z1 - zc) * math.sin(t)))
        self.stack(rings, mat, mat, mat)

    def polar(self, a0, a1, prof, mats, n, ch0, ch1, cap_mat):
        """Sweep a closed (r, z) profile around the origin from a0 to a1 (radians, ccw), with
        chamfered ends (ch0/ch1 px: an inset ring at the end angle)."""
        cr = sum(p[0] for p in prof) / len(prof)
        cz = sum(p[1] for p in prof) / len(prof)

        def ins(c):
            out = []
            for r, z in prof:
                d = math.hypot(cr - r, cz - z) or 1
                k = min(c, 0.45 * d) / d
                out.append((r + (cr - r) * k, z + (cz - z) * k))
            return out
        rings = []
        if ch0 > 0:
            rings.append([(a0, r, z) for r, z in ins(ch0)])
        for i in range(n + 1):
            t = i / n
            ring = []
            for r, z in prof:
                b0 = a0 + ch0 / r
                b1 = a1 - ch1 / r
                ring.append((b0 + (b1 - b0) * t, r, z))
            rings.append(ring)
        if ch1 > 0:
            rings.append([(a1, r, z) for r, z in ins(ch1)])
        vs = [[self.bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for a, r, z in ring] for ring in rings]
        m = len(prof)
        for k in range(len(vs) - 1):
            for i in range(m):
                j = (i + 1) % m
                mm = mats[i] if isinstance(mats, (list, tuple)) else mats
                self.face((vs[k][i], vs[k][j], vs[k + 1][j], vs[k + 1][i]), mm)
        self.face(list(reversed(vs[0])), cap_mat)
        self.face(vs[-1], cap_mat)

    def box(self, centre, size, rot_z, mat, ch=0.0):
        """A (chamfered) box at centre (x, y, z) with size (sx, sy, sz), turned rot_z about z."""
        sx, sy, sz = size
        o = [(-sx / 2, -sy / 2), (sx / 2, -sy / 2), (sx / 2, sy / 2), (-sx / 2, sy / 2)]
        c, s = math.cos(rot_z), math.sin(rot_z)
        o = [(centre[0] + x * c - y * s, centre[1] + x * s + y * c) for x, y in o]
        self.plate(o, centre[2] - sz / 2, centre[2] + sz / 2, ch, ch, mat)

    def cylinder(self, centre, axis, r, length, mat, sides=16, end_mat=None):
        """A closed cylinder from centre along axis (unit vector) for `length`."""
        a = Vector(axis).normalized()
        ref = Vector((0, 0, 1)) if abs(a.z) < 0.9 else Vector((1, 0, 0))
        u = a.cross(ref).normalized()
        v = a.cross(u).normalized()
        c0 = Vector(centre)
        rings = []
        for c in (c0, c0 + a * length):
            rings.append([self.bm.verts.new(c + r * (math.cos(2 * math.pi * (i + 0.5) / sides) * u +
                                                     math.sin(2 * math.pi * (i + 0.5) / sides) * v))
                          for i in range(sides)])
        for i in range(sides):
            j = (i + 1) % sides
            self.face((rings[0][i], rings[0][j], rings[1][j], rings[1][i]), mat)
        em = mat if end_mat is None else end_mat
        self.face(list(reversed(rings[0])), em)
        self.face(rings[1], em)

    def tube(self, centre, axis, r_in, r_out, length, mat, sides=16):
        """A closed annulus (a ring with a hole) from centre along axis for `length`."""
        a = Vector(axis).normalized()
        ref = Vector((0, 0, 1)) if abs(a.z) < 0.9 else Vector((1, 0, 0))
        u = a.cross(ref).normalized()
        v = a.cross(u).normalized()
        c0 = Vector(centre)
        loops = []
        for c, r in ((c0, r_out), (c0 + a * length, r_out), (c0 + a * length, r_in), (c0, r_in)):
            loops.append([self.bm.verts.new(c + r * (math.cos(2 * math.pi * (i + 0.5) / sides) * u +
                                                     math.sin(2 * math.pi * (i + 0.5) / sides) * v))
                          for i in range(sides)])
        for k in range(4):
            l0, l1 = loops[k], loops[(k + 1) % 4]
            for i in range(sides):
                j = (i + 1) % sides
                self.face((l0[i], l0[j], l1[j], l1[i]), mat)

    def done(self):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        return self.bm


def to_mesh(bm, name, mats):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    return me


def to_obj(me, coll):
    obj = bpy.data.objects.new(me.name, me)
    coll.objects.link(obj)
    return obj


def boolean(obj, cutter_part, mats, coll):
    """obj minus the cutter (a Part); cut faces take the cutter's material indices."""
    cme = to_mesh(cutter_part.done(), obj.name + "_cut", mats)
    cut = to_obj(cme, coll)
    cut.hide_render = True
    mod = obj.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.material_mode = "INDEX"
    mod.object = cut
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    obj.modifiers.remove(mod)
    old = obj.data
    obj.data = new
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(cut, do_unlink=True)
    bpy.data.meshes.remove(cme)
    return obj


# ------------------------------------------------------------------------------------------------
# The core (fixed, built once at the origin)
# ------------------------------------------------------------------------------------------------
CORE_R = [(0, 4.55), (3.4, 4.55), (3.95, 4.25), (4.25, 4.0), (4.55, 3.4), (4.55, -1.3), (3.45, -2.5),
          (2.45, -3.5), (1.45, -4.42), (0.5, -4.68)]
CORE = CORE_R + [(-x, y) for x, y in reversed(CORE_R[1:])]
CORE = [p for i, p in enumerate(CORE) if i == 0 or p != CORE[i - 1]]
LOBE = [(-0.45, 2.9), (-1.0, 2.85), (-2.6, 1.35), (-3.5, 0.7), (-3.45, -1.0), (-2.95, -1.8), (-1.95, -2.8),
        (-1.3, -3.45), (-0.85, -3.85), (-0.45, -3.85)]
LIGHT = (2.75, 2.75)
Z_BOT, Z_BELT, Z_TOP = -2.3, 0.0, 2.5
# Front faces of the shell (the diagonal from (4.55,-1.3) to (0.5,-4.68)): direction and normal.
FRONT_A, FRONT_B = Vector((4.55, -1.3)), Vector((0.5, -4.68))


def build_core(mats, coll):
    o = ccw(CORE)
    # Shell: chamfered bottom, lower tier, V-groove belt, upper tier, chamfered top.
    sh = Part()
    g = 0.22  # belt groove depth
    sh.stack([(inset(o, 0.55), Z_BOT), (o, Z_BOT + 0.55), (o, Z_BELT - 0.24), (inset(o, g), Z_BELT),
              (o, Z_BELT + 0.24), (o, Z_TOP - 0.5), (inset(o, 0.5), Z_TOP)],
             [SHELL_LOW, SHELL_LOW, SHELL_LOW, SHELL, SHELL, SHELL], SHELL, SHELL_LOW)
    shell = to_obj(to_mesh(sh.done(), "core_shell", mats), coll)
    # Cutters: front louvre slots, side vents, rear nozzles.
    cut = Part()
    d = (FRONT_B - FRONT_A).normalized()
    nrm = Vector((d.y, -d.x))  # outward (front-right)
    if nrm.dot(Vector((1, -1))) < 0:
        nrm = -nrm
    rot = math.atan2(d.y, d.x)
    for s in (-1, 1):
        mid = FRONT_A.lerp(FRONT_B, 0.47)
        for z in (0.62, 1.12, 1.62):
            c = (s * (mid.x + nrm.x * 0.0), mid.y, z)
            cut.box(c, (2.1, 0.62, 0.26), rot if s > 0 else math.pi - rot, DARK)
        for z in (-1.55, -1.1, -0.65):  # lower tier, side walls: three vent slots
            cut.box((s * 4.55, 0.9, z), (0.62, 2.4, 0.24), 0.0, DARK)
        for z in (0.75, 1.3):  # upper tier, side walls: two longer slots
            cut.box((s * 4.55, 1.3, z), (0.62, 3.2, 0.26), 0.0, DARK)
    for s in (-1, 1):  # rear nozzles: deep bores in the flat rear face, counterbored at the mouth
        cut.cylinder((s * 1.75, 2.55, 1.1), (0, 1, 0), 0.62, 2.4, DARK, sides=16)
    boolean(shell, cut, mats, coll)
    # The counterbores at the nozzle mouths: a pass of their own (overlapping the bores in one
    # cutter would make the exact solver keep a cap over each bore).
    cut = Part()
    for s in (-1, 1):
        cut.cylinder((s * 1.75, 4.3, 1.1), (0, 1, 0), 0.8, 0.6, HOUSING, sides=16)
    boolean(shell, cut, mats, coll)

    parts = [shell]
    # Nozzle glow at the bottom of each bore (smaller than the bore, a dark wall round it) and a
    # throat ring part-way down, so the straight rear view reads as a deep stepped nozzle.
    det = Part()
    for s in (-1, 1):
        det.cylinder((s * 1.75, 2.6, 1.1), (0, 1, 0), 0.4, 0.08, NOZ_GLOW, sides=16)
        det.tube((s * 1.75, 3.45, 1.1), (0, 1, 0), 0.44, 0.66, 0.22, GROOVE, sides=16)
    # Seam: the dark channel between the lobes.
    det.plate([(-0.42, 3.0), (0.42, 3.0), (0.42, -4.0), (-0.42, -4.0)], 2.2, 2.78, 0.0, 0.06, SEAM)
    # Top plate between the lights, a V foot pointing down the seam.
    det.plate([(-1.35, 4.4), (1.35, 4.4), (1.35, 3.25), (0.45, 2.6), (-0.45, 2.6), (-1.35, 3.25)],
              2.4, 3.85, 0.0, 0.3, TOP)
    # A recessed dark slot across the top plate's rear (a sensor slit).
    det.box((0, 3.95, 3.86), (1.5, 0.28, 0.06), 0.0, DARK)
    # Hex housings and faceted lenses.
    for s in (-1, 1):
        lx, ly = s * LIGHT[0], LIGHT[1]
        hexo = [(lx + 1.45 * math.cos(math.pi / 3 * k), ly + 1.3 * math.sin(math.pi / 3 * k)) for k in range(6)]
        det.plate(hexo, 2.2, 3.55, 0.0, 0.25, HOUSING)
        # Faceted lens: a shallow octagonal lens set into the housing, barely proud of its rim.
        oct_ = lambda r, z: ([(lx + r * math.cos(math.pi / 4 * (k + 0.5)), ly + r * 0.95 * math.sin(math.pi / 4 * (k + 0.5)))  # noqa: E731
                              for k in range(8)], z)
        det.stack([oct_(1.0, 3.3), oct_(1.02, 3.48), oct_(0.8, 3.64), oct_(0.42, 3.72)],
                  [LENS_SIDE, LENS_MID, LENS_MID], LENS_TOP, LENS_SIDE)
    # Nose sensor at the tip: a chamfered block with a dark slit.
    det.box((0, -4.55, -0.15), (1.0, 0.7, 1.7), 0.0, HOUSING, ch=0.12)
    det.box((0, -4.86, 0.25), (0.5, 0.12, 0.22), 0.0, DARK)
    parts.append(to_obj(to_mesh(det.done(), "core_detail", mats), coll))

    # Lobes, each split by a panel groove and with a small vent grille on its lower plate.
    for s in (-1, 1):
        lp = Part()
        lp.crown([(-s * x, y) for x, y in LOBE], 2.3, 3.2, 4.45, 0.62, 6, LOBE_M)
        lobe = to_obj(to_mesh(lp.done(), f"lobe_{s}", mats), coll)
        cut = Part()
        # Groove across the lobe: from the seam at y -1.0 slanting up to the outer edge at y -0.2.
        a, b = Vector((s * 0.2, -1.25)), Vector((s * 4.0, -0.35))
        mid = (a + b) / 2
        ang = math.atan2(b.y - a.y, b.x - a.x)
        cut.box((mid.x, mid.y, 4.85), ((b - a).length, 0.24, 2.2), ang, GROOVE)
        # Vent grille on the lower plate: three short slots parallel to the groove.
        for k, off in enumerate((0.75, 1.15, 1.55)):
            c = Vector((s * 1.85, -1.1 - off * 0.85 - 0.1))
            cut.box((c.x, c.y, 5.05), (0.95, 0.17, 2.2), ang, GROOVE)
        boolean(lobe, cut, mats, coll)
        parts.append(lobe)
    # Merge to one mesh, in a fixed order.
    bm = bmesh.new()
    for p in parts:
        bm.from_mesh(p.data)
    me = to_mesh(bm, "core", mats)
    for p in parts:
        d_ = p.data
        bpy.data.objects.remove(p, do_unlink=True)
        bpy.data.meshes.remove(d_)
    return me


# ------------------------------------------------------------------------------------------------
# The arcs (per frame)
# ------------------------------------------------------------------------------------------------
BAND = [(7.2, -1.15), (7.65, -1.6), (9.85, -1.6), (10.42, -1.05), (10.5, 0.45), (10.3, 1.05), (9.85, 1.42),
        (9.15, 1.52), (8.95, 1.87), (7.85, 1.87), (7.68, 1.52), (7.45, 1.4), (7.25, 1.05), (7.2, 0.45)]
BAND_MATS = [WALL, WALL, WALL, WALL, BAND_OUT, BAND_OUT, BAND_OUT, STRIP, STRIP, STRIP, BAND_IN, BAND_IN,
             BAND_IN, WALL]
SPINE_P = [(7.45, -1.25), (10.15, -1.25), (10.15, 1.2), (7.45, 1.2)]


def chamfer_rect(r0, r1, z0, z1, c):
    return [(r0 + c, z0), (r1 - c, z0), (r1, z0 + c), (r1, z1 - c), (r1 - c, z1), (r0 + c, z1), (r0, z1 - c),
            (r0, z0 + c)]


RAIL_P = chamfer_rect(6.5, 7.3, -1.15, 0.95, 0.12)
RIB_P = chamfer_rect(6.4, 7.25, -1.0, 1.2, 0.12)
CLAMP_P = chamfer_rect(6.4, 8.25, -1.35, 1.62, 0.18)
SEG_BOUNDS = (0.0, 0.24, 0.5, 0.76, 1.0)
GAP = 0.24  # px, the panel gaps between band plates
RIB_AT = (0.13, 0.37, 0.63, 0.87)
N_ARC = 30


def build_arc(p, a0d, span_d):
    a0 = a0d * D2R
    span = span_d * D2R
    a1 = a0 + span
    rm = 8.8
    # Band plates over a dark spine.
    for k in range(4):
        u0, u1 = SEG_BOUNDS[k], SEG_BOUNDS[k + 1]
        s0 = a0 + span * u0 + (GAP / 2 / rm if k > 0 else 0)
        s1 = a0 + span * u1 - (GAP / 2 / rm if k < 3 else 0)
        n = max(3, round(N_ARC * (u1 - u0)))
        p.polar(s0, s1, BAND, BAND_MATS, n, 0.12 if k > 0 else 0.32, 0.12 if k < 3 else 0.32, WALL)
    p.polar(a0 + 0.8 / rm, a1 - 0.8 / rm, SPINE_P, SPINE, N_ARC, 0, 0, SPINE)
    # Mechanism rail inside, with ribs.
    p.polar(a0 + 0.5 / 7, a1 - 0.5 / 7, RAIL_P, RAIL, N_ARC, 0.08, 0.08, RAIL)
    for u in RIB_AT:
        c = a0 + span * u
        w = 0.32 / 6.8
        p.polar(c - w, c + w, RIB_P, RIB, 1, 0.08, 0.08, RIB)
    # Clamp blocks at the ends (inner side).
    w = 1.35 / 7.3
    p.polar(a0, a0 + w, CLAMP_P, CLAMP, 2, 0.15, 0.15, CLAMP)
    p.polar(a1 - w, a1, CLAMP_P, CLAMP, 2, 0.15, 0.15, CLAMP)


def build_arcs_bm(arcs):
    p = Part()
    for a0d, a1d in arcs:
        span = (a1d - a0d) % 360
        build_arc(p, a0d, span)
    return p.done()


# ------------------------------------------------------------------------------------------------
# Hidden-face culling (usp_talon.cull_hidden), returning the dead face indices
# ------------------------------------------------------------------------------------------------
def hidden_faces(me, protect=(), grid=3, ndirs=64):
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    golden = math.pi * (3 - math.sqrt(5))
    dirs = []
    for i in range(ndirs):
        z = 1 - 2 * (i + 0.5) / ndirs
        r = math.sqrt(1 - z * z)
        dirs.append(Vector((r * math.cos(golden * i), r * math.sin(golden * i), z)))
    eps = 2e-3
    dead = []
    for f in bm.faces:
        if f.material_index in protect:
            continue
        n = f.normal
        vs = [v.co for v in f.verts]
        c = f.calc_center_median()
        pts = [c]
        if len(vs) == 4:
            for i in range(grid):
                for j in range(grid):
                    u, v = (i + 0.5) / grid, (j + 0.5) / grid
                    pts.append(vs[0].lerp(vs[1], u).lerp(vs[3].lerp(vs[2], u), v))
        else:
            for vco in vs:
                for t in (0.5, 0.9):
                    pts.append(c.lerp(vco, t))
        cand = [d for d in dirs if d.dot(n) > 0.05]
        seen = False
        for q in pts:
            o = q + n * eps
            for d in cand:
                if tree.ray_cast(o, d, 100.0)[0] is None:
                    seen = True
                    break
            if seen:
                break
        if not seen:
            dead.append(f.index)
    bm.free()
    return dead


def delete_faces(me, dead):
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in dead], context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me)
    bm.free()


# ------------------------------------------------------------------------------------------------
# Frame models
# ------------------------------------------------------------------------------------------------
def frame_centre(frame):
    for r, line in enumerate(frame["pixels"]):
        if 121 in line:
            return line.index(121) + 3.5, r + 3.5
    return 12.5, 13.5


def assemble(name, core_me, arcs_me, centre, mats, coll):
    bm = bmesh.new()
    bm.from_mesh(core_me)
    bm.from_mesh(arcs_me)
    ox, oy = centre[0] - 12, 14 - centre[1]
    m = Matrix.Translation((ox * U, oy * U, 0)) @ Matrix.Scale(U, 4)
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    me = to_mesh(bm, name, mats)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(34))
    obj = to_obj(me, coll)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    return obj


def outline_shell_all(obj, collection, voxel=0.012, faces=2000, smooth=6):
    """common.outline_shell, keeping every sizeable island (core + both arcs)."""
    me = obj.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{obj.name}_outline", me)
    collection.objects.link(shell)
    shell.matrix_world = obj.matrix_world.copy()
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    rm.use_smooth_shade = True
    common._apply_modifiers(shell)
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    bm.verts.ensure_lookup_table()
    seen, islands = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        st, isl = [v], []
        while st:
            x = st.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            isl.append(x)
            st.extend(e.other_vert(x) for e in x.link_edges)
        islands.append(isl)
    big = max(len(i) for i in islands)
    dead = [v for isl in islands if len(isl) < 0.05 * big for v in isl]
    # Also drop islands enclosed inside another (inner shells): keep only those whose bbox is not
    # inside a bigger island's bbox by much (rare; the parts here are closed).
    bmesh.ops.delete(bm, geom=dead, context="VERTS")
    bm.to_mesh(shell.data)
    bm.free()
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = smooth
    n = len(shell.data.polygons)
    if n > faces:
        dec = shell.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / n
    common._apply_modifiers(shell)
    shell.data.shade_smooth()
    shell.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell["tyrian_outline"] = True
    return shell, sum(1 for isl in islands if len(isl) >= 0.05 * big)


# ------------------------------------------------------------------------------------------------
# Bake (usp_talon.bake_maps, neutral tint; no concept projection, D50)
# ------------------------------------------------------------------------------------------------
TINT = (0.97, 0.985, 1.0)


def bake_maps(obj, out_dir, textured, size=1024, samples=64):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(d.type == "METAL" for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:  # noqa: BLE001
        print("no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{TAG}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{TAG}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        L = nt.links.new
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    L(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.03
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.14
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.004
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        L(bev.outputs["Normal"], dot.inputs[0])
        L(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.5, math_("MULTIPLY", occl, 0.6)),
                                       math_("MULTIPLY", edge, 0.22)), 1.0)
            tint = node("ShaderNodeCombineColor")
            for k in range(3):
                L(math_("MULTIPLY", v, TINT[k]), tint.inputs[k])
            L(tint.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            L(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            L(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        L(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        L(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()

    for i in textured:
        m = mats[i]
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col_img
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm_img
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])


def copy_uv(src, dst):
    import array
    s = src.data.uv_layers["bake"]
    n = len(s.data)
    assert n == len(dst.data.loops), (n, len(dst.data.loops))
    buf = array.array("f", [0.0]) * (2 * n)
    s.data.foreach_get("uv", buf)
    d = dst.data.uv_layers.new(name="bake")
    d.data.foreach_set("uv", buf)


# ------------------------------------------------------------------------------------------------
def build_frames(sprite, mats, coll, bake_dir=None):
    """The eight frame models (frame 229 first), baked if bake_dir is given."""
    frames_by = {f["index"]: f for f in sprite["frames"]}
    frame_ids = sprite["sprites"][0]["frames"]
    scratch = common.reset_collection(TAG + "_tmp")
    core_me = build_core(mats, scratch)
    dead_core = hidden_faces(core_me, protect={GROOVE, DARK, NOZ_GLOW, SEAM})
    delete_faces(core_me, dead_core)
    arcs0 = to_mesh(build_arcs_bm(RING_FIT[frame_ids[0]]), "arcs0", mats)
    dead_arcs = hidden_faces(arcs0, protect={WALL, SPINE})
    bpy.data.meshes.remove(arcs0)
    print(f"{NAME}: culled hidden faces: core {len(dead_core)}, arcs {len(dead_arcs)}")
    objs = []
    for k, fid in enumerate(frame_ids):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        arcs = to_mesh(build_arcs_bm(RING_FIT[fid]), f"arcs_{fid}", mats)
        delete_faces(arcs, dead_arcs)
        obj = assemble(name, core_me, arcs, frame_centre(frames_by[fid]), mats, coll)
        obj["tyrian_frame"] = fid
        objs.append(obj)
        bpy.data.meshes.remove(arcs)
        if bake_dir is not None:
            if k == 0:  # bake before the shells exist, so they can't occlude the model
                bake_dir.mkdir(parents=True, exist_ok=True)
                bake_maps(obj, bake_dir, [i for i in range(len(mats)) if i not in EMISSIVE])
            else:
                copy_uv(objs[0], obj)
    for o in objs:
        print(f"{o.name}: {len(o.data.polygons)} faces, {sum(len(p.vertices) - 2 for p in o.data.polygons)} triangles")
    return objs, frame_ids


def frames_subset(sprite, indices):
    """The sprite list with only the given frame indices (for one model of an animation)."""
    out = []
    for s in sprite["sprites"]:
        keep = [f for f in s["frames"] if f in indices]
        if keep:
            out.append({**s, "frames": keep})
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(ROOT, NAME)
    mats = make_materials(sprite)
    coll = common.reset_collection(NAME)
    bake = "--no-bake" not in argv
    bake_dir = ROOT / "assets" / "blender" / "textures" / NAME / "bake" if bake else None
    objs, frame_ids = build_frames(sprite, mats, coll, bake_dir)
    fmt = "WEBP" if bake else "AUTO"
    for obj, fid in zip(objs, frame_ids):
        shell, islands = outline_shell_all(obj, coll)
        shell.parent = obj
        print(f"{shell.name}: {len(shell.data.polygons)} faces, {islands} islands")
        common.export_sprite_model(ROOT, [obj, shell], f"enemies/{obj.name}", frames_subset(sprite, [fid]),
                                   image_format=fmt)
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        by_index = {f["index"]: f for f in sprite["frames"]}
        for i, (obj, fid) in enumerate(zip(objs, frame_ids)):
            frame = by_index[fid]
            ref = ROOT / "reference" / "models" / NAME / frame["image"]
            path = out if i == 0 else out.with_name(f"{out.stem}{obj.name[len(NAME):]}.png")
            common.render_preview([obj], str(path), ref, size=frame["size"])


if __name__ == "__main__":
    main()
