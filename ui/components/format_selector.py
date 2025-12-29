"""Output format selector component."""
import customtkinter as ctk
from typing import Callable
import config
from ui.themes import THEME


class FormatSelector(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        on_format_change: Callable[[str], None],
        **kwargs
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.on_format_change = on_format_change
        self.selected_format = ctk.StringVar(value=config.DEFAULT_OUTPUT_FORMAT)

        # Label
        ctk.CTkLabel(
            self,
            text="Output Format:",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_secondary"]
        ).pack(side="left", padx=(0, 10))

        # Dropdown
        self.format_menu = ctk.CTkOptionMenu(
            self,
            values=[f.upper() for f in config.OUTPUT_FORMATS],
            variable=self.selected_format,
            command=self._on_change,
            width=100,
            height=32,
            corner_radius=8,
            fg_color=THEME["bg_tertiary"],
            button_color=THEME["bg_tertiary"],
            button_hover_color=THEME["bg_hover"],
            dropdown_fg_color=THEME["bg_secondary"],
            dropdown_hover_color=THEME["bg_hover"],
            font=ctk.CTkFont(size=12)
        )
        self.format_menu.pack(side="left")

    def _on_change(self, value: str):
        self.on_format_change(value.lower())

    def get_format(self) -> str:
        return self.selected_format.get().lower()