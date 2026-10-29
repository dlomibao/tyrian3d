"""Spinning brown pod (newsh2.shp frames 171, 190, 209, 228, 247, 266): a 3D version of its sprite.

Seen in episodes 1, 2 and 3 (levels 1.25, 1.3, 2.6, 3.17). A brown teardrop, blunt at the top
and pointed at the bottom, flattened so that it is 9 px wide face on (frame 171) and 5 px edge on
(frame 228). The six frames spin it about its long axis (the sprite's vertical): its silhouette
narrows and widens and the light ridges slide across. Each frame is the same pod turned to a
different angle, so each frame gets its own model (newsh2-171, -f2 ... -f6), turned to match.

The pod is hard-surface armour (assets/blender/features/newsh2-171.json): a faceted shell with a
shoulder facet each side of a raised spine down the middle of each face, a glass lens set in the
spine, a groove cut round the shoulder, and a crisp keel with a light rib along both edges. It spins in the air just above the ground.

Run: blender --background --python assets/blender/enemies/newsh2-171.py [-- --preview out.png]
(each extra model's preview goes next to out.png as <name>-fN.png).
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b083 as lib  # noqa: E402

NAME = "newsh2-171"
ROOT = common.repo_root(__file__)
G = lib.Grid(12, 14)
AXIS_U = 6.5  # the pod's long axis runs down the centre of column 6
SPIN_Z = 0.38  # height of the spin axis: the pod's tip just clears the ground edge on
# Turn per frame (degrees); the sprite's silhouettes put frames 2-5 between 40 and 140 degrees.
ANGLES = [0, 45, 65, 90, 115, 135]

# Profile down the pod: (v pixel edge from the top, half width face on, half thickness), px.
PROFILE = [(0.35, 1.2, 0.8), (0.7, 2.4, 1.5), (1.2, 3.4, 2.1), (1.8, 4.1, 2.45), (2.5, 4.6, 2.6),
           (4.5, 4.6, 2.6), (5.0, 4.1, 2.5), (5.6, 3.7, 2.45), (6.6, 3.35, 2.3), (7.2, 2.9, 1.95),
           (8.6, 2.4, 1.6), (9.2, 1.9, 1.45), (10.6, 1.35, 1.1), (11.2, 0.9, 0.75), (12.4, 0.45, 0.4),
           (13.0, 0.0, 0.0)]


def profile_at(v):
    for (v0, a0, b0), (v1, a1, b1) in zip(PROFILE, PROFILE[1:]):
        if v0 <= v <= v1:
            t = (v - v0) / (v1 - v0)
            return a0 + (a1 - a0) * t, b0 + (b1 - b0) * t
    return 0.0, 0.0


# The shell's cross-section (unit half width, unit half thickness): hard-surface armour with a
# crisp keel at each edge (the first vertex), a shoulder facet each side and a flat face on top
# and bottom for the spine to sit on.
SHELL = [(1.0, 0.0), (0.8, 0.6), (0.36, 1.0), (-0.36, 1.0), (-0.8, 0.6), (-1.0, 0.0),
         (-0.8, -0.6), (-0.36, -1.0), (0.36, -1.0), (0.8, -0.6)]
# The spine's section (unit half width, height above its base): a flat-topped bevelled strip.
SPINE = [(1.0, -0.5), (0.62, 1.0), (-0.62, 1.0), (-1.0, -0.5)]
# The edge rib's section, in px from the keel vertex (x outward, z up): a thin bevelled strip.
RIB = [(0.3, 0.0), (0.0, 0.55), (-0.8, 0.45), (-0.8, -0.45), (0.0, -0.55)]
GROOVE = (2.75, 3.6, 0.87)  # the shoulder groove: rows, inset scale


def facet_loft(bm, rings_spec, shape, seg_mats):
    """Loft rings along Y; ring k is (y, scale_x, scale_z, x0, z0) applied to `shape` (a ring
    with zero scale is a point). seg_mats[k] is the material between rings k and k+1. Every
    edge running along the length is marked sharp, so the facets stay crisp."""
    rings = []
    for y, sx, sz, x0, z0 in rings_spec:
        if sx == 0 and sz == 0:
            rings.append([bm.verts.new((x0, y, z0))])
        else:
            rings.append([bm.verts.new((x0 + sx * u, y, z0 + sz * w)) for u, w in shape])
    n = len(shape)
    for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = seg_mats[k]
        for i in range(n):
            a, b = r0[min(i, len(r0) - 1)], r1[min(i, len(r1) - 1)]
            e = bm.edges.get((a, b))
            if e is not None:
                e.smooth = False
        if len(r0) > 1 and len(r1) > 1 and abs(r0[0].co.y - r1[0].co.y) < 1e-6:
            for r in (r0, r1):  # a step (the groove's walls): crisp rims
                for i in range(n):
                    e = bm.edges.get((r[i], r[(i + 1) % n]))
                    if e is not None:
                        e.smooth = False
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        if len(ring) > 1:
            f = bm.faces.new(list(reversed(ring)) if rev else ring)
            f.material_index = seg_mats[0] if rev else seg_mats[-1]
            for e in f.edges:
                e.smooth = False


def build_mesh(mats_idx):
    """The pod lying along Y with its faces up (+Z), centred on its axis at the origin."""
    BODY, BAND, RIDGE, LENS, TIP, SPINE_LO, RIBM = mats_idx
    bm = bmesh.new()
    y = G.y
    P = lib.PX
    g0, g1, inset = GROOVE

    # Shell: the profile with the groove cut in round the shoulder.
    vs = [v for v, _, _ in PROFILE if v < g0 or v > g1]
    rings, mats, cut = [], [], []
    for v in sorted(set(vs + [g0, g1])):
        a, b = profile_at(v)
        if v == g0:
            rings += [(y(v), a * P, b * P, 0.0, 0.0), (y(v), a * inset * P, b * inset * P, 0.0, 0.0)]
            cut += [False, True]
        elif v == g1:
            rings += [(y(v), a * inset * P, b * inset * P, 0.0, 0.0), (y(v), a * P, b * P, 0.0, 0.0)]
            cut += [True, False]
        elif a == 0:
            rings.append((y(v), 0.0, 0.0, 0.0, 0.0))
            cut.append(False)
        else:
            rings.append((y(v), a * P, b * P, 0.0, 0.0))
            cut.append(False)
    for k in range(len(rings) - 1):
        vmid = G.h / 2 - (rings[k][0] + rings[k + 1][0]) / 2 / P
        if cut[k] or cut[k + 1]:
            mats.append(BAND)
        else:
            mats.append(BODY if vmid < 6.6 else TIP)
    facet_loft(bm, rings, SHELL, mats)

    for sgn in (1, -1):
        # Spine down the middle of each face, bridging the groove, with a glass lens at row 5.
        shape = [(u, sgn * w) for u, w in SPINE]
        spine_v = [2.45, 2.75, 3.6, 4.5, 5.5, 6.6, 7.6, 8.6, 9.6, 10.6, 11.5, 12.1]
        rings, mats = [], []
        for v in spine_v:
            _, b = profile_at(v)
            hw = 0.75 if v <= 6.6 else 0.75 - (v - 6.6) / (12.1 - 6.6) * 0.5
            h = 0.6
            if v == spine_v[0]:
                hw, h = hw * 0.55, 0.3
            if v == spine_v[-1]:
                hw, h = hw * 0.7, 0.3
            rings.append((y(v), hw * P, h * P, 0.0, sgn * (b - 0.1) * P))
        for v0, v1 in zip(spine_v, spine_v[1:]):
            mats.append(RIDGE if (v0 + v1) / 2 < 7.6 else SPINE_LO)
        facet_loft(bm, rings, shape, mats)

        lens_rings = []
        for v, hw in ((4.5, 0.22), (4.8, 0.45), (6.0, 0.45), (6.3, 0.22)):
            _, b = profile_at(v)
            lens_rings.append((y(v), hw * P, 0.26 * P, 0.0, sgn * (b + 0.32) * P))
        facet_loft(bm, lens_rings, [(1.0, -0.4 * sgn), (0.7, 1.0 * sgn), (-0.7, 1.0 * sgn), (-1.0, -0.4 * sgn)],
                   [LENS] * 3)

        # A thin light rib along the keel at each edge.
        rib = [(sgn * u, w) for u, w in RIB]
        rib_v = [1.4 + (11.6 - 1.4) * i / 10 for i in range(11)]
        rings = []
        for k, v in enumerate(rib_v):
            a, _ = profile_at(v)
            scale = 0.5 if k in (0, len(rib_v) - 1) else 1.0
            rings.append((y(v), scale * P, scale * P, sgn * a * P, 0.0))
        facet_loft(bm, rings, rib, [RIBM] * (len(rib_v) - 1))
    return bm


def build(sprite, angle, name, coll):
    tag = "nsh2_171"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(22, metallic=0.35, roughness=0.45),  # 0 brown armour shell
        pal(18, metallic=0.2, roughness=0.6),  # 1 dark groove
        pal(27, metallic=0.45, roughness=0.35),  # 2 light spine
        pal(30, metallic=0.0, roughness=0.08, emission_strength=0.5),  # 3 glass lens
        pal(20, metallic=0.3, roughness=0.5),  # 4 darker lower point
        pal(21, metallic=0.35, roughness=0.45),  # 5 spine toward the point
        pal(25, metallic=0.45, roughness=0.35),  # 6 keel ribs
    ]
    bm = build_mesh(tuple(range(len(mats))))
    # Spin about the long axis (positive turns the top face toward +X), then lift and centre.
    rot = Matrix.Rotation(math.radians(angle), 4, "Y")
    bmesh.ops.transform(bm, matrix=Matrix.Translation((G.x(AXIS_U), 0.0, SPIN_Z)) @ rot, verts=bm.verts)
    return common.mesh_object(name, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    sheet = sprite["sprites"][0]
    objs = []
    for k, (frame, angle) in enumerate(zip(sprite["frames"], ANGLES)):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        obj = build(sprite, angle, name, coll)
        subset = [{**sheet, "frames": [frame["index"]]}]
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", subset)
        objs.append((name, obj, frame))
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        for name, obj, frame in objs:
            ref = ROOT / "reference" / "models" / NAME / frame["image"]
            path = out if name == NAME else out.parent / f"{name}.png"
            common.render_preview([obj], str(path), ref, size=frame["size"])


if __name__ == "__main__":
    main()
