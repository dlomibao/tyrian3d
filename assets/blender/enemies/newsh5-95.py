"""Green energy arrow (newsh5.shp frames 95, 209, 247): a 3D version of its sprite.

Seen in episode 4 (level 20). A small glowing green arrow pointing left: a faceted arrowhead
(columns 0-4) on a three-pixel shaft that runs to the right edge, with a white-hot core down its
middle. The three frames only fade its glow (bright, mid, dim green), so one model covers them;
the parts use the bright frame's palette indices and step down to the mid and dim greens on frames
209 and 247 (palette_material frames=).

Run: blender --background --python assets/blender/enemies/newsh5-95.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b029 as lib  # noqa: E402

NAME = "newsh5-95"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = lib.Grid(12, 14)


def ex(c):
    """Pixel edge (left edge of column c) to Blender X."""
    return G.X(c - 0.5)


def ey(r):
    """Pixel edge (top edge of row r) to Blender Y."""
    return G.Y(r - 0.5)


def build(sprite):
    coll = common.reset_collection(NAME)
    glow = lambda i, part, frames, **kw: common.palette_material(  # noqa: E731
        sprite, i, f"{NAME}-{part}", frames=frames, **kw)
    # Each colour fades on frame 209 (mid green) and 247 (dim green). The white core of the shaft
    # drops to the inner head's green, the head's hot cross only to the next brighter green.
    mats = [
        glow(199, "body", {209: 196, 247: 192}, metallic=0.1, roughness=0.3, emission_strength=2.5),  # 0 green body
        glow(207, "inner", {209: 204, 247: 200}, metallic=0.1, roughness=0.25, emission_strength=4.0),  # 1 bright green inner head
        glow(47, "core", {209: 204, 247: 200}, metallic=0.0, roughness=0.2, emission_strength=6.0),  # 2 white-hot shaft core
        glow(47, "hot", {209: 207, 247: 203}, metallic=0.0, roughness=0.2, emission_strength=6.0),  # 3 white-hot head centre
    ]
    BODY, INNER, CORE, HOT = range(4)
    bm = bmesh.new()
    px = 1 / 12
    yc = 6.5  # the arrow's axis (row 6's centre, as a pixel-edge row coordinate)

    # Arrowhead: a faceted bipyramid, one ridge from the tip at column 0 up to its peak at the
    # column 3/4 edge (its widest, 7 px) and down its back into the shaft's crest. Its top is
    # lofted through the sprite's colour bands, each a ring in pixel-edge (column, row, height px):
    # the green rim (199), the bright chevron (207) and the white-hot cross (47).
    def ring(tip, upper, right):
        """Tip, upper points from left to right, right point; mirrored about the axis, counter-
        clockwise from the tip."""
        lower = [(c, 2 * yc - r, z) for c, r, z in upper]
        return [tip] + lower + [right] + upper[::-1]

    rings = [
        ring((0, yc, 0.0), [(3, 3.2, 0.0), (5, 3, 0.0), (5, 5, 0.0)], (5, yc, 0.0)),  # rim, the outline
        ring((1, yc, 1.4), [(3, 4, 1.45), (4, 4, 1.45), (4, 5, 1.6)], (5, yc, 1.0)),  # bright chevron
        ring((2, yc, 2.25), [(3, 5, 2.4), (4, 5, 2.4), (4.5, 5.75, 1.95)], (5, yc, 1.55)),  # white cross
    ]
    apex_c, top, bottom = 4.0, 3.2, -2.8
    vr = [[bm.verts.new((ex(c), ey(r), z * px)) for c, r, z in rg] for rg in rings]
    up = bm.verts.new((ex(apex_c), ey(yc), top * px))
    down = bm.verts.new((ex(apex_c), ey(yc), bottom * px))
    n = len(rings[0])
    for band, mat in ((0, BODY), (1, INNER)):
        r0, r1 = vr[band], vr[band + 1]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).material_index = mat
    for i in range(n):
        j = (i + 1) % n
        # The cross's faces behind the peak (columns 4-5) are the start of the shaft's core.
        behind = min(rings[2][i][0], rings[2][j][0]) >= apex_c
        bm.faces.new((vr[2][i], vr[2][j], up)).material_index = CORE if behind else HOT
        bm.faces.new((vr[0][j], vr[0][i], down)).material_index = BODY

    # Shaft: a round beam 3 px across (rows 5-7), from inside the head to the right edge, ending
    # square with a small bevel (the sprite's shaft ends square). Its top facet is exactly 1 px
    # wide (row 6): the white-hot core as a stripe standing about 0.35 px proud of the beam's crest,
    # then the bright green cell at column 10, where the stripe ramps back down into the beam.
    R = 1.5
    # From the top, about the axis; the first two are the stripe's top edges (raised), the next
    # and the last its feet on the beam, just outside row 6 so the stripe's sides stay green.
    angles = [-19.47, 19.47, 22.5, 62, 105, 145, 180, 215, 255, 298, -22.5]
    raised = {0, 1}
    m = len(angles)
    n0 = len(bm.faces)
    # (column edge, radius scale, stripe rise in px)
    stations = [(4.5, 1.0, 0.35), (10, 1.0, 0.35), (11, 1.0, 0.0), (11.8, 1.0, 0.0), (12, 0.8, 0.0)]
    srings = []
    for c, k, rise in stations:
        ring_v = []
        for i, a in enumerate(angles):
            s, z = math.sin(math.radians(a)) * R * k, math.cos(math.radians(a)) * R * k
            if i in raised:
                z += rise
            ring_v.append(bm.verts.new((ex(c), ey(yc) + s * px, z * px)))
        srings.append(ring_v)
    stripe = []
    for si in range(len(stations) - 1):
        a, b = srings[si], srings[si + 1]
        c0 = stations[si][0]
        crest = CORE if c0 < 10 else INNER if c0 < 11 else BODY
        for k in range(m):
            j = (k + 1) % m
            f = bm.faces.new((a[k], a[j], b[j], b[k]))
            f.material_index = crest if k == 0 else BODY
            if k in (0, 1, m - 1) and c0 < 11:
                stripe.append(f)
    # Back cap: flat (a fan from its centre, so the 11-gon stays clean).
    cc = bm.verts.new((ex(stations[-1][0]), ey(yc), 0.0))
    for k in range(m):
        j = (k + 1) % m
        bm.faces.new((srings[-1][j], srings[-1][k], cc)).material_index = BODY
    lib.faces_since(bm, n0, smooth=True)
    for f in stripe:
        f.smooth = False
    bm.faces.ensure_lookup_table()
    for f in bm.faces[len(bm.faces) - m:]:
        f.smooth = False
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])
    if "--frame-previews" in sys.argv:
        common.render_frame_previews([obj], sys.argv[sys.argv.index("--frame-previews") + 1], sprite, ROOT)


if __name__ == "__main__":
    main()
