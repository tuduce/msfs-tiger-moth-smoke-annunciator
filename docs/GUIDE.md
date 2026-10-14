# Tiger Moth smoke annunciator – project guide (MSFS 2020)

A worn, vintage 60 × 30 × 30 mm box with a **red, white and blue lamp** and a **LONG / SHORT toggle**, mounted on the
**rear-cockpit dash** (the default pilot seat) of the Ant's Airplanes Tiger Moth, in the wood strip to the left of the airspeed indicator,
tilted -60° to follow the slanted panel edge (lamps run red / white / blue from bottom to top, switch at the top end); it clears the
speeds placard below it by 3 mm and its upper end overhangs the panel's slanted edge. It is 60 × 30 mm face and **15 mm** deep. (An earlier position on the right of the RPM
gauge, `-Cx -0.224 -Cz 0.220 -Rot 60`, also fits.)

| Part | Behaviour |
|---|---|
| red / white / blue lamp | lights while the matching smoke is on: `A:SMOKE ENABLE:4` red, `:5` white, `:6` blue (same vars the smoke addon uses) |
| toggle (up = LONG, down = SHORT) | click it in the cockpit. It sends `K:G_LIMITER_TOGGLE` and shows `A:G LIMITER SETTING` (0 = LONG, non-zero = SHORT), so it always agrees with the *Toggle G Limiter* key / joystick binding. Also bindable as `B:TM_Smoke_Duration_Switch_Set` |
| smoke | PaulWalkerUK's addon ("Toggle Smoke Intensity" = *Toggle G Limiter*): the effects read `G LIMITER SETTING` themselves. 0 = more intense (default, LONG), 1 = less intense (SHORT). No override of his files is needed any more |

The colour switches themselves are unchanged (white: prop de-ice / default smoke key, blue: engine anti-ice, red: "plasma").

## What is in the project

```
tigermoth-smoke-annunciator.xml            SDK project (open it in the MSFS SDK Project Editor, or build with fspackagetool)
PackageDefinitions/                        package definition + thumbnail
PackageSources/SimObjects/Airplanes/antsairplanes-tiger-moth/
    model/AntsTigerMoth_int.xml            copy of the Ants file + 2 added lines (Include + Component TM_ANNUNCIATOR)
    model/TigerMoth_Annunciator.xml        lamps (emissive), lever animation, click zone / input event   <- new
    model/AntsTigerMoth_int_LOD00-02.*     copies of the Ants interior glTF with the annunciator merged in (generated)
    texture/ANNUNCIATOR_*.PNG.DDS(+.json)  generated textures
blender/build_annunciator.py               headless Blender: model, materials, lever animation, glTF export, preview renders
blender/textures.py, dds.py                procedural chipped-paint PBR set + DDS (BC1 / BC5S) writer, no external tools
scripts/merge_gltf.py                      merges the annunciator into the interior LODs, in the sim's packed vertex format
scripts/make_package.py                    assembles Packages\... without the SDK tool
scripts/build.ps1  scripts/install.ps1     full rebuild / install / uninstall
_reference/                                pristine copy of the base interior LODs (merge input; never edited)
build/                                     intermediate output and preview renders
```

## Everyday use

```powershell
.\scripts\build.ps1 -Preview          # rebuild everything, also render build\preview\*.png
# add -NoSdkTool while MSFS is running (fspackagetool would start a second sim instance)
.\scripts\install.ps1                  # copy Packages\zz-tigermoth-smoke-annunciator into Community
.\scripts\install.ps1 -Uninstall       # remove it again
```

Needs: Blender 3.6 with the MSFS 2020 glTF exporter addon (already installed), the MSFS 2020 SDK, Python 3 on PATH.
`fspackagetool` starts `FlightSimulator.exe` as its build backend; the Store launcher then shows *"Something went wrong
launching your game. Custom arguments were used."* – harmless, click **Okay**. A build takes 30–90 s.

Requirements in the sim: the base Tiger Moth (`antsairplanes-aircraft-tiger-moth`) and the smoke addon
(`paulwalkeruk-tiger-moth-aerobatic-smoke`) must be installed. The package is called `zz-…` so it loads **after** both and
its copy of `AntsTigerMoth_int.xml` wins. Do **not** also install another mod that replaces that file. The package works with any version of the smoke addon that uses the G-limiter intensity (v1.1.0 here; it is documented in its readme).

## Changing things

* **Move the box**: `build.ps1 -Cx 0.230 -Cz 0.2205 -FaceY 0.797 -Rot -60` (glTF metres: centre x, centre height, and the Blender-y
  of the surface the back sits on; glTF z = −Blender y; `-Rot` tilts the long axis, 0 = horizontal). `scripts/find_spot.py [left] 60 30` maps the free wood and lists spots where a box of that size fits. Use `-Preview` and look at `build\preview\front.png`; render the
  cockpit view with  
  `blender -b --python blender/preview_cockpit.py -- <merged LOD gltf> <out.png>`.
  The rear dash face is crowded with gauges and the padded coaming hides the dash top edge (a first attempt standing the box on
  that edge was invisible from the seat). The only free wood for a 60 × 30 mm box is the diagonal strip between the RPM plate and
  the panel's right edge, with about 1 mm to spare. Render the view from the seat
  with the exterior included: `blender -b --python blender/preview_cockpit.py -- "<int LOD00.gltf>;<ext LOD00.gltf>" <out.png>`.
* **Lamp brightness**: `LAMP_INTENSITY` (default 0.5) in `TigerMoth_Annunciator.xml` scales the lamp's own emissive colour when lit (`OverrideBaseEmissive` must stay FALSE, otherwise the colour is replaced by white); the
  unlit lens colours are in `LAMPS` in `build_annunciator.py`.
* **Look**: edit `blender/textures.py` (colours, wear amount, lettering) or the geometry in `build_annunciator.py`.

## Testing in the sim (dev mode)

**After every rebuild/install, fully restart MSFS.** Reloading the aircraft keeps the old glTF cached (this cost several rounds of
"nothing changed" while debugging). Tip: the tooltip title in `TigerMoth_Annunciator.xml` is a handy version stamp.
`merge_gltf.py --diag-clone` builds a diagnostic variant that borrows two existing Ants meshes (red lamp, click zone) to separate
"nodes/XML work" from "my vertex data works".

1. Enable Developer Mode, load the Tiger Moth (rear seat, any livery) with the package installed.
2. *Tools → Virtual File System*: confirm `…/model/AntsTigerMoth_int.xml` and `…_int_LOD00.gltf` come from `zz-tigermoth-smoke-annunciator`.
3. *Tools → Behaviors*: watch `A:G LIMITER SETTING`, `A:SMOKE ENABLE:4/5/6`; the lamps follow the three smoke switches.
4. Click the lever (or use *Toggle G Limiter*); the smoke should change between more and less intense, and the lever follows. Check the Console window for XML errors mentioning
   `TigerMoth_Annunciator` or `annunciator_`.
5. The `zz-` ordering assumption (later folder name wins) is consistent with how the smoke addon already overrides the Ants
   package, but it has not been verified inside the sim.

## Things I could not verify here / known limits

* Every primitive in the optimized format needs `mode: 4` and `extras.ASOBO_primitive` (`PrimitiveCount`, `VertexType: VTX`, `VertexVersion: 2`);
  `merge_gltf.py` writes it.
* The Ants glTFs are in MSFS' *optimized* format (one shared packed vertex buffer: float32 position, int8 normal/tangent,
  float16 UV/colour). Meshes in any other layout are misread by the sim (invisible mesh, giant click zone), so `merge_gltf.py`
  re-encodes the annunciator vertices to that layout.

* Everything up to a successful package build is verified; **in-sim behaviour has not been run** (no way to drive the sim from here).
  The most likely points to need a tweak are the lamp emissive override (`<Material><EmissiveFactor>`, same pattern the Ants radio
  buttons use) and the tooltip strings.
* Pre-1.1.0 versions of the smoke addon (1.0.0) use different effect names; keep v1.1.0 installed.
* `fspackagetool` rejected a `SimObject`-type asset group for this overlay (no usable error text is exposed), so the package uses
  plain `Copy` groups and the textures are converted to DDS by `blender/dds.py` (same BC1 / BC5S formats as the Ants package).
* The package carries a copy of one third-party XML file (`AntsTigerMoth_int.xml`) and three glTF LODs. After an update of the Ants package or the smoke
  addon, rerun `build.ps1` after refreshing `_reference/` (delete the three `AntsTigerMoth_int_LOD0x.*` files there) and re-apply the
  small edit (Include + Component) to the XML copy. Personal use only – do not redistribute.
