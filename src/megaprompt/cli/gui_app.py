"""Main CustomTkinter GUI application."""

import sys
import threading
import tkinter as tk
from pathlib import Path
from typing import Optional

import customtkinter
import pystray
from PIL import Image, ImageDraw

from megaprompt.cli.gui_theme import apply_oled_theme, get_color

from megaprompt.cli.gui_screens import (
    GenerateScreen,
    BatchScreen,
    ConfigScreen,
    CheckpointsScreen,
    CacheScreen,
    HelpScreen,
)


class MegaPromptGUI(customtkinter.CTk):
    """Main GUI application window."""
    
    def __init__(self):
        super().__init__()
        
        # Apply OLED theme
        apply_oled_theme()
        
        # Window configuration
        self.title("MEGAPROMPT - Interactive UI")
        self.geometry("1200x800")
        self.minsize(800, 600)
        
        # Configure window for rounded corners and transparency
        try:
            self.attributes("-alpha", 0.98)  # Slight transparency
        except:
            pass  # Not supported on all platforms
        
        # System tray
        self.tray_icon: Optional[pystray.Icon] = None
        self.tray_thread: Optional[threading.Thread] = None
        self.is_minimized_to_tray = False
        
        # Current screen
        self.current_screen: Optional[customtkinter.CTkFrame] = None
        
        # Setup UI
        self._setup_ui()
        
        # Setup system tray
        self._setup_system_tray()
        
        # Bind window events
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
    def _setup_ui(self):
        """Setup the main UI layout."""
        # Configure grid weights
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar navigation
        self.sidebar = customtkinter.CTkFrame(
            self,
            width=200,
            corner_radius=0,
            fg_color=get_color("surface"),
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(8, weight=1)
        
        # Logo/Title
        title_label = customtkinter.CTkLabel(
            self.sidebar,
            text="MEGAPROMPT",
            font=customtkinter.CTkFont(size=20, weight="bold"),
            text_color=get_color("primary"),
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Navigation buttons
        nav_buttons = [
            ("Generate", "generate", 1),
            ("Batch", "batch", 2),
            ("Config", "config", 3),
            ("Checkpoints", "checkpoints", 4),
            ("Cache", "cache", 5),
            ("Help", "help", 6),
        ]
        
        self.nav_buttons = {}
        for text, command, row in nav_buttons:
            btn = customtkinter.CTkButton(
                self.sidebar,
                text=text,
                command=lambda cmd=command: self._show_screen(cmd),
                fg_color=get_color("button_bg"),
                hover_color=get_color("button_hover"),
                text_color=get_color("foreground"),
                corner_radius=10,
                height=40,
            )
            btn.grid(row=row, column=0, padx=20, pady=5, sticky="ew")
            self.nav_buttons[command] = btn
        
        # Quit button
        quit_btn = customtkinter.CTkButton(
            self.sidebar,
            text="Quit",
            command=self._on_closing,
            fg_color=get_color("error"),
            hover_color="#CC0000",
            text_color=get_color("foreground"),
            corner_radius=10,
            height=40,
        )
        quit_btn.grid(row=9, column=0, padx=20, pady=10, sticky="ew")
        
        # Main content area
        self.content_frame = customtkinter.CTkFrame(
            self,
            corner_radius=0,
            fg_color=get_color("background"),
        )
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Show initial screen (Generate)
        self._show_screen("generate")
        
    def _show_screen(self, screen_name: str):
        """Show a specific screen."""
        # Hide current screen
        if self.current_screen:
            self.current_screen.grid_forget()
            self.current_screen.destroy()
        
        # Update button states
        for name, btn in self.nav_buttons.items():
            if name == screen_name:
                btn.configure(fg_color=get_color("primary"))
            else:
                btn.configure(fg_color=get_color("button_bg"))
        
        # Create and show new screen
        screen_classes = {
            "generate": GenerateScreen,
            "batch": BatchScreen,
            "config": ConfigScreen,
            "checkpoints": CheckpointsScreen,
            "cache": CacheScreen,
            "help": HelpScreen,
        }
        
        screen_class = screen_classes.get(screen_name)
        if screen_class:
            self.current_screen = screen_class(self.content_frame, app=self)
            self.current_screen.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        else:
            # Fallback: show message
            self.current_screen = customtkinter.CTkLabel(
                self.content_frame,
                text=f"Screen '{screen_name}' not implemented yet",
                font=customtkinter.CTkFont(size=16),
            )
            self.current_screen.grid(row=0, column=0, sticky="nsew")
    
    def _create_tray_icon(self) -> pystray.Icon:
        """Create system tray icon."""
        # Create a simple icon
        try:
            image = Image.new("RGB", (64, 64), color=get_color("background"))
            draw = ImageDraw.Draw(image)
            # Draw a simple "M" logo
            draw.text((20, 20), "M", fill=get_color("primary"))
        except Exception:
            # Fallback: create a simple colored square
            image = Image.new("RGB", (64, 64), color=get_color("primary"))
        
        menu = pystray.Menu(
            pystray.MenuItem("Show", self._show_window),
            pystray.MenuItem("Quit", self._quit_app),
        )
        
        icon = pystray.Icon("MEGAPROMPT", image, "MEGAPROMPT", menu)
        return icon
    
    def _setup_system_tray(self):
        """Setup system tray icon."""
        try:
            self.tray_icon = self._create_tray_icon()
            self.tray_thread = threading.Thread(
                target=self.tray_icon.run,
                daemon=True,
            )
            self.tray_thread.start()
        except Exception as e:
            print(f"Warning: Could not setup system tray: {e}")
    
    def _show_window(self, icon=None, item=None):
        """Show window from system tray."""
        self.deiconify()
        self.lift()
        self.focus_force()
        self.is_minimized_to_tray = False
    
    def _minimize_to_tray(self):
        """Minimize window to system tray."""
        if self.tray_icon:
            self.withdraw()
            self.is_minimized_to_tray = True
    
    def _quit_app(self, icon=None, item=None):
        """Quit the application."""
        if self.tray_icon:
            self.tray_icon.stop()
        self.quit()
        self.destroy()
    
    def _on_closing(self):
        """Handle window closing event."""
        # Ask for confirmation or minimize to tray
        if self.tray_icon:
            self._minimize_to_tray()
        else:
            self._quit_app()


def run_gui():
    """Run the GUI application."""
    app = MegaPromptGUI()
    app.mainloop()

