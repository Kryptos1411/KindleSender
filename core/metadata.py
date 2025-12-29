"""Extract metadata and covers from ebook files."""
from pathlib import Path
from typing import Optional
import zipfile
from dataclasses import dataclass
from PIL import Image
import io
import re
import subprocess
import sys

from core.calibre_setup import get_tool_path


@dataclass
class BookMetadata:
    title: str
    author: str
    cover_image: Optional[Image.Image]
    file_path: Path
    file_size: str
    format: str

    @property
    def display_title(self) -> str:
        return self.title[:50] + "..." if len(self.title) > 50 else self.title


def get_file_size_str(path: Path) -> str:
    """Human-readable file size."""
    size = path.stat().st_size
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def fetch_metadata_calibre(file_path: Path) -> Optional[dict]:
    """Use Calibre's ebook-meta to get metadata."""
    try:
        ebook_meta_tool = get_tool_path("ebook-meta")
    except FileNotFoundError:
        return None

    result = {}

    try:
        creationflags = 0
        if sys.platform == 'win32':
            creationflags = subprocess.CREATE_NO_WINDOW

        proc = subprocess.run(
            [str(ebook_meta_tool), str(file_path)],
            capture_output=True,
            text=True,
            creationflags=creationflags,
            timeout=30
        )

        if proc.returncode == 0:
            output = proc.stdout

            # Parse title
            title_match = re.search(r'^Title\s*:\s*(.+)$', output, re.MULTILINE)
            if title_match:
                result['title'] = title_match.group(1).strip()

            # Parse author
            author_match = re.search(r'^Author\(s\)\s*:\s*(.+)$', output, re.MULTILINE)
            if author_match:
                author = author_match.group(1).strip()
                author = re.sub(r'\s*\[[^\]]+\]', '', author)
                result['author'] = author

        # Extract cover using ebook-meta --get-cover
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            cover_path = Path(temp_dir) / "cover.jpg"

            proc = subprocess.run(
                [str(ebook_meta_tool), str(file_path), "--get-cover", str(cover_path)],
                capture_output=True,
                text=True,
                creationflags=creationflags,
                timeout=30
            )

            if cover_path.exists():
                result['cover_image'] = Image.open(cover_path).copy()

    except subprocess.TimeoutExpired:
        print("Metadata extraction timed out")
    except Exception as e:
        print(f"Error fetching metadata with Calibre: {e}")

    return result if result else None


def extract_epub_metadata_fallback(epub_path: Path) -> dict:
    """Fallback: Extract metadata directly from EPUB using regex."""
    title = epub_path.stem
    author = "Unknown Author"
    cover_image = None

    try:
        with zipfile.ZipFile(epub_path, 'r') as zf:
            opf_path = None
            opf_content = None

            for name in zf.namelist():
                if name.endswith('.opf'):
                    opf_path = name
                    opf_content = zf.read(name).decode('utf-8', errors='ignore')
                    break

            if not opf_path:
                try:
                    container = zf.read('META-INF/container.xml').decode('utf-8', errors='ignore')
                    match = re.search(r'full-path="([^"]+\.opf)"', container)
                    if match:
                        opf_path = match.group(1)
                        opf_content = zf.read(opf_path).decode('utf-8', errors='ignore')
                except:
                    pass

            if opf_content:
                # Extract title
                title_match = re.search(r'<dc:title[^>]*>([^<]+)</dc:title>', opf_content, re.IGNORECASE)
                if not title_match:
                    title_match = re.search(r'<title[^>]*>([^<]+)</title>', opf_content, re.IGNORECASE)
                if title_match:
                    title = title_match.group(1).strip()

                # Extract author
                author_match = re.search(r'<dc:creator[^>]*>([^<]+)</dc:creator>', opf_content, re.IGNORECASE)
                if not author_match:
                    author_match = re.search(r'<creator[^>]*>([^<]+)</creator>', opf_content, re.IGNORECASE)
                if author_match:
                    author = author_match.group(1).strip()

                # Find cover image
                cover_href = None

                cover_id_match = re.search(r'<meta[^>]*name="cover"[^>]*content="([^"]+)"', opf_content, re.IGNORECASE)
                if not cover_id_match:
                    cover_id_match = re.search(r'<meta[^>]*content="([^"]+)"[^>]*name="cover"', opf_content, re.IGNORECASE)

                if cover_id_match:
                    cover_id = cover_id_match.group(1)
                    item_pattern = rf'<item[^>]*id="{re.escape(cover_id)}"[^>]*href="([^"]+)"'
                    item_match = re.search(item_pattern, opf_content, re.IGNORECASE)
                    if not item_match:
                        item_pattern = rf'<item[^>]*href="([^"]+)"[^>]*id="{re.escape(cover_id)}"'
                        item_match = re.search(item_pattern, opf_content, re.IGNORECASE)
                    if item_match:
                        cover_href = item_match.group(1)

                if not cover_href:
                    cover_item_match = re.search(
                        r'<item[^>]*(?:id="[^"]*cover[^"]*"|properties="[^"]*cover[^"]*")[^>]*href="([^"]+)"',
                        opf_content, re.IGNORECASE
                    )
                    if not cover_item_match:
                        cover_item_match = re.search(
                            r'<item[^>]*href="([^"]+)"[^>]*(?:id="[^"]*cover[^"]*"|properties="[^"]*cover[^"]*")',
                            opf_content, re.IGNORECASE
                        )
                    if cover_item_match:
                        cover_href = cover_item_match.group(1)

                if cover_href and opf_path:
                    opf_dir = str(Path(opf_path).parent)
                    if opf_dir and opf_dir != '.':
                        cover_full_path = f"{opf_dir}/{cover_href}"
                    else:
                        cover_full_path = cover_href

                    from urllib.parse import unquote
                    cover_full_path = unquote(cover_full_path)

                    for zf_name in zf.namelist():
                        if zf_name == cover_full_path or zf_name.endswith(cover_href):
                            try:
                                cover_data = zf.read(zf_name)
                                cover_image = Image.open(io.BytesIO(cover_data))
                                break
                            except:
                                continue

            # Fallback: search for common cover image names
            if cover_image is None:
                cover_patterns = ['cover.jpg', 'cover.jpeg', 'cover.png', 'Cover.jpg', 'Cover.jpeg', 'Cover.png']
                for name in zf.namelist():
                    name_lower = name.lower()
                    if any(p.lower() in name_lower for p in cover_patterns):
                        if name_lower.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                            try:
                                cover_data = zf.read(name)
                                cover_image = Image.open(io.BytesIO(cover_data))
                                break
                            except:
                                continue

    except Exception as e:
        print(f"Error extracting EPUB metadata: {e}")

    return {
        'title': title,
        'author': author,
        'cover_image': cover_image
    }


def extract_metadata(file_path: Path) -> BookMetadata:
    """Extract metadata from any supported ebook format."""
    title = file_path.stem
    author = "Unknown Author"
    cover_image = None

    # Try Calibre's ebook-meta first (fast, local)
    calibre_meta = fetch_metadata_calibre(file_path)
    if calibre_meta:
        title = calibre_meta.get('title', title)
        author = calibre_meta.get('author', author)
        cover_image = calibre_meta.get('cover_image')

    # If we didn't get good metadata and it's an EPUB, try direct parsing
    if (title == file_path.stem or author == "Unknown Author") and file_path.suffix.lower() == '.epub':
        fallback = extract_epub_metadata_fallback(file_path)
        if title == file_path.stem and fallback.get('title'):
            title = fallback['title']
        if author == "Unknown Author" and fallback.get('author'):
            author = fallback['author']
        if not cover_image and fallback.get('cover_image'):
            cover_image = fallback['cover_image']

    return BookMetadata(
        title=title,
        author=author,
        cover_image=cover_image,
        file_path=file_path,
        file_size=get_file_size_str(file_path),
        format=file_path.suffix.upper().strip('.')
    )