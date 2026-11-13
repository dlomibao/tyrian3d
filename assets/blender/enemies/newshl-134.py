"""Red-banded canister (newshl.shp 134): a 3D version of its sprite.

- newshl-134, red-banded canister: a grey lathe 4 px across lying nose down the screen: a flared
  tail cap (rows 1-3, dark steel), a thin neck drawn in ink only (row 4, r 0.35 px so it never
  covers the ink pixels), a collar (rows 5-6), the 4 px body (rows 7-10) with a glowing red band
  (row 8) between two steel lips, and a dark rounded nose (row 11). The light stripe down column 5
  is sheen on a round body.


Units: X = (u - 6) / 12, Y = (7 - v) / 12 for sprite edge coordinates (u right, v down), Z up.
Hard-surface build (D50-D53, D65, D189, D192); one frame; outline shell from a sealed copy.

Run: blender --background --python assets/blender/enemies/newshl-134.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

NAME = "newshl-134"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12
W, H = 12, 14


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def X(u):
    return (u - W / 2) * PX


def Y(v):
    return (H / 2 - v) * PX


# --- helpers (local; not shared) -----------------------------------------------------------------

def bridge(bm, rings, mats):
    """Faces between consecutive rings (lists of verts; a single vert is a pole). Band i (between
    ring i-1 and i) takes mats[i]."""
    for i in range(1, len(rings)):
        r0, r1, m = rings[i - 1], rings[i], mats[i]
        n = max(len(r0), len(r1))
        for k in range(n):
            j = (k + 1) % n
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            bm.faces.new(f).material_index = m


def material(sprite, index, tag, metallic, roughness, glow=0.0, spec=None, coat=0.0, coat_rough=0.2):
    m = common.palette_material(sprite, index, tag, metallic=metallic, roughness=roughness, emission_strength=glow)
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if spec is not None:
        bsdf.inputs["Specular IOR Level"].default_value = spec
    if coat:
        bsdf.inputs["Coat Weight"].default_value = coat
        bsdf.inputs["Coat Roughness"].default_value = coat_rough
    return m


def shell_of(obj, coll, name, **kw):
    """Outline shell (D51) from a sealed copy of the model, every outer island kept (D189)."""
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    bpy.context.view_layer.update()
    sh = common.outline_shell(closed, coll, islands="outer", **kw)
    sh.name = sh.data.name = f"{name}_outline"
    bpy.data.objects.remove(closed)
    assert len(sh.data.polygons) > 0, f"{name}: empty outline shell"
    return sh


def finish(obj, angle=38):
    obj.data.shade_smooth()
    obj.data.set_sharp_from_angle(angle=math.radians(angle))

# F0 of IOR 2.4 through Specular IOR Level (D176: the exporter drops a bare IOR).
STEEL_SPEC = 0.5 * ((1.4 / 3.4) ** 2 / 0.04)


def canister(sprite, coll):
    name = "newshl-134"
    mats = [
        material(sprite, 7, f"{name}_body", 0.4, 0.3, spec=STEEL_SPEC, coat=0.5, coat_rough=0.2),  # 0
        material(sprite, 6, f"{name}_cap", 0.45, 0.38, spec=STEEL_SPEC),                           # 1
        material(sprite, 4, f"{name}_dark", 0.4, 0.45),                                             # 2
        material(sprite, 115, f"{name}_band", 1.0, 0.85, glow=0.9),                                 # 3
        material(sprite, 9, f"{name}_lip", 0.5, 0.3, spec=STEEL_SPEC),                              # 4
        material(sprite, 3, f"{name}_groove", 0.2, 0.7),                                            # 5
    ]
    BD, CP, DK, BN, LP, GR = range(6)
    zc = 2.0 * PX + 0.003
    # (v edge row, radius px, material of the band ending here); nose toward +v (down-screen).
    prof = [(1.0, 0.0, CP), (1.0, 0.9, CP), (1.08, 1.05, CP), (1.06, 1.55, CP), (1.15, 1.9, CP), (1.35, 2.0, CP),
            (1.9, 2.0, CP), (1.95, 1.88, GR), (2.1, 1.88, GR), (2.15, 2.0, CP), (2.7, 2.0, CP), (2.95, 1.75, CP),
            (3.1, 1.2, CP), (3.85, 1.0, CP), (3.97, 0.35, DK), (4.95, 0.35, DK), (5.05, 0.95, BD),
            (5.15, 1.05, BD), (5.75, 1.05, BD), (5.8, 0.92, GR), (5.95, 0.92, GR), (6.0, 1.05, BD),
            (6.55, 1.08, BD), (6.95, 1.7, BD), (7.3, 1.98, BD), (7.75, 2.0, BD),
            (7.78, 2.1, LP), (7.98, 2.1, LP), (8.02, 1.96, LP), (8.08, 2.0, BN), (8.9, 2.0, BN),
            (8.98, 1.96, BN), (9.02, 2.1, LP), (9.22, 2.1, LP), (9.25, 2.0, LP), (10.3, 1.97, BD),
            (10.55, 1.85, BD), (10.62, 1.72, GR), (10.72, 1.6, DK), (11.1, 1.3, DK), (11.5, 0.95, DK),
            (11.8, 0.55, DK), (11.97, 0.2, DK), (12.0, 0.0, DK)]
    sides = 20
    bm = bmesh.new()
    rings, bands = [], []
    for v, r, m in prof:
        if r == 0:
            rings.append([bm.verts.new((0.0, Y(v), zc))])
        else:
            rings.append([bm.verts.new((r * PX * math.cos(2 * math.pi * (k + 0.5) / sides), Y(v),
                                        zc + r * PX * math.sin(2 * math.pi * (k + 0.5) / sides))) for k in range(sides)])
        bands.append(m)
    bridge(bm, rings, bands)
    # The tail's rear face: a recessed dark disc (rows 0-1) is the first band (centre to r 0.9) above.
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    obj = common.mesh_object(name, bm, mats, coll, smooth=True)
    finish(obj, 40)
    return obj


# --- main ---------------------------------------------------------------------------------------

def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj = canister(sprite, coll)
    sh = shell_of(obj, coll, NAME, voxel=0.008, faces=1500, smooth=3, inside=0.002)
    common.export_sprite_model(ROOT, [obj, sh], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        f = sprite["frames"][0]
        common.render_preview([obj, sh], out, ROOT / "reference" / "models" / NAME / f["image"], size=f["size"])


if __name__ == "__main__":
    main()
