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
REQUIRED_USER_REJUDGE_FIELDS = (
    "user_rejudge_intent_summary",
    "user_rejudge_affected_scope",
    "user_rejudge_requested_direction",
)
REQUIRED_FORMAL_RECEIPT_FIELDS = (
    "read_what",
    "changed_what",
    "ran_what",
    "evidence",
    "blockers",
    "next",
)
AUTHORITY_EVIDENCE_FIELDS = (
    "role_prompt_source",
    "role_prompt_sha256",
    "dispatch_prompt_path",
    "dispatch_prompt_sha256",
)
REQUIRED_RECEIPT_SECTIONS = ("工单回执", "dispatch_evidence")
PRIMARY_WINDOW_CHILD_THREADS = {
    "01-编排-初始化项目包",
    "10-执行-产品专家",
}
TOTAL_CONTROL_RETURN_TARGETS = {
    "00-编排-总控",
}
NO_PRIMARY_WINDOW_NEXT_HOP = "no_primary_window_next_hop"
SCREENING_GATE_STATUSES = {
    "screening_complete",
    "screening_blocked",
    "screening_changed_boundary",
}
DEEPENING_GATE_STATUSES = {
    "deepening_complete",
    "deepening_blocked",
    "deepening_changed_boundary",
}
CANONICAL_RETURN_REASONS = {
    "completed",
    "blocked",
    "need_user",
    "worker_requested",
    "scope_changed",
    "user_interrupt_rejudge",
}
PLACEHOLDER_VALUES = {"n/a", "na", "none", "null", "无", "不适用", "待填", "tbd"}
CR004_UNCLOSED_TRIGGER_TOKENS = ("unknown_requires_confirmation", "changed_boundary")
CR004_BOOLEAN_FIELDS = ("human_confirmed", "blocks_next_stage")
CR004_BOOLEAN_VALUES = {"true", "false"}
SCREENING_RESULT_REQUIRED_FIELDS = (
    "screening_item",
    "phase",
    "question_asked",
    "user_answer",
    "trigger_status",
    "trigger_reason",
    "formal_hosts",
    "handoff_to_10",
    "human_confirmed",
    "blocks_next_stage",
)
DEEPENING_RESULT_REQUIRED_FIELDS = (
    "source_screening_item",
    "source_trigger_status",
    "deepening_status",
    "prd_hosts",
    "pages_states_paths",
    "rules_or_mechanisms",
    "acceptance_criteria",
    "product_confirmation_items",
    "human_confirmed",
    "blocks_next_stage",
)
SCREENING_TRIGGER_STATUSES = {
    "triggered",
    "not_triggered",
    "unknown_requires_confirmation",
    "changed_boundary",
}
DEEPENING_STATUSES = {
    "resolved",
    "blocked",
    "deferred_non_blocker",
}
EXECUTION_STRUCTURE_FIELDS = (
    "delivery_mode_explicit",
    "active_module_set_explicit",
    "module_structure_ready",
    "writable_targets_ready",
    "next_10_writable_targets",
)
EXECUTION_STRUCTURE_BOOLEAN_FIELDS = (
    "delivery_mode_explicit",
    "active_module_set_explicit",
    "module_structure_ready",
    "writable_targets_ready",
)
FORMAL_MODULE_PRD_TARGET_PATTERN = re.compile(r"^01-模块执行包/[^/]+/01-PRD/01-模块PRD\.md$")


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


def merge_receipt_payload_value(receipt_payload: dict[str, Any], field_name: str, parsed_value: Any) -> None:
    existing_value = receipt_payload.get(field_name)
    if existing_value not in (None, "", parsed_value) and parsed_value not in (None, ""):
        raise ScriptFailure(
            exit_code=3,
            decision="schema_error",
            errors=[f"receipt_carrier contains conflicting field value: {field_name}"],
        )
    receipt_payload[field_name] = parsed_value


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
    nested_item_pattern = re.compile(r"^\s+-\s+(?P<value>.+?)\s*$")
    for heading in REQUIRED_RECEIPT_SECTIONS:
        current_field: str | None = None
        for line in sections[heading].splitlines():
            if not line.strip():
                continue
            match = field_pattern.match(line)
            if not match:
                nested_match = nested_item_pattern.match(line)
                if current_field and nested_match:
                    item_value = nested_match.group("value").strip()
                    if not item_value:
                        continue
                    existing_value = receipt_payload.get(current_field)
                    if existing_value in (None, ""):
                        receipt_payload[current_field] = [item_value]
                    elif isinstance(existing_value, list):
                        existing_value.append(item_value)
                    else:
                        raise ScriptFailure(
                            exit_code=3,
                            decision="schema_error",
                            errors=[f"receipt_carrier contains conflicting field value: {current_field}"],
                        )
                    continue
                current_field = None
                continue
            field_name = match.group("field").strip()
            parsed_value = normalize_receipt_value(match.group("value"))
            merge_receipt_payload_value(receipt_payload, field_name, parsed_value)
            current_field = field_name
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
    recommended_return_target = receipt_payload.get("recommended_return_target")
    if recommended_return_target in TOTAL_CONTROL_RETURN_TARGETS:
        errors.append(
            "recommended_return_target must be business next-hop for 00 rejudge, "
            f"not total-control return target: {recommended_return_target}"
        )
    elif child_thread in PRIMARY_WINDOW_CHILD_THREADS:
        supported_targets = supported_return_targets(child_thread=child_thread, return_reason=return_reason)
        if recommended_return_target not in supported_targets:
            supported_label = ", ".join(sorted(supported_targets)) if supported_targets else "none"
            errors.append(
                "unsupported recommended_return_target for child_thread "
                f"{child_thread}: {recommended_return_target}; supported={supported_label}"
            )
    if return_reason == "user_interrupt_rejudge":
        errors.extend(validate_user_rejudge_intent_fields(receipt_payload))
    if errors:
        raise ScriptFailure(exit_code=2, decision="receipt_blocked", errors=errors)


def validate_user_rejudge_intent_fields(receipt_payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field_name in REQUIRED_USER_REJUDGE_FIELDS:
        value = receipt_payload.get(field_name)
        if not is_meaningful_user_rejudge_value(value):
            errors.append(f"missing user_interrupt_rejudge required field: {field_name}")
    return errors


def is_meaningful_user_rejudge_value(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip()
    if not normalized:
        return False
    return normalized.lower() not in PLACEHOLDER_VALUES


def supported_return_targets(*, child_thread: object, return_reason: object) -> set[str]:
    if child_thread == "01-编排-初始化项目包" and return_reason == "completed":
        return {"10-执行-产品专家"}
    if child_thread == "01-编排-初始化项目包":
        return {NO_PRIMARY_WINDOW_NEXT_HOP}
    if child_thread == "10-执行-产品专家":
        return {NO_PRIMARY_WINDOW_NEXT_HOP}
    return set()


def validate_formal_receipt_fields(receipt_payload: dict[str, Any]) -> None:
    errors: list[str] = []
    for field_name in REQUIRED_FORMAL_RECEIPT_FIELDS:
        value = receipt_payload.get(field_name)
        if value in (None, "") or (isinstance(value, list) and not value):
            errors.append(f"missing formal receipt field: {field_name}")
    if errors:
        raise ScriptFailure(exit_code=2, decision="receipt_blocked", errors=errors)


def validate_cr004_receipt_fields(receipt_payload: dict[str, Any]) -> None:
    if receipt_payload.get("return_reason") == "user_interrupt_rejudge":
        return
    child_thread = receipt_payload.get("child_thread")
    errors: list[str] = []
    if child_thread == "01-编排-初始化项目包":
        errors.extend(
            validate_required_result_and_gate_status(
                receipt_payload,
                result_field="screening_result",
                gate_field="screening_result_gate_status",
                allowed_statuses=SCREENING_GATE_STATUSES,
                complete_status="screening_complete",
                result_required_fields=SCREENING_RESULT_REQUIRED_FIELDS,
                enum_field="trigger_status",
                allowed_enum_values=SCREENING_TRIGGER_STATUSES,
            )
        )
    elif child_thread == "10-执行-产品专家":
        errors.extend(
            validate_required_result_and_gate_status(
                receipt_payload,
                result_field="deepening_result",
                gate_field="deepening_result_gate_status",
                allowed_statuses=DEEPENING_GATE_STATUSES,
                complete_status="deepening_complete",
                result_required_fields=DEEPENING_RESULT_REQUIRED_FIELDS,
                enum_field="deepening_status",
                allowed_enum_values=DEEPENING_STATUSES,
            )
        )
    if errors:
        raise ScriptFailure(exit_code=2, decision="receipt_blocked", errors=errors)


def normalize_target_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        return [part.strip() for part in re.split(r"[|,，]\s*", stripped) if part.strip()]
    return []


def contains_formal_module_prd_target(value: object) -> bool:
    return any(FORMAL_MODULE_PRD_TARGET_PATTERN.fullmatch(target) for target in normalize_target_list(value))


def validate_01_to_10_execution_structure(receipt_payload: dict[str, Any]) -> None:
    if not (
        receipt_payload.get("child_thread") == "01-编排-初始化项目包"
        and receipt_payload.get("return_reason") == "completed"
        and receipt_payload.get("recommended_return_target") == "10-执行-产品专家"
    ):
        return

    errors: list[str] = []
    for field_name in EXECUTION_STRUCTURE_FIELDS:
        value = receipt_payload.get(field_name)
        if value in (None, "") or (isinstance(value, list) and not value):
            errors.append(f"missing 01 -> 10 execution structure field: {field_name}")
    for field_name in EXECUTION_STRUCTURE_BOOLEAN_FIELDS:
        if receipt_payload.get(field_name) is not True:
            errors.append(f"01 -> 10 execution structure field must be true: {field_name}")
    if not contains_formal_module_prd_target(receipt_payload.get("next_10_writable_targets")):
        errors.append(
            "next_10_writable_targets must include a formal PRD target: "
            "01-模块执行包/<模块名>/01-PRD/01-模块PRD.md; "
            "80-完整提交包 cannot stand in for module PRD truth"
        )
    if errors:
        raise ScriptFailure(exit_code=2, decision="receipt_blocked", errors=errors)


def validate_required_result_and_gate_status(
    receipt_payload: dict[str, Any],
    *,
    result_field: str,
    gate_field: str,
    allowed_statuses: set[str],
    complete_status: str,
    result_required_fields: tuple[str, ...],
    enum_field: str,
    allowed_enum_values: set[str],
) -> list[str]:
    errors: list[str] = []
    result_value = receipt_payload.get(result_field)
    if not is_meaningful_receipt_value(result_value):
        errors.append(f"missing CR-004 receipt field: {result_field}")
    gate_value = receipt_payload.get(gate_field)
    if not is_meaningful_receipt_value(gate_value):
        errors.append(f"missing CR-004 receipt field: {gate_field}")
    elif gate_value not in allowed_statuses:
        supported_label = ", ".join(sorted(allowed_statuses))
        errors.append(f"{gate_field} must use allowed CR-004 gate status: {gate_value}; supported={supported_label}")
    elif gate_value == complete_status:
        errors.extend(
            validate_cr004_trigger_relation_closed(
                result_field=result_field,
                result_value=result_value,
                gate_field=gate_field,
                required_fields=result_required_fields,
                enum_field=enum_field,
                allowed_enum_values=allowed_enum_values,
            )
        )
    return errors


def is_meaningful_receipt_value(value: object) -> bool:
    if value in (None, "") or (isinstance(value, list) and not value):
        return False
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return False
        return normalized.lower() not in PLACEHOLDER_VALUES
    return True


def validate_cr004_trigger_relation_closed(
    *,
    result_field: str,
    result_value: object,
    gate_field: str,
    required_fields: tuple[str, ...],
    enum_field: str,
    allowed_enum_values: set[str],
) -> list[str]:
    if not is_meaningful_receipt_value(result_value):
        return []
    structured_result = parse_cr004_result_fields(result_value)
    if isinstance(result_value, list):
        normalized_result = "\n".join(str(item) for item in result_value).lower()
    else:
        normalized_result = str(result_value).lower()
    errors: list[str] = []
    for field_name in required_fields:
        if field_name not in structured_result or not str(structured_result[field_name]).strip():
            errors.append(f"CR-004 trigger relation not closed: {result_field} missing structured field {field_name}")
    enum_value = structured_result.get(enum_field, "").strip()
    if enum_value and enum_value not in allowed_enum_values:
        supported_label = ", ".join(sorted(allowed_enum_values))
        errors.append(f"CR-004 trigger relation not closed: {result_field}.{enum_field}={enum_value}; supported={supported_label}")
    errors.extend(validate_cr004_boolean_fields(result_field=result_field, structured_result=structured_result))
    if result_field == "screening_result" and structured_result.get("trigger_status") == "triggered":
        handoff_value = structured_result.get("handoff_to_10", "").strip().lower()
        if not handoff_value or handoff_value in PLACEHOLDER_VALUES:
            errors.append("CR-004 trigger relation not closed: triggered screening_result missing handoff_to_10")
    if result_field == "deepening_result" and structured_result.get("deepening_status") == "blocked":
        errors.append("CR-004 trigger relation not closed: deepening_result is blocked but gate status is complete")
    if structured_result.get("blocks_next_stage", "").strip().lower() == "true":
        errors.append(f"CR-004 trigger relation not closed: {result_field} has blocks_next_stage=true but {gate_field} is complete")
    for token in CR004_UNCLOSED_TRIGGER_TOKENS:
        if token in normalized_result:
            errors.append(f"CR-004 trigger relation not closed: {result_field} contains {token} but {gate_field} is complete")
    return errors


def validate_cr004_boolean_fields(*, result_field: str, structured_result: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for field_name in CR004_BOOLEAN_FIELDS:
        raw_value = structured_result.get(field_name)
        if raw_value is None:
            continue
        normalized_value = raw_value.strip().lower()
        if normalized_value not in CR004_BOOLEAN_VALUES:
            errors.append(f"CR-004 trigger relation not closed: {result_field}.{field_name} must be true or false: {raw_value}")
    if structured_result.get("human_confirmed", "").strip().lower() == "false":
        errors.append(f"CR-004 trigger relation not closed: {result_field} has human_confirmed=false but gate status is complete")
    return errors


def parse_cr004_result_fields(result_value: object) -> dict[str, str]:
    if isinstance(result_value, list):
        text = "\n".join(str(item) for item in result_value)
    else:
        text = str(result_value)
    fields: dict[str, str] = {}
    for match in re.finditer(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(?P<value>.*?)(?=(?:[;\n]\s*)[A-Za-z_][A-Za-z0-9_]*\s*[:=]|\Z)", text, re.DOTALL):
        key = match.group("key").strip()
        value = match.group("value").strip().strip(";")
        if key:
            fields[key] = value
    return fields


def validate_active_child_thread(authority_snapshot: dict[str, Any], receipt_payload: dict[str, Any]) -> None:
    target_agent = authority_snapshot.get("target_agent")
    if target_agent in (None, ""):
        return
    child_thread = receipt_payload.get("child_thread")
    if child_thread != target_agent:
        raise ScriptFailure(
            exit_code=2,
            decision="receipt_blocked",
            errors=[f"receipt child_thread must match active dispatch target_agent: {child_thread} != {target_agent}"],
        )


def validate_active_dispatch_evidence(authority_snapshot: dict[str, Any], receipt_payload: dict[str, Any]) -> None:
    errors: list[str] = []
    for field_name in AUTHORITY_EVIDENCE_FIELDS:
        authority_value = authority_snapshot.get(field_name)
        if authority_value in (None, ""):
            continue
        receipt_value = receipt_payload.get(field_name)
        if receipt_value in (None, ""):
            errors.append(f"missing receipt evidence field: {field_name}")
            continue
        if receipt_value != authority_value:
            errors.append(f"active dispatch evidence mismatch: {field_name}")
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
        validate_active_child_thread(authority_snapshot, receipt_payload)
        validate_active_dispatch_evidence(authority_snapshot, receipt_payload)
        validate_formal_receipt_fields(receipt_payload)
        validate_replay_fields(receipt_payload)
        validate_cr004_receipt_fields(receipt_payload)
        validate_01_to_10_execution_structure(receipt_payload)
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
