"""
Lógica de negocio para AdminUser (apps/users).

Funciones puras (testables sin DRF). Las views consumen estos helpers.
"""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .models import AdminUser, User, EMAIL_RE, _normalize_email, _validate_full_name, VALID_ROLES

# Misma política que apps.config.services.rotate_password (P2, ADR-0014
# §Seguridad) — duplicada acá porque apps.config depende de apps.users
# (no al revés) y no vale la pena invertir esa dependencia por 3 líneas.
PASSWORD_MIN_LENGTH = 12


def _validate_password_strength(password: str) -> None:
    if (
        len(password) < PASSWORD_MIN_LENGTH
        or not re.search(r'[A-Z]', password)
        or not re.search(r'[0-9]', password)
    ):
        raise ValidationError(
            {'password': f'Mínimo {PASSWORD_MIN_LENGTH} caracteres, 1 mayúscula, 1 dígito'}
        )


def create_admin_user(*, full_name: str, email: str, role: str, password: str,
                      active: bool = True, created_by: AdminUser | None = None) -> AdminUser:
    """
    Crea un AdminUser CON un `users.User` vinculado y autenticable.

    Bug corregido (detectado en demo, 2026-07-23): antes solo se creaba la
    fila AdminUser (cuenta institucional/dominio); el login real
    (`/api/auth/login/`, ADR-0017) valida contra `users.User.password`, no
    contra AdminUser — así que un usuario recién creado no tenía forma de
    entrar al sistema. `password` es ahora obligatorio y se usa para crear
    (o adoptar, si ya existía huérfano de un exchange previo sin AdminUser)
    el User vinculado.

    Raises ValidationError si hay problema de datos (incluida fortaleza
    de contraseña). Raises IntegrityError si el email ya existe en
    AdminUser (UNIQUE constraint DB).
    """
    full_name = _validate_full_name(full_name)
    email = _normalize_email(email)
    if role not in VALID_ROLES:
        raise ValidationError(f'Rol inválido. Debe ser uno de: {VALID_ROLES}')
    _validate_password_strength(password)

    with transaction.atomic():
        # get_or_create: un User puede existir ya (ej. hizo login/exchange
        # antes de que un admin le diera de alta la cuenta institucional).
        # En ese caso lo "adoptamos": misma contraseña/rol que se acaba de
        # definir acá, no dos identidades desincronizadas.
        auth_user, _ = User.objects.get_or_create(email=email)
        auth_user.role = role
        auth_user.is_active = active
        auth_user.is_staff = (role == 'admin')
        auth_user.set_password(password)
        auth_user.save()

        admin_user = AdminUser(
            full_name=full_name,
            email=email,
            role=role,
            active=active,
            created_by=created_by,
            user=auth_user,
        )
        admin_user.full_clean()  # Valida constraints del modelo
        try:
            admin_user.save()
        except IntegrityError as e:
            # UNIQUE constraint violation → email duplicado
            if 'email' in str(e).lower():
                raise ValidationError({'email': 'Email ya registrado'})
            raise
    return admin_user


def update_admin_user(admin_user: AdminUser, *, full_name: str | None = None,
                      role: str | None = None, active: bool | None = None) -> AdminUser:
    """
    Actualiza campos permitidos (full_name, role, active). Email NO se modifica en MVP.
    """
    if full_name is not None:
        admin_user.full_name = _validate_full_name(full_name)
    if role is not None:
        if role not in VALID_ROLES:
            raise ValidationError(f'Rol inválido. Debe ser uno de: {VALID_ROLES}')
        admin_user.role = role
    if active is not None:
        admin_user.active = active
        if not active and admin_user.deactivated_at is None:
            # Si lo desactivan sin soft-delete explícito, marcar también deactivated_at
            from django.utils import timezone
            admin_user.deactivated_at = timezone.now()
        elif active and admin_user.deactivated_at is not None:
            # Reactivar
            admin_user.deactivated_at = None

    admin_user.full_clean()
    admin_user.save()
    return admin_user


def soft_delete_admin_user(admin_user: AdminUser, actor: AdminUser | None = None) -> AdminUser:
    """
    Soft-delete idempotente. Raises ValidationError si ya está desactivado.
    """
    if admin_user.deactivated_at is not None:
        raise ValidationError('El usuario ya está desactivado')
    admin_user.soft_delete(actor=actor)
    return admin_user


def can_delete_user(target: AdminUser, current_user_id: int | None) -> bool:
    """
    Verifica si el actor puede desactivar el target.
    Regla: nadie puede desactivarse a sí mismo.
    """
    if current_user_id is None:
        return True
    return target.user_id != current_user_id


def validate_email_format(email: str) -> str:
    """Valida formato de email. Raises ValidationError si inválido."""
    e = _normalize_email(email)
    if not EMAIL_RE.match(e):
        raise ValidationError('Email inválido')
    return e