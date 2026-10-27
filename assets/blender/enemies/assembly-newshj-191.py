"""Green eye fortress (newshj.shp, assembly of 12 pieces): a 3D version of its sprites.

Seen in episode 2 (levels 2.2, 2.21, 2.22) and episode 4 (4.8). Twelve 2x2 ground enemies side by
side make one 96x84 px structure (sprite.json `assemblyLayout`): a ribbed green shell with a
rounded back, a grey cross bar with bolts and two posts across it, a dark grey socket holding a
big green eye dome with a grey spine and block over it, two grey pods on the flanks, a grey
mechanism and barrel below the eye and a dark housing with a muzzle ring at the front, the lower
shell running out in green ribbed columns.

The whole thing is built once in assembly coordinates (mirror symmetric about the centre) and
cut into the pieces with common.split_assembly. The eye pieces (newshj-161, newshj-163) change
colour through their frames: glowing green with a white core (the base models), dull olive with a
reflection (-f2) and shut grey (-f3). The eye also animates within those models: the glowing eye's
white core is smaller on one frame, larger on the next and gone on the last two, where only a
glyph of pale or yellow flecks shows on it; the dull eye shows that glyph in grey, lighter on its
second frame, while its reflection dims (common.frame_part, palette_material frames=). The front pieces (newshj-231, newshj-233) have a lit frame
(-f2) where the muzzle holds a glowing green core and the ribs beside it glow. Those are the same
shape in other colours, built as separate models so the glow follows the animation.

Run: blender --background --python assets/blender/enemies/assembly-newshj-191.py [-- --preview out.png]
(the preview is the whole structure; each piece also gets <piece>.png next to it) [--frames dir]
(every frame of the animated eye models, <model>.png in dir).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b099 as lib  # noqa: E402

NAME = "assembly-newshj-191"
ROOT = common.repo_root(__file__)
TAG = "nshj191"
PIECES = ["newshj-153", "newshj-155", "newshj-157", "newshj-159",
          "newshj-191", "newshj-161", "newshj-163", "newshj-197",
          "newshj-229", "newshj-231", "newshj-233", "newshj-235"]
# Exported models per colour variant: model name -> (piece, frames it covers; None = all).
VARIANTS = {
    "glow": {**{p: (p, None) for p in PIECES},
             "newshj-161": ("newshj-161", [165, 203, 237, 275]),
             "newshj-163": ("newshj-163", [167, 205, 239, 277]),
             "newshj-231": ("newshj-231", [241]),
             "newshj-233": ("newshj-233", [243])},
    "dim": {"newshj-161-f2": ("newshj-161", [161, 199]),
            "newshj-163-f2": ("newshj-163", [163, 201])},
    "grey": {"newshj-161-f3": ("newshj-161", [193]),
             "newshj-163-f3": ("newshj-163", [195])},
    "lit": {"newshj-231-f2": ("newshj-231", [231]),
            "newshj-233-f2": ("newshj-233", [233])},
}
G = lib.Grid(96, 84)  # assembly px; edge column 48 is the axis (X = 0)
# The eye pieces' frames that show the same step of the eye's animation: (newshj-161, newshj-163).
GLOW_STEPS = {"core-small": (165, 167), "core": (203, 205), "flecks-pale": (237, 239), "flecks-yellow": (275, 277)}
DIM_STEPS = ((161, 163), (199, 201))
# Where each eye piece sits in the assembly (column, row of its top left pixel).
EYE_ORIGIN = {"newshj-161": (24, 28), "newshj-163": (48, 28)}


def mirror(c):
    return 96 - c


def shell_sections(pixels):
    """The green shell: per row, the run of filled pixels around the centre (gaps of up to 3 px
    are slits, bridged), inset half a pixel for the outline. Rows 2-83."""
    sections = []
    for r in range(2, 84):
        lo = hi = 48
        while True:
            near = [c for c in range(lo - 4, lo) if (c, r) in pixels]
            if not near:
                break
            lo = min(near)
        while True:
            near = [c for c in range(hi + 1, hi + 5) if (c, r) in pixels]
            if not near:
                break
            hi = max(near)
        # Height: a rounded back (rows 2-13), then level.
        t = min(max((r + 0.5 - 2) / 11, 0), 1)
        h = 0.08 + 0.34 * math.sin(math.pi / 2 * t)
        sections.append([r + 0.5, lo + 0.5, hi + 0.5, h, 0.0])
    first, last = sections[0], sections[-1]
    sections.insert(0, [2.0, first[1] + 1.5, first[2] - 1.5, first[3] * 0.6, 0.0])
    sections.append([84.0, last[1], last[2], last[3], 0.0])
    # Smooth the steps a little, then symmetrise (the sprite is symmetric to within a pixel).
    raw = [((48 - s[1]) + (s[2] - 48)) / 2 for s in sections]
    widths = [max(raw[max(i - 1, 0):i + 2]) for i in range(len(raw))]  # close 1-row notches
    for i, s in enumerate(sections):
        k = widths[max(i - 1, 0):i + 2]
        s[1], s[2] = 48 - sum(k) / len(k), 48 + sum(k) / len(k)
    return sections


def build(sprite, pixels, variant):
    coll = common.reset_collection(f"{NAME}-{variant}")
    pal = lambda i, **kw: common.palette_material(sprite, i, TAG, **kw)  # noqa: E731
    eye, core = {
        "glow": (pal(205, metallic=0.1, roughness=0.15, emission_strength=3.0), pal(47, roughness=0.2, emission_strength=4.0)),
        # The reflection dims on the second dull frame.
        "dim": (pal(42, metallic=0.2, roughness=0.12),
                common.palette_material(sprite, 141, TAG + "refl", metallic=0.2, roughness=0.1, frames={199: 139})),
        "grey": (pal(8, metallic=0.4, roughness=0.25), pal(14, metallic=0.4, roughness=0.2)),
        "lit": (pal(205, metallic=0.1, roughness=0.15, emission_strength=3.0), pal(47, roughness=0.2, emission_strength=4.0)),
    }[variant]
    lit = variant == "lit"
    mats = [
        pal(40, metallic=0.2, roughness=0.5),  # 0 green shell
        pal(43, metallic=0.2, roughness=0.45),  # 1 light green ribs
        pal(41, metallic=0.2, roughness=0.5),  # 2 green centre plate
        pal(3, metallic=0.4, roughness=0.5),  # 3 dark grey socket and housings
        pal(5, metallic=0.5, roughness=0.45),  # 4 mid grey bar, shoulders, pod backs
        pal(8, metallic=0.5, roughness=0.4),  # 5 light grey pods and mechanism
        pal(11, metallic=0.6, roughness=0.3),  # 6 bright grey bolts and bevels
        pal(7, metallic=0.5, roughness=0.4),  # 7 grey spine, barrel, muzzle ring
        eye,  # 8 eye dome
        core,  # 9 eye core / reflection
        pal(202, emission_strength=3.0) if lit else pal(43, metallic=0.2, roughness=0.45),  # 10 glowing ribs
        pal(205, emission_strength=4.0) if lit else pal(2, metallic=0.3, roughness=0.6),  # 11 muzzle core
    ]
    if variant == "dim":  # 12 the grey glyph on the dull eye, lighter on its second frame
        mats.append(common.palette_material(sprite, 10, TAG + "glyph", metallic=0.3, roughness=0.3,
                                            frames={199: 12, 201: 12}))
    SHELL, RIB, PLATE, DARK, MID, LIGHT, BRIGHT, GREY, EYE, CORE, STRIPE, MUZZLE = range(12)
    bm = bmesh.new()

    # --- green shell ----------------------------------------------------------------------------
    shell = shell_sections(pixels)
    lib.hull(bm, G, shell, n=14, p=3.0, mat=SHELL)
    sz = lambda c, r: lib.hull_z(G, shell, c, r)  # noqa: E731

    def rib(c, r0, r1, hw, hh, mat=RIB, step=2.0, sink=0.02):
        pts = []
        r = r0
        while r < r1 + 1e-6:
            pts.append((c, r, hw, hh, sz(c, r) - sink))
            r += step
        if pts[-1][1] < r1:
            pts.append((c, r1, hw, hh, sz(c, r1) - sink))
        lib.tube(bm, G, pts, sides=8, mat=mat)

    # Centre plate down the back, between the shoulders.
    lib.prism(bm, G, [(43.5, 3.5), (52.5, 3.5), (52.5, 27.5), (43.5, 27.5)], 0.15, 0.46, mat=PLATE, inset=0.8)
    # Ribs over the rounded back and down the flanks.
    for c, r0, r1, hw in ((21.5, 8.5, 18.0, 1.3), (27.5, 5.5, 17.5, 1.3), (34.0, 3.8, 15.5, 1.5), (39.5, 3.2, 16.0, 1.3),
                          (4.5, 22.0, 52.0, 1.3), (25.0, 23.0, 50.0, 1.5)):
        rib(c, r0, r1, hw, 0.04)
        rib(mirror(c), r0, r1, hw, 0.04)
    # Ribbed columns down the front, the inner ones glowing in the lit frame.
    for c, r0, hw in ((14.0, 64.0, 3.0), (20.5, 56.0, 1.4), (23.5, 54.0, 1.4), (28.0, 52.0, 2.2)):
        rib(c, r0, 84.0, hw, 0.06, sink=0.03)
        rib(mirror(c), r0, 84.0, hw, 0.06, sink=0.03)
    rib(34.0, 51.0, 84.0, 2.0, 0.06, mat=STRIPE, sink=0.03)
    rib(mirror(34.0), 51.0, 84.0, 2.0, 0.06, mat=STRIPE, sink=0.03)

    # --- cross bar, posts and bolts (left side, then mirrored) -----------------------------------
    sv, sf = len(bm.verts), len(bm.faces)
    lib.tube(bm, G, [(13.0, 12.2, 0.0, 0.0, 0.40), (13.0, 13.5, 1.6, 0.09, 0.40), (13.0, 15.5, 2.0, 0.12, 0.40),
                     (13.0, 25.0, 2.0, 0.12, 0.38), (13.0, 27.5, 1.6, 0.08, 0.36)], sides=10, mat=LIGHT)
    lib.prism(bm, G, [(14.5, 18.8), (42.0, 18.8), (42.0, 22.6), (14.5, 22.6)], 0.25, 0.5, mat=MID, inset=0.6)
    lib.mound(bm, G, 31.5, 18.0, 2.6, 2.2, 0.12, z0=0.46, mat=BRIGHT, seg=12, rings=3)
    lib.box(bm, G, 36.0, 18.8, 40.5, 21.0, 0.45, 0.54, mat=LIGHT, inset=0.3)

    # Shoulders of the eye socket and the light caps on them.
    lib.mound(bm, G, 37.0, 25.0, 8.0, 4.8, 0.28, z0=0.3, p=2.6, pz=3.0, mat=MID, seg=16, rings=4)
    lib.mound(bm, G, 41.5, 25.5, 2.6, 1.9, 0.14, z0=0.46, mat=BRIGHT, seg=12, rings=3)

    # Side pods: a dark back, a light top and a bevelled front.
    Z = 0.2
    lib.hull(bm, G, [(35.8, 9.0, 20.0, 0.3, Z, MID), (37.0, 8.0, 21.0, 0.4, Z, MID), (40.0, 7.6, 21.4, 0.48, Z, MID),
                     (43.5, 7.6, 21.4, 0.52, Z, LIGHT), (50.0, 7.6, 21.4, 0.54, Z, LIGHT), (55.0, 8.2, 21.2, 0.52, Z, BRIGHT),
                     (58.5, 9.4, 21.0, 0.45, Z, BRIGHT), (62.0, 10.4, 19.8, 0.36, Z, BRIGHT), (65.6, 11.0, 17.0, 0.24, Z)],
             n=12, p=4.0, mat=MID)
    lib.mirror_new(bm, G, sv, sf, 48.0)

    # --- eye socket, eye and its spine ----------------------------------------------------------
    lib.mound(bm, G, 48.0, 37.5, 18.5, 16.0, 0.3, z0=0.28, p=2.3, pz=3.0, mat=DARK, seg=28, rings=6)
    lib.mound(bm, G, 48.0, 37.5, 15.8, 10.2, 0.3, z0=0.5, p=2.0, mat=EYE, seg=28, rings=7)

    if variant in ("glow", "lit"):
        # (On the eye pieces the core changes size frame by frame: strip_core swaps it for eye_parts.)
        # The white-hot core fills most of the eye, a green rim round it.
        lib.mound(bm, G, 48.0, 36.0, 13.0, 6.6, 0.314, z0=0.5, p=2.2, pz=4.5, mat=CORE, seg=24, rings=6)
    else:
        # A reflection up on the left of the dull eye.
        c, r = (38.5, 33.0) if variant == "dim" else (39.5, 32.5)
        lib.mound(bm, G, c, r, 3.2, 2.6, 0.05, z0=eye_z(c, r) - 0.02, p=2.0, mat=CORE, seg=12, rings=3)
        if variant == "dim":
            flecks(bm, eye_pixels(DIM_STEPS[0], range(10, 14), {"newshj-161": (13, 20, 2, 10),
                                                                 "newshj-163": (3, 10, 2, 11)}), {}, 12)

    # Grey spine over the eye down to a block at its bottom.
    lib.tube(bm, G, [(48.5, r, 2.2, 0.06, eye_z(48.5, r) + 0.0) for r in (27.6, 29.0, 31.0, 33.5, 36.0, 38.5)] +
             [(48.5, 39.5, 2.6, 0.08, eye_z(48.5, 39.5) + 0.02)], sides=8, p=3.0, mat=GREY)
    lib.box(bm, G, 45.0, 38.5, 52.0, 46.6, 0.5, 0.84, mat=LIGHT, inset=0.8)
    lib.box(bm, G, 42.6, 42.0, 45.2, 46.6, 0.45, 0.66, mat=GREY, inset=0.4)
    lib.box(bm, G, 51.8, 42.0, 54.4, 46.6, 0.45, 0.66, mat=GREY, inset=0.4)

    # --- mechanism below the eye, barrel and muzzle ----------------------------------------------
    lib.prism(bm, G, [(36.5, 46.5), (59.5, 46.5), (56.5, 56.5), (39.5, 56.5)], 0.0, 0.5, mat=DARK, inset=1.0)
    sv, sf = len(bm.verts), len(bm.faces)
    lib.prism(bm, G, [(40.0, 49.5), (46.0, 49.0), (48.0, 52.5), (46.5, 56.0), (42.0, 55.5)], 0.3, 0.6, mat=LIGHT, inset=0.7)
    lib.mirror_new(bm, G, sv, sf, 48.5)
    lib.tube(bm, G, [(48.5, 54.0, 2.5, 0.13, 0.46), (48.5, 57.0, 2.7, 0.14, 0.46), (48.5, 58.0, 2.5, 0.13, 0.46),
                     (48.5, 68.0, 2.5, 0.13, 0.46)], sides=10, mat=GREY)
    lib.prism(bm, G, [(37.5, 67.0), (59.5, 67.0), (59.5, 82.0), (57.0, 84.0), (40.0, 84.0), (37.5, 82.0)], 0.0, 0.46,
              mat=DARK, inset=1.2)
    lib.ring(bm, G, 48.5, 76.0, 6.0, 4.2, 0.36, 0.54, sides=20, mat=GREY)
    if lit:
        lib.mound(bm, G, 48.5, 75.5, 4.3, 4.3, 0.16, z0=0.4, p=2.0, mat=MUZZLE, seg=16, rings=4)
    else:
        lib.mound(bm, G, 48.5, 76.0, 4.3, 4.3, 0.03, z0=0.4, p=2.0, mat=MUZZLE, seg=16, rings=2)

    return lib.to_object(f"{NAME}-{variant}", bm, mats, coll)


def eye_z(c, r):
    """Height of the eye dome's surface at assembly (col, row)."""
    u = ((c - 48.0) / 15.8) ** 2 + ((r - 37.5) / 10.2) ** 2
    return 0.5 + 0.3 * math.sqrt(max(1 - u, 0))


_EYE_FRAMES = {}


def eye_pixels(step, indices, region):
    """The eye pixels of these palette indices on a step (frames of newshj-161 and newshj-163):
    [(assembly col, row, palette index)]. `region` is each piece's (col0, col1, row0, row1) to look in."""
    out = []
    for piece, frame in zip(EYE_ORIGIN, step):
        if piece not in _EYE_FRAMES:
            _EYE_FRAMES[piece] = {f["index"]: [[int(v) for v in (row.split() if isinstance(row, str) else row)] for row in f["pixels"]]
                                  for f in common.load_sprite(ROOT, piece)["frames"]}
        rows = _EYE_FRAMES[piece][frame]
        c0, c1, r0, r1 = region[piece]
        oc, orow = EYE_ORIGIN[piece]
        out += [(oc + c, orow + r, rows[r][c]) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)
                if rows[r][c] in indices]
    return out


def flecks(bm, pixels, mat_of, mat=0):
    """A small fleck raised on the eye dome for each pixel (col, row, palette index); its material
    is mat_of[palette index], or `mat`."""
    for c, r, i in pixels:
        c, r = c + 0.5, r + 0.5
        lib.mound(bm, G, c, r, 0.52, 0.52, 0.03, z0=eye_z(c, r) - 0.012, p=6.0, pz=3.0, seg=8, rings=2,
                  mat=mat_of.get(i, mat))


def strip_core(obj):
    """Remove the glowing core (material 9, and whatever is joined to it, like the faces filling
    its cut) from a piece of the glow variant; eye_parts builds it per frame instead."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    seen, todo = set(), [f for f in bm.faces if f.material_index == 9]
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        todo += [g for e in f.edges for g in e.link_faces if g not in seen]
    verts = {v for f in seen for v in f.verts}
    bmesh.ops.delete(bm, geom=list(verts), context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()


def eye_parts(sprite, models):
    """What changes on the glowing eye from frame to frame, built in assembly coordinates as
    separate objects: [(object, {model: frames it shows on})] for the eye models `models`
    (newshj-161's, newshj-163's)."""
    coll = common.reset_collection(f"{NAME}-eye")
    core = common.palette_material(sprite, 47, TAG, roughness=0.2, emission_strength=4.0)
    parts = []

    def part(name, bm, mats):
        obj = lib.to_object(f"{NAME}-{name}", bm, mats, coll)
        parts.append((obj, {model: [frame] for model, frame in zip(models, GLOW_STEPS[name])}))

    # The white-hot core over most of the eye, a green rim round it; smaller on the first frame.
    for name, r, rx, ry in (("core", 36.0, 13.0, 6.6), ("core-small", 35.3, 10.6, 4.7)):
        bm = bmesh.new()
        lib.mound(bm, G, 48.0, r, rx, ry, 0.314, z0=0.5, p=2.2, pz=4.5, mat=0, seg=24, rings=6)
        part(name, bm, [core])
    # Without the core, the glyph on the eye shows as flecks: pale, then yellow and white.
    region = {"newshj-161": (10, 22, 0, 18), "newshj-163": (0, 16, 0, 18)}
    for name in ("flecks-pale", "flecks-yellow"):
        pixels = eye_pixels(GLOW_STEPS[name], {14, 31, 45, 94, 95, 110, 126}, region)
        indices = sorted({i for *_, i in pixels})
        bm = bmesh.new()
        flecks(bm, pixels, {i: k for k, i in enumerate(indices)})
        part(name, bm, [common.palette_material(sprite, i, TAG + "fleck", roughness=0.3, emission_strength=2.0)
                        for i in indices])
    return parts


def piece_sprites(piece, frames):
    sprites = common.load_sprite(ROOT, piece)["sprites"]
    if frames is None:
        return sprites
    return [{**sprites[0], "frames": frames}]


def main():
    layout_data = common.load_sprite(ROOT, PIECES[0])["assemblyLayout"]
    pixels, colours, min_cx, min_cy, w, h = lib.composite(ROOT, layout_data)
    sprite = lib.merged_sprite(ROOT, PIECES)
    cx0, cy0 = min_cx + w // 2, min_cy + h // 2
    centre = {e["model"]: (e["cx"] - cx0, e["cy"] - cy0) for e in layout_data}
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    whole = None
    for variant, models in VARIANTS.items():
        obj = build(sprite, pixels, variant)
        layout = [(model, *centre[piece]) for model, (piece, _) in models.items()]
        pieces = common.split_assembly(obj, layout)
        extra = {model: [] for model in models}
        if variant == "glow":
            eye_models = ("newshj-161", "newshj-163")
            for model in eye_models:
                strip_core(pieces[model])
            for part, frames in eye_parts(sprite, eye_models):
                cut = common.split_assembly(part, [(m, *centre[models[m][0]]) for m in eye_models])
                for model, piece_part in cut.items():
                    piece_part.name = f"{model}-{part.name.removeprefix(NAME + '-')}"
                    extra[model].append(common.frame_part(piece_part, frames[model]))
        for model, (piece, frames) in models.items():
            objects = [pieces[model]] + extra[model]
            common.export_sprite_model(ROOT, objects, f"enemies/{model}", piece_sprites(piece, frames))
            if "--frames" in sys.argv and model in ("newshj-161", "newshj-163", "newshj-161-f2", "newshj-163-f2"):
                data = common.load_sprite(ROOT, piece)
                data["frames"] = [f for f in data["frames"] if f["index"] in frames]
                out = Path(sys.argv[sys.argv.index("--frames") + 1]) / f"{model}.png"
                common.render_frame_previews(objects, str(out), data, ROOT)
            if preview:
                data = common.load_sprite(ROOT, piece)
                index = frames[0] if frames else data["frames"][0]["index"]
                image = next(f["image"] for f in data["frames"] if f["index"] == index)
                common.render_preview([pieces[model]], str(preview.parent / f"{model}.png"),
                                      ROOT / "reference" / "models" / piece / image, size=2)
        if variant == "glow":
            whole = obj
    if preview:
        import tempfile
        ref = lib.composite_png(pixels, colours, w, h, Path(tempfile.mkdtemp()) / "assembly.png", pad_to=(96, 112))
        common.render_preview([whole], str(preview), ref, size=8, view_px=640)


if __name__ == "__main__":
    main()
