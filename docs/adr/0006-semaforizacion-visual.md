---
id: ADR-0006
title: Implementación de Semaforización Visual Basada en Confidence Score
date: 2026-06-10
status: accepted
---

# ADR 0006: Implementación de Semaforización Visual Basada en Confidence Score

## Context
The cytogenetic analyst needs to rapidly identify chromosomes that require human review without manually checking each confidence score. The system must highlight these "at-risk" chromosomes to prioritize manual validation and ensure compliance with clinical safety standards.

## Decision
We implement a visual traffic light (semaforización) system integrated into the Konva.js canvas editor:
1. **Green (≥ 0.85):** High confidence. The chromosome is considered "pre-validated" but still subject to random 5% audit (RN-08).
2. **Orange (< 0.85):** Low confidence. These chromosomes MUST be manually reviewed and accepted by the analyst before the report can be exported (RN-02).
3. **Red (Error/Critical):** System error or failed classification. Immediate manual intervention required.

## Trade-offs
- **Pros:** Significantly reduces cognitive load for the specialist, enforces RN-02 at the UI level, and accelerates the validation process.
- **Cons:** Adds complexity to the frontend rendering logic in Konva.js and increases the number of state updates required via WebSockets.

## Consequences
- The UI will now explicitly block the "Export Report" action if any "Orange" or "Red" chromosomes remain unvalidated.
- Visual feedback is synchronized in real-time with the backend via the WebSocket push event "Borrador listo".
- Implementation requires tight integration between the `confidence_score` from the AI engine and the Konva.js shape properties.
