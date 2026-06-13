"""Test hospital detail service — single-hospital stats, staff, admin queries.

Uses SQLite with the established pattern: raw CREATE TABLE for unmanaged
models, PRAGMA foreign_keys = OFF, direct service function calls with
plain dict assertions.
"""
from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.utils import timezone

from medos_internal.models import Hospital, Role, HospitalUserProfile
from medos_internal.services.hospital_detail import read_hospital_detail

User = get_user_model()


class HospitalDetailTestBase(TestCase):
    """Set up unmanaged tables needed by hospital detail tests."""

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

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS medos_patient (
                        id CHAR(32) NOT NULL PRIMARY KEY,
                        hospital_id CHAR(32) NULL,
                        created_at DATETIME NOT NULL
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS medos_encounter (
                        id CHAR(32) NOT NULL PRIMARY KEY,
                        hospital_id CHAR(32) NULL,
                        created_at DATETIME NOT NULL
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS medos_invoice (
                        id CHAR(32) NOT NULL PRIMARY KEY,
                        hospital_id CHAR(32) NULL,
                        created_at DATETIME NOT NULL
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
    defaults = dict(name="Doctor", permissions="{}", is_active=True, created_at=timezone.now())
    defaults.update(kwargs)
    return Role.objects.create(hospital=hospital, **defaults)


def make_admin_user(hospital, role=None, **kwargs):
    uid = uuid4().hex[:8]
    user = User.objects.create_user(
        username=f"admin_{uid}",
        email=f"admin_{uid}@test.com",
        password="test123",
        **{k: v for k, v in kwargs.items() if k in ('first_name', 'last_name')},
    )
    profile = HospitalUserProfile.objects.create(
        user=user,
        hospital=hospital,
        role=role,
        is_active=True,
        created_at=timezone.now(),
        updated_at=timezone.now(),
        **{k: v for k, v in kwargs.items() if k in ('employee_id', 'department', 'designation')},
    )
    return user, profile


def insert_patient(hospital, **kwargs):
    defaults = dict(id=uuid4().hex, created_at=timezone.now())
    defaults.update(kwargs)
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO medos_patient (id, hospital_id, created_at) VALUES (%s, %s, %s)",
            [defaults['id'], hospital.id, defaults['created_at']],
        )


def insert_encounter(hospital, **kwargs):
    defaults = dict(id=uuid4().hex, created_at=timezone.now())
    defaults.update(kwargs)
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO medos_encounter (id, hospital_id, created_at) VALUES (%s, %s, %s)",
            [defaults['id'], hospital.id, defaults['created_at']],
        )


def insert_invoice(hospital, **kwargs):
    defaults = dict(id=uuid4().hex, created_at=timezone.now())
    defaults.update(kwargs)
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO medos_invoice (id, hospital_id, created_at) VALUES (%s, %s, %s)",
            [defaults['id'], hospital.id, defaults['created_at']],
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  STATS
# ═══════════════════════════════════════════════════════════════════════════════


class StatsTest(HospitalDetailTestBase):
    """Tests for the stats section of read_hospital_detail()."""

    def test_counts_patients(self):
        hospital = make_hospital()
        insert_patient(hospital)
        insert_patient(hospital)
        result = read_hospital_detail(hospital)
        self.assertEqual(result['stats']['patients'], 2)

    def test_counts_encounters_within_30_days(self):
        hospital = make_hospital()
        insert_encounter(hospital, created_at=timezone.now() - timedelta(days=5))
        insert_encounter(hospital, created_at=timezone.now() - timedelta(days=40))
        result = read_hospital_detail(hospital)
        self.assertEqual(result['stats']['encounters_30d'], 1)

    def test_counts_invoices(self):
        hospital = make_hospital()
        insert_invoice(hospital)
        insert_invoice(hospital)
        insert_invoice(hospital)
        result = read_hospital_detail(hospital)
        self.assertEqual(result['stats']['invoices'], 3)

    def test_all_stats_zero_when_no_data(self):
        hospital = make_hospital()
        result = read_hospital_detail(hospital)
        self.assertEqual(result['stats']['patients'], 0)
        self.assertEqual(result['stats']['encounters_30d'], 0)
        self.assertEqual(result['stats']['invoices'], 0)

    def test_counts_only_own_hospital(self):
        h1 = make_hospital(name="A", slug="a")
        h2 = make_hospital(name="B", slug="b")
        insert_patient(h1)
        insert_patient(h1)
        insert_patient(h2)
        result = read_hospital_detail(h1)
        self.assertEqual(result['stats']['patients'], 2)


# ═══════════════════════════════════════════════════════════════════════════════
#  STAFF BREAKDOWN
# ═══════════════════════════════════════════════════════════════════════════════


class StaffBreakdownTest(HospitalDetailTestBase):
    """Tests for the staff_breakdown section."""

    def test_returns_total_count(self):
        hospital = make_hospital()
        role = make_role(hospital)
        make_admin_user(hospital, role=role)
        make_admin_user(hospital, role=role,
                        first_name="Jane", last_name="Doe")
        result = read_hospital_detail(hospital)
        self.assertEqual(result['staff_breakdown']['total'], 2)

    def test_groups_by_role_name(self):
        hospital = make_hospital()
        doctor = make_role(hospital, name="Doctor")
        nurse = make_role(hospital, name="Nurse")
        make_admin_user(hospital, role=doctor)
        make_admin_user(hospital, role=doctor,
                        first_name="Jane", last_name="Doe")
        make_admin_user(hospital, role=nurse)
        result = read_hospital_detail(hospital)
        by_role = result['staff_breakdown']['by_role']
        self.assertEqual(by_role.get('Doctor'), 2)
        self.assertEqual(by_role.get('Nurse'), 1)

    def test_assigns_unassigned_when_role_is_null(self):
        hospital = make_hospital()
        make_admin_user(hospital, role=None)
        result = read_hospital_detail(hospital)
        by_role = result['staff_breakdown']['by_role']
        self.assertEqual(by_role.get('Unassigned'), 1)

    def test_excludes_inactive_profiles(self):
        hospital = make_hospital()
        doctor = make_role(hospital, name="Doctor")
        make_admin_user(hospital, role=doctor)
        uid = uuid4().hex[:8]
        user = User.objects.create_user(
            username=f"inactive_{uid}", password="test123",
        )
        HospitalUserProfile.objects.create(
            user=user, hospital=hospital, role=doctor,
            is_active=False,
            created_at=timezone.now(), updated_at=timezone.now(),
        )
        result = read_hospital_detail(hospital)
        self.assertEqual(result['staff_breakdown']['total'], 1)

    def test_empty_breakdown_when_no_profiles(self):
        hospital = make_hospital()
        result = read_hospital_detail(hospital)
        self.assertEqual(result['staff_breakdown']['total'], 0)
        self.assertEqual(result['staff_breakdown']['by_role'], {})


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN
# ═══════════════════════════════════════════════════════════════════════════════


class AdminInfoTest(HospitalDetailTestBase):
    """Tests for the admin section of read_hospital_detail()."""

    def test_returns_admin_info(self):
        hospital = make_hospital()
        admin_role = make_role(hospital, name="Admin")
        user, _ = make_admin_user(
            hospital, role=admin_role,
            first_name="John", last_name="Smith",
            employee_id="EMP-001",
        )
        result = read_hospital_detail(hospital)
        self.assertIsNotNone(result['admin'])
        self.assertEqual(result['admin']['email'], user.email)
        self.assertEqual(result['admin']['first_name'], 'John')
        self.assertEqual(result['admin']['last_name'], 'Smith')
        self.assertEqual(result['admin']['employee_id'], 'EMP-001')

    def test_admin_is_none_when_no_admin_role(self):
        hospital = make_hospital()
        doctor_role = make_role(hospital, name="Doctor")
        make_admin_user(hospital, role=doctor_role)
        result = read_hospital_detail(hospital)
        self.assertIsNone(result['admin'])

    def test_admin_is_none_when_no_profiles(self):
        hospital = make_hospital()
        result = read_hospital_detail(hospital)
        self.assertIsNone(result['admin'])

    def test_picks_first_admin_when_multiple(self):
        hospital = make_hospital()
        admin_role = make_role(hospital, name="Admin")
        user1, _ = make_admin_user(
            hospital, role=admin_role,
            first_name="Primary", last_name="Admin",
        )
        make_admin_user(
            hospital, role=admin_role,
            first_name="Secondary", last_name="Admin",
        )
        result = read_hospital_detail(hospital)
        self.assertIsNotNone(result['admin'])
        # Should return the first match (oldest profile)
        self.assertEqual(result['admin']['first_name'], 'Primary')

    def test_admin_username_fallback(self):
        hospital = make_hospital()
        admin_role = make_role(hospital, name="Admin")
        uid = uuid4().hex[:8]
        user = User.objects.create_user(
            username=f"super_{uid}", email=f"super_{uid}@test.com",
            password="test123",
        )
        HospitalUserProfile.objects.create(
            user=user, hospital=hospital, role=admin_role,
            is_active=True,
            created_at=timezone.now(), updated_at=timezone.now(),
        )
        result = read_hospital_detail(hospital)
        self.assertEqual(result['admin']['username'], f"super_{uid}")
