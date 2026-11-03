using Microsoft.Win32;
using System.Collections.ObjectModel;
using System.IO;
using System.Media;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Verity.Contracts;
using Verity.Desktop.Infrastructure;
using Verity.Desktop.Services;

namespace Verity.Desktop.ViewModels;

public sealed class MainViewModel : ObservableObject, IAsyncDisposable
{
    private readonly WorkerSupervisor _supervisor;
    private WorkerClient? _client;
    private CancellationTokenSource? _eventsCts;
    private CancellationTokenSource? _previewCts;
    private string _page = "Dashboard", _status = "Starting recognition worker…", _name = "", _employeeId = "", _selectedImage = "", _rtspUrl = "", _activeProcessor = "CPU";
    private bool _workerOnline, _modelLoaded, _databaseReady, _monitoring, _useRtsp, _consent;
    private RecognitionEvent? _latestEvent;
    private bool _enrollmentActive;
    private string _enrollmentPose = "center", _enrollmentInstruction = "Position your face inside the guide";
    private int _enrollmentCaptured;
    private ImageSource? _enrollmentPreview;
    private bool _displayMonitor;
    private ImageSource? _monitorPreview;
    private string? _editingPersonId;

    public ObservableCollection<PersonSummary> People { get; } = [];
    public ObservableCollection<RecognitionEvent> Events { get; } = [];
    public string Page { get => _page; set => Set(ref _page, value); }
    public string Status { get => _status; set => Set(ref _status, value); }
    public string Name { get => _name; set => Set(ref _name, value); }
    public string EmployeeId { get => _employeeId; set => Set(ref _employeeId, value); }
    public string SelectedImage { get => _selectedImage; set => Set(ref _selectedImage, value); }
    public string RtspUrl { get => _rtspUrl; set => Set(ref _rtspUrl, value); }
    public bool WorkerOnline { get => _workerOnline; set => Set(ref _workerOnline, value); }
    public bool ModelLoaded { get => _modelLoaded; set => Set(ref _modelLoaded, value); }
    public bool DatabaseReady { get => _databaseReady; set => Set(ref _databaseReady, value); }
    public bool Monitoring
    {
        get => _monitoring;
        set
        {
            if (!Set(ref _monitoring, value)) return;
            (StartMonitorCommand as AsyncCommand)?.Refresh();
            (StopMonitorCommand as AsyncCommand)?.Refresh();
        }
    }
    public bool UseRtsp { get => _useRtsp; set => Set(ref _useRtsp, value); }
    public bool Consent { get => _consent; set => Set(ref _consent, value); }
    public RecognitionEvent? LatestEvent { get => _latestEvent; set => Set(ref _latestEvent, value); }
    public bool EnrollmentActive { get => _enrollmentActive; set => Set(ref _enrollmentActive, value); }
    public string EnrollmentPose { get => _enrollmentPose; set { if (Set(ref _enrollmentPose, value)) Raise(nameof(EnrollmentArrow)); } }
    public string EnrollmentInstruction { get => _enrollmentInstruction; set => Set(ref _enrollmentInstruction, value); }
    public int EnrollmentCaptured { get => _enrollmentCaptured; set { if (Set(ref _enrollmentCaptured, value)) Raise(nameof(EnrollmentProgress)); } }
    public double EnrollmentProgress => EnrollmentCaptured * (100d / 3d);
    public string EnrollmentArrow => EnrollmentPose.ToLowerInvariant() switch { "left" => "←", "right" => "→", _ => "◎" };
    public ImageSource? EnrollmentPreview { get => _enrollmentPreview; set => Set(ref _enrollmentPreview, value); }
    public bool DisplayMonitor { get => _displayMonitor; set { if (Set(ref _displayMonitor, value)) Raise(nameof(DisplayButtonText)); } }
    public string DisplayButtonText => DisplayMonitor ? "Hide display" : "Display camera";
    public ImageSource? MonitorPreview { get => _monitorPreview; set => Set(ref _monitorPreview, value); }
    public string ActiveProcessor { get => _activeProcessor; set => Set(ref _activeProcessor, value); }

    public ICommand NavigateCommand { get; }
    public ICommand BrowseImageCommand { get; }
    public ICommand RegisterCommand { get; }
    public ICommand GuidedEnrollmentCommand { get; }
    public ICommand StartMonitorCommand { get; }
    public ICommand StopMonitorCommand { get; }
    public ICommand ToggleDisplayCommand { get; }
    public ICommand UseCpuCommand { get; }
    public ICommand UseGpuCommand { get; }
    public ICommand RefreshCommand { get; }
    public ICommand EditPersonCommand { get; }
    public ICommand RetakePersonCommand { get; }
    public ICommand DeletePersonCommand { get; }
    public ICommand SavePersonCommand { get; }

    public MainViewModel(WorkerSupervisor supervisor)
    {
        _supervisor = supervisor;
        NavigateCommand = new RelayCommand(p => Page = p?.ToString() ?? "Dashboard");
        BrowseImageCommand = new RelayCommand(_ => BrowseImage());
        RegisterCommand = new AsyncCommand(RegisterAsync);
        GuidedEnrollmentCommand = new AsyncCommand(GuidedEnrollmentAsync);
        StartMonitorCommand = new AsyncCommand(StartMonitorAsync, () => !Monitoring);
        StopMonitorCommand = new AsyncCommand(StopMonitorAsync, () => Monitoring);
        ToggleDisplayCommand = new RelayCommand(_ => ToggleDisplay());
        UseCpuCommand = new AsyncCommand(() => SetProcessorAsync("CPU"));
        UseGpuCommand = new AsyncCommand(() => SetProcessorAsync("GPU"));
        RefreshCommand = new AsyncCommand(RefreshAsync);
        EditPersonCommand = new RelayCommand(p => BeginEdit(p as PersonSummary));
        RetakePersonCommand = new RelayCommand(p => BeginRetake(p as PersonSummary));
        DeletePersonCommand = new RelayCommand(p => _ = DeletePersonAsync(p as PersonSummary));
        SavePersonCommand = new RelayCommand(_ => _ = SavePersonAsync());
    }

    public async Task InitializeAsync()
    {
        try
        {
            _client = await _supervisor.StartAsync(); WorkerOnline = true;
            await _client.LoadModelsAsync("CPU"); ActiveProcessor = "CPU"; await RefreshAsync();
            _eventsCts = new CancellationTokenSource(); _ = ListenAsync(_eventsCts.Token);
            Status = "System ready";
        }
        catch (Exception ex) { Status = ex.Message; WorkerOnline = false; }
    }

    private async Task RefreshAsync()
    {
        if (_client is null) return;
        try
        {
            var health = await _client.HealthAsync(); WorkerOnline = health?.Status == "ok"; ModelLoaded = health?.ModelLoaded == true; DatabaseReady = health?.DatabaseReady == true;
            Replace(People, await _client.PeopleAsync() ?? []); Replace(Events, await _client.EventsAsync() ?? []);
            var monitor = await _client.MonitorStatusAsync(); Monitoring = monitor?.Running == true; Status = monitor?.Error ?? (Monitoring ? "Continuous monitoring active" : "System ready");
        }
        catch (Exception ex) { Status = ex.Message; WorkerOnline = false; }
    }

    private void BrowseImage()
    {
        var dialog = new OpenFileDialog { Filter = "Face images|*.jpg;*.jpeg;*.png", CheckFileExists = true };
        if (dialog.ShowDialog() == true) SelectedImage = dialog.FileName;
    }

    private async Task RegisterAsync()
    {
        if (_client is null || string.IsNullOrWhiteSpace(Name) || string.IsNullOrWhiteSpace(EmployeeId) || !File.Exists(SelectedImage) || !Consent) { Status = "Name, employee ID, consent, and a face image are required."; return; }
        try
        {
            var bytes = await File.ReadAllBytesAsync(SelectedImage); var data = $"data:image/{Path.GetExtension(SelectedImage).Trim('.').Replace("jpg", "jpeg")};base64,{Convert.ToBase64String(bytes)}";
            var encoded = await _client.EncodeImageAsync(data); if (encoded is not { Valid: true }) { Status = encoded?.Message ?? "Image validation failed"; return; }
            var request=new RegisterPersonRequest(Name.Trim(), EmployeeId.Trim(), data, [encoded.Embedding], true);
            if (_editingPersonId is not null) await _client.ReplacePersonFaceAsync(_editingPersonId,request);
            else await _client.RegisterPersonAsync(request);
            Name = EmployeeId = SelectedImage = ""; Consent = false; _editingPersonId=null; Status = "Employee saved successfully"; await RefreshAsync(); Page = "People";
        }
        catch (Exception ex) { Status = $"Registration failed: {ex.Message}"; }
    }

    private void BeginEdit(PersonSummary? person)
    {
        if (person is null) return;
        Name=person.Name; EmployeeId=person.EmployeeId; SelectedImage=""; Consent=true; _editingPersonId=person.Id; Page="Register";
        Status="Edit the employee details, or choose guided capture to retake the face.";
    }

    private void BeginRetake(PersonSummary? person)
    {
        if (person is null) return;
        Name=person.Name; EmployeeId=person.EmployeeId; SelectedImage=""; Consent=true; _editingPersonId=person.Id; Page="Register";
        Status="Ready to retake face. Start guided three-pose capture.";
    }

    private async Task DeletePersonAsync(PersonSummary? person)
    {
        if (_client is null || person is null) return;
        if (MessageBox.Show($"Delete {person.Name} and all saved face templates? This cannot be undone.","Delete person",MessageBoxButton.YesNo,MessageBoxImage.Warning)!=MessageBoxResult.Yes) return;
        try { await _client.DeletePersonAsync(person.Id); Status=$"{person.Name} deleted"; await RefreshAsync(); }
        catch(Exception ex) { Status=$"Delete failed: {ex.Message}"; }
    }

    private async Task SavePersonAsync()
    {
        if (_client is null || _editingPersonId is null) { Status="Choose Edit on an existing person first."; return; }
        if (string.IsNullOrWhiteSpace(Name)||string.IsNullOrWhiteSpace(EmployeeId)) { Status="Name and employee ID are required."; return; }
        try { await _client.UpdatePersonAsync(_editingPersonId,Name.Trim(),EmployeeId.Trim()); Name=EmployeeId=""; Consent=false; _editingPersonId=null; Status="Employee details updated"; await RefreshAsync(); Page="People"; }
        catch(Exception ex) { Status=$"Update failed: {ex.Message}"; }
    }

    private async Task StartMonitorAsync()
    {
        if (_client is null) return;
        try
        {
            var camera = new CameraConfiguration(UseRtsp ? CameraSourceType.Rtsp : CameraSourceType.Webcam, 0, UseRtsp ? RtspUrl : null, 1280, 720, 5, 3);
            await _client.StartMonitorAsync(camera); Monitoring = true; Status = "Continuous monitoring active"; Page = "Live Monitor";
            if (DisplayMonitor) StartPreviewLoop();
        }
        catch (Exception ex) { Status = $"Camera failed: {ex.Message}"; }
    }

    private async Task GuidedEnrollmentAsync()
    {
        if (_client is null || string.IsNullOrWhiteSpace(Name) || string.IsNullOrWhiteSpace(EmployeeId) || !Consent) { Status = "Name, employee ID, and biometric consent are required."; return; }
        try
        {
            EnrollmentActive = true; EnrollmentCaptured = 0; EnrollmentPose = "center"; EnrollmentInstruction = "Look straight at the camera"; EnrollmentPreview = null;
            if (_editingPersonId is not null) await _client.UpdatePersonAsync(_editingPersonId,Name.Trim(),EmployeeId.Trim());
            await _client.StartEnrollmentAsync(Name.Trim(), EmployeeId.Trim(), 0, true, _editingPersonId);
            while (true)
            {
                await Task.Delay(200); var state = await _client.EnrollmentStatusAsync(); if (state is null) break;
                EnrollmentPose = state.Pose; EnrollmentInstruction = state.Message;
                if (state.Captured > EnrollmentCaptured) SystemSounds.Asterisk.Play();
                EnrollmentCaptured = state.Captured;
                if (!string.IsNullOrWhiteSpace(state.PreviewImage)) EnrollmentPreview = DecodeImage(state.PreviewImage);
                Status = $"Guided enrollment: {state.Message} ({state.Captured}/3)";
                if (!state.Running)
                {
                    if (state.Complete) { Name = EmployeeId = ""; Consent = false; _editingPersonId=null; await RefreshAsync(); Page = "People"; }
                    else Status = $"Enrollment failed: {state.Error}";
                    break;
                }
            }
        }
        catch (Exception ex) { Status = $"Enrollment failed: {ex.Message}"; }
        finally { EnrollmentActive = false; }
    }

    private static ImageSource DecodeImage(string dataUrl)
    {
        var bytes = Convert.FromBase64String(dataUrl[(dataUrl.IndexOf(',') + 1)..]);
        using var stream = new MemoryStream(bytes);
        var image = new BitmapImage(); image.BeginInit(); image.CacheOption = BitmapCacheOption.OnLoad; image.StreamSource = stream; image.EndInit(); image.Freeze(); return image;
    }

    private async Task StopMonitorAsync() { if (_client is null) return; await _client.StopMonitorAsync(); Monitoring = false; DisplayMonitor = false; _previewCts?.Cancel(); MonitorPreview = null; Status = "Monitoring stopped"; }
    private void ToggleDisplay()
    {
        if (!Monitoring) { Status = "Start monitoring before opening the camera display."; return; }
        DisplayMonitor = !DisplayMonitor;
        if (DisplayMonitor) StartPreviewLoop();
        else { _previewCts?.Cancel(); MonitorPreview = null; }
    }
    private async Task SetProcessorAsync(string processor)
    {
        if (_client is null) return;
        if (Monitoring || EnrollmentActive) { Status = "Stop monitoring or enrollment before changing processor."; return; }
        try
        {
            Status = $"Loading models on {processor}…";
            await _client.LoadModelsAsync(processor);
            ActiveProcessor = processor;
            Status = $"Recognition is using {processor}";
        }
        catch (Exception ex) { Status = $"Could not use {processor}: {ex.Message}"; }
    }
    private void StartPreviewLoop()
    {
        _previewCts?.Cancel(); _previewCts = new CancellationTokenSource(); _ = PreviewLoopAsync(_previewCts.Token);
    }
    private async Task PreviewLoopAsync(CancellationToken ct)
    {
        if (_client is null) return;
        try
        {
            while (!ct.IsCancellationRequested && DisplayMonitor)
            {
                var state=await _client.MonitorStatusAsync(ct);
                if (!string.IsNullOrWhiteSpace(state?.PreviewImage)) MonitorPreview=DecodeImage(state.PreviewImage);
                await Task.Delay(200,ct);
            }
        }
        catch (OperationCanceledException) { }
        catch (Exception ex) { Status=$"Display unavailable: {ex.Message}"; }
    }
    private async Task ListenAsync(CancellationToken ct)
    {
        if (_client is null) return;
        try
        {
            await foreach (var item in _client.StreamEventsAsync(ct))
                await Application.Current.Dispatcher.InvokeAsync(() => { LatestEvent = item; Events.Insert(0, item); while (Events.Count > 100) Events.RemoveAt(Events.Count - 1); if (item.Result == RecognitionResultType.Unknown) SystemSounds.Exclamation.Play(); });
        }
        catch when (ct.IsCancellationRequested) { }
        catch (Exception ex) { Status = $"Event stream disconnected: {ex.Message}"; }
    }

    private static void Replace<T>(ObservableCollection<T> target, IEnumerable<T> source) { target.Clear(); foreach (var item in source) target.Add(item); }
    public async ValueTask DisposeAsync() { _eventsCts?.Cancel(); _eventsCts?.Dispose(); _previewCts?.Cancel(); _previewCts?.Dispose(); await _supervisor.DisposeAsync(); }
}

public sealed class RelayCommand(Action<object?> action, Func<object?, bool>? canExecute = null) : ICommand
{
    public event EventHandler? CanExecuteChanged { add { } remove { } }
    public bool CanExecute(object? parameter) => canExecute?.Invoke(parameter) ?? true;
    public void Execute(object? parameter) => action(parameter);
}
