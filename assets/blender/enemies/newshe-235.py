"""Broken brown pod (newshe.shp frame 235): a 3D version of its sprite.

A ground object: a round shell split open, seen from above. Its rim is a low ring wall, thin on
the left and top and thick at the front and right, where its shadowed inner wall shows; the
middle is open to the ground. A pink ball sits inside, held by a thin claw that rises from the
front of the rim and bends over the ball's top.

Run: blender --background --python assets/blender/enemies/newshe-235.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b070 as lib  # noqa: E402

NAME = "newshe-235"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def E(ec, er):
    """Pixel-edge coordinates (column, row edges) to Blender X, Y."""
    return ((ec - 12) / 12, (14 - er) / 12)


def build(sprite):
    coll = common.reset_collection(NAME)
    frame = sprite["frames"][0]
    grid = lib.Grid(24, 28, frame["pixels"])
    mats = lib.Mats(NAME, sprite["colors"])
    # A pod's husk is organic, not metal: low metallic and rough, so the light shades it without a
    # metal sheen. The pink ball and bead are glossy (their near-white sprite spots are shine, made
    # by the material, not painted or modelled).
    DARK = mats(65, metallic=0.0, roughness=0.8)  # inner wall in the bowl, claw
    SHELL = mats(67, metallic=0.0, roughness=0.75)  # rim
    LIT = mats(70, metallic=0.0, roughness=0.7)  # redder front of the rim
    BALL = mats(76, metallic=0.0, roughness=0.25)  # pink ball
    BEAD = mats(77, metallic=0.0, roughness=0.25)  # pink bead on the claw
    bm = bmesh.new()

    # Rim: outer outline edges cols 4-20, rows 7-22. The opening is traced from the sprite's open
    # pixels (pixel-edge coordinates): it sits up and left of centre, so the wall is a crescent,
    # 1 px at the left and top and about 4 px at the right and front.
    opening = [(10.2, 8.2), (13.8, 8.2), (15.9, 9.1), (16.0, 10.4), (17, 11.0), (17, 11.4), (16.2, 12),
               (16, 13.5), (16, 14.6), (15, 15.6), (14, 16.6), (12.5, 17.6), (11.6, 18), (8.2, 17.9),
               (7.9, 17.1), (6.1, 16.9), (5.3, 16), (5, 14.5), (5, 12.5), (5.6, 11.4), (6.2, 10.2),
               (8.1, 9.2), (9.9, 8.4)]
    opening = [E(c, r) for c, r in opening]
    n = 48
    ccx, ccy = E(10.8, 13.2)  # every outline point lies on a ray from here
    ocx, ocy, orx, ory = *E(12, 14.5), 8.1 / 12, 7.6 / 12

    def ray_ellipse(dx, dy):
        # Solve ((ccx + t dx - ocx)/orx)^2 + ((ccy + t dy - ocy)/ory)^2 = 1 for t > 0.
        px, py = (ccx - ocx) / orx, (ccy - ocy) / ory
        qx, qy = dx / orx, dy / ory
        a, b, c = qx * qx + qy * qy, 2 * (px * qx + py * qy), px * px + py * py - 1
        t = (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)
        return (ccx + t * dx, ccy + t * dy)

    def ray_polygon(dx, dy, poly):
        best = None
        for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
            ex, ey = x2 - x1, y2 - y1
            den = dx * ey - dy * ex
            if abs(den) < 1e-12:
                continue
            t = ((x1 - ccx) * ey - (y1 - ccy) * ex) / den
            u = ((x1 - ccx) * dy - (y1 - ccy) * dx) / den
            if t > 0 and -1e-9 <= u <= 1 + 1e-9 and (best is None or t < best):
                best = t
        return (ccx + best * dx, ccy + best * dy)

    outer, inner, heights = [], [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        dx, dy = math.cos(a), math.sin(a)
        outer.append(ray_ellipse(dx, dy))
        inner.append(ray_polygon(dx, dy, opening))
        thick = math.hypot(outer[-1][0] - inner[-1][0], outer[-1][1] - inner[-1][1]) * 12
        # A round section: about as tall as it is wide (4 px wide stands about 5 px).
        heights.append((0.9 + 1.0 * thick) / 12)
    profile = [(t, [h * math.sqrt(max(0.0, 1 - (2 * t - 1) ** 2)) ** 0.85 for h in heights])
               for t in (0.0, 0.08, 0.2, 0.35, 0.5, 0.65, 0.8, 0.92, 1.0)]
    first = lib.crater(bm, outer, inner, profile, mat_index=SHELL)

    # The rim's pale pixels at the front right are its highlight (the sprite's light), so they get
    # the rim's own red there, not a pale patch.
    # Dark pixels on the rim stand for its inner wall in shadow, so only faces turned into the bowl
    # take them; the outer side never gets the sprite's dark outline ring.
    def rim_slot(v):
        if v in (16, 64, 65):
            return DARK
        if v <= 67:
            return SHELL
        return LIT
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    for f in bm.faces[first:]:
        c = f.calc_center_median()
        idx = grid.sample(c.x, c.y)
        if idx is None:
            continue
        slot = rim_slot(idx)
        outward = f.normal.x * (c.x - ccx) + f.normal.y * (c.y - ccy) > 0.05 * math.hypot(c.x - ccx, c.y - ccy)
        if slot == DARK and outward:
            slot = SHELL
        f.material_index = slot

    # Pink ball inside (with its dark outline, cols 6-11, rows 10-14), resting on the ground: a
    # sphere about 6 px across and 6 px tall.
    bx, by = E(9.0, 12.4)
    first = lib.blob(bm, (bx, by, 3.0 / 12), (3.0 / 12, 2.55 / 12, 3.0 / 12), segments=20, rings=10,
                     mat_index=BALL)

    # One pink all over: the sprite's dark ring round the ball is its outline and shaded side, and
    # its pale centre its highlight; the game's light and outline draw both.

    # The claw: a thin dark stalk lying in the bowl along the sprite's dark line, from the front of
    # the rim (cols 12-13, row 17) up the ball's right side (cols 13-14, rows 11-13), over to
    # row 9 and hooking down at the ball's top right (col 11, row 10). It stays below the rim.
    path = [(13.0, 18.6, 1.9, 0.75), (13.0, 17.5, 1.3, 0.75), (12.6, 16.5, 1.1, 0.75),
            (12.5, 15.5, 1.1, 1.2), (13.0, 14.5, 1.2, 0.75), (13.6, 13.5, 1.3, 0.75),
            (14.0, 12.5, 1.5, 0.8), (13.5, 11.5, 1.7, 1.25), (13.3, 10.5, 2.0, 0.75),
            (12.4, 9.5, 2.2, 0.75), (11.6, 9.7, 2.1, 0.7), (11.4, 10.5, 1.8, 0.45)]
    first = len(bm.faces)
    lib.tube(bm, [((E(c, r)[0], E(c, r)[1], z / 12), w / 12) for c, r, z, w in path], sides=6,
             mat_index=DARK)


    # The small pink bead on the stalk (col 12, rows 14-15): a 2 px ball sitting on it.
    first = lib.blob(bm, (E(12.5, 15.0)[0], E(12.5, 15.0)[1], 1.9 / 12), (1.0 / 12, 1.0 / 12, 0.9 / 12),
                     segments=8, rings=5, mat_index=BEAD)

    return lib.to_object(NAME, bm, mats.list, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)


if __name__ == "__main__":
    main()
