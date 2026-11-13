"""Small grey eyeball (newsh5.shp frames 202, 221): a machined sensor eye.

Seen in episode 4 (EYESPY, NOSE DRIP): a ring of small eyes escorting the big blue eye, and the
homing eye it spits. The sprite is a grey ball with a dark socket low on its face, looking down the
screen; frame 221 squeezes the ball narrow and tall (the eye wobbles), so each frame is its own
model: newsh5-202 and newsh5-202-f2.

What it is, in 3D: a satin grey steel ball (the sprite's mid grey, 10) with a deep socket bored
into it along its gaze axis, tilted ~20 degrees down the screen. The socket is one revolved
profile round that axis, so every ring is a clean machined section: a chamfered lip, a steep wall
(4, the socket's median shade), a raised machined iris ring (4), a dark iris floor (3) and a convex
glossy black lens (1) whose glint is the material's sheen, not paint (art rule 2). A fine
V-groove bezel line circles the socket, and a seam groove circles the back of the ball where the
eye shell meets its rear housing. The socket is elliptical in angle per frame so its top view
lands on the sprite's dark pixels. The ball's shading, its upper-left highlight and the dark
outline ring are the game's lights and ink, so the ball is one grey.

The outline shell (D51) comes from a plain ball with the socket filled (sealed, one island), so the
ink lands on the silhouette only, never round the socket.

Run: blender --background --python assets/blender/enemies/newsh5-202.py
  exports both frames (model + outline shell each) to public/models/enemies/.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]
import common  # noqa: E402

NAME = "newsh5-202"
ROOT = common.repo_root(__file__)
U = 1 / 12  # one sprite pixel in Blender units

# Per frame (sprite pixels, pixel-centre coordinates of the 12x14 tile): ball centre (col, row),
# semi-axes a (x), b (y), c (z); the gaze tilt down the screen (degrees from straight up) and the
# socket's angular half-size across (x) and along (y) the tilt, fitted to the sprite's dark pixels.
FRAMES = {
    202: dict(centre=(6.0, 6.0), axes=(4.85, 4.85, 4.85), tilt=24.0, socket=(33.0, 30.0)),
    221: dict(centre=(6.0, 6.0), axes=(3.9, 5.6, 4.6), tilt=21.0, socket=(26.0, 34.0)),
}
SEG = 48  # vertices round each ring

BODY, RIM, IRIS, LENS = 10, 4, 3, 1  # palette indices: ball, socket wall + iris ring (the socket median), iris floor, lens
MATS = {  # satin steel ball (F0 raised, D176), satin dark socket, glossy black lens catching the glint
    BODY: dict(metallic=0.35, roughness=0.36, spec=0.9),
    RIM: dict(metallic=0.3, roughness=0.42, spec=0.6),
    IRIS: dict(metallic=0.2, roughness=0.5, spec=0.5),
    LENS: dict(metallic=0.0, roughness=0.08, spec=1.0),
}

# The revolved profile, from the lens apex out to the back pole. Each point: (where, depth, mat,
# sharp). `where` is ("s", f): f times the socket's angular radius at that azimuth; ("o", d): the
# socket radius plus d degrees; ("a", deg): an absolute polar angle from the gaze axis. depth is in
# sprite pixels below the ball's surface (along the radius). `mat` paints the band from the
# previous point to this one; `sharp` makes the ring a hard edge.
PROFILE = [
    (("s", 0.00), 0.95, LENS, False),   # lens apex
    (("s", 0.12), 1.00, LENS, False),
    (("s", 0.26), 1.08, LENS, False),
    (("s", 0.38), 1.22, LENS, False),
    (("s", 0.46), 1.36, LENS, True),    # lens edge
    (("s", 0.46), 1.52, IRIS, True),    # step down to the iris floor
    (("s", 0.58), 1.52, IRIS, False),
    (("s", 0.70), 1.52, IRIS, True),
    (("s", 0.72), 1.36, RIM, True),     # machined iris ring
    (("s", 0.78), 1.36, RIM, True),
    (("s", 0.80), 1.52, RIM, True),
    (("s", 0.87), 1.52, RIM, True),     # wall foot
    (("s", 0.95), 0.30, RIM, True),     # wall top, chamfer below
    (("o", 2.5), 0.00, BODY, True),     # lip chamfer to the ball
    (("o", 6.0), 0.00, BODY, False),
    (("o", 8.5), 0.00, BODY, False),    # bezel panel line
    (("o", 9.5), 0.16, BODY, False),
    (("o", 10.5), 0.00, BODY, False),
    (("o", 14.0), 0.00, BODY, False),
]
_ABS = [62, 70, 78, 86, 94, 102, 110, 116, 117.5, 119, 126, 134, 142, 150, 158, 166, 174]
for _a in _ABS:
    PROFILE.append((("a", _a), 0.16 if _a == 117.5 else 0.0, BODY, False))
PROFILE.append((("a", 180), 0.0, BODY, False))  # back pole
PLAIN = [(("a", a), 0.0, BODY, False) for a in [0, 8, 16, 24, 32, 40, 48, 56] + _ABS + [180]]


def px(c):
    return (c + 0.5 - 6) * U


def row(r):
    return (7 - (r + 0.5)) * U


def ring_theta(where, sx, sy, phi):
    """Polar angle (radians) from the gaze axis of a profile point at azimuth phi."""
    kind, v = where
    if kind == "a":
        return math.radians(v)
    ts = 1 / math.sqrt((math.cos(phi) / sx) ** 2 + (math.sin(phi) / sy) ** 2)  # elliptical socket
    return ts * v if kind == "s" else ts + math.radians(v)


def eyeball(bm, frame, profile, mat_slot):
    a, b, c = frame["axes"]
    R = (a + b + c) / 3  # depths in px are measured against the mean radius
    t = math.radians(frame["tilt"])
    sx, sy = (math.radians(v) for v in frame["socket"])
    # Local frame: z' the gaze (tilted down the screen, toward -Y), x' = world x, y' completes it.
    gaze = Vector((0.0, -math.sin(t), math.cos(t)))
    ex = Vector((1.0, 0.0, 0.0))
    ey = gaze.cross(ex)  # local "up the tilt" direction
    scale = Matrix.Diagonal((a * U, b * U, c * U))
    cx, cy = px(frame["centre"][0]), row(frame["centre"][1])

    rings = []
    for where, depth, mat, sharp in profile:
        pole = (where[0] in "sa" and where[1] in (0, 0.0, 180))
        verts = []
        for j in range(1 if pole else SEG):
            phi = 2 * math.pi * j / SEG
            th = ring_theta(where, sx, sy, phi)
            # azimuth phi: 0 = across (x'), pi/2 = up the tilt (+y'; sy applies along the tilt)
            d = gaze * math.cos(th) + (ex * math.cos(phi) + ey * math.sin(phi)) * math.sin(th)
            p = scale @ (d * (1 - depth / R))
            verts.append(bm.verts.new((p.x + cx, p.y + cy, p.z)))
        rings.append((verts, mat, sharp))

    faces = []
    for i in range(1, len(rings)):
        prev, cur = rings[i - 1][0], rings[i][0]
        mat = mat_slot[rings[i][1]]
        for j in range(SEG):
            k = (j + 1) % SEG
            if len(prev) == 1:
                f = bm.faces.new((prev[0], cur[k], cur[j]))
            elif len(cur) == 1:
                f = bm.faces.new((prev[j], prev[k], cur[0]))
            else:
                f = bm.faces.new((prev[j], prev[k], cur[k], cur[j]))
            f.material_index = mat
            f.smooth = True
            faces.append(f)
    # hard edges along sharp rings
    bm.edges.ensure_lookup_table()
    for verts, _, sharp in rings:
        if sharp and len(verts) > 1:
            for j in range(SEG):
                e = bm.edges.get((verts[j], verts[(j + 1) % SEG]))
                if e:
                    e.smooth = False
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    return faces


def make_material(sprite, index, tag, metallic, roughness, spec):
    mat = common.palette_material(sprite, index, tag, metallic=metallic, roughness=roughness)
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = spec
    return mat


def build(sprite, name, frame, coll):
    used = [LENS, IRIS, RIM, BODY]
    slot = {i: s for s, i in enumerate(used)}
    mats = [make_material(sprite, i, name, **MATS[i]) for i in used]
    bm = bmesh.new()
    eyeball(bm, frame, PROFILE, slot)
    obj = common.mesh_object(name, bm, mats, coll, smooth=None)
    # Outline shell from a sealed plain ball (socket filled): ink on the silhouette only.
    bm = bmesh.new()
    eyeball(bm, frame, PLAIN, {BODY: 0})
    src = common.mesh_object(f"{name}_src", bm, [mats[slot[BODY]]], coll, smooth=True)
    shell = common.outline_shell(src, coll, voxel=0.012, faces=1200, islands="outer")
    shell.name = f"{name}_outline"
    shell.data.name = f"{name}_outline"
    bpy.data.objects.remove(src, do_unlink=True)
    bpy.context.view_layer.update()
    return obj, shell


def main():
    for o in list(bpy.data.objects):  # the startup scene's cube, light and camera
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = common.load_sprite(ROOT, NAME)
    base = sprite["sprites"][0]
    objs = []
    for i, (index, frame) in enumerate(FRAMES.items()):
        name = NAME if i == 0 else f"{NAME}-f{i + 1}"
        coll = common.reset_collection(name)
        obj, shell = build(sprite, name, frame, coll)
        objs.append((index, name, obj, shell))
        tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        print(f"{name}: {tris} tris, shell {len(shell.data.polygons)} faces")
        assert len(shell.data.polygons) > 0, "empty outline shell"
        common.export_sprite_model(ROOT, [obj, shell], f"enemies/{name}", [{**base, "frames": [index]}])


if __name__ == "__main__":
    main()
