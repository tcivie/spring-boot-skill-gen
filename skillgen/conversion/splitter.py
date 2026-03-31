"""Split large markdown files into sub-files by ## headings."""

from __future__ import annotations

import re

SPLIT_THRESHOLD_LINES = 300


def _slugify(heading: str) -> str:
    """Convert a heading to a filename-safe slug."""
    s = heading.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s]+", "-", s)
    return s[:60].rstrip("-")


def split_large_file(md: str, title: str) -> dict[str, str] | None:
    """Split a large markdown file into sub-files by ## headings.

    Returns None if the file is small enough. Otherwise returns a dict:
      {"_index": index_content, "sub-slug.md": sub_content, ...}
    """
    lines = md.split("\n")
    if len(lines) <= SPLIT_THRESHOLD_LINES:
        return None

    sections: list[tuple[str, list[str]]] = []
    preamble: list[str] = []
    current_heading = ""
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if current_heading:
                sections.append((current_heading, current_lines))
            elif current_lines:
                preamble = current_lines
            current_heading = line[3:].strip()
            current_lines = [line]
        else:
            if current_heading:
                current_lines.append(line)
            else:
                preamble.append(line)

    if current_heading:
        sections.append((current_heading, current_lines))

    if len(sections) < 3:
        return None

    result: dict[str, str] = {}
    index_lines = preamble.copy()
    index_lines.append("")
    index_lines.append("## Sections")
    index_lines.append("")
    index_lines.append("Load the relevant section on demand:")
    index_lines.append("")

    for heading, section_lines in sections:
        slug = _slugify(heading)
        filename = f"{slug}.md"
        desc = ""
        for sl in section_lines[1:]:
            sl = sl.strip()
            if sl and not sl.startswith("#") and not sl.startswith("```"):
                desc = sl[:120]
                break
        index_lines.append(f"- `{filename}` — {heading}" + (f": {desc}" if desc else ""))
        result[filename] = "\n".join(section_lines).strip()

    result["_index"] = "\n".join(index_lines).strip()
    return result
