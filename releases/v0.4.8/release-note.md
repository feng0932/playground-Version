# v0.4.8 中文发版执行说明书

## 1. 这个版本做了什么

`v0.4.8` 修复 `v0.4.7-Hotfix-1` 正式内网发版后暴露出的现场体验问题：`01 / 10` 能跑通控制链，但把人的想法掏得不够扎实；`00` 派发给子 agent 的 prompt 偏重，包含过多非当前任务必要的信息。

这版解决两件事：

1. `01-编排-初始化项目包` 和 `10-执行-产品专家` 的 role prompt 从长模板型压缩为发现内核，保留新项目 / 历史项目接管、项目级发现、模块级发现、未确认不得 formalize、最小 fail-closed 和按当前机器回执合同交回。
2. 长模板、长检查表、字段枚举、目录骨架、机器合同和脚本参数不再靠塞进 `01 / 10` prompt 正文承载，而是保留在正式宿主、builder / validator / consumer / resolver 和测试里，避免用删除能力换取行数下降。

用户会得到的结果是：`00 -> 01 -> /读取回执 -> 10 -> /读取回执 -> await_user_next_intent` 仍按 `v0.4.x` 稳定控制链闭合；`01 / 10` 对人追问更聚焦，首轮不会直接把未确认想法 formalize 成 PRD；机器回执仍保持 `00` 可消费的最小结构。

本版已完成仓内回归、candidate 构建、本机 fresh install / doctor / runtime smoke、`01 / 10` 回执消费 smoke 和一条真实业务长对话验收。`v0.4.8` 没有迁入 `v0.5.0` 新流程；`v0.5.0` 只作为 `01 / 10` 如何追问人的想法的方法输入。

## 2. 让大模型去安装和更新的提示词

### 2.1 新安装

#### macOS

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.8 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用正式远端安装入口，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装完成后继续执行校验命令。
5. 任何一步失败都立即停止，不要假装成功。
6. 按设计流程验证，不在 00 / 01 / 10 之间乱跳。
7. 重点验证 fresh /总控、/读取回执 消费 01、/读取回执 消费 10、10 完成后 fresh /总控 等待人的下一步意图，以及 runtime prompt_text 为空。

执行命令：
set -o pipefail
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.8 2>&1 | tee /tmp/ai-team-install-v0.4.8.log

安装后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
mkdir -p /tmp/ai-team-v0.4.8-live-smoke
cd /tmp/ai-team-v0.4.8-live-smoke
git init
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry
cat ai-team.lock.json 2>/dev/null || true
cat .ai-team/runtime.json 2>/dev/null || true

live smoke：
- 如果 total_control_entry 返回 host_native_dispatch.required_tool=spawn_agent，只记录真实可派发目标，不要跳过 01。
- 用一份符合最小结构的 01 Terminal Receipt 执行 read_receipt，验证 00 可消费并判断下一跳为 10。
- 用一份符合最小结构的 10 Terminal Receipt 执行 read_receipt，再执行 fresh total_control_entry，验证不回 01，而是等待人的下一步意图。
- 用缺少必要结构化 ref 的 10 Terminal Receipt 做负向验证，确认 00 fail-closed。

最终必须输出：
- 是否真的完成了新安装
- 实际安装到的 bundle_version / release_tag
- ai-team doctor 的关键字段
- fresh /总控 的 dispatch_target 和 prompt_text
- 01 回执是否被 00 消费并判断下一跳为 10
- 10 回执是否被 00 消费并进入 await_user_next_intent
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- /tmp/ai-team-install-v0.4.8.log 的关键片段

输出格式必须包含：
## ai-team v0.4.8 安装现场验收摘要
- 新安装是否完成：是 / 否
- 实际安装到的 bundle_version / release_tag：v0.4.8 / ai-team-bundle-v0.4.8
- ai-team doctor 的关键字段：machine_vs_project=...；risk_level=...；recommended_action=...
- fresh /总控：decision=...；dispatch_target=...；prompt_text=null；host_native_dispatch.required_tool=spawn_agent
- 01 回执消费：decision=...；dispatch_target=...
- 10 回执消费：decision=...；dispatch_target=...
- 10 后 fresh /总控：decision=...；next_required_action=...
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block：否
- 现场验收结论：通过 / 未通过，原因是...
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.8 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用正式远端安装入口，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装完成后继续执行校验命令。
5. 任何一步失败都立即停止，不要假装成功。
6. 按设计流程验证，不在 00 / 01 / 10 之间乱跳。
7. 重点验证 fresh /总控、/读取回执 消费 01、/读取回执 消费 10、10 完成后 fresh /总控 等待人的下一步意图，以及 runtime prompt_text 为空。

执行命令：
$script = Join-Path $env:TEMP "install-ai-team-v0.4.8.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.8 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-install-v0.4.8.log"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

安装后继续执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
New-Item -ItemType Directory -Force "$env:TEMP\\ai-team-v0.4.8-live-smoke" | Out-Null
Set-Location "$env:TEMP\\ai-team-v0.4.8-live-smoke"
git init
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry
Get-Content ai-team.lock.json -ErrorAction SilentlyContinue
Get-Content .ai-team\\runtime.json -ErrorAction SilentlyContinue

live smoke：
- 如果 total_control_entry 返回 host_native_dispatch.required_tool=spawn_agent，只记录真实可派发目标，不要跳过 01。
- 用一份符合最小结构的 01 Terminal Receipt 执行 read_receipt，验证 00 可消费并判断下一跳为 10。
- 用一份符合最小结构的 10 Terminal Receipt 执行 read_receipt，再执行 fresh total_control_entry，验证不回 01，而是等待人的下一步意图。
- 用缺少必要结构化 ref 的 10 Terminal Receipt 做负向验证，确认 00 fail-closed。

最终必须输出：
- 是否真的完成了新安装
- 实际安装到的 bundle_version / release_tag
- ai-team doctor 的关键字段
- fresh /总控 的 dispatch_target 和 prompt_text
- 01 回执是否被 00 消费并判断下一跳为 10
- 10 回执是否被 00 消费并进入 await_user_next_intent
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- $env:TEMP\\ai-team-install-v0.4.8.log 的关键片段

输出格式必须包含：
## ai-team v0.4.8 安装现场验收摘要
- 新安装是否完成：是 / 否
- 实际安装到的 bundle_version / release_tag：v0.4.8 / ai-team-bundle-v0.4.8
- ai-team doctor 的关键字段：machine_vs_project=...；risk_level=...；recommended_action=...
- fresh /总控：decision=...；dispatch_target=...；prompt_text=null；host_native_dispatch.required_tool=spawn_agent
- 01 回执消费：decision=...；dispatch_target=...
- 10 回执消费：decision=...；dispatch_target=...
- 10 后 fresh /总控：decision=...；next_required_action=...
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block：否
- 现场验收结论：通过 / 未通过，原因是...
```

### 2.2 更新

#### macOS

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.8 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集 which ai-team 与 ai-team doctor。
3. 使用正式远端安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新完成后继续执行校验命令。
6. 任何一步失败都立即停止，不要假装成功。
7. 按设计流程验证，不在 00 / 01 / 10 之间乱跳。

执行命令：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team || true
ai-team doctor --project-root . || true
set -o pipefail
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.8 2>&1 | tee /tmp/ai-team-update-v0.4.8.log

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
- /tmp/ai-team-update-v0.4.8.log 的关键片段

输出格式必须包含：
## ai-team v0.4.8 更新现场验收摘要
- 是否真的完成了更新：是 / 否
- 更新前后的 which ai-team：...
- 更新前后的 ai-team doctor 关键字段：...
- 实际安装到的 bundle_version / release_tag：v0.4.8 / ai-team-bundle-v0.4.8
- ai-team runtime --action total_control_entry 的结果：decision=...；dispatch_target=...
- ai-team.lock.json 和 .ai-team/runtime.json 的关键内容：bundle_version=...；release_tag=...
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block：否
- 现场验收结论：通过 / 未通过，原因是...
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.8 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集 where.exe ai-team 与 ai-team doctor。
3. 使用正式远端安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新完成后继续执行校验命令。
6. 任何一步失败都立即停止，不要假装成功。
7. 按设计流程验证，不在 00 / 01 / 10 之间乱跳。

执行命令：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team doctor --project-root .
$script = Join-Path $env:TEMP "install-ai-team-v0.4.8.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.8 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-update-v0.4.8.log"
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
- $env:TEMP\\ai-team-update-v0.4.8.log 的关键片段

输出格式必须包含：
## ai-team v0.4.8 更新现场验收摘要
- 是否真的完成了更新：是 / 否
- 更新前后的 where.exe ai-team：...
- 更新前后的 ai-team doctor 关键字段：...
- 实际安装到的 bundle_version / release_tag：v0.4.8 / ai-team-bundle-v0.4.8
- ai-team runtime --action total_control_entry 的结果：decision=...；dispatch_target=...
- ai-team.lock.json 和 .ai-team\\runtime.json 的关键内容：bundle_version=...；release_tag=...
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block：否
- 现场验收结论：通过 / 未通过，原因是...
```

