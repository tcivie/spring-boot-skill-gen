---
name: spring-best-practices
description: Guides Spring development with best practices, anti-patterns, and official reference docs for Spring Boot, Security, AI, Cloud, Modulith, and more. Use when working in a Spring-based codebase.
---

# Spring {version} — Reference SKILL

> **Source:** Official Spring {version} docs (auto-discovered from {project_count} projects)
> **Generated:** {generated_at}

---

## Core Principles

Before writing any code, ask: *does Spring already do this?*

1. **Auto-configuration backs off.** Define your own `@Bean` and Boot's disappears.
2. **`@ConfigurationProperties` > `@Value`.** Typed, validated, IDE-friendly.
3. **Starters > manual deps.** `spring-boot-starter-*` manages compatible versions.
4. **`application.yml` is the control panel.** Most behaviors are property-toggleable.
5. **Actuator is free observability.** Health, metrics, tracing — all auto-configured.
6. **Test slices exist for a reason.** `@WebMvcTest`, `@DataJpaTest` — faster, focused.

---

## Anti-Pattern Quick Reference

| Avoid | Spring way |
|---|---|
| `@Value` for property groups | `@ConfigurationProperties(prefix="...")` |
| `new RestTemplate()` | Inject `RestClient.Builder` or `WebClient.Builder` |
| Manual `ObjectMapper` bean | `Jackson2ObjectMapperBuilderCustomizer` |
| Manual `DataSource` config | `spring.datasource.*` properties |
| `@EnableWebMvc` (replaces Boot config) | `WebMvcConfigurer` bean to *extend* config |
| `@SpringBootTest` for everything | Slices: `@WebMvcTest`, `@DataJpaTest`, etc. |
| Hardcoded profile checks | `@Profile("prod")` + `spring.profiles.active` |
| Manual health endpoint | `HealthIndicator` bean + Actuator `/health` |
| Manual security filter chains | Use Spring Security's `SecurityFilterChain` bean |
| Blocking calls in WebFlux | Use reactive operators or `@Async` |

---

## Reference Files

Load on demand when the topic is relevant. Do **not** load all at once.
{topic_index}

---

## How to Use These References

1. Check the anti-pattern table above first — the answer may already be there.
2. Find the relevant project section and topic in the index. Load only that file, not multiple.
3. Some large topics have their own sub-index — load the specific sub-section you need.
4. Before writing a custom `@Bean` or `@Configuration`, check if a `spring.*` property already controls the behavior.
5. Before writing a custom REST endpoint for health/metrics, check Actuator first.
6. For Spring Cloud, check if a starter already provides the integration you need.
