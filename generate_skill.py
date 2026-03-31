#!/usr/bin/env python3
"""
Spring Boot SKILL Generator
============================
Auto-discovers and generates a structured Claude Code SKILL for any Spring Boot version.

Topics are NOT hardcoded — they are discovered from the GitHub repo tree, then
titles and descriptions are extracted from the AsciiDoc headers.

Output layout:
  <output>/<version>/
    SKILL.md            -- lean index with topic listing
    references/
      <section>/<topic>.md   -- one file per topic, loaded by Claude on demand

Requirements:
  - Python 3.10+, httpx (pip install httpx)
  - Node.js + downdoc  (npm install downdoc)

Usage:
  python generate_skill.py --version 4.0.3
  python generate_skill.py --version 3.4.1 --output ./skills/
  python generate_skill.py --version 4.0.3 --no-cache
  python generate_skill.py --list-versions
  python generate_skill.py --clear-cache [VERSION]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

GITHUB_API = "https://api.github.com/repos/spring-projects/spring-boot"
GITHUB_RAW = "https://raw.githubusercontent.com/spring-projects/spring-boot"
CACHE_DIR = Path(".skill_cache")
MAX_CONCURRENT = 10

# Doc path changed in Boot 4.x
DOC_PATH = {
    3: "spring-boot-project/spring-boot-docs/src/docs/antora/modules",
    4: "documentation/spring-boot-docs/src/docs/antora/modules",
}

# Only discover topics under these modules (relative to the antora modules dir)
MODULES = ["reference", "how-to"]

# Skip these files — they're structural, not topical
SKIP_FILES = {"index.adoc", "nav.adoc"}
SKIP_DIRS = {"partials"}

# ---------------------------------------------------------------------------
# Topic discovery
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DiscoveredTopic:
    """A topic auto-discovered from the repo tree."""
    module: str       # "reference" or "how-to"
    section: str      # directory under pages/ e.g. "web", "features", "data"
    adoc_path: str    # full relative path from module root e.g. "web/servlet.adoc"
    raw_url: str      # full raw GitHub URL


def discover_topics(version: str) -> list[DiscoveredTopic]:
    """Use GitHub Trees API to find all .adoc topic files."""
    major = int(version.split(".")[0])
    base = DOC_PATH.get(major, DOC_PATH[3])

    print(f"  Discovering topics from repo tree...", flush=True)
    resp = httpx.get(
        f"{GITHUB_API}/git/trees/v{version}?recursive=1",
        headers={"Accept": "application/vnd.github+json"},
        timeout=30,
    )
    resp.raise_for_status()
    tree = resp.json()["tree"]

    topics = []
    for entry in tree:
        path = entry["path"]
        # Match: <base>/<module>/pages/<section>/<file>.adoc
        # or:    <base>/<module>/pages/<file>.adoc  (top-level how-to pages)
        for module in MODULES:
            prefix = f"{base}/{module}/pages/"
            if not path.startswith(prefix) or not path.endswith(".adoc"):
                continue

            rel = path[len(prefix):]  # e.g. "web/servlet.adoc" or "security.adoc"
            filename = Path(rel).name

            if filename in SKIP_FILES:
                continue
            if any(part in SKIP_DIRS for part in Path(rel).parts):
                continue

            # Section is the directory, or "how-to-guides" for top-level how-to files
            parts = Path(rel).parts
            section = parts[0] if len(parts) > 1 else "how-to-guides"

            topics.append(DiscoveredTopic(
                module=module,
                section=section,
                adoc_path=rel,
                raw_url=f"{GITHUB_RAW}/v{version}/{path}",
            ))

    print(f"  Found {len(topics)} topics across {len(set(t.section for t in topics))} sections")
    return topics

# ---------------------------------------------------------------------------
# Metadata extraction from AsciiDoc content
# ---------------------------------------------------------------------------

_TITLE_RE = re.compile(r"^= (.+)$", re.MULTILINE)

# First non-empty paragraph after the title (skip attribute lines like :key: value)
_FIRST_PARA_RE = re.compile(
    r"^= .+\n"              # title line
    r"(?::[^\n]*\n)*"       # optional attribute lines
    r"\n+"                   # blank line(s)
    r"((?:[^\n=:].+\n?)+)", # first paragraph (non-empty, non-heading, non-attribute lines)
    re.MULTILINE,
)


def extract_title(adoc: str) -> str:
    """Extract the = Title from AsciiDoc content."""
    m = _TITLE_RE.search(adoc)
    return m.group(1).strip() if m else "Untitled"


def extract_keywords(adoc: str) -> str:
    """Extract key concepts from section headings (== level) as a compact description."""
    # Grab all == headings (level 2 in asciidoc)
    headings = re.findall(r"^== (.+)$", adoc, re.MULTILINE)
    if not headings:
        # Fallback: first sentence of first paragraph
        m = _FIRST_PARA_RE.search(adoc)
        if m:
            text = m.group(1).strip().split(".")[0]
            text = re.sub(r"[`{}\[\]<>]", "", text)
            text = " ".join(text.split())
            return text[:100]
        return ""

    # Clean headings, join as keywords, truncate cleanly at keyword boundary
    clean = []
    for h in headings:
        h = re.sub(r"[`{}\[\]<>]", "", h).strip()
        if h and h.lower() not in ("see also", "what to read next"):
            clean.append(h)
        if len(clean) >= 5:
            break

    # Build string, drop last keyword if it would be truncated
    result = ""
    for i, kw in enumerate(clean):
        candidate = f"{result}, {kw}" if result else kw
        if len(candidate) > 100:
            break
        result = candidate
    return result

# ---------------------------------------------------------------------------
# AsciiDoc → Markdown conversion via downdoc Node.js API
# ---------------------------------------------------------------------------

_POST_PATTERNS = [
    # Leftover {attribute} references — MUST run first so javadoc: patterns aren't blocked
    (re.compile(r"\{[\w\-]+\}"), ""),
    # Broad javadoc: macro — extract just the class name from any package
    (re.compile(r"javadoc:[/\w.$]*?(\w+)\[[^\]]*\]"), r"`\1`"),
    # Catch any remaining javadoc: that didn't have brackets
    (re.compile(r"javadoc:[/\w.$]*"), ""),
    # configprop: macro
    (re.compile(r"configprop:([\w.\-]+)\[[^\]]*\]"), r"`\1`"),
    # include-code:: macro
    (re.compile(r"include-code::\w+\[\]"), ""),
    # xref: cross-references converted to [text](path.adoc) — keep just text
    (re.compile(r"\[([^\]]+)\]\([^)]*\.adoc[^)]*\)"), r"\1"),
    # Bare xref macros that downdoc didn't convert
    (re.compile(r"xref:[^\[]*\[([^\]]*)\]"), r"\1"),
    # HTML admonition blocks → simple blockquote
    (re.compile(
        r'<dl><dt><strong>(.*?)</strong></dt><dd>\s*(.*?)\s*</dd></dl>',
        re.DOTALL,
    ), r"> **\1** \2"),
    # Any remaining HTML tags
    (re.compile(r"</?(?:dl|dt|dd|strong|em|q|a[^>]*)>"), ""),
    # Emoji admonition markers from downdoc (normalize to bold)
    (re.compile(r"\*\*[💡📌⚠️❗🔔]\s*(TIP|NOTE|WARNING|IMPORTANT|CAUTION)\*\*\\?"), r"> **\1:**"),
    # Collapse 3+ blank lines
    (re.compile(r"\n{3,}"), "\n\n"),
]

# Files larger than this get split into sub-files by ## heading
SPLIT_THRESHOLD_LINES = 300


def _post_process(md: str) -> str:
    for pat, repl in _POST_PATTERNS:
        md = pat.sub(repl, md)
    return md.strip()


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

    # Parse into sections by ## heading
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

    # Not enough sections to split meaningfully
    if len(sections) < 3:
        return None

    # Build index and sub-files
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
        # First line of content after heading as description
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


def _find_downdoc() -> str | None:
    """Find the downdoc module directory (for require())."""
    search_dirs = [
        Path(__file__).resolve().parent / "node_modules" / "downdoc",
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

# ---------------------------------------------------------------------------
# Async fetch
# ---------------------------------------------------------------------------

async def fetch_all(topics: list[DiscoveredTopic]) -> dict[str, str]:
    """Fetch all topic adoc files concurrently. Returns {adoc_path: content}."""
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    results: dict[str, str] = {}

    async def fetch_one(client: httpx.AsyncClient, topic: DiscoveredTopic) -> None:
        async with sem:
            try:
                resp = await client.get(topic.raw_url)
                if resp.status_code == 200:
                    results[topic.adoc_path] = resp.text
                else:
                    print(f"    {topic.adoc_path}... HTTP {resp.status_code}", flush=True)
            except httpx.HTTPError as e:
                print(f"    {topic.adoc_path}... error: {e}", flush=True)

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        await asyncio.gather(*(fetch_one(client, t) for t in topics))

    return results

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def _out_filename(topic: DiscoveredTopic) -> str:
    """Generate output path: section/stem.md"""
    stem = Path(topic.adoc_path).stem
    return f"{topic.section}/{stem}.md"


_SECTION_OVERRIDES = {"io": "IO", "jms": "JMS", "aot": "AOT", "ssl": "SSL"}

def _section_title(section: str) -> str:
    """Convert directory name to display title."""
    if section in _SECTION_OVERRIDES:
        return _SECTION_OVERRIDES[section]
    return section.replace("-", " ").title()


def build_skill(version: str, output_dir: Path, folder_name: str | None = None,
                 display_version: str | None = None) -> dict:
    display_version = display_version or version
    skill_dir = output_dir / (folder_name or version)
    refs_dir = skill_dir / "references"
    refs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Discover topics from repo tree
    topics = discover_topics(version)

    # 2. Fetch all adoc files concurrently
    print(f"  Fetching {len(topics)} files...", flush=True)
    adoc_contents = asyncio.run(fetch_all(topics))
    print(f"  Fetched {len(adoc_contents)}/{len(topics)} files")

    # 3. Extract metadata from adoc headers
    topic_meta: dict[str, tuple[str, str]] = {}  # adoc_path -> (title, description)
    for path, content in adoc_contents.items():
        topic_meta[path] = (extract_title(content), extract_keywords(content))

    # 4. Convert all to markdown in one Node process
    print("  Converting to markdown...", flush=True)
    md_contents = batch_convert_adoc(adoc_contents)

    # 5. Write reference files, grouped by section
    # Build a map: adoc_path -> DiscoveredTopic for lookup
    topic_by_path = {t.adoc_path: t for t in topics}

    # Group topics by (module, section) for the index
    sections: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)
    # Each entry: (out_path, title, description)

    fetched = 0
    split_count = 0
    for path, md in md_contents.items():
        if not md:
            continue
        topic = topic_by_path[path]
        out_path = _out_filename(topic)
        title, desc = topic_meta.get(path, ("Untitled", ""))

        # Ensure section subdirectory exists
        (refs_dir / topic.section).mkdir(parents=True, exist_ok=True)

        # Split large files into sub-files with an index
        split = split_large_file(md, title)
        if split:
            # Create a directory for this topic's sub-files
            topic_dir = refs_dir / topic.section / Path(topic.adoc_path).stem
            topic_dir.mkdir(parents=True, exist_ok=True)
            index_content = split.pop("_index")
            (refs_dir / out_path).write_text(index_content)
            for sub_name, sub_content in split.items():
                (topic_dir / sub_name).write_text(sub_content)
            split_count += 1
        else:
            (refs_dir / out_path).write_text(md)

        sections[(topic.module, topic.section)].append((out_path, title, desc))
        fetched += 1

    skipped = len(topics) - fetched
    print(f"  Written: {fetched} files ({split_count} split into sub-files), {skipped} skipped\n")

    # 6. Build topic index grouped by section
    # Merge reference + how-to under the same section where they overlap
    merged: dict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
    for (module, section), entries in sections.items():
        for out_path, title, desc in entries:
            prefix = "How-to: " if module == "how-to" else ""
            merged[section].append((out_path, f"{prefix}{title}", desc, module))

    topic_index_lines = []
    for section in sorted(merged.keys()):
        topic_index_lines.append(f"\n### {_section_title(section)}\n")
        for out_path, title, desc, _ in sorted(merged[section], key=lambda e: e[1]):
            line = f"- `references/{out_path}` — {title}"
            if desc:
                line += f" ({desc})"
            topic_index_lines.append(line)

    # 7. Write SKILL.md
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    skill_content = SKILL_MD.format(
        version=display_version,
        generated_at=generated_at,
        topic_index="\n".join(topic_index_lines),
    )
    (skill_dir / "SKILL.md").write_text(skill_content)

    return {
        "version": version,
        "generated_at": generated_at,
        "topics_fetched": fetched,
        "topics_skipped": skipped,
    }

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def cache_path(version: str) -> Path:
    return CACHE_DIR / f"v{version}"


def load_cache(version: str, dest: Path) -> bool:
    src = cache_path(version)
    if not (src / "SKILL.md").exists():
        return False
    meta_file = src / "meta.json"
    ts = json.loads(meta_file.read_text()).get("generated_at", "?") if meta_file.exists() else "?"
    print(f"  [cache] Hit for v{version} (generated {ts})")
    if dest.resolve() != src.resolve():
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
    return True


def save_cache(version: str, skill_dir: Path, meta: dict) -> None:
    dest = cache_path(version)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(skill_dir, dest)
    (dest / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"  [cache] Saved v{version}")

# ---------------------------------------------------------------------------
# SKILL.md template
# ---------------------------------------------------------------------------

SKILL_MD = """\
---
name: spring-boot-best-practices
description: Guides Spring Boot development with best practices, anti-patterns, and official reference docs. Use when working in a Spring Boot codebase or discussing Spring Boot concepts.
---

# Spring Boot {version} — Reference SKILL

> **Source:** Official Spring Boot {version} docs (auto-discovered)
> **Generated:** {generated_at}

---

## Core Principles

Before writing any code, ask: *does Spring Boot already do this?*

1. **Auto-configuration backs off.** Define your own `@Bean` and Boot's disappears.
2. **`@ConfigurationProperties` > `@Value`.** Typed, validated, IDE-friendly.
3. **Starters > manual deps.** `spring-boot-starter-*` manages compatible versions.
4. **`application.yml` is the control panel.** Most behaviors are property-toggleable.
5. **Actuator is free observability.** Health, metrics, tracing — all auto-configured.
6. **Test slices exist for a reason.** `@WebMvcTest`, `@DataJpaTest` — faster, focused.

---

## Anti-Pattern Quick Reference

| Avoid | Spring Boot way |
|---|---|
| `@Value` for property groups | `@ConfigurationProperties(prefix="...")` |
| `new RestTemplate()` | Inject `RestClient.Builder` or `WebClient.Builder` |
| Manual `ObjectMapper` bean | `Jackson2ObjectMapperBuilderCustomizer` |
| Manual `DataSource` config | `spring.datasource.*` properties |
| `@EnableWebMvc` (replaces Boot config) | `WebMvcConfigurer` bean to *extend* config |
| `@SpringBootTest` for everything | Slices: `@WebMvcTest`, `@DataJpaTest`, etc. |
| Hardcoded profile checks | `@Profile("prod")` + `spring.profiles.active` |
| Manual health endpoint | `HealthIndicator` bean + Actuator `/health` |

---

## Reference Files

Load on demand when the topic is relevant. Do **not** load all at once.
{topic_index}

---

## How to Use These References

1. Check the anti-pattern table above first — the answer may already be there.
2. Find the relevant topic in the index. Load only that file, not multiple.
3. Some large topics have their own sub-index — load the specific sub-section you need.
4. Before writing a custom `@Bean` or `@Configuration`, check if a `spring.*` property already controls the behavior.
5. Before writing a custom REST endpoint for health/metrics, check Actuator first.
"""

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def list_versions() -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    dirs = sorted(CACHE_DIR.glob("v*"))
    if not dirs:
        print("No cached versions.")
        return
    print("Cached versions:")
    for d in dirs:
        meta_f = d / "meta.json"
        if meta_f.exists():
            m = json.loads(meta_f.read_text())
            print(f"  {d.name}  ({m['topics_fetched']} topics, generated {m['generated_at']})")
        else:
            print(f"  {d.name}")


def clear_cache(version: str | None) -> None:
    if version:
        target = cache_path(version.lstrip("v"))
        if target.exists():
            shutil.rmtree(target)
            print(f"Cleared cache for v{version}")
        else:
            print(f"No cache for v{version}")
    elif CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        print("Cleared all cache.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Claude Code SKILL from Spring Boot docs")
    parser.add_argument("--version", "-v", help="Spring Boot version (e.g. 4.0.3)")
    parser.add_argument("--output", "-o", default=".", help="Output base directory (default: .)")
    parser.add_argument("--display-version", help="Version shown in SKILL.md (e.g. 3.4.x). Defaults to --version value")
    parser.add_argument("--no-cache", action="store_true", help="Re-fetch even if cached")
    parser.add_argument("--list-versions", action="store_true", help="List cached versions")
    parser.add_argument("--clear-cache", nargs="?", const="ALL", metavar="VERSION",
                        help="Clear cache for VERSION, or all if omitted")
    args = parser.parse_args()

    if args.list_versions:
        list_versions()
        return
    if args.clear_cache is not None:
        clear_cache(None if args.clear_cache == "ALL" else args.clear_cache)
        return
    if not args.version:
        parser.print_help()
        sys.exit(1)

    version = args.version.lstrip("v")
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        print(f"Error: '{version}' is not a valid version (expected X.Y.Z)")
        sys.exit(1)

    output_dir = Path(args.output)
    folder_name = "spring-boot-best-practices"
    skill_dir = output_dir / folder_name

    if not args.no_cache and load_cache(version, skill_dir):
        pass
    else:
        meta = build_skill(version, output_dir, folder_name, args.display_version)
        save_cache(version, skill_dir, meta)

    ref_count = sum(1 for _ in (skill_dir / "references").rglob("*.md"))
    skill_kb = (skill_dir / "SKILL.md").stat().st_size // 1024
    total_kb = sum(f.stat().st_size for f in skill_dir.rglob("*.md")) // 1024

    print(f"Done: {skill_dir}/")
    print(f"  SKILL.md       {skill_kb} KB (always loaded)")
    print(f"  references/    {ref_count} files, ~{total_kb - skill_kb} KB (on demand)")
    print(f"\nInstall:\n  cp -r {skill_dir} ~/.claude/skills/{folder_name}")


if __name__ == "__main__":
    main()
