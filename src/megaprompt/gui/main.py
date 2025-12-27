"""Main entry point for the PyQt6 GUI application."""

import logging
import sys

from PyQt6.QtWidgets import QApplication

from megaprompt.gui.core.command import CommandManager
from megaprompt.gui.core.event_bus import EventBus
from megaprompt.gui.core.interface import MegaPromptCoreInterface
from megaprompt.gui.core.state import StateManager
from megaprompt.gui.ui.main_window import MainWindow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def run_gui() -> None:
    """Run the GUI application."""
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("MEGAPROMPT")
    app.setOrganizationName("MEGAPROMPT")

    try:
        # Initialize State Manager (load state)
        state_manager = StateManager()
        logger.info("State manager initialized")

        # Initialize Event Bus
        event_bus = EventBus()
        logger.info("Event bus initialized")

        # Initialize MEGAPROMPT Core Interface
        core_interface = MegaPromptCoreInterface()
        logger.info("Core interface initialized")

        # Initialize Command Manager
        command_manager = CommandManager(core_interface, event_bus)
        logger.info("Command manager initialized")

        # Create Main Window (applies theme from state)
        main_window = MainWindow(state_manager, event_bus, core_interface, command_manager)
        logger.info("Main window created")

        # Connect Event Bus subscribers (already done in MainWindow._connect_events)
        # Additional subscribers can be added here if needed

        # Show window (already done in MainWindow._restore_geometry)
        # main_window.show()  # Called in _restore_geometry

        # Run application
        logger.info("Starting application event loop")
        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Failed to start GUI application: {e}", exc_info=True)
        # Try to show error dialog if QApplication is available
        if QApplication.instance():
            from PyQt6.QtWidgets import QMessageBox

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Startup Error")
            msg.setText(f"Failed to start GUI application:\n{str(e)}")
            msg.exec()
        sys.exit(1)

