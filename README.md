# Spring Ecosystem Skill Generator

Auto-generates [Claude Code skills](https://docs.anthropic.com/en/docs/claude-code/skills) from official Spring documentation. Covers the entire Spring ecosystem — not just Boot.

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/Tcivie/spring-boot-skill-gen/main/install.sh | bash -s -- 3.4
```

Or download from [Releases](../../releases) and unzip into `~/.claude/skills/`.

## What's Included

Each release bundles docs from **20 Spring projects**, all pinned to compatible versions for your Spring Boot line:

| Category | Projects |
|----------|----------|
| **Core** | Spring Boot |
| **Security** | Spring Security, Authorization Server |
| **AI** | Spring AI |
| **Cloud** | Gateway, Config, Netflix (Eureka), OpenFeign, Circuit Breaker, Stream, Function, Bus, Consul, Kubernetes, Vault, Commons, Contract, Task |
| **Architecture** | Spring Modulith |

## Versioning

Releases are tagged by **Spring Boot minor** (e.g. `v3.4`, `v4.0`). Each release includes all companion projects at their Boot-compatible versions:

| Boot | Security | Cloud Train | AI | Modulith |
|------|----------|------------|-----|----------|
| 3.2.x | 6.2.x | 2023.0.x | — | 1.1.x |
| 3.3.x | 6.3.x | 2023.0.x | 1.0.x | 1.2.x |
| 3.4.x | 6.4.x | 2024.0.x | 1.0.x | 1.3.x |
| 3.5.x | 6.5.x | 2025.0.x | 1.1.x | 1.4.x |
| 4.0.x | 7.0.x | 2025.1.x | — | 2.0.x |

## Skill Structure

```
spring-best-practices/
├── SKILL.md                    # Always loaded — principles, anti-patterns, topic index
└── references/                 # Loaded on demand by topic
    ├── boot/                   # Spring Boot
    │   ├── web/servlet.md
    │   ├── data/sql.md
    │   └── ...
    ├── security/               # Spring Security
    ├── ai/                     # Spring AI
    ├── cloud-gateway/          # Spring Cloud Gateway
    ├── cloud-config/           # Spring Cloud Config
    ├── modulith/               # Spring Modulith
    └── ...
```

## Generate Yourself

```bash
git clone https://github.com/Tcivie/spring-boot-skill-gen.git
cd spring-boot-skill-gen
pip install httpx
npm install

# Single project
python generate_skill.py --project boot --version 4.0.5

# Bundled (all projects)
python generate_skill.py --bundled \
  --companions '{"boot":"4.0.5","security":"7.0.4","ai":"1.1.4"}' \
  --display-version 4.0.x
```

## How It Works

1. **Discover** — GitHub Trees API finds `.adoc` files in each project's Antora docs
2. **Fetch** — async parallel download via `httpx`
3. **Convert** — single Node.js process converts AsciiDoc → Markdown via `downdoc`
4. **Clean** — post-processing strips macros (`javadoc:`, `configprop:`, `{attributes}`)
5. **Split** — files over 300 lines split by `##` headings into sub-files
6. **Bundle** — all projects assembled under one `references/` tree with SKILL.md index

## Project Structure

```
├── generate_skill.py           # CLI entrypoint
├── skillgen/                   # Core package
│   ├── config/                 # Project definitions, constants
│   │   ├── constants.py
│   │   └── projects.py
│   ├── discovery/              # GitHub topic discovery + fetching
│   │   ├── topics.py
│   │   ├── fetch.py
│   │   └── metadata.py
│   ├── conversion/             # AsciiDoc → Markdown
│   │   ├── downdoc.py
│   │   └── splitter.py
│   └── building/               # Skill assembly
│       ├── generator.py
│       └── display.py
├── ci/
│   └── generate_all.py         # CI orchestrator
├── projects.json               # Project registry (repos, doc paths)
├── compatibility.json          # Boot ↔ companion version map
├── templates/
│   └── skill.md                # SKILL.md template
└── versions.json               # Tracked versions (updated by CI)
```

## License

MIT
