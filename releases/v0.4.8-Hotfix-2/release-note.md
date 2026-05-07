# v0.4.8-Hotfix-2 中文发版执行说明书

## 1. 这个版本做了什么

`v0.4.8-Hotfix-2` 修复 `v0.4.8-Hotfix-1` 正式内网发版后暴露出的发布后执行链失败。

这版解决四类问题：

1. `v0.4.8-Hotfix-1` 已发布但现场失败，默认 stable 不再继续指向该失败版本；失败版本保留 `postrelease_failed / quarantined` 标记。
2. 项目包初始化的正式目标统一为 `00-项目包/01...06` 六个宿主，并由 `project_package_formal_targets.json` 承载唯一机器合同。
3. `00 -> 01` 必须携带六个正式项目包宿主写入权；缺写入权时 `01` 必须 fail-closed，不得继续追问人，也不得让 `00` 派发 `10`。
4. 安装成功和失败的终端主输出改为对人友好格式，机器 URL、hash、raw JSON、prompt source 和异常栈只进入日志或 verifier evidence。

用户会得到的结果是：新安装后终端只给出安装结果、下一步口令和日志路径；第一次进入项目时复制 `/总控 请接管当前项目，并授权派发子agent`。`01` 只有在拥有六个正式宿主写入权并能形成目标级回执时才允许继续项目包初始化；`/读取回执` 只能在 `project_package_ready=true` 后把链路推进到 `10`。

本版已经完成仓内全量测试、`release_full_chain_v2` verifier verdict、candidate closeout、release note freeze 和发布仓导出。发布后 macOS / Windows 真机验收由用户继续执行；在该验收完成前，本说明不声明现场问题已完成闭环。

## 2. 让大模型去安装和更新的提示词

### 2.1 新安装

#### macOS

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.8-Hotfix-2 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用正式远端安装入口，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装完成后继续执行校验命令。
5. 任何一步失败都立即停止，不要假装成功。
6. 按设计流程验证，不在 00 / 01 / 10 之间乱跳。
7. 重点验证安装输出是否只给人类可行动信息，以及 fresh /总控、01 项目包落盘、/读取回执、10 下一跳判断。

执行命令：
set -o pipefail
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.8-Hotfix-2 2>&1 | tee /tmp/ai-team-install-v0.4.8-Hotfix-2.log

安装后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
mkdir -p /tmp/ai-team-v0.4.8-Hotfix-2-live-smoke
cd /tmp/ai-team-v0.4.8-Hotfix-2-live-smoke
git init
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry
find 00-项目包 -maxdepth 1 -type f | sort
cat ai-team.lock.json 2>/dev/null || true
cat .ai-team/runtime.json 2>/dev/null || true

live smoke：
- fresh /总控 必须返回 dispatch_target=01-编排-初始化项目包，prompt_text=null，host_native_dispatch.required_tool=spawn_agent。
- 00 -> 01 的派发输入必须包含 00-项目包/01...06 六个 formal_writable_targets。
- 01 完成后必须真实创建或补齐 00-项目包/01...06 六个正式宿主。
- 用 01 Terminal Receipt 执行 read_receipt，验证 00 可消费并且只在 project_package_ready=true 后判断下一跳为 10。
- 用缺少六个正式宿主或 project_package_result_ref_* 的 01 回执做负向验证，确认 00 fail-closed。

最终必须输出：
## ai-team v0.4.8-Hotfix-2 安装现场验收摘要
- 是否真的完成了新安装：是 / 否
- 实际安装到的 bundle_version / release_tag：v0.4.8-Hotfix-2 / ai-team-bundle-v0.4.8-Hotfix-2
- 安装主输出是否对人友好：是 / 否
- ai-team doctor 的关键字段：machine_vs_project=...；risk_level=...；recommended_action=...
- fresh /总控：decision=...；dispatch_target=...；prompt_text=null；host_native_dispatch.required_tool=spawn_agent
- 01 formal_writable_targets 是否覆盖六个正式宿主：是 / 否
- 01 是否真实创建 00-项目包/01...06：是 / 否
- 01 回执消费：decision=...；dispatch_target=...
- 缺目标级结构化 ref 负向验证：decision=receipt_blocked / 其他
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block：否
- 现场验收结论：通过 / 未通过，原因是...
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.8-Hotfix-2 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用正式远端安装入口，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装完成后继续执行校验命令。
5. 任何一步失败都立即停止，不要假装成功。
6. 按设计流程验证，不在 00 / 01 / 10 之间乱跳。
7. 重点验证安装输出是否只给人类可行动信息，以及 fresh /总控、01 项目包落盘、/读取回执、10 下一跳判断。

执行命令：
$script = Join-Path $env:TEMP "install-ai-team-v0.4.8-Hotfix-2.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.8-Hotfix-2 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-install-v0.4.8-Hotfix-2.log"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

安装后继续执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
New-Item -ItemType Directory -Force "$env:TEMP\\ai-team-v0.4.8-Hotfix-2-live-smoke" | Out-Null
Set-Location "$env:TEMP\\ai-team-v0.4.8-Hotfix-2-live-smoke"
git init
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry
Get-ChildItem "00-项目包" -File -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -ExpandProperty Name
Get-Content ai-team.lock.json -ErrorAction SilentlyContinue
Get-Content .ai-team\\runtime.json -ErrorAction SilentlyContinue

live smoke：
- fresh /总控 必须返回 dispatch_target=01-编排-初始化项目包，prompt_text=null，host_native_dispatch.required_tool=spawn_agent。
- 00 -> 01 的派发输入必须包含 00-项目包/01...06 六个 formal_writable_targets。
- 01 完成后必须真实创建或补齐 00-项目包/01...06 六个正式宿主。
- 用 01 Terminal Receipt 执行 read_receipt，验证 00 可消费并且只在 project_package_ready=true 后判断下一跳为 10。
- 用缺少六个正式宿主或 project_package_result_ref_* 的 01 回执做负向验证，确认 00 fail-closed。

最终必须输出：
## ai-team v0.4.8-Hotfix-2 安装现场验收摘要
- 是否真的完成了新安装：是 / 否
- 实际安装到的 bundle_version / release_tag：v0.4.8-Hotfix-2 / ai-team-bundle-v0.4.8-Hotfix-2
- 安装主输出是否对人友好：是 / 否
- ai-team doctor 的关键字段：machine_vs_project=...；risk_level=...；recommended_action=...
- fresh /总控：decision=...；dispatch_target=...；prompt_text=null；host_native_dispatch.required_tool=spawn_agent
- 01 formal_writable_targets 是否覆盖六个正式宿主：是 / 否
- 01 是否真实创建 00-项目包/01...06：是 / 否
- 01 回执消费：decision=...；dispatch_target=...
- 缺目标级结构化 ref 负向验证：decision=receipt_blocked / 其他
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block：否
- 现场验收结论：通过 / 未通过，原因是...
```

### 2.2 更新

#### macOS

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.8-Hotfix-2 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集 which ai-team 与 ai-team doctor。
3. 使用正式远端安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新完成后继续执行校验命令。
6. 任何一步失败都立即停止，不要假装成功。

执行命令：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team || true
ai-team doctor --project-root . || true
set -o pipefail
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.8-Hotfix-2 2>&1 | tee /tmp/ai-team-update-v0.4.8-Hotfix-2.log

更新后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry
cat ai-team.lock.json 2>/dev/null || true
cat .ai-team/runtime.json 2>/dev/null || true

最终必须输出：
## ai-team v0.4.8-Hotfix-2 更新现场验收摘要
- 是否真的完成了更新：是 / 否
- 更新前后的 which ai-team：...
- 更新前后的 ai-team doctor 关键字段：...
- 实际安装到的 bundle_version / release_tag：v0.4.8-Hotfix-2 / ai-team-bundle-v0.4.8-Hotfix-2
- ai-team runtime --action total_control_entry 的结果：decision=...；dispatch_target=...；prompt_text=null
- 安装主输出是否对人友好：是 / 否
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block：否
- 现场验收结论：通过 / 未通过，原因是...
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.8-Hotfix-2 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集 where.exe ai-team 与 ai-team doctor。
3. 使用正式远端安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新完成后继续执行校验命令。
6. 任何一步失败都立即停止，不要假装成功。

执行命令：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team doctor --project-root .
$script = Join-Path $env:TEMP "install-ai-team-v0.4.8-Hotfix-2.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.8-Hotfix-2 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-update-v0.4.8-Hotfix-2.log"
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
## ai-team v0.4.8-Hotfix-2 更新现场验收摘要
- 是否真的完成了更新：是 / 否
- 更新前后的 where.exe ai-team：...
- 更新前后的 ai-team doctor 关键字段：...
- 实际安装到的 bundle_version / release_tag：v0.4.8-Hotfix-2 / ai-team-bundle-v0.4.8-Hotfix-2
- ai-team runtime --action total_control_entry 的结果：decision=...；dispatch_target=...；prompt_text=null
- 安装主输出是否对人友好：是 / 否
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block：否
- 现场验收结论：通过 / 未通过，原因是...
```
