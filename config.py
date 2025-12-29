"""Application configuration."""
from pathlib import Path

# Supported formats
INPUT_FORMATS = [".epub", ".mobi", ".azw", ".azw3", ".pdf", ".txt", ".html", ".docx", ".rtf", ".fb2"]
OUTPUT_FORMATS = ["azw3", "mobi", "epub", "pdf", "txt"]
DEFAULT_OUTPUT_FORMAT = "azw3"

# Temp directory for conversions
TEMP_DIR = Path.home() / ".kindle_sender" / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)