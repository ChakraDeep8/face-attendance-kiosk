using System.Configuration;
using System.Data;
using System.Windows;
using Verity.Desktop.Services;
using Verity.Desktop.ViewModels;

namespace Verity.Desktop;

/// <summary>
/// Interaction logic for App.xaml
/// </summary>
public partial class App : Application
{
    private MainViewModel? _viewModel;
    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        var supervisor = new WorkerSupervisor();
        _viewModel = new MainViewModel(supervisor);
        var window = new MainWindow { DataContext = _viewModel };
        MainWindow = window; window.Show();
        await _viewModel.InitializeAsync();
    }
    protected override async void OnExit(ExitEventArgs e)
    {
        if (_viewModel is not null) await _viewModel.DisposeAsync();
        base.OnExit(e);
    }
}
