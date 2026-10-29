"""Single Shot Option (sidekick item 1, tyrian.shp#8 frames 168, 187, 206): a 3D version of its sprite.

The level-1 pickup option: a small gun pod flying beside the player's ship, nose up the screen. A
round grey drum hull (sprite columns 3-8, rows 4-11) girdled by three raised trim rings (the light
bands across it at rows 5, 7 and 9), a round sponson tube hugging each flank (columns 1-2 and 9-10,
lit down their outer edge) on a solid fairing, a bright collar in front of the hull (rows 2-3) behind
a dark seam (row 4), and a stubby cannon (columns 4-7, rows 0-1) with a dark groove (row 1) behind
a polished muzzle ring and a black bore. The black pixel at the tail (row 11) is an exhaust: a dark
nozzle in the tapered tail cap.

The sprite draws its light (bright upper-left, a dark outline ring); the model leaves that to the
game: polished metal in mid-tone greys, the near-white spots (rows 2 and 5) are sheen.

Animation: after each shot the game plays 168, 187, 206, 187. On 187 and 206 the whole gun recoils
1 and 2 px down the screen while the tail stays put (the hull telescopes), and a muzzle flash shows
in front of the barrel (2 px on 187, a 3 px wide, 2 px long burst on 206). So each frame is its own
model (DECISIONS.md D17, like enemies/newsh2-229.py): single-shot-option (168),
single-shot-option-f2 (187), single-shot-option-f3 (206), each with its own flash.

Run: blender --background --python assets/blender/sidekicks/single-shot-option.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "single-shot-option"
REF = f"sidekick-{NAME}"
ROOT = common.repo_root(__file__)
P = 1 / 12  # one sprite pixel
# (frame, recoil px, model suffix)
FRAMES = [(168, 0, ""), (187, 1, "-f2"), (206, 2, "-f3")]


def X(c):
    """Sprite column edge of the 12x14 block to Blender X (the model is centred on the block)."""
    return (c - 6) * P


def Y(r):
    """Sprite row edge to Blender Y (sprite up is +Y)."""
    return (7 - r) * P


def recoiled(r, s):
    """Where row edge r of frame 168 sits after an s px recoil: the gun moves s px down the screen,
    the tail (row 11 on) stays, and the hull between them telescopes."""
    t = min(1.0, max(0.0, (11.0 - r) / 3.0))
    return r + s * t


def drum(bm, sections, c, sides, mat, s, cap=True):
    """Loft a round part along the sprite's rows: sections are (row edge, half width px, half height
    px, z centre px), on column edge c."""
    start = len(bm.verts)
    common.loft(bm, [(Y(recoiled(r, s)), w * P, h * P, z * P) for r, w, h, z in sections],
                sides=sides, mat_index=mat, cap_start=cap, cap_end=cap)
    common.shift_x(bm, start, X(c))


def build(sprite, frame, s):
    tag = f"{NAME}{'' if s == 0 else f'-f{s + 1}'}"
    coll = common.reset_collection(tag)
    metal = lambda i, r=0.3: common.palette_material(sprite, i, NAME, metallic=0.75, roughness=r)  # noqa: E731
    glow = lambda i, e: common.palette_material(sprite, i, NAME, emission_strength=e)  # noqa: E731
    idx = [254, 3, 4, 7, 8, 9, 10, 11]
    mats = [metal(i) for i in idx]
    mats[0] = common.palette_material(sprite, 254, NAME, metallic=0.0, roughness=0.9)  # the bore
    M = {i: k for k, i in enumerate(idx)}
    RED, ORANGE, AMBER, GOLD, YELLOW = range(len(mats), len(mats) + 5)
    mats += [glow(119, 4.0), glow(121, 5.0), glow(122, 6.0), glow(123, 7.0), glow(124, 8.0)]

    hard = bmesh.new()  # flat shaded: rings, seams, caps, fairings
    round_ = bmesh.new()  # smooth shaded: the drum, sponsons and barrel
    ZC = 2.9  # the drum's axis height, px

    # The drum hull, columns 3-8: a round body from the seam behind the collar, full width to row
    # 8.8, then tapering into the sprite's narrowing tail (rows 10-11) and a hard chamfered tail cap.
    drum(round_, [(3.9, 2.4, 2.3, ZC), (4.3, 2.85, 2.7, ZC), (8.8, 2.85, 2.7, ZC), (9.9, 2.6, 2.5, ZC),
                  (10.9, 2.1, 2.05, ZC)], 6, 16, M[7], s)
    drum(hard, [(10.85, 2.15, 2.1, ZC), (11.3, 1.85, 1.8, ZC), (11.6, 1.4, 1.35, ZC), (11.75, 1.0, 0.95, ZC)],
         6, 16, M[8], s)
    # The exhaust in the tail cap (the black pixel at row 11): a small polished nozzle with a
    # pinhole throat, so the cannon end stays the obvious front.
    drum(hard, [(11.7, 0.6, 0.6, ZC), (11.95, 0.5, 0.5, ZC)], 6, 10, M[9], s)
    drum(hard, [(11.94, 0.25, 0.25, ZC), (11.97, 0.25, 0.25, ZC)], 6, 8, M[254], s)

    # Three raised trim rings round the drum (the sprite's light bands across it), chamfered.
    for r0, r1 in ((5.0, 5.9), (7.0, 7.8)):
        drum(hard, [(r0, 2.95, 2.8, ZC), (r0 + 0.15, 3.15, 3.0, ZC), (r1 - 0.15, 3.15, 3.0, ZC),
                    (r1, 2.95, 2.8, ZC)], 6, 16, M[9], s)
    # The aft ring follows the hull's taper.
    drum(hard, [(9.0, 2.92, 2.77, ZC), (9.15, 3.08, 2.93, ZC), (9.65, 2.95, 2.83, ZC), (9.8, 2.78, 2.66, ZC)],
         6, 16, M[9], s)

    # The dark seam ring at row 4 between collar and hull.
    drum(hard, [(3.7, 2.5, 2.4, ZC), (4.35, 2.5, 2.4, ZC)], 6, 16, M[3], s)

    # The collar, rows 2-3 (columns 3-8): a bright polished ring with a chamfered front face.
    drum(hard, [(1.95, 2.3, 2.2, ZC), (2.25, 3.0, 2.85, ZC), (3.6, 3.0, 2.85, ZC), (3.85, 2.75, 2.6, ZC)],
         6, 16, M[10], s)

    # The cannon, columns 4-7: a barrel from inside the collar, a dark groove at row 1, and a
    # polished muzzle ring at row 0 with a black bore.
    drum(round_, [(2.3, 1.7, 1.7, ZC + 0.2), (1.25, 1.7, 1.7, ZC + 0.2)], 6, 14, M[8], s)
    drum(hard, [(1.3, 1.45, 1.45, ZC + 0.2), (0.85, 1.45, 1.45, ZC + 0.2)], 6, 14, M[3], s)
    drum(hard, [(0.9, 1.95, 1.95, ZC + 0.2), (0.15, 1.95, 1.95, ZC + 0.2), (0.0, 1.75, 1.75, ZC + 0.2)],
         6, 14, M[11], s)
    drum(hard, [(0.1, 0.95, 0.95, ZC + 0.2), (-0.01, 0.95, 0.95, ZC + 0.2)], 6, 12, M[254], s)

    # The sponsons, columns 1-2 and 9-10: round tubes lit down their outer edge, tucked against
    # the drum, with chamfered end caps, rows 4.3-10.1, sitting a little lower than the drum's axis.
    for c in (2.3, 9.7):
        drum(round_, [(4.75, 1.05, 1.15, 2.4), (9.3, 1.05, 1.15, 2.4)], c, 12, M[8], s, cap=False)
        # Hard chamfered end caps: a small domed sensor in the nose, a closed tapered tail with a
        # pinhole vent (no open bores).
        drum(hard, [(4.3, 0.0, 0.0, 2.4), (4.38, 0.5, 0.55, 2.4), (4.5, 0.85, 0.95, 2.4), (4.8, 1.1, 1.2, 2.4)],
             c, 12, M[9], s, cap=False)
        drum(hard, [(4.33, 0.3, 0.33, 2.4), (4.4, 0.32, 0.35, 2.4)], c, 10, M[4], s)
        drum(hard, [(9.25, 1.1, 1.2, 2.4), (9.7, 0.85, 0.95, 2.4), (10.05, 0.45, 0.5, 2.38), (10.12, 0.0, 0.0, 2.38)],
             c, 12, M[9], s, cap=False)
        drum(hard, [(10.06, 0.15, 0.15, 2.38), (10.1, 0.15, 0.15, 2.38)], c, 8, M[3], s)
        # Two clamp bands round each sponson.
        for r0 in (5.6, 8.4):
            drum(hard, [(r0, 1.2, 1.3, 2.4), (r0 + 0.6, 1.2, 1.3, 2.4)], c, 12, M[4], s)
        # A solid fairing joining it to the drum along its length (the sprite's dark column 3 / 8),
        # tapered at both ends, so the pod's outline reads as one oval from above.
        drum(hard, [(4.8, 0.45, 0.55, 2.4), (5.4, 0.95, 1.0, 2.4), (8.9, 0.95, 1.0, 2.4), (9.9, 0.4, 0.5, 2.4)],
             3.15 if c < 6 else 8.85, 8, M[4], s)

    parts = [common.mesh_object(f"{tag}-hard", hard, mats, coll, smooth=False),
             common.mesh_object(f"{tag}-round", round_, mats, coll, smooth=True)]

    # The muzzle flash in front of the recoiled barrel: nested glowing cones (sections are row
    # edge, half width px, half height px, z centre px), a red-orange shell round a yellow core.
    if s:
        fbm = bmesh.new()
        front = recoiled(0.0, s)  # the muzzle's front row edge
        z = ZC + 0.2
        if s == 1:  # frame 187: a 2 px burst at row 0, yellow-orange left, red right
            shells = [(GOLD, [(front, 1.0, 1.0, z), (front - 0.5, 1.1, 1.0, z), (front - 1.0, 0.0, 0.0, z)]),
                      (RED, [(front + 0.01, 1.15, 0.8, z - 0.1), (front - 0.6, 1.0, 0.7, z - 0.1),
                             (front - 0.95, 0.0, 0.0, z - 0.1)])]
        else:  # frame 206: a 3 px wide burst at row 1 (red, yellow, orange) with an amber tip at row 0
            shells = [(RED, [(front, 1.7, 1.2, z - 0.1), (front - 0.55, 2.1, 1.3, z - 0.1),
                             (front - 1.0, 1.3, 0.95, z - 0.1), (front - 1.35, 0.0, 0.0, z - 0.1)]),
                      (ORANGE, [(front + 0.01, 1.1, 1.35, z), (front - 0.9, 1.1, 1.3, z), (front - 1.35, 0.0, 0.0, z)]),
                      (YELLOW, [(front + 0.02, 0.6, 0.6, z + 0.9), (front - 0.95, 0.55, 0.55, z + 0.9),
                                (front - 1.2, 0.0, 0.0, z + 0.9)]),
                      (AMBER, [(front - 0.8, 0.55, 0.6, z + 0.6), (front - 1.5, 0.5, 0.55, z + 0.6),
                               (front - 2.0, 0.0, 0.0, z + 0.6)])]
        for mat, secs in shells:
            drum(fbm, secs, 6, 10, mat, 0)
        parts.append(common.mesh_object(f"{tag}-flash", fbm, mats, coll, smooth=True))
    return parts


def main():
    sprite = common.load_sprite(ROOT, REF)
    base = sprite["sprites"][0]
    built = []
    for frame, s, suffix in FRAMES:
        objs = build(sprite, frame, s)
        sprites = [{**base, "frames": [frame]}]
        common.export_sprite_model(ROOT, objs, f"sidekicks/{NAME}{suffix}", sprites)
        built.append((frame, objs))
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        for frame, objs in built:
            f = next(f for f in sprite["frames"] if f["index"] == frame)
            ref = ROOT / "reference" / "models" / REF / f["image"]
            common.render_preview(objs, out.with_name(f"{out.stem}-{frame}.png"), ref,
                                  size=(f["width"], f["height"]), view_px=320, frame=frame)


if __name__ == "__main__":
    main()
