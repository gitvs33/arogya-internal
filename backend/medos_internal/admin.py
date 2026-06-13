"""Django admin configuration for MedOS Internal Operations.

This registers only the tenant-management models with Django's admin interface.
Superusers (MedOS staff) manage hospitals, monitor system health, and
configure global settings here.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from .models import (
    Hospital, AdminModule, SystemAlert, Department,
    MasterDataEntry, SystemSetting, WorkflowDefinition,
    DeviceIntegration, SecurityPolicy, BackupRecord,
    LicenseInfo, StorageMetrics,
)

User = get_user_model()

# ── Admin branding ───────────────────────────────────────────
admin.site.site_header = 'MedOS Internal Operations'
admin.site.site_title = 'MedOS Internal Admin'
admin.site.index_title = 'Platform Management'

# Unregister Group — we use our own Role model
try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


# ═══════════════════════════════════════════════════════════════════════════════
#  HOSPITAL ADMIN  (MedOS team manages tenants here)
# ═══════════════════════════════════════════════════════════════════════════════

class HospitalUserInline(admin.TabularInline):
    from .models import HospitalUserProfile
    model = HospitalUserProfile
    extra = 0
    fields = ['user', 'employee_id', 'role', 'department', 'designation', 'is_active']
    autocomplete_fields = ['user']
    raw_id_fields = ['role']
    readonly_fields = ['is_active']
    can_delete = False
    verbose_name = 'Staff Member'
    verbose_name_plural = 'Staff Members'


class HospitalRoleInline(admin.TabularInline):
    from .models import Role
    model = Role
    extra = 0
    fields = ['name', 'is_active', 'created_at']
    readonly_fields = ['created_at']
    can_delete = False
    verbose_name = 'Role'
    verbose_name_plural = 'Roles'


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'slug', 'plan', 'is_active', 'user_limit',
        'subscription_expires_at', 'created_at'
    ]
    list_filter = ['plan', 'is_active']
    search_fields = ['name', 'slug', 'email']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = [
        ('Identity', {
            'fields': ['name', 'slug', 'registration_number']
        }),
        ('Contact', {
            'fields': ['address', 'phone', 'email', 'logo_url']
        }),
        ('Subscription', {
            'fields': ['plan', 'is_active', 'subscription_expires_at',
                       'license_key', 'user_limit']
        }),
        ('Metadata', {
            'fields': ['id', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    inlines = [HospitalUserInline, HospitalRoleInline]


# ═══════════════════════════════════════════════════════════════════════════════
#  SYSTEM MONITORING
# ═══════════════════════════════════════════════════════════════════════════════


@admin.register(AdminModule)
class AdminModuleAdmin(admin.ModelAdmin):
    list_display = ['label', 'name', 'status', 'is_critical', 'hospital', 'updated_at']
    list_filter = ['status', 'is_critical']
    search_fields = ['name', 'label']


@admin.register(SystemAlert)
class SystemAlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'severity', 'is_resolved', 'hospital', 'created_at']
    list_filter = ['severity', 'is_resolved']
    search_fields = ['title', 'description']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'hospital']
    list_filter = ['is_active']
    search_fields = ['name', 'code']


@admin.register(MasterDataEntry)
class MasterDataEntryAdmin(admin.ModelAdmin):
    list_display = ['category', 'key', 'value', 'is_active', 'hospital']
    list_filter = ['category', 'is_active']
    search_fields = ['key', 'value', 'category']


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ['key', 'label', 'value_type', 'category', 'hospital']
    list_filter = ['category', 'value_type']
    search_fields = ['key', 'label']


@admin.register(WorkflowDefinition)
class WorkflowDefinitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'module', 'is_active', 'hospital']
    list_filter = ['module', 'is_active']
    search_fields = ['name']


@admin.register(DeviceIntegration)
class DeviceIntegrationAdmin(admin.ModelAdmin):
    list_display = ['name', 'device_type', 'is_active', 'hospital']
    list_filter = ['device_type', 'is_active']
    search_fields = ['name']


@admin.register(SecurityPolicy)
class SecurityPolicyAdmin(admin.ModelAdmin):
    list_display = ['policy_type', 'is_enforced', 'hospital']
    list_filter = ['policy_type', 'is_enforced']


@admin.register(BackupRecord)
class BackupRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'backup_type', 'status', 'started_at', 'completed_at']
    list_filter = ['status', 'backup_type']


@admin.register(LicenseInfo)
class LicenseInfoAdmin(admin.ModelAdmin):
    list_display = ['edition', 'valid_from', 'valid_till', 'is_active', 'hospital']
    list_filter = ['edition', 'is_active']


@admin.register(StorageMetrics)
class StorageMetricsAdmin(admin.ModelAdmin):
    list_display = ['storage_used_gb', 'storage_total_gb', 'database_status', 'recorded_at']
    list_filter = ['database_status']


# ═══════════════════════════════════════════════════════════════════════════════
#  USER ADMIN
# ═══════════════════════════════════════════════════════════════════════════════


class HospitalUserProfileInline(admin.StackedInline):
    from .models import HospitalUserProfile
    model = HospitalUserProfile
    can_delete = False
    verbose_name = 'Hospital Profile'


class CustomUserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'is_staff', 'is_superuser', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active']
    inlines = [HospitalUserProfileInline]


# Re-register UserAdmin
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, CustomUserAdmin)
