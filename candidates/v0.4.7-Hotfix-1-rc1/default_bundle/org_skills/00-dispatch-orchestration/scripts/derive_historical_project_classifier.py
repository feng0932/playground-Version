#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_NAME = SCRIPT_PATH.name
CONTRACT_VERSION = "v0.4.6"
PROJECT_ROOT = Path.cwd()
PROJECT_BASELINE_HOSTS = (
    Path("00-项目包") / "01-项目商业说明.md",
    Path("00-项目包") / "02-用户画像与权限架构.md",
    Path("00-项目包") / "03-系统拓扑与核心名词表.md",
    Path("00-项目包") / "05-项目级原型与高保真标准.md",
    Path("00-项目包") / "06-产品级共享资产底座.md",
)
EXECUTION_SKELETON_TARGETS = (
    Path("AGENTS.md"),
    Path("docs") / "00-说明.md",
    Path("docs") / "01-跨模块补充资料" / "README.md",
)


class ScriptFailure(Exception):
    def __init__(self, *, exit_code: int, decision: str, errors: list[str], result: dict[str, Any] | None = None) -> None:
        super().__init__("; ".join(errors))
        self.exit_code = exit_code
        self.decision = decision
        self.errors = errors
        self.result = result or {}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Derive canonical historical-project classifier fields for fresh /总控 reopening.")
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


def load_input_payload(path: Path) -> dict[str, Any]:
    if not path.is_absolute():
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=["--input-json must be an absolute path"])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=[f"input_json could not be read: {exc}"]) from exc
    except json.JSONDecodeError as exc:
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=[f"input_json is not valid JSON: {exc}"]) from exc
    if not isinstance(payload, dict):
        raise ScriptFailure(exit_code=3, decision="schema_error", errors=["input_json must decode to mapping"])
    return payload


def existing_paths(paths: tuple[Path, ...]) -> tuple[list[str], list[str]]:
    present: list[str] = []
    missing: list[str] = []
    for relative_path in paths:
        if (PROJECT_ROOT / relative_path).exists():
            present.append(relative_path.as_posix())
        else:
            missing.append(relative_path.as_posix())
    return present, missing


def derive_authority_patch() -> dict[str, Any]:
    _, missing_baseline_hosts = existing_paths(PROJECT_BASELINE_HOSTS)
    if missing_baseline_hosts:
        return {
            "project_profile": "historical_project",
            "当前状态": "historical_project_repair_required",
            "legacy_project_type": "missing_project_entry_hosts",
            "project_entry_readiness": "blocked",
            "historical_project_classifier_verdict": "blocked",
            "derivation_path_decision": "repair_project_level_entry",
            "minimal_repair_list": ["repair_project_level_entry"],
        }

    _, missing_execution_skeleton = existing_paths(EXECUTION_SKELETON_TARGETS)
    if missing_execution_skeleton:
        return {
            "project_profile": "historical_project",
            "当前状态": "historical_project_repair_required",
            "legacy_project_type": "missing_execution_skeleton",
            "project_entry_readiness": "blocked",
            "historical_project_classifier_verdict": "blocked",
            "derivation_path_decision": "repair_execution_skeleton",
            "minimal_repair_list": ["repair_execution_skeleton"],
        }

    return {
        "project_profile": "historical_project",
        "当前状态": "historical_project_ready_for_10",
        "legacy_project_type": "already_integrated_history_project",
        "project_entry_readiness": "ready",
        "historical_project_classifier_verdict": "allow_10",
        "derivation_path_decision": "keep_existing_execution_skeleton",
        "minimal_repair_list": [],
    }


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        load_input_payload(Path(args.input_json).expanduser().resolve())
        return emit(
            ok=True,
            decision="classifier_derived",
            result={"authority_patch": derive_authority_patch()},
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
