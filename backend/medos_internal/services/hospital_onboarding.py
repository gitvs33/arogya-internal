"""Hospital onboarding service — transactional workflow for creating hospitals.

Extracted from the mixed GET/POST ``hospital_list`` view so the create
path can be tested independently of the list path.
"""
from django.db import transaction
from django.contrib.auth import get_user_model

from ..models import (
    Hospital, Role, HospitalUserProfile, SystemActivityLog,
)

User = get_user_model()


def onboard_hospital(*, name, slug, plan, admin_name, admin_email,
                      admin_password, address='', phone='', email='',
                      performed_by=None):
    """Create a hospital + admin user + admin role + profile in one transaction.

    Returns the created ``Hospital`` instance.
    Raises ``IntegrityError`` on duplicate slug, duplicate email, etc.
    """
    with transaction.atomic():
        hospital = Hospital.objects.create(
            name=name,
            slug=slug,
            plan=plan,
            address=address,
            phone=phone,
            email=email,
            is_active=True,
        )

        admin_user = User.objects.create_user(
            username=admin_email.split('@')[0],
            email=admin_email,
            password=admin_password,
            first_name=admin_name.split()[0] if admin_name else '',
            last_name=' '.join(admin_name.split()[1:]) if len(admin_name.split()) > 1 else '',
            is_staff=False,
        )

        admin_role, _ = Role.objects.get_or_create(
            name='Admin',
            hospital=hospital,
            defaults={
                'permissions': {
                    'admin': ['read', 'write', 'manage_users', 'manage_roles'],
                    'patients': ['read', 'write', 'delete'],
                    'encounters': ['read', 'write', 'delete'],
                    'billing': ['read', 'write', 'delete'],
                    'sync': ['read', 'write'],
                    'alerts': ['read', 'write', 'acknowledge', 'resolve'],
                    'reports': ['read', 'export'],
                    'teleicu': ['read', 'write', 'monitor'],
                },
                'is_active': True,
            },
        )

        HospitalUserProfile.objects.create(
            user=admin_user,
            hospital=hospital,
            role=admin_role,
            employee_id=f'HOSP-{hospital.slug.upper()[:4]}-001',
            must_change_password=True,
        )

        SystemActivityLog.objects.create(
            event_type='hospital_onboarded',
            description=f'Hospital "{hospital.name}" onboarded by {performed_by.username}',
            author_name=performed_by.username,
            hospital=hospital,
        )

    return hospital
