using System.Globalization;
using System.Windows.Data;

namespace Verity.Desktop;

/// <summary>Formats stored UTC timestamps for the India deployment without changing persisted values.</summary>
public sealed class IndiaTimeConverter : IValueConverter
{
    private static readonly TimeZoneInfo India = TimeZoneInfo.FindSystemTimeZoneById("India Standard Time");

    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is DateTimeOffset timestamp)
        {
            var india = TimeZoneInfo.ConvertTime(timestamp, India);
            return india.ToString("dd MMM yyyy, hh:mm:ss tt", CultureInfo.InvariantCulture) + " IST";
        }
        return value?.ToString() ?? string.Empty;
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture) => throw new NotSupportedException();
}
