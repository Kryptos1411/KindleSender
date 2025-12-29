#!/usr/bin/env python3
"""Kindle Sender - Entry point."""
import sys
import os
from pathlib import Path

# === WINDOWS TASKBAR IDENTITY - MUST BE FIRST ===
if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('CCI.KindleSender.1')
    except Exception:
        pass


def get_resource_path(filename: str) -> Path:
    """Get path to a resource file."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / filename
    else:
        return Path(__file__).resolve().parent / filename


def set_window_icon(window):
    """Set both title bar and taskbar icons."""
    ico_path = get_resource_path("icon.ico")
    png_path = get_resource_path("icon.png")

    # Title bar icon (uses ICO)
    if ico_path.exists():
        try:
            window.iconbitmap(str(ico_path))
        except Exception as e:
            print(f"iconbitmap failed: {e}")

    # Taskbar icon (uses PNG via PhotoImage)
    try:
        from PIL import Image, ImageTk
        import tkinter as tk

        # Try PNG first, fall back to ICO
        if png_path.exists():
            img = Image.open(png_path)
        elif ico_path.exists():
            img = Image.open(ico_path)
        else:
            return

        # Resize for taskbar (Windows uses 32x32 for taskbar)
        img = img.resize((32, 32), Image.Resampling.LANCZOS)

        # Convert to PhotoImage
        photo = ImageTk.PhotoImage(img)

        # Set taskbar icon
        window.iconphoto(True, photo)

        # Keep reference to prevent garbage collection
        window._icon_photo = photo

    except Exception as e:
        print(f"iconphoto failed: {e}")


# Import CustomTkinter AFTER setting AppUserModelID
import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def main():
    from core.calibre_setup import is_ready, get_bundled_zip

    if is_ready():
        from ui.app import KindleSenderApp
        app = KindleSenderApp()
        set_window_icon(app)
        app.mainloop()

    elif get_bundled_zip().exists():
        from ui.launcher import Launcher
        launcher = Launcher()
        set_window_icon(launcher)
        launcher.mainloop()

    else:
        show_error()


def show_error():
    from ui.themes import THEME

    root = ctk.CTk()
    root.title("Kindle Sender - Error")
    root.geometry("400x150")
    root.configure(fg_color=THEME["bg_primary"])
    set_window_icon(root)

    ctk.CTkLabel(
        root,
        text="❌ calibre.zip not found",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color=THEME["text_primary"]
    ).pack(pady=30)

    ctk.CTkLabel(
        root,
        text="The application bundle is incomplete.",
        text_color=THEME["text_secondary"]
    ).pack()

    ctk.CTkButton(root, text="Exit", command=root.destroy).pack(pady=20)
    root.mainloop()


if __name__ == "__main__":
    main()