from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget,
    QMenuBar, QToolBar, QStatusBar, QFileDialog, QMessageBox, QInputDialog,
    QHBoxLayout, QFontComboBox, QComboBox, QLabel, QColorDialog
)
from PyQt6.QtGui import (
    QFont, QAction, QColor, QTextCharFormat, QTextCursor, QKeySequence, 
    QIcon
)
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
        # Ensure a neutral, distraction-free gray background for the "application" layer
        self.central_widget.setStyleSheet("QWidget { background-color: #f3f2f1; }")
        
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 20, 0, 0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.main_window.setCentralWidget(self.central_widget)

        self._create_actions()
        self._build_editor()
        self._build_menu()
        self._build_toolbar()
        self._build_status_bar()

    def _create_actions(self) -> None:
        """Centralize all application actions for Menu & Toolbars (HCI: Consistency)."""
        # --- File Actions ---
        self.action_new = QAction("New", self.main_window)
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        # self.action_new.triggered.connect(self._new_document) # TODO later

        self.action_open = QAction("Open...", self.main_window)
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)

        self.action_save = QAction("Save", self.main_window)
        self.action_save.setShortcut(QKeySequence.StandardKey.Save)

        # --- Formatting Actions ---
        self.action_bold = QAction("Bold", self.main_window)
        self.action_bold.setCheckable(True)
        self.action_bold.setShortcut(QKeySequence.StandardKey.Bold)
        self.action_bold.triggered.connect(self._toggle_bold)

        self.action_italic = QAction("Italic", self.main_window)
        self.action_italic.setCheckable(True)
        self.action_italic.setShortcut(QKeySequence.StandardKey.Italic)
        self.action_italic.triggered.connect(self._toggle_italic)

        self.action_underline = QAction("Underline", self.main_window)
        self.action_underline.setCheckable(True)
        self.action_underline.setShortcut(QKeySequence.StandardKey.Underline)
        self.action_underline.triggered.connect(self._toggle_underline)

        self.action_color = QAction("Text Color", self.main_window)
        self.action_color.triggered.connect(self._apply_text_color)
        
        self.action_highlight = QAction("Highlight", self.main_window)
        self.action_highlight.triggered.connect(self._apply_highlight)

        # --- Paragraph Alignment ---
        self.action_align_left = QAction("Align Left", self.main_window)
        self.action_align_left.triggered.connect(lambda: self._apply_alignment(Qt.AlignmentFlag.AlignLeft))
        self.action_align_center = QAction("Center", self.main_window)
        self.action_align_center.triggered.connect(lambda: self._apply_alignment(Qt.AlignmentFlag.AlignCenter))
        self.action_align_right = QAction("Align Right", self.main_window)
        self.action_align_right.triggered.connect(lambda: self._apply_alignment(Qt.AlignmentFlag.AlignRight))

        # --- LLM Actions ---
        self.action_summarize = QAction("Summarize Selection", self.main_window)
        self.action_summarize.triggered.connect(self._handle_llm_summarize)
        self.action_rewrite = QAction("Rewrite Selection", self.main_window)
        self.action_rewrite.triggered.connect(self._handle_llm_rewrite)

    def _build_editor(self) -> None:
        self.text_widget = QTextEdit()
        # Visual HCI mapping: Make the editor look like a piece of paper
        self.text_widget.setStyleSheet("""
            QTextEdit {
                background-color: white;
                color: black;
                border: 1px solid #d3d3d3;
                border-radius: 2px;
                padding: 40px;
                max-width: 800px;
            }
        """)
        font = QFont("Segoe UI", 12)
        self.text_widget.setFont(font)
        self.text_widget.cursorPositionChanged.connect(self._sync_format_state)
        self.text_widget.textChanged.connect(self._on_text_modified)
        
        # Center the 'paper' horizontally
        self.layout.addWidget(self.text_widget, alignment=Qt.AlignmentFlag.AlignHCenter)

    def _build_menu(self) -> None:
        menu_bar = self.main_window.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction(self.action_new)
        file_menu.addAction(self.action_open)
        file_menu.addAction(self.action_save)
        
        # Format menu
        format_menu = menu_bar.addMenu("Format")
        format_menu.addAction(self.action_bold)
        format_menu.addAction(self.action_italic)
        format_menu.addAction(self.action_underline)
        format_menu.addSeparator()
        format_menu.addAction(self.action_color)
        format_menu.addAction(self.action_highlight)
        
        # LLM menu
        llm_menu = menu_bar.addMenu("LLM")
        llm_menu.addAction(self.action_summarize)
        llm_menu.addAction(self.action_rewrite)

    def _build_toolbar(self) -> None:
        self.toolbar = QToolBar("Formatting")
        self.toolbar.setStyleSheet("QToolBar { background-color: white; border-bottom: 1px solid #d3d3d3; padding: 4px; }")
        self.toolbar.setMovable(False)
        self.main_window.addToolBar(self.toolbar)
        
        # 1. Typography 
        self.combo_font = QFontComboBox()
        self.combo_font.setCurrentFont(QFont("Segoe UI"))
        self.combo_font.currentFontChanged.connect(self._change_font_family)
        
        self.combo_size = QComboBox()
        self.combo_size.addItems([str(s) for s in (8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 72)])
        self.combo_size.setCurrentText("12")
        self.combo_size.currentTextChanged.connect(self._change_font_size)

        self.toolbar.addWidget(self.combo_font)
        self.toolbar.addWidget(self.combo_size)
        self.toolbar.addSeparator()

        # 2. Text Formatting
        self.toolbar.addAction(self.action_bold)
        self.toolbar.addAction(self.action_italic)
        self.toolbar.addAction(self.action_underline)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_color)
        self.toolbar.addAction(self.action_highlight)
        self.toolbar.addSeparator()
        
        # 3. Alignment
        self.toolbar.addAction(self.action_align_left)
        self.toolbar.addAction(self.action_align_center)
        self.toolbar.addAction(self.action_align_right)
        self.toolbar.addSeparator()

        # 4. LLM
        self.toolbar.addAction(self.action_summarize)
        self.toolbar.addAction(self.action_rewrite)

    def _build_status_bar(self) -> None:
        self.status_bar = self.main_window.statusBar()
        self.status_bar.setStyleSheet("QStatusBar { background-color: #f3f2f1; color: #555; }")
        
        self.status_label = QLabel("Ready")
        self.word_count_label = QLabel("0 words | 0 chars")
        
        # Add widget with stretch=1 pushes subsequent permanent widgets to the right
        self.status_bar.addWidget(self.status_label, 1)
        self.status_bar.addPermanentWidget(self.word_count_label)

    def _load_document_text(self) -> None:
        self.text_widget.setPlainText(self.document.text)
        self._update_status(f"Document loaded: {self.document.title}")

    def _update_status(self, message: str) -> None:
        self.status_label.setText(message)

    def _on_text_modified(self) -> None:
        text = self.text_widget.toPlainText()
        words = len(text.split())
        chars = len(text)
        self.word_count_label.setText(f"{words} words | {chars} chars")

    def _sync_format_state(self) -> None:
        """Keeps Toolbar button states synced with the text under the cursor."""
        fmt = self.text_widget.currentCharFormat()
        self.action_bold.setChecked(fmt.fontWeight() == QFont.Weight.Bold)
        self.action_italic.setChecked(fmt.fontItalic())
        self.action_underline.setChecked(fmt.fontUnderline())
        self.combo_font.setCurrentFont(fmt.font())
        self.combo_size.setCurrentText(str(int(fmt.fontPointSize() or 12)))

    def _merge_format(self, fmt: QTextCharFormat) -> None:
        """Safely apply a QTextCharFormat without breaking existing styles in the run."""
        cursor = self.text_widget.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.text_widget.mergeCurrentCharFormat(fmt)

    def _change_font_family(self, font: QFont) -> None:
        fmt = QTextCharFormat()
        fmt.setFontFamily(font.family())
        self._merge_format(fmt)

    def _change_font_size(self, size_str: str) -> None:
        if not size_str.isdigit():
            return
        fmt = QTextCharFormat()
        fmt.setFontPointSize(float(size_str))
        self._merge_format(fmt)

    def _toggle_bold(self) -> None:
        fmt = QTextCharFormat()
        weight = QFont.Weight.Bold if self.action_bold.isChecked() else QFont.Weight.Normal
        fmt.setFontWeight(weight)
        self._merge_format(fmt)

    def _toggle_italic(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.action_italic.isChecked())
        self._merge_format(fmt)

    def _toggle_underline(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontUnderline(self.action_underline.isChecked())
        self._merge_format(fmt)

    def _apply_text_color(self) -> None:
        color = QColorDialog.getColor(Qt.GlobalColor.black, self.main_window, "Text Color")
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            self._merge_format(fmt)

    def _apply_highlight(self) -> None:
        color = QColorDialog.getColor(QColor("#fff5b1"), self.main_window, "Highlight Color")
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setBackground(color)
            self._merge_format(fmt)

    def _apply_alignment(self, alignment: Qt.AlignmentFlag) -> None:
        self.text_widget.setAlignment(alignment)

    # --- LLM Placeholders ---
    def _handle_llm_summarize(self) -> None:
        pass

    def _handle_llm_rewrite(self) -> None:
        pass

    def run(self) -> None:
        self.main_window.show()
        sys.exit(self.app.exec())
