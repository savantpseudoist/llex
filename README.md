# LLex — Local Language Expression Engine

LLex is a Python-native word processor shell that mirrors the familiar controls of Microsoft Word while surfacing a local LLM hook similar to modern AI code editors. The initial release keeps dependencies in the standard library, ships a structured `Document` model, and demonstrates how writing prompts, summarization, and rewriting can be driven by a pluggable bridge.

## Key capabilities

- **Document model + persistence**: `llex.document` tracks metadata, pagination hints, and reusable styles while saving in a lightweight JSON-based `.llex` container.
- **Tkinter-powered editor**: ribbon-style formatting, simple styles, alignment commands, and a status bar provide the feel of a rich text surface without heavyweight frameworks.
- **LLM bridge hooks**: `LocalLLMBridge` is a placeholder for a local language model; menu commands call the bridge to summarize, rewrite, or outline the current selection or document body.
- **Command-line launch**: `python -m llex.main` or the `llex` script from `pyproject.toml` spins up the window and optionally loads an existing document.

## Getting started

1. Create a virtual environment and install the package:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -e .
   ```
2. Launch the editor:
   ```bash
   python -m llex.main path/to/document.llex
   ```
3. Use the File and Format ribbons to apply formatting, or open the **LLM** menu to summarize or rewrite content.

## Local LLM integration

LLex expects a local inference engine in the future. For now, `LocalLLMBridge` simulates prompts by weaving simple heuristics, but you can point LLex at a real model by setting `LLEX_LOCAL_MODEL` in your environment or extending the bridge.

## Architectural notes

- `llex.document` encapsulates the document tree, styles, and disk persistence strategy. The UI writes back to this model before saving to keep state consistent.
- `llex.ui` wires Tkinter widgets, formatting tags, and command menus with the document model plus the LLM bridge.
- `llex.llm` isolates the language-model contract; replacing it with Hugging Face inference or a local server only requires implementing the same methods.
- `dev_docs/software_engineering_journal.md` captures the rationale for this iteration and should be updated as the project evolves.
