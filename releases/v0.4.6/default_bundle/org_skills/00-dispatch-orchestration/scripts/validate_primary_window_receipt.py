#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


SCRIPT_NAME = Path(__file__).name
CONTRACT_VERSION = "v0.4.3"
REQUIRED_JOIN_FIELDS = ("dispatch_instance_id", "task_chain_id", "task_chain_epoch")
REQUIRED_REPLAY_FIELDS = (
    "child_thread",
    "current_phase",
    "return_reason",
    "recommended_return_target",
)
REQUIRED_RECEIPT_SECTIONS = ("工单回执", "dispatch_evidence")
PRIMARY_WINDOW_CHILD_THREADS = {
    "01-编排-初始化项目包",
    "10-执行-产品专家",
}
CANONICAL_RETURN_REASONS = {
    "completed",
    "blocked",
    "need_user",
    "worker_requested",
    "scope_changed",
}


class ScriptFailure(Exception):
    def __init__(self, *, exit_code: int, decision: str, errors: list[str], result: dict[str, Any] | None = None) -> None:
        super().__init__("; ".join(errors))
        self.exit_code = exit_code
        self.decision = decision
        self.errors = errors
        self.result = result or {}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a primary-window receipt carrier for total-control rejudge.")
    parser.add_argument("--input-json", required=True, help="Absolute path to the structured input JSON file.")
    return parser.parse_args(argv)


def emit(*, ok: bool, decision: str, result: dict[str, Any], errors: list[str], exit_code: int) -> int:
    payload = {
        "ok": ok,
        "script": SCRIPT_NAME,
        "contract_version": CONTRACT_VERSION,
        "decision": decision,
        "result": result,
        "errors": errors,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return exit_code


def require_mapping(value: object, *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=[f"{field_name} must decode to mapping"])
    return dict(value)


def require_string(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=[f"{field_name} must be a non-empty string"])
    return value.strip()


def normalize_receipt_value(raw_value: str) -> Any:
    value = raw_value.strip()
    if not value:
        return ""
    if value.startswith("【") and value.endswith("】"):
        return ""
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            return value
    return value


def load_input_payload(input_path: Path) -> dict[str, Any]:
    if not input_path.is_absolute():
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=["--input-json must be an absolute path"])
    try:
        raw_text = input_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=[f"input json could not be read: {exc}"]) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=[f"input json is not valid JSON: {exc}"]) from exc
    return require_mapping(payload, field_name="input_json")


def parse_receipt_carrier(receipt_carrier: str) -> dict[str, Any]:
    section_matches = list(
        re.finditer(r"^## (?P<heading>[^\n]+)\n(?P<body>.*?)(?=^## |\Z)", receipt_carrier, re.MULTILINE | re.DOTALL)
    )
    if not section_matches:
        raise ScriptFailure(
            exit_code=3,
            decision="schema_error",
            errors=["receipt_carrier must be a machine receipt carrier with required sections: 工单回执, dispatch_evidence"],
        )
    sections: dict[str, str] = {}
    duplicate_headings: list[str] = []
    for match in section_matches:
        heading = match.group("heading").strip()
        body = match.group("body")
        if heading in sections:
            duplicate_headings.append(heading)
            continue
        sections[heading] = body
    if duplicate_headings:
        raise ScriptFailure(
            exit_code=3,
            decision="schema_error",
            errors=[f"receipt_carrier duplicate section heading is not allowed: {', '.join(sorted(set(duplicate_headings)))}"],
        )
    missing_sections = [heading for heading in REQUIRED_RECEIPT_SECTIONS if heading not in sections]
    if missing_sections:
        raise ScriptFailure(
            exit_code=3,
            decision="schema_error",
            errors=[f"receipt_carrier missing required sections: {', '.join(missing_sections)}"],
        )

    receipt_payload: dict[str, Any] = {}
    field_pattern = re.compile(r"^- (?P<field>[^：:\n]+)[：:](?P<value>.*)$")
    for heading in REQUIRED_RECEIPT_SECTIONS:
        for line in sections[heading].splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            match = field_pattern.match(stripped)
            if not match:
                continue
            field_name = match.group("field").strip()
            parsed_value = normalize_receipt_value(match.group("value"))
            existing_value = receipt_payload.get(field_name)
            if existing_value not in (None, "", parsed_value) and parsed_value not in (None, ""):
                raise ScriptFailure(
                    exit_code=3,
                    decision="schema_error",
                    errors=[f"receipt_carrier contains conflicting field value: {field_name}"],
                )
            receipt_payload[field_name] = parsed_value
    if not receipt_payload:
        raise ScriptFailure(
            exit_code=3,
            decision="schema_error",
            errors=["receipt_carrier machine sections did not materialize any consumable receipt fields"],
        )
    return receipt_payload


def validate_join_fields(authority_snapshot: dict[str, Any], receipt_payload: dict[str, Any]) -> None:
    errors: list[str] = []
    for field_name in REQUIRED_JOIN_FIELDS:
        authority_value = authority_snapshot.get(field_name)
        if authority_value in (None, ""):
            errors.append(f"missing authority join field: {field_name}")
            continue
        receipt_value = receipt_payload.get(field_name)
        if receipt_value in (None, ""):
            errors.append(f"missing receipt join field: {field_name}")
            continue
        if receipt_value != authority_value:
            errors.append(f"join field mismatch: {field_name}")
    if errors:
        raise ScriptFailure(exit_code=2, decision="receipt_blocked", errors=errors)


def validate_replay_fields(receipt_payload: dict[str, Any]) -> None:
    errors: list[str] = []
    for field_name in REQUIRED_REPLAY_FIELDS:
        value = receipt_payload.get(field_name)
        if value in (None, "") or (isinstance(value, list) and not value):
            errors.append(f"missing replay-required field: {field_name}")
    child_thread = receipt_payload.get("child_thread")
    if child_thread not in PRIMARY_WINDOW_CHILD_THREADS:
        errors.append("primary window receipt must originate from 01-编排-初始化项目包 or 10-执行-产品专家")
    return_reason = receipt_payload.get("return_reason")
    if return_reason not in CANONICAL_RETURN_REASONS:
        errors.append(f"return_reason must use canonical token: {return_reason}")
    if errors:
        raise ScriptFailure(exit_code=2, decision="receipt_blocked", errors=errors)


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        payload = load_input_payload(Path(args.input_json).expanduser().resolve())
        authority_snapshot = require_mapping(payload.get("authority_snapshot"), field_name="authority_snapshot")
        receipt_carrier = require_string(payload.get("receipt_carrier"), field_name="receipt_carrier")
        receipt_payload = parse_receipt_carrier(receipt_carrier)
        validate_join_fields(authority_snapshot, receipt_payload)
        validate_replay_fields(receipt_payload)
        return emit(
            ok=True,
            decision="receipt_valid",
            result={
                "validated_receipt": receipt_payload,
                "rejudge_allowed": True,
            },
            errors=[],
            exit_code=0,
        )
    except ScriptFailure as exc:
        return emit(ok=False, decision=exc.decision, result=exc.result, errors=exc.errors, exit_code=exc.exit_code)
    except Exception as exc:  # pragma: no cover - last-resort envelope guard
        return emit(
            ok=False,
            decision="runtime_error",
            result={},
            errors=[f"unhandled runtime error: {exc}"],
            exit_code=3,
        )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
