# MedOS Internal Operations

Super admin panel for managing hospitals on the MedOS platform.

## Architecture

```
medos_internal_frontend/
├── backend/          # Django REST API (port 8001)
│   ├── medos_internal/       # App: models, views, serializers, admin
│   └── medos_internal_project/ # Project settings
├── frontend/         # React SPA (Vite + React 19 + Tailwind, port 5175)
└── README.md
```

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 8001
```

The internal API is at `http://localhost:8001/api/internal/...`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5175` — proxies `/api` to `http://localhost:8001`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/internal/login/` | Staff login |
| GET | `/api/internal/hospitals/` | List all hospitals |
| POST | `/api/internal/hospitals/` | Create hospital + admin |
| GET | `/api/internal/hospitals/:id/` | Hospital detail |
| PATCH | `/api/internal/hospitals/:id/` | Update hospital |
| POST | `/api/internal/hospitals/:id/activate/` | Activate hospital |
| POST | `/api/internal/hospitals/:id/deactivate/` | Deactivate hospital |
| POST | `/api/internal/hospitals/:id/impersonate/` | Get admin token |
| GET | `/api/internal/stats/` | Platform-wide KPIs |

### Admin Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/internal/admin/kpis/` | KPI cards |
| GET | `/api/internal/admin/system-overview-chart/` | 7-day chart data |
| GET | `/api/internal/admin/module-status/` | Module operational status |
| GET | `/api/internal/admin/system-alerts/` | Infrastructure alerts |
| GET | `/api/internal/admin/user-activity/` | Login activity |
| GET | `/api/internal/admin/audit-summary/` | Audit log summary |
| GET | `/api/internal/admin/security-overview/` | Security metrics |
| GET | `/api/internal/admin/recent-activities/` | Recent system activities |
| GET | `/api/internal/admin/database-storage/` | Storage metrics |
| GET | `/api/internal/admin/license-info/` | License info |
| GET | `/api/internal/admin/system-info/` | Django/Python version |

### Django Admin

The Django admin at `/admin/` provides CRUD for:
- Hospitals (tenants) with inline staff/role management
- Admin modules, system alerts, departments
- System settings, workflows, device integrations
- Security policies, backup records, licenses
- Users with hospital profiles

## Database

This project shares the same PostgreSQL database as the main MedOS backend.
Managed models (Hospital, AdminModule, etc.) are owned here.
Unmanaged models (Role, HospitalUserProfile, Patient, Encounter, Invoice)
use `Meta.managed = False` and `db_table` to read/write existing tables.

## Authentication

All API endpoints (except login) require:
1. A valid staff user (`is_staff=True`)
2. Token authentication (DRF `TokenAuthentication`)

Login returns a token that must be sent as `Authorization: Token <key>`.
