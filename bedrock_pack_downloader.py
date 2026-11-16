import json
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import urllib.error
import urllib.parse
import urllib.request
import zipfile

APP_TITLE = "Bedrock Pack Downloader — v1.26.63"
TARGET_MC_VERSION = "1.26.63"
MODRINTH_API = "https://api.modrinth.com/v2"
USER_AGENT = "BedrockPackDownloader/1.0 (Minecraft Bedrock 1.26.63)"


def get_default_bedrock_packs_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        uwp_path = (
            Path(local_app_data)
            / "Packages"
            / "Microsoft.MinecraftUWP_8wekyb3d8bbwe"
            / "LocalState"
            / "games"
            / "com.mojang"
            / "resource_packs"
        )
        if uwp_path.exists():
            return uwp_path

        preview_path = (
            Path(local_app_data)
            / "Packages"
            / "Microsoft.MinecraftWindowsBeta_8wekyb3d8bbwe"
            / "LocalState"
            / "games"
            / "com.mojang"
            / "resource_packs"
        )
        if preview_path.exists():
            return preview_path

    downloads = Path.home() / "Downloads" / "MinecraftBedrockPacks"
    downloads.mkdir(parents=True, exist_ok=True)
    return downloads


def http_get_json(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_file(url: str, dest: Path, progress_cb=None) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length", 0) or 0)
        downloaded = 0
        chunk_size = 65536
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_cb and total > 0:
                    progress_cb(int(downloaded * 100 / total))


def inspect_mcpack(file_path: Path) -> dict:
    info = {
        "valid": False,
        "name": file_path.stem,
        "description": "",
        "min_engine_version": "не указана",
    }
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            manifest_name = None
            for name in zf.namelist():
                if name.endswith("manifest.json"):
                    manifest_name = name
                    break
            if manifest_name:
                raw = zf.read(manifest_name).decode("utf-8", errors="replace")
                data = json.loads(raw)
                header = data.get("header", {})
                info["valid"] = True
                info["name"] = header.get("name", file_path.stem)
                info["description"] = header.get("description", "")
                min_ver = header.get("min_engine_version")
                if isinstance(min_ver, list):
                    info["min_engine_version"] = ".".join(str(x) for x in min_ver)
    except Exception:
        pass
    return info


class BedrockPackDownloaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("880x620")
        self.root.minsize(760, 520)
        self.root.configure(bg="#181a1f")

        self.save_dir_var = tk.StringVar(value=str(get_default_bedrock_packs_dir()))
        self.search_var = tk.StringVar()
        self.url_var = tk.StringVar()
        self.status_var = tk.StringVar(
            value=f"Готово к работе | Целевая версия Minecraft Bedrock: {TARGET_MC_VERSION}"
        )
        self.results: list[dict] = []

        self._setup_styles()
        self._build_ui()
        self._search_packs(initial=True)

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#181a1f")
        style.configure("TLabel", background="#181a1f", foreground="#e6e6e6", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#4ade80")
        style.configure("Sub.TLabel", font=("Segoe UI", 9), foreground="#9ca3af")
        style.configure(
            "TButton",
            background="#2563eb",
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            padding=(12, 6),
            borderwidth=0,
        )
        style.map("TButton", background=[("active", "#1d4ed8"), ("disabled", "#374151")])
        style.configure(
            "Green.TButton",
            background="#16a34a",
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            padding=(12, 6),
        )
        style.map("Green.TButton", background=[("active", "#15803d"), ("disabled", "#374151")])
        style.configure(
            "Treeview",
            background="#22252c",
            foreground="#f3f4f6",
            fieldbackground="#22252c",
            rowheight=28,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Treeview.Heading",
            background="#2d3139",
            foreground="#e5e7eb",
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Treeview", background=[("selected", "#2563eb")])

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=14)
        main.pack(fill=tk.BOTH, expand=True)

        # Header
        header_frame = ttk.Frame(main)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(
            header_frame,
            text="Загрузчик текстурпаков Minecraft Bedrock (1.26.63)",
            style="Header.TLabel",
        ).pack(side=tk.LEFT)
        ttk.Label(
            header_frame,
            text="Формат: .mcpack / .zip",
            style="Sub.TLabel",
        ).pack(side=tk.RIGHT, pady=4)

        # Save directory row
        dir_frame = ttk.Frame(main)
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(dir_frame, text="Папка сохранения:").pack(side=tk.LEFT, padx=(0, 8))
        dir_entry = tk.Entry(
            dir_frame,
            textvariable=self.save_dir_var,
            bg="#22252c",
            fg="#f3f4f6",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            font=("Segoe UI", 10),
        )
        dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 8))
        ttk.Button(dir_frame, text="Обзор...", command=self._choose_dir).pack(side=tk.LEFT)

        # Search row
        search_frame = ttk.Frame(main)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(search_frame, text="Поиск текстурпака:").pack(side=tk.LEFT, padx=(0, 8))
        search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            bg="#22252c",
            fg="#f3f4f6",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            font=("Segoe UI", 10),
        )
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 8))
        search_entry.bind("<Return>", lambda e: self._search_packs())
        self.search_btn = ttk.Button(search_frame, text="Найти", command=self._search_packs)
        self.search_btn.pack(side=tk.LEFT)

        # Results table
        table_frame = ttk.Frame(main)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns = ("title", "author", "downloads", "description")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("title", text="Название")
        self.tree.heading("author", text="Автор")
        self.tree.heading("downloads", text="Скачивания")
        self.tree.heading("description", text="Описание")

        self.tree.column("title", width=220, minwidth=150)
        self.tree.column("author", width=120, minwidth=90)
        self.tree.column("downloads", width=95, minwidth=80, anchor=tk.CENTER)
        self.tree.column("description", width=360, minwidth=200)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Action buttons for selected pack
        action_frame = ttk.Frame(main)
        action_frame.pack(fill=tk.X, pady=(0, 10))
        self.download_btn = ttk.Button(
            action_frame,
            text="Скачать выбранный текстурпак",
            style="Green.TButton",
            command=self._download_selected,
        )
        self.download_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.auto_install_var = tk.BooleanVar(value=True)
        auto_chk = tk.Checkbutton(
            action_frame,
            text="Автоматически открыть .mcpack в Minecraft после скачивания",
            variable=self.auto_install_var,
            bg="#181a1f",
            fg="#e5e7eb",
            selectcolor="#22252c",
            activebackground="#181a1f",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
        )
        auto_chk.pack(side=tk.LEFT, padx=8)

        # Direct URL row
        url_frame = ttk.Frame(main)
        url_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(url_frame, text="Прямая ссылка (.mcpack/.zip):").pack(side=tk.LEFT, padx=(0, 8))
        url_entry = tk.Entry(
            url_frame,
            textvariable=self.url_var,
            bg="#22252c",
            fg="#f3f4f6",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            font=("Segoe UI", 10),
        )
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 8))
        ttk.Button(url_frame, text="Скачать по ссылке", command=self._download_direct_url).pack(
            side=tk.LEFT
        )

        # Progress bar & status
        self.progress = ttk.Progressbar(main, mode="determinate", maximum=100)
        self.progress.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(main, textvariable=self.status_var, style="Sub.TLabel").pack(anchor=tk.W)

    def _choose_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.save_dir_var.get())
        if chosen:
            self.save_dir_var.set(chosen)

    def _set_status(self, text: str):
        self.root.after(0, lambda: self.status_var.set(text))

    def _set_progress(self, value: int):
        self.root.after(0, lambda: self.progress.configure(value=value))

    def _search_packs(self, initial: bool = False):
        query = self.search_var.get().strip()
        self.search_btn.configure(state=tk.DISABLED)
        self._set_status("Поиск текстурпаков...")

        def worker():
            try:
                facets = json.dumps([["project_type:resourcepack"]])
                params = {
                    "query": query if query else "bedrock",
                    "facets": facets,
                    "limit": "30",
                    "index": "downloads",
                }
                url = f"{MODRINTH_API}/search?{urllib.parse.urlencode(params)}"
                data = http_get_json(url)
                hits = data.get("hits", [])
                self.results = hits

                def update_tree():
                    for item in self.tree.get_children():
                        self.tree.delete(item)
                    for idx, hit in enumerate(hits):
                        self.tree.insert(
                            "",
                            tk.END,
                            iid=str(idx),
                            values=(
                                hit.get("title", "Без названия"),
                                hit.get("author", "Неизвестно"),
                                f"{hit.get('downloads', 0):,}".replace(",", " "),
                                (hit.get("description", "") or "").replace("\n", " "),
                            ),
                        )
                    self.search_btn.configure(state=tk.NORMAL)
                    self._set_status(
                        f"Найдено текстурпаков: {len(hits)} | Версия Minecraft: {TARGET_MC_VERSION}"
                    )

                self.root.after(0, update_tree)
            except Exception as exc:
                self.root.after(0, lambda: self.search_btn.configure(state=tk.NORMAL))
                self._set_status(f"Ошибка поиска: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _download_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите текстурпак из списка.")
            return
        idx = int(selected[0])
        hit = self.results[idx]
        project_id = hit.get("project_id")
        title = hit.get("title", "pack")
        self.download_btn.configure(state=tk.DISABLED)
        self._set_progress(0)
        self._set_status(f"Получение ссылки для «{title}»...")

        def worker():
            try:
                versions = http_get_json(f"{MODRINTH_API}/project/{project_id}/version")
                if not versions:
                    raise RuntimeError("У этого проекта нет доступных файлов.")

                chosen_file = None
                for ver in versions:
                    for f in ver.get("files", []):
                        fname = f.get("filename", "").lower()
                        if fname.endswith(".mcpack") or fname.endswith(".zip"):
                            chosen_file = f
                            break
                    if chosen_file:
                        break

                if not chosen_file:
                    chosen_file = versions[0]["files"][0]

                file_url = chosen_file["url"]
                filename = chosen_file["filename"]
                self._perform_download(file_url, filename)
            except Exception as exc:
                self._set_status(f"Ошибка скачивания: {exc}")
                self.root.after(
                    0, lambda: messagebox.showerror("Ошибка", f"Не удалось скачать:\n{exc}")
                )
            finally:
                self.root.after(0, lambda: self.download_btn.configure(state=tk.NORMAL))

        threading.Thread(target=worker, daemon=True).start()

    def _download_direct_url(self):
        url = self.url_var.get().strip()
        if not url.startswith(("http://", "https://")):
            messagebox.showwarning("Внимание", "Введите корректную ссылку (http:// или https://).")
            return
        filename = Path(urllib.parse.urlparse(url).path).name or "texture_pack.mcpack"
        if not (filename.lower().endswith(".mcpack") or filename.lower().endswith(".zip")):
            filename += ".mcpack"

        self._set_progress(0)
        self._set_status(f"Скачивание {filename}...")

        def worker():
            try:
                self._perform_download(url, filename)
            except Exception as exc:
                self._set_status(f"Ошибка скачивания: {exc}")
                self.root.after(
                    0, lambda: messagebox.showerror("Ошибка", f"Не удалось скачать:\n{exc}")
                )

        threading.Thread(target=worker, daemon=True).start()

    def _perform_download(self, url: str, filename: str):
        save_dir = Path(self.save_dir_var.get())
        save_dir.mkdir(parents=True, exist_ok=True)
        dest = save_dir / filename

        self._set_status(f"Скачивание {filename}...")
        download_file(url, dest, progress_cb=self._set_progress)
        self._set_progress(100)

        info = inspect_mcpack(dest)
        status_msg = f"Скачано: {dest.name}"
        if info["valid"]:
            status_msg += f" | Пак: {info['name']} (min_engine: {info['min_engine_version']})"
        self._set_status(status_msg)

        if self.auto_install_var.get() and sys.platform == "win32" and dest.suffix.lower() == ".mcpack":
            try:
                os.startfile(str(dest))
            except Exception:
                pass

        self.root.after(
            0,
            lambda: messagebox.showinfo(
                "Готово",
                f"Текстурпак успешно скачан!\n\nФайл: {dest}\n"
                f"Совместимость: {info['min_engine_version']}",
            ),
        )


def main():
    root = tk.Tk()
    BedrockPackDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
