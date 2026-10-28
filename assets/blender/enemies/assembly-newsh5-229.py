"""Grey and red gunship (newsh5.shp frames 229 and 231, side by side): a 3D version of its sprites.

Seen in episode 4 (levels 4.16 and 4.47). Two 2x2 enemies make one 48x28 px ship (sprite.json
`assemblyLayout`) flying up the screen: a narrow nose with a red stripe down its spine, a red
shield on its chest between rounded grey shoulders, two grey canards up front with red fins under
them, and two big grey wings swept back and down to pointed tips that each carry a red barrel
pointing down. The lower body runs off the bottom of the sprites between red side panels.

The ship is built whole (left half mirrored about pixel column 24, the sprite's axis) in assembly
coordinates and cut into newsh5-229 (left) and newsh5-231 (right) with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh5-229.py [-- --preview out.png]
(the preview is the whole ship; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b013 as lib  # noqa: E402

NAME = "assembly-newsh5-229"
ROOT = common.repo_root(__file__)
PIECES = ["newsh5-229", "newsh5-231"]
U = lib.U
G = lib.Grid(48, 28)  # assembly pixels: newsh5-229 is columns 0-23, newsh5-231 columns 24-47
AXIS = 24  # mirror axis: the centre of assembly column 24
AX = G.x(AXIS)


def E(c, r):
    """A pixel corner (column edge, row edge) to Blender XY."""
    return (G.x(c - 0.5), G.y(r - 0.5))


def XE(c):
    """A column edge to Blender X."""
    return G.x(c - 0.5)


def YE(r):
    """A row edge to Blender Y."""
    return G.y(r - 0.5)


def tilt(bm, start, x_root, slope):
    """Lower the vertices added since `start` by `slope` units per unit outward of x_root (droop)."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.z -= slope * max(0.0, x_root - v.co.x)


def body_loft(bm, sections, x, sides=16, mat_index=0):
    """A loft along +Y with a round top and a shallower round bottom. Sections are
    (row edge, half width px, z centre px, height above px, depth below px); a zero half width
    is a point at (z centre + height above)."""
    rings = []
    for r, hw, zc, top, bot in sections:
        y = YE(r)
        if hw == 0:
            rings.append([bm.verts.new((x, y, (zc + top) * U))])
            continue
        ring = []
        for i in range(sides):
            a = 2 * math.pi * (i + 0.5) / sides
            s = math.sin(a)
            ring.append(bm.verts.new((x + hw * U * math.cos(a), y, (zc + (top if s > 0 else bot) * s) * U)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = mat_index
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        if len(ring) > 1:
            bm.faces.new(list(reversed(ring)) if rev else ring).material_index = mat_index


def bevel_prism(bm, outline, z0, z1, bevel, mat_index=0):
    """A plate over a counter-clockwise XY outline from z0 to z1 with its top edge chamfered by `bevel`."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(outline, outline[1:] + outline[:1]))
    if area < 0:
        outline = list(reversed(outline))
    top = lib.inset_polygon(outline, bevel)
    rings = [[bm.verts.new((x, y, z0)) for x, y in outline],
             [bm.verts.new((x, y, z1 - bevel)) for x, y in outline],
             [bm.verts.new((x, y, z1)) for x, y in top]]
    n = len(outline)
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat_index
    bm.faces.new(list(reversed(rings[0]))).material_index = mat_index
    bm.faces.new(rings[-1]).material_index = mat_index


def densify(sections, step=1.0):
    """body_loft sections with extra ones interpolated at every `step` rows (for painting)."""
    out = [sections[0]]
    for a, b in zip(sections, sections[1:]):
        if a[1] > 0 and b[1] > 0:
            r = math.floor(a[0] / step) * step + step
            while r < b[0] - 0.2:
                if r > a[0] + 0.2:
                    t = (r - a[0]) / (b[0] - a[0])
                    out.append(tuple(p + (q - p) * t for p, q in zip(a, b)))
                r += step
        out.append(b)
    return out


def crest(sections, r):
    """The top (z centre + height above, px) of body_loft sections at row edge r."""
    for a, b in zip(sections, sections[1:]):
        if a[0] <= r <= b[0]:
            t = (r - a[0]) / (b[0] - a[0])
            return (a[2] + a[3]) + ((b[2] + b[3]) - (a[2] + a[3])) * t
    return sections[-1][2] + sections[-1][3]


def pixel_cut(bm, first_face, c0, c1, r0, r1, min_nz=0.3):
    """Cut the upward faces added since `first_face` along every column edge c0..c1 and row edge
    r0..r1, so each piece can take its own sprite pixel's colour."""
    def tops():
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        fs = [f for f in bm.faces[first_face:] if f.normal.z > min_nz]
        es = list({e for f in fs for e in f.edges})
        vs = list({v for f in fs for v in f.verts})
        return fs + es + vs
    for c in range(int(math.ceil(c0)), int(math.floor(c1)) + 1):
        bmesh.ops.bisect_plane(bm, geom=tops(), plane_co=(XE(c), 0, 0), plane_no=(1, 0, 0))
    for r in range(int(math.ceil(r0)), int(math.floor(r1)) + 1):
        bmesh.ops.bisect_plane(bm, geom=tops(), plane_co=(0, YE(r), 0), plane_no=(0, 1, 0))


def build(sprite, pixels):
    coll = common.reset_collection(NAME)
    tag = "n5a229"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    # Each part takes its mid-tone colour: the sprite's light and dark pixels on the hull, wings
    # and red parts are its drawn lighting (bright streaks = sheen on polished metal, dark right
    # halves = shade), which the game's lights make. The grey hull is polished metal; the red
    # parts are painted metal.
    metal = dict(metallic=0.75, roughness=0.3)
    paint = dict(metallic=0.3, roughness=0.45)
    mats = [
        pal(6, **metal),  # 0 grey hull
        pal(7, **metal),  # 1 grey wings (the sprite draws them a shade lighter than the body)
        pal(7, **metal),  # 2 wing-tip pods
        pal(4, metallic=0.5, roughness=0.5),  # 3 dark groove under the chest (a recess)
        pal(69, **paint),  # 4 red panels, fins and shield
        pal(71, **paint),  # 5 red spine stripe
        pal(70, **paint),  # 6 red cowls and wing-tip barrels
        pal(8, **metal),  # 7 wing ribs (the light diagonal lines)
    ]
    HULL, WING, RIB, DARK, RED, LRED, DRED, LGREY = range(8)
    bm = bmesh.new()

    # ---- left half (mirrored below) ----
    start = len(bm.verts)

    # Wing (rows 13-27): a 2 px plate with a bevelled top, swept from the body out and up to a
    # pointed tip at columns 2-4; its root tucks under the red panel and the lower body. Its top
    # is cut on the pixel grid (small flat facets that follow its droop).
    wing = [E(2, 13), E(5, 13), E(8.2, 16.6), E(9.9, 16.9), E(10.2, 15.9), E(11, 15.0), E(19.5, 15.0),
            E(19.5, 28), E(12.0, 28), E(12.0, 27.0), E(9.2, 27.0), E(9.2, 26.0), E(9.9, 26.0), E(5.9, 22.0),
            E(4.7, 21.0), E(2, 21.0)]
    v0 = len(bm.verts)
    f0 = lib.nfaces(bm)
    bevel_prism(bm, wing, -0.6 * U, 1.4 * U, 0.5 * U, mat_index=WING)
    pixel_cut(bm, f0, 5, 17, 14, 27, min_nz=0.8)
    tilt(bm, v0, G.x(16), 0.02)
    # Raised ribs along the wing (the light diagonal lines).
    for (c0, r0), (c1, r1) in (((5.5, 17.0), (11.5, 27.0)), ((8.5, 19.0), (14.0, 26.5))):
        v0 = len(bm.verts)
        n = 5
        lib.tube(bm, [((*E(c0 + (c1 - c0) * k / n, r0 + (r1 - r0) * k / n), 1.4 * U), 0.5 * U) for k in range(n + 1)],
                 sides=6, mat_index=LGREY, flat=0.8)
        tilt(bm, v0, G.x(16), 0.02)
    # Wing tip (columns 2-4, rows 13-20): a round pod; the red barrel under it (rows 20-27).
    v0 = len(bm.verts)
    f0 = lib.nfaces(bm)
    pod = [(YE(12.9), 0.0, 0.0, 1.0 * U), (YE(13.5), 1.0 * U, 1.0 * U, 1.0 * U), (YE(14.6), 1.5 * U, 1.5 * U, 1.0 * U)]
    pod += [(YE(r), 1.5 * U, 1.5 * U, 1.0 * U) for r in (15.5, 16.5, 17.5, 18.5)]
    pod += [(YE(19.6), 1.5 * U, 1.5 * U, 1.0 * U), (YE(20.6), 0.0, 0.0, 1.0 * U)]
    common.loft(bm, pod, sides=10, mat_index=RIB)
    barrel = [(YE(19.8), 1.35 * U, 1.35 * U, 0.6 * U)]
    barrel += [(YE(r), 1.35 * U, 1.35 * U, 0.6 * U) for r in (21.0, 22.0, 23.0, 24.0, 25.0, 26.0)]
    barrel += [(YE(27.2), 1.35 * U, 1.35 * U, 0.6 * U), (YE(27.95), 0.6 * U, 0.6 * U, 0.6 * U)]
    common.loft(bm, barrel, sides=8, mat_index=DRED)
    common.shift_x(bm, v0, XE(3.5))
    lib.set_smooth(bm, f0)
    tilt(bm, v0, G.x(16), 0.02)
    # Red cowl on the wing's root (columns 10-13, rows 16-18): a dome.
    f0 = lib.ellipsoid(bm, (XE(12.1), YE(17.5), 1.0 * U), (2.2 * U, 1.6 * U, 2.3 * U),
                       segments=10, rings=5, mat_index=DRED)
    lib.set_smooth(bm, f0)

    # Canard (rows 1-4, columns 9-18): a horizontal cylinder 4 px across, and the red fin under
    # it: one flat plate tapering down and out from the nose, which the canard sits on.
    f0 = lib.nfaces(bm)
    canard = [(XE(9.0), 0.8 * U, 0.8 * U, 0.0), (XE(9.8), 1.9 * U, 1.9 * U, 0.0)]
    canard += [(XE(c), 2.2 * U, 2.1 * U, 0.0) for c in (10.6, 12.0, 13.4, 14.8, 16.2)]
    canard += [(XE(17.0), 2.0 * U, 1.9 * U, 0.0), (XE(17.6), 1.3 * U, 1.3 * U, 0.0), (XE(18.4), 0.5 * U, 0.6 * U, 0.0)]
    lib.loft_x(bm, canard, y=YE(3.0), z=2.0 * U, sides=10, mat_index=HULL)
    # Its root (row 4, columns 16-21) running into the nose under the canard's slanted inner end.
    lib.tube(bm, [((XE(15.5), YE(4.6), 1.9 * U), 1.1 * U), ((XE(21.5), YE(4.6), 2.4 * U), 1.1 * U)],
             sides=8, mat_index=HULL)
    lib.set_smooth(bm, f0)
    v0 = len(bm.verts)
    f0 = lib.nfaces(bm)
    fin = [E(9.0, 4.5), E(20.5, 4.5), E(20.5, 6.0), E(19.6, 9.1), E(16.4, 9.1), E(14.8, 7.6), E(12.8, 6.7),
           E(9.0, 6.0)]
    bevel_prism(bm, fin, 0.0, 2.9 * U, 0.4 * U, mat_index=RED)
    pixel_cut(bm, f0, 10, 20, 5, 9, min_nz=0.8)
    # Taper it: the top falls and the underside rises toward the outer end, under the canard.
    bm.verts.ensure_lookup_table()
    root = G.x(20)
    for v in bm.verts[v0:]:
        out = max(0.0, root - v.co.x)
        v.co.z += (-0.06 if v.co.z > 1.5 * U else 0.12) * out

    lib.mirror_x(bm, start, AX)

    # Red side panels down the lower body (columns 15-19 at the top narrowing to 18-19, rows 16-27):
    # round bars standing on the wing (the right one is drawn darker only because it is in shade).
    for side, mat in ((-1, RED), (1, RED)):
        pts = [((15.9, 15.6), 0.9), ((16.6, 17.4), 1.9), ((17.6, 20.3), 1.9), ((18.9, 22.6), 1.15),
               ((19.0, 25.0), 1.1), ((19.0, 27.9), 1.1)]
        f0 = lib.nfaces(bm)
        tube = []
        for (c, r), rad in pts:
            x, y = E(c, r)
            x = AX + (x - AX) * -side if side > 0 else x
            tube.append(((x, y, max(rad, 1.3) * U), rad * U))
        lib.tube(bm, tube, sides=8, mat_index=mat)
        lib.set_smooth(bm, f0)

    # ---- centre parts ----

    # Body: the narrow nose (rows 0-8), the shoulders (rows 9-15), a dark groove at row 16 and the
    # round lower body (rows 17-27, about 9 px across and 6 px tall). Round-topped all along.
    f0 = lib.nfaces(bm)
    body = [(-0.2, 0.0, 0.0, 2.0, 0.0), (0.5, 1.3, 0.0, 2.6, 0.6), (2.9, 1.5, 0.0, 3.6, 0.8),
            (3.5, 3.4, 0.0, 3.9, 1.0), (4.2, 4.5, 0.0, 4.2, 1.2), (8.6, 4.6, 0.0, 6.0, 1.5),
            (9.4, 7.3, 0.0, 6.4, 1.8), (10.4, 8.7, 0.0, 6.8, 2.0), (11.4, 9.5, 0.0, 7.0, 2.2),
            (14.8, 9.5, 0.0, 7.0, 2.4), (15.6, 9.0, 0.0, 6.7, 2.6), (16.0, 8.6, 0.0, 5.2, 2.8),
            (16.8, 8.0, 0.0, 5.2, 3.2), (17.4, 7.0, 0.0, 6.0, 3.6), (18.4, 4.9, 0.0, 6.3, 4.0),
            (27.3, 4.8, 0.0, 6.1, 4.0), (28.0, 3.6, 0.0, 5.0, 3.0)]
    body_loft(bm, densify(body, 1.5), AX, sides=14, mat_index=HULL)
    lib.set_smooth(bm, f0)
    # Red stripe down the spine (rows 0-10): a straight round bar 2 px wide standing about 1.6 px
    # proud of the nose's crest, running into the chest dome.
    f0 = lib.nfaces(bm)
    spine = [((AX, YE(0.4), (crest(body, 0.4) + 0.2) * U), 0.55 * U)]
    spine += [((AX, YE(r), (crest(body, r) + 0.6) * U), 1.0 * U) for r in (1.2, 4.2, 8.6, 11.2)]
    lib.tube(bm, spine, sides=8, mat_index=LRED)
    lib.set_smooth(bm, f0)
    # The red shield on the chest (columns 20-28, rows 10-15): a low smooth dome, 9 x 6 px,
    # rising about 3 px above the hull.
    f0 = lib.nfaces(bm)
    n = 20
    cy = YE(12.9)
    shield = [(AX + 4.7 * U * math.cos(2 * math.pi * k / n), cy + 2.7 * U * math.sin(2 * math.pi * k / n))
              for k in range(n)]
    lib.pillow(bm, shield, (AX, cy), 6.1 * U, 3.5 * U, 2.0 * U, rings=5, mat_index=RED, power=0.8, bottom_rings=1)
    lib.set_smooth(bm, f0)
    # Dark floor of the groove under the chest (row 16).
    lib.box(bm, AX - 3.5 * U, YE(16.9), AX + 3.5 * U, YE(15.9), 3.0 * U, 5.3 * U, mat_index=DARK)
    # The two pieces are cut apart at X = 0 (half a pixel left of the axis), and each piece's
    # normals at the cut come from its own side only: thin strips either side of the cut keep
    # those normals true, so the dome and the body show no crease down the middle.
    bm.normal_update()
    for x in (-0.03 * U, 0.03 * U):
        bm.faces.ensure_lookup_table()
        fs = [f for f in bm.faces if f.smooth and f.normal.z > 0.2
              and min(v.co.x for v in f.verts) < x < max(v.co.x for v in f.verts)]
        geom = fs + list({e for f in fs for e in f.edges}) + list({v for f in fs for v in f.verts})
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(x, 0, 0), plane_no=(1, 0, 0))

    # No per-pixel painting: every part keeps its own mid-tone material (see above), the game
    # draws the outline, and its lights shade the curves.
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    pixels = lib.combined_pixels([(common.load_sprite(ROOT, n)["frames"][0]["pixels"], 24 * k, 0)
                                  for k, n in enumerate(PIECES)], 48, 28)
    obj = build(sprite, pixels)
    # Piece centres relative to the assembly centre, in pixels (sprite.json cx 65 and 89, cy -18).
    layout = [("newsh5-229", -12, 0), ("newsh5-231", 12, 0)]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    out = lib.preview_arg()
    if out:
        out = Path(out)
        import tempfile
        frames = [common.load_sprite(ROOT, n) for n in PIECES]
        # The whole ship's sprite, padded to the 24:28 shape render_preview expects for size 4.
        ref = Path(tempfile.mkdtemp()) / "assembly.png"
        lib.composite_png([(frames[0]["frames"][0]["pixels"], frames[0]["colors"], 0, 14),
                           (frames[1]["frames"][0]["pixels"], frames[1]["colors"], 24, 14)], 48, 56, ref)
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name, data in zip(PIECES, frames):
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
