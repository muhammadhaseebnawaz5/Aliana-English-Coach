@echo off
echo 🚀 Starting Alina Coach Build Process...
echo 📦 Installing dependencies just in case...
py -3.12 -m pip install PyQt6 openai edge_tts sounddevice soundfile groq pygame pillow pyinstaller

echo 🛠 Building Executable...
py -3.12 -m PyInstaller --noconsole --onefile --icon="app_icon.ico" --add-data "data;data" --name "Alina English Coach" app.py

echo ✅ Build Complete! Check the 'dist' folder for your .exe.
pause
