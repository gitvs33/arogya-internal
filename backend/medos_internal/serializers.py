"""Serializers for the MedOS Internal Operations API."""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import (
    Hospital, Role,
    Patient, Encounter, Invoice,
)

User = get_user_model()


# ═══════════════════════════════════════════════════════════════════════════════
#  INTERNAL OPS SERIALIZERS
# ═══════════════════════════════════════════════════════════════════════════════


class InternalLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class HospitalListSerializer(serializers.ModelSerializer):
    staff_count = serializers.IntegerField(read_only=True)
    admin_email = serializers.SerializerMethodField()
    admin_name = serializers.SerializerMethodField()

    class Meta:
        model = Hospital
        fields = [
            'id', 'name', 'slug', 'plan', 'is_active', 'is_expired',
            'subscription_expires_at', 'created_at',
            'staff_count', 'admin_email', 'admin_name',
        ]

    def _get_admin(self, obj):
        admin_profiles = self.context.get('admin_profiles')
        if admin_profiles is None:
            raise RuntimeError(
                'HospitalListSerializer requires admin_profiles in context. '
                'The view must prefetch admin profiles and pass them via context.'
            )
        admin = admin_profiles.get(obj.pk)
        return admin

    def get_admin_email(self, obj):
        admin = self._get_admin(obj)
        return admin.user.email if admin else None

    def get_admin_name(self, obj):
        admin = self._get_admin(obj)
        if admin:
            return f"{admin.user.first_name} {admin.user.last_name}".strip() or admin.user.username
        return None


class HospitalDetailSerializer(serializers.ModelSerializer):
    staff_breakdown = serializers.SerializerMethodField()
    admin = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()

    class Meta:
        model = Hospital
        fields = [
            'id', 'name', 'slug', 'address', 'phone', 'email',
            'logo_url', 'registration_number',
            'plan', 'is_active', 'is_expired', 'subscription_expires_at',
            'license_key', 'user_limit',
            'created_at', 'updated_at',
            'staff_breakdown', 'admin', 'stats',
        ]

    def get_staff_breakdown(self, obj):
        return self.context.get('staff_breakdown')

    def get_admin(self, obj):
        return self.context.get('admin')

    def get_stats(self, obj):
        return self.context.get('stats')


class HospitalCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    slug = serializers.SlugField()
    plan = serializers.ChoiceField(choices=Hospital.Plan.choices, default=Hospital.Plan.BASIC)
    address = serializers.CharField(required=False, allow_blank=True, default='')
    phone = serializers.CharField(required=False, allow_blank=True, default='')
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    admin_name = serializers.CharField(max_length=200)
    admin_email = serializers.EmailField()
    admin_password = serializers.CharField(min_length=8)


class HospitalUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = [
            'name', 'address', 'phone', 'email',
            'logo_url', 'registration_number',
            'plan', 'is_active', 'subscription_expires_at',
            'license_key', 'user_limit',
        ]
        extra_kwargs = {f: {'required': False} for f in [
            'name', 'address', 'phone', 'email',
            'logo_url', 'registration_number',
            'plan', 'is_active', 'subscription_expires_at',
            'license_key', 'user_limit',
        ]}


class AdminUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    is_active = serializers.BooleanField()
    role = serializers.CharField(allow_null=True)
    employee_id = serializers.CharField(allow_null=True)
    hospital_name = serializers.CharField(allow_null=True)
    last_login = serializers.DateTimeField(allow_null=True)
    date_joined = serializers.DateTimeField()


class AdminUserCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=150, required=False, default='')
    last_name = serializers.CharField(max_length=150, required=False, default='')
    role_id = serializers.IntegerField(required=False, allow_null=True)
    employee_id = serializers.CharField(max_length=50, required=False, allow_null=True)
    department = serializers.CharField(max_length=100, required=False, default='')
    designation = serializers.CharField(max_length=100, required=False, default='')
    hospital_id = serializers.UUIDField()


class AdminRoleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    permissions = serializers.JSONField()
    is_active = serializers.BooleanField()
    user_count = serializers.IntegerField()
    hospital_name = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()



