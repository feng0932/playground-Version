#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


BASE_ARTIFACT_RULES = {
    "engineering_handoff_checklist": {
        "required": lambda _scope: True,
        "allow_na": lambda _scope: False,
    },
    "unresolved_issue_ledger": {
        "required": lambda _scope: True,
        "allow_na": lambda _scope: False,
    },
    "qa_truth_source": {
        "required": lambda _scope: True,
        "allow_na": lambda _scope: False,
    },
    "be_truth_source": {
        "required": lambda scope: bool(scope.get("requires_backend")),
        "allow_na": lambda scope: not bool(scope.get("requires_backend")),
    },
    "fe_truth_source": {
        "required": lambda scope: bool(scope.get("has_ui")),
        "allow_na": lambda scope: not bool(scope.get("has_ui")),
    },
    "dba_truth_source": {
        "required": lambda scope: bool(scope.get("affects_persistence")),
        "allow_na": lambda scope: not bool(scope.get("affects_persistence")),
    },
    "ops_truth_source": {
        "required": lambda scope: bool(scope.get("has_operational_risk")),
        "allow_na": lambda scope: not bool(scope.get("has_operational_risk")),
    },
}

TRIGGER_RULES = {
    "async_task": ("pm_module_diagram", "state_flow_diagram", "timeout_policy", "retry_or_compensation_policy"),
    "delete_or_retention": ("lifecycle_matrix", "retention_rule", "cleanup_owner"),
    "dynamic_permission": ("role_matrix", "data_scope_rule", "audit_rule"),
    "dynamic_config": ("effective_rule", "inflight_policy", "rollback_rule"),
    "publish_or_offline": ("pm_module_diagram", "publish_state_flow", "block_type_mapping", "repair_page_mapping"),
    "cross_page_recovery": ("pm_module_diagram", "recovery_flow_or_state_diagram"),
    "privacy_request_or_complaint": ("pm_module_diagram", "request_state_flow", "sla_rule", "pause_resume_rule", "result_feedback_rule"),
    "branching_mainline_ge_3": ("pm_module_diagram",),
    "formal_status_count_ge_4": ("pm_module_diagram", "status_transition_diagram"),
}

COMMON_METADATA = (
    ("Owner", r"Owner:\s*`([^`]+)`"),
    ("Status", r"Status:\s*`([^`]+)`"),
    ("Version", r"Version:\s*`([^`]+)`"),
    ("Linked PRD", r"Linked PRD:\s*`([^`]+)`"),
)

SEMANTIC_PROFILE_REQUIREMENTS = {
    "engineering_handoff_checklist": ["module_id", "engineering_handoff_ready", "required_supporting_docs"],
    "unresolved_issue_ledger": ["blocker", "owner", "status"],
    "role_truth_source": ["truth", "scope", "acceptance"],
    "pm_module_diagram": ["主链", "分支", "结果"],
    "state_flow_diagram": ["state", "transition"],
    "policy_note": ["rule", "condition"],
    "lifecycle_matrix": ["retain", "delete", "archive"],
    "ownership_note": ["owner", "responsible"],
    "role_matrix": ["role", "action", "scope"],
    "data_scope_rule": ["scope", "data"],
    "branch_flow_diagram": ["branch", "flow"],
    "legacy_migration_record": ["legacy", "migration"],
}
KNOWN_REGISTRY_TOP_LEVEL_KEYS = {"approved_repository_scopes", "artifact_registry", "contract_extensions"}

BASE_FIELD_BINDINGS = {
    "unresolved_issue_ledger": {
        "field_name": "unresolved_issue_ledger_ref",
        "owner_map_keys": ("unresolved_issue_ledger", "unresolved_issue_ledger_ref"),
    },
    "fe_truth_source": {
        "field_name": "fe_truth_source_ref_or_na",
        "owner_map_keys": ("fe_truth_source", "fe_truth_source_ref"),
    },
    "be_truth_source": {
        "field_name": "be_truth_source_ref_or_na",
        "owner_map_keys": ("be_truth_source", "be_truth_source_ref"),
    },
    "qa_truth_source": {
        "field_name": "qa_truth_source_ref",
        "owner_map_keys": ("qa_truth_source", "qa_truth_source_ref"),
    },
    "dba_truth_source": {
        "field_name": "dba_truth_source_ref_or_na",
        "owner_map_keys": ("dba_truth_source", "dba_truth_source_ref"),
    },
    "ops_truth_source": {
        "field_name": "ops_truth_source_ref_or_na",
        "owner_map_keys": ("ops_truth_source", "ops_truth_source_ref"),
    },
}

MODULE_LEVEL_INPUT_GLOB = "01-模块执行包/*/04-过程文件/gate-b.input.json"
PROJECT_LEVEL_INPUT_PATH = "00-项目包/04-过程文件/04-全量提交-gate-b.input.json"
DEBUG_FALLBACK_INPUTS = (Path("/tmp/gate-b.json"),)
DEBUG_FALLBACK_ENV = "AI_TEAM_ALLOW_TMP_GATE_B_FALLBACK"
GOVERNANCE_LOG_PATH = Path(".ai-team/state/governance-log.jsonl")
GOVERNANCE_LATEST_PATH = Path(".ai-team/state/governance-latest.json")
EXPECTED_GATE_B_SCHEMA = "submission_status.gate_b_evidence_pack"
AUTHORITATIVE_GATE_B_EXAMPLE_RELATIVE_PATH = Path(
    ".ai-team/runtime/default_bundle/org_skills/03-submission-status-governance/references/gate-b.example.json"
)
MODULE_GREEN_RULE_BASE_FOUR_ONLY = "基础四审全绿（engineering_handoff_required=false）"
MODULE_GREEN_RULE_WITH_GATE_B = "基础四审全绿 + 24-审查-跨角色预审完成 + Gate B green（engineering_handoff_required=true）"
PREREVIEW_24_ARTIFACT_ID = "unresolved_issue_ledger"
PREREVIEW_24_ARTIFACT_LABEL = "unresolved_issue_ledger (24-审查-跨角色预审 prerequisite)"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate standalone Gate B engineering handoff readiness with conditional module-green semantics "
            "(engineering_handoff_required=false -> 基础四审全绿; engineering_handoff_required=true -> 基础四审全绿 + 24 + Gate B)."
        )
    )
    parser.add_argument(
        "--input",
        help="JSON file with module payload and registry inputs. If omitted, repo-persisted Gate B evidence packs are discovered automatically.",
    )
    parser.add_argument(
        "--project-root",
        help="Project root used to resolve artifact paths. Defaults to the inferred project root of --input, or the current working directory.",
    )
    parser.add_argument(
        "--no-sync-status-json",
        action="store_true",
        help="Do not write engineering_handoff_required / engineering_handoff_ready back to 80-完整提交包/00-提交状态.json.",
    )
    return parser.parse_args(argv)


def no_sync_status_json_enabled() -> bool:
    return os.environ.get("AI_TEAM_DEBUG_ALLOW_NO_SYNC_STATUS_JSON") == "1"


def ensure_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def normalize_file_types(values: object) -> list[str]:
    normalized: list[str] = []
    for item in ensure_list(values):
        stripped = item.strip()
        if not stripped:
            continue
        normalized.append(stripped if stripped.startswith(".") else f".{stripped}")
    return normalized


def normalize_registry_entry(entry: dict) -> dict:
    requirements = ensure_list(entry.get("semantic_requirements"))
    if not requirements:
        profile = str(entry.get("semantic_check_profile", "")).strip()
        requirements = SEMANTIC_PROFILE_REQUIREMENTS.get(profile, [])
    return {
        "allowed_path_patterns": ensure_list(entry.get("allowed_path_pattern")),
        "allowed_file_types": normalize_file_types(entry.get("allowed_file_type")),
        "owner_role": str(entry.get("owner_role", "")).strip(),
        "na_policy": str(entry.get("na_policy", "forbidden")).strip(),
        "semantic_requirements": requirements,
    }


def normalize_registry_payload(registry_payload: dict, *, preserve_unknown_top_level_keys: bool = True) -> dict:
    normalized = {
        "approved_repository_scopes": ensure_list(registry_payload.get("approved_repository_scopes")),
        "artifact_registry": {
            artifact_id: normalize_registry_entry(entry) for artifact_id, entry in registry_payload.get("artifact_registry", {}).items()
        },
    }
    contract_extensions = registry_payload.get("contract_extensions")
    if isinstance(contract_extensions, dict):
        normalized["contract_extensions"] = contract_extensions
    elif "contract_extensions" in registry_payload:
        normalized["contract_extensions"] = contract_extensions
    if preserve_unknown_top_level_keys:
        for key, value in registry_payload.items():
            if key in KNOWN_REGISTRY_TOP_LEVEL_KEYS:
                continue
            normalized[key] = value
    return normalized


def preserve_unknown_top_level_registry_keys(registry_payload: dict) -> bool:
    contract_extensions = registry_payload.get("contract_extensions")
    if not isinstance(contract_extensions, dict):
        return False
    return contract_extensions.get("preserve_top_level_unknown_keys") is True


def compare_registry_payloads(input_registry: dict, authoritative_registry: dict) -> dict | None:
    authoritative_normalized = normalize_registry_payload(authoritative_registry)
    if preserve_unknown_top_level_registry_keys(authoritative_normalized):
        input_known = normalize_registry_payload(input_registry, preserve_unknown_top_level_keys=False)
        authoritative_known = normalize_registry_payload(authoritative_registry, preserve_unknown_top_level_keys=False)
        if input_known != authoritative_known:
            return None
        merged = dict(authoritative_normalized)
        for key, value in input_registry.items():
            if key in KNOWN_REGISTRY_TOP_LEVEL_KEYS:
                continue
            merged[key] = value
        return merged

    input_normalized = normalize_registry_payload(input_registry)
    if input_normalized != authoritative_normalized:
        return None
    return input_normalized


def normalize_machine_ref(value: object) -> dict:
    if isinstance(value, dict):
        return {
            "path": str(value.get("path", "")).strip(),
            "na": bool(value.get("na")),
            "rationale": str(value.get("rationale", "")).strip(),
        }
    if value is None:
        return {"path": "", "na": False, "rationale": ""}
    text = str(value).strip()
    return {"path": text, "na": False, "rationale": ""}


def resolve_input_path(input_arg: str | Path | None, project_root: Path) -> Path:
    if input_arg:
        input_path = Path(input_arg).expanduser()
        return input_path if input_path.is_absolute() else (project_root / input_path)

    module_candidates = sorted(project_root.glob(MODULE_LEVEL_INPUT_GLOB))
    if len(module_candidates) == 1:
        return module_candidates[0]

    if len(module_candidates) > 1:
        raise FileNotFoundError(
            "multiple module-level Gate B evidence packs found; use --input to choose one explicitly"
        )

    project_level = project_root / PROJECT_LEVEL_INPUT_PATH
    if project_level.exists():
        return project_level

    if os.environ.get(DEBUG_FALLBACK_ENV) == "1":
        for debug_path in DEBUG_FALLBACK_INPUTS:
            if debug_path.exists():
                return debug_path

    raise FileNotFoundError(
        "no repo-persisted Gate B evidence pack found; expected "
        f"{MODULE_LEVEL_INPUT_GLOB} or {PROJECT_LEVEL_INPUT_PATH}. "
        "Use --input for an explicit file, or set AI_TEAM_ALLOW_TMP_GATE_B_FALLBACK=1 for temporary debug fallback."
    )


def resolve_project_root(project_root_arg: str | Path | None, input_arg: str | Path | None) -> Path:
    if project_root_arg:
        return Path(project_root_arg).expanduser().resolve()
    if not input_arg:
        return Path.cwd().resolve()

    input_path = Path(input_arg).expanduser()
    resolved_input = input_path.resolve() if input_path.is_absolute() else (Path.cwd() / input_path).resolve()
    for candidate in (resolved_input.parent, *resolved_input.parents):
        if (
            (candidate / "80-完整提交包" / "00-提交状态.json").exists()
            or (candidate / "ai-team.lock.json").exists()
            or (candidate / ".ai-team").exists()
            or (candidate / "00-项目包").exists()
            or (candidate / "01-模块执行包").exists()
        ):
            return candidate
    return resolved_input.parent


def _authoritative_gate_b_contract_candidates(project_root: Path) -> list[Path]:
    candidates = [
        project_root / AUTHORITATIVE_GATE_B_EXAMPLE_RELATIVE_PATH,
        Path(__file__).resolve().parents[1] / "references" / "gate-b.example.json",
    ]
    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        normalized = candidate.resolve() if candidate.exists() else candidate
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(candidate)
    return deduped


def load_authoritative_gate_b_contract(project_root: Path) -> dict:
    for candidate in _authoritative_gate_b_contract_candidates(project_root):
        if not candidate.exists():
            continue
        payload = json.loads(candidate.read_text(encoding="utf-8"))
        if payload.get("schema") not in {None, EXPECTED_GATE_B_SCHEMA}:
            raise ValueError(f"unsupported authoritative Gate B schema: {candidate}")
        return payload
    raise FileNotFoundError(
        "missing authoritative Gate B contract snapshot; expected "
        f"{AUTHORITATIVE_GATE_B_EXAMPLE_RELATIVE_PATH.as_posix()} or bundled references/gate-b.example.json"
    )


def _require_matching_version(payload: dict, key: str, expected: str) -> None:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing {key}")
    if value.strip() != expected:
        raise ValueError(f"incompatible {key}: expected {expected}, got {value.strip()}")


def load_input(input_path: Path, project_root: Path) -> tuple[dict, dict]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if payload.get("schema") not in {None, EXPECTED_GATE_B_SCHEMA}:
        raise ValueError("unsupported gate-b evidence pack schema")
    authoritative_payload = load_authoritative_gate_b_contract(project_root)
    authoritative_schema_version = str(authoritative_payload.get("schema_version", "")).strip()
    authoritative_registry_version = str(authoritative_payload.get("registry_version", "")).strip()
    authoritative_linked_rule_version = str(authoritative_payload.get("linked_rule_version", "")).strip()
    if not authoritative_schema_version or not authoritative_registry_version or not authoritative_linked_rule_version:
        raise ValueError("authoritative Gate B contract snapshot is missing version fields")

    _require_matching_version(payload, "schema_version", authoritative_schema_version)
    _require_matching_version(payload, "registry_version", authoritative_registry_version)
    _require_matching_version(payload, "linked_rule_version", authoritative_linked_rule_version)

    input_registry = payload.get("registry")
    if not isinstance(input_registry, dict):
        raise ValueError("missing registry")
    authoritative_registry = authoritative_payload.get("registry")
    if not isinstance(authoritative_registry, dict):
        raise ValueError("authoritative Gate B contract snapshot is missing registry")
    merged_registry = compare_registry_payloads(input_registry, authoritative_registry)
    if merged_registry is None:
        raise ValueError("embedded gate-b registry does not match authoritative bundled contract")

    if "module" not in payload:
        raise ValueError("missing module")
    module_payload = payload.get("module")
    if not isinstance(module_payload, dict):
        raise ValueError("module must be an object")

    return module_payload, merged_registry


def derive_triggers(module_payload: dict) -> list[str]:
    signals = module_payload.get("product_truth_signals", {})
    return sorted(trigger_name for trigger_name, enabled in signals.items() if enabled)


def format_required_artifact_label(artifact_id: str) -> str:
    if artifact_id == PREREVIEW_24_ARTIFACT_ID:
        return PREREVIEW_24_ARTIFACT_LABEL
    return artifact_id


def compute_handoff_required(module_payload: dict, matched_triggers: list[str]) -> bool:
    context = module_payload.get("handoff_context", {})
    scope = module_payload.get("scope", {})
    return bool(
        context.get("engineering_review_requested")
        or scope.get("requires_backend")
        or scope.get("multi_role")
        or matched_triggers
    )


def required_artifacts(scope: dict, matched_triggers: list[str]) -> list[str]:
    required = [artifact_id for artifact_id, rule in BASE_ARTIFACT_RULES.items() if rule["required"](scope)]
    for trigger_name in matched_triggers:
        required.extend(TRIGGER_RULES.get(trigger_name, ()))
    return list(dict.fromkeys(required))


def normalize_relpath(path_text: str) -> str:
    return Path(path_text).as_posix().lstrip("./")


def path_pattern_matches(pattern: str, relpath: str) -> bool:
    if any(token in pattern for token in ("*", "?")):
        regex = re.escape(pattern)
        regex = regex.replace(r"\*\*/", r"(?:.*/)?")
        regex = regex.replace(r"\*\*", r".*")
        regex = regex.replace(r"\*", r"[^/]*")
        regex = regex.replace(r"\?", r"[^/]")
        return re.fullmatch(regex, relpath) is not None
    try:
        return re.fullmatch(pattern, relpath) is not None
    except re.error:
        return False


def check_scope(relpath: str, approved_scopes: list[str], errors: list[str], artifact_id: str) -> None:
    artifact_label = format_required_artifact_label(artifact_id)
    normalized = normalize_relpath(relpath)
    if not any(normalized == scope or normalized.startswith(f"{scope.rstrip('/')}/") for scope in approved_scopes):
        errors.append(f"{artifact_label} outside approved repository scopes: {normalized}")


def check_registry_constraints(relpath: str, registry_entry: dict, errors: list[str], artifact_id: str) -> None:
    artifact_label = format_required_artifact_label(artifact_id)
    normalized = normalize_relpath(relpath)
    actual_suffix = Path(normalized).suffix or "<none>"
    allowed_types = registry_entry["allowed_file_types"]
    if allowed_types and actual_suffix not in allowed_types:
        errors.append(f"{artifact_label} file type mismatch: expected {'/'.join(allowed_types)}, got {actual_suffix}")
    patterns = registry_entry["allowed_path_patterns"]
    if patterns and not any(path_pattern_matches(pattern, normalized) for pattern in patterns):
        errors.append(f"{artifact_label} path pattern mismatch: {normalized}")


def extract_common_metadata(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for label, pattern in COMMON_METADATA:
        match = re.search(pattern, text)
        values[label] = match.group(1).strip() if match and match.group(1).strip() else ""
    return values


def check_common_semantics(text: str, artifact_id: str, registry_entry: dict, errors: list[str]) -> None:
    artifact_label = format_required_artifact_label(artifact_id)
    values = extract_common_metadata(text)
    for label in ("Owner", "Status", "Version", "Linked PRD"):
        if not values[label]:
            errors.append(f"{artifact_label} missing {label} metadata")
    expected_owner = registry_entry.get("owner_role")
    if expected_owner and values["Owner"] and values["Owner"] != expected_owner:
        errors.append(f"{artifact_label} owner metadata mismatch: expected {expected_owner}, got {values['Owner']}")


def check_semantic_profile(text: str, semantic_requirements: list[str], artifact_id: str, errors: list[str]) -> None:
    artifact_label = format_required_artifact_label(artifact_id)
    lowered = text.lower()
    for token in semantic_requirements:
        if token.lower() not in lowered:
            errors.append(f"{artifact_label} missing semantic token '{token}'")


def check_artifact(
    artifact_id: str,
    artifact_ref: dict,
    registry_entry: dict,
    approved_scopes: list[str],
    project_root: Path,
    errors: list[str],
) -> None:
    artifact_label = format_required_artifact_label(artifact_id)
    if artifact_ref.get("na"):
        errors.append(f"artifact declared N/A but was checked as required: {artifact_label}")
        return

    path_text = artifact_ref.get("path", "")
    if not path_text:
        errors.append(f"missing required artifact ref: {artifact_label}")
        return

    check_scope(path_text, approved_scopes, errors, artifact_id)
    check_registry_constraints(path_text, registry_entry, errors, artifact_id)

    artifact_path = project_root / normalize_relpath(path_text)
    if not artifact_path.exists():
        errors.append(f"{artifact_label} file missing on filesystem: {normalize_relpath(path_text)}")
        return

    text = artifact_path.read_text(encoding="utf-8")
    check_common_semantics(text, artifact_id, registry_entry, errors)
    check_semantic_profile(text, registry_entry.get("semantic_requirements", []), artifact_id, errors)


def validate_na(artifact_id: str, artifact_ref: dict | None, registry_entry: dict | None, scope: dict, errors: list[str]) -> bool:
    artifact_label = format_required_artifact_label(artifact_id)
    if not artifact_ref or not artifact_ref.get("na"):
        return False
    if registry_entry is None:
        errors.append(f"missing artifact registry entry: {artifact_label}")
        return True

    registry_allows_na = registry_entry.get("na_policy") in {"allowed", "explicit_justified_na_allowed"}
    base_rule = BASE_ARTIFACT_RULES.get(artifact_id)
    scope_allows_na = bool(base_rule and base_rule["allow_na"](scope))
    rationale = artifact_ref.get("rationale", "").strip()
    if not registry_allows_na or not scope_allows_na or not rationale:
        errors.append(f"illegal N/A for {artifact_label}")
    return True


def sync_machine_fields_into_artifact_refs(module_payload: dict, errors: list[str]) -> dict:
    artifact_refs = dict(module_payload.get("artifact_refs", {}))
    for artifact_id, binding in BASE_FIELD_BINDINGS.items():
        artifact_label = format_required_artifact_label(artifact_id)
        field_name = binding["field_name"]
        if field_name not in module_payload:
            errors.append(f"missing machine field: {field_name}")
            continue

        normalized = normalize_machine_ref(module_payload.get(field_name))
        current_ref = dict(artifact_refs.get(artifact_id, {}))
        if normalized["na"]:
            if current_ref.get("path"):
                errors.append(f"{field_name} conflicts with artifact_refs.{artifact_label}.path")
            artifact_refs[artifact_id] = {"na": True, "rationale": normalized["rationale"]}
            continue

        if not normalized["path"]:
            errors.append(f"empty machine field: {field_name}")
            continue
        if current_ref.get("na"):
            errors.append(f"{field_name} conflicts with artifact_refs.{artifact_label}.na")
            continue
        if current_ref.get("path") and normalize_relpath(current_ref["path"]) != normalize_relpath(normalized["path"]):
            errors.append(f"{field_name} mismatch with artifact_refs.{artifact_label}")
            continue
        artifact_refs[artifact_id] = {"path": normalized["path"]}
    return artifact_refs


def validate_required_supporting_docs(module_payload: dict, required_ids: list[str], errors: list[str]) -> None:
    docs = module_payload.get("required_supporting_docs")
    if not isinstance(docs, list) or not docs:
        errors.append("missing required_supporting_docs")
        return

    documented_ids: set[str] = set()
    for item in docs:
        if not isinstance(item, dict):
            continue
        artifact_id = str(item.get("artifact_id", "")).strip()
        if artifact_id:
            documented_ids.add(artifact_id)

    for artifact_id in required_ids:
        if artifact_id not in documented_ids:
            errors.append(
                f"required_supporting_docs missing artifact_id: {format_required_artifact_label(artifact_id)}"
            )


def validate_owner_map(module_payload: dict, required_ids: list[str], errors: list[str]) -> None:
    owner_map = module_payload.get("artifact_owner_map")
    if not isinstance(owner_map, dict) or not owner_map:
        errors.append("missing or empty artifact_owner_map")
        return

    if "gate_b_result" not in owner_map:
        errors.append("artifact_owner_map missing key: gate_b_result")

    for artifact_id in required_ids:
        binding = BASE_FIELD_BINDINGS.get(artifact_id)
        candidate_keys = binding["owner_map_keys"] if binding else (artifact_id,)
        if not any(key in owner_map for key in candidate_keys):
            errors.append(
                f"artifact_owner_map missing key for {format_required_artifact_label(artifact_id)}"
            )


def evaluate_engineering_handoff(module_payload: dict, registry_payload: dict, project_root: Path | str | None = None) -> dict:
    root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
    errors: list[str] = []
    scope = module_payload.get("scope", {})
    normalized_registry = normalize_registry_payload(registry_payload)
    approved_scopes = normalized_registry.get("approved_repository_scopes", [])
    artifact_registry = normalized_registry.get("artifact_registry", {})

    ready_for_human_review = bool(module_payload.get("ready_for_human_review"))
    if not ready_for_human_review:
        errors.append("ready_for_human_review must be true")

    matched_triggers = derive_triggers(module_payload)
    declared_triggers = sorted(set(module_payload.get("declared_triggers", [])))
    for trigger_name in matched_triggers:
        if trigger_name not in declared_triggers:
            errors.append(f"inferred trigger not declared: {trigger_name}")

    engineering_handoff_required = compute_handoff_required(module_payload, matched_triggers)
    module_green_rule = (
        MODULE_GREEN_RULE_WITH_GATE_B if engineering_handoff_required else MODULE_GREEN_RULE_BASE_FOUR_ONLY
    )
    required_ids = required_artifacts(scope, matched_triggers) if engineering_handoff_required else []
    artifact_refs = sync_machine_fields_into_artifact_refs(module_payload, errors) if engineering_handoff_required else dict(module_payload.get("artifact_refs", {}))

    if engineering_handoff_required:
        validate_required_supporting_docs(module_payload, required_ids, errors)
        validate_owner_map(module_payload, required_ids, errors)

    for artifact_id in required_ids:
        artifact_label = format_required_artifact_label(artifact_id)
        registry_entry = artifact_registry.get(artifact_id)
        if registry_entry is None:
            errors.append(f"missing artifact registry entry: {artifact_label}")
            continue

        artifact_ref = artifact_refs.get(artifact_id)
        if validate_na(artifact_id, artifact_ref, registry_entry, scope, errors):
            continue
        if artifact_ref is None:
            errors.append(f"missing required artifact ref: {artifact_label}")
            continue
        check_artifact(artifact_id, artifact_ref, registry_entry, approved_scopes, root, errors)

    engineering_handoff_ready = ready_for_human_review and engineering_handoff_required and not errors
    if engineering_handoff_required:
        module_green_ready = engineering_handoff_ready
    else:
        module_green_ready = ready_for_human_review and not errors

    return {
        "module_id": module_payload.get("module_id", ""),
        "ready_for_human_review": ready_for_human_review,
        "engineering_handoff_required": engineering_handoff_required,
        "matched_triggers": matched_triggers,
        "required_artifact_ids": required_ids,
        "engineering_handoff_ready": engineering_handoff_ready,
        "module_green_rule": module_green_rule,
        "module_green_ready": module_green_ready,
        "gate_b_blockers": errors,
    }


def sync_status_json(project_root: Path, result: dict) -> bool:
    status_path = project_root / "80-完整提交包/00-提交状态.json"
    if not status_path.exists():
        return False

    payload = json.loads(status_path.read_text(encoding="utf-8"))
    status = payload.setdefault("status", {})
    gates = status.setdefault("gates", {})
    status["engineering_handoff_required"] = bool(result["engineering_handoff_required"])
    status["engineering_handoff_ready"] = bool(result["engineering_handoff_ready"])
    gates["status_synced"] = False
    gates["consistency_check_passed"] = False
    status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def _collect_snapshot_refs(project_root: Path, input_path: Path, module_payload: dict) -> list[Path]:
    refs: list[Path] = [project_root / "80-完整提交包/00-提交状态.json"]
    candidate_paths: list[str] = []

    try:
        candidate_paths.append(input_path.relative_to(project_root).as_posix())
    except ValueError:
        pass

    artifact_refs = module_payload.get("artifact_refs")
    if isinstance(artifact_refs, dict):
        for value in artifact_refs.values():
            if isinstance(value, dict):
                raw_path = value.get("path")
                if isinstance(raw_path, str) and raw_path.strip():
                    candidate_paths.append(raw_path.strip())

    for field_name in (
        "unresolved_issue_ledger_ref",
        "fe_truth_source_ref_or_na",
        "be_truth_source_ref_or_na",
        "qa_truth_source_ref",
        "dba_truth_source_ref_or_na",
        "ops_truth_source_ref_or_na",
    ):
        value = module_payload.get(field_name)
        if isinstance(value, dict):
            raw_path = value.get("path")
            if isinstance(raw_path, str) and raw_path.strip():
                candidate_paths.append(raw_path.strip())

    seen: set[str] = set()
    for raw_path in candidate_paths:
        if raw_path in seen:
            continue
        seen.add(raw_path)
        path = project_root / raw_path
        if path.exists() and path.is_file():
            refs.append(path)
    return refs


def write_governance_event(project_root: Path, *, input_path: Path, module_payload: dict, result: dict) -> None:
    log_path = project_root / GOVERNANCE_LOG_PATH
    latest_path = project_root / GOVERNANCE_LATEST_PATH
    status_path = project_root / "80-完整提交包/00-提交状态.json"
    snapshot_hashes: dict[str, str] = {}
    for target in _collect_snapshot_refs(project_root, input_path, module_payload):
        relative_path = target.relative_to(project_root)
        if target.exists() and target.is_file():
            snapshot_hashes[relative_path.as_posix()] = hashlib.sha256(target.read_bytes()).hexdigest()

    bundle_version = None
    release_tag = None
    runtime_path = project_root / ".ai-team/runtime.json"
    if runtime_path.exists():
        runtime_payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        raw_bundle_version = runtime_payload.get("bundle_version")
        bundle_version = raw_bundle_version if isinstance(raw_bundle_version, str) and raw_bundle_version else None
        raw_release_tag = runtime_payload.get("release_tag")
        release_tag = raw_release_tag if isinstance(raw_release_tag, str) and raw_release_tag else None

    event_scope = "canonical" if result.get("status_json_synced") else "probe"
    latest_eligible = bool(result.get("status_json_synced")) and bool(result.get("engineering_handoff_ready"))
    event = {
        "schema_version": 1,
        "event_type": "gate_b_check",
        "event_scope": event_scope,
        "latest_eligible": latest_eligible,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "bundle_version": bundle_version,
        "release_tag": release_tag,
        "project_root": str(project_root),
        "input_refs": [_relative_or_absolute(input_path, project_root)],
        "output_refs": [status_path.relative_to(project_root).as_posix()] if result.get("status_json_synced") else [],
        "result": "ok" if latest_eligible else "blocked",
        "warnings": [],
        "blockers": list(result.get("gate_b_blockers", [])),
        "written_targets": [status_path.relative_to(project_root).as_posix()] if result.get("status_json_synced") else [],
        "snapshot_hashes": snapshot_hashes,
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    if latest_eligible:
        latest_path.write_text(json.dumps(event, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _relative_or_absolute(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return str(path.resolve())


def fail_closed_result(message: str) -> dict:
    return {
        "result": "blocked",
        "module_id": "",
        "ready_for_human_review": False,
        "engineering_handoff_required": None,
        "matched_triggers": [],
        "required_artifact_ids": [],
        "engineering_handoff_ready": False,
        "module_green_rule": None,
        "module_green_ready": None,
        "gate_b_blockers": [message],
        "status_json_synced": False,
    }


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        if args.no_sync_status_json and not no_sync_status_json_enabled():
            print(
                json.dumps(
                    fail_closed_result(
                        "--no-sync-status-json is debug-only; set AI_TEAM_DEBUG_ALLOW_NO_SYNC_STATUS_JSON=1 to use it"
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 1
        project_root = resolve_project_root(args.project_root, args.input)
        input_path = resolve_input_path(args.input, project_root)
        module_payload, registry_payload = load_input(input_path, project_root)
        result = dict(
            evaluate_engineering_handoff(module_payload, registry_payload, project_root=project_root)
        )
        result["status_json_synced"] = False
        if args.no_sync_status_json:
            result["evaluated_engineering_handoff_ready"] = bool(result.get("engineering_handoff_ready"))
            result["evaluated_module_green_ready"] = bool(result.get("module_green_ready"))
            result["engineering_handoff_ready"] = False
            result["module_green_ready"] = False
            blockers = list(result.get("gate_b_blockers", []))
            blockers.append("status_json sync skipped in debug-only mode")
            result["gate_b_blockers"] = blockers
        else:
            result["status_json_synced"] = sync_status_json(project_root, result)
        write_governance_event(project_root, input_path=input_path, module_payload=module_payload, result=result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.no_sync_status_json:
            return 1
        return 0 if result["engineering_handoff_ready"] else 1
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(json.dumps(fail_closed_result(str(exc)), ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
