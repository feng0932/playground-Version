# 组织技能包

这里放组织级可安装 skill 源。

当前 bundle 中，`assets/` 与 `org_skills/` 是两类不同真源，不得混平。

当前已纳入：

- [org_skills/01-prd-compliance-review/SKILL.md](01-prd-compliance-review/SKILL.md)：中国市场 App 的 `PRD` 前置合规审查
- [org_skills/02-prd-requirement-comprehension/SKILL.md](02-prd-requirement-comprehension/SKILL.md)：技术设计前的 `PRD` 需求理解分析
- [org_skills/03-submission-status-governance/SKILL.md](03-submission-status-governance/SKILL.md)：维护 `80-完整提交包/00-提交状态.json` 真源、同步展示层并执行一致性校验

## 内部编排能力

- 目录：org_skills/00-dispatch-orchestration/
- 角色：bundle-internal orchestration package
- 安装语义：随 bundle 分发，但不属于 manifest.skills，不走用户侧 skill 安装入口
- 单例边界：v0.3.7 的 internal_org_skill_packages 只能是 ["00-dispatch-orchestration"]

已退休：

- `project-package-guide`
- `work-package-entry-coach`
- `product-manager`
- `communication-log-and-sync`
- `record_round.py`
- `check_process_artifact_locations.py`

以上旧 skill / 脚本都不再默认安装，也不再保留在组织能力仓中；对应能力已由当前 bundle 中的 Agent 主流程与 installer/runtime 体系替代。

约束：

- 这里存放的是组织维护的 skill 源，不是业务项目事实源。
- 运行安装时，由 `ai-team install` / current bundle runtime 把需要的 skill 同步到项目运行面或本地 skill 安装位置。
- 上述命令默认要求 `python3` 指向 `Python 3.9+`。
- 规则更新应优先修改这里的源文件，不要直接把运行副本当事实源。
- `org_skills/03-submission-status-governance` 是 submission status 机制的唯一维护源；`assets/project_skeleton/00-项目包模板/` 中的同名脚本是发布副本。

来源说明：

- 上游来源：`http://192.168.1.152/develop_skill/01-prd-compliance-review.git`
- 引入参考提交：`be49886ae8b24985e2d3d3a32de2fb1df1dcea18`
- 本地适配：默认落盘位置已从根 `docs/` 调整为真实项目的 `04-过程文件/`
- 上游来源：`http://192.168.1.152/develop_skill/02.prd-requirement-comprehension`
- 引入参考提交：`88b2a5a205644ca082071c4831fb9aead228a345`
- 本地适配：默认落盘位置已从根 `docs/` 调整为真实项目的 `04-过程文件/`
