"""Kindle connection status bar component."""
import customtkinter as ctk
from typing import Optional, Callable
from ui.themes import THEME


class KindleStatusBar(ctk.CTkFrame):
    """Shows Kindle connection status."""

    def __init__(self, parent, on_refresh: Optional[Callable] = None, **kwargs):
        super().__init__(parent, fg_color=THEME["bg_secondary"], corner_radius=12, height=50, **kwargs)
        self.pack_propagate(False)

        self.on_refresh = on_refresh

        # Status indicator
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(side="left", padx=15, pady=10)

        self.status_dot = ctk.CTkLabel(
            self.status_frame,
            text="●",
            font=ctk.CTkFont(size=16),
            text_color=THEME["error"]
        )
        self.status_dot.pack(side="left", padx=(0, 8))

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Kindle not connected",
            font=ctk.CTkFont(size=13),
            text_color=THEME["text_secondary"]
        )
        self.status_label.pack(side="left")

        # Device info (right side)
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.pack(side="right", padx=15, pady=10)

        self.space_label = ctk.CTkLabel(
            self.info_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_dim"]
        )
        self.space_label.pack(side="left", padx=(0, 10))

        self.refresh_btn = ctk.CTkButton(
            self.info_frame,
            text="↻",
            width=30,
            height=30,
            corner_radius=8,
            fg_color=THEME["bg_tertiary"],
            hover_color=THEME["bg_hover"],
            font=ctk.CTkFont(size=14),
            command=self._on_refresh_click
        )
        self.refresh_btn.pack(side="left")

    def _on_refresh_click(self):
        if self.on_refresh:
            self.on_refresh()

    def update_status(self, device):
        """Update the status display based on device connection."""
        if device:
            self.status_dot.configure(text_color=THEME["success"])
            self.status_label.configure(
                text=f"{device.name} connected",
                text_color=THEME["text_primary"]
            )
            self.space_label.configure(text=f"Free: {device.free_space}")
        else:
            self.status_dot.configure(text_color=THEME["error"])
            self.status_label.configure(
                text="Kindle not connected",
                text_color=THEME["text_secondary"]
            )
            self.space_label.configure(text="")