"""
Tests E2E in-process del auth bridge FastAPI ↔ Django (F7 — ADR-0013).

Cubre el flujo HTTP completo:
  1. Stand-in FastAPI firma un JWT HS256 con AUTH_BRIDGE_SECRET compartido.
  2. Django recibe ese JWT vía POST /api/admin/auth/exchange (Bearer).
  3. Django valida la firma, canjea por un DRF Token.
  4. Cliente usa el DRF Token para llamar GET /api/admin/users/.

No se levanta un servidor FastAPI real (eso es F9 con docker-compose).
Lo que se verifica aquí es:
  - El endpoint /api/admin/auth/exchange acepta un JWT firmado con el secret
    compartido y emite un DRF Token utilizable.
  - Errores: JWT expirado, firma inválida, rol inválido, sin Bearer, JWT mal formado.

RN-03: emails del dominio @biomed.umss.bo (ficticios), no se transmite PII real.
"""

from __future__ import annotations

from datetime import timedelta

import jwt as pyjwt
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers — simulan el backend-clinical firmando un JWT HS256.
# ---------------------------------------------------------------------------

def _make_fastapi_jwt(payload: dict, secret: str, algorithm: str = 'HS256') -> str:
    """Stand-in del endpoint /api/v1/auth/login de FastAPI."""
    return pyjwt.encode(payload, secret, algorithm=algorithm)


def _valid_fastapi_payload(**overrides) -> dict:
    """Payload típico que FastAPI emitiría en /api/v1/auth/login."""
    defaults = {
        'sub': 'uuid-fastapi-user-001',
        'email': 'admin@biomed.umss.bo',
        'role': 'admin',
        'iat': int(timezone.now().timestamp()),
        'exp': int((timezone.now() + timedelta(hours=1)).timestamp()),
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# E2E happy path
# ---------------------------------------------------------------------------

class TestE2EHappyPath:
    def test_login_exchange_then_list_users(self, settings):
        """
        Flujo completo:
          1. FastAPI (stand-in) firma JWT con AUTH_BRIDGE_SECRET.
          2. POST /api/admin/auth/exchange con Bearer → 200 + DRF token.
          3. GET /api/admin/users/ con DRF token → 200 con lista (vacía al inicio).
        """
        # Paso 1: stand-in FastAPI firma el JWT
        jwt_token = _make_fastapi_jwt(
            _valid_fastapi_payload(),
            secret=settings.AUTH_BRIDGE_SECRET,
        )

        # Paso 2: cliente anónimo llama /api/admin/auth/exchange
        anon = APIClient()
        resp = anon.post(
            '/api/admin/auth/exchange',
            HTTP_AUTHORIZATION=f'Bearer {jwt_token}',
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert 'token' in body
        assert body['role'] == 'admin'
        assert body['email'] == 'admin@biomed.umss.bo'
        assert 'expires_at' in body
        django_token = body['token']

        # Paso 3: usar el DRF token para listar usuarios
        authed = APIClient()
        authed.credentials(HTTP_AUTHORIZATION=f'Token {django_token}')
        resp_list = authed.get('/api/admin/users/')
        assert resp_list.status_code == 200, resp_list.content
        # La lista puede tener el AdminUser recién creado por el exchange + nada más
        assert isinstance(resp_list.json(), list)

    def test_exchange_creates_admin_user_in_domain(self, settings):
        """El exchange crea el AdminUser de dominio si no existía."""
        from apps.users.models import AdminUser, User
        jwt_token = _make_fastapi_jwt(
            _valid_fastapi_payload(
                email='nuevo.admin@biomed.umss.bo',
                role='admin',
            ),
            secret=settings.AUTH_BRIDGE_SECRET,
        )
        anon = APIClient()
        resp = anon.post(
            '/api/admin/auth/exchange',
            HTTP_AUTHORIZATION=f'Bearer {jwt_token}',
        )
        assert resp.status_code == 200, resp.content
        # El User de Django existe
        assert User.objects.filter(email='nuevo.admin@biomed.umss.bo').exists()
        # El AdminUser de dominio fue creado por el exchange (no requiere seed previo)
        assert AdminUser.objects.filter(email='nuevo.admin@biomed.umss.bo').exists()

    def test_exchange_is_idempotent_for_same_email(self, settings):
        """Llamar exchange dos veces con mismo JWT → mismo DRF token."""
        jwt_token = _make_fastapi_jwt(
            _valid_fastapi_payload(email='repeat@biomed.umss.bo'),
            secret=settings.AUTH_BRIDGE_SECRET,
        )
        anon = APIClient()
        r1 = anon.post(
            '/api/admin/auth/exchange',
            HTTP_AUTHORIZATION=f'Bearer {jwt_token}',
        )
        r2 = anon.post(
            '/api/admin/auth/exchange',
            HTTP_AUTHORIZATION=f'Bearer {jwt_token}',
        )
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()['token'] == r2.json()['token']


# ---------------------------------------------------------------------------
# E2E errores — cada uno debe devolver 401 con mensaje útil
# ---------------------------------------------------------------------------

class TestE2EFailures:
    def test_missing_bearer_header_returns_401(self):
        anon = APIClient()
        resp = anon.post('/api/admin/auth/exchange')
        assert resp.status_code == 401
        assert 'bearer' in resp.json()['error'].lower()

    def test_wrong_auth_scheme_returns_401(self):
        """Authorization: Basic ... no es válido para /auth/exchange."""
        anon = APIClient()
        resp = anon.post(
            '/api/admin/auth/exchange',
            HTTP_AUTHORIZATION='Basic dXNlcjpwYXNz',
        )
        assert resp.status_code == 401

    def test_expired_jwt_returns_401(self, settings):
        jwt_token = _make_fastapi_jwt(
            _valid_fastapi_payload(
                exp=int((timezone.now() - timedelta(minutes=5)).timestamp()),
            ),
            secret=settings.AUTH_BRIDGE_SECRET,
        )
        anon = APIClient()
        resp = anon.post(
            '/api/admin/auth/exchange',
            HTTP_AUTHORIZATION=f'Bearer {jwt_token}',
        )
        assert resp.status_code == 401
        assert 'expired' in resp.json()['error'].lower()

    def test_invalid_signature_returns_401(self, settings):
        """JWT firmado con secret distinto al compartido."""
        jwt_token = _make_fastapi_jwt(
            _valid_fastapi_payload(),
            secret='wrong-secret-' + 'x' * 50,
        )
        anon = APIClient()
        resp = anon.post(
            '/api/admin/auth/exchange',
            HTTP_AUTHORIZATION=f'Bearer {jwt_token}',
        )
        assert resp.status_code == 401
        assert 'invalid' in resp.json()['error'].lower()

    def test_invalid_role_returns_401(self, settings):
        """JWT con role=hacker (no en AUTH_BRIDGE_VALID_ROLES)."""
        jwt_token = _make_fastapi_jwt(
            _valid_fastapi_payload(role='hacker'),
            secret=settings.AUTH_BRIDGE_SECRET,
        )
        anon = APIClient()
        resp = anon.post(
            '/api/admin/auth/exchange',
            HTTP_AUTHORIZATION=f'Bearer {jwt_token}',
        )
        assert resp.status_code == 401

    def test_missing_required_claim_returns_401(self, settings):
        """JWT sin claim 'role'."""
        payload = _valid_fastapi_payload()
        del payload['role']
        jwt_token = _make_fastapi_jwt(payload, secret=settings.AUTH_BRIDGE_SECRET)
        anon = APIClient()
        resp = anon.post(
            '/api/admin/auth/exchange',
            HTTP_AUTHORIZATION=f'Bearer {jwt_token}',
        )
        assert resp.status_code == 401

    def test_malformed_jwt_returns_401(self):
        """String basura en lugar de JWT."""
        anon = APIClient()
        resp = anon.post(
            '/api/admin/auth/exchange',
            HTTP_AUTHORIZATION='Bearer not-a-real-jwt',
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# E2E flujo completo admin puede usar el sistema post-exchange
# ---------------------------------------------------------------------------

class TestE2EPostExchange:
    def test_admin_can_create_user_after_exchange(self, settings):
        """
        Después de hacer exchange, el admin (rol=admin) puede:
          - listar usuarios (GET)
          - crear un nuevo AdminUser (POST)
        Esto valida que el DRF token tiene los permisos correctos.
        """
        # 1) Exchange
        jwt_token = _make_fastapi_jwt(
            _valid_fastapi_payload(email='root.admin@biomed.umss.bo', role='admin'),
            secret=settings.AUTH_BRIDGE_SECRET,
        )
        anon = APIClient()
        resp = anon.post(
            '/api/admin/auth/exchange',
            HTTP_AUTHORIZATION=f'Bearer {jwt_token}',
        )
        assert resp.status_code == 200
        django_token = resp.json()['token']

        # 2) Crear otro usuario
        authed = APIClient()
        authed.credentials(HTTP_AUTHORIZATION=f'Token {django_token}')
        resp_create = authed.post(
            '/api/admin/users/',
            data={
                'full_name': 'Carlos López',
                'email': 'carlos.lopez@biomed.umss.bo',
                'role': 'analista',
                'active': True,
            },
            format='json',
        )
        assert resp_create.status_code == 201, resp_create.content
        created = resp_create.json()
        assert created['email'] == 'carlos.lopez@biomed.umss.bo'
        assert created['role'] == 'analista'
        assert created['active'] is True

        # 3) Listar y verificar que aparece
        resp_list = authed.get('/api/admin/users/')
        assert resp_list.status_code == 200
        emails = [u['email'] for u in resp_list.json()]
        assert 'carlos.lopez@biomed.umss.bo' in emails
        # El admin que hizo el exchange también está en la lista
        assert 'root.admin@biomed.umss.bo' in emails

    def test_non_admin_role_cannot_create_user(self, settings):
        """
        Si el JWT trae role=supervisor, el exchange funciona pero el supervisor
        no puede crear usuarios (IsAdminRole lo bloquea → 403).
        """
        jwt_token = _make_fastapi_jwt(
            _valid_fastapi_payload(email='sup.user@biomed.umss.bo', role='supervisor'),
            secret=settings.AUTH_BRIDGE_SECRET,
        )
        anon = APIClient()
        resp = anon.post(
            '/api/admin/auth/exchange',
            HTTP_AUTHORIZATION=f'Bearer {jwt_token}',
        )
        assert resp.status_code == 200
        django_token = resp.json()['token']

        authed = APIClient()
        authed.credentials(HTTP_AUTHORIZATION=f'Token {django_token}')
        resp_create = authed.post(
            '/api/admin/users/',
            data={
                'full_name': 'Otro Usuario',
                'email': 'otro@biomed.umss.bo',
                'role': 'analista',
            },
            format='json',
        )
        # El exchange aceptó al supervisor (es rol válido), pero la mutación está
        # restringida por IsAdminRole → 403.
        assert resp_create.status_code == 403
