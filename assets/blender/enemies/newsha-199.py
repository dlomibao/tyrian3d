"""Glowing red orb (newsha.shp frames 199, 201, 239, 277): a 3D version of its sprite.

A ground object seen in episode 2 (level 2.10) and episode 4: a big red glass dome sitting on
the ground, a bright hot spot at its upper left and a glowing rim of reflected light round its
lower right. The four frames only brighten the whole orb (a pulse), so one model covers them: its
colours step up the red-orange ramp on frames 201, 239 and 277 (by 2, 3 and 5 palette indices;
palette_material frames=), the white-hot spot staying as it is.

Run: blender --background --python assets/blender/enemies/newsha-199.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b084 as lib  # noqa: E402

NAME = "newsha-199"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12

# The orb fills columns 3-20 and rows 5-21 (pixel edges 3..21 and 5..22).
CX, CY = (12 - 12) * PX, (14 - 13.5) * PX
RX, RY = 9.0 * PX, 8.5 * PX
ZC, RZ = 0.06, 0.5  # ellipsoid centre height and vertical radius; cut flat at z = 0


def X(c):
    return (c + 0.5 - 12) * PX


def Y(r):
    return (14 - (r + 0.5)) * PX


def surface(x, y):
    """The orb's top surface height and normal above (x, y)."""
    u, v = (x - CX) / RX, (y - CY) / RY
    s = max(0.0, 1 - u * u - v * v)
    z = ZC + RZ * math.sqrt(s)
    n = Vector((u / RX, v / RY, math.sqrt(s) / RZ if s > 0 else 0.0)).normalized()
    return z, n


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    pulse = lambda i, part, frames, **kw: common.palette_material(  # noqa: E731
        sprite, i, f"{NAME}-{part}", frames=frames, **kw)
    mats = [
        pulse(117, "body", {201: 119, 239: 120, 277: 122}, metallic=0.2, roughness=0.15, emission_strength=1.5),  # 0 red glass body
        pulse(114, "base", {201: 116, 239: 117, 277: 119}, metallic=0.5, roughness=0.4),  # 1 dark red base ring
        pulse(121, "glow", {201: 123, 239: 124, 277: 126}, emission_strength=3.0),  # 2 orange glow round the hot spot
        pal(127, emission_strength=6.0),  # 3 white-hot spot
        pulse(125, "rim", {201: 126, 277: 126}, emission_strength=4.0),  # 4 yellow rim light
    ]
    BODY, BASE, GLOW, HOT, RIM = range(5)
    bm = bmesh.new()

    # The orb: an ellipsoid cut flat at the ground.
    lib.ellipsoid(bm, (CX, CY, ZC), (RX, RY, RZ), segments=24, rings=12, mat=BODY)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0.0), plane_no=(0, 0, -1), clear_outer=True)
    edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    for f in bm.faces:
        f.material_index = BODY

    # A low dark ring round its foot.
    pts = []
    for k in range(25):
        a = 2 * math.pi * k / 24
        pts.append((CX + math.cos(a) * (RX - 0.2 * PX), CY + math.sin(a) * (RY - 0.2 * PX), 0.04, 0.9 * PX, 0.045))
    lib.tube(bm, pts, sides=6, mat=BASE, cap_start=False, cap_end=False)

    # The hot spot (columns 9-11, rows 10-12) and the orange glow round it, lying on the surface.
    for (c, r), rx, ry, rz, mat in (((10.0, 11.0), 3.2, 2.6, 0.035, GLOW), ((10.0, 10.8), 1.7, 1.5, 0.04, HOT)):
        x, y = X(c), Y(r)
        z, n = surface(x, y)
        lib.ellipsoid(bm, (x, y, z - 0.012), (rx * PX, ry * PX, rz), normal=n, segments=12, rings=6, mat=mat)

    # The rim of reflected light round the lower right (columns 13-18, rows 16-20).
    rim = []
    for a in range(-78, -14, 8):
        t = math.radians(a)
        x, y = CX + math.cos(t) * (RX - 1.4 * PX), CY + math.sin(t) * (RY - 1.4 * PX)
        z = surface(x, y)[0] - 0.02
        w = 0.9 * PX * math.sin(math.pi * (a + 78) / 64) + 0.2 * PX
        rim.append((x, y, z, w, 0.03))
    rim[0] = (*rim[0][:3], 0, 0)
    rim[-1] = (*rim[-1][:3], 0, 0)
    lib.tube(bm, rim, sides=6, mat=RIM)

    obj = lib.to_object(NAME, bm, mats, coll)
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])
    if "--frame-previews" in sys.argv:
        common.render_frame_previews([obj], sys.argv[sys.argv.index("--frame-previews") + 1], sprite, ROOT)


if __name__ == "__main__":
    main()
