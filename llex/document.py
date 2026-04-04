from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json


@dataclass
class StyleDefinition:
    name: str
    font_family: str
    font_size: int
    weight: str
    slant: str
    underline: bool
    alignment: str
    color: str


class Document:
    """Capture the logical document model and metadata."""

    def __init__(self, title: str = "Untitled Document") -> None:
        self.title = title
        self.created_at = datetime.utcnow()
        self.modified_at = self.created_at
        self.paragraphs: List[str] = [""]
        self.html_content: str = "<p>Start typing your document...</p>"
        self.styles: Dict[str, StyleDefinition] = self._default_styles()
        self.page_size = (8.5, 11.0)
        self.margins = (0.75, 0.75, 0.75, 0.75)
        self.path: Optional[Path] = None

    def _default_styles(self) -> Dict[str, StyleDefinition]:
        return {
            "Normal": StyleDefinition(
                name="Normal",
                font_family="Segoe UI",
                font_size=12,
                weight="normal",
                slant="roman",
                underline=False,
                alignment="left",
                color="#111111",
            ),
            "Heading": StyleDefinition(
                name="Heading",
                font_family="Segoe UI",
                font_size=16,
                weight="bold",
                slant="roman",
                underline=False,
                alignment="left",
                color="#0b3d91",
            ),
        }

    @property
    def text(self) -> str:
        return "\n".join(self.paragraphs)

    @text.setter
    def text(self, value: str) -> None:
        self.paragraphs = value.splitlines() or [""]
        self.touch()

    def apply_paragraph(self, index: int, value: str) -> None:
        if 0 <= index < len(self.paragraphs):
            self.paragraphs[index] = value
        else:
            self.paragraphs.append(value)
        self.touch()

    def touch(self) -> None:
        self.modified_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, object]:
        return {
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "paragraphs": self.paragraphs,
            "styles": {name: asdict(style) for name, style in self.styles.items()},
            "page_size": self.page_size,
            "margins": self.margins,
        }

    def save(self, path: Path | str) -> None:
        target = Path(path)
        target.parent.mkdir(exist_ok=True, parents=True)
        self.touch()
        with target.open("w", encoding="utf-8") as writer:
            json.dump(self.to_dict(), writer, indent=2)
        self.path = target

    @classmethod
    def load(cls, path: Path | str) -> Document:
        target = Path(path)
        with target.open("r", encoding="utf-8") as reader:
            payload = json.load(reader)
        document = cls(title=payload.get("title", "Untitled Document"))
        document.created_at = datetime.fromisoformat(payload.get("created_at", document.created_at.isoformat()))
        document.modified_at = datetime.fromisoformat(payload.get("modified_at", document.modified_at.isoformat()))
        document.paragraphs = payload.get("paragraphs", [""])
        document.styles = {
            name: StyleDefinition(**style_data)
            for name, style_data in payload.get("styles", {}).items()
        }
        document.page_size = tuple(payload.get("page_size", document.page_size))
        document.margins = tuple(payload.get("margins", document.margins))
        document.path = target
        return document

    def is_saved(self) -> bool:
        return self.path is not None
