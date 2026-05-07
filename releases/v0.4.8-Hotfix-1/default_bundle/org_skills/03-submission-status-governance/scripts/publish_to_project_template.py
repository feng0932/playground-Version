#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path


MANAGED_SOURCE_PREFIX = "# AI_TEAM_MANAGED_SOURCE: "
MANAGED_SHA256_PREFIX = "# AI_TEAM_MANAGED_SHA256: "
SOURCE_ROOT = Path("install/default_bundle/org_skills/03-submission-status-governance")
DESTINATION_ROOT = Path("install/default_bundle/assets/project_skeleton/00-项目包模板")
PUBLISH_CONTRACT = {
    "source_root": SOURCE_ROOT.as_posix(),
    "destination_root": DESTINATION_ROOT.as_posix(),
    "managed_entries": (
        {
            "kind": "script",
            "source": "scripts/sync_submission_status.py",
            "destination": "scripts/sync_submission_status.py",
        },
        {
            "kind": "script",
            "source": "scripts/check_submission_consistency.py",
            "destination": "scripts/check_submission_consistency.py",
        },
        {
            "kind": "script",
            "source": "scripts/check_publish_boundary.py",
            "destination": "scripts/check_publish_boundary.py",
        },
        {
            "kind": "script",
            "source": "scripts/check_engineering_handoff_readiness.py",
            "destination": "scripts/check_engineering_handoff_readiness.py",
        },
        {
            "kind": "script",
            "source": "scripts/check_final_delivery_gate.py",
            "destination": "scripts/check_final_delivery_gate.py",
        },
        {
            "kind": "reference",
            "source": "references/00-提交状态.example.json",
            "destination": "80-完整提交包/00-提交状态.json",
        },
    ),
}


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def publish_contract() -> dict[str, object]:
    return {
        "source_root": PUBLISH_CONTRACT["source_root"],
        "destination_root": PUBLISH_CONTRACT["destination_root"],
        "managed_entries": [dict(entry) for entry in PUBLISH_CONTRACT["managed_entries"]],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish submission-status governance assets into the project template.")
    parser.add_argument(
        "--repo-root",
        default=str(default_repo_root()),
        help="Methods repository root. Defaults to current repository layout.",
    )
    return parser.parse_args(argv)


def publish(repo_root: Path) -> list[tuple[Path, Path]]:
    contract = publish_contract()
    skill_root = repo_root / contract["source_root"]
    template_root = repo_root / contract["destination_root"]
    mappings = [
        (skill_root / entry["source"], template_root / entry["destination"])
        for entry in contract["managed_entries"]
    ]

    published: list[tuple[Path, Path]] = []
    for source, destination in mappings:
        if not source.exists():
            raise FileNotFoundError(f"missing source file: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix == ".py":
            relative_source = source.relative_to(skill_root).as_posix()
            destination.write_text(_stamp_managed_script(relative_source, source.read_text(encoding="utf-8")), encoding="utf-8")
        else:
            shutil.copy2(source, destination)
        published.append((source, destination))
    return published


def _stamp_managed_script(relative_source: str, text: str) -> str:
    shebang, body = _split_shebang_and_body(text)
    payload = f"{shebang}{body}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    header = (
        f"{MANAGED_SOURCE_PREFIX}{relative_source}\n"
        f"{MANAGED_SHA256_PREFIX}{digest}\n"
    )
    return f"{shebang}{header}{body}"


def _split_shebang_and_body(text: str) -> tuple[str, str]:
    if text.startswith("#!"):
        first_line, remainder = text.split("\n", 1)
        return f"{first_line}\n", remainder
    return "", text


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).expanduser().resolve()
    published = publish(repo_root)
    print("published submission-status governance assets:")
    for source, destination in published:
        print(f"- {source} -> {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
