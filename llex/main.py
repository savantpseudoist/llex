"""Entry-point for the LLex desktop application."""

from __future__ import annotations

import sys
import threading
import webview
import uvicorn
from pathlib import Path

from .document import Document
from .llm import LocalLLMBridge
from .api import app, register_services

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

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
    
    register_services(document, bridge)

    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    webview.create_window(f"{document.title} - LLex", "http://127.0.0.1:8000", width=1100, height=760)
    webview.start()

if __name__ == "__main__":
    main()
