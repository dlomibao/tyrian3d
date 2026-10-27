"""Blue pipe with an eye (newshs.shp, assembly of newshs-1, -7, -115 and -3): a 3D version of
its sprites.

Seen in levels 1.23 and 3.2. Five 2x2 ground enemies side by side make one 120 x 20 px glossy
dark-blue pipe lying across the screen (sprite.json `assemblyLayout`): newshs-1 is its left end,
newshs-3 its right end, newshs-7 a plain stretch (used twice) and newshs-115 a joint wrapped in
gimbal hoops with a glowing red seam along its crest and an eye that opens: two red bulbs push
out of sockets above and below the seam. The pipe has a lip along its upper edge, a pale crest
line down its top that glints where the pieces meet, and bevelled ends.

The pipe is built whole in assembly coordinates (the layout with the eye fourth, as at the
bottom of the arena) and cut into its pieces with common.split_assembly. The eye's frames change
shape, so it gets three models, each cut from its own build of the pipe: newshs-115 (frames 115
and 117, closed: dark sockets), newshs-115-f2 (119, 121: bulbs half out) and newshs-115-f3 (123:
bulbs fully out and bright). Within a model the eye still animates: the sockets are dark blue like
the pipe on 115 and turn dark red on 117, and the half-out bulbs brighten on 121, where a small
shine lights on each (palette_material frames=, frame_part).

Run: blender --background --python assets/blender/enemies/assembly-newshs-7.py [-- --preview out.png]
(the preview is the whole pipe; each piece also gets <piece>.png next to it).
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b080 as L  # noqa: E402
import common  # noqa: E402

NAME = "assembly-newshs-7"
ROOT = common.repo_root(__file__)
PIECES = ["newshs-1", "newshs-7", "newshs-115", "newshs-3"]
# The bottom pipe of the arena: newshs-1, -7, -7, -115, -3 at screen cx 128 ... 224, cy 157.
# Its centre (screen 176, 157) is the Blender origin; assembly column a = screen x - 116, so the
# pipe's columns are 0-119 and rows are the pieces' own rows 0-27.
CX0, CY0 = 176, 157
LAYOUT = [("newshs-1", 128, 157), ("newshs-7", 152, 157), ("newshs-115", 200, 157), ("newshs-3", 224, 157)]
EYE = 72 + 11.5  # the eye piece's centre column
g = L.Grid(120, 28)
U = L.U

H = 0.29  # half height of the pipe (its centre is at z = H; it lies on the ground)
YC = g.y(14.5)  # the pipe's axis (rows 5-24)
R = 10 * U  # half width
# eye frames per variant
VARIANTS = [("newshs-115", [115, 117]), ("newshs-115-f2", [119, 121]), ("newshs-115-f3", [123])]
SOCKET_FRAMES = (49, {117: 65})  # sockets: the pipe's dark blue on 115, dark red on 117
BULB_FRAMES = (68, {121: 70})  # half-out bulbs: brighter on 121


def profile(a):
    """(top edge row, bottom edge row, height scale) of the pipe at column edge a: bevelled ends,
    and a slight swell round the eye joint."""
    left = [(-0.5, 7.6, 22.5, 0.6), (1.5, 6.4, 22.6, 0.75), (3.5, 5.5, 23.4, 0.88), (6.5, 4.8, 24.1, 0.97),
            (8.5, 4.5, 24.5, 1.0)]
    right = [(110.5, 4.5, 24.5, 1.0), (112.5, 4.7, 24.1, 0.97), (114.5, 5.3, 23.3, 0.9),
             (116.5, 5.9, 22.4, 0.8), (119.5, 7.6, 21.6, 0.6)]
    pts = left + right
    for (a0, t0, b0, s0), (a1, t1, b1, s1) in zip(pts, pts[1:]):
        if a0 <= a <= a1:
            f = (a - a0) / (a1 - a0)
            t, b, s = t0 + (t1 - t0) * f, b0 + (b1 - b0) * f, s0 + (s1 - s0) * f
            break
    else:
        t, b, s = 4.5, 24.5, 1.0
    d = abs(a - EYE)
    if d < 11:
        s *= 1.0 + 0.1 * (0.5 + 0.5 * math.cos(math.pi * d / 11))
    return t, b, s


def surf_z(a, r):
    """Height of the pipe's top surface over column a, row r."""
    t, b, s = profile(a)
    yc, half = (t + b) / 2, (b - t) / 2
    q = min(1.0, abs(r - yc) / half)
    return H + H * s * math.sqrt(1 - q * q)


def surf_strip(bm, a0, a1, r, half_px, lift, mat, steps=None):
    """A thin rounded strip lying on the pipe along row r from column a0 to a1."""
    steps = steps or max(2, int(abs(a1 - a0) / 3))
    path = []
    for k in range(steps + 1):
        a = a0 + (a1 - a0) * k / steps
        path.append((g.x(a), g.y(r), surf_z(a, r) + lift, half_px * U, lift + 0.01))
    L.sweep(bm, path, sides=6, mat=mat)


def hoop(bm, a_half, mat, lift=0.012, rad=0.65):
    """A gimbal hoop round the eye joint: two arcs on the pipe whose top view is an ellipse of half
    width a_half px through the pipe's upper and lower edges."""
    for side in (-1, 1):
        path = []
        n = 12
        for k in range(n + 1):
            t = -math.pi / 2 * 0.92 + math.pi * 0.92 * k / n
            r = 14.5 - 9.0 * math.sin(t)
            a = EYE + side * a_half * math.cos(t)
            path.append((g.x(a), g.y(r), surf_z(a, r) + lift, rad * U, rad * U * 0.9))
        L.sweep(bm, path, sides=6, mat=mat)


def bump(bm, a, r, rx, ry, h, mat, sink=0.03):
    """A dome sitting on the pipe at column a, row r (radii in px, height in units)."""
    z = surf_z(a, r)
    L.ellipsoid(bm, (g.x(a), g.y(r), z - sink), (rx * U, ry * U, h + sink), mat=mat, segments=14, rings=7)


def build(colors, variant, coll_name):
    coll = common.reset_collection(coll_name)
    m = L.Mats("nshs7", colors)
    PIPE = m(52, metallic=0.55, roughness=0.25)
    LIP = m(57, metallic=0.6, roughness=0.25)
    EDGE = m(53, metallic=0.5, roughness=0.3)
    CREST = m(58, metallic=0.6, roughness=0.2)
    GLINT = m(63, metallic=0.3, roughness=0.15, emission_strength=2.5)
    HOOP = m(57, metallic=0.65, roughness=0.25)
    SEAM = m(74, metallic=0.2, roughness=0.2, emission_strength=2.5)
    SOCKET = m(64, metallic=0.2, roughness=0.6)
    BULB_DIM = m(68, metallic=0.2, roughness=0.2, emission_strength=2.0)
    BULB = m(72, metallic=0.2, roughness=0.15, emission_strength=3.5)
    SHINE = m(77, metallic=0.1, roughness=0.1, emission_strength=4.0)
    bm = bmesh.new()

    # The pipe: a loft along X with an elliptical section, lying on the ground.
    cols = [-0.5, 1.5, 3.5, 6.5, 8.5, 30, 50, 66, 70, 74, 77, 80, 83.5, 87, 90, 93, 97, 101, 108, 110.5,
            112.5, 114.5, 116.5, 119.5]
    sections = []
    for a in cols:
        t, b, s = profile(a)
        sections.append((g.x(a), g.y((t + b) / 2), (b - t) / 2 * U, H, H * s))
    L.tube_x(bm, sections, sides=24, mat=PIPE)

    # Lip along the upper edge (row 6) and a dim edge along the lower one (row 23).
    surf_strip(bm, 8.0, 112.0, 6.0, 0.6, 0.006, LIP, steps=26)
    surf_strip(bm, 4.0, 115.0, 23.2, 0.5, 0.004, EDGE, steps=26)
    # Crest line down the top (row 14), with glints where the pieces meet; red seam over the eye.
    surf_strip(bm, 2.0, 71.5, 14.5, 0.7, 0.008, CREST, steps=18)
    surf_strip(bm, 96.5, 117.5, 14.5, 0.7, 0.008, CREST, steps=6)
    for a0, a1 in ((18.0, 29.5), (42.5, 53.5), (66.5, 71.5), (96.5, 101.0)):
        surf_strip(bm, a0, a1, 14.3, 0.9, 0.014, GLINT, steps=3)
    surf_strip(bm, 72.0, 95.5, 14.8, 1.3, 0.016, SEAM, steps=10)

    # Gimbal hoops round the eye joint (the nested ellipses in the sprite).
    hoop(bm, 10.2, HOOP)
    hoop(bm, 5.6, HOOP)

    # The eye: sockets above and below the seam, and the red bulbs that push out of them.
    if variant == 0:
        SOCKET = m(SOCKET_FRAMES[0], metallic=0.2, roughness=0.6, frames=SOCKET_FRAMES[1], part="socket")
        bump(bm, EYE, 9.8, 2.0, 1.8, 0.012, SOCKET)
        bump(bm, EYE, 19.0, 3.3, 1.8, 0.012, SOCKET)
    elif variant == 1:
        BULB_DIM = m(BULB_FRAMES[0], metallic=0.2, roughness=0.2, emission_strength=2.0,
                     frames=BULB_FRAMES[1], part="bulb")
        bump(bm, EYE, 10.0, 2.9, 2.4, 0.05, BULB_DIM)
        bump(bm, EYE, 19.0, 4.3, 2.5, 0.05, BULB_DIM)
    else:
        bump(bm, EYE, 9.6, 3.1, 3.0, 0.09, BULB)
        bump(bm, EYE, 19.3, 4.6, 3.0, 0.09, BULB)
        bump(bm, EYE, 9.2, 1.0, 1.0, 0.095, SHINE, sink=0.0)
        bump(bm, EYE, 18.6, 1.3, 1.0, 0.095, SHINE, sink=0.0)

    return L.to_object(coll_name, bm, m.list, coll)


def shine_121(colors, coll_name):
    """The half-out bulbs' highlights, lit only on frame 121 (rows 9 and 18, just left of the
    eye's centre), poking through the tops of variant 1's bulbs."""
    m = L.Mats("nshs7", colors)
    SHINE = m(73, metallic=0.1, roughness=0.1, emission_strength=4.0)
    bm = bmesh.new()
    bump(bm, EYE - 0.4, 9.4, 0.9, 0.9, 0.066, SHINE, sink=0.0)  # the pipe is lower here than under the bulb
    bump(bm, EYE - 0.4, 18.4, 1.1, 0.9, 0.05, SHINE, sink=0.0)
    return L.to_object(f"{coll_name}-shine", bm, m.list, common.reset_collection(f"{coll_name}-shine"))


def merged_colors():
    colors = {}
    for name in PIECES:
        colors.update(common.load_sprite(ROOT, name)["colors"])
    return colors


def composite_png(out, eye_frame=0):
    """The whole pipe's sprite as one image, padded to the 24:28 shape render_preview expects for
    size 10 (120 x 140 px, the pipe in the middle)."""
    import numpy as np
    img = np.zeros((140, 120, 4), dtype=np.float32)
    for name, cx, cy in [("newshs-1", 128, 157), ("newshs-7", 152, 157), ("newshs-7", 176, 157),
                         ("newshs-115", 200, 157), ("newshs-3", 224, 157)]:
        data = common.load_sprite(ROOT, name)
        frame = data["frames"][eye_frame if name == "newshs-115" else 0]
        x0, y0 = cx - CX0 + 60 - 12, cy - CY0 + 70 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 120, 140, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    colors = merged_colors()
    layout = [(n, cx - CX0, cy - CY0) for n, cx, cy in LAYOUT]
    out = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    whole = build(colors, 0, NAME)
    pieces = common.split_assembly(whole, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        sprites = data["sprites"]
        if name == "newshs-115":
            sprites = [dict(s, frames=VARIANTS[0][1]) for s in sprites]
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", sprites)
    eye = common.load_sprite(ROOT, "newshs-115")
    eye_pieces = {"newshs-115": pieces["newshs-115"]}
    variant_wholes = {}
    eye_objs = {"newshs-115": [pieces["newshs-115"]]}
    _, cx, cy = next(e for e in layout if e[0] == "newshs-115")
    for v, (vname, frames) in enumerate(VARIANTS[1:], start=1):
        obj = build(colors, v, f"{NAME}-v{v}")
        variant_wholes[vname] = obj
        piece = common.split_assembly(obj, [(vname, cx, cy)])[vname]
        objs = [piece]
        if v == 1:
            shine = shine_121(colors, f"{NAME}-v{v}")
            objs.append(common.frame_part(common.split_assembly(shine, [(f"{vname}-shine-121", cx, cy)])[f"{vname}-shine-121"], [121]))
        sprites = [dict(s, frames=frames) for s in eye["sprites"]]
        common.export_sprite_model(ROOT, objs, f"enemies/{vname}", sprites)
        eye_pieces[vname] = piece
        eye_objs[vname] = objs
    if "--frames" in sys.argv:  # every frame of each eye model, beside its sprite
        fout = Path(sys.argv[sys.argv.index("--frames") + 1])
        for vname, frames in VARIANTS[:2]:
            sub = dict(eye, frames=[f for f in eye["frames"] if f["index"] in frames])
            common.render_frame_previews(eye_objs[vname], str(fout.parent / f"{vname}.png"), sub, ROOT)
    if out:
        tmp = Path(tempfile.mkdtemp())
        common.render_preview([whole], str(out), str(composite_png(tmp / "pipe.png")), size=10, view_px=640)
        full = VARIANTS[2][0]
        common.render_preview([variant_wholes[full]], str(out.with_name(f"{NAME}-open.png")),
                              str(composite_png(tmp / "pipe-open.png", eye_frame=4)), size=10, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.with_name(f"{name}.png")), str(img), size=2)
        for v, (vname, frames) in enumerate(VARIANTS[1:], start=1):
            img = ROOT / "reference" / "models" / "newshs-115" / f"frame-newshs-{frames[-1]}.png"
            common.render_preview([eye_pieces[vname]], str(out.with_name(f"{vname}.png")), str(img), size=2)


if __name__ == "__main__":
    main()
