"""
Lógica de negocio para AdminUser (apps/users).

Funciones puras (testables sin DRF). Las views consumen estos helpers.
"""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .models import AdminUser, EMAIL_RE, _normalize_email, _validate_full_name, VALID_ROLES


def create_admin_user(*, full_name: str, email: str, role: str,
                      active: bool = True, created_by: AdminUser | None = None) -> AdminUser:
    """
    Crea un AdminUser con validaciones completas.
    Raises ValidationError si hay problema de datos.
    Raises IntegrityError si el email ya existe (UNIQUE constraint DB).
    """
    full_name = _validate_full_name(full_name)
    email = _normalize_email(email)
    if role not in VALID_ROLES:
        raise ValidationError(f'Rol inválido. Debe ser uno de: {VALID_ROLES}')

    with transaction.atomic():
        admin_user = AdminUser(
            full_name=full_name,
            email=email,
            role=role,
            active=active,
            created_by=created_by,
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