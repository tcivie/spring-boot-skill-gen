# Spring Boot Skill Generator

Auto-generates [Claude Code skills](https://docs.anthropic.com/en/docs/claude-code/skills) from official Spring Boot documentation. Topics are auto-discovered from the repo — no hardcoded list.

## Quick Install

**One-liner** (requires `curl` and `unzip`):

```bash
curl -fsSL https://raw.githubusercontent.com/Tcivie/spring-boot-skill-gen/main/install.sh | bash -s -- 4.0.4
```

**Or manually** — download from [Releases](../../releases) and unzip:

```bash
unzip spring-boot-4-0-4.zip -d ~/.claude/skills/
```

Claude Code picks it up automatically — no restart needed. It activates when you work with Spring Boot code.

## What's Inside

Each skill follows [progressive disclosure](https://docs.anthropic.com/en/docs/claude-code/skills#add-supporting-files):

```
spring-boot-4-0-4/
├── SKILL.md                           # 16 KB — principles, anti-patterns, topic index
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

python generate_skill.py --version 4.0.4
# Output: spring-boot-4-0-4/

cp -r spring-boot-4-0-4 ~/.claude/skills/
```

### Commands

```bash
python generate_skill.py --version 4.0.4              # generate for a version
python generate_skill.py --version 4.0.4 --no-cache   # force re-fetch
python generate_skill.py --list-versions               # show cached versions
python generate_skill.py --clear-cache                 # clear all cache
```

## Versioning

Skills are versioned as `<spring-boot-version>-r<revision>`:

- **New Spring Boot patch** (4.0.4 → 4.0.4): new version starts at `r1`
- **Script change** (better cleanup, new sections): all versions bump revision (`r1` → `r2`)

The CI pipeline checks daily for new Spring Boot releases and regenerates automatically.

## How It Works

1. **Discover** — GitHub Trees API finds all `.adoc` files under `reference/pages/` and `how-to/pages/`
2. **Fetch** — async parallel download of all topics via `httpx`
3. **Convert** — single Node.js process converts all AsciiDoc to Markdown via `downdoc`
4. **Clean** — post-processing strips leftover macros (`javadoc:`, `configprop:`, `{attributes}`, HTML)
5. **Split** — files over 300 lines are split by `##` headings into sub-files with an index
6. **Package** — SKILL.md with frontmatter + topic index, references in subdirectories

## License

MIT
