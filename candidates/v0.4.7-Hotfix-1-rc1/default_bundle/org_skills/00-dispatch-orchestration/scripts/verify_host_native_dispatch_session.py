#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHELL_CONTROL_TOKENS = ("\n", "\r", ";", "|", ">", "<", "&", "`", "$(")
VALUE_OPTIONS = {"--project-root", "--action", "--receipt-file"}
INLINE_VALUE_OPTIONS = tuple(f"{option}=" for option in VALUE_OPTIONS)
CODEX_OUTPUT_MARKER = "\nOutput:\n"
SAFE_RUNTIME_EXEC_ARGUMENT_KEYS = {"cmd", "workdir", "yield_time_ms", "max_output_tokens"}
RUNTIME_DISPATCH_ALLOWED_KEYS = {
    "ok",
    "action",
    "decision",
    "dispatch_target",
    "prompt_text",
    "fixed_user_reply",
    "host_native_dispatch",
    "authority_host",
    "route_result",
}
HOST_NATIVE_DISPATCH_ALLOWED_KEYS = {
    "dispatch_mechanism",
    "required_tool",
    "agent",
    "project_root",
    "dispatch_prompt_path",
    "dispatch_prompt_absolute_path",
    "dispatch_prompt_sha256",
    "spawn_agent_message",
    "session_evidence_required",
    "root_thread_forbidden",
}


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
    if isinstance(payload, dict):
        return [payload]
    return []


def _item_text(item: dict[str, Any]) -> str:
    if item.get("type") == "message":
        content = item.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "\n".join(parts)
    return ""


def _call_arguments_text(item: dict[str, Any]) -> str:
    arguments = item.get("arguments")
    if isinstance(arguments, str):
        return arguments
    if isinstance(arguments, dict):
        return json.dumps(arguments, ensure_ascii=False)
    return ""


def _call_arguments_payload(item: dict[str, Any]) -> dict[str, Any]:
    arguments = item.get("arguments")
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        try:
            payload = json.loads(arguments)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}
    return {}


def _output_text(item: dict[str, Any]) -> str:
    output = item.get("output")
    return output if isinstance(output, str) else ""


def _runtime_actions_from_command(item: dict[str, Any]) -> set[str]:
    if item.get("type") != "function_call" or item.get("name") != "exec_command":
        return set()
    arguments = _call_arguments_payload(item)
    if set(arguments) - SAFE_RUNTIME_EXEC_ARGUMENT_KEYS:
        return set()
    cmd = arguments.get("cmd")
    if not isinstance(cmd, str):
        return set()
    stripped = cmd.strip()
    if not stripped or any(token in stripped for token in SHELL_CONTROL_TOKENS):
        return set()
    try:
        tokens = shlex.split(stripped, comments=True)
    except ValueError:
        return set()
    tokens = _runtime_command_tokens(tokens)
    if not tokens or len(tokens) < 2 or tokens[:2] != ["ai-team", "runtime"]:
        return set()
    return _actions_from_runtime_tokens(tokens)


def _runtime_command_tokens(tokens: list[str]) -> list[str]:
    return tokens


def _actions_from_runtime_tokens(tokens: list[str]) -> set[str]:
    actions: set[str] = set()
    index = 2
    while index < len(tokens):
        token = tokens[index]
        if token == "--action" and index + 1 < len(tokens):
            value = tokens[index + 1]
            index += 2
        elif token.startswith("--action="):
            value = token.split("=", 1)[1]
            index += 1
        elif token in VALUE_OPTIONS:
            if index + 1 >= len(tokens):
                return set()
            index += 2
            continue
        elif token.startswith(INLINE_VALUE_OPTIONS):
            index += 1
            continue
        else:
            return set()
        if value in {"total_control_entry", "read_receipt"}:
            actions.add(value)
        else:
            return set()
    return actions


def _root_accessed_dispatch_prompt(arguments_text: str, dispatch_prompt_path: str, absolute_path: str | None) -> bool:
    candidate_texts = [arguments_text]
    payload = {}
    try:
        loaded = json.loads(arguments_text)
    except json.JSONDecodeError:
        loaded = {}
    if isinstance(loaded, dict):
        payload = loaded
    cmd = payload.get("cmd")
    if isinstance(cmd, str):
        candidate_texts.append(cmd)
        candidate_texts.append(cmd.replace("'", "").replace('"', ""))
        try:
            tokens = shlex.split(cmd, comments=True)
        except ValueError:
            tokens = []
        if tokens:
            candidate_texts.append(" ".join(tokens))
            candidate_texts.extend(tokens)

    if any(dispatch_prompt_path in text for text in candidate_texts):
        return True
    if absolute_path and any(absolute_path in text for text in candidate_texts):
        return True
    prompt_path = Path(dispatch_prompt_path)
    prompt_name = prompt_path.name
    joined_text = "\n".join(candidate_texts)
    if "dispatch-prompts" in joined_text:
        return True
    if ".ai-team/state" in joined_text:
        return True
    return prompt_name in joined_text and ".ai-team/state" in joined_text


def _agent_aliases(expected_agent: str) -> set[str]:
    aliases = {expected_agent}
    without_prefix = re.sub(r"^\d+[-_]", "", expected_agent).strip()
    if without_prefix:
        aliases.add(without_prefix)
    parts = [part.strip() for part in without_prefix.split("-") if part.strip()]
    aliases.update(parts)
    if parts:
        aliases.add(parts[-1])
        aliases.add(parts[-1].replace("专家", "").strip())
        aliases.add(parts[-1] + "专家")
    return {alias for alias in aliases if alias}


def _contains_child_dispatch_prompt_content(value: Any, expected_agent: str) -> bool:
    markers = (
        "请接管当前派发任务",
        "### Dispatch Contract Block",
        "#### Role Prompt Body",
        f"目标角色为 `{expected_agent}`",
    )
    if isinstance(value, str):
        return any(marker in value for marker in markers)
    if isinstance(value, dict):
        return any(_contains_child_dispatch_prompt_content(item, expected_agent) for item in value.values())
    if isinstance(value, list):
        return any(_contains_child_dispatch_prompt_content(item, expected_agent) for item in value)
    return False


def _message_looks_like_child_roleplay(message_text: str, expected_agent: str) -> bool:
    if "请接管当前派发任务" in message_text:
        return True
    if not any(alias in message_text for alias in _agent_aliases(expected_agent)):
        return False
    roleplay_markers = (
        "我作为",
        "接管",
        "opening",
        "开场",
        "当前 child",
        "当前子",
    )
    return any(marker in message_text for marker in roleplay_markers)


def _codex_exec_stdout(item: dict[str, Any]) -> str:
    text = _output_text(item)
    marker_index = text.find(CODEX_OUTPUT_MARKER)
    if marker_index < 0:
        return ""
    header = text[:marker_index]
    if not header.startswith("Chunk ID: "):
        return ""
    exit_codes = re.findall(r"(?m)^Process exited with code ([0-9]+)$", header)
    if exit_codes != ["0"]:
        return ""
    return text[marker_index + len(CODEX_OUTPUT_MARKER) :]


def _extract_runtime_payload(item: dict[str, Any], *, allowed_actions: set[str]) -> dict[str, Any]:
    stdout = _codex_exec_stdout(item).strip()
    if not stdout:
        return {}
    try:
        output_payload = json.loads(stdout)
    except json.JSONDecodeError:
        return {}
    if isinstance(output_payload, dict) and output_payload.get("action") in allowed_actions:
        return output_payload
    return {}


def _spawn_agent_arguments_valid(arguments_text: str, expected_message: str) -> bool:
    try:
        payload = json.loads(arguments_text)
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict):
        return False
    allowed_keys = {"message", "agent_type", "model", "reasoning_effort", "fork_context"}
    if set(payload) - allowed_keys:
        return False
    if payload.get("message") != expected_message:
        return False
    agent_type = payload.get("agent_type")
    if agent_type not in {None, "worker", "default"}:
        return False
    if "model" in payload and not isinstance(payload.get("model"), str):
        return False
    if "reasoning_effort" in payload and payload.get("reasoning_effort") not in {
        "low",
        "medium",
        "high",
        "xhigh",
    }:
        return False
    if payload.get("fork_context") is True:
        return False
    return payload.get("fork_context") in {None, False}


def _spawn_agent_output_valid(output_text: str) -> bool:
    stripped = output_text.strip()
    if not stripped:
        return False
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict):
        return False
    if "ok" in payload and payload.get("ok") is not True:
        return False
    for failure_key in ("error", "failure", "failed", "exception"):
        if payload.get(failure_key):
            return False
    status = payload.get("status")
    if isinstance(status, str) and status.strip().lower() in {
        "failed",
        "failure",
        "error",
        "cancelled",
        "canceled",
        "denied",
        "rejected",
    }:
        return False
    agent_id = payload.get("agent_id")
    return isinstance(agent_id, str) and bool(agent_id.strip())


def _canonical_spawn_agent_message(*, expected_agent: str, project_root: str, absolute_prompt_path: str) -> str:
    return (
        f"你现在接管 `{expected_agent}`。项目根目录是 `{project_root}`；"
        f"先读取 `{absolute_prompt_path}` 的完整内容，"
        "只按其中的 Dispatch Contract Block 与 Role Prompt Body 执行。"
    )


def _validate_host_dispatch(
    payload: dict[str, Any],
    *,
    expected_agent: str,
) -> tuple[str | None, str | None, str | None, list[str]]:
    errors: list[str] = []
    host_dispatch = payload.get("host_native_dispatch")
    if not isinstance(host_dispatch, dict):
        return None, None, None, [f"missing host_native_dispatch for {expected_agent}"]

    extra_host_keys = sorted(set(host_dispatch) - HOST_NATIVE_DISPATCH_ALLOWED_KEYS)
    if extra_host_keys:
        errors.append(f"host_native_dispatch contains unsupported fields: {', '.join(extra_host_keys)}")
    if _contains_child_dispatch_prompt_content(host_dispatch, expected_agent):
        errors.append("host_native_dispatch contains child dispatch prompt content")
    if host_dispatch.get("dispatch_mechanism") != "codex_spawn_agent":
        errors.append("host_native_dispatch.dispatch_mechanism must be codex_spawn_agent")
    if host_dispatch.get("required_tool") != "spawn_agent":
        errors.append("host_native_dispatch.required_tool must be spawn_agent")
    if host_dispatch.get("agent") != expected_agent:
        errors.append(f"host_native_dispatch.agent must be {expected_agent}")
    project_root = host_dispatch.get("project_root")
    if not isinstance(project_root, str) or not project_root.strip():
        errors.append(f"missing host_native_dispatch.project_root for {expected_agent}")
    dispatch_prompt_sha256 = host_dispatch.get("dispatch_prompt_sha256")
    if not isinstance(dispatch_prompt_sha256, str) or not SHA256_RE.match(dispatch_prompt_sha256.strip()):
        errors.append(f"missing or invalid host_native_dispatch.dispatch_prompt_sha256 for {expected_agent}")
    spawn_agent_message = host_dispatch.get("spawn_agent_message")
    if not isinstance(spawn_agent_message, str) or not spawn_agent_message.strip():
        errors.append(f"missing host_native_dispatch.spawn_agent_message for {expected_agent}")
        spawn_agent_message = None

    prompt_path = host_dispatch.get("dispatch_prompt_path")
    if not isinstance(prompt_path, str) or not prompt_path.strip():
        errors.append(f"missing host_native_dispatch.dispatch_prompt_path for {expected_agent}")
        return None, None, None, errors
    absolute_path = host_dispatch.get("dispatch_prompt_absolute_path")
    if not isinstance(absolute_path, str) or not absolute_path.strip():
        errors.append(f"missing host_native_dispatch.dispatch_prompt_absolute_path for {expected_agent}")
        absolute_path = None
    if isinstance(project_root, str) and project_root.strip() and isinstance(absolute_path, str):
        if not absolute_path.strip().startswith(project_root.strip().rstrip("/") + "/"):
            errors.append(
                "host_native_dispatch.dispatch_prompt_absolute_path must be under "
                f"host_native_dispatch.project_root for {expected_agent}"
            )
    if isinstance(project_root, str) and project_root.strip() and isinstance(absolute_path, str):
        root_path = Path(project_root).expanduser().resolve()
        dispatch_prompt_root = root_path / ".ai-team" / "state" / "dispatch-prompts"
        relative_candidate = (root_path / prompt_path).resolve()
        absolute_candidate = Path(absolute_path).expanduser().resolve()
        canonical_message = _canonical_spawn_agent_message(
            expected_agent=expected_agent,
            project_root=project_root.strip().rstrip("/"),
            absolute_prompt_path=absolute_path.strip(),
        )
        if spawn_agent_message != canonical_message:
            errors.append(
                "host_native_dispatch.spawn_agent_message must be canonical "
                f"host-native spawn_agent message for {expected_agent}"
            )
        if relative_candidate != absolute_candidate:
            errors.append("host_native_dispatch prompt paths must resolve to the same file")
        try:
            absolute_candidate.relative_to(dispatch_prompt_root)
        except ValueError:
            errors.append("host_native_dispatch.dispatch_prompt_path must resolve under .ai-team/state/dispatch-prompts")
        spawn_agent_message = canonical_message
    return (
        prompt_path.strip(),
        absolute_path.strip() if isinstance(absolute_path, str) else None,
        spawn_agent_message.strip() if isinstance(spawn_agent_message, str) else None,
        errors,
    )


def verify(records: list[dict[str, Any]], *, expected_agent: str) -> tuple[bool, list[str]]:
    saw_dispatch_allowed_for_agent = False
    saw_prompt_text_only_dispatch = False
    runtime_call_actions: dict[str, set[str]] = {}
    runtime_call_indices: dict[str, int] = {}
    function_call_ids_seen: dict[str, int] = {}
    function_call_outputs: dict[str, tuple[int, str]] = {}
    function_call_output_items: list[tuple[int, str, str]] = []
    function_call_output_ids_seen: set[str] = set()
    runtime_output_call_ids_seen: set[str] = set()
    spawn_agent_calls: list[tuple[int, str, str]] = []
    non_spawn_calls: list[tuple[int, str]] = []
    assistant_messages: list[tuple[int, str]] = []
    dispatch_evidence: list[tuple[str, int, int, str | None, str | None]] = []
    host_dispatch_errors: list[str] = []
    structural_errors: list[str] = []

    for index, record in enumerate(records):
        for item in _candidate_items(record):
            item_type = item.get("type")
            if item_type == "function_call":
                call_name = item.get("name")
                arguments_text = _call_arguments_text(item)
                call_id = item.get("call_id")
                if not isinstance(call_id, str) or not call_id.strip():
                    structural_errors.append(f"missing function_call call_id for {call_name}")
                    call_id = ""
                elif call_id in function_call_ids_seen:
                    structural_errors.append(f"duplicate function_call call_id: {call_id}")
                else:
                    function_call_ids_seen[call_id] = index
                runtime_actions = _runtime_actions_from_command(item)
                if runtime_actions and call_id:
                    runtime_call_actions[call_id] = runtime_actions
                    runtime_call_indices[call_id] = index
                if call_name == "spawn_agent":
                    if call_id:
                        spawn_agent_calls.append((index, arguments_text, call_id))
                else:
                    non_spawn_calls.append((index, arguments_text))
            elif item_type == "message":
                message_text = _item_text(item)
                if message_text:
                    assistant_messages.append((index, message_text))
            elif item_type == "function_call_output":
                output_text = _output_text(item)
                if '"prompt_text": "' in output_text and "请接管当前派发任务" in output_text:
                    saw_prompt_text_only_dispatch = True
                call_id = item.get("call_id")
                output_call_id = call_id if isinstance(call_id, str) else ""
                function_call_output_items.append((index, output_call_id, output_text))
                if isinstance(call_id, str) and call_id.strip():
                    if call_id in function_call_output_ids_seen:
                        structural_errors.append(f"duplicate function_call_output call_id: {call_id}")
                    else:
                        function_call_output_ids_seen.add(call_id)
                        function_call_outputs[call_id] = (index, output_text)
                if call_id not in runtime_call_actions:
                    continue
                if str(call_id) in runtime_output_call_ids_seen:
                    structural_errors.append(f"duplicate runtime function_call_output call_id: {call_id}")
                    continue
                runtime_output_call_ids_seen.add(str(call_id))
                output_payload = _extract_runtime_payload(item, allowed_actions=runtime_call_actions[str(call_id)])
                if not output_payload:
                    continue
                if (
                    output_payload.get("decision") == "dispatch_allowed"
                    and output_payload.get("dispatch_target") == expected_agent
                ):
                    extra_runtime_keys = sorted(set(output_payload) - RUNTIME_DISPATCH_ALLOWED_KEYS)
                    if extra_runtime_keys:
                        host_dispatch_errors.append(
                            f"runtime dispatch payload contains unsupported fields: {', '.join(extra_runtime_keys)}"
                        )
                    if _contains_child_dispatch_prompt_content(output_payload, expected_agent):
                        host_dispatch_errors.append("runtime dispatch payload contains child dispatch prompt content")
                    if output_payload.get("ok") is not True:
                        host_dispatch_errors.append("runtime dispatch payload ok must be true")
                        continue
                    saw_dispatch_allowed_for_agent = True
                    prompt_text = output_payload.get("prompt_text")
                    if prompt_text is not None:
                        host_dispatch_errors.append("runtime dispatch payload prompt_text must be null")
                        saw_prompt_text_only_dispatch = True
                    prompt_path, absolute_path, spawn_agent_message, errors = _validate_host_dispatch(
                        output_payload,
                        expected_agent=expected_agent,
                    )
                    host_dispatch_errors.extend(errors)
                    if prompt_path is not None:
                        dispatch_evidence.append(
                            (
                                prompt_path,
                                runtime_call_indices.get(str(call_id), index),
                                index,
                                absolute_path,
                                spawn_agent_message,
                            )
                        )

    errors: list[str] = []
    if not saw_dispatch_allowed_for_agent:
        errors.append(f"missing dispatch_allowed runtime output from real ai-team runtime call for {expected_agent}")
    if saw_dispatch_allowed_for_agent and not dispatch_evidence:
        errors.append(f"missing host_native_dispatch.dispatch_prompt_path for {expected_agent}")
    errors.extend(structural_errors)
    errors.extend(host_dispatch_errors)
    if saw_prompt_text_only_dispatch:
        errors.append("prompt_text-only dispatch is not host-native dispatch")
    if not any(expected_agent in arguments_text for _, arguments_text, _ in spawn_agent_calls):
        errors.append(f"missing required spawn_agent function_call for {expected_agent}")
    for (
        dispatch_prompt_path,
        runtime_call_index,
        runtime_output_index,
        absolute_path,
        spawn_agent_message,
    ) in dispatch_evidence:
        def matching_spawn(spawn_index: int, arguments_text: str) -> bool:
            if spawn_index <= runtime_output_index:
                return False
            if expected_agent not in arguments_text or dispatch_prompt_path not in arguments_text:
                return False
            if absolute_path and absolute_path not in arguments_text:
                return False
            if spawn_agent_message and not _spawn_agent_arguments_valid(arguments_text, spawn_agent_message):
                return False
            return True

        spawn_after_runtime = [
            (spawn_index, arguments_text, call_id)
            for spawn_index, arguments_text, call_id in spawn_agent_calls
            if spawn_index > runtime_call_index
        ]
        for spawn_index, arguments_text, _ in spawn_agent_calls:
            if spawn_index >= runtime_call_index:
                continue
            errors.append(
                "spawn_agent function_call before runtime dispatch call "
                f"for {expected_agent}"
            )
        matching_spawn_indices: list[int] = []
        for spawn_index, arguments_text, call_id in spawn_after_runtime:
            if spawn_index <= runtime_output_index:
                errors.append(
                    "spawn_agent function_call before runtime dispatch output "
                    f"for {expected_agent}"
                )
                continue
            if not matching_spawn(spawn_index, arguments_text):
                errors.append(
                    "non-matching spawn_agent function_call after runtime dispatch "
                    f"for {expected_agent}"
                )
                continue
            output = function_call_outputs.get(call_id)
            if output is None:
                errors.append(
                    "missing successful spawn_agent function_call_output "
                    f"for {expected_agent}: {call_id}"
                )
                continue
            output_index, output_text = output
            if output_index <= spawn_index:
                errors.append(
                    "spawn_agent function_call_output must occur after spawn_agent function_call "
                    f"for {expected_agent}: {call_id}"
                )
                continue
            if not _spawn_agent_output_valid(output_text):
                errors.append(
                    "failed or invalid spawn_agent function_call_output "
                    f"for {expected_agent}: {call_id}"
                )
                continue
            matching_spawn_indices.append(spawn_index)
        if len(matching_spawn_indices) > 1:
            errors.append(
                "multiple successful spawn_agent function_call after runtime dispatch "
                f"for {expected_agent}"
            )
        for call_index, arguments_text in non_spawn_calls:
            if call_index < runtime_call_index:
                if _root_accessed_dispatch_prompt(arguments_text, dispatch_prompt_path, absolute_path):
                    errors.append(
                        "root thread accessed dispatch_prompt_path before runtime dispatch "
                        f"for {expected_agent}: {dispatch_prompt_path}"
                    )
            elif runtime_call_index < call_index:
                if _root_accessed_dispatch_prompt(arguments_text, dispatch_prompt_path, absolute_path):
                    errors.append(
                        "root thread accessed dispatch_prompt_path after runtime dispatch "
                        f"for {expected_agent}: {dispatch_prompt_path}"
                    )
                else:
                    errors.append(
                        "root thread executed command after runtime dispatch "
                        f"for {expected_agent}"
                    )
        for output_index, output_call_id, output_text in function_call_output_items:
            if output_call_id in runtime_call_actions:
                continue
            if not _contains_child_dispatch_prompt_content(output_text, expected_agent):
                continue
            if output_index < runtime_call_index:
                errors.append(
                    "root thread observed child dispatch prompt before runtime dispatch "
                    f"for {expected_agent}"
                )
            elif runtime_call_index < output_index:
                errors.append(
                    "root thread observed child dispatch prompt after runtime dispatch "
                    f"for {expected_agent}"
                )
        for message_index, message_text in assistant_messages:
            if message_index < runtime_call_index:
                if _message_looks_like_child_roleplay(message_text, expected_agent):
                    errors.append(
                        "root thread emitted child-like message before runtime dispatch "
                        f"for {expected_agent}"
                    )
            elif runtime_call_index < message_index:
                errors.append(
                    "root thread emitted message after runtime dispatch "
                    f"for {expected_agent}"
                )
        if not matching_spawn_indices:
            errors.append(
                "missing required successful spawn_agent function_call "
                f"for {expected_agent} with dispatch_prompt_path {dispatch_prompt_path}"
            )
            continue
    return not errors, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-jsonl", required=True)
    parser.add_argument("--expected-agent", required=True)
    args = parser.parse_args(argv)

    try:
        records = _json_records(Path(args.session_jsonl))
        ok, errors = verify(records, expected_agent=args.expected_agent)
    except Exception as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2

    payload = {
        "ok": ok,
        "verdict": "host_native_dispatch_verified" if ok else "host_native_dispatch_blocked",
        "expected_agent": args.expected_agent,
        "errors": errors,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
