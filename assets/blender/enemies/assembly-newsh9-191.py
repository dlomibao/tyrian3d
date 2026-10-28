"""Armoured eye sphere (newsh9.shp 153, 155, 157, 191, 193, 195, assembly of 6 pieces): a 3D
version of its sprites.

Seen in episode 4 (levels 4.4 and 4.20). Six 2x2 enemies side by side (sprite.json
`assemblyLayout`) make the top 72x56 px of a round machine about 72 px across: a grey ball of
armour plates with a raised swirl on top (a C-shaped boss with two bright spots, curling round
into a glowing blue strip), a latch rod set into each flank, and a big blue eye with a dark pupil
and a dark cross across it at the front (bottom of the screen). The bottom of the ball is drawn by
other pieces (newsh9-210, 212, 214, a separate assembly), so it is cut off here.

The ball is a dome about 26 px tall on a flat base at z = 0 and the eye a dome about 11 px proud
of it, with an 8 px pupil port sunk 3 px into it at the cut edge. The armour takes one mid grey and
the eye one mid blue, leaving the sprite's drawn shading, outline and sheen to the game's lights
and outline; the plate seams and the eye's cross are grooves about 1 px wide and deep, cut with
exact booleans.

The whole ball is built once in assembly coordinates, then cut into the six pieces with
common.split_assembly; each piece keeps the uncut ball's normals so the cuts don't show. Each
piece has one frame, so each gets one model.

Run: blender --background --python assets/blender/enemies/assembly-newsh9-191.py [-- --preview out.png]
(the preview is the whole object; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "assembly-newsh9-191"
ROOT = common.repo_root(__file__)
PIECES = ["newsh9-153", "newsh9-155", "newsh9-157", "newsh9-191", "newsh9-193", "newsh9-195"]
# Assembly pixel (0, 0) is the top-left corner of newsh9-153 (screen cx 137 - 12, cy -18 - 14).
# The six pieces cover 72 x 56 px; their centre (screen 161, -4) is the Blender origin.
CX0, CY0 = 161, -4
PX = 1 / 12  # one sprite pixel in units

# The ball: centre and radii in assembly pixels (pixel edges), and its height above/below z = 0.
# About 22 px tall over a 72 px footprint: a real dome, round to the rim, not a lens.
BU, BV, BRU, BRV = 36.2, 35.0, 36.8, 34.7
ZT, ZB = 2.2, 0.0
# The eye: centre and radii (pixels) and how far it bulges out of the ball (about 12 px).
EU, EV, ERU, ERV = 35.8, 50.5, 20.8, 14.6
EYE_LIFT, EYE_BULGE = 0.03, 0.92
# The pupil: a round port about 8 px across and 3 px deep, cut into the eye at the sprite's
# bottom edge (its black is cols 30-37 from row 47 down to the cut).
PU, PV, PRU, PRV = 34.0, 52.0, 4.0, 4.0
PUPIL_DEPTH = 0.25
# The raised swirl's head: a rounded boss about 7.5 px proud of the ball.
SU, SV, SRU, SRV, SWIRL_H = 28.0, 21.0, 11.8, 11.6, 0.62


def X(u):
    """Assembly x in pixels (pixel edges; a pixel's centre is col + 0.5) to Blender X."""
    return (u - 36) * PX


def Y(v):
    """Assembly y in pixels (pixel edges) to Blender Y: sprite up is +Y."""
    return (28 - v) * PX


def U(x):
    return x / PX + 36


def V(y):
    return 28 - y / PX


def zs(u, v):
    """Height of the ball's top surface over assembly pixel (u, v)."""
    e = ((u - BU) / BRU) ** 2 + ((v - BV) / BRV) ** 2
    return ZT * math.sqrt(max(0.0, 1 - e))


def zeye(u, v):
    """Height of the eye's surface (a dome standing out of the ball)."""
    e = ((u - EU) / ERU) ** 2 + ((v - EV) / ERV) ** 2
    return zs(u, v) + EYE_LIFT + EYE_BULGE * math.sqrt(max(0.0, 1 - e))


def zswirl(u, v):
    """Height of the swirl's head: one smooth bulge on the ball."""
    e = ((u - SU) / SRU) ** 2 + ((v - SV) / SRV) ** 2
    return zs(u, v) + 0.03 + SWIRL_H * max(0.0, 1 - e) ** 0.6


def normal_of(surface, u, v):
    """The surface's normal over (u, v), from its slope."""
    d = 0.3
    dzdu = (surface(u + d, v) - surface(u - d, v)) / (2 * d)
    dzdv = (surface(u, v + d) - surface(u, v - d)) / (2 * d)
    return Vector((-dzdu / PX, dzdv / PX, 1.0)).normalized()


# --- geometry helpers --------------------------------------------------------------------------

def _tag(bm, before, mat, smooth):
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def resample(path, step):
    """Insert points along a sweep path so no two are more than `step` px apart (the tube then
    follows a curved surface instead of cutting chords through it)."""
    out = [path[0]]
    for a, b in zip(path, path[1:]):
        n = max(1, int(math.ceil(math.hypot(b[0] - a[0], b[1] - a[1]) / step)))
        for i in range(1, n + 1):
            t = i / n
            out.append(tuple(x + (y - x) * t for x, y in zip(a, b)))
    return out


def sweep(bm, path, sides=8, mat=0, smooth=True, surface=zs, step=1.5):
    """A tube lying on a surface along a path of (u, v, lift, half_width_px, half_height). The
    tube's centre sits `lift` above the surface along its normal, and its rings stand square to
    the surface. A ring of zero size collapses to a point (a rounded or pointed end)."""
    before = set(bm.faces)
    path = resample(path, step)
    norms = [normal_of(surface, u, v) for u, v, _, _, _ in path]
    pts = [Vector((X(u), Y(v), surface(u, v))) + n * lift for (u, v, lift, _, _), n in zip(path, norms)]
    rings = []
    for i, (_, _, _, w, h) in enumerate(path):
        n = norms[i]
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t -= n * t.dot(n)
        t.normalize()
        side = t.cross(n)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * PX * math.cos(a)) + n * (h * math.sin(a))))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                bm.faces.new((r0[0], r1[j], r1[k]))
            elif len(r1) == 1:
                bm.faces.new((r0[k], r0[j], r1[0]))
            else:
                bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    if len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    _tag(bm, before, mat, smooth)


def cap(bm, cu, cv, ru, rv, top, bottom, mat=0, rings=5, segs=24, smooth=True):
    """An elliptical cap centred on assembly pixel (cu, cv) with radii (ru, rv) px: a top surface
    at height top(u, v) and a bottom at bottom(u, v), joined round the rim. The top is a grid of
    concentric rings, so it follows a curved surface."""
    before = set(bm.faces)

    def ring(t, fn):
        if t == 0:
            return [bm.verts.new((X(cu), Y(cv), fn(cu, cv)))]
        out = []
        for k in range(segs):
            a = 2 * math.pi * k / segs
            u, v = cu + ru * t * math.cos(a), cv - rv * t * math.sin(a)
            out.append(bm.verts.new((X(u), Y(v), fn(u, v))))
        return out

    ts = [i / rings for i in range(rings + 1)]
    tops = [ring(t, top) for t in ts]
    rim_bottom = ring(1.0, bottom)
    centre_bottom = ring(0.0, bottom)
    for r0, r1 in zip(tops, tops[1:]):
        for k in range(segs):
            j = (k + 1) % segs
            if len(r0) == 1:
                bm.faces.new((r0[0], r1[k], r1[j]))
            else:
                bm.faces.new((r0[k], r1[k], r1[j], r0[j]))
    rim = tops[-1]
    for k in range(segs):
        j = (k + 1) % segs
        bm.faces.new((rim[k], rim_bottom[k], rim_bottom[j], rim[j]))
        bm.faces.new((rim_bottom[j], rim_bottom[k], centre_bottom[0]))
    _tag(bm, before, mat, smooth)


def bridge(bm, r0, r1):
    """Faces between two rings of the same length (or a ring and a single centre vertex)."""
    faces = []
    n = max(len(r0), len(r1))
    for k in range(n):
        j = (k + 1) % n
        if len(r0) == 1:
            faces.append(bm.faces.new((r0[0], r1[k], r1[j])))
        elif len(r1) == 1:
            faces.append(bm.faces.new((r0[k], r1[0], r0[j])))
        else:
            faces.append(bm.faces.new((r0[k], r1[k], r1[j], r0[j])))
    return faces


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


def cut_grooves(name, part, grooves, mats, coll):
    """Cut grooves into a closed part: each groove is a closed tube (built by `grooves(bm)`, one
    bmesh per groove) subtracted with an exact boolean, its walls taking the tube's material.
    Returns the result as a new mesh."""
    target = to_object(name, part, mats, coll)
    cutters = []
    solvers = [i.identifier for i in bpy.types.BooleanModifier.bl_rna.properties["solver"].enum_items]
    for i, tube in enumerate(grooves):
        cutter = to_object(f"{name}_cut{i}", tube, mats, coll)
        cutters.append(cutter)
        mod = target.modifiers.new(f"groove{i}", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.solver = "EXACT" if "EXACT" in solvers else solvers[0]
        mod.object = cutter
        if hasattr(mod, "material_mode"):
            mod.material_mode = "INDEX"
    cutter_names = [c.name for c in cutters]
    for c in cutters:
        c.hide_render = True
    dg = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(target.evaluated_get(dg))
    for obj in [target] + [bpy.data.objects[n] for n in cutter_names]:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(data)
    return mesh


def on(lift):
    """A height function: `lift` above the ball's surface."""
    return lambda u, v: zs(u, v) + lift


# --- painting from the sprite ------------------------------------------------------------------

def sprite_grid():
    """The whole object's first frames as rows of palette indices (56 x 72, -1 = empty)."""
    lead = common.load_sprite(ROOT, "newsh9-191")
    grid = [[-1] * 72 for _ in range(56)]
    for e in lead["assemblyLayout"]:
        if e["model"] not in PIECES:
            continue
        x0, y0 = e["cx"] - CX0 + 36 - 12, e["cy"] - CY0 + 28 - 14
        rows = common.load_sprite(ROOT, e["model"])["frames"][0]["pixels"]
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                if v >= 0:
                    grid[y0 + r][x0 + c] = v
    return grid


def face_samples(grid, face, reach=2):
    """Sprite indices round a face's centre (a (2 * reach + 1)^2 px window), so neighbouring
    faces get similar shades instead of a speckle of single pixels. The sprite's 1-2 px dark
    outline is left out: the game draws its own."""
    p = face.calc_center_median()
    c0, r0 = int(math.floor(U(p.x))), int(math.floor(V(p.y)))
    out = []
    for r in range(r0 - reach, r0 + reach + 1):
        for c in range(c0 - reach, c0 + reach + 1):
            if 0 <= r < len(grid) and 0 <= c < len(grid[0]) and grid[r][c] >= 0 and not near_edge(grid, r, c):
                out.append(grid[r][c])
    return out


def near_edge(grid, r, c, d=2):
    """Is the pixel within d px of the sprite's outer edge (the bottom row is a cut, not an edge)?"""
    for rr in range(r - d, r + d + 1):
        for cc in range(c - d, c + d + 1):
            if rr >= len(grid):
                continue
            if rr < 0 or cc < 0 or cc >= len(grid[0]) or grid[rr][cc] < 0:
                return True
    return False


# The ball's armour takes one mid grey all over: the sprite's darker right side and near-black rim
# are its drawn shading and outline, which the game's light and outline make (rubric: "The
# sprite's lighting is not paint").
BALL_TONES = [7]
# The eye's lens takes one mid blue all over: its navy lower edge and teal right side are the
# sprite's shading and its near-white spots the lens's sheen, all left to the lighting.
EYE_ZONES = ((157, lambda i: True),)
EYE_TONES = [z for z, _ in EYE_ZONES]
BALL_REACH, EYE_REACH = 5, 2  # sampling windows (px either side) for the ball's and eye's shades


def nearest_shade(colors, samples, shades, keep):
    """The shade whose colour is nearest the mean colour of the samples that `keep` accepts."""
    rgbs = [colors[str(i)] for i in samples if keep(i)]
    if not rgbs:
        return None
    mean = [sum(c[k] for c in rgbs) / len(rgbs) for k in range(3)]
    return min(shades, key=lambda i: sum((colors[str(i)][k] - mean[k]) ** 2 for k in range(3)))


def ball_shade(colors, samples):
    """The armour's grey under a face (seams and studs average in at their share)."""
    return nearest_shade(colors, samples, BALL_TONES, lambda i: 1 <= i <= 15) or BALL_TONES[len(BALL_TONES) // 2]


def eye_shade(colors, samples):
    """The eye's blue under a face: the zone (EYE_ZONES) most of the samples fall in."""
    counts = [sum(1 for i in samples if keep(i)) for _, keep in EYE_ZONES]
    return EYE_ZONES[counts.index(max(counts))][0] if max(counts) else 157


# --- the machine -------------------------------------------------------------------------------

def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh9a191"
    grid = sprite_grid()
    mats, slots = [], {}

    def M(i, **kw):
        """Material slot for palette index i (one material per index)."""
        if i not in slots:
            slots[i] = len(mats)
            mats.append(common.palette_material(sprite, i, tag, **kw))
        return slots[i]

    # Painted armour plate; the swirl boss and latch rods polished metal; the blue strip a glowing
    # light; the eye a glossy lens with a faint glow; the socket, seams and pupil dark recesses.
    for i in BALL_TONES:
        M(i, metallic=0.45, roughness=0.4)
    SEAM = M(3, metallic=0.3, roughness=0.6)
    SWIRL = M(11, metallic=0.8, roughness=0.28)
    RIM = M(13, metallic=0.8, roughness=0.3)
    STRIP = M(132, metallic=0.05, roughness=0.15, emission_strength=1.0)
    PLATE = M(8, metallic=0.45, roughness=0.4)
    SOCKET = M(2, metallic=0.3, roughness=0.6)
    for i in EYE_TONES:
        M(i, metallic=0.05, roughness=0.1, emission_strength=0.1)
    PUPIL = M(97, metallic=0.0, roughness=0.95)
    CROSS = M(53, metallic=0.1, roughness=0.5)
    bm = bmesh.new()
    colors = sprite['colors']

    # The ball: a dome over the whole footprint, round to the rim, on a flat base at z = 0. Rings
    # bunch towards the rim, where the surface turns down; every face takes the armour's mid grey.
    segs, nr = 72, 16
    bb = bmesh.new()

    def ball_ring(t, z):
        if t == 0:
            return [bb.verts.new((X(BU), Y(BV), z(0.0)))]
        return [bb.verts.new((X(BU + BRU * t * math.cos(2 * math.pi * k / segs)),
                              Y(BV - BRV * t * math.sin(2 * math.pi * k / segs)), z(t))) for k in range(segs)]

    ts = [1 - (1 - i / nr) ** 1.4 for i in range(nr + 1)]
    top = [ball_ring(t, lambda t: ZT * math.sqrt(max(0.0, 1 - t * t))) for t in ts]
    under = [top[-1]] + [ball_ring(t, lambda t: -ZB * math.sqrt(max(0.0, 1 - t * t))) for t in (0.6, 0.0)]
    for r0, r1 in zip(top, top[1:]):
        for f in bridge(bb, r0, r1):
            f.material_index = slots[ball_shade(colors, face_samples(grid, f, reach=BALL_REACH))]
            f.smooth = True
    for r0, r1 in zip(under, under[1:]):
        for f in bridge(bb, r0, r1):
            f.material_index = slots[2]
            f.smooth = False

    # Seams between the armour plates: grooves about 1 px wide and 1 px deep cut into the ball,
    # their walls in the seams' dark grey.
    def groove(points, surface=zs, w=0.6, h=0.085, mat=SEAM):
        t = bmesh.new()
        sweep(t, [(u, v, 0.0, w, h) for u, v in points], sides=6, mat=mat, surface=surface, step=1.0, smooth=False)
        return t

    seams = [[(24.5, 3.0), (26.5, 6.5), (28.5, 9.6), (34.5, 9.6), (36.0, 5.5), (37.5, 2.0)],
             [(49.5, 14.2), (54.0, 14.0), (58.0, 13.6), (63.2, 13.8)],
             [(49.8, 13.0), (49.6, 20.0), (49.6, 27.0), (50.4, 35.0)],
             [(50.0, 26.0), (54.0, 25.8), (58.5, 26.2)],
             [(3.5, 20.0), (6.5, 22.0), (9.5, 24.5), (15.5, 25.6)],
             [(3.0, 38.0), (8.0, 40.0), (14.5, 43.5)],
             [(36.0, 9.8), (42.0, 9.0), (49.5, 13.0)]]
    bm.from_mesh(cut_grooves(NAME + "_ball", bb, [groove(p) for p in seams], mats, coll))

    # The plate between the swirl and the blue strip, a little raised ...
    cap(bm, 38.5, 20.5, 5.0, 9.5, lambda u, v: zs(u, v) + 0.03 + 0.05 * math.sqrt(
        max(0.0, 1 - ((u - 38.5) / 5.0) ** 2 - ((v - 20.5) / 9.5) ** 2)), on(-0.04), mat=PLATE, rings=4, segs=20)
    # ... the swirl's head: one smooth bulge about 7.5 px proud (its two bright spots are the
    # metal's sheen, left to the lighting) ...
    cap(bm, SU, SV, SRU, SRV, zswirl, on(-0.05), mat=SWIRL, rings=7, segs=36)
    # ... and its tail curling from the lower left round under the head and up to the blue strip, a
    # rounded rib about 2 px proud.
    sweep(bm, [(18.6, 38.2, 0.0, 0.0, 0.0), (20.5, 37.3, 0.02, 1.4, 0.10), (24.0, 35.7, 0.03, 1.9, 0.13),
               (29.0, 34.6, 0.03, 2.1, 0.15), (34.5, 33.0, 0.035, 2.5, 0.16), (38.0, 31.0, 0.035, 2.6, 0.16),
               (40.5, 28.5, 0.03, 2.4, 0.15), (42.0, 25.5, 0.03, 2.0, 0.13), (42.6, 23.0, 0.0, 0.0, 0.0)],
          sides=8, mat=SWIRL)

    # The blue strip curving from the top of the swirl round and down its right side: a round
    # pipe about 6.5 px wide lying on the ball, standing about 6 px proud.
    strip = [(38.6, 9.8, 0.0, 0.0), (39.2, 10.6, 2.4, 0.18), (41.0, 12.5, 3.3, 0.27),
             (43.8, 15.0, 3.3, 0.28), (45.6, 17.8, 3.2, 0.28), (46.5, 21.0, 2.9, 0.27),
             (46.6, 24.0, 2.7, 0.25), (46.6, 26.0, 2.5, 0.21), (46.6, 26.8, 0.0, 0.0)]
    sweep(bm, [(u, v, 0.8 * h if h else 0.08, w, h) for u, v, w, h in strip], sides=10, mat=STRIP)

    # A latch rod set into each flank, slanting down and in, in a dark slot.
    for path in ([(9.2, 30.5), (11.2, 34.5), (13.6, 39.6)], [(61.8, 31.0), (60.0, 34.6), (57.8, 38.6)]):
        (u0, v0), _, (u1, v1) = path
        dx = 1.4 if u0 < 36 else -1.4
        sweep(bm, [(u0 - dx, v0 + 0.4, -0.02, 0.0, 0.0)] + [(u - dx * 0.8, v + 0.3, -0.02, 1.6, 0.03) for u, v in path]
              + [(u1 - dx * 0.4, v1 + 1.0, -0.02, 0.0, 0.0)], sides=6, mat=SOCKET)
        sweep(bm, [(u0, v0, 0.05, 0.0, 0.0)] + [(u, v, 0.06, 1.0, 0.07) for u, v in path]
              + [(u1 + (u1 - u0) * 0.08, v1 + 0.6, 0.05, 0.0, 0.0)], sides=8, mat=RIM)

    # The eye: a dome standing out of the ball in a dark socket ring, with the pupil sunk into it.
    # Rings run from the pupil's edge out to the eye's rim, all in the lens's mid blue.
    S = 48
    be = bmesh.new()

    def eye_pt(k, s):
        a = 2 * math.pi * k / S
        iu, iv = PU + PRU * math.cos(a), PV - PRV * math.sin(a)
        ou, ov = EU + ERU * math.cos(a), EV - ERV * math.sin(a)
        return iu + (ou - iu) * s, iv + (ov - iv) * s

    def ring_at(uvs, fn):
        return [be.verts.new((X(u), Y(v), fn(u, v))) for u, v in uvs]

    ss = [0.0, 0.06, 0.15, 0.27, 0.40, 0.53, 0.66, 0.78, 0.88, 0.95, 1.0]
    surf = [ring_at([eye_pt(k, s) for k in range(S)], zeye) for s in ss]
    for r0, r1 in zip(surf, surf[1:]):
        for f in bridge(be, r0, r1):
            f.material_index = slots[eye_shade(colors, face_samples(grid, f, reach=EYE_REACH))]
            f.smooth = True
    # The socket ring round the eye, then a skirt into the ball and a floor under it all.
    out_uv = [(EU + (ERU + 1.2) * math.cos(2 * math.pi * k / S), EV - (ERV + 1.2) * math.sin(2 * math.pi * k / S))
              for k in range(S)]
    rim_low = ring_at([eye_pt(k, 1.0) for k in range(S)], on(0.02))
    socket_ring = ring_at(out_uv, on(0.012))
    skirt = ring_at(out_uv, on(-0.06))
    floor = [be.verts.new((X(EU), Y(EV), zs(EU, EV) - 0.06))]
    for r0, r1, mat, smooth in ((surf[-1], rim_low, SOCKET, False), (rim_low, socket_ring, SOCKET, True),
                                (socket_ring, skirt, SOCKET, False), (skirt, floor, SOCKET, False)):
        for f in bridge(be, r0, r1):
            f.material_index = mat
            f.smooth = smooth
    # The pupil: a round-bottomed port about 3 px deep.
    bowl = [surf[0]]
    for t, depth in ((0.8, 0.15), (0.45, PUPIL_DEPTH - 0.01)):
        bowl.append(ring_at([(PU + PRU * t * math.cos(2 * math.pi * k / S), PV - PRV * t * math.sin(2 * math.pi * k / S))
                             for k in range(S)], lambda u, v, d=depth: zeye(u, v) - d))
    bowl.append([be.verts.new((X(PU), Y(PV), zeye(PU, PV) - PUPIL_DEPTH))])
    for r0, r1 in zip(bowl, bowl[1:]):
        for f in bridge(be, r0, r1):
            f.material_index = PUPIL
            f.smooth = True

    # The dark cross over the eye: grooves about 1 px wide and deep, stopping at the pupil.
    lines = [[(36.5, EV - ERV + 0.9), (36.5, PV - PRV - 0.3)],
             [(EU - ERU + 1.0, 51.5), (PU - PRU - 0.3, 51.5)],
             [(PU + PRU + 0.3, 50.5), (EU + ERU - 1.0, 50.5)]]
    bm.from_mesh(cut_grooves(NAME + "_eye", be, [groove(p, surface=zeye, w=0.6, h=0.075, mat=CROSS)
                                                 for p in lines], mats, coll))

    return to_object(NAME, bm, mats, coll), slots


def keep_normals(piece, whole, offset, fill_mat):
    """Mark the faces split_assembly filled along the cuts flat and dark (material slot
    `fill_mat`, so the ball's and the eye's overlapping fills look the same), and give every smooth corner the
    uncut ball's normal (interpolated from the face under it), so the shading runs on across the
    cuts instead of creasing there."""
    from mathutils.bvhtree import BVHTree
    from mathutils.interpolate import poly_3d_calc
    mesh = piece.data
    hw, hh, eps = 1.0, 14 / 12, 1e-4
    for poly in mesh.polygons:
        vs = [mesh.vertices[i].co for i in poly.vertices]
        if any(all(abs(v.x - b) < eps for v in vs) for b in (-hw, hw)) or \
                any(all(abs(v.y - b) < eps for v in vs) for b in (-hh, hh)):
            poly.use_smooth = False
            poly.material_index = fill_mat
    src = whole.data
    # Only the smooth surfaces: a corner on a groove's lip takes the surface's normal, not the
    # groove wall's.
    smooth = [p.index for p in src.polygons if p.use_smooth]
    tree = BVHTree.FromPolygons([v.co.copy() for v in src.vertices], [list(src.polygons[i].vertices) for i in smooth])
    corner = src.corner_normals
    off = Vector((offset[0], offset[1], 0.0))
    normals = []
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            if not poly.use_smooth:
                normals.append(poly.normal.copy())
                continue
            co = mesh.vertices[mesh.loops[li].vertex_index].co + off
            hit, _, fi, _ = tree.find_nearest(co)
            sp = src.polygons[smooth[fi]]
            w = poly_3d_calc([src.vertices[v].co for v in sp.vertices], hit)
            nrm = Vector()
            for wk, lk in zip(w, sp.loop_indices):
                nrm += wk * corner[lk].vector
            normals.append(nrm.normalized() if nrm.length > 1e-6 else poly.normal.copy())
    mesh.normals_split_custom_set(normals)


def merged_sprite():
    """newsh9-191's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsh9-191")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(layout, out):
    """The whole object's sprite (first frames) as one image, padded to the 24:28 shape that
    render_preview expects for size 6 (72 x 84 px, the object in the middle)."""
    import numpy as np
    img = np.zeros((84, 72, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(ROOT, name)
        frame = data["frames"][0]
        x0, y0 = cx + 36 - 12, cy + 42 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 72, 84, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    obj, slots = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name, cx, cy in layout:
        keep_normals(pieces[name], obj, (cx / 12, -cy / 12), slots[2])
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(layout, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=6, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
