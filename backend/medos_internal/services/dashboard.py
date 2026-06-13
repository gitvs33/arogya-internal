"""Dashboard service — all queries behind three composite endpoints.

Every method returns a plain dict (no Serializer dependency). The views
are thin adapters that call these and wrap the result in a Response.
"""
import platform
import sys
from datetime import date, timedelta

import django

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone

from ..models import (
    Hospital, Role, HospitalUserProfile, SystemActivityLog,
    Patient, Encounter, Invoice,
    AdminModule, Department, LicenseInfo, SecurityPolicy,
    StorageMetrics, SystemAlert, UserLoginActivity,
)

User = get_user_model()


# ═══════════════════════════════════════════════════════════════════════════════
#  PLATFORM STATS  — hospital-level KPIs (hospitals, patients, invoices)
# ═══════════════════════════════════════════════════════════════════════════════


def read_platform_stats():
    """Platform-wide KPIs for the internal ops dashboard.

    Returns hospital-level aggregates: total/active hospitals, staff count,
    patient/encounter/invoice totals, and 30-day growth numbers.
    """
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    return {
        'total_hospitals': Hospital.objects.count(),
        'active_hospitals': Hospital.objects.filter(is_active=True).count(),
        'total_staff': HospitalUserProfile.objects.filter(is_active=True).count(),
        'total_patients': Patient.objects.count(),
        'total_encounters': Encounter.objects.count(),
        'total_invoices': Invoice.objects.count(),
        'patients_30d': Patient.objects.filter(created_at__gte=thirty_days_ago).count(),
        'onboarding_30d': Hospital.objects.filter(created_at__gte=thirty_days_ago).count(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  OVERVIEW  — slow-changing data (KPI cards, modules, storage, license, system)
# ═══════════════════════════════════════════════════════════════════════════════


# ── Cache timeouts (seconds) matching the data cadence tiers ────────────────
CACHE_TTL_OVERVIEW = 300   # 5 min — slow data
CACHE_TTL_ACTIVITY = 60    # 1 min — medium cadence
CACHE_TTL_ALERTS = 30      # 30 s — fast data


def _cached_or_compute(cache_key, ttl, compute_fn):
    """Fetch from cache or compute and store."""
    result = cache.get(cache_key)
    if result is not None:
        return result
    result = compute_fn()
    cache.set(cache_key, result, ttl)
    return result


def read_overview():
    """Composite payload for the admin dashboard overview.

    Merges what were 6 separate endpoints:
      KPIs · module status · database storage · license · system info · security
    Cached for {} seconds.
    """.format(CACHE_TTL_OVERVIEW)
    return _cached_or_compute('dashboard:overview', CACHE_TTL_OVERVIEW, _compute_overview)


def _compute_overview():
    return {
        'kpis': _read_kpis(),
        'module_status': _read_module_status(),
        'database_storage': _read_database_storage(),
        'license_info': _read_license_info(),
        'system_info': _read_system_info(),
        'security_overview': _read_security_overview(),
    }


def _read_kpis():
    """High-level KPI cards — users, departments, roles, storage."""
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    sixty_days_ago = today - timedelta(days=60)

    total_users_count = User.objects.count()
    users_last_month = User.objects.filter(date_joined__gte=thirty_days_ago).count()
    users_prev_month = User.objects.filter(
        date_joined__gte=sixty_days_ago,
        date_joined__lt=thirty_days_ago,
    ).count()
    growth_num = users_last_month - users_prev_month
    users_growth = f'+{growth_num} this month' if growth_num > 0 else ''

    active_user_ids = UserLoginActivity.objects.filter(
        login_timestamp__gte=thirty_days_ago,
        was_successful=True,
    ).values_list('user_id', flat=True).distinct()
    active_users_count = len(set(active_user_ids))
    active_users_pct = round(
        (active_users_count / total_users_count * 100) if total_users_count > 0 else 0.0, 1
    )

    departments_count = Department.objects.count()
    depts_created = Department.objects.filter(created_at__gte=thirty_days_ago).count()
    dept_change = f'+{depts_created}' if depts_created else '0'

    roles_count = Role.objects.count()
    roles_created = Role.objects.filter(created_at__gte=thirty_days_ago).count()

    storage = StorageMetrics.objects.last()
    storage_used = storage.storage_used_gb if storage else 0
    storage_total = storage.storage_total_gb if storage else 1
    storage_pct = round((storage_used / storage_total * 100) if storage_total > 0 else 0, 1)

    return {
        'total_users': {'count': total_users_count, 'growth': users_growth},
        'active_users': {'count': active_users_count, 'percentage': active_users_pct},
        'departments': {'count': departments_count, 'growth': dept_change},
        'roles': {'count': roles_count, 'growth': f'+{roles_created}' if roles_created else '0'},
        'system_uptime': {'count': '99.9%', 'growth': '30 days'},
        'storage_used': {
            'used': f'{storage_used:.2f} TB',
            'total': f'{storage_total:.2f} TB',
            'percentage': storage_pct,
        },
    }


def _read_module_status():
    """Operational status of system modules."""
    qs = AdminModule.objects.all().order_by('name')
    return [
        {
            'id': str(m.id),
            'name': m.name,
            'label': m.label,
            'status': m.status,
            'is_critical': m.is_critical,
            'hospital_id': str(m.hospital_id) if m.hospital_id else None,
            'updated_at': m.updated_at.isoformat() if m.updated_at else None,
        }
        for m in qs
    ]


def _read_database_storage():
    """Current database storage metrics."""
    storage = StorageMetrics.objects.last()
    if not storage:
        return {
            'storage_used_gb': 0,
            'storage_total_gb': 0,
            'database_status': 'Unknown',
            'last_backup': None,
            'next_backup': None,
        }
    return {
        'storage_used_gb': storage.storage_used_gb,
        'storage_total_gb': storage.storage_total_gb,
        'database_status': storage.database_status,
        'last_backup': storage.last_backup.isoformat() if storage.last_backup else None,
        'next_backup': storage.next_backup.isoformat() if storage.next_backup else None,
    }


def _read_license_info():
    """Current active license information."""
    lic = LicenseInfo.objects.filter(is_active=True).last()
    if not lic:
        return None
    return {
        'id': str(lic.id),
        'edition': lic.edition,
        'license_key': lic.license_key,
        'valid_from': lic.valid_from.isoformat() if lic.valid_from else None,
        'valid_till': lic.valid_till.isoformat() if lic.valid_till else None,
        'registered_modules': lic.registered_modules,
        'total_modules': lic.total_modules,
        'active_users': lic.active_users,
        'user_limit': lic.user_limit,
        'is_active': lic.is_active,
        'hospital_id': str(lic.hospital_id) if lic.hospital_id else None,
        'updated_at': lic.updated_at.isoformat() if lic.updated_at else None,
    }


def _read_system_info():
    """Django / Python / DB version info."""
    db_engine = settings.DATABASES.get('default', {}).get('ENGINE', 'Unknown')
    return {
        'django_version': django.get_version(),
        'python_version': sys.version,
        'debug_mode': settings.DEBUG,
        'database': db_engine,
    }


def _read_security_overview():
    """Security overview — user counts, login attempts."""
    thirty_days_ago = timezone.now() - timedelta(days=30)
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)

    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    admins = User.objects.filter(is_superuser=True).count()

    login_qs = UserLoginActivity.objects.all()
    recent_logins = login_qs.filter(login_timestamp__gte=thirty_days_ago, was_successful=True).count()
    failed_logins = login_qs.filter(login_timestamp__gte=thirty_days_ago, was_successful=False).count()
    login_attempts_24h = login_qs.filter(login_timestamp__gte=twenty_four_hours_ago).count()

    return {
        'total_users': total_users,
        'active_users': active_users,
        'admins': admins,
        'recent_logins': recent_logins,
        'failed_logins': failed_logins,
        'login_attempts_24h': login_attempts_24h,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  ACTIVITY  — medium-cadence data (chart, user activity, audit summary)
# ═══════════════════════════════════════════════════════════════════════════════


def read_activity():
    """Composite payload for the activity section.

    Merges what were 3 separate endpoints:
      7-day chart · user activity · audit summary
    Cached for {} seconds.
    """.format(CACHE_TTL_ACTIVITY)
    return _cached_or_compute('dashboard:activity', CACHE_TTL_ACTIVITY, _compute_activity)


def _compute_activity():
    return {
        'system_overview_chart': _read_system_overview_chart(),
        'user_activity': _read_user_activity(),
        'audit_summary': _read_audit_summary(),
    }


def _read_system_overview_chart():
    """System activity overview chart data (last 7 days)."""
    today = date.today()
    points = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        logins = UserLoginActivity.objects.filter(
            login_timestamp__date=day, was_successful=True,
        ).count()
        acts = SystemActivityLog.objects.filter(timestamp__date=day)
        points.append({
            'date': day.isoformat(),
            'logins': logins,
            'transactions': acts.filter(event_type__contains='transaction').count(),
            'errors': acts.filter(event_type__contains='error').count(),
        })
    return points


def _read_user_activity():
    """User login activity summary (top 20 active users, 30 days)."""
    thirty_days_ago = timezone.now() - timedelta(days=30)

    login_qs = UserLoginActivity.objects.filter(
        login_timestamp__gte=thirty_days_ago,
        was_successful=True,
    )

    user_stats = (
        login_qs
        .values('user__username', 'user__email')
        .annotate(login_count=Count('id'))
        .order_by('-login_count')[:20]
    )

    results = []
    for stat in user_stats:
        user_obj = User.objects.filter(username=stat['user__username']).first()
        profile = HospitalUserProfile.objects.filter(user=user_obj).first() if user_obj else None
        last_login = UserLoginActivity.objects.filter(
            user=user_obj, was_successful=True,
        ).order_by('-login_timestamp').first() if user_obj else None
        results.append({
            'username': stat['user__username'],
            'email': stat['user__email'] or '',
            'role': profile.role.name if profile and profile.role else 'N/A',
            'last_active': last_login.login_timestamp.isoformat() if last_login and last_login.login_timestamp else None,
            'login_count': stat['login_count'],
        })

    return results


def _read_audit_summary():
    """Audit log summary grouped by category."""
    thirty_days_ago = timezone.now() - timedelta(days=30)
    qs = SystemActivityLog.objects.filter(timestamp__gte=thirty_days_ago)

    by_category = (
        qs.values('event_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    recent = qs.order_by('-timestamp')[:10]
    recent_data = [
        {
            'id': str(r.id),
            'event_type': r.event_type,
            'description': r.description,
            'author_name': r.author_name,
            'created_at': r.timestamp.isoformat(),
        }
        for r in recent
    ]

    return {
        'total_logs': qs.count(),
        'by_category': [
            {'category': item['event_type'], 'count': item['count']}
            for item in by_category
        ],
        'recent': recent_data,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  ALERTS  — fast-changing data (unresolved alerts, recent activities)
# ═══════════════════════════════════════════════════════════════════════════════


def read_alerts():
    """Composite payload for real-time alerts and recent activities.

    Merges what were 2 separate endpoints:
      system alerts · recent activities
    Cached for {} seconds.
    """.format(CACHE_TTL_ALERTS)
    return _cached_or_compute('dashboard:alerts', CACHE_TTL_ALERTS, _compute_alerts)


def _compute_alerts():
    return {
        'system_alerts': _read_system_alerts(),
        'recent_activities': _read_recent_activities(),
    }


def _read_system_alerts():
    """Unresolved system-level infrastructure alerts."""
    qs = SystemAlert.objects.filter(is_resolved=False).order_by('-created_at')
    return [
        {
            'id': str(a.id),
            'severity': a.severity,
            'title': a.title,
            'description': a.description,
            'is_resolved': a.is_resolved,
            'created_at': a.created_at.isoformat() if a.created_at else None,
            'resolved_at': a.resolved_at.isoformat() if a.resolved_at else None,
            'hospital_id': str(a.hospital_id) if a.hospital_id else None,
        }
        for a in qs
    ]


def _read_recent_activities():
    """Recent system activities across all hospitals."""
    qs = SystemActivityLog.objects.select_related('hospital').order_by('-timestamp')[:20]
    return [
        {
            'id': str(r.id),
            'event_type': r.event_type,
            'description': r.description,
            'author_name': r.author_name,
            'hospital_name': r.hospital.name if r.hospital else 'System',
            'created_at': r.timestamp.isoformat(),
        }
        for r in qs
    ]



