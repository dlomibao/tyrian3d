"""Mini-Missile sidekick (item 10, the level-1 pickup; tyrian.shp#8 frames 163, 182, 201): a 3D
version of its sprite.

A small missile launcher pod flying nose up the screen, 6 px wide and 13 px long on its 12x14 block.
At the front a glowing warhead (rows 2-4) pokes out of a grey launch tube (rows 4.5-8) between two guide cheeks; a raised
collar rings the tube behind its mouth (row 5), and a glass slot along the tube's top (rows 6-7,
columns 5-6, between two rails) shows the missile glowing inside. Behind the tube a 2 px glowing
feed line (rows 8-9) runs back, seated in a channel along a dark keel 4 px wide (the sprite's dark
waist), to a squat rounded engine drum (rows 10-13, about two thirds as tall as it is wide, level
with the tube) with a recessed dark nozzle at its back and a chamfered mounting lug on each flank.

The three frames only change the glow: a pulse runs back from the warhead (white-hot on 163)
through the slot to the feed line (brightest on 201). So one model covers them all, its glowing
parts recoloured per frame (palette_material frames=, DECISIONS.md D17). The grey is polished
metal in mid tones; the sprite's bright row 11 and the light left side are the shine the game's
lights make, not shape (tools/calibration/rubric.md).

Run: blender --background --python assets/blender/sidekicks/mini-missile.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "mini-missile"
SPRITE = "sidekick-mini-missile"
P = 1 / 12  # one sprite pixel
F1, F2, F3 = 163, 182, 201


def ey(r):
    """Sprite row edge of the 12x14 block to Blender Y (sprite up is +Y, block centre is 0)."""
    return (7 - r) / 12


def ring_loft(bm, secs, sides, mat):
    """common.loft with sections given as (row edge, half width px, half height px, z px)."""
    common.loft(bm, [(ey(r), w * P, h * P, z * P) for r, w, h, z in secs], sides=sides, mat_index=mat)


def box(bm, x0, x1, r0, r1, z0, z1, mat, bevel=0.0):
    """A block between columns x0..x1 (px from the centreline), rows r0..r1 and heights z0..z1 px,
    its top edges chamfered by `bevel` px."""
    b = bevel
    top = [(x0 + b, r1 - b), (x1 - b, r1 - b), (x1 - b, r0 + b), (x0 + b, r0 + b)]
    bot = [(x0, r1), (x1, r1), (x1, r0), (x0, r0)]
    vt = [bm.verts.new((x * P, ey(r), z1 * P)) for x, r in top]
    vm = [bm.verts.new((x * P, ey(r), (z1 - b) * P)) for x, r in bot]
    vb = [bm.verts.new((x * P, ey(r), z0 * P)) for x, r in bot]
    bm.faces.new(vt).material_index = mat
    bm.faces.new(list(reversed(vb))).material_index = mat
    for i in range(4):
        j = (i + 1) % 4
        if b > 0:
            bm.faces.new((vm[i], vm[j], vt[j], vt[i])).material_index = mat
        bm.faces.new((vb[i], vb[j], vm[j], vm[i])).material_index = mat


def drum_loft(bm, secs, sides, mat, n=3.2):
    """ring_loft with superellipse rings (exponent n): flatter sides and top, rounded corners, so
    a section reads as a machined drum rather than a ball."""
    rings = []
    for r, w, h, z in secs:
        ring = []
        for i in range(sides):
            a = 2 * math.pi * (i + 0.5) / sides
            c, s_ = math.cos(a), math.sin(a)
            x = w * math.copysign(abs(c) ** (2 / n), c)
            zz = z + h * math.copysign(abs(s_) ** (2 / n), s_)
            ring.append(bm.verts.new((x * P, ey(r), zz * P)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).material_index = mat
    bm.faces.new(list(reversed(rings[0]))).material_index = mat
    bm.faces.new(rings[-1]).material_index = mat


def lug(bm, s, x0, x1, r0, r1, z0, z1, taper, mat, bevel):
    """A mounting lug on side s (+1/-1): an octagonal-section block from x0 (sunk in the hull) out
    to x1 px, narrowing by `taper` (0-1) so it flares into the hull, its long edges and outer face
    chamfered by `bevel` px."""
    rc, zc = (r0 + r1) / 2, (z0 + z1) / 2
    hr, hz, b = (r1 - r0) / 2, (z1 - z0) / 2, bevel
    k = 1 - taper

    def ring(x, a, c, cut):
        pts = [(a - cut, c), (-a + cut, c), (-a, c - cut), (-a, -c + cut),
               (-a + cut, -c), (a - cut, -c), (a, -c + cut), (a, c - cut)]
        return [bm.verts.new((s * x * P, ey(rc + dr), (zc + dz) * P)) for dr, dz in pts]

    rings = [ring(x0, hr, hz, b), ring(x1 - b, hr * k, hz * k, b), ring(x1, hr * k - b, hz * k - b, b * 0.6)]
    for ra, rb_ in zip(rings, rings[1:]):
        for i in range(8):
            j = (i + 1) % 8
            bm.faces.new((ra[i], ra[j], rb_[j], rb_[i])).material_index = mat
    bm.faces.new(list(reversed(rings[0]))).material_index = mat
    bm.faces.new(rings[-1]).material_index = mat


def build(sprite):
    coll = common.reset_collection(NAME)
    metal = lambda i: common.palette_material(sprite, i, NAME, metallic=0.75, roughness=0.32)  # noqa: E731
    glow = lambda i, part, frames, s: common.palette_material(  # noqa: E731
        sprite, i, f"{NAME}-{part}", metallic=0.0, roughness=0.25, emission_strength=s, frames=frames)
    mats = [
        metal(3),   # 0 dark: nozzle throat, spine
        metal(5),   # 1 tube mouth lip, rear cap
        metal(9),   # 2 tube body
        metal(11),  # 3 collar, rails
        metal(10),  # 4 engine housing
        metal(5),   # 5 rear band
        metal(4),   # 6 keel (the sprite's dark waist)
        # The glow, recoloured per frame: the pulse runs from the warhead back to the feed line.
        # Per frame the left (lit) pixel of each row, so the pulse reads: rows 2, 3, 4 of the
        # warhead, rows 6 and 7 of the slot, rows 8 and 9 of the feed line.
        glow(127, "point", {F2: 123, F3: 119}, 2.0),       # 6 warhead point (row 2)
        glow(126, "nose", {F2: 125, F3: 121}, 1.8),        # 7 warhead nose (row 3)
        glow(123, "head", {F2: 119, F3: 114}, 1.4),        # 8 warhead base (row 4)
        # Two narrow in-between bands blend the warhead's rows into a gradient, not stripes.
        glow(124, "head-nose", {F2: 122, F3: 117}, 1.6),
        glow(127, "nose-point", {F2: 124, F3: 120}, 1.9),
        glow(120, "slot-front", {F2: 121, F3: 122}, 1.2),  # 9 slot, row 6
        glow(121, "slot-back", {F2: 124, F3: 127}, 1.2),   # 10 slot, row 7
        glow(115, "feed-front", {F2: 119, F3: 122}, 1.8),  # 11 feed line, row 8
        glow(116, "feed-back", {F2: 121, F3: 125}, 1.8),   # 12 feed line, row 9
    ]
    (DARK, LIP, TUBE, COLLAR, HOUSING, BAND, KEEL, POINT, TIP, HEAD, BLEND1, BLEND2,
     SLOT1, SLOT2, FEED1, FEED2) = range(len(mats))

    # Round parts (smooth shaded).
    rb = bmesh.new()
    # Launch tube: 6 px wide (columns 3-8), a little flatter than round. Its mouth (row 4.6) is
    # open wide so the warhead shows from above at row 4 between two guide cheeks (columns 3 and
    # 8); a raised collar rings it at row 5, and its back (row 8) closes in round the feed line.
    H = 2.5
    ring_loft(rb, [(4.75, 2.25, 1.85, 0), (4.55, 2.7, 2.2, 0), (4.75, 3.0, H, 0)], 16, LIP)
    ring_loft(rb, [(4.75, 3.0, H, 0), (7.85, 3.0, H, 0)], 16, TUBE)
    ring_loft(rb, [(7.85, 3.0, H, 0), (8.05, 2.75, 2.3, 0), (8.3, 1.7, 1.6, 0.3)], 16, BAND)
    # Collar (row 5): a raised ring just behind the mouth.
    ring_loft(rb, [(4.75, 3.05, H + 0.05, 0), (4.85, 3.3, H + 0.3, 0), (5.8, 3.3, H + 0.3, 0),
                   (5.9, 3.05, H + 0.05, 0)], 16, COLLAR)
    # Warhead: an ogive from inside the tube out to its point just past row 2 (2 px wide at row 2,
    # 4 px at rows 3-4), its base glowing at row 4 and white-hot at the tip.
    ring_loft(rb, [(5.6, 2.05, 1.9, 0), (3.75, 2.05, 1.9, 0)], 14, HEAD)
    ring_loft(rb, [(3.75, 2.05, 1.9, 0), (3.3, 1.97, 1.83, 0.03)], 14, BLEND1)
    ring_loft(rb, [(3.3, 1.97, 1.83, 0.03), (3.0, 1.85, 1.75, 0.05), (2.7, 1.63, 1.56, 0.08)], 14, TIP)
    ring_loft(rb, [(2.7, 1.63, 1.56, 0.08), (2.4, 1.36, 1.32, 0.11)], 14, BLEND2)
    ring_loft(rb, [(2.4, 1.36, 1.32, 0.11), (2.05, 0.95, 0.95, 0.15), (1.75, 0.45, 0.45, 0.15), (1.6, 0, 0, 0.15)], 14, POINT)
    # Feed line: a glowing 2 px conduit from the tube's back to the engine housing (rows 8-10),
    # lying in the keel's channel (FZ is its axis height).
    FZ = 0.3
    ring_loft(rb, [(8.1, 1.0, 1.0, FZ), (9.0, 1.0, 1.0, FZ)], 10, FEED1)
    ring_loft(rb, [(9.0, 1.0, 1.0, FZ), (10.4, 1.0, 1.0, FZ)], 10, FEED2)
    # Feed couplings: thin rings where it leaves the tube and enters the housing.
    ring_loft(rb, [(8.2, 1.2, 1.2, FZ), (8.45, 1.2, 1.2, FZ)], 10, COLLAR)
    ring_loft(rb, [(9.7, 1.2, 1.2, FZ), (9.85, 1.35, 1.35, FZ), (10.1, 1.35, 1.35, FZ)], 10, COLLAR)
    # Engine housing (rows 10-13): a squat machined drum, 6 px wide at rows 11-12 and 4 px at 10
    # and 13, about 4.2 px tall (0.7 of its width) so its top sits level with the tube's, not a
    # ball. Its top shines at row 11 in the game's light; the shape stays plain.
    HH = 2.1
    drum_loft(rb, [(9.95, 1.7, 1.25, 0), (10.15, 2.3, 1.65, 0), (10.6, 2.8, 1.95, 0), (11.1, 3.05, HH, 0),
                   (12.4, 3.05, HH, 0), (12.6, 3.0, HH - 0.05, 0)], 16, HOUSING)
    drum_loft(rb, [(12.6, 3.0, HH - 0.05, 0), (12.75, 2.88, HH - 0.15, 0), (13.4, 2.6, 1.8, 0),
                   (13.8, 2.15, 1.45, 0)], 16, BAND)
    # Nozzle: a dark throat recessed into the drum's back face.
    ring_loft(rb, [(13.75, 1.55, 1.1, 0), (13.95, 1.45, 1.0, 0), (13.55, 0.95, 0.65, 0)], 12, DARK)
    round_obj = common.mesh_object(NAME, rb, mats, coll, smooth=True)

    # Hard parts (flat shaded).
    hb = bmesh.new()
    # The slot along the tube top (rows 6-8, columns 5-6): a glass strip just proud of the tube
    # between two rails (columns 4 and 7).
    box(hb, -1.0, 1.0, 5.95, 6.95, H - 0.6, H + 0.15, SLOT1, 0.1)
    box(hb, -1.0, 1.0, 6.95, 8.05, H - 0.6, H + 0.15, SLOT2, 0.1)
    for s in (1, -1):
        x0, x1 = sorted((s * 1.0, s * 1.8))
        box(hb, x0, x1, 5.85, 8.15, H - 0.8, H + 0.45, COLLAR, 0.2)
    # Guide cheeks either side of the warhead (columns 3 and 8, rows 3.5-4.75): the tube's walls
    # run forward as two low plates with chamfered tops.
    for s_ in (1, -1):
        x0, x1 = sorted((s_ * 2.15, s_ * 3.0))
        box(hb, x0, x1, 3.45, 4.8, -1.6, 1.3, LIP, 0.3)
    # The keel (the sprite's dark waist, rows 8-9, 4 px wide): a solid dark block from inside the
    # tube's back to inside the drum, so the pod is one structure; the feed line lies in a channel
    # along its top between two low walls, its glowing top showing between them from above.
    box(hb, -2.0, 2.0, 7.7, 10.5, -1.9, -0.75, KEEL, 0.25)
    for s in (1, -1):
        x0, x1 = sorted((s * 1.05, s * 2.0))
        box(hb, x0, x1, 7.7, 10.5, -0.8, FZ + 0.7, KEEL, 0.25)
    # Mounting lugs on the drum's flanks (rows 11-13): chunky chamfered blocks sunk into the drum
    # and narrowing outwards, so they read as cast mounts, not plates.
    for s in (1, -1):
        lug(hb, s, 2.2, 3.45, 11.0, 13.1, -1.0, 0.9, 0.3, LIP, 0.22)
    hard_obj = common.mesh_object(f"{NAME}-hard", hb, mats, coll, smooth=False)
    return [round_obj, hard_obj]


def main():
    root = common.repo_root(__file__)
    sprite = common.load_sprite(root, SPRITE)
    objects = build(sprite)
    common.export_sprite_model(root, objects, f"sidekicks/{NAME}", sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        common.render_frame_previews(objects, out, sprite, root)


if __name__ == "__main__":
    main()
