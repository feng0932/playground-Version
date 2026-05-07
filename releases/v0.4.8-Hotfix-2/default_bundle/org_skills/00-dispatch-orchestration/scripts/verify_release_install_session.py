#!/usr/bin/env python3
from __future__ import annotations

import argparse
import filecmp
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


CODEX_OUTPUT_MARKER = "\nOutput:\n"
RELEASE_HOST = "http://192.168.1.152/yuhua/playground-Version/raw/branch/main"
BLOCKED_INSTALL_TERMS = (
    "checksum mismatch",
    "metadata fetch failure",
    "downgrade block",
)
PLATFORMS = ("macOS", "Windows")
PLATFORM_STAGES = (
    "official_install",
    "project_runtime",
    "doctor",
    "total_control_entry",
    "read_receipt",
)
RELEASE_PATHS = ("fresh_install", "update")
PROJECTION_CATEGORIES = (
    "scripts",
    "agents",
    "contracts_registry",
    "startup",
    "templates",
    "manifest",
)
VERIFIER_NAME = "verify_release_install_session.py"
HUMAN_ENTRY_COMMAND = "/总控 请接管当前项目，并授权派发子agent"
HUMAN_INSTALL_FORBIDDEN_PATTERNS = (
    re.compile(r"https?://", re.I),
    re.compile(r"\b[a-f0-9]{64}\b", re.I),
    re.compile(r"release metadata:", re.I),
    re.compile(r"archive:", re.I),
    re.compile(r"launcher:", re.I),
    re.compile(r"installer_archive_sha256", re.I),
    re.compile(r"bundle_sha256", re.I),
    re.compile(r"prompt_source", re.I),
    re.compile(r"Traceback", re.I),
    re.compile(r"PowerShell.*Exception", re.I),
    re.compile(r"^\s*[{[]", re.M),
)
PROJECT_PACKAGE_FORMAL_TARGETS_PATH = (
    Path(__file__).resolve().parents[3]
    / "assets"
    / "contracts"
    / "project_package_formal_targets.json"
)
SCRIPT_PROJECTION_PATHS = (
    "org_skills/00-dispatch-orchestration/scripts/build_dispatch_prompt.py",
    "org_skills/00-dispatch-orchestration/scripts/consume_total_control_receipt.py",
    "org_skills/00-dispatch-orchestration/scripts/resolve_route_and_window_state.py",
    "org_skills/00-dispatch-orchestration/scripts/runtime_prompt_materialization.py",
    "org_skills/00-dispatch-orchestration/scripts/validate_primary_window_receipt.py",
    "org_skills/00-dispatch-orchestration/scripts/verify_host_native_dispatch_session.py",
    "org_skills/00-dispatch-orchestration/scripts/verify_release_install_session.py",
)


def _json_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid jsonl at line {line_number}: {exc}") from exc
            if isinstance(record, dict):
                records.append(record)
    return records


def _candidate_items(record: dict[str, Any]) -> list[dict[str, Any]]:
    if record.get("type") != "response_item":
        return []
    payload = record.get("payload")
    return [payload] if isinstance(payload, dict) else []


def _item_text(item: dict[str, Any]) -> str:
    if item.get("type") != "message":
        return ""
    content = item.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for part in content:
        if isinstance(part, dict):
            text = part.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts)


def _output_text(item: dict[str, Any]) -> str:
    output = item.get("output")
    return output if isinstance(output, str) else ""


def _command_text(item: dict[str, Any]) -> str:
    item_type = item.get("type")
    if item_type == "shell_command":
        command = item.get("command")
        return command if isinstance(command, str) else ""
    if item_type != "function_call" or item.get("name") != "exec_command":
        return ""
    arguments = item.get("arguments")
    if isinstance(arguments, str):
        try:
            payload = json.loads(arguments)
        except json.JSONDecodeError:
            return arguments
    elif isinstance(arguments, dict):
        payload = arguments
    else:
        return ""
    command = payload.get("cmd") if isinstance(payload, dict) else None
    return command if isinstance(command, str) else ""


def _tool_stdout(output_text: str) -> str:
    marker_index = output_text.find(CODEX_OUTPUT_MARKER)
    if marker_index >= 0:
        return output_text[marker_index + len(CODEX_OUTPUT_MARKER) :]
    marker_index = output_text.find("\nOutput:\n")
    if marker_index >= 0:
        return output_text[marker_index + len("\nOutput:\n") :]
    return output_text


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _has_failed_tool_output(output_text: str) -> bool:
    for pattern in (r"Process exited with code ([0-9]+)", r"Exit code: ([0-9]+)"):
        matches = re.findall(pattern, output_text)
        if any(match != "0" for match in matches):
            return True
    return False


def _has_zero_exit_marker(output_text: str) -> bool:
    for pattern in (r"Process exited with code ([0-9]+)", r"Exit code: ([0-9]+)"):
        if "0" in re.findall(pattern, output_text):
            return True
    return False


def _extract_json_objects(text: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    objects: list[dict[str, Any]] = []
    index = 0
    while True:
        start = text.find("{", index)
        if start < 0:
            break
        try:
            payload, end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            index = start + 1
            continue
        if isinstance(payload, dict):
            objects.append(payload)
        index = start + max(end, 1)
    return objects


def _nested_value(payload: dict[str, Any], *keys: str) -> Any:
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _release_tag(expected_version: str) -> str:
    return f"ai-team-bundle-{expected_version}"


def _release_metadata_url(expected_version: str) -> str:
    tag = _release_tag(expected_version)
    return f"{RELEASE_HOST}/releases/{expected_version}/{tag}.release.json"


def _version_requires_human_install_output(value: str) -> bool:
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)(?:-Hotfix-(\d+))?", value)
    if not match:
        return False
    major, minor, patch = (int(match.group(index)) for index in (1, 2, 3))
    hotfix = int(match.group(4)) if match.group(4) is not None else None
    if (major, minor, patch) > (0, 4, 8):
        return True
    if (major, minor, patch) == (0, 4, 8) and hotfix is not None and hotfix >= 2:
        return True
    return False


def _default_stable_release_json_path() -> Path:
    return Path(__file__).resolve().parents[4] / "stable-release.json"


def _load_expected_bundle_sha256(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"stable release pointer could not be read: {path.as_posix()} ({exc})") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"stable release pointer is not valid JSON: {path.as_posix()} ({exc})") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"stable release pointer must decode to mapping: {path.as_posix()}")
    bundle_sha256 = payload.get("bundle_sha256")
    if not isinstance(bundle_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", bundle_sha256.strip()):
        raise ValueError(f"stable release pointer missing valid bundle_sha256: {path.as_posix()}")
    return bundle_sha256.strip()


def _command_has_official_install(command: str, *, expected_version: str) -> bool:
    normalized = command.replace("\\", "/")
    mac_install = (
        "install-ai-team.sh" in normalized
        and "bash" in normalized
        and f"-- {expected_version}" in normalized
    )
    windows_install = (
        "install-ai-team.ps1" in normalized
        and f"-Version {expected_version}" in normalized
    )
    return mac_install or windows_install


def _mac_official_install_without_pipefail(command: str, *, expected_version: str) -> bool:
    normalized = command.replace("\\", "/")
    install_script_index = normalized.find("install-ai-team.sh")
    if not (
        install_script_index >= 0
        and "bash" in normalized
        and f"-- {expected_version}" in normalized
        and "| tee" in normalized
    ):
        return False
    pipefail_index = normalized.find("set -o pipefail")
    return pipefail_index < 0 or pipefail_index > install_script_index


def _windows_official_install_without_exitcode_guard(command: str, *, expected_version: str) -> bool:
    normalized = command.replace("\\", "/")
    tee_index = command.find("Tee-Object")
    if not (
        "install-ai-team.ps1" in normalized
        and f"-Version {expected_version}" in normalized
        and tee_index >= 0
    ):
        return False
    last_exit_index = command.find("$LASTEXITCODE", tee_index)
    exit_index = command.find("exit $LASTEXITCODE", tee_index)
    return last_exit_index < 0 or exit_index < 0


def _command_has_project_install(command: str) -> bool:
    return "ai-team install --project-root ." in command


def _command_has_doctor(command: str) -> bool:
    return "ai-team doctor --project-root ." in command


def _command_has_runtime(command: str) -> bool:
    return "ai-team runtime --project-root . --action total_control_entry" in command


def _command_has_read_receipt(command: str) -> bool:
    return "ai-team runtime" in command and "--action read_receipt" in command


def _human_install_success_markers(expected_version: str) -> tuple[str, ...]:
    return (
        f"安装完成：ai-team {expected_version} 已接入当前项目。",
        "下一步：在项目根目录打开 Codex，输入：",
        HUMAN_ENTRY_COMMAND,
        "日志：",
    )


def _has_human_install_success(stdout: str, *, expected_version: str) -> bool:
    return all(marker in stdout for marker in _human_install_success_markers(expected_version))


def _legacy_install_success(stdout: str, *, expected_version: str) -> bool:
    return (
        ("installed ai-team launcher" in stdout or "machine launcher installed" in stdout)
        and f"version: {expected_version}" in stdout
    )


def _validate_official_install_stdout(stdout: str, *, expected_version: str) -> list[str]:
    if not _version_requires_human_install_output(expected_version):
        if _legacy_install_success(stdout, expected_version=expected_version) or _has_human_install_success(
            stdout,
            expected_version=expected_version,
        ):
            return []
        return ["missing installed ai-team launcher evidence"]

    errors: list[str] = []
    if not _has_human_install_success(stdout, expected_version=expected_version):
        errors.append("official install output must use human friendly contract")
    for pattern in HUMAN_INSTALL_FORBIDDEN_PATTERNS:
        if pattern.search(stdout):
            errors.append("official install output leaked machine internal details")
            break
    return errors


def _official_install_stdout_ok(stdout: str, *, expected_version: str) -> bool:
    return not _validate_official_install_stdout(stdout, expected_version=expected_version)


def _validate_command_evidence(
    commands_by_call_id: dict[str, str],
    outputs_by_call_id: dict[str, str],
    *,
    expected_version: str,
) -> list[str]:
    requirements = [
        ("official install", "missing official install command evidence", lambda command: _command_has_official_install(command, expected_version=expected_version)),
        ("ai-team install", "missing ai-team install command evidence", _command_has_project_install),
        ("ai-team doctor", "missing ai-team doctor command evidence", _command_has_doctor),
        ("ai-team runtime", "missing ai-team runtime command evidence", _command_has_runtime),
    ]
    errors: list[str] = []
    for command in commands_by_call_id.values():
        if _mac_official_install_without_pipefail(command, expected_version=expected_version):
            errors.append("macOS official install command must enable pipefail before installer pipeline")
        if _windows_official_install_without_exitcode_guard(command, expected_version=expected_version):
            errors.append("Windows official install command must preserve installer exit code after Tee-Object")
    for call_id, command in commands_by_call_id.items():
        if not _command_has_official_install(command, expected_version=expected_version):
            continue
        output_text = outputs_by_call_id.get(call_id, "")
        if not _has_zero_exit_marker(output_text):
            continue
        errors.extend(
            _validate_official_install_stdout(
                _tool_stdout(output_text),
                expected_version=expected_version,
            )
        )
    for label, missing_error, predicate in requirements:
        matching_call_ids = [
            call_id
            for call_id, command in commands_by_call_id.items()
            if predicate(command)
        ]
        if not matching_call_ids:
            errors.append(missing_error)
            continue
        if not any(_has_zero_exit_marker(outputs_by_call_id.get(call_id, "")) for call_id in matching_call_ids):
            errors.append(f"{label} command is missing zero exit-code evidence")
    return errors


def _validate_install_text(combined_stdout: str, *, expected_version: str) -> list[str]:
    errors: list[str] = []
    if _version_requires_human_install_output(expected_version):
        if not _has_human_install_success(combined_stdout, expected_version=expected_version):
            errors.append("missing human friendly official install output")
        lowered = combined_stdout.lower()
        for term in BLOCKED_INSTALL_TERMS:
            if term in lowered:
                errors.append(f"install output contains blocked failure marker: {term}")
        return errors

    has_machine_launcher_evidence = (
        "installed ai-team launcher" in combined_stdout
        or "machine launcher installed" in combined_stdout
    )
    if not has_machine_launcher_evidence:
        errors.append("missing installed ai-team launcher evidence")
    if f"version: {expected_version}" not in combined_stdout:
        errors.append(f"missing installed launcher version evidence: {expected_version}")
    has_release_source_evidence = (
        _release_metadata_url(expected_version) in combined_stdout
        or "project runtime is not installed by this launcher step" in combined_stdout
    )
    if not has_release_source_evidence:
        errors.append("missing release metadata URL evidence")
    has_project_install_evidence = (
        "[ai-team] install: ok" in combined_stdout
        or "安装完成，可以进入方法论" in combined_stdout
    )
    if not has_project_install_evidence:
        errors.append("missing project install ok evidence")
    lowered = combined_stdout.lower()
    for term in BLOCKED_INSTALL_TERMS:
        if term in lowered:
            errors.append(f"install output contains blocked failure marker: {term}")
    return errors


def _validate_bundle_sha256(payloads: list[dict[str, Any]], *, expected_bundle_sha256: str | None) -> list[str]:
    if expected_bundle_sha256 is None:
        return ["missing expected bundle_sha256 gate"]
    observed = [
        str(payload.get("bundle_sha256")).strip()
        for payload in payloads
        if isinstance(payload.get("bundle_sha256"), str) and str(payload.get("bundle_sha256")).strip()
    ]
    if not observed:
        return ["missing bundle_sha256 evidence"]
    mismatches = sorted({value for value in observed if value != expected_bundle_sha256})
    if mismatches:
        return [
            "bundle_sha256 must match expected pointer: "
            f"expected={expected_bundle_sha256} observed={', '.join(mismatches)}"
        ]
    return []


def _validate_doctor_payloads(payloads: list[dict[str, Any]], *, expected_version: str) -> list[str]:
    expected_tag = _release_tag(expected_version)
    doctor_payload = next(
        (
            payload
            for payload in payloads
            if isinstance(payload.get("machine"), dict)
            and (
                "risk_level" in payload
                or isinstance(payload.get("comparison"), dict)
                or isinstance(payload.get("project"), dict)
            )
        ),
        None,
    )
    if doctor_payload is None:
        return ["missing ai-team doctor JSON evidence"]

    checks = [
        (
            _nested_value(doctor_payload, "machine", "launcher_bundle_version"),
            expected_version,
            "doctor machine.launcher_bundle_version",
        ),
        (_nested_value(doctor_payload, "machine", "release_tag"), expected_tag, "doctor machine.release_tag"),
        (_nested_value(doctor_payload, "project", "lock", "bundle_version"), expected_version, "doctor lock bundle_version"),
        (
            _nested_value(doctor_payload, "project", "runtime", "bundle_version"),
            expected_version,
            "doctor runtime bundle_version",
        ),
        (_nested_value(doctor_payload, "comparison", "machine_vs_project"), "same", "doctor machine_vs_project"),
        (doctor_payload.get("risk_level"), "none", "doctor risk_level"),
        (doctor_payload.get("recommended_action"), "safe_to_install", "doctor recommended_action"),
    ]
    errors: list[str] = []
    for actual, expected, label in checks:
        if actual != expected:
            errors.append(f"{label} must be {expected}")
    return errors


def _validate_runtime_payloads(payloads: list[dict[str, Any]]) -> list[str]:
    runtime_payload = next((payload for payload in payloads if payload.get("action") == "total_control_entry"), None)
    if runtime_payload is None:
        return ["missing runtime total_control_entry evidence", "missing runtime host_native_dispatch evidence"]

    errors: list[str] = []
    if runtime_payload.get("decision") != "dispatch_allowed":
        errors.append("runtime decision must be dispatch_allowed")
    if runtime_payload.get("prompt_text") is not None:
        errors.append("runtime prompt_text must be null")
    host_dispatch = runtime_payload.get("host_native_dispatch")
    if not isinstance(host_dispatch, dict):
        errors.append("missing runtime host_native_dispatch evidence")
        return errors
    if host_dispatch.get("required_tool") != "spawn_agent":
        errors.append("runtime host_native_dispatch.required_tool must be spawn_agent")
    if host_dispatch.get("dispatch_mechanism") != "codex_spawn_agent":
        errors.append("runtime host_native_dispatch.dispatch_mechanism must be codex_spawn_agent")
    return errors


def _formal_read_receipt_payload(
    commands_by_call_id: dict[str, str],
    outputs_by_call_id: dict[str, str],
) -> dict[str, Any] | None:
    command, payload = _formal_read_receipt_command_and_payload(commands_by_call_id, outputs_by_call_id)
    del command
    return payload


def _formal_read_receipt_command_and_payload(
    commands_by_call_id: dict[str, str],
    outputs_by_call_id: dict[str, str],
) -> tuple[str | None, dict[str, Any] | None]:
    for call_id, command in commands_by_call_id.items():
        if not _command_has_read_receipt(command):
            continue
        output_text = outputs_by_call_id.get(call_id, "")
        if not _has_zero_exit_marker(output_text):
            continue
        stdout = _tool_stdout(output_text)
        for payload in _extract_json_objects(stdout):
            if payload.get("action") == "read_receipt":
                return command, payload
    return None, None


def _command_platform(command: str) -> str | None:
    normalized = command.replace("\\", "/")
    lowered = command.lower()
    if (
        "install-ai-team.ps1" in normalized
        or "where.exe ai-team" in lowered
        or "powershell" in lowered
        or "$env:" in command
        or "Tee-Object" in command
    ):
        return "Windows"
    if (
        "install-ai-team.sh" in normalized
        or "which ai-team" in lowered
        or "set -o pipefail" in command
        or "export PATH" in command
    ):
        return "macOS"
    return None


def _read_receipt_payload_errors(
    payload: dict[str, Any],
    *,
    expected_version: str,
    expected_bundle_sha256: str,
) -> list[str]:
    errors: list[str] = []
    expected_tag = _release_tag(expected_version)
    checks = [
        (payload.get("ok"), True, "formal read_receipt ok must be true"),
        (payload.get("action"), "read_receipt", "formal read_receipt action must be read_receipt"),
        (payload.get("decision"), "receipt_consumed", "formal read_receipt decision must be receipt_consumed"),
        (payload.get("bundle_version"), expected_version, "formal read_receipt bundle_version mismatch"),
        (payload.get("release_tag"), expected_tag, "formal read_receipt release_tag mismatch"),
        (payload.get("bundle_sha256"), expected_bundle_sha256, "formal read_receipt bundle_sha256 mismatch"),
    ]
    for actual, expected, message in checks:
        if actual != expected:
            errors.append(message)
    for field_name, message in (
        ("project_root", "missing release_full_chain.project_root"),
        ("authority_path", "missing release_full_chain.authority_path"),
        ("next_required_action", "missing formal read_receipt next_required_action evidence"),
    ):
        value = payload.get(field_name)
        if not isinstance(value, str) or not value.strip():
            errors.append(message)
    authority_writeback = payload.get("authority_writeback")
    if not isinstance(authority_writeback, dict):
        errors.append("missing formal read_receipt authority writeback evidence")
    elif authority_writeback.get("ok") is not True:
        errors.append("formal read_receipt authority_writeback.ok must be true")
    return errors


def _platform_stage_evidence(
    *,
    commands_by_call_id: dict[str, str],
    outputs_by_call_id: dict[str, str],
    expected_version: str,
    expected_bundle_sha256: str,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], list[str]]:
    platform_evidence: dict[str, Any] = {}
    read_receipts: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    for platform in PLATFORMS:
        platform_evidence[platform] = {
            "ok": True,
            **{stage: {"ok": False} for stage in PLATFORM_STAGES},
        }

    for call_id, command in commands_by_call_id.items():
        platform = _command_platform(command)
        if platform not in PLATFORMS:
            continue
        output_text = outputs_by_call_id.get(call_id, "")
        if not _has_zero_exit_marker(output_text):
            continue
        stdout = _tool_stdout(output_text)
        payloads = _extract_json_objects(stdout)
        if _command_has_official_install(command, expected_version=expected_version):
            if _official_install_stdout_ok(stdout, expected_version=expected_version):
                platform_evidence[platform]["official_install"] = {"ok": True, "call_id": call_id}
        if _command_has_project_install(command) and (
            "[ai-team] install: ok" in stdout or "安装完成，可以进入方法论" in stdout
        ):
            platform_evidence[platform]["project_runtime"] = {"ok": True, "call_id": call_id}
        if _command_has_doctor(command) and not _validate_doctor_payloads(payloads, expected_version=expected_version):
            platform_evidence[platform]["doctor"] = {"ok": True, "call_id": call_id}
        if _command_has_runtime(command) and not _validate_runtime_payloads(payloads):
            platform_evidence[platform]["total_control_entry"] = {"ok": True, "call_id": call_id}
        if _command_has_read_receipt(command):
            for payload in payloads:
                if payload.get("action") != "read_receipt":
                    continue
                if payload.get("decision") == "dispatch_allowed":
                    continue
                receipt_errors = _read_receipt_payload_errors(
                    payload,
                    expected_version=expected_version,
                    expected_bundle_sha256=expected_bundle_sha256,
                )
                if receipt_errors:
                    errors.extend(receipt_errors)
                    continue
                read_receipts[platform] = payload
                platform_evidence[platform]["read_receipt"] = {"ok": True, "call_id": call_id}
                break

    for platform in PLATFORMS:
        for stage in PLATFORM_STAGES:
            if platform_evidence[platform][stage].get("ok") is not True:
                errors.append(f"missing platform_evidence.{platform}.{stage}")
                platform_evidence[platform]["ok"] = False
    return platform_evidence, read_receipts, errors


def _command_release_path(command: str) -> str | None:
    match = re.search(r"release_path=(fresh_install|update)", command)
    if match:
        return match.group(1)
    if _command_has_official_install(command, expected_version=""):
        return "fresh_install"
    return None


def _command_has_official_install_any_version(command: str) -> bool:
    normalized = command.replace("\\", "/")
    return (
        ("install-ai-team.sh" in normalized and "bash" in normalized)
        or ("install-ai-team.ps1" in normalized and "-Version " in normalized)
    )


def _release_path_for_command(command: str) -> str | None:
    match = re.search(r"release_path=(fresh_install|update)", command)
    if match:
        return match.group(1)
    if _command_has_official_install_any_version(command):
        return "fresh_install"
    return None


def _platform_stage_evidence_by_release_path(
    *,
    commands_by_call_id: dict[str, str],
    outputs_by_call_id: dict[str, str],
    expected_version: str,
    expected_bundle_sha256: str,
) -> tuple[dict[str, Any], list[str]]:
    evidence_by_path: dict[str, Any] = {
        release_path: {
            platform: {
                "ok": True,
                **{stage: {"ok": False} for stage in PLATFORM_STAGES},
            }
            for platform in PLATFORMS
        }
        for release_path in RELEASE_PATHS
    }
    errors: list[str] = []

    for call_id, command in commands_by_call_id.items():
        platform = _command_platform(command)
        release_path = _release_path_for_command(command)
        if platform not in PLATFORMS or release_path not in RELEASE_PATHS:
            continue
        output_text = outputs_by_call_id.get(call_id, "")
        if not _has_zero_exit_marker(output_text):
            continue
        stdout = _tool_stdout(output_text)
        payloads = _extract_json_objects(stdout)
        platform_evidence = evidence_by_path[release_path][platform]
        if _command_has_official_install(command, expected_version=expected_version):
            if _official_install_stdout_ok(stdout, expected_version=expected_version):
                platform_evidence["official_install"] = {"ok": True, "call_id": call_id}
                platform_evidence["official_install_call_id"] = call_id
        if _command_has_project_install(command) and (
            "[ai-team] install: ok" in stdout or "安装完成，可以进入方法论" in stdout
        ):
            platform_evidence["project_runtime"] = {"ok": True, "call_id": call_id}
            platform_evidence["project_runtime_call_id"] = call_id
        if _command_has_doctor(command) and not _validate_doctor_payloads(payloads, expected_version=expected_version):
            platform_evidence["doctor"] = {"ok": True, "call_id": call_id}
            platform_evidence["doctor_call_id"] = call_id
        if _command_has_runtime(command) and not _validate_runtime_payloads(payloads):
            platform_evidence["total_control_entry"] = {"ok": True, "call_id": call_id}
            platform_evidence["total_control_entry_call_id"] = call_id
        if _command_has_read_receipt(command):
            for payload in payloads:
                if payload.get("action") != "read_receipt" or payload.get("decision") == "dispatch_allowed":
                    continue
                receipt_errors = _read_receipt_payload_errors(
                    payload,
                    expected_version=expected_version,
                    expected_bundle_sha256=expected_bundle_sha256,
                )
                if receipt_errors:
                    errors.extend(receipt_errors)
                    continue
                platform_evidence["read_receipt"] = {"ok": True, "call_id": call_id}
                platform_evidence["read_receipt_call_id"] = call_id
                break

    for release_path in RELEASE_PATHS:
        for platform in PLATFORMS:
            platform_evidence = evidence_by_path[release_path][platform]
            for stage in PLATFORM_STAGES:
                if platform_evidence[stage].get("ok") is not True:
                    errors.append(f"missing {release_path}.{platform}.{stage}")
                    platform_evidence["ok"] = False
    return evidence_by_path, errors


def _validate_release_full_chain(
    *,
    commands_by_call_id: dict[str, str],
    outputs_by_call_id: dict[str, str],
    message_texts: list[str],
    expected_version: str,
    expected_bundle_sha256: str,
    bundle_truth_root: Path | None,
    bundle_projection_root: Path | None,
    source_session_jsonl: Path | None,
) -> tuple[list[str], dict[str, Any] | None]:
    errors: list[str] = []
    del message_texts
    platform_evidence, read_receipts, platform_errors = _platform_stage_evidence(
        commands_by_call_id=commands_by_call_id,
        outputs_by_call_id=outputs_by_call_id,
        expected_version=expected_version,
        expected_bundle_sha256=expected_bundle_sha256,
    )
    errors.extend(platform_errors)
    read_receipt_payload = read_receipts.get("macOS") or read_receipts.get("Windows")

    if not read_receipts:
        errors.append("missing formal read_receipt command evidence")
        errors.append("missing formal read_receipt authority writeback evidence")
        errors.append("missing formal read_receipt next_required_action evidence")

    projection_result, projection_errors = _build_projection_consistency(
        bundle_truth_root=bundle_truth_root,
        bundle_projection_root=bundle_projection_root,
    )
    errors.extend(projection_errors)

    if errors or read_receipt_payload is None:
        return errors, None

    authority_writeback = read_receipt_payload.get("authority_writeback")
    project_root = read_receipt_payload.get("project_root")
    authority_path = read_receipt_payload.get("authority_path")
    if not isinstance(project_root, str) or not project_root.strip():
        errors.append("missing release_full_chain.project_root")
    if not isinstance(authority_path, str) or not authority_path.strip():
        errors.append("missing release_full_chain.authority_path")
    if source_session_jsonl is None:
        errors.append("missing release_full_chain.source_session_jsonl")
    if bundle_truth_root is None:
        errors.append("missing release_full_chain.bundle_truth_root")
    if bundle_projection_root is None:
        errors.append("missing release_full_chain.bundle_projection_root")
    if errors:
        return errors, None
    assert source_session_jsonl is not None
    assert bundle_truth_root is not None
    assert bundle_projection_root is not None
    verdict = {
        "schema_version": 1,
        "ok": True,
        "gate_scope": "release_full_chain",
        "verdict": "release_full_chain_verified",
        "verifier_name": VERIFIER_NAME,
        "source_session_jsonl": str(source_session_jsonl.resolve()),
        "source_session_sha256": _sha256_file(source_session_jsonl),
        "bundle_truth_root": str(bundle_truth_root.resolve()),
        "bundle_projection_root": str(bundle_projection_root.resolve()),
        "bundle_version": expected_version,
        "release_tag": _release_tag(expected_version),
        "bundle_sha256": expected_bundle_sha256,
        "project_root": project_root,
        "authority_path": authority_path,
        "read_receipt_output": {
            "ok": True,
            "action": "read_receipt",
            "decision": "receipt_consumed",
            "authority_writeback": authority_writeback,
        },
        "next_required_action": read_receipt_payload.get("next_required_action"),
        "platform_evidence": platform_evidence,
        "projection_consistency": projection_result,
    }
    return [], verdict


def _validate_release_full_chain_v2(
    *,
    records: list[dict[str, Any]],
    commands_by_call_id: dict[str, str],
    outputs_by_call_id: dict[str, str],
    message_texts: list[str],
    expected_version: str,
    expected_bundle_sha256: str,
    bundle_truth_root: Path | None,
    bundle_projection_root: Path | None,
    source_session_jsonl: Path | None,
) -> tuple[list[str], dict[str, Any] | None]:
    errors: list[str] = []
    v1_errors, v1_verdict = _validate_release_full_chain(
        commands_by_call_id=commands_by_call_id,
        outputs_by_call_id=outputs_by_call_id,
        message_texts=message_texts,
        expected_version=expected_version,
        expected_bundle_sha256=expected_bundle_sha256,
        bundle_truth_root=bundle_truth_root,
        bundle_projection_root=bundle_projection_root,
        source_session_jsonl=source_session_jsonl,
    )
    errors.extend(v1_errors)
    if v1_verdict is None:
        return errors, None

    spawn_call, spawn_output_agent_id = _spawn_agent_evidence(records)
    if spawn_call is None:
        errors.append("missing spawn_agent evidence for release_full_chain_v2")
        return errors, None
    spawn_call_id = spawn_call.get("call_id")
    if not isinstance(spawn_call_id, str) or not spawn_call_id.strip():
        errors.append("missing spawn_agent call_id for release_full_chain_v2")
        return errors, None
    if not isinstance(spawn_output_agent_id, str) or not spawn_output_agent_id.strip():
        errors.append("missing spawn_agent output agent_id for release_full_chain_v2")
        return errors, None

    child_session = _marker_path_from_item(spawn_call, "child_session_jsonl")
    dispatch_prompt = _marker_path_from_item(spawn_call, "dispatch_prompt_path")
    before_snapshot = _marker_path_from_item(spawn_call, "project_root_before_snapshot")
    after_snapshot = _marker_path_from_item(spawn_call, "project_root_after_snapshot")
    for label, path in (
        ("child_session_jsonl", child_session),
        ("dispatch_prompt_path", dispatch_prompt),
        ("project_root_before_snapshot", before_snapshot),
        ("project_root_after_snapshot", after_snapshot),
    ):
        if path is None:
            errors.append(f"missing {label} marker for release_full_chain_v2")
        elif not path.is_file():
            errors.append(f"{label} marker must point to readable file")
    if errors:
        return errors, None
    assert child_session is not None
    assert dispatch_prompt is not None
    assert before_snapshot is not None
    assert after_snapshot is not None
    if source_session_jsonl is None:
        errors.append("missing release_full_chain_v2.source_session_jsonl")
        return errors, None

    formal_targets = _load_project_package_formal_targets()
    after_payload = _load_json_object(after_snapshot)
    observed_after_targets = _snapshot_targets(after_payload)
    missing_after_targets = sorted(set(formal_targets) - observed_after_targets)
    declared_missing = after_payload.get("formal_targets_missing")
    if missing_after_targets or (isinstance(declared_missing, list) and declared_missing):
        errors.append("project_root_after_snapshot formal targets missing")
        return errors, None

    read_receipt_command, read_receipt_payload = _formal_read_receipt_command_and_payload(
        commands_by_call_id,
        outputs_by_call_id,
    )
    if read_receipt_command is None or read_receipt_payload is None:
        errors.append("missing formal read_receipt command evidence")
        return errors, None

    release_path_evidence, release_path_errors = _platform_stage_evidence_by_release_path(
        commands_by_call_id=commands_by_call_id,
        outputs_by_call_id=outputs_by_call_id,
        expected_version=expected_version,
        expected_bundle_sha256=expected_bundle_sha256,
    )
    errors.extend(release_path_errors)
    if errors:
        return errors, None

    verdict = {
        "schema_version": 2,
        "ok": True,
        "gate_scope": "release_full_chain_v2",
        "verdict": "release_full_chain_v2_verified",
        "verifier_name": VERIFIER_NAME,
        "source_session_jsonl": str(source_session_jsonl.resolve()),
        "source_session_sha256": _sha256_file(source_session_jsonl),
        "bundle_truth_root": str(Path(str(v1_verdict["bundle_truth_root"])).resolve()),
        "bundle_projection_root": str(Path(str(v1_verdict["bundle_projection_root"])).resolve()),
        "bundle_version": expected_version,
        "release_tag": _release_tag(expected_version),
        "bundle_sha256": expected_bundle_sha256,
        "parent_session_jsonl": str(source_session_jsonl.resolve()),
        "parent_session_sha256": _sha256_file(source_session_jsonl),
        "spawn_agent_call_id": spawn_call_id,
        "child_agent_id": spawn_output_agent_id,
        "child_session_jsonl": str(child_session.resolve()),
        "child_session_sha256": _sha256_file(child_session),
        "dispatch_prompt_path": str(dispatch_prompt.resolve()),
        "dispatch_prompt_sha256": _sha256_file(dispatch_prompt),
        "project_root_before_snapshot": str(before_snapshot.resolve()),
        "project_root_after_snapshot": str(after_snapshot.resolve()),
        "fresh_install": release_path_evidence["fresh_install"],
        "update": release_path_evidence["update"],
        "project_package_initialization": {
            "spawn_agent_call_id": spawn_call_id,
            "child_agent_id": spawn_output_agent_id,
            "formal_targets_written_or_existing": formal_targets,
            "formal_targets_missing": [],
        },
        "read_receipt_command": read_receipt_command,
        "read_receipt_output": {
            "ok": True,
            "action": "read_receipt",
            "decision": "receipt_consumed",
            "authority_writeback": read_receipt_payload.get("authority_writeback"),
        },
        "stdout_linter": {"ok": True},
    }
    return [], verdict


def _extract_marker_value(text: str, marker: str) -> str | None:
    match = re.search(rf"^{re.escape(marker)}=(.+)$", text, flags=re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def _build_projection_consistency(
    *,
    bundle_truth_root: Path | None,
    bundle_projection_root: Path | None,
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    if bundle_truth_root is None:
        errors.append("missing bundle truth root")
    elif not bundle_truth_root.is_dir():
        errors.append(f"bundle truth root is not readable: {bundle_truth_root}")
    if bundle_projection_root is None:
        errors.append("missing bundle projection root")
    elif not bundle_projection_root.is_dir():
        errors.append(f"bundle projection root is not readable: {bundle_projection_root}")
    if errors:
        return None, errors
    assert bundle_truth_root is not None
    assert bundle_projection_root is not None

    try:
        category_paths = _projection_paths_by_category(bundle_truth_root)
    except ValueError as exc:
        return None, [str(exc)]

    result: dict[str, Any] = {"ok": True}
    for category, relative_paths in category_paths.items():
        category_ok = True
        checked_paths: list[str] = []
        for relative_path in relative_paths:
            truth_path = bundle_truth_root / relative_path
            projection_path = bundle_projection_root / relative_path
            checked_paths.append(relative_path)
            if not truth_path.exists() or not projection_path.exists():
                category_ok = False
                errors.append(f"bundle truth projection consistency mismatch: {relative_path}")
                continue
            if truth_path.is_file() and projection_path.is_file():
                if not filecmp.cmp(truth_path, projection_path, shallow=False):
                    category_ok = False
                    errors.append(f"bundle truth projection consistency mismatch: {relative_path}")
            elif truth_path.is_dir() != projection_path.is_dir():
                category_ok = False
                errors.append(f"bundle truth projection consistency mismatch: {relative_path}")
        result[category] = {"ok": category_ok, "checked_paths": checked_paths}
        if not category_ok:
            result["ok"] = False
    return result, errors


def _projection_paths_by_category(bundle_truth_root: Path) -> dict[str, list[str]]:
    manifest_path = bundle_truth_root / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"bundle truth manifest could not be read: {manifest_path} ({exc})") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"bundle truth manifest is invalid JSON: {manifest_path} ({exc})") from exc
    if not isinstance(manifest, dict):
        raise ValueError(f"bundle truth manifest must be an object: {manifest_path}")

    agent_names: list[str] = []
    for key in ("control_plane_agents", "execution_agents", "review_agents"):
        values = manifest.get(key, [])
        if isinstance(values, list):
            agent_names.extend(str(value) for value in values if isinstance(value, str))

    template_names: list[str] = []
    values = manifest.get("template_files", [])
    if isinstance(values, list):
        template_names.extend(str(value) for value in values if isinstance(value, str))

    return {
        "scripts": list(SCRIPT_PROJECTION_PATHS),
        "agents": [f"agents/{name}" for name in agent_names],
        "contracts_registry": ["assets/contracts/dispatch_contract_registry.json"],
        "startup": ["startup/00-编排-总控.startup.txt"],
        "templates": [f"assets/templates/{name}" for name in template_names],
        "manifest": ["manifest.json"],
    }


def _spawn_agent_evidence(records: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str | None]:
    spawn_call: dict[str, Any] | None = None
    for record in records:
        for item in _candidate_items(record):
            if item.get("type") == "function_call" and item.get("name") == "spawn_agent":
                spawn_call = item
                break
        if spawn_call is not None:
            break
    if spawn_call is None:
        return None, None
    call_id = spawn_call.get("call_id")
    if not isinstance(call_id, str):
        return spawn_call, None
    for record in records:
        for item in _candidate_items(record):
            if item.get("type") != "function_call_output" or item.get("call_id") != call_id:
                continue
            output = item.get("output")
            if isinstance(output, dict) and isinstance(output.get("agent_id"), str):
                return spawn_call, output["agent_id"]
            if isinstance(output, str):
                for payload in _extract_json_objects(output):
                    if isinstance(payload.get("agent_id"), str):
                        return spawn_call, payload["agent_id"]
    return spawn_call, None


def _marker_path_from_item(item: dict[str, Any], marker: str) -> Path | None:
    text = json.dumps(item.get("arguments"), ensure_ascii=False)
    match = re.search(rf"{re.escape(marker)}=([^\s\\\"']+)", text)
    if not match:
        return None
    return Path(match.group(1)).expanduser().resolve()


def _load_project_package_formal_targets() -> list[str]:
    payload = json.loads(PROJECT_PACKAGE_FORMAL_TARGETS_PATH.read_text(encoding="utf-8"))
    targets = payload.get("targets")
    if not isinstance(targets, list):
        raise ValueError("project_package_formal_targets.json missing targets")
    project_targets = [
        entry.get("project_target")
        for entry in targets
        if isinstance(entry, dict) and isinstance(entry.get("project_target"), str)
    ]
    if len(project_targets) != 6 or len(set(project_targets)) != 6:
        raise ValueError("project_package_formal_targets.json must define six unique targets")
    return [str(target) for target in project_targets]


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return payload


def _snapshot_targets(payload: dict[str, Any]) -> set[str]:
    targets: set[str] = set()
    explicit_targets = payload.get("formal_targets_written_or_existing")
    if isinstance(explicit_targets, list):
        targets.update(str(target) for target in explicit_targets if isinstance(target, str))
    files = payload.get("files")
    if isinstance(files, list):
        for item in files:
            if isinstance(item, dict) and item.get("exists") is not False and isinstance(item.get("path"), str):
                targets.add(str(item["path"]))
            elif isinstance(item, str):
                targets.add(item)
    return targets


def _standard_summary_markers(expected_version: str) -> list[str]:
    expected_tag = _release_tag(expected_version)
    install_done_marker = (
        "是否真的完成了新安装：是"
        if _version_requires_human_install_output(expected_version)
        else "新安装是否完成：是"
    )
    markers = [
        f"## ai-team {expected_version} 安装现场验收摘要",
        install_done_marker,
        f"实际安装到的 bundle_version / release_tag：{expected_version} / {expected_tag}",
        "machine_vs_project=same",
        "risk_level=none",
        "recommended_action=safe_to_install",
        "prompt_text=null",
        "host_native_dispatch.required_tool=spawn_agent",
        "是否出现 checksum mismatch、metadata fetch failure、downgrade block：否",
        "停止在安装验收，不进入项目业务初始化",
    ]
    if _version_requires_human_install_output(expected_version):
        markers.append("安装主输出是否对人友好：是")
    return markers


def _has_standard_summary(message_texts: list[str], *, expected_version: str) -> bool:
    markers = _standard_summary_markers(expected_version)
    for message_text in message_texts:
        if all(marker in message_text for marker in markers):
            return True
    return False


def verify(
    records: list[dict[str, Any]],
    *,
    expected_version: str,
    expected_bundle_sha256: str | None = None,
    gate_scope: str = "release_full_chain",
    bundle_truth_root: Path | None = None,
    bundle_projection_root: Path | None = None,
    source_session_jsonl: Path | None = None,
) -> tuple[bool, list[str], dict[str, Any] | None]:
    errors: list[str] = []
    tool_outputs: list[str] = []
    message_texts: list[str] = []
    json_payloads: list[dict[str, Any]] = []
    commands_by_call_id: dict[str, str] = {}
    outputs_by_call_id: dict[str, str] = {}
    saw_spawn_agent_call = False

    for record in records:
        for item in _candidate_items(record):
            item_type = item.get("type")
            call_id = item.get("call_id")
            command_text = _command_text(item)
            if command_text and isinstance(call_id, str) and call_id.strip():
                commands_by_call_id[call_id] = command_text
            if item_type == "function_call" and item.get("name") == "spawn_agent":
                saw_spawn_agent_call = True
            if item_type == "function_call_output":
                output_text = _output_text(item)
                if isinstance(call_id, str) and call_id.strip():
                    outputs_by_call_id[call_id] = output_text
                if _has_failed_tool_output(output_text):
                    errors.append("tool output contains non-zero exit code")
                stdout = _tool_stdout(output_text)
                tool_outputs.append(stdout)
                json_payloads.extend(_extract_json_objects(stdout))
            elif item_type == "message":
                message_text = _item_text(item)
                if message_text:
                    message_texts.append(message_text)

    combined_stdout = "\n".join(tool_outputs)
    errors.extend(
        _validate_command_evidence(
            commands_by_call_id,
            outputs_by_call_id,
            expected_version=expected_version,
        )
    )
    errors.extend(_validate_install_text(combined_stdout, expected_version=expected_version))
    errors.extend(_validate_bundle_sha256(json_payloads, expected_bundle_sha256=expected_bundle_sha256))
    errors.extend(_validate_doctor_payloads(json_payloads, expected_version=expected_version))
    errors.extend(_validate_runtime_payloads(json_payloads))
    if not _has_standard_summary(message_texts, expected_version=expected_version):
        errors.append("missing standardized final install summary")
    if saw_spawn_agent_call and gate_scope != "release_full_chain_v2":
        errors.append("install smoke session must not call spawn_agent")

    if gate_scope == "install_smoke":
        return not errors, errors, None
    if gate_scope not in ("release_full_chain", "release_full_chain_v2"):
        errors.append(f"unsupported gate scope: {gate_scope}")
        return False, errors, None
    if expected_bundle_sha256 is None:
        errors.append("missing expected bundle_sha256 gate")
        return False, errors, None

    if gate_scope == "release_full_chain_v2":
        full_chain_errors, verdict = _validate_release_full_chain_v2(
            records=records,
            commands_by_call_id=commands_by_call_id,
            outputs_by_call_id=outputs_by_call_id,
            message_texts=message_texts,
            expected_version=expected_version,
            expected_bundle_sha256=expected_bundle_sha256,
            bundle_truth_root=bundle_truth_root,
            bundle_projection_root=bundle_projection_root,
            source_session_jsonl=source_session_jsonl,
        )
    else:
        full_chain_errors, verdict = _validate_release_full_chain(
            commands_by_call_id=commands_by_call_id,
            outputs_by_call_id=outputs_by_call_id,
            message_texts=message_texts,
            expected_version=expected_version,
            expected_bundle_sha256=expected_bundle_sha256,
            bundle_truth_root=bundle_truth_root,
            bundle_projection_root=bundle_projection_root,
            source_session_jsonl=source_session_jsonl,
        )
    errors.extend(full_chain_errors)
    return not errors, errors, verdict if not errors else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-jsonl", required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--expected-bundle-sha256")
    parser.add_argument(
        "--gate-scope",
        choices=("install_smoke", "release_full_chain", "release_full_chain_v2"),
        default="release_full_chain",
    )
    parser.add_argument("--bundle-truth-root")
    parser.add_argument("--bundle-projection-root")
    parser.add_argument("--write-verdict")
    parser.add_argument(
        "--stable-release-json",
        default=str(_default_stable_release_json_path()),
        help="Stable release pointer used to resolve expected bundle_sha256 when --expected-bundle-sha256 is omitted.",
    )
    args = parser.parse_args(argv)

    try:
        expected_bundle_sha256 = args.expected_bundle_sha256
        if expected_bundle_sha256 is None:
            expected_bundle_sha256 = _load_expected_bundle_sha256(Path(args.stable_release_json).expanduser().resolve())
        session_jsonl = Path(args.session_jsonl).expanduser().resolve()
        records = _json_records(session_jsonl)
        ok, errors, verdict_payload = verify(
            records,
            expected_version=args.expected_version,
            expected_bundle_sha256=expected_bundle_sha256,
            gate_scope=args.gate_scope,
            bundle_truth_root=Path(args.bundle_truth_root).resolve() if args.bundle_truth_root else None,
            bundle_projection_root=Path(args.bundle_projection_root).resolve() if args.bundle_projection_root else None,
            source_session_jsonl=session_jsonl,
        )
    except Exception as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2

    payload = {
        "ok": ok,
        "verdict": (
            "release_install_smoke_verified"
            if ok and args.gate_scope == "install_smoke"
            else "release_full_chain_v2_verified"
            if ok and args.gate_scope == "release_full_chain_v2"
            else "release_full_chain_verified"
            if ok
            else "release_install_session_blocked"
        ),
        "expected_version": args.expected_version,
        "errors": errors,
    }
    if ok and args.gate_scope in ("release_full_chain", "release_full_chain_v2"):
        if verdict_payload is not None:
            payload = verdict_payload
            if args.write_verdict:
                write_path = Path(args.write_verdict).expanduser().resolve()
                write_path.parent.mkdir(parents=True, exist_ok=True)
                write_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
