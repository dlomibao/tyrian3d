"""Clamshell reactor (newsha.shp, assembly of 4 pieces): a 3D version of its sprites.

Seen in episode 2 (level 10) and 4. Four 2x2 ground enemies side by side make one 48x56 px
structure (sprite.json `assemblyLayout`): a grey-blue half dome (newsha-229 above newsha-267)
with a raised double rim down its flat right side, two dark ports and curved panel ribs, three
grey pins clamping it shut, and a glowing orange core in the gap (newsha-231 above newsha-269).
The core's four frames narrow it from 11 px to a thin red line as the shell closes, so each of
those two pieces gets four models: <piece>, <piece>-f2, -f3 and -f4, one per frame. The grey
half (229, 267) has one frame each.

The whole structure is built in assembly coordinates (one copy per core width) and cut into the
pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsha-229.py [-- --preview out.png]
(the preview is the whole structure; each exported model also gets <model>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b087 as lib  # noqa: E402

NAME = "assembly-newsha-229"
ROOT = common.repo_root(__file__)
PIECES = ["newsha-229", "newsha-231", "newsha-267", "newsha-269"]
# Assembly pixel (0, 0) is the top-left corner of newsha-229 (screen cx 46 - 12, cy 61 - 14); the
# assembly block is 48 x 56 px and its centre (screen 58, 75) is the Blender origin.
CX0, CY0 = 58, 75
CORE_W = [11, 8, 5, 0]  # visible core width (px) in each of the four frames
CORE_FRAMES = {"newsha-231": [231, 233, 235, 237], "newsha-269": [269, 271, 273, 275]}

H = 0.7  # shell height at its rim (units)
HC = 0.6  # core height against the shell


def X(a):
    """Assembly pixel edge column to Blender X."""
    return (a - 24) / 12


def Y(r):
    """Assembly pixel edge row to Blender Y (sprite up is +Y)."""
    return (28 - r) / 12


def A(x):
    return x * 12 + 24


def R(y):
    return 28 - y * 12


# Left edge of the shell's leftmost pixel in each assembly row (rows 6-49).
LEFT = {6: 15, 7: 13, 8: 11, 9: 10, 10: 9, 11: 8, 12: 7, 13: 6, 14: 5, 15: 5, 16: 4, 17: 4, 18: 3,
        19: 3, 20: 2, 21: 2, 22: 2, 23: 1, 24: 1, 25: 1, 26: 1, 27: 1, 28: 1, 29: 1, 30: 1, 31: 1,
        32: 1, 33: 2, 34: 2, 35: 2, 36: 3, 37: 3, 38: 4, 39: 4, 40: 5, 41: 5, 42: 6, 43: 7, 44: 8,
        45: 9, 46: 10, 47: 11, 48: 13, 49: 15}
BAND = 15.0  # the rim band starts at column 15
# The same, averaged over 5 rows so the contour is a smooth curve rather than pixel steps.
SMOOTH_LEFT = [(k + 0.5, sum(LEFT[min(max(k + d, 6), 49)] for d in (-2, -1, 0, 1, 2)) / 5) for k in sorted(LEFT)]


def left_edge(r):
    """The shell's left boundary at (fractional) row r, through the rows' midpoints."""
    pts = [(6.0, 16.0)] + SMOOTH_LEFT + [(50.0, 16.0)]
    for (r0, c0), (r1, c1) in zip(pts, pts[1:]):
        if r0 <= r <= r1:
            return c0 + (c1 - c0) * (r - r0) / (r1 - r0)
    return 16.0


def right_edge(r):
    """The shell's flat side: column 23, stepping in to 21 for the rim's rounded top and bottom."""
    if r <= 7.6 or r >= 48.4:
        return 21.0
    if r < 8.4:
        return 21.0 + 2.0 * (r - 7.6) / 0.8
    if r > 47.6:
        return 23.0 - 2.0 * (r - 47.6) / 0.8
    return 23.0


# Rim band profile across the band (fraction of its full 15-23 width) -> relative height.
BAND_XS = [15.0, 16.0, 17.0, 17.9, 18.5, 19.1, 20.0, 21.0, 22.0, 23.0]
BAND_H = [1.0, 1.0, 1.0, 0.97, 0.92, 0.97, 1.0, 0.98, 0.92, 0.84]


def shell_z(a, r):
    """Shell height at assembly pixel point (a, r)."""
    g = max(0.0, 1 - ((r - 28) / 22) ** 2) ** 0.25
    lft = min(left_edge(r), BAND - 0.6)
    if a < BAND:
        t = max(0.0, min(1.0, (a - lft) / (BAND - lft)))
        h = math.sqrt(max(0.0, 1 - (1 - t) ** 2))
    else:
        s = (a - BAND) / (right_edge(r) - BAND) * 8 + BAND
        h = 1.0
        for (x0, h0), (x1, h1) in zip(zip(BAND_XS, BAND_H), zip(BAND_XS[1:], BAND_H[1:])):
            if x0 <= s <= x1:
                h = h0 + (h1 - h0) * (s - x0) / (x1 - x0)
    return H * g * h


def merged_sprite():
    data = common.load_sprite(ROOT, "newsha-229")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


CORE_IDX = [117, 119, 121, 123, 125, 127]
CORE_EMIT = [1.5, 2.0, 2.5, 3.0, 4.0, 5.0]


def core_index(v):
    """Quantise a core pixel's palette index to one of CORE_IDX (grey pin pixels count as 121)."""
    if v < 112:
        return 121
    for idx in CORE_IDX:
        if v <= idx:
            return idx
    return 127


def build(sprite, k, pixels):
    """The whole structure with the core of frame k. `pixels(a, r)` gives that frame's palette
    index at an assembly pixel of the core pieces (or -1)."""
    coll = common.reset_collection(f"{NAME}_{k}")
    tag = "nsha229"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(104, metallic=0.55, roughness=0.4),  # 0 shell
        pal(108, metallic=0.65, roughness=0.3),  # 1 rim line
        pal(102, metallic=0.5, roughness=0.5),  # 2 groove down the band
        pal(103, metallic=0.55, roughness=0.45),  # 3 inner face of the rim
        pal(98, metallic=0.7, roughness=0.15),  # 4 dark ports
        pal(107, metallic=0.65, roughness=0.3),  # 5 panel ribs
        pal(10, metallic=0.75, roughness=0.3),  # 6 grey pins
        pal(7, metallic=0.6, roughness=0.45),  # 7 pin brackets
        pal(116, emission_strength=1.5),  # 8 red seam
        pal(109, metallic=0.65, roughness=0.3),  # 9 lit upper band
    ] + [pal(i, emission_strength=e) for i, e in zip(CORE_IDX, CORE_EMIT)]  # 10.. core glow
    SHELL, RIM, GROOVE, INNER, PORT, RIB, PIN, BRACKET, SEAM, LIT = range(10)
    CORE = 10
    bm = bmesh.new()

    # ---- the grey half dome ----
    ys = [6.0, 6.4] + [r + 0.5 for r in range(7, 49)] + [49.6, 50.0]
    left_ts = [0.0, 0.12, 0.3, 0.5, 0.7, 0.87]

    def xs_of(y):
        r = R(y)
        lft = min(left_edge(r), BAND - 0.6)
        rgt = right_edge(r)
        cols = [lft + (BAND - lft) * t for t in left_ts]
        cols += [BAND + (c - BAND) * (rgt - BAND) / 8 for c in BAND_XS]
        return [X(c) for c in cols]

    def z_of(x, y):
        r = R(y)
        if r <= 6.01 or r >= 49.99:
            return 0.0
        return shell_z(A(x), r)

    def mat_of(x, y):
        a, r = A(x), R(y)
        s = (a - BAND) / (right_edge(r) - BAND) * 8 + BAND
        if a < BAND:
            return SHELL
        if 19.1 < s < 21.0:
            return RIM  # the rim line down the whole flat side
        if s > 21.0:
            return INNER
        if r < 25.5:  # the lit upper part of the band, split by a groove
            return GROOVE if s > 17.9 else LIT
        return SHELL

    lib.height_solid(bm, [Y(r) for r in ys], xs_of, z_of, mat_of, smooth=True, wall_mat=INNER)

    def on_shell(a, r, lift=0.0):
        return (X(a), Y(r), shell_z(a, r) + lift)

    # Two dark ports in the upper shell (columns 10-14, rows 8-18).
    for a, r, rx, ry in ((12.3, 10.6, 2.3, 2.4), (11.4, 15.8, 2.4, 2.8)):
        z = shell_z(a, r)
        lib.ellipsoid(bm, (X(a), Y(r), z - 0.02), rx / 12, ry / 12, 0.07, mat=PORT, segments=12, rings=6)

    # Curved panel ribs: down from the ports, round the lower-left, and along the bottom.
    ribs = [
        [(11.6, 18.4), (12.8, 19.2), (13.5, 21.0), (13.6, 24.0), (13.4, 26.5)],
        [(4.4, 23.5), (5.5, 25.5), (7.0, 27.8), (8.8, 29.6), (10.8, 31.0), (12.6, 31.6)],
        [(8.4, 36.6), (9.8, 38.6), (11.6, 40.4), (13.8, 41.8), (16.4, 42.8), (19.0, 43.6), (20.8, 44.4)],
    ]
    for rib in ribs:
        pts = []
        for (a0, r0), (a1, r1) in zip(rib, rib[1:]):
            for t in (0.0, 0.5):
                a, r = a0 + (a1 - a0) * t, r0 + (r1 - r0) * t
                pts.append(on_shell(a, r, 0.005))
        pts.append(on_shell(*rib[-1], 0.005))
        lib.polyline_tube(bm, pts, 0.9 / 12, sides=6, mat=RIB)

    # Red seam along the flat side (columns 23-24, rows 9-46).
    lib.box(bm, X(22.9), Y(47.0), X(25.0), Y(9.0), 0.0, 0.42, mat=SEAM)

    # ---- the glowing core (frame k) ----
    w = CORE_W[k]
    if w:
        x0 = 24.0
        cols = [x0 + c for c in range(w)] + [x0 + w - 0.35, x0 + w]
        rows = [9.0, 9.5] + [r + 0.5 for r in range(10, 46)] + [46.5, 47.0]

        def cz(x, y):
            a, r = A(x), R(y)
            gy = max(0.0, 1 - ((r - 28) / 19.2) ** 2) ** 0.3
            return HC * gy * math.sqrt(max(0.0, 1 - ((a - x0) / w) ** 2))

        def cmat(x, y):
            a, r = A(x), R(y)
            # The frame's glow, blurred over 3x3 pixels so it reads as swirls, not pixels.
            vals = [core_index(v) for v in (pixels(int(a) + i, int(r) + j) for i in (-1, 0, 1) for j in (-1, 0, 1))
                    if v >= 0]
            v = sum(vals) / len(vals) if vals else 119
            return CORE + min(range(len(CORE_IDX)), key=lambda n: abs(CORE_IDX[n] - v))

        lib.height_solid(bm, [Y(r) for r in rows], lambda y: [X(c) for c in cols], cz, cmat, smooth=True,
                         wall_mat=CORE)

    # ---- three grey pins clamping the shell to the core (columns 22-26) ----
    for r, rad in ((12.5, 2.5), (27.5, 3.3), (42.5, 2.5)):
        lib.polyline_tube(bm, [(X(21.6), Y(r), 0.5), (X(26.0), Y(r), 0.5)], rad / 12, sides=10, mat=PIN)
        lib.box(bm, X(22.6), Y(r + rad * 0.6), X(25.4), Y(r - rad * 0.6), 0.0, 0.42, mat=BRACKET)

    return lib.to_object(f"{NAME}_{k}", bm, mats, coll)


def core_pixels(k):
    """Frame k's palette index at assembly pixel (a, r) from newsha-231 (rows 0-27) and
    newsha-269 (rows 28-55), both in columns 24-47."""
    top = common.load_sprite(ROOT, "newsha-231")["frames"][k]["pixels"]
    bottom = common.load_sprite(ROOT, "newsha-269")["frames"][k]["pixels"]

    def get(a, r):
        c = a - 24
        if not 0 <= c < 24 or not 0 <= r < 56:
            return -1
        return top[r][c] if r < 28 else bottom[r - 28][c]
    return get


def composite_png(layout, frames, out):
    """The whole structure's sprite as one image (each piece's given frame), padded to 48x56."""
    import numpy as np
    img = np.zeros((56, 48, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(ROOT, name)
        frame = data["frames"][frames.get(name, 0)]
        x0, y0 = cx + 24 - 12, cy + 28 - 14
        for r, prow in enumerate(frame["pixels"]):
            for c, v in enumerate(prow):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 48, 56, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def model_name(piece, k):
    return piece if k == 0 else f"{piece}-f{k + 1}"


def main():
    sprite = merged_sprite()
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    exported = []  # (model, object, piece, frame index)
    wholes = []
    for k in range(4):
        obj = build(sprite, k, core_pixels(k))
        wholes.append(obj)
        cut = common.split_assembly(obj, [(model_name(n, k), cx, cy) for n, cx, cy in layout])
        for piece in PIECES:
            name = model_name(piece, k)
            if piece in CORE_FRAMES:
                sprites = lib.frames_subset(common.load_sprite(ROOT, piece), [CORE_FRAMES[piece][k]])
            elif k == 0:
                sprites = common.load_sprite(ROOT, piece)["sprites"]
            else:
                continue
            common.export_sprite_model(ROOT, [cut[name]], f"enemies/{name}", sprites)
            exported.append((name, cut[name], piece, k))
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        for k in (0, 3):
            ref = composite_png(layout, {"newsha-231": k, "newsha-269": k}, tmp / f"assembly{k}.png")
            path = out if k == 0 else out.with_name(f"{out.stem}-f{k + 1}.png")
            common.render_preview([wholes[k]], str(path), ref, size=4, view_px=480)
        for name, obj, piece, k in exported:
            data = common.load_sprite(ROOT, piece)
            img = ROOT / "reference" / "models" / piece / data["frames"][k]["image"]
            common.render_preview([obj], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
