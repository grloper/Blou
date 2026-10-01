$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot '..')
try {
    python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
    python -m PyInstaller --noconfirm --clean --onefile --windowed --name Blou-Local --paths src scripts/blou_desktop.py
    if ($LASTEXITCODE -ne 0) { throw 'Packaging failed' }
    Get-FileHash -Algorithm SHA256 -LiteralPath dist/Blou-Local.exe | Format-List
} finally { Pop-Location }
