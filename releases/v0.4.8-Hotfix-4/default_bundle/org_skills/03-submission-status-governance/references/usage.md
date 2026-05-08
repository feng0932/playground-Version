# Submission Status Governance 使用说明

## 核心原则

- `80-完整提交包/00-提交状态.json` 是唯一真源
- `00-提交说明.md`、`00-PRD索引.md`、`01-合并PRD阅读层.md`、`00-原型入口.md`、`00-评审索引.md` 是展示层
- 如需把提交状态外显到工程交接对外材料，必须使用 typed contract：
  - `artifacts.engineering_handoff.project_entry`
  - `artifacts.engineering_handoff.module_entries[].entry_file`
  - `artifacts.engineering_handoff.module_entries[].checklist_file`
- `artifacts.engineering_handoff.handoff_audit_globs / process_audit_globs` 是工程交接 `02-工程交接/` 与 `04-过程文件/` 的显式 audit scope；未登记就不属于 submission-status audit 面
- 当 `engineering_handoff_required=true` 或 `engineering_handoff_ready=true` 时，`project_entry / module_entries / handoff_audit_globs / process_audit_globs` 缺任一项都必须 fail-closed
- 若需要同步正式 `PRD` 头部状态，必须通过 `artifacts.prd_files` 声明目标文件
- `status.gates` 也是真源的一部分，只有 `validators_passed / status_synced / consistency_check_passed / review_receipts_present / review_blockers_cleared` 全部为 `true` 时，`phase` 才能进入 `ready_for_human_review`
- `status.engineering_handoff_required / status.engineering_handoff_ready` 是 Gate B 写回真源，不属于 `phase`
- `engineering_handoff_ready` 不是 `phase`，也不覆盖 `ready_for_human_review`
- `模块级绿灯` 必须按条件解释：
  - `engineering_handoff_required=false`：`模块级绿灯 = 基础四审全绿`
  - `engineering_handoff_required=true`：`模块级绿灯 = 基础四审全绿 + 24-审查-跨角色预审完成 + Gate B green`
- `24-审查-跨角色预审` 只作为 Gate B 前置链路，不是第二条独立放行通道
- Gate B 一旦写回 `engineering_handoff_required / engineering_handoff_ready`，旧的 `status_synced / consistency_check_passed` 证据必须立即失效；canonical green 只能靠重新执行 `sync -> check` 恢复
- 在 `consistency_check_passed=false` 期间，对外展示层必须降级为：
  - `当前阶段：pending_consistency_check`
  - `可进入人工评审：no`
- Gate B 需要额外运行 `check_engineering_handoff_readiness.py`
- final gate 需要额外运行 `check_final_delivery_gate.py`
- `check_final_delivery_gate.py` 只判断终审证据是否还能复用，也就是 final-review evidence 的新鲜度；它不重跑 `sync_submission_status.py`，也不写 `00-提交状态.json`
- Gate B evidence pack 的 `registry` 顶层未知扩展键若被 authoritative contract 通过 `contract_extensions.preserve_top_level_unknown_keys=true` 允许保留，则 install/runtime 可以继续 preserve；Gate B consumer 只校验 canonical known keys，不会因同一 pack 的 preserved unknown top-level key 再次 mismatch
- 缺少 handoff README、缺状态块、或状态块漂移时，`sync / check / Gate B` 都必须结构化 fail-closed，不能直接抛 raw traceback
- `01-合并PRD阅读层.md` 已进入 sync / check / audit 面；不再是游离阅读页

## 标准命令

```bash
python3 scripts/sync_submission_status.py --project-root /path/to/project
python3 scripts/check_submission_consistency.py --project-root /path/to/project
cp references/gate-b.example.json /path/to/project/01-模块执行包/<模块>/04-过程文件/gate-b.input.json
python3 scripts/check_engineering_handoff_readiness.py --project-root /path/to/project
python3 scripts/check_final_delivery_gate.py --project-root /path/to/project
```

补充说明：

- 正式输入面优先读取仓库内 repo-persisted evidence pack：
  - module-level：`01-模块执行包/<模块>/04-过程文件/gate-b.input.json`
  - project-level：`00-项目包/04-过程文件/04-全量提交-gate-b.input.json`
- `--input` 仍可显式指定输入文件，用于覆盖自动发现或在多份模块级 evidence pack 并存时精确选择目标。
- `/tmp/gate-b.json` 只保留为 debug-only fallback；不要把它当正式提交流程的默认输入。
- `--no-sync-status-json` 仅限显式 debug 环境，且不会返回正式 Gate B pass；不要把它当正式提交链的一部分。
- evidence pack 顶层建议固定携带：
  - `schema: submission_status.gate_b_evidence_pack`
  - `schema_version: v1`
  - `registry.contract_extensions.*` 之类的顶层扩展键如果存在，必须与 authoritative bundled contract 完全一致，不能在 repo 内私自漂移

## 标准顺序

1. 修改 `80-完整提交包/00-提交状态.json`
2. 运行 `sync_submission_status.py`
3. 运行 `check_submission_consistency.py`
4. 若需要工程交接判断，先从 `references/gate-b.example.json` 复制一份最小样例，按当前模块 scope / trigger / artifact paths 改写后，写回项目内固定 evidence pack 路径，再运行 `check_engineering_handoff_readiness.py`
5. Gate B 脚本会把 `engineering_handoff_required / engineering_handoff_ready` 写回 `00-提交状态.json`，并自动把 `status_synced / consistency_check_passed` 打回 `false`
6. 只有重新执行 `sync_submission_status.py -> check_submission_consistency.py`，才能恢复 canonical green
7. 若当前目标是判断最近一次终审证据是否还能复用，再运行 `check_final_delivery_gate.py`；它只做新鲜度判断，不重跑 `sync_submission_status.py`，也不写 `00-提交状态.json`

## 常见错误

- 只改展示层，不改真源
- `allow_human_review=true`，但 `review` 仍未到 `approved/frozen`
- `allow_human_review=true`，但 `status.gates` 没有全部置为 `true`
- 忘记把正式 `PRD` 文件加入 `artifacts.prd_files`
- 忘记按 typed contract 填 `artifacts.engineering_handoff.project_entry / module_entries`
- 忘记给 `artifacts.engineering_handoff.handoff_audit_globs / process_audit_globs` 声明真实审计范围，导致新增对外交接材料未被 audit
- 项目根目录传错，导致脚本找不到 `80-完整提交包/00-提交状态.json`
- 把 `ready_for_human_review` 当成 `engineering_handoff_ready`
- Gate B 已命中 trigger，但没有准备 `artifact_owner_map / required_supporting_docs / truth_source_ref`
- `engineering_handoff_required=true` 时缺少 `24-审查-跨角色预审` 前置证据（`unresolved_issue_ledger`）却仍尝试声明模块级绿灯
- 直接复用过期 `gate-b.input.json` 或 `/tmp/gate-b.json`，没有按当前 published rules 刷新 `approved_repository_scopes / artifact_registry`
- 以为 Gate B 写回后旧的 `status_synced / consistency_check_passed` 还能继续当证据使用
