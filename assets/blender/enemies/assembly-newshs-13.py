"""Grey ridge-topped block marked 26 (newshs.shp frames 13, 15, 51, 53, 89, 91): a 3D version of
its sprites.

Seen in episodes 2 and 3 (levels 2.8, 3.15). Six 2x2 pieces (two across, three down) make one
48 x 84 px object: a long grey block with a ridge down its middle and a hipped back end, its
lit left slope and shaded right slope each stencilled 26, standing on a dark grilled plinth on
the stone floor.

Built whole and cut into the pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshs-13.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b073 as L  # noqa: E402

NAME = "assembly-newshs-13"
PIECES = [["newshs-13", "newshs-15"], ["newshs-51", "newshs-53"], ["newshs-89", "newshs-91"]]
TOP, EAVE = 0.5, 0.3


def build(sprite, g):
    coll = common.reset_collection(NAME)
    m = L.Mats("nshs13", sprite["colors"])
    bm = bmesh.new()
    L.floor(bm, g, m, sprite["colors"], rect=(0, 28, 48, 84))
    tones = L.grey_tones(m, sprite["colors"], finish=lambda i: m(i, metallic=0.4, roughness=0.5))

    # The plinth (columns 5-42, rows 50-68), its top grilled.
    L.box(bm, g.ex(5), g.ey(68.5), g.ex(42.5), g.ey(50), 0.0, 0.15, mat=m.metal(3))
    L.painted(bm, g, 5, 54, 43, 69, lambda x, y: 0.153, tones)

    # The block: ridge at the edge between columns 23 and 24, eaves at columns 6 and 41, a
    # hipped back end (rows 11-17) and the front end at rows 53-55.
    xl, xm, xr = g.ex(6.2), g.ex(24), g.ex(41.8)
    yb_side, yb_mid, yt_side, yt_mid = g.ey(55.5), g.ey(54.0), g.ey(17), g.ey(11.5)
    pts = []
    for x, z, yt, yb in ((xl, EAVE, yt_side, yb_side), (xm, TOP, yt_mid, yb_mid), (xr, EAVE, yt_side, yb_side)):
        pts += [(x, yt, 0.0), (x, yt, z), (x, yb, 0.0), (x, yb, z)]
    n = len(bm.faces)
    verts = [bm.verts.new(p) for p in pts]
    hull = bmesh.ops.convex_hull(bm, input=verts)
    loose = {g_ for g_ in hull["geom_interior"] + hull["geom_unused"] if isinstance(g_, bmesh.types.BMVert)}
    if loose:
        bmesh.ops.delete(bm, geom=list(loose), context="VERTS")
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    left, right, end = m.metal(9), m.metal(6), m.metal(5)
    for f in bm.faces[n:]:
        nx, nz = f.normal.x, f.normal.z
        f.material_index = left if (nz > 0.3 and nx < -0.1) else right if (nz > 0.3 and nx > 0.1) else end
        if abs(nz) < 0.3 and abs(f.normal.x) > 0.9:
            f.material_index = left if nx < 0 else right
        f.smooth = False

    # The stencilled 26 on each slope, painted on.
    def zl(x, y):
        return EAVE + (TOP - EAVE) * (x - xl) / (xm - xl) + 0.004

    def zr(x, y):
        return EAVE + (TOP - EAVE) * (xr - x) / (xr - xm) + 0.004
    light, shade = m.metal(13), m.metal(10)
    L.painted(bm, g, 7, 18, 24, 53, zl, lambda i: light if 12 <= i <= 15 or i in (108, 109) else None)
    L.painted(bm, g, 24, 18, 41, 53, zr, lambda i: shade if 9 <= i <= 11 or i in (106, 108) else None)
    return L.finish(NAME, bm, m, coll), []


if __name__ == "__main__":
    L.run_assembly(NAME, PIECES, build, __file__, 2, 3)
