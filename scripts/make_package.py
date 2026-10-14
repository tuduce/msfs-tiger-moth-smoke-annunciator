"""Assemble Packages/<name> without fspackagetool (which needs to start its own FlightSimulator.exe).

The package only contains plain copies (model/xml/textures), so this produces the same layout the SDK tool does:
manifest.json, layout.json (path, size, FILETIME date) and the copied asset folders.
Usage: python -I scripts/make_package.py
"""
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "zz-tigermoth-smoke-annunciator"
OUT = os.path.join(ROOT, "Packages", NAME)
SIM = os.path.join("SimObjects", "Airplanes", "antsairplanes-tiger-moth")
VERSION = open(os.path.join(ROOT, "VERSION")).read().strip()

MANIFEST = {
    "dependencies": [],
    "content_type": "MISC",
    "title": "Tiger Moth Smoke Annunciator",
    "manufacturer": "",
    "creator": "tuduce",
    "package_version": f"{VERSION}.0",
    "minimum_game_version": "1.38.2",
    "release_notes": {"neutral": {"LastUpdate": "", "OlderHistory": ""}},
}


def filetime(path):
    return int(os.path.getmtime(path) * 10_000_000) + 116444736000000000


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(os.path.join(ROOT, "PackageSources", SIM), os.path.join(OUT, SIM))
    ci_dst = os.path.join(OUT, "ContentInfo", NAME)
    shutil.copytree(os.path.join(ROOT, "PackageDefinitions", NAME, "ContentInfo"), ci_dst)
    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(MANIFEST, f, indent=2)
    content = []
    for dp, _, files in os.walk(OUT):
        for fn in sorted(files):
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, OUT).replace("\\", "/")
            if rel in ("manifest.json", "layout.json"):
                continue
            content.append({"path": rel, "size": os.path.getsize(full), "date": filetime(full)})
    content.sort(key=lambda c: c["path"])
    with open(os.path.join(OUT, "layout.json"), "w") as f:
        json.dump({"content": content}, f, indent=2)
    print(f"{NAME}: {len(content)} files, {sum(c['size'] for c in content)/1e6:.1f} MB")


if __name__ == "__main__":
    main()
