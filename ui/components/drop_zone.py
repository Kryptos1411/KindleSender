"""Drag and drop zone component."""
import customtkinter as ctk
from tkinterdnd2 import DND_FILES
from pathlib import Path
from typing import Callable, List
import config
from ui.themes import THEME


class DropZone(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        on_files_dropped: Callable[[List[Path]], None],
        **kwargs
    ):
        super().__init__(
            parent,
            fg_color=THEME["bg_tertiary"],
            corner_radius=12,
            border_width=2,
            border_color=THEME["border"],
            **kwargs
        )

        self.on_files_dropped = on_files_dropped
        self._is_hovering = False

        # Icon/emoji
        self.icon_label = ctk.CTkLabel(
            self,
            text="📚",
            font=ctk.CTkFont(size=48)
        )
        self.icon_label.pack(pady=(30, 10))

        # Main text
        self.text_label = ctk.CTkLabel(
            self,
            text="Drag & Drop Books Here",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=THEME["text_primary"]
        )
        self.text_label.pack(pady=(0, 5))

        # Subtext
        formats = ", ".join(config.INPUT_FORMATS[:5]) + "..."
        self.subtext_label = ctk.CTkLabel(
            self,
            text=f"Supports {formats}",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_dim"]
        )
        self.subtext_label.pack(pady=(0, 30))

        # Set up drag and drop
        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self._on_drop)
        self.dnd_bind("<<DragEnter>>", self._on_drag_enter)
        self.dnd_bind("<<DragLeave>>", self._on_drag_leave)

    def _on_drop(self, event):
        """Handle dropped files."""
        self._on_drag_leave(None)

        # Parse file paths (handles spaces in names)
        data = event.data
        files = []

        # Windows wraps paths with spaces in braces
        if '{' in data:
            import re
            files = re.findall(r'\{([^}]+)\}|(\S+)', data)
            files = [f[0] or f[1] for f in files]
        else:
            files = data.split()

        # Filter for supported formats
        valid_files = []
        for f in files:
            path = Path(f)
            if path.suffix.lower() in config.INPUT_FORMATS:
                valid_files.append(path)

        if valid_files:
            self.on_files_dropped(valid_files)

    def _on_drag_enter(self, event):
        """Visual feedback when dragging over."""
        self._is_hovering = True
        self.configure(
            border_color=THEME["accent"],
            fg_color=THEME["bg_hover"]
        )
        self.text_label.configure(text="Drop to Add!")

    def _on_drag_leave(self, event):
        """Reset visual state."""
        self._is_hovering = False
        self.configure(
            border_color=THEME["border"],
            fg_color=THEME["bg_tertiary"]
        )
        self.text_label.configure(text="Drag & Drop Books Here")