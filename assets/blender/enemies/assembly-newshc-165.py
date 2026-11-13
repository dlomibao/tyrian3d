"""assembly-newshc-165, a reactor orb in a plasma ring, and the blue gun pod it escorts.

Pieces (24x28 px each, the column orb / pod / orb of 3.5 BONUS; the second orb is the same model):
- newshc-165, the REACTOR ORB (frames 165/167/169). It flies on its own (114 orbs stream up from
  the bottom edge) and rides rigidly above and below the gun pod, so it is a self-contained floating
  object: a blue armoured sphere split north-south by a slot (two glossy half shells, plan a
  superellipse 16 x 10 px, n = 3), a dark web joining the halves at the bottom of the slot and a
  pink core rail lying in it along the meridian, plugged into dark sockets at both ends. Round it, at
  the equator, a ring of red-orange plasma in two crescents (thick north and south, tapering to the
  east and west where the ring is open). The plasma is emissive palette (D126: metallic 1, rough):
  body 119, a hot crest 122 along the middle, the inner flank 117; frames 167/169 brighten every
  arc pixel 2 and 4 palette steps (palette_material frames=) and the sprite's ring also SWELLS on
  those frames (sparks along its inner edge), so the crescents are three frame parts (D17), each
  fitted to its own frame's inner mask (polar fit, smoothed), with its own outline shell.
- newshc-155, the GUN POD (frames 155/157/159): two blue armour lobes at the back with green light
  panels over their outer corners (39, and a lamp strip 38, brightening on 157/159), a purple cannon
  between the lobes tilted up toward the bottom of the screen (its bore is the dark ellipse), a grey
  housing across the middle with a sloped front and a dark vent each side, and a grey fork hanging
  south (two rails, a crossbar, a centre piston) where the lower orb couples.

Units: sprite px. c east (column edge), r south (row edge), h up. Blender X = (c - 12) / 12,
Y = (14 - r) / 12, Z = h / 12 (each piece centred on its own 24x28 box).

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshc-165.py [-- --measure] [--renders]
Exports public/models/enemies/newshc-165.glb and newshc-155.glb with their spriteModels entries.
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import sprite_mask as SM  # noqa: E402

HERE = Path(tempfile.gettempdir()) / "assembly-newshc-165"  # the review glb, --measure and --renders output
HERE.mkdir(parents=True, exist_ok=True)
OUT_GLB = HERE / "assembly-newshc-165.glb"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
U = 1 / 12
REF = WT / "reference" / "models"

ORB_FRAMES = [165, 167, 169]
POD_FRAMES = [155, 157, 159]


def P(c, r, h):
    return Vector(((c - 12) * U, (14 - r) * U, h * U))


def sgnpow(v, p):
    return math.copysign(abs(v) ** p, v)


# --------------------------------------------------------------------------------------------------
# Materials (pal_<index>_<tag>; game colour from the live palette)

def load_sprite(name):
    return common.load_sprite(WT, name)


SPR = {n: load_sprite(n) for n in ("newshc-165", "newshc-155")}


def pm(sprite, idx, tag, metallic=0.3, roughness=0.5, glow=0.0, frames=None, spec=None):
    m = common.palette_material(SPR[sprite], idx, tag, metallic=metallic, roughness=roughness,
                                emission_strength=glow, frames=frames)
    if spec is not None:  # D176: F0 through Specular IOR Level for polished surfaces
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        for key in ("Specular IOR Level", "Specular"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = spec
                break
    return m


def orb_materials():
    s = "newshc-165"
    return {
        "shell": pm(s, 58, "a165-shell", metallic=0.55, roughness=0.22, spec=0.8),
        "seam": pm(s, 54, "a165-seam", metallic=0.5, roughness=0.4),
        "wall": pm(s, 52, "a165-wall", metallic=0.4, roughness=0.5),
        "web": pm(s, 51, "a165-web", metallic=0.4, roughness=0.55),
        "rail": pm(s, 72, "a165-rail", metallic=0.6, roughness=0.25, glow=0.25, spec=0.8),
        "socket": pm(s, 65, "a165-socket", metallic=0.5, roughness=0.45),
        # plasma (D126/D173: glow surfaces metallic 1, rough); +2 / +4 palette steps on 167 / 169
        "arc": pm(s, 116, "a165-arc", metallic=1.0, roughness=0.8, glow=1.0, frames={167: 118, 169: 120}),
        "hot": pm(s, 121, "a165-hot", metallic=1.0, roughness=0.8, glow=1.1, frames={167: 123, 169: 125}),
        "arcin": pm(s, 117, "a165-arcin", metallic=1.0, roughness=0.8, glow=0.9, frames={167: 119, 169: 121}),
    }


def pod_materials():
    s = "newshc-155"
    return {
        "hood": pm(s, 55, "a155-hood", metallic=0.5, roughness=0.3, spec=0.7),
        "hoodlip": pm(s, 53, "a155-hoodlip", metallic=0.45, roughness=0.4),
        "panel": pm(s, 39, "a155-panel", metallic=0.4, roughness=0.45, glow=0.3, frames={157: 41, 159: 42}),
        "lamp": pm(s, 38, "a155-lamp", metallic=1.0, roughness=0.7, glow=1.0, frames={157: 43, 159: 202}),
        "barrel": pm(s, 89, "a155-barrel", metallic=0.5, roughness=0.3, spec=0.7),
        "collar": pm(s, 91, "a155-collar", metallic=0.5, roughness=0.3),
        "band": pm(s, 86, "a155-band", metallic=0.45, roughness=0.4),
        "bore": pm(s, 82, "a155-bore", metallic=0.3, roughness=0.7),
        "housing": pm(s, 103, "a155-housing", metallic=0.6, roughness=0.32),
        "housing_dk": pm(s, 102, "a155-housingdk", metallic=0.55, roughness=0.4),
        "vent": pm(s, 98, "a155-vent", metallic=0.4, roughness=0.6),
        "slat": pm(s, 101, "a155-slat", metallic=0.5, roughness=0.45),
        "rail": pm(s, 6, "a155-rail", metallic=0.6, roughness=0.35),
        "bar": pm(s, 5, "a155-bar", metallic=0.55, roughness=0.4),
        "piston": pm(s, 7, "a155-piston", metallic=0.7, roughness=0.25),
        "tray": pm(s, 2, "a155-tray", metallic=0.4, roughness=0.6),
    }


# --------------------------------------------------------------------------------------------------
# Geometry accumulator

class Geo:
    def __init__(self):
        self.v = []
        self.f = []  # (vert ids, material key, smooth)

    def add_v(self, p):
        self.v.append(Vector(p))
        return len(self.v) - 1

    def face(self, ids, mat, smooth=True):
        self.f.append((list(ids), mat, smooth))

    def grid(self, rings, mats, closed=True, cap0=None, cap1=None, smooth=True):
        """rings: list of point lists (same length). mats: key or fn(i_ring, j) -> key."""
        ids = [[self.add_v(p) for p in ring] for ring in rings]
        n = len(rings[0])
        for i in range(len(rings) - 1):
            for j in range(n if closed else n - 1):
                j2 = (j + 1) % n
                m = mats(i, j) if callable(mats) else mats
                self.face([ids[i][j], ids[i][j2], ids[i + 1][j2], ids[i + 1][j]], m, smooth)
        for ring_ids, cap, rev in ((ids[0], cap0, True), (ids[-1], cap1, False)):
            if cap is not None:
                c = sum((self.v[k] for k in ring_ids), Vector()) / len(ring_ids)
                ci = self.add_v(c)
                for j in range(n):
                    j2 = (j + 1) % n
                    tri = [ring_ids[j], ring_ids[j2], ci]
                    self.face(tri[::-1] if rev else tri, cap, smooth)
        return ids

    def add_bm(self, bm, keymap):
        base = len(self.v)
        bm.verts.index_update()
        for v in bm.verts:
            self.v.append(v.co.copy())
        for f in bm.faces:
            self.f.append(([base + v.index for v in f.verts], keymap[f.material_index], f.smooth))

    def to_bm(self, keys):
        bm = bmesh.new()
        vs = [bm.verts.new(p) for p in self.v]
        for ids, m, sm in self.f:
            try:
                f = bm.faces.new([vs[i] for i in ids])
            except ValueError:
                continue
            f.material_index = keys.index(m)
            f.smooth = sm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        return bm

    def to_object(self, name, mats, coll, auto_smooth=40.0):
        keys = list(mats.keys())
        bm = self.to_bm(keys)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for k in keys:
            me.materials.append(mats[k])
        o = bpy.data.objects.new(name, me)
        coll.objects.link(o)
        # drop unused slots
        used = sorted({p.material_index for p in me.polygons})
        remap = {u: i for i, u in enumerate(used)}
        orig = [p.material_index for p in me.polygons]
        for i in reversed(range(len(me.materials))):
            if i not in used:
                me.materials.pop(index=i)
        for p, mi in zip(me.polygons, orig):  # pop() shifts the indices: set them afterwards
            p.material_index = remap[mi]
        try:
            bpy.context.view_layer.objects.active = o
            o.select_set(True)
            bpy.ops.object.shade_auto_smooth(angle=math.radians(auto_smooth))
            o.select_set(False)
        except Exception:
            pass
        return o


def sweep(g, path, sides, mat, cap=True, up=Vector((0, 0, 1))):
    """Tube along path [(Vector centre, half_w, half_h)]; half sizes in px."""
    rings = []
    for i, (c, hw, hh) in enumerate(path):
        a = path[max(0, i - 1)][0]
        b = path[min(len(path) - 1, i + 1)][0]
        t = (b - a).normalized()
        side = t.cross(up)
        if side.length < 1e-6:
            side = t.cross(Vector((0, 1, 0)))
        side.normalize()
        nrm = side.cross(t).normalized()
        rings.append([c + side * (hw * U * math.cos(2 * math.pi * k / sides)) +
                      nrm * (hh * U * math.sin(2 * math.pi * k / sides)) for k in range(sides)])
    g.grid(rings, mat, cap0=mat if cap else None, cap1=mat if cap else None)


def bm_from_rings(rings, cap0=True, cap1=True):
    g = Geo()
    g.grid(rings, 0, cap0=0 if cap0 else None, cap1=0 if cap1 else None)
    return g.to_bm([0])


# --------------------------------------------------------------------------------------------------
# newshc-165: the reactor orb

ORB_A, ORB_B, ORB_N = 8.0, 5.0, 3.0  # plan half width/height (px), superellipse exponent
ORB_ZC, ORB_RZ = 6.5, 6.0           # centre height, vertical radius (px)
SLOT = 2.0                          # slot half width (px): columns 10-13


def orb_point(t, phi, a=ORB_A, b=ORB_B, zc=ORB_ZC, rz=ORB_RZ, grooves=True):
    k = max(math.cos(phi), 0.0) ** 0.75
    if grooves:  # an equatorial seam and a crown seam (modelled panel lines)
        for p0, w, d in ((0.0, 0.07, 0.035), (0.95, 0.05, 0.03)):
            k *= 1 - d * max(0.0, 1 - abs(phi - p0) / w)
    x = a * k * sgnpow(math.cos(t), 2 / ORB_N)
    y = b * k * sgnpow(math.sin(t), 2 / ORB_N)
    z = zc + rz * math.sin(phi)
    return P(12 + x, 14 - y, z)


def orb_body(g):
    nt, nphi = 40, 16
    phis = [-math.pi / 2 + math.pi * i / nphi for i in range(1, nphi)]
    # seam rings exactly at the grooves
    phis = sorted(set(phis + [-0.07, 0.0, 0.07, 0.9, 0.95, 1.0]))
    rings = [[orb_point(2 * math.pi * j / nt, ph) for j in range(nt)] for ph in phis]
    bm = bm_from_rings(rings)
    for f in bm.faces:
        f.smooth = True
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(SLOT * U, 0, 0), plane_no=(1, 0, 0), clear_inner=True)
    edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    filled = bmesh.ops.holes_fill(bm, edges=edges, sides=0)["faces"]
    bmesh.ops.triangulate(bm, faces=filled)
    walls = {f for f in bm.faces if abs(f.normal.x + 1) < 1e-3 or all(abs(v.co.x - SLOT * U) < 1e-5 for v in f.verts)}
    # seam faces: the groove bands
    for f in bm.faces:
        if f in walls:
            f.material_index = 1
            f.smooth = False
        else:
            zc = f.calc_center_median().z / U
            ph = math.asin(max(-1, min(1, (zc - ORB_ZC) / ORB_RZ)))
            f.material_index = 2 if (abs(ph) < 0.06 or abs(ph - 0.95) < 0.045) else 0
    keymap = {0: "shell", 1: "wall", 2: "seam"}
    # chamfer the slot lip (a machined edge, not a knife edge)
    lip = [e for e in bm.edges if all(abs(v.co.x - SLOT * U) < 1e-5 for v in e.verts) and
           any(f.material_index == 1 for f in e.link_faces) and any(f.material_index != 1 for f in e.link_faces)]
    try:
        bmesh.ops.bevel(bm, geom=lip, offset=0.35 * U, segments=2, affect="EDGES", profile=0.5)
    except Exception:
        pass
    g.add_bm(bm, keymap)
    # mirror for the west half
    base = len(g.v)
    for v in bm.verts:
        g.v.append(Vector((-v.co.x, v.co.y, v.co.z)))
    bm.verts.index_update()
    for f in bm.faces:
        g.f.append(([base + v.index for v in reversed(f.verts)], keymap[f.material_index], f.smooth))
    bm.free()


def orb_web(g):
    """Dark web filling the bottom of the slot, joining the two halves."""
    nt, nphi = 32, 10
    phis = [-math.pi / 2 + math.pi * i / nphi for i in range(1, nphi)]
    rings = [[orb_point(2 * math.pi * j / nt, ph, a=ORB_A - 0.3, b=ORB_B - 0.25, rz=ORB_RZ - 2.4, grooves=False)
              for j in range(nt)] for ph in phis]
    bm = bm_from_rings(rings)
    for sgn in (1, -1):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(sgn * (SLOT + 0.05) * U, 0, 0),
                                     plane_no=(sgn, 0, 0), clear_outer=True)
        edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    for f in bm.faces:
        f.smooth = abs(f.normal.x) < 0.9
    g.add_bm(bm, {0: "web"})
    bm.free()


def orb_rail(g):
    """The pink core spindle: a straight rod lying in the slot from end to end of the orb (rows
    9-18), held in a dark bearing cap at each end (the 64/65 pixels)."""
    zc = ORB_ZC + 3.7
    ys = [-4.75, -4.55, -4.2, -2.0, 0.0, 2.0, 4.2, 4.55, 4.75]
    path = []
    for y in ys:
        rr = 0.55 if abs(y) > 4.6 else 1.0
        path.append((P(12, 14 - y, zc), rr, rr * 0.85))
    sweep(g, path[1:-1], 12, "rail")
    for sgn in (-1, 1):
        sweep(g, [(P(12, 14 - sgn * 3.9, zc), 1.15, 1.05), (P(12, 14 - sgn * 4.3, zc), 1.2, 1.1),
                  (P(12, 14 - sgn * 4.75, zc), 1.05, 0.95), (P(12, 14 - sgn * 4.95, zc), 0.6, 0.55)], 12, "socket")


def polar_fit(frame):
    """r_in(theta), r_out(theta) of the plasma ring on this frame's rule mask (inner + free)."""
    data = json.loads((REF / "newshc-165" / "sprite.json").read_text())
    rows = {f["index"]: SM._rows(f) for f in data["frames"]}
    idx = rows[frame]
    colors = SM._colors(data)
    partners = SM.pulse_partners(idx, list(rows.values()))
    m = SM.masks(idx, colors, partners)
    tgt = [[a or b for a, b in zip(ra, rb)] for ra, rb in zip(m["inner"], m["free"])]
    nth = 120
    rin, rout = [], []
    for i in range(nth):
        th = 2 * math.pi * i / nth
        hits = []
        r = 6.0
        while r < 16.5:
            c = 12 + r * math.cos(th)
            rr = 14 - r * math.sin(th)
            ci, ri = int(math.floor(c)), int(math.floor(rr))
            if 0 <= ci < 24 and 0 <= ri < 28 and tgt[ri][ci] and idx[ri][ci] >= 112:
                hits.append(r)
            r += 0.02
        if hits:
            rin.append(min(hits))
            rout.append(max(hits) + 0.02)
        else:
            rin.append(None)
            rout.append(None)
    return rin, rout


def smooth_runs(vals, win=3):
    n = len(vals)
    out = list(vals)
    for i in range(n):
        if vals[i] is None:
            continue
        acc = [vals[(i + k) % n] for k in range(-win, win + 1) if vals[(i + k) % n] is not None]
        out[i] = sum(acc) / len(acc)
    return out


def ring_parts(frame, shrink_in=0.0, shrink_out=0.0):
    """The two crescents of this frame: Geo per crescent (north, south)."""
    rin, rout = polar_fit(frame)
    rin, rout = smooth_runs(rin), smooth_runs(rout)
    n = len(rin)
    sides = 12
    # runs: north = theta in (0, pi), south = (pi, 2pi)
    out = []
    for lo, hi in ((0, n // 2), (n // 2, n)):
        sts = []
        for i in range(lo, hi):
            if rin[i] is None:
                continue
            a, b = rin[i] + shrink_in, rout[i] - shrink_out
            w = b - a
            if w < 0.6:
                continue
            sts.append((2 * math.pi * i / n, a, b))
        if not sts:
            continue
        rings = []
        mats_by_j = []
        for j in range(sides):
            s = 2 * math.pi * (j + 0.5) / sides
            if abs(math.atan2(math.sin(s - math.pi / 2), math.cos(s - math.pi / 2))) < 0.75:
                mats_by_j.append("hot")
            elif math.cos(s) < -0.35:
                mats_by_j.append("arcin")
            else:
                mats_by_j.append("arc")

        def section(th, a, b, scale=1.0):
            rm, hw = (a + b) / 2, (b - a) / 2 * scale
            hh = min(max(0.5 * (b - a), 0.6), 2.6) * scale
            pts = []
            for j in range(sides):
                s = 2 * math.pi * j / sides
                cs, sn = math.cos(s), math.sin(s)
                rr = rm + hw * sgnpow(cs, 0.8)
                z = ORB_ZC + hh * sgnpow(sn, 0.85)
                pts.append(P(12 + rr * math.cos(th), 14 - rr * math.sin(th), z))
            return pts

        th0, a0, b0 = sts[0]
        th1, a1, b1 = sts[-1]
        step = 2 * math.pi / n
        rings.append(section(th0 - step * 0.6, a0, b0, 0.05))
        rings.append(section(th0 - step * 0.35, a0, b0, 0.6))
        for th, a, b in sts:
            rings.append(section(th, a, b))
        rings.append(section(th1 + step * 0.35, a1, b1, 0.6))
        rings.append(section(th1 + step * 0.6, a1, b1, 0.05))
        g = Geo()
        g.grid(rings, lambda i, j: mats_by_j[j], cap0="arc", cap1="arc")
        out.append(g)
    return out


# --------------------------------------------------------------------------------------------------
# newshc-155: the gun pod

LOBE_C, LOBE_R, LOBE_A, LOBE_B, LOBE_N = 6.0, 6.6, 5.0, 3.6, 2.6
LOBE_Z0, LOBE_RZ = 1.0, 5.2


def lobe_point(side, t, phi, grow=0.0):
    k = max(math.cos(phi), 0.0) ** 0.55
    x = (LOBE_A + grow) * k * sgnpow(math.cos(t), 2 / LOBE_N)
    y = (LOBE_B + grow) * k * sgnpow(math.sin(t), 2 / LOBE_N)
    z = LOBE_Z0 + (LOBE_RZ + grow) * math.sin(phi)
    c = 12 + side * (12 - LOBE_C) * -1 if False else (LOBE_C if side < 0 else 24 - LOBE_C)
    return P(c + x, LOBE_R - y, z)


def pod_lobes(g):
    nt, nphi = 40, 12
    for side in (-1, 1):
        phis = [0.0] + [math.pi / 2 * i / nphi for i in range(1, nphi)]
        rings = [[lobe_point(side, 2 * math.pi * j / nt, ph) for j in range(nt)] for ph in phis]
        # drop the skirt to the housing at z 0.6 (closed base)
        rings.insert(0, [Vector((p.x, p.y, 0.6 * U)) for p in rings[0]])
        g.grid(rings, lambda i, j: "hoodlip" if i == 0 else "hood", cap0="hoodlip", cap1="hood")
        # green light panel over the outer corner: a raised plate following the lobe
        if side < 0:
            t0, t1 = math.radians(95), math.radians(205)
        else:
            t0, t1 = math.radians(-25), math.radians(85)
        p0, p1 = 0.05, 1.3
        nu, nv = 18, 8
        top, bot = [], []
        for i in range(nv + 1):
            ph = p0 + (p1 - p0) * i / nv
            top.append([lobe_point(side, t0 + (t1 - t0) * j / nu, ph, 0.32) for j in range(nu + 1)])
            bot.append([lobe_point(side, t0 + (t1 - t0) * j / nu, ph, -0.15) for j in range(nu + 1)])
        tid = [[g.add_v(p) for p in row] for row in top]
        bid = [[g.add_v(p) for p in row] for row in bot]
        for i in range(nv):
            for j in range(nu):
                g.face([tid[i][j], tid[i][j + 1], tid[i + 1][j + 1], tid[i + 1][j]], "panel")
        edge = [(tid[0][j], bid[0][j]) for j in range(nu + 1)]
        edge += [(tid[i][nu], bid[i][nu]) for i in range(1, nv + 1)]
        edge += [(tid[nv][j], bid[nv][j]) for j in range(nu - 1, -1, -1)]
        edge += [(tid[i][0], bid[i][0]) for i in range(nv - 1, 0, -1)]
        for k in range(len(edge)):
            (a, b), (c, d) = edge[k], edge[(k + 1) % len(edge)]
            g.face([a, c, d, b], "panel", False)
        # lamp strip on the panel's outer edge (pixels c2-3, rows 4-6 and mirrored)
        tl = [math.radians(a) for a in ((130, 145, 160, 172) if side < 0 else (50, 35, 20, 8))]
        path = [(lobe_point(side, t, 0.45, 0.36), 0.55, 0.3) for t in tl]
        sweep(g, path, 8, "lamp")


def pod_barrel(g):
    alpha = math.radians(26)
    axis = Vector((0, -math.cos(alpha), math.sin(alpha)))  # toward the bottom of the screen and up
    muzzle = P(12, 11.5, 6.6)
    L = 6.8
    r = 2.95

    def ring(c, rad, n=24):
        side = Vector((1, 0, 0))
        up = side.cross(axis).normalized()
        return [c + side * (rad * U * math.cos(2 * math.pi * k / n)) + up * (rad * U * math.sin(2 * math.pi * k / n))
                for k in range(n)]
    rear = muzzle - axis * L * U
    st = [(0.0, 2.55), (0.5, 2.75), (3.0, 2.75), (3.1, 2.55), (3.6, 2.55), (3.7, 2.75), (L - 1.4, 2.75),
          (L - 1.3, r), (L, r)]
    mats = ["barrel", "barrel", "band", "band", "band", "barrel", "barrel", "collar"]
    rings = [ring(rear + axis * d * U, rad) for d, rad in st]
    # muzzle face annulus then the bore
    rings.append(ring(muzzle, 2.25))
    rings.append(ring(muzzle - axis * 2.2 * U, 2.25))
    mats += ["collar", "bore"]
    g.grid(rings, lambda i, j: mats[min(i, len(mats) - 1)], cap0="barrel", cap1="bore")
    # breech: a rounded mantlet block the barrel comes out of, between the lobes
    mant = []
    for d, rad in ((-1.6, 2.2), (-1.0, 3.0), (0.0, 3.05), (0.8, 2.9)):
        c = rear + axis * d * U
        mant.append(ring(c, rad))
    g.grid(mant, "hood", cap0="hood", cap1="hood")


def housing_profile(r):
    """(top height, half width) of the grey housing at row edge r."""
    pts = [(9.0, 4.0, 10.95), (10.4, 4.9, 11.0), (11.3, 5.2, 11.0), (12.2, 4.7, 11.0), (13.3, 3.8, 10.95), (14.0, 3.3, 10.1),
           (15.0, 2.6, 10.3), (16.4, 1.7, 9.9), (17.3, 0.9, 9.3), (17.6, 0.4, 9.0)]
    for (r0, h0, w0), (r1, h1, w1) in zip(pts, pts[1:]):
        if r0 <= r <= r1:
            t = (r - r0) / (r1 - r0)
            return h0 + (h1 - h0) * t, w0 + (w1 - w0) * t
    return pts[-1][1], pts[-1][2]


def pod_housing(g):
    rows = [9.0, 9.7, 10.4, 10.9, 11.3, 11.8, 12.2, 12.9, 13.6, 14.3, 15.0, 15.7, 16.4, 16.9, 17.3, 17.6]
    ch = 0.7
    rings = []
    for r in rows:
        h, w = housing_profile(r)
        sec = [(-w, 0.0), (w, 0.0), (w, h - ch), (w - ch, h), (-(w - ch), h), (-w, h - ch)]
        rings.append([P(12 + x, r, z) for x, z in sec])
    g.grid(rings, lambda i, j: "housing" if j in (2, 3, 4) else "housing_dk", cap0="housing_dk",
           cap1="housing_dk", smooth=False)
    # vents on the sloped front, each side of the fork: a raised grey frame round a dark grille
    for sgn in (-1, 1):
        c0, c1 = (2.7, 6.9) if sgn < 0 else (17.1, 21.3)
        r0, r1 = 13.7, 16.7

        def on(c, r, lift):
            h, _ = housing_profile(r)
            return P(c, r, h + lift)
        # frame
        for (ca, ra, cb, rb) in ((c0, r0, c1, r0 + 0.6), (c0, r1 - 0.6, c1, r1), (c0, r0, c0 + 0.6, r1),
                                 (c1 - 0.6, r0, c1, r1)):
            quad_box(g, on, ca, ra, cb, rb, -0.2, 0.35, "housing")
        quad_box(g, on, c0 + 0.6, r0 + 0.6, c1 - 0.6, r1 - 0.6, -0.4, -0.05, "vent")
        for k in range(3):
            rr = r0 + 1.05 + k * 0.85
            quad_box(g, on, c0 + 0.6, rr, c1 - 0.6, rr + 0.32, -0.2, 0.12, "slat")


def quad_box(g, on, c0, r0, c1, r1, z0, z1, mat, n=3):
    """A block on a surface: on(c, r, lift) gives the surface point; plan rectangle c0..c1 x r0..r1."""
    rings = []
    for k in range(n + 1):
        r = r0 + (r1 - r0) * k / n
        rings.append([on(c0, r, z0), on(c1, r, z0), on(c1, r, z1), on(c0, r, z1)])
    g.grid(rings, mat, cap0=mat, cap1=mat, smooth=False)


def pod_fork(g):
    """The coupling fork hanging south: two rails, a crossbar, a piston, a dark tray between."""
    def cbox(c0, c1, r0, r1, h0, h1, mat, chz=0.3):
        sec = [(c0, h0), (c1, h0), (c1, h1 - chz), (c1 - chz, h1), (c0 + chz, h1), (c0, h1 - chz)]
        rings = [[P(c, r, h) for c, h in sec] for r in (r0, r1)]
        g.grid(rings, mat, cap0=mat, cap1=mat, smooth=False)
    for c0, c1 in ((8.15, 10.0), (14.0, 15.85)):
        # rail: drops from the housing front to a low run, rounded off at the south end
        cbox(c0, c1, 14.0, 21.9, 0.3, 2.7, "rail", 0.45)
    # crossbar (rows 21.6-23.6), plan narrowing to columns 9-15 at the bottom row
    sec_r = [(21.4, 8.15, 15.85), (22.6, 8.3, 15.7), (23.25, 8.9, 15.1), (23.6, 9.6, 14.4)]
    rings = []
    for r, ca, cb in sec_r:
        rings.append([P(ca, r, 0.3), P(cb, r, 0.3), P(cb, r, 2.2), P(cb - 0.4, r, 2.55), P(ca + 0.4, r, 2.55),
                      P(ca, r, 2.2)])
    g.grid(rings, "bar", cap0="bar", cap1="bar", smooth=False)
    # dark tray inside the U
    cbox(10.0, 14.0, 15.5, 21.6, 0.2, 0.7, "tray", 0.1)
    # piston: a round rod from the housing down the middle, its foot in the crossbar
    path = [(P(12, r, 1.75), 1.15, 1.0) for r in (13.0, 15.0, 17.0, 19.0, 21.8)]
    sweep(g, path, 12, "piston")
    path = [(P(12, r, 1.75), 1.45, 1.3) for r in (15.6, 16.6)]
    sweep(g, path, 12, "bar")


# --------------------------------------------------------------------------------------------------
# Outline shells (D51/D90/D118): from a sealed copy, ink on the silhouette only

def shell_of(objs, coll, name, voxel=0.016, faces=2500, inside=0.004):
    me = bpy.data.meshes.new(name + "_seal")
    bm = bmesh.new()
    for o in objs:
        bm.from_mesh(o.data)
    bm.to_mesh(me)
    bm.free()
    seal = bpy.data.objects.new(name, me)
    coll.objects.link(seal)
    shell = common.outline_shell(seal, coll, voxel=voxel, faces=faces, smooth=4, inside=inside)
    bpy.data.objects.remove(seal, do_unlink=True)
    return shell


# --------------------------------------------------------------------------------------------------
# Build

def build(coll):
    om = orb_materials()
    g = Geo()
    orb_body(g)
    orb_web(g)
    orb_rail(g)
    orb = g.to_object("newshc-165_orb", om, coll)
    orb_parts = [orb]
    orb_shells = [shell_of([orb], coll, "newshc-165_orb")]
    rings = {}
    for f in ORB_FRAMES:
        objs = []
        for k, rg in enumerate(ring_parts(f)):
            o = rg.to_object(f"newshc-165_ring{f}_{'ns'[k]}", om, coll, auto_smooth=60)
            common.frame_part(o, [f])
            objs.append(o)
            sh = shell_of([o], coll, f"newshc-165_ring{f}_{'ns'[k]}", voxel=0.012, faces=1500, inside=0.0)
            common.frame_part(sh, [f])
            orb_shells.append(sh)
        rings[f] = objs
        orb_parts += objs

    pmats = pod_materials()
    g = Geo()
    pod_lobes(g)
    pod_barrel(g)
    pod_housing(g)
    pod_fork(g)
    pod = g.to_object("newshc-155_pod", pmats, coll)
    pod_shells = [shell_of([pod], coll, "newshc-155_pod", voxel=0.02, faces=3000)]
    return dict(orb=orb, rings=rings, orb_parts=orb_parts, orb_shells=orb_shells, pod=pod, pod_shells=pod_shells)


# --------------------------------------------------------------------------------------------------
# Rendering / measuring

def setup(px_w, px_h, flat=False, transparent=False):
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "WORKBENCH" in e)
    sh = scene.display.shading
    sh.light = "FLAT" if flat else "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_cavity = not flat
    sh.show_shadows = False
    sh.show_specular_highlight = not flat
    sh.show_object_outline = False
    scene.render.resolution_x, scene.render.resolution_y = px_w, px_h
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = transparent
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.color = (0.03, 0.03, 0.04)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = 0.0 if flat else 0.6


def set_frame_colours(objs, frame):
    for o in objs:
        for m in o.data.materials:
            if m is None:
                continue
            rgb = m.get("tyrian_frame_rgb")
            base = m.get("_base_rgb")
            if base is None:
                base = list(m.diffuse_color[:3])
                m["_base_rgb"] = base
            col = list(rgb[str(frame)]) if rgb is not None and str(frame) in rgb else list(base)
            m.diffuse_color = (*col, 1.0)


def visible_for(objs, frame):
    return [o for o in objs if "tyrian_frames" not in o or int(frame) in list(o["tyrian_frames"])]


def render(objs, path, loc, look, ortho=None, lens=50, size=(480, 480), up="Y", flat=False, transparent=False):
    scene = bpy.context.scene
    setup(*size, flat=flat, transparent=transparent)
    keep = set(objs)
    for o in scene.objects:
        o.hide_render = o not in keep
    cd = bpy.data.cameras.new("cam")
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    cd.clip_end = 200
    cam = bpy.data.objects.new("cam", cd)
    scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", up).to_euler()
    scene.camera = cam
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.cameras.remove(cd)


def top_mask(objs, path, k=8):
    render(objs, path, (0, 0, 20), (0, 0, 0), ortho=28 * U, size=(24 * k, 28 * k), flat=True, transparent=True)


def main():
    coll = common.reset_collection("A_newshc165")
    B = build(coll)
    orb_all = B["orb_parts"] + B["orb_shells"]
    pod_all = [B["pod"]] + B["pod_shells"]

    tris = {}
    for key, objs in (("newshc-165", B["orb_parts"]), ("newshc-155", [B["pod"]])):
        n = 0
        for o in objs:
            for p in o.data.polygons:
                n += len(p.vertices) - 2
        tris[key] = n
    print("TRIS", tris, "per orb frame",
          {f: sum(len(p.vertices) - 2 for o in [B["orb"]] + B["rings"][f] for p in o.data.polygons) for f in ORB_FRAMES})

    # piece roots
    r165 = bpy.data.objects.new("newshc-165", None)
    r155 = bpy.data.objects.new("newshc-155", None)
    for r in (r165, r155):
        coll.objects.link(r)
    for o in orb_all:
        o.parent = r165
    for o in pod_all:
        o.parent = r155

    for name, root_obj, objs in (("newshc-165", r165, orb_all), ("newshc-155", r155, pod_all)):
        common.export_sprite_model(WT, [root_obj] + objs, f"enemies/{name}", common.load_sprite(WT, name)["sprites"])
    r155.location = (2.5, 0, 0)
    common.export_glb([r165, r155] + orb_all + pod_all, OUT_GLB)
    r155.location = (0, 0, 0)
    print("exported", OUT_GLB)

    rd = HERE / "renders"
    rd.mkdir(exist_ok=True)
    if "--measure" in ARGS:
        for f in ORB_FRAMES:
            top_mask(visible_for(B["orb_parts"], f), rd / f"top_165_{f}.png")
        top_mask([B["pod"]], rd / "top_155.png")
        # colour ids: flat render with each material on a unique id colour
        ids = {}
        objs = B["orb_parts"] + [B["pod"]]
        mats = []
        for o in objs:
            for m in o.data.materials:
                if m not in mats:
                    mats.append(m)
        saved = {m.name: tuple(m.diffuse_color) for m in mats}
        for i, m in enumerate(mats):
            rgb = ((i + 1) * 37 % 256 / 255, (i + 1) * 91 % 256 / 255, (i + 1) * 157 % 256 / 255)
            m.diffuse_color = (*rgb, 1.0)
            enc = lambda c: 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
            ids[m.name] = [round(enc(v) * 255) for v in rgb]
        bpy.context.scene.view_settings.view_transform = "Standard"
        for f in ORB_FRAMES:
            top_mask(visible_for(B["orb_parts"], f), rd / f"ids_165_{f}.png")
        top_mask([B["pod"]], rd / "ids_155.png")
        for m in mats:
            m.diffuse_color = saved[m.name]
        (rd / "ids.json").write_text(json.dumps(ids))
        print("measured")

    if "--renders" in ARGS:
        # whole column: orb (north), pod, orb (south), as the stack flies
        col = common.reset_collection("A_column")
        stack = []
        for dy, src in ((28, orb_all), (0, pod_all), (-28, orb_all)):
            for o in src:
                if "tyrian_outline" in o:
                    continue
                c = o.copy()
                c.data = o.data
                c.parent = None
                c.location = (0, dy * U, 0)
                col.objects.link(c)
                stack.append(c)
        f = 169 if "--hot" in ARGS else 165
        set_frame_colours(stack, f)
        vis = visible_for(stack, f)
        zc = 4 * U
        render(vis, rd / "col_top.png", (0, 0, 20), (0, 0, 0), ortho=90 * U, size=(300, 900))
        render(vis, rd / "col_side.png", (20, 0, zc), (0, 0, zc), ortho=90 * U, size=(900, 300), up="Y")
        orbv = [o for o in vis if abs(o.location.y - 28 * U) < 1e-6]
        podv = [o for o in vis if abs(o.location.y) < 1e-6]
        for name, objs, cy in (("orb", orbv, 28 * U), ("pod", podv, 0.0)):
            render(objs, rd / f"{name}_front.png", (0, cy - 20, zc), (0, cy, zc), ortho=30 * U, size=(360, 360), up="Y")
            render(objs, rd / f"{name}_side.png", (20, cy, zc), (0, cy, zc), ortho=30 * U, size=(360, 360), up="Y")
            render(objs, rd / f"{name}_rear.png", (0, cy + 20, zc), (0, cy, zc), ortho=30 * U, size=(360, 360), up="Y")
            render(objs, rd / f"{name}_q34.png", (2.6, cy - 3.2, 3.0), (0, cy, 0.35), lens=60, size=(360, 360), up="Y")
            render(objs, rd / f"{name}_q34b.png", (-2.8, cy + 2.6, 2.6), (0, cy, 0.35), lens=60, size=(360, 360), up="Y")
            render(objs, rd / f"{name}_under.png", (0, cy, -20), (0, cy, 0), ortho=30 * U, size=(300, 300))
            tilt = math.radians(25)
            render(objs, rd / f"{name}_game.png", (0, cy - 12 * math.sin(tilt), 12 * math.cos(tilt)), (0, cy, 0),
                   lens=90, size=(360, 360), up="Y")
            for fr in (ORB_FRAMES if name == "orb" else POD_FRAMES):
                set_frame_colours(objs + stack, fr)
                fv = visible_for([o for o in stack if o in objs or ("tyrian_frames" in o and abs(o.location.y - cy) < 1e-6)], fr)
                render(fv, rd / f"{name}_top_{fr}.png", (0, cy, 20), (0, cy, 0), ortho=28 * U, size=(240, 280))
            set_frame_colours(stack, f)
        print("rendered")


main()
