"""Metadata extraction from AsciiDoc content (titles, keywords)."""

from __future__ import annotations

import re

_TITLE_RE = re.compile(r"^= (.+)$", re.MULTILINE)

_FIRST_PARA_RE = re.compile(
    r"^= .+\n"
    r"(?::[^\n]*\n)*"
    r"\n+"
    r"((?:[^\n=:].+\n?)+)",
    re.MULTILINE,
)


def extract_title(adoc: str) -> str:
    """Extract the = Title from AsciiDoc content."""
    m = _TITLE_RE.search(adoc)
    return m.group(1).strip() if m else "Untitled"


def extract_keywords(adoc: str) -> str:
    """Extract key concepts from section headings (== level) as a compact description."""
    headings = re.findall(r"^== (.+)$", adoc, re.MULTILINE)
    if not headings:
        m = _FIRST_PARA_RE.search(adoc)
        if m:
            text = m.group(1).strip().split(".")[0]
            text = re.sub(r"[`{}\[\]<>]", "", text)
            text = " ".join(text.split())
            return text[:100]
        return ""

    clean = []
    for h in headings:
        h = re.sub(r"[`{}\[\]<>]", "", h).strip()
        if h and h.lower() not in ("see also", "what to read next"):
            clean.append(h)
        if len(clean) >= 5:
            break

    result = ""
    for kw in clean:
        candidate = f"{result}, {kw}" if result else kw
        if len(candidate) > 100:
            break
        result = candidate
    return result
