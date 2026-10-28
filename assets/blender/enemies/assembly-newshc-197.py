"""Green tank bar (newshc.shp frames 197/201/205 and 199/203/207, two pieces): a 3D version of
its sprites.

Seen in episode 1 (level 1.19) and 3 (levels 3.6 and 3.23), at the tail of a column of enemies.
Two 2x2 enemies side by side make one 48x28 px bar (sprite.json `assemblyLayout`; the other
pieces in that layout are separate enemies with their own models): two green tanks lying across
the screen either side of a pink spine block, a pink bar beneath them with a bulb at each end,
dark purple fins hanging below, and a red light between the fins. The three frames of each piece
only brighten the red light (dark red, red, orange; the pixels round it brighten a step or two
with it), so one model per piece covers them: the light changes palette colour on each frame
(palette_material frames=).

The bar is mirror symmetric about the seam between the pieces, so the left half is built
(lib_b031.stock_half, shared with the big gun's stock newshc-269) and mirrored, then cut into
the two pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshc-197.py [-- --preview out.png]
(the preview is the whole bar; each piece also gets <piece>.png next to it).
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b031 as lib  # noqa: E402

NAME = "assembly-newshc-197"
ROOT = common.repo_root(__file__)
PIECES = ["newshc-197", "newshc-199"]
# Assembly image: 48 x 28 px, newshc-197 in columns 0-23 and newshc-199 in 24-47; its centre
# (the seam, screen x 69, y 123) is the Blender origin.
CX0, CY0 = 69, 123
WIDTH = 48


def xtube(bm, points, sides, mat, xy):
    """Like lib_b031.tube for a path along the columns, but with every ring square to the columns
    (lib.tube tilts rings to a path that bends, which folds a short cap whose centre row moves).
    Closed at its first ring, open at its last."""
    w, h = xy
    rings = []
    for c, r, hw, hh, z in points:
        x, y = lib.X(c, w), lib.Y(r, h)
        if hw == 0 and hh == 0:  # a tip
            rings.append([bm.verts.new((x, y, lib.P(z)))])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new((x, y + lib.P(hw) * math.cos(a), lib.P(z) + lib.P(hh) * math.sin(a))))
        rings.append(ring)
    lib._join(bm, rings, mat, True, True, False)


def shade_tank(bm, faces, m, xy, axis):
    """Paint the tank's faces in bands by where they show from above, as the sprite shades it: a
    light row along the back of the crown (row 3), the mid green over the top, a darker green on
    the front slope (row 8) and the dark edge rows (2 and 9) on the steep sides and underneath."""
    w, h = xy
    for f in faces:
        cen = f.calc_center_median()
        c = cen.x * 12 + w / 2
        # The axis (row, z in px) under this face, for the outward normal.
        _, ar, az = axis[-1]
        for (c0, r0, z0), (c1, r1, z1) in zip(axis, axis[1:]):
            if c0 <= c <= c1:
                t = (c - c0) / (c1 - c0)
                ar, az = r0 + (r1 - r0) * t, z0 + (z1 - z0) * t
                break
        # Angle round the axis, 0 straight up, positive towards the back (up the sprite). On the
        # full 4 px radius the sprite's bands fall at: row 3 (light) 21-49 degrees back, row 8
        # (darker) 28-46 degrees forward, the outline rows beyond; banding by angle keeps the
        # bands concentric on the domed end too.
        dy = cen.y - (h / 2 - ar) / 12
        dz = cen.z - az / 12
        if len(f.verts) != 4:  # the end cap
            k = "tank_edge"
        else:
            th = math.degrees(math.atan2(dy, dz))
            if th > 49 or th < -46:
                k = "tank_edge"
            elif th > 21:
                k = "tank_hi"
            elif th < -28:
                k = "tank_lo"
            else:
                k = "tank"
        f.material_index = m[k]


def shade_bar(bm, faces, m, xy, pts, pz):
    """Paint the pipe in the sprite's bands seen from above (by the angle round its axis, forward
    positive): along the shaft row 10 (back) 88, the crown row 11 89-90, the front row 12 87 and
    the dark row 13 under it; over the bulb (columns 0-7) a light crown (rows 11-12, 90-94) between
    89 behind and 85-88 in front. Lit renders read a step darker than the sprite, so the crown and
    front take the lighter of the sprite's tones."""
    w, h = xy
    for f in faces:
        cen = f.calc_center_median()
        c = cen.x * 12 + w / 2
        ar = pts[-1][1]
        for p0, p1 in zip(pts, pts[1:]):
            if p0[0] <= c <= p1[0]:
                t = (c - p0[0]) / ((p1[0] - p0[0]) or 1)
                ar = p0[1] + (p1[1] - p0[1]) * t
                break
        dy = (h / 2 - ar) / 12 - cen.y  # forward of the axis
        dz = cen.z - pz / 12
        fwd = math.degrees(math.atan2(dy, dz))
        # (upper angle limit, palette index): a ramp a step or so at a time so the bands shade the
        # pipe round rather than in facets. Pixel centres seen from above fall at about -39 (row
        # 10), -6 (11), 25 (12) and 71 (13) degrees on the shaft; -55 (row 10), -29, -9, 9, 29 and
        # 55 (row 15) on the bulb.
        if c < 7.0:  # the bulb
            bands = ((-62, 88), (-42, 89), (-36, 91), (-18, 93), (0, 91), (18, 89), (24, 88), (40, 87),
                     (50, 85), (999, 83))
        else:
            bands = ((-50, 88), (-28, 89), (-14, 90), (14, 91), (22, 89), (36, 88), (50, 87), (64, 85),
                     (999, 83))
        f.material_index = next(m[f"p{i}"] for lim, i in bands if fwd < lim)


def wedge(bm, c0, r0, c1, r1, z0, ztop, mat, xy, dzdc=0.0, dzdr=0.0):
    """A block over pixel edges c0..c1, r0..r1 from z0 up to a sloping top: ztop at (c0, r0),
    changing by dzdc per column and dzdr per row (pixels). A top tilted towards the front (+r) or
    the right (+c) shows its own colour from above; a flat one catches the studio light's sheen."""
    w, h = xy
    corners = [(c0, r0), (c1, r0), (c1, r1), (c0, r1)]
    pts = [(lib.X(c, w), lib.Y(r, h), ztop + (c - c0) * dzdc + (r - r0) * dzdr) for c, r in corners]
    pts.reverse()  # counter-clockwise from above
    bottom = [bm.verts.new((x, y, lib.P(z0))) for x, y, _ in pts]
    top = [bm.verts.new((x, y, lib.P(z))) for x, y, z in pts]
    fs = [bm.faces.new(top), bm.faces.new(list(reversed(bottom)))]
    for i in range(4):
        j = (i + 1) % 4
        fs.append(bm.faces.new((bottom[i], bottom[j], top[j], top[i])))
    for f in fs:
        f.material_index = mat
        f.smooth = False


def louvres(bm, c0, r0, c1, r1, z0, ztop, mat, xy):
    """A block whose top is a row of 1 px louvres (cut at whole columns, so the seam between the
    pieces falls between two), each sloping 20 degrees down to the right about height ztop: a
    flat top facing the camera catches the studio light's grey sheen, these keep their colour."""
    k = math.tan(math.radians(20.0))
    cuts = [c0] + [float(c) for c in range(math.floor(c0) + 1, math.ceil(c1))] + [c1]
    for a, b in zip(cuts, cuts[1:]):
        wedge(bm, a, r0, b, r1, z0, ztop + k * (b - a) / 2, mat, xy, dzdc=-k)


def half(bm, m, w=WIDTH):
    """The left half of the bar (columns 0-24, the seam at 24), built here rather than with
    lib_b031.stock_half so this model's proportions can follow its own sprite: an 8 px round tank
    (rows 2-10), a round pipe (rows 10-13) swelling into a bulb at its outer end (rows 10-15),
    a dark grille block with rounded ribs and dark slots cut between them (columns 7-21, rows
    13-20), and a dark notch where the pipe meets the light. The spine block and the light are
    built whole in build(), after mirroring, so no faces meet on the mirror plane."""
    xy = (w, lib.H)
    # Tank: a cylinder 8 px across (rows 2-10, the sprite's outline rows included), axis at z 0.5,
    # rounded at its outer end (the sprite's tank starts at column 0 on rows 5-9).
    tz, tr = 0.5, 4.0
    # Its outer end follows the sprite's outline: the lower edge stays on row 10 while the upper
    # edge curves in from row 2 (column 4.5) to row 5 (column 0), so the end is a dome that leans
    # forward rather than one centred on the axis.
    top = [(0.0, 5.0), (0.5, 4.6), (1.0, 4.1), (1.6, 3.55), (2.5, 3.0), (3.5, 2.6), (4.5, 2.15),
           (5.5, 2.0), (21.0, 2.0)]

    def top_at(c):
        for (c0, t0), (c1, t1) in zip(top, top[1:]):
            if c <= c1:
                return t0 + (t1 - t0) * (c - c0) / (c1 - c0)
        return top[-1][1]

    # The end is a dome DOME px deep (an elliptical profile ending in a tip on the axis) inside
    # that outline, so it shows rounded in every view rather than as a flat end face, while the
    # pixel column 0 (centre 0.5) is still covered on rows 5-9.
    dome = 1.5
    pts = []
    for c in (0.0, 0.06, 0.2, 0.45, 0.75, 1.1, 1.5, 2.5, 3.5, 4.5, 5.5, 21.0):
        t = top_at(c)
        bot = 10.0 + 0.8 * max(0.0, min(1.0, (4.5 - c) / 1.5))  # the dark row 10 under the end (cols 0-3)
        hw = (bot - t) / 2
        u = min(1.0, c / dome)
        s = math.sqrt(max(0.0, 1.0 - (1.0 - u) ** 2))
        z = tz + (tr - hw) * 0.35
        pts.append((c, t + hw, hw * s, hw * s, z))
    first = len(bm.faces)
    xtube(bm, pts, sides=20, mat=m["tank"], xy=xy)
    bm.faces.ensure_lookup_table()
    shade_tank(bm, bm.faces[first:], m, xy, [(c, r, z) for c, r, _, _, z in pts])
    for c in (16.0, 18.0):  # the two dark rings (columns 16 and 18)
        lib.loft_x(bm, 6.0, [(c, tr + 0.15, tr + 0.15, tz), (c + 1.0, tr + 0.15, tr + 0.15, tz)],
                   sides=20, mat=m["ring"], xy=xy)
    # Pipe: one round tube 3.8 px across and 4.4 px tall (rows 9.8-13.6) whose outer end swells
    # into a 6 px bulb (columns 0-8, rows 9.8-15.8), on one axis at z -0.3. Under the spine it
    # narrows to rows 10-12 so the dark notch on row 12 (columns 22-25) shows below it.
    pz = -0.3
    # Its outer end is rounded off to a tip rather than a flat end face.
    bar_pts = [(0.0, 12.15, 0.0, 0.0, pz), (0.1, 12.15, 1.1, 1.2, pz), (0.3, 12.15, 1.6, 1.75, pz),
               (0.6, 12.2, 1.8, 2.2, pz), (1.5, 12.6, 2.3, 2.7, pz),
                  (2.4, 13.0, 3.05, 3.05, pz), (5.0, 13.0, 3.05, 3.05, pz), (6.6, 12.8, 2.85, 2.85, pz),
                  (8.0, 11.7, 1.9, 2.2, pz), (20.6, 11.7, 1.9, 2.2, pz), (21.8, 11.1, 1.25, 1.6, pz),
                  (24.0, 11.1, 1.25, 1.6, pz)]
    first = len(bm.faces)
    xtube(bm, bar_pts, sides=24, mat=m["bar"], xy=xy)
    bm.faces.ensure_lookup_table()
    shade_bar(bm, bm.faces[first:], m, xy, bar_pts, pz)
    # Its highlight line along the top (row 11, near-white over the bulb).
    lib.loft_x(bm, 11.0, [(2.2, 0.0, 0.0, 2.05), (3.0, 0.55, 0.3, 2.15), (7.0, 0.55, 0.3, 2.15),
                          (8.6, 0.5, 0.25, 1.85), (18.0, 0.5, 0.25, 1.85), (18.8, 0.0, 0.0, 1.8)],
               sides=6, mat=m["bar_hi"], xy=xy)
    # Grille block: a dark body (columns 7-21, rows 13-20) under five rounded ribs (columns 7-12,
    # 13, 15, 17 and 19-21; the sprite shades each light in the middle and dark at its sides) with
    # 1 px slots between them down to dark floors (columns 12, 14, 16, 18), open at the front.
    top, floor, bot = 0.0, -1.8, -3.5
    lib.slab(bm, [(7.0, 13.0), (21.5, 13.0), (21.5, 14.0), (24.0, 14.0), (24.0, 18.0), (21.0, 18.0),
                  (21.0, 19.0), (19.0, 19.0), (19.0, 20.0), (7.0, 20.0)], bot, floor, mat=m["fin_body"], xy=xy)
    ribs = [(7.0, 12.0, "fin_hi"), (13.0, 14.0, "fin"), (15.0, 16.0, "fin"), (17.0, 18.0, "fin"),
            (19.0, 21.0, "fin_hi")]
    for a, b, k in ribs:
        r1 = 19.95 if b <= 19.0 else 18.95
        hw = (b - a) / 2 + (0.1 if a > 7.0 else 0.0)
        c = (a + b) / 2 - (0.05 if a == 7.0 else 0.0)
        # A rounded-box tube on the slot floor: its lower half is buried in the body.
        lib.loft_y(bm, c, [(13.0, hw, top - floor, floor), (r1, hw, top - floor, floor)],
                   sides=10, power=0.7, mat=m[k], xy=xy)
    # (The slot floors go in after mirroring, all sloping the same way: see build().)
    # (The dark notch under the spine is built whole in build(), see there.)


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshc197"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        # Indices are the sprite's own tones for each part (tank 34-43 in bands, pipe 83-93 in
        # bands, spine 89-92, ribs 83-88), a step on the light side where the lit render reads
        # darker than the sprite (ribs 87/88, the pipe's crown 91, the light's rim 117).
        pal(41, metallic=0.0, roughness=0.6),  # 0 green tanks
        pal(36, metallic=0.1, roughness=0.55),  # 1 dark green rings
        pal(89, metallic=0.05, roughness=0.5),  # 2 pink pipe
        pal(93, metallic=0.1, roughness=0.35),  # 3 pale pipe highlight
        pal(82, metallic=0.05, roughness=0.6),  # 4 grille body
        pal(87, metallic=0.0, roughness=0.5),  # 5 grille ribs: lilac like the pipe's shade
        pal(88, metallic=0.0, roughness=0.5),  # 6 lighter grille ribs
        pal(90, metallic=0.05, roughness=0.45),  # 7 spine
        pal(80, metallic=0.0, roughness=0.8),  # 8 slot floors and notch
        # 9 red light's rim and 10 its core, sunk inside it: the core is darker than the rim on
        # 197/199 and brightens past it on 201/203 (red) and 205/207 (orange)
        common.palette_material(sprite, 117, f"{tag}-rim", metallic=0.0, roughness=0.9, emission_strength=2.0,
                                frames={205: 118, 207: 118}),
        common.palette_material(sprite, 113, f"{tag}-light", metallic=0.0, roughness=0.9, emission_strength=4.0,
                                frames={201: 119, 203: 119, 205: 123, 207: 123}),
        pal(91, metallic=0.05, roughness=0.4),  # 11 spine's lit top
        pal(43, metallic=0.0, roughness=0.6),  # 12 tanks' light crown (sprite row 3)
        pal(40, metallic=0.0, roughness=0.6),  # 13 tanks' front slope (row 8)
        pal(34, metallic=0.0, roughness=0.7),  # 14 tanks' dark edges (rows 2 and 9)
        pal(83, metallic=0.05, roughness=0.6),  # 15 the pipe's dark underside (row 13)
        pal(85, metallic=0.05, roughness=0.55),  # 16 and above it
    ]
    slots = {"tank": 0, "tank_hi": 12, "tank_lo": 13, "tank_edge": 14, "ring": 1, "bar": 2, "bar_hi": 3, "fin_body": 4, "fin": 5, "fin_hi": 6, "spine": 7,
             "slot": 8,
             # the pipe's bands (shade_bar), by palette index
             "p83": 15, "p85": 16, "p87": 5, "p88": 6, "p89": 2, "p90": 7, "p91": 11, "p93": 3}
    xy = (WIDTH, lib.H)
    bm = bmesh.new()
    half(bm, slots)
    lib.mirror_x(bm, 24.0, xy=xy)
    # Spine block (columns 20-28, rows 1-10.3), standing 2 px proud of the tanks' crown (4.5 px):
    # sides in the spine colour, a lighter bevelled top.
    lib.slab(bm, [(20.0, 1.0), (28.0, 1.0), (28.0, 10.3), (20.0, 10.3)], -3.0, 5.8, mat=7, xy=xy)
    lib.slab(bm, [(20.0, 1.0), (28.0, 1.0), (28.0, 10.3), (20.0, 10.3)], 5.8, 6.6, mat=11, bevel=0.7, xy=xy)
    # Red light between the grille halves (columns 21-27, rows 14-18): a dark red rim round a
    # glowing core (rows 15-17) sunk 1.2 px inside it.
    # Both have louvred tops (see louvres()).
    rim_top, core_top = 0.2, -1.0
    for c0, r0, c1, r1 in ((21.0, 14.0, 27.0, 15.0), (21.0, 17.0, 27.0, 18.0), (21.0, 15.0, 21.6, 17.0),
                           (26.4, 15.0, 27.0, 17.0)):
        louvres(bm, c0, r0, c1, r1, -2.0, rim_top, 9, xy)
    louvres(bm, 21.6, 15.0, 26.4, 17.0, -2.0, core_top, 10, xy)
    # Dark notch under the spine where the pipe meets the light (sprite row 12, columns 22-25).
    louvres(bm, 21.6, 12.0, 26.4, 12.95, -2.0, 0.2, 8, xy)
    # Slot floors between the ribs (columns 12, 14, 16, 18 and their mirror images): near-black,
    # each sloping down to the right a little.
    floor = -1.8
    for a, b in ((12.0, 13.0), (14.0, 15.0), (16.0, 17.0), (18.0, 19.0)):
        for c0, c1 in ((a, b), (WIDTH - b, WIDTH - a)):
            wedge(bm, c0 + 0.1, 13.2, c1 - 0.1, 19.8 if b <= 19.0 else 18.8, floor - 0.2, floor + 0.45,
                  8, xy, dzdc=-0.36)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    out = lib.preview_arg()
    if out:
        out = Path(out)
        # The bar in the middle of a 48 x 56 image (the 24:28 shape render_preview expects).
        ref = lib.composite_png(ROOT, layout, Path(tempfile.mkdtemp()) / "assembly.png", 48, 56, 24, 28)
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)
    out = lib.frames_arg()
    if out:  # every frame of each piece, one row each: <png> with the piece's name appended
        out = Path(out)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            common.render_frame_previews([pieces[name]], str(out.with_name(f"{out.stem}-{name}.png")), data, ROOT)


if __name__ == "__main__":
    main()
