# Spring Boot Skill Generator

Auto-generates [Claude Code skills](https://docs.anthropic.com/en/docs/claude-code/skills) from official Spring Boot documentation. Topics are auto-discovered from the repo — no hardcoded list.

## Quick Install

**One-liner** (requires `curl` and `unzip`):

```bash
curl -fsSL https://raw.githubusercontent.com/Tcivie/spring-boot-skill-gen/main/install.sh | bash -s -- 3.4
```

**Or manually** — download from [Releases](../../releases) and unzip:

```bash
unzip spring-boot-best-practices.zip -d ~/.claude/skills/
```

Claude Code picks it up automatically — no restart needed. It activates when you work with Spring Boot code.

## Versioning

Releases are tagged by **minor version** only (e.g. `v3.4`, `v4.0`), not by patch.

**Why no `3.4.13` or `3.5.13`?** Patch releases contain only bug fixes — no new features, APIs, or configuration properties are introduced. The best practices, reference docs, and anti-patterns are the same across all patches within a minor line. A single `3.4.x` skill covers `3.4.0` through `3.4.13` equally well.

When a new **minor** version is released (e.g. `4.1.0`), the CI pipeline automatically detects it and generates a new skill.

## What's Inside

Each skill follows [progressive disclosure](https://docs.anthropic.com/en/docs/claude-code/skills#add-supporting-files):

```
spring-boot-best-practices/
├── SKILL.md                           # ~16 KB — principles, anti-patterns, topic index
└── references/                        # ~860 KB — loaded on demand
    ├── actuator/
    │   ├── endpoints.md
    │   ├── observability.md
    │   └── metrics/                   # large topics split into sub-files
    │       ├── getting-started.md
    │       └── supported-monitoring-systems.md
    ├── data/
    │   ├── sql.md
    │   └── nosql/                     # auto-split: Redis, MongoDB, Cassandra...
    │       ├── redis.md
    │       └── mongodb.md
    ├── web/
    ├── testing/
    ├── messaging/
    └── ...
```

- **SKILL.md** (always loaded): core principles, anti-pattern table, topic index with keywords
- **references/** (on demand): Claude loads only the specific topic it needs
- **Large topics** auto-split by `##` headings into sub-files with their own index

## Generate Yourself

```bash
git clone https://github.com/Tcivie/spring-boot-skill-gen.git
cd spring-boot-skill-gen
pip install httpx
npm install

python generate_skill.py --version 4.0.5
# Output: spring-boot-best-practices/

cp -r spring-boot-best-practices ~/.claude/skills/
```

### Commands

```bash
python generate_skill.py --version 4.0.5                              # generate for a version
python generate_skill.py --version 4.0.5 --display-version 4.0.x      # custom display version
python generate_skill.py --version 4.0.5 --no-cache                   # force re-fetch
python generate_skill.py --list-versions                               # show cached versions
python generate_skill.py --clear-cache                                 # clear all cache
```

## How It Works

1. **Discover** — GitHub Trees API finds all `.adoc` files under `reference/pages/` and `how-to/pages/`
2. **Fetch** — async parallel download of all topics via `httpx`
3. **Convert** — single Node.js process converts all AsciiDoc to Markdown via `downdoc`
4. **Clean** — post-processing strips leftover macros (`javadoc:`, `configprop:`, `{attributes}`, HTML)
5. **Split** — files over 300 lines are split by `##` headings into sub-files with an index
6. **Package** — SKILL.md with frontmatter + topic index, references in subdirectories

## License

MIT
