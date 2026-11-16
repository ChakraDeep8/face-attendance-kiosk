using System.Text.Json;
using System.Text.Json.Serialization;
using Verity.Contracts;
using Xunit;

namespace Verity.Desktop.Tests;

public class RecognitionEventJsonTests
{
    [Fact]
    public void WorkerStringResultDeserializesToEnum()
    {
        const string json="[{\"id\":\"1\",\"result\":\"Unknown\",\"personId\":null,\"displayName\":\"Unknown person\",\"confidence\":28.3,\"timestamp\":\"2026-11-03T10:00:00+00:00\",\"camera\":\"Webcam\",\"snapshotPath\":null}]";
        var options=new JsonSerializerOptions(JsonSerializerDefaults.Web); options.Converters.Add(new JsonStringEnumConverter());
        var events=JsonSerializer.Deserialize<IReadOnlyList<RecognitionEvent>>(json,options);
        Assert.Equal(RecognitionResultType.Unknown,events![0].Result);
    }

    [Fact]
    public void EvidenceImageIsDeserializedForCrossingEvent()
    {
        const string json="[{\"id\":\"2\",\"result\":\"Unknown\",\"personId\":null,\"displayName\":\"Unauthorized access\",\"confidence\":31.2,\"timestamp\":\"2026-11-03T10:00:00+00:00\",\"camera\":\"RTSP\",\"snapshotPath\":\"evidence.jpg\",\"imageData\":\"data:image/jpeg;base64,AA==\"}]";
        var options=new JsonSerializerOptions(JsonSerializerDefaults.Web); options.Converters.Add(new JsonStringEnumConverter());
        var events=JsonSerializer.Deserialize<IReadOnlyList<RecognitionEvent>>(json,options);
        Assert.Equal("Unauthorized access",events![0].DisplayName);
        Assert.StartsWith("data:image/jpeg",events[0].ImageData);
    }
}
