"""Red domed pod (newshv.shp frames 123, 125, 127): a 3D version of its sprite.

Seen in episode 2 (level 2.15). A round pod 19 px across, lighter in the middle and darker toward
its outline, so a dome about half as tall as it is wide that meets the ground at its full outline,
with a thin dark diamond (about 10 px corner to corner) cut into its surface as a groove; the
sprite's 1 px dark outline is the dome's outermost px. The three frames only dim the whole pod (a
pulse), so one model covers them, its colours stepping darker frame by frame. newshv-153 is the
same disc in blue (built by lib_b003.gem_disc); this one uses the reds 64-79 and its own dome.

Run: blender --background --python assets/blender/enemies/newshv-123.py [-- --preview out.png] [--frame-previews frames.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import math  # noqa: E402

import common  # noqa: E402
import lib_b003 as lib  # noqa: E402

NAME = "newshv-123"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


U = 1 / 12           # one sprite px
R = 9.35 * U         # outer radius: the sprite spans columns 3-20 and rows 5-22 with its outline
RD = 8.5 * U         # inside this the dome is pink; outside it the sprite draws its 1 px dark outline
H = 10.0 * U         # apex height above the base (a bit over half the diameter)
P, E = 2.5, 0.7      # profile z = H (1 - (r/R)^P)^E: within a few % of a hemisphere down to r = 0.75 R,
                     # but its lower side leans in a little, so the outermost px (the sprite's dark
                     # outline, r 8.5-9.35) is a ~3.4 px dark rim rather than a sphere's ~4 px
GROOVE = (4.3, 4.55, 5.45, 5.7)   # diamond groove, L1 radii in px: lip, floor, floor, lip
DEPTH = 1.0 * U
N = 32               # points per ring (a multiple of 4, so the diamond's corners are on it)


def dome_z(x, y):
    """One dome from the apex down to the full outline at z = 0 (no foot, no step)."""
    r = min(math.hypot(x, y) / R, 1.0)
    return H * max(0.0, 1.0 - r ** P) ** E


def ring(radius_of, depth=0.0):
    """N points (x, y, z) on the dome, at radius radius_of(angle); `depth` sinks them."""
    pts = []
    for i in range(N):
        a = 2 * math.pi * i / N
        r = radius_of(a)
        x, y = r * math.cos(a), r * math.sin(a)
        pts.append((x, y, dome_z(x, y) - depth))
    return pts


def diamond(s):
    """A diamond with corners on the axes, L1 radius s px."""
    return lambda a: s * U / (abs(math.cos(a)) + abs(math.sin(a)))


def blend(s, rc, t):
    """Between a diamond (L1 radius s px, t = 0) and a circle (radius rc px, t = 1)."""
    return lambda a: (1 - t) * diamond(s)(a) + t * rc * U


def band(bm, rings, mats, apex=None, bottom=None):
    """Join rings of N verts (outside in or inside out) with quads; ring k+1's band gets mats[k].
    `apex` closes the first ring to a point above, `bottom` the last to a point below."""
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    faces = []
    if apex is not None:
        c = bm.verts.new(apex)
        for i in range(N):
            faces.append((bm.faces.new((c, vs[0][i], vs[0][(i + 1) % N])), mats[0]))
        mats = mats[1:]
    for k in range(len(vs) - 1):
        for i in range(N):
            j = (i + 1) % N
            faces.append((bm.faces.new((vs[k][i], vs[k + 1][i], vs[k + 1][j], vs[k][j])), mats[k]))
    if bottom is not None:
        c = bm.verts.new(bottom)
        for i in range(N):
            faces.append((bm.faces.new((vs[-1][i], c, vs[-1][(i + 1) % N])), mats[-1]))
    for f, m in faces:
        f.material_index = m


def pod(sprite, name, offset):
    import bmesh
    coll = common.reset_collection(name)
    f1, f2 = (f["index"] for f in sprite["frames"][1:3])

    def pal(i, **kw):
        i += offset
        return common.palette_material(sprite, i, f"{name}-pulse", frames={f1: i - 2, f2: i - 4}, **kw)
    # Shades from the sprite, ring by ring from the centre (each the best match, in CIE dE, to
    # the sprite's pixels at that radius), stepping one palette index at a time so the side grades
    # smoothly: 78 at the apex, 77, 76 over the crown and the body, 75, 74, 73, 71, then the
    # outline (64) on the dome's outermost px.
    mats = [
        pal(62, metallic=0.05, roughness=0.4),   # 0 apex highlight (78)
        pal(61, metallic=0.05, roughness=0.45),  # 1 crown (77)
        pal(60, metallic=0.05, roughness=0.45),  # 2 body (76)
        pal(59, metallic=0.05, roughness=0.5),   # 3 shoulder (75)
        pal(58, metallic=0.05, roughness=0.5),   # 4 lower shoulder (74)
        pal(57, metallic=0.05, roughness=0.55),  # 5 side (73)
        pal(55, metallic=0.05, roughness=0.55),  # 6 lower side (71)
        # 7 the outline, the dome's outermost px (64 on every frame, so no pulse)
        common.palette_material(sprite, 64, name, metallic=0.1, roughness=0.6),
        pal(56, metallic=0.1, roughness=0.6),    # 8 groove (72, the diamond ring's shade)
    ]
    APEX, CROWN, BODY, SHOULDER, LOWER, SIDE, LOWSIDE, RIM, GRV = range(9)
    g0, g1, g2, g3 = GROOVE

    def crown(u):
        """Crown ring u (0 centre .. 1 the groove's inner lip): round near the apex, turning
        into the groove's diamond toward its lip, so the crown is the dome's own surface."""
        rc = g0 * 0.82
        return lambda a: u * ((1 - u) * rc * U + u * diamond(g0)(a))

    def circle(r):
        return lambda a: r * U

    # The dome, smooth, from the apex to z = 0 at the full outline. The groove's lips are separate
    # verts so its sharp walls don't bend the dome's smooth normals.
    bm = bmesh.new()
    us = (0.12, 0.27, 0.42, 0.57, 0.72, 0.86, 1.0)
    band(bm, [ring(crown(u)) for u in us], [APEX, APEX, CROWN, CROWN, BODY, BODY, BODY],
         apex=(0.0, 0.0, H))
    band(bm, [ring(diamond(g3)), ring(blend(g3, 6.0, 0.5)), ring(circle(6.0)), ring(circle(6.5)),
              ring(circle(7.0)), ring(circle(7.35)), ring(circle(7.7)), ring(circle(8.2)),
              ring(circle(8.5)), ring(circle(8.85)), ring(circle(9.15)), ring(circle(9.35))],
         [BODY, BODY, SHOULDER, SHOULDER, LOWER, LOWER, SIDE, LOWSIDE, RIM, RIM, RIM])
    # The underside: a flat disc at z = 0 (never seen from the game camera).
    rim = [(R * math.cos(2 * math.pi * i / N), R * math.sin(2 * math.pi * i / N), 0.0) for i in range(N)]
    band(bm, [rim], [RIM], bottom=(0.0, 0.0, 0.0))
    body = common.mesh_object(name, bm, mats, coll, smooth=True)

    # The groove: a 1 px deep diamond channel cut into the dome, flat shaded.
    bm = bmesh.new()
    band(bm, [ring(diamond(g0)), ring(diamond(g1), DEPTH), ring(diamond(g2), DEPTH), ring(diamond(g3))],
         [GRV] * 3)
    groove = common.mesh_object(f"{name}_groove", bm, mats, coll, smooth=False)
    return [body, groove]


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objects = pod(sprite, NAME, 16)
    common.export_sprite_model(ROOT, objects, MODEL, sprite["sprites"])
    lib.preview(objects, ROOT, NAME, sprite)
    if "--frame-previews" in sys.argv:
        common.render_frame_previews(objects, sys.argv[sys.argv.index("--frame-previews") + 1], sprite, ROOT)


if __name__ == "__main__":
    main()
