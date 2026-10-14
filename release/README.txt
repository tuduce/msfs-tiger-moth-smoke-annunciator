Tiger Moth Smoke Annunciator {VERSION}  -  for Microsoft Flight Simulator 2020 and 2024
=========================================================================================

A worn, vintage 60 x 30 x 15 mm box for the REAR cockpit dash of Ant's Airplanes Tiger Moth:

  * a red, a white and a blue lamp that light with the matching smoke
  * a LONG / SHORT toggle for the smoke intensity (click the lever, or use your "Toggle G Limiter"
    binding - it is PaulWalkerUK's smoke-intensity control, the lever just follows it)

YOU NEED (in the Community folder of each simulator you want it in)
  1. Ant's Airplanes Tiger Moth v1.4.1       https://www.antsairplanes.com/msfstigermoth.html
  2. PaulWalkerUK's "Tiger Moth Aerobatic Smoke" v1.1.0 or newer
                                             https://github.com/PaulWalkerUK/msfs-tiger-moth-aerobatic-smoke
  3. Python 3 (free)  https://www.python.org/downloads/   (tick "Add python.exe to PATH")
  Works with MSFS 2020 and MSFS 2024, Microsoft Store or Steam.

INSTALL
  1. Unzip this folder anywhere.
  2. Double-click  Install.cmd
     It finds your simulator(s) and asks which one to install for (2020, 2024 or all of them).
     To skip the question:   Install.cmd --sim 2020     Install.cmd --sim 2024     Install.cmd --sim both
  3. FULLY QUIT and restart Flight Simulator (reloading the aircraft is not enough).
  The box appears on the rear dash, left of the airspeed indicator.

  If your Community entries are junctions/symlinks (add-ons kept on another drive) that is fine: the files are
  written into the folder the link points to and the link is kept.

WHY AN INSTALLER AND NOT A READY-MADE PACKAGE?
  The annunciator has to be added to the Tiger Moth's interior model. Ant's Airplanes' model files may
  not be redistributed, so this kit contains only the annunciator itself; Install.cmd builds the final
  add-on on your PC from the Tiger Moth you already have, and writes it to
  <Community>\zz-tigermoth-smoke-annunciator. Nothing of the original package is modified.
  If you update the Tiger Moth, run Install.cmd again.

UNINSTALL
  Double-click Uninstall.cmd (same questions / same --sim options), or delete the folder
  zz-tigermoth-smoke-annunciator from the Community folder.

TUNING
  Lit-lamp brightness: edit LAMP_INTENSITY (default 0.5) in
  <Community>\zz-tigermoth-smoke-annunciator\SimObjects\Airplanes\antsairplanes-tiger-moth\model\TigerMoth_Annunciator.xml
  then reload the aircraft.

PROBLEMS
  Show what the installer detects:                Install.cmd --list
  Your Community folder is not detected:          Install.cmd --community "D:\path\to\Community"
  The Tiger Moth is somewhere else:               Install.cmd --community "..." --ants "D:\path\to\antsairplanes-aircraft-tiger-moth"
  Box not visible:   did you restart the SIM completely? Is "zz-tigermoth-smoke-annunciator" in that Community folder?
                     In dev mode, Tools > Virtual File System should list AntsTigerMoth_int_LOD00.gltf from it.

Source, build scripts and notes: https://github.com/tuduce/msfs-tiger-moth-smoke-annunciator
