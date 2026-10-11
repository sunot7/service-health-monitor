# Service Health Monitor

[![Developer tests ? Python 3.11 and 3.14](https://github.com/sunot7/service-health-monitor/actions/workflows/ci.yml/badge.svg?branch=pcc%2Fservice-health-monitor-dc8d8c21&event=workflow_dispatch)](https://github.com/sunot7/service-health-monitor/actions/workflows/ci.yml)

A small Python command-line application for checking configured HTTP services and
keeping a local SQLite history. It is for developers and IT support staff who want
to investigate service failures and review recent results without setting up a
hosted monitoring platform.

**Status:** the first offline milestone is accepted and uploaded to a **private**
repository. Developer tests passed on Python 3.11 and 3.14. Live HTTP/TLS/DNS
monitoring has not been verified. The badge may be unavailable without repository
access while the project is private.

## Features

- Named HTTP/HTTPS endpoints in JSON, with URL validation and configurable timeouts.
- HTTP status codes, response-header latency and error-class reporting.
- Timestamped SQLite observations, latest service status and recent success/failure summaries.
- `check`, `status` and `history` commands with text, JSON and CSV reports.
- Mocked HTTP tests, temporary databases and a demonstration that makes no HTTP requests.

## Engineering focus

This project demonstrates a small backend and IT automation workflow:

- **Input validation:** reject duplicate names, malformed URLs and invalid timeouts.
- **Persistence:** parameterized SQL, transactions and deterministic history ordering.
- **Failure handling:** distinguish unhealthy endpoints from input or storage errors.
- **Testable design:** inject HTTP transport and clocks instead of relying on live services.
- **Operational reporting:** expose status, history and machine-readable exports.
- **Reproducibility:** pin dependencies and run a two-version CI test matrix.

The stack is **Python, requests, SQLite, argparse and pytest**. There is no frontend,
background scheduler or hosted service.

## Setup

Clone using an account with repository access, then run commands from its root:

```sh
git clone https://github.com/sunot7/service-health-monitor.git
cd service-health-monitor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes --only-binary=:all: -r requirements-lock.txt
```

Python **3.11 and 3.14** are verified by the developer CI suite. On Windows, create
the environment with `py -3.11 -m venv .venv` (or your installed 3.14 interpreter)
and activate it with `.venv\Scripts\Activate.ps1`.

[requirements.txt](requirements.txt) lists the direct dependencies;
[requirements-lock.txt](requirements-lock.txt) pins all ten packages in the
dependency closure and their exact wheel hashes. Installation requires
package-source access or an approved local wheel cache. The application does not
install or download packages. No application packaging/install step is needed.

## Configuration

A configuration contains a list of uniquely named services:

```json
{
  "services": [
    {"name": "Example API", "url": "https://example.invalid/health", "timeout": 2}
  ]
}
```

See [sample-config.json](sample-config.json) for a two-service example. Names must
be nonempty and unique. URLs must use HTTP/HTTPS and cannot contain credentials,
fragments or whitespace. Timeouts must be positive and finite; the default is five
seconds. An empty services list is allowed.

Sample domains are illustrative. Run real checks only against endpoints you own
or have explicit permission to monitor.

## Try the offline demonstration

This calls the same CLI used by the application, through a thin verification
adapter, with an injected transport that returns HTTP 200. It makes no HTTP
requests and writes a local `demo.sqlite3` database:

```sh
python -c "from verification_adapter import main; main(['check', '--config', 'sample-config.json', '--database', 'demo.sqlite3'], transport=lambda url, timeout: 200)"
python -m service_monitor status --database demo.sqlite3
python -m service_monitor history --database demo.sqlite3 --format json
```

Illustrative output from the synthetic `check` command, assuming a new database:

```text
Example website: UP status=200 time=25.000ms error=- at=2026-01-01T00:00:00+00:00
Example API: UP status=200 time=25.000ms error=- at=2026-01-01T00:00:00+00:00
Summary: 2 checks, 2 successful, 0 failed
```

These are synthetic results, not live observations or performance benchmarks.
Actual timestamps and measured timings vary. Repeating the demo appends two more
observations. Generated databases and the `reports/` directory are excluded from Git.

## CLI commands

Only after authorizing real HTTP access for your configured endpoints:

```sh
python -m service_monitor check --config my-config.json --database health.sqlite3
```

Local reporting does not make HTTP requests:

```sh
python -m service_monitor status --database health.sqlite3
python -m service_monitor history --database health.sqlite3 --limit 20
mkdir reports
python -m service_monitor history --database health.sqlite3 --format json --output reports/history.json
python -m service_monitor history --database health.sqlite3 --format csv --output reports/history.csv
```

Create `reports/` once before exporting. Use `python -m service_monitor --help`
or add `--help` after a command for its options.

All commands accept `--format text|json|csv` and `--output FILE`. History defaults
to the newest 100 observations. Status shows the latest result per service and,
in text mode, a recent summary; `--limit` controls the summary sample. Missing
databases initialize empty history.

Output files are overwritten, except that the current database/configuration and
their filesystem aliases are protected. Parent directories must exist. Text
reports escape control characters; JSON and CSV preserve original values.

| Exit code | Meaning |
| --- | --- |
| 0 | Command completed successfully |
| 1 | At least one endpoint was unhealthy during `check` |
| 2 | Invalid arguments/configuration or a local storage/report failure |

HTTP 2xx is healthy; redirects and other statuses are unhealthy. Errors record
their class without exposing potentially sensitive exception text.

## Tests and CI

Run the developer suite without contacting live endpoints:

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

In PowerShell:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest -q
```

Tests use mocked HTTP responses, injected clocks and temporary databases.
`python -m unittest -v test_app` is also supported, but does not replace the
separate independent verification.

| Evidence | Environment | Established result |
| --- | --- | --- |
| Developer suite | GitHub Actions, Python 3.11 and 3.14 | 42 tests plus 5 subtests passed per version |
| Independent contract scenarios | Approved isolated local Linux environment, Python 3.14 | All 7 passed |
| Additional reviewer checks | Approved isolated local Linux environment, Python 3.14 | All 9 passed |

[GitHub Actions run 38112504132](https://github.com/sunot7/service-health-monitor/actions/runs/38112504132)
completed successfully on 2026-10-11 for commit
`170c46a71ee97e9a2674e8c42ec3c17cb558f040`. The
[workflow](.github/workflows/ci.yml) runs the **developer suite**, not the
independent checks. It is manually dispatched and has no scheduled trigger.

The independent checks cover configuration, mocked HTTP behavior, SQLite,
JSON export, CSV export, CLI arguments and CLI check/status/history integration.
Supplementary review covered real requests options with mocked responses,
failure reporting, rollback and corrupt databases, terminal safety and report
destination protection. Those external review suites and historical acceptance
records remain local; they are not included in this repository.

These are bounded test results, not a claim of exhaustive coverage, production
uptime or verified live monitoring.

## Architecture and design decisions

| Module | Responsibility |
| --- | --- |
| [config.py](service_monitor/config.py) | Load and validate all services before requesting any endpoint |
| [checks.py](service_monitor/checks.py) | Perform one GET using injectable transport and monotonic timing |
| [storage.py](service_monitor/storage.py) | Persist observations and query history/latest results |
| [reports.py](service_monitor/reports.py) | Render text and serialize JSON/CSV |
| [cli.py](service_monitor/cli.py) | Coordinate commands and map expected errors to exit codes |
| [test_app.py](test_app.py) | Exercise behavior using mocks and temporary storage |

SQLite avoids a separate database service. Parameterized statements protect SQL
values, and transactions preserve committed observations when later writes fail.
UTC timestamps and insertion IDs define history ordering.

HTTP responses and sessions are closed with context managers. TLS certificate
validation stays enabled; environment proxies and netrc are disabled; redirects
are not followed. Streaming avoids downloading response bodies. A failed endpoint
does not prevent checks of later services, while persistence failure stops the run
rather than silently discarding observations.

See [architecture.md](architecture.md) for the module-level data flow.

## Limitations and future improvements

- Checks are sequential. Retries, alerts, scheduling and retention are not implemented.
- Requests timeouts bound connect/read inactivity, not total execution time.
  Latency measures response headers rather than the body.
- Live HTTP/TLS/DNS behavior, sustained load and disk-full/crash recovery have not
  been verified. Mocked tests cannot establish real service availability.
- URL query strings may be persisted. Use secret-free health URLs and protect
  local database/report access.
- Treat CSV fields as data rather than executable spreadsheet formulas.
- Report collision checks prevent accidental overwrites, but do not protect
  against a hostile concurrent filesystem writer.
- History ordering assumes application-generated normalized UTC timestamps.

Possible next steps include configuration-size limits, field-indexed validation
messages and explicitly approved live-network integration tests. These are future
work, not implemented features.

The repository is currently **private**. Public visibility requires a separate
decision. No deployment, user adoption or security certification is claimed.
