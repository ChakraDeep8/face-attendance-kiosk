using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Security.Cryptography;

namespace Verity.Desktop.Services;

public sealed class WorkerSupervisor : IAsyncDisposable
{
    private Process? _process;
    private string? _pidFile;
    public WorkerClient? Client { get; private set; }
    public string? LastError { get; private set; }

    public async Task<WorkerClient> StartAsync(CancellationToken ct = default)
    {
        if (Client is not null) return Client;
        var port = FindAvailablePort();
        var token = Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
        var workerRoot = Path.Combine(AppContext.BaseDirectory, "worker");
        var packaged = Path.Combine(workerRoot, "verity-worker.exe");
        var python = Environment.GetEnvironmentVariable("VERITY_PYTHON") ?? "python";
        var usePackaged = File.Exists(packaged);
        var executable = usePackaged ? packaged : python;
        var arguments = usePackaged ? $"--port {port}" : $"-m app.main --port {port}";
        if (!usePackaged && TryFindDevelopmentWorker(out var developmentPython, out var developmentRoot))
        {
            executable = developmentPython;
            workerRoot = developmentRoot;
        }
        var dataRoot = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Verity");
        Directory.CreateDirectory(dataRoot);
        _pidFile = Path.Combine(dataRoot, "worker.pid");
        CleanupStaleWorker(_pidFile);
        var start = CreateStartInfo(executable, arguments, workerRoot, token, dataRoot);
        try
        {
            _process = Process.Start(start) ?? throw new InvalidOperationException("Unable to start recognition worker.");
        }
        catch when (usePackaged && TryFindDevelopmentWorker(out var fallbackPython, out var fallbackRoot))
        {
            LastError = "Packaged worker was blocked; using the local Python worker.";
            start = CreateStartInfo(fallbackPython, $"-m app.main --port {port}", fallbackRoot, token, dataRoot);
            _process = Process.Start(start) ?? throw new InvalidOperationException("Unable to start fallback recognition worker.");
        }
        SaveWorkerIdentity();
        _process.ErrorDataReceived += (_, e) => { if (!string.IsNullOrWhiteSpace(e.Data)) LastError = e.Data; };
        _process.BeginErrorReadLine();
        Client = new WorkerClient(port, token);
        for (var attempt = 0; attempt < 40; attempt++)
        {
            ct.ThrowIfCancellationRequested();
            if (_process.HasExited)
            {
                if (usePackaged && TryFindDevelopmentWorker(out var fallbackPython, out var fallbackRoot))
                {
                    _process.Dispose();
                    LastError = "Packaged worker failed; using the local Python worker.";
                    start = CreateStartInfo(fallbackPython, $"-m app.main --port {port}", fallbackRoot, token, dataRoot);
                    _process = Process.Start(start) ?? throw new InvalidOperationException("Unable to start fallback recognition worker.");
                    SaveWorkerIdentity();
                    _process.ErrorDataReceived += (_, e) => { if (!string.IsNullOrWhiteSpace(e.Data)) LastError = e.Data; };
                    _process.BeginErrorReadLine();
                    usePackaged = false;
                    attempt = 0;
                    continue;
                }
                throw new InvalidOperationException($"Recognition worker exited: {LastError}");
            }
            try { if ((await Client.HealthAsync(ct))?.Status == "ok") return Client; } catch { }
            await Task.Delay(250, ct);
        }
        throw new TimeoutException("Recognition worker did not become ready.");
    }

    private static ProcessStartInfo CreateStartInfo(string executable, string arguments, string workingDirectory, string token, string dataRoot)
    {
        var start = new ProcessStartInfo(executable, arguments)
        {
            WorkingDirectory = workingDirectory,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardError = true,
            RedirectStandardOutput = true
        };
        start.Environment["VERITY_TOKEN"] = token;
        start.Environment["VERITY_DATA_ROOT"] = dataRoot;
        return start;
    }

    private static bool TryFindDevelopmentWorker(out string python, out string workerRoot)
    {
        for (var directory = new DirectoryInfo(AppContext.BaseDirectory); directory is not null; directory = directory.Parent)
        {
            var candidateRoot = Path.Combine(directory.FullName, "worker");
            var candidatePython = Path.Combine(candidateRoot, ".venv", "Scripts", "python.exe");
            if (File.Exists(candidatePython) && File.Exists(Path.Combine(candidateRoot, "app", "main.py")))
            {
                python = candidatePython;
                workerRoot = candidateRoot;
                return true;
            }
        }
        python = workerRoot = string.Empty;
        return false;
    }

    private static int FindAvailablePort()
    {
        using var listener = new TcpListener(System.Net.IPAddress.Loopback, 0);
        listener.Start(); return ((System.Net.IPEndPoint)listener.LocalEndpoint).Port;
    }

    private void SaveWorkerIdentity()
    {
        if (_process is null || _pidFile is null) return;
        File.WriteAllText(_pidFile,$"{_process.Id}|{_process.StartTime.ToUniversalTime().Ticks}");
    }

    private static void CleanupStaleWorker(string pidFile)
    {
        try
        {
            if (!File.Exists(pidFile)) return;
            var parts=File.ReadAllText(pidFile).Split('|');
            if (parts.Length!=2 || !int.TryParse(parts[0],out var pid) || !long.TryParse(parts[1],out var ticks)) return;
            using var process=Process.GetProcessById(pid);
            var sameStart=Math.Abs(process.StartTime.ToUniversalTime().Ticks-ticks)<TimeSpan.TicksPerSecond;
            var expectedName=process.ProcessName.Equals("python",StringComparison.OrdinalIgnoreCase) || process.ProcessName.Equals("verity-worker",StringComparison.OrdinalIgnoreCase);
            if (sameStart && expectedName && !process.HasExited) { process.Kill(true); process.WaitForExit(5000); }
        }
        catch { }
        finally { try { File.Delete(pidFile); } catch { } }
    }

    public async ValueTask DisposeAsync()
    {
        if (Client is not null) { try { await Client.StopMonitorAsync(); } catch { } await Client.DisposeAsync(); }
        if (_process is { HasExited: false }) { _process.Kill(true); await _process.WaitForExitAsync(); }
        _process?.Dispose();
        if (_pidFile is not null) { try { File.Delete(_pidFile); } catch { } }
    }
}
