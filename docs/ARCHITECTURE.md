# TestPulse — Architecture Guide

This document explains **what** TestPulse is made of, **where** each piece of code lives, and **why** it is organised this way. Read this before writing code for a new part of the project.

---

## 1. The problem in one story

A pipeline runs your test suite every night. One morning `test_wrong_password` is red. You rerun it and it's green. A week later it's red again.

**Is it a real bug, or a flaky test?**

A single pipeline run can't answer that, because it only knows about *itself*. To answer it you need **history**: the results of the same test over many runs.

**TestPulse keeps that history and answers questions about it:**
- Which tests are flaky, meaning they flip between pass and fail without code changes?
- What broke since yesterday?
- Which tests are getting slower?

Robot Framework comparison: every run produces an `output.xml`. TestPulse is like keeping **all** those `output.xml` files in one place and analysing them together.

---

## 2. The journey of one test report

This is the most important section. Everything in the codebase exists to support this flow.

### Step 1: a test run produces a report

You run your tests with:

```bash
pytest --junitxml=report.xml
```

pytest writes a **JUnit XML** file. JUnit XML is a standard format that almost every test tool and CI system understands:

```xml
<testsuite name="pytest" tests="3" failures="1" skipped="1">
  <testcase classname="tests.test_login" name="test_valid_login" time="0.120"/>
  <testcase classname="tests.test_login" name="test_wrong_password" time="0.300">
    <failure message="assert 401 == 403">...</failure>
  </testcase>
  <testcase classname="tests.test_login" name="test_sso" time="0.000">
    <skipped message="SSO not configured"/>
  </testcase>
</testsuite>
```

Try it yourself: run `pytest --junitxml=report.xml` in the testpulse repo and open the file. That's real input data for your project.

### Step 2: the report is sent to TestPulse

The CI pipeline uploads the file to the TestPulse API:

```
POST /projects/1/runs     (body: report.xml)
```

→ handled by **`api/`**

### Step 3: the XML is translated into Python objects

The XML is just text. A **parser** reads it and turns it into objects that the rest of the code understands:

```python
TestRun(results=[
    TestResult(suite="tests.test_login", name="test_valid_login",
               status=Status.PASSED, duration_ms=120),
    TestResult(suite="tests.test_login", name="test_wrong_password",
               status=Status.FAILED, duration_ms=300, message="assert 401 == 403"),
    TestResult(suite="tests.test_login", name="test_sso",
               status=Status.SKIPPED, duration_ms=0, message="SSO not configured"),
])
```

→ the parser lives in **`parsers/`**, and `TestRun`, `TestResult` and `Status` live in **`domain/`**

### Step 4: the run is saved

The `TestRun` is stored in the PostgreSQL database, so it's still there tomorrow, next week, and after a restart.

→ handled by **`db/`**, coordinated by **`services/`**

### Step 5: later, someone asks a question

```
GET /projects/1/flaky-tests
```

TestPulse loads the last few runs of each test from the database and looks for flipping results:

```
test_wrong_password on main, last 5 runs:
  PASS → FAIL → PASS → PASS → FAIL     ← flipped 3 times → flaky
test_valid_login on main, last 5 runs:
  PASS → PASS → PASS → PASS → PASS     ← stable
```

→ the flaky logic lives in **`services/`** and the answer is returned by **`api/`**

### Step 6 (later): someone is notified

If a run contains a *new* failure, TestPulse posts a message to a Teams channel.

→ handled by **`notifiers/`** (your existing CI notifier code ends up here)

### The whole flow in one picture

```
 pytest / Robot / Azure DevOps
            │  report.xml
            ▼
        ┌────────┐
        │  api/  │  receives HTTP requests, returns answers
        └───┬────┘
            ▼
      ┌───────────┐
      │ services/ │  coordinates the work + business logic (flaky detection)
      └─┬───┬───┬─┘
        │   │   │
        ▼   │   ▼
 ┌──────────┐│ ┌──────────┐
 │ parsers/ ││ │   db/    │  stores and loads runs (PostgreSQL)
 └──────────┘│ └──────────┘
             ▼
       ┌────────────┐
       │ notifiers/ │  sends Teams messages
       └────────────┘

 All of these use the objects defined in:
       ┌──────────┐
       │ domain/  │  TestRun, TestResult, Status
       └──────────┘
```

---

## 3. Folder by folder

All application code lives in `src/testpulse/`. Each folder has **one job**.

### `domain/`: the vocabulary

| | |
|---|---|
| **Job** | Define what a test run *is* in plain Python |
| **Contains** | `models.py` with `Status`, `TestResult`, `TestRun` |
| **Depends on** | Nothing. No FastAPI, no database, no XML. |
| **Built in** | M1 (now) |

This is the *definitions article* of the project. Every other folder talks in these terms. Because it depends on nothing, it's the easiest code to test: no database, no server, and tests run in milliseconds.

**What each object represents:**
- `Status`: the possible outcomes of a test: passed, failed, skipped, error.
- `TestResult`: the outcome of **one test** in **one run**. It's frozen, meaning it can't be changed after it's created, because a result that already happened shouldn't change.
- `TestRun`: one complete execution of a test suite, holding many `TestResult`s. It can answer "how many passed?" by counting its results.

### `parsers/`: the translators

| | |
|---|---|
| **Job** | Turn an external report format into domain objects |
| **Contains** | `base.py` (`ResultParser`, the abstract "contract"), `junit.py` (`JUnitParser`), later `robot.py` (`RobotParser`) |
| **Depends on** | `domain/` |
| **Built in** | M1 (JUnit), M4 (Robot Framework) |

Every report format is different, but every parser makes the same promise: *give me a file, and I return a `TestRun`.* That promise is the abstract base class:

```python
class ResultParser(ABC):
    @abstractmethod
    def parse(self, content: str) -> TestRun: ...
```

Each format gets its own subclass. The rest of the code never needs to know which format came in. Adding a new format means adding one new class, and nothing else changes.

Robot Framework comparison: like a library interface. Different libraries implement keywords differently, but a test only cares about what a keyword does, not how.

### `services/`: the brains

| | |
|---|---|
| **Job** | Business logic, and coordinating the other folders to complete a task |
| **Contains** | `ingest.py` (parse a report and save it), `flakiness.py` (detect flaky tests) |
| **Depends on** | `domain/`, `parsers/`, `db/` |
| **Built in** | M2 (ingest), M3 (flakiness) |

When the API receives a report, it doesn't do the work itself. It asks a service: "ingest this". The service calls the parser, then the database layer, then (later) the notifier.

`flakiness.py` holds the actual intelligence of the product: given a list of results for one test, is it flaky?

Robot Framework comparison: like a high-level keyword that calls several lower-level keywords in the right order.

### `db/`: the memory

| | |
|---|---|
| **Job** | Save domain objects to PostgreSQL and load them back |
| **Contains** | SQLAlchemy table definitions, the database connection, "repository" functions such as `save_run()` and `get_results_for_test()` |
| **Depends on** | `domain/` |
| **Built in** | M2 |

The database has four tables (see `ROADMAP.md` for the data model): `project`, `run`, `test_case`, `result`.

The rest of the code never writes SQL. It calls functions like `save_run(run)`. If the database changed someday, only this folder would change.

### `api/`: the front door

| | |
|---|---|
| **Job** | Receive HTTP requests, call the right service, return JSON |
| **Contains** | FastAPI routes such as `POST /projects/{id}/runs` and `GET /projects/{id}/flaky-tests` |
| **Depends on** | `services/`, `domain/` |
| **Built in** | M2–M3 |

Routes are kept **thin**: check the input, call a service, return the result. There's no business logic here. That way the logic can be tested without starting a web server.

Comparison: you've tested many APIs from the outside. This is the inside of one.

### `notifiers/`: the messenger

| | |
|---|---|
| **Job** | Tell people when something important happens |
| **Contains** | `teams.py`, your existing CI notifier, refactored |
| **Depends on** | `domain/` |
| **Built in** | M4 |

---

## 4. The one rule: dependencies point inward

```
api/  →  services/  →  parsers/, db/, notifiers/  →  domain/
```

- `domain/` imports **nothing** from the project.
- `parsers/`, `db/` and `notifiers/` import only from `domain/`.
- `services/` uses all of the above.
- `api/` uses `services/` (and `domain/` for types).

**Why it matters:** the further inward, the more stable and easier to test the code is. If `domain/` imported FastAPI, you couldn't test a `TestRun` without a web framework installed.

**Quick check while coding:** if you're writing an `import` in `domain/` that points elsewhere in the project, stop. Something is in the wrong place.

---

## 5. Tests mirror the code

```
tests/
├── unit/           # test one piece alone: domain, parsers, services
│                   # fast, no database, runs on every save
└── integration/    # test pieces together: API + real database
                    # slower, needs Docker (from M2)
```

| Code | Tested in | Example test |
|---|---|---|
| `domain/models.py` | `tests/unit/test_models.py` | "a run with 2 passed and 1 failed reports `total == 3`" |
| `parsers/junit.py` | `tests/unit/test_junit_parser.py` | "a `<skipped>` element becomes `Status.SKIPPED`" |
| `services/flakiness.py` | `tests/unit/test_flakiness.py` | "PASS, FAIL, PASS is flagged as flaky" |
| `api/` routes | `tests/integration/test_api.py` | "uploading a report returns 201 and stores the run" |

---

## 6. Build order, and why

You build from the **inside out**, the same order as the dependency rule. Each step only needs things that already exist.

| Order | What | Why this order | Milestone |
|---|---|---|---|
| 1 | Project skeleton and CI | Every later step is checked automatically | M1 ✅ |
| 2 | **`domain/` models** | Everything else needs this vocabulary | **M1 ← you are here** |
| 3 | `parsers/` (JUnit) | Needs the models to produce; no DB or API needed yet | M1 |
| 4 | `db/` and the ingest service | Now there are runs worth storing | M2 |
| 5 | `api/` upload endpoint | Connects the outside world to steps 3–4 | M2 |
| 6 | Query endpoints and `flakiness.py` | Needs stored history to analyse | M3 |
| 7 | Auth, Robot parser, `notifiers/` | Extras on a working core | M4 |
| 8 | Deploy and documentation | Show it to the world | M5 |

At the end of M1 you'll have something that already works without a database or web server: give it a `report.xml` and get back a `TestRun` that reports how many tests passed, failed and were skipped.

---

## 7. Glossary

| Term | Meaning |
|---|---|
| **Run** | One execution of a test suite, for example one nightly pipeline run |
| **Test case** | One specific test, identified by suite and name. It exists across many runs. |
| **Result** | The outcome of one test case in one run |
| **Flaky test** | A test that switches between pass and fail without code changes |
| **JUnit XML** | The standard test-report format most tools can produce |
| **Domain** | The problem area the software is about; here, test results |
| **Parser** | Code that reads one format and converts it into another |
| **Service** | Code that performs one task by coordinating other parts |
| **Repository** | Code that saves and loads domain objects to and from a database |
| **Endpoint / route** | One URL plus HTTP method the API responds to, such as `POST /projects/1/runs` |