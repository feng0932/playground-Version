# 真实项目仓库执行约束
这份 `AGENTS.md` 是真实项目仓库的仓库级执行契约。
它的优先级高于通用 skill 的默认落盘习惯。
如果外部工作流默认把 spec、plan 或中间文档写到 `docs/superpowers/`、`docs/plans/`、`docs/specs/`，一律以本文件为准覆盖。
## 1. 事实源与非事实源
- `00-项目包/`：项目级事实源
- `00-项目包/00-项目包索引.md`：项目级人类入口
- `01-模块执行包/`：需求与模块事实源
- `01-模块执行包/00-模块索引.md`：模块入口与阅读导航
- `80-完整提交包/`：交付视图，不是事实源
- `80-完整提交包/00-提交状态.json`：完整提交包状态的唯一真源
- `00-项目包/02-工程交接/`、`01-模块执行包/<模块名>/02-工程交接/`：Gate B 技术真源默认落点
- 工程交接是一等入口：项目级走 `00-项目包/02-工程交接/README.md`，模块级走 `01-模块执行包/<模块名>/02-工程交接/README.md`
- `80-完整提交包/01-合并PRD/`、`02-原型索引/`、`03-合并评审记录/`：由真源脚本派生的展示层
- 如需同步正式 `PRD` 头部状态，必须通过 `80-完整提交包/00-提交状态.json` 的 `artifacts.prd_files` 声明目标文件，再运行同步脚本
- `scripts/sync_submission_status.py`、`scripts/check_submission_consistency.py` 的唯一维护源位于组织 skill `org_skills/03-submission-status-governance/`；当前项目中的同名脚本是模板发布副本
- `scripts/check_publish_boundary.py` 的唯一维护源同样位于组织 skill `org_skills/03-submission-status-governance/`；当前项目中的同名脚本是模板发布副本
- `scripts/check_engineering_handoff_readiness.py` 的唯一维护源同样位于组织 skill `org_skills/03-submission-status-governance/`；当前项目中的同名脚本是模板发布副本
- `scripts/check_final_delivery_gate.py` 的唯一维护源同样位于组织 skill `org_skills/03-submission-status-governance/`；当前项目中的同名脚本是模板发布副本
- 正式 `PRD` 文件名必须状态中立，不得使用 `-draft` 承载生命周期状态
- 根 `docs/`：白名单补充区，不是事实源
- 本机 `.ai-team/`：本地运行元数据与绿灯标记，不是事实源
- 项目级与模块级工程交接 README、`80-完整提交包/` 展示层都是消费镜像，不是另一套运行时真源
- `engineering_handoff_required=false` 时，模块级绿灯只看基础四审
- `engineering_handoff_required=true` 时，模块级绿灯 = 基础四审 + `24-审查-跨角色预审` 完成 + Gate B 绿灯
- `24-审查-跨角色预审` 只是 Gate B 前置条件，不是第二条独立绿灯通道
- Gate B 写回只允许 `engineering_handoff_required / engineering_handoff_ready`
- `ready_for_human_review` 与 `engineering_handoff_ready` 是不同语义
## 2. 过程文件落盘规则
任何 spec、plan、草稿、子 agent 输出、临时分析、过程纪要，在落盘前都必须先判断归属层级：
1. 单一模块相关：
   写入 `01-模块执行包/<模块名>/04-过程文件/`
2. 跨多个模块、但仍服务真实项目推进：
   写入 `00-项目包/04-过程文件/`
3. 非事实源、跨模块、明确批准保留的补充资料：
   才允许写入 `docs/01-跨模块补充资料/`
如果一时无法判断归属，默认先写入 `00-项目包/04-过程文件/`，不要落到根 `docs/`。
执行类 Agent 默认不读取 `04-过程文件/`，避免把过程痕迹当成主上下文。
只有当任务职责明确命中过程治理、收口或审查留痕时，才允许显式读取过程文件。
- `总控 / 门禁 / 四审 / 收口` 可以显式读取 `01-总控复核清单.md`
- `记录同步 / 冲突追因 / 复盘 / 审计` 可以显式读取 `00-沟通记录与结论回写.md`
- `delivery owner mode` 只服务当前任务链，不参与 `80-完整提交包/00-提交状态.json` 或 `.ai-team/state/*` 计算
- `00-沟通记录与结论回写.md` 是唯一 authority carrier
- `35-过程-总控复核清单.md` 只做 review-phase echo
- `Required Opening`、`Final User Report` 只做 echo
- 普通 redispatch 与 partial-state recovery 不得推动 `task_chain_epoch` 递增；只有显式 re-lock、scope 变化、exit-reenter 才允许 bump
- `32-过程-沟通记录与结论回写模板.md` 承担 verifier-owned acceptance grammar 的真源定义；本模板只保留消费边界与可见状态，不复述 fixed verifier grammar。
进入四审前，总控必须先把高风险强制检查项展开到 `01-总控复核清单.md`；单一模块写对应模块 `04-过程文件/`，跨模块或无法判断时写 `00-项目包/04-过程文件/`。四审返回后，还要在同一文件补做 `prompt 强制项` 对 `报告已覆盖项` 的二次对照，`未覆盖项` 未清零前不得收口。
若两个及以上 Agent 的预期写入目标重叠，例如同一正式文件、同一正式章节、同一页面编号集合、同一审查记录或同一提交状态链路，必须由总控拆成严格串行依赖链，禁止并行派发。总控只负责调度、核验和收口，不得亲自改写业务正式内容。
所有执行与审查 Agent 在交还控制权前，必须先输出固定格式的 `工单回执`；缺字段视为无效交接。`执行状态` 只允许使用 `done / blocked / need_user`。`下一跳请求` 必须写明确动作；如需补真源，统一写 `改派 10-执行-产品专家补全真源`。
若任务命中多文件综合阅读、多文件改写、测试生成或执行、迁移/repair、多角色终审或外部慢链路，默认按长任务处理。未收到正式 `工单回执` 前，只允许使用临时编排 / 即时状态描述 `仍在运行 / 已部分返回 / 超时未回 / 已重派`；这组状态只用于过程判断，不要求写入 `35-过程-总控复核清单.md`、`32-过程-沟通记录与结论回写.md` 或其他正式文件，也不得直接宣称完成或失败；首轮未回时，必须先缩范围、降并发或要求先回当前结论，避免任务空跑。
## 2.1 安装前置规则
首次在本机接入项目时，先在项目根目录执行 `ai-team install`。若需要 `python -m ai_team_installer install --project-root <项目根>`，只能把它当作 repo-local 调试 fallback，不得与正式用户入口并列。
只有当以下几层都已通过，才允许进入业务主路径：
1. 机器级绿灯
2. 项目级绿灯
3. bundle 资产完整性绿灯
项目级本地标记只允许写入 `<项目根>/.ai-team/install.json`、`<项目根>/.ai-team/runtime.json`、`<项目根>/.ai-team/state/*.json`、`<项目根>/.ai-team/state/governance-log.jsonl`，以及由此维护的 `<项目根>/.ai-team/state/governance-latest.json`，并保持本地不入 git。
## 3. 明确禁止
禁止把以下位置当默认过程文件目录：
- `docs/superpowers/`
- `docs/plans/`
- `docs/specs/`
- 任何未经批准的根 `docs/` 自建目录
## 4. 根 `docs/` 白名单规则
根 `docs/` 只允许放“非事实源、跨模块、明确批准”的补充资料。
`docs/01-跨模块补充资料/` 必须继续拆成两层：
- `local/`：只允许本地保留，不进入远端 git
- `published/`：只有明确批准后，才允许进入远端 git
每份写入 `docs/01-跨模块补充资料/` 的文档，头部都必须说明：
- 这不是事实源
- 为什么必须跨模块保留
- 谁批准放这里
- 对应的正式事实源文件有哪些
## 5. 结论回写规则
当形成新的已确认结论时：
1. 先把完整问答写入对应 `04-过程文件/00-沟通记录与结论回写.md`
2. 再把确认结论回写到正确的正式文件
若当前轮次命中 `delivery owner mode`，authority 结构化记录也只允许追加在同一份 `00-沟通记录与结论回写.md` 中，并固定使用：
- `Delivery Owner Record -> Dispatch Snapshot Record -> Partial State Record`
- `35-过程-总控复核清单.md` 只镜像当前 authority 快照，不得回写 authority
- `Required Opening`、`Final User Report` 只复述当前 authority，不得自造第二套状态
如果当前轮次目标是进入或收口四审，除 `00-沟通记录与结论回写.md` 外，还必须维护对应 `04-过程文件/01-总控复核清单.md`，并显式区分：
- `已核通过项`
- `已核未通过项`
- `未覆盖项`
未确认的讨论，只允许保留在过程文件里。
当形成影响 `80-完整提交包/` 的新结论时，先更新 `80-完整提交包/00-提交状态.json`，再运行同步脚本生成展示层，最后运行一致性校验；如果校验失败，不得宣称已经可以进入人工评审或最终提交。
当本轮目标还包含“研发可直接开工 / 工程交接就绪 / Gate B”时，必须额外准备 Gate B 输入并运行 `scripts/check_engineering_handoff_readiness.py`；该脚本只允许回写 `engineering_handoff_required / engineering_handoff_ready` 到 `80-完整提交包/00-提交状态.json`，不得改写 `phase`。Gate B 写回后，还必须再跑一次 `scripts/sync_submission_status.py -> scripts/check_submission_consistency.py`；`ready_for_human_review` 不等于 `engineering_handoff_ready`。
若当前目标是进入原型链，必须先由总控核对 `02-模块流程图与人类确认.md` 已落盘、已回链模块 `PRD` 真源，且已经拿到 `21-审查-产品审查` 的工单回执或结论；原型前质量准入继续由总控与产品审查共同承担，不新增独立 prototype-entry 运行时脚本门。
若当前目标是确认最近一次终审证据是否还能复用，可额外运行 `scripts/check_final_delivery_gate.py`。它只做 final-review evidence 新鲜度校验，不写 `00-提交状态.json`，也不独立授予“可最终提交”。
若准备推送项目远端 git，还必须先运行 `scripts/check_publish_boundary.py`；一旦发现被跟踪或已暂存的 `04-过程文件/`、`docs/01-跨模块补充资料/local/` 或 `.ai-team/`，必须先清理边界再推送。
本机聊天审计副本只用于补充审计、复盘与学习样本，不替代本条正式回写规则。
## 6. 原型与高风险规则前置门禁
- `4.3 页面合同清单` 是页面合同、页面元素、首屏焦点与页内交互承接的全局第一真源；没有正式 `4.3` 时，不得进入原型链或原型审查链。
- `4.4 结构化契约字段清单` 是结构化业务字段、跨页透传、状态回写与验收字段的全局第一真源；命中时缺少正式 `4.4`，同样不得进入原型链或原型审查链。
- 命中登录、验证码、支付、SLA、删除、第三方接口、动态配置、AIGC 等高风险规则场景时，必须补齐 `4.2A 关键规则参数与边界冻结表` 并通过五维健壮性防穿透。
- 若 `4.2A` 只有概念性表述，没有具体规则值、阈值、时长、重置基准点、生效规则、进行中处理规则或失效承接规则，统一判 `未冻结`，按 `Blocker` 回流。
- 原型执行与原型审查不得只验证“流程存在”，还必须验证“冻结参数已被用户可感知承接”：`TTL/有效期` 要落成倒计时或失效提示，`冷却时间 / 重试上限 / 触发阈值` 要落成禁用态或限制提示，`接口挂起 / 弱依赖失败 / 异步补偿` 要落成挂起态、降级态或重试提示。
