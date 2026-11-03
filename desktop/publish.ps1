$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$artifacts = Join-Path $root 'artifacts'
& (Join-Path $root 'worker\build-worker.ps1')
dotnet publish (Join-Path $root 'Verity.Desktop\Verity.Desktop.csproj') -c Release -r win-x64 --self-contained true -p:PublishSingleFile=false -o (Join-Path $artifacts 'publish')
$workerOut = Join-Path $root 'worker\dist\verity-worker.exe'
Copy-Item $workerOut (Join-Path $artifacts 'publish\worker\verity-worker.exe') -Force
dotnet build (Join-Path $root 'Verity.Installer\Verity.Installer.wixproj') -c Release
dotnet build (Join-Path $root 'Verity.Bootstrapper\Verity.Bootstrapper.wixproj') -c Release
Copy-Item (Join-Path $root 'Verity.Bootstrapper\bin\Release\VeritySetup.exe') (Join-Path $artifacts 'VeritySetup.exe') -Force
