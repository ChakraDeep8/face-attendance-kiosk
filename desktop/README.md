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

### Unsigned developer build

```powershell
.\desktop\publish.ps1
```

This packages the Python worker with PyInstaller, publishes a self-contained `win-x64` WPF app, and builds the WiX installer. It is intended only for machines that permit locally built unsigned applications.

### Signed release build for Windows Application Control

1. Obtain an organisation-approved Authenticode code-signing certificate. Its private key must be available in `Cert:\CurrentUser\My` or `Cert:\LocalMachine\My` on the build machine.
2. Ask the Windows administrator to add the certificate publisher to the organisation's Application Control policy. Signing alone does not override a policy that does not trust that publisher.
3. List the available signing certificates and copy the required thumbprint:

```powershell
Get-ChildItem Cert:\CurrentUser\My, Cert:\LocalMachine\My -CodeSigningCert |
    Select-Object Subject, Thumbprint, NotAfter, HasPrivateKey
```

4. Create a signed release:

```powershell
.\desktop\publish.ps1 `
    -RequireSigning `
    -CertificateThumbprint 'YOUR_CERTIFICATE_THUMBPRINT'
```

The release pipeline signs and verifies the published executables and DLLs before packaging, signs the MSI, and finally signs the bootstrapper. It stops immediately if a required signature is absent or invalid.

5. Confirm the final installer signature before distribution:

```powershell
Get-AuthenticodeSignature .\desktop\artifacts\VeritySetup.exe |
    Format-List Status, StatusMessage, SignerCertificate
```

The status must be `Valid`. If Application Control still blocks the validly signed release, the administrator must deploy the matching publisher allow-rule and refresh the policy.

The final one-click installer is written to `desktop\artifacts\VeritySetup.exe`. It contains the self-contained Windows application, Python worker, native runtime, and recognition models.

## Models and licensing

The default `buffalo_s` InsightFace model is intended for this experiment. Review and replace model weights with production-approved, commercially licensed weights before production deployment.
