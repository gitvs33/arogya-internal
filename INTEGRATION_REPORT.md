# MedOS Internal Frontend — System Integration Report

**Date:** 2026-06-11  
**Codebase:** `/home/vishnus/Desktop/medos_internal_frontend`  
**Backend tests:** 84 passing | **Frontend tests:** 40 passing | **Build:** Clean (code-split)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │   Login  │ │  Stats   │ │Dashboard │ │ Hospitals │  │
│  │  Page    │ │  Page    │ │  Page    │ │  Pages    │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘  │
│       └──────────────┬──────────┘              │        │
│                 ┌────▼─────┐                    │        │
│                 │internalApi│◄───────────────────┘        │
│                 │ (axios)  │                             │
│                 └────┬─────┘                             │
└──────────────────────┼──────────────────────────────────┘
                       │ HTTP
┌──────────────────────▼──────────────────────────────────┐
│                 Backend (Django + DRF)                    │
│  ┌────────┐  ┌──────────┐  ┌─────────────────────────┐   │
│  │ Views  │  │Services  │  │ Models (managed)         │   │
│  │(11 fns)│  │(6 mods)  │  │ AdminModule, SystemAlert │   │
│  │        │  │          │  │ UserLoginActivity, etc.  │   │
│  │ + 11   │  │ dashboard│  │                          │   │
│  │ CRUD   │  │ admin_crud│ │ Models (unmanaged)       │   │
│  │ routes │  │ hospital_ │  │ Hospital, Patient,       │   │
│  │        │  │  onboarding│ │ Encounter, Invoice      │   │
│  └───┬────┘  │ user_     │  └─────────────────────────┘   │
│      │       │  management│                               │
│      │       │ hospital_  │                               │
│      │       │  detail    │                               │
│      │       └────────────┘                               │
│      │                                                    │
│  ┌───▼──────────────────────────────────────────────┐     │
│  │ Infrastructure                                    │     │
│  │ • Token auth (7-day expiry)                      │     │
│  │ • Rate limiting (anon 10/hr, user 120/min)       │     │
│  │ • LocMemCache (Redis-ready)                      │     │
│  │ • CONN_MAX_AGE=600 connection pooling            │     │
│  │ • 2 management commands (log + token cleanup)    │     │
│  └──────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────┘
```

---

## 2. Backend Service Modules

| Module | Lines | Tests | Public API | Description |
|--------|-------|-------|------------|-------------|
| `services/dashboard.py` | 404 | 31 | `read_overview()`, `read_activity()`, `read_alerts()`, `read_platform_stats()` | Composite dashboard queries + caching (5min/1min/30s TTLs) |
| `services/admin_crud.py` | 84 | — | `make_admin_viewset(Model)`, `make_admin_serializer(Model)`, `HospitalScopedViewSet` | Factory for 11 admin CRUD endpoints |
| `services/hospital_onboarding.py` | 77 | 9 | `onboard_hospital(...)` | Transactional 10-step hospital creation |
| `services/hospital_detail.py` | 68 | 16 | `read_hospital_detail(hospital)` | Single-hospital stats, staff breakdown, admin info |
| `services/user_management.py` | 62 | 13 | `create_admin_user(...)` | Transactional user + profile creation |
| `services/admin_crud.py` (shared) | — | — | `HospitalScopedViewSet` | Base class for hospital-scoped CRUD |

**Design patterns:**
- Views are thin adapters (3-24 lines each) delegating to service modules
- Services return plain dicts — no Serializer dependency in service layer
- Services use `with transaction.atomic()` for transactional workflows
- Service seam enables unit testing without HTTP/auth layer

---

## 3. API Endpoints

### Auth
| Method | Path | View | Description |
|--------|------|------|-------------|
| POST | `/api/internal/login/` | `internal_login` | Staff login, returns token + user info |

### Hospital Management
| Method | Path | View | Description |
|--------|------|------|-------------|
| GET | `/api/internal/hospitals/` | `hospital_list` | Paginated list (50/page) with staff counts |
| POST | `/api/internal/hospitals/create/` | `hospital_create` | Create hospital + admin account |
| GET | `/api/internal/hospitals/<pk>/` | `hospital_detail_get` | Full detail with stats, staff, admin |
| PATCH | `/api/internal/hospitals/<pk>/update/` | `hospital_detail_update` | Update hospital fields |
| POST | `/api/internal/hospitals/<pk>/activate/` | `hospital_activate` | Set is_active=True |
| POST | `/api/internal/hospitals/<pk>/deactivate/` | `hospital_deactivate` | Set is_active=False |
| POST | `/api/internal/hospitals/<pk>/impersonate/` | `hospital_impersonate` | Get token for hospital admin |

### Platform Stats
| Method | Path | View | Description |
|--------|------|------|-------------|
| GET | `/api/internal/stats/` | `platform_stats` | Global KPIs (hospitals, patients, invoices, growth) |

### Admin Dashboard (composite, always global)
| Method | Path | View | Cadence | Data |
|--------|------|------|---------|------|
| GET | `/api/internal/admin/dashboard/overview/` | `admin_overview` | 5 min cache | KPIs, modules, storage, license, system, security |
| GET | `/api/internal/admin/dashboard/activity/` | `admin_activity` | 1 min cache | 7-day chart, user activity, audit summary |
| GET | `/api/internal/admin/dashboard/alerts/` | `admin_alerts` | 30 s cache | Unresolved alerts, recent activities |

### Admin CRUD (factory-built, hospital-scoped)
| Endpoint | Model | Auto-generated |
|----------|-------|----------------|
| `/api/internal/admin/users/` | User (custom ViewSet) | No — custom logic |
| `/api/internal/admin/roles/` | Role (custom ViewSet) | No — annotates user_count |
| `/api/internal/admin/departments/` | Department | Yes — `make_admin_viewset` |
| `/api/internal/admin/security-policies/` | SecurityPolicy | Yes |
| `/api/internal/admin/system-settings/` | SystemSetting | Yes |
| `/api/internal/admin/workflows/` | WorkflowDefinition | Yes |
| `/api/internal/admin/device-integrations/` | DeviceIntegration | Yes |
| `/api/internal/admin/master-data/` | MasterDataEntry | Yes |
| `/api/internal/admin/backups/` | BackupRecord | Yes |
| `/api/internal/admin/modules/` | AdminModule | Yes |
| `/api/internal/admin/licenses/` | LicenseInfo | Yes |

---

## 4. Frontend Pages

| Page | Chunk Size | Tests | Data Source | Key Features |
|------|-----------|-------|-------------|--------------|
| `Login.tsx` | (in main) | 3 | `POST /login/` | Username/password form, error display |
| `Stats.tsx` | 4 KB | 5 | `GET /stats/` | KPI cards, growth section, health percentage |
| `HospitalsDashboard.tsx` | 4.2 KB | — | `GET /hospitals/` | Paginated hospital list with cards |
| `HospitalDetail.tsx` | 6.5 KB | 5 | `GET /hospitals/<pk>/`, `PATCH /update/` | Detail view with stats/staff/admin, activate/deactivate |
| `NewHospitalWizard.tsx` | 7 KB | 8 | `POST /hospitals/create/` | 2-step wizard (details → admin account) |
| `AdminDashboard.tsx` | 16.8 KB | 6 | 3 dashboard composite endpoints | Overview/Activity/Alerts tabs |

### Shared Components

| Component | Lines | Tests | Purpose |
|-----------|-------|-------|---------|
| `Layout.tsx` | 79 | 4 | Sidebar navigation + logout |
| `Toast.tsx` | 77 | 4 | Toast notification system (auto-dismiss 5s) |
| `ErrorBoundary.tsx` | 48 | 3 | Catch render errors with fallback UI |

### Frontend API Layer

```
src/api/
├── client.ts           — Axios instance, token interceptor, 401 → toast + redirect
├── internalApi.ts      — Aggregated API object combining all sub-modules
├── types.ts            — Shared TypeScript interfaces
└── internal/
    ├── authApi.ts      — login()
    ├── hospitalsApi.ts — CRUD + activate/deactivate/impersonate
    └── dashboardApi.ts — 3 composite endpoints
```

**Code splitting:** Each page is a `React.lazy()` chunk loaded on route match. Main bundle: 313 KB (React, router, icons, shared deps). Page chunks: 4–17 KB each.

**Error handling chain:** Axios interceptor → 401 clears token + redirects to login. All other errors → `error` property in React Query (handled per-component). `Toast` provides user-visible notifications. `ErrorBoundary` catches render crashes.

---

## 5. Infrastructure

### Authentication
- **Mechanism:** DRF Token Authentication with custom `ExpiringTokenAuthentication`
- **Token lifetime:** 7 days (configurable via `TOKEN_EXPIRY_DAYS`)
- **Expiry handling:** Expired tokens → `AuthenticationFailed`. Login/impersonate endpoints regenerate expired tokens.
- **Cleanup:** `purge_expired_tokens` management command (dry-run supported)

### Rate Limiting
- **Anonymous:** 10 requests/hour
- **Authenticated users:** 120 requests/minute
- **Config:** DRF `DEFAULT_THROTTLE_CLASSES` + `DEFAULT_THROTTLE_RATES`

### Caching
- **Backend:** `LocMemCache` (no Redis dependency)
- **Dashboard overview:** 5 min TTL
- **Dashboard activity:** 1 min TTL
- **Dashboard alerts:** 30 s TTL
- **Easy Redis swap:** Uncomment `redis` backend in `CACHES` setting

### Database
- **Connection pooling:** `CONN_MAX_AGE=600` (persistent connections up to 10 min)
- **Foreign keys to unmanaged tables:** All 18 `ForeignKey(Hospital)` use `db_constraint=False`
- **Unmanaged models:** `Hospital`, `Patient`, `Encounter`, `Invoice` (read-only from medos schema)

### Management Commands
| Command | Function | Schedule |
|---------|----------|----------|
| `purge_old_logs` | Delete `UserLoginActivity` >90 days, `SystemActivityLog` >180 days | Daily (cron) |
| `purge_expired_tokens` | Delete tokens older than `TOKEN_EXPIRY_DAYS` | Daily (cron) |

---

## 6. Test Infrastructure

### Backend Tests (84 total)

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_dashboard_service.py` | 31 | `read_overview()`, `read_activity()`, `read_alerts()` |
| `test_onboarding.py` | 9 | `onboard_hospital()` — 10-step create workflow |
| `test_integration.py` | 15 | End-to-end: login, auth, CRUD, dashboard, onboarding |
| `test_hospital_detail.py` | 16 | `read_hospital_detail()` — stats, staff breakdown, admin |
| `test_user_management.py` | 13 | `create_admin_user()` — user creation, roles, errors |

**Pattern:** SQLite in-memory database via `tests/settings.py`. Unmanaged tables created via raw SQL (`CREATE TABLE IF NOT EXISTS`). `PRAGMA foreign_keys = OFF` to avoid FK constraint issues during setup.

### Frontend Tests (40 total)

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `smoke.test.ts` | 2 | jsdom environment sanity checks |
| `Login.test.tsx` | 3 | Form render, error display, navigation on success |
| `Stats.test.tsx` | 5 | Loading skeleton, data cards, growth, health %, zero edge case |
| `NewHospitalWizard.test.tsx` | 8 | Step navigation, slug generation, form submit, error/loading states |
| `AdminDashboard.test.tsx` | 6 | Loading, 3 tabs, error state, alert count |
| `HospitalDetail.test.tsx` | 5 | Loading, detail render, activate/deactivate buttons, not-found |
| `Layout.test.tsx` | 4 | Nav links, active highlight, username display, logout button |
| `Toast.test.tsx` | 4 | Add, remove, auto-dismiss, multiple toasts |
| `ErrorBoundary.test.tsx` | 3 | Children render, fallback on error, custom fallback |

**Pattern:** `renderWithProviders()` wrapping `QueryClientProvider` + `MemoryRouter` + `ToastProvider`. `vi.mock()` for API module isolation. `vi.resetAllMocks()` in `beforeEach`.

---

## 7. Architecture Changes Summary

### Before (Round 0)
- 11 independent dashboard endpoints (1 query each → 11 queries on page load)
- 9 manually defined ViewSet classes + 11 `fields='__all__'` serializers (~160 boilerplate lines)
- 417-line `views.py` with mixed GET/POST views
- Hospital scoping bug: `getattr(user, 'hospital_profile', None)` always returned `None`
- No token expiry
- 11 of 18 `ForeignKey(Hospital)` missing `db_constraint=False`
- No tests (0 backend, 0 frontend)
- No caching, no rate limiting, no pagination, no code splitting
- 361 KB single frontend bundle
- `recharts` dependency imported nowhere

### After (Round 4)
- 3 composite dashboard endpoints (cached at cadence-appropriate TTLs)
- 11 CRUD endpoints via 2 factory functions (84 lines), 2 custom ViewSets remaining
- 361-line `views.py` — every view is single-method
- Hospital scoping fixed with direct `HospitalUserProfile.objects.filter(...)` query
- 7-day token expiry with auto-regeneration on login
- All 18 `ForeignKey(Hospital)` consistently use `db_constraint=False`
- 84 backend tests + 40 frontend tests = 124 total
- Dashboard responses cached (5 min / 1 min / 30 s), rate limited (10/hr anon, 120/min user)
- Hospital list paginated (50/page)
- Code-split into per-page chunks (313 KB main + 4–17 KB pages)
- Service layer: 6 modules, 695 lines total
- `recharts` removed, dead barrel file deleted

### Deleted If Removed
If the entire service layer were deleted, the complexity would reappear across 11 views and 152 lines of serializers — confirming the service modules earn their keep (the **deletion test** passes).

---

## 8. Remaining Candidates (from Round 4)

These are low-priority hygiene items identified in the final architecture review:

| Candidate | Effort | Type |
|-----------|--------|------|
| Service-layer zero-hospitals guard for `read_platform_stats()` | 10 min | Guard |
| Convert remaining 2 custom ViewSets to factory pattern | 30 min | Consolidation |
| End-to-end Playwright/Cypress test for login → dashboard flow | 1-2 hr | Coverage |
| Redis migration (swap LocMemCache → Redis) | 15 min | Production hardening |
| CI pipeline (GitHub Actions: lint + test + build) | 1 hr | Automation |

---

*Report generated from Round 4 architecture review and implementation session.*
