#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
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


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check submission status consistency against the JSON source of truth.")
    parser.add_argument(
        "--project-root",
        help="Real project root containing 80-完整提交包/00-提交状态.json. Defaults to current working directory.",
    )
    return parser.parse_args(argv)


def repo_root_from_args(project_root: str | None) -> Path:
    return Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()


def load_config(root: Path) -> dict:
    return json.loads((root / "80-完整提交包/00-提交状态.json").read_text(encoding="utf-8"))


def status_path(root: Path) -> Path:
    return root / "80-完整提交包/00-提交状态.json"


def extract_status_block(text: str) -> str:
    pattern = re.compile(rf"{re.escape(MARKER_BEGIN)}[\s\S]*?{re.escape(MARKER_END)}", re.MULTILINE)
    match = pattern.search(text)
    return match.group(0) if match else ""


def read_backtick_value(block: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}：`([^`]+)`", block)
    return match.group(1) if match else ""


def read_plain_value(block: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}：([^\n]+)$", block, re.MULTILINE)
    return match.group(1).strip() if match else ""


def expect(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


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


def append_semantic_slot_mismatch(errors: list[str], field: str) -> None:
    errors.append(f"semantic slot mismatch: {field}")


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


def collect_engineering_handoff_targets(root: Path, contract: dict) -> list[tuple[str, Path]]:
    targets: list[tuple[str, Path]] = []
    if contract["project_entry"]:
        targets.append(("Engineering handoff project entry", root / contract["project_entry"]))
    for entry in contract["module_entries"]:
        targets.append((f"Engineering handoff entry ({entry['module_id']})", root / entry["entry_file"]))
        targets.append((f"Engineering handoff checklist ({entry['module_id']})", root / entry["checklist_file"]))
    deduped: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    for label, path in targets:
        if path in seen:
            continue
        seen.add(path)
        deduped.append((label, path))
    return deduped


def expected_block_values(config: dict) -> dict[str, str]:
    outward_phase, outward_allow_human_review = canonical_outward_phase_and_allow(config["status"])
    expected = {
        "PRD状态": config["status"]["prd"],
        "原型状态": config["status"]["prototype"],
        "评审状态": config["status"]["review"],
        "当前阶段": outward_phase,
        "可进入人工评审": "yes" if outward_allow_human_review else "no",
        "工程交接必检": "yes" if config["status"].get("engineering_handoff_required") is True else "no",
        "工程交接就绪": "yes" if config["status"].get("engineering_handoff_ready") is True else "no",
        "最新评审批次": config["status"]["last_review_batch"],
    }
    gates = config["status"].get("gates", {})
    for key in GATE_KEYS:
        expected[key] = "yes" if gates.get(key) is True else "no"
    return expected


def collect_status_block_targets(
    root: Path,
    artifacts: dict,
    status: dict,
    errors: list[str] | None = None,
) -> list[tuple[str, Path]]:
    targets = [
        ("Overview block", root / artifacts["overview_file"]),
        ("PRD index block", root / artifacts["prd_index"]),
        ("Prototype index block", root / artifacts["prototype_index"]),
        ("Review index block", root / artifacts["review_index"]),
    ]
    reading_layer = str(artifacts.get("reading_layer", "")).strip()
    if reading_layer:
        targets.append(("Reading layer block", root / reading_layer))
    return targets + collect_engineering_handoff_targets(root, engineering_handoff_contract(artifacts, status, errors))


def replace_or_insert_status_block(text: str, block: str) -> str:
    pattern = re.compile(rf"{re.escape(MARKER_BEGIN)}[\s\S]*?{re.escape(MARKER_END)}", re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(block, text, count=1)

    heading_match = re.search(r"^## ", text, re.MULTILINE)
    if not heading_match:
        return text.rstrip() + "\n\n" + block + "\n"
    insert_at = heading_match.start()
    return text[:insert_at].rstrip() + "\n\n" + block + "\n\n" + text[insert_at:].lstrip()


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
            f"- 可进入人工评审：`{'yes' if outward_allow_human_review else 'no'}`",
            f"- 工程交接必检：`{'yes' if status.get('engineering_handoff_required') is True else 'no'}`",
            f"- 工程交接就绪：`{'yes' if status.get('engineering_handoff_ready') is True else 'no'}`",
            f"- 最新评审批次：`{status['last_review_batch']}`",
            f"- validators_passed：{'yes' if gates.get('validators_passed') is True else 'no'}",
            f"- status_synced：{'yes' if gates.get('status_synced') is True else 'no'}",
            f"- consistency_check_passed：{'yes' if gates.get('consistency_check_passed') is True else 'no'}",
            f"- review_receipts_present：{'yes' if gates.get('review_receipts_present') is True else 'no'}",
            f"- review_blockers_cleared：{'yes' if gates.get('review_blockers_cleared') is True else 'no'}",
            f"- 状态真源：[00-提交状态.json]({source_link.as_posix()})",
            MARKER_END,
        ]
    )


def stamp_consistency_pass(root: Path, config: dict, artifacts: dict) -> None:
    updated = json.loads(json.dumps(config, ensure_ascii=False))
    updated.setdefault("status", {}).setdefault("gates", {})["consistency_check_passed"] = True
    state_file = status_path(root)
    state_file.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for _, path in collect_status_block_targets(root, artifacts, updated["status"]):
        text = path.read_text(encoding="utf-8")
        block = render_status_block(updated, path, state_file)
        path.write_text(replace_or_insert_status_block(text, block), encoding="utf-8")


def validate_block(block: str, block_name: str, expected_values: dict[str, str], errors: list[str]) -> None:
    for label, expected in expected_values.items():
        actual = read_plain_value(block, label) if label in GATE_KEYS else read_backtick_value(block, label)
        expect(actual == expected, f"{block_name} {label} mismatch", errors)


def validate_source_link(block: str, block_name: str, current_file: Path, state_file: Path, errors: list[str]) -> None:
    expected_link = Path(os.path.relpath(state_file, start=current_file.parent)).as_posix()
    expect(
        f"状态真源：[00-提交状态.json]({expected_link})" in block,
        f"{block_name} 状态真源 link mismatch",
        errors,
    )


def validate_gate_b_carriers(root: Path, config: dict, artifacts: dict, overview_text: str, errors: list[str]) -> None:
    status = config["status"]

    if status.get("engineering_handoff_required") is True:
        if re.search(r"(?m)^engineering_handoff_required:\s*(true|false)\s*$", overview_text):
            append_semantic_slot_mismatch(errors, "engineering_handoff_required")

    if status.get("engineering_handoff_ready") is True:
        prd_files = artifacts.get("prd_files", [])
        if isinstance(prd_files, list):
            for relative_path in prd_files:
                path = root / str(relative_path)
                if not path.exists() or not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8")
                if re.search(r"(?m)^engineering_handoff_ready:\s*(true|false)\s*$", text):
                    append_semantic_slot_mismatch(errors, "engineering_handoff_ready")
                    break


def validate_semantics(config: dict, errors: list[str]) -> None:
    allow_human_review = config["status"]["allow_human_review"] is True
    review_status = config["status"]["review"]
    phase = config["status"]["phase"]
    last_review_batch = config["status"]["last_review_batch"]
    engineering_handoff_required = config["status"].get("engineering_handoff_required") is True
    engineering_handoff_ready = config["status"].get("engineering_handoff_ready") is True
    gates = config["status"].get("gates", {})
    expect(
        gates.get("status_synced") is True,
        "status.gates.status_synced must be true before consistency_check_passed can be restored",
        errors,
    )
    missing_gates = [
        key
        for key in GATE_KEYS
        if gates.get(key) is not True and key != "consistency_check_passed"
    ]
    all_gates_passed = not missing_gates

    if all_gates_passed:
        expect(allow_human_review, "all gates passed but allow_human_review is false", errors)
        expect(review_status in {"approved", "frozen"}, "all gates passed but review status is not approved/frozen", errors)
        expect(phase == "ready_for_human_review", "all gates passed but phase is not ready_for_human_review", errors)
        expect(last_review_batch not in {"", "pending"}, "all gates passed but last_review_batch is empty/pending", errors)
    else:
        expect(not allow_human_review, "ready_for_human_review requires all gates to be true", errors)
        expect(phase != "ready_for_human_review", f"ready_for_human_review requires all gates to be true: {', '.join(missing_gates)}", errors)

    if engineering_handoff_ready:
        expect(engineering_handoff_required, "engineering_handoff_ready requires engineering_handoff_required=true", errors)
        expect(allow_human_review, "engineering_handoff_ready requires allow_human_review=true", errors)

    if not engineering_handoff_required:
        expect(not engineering_handoff_ready, "engineering_handoff_ready cannot be true when engineering_handoff_required is false", errors)


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        root = repo_root_from_args(args.project_root)
        config = load_config(root)
        errors: list[str] = []

        for key in ("prd", "prototype", "review"):
            expect(config["status"][key] in ALLOWED_STATUSES, f"status.{key} has unsupported value: {config['status'][key]}", errors)

        validate_semantics(config, errors)

        artifacts = config["artifacts"]
        target_blocks = collect_status_block_targets(root, artifacts, config["status"], errors)
        overview_file = root / artifacts["overview_file"]
        prd_index = root / artifacts["prd_index"]
        prototype_index = root / artifacts["prototype_index"]
        review_index = root / artifacts["review_index"]

        for _, path in target_blocks:
            expect(path.exists(), f"missing artifact: {path}", errors)

        target_texts = {label: path.read_text(encoding="utf-8") for label, path in target_blocks}
        validate_gate_b_carriers(root, config, artifacts, target_texts["Overview block"], errors)

        if errors:
            print("submission consistency check failed:")
            for item in errors:
                print(f"- {item}")
            return 1

        target_blocks_text = {label: extract_status_block(text) for label, text in target_texts.items()}

        for label, block in target_blocks_text.items():
            expect(bool(block), f"{label} missing submission status block", errors)

        expected_values = expected_block_values(config)

        overview_block = target_blocks_text["Overview block"]
        prd_block = target_blocks_text["PRD index block"]
        prototype_block = target_blocks_text["Prototype index block"]
        review_block = target_blocks_text["Review index block"]
        overview_text = target_texts["Overview block"]
        prd_index_text = target_texts["PRD index block"]

        if overview_block:
            validate_block(overview_block, "Overview block", expected_values, errors)
            validate_source_link(overview_block, "Overview block", overview_file, status_path(root), errors)
            row_pattern = re.compile(r"^\| `([^`]+)` \| (.*?) \|", re.MULTILINE)
            actual_rows = {m.group(1): m.group(2).strip() for m in row_pattern.finditer(overview_text)}
            for key, value in artifacts.get("overview_status_rows", {}).items():
                expect(actual_rows.get(key) == value, f"Overview row status mismatch for {key}", errors)

        if prd_block:
            validate_block(prd_block, "PRD index block", expected_values, errors)
            validate_source_link(prd_block, "PRD index block", prd_index, status_path(root), errors)
            statuses = re.findall(r"- 状态：`([^`]+)`", prd_index_text)
            if statuses:
                expect(all(status == config["status"]["prd"] for status in statuses), "PRD index entry statuses are not all aligned with config", errors)

        if prototype_block:
            validate_block(prototype_block, "Prototype index block", expected_values, errors)
            validate_source_link(prototype_block, "Prototype index block", prototype_index, status_path(root), errors)

        if review_block:
            validate_block(review_block, "Review index block", expected_values, errors)
            validate_source_link(review_block, "Review index block", review_index, status_path(root), errors)

        for label, path in target_blocks[4:]:
            block = target_blocks_text[label]
            if not block:
                continue
            validate_block(block, label, expected_values, errors)
            validate_source_link(block, label, path, status_path(root), errors)

        for rel in artifacts["prd_files"]:
            path = root / rel
            expect(path.exists(), f"missing PRD file: {path}", errors)
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            match = re.search(r"\| 文档状态 \| `([^`]+)` \|", text)
            expect(bool(match), f"PRD file missing 文档状态: {path}", errors)
            if match:
                expect(match.group(1) == config["status"]["prd"], f"PRD file status mismatch: {path}", errors)

        forbidden_substrings = artifacts.get("forbidden_substrings", [])
        handoff_contract = engineering_handoff_contract(artifacts, config["status"])
        audit_globs = (
            artifacts.get("audit_globs", [])
            + handoff_contract["handoff_audit_globs"]
            + handoff_contract["process_audit_globs"]
        )
        for pattern in audit_globs:
            for path in root.glob(pattern):
                if not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8")
                for token in forbidden_substrings:
                    expect(token not in text, f"forbidden token '{token}' found in audited file: {path}", errors)

        if errors:
            print("submission consistency check failed:")
            for item in errors:
                print(f"- {item}")
            return 1

        stamp_consistency_pass(root, config, artifacts)
        print("submission consistency check passed")
        return 0
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        print("submission consistency check failed:")
        print(f"- {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
