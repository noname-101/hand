<#
PowerShell build helper for creating a Windows executable with PyInstaller

Steps performed:
- Ensure an ICO icon exists (converts icon.jpg to icon.ico using convert_icon.py)
- Run PyInstaller with --onefile and the generated icon

Usage:
    .\build_exe.ps1 -Script 'gesture_control.py' -Name 'gesture_control'

#>

param(
    [string]$Script = 'gesture_control.py',
    [string]$Name = 'gesture_control',
    [string]$IconJpg = 'icon.jpg',
    [string]$IconIco = 'icon.ico'
)

Write-Host "Converting $IconJpg -> $IconIco (if needed)"
python .\convert_icon.py $IconJpg $IconIco

if (-not (Test-Path $IconIco)) {
    Write-Error "Icon conversion failed or $IconIco not found. Aborting."
    exit 2
}

Write-Host "Running PyInstaller..."
# Attempt to detect mediapipe's "modules" folder and include it as data so
# runtime model files (e.g. hand_landmark_tracking_cpu.binarypb) are available
# inside the bundled exe. This prevents FileNotFoundError like:
# "mediapipe/modules/hand_landmark/hand_landmark_tracking_cpu.binarypb"

$mediapipeModules = ''
try {
    $mediapipeModules = & python -c "import mediapipe, os; print(os.path.join(os.path.dirname(mediapipe.__file__), 'modules'))" 2>$null
    if ($mediapipeModules) { $mediapipeModules = $mediapipeModules.Trim() }
} catch {
    $mediapipeModules = ''
}

$addArgs = @()
if ($mediapipeModules -and (Test-Path $mediapipeModules)) {
    Write-Host "Including MediaPipe modules from: $mediapipeModules"
    # On Windows, PyInstaller expects add-data in the form "SRC;DEST"
    $addStr = "$mediapipeModules;mediapipe/modules"
    $addArgs += "--add-data"
    $addArgs += $addStr
} else {
    Write-Host "MediaPipe modules folder not found automatically; build may fail unless you add required media files manually."
    Write-Host "If you encounter FileNotFoundError for mediapipe model files, try building with --onedir or --add-data to include mediapipe/modules."
}

# Include current dir as hooks dir so our hook-mediapipe.py is picked up
$hookDirArg = @('--additional-hooks-dir','.')

$args = @('--onefile','--windowed','--name',$Name,'--icon',$IconIco) + $addArgs + $hookDirArg + @($Script)
Write-Host "pyinstaller $($args -join ' ')"
& pyinstaller @args

Write-Host "Build complete. See the 'dist' folder for the generated exe."