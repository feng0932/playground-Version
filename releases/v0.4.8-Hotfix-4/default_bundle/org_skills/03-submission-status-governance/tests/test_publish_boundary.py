from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
CHECK_SCRIPT = SKILL_ROOT / "scripts" / "check_publish_boundary.py"
PUBLISH_SCRIPT = SKILL_ROOT / "scripts" / "publish_to_project_template.py"


class PublishBoundaryTests(unittest.TestCase):
    def make_repo(self) -> Path:
        temp_dir = Path(tempfile.mkdtemp(prefix="ai-team-publish-boundary-"))
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        repo_root = temp_dir / "project"
        repo_root.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init"], cwd=repo_root, capture_output=True, text=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_root, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_root, check=True)
        return repo_root

    def run_check(self, repo_root: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CHECK_SCRIPT), "--project-root", str(repo_root), *extra_args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

    def _write_and_stage(self, repo_root: Path, relative_path: str, text: str) -> Path:
        file_path = repo_root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(text, encoding="utf-8")
        subprocess.run(["git", "add", str(file_path.relative_to(repo_root))], cwd=repo_root, check=True)
        return file_path

    def _assert_blocked(self, repo_root: Path, expected_issue: str) -> subprocess.CompletedProcess[str]:
        result = self.run_check(repo_root)
        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn(expected_issue, result.stdout)
        return result

    def test_tracked_process_file_is_blocked(self) -> None:
        repo_root = self.make_repo()
        forbidden = repo_root / "00-项目包" / "04-过程文件" / "trace.md"
        forbidden.parent.mkdir(parents=True, exist_ok=True)
        forbidden.write_text("tracked", encoding="utf-8")
        subprocess.run(["git", "add", str(forbidden.relative_to(repo_root))], cwd=repo_root, check=True)
        subprocess.run(["git", "commit", "-m", "track process file"], cwd=repo_root, capture_output=True, text=True, check=True)

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("00-项目包/04-过程文件/trace.md", result.stdout)

    def test_staged_process_file_is_blocked(self) -> None:
        repo_root = self.make_repo()
        forbidden = repo_root / "01-模块执行包" / "模块A" / "04-过程文件" / "trace.md"
        forbidden.parent.mkdir(parents=True, exist_ok=True)
        forbidden.write_text("staged", encoding="utf-8")
        subprocess.run(["git", "add", str(forbidden.relative_to(repo_root))], cwd=repo_root, check=True)

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("01-模块执行包/模块A/04-过程文件/trace.md", result.stdout)

    def test_local_untracked_process_file_is_allowed(self) -> None:
        repo_root = self.make_repo()
        forbidden = repo_root / "00-项目包" / "04-过程文件" / "trace.md"
        forbidden.parent.mkdir(parents=True, exist_ok=True)
        forbidden.write_text("untracked", encoding="utf-8")

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_p0_01_missing_markdown_relative_target_is_blocked(self) -> None:
        repo_root = self.make_repo()
        source = self._write_and_stage(
            repo_root,
            "00-项目包/02-工程交接/README.md",
            "\n".join(
                [
                    "# 工程交接正式索引",
                    "",
                    "- [缺失的本地目标](./missing-relative-target.md)",
                ]
            )
            + "\n",
        )

        result = self._assert_blocked(repo_root, "missing relative target")

        self.assertIn(str(source.relative_to(repo_root)), result.stdout)
        self.assertIn("missing-relative-target.md", result.stdout)

    def test_p0_01_missing_html_href_target_is_blocked(self) -> None:
        repo_root = self.make_repo()
        source = self._write_and_stage(
            repo_root,
            "80-完整提交包/02-原型索引/00-原型入口.md",
            "\n".join(
                [
                    "# 原型入口",
                    "",
                    '<a href="./missing-prototype-entry.html">missing</a>',
                ]
            )
            + "\n",
        )

        result = self._assert_blocked(repo_root, "missing html href target")

        self.assertIn(str(source.relative_to(repo_root)), result.stdout)
        self.assertIn("missing-prototype-entry.html", result.stdout)

    def test_p0_01_javascript_route_is_ignored(self) -> None:
        repo_root = self.make_repo()
        self._write_and_stage(
            repo_root,
            "00-项目包/02-工程交接/README.md",
            "\n".join(
                [
                    "# 工程交接正式索引",
                    "",
                    "- [跳转](javascript:void(0))",
                ]
            )
            + "\n",
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_p0_01_missing_formal_index_target_is_blocked(self) -> None:
        repo_root = self.make_repo()
        source = self._write_and_stage(
            repo_root,
            "80-完整提交包/00-提交说明.md",
            "\n".join(
                [
                    "# 提交说明",
                    "",
                    "- [PRD索引](01-合并PRD/00-PRD索引.md)",
                ]
            )
            + "\n",
        )

        result = self._assert_blocked(repo_root, "missing formal index target")

        self.assertIn(str(source.relative_to(repo_root)), result.stdout)
        self.assertIn("01-合并PRD/00-PRD索引.md", result.stdout)

    def test_p0_01_display_layer_to_formal_target_mapping_break_is_blocked(self) -> None:
        repo_root = self.make_repo()
        source = self._write_and_stage(
            repo_root,
            "80-完整提交包/00-提交说明.md",
            "\n".join(
                [
                    "# 提交说明",
                    "",
                    "- [PRD阅读层](01-合并PRD/01-合并PRD阅读层.md)",
                ]
            )
            + "\n",
        )

        result = self._assert_blocked(repo_root, "mapping contract blocked")

        self.assertIn(str(source.relative_to(repo_root)), result.stdout)
        self.assertIn("01-合并PRD/01-合并PRD阅读层.md", result.stdout)

    def test_explicit_file_list_blocks_forbidden_paths(self) -> None:
        repo_root = self.make_repo()

        result = self.run_check(repo_root, "--path", "docs/01-跨模块补充资料/local/note.md")

        self.assertEqual(result.returncode, 1)
        self.assertIn("docs/01-跨模块补充资料/local/note.md", result.stdout)

    def test_tracked_runtime_metadata_is_blocked(self) -> None:
        repo_root = self.make_repo()
        forbidden = repo_root / ".ai-team" / "runtime.json"
        forbidden.parent.mkdir(parents=True, exist_ok=True)
        forbidden.write_text('{"bundle_root":"local"}', encoding="utf-8")
        subprocess.run(["git", "add", str(forbidden.relative_to(repo_root))], cwd=repo_root, check=True)
        subprocess.run(["git", "commit", "-m", "track runtime metadata"], cwd=repo_root, capture_output=True, text=True, check=True)

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn(".ai-team/runtime.json", result.stdout)

    def test_explicit_runtime_inspection_link_is_blocked(self) -> None:
        repo_root = self.make_repo()

        result = self.run_check(repo_root, "--path", ".ai-team-inspect/manifest.json")

        self.assertEqual(result.returncode, 1)
        self.assertIn(".ai-team-inspect/manifest.json", result.stdout)

    def test_fake_downstream_link_is_blocked(self) -> None:
        repo_root = self.make_repo()
        prd = repo_root / "01-模块执行包" / "模块A" / "01-PRD" / "01-模块PRD.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text(
            "\n".join(
                [
                    "# 模块PRD",
                    "",
                    "#### 12. 下游文档列表",
                    "",
                    "- canonical backlink: [BE 交接](../02-工程交接/be_truth.md)",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", str(prd.relative_to(repo_root))], cwd=repo_root, check=True)

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("fake downstream link", result.stdout)
        self.assertIn("01-模块执行包/模块A/02-工程交接/be_truth.md", result.stdout)

    def test_canonical_backlink_table_field_without_markdown_link_is_blocked_when_target_is_missing(self) -> None:
        repo_root = self.make_repo()
        handoff = repo_root / "01-模块执行包" / "模块A" / "02-工程交接" / "be_truth.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(
            "\n".join(
                [
                    "# BE 真源",
                    "",
                    "| 字段 | 填写内容 |",
                    "|------|------|",
                    "| canonical backlink | `01-模块执行包/模块A/01-PRD/不存在的模块PRD.md` |",
                    "| linked_prd_source | `01-模块执行包/模块A/01-PRD/不存在的模块PRD.md` |",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", str(handoff.relative_to(repo_root))], cwd=repo_root, check=True)

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("missing canonical backlink target", result.stdout)
        self.assertIn("missing linked_prd_source target", result.stdout)

    def test_legacy_linked_prd_header_to_display_layer_is_blocked(self) -> None:
        repo_root = self.make_repo()
        handoff = repo_root / "01-模块执行包" / "模块A" / "02-工程交接" / "be_truth.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(
            "\n".join(
                [
                    "Owner: `BE`",
                    "Status: `active`",
                    "Version: `v1`",
                    "Linked PRD: `80-完整提交包/01-合并PRD/00-PRD索引.md`",
                    "",
                    "truth: service contract",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", str(handoff.relative_to(repo_root))], cwd=repo_root, check=True)

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("display-layer linked-truth conflict", result.stdout)
        self.assertIn("80-完整提交包/01-合并PRD/00-PRD索引.md", result.stdout)

    def test_machine_local_absolute_path_in_truth_doc_is_blocked(self) -> None:
        repo_root = self.make_repo()
        handoff = repo_root / "01-模块执行包" / "模块A" / "02-工程交接" / "be_truth.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(
            "\n".join(
                [
                    "Owner: `BE`",
                    "Status: `active`",
                    "Version: `v1`",
                    "Linked PRD: `/Users/mac/Documents/Playground-English/80-完整提交包/00-提交说明.md`",
                    "",
                    "truth: service contract",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", str(handoff.relative_to(repo_root))], cwd=repo_root, check=True)

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("machine-local absolute path", result.stdout)
        self.assertIn("/Users/mac/Documents/Playground-English/80-完整提交包/00-提交说明.md", result.stdout)

    def test_plain_text_machine_local_absolute_path_in_linked_prd_field_is_blocked_even_when_target_exists(self) -> None:
        repo_root = self.make_repo()
        target = repo_root / "01-模块执行包" / "模块A" / "01-PRD" / "01-模块PRD.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# 模块PRD\n", encoding="utf-8")
        handoff = repo_root / "01-模块执行包" / "模块A" / "02-工程交接" / "be_truth.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(
            "\n".join(
                [
                    "Owner: `BE`",
                    "Status: `active`",
                    "Version: `v1`",
                    f"Linked PRD: {target}",
                    "",
                    "truth: service contract",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "add", str(target.relative_to(repo_root)), str(handoff.relative_to(repo_root))],
            cwd=repo_root,
            check=True,
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("machine-local absolute path", result.stdout)
        self.assertIn(str(target), result.stdout)

    def test_machine_local_absolute_path_in_review_record_is_allowed(self) -> None:
        repo_root = self.make_repo()
        review_record = repo_root / "80-完整提交包" / "03-合并评审记录" / "30-结果-AI深审记录.md"
        review_record.parent.mkdir(parents=True, exist_ok=True)
        review_record.write_text(
            "\n".join(
                [
                    "# AI深审记录",
                    "",
                    "证据引用：`/Users/mac/Documents/Playground-English/80-完整提交包/00-提交说明.md`",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", str(review_record.relative_to(repo_root))], cwd=repo_root, check=True)

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_starter_handoff_contradiction_is_blocked_when_gate_b_ready(self) -> None:
        repo_root = self.make_repo()
        status = repo_root / "80-完整提交包" / "00-提交状态.json"
        status.parent.mkdir(parents=True, exist_ok=True)
        status.write_text(
            '{\n'
            '  "status": {\n'
            '    "engineering_handoff_required": true,\n'
            '    "engineering_handoff_ready": true\n'
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        readme = repo_root / "01-模块执行包" / "模块A" / "02-工程交接" / "README.md"
        readme.parent.mkdir(parents=True, exist_ok=True)
        readme.write_text(
            "# 工程交接目录\n\n仅提供目录入口，不代表已完成工程交接。\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "add", str(status.relative_to(repo_root)), str(readme.relative_to(repo_root))],
            cwd=repo_root,
            check=True,
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("starter-handoff contradiction", result.stdout)
        self.assertIn("01-模块执行包/模块A/02-工程交接/README.md", result.stdout)

    def test_starter_handoff_contradiction_is_blocked_when_handoff_required_even_if_not_ready(self) -> None:
        repo_root = self.make_repo()
        status = repo_root / "80-完整提交包" / "00-提交状态.json"
        status.parent.mkdir(parents=True, exist_ok=True)
        status.write_text(
            '{\n'
            '  "status": {\n'
            '    "engineering_handoff_required": true,\n'
            '    "engineering_handoff_ready": false\n'
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        readme = repo_root / "01-模块执行包" / "模块A" / "02-工程交接" / "README.md"
        readme.parent.mkdir(parents=True, exist_ok=True)
        readme.write_text(
            "# 工程交接目录\n\n仅提供目录入口，不代表已完成工程交接。\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "add", str(status.relative_to(repo_root)), str(readme.relative_to(repo_root))],
            cwd=repo_root,
            check=True,
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("starter-handoff contradiction", result.stdout)

    def test_starter_handoff_contradiction_is_blocked_even_when_status_json_is_malformed(self) -> None:
        repo_root = self.make_repo()
        status = repo_root / "80-完整提交包" / "00-提交状态.json"
        status.parent.mkdir(parents=True, exist_ok=True)
        status.write_text("{ malformed\n", encoding="utf-8")
        readme = repo_root / "01-模块执行包" / "模块A" / "02-工程交接" / "README.md"
        readme.parent.mkdir(parents=True, exist_ok=True)
        readme.write_text(
            "# 工程交接目录\n\n仅提供目录入口，不代表已完成工程交接。\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "add", str(status.relative_to(repo_root)), str(readme.relative_to(repo_root))],
            cwd=repo_root,
            check=True,
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("starter-handoff contradiction", result.stdout)

    def test_starter_handoff_contradiction_is_blocked_for_legacy_starter_keyword(self) -> None:
        repo_root = self.make_repo()
        status = repo_root / "80-完整提交包" / "00-提交状态.json"
        status.parent.mkdir(parents=True, exist_ok=True)
        status.write_text(
            '{\n'
            '  "status": {\n'
            '    "engineering_handoff_required": true,\n'
            '    "engineering_handoff_ready": true\n'
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        readme = repo_root / "01-模块执行包" / "模块A" / "02-工程交接" / "README.md"
        readme.parent.mkdir(parents=True, exist_ok=True)
        readme.write_text(
            "# 工程交接目录\n\nThis starter shell was never upgraded into a formal handoff index.\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "add", str(status.relative_to(repo_root)), str(readme.relative_to(repo_root))],
            cwd=repo_root,
            check=True,
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("starter-handoff contradiction", result.stdout)
        self.assertIn("01-模块执行包/模块A/02-工程交接/README.md", result.stdout)

    def test_formal_handoff_index_is_not_misclassified_for_mentioning_old_starter_wording(self) -> None:
        repo_root = self.make_repo()
        status = repo_root / "80-完整提交包" / "00-提交状态.json"
        status.parent.mkdir(parents=True, exist_ok=True)
        status.write_text(
            '{\n'
            '  "status": {\n'
            '    "engineering_handoff_required": true,\n'
            '    "engineering_handoff_ready": true\n'
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        readme = repo_root / "01-模块执行包" / "模块A" / "02-工程交接" / "README.md"
        readme.parent.mkdir(parents=True, exist_ok=True)
        readme.write_text(
            "# 模块工程交接正式目录索引\n\n- 本 README 是正式目录索引，不再使用“未完成工程交接”的 starter 口径\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "add", str(status.relative_to(repo_root)), str(readme.relative_to(repo_root))],
            cwd=repo_root,
            check=True,
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 0, msg=result.stdout)
        self.assertNotIn("starter-handoff contradiction", result.stdout)

    def test_project_level_formal_handoff_index_is_not_misclassified_for_retired_starter_note(self) -> None:
        repo_root = self.make_repo()
        status = repo_root / "80-完整提交包" / "00-提交状态.json"
        status.parent.mkdir(parents=True, exist_ok=True)
        status.write_text(
            '{\n'
            '  "status": {\n'
            '    "engineering_handoff_required": true,\n'
            '    "engineering_handoff_ready": true\n'
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        readme = repo_root / "00-项目包" / "02-工程交接" / "README.md"
        readme.parent.mkdir(parents=True, exist_ok=True)
        readme.write_text(
            "# 项目工程交接正式目录索引\n\n- 本 README 已升级为正式目录索引，不再使用 starter 占位文案。\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "add", str(status.relative_to(repo_root)), str(readme.relative_to(repo_root))],
            cwd=repo_root,
            check=True,
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 0, msg=result.stdout)
        self.assertNotIn("starter-handoff contradiction", result.stdout)

    def test_display_layer_linked_truth_conflict_is_blocked(self) -> None:
        repo_root = self.make_repo()
        handoff = repo_root / "01-模块执行包" / "模块A" / "02-工程交接" / "be_truth.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(
            "\n".join(
                [
                    "---",
                    "linked_prd_source: 80-完整提交包/01-合并PRD/01-合并PRD阅读层.md",
                    "---",
                    "# BE 真源",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", str(handoff.relative_to(repo_root))], cwd=repo_root, check=True)

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("display-layer linked-truth conflict", result.stdout)
        self.assertIn("80-完整提交包/01-合并PRD/01-合并PRD阅读层.md", result.stdout)

    def test_display_layer_canonical_backlink_conflict_is_blocked(self) -> None:
        repo_root = self.make_repo()
        handoff = repo_root / "01-模块执行包" / "模块A" / "02-工程交接" / "be_truth.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(
            "\n".join(
                [
                    "| 字段 | 填写内容 |",
                    "|------|------|",
                    "| canonical backlink | `80-完整提交包/01-合并PRD/01-合并PRD阅读层.md` |",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        reading_layer = repo_root / "80-完整提交包" / "01-合并PRD" / "01-合并PRD阅读层.md"
        reading_layer.parent.mkdir(parents=True, exist_ok=True)
        reading_layer.write_text("# PRD阅读层\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", str(handoff.relative_to(repo_root)), str(reading_layer.relative_to(repo_root))],
            cwd=repo_root,
            check=True,
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("display-layer canonical-backlink conflict", result.stdout)

    def test_display_layer_downstream_link_conflict_is_blocked(self) -> None:
        repo_root = self.make_repo()
        prd = repo_root / "01-模块执行包" / "模块A" / "01-PRD" / "01-模块PRD.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text(
            "\n".join(
                [
                    "# 模块PRD",
                    "",
                    "#### 12. 下游文档列表",
                    "",
                    "- [阅读层入口](../../../80-完整提交包/01-合并PRD/01-合并PRD阅读层.md)",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        reading_layer = repo_root / "80-完整提交包" / "01-合并PRD" / "01-合并PRD阅读层.md"
        reading_layer.parent.mkdir(parents=True, exist_ok=True)
        reading_layer.write_text("# PRD阅读层\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", str(prd.relative_to(repo_root)), str(reading_layer.relative_to(repo_root))],
            cwd=repo_root,
            check=True,
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("display-layer downstream-link conflict", result.stdout)

    def test_display_layer_downstream_code_span_conflict_is_blocked(self) -> None:
        repo_root = self.make_repo()
        prd = repo_root / "01-模块执行包" / "模块A" / "01-PRD" / "01-模块PRD.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text(
            "\n".join(
                [
                    "# 模块PRD",
                    "",
                    "#### 12. 下游文档列表",
                    "",
                    "- `80-完整提交包/01-合并PRD/01-合并PRD阅读层.md`",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        reading_layer = repo_root / "80-完整提交包" / "01-合并PRD" / "01-合并PRD阅读层.md"
        reading_layer.parent.mkdir(parents=True, exist_ok=True)
        reading_layer.write_text("# PRD阅读层\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", str(prd.relative_to(repo_root)), str(reading_layer.relative_to(repo_root))],
            cwd=repo_root,
            check=True,
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("display-layer downstream-link conflict", result.stdout)

    def test_display_layer_markdown_link_conflict_is_blocked_anywhere_in_truth_doc(self) -> None:
        repo_root = self.make_repo()
        handoff = repo_root / "01-模块执行包" / "模块A" / "02-工程交接" / "be_truth.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(
            "\n".join(
                [
                    "# BE 真源",
                    "",
                    "See also: [阅读层](../../../80-完整提交包/01-合并PRD/01-合并PRD阅读层.md)",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        reading_layer = repo_root / "80-完整提交包" / "01-合并PRD" / "01-合并PRD阅读层.md"
        reading_layer.parent.mkdir(parents=True, exist_ok=True)
        reading_layer.write_text("# PRD阅读层\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", str(handoff.relative_to(repo_root)), str(reading_layer.relative_to(repo_root))],
            cwd=repo_root,
            check=True,
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("display-layer markdown-link conflict", result.stdout)

    def test_root_relative_display_layer_markdown_link_conflict_is_blocked(self) -> None:
        repo_root = self.make_repo()
        handoff = repo_root / "01-模块执行包" / "模块A" / "02-工程交接" / "be_truth.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(
            "\n".join(
                [
                    "# BE 真源",
                    "",
                    "See also: [阅读层](80-完整提交包/01-合并PRD/01-合并PRD阅读层.md)",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        result = self.run_check(repo_root, "--path", "01-模块执行包/模块A/02-工程交接/be_truth.md")

        self.assertEqual(result.returncode, 1)
        self.assertIn("display-layer markdown-link conflict", result.stdout)
        self.assertIn("80-完整提交包/01-合并PRD/01-合并PRD阅读层.md", result.stdout)

    def test_display_layer_truth_metadata_conflict_is_blocked(self) -> None:
        repo_root = self.make_repo()
        reading_layer = repo_root / "80-完整提交包" / "01-合并PRD" / "01-合并PRD阅读层.md"
        reading_layer.parent.mkdir(parents=True, exist_ok=True)
        reading_layer.write_text(
            "\n".join(
                [
                    "# PRD阅读层",
                    "",
                    "Owner: `PM`",
                    "Status: `active`",
                    "Version: `v0.3.3`",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", str(reading_layer.relative_to(repo_root))], cwd=repo_root, check=True)

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("display-layer truth-metadata conflict", result.stdout)

    def test_retired_truth_without_marker_is_blocked(self) -> None:
        repo_root = self.make_repo()
        retired_doc = repo_root / "01-模块执行包" / "模块A" / "02-工程交接" / "be_truth_legacy.md"
        retired_doc.parent.mkdir(parents=True, exist_ok=True)
        retired_doc.write_text(
            "\n".join(
                [
                    "---",
                    "truth_status: retired",
                    "replaced_by: 01-模块执行包/模块A/02-工程交接/be_truth_current.md",
                    "---",
                    "# 历史 BE 真源",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", str(retired_doc.relative_to(repo_root))], cwd=repo_root, check=True)

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("retired-truth ambiguity", result.stdout)
        self.assertIn("01-模块执行包/模块A/02-工程交接/be_truth_legacy.md", result.stdout)

    def test_obsolete_truth_without_marker_is_blocked(self) -> None:
        repo_root = self.make_repo()
        obsolete_doc = repo_root / "01-模块执行包" / "模块A" / "02-工程交接" / "be_truth_obsolete.md"
        obsolete_doc.parent.mkdir(parents=True, exist_ok=True)
        obsolete_doc.write_text(
            "\n".join(
                [
                    "---",
                    "Status: obsolete",
                    "---",
                    "# 旧 BE 真源",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", str(obsolete_doc.relative_to(repo_root))], cwd=repo_root, check=True)

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("retired-truth ambiguity", result.stdout)
        self.assertIn("be_truth_obsolete.md", result.stdout)

    def test_sibling_dual_active_truth_sources_without_retirement_declaration_are_blocked(self) -> None:
        repo_root = self.make_repo()
        handoff_dir = repo_root / "01-模块执行包" / "模块A" / "02-工程交接"
        handoff_dir.mkdir(parents=True, exist_ok=True)
        for filename in ("be_truth_a.md", "be_truth_b.md"):
            (handoff_dir / filename).write_text(
                "\n".join(
                    [
                        "Owner: `BE`",
                        "Status: `approved`",
                        "Version: `v1`",
                        "linked_prd_source: `01-模块执行包/模块A/01-PRD/01-模块PRD.md`",
                        "",
                        "# BE 真源",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
        prd = repo_root / "01-模块执行包" / "模块A" / "01-PRD" / "01-模块PRD.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text("# 模块PRD\n", encoding="utf-8")
        subprocess.run(
            [
                "git",
                "add",
                str((handoff_dir / "be_truth_a.md").relative_to(repo_root)),
                str((handoff_dir / "be_truth_b.md").relative_to(repo_root)),
                str(prd.relative_to(repo_root)),
            ],
            cwd=repo_root,
            check=True,
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("dual-active truth siblings", result.stdout)
        self.assertIn("be_truth_a.md", result.stdout)
        self.assertIn("be_truth_b.md", result.stdout)

    def test_dual_active_truth_sources_allow_distinct_owner_slots(self) -> None:
        repo_root = self.make_repo()
        handoff_dir = repo_root / "01-模块执行包" / "模块A" / "02-工程交接"
        handoff_dir.mkdir(parents=True, exist_ok=True)
        (handoff_dir / "be_truth.md").write_text(
            "\n".join(
                [
                    "Owner: `BE`",
                    "Status: `approved`",
                    "linked_prd_source: `01-模块执行包/模块A/01-PRD/01-模块PRD.md`",
                    "",
                    "# BE 真源",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (handoff_dir / "qa_truth.md").write_text(
            "\n".join(
                [
                    "Owner: `QA`",
                    "Status: `approved`",
                    "linked_prd_source: `01-模块执行包/模块A/01-PRD/01-模块PRD.md`",
                    "",
                    "# QA 真源",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        prd = repo_root / "01-模块执行包" / "模块A" / "01-PRD" / "01-模块PRD.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text("# 模块PRD\n", encoding="utf-8")
        subprocess.run(
            [
                "git",
                "add",
                str((handoff_dir / "be_truth.md").relative_to(repo_root)),
                str((handoff_dir / "qa_truth.md").relative_to(repo_root)),
                str(prd.relative_to(repo_root)),
            ],
            cwd=repo_root,
            check=True,
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_active_truth_version_and_reading_layer_naming_boundary_are_blocked(self) -> None:
        repo_root = self.make_repo()
        active_truth = repo_root / "01-模块执行包" / "模块A" / "02-工程交接" / "README.md"
        active_truth.parent.mkdir(parents=True, exist_ok=True)
        active_truth.write_text(
            "# 工程交接正式索引\n\nVersion: v0.3.1\n",
            encoding="utf-8",
        )
        reading_layer = repo_root / "80-完整提交包" / "01-合并PRD" / "01-合并PRD阅读层.md"
        reading_layer.parent.mkdir(parents=True, exist_ok=True)
        reading_layer.write_text(
            "# 合并PRD\n\n这是唯一正式合并 PRD。\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "add", str(active_truth.relative_to(repo_root)), str(reading_layer.relative_to(repo_root))],
            cwd=repo_root,
            check=True,
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("active truth-source version label", result.stdout)
        self.assertIn("reading-layer naming boundary", result.stdout)

    def test_prd_reading_entry_and_diagram_quick_index_are_required(self) -> None:
        repo_root = self.make_repo()
        prd_index = repo_root / "80-完整提交包" / "01-合并PRD" / "00-PRD索引.md"
        prd_index.parent.mkdir(parents=True, exist_ok=True)
        prd_index.write_text(
            "# PRD阅读入口\n\n## 人读流程图速查\n\n- 项目整体业务闭环图：`01-合并PRD阅读层.md`\n",
            encoding="utf-8",
        )
        reading_layer = repo_root / "80-完整提交包" / "01-合并PRD" / "01-合并PRD阅读层.md"
        reading_layer.write_text(
            "# PRD阅读层\n\n## 人读流程图速查\n\n- 项目整体业务闭环图\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "add", str(prd_index.relative_to(repo_root)), str(reading_layer.relative_to(repo_root))],
            cwd=repo_root,
            check=True,
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("reading-layer entry link missing", result.stdout)
        self.assertIn("diagram quick index link missing", result.stdout)

    def test_diagram_quick_index_requires_expected_navigation_links(self) -> None:
        repo_root = self.make_repo()
        prd_index = repo_root / "80-完整提交包" / "01-合并PRD" / "00-PRD索引.md"
        prd_index.parent.mkdir(parents=True, exist_ok=True)
        prd_index.write_text(
            "# PRD阅读入口\n\n- [PRD阅读层](01-合并PRD阅读层.md)\n",
            encoding="utf-8",
        )
        reading_layer = repo_root / "80-完整提交包" / "01-合并PRD" / "01-合并PRD阅读层.md"
        reading_layer.write_text(
            "# PRD阅读层\n\n## 人读流程图速查\n\n- [foo](other.md)\n",
            encoding="utf-8",
        )
        other = repo_root / "80-完整提交包" / "01-合并PRD" / "other.md"
        other.write_text("# other\n", encoding="utf-8")
        subprocess.run(
            [
                "git",
                "add",
                str(prd_index.relative_to(repo_root)),
                str(reading_layer.relative_to(repo_root)),
                str(other.relative_to(repo_root)),
            ],
            cwd=repo_root,
            check=True,
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("diagram quick index link missing", result.stdout)

    def test_diagram_quick_index_requires_anchor_navigation_targets(self) -> None:
        repo_root = self.make_repo()
        prd_index = repo_root / "80-完整提交包" / "01-合并PRD" / "00-PRD索引.md"
        prd_index.parent.mkdir(parents=True, exist_ok=True)
        prd_index.write_text(
            "# PRD阅读入口\n\n- [PRD阅读层](01-合并PRD阅读层.md)\n",
            encoding="utf-8",
        )
        reading_layer = repo_root / "80-完整提交包" / "01-合并PRD" / "01-合并PRD阅读层.md"
        reading_layer.write_text(
            "# PRD阅读层\n\n## 人读流程图速查\n\n- [项目整体业务闭环图](other.md)\n",
            encoding="utf-8",
        )
        other = repo_root / "80-完整提交包" / "01-合并PRD" / "other.md"
        other.write_text("# other\n", encoding="utf-8")
        subprocess.run(
            [
                "git",
                "add",
                str(prd_index.relative_to(repo_root)),
                str(reading_layer.relative_to(repo_root)),
                str(other.relative_to(repo_root)),
            ],
            cwd=repo_root,
            check=True,
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("diagram quick index link missing", result.stdout)

    def test_diagram_quick_index_requires_existing_anchor_targets(self) -> None:
        repo_root = self.make_repo()
        prd_index = repo_root / "80-完整提交包" / "01-合并PRD" / "00-PRD索引.md"
        prd_index.parent.mkdir(parents=True, exist_ok=True)
        prd_index.write_text(
            "# PRD阅读入口\n\n- [PRD阅读层](01-合并PRD阅读层.md)\n",
            encoding="utf-8",
        )
        reading_layer = repo_root / "80-完整提交包" / "01-合并PRD" / "01-合并PRD阅读层.md"
        reading_layer.write_text(
            "# PRD阅读层\n\n## 人读流程图速查\n\n- [项目整体业务闭环图](other.md#does-not-exist)\n",
            encoding="utf-8",
        )
        other = repo_root / "80-完整提交包" / "01-合并PRD" / "other.md"
        other.write_text("## 已存在的别名\n", encoding="utf-8")
        subprocess.run(
            [
                "git",
                "add",
                str(prd_index.relative_to(repo_root)),
                str(reading_layer.relative_to(repo_root)),
                str(other.relative_to(repo_root)),
            ],
            cwd=repo_root,
            check=True,
        )

        result = self.run_check(repo_root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("diagram quick index link missing", result.stdout)

    def test_publish_flow_requires_check_publish_boundary_script(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ai-team-publish-template-") as tmp:
            repo_root = Path(tmp)
            skill_root = repo_root / "install" / "default_bundle" / "org_skills" / "03-submission-status-governance"
            template_root = repo_root / "install" / "default_bundle" / "assets" / "project_skeleton" / "00-项目包模板"

            (skill_root / "scripts").mkdir(parents=True)
            (skill_root / "references").mkdir(parents=True)
            (template_root / "scripts").mkdir(parents=True)
            (template_root / "80-完整提交包").mkdir(parents=True)

            (skill_root / "scripts" / "sync_submission_status.py").write_text("sync-source", encoding="utf-8")
            (skill_root / "scripts" / "check_submission_consistency.py").write_text("check-source", encoding="utf-8")
            (skill_root / "references" / "00-提交状态.example.json").write_text('{"version": 1}', encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(PUBLISH_SCRIPT), "--repo-root", str(repo_root)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("check_publish_boundary.py", result.stderr)


if __name__ == "__main__":
    unittest.main()
