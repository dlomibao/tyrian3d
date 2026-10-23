"""Spinning brown pod (newsh2.shp frames 171, 190, 209, 228, 247, 266): a 3D version of its sprite.

Seen in episodes 1, 2 and 3 (levels 1.25, 1.3, 2.6, 3.17). A brown teardrop, blunt at the top
and pointed at the bottom, flattened so that it is 9 px wide face on (frame 171) and 5 px edge on
(frame 228). The six frames spin it about its long axis (the sprite's vertical): its silhouette
narrows and widens and the light ridges slide across. Each frame is the same pod turned to a
different angle, so each frame gets its own model (newsh2-171, -f2 ... -f6), turned to match.

The pod has a dark groove round its shoulder, a light ridge down the middle of each face with a
bright stud on it, and light ridges along both edges. It spins in the air just above the ground.

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


def build_mesh(mats_idx):
    """The pod lying along Y with its faces up (+Z), centred on its axis at the origin."""
    BODY, BAND, RIDGE, STUD, TIP = mats_idx
    bm = bmesh.new()
    y = lambda v: G.y(v)  # noqa: E731
    P = lib.PX
    common.loft(bm, [(y(v), a * P, b * P, 0.0) for v, a, b in PROFILE[:9]], sides=14, mat_index=BODY)
    common.loft(bm, [(y(v), a * P, b * P, 0.0) for v, a, b in PROFILE[8:]], sides=14, mat_index=TIP)
    # Dark groove band round the shoulder (row 3).
    common.loft(bm, [(y(2.75), 4.68 * P, 2.66 * P, 0.0), (y(3.6), 4.68 * P, 2.66 * P, 0.0)], sides=14,
                mat_index=BAND)
    # Light ridges down the middle of each face and along both edges.
    for vs in ((3.6, 9.4),):
        v0, v1 = vs
        steps = [v0 + (v1 - v0) * i / 4 for i in range(5)]
        for sgn in (1, -1):
            start = len(bm.verts)
            secs = [(y(v), 0.55 * P, 0.45 * P, sgn * profile_at(v)[1] * P * 0.93) for v in steps]
            secs = [(y(v0 - 0.4), 0.0, 0.0, secs[0][3])] + secs + [(y(v1 + 0.4), 0.0, 0.0, secs[-1][3])]
            common.loft(bm, secs, sides=6, mat_index=RIDGE)
        for sgn in (1, -1):
            start = len(bm.verts)
            steps = [1.4 + (11.6 - 1.4) * i / 6 for i in range(7)]
            common.loft(bm, [(y(v), 0.45 * P, 0.55 * P, 0.0) for v in steps], sides=6, mat_index=RIDGE)
            bm.verts.ensure_lookup_table()
            for vert in bm.verts[start:]:
                v = G.h / 2 - vert.co.y / P
                vert.co.x += sgn * profile_at(v)[0] * P * 0.9
    # Bright studs on each face (row 5).
    for sgn in (1, -1):
        before = set(bm.faces)
        res = bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=5, radius=1.0)
        _, b = profile_at(5.5)
        for vert in res["verts"]:
            vert.co.x *= 0.7 * P
            vert.co.y = vert.co.y * 0.75 * P + G.y(5.5)
            vert.co.z = vert.co.z * 0.45 * P + sgn * b * P
        for f in set(bm.faces) - before:
            f.material_index = STUD
    return bm


def build(sprite, angle, name, coll):
    tag = "nsh2_171"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(23, metallic=0.35, roughness=0.45),  # 0 brown shell
        pal(18, metallic=0.2, roughness=0.6),  # 1 dark groove
        pal(27, metallic=0.45, roughness=0.35),  # 2 light ridges
        pal(30, metallic=0.5, roughness=0.3),  # 3 bright studs
        pal(21, metallic=0.3, roughness=0.5),  # 4 darker lower point
    ]
    bm = build_mesh((0, 1, 2, 3, 4))
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
