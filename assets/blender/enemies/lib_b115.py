"""Shared builder of the newsh3.shp family (lib_b115): the crawlers assembly-newsh3-86 / -122, the forklift newsh3-14, the spire assembly-newsh3-275 and the floor hatch newsh3-18, one object family:

(a) assembly-newsh3-86 (newsh3-84 | newsh3-86) and assembly-newsh3-122 (newsh3-122 | newsh3-124): two mirror-image tan
    armoured crawlers, 48 x 22 px, seen in SURFACE (episode 4 level 4.4, harness main=2). They drift sideways
    ((-1,0) for 86, (+1,0) for 122 px/tick against the terrain), so they are tracked crawlers, not bunkers: a long low
    armoured hull with a flat roof, a raised hatch pad on the roof (where the newsh3-14 forklift rides, dx +16 / +9, dy -3),
    bevelled end caps, two glowing red vent slits in one cap, a stepped front ledge and a sloped glacis over two track
    units (the notch at the bottom of the sprite is the gap between the short track under the vent cap and the long one).
    The hull's plan outline, caps and tracks are mirror twins (122 = 86 mirrored about u = 24.5 px); each roof's ribs,
    hatch plates and vents follow its own sprite.
(b) newsh3-14 (frames 14, 16, 54, 90, 92, 12, 50, 88): a small tan tracked forklift: two fendered track pods, a raised
    hood with a lit chevron between them, a dark fork carriage and two flat tines. Animate 0 with ani 8: the frame is a
    heading set by level events, so each frame is the same vehicle turned (newsh3-14, -f2 .. -f8; -f6/-f7/-f8 are the new
    12 (up-left), 50 (left), 88 (down-left)). Each heading's footprint (body size, tine gap and length, centre) is fitted
    to that frame's own mask (FORK_PARAMS), so every frame matches its sprite.
(c) assembly-newsh3-275 (newsh3-237 over newsh3-275, 24 x 56 px; CORE, level 4.5, harness main=6): a grey stone spire
    leaning up the screen out of a mound of dark lava rock lit red on its left; both take the D175 facet ramp.
(d) newsh3-18 (frames 18, 56, 94, 284; DESERTRUN, level 4.10, harness main=29): an armoured floor hatch in a grey deck
    plate: a salmon coaming round a pit whose two leaves slide back under it while a grey turret head with a glowing red
    eye rises (animate 2: it opens when it fires). The deck is part of the grey platform the hatches are set in (each
    hatch is one tile of it, rigid pairs at dx +-24), modelled plate and seams, not pixels (D130's exemption).

Each of the five scripts (assembly-newsh3-86.py, assembly-newsh3-122.py, newsh3-14.py, assembly-newsh3-275.py,
newsh3-18.py) calls run(<group>) here and exports only its own models through common.export_sprite_model
(public/models/enemies/<model>.glb with its <model>_outline shell, and src/render/spriteModels/<model>.json).
Review outputs only behind flags (--views DIR renders and measurements, --game DIR one glb per model), --nobake.
The repo is found from this file's location (assets/blender/enemies/) or the TYRIAN_REPO environment variable;
reference/models/<name> must exist (npm run catalogue).

    blender -b --factory-startup -P assets/blender/enemies/assembly-newsh3-86.py -- [--views DIR] [--game DIR] [--nobake]
"""

import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


def _repo():
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "assets" / "blender" / "common.py").exists():
            return p
    env = os.environ.get("TYRIAN_REPO")
    if env and (Path(env) / "assets" / "blender" / "common.py").exists():
        return Path(env)
    raise SystemExit("can't find the repo: run from assets/blender/enemies/ or set TYRIAN_REPO")


ROOT = _repo()
sys.path.insert(0, str(ROOT / "assets" / "blender"))
sys.path.insert(0, str(ROOT / "assets" / "blender" / "enemies"))
sys.path.insert(0, str(ROOT / "tools"))
import common  # noqa: E402

REF = ROOT / "reference" / "models"
PX = 1 / 12


def need_ref(name):
    if not (REF / name / "sprite.json").exists():
        raise SystemExit(f"reference/models/{name} is missing: run `npm run catalogue` in {ROOT}")
    return common.load_sprite(ROOT, name)


# =====================================================================================================
# mesh builder in sprite px (u = column edge, v = row edge, z up), mapped to Blender units on a w x h grid
# =====================================================================================================

class B:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.bm = bmesh.new()

    def P(self, u, v, z):
        return Vector(((u - self.w / 2) * PX, (self.h / 2 - v) * PX, z * PX))

    def faces_from(self, n):
        self.bm.faces.ensure_lookup_table()
        return self.bm.faces[n:]

    def tag(self, faces, mat, smooth=False):
        for f in faces:
            f.material_index = mat
            f.smooth = smooth

    def hull(self, pts, mat, smooth=False):
        """Convex hull of px points (a chamfered block or a sloped plate)."""
        bm = self.bm
        vs = [bm.verts.new(self.P(*p)) for p in pts]
        res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
        junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
        if junk:
            bmesh.ops.delete(bm, geom=junk, context="VERTS")
        live = [v for v in vs if v.is_valid]
        faces = list({f for v in live for f in v.link_faces})
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), verts=live,
                                 edges=list({e for f in faces for e in f.edges}))
        out = list({f for v in vs if v.is_valid for f in v.link_faces})
        for f in out:
            f.material_index = mat
            f.smooth = smooth
        return out

    def cbox(self, u0, u1, v0, v1, z0, z1, ch, mat, chz=None, bottom_ch=False):
        """A box with chamfered vertical and top edges (px)."""
        chz = ch if chz is None else chz
        ch = min(ch, (u1 - u0) / 2.01, (v1 - v0) / 2.01)
        chz = min(chz, (z1 - z0) / 1.01)
        pts = []
        for u, su in ((u0, 1), (u1, -1)):
            for v, sv in ((v0, 1), (v1, -1)):
                pts += [(u + su * ch, v, z1), (u, v + sv * ch, z1 - chz), (u + su * ch, v + sv * ch, z1)]
                pts += [(u + su * ch, v, z0), (u, v + sv * ch, z0)] if not bottom_ch else \
                       [(u + su * ch, v + sv * ch, z0), (u + su * ch, v, z0 + chz), (u, v + sv * ch, z0 + chz)]
                pts.append((u, v + sv * ch, z0) if not bottom_ch else (u, v + sv * ch, z0 + chz))
        return self.hull(pts, mat)

    def sloped(self, corners, z0s, z1s, mat):
        """A plate following a slope: plan corners [(u, v)], bottom heights z0s and top heights z1s per corner."""
        pts = [(u, v, z0) for (u, v), z0 in zip(corners, z0s)] + [(u, v, z1) for (u, v), z1 in zip(corners, z1s)]
        return self.hull(pts, mat)

    def loft(self, rings, mat, cap0=True, cap1=True, smooth=False):
        """Quads between rings of px points (same count, closed loops), capped."""
        bm = self.bm
        vr = [[bm.verts.new(self.P(*p)) for p in ring] for ring in rings]
        k = len(vr[0])
        out = []
        for r0, r1 in zip(vr, vr[1:]):
            for i in range(k):
                j = (i + 1) % k
                out.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
        if cap0:
            out.append(bm.faces.new(list(reversed(vr[0]))))
        if cap1:
            out.append(bm.faces.new(vr[-1]))
        self.tag(out, mat, smooth)
        return out

    def cyl(self, c, axis, r, half_len, mat, sides=12, smooth=True, r2=None):
        """A cylinder (px): centre c, axis 'u' | 'v' | 'z', radius r (r2 at the + end), half length."""
        r2 = r if r2 is None else r2
        ring0, ring1 = [], []
        for i in range(sides):
            a = 2 * math.pi * (i + 0.5) / sides
            ca, sa = math.cos(a), math.sin(a)
            for ring, sgn, rr in ((ring0, -1, r), (ring1, 1, r2)):
                if axis == "u":
                    ring.append((c[0] + sgn * half_len, c[1] + ca * rr, c[2] + sa * rr))
                elif axis == "v":
                    ring.append((c[0] + ca * rr, c[1] + sgn * half_len, c[2] + sa * rr))
                else:
                    ring.append((c[0] + ca * rr, c[1] + sa * rr, c[2] + sgn * half_len))
        out = self.loft([ring0, ring1], mat)
        for f in out:
            f.smooth = smooth and len(f.verts) == 4
        return out

    def dome(self, c, rx, ry, rz, mat, seg=14, rings=5, smooth=True):
        """An upper half ellipsoid on z = c[2] (closed with a flat base)."""
        bm = self.bm
        out = []
        rs = []
        for k in range(rings):
            a = math.pi / 2 * k / rings
            rs.append([bm.verts.new(self.P(c[0] + math.cos(a) * rx * math.cos(2 * math.pi * i / seg),
                                           c[1] + math.cos(a) * ry * math.sin(2 * math.pi * i / seg),
                                           c[2] + math.sin(a) * rz)) for i in range(seg)])
        top = bm.verts.new(self.P(c[0], c[1], c[2] + rz))
        for r0, r1 in zip(rs, rs[1:]):
            for i in range(seg):
                j = (i + 1) % seg
                out.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
        for i in range(seg):
            out.append(bm.faces.new((rs[-1][i], rs[-1][(i + 1) % seg], top)))
        out.append(bm.faces.new(list(reversed(rs[0]))))
        for f in out:
            f.material_index = mat
            f.smooth = smooth and len(f.verts) != seg
        return out

    def band(self, pts_uz, v0, v1, thick, mat, smooth=True):
        """A closed belt: the loop pts_uz [(u, z)] (counter-clockwise seen from -v) as a band `thick` px thick
        (inward), from v0 to v1 (a track belt)."""
        cu = sum(p[0] for p in pts_uz) / len(pts_uz)
        cz = sum(p[1] for p in pts_uz) / len(pts_uz)
        inner = []
        k = len(pts_uz)
        for i, (u, z) in enumerate(pts_uz):
            pu, pz = pts_uz[i - 1]
            nu, nz = pts_uz[(i + 1) % k]
            tu, tz = nu - pu, nz - pz
            ln = math.hypot(tu, tz) or 1
            # inward normal (towards the centre)
            a, b = -tz / ln, tu / ln
            if a * (cu - u) + b * (cz - z) < 0:
                a, b = -a, -b
            inner.append((u + a * thick, z + b * thick))
        bm = self.bm
        out = []
        O0 = [bm.verts.new(self.P(u, v0, z)) for u, z in pts_uz]
        O1 = [bm.verts.new(self.P(u, v1, z)) for u, z in pts_uz]
        I0 = [bm.verts.new(self.P(u, v0, z)) for u, z in inner]
        I1 = [bm.verts.new(self.P(u, v1, z)) for u, z in inner]
        for i in range(k):
            j = (i + 1) % k
            out.append(bm.faces.new((O0[i], O0[j], O1[j], O1[i])))
            out.append(bm.faces.new((I0[j], I0[i], I1[i], I1[j])))
            out.append(bm.faces.new((O0[j], O0[i], I0[i], I0[j])))
            out.append(bm.faces.new((O1[i], O1[j], I1[j], I1[i])))
        for f in out:
            f.material_index = mat
            f.smooth = smooth
        return out, O0 + O1 + I0 + I1

    def finish(self, name, mats, coll):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        obj = bpy.data.objects.new(name, me)
        coll.objects.link(obj)
        return obj


def stadium(u0, u1, z0, z1, seg=8):
    """Points of a stadium loop in the (u, z) plane, ends round."""
    r = (z1 - z0) / 2
    cz = z0 + r
    pts = []
    for i in range(seg + 1):  # right end, bottom to top
        a = -math.pi / 2 + math.pi * i / seg
        pts.append((u1 - r + r * math.cos(a), cz + r * math.sin(a)))
    for i in range(seg + 1):  # left end, top to bottom
        a = math.pi / 2 + math.pi * i / seg
        pts.append((u0 + r + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def mat_of(sprite, tag, idx, kind="armour", **kw):
    """Palette materials by kind: satin armour, dark steel, glow (D126/D173: metallic 1, rough)."""
    if kind == "armour":
        m = common.palette_material(sprite, idx, tag, metallic=kw.get("metallic", 0.35), roughness=kw.get("roughness", 0.55))
    elif kind == "steel":
        m = common.palette_material(sprite, idx, tag, metallic=kw.get("metallic", 0.6), roughness=kw.get("roughness", 0.45))
    elif kind == "rubber":
        m = common.palette_material(sprite, idx, tag, metallic=0.1, roughness=0.85)
    elif kind == "glow":
        m = common.palette_material(sprite, idx, tag, metallic=1.0, roughness=0.6, emission_strength=kw.get("glow", 1.0))
    elif kind == "rock":
        m = common.palette_material(sprite, idx, tag, metallic=0.05, roughness=0.72)
    else:
        raise ValueError(kind)
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in bsdf.inputs:  # D176: F0 for satin metal
        bsdf.inputs["Specular IOR Level"].default_value = kw.get("spec", 0.5)
    return m


class Mats:
    """Material slots by name for one model family."""

    def __init__(self, sprite, tag):
        self.sprite, self.tag, self.list, self.idx = sprite, tag, [], {}

    def __call__(self, key, idx, kind="armour", **kw):
        if key not in self.idx:
            self.idx[key] = len(self.list)
            self.list.append(mat_of(self.sprite, f"{self.tag}_{key}", idx, kind, **kw))
        return self.idx[key]


# =====================================================================================================
# (a) the crawlers
# =====================================================================================================

ROOF_H = 6.0   # roof height, px
TOE = 21.0     # glacis toe row edge (front of the hull above the tracks)
TOE_Z = 3.0
TRACK_Z = 2.8  # track loop height
TRACK_V = (21.0, 23.0)


def vb86(u):
    """Back edge (row edge) of the 86 hull's roof at column edge u: the bevels of the sprite's corners."""
    if u < 15.0:
        return 2.0 + (15.0 - u) * 0.5
    if u > 40.0:
        return 2.0 + (u - 40.0)
    return 2.0


def h86(u):
    """Roof height at u: the end caps slope down to the ends."""
    if u < 15.0:
        return ROOF_H - (15.0 - u) / 9.0 * 3.0
    if u > 39.0:
        return ROOF_H - (u - 39.0) / 7.0 * 2.7
    return ROOF_H


U_L, U_R = 6.0, 46.0  # the 86 hull's ends


def profile(u, inset=0.0, dz=0.0):
    """The hull section at u (86 coordinates): (u, v, z) points round a closed loop, back bottom first."""
    vb, h = vb86(u), h86(u) - dz
    vb += inset
    pts = [(vb + 3.0, 0.0), (vb + 3.0, 2.4), (vb + 0.25, h - 0.75), (vb + 0.9, h), (14.2 - inset, h),
           (14.75 - inset, h - 0.45), (15.85 - inset, h - 0.5), (16.25 - inset, h - 0.12), (16.8 - inset, h - 0.3),
           (TOE - inset, TOE_Z - inset * 0.5), (TOE - 0.3 - inset, 0.0)]
    return [(u, v, z) for v, z in pts]


#: Hull stations along u (86 coordinates); the ends get an inset ring (a chamfered end face).
STATIONS = [6.0, 6.45, 7.5, 9.0, 11.0, 13.0, 14.6, 15.0, 15.4, 18.0, 22.0, 26.0, 30.0, 34.0, 38.6, 39.0, 39.4,
            40.0, 41.0, 42.5, 44.0, 45.0, 45.55, 46.0]


# Per crawler: roof details in its own sprite's column edges (u), rows (v).
CRAWLERS = {
    "b86": dict(
        name="assembly-newsh3-86", pieces=["newsh3-84", "newsh3-86"], mirror=False,
        ribs=[(15.0, 16.6, 2.7, 16.1, 0.45, "rib_hi"), (21.0, 22.0, 3.6, 14.2, 0.3, "rib"),
              (34.0, 35.0, 3.0, 14.2, 0.32, "rib"), (38.7, 39.5, 2.8, 16.1, 0.22, "rib_lo")],
        grooves=[(24.0, 31.0, 5.0, 14.0)],             # dark panel frame under a hatch plate
        plates=[(25.0, 30.0, 6.0, 13.0, None)],        # raised hatch plate (u0, u1, v0, v1, seam u)
        slots=[(31.0, 34.0, 6.0, 13.0)],               # louvred dark slot
        vents=[(8.0, 10.0, 9.0, 16.4), (12.0, 14.0, 6.0, 15.9)],   # glowing slits in the cap (u0, u1, v0, v1)
        vent_hot_side=+1,                              # the brighter column of each slit (+1: the right one)
        seams=[15.6, 23.0, 31.0, 38.9],                # glacis panel lines
        track_units=[(7.6, 15.0), (23.4, 45.2)],       # front tracks (u0, u1)
    ),
    "b122": dict(
        name="assembly-newsh3-122", pieces=["newsh3-122", "newsh3-124"], mirror=True,
        ribs=[(10.0, 11.0, 2.7, 16.1, 0.45, "rib_hi"), (14.0, 15.0, 3.6, 14.2, 0.3, "rib"),
              (33.6, 34.4, 2.8, 16.1, 0.22, "rib_lo")],
        grooves=[(15.0, 24.0, 5.0, 14.0), (24.0, 33.4, 5.0, 14.0)],
        plates=[(16.0, 23.0, 6.0, 13.0, 18.0), (25.0, 32.6, 6.0, 13.4, 27.0)],
        slots=[],
        vents=[(35.0, 37.0, 6.0, 15.9), (39.0, 41.0, 9.0, 16.4)],
        vent_hot_side=-1,
        seams=[10.1, 18.0, 26.0, 33.4],
        track_units=[(33.8, 41.4), (3.8, 25.6)],
    ),
}


def crawler(key, coll, detail=True, name=None):
    spec = CRAWLERS[key]
    sprite = need_ref(spec["pieces"][0])
    for p in spec["pieces"][1:]:
        sprite["colors"].update(need_ref(p)["colors"])
    M = Mats(sprite, f"n3{key}")
    roof = M("roof", 168)
    capL = M("cap", 166)
    glacis = M("glacis", 164)
    back = M("back", 164)
    shelf = M("shelf", 165)
    lip = M("lip", 167)
    rib_hi = M("rib_hi", 171)
    rib = M("rib", 170)
    rib_lo = M("rib_lo", 166)
    groove = M("groove", 163)
    plate = M("plate", 168 if key == "b86" else 167)
    slot = M("slot", 162, "steel")
    louvre = M("louvre", 164, "steel")
    vent_frame = M("vent_frame", 163, "steel")
    vent_glow = M("vent_glow", 116, "glow", glow=1.0)
    vent_hot = M("vent_hot", 119, "glow", glow=1.2)
    belt = M("belt", 162, "rubber")
    wheel = M("wheel", 163, "steel")
    hub = M("hub", 166, "steel")
    seamm = M("seam", 163)
    mats = {"rib_hi": rib_hi, "rib": rib, "rib_lo": rib_lo}

    b = B(48, 28)
    mir = spec["mirror"]
    U = (lambda u: 49.0 - u) if mir else (lambda u: u)  # 86 hull coordinates -> this sprite's

    # ---- hull: loft along u through the stations, chamfered end rings
    rings = []
    for u in STATIONS:
        if u in (U_L, U_R):
            rings.append([(U(p[0]), p[1], p[2]) for p in profile(u, inset=0.45, dz=0.35)])
        else:
            rings.append([(U(p[0]), p[1], p[2]) for p in profile(u)])
    if mir:
        rings = list(reversed(rings))
    hull_faces = b.loft(rings, roof)
    # colour the hull's faces by what they are (the sprite's region per face)
    for f in hull_faces:
        f.normal_update()
        c = f.calc_center_median()
        nz, ny, nx = f.normal.z, f.normal.y, f.normal.x
        u86 = (49.0 - (c.x / PX + 24)) if mir else (c.x / PX + 24)
        v = 14 - c.y / PX
        if abs(nx) > 0.75:
            f.material_index = capL
        elif nz > 0.5 and (u86 < 15.0 or u86 > 39.0) and v < 14.3:
            f.material_index = capL
        elif nz > 0.9 and v < 14.3:
            f.material_index = roof
        elif ny > 0.3 and nz < 0.9:
            f.material_index = back
        elif v > 16.7:
            f.material_index = glacis
        elif 14.6 < v < 16.0:
            f.material_index = shelf
        elif v >= 16.0:
            f.material_index = lip
        else:
            f.material_index = roof
    if not detail:
        # the sealed shell source: hull plus track blocks
        for u0, u1 in spec["track_units"]:
            b.cbox(u0, u1, TRACK_V[0] - 0.4, TRACK_V[1], 0.0, TRACK_Z, 0.8, belt)
        return b.finish(name or spec["name"] + "_plain", M.list, coll)

    def hz(u):  # roof height in this sprite's coordinates
        return h86(49.0 - u if mir else u)

    # ---- ribs and straps across the roof (raised, chamfered, following the cap slope where they sit on it)
    for u0, u1, v0, v1, dz, kind in spec["ribs"]:
        z0 = min(hz(u0), hz(u1)) - 0.3
        b.sloped([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], [z0] * 4,
                 [hz(u0) + dz, hz(u1) + dz, hz(u1) + dz, hz(u0) + dz], mats[kind])
        # chamfer: a narrower crown
    # ---- hatch pads: a dark panel frame, a raised chamfered plate (with a raised seam strip on 122's)
    for u0, u1, v0, v1 in spec["grooves"]:
        b.cbox(u0, u1, v0, v1, ROOF_H - 0.3, ROOF_H + 0.06, 0.2, groove, chz=0.05)
    for u0, u1, v0, v1, seam_u in spec["plates"]:
        b.cbox(u0, u1, v0, v1, ROOF_H - 0.2, ROOF_H + 0.42, 0.45, plate, chz=0.3)
        if seam_u is not None:
            b.cbox(seam_u, seam_u + 1.0, v0 + 0.2, v1 - 0.2, ROOF_H + 0.2, ROOF_H + 0.62, 0.25, rib, chz=0.15)
        # four bolt heads at the plate's corners
        for bu in (u0 + 0.8, u1 - 0.8):
            for bv in (v0 + 0.8, v1 - 0.8):
                b.cyl((bu, bv, ROOF_H + 0.45), "z", 0.28, 0.08, lip, sides=8)
    for u0, u1, v0, v1 in spec["slots"]:
        b.cbox(u0, u1, v0, v1, ROOF_H - 0.3, ROOF_H + 0.04, 0.15, slot, chz=0.04)
        n = 3
        for i in range(n):
            vv = v0 + (v1 - v0) * (i + 0.75) / (n + 0.5)
            b.cbox(u0 + 0.3, u1 - 0.3, vv - 0.3, vv + 0.3, ROOF_H - 0.1, ROOF_H + 0.3, 0.12, louvre, chz=0.1)
    # ---- glowing vent slits in the cap: a dark steel frame proud of the slope, the glow sunk inside it
    hot = spec["vent_hot_side"]
    for u0, u1, v0, v1 in spec["vents"]:
        za, zb = hz(u0), hz(u1)
        e = 0.35
        b.sloped([(u0 - e, v0 - e), (u1 + e, v0 - e), (u1 + e, v1 + e), (u0 - e, v1 + e)],
                 [min(za, zb) - 0.4] * 4, [za + 0.3, zb + 0.3, zb + 0.3, za + 0.3], vent_frame)
        um = (u0 + u1) / 2
        lo_u, hi_u = (u0, um) if hot > 0 else (um, u1)
        b.sloped([(u0 + 0.12, v0 + 0.15), (u1 - 0.12, v0 + 0.15), (u1 - 0.12, v1 - 0.15), (u0 + 0.12, v1 - 0.15)],
                 [min(za, zb)] * 4, [za + 0.36, zb + 0.36, zb + 0.36, za + 0.36], vent_glow)
        hu0, hu1 = (um, u1 - 0.15) if hot > 0 else (u0 + 0.15, um)
        b.sloped([(hu0, v0 + 0.5), (hu1, v0 + 0.5), (hu1, v1 - 0.4), (hu0, v1 - 0.4)],
                 [min(za, zb)] * 4, [hz(hu0) + 0.42, hz(hu1) + 0.42, hz(hu1) + 0.42, hz(hu0) + 0.42], vent_hot)
        # louvre bars across the slit (machined detail; thin, so the glow still reads)
        for k in range(1, 4):
            vv = v0 + (v1 - v0) * k / 4
            b.sloped([(u0, vv - 0.14), (u1, vv - 0.14), (u1, vv + 0.14), (u0, vv + 0.14)],
                     [min(za, zb)] * 4, [za + 0.44, zb + 0.44, zb + 0.44, za + 0.44], vent_frame)
    # ---- panel lines down the glacis (thin dark strips proud of the slope)
    for su in spec["seams"]:
        top_v, top_z = 16.85, hz(su) - 0.3
        b.sloped([(su - 0.22, top_v), (su + 0.22, top_v), (su + 0.22, TOE - 0.05), (su - 0.22, TOE - 0.05)],
                 [top_z - 0.3, top_z - 0.3, TOE_Z - 0.3, TOE_Z - 0.3],
                 [top_z + 0.08, top_z + 0.08, TOE_Z + 0.06, TOE_Z + 0.06], seamm)
    # ---- tracks: front units (belt, road wheels, hub caps, grousers) and a rear run under the back overhang
    def track(u0, u1, v0, v1, rear=False):
        b.band(stadium(u0, u1, 0.0, TRACK_Z, seg=8), v0, v1, 0.32, belt)
        r = TRACK_Z / 2 - 0.36
        n = max(2, int((u1 - u0 - 2 * r) / 2.1) + 1)
        for i in range(n):
            wu = u0 + TRACK_Z / 2 + (u1 - u0 - TRACK_Z) * i / (n - 1)
            b.cyl((wu, (v0 + v1) / 2, TRACK_Z / 2), "v", r, (v1 - v0) / 2 - 0.12, wheel, sides=10)
            if not rear:
                b.cyl((wu, v1 - 0.06, TRACK_Z / 2), "v", r * 0.45, 0.12, hub, sides=8)
        # grousers across the top run
        k = int((u1 - u0 - TRACK_Z) / 0.9)
        for i in range(k + 1):
            gu = u0 + TRACK_Z / 2 + (u1 - u0 - TRACK_Z) * i / max(k, 1)
            b.cbox(gu - 0.13, gu + 0.13, v0 + 0.05, v1 - 0.05, TRACK_Z - 0.05, TRACK_Z + 0.16, 0.04, belt, chz=0.04)

    for u0, u1 in spec["track_units"]:
        track(u0, u1, TRACK_V[0], TRACK_V[1])
    ru0, ru1 = (16.5, 38.5) if not mir else (49 - 38.5, 49 - 16.5)
    track(ru0, ru1, 2.0 + 0.9, 2.0 + 2.9, rear=True)
    return b.finish(spec["name"], M.list, coll), sprite


# =====================================================================================================
# (b) the forklift: one vehicle, fitted per heading (fork_fit.py: footprint vs each frame's inner mask)
# =====================================================================================================

#: frame: W, L body size; F tine length; g tine centre gap; fw tine width; c rear corner chamfer; nw/nd front notch;
#: s plan scale; th heading (deg, counter-clockwise from up the screen); cx, cy body centre (sprite px).
FORK_PARAMS = {
    14: dict(W=11.75, L=14.0, F=4.0, g=8.0, fw=2.0, c=1.0, nw=3.409, nd=1.5, s=1.0, th=0.38, cx=13.031, cy=13.135),
    16: dict(W=11.0, L=14.0, F=3.5, g=6.177, fw=2.4, c=0.5, nw=4.0, nd=0.057, s=0.96, th=-45.601, cx=11.258, cy=13.468),
    54: dict(W=11.5, L=13.493, F=4.5, g=4.5, fw=2.0, c=1.5, nw=4.899, nd=0.25, s=1.0, th=-88.0, cx=11.915, cy=13.933),
    92: dict(W=10.25, L=13.289, F=3.5, g=5.839, fw=2.0, c=0.5, nw=4.0, nd=0.0, s=1.014, th=-135.0, cx=11.59, cy=13.545),
    90: dict(W=11.834, L=13.5, F=3.354, g=8.0, fw=2.0, c=1.0, nw=3.085, nd=1.5, s=1.0, th=180.0, cx=12.0, cy=13.953),
    88: dict(W=11.327, L=14.5, F=4.0, g=6.0, fw=2.0, c=0.5, nw=4.0, nd=0.0, s=0.915, th=135.0, cx=12.477, cy=13.497),
    50: dict(W=12.0, L=14.0, F=4.0, g=5.0, fw=2.364, c=1.5, nw=4.0, nd=0.25, s=0.99, th=87.926, cx=12.264, cy=13.933),
    12: dict(W=10.338, L=12.612, F=3.547, g=5.074, fw=2.0, c=0.5, nw=3.0, nd=0.447, s=1.05, th=44.761, cx=12.565, cy=13.519),
}
#: model name per frame (the existing five keep their names; 12/50/88 are new)
FORK_MODELS = [(14, "newsh3-14"), (16, "newsh3-14-f2"), (54, "newsh3-14-f3"), (90, "newsh3-14-f4"), (92, "newsh3-14-f5"),
               (12, "newsh3-14-f6"), (50, "newsh3-14-f7"), (88, "newsh3-14-f8")]


def forklift(frame, name, coll, sprite, detail=True):
    p = FORK_PARAMS[frame]
    M = Mats(sprite, "n3fork")
    body = M("body", 168)
    fender_edge = M("edge", 173)
    side = M("side", 166)
    hood = M("hood", 169)
    hood_top = M("hood_top", 171)
    rear = M("rear", 165)
    deck = M("deck", 164)
    carriage = M("carriage", 163, "steel")
    tine = M("tine", 168, "steel", metallic=0.55, roughness=0.4)
    tine_tip = M("tine_tip", 170, "steel", metallic=0.55, roughness=0.4)
    belt = M("belt", 162, "rubber")
    wheel = M("wheel", 165, "steel")

    W, L, F, g, fw, c, nw, nd = p["W"], p["L"], p["F"], p["g"], p["fw"], p["c"], p["nw"], p["nd"]
    hw, hl = W / 2, L / 2
    nwh = max(nw / 2, 1.2)
    # local frame: build with B on a 0-centred grid: u = x (right), v = -y (v grows backward), so forward = -v
    b = B(0, 0)
    Z_POD, Z_HOOD = 2.9, 3.7
    def chamfered(plan, z0, ztops, ch=0.35):
        cu = sum(q[0] for q in plan) / len(plan)
        cv = sum(q[1] for q in plan) / len(plan)
        pts = []
        for (x, v), zt in zip(plan, ztops):
            dx, dv = cu - x, cv - v
            ln = math.hypot(dx, dv) or 1
            pts += [(x, v, z0), (x, v, zt - ch), (x + dx / ln * ch, v + dv / ln * ch, zt)]
        return b.hull(pts, 0)

    mid_v = hl - 3.4
    for s in (-1, 1):
        x_out, x_in = s * hw, s * nwh
        xa, xb = min(x_out, x_in), max(x_out, x_in)
        front_v, rear_v = -hl, hl
        n = chamfered([(x_in, front_v), (x_out - s * 0.5, front_v), (x_out, front_v + 0.5), (x_out, mid_v), (x_in, mid_v)],
                      1.35, [Z_POD] * 5)
        b.tag(n, body)
        n = chamfered([(x_in, mid_v), (x_out, mid_v), (x_out, rear_v - c), (x_out - s * c, rear_v), (x_in, rear_v)],
                      1.35, [Z_POD, Z_POD, 2.0, 1.9, 2.0])
        b.tag(n, rear)
        if detail:
            # lit front edge strip of the fender
            b.cbox(xa + 0.3, xb - 0.3, front_v + 0.1, front_v + 0.9, Z_POD - 0.3, Z_POD + 0.1, 0.2, fender_edge, chz=0.1)
            # track belt under the fender (a loop along v, extruded across the pod), road wheels on its outer side
            _, bverts = b.band(stadium(front_v + 0.4, rear_v - 0.6, 0.0, 1.9, seg=6), xa + 0.15, xb - 0.15, 0.28, belt)
            for vv in bverts:
                x, y, z = vv.co
                vv.co = Vector((-y, -x, z))  # swap the loop onto the v axis and the band across x
            for k in range(3):
                vv_ = front_v + 1.7 + (L - 3.7) * k / 2
                b.cyl((s * (hw - 0.4), vv_, 0.95), "u", 0.62, 0.2, wheel, sides=10)
    # centre hull: deck between the pods, recessed at the front (the notch), raised hood with sloped sides
    front_c = -hl + nd
    b.cbox(-nwh - 0.1, nwh + 0.1, front_c, hl - 0.2, 0.6, 2.0, 0.3, deck)
    if detail:
        hood_pts = []
        for (x, v, z) in [(-nwh + 0.2, front_c + 0.9, 1.9), (nwh - 0.2, front_c + 0.9, 1.9), (nwh - 0.2, hl - 2.4, 1.9),
                          (-nwh + 0.2, hl - 2.4, 1.9)]:
            hood_pts.append((x, v, z))
        hood_pts += [(-nwh + 1.1, front_c + 2.6, Z_HOOD), (nwh - 1.1, front_c + 2.6, Z_HOOD),
                     (nwh - 1.1, hl - 4.6, Z_HOOD), (-nwh + 1.1, hl - 4.6, Z_HOOD)]
        b.hull(hood_pts, hood)
        # the operator's round hatch on the hood (the sprite's lit ring), a vision slit in front of it
        hv = front_c + 3.4
        b.cyl((0.0, hv + 0.6, Z_HOOD + 0.15), "z", min(1.45, nwh - 0.5), 0.2, hood_top, sides=14)
        b.dome((0.0, hv + 0.6, Z_HOOD + 0.3), min(1.05, nwh - 0.8), min(1.05, nwh - 0.8), 0.45, hood, seg=12, rings=3)
        b.cbox(-nwh + 0.9, nwh - 0.9, front_c + 1.5, front_c + 1.9, 2.6, Z_HOOD - 0.1, 0.1, carriage, chz=0.1)
        # rear deck plate sloping to the tail
        b.sloped([(-nwh, hl - 3.0), (nwh, hl - 3.0), (nwh, hl - 0.3), (-nwh, hl - 0.3)], [0.6] * 4,
                 [2.1, 2.1, 1.4, 1.4], rear)
    # fork carriage (dark steel) in the notch, the tines' shanks and the flat tines
    gx = g / 2
    cw = min(gx + fw / 2, hw - 0.1)
    b.cbox(-nwh, nwh, front_c - 0.05, front_c + 0.7, 0.5, 2.7, 0.15, carriage)
    # the mast: two uprights at the front of the pods and a cross head (the sprite's dark bar across the front)
    mx = min(nwh + 0.55, hw - 0.5)
    for s in (-1, 1):
        b.cbox(s * mx - 0.4, s * mx + 0.4, -hl + 0.05, -hl + 0.85, 0.4, 4.3, 0.12, carriage, chz=0.1)
    b.cbox(-mx - 0.4, mx + 0.4, -hl + 0.1, -hl + 0.8, 3.7, 4.4, 0.15, carriage, chz=0.12)
    for s in (-1, 1):
        x0, x1 = s * gx - fw / 2, s * gx + fw / 2
        b.cbox(x0 + 0.1, x1 - 0.1, -hl - 0.35, -hl + 0.5, 0.25, 2.4, 0.15, carriage)  # tine shank on the carriage
        b.cbox(x0, x1, -hl - F, -hl + 0.2, 0.2, 0.75, 0.15, tine, chz=0.1)
        if detail:
            b.cbox(x0 + 0.1, x1 - 0.1, -hl - F, -hl - F + 1.0, 0.25, 0.82, 0.12, tine_tip, chz=0.1)
    # place: plan scale, heading, centre
    sc = p["s"]
    th = math.radians(p["th"])
    rot = Matrix.Rotation(th, 4, "Z")
    # local (x, v) -> (x, -v) is forward-up; B(0,0) mapped (u, v) to (u/12, -v/12): forward (-v) is +Y already
    S = Matrix.Diagonal((sc, sc, 1.0, 1.0))
    T = Matrix.Translation(((p["cx"] - 12) * PX, (14 - p["cy"]) * PX, 0))
    bmesh.ops.transform(b.bm, matrix=T @ rot @ S, verts=b.bm.verts)
    return b.finish(name, M.list, coll)


# =====================================================================================================
# shells, bake, measure, render
# =====================================================================================================

def split_open(obj, layout, coll):
    """common.split_assembly without filling the cuts (for an outline shell: no ink walls at the seams)."""
    result = {}
    for name, cx, cy in layout:
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
        mesh = bpy.data.meshes.new(name + "_outline")
        bm.to_mesh(mesh)
        bm.free()
        for mat in obj.data.materials:
            mesh.materials.append(mat)
        piece = bpy.data.objects.new(name + "_outline", mesh)
        coll.objects.link(piece)
        result[name] = piece
    return result


def sink_shell(shell, model, margin, reach):
    """Keep the outline shell under the model's top surface (D90/D118: ink on the silhouette only)."""
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    mw = shell.matrix_world
    inv = mw.inverted()
    for v in shell.data.vertices:
        w = mw @ v.co
        hit = tree.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        zt = hit[0].z
        for k in range(12):
            a = 2 * math.pi * k / 12
            for rad in (0.35 * reach, 0.7 * reach, reach):
                h = tree.ray_cast(Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)), Vector((0, 0, -1)))
                if h[0] is not None:
                    zt = min(zt, h[0].z)
        zt -= margin
        if w.z > zt:
            v.co = inv @ Vector((w.x, w.y, zt))
    shell.data.update()


def make_shell(src, coll, name, voxel=0.016, faces=4000, inside=0.012, margin=0.05, reach=0.15):
    bpy.context.view_layer.update()
    sh = common.outline_shell(src, coll, voxel=voxel, faces=faces, inside=inside, islands="outer")
    sink_shell(sh, src, margin, reach)
    sh.name = sh.data.name = name
    return sh


def bake_maps(obj, tag, size=1024, samples=48):
    """AO / edge colour and roughness bake from the model (D50/D65); copied from assembly-newsh3-191.py."""
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
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
    bpy.context.view_layer.update()
    for o in bpy.context.scene.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{tag}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{tag}_rm", size // 2, size // 2, alpha=False)
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
                    nt.links.new(v, n.inputs[k])
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
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.5, math_("MULTIPLY", occl, 0.6)),
                                       math_("MULTIPLY", edge, 0.18)), 1.0)
            comb = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(v, comb.inputs[k])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            nt.links.new(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
        nt.links.new(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], tgt.inputs["Vector"])
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
        img.pack()

    for m in mats:
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


def unique_materials(obj, tag):
    """Each model gets its own copies of its materials (bake images are per model)."""
    for i, m in enumerate(list(obj.data.materials)):
        c = m.copy()
        c.name = f"{m.name}__{tag}"
        obj.data.materials[i] = c


def top_grid(objs, w, h, k=8, ox=0.0, oy=0.0):
    """Top-view coverage of `objs` on a w x h sprite grid (k x k rays per pixel); and per pixel the palette index and
    height of the topmost hit at the pixel centre."""
    bm = bmesh.new()
    for o in objs:
        tmp = bmesh.new()
        tmp.from_mesh(o.data)
        tmp.transform(o.matrix_world)
        me = bpy.data.meshes.new("tmp")
        tmp.to_mesh(me)
        tmp.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    bm.faces.ensure_lookup_table()
    # material names by face: rebuild a lookup from the objects in order
    names = []
    for o in objs:
        for p in o.data.polygons:
            names.append(o.data.materials[p.material_index].name if o.data.materials else "")
    tree = BVHTree.FromBMesh(bm)
    top = [[False] * (w * k) for _ in range(h * k)]
    pal, zz = [], []
    for y in range(h * k):
        for x in range(w * k):
            px_, py_ = (x + 0.5) / k, (y + 0.5) / k
            hit = tree.ray_cast(Vector(((px_ - w / 2) * PX + ox, (h / 2 - py_) * PX + oy, 9.0)), Vector((0, 0, -1)))
            top[y][x] = hit[0] is not None
    for r in range(h):
        pr, zr = [], []
        for c in range(w):
            hit = tree.ray_cast(Vector(((c + 0.5 - w / 2) * PX + ox, (h / 2 - r - 0.5) * PX + oy, 9.0)), Vector((0, 0, -1)))
            if hit[0] is None:
                pr.append(-1)
                zr.append(None)
            else:
                nm = names[hit[2]] if hit[2] < len(names) else ""
                try:
                    pr.append(int(nm.split("_")[1]))
                except (IndexError, ValueError):
                    pr.append(-2)
                zr.append(round(hit[0].z, 3))
        pal.append(pr)
        zz.append(zr)
    bm.free()
    return top, pal, zz


# ----- reference masks (tools/sprite_mask.py rules) for --views -----------------------------------------------------

def _decode_frame(index):
    """A 2x2 frame of newsh3.shp straight from the game data (frames the catalogue has no folder for: 12, 50, 88)."""
    import sprite_data
    return sprite_data.compose(sprite_data.data_file(ROOT, "newsh3.shp").read_bytes(), 2, index)


def ref_target(key):
    """(idx rows, colors, masks) for 'b86' | 'b122' | 'spire' | 'fork:<frame>' | 'hatch:<frame>' | a piece name."""
    import sprite_mask as SM
    asm = {"b86": "assembly-newsh3-86", "b122": "assembly-newsh3-122", "spire": "assembly-newsh3-275"}
    if key in asm:
        idx, colors = SM.load(asm[key], ref=REF)
    elif ":" in key:
        kind, fr = key.split(":")
        name = "newsh3-14" if kind == "fork" else "newsh3-18"
        data = json.loads((REF / name / "sprite.json").read_text())
        colors = {int(k): tuple(v) for k, v in data["colors"].items()}
        f = next((f for f in data["frames"] if f["index"] == int(fr)), None)
        idx = [[int(v) for v in r.split()] for r in f["pixels"]] if f else _decode_frame(int(fr))
    else:
        idx, colors = SM.load(key, ref=REF)
    return idx, colors, SM.masks(idx, colors)


def measure_model(objs, key, out, label, ox=0.0, oy=0.0, ground=None):
    """Top-view IoU (sprite_mask.measure) of objs against the target, per-region colour agreement, and a mask PNG."""
    import sprite_mask as SM
    idx, colors, m = ref_target(key)
    if ground is not None:  # pixels that are ground, not the object (D130): transparent for the rule
        for y, row in enumerate(idx):
            for x, v in enumerate(row):
                if ground(x, y, v):
                    for k in ("outer", "inner", "border", "free"):
                        m[k][y][x] = False
    h, w = len(idx), len(idx[0])
    top, pal, zz = top_grid(objs, w, h, k=8, ox=ox, oy=oy)
    res = SM.measure(m, top)
    # colour: model palette index vs the sprite's, inner pixels that are not ink / not highlight extremes
    agree = tot = 0
    for y in range(h):
        for x in range(w):
            if not m["inner"][y][x] or pal[y][x] < 0:
                continue
            s = idx[y][x]
            tot += 1
            if (s >> 4) == (pal[y][x] >> 4) and abs(s - pal[y][x]) <= 2:
                agree += 1
    res["colour_agree"] = round(agree / max(1, tot), 3)
    res["zmax"] = max((z for r in zz for z in r if z is not None), default=0)
    res["tris"] = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    SM.write_png(out / f"{label}_mask.png", [[top[y][x] for x in range(w * 8)] for y in range(h * 8)])
    (out / f"{label}_measure.json").write_text(json.dumps({"key": key, **res, "pal": pal, "z": zz,
                                                           "idx": idx, "inner": m["inner"]}))
    print(f"MEASURE {label} [{key}] iou_rule_grid {res['iou_rule_grid']} rule {res['iou_rule']} "
          f"colour {res['colour_agree']} zmax {res['zmax']:.3f} tris {res['tris']}")
    return res


def render_views(objs, out, label, w_px, h_px, zmax):
    """Lit EEVEE renders of objs: top, game camera (15 deg, as the game), front, side, rear, 3/4 high, underside."""
    scene = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    try:
        scene.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.32, 0.34, 0.38, 1)
    bg.inputs[1].default_value = 0.8
    if "sunA" not in bpy.data.objects:
        sun = bpy.data.lights.new("sunA", "SUN")
        sun.energy = 3.0
        so = bpy.data.objects.new("sunA", sun)
        scene.collection.objects.link(so)
        so.rotation_euler = Vector((-0.5, 0.45, 1.0)).normalized().to_track_quat("Z", "Y").to_euler()
    shown = set(o.name for o in objs)
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o.name not in shown
    W, H = w_px * PX, h_px * PX
    size = max(W, H) * 1.25
    views = {
        "top": ((0, 0, 10), (0, 0, 0), True),
        "game": ((0, -10 * math.sin(math.radians(15)), 10 * math.cos(math.radians(15))), (0, 0, zmax * 0.3), False),
        "front": ((0, -10, zmax * 0.5 + 0.05), (0, 0, zmax * 0.5), True),
        "rear": ((0, 10, zmax * 0.5 + 0.05), (0, 0, zmax * 0.5), True),
        "side": ((10, 0, zmax * 0.5 + 0.05), (0, 0, zmax * 0.5), True),
        "q34": ((6.5, -6.5, 6.0), (0, 0, zmax * 0.3), False),
        "q34w": ((-6.5, -6.5, 5.0), (0, 0, zmax * 0.3), False),
        "under": ((0.01, -2.0, -10), (0, 0, 0), True),
    }
    out = Path(out)
    for vname, (loc, look, ortho) in views.items():
        cd = bpy.data.cameras.new("cam_" + vname)
        if ortho:
            cd.type = "ORTHO"
            cd.ortho_scale = size
        else:
            cd.angle = 2 * math.atan(size * 0.55 / Vector(loc).length)
        cd.clip_start, cd.clip_end = 0.01, 100
        cam = bpy.data.objects.new("cam_" + vname, cd)
        scene.collection.objects.link(cam)
        cam.location = loc
        d = Vector(look) - Vector(loc)
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        scene.camera = cam
        scene.render.film_transparent = True
        scene.render.resolution_x = scene.render.resolution_y = int(os.environ.get("VIEW_PX", "360"))
        scene.render.filepath = str(out / f"{label}_{vname}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam)


# =====================================================================================================
# main
# =====================================================================================================

LAYOUTS = {
    "b86": [("newsh3-84", -12, 0), ("newsh3-86", 12, 0)],
    "b122": [("newsh3-122", -12, 0), ("newsh3-124", 12, 0)],
    "spire": [("newsh3-237", 0, -14), ("newsh3-275", 0, 14)],
}


def build_assembly(key, coll, models, measure):
    whole, sprite = crawler(key, coll) if key in CRAWLERS else BUILDERS[key](coll)
    plain = crawler(key, coll, detail=False) if key in CRAWLERS else BUILDERS[key](coll, detail=False)[0]
    if measure is not None:
        measure.append((key, [whole], key, None))
    layout = LAYOUTS[key]
    pieces = common.split_assembly(whole, layout)
    shell = make_shell(plain, coll, f"{key}_shell", voxel=0.016, faces=8000)
    shells = split_open(shell, layout, coll)
    props = {k: shell[k] for k in shell.keys() if k.startswith("tyrian")}
    for name, _, _ in layout:
        p = pieces[name]
        p.data.shade_smooth()
        p.data.set_sharp_from_angle(angle=math.radians(30))
        if p.data.attributes.get("facet_n") is not None:
            import lib_newshd_rock as RK
            RK.set_facet_normals(p)
        sh = shells[name]
        sh.name = sh.data.name = f"{name}_outline"
        for k, v in props.items():
            sh[k] = v
        sh.data.shade_smooth()
        assert len(sh.data.vertices) > 0, name
        models.append((name, p, sh))
    bpy.data.objects.remove(shell, do_unlink=True)
    bpy.data.objects.remove(plain, do_unlink=True)
    return whole


def build_fork(coll, models, measure):
    sprite = need_ref("newsh3-14")
    for frame, name in FORK_MODELS:
        obj = forklift(frame, name, coll, sprite)
        plain = forklift(frame, name + "_plain", coll, sprite, detail=False)
        obj.data.shade_smooth()
        obj.data.set_sharp_from_angle(angle=math.radians(30))
        sh = make_shell(plain, coll, f"{name}_outline", voxel=0.010, faces=2500, inside=0.006, margin=0.03, reach=0.08)
        bpy.data.objects.remove(plain, do_unlink=True)
        models.append((name, obj, sh))
        if measure is not None:
            measure.append((name, [obj], f"fork:{frame}", None))


# =====================================================================================================
# (c) the spire: a grey stone fang leaning up the screen out of a lava-rock mound (D175 facet ramp on both)
# =====================================================================================================

def _noise1(i, seed):
    x = math.sin(i * 12.9898 + seed * 78.233) * 43758.5453
    return x - math.floor(x)


class SpriteGrid:
    """The few things lib_newshd_rock.facet_ramp needs of its Grid: size, an inner mask, Blender XY -> sprite px."""

    def __init__(self, w, h, inner):
        self.w, self.h, self.inner = w, h, inner

    def uv(self, x, y):
        return x * 12 + self.w / 2, self.h / 2 - y * 12


def spire_regions():
    """(composite idx rows, colours, inner mask, stone mask, rock mask) of the 24 x 56 assembly."""
    idx, colors, m = ref_target("spire")
    inner = m["inner"]
    stone = [[inner[y][x] and 3 <= idx[y][x] <= 12 for x in range(24)] for y in range(56)]
    rock = [[inner[y][x] and (idx[y][x] >= 112 or idx[y][x] in (1, 2)) for x in range(24)] for y in range(56)]
    return idx, colors, inner, stone, rock


def _mask_extent(inner, v):
    r = int(min(max(v, 0), 55))
    cols = [c for c in range(24) if inner[r][c]]
    return (cols[0], cols[-1] + 1) if cols else None


#: the fang's rings, top down: (z px, top row edge, bottom row edge, inset px from the mask's sides)
def mask_outline(mask, w, h, centre=None, steps=96, smooth=1):
    """Radii of the 0.5 contour of `mask` (bilinear at pixel centres) from its centroid (or `centre`), as
    lib_newshd_rock.Grid.outline: [(u, v)] round the outline, and the centre."""
    cells = [(c + 0.5, r + 0.5) for r in range(h) for c in range(w) if mask[r][c]]
    cu = sum(c for c, _ in cells) / len(cells) if centre is None else centre[0]
    cv = sum(r for _, r in cells) / len(cells) if centre is None else centre[1]

    def val(c, r):
        return 1.0 if 0 <= r < h and 0 <= c < w and mask[r][c] else 0.0

    def field(u, v):
        a, b = u - 0.5, v - 0.5
        c0, r0 = math.floor(a), math.floor(b)
        fa, fb = a - c0, b - r0
        return ((1 - fa) * (1 - fb) * val(c0, r0) + fa * (1 - fb) * val(c0 + 1, r0)
                + (1 - fa) * fb * val(c0, r0 + 1) + fa * fb * val(c0 + 1, r0 + 1))
    radii = []
    for k in range(steps):
        a = 2 * math.pi * k / steps
        du, dv = math.cos(a), -math.sin(a)
        t, last = 0.0, 1.0
        while t < 60:
            f = field(cu + du * t, cv + dv * t)
            if f < 0.5:
                t -= 0.02 * (0.5 - f) / max(1e-6, last - f)
                break
            last = f
            t += 0.02
        radii.append(t)
    for _ in range(smooth):
        radii = [(radii[k - 1] + 2 * radii[k] + radii[(k + 1) % steps]) / 4 for k in range(steps)]
    return (cu, cv), [(cu + r * math.cos(2 * math.pi * k / steps), cv - r * math.sin(2 * math.pi * k / steps))
                      for k, r in enumerate(radii)]


#: shoulder profile of a heightfield dome: (ring scale toward the centre, share of the full height)
SHOULDER = [(1.0, 0.0), (0.985, 0.45), (0.96, 0.8), (0.925, 0.95), (0.88, 1.0), (0.8, 1.0), (0.7, 1.0), (0.58, 1.0),
            (0.45, 1.0), (0.32, 1.0), (0.2, 1.0), (0.09, 1.0)]


def dome_field(b, outline, centre, height, mat, grow=0.0, spacing=1.7, seed=1, shoulder=None, rough=0.0):
    """A closed heightfield rock over a plan outline: a steep shoulder band of rings (SHOULDER) round the outline,
    its top an irregular triangulation (constrained Delaunay over jittered points) at z = height(u, v), so the
    facets never line up into radial spokes."""
    from mathutils.geometry import delaunay_2d_cdt
    cu, cv = centre
    n = len(outline)
    band = shoulder or [sv for sv in SHOULDER if sv[0] >= 0.88]
    rings = []
    for i, (s, f) in enumerate(band):
        ring = []
        for k in range(n):
            t = 0.42 * math.sin(i * 1.73 + k * 2.31) if i > 1 else 0.0
            k0, k1 = (k, (k + 1) % n) if t >= 0 else (k, (k - 1) % n)
            (ua, va), (ub, vb_) = outline[k0], outline[k1]
            u, v = ua + (ub - ua) * abs(t), va + (vb_ - va) * abs(t)
            du, dv = u - cu, v - cv
            ln = math.hypot(du, dv) or 1
            jit = 0.0
            if 0 < i < len(band) - 1:  # rough the walls (inward only: the foot ring keeps the silhouette)
                jit = -rough * (0.25 + 0.75 * _noise1(k * 17 + i * 101, seed + 5))
            pu = cu + s * du + du / ln * (grow * s + jit)
            pv = cv + s * dv + dv / ln * (grow * s + jit)
            ring.append((pu, pv, height(pu, pv) * f))
        rings.append(ring)
    bm = b.bm
    vr = [[bm.verts.new(b.P(*p)) for p in ring] for ring in rings]
    out = []
    for r0, r1 in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            out.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    out.append(bm.faces.new(list(reversed(vr[0]))))
    # the top: jittered grid points inside the innermost ring, triangulated with the ring as the constraint
    inner = rings[-1]
    poly = [(p[0], p[1]) for p in inner]

    def inside(u, v):
        c = False
        for i in range(n):
            (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
            if (y1 > v) != (y2 > v) and u < (x2 - x1) * (v - y1) / (y2 - y1 + 1e-12) + x1:
                c = not c
        return c
    us = [p[0] for p in poly]
    vs = [p[1] for p in poly]
    pts = list(poly)
    gu = min(us)
    while gu <= max(us):
        gv = min(vs)
        row = 0
        while gv <= max(vs):
            ju = (_noise1(int(gu * 7.3) * 131 + int(gv * 5.1), seed) - 0.5) * spacing * 0.7
            jv = (_noise1(int(gu * 3.7) * 71 + int(gv * 9.3), seed + 1) - 0.5) * spacing * 0.7
            u, v = gu + ju, gv + jv
            if inside(u, v) and min(math.hypot(u - a, v - c) for a, c in poly) > spacing * 0.55:
                pts.append((u, v))
            gv += spacing
            row += 1
        gu += spacing * 0.92
    res = delaunay_2d_cdt([Vector(p) for p in pts], [(i, (i + 1) % n) for i in range(n)], [list(range(n))], 1, 1e-6)
    cverts, cedges, cfaces, orig_v = res[0], res[1], res[2], res[3]
    vmap = []
    for k, co in enumerate(cverts):
        ov = orig_v[k] if k < len(orig_v) else []
        if ov and ov[0] < n:
            vmap.append(vr[-1][ov[0]])
        else:
            vmap.append(bm.verts.new(b.P(co.x, co.y, height(co.x, co.y))))
    for f in cfaces:
        try:
            out.append(bm.faces.new([vmap[i] for i in f]))
        except ValueError:
            pass
    for f in out:
        f.material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=out)
    return out


def fang_height(u, v):
    """The stone fang's top: a flat lit plateau at the upper end, a long face sloping down the screen, a crest
    left of the middle (the sprite's lit left / dark right halves)."""
    if v <= 12.6:
        z = 21.0 - (v - 7.0) * 0.08
    else:
        z = 21.0 - 0.45 - 15.5 * ((v - 12.6) / 24.4) ** 0.85
    uc = 14.6 - 0.09 * max(0.0, v - 10.0)
    hw = 6.2 - 0.07 * max(0.0, v - 12.0)
    x = (u - uc) / max(hw, 1.0)
    crest = 1.0 - 0.10 * min(1.0, abs(x - (-0.15)) ** 1.6) if v > 12.0 else 1.0
    return max(1.0, z * crest)


def mound_height(u, v):
    from mathutils import noise
    d = math.hypot((u - 12.5) / 7.0, (v - 33.0) / 9.0)
    z = 4.2 + 3.6 * math.exp(-d * d)
    z *= 1.0 - 0.35 * max(0.0, min(1.0, (v - 42.0) / 10.0))
    p = Vector((u * 0.33, v * 0.33, 0.7))
    z += 1.6 * noise.noise(p) + 0.8 * noise.noise(p * 2.1 + Vector((3.1, 1.7, 0)))
    return max(1.2, z)


def chip_planes(bm, size_px=2.0):
    """lib_newshd_rock.chip_planes (D175), copied with two fixes: the face list is refreshed before each axis (the
    library's goes stale after the last cut of the first axis and fails on a face it already split), and a face
    looking straight down (the flat bottom) is left whole."""
    step = size_px / 12
    planes = []
    for f in bm.faces:
        if len(f.verts) > 4 and f.calc_area() > (1.5 * step) ** 2 and f.normal.z > -0.9:
            n = f.normal.copy()
            planes.append((n, f.calc_center_median().dot(n)))
    for n, d in planes:
        a = n.cross(Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))).normalized()
        b = n.cross(a).normalized()

        def on_plane(f):
            return f.is_valid and f.normal.dot(n) > 0.9999 and abs(f.calc_center_median().dot(n) - d) < 1e-4
        for axis in (a, b):
            faces = [f for f in bm.faces if on_plane(f)]
            if not faces:
                break
            proj = [v.co.dot(axis) for f in faces for v in f.verts]
            lo, hi = min(proj), max(proj)
            k = math.floor(lo / step) + 1
            while k * step < hi - step * 0.25:
                faces = [f for f in bm.faces if on_plane(f)]
                if not faces:
                    break
                geom = list({x for f in faces for x in (*f.verts, *f.edges)}) + faces
                bmesh.ops.bisect_plane(bm, geom=geom, plane_co=axis * (k * step), plane_no=axis)
                k += 1


def spire(coll, detail=True):
    import lib_newshd_rock as RK
    idx, colors, inner, stone, rock = spire_regions()
    sprite = need_ref("newsh3-237")
    sprite["colors"].update(need_ref("newsh3-275")["colors"])
    sprite["frames"] = [{"pixels": idx, "width": 24, "height": 56}]
    stone_m = mat_of(sprite, "n3spire_stone", 7, "rock")
    rock_m = mat_of(sprite, "n3spire_rock", 114, "rock")
    # --- the fang: a heightfield rock over the mask's upper part (rows 7-37), cut by fracture planes
    fang_mask = [[inner[r][c] and r <= 36 and (r <= 22 or 7 <= c <= 19) for c in range(24)] for r in range(56)]
    fb = B(24, 56)
    centre, outline = mask_outline(fang_mask, 24, 56, steps=88)
    dome_field(fb, outline, centre, fang_height, 0, spacing=1.6, seed=7,
               shoulder=[(1.0, 0.0), (0.99, 0.12), (0.975, 0.26), (0.955, 0.4), (0.93, 0.54), (0.9, 0.68), (0.865, 0.8),
                         (0.83, 0.9), (0.79, 0.97), (0.76, 1.0)], rough=0.7)
    if detail:
        RK.cut_planes(fb.bm, [(100, 50, 0.03), (160, 35, 0.03), (20, 40, 0.028), (230, 45, 0.03), (300, 30, 0.025),
                              (60, 65, 0.02), (200, 65, 0.02), (330, 55, 0.022), (130, 20, 0.025),
                              (75, 12, 0.03), (95, 25, 0.025), (115, 8, 0.03), (85, 40, 0.02), (180, 10, 0.02),
                              (0, 12, 0.02), (250, 25, 0.02), (290, 60, 0.018),
                              (40, 2, 0.02), (140, -2, 0.02), (200, 4, 0.018), (330, 3, 0.018), (65, 4, 0.02),
                              (110, 3, 0.02), (170, 5, 0.018), (10, -3, 0.018)])
        chip_planes(fb.bm, 2.0)
    for f in fb.bm.faces:
        f.material_index = 0
    # --- the mound: a lumpy heightfield of lava rock over the mask's lower part, round the fang's foot
    mound_mask = [[inner[r][c] and r >= 21 for c in range(24)] for r in range(56)]
    mb = B(24, 56)
    centre, outline = mask_outline(mound_mask, 24, 56, steps=96)
    dome_field(mb, outline, centre, mound_height, 1, rough=0.5, seed=3)
    if detail:
        RK.cut_planes(mb.bm, [(az, el, d) for az, el, d in [
            (200, 40, 0.05), (250, 30, 0.045), (290, 45, 0.045), (330, 28, 0.04), (20, 35, 0.045), (60, 50, 0.035),
            (110, 30, 0.045), (150, 45, 0.04), (180, 22, 0.04), (230, 60, 0.03), (270, 18, 0.035), (310, 65, 0.025),
            (0, 60, 0.025), (90, 65, 0.025), (135, 70, 0.02), (45, 18, 0.03)]])
        chip_planes(mb.bm, 2.0)
    for f in mb.bm.faces:
        f.material_index = 1
    # flat bottom: drop anything below the ground
    for bb in (fb, mb):
        for v in bb.bm.verts:
            if v.co.z < 0:
                v.co.z = 0.0
        bmesh.ops.remove_doubles(bb.bm, verts=bb.bm.verts, dist=1e-6)
        bmesh.ops.triangulate(bb.bm, faces=bb.bm.faces[:])
    stone_obj = fb.finish("spire_stone", [stone_m, rock_m], coll)
    rock_obj = mb.finish("spire_rock", [stone_m, rock_m], coll)
    # one object (the same two material slots on both)
    bm = bmesh.new()
    bm.from_mesh(stone_obj.data)
    bm.from_mesh(rock_obj.data)
    nm = "assembly-newsh3-275" if detail else "assembly-newsh3-275_plain"
    me = bpy.data.meshes.new(nm)
    bm.to_mesh(me)
    bm.free()
    for m in (stone_m, rock_m):
        me.materials.append(m)
    obj = bpy.data.objects.new(nm, me)
    coll.objects.link(obj)
    bpy.data.objects.remove(stone_obj, do_unlink=True)
    bpy.data.objects.remove(rock_obj, do_unlink=True)
    if not detail:
        return obj, sprite
    obj.data.shade_smooth()
    flat = {}
    spec = {"mid": 7, "metallic": 0.05, "roughness": 0.72, "ramp": {"sprite": 0.6}}
    RK.facet_ramp(sprite, SpriteGrid(24, 56, stone), obj, spec, mid=7, slot=0, flat=flat)
    spec_r = {"mid": 114, "metallic": 0.05, "roughness": 0.7, "ramp": {"sprite": 0.65}}
    RK.facet_ramp(sprite, SpriteGrid(24, 56, rock), obj, spec_r, mid=114, slot=1, flat=flat)
    RK.set_facet_normals(obj, flat)
    if detail:
        # a few glowing lava seams in the mound's cracks (thin emissive ribbons where the sprite glows)
        pass
    return obj, sprite


# =====================================================================================================
# (d) the floor hatch
# =====================================================================================================

HATCH_FRAMES = [
    (18, "newsh3-18", dict(upper=(4.0, 13.0), lower=(13.5, 22.0), crease_u=((17.5, 7.0), (5.5, 12.2)),
                           crease_l=((5.0, 16.6), (17.5, 21.2)), head=None)),
    (56, "newsh3-18-f2", dict(upper=(4.0, 11.0), lower=(16.0, 22.0), crease_u=((16.0, 6.0), (5.5, 10.2)),
                              crease_l=((5.0, 18.0), (17.5, 21.3)), head=2.6)),
    (94, "newsh3-18-f3", dict(upper=(4.0, 9.0), lower=(18.0, 22.0), crease_u=None, crease_l=None, head=3.9)),
    (284, "newsh3-18-f4", dict(upper=(4.0, 7.0), lower=(20.0, 22.0), crease_u=None, crease_l=None, head=5.2)),
]
DECK, PLINTH, RIM = 1.0, 2.2, 2.9
PIT = 0.9
LEAF = 1.75


def clip_half(poly, a, b, keep_left):
    """Sutherland-Hodgman: the part of convex polygon `poly` [(u, v)] left (or right) of the line a->b."""
    def side(p):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    out = []
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        sp, sq = side(p), side(q)
        inp, inq = (sp >= 0) == keep_left, (sq >= 0) == keep_left
        if inp:
            out.append(p)
        if inp != inq:
            t = sp / (sp - sq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def hatch_frame(name, st, coll, sprite, detail=True):
    M = Mats(sprite, "n3hatch")
    deck = M("deck", 5, "steel", metallic=0.5, roughness=0.55)
    seam = M("seam", 3, "steel")
    ridge = M("ridge", 7, "steel", metallic=0.5, roughness=0.45)
    plinth = M("plinth", 5, "steel", metallic=0.5, roughness=0.5)
    rim_lit = M("rim_lit", 73, "armour", metallic=0.45, roughness=0.45)
    rim_dark = M("rim_dark", 72, "armour", metallic=0.45, roughness=0.5)
    pit = M("pit", 2, "steel", metallic=0.3, roughness=0.8)
    leaf = M("leaf", 4, "steel", metallic=0.55, roughness=0.45)
    leaf_lip = M("leaf_lip", 5, "steel", metallic=0.55, roughness=0.4)
    head = M("head", 6, "steel", metallic=0.6, roughness=0.4)
    head_dark = M("head_dark", 3, "steel", metallic=0.6, roughness=0.5)
    eye = M("eye", 117, "glow", glow=1.0)
    eye_hot = M("eye_hot", 119, "glow", glow=1.25)
    eye_core = M("eye_core", 123, "glow", glow=1.1)
    b = B(24, 28)
    # deck plate: the whole tile (the platform the hatches are set in), seams and a lit rail as geometry
    if detail:
        b.cbox(0.0, 24.0, 0.0, 28.0, 0.0, DECK, 0.0, deck, chz=0.0)
    # the housing (plinth) round the pit, chamfered, as four walls so the pit is open
    if detail:
        b.cbox(2.0, 24.0, 1.8, 2.6, DECK - 0.3, DECK + 0.05, 0.1, seam, chz=0.05)      # seam above the housing
        b.cbox(1.8, 2.6, 0.0, 28.0, DECK - 0.3, DECK + 0.05, 0.1, seam, chz=0.05)      # seam left of it
        b.cbox(20.9, 21.9, 4.8, 24.9, DECK - 0.2, DECK + 0.5, 0.35, ridge, chz=0.3)    # lit rail right of it
        b.cbox(3.0, 21.9, 23.9, 24.9, DECK - 0.2, DECK + 0.5, 0.35, ridge, chz=0.3)    # and below it
        b.cbox(0.0, 1.8, 14.8, 15.9, DECK - 0.2, DECK + 0.35, 0.3, ridge, chz=0.25)    # rail stub on the left
    wall = [(3.0, 20.0, 3.0, 4.0), (3.0, 20.0, 22.0, 23.0), (3.0, 4.0, 3.0, 23.0), (19.0, 20.0, 3.0, 23.0)]
    for u0, u1, v0, v1 in wall:
        b.cbox(u0, u1, v0, v1, DECK - 0.2, PLINTH, 0.0, plinth, chz=0.0)
    # the salmon coaming on top: lit on the left and top, shaded on the right and bottom; chamfered crown
    b.cbox(3.0, 4.2, 3.0, 23.0, PLINTH - 0.1, RIM, 0.3, rim_lit, chz=0.3)
    b.cbox(3.0, 20.0, 3.0, 4.2, PLINTH - 0.1, RIM, 0.3, rim_lit, chz=0.3)
    b.cbox(18.8, 20.0, 3.4, 23.0, PLINTH - 0.1, RIM - 0.02, 0.3, rim_dark, chz=0.3)
    b.cbox(3.4, 20.0, 21.8, 23.0, PLINTH - 0.1, RIM - 0.02, 0.3, rim_dark, chz=0.3)
    # pit floor
    b.cbox(4.0, 19.0, 4.0, 22.0, DECK - 0.2, PIT + 0.1, 0.0, pit, chz=0.0)
    if not detail:
        if st["head"] is not None and st["head"] > PLINTH:  # a head standing above the coaming gets its ink too
            b.cbox(8.2, 14.8, 10.0, 16.4, PIT, st["head"] + 0.6, 0.6, head, chz=0.5)
        return b.finish(name + "_plain", M.list, coll)

    # the two leaves: slid back under the coaming; a valley crease across each (the sprite's light/dark diagonal)
    def leaf_plate(v0, v1, crease, lip_top=False):
        rect = [(4.0, v0), (19.0, v0), (19.0, v1), (4.0, v1)]
        z0, zt = LEAF - 0.6, LEAF
        if crease is None:
            b.cbox(4.0, 19.0, v0, v1, z0, zt, 0.15, leaf, chz=0.12)
        else:
            a, c = crease
            for keep in (True, False):
                half = clip_half(rect, a, c, keep)
                if len(half) < 3:
                    continue
                pts = []
                for (u, v) in half:
                    on_line = abs((c[0] - a[0]) * (v - a[1]) - (c[1] - a[1]) * (u - a[0])) < 1e-4
                    pts += [(u, v, z0), (u, v, zt - (0.32 if on_line else 0.0))]
                b.hull(pts, leaf)
        if lip_top:  # the lower leaf's lit leading edge (a rolled lip)
            b.cbox(4.2, 18.8, v0, v0 + 0.9, LEAF - 0.3, LEAF + 0.22, 0.25, leaf_lip, chz=0.2)

    u0, u1 = st["upper"]
    leaf_plate(u0, u1, st["crease_u"])
    l0, l1 = st["lower"]
    leaf_plate(l0, l1, st["crease_l"], lip_top=True)
    top = st["head"]
    if top is not None:
        # the turret head: an armoured block on a ram, flanked by hydraulic arms, the red eye on top
        b.cyl((11.5, 13.2, (PIT + top - 2.0) / 2), "z", 1.5, (top - 2.0 - PIT) / 2 + 0.05, head_dark, sides=12)
        b.cbox(8.2, 14.8, 10.0, 16.4, top - 2.0, top, 0.6, head, chz=0.5)
        b.cbox(8.6, 14.4, 15.4, 16.6, top - 1.7, top - 0.5, 0.3, head_dark, chz=0.2)  # vent lip at the back
        b.cyl((11.5, 12.9, top), "z", 2.45, 0.12, head_dark, sides=16)               # eye bezel
        b.dome((11.5, 12.9, top + 0.1), 2.2, 1.85, 1.0, eye, seg=16, rings=5)
        b.dome((11.6, 12.7, top + 0.45), 1.3, 1.1, 0.85, eye_hot, seg=12, rings=4)
        b.dome((11.7, 12.4, top + 0.95), 0.55, 0.5, 0.45, eye_core, seg=10, rings=3)
        if top > 3.0:
            for s in (-1, 1):  # hydraulic arms from the pit floor to the head's flanks
                bu = 11.5 + s * 5.2
                tu = 11.5 + s * 3.4
                for dv in (11.2, 15.0):
                    pts = []
                    for (uu, zz) in ((bu, PIT + 0.1), (tu, top - 1.2)):
                        for du in (-0.35, 0.35):
                            for dz in (-0.35, 0.35):
                                pts.append((uu + du, dv + dz * 0.8, zz + dz))
                    b.hull(pts, head_dark)
        if top > 4.5:
            # the lift frame's cross bars above and below the head (the sprite's two dark bars)
            b.cbox(7.2, 17.0, 8.2, 9.0, top - 0.9, top - 0.3, 0.2, head_dark, chz=0.15)
            b.cbox(8.0, 18.2, 16.9, 17.7, PIT + 0.2, PIT + 1.6, 0.2, head_dark, chz=0.15)
    return b.finish(name, M.list, coll)


def build_hatch(coll, models, measure):
    sprite = need_ref("newsh3-18")
    for frame, name, st in HATCH_FRAMES:
        obj = hatch_frame(name, st, coll, sprite)
        plain = hatch_frame(name, st, coll, sprite, detail=False)
        obj.data.shade_smooth()
        obj.data.set_sharp_from_angle(angle=math.radians(30))
        # the outline: round the housing only (the deck plate meets its neighbours edge to edge, so no ink there)
        sh = make_shell(plain, coll, f"{name}_outline", voxel=0.012, faces=2500, inside=0.006, margin=0.03,
                        reach=0.08)
        bpy.data.objects.remove(plain, do_unlink=True)
        models.append((name, obj, sh))
        if measure is not None:
            measure.append((name, [obj], f"hatch:{frame}", None))


BUILDERS = {"spire": spire, "hatch": build_hatch}
GROUPS = ["b86", "b122", "fork", "spire", "hatch"]



SPRITES_OF = {}


def _sprites(name):
    """The spriteModels `sprites` entry of a model: its own sprite for a piece, one frame for the forklift/hatch."""
    for frame, nm in FORK_MODELS:
        if nm == name:
            return frame_subset(need_ref("newsh3-14"), [frame])
    for frame, nm, _ in HATCH_FRAMES:
        if nm == name:
            return frame_subset(need_ref("newsh3-18"), [frame])
    return need_ref(name)["sprites"]


def frame_subset(sprite, frames):
    ref = sprite["sprites"][0]
    return [{"sheet": ref["sheet"], "size": ref["size"], "frames": list(frames)}]


def run(group):
    """Build one group (b86, b122, fork, spire, hatch) and export only its models."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

    def arg(flag, default=None):
        return argv[argv.index(flag) + 1] if flag in argv else default
    views = arg("--views")
    game = arg("--game")
    only = [group]
    bake = "--nobake" not in argv
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection("newsh3_" + group)
    models, measure, wholes = [], ([] if views else None), {}
    for g in only:
        if g in ("b86", "b122", "spire"):
            wholes[g] = build_assembly(g, coll, models, measure)
        elif g == "fork":
            build_fork(coll, models, measure)
        elif g == "hatch":
            BUILDERS["hatch"](coll, models, measure)
    # review outputs (behind --views): measurements on the unbaked models, renders
    if views:
        vdir = Path(views)
        vdir.mkdir(parents=True, exist_ok=True)
        summary = {}
        for label, objs, key, ground in measure:
            summary[label] = measure_model(objs, key, vdir, label, ground=ground)
        for name, obj, sh in models:
            if name.startswith("newsh3-"):
                piece_key = name
                try:
                    summary[name + "@own"] = measure_model([obj], piece_key, vdir, name + "_own")
                except Exception as err:  # noqa: BLE001  (a frame without a catalogue folder)
                    print("no own mask for", name, err)
        (vdir / "summary.json").write_text(json.dumps(summary, indent=1))
    for name, obj, sh in models:
        obj.hide_render = sh.hide_render = False
    for w in wholes.values():
        w.hide_render = True
    if bake:
        for name, obj, sh in models:
            sh.hide_render = True
        for name, obj, sh in models:
            for o2, _, s2 in [(m[1], 0, m[2]) for m in models]:
                o2.hide_render = o2 is not obj
            unique_materials(obj, name.replace("-", "_"))
            bake_maps(obj, name.replace("-", "_"))
        for name, obj, sh in models:
            obj.hide_render = False
    if views:
        vdir = Path(views)
        for g, w in wholes.items():
            wsz = {"b86": (48, 28), "b122": (48, 28), "spire": (24, 56)}[g]
            zmax = max((w.matrix_world @ v.co).z for v in w.data.vertices)
            w.hide_render = False
            render_views([w], vdir, g, wsz[0], wsz[1], zmax)
            w.hide_render = True
        for name, obj, sh in models:
            if name.startswith("newsh3-14") or name.startswith("newsh3-18"):
                zmax = max(v.co.z for v in obj.data.vertices)
                render_views([obj], vdir, name, 24, 28, zmax)
    fmt = "WEBP" if bake else "AUTO"
    for g, w in wholes.items():
        bpy.data.objects.remove(w, do_unlink=True)
    for name, obj, sh in models:
        common.export_sprite_model(ROOT, [obj, sh], f"enemies/{name}", _sprites(name), image_format=fmt)
        if game:
            common.export_glb([obj, sh], Path(game) / f"{name}.glb", image_format=fmt)
    for name, obj, sh in models:
        assert len(sh.data.vertices) > 0, f"{name}_outline has no mesh"
        tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        print(f"MODEL {name}: {tris} tris, shell {len(sh.data.vertices)} verts")
