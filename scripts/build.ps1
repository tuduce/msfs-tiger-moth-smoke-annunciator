<#
.SYNOPSIS
  Rebuilds the Tiger Moth smoke annunciator package end to end.

.DESCRIPTION
  1. Blender (headless) builds the model + procedural textures + DDS  -> build\annunciator
  2. merge_gltf.py merges the model into copies of the Ants interior LOD glTFs
  3. DDS textures are copied into PackageSources
  4. fspackagetool builds the MSFS package                              -> Packages\zz-tigermoth-smoke-annunciator

  NOTE: fspackagetool starts FlightSimulator.exe as its build backend.  The Microsoft Store launcher then shows
  "Something went wrong launching your game. Custom arguments were used." - harmless, click Okay.

.PARAMETER Preview      also render preview images to build\preview
.PARAMETER SkipPackage  stop after step 3 (no packaging)
.PARAMETER NoSdkTool    assemble the package with scripts\make_package.py instead of fspackagetool
                (use this while MSFS is running: fspackagetool starts its own FlightSimulator.exe)
.PARAMETER Cx/Cz/FaceY  box placement (glTF metres): centre x, centre height, and Blender-y of the surface the rear sits on
.PARAMETER Rot          tilt of the box long axis from horizontal in degrees (-60 = along the slanted left edge, reading upward; +60 = right edge)
#>
param(
    [switch]$Preview,
    [switch]$SkipPackage,
    [switch]$NoSdkTool,
    [double]$Cx = 0.230,
    [double]$Cz = 0.2205,
    [double]$FaceY = 0.797,
    [double]$Rot = -60,
    [string]$Blender = "C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
    [string]$BaseModelDir = "D:\addons\aircraft\antsairplanes-aircraft-tiger-moth\SimObjects\Airplanes\antsairplanes-tiger-moth\model"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$sim = "PackageSources\SimObjects\Airplanes\antsairplanes-tiger-moth"

New-Item -ItemType Directory -Force build | Out-Null
# pristine copies of the base interior LODs (read-only reference for the merge)
New-Item -ItemType Directory -Force _reference | Out-Null
foreach ($f in "AntsTigerMoth_int_LOD00", "AntsTigerMoth_int_LOD01", "AntsTigerMoth_int_LOD02") {
    foreach ($ext in "gltf", "bin") {
        $dst = "_reference\$f.$ext"
        if (-not (Test-Path $dst)) { Copy-Item "$BaseModelDir\$f.$ext" $dst }
    }
}

Write-Host "== 1/4 Blender build" -ForegroundColor Cyan
$bargs = @("-b", "--python", "blender\build_annunciator.py", "--", "--out", "build\annunciator",
           "--cx", $Cx, "--cz", $Cz, "--face-y", $FaceY, "--rot", $Rot, "--blend", "build\annunciator.blend")
if ($Preview) { $bargs += @("--preview", "build\preview") }
# Blender prints a harmless banner on stderr; keep $ErrorActionPreference=Stop from turning it into a failure
$prevEap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
& $Blender @bargs *> build\blender.log
$ErrorActionPreference = $prevEap
if ($LASTEXITCODE -ne 0 -or -not (Select-String -Path build\blender.log -Pattern "EXPORTED" -Quiet)) {
    Get-Content build\blender.log -Tail 30; throw "Blender build failed (see build\blender.log)"
}

Write-Host "== 2/4 patch Ants interior XML + merge into interior LODs" -ForegroundColor Cyan
python -I scripts\patch_int_xml.py "$BaseModelDir\AntsTigerMoth_int.xml" "$sim\model\AntsTigerMoth_int.xml"
if ($LASTEXITCODE -ne 0) { throw "patch_int_xml failed" }
python -I scripts\merge_gltf.py --base-dir _reference --ann build\annunciator --out "$sim\model"
if ($LASTEXITCODE -ne 0) { throw "merge failed" }

Write-Host "== 3/4 stage textures" -ForegroundColor Cyan
New-Item -ItemType Directory -Force "$sim\texture" | Out-Null
Copy-Item build\annunciator\texture\ANNUNCIATOR_*.PNG.DDS, build\annunciator\texture\ANNUNCIATOR_*.PNG.DDS.json "$sim\texture" -Force

if ($SkipPackage) { Write-Host "skipped fspackagetool (-SkipPackage)"; return }

if ($NoSdkTool) {
    Write-Host "== 4/4 assemble package (make_package.py, no SDK tool)" -ForegroundColor Cyan
    python -I scripts\make_package.py
    if ($LASTEXITCODE -ne 0) { throw "make_package failed" }
    return
}
Write-Host "== 4/4 fspackagetool (starts the sim build backend, takes ~30-90 s)" -ForegroundColor Cyan
& "C:\MSFS SDK\Tools\bin\fspackagetool.exe" -nopause -rebuild tigermoth-smoke-annunciator.xml | Out-Null
[xml]$failed = Get-Content _PackageInt\_FailedPackages.xml
if ($failed.FailedPackages.HasChildNodes) { throw "fspackagetool reported failed packages: see _PackageInt\_FailedPackages.xml" }
if (-not (Test-Path Packages\zz-tigermoth-smoke-annunciator\layout.json)) { throw "package output missing" }
Write-Host "OK -> Packages\zz-tigermoth-smoke-annunciator" -ForegroundColor Green
