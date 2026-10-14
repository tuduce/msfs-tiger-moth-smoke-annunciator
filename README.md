# Tiger Moth smoke annunciator (MSFS 2020 + 2024)

![The annunciator](docs/preview.jpg)

*(Blender render of the model.)*

A worn, vintage 60 × 30 × 15 mm annunciator box for the **rear cockpit dash of Ant's Airplanes Tiger Moth** in Microsoft Flight Simulator **2020 and 2024**, for use with
PaulWalkerUK's [Tiger Moth Aerobatic Smoke](https://github.com/PaulWalkerUK/msfs-tiger-moth-aerobatic-smoke) addon:

* a **red, white and blue lamp** that light up with the matching smoke;
* a **LONG / SHORT toggle** for the smoke intensity. It drives the smoke addon's own *Toggle G Limiter* control, so clicking the lever and using your key or
  joystick binding always agree.

## Install (players)

Download **`TigerMothSmokeAnnunciator-<version>.zip`** from the [Releases](../../releases) page, unzip it and double-click **`Install.cmd`**. It detects your
simulator(s) (2020 and/or 2024, Store or Steam) and asks which to install for; then **fully restart MSFS**.
No questions: `Install.cmd --sim 2020`, `--sim 2024` or `--sim both`. `Install.cmd --list` shows what it detected.

You need

1. MSFS 2020 or 2024 (Store or Steam);
2. [Ant's Airplanes Tiger Moth](https://www.antsairplanes.com/msfstigermoth.html) v1.4.1 in that simulator's Community folder;
3. the [Tiger Moth Aerobatic Smoke](https://github.com/PaulWalkerUK/msfs-tiger-moth-aerobatic-smoke) addon v1.1.0 or newer in the same Community folder;
4. [Python 3](https://www.python.org/downloads/) (the installer is a small standard-library script).

**Why an installer instead of a ready-made package?** The box has to be added to the Tiger Moth's interior model, and Ant's Airplanes' model files may not be
redistributed. The release therefore contains only the annunciator itself; `Install.cmd` builds the final add-on on your PC from the Tiger Moth you already own and
writes it to `Community\zz-tigermoth-smoke-annunciator` (the original package is not modified; if that Community entry is a junction, the files go into the folder it points to). Run it again after updating the Tiger Moth;
`Uninstall.cmd` removes it.

## What it does

| Part | Behaviour |
|---|---|
| red / white / blue lamp | lights while that smoke is on (`A:SMOKE ENABLE:4 / 5 / 6`) |
| lever (up = LONG, down = SHORT) | click it, or use *Toggle G Limiter*. LONG = intense smoke (default), SHORT = less intense. Also bindable as `B:TM_Smoke_Duration_Switch_Set` |

Lit-lamp brightness is `LAMP_INTENSITY` in `TigerMoth_Annunciator.xml` (edit the installed copy, then reload the aircraft).

## Build from source (developers)

Everything is scripted: headless Blender builds the model and its procedural chipped-paint textures, a merge step writes the model into the interior glTFs of the
installed Ants Tiger Moth (in MSFS' *optimized* vertex format), and the result is packaged for the Community folder.

```powershell
.\scripts\build.ps1 -Preview      # Blender build + merge + package   (-NoSdkTool while MSFS is running)
.\scripts\install.ps1             # copy the built package to Community (-Uninstall removes it)
.\scripts\make_release.ps1        # dist\TigerMothSmokeAnnunciator-<VERSION>.zip, the installer kit above
```

Requirements: MSFS 2020 + SDK, Blender 3.6 with the MSFS 2020 glTF exporter addon, Python 3. See **[docs/GUIDE.md](docs/GUIDE.md)** for the design notes,
how to move the box, tune the lamps, test in the sim, and the pitfalls found on the way (the packed vertex format, triangle winding, the sim's model cache).

No file of the Ants Tiger Moth is stored in this repository; derived files are generated locally and git-ignored.

Releases are numbered `year.number` (e.g. `26.1` = first release of 2026).
