"""Create PackageSources/.../model/AntsTigerMoth_int.xml from the user's installed Ants Tiger Moth, adding the annunciator hooks.

Two insertions only (everything else is byte-identical to the Ants file, CRLF preserved):
  1. <Include RelativeFile="TigerMoth_Annunciator.xml"/> after the AntsTigerMoth_FX.xml include
  2. <Component ID="TM_ANNUNCIATOR"> after the existing <Component ID="FX"> block
The Ants file is never committed to this repository; it is regenerated on every build.
Usage: python -I scripts/patch_int_xml.py <base AntsTigerMoth_int.xml> <output path>
"""
import sys

INCLUDE_ANCHOR = '\t<Include RelativeFile="AntsTigerMoth_FX.xml"/>'
FX_ANCHOR = '\t<Component ID="FX">{nl}\t\t<UseTemplate Name="Ants_TigerMoth_FX" />{nl}\t</Component>'


def main(src, dst):
    raw = open(src, "rb").read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw[3:].decode("utf-8") if bom else raw.decode("utf-8")
    nl = "\r\n" if "\r\n" in text else "\n"
    if "TigerMoth_Annunciator.xml" in text or "TM_ANNUNCIATOR" in text:
        raise SystemExit(f"{src} already contains the annunciator hooks - point this script at the pristine Ants file")
    if text.count(INCLUDE_ANCHOR) != 1:
        raise SystemExit("anchor 1 (FX include) not found exactly once - Ants file changed? patch_int_xml.py needs an update")
    fx = FX_ANCHOR.format(nl=nl)
    if text.count(fx) != 1:
        raise SystemExit("anchor 2 (FX component) not found exactly once - Ants file changed? patch_int_xml.py needs an update")
    text = text.replace(INCLUDE_ANCHOR, INCLUDE_ANCHOR + nl + '\t<Include RelativeFile="TigerMoth_Annunciator.xml"/>')
    text = text.replace(fx, fx + nl + nl + "\t<!-- Smoke annunciator (lamps, LONG/SHORT switch) -->" + nl +
                        '\t<Component ID="TM_ANNUNCIATOR">' + nl + '\t\t<UseTemplate Name="TigerMoth_Annunciator" />' + nl +
                        "\t</Component>")
    with open(dst, "wb") as f:
        f.write((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8"))
    print(f"patched {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
