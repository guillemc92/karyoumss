"""Valores de prueba para los secretos obligatorios (DD-AUD-001 F3).

`DJANGO_SECRET_KEY` e `INTERNAL_SERVICE_SECRET` son obligatorios: `settings`
falla al importarse si faltan. Las pruebas no deben depender de que el `.env` de
cada desarrollador los tenga.

Es un plugin de pytest (`-p pruebas_entorno` en `pytest.ini`) y no un
`conftest.py` porque pytest-django importa `settings` ANTES de cargar los
conftest; los plugins de `-p` se cargan antes que eso. `setdefault` no pisa lo
que ya venga del entorno.
"""
import os

os.environ.setdefault('DJANGO_SECRET_KEY', 'test-clinic-secret-key-not-for-production-' + 'x' * 30)
os.environ.setdefault('INTERNAL_SERVICE_SECRET', 'test-internal-service-secret-' + 'd' * 40)
