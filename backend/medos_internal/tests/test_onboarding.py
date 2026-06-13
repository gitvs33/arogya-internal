"""Test hospital onboarding service — the transactional create workflow.

Uses SQLite with the same pattern as test_dashboard_service.py to set up
unmanaged tables with column types matching the actual model definitions.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError

from medos_internal.models import (
    Hospital, Role, HospitalUserProfile, SystemActivityLog,
)
from medos_internal.services.hospital_onboarding import onboard_hospital

User = get_user_model()


class OnboardingTestBase(TestCase):
    """Set up unmanaged tables with schemas matching the Django models."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = OFF')

            # Hospital — id is UUIDField, stored as CHAR(32)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS medos_hospital (
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
                )
            """)

            # Role — id is BigAutoField
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS medos_role (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(50) NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    permissions TEXT NOT NULL DEFAULT '{}',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    hospital_id CHAR(32) NULL,
                    created_at DATETIME NOT NULL
                )
            """)

            # HospitalUserProfile — id is BigAutoField
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS medos_hospitaluserprofile (
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
                )
            """)

            # SystemActivityLog — id is UUIDField
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS medos_systemactivitylog (
                    id CHAR(32) NOT NULL PRIMARY KEY,
                    event_type VARCHAR(100) NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    author_name VARCHAR(255) NOT NULL DEFAULT '',
                    hospital_id CHAR(32) NULL,
                    timestamp DATETIME NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}'
                )
            """)

    def setUp(self):
        self.performed_by = User.objects.create_user(
            username='opsadmin', password='test123', is_staff=True,
        )


class OnboardHospitalTest(OnboardingTestBase):

    def test_creates_hospital(self):
        hospital = onboard_hospital(
            name='Test Hospital',
            slug='test-hospital',
            plan='enterprise',
            admin_name='Dr Smith',
            admin_email='admin@test.com',
            admin_password='secure123',
            address='123 Main St',
            phone='555-0100',
            email='info@test.com',
            performed_by=self.performed_by,
        )
        self.assertEqual(hospital.name, 'Test Hospital')
        self.assertEqual(hospital.slug, 'test-hospital')
        self.assertEqual(hospital.plan, 'enterprise')
        self.assertTrue(hospital.is_active)

    def test_creates_admin_user(self):
        hospital = onboard_hospital(
            name='Test Hospital',
            slug='test-hospital',
            plan='basic',
            admin_name='Dr Smith',
            admin_email='admin@test.com',
            admin_password='secure123',
            performed_by=self.performed_by,
        )
        admin_profile = HospitalUserProfile.objects.filter(hospital=hospital).first()
        self.assertIsNotNone(admin_profile)
        user = admin_profile.user
        self.assertEqual(user.email, 'admin@test.com')
        self.assertEqual(user.first_name, 'Dr')
        self.assertEqual(user.last_name, 'Smith')
        self.assertFalse(user.is_staff)

    def test_creates_admin_role(self):
        hospital = onboard_hospital(
            name='Test Hospital',
            slug='test-hospital',
            plan='basic',
            admin_name='Admin',
            admin_email='admin@test.com',
            admin_password='secure123',
            performed_by=self.performed_by,
        )
        admin_profile = HospitalUserProfile.objects.filter(hospital=hospital).first()
        self.assertIsNotNone(admin_profile)
        self.assertIsNotNone(admin_profile.role)
        self.assertEqual(admin_profile.role.name, 'Admin')
        self.assertIn('admin', admin_profile.role.permissions)

    def test_logs_onboarding_activity(self):
        hospital = onboard_hospital(
            name='Test Hospital',
            slug='test-hospital',
            plan='basic',
            admin_name='Admin',
            admin_email='admin@test.com',
            admin_password='secure123',
            performed_by=self.performed_by,
        )
        log = SystemActivityLog.objects.filter(
            event_type='hospital_onboarded',
            hospital=hospital,
        ).first()
        self.assertIsNotNone(log)
        self.assertIn('Test Hospital', log.description)
        self.assertEqual(log.author_name, 'opsadmin')

    def test_employee_id_format(self):
        hospital = onboard_hospital(
            name='Test Hospital',
            slug='test-hospital',
            plan='basic',
            admin_name='Admin',
            admin_email='admin@test.com',
            admin_password='secure123',
            performed_by=self.performed_by,
        )
        profile = HospitalUserProfile.objects.filter(hospital=hospital).first()
        self.assertIsNotNone(profile)
        self.assertTrue(profile.employee_id.startswith('HOSP-TEST'))
        self.assertTrue(profile.must_change_password)

    def test_duplicate_slug_raises_integrity_error(self):
        onboard_hospital(
            name='First',
            slug='same-slug',
            plan='basic',
            admin_name='Admin',
            admin_email='a@test.com',
            admin_password='pass',
            performed_by=self.performed_by,
        )
        with self.assertRaises(IntegrityError):
            onboard_hospital(
                name='Second',
                slug='same-slug',
                plan='basic',
                admin_name='Admin',
                admin_email='b@test.com',
                admin_password='pass',
                performed_by=self.performed_by,
            )

    def test_rolls_back_on_failure(self):
        """If the transaction fails, no partial data should remain."""
        slug = 'rollback-test'

        onboard_hospital(
            name='First',
            slug=slug,
            plan='basic',
            admin_name='Admin',
            admin_email='first@test.com',
            admin_password='pass',
            performed_by=self.performed_by,
        )

        hospital_count_before = Hospital.objects.count()
        user_count_before = User.objects.count()

        try:
            onboard_hospital(
                name='Second',
                slug=slug,
                plan='basic',
                admin_name='Admin',
                admin_email='second@test.com',
                admin_password='pass',
                performed_by=self.performed_by,
            )
        except IntegrityError:
            pass

        self.assertEqual(Hospital.objects.count(), hospital_count_before)
        self.assertEqual(User.objects.count(), user_count_before)

    def test_handles_single_word_admin_name(self):
        hospital = onboard_hospital(
            name='Test',
            slug='test',
            plan='basic',
            admin_name='Mono',
            admin_email='mono@test.com',
            admin_password='pass',
            performed_by=self.performed_by,
        )
        profile = HospitalUserProfile.objects.filter(hospital=hospital).first()
        user = profile.user
        self.assertEqual(user.first_name, 'Mono')
        self.assertEqual(user.last_name, '')

    def test_handles_multi_word_admin_name(self):
        hospital = onboard_hospital(
            name='Test',
            slug='test',
            plan='basic',
            admin_name='Dr John Smith Jr',
            admin_email='john@test.com',
            admin_password='pass',
            performed_by=self.performed_by,
        )
        profile = HospitalUserProfile.objects.filter(hospital=hospital).first()
        user = profile.user
        self.assertEqual(user.first_name, 'Dr')
        self.assertEqual(user.last_name, 'John Smith Jr')
