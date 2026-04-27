from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_ROOT / "scripts" / "check_final_delivery_gate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_final_delivery_gate", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FinalDeliveryGateUnitTests(unittest.TestCase):
    maxDiff = None

    @staticmethod
    def _copy_minimal_project() -> Path:
        temp_dir = Path(tempfile.mkdtemp())
        project_root = temp_dir / "project"
        shutil.copytree(SKILL_ROOT / "tests" / "fixtures" / "minimal-project", project_root)
        return project_root

    @staticmethod
    def _write_prd_evidence(project_root: Path) -> None:
        prd_path = project_root / "01-模块执行包" / "示例模块" / "01-PRD" / "示例-PRD.md"
        prd_path.parent.mkdir(parents=True, exist_ok=True)
        prd_path.write_text(
            "\n".join(
                [
                    "Owner: `PM`",
                    "Status: `active`",
                    "Version: `v1`",
                    "",
                    "truth: canonical prd evidence",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _write_closeout_source(project_root: Path) -> None:
        closeout_path = project_root / "80-完整提交包" / "03-合并评审记录" / "31-结果-来源.md"
        closeout_path.parent.mkdir(parents=True, exist_ok=True)
        closeout_path.write_text(
            "\n".join(
                [
                    "Owner: `QA`",
                    "Status: `active`",
                    "Version: `v1`",
                    "",
                    "truth: canonical closeout source",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _write_project_level_gate_b_pack(project_root: Path, module) -> None:
        pack_path = project_root / module.PROJECT_LEVEL_GATE_B_INPUT
        pack_path.parent.mkdir(parents=True, exist_ok=True)
        pack_path.write_text(
            json.dumps(
                {
                    "schema": module.EXPECTED_GATE_B_SCHEMA,
                    "schema_version": "v1",
                    "evidence": [],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    @classmethod
    def _prepare_host_project(
        cls,
        module,
        *,
        status_overrides: dict[str, object] | None = None,
        receipt_mode: str = "valid",
        receipt_review_batch: str | None = None,
        receipt_delivery_fingerprint: str | None = None,
    ) -> Path:
        project_root = cls._copy_minimal_project()
        cls._write_prd_evidence(project_root)
        cls._write_closeout_source(project_root)

        status_path = project_root / "80-完整提交包" / "00-提交状态.json"
        config = json.loads(status_path.read_text(encoding="utf-8"))
        if status_overrides:
            config["status"].update(status_overrides)
        status_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if config["status"].get("engineering_handoff_required") is True:
            cls._write_project_level_gate_b_pack(project_root, module)

        receipt_path = project_root / module.RECEIPT_PATH
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        if receipt_mode == "missing":
            return project_root
        if receipt_mode == "invalid":
            receipt_path.write_text(
                "\n".join(
                    [
                        module.RECEIPT_BEGIN_MARKER,
                        "```json",
                        '{"schema":"submission_status.final_review_evidence_receipt","schema_version":"v1",',
                        "```",
                        module.RECEIPT_END_MARKER,
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            return project_root
        if receipt_mode != "valid":
            raise ValueError(f"unsupported receipt_mode: {receipt_mode}")

        expected_inputs, delivery_fingerprint = module.build_fingerprint_inputs(project_root, config)
        receipt = {
            "schema": module.EXPECTED_RECEIPT_SCHEMA,
            "schema_version": module.EXPECTED_RECEIPT_SCHEMA_VERSION,
            "generated_at": "2026-04-11T00:00:00Z",
            "bundle_version": "default-local-v1",
            "receipt_id": "fdr-20260411-001",
            "review_batch": receipt_review_batch or str(config["status"].get("last_review_batch", "")),
            "gate_b_mode": module.expected_gate_b_mode(config["status"]),
            "semantic_boundary": module.final_gate_semantic_boundary(),
            "delivery_fingerprint": receipt_delivery_fingerprint or delivery_fingerprint,
            "fingerprint_inputs": expected_inputs,
            "machine_checks": {
                "sync_submission_status": "pass",
                "check_submission_consistency": "pass",
                "check_publish_boundary": "pass",
            },
            "status_truth_snapshot": module.current_status_snapshot(config["status"]),
            "review_refs": [
                module.RECEIPT_PATH.as_posix(),
                "80-完整提交包/03-合并评审记录/31-结果-来源.md",
            ],
        }
        receipt_path.write_text(
            "\n".join(
                [
                    module.RECEIPT_BEGIN_MARKER,
                    "```json",
                    json.dumps(receipt, ensure_ascii=False, indent=2),
                    "```",
                    module.RECEIPT_END_MARKER,
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return project_root

    @staticmethod
    def _evaluate_final_gate(module, project_root: Path) -> dict[str, object]:
        with patch.object(
            module,
            "rerun_machine_checks",
            return_value=(
                {
                    "sync_submission_status": "pass",
                    "check_submission_consistency": "pass",
                    "check_publish_boundary": "pass",
                },
                [],
                {
                    "sync_submission_status": "",
                    "check_submission_consistency": "",
                    "check_publish_boundary": "",
                },
            ),
        ):
            return module.evaluate_final_delivery_gate(project_root)

    def test_semantic_boundary_contract_is_v0_3_5_and_read_only(self) -> None:
        module = load_module()

        self.assertEqual(
            module.FINAL_GATE_SEMANTIC_BOUNDARY,
            {
                "version": "v0.3.5",
                "judgement_scope": "final_review_evidence_reuse_freshness_only",
                "judges_only_final_review_evidence_reuse_freshness": True,
                "writes_status_truth": False,
                "reruns_sync_submission_status": False,
            },
        )

    def test_evaluate_final_delivery_gate_exposes_semantic_boundary_when_blocked(self) -> None:
        module = load_module()

        with patch.object(
            module,
            "rerun_machine_checks",
            return_value=(
                {"sync_submission_status": "not_required"},
                ["synthetic blocker"],
                {"sync_submission_status": ""},
            ),
        ):
            payload = module.evaluate_final_delivery_gate(Path("/tmp/unused-project-root"))

        self.assertEqual(payload["result"], "blocked")
        self.assertEqual(payload["semantic_boundary"], module.FINAL_GATE_SEMANTIC_BOUNDARY)

    def test_blocks_old_green_reuse_when_status_batch_is_newer_than_canonical_receipt_batch(self) -> None:
        module = load_module()
        project_root = self._prepare_host_project(
            module,
            status_overrides={"last_review_batch": "review-2026-04-11"},
            receipt_review_batch="review-2026-04-02",
        )

        payload = self._evaluate_final_gate(module, project_root)

        self.assertEqual(payload["result"], "blocked")
        self.assertIn("review_batch", " ".join(payload["blockers"]))
        self.assertNotIn("replay-required", json.dumps(payload, ensure_ascii=False))

    def test_blocks_when_canonical_receipt_batch_is_newer_than_status_batch(self) -> None:
        module = load_module()
        project_root = self._prepare_host_project(
            module,
            status_overrides={"last_review_batch": "review-2026-04-02"},
            receipt_review_batch="review-2026-04-11",
        )

        payload = self._evaluate_final_gate(module, project_root)

        self.assertEqual(payload["result"], "blocked")
        self.assertIn("review_batch", " ".join(payload["blockers"]))

    def test_current_status_snapshot_includes_last_review_batch(self) -> None:
        module = load_module()

        snapshot = module.current_status_snapshot(
            {
                "phase": "ready_for_human_review",
                "allow_human_review": True,
                "engineering_handoff_required": False,
                "engineering_handoff_ready": False,
                "last_review_batch": "review-2026-04-11",
            }
        )

        self.assertEqual(
            snapshot,
            {
                "phase": "ready_for_human_review",
                "allow_human_review": True,
                "engineering_handoff_required": False,
                "engineering_handoff_ready": False,
                "last_review_batch": "review-2026-04-11",
            },
        )

    def test_blocks_when_gate_b_required_receipt_matches_but_engineering_handoff_ready_is_false(self) -> None:
        module = load_module()
        project_root = self._prepare_host_project(
            module,
            status_overrides={
                "engineering_handoff_required": True,
                "engineering_handoff_ready": False,
                "gates": {
                    "status_synced": True,
                    "consistency_check_passed": True,
                },
            },
        )

        payload = self._evaluate_final_gate(module, project_root)

        self.assertEqual(payload["result"], "blocked")
        self.assertIn("engineering_handoff_ready", " ".join(payload["blockers"]))

    def test_blocks_when_gate_b_required_receipt_matches_but_status_synced_is_false(self) -> None:
        module = load_module()
        project_root = self._prepare_host_project(
            module,
            status_overrides={
                "engineering_handoff_required": True,
                "engineering_handoff_ready": True,
                "gates": {
                    "status_synced": False,
                    "consistency_check_passed": True,
                },
            },
        )

        payload = self._evaluate_final_gate(module, project_root)

        self.assertEqual(payload["result"], "blocked")
        self.assertIn("status.gates.status_synced", " ".join(payload["blockers"]))

    def test_blocks_when_gate_b_required_receipt_matches_but_consistency_check_passed_is_false(self) -> None:
        module = load_module()
        project_root = self._prepare_host_project(
            module,
            status_overrides={
                "engineering_handoff_required": True,
                "engineering_handoff_ready": True,
                "gates": {
                    "status_synced": True,
                    "consistency_check_passed": False,
                },
            },
        )

        payload = self._evaluate_final_gate(module, project_root)

        self.assertEqual(payload["result"], "blocked")
        self.assertIn("status.gates.consistency_check_passed", " ".join(payload["blockers"]))

    def test_blocks_when_status_sequence_batch_is_numerically_newer_than_receipt_sequence_batch(self) -> None:
        module = load_module()
        project_root = self._prepare_host_project(
            module,
            status_overrides={"last_review_batch": "batch-10"},
            receipt_review_batch="batch-2",
        )

        payload = self._evaluate_final_gate(module, project_root)

        self.assertEqual(payload["result"], "blocked")
        self.assertIn("review_batch", " ".join(payload["blockers"]))

    def test_blocks_when_review_batch_formats_are_mixed_instead_of_falling_back_to_lexicographic_compare(self) -> None:
        module = load_module()
        project_root = self._prepare_host_project(
            module,
            status_overrides={"last_review_batch": "batch-001"},
            receipt_review_batch="review-2026-04-11",
        )

        payload = self._evaluate_final_gate(module, project_root)

        self.assertEqual(payload["result"], "blocked")
        self.assertIn("review_batch", " ".join(payload["blockers"]))

    def test_blocks_when_review_batch_is_unparseable_instead_of_falling_back_to_lexicographic_compare(self) -> None:
        module = load_module()
        project_root = self._prepare_host_project(
            module,
            status_overrides={"last_review_batch": "batch-001"},
            receipt_review_batch="pending",
        )

        payload = self._evaluate_final_gate(module, project_root)

        self.assertEqual(payload["result"], "blocked")
        self.assertIn("review_batch", " ".join(payload["blockers"]))

    def test_blocks_when_canonical_receipt_missing(self) -> None:
        module = load_module()
        project_root = self._prepare_host_project(module, receipt_mode="missing")

        payload = self._evaluate_final_gate(module, project_root)

        self.assertEqual(payload["result"], "blocked")
        self.assertIn(f"canonical receipt missing: {module.RECEIPT_PATH.as_posix()}", payload["blockers"])

    def test_blocks_when_canonical_receipt_is_invalid(self) -> None:
        module = load_module()
        project_root = self._prepare_host_project(module, receipt_mode="invalid")

        payload = self._evaluate_final_gate(module, project_root)

        self.assertEqual(payload["result"], "blocked")
        self.assertTrue(any("receipt JSON is invalid" in blocker for blocker in payload["blockers"]))

    def test_keeps_stale_when_review_batch_matches_but_fingerprint_differs(self) -> None:
        module = load_module()
        project_root = self._prepare_host_project(
            module,
            receipt_review_batch="review-2026-04-02",
            receipt_delivery_fingerprint="sha256:deadbeef",
        )

        payload = self._evaluate_final_gate(module, project_root)

        self.assertEqual(payload["result"], "stale")
        self.assertNotIn("replay-required", json.dumps(payload, ensure_ascii=False))

    def test_extract_receipt_payload_rejects_multiple_receipt_blocks(self) -> None:
        module = load_module()
        receipt = "\n".join(
            [
                module.RECEIPT_BEGIN_MARKER,
                "```json",
                '{"schema":"submission_status.final_review_evidence_receipt","schema_version":"v1"}',
                "```",
                module.RECEIPT_END_MARKER,
            ]
        )
        text = f"{receipt}\n\n{receipt}\n"

        with self.assertRaises(ValueError) as exc:
            module.extract_receipt_payload(text)

        self.assertIn("multiple receipt blocks", str(exc.exception))

    def test_extract_receipt_payload_rejects_non_json_fence(self) -> None:
        module = load_module()
        text = "\n".join(
            [
                module.RECEIPT_BEGIN_MARKER,
                "```yaml",
                "schema: submission_status.final_review_evidence_receipt",
                "```",
                module.RECEIPT_END_MARKER,
            ]
        )

        with self.assertRaises(ValueError) as exc:
            module.extract_receipt_payload(text)

        self.assertIn("exactly one json fenced block", str(exc.exception))

    def test_extract_receipt_payload_rejects_second_fenced_block(self) -> None:
        module = load_module()
        text = "\n".join(
            [
                module.RECEIPT_BEGIN_MARKER,
                "```json",
                '{"schema":"submission_status.final_review_evidence_receipt","schema_version":"v1"}',
                "```",
                "",
                "```json",
                '{"extra":true}',
                "```",
                module.RECEIPT_END_MARKER,
            ]
        )

        with self.assertRaises(ValueError) as exc:
            module.extract_receipt_payload(text)

        self.assertIn("exactly one json fenced block", str(exc.exception))

    def test_validate_status_truth_snapshot_requires_exact_match(self) -> None:
        module = load_module()
        current_status = {
            "phase": "ready_for_human_review",
            "allow_human_review": True,
            "engineering_handoff_required": True,
            "engineering_handoff_ready": True,
        }
        receipt_snapshot = {
            "phase": "ready_for_human_review",
            "allow_human_review": True,
            "engineering_handoff_required": True,
            "engineering_handoff_ready": False,
        }

        with self.assertRaises(ValueError) as exc:
            module.validate_status_truth_snapshot(current_status, receipt_snapshot)

        self.assertIn("status_truth_snapshot mismatch", str(exc.exception))

    def test_validate_fingerprint_inputs_rejects_duplicate_type_path(self) -> None:
        module = load_module()

        with self.assertRaises(ValueError) as exc:
            module.validate_fingerprint_inputs(
                [
                    {"type": "status_truth", "path": "80-完整提交包/00-提交状态.json", "sha256": "a"},
                    {"type": "status_truth", "path": "80-完整提交包/00-提交状态.json", "sha256": "b"},
                ],
                [
                    {"type": "status_truth", "path": "80-完整提交包/00-提交状态.json", "sha256": "a"},
                    {"type": "outward_entry", "path": "80-完整提交包/00-提交说明.md", "sha256": "b"},
                ],
                compare_sha256=True,
            )

        self.assertIn("duplicate", str(exc.exception))

    def test_validate_fingerprint_inputs_rejects_path_order_mismatch(self) -> None:
        module = load_module()

        with self.assertRaises(ValueError) as exc:
            module.validate_fingerprint_inputs(
                [
                    {"type": "outward_entry", "path": "80-完整提交包/00-提交说明.md", "sha256": "b"},
                    {"type": "status_truth", "path": "80-完整提交包/00-提交状态.json", "sha256": "a"},
                ],
                [
                    {"type": "status_truth", "path": "80-完整提交包/00-提交状态.json", "sha256": "a"},
                    {"type": "outward_entry", "path": "80-完整提交包/00-提交说明.md", "sha256": "b"},
                ],
                compare_sha256=True,
            )

        self.assertIn("path order mismatch", str(exc.exception))

    def test_validate_fingerprint_inputs_rejects_sha256_mismatch(self) -> None:
        module = load_module()

        with self.assertRaises(ValueError) as exc:
            module.validate_fingerprint_inputs(
                [
                    {"type": "status_truth", "path": "80-完整提交包/00-提交状态.json", "sha256": "tampered"},
                ],
                [
                    {"type": "status_truth", "path": "80-完整提交包/00-提交状态.json", "sha256": "expected"},
                ],
                compare_sha256=True,
            )

        self.assertIn("sha256 mismatch", str(exc.exception))

    def test_validate_review_refs_requires_closeout_source_reference(self) -> None:
        module = load_module()

        with self.assertRaises(ValueError) as exc:
            module.validate_review_refs(
                {
                    "review_refs": [
                        module.RECEIPT_PATH.as_posix(),
                    ]
                }
            )

        self.assertIn("closeout source reference", str(exc.exception))

    def test_validate_receipt_requires_matching_semantic_boundary(self) -> None:
        module = load_module()
        current_status = {
            "phase": "ready_for_human_review",
            "allow_human_review": True,
            "engineering_handoff_required": False,
            "engineering_handoff_ready": False,
        }
        receipt = {
            "schema": module.EXPECTED_RECEIPT_SCHEMA,
            "schema_version": module.EXPECTED_RECEIPT_SCHEMA_VERSION,
            "generated_at": "2026-04-10T12:34:56Z",
            "bundle_version": "default-local-v1",
            "receipt_id": "fdr-20260410-001",
            "review_batch": "review-2026-04-10",
            "gate_b_mode": module.expected_gate_b_mode(current_status),
            "semantic_boundary": {
                "version": "v0.3.4",
                "judgement_scope": "legacy",
                "judges_only_final_review_evidence_reuse_freshness": False,
                "writes_status_truth": True,
                "reruns_sync_submission_status": True,
            },
            "delivery_fingerprint": "sha",
            "fingerprint_inputs": [
                {"type": "status_truth", "path": "80-完整提交包/00-提交状态.json", "sha256": "sha"}
            ],
            "machine_checks": {
                "sync_submission_status": "pass",
                "check_submission_consistency": "pass",
                "check_publish_boundary": "pass",
            },
            "status_truth_snapshot": module.current_status_snapshot(current_status),
            "review_refs": [
                module.RECEIPT_PATH.as_posix(),
                module.RECEIPT_PATH.as_posix() + "#3-产品审查记录",
            ],
        }

        with self.assertRaises(ValueError) as exc:
            module.validate_receipt(
                receipt,
                current_status=current_status,
                expected_inputs=[
                    {"type": "status_truth", "path": "80-完整提交包/00-提交状态.json", "sha256": "sha"}
                ],
                compare_sha256=False,
            )

        self.assertIn("semantic_boundary", str(exc.exception))

    def test_validate_receipt_requires_review_batch_as_canonical_freshness_carrier(self) -> None:
        module = load_module()
        current_status = {
            "phase": "ready_for_human_review",
            "allow_human_review": True,
            "engineering_handoff_required": False,
            "engineering_handoff_ready": False,
        }
        receipt = {
            "schema": module.EXPECTED_RECEIPT_SCHEMA,
            "schema_version": module.EXPECTED_RECEIPT_SCHEMA_VERSION,
            "generated_at": "2026-04-10T12:34:56Z",
            "bundle_version": "default-local-v1",
            "receipt_id": "fdr-20260410-002",
            "gate_b_mode": module.expected_gate_b_mode(current_status),
            "semantic_boundary": module.final_gate_semantic_boundary(),
            "delivery_fingerprint": "sha",
            "fingerprint_inputs": [
                {"type": "status_truth", "path": "80-完整提交包/00-提交状态.json", "sha256": "sha"}
            ],
            "machine_checks": {
                "sync_submission_status": "pass",
                "check_submission_consistency": "pass",
                "check_publish_boundary": "pass",
            },
            "status_truth_snapshot": module.current_status_snapshot(current_status),
            "review_refs": [
                module.RECEIPT_PATH.as_posix(),
                module.RECEIPT_PATH.as_posix() + "#7-Final-Review-Evidence-Receipt",
            ],
        }

        with self.assertRaises(ValueError) as exc:
            module.validate_receipt(
                receipt,
                current_status=current_status,
                expected_inputs=[
                    {"type": "status_truth", "path": "80-完整提交包/00-提交状态.json", "sha256": "sha"}
                ],
                compare_sha256=False,
            )

        self.assertIn("review_batch", str(exc.exception))

if __name__ == "__main__":
    unittest.main()
