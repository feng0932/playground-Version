# v0.4.8-Hotfix-3 中文发版执行说明书

## 1. 这个版本做了什么

`v0.4.8-Hotfix-3` 是对 `v0.4.8-Hotfix-1 / Hotfix-2` 发布后现场失败的完全重做版。

这个版本重点修复安装执行链和回执消费链：安装完成后输出改为对人友好的最小提示；项目 runtime ready 后，`/总控` 只返回 Codex `spawn_agent` 派发请求，不把子线程 prompt 灌回主窗口；`01` 写入项目包六个正式宿主后，如果还没有确认交付模式、active module set、模块结构和 `next_10_writable_targets`，`/读取回执` 不再派发 `10-执行-产品专家`，而是回到 `01` 补齐结构，避免产品专家没有 PRD 写入目标仍继续追问。

本次发布 macOS fresh / update 已实跑，真实 Codex `spawn_agent` 派发 `01` 已实跑。Windows 当前没有可用环境，按用户授权以模拟证据进入本次发布；后续恢复 Windows 环境后仍需补跑 Windows fresh / update。

## 2. 让大模型去安装和更新的提示词

### 2.1 新安装

#### macOS

把下面这段直接发给大模型：

```text
你现在要在 macOS 上实际执行 ai-team v0.4.8-Hotfix-3 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

前置检查：
1. 确认 shell 可用。
2. 确认可以访问 http://192.168.1.152/。
3. 确认目标项目目录可写。

执行要求：
1. 使用正式远端安装入口，不要手工拼装 bundle。
2. 保留完整 stdout/stderr。
3. 任一步失败即停止，不得脑补成功。

命令：

set -o pipefail
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.8-Hotfix-3 2>&1 | tee /tmp/ai-team-install-v0.4.8-Hotfix-3.log

安装后继续运行：

which ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry

最终输出：
1. 是否真的完成了新安装。
2. 实际 bundle_version / release_tag。
3. doctor 的 machine_vs_project / risk_level / recommended_action。
4. runtime 的 decision / dispatch_target / prompt_text / host_native_dispatch.required_tool。
5. 是否出现 checksum mismatch、metadata fetch failure、downgrade block。
6. 安装主输出是否对人友好，并贴出安装完成后的主输出片段。
7. 下一步提示语是否为：/总控 请接管当前项目，并授权派发子agent。
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在 Windows PowerShell 上实际执行 ai-team v0.4.8-Hotfix-3 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

前置检查：
1. 确认 PowerShell 可用。
2. 确认可以访问 http://192.168.1.152/。
3. 确认目标项目目录可写。

执行要求：
1. 使用正式远端安装入口，不要手工拼装 bundle。
2. 保留完整 stdout/stderr。
3. 任一步失败即停止，不得脑补成功。

命令：

$script = Join-Path $env:TEMP "install-ai-team-v0.4.8-Hotfix-3.ps1"
Invoke-WebRequest -UseBasicParsing -Uri "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1" -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.8-Hotfix-3 *>&1 | Tee-Object -FilePath "$env:TEMP\ai-team-install-v0.4.8-Hotfix-3.log"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

安装后继续运行：

where.exe ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry

最终输出：
1. 是否真的完成了新安装。
2. 实际 bundle_version / release_tag。
3. doctor 的 machine_vs_project / risk_level / recommended_action。
4. runtime 的 decision / dispatch_target / prompt_text / host_native_dispatch.required_tool。
5. 是否出现 checksum mismatch、metadata fetch failure、downgrade block。
6. 安装主输出是否对人友好，并贴出安装完成后的主输出片段。
7. 下一步提示语是否为：/总控 请接管当前项目，并授权派发子agent。
```

### 2.2 更新

#### macOS

把下面这段直接发给大模型：

```text
你现在要在 macOS 上实际执行 ai-team v0.4.8-Hotfix-3 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

前置检查：
1. 确认 shell 可用。
2. 确认可以访问 http://192.168.1.152/。
3. 确认目标项目目录可写。

更新前先采集：

which ai-team || true
ai-team doctor --project-root . || true

执行要求：
1. 使用正式远端安装入口，不要手工拼装 bundle。
2. 保留完整 stdout/stderr。
3. 任一步失败即停止，不得脑补成功。

命令：

set -o pipefail
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.8-Hotfix-3 2>&1 | tee /tmp/ai-team-update-v0.4.8-Hotfix-3.log

更新后继续运行：

which ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry

最终输出：
1. 是否真的完成了更新，并输出更新前后的 bundle_version / release_tag 对照。
2. 更新后 doctor 的 machine_vs_project / risk_level / recommended_action。
3. runtime 的 decision / dispatch_target / prompt_text / host_native_dispatch.required_tool。
4. 是否出现 checksum mismatch、metadata fetch failure、downgrade block。
5. 更新主输出是否对人友好，并贴出安装完成后的主输出片段。
6. 下一步提示语是否为：/总控 请接管当前项目，并授权派发子agent。
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在 Windows PowerShell 上实际执行 ai-team v0.4.8-Hotfix-3 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

前置检查：
1. 确认 PowerShell 可用。
2. 确认可以访问 http://192.168.1.152/。
3. 确认目标项目目录可写。

更新前先采集：

where.exe ai-team
ai-team doctor --project-root .

执行要求：
1. 使用正式远端安装入口，不要手工拼装 bundle。
2. 保留完整 stdout/stderr。
3. 任一步失败即停止，不得脑补成功。

命令：

$script = Join-Path $env:TEMP "install-ai-team-v0.4.8-Hotfix-3.ps1"
Invoke-WebRequest -UseBasicParsing -Uri "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1" -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.8-Hotfix-3 *>&1 | Tee-Object -FilePath "$env:TEMP\ai-team-update-v0.4.8-Hotfix-3.log"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

更新后继续运行：

where.exe ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry

最终输出：
1. 是否真的完成了更新，并输出更新前后的 bundle_version / release_tag 对照。
2. 更新后 doctor 的 machine_vs_project / risk_level / recommended_action。
3. runtime 的 decision / dispatch_target / prompt_text / host_native_dispatch.required_tool。
4. 是否出现 checksum mismatch、metadata fetch failure、downgrade block。
5. 更新主输出是否对人友好，并贴出安装完成后的主输出片段。
6. 下一步提示语是否为：/总控 请接管当前项目，并授权派发子agent。
```
