"""Fire crescent (newshk.shp frames 115, 117, 119), design A: balance of sprite fidelity, game-camera
readability and engineering detail.

What it is: a projectile, a crescent wave of fire. Type 709 is launched by FLEET's invisible type-698
launcher and falls +5 px/tick straight down the screen, so the crescent's convex (bottom) edge is
its leading edge and the horns trail behind it, curling up. The three frames only brighten it
(every pixel +2 palette steps on 117, +4 on 119), and the brighter frames are also a little
bigger: their horns are a pixel longer and their rim is lit colour, not ink. So the model is two
frame-tagged bodies (D17): `-115` fitted to frame 115's inner mask and `-117` (frames 117 and 119),
the same flame swollen to the brighter frames' mask, each with its own frame-tagged outline shell.

Each body is one faired loft along the arc, tip to tip; each station is a chamfered section
spanning plan from the outer (leading) curve to the inner (trailing) curve, so the plan is exactly
the fitted outline (fit/plan.json, fitted by fit/fit.py to iou_rule_grid):
- a blunt rounded leading nose, a crest ridge a third of the way back (the sprite's bright line
  along the band), a long trailing slope thinning to a lip at the inner edge;
- a seam (a 0.25 px step) runs along the band where the crest ridge meets the trailing slope;
- the horns curl up off the ground plane toward their pointed tips;
- at the bottom centre the crest swells (30% taller) into the hot core, the sprite's 122/123 hot
  spot (columns 8-15), with the lobe that pokes up into the trailing edge at columns 10-13;
- the underside is a plain flat-ish closed shape.

Colours (the sprite's palette index per region, frame 115; the +2/+4 steps on 117/119 by
tyrian_frame_pal): flanks 119, crest ridge 121, hot core 122, trailing slope, lip and nose foot 117.
All glow (D126) on metallic 1 / rough surfaces (D173), strengths at or under ~1 (D176) so the reds
stay red.

Run: blender --background --python assets/blender/enemies/newshk-115.py [-- --preview out.png]
Exports public/models/enemies/newshk-115.glb and src/render/spriteModels/newshk-115.json.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newshk-115"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
# Fitted plan (tip, outer and inner edge control points in sprite pixel edges, left half) per body,
# fitted to the sprite's inner masks for iou_rule_grid.
PLAN = json.loads('''{"115": {"tip": [1.4, 13.456], "outer": [[1.094, 14.744], [1.072, 16.195], [1.788, 17.663], [2.711, 19.46], [3.825, 21.308], [5.82, 22.375], [8.472, 23.646], [12.0, 24.625]], "inner": [[2.534, 15.236], [3.359, 16.829], [4.678, 18.215], [6.625, 19.372], [8.47, 20.088], [10.25, 19.5], [12.0, 18.902]]}, "117": {"tip": [1.355, 12.789], "outer": [[0.373, 14.133], [0.154, 15.509], [1.004, 17.075], [2.034, 19.138], [3.571, 21.042], [5.438, 22.692], [8.297, 24.077], [12.0, 25.345]], "inner": [[2.33, 14.625], [3.635, 16.186], [5.051, 17.584], [6.353, 18.929], [7.584, 19.634], [9.5, 19.123], [12.0, 19.026]]}}''')
PX = 1 / 12
W, H = 24, 28
VARIANTS = {"115": [115], "117": [117, 119]}


def P(x, y, z):
    """Sprite pixel-edge column x, row y, height z px -> world."""
    return Vector(((x - W / 2) * PX, (H / 2 - y) * PX, z * PX))


def catmull(pts, steps=10):
    """Catmull-Rom through 2D points, end points kept (as fit.py)."""
    out = []
    n = len(pts)
    for i in range(n - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, n - 1)]
        for s in range(steps):
            t = s / steps
            out.append(tuple(0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t
                                    + (-a + 3 * b - 3 * c + d) * t ** 3) for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(tuple(pts[-1]))
    return out


def resample(poly, n):
    """n points evenly spaced by arc length along a polyline."""
    cum = [0.0]
    for a, b in zip(poly, poly[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    out = []
    j = 0
    for k in range(n):
        t = cum[-1] * k / (n - 1)
        while j < len(cum) - 2 and cum[j + 1] < t:
            j += 1
        f = (t - cum[j]) / max(1e-9, cum[j + 1] - cum[j])
        out.append((poly[j][0] + (poly[j + 1][0] - poly[j][0]) * f, poly[j][1] + (poly[j + 1][1] - poly[j][1]) * f))
    return out


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# The section, outer (leading) edge u=0 to inner (trailing) edge u=1: (u, z as a share of the
# station's height, material key). Top first, then the flat underside back to the nose.
PROFILE = [
    (0.000, 0.18, "trail"),   # 0 nose foot (faces down and forward: the sprite's dark leading rim)
    (0.025, 0.46, "trail"),   # 1 nose (the dark leading rim)
    (0.110, 0.72, "flank"),   # 2 nose chamfer
    (0.330, 0.93, "crest"),   # 3 crest front chamfer
    (0.400, 0.98, "crest"),   # 4 crest front
    (0.500, 1.00, "crest"),   # 5 crest
    (0.590, 0.95, "crest"),   # 6 crest back chamfer
    (0.630, 0.84, "trail"),   # 7 seam step (the panel line down to the trailing slope)
    (0.780, 0.64, "trail"),   # 8 trailing slope (flame licks)
    (0.900, 0.44, "trail"),   # 9
    (0.975, 0.28, "trail"),   # 10 lip chamfer
    (1.000, 0.13, "trail"),   # 11 lip
    (0.960, 0.00, "under"),   # 12 underside
    (0.500, -0.04, "under"),  # 13
    (0.040, 0.00, "under"),   # 14
]
LICKS = {8: 0.26, 9: 0.36, 10: 0.34, 11: 0.3}  # profile vertex: share of its height the flame licks swing


def build_body(sprite, variant, coll, mats):
    plan = PLAN[variant]
    tip = tuple(plan["tip"])
    outer = resample(catmull([tip] + [tuple(p) for p in plan["outer"]]), 41)
    inner = resample(catmull([tip] + [tuple(p) for p in plan["inner"]]), 41)
    # Left half tip -> centre, then the right half mirrored, centre -> tip.
    st = [(o, i, k / 40) for k, (o, i) in enumerate(zip(outer, inner))]
    st += [((W - o[0], o[1]), (W - i[0], i[1]), s) for o, i, s in reversed(st[:-1])]
    hot = 1.08 if variant == "117" else 1.0  # the brighter flame stands a touch taller
    bm = bmesh.new()
    rings = []
    centre = []  # per station: 1 across the hot bottom centre, 0 up the horns
    for o, i, s in st:
        dx = abs((o[0] + i[0]) / 2 - W / 2)
        centre.append(1 - smoothstep(4.5, 7.0, dx))
        core = math.exp(-(dx / 3.4) ** 2)  # the hot core swells the crest at the bottom centre
        w = math.dist(o, i)
        h = min(4.0, max(0.5, (0.6 + 0.22 * smoothstep(0.35, 0.8, s)) * w)) * hot * (1 + 0.3 * core)
        # Horns curl up off the ground plane toward the tips.
        zb = 1.5 * (1 - smoothstep(0.0, 0.6, s)) ** 1.8
        lick = math.cos(2 * math.pi * s * 4.5)
        if s < 0.02:
            c = ((o[0] + i[0]) / 2, (o[1] + i[1]) / 2)
            rings.append([bm.verts.new(P(c[0], c[1], zb + 0.45))])
            continue
        ring = []
        for k, (u, zf, _) in enumerate(PROFILE):
            zf = zf * (1 + LICKS.get(k, 0.0) * lick)
            x = o[0] + (i[0] - o[0]) * u
            y = o[1] + (i[1] - o[1]) * u
            ring.append(bm.verts.new(P(x, y, zb + zf * h)))
        rings.append(ring)
    keys = [k for _, _, k in PROFILE]
    n = len(PROFILE)
    for r, (a, b) in enumerate(zip(rings, rings[1:])):
        c = (centre[r] + centre[r + 1]) / 2
        xm = (a[5].co.x + b[5].co.x) / 2 / PX if len(a) > 1 and len(b) > 1 else 99
        for k in range(n):
            mk = keys[k]
            # Across the bottom centre the bright band is wider (the sprite's rows 20-22) and the
            # trailing slope stays flank-red up to the lip's chamfer.
            um = (PROFILE[k][0] + PROFILE[(k + 1) % n][0]) / 2
            if k <= 10 and (xm / 4.0) ** 2 + ((um - 0.48) / 0.17) ** 2 < 1:
                mk = "core"  # the sprite's 122/123 hot spot, columns 8-15: a lens on the crest
            elif abs(xm) < 4.6 and k in (2, 7):
                mk = "crest"
            elif c > 0.5 and k in (7, 8):
                mk = "flank"
            mi = mats[mk]
            if len(a) == 1 or len(b) == 1:
                one, many = (a, b) if len(a) == 1 else (b, a)
                f = bm.faces.new((one[0], many[k], many[(k + 1) % n]))
            else:
                f = bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
            f.material_index = mi
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = common.mesh_object(f"{NAME}-{variant}", bm, list(mats["list"]), coll, smooth=True)
    es = obj.modifiers.new("hard", "EDGE_SPLIT")  # the crest's chamfers and the seam stay crisp
    es.split_angle = math.radians(38)
    return obj


def build(sprite):
    coll = common.reset_collection(NAME)

    def glow(i, frames, tag, strength):
        return common.palette_material(sprite, i, f"{NAME}-{tag}", metallic=1.0, roughness=0.85,
                                       emission_strength=strength, frames=frames)
    lst = [
        glow(119, {117: 121, 119: 123}, "flank", 0.5),
        glow(121, {117: 123, 119: 125}, "crest", 1.05),
        glow(117, {117: 119, 119: 121}, "trail", 0.45),
        glow(122, {117: 124, 119: 126}, "core", 1.1),
    ]
    mats = {"flank": 0, "crest": 1, "trail": 2, "under": 2, "core": 3, "list": lst}
    bodies = {v: build_body(sprite, v, coll, mats) for v in VARIANTS}
    return coll, bodies


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(ROOT, NAME)
    coll, bodies = build(sprite)
    objs = []
    for v, body in bodies.items():
        # D90/D118: the shell from a sealed copy of the body (nothing culled); one loft = one island.
        sealed = body.copy()
        sealed.data = body.data.copy()
        for m in list(sealed.modifiers):
            sealed.modifiers.remove(m)
        coll.objects.link(sealed)
        bpy.context.view_layer.update()
        shell = common.outline_shell(sealed, coll, voxel=0.010, faces=2500, inside=0.008)
        shell.name = f"{NAME}-{v}_outline"
        bpy.data.objects.remove(sealed, do_unlink=True)
        assert len(shell.data.polygons) > 0, f"empty outline shell {v}"
        common.frame_part(body, VARIANTS[v])
        common.frame_part(shell, VARIANTS[v])
        objs += [body, shell]
    common.export_sprite_model(ROOT, objs, MODEL, sprite["sprites"])
    dg = bpy.context.evaluated_depsgraph_get()
    for o in bodies.values():
        me = o.evaluated_get(dg).to_mesh()
        print(f"{o.name}: triangles {sum(len(p.vertices) - 2 for p in me.polygons)}")
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview(objs, out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
