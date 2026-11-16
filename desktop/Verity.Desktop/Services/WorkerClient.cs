using System.Net.Http;
using System.Net.Http.Json;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Verity.Contracts;

namespace Verity.Desktop.Services;

public sealed class WorkerClient : IAsyncDisposable
{
    private readonly HttpClient _http;
    private readonly string _token;
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web) { Converters = { new JsonStringEnumConverter() } };
    public Uri BaseUri { get; }

    public WorkerClient(int port, string token)
    {
        _token = token;
        BaseUri = new Uri($"http://127.0.0.1:{port}/");
        _http = new HttpClient { BaseAddress = BaseUri, Timeout = TimeSpan.FromSeconds(20) };
        _http.DefaultRequestHeaders.Add("X-Verity-Token", token);
    }

    public Task<HealthResponse?> HealthAsync(CancellationToken ct = default) => _http.GetFromJsonAsync<HealthResponse>("health", ct);
    public Task<IReadOnlyList<PersonSummary>?> PeopleAsync(CancellationToken ct = default) => _http.GetFromJsonAsync<IReadOnlyList<PersonSummary>>("people", ct);
    public Task<IReadOnlyList<RecognitionEvent>?> EventsAsync(CancellationToken ct = default) => _http.GetFromJsonAsync<IReadOnlyList<RecognitionEvent>>("events?limit=100", JsonOptions, ct);
    public async Task DeleteEventAsync(string id,CancellationToken ct=default)
    { using var response=await _http.DeleteAsync($"events/{Uri.EscapeDataString(id)}",ct); response.EnsureSuccessStatusCode(); }
    public Task<MonitorStatusResponse?> MonitorStatusAsync(CancellationToken ct = default) => _http.GetFromJsonAsync<MonitorStatusResponse>("monitor/status", ct);
    public Task<MonitorCalibration?> CalibrationAsync(CancellationToken ct = default) => _http.GetFromJsonAsync<MonitorCalibration>("monitor/calibration",JsonOptions,ct);
    public async Task SaveCalibrationAsync(MonitorCalibration calibration,CancellationToken ct=default)
    {
        using var response=await _http.PutAsync("monitor/calibration",JsonContent.Create(calibration,options:JsonOptions),ct); response.EnsureSuccessStatusCode();
    }

    public async Task StartMonitorAsync(CameraConfiguration camera, CancellationToken ct = default)
    {
        using var response = await _http.PostAsync("monitor/start", JsonContent.Create(new MonitorStartRequest(camera), options: JsonOptions), ct);
        response.EnsureSuccessStatusCode();
    }
    public async Task<EncodeImageResponse?> EncodeImageAsync(string imageBase64, CancellationToken ct = default)
    {
        using var response = await _http.PostAsync("faces/encode-image", JsonContent.Create(new { imageBase64 }, options: JsonOptions), ct);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<EncodeImageResponse>(JsonOptions, ct);
    }
    public async Task RegisterPersonAsync(RegisterPersonRequest request, CancellationToken ct = default)
    {
        using var response = await _http.PostAsync("people", JsonContent.Create(request, options: JsonOptions), ct);
        response.EnsureSuccessStatusCode();
    }
    public async Task DeletePersonAsync(string id, CancellationToken ct = default)
    {
        using var response = await _http.DeleteAsync($"people/{Uri.EscapeDataString(id)}", ct);
        response.EnsureSuccessStatusCode();
    }
    public async Task UpdatePersonAsync(string id, string name, string employeeId, CancellationToken ct = default)
    {
        using var request = new HttpRequestMessage(HttpMethod.Patch, $"people/{Uri.EscapeDataString(id)}") { Content = JsonContent.Create(new { name, employeeId }, options: JsonOptions) };
        using var response = await _http.SendAsync(request, ct); response.EnsureSuccessStatusCode();
    }
    public async Task ReplacePersonFaceAsync(string id, RegisterPersonRequest request, CancellationToken ct = default)
    {
        using var response = await _http.PutAsync($"people/{Uri.EscapeDataString(id)}/face",JsonContent.Create(request,options:JsonOptions),ct);
        response.EnsureSuccessStatusCode();
    }
    public async Task<EnrollmentStatus?> StartEnrollmentAsync(string name, string employeeId, int deviceIndex, bool consent, string? personId = null, CancellationToken ct = default)
    {
        using var response = await _http.PostAsync("enrollment/start", JsonContent.Create(new { name, employeeId, deviceIndex, consent, personId }, options: JsonOptions), ct);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<EnrollmentStatus>(JsonOptions, ct);
    }
    public Task<EnrollmentStatus?> EnrollmentStatusAsync(CancellationToken ct = default) => _http.GetFromJsonAsync<EnrollmentStatus>("enrollment/status", JsonOptions, ct);
    public async Task CancelEnrollmentAsync(CancellationToken ct = default) { using var response = await _http.PostAsync("enrollment/cancel", null, ct); response.EnsureSuccessStatusCode(); }
    public async Task StopMonitorAsync(CancellationToken ct = default)
    {
        using var response = await _http.PostAsync("monitor/stop", null, ct);
        response.EnsureSuccessStatusCode();
    }
    public async Task LoadModelsAsync(string provider = "CPU", CancellationToken ct = default)
    {
        using var response = await _http.PostAsync($"models/load?provider={Uri.EscapeDataString(provider)}", null, ct);
        response.EnsureSuccessStatusCode();
    }

    public async IAsyncEnumerable<RecognitionEvent> StreamEventsAsync([System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken ct)
    {
        using var socket = new ClientWebSocket();
        socket.Options.SetRequestHeader("X-Verity-Token", _token);
        await socket.ConnectAsync(new Uri(BaseUri.ToString().Replace("http://", "ws://") + "monitor/events"), ct);
        var buffer = new byte[64 * 1024];
        while (!ct.IsCancellationRequested && socket.State == WebSocketState.Open)
        {
            var result = await socket.ReceiveAsync(buffer, ct);
            if (result.MessageType == WebSocketMessageType.Close) break;
            var json = Encoding.UTF8.GetString(buffer, 0, result.Count);
            if (json.Contains("\"type\":\"heartbeat\"")) continue;
            var item = JsonSerializer.Deserialize<RecognitionEvent>(json, JsonOptions);
            if (item is not null) yield return item;
        }
    }

    public ValueTask DisposeAsync() { _http.Dispose(); return ValueTask.CompletedTask; }
}
