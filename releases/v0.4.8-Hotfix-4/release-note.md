# v0.4.8-Hotfix-4 中文发版执行说明书

## 1. 这个版本做了什么

`v0.4.8-Hotfix-4` 修复 Hotfix-3 发布后暴露的执行结构循环阻断。

Hotfix-3 已能阻止 `01` 缺执行结构时非法派发 `10`，但没有给 `00` 一个专门的“执行结构修复”下一跳。结果是 `/读取回执` 后 fresh `/总控` 又泛化派发 `01`，且默认不授权子线程直接追问用户，导致 `01` 反复回同一个 `execution-directory-derivation-blocked`。

Hotfix-4 将 primary window 派发默认改为允许在限定范围内直接追问用户；当 `01` 已完成项目包但执行结构未闭合时，`00` 进入 `execution_structure_repair_rejudge_ready`，只让 `01` 追问当前执行结构缺口。`10` 门禁不放松，仍必须等正式模块 PRD 写入目标闭合后才能派发。

## 2. 让大模型去安装和更新的提示词

### 2.1 新安装

#### macOS

把下面这段直接发给大模型：

```text
你现在要在 macOS 上实际执行 ai-team v0.4.8-Hotfix-4 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

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
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.8-Hotfix-4 2>&1 | tee /tmp/ai-team-install-v0.4.8-Hotfix-4.log

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
你现在要在 Windows PowerShell 上实际执行 ai-team v0.4.8-Hotfix-4 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

前置检查：
1. 确认 PowerShell 可用。
2. 确认可以访问 http://192.168.1.152/。
3. 确认目标项目目录可写。

执行要求：
1. 使用正式远端安装入口，不要手工拼装 bundle。
2. 保留完整 stdout/stderr。
3. 任一步失败即停止，不得脑补成功。

命令：

$script = Join-Path $env:TEMP "install-ai-team-v0.4.8-Hotfix-4.ps1"
Invoke-WebRequest -UseBasicParsing -Uri "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1" -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.8-Hotfix-4 *>&1 | Tee-Object -FilePath "$env:TEMP\ai-team-install-v0.4.8-Hotfix-4.log"
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
你现在要在 macOS 上实际执行 ai-team v0.4.8-Hotfix-4 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

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
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.8-Hotfix-4 2>&1 | tee /tmp/ai-team-update-v0.4.8-Hotfix-4.log

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
你现在要在 Windows PowerShell 上实际执行 ai-team v0.4.8-Hotfix-4 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

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

$script = Join-Path $env:TEMP "install-ai-team-v0.4.8-Hotfix-4.ps1"
Invoke-WebRequest -UseBasicParsing -Uri "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1" -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.8-Hotfix-4 *>&1 | Tee-Object -FilePath "$env:TEMP\ai-team-update-v0.4.8-Hotfix-4.log"
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
