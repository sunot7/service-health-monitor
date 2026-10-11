# Service Health Monitor

A small Python command-line application for checking explicitly configured HTTP
services and keeping a local SQLite history. Built for developers and IT support
staff who need an understandable health report without a hosted monitoring platform.

## Features

- Named HTTP/HTTPS endpoints in JSON, with validated URLs and configurable timeouts.
- HTTP status, response-header latency and safe error-class reporting.
- Timestamped SQLite observations, latest service status and recent success/failure summaries.
- `check`, `status` and `history` commands with text, JSON and CSV reports.
- Mocked HTTP tests, temporary databases and an offline demonstration.

## Technologies and architecture

Python, requests, SQLite, argparse and pytest. Configuration, HTTP transport,
storage, reports and CLI orchestration are separate small modules. SQL writes use
bound parameters and transactions. The transport disables environment proxies and
netrc, keeps TLS certificate validation enabled and does not follow redirects.
See [architecture.md](architecture.md) for the module responsibilities and data flow.

## Local setup

Python 3.14 has been tested in the isolated verification environment. Python 3.11
is a target in the proposed CI matrix, but has not yet been locally verified.
Use a separately authorized machine/environment for dependency installation:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes --only-binary=:all: -r requirements-lock.txt
```

On Windows, activate with `.venv\Scripts\Activate.ps1`. Run commands from this
directory; installing the application itself is unnecessary. The lock contains the
reviewed pure-Python dependency closure and exact wheel hashes; installation needs
an approved wheel cache or separately authorized package-source access. No packages
are downloaded by the application. `requirements.txt` lists the two direct dependencies.

## Configuration

```json
{"services": [{"name": "Example API", "url": "https://example.invalid/health", "timeout": 2}]}
```

Names must be unique and nonempty; HTTP/HTTPS URLs cannot contain credentials,
fragments or whitespace. Timeouts must be positive and finite (default: 5 seconds).
An empty service list is valid. Sample domains are illustrative and authorize no
networking. Use only endpoints you own or are explicitly authorized to monitor.

## Offline demo and tests

The demonstration injects a synthetic transport into the actual CLI. It makes no
HTTP requests; `demo.sqlite3` is generated locally and excluded from Git:

```sh
python -c "from verification_adapter import main; main(['check', '--config', 'sample-config.json', '--database', 'demo.sqlite3'], transport=lambda url, timeout: 200)"
python -m service_monitor status --database demo.sqlite3
python -m service_monitor history --database demo.sqlite3 --format json
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

In PowerShell, set `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'` before running pytest.
`python -m unittest -v test_app` also works but does not replace independent
contract verification. Tests use mocked HTTP and temporary databases.

Illustrative output (not real observations; timestamps and latency will vary):

```text
Example API: UP status=200 time=25.000ms error=- at=2026-01-01T00:00:00+00:00
Summary: 1 checks, 1 successful, 0 failed
Recent 1 checks: 1 successful, 0 failed
```

## Commands

Only after separately authorizing real HTTP access for your configured endpoints:

```sh
python -m service_monitor check --config my-config.json --database health.sqlite3
```

Local reports make no HTTP requests:

```sh
python -m service_monitor status --database health.sqlite3
python -m service_monitor history --database health.sqlite3 --limit 20
python -m service_monitor history --database health.sqlite3 --format json --output reports.json
python -m service_monitor history --database health.sqlite3 --format csv --output reports.csv
```

`--help` describes each command. All commands accept `--format text|json|csv` and
`--output FILE`. History defaults to 100 newest observations. Status displays the
latest result per service and a recent summary in text mode (`--limit` controls
the summary sample). Missing databases initialize empty history. Output files are
overwritten, except the database/current configuration and their filesystem aliases
are protected. Parent directories must exist. Text escapes control characters;
machine-readable reports preserve exact original values.

Exit codes: **0** success, **1** at least one unhealthy endpoint during `check`,
**2** invalid arguments/configuration or local storage/report failure. HTTP 2xx
is healthy; redirects and other statuses are unhealthy. Errors record their class
without exposing potentially sensitive exception text.

## Verification and CI

The accepted offline milestone passed 42 pytest tests plus 5 subtests, seven
separate contract-bound behavioral scenarios and nine supplementary reviewer checks
on Python 3.14. Project release preparation repeats the approved offline checks
against the release file hashes. These results do not prove live HTTP reliability.

The manual-only GitHub Actions workflow proposes Python 3.11 and 3.14 test jobs
using hash-checked dependencies. **GitHub Actions has not run.** It requires a
separate user action after the private repository upload. No scheduled trigger or
live monitoring is configured. Internal acceptance/audit notes remain local and
are excluded from the release file list.

## Limitations and security

- Sequential checks; no retries, alerts, scheduler, retention policy or hosted service.
- Requests timeouts bound connect/read inactivity, not total execution time.
  Latency measures response headers, not the response body.
- No live HTTP/TLS/DNS behavior, Python 3.11 runtime, sustained load or disk-full
  recovery has been verified. CI is not evidence until an actual run completes.
- Avoid secret-bearing URL queries; URLs are persisted in local reports/databases.
  Protect local file access and treat CSV fields as data, not spreadsheet formulas.
- Report collision checks prevent accidental overwrites, but do not protect
  against a hostile concurrent filesystem writer. Configuration size limits and
  field-indexed validation messages are future hardening opportunities.
- History ordering assumes application-generated normalized UTC timestamps.

The initial repository is intended to be **private**. Upload and any later public
visibility change require separate explicit decisions. No deployment, uptime,
adoption or security certification is claimed.
