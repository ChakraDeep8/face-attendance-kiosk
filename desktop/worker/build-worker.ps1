$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venv = Join-Path $root '.venv'
if (-not (Test-Path $venv)) { py -3.11 -m venv $venv }
$python = Join-Path $venv 'Scripts\python.exe'

function Invoke-WorkerPython {
    & $python @args
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code ${LASTEXITCODE}: python $($args -join ' ')"
    }
}

Invoke-WorkerPython -m pip install --disable-pip-version-check -r "$root\requirements.txt"
Push-Location $root
try {
    $modelFile = Join-Path $root 'models\models\buffalo_s\w600k_mbf.onnx'
    if (-not (Test-Path $modelFile)) {
        Invoke-WorkerPython download-models.py
    }
    else {
        Write-Host 'Existing InsightFace model bundle found; skipping model download.'
    }
    Invoke-WorkerPython -m PyInstaller --clean --noconfirm verity-worker.spec
}
finally { Pop-Location }
