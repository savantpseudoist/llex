from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import font, filedialog, messagebox, simpledialog
from typing import Iterable

from .document import Document
from .llm import LocalLLMBridge


class EditorApp:
    """Tkinter-based editor window that ties Document + LLM services together."""

    def __init__(self, document: Document, llm_bridge: LocalLLMBridge) -> None:
        self.document = document
        self.llm_bridge = llm_bridge
        self.root = tk.Tk()
        self.root.title(f"{self.document.title} — LLex")
        self.root.geometry("1100x760")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.font_face = tk.StringVar(value="Segoe UI")
        self.font_size = tk.IntVar(value=12)
        self._build_menu()
        self._build_toolbar()
        self._build_editor()
        self._build_status_bar()
        self._load_document_text()

    def run(self) -> None:
        self.root.mainloop()

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self.root)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="New", command=self._new_document)
        file_menu.add_command(label="Open…", command=self._open_document)
        file_menu.add_command(label="Save", command=self._save_document)
        file_menu.add_command(label="Save As…", command=self._save_document_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        menu_bar.add_cascade(label="File", menu=file_menu)

        format_menu = tk.Menu(menu_bar, tearoff=0)
        format_menu.add_command(label="Heading Style", command=lambda: self._apply_style("Heading"))
        format_menu.add_command(label="Normal Style", command=lambda: self._apply_style("Normal"))
        menu_bar.add_cascade(label="Format", menu=format_menu)

        llm_menu = tk.Menu(menu_bar, tearoff=0)
        llm_menu.add_command(label="Summarize Selection", command=self._handle_llm_summarize)
        llm_menu.add_command(label="Rewrite Selection", command=self._handle_llm_rewrite)
        llm_menu.add_command(label="Create Outline", command=self._handle_llm_outline)
        menu_bar.add_cascade(label="LLM", menu=llm_menu)

        self.root.config(menu=menu_bar)

    def _build_toolbar(self) -> None:
        toolbar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        for text, command in (
            ("Bold", self._toggle_bold),
            ("Italic", self._toggle_italic),
            ("Underline", self._toggle_underline),
            ("Align Left", lambda: self._apply_alignment("left")),
            ("Center", lambda: self._apply_alignment("center")),
            ("Align Right", lambda: self._apply_alignment("right")),
        ):
            button = tk.Button(toolbar, text=text, command=command)
            button.pack(side=tk.LEFT, padx=2, pady=2)

        tk.Label(toolbar, text="Font:").pack(side=tk.LEFT, padx=(8, 0))
        font_menu = tk.OptionMenu(toolbar, self.font_face, *self._available_fonts(), command=self._update_text_font)
        font_menu.pack(side=tk.LEFT, padx=2)
        tk.Label(toolbar, text="Size:").pack(side=tk.LEFT, padx=(8, 0))
        size_menu = tk.OptionMenu(toolbar, self.font_size, *self._available_sizes(), command=lambda _: self._update_text_font())
        size_menu.pack(side=tk.LEFT, padx=2)

        llm_frame = tk.Frame(toolbar)
        tk.Button(llm_frame, text="Summarize", command=self._handle_llm_summarize).pack(side=tk.LEFT, padx=2)
        tk.Button(llm_frame, text="Rewrite", command=self._handle_llm_rewrite).pack(side=tk.LEFT, padx=2)
        tk.Button(llm_frame, text="Outline", command=self._handle_llm_outline).pack(side=tk.LEFT, padx=2)
        llm_frame.pack(side=tk.RIGHT, padx=(0, 8))

        toolbar.pack(fill=tk.X)

    def _build_editor(self) -> None:
        self.text_widget = tk.Text(self.root, wrap=tk.WORD, undo=True)
        self.text_widget.pack(fill=tk.BOTH, expand=True)
        self._tag_fonts: dict[str, font.Font] = {}
        self._update_text_font()
        self._configure_font_tag("bold", weight="bold")
        self._configure_font_tag("italic", slant="italic")
        self._configure_font_tag("underline", underline=1)
        self.text_widget.tag_configure("LLexCenter", justify=tk.CENTER)
        self.text_widget.tag_configure("LLexRight", justify=tk.RIGHT)
        self.text_widget.tag_configure("LLexLeft", justify=tk.LEFT)
        self.text_widget.tag_configure("highlight", background="#fff5b1")

    def _build_status_bar(self) -> None:
        self.status_bar = tk.Label(self.root, text="Ready", anchor=tk.W, relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X)

    def _load_document_text(self) -> None:
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert("1.0", self.document.text)
        self._update_status(f"Document loaded: {self.document.title}")

    def _available_fonts(self) -> Iterable[str]:
        return ["Segoe UI", "Arial", "Times New Roman", "Georgia", "Courier New"]

    def _available_sizes(self) -> Iterable[int]:
        return [8, 10, 12, 14, 16, 18, 20, 24]

    def _update_text_font(self, *_args) -> None:
        font_config = font.Font(self.text_widget, family=self.font_face.get(), size=self.font_size.get())
        self.text_widget.configure(font=font_config)
        for tag_font in self._tag_fonts.values():
            tag_font.configure(
                family=self.font_face.get(),
                size=self.font_size.get(),
                weight=tag_font.actual("weight"),
                slant=tag_font.actual("slant"),
                underline=tag_font.actual("underline"),
            )

    def _configure_font_tag(self, tag_name: str, **overrides) -> None:
        tag_font = font.Font(
            self.text_widget,
            family=self.font_face.get(),
            size=self.font_size.get(),
            **overrides,
        )
        self.text_widget.tag_configure(tag_name, font=tag_font)
        self._tag_fonts[tag_name] = tag_font

    def _toggle_tag(self, tag: str) -> None:
        selection = self._selection_range()
        if not selection:
            self._update_status("Select text before toggling formatting.")
            return
        start, end = selection
        if tag in self.text_widget.tag_names(start):
            self.text_widget.tag_remove(tag, start, end)
        else:
            self.text_widget.tag_add(tag, start, end)
        self._update_status(f"Toggled {tag} for selection.")

    def _toggle_bold(self) -> None:
        self._toggle_tag("bold")

    def _toggle_italic(self) -> None:
        self._toggle_tag("italic")

    def _toggle_underline(self) -> None:
        self._toggle_tag("underline")

    def _apply_alignment(self, alignment: str) -> None:
        target_tag = {
            "left": "LLexLeft",
            "center": "LLexCenter",
            "right": "LLexRight",
        }[alignment]
        selection = self._selection_range() or ("1.0", tk.END)
        start, end = selection
        for tag_name in ("LLexLeft", "LLexCenter", "LLexRight"):
            self.text_widget.tag_remove(tag_name, start, end)
        self.text_widget.tag_add(target_tag, start, end)
        self._update_status(f"Aligned selection {alignment}.")

    def _apply_style(self, style_name: str) -> None:
        style = self.document.styles.get(style_name)
        if not style:
            self._update_status("Requested style not found.")
            return
        selection = self._selection_range() or ("1.0", tk.END)
        start, end = selection
        tag_name = f"LLexStyle:{style_name}"
        self.text_widget.tag_configure(
            tag_name,
            font=font.Font(
                family=style.font_family,
                size=style.font_size,
                weight=style.weight,
                slant=style.slant,
                underline=style.underline,
            ),
            foreground=style.color,
            justify=style.alignment,
        )
        self.text_widget.tag_add(tag_name, start, end)
        self._update_status(f"Applied {style_name} style.")

    def _selection_range(self) -> tuple[str, str] | None:
        try:
            return (self.text_widget.index("sel.first"), self.text_widget.index("sel.last"))
        except tk.TclError:
            return None

    def _new_document(self) -> None:
        if self._confirm_discard():
            self.document = Document()
            self._load_document_text()
            self._update_title()

    def _open_document(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("LLex Document", "*.llex"), ("JSON", "*.json")])
        if not path:
            return
        try:
            self.document = Document.load(path)
        except Exception as exc:
            messagebox.showerror("Open Error", f"Failed to open document: {exc}")
            return
        self._load_document_text()
        self._update_title()

    def _save_document(self) -> None:
        if self.document.path:
            self._persist_document()
            self.document.save(self.document.path)
        else:
            self._save_document_as()

    def _save_document_as(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".llex", filetypes=[("LLex Document", "*.llex")])
        if not path:
            return
        self.document.path = Path(path)
        self._persist_document()
        self.document.save(self.document.path)
        self._update_title()

    def _persist_document(self) -> None:
        self.document.text = self.text_widget.get("1.0", tk.END).rstrip("\n")
        self._update_status("Document state synchronized.")

    def _confirm_discard(self) -> bool:
        if not self._document_changed():
            return True
        answer = messagebox.askyesno("Discard changes?", "You have unsaved edits. Discard them?")
        return answer

    def _document_changed(self) -> bool:
        current = self.text_widget.get("1.0", tk.END).rstrip("\n")
        return current != self.document.text

    def _update_title(self) -> None:
        suffix = f" — {Path(self.document.path).name}" if self.document.path else ""
        self.root.title(f"{self.document.title}{suffix} — LLex")

    def _update_status(self, message: str) -> None:
        self.status_bar.config(text=message)

    def _handle_llm_summarize(self) -> None:
        selection = self.text_widget.get("sel.first", "sel.last") if self.text_widget.tag_ranges("sel") else self.text_widget.get("1.0", tk.END)
        summary = self.llm_bridge.summarize(selection)
        messagebox.showinfo("LLM Summary", summary)

    def _handle_llm_rewrite(self) -> None:
        has_selection = bool(self.text_widget.tag_ranges("sel"))
        selection = self.text_widget.get("sel.first", "sel.last") if has_selection else self.text_widget.get("1.0", tk.END)
        tone = simpledialog.askstring("Rewrite Tone", "Enter tone (friendly, technical, professional, creative):", parent=self.root)
        if not tone:
            tone = "professional"
        rewritten = self.llm_bridge.rewrite_with_tone(selection, tone)
        if self.text_widget.tag_ranges("sel"):
            start, end = self.text_widget.index("sel.first"), self.text_widget.index("sel.last")
            self.text_widget.delete(start, end)
            self.text_widget.insert(start, rewritten)
        else:
            self.text_widget.insert(tk.INSERT, rewritten)
        self._update_status(f"LLM rewrote selection with {tone} tone.")

    def _handle_llm_outline(self) -> None:
        text = self.text_widget.get("sel.first", "sel.last") if self.text_widget.tag_ranges("sel") else self.text_widget.get("1.0", tk.END)
        outline = self.llm_bridge.outline(text)
        messagebox.showinfo("LLM Outline", outline)

    def _on_close(self) -> None:
        if self._confirm_discard():
            self.root.destroy()
