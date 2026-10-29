"""Rock wall with purple octagon caps over a row of canisters (newsh2.shp 279, 281, 283): a 3D
version of its sprites.

Seen in episode 1 (level 1.3) and episode 3. Three 2x2 pieces in a row (sprite.json
`assemblyLayout`): newsh2-279 at the left end, newsh2-281 in the middle and newsh2-283 at the
right end. A machine set into a rock wall (the same wall as assembly-newsh2-273, turned the other
way): boulders (a beige one top left of each piece) along the top, a thick purple octagonal armour
cap on each piece, a connector block between each pair of caps, and a row of six upright purple
canisters under and between the caps running to the bottom edge (the ones under the connectors
have a groove across them). Feature list: assets/blender/features/assembly-newsh2-279.json.
Built whole in assembly coordinates and cut into the pieces with common.split_assembly.

Heights (sprite px above the rock bed): caps about 8, connectors about 6.5, canisters about 5.5,
boulders about half as tall as they are wide. The sides of the plates are one mid-tone colour; the
light shades them (the sprite's lit and dark rims are its lighting, not paint).

Run: blender --background --python assets/blender/enemies/assembly-newsh2-279.py [-- --preview out.png]
(the preview is the whole row; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b048 as L  # noqa: E402
from lib_b048 import common  # noqa: E402

PX = 1 / 12
NAME = "assembly-newsh2-279"
TILES = ["newsh2-279", "newsh2-281", "newsh2-283"]

# Rocks (x, y, rx, ry, rz, material key) in tile pixels, from lib_b048's "bottom" wall; rz is
# raised below so the boulders stand round (about half as tall as wide), not as flat lenses.
ROCKS = L.WALL_ROCKS["bottom"]
# Extra boulders in the notch above each connector, between the caps' tops (the sprite's grey rocks
# at columns 20-27, rows 0-6), as offsets from the joint column.
NOTCH_ROCKS = [(0.2, 4.4, 3.4, 2.2, 0.08, "rock")]

# Remodelled on the concept (assets/blender/textures/assembly-newsh2-279/concept.png, registered to
# the sprite) for the parts' shapes, but placed where the sprite puts them: the concept draws the
# caps and connectors about 2.7 px higher than the sprite's octagons (centred at row 12), and the
# sprite decides position. Assembly pixel columns / rows (edges).
# Caps: round armour drums with a notched rim, a raised middle ring and a raised inner disc.
CAP_COLS = [12.2, 36.1, 60.0]
CAP_ROW = 12.0
DY = 2.7  # px: connector parts moved down from the concept's rows with the caps
CAP_R, RING_R, DISC_R = 8.0, 5.4, 4.1
CAP_Z, RING_Z, DISC_Z, DOME_Z = 6.6, 7.3, 8.3, 8.8  # tops, px
# Canisters: round tanks lying down the screen (centre column, first row, last row, material key,
# under a connector?). The ones under the connectors end shorter and carry the sprite's groove.
# Upper ends start under the caps / the connectors' lower plate; lower ends at the sprite's bottom.
CANS = [(16.4, 16.7, 27.3, "mid", False), (24.2, 18.7, 26.6, "mid", True),
        (32.0, 16.7, 27.4, "light", False), (40.0, 16.7, 27.3, "mid", False),
        (48.0, 18.7, 26.6, "mid", True), (55.7, 16.7, 27.4, "light", False)]
CAN_R = 3.75  # px (7.5 px wide, as the concept and the sprite draw them)
CAN_AXIS = 2.0  # px: the tanks sit half sunk in the machine's base, tops at about 5.75 px


def rock_height(rx, ry, rz):
    return max(rz, 0.55 * min(rx, ry) * PX)


def flat_caps(bm, n, smooth):
    """Faces added since index n: smooth sides, flat (sharp) end caps."""
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n:]:
        f.smooth = smooth and len(f.verts) == 4


def ngon(cx, cy, r, sides, rot=0.0):
    return [(cx + r * math.cos(rot + 2 * math.pi * k / sides), cy + r * math.sin(rot + 2 * math.pi * k / sides))
            for k in range(sides)]


def build(sprite, name, tag, kinds):
    n = len(kinds)
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(5, metallic=0.0, roughness=0.9),  # 0 rock bed and crevices
        pal(7, metallic=0.0, roughness=0.85),  # 1 rock (dark)
        pal(8, metallic=0.0, roughness=0.85),  # 2 rock
        pal(10, metallic=0.0, roughness=0.8),  # 3 rock (light)
        pal(170, metallic=0.0, roughness=0.8),  # 4 beige stone
        pal(88, metallic=0.4, roughness=0.45),  # 5 purple cap tops
        pal(90, metallic=0.15, roughness=0.5),  # 6 light purple canister (less metallic so it reads lighter than 89)
        pal(89, metallic=0.4, roughness=0.45),  # 7 purple mid (sides, canisters, connectors)
        pal(86, metallic=0.3, roughness=0.6),  # 8 dark purple seams, grooves, recesses
        pal(173, metallic=0.0, roughness=0.5, emission_strength=0.5),  # 9 canister lenses (dim, recessed)
        pal(172, metallic=0.0, roughness=0.2, emission_strength=1.2),  # 10 small lamps on the caps
    ]
    BED, ROCK_D, ROCK, ROCK_L, BEIGE, PLATE, LIGHT, MID, SEAM, LAMP, SLIT = range(11)
    key = {"rock_d": ROCK_D, "rock": ROCK, "rock_l": ROCK_L, "beige": BEIGE, "mid": MID, "light": LIGHT}
    W = 24 * n
    X = lambda c: (c - W / 2) / 12  # noqa: E731
    Y = lambda r: (14 - r) / 12  # noqa: E731
    P = lambda pts: [(X(c), Y(r)) for c, r in pts]  # noqa: E731
    Z = lambda h: h * PX  # noqa: E731
    bm = bmesh.new()

    def rock(c, r, rx, ry, rz, m):
        # Boulders hidden under a cap or a connector are left out.
        if any(math.hypot(c - cc, r - CAP_ROW) + max(rx, ry) < CAP_R + 0.5 for cc in CAP_COLS):
            return
        L.ellipsoid(bm, X(c), Y(r), -0.03, rx * PX, ry * PX, rock_height(rx, ry, rz),
                    mat=key[m], segments=10, rings=5, smooth=True)

    # Rock bed under the whole row.
    L.box(bm, X(0), Y(28), X(W), Y(0), -0.2, -0.03, mat=BED)

    # Boulders (the sprite's rock wall round the machine).
    for i, kind in enumerate(kinds):
        o = 24 * i
        for x, y, rx, ry, rz, m in ROCKS["all"] + ROCKS.get(kind, []):
            rock(o + x, y, rx, ry, rz, m)
    for i in (0, n):  # the joints between pieces are under the connectors
        for x, y, rx, ry, rz, m in ROCKS["edge"]:
            rock(24 * i + x, y, rx, ry, rz, m)
    for i in range(1, n):
        for x, y, rx, ry, rz, m in NOTCH_ROCKS:
            rock(24 * i + x, y, rx, ry, rz, m)

    # The machine's dark base: the floor of the seams between the canisters.
    L.box(bm, X(12.3), Y(28), X(59.8), Y(13.5), -0.07, Z(0.6), mat=SEAM)

    # Canisters: round tanks lying down the screen, with a raised collar band (row 20.4-21.4), a
    # dark rim ring at the lower end and a glowing lens in its end face (the concept's lamps).
    za = Z(CAN_AXIS)
    r = CAN_R * PX
    for c, r0, r1, m, grooved in CANS:
        x = X(c)
        body = []
        if grooved:
            # Rounded top end coming out from under the connector's lower plate.
            body = [(x, Y(r0), za, r * 0.8, r * 0.8), (x, Y(r0 + 0.6), za, r, r)]
        else:
            body = [(x, Y(r0), za, r, r)]
        segs = [body + [(x, Y(r1 - 0.9), za, r, r)]]
        if grooved:
            # The sprite's groove across the tank (row 23): the tank in two lengths with a thin dark
            # neck between them.
            segs = [body + [(x, Y(22.9), za, r, r)], [(x, Y(23.6), za, r, r), (x, Y(r1 - 0.9), za, r, r)]]
            k = len(bm.faces)
            L.sweep(bm, [(x, Y(22.8), za, r * 0.82, r * 0.82), (x, Y(23.7), za, r * 0.82, r * 0.82)],
                    sides=12, mat=SEAM)
            flat_caps(bm, k, True)
        for pts in segs:
            k = len(bm.faces)
            L.sweep(bm, pts, sides=12, mat=key[m])
            flat_caps(bm, k, True)
        # Collar band.
        k = len(bm.faces)
        L.sweep(bm, [(x, Y(20.4), za, r * 1.05, r * 1.05), (x, Y(21.4), za, r * 1.05, r * 1.05)],
                sides=12, mat=key[m])
        flat_caps(bm, k, True)
        # Dark rim ring, chamfered to the end face, and the lens.
        k = len(bm.faces)
        L.sweep(bm, [(x, Y(r1 - 0.9), za, r * 1.03, r * 1.03), (x, Y(r1 - 0.2), za, r * 1.03, r * 1.03),
                     (x, Y(r1), za, r * 0.85, r * 0.85)], sides=12, mat=SEAM)
        flat_caps(bm, k, True)
        k = len(bm.faces)
        L.sweep(bm, [(x, Y(r1 - 0.1), za + 0.15 * r, r * 0.2, r * 0.2), (x, Y(r1 + 0.05), za + 0.15 * r, r * 0.18, r * 0.18)],
                sides=8, mat=LAMP, smooth=False)

    # Connectors between the caps (the concept's coupling blocks, moved down DY with the caps): a raised
    # beam across the top (concept rows 6.8-10) with a lug at its right end, a dark bay below it holding two small pipes and a
    # junction box (rows 10-14), and a lower plate widening down to the canisters (rows 13.4-16.3).
    Yc = lambda r: Y(r + DY)  # noqa: E731
    Pc = lambda pts: [(X(c), Yc(r)) for c, r in pts]  # noqa: E731
    for i in range(1, n):
        o = 24 * i
        L.box(bm, X(o - 3.8), Yc(16.0), X(o + 3.8), Yc(9.5), 0.0, Z(3.0), mat=SEAM)
        for rr in (11.0, 12.5):
            k = len(bm.faces)
            L.sweep(bm, [(X(o - 3.8), Yc(rr), Z(3.4), 0.5 * PX, 0.5 * PX), (X(o + 3.8), Yc(rr), Z(3.4), 0.5 * PX, 0.5 * PX)],
                    sides=6, mat=MID, smooth=True)
            flat_caps(bm, k, True)
        L.bevel_plate(bm, Pc([(o - 0.6, 10.4), (o + 1.6, 10.4), (o + 1.6, 13.0), (o - 0.6, 13.0)]), 0.0, Z(4.3),
                      0.4 * PX, (MID, MID, MID, MID))
        L.bevel_plate(bm, Pc([(o - 3.6, 13.4), (o + 3.6, 13.4), (o + 4.6, 14.8), (o + 4.6, 16.3), (o - 4.6, 16.3),
                             (o - 4.6, 14.8)]), 0.0, Z(5.2), 0.7 * PX, (MID, MID, MID, MID))
        L.bevel_plate(bm, Pc([(o - 3.4, 6.8), (o + 2.6, 6.8), (o + 2.6, 10.1), (o - 3.4, 10.1)]), 0.0, Z(6.8),
                      0.8 * PX, (PLATE, MID, MID, MID))
        L.bevel_plate(bm, Pc([(o + 2.6, 6.8), (o + 3.9, 6.8), (o + 3.9, 8.4), (o + 2.6, 8.4)]), 0.0, Z(6.2),
                      0.4 * PX, (MID, MID, MID, MID))

    # The armour caps: a round drum with eight notched tabs round its rim, a raised middle ring and
    # a raised inner disc chamfered to a low dome; a slatted grille cut into the right of the ring
    # and small lamps round the disc.
    for cc in CAP_COLS:
        cx, cy = X(cc), Y(CAP_ROW)
        L.bevel_plate(bm, ngon(cx, cy, CAP_R * PX, 20, math.pi / 20), 0.0, Z(CAP_Z), 1.0 * PX,
                      (PLATE, MID, MID, MID))
        for k in range(8):
            a = math.pi / 2 + k * math.pi / 4
            hw = (3.6 if k in (0, 4) else 1.5) * PX
            ra, rb = (CAP_R - 1.0) * PX, (CAP_R + 0.75) * PX
            u = (math.cos(a), math.sin(a))
            t = (-u[1], u[0])
            quad = [(cx + u[0] * rr + t[0] * s, cy + u[1] * rr + t[1] * s)
                    for rr, s in ((ra, -hw), (rb, -hw), (rb, hw), (ra, hw))]
            L.bevel_plate(bm, quad, 0.0, Z(CAP_Z - 0.6), 0.4 * PX, (MID, MID, MID, MID))
        L.bevel_plate(bm, ngon(cx, cy, RING_R * PX, 18, math.pi / 18), Z(CAP_Z - 0.5), Z(RING_Z), 0.5 * PX,
                      (PLATE, MID, MID, MID))
        L.bevel_plate(bm, ngon(cx, cy, DISC_R * PX, 16, math.pi / 16), Z(RING_Z - 0.5), Z(DISC_Z), 0.5 * PX,
                      (PLATE, MID, MID, MID))
        L.bevel_plate(bm, ngon(cx, cy, (DISC_R - 0.9) * PX, 12, math.pi / 12), Z(DISC_Z - 0.3), Z(DOME_Z), 0.6 * PX,
                      (PLATE, PLATE, PLATE, PLATE))
        # Grille: a dark recess in a raised frame, with two slats (concept cols +5.5..+7.5).
        gx0, gx1, gy0, gy1 = cc + 5.5, cc + 7.5, CAP_ROW - 1.8, CAP_ROW + 1.4
        L.box(bm, X(gx0), Y(gy1), X(gx1), Y(gy0), Z(CAP_Z - 0.6), Z(CAP_Z + 0.5), mat=MID)
        L.box(bm, X(gx0 + 0.4), Y(gy1 - 0.4), X(gx1 - 0.4), Y(gy0 + 0.4), Z(CAP_Z - 0.5), Z(CAP_Z + 0.55),
              mat=SEAM)
        for s in range(2):
            ry = gy0 + 0.9 + 1.2 * s
            L.box(bm, X(gx0 + 0.6), Y(ry + 0.35), X(gx1 - 0.6), Y(ry), Z(CAP_Z + 0.4), Z(CAP_Z + 0.7), mat=MID)
        # Lamps: slits above and below the disc on the ring, on the rim at the bottom and at the
        # lower left and right of the ring.
        for dx, dy, z, w in ((0, -4.8, RING_Z, 0.7), (0, 4.8, RING_Z, 0.7), (0, 7.4, CAP_Z - 0.6, 0.7),
                             (-4.6, 4.4, CAP_Z, 0.5), (4.6, 4.4, CAP_Z, 0.5)):
            L.box(bm, X(cc + dx - w), Y(CAP_ROW + dy + 0.3), X(cc + dx + w), Y(CAP_ROW + dy - 0.3),
                  Z(z - 0.3), Z(z + 0.1), mat=SLIT)

    obj = L.to_object(name, bm, mats, coll)
    centres = [(24 * i + 12 - W / 2, 0) for i in range(n)]
    return obj, centres


def main():
    root = common.repo_root(__file__)
    pieces = list(dict.fromkeys(TILES))
    sprite = L.merged_sprite(root, pieces)
    obj, centres = build(sprite, NAME, NAME.replace("assembly-", "a"), ["left", "mid", "right"])
    layout = [(t, cx, cy) for t, (cx, cy) in zip(TILES, centres)]
    parts = common.split_assembly(obj, layout)
    for p in pieces:
        data = common.load_sprite(root, p)
        common.export_sprite_model(root, [parts[p]], f"enemies/{p}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref, size = L.composite_png(root, TILES, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), str(ref), size=size, view_px=480)
        for p in pieces:
            data = common.load_sprite(root, p)
            img = root / "reference" / "models" / p / data["frames"][0]["image"]
            common.render_preview([parts[p]], str(out.parent / f"{p}.png"), str(img), size=2)


if __name__ == "__main__":
    main()
