"""Test user management service — admin user creation workflow.

Uses SQLite with the established pattern: raw CREATE TABLE for unmanaged
models, direct service function calls, and ORM assertions on created records.
"""
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone

from medos_internal.models import Hospital, Role, HospitalUserProfile
from medos_internal.services.user_management import create_admin_user

User = get_user_model()


class UserManagementTestBase(TestCase):
    """Set up unmanaged tables needed by user management tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if connection.vendor == 'sqlite':
            with connection.cursor() as cursor:
                cursor.execute('PRAGMA foreign_keys = OFF')

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


def make_hospital(**kwargs):
    defaults = dict(
        name="Test Hospital",
        slug="test-hospital",
        plan="enterprise",
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )
    defaults.update(kwargs)
    if 'id' not in defaults:
        defaults['id'] = uuid4().hex
    return Hospital.objects.create(**defaults)


def make_role(hospital, **kwargs):
    defaults = dict(name="Admin", permissions='{"admin": true}',
                    is_active=True, created_at=timezone.now())
    defaults.update(kwargs)
    return Role.objects.create(hospital=hospital, **defaults)


class CreateAdminUserTest(UserManagementTestBase):

    def test_creates_user_and_profile(self):
        hospital = make_hospital()
        result = create_admin_user(
            username="dr.smith",
            email="smith@test.com",
            password="secure123",
            hospital_id=hospital.id,
        )
        self.assertEqual(result['username'], "dr.smith")
        self.assertEqual(result['email'], "smith@test.com")
        self.assertTrue(result['is_active'])
        self.assertIsNotNone(result['id'])
        # Verify DB record
        user = User.objects.get(username="dr.smith")
        self.assertTrue(user.check_password("secure123"))
        profile = HospitalUserProfile.objects.get(user=user)
        self.assertEqual(profile.user, user)
        self.assertIsNotNone(profile.hospital_id)

    def test_creates_with_role(self):
        hospital = make_hospital()
        role = make_role(hospital)
        result = create_admin_user(
            username="dr.jane",
            email="jane@test.com",
            password="pass1234",
            hospital_id=hospital.id,
            role_id=role.id,
        )
        self.assertEqual(result['role'], "Admin")
        profile = HospitalUserProfile.objects.get(user__username="dr.jane")
        self.assertEqual(profile.role_id, role.id)

    def test_no_role_returns_none(self):
        hospital = make_hospital()
        result = create_admin_user(
            username="no.role",
            email="norole@test.com",
            password="pass1234",
            hospital_id=hospital.id,
        )
        self.assertIsNone(result['role'])

    def test_employee_id_in_result(self):
        hospital = make_hospital()
        result = create_admin_user(
            username="emp.test",
            email="emp@test.com",
            password="pass1234",
            hospital_id=hospital.id,
            employee_id="EMP-001",
        )
        self.assertEqual(result['employee_id'], "EMP-001")

    def test_full_name_maps_correctly(self):
        hospital = make_hospital()
        result = create_admin_user(
            username="john.doe",
            email="john@test.com",
            password="pass1234",
            hospital_id=hospital.id,
            first_name="John",
            last_name="Doe",
        )
        self.assertEqual(result['first_name'], "John")
        self.assertEqual(result['last_name'], "Doe")

    def test_last_login_is_none_for_new_user(self):
        hospital = make_hospital()
        result = create_admin_user(
            username="new.user",
            email="new@test.com",
            password="pass1234",
            hospital_id=hospital.id,
        )
        self.assertIsNone(result['last_login'])

    def test_raises_integrity_error_on_duplicate_username(self):
        hospital = make_hospital()
        create_admin_user(
            username="duplicate",
            email="first@test.com",
            password="pass1234",
            hospital_id=hospital.id,
        )
        with self.assertRaises(IntegrityError):
            create_admin_user(
                username="duplicate",
                email="second@test.com",
                password="pass1234",
                hospital_id=hospital.id,
            )

    def test_raises_integrity_error_on_duplicate_employee_id(self):
        hospital = make_hospital()
        create_admin_user(
            username="emp.a",
            email="empa@test.com",
            password="pass1234",
            hospital_id=hospital.id,
            employee_id="EMP-DUP",
        )
        with self.assertRaises(IntegrityError):
            create_admin_user(
                username="emp.b",
                email="empb@test.com",
                password="pass1234",
                hospital_id=hospital.id,
                employee_id="EMP-DUP",
            )

    def test_raises_hospital_does_not_exist(self):
        fake_id = uuid4().hex
        with self.assertRaises(Hospital.DoesNotExist):
            create_admin_user(
                username="ghost",
                email="ghost@test.com",
                password="pass1234",
                hospital_id=fake_id,
            )

    def test_raises_role_does_not_exist(self):
        hospital = make_hospital()
        with self.assertRaises(Role.DoesNotExist):
            create_admin_user(
                username="bad.role",
                email="badrole@test.com",
                password="pass1234",
                hospital_id=hospital.id,
                role_id=99999,
            )

    def test_department_and_designation_passed_through(self):
        hospital = make_hospital()
        result = create_admin_user(
            username="dept.test",
            email="dept@test.com",
            password="pass1234",
            hospital_id=hospital.id,
            department="Cardiology",
            designation="Senior Doctor",
        )
        profile = HospitalUserProfile.objects.get(user__username="dept.test")
        self.assertEqual(profile.department, "Cardiology")
        self.assertEqual(profile.designation, "Senior Doctor")

    def test_must_change_password_defaults_to_true(self):
        hospital = make_hospital()
        create_admin_user(
            username="changeme",
            email="changeme@test.com",
            password="pass1234",
            hospital_id=hospital.id,
        )
        profile = HospitalUserProfile.objects.get(user__username="changeme")
        self.assertTrue(profile.must_change_password)

    def test_hospital_name_in_result(self):
        hospital = make_hospital(name="City Care", slug="city-care")
        result = create_admin_user(
            username="city.admin",
            email="cityadmin@test.com",
            password="pass1234",
            hospital_id=hospital.id,
        )
        self.assertEqual(result['hospital_name'], "City Care")

    def test_date_joined_is_set(self):
        hospital = make_hospital()
        result = create_admin_user(
            username="date.test",
            email="date@test.com",
            password="pass1234",
            hospital_id=hospital.id,
        )
        self.assertIsNotNone(result['date_joined'])
