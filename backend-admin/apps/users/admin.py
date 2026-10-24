"""Admin site registration for apps/users."""
from django.contrib import admin

from .models import AdminUser, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active')
    search_fields = ('email',)
    readonly_fields = ('date_joined', 'last_login')


@admin.register(AdminUser)
class AdminUserAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'role', 'active', 'deactivated_at', 'created_at')
    list_filter = ('role', 'active', 'deactivated_at')
    search_fields = ('full_name', 'email')
    readonly_fields = ('id', 'created_at', 'updated_at', 'deactivated_at', 'created_by')