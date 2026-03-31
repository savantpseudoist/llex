import zipfile
import re
from pathlib import Path
from PyQt6.QtGui import QTextDocument, QPdfWriter, QTextDocumentWriter, QTextCursor
from PyQt6.QtCore import QMarginsF

class DocumentExporter:
    """Handles exporting a QTextDocument to various formats."""
    
    def __init__(self, document: QTextDocument):
        self.document = document

    def export(self, filepath: str | Path):
        filepath = Path(filepath)
        ext = filepath.suffix.lower()
        
        exporters = {
            ".pdf": self._export_pdf,
            ".docx": self._export_docx,
            ".odt": self._export_odt,
            ".txt": self._export_txt,
            ".rtf": self._export_rtf,
            ".html": self._export_html_zip,
            ".zip": self._export_html_zip,
            ".epub": self._export_epub,
            ".md": self._export_md,
        }
        
        if ext not in exporters:
            raise ValueError(f"Unsupported export format: {ext}")
            
        exporters[ext](filepath)

    def _export_pdf(self, filepath: Path):
        writer = QPdfWriter(str(filepath))
        # Optional: Set standard page margins and A4 size
        writer.setPageMargins(QMarginsF(15, 15, 15, 15))
        self.document.print(writer)

    def _export_txt(self, filepath: Path):
        filepath.write_text(self.document.toPlainText(), encoding="utf-8")

    def _export_md(self, filepath: Path):
        filepath.write_text(self.document.toMarkdown(), encoding="utf-8")

    def _export_html_zip(self, filepath: Path):
        html_content = self.document.toHtml()
        
        # Ensure it has a zip extension
        if filepath.suffix != ".zip":
            filepath = filepath.with_suffix(".zip")
            
        with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("index.html", html_content.encode("utf-8"))

    def _export_rtf(self, filepath: Path):
        writer = QTextDocumentWriter(str(filepath), b"rtf")
        success = writer.write(self.document)
        if not success:
            raise RuntimeError("Failed to export RTF using standard Qt writer.")

    def _export_epub(self, filepath: Path):
        # A minimal EPUB 3 structure
        html_content = self.document.toHtml()
        title = "LLex Document"  # Can be pulled from document metadata later
        
        # We need a proper xhtml body for epub
        xhtml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
        <html xmlns="http://www.w3.org/1999/xhtml">
        <head><title>{title}</title></head>
        <body>{html_content}</body>
        </html>"""

        container_xml = """<?xml version="1.0"?>
        <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
          <rootfiles>
            <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
          </rootfiles>
        </container>"""

        content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
        <package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id">
          <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
            <dc:title>{title}</dc:title>
            <dc:language>en</dc:language>
            <dc:identifier id="pub-id">urn:uuid:12345</dc:identifier>
            <meta property="dcterms:modified">2026-03-31T12:00:00Z</meta>
          </metadata>
          <manifest>
            <item id="content" href="content.xhtml" media-type="application/xhtml+xml"/>
          </manifest>
          <spine>
            <itemref idref="content"/>
          </spine>
        </package>"""

        with zipfile.ZipFile(filepath, "w") as zf:
            # mimetype must be first, uncompressed
            zf.writestr("mimetype", b"application/epub+zip", compress_type=zipfile.ZIP_STORED)
            zf.writestr("META-INF/container.xml", container_xml.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)
            zf.writestr("OEBPS/content.opf", content_opf.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)
            zf.writestr("OEBPS/content.xhtml", xhtml_content.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)

    def _export_docx(self, filepath: Path):
        import docx
        from docx.shared import RGBColor, Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from PyQt6.QtGui import QTextBlock, QTextFragment

        doc = docx.Document()
        
        block = self.document.begin()
        while block.isValid():
            paragraph = doc.add_paragraph()
            
            # Text alignment mapped to docx
            align_map = {
                1: WD_ALIGN_PARAGRAPH.LEFT,
                2: WD_ALIGN_PARAGRAPH.RIGHT,
                4: WD_ALIGN_PARAGRAPH.CENTER,
                8: WD_ALIGN_PARAGRAPH.JUSTIFY
            }
            paragraph.alignment = align_map.get(int(block.blockFormat().alignment()), WD_ALIGN_PARAGRAPH.LEFT)

            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                if fragment.isValid():
                    run = paragraph.add_run(fragment.text())
                    fmt = fragment.charFormat()
                    
                    if fmt.fontWeight() == 700: # QFont.Weight.Bold
                        run.bold = True
                    if fmt.fontItalic():
                        run.italic = True
                    if fmt.fontUnderline():
                        run.underline = True
                        
                    # Sizes
                    if fmt.fontPointSize() > 0:
                        run.font.size = Pt(fmt.fontPointSize())
                        
                    # Colors
                    fg = fmt.foreground().color()
                    # if it's not the default black/window color
                    if fg.isValid() and fg.name() != "#000000":
                        run.font.color.rgb = RGBColor(fg.red(), fg.green(), fg.blue())
                        
                it += 1
            block = block.next()
            
        doc.save(filepath)

    def _export_odt(self, filepath: Path):
        from odf.opendocument import OpenDocumentText
        from odf.text import P, Span
        from odf.style import Style, TextProperties, ParagraphProperties

        doc = OpenDocumentText()
        
        block = self.document.begin()
        
        style_cache = {}
        
        while block.isValid():
            align = int(block.blockFormat().alignment())
            
            p_style_name = f"P_Align_{align}"
            if p_style_name not in style_cache:
                align_str = {1: "start", 2: "end", 4: "center", 8: "justify"}.get(align, "start")
                p_style = Style(name=p_style_name, family="paragraph")
                p_style.addElement(ParagraphProperties(textalign=align_str))
                doc.automaticstyles.addElement(p_style)
                style_cache[p_style_name] = p_style
                
            p = P(stylename=style_cache[p_style_name])

            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                if fragment.isValid():
                    text = fragment.text()
                    fmt = fragment.charFormat()
                    
                    is_bold = fmt.fontWeight() == 700
                    is_italic = fmt.fontItalic()
                    is_underline = fmt.fontUnderline()
                    fg = fmt.foreground().color()
                    color_hex = fg.name() if fg.isValid() and fg.name() != "#000000" else None
                    
                    style_key = f"T_{is_bold}_{is_italic}_{is_underline}_{color_hex}_{fmt.fontPointSize()}"
                    if style_key not in style_cache:
                        t_style = Style(name=style_key, family="text")
                        props = {}
                        if is_bold:
                            props["fontweight"] = "bold"
                        if is_italic:
                            props["fontstyle"] = "italic"
                        if is_underline:
                            props["textunderlinestyle"] = "solid"
                            props["textunderlinewidth"] = "auto"
                            props["textunderlinecolor"] = "font-color"
                        if color_hex:
                            props["color"] = color_hex
                        if fmt.fontPointSize() > 0:
                            props["fontsize"] = f"{fmt.fontPointSize()}pt"
                            
                        t_style.addElement(TextProperties(**props))
                        doc.automaticstyles.addElement(t_style)
                        style_cache[style_key] = t_style
                        
                    span = Span(stylename=style_cache[style_key], text=text)
                    p.addElement(span)
                    
                it += 1
                
            doc.text.addElement(p)
            block = block.next()
            
        doc.save(str(filepath))