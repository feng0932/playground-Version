#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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
    "latest_consumed_receipt_recommended_total_control_state": "recommended_total_control_state",
}


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
        "window_state": "closed",
        "window_state_reason": reason,
        "human_contact_allowed": False,
        "human_contact_owner": "00-编排-总控",
        "human_contact_mode": "control_entry",
        "human_contact_block_reason": reason,
        "next_required_action": "/总控",
        "child_dispatch_authority_verdict": "route_not_authorized",
        "dispatch_allowed": False,
        "allowed_next_actions": ["/总控"],
    }


def validate_registry_taxonomy(
    *,
    registry_entry: dict[str, Any],
    path_rules: dict[str, Any],
    dispatch_intent: str,
) -> None:
    agent = require_string(registry_entry.get("agent"), field_name=f"{dispatch_intent}.agent")
    human_contact_contract = require_mapping(
        registry_entry.get("human_contact_contract"),
        field_name=f"{dispatch_intent}.human_contact_contract",
    )
    window_family = require_string(
        human_contact_contract.get("window_family"),
        field_name=f"{dispatch_intent}.human_contact_contract.window_family",
    )
    host_window_contract = registry_entry.get("host_window_contract")
    if isinstance(host_window_contract, dict):
        slot_type = require_string(
            host_window_contract.get("slot_type"),
            field_name=f"{dispatch_intent}.host_window_contract.slot_type",
        )
        if slot_type == "primary_window" and window_family != "primary_window":
            raise ScriptFailure(
                exit_code=2,
                decision="dispatch_blocked",
                errors=[
                    "registry taxonomy conflict: "
                    f"{dispatch_intent}.host_window_contract.slot_type={slot_type} "
                    f"conflicts with {dispatch_intent}.human_contact_contract.window_family={window_family}"
                ],
                result=fail_closed_route_result(reason="registry_taxonomy_conflict"),
            )
        if slot_type != "primary_window" and window_family == "primary_window":
            raise ScriptFailure(
                exit_code=2,
                decision="dispatch_blocked",
                errors=[
                    "registry taxonomy conflict: "
                    f"{dispatch_intent}.host_window_contract.slot_type={slot_type} "
                    f"conflicts with {dispatch_intent}.human_contact_contract.window_family={window_family}"
                ],
                result=fail_closed_route_result(reason="registry_taxonomy_conflict"),
            )

    routing_contract = require_mapping(path_rules.get("routing_contract"), field_name="routing_contract")
    human_window_family = require_mapping(routing_contract.get("human_window_family"), field_name="routing_contract.human_window_family")
    primary_window_agents = human_window_family.get("primary_window")
    control_entry_agents = human_window_family.get("control_entry")
    if window_family == "primary_window":
        if not isinstance(primary_window_agents, list) or agent not in primary_window_agents:
            raise ScriptFailure(
                exit_code=2,
                decision="dispatch_blocked",
                errors=[f"registry/path taxonomy conflict: {agent} missing from routing_contract.human_window_family.primary_window"],
                result=fail_closed_route_result(reason="registry_taxonomy_conflict"),
            )
    if window_family == "visible_worker":
        if isinstance(primary_window_agents, list) and agent in primary_window_agents:
            raise ScriptFailure(
                exit_code=2,
                decision="dispatch_blocked",
                errors=[f"registry/path taxonomy conflict: {agent} cannot be both visible_worker and primary_window"],
                result=fail_closed_route_result(reason="registry_taxonomy_conflict"),
            )
        if isinstance(control_entry_agents, list) and agent in control_entry_agents:
            raise ScriptFailure(
                exit_code=2,
                decision="dispatch_blocked",
                errors=[f"registry/path taxonomy conflict: {agent} cannot be both visible_worker and control_entry"],
                result=fail_closed_route_result(reason="registry_taxonomy_conflict"),
            )


def resolve_window_state(
    *,
    dispatch_intent: str,
    registry_entry: dict[str, Any],
    authority_snapshot: dict[str, Any],
    dispatch_request: dict[str, Any],
    latest_status: dict[str, Any],
    path_rules: dict[str, Any],
) -> tuple[str, str, bool, str]:
    human_contact_contract = require_mapping(
        registry_entry.get("human_contact_contract"),
        field_name=f"{dispatch_intent}.human_contact_contract",
    )
    window_family = require_string(
        human_contact_contract.get("window_family"),
        field_name=f"{dispatch_intent}.human_contact_contract.window_family",
    )
    if window_family == "visible_worker":
        return "closed", "visible_worker_static_block", True, "dispatch_authorized"
    if dispatch_intent == "project_package_initialization":
        return "active", "active_primary_window", True, "dispatch_authorized"
    if dispatch_intent != "product_source_completion":
        raise ScriptFailure(
            exit_code=2,
            decision="dispatch_blocked",
            errors=[f"dispatch_intent is outside current primary-window dispatch authority: {dispatch_intent}"],
            result=fail_closed_route_result(reason="unsupported_primary_window_dispatch_intent"),
        )

    entry_authority_grant_contract = require_mapping(
        registry_entry.get("entry_authority_grant_contract"),
        field_name=f"{dispatch_intent}.entry_authority_grant_contract",
    )
    positive_grants = entry_authority_grant_contract.get("positive_grants")
    if not isinstance(positive_grants, list):
        raise ScriptFailure(
            exit_code=3,
            decision="schema_error",
            errors=[f"{dispatch_intent}.entry_authority_grant_contract.positive_grants must be a list"],
        )
    indexed_grants = {
        str(grant.get("grant_id")): grant
        for grant in positive_grants
        if isinstance(grant, dict) and str(grant.get("grant_id", "")).strip()
    }
    new_project_grant = require_mapping(
        indexed_grants.get("new_project_receipt_unlock"),
        field_name=f"{dispatch_intent}.entry_authority_grant_contract.positive_grants.new_project_receipt_unlock",
    )
    historical_grant = require_mapping(
        indexed_grants.get("historical_project_classifier_grant"),
        field_name=f"{dispatch_intent}.entry_authority_grant_contract.positive_grants.historical_project_classifier_grant",
    )
    child_thread = latest_status.get("child_thread")
    receipt_consumed = latest_status.get("receipt_consumed") is True
    same_join_chain = is_same_join_chain(authority_snapshot, latest_status)
    return_reason = latest_status.get("return_reason")
    next_state = latest_status.get("recommended_total_control_state")
    if (
        receipt_consumed
        and same_join_chain
        and child_thread == "01-编排-初始化项目包"
        and return_reason == "completed"
        and next_state == "project_baseline_ready_10_unlocked"
    ):
        return "active", "active_primary_window", True, "new_project_receipt_unlock"
    if str(authority_snapshot.get("project_profile") or "").strip() == "historical_project":
        if str(authority_snapshot.get("historical_project_classifier_verdict") or "").strip() == "allow_10":
            return "active", "active_primary_window", True, "historical_project_classifier_grant"
        return (
            "standby",
            "locked_standby_until_historical_project_entry_grant_materialized",
            False,
            "blocked_by_entry_authority_grant",
        )
    return (
        "standby",
        "locked_standby_until_01_receipt_consumed",
        False,
        "blocked_by_unlock_contract",
    )


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        payload = load_input_payload(Path(args.input_json).expanduser().resolve())
        authority_snapshot = require_mapping(payload.get("authority_snapshot"), field_name="authority_snapshot")
        latest_status = require_mapping(payload.get("latest_consumed_receipt_status", {}), field_name="latest_consumed_receipt_status")
        latest_status = merge_latest_status(authority_snapshot, latest_status)
        dispatch_intent = require_string(payload.get("dispatch_intent"), field_name="dispatch_intent")
        dispatch_request = require_mapping(payload.get("dispatch_request", {}), field_name="dispatch_request")
        validate_join_fields(authority_snapshot, latest_status)
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
        window_state, window_state_reason, dispatch_allowed, authority_verdict = resolve_window_state(
            dispatch_intent=dispatch_intent,
            registry_entry=registry_entry,
            authority_snapshot=authority_snapshot,
            dispatch_request=dispatch_request,
            latest_status=latest_status,
            path_rules=path_rules,
        )
        human_contact_contract = require_mapping(
            registry_entry.get("human_contact_contract"),
            field_name=f"{dispatch_intent}.human_contact_contract",
        )
        window_family = require_string(
            human_contact_contract.get("window_family"),
            field_name=f"{dispatch_intent}.human_contact_contract.window_family",
        )
        if dispatch_allowed and window_family == "visible_worker":
            human_contact_owner = str(human_contact_contract.get("fallback_owner", "00-编排-总控"))
            human_contact_mode = "visible_worker_blocked"
            human_contact_block_reason = "current_not_human_window"
            next_required_action = f"dispatch:{registry_entry['agent']}"
        else:
            human_contact_owner = registry_entry["agent"] if dispatch_allowed else "00-编排-总控"
            human_contact_mode = "direct_primary_window" if dispatch_allowed else "control_entry"
            if dispatch_allowed:
                human_contact_block_reason = "none"
            elif authority_verdict == "blocked_by_unlock_contract":
                human_contact_block_reason = "locked_until_01_receipt_consumed"
            elif authority_verdict == "blocked_by_entry_authority_grant":
                human_contact_block_reason = "locked_until_historical_project_entry_grant_materialized"
            else:
                human_contact_block_reason = "unsupported_route"
            next_required_action = f"dispatch:{registry_entry['agent']}" if dispatch_allowed else "/读取回执"
        result: dict[str, Any] = {
            "route_verdict": "dispatch_allowed" if dispatch_allowed else "dispatch_blocked",
            "window_state": window_state,
            "window_state_reason": window_state_reason,
            "human_contact_allowed": dispatch_allowed and window_family == "primary_window",
            "human_contact_owner": human_contact_owner,
            "human_contact_mode": human_contact_mode,
            "human_contact_block_reason": human_contact_block_reason,
            "next_required_action": next_required_action,
            "child_dispatch_authority_verdict": authority_verdict,
            "dispatch_allowed": dispatch_allowed,
            "allowed_next_actions": [f"dispatch:{registry_entry['agent']}"] if dispatch_allowed else ["/读取回执"],
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
