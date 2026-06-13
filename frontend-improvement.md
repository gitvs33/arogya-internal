# MedOS Frontend Architecture & Backend Correspondence

> All backend architecture cleanups and how they relate to the two frontends.
> Covers Rounds 1–3 of architecture improvements.

---

## Table of Contents

1. [Two-Project Architecture](#two-project-architecture)
2. [API Surface Area](#api-surface-area)
3. [Frontend-Backend Correspondence](#frontend-backend-correspondence)
4. [Internal Ops Frontend Architecture](#internal-ops-frontend-architecture)
5. [Backend Cleanups Summary](#backend-cleanups-summary)
6. [API Contract Observations](#api-contract-observations)
7. [Database Sharing Model](#database-sharing-model)

---

## Two-Project Architecture

MedOS runs as **two separate Django projects** sharing one PostgreSQL database.

```
┌──────────────────────────────────────────────────────────────────┐
│                      PostgreSQL Database                         │
│   (medos_hospital, medos_patient, medos_encounter,              │
│    medos_invoice, medos_role, medos_hospitaluserprofile, ...)    │
└──────────────────────┬──────────────────────────┬────────────────┘
                       │                          │
                       ▼                          ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│  medos/backend/ (port 8000)  │  │  medos_internal_frontend/   │
│                              │  │  backend/ (port 8001)        │
│  Python Django REST API      │  │  Python Django REST API      │
│  Supabase + Token Auth       │  │  Token Auth (is_staff only)  │
│                              │  │                              │
│  medos/frontend/ (port 5173) │  │  frontend/ (port 5175)       │
│  React + Vite + Tailwind     │  │  React + Vite + Tailwind     │
│                              │  │                              │
│  ─── Hospital Staff UI ───   │  │  ─── Internal Ops UI ───     │
│  Patients, Encounters,       │  │  Hospitals management,       │
│  Billing, Lab, TeleICU,      │  │  Platform Stats,             │
│  A.I Scribe, Pharmacy, etc.  │  │  Hospital CRUD,              │
│                              │  │  Activate/Deactivate,        │
│                              │  │  Impersonation,              │
│                              │  │  Admin Dashboard             │
└──────────────────────────────┘  └──────────────────────────────┘
```

### Key difference from single-project design

The backend was monolithic. After the split:

- **medos/backend/** serves hospital staff (doctors, nurses, lab techs)
- **medos_internal_frontend/backend/** serves ops staff (your company)

Both point to the **same PostgreSQL database** but have separate:

| Aspect | medos/ | medos_internal_frontend/ |
|--------|-------|--------------------------|
| Auth | Supabase + local fallback | Token (DRF) |
| Port | 8000 | 8001 |
| Frontend | 5173 | 5175 |
| Users | Hospital staff (is_staff=False) | Ops staff (is_staff=True) |
| Models | All ~50 models | Subset + admin models |
| Migrations | Owns canonical schema | Managed models via `db_table` |

---

## API Surface Area

### medos/ (port 8000) — Hospital Staff API

All endpoints under `/api/` (configured in `medos/urls.py`).

```python
router.register(r'patients', ...)             # Patient CRUD
router.register(r'insurance', ...)            # Insurance CRUD
router.register(r'encounters', ...)           # Encounter CRUD
router.register(r'sync', ...)                 # Offline sync
router.register(r'ddi', ...)                  # Drug-drug interaction
router.register(r'invoices', ...)             # Invoicing
router.register(r'alerts', ...)               # Medical alerts
router.register(r'lab-results', ...)          # Clinical lab results
router.register(r'allergies', ...)            # Allergies
router.register(r'diagnoses', ...)            # Diagnoses
router.register(r'orders', ...)               # Service orders
router.register(r'imaging', ...)              # Imaging
router.register(r'documents', ...)            # Patient documents
router.register(r'care-plans', ...)           # Care plans
router.register(r'payments', ...)             # Payments
router.register(r'refunds', ...)              # Refunds
router.register(r'claims', ...)              # Insurance claims

router.register(r'lab-panels', ...)           # Test panel catalog
router.register(r'lab-orders', ...)           # Lab order lifecycle
router.register(r'lab-parameter-results', ...) # Per-parameter results
router.register(r'lab-documents', ...)        # Lab documents
router.register(r'lab-qc', ...)               # QC audit trail
router.register(r'lab-inventory', ...)        # Lab inventory
router.register(r'lab-alerts', ...)           # Lab critical alerts

path('api/dashboard/', ...)                   # Hospital dashboard KPI
path('api/billing/dashboard/', ...)           # Billing dashboard
path('api/billing/transactions/', ...)        # Transaction feed
path('api/billing/insights/', ...)            # Billing insights
path('api/auth/me/', ...)                     # Current user
path('api/login/', ...)                       # Login
path('api/auth/change-password/', ...)        # Change password

# TeleICU
path('api/teleicu/', ...)                     # ICU wards, beds, sessions, consult, dashboard

# Lab ad-hoc endpoints
path('api/lab-results/trend/', ...)           # Parameter trend
path('api/lab-results/history/', ...)         # Previous orders
path('api/lab-qc/overview/', ...)             # Cross-order QC
path('api/lab-orders/<id>/qc-entry/', ...)    # Per-order QC

# Care Scribe
path('api/care-scribe/', ...)                 # Transcribe
path('api/care-scribe/<id>/confirm/', ...)    # Confirm note
path('api/care-scribe/encounter/<id>/', ...)  # List notes

# Reports & Analytics
path('api/reports/kpis/', ...)
path('api/reports/charts/...', ...)
path('api/reports/tables/...', ...)
path('api/reports/insights/', ...)
path('api/reports/recent/', ...)
path('api/reports/generate/', ...)
path('api/reports/scheduled/', ...)
path('api/reports/saved-views/', ...)
path('api/reports/definitions/', ...)

# Singleton Settings
path('api/settings/<slug>/', ...)             # Billing, pharmacy, lab, teleicu, etc.
path('api/settings/integrations/', ...)
path('api/settings/webhooks/', ...)
path('api/settings/templates/', ...)

# Admin endpoints (used by internal ops frontend via main backend)
# These mirror the endpoints served directly by medos_internal_frontend/backend
path('api/admin/kpis/', ...)
path('api/admin/system-overview-chart/', ...)
path('api/admin/module-status/', ...)
path('api/admin/system-alerts/', ...)
path('api/admin/user-activity/', ...)
path('api/admin/audit-summary/', ...)
path('api/admin/security-overview/', ...)
path('api/admin/recent-activities/', ...)
path('api/admin/database-storage/', ...)
path('api/admin/license-info/', ...)
path('api/admin/system-info/', ...)
path('api/admin/', ...)                       # Admin CRUD router (users, roles, departments, etc.)
```

### medos_internal_frontend/backend/ (port 8001) — Internal Ops API

All endpoints under `/api/internal/` (configured in `medos_internal/urls.py`).

```python
# Auth
path('api/internal/login/', ...)              # Staff login

# Hospital Management
path('api/internal/hospitals/', ...)          # List all hospitals
path('api/internal/hospitals/create/', ...)   # Create hospital + admin
path('api/internal/hospitals/<id>/', ...)     # GET/PATCH detail
path('api/internal/hospitals/<id>/activate/', ...)
path('api/internal/hospitals/<id>/deactivate/', ...)
path('api/internal/hospitals/<id>/impersonate/', ...)

# Platform Stats
path('api/internal/stats/', ...)              # Platform-wide KPIs

# Admin Dashboard (composite endpoints)
path('api/internal/admin/dashboard/overview/', ...)  # KPI cards + module status + storage + license + system info + security
path('api/internal/admin/dashboard/activity/', ...)  # 7-day chart + user activity + audit summary
path('api/internal/admin/dashboard/alerts/', ...)    # System alerts + recent activities

# Admin CRUD ViewSets
path('api/internal/admin/', ...)             # Users, roles, departments, security, settings, workflows, devices, master data, backups, modules, licenses
```

### Key architectural observation

The **admin dashboard endpoints exist on both backends**:

| Endpoint | main backend (8000) | internal ops backend (8001) |
|----------|-------------------|---------------------------|
| KPI cards | `GET /api/admin/kpis/` | `GET /api/internal/admin/dashboard/overview/` (composite) |
| Module status | `GET /api/admin/module-status/` | (in composite overview) |
| System alerts | `GET /api/admin/system-alerts/` | `GET /api/internal/admin/dashboard/alerts/` (composite) |
| User activity | `GET /api/admin/user-activity/` | (in composite activity) |
| Audit summary | `GET /api/admin/audit-summary/` | (in composite activity) |
| ... 11 individual endpoints | ✅ individual | ❌ composite (3 endpoints) |
| Users CRUD | `GET/POST/PATCH/DELETE /api/admin/users/` | `GET/POST/PATCH/DELETE /api/internal/admin/users/` |
| Roles CRUD | ✅ | ✅ |
| Departments CRUD | ✅ | ✅ |
| ... other CRUD | ✅ | ✅ |

The `/api/admin/*` endpoints on the main backend are **not** currently used by the main frontend (`medos/frontend/`) — they only exist because the `medos/views/admin/` module was built as part of the original monolithic app. The internal ops frontend uses the port-8001 composite endpoints instead.

---

## Frontend-Backend Correspondence

### medos/frontend/ → medos/backend/ (port 8000)

| Frontend Page | API Endpoints | Backend Module |
|--------------|--------------|---------------|
| Login | `POST /api/login/` | `medos/auth/views.py` |
| Dashboard | `GET /api/dashboard/` | `medos/views/dashboard.py` |
| Patients | `GET/POST /api/patients/` | `medos/views/patients.py` |
| Patient Detail | `GET /api/patients/<id>/` | `medos/views/patients.py` |
| Encounters | `GET/POST /api/encounters/` | `medos/views/encounters.py` |
| Billing | `GET /api/invoices/`, `/api/billing/dashboard/`, `/api/billing/transactions/`, `/api/billing/insights/` | `medos/views/billing.py` |
| Laboratory | `GET /api/lab-panels/`, `/api/lab-orders/`, `/api/lab-results/trend/` | `medos/views/lab/` (package) |
| TeleICU | `GET /api/teleicu/...` | `medos/views/teleicu.py` + `medos/teleicu/helpers.py` |
| Care Scribe | `POST /api/care-scribe/`, etc. | `medos/views/scribe.py` |
| Reports | `GET /api/reports/...` | `medos/reports/` (package) |
| Settings | `GET /api/settings/<slug>/`, etc. | `medos/settings_views.py` |

### medos_internal_frontend/frontend/ → medos_internal_frontend/backend/ (port 8001)

| Frontend Page | API Endpoints | Backend Module |
|--------------|--------------|---------------|
| Login | `POST /api/internal/login/` | `medos_internal/views.py` |
| Hospitals Dashboard | `GET /api/internal/hospitals/` | `medos_internal/views.py` |
| Hospital Detail | `GET /api/internal/hospitals/<id>/` | `medos_internal/views.py` |
| New Hospital Wizard | `POST /api/internal/hospitals/create/` | `medos_internal/services/hospital_onboarding.py` |
| Platform Stats | `GET /api/internal/stats/` | `medos_internal/services/dashboard.py` |
| Admin Dashboard (Overview) | `GET /api/internal/admin/dashboard/overview/` | `medos_internal/services/dashboard.py` |
| Admin Dashboard (Activity) | `GET /api/internal/admin/dashboard/activity/` | `medos_internal/services/dashboard.py` |
| Admin Dashboard (Alerts) | `GET /api/internal/admin/dashboard/alerts/` | `medos_internal/services/dashboard.py` |

---

## Internal Ops Frontend Architecture

### Frontend file structure

```
medos_internal_frontend/frontend/src/
├── api/
│   ├── client.ts                  — Axios instance (base URL, interceptors)
│   └── internalApi.ts             — Typed API client (all endpoints)
├── components/
│   ├── ErrorBoundary.tsx
│   ├── Layout.tsx                 — App shell (sidebar, header, nav)
│   └── Toast.tsx                  — Notification component
├── pages/
│   ├── Login.tsx                  — Staff login form
│   ├── HospitalsDashboard.tsx     — List/view all hospitals
│   ├── HospitalDetail.tsx         — Single hospital detail/edit
│   ├── NewHospitalWizard.tsx      — Multi-step hospital creation
│   ├── Stats.tsx                  — Platform-wide statistics
│   ├── AdminDashboard.tsx         — 3-tab admin dashboard (overview, activity, alerts)
│   └── ...test.tsx                — Test files per page
├── test/
│   ├── setup.ts
│   ├── test-utils.tsx
│   └── smoke.test.ts
├── App.tsx                        — Router + query provider
├── main.tsx                       — Entry point
└── index.css                      — Global styles
```

### API client structure (`internalApi.ts`)

The client is organized as a single object with typed methods:

```typescript
internalApi = {
  login(username, password),
  getHospitals(),
  createHospital(data),
  getHospital(id),
  updateHospital(id, data),
  activateHospital(id),
  deactivateHospital(id),
  impersonateHospital(id),
  getStats(),
  getDashboardOverview(),
  getDashboardActivity(),
  getDashboardAlerts(),
}
```

### Frontend TypeScript types matching backend serializers

The frontend defines interfaces that mirror the backend response shapes:

| Frontend Type | Backend Serializer(s) |
|--------------|----------------------|
| `HospitalListItem` | `HospitalListSerializer` |
| `HospitalDetail` | `HospitalDetailSerializer` |
| `PlatformStats` | `PlatformStats` (from `dashboard_service.read_platform_stats()`) |
| `DashboardOverviewKpis` | `AdminKPISerializer` |
| `ModuleStatus` | `AdminModuleSerializer` |
| `ChartPoint` | `SystemOverviewPointSerializer` |
| `UserActivityEntry` | `UserActivitySerializer` |
| `SystemAlert` | `SystemAlertSerializer` |
| `RecentActivity` | `RecentActivitySerializer` |

---

## Backend Cleanups Summary

### What changed (and what it means for the frontend)

#### Round 1 — Foundation Cleanups

| Candidate | Change | Frontend Impact |
|-----------|--------|----------------|
| Delete dead `views/internal.py` | Removed 431 lines of dead code | ✅ None — no endpoint was consumed |
| Consolidate auth into `medos/auth/` package | `supabase_auth.py`, `cookie_auth.py` merged | ✅ None — the `POST /api/login/` response shape is unchanged |
| Move `admin_views.py` into `views/` package | File moved, import path changed | ✅ None — only Django import internals |
| Consolidate alert engine (`medos/alerts/engine.py`) | Wires thresholds + broadcaster | ✅ None — no API change |
| Split models into `medos/models/` package | 1 file → 10 domain-aligned files | ✅ None — model attributes unchanged |
| Convert settings to `medos_project/settings/` package | `settings.py` → package | ✅ None — only Django internals |

#### Round 1.5 — Zero-Risk Deletions & Consolidations

| Candidate | Change | Frontend Impact |
|-----------|--------|----------------|
| Delete `alert_engine.py` dead shim | −16 lines, zero callers | ✅ None |
| Merge `admin_models.py` into `models/` package | Models moved, backward-compat shim | ✅ None |
| Collapse settings singleton views | 8 views → 1 generic view + registry | ✅ None — URL patterns preserved |
| Consolidate settings models with `SingletonSettingsBase` | 8 models inherit from base | ✅ None — migration-no-op |

#### Round 2 — Targeted Deepenings

| Candidate | Change | Frontend Impact |
|-----------|--------|----------------|
| Split `hospital_admin.py` → `views/admin/` package | 1 file (831 lines) → 11 files | ✅ None — URL patterns unchanged |
| Merge vitals consumers | `VitalsConsumer` handles both single + aggregated | ✅ None — WebSocket paths unchanged |
| Extract TeleICU helpers | `teleicu/helpers.py` extracted from views | ✅ None — response shapes identical |

#### Round 3 — Final Cleanups

| Candidate | Change | Frontend Impact |
|-----------|--------|----------------|
| Delete `admin_models.py` shim | −8 lines | ✅ None |
| Deepen `BillingTransactionsView` | Extract `billing/transactions.py` helper | ✅ None — response shape unchanged |
| Split `views/lab.py` → `views/lab/` package | 1 file (536 lines) → 9 files | ✅ None — URL patterns preserved |
| Split `admin_serializers.py` → `serializers/admin/` package | 1 file (356 lines) → 11 files | ✅ None — backward-compat shim in place |

### Bottom line

**All cleanups are purely internal to the backend.** The frontend sees:

- Same URL patterns
- Same request/response shapes
- Same WebSocket message formats
- Same authentication flow

---

## API Contract Observations

### No versioning

Both backends serve APIs without version prefixes (`/api/v1/`). Frontend components hardcode paths in the API client. This means:

- Any renaming of a URL pattern in `urls.py` breaks the frontend silently
- There's no contract test or OpenAPI spec validating the shape
- The TypeScript types in `internalApi.ts` are manually maintained — drift is possible

### Admin dashboard endpoints: two scopes, not fragmentation

The main backend has **11 individual** admin dashboard endpoints (`/api/admin/kpis/`, `/api/admin/module-status/`, ...), and the internal ops backend has **3 composite** endpoints (`/api/internal/admin/dashboard/overview/`, `/api/internal/admin/dashboard/activity/`, `/api/internal/admin/dashboard/alerts/`).

**This is not duplication — they serve different scopes:**

| | 11 individual endpoints (port 8000) | 3 composite endpoints (port 8001) |
|---|---|---|
| **Scope** | Per-hospital admin dashboard | Platform-wide ops dashboard |
| **User** | Hospital admin (sees 1 hospital) | Internal ops staff (sees all hospitals) |
| **Data volume** | ~dozens of rows per query | Aggregated across all hospitals |
| **Query pattern** | `WHERE hospital_id = ?` | `SELECT COUNT(*) FROM ...` |
| **Frontend** | `medos/frontend/ AdminDashboard.tsx` | `medos_internal_frontend/frontend/ AdminDashboard.tsx` |

The main frontend's `AdminDashboard.tsx` actively uses all 11 individual endpoints for per-hospital scoped admin. The internal ops frontend uses the 3 composite endpoints for platform-wide stats. Unifying them would require either adding a `?hospital_id=` param to composite endpoints (defeating the composite purpose) or forcing hospital admins to fetch + parse platform-wide responses (wasteful).

**Both should stay as-is.** At the query layer, they could share materialized views (see [Scalability section](#scalability-at-4m-hospitals)).

### Shared models, separate serializers

Both backends define their own serializers for shared models:

| Model | medos serializer | medos_internal serializer |
|-------|-----------------|-------------------------|
| `Hospital` | No serializer (used as FK) | `HospitalListSerializer`, `HospitalDetailSerializer`, etc. |
| `Role` | `AdminRoleSerializer` | `AdminRoleSerializer` |
| `User` | `AdminUserSerializer` | `AdminUserSerializer` |

The internal ops backend also has serializers defined in `medos_internal/serializers.py` that overlap with `medos/admin_serializers.py`. Both are maintained independently.

---

## Database Sharing Model

```
medos database (PostgreSQL)
├── Tables owned by medos/ (migrations there)
│   ├── medos_hospital
│   ├── medos_patient
│   ├── medos_encounter
│   ├── medos_invoice
│   ├── medos_role
│   ├── medos_hospitaluserprofile
│   ├── medos_systemactivitylog
│   ├── auth_user, auth_group, auth_permission
│   ├── authtoken_token
│   ├── medos_laborder, medos_labpanel, ...
│   ├── medos_encounter, medos_invoice, ...
│   └── ... (~50 tables total)
│
└── Tables shared via managed=False + db_table (by medos_internal)
    ├── medos_hospital         → managed=False, db_table='medos_hospital'
    ├── medos_role              → managed=False, db_table='medos_role'
    ├── medos_hospitaluserprofile → managed=False, db_table='medos_hospitaluserprofile'
    ├── medos_systemactivitylog → managed=False, db_table='medos_systemactivitylog'
    ├── auth_user               → managed=False
    ├── authtoken_token         → managed=False
    ├── medos_patient           → managed=False (stats only)
    ├── medos_encounter         → managed=False (stats only)
    └── medos_invoice           → managed=False (stats only)
```

### Managed models (owned by internal ops)

These tables are created and migrated by `medos_internal_frontend/backend/`:

- `medos_adminmodule`, `medos_systemalert`, `medos_userloginactivity`
- `medos_department`, `medos_masterdataentry`, `medos_systemsetting`
- `medos_workflowdefinition`, `medos_deviceintegration`, `medos_securitypolicy`
- `medos_backuprecord`, `medos_licenseinfo`, `medos_storagemetrics`

`Hospital` uses `db_table='medos_hospital'` as a **managed model** — effectively the internal ops backend also owns this table (but the main backend created it first).

---

## Scalability at 4M Hospitals

At scale (4 million hospitals), the **individual endpoints are superior to composites**. Here's why:

### 1. Independent cache TTLs

| Endpoint | Data freshness | Cache TTL | Query cost |
|----------|---------------|-----------|------------|
| `kpis` | Slow (daily) | 5 min | Light — aggregate counts via index |
| `module-status` | Slow | 5 min | Light — status flags |
| `system-alerts` | Fast | 30 s | Medium — unresolved alerts |
| `user-activity` | Slow | 5 min | Heavy — login stats across hospital staff |
| `audit-summary` | Medium | 2 min | Heavy — category counts |
| `storage` | Slow | 10 min | Light — one row |

A composite endpoint bundles fast + slow data → forced to the **shortest TTL** for everything → 6× more cache misses. At 4M hospitals, that means re-computing heavy queries (user activity, audit summary) every 30 seconds even if only alerts changed.

### 2. Independent query optimization

Each endpoint uses a targeted index:

```sql
-- KPIs: fast even at 4M — index-only aggregate
SELECT COUNT(*) FROM medos_patient WHERE hospital_id = $1;

-- User activity: needs composite index on (hospital_id, created_at)
SELECT u.username, COUNT(l.id)
FROM auth_user u
JOIN medos_userloginactivity l ON l.user_id = u.id
WHERE u.hospital_profile->hospital_id = $1
  AND l.created_at > now() - interval '30 days'
GROUP BY u.id;
```

Bundled in a composite, one slow path (audit summary) drags down the entire response.

### 3. Frontend lazy-loads per tab

The main `AdminDashboard.tsx` already uses a 3-tab layout. Individual endpoints fetch only data for the active tab:

- **Tab 1 (Overview):** 3-4 endpoints (kpis, module-status, storage, license)
- **Tab 2 (Activity):** 2 endpoints (user-activity, audit-summary)
- **Tab 3 (Alerts):** 1 endpoint (system-alerts)

Composite endpoints force fetching **all data on every tab switch**. At 4M scale, the `user-activity` query runs even when the user only wants alerts.

### 4. Materialized views are the real answer

At 4M scale, **nothing computes in real-time**. Background jobs (Celery beat) refresh materialized views. Individual endpoints each map to one refresh schedule:

```
medos_admin_kpis_mv          → refresh every 5 min
medos_user_activity_mv       → refresh every 5 min
medos_system_alerts_mv       → refresh every 30 s
medos_audit_summary_mv       → refresh every 2 min
```

Both backends read from the same materialized views. The endpoints stay separate because they serve different consumers with different scoping (`WHERE hospital_id = ?` vs platform-wide), but the **query layer is shared**.

### 5. Independent load balancing

At scale, different endpoints hit different resource bottlenecks:

- Storage endpoint → reads `medos_storagemetrics` (one row) → can go to any replica
- User activity → joins across 3 tables → needs dedicated pool or read replica
- System alerts → frequent writes too → needs careful connection pool tuning

Individual endpoints let you route traffic by query profile. Composites bundle different profiles together, making routing impossible.

## Strategy: Keep both, share the query layer

| Layer | What to do |
|-------|-----------|
| **API endpoints** | Keep individual (port 8000, per-hospital) + composite (port 8001, platform-wide). They serve different consumers with different scoping needs. |
| **Query layer** | Extract into shared helpers or materialized views that both backends import. No duplicate SQL. |
| **Caching** | Per-endpoint cache TTLs. Redis with different expiry per key prefix. |
| **Background jobs** | Celery beat refreshes materialized views. Both backends query the same pre-computed tables. |

## Recommendations for Frontend Improvement

1. **API versioning** — Adding `/api/v1/` prefix would let the frontend detect breaking changes in CI rather than at runtime.

2. **Generated TypeScript types** — The `internalApi.ts` types are manually maintained. They'll drift from the backend serializers. A tool like `openapi-typescript` could generate them from DRF's schema.

3. **Contract tests** — A test that hits each API endpoint and validates the response shape against the frontend's TypeScript types would catch breaks immediately.

4. **Query-layer extraction** — If both backends share materialized view queries, the frontend response shapes become guaranteed consistent without endpoint unification.

5. **The `views/lab/` package split makes future API changes easier** — Since each lab entity has its own file, adding a new lab endpoint only touches one file. The frontend API client can be more granular too.
