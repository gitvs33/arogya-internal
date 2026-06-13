"""Hospital detail service — single-hospital queries for the detail endpoint.

Extracted from ``HospitalDetailSerializer`` so query logic can be unit-tested
independently of the serialization layer. The serializer becomes a pure
data transformer — it receives pre-fetched data and formats it.
"""
from datetime import timedelta

from django.utils import timezone

from ..models import (
    Hospital, HospitalUserProfile,
    Patient, Encounter, Invoice,
)


def read_hospital_detail(hospital):
    """Fetch all detail-page data for a single hospital.

    Returns a dict with three keys: ``stats``, ``staff_breakdown``, ``admin``.
    The result is designed to be passed into ``HospitalDetailSerializer``
    via its ``context`` parameter, eliminating DB queries from the serializer.
    """
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)

    # ── Stats ──────────────────────────────────────────────────────────
    stats = {
        'patients': Patient.objects.filter(hospital=hospital).count(),
        'encounters_30d': Encounter.objects.filter(
            hospital=hospital, created_at__gte=thirty_days_ago
        ).count(),
        'invoices': Invoice.objects.filter(hospital=hospital).count(),
    }

    # ── Staff breakdown ────────────────────────────────────────────────
    profiles = HospitalUserProfile.objects.filter(
        hospital=hospital, is_active=True
    ).select_related('role')

    by_role = {}
    for p in profiles:
        role_name = p.role.name if p.role else 'Unassigned'
        by_role[role_name] = by_role.get(role_name, 0) + 1

    staff_breakdown = {
        'total': sum(by_role.values()),
        'by_role': by_role,
    }

    # ── Admin ──────────────────────────────────────────────────────────
    admin_profile = HospitalUserProfile.objects.filter(
        hospital=hospital, role__name__iexact='Admin'
    ).select_related('user').first()

    admin = None
    if admin_profile:
        admin = {
            'id': admin_profile.user.id,
            'username': admin_profile.user.username,
            'email': admin_profile.user.email,
            'first_name': admin_profile.user.first_name,
            'last_name': admin_profile.user.last_name,
            'last_login': admin_profile.user.last_login,
            'employee_id': admin_profile.employee_id,
        }

    return {'stats': stats, 'staff_breakdown': staff_breakdown, 'admin': admin}
