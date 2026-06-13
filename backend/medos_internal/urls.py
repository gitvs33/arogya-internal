"""URL configuration for the MedOS Internal Operations API."""
from django.urls import path, include
from . import views as internal_views

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────
    path('login/', internal_views.internal_login, name='internal-login'),

    # ── Hospital Management ───────────────────────────────────────────
    path('hospitals/', internal_views.hospital_list, name='internal-hospital-list'),
    path('hospitals/create/', internal_views.hospital_create, name='internal-hospital-create'),
    path('hospitals/<uuid:pk>/', internal_views.hospital_detail_get, name='internal-hospital-detail'),
    path('hospitals/<uuid:pk>/update/', internal_views.hospital_detail_update, name='internal-hospital-update'),
    path('hospitals/<uuid:pk>/activate/', internal_views.hospital_activate, name='internal-hospital-activate'),
    path('hospitals/<uuid:pk>/deactivate/', internal_views.hospital_deactivate, name='internal-hospital-deactivate'),
    path('hospitals/<uuid:pk>/impersonate/', internal_views.hospital_impersonate, name='internal-hospital-impersonate'),

    # ── Platform Stats ────────────────────────────────────────────────
    path('stats/', internal_views.platform_stats, name='internal-stats'),

    # ── Admin Dashboard (composite endpoints) ──────────────────────────
    path('admin/dashboard/overview/', internal_views.admin_overview, name='admin-overview'),
    path('admin/dashboard/activity/', internal_views.admin_activity, name='admin-activity'),
    path('admin/dashboard/alerts/', internal_views.admin_alerts, name='admin-alerts'),

    # ── Admin CRUD ViewSets ───────────────────────────────────────────
    path('admin/', include(internal_views.admin_router.urls)),
]
