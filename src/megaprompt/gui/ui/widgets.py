"""Custom PyQt6 widgets with rounded edges."""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from megaprompt.gui.ui.theme import COLORS, get_color


class RoundedFrame(QFrame):
    """Frame with rounded corners."""

    def __init__(self, parent=None, corner_radius: int = 10, bg_color: Optional[str] = None):
        super().__init__(parent)
        self.corner_radius = corner_radius
        self.bg_color = bg_color or COLORS["surface"]
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

    def paintEvent(self, event):
        """Paint rounded rectangle background."""
        from PyQt6.QtGui import QBrush, QColor

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.bg_color:
            painter.setBrush(QBrush(QColor(self.bg_color)))
        else:
            painter.setBrush(self.palette().color(self.backgroundRole()))
        painter.setPen(Qt.PenStyle.NoPen)
        rect = self.rect()
        painter.drawRoundedRect(rect, self.corner_radius, self.corner_radius)


class RoundedButton(QPushButton):
    """Button with rounded corners."""

    def __init__(self, text: str = "", parent=None, corner_radius: int = 8):
        super().__init__(text, parent)
        self.corner_radius = corner_radius


class RoundedLineEdit(QLineEdit):
    """Line edit with rounded corners."""

    def __init__(self, parent=None, corner_radius: int = 6):
        super().__init__(parent)
        self.corner_radius = corner_radius


class RoundedTextEdit(QTextEdit):
    """Text edit with rounded corners."""

    def __init__(self, parent=None, corner_radius: int = 6):
        super().__init__(parent)
        self.corner_radius = corner_radius


class CardWidget(QWidget):
    """Card-style widget container with rounded edges and shadow effect."""

    def __init__(self, parent=None, corner_radius: int = 10):
        super().__init__(parent)
        self.corner_radius = corner_radius
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(12)

    def add_widget(self, widget: QWidget) -> None:
        """Add widget to card."""
        self.layout.addWidget(widget)

    def paintEvent(self, event):
        """Paint card with rounded rectangle."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        from PyQt6.QtGui import QBrush, QColor

        bg_color = COLORS["surface"]
        if bg_color:
            painter.setBrush(QBrush(QColor(bg_color)))
        else:
            painter.setBrush(self.palette().color(self.backgroundRole()))
        painter.setPen(QPen(QColor(COLORS["border"]), 1))
        rect = self.rect().adjusted(0, 0, -1, -1)  # Adjust for border
        painter.drawRoundedRect(rect, self.corner_radius, self.corner_radius)


class SectionHeader(QWidget):
    """Section header widget with title and optional action buttons."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['primary']};")
        layout.addWidget(self.title_label)
        layout.addStretch()


class StatusLabel(QLabel):
    """Status label with color coding."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._status_type = "info"

    def set_status(self, status_type: str, message: str) -> None:
        """
        Set status with type and message.

        Args:
            status_type: 'success', 'error', 'warning', 'info'
            message: Status message
        """
        self._status_type = status_type
        color_map = {
            "success": COLORS["success"],
            "error": COLORS["error"],
            "warning": COLORS["warning"],
            "info": COLORS["text"],
        }
        color = color_map.get(status_type, COLORS["text"])
        self.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.setText(message)

