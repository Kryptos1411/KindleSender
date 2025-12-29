"""Main application window."""
import customtkinter as ctk
from tkinterdnd2 import TkinterDnD
from tkinter import filedialog
from pathlib import Path
from typing import List

from ui.themes import THEME
from ui.components.drop_zone import DropZone
from ui.components.book_card import BookCard
from ui.components.kindle_status import KindleStatusBar
from ui.components.format_selector import FormatSelector

from core.metadata import extract_metadata
from core.converter import Converter
from core.kindle import KindleManager
from core.task_manager import TaskManager, BookTask, TaskStatus
import config


class KindleSenderApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        # Window setup
        self.title("Kindle Sender")
        self.configure(fg_color=THEME["bg_primary"])
        self._set_icon()

        # Adaptive sizing based on screen
        self._configure_window_size()

        # Core components
        self.converter = Converter()
        self.kindle_manager = KindleManager()
        self.task_manager = TaskManager()

        self.output_format = config.DEFAULT_OUTPUT_FORMAT
        self.book_cards: dict[str, BookCard] = {}

        # Build UI
        self._create_widgets()

        # Start Kindle monitoring
        self.kindle_manager.add_connection_callback(self._on_kindle_connection_change)
        self.kindle_manager.start_monitoring()

        # Task manager updates
        self.task_manager.add_update_callback(self._refresh_task_list)

    def _configure_window_size(self):
        """Configure window size adaptively based on screen dimensions."""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Target 700x800, but cap at 90% of screen size
        win_width = min(700, int(screen_width * 0.9))
        win_height = min(800, int(screen_height * 0.85))  # Leave room for taskbar

        # Minimum size also needs to be adaptive
        min_width = min(600, int(screen_width * 0.85))
        min_height = min(500, int(screen_height * 0.65))

        # Center on screen
        x = (screen_width - win_width) // 2
        y = max(0, (screen_height - win_height) // 2 - 40)  # Slight upward bias

        self.geometry(f"{win_width}x{win_height}+{x}+{y}")
        self.minsize(min_width, min_height)

    def _set_icon(self):
        """Set the window icon."""
        import sys
        from pathlib import Path

        if getattr(sys, 'frozen', False):
            # Running as EXE - icon is embedded
            pass  # Windows uses exe icon automatically
        else:
            # Running as script - try to load icon file
            icon_path = Path(__file__).parent.parent / "icon.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))

    def _create_widgets(self):
        """Build the UI."""
        # === PACK BOTTOM BAR FIRST so it reserves space ===
        bottom_bar = ctk.CTkFrame(self, fg_color=THEME["bg_secondary"], height=65)
        bottom_bar.pack(fill="x", side="bottom")
        bottom_bar.pack_propagate(False)

        self.convert_all_btn = ctk.CTkButton(
            bottom_bar,
            text="⚡ Convert All",
            width=140,
            height=42,
            corner_radius=10,
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._convert_all
        )
        self.convert_all_btn.pack(side="left", padx=20, pady=11)

        self.send_kindle_btn = ctk.CTkButton(
            bottom_bar,
            text="📲 Send to Kindle",
            width=150,
            height=42,
            corner_radius=10,
            fg_color=THEME["success"],
            hover_color=THEME["success_light"],
            text_color="#ffffff",
            text_color_disabled="#9ca3af",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._send_to_kindle,
            state="disabled"
        )
        self.send_kindle_btn.pack(side="right", padx=20, pady=11)

        # === NOW PACK EVERYTHING ELSE FROM TOP DOWN ===
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent", height=60)
        header.pack(fill="x", padx=20, pady=(15, 8))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text="📱 Kindle Sender",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=THEME["text_primary"]
        ).grid(row=0, column=0, sticky="w")

        # Format selector (right side of header)
        self.format_selector = FormatSelector(
            header,
            on_format_change=self._on_format_change
        )
        self.format_selector.grid(row=0, column=2, sticky="e")

        # Kindle status bar
        self.kindle_status = KindleStatusBar(
            self,
            on_refresh=self._refresh_kindle
        )
        self.kindle_status.pack(fill="x", padx=20, pady=8)

        # Drop zone (reduced height for smaller screens)
        self.drop_zone = DropZone(
            self,
            on_files_dropped=self._on_files_dropped,
            height=120
        )
        self.drop_zone.pack(fill="x", padx=20, pady=8)

        # Action buttons row
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=8)

        self.add_files_btn = ctk.CTkButton(
            btn_row,
            text="📁 Add Files",
            width=130,
            height=36,
            corner_radius=10,
            fg_color=THEME["bg_tertiary"],
            hover_color=THEME["bg_hover"],
            font=ctk.CTkFont(size=13),
            command=self._browse_files
        )
        self.add_files_btn.pack(side="left", padx=(0, 10))

        self.save_folder_btn = ctk.CTkButton(
            btn_row,
            text="💾 Save to Folder",
            width=140,
            height=36,
            corner_radius=10,
            fg_color=THEME["bg_tertiary"],
            hover_color=THEME["bg_hover"],
            font=ctk.CTkFont(size=13),
            command=self._save_to_folder
        )
        self.save_folder_btn.pack(side="left", padx=(0, 10))

        self.clear_btn = ctk.CTkButton(
            btn_row,
            text="🗑 Clear Done",
            width=120,
            height=36,
            corner_radius=10,
            fg_color=THEME["bg_tertiary"],
            hover_color=THEME["bg_hover"],
            font=ctk.CTkFont(size=13),
            command=self._clear_completed
        )
        self.clear_btn.pack(side="left")

        # Task list label
        list_header = ctk.CTkFrame(self, fg_color="transparent")
        list_header.pack(fill="x", padx=20, pady=(10, 5))

        ctk.CTkLabel(
            list_header,
            text="Books Queue",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=THEME["text_primary"]
        ).pack(side="left")

        self.task_count_label = ctk.CTkLabel(
            list_header,
            text="0 books",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_dim"]
        )
        self.task_count_label.pack(side="right")

        # Scrollable task list - PACKED LAST so it fills remaining space
        self.task_list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=THEME["bg_primary"],
            corner_radius=0
        )
        self.task_list_frame.pack(fill="both", expand=True, padx=20, pady=(8, 8))

        # Empty state
        self.empty_label = ctk.CTkLabel(
            self.task_list_frame,
            text="No books added yet.\nDrag & drop files above or click 'Add Files'",
            font=ctk.CTkFont(size=14),
            text_color=THEME["text_dim"],
            justify="center"
        )
        self.empty_label.pack(pady=40)

    def _on_format_change(self, format: str):
        self.output_format = format

    def _on_kindle_connection_change(self, device):
        """Called when Kindle connection state changes."""
        self.after(0, lambda: self._update_kindle_ui(device))

    def _update_kindle_ui(self, device):
        self.kindle_status.update_status(device)
        if device:
            self.send_kindle_btn.configure(state="normal")
        else:
            self.send_kindle_btn.configure(state="disabled")

    def _refresh_kindle(self):
        self.kindle_manager.scan()

    def _on_files_dropped(self, files: List[Path]):
        """Handle dropped files."""
        for file_path in files:
            self._add_book(file_path)

    def _browse_files(self):
        """Open file browser."""
        filetypes = [
            ("Ebook files", " ".join(f"*{ext}" for ext in config.INPUT_FORMATS)),
            ("All files", "*.*")
        ]
        files = filedialog.askopenfilenames(filetypes=filetypes)
        for f in files:
            self._add_book(Path(f))

    def _add_book(self, file_path: Path):
        """Add a book to the queue."""
        metadata = extract_metadata(file_path)
        task = BookTask.create(metadata, self.output_format)
        self.task_manager.add_task(task)
        self._create_book_card(task)

    def _create_book_card(self, task: BookTask):
        """Create a book card widget."""
        self.empty_label.pack_forget()

        card = BookCard(
            self.task_list_frame,
            task,
            on_remove=self._remove_task
        )
        card.pack(fill="x", pady=5)
        self.book_cards[task.id] = card

        self._update_task_count()

    def _remove_task(self, task_id: str):
        """Remove a task from the queue."""
        if task_id in self.book_cards:
            self.book_cards[task_id].destroy()
            del self.book_cards[task_id]
        self.task_manager.remove_task(task_id)
        self._update_task_count()

        if not self.book_cards:
            self.empty_label.pack(pady=40)

    def _update_task_count(self):
        count = len(self.task_manager.tasks)
        self.task_count_label.configure(text=f"{count} book{'s' if count != 1 else ''}")

    def _refresh_task_list(self):
        """Refresh the task list UI."""
        self.after(0, self._update_task_count)

    def _convert_all(self):
        """Start converting all pending books."""
        tasks = self.task_manager.get_all_tasks()
        pending = [t for t in tasks if t.status == TaskStatus.QUEUED]

        for task in pending:
            self._convert_task(task)

    def _convert_task(self, task: BookTask, then_send: bool = False):
        """Convert a single task."""
        card = self.book_cards.get(task.id)
        if not card:
            return

        def on_progress(progress, message):
            self.after(0, lambda: card.update_progress(progress, TaskStatus.CONVERTING))

        def on_complete(result, error):
            def update():
                try:
                    if error:
                        task.status = TaskStatus.FAILED
                        task.error_message = str(error)
                        card.update_status(TaskStatus.FAILED, str(error))
                    else:
                        # Handle ConversionResult object
                        if hasattr(result, 'output_path'):
                            task.converted_path = result.output_path
                            task.cover_path = getattr(result, 'cover_path', None)
                            task.mobi_asin = getattr(result, 'mobi_asin', None)
                        else:
                            # Fallback for plain Path
                            task.converted_path = Path(result) if result else None
                            task.cover_path = None
                            task.mobi_asin = None

                        task.status = TaskStatus.CONVERTED
                        card.update_progress(100, TaskStatus.CONVERTED)
                        card.update_status(TaskStatus.CONVERTED)

                        if then_send and self.kindle_manager.is_connected:
                            self._transfer_task(task)
                except Exception as e:
                    print(f"Error in conversion completion handler: {e}")
                    import traceback
                    traceback.print_exc()
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                    card.update_status(TaskStatus.FAILED, str(e))

            self.after(0, update)

        task.status = TaskStatus.CONVERTING
        card.update_status(TaskStatus.CONVERTING)
        card.update_progress(0, TaskStatus.CONVERTING)

        output_format = "azw3" if then_send else self.output_format

        self.converter.convert_async(
            task.metadata.file_path,
            output_format,
            progress_callback=on_progress,
            completion_callback=on_complete
        )

    def _send_to_kindle(self):
        """Send books to Kindle - auto-converts if needed."""
        if not self.kindle_manager.is_connected:
            return

        tasks = self.task_manager.get_all_tasks()

        for task in tasks:
            if task.status == TaskStatus.COMPLETED:
                continue
            elif task.status == TaskStatus.CONVERTED and task.converted_path:
                if task.converted_path.suffix.lower() == '.azw3':
                    self._transfer_task(task)
                else:
                    # Need to re-convert to AZW3
                    task.status = TaskStatus.QUEUED
                    self._convert_task(task, then_send=True)
            elif task.status == TaskStatus.QUEUED:
                self._convert_task(task, then_send=True)

    def _transfer_task(self, task: BookTask):
        """Transfer a converted book to Kindle."""
        card = self.book_cards.get(task.id)
        if not card:
            return

        def on_progress(progress):
            self.after(0, lambda: card.update_progress(progress, TaskStatus.TRANSFERRING))

        def on_complete(success, error):
            def update():
                try:
                    if error:
                        task.status = TaskStatus.FAILED
                        task.error_message = str(error)
                        card.update_status(TaskStatus.FAILED, str(error))
                    else:
                        task.status = TaskStatus.COMPLETED
                        card.update_progress(100, TaskStatus.COMPLETED)
                        card.update_status(TaskStatus.COMPLETED)
                except Exception as e:
                    print(f"Error in transfer completion handler: {e}")
                    task.status = TaskStatus.FAILED
                    card.update_status(TaskStatus.FAILED, str(e))

            self.after(0, update)

        task.status = TaskStatus.TRANSFERRING
        card.update_status(TaskStatus.TRANSFERRING)

        # Get cover and mobi_asin for thumbnail creation
        cover_path = getattr(task, 'cover_path', None)
        mobi_asin = getattr(task, 'mobi_asin', None)

        try:
            self.kindle_manager.transfer_file_async(
                task.converted_path,
                cover_path=cover_path,
                mobi_asin=mobi_asin,
                progress_callback=on_progress,
                completion_callback=on_complete
            )
        except Exception as e:
            print(f"Failed to start transfer: {e}")
            import traceback
            traceback.print_exc()
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            card.update_status(TaskStatus.FAILED, str(e))

    def _save_to_folder(self):
        """Save converted files to a chosen folder."""
        folder = filedialog.askdirectory(title="Select destination folder")
        if not folder:
            return

        folder = Path(folder)
        tasks = self.task_manager.get_all_tasks()

        for task in tasks:
            if task.status == TaskStatus.CONVERTED and task.converted_path:
                import shutil
                dest = folder / task.converted_path.name
                shutil.copy2(task.converted_path, dest)

                task.status = TaskStatus.COMPLETED
                card = self.book_cards.get(task.id)
                if card:
                    card.update_progress(100, TaskStatus.COMPLETED)
                    card.update_status(TaskStatus.COMPLETED)

            elif task.status == TaskStatus.QUEUED:
                self._convert_and_save(task, folder)

    def _convert_and_save(self, task: BookTask, folder: Path):
        """Convert a task and save to folder."""
        card = self.book_cards.get(task.id)
        if not card:
            return

        def on_progress(progress, message):
            self.after(0, lambda: card.update_progress(progress, TaskStatus.CONVERTING))

        def on_complete(result, error):
            def update():
                try:
                    if error:
                        task.status = TaskStatus.FAILED
                        task.error_message = str(error)
                        card.update_status(TaskStatus.FAILED, str(error))
                    else:
                        import shutil

                        # Handle ConversionResult object
                        if hasattr(result, 'output_path'):
                            output_path = result.output_path
                            task.cover_path = getattr(result, 'cover_path', None)
                        else:
                            output_path = Path(result) if result else None
                            task.cover_path = None

                        if output_path and output_path.exists():
                            dest = folder / output_path.name
                            shutil.copy2(output_path, dest)
                            task.converted_path = output_path
                            task.status = TaskStatus.COMPLETED
                            card.update_progress(100, TaskStatus.COMPLETED)
                            card.update_status(TaskStatus.COMPLETED)
                        else:
                            task.status = TaskStatus.FAILED
                            task.error_message = "Output file not found"
                            card.update_status(TaskStatus.FAILED, "Output file not found")
                except Exception as e:
                    print(f"Error in save completion handler: {e}")
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                    card.update_status(TaskStatus.FAILED, str(e))

            self.after(0, update)

        task.status = TaskStatus.CONVERTING
        card.update_status(TaskStatus.CONVERTING)
        card.update_progress(0, TaskStatus.CONVERTING)

        self.converter.convert_async(
            task.metadata.file_path,
            self.output_format,
            progress_callback=on_progress,
            completion_callback=on_complete
        )

    def _clear_completed(self):
        """Remove completed tasks from the list."""
        to_remove = [
            task_id for task_id, card in self.book_cards.items()
            if card.task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
        ]
        for task_id in to_remove:
            self._remove_task(task_id)