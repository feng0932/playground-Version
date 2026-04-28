---
name: 03-submission-status-governance
description: Use when a real project's submission-package status, review readiness, or PRD header state must be updated and synchronized from a single JSON source of truth.
---

# Submission Status Governance

## 概述

这个 skill 用于维护真实项目 `80-完整提交包/` 的状态真源机制。
唯一真源是 `80-完整提交包/00-提交状态.json`；展示层和正式 `PRD` 头部状态只能由脚本派生，不允许手工分别维护。

## 何时使用

- 当前结论会影响 `80-完整提交包/` 的 `PRD / 原型 / 评审 / phase` 状态
- 需要把状态同步到 `00-提交说明.md`、索引页或正式 `PRD` 头部
- 需要确认项目是否真的已经“可进入人工评审”
- 需要检查展示层是否漂移、语义是否打架
- 需要确认某模块是否已经达到 `engineering_handoff_ready`

## 输入前提

- 目标项目根目录下必须存在 `80-完整提交包/00-提交状态.json`
- 如需同步正式 `PRD` 头部状态，真源中的 `artifacts.prd_files` 必须已登记目标文件
- 如需把提交状态同步到工程交接对外材料，真源中的 `artifacts.engineering_handoff` 必须使用 formal typed contract：
  - `project_entry`
  - `module_entries[].entry_file`
  - `module_entries[].checklist_file`
  - `handoff_audit_globs`
  - `process_audit_globs`
- 当 `engineering_handoff_required=true` 或 `engineering_handoff_ready=true` 时，上述 handoff contract 缺任一关键字段都必须 fail-closed

## 标准流程

1. 更新 `80-完整提交包/00-提交状态.json`
2. 运行：
   `python3 scripts/sync_submission_status.py --project-root <项目根>`
3. 再运行：
   `python3 scripts/check_submission_consistency.py --project-root <项目根>`
4. 若本轮目标还包含工程交接判断，再运行：
   `python3 scripts/check_engineering_handoff_readiness.py --input <gate-b-json> --project-root <项目根>`
   `references/gate-b.example.json` 可作为最小输入样例起点。
5. Gate B 脚本会把 `engineering_handoff_required / engineering_handoff_ready` 回写到 `80-完整提交包/00-提交状态.json`，并使既有 `status_synced / consistency_check_passed` 证据失效
6. 若需要恢复 canonical green，必须再跑一次 `sync -> check`
7. 若本轮目标是复用最近一次终审证据，再运行：
   `python3 scripts/check_final_delivery_gate.py --project-root <项目根>`
   它只做 final-review evidence 新鲜度校验，不重跑 `sync_submission_status.py`，也不写 `00-提交状态.json`

## 硬规则

- `80-完整提交包/00-提交状态.json` 是唯一真源
- `80-完整提交包/01-合并PRD/`、`02-原型索引/`、`03-合并评审记录/` 是展示层
- `80-完整提交包/01-合并PRD/01-合并PRD阅读层.md` 已进入 submission-status 的 display / audit / sync-check 链
- `artifacts.engineering_handoff.project_entry` 与 `module_entries` 中登记的文件，属于 submission-status 管理的 outward display surface
- 未通过一致性校验，不得宣称“可进入人工评审”或“已可最终提交”
- `check_final_delivery_gate.py` 只负责 recent final-review evidence 的新鲜度判断，不独立授予“可最终提交”
- `check_final_delivery_gate.py` 不重跑 `sync_submission_status.py`，也不刷新 `.ai-team/state/governance-latest.json`
- `check_final_delivery_gate.py` 不写 `00-提交状态.json`
- `consistency_check_passed=false` 时，展示层必须降级为单一 canonical non-green 语义：
  - `当前阶段：pending_consistency_check`
  - `可进入人工评审：no`
- `ready_for_human_review` 不得被重写为 `engineering_handoff_ready`
- `check_engineering_handoff_readiness.py` 只负责 Gate B 判断，不改变 `phase`
- Gate B 写回只允许更新 `engineering_handoff_required / engineering_handoff_ready` 与失效旧的 `status_synced / consistency_check_passed`，不得改写 `phase`
- `--no-sync-status-json` 仅限显式 debug 环境；未同步真源时不得作为正式 Gate B pass 出口
- Gate B registry 顶层未知扩展键必须 preserve-and-compare；输入包与 bundled contract 不一致时必须阻断
- 若 authoritative contract 开启 `contract_extensions.preserve_top_level_unknown_keys=true`，同一 pack 在 install/runtime 中保留的 top-level unknown registry key 不得在 Gate B 再被误判成 mismatch
- `org_skills/03-submission-status-governance` 是唯一维护源
- `assets/project_skeleton/00-项目包模板` 中同名脚本是发布副本，不单独分叉维护

## 角色边界

- `00-编排-总控`：负责执行 `改真源 -> sync -> check`
- `20-审查-门禁审查`：只检查该链路是否已执行且已通过，不负责改文件

## 参考资产

- `references/00-提交状态.example.json`
- `references/gate-b.example.json`
- `references/usage.md`
- `references/release-process.md`
