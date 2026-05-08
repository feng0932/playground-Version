# 发布副本流程

## 维护规则

- `org_skills/03-submission-status-governance` 是唯一维护源
- `assets/project_skeleton/00-项目包模板` 中同名脚本是发布副本
- 不允许长期在 `assets/project_skeleton/00-项目包模板/` 中手工分叉维护脚本
- 发布链路必须保持单向闭环：源脚本 -> `publish_to_project_template.py` -> `assets/project_skeleton/00-项目包模板` 发布副本 -> 运行时项目
- `check_final_delivery_gate.py` 在 v0.3.5 中只裁定 final-review 证据是否可复用、是否仍然新鲜，不回写 `00-提交状态.json`，也不重跑 `sync_submission_status.py`
- 项目级 Gate B 聚合包仍然是 final gate 依赖的权威输入；模块级 Gate B 包只负责模块内部产出，不提升为 final gate 的真源

## 发布命令

```bash
python3 install/default_bundle/org_skills/03-submission-status-governance/scripts/publish_to_project_template.py
```

## 发布后验证

1. 确认 `assets/project_skeleton/00-项目包模板/scripts/` 中五个治理脚本已按发布契约更新
2. 确认 `check_final_delivery_gate.py` 仍由组织技能源发布到模板副本，而不是反向维护
3. 确认 `assets/project_skeleton/00-项目包模板/80-完整提交包/00-提交状态.json` 已与 example 对齐
4. 确认 `00-提交状态.json` 含 `engineering_handoff_required / engineering_handoff_ready`
5. 确认 Gate B 脚本回写后，`sync -> check` 链路仍可通过，且项目级 Gate B 聚合包仍是 final gate 的权威依赖
6. 确认 final gate 结果 payload 显式携带 semantic boundary，标明它只判断 final-review 证据复用/新鲜度，不回写状态真源，也不重跑 `sync_submission_status.py`
7. 跑 `install/default_bundle/org_skills/03-submission-status-governance/tests/test_publish_to_project_template.py`
8. 跑 `install/default_bundle/org_skills/03-submission-status-governance/tests/test_final_delivery_gate.py`
9. 跑 `install/default_bundle/org_skills/03-submission-status-governance/tests/test_engineering_handoff_readiness.py`
10. 再跑相关 skill tests，确认发布副本与源内容一致
