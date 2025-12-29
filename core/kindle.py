"""Kindle device detection and file transfer."""
import os
import shutil
import threading
from pathlib import Path
from typing import Optional, Callable, List
import string
import platform


class KindleDevice:
    def __init__(self, path: Path, name: str = "Kindle"):
        self.path = path
        self.name = name
        self.documents_folder = path / "documents"
        self.thumbnail_folder = path / "system" / "thumbnails"

    @property
    def free_space(self) -> str:
        """Get free space on device."""
        try:
            if platform.system() == "Windows":
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(str(self.path)), None, None, ctypes.pointer(free_bytes)
                )
                free = free_bytes.value
            else:
                stat = os.statvfs(self.path)
                free = stat.f_bavail * stat.f_frsize

            for unit in ["B", "KB", "MB", "GB"]:
                if free < 1024:
                    return f"{free:.1f} {unit}"
                free /= 1024
            return f"{free:.1f} TB"
        except:
            return "Unknown"

    def get_books(self) -> List[Path]:
        """List books currently on device."""
        if not self.documents_folder.exists():
            return []
        extensions = {'.azw3', '.mobi', '.azw', '.pdf', '.txt', '.epub'}
        return [f for f in self.documents_folder.iterdir() if f.suffix.lower() in extensions]


class KindleManager:
    def __init__(self):
        self._device: Optional[KindleDevice] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitoring = False
        self._callbacks: List[Callable[[Optional[KindleDevice]], None]] = []

    @property
    def device(self) -> Optional[KindleDevice]:
        return self._device

    @property
    def is_connected(self) -> bool:
        return self._device is not None

    def add_connection_callback(self, callback: Callable[[Optional[KindleDevice]], None]):
        """Register callback for connection state changes."""
        self._callbacks.append(callback)

    def _notify_callbacks(self):
        for cb in self._callbacks:
            try:
                cb(self._device)
            except Exception as e:
                print(f"Callback error: {e}")

    def scan(self) -> Optional[KindleDevice]:
        """Scan for connected Kindle device."""
        device = self._scan_impl()
        if device != self._device:
            self._device = device
            self._notify_callbacks()
        return device

    def _scan_impl(self) -> Optional[KindleDevice]:
        """Platform-specific Kindle detection."""
        system = platform.system()

        if system == "Windows":
            return self._scan_windows()
        elif system == "Darwin":
            return self._scan_macos()
        else:
            return self._scan_linux()

    def _scan_windows(self) -> Optional[KindleDevice]:
        """Scan for Kindle on Windows."""
        for letter in string.ascii_uppercase:
            drive = Path(f"{letter}:\\")
            if not drive.exists():
                continue

            docs = drive / "documents"

            if docs.exists():
                kindle_indicators = [
                    drive / "system",
                    drive / "amazon-cover-bug",
                    drive / "audible",
                ]
                for indicator in kindle_indicators:
                    if indicator.exists():
                        return KindleDevice(drive, self._get_kindle_name(drive))

        return None

    def _scan_macos(self) -> Optional[KindleDevice]:
        """Scan for Kindle on macOS."""
        volumes = Path("/Volumes")
        if not volumes.exists():
            return None

        for vol in volumes.iterdir():
            if "kindle" in vol.name.lower():
                docs = vol / "documents"
                if docs.exists():
                    return KindleDevice(vol, vol.name)

        return None

    def _scan_linux(self) -> Optional[KindleDevice]:
        """Scan for Kindle on Linux."""
        try:
            username = os.getlogin()
        except:
            username = os.environ.get('USER', '')

        mount_points = [
            Path("/media") / username,
            Path("/mnt"),
            Path("/run/media") / username
        ]

        for mount in mount_points:
            if not mount.exists():
                continue
            for device in mount.iterdir():
                if device.is_dir():
                    docs = device / "documents"
                    if docs.exists():
                        if (device / "system").exists() or (device / "amazon-cover-bug").exists():
                            return KindleDevice(device, device.name)

        return None

    def _get_kindle_name(self, path: Path) -> str:
        """Try to get Kindle device name."""
        try:
            version_file = path / "system" / "version.txt"
            if version_file.exists():
                content = version_file.read_text()
                if "Kindle" in content:
                    return "Kindle"
        except:
            pass
        return "Kindle"

    def start_monitoring(self, interval: float = 2.0):
        """Start background monitoring for device connection."""
        if self._monitoring:
            return

        self._monitoring = True

        def monitor():
            import time
            while self._monitoring:
                self.scan()
                time.sleep(interval)

        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self):
        """Stop background monitoring."""
        self._monitoring = False

    def _create_thumbnail(self, cover_path: Path, thumbnail_path: Path) -> bool:
        """Create a properly sized thumbnail for Kindle."""
        try:
            from PIL import Image

            # Kindle thumbnail size
            THUMB_WIDTH = 330
            THUMB_HEIGHT = 470

            img = Image.open(cover_path)

            # Convert to RGB
            if img.mode in ('RGBA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Resize maintaining aspect ratio
            img.thumbnail((THUMB_WIDTH, THUMB_HEIGHT), Image.Resampling.LANCZOS)

            # Save as JPEG
            img.save(thumbnail_path, 'JPEG', quality=90)
            return True

        except Exception as e:
            print(f"Failed to create thumbnail: {e}")
            return False

    def transfer_file(
        self,
        file_path,
        cover_path: Optional[Path] = None,
        mobi_asin: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> bool:
        """Transfer file to connected Kindle with cover thumbnail."""
        if not self._device:
            raise RuntimeError("No Kindle device connected")

        # Handle ConversionResult or Path
        if hasattr(file_path, 'output_path'):
            actual_path = Path(file_path.output_path)
            if cover_path is None and hasattr(file_path, 'cover_path'):
                cover_path = file_path.cover_path
            if mobi_asin is None and hasattr(file_path, 'mobi_asin'):
                mobi_asin = file_path.mobi_asin
        elif hasattr(file_path, '__fspath__'):
            actual_path = Path(file_path)
        else:
            actual_path = Path(str(file_path))

        if not actual_path.exists():
            raise FileNotFoundError(f"Source file not found: {actual_path}")

        dest = self._device.documents_folder / actual_path.name

        print(f"Transferring: {actual_path.name}")

        file_size = actual_path.stat().st_size
        copied = 0
        chunk_size = 1024 * 1024

        # Copy the book file
        with open(actual_path, 'rb') as src, open(dest, 'wb') as dst:
            while True:
                chunk = src.read(chunk_size)
                if not chunk:
                    break
                dst.write(chunk)
                copied += len(chunk)
                if progress_callback:
                    progress_callback((copied / file_size) * 80)

        print(f"Book transferred to: {dest}")

        # Create thumbnail if we have cover and mobi_asin
        if cover_path and Path(cover_path).exists() and mobi_asin:
            if progress_callback:
                progress_callback(85)

            # Ensure thumbnail folder exists
            self._device.thumbnail_folder.mkdir(parents=True, exist_ok=True)

            # Create thumbnail with correct naming pattern
            thumb_name = f"thumbnail_{mobi_asin}_EBOK_portrait.jpg"
            thumb_path = self._device.thumbnail_folder / thumb_name

            if progress_callback:
                progress_callback(90)

            if self._create_thumbnail(Path(cover_path), thumb_path):
                print(f"✓ Thumbnail created: {thumb_name}")
            else:
                print("✗ Failed to create thumbnail")
        else:
            if not mobi_asin:
                print("⚠ No mobi-asin - thumbnail not created")
            if not cover_path or not Path(cover_path).exists():
                print("⚠ No cover available - thumbnail not created")

        if progress_callback:
            progress_callback(100)

        return True

    def transfer_file_async(
        self,
        file_path,
        cover_path: Optional[Path] = None,
        mobi_asin: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
        completion_callback: Optional[Callable[[bool, Optional[Exception]], None]] = None
    ):
        """Transfer file in background thread."""
        def worker():
            try:
                result = self.transfer_file(file_path, cover_path, mobi_asin, progress_callback)
                if completion_callback:
                    completion_callback(result, None)
            except Exception as e:
                print(f"Transfer error: {e}")
                import traceback
                traceback.print_exc()
                if completion_callback:
                    completion_callback(False, e)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread