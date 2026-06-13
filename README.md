# Arogya OS Internal — Hospital Tenant Management

Super admin panel for managing hospitals (tenants) on the Arogya OS platform.
Shares the same database as the main Arogya OS backend but only owns the Hospital/tenant-management tables.

| Layer | Tech | Port |
|---|---|---|
| **Backend** | Django REST API | `8001` |
| **Frontend** | React SPA (Vite + React 19 + TypeScript + Tailwind) | `5175` |

## Modules

- **Hospitals CRUD** — List, create, detail, update, activate/deactivate, impersonate
- **Admin Dashboard** — KPIs, charts, module status, alerts, user activity, audit, security, storage, license, system info
- **Django Admin** — at `/admin/`

## Quick Start

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Edit with your settings
python manage.py migrate
python manage.py runserver 8001
```

```bash
cd frontend
npm install
npm run dev -- --port 5175
```

## Auth

Staff login → token → `Authorization: Token <key>` header.

## Tech Stack

- **Backend:** Django 5, Django REST Framework, PostgreSQL
- **Frontend:** React 19, TypeScript, Vite, TanStack Query, Tailwind CSS v4
- **Auth:** Token-based authentication
