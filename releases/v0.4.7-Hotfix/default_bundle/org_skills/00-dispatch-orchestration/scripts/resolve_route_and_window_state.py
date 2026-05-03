#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_NAME = SCRIPT_PATH.name
CONTRACT_VERSION = "v0.4.3"
REQUIRED_JOIN_FIELDS = ("dispatch_instance_id", "task_chain_id", "task_chain_epoch")
DEFAULT_WRITABLE_TARGET = "00-项目包/04-过程文件/00-沟通记录与结论回写.md"
ROOT = SCRIPT_PATH.parents[3]
REGISTRY_PATH = ROOT / "assets" / "contracts" / "dispatch_contract_registry.json"
PATH_RULES_PATH = ROOT / "assets" / "rules" / "产品路径约束.yaml"
AUTHORITY_REPLAY_RETENTION_FIELD_MAP = {
    "latest_consumed_receipt_consumed": "receipt_consumed",
    "latest_consumed_receipt_dispatch_instance_id": "dispatch_instance_id",
    "latest_consumed_receipt_task_chain_id": "task_chain_id",
    "latest_consumed_receipt_task_chain_epoch": "task_chain_epoch",
    "latest_consumed_receipt_child_thread": "child_thread",
    "latest_consumed_receipt_current_phase": "current_phase",
    "latest_consumed_receipt_return_reason": "return_reason",
    "latest_consumed_receipt_recommended_return_target": "recommended_return_target",
    "latest_consumed_receipt_delivery_mode_explicit": "delivery_mode_explicit",
    "latest_consumed_receipt_active_module_set_explicit": "active_module_set_explicit",
    "latest_consumed_receipt_module_structure_ready": "module_structure_ready",
    "latest_consumed_receipt_writable_targets_ready": "writable_targets_ready",
    "latest_consumed_receipt_next_10_writable_targets": "next_10_writable_targets",
}
PRIMARY_WINDOW_DISPATCH = {
    "project_package_initialization": "01-编排-初始化项目包",
    "product_source_completion": "10-执行-产品专家",
}
PRIMARY_WINDOW_AGENTS = tuple(PRIMARY_WINDOW_DISPATCH.values())
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
    parser = argparse.ArgumentParser(description="Resolve route/window state and materialize a closed handoff spec.")
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


def parse_boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return bool(value)


def load_json_mapping(path: Path, *, field_name: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=[f"{field_name} could not be read: {exc}"]) from exc
    except json.JSONDecodeError as exc:
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=[f"{field_name} is not valid JSON: {exc}"]) from exc
    return require_mapping(payload, field_name=field_name)


def load_yaml_mapping(path: Path, *, field_name: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=[f"{field_name} could not be read: {exc}"]) from exc
    except yaml.YAMLError as exc:
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=[f"{field_name} is not valid YAML: {exc}"]) from exc
    return require_mapping(payload, field_name=field_name)


def load_input_payload(input_path: Path) -> dict[str, Any]:
    if not input_path.is_absolute():
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=["--input-json must be an absolute path"])
    return load_json_mapping(input_path, field_name="input_json")


def load_registry_entry(dispatch_intent: str) -> dict[str, Any]:
    registry_payload = load_json_mapping(REGISTRY_PATH, field_name="dispatch_contract_registry")
    entries = registry_payload.get("entries")
    if not isinstance(entries, list):
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=["dispatch_contract_registry entries must be a list"])
    for entry in entries:
        if isinstance(entry, dict) and entry.get("dispatch_intent") == dispatch_intent:
            return entry
    raise ScriptFailure(exit_code=2, decision="dispatch_blocked", errors=[f"dispatch_intent has no registry entry: {dispatch_intent}"])


def validate_join_fields(authority_snapshot: dict[str, Any], latest_status: dict[str, Any]) -> None:
    errors: list[str] = []
    for field_name in REQUIRED_JOIN_FIELDS:
        if authority_snapshot.get(field_name) in (None, ""):
            errors.append(f"missing authority join field: {field_name}")
            continue
        latest_value = latest_status.get(field_name)
        if latest_value in (None, ""):
            continue
        if latest_value != authority_snapshot[field_name]:
            errors.append(f"join field mismatch: {field_name}")
    if errors:
        raise ScriptFailure(exit_code=2, decision="dispatch_blocked", errors=errors)


def is_same_join_chain(authority_snapshot: dict[str, Any], latest_status: dict[str, Any]) -> bool:
    return all(
        latest_status.get(field_name) not in (None, "") and latest_status.get(field_name) == authority_snapshot.get(field_name)
        for field_name in REQUIRED_JOIN_FIELDS
    )


def is_same_retained_receipt_join_chain(authority_snapshot: dict[str, Any], latest_status: dict[str, Any]) -> bool:
    retained_field_map = {
        "dispatch_instance_id": "latest_consumed_receipt_dispatch_instance_id",
        "task_chain_id": "latest_consumed_receipt_task_chain_id",
        "task_chain_epoch": "latest_consumed_receipt_task_chain_epoch",
    }
    return all(
        latest_status.get(status_field) not in (None, "")
        and latest_status.get(status_field) == authority_snapshot.get(authority_field)
        for status_field, authority_field in retained_field_map.items()
    )


def build_retained_latest_status(authority_snapshot: dict[str, Any]) -> dict[str, Any]:
    retained_status: dict[str, Any] = {}
    for authority_field, status_field in AUTHORITY_REPLAY_RETENTION_FIELD_MAP.items():
        value = authority_snapshot.get(authority_field)
        if value in (None, ""):
            continue
        if status_field == "receipt_consumed":
            retained_status[status_field] = parse_boolish(value)
        else:
            retained_status[status_field] = value
    return retained_status


def merge_latest_status(authority_snapshot: dict[str, Any], latest_status: dict[str, Any]) -> dict[str, Any]:
    merged = build_retained_latest_status(authority_snapshot)
    merged.update(latest_status)
    return merged


def normalize_writable_targets(dispatch_request: dict[str, Any]) -> list[str]:
    writable_targets = dispatch_request.get("writable_targets")
    if not isinstance(writable_targets, list) or not writable_targets:
        return [DEFAULT_WRITABLE_TARGET]
    normalized: list[str] = []
    for target in writable_targets:
        if isinstance(target, str) and target.strip():
            normalized.append(target.strip())
    return normalized or [DEFAULT_WRITABLE_TARGET]


def normalize_target_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        return [part.strip() for part in re.split(r"[|,，]\s*", stripped) if part.strip()]
    return []


def formal_module_prd_targets(value: object) -> set[str]:
    return {
        target
        for target in normalize_target_list(value)
        if FORMAL_MODULE_PRD_TARGET_PATTERN.fullmatch(target)
    }


def execution_structure_ready_for_10(latest_status: dict[str, Any], dispatch_request: dict[str, Any]) -> bool:
    if any(latest_status.get(field_name) is not True for field_name in EXECUTION_STRUCTURE_BOOLEAN_FIELDS):
        return False
    next_targets = formal_module_prd_targets(latest_status.get("next_10_writable_targets"))
    if not next_targets:
        return False
    dispatch_targets = set(normalize_writable_targets(dispatch_request))
    return bool(next_targets.intersection(dispatch_targets))


def build_closed_handoff_spec(
    *,
    authority_snapshot: dict[str, Any],
    dispatch_request: dict[str, Any],
    dispatch_intent: str,
    registry_entry: dict[str, Any],
) -> dict[str, Any]:
    allow_direct_user_question = bool(dispatch_request.get("allow_direct_user_question", False))
    allowed_user_question_scope = str(dispatch_request.get("allowed_user_question_scope", "none")).strip() or "none"
    if allow_direct_user_question and allowed_user_question_scope == "none":
        allowed_user_question_scope = "resolver-runtime-dispatch"
    if not allow_direct_user_question:
        allowed_user_question_scope = "none"
    input_package = dispatch_request.get("input_package")
    if not isinstance(input_package, dict):
        input_package = {
            "goal": f"Dispatch {registry_entry['agent']} from total-control route resolver.",
            "source": SCRIPT_NAME,
        }
    handoff_spec = {
        "label": str(dispatch_request.get("label") or f"派发{registry_entry['agent']}"),
        "agent": registry_entry["agent"],
        "role_prompt_source": registry_entry["role_prompt_source"],
        "dispatch_instance_id": authority_snapshot["dispatch_instance_id"],
        "task_chain_id": authority_snapshot["task_chain_id"],
        "task_chain_epoch": authority_snapshot["task_chain_epoch"],
        "writable_targets": normalize_writable_targets(dispatch_request),
        "allow_direct_user_question": allow_direct_user_question,
        "allowed_user_question_scope": allowed_user_question_scope,
        "input_package": input_package,
        "dispatch_intent": dispatch_intent,
        "dod": registry_entry["dod"],
        "receipt_contract": registry_entry["receipt_contract"],
        "blocker_scope": registry_entry["blocker_scope"],
    }
    return handoff_spec


def fail_closed_route_result(*, reason: str) -> dict[str, Any]:
    return {
        "route_verdict": "route_blocked",
        "dispatch_allowed": False,
        "dispatch_target": None,
        "next_required_action": "/总控",
        "receipt_join_fields": list(REQUIRED_JOIN_FIELDS),
        "receipt_replay_required_fields": [
            "child_thread",
            "current_phase",
            "return_reason",
            "recommended_return_target",
        ],
        "block_reason": reason,
    }


def validate_registry_taxonomy(
    *,
    registry_entry: dict[str, Any],
    path_rules: dict[str, Any],
    dispatch_intent: str,
) -> None:
    agent = require_string(registry_entry.get("agent"), field_name=f"{dispatch_intent}.agent")
    routing_contract = require_mapping(path_rules.get("routing_contract"), field_name="routing_contract")
    new_project_host_model = routing_contract.get("new_project_host_model")
    historical_project_host_model = routing_contract.get("historical_project_host_model")
    if new_project_host_model != ["00-编排-总控", *PRIMARY_WINDOW_AGENTS]:
        raise ScriptFailure(
            exit_code=2,
            decision="dispatch_blocked",
            errors=["routing_contract.new_project_host_model must stay fixed as 00 + 01 + 10"],
            result=fail_closed_route_result(reason="registry_taxonomy_conflict"),
        )
    if historical_project_host_model != ["00-编排-总控", "10-执行-产品专家"]:
        raise ScriptFailure(
            exit_code=2,
            decision="dispatch_blocked",
            errors=["routing_contract.historical_project_host_model must stay fixed as 00 + 10"],
            result=fail_closed_route_result(reason="registry_taxonomy_conflict"),
        )
    if dispatch_intent in PRIMARY_WINDOW_DISPATCH:
        expected_agent = PRIMARY_WINDOW_DISPATCH[dispatch_intent]
        if agent != expected_agent:
            raise ScriptFailure(
                exit_code=2,
                decision="dispatch_blocked",
                errors=[f"registry taxonomy conflict: {dispatch_intent} must map to {expected_agent}"],
                result=fail_closed_route_result(reason="registry_taxonomy_conflict"),
            )
        return
    if agent in PRIMARY_WINDOW_AGENTS:
        raise ScriptFailure(
            exit_code=2,
            decision="dispatch_blocked",
            errors=[f"registry taxonomy conflict: non-primary dispatch_intent cannot reuse primary-window agent {agent}"],
            result=fail_closed_route_result(reason="registry_taxonomy_conflict"),
        )


def resolve_dispatch_authority(
    *,
    dispatch_intent: str,
    registry_entry: dict[str, Any],
    authority_snapshot: dict[str, Any],
    dispatch_request: dict[str, Any],
    latest_status: dict[str, Any],
) -> tuple[bool, str]:
    agent = require_string(registry_entry.get("agent"), field_name=f"{dispatch_intent}.agent")
    if agent not in PRIMARY_WINDOW_AGENTS:
        return True, "dispatch_authorized"
    if dispatch_intent == "project_package_initialization":
        return True, "dispatch_authorized"
    if dispatch_intent != "product_source_completion":
        raise ScriptFailure(
            exit_code=2,
            decision="dispatch_blocked",
            errors=[f"dispatch_intent is outside current primary-window dispatch authority: {dispatch_intent}"],
            result=fail_closed_route_result(reason="unsupported_primary_window_dispatch_intent"),
        )

    child_thread = latest_status.get("child_thread")
    receipt_consumed = latest_status.get("receipt_consumed") is True
    same_join_chain = is_same_join_chain(authority_snapshot, latest_status) or is_same_retained_receipt_join_chain(
        authority_snapshot,
        latest_status,
    )
    return_reason = latest_status.get("return_reason")
    recommended_return_target = latest_status.get("recommended_return_target")
    if (
        receipt_consumed
        and same_join_chain
        and child_thread == "01-编排-初始化项目包"
        and return_reason == "completed"
        and recommended_return_target == "10-执行-产品专家"
    ):
        if not execution_structure_ready_for_10(latest_status, dispatch_request):
            return False, "execution_structure_rejudge_required"
        return True, "receipt_rejudge_ready"
    return False, "receipt_rejudge_required"


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        payload = load_input_payload(Path(args.input_json).expanduser().resolve())
        authority_snapshot = require_mapping(payload.get("authority_snapshot"), field_name="authority_snapshot")
        raw_latest_status = require_mapping(
            payload.get("latest_consumed_receipt_status", {}),
            field_name="latest_consumed_receipt_status",
        )
        dispatch_intent = require_string(payload.get("dispatch_intent"), field_name="dispatch_intent")
        dispatch_request = require_mapping(payload.get("dispatch_request", {}), field_name="dispatch_request")
        validate_join_fields(authority_snapshot, raw_latest_status)
        latest_status = merge_latest_status(authority_snapshot, raw_latest_status)
        registry_entry = load_registry_entry(dispatch_intent)
        if dispatch_request.get("target_agent") not in (None, registry_entry["agent"]):
            raise ScriptFailure(
                exit_code=2,
                decision="dispatch_blocked",
                errors=[f"dispatch_request.target_agent mismatch: {dispatch_request.get('target_agent')}"],
            )
        path_rules = load_yaml_mapping(PATH_RULES_PATH, field_name="product_path_constraints")
        validate_registry_taxonomy(
            registry_entry=registry_entry,
            path_rules=path_rules,
            dispatch_intent=dispatch_intent,
        )
        dispatch_allowed, authority_verdict = resolve_dispatch_authority(
            dispatch_intent=dispatch_intent,
            registry_entry=registry_entry,
            authority_snapshot=authority_snapshot,
            dispatch_request=dispatch_request,
            latest_status=latest_status,
        )
        agent = require_string(registry_entry.get("agent"), field_name=f"{dispatch_intent}.agent")
        result: dict[str, Any] = {
            "route_verdict": "dispatch_allowed" if dispatch_allowed else "dispatch_blocked",
            "dispatch_allowed": dispatch_allowed,
            "dispatch_target": agent if dispatch_allowed else None,
            "next_required_action": (
                f"dispatch:{agent}"
                if dispatch_allowed
                else "/总控"
                if authority_verdict == "execution_structure_rejudge_required"
                else "/读取回执"
            ),
            "receipt_join_fields": list(REQUIRED_JOIN_FIELDS),
            "receipt_replay_required_fields": [
                "child_thread",
                "current_phase",
                "return_reason",
                "recommended_return_target",
            ],
            "dispatch_authority": authority_verdict,
        }
        decision = "dispatch_allowed" if dispatch_allowed else "dispatch_blocked"
        if dispatch_allowed:
            result["closed_handoff_spec"] = build_closed_handoff_spec(
                authority_snapshot=authority_snapshot,
                dispatch_request=dispatch_request,
                dispatch_intent=dispatch_intent,
                registry_entry=registry_entry,
            )
        return emit(ok=True, decision=decision, result=result, errors=[], exit_code=0)
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
