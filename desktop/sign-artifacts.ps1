[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Path,

    [Parameter(Mandatory = $true)]
    [string]$CertificateThumbprint,

    [string]$TimestampUrl = 'http://timestamp.digicert.com',

    [switch]$IncludeMsi
)

$ErrorActionPreference = 'Stop'

function Find-SignTool {
    $command = Get-Command 'signtool.exe' -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    $kitRoot = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin'
    if (Test-Path $kitRoot) {
        $candidate = Get-ChildItem $kitRoot -Recurse -Filter 'signtool.exe' -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($candidate) { return $candidate.FullName }
    }

    throw 'signtool.exe was not found. Install the Windows SDK Signing Tools component.'
}

$certificate = Get-ChildItem 'Cert:\CurrentUser\My', 'Cert:\LocalMachine\My' -CodeSigningCert -ErrorAction SilentlyContinue |
    Where-Object { $_.Thumbprint -eq $CertificateThumbprint -and $_.HasPrivateKey } |
    Select-Object -First 1

if (-not $certificate) {
    throw "A code-signing certificate with thumbprint '$CertificateThumbprint' and an accessible private key was not found."
}

$resolvedPath = (Resolve-Path -LiteralPath $Path).Path
$extensions = @('.exe', '.dll')
if ($IncludeMsi) { $extensions += '.msi' }

$files = if (Test-Path -LiteralPath $resolvedPath -PathType Leaf) {
    Get-Item -LiteralPath $resolvedPath
}
else {
    Get-ChildItem -LiteralPath $resolvedPath -Recurse -File |
        Where-Object { $extensions -contains $_.Extension.ToLowerInvariant() }
}

if (-not $files) { throw "No signable files were found under '$resolvedPath'." }

$signTool = Find-SignTool
foreach ($file in $files) {
    & $signTool sign /sha1 $CertificateThumbprint /fd SHA256 /tr $TimestampUrl /td SHA256 /v $file.FullName
    if ($LASTEXITCODE -ne 0) { throw "Signing failed for '$($file.FullName)'." }
}

foreach ($file in $files) {
    & $signTool verify /pa /all /v $file.FullName
    if ($LASTEXITCODE -ne 0) { throw "Signature verification failed for '$($file.FullName)'." }
}

Write-Host "Signed and verified $($files.Count) file(s) under '$resolvedPath'."
