from __future__ import annotations

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QScrollArea, QWidget   
)
from PyQt6.QtGui import QFont, QTextCursor, QTextDocument
from PyQt6.QtCore import Qt, pyqtSignal


class PageWidget(QFrame):
    """
    Represents a single physical page within the pagination system.
    Contains header, editor, and footer sections with fixed page dimensions.    
    """

    contentsChanged = pyqtSignal()
    cursorPositionChanged = pyqtSignal()

    def __init__(self, page_index: int = 0, parent=None):
        super().__init__(parent)
        self.page_index = page_index
        self.page_width = 816
        self.page_height = 1056
        self.editor_height = 900  # Height reserved for text editing (page_height - header - footer margins)

        # Frame styling
        self.setFrameShape(QFrame.Shape.Box)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setLineWidth(1)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 2px;
            }
        """)

        # Fixed dimensions
        self.setFixedWidth(self.page_width)
        self.setFixedHeight(self.page_height)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(10)

        # Header label (fixed height)
        self.header_label = QLabel()
        self.header_label.setFixedHeight(30)
        self.header_label.setStyleSheet("color: #888888; font-size: 9pt; background: transparent; border: none;")
        layout.addWidget(self.header_label)

        # Main text editor (borderless, scrollbar off)
        self.editor = QTextEdit()
        self.editor.setStyleSheet("""
            QTextEdit {
                background-color: white;
                color: #000000;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.editor.setFont(QFont("Segoe UI", 12))

        # Connect editor signals
        self.editor.document().contentsChanged.connect(self._on_contents_changed)
        self.editor.cursorPositionChanged.connect(self.cursorPositionChanged)   

        layout.addWidget(self.editor, 1)

        # Footer label (fixed height)
        self.footer_label = QLabel()
        self.footer_label.setFixedHeight(30)
        self.footer_label.setStyleSheet("color: #888888; font-size: 9pt; background: transparent; border: none;")
        layout.addWidget(self.footer_label)

    def _on_contents_changed(self):
        """Emit signal when document contents change."""
        self.contentsChanged.emit()

    def set_header(self, text: str):
        """Set header text with <Page Num> substitution."""
        display_text = text.replace("<Page Num>", str(self.page_index + 1))     
        self.header_label.setText(display_text)

    def set_footer(self, text: str):
        """Set footer text with <Page Num> substitution."""
        display_text = text.replace("<Page Num>", str(self.page_index + 1))     
        self.footer_label.setText(display_text)

    def get_text(self) -> str:
        """Get all text from the editor."""
        return self.editor.toPlainText()

    def set_text(self, text: str):
        """Set text in the editor."""
        self.editor.setPlainText(text)

    def get_document(self):
        """Get the QTextDocument from the editor."""
        return self.editor.document()

    def get_text_cursor(self) -> QTextCursor:
        """Get the current text cursor."""
        return self.editor.textCursor()

    def set_text_cursor(self, cursor: QTextCursor):
        """Set the text cursor."""
        self.editor.setTextCursor(cursor)

    def textCursor(self) -> QTextCursor:
        """Alias for get_text_cursor (compatibility)."""
        return self.get_text_cursor()

    def setTextCursor(self, cursor: QTextCursor):
        """Alias for set_text_cursor (compatibility)."""
        self.set_text_cursor(cursor)

    def toPlainText(self) -> str:
        """Alias for get_text (compatibility)."""
        return self.get_text()

    def setPlainText(self, text: str):
        """Alias for set_text (compatibility)."""
        self.set_text(text)

    def document(self):
        """Compatibility method."""
        return self.get_document()

    def currentCharFormat(self):
        """Get current character format at cursor."""
        return self.editor.currentCharFormat()

    def mergeCurrentCharFormat(self, fmt):
        """Merge character format at cursor."""
        return self.editor.mergeCurrentCharFormat(fmt)

    def setAlignment(self, alignment):
        """Set text alignment."""
        self.editor.setAlignment(alignment)

    def setFont(self, font: QFont):
        """Set the editor font."""
        self.editor.setFont(font)

    def font(self) -> QFont:
        """Get the editor font."""
        return self.editor.font()

    def paste(self):
        """Paste from clipboard."""
        self.editor.paste()

    def copy(self):
        """Copy to clipboard."""
        self.editor.copy()

    def cut(self):
        """Cut to clipboard."""
        self.editor.cut()

    def get_document_height(self) -> int:
        """Get the document height in pixels."""
        doc = self.editor.document()
        return int(doc.size().height())

    def is_overflowing(self) -> bool:
        """Check if document content exceeds editable height."""
        return self.get_document_height() > self.editor_height


class PagedEditorContainer(QScrollArea):
    """
    Multi-widget pagination container hosting an array of PageWidget instances. 
    Manages text overflow, cursor navigation between pages, and header/footer injection.
    """

    textChanged = pyqtSignal()
    cursorPositionChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.page_width = 816
        self.page_height = 1056
        self.header_text = ""
        self.footer_text = ""
        self.pages: list[PageWidget] = []

        # Setup scroll area
        self.setStyleSheet("""
            QScrollArea {
                background-color: #f0f0f0;
            }
        """)
        self.setWidgetResizable(False)

        # Container widget with vertical layout for pages
        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(20, 20, 20, 20)
        self.container_layout.setSpacing(40)  # Physical gap between pages      
        self.container_layout.addStretch()

        self.setWidget(self.container_widget)

        # Create first page
        self._add_page()

    def _add_page(self):
        """Add a new page to the container."""
        page = PageWidget(len(self.pages), self)
        page.contentsChanged.connect(self._on_page_changed)
        page.cursorPositionChanged.connect(self.cursorPositionChanged)

        # Insert before the final stretch
        insert_index = self.container_layout.count() - 1
        self.container_layout.insertWidget(insert_index, page)

        self.pages.append(page)
        self._update_page_headers_footers()

    def _remove_page(self, index: int):
        """Remove a page at the given index."""
        if index < 0 or index >= len(self.pages):
            return
        if len(self.pages) <= 1:  # Always keep at least one page
            return

        page = self.pages.pop(index)
        self.container_layout.removeWidget(page)
        page.deleteLater()
        self._update_page_headers_footers()

    def _update_page_headers_footers(self):
        """Update headers and footers for all pages."""
        for page in self.pages:
            page.set_header(self.header_text)
            page.set_footer(self.footer_text)

    def _on_page_changed(self):
        """Handle page content change - implements overflow logic."""
        # TODO: Implement overflow detection and text migration
        self.textChanged.emit()

    def _get_all_text(self) -> str:
        """Get concatenated text from all pages."""
        return "\n\n".join(page.get_text() for page in self.pages)

    def _set_all_text(self, text: str):
        """Distribute text across pages."""
        # Clear all but first page
        for page in self.pages[1:]:
            self._remove_page(self.pages.index(page))

        # Split text into pages (naive split on \n\n)
        parts = text.split("\n\n")

        # Fill first page
        if self.pages:
            self.pages[0].set_text(parts[0] if parts else "")

        # Create additional pages as needed
        for part in parts[1:]:
            self._add_page()
            self.pages[-1].set_text(part)

    # --- Compatibility API (to replace PagedTextEdit) ---

    def textChanged(self):
        """Signal emitted when text changes."""
        return self.textChanged

    def cursorPositionChanged(self):
        """Signal emitted when cursor position changes."""
        return self.cursorPositionChanged

    def toPlainText(self) -> str:
        """Get all text from all pages."""
        return self._get_all_text()

    def setPlainText(self, text: str):
        """Set text across all pages."""
        self._set_all_text(text)

    def textCursor(self) -> QTextCursor:
        """Get text cursor from the currently focused page."""
        if self.pages:
            return self.pages[0].textCursor()
        return QTextCursor()

    def setTextCursor(self, cursor: QTextCursor):
        """Set cursor in the first page."""
        if self.pages:
            self.pages[0].setTextCursor(cursor)

    def document(self):
        """Get document from the first page."""
        if self.pages:
            return self.pages[0].document()
        return None

    def currentCharFormat(self):
        """Get format from first page."""
        if self.pages:
            return self.pages[0].currentCharFormat()
        return None

    def mergeCurrentCharFormat(self, fmt):
        """Merge format in first page."""
        if self.pages:
            return self.pages[0].mergeCurrentCharFormat(fmt)

    def setAlignment(self, alignment):
        """Set alignment for first page."""
        if self.pages:
            self.pages[0].setAlignment(alignment)

    def setFont(self, font: QFont):
        """Set font for all pages."""
        for page in self.pages:
            page.setFont(font)

    def font(self) -> QFont:
        """Get font from first page."""
        if self.pages:
            return self.pages[0].font()
        return QFont()

    def paste(self):
        """Paste in first page."""
        if self.pages:
            self.pages[0].paste()

    def copy(self):
        """Copy from first page."""
        if self.pages:
            self.pages[0].copy()

    def cut(self):
        """Cut from first page."""
        if self.pages:
            self.pages[0].cut()

    def setVerticalScrollBarPolicy(self, policy):
        """Set scroll bar policy."""
        super().setVerticalScrollBarPolicy(policy)

    def verticalScrollBar(self):
        """Get the vertical scrollbar."""
        return super().verticalScrollBar()

    def viewport(self):
        """Get the viewport."""
        return super().viewport()

    def setStyleSheet(self, stylesheet: str):
        """Set stylesheet for pages."""
        super().setStyleSheet(stylesheet)
        for page in self.pages:
            page.editor.setStyleSheet("""
                QTextEdit {
                    background-color: white;
                    color: #000000;
                    border: none;
                    padding: 0px;
                    margin: 0px;
                }
            """)

    def setFixedWidth(self, width: int):
        """Set fixed width (applies to pages)."""
        # Pages maintain their own fixed width
        pass
