# UniVote

University student council election management system. Admins configure election
cycles, positions, and candidates; voters cast a single ballot; auditors review
turnout, results, and integrity signals.

> **Status:** rebuild in progress. This README is replaced with full setup and
> deployment instructions in Phase 9.

---

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
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
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

Creates a demo election with voters, candidates, and ballots. Demo accounts use
`@test.com` addresses with development-only passwords printed to the console.

Never run this against a database holding a real election.

## Roles

| Role | Can |
|---|---|
| Admin | Create and publish elections, define positions, import voters, register candidates, manage the roster |
| Voter | Change their initial password, view their ballot, cast it once |
| Auditor | View turnout, results, voting timeline, and integrity signals (read-only) |

## A note on ballot privacy

Ballots are recorded once per voter and every submission is timestamped for
audit. The receipt code returned after voting confirms that a ballot was
recorded — it is not a cryptographic proof, and this system does not provide a
cryptographically secret ballot. Anyone with direct database access can
determine how a given voter voted. Treat it accordingly when deciding where to
use it.

## License

MIT
