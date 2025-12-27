"""Codebase analysis screen."""

import logging
from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget

from megaprompt.gui.core.command import AnalyzeCodebaseCommand, CommandManager
from megaprompt.gui.core.event_bus import EventBus, EVENT_COMMAND_FINISHED
from megaprompt.gui.core.interface import MegaPromptCoreInterface
from megaprompt.gui.ui.theme import get_color
from megaprompt.gui.ui.widgets import CardWidget, RoundedButton, RoundedLineEdit, RoundedTextEdit, SectionHeader

logger = logging.getLogger(__name__)


class AnalyzeScreen(QWidget):
    """Screen for codebase analysis."""

    def __init__(
        self,
        parent: QWidget,
        core_interface: MegaPromptCoreInterface,
        command_manager: CommandManager,
        event_bus: EventBus,
    ):
        super().__init__(parent)
        self.core_interface = core_interface
        self.command_manager = command_manager
        self.event_bus = event_bus
        self._current_command_id = None
        self._setup_ui()
        self._connect_events()

    def _setup_ui(self) -> None:
        """Setup the analyze screen UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Title
        header = SectionHeader("Codebase Analysis")
        layout.addWidget(header)

        # Path selection
        path_card = CardWidget()
        path_layout = QVBoxLayout()
        path_card.layout.addLayout(path_layout)

        path_label = QLabel("Codebase Path:")
        path_label.setStyleSheet(f"font-weight: bold; color: {get_color('text')};")
        path_layout.addWidget(path_label)

        path_input_layout = QHBoxLayout()
        self.path_entry = RoundedLineEdit()
        self.path_entry.setPlaceholderText("Enter path to codebase directory or click Browse...")
        path_input_layout.addWidget(self.path_entry)

        browse_btn = RoundedButton("Browse...")
        browse_btn.clicked.connect(self._browse_directory)
        path_input_layout.addWidget(browse_btn)

        path_layout.addLayout(path_input_layout)

        layout.addWidget(path_card)

        # Output
        output_card = CardWidget()
        output_layout = QVBoxLayout()
        output_card.layout.addLayout(output_layout)

        output_label = QLabel("Analysis Results:")
        output_label.setStyleSheet(f"font-weight: bold; color: {get_color('text')};")
        output_layout.addWidget(output_label)

        self.output_text = RoundedTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(300)
        output_layout.addWidget(self.output_text)

        # Output buttons
        output_buttons = QHBoxLayout()
        save_btn = RoundedButton("Save Results")
        save_btn.clicked.connect(self._save_results)
        output_buttons.addWidget(save_btn)
        output_buttons.addStretch()
        output_layout.addLayout(output_buttons)

        layout.addWidget(output_card)

        # Action buttons
        action_buttons = QHBoxLayout()
        self.analyze_btn = RoundedButton("Analyze")
        self.analyze_btn.setStyleSheet(f"background-color: {get_color('primary')}; font-size: 16px; padding: 12px;")
        self.analyze_btn.clicked.connect(self._analyze)
        action_buttons.addWidget(self.analyze_btn)

        self.cancel_btn = RoundedButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel)
        action_buttons.addWidget(self.cancel_btn)
        action_buttons.addStretch()

        layout.addLayout(action_buttons)
        layout.addStretch()

    def _connect_events(self) -> None:
        """Connect to event bus."""
        from megaprompt.gui.core.events import CommandFinishedEvent

        def on_command_finished(event: CommandFinishedEvent):
            if event.command_type == "analyze_codebase":
                self._on_analysis_finished(event.success, event.result, event.error)

        self.event_bus.subscribe(EVENT_COMMAND_FINISHED, on_command_finished)

    def _browse_directory(self) -> None:
        """Browse for codebase directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Codebase Directory")
        if directory:
            self.path_entry.setText(directory)

    def _analyze(self) -> None:
        """Analyze codebase."""
        codebase_path = self.path_entry.text().strip()
        if not codebase_path:
            QMessageBox.warning(self, "Warning", "Please enter a codebase path")
            return

        path = Path(codebase_path)
        if not path.exists() or not path.is_dir():
            QMessageBox.warning(self, "Warning", "Path does not exist or is not a directory")
            return

        # Disable analyze button, enable cancel
        self.analyze_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.output_text.clear()
        self.output_text.setPlainText("Analyzing codebase...")

        # Create and execute command
        config = {"provider": "auto"}  # Use default config for now
        command = AnalyzeCodebaseCommand(self.core_interface, codebase_path, config, mode="full")
        self._current_command_id = command.command_id
        self.command_manager.execute(command, background=True)

    def _cancel(self) -> None:
        """Cancel analysis."""
        if self._current_command_id:
            self.command_manager.cancel_command(self._current_command_id)
            self._current_command_id = None
            self.analyze_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            self.output_text.setPlainText("Analysis cancelled")

    def _on_analysis_finished(self, success: bool, result, error: str) -> None:
        """Handle analysis completion."""
        self.analyze_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self._current_command_id = None

        if success and result:
            # Format result (could be dict, convert to readable format)
            import json

            try:
                result_text = json.dumps(result, indent=2)
            except Exception:
                result_text = str(result)
            self.output_text.setPlainText(result_text)
        else:
            error_msg = error or "Unknown error occurred"
            self.output_text.setPlainText(f"Error: {error_msg}")
            QMessageBox.critical(self, "Analysis Failed", error_msg)

    def _save_results(self) -> None:
        """Save analysis results to file."""
        if not self.output_text.toPlainText():
            QMessageBox.warning(self, "Warning", "No results to save")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Analysis Results",
            "",
            "JSON Files (*.json);;Text Files (*.txt);;All Files (*)",
        )
        if file_path:
            try:
                Path(file_path).write_text(self.output_text.toPlainText(), encoding="utf-8")
                QMessageBox.information(self, "Success", f"Results saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {e}")

