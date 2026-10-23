"""Spiral pod (newshm.shp frames 117, 119, 121): a 3D version of its sprite.

A ground enemy seen in episode 1 (levels 1.21 and 1.23) and episode 3. It is a round mauve pod
like a coiled shell seen from above: a bright inner whorl at the upper left, a dark groove that
runs down its right side and hooks left underneath, and the outer whorl wrapping round the right
and the bottom. The three frames swell it (15, 17 then 19 px across) and darken it, so each frame
gets its own model: newshm-117, newshm-117-f2 and newshm-117-f3.

Run: blender --background --python assets/blender/enemies/newshm-117.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b102 as lib  # noqa: E402

NAME = "newshm-117"
ROOT = common.repo_root(__file__)

# Per frame, in sprite pixels (column, row): the body ellipse (centre, half width, half height),
# its height in units, the inner whorl (centre, radii), the groove and outer whorl paths, and the
# palette indices (rim, body, top, inner whorl, outer whorl, groove).
FRAMES = {
    117: dict(c=(11.0, 13.5), r=(6.6, 7.3), h=0.36,
              inner=((9.6, 11.0), (3.3, 2.9)),
              groove=[(12.6, 8.2), (13.0, 10.5), (12.9, 12.8), (12.0, 14.5), (10.6, 15.2), (9.4, 14.6)],
              outer=[(14.3, 8.6), (15.4, 11.5), (15.4, 14.6), (13.6, 17.0), (10.6, 18.0), (7.6, 17.0),
                     (6.2, 14.6), (6.4, 12.5)],
              mats=(84, 87, 89, 93, 91, 85)),
    119: dict(c=(11.0, 13.5), r=(7.6, 8.3), h=0.40,
              inner=((9.2, 10.6), (3.5, 3.1)),
              groove=[(13.0, 7.2), (13.8, 9.8), (13.9, 12.4), (12.8, 14.4), (11.0, 15.2), (9.4, 14.7)],
              outer=[(15.2, 8.4), (16.5, 11.8), (16.3, 15.0), (14.3, 17.8), (10.8, 18.8), (7.4, 17.6),
                     (5.6, 14.8), (5.6, 12.6)],
              mats=(83, 86, 87, 91, 90, 83)),
    121: dict(c=(11.0, 13.5), r=(8.6, 9.3), h=0.44,
              inner=((9.0, 9.9), (3.7, 3.2)),
              groove=[(13.0, 6.4), (14.0, 9.4), (14.0, 12.2), (12.9, 14.0), (11.2, 15.2), (9.4, 14.8)],
              outer=[(15.8, 8.0), (17.2, 11.8), (16.9, 15.2), (14.6, 18.2), (10.8, 19.4), (7.0, 18.2),
                     (4.8, 15.0), (4.6, 12.4)],
              mats=(82, 85, 86, 90, 89, 82)),
}


def P(c, r):
    return lib.px(c), lib.row(r)


def build(sprite, name, f):
    coll = common.reset_collection(name)
    rim, body, top, inner, outer, groove = f["mats"]
    mats = [
        common.palette_material(sprite, rim, name, metallic=0.15, roughness=0.6),
        common.palette_material(sprite, body, name, metallic=0.2, roughness=0.5),
        common.palette_material(sprite, top, name, metallic=0.2, roughness=0.45),
        common.palette_material(sprite, inner, name, metallic=0.3, roughness=0.3),
        common.palette_material(sprite, outer, name, metallic=0.25, roughness=0.35),
        common.palette_material(sprite, groove, name, metallic=0.1, roughness=0.7),
    ]
    RIM, BODY, TOP, INNER, OUTER, GROOVE = range(6)
    bm = bmesh.new()

    cx, cy = P(*f["c"])
    dome = lib.HalfDome(cx, cy, f["r"][0] / 12, f["r"][1] / 12, f["h"])
    dome.build(bm, [TOP, TOP, TOP, BODY, BODY, BODY, RIM, RIM], segments=28)

    # Outer whorl: a fat coil round the right side and the bottom, thinning as it climbs the left.
    pts = [P(c, r) for c, r in f["outer"]]
    scale = f["r"][0] / 6.6
    lib.surface_tube(bm, dome, pts, (2.6 * scale / 12, 1.6 * scale / 12), lift=-0.5 * scale / 12, mat_index=OUTER,
                     sides=8, samples=18, taper=0.2, flat=0.6)

    # Inner whorl: the bright raised dome at the upper left.
    (ic, ir), (rx, ry) = f["inner"]
    lib.patch(bm, dome, *P(ic, ir), rx / 12, ry / 12, 0.07 * scale, angle=0.3, mat_index=INNER, sides=16, rings=4)

    # The dark groove between the whorls.
    pts = [P(c, r) for c, r in f["groove"]]
    lib.surface_tube(bm, dome, pts, 1.0 / 12 * scale, lift=0.01, mat_index=GROOVE, sides=6, samples=14,
                     taper=0.25, flat=0.35)

    return common.mesh_object(name, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    base = sprite["sprites"][0]
    for i, (index, f) in enumerate(FRAMES.items()):
        name = NAME if i == 0 else f"{NAME}-f{i + 1}"
        obj = build(sprite, name, f)
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", [dict(base, frames=[index])])
        if "--preview" in sys.argv:
            out = Path(sys.argv[sys.argv.index("--preview") + 1])
            ref = ROOT / "reference" / "models" / NAME / f"frame-newshm-{index}.png"
            common.render_preview([obj], out.with_name(f"{name}.png"), ref, size=2)


if __name__ == "__main__":
    main()
