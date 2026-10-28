"""Gencore Phoenix (player ship, tyrian.shp#8 sprite 157 and its banking frames 153-161).

A grey fighter: a long fuselage with a faceted pointed nose, a dark glass windshield behind it, a
polished hard-surface metal hull, and two thin, knife-edged blade wings pointed at both ends, joined to
the fuselage by struts near the tail.

The game's sun only flashes on faces that tilt back towards the camera (about 27 degrees towards the
tail), so the sprite's bright streaks sit on such facets: the spine ridge and the wing ridges slope
down towards the tail, and the canopy plate and the struts have long, shallow rear chamfers.

Run: blender --background --python assets/blender/ships/ship-gencore-phoenix.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import common  # noqa: E402
from lib_b001 import px, row  # noqa: E402

NAME = "ship-gencore-phoenix"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
P = 1 / 12  # one sprite pixel


def ploft(bm, rings, paint, faces, cap_start=True, cap_end=True):
    """A flat-faced loft through rings of sprite-space points (col, row, z px), all with the same
    count (a one-point ring is a tip). Each face is recorded with paint(row, col, up), applied once
    the normals are known, so the top view can follow the sprite's pixels."""
    vs = [[bm.verts.new((px(c), row(r), z * P)) for c, r, z in ring] for ring in rings]
    for r0, r1 in zip(vs, vs[1:]):
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                f = (r0[i], r0[j], r1[0])
            else:
                f = (r0[i], r0[j], r1[j], r1[i])
            faces.append((bm.faces.new(f), paint))
    if cap_start and len(vs[0]) > 2:
        faces.append((bm.faces.new(list(reversed(vs[0]))), paint))
    if cap_end and len(vs[-1]) > 2:
        faces.append((bm.faces.new(vs[-1]), paint))


def hull_ring(r, v, d, zt, s, zs, w, zc, lo, zl, k, zb, zv=None, cx=11.5):
    """A hard-surface section across the ship at row r, symmetric about column cx: a centre deck
    strip (half width v, at zv or zt), a flat deck out to d at zt, a chamfered shoulder (s, zs), the
    chine at the silhouette (w, zc), a lower chamfer (lo, zl) and a flat keel (k, zb)."""
    zv = zt if zv is None else zv
    right = [(v, zv), (d, zt), (s, zs), (w, zc), (lo, zl), (k, zb)]
    left = [(-x, z) for x, z in reversed(right)]
    return [(cx + x, r, z) for x, z in right + left]


def build(sprite):
    coll = common.reset_collection(NAME)
    used = {}
    mats = []

    def m(i, metallic=0.3, roughness=0.45):
        """Material slot for palette index i (one slot per index)."""
        if i not in used:
            used[i] = len(mats)
            mats.append(common.palette_material(sprite, i, NAME, metallic=metallic, roughness=roughness))
        return used[i]

    # Polished grey metal, built as a hard-surface hull: flat panels with chamfered edges and crisp
    # creases, flat shaded. The sprite's near-white spots and streaks (the nose ridge, the bright
    # spot on the canopy plate, the spine, the pods' inner edges) are specular highlights on the
    # metal, not bumps: the flat panels catch the light. The windshield is a separate glossy dark
    # glass part set into a frame in the hull.
    METAL = dict(metallic=0.8, roughness=0.3)
    GLASS, DARK, HULL, LIGHTP, PLATE = (m(1, 0.2, 0.1), m(4, **METAL), m(6, **METAL), m(8, **METAL),
                                        m(10, **METAL))
    POD = STRUT = HULL
    bm = bmesh.new()
    faces = []

    # Fuselage, nose (row 1) to the engine (row 22): (row, centre strip v, deck d, deck z, shoulder
    # s and z, chine w (the silhouette) and z, lower chamfer and z, keel and z, centre strip z).
    # The nose is a faceted wedge with a crisp ridge; behind it the deck drops into a frame for the
    # windshield; the body behind the glass is a flat deck with a seam groove across it (row 13), and
    # the centre strip sinks into the rear vent (rows 18-19).
    H = [(0.55, 0.05, 0.3, 1.2, 0.5, 1.0, 0.9, 0.6, 0.6, 0.2, 0.2, 0.0, 1.3),
         (2.5, 0.05, 0.5, 2.5, 1.1, 2.1, 2.0, 0.9, 1.5, -0.5, 0.6, -0.9, 2.65),
         (4.5, 0.05, 0.65, 3.6, 1.8, 3.0, 3.0, 1.0, 2.4, -1.0, 0.9, -1.4, 3.8),
         (5.5, 0.05, 0.75, 4.1, 2.0, 3.4, 3.0, 1.0, 2.5, -1.1, 1.0, -1.5, 4.3),
         (5.75, 1.0, 2.5, 4.1, 3.2, 4.4, 4.0, 1.0, 3.3, -1.3, 1.4, -1.7, None),
         (8.5, 1.0, 2.7, 4.3, 3.4, 4.8, 4.0, 1.1, 3.5, -1.5, 1.6, -1.9, None),
         (8.65, 1.0, 2.8, 4.4, 3.9, 4.8, 5.0, 1.2, 4.2, -1.5, 1.8, -2.0, None),
         (9.5, 1.0, 2.8, 4.6, 4.0, 4.9, 5.0, 1.3, 4.3, -1.6, 1.8, -2.0, None),
         (9.65, 1.0, 2.8, 5.4, 4.0, 4.9, 5.0, 1.3, 4.3, -1.6, 1.8, -2.0, None),
         (12.6, 1.0, 2.8, 5.4, 4.0, 4.8, 5.0, 1.3, 4.3, -1.6, 1.8, -2.0, None),
         (12.7, 1.0, 2.8, 4.8, 4.0, 4.6, 5.0, 1.3, 4.3, -1.6, 1.8, -2.0, None),
         (13.3, 1.0, 2.8, 4.8, 4.0, 4.6, 5.0, 1.3, 4.3, -1.6, 1.8, -2.0, None),
         (13.4, 1.0, 2.8, 5.3, 4.0, 4.8, 5.0, 1.3, 4.3, -1.6, 1.8, -2.0, None),
         (16.4, 1.0, 2.8, 5.2, 4.0, 4.7, 5.0, 1.3, 4.3, -1.6, 1.8, -2.0, None),
         (16.6, 1.0, 2.7, 5.1, 3.4, 4.5, 4.0, 1.2, 3.5, -1.6, 1.7, -2.0, None),
         (17.5, 1.0, 2.7, 5.0, 3.4, 4.4, 4.0, 1.2, 3.5, -1.6, 1.7, -2.0, None),
         (17.6, 1.0, 2.7, 5.0, 3.4, 4.4, 4.0, 1.2, 3.5, -1.6, 1.7, -2.0, 3.9),
         (19.4, 1.0, 2.6, 4.8, 3.3, 4.2, 4.0, 1.1, 3.4, -1.5, 1.6, -1.9, 3.7),
         (19.5, 1.0, 2.6, 4.7, 3.3, 4.2, 4.0, 1.1, 3.4, -1.5, 1.6, -1.9, None),
         (22.4, 0.8, 2.0, 4.0, 2.8, 3.6, 4.0, 1.0, 3.2, -1.4, 1.4, -1.8, None)]

    def hull_paint(r, c, up):
        x = abs(c - 11.5)
        if up > 0.5 and 12.6 < r < 13.4:
            return DARK  # seam groove across the deck
        if up > 0.5 and 17.55 < r < 19.45 and x < 1.0:
            return GLASS  # floor of the rear vent
        if up > 0.5 and 17.55 < r < 19.45:
            return LIGHTP  # the lighter lips either side of the vent
        if r > 19.5:
            return DARK  # the darker tail
        return HULL

    ploft(bm, [hull_ring(*h[:12], zv=h[12]) for h in H], hull_paint, faces, cap_end=False)

    # Tail engine (rows 22-25): an angular block, darker than the hull, narrowing to the back, with
    # the nozzle cut into its end face.
    E = [(22.3, 0.8, 1.8, 3.4, 2.6, 3.0, 4.0, 0.9, 3.2, -1.2, 1.4, -1.6),
         (23.5, 0.8, 1.6, 3.2, 2.4, 2.8, 3.6, 0.8, 2.9, -1.1, 1.3, -1.5),
         (24.5, 0.6, 1.2, 2.6, 2.0, 2.2, 2.9, 0.7, 2.3, -1.0, 1.0, -1.3),
         (25.4, 0.5, 0.9, 2.0, 1.5, 1.7, 2.0, 0.6, 1.6, -0.8, 0.8, -1.0)]
    eng = [hull_ring(*e) for e in E]

    def inset(ring, k, dr):
        return [(11.5 + (c - 11.5) * k, r + dr, 0.5 + (z - 0.5) * k) for c, r, z in ring]

    eng += [inset(eng[-1], 0.6, 0.0), inset(eng[-1], 0.55, -0.9)]

    def engine_paint(r, c, up):
        return GLASS if r > 24.6 and abs(c - 11.5) < 1.3 and up < 0.6 else DARK

    ploft(bm, eng, engine_paint, faces, cap_start=False)

    # Windshield: a separate faceted wedge of dark glass set into the frame behind the nose, low at
    # its front edge (row 6) and rising to its back edge (row 9), with a flat top panel and angled
    # side panels. Its bright glint in the sprite (row 7) is the glass catching the light.
    # The top is three shallow facets (shaded smooth between them, so the glass carries a glint);
    # the edges to the side panels and the frame stay crisp.
    def glass_ring(r, zt, zs, zb, k):
        half = ((0.6 * k, zt + 0.35), (1.7 * k, zt), (2.7, zs), (2.7, zb))
        right = list(half)
        return [(11.5 + x, r, z) for x, z in right + [(-x, z) for x, z in reversed(right)]]

    glass = [glass_ring(5.8, 5.0, 4.5, 3.9, 1.0), glass_ring(7.7, 5.9, 5.0, 4.0, 0.97),
             glass_ring(9.55, 6.5, 5.3, 4.2, 0.9)]
    ploft(bm, glass, lambda r, c, up: GLASS, faces)

    # Canopy plate (rows 10-12, columns 10-12): a light, raised flat plate with chamfered edges.
    def plate(c0, c1, r0, r1, z0, z1, ch, mat, rear=1.0):
        # The rear chamfer is longer and shallower: it faces the game's sun and carries the glint.
        rings = []
        for r, k, dz in ((r0, ch, ch), (r0 + ch, 0, 0), (r1 - rear, 0, 0), (r1, ch, 0.55)):
            zt = z1 - dz
            rings.append([(c0 + k, r, z0), (c1 - k, r, z0), (c1 - k, r, zt - ch), (c1 - k - ch, r, zt),
                          (c0 + k + ch, r, zt), (c0 + k, r, zt - ch)])
        ploft(bm, rings, lambda r, c, up: mat, faces)

    plate(9.7, 12.9, 9.9, 12.5, 5.0, 6.1, 0.4, PLATE)

    # Spine ridge (rows 14-17, column 11): a straight, flat-topped strip down the back, rising at its
    # front and sloping back towards the vent so its top catches the sun.
    spine = [[(10.45, r, 5.0), (11.55, r, 5.0), (11.3, r, z), (10.7, r, z - 0.08)]
             for r, z in ((13.55, 5.5), (14.0, 6.6), (17.2, 5.15), (17.45, 5.0))]
    ploft(bm, spine, lambda r, c, up: PLATE, faces)

    # Wings: thin, knife-edged blades pointed at both ends. Each section is a wedge: a crisp ridge
    # along the inner top edge (the bright line in the sprite), a near-vertical inner face, a flat
    # upper face sloping down to a knife edge on the outer side and a lower face back up from the
    # keel to that edge. (row, outer edge, inner edge, ridge height, keel depth.)
    def pod_ring(r, o, i, t, b):
        return [(i - 1.4, r, t - 0.12), (i - 0.5, r, t), (i, r, t - 0.6), (i, r, b + 0.5), (i - 0.9, r, b),
                (o, r, 0.3)]

    # The ridge climbs from the front point to row 15 and then slopes back down towards the strut,
    # so its flat top catches the sun there (the bright inner edge in the sprite).
    tip_f = [(4.6, 8.4, 0.6)]
    tip_b = [(3.4, 24.7, 0.4)]
    pod = [tip_f] + [pod_ring(*p) for p in (
        (9.6, 2.9, 5.4, 1.4, -0.3), (11.5, 2.0, 5.5, 2.6, -0.7), (13.8, 0.7, 5.5, 3.5, -0.9),
        (15.2, 0.7, 5.5, 3.9, -0.9), (19.2, 0.7, 5.5, 2.1, -0.9), (21.8, 0.7, 5.5, 2.0, -0.9),
        (22.5, 0.9, 5.5, 1.9, -0.85), (23.0, 2.6, 5.4, 1.5, -0.6), (23.6, 2.7, 5.2, 1.1, -0.45))] + [tip_b]
    for flip in (False, True):
        rings = [[(23 - c, r, z) for c, r, z in ring][::-1] if flip else ring for ring in pod]
        ploft(bm, rings, lambda r, c, up: POD, faces)

    # Struts (rows 19-22, columns 5-8): box-section bars from the pods into the hull with a
    # chamfered top: the bright top edge in the sprite is the front chamfer catching the light.
    for a, b in ((4.0, 8.6), (23 - 8.6, 23 - 4.0)):
        sec = [(19.0, 0.6), (19.6, 1.9), (20.4, 1.9), (22.2, 1.0), (22.4, 0.4), (22.0, -1.0), (19.4, -1.0)]
        ploft(bm, [[(x, r, z) for r, z in sec] for x in (a, b)],
              lambda r, c, up: LIGHTP if up > 0.3 and r < 20.5 else STRUT, faces)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f, paint in faces:
        cen = f.calc_center_median()
        f.material_index = paint(14 - 0.5 - cen.y * 12, cen.x * 12 + 11.5, f.normal.z)
    # Smooth shading split at the creases: flat panels and chamfers stay crisp, and the polished
    # metal's sheen runs along each panel instead of flashing face by face.
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    obj.modifiers.new("edges", "EDGE_SPLIT").split_angle = math.radians(30)
    return obj


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        level = next(f for f in sprite["frames"] if f["index"] == sprite["sprites"][0]["frames"][0])
        ref = ROOT / "reference" / "models" / NAME / level["image"]
        common.render_preview([obj], out, ref, size=level["size"])


if __name__ == "__main__":
    main()
