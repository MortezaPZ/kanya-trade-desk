$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Create the project virtual environment before building the Windows app."
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$distRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "dist"))
$guiDist = Join-Path $distRoot "gui-build"
$serverDist = Join-Path $distRoot "server-build"
$guiBuild = Join-Path $guiDist "KanyaTradeDesk"
$serverBuild = Join-Path $serverDist "KanyaTradeDeskServer"
$releaseName = "KanyaTradeDesk_$stamp"
$releaseDir = Join-Path $distRoot $releaseName
$zipPath = Join-Path $distRoot ($releaseName + ".zip")

foreach ($path in @($guiDist, $serverDist)) {
    $resolved = [System.IO.Path]::GetFullPath($path)
    if (-not $resolved.StartsWith(($distRoot.TrimEnd('\') + '\'), [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Build output escaped the dist directory."
    }
    if (Test-Path -LiteralPath $resolved) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}

& $python -m PyInstaller `
    --clean `
    --noconfirm `
    --onedir `
    --windowed `
    --name KanyaTradeDesk `
    --distpath $guiDist `
    --workpath (Join-Path $PSScriptRoot "build\gui") `
    launcher.py
if ($LASTEXITCODE -ne 0) {
    throw "Windows launcher build failed with exit code $LASTEXITCODE."
}

& $python -m PyInstaller `
    --clean `
    --noconfirm `
    --onedir `
    --console `
    --name KanyaTradeDeskServer `
    --distpath $serverDist `
    --workpath (Join-Path $PSScriptRoot "build\server") `
    --add-data ".env.example;." `
    --add-data "app\static;app\static" `
    --hidden-import MetaTrader5 `
    --hidden-import MetaTrader5._core `
    --hidden-import numpy `
    --collect-all MetaTrader5 `
    server_entry.py
if ($LASTEXITCODE -ne 0) {
    throw "Windows server build failed with exit code $LASTEXITCODE."
}

New-Item -ItemType Directory -Path $releaseDir | Out-Null
$serverPackage = Join-Path $releaseDir "server"
New-Item -ItemType Directory -Path $serverPackage | Out-Null
Copy-Item -Path (Join-Path $guiBuild "*") -Destination $releaseDir -Recurse -Force
Copy-Item -Path (Join-Path $serverBuild "*") -Destination $serverPackage -Recurse -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot ".env.example") -Destination $releaseDir
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "docs\CLIENT.md") -Destination (Join-Path $releaseDir "راهنمای فارسی.txt")
Compress-Archive -Path (Join-Path $releaseDir "*") -DestinationPath $zipPath -CompressionLevel Optimal

Write-Output $zipPath
