"""Steel eyeball (newshl.shp 117): a 3D version of its sprite.

- newshl-117, steel eyeball: a polished steel sentry orb 9.5 px across (inner mask: rows 3-11,
  columns 2-10, a circle of radius 4.75 px round edge point (6.5, 7.5)) resting on the ground. Its
  eye is a domed blue lens in a proud blue anodised bezel, centred 1.5 px down-screen of the ball's
  centre (the sprite's blue: rows 7-10, columns 4-8), so the lens axis leans 21 deg toward the
  camera. The ball is lathed round that axis: lens, dark inner lip, bezel, a seam groove round the
  bezel, and a split-line groove round the back (behind the limb from above). Flush trunnion caps
  on its left and right flanks, and a louvred vent plate on its back (north) face. The sprite's
  white 13-15 at the upper left and the 61 glint on the lens are sheen; its 7-9 lower limb is
  lighting (rubric).

Units: X = (u - 6) / 12, Y = (7 - v) / 12 for sprite edge coordinates (u right, v down), Z up.
Hard-surface build (D50-D53, D65, D189, D192); one frame; outline shell from a sealed copy.

Run: blender --background --python assets/blender/enemies/newshl-117.py [-- --preview out.png]
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

NAME = "newshl-117"
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


# --- newshl-117: steel eyeball ---------------------------------------------------------------------

EYE_C = (6.5, 7.5)      # ball centre, sprite edge coordinates
EYE_R = 4.75            # px
EYE_TILT = 21.0         # lens axis lean toward -Y (down-screen), degrees from vertical


def eyeball(sprite, coll):
    name = "newshl-117"
    mats = [
        material(sprite, 10, f"{name}_shell", 0.3, 0.32, coat=0.35, coat_rough=0.25),  # 0
        material(sprite, 53, f"{name}_bezel", 0.55, 0.32),                                                # 1
        material(sprite, 57, f"{name}_lens", 0.1, 0.15, glow=0.12, coat=1.0, coat_rough=0.05),            # 2
        material(sprite, 50, f"{name}_lip", 0.2, 0.6),                                                    # 3
        material(sprite, 8, f"{name}_seam", 0.2, 0.7),                                                    # 4
        material(sprite, 9, f"{name}_cap", 0.4, 0.35, spec=STEEL_SPEC),                                   # 5
    ]
    SH, BZ, LN, LP, SM_, CP = range(6)
    R_ = EYE_R
    centre = Vector((X(EYE_C[0]), Y(EYE_C[1]), R_ * PX + 0.004))
    tilt = Matrix.Rotation(math.radians(EYE_TILT), 4, "X")   # +Z -> (0, -sin t, cos t)
    # (polar angle from the lens axis deg, radius px, material of the band ending here)
    prof = [(0, 4.93, LN), (5, 4.925, LN), (10, 4.90, LN), (14, 4.86, LN), (16.2, 4.80, LN),
            (16.6, 4.58, LP), (18.2, 4.56, LP), (18.6, 4.93, BZ), (19.6, 5.02, BZ), (26.2, 5.02, BZ),
            (27.6, 4.90, BZ), (28.2, 4.66, SM_), (29.4, 4.66, SM_), (30.0, 4.75, SH)]
    a = 30.0
    while a < 96:
        a += 7.0
        prof.append((min(a, 97.5), R_, SH))
    prof += [(98.6, 4.58, SM_), (100.0, 4.58, SM_), (101.0, R_, SH)]
    a = 101.0
    while a < 172:
        a += 9.0
        prof.append((min(a, 172.0), R_, SH))
    prof.append((180.0, R_, SH))
    sides = 40
    bm = bmesh.new()
    rings, bands = [], []
    for phi, r, m in prof:
        p = math.radians(phi)
        if phi in (0, 180):
            pts = [Vector((0, 0, r * math.cos(p)))]
        else:
            pts = [Vector((r * math.sin(p) * math.cos(2 * math.pi * k / sides),
                           r * math.sin(p) * math.sin(2 * math.pi * k / sides), r * math.cos(p))) for k in range(sides)]
        rings.append([bm.verts.new(centre + (tilt @ (q * PX))) for q in pts])
        bands.append(m)
    bridge(bm, rings, bands)

    # Trunnion caps, flush on the left and right flanks (on the equator, so the silhouette stays round).
    for s in (-1, 1):
        # (radius px, distance px from the ball's centre along X): a low flat boss, 0.1 px proud
        prof_c = [(1.6, 4.15), (1.6, 4.78), (1.42, 4.86), (0.0, 4.86)]
        cr = []
        for rho, d in prof_c:
            if rho == 0:
                cr.append([bm.verts.new(centre + Vector((s * d * PX, 0, 0)))])
                continue
            cr.append([bm.verts.new(centre + Vector((s * d, rho * math.cos(2 * math.pi * k / 16),
                                                     rho * math.sin(2 * math.pi * k / 16))) * PX) for k in range(16)])
        # sunk base ring -> surface ring -> chamfer -> crown; the base closed by a disc
        bridge(bm, cr, [CP, CP, CP, CP])
        bm.faces.new(cr[0]).material_index = CP

    # Louvred vent plate on the back (north) face: a curved plate 0.12 px proud with three dark slots.
    def sph(lon, el, r):
        lo, e = math.radians(lon), math.radians(el)
        return centre + Vector((r * math.cos(e) * math.sin(lo), r * math.cos(e) * math.cos(lo), r * math.sin(e))) * PX
    lons = [-20 + 40 * i / 8 for i in range(9)]
    els = [-14, -10, -7.5, -5.5, -2.5, -0.5, 2.5, 4.5, 7.5, 9.5, 14]
    slot_rows = {3, 5, 7}       # bands between els[i] and els[i+1] that are slots
    grid = [[bm.verts.new(sph(lo, el, R_ + 0.14)) for lo in lons] for el in els]
    for i in range(len(els) - 1):
        for j in range(len(lons) - 1):
            f = bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
            f.material_index = SM_ if (i in slot_rows and 0 < j < len(lons) - 2) else CP
    # its rim: skirt down into the ball
    edge = [grid[0][j] for j in range(len(lons))] + [grid[i][-1] for i in range(1, len(els))] + \
           [grid[-1][j] for j in range(len(lons) - 2, -1, -1)] + [grid[i][0] for i in range(len(els) - 2, 0, -1)]
    inner = []
    for v in edge:
        d = (v.co - centre).normalized()
        inner.append(bm.verts.new(centre + d * (R_ - 0.25) * PX))
    for k in range(len(edge)):
        j = (k + 1) % len(edge)
        bm.faces.new((edge[j], edge[k], inner[k], inner[j])).material_index = CP
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    obj = common.mesh_object(name, bm, mats, coll, smooth=True)
    finish(obj, 40)
    return obj


# --- newshl-118: lava lump (rock builder, D175) -----------------------------------------------------

def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj = eyeball(sprite, coll)
    sh = shell_of(obj, coll, NAME, voxel=0.012, faces=2000, smooth=4, inside=0.003)
    common.export_sprite_model(ROOT, [obj, sh], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        f = sprite["frames"][0]
        common.render_preview([obj, sh], out, ROOT / "reference" / "models" / NAME / f["image"], size=f["size"])


if __name__ == "__main__":
    main()
