from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget,
    QMenuBar, QToolBar, QStatusBar, QFileDialog, QMessageBox, QInputDialog
)
from PyQt6.QtGui import QFont, QAction, QColor, QTextCharFormat, QTextCursor
from PyQt6.QtCore import Qt

from .document import Document
from .llm import LocalLLMBridge


class EditorApp:
    """PyQt6-based editor window that ties Document + LLM services together."""

    def __init__(self, document: Document, llm_bridge: LocalLLMBridge) -> None:
        self.document = document
        self.llm_bridge = llm_bridge
        
        # We only want one QApplication instance
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication(sys.argv)
            
        self.main_window = QMainWindow()
        self.main_window.setWindowTitle(f"{self.document.title} — LLex")
        self.main_window.resize(1100, 760)

        self._setup_ui()
        self._load_document_text()

    def _setup_ui(self) -> None:
        """Initialize the core UI components."""
        self.central_widget = QWidget()
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.main_window.setCentralWidget(self.central_widget)

        self._build_editor()
        self._build_menu()
        self._build_toolbar()
        self._build_status_bar()

    def _build_editor(self) -> None:
        self.text_widget = QTextEdit()
        font = QFont("Segoe UI", 12)
        self.text_widget.setFont(font)
        self.text_widget.textChanged.connect(self._on_text_modified)
        self.layout.addWidget(self.text_widget)

    def _build_menu(self) -> None:
        menu_bar = self.main_window.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")
        
        # Format menu
        format_menu = menu_bar.addMenu("Format")
        
        # LLM menu
        llm_menu = menu_bar.addMenu("LLM")

        # TODO: Add actions to menus (New, Open, Save, etc. similar to Tkinter version)

    def _build_toolbar(self) -> None:
        self.toolbar = QToolBar("Formatting")
        self.main_window.addToolBar(self.toolbar)
        
        # Placeholders for toolbar actions
        # TODO: Implement full Qt Toolbar actions (Bold, Italic, Color, etc.)

    def _build_status_bar(self) -> None:
        self.status_bar = self.main_window.statusBar()
        self.status_bar.showMessage("Ready")
        # TODO: Implement live word count label

    def _load_document_text(self) -> None:
        self.text_widget.setPlainText(self.document.text)
        self._update_status(f"Document loaded: {self.document.title}")

    def _update_status(self, message: str) -> None:
        self.status_bar.showMessage(message)

    def _on_text_modified(self) -> None:
        """Live word count updates go here."""
        text = self.text_widget.toPlainText()
        words = len(text.split())
        chars = len(text)
        # We will need a dedicated label for this later.
        # self.status_bar.showMessage(f"Ready | {words} words | {chars} chars")

    def run(self) -> None:
        self.main_window.show()
        sys.exit(self.app.exec())
