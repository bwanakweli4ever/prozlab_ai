# Prozlab Backend API

FastAPI backend for **Prozlab** — an AI-powered hiring platform that vets candidates based on real-world work, not interviews.

## Product domains

| Module | Purpose |
|--------|---------|
| **auth** | User accounts, JWT login, email verification, password reset |
| **onboarding** | 7-step candidate wizard (expertise → experience → preferences → portfolio → skills → profile) |
| **proz** | Candidate profiles, public directory, AI resume tools, admin verification |
| **tasks** | Employer hiring requests and professional assignments |

## Getting started

### Prerequisites

- Python 3.12+
- PostgreSQL

### Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # configure DB, JWT, SMTP, OPENAI_API_KEY
python setup_db.py
alembic upgrade head
python app/scripts/seed_hiring_specialties.py
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Onboarding API

Base path: `/api/v1/onboarding` (requires Bearer token)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/status` | Current step, completed steps, saved data |
| POST | `/start` | Initialize onboarding for user |
| PATCH | `/step` | Save step data and advance |
| POST | `/complete` | Sync onboarding data to candidate profile |

### Step payload example

```json
{
  "step": "expertise",
  "data": { "skills": ["Product Design", "UI/UX", "Figma"] }
}
```

Steps: `welcome`, `expertise`, `experience`, `preferences`, `portfolio`, `skills_verification`, `profile`

## Candidate profile fields (new)

- `skills` — expertise tags (JSON array)
- `work_types` — full-time, contract, freelance, part-time
- `experience_level` — e.g. "3-5 years"
- `portfolio_links` — project/portfolio URLs
- `skill_verification_status` — not_started | in_progress | verified
- `onboarding_completed` — boolean
- `predicted_success_score` — AI match score (0–100)

## Environment variables

See `.env` for `DB_*`, `SECRET_KEY`, `SMTP_*`, `OPENAI_API_KEY`, `CORS_ORIGINS`.
