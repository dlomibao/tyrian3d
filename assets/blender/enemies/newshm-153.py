"""newshm-153, the WINDY red wall block with three raised chevrons (newshm.shp frame 153).

What it is: one block of the WINDY red block wall (assembly-newshm-1). It spawns rigid in rows beside
newshm-1 / -15 / -17 / -53, so the block itself is lib_newshm_block's cast shell, unchanged
(imported, not copied: same superellipse plan, section, south roll bands, foot plate, sockets,
bolts, enamel roughness), in the sprite's flat-top index 71 with the 66 steel foot, as newshm-1.

The emblem: three raised chevrons pointing up the screen, pressed up out of the enamel top. Their
crest lines are traced from the sprite's lit / body pixel pairs (left arms 74-75 lit on the north-west
face, right arms 72 with the 70 shadow on the inner face): apexes at col 11.5, rows 3 / 7 / 12, each
arm 4 rows down and 4 cols out. Section: a chamfered ridge (wide foot sunk into the top, chamfer,
narrow flat crest), mitred at the apex, ends ramped down into the top (no square-cut ends); every
section point follows the shell surface, so the north apex wraps over the shoulder (no blade).
Colour: pal 72, the median of the chevron pixels once the 73-75 sheen and 70 shadow are left out:
the same enamel family one step lighter than the 71 shell. The sprite's lit and shadow pixels on
the chevrons are the game lights on those faces (art rule 2).

Run: blender --background --python assets/blender/enemies/newshm-153.py [-- --no-bake] [--out review.glb]
Exports public/models/enemies/newshm-153.glb + src/render/spriteModels/newshm-153.json (or only --out).
The old lib_b078 is merged away: this script uses lib_newshm_block like its wall neighbours.
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve()
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def find_repo():
    if "--repo" in argv:
        return Path(argv[argv.index("--repo") + 1]).resolve()
    for p in HERE.parents:
        if (p / "package.json").exists() and (p / "assets" / "blender" / "common.py").exists():
            return p
    raise SystemExit("newshm-153: pass --repo <tyrian checkout> (no repo above this script)")


ROOT = find_repo()
sys.path.insert(0, str(ROOT / "assets" / "blender"))
sys.path.insert(0, str(ROOT / "assets" / "blender" / "enemies"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
import lib_newshm_block as block  # noqa: E402

NAME = "newshm-153"
if not (ROOT / "reference" / "models" / NAME / "sprite.json").exists():
    raise SystemExit(f"reference/models/{NAME} is missing under {ROOT}: run `npm run catalogue` there")

SHELL_PAL, FOOT_PAL, CHEV_PAL = 71, 66, 72

# Chevron crests in sprite pixel-centre coordinates (col, row): apex and the two arm ends.
APEX_ROWS = (3.0, 7.0, 12.0)
ARM_DC, ARM_DR = 4.0, 4.15     # arm run: cols out, rows down
APEX_C = 11.5
# Ridge section across the crest (perpendicular offset px, height px over the flat top H):
# foot sunk into the enamel, chamfer, fillet, narrow flat crest.
SECTION = [(1.10, -0.35), (1.02, 0.08), (0.78, 0.44), (0.52, 0.62)]
# Arm-end ramp (distance from the arm end in px, raise factor k): the crest eases down into the top
# over 2.4 px and the upper section narrows towards the foot, so the ends melt into the enamel.
RAMP = [(0.0, 0.0), (0.7, 0.3), (1.5, 0.72), (2.4, 1.0)]


def chevron(m, apex_row, mat):
    """One chevron ridge. Every section point sits on the shell's own surface (block.surface_z,
    clamped to the flat top H) plus its section height, so where an apex reaches the north shoulder
    the ridge wraps down over it instead of standing as a flat blade over the falling shell."""
    pts = [(APEX_C - ARM_DC, apex_row + ARM_DR), (APEX_C, apex_row), (APEX_C + ARM_DC, apex_row + ARM_DR)]
    P = [Vector((*block.P(c, r), 0.0)) for c, r in pts]
    d01 = (P[1] - P[0]).normalized()
    d12 = (P[2] - P[1]).normalized()
    # stations along the polyline: end ramp (west arm), apex, end ramp (east arm)
    # (full-height stations every ~0.6 px too, so the crest follows the curved shoulder between them)
    L = (P[1] - P[0]).length
    run = list(RAMP)
    nfull = max(1, math.ceil((L - RAMP[-1][0]) / 0.6))
    run += [(RAMP[-1][0] + (L - RAMP[-1][0]) * i / nfull, 1.0) for i in range(1, nfull)]
    st = [(P[0] + d01 * t, d01, k) for t, k in run]
    st.append((P[1], None, 1.0))
    st += [(P[2] - d12 * t, d12, k) for t, k in reversed(run)]
    n01 = Vector((-d01.y, d01.x, 0.0))
    n12 = Vector((-d12.y, d12.x, 0.0))
    H = block.H
    sec = SECTION + [(-w, z) for w, z in reversed(SECTION)]
    rows = []
    for p, d, k in st:
        if d is None:
            nm = (n01 + n12).normalized()
            off = nm * (1.0 / max(nm.dot(n01), 0.3))  # mitre
        else:
            off = Vector((-d.y, d.x, 0.0))
        row = []
        for w, z in sec:
            if z >= 0:
                w *= 0.62 + 0.38 * k  # the crest tapers to the foot at the ends
            q = p + off * w
            zs = min(H, block.surface_z(q.x, q.y))
            zz = zs + z if z < 0 else zs + 0.02 + z * (0.1 + 0.9 * k)
            row.append(m.bm.verts.new((q.x, q.y, zz)))
        rows.append(row)
    n = len(rows[0])
    for r0, r1 in zip(rows, rows[1:]):
        for i in range(n - 1):
            m.bm.faces.new((r0[i], r1[i], r1[i + 1], r0[i + 1])).material_index = mat
        m.bm.faces.new((r0[n - 1], r1[n - 1], r1[0], r0[0])).material_index = mat  # bottom
    m.bm.faces.new(list(reversed(rows[0]))).material_index = mat
    m.bm.faces.new(rows[-1]).material_index = mat


def build(sprite, coll):
    block.VARIANTS[NAME] = (SHELL_PAL, FOOT_PAL)
    parts, mats = block.build(NAME, sprite, coll)
    chev = common.palette_material(sprite, CHEV_PAL, f"{NAME}_chevron", metallic=0.28, roughness=0.3)
    mats.append(chev)
    for o in parts:
        o.data.materials.append(chev)
    CH = len(mats) - 1
    m = block.Mesh()
    for r in APEX_ROWS:
        chevron(m, r, CH)
    bmesh.ops.recalc_face_normals(m.bm, faces=m.bm.faces)
    bmesh.ops.transform(m.bm, matrix=__import__("mathutils").Matrix.Scale(block.PX, 4), verts=m.bm.verts)
    me = bpy.data.meshes.new(NAME + "_chevrons")
    m.bm.to_mesh(me)
    m.bm.free()
    for mt in mats:
        me.materials.append(mt)
    o = bpy.data.objects.new(NAME + "_chevrons", me)
    coll.objects.link(o)
    o.data.shade_smooth()
    o.data.set_sharp_from_angle(angle=math.radians(38))
    parts.append(o)
    return parts, mats


def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    parts, mats = build(sprite, coll)
    # The ink shell comes from the sealed block body alone (pre-join copy): the chevrons and bolts
    # stand inside the top view, and in the shell their south faces drew ink lines across the top.
    closed = parts[0].copy()
    closed.data = parts[0].data.copy()
    closed.modifiers.clear()
    coll.objects.link(closed)
    obj = T.join(parts, NAME)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        tint, textured = T.TINT, T.TEXTURED
        T.TINT = (1.0, 1.0, 1.0)
        T.TEXTURED = tuple(range(len(mats)))
        try:
            T.bake_maps(obj, tempfile.mkdtemp(prefix=f"{NAME}_bake_"), size=1024, samples=96)
        finally:
            T.TINT, T.TEXTURED = tint, textured
        for img in bpy.data.images:
            if img.name.startswith("talon_"):
                img.name = img.name.replace("talon_", f"{NAME}_")
        fmt = "WEBP"
    shell = common.outline_shell(closed, coll, voxel=0.014, faces=1500, smooth=8)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    assert len(shell.data.polygons) > 0, "outline shell has no mesh"
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
        common.export_glb([obj, shell], out, image_format=fmt)
        print("exported", out)
    else:
        common.export_sprite_model(ROOT, [obj, shell], f"enemies/{NAME}", sprite["sprites"], image_format=fmt)

if __name__ == "__main__":
    main()
