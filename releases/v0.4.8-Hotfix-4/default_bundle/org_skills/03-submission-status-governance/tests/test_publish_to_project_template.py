from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


PUBLISH_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish_to_project_template.py"


def load_publish_module():
    spec = importlib.util.spec_from_file_location("publish_module", PUBLISH_SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load publish script: {PUBLISH_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PublishToProjectTemplateTests(unittest.TestCase):
    def test_publish_contract_declares_final_gate_script_in_managed_set(self):
        module = load_publish_module()
        contract = module.publish_contract()
        managed_destinations = [entry["destination"] for entry in contract["managed_entries"]]

        self.assertTrue(
            all(dest.startswith("scripts/") or dest == "80-完整提交包/00-提交状态.json" for dest in managed_destinations),
            msg="publish contract should stay contracted to scripts plus the status JSON copy",
        )
        self.assertNotIn("AGENTS.md", "\n".join(managed_destinations))
        self.assertNotIn("20-项目执行文件包目录标准.md", "\n".join(managed_destinations))

        self.assertEqual(
            contract,
            {
                "source_root": "install/default_bundle/org_skills/03-submission-status-governance",
                "destination_root": "install/default_bundle/assets/project_skeleton/00-项目包模板",
                "managed_entries": [
                    {
                        "kind": "script",
                        "source": "scripts/sync_submission_status.py",
                        "destination": "scripts/sync_submission_status.py",
                    },
                    {
                        "kind": "script",
                        "source": "scripts/check_submission_consistency.py",
                        "destination": "scripts/check_submission_consistency.py",
                    },
                    {
                        "kind": "script",
                        "source": "scripts/check_publish_boundary.py",
                        "destination": "scripts/check_publish_boundary.py",
                    },
                    {
                        "kind": "script",
                        "source": "scripts/check_engineering_handoff_readiness.py",
                        "destination": "scripts/check_engineering_handoff_readiness.py",
                    },
                    {
                        "kind": "script",
                        "source": "scripts/check_final_delivery_gate.py",
                        "destination": "scripts/check_final_delivery_gate.py",
                    },
                    {
                        "kind": "reference",
                        "source": "references/00-提交状态.example.json",
                        "destination": "80-完整提交包/00-提交状态.json",
                    },
                ],
            },
        )

    def test_main_without_repo_root_uses_repository_root(self):
        module = load_publish_module()
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            skill_root = repo_root / "install" / "default_bundle" / "org_skills" / "03-submission-status-governance"
            template_root = repo_root / "install" / "default_bundle" / "assets" / "project_skeleton" / "00-项目包模板"
            fake_script_path = skill_root / "scripts" / "publish_to_project_template.py"

            (skill_root / "scripts").mkdir(parents=True)
            (skill_root / "references").mkdir(parents=True)
            (template_root / "scripts").mkdir(parents=True)
            (template_root / "80-完整提交包").mkdir(parents=True)
            fake_script_path.write_text("# fake script path for default repo-root resolution\n", encoding="utf-8")

            (skill_root / "scripts" / "sync_submission_status.py").write_text("sync-source", encoding="utf-8")
            (skill_root / "scripts" / "check_submission_consistency.py").write_text("check-source", encoding="utf-8")
            (skill_root / "scripts" / "check_engineering_handoff_readiness.py").write_text("handoff-source", encoding="utf-8")
            (skill_root / "scripts" / "check_final_delivery_gate.py").write_text("final-delivery-source", encoding="utf-8")
            (skill_root / "scripts" / "check_publish_boundary.py").write_text("boundary-source", encoding="utf-8")
            (skill_root / "references" / "00-提交状态.example.json").write_text('{"version": 1}', encoding="utf-8")

            original_file = module.__file__
            module.__file__ = str(fake_script_path)
            try:
                exit_code = module.main([])
            finally:
                module.__file__ = original_file

            self.assertEqual(exit_code, 0)
            sync_text = (template_root / "scripts" / "sync_submission_status.py").read_text(encoding="utf-8")
            check_text = (template_root / "scripts" / "check_submission_consistency.py").read_text(encoding="utf-8")
            handoff_text = (template_root / "scripts" / "check_engineering_handoff_readiness.py").read_text(encoding="utf-8")
            final_delivery_text = (template_root / "scripts" / "check_final_delivery_gate.py").read_text(encoding="utf-8")
            boundary_text = (template_root / "scripts" / "check_publish_boundary.py").read_text(encoding="utf-8")
            self.assertIn("AI_TEAM_MANAGED_SOURCE: scripts/sync_submission_status.py", sync_text)
            self.assertIn("sync-source", sync_text)
            self.assertIn("AI_TEAM_MANAGED_SOURCE: scripts/check_submission_consistency.py", check_text)
            self.assertIn("check-source", check_text)
            self.assertIn("AI_TEAM_MANAGED_SOURCE: scripts/check_engineering_handoff_readiness.py", handoff_text)
            self.assertIn("handoff-source", handoff_text)
            self.assertIn("AI_TEAM_MANAGED_SOURCE: scripts/check_final_delivery_gate.py", final_delivery_text)
            self.assertIn("final-delivery-source", final_delivery_text)
            self.assertEqual(
                final_delivery_text,
                module._stamp_managed_script("scripts/check_final_delivery_gate.py", "final-delivery-source"),
            )
            self.assertIn("AI_TEAM_MANAGED_SOURCE: scripts/check_publish_boundary.py", boundary_text)
            self.assertIn("boundary-source", boundary_text)
            self.assertEqual((template_root / "80-完整提交包" / "00-提交状态.json").read_text(encoding="utf-8"), '{"version": 1}')

    def test_publish_copies_scripts_and_example_json(self):
        module = load_publish_module()
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            skill_root = repo_root / "install" / "default_bundle" / "org_skills" / "03-submission-status-governance"
            template_root = repo_root / "install" / "default_bundle" / "assets" / "project_skeleton" / "00-项目包模板"

            (skill_root / "scripts").mkdir(parents=True)
            (skill_root / "references").mkdir(parents=True)
            (template_root / "scripts").mkdir(parents=True)
            (template_root / "80-完整提交包").mkdir(parents=True)

            (skill_root / "scripts" / "sync_submission_status.py").write_text("sync-source", encoding="utf-8")
            (skill_root / "scripts" / "check_submission_consistency.py").write_text("check-source", encoding="utf-8")
            (skill_root / "scripts" / "check_engineering_handoff_readiness.py").write_text("handoff-source", encoding="utf-8")
            (skill_root / "scripts" / "check_final_delivery_gate.py").write_text("final-delivery-source", encoding="utf-8")
            (skill_root / "scripts" / "check_publish_boundary.py").write_text("boundary-source", encoding="utf-8")
            (skill_root / "references" / "00-提交状态.example.json").write_text('{"version": 1}', encoding="utf-8")

            published = module.publish(repo_root)

            self.assertEqual(len(published), 6)
            sync_text = (template_root / "scripts" / "sync_submission_status.py").read_text(encoding="utf-8")
            check_text = (template_root / "scripts" / "check_submission_consistency.py").read_text(encoding="utf-8")
            handoff_text = (template_root / "scripts" / "check_engineering_handoff_readiness.py").read_text(encoding="utf-8")
            final_delivery_text = (template_root / "scripts" / "check_final_delivery_gate.py").read_text(encoding="utf-8")
            boundary_text = (template_root / "scripts" / "check_publish_boundary.py").read_text(encoding="utf-8")
            self.assertIn("AI_TEAM_MANAGED_SOURCE: scripts/sync_submission_status.py", sync_text)
            self.assertIn("sync-source", sync_text)
            self.assertIn("AI_TEAM_MANAGED_SOURCE: scripts/check_submission_consistency.py", check_text)
            self.assertIn("check-source", check_text)
            self.assertIn("AI_TEAM_MANAGED_SOURCE: scripts/check_engineering_handoff_readiness.py", handoff_text)
            self.assertIn("handoff-source", handoff_text)
            self.assertIn("AI_TEAM_MANAGED_SOURCE: scripts/check_final_delivery_gate.py", final_delivery_text)
            self.assertIn("final-delivery-source", final_delivery_text)
            self.assertEqual(
                final_delivery_text,
                module._stamp_managed_script("scripts/check_final_delivery_gate.py", "final-delivery-source"),
            )
            self.assertIn("AI_TEAM_MANAGED_SOURCE: scripts/check_publish_boundary.py", boundary_text)
            self.assertIn("boundary-source", boundary_text)
            self.assertEqual((template_root / "80-完整提交包" / "00-提交状态.json").read_text(encoding="utf-8"), '{"version": 1}')

    def test_publish_does_not_rewrite_consumer_docs(self):
        module = load_publish_module()
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            skill_root = repo_root / "install" / "default_bundle" / "org_skills" / "03-submission-status-governance"
            template_root = repo_root / "install" / "default_bundle" / "assets" / "project_skeleton" / "00-项目包模板"

            (skill_root / "scripts").mkdir(parents=True)
            (skill_root / "references").mkdir(parents=True)
            (template_root / "scripts").mkdir(parents=True)
            (template_root / "assets").mkdir(parents=True)
            (template_root / "80-完整提交包").mkdir(parents=True)

            (skill_root / "scripts" / "sync_submission_status.py").write_text("sync-source", encoding="utf-8")
            (skill_root / "scripts" / "check_submission_consistency.py").write_text("check-source", encoding="utf-8")
            (skill_root / "scripts" / "check_engineering_handoff_readiness.py").write_text("handoff-source", encoding="utf-8")
            (skill_root / "scripts" / "check_final_delivery_gate.py").write_text("final-delivery-source", encoding="utf-8")
            (skill_root / "scripts" / "check_publish_boundary.py").write_text("boundary-source", encoding="utf-8")
            (skill_root / "references" / "00-提交状态.example.json").write_text('{"version": 1}', encoding="utf-8")

            (template_root / "AGENTS.md").write_text("consumer-doc-sentinel", encoding="utf-8")
            directory_standard = template_root / "assets" / "20-项目执行文件包目录标准.md"
            directory_standard.write_text("consumer-doc-sentinel", encoding="utf-8")
            agents_before = (template_root / "AGENTS.md").read_text(encoding="utf-8")
            directory_before = directory_standard.read_text(encoding="utf-8")

            module.publish(repo_root)

            self.assertEqual((template_root / "AGENTS.md").read_text(encoding="utf-8"), agents_before)
            self.assertEqual(directory_standard.read_text(encoding="utf-8"), directory_before)


if __name__ == "__main__":
    unittest.main()
