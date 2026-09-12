"""
Migración inicial del bounded context admin (apps/users).

El db_table se deriva en runtime via _admin_schema_table() en models.py:
- PostgreSQL prod: admin.users_user, admin.admin_users (ADR-0012 schema isolation)
- SQLite tests:   users_user, admin_users (plano)

Django emite el SQL del modelo directamente al crear las tablas, usando el
db_table que el modelo declara en el momento del import. Por eso:
- Con settings.DATABASES ENGINE=postgresql → db_table='admin"."users_user'
- Con settings.DATABASES ENGINE=sqlite3   → db_table='users_user'

Si el día de mañana se necesita MySQL u otro vendor, basta con agregar la rama
en _admin_schema_table() y regenerar esta migration con --database apuntando
al nuevo vendor.
"""

import uuid

import django.contrib.auth.models
import django.contrib.auth.validators
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether this user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('role', models.CharField(choices=[('analista', 'Analista Citogenetista'), ('supervisor', 'Supervisor Clínico'), ('admin', 'Administrador TI')], default='analista', max_length=16)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for each of their groups.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'Usuario (auth)',
                'verbose_name_plural': 'Usuarios (auth)',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='AdminUser',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('full_name', models.CharField(max_length=80)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('role', models.CharField(choices=[('analista', 'Analista Citogenetista'), ('supervisor', 'Supervisor Clínico'), ('admin', 'Administrador TI')], default='analista', max_length=16)),
                ('active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deactivated_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_users', to='users.adminuser')),
                ('user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='admin_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Cuenta institucional',
                'verbose_name_plural': 'Cuentas institucionales',
                'db_table': 'admin_users',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='adminuser',
            constraint=models.CheckConstraint(check=models.Q(role__in=['analista', 'supervisor', 'admin']), name='admin_users_role_valid'),
        ),
        migrations.AddConstraint(
            model_name='adminuser',
            constraint=models.CheckConstraint(
                check=models.Q(deactivated_at__isnull=True, active=False, _connector='OR'),
                name='admin_users_deactivated_implies_inactive',
            ),
        ),
        # Índice único case-insensitive en Postgres. SQLite no soporta
        # functional indexes, así que esta operación se salta en SQLite.
        # En SQLite, AdminUser.email tiene unique=True que Django traduce a
        # UNIQUE constraint case-sensitive (suficiente para tests). En prod,
        # este índice es la autoridad final para unicidad de emails.
        migrations.RunPython(
            code=lambda apps, schema_editor: (
                schema_editor.execute(
                    'CREATE UNIQUE INDEX IF NOT EXISTS admin_users_email_lower_unique_idx '
                    'ON admin."admin_users" (LOWER(email))'
                )
                if schema_editor.connection.vendor == 'postgresql'
                else None  # no-op en SQLite
            ),
            reverse_code=lambda apps, schema_editor: (
                schema_editor.execute(
                    'DROP INDEX IF EXISTS admin.admin_users_email_lower_unique_idx'
                )
                if schema_editor.connection.vendor == 'postgresql'
                else None
            ),
        ),
    ]