"""Grey hull with a fire hatch (newsha.shp, assembly of 4 pieces): a 3D version of its sprites.

A ground structure seen in episode 2 (level 2.10) and episode 4, next to the "WARNING MISSILE
SHIPS!!" sign (newsha-49 and newsha-51, which are separate models). Four 2x2 enemies make one
48x56 px object (sprite.json `assemblyLayout`):

- newsha-9 and newsha-47 (one frame each): the right half of a big grey-blue dome, a D shape seen
  from above with its flat side on the left. Two light ribs run down its crown next to that side,
  a dark visor with two small lights sits on its upper slope and curved plating seams sweep round
  its lower half.
- newsha-1 and newsha-39 (four frames each): along the dome's flat side, a glowing red slit held
  by three grey brackets, out of which a slab of fire slides to the left and back (11, 8, 5 and
  0 px wide). The frames change the fire's shape, so each frame gets its own model: newsha-1
  (frame 1), newsha-1-f2 (3), newsha-1-f3 (5), newsha-1-f4 (7), and likewise newsha-39 (39) to
  newsha-39-f4 (45).

The whole object is built once per fire width in assembly coordinates, then cut into the pieces
with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsha-1.py [-- --preview out.png]
(the preview is the whole object; each piece model also gets <model>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b084 as lib  # noqa: E402

NAME = "assembly-newsha-1"
ROOT = common.repo_root(__file__)
PIECES = ["newsha-1", "newsha-9", "newsha-39", "newsha-47"]
ANIMATED = ["newsha-1", "newsha-39"]  # four frames each, one per fire width
STATIC = ["newsha-9", "newsha-47"]
# Assembly pixel (0, 0) is the top-left corner of newsha-1 (screen cx 209 - 12, cy 11 - 14); the
# object is 48 x 56 px and its centre (screen 221, 25) is the Blender origin.
CX0, CY0 = 221, 25
PX = 1 / 12
# Left edge of the fire slab for each frame (pixel edge; None = closed, only the slit shows).
FIRE_LEFT = [13, 16, 19, None]


def XE(e):
    """Assembly pixel edge (column) to Blender X."""
    return (e - 24) * PX


def YE(e):
    """Assembly pixel edge (row) to Blender Y: sprite up is +Y."""
    return (28 - e) * PX


# The dome: a superellipsoid centred on edge (27, 28), reaching edge 47 on the right, 25 on the
# left (a short rounded shoulder down to the slit) and rows 6..50.
DC, DR = 27.0, 28.0
RXR, RXL, RY = 20.0, 2.0, 22.0
H = 0.6
N_XY, N_Z = 2.1, 2.2


def dome_height(x, y):
    """Height of the dome surface above Blender (x, y), 0 outside it."""
    c, r = x / PX + 24, 28 - y / PX
    dx = (c - DC) / (RXR if c > DC else RXL)
    dy = (r - DR) / RY
    rho = (abs(dx) ** N_XY + abs(dy) ** N_XY) ** (1 / N_XY)
    if rho >= 1:
        return 0.0
    return H * (1 - rho ** N_Z) ** (1 / N_Z)


def dome_normal(x, y):
    e = 0.004
    gx = (dome_height(x + e, y) - dome_height(x - e, y)) / (2 * e)
    gy = (dome_height(x, y + e) - dome_height(x, y - e)) / (2 * e)
    return Vector((-gx, -gy, 1)).normalized()


def on_dome(c, r, lift=0.0):
    """(x, y, z) on the dome surface at pixel edge (c, r), raised by `lift`."""
    x, y = XE(c), YE(r)
    return x, y, dome_height(x, y) + lift


def dome(bm, mat):
    """The dome as rings of a superellipsoid, from the ground up to its crown."""
    seg, rings = 36, 9
    def sgnpow(v, p):
        return math.copysign(abs(v) ** p, v)
    grid = []
    for j in range(rings):
        t = (math.pi / 2) * j / rings
        rho = sgnpow(math.cos(t), 2 / N_Z)
        z = H * sgnpow(math.sin(t), 2 / N_Z)
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            ca, sa = math.cos(a), math.sin(a)
            dx = sgnpow(ca, 2 / N_XY) * rho * (RXR if ca > 0 else RXL)
            dy = sgnpow(sa, 2 / N_XY) * rho * RY
            ring.append(bm.verts.new((XE(DC + dx), YE(DR - dy), z)))
        grid.append(ring)
    top = bm.verts.new((XE(DC), YE(DR), H))
    faces = []
    for r0, r1 in zip(grid, grid[1:]):
        for i in range(seg):
            k = (i + 1) % seg
            faces.append(bm.faces.new((r0[i], r0[k], r1[k], r1[i])))
    for i in range(seg):
        faces.append(bm.faces.new((grid[-1][i], grid[-1][(i + 1) % seg], top)))
    faces.append(bm.faces.new(list(reversed(grid[0]))))
    for f in faces:
        f.material_index = mat
        f.smooth = True


def surface_tube(bm, pts, half_w, half_h, mat, lift=0.0):
    """A rib lying on the dome along pixel-edge points (c, r), tapered shut at both ends."""
    path = []
    for i, p in enumerate(pts):
        c, r = p[:2]
        w = p[2] if len(p) > 2 else half_w
        end = i in (0, len(pts) - 1)
        x, y, z = on_dome(c, r, lift)
        path.append((x, y, z, 0.0 if end else w * PX, 0.0 if end else half_h))
    lib.tube(bm, path, sides=6, mat=mat)


def box(bm, c0, r0, c1, r1, z0, z1, mat):
    """A block over pixel edges c0..c1, r0..r1."""
    lib.prism(bm, [(XE(c0), YE(r1)), (XE(c1), YE(r1)), (XE(c1), YE(r0)), (XE(c0), YE(r0))], z0, z1, mat=mat)


def build(sprite, frame):
    """The whole object with the fire slab of `frame` (0-3)."""
    coll = common.reset_collection(f"{NAME}-f{frame + 1}")
    tag = "nsha1"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(106, metallic=0.35, roughness=0.4),  # 0 grey-blue hull
        pal(111, metallic=0.4, roughness=0.3),  # 1 bright ribs on the crown
        pal(107, metallic=0.4, roughness=0.35),  # 2 lighter seams
        pal(100, metallic=0.6, roughness=0.12),  # 3 dark visor
        pal(110, emission_strength=2.5),  # 4 visor lights
        pal(119, emission_strength=3.0),  # 5 red glowing slit
        pal(8, metallic=0.6, roughness=0.4),  # 6 grey brackets
        pal(12, metallic=0.7, roughness=0.3),  # 7 bracket tops
        pal(120, emission_strength=2.0),  # 8 fire slab body
        pal(123, emission_strength=3.0),  # 9 fire slab top
        pal(126, emission_strength=5.0),  # 10 hot streak
        pal(127, emission_strength=6.0),  # 11 white-hot spots
    ]
    mats.append(pal(109, metallic=0.4, roughness=0.3))  # 12 silver band along the crown
    HULL, RIB, SEAM, VISOR, LIGHT, SLIT, BRACKET, BTOP, FIRE, FIRETOP, STREAK, HOT, BAND = range(13)
    bm = bmesh.new()

    # ---- the dome (newsha-9 and newsha-47) ----
    dome(bm, HULL)
    # A silver band along the crown (columns 26-32, narrowing to 26-29 on the lower half) with two
    # bright ribs on it, over columns 27-28 and column 30.
    surface_tube(bm, [(30.0, 6.3), (30.0, 7.5, 2.5), (29.8, 9.5, 3.3), (29.8, 18, 3.3), (29.8, 27, 3.3),
                      (28.4, 31, 1.9), (28.3, 40, 1.7), (28.2, 46, 1.5), (28.2, 48.5, 1.0), (28.2, 49.6)],
                 0, 0.035, BAND, lift=0.008)
    surface_tube(bm, [(28.0, 6.6), (28.0, 8.5), (28.0, 14), (28.0, 22), (28.0, 30), (28.0, 38),
                      (28.0, 44), (28.0, 46.5)], 0.9, 0.03, RIB, lift=0.03)
    surface_tube(bm, [(30.5, 7.6), (30.5, 9.0), (30.5, 16), (30.5, 21), (30.5, 24.5)], 0.55, 0.025, RIB, lift=0.03)
    # The dark visor on the upper slope (columns 33-40, rows 7-17) and its two small lights.
    for c, r, rx, ry in ((35.6, 12.3, 2.6, 5.0), (38.2, 16.0, 2.4, 2.4)):
        x, y, z = on_dome(c, r)
        lib.ellipsoid(bm, (x, y, z - 0.012), (rx * PX, ry * PX, 0.035), normal=dome_normal(x, y),
                      segments=14, rings=7, mat=VISOR)
    for c, r in ((35.5, 9.5), (35.5, 14.5)):
        x, y, z = on_dome(c, r)
        lib.ellipsoid(bm, (x, y, z + 0.02), (0.7 * PX, 0.7 * PX, 0.022), normal=dome_normal(x, y),
                      segments=8, rings=4, mat=LIGHT)
    # Plating seams: a short line under the visor and two arcs round the lower half.
    surface_tube(bm, [(34.5, 18.0), (34.5, 19.0), (34.6, 23.0), (34.8, 26.8)], 0.6, 0.02, SEAM)
    surface_tube(bm, [(45.0, 20.5), (44.5, 21.5), (42.5, 26.0), (40.5, 29.5), (37.5, 31.4), (34.0, 32.0),
                      (33.0, 32.0)], 0.6, 0.02, SEAM)
    surface_tube(bm, [(39.0, 39.0), (38.0, 39.6), (34.0, 41.6), (30.0, 43.0), (27.5, 44.0), (26.5, 44.3)],
                 0.7, 0.02, SEAM)

    # ---- along the flat side (newsha-1 and newsha-39) ----
    # The glowing slit (columns 23-24, rows 9-46) and the three grey brackets over it.
    box(bm, 23.0, 9.0, 25.4, 47.0, 0.0, 0.26, SLIT)
    for r0, r1 in ((10, 15), (24, 31), (40, 45)):
        box(bm, 22.0, r0, 25.6, r1, 0.0, 0.34, BRACKET)
        box(bm, 22.2, r0 + 0.2, 25.4, r0 + (r1 - r0) * 0.6, 0.34, 0.38, BTOP)

    # The fire slab sliding out to the left (rows 9-46), if the frame shows it.
    left = FIRE_LEFT[frame]
    if left is not None:
        w = 23.0 - left
        outline = [(left, 10.0), (left + 1, 9.0), (23.0, 9.0), (23.0, 47.0), (left + 2, 47.0), (left, 45.5)]
        lib.prism(bm, [(XE(c), YE(r)) for c, r in reversed(outline)], 0.0, 0.14, mat=FIRE)
        mid = XE(left + w / 2 + 0.2)
        hw = (w / 2 - 0.5) * PX
        lib.tube(bm, [(mid, YE(9.6), 0.13, 0, 0), (mid, YE(10.6), 0.13, hw * 0.8, 0.07),
                      (mid, YE(12.0), 0.13, hw, 0.09), (mid, YE(43.0), 0.13, hw, 0.09),
                      (mid, YE(44.8), 0.13, hw * 0.8, 0.07), (mid, YE(45.8), 0.13, 0, 0)], sides=10, mat=FIRETOP)
        # The white-hot streak across it (row 19) and the hot spots.
        lib.tube(bm, [(XE(left + 0.8), YE(19.5), 0.2, 0, 0), (XE(left + 1.6), YE(19.5), 0.2, 0.6 * PX, 0.03),
                      (XE(22.4), YE(19.5), 0.2, 0.6 * PX, 0.03), (XE(23.2), YE(19.5), 0.2, 0, 0)],
                 sides=6, mat=STREAK)
        spots = [(left + 0.55 * w + 0.5, 33.0, min(1.8, w / 2 - 0.6), 2.4)]
        if frame == 0:
            spots.append((18.0, 14.0, 1.5, 1.4))
        for c, r, rx, ry in spots:
            lib.ellipsoid(bm, (XE(c), YE(r), 0.2), (rx * PX, ry * PX, 0.035), segments=10, rings=5, mat=HOT)

    return lib.to_object(f"{NAME}-f{frame + 1}", bm, mats, coll)


def merged_sprite():
    """newsha-1's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsha-1")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def model_name(piece, frame):
    return piece if frame == 0 else f"{piece}-f{frame + 1}"


def main():
    sprite = merged_sprite()
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    data = {name: common.load_sprite(ROOT, name) for name in PIECES}
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    for frame in range(4):
        whole = build(sprite, frame)
        pieces = common.split_assembly(whole, layout)
        names = ANIMATED + (STATIC if frame == 0 else [])
        for name in names:
            model = model_name(name, frame) if name in ANIMATED else name
            obj = pieces[name]
            obj.name = model
            sprites = data[name]["sprites"]
            if name in ANIMATED:
                sprites = [{**s, "frames": [s["frames"][frame]]} for s in sprites]
            common.export_sprite_model(ROOT, [obj], f"enemies/{model}", sprites)
            if preview:
                img = ROOT / "reference" / "models" / name / data[name]["frames"][frame if name in ANIMATED else 0]["image"]
                common.render_preview([obj], str(preview.parent / f"{model}.png"), img, size=2)
        if preview:
            import tempfile
            ref = lib.composite_png(ROOT, [("newsha-1", 0, 0), ("newsha-9", 24, 0), ("newsha-39", 0, 28),
                                           ("newsha-47", 24, 28)], Path(tempfile.mkdtemp()) / "assembly.png",
                                    48, 56, frame_of={n: frame for n in ANIMATED})
            out = preview if frame == 0 else preview.parent / f"{preview.stem}-f{frame + 1}.png"
            common.render_preview([whole], str(out), ref, size=(48, 56), view_px=480)


if __name__ == "__main__":
    main()
