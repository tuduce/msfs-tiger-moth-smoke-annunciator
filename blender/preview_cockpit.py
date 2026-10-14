"""Render the merged interior LOD from the rear pilot's eye point (geometry only, Workbench).
blender -b --python blender/preview_cockpit.py -- <merged_lod.gltf> <out.png> [cam_x cam_y cam_z lens]
Reads POSITION + indices straight from the glTF (the stock importer chokes on some Ants meshes).
"""
import json, math, os, sys
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
gltf_path, out = argv[0], argv[1]
cam = [float(v) for v in argv[2:5]] if len(argv) >= 5 else [0.0, 0.408, -1.158]   # glTF coords
lens = float(argv[5]) if len(argv) >= 6 else 18.0

def load_gltf(path):
    global g, binf
    g = json.load(open(path))
    binf = open(os.path.join(os.path.dirname(path), os.path.basename(g["buffers"][0]["uri"])), "rb").read()


g = binf = None
CT = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read(ai):
    ac = g["accessors"][ai]
    bv = g["bufferViews"][ac["bufferView"]]
    dt = np.dtype(CT[ac["componentType"]])
    n = NC[ac["type"]]
    off = bv.get("byteOffset", 0) + ac.get("byteOffset", 0)
    stride = bv.get("byteStride", dt.itemsize * n)
    if stride == dt.itemsize * n:
        return np.frombuffer(binf, dt, ac["count"] * n, off).reshape(ac["count"], n)
    raw = np.frombuffer(binf, np.uint8, stride * ac["count"], off).reshape(ac["count"], stride)
    return raw[:, :dt.itemsize * n].copy().view(dt).reshape(ac["count"], n)


def local_matrix(n):
    t = Vector(n.get("translation", (0, 0, 0)))
    r = n.get("rotation", (0, 0, 0, 1))
    s = n.get("scale", (1, 1, 1))
    q = Quaternion((r[3], r[0], r[1], r[2]))
    return Matrix.Translation(t) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((*s, 1.0))


# glTF (x,y,z) -> Blender (x,-z,y)
C = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
scene = bpy.context.scene
SKIP_MATS = ("collision", "env_occluder", "mousezone", "shadows", "possible_orphans", "atm_col_")


def visit(ni, parent_m):
    n = g["nodes"][ni]
    m = parent_m @ local_matrix(n)
    if "mesh" in n and not n.get("name", "").lower().startswith(("mousezone", "collision")):
        verts, faces = [], []
        for p in g["meshes"][n["mesh"]]["primitives"]:
            mat = g["materials"][p["material"]]["name"].lower() if "material" in p else ""
            if any(k in mat for k in SKIP_MATS) or "indices" not in p:
                continue
            pos = read(p["attributes"]["POSITION"]).astype(np.float64)
            idx = read(p["indices"]).reshape(-1, 3).astype(np.int64)
            base = len(verts)
            verts.extend(pos.tolist())
            faces.extend((idx + base).tolist())
        if faces:
            me = bpy.data.meshes.new(n.get("name", "n"))
            me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
            ob = bpy.data.objects.new(n.get("name", "n"), me)
            ob.matrix_world = C @ m
            scene.collection.objects.link(ob)
            for p in me.polygons:
                p.use_smooth = False
    for c in n.get("children", []):
        visit(c, m)


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
for path in gltf_path.split(";"):
    load_gltf(path)
    for r in g["scenes"][g.get("scene", 0)]["nodes"]:
        visit(r, Matrix.Identity(4))

scene.render.engine = "BLENDER_WORKBENCH"
sh = scene.display.shading
sh.light, sh.color_type, sh.show_cavity = "STUDIO", "OBJECT", True
scene.render.resolution_x, scene.render.resolution_y = 1500, 900
scene.view_settings.view_transform = "Standard"
for o in scene.objects:
    n = o.name.lower()
    if "annunciator_lamp_red" in n: o.color = (1, 0.1, 0.05, 1)
    elif "annunciator_lamp_white" in n: o.color = (1, 1, 0.9, 1)
    elif "annunciator_lamp_blue" in n: o.color = (0.1, 0.25, 1, 1)
    elif "annunciator" in n: o.color = (0.35, 0.45, 0.2, 1)
    elif "panel_rear" in n: o.color = (0.12, 0.12, 0.13, 1)
    elif n.startswith(("rollover", "windscreen", "fuselage", "wing")): o.color = (0.9, 0.75, 0.1, 1)
    else: o.color = (0.55, 0.55, 0.58, 1)

eye = Vector((cam[0], -cam[2], cam[1]))
cd = bpy.data.cameras.new("c"); cd.lens = lens; cd.clip_start = 0.02
co = bpy.data.objects.new("c", cd); scene.collection.objects.link(co)
co.location = eye
pitch = math.radians(-11)
direction = Vector((0, -math.cos(pitch), math.sin(pitch)))
co.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
scene.camera = co
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("RENDERED", out, "objects", len(scene.objects))
