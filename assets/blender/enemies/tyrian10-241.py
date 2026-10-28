"""Beer mug (tyrian.shp#10 frame 241): a 3D version of its sprite.

Seen in episode 1 (level section 41). The sprite draws a fluted glass tankard from the side,
mouth up the screen: grey glass at the top, brown beer below a pale foam line, a dark base row,
and a grey strap handle on the right. In 3D it lies on its side in the screen plane: a round body
along Y, 13 px across and as deep (the sprite's highlight and shadow columns say a round glass).
The sprite's light and shade, its dark outline ring and its bright streaks are drawn light: the
glass, the beer, the foam line and the handle each take one mid-tone and a glossy material, and the
game's lights and outline do the rest. Only the fluted glass's pale columns over the beer (columns
8, 11 and 14) stay painted, as flat stripes. The handle is a round glass loop round a hole, centred
on the body's midplane. The near-black pixels to the right of and below the mug (indices 160 and
161) are its drop shadow: a thin dark plate under the mug, its outline the sprite's staircase
smoothed, carries them, so they also show through the handle's hole.

Run: blender --background --python assets/blender/enemies/tyrian10-241.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b021 as lib  # noqa: E402
from lib_b021 import common, ex, ey  # noqa: E402

NAME = "tyrian10-241"
U = 1 / 12  # one sprite px
CX = ex(11)  # the body's centre line: columns 5-16 (13 px with the outline)
R = 6.6 * U  # body radius: round, as deep as it is wide


def _angles():
    """The ring's vertex angles (0 = the right side, pi/2 = on top). On top, a vertex on every
    sprite column edge, so each column from above is one facet and takes its own colour (the
    sprite's pale stripes and dark grooves); underneath, where nothing sees it, fewer."""
    xs = [17.6, 17.3] + list(range(17, 4, -1)) + [4.7, 4.4]
    top = [math.acos(max(-1.0, min(1.0, (x - 11) * U / R))) for x in xs]
    bottom = [math.pi + math.pi * k / 8 for k in range(1, 8)]
    return top + bottom


ANGLES = _angles()
SIDES = len(ANGLES)
Z0 = R + 0.5 * U  # the axis's height: the mug lies on its drop-shadow plate on the ground


def ring(y, s=1.0):
    """A ring round the body at height y, scaled by s."""
    return [(CX + s * R * math.cos(a), y, s * R * math.sin(a)) for a in ANGLES]


# The drop shadow's outline (sprite column, row of pixel edges): the sprite's own staircase smoothed
# into straight runs that still take in exactly its shadow pixels (and never an empty one). Its top
# and left run under the mug and the handle.
PLATE = [(6, 8), (17, 8), (19.6, 11), (23, 11), (23, 19.6), (22.1, 20.5), (20.1, 21.5), (18.1, 23.6),
         (17.8, 24), (7.4, 24), (5.4, 22)]


def shadow_plate(bm, z0, z1, mat_index):
    """A thin plate under the mug with the smoothed outline PLATE: it shows only where the sprite
    has its drop shadow (and through the handle's hole)."""
    top = [bm.verts.new((ex(c), ey(r), z1)) for c, r in PLATE]
    bot = [bm.verts.new((ex(c), ey(r), z0)) for c, r in PLATE]
    f = bm.faces.new(top)
    f.normal_update()
    if f.normal.z < 0:
        f.normal_flip()
    f.material_index = mat_index
    n = len(PLATE)
    for i in range(n):
        j = (i + 1) % n
        w = bm.faces.new((top[i], bot[i], bot[j], top[j]))
        w.material_index = mat_index
        w.normal_update()
        mid = (top[i].co + top[j].co) / 2
        cen = sum((v.co for v in top), top[0].co * 0) / n
        if w.normal.dot(mid - cen) < 0:
            w.normal_flip()


GLASS = 10  # the glass's mid-tone (the sprite's glass rows average about index 9-10)
BEER = 22  # the beer's mid-tone seen through the glass (dark 18-21 between pale 24-31 flutes)
FOAM = 26  # the pale foam line at the top of the beer (row 12)
FLUTE = 24  # the fluted glass's pale columns over the beer (columns 8, 11 and 14)
FLUTE_COLS = (8, 11, 14)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    # Glass and the beer seen through it are one glossy surface: mid-tone colours, and the
    # game's lights make the shine and the shading (the sprite's light and dark columns, its
    # dark outline ring and its bright streaks are drawn light, not paint).
    mats = [
        pal(GLASS, metallic=0.0, roughness=0.1),  # 0 glass: the upper body, the lip and the foot
        pal(BEER, metallic=0.0, roughness=0.12),  # 1 beer through the glass, and the base end
        pal(FOAM, metallic=0.0, roughness=0.3),  # 2 foam line
        pal(2, metallic=0.0, roughness=0.6),  # 3 inside the mouth (a real recess)
        pal(FLUTE, metallic=0.0, roughness=0.12),  # 4 the flutes' pale columns over the beer
    ]
    G, B, F, IN, FL = range(5)

    def beer_band():
        out = []
        for i in range(SIDES):
            a = (ANGLES[i] + ANGLES[(i + 1) % SIDES]) / 2
            x = 11 + R / U * math.cos(a)
            out.append(FL if math.sin(a) > 0 and any(c <= x < c + 1 for c in FLUTE_COLS) else B)
        return out

    # Body from the base foot (row 21) to the mouth (rows 5-6), then in and down into the mug.
    bm = bmesh.new()
    rings = [ring(ey(22.0), 0.86), ring(ey(21.6), 0.96), ring(ey(21.0), 0.99), ring(ey(20.9)),
             ring(ey(13.0)), ring(ey(12.0)), ring(ey(6.0)),
             ring(ey(5.0), 0.95), ring(ey(5.0), 0.84), ring(ey(7.0), 0.8)]
    lib.ring_loft(bm, rings, [G, G, G, beer_band(), F, G, G, G, IN], cap_mats=(B, IN))
    body = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    lib._sharpen(body, 35)

    # The handle: a round glass loop about 2.2 px thick round a hole (columns 17-21, rows 8-19),
    # its centre line along the strap's middle (rows 9 and 18, column 20) at the body's axis
    # height, its ends buried in the body; and the drop-shadow plate under everything.
    hmats = [
        pal(GLASS, metallic=0.0, roughness=0.1),  # 0 the handle: glass, one mid-tone all round
        pal(160, metallic=0.0, roughness=0.15),  # 1 drop shadow
    ]
    bm = bmesh.new()
    path = [(15.5, 9.5), (19.5, 9.5), (20.5, 10.5), (20.5, 17.5), (19.5, 18.5), (15.5, 18.5)]
    # 1.1 px round, widened at the four 45-degree bends so the mitred joints don't pinch
    radii = [1.1 * U] + [1.1 * U / math.cos(math.pi / 8)] * 4 + [1.1 * U]
    lib.polyline_tube(bm, [(ex(c), ey(r), 0.0) for c, r in path], radii, sides=8)
    for f in bm.faces:
        f.material_index = 0
    shadow_plate(bm, -Z0, -R, 1)
    for node in hmats[1].node_tree.nodes:  # a matte shadow: no sheen from the sky
        if node.type == "BSDF_PRINCIPLED":
            for key in ("Specular IOR Level", "Specular"):
                if key in node.inputs:
                    node.inputs[key].default_value = 0.0
    handle = common.mesh_object(f"{NAME}_handle", bm, hmats, coll, smooth=True)
    lib._sharpen(handle, 50)  # a smooth loop; the plate's edges stay crisp

    from mathutils import Matrix
    for obj in (body, handle):  # lift the mug onto the ground
        obj.data.transform(Matrix.Translation((0, 0, Z0)))
    return [(NAME, [body, handle], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
