"""Skill generation: assembles reference files and SKILL.md."""

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


def generate_project(
    project_id: str,
    version: str,
    config: ProjectConfig,
    refs_dir: Path,
) -> tuple[int, int, list[str]]:
    """Generate reference files for one project.

    Returns (fetched_count, skipped_count, topic_index_lines).
    """
    project_refs = refs_dir / project_id
    project_refs.mkdir(parents=True, exist_ok=True)

    print(f"\n[{project_id}] Generating for version {version}...")

    # 1. Discover topics
    topics = discover_topics(version, config)
    if not topics:
        print(f"  No topics found for {project_id} {version}")
        return 0, 0, []

    # 2. Fetch
    print(f"  Fetching {len(topics)} files...", flush=True)
    adoc_contents = asyncio.run(fetch_all(topics))
    print(f"  Fetched {len(adoc_contents)}/{len(topics)} files")

    # 3. Extract metadata
    topic_meta: dict[str, tuple[str, str]] = {}
    for path, content in adoc_contents.items():
        topic_meta[path] = (extract_title(content), extract_keywords(content))

    # 4. Convert
    print("  Converting to markdown...", flush=True)
    md_contents = batch_convert_adoc(adoc_contents)

    # 5. Write reference files
    topic_by_path = {t.adoc_path: t for t in topics}
    sections: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)

    fetched = 0
    split_count = 0
    for path, md in md_contents.items():
        if not md:
            continue
        topic = topic_by_path[path]
        out_path = _out_filename(topic)
        title, desc = topic_meta.get(path, ("Untitled", ""))

        (project_refs / topic.section).mkdir(parents=True, exist_ok=True)

        split = split_large_file(md, title)
        if split:
            topic_dir = project_refs / topic.section / Path(topic.adoc_path).stem
            topic_dir.mkdir(parents=True, exist_ok=True)
            index_content = split.pop("_index")
            (project_refs / out_path).write_text(index_content)
            for sub_name, sub_content in split.items():
                (topic_dir / sub_name).write_text(sub_content)
            split_count += 1
        else:
            (project_refs / out_path).write_text(md)

        sections[(topic.module, topic.section)].append((out_path, title, desc))
        fetched += 1

    skipped = len(topics) - fetched
    print(f"  Written: {fetched} files ({split_count} split), {skipped} skipped")

    # 6. Build topic index lines for this project
    merged: dict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
    for (module, section), entries in sections.items():
        for out_path, title, desc in entries:
            prefix = "How-to: " if module == "how-to" else ""
            merged[section].append((out_path, f"{prefix}{title}", desc, module))

    index_lines: list[str] = []
    display_name = PROJECT_DISPLAY_NAMES.get(project_id, project_id.replace("-", " ").title())
    index_lines.append(f"\n### {display_name}\n")
    for section in sorted(merged.keys()):
        if len(merged) > 1:
            index_lines.append(f"\n#### {section_title(section)}\n")
        for out_path, title, desc, _ in sorted(merged[section], key=lambda e: e[1]):
            line = f"- `references/{project_id}/{out_path}` — {title}"
            if desc:
                line += f" ({desc})"
            index_lines.append(line)

    return fetched, skipped, index_lines


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

    all_index_lines: list[str] = []
    total_fetched = 0
    total_skipped = 0
    project_count = 0

    for project_id, version in companions.items():
        config = projects.get(project_id)
        if not config:
            print(f"  Warning: unknown project '{project_id}', skipping")
            continue

        fetched, skipped, index_lines = generate_project(
            project_id, version, config, refs_dir
        )
        total_fetched += fetched
        total_skipped += skipped
        if fetched > 0:
            all_index_lines.extend(index_lines)
            project_count += 1

    # Write SKILL.md from template
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    template = (TEMPLATES_DIR / "skill.md").read_text()
    skill_content = template.format(
        version=display_version,
        generated_at=generated_at,
        topic_index="\n".join(all_index_lines),
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

    fetched, skipped, index_lines = generate_project(
        project_id, version, config, refs_dir
    )

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    template = (TEMPLATES_DIR / "skill.md").read_text()
    skill_content = template.format(
        version=display_version,
        generated_at=generated_at,
        topic_index="\n".join(index_lines),
        project_count=1,
    )
    (skill_dir / "SKILL.md").write_text(skill_content)

    return {
        "version": version,
        "generated_at": generated_at,
        "topics_fetched": fetched,
        "topics_skipped": skipped,
    }
