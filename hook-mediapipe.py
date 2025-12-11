"""
PyInstaller hook to collect MediaPipe package data files (models & modules).

This hook uses PyInstaller's helper to collect package data so model files
like hand_landmark_tracking_cpu.binarypb are bundled into the frozen app.

Place this file in the project root and pass --additional-hooks-dir . to
PyInstaller (the build script will do this automatically).
"""
from PyInstaller.utils.hooks import collect_data_files

# collect all data files for mediapipe (this will include the 'modules' folder)
datas = collect_data_files('mediapipe')


'''
pyinstaller --onedir `
  --windowed `
  --name gesture_control `
  --icon icon.ico `
  --add-data "C:\path\to\site-packages\mediapipe\modules;mediapipe/modules" `
  --additional-hooks-dir . `
  gesture_control.py
'''