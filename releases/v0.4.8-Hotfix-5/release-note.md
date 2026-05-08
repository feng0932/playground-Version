# v0.4.8-Hotfix-5 中文发版执行说明书

## 1. 这个版本做了什么

`v0.4.8-Hotfix-5` 修复 Hotfix-4 发布后暴露的 `02` 派发死路。

Hotfix-4 已修复执行结构缺口下的 `01` 限定追问，但真实现场继续证明：fresh `/总控` 会把 governance snapshot drift 误判成安装准入失败，转而派发 `02-编排-安装与运行检查`。`02` 可以完成检查并写出人类可读结论，但它不是 primary-window agent，正式 `/读取回执` 只消费 `01 / 10`，所以主链无法接回。

Hotfix-5 把安装准入收回 runtime 本地窄检查：runtime 状态真实缺失或损坏时，直接返回 `runtime_not_ready` 和 repair 指引；runtime 核心状态可用但只是治理快照漂移时，继续进入 primary-window 主链，通常派发 `01`。旧现场残留的 `02` dispatch snapshot 只返回结构化 fail-closed 解释，不消费、不续派、不改写 authority。

本版同时明确：`02-编排-安装与运行检查` 不再属于正式 runtime opening 主链；后续版本不能因为 bundle 中仍保留 02 agent 文件，就把它误拉回主链。

## 2. 让大模型去安装和更新的提示词

### 2.1 新安装

#### macOS

把下面这段直接发给大模型：

```text
你现在要在 macOS 上实际执行 ai-team v0.4.8-Hotfix-5 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

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
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.8-Hotfix-5 2>&1 | tee /tmp/ai-team-install-v0.4.8-Hotfix-5.log

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
8. 是否错误派发 02；若派发 02，必须判定失败。
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在 Windows PowerShell 上实际执行 ai-team v0.4.8-Hotfix-5 的正式新安装，不要只解释步骤，要真的运行命令，并把关键结果输出出来。

前置检查：
1. 确认 PowerShell 可用。
2. 确认可以访问 http://192.168.1.152/。
3. 确认目标项目目录可写。

执行要求：
1. 使用正式远端安装入口，不要手工拼装 bundle。
2. 保留完整 stdout/stderr。
3. 任一步失败即停止，不得脑补成功。

命令：

$script = Join-Path $env:TEMP "install-ai-team-v0.4.8-Hotfix-5.ps1"
Invoke-WebRequest -UseBasicParsing -Uri "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1" -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.8-Hotfix-5 *>&1 | Tee-Object -FilePath "$env:TEMP\ai-team-install-v0.4.8-Hotfix-5.log"
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
8. 是否错误派发 02；若派发 02，必须判定失败。
```

### 2.2 更新

#### macOS

把下面这段直接发给大模型：

```text
你现在要在 macOS 上实际执行 ai-team v0.4.8-Hotfix-5 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

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
curl -fsSL http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.sh | bash -s -- v0.4.8-Hotfix-5 2>&1 | tee /tmp/ai-team-update-v0.4.8-Hotfix-5.log

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
7. 是否错误派发 02；若派发 02，必须判定失败。
```

#### Windows

把下面这段直接发给大模型：

```text
你现在要在 Windows PowerShell 上实际执行 ai-team v0.4.8-Hotfix-5 的正式更新，不要只解释步骤，要真的运行命令，并把更新前后结果对照输出。

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

$script = Join-Path $env:TEMP "install-ai-team-v0.4.8-Hotfix-5.ps1"
Invoke-WebRequest -UseBasicParsing -Uri "http://192.168.1.152/yuhua/playground-Version/raw/branch/main/install-ai-team.ps1" -OutFile $script
powershell -ExecutionPolicy Bypass -File $script -Version v0.4.8-Hotfix-5 *>&1 | Tee-Object -FilePath "$env:TEMP\ai-team-update-v0.4.8-Hotfix-5.log"
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
7. 是否错误派发 02；若派发 02，必须判定失败。
```
