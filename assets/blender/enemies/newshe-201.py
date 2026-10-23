"""Spiked mine (newshe.shp frames 201, 239, 241): a 3D version of its sprite.

Seen on the ground in level 1.13. A round tan ball, lit from the top left with a dark shadowed
underside and a dark slot on its right, studded with short knobs on top and long spikes round
its rim. The three frames turn the ball, so the rim spikes change length and direction: each frame
gets its own model (newshe-201, -f2, -f3) sharing the ball and its knobs.

Run: blender --background --python assets/blender/enemies/newshe-201.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newshe-201"
ROOT = common.repo_root(__file__)

# Ball centre in sprite pixel-edge coordinates, its radii (px) and its height (units).
CU, CV = 11.5, 13.5
RX, RY = 8.0, 7.6
ZC, RZ = 0.28, 0.36

# Rim spikes per frame: the tip as a pixel (column, row) of the sprite, and how far (px) the tip
# rises above the ball's equator (short spikes lean up a little, as if turning toward the viewer).
FRAMES = {
    201: [((11, 1), 1.0), ((2, 4), 2.0), ((0, 13), 0.5), ((21, 13), 0.5), ((11, 23), 1.5),
          ((21, 23), 0.0)],
    239: [((11, 2), 1.5), ((3, 5), 2.5), ((19, 5), 2.5), ((0, 13), 0.5), ((22, 13), 0.0),
          ((11, 25), 0.0), ((3, 21), 2.5), ((20, 22), 1.5)],
    241: [((11, 3), 2.0), ((4, 6), 3.0), ((20, 4), 0.5), ((1, 13), 1.0), ((23, 13), 0.0),
          ((11, 26), 0.0), ((2, 22), 0.5), ((19, 21), 2.5)],
}

# Knobs on top (the bright pixels inside the ball): pixel centre (column, row).
KNOBS = [(14, 7), (6.5, 8.5), (6, 13), (11, 12.5), (15.5, 16.5), (7, 17)]


def to_xy(u, v):
    """Sprite pixel-edge coordinates to Blender X, Y."""
    return (u - 12) / 12, (14 - v) / 12


def surface_z(x, y):
    """Height of the ball's top surface above (x, y)."""
    cx, cy = to_xy(CU, CV)
    t = 1 - ((x - cx) / (RX / 12)) ** 2 - ((y - cy) / (RY / 12)) ** 2
    return ZC + RZ * math.sqrt(max(t, 0.0))


def cone(bm, p0, p1, r0, sides, mat_index):
    """A cone from base centre p0 (radius r0) to tip p1."""
    p0, p1 = Vector(p0), Vector(p1)
    axis = (p1 - p0).normalized()
    ref = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    a = axis.cross(ref).normalized()
    b = axis.cross(a)
    ring = [bm.verts.new(p0 + r0 * (math.cos(2 * math.pi * i / sides) * a + math.sin(2 * math.pi * i / sides) * b))
            for i in range(sides)]
    tip = bm.verts.new(p1)
    for i in range(sides):
        bm.faces.new((ring[i], ring[(i + 1) % sides], tip)).material_index = mat_index
    bm.faces.new(list(reversed(ring))).material_index = mat_index


def squircle(t, n=2.6):
    """Superellipse profile: the sprite's ball is a little squarer than a circle seen from above."""
    return math.copysign(abs(t) ** (2 / n), t)


def ball(bm, body, shadow, segs=20, rings=7):
    """The ball: an ellipsoid cut flat at z = 0. Faces on the lower (south) side get the shadow colour."""
    cx, cy = to_xy(CU, CV)
    rx, ry = RX / 12, RY / 12
    phi0 = math.asin(-ZC / RZ)  # elevation where the ellipsoid meets the ground
    phis = [phi0 + (math.pi / 2 - phi0) * k / rings for k in range(rings)]
    loops = []
    for phi in phis:
        c, s = math.cos(phi), math.sin(phi)
        loops.append([bm.verts.new((cx + rx * c * squircle(math.cos(2 * math.pi * i / segs)),
                                    cy + ry * c * squircle(math.sin(2 * math.pi * i / segs)), ZC + RZ * s))
                      for i in range(segs)])
    top = bm.verts.new((cx, cy, ZC + RZ))
    south = to_xy(0, 16.5)[1]

    def mat_for(verts):
        y = sum(v.co.y for v in verts) / len(verts)
        z = sum(v.co.z for v in verts) / len(verts)
        return shadow if y < south and z < ZC + RZ * 0.8 else body

    for l0, l1 in zip(loops, loops[1:]):
        for i in range(segs):
            j = (i + 1) % segs
            f = (l0[i], l0[j], l1[j], l1[i])
            bm.faces.new(f).material_index = mat_for(f)
    for i in range(segs):
        f = (loops[-1][i], loops[-1][(i + 1) % segs], top)
        bm.faces.new(f).material_index = mat_for(f)
    bm.faces.new(list(reversed(loops[0]))).material_index = shadow


def build(sprite, name, spikes):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    mats = [
        pal(233, metallic=0.35, roughness=0.5),  # 0 ball
        pal(228, metallic=0.3, roughness=0.6),  # 1 shadowed underside
        pal(235, metallic=0.5, roughness=0.35),  # 2 spikes
        pal(237, metallic=0.5, roughness=0.3),  # 3 knobs
        pal(226, metallic=0.2, roughness=0.7),  # 4 dark slot
    ]
    BODY, SHADOW, SPIKE, KNOB, SLOT = range(5)
    bm = bmesh.new()
    ball(bm, BODY, SHADOW)

    # Rim spikes: from inside the ball out to the tip pixel's outer edge.
    cx, cy = to_xy(CU, CV)
    R = (RX + RY) / 2 / 12
    for (c, r), rise in spikes:
        d = Vector((c + 0.5 - CU, r + 0.5 - CV))
        tip_uv = Vector((c + 0.5, r + 0.5)) + d.normalized() * 0.5
        tx, ty = to_xy(tip_uv.x, tip_uv.y)
        tip = Vector((tx, ty, ZC + rise / 12))
        dirv = Vector((tx - cx, ty - cy, 0)).normalized()
        base = Vector((cx, cy, ZC)) + dirv * R * 0.6
        length = (tip - base).length
        # About 3 px wide where the spike leaves the ball.
        r0 = min(1.5 / 12 * length / max(length - R * 0.4, 0.05), 3.0 / 12)
        cone(bm, base, tip, r0, 6, SPIKE)

    # Knobs on top, standing out along the surface normal.
    for c, r in KNOBS:
        x, y = to_xy(c + 0.5, r + 0.5)
        z = surface_z(x, y)
        n = Vector(((x - cx) / (RX / 12) ** 2, (y - cy) / (RY / 12) ** 2, (z - ZC) / RZ ** 2)).normalized()
        p = Vector((x, y, z))
        cone(bm, p - n * 0.04, p + n * 0.13, 1.2 / 12, 6, KNOB)

    # The dark slot on the right (columns 16-17, rows 11-15): a shallow dark lens on the surface.
    sx, sy = to_xy(17.0, 13.5)
    start = len(bm.verts)
    common.loft(bm, [(sy + 2.4 / 12, 0.0, 0.0, 0.0), (sy + 1.3 / 12, 0.7 / 12, 0.4 / 12, 0.0),
                     (sy - 1.3 / 12, 0.7 / 12, 0.4 / 12, 0.0), (sy - 2.4 / 12, 0.0, 0.0, 0.0)],
                sides=6, mat_index=SLOT)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.x += sx
        v.co.z += surface_z(sx, v.co.y) - 0.01

    return common.mesh_object(name, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    base = sprite["sprites"][0]
    for i, (index, spikes) in enumerate(FRAMES.items()):
        name = NAME if i == 0 else f"{NAME}-f{i + 1}"
        obj = build(sprite, name, spikes)
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", [{**base, "frames": [index]}])
        if "--preview" in sys.argv:
            out = Path(sys.argv[sys.argv.index("--preview") + 1])
            ref = ROOT / "reference" / "models" / NAME / f"frame-newshe-{index}.png"
            common.render_preview([obj], out.with_name(f"{name}.png"), ref, size=2)


if __name__ == "__main__":
    main()
