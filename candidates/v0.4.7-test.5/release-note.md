# v0.4.7-test.5 中文发版执行说明书

## 1. 这个版本做了什么

`v0.4.7-test.5` 是 `v0.4.7` 正式版前的 CR-004 测试候选，不是正式稳定版。

这版把 CR-004 已冻结的产品发现增强放进测试候选链路：

1. `01-编排-初始化项目包` 前置项目级七类必筛，要求把必问清单、条件触发清单和六个项目级宿主写清楚。
2. `10-执行-产品专家` 承接 `01` 的 `screening_result`，在需求级继续做三阶段深挖，并写出 `deepening_result`。
3. `20 / 21 / 22` 审查角色能看到机器回执和正式宿主证据；缺字段、触发未闭合、内容没有真实承接或原型泄漏内部字段时要阻断。
4. 回执字段负责可追踪和阻断入口，审查负责判断内容对不对。

这版要验证的是 CR-004 能不能从已冻结需求进入真实候选包，并在 fresh install、doctor、runtime smoke 和受影响回归里保持可运行、可追踪、可审查。

通过本候选后，只能说：

- `v0.4.7-test.5` 作为 CR-004 测试候选已经可安装、可运行、可验收。

不能说：

- `v0.4.7` 已经正式发版。
- `v0.4.7` 已经切 stable。
- `stable-release.json` 已经更新到 `v0.4.7`。

## 2. 让大模型去安装和更新的提示词

### 2.1 新安装

#### macOS

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7-test.5 的测试版新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用内部 Gitea 测试版发布入口，不要手工拼装 bundle。
3. 本版本是 release-candidate，不是 stable。
4. 保留完整 stdout/stderr。
5. 安装完成后继续执行校验命令。
6. 任一步失败都立即停止，不要脑补成功。
7. 只做安装现场验收和总控入口检查；如果 runtime 返回 dispatch_allowed，只记录 host_native_dispatch，不要继续调用 spawn_agent。

执行命令：
set -o pipefail
export AI_TEAM_RELEASE_METADATA_URL="http://192.168.1.152/yuhua/playground-Version/raw/branch/main/candidates/v0.4.7-test.5/ai-team-bundle-v0.4.7-test.5.release.json"
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash 2>&1 | tee /tmp/ai-team-install-v0.4.7-test.5.log

安装后继续执行：
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team
mkdir -p /tmp/ai-team-v0.4.7-test.5-smoke
cd /tmp/ai-team-v0.4.7-test.5-smoke
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry
cat ai-team.lock.json 2>/dev/null || true
cat .ai-team/runtime.json 2>/dev/null || true

最终必须输出：
- 是否真的完成了新安装
- 实际安装到的 bundle_version / release_tag
- 渠道
- ai-team doctor 的关键字段
- ai-team runtime --action total_control_entry 的结果
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- /tmp/ai-team-install-v0.4.7-test.5.log 的关键片段

输出格式必须包含：
## ai-team v0.4.7-test.5 安装现场验收摘要
- 新安装是否完成：是 / 否
- 实际安装到的 bundle_version / release_tag：v0.4.7-test.5 / ai-team-bundle-v0.4.7-test.5
- 渠道：release-candidate
- ai-team doctor 的关键字段：machine_vs_project=...；risk_level=...；recommended_action=...
- runtime 入口结果：decision=...；dispatch_target=...；prompt_text=null；host_native_dispatch.required_tool=spawn_agent
- 现场验收结论：通过安装层 smoke / 未通过，原因是...
- 业务初始化状态：停止在安装验收，不进入项目业务初始化。
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7-test.5 的测试版新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 使用内部 Gitea 测试版发布入口，不要手工拼装 bundle。
3. 本版本是 release-candidate，不是 stable。
4. 保留完整 stdout/stderr。
5. 安装完成后继续执行校验命令。
6. 任一步失败都立即停止，不要脑补成功。
7. 只做安装现场验收和总控入口检查；如果 runtime 返回 dispatch_allowed，只记录 host_native_dispatch，不要继续调用 spawn_agent。

执行命令：
$env:AI_TEAM_RELEASE_METADATA_URL = "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/candidates/v0.4.7-test.5/ai-team-bundle-v0.4.7-test.5.release.json"
$script = Join-Path $env:TEMP "install-ai-team-v0.4.7-test.5.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script *>&1 | Tee-Object -FilePath "$env:TEMP\ai-team-install-v0.4.7-test.5.log"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

安装后继续执行：
$env:Path = "$HOME\.ai-team\bin;$env:Path"
where.exe ai-team
$smoke = Join-Path $env:TEMP "ai-team-v0.4.7-test.5-smoke"
New-Item -ItemType Directory -Force -Path $smoke | Out-Null
Set-Location $smoke
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry
Get-Content ai-team.lock.json -ErrorAction SilentlyContinue
Get-Content .ai-team\runtime.json -ErrorAction SilentlyContinue

最终必须输出：
- 是否真的完成了新安装
- 实际安装到的 bundle_version / release_tag
- 渠道
- ai-team doctor 的关键字段
- ai-team runtime --action total_control_entry 的结果
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- $env:TEMP\ai-team-install-v0.4.7-test.5.log 的关键片段

输出格式必须包含：
## ai-team v0.4.7-test.5 安装现场验收摘要
- 新安装是否完成：是 / 否
- 实际安装到的 bundle_version / release_tag：v0.4.7-test.5 / ai-team-bundle-v0.4.7-test.5
- 渠道：release-candidate
- ai-team doctor 的关键字段：machine_vs_project=...；risk_level=...；recommended_action=...
- runtime 入口结果：decision=...；dispatch_target=...；prompt_text=null；host_native_dispatch.required_tool=spawn_agent
- 现场验收结论：通过安装层 smoke / 未通过，原因是...
- 业务初始化状态：停止在安装验收，不进入项目业务初始化。
```

### 2.2 更新

#### macOS

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7-test.5 的测试版更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 shell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集 which ai-team 和 ai-team doctor 的旧状态。
3. 使用内部 Gitea 测试版发布入口，不要手工拼装 bundle。
4. 本版本是 release-candidate，不是 stable。
5. 保留完整 stdout/stderr。
6. 任一步失败都立即停止，不要脑补成功。
7. 只做更新现场验收和总控入口检查；如果 runtime 返回 dispatch_allowed，只记录 host_native_dispatch，不要继续调用 spawn_agent。

执行命令：
set -o pipefail
export PATH="$HOME/.ai-team/bin:$PATH"
which ai-team || true
ai-team doctor --project-root . || true
export AI_TEAM_RELEASE_METADATA_URL="http://192.168.1.152/yuhua/playground-Version/raw/branch/main/candidates/v0.4.7-test.5/ai-team-bundle-v0.4.7-test.5.release.json"
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash 2>&1 | tee /tmp/ai-team-update-v0.4.7-test.5.log
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry

最终必须输出：
- 是否真的完成了更新
- 更新前后的 bundle_version / release_tag
- 渠道
- ai-team doctor 的更新前后关键字段
- ai-team runtime --action total_control_entry 的结果
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- /tmp/ai-team-update-v0.4.7-test.5.log 的关键片段
- 是否停止在更新验收、不进入项目业务初始化
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在本机实际执行 ai-team v0.4.7-test.5 的测试版更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

要求：
1. 先确认当前机器有 PowerShell、网络和文件写权限；如果没有，直接说明不能执行。
2. 更新前先采集 where.exe ai-team 和 ai-team doctor 的旧状态。
3. 使用内部 Gitea 测试版发布入口，不要手工拼装 bundle。
4. 本版本是 release-candidate，不是 stable。
5. 保留完整 stdout/stderr。
6. 任一步失败都立即停止，不要脑补成功。
7. 只做更新现场验收和总控入口检查；如果 runtime 返回 dispatch_allowed，只记录 host_native_dispatch，不要继续调用 spawn_agent。

执行命令：
$env:Path = "$HOME\.ai-team\bin;$env:Path"
where.exe ai-team
ai-team doctor --project-root .
$env:AI_TEAM_RELEASE_METADATA_URL = "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/candidates/v0.4.7-test.5/ai-team-bundle-v0.4.7-test.5.release.json"
$script = Join-Path $env:TEMP "install-ai-team-v0.4.7-test.5.ps1"
Invoke-WebRequest http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1 -UseBasicParsing -OutFile $script
powershell -ExecutionPolicy Bypass -File $script *>&1 | Tee-Object -FilePath "$env:TEMP\ai-team-update-v0.4.7-test.5.log"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
ai-team install --project-root .
ai-team doctor --project-root .
ai-team runtime --project-root . --action total_control_entry

最终必须输出：
- 是否真的完成了更新
- 更新前后的 bundle_version / release_tag
- 渠道
- ai-team doctor 的更新前后关键字段
- ai-team runtime --action total_control_entry 的结果
- 是否出现 checksum mismatch、metadata fetch failure、downgrade block
- $env:TEMP\ai-team-update-v0.4.7-test.5.log 的关键片段
- 是否停止在更新验收、不进入项目业务初始化
```
