# Architecture

`config.py` reads JSON and validates every service before any request starts.
`checks.py` performs one synchronous GET per service using an injectable transport
and monotonic clock; UTC timestamps identify stored observations. Success means
HTTP 200–299. Redirects count as failures and are not followed. Requests reads
headers only and closes the response, avoiding unbounded response bodies.

`storage.py` uses SQLite transactions and bound parameters. History orders by UTC
timestamp then insertion ID; latest partitions by exact, case-sensitive service
name. Connections close after each operation. `reports.py` serializes rows or
renders text summaries. `cli.py` coordinates these modules and converts expected
input, filesystem and database failures to exit code 2. A failed endpoint does
not prevent subsequent checks. Persistence failures stop the run to avoid
silently losing observations. Earlier committed observations remain available.

`verification_adapter.py` directly re-exports production functions. Tests use
temporary databases, deterministic clocks, injected transports and a mocked
requests Session. There is no background process, scheduler or network discovery.

Stages: requirements/design captured in README; implementation and developer
tests in source; independent verification and human review tracked in REVIEW.md.
