# TestPulse — Roadmap

> A back-end service that collects test results from CI pipelines, stores their history, and answers the questions a single pipeline run can't: **Which tests are flaky? What's getting slower? What broke since yesterday?**

---

## Why this project

- **Clear problem.** Anyone who has worked with CI understands it in ten seconds.
- **Real back-end work.** Ingesting, modelling, querying and serving data through an API.
- **Built on domain expertise.** It comes from years of test automation experience: Robot Framework, pytest, Azure DevOps.
- **Grows out of existing work.** The CI result notifier (Azure DevOps result parsing and notifications) gets ported in at a later milestone.

---

## MVP scope

### Must have
1. **Ingest:** `POST /projects/{id}/runs` accepts a JUnit XML report and stores the run.
2. **Query:** list runs, get one run's details, and see one test case's history.
3. **Flaky detection:** flag tests whose status flipped between pass and fail in the last N runs on the same branch.
4. **Auth:** an API key per project, stored as a hash.
5. **Quality bar:** a pytest suite with unit and integration tests, CI on GitHub Actions, Docker Compose to run locally, and auto-generated OpenAPI docs.

### Should have (after the MVP)
- Robot Framework `output.xml` parser
- Pulling runs directly from the Azure DevOps API (the notifier code moves in here)
- Teams webhook notification when a new failure appears (the existing notifier, refactored)
- Trend endpoints: slowest tests and failure rate over time

### Out of scope
- Front-end. The OpenAPI docs page is the UI.
- Users and roles beyond API keys
- Microservices

---

## Stack

| Layer | Choice | Why |
|---|---|---|
| API | FastAPI + Pydantic | API-first, type hints, built-in OpenAPI docs |
| Database | PostgreSQL | Industry standard; SQLite hides real database problems |
| ORM and migrations | SQLAlchemy 2.0 + Alembic | Standard pairing; safe schema changes |
| Testing | pytest | Existing strength; becomes the showcase |
| Tooling | `pyproject.toml`, ruff, Docker Compose, GitHub Actions | Professional repo hygiene |

---

## Data model

```
project    (id, name, api_key_hash, created_at)
run        (id, project_id → project, branch, commit_sha, source,
            started_at, duration_ms, total, passed, failed, skipped)
test_case  (id, project_id → project, suite, name)
           UNIQUE(project_id, suite, name)
result     (id, run_id → run, test_case_id → test_case,
            status, duration_ms, failure_message)
```

**Key design decision:** `test_case` is separate from `result`, so a single test can be followed across hundreds of runs. Flaky detection and trends depend on this.

---

## Repo structure

```
testpulse/
├── src/testpulse/
│   ├── api/            # routes: thin, no business logic
│   ├── domain/         # plain Python models: no FastAPI, no DB
│   ├── parsers/        # base.py (abstract parser), junit.py, robot.py
│   ├── services/       # flakiness.py, ingest.py: business logic
│   ├── db/             # SQLAlchemy models, session, repositories
│   └── notifiers/      # teams.py (ported CI notifier)
├── tests/
│   ├── unit/           # parsers, services: fast, no DB
│   └── integration/    # API + real Postgres via Docker
├── alembic/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── .github/workflows/ci.yml
└── README.md           # problem, architecture diagram, how to run
```

**Design note:** `parsers/` uses an abstract `ResultParser` base class with one subclass per report format (strategy pattern). Adding a new format means adding a class, without touching existing code.

---

## Milestones

Pace: 6–10 hours a week. Total: about 18 weeks.

### M1 — Skeleton and first parser (weeks 1–3)
- [ ] Create the GitHub repo `testpulse` and clone it locally
- [ ] `pyproject.toml` with the `src/` layout
- [ ] `.gitignore` for Python (`__pycache__/`, `.venv/`, `.pytest_cache/`)
- [ ] ruff and pytest configured
- [ ] GitHub Actions workflow running lint and tests, with the CI badge green
- [ ] Domain models: `TestRun`, `TestResult` (plain dataclasses)
- [ ] Abstract `ResultParser` and a `JUnitParser` implementation
- [ ] Unit tests for the parser, including edge cases: empty report, skipped tests, malformed XML

**Done when:** CI is green and the JUnit parser is fully unit-tested. No database or API yet.

### M2 — Persistence and ingest (weeks 4–7)
- [ ] Postgres in `docker-compose.yml`
- [ ] SQLAlchemy models matching the data model above
- [ ] Alembic set up, with the first migration
- [ ] `POST /projects/{id}/runs` endpoint storing a parsed run
- [ ] Integration tests against real Postgres in CI

**Done when:** a JUnit report can be uploaded and is stored correctly.

### M3 — Query and flaky detection (weeks 8–11)
- [ ] `GET /projects/{id}/runs` with pagination
- [ ] `GET /runs/{id}`
- [ ] `GET /test-cases/{id}/history`
- [ ] Flaky detection service, unit-tested with crafted run histories
- [ ] `GET /projects/{id}/flaky-tests`

**Done when:** flaky tests are correctly identified from a seeded history.

### M4 — Auth, Robot Framework and notifications (weeks 12–15)
- [ ] API-key auth per project (hashed keys)
- [ ] `RobotParser` for `output.xml`
- [ ] Teams notifier (port and refactor the CI notifier)
- [ ] Notification triggered on new failures

**Done when:** an authenticated upload of a Robot Framework report triggers a notification on a new failure.

### M5 — Ship it (weeks 16–18)
- [ ] Deploy to a public host
- [ ] README: the problem, an architecture diagram, run instructions, design decisions
- [ ] Pin the repo on the GitHub profile
- [ ] LinkedIn post on what was built and why

**Done when:** a stranger can understand, run and try the service from the README alone.

---

## Working agreements

- **Small, frequent commits** with clear messages.
- **Every feature comes with tests.** No milestone is done with failing or missing tests.
- **Work in feature branches with PRs, even solo.** This shows a professional workflow.
- **Log decisions.** Record notable design choices in the README; they become interview material.
