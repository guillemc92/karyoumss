---
id: ADR-0002
title: Async Pipeline using Redis and Celery
date: 2026-05-22
status: accepted
---

# ADR 0002: Async Pipeline using Redis and Celery

## Context
The AI pipeline (CLAHE $\to$ Tiling $\to$ Segmentation $\to$ Classification) takes between 8 and 15 seconds per sample. A synchronous HTTP request would lead to timeout errors and a poor user experience.

## Decision
We implement an asynchronous orchestration pattern:
1. FastAPI accepts the upload and immediately returns `202 Accepted`.
2. The task is enqueued in a Redis broker.
3. A Celery worker consumes the task and executes the AI pipeline.
4. Upon completion, a WebSocket event is pushed to the client via a dedicated Manager.

## Trade-offs
- **Pros:** Decoupled processing, improved system resilience (retries), non-blocking UI.
- **Cons:** Eventual consistency of sample status, requirement for a persistent message broker.

## Consequences
- System can handle spikes in uploads by scaling Celery workers.
- WebSocket integration is required for real-time updates.
