# MedOS Architecture — Two-Project Split

## The Big Picture

MedOS runs as **two separate Django projects** sharing one PostgreSQL database.

```
┌─────────────────────────────────────────────────────────────────┐
│                     PostgreSQL Database                          │
│  (medos_hospital, medos_patient, medos_encounter,               │
│   medos_invoice, medos_role, medos_hospitaluserprofile, ...)     │
└──────────────────────┬──────────────────────────┬───────────────┘
                       │                          │
                       ▼                          ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│   medos/                     │  │  medos_internal_frontend/    │
│                              │  │                              │
│  Backend (port 8000)         │  │  Backend (port 8001)         │
│  Python Django REST API      │  │  Python Django REST API      │
│                              │  │                              │
│  Frontend (port 5173)        │  │  Frontend (port 5175)        │
│  React + Vite + Tailwind     │  │  React + Vite + Tailwind     │
│                              │  │                              │
│  ─── Hospital Staff UI ───   │  │  ─── Internal Ops UI ───     │
│  Patients, Encounters,       │  │  All Hospitals management,   │
│  Billing, Lab, TeleICU,      │  │  Platform Stats,             │
│  A.I Scribe, Pharmacy, etc.  │  │  Hospital CRUD,              │
│                              │  │  Activate/Deactivate,        │
│                              │  │  Impersonation,              │
│                              │  │  Admin Dashboard             │
└──────────────────────────────┘  └──────────────────────────────┘
```

---

## Project 1: `medos/` — Hospital Staff App

### Location
`~/Desktop/medos/`

### Who uses it
**Hospital staff** — doctors, nurses, billing clerks, lab technicians, admins at each hospital.

### What it does
- Patient registration & management
- Encounter (OPD/IPD) creation & management
- Clinical workflows (vitals, medications, diagnoses)
- Billing & invoicing (GST-compliant)
- Laboratory module (orders, results, QC)
- TeleICU monitoring
- A.I Scribe (Whisper + LLM)
- Drug-drug interaction checking
- Offline-first CRDT sync
- Reports & analytics

### Backend models it owns
All core models are defined here and their **migrations live here**:

| Model | Table |
|---|---|
| `Hospital` | `medos_hospital` |
| `Patient` | `medos_patient` |
| `Encounter` | `medos_encounter` |
| `Invoice` | `medos_invoice` |
| `Role` | `medos_role` |
| `HospitalUserProfile` | `medos_hospitaluserprofile` |
| `SystemActivityLog` | `medos_systemactivitylog` |
| `LabOrder`, `LabResult` | `medos_laborder`, `medos_labresult` |
| ... and ~40 more | `medos_*` |

### Auth flow
- **Primary:** Supabase JWT (email/password → Supabase → Django verifies JWT)
- **Fallback (dev):** Local username/password
- Session + Token auth for API calls

### How to run
```bash
cd ~/Desktop/medos/backend
python manage.py runserver 8000

# In another terminal:
cd ~/Desktop/medos/frontend
npm run dev   # → http://localhost:5173
```

---

## Project 2: `medos_internal_frontend/` — Internal Ops Panel

### Location
`~/Desktop/medos_internal_frontend/`

### Who uses it
**Your company's staff** — MedOS operations team, super admins, support staff.

### What it does
- **Hospital management** — create new hospitals, view all hospitals, edit details
- **Activate / Deactivate** hospitals (subscription control)
- **Impersonate** — get a token to log in as any hospital's admin (for debugging)
- **Platform-wide stats** — total hospitals, active hospitals, total patients, encounters, invoices
- **Admin Dashboard** — KPI cards, system overview charts, module status, system alerts, user activity, audit logs, security overview, database storage, license info

### Backend setup
This project **shares the same database** as the main `medos/` project but is a separate Django process.

**Managed models** (owned here — migrations run here):
- AdminModule, SystemAlert, UserLoginActivity, Department, MasterDataEntry
- SystemSetting, WorkflowDefinition, DeviceIntegration, SecurityPolicy
- BackupRecord, LicenseInfo, StorageMetrics

**Unmanaged models** (read/write existing tables via `db_table` + `managed = False`):
- `Role` → `medos_role`
- `HospitalUserProfile` → `medos_hospitaluserprofile`
- `SystemActivityLog` → `medos_systemactivitylog`
- `Patient` → `medos_patient` (stats only)
- `Encounter` → `medos_encounter` (stats only)
- `Invoice` → `medos_invoice` (stats only)

The `Hospital` model is defined here as a **managed model** with `db_table = 'medos_hospital'` — so it maps to the same table the main project created.

### Auth flow
- **Token-based** (DRF `TokenAuthentication`)
- Only `is_staff=True` users can log in
- No Supabase dependency

### How to run
```bash
cd ~/Desktop/medos_internal_frontend/backend
python manage.py runserver 8001

# In another terminal:
cd ~/Desktop/medos_internal_frontend/frontend
npm run dev   # → http://localhost:5175
```

---

## Database Sharing Explained

Both projects point to the same PostgreSQL database (`medos`). The trick is how they share tables:

```
┌──────────────────────────────────────────────────────────────┐
│                     medos database                           │
│                                                              │
│  Tables created by medos/backend migrations:                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  auth_user, medos_patient, medos_encounter,          │   │
│  │  medos_hospital, medos_role, medos_invoice,          │   │
│  │  medos_hospitaluserprofile, medos_systemactivitylog,  │   │
│  │  medos_laborder, ... (40+ tables)                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Tables created by medos_internal_frontend/backend           │
│  migrations (same names, same DB):                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  medos_hospital (same table — db_table mapping)       │   │
│  │  medos_adminmodule, medos_systemalert,               │   │
│  │  medos_userloginactivity, medos_department,           │   │
│  │  medos_masterdataentry, medos_systemsetting,         │   │
│  │  medos_workflowdefinition, ... (13 tables)            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Tables shared via managed=False + db_table:                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  medos_role, medos_hospitaluserprofile,              │   │
│  │  medos_systemactivitylog, medos_patient,             │   │
│  │  medos_encounter, medos_invoice                       │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Why not make it fully independent?

The `Hospital` model has **~20 ForeignKeys** from models in `medos/backend/` — `Patient.hospital`, `Encounter.hospital`, `Invoice.hospital`, `Role.hospital`, etc. Moving `Hospital` out would require breaking those relationships, which is a much larger refactor.

For now, the internal ops project:
1. Maps `Hospital` to the existing `medos_hospital` table via `db_table`
2. Uses unmanaged models to read/write shared tables without migrating them
3. Lets the main `medos/` backend own the canonical model definitions and migrations

---

## API Endpoints Summary

### `medos/backend/` (port 8000) — Hospital Staff API

| Endpoint | Purpose |
|---|---|
| `POST /api/login/` | Login (Supabase or local) |
| `GET /api/auth/me/` | Current user profile |
| `GET/POST /api/patients/` | Patient CRUD |
| `GET/POST /api/encounters/` | Encounter CRUD |
| `GET/POST /api/invoices/` | Billing |
| `GET/POST /api/lab-orders/` | Laboratory |
| `GET/POST /api/teleicu/` | TeleICU |
| ... | ... |

### `medos_internal_frontend/backend/` (port 8001) — Internal Ops API

| Endpoint | Purpose |
|---|---|
| `POST /api/internal/login/` | Staff login |
| `GET/POST /api/internal/hospitals/` | List/create hospitals |
| `GET/PATCH /api/internal/hospitals/:id/` | Hospital detail/update |
| `POST /api/internal/hospitals/:id/activate/` | Activate hospital |
| `POST /api/internal/hospitals/:id/deactivate/` | Deactivate hospital |
| `POST /api/internal/hospitals/:id/impersonate/` | Get admin token |
| `GET /api/internal/stats/` | Platform KPIs |
| `GET /api/internal/admin/kpis/` | Admin dashboard KPI cards |
| `GET /api/internal/admin/module-status/` | Module operational status |
| `GET /api/internal/admin/system-alerts/` | Infrastructure alerts |
| `GET /api/internal/admin/user-activity/` | User login activity |
| `GET /api/internal/admin/audit-summary/` | Audit log summary |
| `GET /api/internal/admin/security-overview/` | Security metrics |
| `GET /api/internal/admin/recent-activities/` | Recent system activities |
| `GET /api/internal/admin/database-storage/` | Storage metrics |
| `GET /api/internal/admin/license-info/` | License info |
| `GET /api/internal/admin/system-info/` | Django/Python info |
| `GET/POST/PATCH/DELETE /api/internal/admin/users/` | User CRUD |
| `GET/POST/PATCH/DELETE /api/internal/admin/roles/` | Role CRUD |
| `GET/POST/PATCH/DELETE /api/internal/admin/departments/` | Department CRUD |

---

## Django Admin

Both projects have Django admin at `/admin/`:

| Project | Admin URL | What you can manage |
|---|---|---|
| `medos/backend/` | `http://localhost:8000/admin/` | All models — patients, encounters, billing, lab, teleICU, roles, users, hospitals, system settings, etc. |
| `medos_internal_frontend/backend/` | `http://localhost:8001/admin/` | Hospital management, admin modules, system alerts, departments, system settings, workflows, device integrations, security policies, backups, licenses, storage |

---

## Why Two Projects?

| Reason | Detail |
|---|---|
| **Separation of concerns** | Hospital staff UI and internal ops UI are completely different apps with different auth flows, UX patterns, and user bases |
| **Security isolation** | Internal ops endpoints require `is_staff=True` — they shouldn't be on the same server as hospital-facing endpoints |
| **Independent deployment** | Each project can be deployed, scaled, and updated independently |
| **Different auth providers** | Hospital app uses Supabase; internal ops uses simple Token auth |
| **Cleaner codebase** | Each project has only the code relevant to its purpose — no confusing mix of hospital-facing and ops-facing views |
