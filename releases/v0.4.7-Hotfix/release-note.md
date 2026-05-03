# v0.4.7-Hotfix 中文发版执行说明书

## 1. 这个版本做了什么

`v0.4.7-Hotfix` 修复 `v0.4.7` 正式内网发版后暴露出的控制链问题。

这版解决三件事：

1. `/返回总控` 需要交出 `00` 能消费的机器回执，不能只留人话总结。
2. `01` 派发 `10` 前必须先问清整包还是分模块，并明确当前模块集合和正式写入目标。
3. `00` 不能为了尽快读回执，催任何子 agent 提前完工或提交未完成的最小回执。

用户会得到的结果是：`01 -> 10` 的入口更扎实，缺执行结构会被阻断，合格回执能被 `00` 直接消费；长期任务中，未完成工作不会被包装成可验收结果。

本版已完成候选构建、fresh install / doctor、`/总控 -> 01`、`/读取回执 -> 10` 和缺执行结构 fail-closed 验收。真实 Codex child 是否每次无人干预都首次写对 appendix，仍以现场 transcript 为准。

## 2. 让大模型去安装和更新的提示词

### 2.1 新安装

#### macOS

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7-Hotfix 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用正式远端安装入口，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装完成后继续执行校验命令。
5. 任何一步失败都立即停止，不要假装成功。
6. 只做安装现场验收；ai-team runtime 出现 dispatch_allowed 时，只记录 host_native_dispatch，不要继续调用 spawn_agent，也不要进入项目业务初始化。

执行命令：
set -o pipefail
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.7-Hotfix 2>&1 | tee /tmp/ai-team-install-v0.4.7-Hotfix.log

安装后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry
cat ai-team.lock.json 2>/dev/null || true
cat .ai-team/runtime.json 2>/dev/null || true
ls -la .ai-team/state 2>/dev/null || true

最终必须输出：
- 是否真的完成了新安装
- 实际安装到的 bundle_version / release_tag
- ai-team doctor 的关键字段
- ai-team runtime --action total_control_entry 的结果
- ai-team.lock.json 和 .ai-team/runtime.json 的关键内容
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- /tmp/ai-team-install-v0.4.7-Hotfix.log 的关键片段

输出格式必须包含：
## ai-team v0.4.7-Hotfix 安装现场验收摘要
- 新安装是否完成：是 / 否
- 实际安装到的 bundle_version / release_tag：v0.4.7-Hotfix / ai-team-bundle-v0.4.7-Hotfix
- ai-team doctor 的关键字段：machine_vs_project=...；risk_level=...；recommended_action=...
- ai-team runtime --action total_control_entry 的结果：decision=...；dispatch_target=...；prompt_text=null；host_native_dispatch.required_tool=spawn_agent
- ai-team.lock.json 和 .ai-team/runtime.json 的关键内容：bundle_version=...；release_tag=...
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block：否
- 现场验收结论：通过安装层 smoke；停止在安装验收，不进入项目业务初始化。
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7-Hotfix 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用正式远端安装入口，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装完成后继续执行校验命令。
5. 任何一步失败都立即停止，不要假装成功。
6. 只做安装现场验收；ai-team runtime 出现 dispatch_allowed 时，只记录 host_native_dispatch，不要继续调用 spawn_agent，也不要进入项目业务初始化。

执行命令：
$script = Join-Path $env:TEMP "install-ai-team-v0.4.7-Hotfix.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.7-Hotfix *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-install-v0.4.7-Hotfix.log"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

安装后继续执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry
Get-Content ai-team.lock.json -ErrorAction SilentlyContinue
Get-Content .ai-team\\runtime.json -ErrorAction SilentlyContinue
Get-ChildItem .ai-team\\state -Force -ErrorAction SilentlyContinue

最终必须输出：
- 是否真的完成了新安装
- 实际安装到的 bundle_version / release_tag
- ai-team doctor 的关键字段
- ai-team runtime --action total_control_entry 的结果
- ai-team.lock.json 和 .ai-team\\runtime.json 的关键内容
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- $env:TEMP\\ai-team-install-v0.4.7-Hotfix.log 的关键片段

输出格式必须包含：
## ai-team v0.4.7-Hotfix 安装现场验收摘要
- 新安装是否完成：是 / 否
- 实际安装到的 bundle_version / release_tag：v0.4.7-Hotfix / ai-team-bundle-v0.4.7-Hotfix
- ai-team doctor 的关键字段：machine_vs_project=...；risk_level=...；recommended_action=...
- ai-team runtime --action total_control_entry 的结果：decision=...；dispatch_target=...；prompt_text=null；host_native_dispatch.required_tool=spawn_agent
- ai-team.lock.json 和 .ai-team\\runtime.json 的关键内容：bundle_version=...；release_tag=...
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block：否
- 现场验收结论：通过安装层 smoke；停止在安装验收，不进入项目业务初始化。
```

### 2.2 更新

#### macOS

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7-Hotfix 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集旧状态。
3. 使用正式远端安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新完成后继续执行校验命令。
6. 任何一步失败都立即停止，不要假装成功。
7. 只做更新现场验收；ai-team runtime 出现 dispatch_allowed 时，只记录 host_native_dispatch，不要继续调用 spawn_agent，也不要进入项目业务初始化。

执行命令：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team || true
ai-team doctor --project-root . || true
set -o pipefail
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.7-Hotfix 2>&1 | tee /tmp/ai-team-update-v0.4.7-Hotfix.log

更新后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry
cat ai-team.lock.json 2>/dev/null || true
cat .ai-team/runtime.json 2>/dev/null || true

最终必须输出：
- 是否真的完成了更新
- 更新前后的 which ai-team
- 更新前后的 ai-team doctor 关键字段
- 实际安装到的 bundle_version / release_tag
- ai-team runtime --action total_control_entry 的结果
- ai-team.lock.json 和 .ai-team/runtime.json 的关键内容
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- /tmp/ai-team-update-v0.4.7-Hotfix.log 的关键片段
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7-Hotfix 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集旧状态。
3. 使用正式远端安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新完成后继续执行校验命令。
6. 任何一步失败都立即停止，不要假装成功。
7. 只做更新现场验收；ai-team runtime 出现 dispatch_allowed 时，只记录 host_native_dispatch，不要继续调用 spawn_agent，也不要进入项目业务初始化。

执行命令：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team doctor --project-root . *>&1
$script = Join-Path $env:TEMP "install-ai-team-v0.4.7-Hotfix.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.7-Hotfix *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-update-v0.4.7-Hotfix.log"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

更新后继续执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry
Get-Content ai-team.lock.json -ErrorAction SilentlyContinue
Get-Content .ai-team\\runtime.json -ErrorAction SilentlyContinue

最终必须输出：
- 是否真的完成了更新
- 更新前后的 where.exe ai-team
- 更新前后的 ai-team doctor 关键字段
- 实际安装到的 bundle_version / release_tag
- ai-team runtime --action total_control_entry 的结果
- ai-team.lock.json 和 .ai-team\\runtime.json 的关键内容
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- $env:TEMP\\ai-team-update-v0.4.7-Hotfix.log 的关键片段
```
