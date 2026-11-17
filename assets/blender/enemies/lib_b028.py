"""Shared builder for the EYESPY (4.13) boss's two limbs: assembly-newsh9-39 (newsh9 1/3/39) and
assembly-newsh9-45 (newsh9 5/7/45, its pixel mirror one px over). DECISIONS.md D227.

WHAT IT IS. The eye boss's LEGS, drawn upside down. The level flips the screen (smoothie 9) from
t7511, four seconds after the limbs close round the eye, and stays flipped for the rest of the
fight: 6,530 of the limbs' 7,131 ticks. So the top of the 48 x 56 drawing is the bottom of the
screen, and the boss is an eyeball standing on two feet with a pincer raised each side:
- the FOOT (rows 2-13, cols 24-46; the older builds' "shoulder housing"): a rounded pad lying across
  the screen, mid-dark grey (mean luma 78), darker toward its ends, with two small TOE studs on its
  crown (cols 35-38 and 40-42), each a 3 x 4 px highlight;
- the ANKLE (rows 8-12, cols 18-35), a lower neck into
- the COWL (rows 11-18): a light wedge (pal 9) with a dark FLANK (pal 3-4) down its outer side, its
  lit edge running on as the bevel of the BOX (rows 13-22, cols 34-44) across a dark HOLLOW with
  two thin rods; the eye covers nearly all of the box and the hollow while the limbs are closed;
- the BEAM (pal 5, rows 19-27) slanting out to the knee, its UNDER side rolling into the dark
  (pal 2-3, rows 24-30), with a light DRUM (pal 9, rows 19-28) lying along it, lit along one edge;
- the FOREARM (pal 6-7, rows 29-38), a short tube, beside
- the PINCER: a RING of tube (rows 31-38, its outer leg the one bright run, pal 9-11) round a dark
  PIT, and a FINGER (rows 39-46) holding a blue GEM lamp (pal 151-156).

HOW IT IS BUILT (the sprite is the ruler; the method of D213's saw rotor, for round parts).
- Plan: the sprite's inner mask (tools/sprite_mask.py, D74) blurred 0.4 px and cut at one half, on a
  grid of K cells per px, the cut then pulled smooth (`relax`: surface nets). Grid IoU 1.0.
- Plate: the plan as a thin dark slab (pal_1): the ink the sprite draws between the parts shows as
  a groove down to it.
- Relief: every steel pixel stands on the plate as part of one height field, crown height and edge
  radius per part (PARTS, `part`): a lip straight up from the nearest ink or outline, a quarter-round
  shoulder, a level crown; the two toe studs are low domes on the foot's crown. Low on purpose (the
  crowns 2.0-3.4 px, the toes 3.8): the boss fights at the far edge of the playfield, where the
  camera's rays lean about 0.65 px per px of height, and the older builds' 6-7 px foot stood 3-4 px
  past its sprite, toward the bottom of the flipped screen. `tyrian_anchor` (ANCHOR) puts the
  plane of the crowns, not the base, on the camera ray, so the bands sit where the sprite has them.
- Tone bands: the top is cut along the sprite's own tone steps. The steel's luma, blurred 0.4 px
  over the steel only, is divided by what the game's lights add (GAIN, TRIM) and each cell takes
  the nearest grey of the sprite's ramp as its pal_ material, so the bands are the sprite's shading
  at its darkness. The game's sun is nearly overhead: a 3 px high relief cannot shade its own flanks
  to the sprite's 0.3-0.5x (D176), which is why every earlier build came out one pale mass.
- Sheen: the brighter a band the glossier it is (roughness 0.80 at pal 2 down to 0.40 at pal 11
  and up, a steel F0 from pal 10), so the sprite's highlights are still the surface's shine, on the
  bands that carry them. Nearly dielectric (metallic 0.1): a metal band reflects the dark room.
- Gem: the blue pixels as a low dome that glows (D126), cut into its own blues the same way.
- Ink: D90's shell, made from the same relief with the grooves filled and nine tenths as high (one
  smooth pillow under the model, so no fold of it draws a hairline across a part, D213).
No greeble; the underside is the plan, flat.

Units while building: left-drawing pixel EDGES (c right, r down the screen) and z in px; Blender
X = (c - 24) / 12, Y = (28 - r) / 12, Z = z / 12. The right limb is the left mirrored.

Used by assembly-newsh9-39.py (exports the left pieces) and assembly-newsh9-45.py (the right
pieces): run(script_file, side) builds only that side.

    blender -b --factory-startup -P assembly-newsh9-39.py [-- --pieces DIR] [--whole DIR]

--pieces DIR also writes the pieces' glbs to DIR; --whole DIR the whole limb with its shell.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

WT = common.repo_root(__file__)
sys.path.insert(0, str(Path(WT) / "tools"))
import sprite_mask as SM  # noqa: E402

NAME = "assembly-newsh9-39"
TAG = "nsh9arm"
W, H = 48, 56
WINDOWS = {
    "left": {"newsh9-1": (0, 0), "newsh9-3": (24, 0), "newsh9-39": (0, 28)},
    "right": {"newsh9-5": (0, 0), "newsh9-7": (24, 0), "newsh9-45": (24, 28)},
}

K = 3                 # grid cells per sprite px
K_SHELL = 3           # the same for the pillow the outline shell is made from
SIG_MASK = 0.40       # blur (px) of the plan and ink indicators before they are cut at one half
SIG_TONE = 0.40       # blur (px) of the tone field the bands are cut from
SIG_PART = 0.45       # blur (px) of the parts' crown heights and edge radii
Z_PLATE = 1.0         # px: top of the dark plate, the floor of every groove
Z_BOTTOM = 0.6        # px: the model's flat underside (the shell's is at 0)
LIP = 0.4             # the share of a part's rise above the plate that stands straight up at its edge;
                      # the rest is the quarter-round shoulder
Z_RIM = 0.85          # px: the pillow the outline shell is made from is this high at the outline and
PILLOW = 0.9          # this share of the relief's height inside it: under the model everywhere, so no
                      # fold of the shell can draw a hairline across a part (D213)
GAIN = 1.20           # what the game's lights make of a band's grey: luma in game / palette luma, the
                      # mean over the six broad bands pal 2-7 (1.16-1.31; EYESPY t7400 and t7800,
                      # `&compare=1` at 3840x2160)
MIN_CELLS = 4         # a band's specks smaller than this (cells) join their surroundings
GEM_FIRST = 151       # the blue ramp's first index

# The parts: crown height (px above the model's origin plane) and the radius (px) of the
# quarter-round shoulder that rises from the nearest ink or outline.
PARTS = {
    "foot": (3.1, 4.5), "toe": (3.1, 4.5), "ankle": (2.6, 2.2), "cowl": (3.3, 1.4), "flank": (2.4, 2.2),
    "box": (3.1, 1.2), "hollow": (1.5, 1.0), "rod": (2.0, 0.8), "pod": (2.4, 1.6),
    "beam": (2.9, 1.6), "under": (2.0, 2.0), "drum": (3.4, 3.2), "fore": (2.9, 3.0),
    "ring": (2.5, 1.4), "pit": (1.2, 1.0), "finger": (2.4, 1.8), "gem": (2.6, 2.0),
}
# A part whose crown squarely faces the game's sun comes out brighter than GAIN says: its tone is
# divided by this too (the foot measured 1.13x its sprite where the limb as a whole measured 0.99x).
# The small bright spots lose their peak to the tone field's blur and get it back here: the toe
# studs' highlights (144 in the sprite, 106-118 in game without it) and the lamp's glint.
TRIM = {"foot": 1.08, "toe": 0.85, "gem": 0.8}
# The toe studs: (c, r) of each highlight's middle (px edges), height and radius (px) of the dome
# added to the foot's crown.
TOES = [(37.5, 6.2, 0.75, 1.25), (41.5, 7.1, 0.75, 1.2)]
# px: the height of the plane the renderer puts on the camera ray (`tyrian_anchor`, D181), on all six
# pieces. The boss fights at the far edge of the playfield, where the camera's rays lean 0.5-0.7 px
# per px of height: with the base on the ray (0) a 3.8 px foot crown stood 1.5-2 px past its sprite,
# toward the bottom of the flipped screen; with the plane of the crowns on it the painted bands sit
# where the sprite has them (the toe studs on the sprite's own pixels, EYESPY t7485 and t7800).
ANCHOR = 2.2


def part(idx, r, c):
    """Which solid the left drawing's pixel (r, c) belongs to (a key of PARTS)."""
    v = idx[r][c]
    if v >= GEM_FIRST:
        return "gem"
    # the foot pad, the highlights of its two toe studs, and the ankle that joins it to the leg
    if 4 <= r <= 8 and 34 <= c <= 43 and v >= 10:
        return "toe"
    if r <= 8 and c >= 24:
        return "foot"
    if r <= 10:
        return "foot" if c >= 30 else "ankle"
    if r == 11 and c >= 30:
        return "foot" if c >= 36 else "ankle"
    if r == 12 and c >= 32:
        return "foot" if c >= 36 else "ankle"
    if r == 13 and c >= 36:
        return "foot"
    # the gem's finger and the ring
    if r >= 39 and c <= 15:
        return "finger"
    if r >= 31 and c <= 13:
        return "pit" if 34 <= r <= 38 and 7 <= c <= 11 and v <= 4 else "ring"
    if r >= 29 and c >= 14:
        return "fore"
    if r >= 28 and c <= 16:
        return "under"
    # the beam, its dark underside, the light drum
    if r >= 19 and c <= 25:
        if c >= 25 and v <= 4:
            return "hollow"
        if v >= 8 or c >= 22 or (c >= 17 and r >= 26):
            return "drum"
        return "under" if r >= 24 and v <= 4 else "beam"
    # the box with its bright bevel, the dark hollow beside it, the rods and the pod under the box
    if (r >= 14 and c >= 26) or (r == 13 and c >= 34):
        if v >= 9 or (c >= 34 and r <= 22 and v >= 6):
            return "box"
        if v >= 6:
            return "rod"
        return "pod" if r >= 20 and c >= 35 else "hollow"
    # the cowl and its dark outer flank
    return "flank" if v <= 5 and r >= 12 and c <= 26 else "cowl"


# --- the drawing ------------------------------------------------------------------------------------

def merged_sprite():
    data = common.load_sprite(WT, "newsh9-1")
    for side in WINDOWS.values():
        for n in side:
            data["colors"].update(common.load_sprite(WT, n)["colors"])
    return data


def left_drawing():
    """The left limb's 48 x 56 drawing as palette indices (-1 transparent)."""
    idx = [[-1] * W for _ in range(H)]
    for n, (x0, y0) in WINDOWS["left"].items():
        px = common.load_sprite(WT, n)["frames"][0]["pixels"]
        for r, row in enumerate(px):
            for c, v in enumerate(row):
                idx[y0 + r][x0 + c] = v
    return idx


# --- fields (numpy) ---------------------------------------------------------------------------------

def _gauss(sig, k):
    r = max(1, int(math.ceil(3 * sig * k)))
    x = np.arange(-r, r + 1) / k
    g = np.exp(-0.5 * (x / sig) ** 2)
    return g / g.sum()


def blur(a, sig, k):
    """Gaussian blur of a cell field, `sig` in px, zero outside the picture."""
    g = _gauss(sig, k)
    r = len(g) // 2
    p = np.pad(np.asarray(a, float), r, mode="constant")
    for axis in (0, 1):
        out = np.zeros_like(p)
        for i, w in enumerate(g):
            out += w * np.roll(p, i - r, axis=axis)
        p = out
    return p[r:-r, r:-r]


def up(a, k):
    return np.kron(np.asarray(a, float), np.ones((k, k)))


def corners(cell):
    """A cell field at the grid's corners (the mean of the cells round each)."""
    p = np.pad(cell, 1, mode="edge")
    return 0.25 * (p[:-1, :-1] + p[1:, :-1] + p[:-1, 1:] + p[1:, 1:])


def fields(idx, colors, k, filled=False):
    """The relief's fields on a grid of k cells per px: `inside` (the plan), `body` (steel or gem
    standing on the plate), `gem`, `tone` / `gtone` (luma of the steel / the gem, blurred over its
    own pixels) per cell, and `z` (px) per corner. `filled`: the ink between the parts stands too
    (the pillow the outline shell is made from)."""
    a = np.asarray(idx)
    m = SM.masks(idx, colors)
    inner = np.asarray(m["inner"], bool)
    gem = inner & (a >= GEM_FIRST)
    steel = inner & (a >= 2) & ~gem
    body = steel | gem
    lum = np.zeros(a.shape)
    crown = np.zeros(a.shape)
    rad = np.zeros(a.shape)
    for r in range(H):
        for c in range(W):
            if a[r, c] >= 0:
                lum[r, c] = SM.luma(colors[int(a[r, c])])
            if body[r, c]:
                name = part(idx, r, c)
                crown[r, c], rad[r, c] = PARTS[name]
                lum[r, c] /= TRIM.get(name, 1.0)
    inside = blur(up(inner, k), SIG_MASK, k) > 0.5
    stands = inside if filled else inside & (blur(up(body, k), SIG_MASK, k) > 0.5)
    is_gem = stands & (blur(up(gem, k), SIG_MASK, k) > blur(up(steel, k), SIG_MASK, k))

    def nblur(val, mask, sig):
        den = blur(up(mask, k), sig, k)
        return blur(up(val * mask, k), sig, k) / np.maximum(den, 1e-9)

    tone = nblur(lum, steel, SIG_TONE)
    gtone = nblur(lum, gem, SIG_TONE)
    sig = SIG_PART * (2.0 if filled else 1.0)
    cr = corners(nblur(crown, body, sig))
    rr = np.maximum(corners(nblur(rad, body, sig)), 0.3)
    # the toe studs
    ys, xs = np.mgrid[0:H * k + 1, 0:W * k + 1] / k
    for c0, r0, h0, s0 in TOES:
        q = np.clip(np.hypot(xs - c0, ys - r0) / (2.0 * s0), 0, 1)
        cr = cr + h0 * np.sqrt(1 - q * q) * (0.5 + 0.5 * np.cos(np.pi * q))
    # distance (px) of every corner inside the standing part from the nearest corner on its edge
    sb = np.pad(stands, 1, mode="constant")
    interior = sb[:-1, :-1] & sb[1:, :-1] & sb[:-1, 1:] & sb[1:, 1:]
    pi = np.pad(interior, 1, mode="constant")
    edge = ~interior & (pi[:-2, 1:-1] | pi[2:, 1:-1] | pi[1:-1, :-2] | pi[1:-1, 2:]
                        | pi[:-2, :-2] | pi[2:, 2:] | pi[:-2, 2:] | pi[2:, :-2])
    by, bx = np.nonzero(edge)
    iy, ix = np.nonzero(interior)
    d = np.zeros(interior.shape)
    for s in range(0, len(iy), 2000):
        yy, xx = iy[s:s + 2000], ix[s:s + 2000]
        d[yy, xx] = np.sqrt((yy[:, None] - by[None, :]) ** 2 + (xx[:, None] - bx[None, :]) ** 2).min(axis=1) / k
    t = np.clip(d / rr, 0, 1)
    prof = LIP + (1 - LIP) * np.sqrt(1 - (1 - t) ** 2)
    z = np.where(interior, Z_PLATE + (np.maximum(cr, Z_PLATE) - Z_PLATE) * prof, Z_PLATE)
    if filled:
        z = np.maximum(PILLOW * z, Z_RIM)
    return {"inside": inside, "body": stands, "gem": is_gem, "tone": tone, "gtone": gtone, "z": z}


def nearest(field, table):
    """Each cell's nearest entry of {index: luma}, by luma."""
    keys = np.array(sorted(table))
    lum = np.array([table[i] for i in keys])
    return keys[np.abs(field[..., None] - lum[None, None, :]).argmin(axis=2)]


def despeckle(lab, min_cells):
    """Join every 4-connected region of one band smaller than min_cells to the band it borders most."""
    h, w = lab.shape
    lab = lab.copy()
    seen = np.zeros(lab.shape, bool)
    for y in range(h):
        for x in range(w):
            if seen[y, x] or lab[y, x] <= 1:
                continue
            v = lab[y, x]
            stack, comp, nb = [(y, x)], [], {}
            seen[y, x] = True
            while stack:
                cy, cx = stack.pop()
                comp.append((cy, cx))
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < h and 0 <= nx < w:
                        u = int(lab[ny, nx])
                        if u == v:
                            if not seen[ny, nx]:
                                seen[ny, nx] = True
                                stack.append((ny, nx))
                        elif u > 1:
                            nb[u] = nb.get(u, 0) + 1
            if len(comp) < min_cells and nb:
                to = min(nb, key=lambda q: (-nb[q], abs(q - v)))
                for cy, cx in comp:
                    lab[cy, cx] = to
    return lab


def bands(F, colors):
    """Cell labels: -1 outside the plan, 1 the plate (ink), else the palette index painted there:
    the grey that the game shows nearest to the sprite's tone at the cell (GAIN)."""
    greys = {i: GAIN * SM.luma(c) for i, c in colors.items() if 2 <= i < 16}
    blues = {i: SM.luma(c) for i, c in colors.items() if i >= GEM_FIRST}
    lab = np.where(F["gem"], nearest(F["gtone"], blues), nearest(F["tone"], greys))
    lab = np.where(F["body"], lab, 1)
    lab = np.where(F["inside"], lab, -1)
    return despeckle(lab, MIN_CELLS)


def relax(lab, k, iters=4, lam=0.5, clamp=0.42):
    """Surface nets in 2D: the grid's corner positions (px), each corner on a line between two labels
    pulled toward its neighbours along that line and held within `clamp` cells of its place, so the
    cells' stair steps become the smooth cut they sample."""
    h, w = lab.shape
    p = np.pad(lab, 1, mode="constant", constant_values=-1)
    a, b, c, d = p[:-1, :-1], p[:-1, 1:], p[1:, :-1], p[1:, 1:]   # the four cells round each corner
    eu, ed, el, er = a != b, c != d, a != c, b != d               # lines up, down, left, right from it
    ys, xs = np.mgrid[0:h + 1, 0:w + 1].astype(float)
    y0, x0 = ys.copy(), xs.copy()
    n = eu.astype(int) + ed + el + er
    on = n >= 2
    for _ in range(iters):
        sy = np.zeros_like(ys)
        sx = np.zeros_like(xs)
        sy[1:, :] += np.where(eu[1:, :], ys[:-1, :], 0)
        sx[1:, :] += np.where(eu[1:, :], xs[:-1, :], 0)
        sy[:-1, :] += np.where(ed[:-1, :], ys[1:, :], 0)
        sx[:-1, :] += np.where(ed[:-1, :], xs[1:, :], 0)
        sy[:, 1:] += np.where(el[:, 1:], ys[:, :-1], 0)
        sx[:, 1:] += np.where(el[:, 1:], xs[:, :-1], 0)
        sy[:, :-1] += np.where(er[:, :-1], ys[:, 1:], 0)
        sx[:, :-1] += np.where(er[:, :-1], xs[:, 1:], 0)
        ty = np.where(on, sy / np.maximum(n, 1), ys)
        tx = np.where(on, sx / np.maximum(n, 1), xs)
        ys = np.clip(ys + lam * (ty - ys), y0 - clamp, y0 + clamp)
        xs = np.clip(xs + lam * (tx - xs), x0 - clamp, x0 + clamp)
    return xs / k, ys / k


# --- mesh -------------------------------------------------------------------------------------------

def V(c, r, z):
    return Vector(((c - W / 2) / 12, (H / 2 - r) / 12, z / 12))


def solid(bm, lab, xs, ys, z, slot, z_bottom):
    """The closed solid of a labelled grid: a top face per cell at the corners' heights (material
    slot[label]), a wall down to z_bottom round the plan and the plan itself as the flat underside."""
    h, w = lab.shape
    top, low = {}, {}

    def vt(j, i):
        v = top.get((j, i))
        if v is None:
            v = top[(j, i)] = bm.verts.new(V(xs[j, i], ys[j, i], z[j, i]))
        return v

    def vb(j, i):
        v = low.get((j, i))
        if v is None:
            v = low[(j, i)] = bm.verts.new(V(xs[j, i], ys[j, i], z_bottom))
        return v

    inside = lab >= 0
    rim = []
    for j in range(h):
        for i in range(w):
            if not inside[j, i]:
                continue
            f = bm.faces.new((vt(j, i), vt(j + 1, i), vt(j + 1, i + 1), vt(j, i + 1)))
            f.material_index = slot[int(lab[j, i])]
            f.smooth = True
            # walls where the neighbour cell is outside (wound to face out)
            for (dj, di), (p, q) in (((-1, 0), ((j, i + 1), (j, i))), ((1, 0), ((j + 1, i), (j + 1, i + 1))),
                                     ((0, -1), ((j, i), (j + 1, i))), ((0, 1), ((j + 1, i + 1), (j, i + 1)))):
                nj, ni = j + dj, i + di
                if 0 <= nj < h and 0 <= ni < w and inside[nj, ni]:
                    continue
                wall = bm.faces.new((vt(*p), vb(*p), vb(*q), vt(*q)))
                wall.material_index = slot[1]
                wall.smooth = True
                rim.append(bm.edges.get((vb(*p), vb(*q))))
    fill = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=rim)
    for f in fill["geom"]:
        if isinstance(f, bmesh.types.BMFace):
            f.material_index = slot[1]
            f.smooth = False


def mirror(bm):
    for v in bm.verts:
        v.co.x = -v.co.x + 1 / 12
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])


STEEL_SPEC = 0.5 * ((1.0 / 3.0) ** 2 / 0.04)  # F0 of IOR 2.0 via Specular IOR Level (D176)


def band_material(sprite, index):
    """The material of one band: the darker the band the more matte, the brighter the glossier (the
    sprite's highlights are the surface's shine, on the bands that carry them)."""
    if index >= GEM_FIRST:   # the lamp: its own blues, glowing (D126/D173: glow on metallic 1, rough)
        return common.palette_material(sprite, index, TAG, metallic=1.0, roughness=0.7, emission_strength=0.9)
    if index <= 1:           # the plate: the sprite's ink, matte
        return common.palette_material(sprite, index, TAG + "ink", metallic=0.0, roughness=0.9)
    t = min(1.0, max(0.0, (index - 2) / 9.0))
    m = common.palette_material(sprite, index, TAG, metallic=0.10, roughness=0.80 - 0.40 * t)
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if index >= 10 and "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = STEEL_SPEC
    return m


def make_object(name, coll, sprite, idx, colors, side, k, filled=False):
    F = fields(idx, colors, k, filled)
    lab = bands(F, colors)
    if filled:
        lab = np.where(lab >= 0, 1, -1)
    xs, ys = relax(lab, k)
    used = sorted(int(v) for v in np.unique(lab) if v >= 0)
    if 1 not in used:
        used = [1] + used
    slot = {v: i for i, v in enumerate(used)}
    bm = bmesh.new()
    solid(bm, lab, xs, ys, F["z"], slot, 0.0 if filled else Z_BOTTOM)
    if side == "right":
        mirror(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    open_edges = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for v in used:
        mesh.materials.append(band_material(sprite, v))
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj, lab, open_edges


def split_open(obj, layout):
    """Each piece keeps the part of `obj` inside its 24 x 28 px window, open along the cut (the
    neighbouring piece closes the surface; no cap wall to show where the renderer lifts a piece, D181)."""
    result = {}
    coll = obj.users_collection[0]
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 12 / 12, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        for mt in obj.data.materials:
            mesh.materials.append(mt)
        piece = bpy.data.objects.new(name, mesh)
        coll.objects.link(piece)
        result[name] = piece
    return result


def drop_unused_materials(obj):
    """Keep only the material slots the piece's faces use (a band that lies wholly in another piece)."""
    me = obj.data
    used = sorted({p.material_index for p in me.polygons})
    mats = [me.materials[i] for i in used]
    remap = {old: new for new, old in enumerate(used)}
    index = [remap[p.material_index] for p in me.polygons]
    me.materials.clear()   # (this resets every face to slot 0)
    for m in mats:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", index)
    me.update()


def layout(side):
    return [(n, x0 + 12 - W / 2, y0 + 14 - H / 2) for n, (x0, y0) in WINDOWS[side].items()]


def finish_normals(obj):
    obj.data.shade_smooth()
    obj.data.set_sharp_from_angle(angle=math.radians(40))


def make_side(side):
    sprite = merged_sprite()
    colors = {int(i): tuple(c) for i, c in sprite["colors"].items()}
    idx = left_drawing()
    coll = common.reset_collection(f"{NAME}-{side}")
    obj, lab, open_edges = make_object(f"{NAME}-{side}", coll, sprite, idx, colors, side, K)
    bpy.context.view_layer.update()
    pillow, _, _ = make_object(f"{NAME}-{side}-pillow", coll, sprite, idx, colors, side, K_SHELL, filled=True)
    shell = common.outline_shell(pillow, coll, voxel=0.012, faces=5000, smooth=4, inside=0.004, islands="outer")
    bpy.data.objects.remove(pillow, do_unlink=True)
    shell.name = f"{NAME}-{side}_outline"
    finish_normals(obj)
    lay = layout(side)
    bodies = split_open(obj, lay)
    shells = split_open(shell, lay)
    pieces = []
    for n, _, _ in lay:
        b, sh = bodies[n], shells[n]
        b.name = n
        sh.name = f"{n}_outline"
        sh["tyrian_outline"] = True
        b["tyrian_anchor"] = sh["tyrian_anchor"] = ANCHOR / 12
        drop_unused_materials(b)
        finish_normals(b)
        sh.data.shade_smooth()
        if len(sh.data.polygons) == 0:
            print(f"WARNING: {n} outline has no mesh")
        pieces.append((n, b, sh))
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    share = {int(v): int((lab == v).sum()) for v in np.unique(lab) if v >= 0}
    print(f"{NAME} ({side}): whole {tris} tris, {open_edges} open edges, z max "
          f"{max(v.co.z for v in obj.data.vertices) * 12:.2f} px, bands (cells) {share}; "
          + ", ".join(f"{n} {sum(len(p.vertices) - 2 for p in b.data.polygons)} tris / "
                      f"{len(b.data.materials)} materials / shell {len(sh.data.polygons)} faces" for n, b, sh in pieces))
    return obj, shell, pieces


def run(script_file, side):
    """Build one limb and export its three pieces (models and spriteModels entries)."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    obj, shell, pieces = make_side(side)
    root = common.repo_root(script_file)
    for n, b, sh in pieces:
        data = common.load_sprite(root, n)
        common.export_sprite_model(root, [b, sh], f"enemies/{n}", data["sprites"])
    if "--pieces" in argv:  # review output only
        pdir = Path(argv[argv.index("--pieces") + 1])
        for n, b, sh in pieces:
            common.export_glb([b, sh], str(pdir / f"{n}.glb"))
    if "--whole" in argv:  # review output only
        wdir = Path(argv[argv.index("--whole") + 1])
        shell["tyrian_outline"] = True
        common.export_glb([obj, shell], str(wdir / f"{Path(script_file).stem}.glb"))
