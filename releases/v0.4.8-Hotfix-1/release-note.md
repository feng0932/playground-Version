# v0.4.8-Hotfix-1 中文发版执行说明书

## 1. 这个版本做了什么

`v0.4.8-Hotfix-1` 修复 `v0.4.8` 正式安装后暴露的安装执行链验收缺口和安装交接体验问题。

这版解决三件事：

1. 正式发版的稳定指针切换、候选收口、发版说明冻结和发布仓导出，必须消费可从同一现场 session 重放出来的 `release_full_chain` verifier verdict；字段完整但不可重放的手写 verdict 不再能放行。
2. 安装完成后的终端主输出改为面向人的最小交接：只说明机器入口、项目运行时、进入方法论的下一步和日志位置，不再把长 prompt 正文直接打到终端。
3. 安装失败输出改为固定结构加动态原因：明确卡住位置、真实原因、下一步动作和当前状态，不再把不同失败统一写成同一种原因。

用户会得到的结果是：正式安装后能清楚看到下一步应该在项目根目录打开 Codex，并输入 `/总控 请接管当前项目，并授权派发子agent`；发布链路也会在正式切 stable pointer 前阻断不可追溯的人工放行材料。

## 2. 让大模型去安装和更新的提示词

### 2.1 新安装

#### macOS

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.8-Hotfix-1 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用正式远端安装入口，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装完成后继续执行校验命令。
5. 任何一步失败都立即停止，不要假装成功。
6. 安装成功后确认终端主输出包含：在项目根目录打开 Codex，输入：/总控 请接管当前项目，并授权派发子agent。
7. 按设计流程验证 fresh /总控、/读取回执 消费 01、/读取回执 消费 10、10 完成后 fresh /总控 等待人的下一步意图，且 runtime prompt_text 为空。

执行命令：
set -o pipefail
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.8-Hotfix-1 2>&1 | tee /tmp/ai-team-install-v0.4.8-Hotfix-1.log

安装后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
mkdir -p /tmp/ai-team-v0.4.8-Hotfix-1-live-smoke
cd /tmp/ai-team-v0.4.8-Hotfix-1-live-smoke
git init
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry
cat ai-team.lock.json 2>/dev/null || true
cat .ai-team/runtime.json 2>/dev/null || true

最终必须输出：
- 是否真的完成了新安装
- 实际安装到的 bundle_version / release_tag
- ai-team doctor 的关键字段
- fresh /总控 的 dispatch_target 和 prompt_text
- 01 回执是否被 00 消费并判断下一跳为 10
- 10 回执是否被 00 消费并进入 await_user_next_intent
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- /tmp/ai-team-install-v0.4.8-Hotfix-1.log 的关键片段
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.8-Hotfix-1 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用正式远端安装入口，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装完成后继续执行校验命令。
5. 任何一步失败都立即停止，不要假装成功。
6. 安装成功后确认终端主输出包含：在项目根目录打开 Codex，输入：/总控 请接管当前项目，并授权派发子agent。
7. 按设计流程验证 fresh /总控、/读取回执 消费 01、/读取回执 消费 10、10 完成后 fresh /总控 等待人的下一步意图，且 runtime prompt_text 为空。

执行命令：
$script = Join-Path $env:TEMP "install-ai-team-v0.4.8-Hotfix-1.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.8-Hotfix-1 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-install-v0.4.8-Hotfix-1.log"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

安装后继续执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
New-Item -ItemType Directory -Force "$env:TEMP\\ai-team-v0.4.8-Hotfix-1-live-smoke" | Out-Null
Set-Location "$env:TEMP\\ai-team-v0.4.8-Hotfix-1-live-smoke"
git init
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry
Get-Content ai-team.lock.json -ErrorAction SilentlyContinue
Get-Content .ai-team\\runtime.json -ErrorAction SilentlyContinue

最终必须输出：
- 是否真的完成了新安装
- 实际安装到的 bundle_version / release_tag
- ai-team doctor 的关键字段
- fresh /总控 的 dispatch_target 和 prompt_text
- 01 回执是否被 00 消费并判断下一跳为 10
- 10 回执是否被 00 消费并进入 await_user_next_intent
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- $env:TEMP\\ai-team-install-v0.4.8-Hotfix-1.log 的关键片段
```

### 2.2 更新

#### macOS

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.8-Hotfix-1 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集 which ai-team 与 ai-team doctor。
3. 使用正式远端安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新完成后继续执行校验命令。
6. 任何一步失败都立即停止，不要假装成功。
7. 更新成功后确认终端主输出包含：在项目根目录打开 Codex，输入：/总控 请接管当前项目，并授权派发子agent。

执行命令：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team || true
ai-team doctor --project-root . || true
set -o pipefail
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.8-Hotfix-1 2>&1 | tee /tmp/ai-team-update-v0.4.8-Hotfix-1.log

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
- /tmp/ai-team-update-v0.4.8-Hotfix-1.log 的关键片段
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.8-Hotfix-1 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集 where.exe ai-team 与 ai-team doctor。
3. 使用正式远端安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新完成后继续执行校验命令。
6. 任何一步失败都立即停止，不要假装成功。
7. 更新成功后确认终端主输出包含：在项目根目录打开 Codex，输入：/总控 请接管当前项目，并授权派发子agent。

执行命令：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team doctor --project-root .
$script = Join-Path $env:TEMP "install-ai-team-v0.4.8-Hotfix-1.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.8-Hotfix-1 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-update-v0.4.8-Hotfix-1.log"
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
- $env:TEMP\\ai-team-update-v0.4.8-Hotfix-1.log 的关键片段
```
