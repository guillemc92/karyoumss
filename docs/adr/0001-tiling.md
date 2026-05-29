---
id: ADR-0001
title: Tiling and NMS for High-Resolution Meta-phase Images
date: 2026-05-20
status: accepted
---

# ADR 0001: Tiling and NMS for High-Resolution Meta-phase Images

## Context
Meta-phase images in citogenetics often exceed 4K resolution (e.g., 8000x6000px). Processing these as a single tensor in GPU memory leads to Out-Of-Memory (OOM) errors and loss of fine detail due to aggressive downsampling.

## Decision
We implement a Tiling strategy:
1. Divide images > 4K into $1024 \times 1024\text{px}$ tiles.
2. Apply an overlap of $64\text{px}$ to prevent chromosomes from being cut at the edges.
3. Use Non-Maximum Suppression (NMS) with an IoU threshold of 0.5 to merge duplicate detections in overlap zones.

## Trade-offs
- **Pros:** Constant memory footprint, preservation of high-frequency details (G-bands), scalability.
- **Cons:** Increased total inference time (multiple forward passes per image), added complexity in coordinate re-mapping.

## Consequences
- Inference is now bound by the number of tiles, not the image size.
- Coordinates are managed in a global system relative to the original image.
