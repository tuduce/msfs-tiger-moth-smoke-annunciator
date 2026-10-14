<#
.SYNOPSIS  Builds dist\TigerMothSmokeAnnunciator-<version>.zip - the installer kit for other people.

.DESCRIPTION
  The kit contains ONLY this project's own work: annunciator model (glTF), textures, behaviour XML, thumbnail, the installer and the
  two merge scripts.  It does NOT contain any file of the Ant's Airplanes Tiger Moth (its model files may not be redistributed);
  install_annunciator.py builds the final add-on on the user's PC from their installed copy.
  Version comes from the VERSION file (year.number, e.g. 26.1).
#>
param([switch]$SkipBuild)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$version = (Get-Content VERSION -Raw).Trim()
$name = "TigerMothSmokeAnnunciator-$version"
if (-not $SkipBuild) { & "$PSScriptRoot\build.ps1" -NoSdkTool | Out-Null }

$stage = Join-Path $root "dist\$name"
if (Test-Path $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
New-Item -ItemType Directory -Force "$stage\tools", "$stage\assets\texture" | Out-Null
Copy-Item release\install_annunciator.py $stage
# cmd.exe needs CRLF (LF-only .cmd files can break goto/labels)
foreach ($f in "Install.cmd", "Uninstall.cmd") {
    [IO.File]::WriteAllText("$stage\$f", ((Get-Content "release\$f" -Raw) -replace "`r?`n", "`r`n"), [Text.Encoding]::ASCII)
}
Copy-Item scripts\merge_gltf.py, scripts\patch_int_xml.py "$stage\tools"
Copy-Item VERSION $stage
[IO.File]::WriteAllText("$stage\README.txt", ((Get-Content release\README.txt -Raw).Replace("{VERSION}", $version) -replace "`r?`n", "`r`n"), (New-Object Text.UTF8Encoding($false)))
Copy-Item build\annunciator\annunciator.gltf, build\annunciator\annunciator.bin "$stage\assets"
Copy-Item PackageSources\SimObjects\Airplanes\antsairplanes-tiger-moth\model\TigerMoth_Annunciator.xml "$stage\assets"
Copy-Item PackageDefinitions\zz-tigermoth-smoke-annunciator\ContentInfo\Thumbnail.jpg "$stage\assets"
Copy-Item build\annunciator\texture\ANNUNCIATOR_*.PNG.DDS, build\annunciator\texture\ANNUNCIATOR_*.PNG.DDS.json "$stage\assets\texture"

# safety net: nothing Ants-derived may be in the kit
$bad = Get-ChildItem $stage -Recurse -File | Where-Object { $_.Name -match '^AntsTigerMoth|_LOD\d\d\.(gltf|bin)$' }
if ($bad) { throw "kit contains Ants-derived files: $($bad.Name -join ', ')" }

$zip = Join-Path $root "dist\$name.zip"
if (Test-Path $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path $stage -DestinationPath $zip -CompressionLevel Optimal
$hash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
"{0}  {1:N1} MB  sha256 {2}" -f $zip, ((Get-Item $zip).Length / 1MB), $hash
Get-ChildItem $stage -Recurse -File | ForEach-Object { "  " + $_.FullName.Substring($stage.Length + 1) }
