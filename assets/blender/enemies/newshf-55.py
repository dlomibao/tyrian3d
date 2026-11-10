"""Horned green insect fighter (newshf.shp frame 55), flying down the screen.

Built by newshf-85.py (the SAVARA fighter squadron, batch b023): newshf-47's level frame recoloured (+16, eyes 132); model newshf-55.
Run: blender --background --python assets/blender/enemies/newshf-55.py [-- --no-bake]
"""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("newshf_85_squadron", Path(__file__).resolve().parent / "newshf-85.py")
squadron = importlib.util.module_from_spec(spec)
spec.loader.exec_module(squadron)

if __name__ == "__main__":
    squadron.run({"55"})
