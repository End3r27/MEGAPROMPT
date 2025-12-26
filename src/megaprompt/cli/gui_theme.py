"""OLED theme configuration for CustomTkinter GUI."""

import customtkinter

# OLED Color Scheme
OLED_COLORS = {
    "background": "#000000",      # Pure black
    "surface": "#000000",         # Pure black surface
    "foreground": "#FFFFFF",      # Bright white text
    "primary": "#00FFFF",         # Bright cyan for selection/focus
    "secondary": "#00FF00",       # Bright green
    "warning": "#FFFF00",         # Bright yellow
    "error": "#FF0000",           # Bright red
    "success": "#00FF00",         # Bright green
    "accent": "#00FFFF",          # Bright cyan
    "border": "#333333",           # Dark gray for borders
    "text_muted": "#E0E0E0",      # Light gray for muted text
    "hover": "#00FFFF",           # Cyan on hover
    "button_bg": "#333333",       # Dark gray button background
    "button_hover": "#00FFFF",    # Cyan button hover
    "input_bg": "#1A1A1A",        # Slightly lighter black for inputs
}


def apply_oled_theme():
    """Apply OLED theme to CustomTkinter."""
    # Set appearance mode to dark
    customtkinter.set_appearance_mode("dark")
    
    # Set default color theme
    customtkinter.set_default_color_theme("blue")  # We'll override with custom colors
    
    # Configure custom color scheme
    # Note: CustomTkinter doesn't have a direct way to set all colors,
    # so we'll use CSS-like styling in the widgets themselves


def get_color(color_name: str) -> str:
    """Get a color from the OLED color scheme."""
    return OLED_COLORS.get(color_name, OLED_COLORS["foreground"])

