"""Installer for the Tiger Moth Smoke Annunciator (MSFS 2020).  Python 3, standard library only.

It does NOT ship any file of the Ant's Airplanes Tiger Moth.  Instead it builds the add-on package on this PC from the Tiger Moth
you have installed:

  1. adds the two annunciator hooks to a copy of your AntsTigerMoth_int.xml
  2. merges the annunciator model (assets/annunciator.gltf) into copies of your interior LOD glTFs
  3. writes <Community>/zz-tigermoth-smoke-annunciator (model, textures, behaviour XML, manifest, layout)

Usage:   py -3 install_annunciator.py [--community PATH] [--ants PATH] [--uninstall] [--dry-run]
"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
for d in (HERE, os.path.join(HERE, "tools"), os.path.join(os.path.dirname(HERE), "scripts")):
    if os.path.isdir(d):
        sys.path.insert(0, d)
import merge_gltf  # noqa: E402
import patch_int_xml  # noqa: E402

PKG = "zz-tigermoth-smoke-annunciator"
ANTS_PKG = "antsairplanes-aircraft-tiger-moth"
SMOKE_PKG = "paulwalkeruk-tiger-moth-aerobatic-smoke"
SIM = os.path.join("SimObjects", "Airplanes", "antsairplanes-tiger-moth")
LODS = ("00", "01", "02")


def read_version():
    for p in (os.path.join(HERE, "VERSION"), os.path.join(os.path.dirname(HERE), "VERSION")):
        if os.path.exists(p):
            return open(p).read().strip()
    return "0.0"


def parse_usercfg(path):
    try:
        text = open(path, "r", encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    m = re.search(r'^InstalledPackagesPath\s+"([^"]+)"', text, re.M)
    return m.group(1) if m else None


def community_candidates():
    out = []
    env = os.environ.get("MSFSCOMMUNITYDIRECTORY")
    if env:
        out.append(env)
    local = os.environ.get("LOCALAPPDATA", "")
    roaming = os.environ.get("APPDATA", "")
    cfgs = [os.path.join(local, "Packages", "Microsoft.FlightSimulator_8wekyb3d8bbwe", "LocalCache", "UserCfg.opt"),   # Microsoft Store
            os.path.join(roaming, "Microsoft Flight Simulator", "UserCfg.opt")]                                        # Steam
    for cfg in cfgs:
        p = parse_usercfg(cfg)
        if p:
            out.append(os.path.join(p, "Community"))
    out += [os.path.join(local, "Packages", "Microsoft.FlightSimulator_8wekyb3d8bbwe", "LocalCache", "Packages", "Community"),
            os.path.join(roaming, "Microsoft Flight Simulator", "Packages", "Community")]
    seen, res = set(), []
    for p in out:
        k = os.path.normcase(os.path.abspath(p))
        if k not in seen and os.path.isdir(p):
            seen.add(k)
            res.append(os.path.abspath(p))
    return res


def find_ants_model_dir(community, explicit=None):
    cands = []
    if explicit:
        for sub in ("", os.path.join(SIM, "model")):
            d = os.path.join(explicit, sub)
            if os.path.exists(os.path.join(d, "AntsTigerMoth_int.xml")):
                return d
        raise SystemExit(f"--ants {explicit}: no AntsTigerMoth_int.xml found there")
    for name in sorted(os.listdir(community)):
        if name == PKG:
            continue
        d = os.path.join(community, name, SIM, "model")
        if all(os.path.exists(os.path.join(d, f)) for f in ("AntsTigerMoth_int.xml", "AntsTigerMoth_int_LOD00.gltf",
                                                           "AntsTigerMoth_int_LOD00.bin")):
            cands.append(d)
    if not cands:
        raise SystemExit("Could not find the Ant's Airplanes Tiger Moth in your Community folder.\n"
                         "Install it first, or point to it with  --ants <path to its package folder>.")
    pref = [c for c in cands if ANTS_PKG in c]
    return (pref or cands)[0]


def package_version(pkg_dir):
    try:
        return json.load(open(os.path.join(pkg_dir, "manifest.json"), encoding="utf-8-sig")).get("package_version")
    except (OSError, ValueError):
        return None


def vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "0"))[:3]


def filetime(path):
    return int(os.path.getmtime(path) * 10_000_000) + 116444736000000000


def write_package(out, assets, ants_dir, version):
    sim = os.path.join(out, SIM)
    model = os.path.join(sim, "model")
    os.makedirs(model)
    # 1. patched interior XML
    patch_int_xml.main(os.path.join(ants_dir, "AntsTigerMoth_int.xml"), os.path.join(model, "AntsTigerMoth_int.xml"))
    # 2. merged interior LODs
    ann = os.path.join(assets)
    for lod in LODS:
        stem = f"AntsTigerMoth_int_LOD{lod}"
        res = merge_gltf.merge(os.path.join(ants_dir, stem + ".gltf"), os.path.join(ants_dir, stem + ".bin"),
                               os.path.join(ann, "annunciator.gltf"), os.path.join(ann, "annunciator.bin"),
                               os.path.join(model, stem + ".gltf"), os.path.join(model, stem + ".bin"))
        print(f"  {stem}: +{res['meshes_added']} meshes, {res['vertices_added']} vertices")
    # 3. own files
    shutil.copy2(os.path.join(assets, "TigerMoth_Annunciator.xml"), model)
    shutil.copytree(os.path.join(assets, "texture"), os.path.join(sim, "texture"))
    ci = os.path.join(out, "ContentInfo", PKG)
    os.makedirs(ci)
    if os.path.exists(os.path.join(assets, "Thumbnail.jpg")):
        shutil.copy2(os.path.join(assets, "Thumbnail.jpg"), ci)
    manifest = {"dependencies": [], "content_type": "MISC", "title": "Tiger Moth Smoke Annunciator", "manufacturer": "",
                "creator": "tuduce", "package_version": f"{version}.0", "minimum_game_version": "1.38.2",
                "release_notes": {"neutral": {"LastUpdate": "", "OlderHistory": ""}}}
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    content = []
    for dp, _, files in os.walk(out):
        for fn in files:
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, out).replace("\\", "/")
            if rel not in ("manifest.json", "layout.json"):
                content.append({"path": rel, "size": os.path.getsize(full), "date": filetime(full)})
    content.sort(key=lambda c: c["path"])
    with open(os.path.join(out, "layout.json"), "w") as f:
        json.dump({"content": content}, f, indent=2)
    return len(content)


def main():
    ap = argparse.ArgumentParser(description="Install the Tiger Moth Smoke Annunciator for MSFS 2020")
    ap.add_argument("--community", help="MSFS 2020 Community folder (auto-detected if omitted)")
    ap.add_argument("--ants", help="the Ants Tiger Moth package folder (auto-detected if omitted)")
    ap.add_argument("--assets", default=None, help="annunciator assets folder (default: ./assets)")
    ap.add_argument("--uninstall", action="store_true", help="remove the annunciator from the Community folder")
    ap.add_argument("--dry-run", action="store_true", help="build the package in a temp folder, do not touch Community")
    args = ap.parse_args()
    version = read_version()
    print(f"Tiger Moth Smoke Annunciator {version}")

    if args.community:
        cands = [os.path.abspath(args.community)]
    else:
        cands = community_candidates()
    cands = [c for c in cands if os.path.isdir(c)]
    if not cands:
        raise SystemExit("Could not find your MSFS 2020 Community folder. Run again with  --community <path>.")
    community = cands[0]
    if len(cands) > 1:
        print("  other Community folders found (using the first): " + "; ".join(cands[1:]))
    print(f"Community folder: {community}")
    target = os.path.join(community, PKG)

    if args.uninstall:
        if os.path.isdir(target):
            shutil.rmtree(target)
            print("Removed " + target)
        else:
            print("Not installed.")
        return

    assets = args.assets or os.path.join(HERE, "assets")
    if not os.path.exists(os.path.join(assets, "annunciator.gltf")):
        raise SystemExit(f"assets not found in {assets}")
    ants_dir = find_ants_model_dir(community, args.ants)
    print(f"Ants Tiger Moth model folder: {ants_dir}")

    # dependency checks (warnings only)
    ants_ver = package_version(os.path.normpath(os.path.join(ants_dir, "..", "..", "..", "..")))
    if ants_ver and vtuple(ants_ver) != (1, 4, 1):
        print(f"  NOTE: this was made for Ants Tiger Moth 1.4.1; you have {ants_ver}. If the build below fails, that is why.")
    smoke = os.path.join(community, SMOKE_PKG)
    if not os.path.isdir(smoke):
        print("  WARNING: PaulWalkerUK's 'Tiger Moth Aerobatic Smoke' (v1.1.0+) is not in this Community folder.\n"
              "           The lamps and the switch need it: https://github.com/PaulWalkerUK/msfs-tiger-moth-aerobatic-smoke")
    else:
        sv = package_version(smoke)
        if sv and vtuple(sv) < (1, 1, 0):
            print(f"  WARNING: smoke addon {sv} found; v1.1.0 or newer is required (lamps/switch use its smoke slots and effects).")

    tmp = tempfile.mkdtemp(prefix="tm_annunciator_")
    try:
        out = os.path.join(tmp, PKG)
        print("Building the package from your installed Tiger Moth ...")
        n = write_package(out, assets, ants_dir, version)
        print(f"  {n} files")
        if args.dry_run:
            print("Dry run OK (nothing written to Community).")
            return
        if os.path.isdir(target):
            shutil.rmtree(target)
        shutil.copytree(out, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"Installed to {target}")
    print("Now FULLY QUIT and restart Microsoft Flight Simulator (reloading the aircraft is not enough).")
    print("Look for the box on the rear-cockpit dash, to the left of the airspeed indicator.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if e.code not in (0, None):
            print("\nERROR: " + str(e.code))
        sys.exit(e.code)
