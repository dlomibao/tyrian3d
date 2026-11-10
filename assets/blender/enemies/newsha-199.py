"""newsha-199: a glowing energy ORB in flight (newsha.shp 199, 201, 239, 277).

What it is (object-identity audit, tyrian-scratch/object-audit/behaviour.txt): enemy type 841 is
launched by the sand-dome turret newshf-39 (type 840, launch=841) in SOH JIN and flies off at
4 px/tick (mv(4,0)), spawned in the top layer; type 779 is the same orb pushed about by the
level's move events. Nothing mounts it: it is a free-flying ball of light, not a lamp on a ring.
Its frames cycle 277-239-201-199-201-239: the same drawing with the palette shifted +5/+3/+2/0 in
the red ramp (112-127), so it pulses orange to red. The sprite's shading is a sphere's: a white-hot
core up-left (126-127, the glow's centre), concentric falloff to the body red (117), darker toward
the lower right (114-115), and a bright crescent hugging the lower-right rim (119-125, light
through the far side of the glowing ball).

Build: one round, closed spheroid (plan = the D74 inner mask's ellipse, 16 x 15 px; height 15 px,
so it reads as a ball from the tilted game camera and in 3/4; the underside is plain and round,
resting just above z = 0). Every colour band is a circle on the sphere, so each band edge is an
exact plane cut of the mesh (smooth, not stair-stepped): caps round the core direction for the
glow falloff, and a rim cap cut by a height plane for the crescent. Each band is an emissive
palette material at the sprite's index for that region, with the per-frame index of the pulse
(D17: +2 on 201, +3 on 239, +5 on 277, clamped at 127), so the bands pulse as the sprite does.
Nothing is painted, nothing baked (a smooth glowing ball has no AO to speak of); outline shell D90.

Run: Blender -b --factory-startup -P assets/blender/enemies/newsha-199.py -- [--preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newsha-199"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12
D2R = math.pi / 180

# Sprite px; x = col + 0.5 - 12, y = 14 - (row + 0.5), z up.
CX, CY = 0.0, 0.5
RX, RY = 8.0, 7.5          # plan ellipse = the inner mask (cols 4-19, rows 6-20)
RZ = 7.5                   # vertical semi-axis: a ball, height close to its width
Z0 = 0.25                  # underside clear of the ground plane
ZC = Z0 + RZ
U_SEG, V_SEG = 64, 40

# Pulse: sprite frame -> index shift from frame 199 (measured: every pixel of 201/239/277 is 199's
# index +2/+3/+5 in the 112-127 ramp, clamped at 127).
PULSE = {201: 2, 239: 3, 277: 5}


def unit(x, y, z):
    return Vector((x, y, z)).normalized()


def sprite_dir(col, row):
    """Unit-sphere direction of the top-view point at the centre of sprite pixel (col, row)."""
    u = (col + 0.5 - 12 - CX) / RX
    v = (14 - (row + 0.5) - CY) / RY
    return unit(u, v, math.sqrt(max(0.0, 1 - u * u - v * v)))


HOT = sprite_dir(9.4, 10.5)                                # the white-hot core (rows 10-11, cols 9-10)
RIM = unit(math.cos(-60 * D2R), math.sin(-60 * D2R), 0.15)  # the lower-right crescent's centre

# Bands, first match wins: (name, frame-199 index, test on the unit-sphere point p, emission).
# Glow falloff: caps round HOT (directions and angles least-squares fitted per pixel to the sprite's 199 ramp: 126 core, 124, 121, 119,
# body 117, then 116/115/114 toward the lower right and the rim). Crescent: caps round RIM below a
# height plane (the sprite draws it 1-2 px in from the lower-right ink only).
HOT_BANDS = [("core", 126, 7), ("hot", 124, 11), ("glow", 121, 18), ("halo", 119, 24),
             ("body", 117, 40), ("shade1", 116, 48), ("shade2", 115, 58), ("shade3", 114, 100)]
# Crescent bands: (name, index, cap angle round RIM, lowest z on the unit sphere, angle of the cap
# round RIM_UP cut out of its top). The cut-out cap's edge is an arc, so from the side each band is
# a thin glowing crescent hugging the rim (horns rising to either side), not a lamp on the flank.
RIM_UP = (Vector((RIM.x, RIM.y, 0)).normalized() * math.cos(70 * D2R) + Vector((0, 0, math.sin(70 * D2R)))).normalized()
RIM_BANDS = [("rim1", 125, 14, 0.02, 50), ("rim2", 122, 22, -0.03, 40), ("rim3", 119, 40, -0.08, 38)]
UNDER = ("under", 113)


def emission_of(index):
    """A glowing ball: everything emits, the hot parts most; the body glows only part way so the
    game's light still shapes the ball and the red reads at the sprite's depth (117 = 158, 8, 0)."""
    return 1.6 if index >= 121 else 0.9 if index >= 119 else 0.5


def bands():
    """[(name, index, test(p))] in priority order; the last one catches everything."""
    out = []
    for name, idx, ang in HOT_BANDS[:4]:
        out.append((name, idx, (lambda c: lambda p: p.dot(HOT) >= c)(math.cos(ang * D2R))))
    for name, idx, ang, zmin, cut in RIM_BANDS:
        out.append((name, idx, (lambda c, z0, cu: lambda p: p.dot(RIM) >= c and p.z >= z0 and p.dot(RIM_UP) < cu)(
            math.cos(ang * D2R), zmin, math.cos(cut * D2R))))
    for name, idx, ang in HOT_BANDS[4:]:
        out.append((name, idx, (lambda c: lambda p: p.dot(HOT) >= c)(math.cos(ang * D2R))))
    out.append((UNDER[0], UNDER[1], lambda p: True))
    return out


def cut_planes():
    """(normal, offset) of every band edge on the unit sphere: n . p = offset."""
    planes = []
    for _, _, ang in HOT_BANDS:
        planes.append((HOT, math.cos(ang * D2R)))
    for _, _, ang, zmin, cut in RIM_BANDS:
        planes.append((RIM, math.cos(ang * D2R)))
        planes.append((Vector((0, 0, 1)), zmin))
        planes.append((RIM_UP, math.cos(cut * D2R)))
    return planes


def materials(sprite):
    mats, slot = [], {}
    for name, idx, _ in bands():
        if idx in slot:
            continue
        frames = {f: min(127, idx + d) for f, d in PULSE.items()}
        slot[idx] = len(mats)
        mats.append(common.palette_material(sprite, idx, f"{NAME}-{name}", metallic=0.0, roughness=0.35,
                                            emission_strength=emission_of(idx), frames=frames))
    return mats, slot


def build(coll, sprite):
    mats, slot = materials(sprite)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=U_SEG, v_segments=V_SEG, radius=1.0)
    # Every band edge is a circle on the sphere: cut the mesh along each so the edges are smooth.
    for n, d in cut_planes():
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=n * d, plane_no=n)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    tests = bands()
    for f in bm.faces:
        c = f.calc_center_median().normalized()
        for _, idx, test in tests:
            if test(c):
                f.material_index = slot[idx]
                break
        f.smooth = True
    # unit sphere -> the orb's spheroid (an affine map: the plane cuts stay band edges)
    for v in bm.verts:
        p = v.co
        v.co = Vector((CX + RX * p.x, CY + RY * p.y, ZC + RZ * p.z)) * PX
    bm.normal_update()
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    for m in mats:
        me.materials.append(m)
    me.shade_smooth()
    return obj, mats


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj, mats = build(coll, sprite)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles, {len(mats)} materials")
    shell = common.outline_shell(obj, coll, voxel=0.03, inside=0.004)
    shell.name = shell.data.name = f"{NAME}_outline"
    common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"])
    if "--preview" in argv:
        out = argv[argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
