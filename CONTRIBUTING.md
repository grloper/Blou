# Contributing

Thanks for helping. Humans and AI agents follow the same rules.

1. Set up: `scripts/setup.sh` (Python 3.10+, network once).
2. Make changes on a branch; keep them small and focused.
3. Run `scripts/verify.sh` and read the output. It must exit 0 before you open a PR. It is the only gate.
4. Add or update tests for behaviour changes. Never delete tests, add skip/xfail markers, or loosen assertions to get green. `scripts/check-test-integrity.sh` guards the test count (`scripts/test-baseline.txt`).
5. Do not commit personal data: real IPs, hostnames, usernames, absolute home paths, credentials. Use placeholders (`100.64.0.10`, `<WORKSTATION_TAILSCALE_IP>`) and environment variables.
6. Update `CHANGELOG.md` for user-visible changes; docs must state only what was actually verified.

By contributing you agree your work is licensed under Apache-2.0 (see `LICENSE`).
Security issues: see [SECURITY.md](SECURITY.md), not public issues.
