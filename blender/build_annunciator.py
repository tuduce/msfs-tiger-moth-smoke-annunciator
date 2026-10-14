"""Headless Blender build of the Tiger Moth smoke annunciator (MSFS 2020 glTF).

Run:
  blender.exe -b --python blender/build_annunciator.py -- --out build/annunciator [--preview build/preview]

World frame = Blender frame of the Ants Tiger Moth interior (nose = -Y, glTF z = -Blender y).
The box is mounted on the rear dash face (z_gltf -0.797) below the RPM gauge, over the lower half of the warning placard; the pilot sits behind it (larger y) looking at -Y,
so the pilot's LEFT is +X.  Box local frame: lx = +X (pilot left), ly = +Y (towards pilot), lz = up.
All dimensions below are millimetres until multiplied by MM.
"""
import argparse
import math
import os
import sys

import addon_utils
import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import textures  # noqa: E402

MM = 0.001
BOX = (60.0, 15.0, 30.0)                 # lx (width), ly (depth), lz (height)
FACE_Y = 0.797                           # rear dash face, Blender y (see --face-y)
SINK = 0.6                               # mm the box rear sinks into the panel (no gap)
SWITCH_ANGLE = 24.0                      # degrees either side of centre
ANIM_FRAMES = 20                         # ANIM_LENGTH used in the behaviour XML
LAMP_X = (11.0, 24.0, 37.0)              # pilot-left based x (mm) of red / white / blue
LAMP_Z = 17.0                            # mm from bottom of face
SWITCH_X = 50.0

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True, help="output dir for annunciator.gltf/.bin")
ap.add_argument("--tex", default=None, help="dir for the generated PNG textures (default: <out>/texture)")
ap.add_argument("--cx", type=float, default=0.230, help="box centre x (glTF/Blender x)")
ap.add_argument("--cz", type=float, default=0.2205, help="box centre height (glTF y / Blender z)")
ap.add_argument("--face-y", type=float, default=0.797, help="Blender y of the surface the box rear sits against")
ap.add_argument("--rot", type=float, default=-60.0, help="tilt of the box long axis from horizontal (deg), seen from the pilot, + = up towards pilot-left")
ap.add_argument("--preview", default=None, help="dir to write preview renders into")
ap.add_argument("--blend", default=None, help="save the .blend here")
ap.add_argument("--no-export", action="store_true")
args = ap.parse_args(argv)

out_dir = os.path.abspath(args.out)
tex_dir = os.path.abspath(args.tex or os.path.join(out_dir, "texture"))
os.makedirs(out_dir, exist_ok=True)
os.makedirs(tex_dir, exist_ok=True)

FACE_Y = args.face_y
ORIGIN = Vector((args.cx, FACE_Y + (BOX[1] - SINK) * 0.5 * MM, args.cz))
FRONT_Y = BOX[1] * 0.5                   # local front face (mm)


# ------------------------------------------------------------------ scene setup
addon_utils.enable("io_scene_gltf2_msfs_2020", default_set=False, persistent=False)
bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable("io_scene_gltf2_msfs_2020", default_set=False, persistent=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
scene.render.fps = 60

print("texture stats:", textures.generate(tex_dir))


# ------------------------------------------------------------------ mesh helpers
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def region_uv(region, fu, fv, inset=1.6 / textures.SIZE):
    u0, v0, u1, v1 = textures.ATLAS[region][:4]
    fu = clamp(fu, 0.0, 1.0)
    fv = clamp(fv, 0.0, 1.0)
    return (u0 + inset + fu * (u1 - u0 - 2 * inset), v0 + inset + fv * (v1 - v0 - 2 * inset))


class Builder:
    """Accumulates faces (with per-loop UVs) into one bmesh."""

    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")

    def add_face(self, coords, uv_fn):
        vs = [self.bm.verts.new(c) for c in coords]
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return
        for loop, c in zip(f.loops, coords):
            loop[self.uv].uv = uv_fn(c)

    def finish(self, name, material, smooth=True, angle=40.0, location=(0, 0, 0)):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        mesh.materials.append(material)
        if smooth:
            for p in mesh.polygons:
                p.use_smooth = True
            mesh.use_auto_smooth = True
            mesh.auto_smooth_angle = math.radians(angle)
        obj = bpy.data.objects.new(name, mesh)
        scene.collection.objects.link(obj)
        obj.location = location
        return obj


def lathe(builder, profile, segs, center, uv_fn):
    """Revolve a closed (r, h) polygon (mm) around local +Y.  center = local (x, y, z) mm."""
    cx, cy, cz = center
    n = len(profile)
    for i in range(segs):
        a0 = 2 * math.pi * i / segs
        a1 = 2 * math.pi * (i + 1) / segs
        for k in range(n):
            (r0, h0), (r1, h1) = profile[k], profile[(k + 1) % n]
            if r0 == 0 and r1 == 0:
                continue

            def P(r, h, a):
                return Vector(((cx + r * math.cos(a)) * MM, (cy + h) * MM, (cz + r * math.sin(a)) * MM))

            if r0 == 0:
                tri = [P(0, h0, a0), P(r1, h1, a0), P(r1, h1, a1)]
                builder.add_face(tri, uv_fn)
            elif r1 == 0:
                tri = [P(r0, h0, a0), P(0, h1, a0), P(r0, h0, a1)]
                builder.add_face(tri, uv_fn)
            else:
                quad = [P(r0, h0, a0), P(r1, h1, a0), P(r1, h1, a1), P(r0, h0, a1)]
                builder.add_face(quad, uv_fn)


def swatch_uv(region, scale_mm=12.0):
    def fn(c):
        fu = (c[0] / MM + scale_mm) / (2 * scale_mm)
        fv = (c[2] / MM + scale_mm) / (2 * scale_mm)
        return region_uv(region, 0.1 + 0.8 * clamp(fu, 0, 1), 0.1 + 0.8 * clamp(fv, 0, 1))
    return fn


def local(x_p, z_f):
    """Face coordinates (pilot-left x in mm, height from bottom in mm) -> local (lx, lz) mm."""
    return (BOX[0] * 0.5 - x_p, z_f - BOX[2] * 0.5)


# ------------------------------------------------------------------ materials
def tex_image(name, colour):
    img = bpy.data.images.load(os.path.join(tex_dir, name))
    img.name = name
    img.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    return img


def make_standard(name, albd=None, comp=None, norm=None, base=(1, 1, 1, 1), emis=None, metal=None, rough=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.msfs_material_type = "msfs_standard"
    if albd:
        m.msfs_base_color_texture = albd
    if comp:
        m.msfs_occlusion_metallic_roughness_texture = comp
    if norm:
        m.msfs_normal_texture = norm
    m.msfs_base_color_factor = base
    if emis is not None:
        m.msfs_emissive_factor = emis
        m.msfs_emissive_scale = 1.0
    if metal is not None:
        m.msfs_metallic_factor = metal
    if rough is not None:
        m.msfs_roughness_factor = rough
    return m


img_albd = tex_image("ANNUNCIATOR_ALBD.PNG", True)
img_comp = tex_image("ANNUNCIATOR_COMP.PNG", False)
img_norm = tex_image("ANNUNCIATOR_NORM.PNG", False)

mat_body = make_standard("annunciator_body", img_albd, img_comp, img_norm)
LAMPS = (
    ("red",   (0.11, 0.002, 0.002, 1.0), (1.0, 0.02, 0.0)),
    ("white", (0.13, 0.12, 0.10, 1.0), (1.0, 0.90, 0.70)),
    ("blue",  (0.004, 0.011, 0.11, 1.0), (0.04, 0.16, 1.0)),
)
mat_lamp = {n: make_standard(f"annunciator_lamp_{n}", base=base, emis=emis, metal=0.0, rough=0.40)
            for n, base, emis in LAMPS}
mat_mouse = bpy.data.materials.new("mousezone")
mat_mouse.use_nodes = True
mat_mouse.msfs_material_type = "msfs_standard"
mat_mouse.msfs_alpha_mode = "BLEND"
mat_mouse.msfs_base_color_factor = (1, 1, 1, 0)


# ------------------------------------------------------------------ body (box + hardware, one mesh)
body = Builder()

# rounded box -----------------------------------------------------------
bm_box = bmesh.new()
bmesh.ops.create_cube(bm_box, size=1.0)
for v in bm_box.verts:
    v.co = Vector((v.co.x * BOX[0] * MM, v.co.y * BOX[1] * MM, v.co.z * BOX[2] * MM))
bmesh.ops.bevel(bm_box, geom=list(bm_box.edges), offset=1.8 * MM, offset_type="OFFSET",
                segments=2, profile=0.5, affect="EDGES")


def box_uv(face, co):
    n = face.normal
    ax = max(range(3), key=lambda i: abs(n[i]))
    sgn = 1 if n[ax] >= 0 else -1
    lx, ly, lz = co[0] / MM, co[1] / MM, co[2] / MM
    fx = (BOX[0] * 0.5 - lx) / BOX[0]            # 0 at pilot's left, 1 at pilot's right
    fy = (ly + BOX[1] * 0.5) / BOX[1]
    fz = (lz + BOX[2] * 0.5) / BOX[2]
    if ax == 1:
        return region_uv("FRONT" if sgn > 0 else "BACK", fx, fz)
    if ax == 2:
        return region_uv("TOP" if sgn > 0 else "BOTTOM", fx, fy)
    return region_uv("LEFT" if sgn > 0 else "RIGHT", fy, fz)


for f in bm_box.faces:
    coords = [v.co.copy() for v in f.verts]
    vs = [body.bm.verts.new(c) for c in coords]
    nf = body.bm.faces.new(vs)
    for loop, c in zip(nf.loops, coords):
        loop[body.uv].uv = box_uv(f, c)
bm_box.free()

# lamp bezels (brass) ---------------------------------------------------
BEZEL = [(6.3, 0.0), (6.3, 1.5), (5.7, 2.2), (4.6, 2.2), (4.6, 0.9), (4.6, 0.0)]
for x_p in LAMP_X:
    lx, lz = local(x_p, LAMP_Z)
    lathe(body, BEZEL, 32, (lx, FRONT_Y, lz), swatch_uv("BRASS"))

# screws (chrome), four corners ----------------------------------------
SCREW = [(0, 0.0), (1.5, 0.0), (1.5, 0.45), (1.2, 0.8), (0, 0.8)]
for x_p, z_f in ((3.6, 26.4), (56.4, 26.4), (3.6, 3.6), (56.4, 3.6)):
    lx, lz = local(x_p, z_f)
    lathe(body, SCREW, 14, (lx, FRONT_Y, lz), swatch_uv("CHROME", 4.0))
    # slot
    for sgn in (1, -1):
        pass

# toggle switch hardware: hex nut (chrome) + collar (steel) ---------------
sx, sz = local(SWITCH_X, LAMP_Z)
lathe(body, [(0, 1.5), (3.9, 1.5), (3.9, 0.0), (0, 0.0)], 6, (sx, FRONT_Y, sz), swatch_uv("CHROME"))
lathe(body, [(0, 4.2), (2.0, 4.2), (2.4, 3.2), (2.4, 1.5), (0, 1.5)], 24, (sx, FRONT_Y, sz), swatch_uv("STEEL"))

obj_body = body.finish("annunciator_body", mat_body, smooth=True, angle=38.0, location=(0, 0, 0))

# ------------------------------------------------------------------ lenses (one node + material each)
LENS = [(0, 0.5), (4.5, 0.5), (4.5, 1.1), (4.1, 2.0), (3.1, 3.0), (1.6, 3.6), (0, 3.8)]
lens_objs = {}
for (name, _, _), x_p in zip(LAMPS, LAMP_X):
    lx, lz = local(x_p, LAMP_Z)
    b = Builder()
    lathe(b, LENS, 32, (0, 0, 0), lambda c: (0.5, 0.5))
    loc = Vector((lx * MM, FRONT_Y * MM, lz * MM))
    lens_objs[name] = b.finish(f"annunciator_lamp_{name}", mat_lamp[name], smooth=True, angle=60.0, location=loc)

# ------------------------------------------------------------------ switch lever (animated node, origin = pivot)
lever = Builder()
PIVOT_H = 4.2
LEVER = [(0, -2.1), (1.2, -1.7), (1.9, -0.7), (1.8, 0.4), (1.45, 1.0), (1.25, 3.0), (0.95, 9.5),
         (0.95, 11.2), (1.7, 12.4), (1.9, 13.8), (1.4, 15.0), (0, 15.5)]


def lever_uv(c):
    h = c[1] / MM
    return swatch_uv("RUBBER" if h > 11.0 else "CHROME", 3.0)(c)


lathe(lever, LEVER, 24, (0, 0, 0), lever_uv)
lever_loc = Vector((sx * MM, (FRONT_Y + PIVOT_H) * MM, sz * MM))
obj_lever = lever.finish("annunciator_switch", mat_body, smooth=True, angle=60.0, location=lever_loc)

# animation: frame 0 = SHORT (down), frame ANIM_FRAMES = LONG (up) --------
obj_lever.rotation_mode = "XYZ"
act_name = "annunciator_switch"
for frame, deg in ((0, -SWITCH_ANGLE), (ANIM_FRAMES, SWITCH_ANGLE)):
    obj_lever.rotation_euler = (math.radians(deg), 0.0, 0.0)
    obj_lever.keyframe_insert("rotation_euler", frame=frame)
obj_lever.animation_data.action.name = act_name
for fc in obj_lever.animation_data.action.fcurves:
    for kp in fc.keyframe_points:
        kp.interpolation = "LINEAR"
scene.frame_start, scene.frame_end = 0, ANIM_FRAMES
scene.frame_set(0)
obj_lever.rotation_euler = (math.radians(-SWITCH_ANGLE), 0.0, 0.0)

# ------------------------------------------------------------------ mousezone
mz = bmesh.new()
bmesh.ops.create_cube(mz, size=1.0)
for v in mz.verts:
    v.co = Vector((v.co.x * 14.0 * MM, v.co.y * 20.0 * MM, v.co.z * 20.0 * MM))
mz_mesh = bpy.data.meshes.new("mousezone_annunciator_switch")
mz.to_mesh(mz_mesh)
mz.free()
mz_mesh.materials.append(mat_mouse)
obj_mz = bpy.data.objects.new("mousezone_annunciator_switch", mz_mesh)
scene.collection.objects.link(obj_mz)
obj_mz.location = Vector((sx * MM, (FRONT_Y + 7.0) * MM, sz * MM))
uv = mz_mesh.uv_layers.new(name="UVMap")

# ------------------------------------------------------------------ root node (placement + tilt)
# Everything hangs off one empty at ORIGIN.  Rotation about Blender Y (the depth axis) by -rot maps the box's long axis (+lx,
# pilot-left) to the direction (cos rot, sin rot) in the (x, up) plane, i.e. tilted up towards the pilot's left.
root = bpy.data.objects.new("annunciator_root", None)
scene.collection.objects.link(root)
root.location = ORIGIN
root.rotation_mode = "XYZ"
root.rotation_euler = (0.0, math.radians(-args.rot), 0.0)
for o in (obj_body, obj_lever, obj_mz, *lens_objs.values()):
    o.parent = root

# ------------------------------------------------------------------ report
for o in (obj_body, obj_lever, obj_mz, *lens_objs.values()):
    print("NODE", o.name, tuple(round(c, 4) for c in o.matrix_world.translation), len(o.data.polygons), "polys")

# ------------------------------------------------------------------ export
if not args.no_export:
    bpy.ops.object.select_all(action="DESELECT")
    scene.frame_set(0)
    gltf_path = os.path.join(out_dir, "annunciator.gltf")
    props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    kw = dict(filepath=gltf_path, export_format="GLTF_SEPARATE", export_yup=True, export_apply=True,
              export_texcoords=True, export_normals=True, export_materials="EXPORT", export_animations=True,
              export_extras=False, use_selection=False)
    for opt, val in (("export_tangents", False), ("export_cameras", False), ("export_lights", False),
                     ("export_frame_range", False), ("export_force_sampling", True),
                     ("export_nla_strips", False), ("export_image_format", "AUTO"),
                     ("export_texture_dir", "texture")):
        if opt in props:
            kw[opt] = val
    print("EXPORT opts:", sorted(k for k in props if "msfs" in k.lower()))
    bpy.ops.export_scene.gltf(**kw)
    print("EXPORTED", gltf_path)

# ------------------------------------------------------------------ previews
def render_previews(pdir):
    os.makedirs(pdir, exist_ok=True)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 48
    scene.cycles.use_denoising = False
    scene.render.resolution_x, scene.render.resolution_y = 1200, 700
    scene.render.image_settings.file_format = "PNG"
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.36, 0.38, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    scene.world = world
    scene.view_settings.view_transform = "Standard"

    def principled(name, base=None, img_albd=None, img_comp=None, img_norm=None, emit=None, rough=0.5, metal=0.0):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        if img_albd:
            t = nt.nodes.new("ShaderNodeTexImage"); t.image = img_albd
            nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
        if img_comp:
            t = nt.nodes.new("ShaderNodeTexImage"); t.image = img_comp
            sep = nt.nodes.new("ShaderNodeSeparateColor")
            nt.links.new(t.outputs["Color"], sep.inputs["Color"])
            nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
            nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
        if img_norm:
            t = nt.nodes.new("ShaderNodeTexImage"); t.image = img_norm
            sp = nt.nodes.new("ShaderNodeSeparateColor"); cb = nt.nodes.new("ShaderNodeCombineColor")
            inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
            nt.links.new(t.outputs["Color"], sp.inputs["Color"])
            nt.links.new(sp.outputs["Red"], cb.inputs["Red"])
            nt.links.new(sp.outputs["Green"], inv.inputs[1])       # DirectX -> OpenGL green flip
            nt.links.new(inv.outputs[0], cb.inputs["Green"])
            nt.links.new(sp.outputs["Blue"], cb.inputs["Blue"])
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nt.links.new(cb.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
        if base:
            bsdf.inputs["Base Color"].default_value = base
        if emit:
            bsdf.inputs["Emission"].default_value = (*emit, 1.0)
            bsdf.inputs["Emission Strength"].default_value = 6.0
        if not img_comp:
            bsdf.inputs["Roughness"].default_value = rough
            bsdf.inputs["Metallic"].default_value = metal
        return m

    body_prev = principled("pv_body", img_albd=img_albd, img_comp=img_comp, img_norm=img_norm)
    obj_body.data.materials[0] = body_prev
    obj_lever.data.materials[0] = body_prev
    lamp_prev = {n: principled("pv_" + n, base=b, rough=0.12) for n, b, e in LAMPS}
    lamp_lit = {n: principled("pvl_" + n, base=b, emit=e, rough=0.12) for n, b, e in LAMPS}
    obj_mz.hide_render = True

    def set_lamps(lit):
        for n, o in lens_objs.items():
            o.data.materials[0] = (lamp_lit if lit.get(n) else lamp_prev)[n]

    set_lamps({})

    # mock rear panel so the box is seen in context
    bpy.ops.mesh.primitive_plane_add(size=0.6, location=(ORIGIN.x, FACE_Y, ORIGIN.z), rotation=(math.pi / 2, 0, 0))
    panel = bpy.context.object
    pm = bpy.data.materials.new("panel")
    pm.use_nodes = True
    pm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.06, 0.06, 0.065, 1)
    pm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
    panel.data.materials.append(pm)

    def add_light(loc, energy, size):
        ld = bpy.data.lights.new("l", "AREA")
        ld.energy, ld.size = energy, size
        lo = bpy.data.objects.new("l", ld)
        scene.collection.objects.link(lo)
        lo.location = loc
        direction = (ORIGIN - Vector(loc))
        lo.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    add_light((ORIGIN.x + 0.25, ORIGIN.y + 0.35, ORIGIN.z + 0.25), 25, 0.25)
    add_light((ORIGIN.x - 0.3, ORIGIN.y + 0.3, ORIGIN.z + 0.05), 10, 0.3)

    def shot(name, loc, target, lens=60):
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        co = bpy.data.objects.new(name, cd)
        scene.collection.objects.link(co)
        co.location = loc
        co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.camera = co
        scene.render.filepath = os.path.join(pdir, name + ".png")
        bpy.ops.render.render(write_still=True)

    c = ORIGIN + Vector((0, 0.0, 0))
    shot("front", (c.x, c.y + 0.22, c.z), (c.x, c.y, c.z), 70)
    set_lamps({"red": 1, "white": 1, "blue": 1})
    shot("front_lit", (c.x, c.y + 0.22, c.z), (c.x, c.y, c.z), 70)
    set_lamps({})
    shot("angle_left", (c.x + 0.10, c.y + 0.16, c.z + 0.07), (c.x, c.y + 0.01, c.z), 70)
    # lit state: switch lamps emissive via the principled/msfs node would need runtime; show lever up
    scene.frame_set(ANIM_FRAMES)                       # lever up = LONG
    shot("angle_right_long", (c.x - 0.10, c.y + 0.16, c.z + 0.05), (c.x, c.y + 0.01, c.z), 70)
    scene.frame_set(0)


if args.preview:
    render_previews(os.path.abspath(args.preview))

if args.blend:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.blend))

