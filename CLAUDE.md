# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Django 6.1 + Django REST Framework backend for the Shorolikoron platform. Serves two independent Flutter clients over one JWT-authenticated REST API — there is no server-rendered frontend beyond the Django admin.

Related sibling repos (`../shorolikoron-flutter/`, not in this working tree):
- `shorolikoron` — the customer-facing app: browse the service catalog, submit service requests, track them. Its own `CLAUDE.md` documents the client side of the same API described here.
- `shorolikoron-representative` — the representative-facing app: view assigned tasks, confirm/dismiss them, manage availability. As of this writing its auth is still UI-only (no real backend wiring) — see that repo's `CLAUDE.md`.

## Commands

```bash
python manage.py runserver 127.0.0.1:8000   # dev server (ALLOWED_HOSTS assumes this + the Android emulator alias)
python manage.py makemigrations             # after model changes
python manage.py migrate
python manage.py seed_services              # upserts the Service catalog by title — safe to re-run
python manage.py createsuperuser            # for /admin/ access
```

Virtualenv lives at `venv/` in the repo root — activate it before running any of the above.

## Architecture

**Two real apps, one empty scaffold:**
- **`accounts`** — identity. Wraps Django's built-in `auth.User` with two optional one-to-one profiles: `Customer` and `Representative` (`accounts/models.py`). There is no explicit role field — "what a user is" is purely determined by *which profile row exists* (`hasattr(request.user, "customer")` / `"representative")`). Nothing currently prevents a `User` from having both. `User.username` is always set equal to the user's email.
- **`tasks`** — the domain: `Service` (the catalog customers browse) and `ServiceRequest` (what a customer submits against a service, or a custom request), plus `TaskDismissal` (an audit row created every time a representative dismisses a request). `tasks/permissions.py` has `IsCustomer`/`IsRepresentative`, which just check for the corresponding profile.
- **`core`** — an empty `startapp` scaffold, never given models/views/urls. Not wired into `config/urls.py`. Dead weight; safe to remove if you notice it's still empty.

**Auth is JWT (`djangorestframework-simplejwt`) — not Firebase, not session auth**, despite the project's name/history (see `git log`; it started as a Firebase-authenticated app on `main`/the initial commit and was fully converted on the `jwt-authentication` branch, now merged into `dev`). `REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]` is `IsAuthenticated` globally — every view needs `AllowAny` explicitly if it should be open. Three ways to get a token pair:
- `POST /api/auth/register/` (`accounts.views.RegisterView`, `AllowAny`) — name/email/password, creates a `User` + **`Customer`** profile. There is no equivalent for representatives; see the caveat below.
- `POST /api/auth/google/` (`GoogleLoginView`, `AllowAny`) — verifies a Google ID token against `GOOGLE_OAUTH_CLIENT_ID` (`accounts/google_auth.py`), `get_or_create`s a `User` by email, and — like register — always provisions a **Customer** profile if the user has none.
- `POST /api/auth/login/` (SimpleJWT's stock `TokenObtainPairView`) — plain `username`/`password` (username = email). This is the only path that works for a representative today, since nothing else can produce one — a `Representative` row currently has to be created by hand (Django admin, shell, or a fixture).
- `POST /api/auth/refresh/` — stock `TokenRefreshView`.
- `GET /api/auth/me/` (`MeView`, `IsAuthenticated`) — **only reads `request.user.customer`**; a representative hitting this gets blank `name`/`phone` even though `Representative` has real data. Fix this (branch on which profile exists) before the representative app relies on it.

**Full route table** (`config/urls.py` + `tasks/urls.py` + `accounts/urls.py`):

| Method | Path | View | Auth |
|---|---|---|---|
| POST | `/api/auth/register/` | `RegisterView` | `AllowAny` |
| POST | `/api/auth/google/` | `GoogleLoginView` | `AllowAny` |
| GET | `/api/auth/me/` | `MeView` | `IsAuthenticated` |
| POST | `/api/auth/login/` | `TokenObtainPairView` | `AllowAny` |
| POST | `/api/auth/refresh/` | `TokenRefreshView` | `AllowAny` |
| GET | `/api/services/` | `ServiceListView` | `IsAuthenticated` (any profile) |
| POST | `/api/service-requests/` | `ServiceRequestCreateView` | `IsAuthenticated, IsCustomer` |
| GET | `/api/rep/tasks/` | `RepAssignedTasksView` | `IsAuthenticated, IsRepresentative` |
| POST | `/api/rep/tasks/<id>/confirm/` | `RepConfirmTaskView` | `IsAuthenticated, IsRepresentative` |
| POST | `/api/rep/tasks/<id>/undo-confirm/` | `RepUndoConfirmTaskView` | `IsAuthenticated, IsRepresentative` |
| POST | `/api/rep/tasks/<id>/dismiss/` | `RepDismissTaskView` | `IsAuthenticated, IsRepresentative` |

**Task lifecycle:** a `ServiceRequest` starts `pending`. **Assignment to a representative happens only through the Django admin** (`ServiceRequestAdmin.list_editable = ("assigned_representative",)`) — there is no API for a rep to claim a task or for the app to assign one. A `pre_save` signal (`tasks/models.py`) resets status back to `PENDING` whenever admin reassigns an existing request to a *different* rep. A rep can then `confirm` (→ `CONFIRMED`, undoable via `undo-confirm`) or `dismiss` (→ `DISMISSED`, requires a `reason` from the `DismissReason` choices + optional free-text `note`, writes a `TaskDismissal` row, and clears `assigned_representative` so admin can reassign it).

**Error handling convention:** DRF's default validation-error shapes are used as-is rather than a custom envelope — `{"field": ["message"]}` for serializer validation, `{"detail": "message"}` for permission/auth failures. Both client apps' repositories are written to handle both shapes (see their own `CLAUDE.md`s). Follow this for new endpoints rather than inventing a new error shape.

## Known rough edges (real, not hypothetical — check before assuming otherwise)

- **DB password is a hardcoded literal in `config/settings.py`** (`REPLACE_WITH_YOUR_PASSWORD`), not read from `.env`, even though `django-environ` is set up and used for `GOOGLE_OAUTH_CLIENT_ID`. The `.env` file exists but is empty. If you rotate the local Postgres password, you're editing a tracked file — worth moving to `env()` properly at some point.
- **`SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"] = True` but `rest_framework_simplejwt.token_blacklist` is not in `INSTALLED_APPS`/migrated** — this setting is likely a silent no-op (or will error) as configured.
- **No representative self-registration path exists.** `RegisterView`/`GoogleLoginView` can only ever produce a `Customer`. If you're building the "request to become a representative, admin approves" flow, this is the gap it fills — don't bolt it onto `RegisterSerializer`, which is customer-specific by design.
- `accounts/authentication.py` is an empty, unreferenced file — leftover from the pre-JWT Firebase auth backend. Dead.
- `tasks.models.ServiceCategory` (a `TextChoices`) is defined but no field references it anymore (removed by migration `0002_rename_description_servicerequest_details_and_more`, which replaced fixed categories with free-text `service_title`). Dead.
- `rest_framework.authtoken` is installed but unused — JWT is the only active `DEFAULT_AUTHENTICATION_CLASSES` entry.
- `MAILERS` in `settings.py` is not a real Django setting (`EMAIL_BACKEND` is) — likely a no-op leftover, not actually wired to anything.
- `ServiceRequestCreateSerializer` is reused as the rep task-list serializer even though it omits fields a rep UI would plausibly want (`assigned_representative`, `dismiss_reason`, `dismiss_note`, `updated_at`) — a source comment already flags this (`# or a dedicated RepTaskSerializer`).
- `core` app is empty and unwired — see above.
- No tests beyond stub `tests.py` files, no CI/lint config, no README elsewhere in the repo.

## Git branches

`main` is behind `dev` (stale). `dev` is the active mainline — `jwt-authentication` (the Firebase→JWT rewrite) and the services-in-Postgres work have both been merged into it. Branch off `dev` for new work; don't push directly to it.
