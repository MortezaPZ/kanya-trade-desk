from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


FROZEN = bool(getattr(sys, "frozen", False))
APP_DIR = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent


def prepare_local_config() -> Path:
    if FROZEN:
        config_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "KanyaTradeDesk"
        os.environ["APP_CONFIG_DIR"] = str(config_dir)
    else:
        config_dir = APP_DIR
    config_dir.mkdir(parents=True, exist_ok=True)
    env_file = config_dir / ".env"
    template = APP_DIR / ".env.example"
    if not env_file.exists() and template.exists():
        shutil.copyfile(template, env_file)
    os.chdir(APP_DIR)
    return config_dir


class DeskLauncher:
    def __init__(self, root, config_dir: Path):
        import tkinter as tk

        self.tk = tk
        self.root = root
        self.config_dir = config_dir
        self.server_process = None
        self.start_time = 0.0
        self.url = "http://127.0.0.1:8787"

        root.title("دستیار کانیا تریدینگ")
        root.geometry("520x330")
        root.resizable(False, False)
        root.configure(bg="#f5f7fa")
        root.protocol("WM_DELETE_WINDOW", self.close)

        tk.Label(
            root,
            text="دستیار کانیا تریدینگ",
            font=("Segoe UI", 18, "bold"),
            bg="#f5f7fa",
            fg="#17324d",
        ).pack(pady=(22, 8))
        tk.Label(
            root,
            text="متاتریدر ۵ را باز کنید و وارد حساب شوید.\nصفحهٔ دستیار با بازشدن این برنامه در مرورگر آماده می‌شود.",
            font=("Segoe UI", 11),
            bg="#f5f7fa",
            fg="#293845",
            justify="right",
            anchor="e",
        ).pack(fill="x", padx=34, pady=8)

        self.status = tk.StringVar(value="برای شروع، متاتریدر را باز و وارد حساب کنید.")
        tk.Label(
            root,
            textvariable=self.status,
            font=("Segoe UI", 10),
            bg="#f5f7fa",
            fg="#526575",
            wraplength=450,
            justify="center",
            height=3,
        ).pack(fill="x", padx=28, pady=(6, 8))

        buttons = tk.Frame(root, bg="#f5f7fa")
        buttons.pack(pady=12)
        tk.Button(
            buttons,
            text="بازکردن صفحه",
            font=("Segoe UI", 12, "bold"),
            bg="#d4a017",
            fg="#1a1404",
            activebackground="#edc24b",
            relief="flat",
            padx=24,
            pady=10,
            command=self.start,
        ).pack(side="right", padx=8)
        tk.Button(
            buttons,
            text="بستن",
            font=("Segoe UI", 11),
            padx=18,
            pady=9,
            command=self.close,
        ).pack(side="right", padx=8)

        tk.Label(
            root,
            text="این برنامه سفارش خرید یا فروش ارسال نمی‌کند.",
            font=("Segoe UI", 9),
            bg="#f5f7fa",
            fg="#73818b",
        ).pack(side="bottom", pady=16)

    def start(self) -> None:
        if self.server_process and self.server_process.poll() is None:
            self.status.set("دستیار در حال آماده‌شدن است؛ چند لحظه صبر کنید…")
            self.root.after(500, self._check_ready)
            return

        self.status.set("دستیار در حال آماده‌شدن است؛ چند لحظه صبر کنید…")
        self.start_time = time.monotonic()
        server_dir = APP_DIR / "server"
        server_exe = server_dir / "KanyaTradeDeskServer.exe"
        if FROZEN:
            if not server_exe.is_file():
                self.status.set("فایل‌های برنامه کامل نیستند؛ بسته را دوباره دریافت کنید.")
                self._show_error("نسخهٔ برنامه ناقص است", f"فایل پیدا نشد: {server_exe}")
                return
            command = [str(server_exe)]
            server_cwd = server_dir
        else:
            command = [sys.executable, str(APP_DIR / "server_entry.py")]
            server_cwd = APP_DIR
        server_env = os.environ.copy()
        if FROZEN:
            server_env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        server_env["APP_OPEN_BROWSER"] = "false"
        try:
            self.server_process = subprocess.Popen(
                command,
                cwd=server_cwd,
                env=server_env,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                close_fds=True,
            )
        except OSError as exc:
            self.status.set("برنامه آمادهٔ اجرا نشد. پوشهٔ برنامه را دوباره دریافت کنید.")
            self._show_error("راه‌اندازی ناموفق بود", str(exc))
            return
        self.root.after(500, self._check_ready)

    def _check_ready(self) -> None:
        try:
            with urllib.request.urlopen(self.url + "/api/health", timeout=1) as response:
                health = json.loads(response.read().decode("utf-8"))
            if health.get("ok") and health.get("read_only") is True:
                self.status.set(
                    "صفحهٔ دستیار باز شد. اگر متاتریدر متصل نیست، آن را باز کنید و دوباره تلاش کنید."
                    if not health.get("connected")
                    else "دستیار آماده است و متاتریدر متصل است."
                )
                self.open_page()
                return
            self._show_error("سرویس مورد انتظار پیدا نشد", "پورت برنامه در حال استفاده است. برنامه را ببندید و دوباره اجرا کنید.")
            return
        except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError):
            if not self.server_process or self.server_process.poll() is not None:
                code = self.server_process.returncode if self.server_process else "—"
                self._show_error("راه‌اندازی ناموفق بود", f"برنامه متوقف شد (کد {code}). پنجره را ببندید و دوباره اجرا کنید.")
                return

        if time.monotonic() - self.start_time > 30:
            self._show_error("راه‌اندازی طول کشید", "صفحه باز نشد. متاتریدر را بررسی کنید و دوباره تلاش کنید.")
            return
        self.root.after(500, self._check_ready)

    def open_page(self) -> None:
        webbrowser.open(self.url)
        if self.status.get().startswith("دستیار در حال"):
            self.status.set("صفحهٔ دستیار در مرورگر باز می‌شود.")

    def _show_error(self, title: str, message: str) -> None:
        from tkinter import messagebox

        messagebox.showerror(title, message, parent=self.root)

    def close(self) -> None:
        if self.server_process and self.server_process.poll() is None:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
        self.root.destroy()


def main() -> None:
    prepare_local_config()
    import tkinter as tk

    root = tk.Tk()
    launcher = DeskLauncher(root, Path(os.environ.get("APP_CONFIG_DIR", APP_DIR)))
    root.after(300, launcher.start)
    root.mainloop()


if __name__ == "__main__":
    main()
