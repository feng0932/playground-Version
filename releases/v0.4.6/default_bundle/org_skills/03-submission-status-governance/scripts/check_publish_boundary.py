#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


FORBIDDEN_PREFIXES = (
    ".ai-team/",
    ".ai-team-inspect/",
    "00-项目包/04-过程文件/",
    "docs/01-跨模块补充资料/local/",
)

READING_LAYER_PATH = "80-完整提交包/01-合并PRD/01-合并PRD阅读层.md"
PRD_INDEX_PATH = "80-完整提交包/01-合并PRD/00-PRD索引.md"
HANDOFF_README_SUFFIX = "02-工程交接/README.md"
MISLEADING_HANDOFF_PHRASES = (
    "不代表已完成工程交接",
    "仅提供目录入口",
    "占位",
)
LEGACY_VERSION_PATTERNS = (
    re.compile(r"(?mi)^Version\s*:\s*(v\d+\.\d+\.\d+)\s*$"),
    re.compile(r"(?mi)^版本\s*[:：]\s*(v\d+\.\d+\.\d+)\s*$"),
)
CURRENT_VERSION_MARKERS = (
    "当前适用版本",
    "active_version",
    "active truth",
    "当前 active",
)
DISPLAY_LAYER_PREFIX = "80-完整提交包/"
STATUS_TRUTH_PATH = "80-完整提交包/00-提交状态.json"
OUTWARD_ENTRY_PATHS = {
    "80-完整提交包/00-提交说明.md",
    PRD_INDEX_PATH,
    READING_LAYER_PATH,
    "80-完整提交包/02-原型索引/00-原型入口.md",
}
QUICK_INDEX_LABEL_KEYWORDS = (
    "项目整体业务闭环图",
    "模块关系图",
    "分模块主流程图",
    "C端主旅程图",
    "后台支撑旅程图",
)
ROOT_RELATIVE_PREFIXES = {
    ".ai-team",
    ".ai-team-inspect",
    "00-项目包",
    "01-模块执行包",
    "80-完整提交包",
    "docs",
    "assets",
    "scripts",
}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check that local-only process files are not entering remote git scope.")
    parser.add_argument(
        "--project-root",
        help="Real project root. Defaults to current working directory.",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        dest="paths",
        help="Explicit relative or absolute path to validate in addition to tracked and staged git paths.",
    )
    return parser.parse_args(argv)


def project_root_from_args(project_root: str | None) -> Path:
    return Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()


def normalize_slashes(raw_path: str) -> str:
    normalized = raw_path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    while normalized.startswith("/"):
        normalized = normalized[1:]
    return normalized


def normalize_path(raw_path: str, project_root: Path) -> str:
    path = Path(raw_path)
    if path.is_absolute():
        try:
            path = path.resolve().relative_to(project_root)
        except ValueError:
            path = Path(raw_path)
    return normalize_slashes(path.as_posix())


def is_forbidden(path: str) -> bool:
    normalized = normalize_slashes(path)
    if any(_matches_forbidden_prefix(normalized, prefix) for prefix in FORBIDDEN_PREFIXES):
        return True
    parts = normalized.split("/")
    return len(parts) >= 4 and parts[0] == "01-模块执行包" and parts[2] == "04-过程文件"


def _matches_forbidden_prefix(normalized: str, prefix: str) -> bool:
    exact = prefix.rstrip("/")
    return normalized == exact or normalized.startswith(prefix)


def run_git_paths(project_root: Path, *args: str) -> list[str]:
    result = subprocess.run(
        ["git", "-c", "core.quotePath=false", *args],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def collect_candidate_paths(project_root: Path, explicit_paths: list[str]) -> list[str]:
    tracked = run_git_paths(project_root, "ls-files")
    staged = run_git_paths(project_root, "diff", "--cached", "--name-only")
    explicit = [normalize_path(raw_path, project_root) for raw_path in explicit_paths]
    mandatory = [READING_LAYER_PATH] if (project_root / READING_LAYER_PATH).exists() else []
    return sorted({path for path in [*tracked, *staged, *explicit, *mandatory] if path})


def load_status_payload(project_root: Path) -> dict[str, object]:
    status_path = project_root / "80-完整提交包" / "00-提交状态.json"
    if not status_path.exists():
        return {}
    try:
        return json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_link_fragment(raw_target: str) -> str:
    return raw_target.split("#", 1)[0].split("?", 1)[0].strip()


def _should_ignore_reference_target(raw_target: str) -> bool:
    target = _strip_link_fragment(raw_target.strip().strip("`").strip('"').strip("'"))
    if not target:
        return True
    lowered = target.lower()
    return target.startswith("#") or lowered.startswith(("http://", "https://", "mailto:", "javascript:"))


def is_truth_source_path(path: str) -> bool:
    parts = path.split("/")
    if len(parts) >= 3 and parts[0] == "00-项目包" and parts[1] == "02-工程交接":
        return True
    if len(parts) >= 4 and parts[0] == "01-模块执行包" and parts[2] in {"01-PRD", "02-工程交接"}:
        return True
    return False


def markdown_links(text: str) -> list[tuple[str, str]]:
    return [(match.group(1).strip(), match.group(2).strip()) for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text)]


def extract_mermaid_blocks(text: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"```mermaid\s*\n([\s\S]*?)\n```", text)]


def reading_layer_flowchart_issues(text: str) -> list[str]:
    blocks = extract_mermaid_blocks(text)
    if not blocks:
        return ["reading-layer actual flowchart missing"]
    issues: list[str] = []
    placeholder_terms = ("待补", "待按", "回链见模块真源", "A -> B -> C")
    for block in blocks:
        compact = re.sub(r"\s+", " ", block)
        if not block or any(term in compact for term in placeholder_terms):
            issues.append("reading-layer actual flowchart missing")
        elif "-->" not in block or not re.search(r"\[[^\]]+\]", block) or not re.search(r"(?m)^\s*flowchart\s+(TD|LR|RL|BT)\b", block):
            issues.append("reading-layer actual flowchart missing")
        elif not any(term in block for term in ("模块", "页面", "主流程")):
            issues.append("reading-layer actual flowchart missing")
    return issues


def has_reading_layer_truth_claim(text: str) -> bool:
    protected = ("不得写成", "不能写成", "禁止写成", "不能反向", "不得反向")
    for line in text.splitlines():
        if ("唯一正式合并 PRD" in line or "反向作为模块真源" in line) and not any(term in line for term in protected):
            return True
    return False


def markdown_link_targets(text: str) -> list[str]:
    return [target for _, target in markdown_links(text)]


def extract_section(text: str, heading_keyword: str) -> str:
    lines = text.splitlines()
    start_index: int | None = None
    start_level: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        if heading_keyword in stripped:
            start_index = index + 1
            start_level = len(stripped) - len(stripped.lstrip("#"))
            break
    if start_index is None or start_level is None:
        return ""

    collected: list[str] = []
    for line in lines[start_index:]:
        stripped = line.strip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            if level <= start_level:
                break
        collected.append(line)
    return "\n".join(collected)


def markdown_heading_anchors(text: str) -> set[str]:
    anchors: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        heading = stripped.lstrip("#").strip().lower()
        if not heading:
            continue
        slug = re.sub(r"[^\w\u4e00-\u9fff\- ]", "", heading)
        slug = re.sub(r"\s+", "-", slug).strip("-")
        slug = re.sub(r"-{2,}", "-", slug)
        anchors.add(f"#{slug}")
    return anchors


def local_link_targets(text: str, source_path: str, project_root: Path) -> list[str]:
    targets: list[str] = []
    seen: set[str] = set()
    for raw_target in markdown_link_targets(text):
        if _should_ignore_reference_target(raw_target):
            continue
        for normalized in resolve_reference(raw_target, source_path, project_root):
            if normalized in seen:
                continue
            seen.add(normalized)
            targets.append(normalized)
    return targets


def html_href_targets(text: str) -> list[str]:
    return [
        match.group(2).strip()
        for match in re.finditer(r'<a\b[^>]*\bhref\s*=\s*(["\'])(.*?)\1', text, re.IGNORECASE | re.DOTALL)
    ]


def local_href_targets(text: str, source_path: str, project_root: Path) -> list[str]:
    targets: list[str] = []
    seen: set[str] = set()
    for raw_target in html_href_targets(text):
        for normalized in resolve_reference(raw_target, source_path, project_root):
            if normalized in seen:
                continue
            seen.add(normalized)
            targets.append(normalized)
    return targets


def _split_markdown_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _looks_like_repo_path(value: str) -> bool:
    stripped = value.strip().strip("`").strip('"').strip("'")
    if not stripped or stripped.startswith(("#", "http://", "https://", "mailto:")):
        return False
    return "/" in stripped and Path(stripped).suffix.lower() in {".md", ".html", ".json", ".yaml", ".yml", ".txt"}


def _extract_reference_targets(raw_value: str) -> list[str]:
    targets = [_strip_link_fragment(match.group(1)) for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", raw_value)]
    targets = [target for target in targets if target]
    if targets:
        return targets

    code_spans = [match.group(1).strip() for match in re.finditer(r"`([^`]+)`", raw_value)]
    path_like_spans = [value for value in code_spans if _looks_like_repo_path(value)]
    if path_like_spans:
        return path_like_spans

    stripped = raw_value.strip().strip("`").strip('"').strip("'")
    return [stripped] if _looks_like_repo_path(stripped) else []


def _table_field_values(text: str, field_name: str) -> list[str]:
    values: list[str] = []
    normalized_field = field_name.strip().lower()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = _split_markdown_cells(stripped)
        if len(cells) < 2:
            continue
        if cells[0].strip().lower() == normalized_field:
            values.append(cells[1].strip())
    return values


def _inline_field_values(text: str, field_name: str) -> list[str]:
    values: list[str] = []
    patterns = (
        re.compile(rf'{re.escape(field_name)}"\s*:\s*"([^"]+)"', re.IGNORECASE),
        re.compile(rf"(?mi)^{re.escape(field_name)}\s*[:：]\s*(.+?)\s*$"),
    )
    for pattern in patterns:
        values.extend(match.group(1).strip() for match in pattern.finditer(text))
    return values


def field_values(text: str, *field_names: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for field_name in field_names:
        for value in [*_table_field_values(text, field_name), *_inline_field_values(text, field_name)]:
            if value not in seen:
                seen.add(value)
                values.append(value)
    return values


def section_reference_targets(text: str, source_path: str, project_root: Path) -> list[str]:
    targets: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        cleaned = re.sub(r"^[\-\*\d\.\)\s]+", "", stripped)
        for normalized in resolve_reference(cleaned, source_path, project_root):
            if normalized not in seen:
                seen.add(normalized)
                targets.append(normalized)
    return targets


def quick_index_link_is_valid(
    label: str,
    target: str,
    *,
    project_root: Path,
    source_path: str,
    source_text: str,
) -> bool:
    if not any(keyword in label for keyword in QUICK_INDEX_LABEL_KEYWORDS):
        return False
    if "#" not in target:
        return False

    if target.startswith("#"):
        return target.lower() in markdown_heading_anchors(source_text)

    path_part, fragment = target.split("#", 1)
    normalized_targets = resolve_reference(path_part, source_path, project_root)
    if not normalized_targets:
        return False
    normalized_target = normalized_targets[0]
    target_path = project_root / normalized_target
    if not target_path.exists() or target_path.suffix.lower() != ".md":
        return False
    return f"#{fragment.lower()}" in markdown_heading_anchors(read_text(target_path))


def _normalized_owner_token(value: str) -> str | None:
    normalized = value.strip().strip("`").strip('"').strip("'").upper()
    return normalized or None


def truth_slot(relative_path: str, text: str) -> str:
    for value in field_values(text, "owner", "Owner", "角色", "责任角色"):
        owner = _normalized_owner_token(value)
        if owner:
            return owner

    stem = Path(relative_path).stem.lower()
    for prefix, token in (
        ("be_", "BE"),
        ("fe_", "FE"),
        ("qa_", "QA"),
        ("dba_", "DBA"),
        ("ops_", "OPS"),
        ("pm_", "PM"),
    ):
        if stem.startswith(prefix):
            return token
    return "UNSPECIFIED"


def resolve_reference(raw_value: str, source_path: str, project_root: Path) -> list[str]:
    if _should_ignore_reference_target(raw_value):
        return []

    source_parent = Path(source_path).parent
    targets: list[str] = []
    for raw_target in _extract_reference_targets(raw_value):
        target_path = Path(raw_target)
        if target_path.is_absolute():
            normalized = normalize_path(raw_target, project_root)
        elif target_path.parts and target_path.parts[0] in ROOT_RELATIVE_PREFIXES:
            normalized = normalize_slashes(raw_target)
        else:
            resolved = (project_root / source_parent / raw_target).resolve()
            normalized = normalize_path(str(resolved), project_root)
        targets.append(normalized)
    return targets


def linked_prd_sources(text: str) -> list[str]:
    return field_values(text, "linked_prd_source", "Linked PRD")


def canonical_backlinks(text: str) -> list[str]:
    return field_values(text, "canonical backlink")


def truth_status_value(text: str) -> str | None:
    for value in field_values(text, "truth_status", "Status", "文档状态", "retired-truth marker", "retired_truth_marker"):
        normalized = value.strip().strip("`").strip('"').lower()
        if normalized:
            return normalized
    return None


def display_layer_truth_metadata_present(text: str) -> bool:
    return any(
        field_values(
            text,
            "owner",
            "Owner",
            "角色",
            "责任角色",
            "truth_status",
            "Status",
            "文档状态",
            "Version",
            "版本",
            "linked_prd_source",
            "canonical backlink",
            "retired-truth marker",
            "retired_truth_marker",
            "replaced_by",
            "replaced by",
        )
    )


def status_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for value in field_values(text, "truth_status", "Status", "文档状态", "retired-truth marker", "retired_truth_marker"):
        normalized = value.strip().strip("`").strip('"').lower()
        if not normalized:
            continue
        if "retired" in normalized:
            tokens.add("retired")
        if "historical" in normalized:
            tokens.add("historical")
        if normalized == "obsolete":
            tokens.add("obsolete")
        if normalized == "active":
            tokens.add("active")
        if normalized == "approved":
            tokens.add("approved")
    return tokens


def has_explicit_retired_truth_marker(text: str) -> bool:
    return bool(field_values(text, "retired-truth marker", "retired_truth_marker"))


def has_replacement_marker(text: str) -> bool:
    for value in field_values(text, "replaced_by", "replaced by"):
        if value.strip().strip("`").strip('"'):
            return True
    return False


def has_marker(text: str, field_name: str) -> bool:
    patterns = (
        re.compile(rf'{re.escape(field_name)}"\s*:\s*"([^"]*)"'),
        re.compile(rf"(?mi)^{re.escape(field_name)}\s*:\s*(.+?)\s*$"),
    )
    for pattern in patterns:
        match = pattern.search(text)
        if match and match.group(1).strip().strip('"'):
            return True
    return False


def heading_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped
    return ""


def handoff_truth_docs_exist(file_path: Path) -> bool:
    handoff_dir = file_path.parent
    for child in handoff_dir.iterdir():
        if child.is_file() and child.name != "README.md" and child.suffix.lower() in {".md", ".json"}:
            return True
    return False


def is_machine_local_absolute_target(raw_value: str) -> bool:
    stripped = _strip_link_fragment(raw_value.strip().strip("`").strip('"').strip("'"))
    if not stripped:
        return False
    if Path(stripped).is_absolute():
        return True
    return bool(re.match(r"^[A-Za-z]:[\\/]", stripped))


def absolute_reference_targets(text: str) -> list[str]:
    targets: list[str] = []
    seen: set[str] = set()
    for raw_target in [
        *markdown_link_targets(text),
        *(match.group(1).strip() for match in re.finditer(r"`([^`]+)`", text)),
    ]:
        candidate = _strip_link_fragment(raw_target)
        if not is_machine_local_absolute_target(candidate):
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        targets.append(candidate)
    return targets


def content_issues(project_root: Path, candidate_paths: list[str]) -> list[str]:
    issues: list[str] = []
    active_truth_slots: dict[tuple[str, str], list[str]] = {}

    for relative_path in candidate_paths:
        file_path = project_root / relative_path
        if not file_path.exists() or file_path.suffix.lower() not in {".md", ".html", ".json"}:
            continue

        try:
            text = read_text(file_path)
        except OSError:
            continue

        if file_path.suffix.lower() == ".md" and relative_path.startswith(DISPLAY_LAYER_PREFIX):
            if display_layer_truth_metadata_present(text):
                issues.append(f"display-layer truth-metadata conflict: {relative_path}")

        should_check_publish_targets = (
            file_path.suffix.lower() in {".md", ".html"}
            and (
                is_truth_source_path(relative_path)
                or relative_path in OUTWARD_ENTRY_PATHS
                or relative_path.startswith(DISPLAY_LAYER_PREFIX)
            )
        )

        if should_check_publish_targets:
            for target in local_link_targets(text, relative_path, project_root):
                target_path = project_root / target
                if target_path.exists():
                    continue
                if target == PRD_INDEX_PATH:
                    issues.append(f"missing formal index target: {relative_path} -> {target}")
                elif relative_path.startswith(DISPLAY_LAYER_PREFIX) and target == READING_LAYER_PATH:
                    issues.append(f"mapping contract blocked: {relative_path} -> {target}")
                else:
                    issues.append(f"missing relative target: {relative_path} -> {target}")

            for target in local_href_targets(text, relative_path, project_root):
                if not (project_root / target).exists():
                    issues.append(f"missing html href target: {relative_path} -> {target}")

        if is_truth_source_path(relative_path) or relative_path in OUTWARD_ENTRY_PATHS:
            for absolute_target in absolute_reference_targets(text):
                issues.append(f"machine-local absolute path: {relative_path} -> {absolute_target}")

        if is_truth_source_path(relative_path):
            for target in local_link_targets(text, relative_path, project_root):
                if target == STATUS_TRUTH_PATH:
                    continue
                if target.startswith(DISPLAY_LAYER_PREFIX):
                    issues.append(f"display-layer markdown-link conflict: {relative_path} -> {target}")

        if file_path.suffix.lower() == ".md" and "下游文档列表" in text:
            downstream_section = extract_section(text, "下游文档列表")
            for target in section_reference_targets(downstream_section, relative_path, project_root):
                if not (project_root / target).exists():
                    issues.append(f"fake downstream link: {relative_path} -> {target}")
                if target.startswith(DISPLAY_LAYER_PREFIX):
                    issues.append(f"display-layer downstream-link conflict: {relative_path} -> {target}")

        for backlink in canonical_backlinks(text):
            if is_machine_local_absolute_target(backlink):
                issues.append(f"machine-local absolute path: {relative_path} -> {backlink}")
            for normalized in resolve_reference(backlink, relative_path, project_root):
                if not (project_root / normalized).exists():
                    issues.append(f"missing canonical backlink target: {relative_path} -> {normalized}")
                if normalized.startswith(DISPLAY_LAYER_PREFIX):
                    issues.append(
                        f"display-layer canonical-backlink conflict: {relative_path} -> {normalized}"
                    )

        for linked_source in linked_prd_sources(text):
            if is_machine_local_absolute_target(linked_source):
                issues.append(f"machine-local absolute path: {relative_path} -> {linked_source}")
            for normalized in resolve_reference(linked_source, relative_path, project_root):
                if not (project_root / normalized).exists():
                    issues.append(f"missing linked_prd_source target: {relative_path} -> {normalized}")
                if normalized.startswith(DISPLAY_LAYER_PREFIX):
                    issues.append(
                        f"display-layer linked-truth conflict: {relative_path} -> {normalized}"
                    )

        if relative_path.endswith(HANDOFF_README_SUFFIX):
            if looks_like_legacy_handoff_readme(text):
                issues.append(f"starter-handoff contradiction: {relative_path}")

        tokens = status_tokens(text)
        if {"retired", "historical", "obsolete"} & tokens:
            if not has_explicit_retired_truth_marker(text) or not has_replacement_marker(text):
                issues.append(f"retired-truth ambiguity: {relative_path}")

        if is_truth_source_path(relative_path) and not ({"retired", "historical", "obsolete"} & tokens):
            if any(pattern.search(text) for pattern in LEGACY_VERSION_PATTERNS):
                if not any(marker in text for marker in CURRENT_VERSION_MARKERS):
                    issues.append(f"active truth-source version label ambiguous: {relative_path}")

        if is_truth_source_path(relative_path) and ("active" in tokens or "approved" in tokens):
            directory = str(file_path.parent.relative_to(project_root))
            slot = truth_slot(relative_path, text)
            active_truth_slots.setdefault((directory, slot), []).append(relative_path)

        if relative_path == PRD_INDEX_PATH and "PRD阅读入口" not in text:
            issues.append(f"reading-layer entry boundary violated: {relative_path}")
        if relative_path == PRD_INDEX_PATH:
            reading_layer_targets = [
                target for target in local_link_targets(text, relative_path, project_root) if target == READING_LAYER_PATH
            ]
            if not reading_layer_targets:
                issues.append(f"reading-layer entry link missing: {relative_path}")

        if relative_path == READING_LAYER_PATH:
            heading = heading_line(text)
            if "阅读层" not in heading or "PRD阅读层" not in text or has_reading_layer_truth_claim(text):
                issues.append(f"reading-layer naming boundary violated: {relative_path}")
            issues.extend(reading_layer_flowchart_issues(text))
            quick_index = extract_section(text, "人读流程图速查")
            if "人读流程图速查" not in text:
                issues.append(f"diagram quick index missing: {relative_path}")
            elif not any(
                quick_index_link_is_valid(
                    label,
                    target,
                    project_root=project_root,
                    source_path=relative_path,
                    source_text=text,
                )
                for label, target in markdown_links(quick_index)
            ):
                issues.append(f"diagram quick index link missing: {relative_path}")

    for (directory, slot), docs in active_truth_slots.items():
        if len(docs) > 1:
            issues.append(
                "dual-active truth siblings: "
                + directory
                + f" [{slot}]"
                + " -> "
                + ", ".join(Path(path).name for path in sorted(docs))
            )

    return issues


def looks_like_legacy_handoff_readme(text: str) -> bool:
    for line in text.splitlines():
        normalized = line.strip()
        if not normalized:
            continue
        if "不再使用" in normalized:
            continue
        lowered = normalized.lower()
        if "starter" in lowered:
            return True
        if any(phrase in normalized for phrase in MISLEADING_HANDOFF_PHRASES):
            return True
    return False


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    project_root = project_root_from_args(args.project_root)
    candidate_paths = collect_candidate_paths(project_root, args.paths)
    offenders = [path for path in candidate_paths if is_forbidden(path)]
    content_offenders = content_issues(project_root, candidate_paths)
    if offenders or content_offenders:
        print("publish boundary check failed:")
        for path in offenders:
            print(path)
        for issue in content_offenders:
            print(issue)
        return 1

    print("publish boundary check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
