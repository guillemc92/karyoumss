# 🗺️ Roadmap BIOMED UMSS - Path to v2.0

## 🚀 Fase 1: Core Stabilisation (S06 - S09)
- [x] Implementación de Ingesta Asíncrona (FSD-UC-001).
- [x] Motor de Segmentación U-Net + EfficientNet-B3.
- [x] Mesa de Edición Interactiva con Konva.js.
- [x] Anonimización CHN en el Borde.

## 📈 Fase 2: Clinical Validation & Scale (S10 - S12)
- [ ] Implementación de Firma Digital con MFA (TOTP/Huella).
- [ ] Motor determinístico de Nomenclatura ISCN 2024.
- [ ] Audit Trail inmutable con Hash Chain (Sincronización con PostgreSQL).
- [ ] Implementación de la Auditoría Aleatoria (5% Verdes).

## 🌐 Fase 3: Enterprise Integration (Post-Defensa)
- [ ] Integración HL7 FHIR para envío a LIS Hospitalarios.
- [ ] Despliegue en Cluster GPU AWS (Triton Inference Server).
- [ ] Dashboard de métricas de calidad del modelo para el Director del Lab.
- [ ] Soporte para Microarrays (CMA) y NGS.

## ⚠️ Riesgos Monitorizados
- **Latencia de Red:** Mitigado mediante Tiling y procesamiento asíncrono.
- **Sesgo de Automatización:** Mitigado mediante XAI (Grad-CAM) y revisión humana obligatoria.
