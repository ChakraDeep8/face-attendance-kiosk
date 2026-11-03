# Verity Windows Experiment

The Windows application is a .NET 8 WPF administrator and monitoring shell backed by a bundled Python recognition worker.

## Development

```powershell
cd desktop\worker
py -3.11 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
$env:VERITY_PYTHON = (Resolve-Path .\.venv\Scripts\python.exe)
cd ..\..
dotnet run --project desktop\Verity.Desktop
```

Data is written to `%LOCALAPPDATA%\Verity`: SQLite database, registered images, and unknown-person snapshots.

## Build installer

```powershell
.\desktop\publish.ps1
```

This packages the Python worker with PyInstaller, publishes a self-contained `win-x64` WPF app, and builds the WiX installer.

The final one-click installer is written to `desktop\artifacts\VeritySetup.exe`. It contains the self-contained Windows application, Python worker, native runtime, and recognition models.

## Models and licensing

The default `buffalo_s` InsightFace model is intended for this experiment. Review and replace model weights with production-approved, commercially licensed weights before production deployment.
