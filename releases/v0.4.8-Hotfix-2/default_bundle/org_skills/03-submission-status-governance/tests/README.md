# Submission Status Governance Tests

这组测试覆盖 3 件事：

1. `sync_submission_status.py` 能基于 `00-提交状态.json` 同步展示层
2. `check_submission_consistency.py` 能抓住语义冲突与展示层漂移
3. `publish_to_project_template.py` 能把 skill 中的发布副本同步到 `assets/project_skeleton/00-项目包模板`
4. `check_publish_boundary.py` 能阻断被跟踪或已暂存的本地过程文件进入远端 git 范围
5. `check_engineering_handoff_readiness.py` 能对 Gate B 的 owner、supporting docs、trigger 与 legal N/A 做机器校验
6. Gate B 结果能回写 `00-提交状态.json`，并在重新执行 `sync -> check` 后进入展示层一致性校验

建议运行：

```bash
python3 -m unittest discover -s install/default_bundle/org_skills/03-submission-status-governance/tests -p 'test_*.py'
```

运行该命令前，默认要求 `python3` 指向 `Python 3.9+`。
