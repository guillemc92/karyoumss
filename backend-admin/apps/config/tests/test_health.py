"""
Tests del bounded context config (DD-ADMIN-002).

P0: smoke test del health check para validar routing + bootstrap.
Tests concretos por sección se añaden en P1–P6 con cobertura ≥90%
(RN-09) por archivo de test.
"""
from django.test import TestCase
from django.urls import reverse


class ConfigHealthTests(TestCase):
    """P0: el health check responde 200 + shape correcto."""

    def test_health_endpoint_returns_ok(self):
        url = reverse('config:health')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body['status'], 'ok')
        self.assertEqual(body['app'], 'config')
        self.assertIn('version', body)
        self.assertIn('sections', body)
        # sections es lista; P1 añade 'profile', P2+ añadirá más
        self.assertIsInstance(body['sections'], list)
        self.assertIn('profile', body['sections'])

    def test_health_does_not_require_auth(self):
        """Health check es público (AllowAny) para no bloquear health probes."""
        url = reverse('config:health')
        # Sin Authorization header
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
