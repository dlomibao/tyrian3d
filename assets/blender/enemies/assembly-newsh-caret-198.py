"""assembly-newsh-caret-198: UNDERDELI's horizontal torpedo, newsh^.shp size 2, units
newsh-caret-198/-200/-201 (torpedo A, nose to the left) and newsh-caret-203/-204/-206 (torpedo B, its
mirror, nose to the right, 2 px longer in the waist). Episode 4, level 4.7.

What it is (evidence: tools/enemy_behaviour.mjs, harness main=14 at t3080-3200): three rigid pieces
on one link rise up the screen from the bottom at 3 px/tick; when level with the player every piece
hides (frame 999 = enemy_gone, never drawn) and launches a copy of itself that accelerates away
sideways toward the bulb end. So it is a torpedo carried up the screen and fired sideways, the bulb
end its nose. Read from the 58x28 (A) composite, light from the top of the screen:
- Nose: a segmented warhead cluster. A central tube (rows 10-16) with a rounded cap and two more
  beads behind it (highlights at cols 4 and 15 are sheen), flanked by two side tubes (rows 5-9 and
  17-21) that start as slim ogives at col 4 and carry three ring collars each (the 1 px notches at
  cols 15 and 19 of the outline are the grooves between collars). A conical fairing (cols 19-24)
  runs the cluster into the body.
- Body: a plain round cylinder (rows 7-19), brightest along row 12: lighting, not paint.
- Fins: a pair of broad strakes (cols 21-38, rows 1-25) framed by a chamfered rim round a recessed
  panel (light frame 59 / panel 58 on the upper one, dark teal panel 210 / rim 58 on the lower one,
  as the sprite paints them), then swept tail fins (cols 38-52; 61 upper, 215 lower, the lower one
  1 px smaller as in the sprite).
- Tail: a narrower tail cone (cols 39-48) with a thin light probe rod (rows 12-13, cols 40-51) lying
  along its top and sticking out ~4 px past its end.

Built once whole per torpedo in assembly pixel coordinates (u = column edge, v = row edge, axis on
v = 13.5), then cut into its three overlapping 24x28 pieces with common.split_assembly (pieces
overlap 2 and 12 px; each piece keeps exactly what its own sprite box shows, as the C draws them).
The outline shell (D51) is voxel-remeshed from a sealed copy of the whole torpedo (no grooves or
panel recesses) and then clipped to each piece box WITHOUT capping the cut, so no ink ring is drawn
where a piece ends inside its neighbour; ink stays on the silhouette (D90/D118, islands="outer" D189).

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsh-caret-198.py (exports torpedo A:
newsh-caret-198/-200/-201); assembly-newsh-caret-203.py loads this builder and exports torpedo B
(-203/-204/-206) only. Each model goes to public/models/enemies/<piece>.glb with its spriteModels JSON
(common.export_sprite_model). Optional after "--": --review DIR writes review renders and top-view
masks into DIR (nothing is written outside the repo outputs on a normal build). The repo is found from this file's location (a parent holding assets/blender/common.py),
else $TYRIAN_REPO, else the current directory. The catalogue has no reference/models folder for
these six units, so their frames are read straight from the game data with tools/sprite_data.py
(newsh^.shp, palette 5, the catalogue's decode).
"""

import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


def find_repo():
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "assets" / "blender" / "common.py").exists():
            return p
    env = os.environ.get("TYRIAN_REPO")
    if env and (Path(env) / "assets" / "blender" / "common.py").exists():
        return Path(env)
    cwd = Path.cwd()
    if (cwd / "assets" / "blender" / "common.py").exists():
        return cwd
    raise SystemExit("can't find the repo: run from the worktree or set TYRIAN_REPO")


ROOT = find_repo()
sys.path.insert(0, str(ROOT / "assets" / "blender"))
sys.path.insert(0, str(ROOT / "tools"))
import common  # noqa: E402
import sprite_data  # noqa: E402

NAME = "assembly-newsh-caret-198"
TAG = "nshc198"
PX = 1 / 12
SHEET = "newsh^.shp"
AXIS_V = 13.5
# Torpedo A (nose left) and B (nose right): pieces with their left pixel column in the composite.
VARIANTS = {
    "A": dict(width=58, ext=0.0, mirror=False, pieces=[("newsh-caret-198", 0), ("newsh-caret-200", 22),
                                                       ("newsh-caret-201", 34)]),
    "B": dict(width=60, ext=2.0, mirror=True, pieces=[("newsh-caret-203", 0), ("newsh-caret-204", 12),
                                                      ("newsh-caret-206", 36)]),
}
ALL_PIECES = [n for v in VARIANTS.values() for n, _ in v["pieces"]]


# ---- sprite data ------------------------------------------------------------------------------

def load_sprites():
    """{piece: sprite dict like common.load_sprite}, read from the game data with tools/sprite_data.py
    (the catalogue has no reference/models folder for these six units), plus the whole palette under
    "_pal" for materials on indices the frames don't use."""
    pal = sprite_data.palette_rgb(ROOT)
    out = {}
    for n in ALL_PIECES:
        out[n] = sprite_data.load(ROOT, n, SHEET, [int(n.rsplit("-", 1)[1])])
        out[n]["_pal"] = pal
    return out


def composite(sprites, variant):
    v = VARIANTS[variant]
    g = [[-1] * v["width"] for _ in range(28)]
    for name, ox in v["pieces"]:
        for y, row in enumerate(sprites[name]["frames"][0]["pixels"]):
            for x, val in enumerate(row):
                if val >= 0:
                    g[y][ox + x] = val
    return g


# ---- geometry helpers (pixel-edge coordinates of torpedo A; B is mapped on output) -------------

class Space:
    """u, v (A pixel edges) -> Blender, with B's waist insert (ext px after u = 20.5) and mirror."""

    def __init__(self, width, ext, mirror):
        self.width, self.ext, self.mirror = width, ext, mirror

    def U(self, u):
        return u + self.ext if u > 20.5 else u

    def X(self, u):
        uu = self.U(u)
        return (self.width - uu if self.mirror else uu) * PX

    def P(self, u, v, z):
        return Vector((self.X(u), -v * PX, z))


def faces_ring(bm, r0, r1, mat, smooth=True):
    out = []
    n0, n1 = len(r0), len(r1)
    if n0 == 1 and n1 == 1:
        return out
    nk = max(n0, n1)
    for k in range(nk):
        j = (k + 1) % nk
        if n0 == 1:
            f = bm.faces.new((r0[0], r1[k], r1[j]))
        elif n1 == 1:
            f = bm.faces.new((r0[k], r0[j], r1[0]))
        else:
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
        f.material_index = mat
        f.smooth = smooth
        out.append(f)
    return out


def lathe(bm, S, stations, vc, zc=0.0, sides=32, cap0=True, cap1=True):
    """A body of revolution about the line v = vc, z = zc along u. stations: (u, r_px, mat) with the
    band from a station to the next in that station's material; r = 0 is a point (a rounded tip)."""
    rings = []
    for st in stations:
        u, r = st[0], st[1]
        # an optional 4th value: this station's lateral offset from vc (a bent axis), signed by `bend`
        c = S.P(u, vc + (st[3] if len(st) > 3 else 0.0), zc)
        if r <= 0:
            rings.append([bm.verts.new(c)])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            ring.append(bm.verts.new(c + Vector((0, -math.cos(a) * r * PX, math.sin(a) * r * PX))))
        rings.append(ring)
    for i in range(len(rings) - 1):
        faces_ring(bm, rings[i], rings[i + 1], stations[i][2])
    if cap0 and len(rings[0]) > 1:
        f = bm.faces.new(list(reversed(rings[0])))
        f.material_index = stations[0][2]
    if cap1 and len(rings[-1]) > 1:
        f = bm.faces.new(rings[-1])
        f.material_index = stations[-1][2]
    return rings


def inset_poly(poly, d):
    """Offset a convex polygon (u, v) inward by d px (vertices moved along the bisectors)."""
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    s = 1 if area > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        e0 = (p1 - p0).normalized()
        e1 = (p2 - p1).normalized()
        n0 = Vector((-e0.y, e0.x)) * s
        n1 = Vector((-e1.y, e1.x)) * s
        b = n0 + n1
        if b.length < 1e-6:
            b = n0
        b.normalize()
        cosh = max(0.3, b.dot(n0))
        q = p1 + b * (d / cosh)
        out.append((q.x, q.y))
    return out


def fin_plate(bm, S, poly, root_v, tip_d, h_root, h_tip, mat_edge, mat_top, ch=0.35, panel=None,
              mat_panel=None, recess=0.022, zc=0.0):
    """A horizontal fin: a convex plan polygon (u, v px), a chamfered rim all round (ch px), half
    thickness tapering from h_root (units) at v = root_v to h_tip at tip_d px from it. `panel`: an
    inner polygon recessed `recess` units into the top face (a modelled panel line round it)."""

    def h(v):
        t = min(1.0, abs(v - root_v) / tip_d)
        return h_root + (h_tip - h_root) * t

    inner = inset_poly(poly, ch)
    loops = []
    for pl, dz in ((inner, -1.0), (poly, -0.55), (poly, 0.55), (inner, 1.0)):
        loops.append([bm.verts.new(S.P(u, v, zc + dz * h(v))) for u, v in pl])
    for i in range(3):
        m = mat_edge
        fs = faces_ring(bm, loops[i], loops[i + 1], m, smooth=False)
        for f in fs:
            f.smooth = False
    bot = bm.faces.new(list(reversed(loops[0])))
    bot.material_index = mat_edge
    top_loop = loops[3]
    if panel is None:
        f = bm.faces.new(top_loop)
        f.material_index = mat_top
        return
    # top face with a recessed panel: rim ring (top loop -> panel outline), wall, sunken panel
    pv = [bm.verts.new(S.P(u, v, zc + h(v))) for u, v in panel]
    pl = [bm.verts.new(S.P(u, v, zc + h(v) - recess)) for u, v in panel]
    bridge_loops(bm, top_loop, pv, inner, panel, mat_top)
    faces_ring(bm, pv, pl, mat_panel, smooth=False)
    f = bm.faces.new(pl)
    f.material_index = mat_panel


def bridge_loops(bm, outer_v, inner_v, outer_uv, inner_uv, mat):
    """Fill between an outer loop and an inner loop (different counts) by walking both in step."""
    n, m = len(outer_v), len(inner_v)
    # align: start the inner loop at the vertex nearest outer[0]
    o0 = Vector(outer_uv[0])
    k0 = min(range(m), key=lambda k: (Vector(inner_uv[k]) - o0).length)
    inner_v = inner_v[k0:] + inner_v[:k0]
    inner_uv = inner_uv[k0:] + inner_uv[:k0]
    i = j = 0
    while i < n or j < m:
        a, b = outer_v[i % n], inner_v[j % m]
        if i >= n:
            tri = (a, inner_v[(j + 1) % m], b)
            j += 1
        elif j >= m:
            tri = (a, outer_v[(i + 1) % n], b)
            i += 1
        else:
            # advance the side whose next step is shorter
            da = (Vector(outer_uv[(i + 1) % n]) - Vector(inner_uv[j % m])).length
            db = (Vector(inner_uv[(j + 1) % m]) - Vector(outer_uv[i % n])).length
            if da <= db:
                tri = (a, outer_v[(i + 1) % n], b)
                i += 1
            else:
                tri = (a, inner_v[(j + 1) % m], b)
                j += 1
        try:
            f = bm.faces.new(tri)
            f.material_index = mat
            f.smooth = False
        except ValueError:
            pass


# ---- the torpedo --------------------------------------------------------------------------------

MATS = [  # key, palette index, metallic, roughness, Specular IOR Level (F0)
    ("nose", 54, 0.65, 0.36, 0.6),     # central warhead tube (median 0x36)
    ("side", 56, 0.65, 0.36, 0.6),     # side tubes (upper median 0x38; the lower one's darks are shading)
    ("collar", 57, 0.7, 0.32, 0.7),    # their ring collars, a touch brighter (rows 6-8: 0x37-0x39)
    ("body", 56, 0.65, 0.36, 0.6),     # body cylinder (median 0x38)
    ("groove", 51, 0.4, 0.55, 0.4),    # panel lines and grooves (0x33)
    ("fairing", 54, 0.65, 0.36, 0.6),  # nose-to-body fairing (median 0x36)
    ("fin_rim", 59, 0.75, 0.36, 0.6),   # upper strake frame (0x3b)
    ("fin_pan", 58, 0.7, 0.38, 0.6),  # upper strake panel (0x3a)
    ("lfin_rim", 58, 0.75, 0.36, 0.6),  # lower strake rim (0x3a)
    ("lfin_pan", 210, 0.65, 0.4, 0.5),  # lower strake panel (0xd2)
    ("tail_up", 61, 0.8, 0.38, 0.6),   # upper tail fins (0x3d)
    ("tail_lo", 215, 0.75, 0.38, 0.6),  # lower tail fins (0xd7)
    ("tail", 53, 0.65, 0.38, 0.6),     # tail cone (0x35)
    ("rod", 61, 0.8, 0.3, 0.7),        # probe rod: light satin metal (row 12 0x3d; row 13 0x3a is shading)
]


def materials(sprites):
    merged = {"name": NAME, "colors": {}}
    pal = next(iter(sprites.values())).get("_pal")
    for s in sprites.values():
        merged["colors"].update(s["colors"])
    mats, M, seen = [], {}, {}
    for key, idx, met, rough, spec in MATS:
        if str(idx) not in merged["colors"] and pal:
            merged["colors"][str(idx)] = pal[idx]
        sig = (idx, met, rough, spec)
        if sig not in seen:
            m = common.palette_material(merged, idx, f"{TAG}_{len(mats)}", metallic=met, roughness=rough)
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = spec
            seen[sig] = len(mats)
            mats.append(m)
        M[key] = seen[sig]
    return mats, M


def rod_tube(bm, S, mat, v, stations, z0, z1, sides=16):
    """A straight round rod along u at row v, its centre height running linearly through z0 and z1
    ((u, z_px) pairs), so it can lie along a tapering cone. stations: (u, r_px); r = 0 is a point."""
    k = (z1[1] - z0[1]) / (z1[0] - z0[0])
    rings = []
    for u, r in stations:
        c = S.P(u, v, (z0[1] + k * (u - z0[0])) * PX)
        if r <= 0:
            rings.append([bm.verts.new(c)])
            continue
        rings.append([bm.verts.new(c + Vector((0, -math.cos(2 * math.pi * i / sides) * r * PX,
                                               math.sin(2 * math.pi * i / sides) * r * PX)))
                      for i in range(sides)])
    for i in range(len(rings) - 1):
        faces_ring(bm, rings[i], rings[i + 1], mat)


def build_torpedo(bm, S, M, detail=True):
    g = M["groove"] if detail else None

    def gr(default):
        return g if g is not None else default

    nose, body, tail = M["nose"], M["body"], M["tail"]
    # Central tube, fairing, body and tail cone: one lathe on the axis.
    st = [
        (2.0, 0.0, nose), (2.12, 1.25, nose), (2.45, 2.15, nose), (3.1, 2.85, nose), (4.1, 3.3, nose),
        (5.4, 3.55, nose), (6.9, 3.55, nose), (7.5, 3.3, nose),
        (7.75, 2.95, gr(nose)), (8.35, 2.95, nose), (8.6, 3.35, nose),          # groove, bead 2
        (9.0, 3.6, nose), (11.0, 3.6, nose), (11.4, 3.3, nose),
        (11.65, 2.95, gr(nose)), (13.15, 2.95, nose), (13.4, 3.4, nose),        # groove, bead 3
        (13.8, 3.85, nose), (18.2, 3.85, nose), (18.6, 3.4, nose),
        (18.85, 3.05, gr(nose)), (19.35, 3.05, M["fairing"]),                   # groove, fairing
        (19.6, 3.9, M["fairing"]), (20.4, 4.7, M["fairing"]), (21.6, 5.45, M["fairing"]),
        (22.8, 5.95, M["fairing"]), (23.45, 6.1, M["fairing"]),
        (23.6, 5.75, gr(body)), (24.05, 5.75, body), (24.25, 6.3, body),        # body joint
        (24.6, 6.45, body), (31.0, 6.45, body), (31.12, 6.3, gr(body)), (31.38, 6.3, body),  # panel line
        (31.5, 6.45, body), (37.7, 6.45, body), (38.1, 6.2, body),
        (38.3, 5.5, gr(tail)), (38.75, 5.5, tail), (38.95, 5.05, tail),         # tail joint
        (39.4, 4.85, tail), (43.5, 4.55, tail), (46.4, 4.25, tail), (47.6, 4.0, tail),
        (48.15, 3.55, tail), (48.4, 2.7, tail), (48.4, 0.0, tail),
    ]
    lathe(bm, S, st, AXIS_V, sides=36)
    # Probe rod: a 2 px bar (rows 12-13, cols 40-51) out of the tail joint, lying along the top of
    # the tail cone (centre 0.15 px under its surface) and sticking out ~4 px past the cone end.
    rod_tube(bm, S, M["rod"], 13.0, [(39.0, 0.0), (39.15, 0.55), (39.45, 0.9), (39.8, 1.0), (51.2, 0.98),
                                     (51.65, 0.82), (51.95, 0.5), (52.05, 0.0)],
             z0=(39.0, 4.75), z1=(47.6, 3.85), sides=16)
    # Side tubes of the warhead: slim ogive noses, then three ring collars with grooves between.
    for side in (-1, 1):
        vc = AXIS_V + side * 4.45
        sm = M["side"]
        # the noses curve in to the central tube (axis offset 2.8 px at the tip, 4.45 px from col 10)
        nose_st = [(4.5, 0.0, 2.8), (4.8, 0.6, 2.9), (5.5, 0.92, 3.05), (6.5, 1.25, 3.4), (7.5, 1.5, 3.75),
                   (8.8, 1.72, 4.05), (9.9, 1.92, 4.27), (10.3, 2.15, 4.45)]
        lathe(bm, S, [(u, r, sm, side * (o - 4.45)) for u, r, o in nose_st] + [(11.5, 2.15, M["side"]), (11.65, 2.75, M["collar"]),
                      (11.9, 3.0, M["collar"]), (14.6, 3.0, M["collar"]), (14.85, 2.75, M["collar"]),
                      (15.0, 2.05, gr(M["side"])), (15.85, 2.05, M["collar"]), (16.0, 2.75, M["collar"]),
                      (16.25, 3.0, M["collar"]), (18.6, 3.0, M["collar"]), (18.85, 2.75, M["collar"]),
                      (19.0, 2.05, gr(M["side"])), (19.85, 2.05, M["collar"]), (20.0, 2.75, M["collar"]),
                      (20.25, 3.05, M["collar"]), (23.2, 3.05, M["collar"]), (23.6, 2.4, M["side"]),
                      (25.5, 1.4, M["side"]), (26.5, 0.0, M["side"])], vc, zc=0.0, sides=20)
    # Strakes: chamfered plates with a recessed panel.
    up = [(20.9, 9.5), (20.9, 5.3), (23.8, 4.4), (25.3, 3.2), (26.3, 2.05), (37.9, 2.05),
          (38.55, 2.7), (38.55, 9.5)]
    panel_up = [(26.9, 3.95), (35.5, 3.95), (34.9, 6.9), (25.9, 6.9)]
    lo = [(u, 2 * AXIS_V - v) for u, v in reversed(up)]
    panel_lo = [(u, 2 * AXIS_V - v) for u, v in reversed(panel_up)]
    for poly, pan, rim, pm, root in ((up, panel_up, M["fin_rim"], M["fin_pan"], 9.5),
                                     (lo, panel_lo, M["lfin_rim"], M["lfin_pan"], 17.5)):
        fin_plate(bm, S, poly, root, 7.5, 0.85 * PX * 1.0 + 0.0, 0.5 * PX, rim, rim, ch=0.4,
                  panel=pan if detail else None, mat_panel=pm)
        if not detail:
            pass
    # Swept tail fins (the lower one 1 px smaller, as drawn).
    tup = [(38.6, 10.0), (38.6, 4.35), (39.2, 4.0), (40.8, 3.65), (42.0, 3.05), (43.2, 2.1), (46.7, 2.05),
           (47.3, 2.75), (48.8, 3.2), (50.1, 4.2), (51.4, 5.4), (52.0, 6.1), (51.9, 6.8), (51.0, 7.5), (50.0, 8.4),
           (48.9, 9.1), (47.4, 9.7), (46.5, 10.0)]
    tlo = [(38.6, 17.0), (47.5, 17.0), (48.6, 17.4), (49.9, 18.4), (50.9, 19.4), (51.05, 20.2),
           (50.4, 20.9), (49.4, 22.0), (48.6, 22.9), (47.2, 23.3), (46.8, 24.0), (41.5, 24.0),
           (40.8, 23.4), (39.2, 23.0), (38.6, 22.7)]
    fin_plate(bm, S, tup, 10.0, 8.0, 0.6 * PX, 0.32 * PX, M["tail_up"], M["tail_up"], ch=0.3)
    fin_plate(bm, S, tlo, 17.0, 7.0, 0.6 * PX, 0.32 * PX, M["tail_lo"], M["tail_lo"], ch=0.3)


def finish_mesh(bm, name, mats, coll, mirror):
    if mirror:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # smooth by angle: crease edges sharper than 40 degrees
    for e in bm.edges:
        if len(e.link_faces) == 2:
            a = e.link_faces[0].normal.angle(e.link_faces[1].normal, 0.0)
            if a > math.radians(40):
                e.smooth = False
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def build_variant(key, mats, M, coll, detail=True):
    v = VARIANTS[key]
    S = Space(v["width"], v["ext"], v["mirror"])
    bm = bmesh.new()
    build_torpedo(bm, S, M, detail)
    return finish_mesh(bm, f"{NAME}_{key}" + ("" if detail else "_plain"), mats, coll, v["mirror"])


def layout(key):
    return [(n, ox + 12, 14) for n, ox in VARIANTS[key]["pieces"]]


def clip_open(obj, cx, cy, coll, name):
    """Copy of `obj` clipped to the piece box round (cx, cy) px, cut faces NOT filled, moved to the
    piece origin (for the outline shell: no ink cap where the piece ends inside its neighbour)."""
    x0, y0 = cx / 12, -cy / 12
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
    hw, hh = 1.0, 14 / 12
    for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                   ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
    bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in obj.data.materials:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    for k in obj.keys():
        ob[k] = obj[k]
    return ob


def build_all(sprites, keys=("A", "B")):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    mats, M = materials(sprites)
    whole, pieces, shells = {}, {}, {}
    for key in keys:
        obj = build_variant(key, mats, M, coll)
        whole[key] = obj
        lay = layout(key)
        pieces.update(common.split_assembly(obj, lay))
        plain = build_variant(key, mats, M, coll, detail=False)
        bpy.context.view_layer.update()
        shell = common.outline_shell(plain, coll, voxel=0.014, faces=9000, inside=0.006, islands="outer")
        for name, cx, cy in lay:
            sh = clip_open(shell, cx, cy, coll, f"{name}_outline")
            shells[name] = sh
        bpy.data.objects.remove(shell, do_unlink=True)
        bpy.data.objects.remove(plain, do_unlink=True)
    for name in [n for k in keys for n, _ in VARIANTS[k]["pieces"]]:
        p = pieces[name]
        for poly in p.data.polygons:
            if len(poly.vertices) > 8:  # the split's filled cut faces are flat
                poly.use_smooth = False
        nv = len(shells[name].data.vertices)
        if nv == 0:
            raise SystemExit(f"{name}_outline has no mesh")
        tris = sum(len(q.vertices) - 2 for q in p.data.polygons)
        print(f"PIECE {name}: {tris} tris, outline {nv} verts")
    return coll, mats, whole, pieces, shells


# ---- review renders (only with --review) ---------------------------------------------------------

def review(sprites, whole, pieces, shells, out_dir):
    import numpy as np
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.get("rev") or bpy.data.worlds.new("rev")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.32, 0.34, 0.38, 1)
    bg.inputs[1].default_value = 1.0
    scene.world = world
    # the game's sun: from the left, the camera side and above (src/render/sun.ts, three -> Blender)
    sun_d = bpy.data.lights.new("rev_sun", "SUN")
    sun_d.energy = 3.2
    sun = bpy.data.objects.new("rev_sun", sun_d)
    scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((6, 8.4, -20)).to_track_quat("-Z", "Y").to_euler()
    sun.rotation_euler = (Vector((0, 0, 0)) - Vector((-6, -8.4, 20))).to_track_quat("-Z", "Y").to_euler()
    cam_d = bpy.data.cameras.new("rev_cam")
    cam = bpy.data.objects.new("rev_cam", cam_d)
    scene.collection.objects.link(cam)
    scene.camera = cam
    shells_all = list(shells.values())
    for s in shells_all:
        s.hide_render = True
    for p in pieces.values():
        p.hide_render = True

    def shot(objs, path, loc, target, ortho=None, res=(640, 400), lens=50):
        for o in whole.values():
            o.hide_render = o not in objs
        cam.location = Vector(loc)
        cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        if ortho:
            cam_d.type = "ORTHO"
            cam_d.ortho_scale = ortho
        else:
            cam_d.type = "PERSP"
            cam_d.lens = lens
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.resolution_percentage = 100
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    K = 10
    for key, v in VARIANTS.items():
        obj = whole[key]
        W = v["width"]
        cx, cy = W / 2 * PX, -14 * PX
        # top view on the sprite grid (K image px per sprite px), lit, and as a mask
        shot([obj], out_dir / f"top_{key}.png", (cx, cy, 10), (cx, cy, 0), ortho=W * PX, res=(W * K, 28 * K))
        c = (cx, cy, 0)
        L = 6.0
        shot([obj], out_dir / f"side_{key}.png", (cx, cy - L, 0.0), c, ortho=W * PX * 1.1, res=(640, 320))
        nose_x = 0 if not v["mirror"] else W * PX
        dirx = -1 if not v["mirror"] else 1
        shot([obj], out_dir / f"front_{key}.png", (nose_x + dirx * L, cy, 0.0), c, ortho=30 * PX, res=(320, 320))
        shot([obj], out_dir / f"rear_{key}.png", (nose_x - dirx * (W * PX + L), cy, 0.0), c, ortho=30 * PX,
             res=(320, 320))
        shot([obj], out_dir / f"q34_{key}.png", (cx - dirx * 3.5, cy - 4.5, 3.6), c, res=(640, 400), lens=55)
        shot([obj], out_dir / f"game_{key}.png", (cx, cy - 7.5, 12.0), c, res=(640, 400), lens=120)
        shot([obj], out_dir / f"under_{key}.png", (cx + 1.0, cy - 3.0, -5.0), c, res=(640, 400), lens=50)
    # per-piece glbs for the game harness
    for name in ALL_PIECES:
        common.export_glb([pieces[name], shells[name]], out_dir / "game" / f"{name}.glb")
    print("review renders in", out_dir)


def export_variant(key, argv=None):
    """Build torpedo  ("A" or "B") and export its three pieces as game models."""
    argv = argv if argv is not None else (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    sprites = load_sprites()
    coll, mats, whole, pieces, shells = build_all(sprites, (key,))
    names = [n for n, _ in VARIANTS[key]["pieces"]]
    for name in names:
        common.export_sprite_model(ROOT, [pieces[name], shells[name]], f"enemies/{name}",
                                   sprites[name]["sprites"])
    if "--review" in argv:
        # review() only touches the variants it was handed
        review_variants(key, whole, pieces, shells, argv[argv.index("--review") + 1])


def review_variants(key, whole, pieces, shells, out_dir):
    global ALL_PIECES, VARIANTS
    saved = VARIANTS
    VARIANTS = {key: saved[key]}
    ALL_PIECES = [n for n, _ in VARIANTS[key]["pieces"]]
    try:
        review(None, whole, pieces, shells, out_dir)
    finally:
        VARIANTS = saved
        ALL_PIECES = [n for v in saved.values() for n, _ in v["pieces"]]


def main():
    export_variant("A")


if __name__ == "__main__":
    main()
