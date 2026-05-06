#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_NAME = Path(__file__).name
CONTRACT_VERSION = "v0.4.3"


class ScriptFailure(Exception):
    def __init__(self, *, exit_code: int, decision: str, errors: list[str], result: dict[str, Any] | None = None) -> None:
        super().__init__("; ".join(errors))
        self.exit_code = exit_code
        self.decision = decision
        self.errors = errors
        self.result = result or {}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lint human-visible output and block machine-only leakage.")
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
    if not isinstance(value, str):
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=[f"{field_name} must be a string"])
    return value


def require_string_list(value: object, *, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=[f"{field_name} must decode to list"])
    normalized: list[str] = []
    for index, member in enumerate(value):
        if not isinstance(member, str) or not member.strip():
            raise ScriptFailure(
                exit_code=3,
                decision="schema_error",
                errors=[f"{field_name}[{index}] must be a non-empty string"],
            )
        normalized.append(member.strip())
    return normalized


def collect_non_empty_lines(candidate_body: str) -> list[str]:
    return [line.strip() for line in candidate_body.splitlines() if line.strip()]


def lint_summary_shape(candidate_body: str, surface_contract: dict[str, Any]) -> list[str]:
    allowed_single_line_literals = require_string_list(
        surface_contract.get("allowed_single_line_literals", []),
        field_name="allowed_single_line_literals",
    )
    if candidate_body.strip() in allowed_single_line_literals:
        return []

    required_non_empty_lines = surface_contract.get("required_non_empty_lines")
    if required_non_empty_lines is None and "required_line_prefix_groups" not in surface_contract:
        return []
    if not isinstance(required_non_empty_lines, int) or required_non_empty_lines <= 0:
        raise ScriptFailure(
            exit_code=3,
            decision="schema_error",
            errors=["required_non_empty_lines must be a positive integer when summary shape contract is enabled"],
        )

    required_line_prefix_groups_raw = surface_contract.get("required_line_prefix_groups")
    if not isinstance(required_line_prefix_groups_raw, list):
        raise ScriptFailure(
            exit_code=3,
            decision="schema_error",
            errors=["required_line_prefix_groups must decode to list when summary shape contract is enabled"],
        )
    required_line_prefix_groups = [
        require_string_list(group, field_name=f"required_line_prefix_groups[{index}]")
        for index, group in enumerate(required_line_prefix_groups_raw)
    ]

    lines = collect_non_empty_lines(candidate_body)
    errors: list[str] = []
    if len(lines) != required_non_empty_lines:
        errors.append(
            "human-visible surface must match required_non_empty_lines="
            f"{required_non_empty_lines}, got {len(lines)}"
        )

    for index, prefix_group in enumerate(required_line_prefix_groups):
        if index >= len(lines):
            break
        if not any(lines[index].startswith(prefix) for prefix in prefix_group):
            errors.append(
                "human-visible surface line "
                f"{index + 1} must start with one of: {', '.join(prefix_group)}"
            )
    return errors


def load_input_payload(input_path: Path) -> dict[str, Any]:
    if not input_path.is_absolute():
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=["--input-json must be an absolute path"])
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=[f"input json could not be read: {exc}"]) from exc
    except json.JSONDecodeError as exc:
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=[f"input json is not valid JSON: {exc}"]) from exc
    return require_mapping(payload, field_name="input_json")


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        payload = load_input_payload(Path(args.input_json).expanduser().resolve())
        candidate_body = require_string(payload.get("candidate_human_visible_body"), field_name="candidate_human_visible_body")
        surface_contract = require_mapping(payload.get("surface_contract"), field_name="surface_contract")
        errors: list[str] = []
        for forbidden_literal in surface_contract.get("forbidden_literals", []):
            if isinstance(forbidden_literal, str) and forbidden_literal and forbidden_literal in candidate_body:
                errors.append(f"human-visible surface leaked forbidden literal: {forbidden_literal}")
        for forbidden_field in surface_contract.get("forbidden_internal_fields", []):
            if isinstance(forbidden_field, str) and forbidden_field and forbidden_field in candidate_body:
                errors.append(f"human-visible surface leaked machine-only field: {forbidden_field}")
        errors.extend(lint_summary_shape(candidate_body, surface_contract))
        if errors:
            raise ScriptFailure(
                exit_code=2,
                decision="surface_blocked",
                errors=errors,
                result={"clean_human_visible_body": ""},
            )
        return emit(
            ok=True,
            decision="surface_clean",
            result={"clean_human_visible_body": candidate_body},
            errors=[],
            exit_code=0,
        )
    except ScriptFailure as exc:
        return emit(ok=False, decision=exc.decision, result=exc.result, errors=exc.errors, exit_code=exc.exit_code)
    except Exception as exc:  # pragma: no cover - envelope guard
        return emit(
            ok=False,
            decision="runtime_error",
            result={},
            errors=[f"unhandled runtime error: {exc}"],
            exit_code=3,
        )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
