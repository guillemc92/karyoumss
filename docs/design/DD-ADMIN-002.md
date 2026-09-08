# DD-ADMIN-002 — Diseño Detallado: Panel "Configuración del Sistema" (6 secciones + shell)

> **Documento de Diseño Detallado** del bounded context admin.
> Espejo técnico de **ADR-0014** y de **FSD-UC-ADMIN-001** (panel Configuración).
> Este DD **no** redefine el stack (eso es ADR-0013) ni la separación por
> bounded context (ADR-0011, ADR-0012). Define **el cómo** de las 6 secciones
> que el panel "Configuración del Sistema" requiere para dejar de ser demo.

| Campo | Detalle |
|---|---|
| **Producto** | BIOMED UMSS — Intelligent Karyotyping Platform |
| **Bounded context** | admin (ADR-0011, ADR-0013) |
| **Documento drive** | [ADR-0014](../adr/0014-configuracion-panel-react-real-backend.md) |
| **Documento funcional** | FSD-UC-ADMIN-001 §5 (panel Configuración) |
| **Stack backend** | Django 5 + DRF 3.15 + django-auditlog + django-guardian (ADR-0013) |
| **Stack frontend** | React 18 + Vite 5 + TypeScript 5 + Vitest 1.x + MSW 2.x (ADR-0013) |
| **Versión** | 0.1 (borrador P0) |
| **Fecha** | 2026-07-08 |
| **Autor** | Ing. Guillermo Mamani Chambi |
| **Estado** | proposed |

---

## 0. Cómo leer este documento

Cada sección P1–P6 sigue la misma plantilla para que la revisión por fase
sea predecible:

1. **Caso de uso FSD** al que responde.
2. **Modelo backend** (campos, constraints, índices).
3. **Endpoints DRF** (URL, método, permiso, request/response).
4. **Componentes React** (ruta, props, estados).
5. **Validaciones** (cliente y servidor).
6. **Tests mínimos** para RN-09 ≥90%.

P0 (skeleton) y P7–P10 (shell, migración localStorage, E2E, docs) cierran
el documento.

---

## 1. P0 — Skeleton de `apps/config` y routing

### 1.1 Estructura de archivos a crear

```
backend-admin/
└── apps/
    └── config/
        ├── __init__.py
        ├── apps.py
        ├── models.py              (6 modelos, ver §2–§7)
        ├── serializers.py         (6 serializers)
        ├── views.py               (6 viewsets + 1 viewset /me)
        ├── urls.py                (router + /me/*)
        ├── permissions.py         (IsOwnerOrAdmin)
        ├── services.py            (lógica dominio: rotate_password, test_integration_connection, get_active_model_config)
        ├── migrations/            (auto-generadas por makemigrations)
        └── tests/
            ├── __init__.py
            ├── test_profile.py
            ├── test_security.py
            ├── test_models_config.py
            ├── test_notifications.py
            ├── test_integrations.py
            ├── test_appearance.py
            └── conftest.py        (factories compartidos)

frontend-admin/
└── src/
    └── admin/
        ├── types/
        │   └── config.ts         (types manuales, espejo de serializers)
        ├── api/
        │   └── adminConfigClient.ts  (6 clientes tipados)
        ├── components/
        │   ├── ConfigShell.tsx
        │   ├── ConfigContent.tsx
        │   ├── ConfigSection.tsx     (esqueleto loading/error/data)
        │   ├── ConfigForm.tsx        (form genérico con Zod)
        │   ├── ErrorBanner.tsx
        │   ├── Skeleton.tsx
        │   ├── ProfileSection.tsx
        │   ├── SecuritySection.tsx
        │   ├── ModelsSection.tsx
        │   ├── NotificationsSection.tsx
        │   ├── IntegrationsSection.tsx
        │   ├── AppearanceSection.tsx
        │   └── LocalStorageMigrationBanner.tsx
        └── state/
            └── adminConfigStore.tsx  (opcional; ver §11)
```

### 1.2 Registro

- `backend-admin/admin_backend/settings.py` → añadir `'apps.config'` a `INSTALLED_APPS`.
- `backend-admin/admin_backend/urls.py` → añadir
  `path('api/admin/', include('apps.config.urls', namespace='config'))`
  junto al include de `apps.users`.
- `apps.config.apps.py` → `name = 'apps.config'`, `label = 'admin_config'`
  (label explícito para evitar colisión con `apps.users` en migraciones).

### 1.3 Convenciones heredadas de `apps/users`

- `db_table` derivado de `connection.vendor` mediante helper
  `_admin_schema_table('admin_<tabla>')` (mismo patrón que `apps/users/models.py:59`).
- `django-auditlog` registra **todos los modelos** por default
  (create/update/delete con `actor`).
- Tabla `audit_log` separada (la de `apps.audit`) recibe los
  `LogEntry` automáticamente.
- Tests usan `pytest-django` con `pytest-cov`, factory_boy
  ya en `apps/users/factories.py` se reusan cuando aplique.

### 1.4 Permiso nuevo: `IsOwnerOrAdmin`

```python
# apps/config/permissions.py
from rest_framework.permissions import BasePermission

class IsOwnerOrAdmin(BasePermission):
    """
    Para endpoints /me/*:
    - GET: el propio usuario autenticado O un admin.
    - PATCH/POST: el propio usuario O un admin.
    El admin puede ver/editar el recurso de cualquier usuario; el usuario
    normal solo el propio.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, 'role', None) == 'admin':
            return True
        # obj.user es la FK al User de auth
        return obj.user_id == request.user.id
```

---

## 2. P1 — Sección Perfil (`profile-tab`)

### 2.1 Caso de uso (FSD)

**FSD-UC-CONF-001 — Editar perfil propio.**
- Actor: cualquier usuario autenticado.
- Pre: usuario autenticado, tiene `AdminUser` vinculado (o se crea en
  el primer GET).
- Flujo: GET carga datos; PATCH guarda; el cambio queda registrado
  en `audit_log`.

### 2.2 Modelo backend

```python
# apps/config/models.py
class AdminProfile(models.Model):
    """
    Datos de perfil visibles/editables por el propio usuario.
    Separado de AdminUser (que es la "cuenta institucional").
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField('users.User', on_delete=models.CASCADE,
                                related_name='profile')
    full_name = models.CharField(max_length=80)
    email = models.EmailField()  # espejo de User.email; re-validado
    specialty = models.CharField(max_length=80, blank=True, default='')
    professional_license = models.CharField(max_length=40, blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='')
    location = models.CharField(max_length=120, blank=True, default='')
    avatar_url = models.URLField(blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = _admin_schema_table('admin_profiles')
        constraints = [
            models.CheckConstraint(
                check=models.Q(full_name__length__gte=3) & models.Q(full_name__length__lte=80),
                name='admin_profiles_name_len',
            ),
        ]
        verbose_name = 'Perfil de usuario'

    def clean(self):
        if self.full_name:
            self.full_name = _validate_full_name(self.full_name)
        if self.email:
            self.email = _normalize_email(self.email)

    def __str__(self):
        return f'Perfil<{self.user.email}>'

auditlog.register(AdminProfile,
                  include_fields=['full_name', 'email', 'specialty',
                                  'professional_license', 'phone', 'location'])
```

**Decisión:** `specialty`, `professional_license`, `phone`, `location`
salen 1:1 del HTML original (líneas 842–857 de `configuracion.html`).
`avatar_url` se modela como URL por ahora — si en F8 se decide upload
binario, se cambia a `ImageField` con storage S3 (ADR-0005).

### 2.3 Endpoints

| Método | URL | Permiso | Body | Respuesta |
|:---|:---|:---|:---|:---|
| GET | `/api/admin/me/profile/` | `IsAuthenticated` | — | `AdminProfileSerializer` (200) o 404 si no existe |
| PATCH | `/api/admin/me/profile/` | `IsOwnerOrAdmin` | campos editables | `AdminProfileSerializer` (200) |

```python
# apps/config/views.py
class MeProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = AdminProfileSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_object(self):
        profile, _ = AdminProfile.objects.get_or_create(
            user=self.request.user,
            defaults={'full_name': self.request.user.username,
                      'email': self.request.user.email},
        )
        return profile
```

### 2.4 Serializer

```python
class AdminProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminProfile
        fields = ['id', 'full_name', 'email', 'specialty',
                  'professional_license', 'phone', 'location',
                  'avatar_url', 'updated_at']
        read_only_fields = ['id', 'updated_at']

    def validate_full_name(self, v):
        return _validate_full_name(v)
    def validate_email(self, v):
        return _normalize_email(v)
    def validate_phone(self, v):
        # Acepta vacío o E.164 ligero
        if v and not re.match(r'^\+?[\d\s\-()]{6,30}$', v):
            raise serializers.ValidationError('Teléfono inválido')
        return v
```

### 2.5 Componente React

`ProfileSection.tsx` reemplaza `<Placeholder icon="fa-user" title="Perfil
de Usuario" .../>` cuando `active === 'profile'`. Layout 2 columnas
(avatar a la izquierda, form-grid a la derecha), replicando
`configuracion.html` líneas 815–867.

```tsx
// frontend-admin/src/admin/components/ProfileSection.tsx
export function ProfileSection() {
  const { data, isLoading, error, refetch } = useProfile();
  const { mutate, isPending } = useUpdateProfile();
  const [toast, setToast] = useState<Toast | null>(null);

  if (isLoading) return <Skeleton rows={6} />;
  if (error) return <ErrorBanner onRetry={refetch} />;
  if (!data) return null;

  return (
    <ConfigSection title="Perfil de Usuario"
                   subtitle="Actualiza tu información personal y credenciales">
      <div className="profile-grid">
        <ProfileAvatar url={data.avatar_url} />
        <ConfigForm
          schema={profileSchema}
          initial={data}
          fields={['full_name', 'email', 'specialty',
                   'professional_license', 'phone', 'location']}
          onSubmit={(values) => mutate(values, {
            onSuccess: () => setToast({ kind: 'success',
              message: 'Perfil actualizado correctamente' }),
            onError: (e) => setToast({ kind: 'error', message: e.message }),
          })}
          busy={isPending}
        />
      </div>
      {toast && <Toast {...toast} onDismiss={() => setToast(null)} />}
    </ConfigSection>
  );
}
```

### 2.6 Validaciones

- **Cliente (Zod):** `full_name` 3–80 chars, `email` RFC 5322 lite,
  `phone` regex E.164 ligero.
- **Servidor (DRF):** mismas reglas + unicidad de email
  case-insensitive (mismo patrón que `apps/users/serializers.py:41`).

### 2.7 Tests mínimos

- `test_profile.py`:
  - `test_get_creates_profile_if_missing` (idempotente)
  - `test_patch_updates_fields_and_writes_audit`
  - `test_patch_validates_full_name_length`
  - `test_other_user_cannot_patch_my_profile` (403)
  - `test_admin_can_patch_any_profile`
- `ProfileSection.spec.tsx` (Vitest + MSW):
  - renderiza skeleton en loading
  - muestra error y reintenta con `ErrorBanner`
  - envía form y muestra toast de éxito
  - muestra error de validación por campo

---

## 3. P2 — Sección Seguridad (`security-tab`)

### 3.1 Caso de uso (FSD)

**FSD-UC-CONF-002 — Cambiar contraseña y gestionar 2FA.**
- Actor: usuario autenticado.
- Subflujos:
  - 3a. Cambiar contraseña (actual + nueva + confirmar).
  - 3b. Activar/desactivar 2FA.

### 3.2 Cambios al modelo `User` (apps/users)

```python
# apps/users/models.py — añadir a User
class User(AbstractUser):
    # ... (existente) ...
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True, default='')
    password_changed_at = models.DateTimeField(null=True, blank=True)
```

**Decisión:** `two_factor_secret` se almacena **hasheado** (no en claro)
siguiendo TOTP RFC 6238. El endpoint de toggle genera el secret
server-side; el cliente solo ve un QR (base64) durante el setup.

### 3.3 Modelo nuevo: `PasswordHistory`

```python
class PasswordHistory(models.Model):
    """Historial de hashes de contraseña para forzar no-reutilización."""
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE,
                              related_name='password_history')
    password_hash = models.CharField(max_length=128)  # hash Django pbkdf2
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = _admin_schema_table('admin_password_history')
        indexes = [models.Index(fields=['user', '-changed_at'])]
        ordering = ['-changed_at']
```

**Regla:** el servicio `rotate_password` rechaza una nueva contraseña
si su hash coincide con cualquiera de las últimas 5 entradas
(`PasswordHistory.objects.filter(user=u).order_by('-changed_at')[:5]`).
Esto evita el patrón "alterno entre 2 contraseñas".

### 3.4 Endpoints

| Método | URL | Permiso | Body | Respuesta |
|:---|:---|:---|:---|:---|
| POST | `/api/admin/me/password/` | `IsAuthenticated` | `{current, new, confirm}` | 204 (no body) |
| POST | `/api/admin/me/2fa/setup/` | `IsAuthenticated` | — | `{secret, qr_code_b64}` |
| POST | `/api/admin/me/2fa/toggle/` | `IsAuthenticated` | `{enabled, code}` | `{enabled, two_factor_enabled}` |

**Lógica de `toggle`:** para **activar** 2FA el cliente debe enviar un
código TOTP válido (`code`) que coincida con el `secret` previamente
generado por `/setup/`. Para **desactivar**, basta con `enabled:false`
y `code` válido (protección contra desactivación por sesión robada).

### 3.5 Servicio

```python
# apps/config/services.py
def rotate_password(user: 'User', current: str, new: str, confirm: str) -> None:
    if new != confirm:
        raise ValidationError({'confirm': 'No coincide con la nueva contraseña'})
    if not user.check_password(current):
        raise ValidationError({'current': 'Contraseña actual incorrecta'})
    if len(new) < 12 or not re.search(r'[A-Z]', new) or not re.search(r'[0-9]', new):
        raise ValidationError({'new': 'Mínimo 12 chars, 1 mayúscula, 1 dígito'})
    recent = PasswordHistory.objects.filter(user=user).order_by('-changed_at')[:5]
    for h in recent:
        if check_password(new, h.password_hash):
            raise ValidationError({'new': 'No reutilice contraseñas recientes'})
    user.set_password(new)
    user.password_changed_at = timezone.now()
    user.save(update_fields=['password', 'password_changed_at'])
    PasswordHistory.objects.create(user=user, password_hash=user.password)
```

### 3.6 Componente React

`SecuritySection.tsx` replica el layout de `configuracion.html`
líneas 868–911: form de contraseña + bloque "Verificación en dos
pasos (2FA)" con toggle. Usa `react-simple-totp` (≤2 KB) para el input
de código de 6 dígitos, sin librería pesada tipo `otplib`.

### 3.7 Tests mínimos

- `test_security.py`:
  - `test_password_too_short_rejected` (RN-12 implícito)
  - `test_password_must_differ_from_last_5`
  - `test_password_mismatch_confirm`
  - `test_2fa_toggle_requires_valid_code`
  - `test_2fa_disable_requires_code`
  - `test_2fa_secret_is_hashed_not_plain`
- `SecuritySection.spec.tsx`: form, toggle, mensajes de error.

---

## 4. P3 — Sección Modelos IA (`modelos-tab`)

### 4.1 Caso de uso (FSD)

**FSD-UC-CONF-003 — Configurar parámetros del modelo IA y consultar métricas.**
- Actor: solo rol `admin` (ADR-0011).
- Subflujos:
  - 4a. Ver modelos disponibles (cards de U-Net + EfficientNet-B3).
  - 4b. Ajustar `umbral_confianza_minima` y `modo_analisis`.
  - 4c. Ver métricas de precisión (tabla histórica).
  - 4d. Ver rendimiento del sistema (latencia p50/p95/p99).

### 4.2 Modelo `ModelConfig`

```python
class ModelConfig(models.Model):
    """Una sola fila activa por institución (singleton lógico)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_active = models.BooleanField(default=True)
    # U-Net (segmentación)
    unet_version = models.CharField(max_length=40, default='u-net-v2.1')
    unet_enabled = models.BooleanField(default=True)
    # EfficientNet-B3 (clasificación)
    classifier_version = models.CharField(max_length=40, default='efficientnet-b3-v1.4')
    classifier_enabled = models.BooleanField(default=True)
    # Parámetros ajustables (ADR-0006 semaforización)
    confidence_threshold = models.DecimalField(max_digits=4, decimal_places=3,
                                                default=Decimal('0.850'))
    detection_sensitivity = models.DecimalField(max_digits=4, decimal_places=3,
                                                 default=Decimal('0.500'))
    # Modo de análisis: 'fast' | 'balanced' | 'accurate'
    analysis_mode = models.CharField(max_length=16, default='balanced')
    # Logging
    log_level = models.CharField(max_length=10, default='INFO')
    updated_at = models.ModelTimeField(auto_now=True)
    updated_by = models.ForeignKey('users.User', on_delete=models.SET_NULL,
                                    null=True, related_name='model_configs')

    class Meta:
        db_table = _admin_schema_table('admin_model_config')
        constraints = [
            models.CheckConstraint(
                check=models.Q(confidence_threshold__gte=0) &
                      models.Q(confidence_threshold__lte=1),
                name='admin_model_config_confidence_0_1',
            ),
            models.CheckConstraint(
                check=models.Q(analysis_mode__in=['fast', 'balanced', 'accurate']),
                name='admin_model_config_mode_valid',
            ),
            # Singleton: máximo 1 fila activa
            models.UniqueConstraint(
                fields=['is_active'],
                condition=models.Q(is_active=True),
                name='admin_model_config_single_active',
            ),
        ]
```

**Regla crítica:** `confidence_threshold` por debajo de **0.85** activa
un **warning de cumplimiento**: el sistema operativo clínico no debe
operar por debajo de ese umbral (RN-02). El endpoint PATCH acepta el
valor pero la respuesta incluye `compliance_warning: true` si
`confidence_threshold < 0.85`. La UI muestra un banner amarillo.

### 4.3 Modelo `ModelMetric`

```python
class ModelMetric(models.Model):
    """Snapshots append-only de precisión/rendimiento. Append-Only por RN-05."""
    id = models.BigAutoField(primary_key=True)
    measured_at = models.DateTimeField(db_index=True)
    precision_overall = models.DecimalField(max_digits=5, decimal_places=4)
    precision_per_class = models.JSONField(default=dict)  # {1: 0.92, 2: 0.88, ...}
    recall_overall = models.DecimalField(max_digits=5, decimal_places=4)
    f1_overall = models.DecimalField(max_digits=5, decimal_places=4)
    latency_p50_ms = models.IntegerField()
    latency_p95_ms = models.IntegerField()
    latency_p99_ms = models.IntegerField()
    samples_evaluated = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = _admin_schema_table('admin_model_metrics')
        ordering = ['-measured_at']
        indexes = [models.Index(fields=['-measured_at'])]
```

**Append-Only por diseño (RN-05):** no se expone `PATCH` ni `DELETE` en
el viewset; solo `GET` con `?days=N`.

### 4.4 Endpoints

| Método | URL | Permiso | Query | Respuesta |
|:---|:---|:---|:---|:---|
| GET | `/api/admin/models/active/` | `IsAdminRole` | — | `ModelConfigSerializer` |
| PATCH | `/api/admin/models/active/` | `IsAdminRole` (mutación) | — | `ModelConfigSerializer` con `compliance_warning` si aplica |
| GET | `/api/admin/models/metrics/?days=30` | `IsAdminRole` | `days` (default 30, max 365) | `[ModelMetricSerializer]` |
| GET | `/api/admin/models/metrics/latest/` | `IsAdminRole` | — | último `ModelMetricSerializer` |
| POST | `/api/admin/models/metrics/` | `IsAdminRole` (solo el pipeline de entrenamiento escribe) | snapshot | `ModelMetricSerializer` (append-only) |

### 4.5 Serializer con `compliance_warning`

```python
class ModelConfigSerializer(serializers.ModelSerializer):
    compliance_warning = serializers.SerializerMethodField()

    class Meta:
        model = ModelConfig
        fields = ['id', 'is_active', 'unet_version', 'unet_enabled',
                  'classifier_version', 'classifier_enabled',
                  'confidence_threshold', 'detection_sensitivity',
                  'analysis_mode', 'log_level', 'updated_at',
                  'updated_by', 'compliance_warning']
        read_only_fields = ['id', 'updated_at', 'updated_by',
                            'compliance_warning']

    def get_compliance_warning(self, obj) -> bool:
        return obj.confidence_threshold < Decimal('0.850')

    def validate_confidence_threshold(self, v):
        if not (Decimal('0') <= v <= Decimal('1')):
            raise serializers.ValidationError('Debe estar entre 0 y 1')
        return v
```

### 4.6 Componente React

`ModelsSection.tsx` replica 5 form-sections del HTML original
(líneas 914–1076):

1. **MODELOS DISPONIBLES** (cards con icono + versión + estado on/off).
2. **PARÁMETROS DE CLASIFICACIÓN** (sliders con `confidence_threshold`,
   `detection_sensitivity`; selects con `analysis_mode`, `log_level`).
3. **MÉTRICAS DE PRECISIÓN** (tabla histórica + sparkline — sin lib de
   charting: SVG inline con ~30 LOC).
4. **ENTRENAMIENTO Y VALIDACIÓN** (placeholder con CTA "Iniciar
   reentrenamiento" — disabled en MVP, no entra en este DD).
5. **RENDIMIENTO DEL SISTEMA** (latencias p50/p95/p99 del último
   `ModelMetric`).

El banner de cumplimiento aparece cuando `compliance_warning` es true:
```tsx
{compliance_warning && (
  <div className="biomed-warning-banner" role="alert">
    <i className="fas fa-exclamation-triangle" /> El umbral de confianza
    está por debajo de 0.85 (RN-02). El sistema seguirá operando pero los
    reportes requerirán validación manual adicional.
  </div>
)}
```

### 4.7 Tests mínimos

- `test_models_config.py`:
  - `test_singleton_constraint_prevents_two_active`
  - `test_confidence_below_0_85_sets_compliance_warning`
  - `test_patch_requires_admin_role`
  - `test_metrics_endpoint_filters_by_days`
  - `test_metrics_append_only_no_patch_no_delete`
- `ModelsSection.spec.tsx`: warning visible, sliders, sparkline render.

---

## 5. P4 — Sección Notificaciones (`notifications-tab`)

### 5.1 Caso de uso

**FSD-UC-CONF-004 — Configurar preferencias de notificación.**
- Actor: usuario autenticado.
- Canales: email, in-app.
- Categorías: revisión pendiente, validación supervisor, errores sistema,
  reentrenamiento completado.

### 5.2 Modelo

```python
class NotificationPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField('users.User', on_delete=models.CASCADE,
                                related_name='notification_prefs')
    # Matriz canal × categoría
    email_review_pending = models.BooleanField(default=True)
    email_supervisor_validation = models.BooleanField(default=True)
    email_system_errors = models.BooleanField(default=True)
    email_training_completed = models.BooleanField(default=False)
    inapp_review_pending = models.BooleanField(default=True)
    inapp_supervisor_validation = models.BooleanField(default=True)
    inapp_system_errors = models.BooleanField(default=True)
    inapp_training_completed = models.BooleanField(default=True)
    # Quiet hours (RN-07: no notificar fuera de horario)
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(default='20:00')
    quiet_hours_end = models.TimeField(default='07:00')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = _admin_schema_table('admin_notification_prefs')
```

### 5.3 Endpoints

| Método | URL | Permiso | Body | Respuesta |
|:---|:---|:---|:---|:---|
| GET | `/api/admin/me/notifications/` | `IsAuthenticated` | — | `NotificationPreferenceSerializer` |
| PATCH | `/api/admin/me/notifications/` | `IsOwnerOrAdmin` | campos booleanos | `NotificationPreferenceSerializer` |

### 5.4 Componente React

`NotificationsSection.tsx` replica la matriz del HTML (líneas 1079–1109):
4 filas de categorías × 2 columnas de canales con checkboxes, más un
bloque "Horario silencioso" con 2 time pickers.

### 5.5 Tests

- `test_notifications.py`: get_or_create idempotente, PATCH parcial,
  quiet_hours validados.
- `NotificationsSection.spec.tsx`: render de matriz, time pickers.

---

## 6. P5 — Sección Integraciones (`integrations-tab`)

### 6.1 Caso de uso

**FSD-UC-CONF-005 — Configurar integraciones externas (HIS / LIS / API).**
- Actor: solo rol `admin`.
- Subflujos: alta, edición, prueba de conexión (`POST /test/`),
  desactivación (no borrado físico por trazabilidad).

### 6.2 Modelo

```python
class Integration(models.Model):
    SYSTEM_CHOICES = [
        ('HIS', 'Sistema Hospitalario (HIS)'),
        ('LIS', 'Sistema de Laboratorio (LIS)'),
        ('PACS', 'PACS de Imagen'),
        ('API_CUSTOM', 'API personalizada'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    system = models.CharField(max_length=20, choices=SYSTEM_CHOICES)
    name = models.CharField(max_length=80)
    base_url = models.URLField()
    # Credenciales: se almacenan cifradas con Fernet (django-cryptography)
    # o KMS en producción. Este DD usa Fernet (más simple) y documenta
    # el upgrade path a KMS en ADR-0015 si se decide.
    api_key_encrypted = models.BinaryField(blank=True, null=True)
    username_encrypted = models.BinaryField(blank=True, null=True)
    password_encrypted = models.BinaryField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_test_at = models.DateTimeField(null=True, blank=True)
    last_test_status = models.CharField(max_length=20, blank=True, default='')
    last_test_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = _admin_schema_table('admin_integrations')
        indexes = [models.Index(fields=['system', 'is_active'])]
```

**Decisión de cifrado:** `api_key_encrypted` y compañía se cifran con
**Fernet (AES-128-CBC + HMAC-SHA256)** usando
`django-cryptography`'s `encrypt()` decorator. La `FIELD_ENCRYPTION_KEY`
se obtiene de env var; rotación documentada en
`docs/adr/0015-fernet-rotation.md` (a redactar si el equipo lo aprueba;
no se incluye en este DD por scope).

### 6.3 Endpoints

| Método | URL | Permiso | Body | Respuesta |
|:---|:---|:---|:---|:---|
| GET | `/api/admin/integrations/` | `IsAdminRole` | — | `[IntegrationSerializer]` |
| POST | `/api/admin/integrations/` | `IsAdminRole` | `IntegrationCreateSerializer` | `IntegrationSerializer` (201) |
| PATCH | `/api/admin/integrations/{id}/` | `IsAdminRole` | parcial | `IntegrationSerializer` |
| POST | `/api/admin/integrations/{id}/test/` | `IsAdminRole` | — | `{status, message, latency_ms}` |

**Lógica de `test/`:**
1. Descifra credenciales en memoria (nunca en log).
2. Hace `GET {base_url}/health` con timeout 5s.
3. Status 2xx → `{status: 'ok', latency_ms: 42}`.
4. Status !=2xx o timeout → `{status: 'fail', message: '...', latency_ms: 5000}`.
5. Persiste `last_test_*` en la fila.

```python
# apps/config/services.py
def test_integration_connection(integration: Integration) -> dict:
    started = time.monotonic()
    try:
        headers = {}
        if integration.api_key_encrypted:
            headers['Authorization'] = f'Bearer {decrypt(integration.api_key_encrypted).decode()}'
        resp = requests.get(f'{integration.base_url}/health',
                            headers=headers, timeout=5)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        integration.last_test_at = timezone.now()
        integration.last_test_status = 'ok' if resp.ok else 'fail'
        integration.last_test_message = resp.text[:500]
        integration.save(update_fields=['last_test_at', 'last_test_status',
                                       'last_test_message', 'updated_at'])
        return {'status': integration.last_test_status,
                'message': integration.last_test_message,
                'latency_ms': elapsed_ms}
    except (requests.RequestException, ValueError) as e:
        integration.last_test_status = 'fail'
        integration.last_test_message = str(e)[:500]
        integration.save(update_fields=['last_test_at', 'last_test_status',
                                       'last_test_message', 'updated_at'])
        return {'status': 'fail', 'message': str(e)[:500], 'latency_ms': 5000}
```

### 6.4 Componente React

`IntegrationsSection.tsx` replica `configuracion.html` líneas 1110–1146:
lista de cards (una por integración con badge de estado del último
`test`), botón "Probar conexión" en cada card, botón "Agregar
integración" arriba a la derecha que abre un modal.

El modal **nunca muestra la API key en claro** después de creada:
muestra `••••••••` y un botón "Rotar" que abre un sub-modal de
generación.

### 6.5 Tests

- `test_integrations.py`:
  - `test_credentials_encrypted_at_rest` (lee la fila directo, verifica
    que el campo binario no contiene el plaintext)
  - `test_test_endpoint_makes_real_http_call` (mockea `requests.get`,
    verifica status/latency persistidos)
  - `test_test_endpoint_handles_timeout`
  - `test_non_admin_cannot_list_or_create`
  - `test_api_key_not_returned_in_get_after_creation`
- `IntegrationsSection.spec.tsx`: render de cards, modal, botón test.

---

## 7. P6 — Sección Apariencia (`appearance-tab`)

### 7.1 Caso de uso

**FSD-UC-CONF-006 — Configurar tema, densidad e idioma.**
- Actor: usuario autenticado (preferencias propias).

### 7.2 Modelo

```python
class AppearancePreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField('users.User', on_delete=models.CASCADE,
                                related_name='appearance_prefs')
    THEME_CHOICES = [('light', 'Claro'), ('dark', 'Oscuro'),
                     ('auto', 'Automático (sistema)')]
    DENSITY_CHOICES = [('compact', 'Compacto'), ('comfortable', 'Cómodo'),
                        ('spacious', 'Espacioso')]
    LANG_CHOICES = [('es', 'Español'), ('en', 'English'),
                    ('pt', 'Português')]
    theme = models.CharField(max_length=8, choices=THEME_CHOICES, default='light')
    density = models.CharField(max_length=12, choices=DENSITY_CHOICES,
                                default='comfortable')
    language = models.CharField(max_length=5, choices=LANG_CHOICES, default='es')
    font_size = models.CharField(max_length=4,
                                  choices=[('sm', 'Pequeño'),
                                           ('md', 'Mediano'),
                                           ('lg', 'Grande')],
                                  default='md')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = _admin_schema_table('admin_appearance_prefs')
```

### 7.3 Endpoints

| Método | URL | Permiso | Body | Respuesta |
|:---|:---|:---|:---|:---|
| GET | `/api/admin/me/appearance/` | `IsAuthenticated` | — | `AppearancePreferenceSerializer` |
| PATCH | `/api/admin/me/appearance/` | `IsOwnerOrAdmin` | campos | `AppearancePreferenceSerializer` |

### 7.4 Aplicación en cliente

`SessionProvider` ya carga la apariencia al montar y la aplica como
`data-theme` en `<html>` y `data-density` en `<body>`. El cambio
inmediato (sin reload) se hace con:

```tsx
function applyAppearance(prefs: AppearancePreference) {
  document.documentElement.dataset.theme = prefs.theme;
  document.body.dataset.density = prefs.density;
  document.documentElement.lang = prefs.language;
}
```

### 7.5 Tests

- `test_appearance.py`: choices válidos, get_or_create, PATCH aplica en
  cliente (probado con jsdom en el spec).
- `AppearanceSection.spec.tsx`: selectores, aplicación inmediata.

---

## 8. P7 — Shell interno: `ConfigShell` + `ConfigContent`

### 8.1 Propósito

Extraer el sidebar interno de la pestaña "Configuración del Sistema"
(los 7 iconos pequeños en `configuracion.html` líneas 745–795) a un
componente reutilizable. Hoy el shell de la app solo tiene sidebar
externo (`BiomedSidebar`); al hacer click en "Configuración" se
muestra `<Placeholder/>`. Con P7, el click en "Configuración" muestra
un nuevo sidebar interno con las 6 secciones + "Usuarios".

### 8.2 Layout

```
┌─────────────────────────────────────────────────────────────┐
│ BiomedNavbar (existente)                                    │
├──────────┬──────────────────────────────────────────────────┤
│ Biomed   │ ┌─ConfigShell──┐ ┌─ConfigContent─────────────┐ │
│ Sidebar  │ │ Perfil       │ │ <h2>Configuración ...</h2> │ │
│ (existente│ │ Seguridad    │ │ <XxxSection/>              │ │
│  7 items)│ │ Modelo IA    │ │                            │ │
│          │ │ Notificaciones│ │                            │ │
│          │ │ Integraciones │ │                            │ │
│          │ │ Visualización │ │                            │ │
│          │ └──────────────┘ └────────────────────────────┘ │
└──────────┴──────────────────────────────────────────────────┘
```

### 8.3 Componentes

```tsx
// ConfigShell.tsx
type ConfigSectionId = 'profile' | 'security' | 'modelos'
                     | 'notifications' | 'integrations' | 'appearance'
                     | 'users';

const CONFIG_NAV: { id: ConfigSectionId; icon: string; label: string }[] = [
  { id: 'profile',       icon: 'fa-user',          label: 'Perfil' },
  { id: 'security',      icon: 'fa-lock',          label: 'Seguridad' },
  { id: 'modelos',       icon: 'fa-brain',         label: 'Modelo IA' },
  { id: 'notifications', icon: 'fa-bell',          label: 'Notificaciones' },
  { id: 'integrations',  icon: 'fa-plug',          label: 'Integraciones' },
  { id: 'appearance',    icon: 'fa-palette',       label: 'Visualización' },
  { id: 'users',         icon: 'fa-users-cog',     label: 'Usuarios' },
];

export function ConfigShell({ active, onChange, children }: {
  active: ConfigSectionId;
  onChange: (id: ConfigSectionId) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="config-shell">
      <nav className="config-shell__nav" aria-label="Secciones de configuración">
        {CONFIG_NAV.map(item => (
          <button
            key={item.id}
            type="button"
            className={`config-shell__item ${active === item.id ? 'is-active' : ''}`}
            onClick={() => onChange(item.id)}
            aria-current={active === item.id ? 'page' : undefined}
          >
            <i className={`fas ${item.icon}`} aria-hidden="true" />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="config-shell__content">{children}</div>
    </div>
  );
}
```

### 8.4 Cambio en `App.tsx`

`renderSection(active)` (líneas 32–76) se reemplaza por:

```tsx
function renderSection(section: SidebarSection) {
  if (section !== 'config') {
    // (compatibilidad: el sidebar externo 'users' sigue funcionando)
    return /* AdminUsersPanel sin cambios */;
  }
  return <ConfigSectionRouter />;
}

function ConfigSectionRouter() {
  const [configSection, setConfigSection] = useState<ConfigSectionId>('profile');
  return (
    <ConfigShell active={configSection} onChange={setConfigSection}>
      {configSection === 'users'        ? <AdminUsersPanel /> :
       configSection === 'profile'      ? <ProfileSection /> :
       configSection === 'security'     ? <SecuritySection /> :
       configSection === 'modelos'      ? <ModelsSection /> :
       configSection === 'notifications'? <NotificationsSection /> :
       configSection === 'integrations' ? <IntegrationsSection /> :
       configSection === 'appearance'   ? <AppearanceSection /> :
       null}
    </ConfigShell>
  );
}
```

**Decisión:** el `BiomedSidebar` externo sigue teniendo "Configuración"
como un solo item que abre el `ConfigSectionRouter`. El `AdminUsersPanel`
sigue accesible directamente desde el sidebar externo (no se elimina)
**y** desde el sub-sidebar "Usuarios" de Configuración. Esto preserva
F4–F6 sin reescritura.

### 8.5 Tests

- `ConfigShell.spec.tsx`: navegación por teclado (Tab, Enter, Arrow keys),
  estado `aria-current`, onChange invocado con id correcto.
- `ConfigSectionRouter.spec.tsx`: integración shallow, cada id mapea
  al componente correcto.

---

## 9. P8 — Banner de migración `localStorage` → backend

### 9.1 Detección

```typescript
// frontend-admin/src/admin/state/localStoragePrefs.ts
type LegacyPrefs = {
  profile?: Partial<AdminProfile>;
  notifications?: Partial<NotificationPreference>;
  appearance?: Partial<AppearancePreference>;
};

const LEGACY_KEYS = ['biomed.config.profile', 'biomed.config.notifications',
                      'biomed.config.appearance'];

export function readLegacyPrefs(): LegacyPrefs {
  const out: LegacyPrefs = {};
  for (const k of LEGACY_KEYS) {
    const raw = localStorage.getItem(k);
    if (raw) try { out[k.split('.').pop() as keyof LegacyPrefs] = JSON.parse(raw); } catch {}
  }
  return out;
}

export function clearLegacyPrefs(): void {
  for (const k of LEGACY_KEYS) localStorage.removeItem(k);
}
```

### 9.2 Componente

`LocalStorageMigrationBanner.tsx` aparece en la parte superior del
`ConfigSection` cuando `readLegacyPrefs()` retorna no-vacío. Ofrece
dos acciones:

- **"Migrar al servidor"** → 3 PATCH en paralelo (`/me/profile/`,
  `/me/notifications/`, `/me/appearance/`) con los valores legacy.
  Al éxito, `clearLegacyPrefs()`.
- **"Descartar"** → `clearLegacyPrefs()` directo.

El banner se persiste como dismissed en `localStorage` con key
`biomed.migration.dismissed.${userId}` para no reaparecer.

### 9.3 Tests

- `localStoragePrefs.spec.ts`: lectura, parsing tolerante a JSON
  corrupto, idempotencia de `clear`.
- `LocalStorageMigrationBanner.spec.tsx`: aparece/no aparece, ambos
  flujos, manejo de error de PATCH.

---

## 10. P9 — Validación E2E manual

### 10.1 Checklist

Para cada sección P1–P6:

- [ ] Login con `admin`/`admin123` (token fresco vía auth_bridge).
- [ ] GET inicial carga datos correctos.
- [ ] PATCH guarda y aparece en `audit_log` (consultable vía
      `http://127.0.0.1:8001/admin/audit/logentry/`).
- [ ] Validación cliente: enviar datos inválidos muestra error
      inline.
- [ ] Validación servidor: con DevTools simulando bypass de validación
      cliente, el servidor rechaza.
- [ ] 403 si usuario no-admin intenta PATCH en sección admin-only.
- [ ] Banner de migración localStorage aparece con datos sembrados y
      desaparece al migrar.

### 10.2 Captura de evidencia

- 1 screenshot por sección (estado inicial + estado con datos).
- 1 log de `audit_log` filtrado por `actor=request.user` y
  `timestamp >= today`.
- Resultado de `npm run test:coverage` con `≥90%` en `apps/config/`
  y en `frontend-admin/src/admin/components/*Section.tsx`.

---

## 11. P10 — Documentación y CHANGELOG

### 11.1 `DD-ADMIN-002` (este documento)

Se publica tal cual; se referencia desde `AGENTS.md` §5 (índice de
ADRs, no — eso es para ADRs; este es un DD) y desde `docs/PROMPT_MAPPING.md`
como input del prompt de implementación P1–P6.

### 11.2 `CHANGELOG.md` (crear)

Nuevo `docs/CHANGELOG.md` siguiendo [Keep a Changelog 1.1](https://keepachangelog.com):

```markdown
# Changelog

## [Unreleased]

### Added
- ADR-0014 / DD-ADMIN-002: Panel Configuración portado a React+backend
  real. 6 secciones nuevas (Perfil, Seguridad, Modelo IA, Notificaciones,
  Integraciones, Apariencia) + shell interno `ConfigShell`. Cobertura
  RN-09 ≥90% por sección.

### Changed
- `App.tsx` `renderSection` ahora enruta a `ConfigSectionRouter` en
  lugar de `<Placeholder/>` para `section === 'config'`.
```

### 11.3 Estado nuevo de `adminConfigStore`

Si la lógica de fetch crece más allá de 6 useState locales, se introduce
`adminConfigStore.tsx` siguiendo el patrón de `adminUsersStore.tsx`
(reducer + acciones tipadas). **Hoy no se introduce** — se difiere
hasta P3, donde se ve si el estado cruzado entre Modelos y
Notificaciones justifica una store global.

---

## 12. Matriz de esfuerzo consolidada

| Fase | Alcance | Esfuerzo | Dependencia |
|:-:|:---|:---:|:---|
| **P0** | Skeleton `apps/config` + URL routing | 2h | — |
| **P1** | Perfil | 6h | P0 |
| **P2** | Seguridad | 8h | P0 |
| **P3** | Modelos IA | 10h | P0 |
| **P4** | Notificaciones | 5h | P0 |
| **P5** | Integraciones | 8h | P0 |
| **P6** | Apariencia | 4h | P0 |
| **P7** | `ConfigShell` + router | 4h | P1–P6 |
| **P8** | Banner migración localStorage | 2h | P1, P4, P6 |
| **P9** | Validación E2E manual | 2h | P1–P8 |
| **P10** | Docs + CHANGELOG | 2h | P9 |
| **Total** | | **53h** | |

---

## 13. Riesgos abiertos

| # | Riesgo | Mitigación |
|:-:|:---|:---|
| 1 | `ModelConfig` con threshold <0.85 se permite pero la UI debe avisar (RN-02) | `compliance_warning` en serializer + banner en `ModelsSection` |
| 2 | Credenciales HIS/LIS encriptadas con Fernet: rotación de clave requiere re-encriptar todas las filas | Documentar `FIELD_ENCRYPTION_KEY` rotation procedure en `docs/adr/0015-fernet-rotation.md` (futuro) |
| 3 | localStorage puede contener JSON corrupto | `try/catch` en `readLegacyPrefs`; descartar silenciosamente |
| 4 | 2FA con TOTP requiere lib cliente liviana | `react-simple-totp` (≤2 KB) o input custom de 6 dígitos |
| 5 | Cobertura RN-09 podría caer al portar 6 secciones a la vez | Gate por fase; no mergea si <90% |
| 6 | Modelos P3 con `is_active=True` constraint: si dos requests crean a la vez, race condition | Migración usa `get_or_create` + `select_for_update` |
| 7 | El clínico no debe leer `ModelConfig` directamente (debe pasar por el microservicio de inferencia, ADR-0007) | No exponer `ModelConfig` en ninguna API pública FastAPI; solo desde `apps/config` interno |

---

## 14. Trazabilidad

- **Sube a:** BRD §3.2 → FSD-UC-ADMIN-001 §5 → DD-ADMIN-001 → ADR-0011
  → ADR-0013 → **ADR-0014** → **este DD-ADMIN-002**.
- **Genera:** `PR-IMPL-ADMIN-004` a `PR-IMPL-ADMIN-009` (uno por fase
  P1–P6), rama `feature/admin-config-panel`.
- **Impacta:**
  - `AGENTS.md` §3 (apunte sobre `apps/config` y las 6 secciones, ya hecho en ADR-0014).
  - `docs/DTI.md` §21 (fila ADR-0014 ya insertada).
  - `FSD-UC-ADMIN-001` §5 (nuevos casos UC-CONF-001 a UC-CONF-006).
  - `docs/PROMPT_MAPPING.md` (nuevos prompts P1–P6).
  - `docs/CHANGELOG.md` (nuevo, entrada Unreleased).
  - `docs/adr/0015-fernet-rotation.md` (futuro, si se decide abordar).

---

## 15. Notas

- Este DD **no** autoriza la implementación; eso ocurre en P0–P10 con
  PRs pequeñas. Cualquier desviación de este diseño se discute en
  retrospectiva y se documenta como ADR-0015+ o como entrada en
  CHANGELOG.
- El orden de las fases (P1–P6) sigue complejidad creciente + valor
  para demo. P5 (Integraciones) es la más costosa y se podría diferir
  si la prioridad es mostrar demo rápido.
- El banner de migración localStorage (P8) **es one-shot** por usuario.
  Si el usuario lo descarta, no vuelve a aparecer.
- `apps/config` no se acopla al bounded context clínico. Si en el
  futuro el microservicio de inferencia (ADR-0007) necesita leer
  `ModelConfig`, el acoplamiento se aborda en un ADR-0015 dedicado
  con su propio análisis de riesgo (latencia, eventual consistency,
  cache invalidation).
