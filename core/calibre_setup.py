"""Calibre extraction and management."""
import sys
import zipfile
import shutil
from pathlib import Path
import threading

# Calibre will live here
APP_DATA = Path.home() / "AppData" / "Local" / "KindleSender"
CALIBRE_DIR = APP_DATA / "calibre"
VERSION_FILE = CALIBRE_DIR / ".installed_version"
CURRENT_VERSION = "1"

# Debug only when running as script, not EXE
DEBUG = not getattr(sys, 'frozen', False)


def _debug(msg):
    """Print debug message if debug mode is on."""
    if DEBUG:
        print(msg)


def get_bundled_zip() -> Path:
    """Get path to bundled calibre.zip."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / "calibre.zip"
    return Path(__file__).parent.parent / "calibre.zip"


def is_ready() -> bool:
    """Check if Calibre is extracted and ready."""
    exe = CALIBRE_DIR / "ebook-convert.exe"
    app_folder = CALIBRE_DIR / "app"

    _debug(f"[DEBUG] Checking Calibre at: {CALIBRE_DIR}")
    _debug(f"[DEBUG] ebook-convert.exe exists: {exe.exists()}")
    _debug(f"[DEBUG] app folder exists: {app_folder.exists()}")

    if not exe.exists():
        _debug("[DEBUG] is_ready: False (exe missing)")
        return False

    if not app_folder.exists():
        _debug("[DEBUG] is_ready: False (app folder missing)")
        return False

    if VERSION_FILE.exists():
        current = VERSION_FILE.read_text().strip()
        _debug(f"[DEBUG] Version file: {current}, Expected: {CURRENT_VERSION}")
        if current == CURRENT_VERSION:
            _debug("[DEBUG] is_ready: True")
            return True

    _debug("[DEBUG] is_ready: False (version mismatch or missing)")
    return False


def extract(progress_callback=None):
    """Extract Calibre to AppData."""
    zip_path = get_bundled_zip()

    _debug(f"[DEBUG] Extracting from: {zip_path}")
    _debug(f"[DEBUG] Extracting to: {CALIBRE_DIR}")

    if not zip_path.exists():
        raise FileNotFoundError(f"calibre.zip not found: {zip_path}")

    APP_DATA.mkdir(parents=True, exist_ok=True)

    if CALIBRE_DIR.exists():
        if progress_callback:
            progress_callback(5, "Removing old version...")
        _debug("[DEBUG] Removing old installation...")
        shutil.rmtree(CALIBRE_DIR, ignore_errors=True)

    CALIBRE_DIR.mkdir(parents=True, exist_ok=True)

    if progress_callback:
        progress_callback(10, "Extracting Calibre tools...")

    with zipfile.ZipFile(zip_path, 'r') as zf:
        members = zf.namelist()
        total = len(members)
        _debug(f"[DEBUG] Extracting {total} files...")

        for i, member in enumerate(members):
            zf.extract(member, CALIBRE_DIR)

            if progress_callback and i % 100 == 0:
                pct = 10 + int((i / total) * 85)
                progress_callback(pct, f"Extracting... ({i}/{total})")

    VERSION_FILE.write_text(CURRENT_VERSION)
    _debug(f"[DEBUG] Wrote version file: {VERSION_FILE}")

    exe = CALIBRE_DIR / "ebook-convert.exe"
    _debug(f"[DEBUG] Verification - exe exists: {exe.exists()}")

    if progress_callback:
        progress_callback(100, "Setup complete!")

    _debug("[DEBUG] Extraction complete!")
    return True


def extract_async(progress_callback=None, on_complete=None):
    """Extract in background thread."""
    def worker():
        try:
            extract(progress_callback)
            if on_complete:
                on_complete(True, None)
        except Exception as e:
            _debug(f"[DEBUG] Extraction error: {e}")
            if on_complete:
                on_complete(False, e)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


def get_tool_path(name: str) -> Path:
    """Get path to a Calibre tool."""
    tool = CALIBRE_DIR / f"{name}.exe"
    if tool.exists():
        return tool

    for path in [
        Path(rf"C:\Program Files\Calibre2\{name}.exe"),
        Path(rf"C:\Program Files (x86)\Calibre2\{name}.exe"),
    ]:
        if path.exists():
            return path

    raise FileNotFoundError(f"Calibre tool not found: {name}")