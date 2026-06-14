# RBAC System

[![CI](https://github.com/Safaraliyev05/RBAC/actions/workflows/ci.yml/badge.svg)](https://github.com/Safaraliyev05/RBAC/actions/workflows/ci.yml)
[![Build & Push Images](https://github.com/Safaraliyev05/RBAC/actions/workflows/docker-build.yml/badge.svg)](https://github.com/Safaraliyev05/RBAC/actions/workflows/docker-build.yml)

A production-ready, secure Role-Based Access Control system built with Django REST Framework (backend) and React + TypeScript + Vite (frontend). Containerised with Docker, deployed to Kubernetes/k3s via a **Helm chart** and **Argo CD** (GitOps), with **GitHub Actions** CI/CD and **Prometheus** monitoring.

## Architecture Overview

```
RBAC/
├── backend/                   # Django project
│   ├── config/                # Settings, URLs, WSGI
│   ├── apps/
│   │   ├── accounts/          # Custom User model, auth endpoints, JWT, lockout
│   │   ├── rbac/              # Role, Permission, UserRole models + DRF permission classes
│   │   └── audit/             # AccessLog model, middleware, report endpoints
│   ├── .env.example
│   └── requirements.txt
├── frontend/                  # Vite + React + TypeScript
│   └── src/
│       ├── api/               # Axios instance + auth/rbac/audit API clients
│       ├── contexts/          # AuthContext (user state, login/logout/register)
│       ├── components/        # Layout (AppLayout, ProtectedRoute), UI (Alert, Pagination)
│       ├── pages/             # Login, Register, Dashboard, Profile, Admin, Audit
│       └── types/             # TypeScript interfaces matching backend serializers
├── README.md
├── SECURITY.md
└── .gitignore
```

## RBAC Model

### Entities
- **User** — custom email-based user with lockout fields
- **Permission** — `resource.action` codename (e.g. `users.create`, `audit.read`)
- **Role** — named set of permissions (M2M via `RolePermission`)
- **UserRole** — assigns a role to a user (M2M via `UserRole`, records `assigned_by`)

### Permission Matrix

| Permission Codename | Admin | Auditor | User |
|---|---|---|---|
| users.create / read / update / delete | All | read | - |
| roles.create / read / update / delete | All | read | - |
| permissions.read | Yes | Yes | - |
| permissions.assign | Yes | - | - |
| audit.read | Yes | Yes | - |
| audit.export | Yes | Yes | - |
| reports.view | Yes | Yes | - |
| profile.read / update | Yes | Yes | Yes |

### How authorization works
1. Each DRF view declares a required permission codename.
2. `rbac_permission('codename')` returns a permission class that calls `user.has_rbac_permission(codename)`.
3. `has_rbac_permission` aggregates permissions from all of the user's roles (via `UserRole → Role → Permission`).
4. Django superusers (`is_superuser=True`) bypass all RBAC checks.

## Universal model-driven permissions

This RBAC app is **reusable across projects**. Drop it in, add your own models, and
permissions are generated for you — you never hand-edit a permission list.

- **Discovery engine** — `apps/rbac/permission_sync.py` scans every installed model and
  upserts a permission per action using the convention `app_label.model.action`
  (e.g. `blog.post.create`, `blog.post.read`, …).
- **Automatic** — discovery runs on Django's `post_migrate` signal, so the workflow is
  simply: *write a model → `makemigrations` → `migrate`* and its permissions appear.
- **Manual / CI** — `python manage.py sync_permissions [--prune]`.
- **From the UI** — admins can click **Sync from models** on the Permissions page
  (`POST /api/rbac/permissions/sync/`, gated by `permissions.sync`).
- **Managed vs custom** — auto-generated permissions are flagged `managed=True` and linked
  to their model's `ContentType`. Hand-defined "management" permissions
  (`users.create`, `audit.export`, …) live in `RBAC_CUSTOM_PERMISSIONS` and are never pruned.
- **Admin auto-grant** — every sync attaches any newly discovered permission to the
  superuser role (`RBAC_SUPERUSER_ROLE`, default `Admin`), so admins get access to new
  models immediately without re-seeding. Set it to `None` to disable.
- **Seeding** — `seed_data` runs discovery first, then grants the **Admin** role *every*
  permission (including future model permissions).

### Configuration (settings.py / .env)

| Setting | Default | Purpose |
|---|---|---|
| `RBAC_AUTO_DISCOVER` | `True` | Run discovery automatically after every `migrate` |
| `RBAC_AUTO_PRUNE` | `False` | Delete managed permissions whose model is gone |
| `RBAC_PERMISSION_ACTIONS` | `create, read, update, delete, list, export` | Actions generated per model |
| `RBAC_EXCLUDED_APPS` | `admin, auth, contenttypes, sessions, token_blacklist` | Apps to skip |
| `RBAC_EXCLUDED_MODELS` | RBAC's own through-tables | `app_label.model` entries to skip |
| `RBAC_CUSTOM_PERMISSIONS` | management permissions | Non-model permissions to always ensure |
| `RBAC_SUPERUSER_ROLE` | `Admin` | Role auto-granted every permission on each sync (`None` to disable) |

## Setup & Run Instructions

### Prerequisites
- Python 3.13+
- Node 25+ / npm 11+

### Backend

```bash
# 1. Create and activate virtual environment
cd /home/sardor/PycharmProjects/RBAC/backend
python3 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and set SECRET_KEY to a long random string

# 4. Run migrations
python manage.py makemigrations accounts rbac audit
python manage.py migrate

# 5. Seed default roles, permissions, and admin user
python manage.py seed_data

# 6. Start development server
python manage.py runserver 0.0.0.0:8000
```

### Frontend

```bash
cd /home/sardor/PycharmProjects/RBAC/frontend
npm install
npm run dev    # starts at http://localhost:5173
```

## Default Admin Credentials

**CHANGE THESE IMMEDIATELY IN PRODUCTION**

| Field | Value |
|---|---|
| Email | `admin@example.com` |
| Password | `Admin@1234!` |
| Role | Admin (all permissions) |

To change: log in and use the Change Password feature, or run:
```bash
python manage.py seed_data --admin-email your@email.com --admin-password 'YourNewPassword!'
```

## API Endpoint Reference

### Authentication — `/api/auth/`
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register/` | Register a new user |
| POST | `/api/auth/login/` | Login, returns access + refresh tokens |
| POST | `/api/auth/logout/` | Blacklist refresh token |
| POST | `/api/auth/token/refresh/` | Refresh access token |
| GET/PATCH | `/api/auth/profile/` | View/update own profile |
| POST | `/api/auth/change-password/` | Change own password |

### RBAC Admin — `/api/rbac/`
| Method | Endpoint | Permission required |
|---|---|---|
| GET | `/api/rbac/permissions/` | `permissions.read` |
| POST | `/api/rbac/permissions/sync/` | `permissions.sync` |
| GET/POST | `/api/rbac/roles/` | `roles.read` / `roles.create` |
| GET/PATCH/DELETE | `/api/rbac/roles/{id}/` | `roles.read` / `roles.update` / `roles.delete` |
| GET/POST | `/api/rbac/users/` | `users.read` / `users.create` |
| GET/PATCH/DELETE | `/api/rbac/users/{id}/` | `users.read` / `users.update` / `users.delete` |
| POST | `/api/rbac/users/{id}/assign-roles/` | `roles.update` |
| GET | `/api/rbac/users/{id}/roles/` | `users.read` |
| DELETE | `/api/rbac/users/{id}/roles/{role_id}/remove/` | `roles.update` |

### Audit — `/api/audit/`
| Method | Endpoint | Permission required |
|---|---|---|
| GET | `/api/audit/logs/` | `audit.read` |
| GET | `/api/audit/logs/export/` | `audit.export` |
| GET | `/api/audit/reports/summary/` | `reports.view` |
| GET | `/api/audit/reports/login-failures/` | `reports.view` |

#### Audit log filters
`user_email`, `user_id`, `action`, `result` (success/failure/denied/locked), `http_method`, `path`, `ip_address`, `date_from`, `date_to`, `resource`

## Testing

The backend ships with an automated test suite (`apps/*/tests.py`) covering authentication
and lockout, RBAC permission discovery/aggregation/enforcement, and audit logging/reporting.

```bash
cd backend
pytest                     # or: python manage.py test apps
```

GitHub Actions runs the suite on every push (see the CI badge above).

## Deployment

### Docker Compose (local)

```bash
docker compose up --build
# backend → http://localhost:8000   frontend → http://localhost:8080
```

### Container images (GitHub Actions → Docker Hub)

`.github/workflows/docker-build.yml` builds and pushes both images to Docker Hub on every
push to `main` (requires repo secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`):

- `safaral1yev05/rbac-backend:latest`
- `safaral1yev05/rbac-frontend:latest`

### Kubernetes / k3s via Helm

The `rbac/` directory is a Helm chart (backend + frontend + PostgreSQL + Ingress +
Prometheus `ServiceMonitor`).

```bash
# render / lint
helm lint rbac
helm template rbac-platform rbac -n rbac

# install (k3s or any cluster)
helm install rbac-platform rbac -n rbac --create-namespace

# run the chart's smoke test
helm test rbac-platform -n rbac
```

The backend exposes `/health/` (probes) and `/metrics` (Prometheus, scraped by the
`ServiceMonitor` in the `monitoring` namespace).

### GitOps with Argo CD

`argocd/application.yaml` defines an Argo CD `Application` that watches the `rbac/` chart in
this repository and continuously reconciles the cluster to match Git.

```bash
kubectl apply -f argocd/application.yaml
```

## CI/CD pipeline

| Workflow | Trigger | Does |
|---|---|---|
| `ci.yml` | push / PR | Backend `manage.py check` + migrations + `pytest`; frontend lint + build |
| `docker-build.yml` | push to `main` | Build & push backend/frontend images to Docker Hub |
| Argo CD | Git change | Sync the Helm chart to the k3s cluster (prune + self-heal) |

## Security

See [SECURITY.md](./SECURITY.md) for full threat model, OWASP Top 10 mapping, and ethical considerations.
