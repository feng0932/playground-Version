# v0.4.7 中文发版执行说明书

## 1. 这个版本做了什么

`v0.4.7` 把产品发现链补到正式稳定版里。

这版解决的核心问题是：进入开发前，AI 不能只凭零散描述往下做，也不能把关键产品问题留到开发阶段临时补料。现在 `01` 和 `10` 会在前置阶段主动把项目级必筛、需求边界、原型前确认和 UI/UE 回修口径问清楚，并把结果写成机器可追踪回执，交给 `00` 判断下一步。

主要变化有四个：

1. `01-编排-初始化项目包` 增加项目级七类必筛，覆盖合规、商业化、增长、数据指标、权限角色、原型标准和共享资产底座。
2. `10-执行-产品专家` 固定三段深化：`requirements_discovery`、`prototype_preconfirmation`、`uiue_reclaim_confirmation`。
3. `01 / 10` 的终态回执增加 `screening_result / deepening_result`，用于让 `00` 可追踪地判断有没有完成前置问题。
4. `20 / 21 / 22` 审查链同步收口，不再只看有没有回执字段，而要继续审查内容是否真的能支撑进入下一阶段。

用人话说：这版让 AI 在开发前把关键需求问扎实，把缺口显性化，把“开发阶段才发现要补料”的风险提前拦住。`v0.4.7-test.6` 已经证明 `01 / 10` 第一次回执可以不靠 correction 被 `00` 直接消费；正式版沿用这条已验证链路。

## 2. 让大模型去安装和更新的提示词

### 2.1 新安装

#### macOS

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用正式远端安装入口，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装完成后继续执行校验命令。
5. 任何一步失败都立即停止，不要假装成功。
6. 只做安装现场验收；ai-team runtime 出现 dispatch_allowed 时，只记录 host_native_dispatch，不要继续调用 spawn_agent，也不要进入项目业务初始化。

执行命令：
set -o pipefail
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.7 2>&1 | tee /tmp/ai-team-install-v0.4.7.log

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
- /tmp/ai-team-install-v0.4.7.log 的关键片段

输出格式必须包含：
## ai-team v0.4.7 安装现场验收摘要
- 新安装是否完成：是 / 否
- 实际安装到的 bundle_version / release_tag：v0.4.7 / ai-team-bundle-v0.4.7
- ai-team doctor 的关键字段：machine_vs_project=...；risk_level=...；recommended_action=...
- ai-team runtime --action total_control_entry 的结果：decision=...；dispatch_target=...；prompt_text=null；host_native_dispatch.required_tool=spawn_agent
- ai-team.lock.json 和 .ai-team/runtime.json 的关键内容：bundle_version=...；release_tag=...
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block：否
- 现场验收结论：通过安装层 smoke；停止在安装验收，不进入项目业务初始化。
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用正式远端安装入口，不要手工拼装 bundle。
3. 保留完整 stdout/stderr。
4. 安装完成后继续执行校验命令。
5. 任何一步失败都立即停止，不要假装成功。
6. 只做安装现场验收；ai-team runtime 出现 dispatch_allowed 时，只记录 host_native_dispatch，不要继续调用 spawn_agent，也不要进入项目业务初始化。

执行命令：
$script = Join-Path $env:TEMP "install-ai-team-v0.4.7.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.7 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-install-v0.4.7.log"
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
- $env:TEMP\\ai-team-install-v0.4.7.log 的关键片段

输出格式必须包含：
## ai-team v0.4.7 安装现场验收摘要
- 新安装是否完成：是 / 否
- 实际安装到的 bundle_version / release_tag：v0.4.7 / ai-team-bundle-v0.4.7
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
你现在要在本机实际执行 ai-team v0.4.7 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

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
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.7 2>&1 | tee /tmp/ai-team-update-v0.4.7.log

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
- /tmp/ai-team-update-v0.4.7.log 的关键片段
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

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
$script = Join-Path $env:TEMP "install-ai-team-v0.4.7.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.7 *>&1 | Tee-Object -FilePath "$env:TEMP\\ai-team-update-v0.4.7.log"
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
- $env:TEMP\\ai-team-update-v0.4.7.log 的关键片段
```
