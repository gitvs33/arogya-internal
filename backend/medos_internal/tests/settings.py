"""Test settings — overrides DB to SQLite so unmanaged model FKs work.

The main project's production DB is PostgreSQL, but for tests we use SQLite
because several managed models have ForeignKey constraints to the unmanaged
Hospital model (whose table doesn't exist in the test database).
"""
from medos_internal_project.settings import *  # noqa: F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}
