"""Batch processing screen."""

import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from megaprompt.gui.ui.theme import get_color
from megaprompt.gui.ui.widgets import CardWidget, RoundedButton, SectionHeader

logger = logging.getLogger(__name__)


class BatchScreen(QWidget):
    """Screen for batch processing multiple files."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the batch screen UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Title
        header = SectionHeader("Batch Processing")
        layout.addWidget(header)

        # File selection
        files_card = CardWidget()
        files_layout = QVBoxLayout()
        files_card.layout.addLayout(files_layout)

        files_label = QLabel("Select input files:")
        files_label.setStyleSheet(f"font-weight: bold; color: {get_color('text')};")
        files_layout.addWidget(files_label)

        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(200)
        files_layout.addWidget(self.file_list)

        # File buttons
        file_buttons = QHBoxLayout()
        add_files_btn = RoundedButton("Add Files")
        add_files_btn.clicked.connect(self._add_files)
        file_buttons.addWidget(add_files_btn)

        remove_file_btn = RoundedButton("Remove Selected")
        remove_file_btn.clicked.connect(self._remove_file)
        file_buttons.addWidget(remove_file_btn)

        clear_all_btn = RoundedButton("Clear All")
        clear_all_btn.clicked.connect(self._clear_all)
        file_buttons.addWidget(clear_all_btn)

        file_buttons.addStretch()
        files_layout.addLayout(file_buttons)

        layout.addWidget(files_card)

        # Progress
        progress_card = CardWidget()
        progress_layout = QVBoxLayout()
        progress_card.layout.addLayout(progress_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(f"color: {get_color('text_muted')};")
        progress_layout.addWidget(self.status_label)

        layout.addWidget(progress_card)

        # Action buttons
        action_buttons = QHBoxLayout()
        self.process_btn = RoundedButton("Process Batch")
        self.process_btn.setStyleSheet(f"background-color: {get_color('primary')}; font-size: 16px; padding: 12px;")
        self.process_btn.clicked.connect(self._process_batch)
        action_buttons.addWidget(self.process_btn)
        action_buttons.addStretch()

        layout.addLayout(action_buttons)
        layout.addStretch()

    def _add_files(self) -> None:
        """Add files to batch list."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Input Files",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        for file_path in files:
            if file_path not in [self.file_list.item(i).text() for i in range(self.file_list.count())]:
                self.file_list.addItem(file_path)

    def _remove_file(self) -> None:
        """Remove selected file from list."""
        current_item = self.file_list.currentItem()
        if current_item:
            self.file_list.takeItem(self.file_list.row(current_item))

    def _clear_all(self) -> None:
        """Clear all files from list."""
        self.file_list.clear()

    def _process_batch(self) -> None:
        """Process batch files."""
        files = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        if not files:
            QMessageBox.warning(self, "Warning", "Please add files to process.")
            return

        # TODO: Implement actual batch processing
        QMessageBox.information(self, "Info", f"Batch processing {len(files)} files...\n(This feature will be implemented)")

