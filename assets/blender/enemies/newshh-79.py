"""Grey dome (newshh.shp frame 79): the silver cap on the organism's stalk, a 3D version of its sprites.
The damaged frame 41 is drawn with this intact model (D87). Built by lib_b063's helpers; the shape lives here.

QA 2026-11-17: in game the cap read dull slate where the sprite draws BRIGHT SILVER with a white crown highlight,
so it is repainted with the sprite's own ramp by plan row, on the cap's row rings (so every boundary is a clean
ring): the crown (rows 17-22) 108 (round 3; it was 109), the band under it (rows 23-24, 106-107) 107, the south lip
(rows 25-27, 104-106) 106, the lip's camera-facing face 104. Nearly no metal (lib's 0.55-0.6 renders this mid-grey
steel charcoal, D201), a tight roughness and full F0 (D176), so the white of 110-111 comes as sheen on the crown.

QA 2026-11-18 (round 3): lib_b063's cap (a superellipse section, n 2.6, under a crown that rose over the north six
rows and then ran level to the lip) was a flat-topped drum: its whole top faced straight up, so no face turned to
the sun/camera half vector and the sprite's white crown hotspot (111, rows 19-21, cols 7-11) never lit (max 236 vs
253), and the level top over a vertical lip read as a cylinder with a side band. Now the cap is a dome: a true
ellipse section across (SECTION_N) under a crown profile that rises from the north rim to a peak at DOME_PEAK and
falls on a rounded even slope (a hyperbola) to a short rounded lip at the south face, taller (DOME_TOP). The half
vector of the game's sun (sun.ts, from the left and the camera's side) and its 32-degree camera leans south and a
little west, so the hotspot lands on the dome's south-west shoulder, west of the cap's centre like the sprite's
(in game at t2550: max luma 254 vs the sprite's 253). The crown takes 108, its own region's median (rows 17-22:
median 107, rows 19-21: 108; 109 was a step above it and washed the hotspot out: in-game crown median 206 vs the
sprite's 197, now 190). The plan (row extents of the sprite's inner mask) is lib_b063's, unchanged, so the top view
is the sprite's. lib_b063 is shared with the
block, orbs and thorn, so its build_cap is replaced here, not edited.

QA 2026-11-18 (round 4): the round-3 hotspot peaked right (254) but covered 118 px at >= 240 against the sprite's 396,
and as a broken, streaky sheen; the 108/107/106 row rings drew two hard stripes (D228/D229: no painted tone bands);
the cap was pale (median 179 vs 168, lower half 157 vs 142). The streaks were the RoomEnvironment's light panels in a
0.18-rough sheen, broken further by a crease at every plan row (a linear read of the row extents). Now:
- the plan is the row extents read through a Gaussian (no row creases; IoU 0.96, grid 1.0), the section n 1.8 and
  the crown's profile is drawn by its slope angle: a gentle north rise (visible to the camera, so grey above the
  hotspot), the peak at row 20.3, an even 24-30 degree lean over rows 22.3-24 (about the half vector of the sun and
  the camera, so the sun's lobe lands there, west of centre as the sprite's blob) and a shoulder that turns to
  80 degrees at the south rim;
- each face keeps the sprite's index for its row (108 crown, 107, 106, 105, 104), and a colour multiplier (a
  texture by row) draws the shade between them continuously, so no boundary shows; it also takes the crown and lip
  a little under their flat index, as the lit 3D surface reads brighter than the flat sprite;
- the sheen is a material map, not paint: one polished patch (high F0, roughness 0.37) where the sun's lobe falls,
  the rest of the crown satin (roughness 0.5, a fraction of the F0) and the lower cap nearly matte (0.7, little
  F0), so the environment's panels blur into an even sheen instead of streaks and the lower cap stays grey, as
  D176's polished patch on the steel ball.
In game (t2550, 4K, compare=1): max 252, 352 px >= 240 (sprite 396), one blob at (0.45, 0.29) of the cap box
(sprite 0.42, 0.33); lit median 173 (168), halves 186/146 (168/142).

Run: blender --background --python assets/blender/enemies/newshh-79.py
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import lib_b063 as lib  # noqa: E402

SPEC = 8.5  # Specular IOR Level (F0 about 0.34 where the sheen map is 1: the polished patch)
RAMP = {i: (0.08, 0.45, SPEC) for i in (104, 105, 106, 107, 108)}  # metallic, roughness (the map's), spec
# Each face's index: the sprite's for its plan row (rows 17-22 108, 23 107, 24 106, 25 105, 26-27 104).
ROW_INDEX = {23: 107, 24: 106, 25: 105, 26: 104, 27: 104}
# The shade drawn, by plan row, as a continuous palette index: under each face's own index (the colour multiplier
# takes it there), a little under the sprite's flat colours as the lit surface reads brighter than the flat sprite.
SHADE = [(17.2, 106.5), (18.6, 106.6), (22.6, 106.6), (23.5, 106.6), (24.5, 105.0), (25.5, 104.0), (26.5, 103.0),
         (27.5, 103.0)]
ROUGH_ROWS = (21.5, 25.5)  # the roughness and sheen ease from the crown's to the lower cap's over these rows
ROUGH = (0.5, 0.7)  # crown, lower cap
SHEEN = (0.12, 0.04)  # the crown's and the lower cap's F0, as a fraction of the patch's
METAL = 0.08
# The polished patch, where the sun's lobe falls (the sprite's 110-111 blob, rows 19-21, cols 7-11 seen in game):
# centre col, row, sigma col, row (px); its roughness.
PATCH = (9.0, 21.1, 4.6, 2.4)
PATCH_ROUGH = 0.37
XM = 0.08  # margin of each index's block in the maps (no bleed from the next block)
NORTH_FLOOR = 0.6  # crown height at the north rim, fraction of the top (a gentle north rise the camera sees)
DOME_PEAK = 20.3  # plan row of the crown's highest point
# South of the peak, the profile's slope angle (degrees): rising to LEAN[0] at LEAN_ROW, LEAN[1] at SHOULDER, then
# evenly to SIDE_ANGLE at the south rim. The top's height follows from the angles (about 9.4 px over the sole).
LEAN_ROW, SHOULDER = 22.3, 24.0
LEAN = (24.0, 30.0)
SIDE_ANGLE = 80.0
LIP_Z = 0.5  # px over the sole where the side meets the sole's edge
PLAN_SIGMA = 0.7  # rows: the Gaussian read of the plan's row extents
PLAN_RIM = 3.0  # half width just north of the plan (pads the read)
SECTION_N = 1.8  # superellipse exponent across X (2 an ellipse; lib's 2.6 was a flat-topped drum)
Z_BASE = lib.Z_B  # same sole as the block it stands on


def build_cap(coll):
    """Tile pixel corner coords (col 0..24, row 0..28); the shell fills rows 0-12 at the tile's bottom (rows 16-28).
    Ellipse sections across X per plan row (the plan is lib_b063's), the crown a dome along the rows."""
    sp = lib.load("newshh-79")
    ext = lib.inner_extents("newshh-79")  # the shell's inner mask (its ink ring is the game's outline)
    rows = sorted(ext)
    r0, r1 = rows[0], rows[-1] + 1  # 17, 28
    mats, slot = [], {}
    for i, (m, rgh, spec) in RAMP.items():
        slot[i] = len(mats)
        mat = lib.common.palette_material(sp, i, "nshh79C", metallic=m, roughness=rgh)
        lib.set_spec(mat, spec)
        mats.append(mat)

    def TX(c):
        return (c - 12) * lib.PX

    def TY(r):
        return (14 - r) * lib.PX

    z0 = Z_BASE
    inset = 0.1
    # The row extents (pixel edges) as centre and half width per row, read through a Gaussian (PLAN_SIGMA rows): a
    # plan with no crease at any row (lib_b063's linear read creased every row, which broke the sheen into streaks).
    raw = {r: ((ext[r][0] + ext[r][1]) / 2, (ext[r][1] - ext[r][0]) / 2) for r in rows}
    raw[r0 - 1] = (raw[r0][0], PLAN_RIM)

    def halfw(rf):
        y = rf - 0.5
        ws = cs = tot = 0.0
        for r in range(r0 - 1, r1 + 3):
            c, w = raw[min(r, r1 - 1)]
            g = math.exp(-0.5 * ((y - r) / PLAN_SIGMA) ** 2)
            ws, cs, tot = ws + g * w, cs + g * c, tot + g
        return cs / tot, ws / tot - inset

    # South of the peak the crown is drawn by its slope angle: level at the peak, an even lean (LEAN, about the
    # sun/camera half vector's) over the crown, where the hotspot spreads, then the shoulder turns down to SIDE_ANGLE
    # at the south rim: that steep side faces away from the high sun and darkens by itself, the sprite's lower cap.
    def angle(rf):
        if rf <= LEAN_ROW:
            return LEAN[0] * math.sin(0.5 * math.pi * (rf - DOME_PEAK) / (LEAN_ROW - DOME_PEAK))
        if rf <= SHOULDER:
            return LEAN[0] + (LEAN[1] - LEAN[0]) * (rf - LEAN_ROW) / (SHOULDER - LEAN_ROW)
        t = min((rf - SHOULDER) / (r1 - SHOULDER), 1.0)
        return LEAN[1] + (SIDE_ANGLE - LEAN[1]) * t

    steps = 400
    zs, h = [0.0], (r1 - DOME_PEAK) / steps
    for k in range(steps):
        zs.append(zs[-1] + math.tan(math.radians(angle(DOME_PEAK + (k + 0.5) * h))) * h)
    top = LIP_Z + zs[-1]

    def crown(rf):
        # px over the sole: a quarter ellipse up from the north rim to the peak, the slope profile down to the lip.
        if rf <= DOME_PEAK:
            d = (DOME_PEAK - rf) / (DOME_PEAK - r0)
            return top * (NORTH_FLOOR + (1 - NORTH_FLOOR) * math.sqrt(max(0.0, 1 - d * d)))
        f = min((rf - DOME_PEAK) / h, steps - 1e-9)
        k = int(f)
        return top - (zs[k] + (zs[k + 1] - zs[k]) * (f - k))

    bm = bmesh.new()
    stations = []
    nrow = 120
    for k in range(nrow + 1):
        t = k / nrow
        # stations crowd toward the south lip, where the side turns vertical
        t = 1 - (1 - t) ** 1.6
        rf = r0 + 0.25 + (r1 - 0.02 - (r0 + 0.25)) * t
        cen, w = halfw(rf)
        stations.append((cen, rf, max(w, 0.3), z0 + crown(rf)))
    rings = []
    for cen, rf, w, zt in stations:
        ring = [bm.verts.new((TX(cen + x), TY(rf), z * lib.PX))
                for x, z in lib.d_section(w, z0, zt, 64, n=SECTION_N)]
        rings.append(ring)
    m = len(rings[0])
    for ra, rb in zip(rings, rings[1:]):
        for k in range(m):
            j = (k + 1) % m
            bm.faces.new((ra[k], ra[j], rb[j], rb[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bm.normal_update()
    # Faces take the sprite's index for their row (ROW_INDEX), and a colour multiplier draws SHADE over it: a face of
    # index k is drawn at the shade's colour over k's, so the cap's colour runs on smoothly from the crown to the lip
    # with no ring edge (the live palette still sets each index). UV: u = the index's block + the plan column, v = row.
    uv = bm.loops.layers.uv.new("bake")
    for n, f in enumerate(bm.faces):
        if n >= nrow * m:  # the end faces: the sole's rim and the north end
            k = 104
        else:
            k = ROW_INDEX.get(int(14 - f.calc_center_median().y / lib.PX), 108)
        f.material_index = slot[k]
        f.smooth = n < nrow * m
        for lp in f.loops:
            r = 14 - lp.vert.co.y / lib.PX
            c = min(max((lp.vert.co.x / lib.PX + 12) / 24, 0.0), 1.0)
            lp[uv].uv = ((k - 104 + XM + (1 - 2 * XM) * c) / 5, min(max((r - 16) / 12, 0.0), 1.0))
    ob = lib.mesh_obj(coll, "newshh-79", bm, mats)
    ramp_maps(sp, mats, slot)
    return ob, sp


def shade(r):
    """The cap's shade at plan row r, as a continuous palette index (piecewise linear through SHADE)."""
    if r <= SHADE[0][0]:
        return SHADE[0][1]
    for (ra, va), (rb, vb) in zip(SHADE, SHADE[1:]):
        if r <= rb:
            return va + (vb - va) * (r - ra) / (rb - ra)
    return SHADE[-1][1]


def ramp_maps(sp, mats, slot):
    """The maps, one block per index (104-108), each across the plan's columns and down its rows: the colour multiplier
    (SHADE over the index), roughness/metalness and the sheen's strength (specular tint), the polished patch in both."""
    import bpy

    def lin(i):
        return lib.common.srgb(*sp["colors"][str(i)])

    def to_srgb(c):
        c = min(max(c, 0.0), 1.0)
        return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055

    XW, H = 48, 256  # texels across one index's block (the plan's 24 columns), and down the plan's rows 16-28
    W = 5 * XW
    col = bpy.data.images.new("nshh79_shade", W, H, alpha=False)
    rm = bpy.data.images.new("nshh79_rm", W, H, alpha=False)
    rm.colorspace_settings.name = "Non-Color"
    spec = bpy.data.images.new("nshh79_spec", W, H, alpha=False)  # the sheen's strength (specular tint)
    cpx, rpx, spx = [], [], []

    def smooth(a, b, x):
        t = min(max((x - a) / (b - a), 0.0), 1.0)
        return t * t * (3 - 2 * t)

    for y in range(H):
        r = 16 + 12 * (y + 0.5) / H
        e = shade(r)
        lo = math.floor(e)
        a, b = lin(min(lo, 108)), lin(min(lo + 1, 108))
        t = e - lo
        want = [a[c] + (b[c] - a[c]) * t for c in range(3)]
        u = smooth(ROUGH_ROWS[0], ROUGH_ROWS[1], r)
        rough_r = ROUGH[0] + (ROUGH[1] - ROUGH[0]) * u
        spec_r = SHEEN[0] + (SHEEN[1] - SHEEN[0]) * u
        cols = []
        for xi in range(XW):
            xn = min(max(((xi + 0.5) / XW - XM) / (1 - 2 * XM), 0.0), 1.0)
            pc = xn * 24
            pw = math.exp(-0.5 * (((pc - PATCH[0]) / PATCH[2]) ** 2 + ((r - PATCH[1]) / PATCH[3]) ** 2))
            cols.append((rough_r + (PATCH_ROUGH - rough_r) * pw, spec_r + (1 - spec_r) * pw))
        for k in range(104, 109):
            base = lin(k)
            mul = [to_srgb(min(want[c] / base[c], 1.0)) for c in range(3)]
            cpx += (mul + [1.0]) * XW
            for rg, sv in cols:
                rpx += [1.0, rg, METAL, 1.0]
                sv = to_srgb(sv)
                spx += [sv, sv, sv, 1.0]
    col.pixels = cpx
    rm.pixels = rpx
    spec.pixels = spx
    for img in (col, rm, spec):
        img.pack()
    for mat in mats:
        nt = mat.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])
        st = nt.nodes.new("ShaderNodeTexImage")
        st.image = spec
        nt.links.new(uvn.outputs["UV"], st.inputs["Vector"])
        nt.links.new(st.outputs["Color"], bsdf.inputs["Specular Tint"])


lib.build_cap = build_cap

if __name__ == "__main__":
    lib.export_cap()
