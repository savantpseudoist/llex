from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget, QMenu,
    QMenuBar, QToolBar, QStatusBar, QFileDialog, QMessageBox, QInputDialog,     
    QHBoxLayout, QFontComboBox, QComboBox, QLabel, QColorDialog, QScrollBar,    
    QPushButton, QSizePolicy, QToolButton, QFrame, QLayout
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush,
    QFont, QAction, QColor, QTextCharFormat, QTextCursor, QKeySequence,
    QIcon, QTextBlockFormat
)
from PyQt6.QtCore import Qt

from .document import Document
from .llm import LocalLLMBridge
from .export import DocumentExporter






from PyQt6.QtCore import Qt, QSizeF
class DraftEditor(QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_width = 816
        self.page_height = 1056
        self.document().setPageSize(QSizeF(self.page_width, self.page_height))
        self.setFixedWidth(self.page_width)

    def paintEvent(self, event):
        super().paintEvent(event)
        from PyQt6.QtGui import QPainter, QPen, QColor
        from PyQt6.QtCore import Qt
        painter = QPainter(self.viewport())
        line_pen = QPen(QColor(150, 150, 150))
        line_pen.setStyle(Qt.PenStyle.DashLine)
        line_pen.setWidth(1)
        painter.setPen(line_pen)

        offset = self.verticalScrollBar().value()
        viewport_height = self.viewport().height()

        start_page = int(offset // self.page_height)
        end_page = int((offset + viewport_height) // self.page_height)

        for i in range(start_page + 1, end_page + 2):
            y = int(i * self.page_height - offset)
            painter.drawLine(0, y, self.viewport().width(), y)

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
        self.central_widget.setStyleSheet("QWidget { background-color: #1e1e1e; }")
        
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 20, 0, 0)
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

        self.action_export = QAction("Export As...", self.main_window)
        self.action_export.triggered.connect(self._handle_export)

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
        self.action_add_llm = QAction("Add New LLM...", self.main_window)
        # Assuming placeholders for now
        self.action_manage_llm = QAction("Manage Models...", self.main_window)
        self.action_llm_settings = QAction("LLM Settings...", self.main_window)

        # --- View/Settings Actions ---
        self.action_theme = QAction("Toggle Paper Theme", self.main_window)
        self.action_theme.setShortcut(QKeySequence("F5"))
        self.action_header_footer = QAction("Headers & Footers", self.main_window)
        self.action_header_footer.triggered.connect(self._edit_header_footer)
        self.action_page_orientation = QAction("Page Orientation", self.main_window)
        self.action_page_orientation.triggered.connect(self._toggle_orientation)
        self.action_header_footer = QAction("Headers & Footers", self.main_window)
        self.action_header_footer.triggered.connect(self._edit_header_footer)
        self.action_page_orientation = QAction("Page Orientation", self.main_window)
        self.action_page_orientation.triggered.connect(self._toggle_orientation)
        self.action_theme.triggered.connect(self._toggle_theme)

        self.action_toggle_sidebar = QAction("◨ Copilot", self.main_window)
        self.action_toggle_sidebar.setShortcut(QKeySequence("Ctrl+Shift+L"))
        self.action_toggle_sidebar.triggered.connect(self._toggle_sidebar)

    def _build_editor(self) -> None:
        self.editor_container = QWidget()
        editor_layout = QHBoxLayout(self.editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)

        # Build Sidebar
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setFixedWidth(280)
        self.sidebar_widget.setStyleSheet("""
            QWidget { background-color: #252526; border-left: 1px solid #444444; color: #cccccc; }
            QPushButton { background-color: #3a3d41; border: 1px solid #555555; border-radius: 4px; padding: 6px; color: white; margin-top: 4px; }
            QPushButton:hover { background-color: #505357; }
        """)
        sidebar_layout = QVBoxLayout(self.sidebar_widget)
        sidebar_layout.setContentsMargins(12, 16, 12, 12)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        sidebar_title = QLabel("LLM Assistant")
        sidebar_title.setStyleSheet("font-weight: bold; font-size: 14px; border: none; margin-bottom: 8px;")
        sidebar_layout.addWidget(sidebar_title)
        
        btn_summarize = QPushButton("Summarize Selection")
        btn_summarize.setStyleSheet("border: none; margin: 0; background: #3a3d41;")  # Reset child style cascades
        btn_summarize.clicked.connect(self._handle_llm_summarize)
        sidebar_layout.addWidget(btn_summarize)
        
        btn_rewrite = QPushButton("Rewrite Selection")
        btn_rewrite.setStyleSheet("border: none; margin: 0; background: #3a3d41;")
        btn_rewrite.clicked.connect(self._handle_llm_rewrite)
        sidebar_layout.addWidget(btn_rewrite)

        sidebar_layout.addStretch(1)
        
        prompt_label = QLabel("Ask Copilot:")
        prompt_label.setStyleSheet("border: none; font-size: 12px;")
        sidebar_layout.addWidget(prompt_label)
        
        self.llm_prompt_input = QTextEdit()
        self.llm_prompt_input.setPlaceholderText("Ask LLM to edit or generate text...")
        self.llm_prompt_input.setFixedHeight(80)
        self.llm_prompt_input.setStyleSheet("background-color: #1e1e1e; border: 1px solid #444444; border-radius: 2px; padding: 4px; color: white;")
        sidebar_layout.addWidget(self.llm_prompt_input)
        
        btn_ask = QPushButton("Submit Prompt")
        btn_ask.setStyleSheet("border: none; margin: 0; background: #0e639c;") # VS Code blue
        sidebar_layout.addWidget(btn_ask)
        
        self.sidebar_widget.hide()

        self.text_widget = DraftEditor()
        # Visual HCI mapping: Make the editor look like a piece of paper        
        self.is_dark_paper = True
        self._apply_paper_theme()
        
        font = QFont("Segoe UI", 12)
        self.text_widget.setFont(font)
        self.text_widget.cursorPositionChanged.connect(self._sync_format_state)
        self.text_widget.textChanged.connect(self._on_text_modified)
        
        # Link scrollbars so real scrollbar renders dynamically on UI's far right.
        self.text_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollbar = QScrollBar(Qt.Orientation.Vertical)
        self.text_widget.verticalScrollBar().valueChanged.connect(self.scrollbar.setValue)
        self.scrollbar.valueChanged.connect(self.text_widget.verticalScrollBar().setValue)
        self.text_widget.verticalScrollBar().rangeChanged.connect(self.scrollbar.setRange)
        
        editor_layout.addStretch(1)
        editor_layout.addWidget(self.text_widget)
        editor_layout.addStretch(1)
        editor_layout.addWidget(self.sidebar_widget)
        editor_layout.addWidget(self.scrollbar)
        
        self.layout.addWidget(self.editor_container)

    def _toggle_bullet_list(self) -> None:
        cursor = self.text_widget.textCursor()
        if cursor.currentList():
            pass
        else:
            from PyQt6.QtGui import QTextListFormat
            list_fmt = QTextListFormat()
            list_fmt.setStyle(QTextListFormat.Style.ListDisc)
            cursor.createList(list_fmt)

    def _apply_numbering(self, action) -> None:
        from PyQt6.QtGui import QTextListFormat, QTextBlockFormat
        text = action.text()
        style_map = {
            "None": None,
            "1.": QTextListFormat.Style.ListDecimal,
            "1)": QTextListFormat.Style.ListDecimal,
            "I.": QTextListFormat.Style.ListUpperRoman,
            "A.": QTextListFormat.Style.ListUpperAlpha,
            "a)": QTextListFormat.Style.ListLowerAlpha,
            "a.": QTextListFormat.Style.ListLowerAlpha,
            "i.": QTextListFormat.Style.ListLowerRoman,
        }
        cursor = self.text_widget.textCursor()
        style = style_map.get(text)
        if style is None:
            new_fmt = QTextBlockFormat()
            cursor.setBlockFormat(new_fmt)
        else:
            list_fmt = QTextListFormat()
            list_fmt.setStyle(style)
            list_fmt.setNumberSuffix(")" if ")" in text else ".")
            cursor.createList(list_fmt)

    def _apply_paper_theme(self) -> None:
        bg = "#2b2b2b" if self.is_dark_paper else "white"
        fg = "#ffffff" if self.is_dark_paper else "black"
        border = "#444444" if self.is_dark_paper else "#d3d3d3"
        self.text_widget.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 2px;
                padding: 40px;
            }}
        """)

    def _toggle_theme(self) -> None:
        self.is_dark_paper = not getattr(self, 'is_dark_paper', True)
        self._apply_paper_theme()


    def _handle_export(self) -> None:
        try:
            from llex.export import DocumentExporter
        except ImportError:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self.main_window, "Error", "Export module not found.")
            return

        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        filepath, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Export Document",
            "",
            "Microsoft Word (*.docx);;PDF Document (*.pdf);;OpenDocument Text (*.odt);;Rich Text Format (*.rtf);;HTML Document (*.html);;EPUB eBook (*.epub);;Markdown (*.md);;Text File (*.txt)"
        )
        
        if filepath:
            try:
                exporter = DocumentExporter(self.text_widget.document())
                exporter.export(filepath)
                self.status_label.setText(f"Exported to {filepath}")
            except Exception as e:
                QMessageBox.critical(self.main_window, "Export Failed", str(e))


    def _handle_export(self) -> None:
        try:
            from llex.export import DocumentExporter
        except ImportError:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self.main_window, "Error", "Export module not found.")
            return

        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        filepath, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Export Document",
            "",
            "Microsoft Word (*.docx);;PDF Document (*.pdf);;OpenDocument Text (*.odt);;Rich Text Format (*.rtf);;HTML Document (*.html);;EPUB eBook (*.epub);;Markdown (*.md);;Text File (*.txt)"
        )
        
        if filepath:
            try:
                exporter = DocumentExporter(self.text_widget.document())
                exporter.export(filepath)
                self.status_label.setText(f"Exported to {filepath}")
            except Exception as e:
                QMessageBox.critical(self.main_window, "Export Failed", str(e))

    def _toggle_sidebar(self) -> None:
        self.sidebar_widget.setVisible(not self.sidebar_widget.isVisible())

    def _build_menu(self) -> None:
        menu_bar = self.main_window.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction(self.action_new)
        file_menu.addAction(self.action_open)
        file_menu.addAction(self.action_save)
        file_menu.addSeparator()
        file_menu.addAction(self.action_export)
        
        # Format menu
        format_menu = menu_bar.addMenu("Format")
        format_menu.addAction(self.action_header_footer)
        format_menu.addAction(self.action_page_orientation)
        format_menu.addSeparator()
        format_menu.addAction(self.action_bold)
        format_menu.addAction(self.action_italic)
        format_menu.addAction(self.action_underline)
        format_menu.addSeparator()
        format_menu.addAction(self.action_color)
        format_menu.addAction(self.action_highlight)
        
        # LLM menu
        llm_menu = menu_bar.addMenu("LLM")
        llm_menu.addAction(self.action_add_llm)
        llm_menu.addAction(self.action_manage_llm)
        llm_menu.addSeparator()
        llm_menu.addAction(self.action_llm_settings)

        # Settings
        settings_menu = menu_bar.addMenu("Settings")
        settings_menu.addAction(self.action_theme)

    def _create_ribbon_group(self, title: str, layout: QLayout) -> QWidget:
        group_container = QWidget()
        vlayout = QVBoxLayout(group_container)
        vlayout.setContentsMargins(4, 0, 4, 0)
        vlayout.setSpacing(2)
        
        content = QWidget()
        content.setLayout(layout)
        vlayout.addWidget(content, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        
        lbl = QLabel(title)
        lbl.setStyleSheet("color: #999999; font-size: 10px;")
        vlayout.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        
        wrapper = QWidget()
        h = QHBoxLayout(wrapper)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(group_container)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet("color: #444444;")
        h.addWidget(sep)
        return wrapper

    def _build_toolbar(self) -> None:
        self.toolbar = QToolBar("Formatting")
        self.toolbar.setStyleSheet('''
            QToolBar { background-color: #2b2b2b; color: white; border-bottom: 1px solid #444444; padding: 4px; }
            QToolButton { background: transparent; border: 1px solid transparent; border-radius: 4px; color: white; padding: 4px; font-size: 14px; font-weight: bold; }
            QToolButton:hover { background-color: #3a3d41; border: 1px solid #555555; }
            QToolButton:checked { background-color: #505357; border: 1px solid #555555; }
            QPushButton { background: white; color: black; border: 1px solid #ccc; padding: 4px; }
        ''')
        self.toolbar.setMovable(False)
        self.main_window.addToolBar(self.toolbar)

        # 1. Clipboard
        clip_layout = QHBoxLayout()
        clip_layout.setContentsMargins(0, 0, 0, 0)
        btn_paste = QToolButton()
        btn_paste.setText("📋\nPaste")
        btn_paste.clicked.connect(self.text_widget.paste)
        btn_paste.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        btn_paste.setFixedSize(50, 50)
        
        col = QVBoxLayout()
        col.setSpacing(0)
        btn_cut = QToolButton(); btn_cut.setText("✂ Cut"); btn_cut.clicked.connect(self.text_widget.cut)
        btn_copy = QToolButton(); btn_copy.setText("📄 Copy"); btn_copy.clicked.connect(self.text_widget.copy)
        btn_fmt = QToolButton(); btn_fmt.setText("🖌 Format Painter")
        col.addWidget(btn_cut)
        col.addWidget(btn_copy)
        col.addWidget(btn_fmt)
        clip_layout.addWidget(btn_paste)
        clip_layout.addLayout(col)
        self.toolbar.addWidget(self._create_ribbon_group("Clipboard", clip_layout))

        # 2. Font
        font_layout = QVBoxLayout()
        font_layout.setContentsMargins(0, 0, 0, 0)
        font_layout.setSpacing(2)
        row1 = QHBoxLayout(); row1.setSpacing(2); row1.setContentsMargins(0, 0, 0, 0)
        self.combo_font = QFontComboBox()
        self.combo_font.setCurrentFont(QFont("Segoe UI"))
        self.combo_font.currentFontChanged.connect(self._change_font_family)
        row1.addWidget(self.combo_font)
        
        self.combo_size = QComboBox()
        self.combo_size.addItems([str(size) for size in (8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 72)])
        self.combo_size.setCurrentText("12")
        self.combo_size.currentTextChanged.connect(self._change_font_size)
        row1.addWidget(self.combo_size)
        
        for t in ["A↑", "A↓", "Aa", "A\u232b"]:
            b = QToolButton(); b.setText(t); row1.addWidget(b)
        
        row2 = QHBoxLayout(); row2.setSpacing(2); row2.setContentsMargins(0, 0, 0, 0)
        for action, t in zip([self.action_bold, self.action_italic, self.action_underline], ["B", "I", "U"]):
            b = QToolButton(); b.setDefaultAction(action); b.setText(t); row2.addWidget(b)
        
        for t in ["ab", "x₂", "x²"]:
            b = QToolButton(); b.setText(t); b.setCheckable(True); row2.addWidget(b)
        
        b = QToolButton(); b.setDefaultAction(self.action_highlight); b.setText("ab"); row2.addWidget(b)
        b = QToolButton(); b.setDefaultAction(self.action_color); b.setText("A"); row2.addWidget(b)

        font_layout.addLayout(row1)
        font_layout.addLayout(row2)
        self.toolbar.addWidget(self._create_ribbon_group("Font", font_layout))

        # 3. Paragraph
        para_layout = QVBoxLayout()
        para_layout.setContentsMargins(0, 0, 0, 0)
        para_layout.setSpacing(2)
        p_row1 = QHBoxLayout(); p_row1.setSpacing(2); p_row1.setContentsMargins(0, 0, 0, 0)
        
        self.btn_bullet = QToolButton()
        self.btn_bullet.setText("•")
        self.btn_bullet.clicked.connect(self._toggle_bullet_list)
        p_row1.addWidget(self.btn_bullet)
        
        self.btn_numbering = QToolButton()
        self.btn_numbering.setText("1.")
        self.btn_numbering.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        num_menu = QMenu(self.btn_numbering)
        for style_name in ["None", "1.", "1)", "I.", "A.", "a)", "a.", "i."]:
            action = num_menu.addAction(style_name)
            action.triggered.connect(lambda checked, s=style_name: self._apply_numbering_style(s))
        self.btn_numbering.setMenu(num_menu)
        p_row1.addWidget(self.btn_numbering)

        p_row2 = QHBoxLayout(); p_row2.setSpacing(2); p_row2.setContentsMargins(0, 0, 0, 0)
        for action, t in zip([self.action_align_left, self.action_align_center, self.action_align_right], ["Left", "Center", "Right"]):
            b = QToolButton(); b.setDefaultAction(action); b.setText(t); p_row2.addWidget(b)

        para_layout.addLayout(p_row1)
        para_layout.addLayout(p_row2)
        self.toolbar.addWidget(self._create_ribbon_group("Paragraph", para_layout))

        # 4. Headings
        headings_layout = QHBoxLayout()
        headings_layout.setContentsMargins(0, 0, 0, 0)
        headings_layout.setSpacing(4)
        self.combo_heading = QComboBox()
        self.combo_heading.addItems([
            "Normal text",
            "Title",
            "Subtitle",
            "Heading 1",
            "Heading 2",
            "Heading 3",
            "Heading 4",
            "Heading 5"
        ])
        self.combo_heading.setMinimumWidth(120)
        self.combo_heading.currentTextChanged.connect(self._apply_heading_style)
        headings_layout.addWidget(self.combo_heading)
        self.toolbar.addWidget(self._create_ribbon_group("Headings", headings_layout))

        # 5. Editing
        edit_layout = QVBoxLayout()
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.setSpacing(0)
        for t in ["🔎 Find", "🔁 Replace", "↖ Select"]:
            btn = QToolButton(); btn.setText(t); edit_layout.addWidget(btn)
        self.toolbar.addWidget(self._create_ribbon_group("Editing", edit_layout))

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(spacer)
        
        btn_sidebar = QToolButton()
        btn_sidebar.setDefaultAction(self.action_toggle_sidebar)
        btn_sidebar.setText("◨ llex assistant")
        self.toolbar.addWidget(btn_sidebar)

    def _build_status_bar(self) -> None:
        self.status_bar = self.main_window.statusBar()
        self.status_bar.setStyleSheet("QStatusBar { background-color: #1e1e1e; border-top: 1px solid #444444; }")
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: white;")
        self.word_count_label = QLabel("0 words | 0 chars")
        self.word_count_label.setStyleSheet("color: white;")
        
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

    def _apply_heading_style(self, style_name: str) -> None:
        cursor = self.text_widget.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)

        block_fmt = QTextBlockFormat()
        char_fmt = QTextCharFormat()

        block_fmt.setTopMargin(0)
        block_fmt.setBottomMargin(8)
        char_fmt.setFontPointSize(12)
        char_fmt.setFontWeight(QFont.Weight.Normal)
        char_fmt.clearForeground()

        levels = {
            "Normal text": 0, "Title": 1, "Subtitle": 2, 
            "Heading 1": 1, "Heading 2": 2, "Heading 3": 3, 
            "Heading 4": 4, "Heading 5": 5
        }

        if style_name == "Title":
            char_fmt.setFontPointSize(26)
            char_fmt.setFontWeight(QFont.Weight.Bold)
            block_fmt.setTopMargin(24)
            block_fmt.setBottomMargin(8)
        elif style_name == "Subtitle":
            char_fmt.setFontPointSize(16)
            char_fmt.setForeground(QColor("#888888"))
            block_fmt.setBottomMargin(16)
            char_fmt.setFontWeight(QFont.Weight.Normal)
        elif style_name == "Heading 1":
            char_fmt.setFontPointSize(20)
            char_fmt.setFontWeight(QFont.Weight.Bold)
            block_fmt.setTopMargin(18)
            block_fmt.setBottomMargin(6)
        elif style_name == "Heading 2":
            char_fmt.setFontPointSize(16)
            char_fmt.setFontWeight(QFont.Weight.Bold)
            block_fmt.setTopMargin(14)
            block_fmt.setBottomMargin(4)
        elif style_name == "Heading 3":
            char_fmt.setFontPointSize(14)
            char_fmt.setFontWeight(QFont.Weight.DemiBold)
            block_fmt.setTopMargin(10)
            block_fmt.setBottomMargin(4)
        elif style_name == "Heading 4":
            char_fmt.setFontPointSize(12)
            char_fmt.setFontWeight(QFont.Weight.DemiBold)
            block_fmt.setTopMargin(8)
            block_fmt.setBottomMargin(2)
        elif style_name == "Heading 5":
            char_fmt.setFontPointSize(11)
            char_fmt.setFontWeight(QFont.Weight.DemiBold)
            block_fmt.setTopMargin(8)
            block_fmt.setBottomMargin(2)

        try:
            block_fmt.setHeadingLevel(levels.get(style_name, 0))
        except AttributeError:
            pass

        cursor.setBlockFormat(block_fmt)
        cursor.mergeCharFormat(char_fmt)
        self.text_widget.setTextCursor(cursor)
        
        self.combo_size.blockSignals(True)
        self.combo_size.setCurrentText(str(int(char_fmt.fontPointSize())))
        self.combo_size.blockSignals(False)

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

    def _edit_header_footer(self) -> None:
        h, ok = QInputDialog.getText(self.main_window, "Header", "Enter Header Text (Use <Page Num>):", text=self.text_widget.header_text)
        if ok:
            self.text_widget.header_text = h
        f, ok = QInputDialog.getText(self.main_window, "Footer", "Enter Footer Text (Use <Page Num>):", text=self.text_widget.footer_text)
        if ok:
            self.text_widget.footer_text = f
        self.text_widget._update_page_headers_footers()

    def _toggle_orientation(self) -> None:
        if self.text_widget.page_width == 816:
            self.text_widget.page_width = 1056
            self.text_widget.page_height = 816
        else:
            self.text_widget.page_width = 816
            self.text_widget.page_height = 1056
        # Update all pages with new dimensions
        for page in self.text_widget.pages:
            page.page_width = self.text_widget.page_width
            page.page_height = self.text_widget.page_height
            page.setFixedWidth(self.text_widget.page_width)
            page.setFixedHeight(self.text_widget.page_height)

    def _handle_export(self) -> None:
        filters = (
            "Microsoft Word (*.docx);;"
            "PDF Document (*.pdf);;"
            "OpenDocument (*.odt);;"
            "Rich Text Format (*.rtf);;"
            "Web Page Zipped (*.zip);;"
            "EPUB Publication (*.epub);;"
            "Markdown (*.md);;"
            "Plain Text (*.txt)"
        )
        filepath, _ = QFileDialog.getSaveFileName(self.main_window, "Export Document", "", filters)
        if not filepath:
            return
            
        exporter = DocumentExporter(self.text_widget.document())
        try:
            exporter.export(filepath)
            QMessageBox.information(self.main_window, "Export Successful", f"Successfully exported to {filepath}")
        except Exception as e:
            QMessageBox.critical(self.main_window, "Export Error", f"An error occurred during export:\n{e}")

    def run(self) -> None:
        self.main_window.show()
        sys.exit(self.app.exec())
