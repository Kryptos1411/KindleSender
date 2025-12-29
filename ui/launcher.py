"""Launcher that handles setup then transitions to main app."""
import sys
import customtkinter as ctk
from tkinterdnd2 import TkinterDnD
from pathlib import Path
from ui.themes import THEME
from core.calibre_setup import extract_async, is_ready


class Launcher(ctk.CTk, TkinterDnD.DnDWrapper):
    """Single window that shows setup, then becomes the main app."""

    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        self.title("Kindle Sender")
        self.geometry("450x200")
        self.resizable(False, False)
        self.configure(fg_color=THEME["bg_primary"])

        # Center on screen
        self._center_window(450, 200)

        # Prevent closing during setup
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._setup_complete = False

        # Build setup UI
        self._build_setup_ui()

        # Start extraction
        self.after(500, self._start_extraction)

    def _center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = max(0, (screen_height - height) // 2 - 40)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_setup_ui(self):
        """Build the setup screen UI."""
        self.setup_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.setup_frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            self.setup_frame,
            text="📚 First Run Setup",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=THEME["text_primary"]
        ).pack(pady=(30, 10))

        self.status_label = ctk.CTkLabel(
            self.setup_frame,
            text="Preparing conversion tools...",
            font=ctk.CTkFont(size=13),
            text_color=THEME["text_secondary"]
        )
        self.status_label.pack(pady=5)

        self.progress_bar = ctk.CTkProgressBar(
            self.setup_frame,
            width=350,
            height=10,
            corner_radius=5,
            fg_color=THEME["progress_bg"],
            progress_color=THEME["accent"]
        )
        self.progress_bar.pack(pady=15)
        self.progress_bar.set(0)

        self.hint_label = ctk.CTkLabel(
            self.setup_frame,
            text="This only happens once...",
            font=ctk.CTkFont(size=11),
            text_color=THEME["text_dim"]
        )
        self.hint_label.pack()

    def _on_close(self):
        """Handle window close."""
        if self._setup_complete:
            self.destroy()

    def _start_extraction(self):
        """Begin Calibre extraction."""
        extract_async(
            progress_callback=self._on_progress,
            on_complete=self._on_extraction_complete
        )

    def _on_progress(self, pct, msg):
        """Progress callback (from background thread)."""
        self.after(0, lambda: self._update_progress(pct, msg))

    def _update_progress(self, pct, msg):
        """Update progress UI (main thread)."""
        try:
            self.progress_bar.set(pct / 100)
            self.status_label.configure(text=msg)
        except Exception:
            pass

    def _on_extraction_complete(self, success, error):
        """Extraction finished (from background thread)."""
        self.after(0, lambda: self._handle_complete(success, error))

    def _handle_complete(self, success, error):
        """Handle extraction result (main thread)."""
        self._setup_complete = True

        if success and is_ready():
            self.status_label.configure(text="✓ Setup complete!")
            self.progress_bar.set(1.0)
            self.progress_bar.configure(progress_color=THEME["success"])
            self.hint_label.configure(text="Starting application...")
            self.after(800, self._transition_to_app)
        else:
            self.status_label.configure(
                text=f"✗ Setup failed: {error}",
                text_color=THEME["error"]
            )
            self.hint_label.configure(text="Please restart the application.")
            self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _transition_to_app(self):
        """Transform this window into the main app."""
        self.setup_frame.destroy()

        # Adaptive sizing based on screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        win_width = min(700, int(screen_width * 0.9))
        win_height = min(800, int(screen_height * 0.85))
        min_width = min(600, int(screen_width * 0.85))
        min_height = min(500, int(screen_height * 0.65))

        self.geometry(f"{win_width}x{win_height}")
        self.minsize(min_width, min_height)
        self.resizable(True, True)
        self._center_window(win_width, win_height)

        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._build_main_app()

    def _build_main_app(self):
        """Build the main application UI inside this window."""
        from core.converter import Converter
        from core.kindle import KindleManager
        from core.task_manager import TaskManager
        import config

        # Store references
        self.converter = Converter()
        self.kindle_manager = KindleManager()
        self.task_manager = TaskManager()
        self.output_format = config.DEFAULT_OUTPUT_FORMAT
        self.book_cards = {}

        # Build UI
        self._create_main_widgets()

        # Start Kindle monitoring
        self.kindle_manager.add_connection_callback(self._on_kindle_connection_change)
        self.kindle_manager.start_monitoring()
        self.task_manager.add_update_callback(self._refresh_task_list)

    def _create_main_widgets(self):
        """Build the main app UI."""
        from ui.components.drop_zone import DropZone
        from ui.components.kindle_status import KindleStatusBar
        from ui.components.format_selector import FormatSelector
        import config

        # === PACK BOTTOM BAR FIRST so it reserves space ===
        bottom_bar = ctk.CTkFrame(self, fg_color=THEME["bg_secondary"], height=65)
        bottom_bar.pack(fill="x", side="bottom")
        bottom_bar.pack_propagate(False)

        self.convert_all_btn = ctk.CTkButton(
            bottom_bar, text="⚡ Convert All", width=140, height=42, corner_radius=10,
            fg_color=THEME["accent"], hover_color=THEME["accent_hover"],
            font=ctk.CTkFont(size=14, weight="bold"), command=self._convert_all
        )
        self.convert_all_btn.pack(side="left", padx=20, pady=11)

        self.send_kindle_btn = ctk.CTkButton(
            bottom_bar, text="📲 Send to Kindle", width=150, height=42, corner_radius=10,
            fg_color=THEME["success"], hover_color=THEME["success_light"],
            text_color="#ffffff", text_color_disabled="#9ca3af",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._send_to_kindle, state="disabled"
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

        self.format_selector = FormatSelector(header, on_format_change=self._on_format_change)
        self.format_selector.grid(row=0, column=2, sticky="e")

        # Kindle status
        self.kindle_status = KindleStatusBar(self, on_refresh=self._refresh_kindle)
        self.kindle_status.pack(fill="x", padx=20, pady=8)

        # Drop zone (reduced height)
        self.drop_zone = DropZone(self, on_files_dropped=self._on_files_dropped, height=120)
        self.drop_zone.pack(fill="x", padx=20, pady=8)

        # Buttons row
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=8)

        ctk.CTkButton(
            btn_row, text="📁 Add Files", width=130, height=36, corner_radius=10,
            fg_color=THEME["bg_tertiary"], hover_color=THEME["bg_hover"],
            font=ctk.CTkFont(size=13), command=self._browse_files
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row, text="💾 Save to Folder", width=140, height=36, corner_radius=10,
            fg_color=THEME["bg_tertiary"], hover_color=THEME["bg_hover"],
            font=ctk.CTkFont(size=13), command=self._save_to_folder
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row, text="🗑 Clear Done", width=120, height=36, corner_radius=10,
            fg_color=THEME["bg_tertiary"], hover_color=THEME["bg_hover"],
            font=ctk.CTkFont(size=13), command=self._clear_completed
        ).pack(side="left")

        # Task list header
        list_header = ctk.CTkFrame(self, fg_color="transparent")
        list_header.pack(fill="x", padx=20, pady=(10, 5))

        ctk.CTkLabel(
            list_header, text="Books Queue",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=THEME["text_primary"]
        ).pack(side="left")

        self.task_count_label = ctk.CTkLabel(
            list_header, text="0 books",
            font=ctk.CTkFont(size=12), text_color=THEME["text_dim"]
        )
        self.task_count_label.pack(side="right")

        # Task list - PACKED LAST so it fills remaining space
        self.task_list_frame = ctk.CTkScrollableFrame(
            self, fg_color=THEME["bg_primary"], corner_radius=0
        )
        self.task_list_frame.pack(fill="both", expand=True, padx=20, pady=(8, 8))

        self.empty_label = ctk.CTkLabel(
            self.task_list_frame,
            text="No books added yet.\nDrag & drop files above or click 'Add Files'",
            font=ctk.CTkFont(size=14), text_color=THEME["text_dim"], justify="center"
        )
        self.empty_label.pack(pady=40)


    # --- Event Handlers ---

    def _on_format_change(self, fmt):
        self.output_format = fmt

    def _on_kindle_connection_change(self, device):
        self.after(0, lambda: self._update_kindle_ui(device))

    def _update_kindle_ui(self, device):
        self.kindle_status.update_status(device)
        self.send_kindle_btn.configure(state="normal" if device else "disabled")

    def _refresh_kindle(self):
        self.kindle_manager.scan()

    def _on_files_dropped(self, files):
        for f in files:
            self._add_book(f)

    def _browse_files(self):
        from tkinter import filedialog
        import config

        filetypes = [
            ("Ebook files", " ".join(f"*{ext}" for ext in config.INPUT_FORMATS)),
            ("All files", "*.*")
        ]
        files = filedialog.askopenfilenames(filetypes=filetypes)
        for f in files:
            self._add_book(Path(f))

    def _add_book(self, file_path):
        from core.metadata import extract_metadata
        from core.task_manager import BookTask

        metadata = extract_metadata(file_path)
        task = BookTask.create(metadata, self.output_format)
        self.task_manager.add_task(task)
        self._create_book_card(task)

    def _create_book_card(self, task):
        from ui.components.book_card import BookCard

        self.empty_label.pack_forget()

        card = BookCard(self.task_list_frame, task, on_remove=self._remove_task)
        card.pack(fill="x", pady=5)
        self.book_cards[task.id] = card
        self._update_task_count()

    def _remove_task(self, task_id):
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
        self.after(0, self._update_task_count)

    def _convert_all(self):
        from core.task_manager import TaskStatus

        pending = [t for t in self.task_manager.get_all_tasks() if t.status == TaskStatus.QUEUED]
        for task in pending:
            self._convert_task(task)

    def _convert_task(self, task, then_send=False):
        """Convert a single task."""
        from core.task_manager import TaskStatus

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

    def _transfer_task(self, task):
        """Transfer a converted book to Kindle."""
        from core.task_manager import TaskStatus

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

        # Get cover and mobi_asin for thumbnail creation (FIXED: use mobi_asin not book_uuid)
        cover_path = getattr(task, 'cover_path', None)
        mobi_asin = getattr(task, 'mobi_asin', None)

        try:
            self.kindle_manager.transfer_file_async(
                task.converted_path,
                cover_path=cover_path,
                mobi_asin=mobi_asin,  # FIXED: was book_uuid
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

    def _send_to_kindle(self):
        """Send books to Kindle - auto-converts if needed."""
        from core.task_manager import TaskStatus

        if not self.kindle_manager.is_connected:
            return

        for task in self.task_manager.get_all_tasks():
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

    def _save_to_folder(self):
        """Save converted files to a chosen folder."""
        from tkinter import filedialog
        from core.task_manager import TaskStatus
        import shutil

        folder = filedialog.askdirectory(title="Select destination folder")
        if not folder:
            return

        folder = Path(folder)

        for task in self.task_manager.get_all_tasks():
            if task.status == TaskStatus.CONVERTED and task.converted_path:
                dest = folder / task.converted_path.name
                shutil.copy2(task.converted_path, dest)
                task.status = TaskStatus.COMPLETED
                card = self.book_cards.get(task.id)
                if card:
                    card.update_progress(100, TaskStatus.COMPLETED)
                    card.update_status(TaskStatus.COMPLETED)

            elif task.status == TaskStatus.QUEUED:
                self._convert_and_save(task, folder)

    def _convert_and_save(self, task, folder):
        """Convert a task and save to folder."""
        from core.task_manager import TaskStatus
        import shutil

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
                            output_path = result.output_path
                            task.cover_path = getattr(result, 'cover_path', None)
                        else:
                            # Fallback for plain Path
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
        from core.task_manager import TaskStatus

        to_remove = [
            tid for tid, card in self.book_cards.items()
            if card.task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
        ]
        for tid in to_remove:
            self._remove_task(tid)