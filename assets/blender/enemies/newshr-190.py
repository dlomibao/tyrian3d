"""Tan rock (newshr.shp frame 190): a 3D version of its sprite.

Seen in episode 3 (levels 19 and 4). A small tumbling rock, 9 x 11 px: an elongated lump of sandy
stone lying on the diagonal from upper right to lower left, lit from the upper left, with darker
brown edges. One frame, one model: a lumpy rock whose outline follows the sprite and whose faces
take the colour of the sprite pixel under them, the lighter pixels standing a little prouder.

Run: blender --background --python assets/blender/enemies/newshr-190.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b022 as lib  # noqa: E402

NAME = "newshr-190"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
RZ = 0.34  # half thickness, units (about 4 px either side of the midplane; 9 px wide)
HR_EXP = 0.8  # side curvature: 1 is a plain ellipsoid, lower makes steeper walls
SIDE_NZ = 0.2  # faces steeper than this take the dark rim colour
SHOULDER_NZ = 0.5  # faces between this and SIDE_NZ are no lighter than 23, a shaded shoulder
RZ_TOP, RZ_BOTTOM = 0.37, 0.33  # crown about 4.5 px up, base about 4 px down
# (column, row, radius px, depth px) of the pits, in sprite pixel coordinates
PITS = [(8.0, 7.6, 2.0, 0.8), (4.0, 7.4, 1.4, 0.6)]


def lumps(x, y, z):
    """Irregular facets so it reads as stone, not a sausage."""
    return 1 + 0.07 * math.sin(4.1 * x - 0.7) * math.cos(3.3 * y + 0.8) + 0.06 * math.sin(4.5 * z + 2.7 * x + 1.1)


def build(sprite):
    coll = common.reset_collection(NAME)
    grid = lib.Grid(12, 14, sprite["frames"][0]["pixels"])
    mats = lib.Mats(NAME, sprite["colors"])
    # Sandy stone, one material per shade (21-27) so the top keeps the sprite's warm tan mottling;
    # 19, 178 and 179 are the darkest brown edge pixels and share 20's.
    dark = mats(20, roughness=1.0)
    shades = {19: dark, 20: dark, 178: dark, 179: dark}
    for i in range(21, 28):
        shades[i] = mats(i, roughness=1.0)

    light = {shades[i] for i in range(24, 28)}

    def slot(i):
        return shades.get(i, dark)

    def brightness(i):
        return 0.05 if i in (178, 179) else (i - 19) / 8

    bm = bmesh.new()
    # The sprite shades it as one round lump (central highlight, dark rim all round), so it is
    # about as thick as it is wide: +-RZ around the midplane, nearly a round cross-section.
    rock(bm, grid, RZ, slot, brightness, n=10, relief=0.22, under_slot=dark)
    for v in bm.verts:  # a slightly taller crown than base, so the game camera sees a dome
        v.co.z *= (RZ_TOP if v.co.z > 0 else RZ_BOTTOM) / RZ
    pits(bm, grid)
    # The steep flanks are the sprite's dark rim, not stripes of whatever pixel lies under them.
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        f.normal_update()
        if f.normal.z < SIDE_NZ:
            f.material_index = dark
        elif f.normal.z < SHOULDER_NZ and f.material_index in light:
            f.material_index = shades[23]  # shade the shoulder so the tan top fades into the rim
    for m in mats.list:  # matte sandy stone: a soft tan lift, not a grey gloss
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Roughness"].default_value = 1.0
        m.roughness, m.metallic, m.specular_intensity = 1.0, 0.0, 0.1  # viewport/preview shading
        for key in ("Specular IOR Level", "Specular"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = 0.15
                break
    return common.mesh_object(NAME, bm, mats.list, coll, smooth=True)


def rock(bm, grid, rz, slot_for, brightness, n=10, relief=0.22, shrink=0.15, under_slot=None):
    """lib_b022.rock reshaped into one round boulder: a cube-mapped sphere whose equator follows
    the sprite's mask (so the top view is unchanged) but whose upper and lower latitudes follow a
    smoothed, rounder outline, with gently curved sides (no vertical walls or lobes) so the section
    is an irregular ellipsoid. The lumps and the brightness relief act on both halves alike, so the
    underside is the same craggy stone as the top rather than a smooth shell."""
    cells = [(c, r) for r in range(grid.h) for c in range(grid.w) if grid.filled(c, r)]
    cc = sum(c + 0.5 for c, _ in cells) / len(cells)
    cr = sum(r + 0.5 for _, r in cells) / len(cells)
    samples = 144
    prof = lib.radial_profile(grid, cc, cr, samples)
    k = samples // 7  # +-50 degrees: the rounded outline the shoulders follow
    soft = [sum(prof[(i + j) % samples] for j in range(-k, k + 1)) / (2 * k + 1) for i in range(samples)]

    def interp(p, a):
        t = (a % (2 * math.pi)) / (2 * math.pi) * samples
        i = int(t)
        f = t - i
        return p[i % samples] * (1 - f) + p[(i + 1) % samples] * f

    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    first_face, first_vert = len(bm.faces), len(bm.verts)
    cube = bmesh.ops.create_cube(bm, size=2.0)
    edges = list({e for v in cube["verts"] for e in v.link_edges})
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=n - 1, use_grid_fill=True)
    bm.verts.ensure_lookup_table()
    ox, oy = (cc - grid.w / 2) * lib.U, (grid.h / 2 - cr) * lib.U
    for v in bm.verts[first_vert:]:
        x, y, z = v.co
        sx = x * math.sqrt(max(0.0, 1 - y * y / 2 - z * z / 2 + y * y * z * z / 3))
        sy = y * math.sqrt(max(0.0, 1 - z * z / 2 - x * x / 2 + z * z * x * x / 3))
        sz = z * math.sqrt(max(0.0, 1 - x * x / 2 - y * y / 2 + x * x * y * y / 3))
        h = math.hypot(sx, sy)
        a = math.atan2(sy, sx)
        w = min(1.0, abs(sz) * 1.4) ** 1.5  # 0 at the equator, 1 over the crown and the base
        rad = (1 - w) * interp(prof, a) + w * interp(soft, a) - shrink
        hr = h ** HR_EXP if h > 0 else 0.0
        s = lumps(sx, sy, sz)
        r = rad * lib.U * hr * (0.96 + 0.04 * s)
        px, py = ox + r * math.cos(a), oy + r * math.sin(a)
        zz = rz * sz * s
        idx = grid.sample(px, py)
        if idx is not None:
            zz *= 1 + relief * (brightness(idx) - 0.5) * 2 * min(1.0, h * 1.5)
        v.co = (px, py, zz)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first_face:]:
        f.normal_update()
        if under_slot is not None and f.normal.z < -0.35:
            f.material_index = under_slot
            continue
        c = f.calc_center_median()
        idx = grid.sample(c.x, c.y)
        f.material_index = slot_for(idx if idx is not None else -1)
    return first_face


def pits(bm, grid):
    """Shallow craters where the sprite has dark pixels inside the lit face: the 22s right of
    centre (columns 7-9, rows 7-8) and the darker pair at the lower left (column 4, rows 7-8)."""
    for v in bm.verts:
        x, y, z = v.co
        if z <= 0.4 * RZ:
            continue
        for c, r, rad, depth in PITS:
            d = math.hypot(x - grid.x(c), y - grid.y(r)) / (rad * lib.U)
            if d < 1:
                v.co.z -= depth * lib.U * (1 - d * d) ** 2 * min(1.0, (z - 0.4 * RZ) / (0.4 * RZ))


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)


if __name__ == "__main__":
    main()
