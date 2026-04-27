#!/usr/bin/env python3
# AI_TEAM_MANAGED_SOURCE: scripts/check_final_delivery_gate.py
# AI_TEAM_MANAGED_SHA256: 9f31ef216a5490d82d0497ef9110d2147ae156661c65c670fa13803cde17ed9f
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path


STATUS_PATH = Path("80-完整提交包/00-提交状态.json")
RECEIPT_PATH = Path("80-完整提交包/03-合并评审记录/30-结果-AI深审记录.md")
PROJECT_LEVEL_GATE_B_INPUT = Path("00-项目包/04-过程文件/04-全量提交-gate-b.input.json")
MODULE_LEVEL_GATE_B_GLOB = "01-模块执行包/*/04-过程文件/gate-b.input.json"
EXPECTED_GATE_B_SCHEMA = "submission_status.gate_b_evidence_pack"
EXPECTED_RECEIPT_SCHEMA = "submission_status.final_review_evidence_receipt"
EXPECTED_RECEIPT_SCHEMA_VERSION = "v1"
RECEIPT_BEGIN_MARKER = "<!-- FINAL_REVIEW_EVIDENCE_RECEIPT:BEGIN -->"
RECEIPT_END_MARKER = "<!-- FINAL_REVIEW_EVIDENCE_RECEIPT:END -->"
REQUIRED_MACHINE_CHECKS = (
    "sync_submission_status",
    "check_submission_consistency",
    "check_publish_boundary",
)
STATUS_SNAPSHOT_KEYS = (
    "phase",
    "allow_human_review",
    "engineering_handoff_required",
    "engineering_handoff_ready",
    "last_review_batch",
)
OUTWARD_ENTRY_KEYS = (
    "overview_file",
    "prd_index",
    "reading_layer",
    "prototype_index",
    "review_index",
)
SCRIPT_EXIT_CODES = {
    "pass": 0,
    "blocked": 1,
    "stale": 2,
}
FINAL_GATE_SEMANTIC_BOUNDARY = {
    "version": "v0.3.5",
    "judgement_scope": "final_review_evidence_reuse_freshness_only",
    "judges_only_final_review_evidence_reuse_freshness": True,
    "writes_status_truth": False,
    "reruns_sync_submission_status": False,
}

BATCH_SEQUENCE_PATTERN = re.compile(r"batch-(\d+)\Z")
REVIEW_DATE_PATTERN = re.compile(r"review-(\d{4}-\d{2}-\d{2})\Z")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate whether final-review evidence can still be reused.")
    parser.add_argument(
        "--project-root",
        help="Project root containing 80-完整提交包/00-提交状态.json. Defaults to current working directory.",
    )
    return parser.parse_args(argv)


def repo_root_from_args(project_root: str | None) -> Path:
    return Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()


def read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object expected: {path}")
    return payload


def canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def file_sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def normalize_text_file(path: Path) -> bytes:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return text.encode("utf-8")


def current_status_snapshot(status: dict) -> dict[str, object]:
    return {key: status.get(key) for key in STATUS_SNAPSHOT_KEYS}


def final_gate_semantic_boundary() -> dict[str, object]:
    return dict(FINAL_GATE_SEMANTIC_BOUNDARY)


def validate_status_truth_snapshot(current_status: dict, snapshot: dict) -> None:
    expected = current_status_snapshot(current_status)
    if snapshot != expected:
        raise ValueError("status_truth_snapshot mismatch")


def extract_receipt_payload(text: str) -> dict:
    begin_count = text.count(RECEIPT_BEGIN_MARKER)
    end_count = text.count(RECEIPT_END_MARKER)
    if begin_count != 1 or end_count != 1:
        if begin_count > 1 or end_count > 1:
            raise ValueError("multiple receipt blocks found")
        raise ValueError("canonical receipt block missing")

    start = text.index(RECEIPT_BEGIN_MARKER) + len(RECEIPT_BEGIN_MARKER)
    end = text.index(RECEIPT_END_MARKER)
    if end <= start:
        raise ValueError("canonical receipt markers are out of order")
    body = text[start:end].strip()
    fence_count = body.count("```")
    if fence_count != 2:
        raise ValueError("receipt block must contain exactly one json fenced block")
    match = re.fullmatch(r"```json\s*\n([\s\S]*?)\n```", body)
    if match is None:
        raise ValueError("receipt block must contain exactly one json fenced block")
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ValueError(f"receipt JSON is invalid: {exc}") from None
    if not isinstance(payload, dict):
        raise ValueError("receipt JSON must be an object")
    return payload


def require_receipt_file(project_root: Path) -> Path:
    path = project_root / RECEIPT_PATH
    if not path.exists():
        raise ValueError(f"canonical receipt missing: {RECEIPT_PATH.as_posix()}")
    return path


def require_status_file(project_root: Path) -> Path:
    path = project_root / STATUS_PATH
    if not path.exists():
        raise ValueError(f"missing status truth: {STATUS_PATH.as_posix()}")
    return path


def expected_gate_b_mode(status: dict) -> str:
    return "required" if status.get("engineering_handoff_required") is True else "not_required"


def require_project_level_gate_b_pack(project_root: Path, *, required: bool) -> tuple[dict | None, Path | None]:
    project_level = project_root / PROJECT_LEVEL_GATE_B_INPUT
    module_level = sorted(project_root.glob(MODULE_LEVEL_GATE_B_GLOB))
    if not required:
        return None, None
    if not project_level.exists():
        if module_level:
            raise ValueError(
                "project-level Gate B aggregate pack is missing; module-level packs are not authoritative for final gate"
            )
        raise ValueError("project-level Gate B aggregate pack is missing")
    payload = read_json(project_level)
    if payload.get("schema") != EXPECTED_GATE_B_SCHEMA:
        raise ValueError("project-level Gate B aggregate pack schema mismatch")
    if not payload.get("schema_version"):
        raise ValueError("project-level Gate B aggregate pack schema_version is missing")
    return payload, project_level


def normalize_status_for_fingerprint(status: dict) -> dict[str, object]:
    return {
        "phase": status.get("phase"),
        "allow_human_review": status.get("allow_human_review"),
        "gates": status.get("gates", {}),
        "engineering_handoff_required": status.get("engineering_handoff_required"),
        "engineering_handoff_ready": status.get("engineering_handoff_ready"),
        "last_review_batch": status.get("last_review_batch"),
    }


def fingerprint_entry(entry_type: str, path: Path, payload: bytes, *, project_root: Path) -> dict[str, str]:
    return {
        "type": entry_type,
        "path": path.relative_to(project_root).as_posix(),
        "sha256": file_sha256_bytes(payload),
    }


def build_fingerprint_inputs(project_root: Path, config: dict) -> tuple[list[dict[str, str]], str]:
    status = config.get("status", {})
    artifacts = config.get("artifacts", {})
    entries: list[dict[str, str]] = []

    status_payload = canonical_json_bytes(normalize_status_for_fingerprint(status))
    entries.append(
        fingerprint_entry(
            "status_truth",
            project_root / STATUS_PATH,
            status_payload,
            project_root=project_root,
        )
    )

    for relative_path in sorted(str(item).strip() for item in artifacts.get("prd_files", []) if str(item).strip()):
        path = project_root / relative_path
        if not path.exists():
            raise ValueError(f"missing PRD fingerprint input: {relative_path}")
        entries.append(fingerprint_entry("prd_truth", path, normalize_text_file(path), project_root=project_root))

    for key in OUTWARD_ENTRY_KEYS:
        relative_path = str(artifacts.get(key, "")).strip()
        if not relative_path:
            continue
        path = project_root / relative_path
        if not path.exists():
            raise ValueError(f"missing outward fingerprint input: {relative_path}")
        entries.append(fingerprint_entry("outward_entry", path, normalize_text_file(path), project_root=project_root))

    gate_b_required = expected_gate_b_mode(status) == "required"
    gate_b_payload, gate_b_path = require_project_level_gate_b_pack(project_root, required=gate_b_required)
    if gate_b_payload is not None and gate_b_path is not None:
        entries.append(
            fingerprint_entry(
                "gate_b_project_pack",
                gate_b_path,
                canonical_json_bytes(gate_b_payload),
                project_root=project_root,
            )
        )

    digest = "sha256:" + file_sha256_bytes(canonical_json_bytes(entries))
    return entries, digest


def validate_fingerprint_inputs(
    receipt_inputs: object,
    expected_inputs: list[dict[str, str]],
    *,
    compare_sha256: bool,
) -> None:
    if not isinstance(receipt_inputs, list):
        raise ValueError("fingerprint_inputs must be a list")
    if len(receipt_inputs) != len(expected_inputs):
        raise ValueError("fingerprint_inputs length mismatch")

    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(receipt_inputs):
        if not isinstance(item, dict):
            raise ValueError("fingerprint_inputs entries must be objects")
        entry_type = str(item.get("type", "")).strip()
        path = str(item.get("path", "")).strip()
        sha256 = str(item.get("sha256", "")).strip()
        if not entry_type or not path or not sha256:
            raise ValueError("fingerprint_inputs entries must contain type/path/sha256")
        key = (entry_type, path)
        if key in seen:
            raise ValueError("fingerprint_inputs contains duplicate type/path entries")
        seen.add(key)
        expected_key = (expected_inputs[index]["type"], expected_inputs[index]["path"])
        if key != expected_key:
            raise ValueError("fingerprint_inputs path order mismatch")
        if compare_sha256 and sha256 != expected_inputs[index]["sha256"]:
            raise ValueError("fingerprint_inputs sha256 mismatch")


def validate_receipt_machine_checks(receipt: dict) -> None:
    machine_checks = receipt.get("machine_checks")
    if not isinstance(machine_checks, dict):
        raise ValueError("receipt.machine_checks must be an object")
    for key in REQUIRED_MACHINE_CHECKS:
        value = machine_checks.get(key)
        if value not in {"pass", "not_required"}:
            raise ValueError(f"receipt.machine_checks.{key} has unsupported value")


def validate_review_refs(receipt: dict) -> None:
    review_refs = receipt.get("review_refs")
    if not isinstance(review_refs, list):
        raise ValueError("receipt.review_refs must be a list")
    normalized = [str(item).strip() for item in review_refs if str(item).strip()]
    carrier = RECEIPT_PATH.as_posix()
    if carrier not in normalized:
        raise ValueError("receipt.review_refs must include the canonical receipt carrier")
    review_scope_prefix = RECEIPT_PATH.parent.as_posix() + "/"
    closeout_sources = [item for item in normalized if item != carrier and item.startswith(review_scope_prefix)]
    if not closeout_sources:
        raise ValueError("receipt.review_refs must include at least one closeout source reference")


def validate_semantic_boundary(receipt: dict) -> None:
    if receipt.get("semantic_boundary") != final_gate_semantic_boundary():
        raise ValueError("receipt semantic_boundary mismatch")


def parse_review_batch(value: object, *, field_name: str) -> tuple[str, int | date]:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty")
    match = BATCH_SEQUENCE_PATTERN.fullmatch(normalized)
    if match is not None:
        return ("batch", int(match.group(1)))
    match = REVIEW_DATE_PATTERN.fullmatch(normalized)
    if match is not None:
        try:
            return ("review", date.fromisoformat(match.group(1)))
        except ValueError as exc:
            raise ValueError(f"{field_name} has invalid review_batch date") from exc
    raise ValueError(f"{field_name} has unsupported review_batch format")


def validate_review_batch_alignment(status: dict, receipt: dict) -> None:
    status_batch = str(status.get("last_review_batch", "")).strip()
    receipt_batch = str(receipt.get("review_batch", "")).strip()
    parse_review_batch(status_batch, field_name="status.last_review_batch")
    parse_review_batch(receipt_batch, field_name="receipt.review_batch")
    if status_batch != receipt_batch:
        raise ValueError("receipt.review_batch must exactly match status.last_review_batch")


def validate_receipt(
    receipt: dict,
    *,
    current_status: dict,
    expected_inputs: list[dict[str, str]],
    compare_sha256: bool,
) -> None:
    required_keys = {
        "schema",
        "schema_version",
        "generated_at",
        "bundle_version",
        "receipt_id",
        "review_batch",
        "gate_b_mode",
        "semantic_boundary",
        "delivery_fingerprint",
        "fingerprint_inputs",
        "machine_checks",
        "status_truth_snapshot",
        "review_refs",
    }
    missing = sorted(key for key in required_keys if key not in receipt)
    if missing:
        raise ValueError(f"receipt missing required keys: {', '.join(missing)}")
    if not str(receipt.get("review_batch", "")).strip():
        raise ValueError("receipt review_batch must be non-empty")
    if receipt.get("schema") != EXPECTED_RECEIPT_SCHEMA:
        raise ValueError("receipt schema mismatch")
    if receipt.get("schema_version") != EXPECTED_RECEIPT_SCHEMA_VERSION:
        raise ValueError("receipt schema_version mismatch")
    if receipt.get("gate_b_mode") != expected_gate_b_mode(current_status):
        raise ValueError("receipt gate_b_mode mismatch")
    validate_semantic_boundary(receipt)
    validate_status_truth_snapshot(current_status, receipt.get("status_truth_snapshot"))
    validate_fingerprint_inputs(receipt.get("fingerprint_inputs"), expected_inputs, compare_sha256=compare_sha256)
    validate_receipt_machine_checks(receipt)
    validate_review_refs(receipt)


def script_path(script_name: str) -> Path:
    return Path(__file__).resolve().parent / script_name


def run_required_script(project_root: Path, script_name: str) -> tuple[str, str, list[str]]:
    path = script_path(script_name)
    if not path.exists():
        return "blocked", "", [f"required script missing: {path.name}"]
    result = subprocess.run(
        [sys.executable, str(path), "--project-root", str(project_root)],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode == 0:
        return "pass", output, []
    return "blocked", output, [f"{path.name} failed"]


def rerun_machine_checks(project_root: Path) -> tuple[dict[str, str], list[str], dict[str, str]]:
    machine_checks: dict[str, str] = {"sync_submission_status": "not_required"}
    outputs: dict[str, str] = {"sync_submission_status": ""}
    blockers: list[str] = []
    for script_name in (
        "check_submission_consistency.py",
        "check_publish_boundary.py",
    ):
        status, output, script_blockers = run_required_script(project_root, script_name)
        key = script_name.replace(".py", "")
        machine_checks[key] = status
        outputs[key] = output
        blockers.extend(script_blockers)
        if status != "pass":
            break
    return machine_checks, blockers, outputs


def load_status_config(project_root: Path) -> dict:
    return read_json(require_status_file(project_root))


def evaluate_final_delivery_gate(project_root: Path) -> dict[str, object]:
    semantic_boundary = final_gate_semantic_boundary()
    machine_checks, blockers, script_outputs = rerun_machine_checks(project_root)
    if blockers:
        return {
            "result": "blocked",
            "gate_b_mode": "unknown",
            "machine_checks": machine_checks,
            "blockers": blockers,
            "warnings": [],
            "script_outputs": script_outputs,
            "semantic_boundary": semantic_boundary,
        }

    config = load_status_config(project_root)
    status = config.get("status", {})
    gate_b_mode = expected_gate_b_mode(status)
    if gate_b_mode == "required":
        if status.get("engineering_handoff_ready") is not True:
            blockers.append("engineering_handoff_ready must be true when final gate requires Gate B")
        gates = status.get("gates", {})
        if gates.get("status_synced") is not True:
            blockers.append("status.gates.status_synced must be true before final gate can pass")
        if gates.get("consistency_check_passed") is not True:
            blockers.append("status.gates.consistency_check_passed must be true before final gate can pass")
        if blockers:
            return {
                "result": "blocked",
                "gate_b_mode": gate_b_mode,
                "machine_checks": machine_checks,
                "blockers": blockers,
                "warnings": [],
                "script_outputs": script_outputs,
                "semantic_boundary": semantic_boundary,
            }

    try:
        expected_inputs, delivery_fingerprint = build_fingerprint_inputs(project_root, config)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        blockers.append(str(exc))
        return {
            "result": "blocked",
            "gate_b_mode": gate_b_mode,
            "machine_checks": machine_checks,
            "blockers": blockers,
            "warnings": [],
            "script_outputs": script_outputs,
            "semantic_boundary": semantic_boundary,
        }

    try:
        receipt_path = require_receipt_file(project_root)
        receipt = extract_receipt_payload(receipt_path.read_text(encoding="utf-8"))
        validate_review_batch_alignment(status, receipt)
        compare_sha256 = receipt.get("delivery_fingerprint") == delivery_fingerprint
        validate_receipt(
            receipt,
            current_status=status,
            expected_inputs=expected_inputs,
            compare_sha256=compare_sha256,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        blockers.append(str(exc))
        return {
            "result": "blocked",
            "gate_b_mode": gate_b_mode,
            "machine_checks": machine_checks,
            "delivery_fingerprint": delivery_fingerprint,
            "fingerprint_inputs": expected_inputs,
            "blockers": blockers,
            "warnings": [],
            "script_outputs": script_outputs,
            "semantic_boundary": semantic_boundary,
        }

    result = "pass" if compare_sha256 else "stale"
    return {
        "result": result,
        "gate_b_mode": gate_b_mode,
        "machine_checks": machine_checks,
        "canonical_receipt_path": RECEIPT_PATH.as_posix(),
        "delivery_fingerprint": delivery_fingerprint,
        "fingerprint_inputs": expected_inputs,
        "status_truth_snapshot": current_status_snapshot(status),
        "receipt_id": receipt.get("receipt_id"),
        "blockers": blockers,
        "warnings": [],
        "script_outputs": script_outputs,
        "semantic_boundary": semantic_boundary,
    }


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        result = evaluate_final_delivery_gate(repo_root_from_args(args.project_root))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return SCRIPT_EXIT_CODES[result["result"]]
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        payload = {
            "result": "blocked",
            "gate_b_mode": "unknown",
            "machine_checks": {},
            "blockers": [str(exc)],
            "warnings": [],
            "semantic_boundary": final_gate_semantic_boundary(),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return SCRIPT_EXIT_CODES["blocked"]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
