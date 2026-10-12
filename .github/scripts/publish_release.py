"""Publish semantic releases from a validated, trusted branch checkout."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

VERSION = r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
STABLE = re.compile(rf"v{VERSION}")
BETA = re.compile(rf"v{VERSION}-beta\.([1-9]\d*)")
MANIFEST = Path("custom_components/mbecocoach/manifest.json")


@dataclass(frozen=True)
class ReleasePlan:
    """A tag and its immutable target."""

    tag: str
    sha: str
    prerelease: bool
    create_tag: bool


def plan_release(version: str, tags: dict[str, str], sha: str, *, beta: bool) -> ReleasePlan | None:
    """Reuse same-commit betas, reject downgrades and never move stable tags."""
    if not re.fullmatch(VERSION, version):
        raise ValueError("Manifest version must be plain X.Y.Z without leading zeros")
    current = tuple(map(int, version.split(".")))
    stable_versions = [tuple(map(int, match.groups())) for tag in tags if (match := STABLE.fullmatch(tag))]
    if stable_versions and current < max(stable_versions):
        raise ValueError("Manifest version is older than an existing stable release")
    stable_tag = f"v{version}"
    if not beta:
        return ReleasePlan(stable_tag, tags.get(stable_tag, sha), False, stable_tag not in tags)
    if stable_tag in tags:
        return None
    numbers: list[int] = []
    for tag, target in tags.items():
        match = BETA.fullmatch(tag)
        if match and tag.startswith(f"{stable_tag}-beta."):
            numbers.append(int(match.group(4)))
            if target == sha:
                return ReleasePlan(tag, sha, True, False)
    return ReleasePlan(f"{stable_tag}-beta.{max(numbers, default=0) + 1}", sha, True, True)


def command(*args: str) -> str:
    """Run a command, propagating failed operations explicitly."""
    return subprocess.run(args, check=True, stdout=subprocess.PIPE, text=True).stdout


def publish(plan: ReleasePlan, repo: str) -> None:
    """Recover a missing release on retry without replacing an existing tag."""
    releases = json.loads(command("gh", "api", "--paginate", "--slurp", f"repos/{repo}/releases"))
    existing = next((release for page in releases for release in page if release["tag_name"] == plan.tag), None)
    if existing is not None:
        if existing["draft"] or existing["prerelease"] != plan.prerelease:
            raise ValueError(f"Existing release {plan.tag} has unexpected draft/prerelease state")
        print(f"Release {plan.tag} already published; nothing to change.")
        return
    if plan.create_tag:
        command("gh", "api", f"repos/{repo}/git/refs", "-f", f"ref=refs/tags/{plan.tag}", "-f", f"sha={plan.sha}")
    args = [
        "gh",
        "release",
        "create",
        plan.tag,
        "--repo",
        repo,
        "--verify-tag",
        "--generate-notes",
        "--title",
        plan.tag,
    ]
    if plan.prerelease:
        args += [
            "--prerelease",
            "--latest=false",
            "--notes",
            "Development pre-release, not for production. Enable beta releases in HACS or copy "
            "custom_components/mbecocoach manually. See CONTRIBUTING.md for the testing strategy.",
        ]
    else:
        args += ["--latest"]
    command(*args)
    print(f"Published {plan.tag}.")


def main() -> None:
    """Read the checked-out manifest/tags; workflows enforce branch/CI gates."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("channel", choices=["beta", "stable"])
    parser.add_argument("--sha", required=True)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()
    if command("git", "rev-parse", "HEAD").strip() != args.sha:
        raise ValueError("Release SHA must match the checked-out commit")
    tags = {
        tag: command("git", "rev-list", "-n", "1", tag).strip()
        for tag in command("git", "tag", "--list", "v*").splitlines()
    }
    version = json.loads(MANIFEST.read_text(encoding="utf-8"))["version"]
    plan = plan_release(version, tags, args.sha, beta=args.channel == "beta")
    if plan is None:
        print(f"::warning::v{version} is already stable; land a separate next-development-version PR to dev first.")
        return
    publish(plan, args.repo)


if __name__ == "__main__":
    main()
