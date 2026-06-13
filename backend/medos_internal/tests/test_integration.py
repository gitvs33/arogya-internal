"""Integration tests — exercise the full HTTP-to-DB stack.

These tests use DRF's APIClient to verify that URL routing, authentication,
permissions, views, serializers, services, and models all work together.

Run with:
    cd backend
    python manage.py test medos_internal.tests.test_integration --settings=medos_internal.tests.settings --verbosity=2
"""
from datetime import timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from medos_internal.models import (
    Hospital, Role, HospitalUserProfile, SystemActivityLog,
)
from medos_internal.auth import token_is_expired

User = get_user_model()

# ── Shared SQL for unmanaged tables ──────────────────────────────────────────

UNMANAGED_TABLES = [
    ("""CREATE TABLE IF NOT EXISTS medos_hospital (
        id CHAR(32) NOT NULL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        slug VARCHAR(50) NOT NULL UNIQUE,
        plan VARCHAR(20) NOT NULL DEFAULT 'basic',
        is_active INTEGER NOT NULL DEFAULT 1,
        address TEXT NOT NULL DEFAULT '',
        phone VARCHAR(20) NOT NULL DEFAULT '',
        email VARCHAR(254) NOT NULL DEFAULT '',
        logo_url VARCHAR(200) NOT NULL DEFAULT '',
        registration_number VARCHAR(100) NOT NULL DEFAULT '',
        license_key VARCHAR(200) NOT NULL DEFAULT '',
        user_limit INTEGER NOT NULL DEFAULT 0,
        subscription_expires_at DATETIME NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL
    )"""),
    ("""CREATE TABLE IF NOT EXISTS medos_role (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(50) NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        permissions TEXT NOT NULL DEFAULT '{}',
        is_active INTEGER NOT NULL DEFAULT 1,
        hospital_id CHAR(32) NULL,
        created_at DATETIME NOT NULL
    )"""),
    ("""CREATE TABLE IF NOT EXISTS medos_hospitaluserprofile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        hospital_id CHAR(32) NULL,
        role_id INTEGER NULL,
        employee_id VARCHAR(50) NULL UNIQUE,
        department VARCHAR(100) NOT NULL DEFAULT '',
        phone VARCHAR(20) NOT NULL DEFAULT '',
        designation VARCHAR(100) NOT NULL DEFAULT '',
        must_change_password INTEGER NOT NULL DEFAULT 1,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL
    )"""),
    ("""CREATE TABLE IF NOT EXISTS medos_patient (
        id CHAR(32) NOT NULL PRIMARY KEY,
        hospital_id CHAR(32) NULL,
        created_at DATETIME NOT NULL
    )"""),
    ("""CREATE TABLE IF NOT EXISTS medos_encounter (
        id CHAR(32) NOT NULL PRIMARY KEY,
        hospital_id CHAR(32) NULL,
        created_at DATETIME NOT NULL
    )"""),
    ("""CREATE TABLE IF NOT EXISTS medos_invoice (
        id CHAR(32) NOT NULL PRIMARY KEY,
        hospital_id CHAR(32) NULL,
        created_at DATETIME NOT NULL
    )"""),
    ("""CREATE TABLE IF NOT EXISTS medos_systemactivitylog (
        id CHAR(32) NOT NULL PRIMARY KEY,
        event_type VARCHAR(100) NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        author_name VARCHAR(255) NOT NULL DEFAULT '',
        hospital_id CHAR(32) NULL,
        timestamp DATETIME NOT NULL,
        metadata TEXT NOT NULL DEFAULT '{}'
    )"""),
]


class IntegrationTestBase(TestCase):
    """Set up unmanaged tables and a staff user with token."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = OFF')
            for sql in UNMANAGED_TABLES:
                cursor.execute(sql)

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

        self.client = APIClient()
        self.staff_user = User.objects.create_user(
            username='opsadmin',
            password='test123',
            is_staff=True,
        )
        self.token, _ = Token.objects.get_or_create(user=self.staff_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')


# ═══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


class DashboardIntegrationTest(IntegrationTestBase):

    def test_platform_stats_returns_kpis(self):
        resp = self.client.get('/api/internal/stats/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('total_hospitals', data)
        self.assertIn('active_hospitals', data)
        self.assertIn('total_staff', data)
        self.assertIn('total_patients', data)
        self.assertIn('total_encounters', data)
        self.assertIn('total_invoices', data)
        self.assertIn('patients_30d', data)
        self.assertIn('onboarding_30d', data)

    def test_admin_dashboard_overview(self):
        resp = self.client.get('/api/internal/admin/dashboard/overview/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('kpis', data)
        self.assertIn('module_status', data)
        self.assertIn('database_storage', data)
        self.assertIn('system_info', data)
        self.assertIn('security_overview', data)

    def test_admin_dashboard_activity(self):
        resp = self.client.get('/api/internal/admin/dashboard/activity/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('system_overview_chart', data)
        self.assertIn('user_activity', data)
        self.assertIn('audit_summary', data)

    def test_admin_dashboard_alerts(self):
        resp = self.client.get('/api/internal/admin/dashboard/alerts/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('system_alerts', data)
        self.assertIn('recent_activities', data)


# ═══════════════════════════════════════════════════════════════════════════════
#  HOSPITAL MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════


class HospitalIntegrationTest(IntegrationTestBase):

    def test_hospital_list_returns_empty(self):
        resp = self.client.get('/api/internal/hospitals/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['results'], [])
        self.assertEqual(data['count'], 0)

    def test_hospital_create_and_list(self):
        create_resp = self.client.post('/api/internal/hospitals/create/', {
            'name': 'Test Hospital',
            'slug': 'test-hospital',
            'plan': 'enterprise',
            'admin_name': 'Dr Admin',
            'admin_email': 'admin@test.com',
            'admin_password': 'secure123',
            'address': '123 Main St',
        }, format='json')
        self.assertEqual(create_resp.status_code, 201)
        created = create_resp.json()
        self.assertEqual(created['name'], 'Test Hospital')
        self.assertEqual(created['plan'], 'enterprise')
        self.assertTrue(created['is_active'])

        list_resp = self.client.get('/api/internal/hospitals/')
        self.assertEqual(list_resp.status_code, 200)
        data = list_resp.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['name'], 'Test Hospital')
        self.assertEqual(data['count'], 1)

    def test_hospital_create_validates_required_fields(self):
        resp = self.client.post('/api/internal/hospitals/create/', {}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_hospital_create_creates_admin_user_and_role(self):
        self.client.post('/api/internal/hospitals/create/', {
            'name': 'Test Hospital',
            'slug': 'test-hospital',
            'plan': 'basic',
            'admin_name': 'Dr John Smith',
            'admin_email': 'admin@test.com',
            'admin_password': 'secure123',
        }, format='json')

        admin_user = User.objects.filter(email='admin@test.com').first()
        self.assertIsNotNone(admin_user)
        self.assertEqual(admin_user.first_name, 'Dr')
        self.assertEqual(admin_user.last_name, 'John Smith')

        hospital = Hospital.objects.get(slug='test-hospital')
        profile = HospitalUserProfile.objects.filter(hospital=hospital).first()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.role.name, 'Admin')

        log = SystemActivityLog.objects.filter(
            event_type='hospital_onboarded',
            hospital=hospital,
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.author_name, 'opsadmin')

    def test_hospital_detail(self):
        self.client.post('/api/internal/hospitals/create/', {
            'name': 'Test Hospital',
            'slug': 'test-hospital',
            'plan': 'enterprise',
            'admin_name': 'Dr Admin',
            'admin_email': 'admin@test.com',
            'admin_password': 'secure123',
        }, format='json')

        hospital = Hospital.objects.get(slug='test-hospital')
        resp = self.client.get(f'/api/internal/hospitals/{hospital.pk}/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['name'], 'Test Hospital')
        self.assertIn('stats', data)
        self.assertIn('admin', data)
        self.assertIn('staff_breakdown', data)


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════════════════════════════════


class AuthIntegrationTest(IntegrationTestBase):

    def test_login_returns_token(self):
        resp = self.client.post('/api/internal/login/', {
            'username': 'opsadmin',
            'password': 'test123',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('token', data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'opsadmin')

    def test_invalid_login_returns_401(self):
        resp = self.client.post('/api/internal/login/', {
            'username': 'opsadmin',
            'password': 'wrong',
        }, format='json')
        self.assertEqual(resp.status_code, 401)

    def test_unauthenticated_returns_401(self):
        self.client.credentials()
        resp = self.client.get('/api/internal/stats/')
        self.assertEqual(resp.status_code, 401)

    def test_non_staff_returns_403(self):
        non_staff = User.objects.create_user(
            username='regular', password='test123', is_staff=False,
        )
        token = Token.objects.create(user=non_staff)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        resp = self.client.get('/api/internal/stats/')
        self.assertEqual(resp.status_code, 403)

    def test_expired_token_is_rejected(self):
        self.token.created = timezone.now() - timedelta(days=8)
        self.token.save(update_fields=['created'])

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        resp = self.client.get('/api/internal/stats/')
        self.assertEqual(resp.status_code, 401)
        self.assertIn('expired', resp.json().get('detail', '').lower())

    def test_token_is_expired_helper(self):
        self.assertFalse(token_is_expired(self.token))

        self.token.created = timezone.now() - timedelta(days=8)
        self.assertTrue(token_is_expired(self.token))
