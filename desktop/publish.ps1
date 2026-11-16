[CmdletBinding()]
param(
    [string]$CertificateThumbprint,
    [string]$TimestampUrl = 'http://timestamp.digicert.com',
    [switch]$RequireSigning
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$artifacts = Join-Path $root 'artifacts'
$publishDir = Join-Path $artifacts 'publish'
$signScript = Join-Path $root 'sign-artifacts.ps1'

if ($RequireSigning -and -not $CertificateThumbprint) {
    throw 'A certificate thumbprint is required when -RequireSigning is used.'
}

if ($CertificateThumbprint) {
    $signingCertificate = Get-ChildItem 'Cert:\CurrentUser\My', 'Cert:\LocalMachine\My' -CodeSigningCert -ErrorAction SilentlyContinue |
        Where-Object { $_.Thumbprint -eq $CertificateThumbprint -and $_.HasPrivateKey } |
        Select-Object -First 1
    if (-not $signingCertificate) {
        throw "The code-signing certificate '$CertificateThumbprint' was not found with an accessible private key. Run Get-ChildItem Cert:\CurrentUser\My, Cert:\LocalMachine\My -CodeSigningCert and use a thumbprint displayed by that command."
    }
    Write-Host "Using code-signing certificate: $($signingCertificate.Subject)"
}

& (Join-Path $root 'worker\build-worker.ps1')
dotnet publish (Join-Path $root 'Verity.Desktop\Verity.Desktop.csproj') -c Release -r win-x64 --self-contained true -p:PublishSingleFile=false -o $publishDir
$workerOut = Join-Path $root 'worker\dist\verity-worker.exe'
Copy-Item $workerOut (Join-Path $publishDir 'worker\verity-worker.exe') -Force

if ($CertificateThumbprint) {
    & $signScript -Path $publishDir -CertificateThumbprint $CertificateThumbprint -TimestampUrl $TimestampUrl
}
elseif (-not $RequireSigning) {
    Write-Warning 'Unsigned developer build created. Windows Application Control may block it. Use -RequireSigning with an approved certificate for release builds.'
}

dotnet build (Join-Path $root 'Verity.Installer\Verity.Installer.wixproj') -c Release

$msi = Join-Path $root 'Verity.Installer\bin\Release\VeritySetup.msi'
if ($CertificateThumbprint) {
    & $signScript -Path $msi -CertificateThumbprint $CertificateThumbprint -TimestampUrl $TimestampUrl -IncludeMsi
}

dotnet build (Join-Path $root 'Verity.Bootstrapper\Verity.Bootstrapper.wixproj') -c Release
$setupSource = Join-Path $root 'Verity.Bootstrapper\bin\Release\VeritySetup.exe'
if ($CertificateThumbprint) {
    & $signScript -Path $setupSource -CertificateThumbprint $CertificateThumbprint -TimestampUrl $TimestampUrl
}
Copy-Item $setupSource (Join-Path $artifacts 'VeritySetup.exe') -Force

if ($RequireSigning) {
    $invalid = Get-ChildItem $publishDir -Recurse -File -Include *.exe,*.dll |
        Where-Object { (Get-AuthenticodeSignature -LiteralPath $_.FullName).Status -ne 'Valid' }
    if ($invalid) {
        $names = $invalid.FullName -join [Environment]::NewLine
        throw "Release verification found unsigned or invalid binaries:$([Environment]::NewLine)$names"
    }
    Write-Host 'Signed release build completed and verified.'
}
