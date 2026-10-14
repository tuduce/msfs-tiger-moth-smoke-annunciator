<#
.SYNOPSIS  Installs (or removes) the built package in the MSFS 2020 Community folder.
.PARAMETER Uninstall  remove the package from Community again.
Only the folder  <Community>\zz-tigermoth-smoke-annunciator  is ever touched.
#>
param([switch]$Uninstall)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$community = $env:MSFSCOMMUNITYDIRECTORY
if (-not $community -or -not (Test-Path $community)) { throw "MSFSCOMMUNITYDIRECTORY is not set / does not exist" }
$name = "zz-tigermoth-smoke-annunciator"
$target = Join-Path $community $name
if ((Split-Path -Leaf $target) -ne $name) { throw "unexpected target $target" }

if ($Uninstall) {
    if (Test-Path $target) { Remove-Item -LiteralPath $target -Recurse -Force; Write-Host "removed $target" }
    else { Write-Host "not installed" }
    return
}
$src = Join-Path $root "Packages\$name"
if (-not (Test-Path (Join-Path $src "layout.json"))) { throw "build the package first (scripts\build.ps1)" }
foreach ($dep in "antsairplanes-aircraft-tiger-moth", "paulwalkeruk-tiger-moth-aerobatic-smoke") {
    if (-not (Test-Path (Join-Path $community $dep))) { Write-Warning "$dep is not in Community - the annunciator needs it" }
}
New-Item -ItemType Directory -Force $target | Out-Null
robocopy $src $target /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($LASTEXITCODE)" }
Write-Host "installed -> $target"
