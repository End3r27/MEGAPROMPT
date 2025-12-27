"""Configuration screen."""

import logging
from pathlib import Path

import yaml
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget

from megaprompt.core.config import Config
from megaprompt.gui.ui.theme import get_color
from megaprompt.gui.ui.widgets import CardWidget, RoundedButton, RoundedTextEdit, SectionHeader

logger = logging.getLogger(__name__)


class ConfigScreen(QWidget):
    """Screen for configuration management."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the config screen UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Title
        header = SectionHeader("Configuration")
        layout.addWidget(header)

        # Info
        info_card = CardWidget()
        info_layout = QVBoxLayout()
        info_card.layout.addLayout(info_layout)

        info_text = (
            "Configuration is loaded from:\n"
            "1. CLI arguments (highest priority)\n"
            "2. Project config (.megaprompt.yaml)\n"
            "3. User config (~/.megaprompt/config.yaml)\n"
            "4. Defaults (lowest priority)"
        )
        info_label = QLabel(info_text)
        info_label.setStyleSheet(f"color: {get_color('text_muted')};")
        info_layout.addWidget(info_label)

        layout.addWidget(info_card)

        # Config editor
        editor_card = CardWidget()
        editor_layout = QVBoxLayout()
        editor_card.layout.addLayout(editor_layout)

        editor_label = QLabel("Current Configuration (YAML):")
        editor_label.setStyleSheet(f"font-weight: bold; color: {get_color('text')};")
        editor_layout.addWidget(editor_label)

        self.config_text = RoundedTextEdit()
        self.config_text.setMinimumHeight(300)
        editor_layout.addWidget(self.config_text)

        # Buttons
        buttons_layout = QHBoxLayout()
        load_btn = RoundedButton("Load from File")
        load_btn.clicked.connect(self._load_from_file)
        buttons_layout.addWidget(load_btn)

        reload_btn = RoundedButton("Reload Current")
        reload_btn.clicked.connect(self._reload_config)
        buttons_layout.addWidget(reload_btn)

        save_btn = RoundedButton("Save to User Config")
        save_btn.clicked.connect(self._save_to_user_config)
        buttons_layout.addWidget(save_btn)

        buttons_layout.addStretch()
        editor_layout.addLayout(buttons_layout)

        layout.addWidget(editor_card)

        # Load current config
        self._reload_config()

        layout.addStretch()

    def _reload_config(self) -> None:
        """Reload current configuration."""
        try:
            config = Config.load()
            config_dict = config.to_dict()
            config_yaml = yaml.dump(config_dict, default_flow_style=False, sort_keys=False)
            self.config_text.setPlainText(config_yaml)
        except Exception as e:
            logger.error(f"Error loading config: {e}", exc_info=True)
            self.config_text.setPlainText(f"# Error loading config: {e}")

    def _load_from_file(self) -> None:
        """Load configuration from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Configuration File",
            "",
            "YAML Files (*.yaml *.yml);;JSON Files (*.json);;All Files (*)",
        )
        if file_path:
            try:
                content = Path(file_path).read_text(encoding="utf-8")
                self.config_text.setPlainText(content)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file: {e}")

    def _save_to_user_config(self) -> None:
        """Save configuration to user config file."""
        try:
            content = self.config_text.toPlainText()
            # Validate YAML
            try:
                yaml.safe_load(content)
            except yaml.YAMLError as e:
                QMessageBox.warning(self, "Invalid YAML", f"Configuration is not valid YAML:\n{e}")
                return

            # Save to user config
            config_path = Path.home() / ".megaprompt" / "config.yaml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(content, encoding="utf-8")
            QMessageBox.information(self, "Success", f"Configuration saved to {config_path}")
        except Exception as e:
            logger.error(f"Error saving config: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {e}")

