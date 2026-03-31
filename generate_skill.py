#!/usr/bin/env python3
"""
Spring Ecosystem SKILL Generator — CLI entrypoint.

Usage:
  # Single project
  python generate_skill.py --project boot --version 4.0.5

  # Bundled (called by CI)
  python generate_skill.py --bundled --companions '{"boot":"4.0.5","security":"7.0.4",...}'
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from skillgen.config import load_projects, CACHE_DIR, SKILL_FOLDER
from skillgen.building import build_bundled_skill, build_single_skill


def _cache_path(project_id: str, version: str) -> Path:
    return CACHE_DIR / project_id / f"v{version}"


def _load_cache(project_id: str, version: str, dest: Path) -> bool:
    src = _cache_path(project_id, version)
    if not src.exists():
        return False
    meta_file = src / "meta.json"
    ts = json.loads(meta_file.read_text()).get("generated_at", "?") if meta_file.exists() else "?"
    print(f"  [cache] Hit for {project_id}/v{version} (generated {ts})")
    if dest.resolve() != src.resolve():
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
    return True


def _save_cache(project_id: str, version: str, skill_dir: Path, meta: dict) -> None:
    dest = _cache_path(project_id, version)
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill_dir, dest)
    (dest / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"  [cache] Saved {project_id}/v{version}")


def cmd_list_versions() -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    for project_dir in sorted(CACHE_DIR.iterdir()):
        if not project_dir.is_dir():
            continue
        for version_dir in sorted(project_dir.glob("v*")):
            meta_f = version_dir / "meta.json"
            if meta_f.exists():
                m = json.loads(meta_f.read_text())
                print(f"  {project_dir.name}/{version_dir.name}  "
                      f"({m.get('topics_fetched', '?')} topics, generated {m.get('generated_at', '?')})")
            else:
                print(f"  {project_dir.name}/{version_dir.name}")


def cmd_clear_cache(version: str | None) -> None:
    if version:
        for project_dir in CACHE_DIR.iterdir():
            target = project_dir / f"v{version.lstrip('v')}"
            if target.exists():
                shutil.rmtree(target)
                print(f"Cleared cache for {project_dir.name}/v{version}")
    elif CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        print("Cleared all cache.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Claude Code SKILLs from Spring docs")
    parser.add_argument("--project", "-p", default="boot", help="Project ID (default: boot)")
    parser.add_argument("--version", "-v", help="Project version (e.g. 4.0.5)")
    parser.add_argument("--display-version", help="Version shown in SKILL.md (e.g. 3.4.x)")
    parser.add_argument("--output", "-o", default=".", help="Output base directory")
    parser.add_argument("--no-cache", action="store_true", help="Re-fetch even if cached")
    parser.add_argument("--bundled", action="store_true", help="Generate bundled skill (used by CI)")
    parser.add_argument("--companions", help="JSON dict of project_id:version pairs (with --bundled)")
    parser.add_argument("--list-versions", action="store_true")
    parser.add_argument("--clear-cache", nargs="?", const="ALL", metavar="VERSION")
    args = parser.parse_args()

    if args.list_versions:
        cmd_list_versions()
        return
    if args.clear_cache is not None:
        cmd_clear_cache(None if args.clear_cache == "ALL" else args.clear_cache)
        return

    projects = load_projects()
    output_dir = Path(args.output)

    if args.bundled:
        if not args.companions:
            print("Error: --bundled requires --companions JSON")
            sys.exit(1)
        companions = json.loads(args.companions)
        display_version = args.display_version or "unknown"
        build_bundled_skill(display_version, companions, output_dir, projects)
    else:
        if not args.version:
            parser.print_help()
            sys.exit(1)

        version = args.version.lstrip("v")
        if not re.match(r"^\d+\.\d+\.\d+$", version):
            print(f"Error: '{version}' is not a valid version (expected X.Y.Z)")
            sys.exit(1)

        config = projects.get(args.project)
        if not config:
            print(f"Error: unknown project '{args.project}'. Available: {', '.join(projects.keys())}")
            sys.exit(1)

        skill_dir = output_dir / SKILL_FOLDER
        if not args.no_cache and _load_cache(args.project, version, skill_dir):
            pass
        else:
            meta = build_single_skill(args.project, version, config, output_dir, args.display_version)
            _save_cache(args.project, version, skill_dir, meta)

    skill_dir = output_dir / SKILL_FOLDER
    ref_count = sum(1 for _ in (skill_dir / "references").rglob("*.md"))
    skill_kb = (skill_dir / "SKILL.md").stat().st_size // 1024
    total_kb = sum(f.stat().st_size for f in skill_dir.rglob("*.md")) // 1024

    print(f"\nDone: {skill_dir}/")
    print(f"  SKILL.md       {skill_kb} KB (always loaded)")
    print(f"  references/    {ref_count} files, ~{total_kb - skill_kb} KB (on demand)")


if __name__ == "__main__":
    main()
