# v0.4.7-test.3 中文发版执行说明书

## 1. 这个版本做了什么

`v0.4.7-test.3` 是 `v0.4.7` 的第三次真实安装和控制链路测试版，不是正式稳定版。

这版修掉了 `v0.4.7-test.1` 和 `v0.4.7-test.2` 真实链路测试连续发现的两个 release-gate 问题：

1. `00` 读取 `00-沟通记录与结论回写.md` 时，如果文件里已经有多段子线程回执，运行时现在会读取最后一段 `Terminal Receipt`，不会再把整份过程文件当作一个回执而因为重复的 `工单回执 / dispatch_evidence` 标题失败。
2. 子线程真实写出的回执里，`read_what / changed_what / ran_what / evidence / blockers / next` 这类字段如果是“字段名 + 缩进列表”，机器校验器现在能正常消费，不会再误判成字段缺失。

这版要验证的不是“产品方法论已经完整成熟”，而是先把最关键的运行链路拿到真实证据：

1. 测试包能不能从发布入口被安装。
2. 安装后的项目里，版本号是不是 `v0.4.7-test.3`。
3. `/总控` 能不能生成真实派发。
4. 宿主能不能真的创建子线程。
5. 子线程能不能读取派发文件，而不是自己开聊。
6. 子线程能不能生成正式回执。
7. `00` 能不能从过程文件里读取最新一段回执，并正确消费子线程真实写出的列表型字段。
8. 如果需要下一跳，宿主能不能再次创建新子线程。

这版已经把 `CR-005` 放进候选链路：产品经理在 `01` 或 `10` 里中断、改方向、回上一步、跨模块回修时，AI 不能把人锁在流程里，必须把人的决定带回 `00` 总控重新判断。

这版仍然不解决 `CR-004`。也就是说，行业级完整产品发现体系、产品专家进一步把人的想法掏深、项目说明书正式质量提升，都不在本次测试版里宣布完成。

本版测试通过后，只能说：

- `v0.4.7-test.3 真实安装和控制链路通过。`

不能说：

- `v0.4.7 是正式稳定版。`
- `产品方法论能力完整达标。`
- `项目说明书成型能力已经正式达标。`

## 2. 让大模型去安装和更新的提示词

设备选择：

### 2.1 新安装

#### macOS

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7-test.3 的测试版新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用测试版发布入口，不要手工拼装 bundle。
3. 本版本是 release-candidate（候选/测试渠道），不是 stable（正式稳定渠道）。
4. 保留完整 stdout/stderr。
5. 安装完成后继续执行校验命令。
6. 任何一步失败都立即停止，不要假装成功。
7. 只做安装现场验收和总控入口检查；如果 ai-team runtime 出现 dispatch_allowed，只记录 host_native_dispatch，不要在安装验收阶段继续调用 spawn_agent。
8. 后续真实控制链路验证必须另存 session json 或 session jsonl。

执行命令：
set -o pipefail
export AI_TEAM_RELEASE_METADATA_URL="http://192.168.1.152/yuhua/playground-Version/raw/branch/main/candidates/v0.4.7-test.3/ai-team-bundle-v0.4.7-test.3.release.json"
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash 2>&1 | tee /tmp/ai-team-install-v0.4.7-test.3.log

安装后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
mkdir -p /tmp/ai-team-v0.4.7-test.3-smoke
cd /tmp/ai-team-v0.4.7-test.3-smoke
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
- /tmp/ai-team-install-v0.4.7-test.3.log 的关键片段
- 后续真实 session json / session jsonl 应保存到哪里

输出格式必须包含：
## ai-team v0.4.7-test.3 安装现场验收摘要
- 新安装是否完成：是 / 否
- 实际安装到的 bundle_version / release_tag：v0.4.7-test.3 / ai-team-bundle-v0.4.7-test.3
- 渠道：release-candidate
- ai-team doctor 的关键字段：machine_vs_project=...；risk_level=...；recommended_action=...
- ai-team runtime --action total_control_entry 的结果：decision=...；dispatch_target=...；prompt_text=null；host_native_dispatch.required_tool=spawn_agent
- ai-team.lock.json 和 .ai-team/runtime.json 的关键内容：bundle_version=...；release_tag=...
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block：否
- 现场验收结论：通过安装层 smoke / 未通过，原因是...
- 真实控制链路验证证据：等待 session json 或 session jsonl。
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7-test.3 的测试版新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用测试版发布入口，不要手工拼装 bundle。
3. 本版本是 release-candidate（候选/测试渠道），不是 stable（正式稳定渠道）。
4. 保留完整 stdout/stderr。
5. 安装完成后继续执行校验命令。
6. 任何一步失败都立即停止，不要假装成功。
7. 只做安装现场验收和总控入口检查；如果 ai-team runtime 出现 dispatch_allowed，只记录 host_native_dispatch，不要在安装验收阶段继续调用 spawn_agent。
8. 后续真实控制链路验证必须另存 session json 或 session jsonl。

执行命令：
$env:AI_TEAM_RELEASE_METADATA_URL = "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/candidates/v0.4.7-test.3/ai-team-bundle-v0.4.7-test.3.release.json"
$script = Join-Path $env:TEMP "install-ai-team-v0.4.7-test.3.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-install-v0.4.7-test.3.log"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

安装后继续执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
$smoke = Join-Path $env:TEMP "ai-team-v0.4.7-test.3-smoke"
New-Item -ItemType Directory -Force -Path $smoke | Out-Null
Set-Location $smoke
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
- $env:TEMP\\ai-team-install-v0.4.7-test.3.log 的关键片段
- 后续真实 session json / session jsonl 应保存到哪里

输出格式必须包含：
## ai-team v0.4.7-test.3 安装现场验收摘要
- 新安装是否完成：是 / 否
- 实际安装到的 bundle_version / release_tag：v0.4.7-test.3 / ai-team-bundle-v0.4.7-test.3
- 渠道：release-candidate
- ai-team doctor 的关键字段：machine_vs_project=...；risk_level=...；recommended_action=...
- ai-team runtime --action total_control_entry 的结果：decision=...；dispatch_target=...；prompt_text=null；host_native_dispatch.required_tool=spawn_agent
- ai-team.lock.json 和 .ai-team\\runtime.json 的关键内容：bundle_version=...；release_tag=...
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block：否
- 现场验收结论：通过安装层 smoke / 未通过，原因是...
- 真实控制链路验证证据：等待 session json 或 session jsonl。
```

### 2.2 更新

#### macOS

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7-test.3 的测试版更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集旧状态。
3. 使用测试版发布入口执行更新，不要手工拼装 bundle。
4. 本版本是 release-candidate（候选/测试渠道），不是 stable（正式稳定渠道）。
5. 保留完整 stdout/stderr。
6. 更新完成后继续执行校验命令。
7. 任何一步失败都立即停止，不要假装成功。
8. 只做更新现场验收和总控入口检查；如果 ai-team runtime 出现 dispatch_allowed，只记录 host_native_dispatch，不要在安装验收阶段继续调用 spawn_agent。
9. 后续真实控制链路验证必须另存 session json 或 session jsonl。

执行命令：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team || true
ai-team doctor --project-root . || true
set -o pipefail
export AI_TEAM_RELEASE_METADATA_URL="http://192.168.1.152/yuhua/playground-Version/raw/branch/main/candidates/v0.4.7-test.3/ai-team-bundle-v0.4.7-test.3.release.json"
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash 2>&1 | tee /tmp/ai-team-update-v0.4.7-test.3.log

更新后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
mkdir -p /tmp/ai-team-v0.4.7-test.3-smoke
cd /tmp/ai-team-v0.4.7-test.3-smoke
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
- /tmp/ai-team-update-v0.4.7-test.3.log 的关键片段
- 后续真实 session json / session jsonl 应保存到哪里
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7-test.3 的测试版更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集旧状态。
3. 使用测试版发布入口执行更新，不要手工拼装 bundle。
4. 本版本是 release-candidate（候选/测试渠道），不是 stable（正式稳定渠道）。
5. 保留完整 stdout/stderr。
6. 更新完成后继续执行校验命令。
7. 任何一步失败都立即停止，不要假装成功。
8. 只做更新现场验收和总控入口检查；如果 ai-team runtime 出现 dispatch_allowed，只记录 host_native_dispatch，不要在安装验收阶段继续调用 spawn_agent。
9. 后续真实控制链路验证必须另存 session json 或 session jsonl。

执行命令：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team doctor --project-root . *>&1
$env:AI_TEAM_RELEASE_METADATA_URL = "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/candidates/v0.4.7-test.3/ai-team-bundle-v0.4.7-test.3.release.json"
$script = Join-Path $env:TEMP "install-ai-team-v0.4.7-test.3.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-update-v0.4.7-test.3.log"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

更新后继续执行：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
$smoke = Join-Path $env:TEMP "ai-team-v0.4.7-test.3-smoke"
New-Item -ItemType Directory -Force -Path $smoke | Out-Null
Set-Location $smoke
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
- $env:TEMP\\ai-team-update-v0.4.7-test.3.log 的关键片段
- 后续真实 session json / session jsonl 应保存到哪里
```
