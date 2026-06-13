"""Tests for the DashboardService — the internal seam behind dashboard views.

These tests exercise query logic directly, not through HTTP. No client login,
no token setup, no middleware. Just call the service function and assert on
the returned dict.

Run with:
    cd backend
    python manage.py test medos_internal.tests.test_dashboard_service --verbosity=2
"""
from datetime import date, timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.utils import timezone

from medos_internal.models import (
    AdminModule, Department, Hospital, LicenseInfo,
    Role, StorageMetrics, SystemActivityLog, UserLoginActivity,
)
from medos_internal.services.dashboard import read_overview, read_activity, read_alerts

User = get_user_model()


# ═══════════════════════════════════════════════════════════════════════════════
#  BASE — creates unmanaged tables in test database
# ═══════════════════════════════════════════════════════════════════════════════


class DashboardServiceTestBase(TestCase):
    """Creates unmanaged tables needed by dashboard service tests.

    Hospital and other shared models have managed=False, so Django's
    test DB doesn't create them automatically. We create the tables
    with raw SQL so they exist for FK references.

    Also clears the Django cache before each test so cached dashboard
    results don't leak between test cases.
    """

    def setUp(self):
        super().setUp()
        from django.core.cache import cache
        cache.clear()

    # SQLite CREATE TABLE statements mirroring the unmanaged models.
    _UNMANAGED_SQL = {
        'medos_hospital': '''
            CREATE TABLE IF NOT EXISTS medos_hospital (
                id UUID PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                slug VARCHAR(50) NOT NULL UNIQUE,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                address TEXT NOT NULL DEFAULT '',
                phone VARCHAR(20) NOT NULL DEFAULT '',
                email VARCHAR(254) NOT NULL DEFAULT '',
                logo_url VARCHAR(200) NOT NULL DEFAULT '',
                registration_number VARCHAR(100) NOT NULL DEFAULT '',
                plan VARCHAR(20) NOT NULL DEFAULT 'basic',
                subscription_expires_at TIMESTAMP NULL,
                license_key VARCHAR(200) NOT NULL DEFAULT '',
                user_limit INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        ''',
        'medos_role': '''
            CREATE TABLE IF NOT EXISTS medos_role (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                permissions TEXT NOT NULL DEFAULT '{}',
                is_active BOOLEAN NOT NULL DEFAULT 1,
                hospital_id UUID REFERENCES medos_hospital(id),
                created_at TIMESTAMP NOT NULL
            )
        ''',
        'medos_userloginactivity': '''
            CREATE TABLE IF NOT EXISTS medos_userloginactivity (
                id UUID PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES auth_user(id),
                login_timestamp TIMESTAMP NOT NULL,
                ip_address VARCHAR(39) NULL,
                user_agent TEXT NOT NULL DEFAULT '',
                was_successful BOOLEAN NOT NULL DEFAULT 1,
                hospital_id UUID REFERENCES medos_hospital(id)
            )
        ''',
        'medos_systemactivitylog': '''
            CREATE TABLE IF NOT EXISTS medos_systemactivitylog (
                id UUID PRIMARY KEY,
                event_type VARCHAR(100) NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                author_name VARCHAR(255) NOT NULL DEFAULT '',
                hospital_id UUID REFERENCES medos_hospital(id),
                timestamp TIMESTAMP NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}'
            )
        ''',
        'medos_hospitaluserprofile': '''
            CREATE TABLE IF NOT EXISTS medos_hospitaluserprofile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE REFERENCES auth_user(id),
                hospital_id UUID REFERENCES medos_hospital(id),
                employee_id VARCHAR(50) UNIQUE,
                role_id INTEGER REFERENCES medos_role(id),
                department VARCHAR(100) NOT NULL DEFAULT '',
                phone VARCHAR(20) NOT NULL DEFAULT '',
                designation VARCHAR(100) NOT NULL DEFAULT '',
                must_change_password BOOLEAN NOT NULL DEFAULT 1,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        ''',
        'medos_storagemetrics': '''
            CREATE TABLE IF NOT EXISTS medos_storagemetrics (
                id UUID PRIMARY KEY,
                storage_used_gb REAL NOT NULL,
                storage_total_gb REAL NOT NULL,
                database_status VARCHAR(50) NOT NULL DEFAULT 'Healthy',
                last_backup TIMESTAMP NULL,
                next_backup TIMESTAMP NULL,
                recorded_at TIMESTAMP NOT NULL,
                hospital_id UUID REFERENCES medos_hospital(id)
            )
        ''',
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if connection.vendor == 'sqlite':
            with connection.cursor() as cursor:
                cursor.execute('PRAGMA foreign_keys = OFF')
                for sql in cls._UNMANAGED_SQL.values():
                    cursor.execute(sql)
                cursor.execute('PRAGMA foreign_keys = ON')


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def make_hospital(**kwargs) -> Hospital:
    defaults = dict(name="Test Hospital", slug="test-hospital")
    defaults.update(kwargs)
    return Hospital.objects.get_or_create(**defaults)[0]


def make_user(**kwargs) -> User:
    uid = str(uuid4())[:8]
    defaults = dict(
        username=f"user_{uid}",
        email=f"user_{uid}@test.com",
        is_staff=True,
        is_superuser=False,
    )
    defaults.update(kwargs)
    user = User.objects.create_user(**defaults)
    return user


# ═══════════════════════════════════════════════════════════════════════════════
#  OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════


class ReadOverviewTest(DashboardServiceTestBase):
    """Tests for DashboardService.read_overview()."""

    def test_returns_all_six_top_level_keys(self):
        result = read_overview()
        self.assertCountEqual(
            result.keys(),
            {'kpis', 'module_status', 'database_storage',
             'license_info', 'system_info', 'security_overview'},
        )

    # ── KPIs ─────────────────────────────────────────────────────────

    def test_kpis_count_users(self):
        make_user()
        make_user()
        make_user()
        result = read_overview()
        self.assertEqual(result['kpis']['total_users']['count'], 3)

    def test_kpis_user_growth(self):
        # User from 90 days ago — outside both 30-day windows
        long_ago = timezone.now() - timedelta(days=90)
        make_user(date_joined=long_ago)
        # User from 15 days ago — inside the current 30-day window
        recently = timezone.now() - timedelta(days=15)
        make_user(date_joined=recently)
        result = read_overview()
        growth = result['kpis']['total_users']['growth']
        self.assertIn('+1', growth)

    def test_kpis_active_users_percentage(self):
        u1 = make_user()
        make_user()
        UserLoginActivity.objects.create(
            user=u1, was_successful=True,
            login_timestamp=timezone.now() - timedelta(days=1),
        )
        result = read_overview()
        active = result['kpis']['active_users']
        self.assertEqual(active['count'], 1)
        self.assertAlmostEqual(active['percentage'], 50.0, places=1)

    def test_kpis_departments_count(self):
        hospital = make_hospital()
        Department.objects.create(name="Cardiology", code="CARD", hospital=hospital)
        Department.objects.create(name="Ortho", code="ORTH", hospital=hospital)
        result = read_overview()
        self.assertEqual(result['kpis']['departments']['count'], 2)

    def test_kpis_roles_count(self):
        hospital = make_hospital()
        Role.objects.create(name="Admin", hospital=hospital)
        Role.objects.create(name="Doctor", hospital=hospital)
        result = read_overview()
        self.assertEqual(result['kpis']['roles']['count'], 2)

    def test_kpis_storage_metrics_from_latest_record(self):
        StorageMetrics.objects.create(
            storage_used_gb=123.0, storage_total_gb=500.0,
            database_status="Healthy",
        )
        result = read_overview()
        storage = result['kpis']['storage_used']
        self.assertIn("123.00", storage['used'])
        self.assertIn("500.00", storage['total'])
        self.assertAlmostEqual(storage['percentage'], 24.6, places=1)

    def test_kpis_storage_metrics_when_no_records(self):
        result = read_overview()
        storage = result['kpis']['storage_used']
        self.assertEqual(storage['used'], "0.00 TB")
        self.assertEqual(storage['total'], "1.00 TB")
        self.assertEqual(storage['percentage'], 0.0)

    # ── Module status ─────────────────────────────────────────────────

    def test_module_status_list(self):
        AdminModule.objects.create(
            name="emr", label="EMR", status="Operational", is_critical=True,
        )
        AdminModule.objects.create(name="billing", label="Billing", status="Degraded")
        result = read_overview()
        modules = result['module_status']
        self.assertEqual(len(modules), 2)
        names = {m['name'] for m in modules}
        self.assertEqual(names, {'emr', 'billing'})

    def test_module_status_empty_when_no_modules(self):
        result = read_overview()
        self.assertEqual(result['module_status'], [])

    # ── Database storage ──────────────────────────────────────────────

    def test_database_storage_returns_latest(self):
        StorageMetrics.objects.create(
            storage_used_gb=50.0, storage_total_gb=200.0,
            database_status="Healthy",
            last_backup=timezone.now(),
        )
        result = read_overview()
        ds = result['database_storage']
        self.assertEqual(ds['database_status'], 'Healthy')
        self.assertEqual(ds['storage_used_gb'], 50.0)

    def test_database_storage_default_when_no_records(self):
        result = read_overview()
        ds = result['database_storage']
        self.assertEqual(ds['storage_used_gb'], 0)
        self.assertEqual(ds['database_status'], 'Unknown')

    # ── License info ──────────────────────────────────────────────────

    def test_license_info_returns_active_license(self):
        LicenseInfo.objects.create(
            edition="Enterprise", license_key="KEY-123",
            valid_from=date.today(), valid_till=date.today() + timedelta(days=365),
            is_active=True,
        )
        result = read_overview()
        self.assertIsNotNone(result['license_info'])
        self.assertEqual(result['license_info']['edition'], 'Enterprise')
        self.assertEqual(result['license_info']['license_key'], 'KEY-123')

    def test_license_info_none_when_no_active_license(self):
        result = read_overview()
        self.assertIsNone(result['license_info'])

    # ── System info ───────────────────────────────────────────────────

    def test_system_info_returns_expected_keys(self):
        result = read_overview()
        si = result['system_info']
        self.assertIn('django_version', si)
        self.assertIn('python_version', si)
        self.assertIn('debug_mode', si)
        self.assertIn('database', si)

    # ── Security overview ─────────────────────────────────────────────

    def test_security_overview_counts(self):
        u1 = make_user(is_superuser=True)
        make_user()
        make_user()
        UserLoginActivity.objects.create(
            user=u1, was_successful=True,
            login_timestamp=timezone.now() - timedelta(hours=1),
        )
        UserLoginActivity.objects.create(
            user=u1, was_successful=False,
            login_timestamp=timezone.now() - timedelta(minutes=30),
        )
        result = read_overview()
        sec = result['security_overview']
        self.assertEqual(sec['total_users'], 3)
        self.assertEqual(sec['admins'], 1)
        self.assertEqual(sec['recent_logins'], 1)
        self.assertEqual(sec['failed_logins'], 1)

    def test_security_overview_login_attempts_24h(self):
        u = make_user()
        now = timezone.now()
        UserLoginActivity.objects.create(
            user=u, login_timestamp=now - timedelta(hours=2),
        )
        UserLoginActivity.objects.create(
            user=u, login_timestamp=now - timedelta(hours=23),
        )
        result = read_overview()
        self.assertEqual(result['security_overview']['login_attempts_24h'], 2)


# ═══════════════════════════════════════════════════════════════════════════════
#  ACTIVITY
# ═══════════════════════════════════════════════════════════════════════════════


class ReadActivityTest(DashboardServiceTestBase):
    """Tests for DashboardService.read_activity()."""

    def test_returns_three_top_level_keys(self):
        result = read_activity()
        self.assertCountEqual(
            result.keys(),
            {'system_overview_chart', 'user_activity', 'audit_summary'},
        )

    # ── Chart ─────────────────────────────────────────────────────────

    def test_chart_has_seven_days(self):
        result = read_activity()
        chart = result['system_overview_chart']
        self.assertEqual(len(chart), 7)

    def test_chart_each_point_has_expected_fields(self):
        result = read_activity()
        point = result['system_overview_chart'][0]
        self.assertIn('date', point)
        self.assertIn('logins', point)
        self.assertIn('transactions', point)
        self.assertIn('errors', point)

    def test_chart_counts_logins_for_today(self):
        u = make_user()
        UserLoginActivity.objects.create(
            user=u, was_successful=True,
            login_timestamp=timezone.now(),
        )
        result = read_activity()
        today = date.today().isoformat()
        for point in result['system_overview_chart']:
            if point['date'] == today:
                self.assertEqual(point['logins'], 1)
                return
        self.fail("Today not found in chart")

    # ── User activity ─────────────────────────────────────────────────

    def test_user_activity_lists_top_users(self):
        u1 = make_user()
        u2 = make_user()
        for _ in range(5):
            UserLoginActivity.objects.create(
                user=u1, was_successful=True,
                login_timestamp=timezone.now() - timedelta(minutes=1),
            )
        UserLoginActivity.objects.create(
            user=u2, was_successful=True,
            login_timestamp=timezone.now(),
        )
        result = read_activity()
        users = result['user_activity']
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0]['username'], u1.username)

    # ── Audit summary ─────────────────────────────────────────────────

    def test_audit_summary_groups_by_event_type(self):
        SystemActivityLog.objects.create(event_type="user_login", description="x")
        SystemActivityLog.objects.create(event_type="user_login", description="y")
        SystemActivityLog.objects.create(
            event_type="hospital_onboarded", description="z",
        )
        result = read_activity()
        by_cat = result['audit_summary']['by_category']
        mapping = {c['category']: c['count'] for c in by_cat}
        self.assertEqual(mapping['user_login'], 2)
        self.assertEqual(mapping['hospital_onboarded'], 1)

    def test_audit_summary_total_logs(self):
        for i in range(5):
            SystemActivityLog.objects.create(
                event_type=f"event_{i}", description=str(i),
            )
        result = read_activity()
        self.assertEqual(result['audit_summary']['total_logs'], 5)

    def test_audit_summary_recent_has_up_to_10(self):
        for i in range(15):
            SystemActivityLog.objects.create(
                event_type=f"e{i}", description=str(i),
            )
        result = read_activity()
        self.assertLessEqual(len(result['audit_summary']['recent']), 10)


# ═══════════════════════════════════════════════════════════════════════════════
#  ALERTS
# ═══════════════════════════════════════════════════════════════════════════════


class ReadAlertsTest(DashboardServiceTestBase):
    """Tests for DashboardService.read_alerts()."""

    def test_returns_two_top_level_keys(self):
        result = read_alerts()
        self.assertCountEqual(
            result.keys(),
            {'system_alerts', 'recent_activities'},
        )

    # ── System alerts ─────────────────────────────────────────────────

    def test_system_alerts_only_unresolved(self):
        hospital = make_hospital()
        SystemActivityLog.objects.create(
            event_type="test", description="seed workaround",
        )
        from medos_internal.models import SystemAlert
        SystemAlert.objects.create(
            severity="critical", title="DB down", hospital=hospital,
        )
        SystemAlert.objects.create(
            severity="warning", title="Disk space",
            is_resolved=True, hospital=hospital,
        )
        result = read_alerts()
        titles = [a['title'] for a in result['system_alerts']]
        self.assertIn('DB down', titles)
        self.assertNotIn('Disk space', titles)

    def test_system_alerts_empty_when_all_resolved(self):
        from medos_internal.models import SystemAlert
        SystemAlert.objects.create(
            severity="info", title="All good", is_resolved=True,
        )
        result = read_alerts()
        self.assertEqual(result['system_alerts'], [])

    # ── Recent activities ─────────────────────────────────────────────

    def test_recent_activities_up_to_20(self):
        for i in range(25):
            SystemActivityLog.objects.create(
                event_type=f"ev{i}", description=str(i),
            )
        result = read_alerts()
        self.assertLessEqual(len(result['recent_activities']), 20)

    def test_recent_activities_includes_hospital_name(self):
        hospital = make_hospital(name="City Care")
        SystemActivityLog.objects.create(
            event_type="test", description="test", hospital=hospital,
        )
        result = read_alerts()
        self.assertEqual(
            result['recent_activities'][0]['hospital_name'], 'City Care',
        )

    def test_recent_activities_system_when_no_hospital(self):
        SystemActivityLog.objects.create(
            event_type="test", description="no hospital",
        )
        result = read_alerts()
        self.assertEqual(
            result['recent_activities'][0]['hospital_name'], 'System',
        )
