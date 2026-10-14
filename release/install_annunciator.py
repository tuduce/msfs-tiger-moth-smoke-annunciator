"""Installer for the Tiger Moth Smoke Annunciator - MSFS 2020 and MSFS 2024.  Python 3, standard library only.

It does NOT ship any file of the Ant's Airplanes Tiger Moth.  For each simulator you pick, it builds the add-on package from the Tiger
Moth installed in THAT simulator's Community folder:

  1. adds the two annunciator hooks to a copy of your AntsTigerMoth_int.xml
  2. merges the annunciator model (assets/annunciator.gltf) into copies of your interior LOD glTFs
  3. writes <Community>/zz-tigermoth-smoke-annunciator (model, textures, behaviour XML, manifest, layout)

Usage:
  py -3 install_annunciator.py                     detect your simulators and ask which to install for
  py -3 install_annunciator.py --sim 2024          2020 | 2024 | both | all   (no questions asked)
  py -3 install_annunciator.py --sim 2020 --uninstall
  py -3 install_annunciator.py --community "D:\\Path\\To\\Community" [--ants "<Tiger Moth package folder>"]   (custom location)
Add --dry-run to build in a temporary folder without touching Community, --list to only show what was detected.

If the Community entry is a junction/symlink (a common way to keep add-ons on another drive) the files are written into the folder it
points to and the link itself is kept.
"""
import argparse
import json
import os
import re
import shutil
import stat
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

# (label, MSFS version, UserCfg.opt that holds InstalledPackagesPath, default Community folder)
LOCAL = os.environ.get("LOCALAPPDATA", "")
ROAMING = os.environ.get("APPDATA", "")
INSTALLS = [
    ("MSFS 2020 (Microsoft Store)", "2020",
     os.path.join(LOCAL, "Packages", "Microsoft.FlightSimulator_8wekyb3d8bbwe", "LocalCache", "UserCfg.opt"),
     os.path.join(LOCAL, "Packages", "Microsoft.FlightSimulator_8wekyb3d8bbwe", "LocalCache", "Packages", "Community")),
    ("MSFS 2020 (Steam)", "2020",
     os.path.join(ROAMING, "Microsoft Flight Simulator", "UserCfg.opt"),
     os.path.join(ROAMING, "Microsoft Flight Simulator", "Packages", "Community")),
    ("MSFS 2024 (Microsoft Store)", "2024",
     os.path.join(LOCAL, "Packages", "Microsoft.Limitless_8wekyb3d8bbwe", "LocalCache", "UserCfg.opt"),
     os.path.join(LOCAL, "Packages", "Microsoft.Limitless_8wekyb3d8bbwe", "LocalCache", "Packages", "Community")),
    ("MSFS 2024 (Steam)", "2024",
     os.path.join(ROAMING, "Microsoft Flight Simulator 2024", "UserCfg.opt"),
     os.path.join(ROAMING, "Microsoft Flight Simulator 2024", "Packages", "Community")),
]


# ---------------------------------------------------------------------------------------------- helpers
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


def is_link(path):
    """True for symlinks and Windows junctions."""
    try:
        st = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & 0x400)


def detect_installs():
    """-> list of dicts {label, sim, community}; one per Community folder that exists."""
    found, seen = [], set()

    def add(label, sim, community):
        if not community or not os.path.isdir(community):
            return
        key = os.path.normcase(os.path.realpath(community))
        if key in seen:
            return
        seen.add(key)
        found.append({"label": label, "sim": sim, "community": os.path.abspath(community)})

    for label, sim, cfg, default in INSTALLS:
        p = parse_usercfg(cfg)
        add(label, sim, os.path.join(p, "Community") if p else None)
        add(label, sim, default)
    env = os.environ.get("MSFSCOMMUNITYDIRECTORY")
    if env:
        low = env.lower()
        add("custom (MSFSCOMMUNITYDIRECTORY)", "2024" if ("limitless" in low or "2024" in low) else "2020", env)
    return found


def find_ants_model_dir(community, explicit=None):
    if explicit:
        for sub in ("", os.path.join(SIM, "model")):
            d = os.path.join(explicit, sub)
            if os.path.exists(os.path.join(d, "AntsTigerMoth_int.xml")):
                return d
        raise SystemExit(f"--ants {explicit}: no AntsTigerMoth_int.xml found there")
    cands = []
    for name in sorted(os.listdir(community)):
        if name == PKG:
            continue
        d = os.path.join(community, name, SIM, "model")
        if all(os.path.exists(os.path.join(d, f)) for f in ("AntsTigerMoth_int.xml", "AntsTigerMoth_int_LOD00.gltf",
                                                           "AntsTigerMoth_int_LOD00.bin")):
            cands.append(d)
    if not cands:
        return None
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
    patch_int_xml.main(os.path.join(ants_dir, "AntsTigerMoth_int.xml"), os.path.join(model, "AntsTigerMoth_int.xml"))
    for lod in LODS:
        stem = f"AntsTigerMoth_int_LOD{lod}"
        merge_gltf.merge(os.path.join(ants_dir, stem + ".gltf"), os.path.join(ants_dir, stem + ".bin"),
                         os.path.join(assets, "annunciator.gltf"), os.path.join(assets, "annunciator.bin"),
                         os.path.join(model, stem + ".gltf"), os.path.join(model, stem + ".bin"))
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


def clear_dir_contents(path):
    for name in os.listdir(path):
        p = os.path.join(path, name)
        if is_link(p) or os.path.isfile(p):
            os.remove(p) if not os.path.isdir(p) else os.rmdir(p)
        else:
            shutil.rmtree(p)


# ---------------------------------------------------------------------------------------------- per-target actions
def install_one(target_info, assets, version, explicit_ants, dry_run):
    label, community = target_info["label"], target_info["community"]
    print(f"\n=== {label}\n    Community: {community}")
    ants_dir = find_ants_model_dir(community, explicit_ants)
    if not ants_dir:
        print("    SKIPPED: the Ant's Airplanes Tiger Moth is not in this Community folder (install it there first,\n"
              "             or give its location with --ants).")
        return False
    print(f"    Tiger Moth: {os.path.normpath(os.path.join(ants_dir, '..', '..', '..', '..'))}")
    ants_ver = package_version(os.path.normpath(os.path.join(ants_dir, "..", "..", "..", "..")))
    if ants_ver and vtuple(ants_ver) != (1, 4, 1):
        print(f"    NOTE: made for Ants Tiger Moth 1.4.1; you have {ants_ver}. If the build fails, that is why.")
    smoke = os.path.join(community, SMOKE_PKG)
    if not os.path.isdir(smoke):
        print("    WARNING: PaulWalkerUK's 'Tiger Moth Aerobatic Smoke' (v1.1.0+) is not in this Community folder - the lamps and the\n"
              "             switch need it: https://github.com/PaulWalkerUK/msfs-tiger-moth-aerobatic-smoke")
    else:
        sv = package_version(smoke)
        if sv and vtuple(sv) < (1, 1, 0):
            print(f"    WARNING: smoke addon {sv} found; v1.1.0 or newer is required.")

    tmp = tempfile.mkdtemp(prefix="tm_annunciator_")
    try:
        out = os.path.join(tmp, PKG)
        old_stdout = sys.stdout
        sys.stdout = open(os.devnull, "w")          # the merge helpers are chatty
        try:
            n = write_package(out, assets, ants_dir, version)
        finally:
            sys.stdout.close()
            sys.stdout = old_stdout
        if dry_run:
            print(f"    dry run OK ({n} files built, nothing written)")
            return True
        target = os.path.join(community, PKG)
        if is_link(target):
            real = os.path.realpath(target)
            os.makedirs(real, exist_ok=True)
            clear_dir_contents(real)
            for name in os.listdir(out):
                src = os.path.join(out, name)
                (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, os.path.join(real, name))
            print(f"    installed ({n} files) through the link {PKG} -> {real}")
        else:
            if os.path.isdir(target):
                shutil.rmtree(target)
            shutil.copytree(out, target)
            print(f"    installed ({n} files) -> {target}")
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def uninstall_one(target_info):
    label, community = target_info["label"], target_info["community"]
    target = os.path.join(community, PKG)
    print(f"\n=== {label}\n    Community: {community}")
    if is_link(target):
        os.rmdir(target)                              # removes only the junction/link, never what it points to
        print(f"    removed the link {PKG} (the folder it pointed to was left in place)")
    elif os.path.isdir(target):
        shutil.rmtree(target)
        print(f"    removed {target}")
    else:
        print("    not installed")


def choose_targets(installs, sim_arg):
    sims = {"2020": ["2020"], "2024": ["2024"], "both": ["2020", "2024"], "all": ["2020", "2024"]}
    if sim_arg:
        want = sims[sim_arg]
        chosen = [i for i in installs if i["sim"] in want]
        missing = [s for s in want if not any(i["sim"] == s for i in installs)]
        for s in missing:
            print(f"NOTE: no MSFS {s} Community folder was detected (use --community to point to it).")
        return chosen
    if len(installs) == 1:
        return installs
    if not sys.stdin or not sys.stdin.isatty():
        return installs                               # non-interactive: every detected simulator
    print("\nInstall for which simulator?")
    for n, i in enumerate(installs, 1):
        print(f"  [{n}] {i['label']}")
    print("  [a] all of the above")
    ans = input("Enter a number, several separated by commas, or 'a' (Enter = cancel): ").strip().lower()
    if not ans:
        return []
    if ans in ("a", "all"):
        return installs
    picked = []
    for part in re.split(r"[,\s]+", ans):
        if part.isdigit() and 1 <= int(part) <= len(installs):
            picked.append(installs[int(part) - 1])
    return picked


def main():
    ap = argparse.ArgumentParser(description="Install the Tiger Moth Smoke Annunciator for MSFS 2020 and/or 2024")
    ap.add_argument("--sim", choices=("2020", "2024", "both", "all"), help="which simulator(s); omit to be asked")
    ap.add_argument("--community", help="a specific Community folder (instead of auto-detection)")
    ap.add_argument("--ants", help="the Ants Tiger Moth package folder (auto-detected inside Community if omitted)")
    ap.add_argument("--assets", default=None, help="annunciator assets folder (default: ./assets)")
    ap.add_argument("--uninstall", action="store_true", help="remove the annunciator again")
    ap.add_argument("--dry-run", action="store_true", help="build in a temp folder, do not touch Community")
    ap.add_argument("--list", action="store_true", help="only show the detected simulators")
    args = ap.parse_args()
    version = read_version()
    print(f"Tiger Moth Smoke Annunciator {version}")

    if args.community:
        if not os.path.isdir(args.community):
            raise SystemExit(f"--community {args.community}: folder not found")
        installs = [{"label": "custom location", "sim": args.sim or "custom", "community": os.path.abspath(args.community)}]
    else:
        installs = detect_installs()
    if args.list or not installs:
        if not installs:
            raise SystemExit("No MSFS Community folder was found. Run again with  --community \"<path to your Community folder>\".")
        print("Detected:")
        for i in installs:
            print(f"  {i['label']:<32} {i['community']}")
        if args.list:
            return

    targets = installs if args.community else choose_targets(installs, args.sim)
    if not targets:
        print("Nothing selected.")
        return

    if args.uninstall:
        for t in targets:
            uninstall_one(t)
        return

    assets = args.assets or os.path.join(HERE, "assets")
    if not os.path.exists(os.path.join(assets, "annunciator.gltf")):
        raise SystemExit(f"assets not found in {assets}")
    ok = [install_one(t, assets, version, args.ants, args.dry_run) for t in targets]
    print()
    if any(ok) and not args.dry_run:
        print("Done. Now FULLY QUIT and restart Microsoft Flight Simulator (reloading the aircraft is not enough).")
        print("The box is on the rear-cockpit dash, to the left of the airspeed indicator.")
    elif not any(ok):
        raise SystemExit("Nothing was installed.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if e.code not in (0, None):
            print("\nERROR: " + str(e.code))
        sys.exit(e.code)
