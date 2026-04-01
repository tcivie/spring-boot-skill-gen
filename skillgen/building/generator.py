"""Skill generation: assembles reference files with progressive CONTENTS.md indexes."""

from __future__ import annotations

import asyncio
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from skillgen.config import ProjectConfig, SKILL_FOLDER, TEMPLATES_DIR
from skillgen.conversion import batch_convert_adoc, split_large_file
from skillgen.discovery import discover_topics, fetch_all, extract_title, extract_keywords
from skillgen.building.display import PROJECT_DISPLAY_NAMES, section_title


def _out_filename(topic) -> str:
    """Generate output path: section/stem.md"""
    stem = Path(topic.adoc_path).stem
    return f"{topic.section}/{stem}.md"


def _write_section_contents(
    section_dir: Path,
    section_name: str,
    entries: list[tuple[str, str, str]],
    display_name: str,
) -> None:
    """Write a CONTENTS.md for a section directory listing its topic files."""
    lines = [f"# {display_name} — {section_title(section_name)}\n"]
    lines.append("Load the specific topic you need:\n")

    for filename, title, desc in sorted(entries, key=lambda e: e[1]):
        line = f"- [{title}]({filename})"
        if desc:
            line += f" — {desc}"
        lines.append(line)

    (section_dir / "CONTENTS.md").write_text("\n".join(lines) + "\n")


def _write_project_contents(
    project_dir: Path,
    display_name: str,
    section_entries: dict[str, list[tuple[str, str, str]]],
) -> None:
    """Write a CONTENTS.md for a project directory listing its sections.

    If the project has only one section called "general", skip the section
    level and list topics directly — avoids a useless indirection layer.
    """
    sections = list(section_entries.keys())

    # Single "general" section → list topics directly
    if len(sections) == 1 and sections[0] == "general":
        entries = section_entries["general"]
        lines = [f"# {display_name}\n"]
        lines.append("Load the specific topic you need:\n")
        for filename, title, desc in sorted(entries, key=lambda e: e[1]):
            line = f"- [{title}](general/{filename})"
            if desc:
                line += f" — {desc}"
            lines.append(line)
        (project_dir / "CONTENTS.md").write_text("\n".join(lines) + "\n")
        return

    lines = [f"# {display_name}\n"]
    lines.append("Browse by section:\n")

    for section_name in sorted(section_entries.keys()):
        entries = section_entries[section_name]
        topic_count = len(entries)
        all_topics = ", ".join(t for _, t, _ in sorted(entries, key=lambda e: e[1]))

        lines.append(f"- [{section_title(section_name)}]({section_name}/CONTENTS.md) ({topic_count} topics) — {all_topics}")

    (project_dir / "CONTENTS.md").write_text("\n".join(lines) + "\n")


def generate_project(
    project_id: str,
    version: str,
    config: ProjectConfig,
    refs_dir: Path,
) -> tuple[int, int, str]:
    """Generate reference files for one project.

    Returns (fetched_count, skipped_count, project_summary_line).
    """
    project_refs = refs_dir / project_id
    project_refs.mkdir(parents=True, exist_ok=True)

    print(f"\n[{project_id}] Generating for version {version}...")

    # 1. Discover topics
    topics = discover_topics(version, config)
    if not topics:
        print(f"  No topics found for {project_id} {version}")
        return 0, 0, ""

    # 2. Fetch
    print(f"  Fetching {len(topics)} files...", flush=True)
    adoc_contents = asyncio.run(fetch_all(topics))
    print(f"  Fetched {len(adoc_contents)}/{len(topics)} files")

    # 3. Extract metadata (pass filename for fallback title)
    topic_meta: dict[str, tuple[str, str]] = {}
    for path, content in adoc_contents.items():
        filename = Path(path).name
        topic_meta[path] = (extract_title(content, filename), extract_keywords(content))

    # 4. Convert
    print("  Converting to markdown...", flush=True)
    md_contents = batch_convert_adoc(adoc_contents)

    # 5. Write reference files
    topic_by_path = {t.adoc_path: t for t in topics}
    # section -> [(filename_relative_to_section, title, desc)]
    section_entries: dict[str, list[tuple[str, str, str]]] = defaultdict(list)

    fetched = 0
    split_count = 0
    for path, md in md_contents.items():
        if not md:
            continue
        topic = topic_by_path[path]
        out_path = _out_filename(topic)
        title, desc = topic_meta.get(path, ("Untitled", ""))

        # Prefix how-to titles
        if topic.module == "how-to":
            title = f"How-to: {title}"

        (project_refs / topic.section).mkdir(parents=True, exist_ok=True)

        stem = Path(topic.adoc_path).stem
        split = split_large_file(md, title)
        if split:
            topic_dir = project_refs / topic.section / stem
            topic_dir.mkdir(parents=True, exist_ok=True)
            index_content = split.pop("_index")
            (project_refs / out_path).write_text(index_content)
            for sub_name, sub_content in split.items():
                (topic_dir / sub_name).write_text(sub_content)
            split_count += 1
        else:
            (project_refs / out_path).write_text(md)

        # Track for CONTENTS.md — filename is relative to section dir
        section_entries[topic.section].append((f"{stem}.md", title, desc))
        fetched += 1

    skipped = len(topics) - fetched
    print(f"  Written: {fetched} files ({split_count} split), {skipped} skipped")

    # 6. Write CONTENTS.md at each level
    display_name = PROJECT_DISPLAY_NAMES.get(project_id, project_id.replace("-", " ").title())

    # Section-level CONTENTS.md
    for section_name, entries in section_entries.items():
        section_dir = project_refs / section_name
        _write_section_contents(section_dir, section_name, entries, display_name)

    # Project-level CONTENTS.md
    _write_project_contents(project_refs, display_name, section_entries)

    # Build a one-line summary for the top-level SKILL.md
    section_names = ", ".join(section_title(s) for s in sorted(section_entries.keys()))
    summary = f"- [{display_name}](references/{project_id}/CONTENTS.md) ({fetched} topics) — {section_names}"

    return fetched, skipped, summary


def build_bundled_skill(
    display_version: str,
    companions: dict[str, str],
    output_dir: Path,
    projects: dict[str, ProjectConfig],
) -> dict:
    """Generate a single bundled skill with all companion projects."""
    skill_dir = output_dir / SKILL_FOLDER
    refs_dir = skill_dir / "references"
    if skill_dir.exists():
        shutil.rmtree(skill_dir)
    refs_dir.mkdir(parents=True, exist_ok=True)

    project_summaries: list[str] = []
    total_fetched = 0
    total_skipped = 0
    project_count = 0

    for project_id, version in companions.items():
        config = projects.get(project_id)
        if not config:
            print(f"  Warning: unknown project '{project_id}', skipping")
            continue

        fetched, skipped, summary = generate_project(
            project_id, version, config, refs_dir
        )
        total_fetched += fetched
        total_skipped += skipped
        if fetched > 0:
            project_summaries.append(summary)
            project_count += 1

    # Write SKILL.md from template
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    template = (TEMPLATES_DIR / "skill.md").read_text()
    skill_content = template.format(
        version=display_version,
        generated_at=generated_at,
        project_index="\n".join(project_summaries),
        project_count=project_count,
    )
    (skill_dir / "SKILL.md").write_text(skill_content)

    print(f"\nBundled skill: {total_fetched} files from {project_count} projects")
    return {
        "version": display_version,
        "generated_at": generated_at,
        "topics_fetched": total_fetched,
        "topics_skipped": total_skipped,
        "project_count": project_count,
    }


def build_single_skill(
    project_id: str,
    version: str,
    config: ProjectConfig,
    output_dir: Path,
    display_version: str | None = None,
) -> dict:
    """Generate a skill for a single project (standalone mode)."""
    display_version = display_version or version
    skill_dir = output_dir / SKILL_FOLDER
    refs_dir = skill_dir / "references"
    if skill_dir.exists():
        shutil.rmtree(skill_dir)
    refs_dir.mkdir(parents=True, exist_ok=True)

    fetched, skipped, summary = generate_project(
        project_id, version, config, refs_dir
    )

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    template = (TEMPLATES_DIR / "skill.md").read_text()
    skill_content = template.format(
        version=display_version,
        generated_at=generated_at,
        project_index=summary,
        project_count=1,
    )
    (skill_dir / "SKILL.md").write_text(skill_content)

    return {
        "version": version,
        "generated_at": generated_at,
        "topics_fetched": fetched,
        "topics_skipped": skipped,
    }
