---
name: spring-best-practices
description: Official Spring Framework and Spring Boot {version} reference docs with best practices and anti-patterns. ALWAYS load when working on a Spring service — editing application.yml, application.properties, application-*.yml, bootstrap.yml, build.gradle / build.gradle.kts / pom.xml with spring-boot-starter dependencies, or any Java/Kotlin/Scala source containing @SpringBootApplication, @RestController, @Service, @Repository, @Component, @Configuration, @Bean, @ConfigurationProperties, @EnableAutoConfiguration, @EnableEurekaClient, @FeignClient, @KafkaListener annotations. Also load when user mentions "Spring", "Spring Boot", "Spring Cloud", "Spring Security", "Spring Data", "Actuator", "Eureka", "Feign", "auto-configuration", "dependency injection", or asks about application.yml / application.properties configuration.
paths:
  - "**/application.yml"
  - "**/application.yaml"
  - "**/application.properties"
  - "**/application-*.yml"
  - "**/application-*.yaml"
  - "**/application-*.properties"
  - "**/bootstrap.yml"
  - "**/bootstrap.yaml"
  - "**/bootstrap.properties"
  - "**/spring.factories"
  - "**/META-INF/spring/*.imports"
  - "**/META-INF/spring.factories"
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

## Reference Projects

Load the project you need, then drill into sections and topics. Do **not** load everything at once.

{project_index}

---

## How to Use These References

1. Check the anti-pattern table above first — the answer may already be there.
2. Open the relevant project's `CONTENTS.md` to see available sections.
3. Open the section's `CONTENTS.md` to see available topics.
4. Load only the specific topic file you need.
5. Before writing a custom `@Bean`, check if a `spring.*` property already controls the behavior.
6. Before writing a custom endpoint for health/metrics, check Actuator first.
