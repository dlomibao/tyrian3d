"""Red crystal shard (newshe.shp frames 199 and 237, an assembly of 2 pieces): a 3D version of
its sprites.

Seen in episode 3 (level 3.8), on the ground. Two 2x2 enemies stacked make one 24x56 px shard
(sprite.json `assemblyLayout`; newshe-277 in the layout is a separate enemy above it, not part of
it): a long faceted crystal pointing down the screen, with a white-hot ridge down its middle, a
bright bevel on its left edge, a narrower blade split off along its right side by a slit, and a
pointed hood over the top with a bright rim along its front edge. Its lower point glows.

The whole shard is built once in assembly coordinates, then cut into the two pieces with
common.split_assembly. Neither piece is animated.

Run: blender --background --python assets/blender/enemies/assembly-newshe-237.py [-- --preview out.png]
(the preview is the whole shard; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b114 as lib  # noqa: E402

NAME = "assembly-newshe-237"
ROOT = common.repo_root(__file__)
PIECES = ["newshe-199", "newshe-237"]
# The shard is 24 x 56 px: newshe-199 (screen centre 224, 139) on top of newshe-237 (224, 167).
# Its centre (screen 224, 153) is the Blender origin.
CX0, CY0 = 224, 153


def X(u):
    """Assembly column edge coordinate (column c spans u = c .. c + 1) to Blender X."""
    return (u - 12) / 12


def Y(v):
    """Assembly row edge coordinate (row r spans v = r .. r + 1) to Blender Y: up is +Y."""
    return (28 - v) / 12


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshe237"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(64, metallic=0.2, roughness=0.8),  # 0 underside
        pal(113, metallic=0.1, roughness=0.5),  # 1 dark left facet
        pal(121, metallic=0.4, roughness=0.25),  # 2 bright bevels and the right facet
        pal(126, emission_strength=3.0),  # 3 white-hot ridge
        pal(116, metallic=0.35, roughness=0.35),  # 4 right side wall
        pal(115, metallic=0.1, roughness=0.45),  # 5 hood and blade facets
        pal(119, metallic=0.4, roughness=0.3),  # 6 blade's bright edge
        pal(123, emission_strength=1.5),  # 7 glowing lower point
    ]
    UNDER, DARK, BRIGHT, RIDGE, SIDE, HOOD, EDGE, GLOW = range(8)
    bm = bmesh.new()

    def profile(u_left, u_right, h, bevel, shoulder=0.6):
        """Cross-section of the main shard: left bevel, sloping left facet up to the ridge on
        column 12, a short right facet and a steep side wall."""
        p1 = min(u_left + bevel, 11.4)
        p4 = max(u_right - shoulder, 13.4)
        return [(X(min(u_left, p1)), 0.0), (X(p1), h * 0.5), (X(11.5), h * 0.97), (X(13.0), h),
                (X(p4), h * 0.62), (X(max(u_right, p4)), 0.0)]

    # Main shard, from under the hood to the lower point:
    # (v, left edge, right edge, ridge height, left bevel width). The bright bevel widens toward
    # the lower point, which glows.
    body = [(7.0, 4.0, 15.0, 0.42, 1.0), (30.0, 4.0, 15.0, 0.42, 1.0), (32.5, 5.0, 14.2, 0.42, 1.2),
            (36.0, 5.6, 14.0, 0.41, 1.6), (39.0, 6.3, 14.0, 0.4, 1.8), (41.5, 7.0, 14.0, 0.39, 1.8),
            (43.5, 8.0, 14.4, 0.37, 1.6), (45.0, 8.2, 16.0, 0.35, 1.8), (47.0, 9.0, 16.8, 0.3, 2.0),
            (49.0, 9.5, 16.0, 0.25, 1.8), (50.5, 10.0, 15.0, 0.2, 1.4), (52.0, 11.0, 14.0, 0.15, 0.4),
            (53.4, 12.4, 12.6, 0.08, 0.0)]
    sections = [(Y(v), profile(ul, ur, h, b)) for v, ul, ur, h, b in body]

    def body_mat(k, i):
        lower = body[k][0] >= 45.0  # the glowing lower point
        return [GLOW if lower else BRIGHT, GLOW if lower else DARK, RIDGE, BRIGHT, SIDE][i]

    lib.section_loft(bm, sections, body_mat, bottom_mat=UNDER)

    # The blade split off along the right side, joining the shard above its point.
    blade = [(7.0, 17.5, 22.0, 0.26), (31.0, 17.5, 22.0, 0.26), (32.5, 17.5, 21.2, 0.25),
             (36.0, 17.0, 20.5, 0.24), (40.0, 16.8, 19.6, 0.22), (42.0, 16.0, 19.0, 0.2),
             (43.5, 15.5, 18.3, 0.18), (45.5, 14.5, 17.0, 0.14)]

    def blade_profile(ul, ur, h):
        w = ur - ul
        return [(X(ul), 0.0), (X(ul + 0.4), h * 0.3), (X(ur - min(1.4, w * 0.35)), h),
                (X(ur - min(0.8, w * 0.2)), h), (X(ur - 0.3), h * 0.6), (X(ur), 0.0)]

    lib.section_loft(bm, [(Y(v), blade_profile(ul, ur, h)) for v, ul, ur, h in blade],
                     lambda k, i: [HOOD, DARK, HOOD, EDGE, SIDE][i], bottom_mat=UNDER)

    # Pointed hood over the top, wider than both, with a bright rim along its front edge.
    hood = [(1.6, 12.4, 12.6, 0.14), (2.5, 10.0, 15.0, 0.26), (4.0, 8.0, 18.5, 0.37),
            (5.5, 5.5, 21.0, 0.45), (7.0, 4.0, 22.0, 0.5), (8.0, 3.8, 22.0, 0.5),
            (9.6, 3.8, 22.0, 0.46)]

    def hood_profile(ul, ur, h):
        return [(X(ul), 0.0), (X(min(ul + 0.8, 11.8)), h * 0.45), (X(12.0), h), (X(13.0), h),
                (X(max(ur - 0.8, 13.2)), h * 0.45), (X(ur), 0.0)]

    def hood_mat(k, i):
        if k == len(hood) - 2:  # the rim along the front edge
            return [BRIGHT, BRIGHT, RIDGE, BRIGHT, EDGE][i]
        return [BRIGHT, HOOD, RIDGE, HOOD, EDGE][i]

    lib.section_loft(bm, [(Y(v), hood_profile(ul, ur, h)) for v, ul, ur, h in hood], hood_mat,
                     bottom_mat=UNDER)

    return lib.to_object(NAME, bm, mats, coll, merge=0.002)


def merged_sprite():
    """newshe-199's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, PIECES[0])
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(layout, out):
    """The whole shard's sprite (first frames) as one image, padded to the 24:28 shape that
    render_preview expects for size 4 (48 x 56 px, the shard in the middle)."""
    import numpy as np
    img = np.zeros((56, 48, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(ROOT, name)
        frame = data["frames"][0]
        x0, y0 = cx + 24 - 12, cy + 28 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 48, 56, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(layout, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
