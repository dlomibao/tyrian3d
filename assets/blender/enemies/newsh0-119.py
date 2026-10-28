"""Snapping skull head (newsh0.shp frames 119, 121, 123, 129): a 3D version of its sprite.

Seen in episode 2 (level 2.12). A blue-steel demon skull seen from above: a domed cranium with a
pale crest down the middle, slanted glowing red eyes set in dark sockets under the brow,
cheekbones curving down to the corners of the mouth, the crest's two prongs running down into a
deep dark mouth, and a lower jaw (side arms, three teeth and a round chin) that slides up and down.

The head is a smooth height field over the sprite's own pixels, so the outline is the sprite's. Its
colours are the parts' mid-tones, not the sprite's drawn light (no outline ring, no baked shading or
hot spots): polished blue steel (metallic, smooth) that the game's lights shade, a pale crest and
prongs, a darker jaw, red eyes and a dark mouth and sockets. The shape is a dome
about 9 px tall at the crest that rolls down to the underside at the outline (no skirt wall; the
staircase's step pixels are split so the rim is one smooth edge), with the eye sockets about
2.5 px deep. Every corner has one height per part (head, jaw), relaxed so the surface is one
continuous dome without peaks or fins. The mouth is cut in with a wall: its floor is a dark ramp
(tilted away from the light so it stays black), and the crest's two prongs are painted on it.
Only the mouth's edge and the jaw's edge against the head keep walls. The eyes are the sockets'
red pixels, flat and matte at the socket floor; the lower teeth are the floor's lighter pixels.

The four frames only move the jaw: 123 closed (jaw 4 px up), 121 (2 px up), 119, 129 wide open
(2 px down). Each jaw position is its own model, built from its own frame's pixels: newsh0-119
(frame 119), newsh0-119-f2 (121), newsh0-119-f3 (123), newsh0-119-f4 (129).

Run: blender --background --python assets/blender/enemies/newsh0-119.py [-- --preview out.png]
(the preview is frame 119; the other jaw positions go to <out>-f2.png ... next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b025 as lib  # noqa: E402
from lib_b025 import common  # noqa: E402

NAME = "newsh0-119"
ROOT = common.repo_root(__file__)
G = lib.Grid(24, 28)
U = 1 / 12
AXE = 11.5  # the skull is mirror symmetric about the centre of column 11 (pixel-edge x 11.5)
# (model name, frame, jaw offset in px down from frame 119's position)
MODELS = [(NAME, 119, 0), (f"{NAME}-f2", 121, -2), (f"{NAME}-f3", 123, -4), (f"{NAME}-f4", 129, 2)]

BASE = -1.0  # underside, px
FLOOR = -0.5  # floor of the mouth, px (at its right edge; the underside is at BASE)
FLOOR_TILT = 0.3  # px of rise per px to the left
EDGE = BASE  # the dome's height at the outline, px: it rolls down to the underside (no skirt wall)
R_FALL = 4.5  # px over which the dome rounds off to the outline
SOCKET = 2.5  # eye socket depth, px
RECESS = ("floor", "socket", "prong")  # kinds cut into the surface (the prongs are painted on the floor)
MOUTH = ("floor", "prong")  # cut in with a wall: the surface rolls part way down (LIP), then drops
LIP = 0.5
DIST_SMOOTH = 4  # passes smoothing the distance-to-outline field (rounds the staircase outline off)
H_SMOOTH = 3  # passes smoothing the finished heights (no peaks or fins)
DARK = (1, 48, 49)
# Colours: the sprite draws its light (outline ring, dark lower-right, near-white hot spots); the game
# lights the model and draws the outline, so each part takes one mid-tone and the light shades it.
METAL, ROUGH = 0.75, 0.3  # the skull's steel: the game's lights make its sheen
BODY = 54  # the cranium and cheeks: blue steel
CREST = 58  # the pale crest down the middle and its two prongs (a real marking)
JAW = 52  # the jaw's arms and chin
TOOTH = 56  # the lower teeth, painted on the mouth floor
VOID = 48  # the mouth floor and the eye sockets' dark (cut in)


def floor_z(x):
    """The mouth floor (px): a ramp falling gently to the right, so its faces turn away from the
    upper-left light and the floor stays a dark void (a level floor catches the studio sheen)."""
    return FLOOR + FLOOR_TILT * max(0.0, 16.5 - x)


def quant(idx):
    """Sprite palette index -> the index its face uses (the blue ramp in steps of two)."""
    if idx == 1:
        return 48
    if 48 <= idx <= 62:
        return idx - (idx % 2) if idx < 55 else idx + (idx % 2)
    if idx in (112, 113):
        return 113
    if 114 <= idx <= 116:
        return 116
    return idx


def mirror_dist(x):
    """Distance from the centre line, in px."""
    return abs(x - AXE)


def seg_dist(x, y, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(x - ax - t * dx, y - ay - t * dy)


class Shape:
    """Heights (px) of one frame's height field at pixel-edge points (x, y): column / row edges."""

    def __init__(self, pix, off):
        self.pix, self.off = pix, off
        self.h, self.w = len(pix), len(pix[0])
        self.jaw_row = min(14, 17 + off)
        self.empty = [(c, r) for r in range(self.h + 1) for c in range(-1, self.w + 1)
                      if not self.filled(c, r)]
        self.dcache = {}
        self.kinds = {(c, r): self.kind(c, r) for r in range(self.h) for c in range(self.w)
                      if pix[r][c] >= 0}
        self.dsmooth = None
        self.dsmooth = self.smooth_dist()
        self.hv = self.solve()

    @staticmethod
    def around(x, y):
        return ((x - 1, y - 1), (x, y - 1), (x, y), (x - 1, y))

    def graph(self, pixels):
        """Vertices (pixel corners) of the given pixels, and each one's neighbours along their edges."""
        vs = {v for c, r in pixels for v in ((c, r), (c + 1, r), (c, r + 1), (c + 1, r + 1))}
        nb = {v: [] for v in vs}
        for c, r in pixels:
            ring = [(c, r), (c + 1, r), (c + 1, r + 1), (c, r + 1)]
            for i in range(4):
                a, b = ring[i], ring[(i + 1) % 4]
                if b not in nb[a]:
                    nb[a].append(b)
                    nb[b].append(a)
        return vs, nb

    def on_outline(self, v):
        x, y = v
        return any(not self.filled(c, r) for c, r in self.around(x, y))

    @staticmethod
    def relax(vals, nb, fixed, passes, lam=0.5):
        for _ in range(passes):
            vals = {v: z if v in fixed else (1 - lam) * z + lam * sum(vals[u] for u in nb[v]) / len(nb[v])
                    for v, z in vals.items()}
        return vals

    def smooth_dist(self):
        """Distance to the outline at every corner, relaxed so the sprite's pixel staircase rounds
        off into one smooth edge (outline corners stay at 0)."""
        vs, nb = self.graph(list(self.kinds))
        d = {v: self.dist(*v) for v in vs}
        fixed = {v for v in vs if self.on_outline(v)}
        return self.relax(d, nb, fixed, DIST_SMOOTH)

    def solve(self):
        """One height per corner per group (head, jaw): the group's surface, cut down by the share
        of recess pixels (mouth floor, eye sockets) around the corner, then relaxed so the surface
        is one continuous dome without peaks. The outline sits at EDGE."""
        hv = {}
        for g in ("head", "jaw"):
            pixels = [p for p in self.kinds if self.group(p) == g and self.kinds[p] not in MOUTH]
            vs, nb = self.graph(pixels)
            fixed = {v for v in vs if self.on_outline(v)}
            vals = {}
            for v in vs:
                x, y = v
                if v in fixed:
                    vals[v] = EDGE
                    continue
                ps = [q for q in self.around(x, y) if q in self.kinds and self.group(q) == g]
                surf = [self.z(self.kinds[q], x, y) for q in ps if self.kinds[q] not in RECESS]
                cut = [self.z(self.kinds[q], x, y) for q in ps if self.kinds[q] in RECESS]
                w = sum(LIP if self.kinds[q] in MOUTH else 1.0 for q in ps if self.kinds[q] in RECESS) / len(ps)
                s = sum(surf) / len(surf) if surf else (self.skull(x, y) if g == "head" else 0.0)
                rz = sum(cut) / len(cut) if cut else 0.0
                vals[v] = s * (1 - w) + rz * w
            vals = self.relax(vals, nb, fixed, H_SMOOTH, 0.45)
            for v, z in vals.items():
                hv[(g, v)] = z
        return hv

    def paint(self, c, r):
        """Palette index a pixel's faces use: its part's mid-tone, not the sprite's drawn shading."""
        idx, k = self.pix[r][c], self.kinds[(c, r)]
        if k == "socket":
            return idx if idx >= 112 else VOID  # the eyes keep their red; the socket's dark stays
        if k == "floor":
            return TOOTH if 52 <= idx <= 62 else VOID
        if k == "prong":
            return CREST
        if k in ("arm", "chin"):
            return JAW
        if (r <= 5 and 9 <= c <= 13) or (r <= 8 and c in (9, 13)):
            return CREST
        return BODY

    def group(self, p):
        return "jaw" if p[1] >= self.jaw_row else "head"

    def corner(self, p, x, y):
        """Height (px) of pixel p's top corner at pixel-edge point (x, y): shared by every pixel of
        its group around the point, so the surface is continuous (walls only where the jaw meets
        the head)."""
        if self.kinds[p] in MOUTH:
            return self.z(self.kinds[p], x, y)
        return self.hv[(self.group(p), (x, y))]

    def filled(self, c, r):
        if r < 0:
            return True  # nothing above the top row: treated separately
        return 0 <= c < self.w and 0 <= r < self.h and self.pix[r][c] >= 0

    def edge(self, c, r):
        return any(not self.filled(c + dc, r + dr) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)))

    def dist(self, x, y):
        """Distance from an edge point to the nearest empty pixel (the top edge counts 1.5 px away)."""
        key = (x, y)
        if self.dsmooth is not None:
            return self.dsmooth[key]
        if key not in self.dcache:
            best = y + 0.5
            for c, r in self.empty:
                dx = max(c - x, 0, x - (c + 1))
                dy = max(r - y, 0, y - (r + 1))
                best = min(best, math.hypot(dx, dy))
            self.dcache[key] = best
        return self.dcache[key]

    def kind(self, c, r):
        idx = self.pix[r][c]
        if r >= self.jaw_row:
            jr = r - self.off
            if jr >= 19:
                return "chin"
            if c <= 7 or c >= 15:
                return "arm"
            return "floor"
        if 112 <= idx <= 119:
            return "socket"
        if idx in DARK and not self.edge(c, r):
            if r >= 9 and 6 <= c <= 16:  # row 8's lone dark pixels are painted on: a straight upper lip
                return "floor"
            if 2 <= r <= 7 and (2 <= c <= 8 or 14 <= c <= 20):
                return "socket"
        if c in (9, 13) and 9 <= r <= 11:
            return "prong"
        return "skull"

    def skull(self, x, y):
        """The domed cranium and cheeks."""
        crown = 8.0 if y <= 6 else 8.0 - 2.6 * min(1.0, (y - 6) / 7.5)
        lat = 1 - 0.42 * (mirror_dist(x) / 11.5) ** 2
        crest = 1.6 * math.exp(-(mirror_dist(x) / 1.6) ** 2) * max(0.0, min(1.0, (9.5 - y) / 3.5))
        mx = 23 - x if x > AXE else x  # left half coordinates
        brow = 0.9 * math.exp(-(seg_dist(mx, y, (8.8, 2.6), (2.6, 1.8)) / 1.1) ** 2)
        cheek = 1.8 * math.exp(-(seg_dist(mx, y, (3.8, 8.5), (5.6, 13.0)) / 1.5) ** 2)
        top = crown * lat + crest + brow + cheek
        d = min(self.dist(x, y), R_FALL) / R_FALL
        return EDGE + (top - EDGE) * math.sqrt(1 - (1 - d) ** 2)

    def z(self, kind, x, y):
        if kind == "skull":
            return self.skull(x, y)
        if kind == "socket":
            return self.skull(x, y) - SOCKET
        if kind in ("floor", "prong"):  # the prongs are painted on the mouth floor
            return floor_z(x)
        jy = y - self.off
        if kind == "arm":
            ax = x if x < AXE else 23 - x
            t = max(0.0, min(1.0, (jy - 14.0) / 4.0))  # 0 at the arm's top, 1 at the chin
            mid, h = 6.2 + 0.8 * t, 4.0 - 1.6 * t
            top = 0.8 + h * math.sqrt(max(0.0, 1 - ((ax - mid) / 2.0) ** 2))
            d = min(self.dist(x, y), 2.0) / 2.0  # rounded off to the outline like the dome
            return EDGE + (top - EDGE) * math.sqrt(1 - (1 - d) ** 2)
        if kind == "chin":
            q = 1 - ((x - AXE) / 5.0) ** 2 - ((jy - 20.8) / 2.8) ** 2
            top = 0.4 + 5.0 * math.sqrt(max(0.0, q))
            d = min(self.dist(x, y), 1.5) / 1.5  # rounded off to the outline like the dome
            return EDGE + (top - EDGE) * math.sqrt(1 - (1 - d) ** 2)
        raise ValueError(kind)


def split(shape, corners, zs):
    """A pixel's top as two triangles (indices into its CCW corners). A step of the outline's
    staircase (a pixel with one convex outline corner) is split between its other two corners, so
    no ridge runs out to the corner and the rim reads as one smooth edge, not a row of teeth.
    Elsewhere the higher diagonal is used, which keeps the dome convex (no creases)."""
    convex = [i for i, (x, y) in enumerate(corners)
              if sum(shape.filled(c2, r2) for c2, r2 in Shape.around(x, y)) == 1]
    if len(convex) == 1:
        i = convex[0]
    else:
        i = 0 if zs[0] + zs[2] < zs[1] + zs[3] else 1  # split along the diagonal i+1 .. i+3
    return [(i, (i + 1) % 4, (i + 3) % 4), ((i + 1) % 4, (i + 2) % 4, (i + 3) % 4)]


def height_field(bm, shape, slot):
    """Top faces over every pixel (smooth), walls where heights step and at the outline (flat), and
    a flat underside. Winding is built outward; the faces of all three share vertices."""
    verts = {}

    def V(x, y, z):
        key = (round(x, 4), round(y, 4), round(z, 4))
        if key not in verts:
            verts[key] = bm.verts.new((G.ex(x), G.ey(y), z * U))
        return verts[key]

    tops = {}
    for r in range(shape.h):
        for c in range(shape.w):
            if shape.pix[r][c] < 0:
                continue
            k = shape.kind(c, r)
            corners = [(c, r + 1), (c + 1, r + 1), (c + 1, r), (c, r)]  # CCW seen from above
            zs = [shape.corner((c, r), x, y) for x, y in corners]
            tops[(c, r)] = dict(zip(corners, zs))
            vs = [V(x, y, z) for (x, y), z in zip(corners, zs)]
            for tri in split(shape, corners, zs):
                f = bm.faces.new([vs[i] for i in tri])
                f.material_index = slot(shape.paint(c, r), matte=k == "floor")
                f.smooth = k != "floor"  # the floor is faceted so no face looks straight up
    bottoms = []
    for (c, r), zc in tops.items():
        corners = [(c, r + 1), (c + 1, r + 1), (c + 1, r), (c, r)]
        nbrs = [(c, r + 1), (c + 1, r), (c, r - 1), (c - 1, r)]  # across each edge a -> b
        for i, n in enumerate(nbrs):
            a, b = corners[i], corners[(i + 1) % 4]
            a0, a1 = zc[a], zc[b]
            if n in tops:
                b0, b1 = tops[n][a], tops[n][b]
                mat = slot(shape.paint(*n))
            elif n[1] < 0:
                b0 = b1 = BASE  # the top row: closed by a wall too
                mat = slot(shape.paint(c, r))
            else:
                b0 = b1 = BASE
                mat = slot(shape.paint(c, r))
            da, db = a0 - b0, a1 - b1
            if da <= 1e-4 and db <= 1e-4:
                continue  # level, or the neighbour is the higher side and builds the wall
            if da < -1e-4 or db < -1e-4:
                # The heights cross along the edge: this side builds only its higher part.
                t = da / (da - db)
                p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                pz = a0 + (a1 - a0) * t
                if da > 0:
                    rings = [[V(a[0], a[1], b0), V(p[0], p[1], pz), V(a[0], a[1], a0)]]
                else:
                    rings = [[V(p[0], p[1], pz), V(b[0], b[1], b1), V(b[0], b[1], a1)]]
            else:
                rings = [[V(a[0], a[1], b0), V(b[0], b[1], b1), V(b[0], b[1], a1), V(a[0], a[1], a0)]]
            for ring in rings:
                ring = [v for i2, v in enumerate(ring) if v not in ring[:i2]]
                if len(ring) < 3:
                    continue
                f = bm.faces.new(ring)
                f.material_index = mat
                f.smooth = False
        f = bm.faces.new([V(x, y, BASE) for x, y in reversed(corners)])
        f.material_index = slot(48)
        f.smooth = False
        bottoms.append(f)
    return bottoms


def to_object(name, bm, mats, coll, fix_faces):
    """lib.to_object, but only the helper parts' normals are recalculated (the height field is
    wound outward as built)."""
    bmesh.ops.recalc_face_normals(bm, faces=[f for f in fix_faces if f.is_valid])
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def build(sprite, name, frame, off):
    coll = common.reset_collection(name)
    pix = next(f for f in sprite["frames"] if f["index"] == frame)["pixels"]
    m = lib.Mats(name, sprite["colors"])
    slots = {}

    def slot(idx, matte=False):
        q = quant(idx)
        if matte:  # the mouth's floor: dead matte so it stays a dark void under any light
            if ("matte", q) not in slots:
                slots[("matte", q)] = m(q, metallic=0.0, roughness=1.0)
            return slots[("matte", q)]
        if q not in slots:
            if q >= 112:  # the eyes: matte, faintly glowing
                slots[q] = m(q, metallic=0.0, roughness=0.95, emission_strength=1.2 if q >= 116 else 0.0)
            elif q == 48:
                slots[q] = m(q, metallic=0.1, roughness=0.85)
            else:
                slots[q] = m(q, metallic=METAL, roughness=ROUGH)  # polished blue steel
        return slots[q]

    # The eyes are the sockets' own red pixels, flat and matte at the socket floor (the sprite's
    # slanted slits); they glow a little so they read in the dark sockets. The lower teeth are the
    # mouth floor's own lighter pixels, painted on the matte floor.
    shape = Shape(pix, off)
    bm = bmesh.new()
    bottoms = height_field(bm, shape, slot)
    field = set(bm.faces)

    # Helpers find their faces by index, so the underside is merged into one face only now.
    fix = [f for f in bm.faces if f not in field]
    bmesh.ops.dissolve_faces(bm, faces=bottoms)
    return to_object(name, bm, m.list, coll, fix)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objs = {}
    for name, frame, off in MODELS:
        obj = build(sprite, name, frame, off)
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", lib.subset(sprite["sprites"], [frame]))
        objs[name] = (obj, frame)
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        for name, (obj, frame) in objs.items():
            path = out if name == NAME else out.with_name(f"{out.stem}{name[len(NAME):]}.png")
            ref = ROOT / "reference" / "models" / NAME / f"frame-newsh0-{frame}.png"
            common.render_preview([obj], str(path), ref, size=2)


if __name__ == "__main__":
    main()
