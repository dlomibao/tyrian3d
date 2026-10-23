"""Green hover tank (newshj.shp frames 245 + 283, two pieces side by side): a 3D version of its sprites.

Seen in levels 2.2 and 2.21. Two 2x2 ground enemies make one 48x28 px vehicle lying across the
screen, nose to the left (sprite.json `assemblyLayout`; the grey ship above it in assembly.png is a
separate enemy): a long green hull that widens from a blunt nose (newshj-245, with ring bands and
a hatch) to a big glossy canopy and a rounded tail (newshj-283), with a dark green underside, a red
tail light on top, a red thruster housing with a glowing nozzle below the tail, a short leg and a
small red foot. Each piece has one frame.

The whole vehicle is built once in composite pixel coordinates (48x28, centre at the seam
between the pieces), then cut in two with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshj-245.py [-- --preview out.png]
(the preview is the whole vehicle; each piece also gets <piece>.png next to it).
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b118 as lib  # noqa: E402

NAME = "assembly-newshj-245"
ROOT = common.repo_root(__file__)
PIECES = ["newshj-245", "newshj-283"]
# Composite pixel (0, 0) is screen (198, 82); its centre (screen 222, 96) is the Blender origin.
CX0, CY0 = 222, 96
G = lib.Grid(48, 28)

# Hull silhouette, by pixel-edge column: (col, top edge row, bottom edge row, half height units).
HULL = [(2.6, 11.8, 18.2, 0.10), (3.0, 11.0, 19.0, 0.13), (5.0, 10.0, 20.0, 0.16),
        (9.5, 9.0, 21.0, 0.19), (13.5, 8.0, 22.0, 0.22), (18.5, 7.0, 23.0, 0.245),
        (23.5, 6.0, 24.0, 0.26), (28.5, 5.5, 24.0, 0.26), (35.5, 5.0, 24.0, 0.26),
        (37.5, 5.0, 22.6, 0.255), (39.6, 5.4, 21.2, 0.24)]
SIDES = 16
RIDGE = 0.42  # the hull's crest sits this far from its top edge towards its bottom edge
ZC = 0.72  # centre height as a fraction of the half height (the underside is flattened)


def hull_at(c):
    for (c0, t0, b0, h0), (c1, t1, b1, h1) in zip(HULL, HULL[1:]):
        if c0 <= c <= c1:
            f = (c - c0) / (c1 - c0)
            return t0 + (t1 - t0) * f, b0 + (b1 - b0) * f, h0 + (h1 - h0) * f
    c0, t0, b0, h0 = HULL[0] if c < HULL[0][0] else HULL[-1]
    return t0, b0, h0


def ring(c, top, bottom, hz, scale=1.0, ridge=RIDGE, zc=ZC):
    """A hull cross-section at column edge c (a ring in the YZ plane)."""
    rmid = top + ridge * (bottom - top)
    z0 = hz * zc
    pts = []
    for i in range(SIDES):
        a = 2 * math.pi * (i + 0.5) / SIDES
        u, v = math.cos(a), math.sin(a)
        r = rmid - (rmid - top) * u * scale if u >= 0 else rmid - (bottom - rmid) * u * scale
        z = z0 + (hz if v >= 0 else z0) * v * scale
        pts.append((G.xe(c), G.ye(r), z))
    return pts


def surface_z(c, r):
    """Height of the hull's upper surface over pixel-edge point (c, r)."""
    top, bottom, hz = hull_at(c)
    rmid = top + RIDGE * (bottom - top)
    u = (rmid - r) / (rmid - top) if r <= rmid else (rmid - r) / (bottom - rmid)
    u = max(-1.0, min(1.0, u))
    return hz * ZC + hz * math.sqrt(max(0.0, 1 - u * u))


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshj245"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(42, metallic=0.25, roughness=0.5),  # 0 hull green
        pal(34, metallic=0.2, roughness=0.6),  # 1 dark green underside
        pal(44, metallic=0.3, roughness=0.4),  # 2 light green bands and hatch
        pal(45, metallic=0.2, roughness=0.12),  # 3 glossy canopy
        pal(38, metallic=0.2, roughness=0.55),  # 4 darker green (nose underside, leg bracket)
        pal(41, metallic=0.25, roughness=0.45),  # 5 mid green tail
        pal(116, metallic=0.3, roughness=0.45),  # 6 red thruster housing
        pal(117, emission_strength=2.5),  # 7 red tail light
        pal(120, emission_strength=4.0),  # 8 orange nozzle glow
        pal(124, emission_strength=5.0),  # 9 yellow nozzle core
        pal(46, metallic=0.2, roughness=0.15),  # 10 pale studs
        pal(115, metallic=0.3, roughness=0.5),  # 11 red foot
        pal(47, metallic=0.1, roughness=0.1),  # 12 canopy highlight
        pal(43, metallic=0.3, roughness=0.45),  # 13 panel lines
    ]
    HULLM, UNDER, LIGHT, CANOPY, DARK, TAIL, HOUSING, TAILLIGHT, GLOW, CORE, STUD, FOOT, SHINE, PANEL = range(14)
    bm = bmesh.new()

    # Main hull, nose (left) to the tail section.
    cols = [2.6, 3.0, 4.0, 5.0, 7.0, 9.5, 11.5, 13.5, 16.0, 18.5, 21.0, 23.5, 26.0, 28.5, 32.0, 35.5,
            37.5, 39.6]
    rings = [ring(c, *hull_at(c)) for c in cols]
    faces = lib.ring_loft(bm, rings, mat=HULLM)
    for f in faces:
        cen = f.calc_center_median()
        row = 14 - cen.y * 12
        col = cen.x * 12 + 24
        if row > 18.6:
            f.material_index = UNDER
        elif row > 15.6 and col < 11:
            f.material_index = DARK

    # Raised light bands round the hull (columns 3-4 at the nose, 11-12 and 14).
    for c0, c1 in ((2.9, 4.0), (10.6, 12.5), (13.6, 14.5)):
        rr = [ring(c, *hull_at(c), scale=1.06) for c in (c0, c1)]
        lib.ring_loft(bm, rr, mat=LIGHT)

    # Panel lines along the nose (rows 12 and 14, columns 4-10) and its upright seam (column 15).
    for r in (12.2, 14.2):
        lib.sweep(bm, [(G.xe(c), G.ye(r), surface_z(c, r) - 0.01, 0.45 * lib.PX, 0.025) for c in (4.0, 7.0, 10.5)],
                  sides=6, mat=PANEL)
    lib.sweep(bm, [(G.xe(15.5), G.ye(r), surface_z(15.5, r) - 0.01, 0.45 * lib.PX, 0.025) for r in (9.0, 13.0, 18.0)],
              sides=6, mat=PANEL)

    # Hatch on top (columns 18-20, rows 13-17) and pale studs (columns 21-23, rows 9-11).
    z = surface_z(19, 15)
    lib.prism(bm, [(G.xe(17.6), G.ye(17.4)), (G.xe(20.6), G.ye(17.4)), (G.xe(20.6), G.ye(12.8)),
                   (G.xe(17.6), G.ye(12.8))], z - 0.06, z + 0.025, mat=LIGHT)
    for c, r in ((21.5, 10.5), (23.3, 10.3)):
        lib.dome(bm, G.xe(c), G.ye(r), surface_z(c, r) - 0.03, 0.9 * lib.PX, 1.2 * lib.PX, 0.06,
                 mat=STUD, segments=8, rings=2)

    # Big glossy canopy (columns 28-37, rows 6-13) and its smaller front pane (columns 24-27).
    cz = surface_z(32.5, 10.0)
    lib.dome(bm, G.xe(32.6), G.ye(10.0), cz - 0.1, 5.8 * lib.PX, 4.3 * lib.PX, 0.27, mat=CANOPY,
             segments=18, rings=5)
    lib.dome(bm, G.xe(31.0), G.ye(9.0), cz + 0.08, 2.2 * lib.PX, 1.5 * lib.PX, 0.075, mat=SHINE,
             segments=10, rings=2)
    fz = surface_z(26.0, 10.8)
    lib.dome(bm, G.xe(26.0), G.ye(10.8), fz - 0.08, 2.6 * lib.PX, 2.8 * lib.PX, 0.16, mat=LIGHT,
             segments=12, rings=3)

    # Rounded tail section (columns 40-45, rows 8-15) behind the main hull.
    tail = [(39.3, 8.0, 16.2, 0.2), (42.0, 7.8, 16.2, 0.2), (44.5, 8.2, 15.8, 0.19),
            (45.7, 9.0, 15.0, 0.15), (46.3, 10.3, 13.7, 0.08)]
    rr = [ring(c, t, b, h, ridge=0.45, zc=1.2) for c, t, b, h in tail]
    lib.ring_loft(bm, rr, mat=TAIL)
    # Red tail light on top of it (columns 41-43, rows 6-7).
    lib.ellipsoid(bm, G.xe(42.5), G.ye(7.1), 0.36, 1.7 * lib.PX, 1.2 * lib.PX, 0.07, mat=TAILLIGHT,
                  segments=10, rings=4)

    # Red thruster housing under the tail (columns 40-44, rows 16-23), a nozzle glowing in its top,
    # and the red strip running back along the hull's bottom edge (columns 37-41, rows 22-24).
    lib.sweep(bm, [(G.xe(42.5), G.ye(15.6), 0.2, 0.0, 0.0), (G.xe(42.5), G.ye(16.0), 0.2, 2.2 * lib.PX, 0.15),
                   (G.xe(42.5), G.ye(17.0), 0.2, 2.6 * lib.PX, 0.19),
                   (G.xe(42.5), G.ye(22.0), 0.17, 2.5 * lib.PX, 0.17),
                   (G.xe(42.5), G.ye(23.6), 0.12, 1.9 * lib.PX, 0.12), (G.xe(42.5), G.ye(24.0), 0.1, 0.0, 0.0)],
              sides=10, mat=HOUSING)
    lib.ellipsoid(bm, G.xe(42.5), G.ye(19.6), 0.37, 1.3 * lib.PX, 2.4 * lib.PX, 0.06, mat=GLOW,
                  segments=10, rings=4)
    lib.ellipsoid(bm, G.xe(42.5), G.ye(19.6), 0.415, 0.7 * lib.PX, 1.0 * lib.PX, 0.04, mat=CORE,
                  segments=8, rings=3)
    lib.prism(bm, [(G.xe(37.0), G.ye(24.8)), (G.xe(41.5), G.ye(24.8)), (G.xe(41.5), G.ye(21.6)),
                   (G.xe(38.5), G.ye(21.6)), (G.xe(37.0), G.ye(23.0))], 0.0, 0.1, mat=HOUSING)

    # Leg under the hull (columns 32-33, rows 19-26) on a dark bracket (columns 34-39, rows 19-21).
    lib.sweep(bm, [(G.xe(33.0), G.ye(18.0), 0.14, 1.2 * lib.PX, 0.06), (G.xe(33.0), G.ye(22.0), 0.11, 1.2 * lib.PX, 0.06),
                   (G.xe(33.0), G.ye(26.4), 0.06, 1.1 * lib.PX, 0.05), (G.xe(33.0), G.ye(27.0), 0.06, 0.0, 0.0)],
              sides=8, mat=TAIL)
    lib.prism(bm, [(G.xe(33.8), G.ye(22.4)), (G.xe(40.0), G.ye(22.4)), (G.xe(40.0), G.ye(18.6)),
                   (G.xe(33.8), G.ye(18.6))], 0.0, 0.17, mat=DARK)

    # Small red foot under the hull (columns 26-30, rows 24-26).
    lib.prism(bm, [(G.xe(26.0), G.ye(24.0)), (G.xe(31.0), G.ye(24.0)), (G.xe(30.5), G.ye(27.0)),
                   (G.xe(28.0), G.ye(27.0)), (G.xe(26.0), G.ye(25.0))], 0.0, 0.07, mat=FOOT)

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
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        # The vehicle (48x28) in the middle of a 48x56 image, the 24:28 shape of a size-4 preview.
        entries = [(e["model"], int(e["frame"].split("|")[2]), e["cx"] - CX0 + 24 - 12, e["cy"] - CY0 + 28 - 14)
                   for e in sprite["assemblyLayout"] if e["model"] in PIECES]
        ref = lib.composite_png(ROOT, entries, Path(tempfile.mkdtemp()) / "assembly.png", 48, 56)
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
