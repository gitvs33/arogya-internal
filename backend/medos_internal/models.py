"""Models for MedOS Internal Operations.

Models that already exist in the main medos database are declared as
unmanaged (Meta.managed = False) with explicit db_table so we can
read/write the same tables without migrating them here.
"""
import uuid
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


# ═══════════════════════════════════════════════════════════════════════════════
#  MANAGED MODELS  — owned by this project
# ═══════════════════════════════════════════════════════════════════════════════


class Hospital(models.Model):
    """The core tenant — each hospital is a separate organisation."""
    class Plan(models.TextChoices):
        BASIC = 'basic', 'Basic'
        PROFESSIONAL = 'professional', 'Professional'
        ENTERPRISE = 'enterprise', 'Enterprise'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text='Hospital / organisation name')
    slug = models.SlugField(unique=True, help_text='Used in subdomain, e.g. citycare.medos.com')
    address = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    logo_url = models.URLField(blank=True, default='')
    registration_number = models.CharField(max_length=100, blank=True, default='')
    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.BASIC)
    is_active = models.BooleanField(default=True, help_text='Deactivated = subscription expired / disabled')
    subscription_expires_at = models.DateTimeField(null=True, blank=True)
    license_key = models.CharField(max_length=200, blank=True, default='')
    user_limit = models.IntegerField(default=0, help_text='Max allowed users (0 = unlimited)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False  # main medos project owns the migrations for medos_hospital
        db_table = 'medos_hospital'
        ordering = ['name']
        verbose_name_plural = 'hospitals'

    def __str__(self) -> str:
        return self.name

    @property
    def is_expired(self) -> bool:
        if self.subscription_expires_at is None:
            return False
        return timezone.now() > self.subscription_expires_at


class AdminModule(models.Model):
    """Tracks the real-time operational status of system modules."""
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    STATUS_CHOICES = [
        ('Operational', 'Operational'),
        ('Degraded', 'Degraded'),
        ('Offline', 'Offline'),
    ]
    name = models.CharField(max_length=100, unique=True,
                            help_text='Machine name, e.g. emr, billing, pharmacy')
    label = models.CharField(max_length=100,
                             help_text='Human-readable name, e.g. EMR, Patient Registration')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Operational')
    is_critical = models.BooleanField(default=False)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name='admin_modules', db_constraint=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'medos_adminmodule'
        ordering = ['name']


class SystemAlert(models.Model):
    """System-level notifications (infrastructure, not medical alerts)."""
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    SEVERITY_CHOICES = [
        ('critical', 'Critical'),
        ('warning', 'Warning'),
        ('info', 'Info'),
        ('success', 'Success'),
    ]
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name='+', db_constraint=False)

    class Meta:
        db_table = 'medos_systemalert'
        ordering = ['-created_at']


class UserLoginActivity(models.Model):
    """Tracks every user login for admin dashboard analytics."""
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='+')
    login_timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, default='')
    was_successful = models.BooleanField(default=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name='+', db_constraint=False)

    class Meta:
        db_table = 'medos_userloginactivity'
        ordering = ['-login_timestamp']


class Department(models.Model):
    """Hospital department / ward."""
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, help_text='Short code, e.g. CARD, ORTH')
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    head_of_department = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name='departments', db_constraint=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'medos_department'
        ordering = ['name']


class MasterDataEntry(models.Model):
    """Lookup table entries for dropdowns and config lists."""
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    category = models.CharField(max_length=100, db_index=True)
    key = models.CharField(max_length=100)
    value = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name='+', db_constraint=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'medos_masterdataentry'
        unique_together = [('hospital', 'category', 'key')]
        ordering = ['category', 'display_order', 'key']
        verbose_name_plural = 'master data entries'

    def __str__(self):
        return f'{self.category}: {self.key} = {self.value}'


class SystemSetting(models.Model):
    """Key-value global application configuration."""
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    key = models.CharField(max_length=100, unique=True)
    label = models.CharField(max_length=200)
    value = models.JSONField(help_text='Stored as JSON; cast to value_type on read')
    value_type = models.CharField(max_length=20, default='string')
    category = models.CharField(max_length=100, default='general')
    is_encrypted = models.BooleanField(default=False)
    description = models.TextField(blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name='+', db_constraint=False)

    class Meta:
        db_table = 'medos_systemsetting'
        ordering = ['category', 'key']


class WorkflowDefinition(models.Model):
    """Defines a state machine workflow for a module."""
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=100)
    module = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    initial_state = models.CharField(max_length=100)
    states = models.JSONField()
    transitions = models.JSONField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name='+', db_constraint=False)

    class Meta:
        db_table = 'medos_workflowdefinition'
        unique_together = [('hospital', 'module', 'name')]
        ordering = ['module', 'name']


class DeviceIntegration(models.Model):
    """External hardware / device integration configuration."""
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=100)
    device_type = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    port = models.IntegerField(blank=True, null=True)
    api_endpoint = models.URLField(blank=True, default='')
    auth_type = models.CharField(max_length=20, default='none')
    credentials = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name='+', db_constraint=False)

    class Meta:
        db_table = 'medos_deviceintegration'
        ordering = ['name']


class SecurityPolicy(models.Model):
    """Security configuration entries."""
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    policy_type = models.CharField(max_length=50, unique=True)
    settings = models.JSONField(default=dict)
    is_enforced = models.BooleanField(default=True)
    description = models.TextField(blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name='+', db_constraint=False)

    class Meta:
        db_table = 'medos_securitypolicy'
        ordering = ['policy_type']


class BackupRecord(models.Model):
    """Tracks database backup operations."""
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    backup_type = models.CharField(max_length=20)
    status = models.CharField(max_length=20, default='IN_PROGRESS')
    file_url = models.URLField(blank=True, default='')
    file_size_mb = models.FloatField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    triggered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name='+', db_constraint=False)

    class Meta:
        db_table = 'medos_backuprecord'
        ordering = ['-started_at']


class LicenseInfo(models.Model):
    """Software license and subscription details."""
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    edition = models.CharField(max_length=50, default='Enterprise')
    license_key = models.CharField(max_length=200, blank=True, default='')
    valid_from = models.DateField()
    valid_till = models.DateField()
    registered_modules = models.IntegerField(default=0)
    total_modules = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)
    user_limit = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name='+', db_constraint=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'medos_licenseinfo'
        verbose_name_plural = 'license info'
        ordering = ['-valid_till']


class StorageMetrics(models.Model):
    """Tracks database storage usage over time."""
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    storage_used_gb = models.FloatField(help_text='Used storage in GB')
    storage_total_gb = models.FloatField(help_text='Total capacity in GB')
    database_status = models.CharField(max_length=50, default='Healthy')
    last_backup = models.DateTimeField(null=True, blank=True)
    next_backup = models.DateTimeField(null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name='+', db_constraint=False)

    class Meta:
        db_table = 'medos_storagemetrics'
        verbose_name_plural = 'storage metrics'
        ordering = ['-recorded_at']


# ═══════════════════════════════════════════════════════════════════════════════
#  UNMANAGED MODELS  — reflect existing tables in the medos backend DB
# ═══════════════════════════════════════════════════════════════════════════════


class Role(models.Model):
    """Staff role with permission scopes (from medos.models)."""
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, default='')
    permissions = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name='+', db_constraint=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'medos_role'
        ordering = ['name']

    def __str__(self):
        return self.name


class HospitalUserProfile(models.Model):
    """Extended profile for hospital staff (from medos.models)."""
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='+', db_constraint=False)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name='staff_profiles', db_constraint=False)
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', db_constraint=False)
    department = models.CharField(max_length=100, blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    designation = models.CharField(max_length=100, blank=True, default='')
    must_change_password = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'medos_hospitaluserprofile'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.employee_id or 'no ID'})"

    def get_role_snapshot_hash(self):
        import hashlib, json
        raw = json.dumps({
            'user_id': self.user_id,
            'role': self.role.name if self.role else None,
            'permissions': self.role.permissions if self.role else {},
        }, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()


class SystemActivityLog(models.Model):
    """Tracks important system events (from medos.models)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    author_name = models.CharField(max_length=255, blank=True, default='')
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name='+', db_constraint=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        managed = False
        db_table = 'medos_systemactivitylog'
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.event_type} @ {self.timestamp}'


class Patient(models.Model):
    """Patient record (from medos.models) — read-only for stats."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name='+', db_constraint=False)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'medos_patient'


class Encounter(models.Model):
    """Patient encounter (from medos.models) — read-only for stats."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name='+', db_constraint=False)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'medos_encounter'


class Invoice(models.Model):
    """Invoice (from medos.models) — read-only for stats."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name='+', db_constraint=False)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'medos_invoice'
