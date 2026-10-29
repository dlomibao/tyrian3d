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


def rock_height(rx, ry, rz):
    return max(rz, 0.55 * min(rx, ry) * PX)


def canister(bm, x0, x1, ya, yb, z0, z1, c, mat, end=True):
    """A hard-edged tank along Y from ya (top of the screen) down to yb: a flat top with its long
    edges chamfered by c, and (end=True) the top end chamfered too. Units."""
    prof = [(x0, z0), (x1, z0), (x1, z1 - c), (x1 - c, z1), (x0 + c, z1), (x0, z1 - c)]
    endp = [(x0, z0), (x1, z0), (x1, z1 - 1.8 * c), (x1 - c, z1 - c), (x0 + c, z1 - c),
            (x0, z1 - 1.8 * c)]
    rings = [[bm.verts.new((x, yb, z)) for x, z in prof]]
    if end:
        rings.append([bm.verts.new((x, ya - c, z)) for x, z in prof])
        rings.append([bm.verts.new((x, ya, z)) for x, z in endp])
    else:
        rings.append([bm.verts.new((x, ya, z)) for x, z in prof])
    faces = []
    n = len(prof)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    faces.append(bm.faces.new(list(reversed(rings[0]))))
    faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = False


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
        pal(88, metallic=0.4, roughness=0.45),  # 5 purple cap top
        pal(90, metallic=0.4, roughness=0.4),  # 6 light purple canister
        pal(89, metallic=0.4, roughness=0.45),  # 7 purple mid (sides, canisters, connectors)
        pal(86, metallic=0.3, roughness=0.6),  # 8 dark purple seams and grooves
    ]
    BED, ROCK_D, ROCK, ROCK_L, BEIGE, PLATE, LIGHT, MID, SEAM = range(9)
    key = {"rock_d": ROCK_D, "rock": ROCK, "rock_l": ROCK_L, "beige": BEIGE}
    W = 24 * n
    X = lambda c: (c - W / 2) / 12  # noqa: E731
    Y = lambda r: (14 - r) / 12  # noqa: E731
    bm = bmesh.new()

    # Rock bed under the whole row.
    L.box(bm, X(0), Y(28), X(W), Y(0), -0.2, -0.03, mat=BED)

    # Boulders.
    for i, kind in enumerate(kinds):
        o = 24 * i
        for x, y, rx, ry, rz, m in ROCKS["all"] + ROCKS.get(kind, []):
            L.ellipsoid(bm, X(o + x), Y(y), -0.03, rx * PX, ry * PX, rock_height(rx, ry, rz),
                        mat=key[m], segments=12, rings=6, smooth=True)
    for i in range(n + 1):
        for x, y, rx, ry, rz, m in ROCKS["edge"]:
            L.ellipsoid(bm, X(24 * i + x), Y(y), -0.03, rx * PX, ry * PX, rock_height(rx, ry, rz),
                        mat=key[m], segments=12, rings=6, smooth=True)

    # The machine's dark base: the floor of the seams between the canisters (sprite cols 12-60).
    L.box(bm, X(12.3), Y(28), X(60.2), Y(11.5), -0.07, 0.05, mat=SEAM)

    # Canisters (x edges in pixels, light?) per tile offset; the ones under the connectors
    # (cols 20-28, 44-52) are grooved at row 23.
    zc0, zc1, c = 0.0, 0.43, 1.7 * PX
    cans = [(12.6, 19.6, MID, False), (20.0, 28.0, MID, True), (28.7, 35.9, LIGHT, False),
            (36.6, 43.6, MID, False), (44.0, 52.0, MID, True), (52.7, 59.9, LIGHT, False)]
    for x0, x1, m, grooved in cans:
        if grooved:
            # Upper section from under the connector to the groove, then a lower one beyond it.
            canister(bm, X(x0), X(x1), Y(19.5), Y(23.0), zc0, zc1, c, m, end=False)
            L.box(bm, X(x0 + 0.8), Y(23.8), X(x1 - 0.8), Y(22.9), zc0, zc1 - 0.14, mat=SEAM)
            canister(bm, X(x0), X(x1), Y(23.6), Y(28), zc0, zc1 - 0.03, c, PLATE)
        else:
            canister(bm, X(x0), X(x1), Y(17.0), Y(28), zc0, zc1, c, m, end=False)

    # Connector blocks between the caps (rows 11-20, cols 20-28 of the joint), on a lower skirt
    # that fills the space where the caps' lower edges draw back (rows 15-20).
    for i in range(1, n):
        o = 24 * i
        skirt = [(X(o - 3.4), Y(14.5)), (X(o + 3.6), Y(14.5)), (X(o + 7.5), Y(19)),
                 (X(o + 7.5), Y(20)), (X(o - 7.5), Y(20)), (X(o - 7.5), Y(19))]
        L.bevel_plate(bm, skirt, 0.0, 0.40, 0.8 * PX, (MID, MID, MID, MID))
        block = [(X(o - 3.6), Y(20)), (X(o + 3.8), Y(20)), (X(o + 3.8), Y(11)), (X(o - 3.6), Y(11))]
        L.bevel_plate(bm, block, 0.0, 0.52, 1.0 * PX, (MID, MID, MID, MID))

    # The octagonal armour cap on every tile: a vertical wall, then a chamfered rim to the top.
    for i in range(n):
        o = 24 * i
        L.bevel_plate(bm, [(X(o + cc), Y(r)) for cc, r in L.OCTAGON], 0.0, 0.66, 1.5 * PX,
                      (PLATE, MID, MID, MID))

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
