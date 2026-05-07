#!/usr/bin/env python3
# AI_TEAM_MANAGED_SOURCE: scripts/sync_submission_status.py
# AI_TEAM_MANAGED_SHA256: 84db7d4baae55b0cd2886688e2d8bcfdcf0eeea635b66293d8595bbb514bae0f
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


MARKER_BEGIN = "<!-- SUBMISSION_STATUS:BEGIN -->"
MARKER_END = "<!-- SUBMISSION_STATUS:END -->"
ALLOWED_STATUSES = {"draft", "in_review", "approved", "frozen", "obsolete"}
GATE_KEYS = (
    "validators_passed",
    "status_synced",
    "consistency_check_passed",
    "review_receipts_present",
    "review_blockers_cleared",
)
HANDOFF_CONTRACT_KEYS = (
    "project_entry",
    "module_entries",
    "handoff_audit_globs",
    "process_audit_globs",
)
GOVERNANCE_LOG_PATH = Path(".ai-team/state/governance-log.jsonl")
GOVERNANCE_LATEST_PATH = Path(".ai-team/state/governance-latest.json")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync submission status from the JSON source of truth.")
    parser.add_argument(
        "--project-root",
        help="Real project root containing 80-完整提交包/00-提交状态.json. Defaults to current working directory.",
    )
    return parser.parse_args(argv)


def repo_root_from_args(project_root: str | None) -> Path:
    root = Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()
    return root


def load_config(root: Path) -> dict:
    path = root / "80-完整提交包/00-提交状态.json"
    return json.loads(path.read_text(encoding="utf-8"))


def status_path(root: Path) -> Path:
    return root / "80-完整提交包/00-提交状态.json"


def bool_label(value: bool) -> str:
    return "yes" if value is True else "no"


def canonical_outward_phase_and_allow(status: dict) -> tuple[str, bool]:
    gates = status.get("gates", {})
    phase = status["phase"]
    allow_human_review = status["allow_human_review"] is True
    if gates.get("consistency_check_passed") is not True:
        if phase == "ready_for_human_review":
            phase = "pending_consistency_check"
        allow_human_review = False
    return phase, allow_human_review


def append_handoff_error(errors: list[str], message: str) -> None:
    errors.append(f"artifacts.engineering_handoff {message}")


def normalize_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def normalize_module_entries(value: object, errors: list[str], *, required: bool) -> list[dict[str, str]]:
    if not isinstance(value, list):
        append_handoff_error(errors, "module_entries must be a list")
        return []

    normalized: list[dict[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            append_handoff_error(errors, f"module_entries[{index}] must be an object")
            continue
        module_id = str(item.get("module_id", "")).strip()
        entry_file = str(item.get("entry_file", "")).strip()
        checklist_file = str(item.get("checklist_file", "")).strip()
        if not module_id:
            append_handoff_error(errors, f"module_entries[{index}].module_id must be a non-empty string")
        if not entry_file:
            append_handoff_error(errors, f"module_entries[{index}].entry_file must be a non-empty string")
        if not checklist_file:
            append_handoff_error(errors, f"module_entries[{index}].checklist_file must be a non-empty string")
        if module_id and entry_file and checklist_file:
            normalized.append(
                {
                    "module_id": module_id,
                    "entry_file": entry_file,
                    "checklist_file": checklist_file,
                }
            )
    if required and not normalized:
        append_handoff_error(errors, "module_entries must contain at least one typed entry")
    return normalized


def engineering_handoff_contract(artifacts: dict, status: dict, errors: list[str] | None = None) -> dict:
    issues = errors if errors is not None else []
    required = status.get("engineering_handoff_required") is True or status.get("engineering_handoff_ready") is True
    value = artifacts.get("engineering_handoff")
    empty_contract = {
        "project_entry": "",
        "module_entries": [],
        "handoff_audit_globs": [],
        "process_audit_globs": [],
    }
    if not isinstance(value, dict):
        if required:
            append_handoff_error(issues, "missing formal contract")
        return empty_contract

    has_formal_contract = any(key in value for key in HANDOFF_CONTRACT_KEYS)
    if not has_formal_contract:
        if required:
            append_handoff_error(issues, "missing formal contract")
        return empty_contract

    for key in HANDOFF_CONTRACT_KEYS:
        if key not in value:
            append_handoff_error(issues, f"missing required key: {key}")

    project_entry = str(value.get("project_entry", "")).strip()
    if not project_entry and required:
        append_handoff_error(issues, "project_entry must be a non-empty string path")

    handoff_audit_globs = normalize_string_list(value.get("handoff_audit_globs"))
    process_audit_globs = normalize_string_list(value.get("process_audit_globs"))
    if required and not handoff_audit_globs:
        append_handoff_error(issues, "handoff_audit_globs must be a non-empty list")
    if required and not process_audit_globs:
        append_handoff_error(issues, "process_audit_globs must be a non-empty list")

    return {
        "project_entry": project_entry,
        "module_entries": normalize_module_entries(value.get("module_entries"), issues, required=required),
        "handoff_audit_globs": handoff_audit_globs,
        "process_audit_globs": process_audit_globs,
    }


def collect_engineering_handoff_targets(root: Path, contract: dict) -> list[Path]:
    targets: list[Path] = []
    if contract["project_entry"]:
        targets.append(root / contract["project_entry"])
    for entry in contract["module_entries"]:
        targets.append(root / entry["entry_file"])
        targets.append(root / entry["checklist_file"])
    deduped: list[Path] = []
    seen: set[Path] = set()
    for target in targets:
        if target in seen:
            continue
        seen.add(target)
        deduped.append(target)
    return deduped


def render_status_block(config: dict, current_file: Path, state_file: Path) -> str:
    source_link = Path(os.path.relpath(state_file, start=current_file.parent))
    status = config["status"]
    gates = status.get("gates", {})
    outward_phase, outward_allow_human_review = canonical_outward_phase_and_allow(status)
    return "\n".join(
        [
            MARKER_BEGIN,
            "## 提交状态",
            "",
            f"- PRD状态：`{status['prd']}`",
            f"- 原型状态：`{status['prototype']}`",
            f"- 评审状态：`{status['review']}`",
            f"- 当前阶段：`{outward_phase}`",
            f"- 可进入人工评审：`{bool_label(outward_allow_human_review)}`",
            f"- 工程交接必检：`{bool_label(status.get('engineering_handoff_required'))}`",
            f"- 工程交接就绪：`{bool_label(status.get('engineering_handoff_ready'))}`",
            f"- 最新评审批次：`{status['last_review_batch']}`",
            f"- validators_passed：{bool_label(gates.get('validators_passed') is True)}",
            f"- status_synced：{bool_label(gates.get('status_synced') is True)}",
            f"- consistency_check_passed：{bool_label(gates.get('consistency_check_passed') is True)}",
            f"- review_receipts_present：{bool_label(gates.get('review_receipts_present') is True)}",
            f"- review_blockers_cleared：{bool_label(gates.get('review_blockers_cleared') is True)}",
            f"- 状态真源：[00-提交状态.json]({source_link.as_posix()})",
            MARKER_END,
        ]
    )


def replace_or_insert_status_block(text: str, block: str) -> str:
    pattern = re.compile(rf"{re.escape(MARKER_BEGIN)}[\s\S]*?{re.escape(MARKER_END)}", re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(block, text, count=1)

    heading_match = re.search(r"^## ", text, re.MULTILINE)
    if not heading_match:
        return text.rstrip() + "\n\n" + block + "\n"
    insert_at = heading_match.start()
    return text[:insert_at].rstrip() + "\n\n" + block + "\n\n" + text[insert_at:].lstrip()


def sync_prd_index(text: str, prd_status: str) -> str:
    pattern = re.compile(r"(^- 状态：`)([^`]+)(`$)", re.MULTILINE)
    return pattern.sub(lambda m: f"{m.group(1)}{prd_status}{m.group(3)}", text)


def sync_prd_file(text: str, prd_status: str, updated_at: str) -> str:
    text = re.sub(
        r"(\| 文档状态 \| `)([^`]+)(` \|)",
        lambda m: f"{m.group(1)}{prd_status}{m.group(3)}",
        text,
        count=1,
    )
    text = re.sub(
        r"(\| 更新时间 \| `)([^`]+)(` \|)",
        lambda m: f"{m.group(1)}{updated_at}{m.group(3)}",
        text,
        count=1,
    )
    return text


def sync_overview_table(text: str, status_rows: dict[str, str]) -> str:
    lines = []
    row_pattern = re.compile(r"^\| `([^`]+)` \| (.*?) \|")
    for line in text.splitlines():
        match = row_pattern.match(line)
        if match and match.group(1) in status_rows:
            parts = line.split("|")
            if len(parts) >= 4:
                parts[2] = f" {status_rows[match.group(1)]} "
                line = "|".join(parts)
        lines.append(line)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def normalize_sync_gates(config: dict) -> dict:
    status = config.setdefault("status", {})
    gates = status.setdefault("gates", {})
    for key in GATE_KEYS:
        if key not in gates:
            gates[key] = False
    gates["status_synced"] = True
    gates["consistency_check_passed"] = False
    return config


def collect_status_block_targets(root: Path, artifacts: dict, status: dict, errors: list[str] | None = None) -> list[Path]:
    base_targets = [
        root / artifacts["overview_file"],
        root / artifacts["prd_index"],
        root / artifacts["prototype_index"],
        root / artifacts["review_index"],
    ]
    reading_layer = str(artifacts.get("reading_layer", "")).strip()
    if reading_layer:
        base_targets.append(root / reading_layer)
    handoff_contract = engineering_handoff_contract(artifacts, status, errors)
    return base_targets + collect_engineering_handoff_targets(root, handoff_contract)


def assert_allowed(config: dict) -> None:
    for key in ("prd", "prototype", "review"):
        value = config["status"][key]
        if value not in ALLOWED_STATUSES:
            raise ValueError(f"Unsupported status for {key}: {value}")


def write_governance_event(root: Path, state_file: Path, written_targets: list[Path]) -> None:
    runtime_path = root / ".ai-team/runtime.json"
    bundle_version = None
    release_tag = None
    if runtime_path.exists():
        runtime_payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        raw_bundle_version = runtime_payload.get("bundle_version")
        bundle_version = raw_bundle_version if isinstance(raw_bundle_version, str) and raw_bundle_version else None
        raw_release_tag = runtime_payload.get("release_tag")
        release_tag = raw_release_tag if isinstance(raw_release_tag, str) and raw_release_tag else None

    relative_written = [path.relative_to(root).as_posix() for path in written_targets]
    snapshot_targets = [state_file, *written_targets]
    snapshot_hashes = {}
    for path in snapshot_targets:
        if path.exists() and path.is_file():
            snapshot_hashes[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()

    event = {
        "schema_version": 1,
        "event_type": "submission_status_sync",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "bundle_version": bundle_version,
        "release_tag": release_tag,
        "project_root": str(root),
        "input_refs": [state_file.relative_to(root).as_posix()],
        "output_refs": relative_written,
        "result": "ok",
        "warnings": [],
        "blockers": [],
        "written_targets": relative_written,
        "snapshot_hashes": snapshot_hashes,
    }
    log_path = root / GOVERNANCE_LOG_PATH
    latest_path = root / GOVERNANCE_LATEST_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    latest_path.write_text(json.dumps(event, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        root = repo_root_from_args(args.project_root)
        config = normalize_sync_gates(load_config(root))
        assert_allowed(config)
        state_file = status_path(root)
        artifacts = config["artifacts"]
        errors: list[str] = []

        status_block_targets = collect_status_block_targets(root, artifacts, config["status"], errors)
        for path in status_block_targets:
            if not path.exists():
                errors.append(f"missing artifact: {path}")
        prd_paths = [root / rel for rel in artifacts["prd_files"]]
        for path in prd_paths:
            if not path.exists():
                errors.append(f"missing PRD file: {path}")
        if errors:
            print("submission status sync failed:")
            for item in errors:
                print(f"- {item}")
            return 1

        overview_path = root / artifacts["overview_file"]
        overview_text = overview_path.read_text(encoding="utf-8")
        overview_block = render_status_block(config, overview_path, state_file)
        overview_text = replace_or_insert_status_block(overview_text, overview_block)
        overview_rows = artifacts.get("overview_status_rows", {})
        if isinstance(overview_rows, dict):
            overview_text = sync_overview_table(overview_text, overview_rows)
        overview_path.write_text(overview_text, encoding="utf-8")

        for path in status_block_targets[1:]:
            text = path.read_text(encoding="utf-8")
            block = render_status_block(config, path, state_file)
            text = replace_or_insert_status_block(text, block)
            if path == root / artifacts["prd_index"]:
                text = sync_prd_index(text, config["status"]["prd"])
            path.write_text(text, encoding="utf-8")

        for path in prd_paths:
            text = path.read_text(encoding="utf-8")
            text = sync_prd_file(text, config["status"]["prd"], config["updated_at"])
            path.write_text(text, encoding="utf-8")

        state_file.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written_targets = [state_file, *status_block_targets, *prd_paths]
        write_governance_event(root, state_file, written_targets)
        print(f"synced submission status from {state_file}")
        return 0
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        print("submission status sync failed:")
        print(f"- {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
