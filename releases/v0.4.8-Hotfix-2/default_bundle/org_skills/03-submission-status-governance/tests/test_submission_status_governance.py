from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPT = SKILL_ROOT / "scripts" / "sync_submission_status.py"
CHECK_SCRIPT = SKILL_ROOT / "scripts" / "check_submission_consistency.py"
HANDOFF_SCRIPT = SKILL_ROOT / "scripts" / "check_engineering_handoff_readiness.py"
FIXTURE_ROOT = SKILL_ROOT / "tests" / "fixtures"
GATE_B_EXAMPLE_PATH = SKILL_ROOT / "references" / "gate-b.example.json"


def copy_fixture(name: str) -> Path:
    temp_dir = Path(tempfile.mkdtemp())
    destination = temp_dir / "project"
    shutil.copytree(FIXTURE_ROOT / name, destination)
    return destination


class SubmissionStatusGovernanceTests(unittest.TestCase):
    @staticmethod
    def engineering_handoff_contract(module_name: str = "示例模块") -> dict[str, object]:
        return {
            "project_entry": "00-项目包/02-工程交接/README.md",
            "module_entries": [
                {
                    "module_id": module_name,
                    "entry_file": f"01-模块执行包/{module_name}/02-工程交接/README.md",
                    "checklist_file": f"01-模块执行包/{module_name}/04-过程文件/{module_name}-工程交接门槛清单.md",
                }
            ],
            "handoff_audit_globs": [
                "00-项目包/02-工程交接/**/*.md",
                "01-模块执行包/*/02-工程交接/**/*.md",
            ],
            "process_audit_globs": [
                "00-项目包/04-过程文件/**/*.md",
                "01-模块执行包/*/04-过程文件/**/*.md",
            ],
        }

    @staticmethod
    def authoritative_gate_b_contract() -> dict[str, object]:
        payload = json.loads(GATE_B_EXAMPLE_PATH.read_text(encoding="utf-8"))
        return {
            "schema": payload["schema"],
            "schema_version": payload["schema_version"],
            "registry_version": payload["registry_version"],
            "linked_rule_version": payload["linked_rule_version"],
            "registry": payload["registry"],
        }

    @staticmethod
    def write_doc(root: Path, relative_path: str, owner: str, semantic_lines: list[str]) -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                [
                    f"Owner: `{owner}`",
                    "Status: `active`",
                    "Version: `v1`",
                    "Linked PRD: `01-模块执行包/示例模块/01-PRD/示例-PRD.md`",
                    "",
                    *semantic_lines,
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def append_lines(path: Path, extra_lines: list[str]) -> None:
        path.write_text(
            path.read_text(encoding="utf-8").rstrip() + "\n\n" + "\n".join(extra_lines) + "\n",
            encoding="utf-8",
        )

    def seed_gate_b_ready_project(self, project_root: Path) -> Path:
        status_path = project_root / "80-完整提交包" / "00-提交状态.json"
        payload = json.loads(status_path.read_text(encoding="utf-8"))
        payload["artifacts"]["engineering_handoff"] = self.engineering_handoff_contract()
        status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        self.write_doc(
            project_root,
            "00-项目包/02-工程交接/README.md",
            "总控",
            ["truth: project handoff index", "scope: engineering handoff", "acceptance: outward artifact listed"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/README.md",
            "总控",
            ["truth: handoff index", "scope: engineering handoff", "acceptance: outward artifact listed"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/04-过程文件/示例模块-工程交接门槛清单.md",
            "总控",
            ["module_id: 示例模块", "engineering_handoff_ready: true", "required_supporting_docs: listed"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/04-过程文件/示例模块-跨角色预审讨论清单.md",
            "总控",
            ["blocker: none", "owner: 总控", "status: cleared"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/fe_module.md",
            "FE",
            ["truth: fe flow", "scope: frontend", "acceptance: ready"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/be_module.md",
            "BE",
            ["truth: be flow", "scope: backend", "acceptance: ready"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/qa_module.md",
            "QA",
            ["truth: qa plan", "scope: validation", "acceptance: ready"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/01-PRD/示例模块-模块图.md",
            "PM",
            ["主链: 提交任务 -> 等待回调 -> 返回结果", "分支: 超时转人工", "结果: 成功/失败/转人工"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/async-state-diagram.md",
            "BE",
            ["state: pending", "transition: pending -> succeeded"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/async-timeout-policy.md",
            "BE",
            ["rule: timeout after 30m", "condition: third-party no callback"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/async-retry-policy.md",
            "BE",
            ["rule: retry up to 3 times", "condition: idempotent failure only"],
        )

        gate_b_contract = self.authoritative_gate_b_contract()
        gate_b_input = {
            "schema": gate_b_contract["schema"],
            "schema_version": gate_b_contract["schema_version"],
            "registry_version": gate_b_contract["registry_version"],
            "linked_rule_version": gate_b_contract["linked_rule_version"],
            "module": {
                "module_id": "示例模块",
                "ready_for_human_review": True,
                "handoff_context": {"engineering_review_requested": True},
                "scope": {
                    "has_ui": True,
                    "requires_backend": True,
                    "multi_role": False,
                    "affects_persistence": False,
                    "has_operational_risk": False,
                },
                "declared_triggers": ["async_task"],
                "product_truth_signals": {"async_task": True},
                "artifact_owner_map": {
                    "engineering_handoff_checklist": {"总控": "R/A/G"},
                    "unresolved_issue_ledger_ref": {"总控": "R/A/G"},
                    "fe_truth_source_ref": {"FE": "R/A", "总控": "G"},
                    "be_truth_source_ref": {"BE": "R/A", "总控": "G"},
                    "qa_truth_source_ref": {"QA": "R/A", "总控": "G"},
                    "pm_module_diagram": {"PM": "R/A", "总控": "G"},
                    "state_flow_diagram": {"BE": "R/A", "总控": "G"},
                    "timeout_policy": {"BE": "R/A", "总控": "G"},
                    "retry_or_compensation_policy": {"BE": "R/A", "总控": "G"},
                    "gate_b_result": {"总控": "R/A/G"},
                },
                "required_supporting_docs": [
                    {"artifact_id": "engineering_handoff_checklist"},
                    {"artifact_id": "unresolved_issue_ledger"},
                    {"artifact_id": "fe_truth_source"},
                    {"artifact_id": "be_truth_source"},
                    {"artifact_id": "qa_truth_source"},
                    {"artifact_id": "pm_module_diagram"},
                    {"artifact_id": "state_flow_diagram"},
                    {"artifact_id": "timeout_policy"},
                    {"artifact_id": "retry_or_compensation_policy"},
                ],
                "unresolved_issue_ledger_ref": {
                    "path": "01-模块执行包/示例模块/04-过程文件/示例模块-跨角色预审讨论清单.md"
                },
                "fe_truth_source_ref_or_na": {"path": "01-模块执行包/示例模块/02-工程交接/fe_module.md"},
                "be_truth_source_ref_or_na": {"path": "01-模块执行包/示例模块/02-工程交接/be_module.md"},
                "qa_truth_source_ref": {"path": "01-模块执行包/示例模块/02-工程交接/qa_module.md"},
                "dba_truth_source_ref_or_na": {"na": True, "rationale": "module has no persistence impact"},
                "ops_truth_source_ref_or_na": {"na": True, "rationale": "module has no operational risk"},
                "artifact_refs": {
                    "engineering_handoff_checklist": {
                        "path": "01-模块执行包/示例模块/04-过程文件/示例模块-工程交接门槛清单.md"
                    },
                    "unresolved_issue_ledger": {
                        "path": "01-模块执行包/示例模块/04-过程文件/示例模块-跨角色预审讨论清单.md"
                    },
                    "fe_truth_source": {"path": "01-模块执行包/示例模块/02-工程交接/fe_module.md"},
                    "be_truth_source": {"path": "01-模块执行包/示例模块/02-工程交接/be_module.md"},
                    "qa_truth_source": {"path": "01-模块执行包/示例模块/02-工程交接/qa_module.md"},
                    "pm_module_diagram": {"path": "01-模块执行包/示例模块/01-PRD/示例模块-模块图.md"},
                    "state_flow_diagram": {"path": "01-模块执行包/示例模块/02-工程交接/async-state-diagram.md"},
                    "timeout_policy": {"path": "01-模块执行包/示例模块/02-工程交接/async-timeout-policy.md"},
                    "retry_or_compensation_policy": {
                        "path": "01-模块执行包/示例模块/02-工程交接/async-retry-policy.md"
                    },
                },
            },
            "registry": gate_b_contract["registry"],
        }
        gate_b_path = project_root / "gate-b.json"
        gate_b_path.write_text(json.dumps(gate_b_input, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return gate_b_path

    def run_gate_b_pair_writeback(self, project_root: Path) -> None:
        gate_b_path = self.seed_gate_b_ready_project(project_root)
        handoff = subprocess.run(
            [sys.executable, str(HANDOFF_SCRIPT), "--input", str(gate_b_path), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(handoff.returncode, 0, handoff.stdout + handoff.stderr)

        sync = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(sync.returncode, 0, sync.stdout + sync.stderr)

        state_path = project_root / "80-完整提交包" / "00-提交状态.json"
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertTrue(payload["status"]["engineering_handoff_required"])
        self.assertTrue(payload["status"]["engineering_handoff_ready"])

    def test_sync_and_check_pass_for_minimal_project(self):
        project_root = copy_fixture("minimal-project")
        sync = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(sync.returncode, 0, sync.stdout + sync.stderr)
        self.assertIn("synced submission status", sync.stdout)
        overview = (project_root / "80-完整提交包" / "00-提交说明.md").read_text(encoding="utf-8")
        self.assertIn("validators_passed", overview)
        self.assertIn("status_synced", overview)
        self.assertIn("工程交接必检：`no`", overview)
        self.assertIn("工程交接就绪：`no`", overview)

        check = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertIn("submission consistency check passed", check.stdout)

    def test_check_fails_for_semantic_conflict(self):
        project_root = copy_fixture("fail-semantic-conflict")
        result = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("review status is not approved/frozen", result.stdout)

    def test_engineering_handoff_required_source_chain_rejects_illegal_display_carrier_even_when_values_match(self) -> None:
        project_root = copy_fixture("minimal-project")
        self.run_gate_b_pair_writeback(project_root)

        self.append_lines(
            project_root / "80-完整提交包/00-提交说明.md",
            ["engineering_handoff_required: true", "semantic_slot_owner: illegal_display_carrier"],
        )

        result = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertNotIn("submission consistency check passed", result.stdout)
        self.assertIn("semantic slot mismatch: engineering_handoff_required", result.stdout)
        updated_payload = json.loads((project_root / "80-完整提交包" / "00-提交状态.json").read_text(encoding="utf-8"))
        self.assertFalse(updated_payload["status"]["gates"]["consistency_check_passed"])
        self.assertTrue(updated_payload["status"]["gates"]["status_synced"])

    def test_engineering_handoff_ready_prd_evidence_only_rejects_same_value_prd_carrier(self) -> None:
        project_root = copy_fixture("minimal-project")
        self.run_gate_b_pair_writeback(project_root)

        self.append_lines(
            project_root / "01-模块执行包/示例模块/01-PRD/示例-PRD.md",
            ["engineering_handoff_ready: true", "semantic_slot_owner: illegal_prd_carrier"],
        )

        result = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertNotIn("submission consistency check passed", result.stdout)
        self.assertIn("semantic slot mismatch: engineering_handoff_ready", result.stdout)
        updated_payload = json.loads((project_root / "80-完整提交包" / "00-提交状态.json").read_text(encoding="utf-8"))
        self.assertFalse(updated_payload["status"]["gates"]["consistency_check_passed"])
        self.assertTrue(updated_payload["status"]["gates"]["status_synced"])

    def test_check_fails_for_drifted_display(self):
        project_root = copy_fixture("fail-drifted-display")
        result = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Overview block", result.stdout)

    def test_check_fails_when_ready_without_all_gates_true(self):
        project_root = copy_fixture("minimal-project")
        state_path = project_root / "80-完整提交包" / "00-提交状态.json"
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        payload["status"]["gates"] = {
            "validators_passed": True,
            "status_synced": True,
            "consistency_check_passed": True,
            "review_receipts_present": True,
            "review_blockers_cleared": False,
        }
        state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("gates", result.stdout)

    def test_check_fails_closed_when_status_synced_is_false_even_if_other_fields_align(self):
        project_root = copy_fixture("minimal-project")
        sync = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(sync.returncode, 0, sync.stdout + sync.stderr)

        state_path = project_root / "80-完整提交包" / "00-提交状态.json"
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        payload["status"]["phase"] = "pending_consistency_check"
        payload["status"]["allow_human_review"] = False
        payload["status"]["gates"]["status_synced"] = False
        payload["status"]["gates"]["consistency_check_passed"] = False
        state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        for relative_path in (
            "80-完整提交包/00-提交说明.md",
            "80-完整提交包/01-合并PRD/00-PRD索引.md",
            "80-完整提交包/02-原型索引/00-原型入口.md",
            "80-完整提交包/03-合并评审记录/00-评审索引.md",
        ):
            target_path = project_root / relative_path
            target_path.write_text(
                target_path.read_text(encoding="utf-8").replace("status_synced：yes", "status_synced：no"),
                encoding="utf-8",
            )

        result = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("status_synced", result.stdout)
        updated_payload = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertFalse(updated_payload["status"]["gates"]["consistency_check_passed"])

    def test_scripts_fall_back_to_current_working_directory(self):
        project_root = copy_fixture("minimal-project")
        sync = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT)],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(sync.returncode, 0, sync.stdout + sync.stderr)

        check = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT)],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertIn("submission consistency check passed", check.stdout)

    def test_gate_b_missing_module_returns_structured_blocked_output(self):
        project_root = copy_fixture("minimal-project")
        gate_b_path = project_root / "gate-b-missing-module.json"
        gate_b_path.write_text(
            json.dumps(self.authoritative_gate_b_contract(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [sys.executable, str(HANDOFF_SCRIPT), "--input", str(gate_b_path), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertFalse(payload["status_json_synced"])
        self.assertIn("missing module", " ".join(payload["gate_b_blockers"]))

    def test_gate_b_no_trigger_path_keeps_module_green_bound_to_base_reviews_only(self):
        project_root = copy_fixture("minimal-project")
        gate_b_contract = self.authoritative_gate_b_contract()
        gate_b_input = {
            "schema": gate_b_contract["schema"],
            "schema_version": gate_b_contract["schema_version"],
            "registry_version": gate_b_contract["registry_version"],
            "linked_rule_version": gate_b_contract["linked_rule_version"],
            "module": {
                "module_id": "示例模块",
                "ready_for_human_review": True,
                "handoff_context": {"engineering_review_requested": False},
                "scope": {
                    "has_ui": False,
                    "requires_backend": False,
                    "multi_role": False,
                    "affects_persistence": False,
                    "has_operational_risk": False,
                },
                "declared_triggers": [],
                "product_truth_signals": {},
            },
            "registry": gate_b_contract["registry"],
        }
        gate_b_path = project_root / "gate-b-no-trigger.json"
        gate_b_path.write_text(json.dumps(gate_b_input, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(HANDOFF_SCRIPT), "--input", str(gate_b_path), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )

        payload = json.loads(result.stdout)
        self.assertTrue(payload["ready_for_human_review"])
        self.assertFalse(payload["engineering_handoff_required"])
        self.assertFalse(payload["engineering_handoff_ready"])
        self.assertEqual(payload["matched_triggers"], [])
        self.assertEqual(payload["module_green_rule"], "基础四审全绿（engineering_handoff_required=false）")
        self.assertTrue(payload["module_green_ready"])

        status_payload = json.loads((project_root / "80-完整提交包/00-提交状态.json").read_text(encoding="utf-8"))
        self.assertFalse(status_payload["status"]["engineering_handoff_required"])
        self.assertFalse(status_payload["status"]["engineering_handoff_ready"])

    def test_sync_and_check_cover_engineering_handoff_outward_surfaces(self):
        project_root = copy_fixture("minimal-project")
        state_path = project_root / "80-完整提交包" / "00-提交状态.json"
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        payload["artifacts"]["engineering_handoff"] = self.engineering_handoff_contract()
        state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.write_doc(
            project_root,
            "00-项目包/02-工程交接/README.md",
            "总控",
            ["truth: project handoff index", "scope: engineering handoff", "acceptance: outward artifact listed"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/README.md",
            "总控",
            ["truth: handoff index", "scope: engineering handoff", "acceptance: outward artifact listed"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/04-过程文件/示例模块-工程交接门槛清单.md",
            "总控",
            ["module_id: 示例模块", "engineering_handoff_ready: false", "required_supporting_docs: listed"],
        )

        sync = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(sync.returncode, 0, sync.stdout + sync.stderr)

        handoff_readme = (project_root / "01-模块执行包/示例模块/02-工程交接/README.md").read_text(encoding="utf-8")
        self.assertIn("PRD状态：`approved`", handoff_readme)
        self.assertIn("工程交接必检：`no`", handoff_readme)
        checklist = (
            project_root / "01-模块执行包/示例模块/04-过程文件/示例模块-工程交接门槛清单.md"
        ).read_text(encoding="utf-8")
        self.assertIn("status_synced", checklist)

        check = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertIn("submission consistency check passed", check.stdout)

    def test_sync_fails_closed_when_required_engineering_handoff_contract_is_incomplete(self):
        project_root = copy_fixture("minimal-project")
        state_path = project_root / "80-完整提交包" / "00-提交状态.json"
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        payload["status"]["engineering_handoff_required"] = True
        payload["artifacts"]["engineering_handoff"] = {
            "project_entry": "00-项目包/02-工程交接/README.md",
            "module_entries": [],
            "handoff_audit_globs": ["01-模块执行包/*/02-工程交接/**/*.md"],
        }
        state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        sync = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(sync.returncode, 1)
        self.assertIn("submission status sync failed", sync.stdout)
        self.assertIn("artifacts.engineering_handoff missing required key: process_audit_globs", sync.stdout)

    def test_sync_fails_closed_when_registered_engineering_handoff_file_is_missing(self):
        project_root = copy_fixture("minimal-project")
        state_path = project_root / "80-完整提交包" / "00-提交状态.json"
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        payload["status"]["engineering_handoff_required"] = True
        payload["artifacts"]["engineering_handoff"] = self.engineering_handoff_contract()
        state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.write_doc(
            project_root,
            "00-项目包/02-工程交接/README.md",
            "总控",
            ["truth: project handoff index", "scope: engineering handoff", "acceptance: outward artifact listed"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/04-过程文件/示例模块-工程交接门槛清单.md",
            "总控",
            ["module_id: 示例模块", "engineering_handoff_ready: false", "required_supporting_docs: listed"],
        )

        sync = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(sync.returncode, 1)
        self.assertIn("submission status sync failed", sync.stdout)
        self.assertIn("01-模块执行包/示例模块/02-工程交接/README.md", sync.stdout)

    def test_sync_masks_ready_green_until_consistency_check_passes(self):
        project_root = copy_fixture("minimal-project")
        state_path = project_root / "80-完整提交包" / "00-提交状态.json"
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        payload["status"].update(
            {
                "phase": "ready_for_human_review",
                "allow_human_review": True,
                "last_review_batch": "batch-001",
                "gates": {
                    "validators_passed": True,
                    "status_synced": True,
                    "consistency_check_passed": True,
                    "review_receipts_present": True,
                    "review_blockers_cleared": True,
                },
            }
        )
        payload["artifacts"]["engineering_handoff"] = self.engineering_handoff_contract()
        state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.write_doc(
            project_root,
            "00-项目包/02-工程交接/README.md",
            "总控",
            ["truth: project handoff index", "scope: engineering handoff", "acceptance: outward artifact listed"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/README.md",
            "总控",
            ["truth: handoff index", "scope: engineering handoff", "acceptance: outward artifact listed"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/04-过程文件/示例模块-工程交接门槛清单.md",
            "总控",
            ["module_id: 示例模块", "engineering_handoff_ready: false", "required_supporting_docs: listed"],
        )

        sync = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(sync.returncode, 0, sync.stdout + sync.stderr)
        overview = (project_root / "80-完整提交包" / "00-提交说明.md").read_text(encoding="utf-8")
        self.assertIn("当前阶段：`pending_consistency_check`", overview)
        self.assertIn("可进入人工评审：`no`", overview)

        check = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        overview = (project_root / "80-完整提交包" / "00-提交说明.md").read_text(encoding="utf-8")
        self.assertIn("当前阶段：`ready_for_human_review`", overview)
        self.assertIn("可进入人工评审：`yes`", overview)

    def test_check_fails_closed_when_engineering_handoff_block_drifted(self):
        project_root = copy_fixture("minimal-project")
        state_path = project_root / "80-完整提交包" / "00-提交状态.json"
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        payload["artifacts"]["engineering_handoff"] = self.engineering_handoff_contract()
        state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.write_doc(
            project_root,
            "00-项目包/02-工程交接/README.md",
            "总控",
            ["truth: project handoff index", "scope: engineering handoff", "acceptance: outward artifact listed"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/README.md",
            "总控",
            ["truth: handoff index", "scope: engineering handoff", "acceptance: outward artifact listed"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/04-过程文件/示例模块-工程交接门槛清单.md",
            "总控",
            ["module_id: 示例模块", "engineering_handoff_ready: false", "required_supporting_docs: listed"],
        )

        sync = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(sync.returncode, 0, sync.stdout + sync.stderr)

        handoff_readme_path = project_root / "01-模块执行包/示例模块/02-工程交接/README.md"
        handoff_readme_path.write_text(
            handoff_readme_path.read_text(encoding="utf-8").replace("PRD状态：`approved`", "PRD状态：`draft`"),
            encoding="utf-8",
        )

        check = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(check.returncode, 1)
        self.assertIn("Engineering handoff entry (示例模块) PRD状态 mismatch", check.stdout)

    def test_check_fails_when_forbidden_token_found_in_handoff_audit_scope(self):
        project_root = copy_fixture("minimal-project")
        state_path = project_root / "80-完整提交包" / "00-提交状态.json"
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        payload["artifacts"]["engineering_handoff"] = self.engineering_handoff_contract()
        state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.write_doc(
            project_root,
            "00-项目包/02-工程交接/README.md",
            "总控",
            ["truth: project handoff index", "scope: engineering handoff", "acceptance: outward artifact listed"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/README.md",
            "总控",
            ["truth: handoff index", "scope: engineering handoff", "acceptance: 待评审"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/04-过程文件/示例模块-工程交接门槛清单.md",
            "总控",
            ["module_id: 示例模块", "engineering_handoff_ready: false", "required_supporting_docs: listed"],
        )

        sync = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(sync.returncode, 0, sync.stdout + sync.stderr)

        check = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(check.returncode, 1)
        self.assertIn("forbidden token '待评审' found in audited file", check.stdout)
        self.assertIn("01-模块执行包/示例模块/02-工程交接/README.md", check.stdout)

    def test_check_fails_when_forbidden_token_found_in_process_audit_scope(self):
        project_root = copy_fixture("minimal-project")
        state_path = project_root / "80-完整提交包" / "00-提交状态.json"
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        payload["artifacts"]["engineering_handoff"] = self.engineering_handoff_contract()
        state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.write_doc(
            project_root,
            "00-项目包/02-工程交接/README.md",
            "总控",
            ["truth: project handoff index", "scope: engineering handoff", "acceptance: outward artifact listed"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/README.md",
            "总控",
            ["truth: handoff index", "scope: engineering handoff", "acceptance: outward artifact listed"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/04-过程文件/示例模块-工程交接门槛清单.md",
            "总控",
            ["module_id: 示例模块", "engineering_handoff_ready: false", "required_supporting_docs: 待评审"],
        )

        sync = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(sync.returncode, 0, sync.stdout + sync.stderr)

        check = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(check.returncode, 1)
        self.assertIn("forbidden token '待评审' found in audited file", check.stdout)
        self.assertIn("01-模块执行包/示例模块/04-过程文件/示例模块-工程交接门槛清单.md", check.stdout)

    def test_gate_b_script_writes_back_status_truth_then_sync_chain_surfaces_it(self):
        project_root = copy_fixture("minimal-project")
        state_path = project_root / "80-完整提交包" / "00-提交状态.json"
        status_payload = json.loads(state_path.read_text(encoding="utf-8"))
        status_payload["artifacts"]["engineering_handoff"] = self.engineering_handoff_contract()
        state_path.write_text(json.dumps(status_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        self.write_doc(
            project_root,
            "00-项目包/02-工程交接/README.md",
            "总控",
            ["truth: project handoff index", "scope: engineering handoff", "acceptance: outward artifact listed"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/README.md",
            "总控",
            ["truth: handoff index", "scope: engineering handoff", "acceptance: outward artifact listed"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/04-过程文件/示例模块-工程交接门槛清单.md",
            "总控",
            ["module_id: 示例模块", "engineering_handoff_ready: true", "required_supporting_docs: listed"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/04-过程文件/示例模块-跨角色预审讨论清单.md",
            "总控",
            ["blocker: none", "owner: 总控", "status: closed"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/fe_module.md",
            "FE",
            ["truth: ui state mapping", "scope: loading empty error", "acceptance: all states visible"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/be_module.md",
            "BE",
            ["truth: api and service contract", "scope: review flow", "acceptance: state returned"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/qa_module.md",
            "QA",
            ["truth: executable coverage", "scope: happy and sad paths", "acceptance: blocker paths covered"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/01-PRD/示例模块-模块图.md",
            "PM",
            ["主链: 提交任务 -> 等待回调 -> 返回结果", "分支: 超时转人工", "结果: 成功/失败/转人工"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/async-state-diagram.md",
            "BE",
            ["state: pending", "transition: pending -> succeeded"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/async-timeout-policy.md",
            "BE",
            ["rule: timeout after 30m", "condition: third-party no callback"],
        )
        self.write_doc(
            project_root,
            "01-模块执行包/示例模块/02-工程交接/async-retry-policy.md",
            "BE",
            ["rule: retry up to 3 times", "condition: idempotent failure only"],
        )

        gate_b_contract = self.authoritative_gate_b_contract()
        gate_b_input = {
            "schema": gate_b_contract["schema"],
            "schema_version": gate_b_contract["schema_version"],
            "registry_version": gate_b_contract["registry_version"],
            "linked_rule_version": gate_b_contract["linked_rule_version"],
            "module": {
                "module_id": "示例模块",
                "ready_for_human_review": True,
                "handoff_context": {"engineering_review_requested": True},
                "scope": {
                    "has_ui": True,
                    "requires_backend": True,
                    "multi_role": False,
                    "affects_persistence": False,
                    "has_operational_risk": False,
                },
                "declared_triggers": ["async_task"],
                "product_truth_signals": {"async_task": True},
                "artifact_owner_map": {
                    "engineering_handoff_checklist": {"总控": "R/A/G"},
                    "unresolved_issue_ledger_ref": {"总控": "R/A/G"},
                    "fe_truth_source_ref": {"FE": "R/A", "总控": "G"},
                    "be_truth_source_ref": {"BE": "R/A", "总控": "G"},
                    "qa_truth_source_ref": {"QA": "R/A", "总控": "G"},
                    "pm_module_diagram": {"PM": "R/A", "总控": "G"},
                    "state_flow_diagram": {"BE": "R/A", "总控": "G"},
                    "timeout_policy": {"BE": "R/A", "总控": "G"},
                    "retry_or_compensation_policy": {"BE": "R/A", "总控": "G"},
                    "gate_b_result": {"总控": "R/A/G"},
                },
                "required_supporting_docs": [
                    {"artifact_id": "engineering_handoff_checklist"},
                    {"artifact_id": "unresolved_issue_ledger"},
                    {"artifact_id": "fe_truth_source"},
                    {"artifact_id": "be_truth_source"},
                    {"artifact_id": "qa_truth_source"},
                    {"artifact_id": "pm_module_diagram"},
                    {"artifact_id": "state_flow_diagram"},
                    {"artifact_id": "timeout_policy"},
                    {"artifact_id": "retry_or_compensation_policy"},
                ],
                "unresolved_issue_ledger_ref": {
                    "path": "01-模块执行包/示例模块/04-过程文件/示例模块-跨角色预审讨论清单.md"
                },
                "fe_truth_source_ref_or_na": {"path": "01-模块执行包/示例模块/02-工程交接/fe_module.md"},
                "be_truth_source_ref_or_na": {"path": "01-模块执行包/示例模块/02-工程交接/be_module.md"},
                "qa_truth_source_ref": {"path": "01-模块执行包/示例模块/02-工程交接/qa_module.md"},
                "dba_truth_source_ref_or_na": {"na": True, "rationale": "module has no persistence impact"},
                "ops_truth_source_ref_or_na": {"na": True, "rationale": "module has no operational risk"},
                "artifact_refs": {
                    "engineering_handoff_checklist": {
                        "path": "01-模块执行包/示例模块/04-过程文件/示例模块-工程交接门槛清单.md"
                    },
                    "unresolved_issue_ledger": {
                        "path": "01-模块执行包/示例模块/04-过程文件/示例模块-跨角色预审讨论清单.md"
                    },
                    "fe_truth_source": {"path": "01-模块执行包/示例模块/02-工程交接/fe_module.md"},
                    "be_truth_source": {"path": "01-模块执行包/示例模块/02-工程交接/be_module.md"},
                    "qa_truth_source": {"path": "01-模块执行包/示例模块/02-工程交接/qa_module.md"},
                    "pm_module_diagram": {"path": "01-模块执行包/示例模块/01-PRD/示例模块-模块图.md"},
                    "state_flow_diagram": {"path": "01-模块执行包/示例模块/02-工程交接/async-state-diagram.md"},
                    "timeout_policy": {"path": "01-模块执行包/示例模块/02-工程交接/async-timeout-policy.md"},
                    "retry_or_compensation_policy": {
                        "path": "01-模块执行包/示例模块/02-工程交接/async-retry-policy.md"
                    },
                },
            },
            "registry": gate_b_contract["registry"],
        }
        gate_b_path = project_root / "gate-b.json"
        gate_b_path.write_text(json.dumps(gate_b_input, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        gate_b = subprocess.run(
            [sys.executable, str(HANDOFF_SCRIPT), "--input", str(gate_b_path), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(gate_b.returncode, 0, gate_b.stdout + gate_b.stderr)
        self.assertIn('"status_json_synced": true', gate_b.stdout)

        status_payload = json.loads((project_root / "80-完整提交包/00-提交状态.json").read_text(encoding="utf-8"))
        self.assertTrue(status_payload["status"]["engineering_handoff_required"])
        self.assertTrue(status_payload["status"]["engineering_handoff_ready"])
        self.assertFalse(status_payload["status"]["gates"]["status_synced"])
        self.assertFalse(status_payload["status"]["gates"]["consistency_check_passed"])

        stale_check = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(stale_check.returncode, 1)
        self.assertIn("status_synced", stale_check.stdout)

        sync = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(sync.returncode, 0, sync.stdout + sync.stderr)
        overview = (project_root / "80-完整提交包/00-提交说明.md").read_text(encoding="utf-8")
        self.assertIn("工程交接必检：`yes`", overview)
        self.assertIn("工程交接就绪：`yes`", overview)
        self.assertIn("当前阶段：`pending_consistency_check`", overview)
        self.assertIn("可进入人工评审：`no`", overview)
        status_payload = json.loads((project_root / "80-完整提交包/00-提交状态.json").read_text(encoding="utf-8"))
        self.assertTrue(status_payload["status"]["gates"]["status_synced"])
        self.assertFalse(status_payload["status"]["gates"]["consistency_check_passed"])

        check = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        status_payload = json.loads((project_root / "80-完整提交包/00-提交状态.json").read_text(encoding="utf-8"))
        self.assertTrue(status_payload["status"]["gates"]["status_synced"])
        self.assertTrue(status_payload["status"]["gates"]["consistency_check_passed"])

    def test_gate_b_no_sync_status_json_logs_probe_without_overwriting_latest(self):
        project_root = copy_fixture("minimal-project")
        gate_b_path = self.seed_gate_b_ready_project(project_root)

        canonical = subprocess.run(
            [sys.executable, str(HANDOFF_SCRIPT), "--input", str(gate_b_path), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(canonical.returncode, 0, canonical.stdout + canonical.stderr)
        latest_before = json.loads((project_root / ".ai-team/state/governance-latest.json").read_text(encoding="utf-8"))
        self.assertEqual(latest_before["event_scope"], "canonical")
        self.assertTrue(latest_before["latest_eligible"])

        probe = subprocess.run(
            [
                sys.executable,
                str(HANDOFF_SCRIPT),
                "--input",
                str(gate_b_path),
                "--project-root",
                str(project_root),
                "--no-sync-status-json",
            ],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "AI_TEAM_DEBUG_ALLOW_NO_SYNC_STATUS_JSON": "1"},
        )
        self.assertEqual(probe.returncode, 1, probe.stdout + probe.stderr)
        payload = json.loads(probe.stdout)
        self.assertFalse(payload["status_json_synced"])
        self.assertFalse(payload["engineering_handoff_ready"])
        self.assertTrue(payload["evaluated_engineering_handoff_ready"])

        log_lines = (project_root / ".ai-team/state/governance-log.jsonl").read_text(encoding="utf-8").splitlines()
        last_event = json.loads(log_lines[-1])
        self.assertEqual(last_event["event_scope"], "probe")
        self.assertFalse(last_event["latest_eligible"])
        self.assertEqual(last_event["result"], "blocked")
        self.assertEqual(last_event["output_refs"], [])
        self.assertIn("status_json sync skipped in debug-only mode", last_event["blockers"])

        latest_after = json.loads((project_root / ".ai-team/state/governance-latest.json").read_text(encoding="utf-8"))
        self.assertEqual(latest_after["recorded_at"], latest_before["recorded_at"])
        self.assertEqual(latest_after["event_scope"], "canonical")

    def test_gate_b_accepts_registry_with_unknown_top_level_extensions_when_contract_allows_it(self):
        project_root = copy_fixture("minimal-project")
        gate_b_path = self.seed_gate_b_ready_project(project_root)
        payload = json.loads(gate_b_path.read_text(encoding="utf-8"))
        payload["registry"]["future_registry_extension"] = {
            "owner": "PM",
            "notes": ["preserve me"],
        }
        gate_b_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        gate_b = subprocess.run(
            [sys.executable, str(HANDOFF_SCRIPT), "--input", str(gate_b_path), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(gate_b.returncode, 0, gate_b.stdout + gate_b.stderr)
        self.assertIn('"status_json_synced": true', gate_b.stdout)


if __name__ == "__main__":
    unittest.main()
