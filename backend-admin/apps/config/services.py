"""
Servicios de dominio de apps/config (DD-ADMIN-002).

P0: placeholder. Servicios concretos a añadir en P1–P6:
- P1: (sin service; la lógica es trivial en el viewset)
- P2: rotate_password(user, current, new, confirm) — RN-12 implícito
- P3: get_active_model_config() con select_for_update anti-race
- P4: (sin service)
- P5: test_integration_connection(integration) con timeout 5s
- P6: (sin service)
"""
