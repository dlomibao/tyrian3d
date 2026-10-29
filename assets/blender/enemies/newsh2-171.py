"""Spinning brown pod (newsh2.shp frames 171, 190, 209, 228, 247, 266): a 3D version of its sprite.

Seen in episodes 1, 2 and 3 (levels 1.25, 1.3, 2.6, 3.17). A brown armoured heart-shaped pod,
broad and round-shouldered across its top rows and drawn out to a point at the bottom, flattened
so that it is 11 px wide face on (frame 171) and 5 px edge on (frame 228). The six frames spin it
about its long axis (the sprite's vertical), so each frame gets its own model (newsh2-171, -f2 ...
-f6), the same pod turned to match.

Traced from the concept (assets/blender/textures/newsh2-171/concept.png, lined up with the sprite;
features in assets/blender/features/newsh2-171.json), the same on both faces: a dark core hull with
a crisp keel along each side; a raised armoured spine down the middle (rows 0.6-8.9) ending in a
point, crossed by a dark strap at row 2 and carrying a framed glowing lens at rows 5-7; a big
curved shoulder pad at each top corner (a crescent of riveted plates round a dark recess); a dark
strap out to each side at row 5; a block either side of the spine below it (rows 6-8.6); and a
V-shaped plate wrapping the tail point (rows 9-13.4) with a small block in its notch. It spins in
the air just above the ground.

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
P = lib.PX

# Core hull down the pod: (row edge, half width px, half thickness px). Inside the sprite's
# outline ring: the pads cover its top corners, the tail plate its point.
HULL = [(0.25, 2.4, 0.8), (0.8, 3.9, 1.1), (1.6, 4.8, 1.3), (2.3, 5.3, 1.4), (4.7, 5.3, 1.4),
        (5.0, 4.45, 1.4), (6.9, 4.4, 1.35), (7.1, 3.45, 1.3), (8.8, 3.4, 1.2), (9.0, 2.5, 1.1),
        (11.0, 1.5, 0.9), (12.6, 0.75, 0.6), (13.6, 0.0, 0.0)]
# Hull section (unit half width, unit half thickness): a crisp keel at each edge, flat faces.
SHELL = [(1.0, 0.0), (0.82, 0.55), (0.4, 1.0), (-0.4, 1.0), (-0.82, 0.55), (-1.0, 0.0),
         (-0.82, -0.55), (-0.4, -1.0), (0.4, -1.0), (0.82, -0.55)]
# Spine: (row edge, half width px, top px); flat-topped with chamfered shoulders.
SPINE = [(0.55, 1.0, 2.15), (0.8, 1.35, 2.4), (8.0, 1.35, 2.4), (8.95, 0.3, 2.0)]
SPINE_SEC = [(1.0, 0.0), (1.0, 0.82), (0.72, 1.0), (-0.72, 1.0), (-1.0, 0.82), (-1.0, 0.0)]
# Shoulder pad (left; the right is its mirror): a crescent about (u, v) = PAD_C, outer and inner
# elliptical radii (u, v), swept from the top (next to the spine) round to the side.
PAD_C = (5.15, 4.9)
PAD_OUT = (4.1, 4.25)
PAD_IN = (2.7, 1.45)
# Across the crescent (t outer 0 -> inner 1, top px): low outer rim, domed crown, stepped inner lip.
PAD_SEC = [(0.0, 0.05), (0.0, 1.35), (0.12, 1.95), (0.42, 2.3), (0.78, 2.2), (1.0, 1.7), (1.0, 0.05)]
# The edge rib's section, in px from the keel vertex (x outward, z up): a thin bevelled strip.
RIB = [(0.25, 0.0), (0.0, 0.45), (-0.7, 0.4), (-0.7, -0.4), (0.0, -0.45)]


def hull_at(v):
    for (v0, a0, b0), (v1, a1, b1) in zip(HULL, HULL[1:]):
        if v0 <= v <= v1:
            t = (v - v0) / (v1 - v0)
            return a0 + (a1 - a0) * t, b0 + (b1 - b0) * t
    return 0.0, 0.0


def lx(u):
    """Sprite pixel-edge column to local x (units) about the long axis."""
    return (u - AXIS_U) * P


def loft(bm, rings, mats, cap_start=True, cap_end=True):
    """Join rings of 3D points (same count, or a single point) into a tube; mats[k] is the material
    between rings k and k+1. All faces flat; caps on the open ends."""
    vr = [[bm.verts.new(p) for p in r] for r in rings]
    n = max(len(r) for r in vr)
    for k, (r0, r1) in enumerate(zip(vr, vr[1:])):
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                f = (r0[i], r0[j], r1[0])
            else:
                f = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(f).material_index = mats[k]
    if cap_start and len(vr[0]) > 2:
        bm.faces.new(list(reversed(vr[0]))).material_index = mats[0]
    if cap_end and len(vr[-1]) > 2:
        bm.faces.new(vr[-1]).material_index = mats[-1]


def prism(bm, outline, z0, z1, ch, mat, sgn):
    """A plate over an outline of (u, v) pixel edges from z0 to z1 px (mirrored by sgn), its top
    edge chamfered by ch px (mitred inset, so concave outlines work)."""
    pts = [(lx(u) / P, -v) for u, v in outline]  # px, y up
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts = pts[::-1]
    n = len(pts)
    inset = []
    for i in range(n):
        (ax, ay), (bx, by), (cx, cy) = pts[i - 1], pts[i], pts[(i + 1) % n]
        n1 = (-(by - ay), bx - ax)
        n2 = (-(cy - by), cx - bx)
        l1, l2 = math.hypot(*n1), math.hypot(*n2)
        n1 = (n1[0] / l1, n1[1] / l1)
        n2 = (n2[0] / l2, n2[1] / l2)
        d = 1 + n1[0] * n2[0] + n1[1] * n2[1]
        inset.append((bx + ch * (n1[0] + n2[0]) / d, by + ch * (n1[1] + n2[1]) / d))

    def ring2(ps, z):
        return [(x * P, G.y(-y), z * P * sgn) for x, y in ps]

    loft(bm, [ring2(pts, z0), ring2(pts, z1 - ch), ring2(inset, z1)], [mat, mat])


def build_mesh(m):
    bm = bmesh.new()
    y = G.y

    # Core hull.
    rings = []
    for v, a, b in HULL:
        if a == 0:
            rings.append([(0.0, y(v), 0.0)])
        else:
            rings.append([(a * P * s, y(v), b * P * t) for s, t in SHELL])
    loft(bm, rings, [m["hull"]] * (len(rings) - 1))

    for sgn in (1, -1):
        # Spine, with a dark strap across it at row 2 and a framed lens at rows 5-7.
        rings = [[(hw * P * s, y(v), sgn * top * P * t) for s, t in SPINE_SEC] for v, hw, top in SPINE]
        loft(bm, rings, [m["spine"]] * (len(rings) - 1))
        prism(bm, [(4.95, 1.85), (8.05, 1.85), (8.05, 2.75), (4.95, 2.75)], 0.0, 2.6, 0.15, m["strap"], sgn)
        oct_ = lambda hw, v0, v1, c: [(AXIS_U - hw, v0 + c), (AXIS_U - hw + c, v0), (AXIS_U + hw - c, v0),  # noqa: E731
                                     (AXIS_U + hw, v0 + c), (AXIS_U + hw, v1 - c), (AXIS_U + hw - c, v1),
                                     (AXIS_U - hw + c, v1), (AXIS_U - hw, v1 - c)]
        prism(bm, oct_(0.62, 4.8, 7.05, 0.35), 1.5, 2.55, 0.08, m["frame"], sgn)
        prism(bm, oct_(0.38, 5.05, 6.8, 0.25), 1.5, 2.72, 0.1, m["lens"], sgn)

        for side in (1, -1):
            U = lambda u: AXIS_U + side * (u - AXIS_U)  # noqa: E731  mirror left -> right
            # Shoulder pad: a crescent of armour plates round a dark recess.
            rings = []
            for k in range(8):
                a = math.radians(90 * k / 7)
                o = (PAD_C[0] - PAD_OUT[0] * math.sin(a), PAD_C[1] - PAD_OUT[1] * math.cos(a))
                i = (PAD_C[0] - PAD_IN[0] * math.sin(a), PAD_C[1] - PAD_IN[1] * math.cos(a))
                ring = []
                for t, z in PAD_SEC:
                    u, v = o[0] + t * (i[0] - o[0]), o[1] + t * (i[1] - o[1])
                    ring.append((lx(U(u)), y(v), sgn * z * P))
                rings.append(ring)
            loft(bm, rings, [m["pad"]] * 7)
            # Strap out to the side at row 5, a block below it beside the spine.
            prism(bm, [(U(2.2), 4.95), (U(5.2), 4.95), (U(5.2), 6.05), (U(2.2), 6.05)], 0.0, 2.0, 0.15,
                  m["strap2"], sgn)
            prism(bm, [(U(2.45), 6.05), (U(5.2), 6.05), (U(5.2), 8.6), (U(3.15), 8.6), (U(3.05), 7.1),
                       (U(2.45), 6.95)], 0.0, 1.85, 0.2, m["box"], sgn)

        # V plate round the tail point, a small block in its notch.
        prism(bm, [(4.05, 8.9), (5.3, 8.9), (6.5, 11.1), (7.7, 8.9), (8.95, 8.9), (6.5, 13.45)],
              0.0, 1.65, 0.18, m["tail"], sgn)
        prism(bm, [(6.0, 8.9), (7.0, 8.9), (7.0, 10.0), (6.5, 10.6), (6.0, 10.0)], 0.0, 1.4, 0.12,
              m["box"], sgn)

    # A thin light rib along the keel at each edge, below the pads.
    for side in (1, -1):
        rib_v = [5.2 + (12.4 - 5.2) * i / 8 for i in range(9)]
        rings = []
        for k, v in enumerate(rib_v):
            a, _ = hull_at(v)
            sc = 0.5 if k in (0, len(rib_v) - 1) else 1.0
            rings.append([(side * (a + sc * du) * P, y(v), sc * dz * P) for du, dz in RIB])
        loft(bm, rings, [m["rib"]] * (len(rings) - 1))
    return bm


def build(sprite, angle, name, coll):
    tag = "nsh2_171"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    spec = [
        ("hull", pal(19, metallic=0.15, roughness=0.65)),  # dark core between the plates
        ("pad", pal(22, metallic=0.4, roughness=0.42)),  # shoulder pads
        ("spine", pal(24, metallic=0.45, roughness=0.38)),  # light central spine
        ("strap", pal(18, metallic=0.35, roughness=0.5)),  # dark strap across the spine
        ("frame", pal(17, metallic=0.4, roughness=0.4)),  # lens frame
        ("lens", pal(30, metallic=0.0, roughness=0.06, emission_strength=0.6)),  # glowing lens
        ("strap2", pal(20, metallic=0.25, roughness=0.55)),  # side straps
        ("box", pal(21, metallic=0.4, roughness=0.45)),  # blocks beside the spine
        ("tail", pal(20, metallic=0.4, roughness=0.45)),  # V plate on the darker point
        ("rib", pal(25, metallic=0.45, roughness=0.35)),  # keel ribs
    ]
    mats, idx = [], {}
    for key, mat in spec:
        if mat not in mats:
            mats.append(mat)
        idx[key] = mats.index(mat)
    bm = build_mesh(idx)
    # Spin about the long axis (positive turns the top face toward +X), then lift and centre.
    rot = Matrix.Rotation(math.radians(angle), 4, "Y")
    bmesh.ops.transform(bm, matrix=Matrix.Translation((G.x(AXIS_U), 0.0, SPIN_Z)) @ rot, verts=bm.verts)
    return common.mesh_object(name, bm, mats, coll, smooth=False)


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
