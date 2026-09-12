"""Django Admin para el RBAC jerárquico (ADR-0019, DD-RBAC-001).

Punto de entrada de navegación para todo el sistema clínico — se prioriza
robustez operativa sobre minimalismo: inlines para editar la matriz de
privilegios sin salir de la pantalla del Grupo/Usuario, y resaltado visual
cuando una excepción individual difiere del resultado de grupo (mismo
criterio que el C# original, que coloreaba en rojo/azul el árbol de
opciones en frmUsuariosEdit.cs::loadIndividual).
"""
from django.contrib import admin
from django.utils.html import format_html

from .models_rbac import (
    Grupo,
    Objeto,
    Opcion,
    PrivilegioGrupo,
    PrivilegioIndividual,
    TipoObjeto,
    UsuarioGrupo,
)
from .permissions import tiene_opcion


@admin.register(TipoObjeto)
class TipoObjetoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'objetos_count')
    search_fields = ('nombre',)

    def objetos_count(self, obj):
        return obj.objetos.count()

    objetos_count.short_description = 'Objetos'


class OpcionInline(admin.TabularInline):
    """Editar las opciones de un Objeto directamente desde su pantalla,
    en vez de navegar a un listado separado."""

    model = Opcion
    extra = 1
    fields = ('codigo', 'nombre', 'descripcion')


@admin.register(Objeto)
class ObjetoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'tipo', 'opciones_count')
    list_filter = ('tipo',)
    search_fields = ('nombre',)
    inlines = [OpcionInline]

    def opciones_count(self, obj):
        return obj.opciones.count()

    opciones_count.short_description = 'Opciones'


@admin.register(Opcion)
class OpcionAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'objeto', 'tipo_objeto')
    list_filter = ('objeto__tipo', 'objeto')
    search_fields = ('codigo', 'nombre', 'descripcion')

    def tipo_objeto(self, obj):
        return obj.objeto.tipo.nombre

    tipo_objeto.short_description = 'Tipo'


class PrivilegioGrupoInline(admin.TabularInline):
    """Editar qué opciones puede hacer un Grupo directamente desde su
    pantalla — evita tener que ir a un listado plano de privilegios
    para configurar un grupo completo."""

    model = PrivilegioGrupo
    extra = 1
    autocomplete_fields = ('opcion',)
    fields = ('opcion', 'permitido')


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'usuarios_count', 'privilegios_count')
    search_fields = ('nombre',)
    inlines = [PrivilegioGrupoInline]

    def usuarios_count(self, obj):
        return obj.usuarios.count()

    usuarios_count.short_description = 'Usuarios'

    def privilegios_count(self, obj):
        return obj.privilegios.filter(permitido=True).count()

    privilegios_count.short_description = 'Opciones permitidas'


@admin.register(PrivilegioGrupo)
class PrivilegioGrupoAdmin(admin.ModelAdmin):
    list_display = ('grupo', 'opcion', 'permitido_badge')
    list_filter = ('grupo', 'permitido', 'opcion__objeto')
    search_fields = ('grupo__nombre', 'opcion__codigo', 'opcion__nombre')
    autocomplete_fields = ('opcion',)

    def permitido_badge(self, obj):
        color = 'green' if obj.permitido else 'red'
        texto = 'SI' if obj.permitido else 'NO'
        return format_html('<b style="color: {}">{}</b>', color, texto)

    permitido_badge.short_description = 'Permitido'


@admin.register(UsuarioGrupo)
class UsuarioGrupoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'grupo')
    list_filter = ('grupo',)
    search_fields = ('usuario__username', 'grupo__nombre')
    autocomplete_fields = ('usuario', 'grupo')


@admin.register(PrivilegioIndividual)
class PrivilegioIndividualAdmin(admin.ModelAdmin):
    """Excepción por usuario específico — ADR-0019 D4. `permitido=None`
    (mostrado como 'Sin excepción') no tiene efecto; True/False fuerza
    el valor sin importar los grupos del usuario. El campo
    `efecto_real` resalta en rojo/azul cuando la excepción difiere del
    resultado de grupo, replicando el criterio visual del C# original
    (frmUsuariosEdit.cs::loadIndividual, colores Color.Red/Color.Blue)
    para que un administrador no se sorprenda de por qué un usuario
    puntual no puede hacer algo que su grupo sí permite (o viceversa)."""

    list_display = ('usuario', 'opcion', 'permitido_display', 'efecto_real')
    list_filter = ('opcion__objeto', 'permitido')
    search_fields = ('usuario__username', 'opcion__codigo')
    autocomplete_fields = ('usuario', 'opcion')

    def permitido_display(self, obj):
        if obj.permitido is None:
            return 'Sin excepción'
        return 'SI (forzado)' if obj.permitido else 'NO (forzado)'

    permitido_display.short_description = 'Excepción'

    def efecto_real(self, obj):
        """Compara el resultado final (tiene_opcion) contra lo que el
        grupo diría sin la excepción, para hacer visible el conflicto."""
        resultado_final = tiene_opcion(obj.usuario, obj.opcion.codigo)
        if obj.permitido is None:
            return format_html('<span style="color: {}">{}</span>', 'gray', '— (usa grupo)')
        resultado_grupo = list(
            PrivilegioGrupo.objects.filter(
                opcion=obj.opcion, grupo__usuarios__usuario=obj.usuario,
            ).values_list('permitido', flat=True)
        )
        difiere = bool(resultado_grupo) and all(resultado_grupo) != obj.permitido
        color = 'red' if difiere else 'blue'
        etiqueta = 'DIFIERE del grupo' if difiere else 'coincide con grupo'
        return format_html(
            '<b style="color: {}">{}</b> → resultado final: {}',
            color, etiqueta, 'SI' if resultado_final else 'NO',
        )

    efecto_real.short_description = 'Efecto vs. grupo'
