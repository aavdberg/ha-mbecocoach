# Mercedes Eco Coach integration

## Project and evidence

- Domain: `mbecocoach`; cloud polling, Config Flow and `DataUpdateCoordinator`.
- Target **Python 3.14 and Home Assistant 2026.9**. Keep the test HA dependency
  pinned to that target; do not claim target validation from another HA version.
- Never invent API endpoints or response fields. A redacted iOS 5.7.0 capture
  confirms `GET /api/v5/{VIN}/statistics/personal` returns nested cards (not flat
  numeric metrics), and also shows `/api/v5/{VIN}/report`,
  `/api/v5/{VIN}/statistics/all`, and `/api/v5/user/points`.
- Browser-assisted and optional direct Eco Coach login have passed a private
  real-account test. Automatic refresh-token rotation is implemented and covered
  by synthetic tests, but remains unverified at a live token expiry.
- Never commit or log actual credentials, tokens, callback URLs, VINs, captures,
  trip data or private personal information. Use synthetic fixtures in tests.
  Do not enable HTTP wire logging or include raw HA logs in issues/reviews.
- Keep persistent instructions accurate when architecture or evidence changes;
  see `.github/instructions/mbecocoach.instructions.md` for scoped code guidance.

## Development workflow

All changes, including docs and CI, go through a PR to `dev`. `main` is the
published production branch. Never push directly to `dev` or `main`, and never
promote to `main` without an **explicit user release request**.

1. Inspect the existing code, templates and evidence; plan the smallest complete
   change. Keep temporary plans outside the repository. Ask about material
   unresolved user decisions, not routine execution already authorized.
2. Add an English GitHub issue before each feature or bug fix. Use the repository
   issue template and link the issue from the PR.
3. Work on an isolated feature/fix/chore branch based on `dev`. Use the
   app-provided worktree and branch when present; do not switch or manipulate
   app-owned branches or the main checkout.
4. Implement with English code, comments, docstrings, issues, commit messages and
   PR descriptions. Use Conventional Commits (`feat:`, `fix:`, `docs:`, `ci:`,
   `chore:`, `refactor:`). Preserve typing and repository Ruff conventions.
5. Run `python -m ruff check custom_components tests .github/scripts`,
   `python -m ruff format --check custom_components tests .github/scripts`,
   `python -m pytest -q` and `node --test tests/*.mjs`.
   GitHub also runs hassfest, HACS and secret scanning. Inspect all required
   checks; do not substitute local synthetic tests for real-account testing.
6. Commit, push and open a PR **targeting `dev`** using
   `.github/pull_request_template.md`. Record exact validation commands/results.
7. Wait for CI and an **actually submitted** Copilot review. The review-request
   workflow only requests review asynchronously; a green request job is not a
   submitted review. Check `gh pr view <N> --json reviews`, read all comments,
   reply to each thread with the fix or reason for disagreement and resolve
   addressed threads. Re-run checks after fixes. Report unavailable review
   permissions or entitlement as blockers rather than bypassing the gate.
8. Merge only when authorized, checks pass and review threads are addressed.
   Ordinary PRs may use squash merge with a Conventional Commit title. If asked
   only to open a PR, leave it open. After an authorized merge to `dev`, verify
   the Pre-release workflow and the resulting beta (or its explicit skip reason).

## Releases (only on explicit user request)

- Development prereleases use `v<manifest-version>-beta.N`, not timestamps.
  The release scripts serialize publication, reuse a tag on retries and wait
  for CI, hassfest and secret scanning on the exact trusted branch commit.
- The manifest contains a plain semantic version (`X.Y.Z`), not a beta suffix.
  Before publishing betas for a new cycle, land a **separate normal PR to dev**
  setting the next development version. The current `0.7.5` is already stable:
  betas are deliberately skipped until that PR lands (e.g. `0.8.0`).
- Choose the stable target version with the user. Land any required manifest
  bump via a normal PR to `dev` before opening the release PR.
  Discuss breaking changes/major version bumps explicitly.
- Open the authorized release PR from **dev to main**; wait for CI and a
  submitted review, address/resolve review threads, then use a **merge commit,
  never squash or rebase**, to preserve development history.
- Verify Release published the non-prerelease `vX.Y.Z` at the intended commit.
  Existing tags are never moved; an unchanged stable version does not publish
  a new release. A retry can recover publication after tag creation succeeded.
- After the stable release, land the next development version through a
  **separate PR to dev**, so beta users get a version newer than stable.
- Refresh the bug-report version dropdown with
  `python .github/scripts/update_version_dropdown.py --repo aavdberg/ha-mbecocoach`
  and include the resulting change in a normal PR, never a direct bot push.
- Do not delete releases/tags, modify protections/settings/secrets or authorize
  production promotion merely to make an automation check green.

Strategy provenance and workflow prerequisites: [CONTRIBUTING.md](../CONTRIBUTING.md).
