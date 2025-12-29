"""Book card component showing book info and progress."""
import customtkinter as ctk
from PIL import Image, ImageTk
from pathlib import Path
from typing import Callable, Optional
from core.task_manager import BookTask, TaskStatus
from ui.themes import THEME
import io


class BookCard(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        task: BookTask,
        on_remove: Callable[[str], None],
        **kwargs
    ):
        super().__init__(
            parent,
            fg_color=THEME["bg_card"],
            corner_radius=10,
            height=100,
            **kwargs
        )

        self.task = task
        self.on_remove = on_remove

        self.grid_columnconfigure(1, weight=1)
        self.grid_propagate(False)

        # Cover image
        self.cover_label = ctk.CTkLabel(
            self,
            text="",
            width=60,
            height=80,
            corner_radius=6,
            fg_color=THEME["bg_tertiary"]
        )
        self.cover_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10, sticky="nsw")
        self._set_cover_image(task.metadata.cover_image)

        # Info container
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=0, column=1, sticky="new", padx=(0, 10), pady=(10, 0))
        info_frame.grid_columnconfigure(0, weight=1)

        # Title
        self.title_label = ctk.CTkLabel(
            info_frame,
            text=task.metadata.display_title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w"
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        # Author and format info
        info_text = f"{task.metadata.author} • {task.metadata.file_size} • {task.metadata.format} → {task.output_format.upper()}"
        self.info_label = ctk.CTkLabel(
            info_frame,
            text=info_text,
            font=ctk.CTkFont(size=11),
            text_color=THEME["text_secondary"],
            anchor="w"
        )
        self.info_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Status and progress
        progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        progress_frame.grid(row=1, column=1, sticky="sew", padx=(0, 10), pady=(0, 10))
        progress_frame.grid_columnconfigure(0, weight=1)

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            height=6,
            corner_radius=3,
            fg_color=THEME["progress_bg"],
            progress_color=THEME["accent"]
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self.progress_bar.set(0)

        # Status text
        self.status_label = ctk.CTkLabel(
            progress_frame,
            text=self._get_status_text(),
            font=ctk.CTkFont(size=10),
            text_color=THEME["text_dim"],
            anchor="w"
        )
        self.status_label.grid(row=1, column=0, sticky="w")

        # Remove button
        self.remove_btn = ctk.CTkButton(
            self,
            text="✕",
            width=30,
            height=30,
            corner_radius=15,
            fg_color=THEME["bg_tertiary"],
            hover_color=THEME["error"],
            text_color=THEME["text_secondary"],
            font=ctk.CTkFont(size=14),
            command=lambda: self.on_remove(task.id)
        )
        self.remove_btn.grid(row=0, column=2, padx=10, pady=10, sticky="ne")

    def _set_cover_image(self, image: Optional[Image.Image]):
        """Set the cover image."""
        if image:
            # Resize to fit
            image = image.copy()
            image.thumbnail((60, 80), Image.Resampling.LANCZOS)
            ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(60, 80))
            self.cover_label.configure(image=ctk_image, text="")
        else:
            self.cover_label.configure(text="📖", font=ctk.CTkFont(size=32))

    def _get_status_text(self) -> str:
        status_map = {
            TaskStatus.QUEUED: "⏳ Waiting...",
            TaskStatus.CONVERTING: f"🔄 Converting... {self.task.progress:.0f}%",
            TaskStatus.CONVERTED: "✅ Converted - Ready to send",
            TaskStatus.TRANSFERRING: f"📤 Sending to Kindle... {self.task.progress:.0f}%",
            TaskStatus.COMPLETED: "✅ Done!",
            TaskStatus.FAILED: f"❌ Failed: {self.task.error_message[:30]}",
        }
        return status_map.get(self.task.status, "Unknown")

    def update_progress(self, progress: float, status: Optional[TaskStatus] = None):
        """Update progress bar and status."""
        self.task.progress = progress
        if status:
            self.task.status = status

        self.progress_bar.set(progress / 100)
        self.status_label.configure(text=self._get_status_text())

        # Color coding
        if self.task.status == TaskStatus.COMPLETED:
            self.progress_bar.configure(progress_color=THEME["success"])
        elif self.task.status == TaskStatus.FAILED:
            self.progress_bar.configure(progress_color=THEME["error"])

    def update_status(self, status: TaskStatus, error: str = ""):
        """Update task status."""
        self.task.status = status
        self.task.error_message = error
        self.status_label.configure(text=self._get_status_text())

        if status == TaskStatus.COMPLETED:
            self.progress_bar.configure(progress_color=THEME["success"])
            self.progress_bar.set(1.0)
        elif status == TaskStatus.FAILED:
            self.progress_bar.configure(progress_color=THEME["error"])