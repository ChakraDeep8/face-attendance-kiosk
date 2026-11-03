$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venv = Join-Path $root '.venv'
if (-not (Test-Path $venv)) { py -3.11 -m venv $venv }
& "$venv\Scripts\python.exe" -m pip install --upgrade pip
& "$venv\Scripts\pip.exe" install -r "$root\requirements.txt"
Push-Location $root
try {
    & "$venv\Scripts\python.exe" download-models.py
    & "$venv\Scripts\pyinstaller.exe" --clean --noconfirm verity-worker.spec
}
finally { Pop-Location }
