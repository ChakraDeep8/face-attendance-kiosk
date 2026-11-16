using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
using System.Windows.Shapes;
using Verity.Desktop.ViewModels;

namespace Verity.Desktop;

/// <summary>
/// Interaction logic for MainWindow.xaml
/// </summary>
public partial class MainWindow : Window
{
    private Point? _calibrationStart;
    public MainWindow()
    {
        InitializeComponent();
        Loaded += (_, _) => ConfigureTimestampColumns();
    }

    private void AddRegistrationProcessorSelector()
    {
        var faceLabel = FindVisualChildren<TextBlock>(this).FirstOrDefault(x => x.Text == "Face image");
        var parent = faceLabel is null ? null : FindParent<StackPanel>(faceLabel);
        if (parent is null || parent.Children.OfType<FrameworkElement>().Any(x => x.Tag as string == "RegistrationProcessor")) return;

        var selector = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 8, 0, 8), Tag = "RegistrationProcessor" };
        selector.Children.Add(new TextBlock { Text = "Inference device", VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(0, 0, 14, 0) });
        var cpu = new Button { Content = "Use CPU", Margin = new Thickness(0, 0, 6, 0) };
        cpu.SetBinding(Button.CommandProperty, new Binding("UseCpuCommand"));
        var gpu = new Button { Content = "Use GPU" };
        gpu.SetBinding(Button.CommandProperty, new Binding("UseGpuCommand"));
        selector.Children.Add(cpu); selector.Children.Add(gpu);
        selector.Children.Add(new TextBlock { Text = "  Active: ", VerticalAlignment = VerticalAlignment.Center });
        var active = new TextBlock { VerticalAlignment = VerticalAlignment.Center };
        active.SetBinding(TextBlock.TextProperty, new Binding("ActiveProcessor"));
        selector.Children.Add(active);
        parent.Children.Insert(Math.Max(0, parent.Children.IndexOf(faceLabel)), selector);
    }

    private static T? FindParent<T>(DependencyObject child) where T : DependencyObject
    {
        for (var current = VisualTreeHelper.GetParent(child); current is not null; current = VisualTreeHelper.GetParent(current))
            if (current is T match) return match;
        return null;
    }

    private void ConfigureTimestampColumns()
    {
        foreach (var grid in FindVisualChildren<DataGrid>(this))
        foreach (var column in grid.Columns.OfType<DataGridTextColumn>())
        {
            var header = column.Header?.ToString();
            if (header is "Time" or "Created")
            {
                column.Header += " (IST)";
                column.Binding = new Binding(header == "Time" ? "Timestamp" : "CreatedAt")
                {
                    Converter = new IndiaTimeConverter()
                };
            }
        }
    }

    private static IEnumerable<T> FindVisualChildren<T>(DependencyObject root) where T : DependencyObject
    {
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
        {
            var child = VisualTreeHelper.GetChild(root, i);
            if (child is T match) yield return match;
            foreach (var nested in FindVisualChildren<T>(child)) yield return nested;
        }
    }

    private void CalibrationCanvas_Down(object sender,MouseButtonEventArgs e)
    {
        if(DataContext is not MainViewModel { CalibrationMode:not null } || CalibrationCanvas.ActualWidth<=0 || CalibrationCanvas.ActualHeight<=0) return;
        _calibrationStart=e.GetPosition(CalibrationCanvas); CalibrationCanvas.CaptureMouse(); CalibrationCanvas_Move(sender,e);
    }
    private void CalibrationCanvas_Move(object sender,MouseEventArgs e)
    {
        if(_calibrationStart is not Point start || DataContext is not MainViewModel vm) return;
        var point=e.GetPosition(CalibrationCanvas);
        if(vm.CalibrationMode=="zone")
        {
            DraftZone.Visibility=Visibility.Visible; DraftLine.Visibility=Visibility.Collapsed;
            Canvas.SetLeft(DraftZone,Math.Min(start.X,point.X)); Canvas.SetTop(DraftZone,Math.Min(start.Y,point.Y)); DraftZone.Width=Math.Abs(point.X-start.X); DraftZone.Height=Math.Abs(point.Y-start.Y);
        }
        else { DraftLine.Visibility=Visibility.Visible; DraftZone.Visibility=Visibility.Collapsed; DraftLine.X1=start.X; DraftLine.Y1=start.Y; DraftLine.X2=point.X; DraftLine.Y2=point.Y; }
    }
    private async void CalibrationCanvas_Up(object sender,MouseButtonEventArgs e)
    {
        if(_calibrationStart is not Point start || DataContext is not MainViewModel vm) return;
        var point=e.GetPosition(CalibrationCanvas); _calibrationStart=null; CalibrationCanvas.ReleaseMouseCapture(); DraftZone.Visibility=DraftLine.Visibility=Visibility.Collapsed;
        if(Math.Abs(point.X-start.X)<10 && Math.Abs(point.Y-start.Y)<10) return;
        await vm.SaveCalibrationAsync(start.X/CalibrationCanvas.ActualWidth,start.Y/CalibrationCanvas.ActualHeight,point.X/CalibrationCanvas.ActualWidth,point.Y/CalibrationCanvas.ActualHeight);
    }
    private void EvidenceOverlay_MouseDown(object sender,MouseButtonEventArgs e)
    {
        if(e.OriginalSource==sender && DataContext is MainViewModel vm) vm.EvidenceOpen=false;
    }
}
