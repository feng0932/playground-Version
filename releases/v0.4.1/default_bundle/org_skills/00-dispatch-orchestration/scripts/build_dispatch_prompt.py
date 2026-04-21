#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, NoReturn

import yaml


SCRIPT_PATH = Path(__file__).resolve()
BUNDLE_ROOT = SCRIPT_PATH.parents[3]
PUBLISHED_BUNDLE_ROOT = Path("install") / "default_bundle"
RUNTIME_BUNDLE_ROOT = Path(".ai-team") / "runtime" / "default_bundle"
DISPATCH_CONTRACT_REGISTRY_SOURCE = (PUBLISHED_BUNDLE_ROOT / "assets" / "contracts" / "dispatch_contract_registry.json").as_posix()

REQUIRED_HANDOFF_SPEC_KEYS = (
    "label",
    "agent",
    "role_prompt_source",
    "dispatch_instance_id",
    "task_chain_id",
    "task_chain_epoch",
    "writable_targets",
    "allow_direct_user_question",
    "allowed_user_question_scope",
    "input_package",
    "dispatch_intent",
)
FORBIDDEN_HANDOFF_SPEC_KEYS = {
    "message",
    "raw_prompt",
    "manual_payload",
    "summary_only_prompt",
}
SUPPORTED_OPTIONAL_HANDOFF_SPEC_KEYS = {
    "dod",
    "receipt_contract",
    "blocker_scope",
}
EXPECTED_DISPATCH_INTENTS = (
    "install_runtime_check",
    "project_package_initialization",
    "product_source_completion",
    "prototype_admin_canvas_delivery",
    "prototype_mobile_canvas_delivery",
    "prototype_pc_canvas_delivery",
    "gate_review",
    "product_review",
    "prototype_review",
    "reverse_review",
    "cross_role_prereview",
    "test_review",
)


DELIVERY_READINESS_SCOPE_SLICE_DISPATCH_INTENTS = {
    "product_review",
    "prototype_review",
    "reverse_review",
    "test_review",
}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile a canonical dispatch prompt from a handoff spec and the published contract registry."
    )
    parser.add_argument(
        "--handoff-spec",
        required=True,
        help="Path to the structured handoff spec JSON document.",
    )
    return parser.parse_args(argv)


def fail(message: str) -> NoReturn:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def detect_project_root(bundle_root: Path) -> Path:
    if bundle_root.parent.name == "install":
        return bundle_root.parent.parent
    if bundle_root.parent.name == "runtime" and bundle_root.parent.parent.name == ".ai-team":
        return bundle_root.parent.parent.parent
    fail(f"dispatch helper bundle root is not in a supported published/runtime layout: {bundle_root.as_posix()}")


PROJECT_ROOT = detect_project_root(BUNDLE_ROOT)
REGISTRY_PATH = BUNDLE_ROOT / "assets" / "contracts" / "dispatch_contract_registry.json"


def load_json_mapping(path: Path, *, context: str) -> dict[str, Any]:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"{context} could not be read: {path.as_posix()} ({exc})")
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        fail(f"{context} is not valid JSON: {path.as_posix()} ({exc})")
    if not isinstance(payload, dict):
        fail(f"{context} must decode to mapping: {path.as_posix()}")
    return payload


def load_handoff_spec(path: Path) -> dict[str, Any]:
    payload = load_json_mapping(path, context="handoff spec")
    actual_keys = set(payload)
    expected_keys = set(REQUIRED_HANDOFF_SPEC_KEYS) | SUPPORTED_OPTIONAL_HANDOFF_SPEC_KEYS
    extra_keys = sorted(actual_keys - expected_keys)
    missing_keys = sorted(expected_keys - actual_keys)
    missing_optional_keys = sorted(set(SUPPORTED_OPTIONAL_HANDOFF_SPEC_KEYS) & set(missing_keys))
    missing_keys = sorted(set(missing_keys) - set(missing_optional_keys))
    if extra_keys or missing_keys:
        problems: list[str] = []
        if missing_keys:
            problems.append("missing required keys: " + ", ".join(missing_keys))
        if extra_keys:
            problems.append("unexpected top-level key(s): " + ", ".join(extra_keys))
        fail("handoff spec failed closed schema validation: " + "; ".join(problems))

    for forbidden_key in sorted(FORBIDDEN_HANDOFF_SPEC_KEYS):
        if forbidden_key in payload:
            fail(f"handoff spec rejected forbidden manual payload field: {forbidden_key}")

    label = payload["label"]
    agent = payload["agent"]
    role_prompt_source = payload["role_prompt_source"]
    dispatch_instance_id = payload["dispatch_instance_id"]
    task_chain_id = payload["task_chain_id"]
    dispatch_intent = payload["dispatch_intent"]
    allowed_user_question_scope = payload["allowed_user_question_scope"]
    if not isinstance(label, str) or not label.strip():
        fail("handoff spec rejected empty label")
    if not isinstance(agent, str) or not agent.strip():
        fail("handoff spec rejected empty agent")
    if not isinstance(role_prompt_source, str) or not role_prompt_source.strip():
        fail("handoff spec rejected empty role_prompt_source")
    if not isinstance(dispatch_instance_id, str) or not dispatch_instance_id.strip():
        fail("handoff spec rejected empty dispatch_instance_id")
    if not isinstance(task_chain_id, str) or not task_chain_id.strip():
        fail("handoff spec rejected empty task_chain_id")
    if not isinstance(dispatch_intent, str) or not dispatch_intent.strip():
        fail("handoff spec rejected empty dispatch_intent")
    if not label:
        fail("handoff spec rejected empty label")

    task_chain_epoch = payload["task_chain_epoch"]
    if not isinstance(task_chain_epoch, int) or isinstance(task_chain_epoch, bool):
        fail("handoff spec rejected non-integer task_chain_epoch")

    writable_targets = payload["writable_targets"]
    if not isinstance(writable_targets, list):
        fail("handoff spec rejected invalid writable_targets: must be a list of non-empty strings")
    normalized_targets: list[str] = []
    for index, target in enumerate(writable_targets):
        if not isinstance(target, str):
            fail(f"handoff spec rejected invalid writable_targets member at index {index}: must be a string")
        normalized_target = target.strip()
        if not normalized_target:
            fail(f"handoff spec rejected invalid writable_targets member at index {index}: empty value")
        normalized_targets.append(normalized_target)
    if not normalized_targets:
        fail("handoff spec rejected invalid writable_targets: must not be empty")
    payload["writable_targets"] = normalized_targets

    input_package = payload["input_package"]
    if not isinstance(input_package, dict):
        fail("handoff spec rejected invalid input_package: must decode to mapping")

    for optional_key in sorted(SUPPORTED_OPTIONAL_HANDOFF_SPEC_KEYS):
        if optional_key not in payload:
            continue
        if not isinstance(payload[optional_key], dict):
            fail(f"handoff spec rejected invalid {optional_key}: must decode to mapping")

    allow_direct_user_question = payload["allow_direct_user_question"]
    if not isinstance(allow_direct_user_question, bool):
        fail("handoff spec rejected non-boolean allow_direct_user_question")
    if not isinstance(allowed_user_question_scope, str):
        fail("handoff spec rejected non-string allowed_user_question_scope")
    allowed_user_question_scope = allowed_user_question_scope.strip()
    if allow_direct_user_question:
        if not allowed_user_question_scope or allowed_user_question_scope == "none":
            fail("handoff spec rejected invalid allowed_user_question_scope for allow_direct_user_question=true")
    else:
        if allowed_user_question_scope != "none":
            fail("handoff spec rejected invalid allowed_user_question_scope for allow_direct_user_question=false")

    role_prompt_path = resolve_role_prompt_source(role_prompt_source)
    if not role_prompt_path.exists():
        fail(f"role_prompt_source does not exist: {role_prompt_source}")

    payload["role_prompt_source"] = role_prompt_source
    payload["allow_direct_user_question"] = allow_direct_user_question
    payload["allowed_user_question_scope"] = allowed_user_question_scope
    return payload


def resolve_role_prompt_source(role_prompt_source: str) -> Path:
    path = Path(role_prompt_source)
    published_prefix = PUBLISHED_BUNDLE_ROOT.as_posix()
    runtime_prefix = RUNTIME_BUNDLE_ROOT.as_posix()
    if not path.is_absolute():
        if role_prompt_source == published_prefix or role_prompt_source.startswith(f"{published_prefix}/"):
            relative = Path(role_prompt_source[len(published_prefix) :].lstrip("/"))
            path = BUNDLE_ROOT / relative
        elif role_prompt_source == runtime_prefix or role_prompt_source.startswith(f"{runtime_prefix}/"):
            path = PROJECT_ROOT / Path(role_prompt_source)
        else:
            path = PROJECT_ROOT / path
    try:
        resolved = path.resolve()
    except OSError as exc:
        fail(f"role_prompt_source could not be resolved: {role_prompt_source} ({exc})")
    allowed_roots = {PROJECT_ROOT.resolve(), BUNDLE_ROOT.resolve()}
    if not any(_is_within_root(resolved, root) for root in allowed_roots):
        fail(f"role_prompt_source must stay within project or bundle root: {role_prompt_source}")
    return resolved


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def split_frontmatter(text: str, source: Path) -> tuple[dict[str, Any], str]:
    match = re.match(r"^---\n(.*?)\n---\n?", text, re.DOTALL)
    if not match:
        fail(f"frontmatter parse failure in role prompt source: {source.as_posix()}")
    frontmatter_text = match.group(1)
    try:
        frontmatter_payload = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError as exc:
        fail(f"frontmatter parse failure in role prompt source: {source.as_posix()} ({exc})")
    if not isinstance(frontmatter_payload, dict):
        fail(f"frontmatter parse failure in role prompt source: {source.as_posix()}")
    body = text[match.end() :]
    if not body.strip():
        fail(f"role prompt body is empty: {source.as_posix()}")
    return frontmatter_payload, body


def load_role_prompt_body(role_prompt_path: Path) -> tuple[dict[str, Any], str]:
    try:
        text = role_prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"role_prompt_source could not be read: {role_prompt_path.as_posix()} ({exc})")
    return split_frontmatter(text, role_prompt_path)


def load_registry() -> dict[str, Any]:
    payload = load_json_mapping(REGISTRY_PATH, context="dispatch contract registry")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        fail("dispatch contract registry must provide `entries` list")
    if len(entries) != len(EXPECTED_DISPATCH_INTENTS):
        fail("dispatch contract registry must contain exactly twelve entries")

    actual_intents: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            fail(f"registry entry[{index}] must decode to mapping")
        for required_key in ("dispatch_intent", "agent", "role_prompt_source", "dod", "receipt_contract", "blocker_scope"):
            value = entry.get(required_key)
            if str(value).strip() == "":
                fail(f"registry entry[{index}] missing required key: {required_key}")
        dispatch_intent = str(entry["dispatch_intent"]).strip()
        agent = str(entry["agent"]).strip()
        role_prompt_source = str(entry["role_prompt_source"]).strip()
        if Path(role_prompt_source).name.removesuffix(".agent.md") != agent:
            fail(f"registry entry[{index}] agent/role_prompt_source basename mismatch")
        actual_intents.append(dispatch_intent)

    actual_intent_set = set(actual_intents)
    expected_intent_set = set(EXPECTED_DISPATCH_INTENTS)
    if actual_intent_set != expected_intent_set:
        missing = sorted(expected_intent_set - actual_intent_set)
        extra = sorted(actual_intent_set - expected_intent_set)
        problems: list[str] = []
        if missing:
            problems.append("missing intents: " + ", ".join(missing))
        if extra:
            problems.append("unexpected intents: " + ", ".join(extra))
        fail("dispatch contract registry intent keyspace mismatch: " + "; ".join(problems))

    duplicate_intents = sorted(intent for intent in expected_intent_set if actual_intents.count(intent) != 1)
    if duplicate_intents:
        fail("dispatch contract registry intent keyspace must be exact singleton set: " + ", ".join(duplicate_intents))

    return payload


def find_registry_entry(registry_payload: dict[str, Any], dispatch_intent: str) -> dict[str, Any]:
    entries = registry_payload.get("entries")
    if not isinstance(entries, list):
        fail("dispatch contract registry must provide `entries` list")
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            fail(f"registry entry[{index}] must decode to mapping")
        if str(entry.get("dispatch_intent", "")).strip() != dispatch_intent:
            continue
        for required_key in ("dod", "receipt_contract", "blocker_scope"):
            if str(entry.get(required_key, "")).strip() == "":
                fail(f"registry entry missing required key: {required_key}")
        return entry
    fail(f"dispatch_intent has no registry entry: {dispatch_intent}")


def validate_registry_owned_contract_fields(
    handoff_spec: dict[str, Any],
    registry_entry: dict[str, Any],
) -> None:
    for key in sorted(SUPPORTED_OPTIONAL_HANDOFF_SPEC_KEYS):
        if key not in handoff_spec:
            continue
        if handoff_spec[key] != registry_entry[key]:
            fail(f"handoff spec conflicts with registry-owned field: {key}")


def canonical_role_prompt_body(role_prompt_path: Path) -> tuple[dict[str, Any], str, bytes, str]:
    frontmatter, body = load_role_prompt_body(role_prompt_path)
    body_bytes = body.encode("utf-8")
    body_sha = hashlib.sha256(body_bytes).hexdigest()
    return frontmatter, body, body_bytes, body_sha


def build_dispatch_contract_block(
    handoff_spec: dict[str, Any],
    registry_entry: dict[str, Any],
    role_prompt_sha256: str,
) -> str:
    contract_block: dict[str, Any] = {
        "dispatch_schema_version": 1,
        "dispatch_instance_id": handoff_spec["dispatch_instance_id"],
        "task_chain_id": handoff_spec["task_chain_id"],
        "task_chain_epoch": handoff_spec["task_chain_epoch"],
        "agent": handoff_spec["agent"],
        "dispatch_intent": handoff_spec["dispatch_intent"],
        "role_prompt_source": handoff_spec["role_prompt_source"],
        "role_prompt_sha256": role_prompt_sha256,
        "writable_targets": handoff_spec["writable_targets"],
        "allow_direct_user_question": handoff_spec["allow_direct_user_question"],
        "allowed_user_question_scope": handoff_spec["allowed_user_question_scope"],
        "input_package": handoff_spec["input_package"],
        "dod": registry_entry["dod"],
        "receipt_contract": registry_entry["receipt_contract"],
        "blocker_scope": registry_entry["blocker_scope"],
    }
    dispatch_intent = str(handoff_spec.get("dispatch_intent", "")).strip()
    input_package = handoff_spec.get("input_package")
    review_scope = ""
    if isinstance(input_package, dict):
        review_scope = str(input_package.get("review_scope", "")).strip()

    if "scope_matrix" in registry_entry:
        if dispatch_intent in DELIVERY_READINESS_SCOPE_SLICE_DISPATCH_INTENTS and review_scope == "delivery_readiness":
            scope_matrix = registry_entry.get("scope_matrix")
            if not isinstance(scope_matrix, dict):
                fail(f"registry entry {dispatch_intent} scope_matrix must decode to mapping")
            scope_specific_slice = scope_matrix.get("delivery_readiness")
            if not isinstance(scope_specific_slice, dict):
                fail(f"registry entry {dispatch_intent} must publish delivery_readiness scope contract slice")
            contract_block["scope_specific_contract_slice"] = scope_specific_slice
        else:
            contract_block["scope_matrix"] = registry_entry["scope_matrix"]

    if dispatch_intent == "cross_role_prereview" and "issue_ticket_contract" in registry_entry:
        issue_ticket_contract = registry_entry.get("issue_ticket_contract")
        if not isinstance(issue_ticket_contract, dict):
            fail("registry entry cross_role_prereview issue_ticket_contract must decode to mapping")
        contract_block["issue_ticket_contract"] = issue_ticket_contract
    yaml_block = yaml.safe_dump(contract_block, allow_unicode=True, sort_keys=False).rstrip()
    return f"### Dispatch Contract Block\n```yaml\n{yaml_block}\n```"


def build_dispatch_prompt(
    handoff_spec: dict[str, Any],
    registry_entry: dict[str, Any],
    role_prompt_body: str,
    role_prompt_sha256: str,
    role_prompt_bytes: int,
) -> str:
    contract_block = build_dispatch_contract_block(handoff_spec, registry_entry, role_prompt_sha256)
    return "\n".join(
        [
            f"请接管当前派发任务，目标角色为 `{handoff_spec['agent']}`。",
            "你必须先读取下方 `Dispatch Contract Block` 与 raw `Role Prompt Body` carrier；若 authority 缺字段、raw payload 不可解析或写入目标不清，直接 `blocked` 并返回总控。",
            contract_block,
            "#### Role Prompt Body",
            f"<<<ROLE_PROMPT_BODY sha256={role_prompt_sha256} bytes={role_prompt_bytes}>>>",
            role_prompt_body,
            f"<<<END_ROLE_PROMPT_BODY sha256={role_prompt_sha256}>>>",
        ]
    )


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    handoff_spec_path = Path(args.handoff_spec).expanduser()
    if not handoff_spec_path.exists():
        fail(f"handoff spec does not exist: {handoff_spec_path.as_posix()}")

    handoff_spec = load_handoff_spec(handoff_spec_path)
    registry_payload = load_registry()
    registry_entry = find_registry_entry(registry_payload, str(handoff_spec["dispatch_intent"]))

    role_prompt_path = resolve_role_prompt_source(str(handoff_spec["role_prompt_source"]))
    validate_registry_owned_contract_fields(
        handoff_spec,
        registry_entry,
    )
    _, role_prompt_body, role_prompt_bytes_data, role_prompt_sha256 = canonical_role_prompt_body(role_prompt_path)

    expected_agent = Path(str(handoff_spec["role_prompt_source"])).name.removesuffix(".agent.md")
    if str(handoff_spec["agent"]).strip() != expected_agent:
        fail(
            "agent / role_prompt_source mismatch: "
            f"agent={handoff_spec['agent']} role_prompt_source={handoff_spec['role_prompt_source']}"
        )

    if str(registry_entry["agent"]).strip() != str(handoff_spec["agent"]).strip():
        fail(
            "agent / role_prompt_source mismatch: "
            f"agent={handoff_spec['agent']} role_prompt_source={handoff_spec['role_prompt_source']}"
        )

    registry_role_prompt_source = str(registry_entry["role_prompt_source"]).strip()
    registry_role_prompt_path = resolve_role_prompt_source(registry_role_prompt_source)
    if registry_role_prompt_path != role_prompt_path:
        fail(
            "role_prompt_source mismatch between handoff spec and registry entry: "
            f"{handoff_spec['role_prompt_source']}"
        )

    dispatch_prompt = build_dispatch_prompt(
        handoff_spec=handoff_spec,
        registry_entry=registry_entry,
        role_prompt_body=role_prompt_body,
        role_prompt_sha256=role_prompt_sha256,
        role_prompt_bytes=len(role_prompt_bytes_data),
    )
    output_payload = {
        "agent": handoff_spec["agent"],
        "dispatch_intent": handoff_spec["dispatch_intent"],
        "dispatch_prompt": dispatch_prompt,
        "role_prompt_source": handoff_spec["role_prompt_source"],
        "role_prompt_sha256": role_prompt_sha256,
        "role_prompt_bytes": len(role_prompt_bytes_data),
        "dispatch_contract_registry_source": DISPATCH_CONTRACT_REGISTRY_SOURCE,
        "handoff_spec_path": args.handoff_spec,
        "dispatch_instance_id": handoff_spec["dispatch_instance_id"],
        "task_chain_id": handoff_spec["task_chain_id"],
        "task_chain_epoch": handoff_spec["task_chain_epoch"],
    }
    json.dump(output_payload, sys.stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
