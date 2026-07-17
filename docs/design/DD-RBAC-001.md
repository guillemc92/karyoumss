---
id: DD-RBAC-001
titulo: "RBAC jerárquico (TipoObjeto→Objeto→Opción, Grupos + excepción individual) en backend-clinic — port fiel del módulo Security/ real"
producto: "BIOMED UMSS — Intelligent Karyotyping Platform"
grupo: "G04"
fsd_uc:
  - "FSD-UC-001"
  - "FSD-UC-CRUD-MUESTRA-001"
prd_refs:
  - "PRD-US-001"
adrs:
  - "ADR-0015"  # Stack Django+React para Muestras
  - "ADR-0018"  # Permisos por rol (is_staff/is_superuser) — extendido, no derogado
  - "ADR-0019"  # RBAC jerárquico (este DD)
prompts:
  - "PM-RBAC-001"  # a crear en PROMPT_MAPPING.md tras implementar
specs:
  - "SPEC-008-crud-muestra-react.md"
release: "release/2.0.0"
status: proposed
fecha: "2026-07-17"
autores:
  - "Ing. Guillermo Mamani Chambi"
---

# Design Doc `DD-RBAC-001` — RBAC jerárquico portado del módulo Security/ real

## 0. Relación con `DD-PERMISOS-ROL-001` y ADR-0018

Este DD **extiende** `DD-PERMISOS-ROL-001.md` (ADR-0018), no lo
reemplaza. El scoping "propias vs. todas" en `get_queryset()` /
`IsOwnerOrStaff` no cambia — sigue siendo responsabilidad de la vista,
no de este RBAC. Lo que este DD agrega es: **¿puede este usuario
intentar esta acción en absoluto?**, resuelto por una jerarquía
`TipoObjeto → Objeto → Opción` con permisos por `Grupo` y excepción
por usuario individual, portada del código C# real (`Security/`) que
el arquitecto compartió el 2026-07-17.

**Nota de proceso:** este DD reemplaza una primera versión (mismo
día) que asumía un modelo de 3 niveles de acceso resuelto por "máximo
privilegio" — diseñada solo a partir de `script.sql` (esquema
MetaClass) sin haber visto el código real. Al leer `Security/*.cs`
se confirmó que el modelo real es binario y se resuelve por
deny-overrides + excepción individual absoluta. Ver ADR-0019
"Historial de revisión" para el detalle completo de qué cambió y por
qué. Esta reescritura es más fiel al sistema portado.

## 1. Trazabilidad SDD

```
Security/*.cs (frmUsuarios, frmGrupos, frmObjetos, frmOpciones, frmTiposObjeto, frmLogin)
  + sqlaserca.sql (seg_tipos_objetos, seg_objetos, seg_opciones, seg_grupos,
    seg_privilegios_grupo, seg_usuarios_grupos, seg_privilegios_individuales)
    → decisión del arquitecto 2026-07-17 (portar RBAC granular real)
      → ADR-0019 (proposed, reescrito tras leer el código)
        → este DD (arquitectura de componentes + migración de datos)
          → código (models_rbac.py, permissions.py, migrations/, admin.py)
            → tests (tiene_opcion() con todas las combinaciones, seed, fail-closed)
              → PROMPT_MAPPING (PM-RBAC-001)
```

## 2. Arquitectura de permisos

```
┌──────────────────────┐
│  TipoObjeto            │  "Formulario", "Menú", etc. (seg_tipos_objetos)
└──────────────────────┘
            │ 1:N
            ▼
┌──────────────────────┐
│  Objeto                 │  "Muestras" (seg_objetos)
└──────────────────────┘
            │ 1:N
            ▼
┌──────────────────────┐
│  Opcion                 │  code='sample.delete' (seg_opciones)
└──────────────────────┘
            │ 1:N                                    │ 1:N
            ▼                                          ▼
┌──────────────────────┐                    ┌──────────────────────────┐
│  PrivilegioGrupo         │                    │  PrivilegioIndividual        │
│  (grupo, opcion, permitido)│                  │  (usuario, opcion, permitido)│
│  seg_privilegios_grupo   │                    │  seg_privilegios_individuales│
└──────────────────────┘                    └──────────────────────────┘
            ▲                                          ▲
            │ N:1                                      │ N:1
┌──────────────────────┐                    ┌──────────────────────────┐
│  Grupo                   │◄──────N:M─────────│  Usuario (Django User)       │
│  'Analista'/'Supervisor'/│  UsuarioGrupo      │                              │
│  'Admin' (seed inicial)   │  seg_usuarios_grupos│                            │
└──────────────────────┘                    └──────────────────────────┘

                    tiene_opcion(user, 'sample.delete')
                              │
              ┌───────────────┴───────────────┐
              ▼                                ▼
   1. ¿Existe PrivilegioIndividual     2. Si no hay excepción:
      con permitido != None?             combinar TODOS los PrivilegioGrupo
      SÍ → retorna ese valor             de los grupos del usuario:
      (override absoluto)                deny-overrides (basta un False)
                                          sin grupos que definan -> False
```

## 3. Modelos de datos (nuevos, `apps/samples/models_rbac.py`)

### 3.1 `TipoObjeto`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | AutoField (PK) | |
| `nombre` | `CharField(25)` | Ej: "Formulario" |
| `descripcion` | `TextField`, blank | |

### 3.2 `Objeto`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | AutoField (PK) | |
| `tipo` | FK → `TipoObjeto` | `on_delete=CASCADE`, `related_name='objetos'` |
| `nombre` | `CharField(50)` | Ej: "Muestras" |
| `descripcion` | `TextField`, blank | |

### 3.3 `Opcion`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | AutoField (PK) | |
| `objeto` | FK → `Objeto` | `on_delete=CASCADE`, `related_name='opciones'` |
| `codigo` | `CharField(50)`, unique | Estable, referenciado desde código. Ej: `sample.create`, `sample.list`, `sample.view`, `sample.edit`, `sample.delete`, `sample.process` |
| `nombre` | `CharField(50)` | Ej: "Eliminar muestra" |
| `descripcion` | `TextField`, blank | |

Constraint: `UniqueConstraint(['objeto', 'nombre'])` — mismo patrón
que `seg_opciones_uq` (`opc_nom`, `opc_obj_cod`) del esquema real.

### 3.4 `Grupo`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | AutoField (PK) | |
| `nombre` | `CharField(25)`, unique | Seed inicial: `'Analista'`, `'Supervisor'`, `'Admin'` |
| `descripcion` | `TextField`, blank | |

### 3.5 `PrivilegioGrupo`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | AutoField (PK) | |
| `grupo` | FK → `Grupo` | `on_delete=CASCADE` |
| `opcion` | FK → `Opcion` | `on_delete=CASCADE` |
| `permitido` | `BooleanField`, default `False` | Análogo a `plp_val bit` |

Constraint: `UniqueConstraint(['grupo', 'opcion'])`.

### 3.6 `UsuarioGrupo`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | AutoField (PK) | |
| `usuario` | FK → `settings.AUTH_USER_MODEL` | `on_delete=CASCADE`, `related_name='grupos_clinicos'` |
| `grupo` | FK → `Grupo` | `on_delete=CASCADE`, `related_name='usuarios'` |

Constraint: `UniqueConstraint(['usuario', 'grupo'])`. N:M real — un
usuario puede pertenecer a varios grupos simultáneamente.

### 3.7 `PrivilegioIndividual`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | AutoField (PK) | |
| `usuario` | FK → `settings.AUTH_USER_MODEL` | `on_delete=CASCADE`, `related_name='privilegios_individuales'` |
| `opcion` | FK → `Opcion` | `on_delete=CASCADE` |
| `permitido` | `BooleanField(null=True)`, default `None` | `None`=sin excepción (usa grupo), `True`/`False`=override absoluto |

Constraint: `UniqueConstraint(['usuario', 'opcion'])`. Análogo directo
a `seg_privilegios_individuales` (`pri_val bit NULL`).

## 4. Función de resolución (port literal de `nodeValue()`)

```python
# apps/samples/permissions.py

def tiene_opcion(user, opcion_code: str) -> bool:
    opcion = Opcion.objects.filter(codigo=opcion_code).first()
    if opcion is None:
        return False  # fail-closed

    individual = PrivilegioIndividual.objects.filter(usuario=user, opcion=opcion).first()
    if individual is not None and individual.permitido is not None:
        return individual.permitido

    privilegios_grupo = list(
        PrivilegioGrupo.objects.filter(
            opcion=opcion, grupo__usuarios__usuario=user,
        ).values_list('permitido', flat=True)
    )
    if not privilegios_grupo:
        return False
    return all(privilegios_grupo)
```

**Correspondencia con el C# original** (para auditoría/revisión):

| Python | C# (`frmUsuariosEdit.cs`) |
|---|---|
| `individual.permitido is not None: return individual.permitido` | `switch(val_usu) { case "False"/"True": return val_usu; }` |
| `all(privilegios_grupo)` | Consulta SQL de `createArrayGrupos()` con `NOT IN (...WHERE plp_val=0...)` |
| `not privilegios_grupo: return False` | Ausencia de fila → tratado implícitamente como sin acceso en el árbol (nodo sin marcar) |

## 5. Migración de datos (no solo de schema)

**Regla de oro (igual que ADR-0018 y el borrador anterior de este
mismo ADR): el día 1 del despliegue, ningún usuario existente pierde
ni gana acceso.**

### 5.1 Seed de `Opcion` (jerarquía completa)

```python
JERARQUIA = {
    'Formulario': {  # TipoObjeto
        'Muestras': [  # Objeto
            ('sample.create', 'Crear muestra'),
            ('sample.list', 'Listar muestras'),
            ('sample.view', 'Ver detalle de muestra'),
            ('sample.edit', 'Editar muestra'),
            ('sample.delete', 'Eliminar muestra (soft-delete)'),
            ('sample.process', 'Disparar procesamiento IA'),
        ],
    },
}
```

### 5.2 Seed de `Grupo` + `UsuarioGrupo` (reproduce ADR-0018)

```python
def seed_grupos_desde_is_staff(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL)
    Grupo = apps.get_model('samples', 'Grupo')
    UsuarioGrupo = apps.get_model('samples', 'UsuarioGrupo')

    g_analista, _ = Grupo.objects.get_or_create(nombre='Analista')
    g_supervisor, _ = Grupo.objects.get_or_create(nombre='Supervisor')
    g_admin, _ = Grupo.objects.get_or_create(nombre='Admin')

    for user in User.objects.all():
        grupo = g_admin if user.is_superuser else (g_supervisor if user.is_staff else g_analista)
        UsuarioGrupo.objects.get_or_create(usuario=user, grupo=grupo)
```

### 5.3 Seed de `PrivilegioGrupo` (matriz idéntica a ADR-0018 D3)

| Opción (`code`) | Analista | Supervisor | Admin |
|---|:---:|:---:|:---:|
| `sample.create` | ✅ | ✅ | ✅ |
| `sample.list` | ✅ | ✅ | ✅ |
| `sample.view` | ✅ | ✅ | ✅ |
| `sample.edit` | ✅ | ✅ | ✅ |
| `sample.delete` | ❌ | ❌ | ✅ |
| `sample.process` | ✅ | ✅ | ✅ |

**Nota, igual que en el borrador anterior:** ✅ en `sample.list`/
`sample.view`/`sample.edit` para `Analista` **no** implica ver todas
las muestras — el scoping propias/todas sigue en `get_queryset()`/
`IsOwnerOrStaff`, sin cambios.

## 5.4 Auto-asignación de grupo para usuarios nuevos (addendum de implementación)

Al implementar los tests se detectó un gap operativo real: el seed
(§5.2) solo asigna `UsuarioGrupo` a los usuarios que **ya existían**
en el momento de correr la migración. Un usuario creado **después**
(ej. `User.objects.create_user(...)` en producción, o en cualquier
fixture de test) queda sin ningún grupo — y con `tiene_opcion()`
fail-closed (§4), ese usuario no podría hacer absolutamente nada hasta
que un administrador lo asigne manualmente vía Django Admin.

Esto es consistente con el espíritu fail-closed del diseño, pero es
una trampa operativa real: "creé un usuario y no puede ni listar sus
propias muestras" sería un bug reportado con seguridad. Se agrega un
`post_save` signal sobre `User` (registrado en
`SamplesConfig.ready()`) que auto-asigna el grupo `Analista` (el de
menor privilegio, igual criterio que `roles_for_user()` del borrador
anterior — nunca asumir el privilegio más alto por default) la
primera vez que se crea un usuario, si aún no tiene ningún
`UsuarioGrupo`. Un administrador puede reasignar o agregar grupos
después sin restricción — el signal solo actúa en la creación.

```python
# apps/samples/signals.py (nuevo)
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def asignar_grupo_analista_por_defecto(sender, instance, created, **kwargs):
    if not created:
        return
    if UsuarioGrupo.objects.filter(usuario=instance).exists():
        return  # defensivo: no debería ocurrir en post_save de creación, pero evita duplicar
    grupo_analista, _ = Grupo.objects.get_or_create(nombre='Analista')
    UsuarioGrupo.objects.create(usuario=instance, grupo=grupo_analista)
```

## 6. Componentes de código

| Componente | Responsabilidad |
|---|---|
| `models_rbac.py` | 7 modelos: `TipoObjeto`, `Objeto`, `Opcion`, `Grupo`, `PrivilegioGrupo`, `UsuarioGrupo`, `PrivilegioIndividual` |
| `permissions.py::tiene_opcion(user, code)` | Función pura de resolución (port de `nodeValue()`) |
| `permissions.py::HasOpcion` | Permission class DRF parametrizable |
| `views.py` (modificada) | `SampleListCreateView`/`SampleDetailView`/`SampleProcessView` migran de `IsClinicRole`/`IsAdminRole` a `HasOpcion('sample.X')` |
| `admin.py` (nuevo) | `ModelAdmin` para las 7 tablas — permite editar grupos, privilegios y excepciones individuales sin tocar código. Idealmente resaltar (igual que el C# original coloreaba en rojo/azul) cuando una excepción individual difiere del resultado de grupo — a implementar como método de `list_display`/`readonly_fields` con color, o diferir a una mejora visual posterior si el esfuerzo no se justifica en el MVP |
| `migrations/000X_rbac_jerarquico.py` | Schema (7 tablas) + `RunPython` con los 3 seeds de §5 |

## 7. Plan de pruebas (RN-09 ≥90%)

### 7.1 Tests de `tiene_opcion()` (`test_tiene_opcion.py`, nuevo) — el corazón de este DD

| Test | Verifica |
|---|---|
| `test_opcion_inexistente_fail_closed` | `Opcion` sin seed → `False` |
| `test_sin_grupo_sin_privilegio` | Usuario sin grupos → `False` |
| `test_un_grupo_permite` | 1 grupo con `permitido=True` → `True` |
| `test_un_grupo_deniega` | 1 grupo con `permitido=False` → `False` |
| `test_dos_grupos_uno_permite_uno_deniega_gana_denegacion` | Deny-overrides: `[True, False] → all() → False` |
| `test_dos_grupos_ambos_permiten` | `[True, True] → True` |
| `test_excepcion_individual_true_sobre_grupo_false` | Grupo deniega, excepción individual `True` → `True` (override absoluto) |
| `test_excepcion_individual_false_sobre_grupo_true` | Grupo permite, excepción individual `False` → `False` (override absoluto) |
| `test_excepcion_individual_none_usa_grupo` | `permitido=None` explícito → se comporta como sin excepción, usa el resultado de grupo |
| `test_usuario_en_multiples_grupos` | Usuario en `Analista` (deniega `sample.delete`) + `Admin` (permite) → `False` (deny-overrides entre grupos, no gana el privilegio) |

### 7.2 Tests de modelos y seed (`test_rbac_models.py`, nuevo)

| Test | Verifica |
|---|---|
| `test_seed_grupos_reproduce_is_staff` | Tras la migración, cada usuario existente está en el grupo que `is_staff`/`is_superuser` habría indicado |
| `test_seed_idempotente` | Correr el seed dos veces no duplica filas |
| `test_seed_matriz_reproduce_adr0018` | `PrivilegioGrupo` post-seed coincide con la tabla §5.3 |
| `test_unique_constraints` | Los 4 `UniqueConstraint` (objeto+nombre en Opcion, grupo+opcion, usuario+grupo, usuario+opcion individual) se respetan |

### 7.3 Tests de integración (extender vistas existentes)

Re-ejecutar los tests existentes de permisos (ADR-0018 y la sesión de
filtros/process/status) contra las vistas migradas a `HasOpcion` — sin
modificar sus aserciones, confirmando cero regresión observable.

## 8. Riesgos (ver también ADR-0019 §Consecuencias)

| Riesgo | Mitigación |
|---|---|
| Seed no se ejecuta en un ambiente nuevo → todo `False` | Documentar en README; test explícito de fail-closed (§7.1) |
| Confusión sobre por qué un usuario específico no tiene un permiso que su grupo sí da | Documentar la regla (D5/§4) claramente; considerar resaltado visual en `admin.py` (§6), igual que hacía el C# original con colores |
| Migrar las vistas existentes rompe tests de ADR-0018 | Mitigado por §7.3 |
| Confundir `sample.list`/`view`/`edit`=`True` con "ve todas las muestras" | Documentado explícitamente en §5.3 |

## 9. Plan de implementación

| # | Tarea | Estado |
|---|---|---|
| T1 | ADR-0019 (decisión: modelo real jerárquico, deny-overrides + excepción individual) | ✅ |
| T2 | Este DD | ✅ |
| T3 | `models_rbac.py`: 7 modelos | ⏸ pendiente |
| T4 | Migración: schema + 3 seeds (§5.1-5.3) | ⏸ pendiente |
| T5 | `permissions.py`: `tiene_opcion()`, `HasOpcion` | ⏸ pendiente |
| T6 | `admin.py`: `ModelAdmin` para las 7 tablas | ⏸ pendiente |
| T7 | Migrar `views.py` a `HasOpcion` | ⏸ pendiente |
| T8 | Tests §7.1-7.3 (~20 tests nuevos estimados) | ⏸ pendiente |
| T9 | Correr suite completa, confirmar RN-09 ≥90% y cero regresión | ⏸ pendiente |
| T10 | `PROMPT_MAPPING.md` (`PM-RBAC-001`), `docs/DTI.md`, `AGENTS.md` §5 | ⏸ pendiente |
| T11 | Commit | ⏸ pendiente |

## 10. Trazabilidad

- **Sube a:** `Security/*.cs` + `sqlaserca.sql` (código real) → ADR-0019 → este DD.
- **Baja a:** `backend-clinic/apps/samples/{models_rbac,permissions,views,admin}.py`, migración nueva, tests nuevos.
- **Impacta:** `docs/PROMPT_MAPPING.md` (`PM-RBAC-001`), `docs/DTI.md`, `AGENTS.md` §5, `DD-PERMISOS-ROL-001.md` (referenciado, no modificado).

## Notas

- Este DD **no** migra datos reales de una instalación del sistema
  legado — solo porta el *modelo*. Migración de datos reales sigue sin
  decidirse (`project-metaclass-integration-pending`).
- `backend-admin` no se toca (ADR-0019 D1).
- El código fuente `Security/*.cs` referencia clases externas
  (`SQLClass`, `Seguridad`, `App`, `Change`, `Validar`) que no están en
  el repo — este DD no asume nada sobre ellas más allá de lo que su
  uso en los forms revela.
- Rama de trabajo: a decidir — dado el mayor blast radius (7 tablas),
  se recomienda una rama dedicada `feature/rbac-jerarquico` en vez de
  continuar en `feature/clinic-django-stack`.
