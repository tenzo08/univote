# UniVote

University student council election management system. Admins configure election
cycles, positions, and candidates; voters cast a single ballot; auditors review
turnout, results, and integrity signals.

## Stack

- **Backend** — Django 5 + Django REST Framework, JWT auth, PostgreSQL (SQLite locally)
- **Frontend** — React 18 + Vite, Tailwind CSS, TanStack Query, Recharts

## Requirements

| Layer | Requirement |
|---|---|
| Backend | Python 3.11+ |
| Frontend | Node.js 18+ and npm |

## Local setup

**Backend**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver        # http://127.0.0.1:8000
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env
npm run dev                       # http://localhost:5173
```

Run both at once in separate terminals, then open http://localhost:5173.

## Demo data

```bash
cd backend
python manage.py seed_demo --reset
```

Creates one archived election, one live published election with staggered
ballots, one draft election, and roughly 60 bulk voters. Refuses to run
against a non-empty database unless `--reset` is passed.

Never run this against a database holding a real election — the accounts
below use fixed, publicly-known passwords, which is only acceptable because
this command only ever creates `@test.com` demo data.

| Account | Password | Role |
|---|---|---|
| `admin@test.com` | `DemoAdmin123!` | Admin |
| `auditor@test.com` | `DemoAuditor123!` | Auditor |
| `voter@test.com` | `DemoVoter123!` | Voter (already voted; password already changed) |
| `candidate@test.com` | `DemoCandidate123!` | Voter and a registered candidate |
| `bulkvoter<N>@test.com` (0–64) | their own student number, e.g. `bulk-0001` | Voter — forced to change their password on first login, same as a real CSV-imported voter |

## Roles

| Role | Can |
|---|---|
| Admin | Create and publish elections, define positions, import voters, register candidates, manage the roster |
| Voter | Change their initial password, view their ballot, cast it once |
| Auditor | View turnout, results, voting timeline, and integrity signals (read-only) |

## API

Base path `/api/`, JSON everywhere, errors as `{"detail": "..."}` or
DRF's field-level `{"field": ["..."]}`. JWT auth (`POST /api/auth/login/`,
`POST /api/auth/refresh/`) with three roles — `voter`, `admin`, `auditor` —
enforced per-endpoint. Elections, candidates, and the voter roster are
admin-managed; voting is a two-call flow (`GET
/api/voters/ballot-session/` then `POST /api/voters/cast-ballot/`); results,
turnout, timeline, and an integrity report are available to auditors and
admins once an election exists. The full endpoint-by-endpoint contract lives
in local project docs (not shipped with this repo) — read the Django views
in `backend/api/views/` and the URL table in `backend/api/urls.py` for the
authoritative list.

## Deployment

Backend on **Render** (Django + Postgres), frontend on **Vercel** (the Vite
build). Both have workable free tiers for a class project or a pilot
election — check current provider pricing before relying on any specific
limit, especially how long a free Postgres instance lives.

**Order matters:** deploy the backend first and note its URL, deploy the
frontend with that URL as `VITE_API_BASE_URL`, then go back and set the
backend's CORS/CSRF origins to the Vercel URL and redeploy the backend. A
CORS error after deploying the frontend almost always means this last step
was skipped.

### Backend (Render)

| Setting | Value |
|---|---|
| Root directory | `backend` |
| Runtime | Python 3 |
| Build command | `./build.sh` |
| Start command | `gunicorn univote.wsgi:application` |

Create the Postgres instance before the web service, so its internal
connection string is ready to paste into `DATABASE_URL`.

| Environment variable | Value |
|---|---|
| `DJANGO_SECRET_KEY` | generate fresh — see below, never reuse the local dev value |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `your-api.onrender.com` |
| `DATABASE_URL` | the Postgres internal connection string |
| `CORS_ALLOWED_ORIGINS` | `https://your-app.vercel.app` |
| `CSRF_TRUSTED_ORIGINS` | `https://your-app.vercel.app` |
| `PYTHON_VERSION` | `3.11.9` |

Generate a fresh secret key (never the value in `.env.example` or your local
`.env`):

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

After the first deploy, from a Render shell:

```bash
python manage.py createsuperuser
python manage.py seed_demo --reset   # demo instances ONLY — never a real election
```

Uploaded candidate photos will not survive a redeploy — Render's filesystem
is ephemeral. Acceptable for a demo; for real use, move `ImageField` storage
to S3 or Cloudinary via `django-storages` as a separate task. Free web
services also sleep after inactivity, so the first request after idle time
can take 30–60 seconds — expected, not a bug.

### Frontend (Vercel)

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Framework preset | Vite |
| Build command | `npm run build` |
| Output directory | `dist` |
| Environment variable | `VITE_API_BASE_URL=https://your-api.onrender.com` |

`vercel.json` already carries the SPA rewrite so refreshing on a route like
`/vote` doesn't 404. `VITE_*` variables are inlined at build time and are
public in the shipped bundle — changing one requires a redeploy, and none of
them may ever hold a secret.

### Pre-deploy checklist

- [ ] `DJANGO_DEBUG=False` in production
- [ ] `DJANGO_SECRET_KEY` freshly generated, not the local default
- [ ] `DJANGO_ALLOWED_HOSTS` does not contain `*`
- [ ] `CORS_ALLOWED_ORIGINS` lists the exact Vercel origin, not `*`
- [ ] No `.env` file tracked by git (`git ls-files | grep env` prints nothing)
- [ ] `python manage.py check --deploy` reviewed
- [ ] Full test suite green (`pytest` in `backend/`, `npm run test -- --run`
      in `frontend/`)
- [ ] Seed data absent from any non-demo instance

### Verifying a live deploy

```bash
curl -i https://your-api.onrender.com/api/elections/active/
# expect 401 — the endpoint requires auth, which means it's alive and protected
```

Then open the Vercel URL, log in as each of the three demo roles above, and
walk one journey per role. A green build is not a working app.

## A note on ballot privacy

Ballots are recorded once per voter and every submission is timestamped for
audit. The receipt code returned after voting confirms that a ballot was
recorded — it is not a cryptographic proof, and this system does not provide a
cryptographically secret ballot. Anyone with direct database access can
determine how a given voter voted. Treat it accordingly when deciding where to
use it.

## License

MIT
