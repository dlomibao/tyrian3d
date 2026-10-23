"""Green spike (newshh.shp frames 77 and 115, an assembly of 2 pieces): a 3D version of its sprites.

Seen in episode 2 (level 2.4). Two 2x2 enemies stacked make one 24 x 56 px object pointing down
the screen (sprite.json `assemblyLayout`; the other entries there are unrelated neighbours):
newshh-77 is a carved olive head under a green hood (a rounded green cap with a bright ridge down
its middle that narrows to a point between the dark cheeks, a green arch below it and a pale knob
at its chin) ending in a bright green collar; newshh-115 below is a long faceted olive spike,
widest at its shoulder under the collar, lit from the left with a pale ridge line down its
middle and dark on its right.

The whole object is built once in assembly coordinates (the head as a smooth loft, the spike as
a flat-shaded 12-sided cone with a ridge on top), both following the sprite's width row by row.
The hood, arch and collar stand slightly proud of the olive body, and every facet takes the
colour of the sprite pixels under it. It is then cut into the two pieces with
common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshh-77.py [-- --preview out.png]
(the preview is the whole object; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b063 as lib  # noqa: E402

NAME = "assembly-newshh-77"
ROOT = common.repo_root(__file__)
PIECES = ["newshh-77", "newshh-115"]
# Grid rows 0-27 are newshh-77, rows 28-55 newshh-115; the grid's centre is screen (197, 87),
# the Blender origin.
CX0, CY0 = 197, 87
GW, GH = 24, 56
HEAD_END = 28  # first grid row of the spike


def X(c):
    return lib.px(c, GW)


def Y(r):
    return lib.row(r, GH)


def grid():
    """Both pieces' pixels pasted into one 24 x 56 grid."""
    rows = []
    for name in PIECES:
        rows += common.load_sprite(ROOT, name)["frames"][0]["pixels"]
    return rows


def merged_sprite():
    data = common.load_sprite(ROOT, PIECES[0])
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def is_green(i):
    return 192 <= i <= 207


def build(sprite, pixels):
    coll = common.reset_collection(NAME)
    indices = sorted(int(k) for k in sprite["colors"] if int(k) != 1)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [pal(i, metallic=0.35 if is_green(i) else 0.15, roughness=0.3 if is_green(i) else 0.55)
            for i in indices]
    slot = {i: k for k, i in enumerate(indices)}
    # Paint with a few steps of each ramp so the carving reads instead of every pixel's speckle.
    groups = {34: (32, 33, 34, 35), 37: (36, 37), 39: (38, 39), 41: (40, 41), 43: (42, 43),
              45: (44, 45), 194: (192, 193, 194), 196: (195, 196, 197), 201: (198, 199, 200, 201),
              204: (202, 203, 204)}
    step = {i: rep for rep, members in groups.items() for i in members}

    def slot_of(i):
        return slot.get(step.get(i, i))

    ext = lib.extents(pixels)
    inset = 0.6

    bm = bmesh.new()

    # Head: grid rows 6-27, a smooth body whose top bulges like a dome.
    head = [r for r in sorted(ext) if r < HEAD_END]
    hh = lambda w: min(0.27, 0.56 * w)  # noqa: E731
    prof = [(r, X(c), (half - inset) / 12) for r, c, half in lib.resample(lib.profile(ext, head), 1.0)]
    sections = []
    r, xc, w = prof[0]
    sections.append((Y(r - 0.5), xc, 0.0, 0.0, 0.0))
    sections.append((Y(r - 0.3), xc, w * 0.75, w * 0.25, 0.0))
    for r, xc, w in prof:
        sections.append((Y(r), xc, w, hh(w), 0.0))
    # Run the collar a little way into the spike's shoulder so the two meet without a gap.
    sections.append((Y(HEAD_END - 0.2), xc, w, hh(w), 0.0))
    head_start = len(bm.faces)
    lib.loft_x(bm, sections, sides=24, phase=0.5)
    bm.faces.ensure_lookup_table()
    head_faces = bm.faces[head_start:]
    # Relief: the green hood, arch and collar stand proud of the olive body; the pale chin knob
    # and the lighter olive bulge a little.
    head_verts = {v for f in head_faces for v in f.verts}
    for v in head_verts:
        if v.co.z <= 0.0:
            continue
        i = lib.sample(pixels, v.co.x, v.co.y)
        k = v.co.z / 0.27
        if is_green(i):
            v.co.z += 0.04 * k
        elif 35 <= i <= 45:
            v.co.z += (i - 37) * 0.004 * k

    # Spike: grid rows 28-52, a 12-sided cone with a ridge vertex on top, flat shaded.
    spike = [r for r in sorted(ext) if r >= HEAD_END]
    h = lambda w: min(0.3, 0.55 * w)  # noqa: E731
    prof = [(r, X(c), (half - inset) / 12) for r, c, half in lib.profile(ext, spike)]
    sections = []
    r, xc, w = prof[0]
    sections.append((Y(HEAD_END - 0.5), xc, w * 0.85, h(w) * 0.75, 0.0))
    for r, xc, w in prof[:-1]:
        sections.append((Y(r), xc, w, h(w), 0.0))
    sections.append((Y(prof[-1][0] - 0.2), prof[-1][1], 0.0, 0.0, 0.0))
    spike_start = len(bm.faces)
    lib.loft_x(bm, sections, sides=12, phase=0.0)
    bm.faces.ensure_lookup_table()
    spike_faces = list(bm.faces[spike_start:])
    head_faces = list(bm.faces[head_start:spike_start])

    lib.paint(bm, pixels, slot_of, under_slot=slot[35], min_nz=-0.3, faces=head_faces)
    lib.paint(bm, pixels, slot_of, under_slot=slot[35], min_nz=-0.3, faces=spike_faces, spread=0.4)
    # The spike's top face (its shoulder round the collar) is the pale lit rim.
    for f in spike_faces:
        if f.normal.y > 0.9:
            f.material_index = slot[44]
    flat = {f.index for f in spike_faces}
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    for poly in obj.data.polygons:
        poly.use_smooth = poly.index not in flat
    return obj


def composite_png(pixels, colors, out):
    """The whole object's sprite as one image, padded to the 24:28 shape that render_preview
    expects for size 4 (48 x 56 px, the object in the middle)."""
    import numpy as np
    img = np.zeros((56, 48, 4), dtype=np.float32)
    for r, line in enumerate(pixels):
        for c, v in enumerate(line):
            if v >= 0:
                img[r, c + 12] = [*(ch / 255 for ch in colors[str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 48, 56, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    pixels = grid()
    obj = build(sprite, pixels)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(pixels, sprite["colors"], Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=4)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
