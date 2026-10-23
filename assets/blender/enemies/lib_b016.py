"""Helpers shared by batch b016's models: sprite coordinates, a blade lofted with a sculpted
cross-section, and the usual build/export/preview main.

build-models.sh skips lib_ files; the model scripts import this next to them.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402,F401


def px(c):
    """Sprite column (pixel centre, or any fractional column) of a 24x28 sprite to Blender X."""
    return (c + 0.5 - 12) / 12


def row(r):
    """Sprite row (pixel centre) of a 24x28 sprite to Blender Y: sprite up is +Y."""
    return (14 - (r + 0.5)) / 12


def ex(c):
    """Sprite pixel edge (column boundary) to Blender X."""
    return (c - 12) / 12


def ey(r):
    """Sprite pixel edge (row boundary) to Blender Y."""
    return (14 - r) / 12


def profile_blade(bm, sections, top, bottom, mats, side=1, mirror_about=0.0, under_mat=0):
    """Loft a blade along Y whose cross-section is sculpted across its width rather than an ellipse.

    `sections` are (y, x_inner, x_outer, h_top, h_bottom, extra): the blade spans X from x_inner
    (its inner edge) to x_outer. `top(width_px, extra)` returns a list of (d_px, z_factor) from the
    inner edge (d = 0) out to the outer edge (d = width): the top surface, scaled by h_top.
    `bottom(width_px, extra)` likewise for the underside (z factors positive, applied downward,
    scaled by h_bottom), ordered inner to outer and with the same count as `top`. `mats[k]` is the
    material of the top strip between points k and k+1; the underside uses `under_mat`.
    side=-1 mirrors the blade about X = mirror_about. Ends are capped."""
    rings = []
    n = None
    for y, xi, xo, ht, hb, extra in sections:
        w = abs(xo - xi) * 12
        sgn = 1 if xo > xi else -1
        tp = top(w, extra)
        bt = bottom(w, extra)
        if n is None:
            n = len(tp)
        assert len(tp) == n and len(bt) == n
        ring = []
        for d, f in tp:
            ring.append((xi + sgn * d / 12, y, ht * f))
        for d, f in reversed(bt):
            ring.append((xi + sgn * d / 12, y, -hb * f))
        verts = []
        for x, yy, z in ring:
            if side < 0:
                x = 2 * mirror_about - x
            verts.append(bm.verts.new((x, yy, z)))
        rings.append(verts)
    m = len(rings[0])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(m):
            j = (k + 1) % m
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = mats[k] if k < n - 1 else under_mat
    bm.faces.new(rings[0]).material_index = under_mat
    bm.faces.new(list(reversed(rings[-1]))).material_index = under_mat


def run(name, build, file):
    """Build, export every model and, with -- --preview <png>, preview the first.

    `build(sprite)` returns a list of (model_name, objects, sprites) to export."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    models = build(sprite)
    for model, objects, sprites in models:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = sprite["frames"][0]
        ref = root / "reference" / "models" / name / frame["image"]
        common.render_preview(models[0][1], out, ref, size=frame["size"])
    return sprite
