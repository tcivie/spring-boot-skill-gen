<div align="center">

# Spring Skill for Claude Code

**Make Claude an instant Spring expert.**

One install. Claude reads the official Spring docs only when it needs to — no token bloat, no stale knowledge.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Latest release](https://img.shields.io/github/v/release/Tcivie/spring-boot-skill-gen)](../../releases/latest)
[![Auto-updated daily](https://img.shields.io/badge/auto--updated-daily-brightgreen)](.github/workflows/generate.yml)

[Install](#install) · [What you get](#what-you-get) · [Versions](#versions) · [Spring docs ↗](https://spring.io/projects/spring-boot)

</div>

---

## Why?

You're vibing on a Spring app with Claude. You ask:

> "Why won't my `@ConfigurationProperties` bind?"
> "How do I add JWT auth?"
> "What's the right way to use `RestClient` here?"

Without this skill, Claude guesses from memory — which may be a year stale.
With this skill, Claude **reads the actual Spring docs** for your exact Boot version. Right answer, every time.

---

## Install

**One command:**

```bash
curl -fsSL https://raw.githubusercontent.com/Tcivie/spring-boot-skill-gen/main/install.sh | bash -s -- 4.0
```

Pick the version that matches your project (`3.3`, `3.4`, `3.5`, or `4.0`). Done — restart Claude Code and the skill auto-loads when you work on Spring files.

> **Don't trust curl-pipe-bash?** Download the zip from [Releases](../../releases) and unzip into `~/.claude/skills/`.

---

## What you get

A bundled reference pack covering the **whole Spring ecosystem** at versions that work together:

| | What's inside |
|---|---|
| **Core** | Spring Boot |
| **Security** | Spring Security · Authorization Server |
| **AI** | Spring AI |
| **Cloud** | Gateway · Config · Eureka · OpenFeign · Circuit Breaker · Stream · Function · Bus · Consul · Kubernetes · Vault · Commons · Contract · Task |
| **Architecture** | Spring Modulith |

Claude loads only the file it needs (e.g. `references/security/jwt.md`) instead of swallowing the whole spec. Fast, focused, cheap.

---

## Versions

Releases pin every project to versions that ship together — no compatibility roulette.

| Boot | Security | Cloud | AI | Modulith | Tag |
|------|----------|-------|----|----------|-----|
| 3.3.x | 6.3.x | 2023.0.x | 1.0.x | 1.2.x | [`v3.3`](../../releases/tag/v3.3) |
| 3.4.x | 6.4.x | 2024.0.x | 1.0.x | 1.3.x | [`v3.4`](../../releases/tag/v3.4) |
| 3.5.x | 6.5.x | 2025.0.x | 1.1.x | 1.4.x | [`v3.5`](../../releases/tag/v3.5) |
| 4.0.x | 7.0.x | 2025.1.x | — | 2.0.x | [`v4.0`](../../releases/tag/v4.0) |

Daily cron rebuilds every release if upstream Spring docs change. You stay current automatically.

---

## What's a Claude Skill?

A skill is a folder of Markdown the Anthropic CLI can browse on demand. Think of it as a **plug-in brain**: Claude reads only the section relevant to the question, so the rest doesn't waste your context window.

Read more: [Anthropic — Skills](https://docs.anthropic.com/en/docs/claude-code/skills)

The pack you install looks like this:

```
spring-best-practices/
├── SKILL.md                  always loaded (principles + index)
└── references/               loaded only when relevant
    ├── boot/web/servlet.md
    ├── security/jwt.md
    ├── ai/chat-client.md
    └── ...
```

---

## Build it yourself

If you want to tweak the output or pin a custom Boot patch version:

```bash
git clone https://github.com/Tcivie/spring-boot-skill-gen.git
cd spring-boot-skill-gen
pip install httpx && npm install

# One project
python generate_skill.py --project boot --version 4.0.5

# Bundled (the same thing CI ships)
python generate_skill.py --bundled \
  --companions '{"boot":"4.0.5","security":"7.0.4","ai":"1.1.4"}' \
  --display-version 4.0.x
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full pipeline.

---

## How it works (under the hood)

1. **Discover** — GitHub Trees API finds `.adoc` files in each Spring project's Antora docs
2. **Fetch** — async parallel download (`httpx`)
3. **Convert** — AsciiDoc → Markdown via `downdoc` (single Node process)
4. **Clean** — strip Antora macros (`javadoc:`, `configprop:`, attributes)
5. **Split** — files over 300 lines broken on `##` headings
6. **Bundle** — assemble under one `references/` tree with `CONTENTS.md` indexes

---

## Links

- **Spring** — [spring.io](https://spring.io) · [Boot reference](https://docs.spring.io/spring-boot/) · [Security](https://spring.io/projects/spring-security) · [Cloud](https://spring.io/projects/spring-cloud) · [AI](https://spring.io/projects/spring-ai)
- **Claude Code** — [Skills](https://docs.anthropic.com/en/docs/claude-code/skills) · [Authoring guide](https://docs.anthropic.com/en/docs/claude-code/skills-authoring)
- **Sister projects** — [`nomad-skill-gen`](https://github.com/Tcivie/nomad-skill-gen)

---

## Support

If this saves you tokens or headaches, [buy me a coffee on Ko-fi](https://ko-fi.com/tcivie). Stars on GitHub also help.

## License

[MIT](LICENSE) — use it however you want.
