"""Eight-claw blade rotor with a blue core (newsh#.shp, assembly of 4 pieces): a 3D version of
its sprites.

Seen in episode 3 (levels 3.4 and 3.19). Four 2x2 enemies make one 48x56 px ground machine: a
glowing blue core with a white glint and eight grey claw arms round it. The arms are the same
claw as the four-armed grabber (assembly-newsh-hash-41, lib_b094.claw_arm): the sprite draws two
of that grabber's frames on top of each other, so there are two sets of four arms 45 degrees
apart (frame 0), or 50 degrees apart while it turns (frame 1, the grabber's frames 1 and 3).

Its five frames: 0 is the rotor at rest; 1 is it turning; 2, 3 and 4 repeat frame 0 two palette
steps darker each time (it fades out; frame 3 also draws it a pixel off, a jolt the model leaves
out). So every piece gets three models: <piece> frames 0 and 2, -f2 frame 1, and -f3 frames 3
and 4 (frame 0's shape with the arms in dark grey). <piece> and -f3 animate: their grey arm
materials take each frame's shade (common.palette_material frames=); the blue core doesn't
change. The whole rotor is built once per shape in assembly coordinates and cut into the
four pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh-hash-195.py [-- --preview out.png]
(the preview is the whole rotor at frame 0; out-f2.png and out-f3.png show the other shapes and
each piece also gets <piece>.png next to it). Add --frames <dir> to render every frame of the
animated pieces into <dir>/<piece><suffix>.png. Add --report to print a top-view silhouette check.
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b094 as lib  # noqa: E402

NAME = "assembly-newsh-hash-195"
ROOT = common.repo_root(__file__)
# Pieces and where they sit in the 48 x 56 px assembly (left, top), from sprite.json
# `assemblyLayout` (157 at screen 158, 37; 159 at 182, 37; 195 at 158, 65; 197 at 182, 65).
GRID = [("newsh-hash-157", 0, 0), ("newsh-hash-159", 24, 0), ("newsh-hash-195", 0, 28),
        ("newsh-hash-197", 24, 28)]
PIECES = [g[0] for g in GRID]
CORE = (0.5, 0.5)  # core centre in pixels from the assembly's centre (it sits on pixel 24, 27)

# The shapes: suffix, frames, the two arm sets' angles (degrees anticlockwise from straight up)
# with their bulk (see lib_b094.claw_arm), and the shade.
SHAPES = [
    ("", [0, 2], [(45.0, 0.0), (0.0, 0.0)], 0),
    ("-f2", [1], [(24.0, 0.6), (-26.0, 0.0)], 0),
    ("-f3", [3, 4], [(45.0, 0.0), (0.0, 0.0)], 0),
]
# Grey arm colours per shade: (body, light ridge, dark underside) palette indices.
SHADES = [(9, 12, 6)]
# Shapes that fade within their frames: {frame position: palette steps darker than the shade}.
# The sprite's greys are a ramp (1 darkest ... 13) and each fading frame is frame 0 with every
# grey two steps darker than the frame before. A shape takes its first frame's shade.
FADE = {"": {0: 0, 2: 2}, "-f3": {3: 4, 4: 6}}


def grey_materials(sprite, shade, suffix):
    """The arm's (body, ridge, underside) materials for a shape: plain for a still shape, else
    in its first frame's shade with the later frames' shades by sprite index (every piece's own
    indices, since split_assembly gives all four pieces the same materials)."""
    if suffix not in FADE:
        return [common.palette_material(sprite, i, "nsh195", metallic=m, roughness=r)
                for i, m, r in zip(SHADES[shade], (0.6, 0.6, 0.4), (0.35, 0.3, 0.6))]
    fade = FADE[suffix]
    base = fade[min(fade)]
    data = [common.load_sprite(ROOT, name)["frames"] for name in PIECES]
    tag = f"nsh195{suffix or '-f1'}"
    mats = []
    for i, m, r in zip(SHADES[shade], (0.6, 0.6, 0.4), (0.35, 0.3, 0.6)):
        frames = {f[pos]["index"]: max(1, i - k) for f in data for pos, k in fade.items() if k != base}
        mats.append(common.palette_material(sprite, max(1, i - base), tag, metallic=m, roughness=r, frames=frames))
    return mats


def build(sprite, arm_sets, shade, tag):
    coll = common.reset_collection(f"{NAME}{tag}")
    pal = lambda i, **kw: common.palette_material(sprite, i, "nsh195", **kw)  # noqa: E731
    mats = [
        *grey_materials(sprite, shade, tag),  # 0 grey arm, 1 light edge, 2 dark underside
        pal(144, metallic=0.3, roughness=0.5),  # 3 navy footing
        pal(152, metallic=0.3, roughness=0.3, emission_strength=1.5),  # 4 deep blue rim
        pal(154, metallic=0.2, roughness=0.2, emission_strength=2.5),  # 5 blue core
        pal(157, emission_strength=3.0),  # 6 pale blue highlight
        pal(143, emission_strength=5.0),  # 7 white glint
    ]
    ARM, RIDGE, DARK, FOOT, RIM, CORE_M, HIGH, GLINT = range(8)
    bm = bmesh.new()

    for k, (angle, bulk) in enumerate(arm_sets):
        start, fstart = len(bm.verts), len(bm.faces)
        lib.claw_arm(bm, ARM, RIDGE, DARK, bulk, z=0.11 + 0.015 * k)
        lib.copy_rotated(bm, start, fstart, [-90, -180, -270])  # clockwise round the core
        lib.transform(bm, start, angle_deg=angle)

    # The core: a navy footing, a deep blue rim and a glowing blue dome (about 10 px across).
    lib.prism(bm, lib.ngon(5.4, 8, start=0.39), 0.0, 0.1, mat=FOOT)
    lib.frustum(bm, 0, 0, 5.3, 4.8, 0.1, 0.17, sides=16, mat=RIM, cap_top=False)
    lib.ellipsoid(bm, 0, 0, 0.17, 4.8, 4.8, 0.15, mat=CORE_M, segments=16, rings=8, z_min=0.16)
    # The pale blue sheen and the white glint up and left of the centre (fixed in every frame).
    lib.ellipsoid(bm, -0.8, 1.3, 0.27, 2.2, 2.0, 0.045, mat=HIGH, segments=12, rings=6)
    lib.ellipsoid(bm, -1.0, 2.0, 0.31, 0.9, 0.9, 0.02, mat=GLINT, segments=8, rings=4)
    lib.transform(bm, 0, dx_px=CORE[0], dy_px=CORE[1])
    return lib.to_object(f"{NAME}{tag}", bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    layout = [(name, float(x0 + 12 - 24), float(y0 + 14 - 28)) for name, x0, y0 in GRID]
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    for suffix, frames, arm_sets, shade in SHAPES:
        obj = build(sprite, arm_sets, shade, suffix)
        if "--report" in sys.argv:
            lib.silhouette_report(obj, ROOT, GRID, frames[0], label=f"{NAME}{suffix} frame {frames[0]}")
        pieces = common.split_assembly(obj, [(f"{n}{suffix}", cx, cy) for n, cx, cy in layout])
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            common.export_sprite_model(ROOT, [pieces[f"{name}{suffix}"]], f"enemies/{name}{suffix}",
                                       lib.frame_subset(data["sprites"], frames))
        if preview:
            import tempfile
            out = preview if not suffix else preview.with_name(f"{preview.stem}{suffix}.png")
            ref = lib.composite_png(ROOT, GRID, frames[0], Path(tempfile.mkdtemp()) / "a.png")
            common.render_preview([obj], str(out), ref, size=4, view_px=480)
            for name in PIECES:
                data = common.load_sprite(ROOT, name)
                img = ROOT / "reference" / "models" / name / data["frames"][frames[0]]["image"]
                common.render_preview([pieces[f"{name}{suffix}"]], str(out.parent / f"{name}{suffix}.png"), img, size=2)
        if "--frames" in sys.argv and suffix in FADE:  # every frame of each animated piece
            out_dir = Path(sys.argv[sys.argv.index("--frames") + 1])
            for name in PIECES:
                data = common.load_sprite(ROOT, name)
                data["frames"] = [data["frames"][i] for i in frames]
                common.render_frame_previews([pieces[f"{name}{suffix}"]], str(out_dir / f"{name}{suffix}.png"), data, ROOT)


if __name__ == "__main__":
    main()
