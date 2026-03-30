from __future__ import annotations

import os
import random
import re
from typing import Optional


class LocalLLMBridge:
    """Placeholder bridge to a future local LLM service."""

    def __init__(self, model_path: Optional[str] = None, summary_size: int = 3) -> None:
        self.model_path = model_path or os.environ.get("LLEX_LOCAL_MODEL", "")
        self.summary_size = summary_size

    def summarize(self, text: str) -> str:
        """Return a deterministic summary using sentence slicing heuristics."""
        sentences = self._split_sentences(text)
        selected = sentences[: self.summary_size] or sentences[-self.summary_size :]
        return " ".join(selected).strip() or "Nothing to summarize."

    def rewrite_with_tone(self, text: str, tone: str = "professional") -> str:
        """Pretend to rewrite text with the requested tone by reinserting cues."""
        tone_keyword = tone.capitalize()
        core = text.strip() or ""
        if not core:
            return "Select text to rewrite."
        suffix = {
            "friendly": "Let's keep it light and human.",
            "technical": "Maintain precise terminology.",
            "professional": "Keep formatting consistent with internal standards.",
            "creative": "Add imagery where suitable.",
        }
        cue = suffix.get(tone.lower(), "Adjust the wording to match the desired tone.")
        lines = re.split(r"\n+", core)
        sampled = random.choice(lines) if lines else core
        return f"[{tone_keyword} tone] {sampled} ... {cue}"

    def outline(self, text: str) -> str:
        """Simulate outlining by enumerating the leading sentences."""
        sentences = self._split_sentences(text)
        if not sentences:
            return "Add more text to outline."
        seed = sentences[: min(5, len(sentences))]
        outline_lines = [f"{idx + 1}. {line}" for idx, line in enumerate(seed)]
        return "\n".join(outline_lines)

    def _split_sentences(self, text: str) -> list[str]:
        if not text:
            return []
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        return [part for part in parts if part]
