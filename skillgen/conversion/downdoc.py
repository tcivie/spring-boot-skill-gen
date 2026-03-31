"""AsciiDoc to Markdown conversion via downdoc Node.js API."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# Post-processing patterns to clean downdoc output
_POST_PATTERNS = [
    (re.compile(r"\{[\w\-]+\}"), ""),
    (re.compile(r"javadoc:[/\w.$]*?(\w+)\[[^\]]*\]"), r"`\1`"),
    (re.compile(r"javadoc:[/\w.$]*"), ""),
    (re.compile(r"configprop:([\w.\-]+)\[[^\]]*\]"), r"`\1`"),
    (re.compile(r"include-code::\w+\[\]"), ""),
    (re.compile(r"\[([^\]]+)\]\([^)]*\.adoc[^)]*\)"), r"\1"),
    (re.compile(r"xref:[^\[]*\[([^\]]*)\]"), r"\1"),
    (re.compile(
        r'<dl><dt><strong>(.*?)</strong></dt><dd>\s*(.*?)\s*</dd></dl>',
        re.DOTALL,
    ), r"> **\1** \2"),
    (re.compile(r"</?(?:dl|dt|dd|strong|em|q|a[^>]*)>"), ""),
    (re.compile(
        r"\*\*[\U0001f4a1\U0001f4cc\u26a0\ufe0f\u2757\U0001f514]\s*(TIP|NOTE|WARNING|IMPORTANT|CAUTION)\*\*\\?"
    ), r"> **\1:**"),
    (re.compile(r"\n{3,}"), "\n\n"),
]


def _post_process(md: str) -> str:
    for pat, repl in _POST_PATTERNS:
        md = pat.sub(repl, md)
    return md.strip()


def _find_downdoc() -> str | None:
    """Find the downdoc module directory (for require())."""
    search_dirs = [
        Path(__file__).resolve().parent.parent.parent / "node_modules" / "downdoc",
        Path.cwd() / "node_modules" / "downdoc",
        Path.home() / "node_modules" / "downdoc",
    ]
    for d in search_dirs:
        if (d / "package.json").exists():
            return str(d)
    result = subprocess.run(["node", "-e", "console.log(require.resolve('downdoc'))"],
                            capture_output=True, text=True, timeout=5)
    if result.returncode == 0 and result.stdout.strip():
        return "downdoc"
    return None


def batch_convert_adoc(adoc_contents: dict[str, str]) -> dict[str, str | None]:
    """Convert multiple adoc strings to markdown in a single Node process."""
    if not adoc_contents:
        return {}

    downdoc_path = _find_downdoc()
    if downdoc_path is None:
        print("Error: downdoc not found. Run: npm install downdoc", file=sys.stderr)
        sys.exit(1)

    node_script = f"""
const downdoc = require({json.dumps(downdoc_path)});
const input = JSON.parse(require('fs').readFileSync('/dev/stdin', 'utf8'));
const result = {{}};
for (const [key, adoc] of Object.entries(input)) {{
    try {{
        result[key] = downdoc(adoc);
    }} catch (e) {{
        result[key] = null;
    }}
}}
process.stdout.write(JSON.stringify(result));
"""
    try:
        proc = subprocess.run(
            ["node", "-e", node_script],
            input=json.dumps(adoc_contents),
            capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0:
            print(f"  downdoc batch error: {proc.stderr[:200]}", file=sys.stderr)
            return {k: None for k in adoc_contents}

        raw_results = json.loads(proc.stdout)
        return {k: _post_process(v) if v else None for k, v in raw_results.items()}
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        print(f"  downdoc batch failed: {e}", file=sys.stderr)
        return {k: None for k in adoc_contents}
