"""Ebook conversion using Calibre's ebook-convert."""
import subprocess
import threading
import tempfile
from pathlib import Path
from typing import Callable, Optional
import re
import sys
import shutil

from core.calibre_setup import get_tool_path
import config


class ConversionResult:
    """Result of a conversion operation."""
    def __init__(self, output_path: Path, cover_path: Optional[Path] = None, mobi_asin: Optional[str] = None):
        self.output_path = output_path
        self.cover_path = cover_path
        self.mobi_asin = mobi_asin  # The UUID calibre assigns

    def __str__(self):
        return str(self.output_path)

    def __fspath__(self):
        return str(self.output_path)

    @property
    def name(self):
        return self.output_path.name

    @property
    def suffix(self):
        return self.output_path.suffix

    @property
    def stem(self):
        return self.output_path.stem

    def exists(self):
        return self.output_path.exists()

    def stat(self):
        return self.output_path.stat()


class Converter:
    def __init__(self):
        self.ebook_convert = self._find_tool("ebook-convert")
        self.ebook_meta = self._find_tool("ebook-meta")

    def _find_tool(self, name: str) -> str:
        """Find a Calibre tool executable."""
        try:
            return str(get_tool_path(name))
        except FileNotFoundError:
            return name

    def _get_creation_flags(self):
        """Get subprocess creation flags to hide console on Windows."""
        if sys.platform == 'win32':
            return subprocess.CREATE_NO_WINDOW
        return 0

    def _extract_cover(self, input_path: Path, cover_path: Path) -> bool:
        """Extract cover image from ebook."""
        try:
            cmd = [
                self.ebook_meta,
                str(input_path),
                "--get-cover", str(cover_path)
            ]

            subprocess.run(
                cmd,
                capture_output=True,
                creationflags=self._get_creation_flags(),
                timeout=60
            )

            return cover_path.exists() and cover_path.stat().st_size > 0

        except Exception as e:
            print(f"Cover extraction failed: {e}")
            return False

    def _extract_mobi_asin(self, book_path: Path) -> Optional[str]:
        """Extract mobi-asin from book using ebook-meta."""
        try:
            cmd = [self.ebook_meta, str(book_path)]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=self._get_creation_flags(),
                timeout=30
            )

            if result.returncode != 0:
                return None

            # Parse output for mobi-asin
            match = re.search(r'mobi-asin:([a-f0-9-]+)', result.stdout, re.IGNORECASE)
            if match:
                return match.group(1)

        except Exception as e:
            print(f"Error extracting mobi-asin: {e}")

        return None

    def _clean_filename(self, name: str) -> str:
        """Clean filename to avoid path issues."""
        clean = re.sub(r'[<>:"/\\|?*]', '', name)
        clean = re.sub(r'\s+', ' ', clean).strip()
        if len(clean) > 80:
            clean = clean[:80]
        return clean

    def convert(
        self,
        input_path: Path,
        output_format: str,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> ConversionResult:
        """Convert ebook to specified format with cover preservation."""
        if output_dir is None:
            output_dir = config.TEMP_DIR

        output_dir.mkdir(parents=True, exist_ok=True)

        # Clean filename
        clean_name = self._clean_filename(input_path.stem)
        output_path = output_dir / f"{clean_name}.{output_format}"

        # Cover save path
        cover_save_path = output_dir / f"{clean_name}_cover.jpg"

        if output_path.exists():
            output_path.unlink()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            cover_path = temp_dir / "cover.jpg"

            # Step 1: Extract cover from source first
            if progress_callback:
                progress_callback(5, "Extracting cover...")

            has_cover = self._extract_cover(input_path, cover_path)
            if has_cover:
                print(f"Extracted cover: {cover_path.stat().st_size} bytes")
                shutil.copy2(cover_path, cover_save_path)
            else:
                print("No cover found in source file")
                cover_save_path = None

            # Step 2: Convert
            cmd = [
                self.ebook_convert,
                str(input_path),
                str(output_path),
            ]

            # Include cover during conversion
            if has_cover:
                cmd.extend(["--cover", str(cover_path)])

            if progress_callback:
                progress_callback(10, "Converting...")

            print(f"Converting: {input_path.name} -> {output_path.name}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=self._get_creation_flags()
            )

            for line in iter(process.stdout.readline, ''):
                if progress_callback:
                    match = re.search(r'(\d+)%', line)
                    if match:
                        raw_pct = int(match.group(1))
                        current_progress = 10 + int(raw_pct * 0.70)
                        progress_callback(current_progress, line.strip()[:50])

            process.wait()

            if process.returncode != 0:
                raise RuntimeError(f"Conversion failed with code {process.returncode}")

            if not output_path.exists():
                raise RuntimeError("Output file not found after conversion")

            # Step 3: Extract mobi-asin that calibre assigned
            if progress_callback:
                progress_callback(85, "Reading metadata...")

            mobi_asin = self._extract_mobi_asin(output_path)
            if mobi_asin:
                print(f"Found mobi-asin: {mobi_asin}")
            else:
                print("Warning: No mobi-asin found in converted file")

            # Step 4: Verify cover in output
            if progress_callback:
                progress_callback(90, "Verifying cover...")

            if not cover_save_path or not cover_save_path.exists():
                # Try extracting from converted file
                verify_cover = temp_dir / "verify_cover.jpg"
                if self._extract_cover(output_path, verify_cover):
                    shutil.copy2(verify_cover, output_dir / f"{clean_name}_cover.jpg")
                    cover_save_path = output_dir / f"{clean_name}_cover.jpg"
                    print(f"Extracted cover from output: {cover_save_path.stat().st_size} bytes")

        if progress_callback:
            progress_callback(100, "Complete")

        return ConversionResult(output_path, cover_save_path, mobi_asin)

    def convert_async(
        self,
        input_path: Path,
        output_format: str,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        completion_callback: Optional[Callable[[Optional[ConversionResult], Optional[Exception]], None]] = None
    ):
        """Run conversion in background thread."""
        def worker():
            try:
                result = self.convert(input_path, output_format, output_dir, progress_callback)
                if completion_callback:
                    completion_callback(result, None)
            except Exception as e:
                print(f"Conversion error: {e}")
                import traceback
                traceback.print_exc()
                if completion_callback:
                    completion_callback(None, e)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread