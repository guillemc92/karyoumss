---
id: ADR-0019
title: RBAC jerárquico (TipoObjeto→Objeto→Opción, Grupo con deny-overrides + excepción individual) en backend-clinic, portado del módulo Security/ real
date: 2026-07-17
status: proposed
supersedes: ninguno (extiende ADR-0018, no lo deroga)
related: [ADR-0018, ADR-0015, ADR-0017, SPEC-008, reference-metaclass-legacy-schema]
fase: diseño
autor: Ing. Guillermo Mamani Chambi
---

# ADR-0019: RBAC jerárquico portado del módulo Security/ real (TipoObjeto→Objeto→Opción, Grupos + excepción individual)

## Historial de revisión de este documento

Este ADR tuvo un primer borrador (mismo día) basado únicamente en
`script.sql` (esquema MetaClass, tablas `SCAFuncionalidades`/
`SCARoles`/`SCAFuncionalidad_Rol`/`SCAUsuarios_Roles`) y `ayuda.pdf`
(manual de usuario). Ese borrador asumía un modelo de **3 niveles de
acceso** (`TipoAcceso`: sin acceso/solo lectura/total) resuelto por
**máximo privilegio** entre los roles de un usuario.

El arquitecto compartió después el **código fuente C# real** del
módulo de administración de usuarios y permisos (carpeta `Security/`:
`frmUsuarios`, `frmGrupos`, `frmObjetos`, `frmOpciones`,
`frmTiposObjeto`, `frmLogin`, + esquema `sqlaserca.sql`). La lectura de
ese código **invalidó dos supuestos** del borrador inicial:

1. **El modelo real es binario** (`bit`: 0=NO, 1=SI), no de 3 niveles.
   `plp_val`/`pri_val` en `sqlaserca.sql` son `bit`, no un entero
   0/1/2. El "solo lectura" del manual de MetaClass (§2.4.9) pertenece
   a *otro* sistema (el módulo de cariotipo en sí), no al framework de
   seguridad genérico de `Security/` — no deben mezclarse.

2. **La regla de resolución no es "máximo privilegio"**, es
   **deny-overrides entre grupos + excepción individual absoluta**.
   Confirmado leyendo `frmUsuariosEdit.cs::nodeValue()` y
   `createArrayGrupos()`:
   ```csharp
   private string nodeValue(string opc_cod) {
       string val_gru = nodeValueGru(opc_cod);  // resultado combinado de TODOS los grupos del usuario
       string val_usu = nodeValueUsu(opc_cod);  // excepción individual de ESTE usuario
       switch (val_usu) {
           case "Null": return val_gru;   // sin excepción -> usa el resultado de grupo
           case "False":
           case "True": return val_usu;   // la excepción SIEMPRE gana, sea para dar o quitar acceso
       }
       return "Null";
   }
   ```
   Y `createArrayGrupos()` arma el resultado de "TODOS los grupos" con
   una consulta SQL que **excluye** cualquier opción donde *algún*
   grupo del usuario tenga `plp_val=0` — es decir, entre grupos
   múltiples, **la denegación de cualquiera de ellos gana** sobre la
   concesión de los demás.

Este documento reemplaza el D2-D4 del borrador con el modelo real.
Ver la sección "Alternativas evaluadas" para el registro de por qué el
primer borrador se descartó (no se oculta, se documenta el cambio).

## Contexto

El 2026-07-15 el arquitecto compartió `script.sql` (esquema legado de
**MetaClass**, software de cariotipado que este proyecto reemplaza) y
`ayuda.pdf` (manual de usuario 3.0, MICROPTIC S.L. 2013). El
2026-07-17 pidió portar el modelo de permisos granular, y luego
compartió el **código fuente C# real** de ese módulo (carpeta
`Security/` del repo, proyecto WinForms `iibismed`, sin `.csproj` —
es un fragmento de un sistema mayor, probablemente un ERP de
MICROPTIC/terceros donde este framework de seguridad se reutiliza).

### El modelo real portado (confirmado leyendo `Security/*.cs` + `sqlaserca.sql`)

```
seg_tipos_objetos(tio_cod, tio_nom, tio_des)
  -- "Tipos de objetos: formularios, menús, etc." (comentario en el propio esquema)
seg_objetos(obj_cod, obj_tio_cod → tio_cod, obj_nom, obj_des)
  -- una pantalla/form concreto, ej. "Usuarios", "Grupos"
seg_opciones(opc_cod, opc_obj_cod → obj_cod, opc_nom, opc_des)
  -- una acción dentro de ese objeto, ej. "Insertar", "Modificar", "Eliminar", "Ver listado"
  -- UNIQUE(opc_nom, opc_obj_cod)

seg_grupos(gru_cod, gru_nom UNIQUE, gru_des)
seg_privilegios_grupo(plp_gru_cod, plp_opc_cod, plp_val bit)  -- PK compuesta
  -- qué puede hacer cada grupo en cada opción (0=NO, 1=SI)
seg_usuarios_grupos(usg_usu_cod, usg_gru_cod)  -- N:M, un usuario puede estar en varios grupos

seg_privilegios_individuales(pri_usu_cod, pri_opc_cod, pri_val bit NULL)  -- PK compuesta
  -- EXCEPCIÓN por usuario específico: NULL=sin excepción (usa el de grupo),
  -- 0/1=fuerza el valor sin importar qué digan los grupos

seg_usuarios(usu_cod, usu_log, usu_pas [MD5], usu_hab [habilitado],
             usu_cpa [política cambio pwd: 0=libre/1=en próxima sesión/
                      2=no puede cambiar/3=cada N días], usu_cca
             [cuenta caduca sí/no], usu_fcc [fecha caducidad], ...)
seg_session(ses_cod, ses_usu_cod, ses_hos, ses_ini, ses_fin, ses_pcn)
  -- auditoría de inicio/fin de sesión, host y PC
seg_log(log_cod, log_usu_cod, log_ses_cod, log_fec, log_mod, log_tab, log_act, log_sql)
  -- auditoría de sentencias SQL ejecutadas por sesión
```

**Regla de resolución (código real, `frmUsuariosEdit.cs`):**

1. Calcular el resultado combinado de **todos los grupos** del
   usuario: para cada opción, si *algún* grupo la deniega (`plp_val=0`),
   el resultado combinado es `False` — no importa si otro grupo la
   concede. Si ningún grupo la deniega y al menos uno la concede
   (`plp_val=1`), el resultado es `True`. Si ningún grupo tiene fila
   para esa opción, el resultado es `Null` (sin definir).
2. Si el usuario tiene una **excepción individual** (`pri_val` no
   nulo) para esa opción, esa excepción **gana siempre**, sea `True`
   (dar acceso aunque el grupo lo niegue) o `False` (quitar acceso
   aunque el grupo lo conceda).
3. Si no hay excepción individual, se usa el resultado combinado de
   grupos del paso 1.

**Otros hallazgos de seguridad relevantes del código real** (no forman
parte del RBAC en sí, pero informan las Consecuencias de este ADR):

- `Change.ToMD5()` para contraseñas — hash sin salt, hoy considerado
  criptográficamente débil.
- `frmUsuarios.cs::btnBuscar_Click` construye SQL por concatenación
  directa de texto de usuario (`"usu_cod LIKE '%" + txt_search.Text +
  "%'"`) — inyección SQL clásica.
- `frmLogin.cs`: máximo 3 intentos de login antes de **cerrar la
  aplicación completa** (`Application.Exit()`), no solo bloquear al
  usuario.
- `seg_usuarios.usu_cca`/`usu_fcc`: cuentas con fecha de caducidad
  explícita, verificada en cada login.

### Lo que BIOMED tiene hoy (ADR-0018, `backend-clinic`)

```python
def role_for_user(user) -> str:
    if user.is_superuser: return 'admin'
    if user.is_staff: return 'supervisor'
    return 'analista'
```

3 roles fijos, derivados de campos ya existentes de Django
(`is_staff`/`is_superuser`), con permission classes **hardcodeadas por
vista** (`IsClinicRole`, `IsAdminRole`, `IsOwnerOrStaff`). ADR-0018
evaluó y **rechazó explícitamente** un campo `role` nuevo y Django
Groups, por ser "sobre-ingeniería para una jerarquía de 3 niveles
totalmente ordenada" (`analista < supervisor < admin`).

### Por qué esto NO contradice ADR-0018

ADR-0018 rechazó agregar *estructura* para resolver una jerarquía
**ya totalmente ordenada** — ese rechazo sigue siendo correcto y este
ADR no lo revierte. El sistema real de `Security/` resuelve un
problema distinto: **permisos por acción concreta sobre una pantalla
concreta** (`opc_cod`), configurables por grupo y ajustables por
excepción individual — algo que el modelo de 3 roles fijos de
ADR-0018 no puede expresar (hoy, "puede eliminar" es una permission
class hardcodeada en Python, no un dato).

## Decisión

### D1 — Alcance: solo `backend-clinic`, no tocar `backend-admin`

Igual criterio que ADR-0015/0017/0018 (YAGNI, dos bounded contexts
con auth independiente por diseño): este ADR **no** toca
`backend-admin`.

### D2 — Portar la jerarquía completa: `TipoObjeto → Objeto → Opción`

```python
# apps/samples/models_rbac.py

class TipoObjeto(models.Model):
    """Análogo a seg_tipos_objetos. Categoría de objeto: 'Formulario', 'Menú', etc."""
    nombre = models.CharField(max_length=25)
    descripcion = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'clinic_rbac_tipo_objeto'


class Objeto(models.Model):
    """Análogo a seg_objetos. Una pantalla/recurso concreto, ej. 'Muestras'."""
    tipo = models.ForeignKey(TipoObjeto, on_delete=models.CASCADE, related_name='objetos')
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'clinic_rbac_objeto'


class Opcion(models.Model):
    """Análogo a seg_opciones. Una acción dentro de un Objeto, ej. 'sample.delete'."""
    objeto = models.ForeignKey(Objeto, on_delete=models.CASCADE, related_name='opciones')
    codigo = models.CharField(max_length=50, unique=True)  # equivalente estable a opc_cod, referenciado desde código
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'clinic_rbac_opcion'
        constraints = [
            models.UniqueConstraint(fields=['objeto', 'nombre'], name='uniq_objeto_opcion_nombre'),
        ]
```

**Por qué `codigo` en `Opcion` y no depender del `id` autoincremental
(a diferencia de `seg_opciones.opc_cod` que sí usa el autoincremental
directo en el código C#, ej. `TieneOpcion(31)`):** el código legado
referencia opciones por **número mágico hardcodeado** en cada form
(`Seguridad.TieneOpcion(31) // Modificar usuarios`). Es un patrón
frágil (el número depende del orden de inserción en la DB) que este
ADR **no repite** — se usa un `code` string estable (`'sample.delete'`)
para que el código Python sea legible y no dependa del orden de un
seed.

### D3 — Portar Grupos + privilegios de grupo (deny-overrides)

```python
class Grupo(models.Model):
    """Análogo a seg_grupos. Reemplaza los 3 roles fijos de ADR-0018
    por un catálogo configurable (el arquitecto pidió esto en la
    revisión de este ADR, ver historial arriba)."""
    nombre = models.CharField(max_length=25, unique=True)
    descripcion = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'clinic_rbac_grupo'


class PrivilegioGrupo(models.Model):
    """Análogo a seg_privilegios_grupo. bit real (BooleanField), no TipoAcceso."""
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE)
    opcion = models.ForeignKey(Opcion, on_delete=models.CASCADE)
    permitido = models.BooleanField(default=False)  # plp_val: 0=NO, 1=SI

    class Meta:
        db_table = 'clinic_rbac_privilegio_grupo'
        constraints = [
            models.UniqueConstraint(fields=['grupo', 'opcion'], name='uniq_grupo_opcion'),
        ]


class UsuarioGrupo(models.Model):
    """Análogo a seg_usuarios_grupos. N:M real (un usuario, varios grupos) —
    confirma la decisión ya tomada por el arquitecto en la revisión previa
    de este ADR de permitir roles múltiples, ahora con el nombre y
    semántica reales del sistema portado (Grupo, no 'rol')."""
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='grupos_clinicos')
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, related_name='usuarios')

    class Meta:
        db_table = 'clinic_rbac_usuario_grupo'
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'grupo'], name='uniq_usuario_grupo'),
        ]
```

### D4 — Portar excepción individual (override absoluto)

```python
class PrivilegioIndividual(models.Model):
    """Análogo a seg_privilegios_individuales. permitido=None significa
    'sin excepción' (usa el resultado de grupo) — por eso es
    BooleanField(null=True), replicando el NULL real de pri_val."""
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='privilegios_individuales')
    opcion = models.ForeignKey(Opcion, on_delete=models.CASCADE)
    permitido = models.BooleanField(null=True, default=None)  # None=sin excepción, True/False=override

    class Meta:
        db_table = 'clinic_rbac_privilegio_individual'
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'opcion'], name='uniq_usuario_opcion_individual'),
        ]
```

### D5 — Función de resolución, port directo de `nodeValue()`

```python
# apps/samples/permissions.py (extensión)

def tiene_opcion(user, opcion_code: str) -> bool:
    """Port directo de Seguridad.TieneOpcion()/nodeValue() del C# real.

    1. Resultado combinado de TODOS los grupos del usuario: deny-overrides
       (si algún grupo deniega, el combinado es False).
    2. La excepción individual del usuario, si existe, gana siempre.
    """
    opcion = Opcion.objects.filter(codigo=opcion_code).first()
    if opcion is None:
        return False  # fail-closed: opción no registrada, sin acceso

    individual = PrivilegioIndividual.objects.filter(usuario=user, opcion=opcion).first()
    if individual is not None and individual.permitido is not None:
        return individual.permitido  # excepción SIEMPRE gana (D5.1)

    privilegios_grupo = PrivilegioGrupo.objects.filter(
        opcion=opcion, grupo__usuarios__usuario=user,
    ).values_list('permitido', flat=True)
    privilegios_grupo = list(privilegios_grupo)
    if not privilegios_grupo:
        return False  # ningún grupo define esta opción -> fail-closed
    return all(privilegios_grupo)  # deny-overrides: basta un False para bloquear (D5.2)
```

**D5.1 y D5.2 son ports literales de la lógica C#**, no una
reinterpretación: `all(privilegios_grupo)` replica exactamente que
"basta un grupo con `plp_val=0`" para que el combinado sea `False`
(equivalente al `NOT IN (...WHERE plp_val=0...)` de
`createArrayGrupos()`); el `if individual.permitido is not None: return
individual.permitido` replica el `switch` de `nodeValue()`.

### D6 — Permission class DRF que envuelve `tiene_opcion()`

```python
class HasOpcion(BasePermission):
    """Reemplaza IsClinicRole/IsAdminRole con una versión configurable
    equivalente a Seguridad.TieneOpcion() del sistema real."""
    def __init__(self, opcion_code: str):
        self.opcion_code = opcion_code

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return tiene_opcion(request.user, self.opcion_code)
```

### D7 — Migración de datos: seed que reproduce ADR-0018 exactamente

Igual principio que el borrador anterior: **el día del despliegue,
ningún usuario pierde ni gana acceso** respecto al comportamiento
actual. Se crean 3 `Grupo` (`Analista`, `Supervisor`, `Admin`)
replicando los 3 roles de ADR-0018, se asigna cada `User` existente a
su grupo correspondiente vía `UsuarioGrupo` (derivado de
`is_staff`/`is_superuser`, igual que antes), y se puebla
`PrivilegioGrupo` con la matriz de ADR-0018 D3 (`sample.delete` solo
en `Admin`, el resto en los 3 grupos). Detalle completo en
`DD-RBAC-001.md`.

### D8 — Fuera de alcance en este ADR (documentado explícitamente, no ignorado)

El módulo `Security/` real incluye piezas que **no se portan** en este
ADR porque no fueron pedidas y ampliarían el alcance sin necesidad
inmediata:

- **`seg_session`/`seg_log`** (auditoría de sesión y de SQL ejecutado)
  — `backend-clinic` ya tiene un mecanismo de auditoría propio
  (`django-auditlog`, ver ADR-0016); duplicar con el patrón legado de
  `seg_log` (que registra el SQL crudo ejecutado) sería redundante y
  además reintroduciría el antipatrón de SQL concatenado que el
  código legado ya tiene.
- **Políticas de contraseña** (`usu_cpa`, `usu_per`, `usu_cca`,
  `usu_fcc` — cambio obligatorio, expiración, caducidad de cuenta) —
  Django/SimpleJWT ya tiene su propio ciclo de vida de credenciales;
  portar la política legada completa es un ADR aparte si se decide
  necesaria.
- **MD5 para contraseñas** — explícitamente NO se porta (sería
  regresión de seguridad); Django usa PBKDF2/Argon2 por defecto, se
  mantiene.
- **Máximo 3 intentos de login → cerrar aplicación** — no aplica a
  una API REST (no hay "aplicación" que cerrar); si se quiere control
  de intentos, es rate-limiting, tema aparte.

## Justificación

- **El código real es la fuente de verdad más fuerte posible** para
  decidir el modelo de permisos — no es una interpretación de un
  manual ni un esquema sin lógica, es la implementación que un
  sistema clínico comparable usó en producción durante años.
- **Blast radius sigue acotado y con seed no disruptivo**: 6 tablas
  nuevas (más que el borrador de 3, porque el modelo real es más rico
  — jerarquía de 3 niveles + grupos + excepción individual), 0 cambios
  al modelo `User`, 0 cambios a la superficie observable el día 1 del
  despliegue gracias al seed (D7).
- **La corrección del borrador inicial es, en sí, la lección del
  proceso AI-SDLC**: diseñar sobre un esquema sin la lógica de negocio
  real llevó a una regla de resolución (máximo privilegio) que era
  razonable en abstracto pero incorrecta frente al sistema real que se
  pretendía portar. Confirma la práctica de "verificar contra el
  código real antes de comprometerse a una decisión", ya documentada
  en `feedback-aisdlc-applied-to-bug` para el caso de bugs — aquí
  aplica igual para decisiones de diseño.

## Consecuencias

### Positivas
- Modelo de permisos fiel al sistema legado real, con excepción
  individual (útil para casos borde: "este analista en particular
  necesita eliminar muestras sin ser todo el grupo Admin", sin crear
  un grupo nuevo solo para él).
- Configurable sin redeploy vía Django Admin (D5/D9 abajo).
- Documentado 1:1 contra código real — más defendible en la
  sustentación que un modelo inspirado solo en un manual.

### Negativas
- **Mayor blast radius que el borrador inicial**: 6 tablas en vez de
  3 (`TipoObjeto`, `Objeto`, `Opcion`, `Grupo`, `PrivilegioGrupo`,
  `UsuarioGrupo`, `PrivilegioIndividual` — de hecho 7). Mitigado con
  seed idempotente y tests exhaustivos de la función `tiene_opcion()`.
- **La regla de resolución es menos intuitiva** que "máximo
  privilegio": un grupo puede *bloquear* lo que otro concede, y un
  usuario puede tener una excepción que ni siquiera su propio grupo
  explica. Mitigado documentando la regla explícitamente (D5) con
  tests que cubren cada combinación.
- **Riesgo operativo real, heredado del sistema original**: un
  administrador puede, sin darse cuenta, dejar `permitido=False` como
  excepción individual de un usuario y no entender por qué ese usuario
  no puede hacer algo que su grupo sí permite — el propio código C#
  original mitiga esto coloreando en rojo/azul el nodo del árbol según
  si la excepción individual coincide o difiere del grupo
  (`frmUsuariosEdit.cs::loadIndividual`, colores `Color.Red`/
  `Color.Blue`). Se recomienda un tratamiento equivalente en el
  `ModelAdmin` (D9) — a definir en el DD.
- Si el seed no corre en un ambiente nuevo, `tiene_opcion()` es
  fail-closed (retorna `False` sin `Opcion` u sin `PrivilegioGrupo`
  registrado) — más seguro que fail-open, pero requiere documentar el
  seed obligatorio en el runbook.

### Neutras
- `backend-admin` no se toca (D1).
- Auditoría de sesión/SQL (`seg_session`/`seg_log`) y políticas de
  contraseña del sistema legado NO se portan (D8) — decisión explícita,
  no omisión.

## Tensión con reglas del proyecto y cómo se resuelve

| Regla | Tensión | Resolución |
|---|---|---|
| **RN-06** (segregación analista/supervisor) | Un grupo o una excepción individual mal configurados podrían dar acceso indebido a `sample.delete` | El seed (D7) reproduce exactamente ADR-0018 el día 1; cambios posteriores son responsabilidad operativa del admin, igual que en el sistema legado (no hay constraint de DB que lo impida, tampoco lo tenía el original) |
| **No modificar ADRs sin uno nuevo** | Este ADR extiende ADR-0018 | ADR-0018 permanece sin cambios; `role_for_user()` puede conservarse como wrapper de compatibilidad si algún código lo sigue usando, o eliminarse si `HasOpcion` reemplaza completamente sus usos (a decidir en el DD/implementación) |
| **RN-09 cobertura ≥90%** | 7 modelos nuevos + función de resolución con lógica no trivial | Tests exhaustivos de `tiene_opcion()`: sin grupo, un grupo permite, un grupo deniega, dos grupos en conflicto (uno permite/uno deniega → False), excepción individual True sobre grupo False, excepción individual False sobre grupo True, sin `Opcion` registrada (fail-closed) |

## Alternativas evaluadas

**A1 (borrador inicial de este mismo ADR, descartado tras leer el
código real).** Modelo de 3 niveles de acceso (`TipoAcceso`
0/1/2) resuelto por máximo privilegio entre roles. Descartado porque
no es fiel al sistema real que se pidió portar — el modelo real es
binario y resuelve por deny-overrides + excepción individual, no por
máximo. Ver "Historial de revisión" al inicio de este documento.

**A2. No portar la excepción individual (`PrivilegioIndividual`),
solo grupos.** Rechazada: es una pieza central del sistema real (dos
forms completos, `frmUsuariosEdit.cs` tab "Individual", dedicados a
ella) — omitirla sería portar un modelo incompleto que no resuelve el
caso de uso real que motivó "portar el RBAC granular de MetaClass".

**A3. Usar el `id` autoincremental de `Opcion` como referencia desde
código (como hace el C# real con `TieneOpcion(31)`).** Rechazada: es
exactamente el antipatrón que hace frágil al código legado (los
números mágicos dependen del orden de un seed/migración). Se usa
`Opcion.codigo` (string estable) en su lugar (D2).

**A4. Aplicar el mismo patrón también a `backend-admin`.** Rechazada
por alcance (D1), igual razón que en el borrador anterior.

**A5. Portar `seg_session`/`seg_log`/políticas de contraseña.**
Rechazada explícitamente (D8) — `backend-clinic` ya tiene mecanismos
equivalentes o superiores (`django-auditlog`, SimpleJWT) y duplicar
introduciría redundancia sin beneficio.

## Trazabilidad

- **Sube a:** `reference-metaclass-legacy-schema` (memoria, esquema
  `script.sql`) + código fuente real `Security/*.cs` + `sqlaserca.sql`
  → decisión del arquitecto 2026-07-17 (portar RBAC granular, luego
  corregida tras compartir el código real) → **este ADR-0019**.
- **Genera:** `docs/design/DD-RBAC-001.md` (rediseñado con el modelo
  real) → `apps/samples/models_rbac.py` (7 modelos) →
  `apps/samples/permissions.py` (`tiene_opcion()`, `HasOpcion`) →
  migración con seed → tests.
- **Impacta:** `apps/samples/views.py` (migran de `IsClinicRole`/
  `IsAdminRole` a `HasOpcion('sample.X')`), `PROMPT_MAPPING.md`,
  `AGENTS.md` §5, `docs/DTI.md`.

## Notas

- **No implica migrar datos reales de una instalación de `Security/`
  o MetaClass** — solo el *modelo* de permisos. Migración de datos
  reales sigue sin decidirse (`project-metaclass-integration-pending`).
- El código fuente C# (`Security/`) no tiene `.csproj` en el repo —
  es un fragmento aportado por el arquitecto, no el proyecto completo.
  No se asume nada sobre las clases externas que referencia
  (`SQLClass`, `Seguridad`, `App`, `Change`, `Validar`, `Config`,
  `ErrorLog`, `ConnectionSQL`) más allá de lo que su uso revela —
  no están en el repo, no se leyeron.
- Rama de trabajo: a decidir en el DD.
- Este ADR es `proposed`, no `accepted` — requiere sign-off del
  arquitecto antes de implementar.
