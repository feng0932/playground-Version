# v0.4.6-release-a 中文发版执行说明书

## 1. 这个版本做了什么

`v0.4.6-release-a` 是 `v0.4.6` 的 hotfix 准备版，不改变产品/原型方法论范围，只收口发版后现场继续暴露的三个收口点。

第一，安装现场验收不再只看模型总结。

现在必须同时看到真实安装命令、`ai-team install`、`ai-team doctor`、`ai-team runtime --action total_control_entry` 的命令证据、零退出码证据、标准摘要和当前 `bundle_sha256`。同版本旧包、伪造 stdout、只写总结不执行命令，都不能通过发版检查门。

第二，`/读取回执` 不能先写脏 authority 再失败。

现在回执必须绑定当前 active child thread；`01` 只能把业务 next-hop 指向 `10`；重复回执、错线程回执、unsupported next-hop、Dispatch Snapshot 与 Delivery Owner 漂移，都会在写回 authority 前 fail-closed。

第三，`10` 的机器回执不再预填自循环 next-hop。

`10-执行-产品专家` 的 `recommended_return_target` 默认留空，由真实完成结果决定；不能把 `10 -> 10` 当成默认可消费回执。

当前状态：本文件是发版前执行说明书。还没有推远端、没有打 tag、没有更新 release page，也没有 fresh live transcript 证明 Mac / Windows 现场问题已解决。

## 2. 让大模型去安装和更新的提示词

设备选择：

### 2.1 新安装

#### macOS

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.6-release-a 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用正式安装入口，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装完成后继续执行校验命令。
5. 任何一步失败都立即停止，不要假装成功。
6. 只做安装现场验收；ai-team runtime 出现 dispatch_allowed 时，只记录 host_native_dispatch，不要继续调用 spawn_agent，也不要进入项目业务初始化。

执行命令：
set -o pipefail
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.6-release-a 2>&1 | tee /tmp/ai-team-install-v0.4.6-release-a.log

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
- /tmp/ai-team-install-v0.4.6-release-a.log 的关键片段

输出格式必须包含：
## ai-team v0.4.6-release-a 安装现场验收摘要
- 新安装是否完成：是 / 否
- 实际安装到的 bundle_version / release_tag：v0.4.6-release-a / ai-team-bundle-v0.4.6-release-a
- ai-team doctor 的关键字段：machine_vs_project=...；risk_level=...；recommended_action=...
- ai-team runtime --action total_control_entry 的结果：decision=...；dispatch_target=...；prompt_text=null；host_native_dispatch.required_tool=spawn_agent
- ai-team.lock.json 和 .ai-team/runtime.json 的关键内容：bundle_version=...；release_tag=...
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block：否
- 现场验收结论：通过安装层 smoke；停止在安装验收，不进入项目业务初始化。
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.6-release-a 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用正式安装入口，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装完成后继续执行校验命令。
5. 任何一步失败都立即停止，不要假装成功。
6. 只做安装现场验收；ai-team runtime 出现 dispatch_allowed 时，只记录 host_native_dispatch，不要继续调用 spawn_agent，也不要进入项目业务初始化。

执行命令：
$script = Join-Path $env:TEMP "install-ai-team-v0.4.6-release-a.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.6-release-a *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-install-v0.4.6-release-a.log"
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
- $env:TEMP\\ai-team-install-v0.4.6-release-a.log 的关键片段

输出格式必须包含：
## ai-team v0.4.6-release-a 安装现场验收摘要
- 新安装是否完成：是 / 否
- 实际安装到的 bundle_version / release_tag：v0.4.6-release-a / ai-team-bundle-v0.4.6-release-a
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
你现在要在本机实际执行 ai-team v0.4.6-release-a 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集旧状态。
3. 使用正式安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新完成后继续执行校验命令。
6. 任何一步失败都立即停止，不要假装成功。
7. 只做更新现场验收；ai-team runtime 出现 dispatch_allowed 时，只记录 host_native_dispatch，不要继续调用 spawn_agent，也不要进入项目业务初始化。

执行命令：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team || true
ai-team doctor --project-root . || true
set -o pipefail
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.6-release-a 2>&1 | tee /tmp/ai-team-update-v0.4.6-release-a.log

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
- /tmp/ai-team-update-v0.4.6-release-a.log 的关键片段
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.6-release-a 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集旧状态。
3. 使用正式安装入口执行更新，不要手工拼装 bundle。
4. 保留完整 stdout/stderr。
5. 更新完成后继续执行校验命令。
6. 任何一步失败都立即停止，不要假装成功。
7. 只做更新现场验收；ai-team runtime 出现 dispatch_allowed 时，只记录 host_native_dispatch，不要继续调用 spawn_agent，也不要进入项目业务初始化。

执行命令：
$env:Path = "$HOME\\.ai-team\\bin;$env:Path"
where.exe ai-team
ai-team doctor --project-root . *>&1
$script = Join-Path $env:TEMP "install-ai-team-v0.4.6-release-a.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.6-release-a *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-update-v0.4.6-release-a.log"
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
- $env:TEMP\\ai-team-update-v0.4.6-release-a.log 的关键片段
```
