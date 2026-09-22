# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Django 6.1 + Django REST Framework backend for the Shorolikoron platform. Serves two independent Flutter clients over one JWT-authenticated REST API — there is no server-rendered frontend beyond the Django admin.

Related sibling repos (`../shorolikoron-flutter/`, not in this working tree):
- `shorolikoron` — the customer-facing app: browse the service catalog, submit service requests, track them. Its own `CLAUDE.md` documents the client side of the same API described here.
- `shorolikoron-representative` — the representative-facing app: view assigned tasks, confirm/dismiss them, manage availability, view profile (skills/coverage). Auth, task list, availability, and profile are all wired to this backend's JWT API — see that repo's `CLAUDE.md`.

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
- **`accounts`** — identity. Wraps Django's built-in `auth.User` with two optional one-to-one profiles: `Customer` and `Representative` (`accounts/models.py`). There is no explicit role field — "what a user is" is purely determined by *which profile row exists* (`hasattr(request.user, "customer")` / `"representative")`). Nothing currently prevents a `User` from having both. `User.username` is always set equal to the user's email. `Representative` also carries `is_available`/`availability_updated_at` and a free-text `coverage_area` (admin-editable, e.g. "Dhaka campus routes"), plus a related `RepresentativeSkill` set (`name`, `level` — a `SkillLevel` TextChoices of beginner/intermediate/advanced — and an optional `note`), all admin-assigned via a `RepresentativeSkillInline` on `RepresentativeAdmin`; there is no representative-facing write path for skills or coverage, by design. Representative onboarding is request-based: `RepresentativeApplication` (name/email/password_hash/status) is submitted by the app, and only an admin action (`approve_applications`/`reject_applications` on `RepresentativeApplicationAdmin`) provisions the actual `User`+`Representative` row — there is no representative self-registration endpoint.
- **`tasks`** — the domain: `Service` (the catalog customers browse) and `ServiceRequest` (what a customer submits against a service, or a custom request), plus `TaskDismissal` (an audit row created every time a representative dismisses a request). `tasks/permissions.py` has `IsCustomer`/`IsRepresentative`, which just check for the corresponding profile.
- **`core`** — an empty `startapp` scaffold, never given models/views/urls. Not wired into `config/urls.py`. Dead weight; safe to remove if you notice it's still empty.

**Auth is JWT (`djangorestframework-simplejwt`) — not Firebase, not session auth**, despite the project's name/history (see `git log`; it started as a Firebase-authenticated app on `main`/the initial commit and was fully converted on the `jwt-authentication` branch, now merged into `dev`). `REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]` is `IsAuthenticated` globally — every view needs `AllowAny` explicitly if it should be open. Three ways to get a token pair:
- `POST /api/auth/register/` (`accounts.views.RegisterView`, `AllowAny`) — name/email/password, creates a `User` + **`Customer`** profile. There is no equivalent self-service path for representatives — see `RepresentativeApplication` above; a rep only gets a `User` once an admin approves their application.
- `POST /api/auth/google/` (`GoogleLoginView`, `AllowAny`) — verifies a Google ID token against `GOOGLE_OAUTH_CLIENT_ID` (`accounts/google_auth.py`), `get_or_create`s a `User` by email, and — like register — always provisions a **Customer** profile if the user has none.
- `POST /api/auth/login/` (SimpleJWT's stock `TokenObtainPairView`) — plain `username`/`password` (username = email). Works for both roles; a representative's `User`/`Representative` row is created by admin approval of their application (or, for one-off testing, by hand via Django admin/shell).
- `POST /api/auth/refresh/` — stock `TokenRefreshView`.
- `GET /api/auth/me/` (`MeView`, `IsAuthenticated`) — branches on whichever of `request.user.customer`/`request.user.representative` exists and returns a unified shape: `{id, email, name, phone, role, is_available, coverage_area, skills}` — `is_available`/`coverage_area` are `null` and `skills` is `[]` for a customer. `role` is `"representative"` or `"customer"`, derived the same way as everywhere else (`hasattr`, not a stored field).

**Full route table** (`config/urls.py` + `tasks/urls.py` + `accounts/urls.py`):

| Method | Path | View | Auth |
|---|---|---|---|
| POST | `/api/auth/register/` | `RegisterView` | `AllowAny` |
| POST | `/api/auth/google/` | `GoogleLoginView` | `AllowAny` |
| GET | `/api/auth/me/` | `MeView` | `IsAuthenticated` |
| POST | `/api/auth/login/` | `TokenObtainPairView` | `AllowAny` |
| POST | `/api/auth/refresh/` | `TokenRefreshView` | `AllowAny` |
| POST | `/api/auth/representative-applications/` | `RepresentativeApplicationCreateView` | `AllowAny` |
| GET | `/api/services/` | `ServiceListView` | `IsAuthenticated` (any profile) |
| POST | `/api/service-requests/` | `ServiceRequestCreateView` | `IsAuthenticated, IsCustomer` |
| GET | `/api/rep/tasks/` | `RepAssignedTasksView` | `IsAuthenticated, IsRepresentative` |
| POST | `/api/rep/tasks/<id>/confirm/` | `RepConfirmTaskView` | `IsAuthenticated, IsRepresentative` |
| POST | `/api/rep/tasks/<id>/undo-confirm/` | `RepUndoConfirmTaskView` | `IsAuthenticated, IsRepresentative` |
| POST | `/api/rep/tasks/<id>/dismiss/` | `RepDismissTaskView` | `IsAuthenticated, IsRepresentative` |
| POST | `/api/rep/availability/` | `RepAvailabilityView` | `IsAuthenticated, IsRepresentative` |

**Task lifecycle:** a `ServiceRequest` starts `pending`. **Assignment to a representative happens only through the Django admin** (`ServiceRequestAdmin.list_editable = ("assigned_representative",)`) — there is no API for a rep to claim a task or for the app to assign one. A `pre_save` signal (`tasks/models.py`) resets status back to `PENDING` whenever admin reassigns an existing request to a *different* rep. A rep can then `confirm` (→ `CONFIRMED`, undoable via `undo-confirm`) or `dismiss` (→ `DISMISSED`, requires a `reason` from the `DismissReason` choices + optional free-text `note`, writes a `TaskDismissal` row, and clears `assigned_representative` so admin can reassign it).

**Error handling convention:** DRF's default validation-error shapes are used as-is rather than a custom envelope — `{"field": ["message"]}` for serializer validation, `{"detail": "message"}` for permission/auth failures. Both client apps' repositories are written to handle both shapes (see their own `CLAUDE.md`s). Follow this for new endpoints rather than inventing a new error shape.

## Known rough edges (real, not hypothetical — check before assuming otherwise)

- **DB password is a hardcoded literal in `config/settings.py`** (`REPLACE_WITH_YOUR_PASSWORD`), not read from `.env`, even though `django-environ` is set up and used for `GOOGLE_OAUTH_CLIENT_ID`. The `.env` file exists but is empty. If you rotate the local Postgres password, you're editing a tracked file — worth moving to `env()` properly at some point.
- **`SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"] = True` but `rest_framework_simplejwt.token_blacklist` is not in `INSTALLED_APPS`/migrated** — this setting is likely a silent no-op (or will error) as configured.
- **There is deliberately no representative self-registration endpoint.** `RegisterView`/`GoogleLoginView` can only ever produce a `Customer` — a representative's `User`+`Representative` row is only ever created by an admin approving a `RepresentativeApplication`. Don't bolt rep account creation onto `RegisterSerializer`, which is customer-specific by design.
- `accounts/authentication.py` is an empty, unreferenced file — leftover from the pre-JWT Firebase auth backend. Dead.
- `tasks.models.ServiceCategory` (a `TextChoices`) is defined but no field references it anymore (removed by migration `0002_rename_description_servicerequest_details_and_more`, which replaced fixed categories with free-text `service_title`). Dead.
- `rest_framework.authtoken` is installed but unused — JWT is the only active `DEFAULT_AUTHENTICATION_CLASSES` entry.
- `MAILERS` in `settings.py` is not a real Django setting (`EMAIL_BACKEND` is) — likely a no-op leftover, not actually wired to anything.
- `ServiceRequestCreateSerializer` is reused as the rep task-list serializer even though it omits fields a rep UI would plausibly want (`assigned_representative`, `dismiss_reason`, `dismiss_note`, `updated_at`) — a source comment already flags this (`# or a dedicated RepTaskSerializer`).
- `core` app is empty and unwired — see above.
- No tests beyond stub `tests.py` files, no CI/lint config, no README elsewhere in the repo.

## Git branches

`main` is behind `dev` (stale). `dev` is the active mainline — `jwt-authentication` (the Firebase→JWT rewrite) and the services-in-Postgres work have both been merged into it. Branch off `dev` for new work; don't push directly to it.
