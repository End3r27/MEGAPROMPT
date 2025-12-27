"""UI Framework & Theming - Dark theme with vibrant red/green/yellow colors."""

from typing import Optional

# Vibrant color scheme (red, green, yellow) with dark theme
COLORS = {
    "background": "#1a1a1a",      # Dark background
    "surface": "#2a2a2a",         # Surface color
    "primary": "#00ff00",         # Green (vibrant)
    "secondary": "#ffff00",       # Yellow (vibrant)
    "accent": "#ff0000",          # Red (vibrant)
    "text": "#ffffff",            # White text
    "text_muted": "#cccccc",      # Muted text
    "border": "#404040",          # Border color
    "button_bg": "#333333",       # Button background
    "button_hover": "#00ff00",    # Button hover (green)
    "input_bg": "#252525",        # Input background
    "selection": "#00ff00",       # Selection color (green)
    "error": "#ff0000",           # Error color (red)
    "success": "#00ff00",         # Success color (green)
    "warning": "#ffff00",         # Warning color (yellow)
}


def get_color(color_name: str) -> str:
    """
    Get a color from the theme.

    Args:
        color_name: Color name from COLORS dictionary

    Returns:
        Hex color string
    """
    return COLORS.get(color_name, COLORS["text"])


def get_stylesheet() -> str:
    """
    Get QStyleSheet for dark theme.

    Returns:
        QStyleSheet string
    """
    bg = COLORS["background"]
    surface = COLORS["surface"]
    text = COLORS["text"]
    text_muted = COLORS["text_muted"]
    primary = COLORS["primary"]
    secondary = COLORS["secondary"]
    accent = COLORS["accent"]
    border = COLORS["border"]
    button_bg = COLORS["button_bg"]
    input_bg = COLORS["input_bg"]

    return f"""
    /* Main window */
    QMainWindow {{
        background-color: {bg};
        color: {text};
    }}
    
    /* QWidget base */
    QWidget {{
        background-color: {bg};
        color: {text};
        font-family: system-ui, -apple-system, sans-serif;
    }}
    
    /* Buttons */
    QPushButton {{
        background-color: {button_bg};
        color: {text};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 14px;
    }}
    
    QPushButton:hover {{
        background-color: {primary};
        color: {bg};
        border-color: {primary};
    }}
    
    QPushButton:pressed {{
        background-color: {accent};
        border-color: {accent};
    }}
    
    QPushButton:disabled {{
        background-color: {surface};
        color: {text_muted};
        border-color: {border};
    }}
    
    /* Line edits */
    QLineEdit {{
        background-color: {input_bg};
        color: {text};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 8px;
        font-size: 14px;
    }}
    
    QLineEdit:focus {{
        border-color: {primary};
        border-width: 2px;
    }}
    
    /* Text edits */
    QTextEdit {{
        background-color: {input_bg};
        color: {text};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 8px;
        font-size: 14px;
    }}
    
    QTextEdit:focus {{
        border-color: {primary};
        border-width: 2px;
    }}
    
    /* Labels */
    QLabel {{
        color: {text};
        background-color: transparent;
    }}
    
    /* Scroll bars */
    QScrollBar:vertical {{
        background-color: {surface};
        width: 12px;
        border-radius: 6px;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {border};
        border-radius: 6px;
        min-height: 20px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {primary};
    }}
    
    QScrollBar:horizontal {{
        background-color: {surface};
        height: 12px;
        border-radius: 6px;
    }}
    
    QScrollBar::handle:horizontal {{
        background-color: {border};
        border-radius: 6px;
        min-width: 20px;
    }}
    
    QScrollBar::handle:horizontal:hover {{
        background-color: {primary};
    }}
    
    /* List widgets */
    QListWidget {{
        background-color: {surface};
        color: {text};
        border: 1px solid {border};
        border-radius: 6px;
    }}
    
    QListWidget::item {{
        padding: 8px;
        border-bottom: 1px solid {border};
    }}
    
    QListWidget::item:selected {{
        background-color: {primary};
        color: {bg};
    }}
    
    /* Combo boxes */
    QComboBox {{
        background-color: {input_bg};
        color: {text};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 8px;
        font-size: 14px;
    }}
    
    QComboBox:focus {{
        border-color: {primary};
        border-width: 2px;
    }}
    
    QComboBox::drop-down {{
        border: none;
    }}
    
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid {text};
        width: 0;
        height: 0;
    }}
    
    /* Progress bars */
    QProgressBar {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: 6px;
        text-align: center;
        color: {text};
        height: 24px;
    }}
    
    QProgressBar::chunk {{
        background-color: {primary};
        border-radius: 5px;
    }}
    
    /* Check boxes */
    QCheckBox {{
        color: {text};
        spacing: 8px;
    }}
    
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {border};
        border-radius: 3px;
        background-color: {input_bg};
    }}
    
    QCheckBox::indicator:checked {{
        background-color: {primary};
        border-color: {primary};
    }}
    
    /* Radio buttons */
    QRadioButton {{
        color: {text};
        spacing: 8px;
    }}
    
    QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {border};
        border-radius: 9px;
        background-color: {input_bg};
    }}
    
    QRadioButton::indicator:checked {{
        background-color: {primary};
        border-color: {primary};
    }}
    
    /* Group boxes */
    QGroupBox {{
        border: 1px solid {border};
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 12px;
        color: {text};
        font-weight: bold;
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        background-color: {bg};
    }}
    
    /* Tabs */
    QTabWidget::pane {{
        border: 1px solid {border};
        border-radius: 6px;
        background-color: {surface};
    }}
    
    QTabBar::tab {{
        background-color: {button_bg};
        color: {text};
        border: 1px solid {border};
        border-bottom: none;
        padding: 8px 16px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }}
    
    QTabBar::tab:selected {{
        background-color: {primary};
        color: {bg};
    }}
    
    QTabBar::tab:hover {{
        background-color: {surface};
    }}
    """


def apply_theme(widget) -> None:
    """
    Apply theme to a widget.

    Args:
        widget: QWidget or QApplication to apply theme to
    """
    stylesheet = get_stylesheet()
    widget.setStyleSheet(stylesheet)

