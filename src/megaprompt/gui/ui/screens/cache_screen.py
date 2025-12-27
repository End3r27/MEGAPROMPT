"""Cache management screen."""

import logging
from pathlib import Path

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget

from megaprompt.core.cache import Cache
from megaprompt.gui.ui.theme import get_color
from megaprompt.gui.ui.widgets import CardWidget, RoundedButton, RoundedTextEdit, SectionHeader

logger = logging.getLogger(__name__)


class CacheScreen(QWidget):
    """Screen for cache management."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the cache screen UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Title
        header = SectionHeader("Cache Management")
        layout.addWidget(header)

        # Stats card
        stats_card = CardWidget()
        stats_layout = QVBoxLayout()
        stats_card.layout.addLayout(stats_layout)

        self.stats_text = RoundedTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMinimumHeight(150)
        stats_layout.addWidget(self.stats_text)

        # Action buttons
        action_buttons = QHBoxLayout()
        refresh_btn = RoundedButton("Refresh Stats")
        refresh_btn.clicked.connect(self._refresh_stats)
        action_buttons.addWidget(refresh_btn)

        clear_btn = RoundedButton("Clear Cache")
        clear_btn.setStyleSheet(f"background-color: {get_color('accent')};")
        clear_btn.clicked.connect(self._clear_cache)
        action_buttons.addWidget(clear_btn)

        action_buttons.addStretch()
        stats_layout.addLayout(action_buttons)

        layout.addWidget(stats_card)

        layout.addStretch()

        # Load initial stats
        self._refresh_stats()

    def _refresh_stats(self) -> None:
        """Refresh cache statistics."""
        try:
            cache_dir = Path.home() / ".megaprompt" / "cache"
            if cache_dir.exists():
                cache = Cache(cache_dir)

                # Get cache stats (this would need to be added to Cache class)
                stats_text = f"Cache Directory: {cache_dir}\n"
                stats_text += f"Cache exists: {cache_dir.exists()}\n"

                # Count files in cache
                cache_files = list(cache_dir.glob("**/*")) if cache_dir.exists() else []
                file_count = len([f for f in cache_files if f.is_file()])
                total_size = sum(f.stat().st_size for f in cache_files if f.is_file())

                stats_text += f"Cache files: {file_count}\n"
                stats_text += f"Total size: {total_size / 1024 / 1024:.2f} MB"

                self.stats_text.setPlainText(stats_text)
            else:
                self.stats_text.setPlainText("Cache directory does not exist.")
        except Exception as e:
            logger.error(f"Error refreshing cache stats: {e}", exc_info=True)
            self.stats_text.setPlainText(f"Error loading cache statistics: {e}")

    def _clear_cache(self) -> None:
        """Clear cache."""
        reply = QMessageBox.question(
            self,
            "Confirm Clear Cache",
            "Are you sure you want to clear the cache? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                cache_dir = Path.home() / ".megaprompt" / "cache"
                if cache_dir.exists():
                    import shutil

                    shutil.rmtree(cache_dir)
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    QMessageBox.information(self, "Success", "Cache cleared successfully")
                    self._refresh_stats()
                else:
                    QMessageBox.information(self, "Info", "Cache directory does not exist")
            except Exception as e:
                logger.error(f"Error clearing cache: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Failed to clear cache: {e}")

