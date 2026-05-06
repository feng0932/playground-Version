# v0.4.7-Hotfix-1-rc2 内网候选发版执行说明书

## 1. 这个版本做了什么

`v0.4.7-Hotfix-1-rc2` 是 `v0.4.7-Hotfix-1` 的第二个内网预发候选版，不是正式 stable。

相对 `rc1`，本版修正了 `10-执行-产品专家` raw role prompt 里残留的旧机器回执说明：`layer_consumed`、`inherited_hosts_checked`、`module_exceptions`、`upgrade_required`、`upgrade_target_host` 只能落入正式 PRD 证据或结构化阻塞包，不得额外塞入 `Machine Receipt Carrier`。

这版继续验证两件事：

1. `10 completed + no_primary_window_next_hop` 之后，fresh `/总控` 不再反复派回 `01`，而是等待人的下一步意图。
2. `01 / 10` 的机器回执保持最小可消费结构，`00` 可通过 `/读取回执` 消费，并据此判断下一跳。

本候选不切 stable pointer，不创建正式 release，不做 GitHub 发布或镜像。

## 2. 让大模型去安装和更新的提示词

### 2.1 新安装

#### macOS

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

安装后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
mkdir -p /tmp/ai-team-v0.4.7-Hotfix-1-rc2-live-smoke
cd /tmp/ai-team-v0.4.7-Hotfix-1-rc2-live-smoke
git init
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry

live smoke：
- 如果 total_control_entry 返回 host_native_dispatch.required_tool=spawn_agent，只记录真实可派发目标，不要跳过 01。
- 用一份符合最小结构的 01 Terminal Receipt 执行 read_receipt，验证 00 可消费并判断下一跳为 10。
- 用一份符合最小结构的 10 Terminal Receipt 执行 read_receipt，再执行 fresh total_control_entry，验证不回 01，而是等待人的下一步意图。
- 用缺少必要结构化 ref 的 10 Terminal Receipt 做负向验证，确认 00 fail-closed。
- 检查 Machine Receipt Carrier 不再要求 `layer_consumed`、`inherited_hosts_checked`、`module_exceptions`、`upgrade_required`、`upgrade_target_host` 进入 carrier。

最终必须输出：
## ai-team v0.4.7-Hotfix-1-rc2 内网候选验收摘要
- 是否真的完成了新安装：是 / 否
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

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7-Hotfix-1-rc2 的内网候选新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

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
$env:AI_TEAM_RELEASE_METADATA_URL = "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/candidates/v0.4.7-Hotfix-1-rc2/ai-team-bundle-v0.4.7-Hotfix-1-rc2.release.json"
$script = Join-Path $env:TEMP "install-ai-team-v0.4.7-Hotfix-1-rc2.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-install-v0.4.7-Hotfix-1-rc2.log"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

安装后继续执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
New-Item -ItemType Directory -Force "$env:TEMP\\ai-team-v0.4.7-Hotfix-1-rc2-live-smoke" | Out-Null
Set-Location "$env:TEMP\\ai-team-v0.4.7-Hotfix-1-rc2-live-smoke"
git init
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry

live smoke：
- 如果 total_control_entry 返回 host_native_dispatch.required_tool=spawn_agent，只记录真实可派发目标，不要跳过 01。
- 用一份符合最小结构的 01 Terminal Receipt 执行 read_receipt，验证 00 可消费并判断下一跳为 10。
- 用一份符合最小结构的 10 Terminal Receipt 执行 read_receipt，再执行 fresh total_control_entry，验证不回 01，而是等待人的下一步意图。
- 用缺少必要结构化 ref 的 10 Terminal Receipt 做负向验证，确认 00 fail-closed。
- 检查 Machine Receipt Carrier 不再要求 `layer_consumed`、`inherited_hosts_checked`、`module_exceptions`、`upgrade_required`、`upgrade_target_host` 进入 carrier。

最终必须输出：
## ai-team v0.4.7-Hotfix-1-rc2 内网候选验收摘要
- 是否真的完成了新安装：是 / 否
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

### 2.2 更新

#### macOS

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7-Hotfix-1-rc2 的内网候选更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 更新前先采集 which ai-team 与 ai-team doctor。
2. 只使用内部 Gitea 候选入口，不使用 GitHub。
3. 本版本是 release-candidate，不是 stable。
4. 不切 stable pointer，不创建正式 release。
5. 保留完整 stdout/stderr。
6. 任一步失败都立即停止，不要脑补成功。

执行命令：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team || true
ai-team doctor --project-root . || true
set -o pipefail
export AI_TEAM_RELEASE_METADATA_URL="http://192.168.1.152/yuhua/playground-Version/raw/branch/main/candidates/v0.4.7-Hotfix-1-rc2/ai-team-bundle-v0.4.7-Hotfix-1-rc2.release.json"
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash 2>&1 | tee /tmp/ai-team-update-v0.4.7-Hotfix-1-rc2.log

更新后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry

最终必须输出：
## ai-team v0.4.7-Hotfix-1-rc2 内网候选更新验收摘要
- 是否真的完成了更新：是 / 否
- 更新前后的 which ai-team：...
- 更新前后的 ai-team doctor 关键字段：...
- 实际 bundle_version / release_tag：v0.4.7-Hotfix-1-rc2 / ai-team-bundle-v0.4.7-Hotfix-1-rc2
- 渠道：release-candidate
- 是否使用 GitHub：否
- 是否切 stable：否
- 结论：通过 / 未通过，原因是...
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7-Hotfix-1-rc2 的内网候选更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 更新前先采集 where.exe ai-team 与 ai-team doctor。
2. 只使用内部 Gitea 候选入口，不使用 GitHub。
3. 本版本是 release-candidate，不是 stable。
4. 不切 stable pointer，不创建正式 release。
5. 保留完整 stdout/stderr。
6. 任一步失败都立即停止，不要脑补成功。

执行命令：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team doctor --project-root .
$env:AI_TEAM_RELEASE_METADATA_URL = "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/candidates/v0.4.7-Hotfix-1-rc2/ai-team-bundle-v0.4.7-Hotfix-1-rc2.release.json"
$script = Join-Path $env:TEMP "install-ai-team-v0.4.7-Hotfix-1-rc2.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-update-v0.4.7-Hotfix-1-rc2.log"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

更新后继续执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry

最终必须输出：
## ai-team v0.4.7-Hotfix-1-rc2 内网候选更新验收摘要
- 是否真的完成了更新：是 / 否
- 更新前后的 where.exe ai-team：...
- 更新前后的 ai-team doctor 关键字段：...
- 实际 bundle_version / release_tag：v0.4.7-Hotfix-1-rc2 / ai-team-bundle-v0.4.7-Hotfix-1-rc2
- 渠道：release-candidate
- 是否使用 GitHub：否
- 是否切 stable：否
- 结论：通过 / 未通过，原因是...
```
