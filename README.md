<div align="center">

# Spring Skill for Claude Code

**Stop Claude from hallucinating Spring code.**

Claude's training data is months stale. Without help it confidently writes deprecated code, invents APIs that don't exist, and rebuilds things Boot already does for you. This skill plugs the **real, version-pinned Spring docs** into Claude — only the page it needs, only when it needs it.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Latest release](https://img.shields.io/github/v/release/Tcivie/spring-boot-skill-gen)](../../releases/latest)
[![Auto-updated daily](https://img.shields.io/badge/auto--updated-daily-brightgreen)](.github/workflows/generate.yml)

[Install](#install) · [The problem](#the-problem-claude-hallucinates-spring) · [Versions](#versions) · [Spring docs ↗](https://spring.io/projects/spring-boot)

</div>

---

## The problem: Claude hallucinates Spring

Real things Claude says when you don't give it the docs:

> 🤖 *"Use `RestTemplate` for the HTTP call…"*
> Reality: RestTemplate has been in maintenance mode since Boot 3.0. The right answer is `RestClient` (sync) or `WebClient` (reactive).

> 🤖 *"Spring AI doesn't support tool calling yet, you'll need to roll your own."*
> Reality: Spring AI 1.0 ships `@Tool` + `ToolCallback`. Built in.

> 🤖 *"Add a `@Bean` for `ObjectMapper` and configure it manually…"*
> Reality: Boot autoconfigures it. You add a `Jackson2ObjectMapperBuilderCustomizer` instead — five lines.

> 🤖 *"Wire `@Value` for each property and validate them in `@PostConstruct`…"*
> Reality: `@ConfigurationProperties` does this in one annotation, with JSR-303 validation included.

After install, Claude reads the actual Spring docs for **your exact Boot version** and stops guessing.

---

## Install

1. Go to [Releases](../../releases) and download the zip for your Boot version (`v3.3`, `v3.4`, `v3.5`, `v4.0`).
2. Unzip into `~/.claude/skills/`.
3. Restart Claude Code.

That's it. The skill auto-loads whenever you open a Spring file (`application.yml`, `pom.xml`, anything with `@SpringBootApplication`, etc.).

**Or one line in your terminal:**

```bash
curl -fsSL https://raw.githubusercontent.com/Tcivie/spring-boot-skill-gen/main/install.sh | bash -s -- 4.0
```

(Replace `4.0` with whatever Boot major.minor your project uses.)

---

## What you get

The full Spring ecosystem, version-pinned and bundled:

| | Inside the pack |
|---|---|
| **Core** | Spring Boot |
| **Security** | Spring Security · Authorization Server |
| **AI** | Spring AI |
| **Cloud** | Gateway · Config · Eureka · OpenFeign · Circuit Breaker · Stream · Function · Bus · Consul · Kubernetes · Vault · Commons · Contract · Task |
| **Architecture** | Spring Modulith |

Claude pulls a single file at a time — `references/security/jwt.md` for an auth question, `references/boot/messaging/kafka.md` for a Kafka question. The rest of the pack costs you zero tokens until needed.

---

## Versions

Releases pin every project to versions that ship together — no compatibility roulette.

| Boot | Security | Cloud | AI | Modulith | Tag |
|------|----------|-------|----|----------|-----|
| 3.3.x | 6.3.x | 2023.0.x | 1.0.x | 1.2.x | [`v3.3`](../../releases/tag/v3.3) |
| 3.4.x | 6.4.x | 2024.0.x | 1.0.x | 1.3.x | [`v3.4`](../../releases/tag/v3.4) |
| 3.5.x | 6.5.x | 2025.0.x | 1.1.x | 1.4.x | [`v3.5`](../../releases/tag/v3.5) |
| 4.0.x | 7.0.x | 2025.1.x | — | 2.0.x | [`v4.0`](../../releases/tag/v4.0) |

A daily cron rebuilds every release if upstream Spring docs change. You stay current automatically.

---

## What's a Claude Skill, anyway?

A skill is a folder of Markdown the Claude Code CLI can browse on demand. Think of it as a **plug-in brain**: Claude reads only the page that matters for your current question, so the rest doesn't burn your context window.

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

If you want a custom Boot patch or to tweak the output:

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
- **Sister project** — [`nomad-skill-gen`](https://github.com/Tcivie/nomad-skill-gen)

---

## Support

If this saves you tokens or headaches, [buy me a coffee on Ko-fi](https://ko-fi.com/tcivie). Stars on GitHub also help.

## License

[MIT](LICENSE) — use it however you want.
