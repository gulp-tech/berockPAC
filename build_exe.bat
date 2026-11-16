@echo off
echo Installing PyInstaller and building BedrockPackDownloader.exe...
python -m pip install --upgrade pip pyinstaller
if errorlevel 1 (
    echo ERROR: Python or pip not found. Please install Python 3.10+ from python.org
    pause
    exit /b 1
)
pyinstaller --noconfirm --onefile --windowed --name "BedrockPackDownloader" bedrock_pack_downloader.py
if errorlevel 1 (
    echo ERROR: Build failed.
    pause
    exit /b 1
)
echo.
echo Done! File saved to dist\BedrockPackDownloader.exe
pause
