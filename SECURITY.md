# Security policy

Blou is pre-alpha research code. It is **not** audited and must not be used to protect real remote-access sessions.

## Reporting a vulnerability

Please report privately through GitHub: **Security tab -> "Report a vulnerability"** on https://github.com/grloper/Blou (private vulnerability reporting). Do not open a public issue for security problems. Expect an initial response within about 7 days; this is a single-maintainer project and no SLA is offered.

## Scope

In scope: the Python code in `src/blou` and `scripts/` (for example certificate pinning logic, the loopback workbench's Host/bearer checks, input validation in the DVC encoder).
Out of scope: upstream FreeRDP (report to that project), and the design documents' threat model, which is aspirational.

## Supported versions

Only the latest release and `main`.
