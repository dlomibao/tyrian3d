"""newsh5-268: the 24x28 grey torpedo fuselage and nose that hangs under the centre of
assembly-newsh5-229 (episode 4, SAVARA IV and APPROACH). It is one third of one craft built by
assembly-newsh5-229.py (design A: one gunship, nose down the screen); this wrapper runs that builder
and exports only newsh5-268 (the 229 and 231 pieces are exported by assembly-newsh5-229.py).

Run: blender --background --python assets/blender/enemies/newsh5-268.py
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "assembly_newsh5_229", Path(__file__).resolve().parent / "assembly-newsh5-229.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

if __name__ == "__main__":
    _mod.main(export=("newsh5-268",))
