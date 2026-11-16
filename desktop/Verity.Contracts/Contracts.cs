using System.Text.Json.Serialization;

namespace Verity.Contracts;

public enum CameraSourceType { Webcam, Rtsp }
public enum RecognitionResultType { Authorized, Unknown, Duplicate }

public sealed record HealthResponse(
    string Status,
    bool ModelLoaded,
    bool DatabaseReady,
    string Version,
    DateTimeOffset Time);

public sealed record PersonSummary(
    string Id,
    string Name,
    string EmployeeId,
    DateTimeOffset CreatedAt,
    int TemplateCount,
    bool Active,
    string? ImageData);

public sealed record RecognitionEvent(
    string Id,
    RecognitionResultType Result,
    string? PersonId,
    string DisplayName,
    double Confidence,
    DateTimeOffset Timestamp,
    string Camera,
    string? SnapshotPath,
    string? ImageData);

public sealed record CalibrationRectangle(double X1,double Y1,double X2,double Y2);
public sealed record CalibrationLine(double X1,double Y1,double X2,double Y2);
public sealed record MonitorCalibration(CalibrationRectangle Zone,CalibrationLine Line);

public sealed record CameraConfiguration(
    CameraSourceType SourceType,
    int DeviceIndex,
    string? RtspUrl,
    int Width,
    int Height,
    int RecognitionFps,
    int ReconnectSeconds);

public sealed record RecognitionSettings(
    double MatchThreshold,
    int AttendanceCooldownMinutes,
    int AlertCooldownSeconds,
    int SnapshotRetentionDays,
    string ModelName);

public sealed record MonitorStartRequest(CameraConfiguration Camera);
public sealed record MonitorStatusResponse(bool Running, string State, string Camera, double Fps, string? Error, string? PreviewImage);
public sealed record EncodeImageResponse(bool Valid, string Message, int FaceCount, double Quality, IReadOnlyList<float> Embedding);
public sealed record RegisterPersonRequest(string Name, string EmployeeId, string ImageBase64, IReadOnlyList<IReadOnlyList<float>> Embeddings, bool Consent);
public sealed record EnrollmentStatus(bool Running, string Pose, int Captured, string Message, bool Complete, string? Error, string? PersonId, string? PreviewImage);
public sealed record ApiError([property: JsonPropertyName("detail")] string Detail);
