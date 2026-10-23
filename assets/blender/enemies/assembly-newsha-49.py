"""The "WARNING / MISSILE SHIPS!!" sign (newsha.shp frames 49 and 51): a 3D version of its sprites.

Seen in episode 2 (level 2.10), where it flies in ahead of the missile ships. Two 2x2 pieces side
by side (sprite.json `assemblyLayout`; the layout's other entries are an unrelated grey ship
next to it) spell WARNING over MISSILE SHIPS!! in red-orange block letters, with an underline
under each word that fades from bright orange to dark red at its tail.

Built whole as raised letters in assembly coordinates, then cut into newsha-49 (left) and
newsha-51 (right) with common.split_assembly. Each letter stands as one solid with chamfered
top edges, its shaded left edges (palette 118) a lower step beside the bright face (120), and the underlines
thin out towards their dark tails (119, 118, 117, 116, 114). The letters glow a little: it is
a lit warning sign.

Run: blender --background --python assets/blender/enemies/assembly-newsha-49.py [-- --preview out.png]
(the preview is the whole sign; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b044 as lib  # noqa: E402
import common  # noqa: E402

NAME = "assembly-newsha-49"
ROOT = common.repo_root(__file__)
PIECES = ["newsha-49", "newsha-51"]
CX0, CY0 = 173, 39  # screen centre of the sign (between the pieces at cx 161 and 185)
W, H = 48, 28  # the sign's pixel grid: newsha-49 is columns 0-23, newsha-51 columns 24-47
PX = lib.PX

# Palette index -> (letter height in units,): bright faces stand tallest, the darker shades are
# lower steps (stroke edges, the underlines' fading tails).
HEIGHT = {120: (0.13,), 119: (0.115,), 118: (0.095,), 117: (0.08,), 116: (0.07,), 114: (0.055,)}
Z0 = -0.06  # the letters' flat back


def X(c):
    return (c - W / 2) / 12


def Y(r):
    return (H / 2 - r) / 12


def grid():
    """The sign's pixels as one W x H grid of palette indices (-1 transparent)."""
    g = [[-1] * W for _ in range(H)]
    for k, name in enumerate(PIECES):
        pixels = common.load_sprite(ROOT, name)["frames"][0]["pixels"]
        for r, line in enumerate(pixels):
            for c, v in enumerate(line):
                g[r][c + 24 * k] = v
    return g


def rectangles(g):
    """Cover the grid's pixels with as few same-index rectangles as a greedy sweep finds:
    (index, c0, r0, c1, r1) with c1 / r1 exclusive."""
    used = [[False] * W for _ in range(H)]
    out = []
    for r in range(H):
        for c in range(W):
            v = g[r][c]
            if v < 0 or used[r][c]:
                continue
            c1 = c
            while c1 < W and g[r][c1] == v and not used[r][c1]:
                c1 += 1
            r1 = r + 1
            while r1 < H and all(g[r1][k] == v and not used[r1][k] for k in range(c, c1)):
                r1 += 1
            for rr in range(r, r1):
                for k in range(c, c1):
                    used[rr][k] = True
            out.append((v, c, r, c1, r1))
    return out


def drop_strays(obj):
    """split_assembly keeps faces lying exactly on a cut plane, so a piece also keeps the walls
    of its neighbour's letters that stand on the shared tile edge. Remove faces on the piece's
    edge planes that don't join any face inside the piece (the cut's own caps do)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    eps = 1e-5

    def on_edge(f):
        return any(all(abs(v.co.x - b) < eps for v in f.verts) for b in (-1.0, 1.0)) or \
            any(all(abs(v.co.y - b) < eps for v in f.verts) for b in (-14 / 12, 14 / 12))

    flat = {f for f in bm.faces if on_edge(f)}
    stray = [f for f in flat if all(set(e.link_faces) <= flat for e in f.edges)]
    bmesh.ops.delete(bm, geom=stray, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def merged_sprite():
    data = common.load_sprite(ROOT, PIECES[0])
    for name in PIECES[1:]:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def build(sprite):
    """Raised letters: every lit pixel stands at its shade's height, side walls only where a
    neighbour is lower, then coplanar faces are merged and the top edges chamfered."""
    coll = common.reset_collection(NAME)
    tag = "nsha49"
    indices = sorted(HEIGHT, reverse=True)
    glow = {120: 2.0, 119: 1.8, 118: 1.4, 117: 1.2, 116: 1.0, 114: 0.8}
    mats = [common.palette_material(sprite, i, tag, metallic=0.2, roughness=0.4, emission_strength=glow[i])
            for i in indices]
    slot = {i: k for k, i in enumerate(indices)}
    g = grid()

    def top(r, c):
        if 0 <= r < H and 0 <= c < W and g[r][c] >= 0:
            return Z0 + HEIGHT[g[r][c]][0]
        return Z0

    bm = bmesh.new()

    def quad(pts, mat):
        bm.faces.new([bm.verts.new(p) for p in pts]).material_index = mat

    for r in range(H):
        for c in range(W):
            v = g[r][c]
            if v < 0:
                continue
            m, z = slot[v], top(r, c)
            x0, x1, y0, y1 = X(c), X(c + 1), Y(r + 1), Y(r)
            quad([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], m)
            quad([(x0, y1, Z0), (x1, y1, Z0), (x1, y0, Z0), (x0, y0, Z0)], m)
            for (dr, dc), (a, b) in (((0, -1), ((x0, y1), (x0, y0))), ((0, 1), ((x1, y0), (x1, y1))),
                                     ((-1, 0), ((x1, y1), (x0, y1))), ((1, 0), ((x0, y0), (x1, y0)))):
                zn = top(r + dr, c + dc)
                if zn < z - 1e-6:
                    quad([(*a, zn), (*b, zn), (*b, z), (*a, z)], m)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.dissolve_limit(bm, angle_limit=0.01, verts=bm.verts, edges=bm.edges, delimit={"MATERIAL"})
    # Chamfer the letters' top outer edges.
    edges = [e for e in bm.edges if len(e.link_faces) == 2 and
             sorted(abs(f.normal.z) > 0.9 for f in e.link_faces) == [False, True] and
             max(v.co.z for v in e.verts) > Z0 + 0.03]
    bmesh.ops.bevel(bm, geom=edges, offset=0.12 * PX, segments=1, affect="EDGES", profile=0.5,
                    clamp_overlap=True)
    for f in bm.faces:
        f.smooth = False
    return lib.to_object(NAME, bm, mats, coll)


def composite_png(out):
    """The whole sign's sprite as one image, padded to the 24:28 shape that render_preview
    expects for size 4 (48 x 56 px, the sign in the middle)."""
    import numpy as np
    sprite = merged_sprite()
    img = np.zeros((56, 48, 4), dtype=np.float32)
    for r, line in enumerate(grid()):
        for c, v in enumerate(line):
            if v >= 0:
                img[14 + r, c] = [*(ch / 255 for ch in sprite["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 48, 56, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for piece in pieces.values():
        drop_strays(piece)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
