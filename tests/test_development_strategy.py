"""Synthetic regression tests for development automation, never real account data."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> ModuleType:
    """Load repository scripts without turning .github into a Python package."""
    spec = importlib.util.spec_from_file_location(name, ROOT / ".github" / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


release = load_script("publish_release")
dropdown = load_script("update_version_dropdown")
SHA = "a" * 40
OLD_SHA = "b" * 40


@pytest.mark.parametrize("version", ["1.2", "1.2.3-beta.1", "01.2.3", "1.02.3", "1.2.3\n", "not-a-version"])
def test_invalid_manifest_version(version: str) -> None:
    with pytest.raises(ValueError, match=r"plain X\.Y\.Z"):
        release.plan_release(version, {}, SHA, beta=True)


def test_first_beta_and_numeric_increment() -> None:
    assert release.plan_release("0.8.0", {"v0.7.5": OLD_SHA}, SHA, beta=True) == release.ReleasePlan(
        "v0.8.0-beta.1", SHA, True, True
    )
    tags = {
        "v0.8.0-beta.9": OLD_SHA,
        "v0.8.0-beta.10": OLD_SHA,
        "v0.7.0-beta.99": OLD_SHA,
        "v0.8.0-beta.bad": OLD_SHA,
        "v0.8.0-dev.20261012": OLD_SHA,
    }
    assert release.plan_release("0.8.0", tags, SHA, beta=True).tag == "v0.8.0-beta.11"


def test_beta_retry_reuses_same_commit_tag() -> None:
    tags = {"v0.8.0-beta.2": SHA, "v0.8.0-beta.3": OLD_SHA}
    assert release.plan_release("0.8.0", tags, SHA, beta=True) == release.ReleasePlan("v0.8.0-beta.2", SHA, True, False)


def test_already_stable_beta_is_skipped() -> None:
    assert release.plan_release("0.7.5", {"v0.7.5": OLD_SHA}, SHA, beta=True) is None


@pytest.mark.parametrize("beta", [False, True])
def test_stable_downgrade_is_rejected(beta: bool) -> None:
    with pytest.raises(ValueError, match="older"):
        release.plan_release("0.7.4", {"v0.7.5": OLD_SHA}, SHA, beta=beta)


@pytest.mark.parametrize("beta", [False, True])
def test_beta_base_version_downgrade_is_rejected(beta: bool) -> None:
    with pytest.raises(ValueError, match="older"):
        release.plan_release("0.8.0", {"v0.9.0-beta.1": OLD_SHA}, SHA, beta=beta)


def test_existing_stable_remains_idempotent_after_new_development_betas() -> None:
    assert release.plan_release(
        "0.7.5", {"v0.7.5": OLD_SHA, "v0.8.0-beta.1": SHA}, SHA, beta=False
    ) == release.ReleasePlan("v0.7.5", OLD_SHA, False, False)


def test_new_stable_tag_and_existing_immutable_tag() -> None:
    assert release.plan_release("0.8.0", {"v0.8.0-beta.1": OLD_SHA}, SHA, beta=False) == release.ReleasePlan(
        "v0.8.0", SHA, False, True
    )
    assert release.plan_release("0.8.0", {"v0.8.0": OLD_SHA}, SHA, beta=False) == release.ReleasePlan(
        "v0.8.0", OLD_SHA, False, False
    )


@pytest.mark.parametrize("beta", [False, True])
def test_publish_creates_tag_before_release(monkeypatch: pytest.MonkeyPatch, beta: bool) -> None:
    execute = Mock(side_effect=["[[]]", "", ""])
    monkeypatch.setattr(release, "command", execute)
    tag = "v0.8.0-beta.1" if beta else "v0.8.0"
    release.publish(release.ReleasePlan(tag, SHA, beta, True), "example/integration")
    calls = [call.args for call in execute.call_args_list]
    assert calls[1] == (
        "gh",
        "api",
        "repos/example/integration/git/refs",
        "-f",
        f"ref=refs/tags/{tag}",
        "-f",
        f"sha={SHA}",
    )
    assert calls[2][:4] == ("gh", "release", "create", tag)
    assert "--verify-tag" in calls[2]
    assert ("--prerelease" in calls[2]) == beta
    assert ("--latest=false" in calls[2]) == beta
    assert ("--latest" in calls[2]) != beta


def test_missing_release_recovers_existing_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    execute = Mock(side_effect=["[[]]", ""])
    monkeypatch.setattr(release, "command", execute)
    release.publish(release.ReleasePlan("v0.8.0-beta.1", SHA, True, False), "example/integration")
    assert execute.call_count == 2
    assert execute.call_args.args[:3] == ("gh", "release", "create")


def test_existing_release_is_idempotent_across_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    existing = {"tag_name": "v0.8.0", "draft": False, "prerelease": False}
    execute = Mock(return_value=json.dumps([[], [existing]]))
    monkeypatch.setattr(release, "command", execute)
    release.publish(release.ReleasePlan("v0.8.0", OLD_SHA, False, False), "example/integration")
    execute.assert_called_once()


@pytest.mark.parametrize(
    ("draft", "prerelease"),
    [(True, False), (False, True)],
)
def test_unexpected_existing_release_fails(monkeypatch: pytest.MonkeyPatch, draft: bool, prerelease: bool) -> None:
    execute = Mock(return_value=json.dumps([[{"tag_name": "v0.8.0", "draft": draft, "prerelease": prerelease}]]))
    monkeypatch.setattr(release, "command", execute)
    with pytest.raises(ValueError, match="unexpected"):
        release.publish(release.ReleasePlan("v0.8.0", SHA, False, False), "example/integration")
    execute.assert_called_once()


def test_publication_error_is_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    execute = Mock(side_effect=["[[]]", subprocess.CalledProcessError(1, "gh")])
    monkeypatch.setattr(release, "command", execute)
    with pytest.raises(subprocess.CalledProcessError):
        release.publish(release.ReleasePlan("v0.8.0", SHA, False, True), "example/integration")


def test_release_main_rejects_wrong_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["publish_release.py", "beta", "--sha", SHA, "--repo", "example/integration"])
    monkeypatch.setattr(release, "command", Mock(return_value=OLD_SHA))
    with pytest.raises(ValueError, match="checked-out"):
        release.main()


def test_version_dropdown_filters_legacy_duplicates_and_invalid_tags() -> None:
    tags = ["v0.8.0-beta.10", "v0.7.5", "v0.7.5", "v0.8.0-dev.123", "v01.2.3", "junk", None]
    assert dropdown.release_tags([{"tagName": tag} for tag in tags]) == ["v0.8.0-beta.10", "v0.7.5"]
    assert len(dropdown.release_tags([{"tagName": f"v1.0.{number}"} for number in range(20)])) == 15


def test_dropdown_render_preserves_form_and_is_idempotent() -> None:
    form = (ROOT / dropdown.BUG_REPORT_PATH).read_text(encoding="utf-8")
    updated = dropdown.render_options(form, ["v0.8.0-beta.1", "v0.7.5"])
    assert dropdown.render_options(updated, ["v0.8.0-beta.1", "v0.7.5"]) == updated
    data = yaml.safe_load(updated)
    field = next(item for item in data["body"] if item["id"] == "version")
    assert field["type"] == "dropdown"
    assert field["attributes"]["options"] == [
        "v0.8.0-beta.1",
        "v0.7.5",
        "Development branch (unreleased)",
        "Other / Older",
    ]
    original = yaml.safe_load(form)
    assert [item for item in data["body"] if item["id"] != "version"] == [
        item for item in original["body"] if item["id"] != "version"
    ]
    assert dropdown.render_options(updated, []).count("        - ") == 2


@pytest.mark.parametrize(
    "content",
    [
        "missing",
        dropdown.START_SENTINEL,
        dropdown.END_SENTINEL + dropdown.START_SENTINEL,
        dropdown.START_SENTINEL * 2 + dropdown.END_SENTINEL,
    ],
)
def test_dropdown_rejects_invalid_markers(content: str) -> None:
    with pytest.raises(ValueError):
        dropdown.render_options(content, [])


def test_dropdown_github_error_leaves_form_unchanged(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "form.yml"
    path.write_text("unchanged", encoding="utf-8")
    monkeypatch.setattr(dropdown, "BUG_REPORT_PATH", path)
    monkeypatch.setattr(sys, "argv", ["update_version_dropdown.py", "--repo", "example/integration"])
    monkeypatch.setattr(dropdown.subprocess, "run", Mock(side_effect=subprocess.CalledProcessError(1, "gh")))
    with pytest.raises(subprocess.CalledProcessError):
        dropdown.main()
    assert path.read_text(encoding="utf-8") == "unchanged"


def workflow(name: str) -> dict:
    """BaseLoader keeps YAML's 'on' key rather than treating it as boolean."""
    return yaml.load((ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_required_workflow_coverage_and_target_versions() -> None:
    ci = workflow("ci.yml")
    assert ci["jobs"]["ruff"]["name"] == "Ruff (lint + format check)"
    assert ci["permissions"] == {"contents": "read"}
    for job in ("ruff", "pytest"):
        python = next(
            step for step in ci["jobs"][job]["steps"] if step.get("uses", "").startswith("actions/setup-python")
        )
        assert python["with"]["python-version"] == "3.14"
    assert any(step.get("uses") == "hacs/action@main" for step in ci["jobs"]["validate-hacs"]["steps"])
    assert "homeassistant==2026.9.0" in (ROOT / "requirements_test.txt").read_text(encoding="utf-8")
    for name in ("ci.yml", "hassfest.yml", "gitleaks.yml"):
        assert workflow(name)["on"]["pull_request"]["branches"] == ["main", "dev"]


@pytest.mark.parametrize(("name", "branch"), [("pre-release.yml", "dev"), ("release.yml", "main")])
def test_release_workflows_are_trusted_and_serialized(name: str, branch: str) -> None:
    data = workflow(name)
    assert data["permissions"] == {}
    assert data["concurrency"] == {"group": "publish-release", "cancel-in-progress": "false"}
    assert set(data["on"]) == {"workflow_run", "workflow_dispatch"}
    assert data["on"]["workflow_run"]["branches"] == [branch]
    assert set(data["on"]["workflow_run"]["workflows"]) == {"CI", "Validate with hassfest", "Secret scan"}
    job = next(iter(data["jobs"].values()))
    assert "head_repository.full_name == github.repository" in job["if"]
    assert "workflow_run.event == 'push'" in job["if"]
    assert f"github.ref == 'refs/heads/{branch}'" in job["if"]
    assert job["permissions"] == {"actions": "read", "contents": "write"}
    checkout = job["steps"][0]
    assert checkout["with"]["persist-credentials"] == "false"
    assert checkout["with"]["ref"] == "${{ github.event.workflow_run.head_sha || github.sha }}"
    assert job["steps"][-1]["if"] == "steps.gate.outputs.ready == 'true'"


def test_review_request_never_executes_pr_code() -> None:
    data = workflow("copilot-review.yml")
    assert data["permissions"] == {}
    assert set(data["on"]) == {"pull_request"}
    assert "ready_for_review" in data["on"]["pull_request"]["types"]
    job = data["jobs"]["copilot-review"]
    assert job["permissions"] == {"pull-requests": "write"}
    assert "head.repo.full_name == github.repository" in job["if"]
    assert all(step.get("uses") == "actions/github-script@v7" for step in job["steps"])
    assert "reviewers: ['copilot-pull-request-reviewer[bot]']" in job["steps"][0]["with"]["script"]
