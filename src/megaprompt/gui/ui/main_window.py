"""Main application window."""

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import QPainter, QPainterPath, QRegion
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from megaprompt.gui.core.command import CommandManager
from megaprompt.gui.core.event_bus import EventBus, EVENT_ERROR, EVENT_PROGRESS_UPDATE, EVENT_PROMPT_COMPLETED
from megaprompt.gui.core.interface import MegaPromptCoreInterface
from megaprompt.gui.core.state import StateManager
from megaprompt.gui.ui.screens.analyze_screen import AnalyzeScreen
from megaprompt.gui.ui.screens.batch_screen import BatchScreen
from megaprompt.gui.ui.screens.cache_screen import CacheScreen
from megaprompt.gui.ui.screens.checkpoint_screen import CheckpointScreen
from megaprompt.gui.ui.screens.config_screen import ConfigScreen
from megaprompt.gui.ui.screens.generate_screen import GenerateScreen
from megaprompt.gui.ui.screens.help_screen import HelpScreen
from megaprompt.gui.ui.theme import apply_theme, get_color
from megaprompt.gui.ui.widgets import RoundedButton

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(
        self,
        state_manager: StateManager,
        event_bus: EventBus,
        core_interface: MegaPromptCoreInterface,
        command_manager: CommandManager,
    ):
        super().__init__()
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.core_interface = core_interface
        self.command_manager = command_manager

        # Window configuration
        self.setWindowTitle("MEGAPROMPT")
        self.setMinimumSize(800, 600)

        # Apply theme
        apply_theme(self)

        # Setup UI
        self._setup_ui()

        # Connect event bus subscribers
        self._connect_events()

        # Restore window geometry
        self._restore_geometry()

        # Current screen
        self.current_screen: Optional[str] = None

    def _setup_ui(self) -> None:
        """Setup the main UI layout."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar, 0)  # Fixed width

        # Content area
        content_area = self._create_content_area()
        main_layout.addWidget(content_area, 1)  # Stretch

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _create_sidebar(self) -> QWidget:
        """Create sidebar navigation."""
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(f"background-color: {get_color('surface')};")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(10)

        # Title
        title = QLabel("MEGAPROMPT")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {get_color('primary')}; padding: 10px;")
        layout.addWidget(title)

        layout.addStretch()

        # Navigation buttons
        self.nav_buttons = {}
        screens = [
            ("generate", "Generate"),
            ("batch", "Batch"),
            ("analyze", "Analyze"),
            ("config", "Config"),
            ("cache", "Cache"),
            ("checkpoint", "Checkpoints"),
            ("help", "Help"),
        ]

        for screen_id, screen_name in screens:
            btn = RoundedButton(screen_name)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked, sid=screen_id: self._show_screen(sid))
            self.nav_buttons[screen_id] = btn
            layout.addWidget(btn)

        layout.addStretch()

        return sidebar

    def _create_content_area(self) -> QWidget:
        """Create content area with stacked widgets."""
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # Stacked widget for screens
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)

        # Create screens
        self.screens = {}
        self.screens["generate"] = GenerateScreen(self, self.core_interface, self.command_manager, self.event_bus)
        self.screens["batch"] = BatchScreen(self)
        self.screens["analyze"] = AnalyzeScreen(self, self.core_interface, self.command_manager, self.event_bus)
        self.screens["config"] = ConfigScreen(self)
        self.screens["cache"] = CacheScreen(self)
        self.screens["checkpoint"] = CheckpointScreen(self)
        self.screens["help"] = HelpScreen(self)

        # Add screens to stacked widget
        for screen_id, screen in self.screens.items():
            self.stacked_widget.addWidget(screen)

        # Show generate screen by default
        self._show_screen("generate")

        return content_widget

    def _show_screen(self, screen_id: str) -> None:
        """Show a specific screen."""
        if screen_id not in self.screens:
            logger.warning(f"Screen {screen_id} not implemented yet")
            # Create placeholder screen
            placeholder = QWidget()
            layout = QVBoxLayout(placeholder)
            label = QLabel(f"Screen '{screen_id}' not implemented yet")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
            self.stacked_widget.addWidget(placeholder)
            self.screens[screen_id] = placeholder

        # Update button states
        for sid, btn in self.nav_buttons.items():
            if sid == screen_id:
                btn.setStyleSheet(f"background-color: {get_color('primary')}; color: {get_color('background')};")
            else:
                btn.setStyleSheet("")  # Use default theme

        # Show screen
        screen = self.screens[screen_id]
        index = self.stacked_widget.indexOf(screen)
        if index == -1:
            index = self.stacked_widget.addWidget(screen)
        self.stacked_widget.setCurrentIndex(index)
        self.current_screen = screen_id

    def _connect_events(self) -> None:
        """Connect event bus subscribers."""
        from megaprompt.gui.core.events import ErrorEvent, ProgressUpdateEvent, PromptCompletedEvent

        # Progress updates
        def on_progress_update(event: ProgressUpdateEvent):
            self.status_bar.showMessage(f"{event.stage}: {event.message}")
            if event.progress >= 0:
                # Update progress bar if we add one
                pass

        self.event_bus.subscribe(EVENT_PROGRESS_UPDATE, on_progress_update)

        # Errors
        def on_error(event: ErrorEvent):
            self.status_bar.showMessage(f"Error: {event.message}", 5000)
            logger.error(f"Error: {event.message}")

        self.event_bus.subscribe(EVENT_ERROR, on_error)

        # Prompt completed
        def on_prompt_completed(event: PromptCompletedEvent):
            if event.success:
                self.status_bar.showMessage("Prompt generation completed", 3000)
            else:
                self.status_bar.showMessage("Prompt generation failed", 3000)

        self.event_bus.subscribe(EVENT_PROMPT_COMPLETED, on_prompt_completed)

    def _restore_geometry(self) -> None:
        """Restore window geometry from state."""
        geometry = self.state_manager.get("window.geometry")
        if geometry and isinstance(geometry, list) and len(geometry) == 4:
            self.setGeometry(*geometry)

        maximized = self.state_manager.get("window.maximized", False)
        if maximized:
            self.showMaximized()
        else:
            self.show()

    def closeEvent(self, event):
        """Handle window close event."""
        # Save window geometry
        if not self.isMaximized():
            geometry = [self.x(), self.y(), self.width(), self.height()]
            self.state_manager.set("window.geometry", geometry)
        self.state_manager.set("window.maximized", self.isMaximized())
        self.state_manager.save()

        # Close event
        event.accept()

