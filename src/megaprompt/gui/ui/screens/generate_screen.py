"""Generate screen for prompt generation."""

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from megaprompt.gui.core.command import CommandManager, GeneratePromptCommand
from megaprompt.gui.core.event_bus import EventBus, EVENT_COMMAND_FINISHED, EVENT_PROMPT_COMPLETED
from megaprompt.gui.core.interface import MegaPromptCoreInterface
from megaprompt.gui.ui.theme import get_color
from megaprompt.gui.ui.widgets import CardWidget, RoundedButton, RoundedLineEdit, RoundedTextEdit, SectionHeader

logger = logging.getLogger(__name__)


class GenerateScreen(QWidget):
    """Screen for generating mega-prompts."""

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
        self._current_command_id: Optional[str] = None
        self._setup_ui()
        self._connect_events()

    def _setup_ui(self) -> None:
        """Setup the generate screen UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Title
        header = SectionHeader("Generate Mega-Prompt")
        layout.addWidget(header)

        # Input section
        input_card = CardWidget()
        input_layout = QVBoxLayout()
        input_card.layout.addLayout(input_layout)

        input_label = QLabel("Input Prompt:")
        input_label.setStyleSheet(f"font-weight: bold; color: {get_color('text')};")
        input_layout.addWidget(input_label)

        self.input_text = RoundedTextEdit()
        self.input_text.setPlaceholderText("Enter your prompt here...")
        self.input_text.setMinimumHeight(150)
        input_layout.addWidget(self.input_text)

        # Input buttons
        input_buttons = QHBoxLayout()
        load_file_btn = RoundedButton("Load File")
        load_file_btn.clicked.connect(self._load_file)
        input_buttons.addWidget(load_file_btn)

        clear_btn = RoundedButton("Clear")
        clear_btn.clicked.connect(self._clear_input)
        input_buttons.addWidget(clear_btn)
        input_buttons.addStretch()
        input_layout.addLayout(input_buttons)

        layout.addWidget(input_card)

        # Configuration section
        config_card = CardWidget()
        config_layout = QFormLayout()
        config_card.layout.addLayout(config_layout)

        # Provider
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["auto", "ollama", "qwen", "gemini", "openrouter"])
        self.provider_combo.setCurrentText("auto")
        config_layout.addRow("Provider:", self.provider_combo)

        # Model
        self.model_entry = RoundedLineEdit()
        self.model_entry.setPlaceholderText("Leave empty for default")
        config_layout.addRow("Model:", self.model_entry)

        # Temperature
        self.temp_entry = RoundedLineEdit()
        self.temp_entry.setText("0.0")
        self.temp_entry.setPlaceholderText("0.0")
        config_layout.addRow("Temperature:", self.temp_entry)

        # API Key
        self.api_key_entry = RoundedLineEdit()
        self.api_key_entry.setPlaceholderText("Optional (uses env vars if empty)")
        self.api_key_entry.setEchoMode(QLineEdit.EchoMode.Password)
        config_layout.addRow("API Key:", self.api_key_entry)

        # Output format
        self.format_combo = QComboBox()
        self.format_combo.addItems(["markdown", "json", "yaml"])
        self.format_combo.setCurrentText("markdown")
        config_layout.addRow("Output Format:", self.format_combo)

        layout.addWidget(config_card)

        # Output section
        output_card = CardWidget()
        output_layout = QVBoxLayout()
        output_card.layout.addLayout(output_layout)

        output_label = QLabel("Output:")
        output_label.setStyleSheet(f"font-weight: bold; color: {get_color('text')};")
        output_layout.addWidget(output_label)

        self.output_text = RoundedTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(200)
        output_layout.addWidget(self.output_text)

        # Output buttons
        output_buttons = QHBoxLayout()
        save_file_btn = RoundedButton("Save to File")
        save_file_btn.clicked.connect(self._save_output)
        output_buttons.addWidget(save_file_btn)
        output_buttons.addStretch()
        output_layout.addLayout(output_buttons)

        layout.addWidget(output_card)

        # Action buttons
        action_buttons = QHBoxLayout()
        self.generate_btn = RoundedButton("Generate")
        self.generate_btn.setStyleSheet(f"background-color: {get_color('primary')}; font-size: 16px; padding: 12px;")
        self.generate_btn.clicked.connect(self._generate)
        action_buttons.addWidget(self.generate_btn)

        self.cancel_btn = RoundedButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel)
        action_buttons.addWidget(self.cancel_btn)
        action_buttons.addStretch()

        layout.addLayout(action_buttons)
        layout.addStretch()

    def _connect_events(self) -> None:
        """Connect to event bus."""
        from megaprompt.gui.core.events import CommandFinishedEvent, PromptCompletedEvent

        def on_command_finished(event: CommandFinishedEvent):
            if event.command_type == "generate_prompt":
                self._on_generation_finished(event.success, event.result, event.error)

        self.event_bus.subscribe(EVENT_COMMAND_FINISHED, on_command_finished)

    def _load_file(self) -> None:
        """Load prompt from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Prompt File",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if file_path:
            try:
                content = Path(file_path).read_text(encoding="utf-8")
                self.input_text.setPlainText(content)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file: {e}")

    def _clear_input(self) -> None:
        """Clear input text."""
        self.input_text.clear()

    def _save_output(self) -> None:
        """Save output to file."""
        if not self.output_text.toPlainText():
            QMessageBox.warning(self, "Warning", "No output to save")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Output",
            "",
            "Markdown Files (*.md);;Text Files (*.txt);;All Files (*)",
        )
        if file_path:
            try:
                Path(file_path).write_text(self.output_text.toPlainText(), encoding="utf-8")
                QMessageBox.information(self, "Success", f"Output saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {e}")

    def _get_config(self) -> dict:
        """Get configuration from UI."""
        config = {
            "provider": self.provider_combo.currentText(),
            "model": self.model_entry.text().strip() or None,
            "temperature": float(self.temp_entry.text() or "0.0"),
            "api_key": self.api_key_entry.text().strip() or None,
            "output_format": self.format_combo.currentText(),
            "verbose": True,
        }
        return {k: v for k, v in config.items() if v is not None}

    def _generate(self) -> None:
        """Generate mega-prompt."""
        user_prompt = self.input_text.toPlainText().strip()
        if not user_prompt:
            QMessageBox.warning(self, "Warning", "Please enter a prompt")
            return

        # Get configuration
        config = self._get_config()

        # Validate temperature
        try:
            float(config.get("temperature", 0.0))
        except ValueError:
            QMessageBox.warning(self, "Warning", "Invalid temperature value")
            return

        # Disable generate button, enable cancel
        self.generate_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.output_text.clear()
        self.output_text.setPlainText("Generating...")

        # Create and execute command
        command = GeneratePromptCommand(self.core_interface, user_prompt, config)
        self._current_command_id = command.command_id
        self.command_manager.execute(command, background=True)

    def _cancel(self) -> None:
        """Cancel generation."""
        if self._current_command_id:
            self.command_manager.cancel_command(self._current_command_id)
            self._current_command_id = None
            self.generate_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            self.output_text.setPlainText("Generation cancelled")

    def _on_generation_finished(self, success: bool, result: Optional[str], error: Optional[str]) -> None:
        """Handle generation completion."""
        self.generate_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self._current_command_id = None

        if success and result:
            self.output_text.setPlainText(result)
        else:
            error_msg = error or "Unknown error occurred"
            self.output_text.setPlainText(f"Error: {error_msg}")
            QMessageBox.critical(self, "Generation Failed", error_msg)

