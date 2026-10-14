Tiger Moth Smoke Annunciator {VERSION}  -  for Microsoft Flight Simulator 2020
================================================================================

A worn, vintage 60 x 30 x 15 mm box for the REAR cockpit dash of Ant's Airplanes Tiger Moth:

  * a red, a white and a blue lamp that light with the matching smoke
  * a LONG / SHORT toggle for the smoke intensity (click the lever, or use your "Toggle G Limiter"
    binding - it is PaulWalkerUK's smoke-intensity control, the lever just follows it)

YOU NEED
  1. Microsoft Flight Simulator 2020 (Store or Steam)
  2. Ant's Airplanes Tiger Moth v1.4.1, installed in your Community folder
     https://www.antsairplanes.com/msfstigermoth.html
  3. PaulWalkerUK's "Tiger Moth Aerobatic Smoke" v1.1.0 or newer, installed in Community
     https://github.com/PaulWalkerUK/msfs-tiger-moth-aerobatic-smoke
  4. Python 3 (free)  https://www.python.org/downloads/   (tick "Add python.exe to PATH")

INSTALL
  1. Unzip this folder anywhere.
  2. Double-click  Install.cmd
  3. FULLY QUIT and restart Flight Simulator (reloading the aircraft is not enough).
  The box appears on the rear dash, left of the airspeed indicator.

WHY AN INSTALLER AND NOT A READY-MADE PACKAGE?
  The annunciator has to be added to the Tiger Moth's interior model. Ant's Airplanes' model files may
  not be redistributed, so this kit contains only the annunciator itself; Install.cmd builds the final
  add-on on your PC from the Tiger Moth you already have, and writes it to
  <Community>\zz-tigermoth-smoke-annunciator. Nothing of the original package is modified.

  If you update the Tiger Moth, run Install.cmd again.

UNINSTALL
  Double-click Uninstall.cmd (or delete the folder zz-tigermoth-smoke-annunciator from Community).

TUNING
  Lit-lamp brightness: edit LAMP_INTENSITY (default 0.5) in
  <Community>\zz-tigermoth-smoke-annunciator\SimObjects\Airplanes\antsairplanes-tiger-moth\model\TigerMoth_Annunciator.xml
  then reload the aircraft.

PROBLEMS
  Installer cannot find your Community folder:   Install.cmd --community "D:\path\to\Community"
  Installer cannot find the Tiger Moth:          Install.cmd --ants "D:\path\to\antsairplanes-aircraft-tiger-moth"
  Box not visible:   did you restart the SIM completely? Is "zz-tigermoth-smoke-annunciator" in Community?
                     In dev mode, Tools > Virtual File System should list AntsTigerMoth_int_LOD00.gltf from it.

Source, build scripts and notes: https://github.com/tuduce/msfs-tiger-moth-smoke-annunciator
