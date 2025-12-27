"""Help screen with documentation."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from megaprompt.gui.ui.theme import get_color
from megaprompt.gui.ui.widgets import CardWidget, SectionHeader


class HelpScreen(QWidget):
    """Screen for help and documentation."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the help screen UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Title
        header = SectionHeader("Help & Documentation")
        layout.addWidget(header)

        # Help content
        help_card = CardWidget()
        help_layout = QVBoxLayout()
        help_card.layout.addLayout(help_layout)

        help_text = """
        <h2>MEGAPROMPT GUI</h2>
        
        <h3>Generate Screen</h3>
        <p>Enter your prompt in the input area and click Generate to create a structured mega-prompt.</p>
        <ul>
            <li>You can load prompts from files using the "Load File" button</li>
            <li>Configure the LLM provider, model, temperature, and other settings</li>
            <li>Results are displayed in the output area and can be saved to a file</li>
        </ul>
        
        <h3>Batch Screen</h3>
        <p>Process multiple prompt files in batch mode.</p>
        
        <h3>Analyze Screen</h3>
        <p>Analyze codebases to identify system holes, architectural risks, and enhancement opportunities.</p>
        
        <h3>Config Screen</h3>
        <p>View and edit configuration settings. Configuration is loaded from multiple sources with priority order.</p>
        
        <h3>Cache Screen</h3>
        <p>View cache statistics and manage cached results.</p>
        
        <h3>Checkpoints Screen</h3>
        <p>View and manage checkpoints from previous generation runs.</p>
        
        <h3>Settings</h3>
        <p>Application settings are saved automatically and restored on startup.</p>
        
        <h3>Keyboard Shortcuts</h3>
        <ul>
            <li>Ctrl+O: Open file (in Generate screen)</li>
            <li>Ctrl+S: Save output (in Generate screen)</li>
            <li>Ctrl+G: Generate prompt (in Generate screen)</li>
            <li>Ctrl+Q: Quit application</li>
        </ul>
        """

        help_label = QLabel(help_text)
        help_label.setWordWrap(True)
        help_label.setStyleSheet(f"color: {get_color('text')}; padding: 10px;")
        help_label.setTextFormat(Qt.TextFormat.RichText)
        help_layout.addWidget(help_label)

        layout.addWidget(help_card)

        # About
        about_card = CardWidget()
        about_layout = QVBoxLayout()
        about_card.layout.addLayout(about_layout)

        about_text = """
        <h3>About MEGAPROMPT</h3>
        <p>MEGAPROMPT transforms messy human prompts into structured, deterministic mega-prompts optimized for AI execution.</p>
        <p>Version: 0.1.0</p>
        <p>License: MIT</p>
        """
        about_label = QLabel(about_text)
        about_label.setWordWrap(True)
        about_label.setStyleSheet(f"color: {get_color('text')}; padding: 10px;")
        about_label.setTextFormat(Qt.TextFormat.RichText)
        about_layout.addWidget(about_label)

        layout.addWidget(about_card)

        layout.addStretch()

