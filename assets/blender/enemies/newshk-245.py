"""Grey octagonal emplacement with a red drum (newshk.shp frame 245): a 3D version of its sprite.

Seen in episode 3 (level 12) as a ground object. A bevelled grey octagonal pad with a raised
vented block above and below the centre, a dark pit across the middle holding a red drum that
lies along X (orange bands round it), a blue lens in a dark socket on top of the drum, and the
drum's axle running out to grooves in the pad's left and right edges.

Run: blender --background --python assets/blender/enemies/newshk-245.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
from lib_b074 import box, dome, ex, ey, frustum, loft_x  # noqa: E402

NAME = "newshk-245"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

PX = 1 / 12
PAD_WALL = 3 * PX  # the pad's upright outer wall
PAD_TOP = 4.5 * PX  # the deck: a bevelled drum about 4.5 px thick
DRUM_W = 4.0  # the drum's half depth in px at its widest (sprite rows 10-17)
DRUM_H = 5.0  # its half height in px: it rests on the deck with its crest 10 px above it
GROOVE = 2.0  # the lens socket's half width in px (sprite rows 12-15)


def drum_ring(w, h, grooved, floor):
    """The drum's cross-section as (y, z) offsets from its axis (units): an ellipse w wide and h
    tall, with two points on top that drop to `floor` between y = +-GROOVE px on grooved sections
    (the socket) and lie on the ellipse elsewhere. The same 15 points on every section."""
    t0 = math.asin(GROOVE / DRUM_W)
    ring = []
    for k in range(13):  # t0 .. 2 pi - t0, round the bottom
        t = t0 + (2 * math.pi - 2 * t0) * k / 12
        ring.append((w * math.sin(t), h * math.cos(t)))
    if grooved:
        g = w * math.sin(t0)
        ring += [(-g, floor), (g, floor)]
    else:
        for t in (-t0 / 3, t0 / 3):
            ring.append((w * math.sin(t), h * math.cos(t)))
    return ring


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(10, metallic=0.4, roughness=0.5),  # 0 pad grey
        pal(7, metallic=0.4, roughness=0.55),  # 1 pad wall, dark grey
        pal(13, metallic=0.45, roughness=0.35),  # 2 light grey frames and lips
        pal(4, metallic=0.3, roughness=0.6),  # 3 dark vents and axle
        pal(2, metallic=0.2, roughness=0.7),  # 4 the pit and grooves
        pal(116, metallic=0.15, roughness=0.35),  # 5 red drum, its crest
        pal(122, metallic=0.1, roughness=0.3, emission_strength=2.5),  # 6 yellow-orange bands
        pal(119, metallic=0.1, roughness=0.3, emission_strength=1.5),  # 7 red-orange centre band
        pal(112, metallic=0.2, roughness=0.6),  # 8 dark socket
        pal(149, metallic=0.1, roughness=0.15, emission_strength=3.0),  # 9 blue lens
        pal(11, metallic=0.45, roughness=0.4),  # 10 vent rib
        pal(8, metallic=0.4, roughness=0.5),  # 11 pad bevel
        pal(115, metallic=0.15, roughness=0.4),  # 12 red drum, its flanks
        pal(113, metallic=0.15, roughness=0.45),  # 13 dark red stripes and ends
        pal(117, metallic=0.15, roughness=0.35),  # 14 brighter red stripe
    ]
    (PAD, WALL, LIGHT, VENT, PIT, DRUM, BAND, CBAND, SOCKET, LENS, RIB, BEVEL, FLANK, DARKRED,
     REDHI) = range(15)
    bm = bmesh.new()

    # The octagonal pad (sprite rows 1-26, all 24 columns at rows 8-19): an upright wall, then a
    # 2.5 px bevel rising to the deck. The diagonals run through the middle of the sprite's steps.
    octagon = [(7.5, 27), (16.5, 27), (24, 19.5), (24, 8.5), (16.5, 1), (7.5, 1), (0, 8.5), (0, 19.5)]
    outline = [(ex(c), ey(r)) for c, r in octagon]
    frustum(bm, outline, 0.0, PAD_WALL + 0.001, mat_index=WALL)
    frustum(bm, outline, PAD_WALL, PAD_TOP, inset=2.5 * PX, mat_index=BEVEL, mat_top=PAD)

    # The dark pit across the middle (rows 9-18, columns 5-18, corners cut).
    pit = [(6, 19), (18, 19), (19, 17), (19, 11), (18, 9), (6, 9), (5, 11), (5, 17)]
    frustum(bm, [(ex(c), ey(r)) for c, r in pit], PAD_TOP - 0.01, PAD_TOP + 0.012, mat_index=PIT)

    # Raised vented blocks above and below the pit (columns 8-15, rows 4-8 and 19-23), the rails
    # 1.5 px above the deck.
    for s in (1, -1):
        y = lambda r: s * ey(r)  # noqa: E731
        def ybox(c0, r0, c1, r1, dz, mat, z0=PAD_TOP - 0.01):
            a, b = sorted((y(r0), y(r1)))
            box(bm, ex(c0), a, ex(c1), b, z0, PAD_TOP + dz * PX, mat)
        ybox(8, 4, 16, 5, 1.5, LIGHT)  # outer bar
        ybox(8, 5, 9, 9, 1.5, LIGHT)  # side bars
        ybox(15, 5, 16, 9, 1.5, LIGHT)
        ybox(9, 5, 15, 9, 0.4, VENT)  # dark vent
        ybox(10, 6, 14, 9, 0.75, PAD)  # the panel inside it
        ybox(12, 5, 13, 9, 1.1, RIB)  # centre rib

    # The red drum lying along X on the deck (columns 4-19, rows 10-17), a round solid as tall as
    # the sprite shows it wide: half depth DRUM_W px, half height DRUM_H px, axis at rows 13-14.
    # Each column takes the sprite's shade; the dark socket (columns 10-13, rows 12-15) is cut
    # about 1 px into its crest.
    zc = PAD_TOP + DRUM_H * PX
    hz = DRUM_H / DRUM_W
    floor = (DRUM_H * math.cos(math.asin(GROOVE / DRUM_W)) - 1.2) * PX
    profile = [(4.3, 1.6), (5.0, 2.4), (5.6, 3.0), (6.5, 3.4), (7.0, 3.85), (7.5, 4.0), (8, 4), (9, 4), (10, 4),
               (11, 4), (12, 4), (13, 4), (14, 4), (15, 4), (16, 4), (16.5, 4.0), (17.0, 3.85), (17.5, 3.4),
               (18.4, 3.0), (19.0, 2.4), (19.7, 1.6)]
    sections = []  # (x px, half depth px, grooved)
    for c, h in profile:
        if c == 10:
            sections += [(c, h, False), (c, h, True)]
        elif c == 14:
            sections += [(c, h, True), (c, h, False)]
        else:
            sections.append((c, h, 10 < c < 14))
    col_mat = {4: DARKRED, 5: FLANK, 6: FLANK, 7: FLANK, 8: BAND, 9: FLANK, 10: DARKRED, 11: REDHI, 12: CBAND,
               13: DARKRED, 14: FLANK, 15: BAND, 16: FLANK, 17: DARKRED, 18: DARKRED, 19: DARKRED}

    def face_mat(c0, c1, k, grooved):
        if grooved and k >= 12:  # the socket's walls and floor
            return SOCKET
        if c1 - c0 < 1e-6:
            return SOCKET  # the socket's end walls
        mat = col_mat.get(int(math.floor((c0 + c1) / 2)), FLANK)
        if mat == FLANK and (k >= 12 or k in (0, 11)):
            return DRUM  # the crest is a shade brighter
        return mat

    rings = []
    for i, (c, h, grooved) in enumerate(sections):
        ring = drum_ring(h * PX, h * hz * PX, grooved, floor)
        verts = [bm.verts.new((ex(c), y, zc + z)) for y, z in ring[13:]]
        if i and sections[i - 1][0] == c:  # a full and a grooved section share the ellipse's points
            rings.append(rings[-1][:13] + verts)
        else:
            rings.append([bm.verts.new((ex(c), y, zc + z)) for y, z in ring[:13]] + verts)
    n = len(rings[0])
    smooth_faces = set()
    for i in range(len(sections) - 1):
        c0, _, g0 = sections[i]
        c1, _, g1 = sections[i + 1]
        for k in range(n):
            j = (k + 1) % n
            a, b = rings[i], rings[i + 1]
            quad = []
            for v in (a[k], a[j], b[j], b[k]):
                if v not in quad:
                    quad.append(v)
            if len(quad) < 3:
                continue
            f = bm.faces.new(quad)
            f.material_index = face_mat(c0, c1, k, g0 and g1)
            if f.material_index != SOCKET:
                smooth_faces.add(f)
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        f = bm.faces.new(list(reversed(ring)) if rev else ring)
        f.material_index = DARKRED
    # Raised yellow-orange bands round it at columns 8 and 15.
    for c0 in (8, 15):
        h = 4.2
        start = len(bm.faces)
        loft_x(bm, [(ex(c0), h * PX, h * hz * PX), (ex(c0 + 1), h * PX, h * hz * PX)], 0.0, zc, sides=16,
               mat_index=BAND)
        bm.faces.ensure_lookup_table()
        smooth_faces.update(bm.faces[start:])

    # The blue lens standing in the socket on a dark post, a dome 2 px proud of the drum's crest.
    base = zc + (DRUM_H - 0.6) * PX
    box(bm, ex(10.8), ey(15.2), ex(13.2), ey(12.8), zc + floor - 0.002, base + 0.002, SOCKET)
    dome(bm, ex(12), ey(14), base, 1.4 * PX, 1.4 * PX, 2.6 * PX, sides=12, rings=4, mat_index=LENS)

    # The axle (rows 13-14) runs out from the drum's ends to the pad's left and right edges, held
    # in a bearing block whose light lips (rows 12 and 15) stand either side of it.
    for s in (1, -1):
        x0, x1 = sorted((s * ex(0.3), s * ex(5.2)))
        box(bm, x0, ey(15), x1, ey(13), 0.0, PAD_TOP + 0.015, PIT)
        xa, xb = sorted((s * ex(1), s * ex(5)))
        box(bm, xa, ey(16), xb, ey(12), PAD_TOP - 0.01, zc - 0.6 * PX, PAD)
        for r in (12, 15):
            box(bm, xa, ey(r + 1), xb, ey(r), zc - 0.6 * PX - 0.002, zc + 0.9 * PX, LIGHT)
        loft_x(bm, [(x0, 0.8 * PX, 0.8 * PX), (x1, 0.8 * PX, 0.8 * PX)], 0.0, zc, sides=8, mat_index=VENT)

    bm.normal_update()
    flags = [f in smooth_faces or f.material_index == LENS or (
        f.material_index == VENT and len(f.verts) == 4 and abs(f.normal.x) < 0.5) for f in bm.faces]
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    for poly, flag in zip(obj.data.polygons, flags):
        poly.use_smooth = flag
    return obj


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
