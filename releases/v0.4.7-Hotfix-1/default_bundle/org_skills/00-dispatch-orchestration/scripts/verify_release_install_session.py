#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
    if "installed ai-team launcher" not in combined_stdout:
        errors.append("missing installed ai-team launcher evidence")
    if f"version: {expected_version}" not in combined_stdout:
        errors.append(f"missing installed launcher version evidence: {expected_version}")
    if _release_metadata_url(expected_version) not in combined_stdout:
        errors.append("missing release metadata URL evidence")
    if "[ai-team] install: ok" not in combined_stdout:
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


def _standard_summary_markers(expected_version: str) -> list[str]:
    expected_tag = _release_tag(expected_version)
    return [
        f"## ai-team {expected_version} 安装现场验收摘要",
        "新安装是否完成：是",
        f"实际安装到的 bundle_version / release_tag：{expected_version} / {expected_tag}",
        "machine_vs_project=same",
        "risk_level=none",
        "recommended_action=safe_to_install",
        "prompt_text=null",
        "host_native_dispatch.required_tool=spawn_agent",
        "是否出现 checksum mismatch、metadata fetch failure、downgrade block：否",
        "停止在安装验收，不进入项目业务初始化",
    ]


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
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    tool_outputs: list[str] = []
    message_texts: list[str] = []
    json_payloads: list[dict[str, Any]] = []
    commands_by_call_id: dict[str, str] = {}
    outputs_by_call_id: dict[str, str] = {}

    for record in records:
        for item in _candidate_items(record):
            item_type = item.get("type")
            call_id = item.get("call_id")
            command_text = _command_text(item)
            if command_text and isinstance(call_id, str) and call_id.strip():
                commands_by_call_id[call_id] = command_text
            if item_type == "function_call" and item.get("name") == "spawn_agent":
                errors.append("install smoke session must not call spawn_agent")
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

    return not errors, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-jsonl", required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--expected-bundle-sha256")
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
        records = _json_records(Path(args.session_jsonl))
        ok, errors = verify(
            records,
            expected_version=args.expected_version,
            expected_bundle_sha256=expected_bundle_sha256,
        )
    except Exception as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2

    payload = {
        "ok": ok,
        "verdict": "release_install_session_verified" if ok else "release_install_session_blocked",
        "expected_version": args.expected_version,
        "errors": errors,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
