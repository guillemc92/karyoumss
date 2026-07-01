"""
Factories factory_boy para tests de backend-admin.

Uso:
    from apps.users.factories import AdminUserFactory, UserFactory
    user = AdminUserFactory(email='x@biomed.umss.bo')
    users = AdminUserFactory.create_batch(3, role='supervisor')
"""
from __future__ import annotations

import factory
from factory.django import DjangoModelFactory
from rest_framework.authtoken.models import Token


class UserFactory(DjangoModelFactory):
    """Django auth User con rol parametrizable."""

    class Meta:
        model = 'users.User'
        django_get_or_create = ('email',)

    email = factory.Sequence(lambda n: f'user{n}@biomed.umss.bo')
    username = factory.LazyAttribute(lambda o: o.email)
    role = 'analista'
    is_active = True
    is_staff = False
    is_superuser = False


class AdminUserFactory(DjangoModelFactory):
    """AdminUser de dominio (cuenta institucional)."""

    class Meta:
        model = 'users.AdminUser'

    full_name = factory.Sequence(lambda n: f'Usuario Institucional {n}')
    email = factory.Sequence(lambda n: f'admin{n}@biomed.umss.bo')
    role = 'analista'
    active = True
    user = factory.SubFactory(UserFactory, email=factory.SelfAttribute('..email'))

    @factory.lazy_attribute
    def user(self):
        # Crea/recupera un User con el mismo email para mantener 1:1 lógico.
        return UserFactory(email=self.email)


class DeactivatedAdminUserFactory(AdminUserFactory):
    """AdminUser ya desactivado (soft-deleted)."""
    active = False
    deactivated_at = factory.LazyFunction(
        lambda: __import__('django.utils.timezone', fromlist=['timezone']).now()
    )


class TokenFactory(DjangoModelFactory):
    """DRF Token vinculado a un User."""

    class Meta:
        model = Token

    user = factory.SubFactory(UserFactory)