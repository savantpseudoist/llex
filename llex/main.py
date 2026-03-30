"""Entry-point for the LLex desktop application."""

from __future__ import annotations

import sys
from pathlib import Path

from .document import Document
from .llm import LocalLLMBridge
from .ui import EditorApp


def main(argv: list[str] | None = None) -> None:
    """Bootstraps the LLex editor and opens an optional document."""
    argv = argv or sys.argv[1:]
    document = Document()
    if argv:
        requested = Path(argv[0])
        if requested.exists():
            document = Document.load(requested)
        else:
            print(f"Document {requested} not found, creating a new one.")
    bridge = LocalLLMBridge()
    app = EditorApp(document=document, llm_bridge=bridge)
    app.run()


if __name__ == "__main__":
    main()
