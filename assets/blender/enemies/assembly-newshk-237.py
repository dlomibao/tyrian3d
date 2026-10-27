"""Grey yoke boss with a red core (newshk.shp, assembly of 8 pieces plus newshk-163): a 3D
version of its sprites.

Seen in episode 3 (level 3.12). Eight 2x2 enemies make one 72x84 px machine (sprite.json
`assemblyLayout`): a grey pod in the middle (newshk-153 over newshk-191) with a lidded top, a
grilled back, a big glowing red orb in a cradle, a bar with a red nozzle under it and two thin
legs; a beam and a thin pipe on each side carry a big C-shaped grey arm that sweeps out, down and
back in to a claw with a glowing red inner face (newshk-161/199/237 on the left, 167/205/243 on
the right). newshk-153's four frames only brighten the orb (its glow materials change palette colour per
frame) and newshk-191's two flare the nozzle (a bigger glow shown on frame 193), so each gets one
model. newshk-163 is the left beam's stub where the pod hangs (the same 24x28 box as
newshk-153: its bar and beam carry on from newshk-161's right edge); it is built from the same
beam and pipe and cut from that box.

The machine is built once in assembly coordinates (the left half, mirrored about the sprite's
axis at pixel column 36), then cut into pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshk-237.py [-- --preview out.png]
(the preview is the whole machine; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b055 as L  # noqa: E402

NAME = "assembly-newshk-237"
ROOT = common.repo_root(__file__)
PIECES = ["newshk-161", "newshk-153", "newshk-167", "newshk-199", "newshk-191", "newshk-205",
          "newshk-237", "newshk-243"]
STUB = "newshk-163"
CX0, CY0 = 141, 71  # screen centre of newshk-191 = assembly edge (36, 42) = Blender origin
AXIS = 36.5  # the sprite mirrors about the centre of pixel column 36


def materials(sprite, tag="nshk237", glow=None):
    """The palette materials. With `glow` (palette index -> {frame: index}), the red glow
    materials (5-8) change colour on those frames; give them their own `tag`."""
    def pal(i, red=False, **kw):
        return common.palette_material(sprite, i, tag, frames=glow(i) if red and glow else None, **kw)
    return [
        pal(10, metallic=0.4, roughness=0.35),  # 0 grey hull
        pal(12, metallic=0.45, roughness=0.3),  # 1 light grey rails and plates
        pal(7, metallic=0.4, roughness=0.45),  # 2 dark grey (the claw's shaded band)
        pal(3, metallic=0.4, roughness=0.6),  # 3 deep recesses
        pal(13, metallic=0.7, roughness=0.25),  # 4 bright grey lid and claw foot
        pal(118, True, metallic=0.3, roughness=0.15, emission_strength=2.5),  # 5 red orb
        pal(124, True, emission_strength=5.0),  # 6 hot core
        pal(119, True, emission_strength=3.0),  # 7 red vents and claw face
        pal(113, True, metallic=0.3, roughness=0.5, emission_strength=1.0),  # 8 dark red vent bed
        pal(9, metallic=0.45, roughness=0.4),  # 9 mid grey pipes and bars
        pal(5, metallic=0.4, roughness=0.55),  # 10 dark grey beam flange and hub
    ]


HULL, LIGHT, DARK, DEEP, BRIGHT, ORB, HOT, VENT, BED, MID, FLANGE = range(11)


def beam(bm, c0, c1, end_round=True):
    """The side beam between an arm and the pod (rows 15-21) and the thin pipe over it (row 9),
    from column edge c0 to c1 (left half): a dark flange with two light rails along its top."""
    L.pillow(bm, [(c0, 15.2), (c1, 15.2), (c1, 21), (c0, 21)], -0.10, 0.04, bevel=0.5, mat=FLANGE)
    for r in (15.9, 18.4):
        L.sweep(bm, [(c0, r, 0.05, 0.9, 0.045), (c1 - 0.4, r, 0.05, 0.9, 0.045)]
                + ([(c1, r, 0.05, 0.0, 0.0)] if end_round else []), sides=8, mat=HULL)


def stub_pipe(bm, c0, c1):
    L.sweep(bm, [(c0, 9.5, 0.05, 1.0, 0.05), (c1 - 0.6, 9.5, 0.05, 1.0, 0.05), (c1, 9.5, 0.05, 0.0, 0.0)],
            sides=8, mat=MID)


def build_left(bm):
    """The left arm, beam and pipe, and the left-hand pod details (mirrored afterwards)."""
    # Thin pipe from the pod's side (row 9) out and down into the top of the arm.
    L.sweep(bm, [(27.0, 9.5, 0.05, 1.0, 0.05), (17.0, 9.5, 0.05, 1.0, 0.05), (15.0, 10.6, 0.05, 1.0, 0.05),
                 (13.4, 12.8, 0.04, 1.0, 0.05), (12.8, 15.5, 0.02, 1.1, 0.05)], sides=8, mat=MID)
    # Side beam from the arm into the pod.
    beam(bm, 14.0, 29.0, end_round=False)

    # The arm, upper part: shoulder, the long vertical side and the vent bulge (rows 15-53).
    upper = [(11, 15), (18, 15), (18, 21), (20, 21.2), (19, 22.5), (15, 26.5), (14, 27), (9, 27),
             (9, 30.5), (10, 31), (13, 34), (13, 39.5), (12, 40), (12, 44), (8, 44), (8, 52), (9, 53),
             (2.5, 53), (2, 52.5), (2, 22), (6, 21), (8, 20), (10, 19.5), (10, 16)]
    L.pillow(bm, upper, -0.13, 0.13, bevel=1.0, mat=HULL)
    # Lower part: the band that curves back in, darker as it faces down, to the claw foot.
    lower = [(2.5, 53), (9, 53), (10, 55), (11, 57), (12, 59), (13, 61), (14, 63.5), (15.5, 66),
             (16.5, 68), (17.5, 70), (18.5, 72), (19, 74), (19, 75), (25, 75), (25, 82), (20.5, 82),
             (15, 76.2), (14, 75), (13, 74), (12.5, 72.5), (12, 69.5), (11, 68), (9.5, 66.5), (9, 64.5),
             (8, 63), (7, 61.5), (6.5, 59), (5, 57.5), (4, 55.5), (3, 54)]
    L.pillow(bm, lower, -0.12, 0.12, bevel=1.0, mat=DARK)
    # The glowing red inner face of the claw (rows 64-73).
    face = [(14, 63.6), (15, 63.8), (19, 65), (23, 69), (23, 74), (19.2, 74), (18.5, 72), (17.5, 70),
            (16.5, 68), (15.5, 66)]
    L.pillow(bm, face, -0.09, 0.08, bevel=0.7, mat=VENT)
    # Light claw foot (rows 75-81) and the light elbow plate (rows 53-58).
    L.pillow(bm, [(15, 75.4), (25, 75.4), (25, 81.6), (20.7, 81.6)], 0.06, 0.15, bevel=0.6, mat=BRIGHT,
             bottom_bevel=0)
    L.pillow(bm, [(5.5, 53.3), (9.3, 53.3), (10.6, 57.8), (7, 57.8)], 0.06, 0.15, bevel=0.5, mat=LIGHT,
             bottom_bevel=0)
    # Light rail down the outer side (column 4) and an inner lip (columns 7-11).
    L.sweep(bm, [(4.5, 22.5, 0.13, 0.0, 0.0), (4.5, 23.5, 0.13, 0.8, 0.04), (4.5, 52.0, 0.13, 0.8, 0.04),
                 (5.0, 53.5, 0.13, 0.0, 0.0)], sides=6, mat=LIGHT)
    L.sweep(bm, [(7.3, 26.8, 0.13, 0.0, 0.0), (7.3, 27.8, 0.13, 0.7, 0.035), (7.6, 31.5, 0.13, 0.7, 0.035),
                 (10.8, 34.2, 0.13, 0.7, 0.035), (10.8, 39.0, 0.13, 0.7, 0.035), (10.8, 39.8, 0.13, 0.0, 0.0)],
            sides=6, mat=LIGHT)
    # Light diagonal on the shoulder (from column 11, row 16 down to column 3, row 22).
    L.sweep(bm, [(12.5, 16.2, 0.13, 0.0, 0.0), (12.0, 16.8, 0.13, 0.8, 0.04), (4.0, 22.6, 0.13, 0.8, 0.04),
                 (3.2, 23.2, 0.13, 0.0, 0.0)], sides=6, mat=LIGHT)
    # Vent in the arm's inner bulge: a dark bed (rows 39-53) with two red slots (columns 9 and 11).
    L.pillow(bm, [(8, 39.3), (12.4, 39.3), (12.4, 53), (8, 53)], -0.08, 0.12, bevel=0.5, mat=DEEP)
    for c in (9.0, 11.0):
        L.pillow(bm, [(c, 44), (c + 1, 44), (c + 1, 52.5), (c, 52.5)], 0.0, 0.135, bevel=0.25, mat=VENT,
                 bottom_bevel=0)

    # Pod details on the left: the cradle strut beside the orb (rows 21-28) and the leg (rows 30-46).
    L.pillow(bm, [(26.5, 20.5), (30, 20.5), (31.5, 22.5), (34, 24), (34, 29), (29, 29), (30, 26.5),
                  (30, 24), (28, 22)], -0.12, 0.1, bevel=0.6, mat=HULL)
    L.sweep(bm, [(26.8, 30.0, -0.02, 0.0, 0.0), (26.8, 30.6, -0.02, 2.0, 0.08), (26.8, 38.0, -0.04, 1.8, 0.07),
                 (26.6, 39.0, -0.05, 0.8, 0.04), (26.5, 45.4, -0.06, 0.6, 0.035), (26.5, 46.0, -0.06, 0.0, 0.0)],
            sides=8, mat=HULL)
    # Light shoulder plate where the beam meets the pod (rows 15-18).
    L.pillow(bm, [(24.8, 15), (30.5, 15), (30.5, 18.2), (24.8, 18.2)], -0.02, 0.15, bevel=0.6, mat=LIGHT)


def build_centre(bm):
    """The pod (symmetric about the axis)."""
    A = AXIS
    # Barrel body, back (row 3) to the cradle (row 22).
    L.loft_y(bm, A, [(2.6, 3.5, 0.08, 0.0), (3.4, 6.5, 0.13, 0.0), (4.5, 8.0, 0.16, 0.0),
                     (5.5, 9.2, 0.18, 0.0), (6.5, 10.3, 0.19, 0.0), (7.8, 11.3, 0.2, 0.0),
                     (9.0, 11.6, 0.2, 0.0), (12.5, 11.6, 0.2, 0.0), (14.5, 11.8, 0.13, 0.0),
                     (20.0, 11.8, 0.12, 0.0), (21.2, 10.0, 0.1, 0.0), (22.3, 6.5, 0.08, 0.0), (22.8, 0.0, 0.0, 0.0)], sides=14, mat=HULL)
    # Lid on the back (rows 1-3) over a dark recess.
    L.pillow(bm, [(31, 0.8), (42, 0.8), (42, 3.2), (31, 3.2)], 0.0, 0.17, bevel=0.6, mat=BRIGHT)
    L.pillow(bm, [(32, 2.8), (41, 2.8), (41, 4.2), (32, 4.2)], 0.0, 0.15, bevel=0.3, mat=DEEP, bottom_bevel=0)
    # Light ribs either side of the grille (columns 31 and 40, rows 4-13).
    for c in (32.0, 41.0):
        L.sweep(bm, [(c, 4.2, 0.15, 0.0, 0.0), (c, 5.0, 0.165, 1.0, 0.04), (c, 12.4, 0.178, 1.0, 0.04),
                     (c, 13.2, 0.17, 0.0, 0.0)], sides=6, mat=LIGHT)
    # Grille on the back (columns 33-39, rows 7-13): a dark slot with three light bars.
    L.pillow(bm, [(33.4, 6.8), (39.6, 6.8), (39.6, 13.2), (33.4, 13.2)], 0.1, 0.205, bevel=0.3, mat=DEEP,
             bottom_bevel=0)
    for c in (34.0, 36.0, 38.0):
        L.pillow(bm, [(c, 7.6), (c + 1, 7.6), (c + 1, 10.8), (c, 10.8)], 0.1, 0.225, bevel=0.25, mat=BRIGHT,
                 bottom_bevel=0)
    # The big red orb (columns 31-41, rows 13-23) and its hot core, upper left.
    L.ellipsoid(bm, A, 18.4, 0.09, 6.0, 5.8, 0.25, mat=ORB, segments=18, rings=10)
    L.ellipsoid(bm, 34.4, 16.4, 0.26, 1.5, 1.5, 0.07, mat=HOT, segments=10, rings=5)
    # Red stem from under the orb down to the nozzle (column 36, rows 22-36).
    L.loft_y(bm, A, [(22.0, 1.5, 0.07, 0.02), (36.0, 1.5, 0.07, 0.02)], sides=8, mat=VENT)
    # Bar across under the cradle (rows 29-31), its ends turning down into the legs.
    L.sweep(bm, [(26.0, 30.6, 0.0, 0.0, 0.0), (26.6, 30.6, 0.0, 1.6, 0.08), (46.4, 30.6, 0.0, 1.6, 0.08),
                 (47.0, 30.6, 0.0, 0.0, 0.0)], sides=10, mat=MID)
    # Hub under the bar (columns 31-41, rows 31-38) with the red nozzle glowing out of it.
    L.loft_y(bm, A, [(31.5, 4.0, 0.08, -0.02), (32.5, 5.2, 0.1, -0.02), (35.5, 4.8, 0.1, -0.02),
                     (37.0, 3.6, 0.07, -0.03), (38.0, 0.0, 0.0, -0.03)], sides=10, mat=FLANGE)
    L.ellipsoid(bm, A, 35.2, 0.06, 2.4, 1.2, 0.05, mat=VENT, segments=10, rings=5)
    L.ellipsoid(bm, A, 35.2, 0.08, 1.0, 0.7, 0.04, mat=HOT, segments=8, rings=4)


def build(sprite, coll):
    mats = materials(sprite)
    bm = bmesh.new()
    build_left(bm)
    L.mirror_all(bm, AXIS)
    build_centre(bm)
    return L.to_object(NAME, bm, mats, coll)


def build_stub(sprite, coll):
    """newshk-163: the left beam and pipe carried on to column 35 where the pod would hang."""
    bm = bmesh.new()
    beam(bm, 23.0, 35.0)
    stub_pipe(bm, 23.0, 35.0)
    return L.to_object("stub-newshk-163", bm, materials(sprite), coll)


GLOW = (ORB, HOT, VENT, BED)


def animate_orb(piece):
    """newshk-153: the orb and stem brighten over its frames, every red shade 2, 6 and 8 steps
    up on frames 155, 157 and 159 (to white-hot 127 at most). Its glow materials get their own
    tag so the other pieces keep the static ones."""
    sprite = common.load_sprite(ROOT, "newshk-153")
    mats = materials(sprite, "nshk153", lambda i: {155: i + 2, 157: min(i + 6, 127), 159: min(i + 8, 127)})
    for slot in GLOW:
        piece.data.materials[slot] = mats[slot]
    return [piece]


def nozzle_flare(sprite, coll):
    """newshk-191, frame 193: the nozzle under the hub flares from a narrow red slit into a big
    glow (columns 34-38, rows 31-37 of the assembly) with a yellow-white core. Built in assembly
    coordinates, which for this piece are its own (its centre is the origin)."""
    pal = lambda i, k: common.palette_material(sprite, i, "nshk191-flare", emission_strength=k)  # noqa: E731
    mats = [pal(119, 3.0), pal(122, 4.0), pal(126, 6.0)]
    bm = bmesh.new()
    L.ellipsoid(bm, AXIS, 34.6, 0.05, 2.8, 3.7, 0.06, mat=0, segments=16, rings=8)
    L.ellipsoid(bm, AXIS, 34.7, 0.08, 2.4, 3.2, 0.06, mat=1, segments=14, rings=7)
    L.ellipsoid(bm, AXIS, 34.4, 0.1, 1.5, 2.0, 0.06, mat=2, segments=12, rings=6)
    return common.frame_part(L.to_object("newshk-191-flare-193", bm, mats, coll), [193])


def main():
    sprite = L.merged_sprite(ROOT, PIECES + [STUB])
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    stub = build_stub(sprite, coll)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    pieces.update(common.split_assembly(stub, [(STUB, 141 - CX0, 43 - CY0)]))
    parts = {name: [pieces[name]] for name in PIECES + [STUB]}
    parts["newshk-153"] = animate_orb(pieces["newshk-153"])
    parts["newshk-191"] = [pieces["newshk-191"], nozzle_flare(sprite, coll)]
    for name in PIECES + [STUB]:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, parts[name], f"enemies/{name}", data["sprites"])
    if "--frame-previews" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--frame-previews") + 1])
        for name in ("newshk-153", "newshk-191"):
            common.render_frame_previews(parts[name], str(out / f"{name}.png"),
                                         common.load_sprite(ROOT, name), ROOT)
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = L.composite_png(ROOT, layout, Path(tempfile.mkdtemp()) / "assembly.png", 72, 84, 36, 42)
        common.render_preview([obj], str(out), ref, size=6, view_px=640)
        for name in PIECES + [STUB]:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview(parts[name], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
