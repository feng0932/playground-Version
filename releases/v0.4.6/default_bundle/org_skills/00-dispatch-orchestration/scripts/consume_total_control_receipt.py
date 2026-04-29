#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_NAME = Path(__file__).name
CONTRACT_VERSION = "v0.4.3"
REQUIRED_JOIN_FIELDS = ("dispatch_instance_id", "task_chain_id", "task_chain_epoch")
REQUIRED_REPLAY_FIELDS = (
    "child_thread",
    "current_phase",
    "return_reason",
    "recommended_return_target",
)
PRIMARY_WINDOW_CHILD_THREADS = {
    "01-编排-初始化项目包",
    "10-执行-产品专家",
}
AUTHORITY_REPLAY_RETENTION_FIELD_MAP = {
    "receipt_consumed": "latest_consumed_receipt_consumed",
    "dispatch_instance_id": "latest_consumed_receipt_dispatch_instance_id",
    "task_chain_id": "latest_consumed_receipt_task_chain_id",
    "task_chain_epoch": "latest_consumed_receipt_task_chain_epoch",
    "child_thread": "latest_consumed_receipt_child_thread",
    "current_phase": "latest_consumed_receipt_current_phase",
    "return_reason": "latest_consumed_receipt_return_reason",
    "recommended_return_target": "latest_consumed_receipt_recommended_return_target",
}


class ScriptFailure(Exception):
    def __init__(self, *, exit_code: int, decision: str, errors: list[str], result: dict[str, Any] | None = None) -> None:
        super().__init__("; ".join(errors))
        self.exit_code = exit_code
        self.decision = decision
        self.errors = errors
        self.result = result or {}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Consume a validated total-control receipt without writing carriers.")
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


def validate_join_chain(validated_receipt: dict[str, Any], authority_snapshot: dict[str, Any]) -> None:
    errors: list[str] = []
    for field_name in REQUIRED_JOIN_FIELDS:
        receipt_value = validated_receipt.get(field_name)
        authority_value = authority_snapshot.get(field_name)
        if receipt_value in (None, ""):
            errors.append(f"missing receipt join field: {field_name}")
            continue
        if authority_value in (None, ""):
            errors.append(f"missing authority join field: {field_name}")
            continue
        if receipt_value != authority_value:
            errors.append(f"join field mismatch: {field_name}")
    if errors:
        raise ScriptFailure(exit_code=2, decision="receipt_blocked", errors=errors)


def validate_consumable_receipt(validated_receipt: dict[str, Any]) -> None:
    errors: list[str] = []
    for field_name in REQUIRED_REPLAY_FIELDS:
        value = validated_receipt.get(field_name)
        if value in (None, "") or (isinstance(value, list) and not value):
            errors.append(f"missing replay-required field: {field_name}")
    if validated_receipt.get("child_thread") not in PRIMARY_WINDOW_CHILD_THREADS:
        errors.append("only valid 01/10 primary-window receipts are consumable")
    if errors:
        raise ScriptFailure(exit_code=2, decision="receipt_blocked", errors=errors)


def is_same_join_chain_receipt(validated_receipt: dict[str, Any], latest_status: dict[str, Any]) -> bool:
    return all(
        latest_status.get(field_name) not in (None, "") and latest_status.get(field_name) == validated_receipt.get(field_name)
        for field_name in REQUIRED_JOIN_FIELDS
    )


def build_authority_replay_retention_fields(canonical_consume_result: dict[str, Any]) -> dict[str, Any]:
    return {
        retained_field: canonical_consume_result[source_field]
        for source_field, retained_field in AUTHORITY_REPLAY_RETENTION_FIELD_MAP.items()
        if source_field in canonical_consume_result
    }


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        payload = load_input_payload(Path(args.input_json).expanduser().resolve())
        validated_receipt = require_mapping(payload.get("validated_receipt"), field_name="validated_receipt")
        authority_snapshot = require_mapping(payload.get("authority_snapshot"), field_name="authority_snapshot")
        latest_status = require_mapping(payload.get("latest_receipt_consumption_status", {}), field_name="latest_receipt_consumption_status")
        validate_join_chain(validated_receipt, authority_snapshot)
        validate_consumable_receipt(validated_receipt)
        if latest_status.get("receipt_consumed") is True and is_same_join_chain_receipt(validated_receipt, latest_status):
            return emit(
                ok=True,
                decision="receipt_not_consumed",
                result={
                    "canonical_consume_result": {
                        "receipt_consumed": False,
                        "dispatch_instance_id": validated_receipt["dispatch_instance_id"],
                        "task_chain_id": validated_receipt["task_chain_id"],
                        "task_chain_epoch": validated_receipt["task_chain_epoch"],
                        "stale_reason": "same_join_chain_receipt_already_consumed",
                        "child_thread": validated_receipt["child_thread"],
                    },
                    "authority_writeback_input": {
                        "dispatch_instance_id": validated_receipt["dispatch_instance_id"],
                        "task_chain_id": validated_receipt["task_chain_id"],
                        "task_chain_epoch": validated_receipt["task_chain_epoch"],
                        "previous_receipt_consumption_status": latest_status,
                    },
                },
                errors=[],
                exit_code=0,
            )
        canonical_consume_result = {
            "receipt_consumed": True,
            "dispatch_instance_id": validated_receipt["dispatch_instance_id"],
            "task_chain_id": validated_receipt["task_chain_id"],
            "task_chain_epoch": validated_receipt["task_chain_epoch"],
            "child_thread": validated_receipt["child_thread"],
            "current_phase": validated_receipt["current_phase"],
            "return_reason": validated_receipt["return_reason"],
            "recommended_return_target": validated_receipt["recommended_return_target"],
        }
        authority_writeback_input = {
            "dispatch_instance_id": validated_receipt["dispatch_instance_id"],
            "task_chain_id": validated_receipt["task_chain_id"],
            "task_chain_epoch": validated_receipt["task_chain_epoch"],
            "consumed_receipt": validated_receipt,
            "previous_receipt_consumption_status": latest_status,
            "authority_replay_retention_fields": build_authority_replay_retention_fields(canonical_consume_result),
        }
        return emit(
            ok=True,
            decision="receipt_consumed",
            result={
                "canonical_consume_result": canonical_consume_result,
                "authority_writeback_input": authority_writeback_input,
            },
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
