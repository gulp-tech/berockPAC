# Bedrock Pack Downloader (Minecraft Bedrock 1.26.63)

Простая программа для Windows (`.exe`) для поиска, скачивания и автоматической установки текстурпаков (`.mcpack` / `.zip`) в Minecraft Bedrock Edition **1.26.63**.

## Возможности
- Поиск текстурпаков через Modrinth API без регистрации и ключей.
- Скачивание по прямой ссылке (`.mcpack` / `.zip`).
- Автоматическое определение папки `resource_packs` Minecraft Bedrock (`Microsoft.MinecraftUWP_8wekyb3d8bbwe`).
- Автоматический запуск `.mcpack` в Minecraft после скачивания.
- Проверка `manifest.json` и отображение `min_engine_version`.

## Как получить `.exe`
1. **Через GitHub Actions:** перейдите во вкладку **Actions** в репозитории, откройте последний запуск **Build Windows EXE** и скачайте артефакт `BedrockPackDownloader-exe`.
2. **Локально на Windows:** установите Python 3.10+ и дважды кликните `build_exe.bat` — готовый файл появится в `dist\BedrockPackDownloader.exe`.

## Запуск из исходников
```bash
python bedrock_pack_downloader.py
```
