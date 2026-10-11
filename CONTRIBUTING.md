# Contributing

Most useful contributions, in order:
1. **Export header aliases.** If ingest prints missing columns for a real export, add the header to `ALIASES` in `skills/ads/scripts/adslib/normalize.py`, and add a 3-row anonymised sample to `skills/ads/examples/exports/`. Never commit real client data.
2. **Platform registry updates.** Edit `skills/ads/references/platform-registry.json` with the new fact, an official source URL and today's `verified_at`.
3. **New deterministic checks.** Add the check to `adslib/checks.py`. It must declare the columns it needs (`c.needs(...)`), cite evidence, compute confidence with `score(...)`, and come with a test case.
4. **Evals.** Add a case under `evals/` for any behaviour you fix.

Rules:
- Stdlib-only Python 3.9+.
- No change may weaken the safety model (gate checks, guard, approval flow) without a security review in the PR description.
- Run `sh tests/run_tests.sh` and `claude plugin validate --strict .` before opening a PR.
