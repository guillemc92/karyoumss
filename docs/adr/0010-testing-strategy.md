---
id: ADR-0010
title: Estrategia de Testing (TDD + Gherkin + Integración Clínica)
date: 2026-06-10
status: accepted
---

# ADR 0010: Estrategia de Testing (TDD + Gherkin + Integración Clínica)

## Context
Due to the critical nature of clinical diagnostics, the system cannot afford regressions in the rules that govern chromosome validation (RN-01 to RN-08). We need a testing strategy that ensures these rules are always respected and provides living documentation of the clinical expectations.

## Decision
We adopt a comprehensive testing strategy based on:
1. **TDD (Test-Driven Development):** All new features must be preceded by a failing test.
2. **Gherkin-style BDD:** Using "Given/When/Then" scenarios to describe clinical use cases, which serve as the source for integration tests.
3. **End-to-End Integration:** Validating the full flow from image upload to report generation.

## Trade-offs
- **Pros:** Guarantees that clinical invariants (RN-01 to RN-08) are never violated, facilitates the use of the `skill-validation-agent`, and significantly improves long-term maintainability.
- **Cons:** Increased initial development time and more overhead in maintaining the test suite.

## Consequences
- The project maintains an exceptionally high standard of code quality.
- Regression testing becomes automated, allowing for faster and safer releases to `release/2.0.0`.
- Documentation is always in sync with the actual behavior of the system.
