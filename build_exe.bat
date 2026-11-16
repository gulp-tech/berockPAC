@echo off
chcp 65001 >nul
echo Установка PyInstaller и сборка BedrockPackDownloader.exe...
python -m pip install --upgrade pip pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "BedrockPackDownloader" bedrock_pack_downloader.py
echo.
echo Готово! Файл находится в папке dist\BedrockPackDownloader.exe
pause
