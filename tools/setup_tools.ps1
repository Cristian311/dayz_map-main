# Instaleaza uneltele necesare in folderul tools\ (Sollumz + szio + pymateria), izolat de Blender-ul tau.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$tools = Join-Path $root "tools"
$sollumzVersion = "v2.9.0"
$szioVersion = "1.3.0.dev9"
$pymateriaVersion = "0.2.0"

# --- Blender ---
$blender = $null
$pathFile = Join-Path $tools "blender_path.txt"
if (Test-Path $pathFile) { $blender = (Get-Content $pathFile -TotalCount 1).Trim() }
if (-not $blender -or -not (Test-Path $blender)) {
    $cand = Get-ChildItem "$env:ProgramFiles\Blender Foundation" -Directory -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending | Select-Object -First 1
    if ($cand) { $blender = Join-Path $cand.FullName "blender.exe" }
}
if (-not $blender -or -not (Test-Path $blender)) {
    Write-Host "Nu am gasit blender.exe. Instaleaza Blender 4.2+ (recomandat 5.x) sau scrie calea in tools\blender_path.txt"
    exit 1
}
$blenderDir = Split-Path -Parent $blender
$py = Get-ChildItem (Join-Path $blenderDir "*\python\bin\python.exe") | Select-Object -First 1
if (-not $py) { Write-Host "Nu am gasit python.exe in $blenderDir"; exit 1 }
Write-Host "Blender: $blender"
Write-Host "Python:  $($py.FullName)"

# --- Sollumz ---
$extDir = Join-Path $tools "blender_ext\user_default"
$szDir = Join-Path $extDir "sollumz"
if (Test-Path (Join-Path $szDir "blender_manifest.toml")) {
    Write-Host "Sollumz: deja instalat in tools\blender_ext"
} else {
    New-Item -ItemType Directory -Force $extDir | Out-Null
    $zip = Join-Path $tools "Sollumz-$($sollumzVersion.TrimStart('v')).zip"
    if (-not (Test-Path $zip)) {
        $url = "https://github.com/Sollumz/Sollumz/releases/download/$sollumzVersion/Sollumz.zip"
        Write-Host "Descarc $url ..."
        Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
    }
    $tmp = Join-Path $tools "_sollumz_tmp"
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    Expand-Archive -Path $zip -DestinationPath $tmp -Force
    $inner = Get-ChildItem $tmp -Directory | Select-Object -First 1
    Move-Item $inner.FullName $szDir
    Remove-Item -Recurse -Force $tmp
    Write-Host "Sollumz: instalat in $szDir"
}

# --- szio + pymateria ---
$pydeps = Join-Path $tools "pydeps"
$ok = (Test-Path (Join-Path $pydeps "szio")) -and (Test-Path (Join-Path $pydeps "pymateria"))
if ($ok) {
    Write-Host "szio + pymateria: deja instalate in tools\pydeps"
} else {
    Write-Host "Instalez szio==$szioVersion si pymateria==$pymateriaVersion (pip, ~10 MB)..."
    & $py.FullName -m pip install --target $pydeps --no-deps --upgrade `
        --extra-index-url https://static.cfx.re/whl/ "szio==$szioVersion" "pymateria==$pymateriaVersion"
    if ($LASTEXITCODE -ne 0) { Write-Host "pip a esuat"; exit 1 }
}
New-Item -ItemType Directory -Force (Join-Path $tools "blender_config") | Out-Null
Write-Host ""
Write-Host "GATA. Acum ruleaza GENEREAZA_DEMO.bat"
