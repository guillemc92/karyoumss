---
id: ADR-0003
title: CHN Anonymization at the Edge
date: 2026-05-25
status: accepted
---

# ADR 0003: CHN Anonymization at the Edge

## Context
Medical data (PII) is subject to strict laws. Sending patient names or IDs to cloud-based GPU clusters (TorchServe) creates a critical security risk and violates legal compliance.

## Decision
We implement "Anonymization at the Edge":
1. The frontend/local node generates a unique **CHN code** (format: `CHN-YYYY-MM-DD-NNNN`).
2. The mapping between the real patient and the CHN code is stored in a local, encrypted vault.
3. Only the CHN code and the image (stripped of DICOM metadata) are transmitted to the backend and AI engine.

## Trade-offs
- **Pros:** Absolute PII isolation, compliance with medical secrecy laws, reduced liability for the cloud provider.
- **Cons:** Dependency on the local vault for recovery; if the vault is lost, the sample cannot be re-linked to the patient.

## Consequences
- All API endpoints and logs must use CHN codes exclusively.
- Any PII detected in requests to TorchServe must trigger a critical system alert.
