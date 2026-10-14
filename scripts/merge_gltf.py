"""Merge the exported annunciator glTF into copies of the Ants Tiger Moth interior LOD glTFs.

Pure stdlib.  Usage:
  python -I scripts/merge_gltf.py --base-dir <Ants model dir> --ann build/annunciator --out <package model dir> [--lods 00 01 02]

The Ants files are in MSFS' *optimized* format (extension ASOBO_asset_optimized): ONE shared interleaved vertex buffer view
('BufferViewVertexND', stride 36) and ONE shared index buffer view ('BufferViewIndex'):

    offset  0  POSITION    float32 x3
    offset 12  TANGENT     int8    x4   (xyz * 127, w = +-127)
    offset 16  NORMAL      int8    x4   (xyz * 127, w = 127)
    offset 20  TEXCOORD_0  float16 x2   (stored in 16-bit slots, componentType 5122)
    offset 24  TEXCOORD_1  float16 x2
    offset 28  COLOR_0     float16 x4   (componentType 5123)

Every primitive also needs `mode: 4` and extras.ASOBO_primitive {PrimitiveCount, VertexType 'VTX', VertexVersion 2}.
Triangle winding is reversed (left-handed MSFS convention).
The annunciator vertices are converted to exactly this layout and appended to those shared views (a mesh in a different
layout is misread by the sim: invisible geometry and a huge click zone).  Textures are rewritten to the Ants convention
(<NAME>.PNG.DDS via MSFT_texture_dds); the 'mousezone' material is mapped onto the base file's existing 'mousezone'.
The base files are only read.
"""
import argparse
import copy
import json
import math
import os
import struct

ANN_NAME_PREFIXES = ("annunciator_", "mousezone_annunciator_")
STRIDE = 36
CT_SIZE = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
CT_FMT = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_accessor(g, binb, ai):
    ac = g["accessors"][ai]
    bv = g["bufferViews"][ac["bufferView"]]
    n = NCOMP[ac["type"]]
    fmt = "<" + CT_FMT[ac["componentType"]] * n
    size = CT_SIZE[ac["componentType"]] * n
    stride = bv.get("byteStride", size)
    off = bv.get("byteOffset", 0) + ac.get("byteOffset", 0)
    out = []
    for i in range(ac["count"]):
        v = struct.unpack_from(fmt, binb, off + i * stride)
        out.append(v if n > 1 else v[0])
    return out


def norm3(v):
    ln = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    return (v[0] / ln, v[1] / ln, v[2] / ln) if ln > 1e-12 else (0.0, 0.0, 1.0)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def tangents(pos, nrm, uv, idx):
    n = len(pos)
    tan = [[0.0, 0.0, 0.0] for _ in range(n)]
    bit = [[0.0, 0.0, 0.0] for _ in range(n)]
    for t in range(0, len(idx), 3):
        a, b, c = idx[t], idx[t + 1], idx[t + 2]
        e1 = [pos[b][k] - pos[a][k] for k in range(3)]
        e2 = [pos[c][k] - pos[a][k] for k in range(3)]
        du1, dv1 = uv[b][0] - uv[a][0], uv[b][1] - uv[a][1]
        du2, dv2 = uv[c][0] - uv[a][0], uv[c][1] - uv[a][1]
        d = du1 * dv2 - du2 * dv1
        if abs(d) < 1e-20:
            continue
        r = 1.0 / d
        T = [(e1[k] * dv2 - e2[k] * dv1) * r for k in range(3)]
        B = [(e2[k] * du1 - e1[k] * du2) * r for k in range(3)]
        for vtx in (a, b, c):
            for k in range(3):
                tan[vtx][k] += T[k]
                bit[vtx][k] += B[k]
    out = []
    for i in range(n):
        nn = nrm[i]
        t = tan[i]
        d = dot(nn, t)
        t = [t[k] - nn[k] * d for k in range(3)]
        if t[0] == t[1] == t[2] == 0.0 or math.sqrt(dot(t, t)) < 1e-9:       # degenerate uv -> any perpendicular
            t = cross(nn, (0.0, 1.0, 0.0) if abs(nn[1]) < 0.9 else (1.0, 0.0, 0.0))
        t = norm3(t)
        w = 1.0 if dot(cross(nn, t), bit[i]) >= 0.0 else -1.0
        out.append((t[0], t[1], t[2], w))
    return out


def i8(x):
    return max(-127, min(127, int(round(x * 127.0))))


def pack_vertices(pos, nrm, tan, uv):
    buf = bytearray()
    for i in range(len(pos)):
        buf += struct.pack("<3f", *pos[i])
        buf += struct.pack("<4b", i8(tan[i][0]), i8(tan[i][1]), i8(tan[i][2]), 127 if tan[i][3] >= 0 else -127)
        buf += struct.pack("<4b", i8(nrm[i][0]), i8(nrm[i][1]), i8(nrm[i][2]), 127)
        u = struct.pack("<2e", max(-65504.0, min(65504.0, uv[i][0])), max(-65504.0, min(65504.0, uv[i][1])))
        buf += u + u                                      # TEXCOORD_0 and TEXCOORD_1 identical (as in the Ants files)
        buf += struct.pack("<4e", 1.0, 1.0, 1.0, 1.0)     # COLOR_0 white
    return bytes(buf)


def merge(base_gltf_path, base_bin_path, ann_gltf_path, ann_bin_path, out_gltf_path, out_bin_path, diag_clone=False):
    g = load(base_gltf_path)
    a = load(ann_gltf_path)
    with open(base_bin_path, "rb") as f:
        base_bin = f.read()
    with open(ann_bin_path, "rb") as f:
        ann_bin = f.read()

    if any(n.get("name", "").startswith(ANN_NAME_PREFIXES) for n in g["nodes"]):
        raise SystemExit(f"{base_gltf_path} already contains annunciator nodes - merge from the pristine base")
    assert len(g["buffers"]) == 1 and len(a["buffers"]) == 1, "expected single buffer files"
    ext = g.get("asset", {}).get("extensions", {})
    assert "ASOBO_asset_optimized" in ext, "base file is not in the optimized layout this script targets"

    vi = [i for i, b in enumerate(g["bufferViews"]) if b.get("name") == "BufferViewVertexND"]
    ii = [i for i, b in enumerate(g["bufferViews"]) if b.get("name") == "BufferViewIndex"]
    assert len(vi) == 1 and len(ii) == 1, "expected exactly one shared vertex and one shared index buffer view"
    vi, ii = vi[0], ii[0]
    vbv, ibv = g["bufferViews"][vi], g["bufferViews"][ii]
    assert vbv["byteStride"] == STRIDE and vbv["byteLength"] % STRIDE == 0

    off_acc = len(g["accessors"])
    off_mesh = len(g["meshes"])
    off_node = len(g["nodes"])
    off_img = len(g["images"])
    off_tex = len(g["textures"])

    # ---- convert annunciator meshes to the packed layout --------------------------------
    new_vertices = bytearray()
    new_indices = bytearray()
    base_vcount = vbv["byteLength"] // STRIDE
    prim_infos = []                                         # (mesh index, primitive index, vstart, istart, vcount, icount, bounds)
    for mi, me in enumerate(a["meshes"]):
        for pi, p in enumerate(me["primitives"]):
            at = p["attributes"]
            pos = read_accessor(a, ann_bin, at["POSITION"])
            nrm = [norm3(v) for v in read_accessor(a, ann_bin, at["NORMAL"])]
            uv = read_accessor(a, ann_bin, at["TEXCOORD_0"])
            idx = read_accessor(a, ann_bin, p["indices"])
            assert len(pos) < 65536
            tan = tangents(pos, nrm, uv, idx)
            vstart = base_vcount + len(new_vertices) // STRIDE
            istart = ibv["byteLength"] + len(new_indices)
            new_vertices += pack_vertices(pos, nrm, tan, uv)
            # MSFS meshes are wound opposite to glTF's right-handed convention (all 20k sampled Ants triangles have
            # cross(e1,e2).normal < 0): swap two indices per triangle or the sim culls the outside and shows the inside
            flipped = []
            for t in range(0, len(idx), 3):
                flipped += [idx[t], idx[t + 2], idx[t + 1]]
            new_indices += struct.pack(f"<{len(flipped)}H", *flipped)
            lo = [min(v[k] for v in pos) for k in range(3)]
            hi = [max(v[k] for v in pos) for k in range(3)]
            prim_infos.append((mi, pi, vstart, istart, len(pos), len(idx), lo, hi))

    # ---- new binary: [..vertex view][our vertices][index view][our indices][animation data] ----
    v_end = vbv.get("byteOffset", 0) + vbv["byteLength"]
    assert ibv.get("byteOffset", 0) >= v_end
    out = bytearray(base_bin[:v_end])
    out += new_vertices
    shift_v = len(new_vertices)
    # everything after the vertex view moves by shift_v
    tail = base_bin[v_end:]
    out += tail
    for i, b in enumerate(g["bufferViews"]):
        if i != vi and b.get("byteOffset", 0) >= v_end:
            b["byteOffset"] = b.get("byteOffset", 0) + shift_v
    vbv["byteLength"] += shift_v
    i_end = ibv.get("byteOffset", 0) + ibv["byteLength"]            # (ibv offset already shifted)
    assert i_end == len(out) or i_end <= len(out)
    ins = bytes(out[:i_end]) + bytes(new_indices) + bytes(out[i_end:])
    out = bytearray(ins)
    for i, b in enumerate(g["bufferViews"]):
        if i != ii and b.get("byteOffset", 0) >= i_end:
            b["byteOffset"] = b.get("byteOffset", 0) + len(new_indices)
    ibv["byteLength"] += len(new_indices)

    # animation data (plain float arrays in their own buffer views, as in the Ants file)
    anim_acc_map = {}

    def copy_accessor(ai):
        if ai in anim_acc_map:
            return anim_acc_map[ai]
        ac = copy.deepcopy(a["accessors"][ai])
        bv = a["bufferViews"][ac["bufferView"]]
        start = bv.get("byteOffset", 0) + ac.get("byteOffset", 0)
        size = CT_SIZE[ac["componentType"]] * NCOMP[ac["type"]] * ac["count"]
        out.extend(b"\x00" * ((-len(out)) % 4))
        g["bufferViews"].append({"buffer": 0, "byteLength": size, "byteOffset": len(out)})
        out.extend(ann_bin[start:start + size])
        ac["bufferView"] = len(g["bufferViews"]) - 1
        ac.pop("byteOffset", None)
        ac.pop("name", None)
        g["accessors"].append(ac)
        anim_acc_map[ai] = len(g["accessors"]) - 1
        return anim_acc_map[ai]

    # ---- accessors / meshes ------------------------------------------------------------------
    new_meshes = []
    idx_acc_cache = {}
    for (mi, pi, vstart, istart, vc, ic, lo, hi) in prim_infos:
        me = new_meshes[mi] if mi < len(new_meshes) else None
        if me is None:
            me = copy.deepcopy(a["meshes"][mi])
            for p in me["primitives"]:
                p["attributes"] = {}
            new_meshes.append(me)
        prim = me["primitives"][pi]
        base_off = vstart * STRIDE
        defs = (("POSITION", 0, 5126, "VEC3"), ("TANGENT", 12, 5120, "VEC4"), ("NORMAL", 16, 5120, "VEC4"),
                ("TEXCOORD_0", 20, 5122, "VEC2"), ("TEXCOORD_1", 24, 5122, "VEC2"), ("COLOR_0", 28, 5123, "VEC4"))
        for name, o, ct, tp in defs:
            ac = {"bufferView": vi, "byteOffset": base_off + o, "componentType": ct, "count": vc, "type": tp}
            if name == "POSITION":
                ac["min"], ac["max"] = lo, hi
            g["accessors"].append(ac)
            prim["attributes"][name] = len(g["accessors"]) - 1
        g["accessors"].append({"bufferView": ii, "byteOffset": istart, "componentType": 5123, "count": ic,
                               "type": "SCALAR"})
        prim["indices"] = len(g["accessors"]) - 1
        # the optimized format is recognised through this per-primitive marker (present on every Ants primitive)
        prim["mode"] = 4
        prim["extras"] = {"ASOBO_primitive": {"PrimitiveCount": ic // 3, "VertexType": "VTX", "VertexVersion": 2}}

    # ---- images / textures (Ants convention) ---------------------------------------------------
    for img in a["images"]:
        base_name = os.path.splitext(os.path.basename(img["uri"]))[0].upper()
        g["images"].append({"uri": base_name + ".PNG.DDS", "name": img.get("name", base_name).lower(),
                            "extras": "ASOBO_image_converted_meta"})
    for t in a["textures"]:
        g["textures"].append({"extensions": {"MSFT_texture_dds": {"source": off_img + t["source"]}}})

    # ---- materials ---------------------------------------------------------------------------------
    base_mat_by_name = {m.get("name"): i for i, m in enumerate(g["materials"])}
    mat_map = {}
    for i, m in enumerate(a["materials"]):
        name = m.get("name")
        if name in base_mat_by_name:                      # e.g. 'mousezone' -> reuse base material
            mat_map[i] = base_mat_by_name[name]
            continue
        m = copy.deepcopy(m)

        def fix(tex):
            if isinstance(tex, dict) and "index" in tex:
                tex["index"] += off_tex
                tex.pop("texCoord", None)

        fix(m.get("normalTexture"))
        fix(m.get("occlusionTexture"))
        fix(m.get("emissiveTexture"))
        pbr = m.get("pbrMetallicRoughness", {})
        fix(pbr.get("baseColorTexture"))
        fix(pbr.get("metallicRoughnessTexture"))
        mat_map[i] = len(g["materials"])
        g["materials"].append(m)
    for me in new_meshes:
        for p in me["primitives"]:
            if "material" in p:
                p["material"] = mat_map[p["material"]]
        g["meshes"].append(me)

    # ---- nodes / scene --------------------------------------------------------------------------------
    for n in a["nodes"]:
        n = copy.deepcopy(n)
        if "mesh" in n:
            n["mesh"] += off_mesh
        if "children" in n:
            n["children"] = [c + off_node for c in n["children"]]
        g["nodes"].append(n)
    root_scene = g["scenes"][g.get("scene", 0)]
    root_scene["nodes"].extend(i + off_node for i in a["scenes"][a.get("scene", 0)]["nodes"])
    if diag_clone:      # DIAGNOSTIC: reuse known-good Ants meshes for two of our nodes
        by_name = {n.get("name"): n for n in g["nodes"][:off_node]}
        clone = {"mousezone_annunciator_switch": "mousezone_mag_left_hidden",
                 "annunciator_lamp_red": "altimeter_rear_modern_knob"}
        for n in g["nodes"][off_node:]:
            if n.get("name") in clone:
                n["mesh"] = by_name[clone[n["name"]]]["mesh"]

    # ---- animations -----------------------------------------------------------------------------------------
    g.setdefault("animations", [])
    for an in a.get("animations", []):
        an = copy.deepcopy(an)
        for ch in an["channels"]:
            ch["target"]["node"] += off_node
        for s in an["samplers"]:
            s["input"] = copy_accessor(s["input"])
            s["output"] = copy_accessor(s["output"])
        g["animations"].append(an)

    out.extend(b"\x00" * ((-len(out)) % 4))
    g["buffers"][0]["byteLength"] = len(out)
    g["buffers"][0]["uri"] = os.path.basename(out_bin_path)

    with open(out_gltf_path, "w", encoding="utf-8") as f:
        json.dump(g, f, indent=2)
    with open(out_bin_path, "wb") as f:
        f.write(out)
    return {"nodes_added": len(a["nodes"]), "meshes_added": len(a["meshes"]), "vertices_added": len(new_vertices) // STRIDE,
            "bin_bytes": len(out)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-dir", required=True)
    ap.add_argument("--ann", required=True, help="dir with annunciator.gltf / annunciator.bin")
    ap.add_argument("--out", required=True)
    ap.add_argument("--lods", nargs="+", default=["00", "01", "02"])
    ap.add_argument("--diag-clone", action="store_true", help="diagnostic: borrow existing Ants meshes for two nodes")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    for lod in args.lods:
        stem = f"AntsTigerMoth_int_LOD{lod}"
        res = merge(os.path.join(args.base_dir, stem + ".gltf"), os.path.join(args.base_dir, stem + ".bin"),
                    os.path.join(args.ann, "annunciator.gltf"), os.path.join(args.ann, "annunciator.bin"),
                    os.path.join(args.out, stem + ".gltf"), os.path.join(args.out, stem + ".bin"), args.diag_clone)
        print(stem, res)


if __name__ == "__main__":
    main()
