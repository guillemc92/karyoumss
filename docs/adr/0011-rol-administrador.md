---
id: ADR-0011
title: Diseño del Rol de Administrador (Inicio Simple)
date: 2026-06-23
status: accepted
---

# ADR 0011: Diseño del Rol de Administrador (Inicio Simple)

## Contexto

El sistema necesita un rol de **Administrador institucional (TI)** que pueda gestionar usuarios, configurar parámetros del sistema (como el umbral de confianza), monitorear logs y auditar el uso, sin interferir en el flujo clínico diario.

## Decisión

Implementar un rol de **Administrador** con permisos limitados y separados del rol de **Supervisor Clínico** y **Analista**.

## Justificación

- **Separación clara de responsabilidades** (principio de menor privilegio).
- Cumple con requerimientos de TI institucional mencionados en el BRD.
- Evita que un administrador clínico tenga acceso a configuración técnica.
- Facilita auditoría y compliance.

## Consecuencias

**Positivas:**

- Mayor seguridad y control institucional.
- Permite configuración del umbral de confianza (0.85) de forma centralizada.
- Facilita monitoreo del sistema.

**Negativas:**

- Aumenta ligeramente la complejidad de autenticación y autorización.
- Requiere UI específica para el Admin.

**Neutras:**

- Se implementará usando el mismo sistema de roles (RBAC) que ya existe.
