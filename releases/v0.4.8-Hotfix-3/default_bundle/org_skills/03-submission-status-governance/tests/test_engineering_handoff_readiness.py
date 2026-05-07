from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

import yaml


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_ROOT / "scripts" / "check_engineering_handoff_readiness.py"
BUNDLE_ROOT = SKILL_ROOT.parents[1]
STRUCTURE_RULE_PATH = BUNDLE_ROOT / "assets" / "rules" / "产品结构约束.yaml"
PATH_RULE_PATH = BUNDLE_ROOT / "assets" / "rules" / "产品路径约束.yaml"
EXAMPLE_INPUT_PATH = SKILL_ROOT / "references" / "gate-b.example.json"


def load_module():
    spec = importlib.util.spec_from_file_location("check_engineering_handoff_readiness", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_doc(root: Path, relative_path: str, metadata: dict[str, str], semantic_lines: list[str]) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"Owner: `{metadata['owner']}`",
        f"Status: `{metadata['status']}`",
        f"Version: `{metadata['version']}`",
        f"Linked PRD: `{metadata['linked_prd_source']}`",
        "",
    ]
    lines.extend(semantic_lines)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class EngineeringHandoffReadinessTests(unittest.TestCase):
    maxDiff = None
    MODULE_GREEN_RULE_BASE_FOUR_ONLY = "基础四审全绿（engineering_handoff_required=false）"
    MODULE_GREEN_RULE_WITH_GATE_B = "基础四审全绿 + 24-审查-跨角色预审完成 + Gate B green（engineering_handoff_required=true）"
    PREREVIEW_24_LABEL = "24-审查-跨角色预审 prerequisite"

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.module = load_module()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def registry(self) -> dict:
        return {
            "approved_repository_scopes": ["docs/handoff", "docs/issues"],
            "artifact_registry": {
                "engineering_handoff_checklist": {
                    "allowed_path_pattern": [r"docs/issues/.+checklist\.md"],
                    "allowed_file_type": [".md"],
                    "owner_role": "总控",
                    "na_policy": "forbidden",
                    "semantic_check_profile": "engineering_handoff_checklist",
                },
                "unresolved_issue_ledger": {
                    "allowed_path_pattern": [r"docs/issues/.+\.md"],
                    "allowed_file_type": [".md"],
                    "owner_role": "总控",
                    "na_policy": "forbidden",
                    "semantic_check_profile": "unresolved_issue_ledger",
                },
                "qa_truth_source": {
                    "allowed_path_pattern": [r"docs/handoff/qa/.+\.md"],
                    "allowed_file_type": [".md"],
                    "owner_role": "QA",
                    "na_policy": "forbidden",
                    "semantic_check_profile": "role_truth_source",
                },
                "be_truth_source": {
                    "allowed_path_pattern": [r"docs/handoff/be/.+\.md"],
                    "allowed_file_type": [".md"],
                    "owner_role": "BE",
                    "na_policy": "allowed",
                    "semantic_check_profile": "role_truth_source",
                },
                "role_matrix": {
                    "allowed_path_pattern": [r"docs/handoff/rbac/.+role-matrix\.md"],
                    "allowed_file_type": [".md"],
                    "owner_role": "BE",
                    "na_policy": "forbidden",
                    "semantic_check_profile": "role_matrix",
                },
                "data_scope_rule": {
                    "allowed_path_pattern": [r"docs/handoff/rbac/.+data-scope\.md"],
                    "allowed_file_type": [".md"],
                    "owner_role": "BE",
                    "na_policy": "forbidden",
                    "semantic_check_profile": "data_scope_rule",
                },
                "audit_rule": {
                    "allowed_path_pattern": [r"docs/handoff/rbac/.+audit\.md"],
                    "allowed_file_type": [".md"],
                    "owner_role": "BE",
                    "na_policy": "forbidden",
                    "semantic_check_profile": "policy_note",
                },
            },
        }

    def published_registry(self) -> dict:
        example_payload = json.loads(EXAMPLE_INPUT_PATH.read_text(encoding="utf-8"))
        with PATH_RULE_PATH.open("r", encoding="utf-8") as handle:
            path_rules = yaml.safe_load(handle)
        with STRUCTURE_RULE_PATH.open("r", encoding="utf-8") as handle:
            structure_rules = yaml.safe_load(handle)
        registry = example_payload["registry"]
        required_artifacts = set(structure_rules["handoff_gate_requirements"]["required_artifacts"])
        missing_required_artifacts = sorted(required_artifacts - set(registry["artifact_registry"].keys()))
        if missing_required_artifacts:
            raise AssertionError(
                f"published Gate B contract is missing structure-required artifacts: {missing_required_artifacts}"
            )
        return {
            "approved_repository_scopes": path_rules["engineering_handoff_boundary"]["approved_repository_scopes"],
            "artifact_registry": registry["artifact_registry"],
            "contract_extensions": registry["contract_extensions"],
        }

    def published_contract_versions(self) -> dict[str, str]:
        example_payload = json.loads(EXAMPLE_INPUT_PATH.read_text(encoding="utf-8"))
        return {
            "schema_version": example_payload["schema_version"],
            "registry_version": example_payload["registry_version"],
            "linked_rule_version": example_payload["linked_rule_version"],
        }

    def test_published_gate_b_example_tracks_published_registry_subset(self) -> None:
        example_payload = json.loads(EXAMPLE_INPUT_PATH.read_text(encoding="utf-8"))
        published = self.published_registry()

        self.assertEqual(example_payload["schema"], "submission_status.gate_b_evidence_pack")
        self.assertEqual(example_payload["schema_version"], "v1")
        self.assertTrue(example_payload["registry_version"])
        self.assertTrue(example_payload["linked_rule_version"])
        self.assertIn("module", example_payload)
        self.assertIn("registry", example_payload)
        self.assertEqual(
            example_payload["module"]["module_green_contract"]["when_engineering_handoff_required_false"],
            "基础四审全绿",
        )
        self.assertEqual(
            example_payload["module"]["module_green_contract"]["when_engineering_handoff_required_true"],
            "基础四审全绿 + 24-审查-跨角色预审完成 + Gate B green",
        )
        self.assertEqual(
            example_payload["registry"]["approved_repository_scopes"],
            published["approved_repository_scopes"],
        )
        self.assertEqual(
            example_payload["registry"]["contract_extensions"],
            published["contract_extensions"],
        )

        example_registry = example_payload["registry"]["artifact_registry"]
        for artifact_id, entry in example_registry.items():
            with self.subTest(artifact_id=artifact_id):
                self.assertIn(artifact_id, published["artifact_registry"])
                self.assertEqual(entry, published["artifact_registry"][artifact_id])

    def test_normalize_registry_payload_preserves_unknown_top_level_extension_keys(self):
        payload = self.module.normalize_registry_payload(
            {
                "approved_repository_scopes": ["docs/handoff"],
                "artifact_registry": {},
                "contract_extensions": {"preserve_top_level_unknown_keys": True},
            }
        )

        self.assertEqual(payload["contract_extensions"], {"preserve_top_level_unknown_keys": True})

    def test_load_input_rejects_mismatched_unknown_top_level_registry_extensions(self):
        input_path = self.project_root / "gate-b.input.json"
        input_path.write_text(
            json.dumps(
                {
                    "schema": self.module.EXPECTED_GATE_B_SCHEMA,
                    "schema_version": "v1",
                    "registry_version": "gate-b-registry.v0.3.3",
                    "linked_rule_version": "gate-b-rules.v0.3.3",
                    "module": {},
                    "registry": {
                        "approved_repository_scopes": [],
                        "artifact_registry": {},
                        "contract_extensions": {"preserve_top_level_unknown_keys": False},
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        original_loader = self.module.load_authoritative_gate_b_contract
        self.module.load_authoritative_gate_b_contract = lambda _project_root: {
            "schema": self.module.EXPECTED_GATE_B_SCHEMA,
            "schema_version": "v1",
            "registry_version": "gate-b-registry.v0.3.3",
            "linked_rule_version": "gate-b-rules.v0.3.3",
            "registry": {
                "approved_repository_scopes": [],
                "artifact_registry": {},
                "contract_extensions": {"preserve_top_level_unknown_keys": True},
            },
        }
        try:
            with self.assertRaises(ValueError) as exc:
                self.module.load_input(input_path, self.project_root)
        finally:
            self.module.load_authoritative_gate_b_contract = original_loader

        self.assertIn("embedded gate-b registry does not match authoritative bundled contract", str(exc.exception))

    def test_load_input_allows_preserved_unknown_top_level_registry_keys(self):
        input_path = self.project_root / "gate-b.input.json"
        input_path.write_text(
            json.dumps(
                {
                    "schema": self.module.EXPECTED_GATE_B_SCHEMA,
                    "schema_version": "v1",
                    "registry_version": "gate-b-registry.v0.3.3",
                    "linked_rule_version": "gate-b-rules.v0.3.3",
                    "module": {},
                    "registry": {
                        "approved_repository_scopes": [],
                        "artifact_registry": {},
                        "contract_extensions": {"preserve_top_level_unknown_keys": True},
                        "custom_registry_key": {"keep": True},
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        original_loader = self.module.load_authoritative_gate_b_contract
        self.module.load_authoritative_gate_b_contract = lambda _project_root: {
            "schema": self.module.EXPECTED_GATE_B_SCHEMA,
            "schema_version": "v1",
            "registry_version": "gate-b-registry.v0.3.3",
            "linked_rule_version": "gate-b-rules.v0.3.3",
            "registry": {
                "approved_repository_scopes": [],
                "artifact_registry": {},
                "contract_extensions": {"preserve_top_level_unknown_keys": True},
            },
        }
        try:
            _, registry = self.module.load_input(input_path, self.project_root)
        finally:
            self.module.load_authoritative_gate_b_contract = original_loader

        self.assertEqual(registry["custom_registry_key"], {"keep": True})

    def minimal_payload(self) -> dict:
        return {
            "module_id": "module-06",
            "ready_for_human_review": True,
            "handoff_context": {"engineering_review_requested": True},
            "scope": {
                "has_ui": False,
                "requires_backend": True,
                "multi_role": False,
                "affects_persistence": False,
                "has_operational_risk": False,
            },
            "declared_triggers": ["dynamic_permission"],
            "product_truth_signals": {"dynamic_permission": True},
            "artifact_owner_map": {
                "engineering_handoff_checklist": {"总控": "R/A/G"},
                "unresolved_issue_ledger_ref": {"总控": "R/A/G"},
                "be_truth_source_ref": {"BE": "R/A", "总控": "G"},
                "qa_truth_source_ref": {"QA": "R/A", "总控": "G"},
                "role_matrix": {"BE": "R/A", "总控": "G"},
                "data_scope_rule": {"BE": "R/A", "总控": "G"},
                "audit_rule": {"BE": "R/A", "总控": "G"},
                "gate_b_result": {"总控": "R/A/G"},
            },
            "required_supporting_docs": [
                {"artifact_id": "engineering_handoff_checklist"},
                {"artifact_id": "unresolved_issue_ledger"},
                {"artifact_id": "qa_truth_source"},
                {"artifact_id": "be_truth_source"},
                {"artifact_id": "role_matrix"},
                {"artifact_id": "data_scope_rule"},
                {"artifact_id": "audit_rule"},
            ],
            "unresolved_issue_ledger_ref": {"path": "docs/issues/module-06-ledger.md"},
            "fe_truth_source_ref_or_na": {"na": True, "rationale": "module has no UI"},
            "be_truth_source_ref_or_na": {"path": "docs/handoff/be/module-06-be.md"},
            "qa_truth_source_ref": {"path": "docs/handoff/qa/module-06-qa.md"},
            "dba_truth_source_ref_or_na": {"na": True, "rationale": "module has no persistence impact"},
            "ops_truth_source_ref_or_na": {"na": True, "rationale": "module has no operational risk"},
            "artifact_refs": {
                "engineering_handoff_checklist": {"path": "docs/issues/module-06-checklist.md"},
                "unresolved_issue_ledger": {"path": "docs/issues/module-06-ledger.md"},
                "qa_truth_source": {"path": "docs/handoff/qa/module-06-qa.md"},
                "be_truth_source": {"path": "docs/handoff/be/module-06-be.md"},
                "role_matrix": {"path": "docs/handoff/rbac/module-06-role-matrix.md"},
                "data_scope_rule": {"path": "docs/handoff/rbac/module-06-data-scope.md"},
                "audit_rule": {"path": "docs/handoff/rbac/module-06-audit.md"},
            },
        }

    def write_minimal_pass_docs(self) -> None:
        write_doc(
            self.project_root,
            "docs/issues/module-06-checklist.md",
            {
                "owner": "总控",
                "status": "active",
                "version": "v1",
                "linked_prd_source": "01-PRD/module-06.md",
            },
            ["module_id: module-06", "engineering_handoff_ready: true", "required_supporting_docs: listed"],
        )
        write_doc(
            self.project_root,
            "docs/issues/module-06-ledger.md",
            {
                "owner": "总控",
                "status": "active",
                "version": "v1",
                "linked_prd_source": "01-PRD/module-06.md",
            },
            ["blocker: none", "owner: 总控", "status: closed"],
        )
        write_doc(
            self.project_root,
            "docs/handoff/qa/module-06-qa.md",
            {
                "owner": "QA",
                "status": "active",
                "version": "v1",
                "linked_prd_source": "01-PRD/module-06.md",
            },
            ["truth: executable acceptance", "scope: gate b minimal", "acceptance: reviewer can execute"],
        )
        write_doc(
            self.project_root,
            "docs/handoff/be/module-06-be.md",
            {
                "owner": "BE",
                "status": "active",
                "version": "v1",
                "linked_prd_source": "01-PRD/module-06.md",
            },
            ["truth: api contract", "scope: create review", "acceptance: deny invalid role"],
        )
        write_doc(
            self.project_root,
            "docs/handoff/rbac/module-06-role-matrix.md",
            {
                "owner": "BE",
                "status": "active",
                "version": "v1",
                "linked_prd_source": "01-PRD/module-06.md",
            },
            ["roles: admin, auditor", "actions: approve, reject", "scope boundary: tenant only"],
        )
        write_doc(
            self.project_root,
            "docs/handoff/rbac/module-06-data-scope.md",
            {
                "owner": "BE",
                "status": "active",
                "version": "v1",
                "linked_prd_source": "01-PRD/module-06.md",
            },
            ["scope: tenant only", "data: customer records"],
        )
        write_doc(
            self.project_root,
            "docs/handoff/rbac/module-06-audit.md",
            {
                "owner": "BE",
                "status": "active",
                "version": "v1",
                "linked_prd_source": "01-PRD/module-06.md",
            },
            ["rule: audit every approval", "condition: privileged action only"],
        )

    def async_payload(self) -> dict:
        return {
            "module_id": "module-async",
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
                "path": "01-模块执行包/06-后台/04-过程文件/06-后台-跨角色预审讨论清单.md"
            },
            "fe_truth_source_ref_or_na": {"path": "01-模块执行包/06-后台/02-工程交接/fe_module.md"},
            "be_truth_source_ref_or_na": {"path": "01-模块执行包/06-后台/02-工程交接/be_module.md"},
            "qa_truth_source_ref": {"path": "01-模块执行包/06-后台/02-工程交接/qa_module.md"},
            "dba_truth_source_ref_or_na": {"na": True, "rationale": "module has no persistence impact"},
            "ops_truth_source_ref_or_na": {"na": True, "rationale": "module has no operational risk"},
            "artifact_refs": {
                "engineering_handoff_checklist": {
                    "path": "01-模块执行包/06-后台/04-过程文件/06-后台-工程交接门槛清单.md"
                },
                "unresolved_issue_ledger": {
                    "path": "01-模块执行包/06-后台/04-过程文件/06-后台-跨角色预审讨论清单.md"
                },
                "fe_truth_source": {"path": "01-模块执行包/06-后台/02-工程交接/fe_module.md"},
                "be_truth_source": {"path": "01-模块执行包/06-后台/02-工程交接/be_module.md"},
                "qa_truth_source": {"path": "01-模块执行包/06-后台/02-工程交接/qa_module.md"},
                "pm_module_diagram": {"path": "01-模块执行包/06-后台/01-PRD/06-后台-模块图.md"},
                "state_flow_diagram": {"path": "01-模块执行包/06-后台/02-工程交接/async-state-diagram.md"},
                "timeout_policy": {"path": "01-模块执行包/06-后台/02-工程交接/async-timeout-policy.md"},
                "retry_or_compensation_policy": {
                    "path": "01-模块执行包/06-后台/02-工程交接/async-retry-policy.md"
                },
            },
        }

    def write_async_docs(self) -> None:
        write_doc(
            self.project_root,
            "01-模块执行包/06-后台/04-过程文件/06-后台-工程交接门槛清单.md",
            {
                "owner": "总控",
                "status": "active",
                "version": "v1",
                "linked_prd_source": "01-模块执行包/06-后台/01-PRD/06-后台-PRD.md",
            },
            ["module_id: 06-后台", "engineering_handoff_ready: true", "required_supporting_docs: listed"],
        )
        write_doc(
            self.project_root,
            "01-模块执行包/06-后台/04-过程文件/06-后台-跨角色预审讨论清单.md",
            {
                "owner": "总控",
                "status": "closed",
                "version": "v1",
                "linked_prd_source": "01-模块执行包/06-后台/01-PRD/06-后台-PRD.md",
            },
            ["blocker: none", "owner: 总控", "status: closed"],
        )
        write_doc(
            self.project_root,
            "01-模块执行包/06-后台/02-工程交接/fe_module.md",
            {
                "owner": "FE",
                "status": "active",
                "version": "v1",
                "linked_prd_source": "01-模块执行包/06-后台/01-PRD/06-后台-PRD.md",
            },
            ["truth: ui state mapping", "scope: pending and timeout", "acceptance: state visible"],
        )
        write_doc(
            self.project_root,
            "01-模块执行包/06-后台/02-工程交接/be_module.md",
            {
                "owner": "BE",
                "status": "active",
                "version": "v1",
                "linked_prd_source": "01-模块执行包/06-后台/01-PRD/06-后台-PRD.md",
            },
            ["truth: api contract", "scope: async processing", "acceptance: retry idempotent"],
        )
        write_doc(
            self.project_root,
            "01-模块执行包/06-后台/02-工程交接/qa_module.md",
            {
                "owner": "QA",
                "status": "active",
                "version": "v1",
                "linked_prd_source": "01-模块执行包/06-后台/01-PRD/06-后台-PRD.md",
            },
            ["truth: executable coverage", "scope: timeout and retry", "acceptance: failures covered"],
        )
        write_doc(
            self.project_root,
            "01-模块执行包/06-后台/01-PRD/06-后台-模块图.md",
            {
                "owner": "PM",
                "status": "active",
                "version": "v1",
                "linked_prd_source": "01-模块执行包/06-后台/01-PRD/06-后台-PRD.md",
            },
            ["主链: 提交任务 -> 等待回调 -> 返回结果", "分支: 超时转人工", "结果: 成功/失败/转人工"],
        )
        write_doc(
            self.project_root,
            "01-模块执行包/06-后台/02-工程交接/async-state-diagram.md",
            {
                "owner": "BE",
                "status": "active",
                "version": "v1",
                "linked_prd_source": "01-模块执行包/06-后台/01-PRD/06-后台-PRD.md",
            },
            ["state: pending", "transition: pending -> success"],
        )
        write_doc(
            self.project_root,
            "01-模块执行包/06-后台/02-工程交接/async-timeout-policy.md",
            {
                "owner": "BE",
                "status": "active",
                "version": "v1",
                "linked_prd_source": "01-模块执行包/06-后台/01-PRD/06-后台-PRD.md",
            },
            ["rule: timeout after 30m", "condition: callback absent"],
        )
        write_doc(
            self.project_root,
            "01-模块执行包/06-后台/02-工程交接/async-retry-policy.md",
            {
                "owner": "BE",
                "status": "active",
                "version": "v1",
                "linked_prd_source": "01-模块执行包/06-后台/01-PRD/06-后台-PRD.md",
            },
            ["rule: retry up to 3 times", "condition: transient failure"],
        )

    def write_evidence_pack(self, relative_path: str, module_payload: dict | None = None, registry_payload: dict | None = None) -> Path:
        versions = self.published_contract_versions()
        payload = {
            "schema": self.module.EXPECTED_GATE_B_SCHEMA,
            "schema_version": versions["schema_version"],
            "registry_version": versions["registry_version"],
            "linked_rule_version": versions["linked_rule_version"],
            "module": module_payload or self.minimal_payload(),
            "registry": registry_payload or self.registry(),
        }
        path = self.project_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def test_passes_minimal_registry_driven_payload(self):
        self.write_minimal_pass_docs()
        result = self.module.evaluate_engineering_handoff(
            self.minimal_payload(),
            self.registry(),
            project_root=self.project_root,
        )

        self.assertTrue(result["engineering_handoff_required"])
        self.assertTrue(result["engineering_handoff_ready"], result["gate_b_blockers"])
        self.assertEqual(result["matched_triggers"], ["dynamic_permission"])
        self.assertEqual(result["gate_b_blockers"], [])
        self.assertEqual(result["module_green_rule"], self.MODULE_GREEN_RULE_WITH_GATE_B)
        self.assertTrue(result["module_green_ready"])

    def test_module_green_rule_falls_back_to_base_four_reviews_when_engineering_handoff_not_required(self):
        payload = self.minimal_payload()
        payload["handoff_context"] = {"engineering_review_requested": False}
        payload["scope"]["requires_backend"] = False
        payload["declared_triggers"] = []
        payload["product_truth_signals"] = {}

        result = self.module.evaluate_engineering_handoff(
            payload,
            self.registry(),
            project_root=self.project_root,
        )

        self.assertFalse(result["engineering_handoff_required"])
        self.assertFalse(result["engineering_handoff_ready"])
        self.assertEqual(result["gate_b_blockers"], [])
        self.assertEqual(result["module_green_rule"], self.MODULE_GREEN_RULE_BASE_FOUR_ONLY)
        self.assertTrue(result["module_green_ready"])

    def test_engineering_handoff_required_true_requires_24_prereview_and_gate_b(self):
        self.write_minimal_pass_docs()
        payload = self.minimal_payload()
        payload["required_supporting_docs"] = [
            item for item in payload["required_supporting_docs"] if item.get("artifact_id") != "unresolved_issue_ledger"
        ]
        payload["artifact_refs"].pop("unresolved_issue_ledger")

        result = self.module.evaluate_engineering_handoff(
            payload,
            self.registry(),
            project_root=self.project_root,
        )

        self.assertTrue(result["engineering_handoff_required"])
        self.assertFalse(result["engineering_handoff_ready"])
        self.assertIn("24-审查-跨角色预审", " ".join(result["gate_b_blockers"]))
        self.assertEqual(result["module_green_rule"], self.MODULE_GREEN_RULE_WITH_GATE_B)
        self.assertFalse(result["module_green_ready"])

    def test_unresolved_issue_ledger_errors_are_labeled_as_24_prereview_prerequisite(self):
        self.write_minimal_pass_docs()

        cases: list[tuple[str, callable]] = []

        def remove_required_doc(payload: dict) -> None:
            payload["required_supporting_docs"] = [
                item for item in payload["required_supporting_docs"] if item.get("artifact_id") != "unresolved_issue_ledger"
            ]

        cases.append(("required_supporting_docs missing artifact_id", remove_required_doc))

        def missing_artifact_ref(payload: dict) -> None:
            payload["artifact_refs"].pop("unresolved_issue_ledger")
            payload.pop("unresolved_issue_ledger_ref")

        cases.append(("missing required artifact ref", missing_artifact_ref))

        def owner_map_missing(payload: dict) -> None:
            payload["artifact_owner_map"].pop("unresolved_issue_ledger_ref")

        cases.append(("artifact_owner_map missing key", owner_map_missing))

        def machine_field_conflicts_path(payload: dict) -> None:
            payload["unresolved_issue_ledger_ref"] = {"na": True, "rationale": "use NA branch for conflict test"}

        cases.append(("unresolved_issue_ledger_ref conflicts with artifact_refs.", machine_field_conflicts_path))

        def machine_field_conflicts_na(payload: dict) -> None:
            payload["artifact_refs"]["unresolved_issue_ledger"] = {"na": True, "rationale": "existing NA ref"}

        cases.append(("conflicts with artifact_refs.", machine_field_conflicts_na))

        def machine_field_mismatch(payload: dict) -> None:
            payload["unresolved_issue_ledger_ref"] = {"path": "docs/issues/module-06-ledger-alt.md"}

        cases.append(("mismatch with artifact_refs.", machine_field_mismatch))

        def scope_mismatch(payload: dict) -> None:
            outside = self.project_root / "outside" / "module-06-ledger.md"
            outside.parent.mkdir(parents=True, exist_ok=True)
            outside.write_text("placeholder\n", encoding="utf-8")
            payload["unresolved_issue_ledger_ref"] = {"path": "outside/module-06-ledger.md"}
            payload["artifact_refs"]["unresolved_issue_ledger"] = {"path": "outside/module-06-ledger.md"}

        cases.append(("outside approved repository scopes", scope_mismatch))

        def path_pattern_mismatch(payload: dict) -> None:
            mismatch_path = "docs/handoff/qa/module-06-ledger.md"
            write_doc(
                self.project_root,
                mismatch_path,
                {
                    "owner": "总控",
                    "status": "active",
                    "version": "v1",
                    "linked_prd_source": "01-PRD/module-06.md",
                },
                ["blocker: none", "owner: 总控", "status: closed"],
            )
            payload["unresolved_issue_ledger_ref"] = {"path": mismatch_path}
            payload["artifact_refs"]["unresolved_issue_ledger"] = {"path": mismatch_path}

        cases.append(("path pattern mismatch", path_pattern_mismatch))

        def metadata_missing(payload: dict) -> None:
            write_doc(
                self.project_root,
                "docs/issues/module-06-ledger.md",
                {
                    "owner": "总控",
                    "status": "active",
                    "version": "",
                    "linked_prd_source": "01-PRD/module-06.md",
                },
                ["blocker: none", "owner: 总控", "status: closed"],
            )

        cases.append(("missing Version metadata", metadata_missing))

        def semantic_missing(payload: dict) -> None:
            write_doc(
                self.project_root,
                "docs/issues/module-06-ledger.md",
                {
                    "owner": "总控",
                    "status": "active",
                    "version": "v1",
                    "linked_prd_source": "01-PRD/module-06.md",
                },
                ["owner: 总控", "status: closed"],
            )

        cases.append(("missing semantic token 'blocker'", semantic_missing))

        for expected_fragment, mutate in cases:
            payload = self.minimal_payload()
            mutate(payload)
            result = self.module.evaluate_engineering_handoff(payload, self.registry(), project_root=self.project_root)
            with self.subTest(expected_fragment=expected_fragment):
                branch_messages = [item for item in result["gate_b_blockers"] if expected_fragment in item]
                self.assertTrue(branch_messages, msg=f"missing branch message: {expected_fragment}")
                self.assertTrue(
                    any(self.PREREVIEW_24_LABEL in item for item in branch_messages),
                    msg=f"branch message not labeled with 24 prerequisite: {branch_messages}",
                )

    def test_fails_when_required_supporting_doc_is_missing(self):
        self.write_minimal_pass_docs()
        payload = self.minimal_payload()
        payload["artifact_refs"].pop("data_scope_rule")

        result = self.module.evaluate_engineering_handoff(
            payload,
            self.registry(),
            project_root=self.project_root,
        )

        self.assertFalse(result["engineering_handoff_ready"])
        self.assertIn("missing required artifact ref: data_scope_rule", result["gate_b_blockers"])

    def test_fails_for_invalid_path_type_and_scope(self):
        self.write_minimal_pass_docs()
        payload = self.minimal_payload()

        (self.project_root / "outside").mkdir(parents=True, exist_ok=True)
        wrong_scope = self.project_root / "outside" / "role-matrix.md"
        wrong_scope.write_text("placeholder\n", encoding="utf-8")
        payload["artifact_refs"]["role_matrix"] = {"path": "outside/role-matrix.md"}
        result = self.module.evaluate_engineering_handoff(payload, self.registry(), project_root=self.project_root)
        self.assertFalse(result["engineering_handoff_ready"])
        self.assertTrue(any("outside approved repository scopes" in item for item in result["gate_b_blockers"]))

        payload["artifact_refs"]["role_matrix"] = {"path": "docs/handoff/rbac/module-06-role-matrix.txt"}
        txt_path = self.project_root / "docs/handoff/rbac/module-06-role-matrix.txt"
        txt_path.write_text("placeholder\n", encoding="utf-8")
        result = self.module.evaluate_engineering_handoff(payload, self.registry(), project_root=self.project_root)
        self.assertFalse(result["engineering_handoff_ready"])
        self.assertTrue(any("file type mismatch" in item for item in result["gate_b_blockers"]))

        payload["artifact_refs"]["role_matrix"] = {"path": "docs/handoff/be/module-06-role-matrix.md"}
        wrong_pattern = self.project_root / "docs/handoff/be/module-06-role-matrix.md"
        wrong_pattern.write_text("placeholder\n", encoding="utf-8")
        result = self.module.evaluate_engineering_handoff(payload, self.registry(), project_root=self.project_root)
        self.assertFalse(result["engineering_handoff_ready"])
        self.assertTrue(any("path pattern mismatch" in item for item in result["gate_b_blockers"]))

    def test_fails_for_illegal_na(self):
        self.write_minimal_pass_docs()
        payload = self.minimal_payload()
        payload["artifact_refs"]["be_truth_source"] = {"na": True, "rationale": "backend design not needed"}

        result = self.module.evaluate_engineering_handoff(
            payload,
            self.registry(),
            project_root=self.project_root,
        )

        self.assertFalse(result["engineering_handoff_ready"])
        self.assertTrue(any("illegal N/A for be_truth_source" in item for item in result["gate_b_blockers"]))

    def test_fails_when_trigger_is_inferred_but_not_declared(self):
        self.write_minimal_pass_docs()
        payload = self.minimal_payload()
        payload["declared_triggers"] = []

        result = self.module.evaluate_engineering_handoff(
            payload,
            self.registry(),
            project_root=self.project_root,
        )

        self.assertFalse(result["engineering_handoff_ready"])
        self.assertTrue(any("inferred trigger not declared: dynamic_permission" in item for item in result["gate_b_blockers"]))

    def test_fails_when_semantic_minimum_is_not_met(self):
        self.write_minimal_pass_docs()
        write_doc(
            self.project_root,
            "docs/handoff/rbac/module-06-role-matrix.md",
            {
                "owner": "BE",
                "status": "active",
                "version": "",
                "linked_prd_source": "01-PRD/module-06.md",
            },
            ["roles: admin, auditor", "actions: approve, reject"],
        )

        result = self.module.evaluate_engineering_handoff(
            self.minimal_payload(),
            self.registry(),
            project_root=self.project_root,
        )

        self.assertFalse(result["engineering_handoff_ready"])
        self.assertTrue(any("missing Version metadata" in item for item in result["gate_b_blockers"]))
        self.assertTrue(any("missing semantic token 'scope'" in item for item in result["gate_b_blockers"]))

    def test_parse_args_allows_repo_persisted_default_without_input(self):
        args = self.module.parse_args(["--project-root", str(self.project_root)])

        self.assertIsNone(args.input)
        self.assertEqual(args.project_root, str(self.project_root))

    def test_repo_persisted_module_level_evidence_pack_is_preferred(self):
        self.write_minimal_pass_docs()
        module_path = self.write_evidence_pack("01-模块执行包/module-06/04-过程文件/gate-b.input.json")
        self.write_evidence_pack(
            "00-项目包/04-过程文件/04-全量提交-gate-b.input.json",
            module_payload={**self.minimal_payload(), "module_id": "project-level-module"},
        )

        resolved = self.module.resolve_input_path(None, self.project_root)

        self.assertEqual(resolved, module_path)

    def test_project_level_evidence_pack_does_not_mask_multiple_module_level_packs(self):
        self.write_minimal_pass_docs()
        self.write_evidence_pack("01-模块执行包/module-06/04-过程文件/gate-b.input.json")
        self.write_evidence_pack("01-模块执行包/module-07/04-过程文件/gate-b.input.json")
        self.write_evidence_pack("00-项目包/04-过程文件/04-全量提交-gate-b.input.json")

        with self.assertRaises(FileNotFoundError) as exc:
            self.module.resolve_input_path(None, self.project_root)

        self.assertIn("multiple module-level Gate B evidence packs found", str(exc.exception))

    def test_repo_persisted_project_level_evidence_pack_is_used_as_fallback(self):
        self.write_minimal_pass_docs()
        project_path = self.write_evidence_pack("00-项目包/04-过程文件/04-全量提交-gate-b.input.json")

        resolved = self.module.resolve_input_path(None, self.project_root)

        self.assertEqual(resolved, project_path)

    def test_explicit_input_overrides_repo_persisted_discovery(self):
        self.write_minimal_pass_docs()
        explicit_path = self.write_evidence_pack("custom/gate-b-explicit.json")
        self.write_evidence_pack("00-项目包/04-过程文件/04-全量提交-gate-b.input.json")

        resolved = self.module.resolve_input_path(explicit_path, self.project_root)

        self.assertEqual(resolved, explicit_path)

    def test_relative_explicit_input_is_resolved_from_project_root_not_cwd(self):
        self.write_minimal_pass_docs()
        explicit_path = self.write_evidence_pack("custom/gate-b-explicit.json")
        unrelated_cwd = self.project_root / "elsewhere"
        unrelated_cwd.mkdir(parents=True, exist_ok=True)
        original_cwd = Path.cwd()
        os.chdir(unrelated_cwd)
        try:
            resolved = self.module.resolve_input_path("custom/gate-b-explicit.json", self.project_root)
        finally:
            os.chdir(original_cwd)

        self.assertEqual(resolved, explicit_path)

    def test_tmp_debug_fallback_is_disabled_by_default(self):
        self.write_minimal_pass_docs()
        debug_path = Path("/tmp/gate-b.json")
        original = debug_path.read_text(encoding="utf-8") if debug_path.exists() else None
        debug_path.write_text('{"schema":"submission_status.gate_b_evidence_pack","schema_version":"v1","module":{},"registry":{}}\n', encoding="utf-8")
        try:
            with self.assertRaises(FileNotFoundError) as exc:
                self.module.resolve_input_path(None, self.project_root)
            self.assertIn("Use --input for an explicit file", str(exc.exception))
        finally:
            if original is None:
                debug_path.unlink(missing_ok=True)
            else:
                debug_path.write_text(original, encoding="utf-8")

    def test_tmp_debug_fallback_is_used_only_when_explicitly_enabled(self):
        self.write_minimal_pass_docs()
        debug_path = Path("/tmp/gate-b.json")
        original = debug_path.read_text(encoding="utf-8") if debug_path.exists() else None
        debug_path.write_text('{"schema":"submission_status.gate_b_evidence_pack","schema_version":"v1","module":{},"registry":{}}\n', encoding="utf-8")
        original_flag = os.environ.get(self.module.DEBUG_FALLBACK_ENV)
        os.environ[self.module.DEBUG_FALLBACK_ENV] = "1"
        try:
            resolved = self.module.resolve_input_path(None, self.project_root)
            self.assertEqual(resolved, debug_path)
        finally:
            if original_flag is None:
                os.environ.pop(self.module.DEBUG_FALLBACK_ENV, None)
            else:
                os.environ[self.module.DEBUG_FALLBACK_ENV] = original_flag
            if original is None:
                debug_path.unlink(missing_ok=True)
            else:
                debug_path.write_text(original, encoding="utf-8")

    def test_multiple_module_level_evidence_packs_require_explicit_input(self):
        self.write_minimal_pass_docs()
        self.write_evidence_pack("01-模块执行包/module-06/04-过程文件/gate-b.input.json")
        self.write_evidence_pack("01-模块执行包/module-07/04-过程文件/gate-b.input.json")
        self.write_evidence_pack("00-项目包/04-过程文件/04-全量提交-gate-b.input.json")

        with self.assertRaises(FileNotFoundError) as exc:
            self.module.resolve_input_path(None, self.project_root)

        self.assertIn("multiple module-level Gate B evidence packs found", str(exc.exception))

    def test_explicit_input_without_project_root_infers_project_root_from_input_path(self):
        self.write_async_docs()
        input_path = self.write_evidence_pack(
            "01-模块执行包/06-后台/04-过程文件/gate-b.input.json",
            module_payload=self.async_payload(),
            registry_payload=self.published_registry(),
        )

        inferred_root = self.module.resolve_project_root(None, input_path)

        self.assertEqual(inferred_root.resolve(), self.project_root.resolve())

    def test_fails_when_owner_map_or_machine_ref_fields_are_missing(self):
        self.write_minimal_pass_docs()
        payload = self.minimal_payload()
        payload.pop("artifact_owner_map")
        payload.pop("be_truth_source_ref_or_na")

        result = self.module.evaluate_engineering_handoff(
            payload,
            self.registry(),
            project_root=self.project_root,
        )

        self.assertFalse(result["engineering_handoff_ready"])
        self.assertIn("missing or empty artifact_owner_map", result["gate_b_blockers"])
        self.assertIn("missing machine field: be_truth_source_ref_or_na", result["gate_b_blockers"])

    def test_published_registry_async_task_requires_timeout_and_retry_docs(self):
        self.write_async_docs()
        payload = self.async_payload()
        payload["artifact_refs"].pop("timeout_policy")

        result = self.module.evaluate_engineering_handoff(
            payload,
            self.published_registry(),
            project_root=self.project_root,
        )

        self.assertFalse(result["engineering_handoff_ready"])
        self.assertIn("missing required artifact ref: timeout_policy", result["gate_b_blockers"])

    def test_published_registry_async_task_requires_pm_module_diagram(self):
        self.write_async_docs()
        payload = self.async_payload()
        payload["artifact_refs"].pop("pm_module_diagram")

        result = self.module.evaluate_engineering_handoff(
            payload,
            self.published_registry(),
            project_root=self.project_root,
        )

        self.assertFalse(result["engineering_handoff_ready"])
        self.assertIn("missing required artifact ref: pm_module_diagram", result["gate_b_blockers"])

    def test_published_registry_accepts_complete_async_payload(self):
        self.write_async_docs()
        result = self.module.evaluate_engineering_handoff(
            self.async_payload(),
            self.published_registry(),
            project_root=self.project_root,
        )

        self.assertTrue(result["engineering_handoff_required"])
        self.assertTrue(result["engineering_handoff_ready"], result["gate_b_blockers"])
        self.assertEqual(result["matched_triggers"], ["async_task"])

    def test_fail_closed_result_uses_blocked_unknown_semantics(self):
        result = self.module.fail_closed_result("synthetic blocker")

        self.assertEqual(result["result"], "blocked")
        self.assertIsNone(result["engineering_handoff_required"])
        self.assertIsNone(result["module_green_rule"])
        self.assertIsNone(result["module_green_ready"])
        self.assertFalse(result["status_json_synced"])
        self.assertEqual(result["gate_b_blockers"], ["synthetic blocker"])


if __name__ == "__main__":
    unittest.main()
