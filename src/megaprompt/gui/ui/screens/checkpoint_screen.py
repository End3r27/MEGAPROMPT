"""Checkpoint management screen."""

import logging
from pathlib import Path

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget

from megaprompt.core.checkpoint import CheckpointManager
from megaprompt.gui.ui.theme import get_color
from megaprompt.gui.ui.widgets import CardWidget, RoundedButton, SectionHeader

logger = logging.getLogger(__name__)


class CheckpointScreen(QWidget):
    """Screen for checkpoint management."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the checkpoint screen UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Title
        header = SectionHeader("Checkpoints")
        layout.addWidget(header)

        # Checkpoints list
        list_card = CardWidget()
        list_layout = QVBoxLayout()
        list_card.layout.addLayout(list_layout)

        list_label = QLabel("Available Checkpoints:")
        list_label.setStyleSheet(f"font-weight: bold; color: {get_color('text')};")
        list_layout.addWidget(list_label)

        self.checkpoint_list = QListWidget()
        self.checkpoint_list.setMinimumHeight(200)
        self.checkpoint_list.itemSelectionChanged.connect(self._on_checkpoint_selected)
        list_layout.addWidget(self.checkpoint_list)

        # Action buttons
        action_buttons = QHBoxLayout()
        refresh_btn = RoundedButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_list)
        action_buttons.addWidget(refresh_btn)

        delete_btn = RoundedButton("Delete Selected")
        delete_btn.setStyleSheet(f"background-color: {get_color('accent')};")
        delete_btn.clicked.connect(self._delete_checkpoint)
        action_buttons.addWidget(delete_btn)

        action_buttons.addStretch()
        list_layout.addLayout(action_buttons)

        layout.addWidget(list_card)

        # Details
        details_card = CardWidget()
        details_layout = QVBoxLayout()
        details_card.layout.addLayout(details_layout)

        details_label = QLabel("Checkpoint Details:")
        details_label.setStyleSheet(f"font-weight: bold; color: {get_color('text')};")
        details_layout.addWidget(details_label)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMinimumHeight(200)
        details_layout.addWidget(self.details_text)

        layout.addWidget(details_card)

        layout.addStretch()

        # Load initial list
        self._refresh_list()

    def _refresh_list(self) -> None:
        """Refresh checkpoint list."""
        try:
            checkpoint_dir = Path.home() / ".megaprompt" / "checkpoints"
            self.checkpoint_list.clear()

            if checkpoint_dir.exists():
                checkpoint_files = list(checkpoint_dir.glob("*.json"))
                for checkpoint_file in sorted(checkpoint_files, key=lambda p: p.stat().st_mtime, reverse=True):
                    self.checkpoint_list.addItem(checkpoint_file.name)
            else:
                self.checkpoint_list.addItem("No checkpoints found")
        except Exception as e:
            logger.error(f"Error refreshing checkpoint list: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to refresh checkpoint list: {e}")

    def _on_checkpoint_selected(self) -> None:
        """Handle checkpoint selection."""
        current_item = self.checkpoint_list.currentItem()
        if current_item and current_item.text() != "No checkpoints found":
            try:
                checkpoint_dir = Path.home() / ".megaprompt" / "checkpoints"
                checkpoint_file = checkpoint_dir / current_item.text()

                if checkpoint_file.exists():
                    import json

                    content = checkpoint_file.read_text(encoding="utf-8")
                    data = json.loads(content)
                    details_text = json.dumps(data, indent=2)
                    self.details_text.setPlainText(details_text)
                else:
                    self.details_text.setPlainText("Checkpoint file not found")
            except Exception as e:
                logger.error(f"Error loading checkpoint details: {e}", exc_info=True)
                self.details_text.setPlainText(f"Error loading checkpoint: {e}")
        else:
            self.details_text.clear()

    def _delete_checkpoint(self) -> None:
        """Delete selected checkpoint."""
        current_item = self.checkpoint_list.currentItem()
        if not current_item or current_item.text() == "No checkpoints found":
            QMessageBox.warning(self, "Warning", "Please select a checkpoint to delete")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete checkpoint '{current_item.text()}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                checkpoint_dir = Path.home() / ".megaprompt" / "checkpoints"
                checkpoint_file = checkpoint_dir / current_item.text()
                if checkpoint_file.exists():
                    checkpoint_file.unlink()
                    QMessageBox.information(self, "Success", "Checkpoint deleted successfully")
                    self._refresh_list()
                    self.details_text.clear()
                else:
                    QMessageBox.warning(self, "Warning", "Checkpoint file not found")
            except Exception as e:
                logger.error(f"Error deleting checkpoint: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Failed to delete checkpoint: {e}")

