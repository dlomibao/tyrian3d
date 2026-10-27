"""Helpers shared by batch b082's model scripts (newsh8.shp ground objects): small mesh builders
and the red rocket that assemblies newsh8-191 (standing) and newsh8-125 (lying sideways) are both
made of. build-models.sh skips lib_ files; the scripts import this one."""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12  # one sprite pixel in units


# --- mesh builders ------------------------------------------------------------------------------

def _mark(bm, before, mat, smooth):
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def loft(bm, sections, sides=10, mat=0, smooth=True, x=0.0):
    """common.loft along +Y (sections are (y, half_width, half_height, z_centre) in units), moved
    to X = x, with the faces' material and smooth flag set."""
    before = set(bm.faces)
    start = len(bm.verts)
    common.loft(bm, sections, sides=sides, mat_index=mat)
    common.shift_x(bm, start, x)
    _mark(bm, before, mat, smooth)


def loft_xy(bm, sections, sides=10, mat=0, smooth=True):
    """Like loft, but each section (x, y, half_width, half_height, z_centre) has its own X, so the
    tube can bend or taper to one side (rings stay square to Y)."""
    before = set(bm.faces)
    start = len(bm.verts)
    common.loft(bm, [(y, w, h, z) for _, y, w, h, z in sections], sides=sides, mat_index=mat)
    bm.verts.ensure_lookup_table()
    i = start
    for x, _, w, h, _ in sections:
        n = 1 if w == 0 and h == 0 else sides
        for v in bm.verts[i:i + n]:
            v.co.x += x
        i += n
    _mark(bm, before, mat, smooth)


def box(bm, x0, x1, y0, y1, z0, z1, mat=0, bevel=0.0):
    """An axis-aligned box in units; `bevel` chamfers its four vertical edges (seen from above)."""
    before = set(bm.faces)
    b = bevel
    if b:
        outline = [(x0 + b, y0), (x1 - b, y0), (x1, y0 + b), (x1, y1 - b), (x1 - b, y1), (x0 + b, y1),
                   (x0, y1 - b), (x0, y0 + b)]
    else:
        outline = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    _mark(bm, before, mat, False)


def plate(bm, outline, z0, z1, mat=0, smooth=False):
    """An outline (counter-clockwise, units) extruded from z0 to z1."""
    before = set(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    _mark(bm, before, mat, smooth)


def ellipsoid(bm, cx, cy, cz, rx, ry, rz, mat=0, segments=16, rings=8, floor=None):
    """An ellipsoid (units). With `floor`, vertices below that height are flattened onto it."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((cx + v.co.x * rx, cy + v.co.y * ry, cz + v.co.z * rz))
        if floor is not None and v.co.z < floor:
            v.co.z = floor
    _mark(bm, before, mat, True)


def tube_x(bm, x0, x1, y, z, ry, rz, mat=0, sides=8):
    """A tube along X from x0 to x1 (units) with radii ry (across Y) and rz."""
    before = set(bm.faces)
    rings = []
    for x in (x0, x1):
        rings.append([bm.verts.new((x, y + ry * math.cos(2 * math.pi * (i + 0.5) / sides),
                                    z + rz * math.sin(2 * math.pi * (i + 0.5) / sides))) for i in range(sides)])
    a, b = rings
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)
    _mark(bm, before, mat, True)


def to_object(name, bm, mats, coll):
    """Like common.mesh_object, but keeps each face's own smooth/flat flag."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def merged_sprite(root, names):
    """The first piece's sprite.json with every listed piece's colours, so any index is valid."""
    data = common.load_sprite(root, names[0])
    for name in names[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_png(root, layout, out, width, height):
    """An assembly's first frames drawn into one image `width` x `height` px, with layout centres
    (cx, cy) measured from the image centre; for render_preview."""
    import numpy as np
    img = np.zeros((height, width, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(cx + width / 2 - 12), int(cy + height / 2 - 14)
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= y0 + r < height and 0 <= x0 + c < width:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", width, height, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


# --- the red rocket (assemblies newsh8-191 and newsh8-125) --------------------------------------
#
# Built along its own axis: R is the pixel row of the standing sprite (newsh8-153 rows 0-27, then
# newsh8-191 rows 28-55), L the pixel column from the axis (sprite column 11). Local X = L / 12,
# Y = -R / 12, so the glowing nozzle points +Y and the nose -Y; it lies on the ground (z = 0).

ROCKET_MATS = [
    # (palette index, kwargs)
    (72, dict(metallic=0.35, roughness=0.4)),  # 0 red hull
    (76, dict(metallic=0.35, roughness=0.3)),  # 1 light red ridge
    (69, dict(metallic=0.3, roughness=0.5)),  # 2 dark red lugs
    (7, dict(metallic=0.7, roughness=0.3)),  # 3 grey housing
    (12, dict(metallic=0.75, roughness=0.25)),  # 4 bright grey rims
    (65, dict(metallic=0.2, roughness=0.7)),  # 5 dark window frame
    (21, dict(metallic=0.2, roughness=0.6)),  # 6 brown window
    (24, dict(metallic=0.3, roughness=0.5)),  # 7 light brown collar
    (21, dict(metallic=0.3, roughness=0.55)),  # 8 brown fins
    (74, dict(metallic=0.3, roughness=0.4)),  # 9 red fin tips
    (115, dict(metallic=0.3, roughness=0.5)),  # 10 dark red nozzle rings
    (119, dict(emission_strength=3.0)),  # 11 exhaust glow
    (120, dict(emission_strength=3.5)),  # 12 glowing slits
    (125, dict(emission_strength=5.0)),  # 13 hot exhaust bands
]
(R_HULL, R_RIDGE, R_LUG, R_GREY, R_RIM, R_FRAME, R_WINDOW, R_COLLAR, R_FIN, R_TIP, R_RING, R_GLOW,
 R_SLIT, R_HOT) = range(len(ROCKET_MATS))
R_HOT2 = len(ROCKET_MATS)  # the exhaust's lower hot band, when animated (rocket_mats animate=True)

# The standing rocket's animation (assembly-newsh8-191, DECISIONS.md D17). Its exhaust's two hot
# bands pulse down the bell: the upper one (rows 5-6) is brightest on newsh8-153's frame 153 and
# dims, the lower one (row 8) brightens to frame 157. {frame: palette index} for each band.
HOT_FRAMES = {153: (125, 123), 155: (123, 125), 157: (121, 127)}
# A bright spark runs along each glowing slit of newsh8-191 (rows 33 and 35), the two in opposite
# directions: (R, sprite column, palette index) of the spark's pixels on each frame.
SLIT_SPARKS = {191: [(33, 8, 126), (33, 9, 123), (35, 13, 125), (35, 12, 121)],
               193: [(33, 10, 126), (33, 11, 123), (35, 11, 125), (35, 10, 121)],
               195: [(33, 13, 126), (35, 8, 125)]}

ZC = 0.38  # hull axis height
# Hull: (R, half width px, half height units)
HULL = [(23.5, 5.2, 0.30), (25.5, 6.0, 0.33), (27.5, 6.5, 0.34), (30.6, 6.5, 0.34), (31.4, 7.8, 0.35),
        (32.5, 8.5, 0.36), (41.5, 8.5, 0.36), (43.0, 7.8, 0.345), (45.0, 6.8, 0.315), (47.0, 5.6, 0.27),
        (49.0, 4.4, 0.215), (50.5, 3.2, 0.16), (51.3, 1.6, 0.08), (51.6, 0.0, 0.0)]


def rocket_mats(sprite, tag, animate=False):
    mats = [common.palette_material(sprite, i, tag, **kw) for i, kw in ROCKET_MATS]
    if animate:  # the hot bands get their own colours per frame (HOT_FRAMES)
        first = min(HOT_FRAMES)
        for slot, band in ((R_HOT, 0), (R_HOT2, 1)):
            frames = {f: c[band] for f, c in HOT_FRAMES.items() if f != first}
            mat = common.palette_material(sprite, HOT_FRAMES[first][band], f"{tag}-hot{band + 1}",
                                          emission_strength=5.0, frames=frames)
            if slot < len(mats):
                mats[slot] = mat
            else:
                mats.append(mat)
    return mats


def _hull_top(R, L=0.0):
    """Height of the hull's top surface at row R, L px from the axis."""
    for (r0, w0, h0), (r1, w1, h1) in zip(HULL, HULL[1:]):
        if r0 <= R <= r1:
            t = (R - r0) / (r1 - r0)
            w, h = w0 + (w1 - w0) * t, h0 + (h1 - h0) * t
            return ZC + h * math.sqrt(max(0.0, 1 - (L / w) ** 2)) if w else ZC
    return ZC


def build_rocket(bm, rib_side=-1, animate=False):
    """Add the rocket to `bm` in its local frame (see above). `rib_side` is the side of the axis
    (-1 left, +1 right, in the standing sprite's columns) of the housing's bright rib, which
    follows the sprites' light from the screen's top left. With `animate` the exhaust's lower hot
    band gets its own material (R_HOT2; use rocket_mats(..., animate=True))."""
    def Y(R):
        return -R * PX

    # Hull: a neck under the collar, a bulging body and a rounded nose.
    loft(bm, [(Y(R), w * PX, h, ZC) for R, w, h in HULL], sides=16, mat=R_HULL)
    # Light ridge down the middle of the body and the two glowing slits across it (rows 33, 35).
    loft(bm, [(Y(36.5), 0.0, 0.0, _hull_top(36.5)), (Y(37.5), 0.7 * PX, 0.03, _hull_top(37.5) - 0.01),
              (Y(45.0), 0.7 * PX, 0.03, _hull_top(45.0) - 0.01), (Y(47.0), 0.0, 0.0, _hull_top(47.0) - 0.02)],
         sides=6, mat=R_RIDGE)
    for R in (33.0, 35.0):
        z = _hull_top(R, 3.5)
        box(bm, -3.5 * PX, 2.5 * PX, Y(R + 0.45), Y(R - 0.45), z - 0.04, _hull_top(R) + 0.02, mat=R_SLIT)

    # Brown collar round the neck (rows 20-23) with fins either side ending in red tips.
    loft(bm, [(Y(20.4), 7.6 * PX, 0.34, ZC), (Y(20.8), 8.5 * PX, 0.37, ZC), (Y(23.4), 8.5 * PX, 0.37, ZC),
              (Y(23.8), 7.6 * PX, 0.34, ZC)], sides=16, mat=R_COLLAR, smooth=True)
    # Broad brown fins either side (columns 1-5 and 17-21, rows 18-27) with red tips.
    fin = [(5.0, 18.3), (7.6, 18.3), (9.6, 20.6), (10.6, 21.4), (10.6, 24.6), (9.6, 25.6), (8.4, 27.4),
           (5.0, 27.4)]
    for s in (-1, 1):
        pts = [(s * l * PX, Y(R)) for l, R in fin]
        plate(bm, pts if s < 0 else list(reversed(pts)), ZC - 0.16, ZC + 0.08, mat=R_FIN)
        box(bm, *sorted((s * 9.4 * PX, s * 10.8 * PX)), Y(24.6), Y(21.4), ZC - 0.17, ZC + 0.1, mat=R_TIP,
            bevel=0.02)

    # Grey housing (rows 10-20, columns 6-16): a chamfered block with a recessed brown window.
    hw = 5.5 * PX
    top = 0.72
    before = set(bm.faces)
    start = len(bm.verts)
    for R0, R1 in ((9.6, 20.6),):
        prof = [(-hw + 0.06, 0.02), (hw - 0.06, 0.02), (hw, 0.1), (hw, top - 0.08), (hw - 0.08, top),
                (-hw + 0.08, top), (-hw, top - 0.08), (-hw, 0.1)]
        a = [bm.verts.new((x, Y(R0), z)) for x, z in prof]
        b = [bm.verts.new((x, Y(R1), z)) for x, z in prof]
        n = len(prof)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
        bm.faces.new(a)
        bm.faces.new(list(reversed(b)))
    _mark(bm, before, R_GREY, False)
    # Bright rim round its nozzle end (row 10) and a bright rib down its left side (column 7).
    box(bm, -hw - 0.01, hw + 0.01, Y(10.6), Y(9.5), 0.03, top + 0.015, mat=R_RIM, bevel=0.05)
    box(bm, *sorted((rib_side * 4.5 * PX, rib_side * 3.5 * PX)), Y(18.0), Y(10.6), top - 0.04, top + 0.02,
        mat=R_RIM)
    # Window frame (columns 9-13, rows 11-17) and the brown pane sunk inside it.
    for x0, x1, R0, R1 in ((-2.5, 2.5, 10.6, 11.6), (-2.5, 2.5, 16.4, 17.5), (-2.5, -1.5, 10.6, 17.5),
                           (1.5, 2.5, 10.6, 17.5)):
        box(bm, x0 * PX, x1 * PX, Y(R1), Y(R0), top - 0.02, top + 0.03, mat=R_FRAME)
    box(bm, -1.5 * PX, 1.5 * PX, Y(16.4), Y(11.6), top - 0.03, top + 0.004, mat=R_WINDOW)
    # Grey band where the housing meets the collar (row 18).
    box(bm, -hw - 0.012, hw + 0.012, Y(19.2), Y(17.8), 0.08, top - 0.09, mat=R_RIM)

    # Exhaust nozzle (rows 4-9): a glowing bell banded bright (rows 5-6, 8) and dark red (7, 9).
    loft(bm, [(Y(9.6), 4.0 * PX, 0.28, ZC), (Y(8.0), 4.2 * PX, 0.3, ZC), (Y(7.0), 4.4 * PX, 0.31, ZC),
              (Y(6.0), 3.9 * PX, 0.28, ZC), (Y(5.0), 3.0 * PX, 0.22, ZC), (Y(4.2), 1.8 * PX, 0.13, ZC),
              (Y(3.7), 0.0, 0.0, ZC)], sides=14, mat=R_GLOW)
    hot2 = R_HOT2 if animate else R_HOT
    for R0, R1, w0, w1, h0, h1, m in ((5.0, 6.5, 3.15, 4.1, 0.23, 0.295, R_HOT), (7.65, 8.45, 4.4, 4.35, 0.31, 0.305, hot2),
                                      (6.55, 7.45, 4.65, 4.65, 0.33, 0.33, R_RING), (8.55, 9.5, 4.3, 4.3, 0.31, 0.31, R_RING)):
        loft(bm, [(Y(R1), w1 * PX, h1, ZC), (Y(R0), w0 * PX, h0, ZC)], sides=14, mat=m)
    for s in (-1, 1):
        box(bm, *sorted((s * 4.6 * PX, s * 5.6 * PX)), Y(9.6), Y(7.6), ZC - 0.18, ZC + 0.12, mat=R_LUG,
            bevel=0.02)


def build_sparks(bm, frame, mat_of):
    """The bright pixels running along the slits on this frame of newsh8-191 (SLIT_SPARKS), raised
    a little over the slit; mat_of[palette index] is each one's material slot."""
    for R, c, i in SLIT_SPARKS[frame]:
        L = c - 11
        z0 = _hull_top(R, abs(L) + 0.5) - 0.03
        box(bm, (L - 0.5) * PX, (L + 0.5) * PX, -(R + 0.45) * PX, -(R - 0.45) * PX, z0, _hull_top(R) + 0.028,
            mat=mat_of[i])


def place(obj, matrix):
    """Apply a transform to an object's mesh in place."""
    obj.data.transform(matrix)
    obj.data.update()


def rocket_matrix(rotate_deg, dx, dy):
    """Rotate the rocket's local frame about Z and move it (units)."""
    return Matrix.Translation((dx, dy, 0)) @ Matrix.Rotation(math.radians(rotate_deg), 4, "Z")


def rocket_assembly(name, root, layout, rotate_deg, dx, dy, rib_side=-1, animate=False):
    """Build the rocket, place it in assembly coordinates (Blender units with the assembly's centre
    at the origin), cut it into its pieces and export each; `layout` is [(piece, cx, cy), ...] in
    pixels from that centre. With `-- --preview out.png` renders the whole rocket to out.png and
    each piece to <piece>.png beside it. `animate` (the standing rocket, newsh8-153 over
    newsh8-191) makes the exhaust pulse and the slits' sparks run with the frames; then
    `-- --frames dir` renders every frame of each piece to <piece>-frames.png in dir."""
    pieces = [p for p, _, _ in layout]
    sprite = merged_sprite(root, pieces)
    coll = common.reset_collection(name)
    bm = bmesh.new()
    build_rocket(bm, rib_side, animate)
    tag = name.replace("assembly-", "")
    obj = to_object(name, bm, rocket_mats(sprite, tag, animate), coll)
    matrix = rocket_matrix(rotate_deg, dx, dy)
    place(obj, matrix)
    parts = common.split_assembly(obj, layout)
    objects = {piece: [parts[piece]] for piece in pieces}
    if animate:
        indices = sorted({i for sparks in SLIT_SPARKS.values() for *_, i in sparks})
        mats = [common.palette_material(sprite, i, f"{tag}-spark", emission_strength=5.0) for i in indices]
        for frame in SLIT_SPARKS:
            sbm = bmesh.new()
            build_sparks(sbm, frame, {i: k for k, i in enumerate(indices)})
            sparks = to_object(f"{name}-sparks-{frame}", sbm, mats, coll)
            place(sparks, matrix)
            for piece, part in common.split_assembly(sparks, layout).items():
                if part.data.polygons:
                    part.name = f"{piece}-sparks-{frame}"
                    objects[piece].append(common.frame_part(part, [frame]))
    for piece in pieces:
        data = common.load_sprite(root, piece)
        common.export_sprite_model(root, objects[piece], f"enemies/{piece}", data["sprites"])
        if "--frames" in sys.argv:
            out = Path(sys.argv[sys.argv.index("--frames") + 1]) / f"{piece}-frames.png"
            common.render_frame_previews(objects[piece], str(out), data, root)
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = composite_png(root, layout, Path(tempfile.mkdtemp()) / "assembly.png", 48, 56)
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for piece in pieces:
            data = common.load_sprite(root, piece)
            img = root / "reference" / "models" / piece / data["frames"][0]["image"]
            common.render_preview([parts[piece]], str(out.parent / f"{piece}.png"), img, size=2)
