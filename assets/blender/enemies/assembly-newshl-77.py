"""Grey thruster tower (newshl.shp 77 and 79, side by side): a 3D version of its sprites.

Seen in episode 4, level 40. Two 2x2 sprites make one symmetric object 25 px wide (centred on the
seam's right-hand column): the lower end of a grey machine. Down the screen it has a narrow neck
with red lights (rows 0-6), a wide rounded tier with a dark slot across it (rows 7-11), a groove,
a narrower band, another groove, a second wide tier with a bright upper rim (rows 16-19) and a
glowing red exhaust ring at the bottom (rows 21-22). It is lofted down the screen as stacked
rounded discs, then cut into the two pieces (newshl-77 left, newshl-79 right).

Run: blender --background --python assets/blender/enemies/assembly-newshl-77.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b006 as lib  # noqa: E402

NAME = "assembly-newshl-77"
PIECES = ["newshl-77", "newshl-79"]
ROOT = common.repo_root(__file__)

# Profile down the screen: (row edge, half width px from the axis, half height in units, part).
# Equal rows next to each other make the steps between tiers.
NECK, TIER, GROOVE, BAND, TIER2, ENGINE = range(6)
PROFILE = [
    (-0.5, 10.0, 0.13, NECK), (0.6, 9.0, 0.14, NECK), (1.2, 7.6, 0.16, NECK), (3.6, 7.4, 0.16, NECK),
    (4.4, 5.6, 0.13, NECK), (5.5, 6.0, 0.14, NECK), (6.5, 7.4, 0.17, NECK),
    (6.5, 9.0, 0.2, TIER), (7.2, 10.8, 0.24, TIER), (8.2, 12.0, 0.27, TIER), (10.0, 12.6, 0.28, TIER),
    (11.4, 12.3, 0.26, TIER), (11.8, 11.0, 0.22, TIER),
    (11.8, 7.0, 0.18, GROOVE), (12.6, 6.6, 0.17, GROOVE),
    (12.6, 9.0, 0.22, BAND), (13.2, 9.8, 0.24, BAND), (14.6, 9.8, 0.24, BAND), (15.0, 9.0, 0.22, BAND),
    (15.0, 7.0, 0.18, GROOVE), (15.6, 7.0, 0.18, GROOVE),
    (15.6, 11.0, 0.25, TIER2), (16.3, 12.6, 0.29, TIER2), (17.5, 12.6, 0.3, TIER2), (18.5, 11.6, 0.27, TIER2),
    (19.6, 9.6, 0.22, TIER2),
    (19.6, 5.4, 0.15, GROOVE), (20.6, 5.4, 0.15, GROOVE),
    (20.6, 7.4, 0.17, ENGINE), (21.5, 7.8, 0.18, ENGINE), (22.6, 7.2, 0.15, ENGINE), (22.9, 0.0, 0.0, ENGINE),
]


def build(sprites):
    coll = common.reset_collection(NAME)
    grid = lib.Grid(48, 28)
    mats = lib.Mats(NAME, lib.merged_colors(sprites))
    slot = {
        NECK: mats(6, metallic=0.55, roughness=0.4),
        TIER: mats(8, metallic=0.55, roughness=0.35),
        GROOVE: mats(3, metallic=0.4, roughness=0.6),
        BAND: mats(6, metallic=0.55, roughness=0.4),
        TIER2: mats(7, metallic=0.55, roughness=0.35),
        ENGINE: mats(119, metallic=0.0, roughness=0.4, emission_strength=3.5),
    }
    rim = mats(12, metallic=0.6, roughness=0.25)
    dark = mats(3, metallic=0.4, roughness=0.6)
    light_a = mats(116, metallic=0.0, roughness=0.4, emission_strength=3.0)
    light_b = mats(118, metallic=0.0, roughness=0.4, emission_strength=3.0)
    axis = grid.x(24)
    bm = bmesh.new()

    def loft_profile(profile, part_of):
        """One loft per run of the same part, so each takes its own material."""
        runs = []
        for sec in profile:
            if runs and runs[-1][0] == sec[3]:
                runs[-1][1].append(sec)
            else:
                runs.append((sec[3], [sec]))
        for i, (part, secs) in enumerate(runs):
            # Close each run against its neighbour so the steps between parts are solid.
            sections = [(grid.y(r - 0.5), w * lib.U, h, 0.0) for r, w, h, _ in secs]
            if len(sections) < 2:
                continue
            start = len(bm.verts)
            common.loft(bm, sections, sides=18, mat_index=part_of(part))
            common.shift_x(bm, start, axis)

    loft_profile(PROFILE, lambda p: slot[p])

    # Bright rim along the top of the lower tier (row 16's highlight).
    start = len(bm.verts)
    common.loft(bm, [(grid.y(15.9), 12.0 * lib.U, 0.29, 0.0), (grid.y(16.6), 12.7 * lib.U, 0.3, 0.0)],
                sides=18, mat_index=rim, cap_start=False, cap_end=False)
    common.shift_x(bm, start, axis)
    # Hmm: the rim sits just outside the tier surface.
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.x = axis + (v.co.x - axis) * 1.02
        v.co.z *= 1.02

    # Dark slot across the upper tier (rows 10-11, columns 20-28).
    lib.box(bm, grid.x(19.6), grid.y(11.6), grid.x(28.4), grid.y(9.6), 0.2, 0.29, mat_index=dark)
    # Dark vent on the band's right side (rows 13-14, columns 30-33).
    lib.box(bm, grid.x(29.6), grid.y(14.5), grid.x(33.4), grid.y(12.6), 0.14, 0.235, mat_index=dark)

    # Red lights: on the neck's flare (rows 0-1, columns 16 and 32) and its pinch (row 5, columns 18.5, 29.5).
    for c in (16.0, 32.0):
        start = len(bm.verts)
        common.loft(bm, [(grid.y(1.4), 0.0, 0.0, 0.1), (grid.y(0.9), 0.07, 0.045, 0.11), (grid.y(-0.2), 0.07, 0.045, 0.11),
                         (grid.y(-0.5), 0.0, 0.0, 0.1)], sides=8, mat_index=light_a)
        common.shift_x(bm, start, grid.x(c))
    for c in (18.5, 29.5):
        start = len(bm.verts)
        common.loft(bm, [(grid.y(5.6), 0.0, 0.0, 0.08), (grid.y(5.3), 0.08, 0.05, 0.09), (grid.y(4.7), 0.08, 0.05, 0.09),
                         (grid.y(4.4), 0.0, 0.0, 0.08)], sides=8, mat_index=light_b)
        common.shift_x(bm, start, grid.x(c))

    obj = common.mesh_object(NAME, bm, mats.list, coll, smooth=True)
    return obj


def main():
    sprites = [common.load_sprite(ROOT, n) for n in PIECES]
    obj = build(sprites)
    layout = [(p["model"], p["cx"] - 123, p["cy"] + 17) for p in sprites[0]["assemblyLayout"]]
    pieces = common.split_assembly(obj, layout)
    for s in sprites:
        piece = pieces[s["name"]]
        for poly in piece.data.polygons:
            poly.use_smooth = True
        common.export_sprite_model(ROOT, [piece], f"enemies/{s['name']}", s["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        common.render_preview([obj], str(out), None, size=4)
        for s in sprites:
            f = s["frames"][0]
            common.render_preview([pieces[s["name"]]], str(out.with_name(f"{s['name']}.png")),
                                  ROOT / "reference" / "models" / s["name"] / f["image"], size=2)


if __name__ == "__main__":
    main()
