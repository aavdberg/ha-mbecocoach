# Development and releases

All changes, including repository tooling and documentation, go through a PR
to `dev`. `main` contains published production code. Use Conventional Commits,
English issues/code/docs, the issue and PR templates, and synthetic fixtures.
Never publish credentials, tokens, callbacks, VINs, captures or real trip data.
An explicit user release request is required before promoting `dev` to `main`.

## Validation and review

Use Python 3.14 with Home Assistant 2026.9. Install `requirements_test.txt`, then:

```text
python -m ruff check custom_components tests .github/scripts
python -m ruff format --check custom_components tests .github/scripts
python -m pytest -q
node --test tests/*.mjs
```

Node 24 runs the card and release-gate tests. CI also validates the workflow
structure, synthetic release/dropdown behavior, hassfest, HACS and secret
scanning. Do not infer live token-expiry verification from synthetic tests.

The Copilot Review workflow requests review of non-draft, same-repository PRs
to `dev`/`main`, without checking out or executing PR code. Fork review requests
need a maintainer to request review manually. Review submission is asynchronous:
check `gh pr view <N> --json reviews`, read and reply to comments, and resolve
addressed threads before an authorized merge. A successful request job alone
does not satisfy this gate. Leave PRs open unless merging is authorized.

## Beta and stable releases

After trusted branch pushes pass CI (including HACS), hassfest and secret
scanning, Pre-release publishes `v<manifest-version>-beta.N` from `dev`, and
Release publishes stable `v<manifest-version>` from `main`. Runs are serialized,
check the exact SHA and current branch head, never run fork/PR code with a
publication token, never move tags and recover missing releases on retries.
Failed or pending validation blocks publication; completion of the last passing
workflow retries the gate. A manual dispatch on the matching branch can retry
publication, but fails unless all three push workflows passed that exact SHA.
Unchanged stable versions do not generate new tags/releases.

**Bootstrap:** the current manifest `0.7.5` already has stable tag `v0.7.5`.
Publishing `v0.7.5-beta.1` would rank below stable in HACS. Pre-release therefore
warns and skips until a **separate PR to dev** sets the next development version
(for example `0.8.0`). This adoption does not change the manifest, publish a
release or promote to `main`.

For an explicitly requested stable release, agree the semantic version and land
any manifest bump via a normal PR to `dev` first. Open the release PR **dev to
main**, pass checks and submitted review, address threads, then merge with a
**merge commit**, not squash/rebase. Verify the stable release at the intended
commit. Immediately follow it with a **separate PR to dev** for the next
development version; do not directly push a version bump or delete old tags.
Major/breaking changes require a user decision.

After publication, run the read-only release-list helper and submit any changed
issue form through a normal PR to `dev`:

```text
python .github/scripts/update_version_dropdown.py --repo aavdberg/ha-mbecocoach
```

It preserves manual/unreleased choices, excludes draft and legacy timestamp
releases, caps published options at 15, and fails visibly on malformed markers
or GitHub errors. No bot token or direct protected-branch write is required.

## Automation prerequisites

The built-in `GITHUB_TOKEN` is sufficient for publication (`contents: write`,
`actions: read`) and review requests (`pull-requests: write`) when repository/
organization policy allows those job-scoped permissions. No additional secret
is used. Copilot review additionally requires repository/account entitlement;
API rejection is a failed check, not a silently successful review.
The setting allowing Actions to *approve* PRs is not needed: this only requests
a reviewer. Do not change settings, secrets or protection rules to bypass gates.

`workflow_run` definitions must exist on the default branch before GitHub can
trigger them. This repository's default branch is `main`; adding the workflows
only to `dev` does **not** activate automatic publication yet. They become
available after a separately authorized production promotion includes them.
Likewise an Actions dispatch must be available on the default branch before it
can be used as a retry. No workflow activation or main promotion is authorized
by this adoption PR. Actions-created releases do not trigger other token-based
workflows, so the dropdown is intentionally refreshed via a separate PR.

## Source and adaptations

Adapted from [aavdberg/ha-petkit at
a55e1622aa84d13335305ac0ec04cb4eef4919bd](https://github.com/aavdberg/ha-petkit/tree/a55e1622aa84d13335305ac0ec04cb4eef4919bd).
Source `dev` was `cb0c869214635e22278bafaf7fa64384a1888985` with no content
differences from `main` at inspection.

| Source | Eco Coach adaptation |
| --- | --- |
| `copilot-instructions.md` | PR-to-dev, Conventional Commits, submitted reviews and explicit-release rules; no direct-to-main chore exception, app branch commands or mandatory repository plans |
| `instructions/petkit-ble.instructions.md` | `instructions/mbecocoach.instructions.md` with verified cloud/OAuth/history/card architecture and privacy evidence, not BLE |
| `workflows/lint.yml` | Retain `ci.yml`, Ruff/pytest/HACS; Python 3.14, HA 2026.9, script/workflow and Node tests |
| `workflows/gitleaks.yml`, `hassfest.yml` | Retain existing checks; adopt hassfest's daily schedule, no duplicate jobs or HACS brands bypass |
| `workflows/copilot-review.yml` | Least-privilege no-checkout review requests; ready-for-review event and fork/draft guards |
| `workflows/pre-release.yml`, `release.yml` | CI-gated trusted SHA publication, numeric beta tags, retries, stable-version guard and immutable tags |
| `scripts/update_version_dropdown.py` | Marked Eco Coach issue dropdown; explicit repo, synthetic tests and normal-PR update guidance |
