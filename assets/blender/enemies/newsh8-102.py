"""Red boulder (newsh8.shp frame 102): a 3D version of its sprite.

Seen in episode 3 (levels 3.4 and 3.9): the red rockets (assembly-newsh8-125 lying, -191 standing)
drop it behind them every 10 / 30 ticks, and it stays where it falls (a still ground object, armour
20, no guns). A small (12x14 px) egg-shaped red stone lit from the top left, with a lighter rim of
reflected light round its lower right. One frame, one model: a slightly egg-shaped dome sitting on
the ground, its waist on the sprite's inner mask, given the sprite's shades by the facet ramp (D175,
D178: lib_newshd_rock.facet_ramp): each small triangle one shade of the sprite's red ramp, ranked
mostly by how squarely it faces the art's light and matched to the sprite's own shade distribution,
so it has the sprite's range from the near-white highlight at the upper left to the dark limb (one
glossy mid-red read flat: spread 77 against the sprite's 179). Smooth normals (the sprite draws no
breaks), a soft sheen; D90's outline shell.

Run: blender --background --python assets/blender/enemies/newsh8-102.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b082  # noqa: E402
import lib_newshd_rock as R  # noqa: E402

NAME = "newsh8-102"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

# The facet ramp (lib_newshd_rock.facet_ramp, D175, D178): the red ramp's shades on the stone. The
# sprite draws a smooth stone (no breaks; one highlight at the upper left, the dark limb lower right),
# so its "facets" are the icosphere's single triangles (`angle`, `size`) ranked mostly by how squarely
# they face the art's light (`sprite` 0.25: ranked by the sprite's pixels the shades came out as a
# mottle), on smooth normals (`flat` False). Flat 1.5-2 px chips read as a cut gem in game.
SPEC = {"mid": 72, "metallic": 0.0, "roughness": 0.45,
        "ramp": {"angle": 4.0, "size": 0.6, "sprite": 0.25, "flat": False}}


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = [common.palette_material(sprite, SPEC["mid"], NAME, metallic=SPEC["metallic"],
                                    roughness=SPEC["roughness"])]  # 0 red body
    bm = bmesh.new()
    # An egg-shaped dome on the ground whose waist follows the sprite's inner mask (inside its ink
    # ring, D74; traced by rays from its centroid, lib_newshd_rock.Grid.outline): an icosphere (no
    # pole fan, so the shades' edges come out irregular).
    g = R.Grid(sprite, NAME)
    cu, cv, radii = g.outline(steps=72, smooth=2)
    cz, rz = 0.06, 0.4
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    for v in bm.verts:
        d = v.co.copy()
        a = math.atan2(d.y, d.x)
        r = math.hypot(d.x, d.y) * R.radius_at(radii, a)
        v.co = Vector((g.x(cu + r * math.cos(a)), g.y(cv - r * math.sin(a)), max(cz + d.z * rz, 0.0)))
    for f in bm.faces:
        f.material_index = 0
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    obj = lib_b082.to_object(NAME, bm, mats, coll)
    obj.data.shade_smooth()
    R.facet_ramp(sprite, g, obj, SPEC)
    return [obj, R.d90_shell(obj, coll, NAME)]


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objs = build(sprite)
    common.export_sprite_model(ROOT, objs, MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview(objs[:1], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
