# v0.4.7-Hotfix-1-rc2 内网候选发版执行说明书

## 1. 这个版本做了什么

`v0.4.7-Hotfix-1-rc2` 是 `v0.4.7-Hotfix-1` 的第二个内网预发候选版，不是正式 stable。

相对 `rc1`，本版修正了 `10-执行-产品专家` raw role prompt 里残留的旧机器回执说明：`layer_consumed`、`inherited_hosts_checked`、`module_exceptions`、`upgrade_required`、`upgrade_target_host` 只能落入正式 PRD 证据或结构化阻塞包，不得额外塞入 `Machine Receipt Carrier`。

这版继续验证两件事：

1. `10 completed + no_primary_window_next_hop` 之后，fresh `/总控` 不再反复派回 `01`，而是等待人的下一步意图。
2. `01 / 10` 的机器回执保持最小可消费结构，`00` 可通过 `/读取回执` 消费，并据此判断下一跳。

本候选不切 stable pointer，不创建正式 release，不做 GitHub 发布或镜像。

## 2. 让大模型去安装和 live 验收的提示词

### macOS / Linux-like Shell

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7-Hotfix-1-rc2 的内网候选安装和 live smoke，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 只使用内部 Gitea 候选入口，不使用 GitHub。
2. 本版本是 release-candidate，不是 stable。
3. 不切 stable pointer，不创建正式 release。
4. 保留完整 stdout/stderr。
5. 任一步失败都立即停止，不要脑补成功。
6. 按设计流程验证，不在 00 / 01 / 10 之间乱跳。
7. 重点验证 01 -> 10、10 -> 等待人下一意图，以及 /读取回执 可被 00 消费。
8. 检查生成的 Machine Receipt Carrier 不再要求 `layer_consumed`、`inherited_hosts_checked`、`module_exceptions`、`upgrade_required`、`upgrade_target_host` 进入 carrier。

执行命令：
set -o pipefail
export AI_TEAM_RELEASE_METADATA_URL="http://192.168.1.152/yuhua/playground-Version/raw/branch/main/candidates/v0.4.7-Hotfix-1-rc2/ai-team-bundle-v0.4.7-Hotfix-1-rc2.release.json"
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash 2>&1 | tee /tmp/ai-team-install-v0.4.7-Hotfix-1-rc2.log

最终必须输出：
## ai-team v0.4.7-Hotfix-1-rc2 内网候选验收摘要
- fresh install 是否完成：是 / 否
- 实际 bundle_version / release_tag：v0.4.7-Hotfix-1-rc2 / ai-team-bundle-v0.4.7-Hotfix-1-rc2
- 渠道：release-candidate
- 00 -> 01 流程是否合法：是 / 否
- 01 回执是否被 00 消费并判断下一跳 10：是 / 否
- 10 回执是否被 00 消费并进入 await_user_next_intent：是 / 否
- Machine Receipt Carrier 是否仍含旧无效字段要求：否
- 最小机器回执是否还能继续优化：否；如不是，说明缺哪个字段仍能通过
- 是否使用 GitHub：否
- 是否切 stable：否
- 结论：通过 / 未通过，原因是...
```
