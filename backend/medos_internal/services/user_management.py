"""User management service — transactional workflows for admin panel user CRUD.

Extracted from ``HospitalAdminViewSet.create()`` so the user creation
path can be unit-tested independently of the HTTP layer.
"""
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model

from ..models import Hospital, Role, HospitalUserProfile

User = get_user_model()


def create_admin_user(*, username, email, password,
                       first_name='', last_name='',
                       hospital_id, role_id=None,
                       employee_id=None, department='', designation=''):
    """Create a Django user + HospitalUserProfile in one transaction.

    Returns a dict with the created user data (ready for serialization).
    Raises ``IntegrityError`` on duplicate username/email/employee_id,
    ``Hospital.DoesNotExist`` if hospital_id is invalid,
    ``Role.DoesNotExist`` if role_id is given but invalid.
    """
    with transaction.atomic():
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        hospital = Hospital.objects.get(pk=hospital_id)

        role = None
        if role_id is not None:
            role = Role.objects.get(pk=role_id)

        profile = HospitalUserProfile.objects.create(
            user=user,
            hospital=hospital,
            role=role,
            employee_id=employee_id,
            department=department,
            designation=designation,
            must_change_password=True,
        )

    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_active': user.is_active,
        'role': role.name if role else None,
        'employee_id': profile.employee_id,
        'hospital_name': hospital.name,
        'last_login': user.last_login,
        'date_joined': user.date_joined,
    }
